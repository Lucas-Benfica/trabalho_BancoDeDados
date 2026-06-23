# TP Banco de Dados — CPGF

**Disciplina:** Banco de Dados — Prof. Pedro H. Barros (DCC/UFMG, 2026/1)
**Grupo:** Lucas Soares Benfica · Vinícius Cardoso Antunes · Pedro Soares Pinto
**Dataset:** [CPGF — Cartão de Pagamento do Governo Federal](https://portaldatransparencia.gov.br/download-de-dados/cpgf) (Portal da Transparência / CGU)
**SGBD:** PostgreSQL 14+ (com modo SQLite para validação rápida)
**Repositório:** https://github.com/Lucas-Benfica/trabalho_BancoDeDados

---

## Estrutura do projeto

```
trabalho/
├── README.md                       ← este arquivo
├── requirements.txt                ← dependências Python
├── data/
│   ├── raw/                        ← CSVs do Portal da Transparência (não versionado)
│   │   └── AMOSTRA_CPGF.csv        ← amostra sintética para validação rápida
│   └── processed/                  ← base materializada (.db SQLite ou dump pg)
├── docs/                           ← documentação e artefatos das etapas
│   ├── 01_modelo_conceitual.md
│   ├── 02_modelo_relacional.md
│   ├── 04_eda_discussao.md
│   ├── diagrama_er.png
│   ├── diagrama_relacional.png
│   └── graficos/                   ← PNGs das 5 perguntas analíticas
├── sql/
│   ├── 01_ddl.sql                  ← CREATE TABLE em PostgreSQL
│   ├── 02_carga_etl.sql            ← ETL do staging para o modelo normalizado
│   └── 03_consultas.sql            ← consultas da Etapa 4 (versão canônica PostgreSQL)
├── scripts/
│   ├── gerar_amostra_sintetica.py  ← gera CSV de validação com schema CPGF
│   ├── carregar_dados.py           ← pipeline ETL (PostgreSQL ou SQLite)
│   ├── gerar_diagramas.py          ← renderiza ER e Relacional via Graphviz
│   ├── rodar_eda.py                ← roda as 5 consultas e gera gráficos
│   ├── gerar_relatorio.py          ← monta o DOCX do relatório técnico
│   └── gerar_slides.py             ← monta o PPTX da apresentação
├── notebook/
│   └── analise_cpgf.ipynb          ← notebook reprodutível da Etapa 4
├── relatorio/
│   ├── Relatorio_TP_BD.docx
│   └── Relatorio_TP_BD.pdf         ← ENTREGÁVEL (c)
├── slides/
│   └── Apresentacao_TP_BD.pptx     ← ENTREGÁVEL (a)
└── video/
    └── roteiro_apresentacao.md     ← roteiro para a gravação 10-15 min
```

---

## Pré-requisitos

- Python 3.10+
- PostgreSQL 14+ (opcional — para o modo de produção; SQLite vem com Python)
- Bibliotecas Python — veja `requirements.txt`:

```bash
pip install -r requirements.txt
```

Para os diagramas é necessário o binário Graphviz instalado:

```bash
# Ubuntu/Debian
sudo apt-get install graphviz

# macOS (Homebrew)
brew install graphviz

# Windows
# https://graphviz.org/download/
```

---

## Como reproduzir do zero

### 1. Obter os dados

#### Opção A (recomendada) — usar a amostra sintética
```bash
python scripts/gerar_amostra_sintetica.py --out data/raw/AMOSTRA_CPGF.csv --linhas 10000
```
A amostra sintética **tem schema idêntico ao CPGF real** (mesmas 15 colunas, mesma ordem, mesmo encoding LATIN1, mesmo delimitador `;`). Serve para validar o pipeline em segundos.

#### Opção B — usar dados reais do Portal
1. Acesse https://portaldatransparencia.gov.br/download-de-dados/cpgf
2. Selecione um ou mais meses (ex.: jan/2024 a dez/2024)
3. Baixe os ZIPs e extraia os CSVs em `data/raw/`
4. Os arquivos vêm com nome `AAAAMM_CPGF.csv`

### 2. Carregar e popular a base

#### Modo SQLite (validação rápida — não exige servidor)
```bash
python scripts/carregar_dados.py \
    --csv data/raw/AMOSTRA_CPGF.csv \
    --sqlite data/processed/cpgf.db
```

#### Modo PostgreSQL (produção)
```bash
# 1) criar a base
createdb cpgf

# 2) rodar o pipeline
python scripts/carregar_dados.py \
    --csv data/raw/202404_CPGF.csv \
    --postgres "postgresql://usuario:senha@localhost:5432/cpgf"
```

> O script é idempotente: ele dropa as tabelas e recria do zero a cada execução. Para carregar múltiplos meses, basta concatenar os CSVs ou chamar uma vez e depois desativar o DROP no DDL.

### 3. Renderizar diagramas (ER + Relacional)
```bash
python scripts/gerar_diagramas.py
```
Saída: `docs/diagrama_er.png` e `docs/diagrama_relacional.png`.

### 4. Rodar as consultas analíticas + gráficos
```bash
python scripts/rodar_eda.py --sqlite data/processed/cpgf.db --out docs/graficos
```
Saída: 6 PNGs em `docs/graficos/` + CSVs com os resultados tabulares.

### 5. (Opcional) Regenerar o relatório PDF e os slides
```bash
python scripts/gerar_relatorio.py
libreoffice --headless --convert-to pdf relatorio/Relatorio_TP_BD.docx --outdir relatorio/

python scripts/gerar_slides.py
```

### 6. (Opcional) Abrir o notebook
```bash
jupyter notebook notebook/analise_cpgf.ipynb
```

---

## Cobertura dos requisitos do enunciado

| Requisito | Onde está | Como verificar |
|---|---|---|
| Modelo ER/EER com ≥ 4 entidades | `docs/01_modelo_conceitual.md`, `docs/diagrama_er.png` | 7 entidades + especialização EER em FAVORECIDO |
| Cardinalidades e restrições de integridade | `docs/01_modelo_conceitual.md` § 1.4 e § 1.5 | 9 restrições R1-R9 listadas |
| Notação declarada | `docs/01_modelo_conceitual.md` § cabeçalho | ER clássica + `erDiagram` Mermaid |
| Modelo relacional + chaves | `docs/02_modelo_relacional.md`, `sql/01_ddl.sql` | 9 relações, PK/FK explícitas |
| Normalização justificada (≥ 3FN) | `docs/02_modelo_relacional.md` § 2.4 | BCNF demonstrada |
| DDL em SQL | `sql/01_ddl.sql` | PostgreSQL 14+ |
| Carga reprodutível | `scripts/carregar_dados.py`, `sql/02_carga_etl.sql` | rodar conforme passo 2 |
| Limpeza documentada | `scripts/carregar_dados.py` (função `limpar`) | imprime contagem de descartes |
| SELECT/WHERE | `sql/03_consultas.sql` Q0 | sanity check |
| COUNT/SUM/AVG/MIN/MAX + COUNT DISTINCT | Q0, Q1, Q3, Q4 | múltiplas |
| GROUP BY + HAVING | Q3 | HAVING COUNT(...) >= 5 |
| JOIN entre tabelas | Q1, Q3, Q4, Q5 | JOIN multi-tabela |
| Consulta avançada (CTE / window) | Q5 | CTE + RANK() OVER (PARTITION BY ...) |
| 3 a 5 perguntas investigativas com gráfico | P1-P5 | 5 perguntas + bônus, 6 PNGs em docs/graficos/ |
| Discussão crítica | `docs/04_eda_discussao.md` | padrões, anomalias, limitações |
| Notebook ou scripts reprodutíveis | `notebook/analise_cpgf.ipynb`, `scripts/` | abre e executa |
| README com instruções | este arquivo | ✓ |
| Lista de dependências | `requirements.txt` | ✓ |
| Relatório PDF | `relatorio/Relatorio_TP_BD.pdf` | ✓ |
| Slides | `slides/Apresentacao_TP_BD.pptx` | ✓ |
| Declaração de uso de IA | Último slide do .pptx e anexo do relatório | ✓ |

### Bônus contemplados
- **Conexão com a LAI** — relatório § 6 e slide 14.
- **Detecção de anomalias** — `sql/03_consultas.sql` Q6 (transações > μ + 3σ).
- **Profundidade analítica** — window functions em Q5, discussão crítica detalhada em `docs/04_eda_discussao.md`.

---

## Notas sobre a amostra sintética

Por uma limitação temporária de acesso ao Portal da Transparência durante o desenvolvimento (proxy bloqueado), o pipeline foi validado ponta-a-ponta com uma **amostra sintética de 10 mil linhas** gerada por `scripts/gerar_amostra_sintetica.py`. Essa amostra:

- usa as **mesmas 15 colunas, na mesma ordem, com o mesmo formato** do CSV oficial do Portal;
- preserva encoding (LATIN1), delimitador (`;`), formato de data (DD/MM/YYYY) e separador decimal (vírgula);
- inclui hierarquia administrativa, portadores e favorecidos plausíveis;
- injeta propositalmente **linhas inválidas** (~1%) para validar a etapa de limpeza.

Para substituir pelos dados reais, basta colocar o CSV do Portal em `data/raw/` e apontar `--csv` para ele. O pipeline produz exatamente os mesmos artefatos.

---

## Licença

Trabalho acadêmico — DCC/UFMG.
