"""Passo 3 — relatorio. Transforma os Findings num markdown legivel (o print do post)."""

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from collections.abc import Sequence
from typing import TYPE_CHECKING

from .models import Finding, Severity, Verdict

if TYPE_CHECKING:
    from .fixer import Fix

_VERDICT_LABEL = {
    Verdict.BREAKS: "🔴 QUEBRA",
    Verdict.REVIEW: "🟡 REVISAR",
    Verdict.SAFE: "🟢 OK",
}
_VERDICT_ORDER = {Verdict.BREAKS: 0, Verdict.REVIEW: 1, Verdict.SAFE: 2}
_SEV_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}


def _sort_key(f: Finding):
    return (
        _VERDICT_ORDER[f.verdict],
        _SEV_ORDER[f.candidate.severity],
        f.candidate.file,
        f.candidate.line,
    )


def build_markdown(
    findings: list[Finding],
    root: str,
    used_llm: bool,
    fixes: Sequence[Fix] | None = None,
    patch: str | None = None,
    applied: bool = False,
) -> str:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    verdict_counts = Counter(f.verdict for f in findings)
    rule_counts = Counter(f.candidate.rule_id for f in findings if f.verdict == Verdict.BREAKS)

    lines: list[str] = []
    lines.append("# Relatorio — CNPJ Alfanumerico")
    lines.append("")
    lines.append(f"- **Alvo varrido:** `{root}`")
    lines.append(f"- **Data:** {now}")
    lines.append(f"- **Classificacao:** {'Claude (LLM)' if used_llm else 'somente regex'}")
    lines.append("- **Referencia:** IN RFB 2.229/2024 — CNPJ alfanumerico a partir de julho/2026")
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

    if fixes:
        real = [fx for fx in fixes if fx.original != fx.fixed]
        status = (
            "APLICADAS no working tree" if applied else "propostas (dry-run — nada foi escrito)"
        )
        lines.append(f"## 🛠️ Correções {status} ({len(real)})")
        lines.append("")
        for fx in real:
            lines.append(f"### `{fx.file}:{fx.start_line}-{fx.end_line}`")
            lines.append("")
            if fx.note:
                lines.append(f"**Nota:** {fx.note}")
                lines.append("")
        if patch and patch.strip():
            lines.append("### Patch consolidado")
            lines.append("")
            lines.append("Aplique com `git apply cnpj-fixes.patch` (revise antes):")
            lines.append("")
            lines.append("```diff")
            lines.append(patch.rstrip("\n"))
            lines.append("```")
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
