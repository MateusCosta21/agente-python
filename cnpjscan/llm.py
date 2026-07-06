"""Camada de provider de LLM.

Abstrai as diferencas entre a Claude (Anthropic) e a DeepSeek (API compativel
com a da OpenAI) atras de uma unica funcao — `complete_json` — que recebe um
system prompt, uma mensagem do usuario e um JSON Schema, e devolve o texto JSON
da resposta. O resto do projeto (classifier, fixer) nao precisa saber qual
provider esta' em uso.

O provider e' escolhido por `--provider`, pela variavel `CNPJSCAN_PROVIDER` ou,
por padrao, Anthropic. O modelo pode ser sobrescrito por `--model`/`CNPJSCAN_MODEL`.
Os SDKs (`anthropic`, `openai`) so' sao importados sob demanda, entao o modo
`--no-llm` (regex puro) nao exige nenhum deles instalado.
"""

from __future__ import annotations

import json
import os
from typing import Any

ANTHROPIC = "anthropic"
DEEPSEEK = "deepseek"

# Modelo padrao de cada provider. Para a DeepSeek usamos o `deepseek-chat`, que
# suporta oficialmente o "JSON mode"; o `deepseek-reasoner` pode ser escolhido
# via --model (melhor no raciocinio, porem o suporte a JSON mode varia).
DEFAULT_MODELS = {
    ANTHROPIC: "claude-opus-4-8",
    DEEPSEEK: "deepseek-chat",
}

# Variavel de ambiente com a chave de API de cada provider.
_API_KEY_ENV = {
    ANTHROPIC: "ANTHROPIC_API_KEY",
    DEEPSEEK: "DEEPSEEK_API_KEY",
}

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class LLMError(RuntimeError):
    """SDK do provider ausente ou provider mal configurado."""


def resolve_provider(explicit: str | None = None) -> str:
    """Resolve o provider a partir do argumento, do ambiente ou do padrao."""
    provider = (explicit or os.environ.get("CNPJSCAN_PROVIDER") or ANTHROPIC).lower()
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"provider desconhecido: {provider!r} (use 'anthropic' ou 'deepseek')")
    return provider


def api_key_env(provider: str) -> str:
    return _API_KEY_ENV[provider]


def api_key_present(provider: str) -> bool:
    return bool(os.environ.get(_API_KEY_ENV[provider]))


def default_model(provider: str) -> str:
    return os.environ.get("CNPJSCAN_MODEL") or DEFAULT_MODELS[provider]


def ensure_available(provider: str) -> None:
    """Levanta LLMError se o SDK necessario ao provider nao estiver instalado."""
    if provider == ANTHROPIC:
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:
            raise LLMError("pacote 'anthropic' nao instalado (pip install anthropic).") from exc
    elif provider == DEEPSEEK:
        try:
            import openai  # noqa: F401
        except ImportError as exc:
            raise LLMError(
                "pacote 'openai' nao instalado — necessario para o provider deepseek "
                "(pip install 'cnpj-alfa-scanner[deepseek]')."
            ) from exc
    else:
        raise ValueError(f"provider desconhecido: {provider!r}")


def loads_lenient(text: str) -> Any:
    """json.loads tolerante: remove cercas ```json e texto ao redor do objeto.

    A Claude com `output_config.format` ja' devolve JSON limpo; a DeepSeek em
    JSON mode tambem, mas modelos podem embrulhar a saida em cercas de codigo.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text[:4].lower() == "json":
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def augment_system_for_json(system: str, schema: dict[str, Any]) -> str:
    """Anexa o JSON Schema ao system prompt (usado pelos providers sem
    structured outputs nativo, como a DeepSeek em JSON mode)."""
    return (
        f"{system}\n\nResponda SOMENTE com um objeto JSON valido que satisfaca "
        f"este JSON Schema, sem nenhum texto fora do JSON:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )


def complete_json(
    *,
    provider: str,
    model: str,
    system: str,
    user: str,
    schema: dict[str, Any],
    effort: str,
    max_tokens: int,
) -> str:
    """Chama o modelo e devolve o texto JSON da resposta (nao faz o parse)."""
    if provider == ANTHROPIC:
        return _anthropic_json(model, system, user, schema, effort, max_tokens)
    if provider == DEEPSEEK:
        return _deepseek_json(model, system, user, schema, max_tokens)
    raise ValueError(f"provider desconhecido: {provider!r}")


def _anthropic_json(
    model: str, system: str, user: str, schema: dict[str, Any], effort: str, max_tokens: int
) -> str:
    from anthropic import Anthropic

    client = Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        },
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def _deepseek_json(
    model: str, system: str, user: str, schema: dict[str, Any], max_tokens: int
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get(_API_KEY_ENV[DEEPSEEK]), base_url=DEEPSEEK_BASE_URL)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": augment_system_for_json(system, schema)},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""
