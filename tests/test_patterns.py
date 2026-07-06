"""Testes das regras deterministicas (patterns.py)."""

from cnpjscan.patterns import RULES, rules_for


def _ids(rules):
    return {r.id for r in rules}


def test_regra_de_coluna_e_restrita_por_linguagem():
    # coluna-numerica so' se aplica a linguagens com schema/DDL, nao a .txt
    assert "coluna-numerica" in _ids(rules_for(".php"))
    assert "coluna-numerica" in _ids(rules_for(".sql"))
    assert "coluna-numerica" not in _ids(rules_for(".txt"))


def test_regras_sem_linguagem_valem_para_todas():
    todas = rules_for(".txt")
    # regras sem restricao de linguagem aparecem em qualquer extensao
    assert "regex-numerico" in _ids(todas)
    assert "cast-inteiro" in _ids(todas)


def test_ids_das_regras_sao_unicos():
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids))


def test_regex_numerica_casa_com_d14():
    regra = next(r for r in RULES if r.id == "regex-numerico")
    assert regra.pattern.search(r"preg_match('/^\d{14}$/', $cnpj)")
    assert regra.pattern.search(r"/^[0-9]{14}$/")
    assert not regra.pattern.search("apenas um texto qualquer")


def test_checagem_digito_casa_funcoes_conhecidas():
    regra = next(r for r in RULES if r.id == "checagem-digito")
    assert regra.pattern.search("if (!ctype_digit($clean)) {")
    assert regra.pattern.search("cnpj.isdigit()")


def test_coluna_numerica_casa_migration_e_sql_real():
    regra = next(r for r in RULES if r.id == "coluna-numerica")
    assert regra.pattern.search("$table->unsignedBigInteger('cnpj')")
    assert regra.pattern.search("$table->integer('cnpj')")
    assert regra.pattern.search("cnpj BIGINT NOT NULL")


def test_coluna_numerica_nao_casa_palavra_em_prosa():
    # falsos positivos que a versao antiga pegava: palavra inglesa em string/lista
    regra = next(r for r in RULES if r.id == "coluna-numerica")
    assert not regra.pattern.search('"message" => "Maximun Call Must Be Integer"')
    assert not regra.pattern.search('["name", "cnpj", "email", "number", "status"]')
    # tipo string (correto) tambem nao deve casar
    assert not regra.pattern.search("$table->string('cnpj', 14)")
