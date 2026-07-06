# Relatorio — CNPJ Alfanumerico

- **Alvo varrido:** `/home/mateuscosta/modernization-base/backend`
- **Data:** 2026-07-06 19:58
- **Classificacao:** Claude (LLM)
- **Referencia:** IN RFB 2.229/2024 — CNPJ alfanumerico a partir de julho/2026

## Resumo

| Veredito | Qtd |
|---|---:|
| 🔴 QUEBRA | 0 |
| 🟡 REVISAR | 5 |
| 🟢 OK | 5 |
| **Total** | **10** |

## 🟡 REVISAR (5)

### `/home/mateuscosta/modernization-base/backend/app/Modules/Grants/Application/Services/GrantContractPdfGenerator.php:95` — LOW · `cnpj-hardcoded-formatado`

**Por que:** Mesmo CNPJ do item 0, literal repetido; mesma decisão se aplica.

**Sugestao:** Idem item 0.

```
      92|             'logoDataUri' => $this->imageDataUri(resource_path('images/brand-symbol.jpg')),
      93|             'foundation' => [
      94|                 'name' => 'Fundação Beto Studart de Incentivo ao Talento',
>>    95|                 'cnpj' => '06.288.466/0001-26',
      96|                 'address' => 'Rua Marcos Macedo, 1.333 - Torre II, Sala 1810, Meireles - Fortaleza - CE, CEP: 60.150-190',
      97|                 'representative' => 'Ana Maria Nogueira Studart Gomes',
      98|                 'representativeDocument' => 'Carteira de Identidade nº 326.303 SSP-CE de 10.09.81 e CPF nº 134.242.973-72',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/app/Modules/Grants/Application/Services/GrantContractPdfGenerator.php:181` — LOW · `cnpj-hardcoded-formatado`

**Por que:** Outro CNPJ (06.288.466/0001-10) da mesma fundação; verificar se é válido ou erro de digitação (DV diferente). Deve ser analisado se precisa ser atualizado.

**Sugestao:** Confirmar CNPJ correto com área responsável; se for terceiro, manter como string.

```
     178|             'logoDataUri' => $this->imageDataUri(resource_path('images/brand-symbol.jpg')),
     179|             'foundation' => [
     180|                 'name' => 'Fundação Beto Studart de Incentivo ao Talento',
>>   181|                 'cnpj' => '06.288.466/0001-10',
     182|                 'address' => 'Rua Marcos Macedo, 1.333 - Torre II, Sala 1810, Meireles - Fortaleza - CE, CEP: 60.150-190',
     183|                 'representative' => 'Ana Maria Nogueira Studart Gomes',
     184|                 'representativeDocument' => 'CPF sob o nº 134.242.973-72',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/app/Modules/Support/Application/Services/ExtraRequestContractPdfGenerator.php:121` — LOW · `cnpj-hardcoded-formatado`

**Por que:** CNPJ da Fundação Beto Studart, terceiro; é literal numérico, mas pode ser fixo por contrato/legislação; verificar se precisa aceitar alfanumérico.

**Sugestao:** Se necessário armazenar como string, manter literal; caso seja usado para validação, atualizar para aceitar formato alfanumérico.

```
     118|             'logoDataUri' => $this->imageDataUri(resource_path('images/brand-symbol.jpg')),
     119|             'foundation' => [
     120|                 'name' => 'Fundação Beto Studart de Incentivo ao Talento',
>>   121|                 'cnpj' => '06.288.466/0001-26',
     122|                 'address' => 'Rua Marcos Macedo, 1.333 - Torre II, Sala 1810, Meireles - Fortaleza - CE, CEP: 60.150-190',
     123|                 'representative' => 'Ana Maria Nogueira Studart Gomes',
     124|                 'representativeDocument' => 'Carteira de Identidade nº 326.303 SSP-CE de 10.09.81 e CPF nº 134.242.973-72',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/tests/Feature/Modules/Grants/GrantAdditiveTest.php:332` — LOW · `cnpj-hardcoded-formatado`

**Por que:** CNPJ literal hardcoded em teste: pode ser de terceiro (não alterar) ou da própria empresa (precisa ser atualizado?); o valor '12.345.678/0001-90' é numérico e não quebra com alfanumérico, mas o código de validação do sistema pode não aceitar letras.

**Sugestao:** Avaliar se o CNPJ '12.345.678/0001-90' é da própria empresa (precisa ser atualizado para um exemplo alfanumérico?) ou de terceiro (manter). Em testes, considere usar um CNPJ alfanumérico válido, ex.: '12.ABC.345/0001-90' (se aplicável à lógica de teste).

```
     329|         $project = Project::create([
     330|             'users_id' => $projectUser->id,
     331|             'nome_instituicao' => 'Instituto Projeto Teste',
>>   332|             'cnpj' => '12.345.678/0001-90',
     333|             'email' => 'instituto@teste.local',
     334|             'telefone_ong' => '(85) 99999-1111',
     335|             'endereco' => 'Rua do Projeto',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/tests/Feature/Modules/Grants/GrantAdditiveTest.php:393` — LOW · `cnpj-hardcoded-formatado`

**Por que:** Mesmo CNPJ literal hardcoded que no item 0, em outro teste; mesma análise se aplica.

**Sugestao:** Mesmo que item 0: revisar se o CNPJ deve ser alterado para refletir formato alfanumérico ou se permanece como dado de terceiro.

