"""
rodar_eda.py
============
Executa as consultas da Etapa 4 e gera as visualizações da EDA.
Lê do SQLite (modo validação) ou do PostgreSQL (modo produção).

USO:
    python scripts/rodar_eda.py --sqlite /tmp/cpgf/cpgf.db --out docs/graficos
    python scripts/rodar_eda.py --postgres "postgresql://..." --out docs/graficos
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend headless
import matplotlib.pyplot as plt
import pandas as pd


# ---------------------------------------------------------------------------
# Queries — versão SQLite-compatível (sem ::numeric, sem STDDEV antigo)
# As versões PostgreSQL-canônicas estão em sql/03_consultas.sql
# ---------------------------------------------------------------------------
Q1 = """
SELECT
    os.nome                         AS ministerio,
    COUNT(t.id)                     AS qtd_transacoes,
    ROUND(SUM(t.valor), 2)          AS gasto_total_brl,
    ROUND(AVG(t.valor), 2)          AS ticket_medio_brl,
    COUNT(DISTINCT t.cpf_portador)  AS portadores_distintos
FROM transacao         t
JOIN unidade_gestora   ug   ON ug.codigo   = t.codigo_ug
JOIN orgao_subordinado osub ON osub.codigo = ug.codigo_orgao_subordinado
JOIN orgao_superior    os   ON os.codigo   = osub.codigo_orgao_superior
WHERE t.valor > 0
GROUP BY os.nome
ORDER BY gasto_total_brl DESC;
"""

Q2 = """
SELECT
    ano_extrato,
    mes_extrato,
    COUNT(*) AS qtd_transacoes,
    ROUND(SUM(valor), 2) AS gasto_total
FROM transacao
WHERE valor > 0
GROUP BY ano_extrato, mes_extrato
ORDER BY ano_extrato, mes_extrato;
"""

Q3 = """
SELECT
    f.nome AS favorecido,
    f.tipo AS pf_ou_pj,
    COUNT(t.id) AS qtd_pagamentos,
    ROUND(SUM(t.valor), 2) AS total_recebido,
    ROUND(AVG(t.valor), 2) AS ticket_medio
FROM transacao  t
JOIN favorecido f ON f.cpf_cnpj = t.cpf_cnpj_favorecido
WHERE t.valor > 0
GROUP BY f.nome, f.tipo
HAVING COUNT(t.id) >= 5
ORDER BY total_recebido DESC
LIMIT 10;
"""

Q4 = """
SELECT
    tt.descricao AS tipo_transacao,
    COUNT(t.id) AS qtd,
    ROUND(SUM(t.valor), 2) AS total,
    ROUND(MIN(t.valor), 2) AS minimo,
    ROUND(MAX(t.valor), 2) AS maximo,
    ROUND(AVG(t.valor), 2) AS media
FROM transacao      t
JOIN tipo_transacao tt ON tt.codigo = t.codigo_tipo_transacao
GROUP BY tt.descricao
ORDER BY total DESC;
"""

Q5 = """
WITH gasto_por_portador AS (
    SELECT
        t.cpf_portador,
        p.nome AS nome_portador,
        os.nome AS ministerio,
        SUM(t.valor) AS gasto_portador
    FROM transacao         t
    JOIN portador          p   ON p.cpf = t.cpf_portador
    JOIN unidade_gestora   ug  ON ug.codigo = t.codigo_ug
    JOIN orgao_subordinado osub ON osub.codigo = ug.codigo_orgao_subordinado
    JOIN orgao_superior    os  ON os.codigo = osub.codigo_orgao_superior
    WHERE t.valor > 0
    GROUP BY t.cpf_portador, p.nome, os.nome
),
estatisticas_ministerio AS (
    SELECT
        cpf_portador, nome_portador, ministerio, gasto_portador,
        AVG(gasto_portador)  OVER (PARTITION BY ministerio) AS media_min,
        RANK()               OVER (PARTITION BY ministerio
                                   ORDER BY gasto_portador DESC) AS rank_no_min
    FROM gasto_por_portador
)
SELECT
    ministerio,
    nome_portador,
    ROUND(gasto_portador, 2)  AS gasto_brl,
    ROUND(media_min, 2)       AS media_do_ministerio,
    ROUND(gasto_portador / media_min, 2) AS razao_vs_media,
    rank_no_min
