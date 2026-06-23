# Etapa 1 — Projeto Conceitual (Modelo ER/EER)

**Domínio:** Cartão de Pagamento do Governo Federal (CPGF)
**Fonte:** Portal da Transparência / CGU — https://portaldatransparencia.gov.br/download-de-dados/cpgf
**Dicionário de dados:** https://portaldatransparencia.gov.br/dicionario-de-dados/cpgf
**Notação adotada:** **ER clássica (Chen)** com extensão EER (especialização) — representada também em formato `erDiagram` (Mermaid) para legibilidade.

---

## 1.1 Visão geral do domínio

O CPGF é um cartão de crédito corporativo emitido em nome de uma **Unidade Gestora (UG)** da Administração Pública Federal e portado por um servidor autorizado (**Portador**). Cada **Transação** registra um pagamento feito a um **Favorecido** (estabelecimento PJ ou pessoa física PF), com data, valor e tipo (compra à vista em R$, saque, reversão etc.). UGs pertencem a **Órgãos Subordinados**, que por sua vez são supervisionados por **Órgãos Superiores** (ministérios).

A modelagem precisa capturar essa hierarquia administrativa (Órgão Superior → Subordinado → UG), o ato em si (Transação) e os papéis envolvidos (Portador, Favorecido, Tipo de Transação).

## 1.2 Entidades identificadas

Sete entidades — bem acima do mínimo de 4 exigido — capturando hierarquia organizacional, atores e o evento da transação:

1. **ORGAO_SUPERIOR** — Ministério ou órgão equivalente da Administração Direta.
2. **ORGAO_SUBORDINADO** — Entidade supervisionada por um Órgão Superior.
3. **UNIDADE_GESTORA** — Unidade orçamentária/administrativa em cujo nome o cartão é emitido.
4. **PORTADOR** — Servidor autorizado a portar o cartão.
5. **FAVORECIDO** — Recebedor do pagamento (entidade *generalizada*, com especialização EER em PF/PJ).
   - **PESSOA_FISICA** — favorecido identificado por CPF.
   - **PESSOA_JURIDICA** — favorecido identificado por CNPJ.
6. **TIPO_TRANSACAO** — Catálogo de naturezas de operação (ex.: `COMPRA A/V - R$ - APRES`, `SAQUE - R$ - APRES`).
7. **TRANSACAO** — Ato de pagamento; ponto de junção das demais entidades.

## 1.3 Atributos e chaves

| Entidade | Atributos | Chave |
|---|---|---|
| ORGAO_SUPERIOR | `codigo`, `nome` | PK: `codigo` |
| ORGAO_SUBORDINADO | `codigo`, `nome` | PK: `codigo` |
| UNIDADE_GESTORA | `codigo`, `nome` | PK: `codigo` |
| PORTADOR | `cpf` (anonimizado), `nome` | PK: `cpf` |
| FAVORECIDO | `cpf_cnpj`, `nome`, `tipo` (PF/PJ — discriminador) | PK: `cpf_cnpj` |
| PESSOA_FISICA | `cpf_cnpj` | PK/FK: `cpf_cnpj` → FAVORECIDO |
| PESSOA_JURIDICA | `cpf_cnpj` | PK/FK: `cpf_cnpj` → FAVORECIDO |
| TIPO_TRANSACAO | `codigo`, `descricao` | PK: `codigo` (gerado a partir da descrição) |
| TRANSACAO | `id`, `data`, `valor`, `ano_extrato`, `mes_extrato` | PK: `id` (surrogate) |

Observação: o CSV bruto **não** traz IDs surrogate para Transação nem para Tipo de Transação — eles são derivados no processo de carga (Etapa 3).

## 1.4 Relacionamentos e cardinalidades

| Relacionamento | Entidades | Cardinalidade | Participação |
|---|---|---|---|
| **SUPERVISIONA** | ORGAO_SUPERIOR — ORGAO_SUBORDINADO | 1 : N | Total dos dois lados (toda subordinada tem superior; um superior tem ≥1 subordinada nos dados) |
| **POSSUI** | ORGAO_SUBORDINADO — UNIDADE_GESTORA | 1 : N | Total dos dois lados |
| **REGISTRA** | UNIDADE_GESTORA — TRANSACAO | 1 : N | Parcial em UG (UG pode não ter transação no período), total em Transação |
| **REALIZA** | PORTADOR — TRANSACAO | 1 : N | Total em Transação |
| **RECEBE** | FAVORECIDO — TRANSACAO | 1 : N | Total em Transação |
| **CLASSIFICA** | TIPO_TRANSACAO — TRANSACAO | 1 : N | Total em Transação |
| **É-UM (EER)** | FAVORECIDO ▷ PESSOA_FISICA, PESSOA_JURIDICA | Especialização **total** e **disjunta** (todo favorecido é exatamente PF ou PJ) | — |

## 1.5 Restrições de integridade (do domínio)

