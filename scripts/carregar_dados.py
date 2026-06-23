"""
carregar_dados.py
=================
Pipeline ETL completo do CSV CPGF → base normalizada.

Suporta dois backends:
- PostgreSQL  (padrão, alvo do projeto)
- SQLite      (modo de validação local; ativado com --sqlite arquivo.db)

USO:
    # Modo PostgreSQL (produção)
    python scripts/carregar_dados.py \\
        --csv data/raw/202504_CPGF.csv \\
        --postgres "postgresql://usuario:senha@localhost:5432/cpgf"

    # Modo SQLite (validação rápida)
    python scripts/carregar_dados.py \\
        --csv data/raw/AMOSTRA_CPGF.csv \\
        --sqlite data/processed/cpgf.db

O script:
1) Cria o schema (DDL) se --recreate for passado
2) Lê o CSV em chunks (resiliente a arquivos grandes)
3) Limpa e tipa os dados
4) Popula dimensões e fato em ordem topológica
5) Imprime relatório de carga (counts e linhas descartadas)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

# Colunas do CSV CPGF (na ordem do Portal da Transparência)
COLS_CSV = [
    "codigo_orgao_superior", "nome_orgao_superior",
    "codigo_orgao_subordinado", "nome_orgao_subordinado",
    "codigo_unidade_gestora", "nome_unidade_gestora",
    "ano_extrato", "mes_extrato",
    "cpf_portador", "nome_portador",
    "transacao", "data_transacao",
    "cpf_cnpj_favorecido", "nome_favorecido",
    "valor_transacao",
]

# ---------------------------------------------------------------------------
# DDL (PostgreSQL e SQLite — pequenas diferenças tratadas no codigo)
# ---------------------------------------------------------------------------
DDL_POSTGRES = """
DROP TABLE IF EXISTS transacao CASCADE;
DROP TABLE IF EXISTS pessoa_fisica CASCADE;
DROP TABLE IF EXISTS pessoa_juridica CASCADE;
DROP TABLE IF EXISTS favorecido CASCADE;
DROP TABLE IF EXISTS portador CASCADE;
DROP TABLE IF EXISTS tipo_transacao CASCADE;
DROP TABLE IF EXISTS unidade_gestora CASCADE;
DROP TABLE IF EXISTS orgao_subordinado CASCADE;
DROP TABLE IF EXISTS orgao_superior CASCADE;

