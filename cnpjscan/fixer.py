"""Passo 4 (v2) — correção assistida com human-in-the-loop.

Para cada achado marcado como QUEBRA, pede à Claude o trecho corrigido (que passa a
aceitar CNPJ alfanumérico E o numérico legado), monta um diff unificado e grava um
`.patch` aplicável com `git apply`. Nada é escrito nos arquivos a menos que o usuário
passe `--apply` — o agente propõe, o humano decide.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import llm
from .models import Finding, Verdict

# Callback de progresso: (concluidos, total) -> None
ProgressFn = Callable[[int, int], None]

WINDOW_RADIUS = 5  # linhas de contexto acima/abaixo do achado enviadas ao modelo
MERGE_GAP = 3  # janelas a <= 3 linhas de distância são fundidas

SYSTEM_PROMPT = """\
Voce e' um engenheiro senior corrigindo um codebase para o CNPJ alfanumerico \
(IN RFB 2.229/2024, em vigor em julho/2026).

Regras da correcao:
- As 12 primeiras posicoes do CNPJ passam a aceitar A-Z e 0-9; os 2 digitos \
verificadores finais continuam SOMENTE numericos; total continua 14 caracteres; \
mascara XX.XXX.XXX/XXXX-XX inalterada.
- O DV continua modulo 11, mas calculado sobre (valor ASCII do caractere - 48).
- CNPJs antigos continuam numericos: a correcao DEVE continuar aceitando o formato \
numerico legado (aceitar os DOIS).

O que fazer, conforme o caso:
- Regex numerica -> aceitar letras nas 12 primeiras posicoes, manter DV numerico. \
Ex.: `\\d{14}` vira `[A-Z\\d]{12}\\d{2}`; a mascara vira \
`[A-Z\\d]{2}\\.[A-Z\\d]{3}\\.[A-Z\\d]{3}/[A-Z\\d]{4}-\\d{2}`.
- Cast para inteiro -> tratar como string; nunca converter CNPJ para int.
- Coluna de banco numerica -> mudar para string/VARCHAR(14).
- Checagem is-digit -> validar comprimento/alfanumerico em vez de so' digito.
- Mascara de input so' de digitos -> permitir letras nas 12 primeiras posicoes.

Faca a MENOR mudanca que resolve. Preserve indentacao, estilo e comportamento. \
NAO refatore alem do necessario, NAO adicione comentarios explicativos longos. \
Se o trecho ja' estiver correto, devolva-o sem mudancas e changed=false.

Voce recebe um trecho com numeros de linha. Devolva SOMENTE o codigo corrigido das \
mesmas linhas (sem os numeros de linha, sem cercas de codigo), mantendo a mesma \
quantidade logica de linhas quando possivel."""

FIX_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "changed": {"type": "boolean"},
        "fixed_code": {"type": "string"},
        "note": {"type": "string"},
    },
    "required": ["changed", "fixed_code", "note"],
}


@dataclass
class Fix:
    file: str
    start_line: int  # 1-indexed, inclusivo
    end_line: int  # 1-indexed, inclusivo
    original: str
    fixed: str
    note: str


def _windows_for_file(lines: list[str], finding_lines: list[int]) -> list[tuple[int, int]]:
    """Constroi e funde janelas [start, end] (1-indexed) ao redor de cada achado."""
    n = len(lines)
    raw = []
    for ln in sorted(set(finding_lines)):
        start = max(1, ln - WINDOW_RADIUS)
        end = min(n, ln + WINDOW_RADIUS)
        raw.append((start, end))
    merged: list[list[int]] = []
    for start, end in raw:
        if merged and start <= merged[-1][1] + MERGE_GAP:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def _numbered(lines: list[str], start: int, end: int) -> str:
    return "\n".join(f"{i}| {lines[i - 1]}" for i in range(start, end + 1))


def generate_fixes(
    findings: list[Finding],
    model: str | None = None,
    progress: ProgressFn | None = None,
    provider: str | None = None,
) -> list[Fix]:
    breaks = [f for f in findings if f.verdict == Verdict.BREAKS]
    if not breaks:
        return []
    provider = llm.resolve_provider(provider)
    if not llm.api_key_present(provider):
        raise RuntimeError(
            f"{llm.api_key_env(provider)} nao definido — a correcao (v2) exige um provider de LLM."
        )
    try:
        llm.ensure_available(provider)
    except llm.LLMError as exc:
        raise RuntimeError(str(exc)) from exc

    model = model or llm.default_model(provider)

    by_file: dict[str, list[int]] = {}
    for f in breaks:
        by_file.setdefault(f.candidate.file, []).append(f.candidate.line)

    # Le cada arquivo uma unica vez e ja' calcula as janelas de correcao,
    # para nao reabrir os arquivos so' para contar o total do progresso.
    plan: list[tuple[str, list[str], int, int]] = []
    for file, finding_lines in by_file.items():
        try:
            lines = Path(file).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for start, end in _windows_for_file(lines, finding_lines):
            plan.append((file, lines, start, end))

    fixes: list[Fix] = []
    total = len(plan)
    done = 0

    for file, lines, start, end in plan:
        if progress:
            progress(done, total)
        done += 1
        original_block = "\n".join(lines[start - 1 : end])
        user_msg = (
            f"Arquivo: {file}\n"
            f"Corrija o trecho abaixo (linhas {start}-{end}). Devolva o codigo "
            f"corrigido dessas linhas.\n\n{_numbered(lines, start, end)}"
        )
        try:
            text = llm.complete_json(
                provider=provider,
                model=model,
                system=SYSTEM_PROMPT,
                user=user_msg,
                schema=FIX_SCHEMA,
                effort="medium",
                max_tokens=2048,
            )
            data = llm.loads_lenient(text)
        except Exception as exc:  # rede/parse — pula esta janela
            fixes.append(
                Fix(
                    file,
                    start,
                    end,
                    original_block,
                    original_block,
                    f"[falha ao gerar correcao: {type(exc).__name__}]",
                )
            )
            continue

        if not data.get("changed"):
            continue
        fixed_block = data.get("fixed_code", "").rstrip("\n")
        if fixed_block and fixed_block != original_block:
            fixes.append(
                Fix(file, start, end, original_block, fixed_block, data.get("note", "").strip())
            )

    if progress:
        progress(total, total)
    return fixes


def apply_fix_to_text(src: str, fixes_for_file: list[Fix]) -> str:
    """Aplica os fixes de um arquivo, de baixo para cima (preserva numeracao)."""
    lines = src.splitlines()
    for fx in sorted(fixes_for_file, key=lambda f: f.start_line, reverse=True):
        new_lines = fx.fixed.splitlines()
        lines[fx.start_line - 1 : fx.end_line] = new_lines
    return "\n".join(lines) + ("\n" if src.endswith("\n") else "")


def unified_patch(fixes: list[Fix]) -> str:
    """Gera um patch unico (git apply) com todos os arquivos alterados."""
    by_file: dict[str, list[Fix]] = {}
    for fx in fixes:
        if fx.original != fx.fixed:
            by_file.setdefault(fx.file, []).append(fx)

    out: list[str] = []
    cwd = Path.cwd()
    for file, file_fixes in by_file.items():
        try:
            original = Path(file).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        patched = apply_fix_to_text(original, file_fixes)
        try:
            rel = str(Path(file).resolve().relative_to(cwd))
        except ValueError:
            rel = file
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
        out.extend(diff)
    return "".join(out)
