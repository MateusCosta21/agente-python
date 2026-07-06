"""Fixtures compartilhadas pelos testes."""

import pytest

from cnpjscan.models import Candidate, Finding, Severity, Verdict


@pytest.fixture
def candidato() -> Candidate:
    return Candidate(
        file="app.php",
        line=10,
        rule_id="cast-inteiro",
        rule_desc="Converte CNPJ para inteiro",
        severity=Severity.HIGH,
        language=".php",
        matched_text="return intval($cnpj);",
        context=">>    10| return intval($cnpj);",
    )


@pytest.fixture
def finding_quebra(candidato: Candidate) -> Finding:
    return Finding(
        candidate=candidato,
        verdict=Verdict.BREAKS,
        reason="Cast para inteiro corrompe CNPJ alfanumerico.",
        suggested_fix="Tratar como string.",
        confidence="alta",
    )