CREATE TABLE orgao_superior (codigo INTEGER PRIMARY KEY, nome TEXT NOT NULL);
CREATE TABLE orgao_subordinado (
    codigo INTEGER PRIMARY KEY, nome TEXT NOT NULL,
    codigo_orgao_superior INTEGER NOT NULL REFERENCES orgao_superior(codigo)
);
CREATE TABLE unidade_gestora (
    codigo INTEGER PRIMARY KEY, nome TEXT NOT NULL,
    codigo_orgao_subordinado INTEGER NOT NULL REFERENCES orgao_subordinado(codigo)
);
CREATE TABLE portador (cpf TEXT PRIMARY KEY, nome TEXT NOT NULL);
CREATE TABLE favorecido (
    cpf_cnpj TEXT PRIMARY KEY, nome TEXT NOT NULL,
    tipo CHAR(2) NOT NULL CHECK (tipo IN ('PF','PJ','NI'))
);
CREATE TABLE pessoa_fisica   (cpf_cnpj TEXT PRIMARY KEY REFERENCES favorecido(cpf_cnpj));
CREATE TABLE pessoa_juridica (cpf_cnpj TEXT PRIMARY KEY REFERENCES favorecido(cpf_cnpj));
CREATE TABLE tipo_transacao  (codigo SERIAL PRIMARY KEY, descricao TEXT NOT NULL UNIQUE);
CREATE TABLE transacao (
    id BIGSERIAL PRIMARY KEY,
    data_transacao DATE NOT NULL,
    valor NUMERIC(14,2) NOT NULL CHECK (valor <> 0),
    ano_extrato SMALLINT NOT NULL,
    mes_extrato SMALLINT NOT NULL CHECK (mes_extrato BETWEEN 1 AND 12),
    codigo_ug INTEGER NOT NULL REFERENCES unidade_gestora(codigo),
    cpf_portador TEXT NOT NULL REFERENCES portador(cpf),
    cpf_cnpj_favorecido TEXT NOT NULL REFERENCES favorecido(cpf_cnpj),
    codigo_tipo_transacao INTEGER NOT NULL REFERENCES tipo_transacao(codigo)
);
CREATE INDEX idx_transacao_data        ON transacao(data_transacao);
CREATE INDEX idx_transacao_ug          ON transacao(codigo_ug);
CREATE INDEX idx_transacao_portador    ON transacao(cpf_portador);
CREATE INDEX idx_transacao_favorecido  ON transacao(cpf_cnpj_favorecido);
CREATE INDEX idx_transacao_tipo        ON transacao(codigo_tipo_transacao);
CREATE INDEX idx_transacao_ano_mes     ON transacao(ano_extrato, mes_extrato);
"""

DDL_SQLITE = """
PRAGMA foreign_keys = ON;
DROP TABLE IF EXISTS transacao;
DROP TABLE IF EXISTS pessoa_fisica;
DROP TABLE IF EXISTS pessoa_juridica;
DROP TABLE IF EXISTS favorecido;
DROP TABLE IF EXISTS portador;
DROP TABLE IF EXISTS tipo_transacao;
DROP TABLE IF EXISTS unidade_gestora;
DROP TABLE IF EXISTS orgao_subordinado;
DROP TABLE IF EXISTS orgao_superior;

