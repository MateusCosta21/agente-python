"""Testes da classificacao no modo regex (sem LLM / sem rede)."""

from cnpjscan.classifier import classify
from cnpjscan.models import Verdict


def test_modo_regex_marca_tudo_como_revisar(candidato):
    findings = classify([candidato], use_llm=False)
    assert len(findings) == 1
    f = findings[0]
    assert f.verdict == Verdict.REVIEW
    assert f.confidence == "regex"
    assert f.candidate is candidato


def test_lista_vazia_retorna_vazio():
    assert classify([]) == []


def test_sem_api_key_cai_para_regex(candidato, monkeypatch):
    # mesmo pedindo LLM, sem chave nao ha' chamada de rede
    monkeypatch.delenv("CNPJSCAN_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    findings = classify([candidato], use_llm=True)
    assert findings[0].confidence == "regex"


def test_provider_deepseek_sem_chave_cai_para_regex(candidato, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    findings = classify([candidato], use_llm=True, provider="deepseek")
    assert findings[0].confidence == "regex"