- **R1.** `valor` da transação **≠ 0** (transações zero são erro de origem — descartadas na limpeza).
- **R2.** `valor` em geral é positivo; valores negativos só são aceitos quando o `TIPO_TRANSACAO` indica reversão/estorno (ex.: `VOUCHER - R$ - REVRS REAPR`).
- **R3.** `data_transacao` deve ser válida e estar dentro do intervalo `[ano_extrato-mes_extrato]` ± 90 dias (tolerância para fechamento de fatura).
- **R4.** `mes_extrato` ∈ {1..12}; `ano_extrato` ≥ 2003 (início histórico do CPGF) e ≤ ano corrente.
- **R5.** `cpf_portador` segue máscara anonimizada do Portal (`***.NNN.NNN-**`) — preservar como **string** (não converter para número).
- **R6.** `cpf_cnpj_favorecido`: 11 dígitos → PF; 14 dígitos → PJ; outros valores (sigilo, exterior, "Sem informação") tratados como `NULL` e/ou movidos para favorecido genérico.
- **R7.** Toda transação **deve** referenciar UG, Portador, Favorecido e Tipo de Transação existentes (integridade referencial).
- **R8.** Hierarquia: toda `UNIDADE_GESTORA` referencia um `ORGAO_SUBORDINADO`, que por sua vez referencia um `ORGAO_SUPERIOR`.
- **R9.** `tipo` em FAVORECIDO ∈ {`PF`, `PJ`} — usado como discriminador da especialização.

## 1.6 Decisões de modelagem

1. **Separar `TIPO_TRANSACAO`** em entidade própria, em vez de manter a descrição textual repetida em cada linha. Isso vira fundamental na 3FN (Etapa 2) e em consultas analíticas.
2. **Especialização EER em Favorecido** justificada porque PF e PJ têm semântica distinta (CPF vs CNPJ, capacidade jurídica, regras de sanções) — possibilita futuras extensões (cruzamento com Sanções/CEIS).
3. **Surrogate key em `TRANSACAO`**: o CSV não tem ID natural único (existem linhas duplicadas legítimas — mesmo portador comprando no mesmo dia o mesmo valor). Adotamos `id` `BIGSERIAL` para garantir unicidade.
4. **Manter `ano_extrato`/`mes_extrato` em TRANSACAO** (e não derivar só de `data_transacao`) porque o extrato pode incluir transações de mês anterior — fato relevante para a análise temporal.
5. **Hierarquia em 3 níveis** (Superior → Subordinado → UG) modelada como 3 entidades independentes para refletir 3 níveis hierárquicos reais — não foi colapsada porque cada nível tem suas próprias análises.

## 1.7 Diagrama ER (Mermaid)

```mermaid
erDiagram
    ORGAO_SUPERIOR ||--o{ ORGAO_SUBORDINADO : "supervisiona"
    ORGAO_SUBORDINADO ||--o{ UNIDADE_GESTORA : "possui"
    UNIDADE_GESTORA ||--o{ TRANSACAO : "registra"
    PORTADOR ||--o{ TRANSACAO : "realiza"
    FAVORECIDO ||--o{ TRANSACAO : "recebe"
    TIPO_TRANSACAO ||--o{ TRANSACAO : "classifica"
    FAVORECIDO ||--o| PESSOA_FISICA : "é-um (PF)"
    FAVORECIDO ||--o| PESSOA_JURIDICA : "é-um (PJ)"

    ORGAO_SUPERIOR {
        int    codigo PK
        string nome
    }
    ORGAO_SUBORDINADO {
        int    codigo PK
        string nome
        int    codigo_orgao_superior FK
    }
    UNIDADE_GESTORA {
        int    codigo PK
        string nome
        int    codigo_orgao_subordinado FK
    }
    PORTADOR {
        string cpf PK
        string nome
    }
    FAVORECIDO {
        string cpf_cnpj PK
        string nome
        string tipo "PF|PJ"
    }
    PESSOA_FISICA {
        string cpf_cnpj PK_FK
    }
    PESSOA_JURIDICA {
        string cpf_cnpj PK_FK
    }
    TIPO_TRANSACAO {
        int    codigo PK
        string descricao
    }
    TRANSACAO {
        bigint id PK
        date   data_transacao
        numeric valor
        int    ano_extrato
        int    mes_extrato
        int    codigo_ug FK
        string cpf_portador FK
        string cpf_cnpj_favorecido FK
        int    codigo_tipo_transacao FK
    }
```

> Este `.md` é compatível com renderização Mermaid no GitHub e em viewers Markdown modernos. Para o relatório final será gerada uma imagem PNG embutida.

---

## Entregável da Etapa 1 — Checklist
- [x] Diagrama ER/EER com 7 entidades (≥ 4 exigido)
- [x] Atributos com chaves identificados por entidade
- [x] Cardinalidades e participação descritas para todos os relacionamentos
- [x] Aplicação de EER (especialização disjunta total em FAVORECIDO)
- [x] 9 restrições de integridade documentadas
- [x] Notação declarada explicitamente (ER clássica + Mermaid `erDiagram`)
- [x] Texto descrevendo decisões de modelagem