FROM estatisticas_ministerio
WHERE rank_no_min <= 3
ORDER BY ministerio, rank_no_min;
"""


def conectar(args):
    if args.sqlite:
        return sqlite3.connect(args.sqlite)
    raise SystemExit("Modo postgres ainda nao implementado neste script de EDA")


def grafico_q1(df: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(11, 5))
    df_plot = df.sort_values("gasto_total_brl")
    ax.barh(df_plot["ministerio"], df_plot["gasto_total_brl"], color="#1f4e79")
    ax.set_xlabel("Gasto total (R$)")
    ax.set_title("P1 — Gasto total via CPGF por Ministério (Órgão Superior)")
    for i, v in enumerate(df_plot["gasto_total_brl"]):
        ax.text(v, i, f"  R$ {v:,.0f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "q1_gasto_por_ministerio.png", dpi=130)
    plt.close(fig)


def grafico_q2(df: pd.DataFrame, out: Path):
    df = df.copy()
    df["periodo"] = df["ano_extrato"].astype(str) + "-" + df["mes_extrato"].astype(str).str.zfill(2)
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(df["periodo"], df["gasto_total"], marker="o", color="#c0504d", linewidth=2)
    ax.set_xlabel("Período (ano-mês do extrato)")
    ax.set_ylabel("Gasto total (R$)")
    ax.set_title("P2 — Evolução temporal do gasto CPGF")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "q2_serie_temporal.png", dpi=130)
    plt.close(fig)


def grafico_q3(df: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(11, 5))
    df_plot = df.sort_values("total_recebido")
    cores = ["#2e7d32" if t == "PJ" else "#ef6c00" for t in df_plot["pf_ou_pj"]]
    ax.barh(df_plot["favorecido"], df_plot["total_recebido"], color=cores)
    ax.set_xlabel("Total recebido (R$)")
    ax.set_title("P3 — Top-10 favorecidos (verde = PJ, laranja = PF)")
    fig.tight_layout()
    fig.savefig(out / "q3_top_favorecidos.png", dpi=130)
    plt.close(fig)


def grafico_q4(df: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(11, 5))
    df_plot = df.sort_values("total")
    ax.barh(df_plot["tipo_transacao"], df_plot["total"], color="#7b1fa2")
    ax.set_xlabel("Total movimentado (R$)")
    ax.set_title("P4 — Movimentação por tipo de transação")
    fig.tight_layout()
    fig.savefig(out / "q4_tipo_transacao.png", dpi=130)
    plt.close(fig)


def grafico_q5(df: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(11, 6))
    df_plot = df.sort_values(["ministerio", "rank_no_min"])
    rotulo = df_plot["ministerio"] + " — #" + df_plot["rank_no_min"].astype(str)
    ax.barh(rotulo, df_plot["razao_vs_media"], color="#0277bd")
    ax.axvline(1.0, color="grey", linestyle="--", label="média do ministério")
    ax.set_xlabel("Razão (gasto / média do ministério)")
    ax.set_title("P5 — Top-3 portadores por ministério vs média (window function)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "q5_top_portadores.png", dpi=130)
    plt.close(fig)


def grafico_extra_distribuicao(conn, out: Path):
    df = pd.read_sql("SELECT valor FROM transacao WHERE valor BETWEEN 0 AND 5000", conn)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.hist(df["valor"], bins=50, color="#455a64", edgecolor="white")
    ax.set_xlabel("Valor da transação (R$)")
    ax.set_ylabel("Frequência")
    ax.set_title("Distribuição de valores de transação (até R$ 5.000) — cauda longa esperada")
    fig.tight_layout()
    fig.savefig(out / "extra_distribuicao_valores.png", dpi=130)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sqlite", help="Caminho do .db SQLite")
    p.add_argument("--postgres", help="(nao implementado neste script auxiliar)")
    p.add_argument("--out", type=Path, default=Path("docs/graficos"))
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    conn = conectar(args)

    print("\n=== P1 — Gasto por Ministério ===")
    d1 = pd.read_sql(Q1, conn);   print(d1.to_string(index=False))
    grafico_q1(d1, args.out)

    print("\n=== P2 — Sazonalidade ===")
    d2 = pd.read_sql(Q2, conn);   print(d2.to_string(index=False))
    grafico_q2(d2, args.out)

    print("\n=== P3 — Top favorecidos ===")
    d3 = pd.read_sql(Q3, conn);   print(d3.to_string(index=False))
    grafico_q3(d3, args.out)

    print("\n=== P4 — Tipos de transação ===")
    d4 = pd.read_sql(Q4, conn);   print(d4.to_string(index=False))
    grafico_q4(d4, args.out)

    print("\n=== P5 — Top portadores por ministério (window function) ===")
    d5 = pd.read_sql(Q5, conn);   print(d5.to_string(index=False))
    grafico_q5(d5, args.out)

    grafico_extra_distribuicao(conn, args.out)

    # salva tabelas em CSV para o relatório
    for name, df in [("q1", d1), ("q2", d2), ("q3", d3), ("q4", d4), ("q5", d5)]:
        df.to_csv(args.out / f"{name}_resultado.csv", index=False)

    print(f"\nGraficos salvos em {args.out}")
    conn.close()


if __name__ == "__main__":
    main()
