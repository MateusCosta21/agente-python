"""Regras deterministicas: onde um codebase costuma assumir que CNPJ e' so' numero.

Cada regra e' um regex barato aplicado linha a linha. `requires_cnpj` significa que a
palavra "cnpj" precisa aparecer na linha OU no contexto ao redor (para cortar ruido).
A camada de LLM (classifier.py) e' quem decide de fato se cada candidato quebra.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Severity


@dataclass(frozen=True)
class Rule:
    id: str
    desc: str
    severity: Severity
    pattern: re.Pattern
    requires_cnpj: bool
    # extensoes as quais a regra se aplica; vazio = todas
    languages: frozenset[str] = frozenset()


def _r(p: str) -> re.Pattern:
    return re.compile(p, re.IGNORECASE)


RULES: list[Rule] = [
    Rule(
        id="regex-numerico",
        desc="Regex que espera N digitos (\\d{14}, [0-9]{14}) — rejeita letras do novo CNPJ",
        severity=Severity.HIGH,
        pattern=_r(r"(?:\\d|\[0-9\])\s*\{\s*1[0-4](?:\s*,\s*1[0-4])?\s*\}"),
        requires_cnpj=True,
    ),
    Rule(
        id="regex-mascara-numerica",
        desc="Regex de CNPJ formatado so' com classes de digito (\\d{2}\\.\\d{3}...)",
        severity=Severity.HIGH,
        pattern=_r(r"(?:\\d|\[0-9\])\{2\}\\?[./-].*(?:\\d|\[0-9\])\{3\}"),
        requires_cnpj=True,
    ),
    Rule(
        id="checagem-digito",
        desc="Checa 'e' so' digito' (is_numeric/ctype_digit/.isdigit/isNumeric) — falha com letra",
        severity=Severity.HIGH,
        pattern=_r(r"\b(?:is_numeric|ctype_digit|isnumeric|isdigit|isDigit)\b|\.isdigit\s*\("),
        requires_cnpj=True,
    ),
    Rule(
        id="cast-inteiro",
        desc="Converte CNPJ para inteiro (intval/parseInt/(int)/Integer.parse/int()/Number()) — corrompe silenciosamente",
        severity=Severity.HIGH,
        pattern=_r(
            r"\b(?:intval|floatval|parseInt|parseFloat|bigint|Integer\.parse\w*|Long\.parse\w*)\s*\("
            r"|\(\s*int\s*\)|::\s*(?:big)?int\b|\bint\s*\(|\bNumber\s*\("
        ),
        requires_cnpj=True,
    ),
    Rule(
        id="coluna-numerica",
        desc="Coluna de banco numerica para CNPJ (bigInteger/BIGINT/NUMERIC/DECIMAL) — precisa virar VARCHAR/string",
        severity=Severity.HIGH,
        pattern=_r(
            r"\b(?:unsignedBigInteger|bigInteger|unsignedInteger|integer|bigint|"
            r"BIGINT|INTEGER|NUMERIC|NUMBER|DECIMAL|decimal|numeric|Long|BigInteger)\b"
        ),
        requires_cnpj=True,
        languages=frozenset({".php", ".sql", ".rb", ".py", ".java", ".cs", ".ts", ".js"}),
    ),
    Rule(
        id="mascara-input-digitos",
        desc="Mascara de input que so' aceita digitos (00.000.000/0000-00) — bloqueia letras",
        severity=Severity.MEDIUM,
        pattern=_r(r"0{2}\.0{3}\.0{3}/0{4}-0{2}|9{2}\.9{3}\.9{3}/9{4}-9{2}"),
        requires_cnpj=False,
    ),
    Rule(
        id="cnpj-hardcoded-formatado",
        desc="CNPJ literal formatado no codigo — pode ser de terceiro/historico (nao mudar) ou proprio",
        severity=Severity.LOW,
        pattern=_r(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
        requires_cnpj=False,
    ),
    Rule(
        id="cnpj-hardcoded-bare",
        desc="Numero de 14 digitos proximo a 'cnpj' — possivel CNPJ literal so' numerico",
        severity=Severity.LOW,
        pattern=_r(r"(?<!\d)\d{14}(?!\d)"),
        requires_cnpj=True,
    ),
]


def rules_for(ext: str) -> list[Rule]:
    return [r for r in RULES if not r.languages or ext in r.languages]
