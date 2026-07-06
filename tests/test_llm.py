"""Testes da camada de provider de LLM (llm.py) — sem rede."""

import types

import pytest

from cnpjscan import llm


def test_resolve_provider_padrao_e_explicito(monkeypatch):
    monkeypatch.delenv("CNPJSCAN_PROVIDER", raising=False)
    assert llm.resolve_provider() == "anthropic"
    assert llm.resolve_provider("deepseek") == "deepseek"


def test_resolve_provider_por_ambiente(monkeypatch):
    monkeypatch.setenv("CNPJSCAN_PROVIDER", "deepseek")
    assert llm.resolve_provider() == "deepseek"


def test_resolve_provider_invalido():
    with pytest.raises(ValueError):
        llm.resolve_provider("gpt")


def test_default_model_por_provider(monkeypatch):
    monkeypatch.delenv("CNPJSCAN_MODEL", raising=False)
    assert llm.default_model("anthropic") == "claude-opus-4-8"
    assert llm.default_model("deepseek") == "deepseek-chat"


def test_default_model_respeita_override(monkeypatch):
    monkeypatch.setenv("CNPJSCAN_MODEL", "deepseek-reasoner")
    assert llm.default_model("deepseek") == "deepseek-reasoner"


def test_api_key_present_e_env(monkeypatch):
    assert llm.api_key_env("deepseek") == "DEEPSEEK_API_KEY"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert llm.api_key_present("deepseek") is False
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-x")
    assert llm.api_key_present("deepseek") is True


def test_loads_lenient_json_puro():
    assert llm.loads_lenient('{"a": 1}') == {"a": 1}


def test_loads_lenient_remove_cerca_de_codigo():
    texto = '```json\n{"a": 1, "b": [2, 3]}\n```'
    assert llm.loads_lenient(texto) == {"a": 1, "b": [2, 3]}


def test_loads_lenient_extrai_objeto_com_texto_ao_redor():
    texto = 'Aqui esta:\n{"ok": true}\nfim.'
    assert llm.loads_lenient(texto) == {"ok": True}


def test_augment_system_menciona_json_e_schema():
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    out = llm.augment_system_for_json("sistema base", schema)
    assert "sistema base" in out
    assert "json" in out.lower()
    assert '"type"' in out  # o schema foi serializado dentro


def test_complete_json_deepseek_usa_json_mode(monkeypatch):
    openai = pytest.importorskip("openai")
    capturado = {}

    class FakeCompletions:
        def create(self, **kwargs):
            capturado.update(kwargs)
            msg = types.SimpleNamespace(content='{"results": []}')
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class FakeOpenAI:
        def __init__(self, **kw):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake")

    texto = llm.complete_json(
        provider="deepseek",
        model="deepseek-chat",
        system="classifique",
        user="item 0",
        schema={"type": "object"},
        effort="low",
        max_tokens=128,
    )
    assert texto == '{"results": []}'
    # confirma que foi pedido JSON mode e que o schema entrou no system
    assert capturado["response_format"] == {"type": "json_object"}
    assert "json" in capturado["messages"][0]["content"].lower()
