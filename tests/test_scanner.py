"""Testes da varredura deterministica (scanner.py)."""

from pathlib import Path

from cnpjscan.scanner import _ext_of, scan_file, scan_path

PHP_COM_PROBLEMAS = """\
<?php
class FornecedorValidator
{
    public function isValid(string $cnpj): bool
    {
        return preg_match('/^\\d{14}$/', $cnpj) === 1;
    }

    public function toKey(string $cnpj): int
    {
        return intval(preg_replace('/\\D/', '', $cnpj));
    }
}
"""


def test_scan_file_detecta_candidatos(tmp_path: Path):
    f = tmp_path / "validator.php"
    f.write_text(PHP_COM_PROBLEMAS, encoding="utf-8")

    candidatos = scan_file(f)
    ids = {c.rule_id for c in candidatos}

    assert "regex-numerico" in ids
    assert "cast-inteiro" in ids
    # todos apontam para o arquivo certo e uma linha valida
    assert all(c.file == str(f) for c in candidatos)
    assert all(c.line >= 1 for c in candidatos)


def test_ext_of_reconhece_blade():
    assert _ext_of(Path("view.blade.php")) == ".blade.php"
    assert _ext_of(Path("app.py")) == ".py"


def test_scan_path_ignora_extensao_desconhecida(tmp_path: Path):
    # a filtragem por extensao acontece no walk do scan_path (nao no scan_file)
    (tmp_path / "leiame.txt").write_text("cnpj \\d{14}", encoding="utf-8")
    (tmp_path / "app.php").write_text(PHP_COM_PROBLEMAS, encoding="utf-8")

    arquivos = {c.file for c in scan_path(str(tmp_path))}
    assert str(tmp_path / "app.php") in arquivos
    assert str(tmp_path / "leiame.txt") not in arquivos


def test_scan_path_pula_diretorios_ignorados(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.php").write_text(PHP_COM_PROBLEMAS, encoding="utf-8")
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "b.php").write_text(PHP_COM_PROBLEMAS, encoding="utf-8")

    candidatos = scan_path(str(tmp_path))
    arquivos = {c.file for c in candidatos}

    assert str(tmp_path / "src" / "a.php") in arquivos
    # nada dentro de vendor/ deve ser varrido
    assert not any("vendor" in a for a in arquivos)


def test_scan_file_nao_duplica_mesma_regra_na_linha(tmp_path: Path):
    f = tmp_path / "dup.php"
    f.write_text("// cnpj\n$x = intval($cnpj); $y = intval($cnpj);\n", encoding="utf-8")
    candidatos = [c for c in scan_file(f) if c.rule_id == "cast-inteiro"]
    # a mesma (arquivo, linha, regra) so' aparece uma vez
    assert len(candidatos) == 1
