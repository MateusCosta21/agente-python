"""Testes de fumaca da CLI (cli.py) — modo --no-llm, sem rede."""

from pathlib import Path

from cnpjscan.cli import _load_dotenv, main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_load_dotenv_define_variaveis(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CNPJSCAN_TESTVAR", raising=False)
    (tmp_path / ".env").write_text(
        "# comentario\nCNPJSCAN_TESTVAR=valor123\nSEM_IGUAL\n", encoding="utf-8"
    )
    _load_dotenv()
    import os

    assert os.environ.get("CNPJSCAN_TESTVAR") == "valor123"


def test_load_dotenv_nao_sobrescreve_existente(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CNPJSCAN_TESTVAR", "original")
    (tmp_path / ".env").write_text("CNPJSCAN_TESTVAR=novo\n", encoding="utf-8")
    _load_dotenv()
    import os

    assert os.environ.get("CNPJSCAN_TESTVAR") == "original"


def test_caminho_inexistente_retorna_codigo_2(tmp_path: Path):
    saida = tmp_path / "r.md"
    rc = main([str(tmp_path / "nao-existe"), "--no-llm", "-o", str(saida)])
    assert rc == 2


def test_run_no_llm_gera_relatorio(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # evita ler um .env real do repo
    saida = tmp_path / "relatorio.md"
    rc = main([str(EXAMPLES), "--no-llm", "-o", str(saida)])
    # sem LLM nada vira QUEBRA, entao o codigo de saida e' 0
    assert rc == 0
    assert saida.exists()
    conteudo = saida.read_text(encoding="utf-8")
    assert "# Relatorio" in conteudo
    # os exemplos tem pontos suspeitos, marcados como REVISAR no modo regex
    assert "🟡 REVISAR" in conteudo