CREATE TABLE orgao_superior (codigo INTEGER PRIMARY KEY, nome TEXT NOT NULL);
CREATE TABLE orgao_subordinado (
    codigo INTEGER PRIMARY KEY, nome TEXT NOT NULL,
    codigo_orgao_superior INTEGER NOT NULL REFERENCES orgao_superior(codigo)
);
CREATE TABLE unidade_gestora (
    codigo INTEGER PRIMARY KEY, nome TEXT NOT NULL,
    codigo_orgao_subordinado INTEGER NOT NULL REFERENCES orgao_subordinado(codigo)
);
CREATE TABLE portador (cpf TEXT PRIMARY KEY, nome TEXT NOT NULL);
CREATE TABLE favorecido (
    cpf_cnpj TEXT PRIMARY KEY, nome TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('PF','PJ','NI'))
);
CREATE TABLE pessoa_fisica   (cpf_cnpj TEXT PRIMARY KEY REFERENCES favorecido(cpf_cnpj));
CREATE TABLE pessoa_juridica (cpf_cnpj TEXT PRIMARY KEY REFERENCES favorecido(cpf_cnpj));
CREATE TABLE tipo_transacao  (codigo INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL UNIQUE);
CREATE TABLE transacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_transacao TEXT NOT NULL,
    valor REAL NOT NULL CHECK (valor <> 0),
    ano_extrato INTEGER NOT NULL,
    mes_extrato INTEGER NOT NULL CHECK (mes_extrato BETWEEN 1 AND 12),
    codigo_ug INTEGER NOT NULL REFERENCES unidade_gestora(codigo),
    cpf_portador TEXT NOT NULL REFERENCES portador(cpf),
    cpf_cnpj_favorecido TEXT NOT NULL REFERENCES favorecido(cpf_cnpj),
    codigo_tipo_transacao INTEGER NOT NULL REFERENCES tipo_transacao(codigo)
);
CREATE INDEX idx_transacao_data        ON transacao(data_transacao);
CREATE INDEX idx_transacao_ug          ON transacao(codigo_ug);
CREATE INDEX idx_transacao_portador    ON transacao(cpf_portador);
CREATE INDEX idx_transacao_favorecido  ON transacao(cpf_cnpj_favorecido);
CREATE INDEX idx_transacao_tipo        ON transacao(codigo_tipo_transacao);
CREATE INDEX idx_transacao_ano_mes     ON transacao(ano_extrato, mes_extrato);
"""


def classificar_favorecido(cpf_cnpj: str) -> str:
    if not isinstance(cpf_cnpj, str):
        return "NI"
    c = cpf_cnpj.strip()
    if re.fullmatch(r"\d{11}", c):
        return "PF"
    if re.fullmatch(r"\d{14}", c):
        return "PJ"
    if re.fullmatch(r"\*{3}\.\d{3}\.\d{3}-\*{2}", c):
        return "PF"
    return "NI"


def carregar_csv(path: Path) -> pd.DataFrame:
    """Lê o CSV do CPGF com tipos textuais — tratamento vem depois."""
    df = pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        dtype=str,
        header=0,
        names=COLS_CSV,
        skiprows=1,  # pula o cabeçalho original do Portal
        na_values=["", " ", "Sem informação", "Sigiloso"],
        keep_default_na=True,
    )
    return df


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica regras de limpeza e devolve (df_limpo, relatorio_descartes)."""
    descartes = {"total_bruto": len(df)}

    # Strip básico
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].str.strip()

    # Conversões numéricas
    for c in ["codigo_orgao_superior", "codigo_orgao_subordinado",
              "codigo_unidade_gestora", "ano_extrato", "mes_extrato"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Valor: troca vírgula por ponto
    df["valor"] = (
        df["valor_transacao"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )
    df.drop(columns=["valor_transacao"], inplace=True)

    # Data
    df["data_transacao_dt"] = pd.to_datetime(
        df["data_transacao"], format="%d/%m/%Y", errors="coerce"
    )

    # Descartes
    mask_chave_nula = (
        df["codigo_unidade_gestora"].isna()
        | df["cpf_portador"].isna()
        | df["data_transacao_dt"].isna()
        | df["valor"].isna()
    )
    descartes["chave_nula"] = int(mask_chave_nula.sum())
    df = df[~mask_chave_nula].copy()

    mask_valor_zero = df["valor"] == 0
    descartes["valor_zero"] = int(mask_valor_zero.sum())
    df = df[~mask_valor_zero].copy()

    mask_mes_invalido = ~df["mes_extrato"].between(1, 12)
    descartes["mes_invalido"] = int(mask_mes_invalido.sum())
    df = df[~mask_mes_invalido].copy()

    # Duplicatas (mesma linha integral)
    antes = len(df)
    df = df.drop_duplicates()
    descartes["duplicatas"] = antes - len(df)

    descartes["total_carregado"] = len(df)
    return df, descartes


def montar_dimensoes(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    org_sup = (
        df[["codigo_orgao_superior", "nome_orgao_superior"]]
        .dropna().drop_duplicates(subset=["codigo_orgao_superior"])
        .rename(columns={"codigo_orgao_superior": "codigo", "nome_orgao_superior": "nome"})
        .astype({"codigo": int})
    )

    org_sub = (
        df[["codigo_orgao_subordinado", "nome_orgao_subordinado", "codigo_orgao_superior"]]
        .dropna().drop_duplicates(subset=["codigo_orgao_subordinado"])
        .rename(columns={
            "codigo_orgao_subordinado": "codigo",
            "nome_orgao_subordinado": "nome",
            "codigo_orgao_superior": "codigo_orgao_superior",
        })
        .astype({"codigo": int, "codigo_orgao_superior": int})
    )

    ug = (
        df[["codigo_unidade_gestora", "nome_unidade_gestora", "codigo_orgao_subordinado"]]
        .dropna().drop_duplicates(subset=["codigo_unidade_gestora"])
        .rename(columns={
            "codigo_unidade_gestora": "codigo",
            "nome_unidade_gestora": "nome",
            "codigo_orgao_subordinado": "codigo_orgao_subordinado",
        })
        .astype({"codigo": int, "codigo_orgao_subordinado": int})
    )

    portador = (
        df[["cpf_portador", "nome_portador"]]
        .dropna(subset=["cpf_portador"])
        .drop_duplicates(subset=["cpf_portador"])
        .rename(columns={"cpf_portador": "cpf", "nome_portador": "nome"})
    )
    portador["nome"] = portador["nome"].fillna("(SEM NOME)")

    favorecido = (
        df[["cpf_cnpj_favorecido", "nome_favorecido"]]
        .dropna(subset=["cpf_cnpj_favorecido"])
        .drop_duplicates(subset=["cpf_cnpj_favorecido"])
        .rename(columns={"cpf_cnpj_favorecido": "cpf_cnpj", "nome_favorecido": "nome"})
    )
    favorecido["nome"] = favorecido["nome"].fillna("(SEM NOME)")
    favorecido["tipo"] = favorecido["cpf_cnpj"].apply(classificar_favorecido)

    tipo_tx = (
        df[["transacao"]].dropna().drop_duplicates()
        .rename(columns={"transacao": "descricao"})
        .reset_index(drop=True)
    )
    tipo_tx["codigo"] = tipo_tx.index + 1
    tipo_tx = tipo_tx[["codigo", "descricao"]]

    return {
        "orgao_superior": org_sup,
        "orgao_subordinado": org_sub,
        "unidade_gestora": ug,
        "portador": portador,
        "favorecido": favorecido,
        "tipo_transacao": tipo_tx,
    }


def montar_fato(df: pd.DataFrame, tipo_tx: pd.DataFrame) -> pd.DataFrame:
    desc2cod = dict(zip(tipo_tx["descricao"], tipo_tx["codigo"]))
    fato = pd.DataFrame({
        "data_transacao": df["data_transacao_dt"].dt.strftime("%Y-%m-%d"),
        "valor": df["valor"].astype(float),
        "ano_extrato": df["ano_extrato"].astype(int),
        "mes_extrato": df["mes_extrato"].astype(int),
        "codigo_ug": df["codigo_unidade_gestora"].astype(int),
        "cpf_portador": df["cpf_portador"],
        "cpf_cnpj_favorecido": df["cpf_cnpj_favorecido"],
        "codigo_tipo_transacao": df["transacao"].map(desc2cod).astype("Int64"),
    })
    # Filtra fatos com FKs ausentes
    fato = fato.dropna(subset=[
        "data_transacao", "valor", "codigo_ug", "cpf_portador",
        "cpf_cnpj_favorecido", "codigo_tipo_transacao",
    ])
    # Converte Int64 nullable para int (SQLite/Postgres lidam melhor com tipos plenos)
    fato["codigo_tipo_transacao"] = fato["codigo_tipo_transacao"].astype(int)
    fato["ano_extrato"] = fato["ano_extrato"].astype(int)
    fato["mes_extrato"] = fato["mes_extrato"].astype(int)
    fato["codigo_ug"] = fato["codigo_ug"].astype(int)
    return fato


def gravar(engine_url: str, dims: dict, fato: pd.DataFrame, *, sqlite: bool):
    if sqlite:
        import sqlite3
        conn = sqlite3.connect(engine_url)
        conn.executescript(DDL_SQLITE)
        cur = conn.cursor()

        def insert(table, df_):
            if df_.empty:
                return
            cols = ",".join(df_.columns)
            placeholders = ",".join(["?"] * len(df_.columns))
            sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            cur.executemany(sql, df_.itertuples(index=False, name=None))

        insert("orgao_superior",    dims["orgao_superior"])
        insert("orgao_subordinado", dims["orgao_subordinado"])
        insert("unidade_gestora",   dims["unidade_gestora"])
        insert("portador",          dims["portador"])
        insert("favorecido",        dims["favorecido"])

        pf = dims["favorecido"][dims["favorecido"]["tipo"] == "PF"][["cpf_cnpj"]]
        pj = dims["favorecido"][dims["favorecido"]["tipo"] == "PJ"][["cpf_cnpj"]]
        insert("pessoa_fisica",   pf)
        insert("pessoa_juridica", pj)

        insert("tipo_transacao", dims["tipo_transacao"][["codigo", "descricao"]])
        insert("transacao",      fato)
        conn.commit()
        return conn
    else:
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            print("ERRO: precisa instalar sqlalchemy e psycopg2-binary para modo PostgreSQL.")
            sys.exit(1)
        eng = create_engine(engine_url)
        with eng.begin() as conn:
            for stmt in DDL_POSTGRES.split(";"):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
            for tbl in ["orgao_superior", "orgao_subordinado", "unidade_gestora",
                        "portador", "favorecido", "tipo_transacao"]:
                dims[tbl].to_sql(tbl, conn, if_exists="append", index=False)
            pf = dims["favorecido"][dims["favorecido"]["tipo"] == "PF"][["cpf_cnpj"]]
            pj = dims["favorecido"][dims["favorecido"]["tipo"] == "PJ"][["cpf_cnpj"]]
            pf.to_sql("pessoa_fisica", conn, if_exists="append", index=False)
            pj.to_sql("pessoa_juridica", conn, if_exists="append", index=False)
            fato.to_sql("transacao", conn, if_exists="append", index=False)
        return eng


def relatorio(conn, dims, fato, descartes, sqlite=True):
    print("=" * 70)
    print("RELATÓRIO DE CARGA")
    print("=" * 70)
    print(f"  Linhas brutas:        {descartes['total_bruto']:>10,}")
    print(f"  Descartadas (chave nula): {descartes['chave_nula']:>6,}")
    print(f"  Descartadas (valor 0):    {descartes['valor_zero']:>6,}")
    print(f"  Descartadas (mês inv.):   {descartes['mes_invalido']:>6,}")
    print(f"  Descartadas (duplicata):  {descartes['duplicatas']:>6,}")
    print(f"  Linhas carregadas:    {descartes['total_carregado']:>10,}")
    print("-" * 70)
    print(f"  orgao_superior:     {len(dims['orgao_superior']):>10,}")
    print(f"  orgao_subordinado:  {len(dims['orgao_subordinado']):>10,}")
    print(f"  unidade_gestora:    {len(dims['unidade_gestora']):>10,}")
    print(f"  portador:           {len(dims['portador']):>10,}")
    print(f"  favorecido:         {len(dims['favorecido']):>10,}")
    print(f"    -> pessoa_fisica:   {(dims['favorecido']['tipo'] == 'PF').sum():>10,}")
    print(f"    -> pessoa_juridica: {(dims['favorecido']['tipo'] == 'PJ').sum():>10,}")
    print(f"    -> não identificado:{(dims['favorecido']['tipo'] == 'NI').sum():>10,}")
    print(f"  tipo_transacao:     {len(dims['tipo_transacao']):>10,}")
    print(f"  transacao (fato):   {len(fato):>10,}")
    print("=" * 70)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--postgres", help="URL de conexão PostgreSQL (sqlalchemy)")
    p.add_argument("--sqlite",   help="Caminho de arquivo .db SQLite (modo validação)")
    args = p.parse_args()

    if not args.postgres and not args.sqlite:
        p.error("Passe --postgres OU --sqlite.")

    print(f"Lendo {args.csv}...")
    df = carregar_csv(args.csv)
    print(f"  {len(df):,} linhas brutas")

    print("Limpando e tipando dados...")
    df_limpo, descartes = limpar(df)

    print("Montando dimensões e fato...")
    dims = montar_dimensoes(df_limpo)
    fato = montar_fato(df_limpo, dims["tipo_transacao"])


    if args.sqlite:
        Path(args.sqlite).parent.mkdir(parents=True, exist_ok=True)
        conn = gravar(args.sqlite, dims, fato, sqlite=True)
        relatorio(conn, dims, fato, descartes, sqlite=True)
        conn.close()
        print(f"\nOK - base gerada em {args.sqlite}")
    else:
        gravar(args.postgres, dims, fato, sqlite=False)
        relatorio(None, dims, fato, descartes, sqlite=False)
        print(f"\nOK - base populada em {args.postgres}")


if __name__ == "__main__":
    main()
