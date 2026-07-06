"""Estruturas de dados compartilhadas pelo scanner, classificador e relatorio."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Severity(str, Enum):
    HIGH = "HIGH"  # quase certo que quebra com alfanumerico
    MEDIUM = "MEDIUM"  # provavel, depende do contexto
    LOW = "LOW"  # vale revisar


class Verdict(str, Enum):
    BREAKS = "BREAKS"  # quebra com CNPJ alfanumerico, precisa de correcao
    SAFE = "SAFE"  # nao quebra / falso positivo
    REVIEW = "REVIEW"  # ambiguo, humano precisa decidir


@dataclass
class Candidate:
    """Um ponto do codigo que o scanner deterministico marcou como suspeito."""

    file: str
    line: int
    rule_id: str
    rule_desc: str
    severity: Severity
    language: str
    matched_text: str
    context: str  # linhas ao redor, com numeracao

    def key(self) -> tuple[str, int, str]:
        return (self.file, self.line, self.rule_id)


@dataclass
class Finding:
    """Um candidato apos passar pela classificacao (LLM ou modo regex)."""

    candidate: Candidate
    verdict: Verdict
    reason: str
    suggested_fix: str
    confidence: str  # "alta" | "media" | "baixa" | "regex"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["candidate"]["severity"] = self.candidate.severity.value
        d["verdict"] = self.verdict.value
        return d