```
     390|         $project = Project::create([
     391|             'users_id' => $projectUser->id,
     392|             'nome_instituicao' => 'Instituto Patrocinio Teste',
>>   393|             'cnpj' => '12.345.678/0001-90',
     394|             'email' => 'patrocinio@teste.local',
     395|             'telefone_ong' => '(85) 99999-1111',
     396|             'endereco' => 'Rua do Patrocinio',
```
_confianca: alta_

## 🟢 OK (5)

### `/home/mateuscosta/modernization-base/backend/database/seeders/TestScenariosSeeder.php:330` — LOW · `cnpj-hardcoded-bare`

**Por que:** Seed de teste, CNPJ fictício '12345678000100' (provavelmente inválido); não afeta produção. Pode usar qualquer string, mas não quebra com alfanumérico.

**Sugestao:** Nenhuma, a menos que se deseje testar CNPJ alfanumérico.

```
     327|             'name' => 'Associação Viver Esporte e Cultura',
     328|         ], [
     329|             'nome_instituicao' => 'Associação Viver Esporte e Cultura',
>>   330|             'cnpj' => '12345678000100', 'data_fundacao' => '15/03/2010',
     331|             'email' => 'projeto-p1@viveresporte.org.br', 'telefone_ong' => '(11) 3456-7890',
     332|             'cep' => '04001000', 'endereco' => 'Av. Paulista', 'numero' => '1500', 'complemento' => 'Sala 201',
     333|             'bairro' => 'Bela Vista', 'cidade' => 'São Paulo', 'estado' => 'SP',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/database/seeders/TestScenariosSeeder.php:369` — LOW · `cnpj-hardcoded-bare`

**Por que:** Seed de teste, CNPJ fictício '98765432000111'; mesmo cenário.

**Sugestao:** Nenhuma.

```
     366|         $this->project('projeto-p2@educar.org.br', [
     367|             'name' => 'Instituto Educar',
     368|         ], [
>>   369|             'nome_instituicao' => 'Instituto Educar', 'cnpj' => '98765432000111', 'data_fundacao' => '20/06/2015',
     370|             'email' => 'projeto-p2@educar.org.br', 'telefone_ong' => '(21) 2222-3333',
     371|             'cep' => '20040020', 'endereco' => 'Rua Buenos Aires', 'numero' => '50',
     372|             'bairro' => 'Centro', 'cidade' => 'Rio de Janeiro', 'estado' => 'RJ',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/database/seeders/TestScenariosSeeder.php:406` — LOW · `cnpj-hardcoded-bare`

**Por que:** Seed de teste, CNPJ fictício '11223344000155'; mesmo cenário.

**Sugestao:** Nenhuma.

```
     403|         $this->project('projeto-p3@arteviva.org.br', [
     404|             'name' => 'Instituto Arte Viva',
     405|         ], [
>>   406|             'nome_instituicao' => 'Instituto Arte Viva', 'cnpj' => '11223344000155', 'data_fundacao' => '10/09/2008',
     407|             'email' => 'projeto-p3@arteviva.org.br', 'telefone_ong' => '(31) 3333-4444',
     408|             'cep' => '30130100', 'endereco' => 'Av. do Contorno', 'numero' => '800', 'complemento' => 'Bloco B',
     409|             'bairro' => 'Floresta', 'cidade' => 'Belo Horizonte', 'estado' => 'MG',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/database/seeders/TestScenariosSeeder.php:443` — LOW · `cnpj-hardcoded-bare`

**Por que:** Seed de teste, CNPJ fictício '55443322000177'; mesmo cenário.

**Sugestao:** Nenhuma.

```
     440|         $this->project('projeto-p4@saudevida.org.br', [
     441|             'name' => 'Ação Comunitária Saúde e Vida',
     442|         ], [
>>   443|             'nome_instituicao' => 'Ação Comunitária Saúde e Vida', 'cnpj' => '55443322000177', 'data_fundacao' => '01/01/2005',
     444|             'email' => 'projeto-p4@saudevida.org.br', 'telefone_ong' => '(83) 3211-0000',
     445|             'cep' => '58000100', 'endereco' => 'R. João Pessoa', 'numero' => '300',
     446|             'bairro' => 'Centro', 'cidade' => 'João Pessoa', 'estado' => 'PB',
```
_confianca: alta_

### `/home/mateuscosta/modernization-base/backend/database/seeders/TestScenariosSeeder.php:479` — LOW · `cnpj-hardcoded-bare`

**Por que:** Seed de teste, CNPJ fictício '44332211000199'; mesmo cenário.

**Sugestao:** Nenhuma.

```
     476|             'name' => 'Ecofuturo — Instituto para o Desenvolvimento Sustentável',
     477|         ], [
     478|             'nome_instituicao' => 'Ecofuturo — Instituto para o Desenvolvimento Sustentável',
>>   479|             'cnpj' => '44332211000199', 'data_fundacao' => '22/04/2012',
     480|             'email' => 'projeto-p5@ecofuturo.org.br', 'telefone_ong' => '(48) 3222-1111',
     481|             'cep' => '88000200', 'endereco' => 'Av. Beira-Mar Norte', 'numero' => '3300',
     482|             'bairro' => 'Agronômica', 'cidade' => 'Florianópolis', 'estado' => 'SC',
```
_confianca: alta_
