"""Testes da geracao de relatorio markdown/JSON (report.py)."""

import json

from cnpjscan.report import build_json, build_markdown


def test_markdown_vazio_tem_resumo():
    md = build_markdown([], "algum/caminho", used_llm=False)
    assert "# Relatorio" in md
    assert "somente regex" in md
    assert "**Total** | **0**" in md


def test_markdown_com_finding_mostra_veredito(finding_quebra):
    md = build_markdown([finding_quebra], "raiz", used_llm=True)
    assert "🔴 QUEBRA" in md
    assert "Claude (LLM)" in md
    assert finding_quebra.reason in md
    assert finding_quebra.candidate.file in md


def test_build_json_e_valido_e_serializa_enums(finding_quebra):
    data = json.loads(build_json([finding_quebra]))
    assert isinstance(data, list) and len(data) == 1
    item = data[0]
    assert item["verdict"] == "BREAKS"
    assert item["candidate"]["severity"] == "HIGH"
    assert item["confidence"] == "alta"
