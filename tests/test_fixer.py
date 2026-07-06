"""Testes da aplicacao de correcoes e geracao de patch (fixer.py)."""

from pathlib import Path

from cnpjscan.fixer import Fix, _windows_for_file, apply_fix_to_text, unified_patch


def test_apply_fix_preserva_linhas_e_newline_final():
    src = "a\nb\nc\nd\n"
    fix = Fix("f.py", start_line=2, end_line=3, original="b\nc", fixed="B\nC", note="")
    out = apply_fix_to_text(src, [fix])
    assert out == "a\nB\nC\nd\n"


def test_apply_fix_de_baixo_para_cima_nao_desloca():
    src = "1\n2\n3\n4\n5\n"
    # fix1 expande a linha 1 em duas; fix2 mexe na linha 4.
    # aplicados de baixo p/ cima, o fix2 nao pode ser afetado pelo fix1.
    fix1 = Fix("f", 1, 1, "1", "1a\n1b", "")
    fix2 = Fix("f", 4, 4, "4", "QUATRO", "")
    out = apply_fix_to_text(src, [fix1, fix2])
    assert out == "1a\n1b\n2\n3\nQUATRO\n5\n"


def test_apply_fix_sem_newline_final():
    src = "x\ny"
    fix = Fix("f", 1, 1, "x", "X", "")
    assert apply_fix_to_text(src, [fix]) == "X\ny"


def test_windows_funde_janelas_proximas():
    linhas = [str(i) for i in range(1, 31)]
    # duas linhas proximas devem gerar uma janela unica (raio 5, gap 3)
    janelas = _windows_for_file(linhas, [10, 12])
    assert len(janelas) == 1
    # duas linhas distantes geram janelas separadas
    janelas2 = _windows_for_file(linhas, [3, 28])
    assert len(janelas2) == 2


def test_unified_patch_gera_diff(tmp_path: Path, monkeypatch):
    arquivo = tmp_path / "codigo.php"
    arquivo.write_text("linha um\nlinha dois\nlinha tres\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    fix = Fix(str(arquivo), 2, 2, "linha dois", "linha DOIS", "ajuste")
    patch = unified_patch([fix])

    assert "linha dois" in patch
    assert "linha DOIS" in patch
    assert patch.startswith("---") or "@@" in patch


def test_unified_patch_ignora_fix_sem_mudanca(tmp_path: Path):
    arquivo = tmp_path / "codigo.php"
    arquivo.write_text("a\nb\n", encoding="utf-8")
    fix = Fix(str(arquivo), 1, 1, "a", "a", "sem mudanca")
    assert unified_patch([fix]) == ""
