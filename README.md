# cnpj-alfa-scanner

Agente que varre um codebase inteiro procurando **suposições de que o CNPJ é só número** — as que quebram com o **CNPJ alfanumérico** (Instrução Normativa RFB 2.229/2024, em vigor a partir de **julho/2026**).

Não é um `find & replace`. É análise estática determinística **+** uma camada de IA (Claude) que entende o contexto de cada ocorrência e decide se ela realmente quebra — distinguindo código de produção de teste, dado histórico e CNPJ de terceiro — com justificativa e sugestão de correção.

## Por que isso importa

A partir de julho/2026, novos CNPJs passam a ter **letras (A–Z) nas 12 primeiras posições**; só os 2 dígitos verificadores continuam numéricos. A máscara `XX.XXX.XXX/XXXX-XX` e os 14 caracteres não mudam. E o pulo do gato: **CNPJs antigos continuam numéricos**, então todo sistema precisa aceitar os **dois formatos ao mesmo tempo**.

Ou seja: qualquer sistema brasileiro que valida, armazena ou mascara CNPJ tem, agora, uma superfície de bug real. Este agente encontra esses pontos.

### O que ele detecta

| Categoria | Exemplo que quebra |
|---|---|
| Regex numérica | `^\d{14}$`, `[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}` |
| Cast para inteiro | `intval($cnpj)`, `parseInt`, `(int)`, `Integer.parseLong` |
| Coluna de banco numérica | `unsignedBigInteger('cnpj')`, `BIGINT`, `NUMERIC` |
| Checagem "é dígito" | `ctype_digit`, `is_numeric`, `.isdigit()` |
| Máscara de input só de dígitos | `00.000.000/0000-00` |
| CNPJ literal hardcoded | pode ser de terceiro/histórico (**não** mudar) → marcado como REVISAR |

## Arquitetura (híbrida, de propósito)

```
  1. DESCOBERTA        2. CLASSIFICAÇÃO           3. RELATÓRIO
  (determinística)      (Claude / LLM)             (markdown/JSON)
  regex + AST     -->   BREAKS / SAFE / REVIEW  -->  agrupado por veredito
  sem token             + motivo + fix                (o print do post)
```

- **Passo 1 é regex puro** — rápido, sem alucinação, sem custo de token. Corta o volume.
- **Passo 2 usa a Claude** só nos candidatos que sobraram, em lotes, com *structured outputs* (JSON garantido).
- **Passo 3** é um relatório legível. Nada é alterado no seu código — o agente é read-only por design (human-in-the-loop).

## Instalação

```bash
cd cnpj-alfa-scanner
python3 -m pip install -e .          # instala o comando `cnpjscan` + a lib anthropic
cp .env.example .env                 # e coloque sua ANTHROPIC_API_KEY
```

## Uso

```bash
# Varredura completa com classificação por IA
cnpjscan /caminho/do/sistema -o relatorio.md

# Só a varredura determinística (sem IA, sem chave, ótimo para demo)
cnpjscan /caminho/do/sistema --no-llm

# Também exporta os achados em JSON (para pipeline/CI)
cnpjscan ./backend -o relatorio.md --json achados.json

# Modelo mais barato para codebases grandes
cnpjscan ./backend --model claude-haiku-4-5
```

Sem instalar, dá pra rodar direto do repo:

```bash
python3 -m cnpjscan examples --no-llm
```

O comando sai com **código 1** se encontrar algo que quebra (útil como *gate* em CI).

## Exemplo

O diretório `examples/` tem arquivos com problemas plantados (PHP, migration Laravel, componente Angular). Rode:

```bash
python3 -m cnpjscan examples --no-llm -o /tmp/relatorio.md
```

## Como funciona a classificação

O `--no-llm` marca tudo como **REVISAR** (é só o filtro determinístico). Com a chave da Claude configurada, cada candidato é classificado em:

- **🔴 QUEBRA** — assume CNPJ numérico e vai falhar/corromper com letras.
- **🟡 REVISAR** — ambíguo, precisa de decisão humana (o caso clássico: um CNPJ literal que pode ser de terceiro ou histórico e **não** deve ser tocado).
- **🟢 OK** — falso positivo, ou já trata string, ou é um número de 14 dígitos que não é CNPJ.

## Modelo usado

Por padrão usa `claude-opus-4-8`. Você pode trocar por `claude-sonnet-5` ou `claude-haiku-4-5` (mais baratos para varreduras grandes) via `--model` ou a variável `CNPJSCAN_MODEL`.

## Aviso

Ferramenta de **apoio à migração** — ela aponta e explica, não altera código. Toda mudança de CNPJ (especialmente em dados fiscais/históricos) deve passar por revisão humana.

---

Referência: [Instrução Normativa RFB nº 2.229/2024](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/cnpj/cnpj-alfanumerico) — CNPJ alfanumérico.
