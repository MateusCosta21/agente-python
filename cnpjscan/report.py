"""Passo 3 — relatorio. Transforma os Findings num markdown legivel (o print do post)."""

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter

from .models import Finding, Verdict, Severity

_VERDICT_LABEL = {
    Verdict.BREAKS: "🔴 QUEBRA",
    Verdict.REVIEW: "🟡 REVISAR",
    Verdict.SAFE: "🟢 OK",
}
_VERDICT_ORDER = {Verdict.BREAKS: 0, Verdict.REVIEW: 1, Verdict.SAFE: 2}
_SEV_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}


def _sort_key(f: Finding):
    return (_VERDICT_ORDER[f.verdict], _SEV_ORDER[f.candidate.severity], f.candidate.file, f.candidate.line)


def build_markdown(findings: list[Finding], root: str, used_llm: bool) -> str:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    verdict_counts = Counter(f.verdict for f in findings)
    rule_counts = Counter(f.candidate.rule_id for f in findings if f.verdict == Verdict.BREAKS)

    lines: list[str] = []
    lines.append("# Relatorio — CNPJ Alfanumerico")
    lines.append("")
    lines.append(f"- **Alvo varrido:** `{root}`")
    lines.append(f"- **Data:** {now}")
    lines.append(f"- **Classificacao:** {'Claude (LLM)' if used_llm else 'somente regex'}")
    lines.append(f"- **Referencia:** IN RFB 2.229/2024 — CNPJ alfanumerico a partir de julho/2026")
    lines.append("")
    lines.append("## Resumo")
    lines.append("")
    lines.append("| Veredito | Qtd |")
    lines.append("|---|---:|")
    for v in (Verdict.BREAKS, Verdict.REVIEW, Verdict.SAFE):
        lines.append(f"| {_VERDICT_LABEL[v]} | {verdict_counts.get(v, 0)} |")
    lines.append(f"| **Total** | **{len(findings)}** |")
    lines.append("")

    if rule_counts:
        lines.append("### Quebras por categoria")
        lines.append("")
        lines.append("| Categoria | Ocorrencias |")
        lines.append("|---|---:|")
        for rule_id, n in rule_counts.most_common():
            lines.append(f"| `{rule_id}` | {n} |")
        lines.append("")

    for verdict in (Verdict.BREAKS, Verdict.REVIEW, Verdict.SAFE):
        group = sorted((f for f in findings if f.verdict == verdict), key=_sort_key)
        if not group:
            continue
        lines.append(f"## {_VERDICT_LABEL[verdict]} ({len(group)})")
        lines.append("")
        for f in group:
            c = f.candidate
            lines.append(f"### `{c.file}:{c.line}` — {c.severity.value} · `{c.rule_id}`")
            lines.append("")
            lines.append(f"**Por que:** {f.reason or c.rule_desc}")
            lines.append("")
            if f.suggested_fix:
                lines.append(f"**Sugestao:** {f.suggested_fix}")
                lines.append("")
            lines.append("```")
            lines.append(c.context)
            lines.append("```")
            lines.append(f"_confianca: {f.confidence}_")
            lines.append("")

    return "\n".join(lines)


def build_json(findings: list[Finding]) -> str:
    return json.dumps([f.to_dict() for f in findings], ensure_ascii=False, indent=2)
