"""Passo 2 — classificacao com a Claude.

Recebe os candidatos do scanner e, para cada um, decide se REALMENTE quebra com o
CNPJ alfanumerico, distinguindo contexto (codigo de producao x teste x dado
historico x CNPJ de terceiro). Devolve Findings com justificativa e sugestao de fix.

O scanner deterministico ja' cortou o volume; aqui gastamos token so' com os
candidatos que sobraram, em lotes.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable

from .models import Candidate, Finding, Verdict

# Callback de progresso: (concluidos, total) -> None
ProgressFn = Callable[[int, int], None]

BATCH_SIZE = 8
DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
Voce e' um engenheiro de software brasileiro revisando um codebase para a migracao \
do CNPJ alfanumerico (Instrucao Normativa RFB 2.229/2024, em vigor a partir de \
julho/2026).

Fatos da mudanca:
- As 12 primeiras posicoes do CNPJ passam a aceitar letras (A-Z) e numeros (0-9).
- Os 2 digitos verificadores finais continuam SOMENTE numericos.
- A mascara XX.XXX.XXX/XXXX-XX e o total de 14 caracteres NAO mudam.
- O calculo do DV continua modulo 11, mas sobre o valor ASCII do caractere menos 48.
- CNPJs ja' existentes continuam numericos; os sistemas precisam aceitar OS DOIS \
formatos ao mesmo tempo.

Sua tarefa: para cada trecho suspeito, decidir se ele QUEBRA com o CNPJ alfanumerico.

Classifique cada item em:
- BREAKS: assume que CNPJ e' so' numero e vai falhar/corromper com letras \
(regex numerica, cast para inteiro, coluna numerica, checagem is-digit, mascara \
so' de digitos).
- SAFE: falso positivo, ou codigo que ja' trata string/alfanumerico, ou um numero \
de 14 digitos que claramente NAO e' CNPJ (telefone, id, timestamp).
- REVIEW: ambiguo e precisa de decisao humana. Use principalmente para CNPJ literal \
hardcoded: pode ser de terceiro (fornecedor/parceiro — NAO mudar), dado historico/\
fiscal (NAO pode mudar por lei) ou da propria empresa. Nao invente qual e'; marque \
REVIEW e explique o dilema.

Seja conservador: nao marque BREAKS sem evidencia no trecho. Responda em portugues, \
justificativas curtas e diretas. A sugestao de fix deve ser no idioma/framework do \
trecho (ex.: Laravel migration, regex JS, validacao PHP)."""

RESULT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["BREAKS", "SAFE", "REVIEW"]},
                    "confidence": {"type": "string", "enum": ["alta", "media", "baixa"]},
                    "reason": {"type": "string"},
                    "suggested_fix": {"type": "string"},
                },
                "required": ["index", "verdict", "confidence", "reason", "suggested_fix"],
            },
        }
    },
    "required": ["results"],
}


def _render_batch(batch: list[Candidate]) -> str:
    parts = []
    for i, c in enumerate(batch):
        parts.append(
            f"### Item {i}\n"
            f"Arquivo: {c.file}:{c.line}\n"
            f"Regra que disparou: {c.rule_id} — {c.rule_desc}\n"
            f"Trecho (>> marca a linha suspeita):\n```\n{c.context}\n```"
        )
    return "\n\n".join(parts)


def _regex_only_finding(c: Candidate) -> Finding:
    return Finding(
        candidate=c,
        verdict=Verdict.REVIEW,
        reason=f"[modo regex, sem LLM] {c.rule_desc}",
        suggested_fix="Revisar manualmente ou rodar com ANTHROPIC_API_KEY para classificacao automatica.",
        confidence="regex",
    )


def classify(
    candidates: list[Candidate],
    use_llm: bool = True,
    model: str | None = None,
    progress: ProgressFn | None = None,
) -> list[Finding]:
    if not candidates:
        return []

    if not use_llm or not os.environ.get("ANTHROPIC_API_KEY"):
        return [_regex_only_finding(c) for c in candidates]

    try:
        from anthropic import Anthropic
    except ImportError:
        return [_regex_only_finding(c) for c in candidates]

    client = Anthropic()
    model = model or os.environ.get("CNPJSCAN_MODEL") or DEFAULT_MODEL
    findings: list[Finding] = []

    for start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[start : start + BATCH_SIZE]
        if progress:
            progress(start, len(candidates))
        user_msg = (
            "Classifique cada item abaixo. Responda para TODOS os indices "
            f"(0 a {len(batch) - 1}).\n\n" + _render_batch(batch)
        )
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": RESULT_SCHEMA},
                },
                messages=[{"role": "user", "content": user_msg}],
            )
            findings.extend(_parse_response(resp, batch))
        except Exception as exc:  # rede, rate limit, etc. — degrada para regex
            for c in batch:
                f = _regex_only_finding(c)
                f.reason = f"[falha na classificacao: {type(exc).__name__}] {c.rule_desc}"
                findings.append(f)

    if progress:
        progress(len(candidates), len(candidates))
    return findings


def _parse_response(resp, batch: list[Candidate]) -> list[Finding]:
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    data = json.loads(text)
    by_index = {r["index"]: r for r in data.get("results", [])}

    out: list[Finding] = []
    for i, c in enumerate(batch):
        r = by_index.get(i)
        if r is None:
            out.append(_regex_only_finding(c))
            continue
        try:
            verdict = Verdict(r["verdict"])
        except ValueError:
            verdict = Verdict.REVIEW
        out.append(
            Finding(
                candidate=c,
                verdict=verdict,
                reason=r.get("reason", "").strip(),
                suggested_fix=r.get("suggested_fix", "").strip(),
                confidence=r.get("confidence", "media"),
            )
        )
    return out
