"""
gerar_amostra_sintetica.py
==========================
Gera um CSV sintético com schema idêntico ao CPGF do Portal da Transparência.
Útil para validar o pipeline ponta-a-ponta antes de baixar os dados reais
(o servidor do Portal estava intermitente / bloqueado por proxy no momento
do desenvolvimento).

O arquivo gerado replica:
- Mesmo delimitador (;), mesmo encoding (LATIN1)
- Mesmas 15 colunas, mesma ordem, mesmos nomes
- Mesmos formatos: data DD/MM/YYYY, valor com vírgula decimal,
  CPF anonimizado ***.NNN.NNN-**

USO:
    python scripts/gerar_amostra_sintetica.py \\
        --out data/raw/AMOSTRA_CPGF.csv \\
        --linhas 10000 \\
        --seed 42
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path


CABECALHO = [
    "Código Órgão Superior",
    "Nome Órgão Superior",
    "Código Órgão Subordinado",
    "Nome Órgão Subordinado",
    "Código Unidade Gestora",
    "Nome Unidade Gestora",
    "Ano Extrato",
    "Mês Extrato",
    "CPF Portador",
    "Nome Portador",
    "Transação",
    "Data Transação",
    "CNPJ ou CPF do Favorecido",
    "Nome Favorecido",
    "Valor Transação",
]

# Hierarquia organizacional inspirada em órgãos reais (códigos fictícios)
ORGAOS_SUPERIORES = [
    (36000, "MINISTERIO DA SAUDE"),
    (26000, "MINISTERIO DA EDUCACAO"),
    (52000, "MINISTERIO DA DEFESA"),
    (30000, "MINISTERIO DA JUSTICA E SEGURANCA PUBLICA"),
    (44000, "MINISTERIO DO MEIO AMBIENTE E MUDANCA DO CLIMA"),
    (22000, "MINISTERIO DA AGRICULTURA E PECUARIA"),
]

ORG_SUBS = [
    # (cod_sub, nome_sub, cod_sup)
    (36901, "FUNDACAO OSWALDO CRUZ",             36000),
    (36902, "FUNDACAO NACIONAL DE SAUDE",        36000),
    (26298, "UNIVERSIDADE FEDERAL DE MINAS GERAIS", 26000),
    (26252, "UNIVERSIDADE FEDERAL DE OURO PRETO",   26000),
    (52111, "COMANDO DO EXERCITO",                52000),
    (52121, "COMANDO DA MARINHA",                 52000),
    (30911, "POLICIA FEDERAL",                    30000),
    (44205, "IBAMA",                              44000),
    (22202, "EMBRAPA",                            22000),
]

# (cod_ug, nome_ug, cod_sub)
UGS = [
    (250003, "FIOCRUZ-MANGUINHOS",                36901),
    (255000, "FIOCRUZ-PE",                        36901),
    (255010, "FIOCRUZ-AM",                        36901),
    (255020, "FIOCRUZ-BA",                        36901),
    (153028, "REITORIA UFMG",                     26298),
    (153036, "HC-UFMG",                           26298),
    (153053, "ICEX-UFMG",                         26298),
    (154046, "REITORIA UFOP",                     26252),
    (160000, "COMANDO DO EXERCITO/DF",            52111),
    (160245, "12 BIB - BELO HORIZONTE",           52111),
    (170000, "CMN-DF",                            52121),
    (200001, "PF-DPF/DF",                         30911),
    (200120, "PF-MG",                             30911),
    (193099, "IBAMA-DF",                          44205),
    (193100, "IBAMA-AM",                          44205),
    (135005, "EMBRAPA-CERRADOS",                  22202),
]

TIPOS_TRANSACAO = [
    "COMPRA A/V - R$ - APRES",
    "COMPRA A/V - INT$ - APRES",
    "SAQUE - R$ - APRES",
    "SAQUE - INT$ - APRES",
    "SAQUE CASH/ATM BB",
    "SAQUE BB B24HORAS-SOL C/CLIENTE",
    "SAQUE MANUAL - CARTOES BB NA AGENCIA",
    "CPP LOJISTA TRF P/FATURA - REAL",
    "COMP A/V-SOL DISP C/CLI-R$ ANT VENC",
    "COMP A/V-SOL DISP C/CLI-R$ APOS VENC",
    "VOUCHER - R$ - REVRS REAPR",
]

# Favorecidos PJ (CNPJ 14 dígitos) — categorias plausíveis para uso de CPGF
FAVORECIDOS_PJ = [
    ("33041260000564", "PETROBRAS DISTRIBUIDORA SA"),
    ("33000167000101", "POSTO IPIRANGA DA UFMG LTDA"),
    ("47866934000174", "RESTAURANTE UNIVERSITARIO LTDA"),
    ("60746948000112", "BANCO DO BRASIL SA"),
    ("33683111000280", "CORREIOS - EMPRESA BRASILEIRA"),
    ("00041867000199", "OFICINA MECANICA SERTAO LTDA"),
    ("12345678000190", "FERRAGENS BELO HORIZONTE ME"),
    ("98765432000122", "PAPELARIA UNIVERSAL LTDA"),
    ("23456789000180", "FARMACIA DROGAFARMA"),
    ("34567890000170", "MERCADO CENTRAL ATACADO"),
    ("45678901000160", "TRANSPORTADORA EXPRESSO BR"),
    ("56789012000150", "MATERIAIS DE LIMPEZA LTDA"),
    ("67890123000140", "INFORMATICA TOTAL LTDA"),
    ("78901234000130", "TAXI COOPERATIVA MG"),
    ("89012345000120", "HOTEL CIDADE LTDA"),
]

# Favorecidos PF — formato anonimizado do Portal
FAVORECIDOS_PF = [
    ("***.123.456-**", "JOAO SILVA"),
    ("***.234.567-**", "MARIA SOUZA"),
    ("***.345.678-**", "PEDRO COSTA"),
    ("***.456.789-**", "ANA OLIVEIRA"),
]

# Portadores
def gen_cpf_anon(seed: int) -> str:
    rng = random.Random(seed)
    return f"***.{rng.randint(100,999)}.{rng.randint(100,999)}-**"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--linhas", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--ano-min", type=int, default=2023)
    p.add_argument("--ano-max", type=int, default=2024)
    args = p.parse_args()

    rng = random.Random(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    # gera portadores fixos (uns 50 distintos)
    portadores = [
        (gen_cpf_anon(args.seed + i), f"SERVIDOR FICTICIO {i:03d}")
        for i in range(50)
    ]

    # Cria o dicionário (subordinado -> superior) e (UG -> subordinado)
    sub2sup = {sub[0]: sub[2] for sub in ORG_SUBS}
    sub_names = {sub[0]: sub[1] for sub in ORG_SUBS}
    sup_names = dict(ORGAOS_SUPERIORES)

    todos_favorecidos = (
        [(c, n, "PJ") for c, n in FAVORECIDOS_PJ]
        + [(c, n, "PF") for c, n in FAVORECIDOS_PF]
    )

    with args.out.open("w", encoding="latin-1", newline="") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CABECALHO)

        for _ in range(args.linhas):
            ug = rng.choice(UGS)
            cod_ug, nome_ug, cod_sub = ug
            cod_sup = sub2sup[cod_sub]

            portador = rng.choice(portadores)
            cpf_port, nome_port = portador

            fav = rng.choice(todos_favorecidos)
            cpf_cnpj_fav, nome_fav, _ = fav

            ano = rng.randint(args.ano_min, args.ano_max)
            mes = rng.randint(1, 12)

            # data dentro do mês do extrato (com algum spill ±15 dias)
            base = date(ano, mes, rng.randint(1, 28))
            spill = timedelta(days=rng.randint(-15, 15))
            data_tx = base + spill

            tipo = rng.choices(
                TIPOS_TRANSACAO,
                weights=[60, 2, 8, 1, 5, 1, 1, 5, 1, 1, 1],  # compras à vista R$ dominam
                k=1,
            )[0]

            # distribuição de valor: 90% até R$ 500, 9% até R$ 5000, 1% até R$ 50000
            r = rng.random()
            if r < 0.90:
                val = round(rng.uniform(5, 500), 2)
            elif r < 0.99:
                val = round(rng.uniform(500, 5000), 2)
            else:
                val = round(rng.uniform(5000, 50_000), 2)

            # reversões saem negativas
            if "REVRS" in tipo:
                val = -val

            # injetar alguns problemas para a limpeza encontrar:
            # 1) ~0.5% valor zero  -> deve ser descartado
            # 2) ~0.5% data inválida vazia -> descartado
            roll = rng.random()
            if roll < 0.005:
                val = 0.0
            data_str = data_tx.strftime("%d/%m/%Y") if roll >= 0.010 else ""

            writer.writerow([
                cod_sup,
                sup_names[cod_sup],
                cod_sub,
                sub_names[cod_sub],
                cod_ug,
                nome_ug,
                ano,
                mes,
                cpf_port,
                nome_port,
                tipo,
                data_str,
                cpf_cnpj_fav,
                nome_fav,
                f"{val:.2f}".replace(".", ","),
            ])

    print(f"OK — {args.linhas} linhas geradas em {args.out}")


if __name__ == "__main__":
    main()
