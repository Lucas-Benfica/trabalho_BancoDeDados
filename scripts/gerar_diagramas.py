"""
gerar_diagramas.py
==================
Renderiza os diagramas ER/EER e Relacional usando Graphviz.
Saída: docs/diagrama_er.png e docs/diagrama_relacional.png
"""
from pathlib import Path
from graphviz import Digraph


def er():
    g = Digraph("ER", format="png")
    g.attr(rankdir="LR", bgcolor="white", fontname="Helvetica")
    g.attr("node", shape="box", style="filled,rounded", fillcolor="#dbeafe",
           fontname="Helvetica", fontsize="11")
    g.attr("edge", fontname="Helvetica", fontsize="10")

    entities = {
        "orgao_superior":     "ORGAO_SUPERIOR\\ncodigo (PK), nome",
        "orgao_subordinado":  "ORGAO_SUBORDINADO\\ncodigo (PK), nome\\ncodigo_orgao_superior (FK)",
        "unidade_gestora":    "UNIDADE_GESTORA\\ncodigo (PK), nome\\ncodigo_orgao_subordinado (FK)",
        "portador":           "PORTADOR\\ncpf (PK), nome",
        "favorecido":         "FAVORECIDO\\ncpf_cnpj (PK), nome, tipo",
        "pessoa_fisica":      "PESSOA_FISICA\\ncpf_cnpj (PK,FK)",
        "pessoa_juridica":    "PESSOA_JURIDICA\\ncpf_cnpj (PK,FK)",
        "tipo_transacao":     "TIPO_TRANSACAO\\ncodigo (PK), descricao",
        "transacao":          "TRANSACAO\\nid (PK), data, valor\\nano/mes_extrato\\n+ 4 FKs",
    }
    for n, lbl in entities.items():
        if n == "transacao":
            g.node(n, lbl, fillcolor="#fef3c7")
        elif n in ("pessoa_fisica", "pessoa_juridica"):
            g.node(n, lbl, fillcolor="#fee2e2")
        else:
            g.node(n, lbl)

    g.edge("orgao_superior",    "orgao_subordinado", label="1 — supervisiona — N")
    g.edge("orgao_subordinado", "unidade_gestora",   label="1 — possui — N")
    g.edge("unidade_gestora",   "transacao",         label="1 — registra — N")
    g.edge("portador",          "transacao",         label="1 — realiza — N")
    g.edge("favorecido",        "transacao",         label="1 — recebe — N")
    g.edge("tipo_transacao",    "transacao",         label="1 — classifica — N")
    g.edge("favorecido", "pessoa_fisica",   label="(EER: PF)", style="dashed")
    g.edge("favorecido", "pessoa_juridica", label="(EER: PJ)", style="dashed")
    return g


def relacional():
    g = Digraph("Relacional", format="png")
    g.attr(rankdir="LR", bgcolor="white", fontname="Helvetica")
    g.attr("node", shape="plain", fontname="Helvetica", fontsize="10")

    def tbl(name, color, rows):
        rows_html = "".join(
            f'<TR><TD ALIGN="LEFT" BGCOLOR="white">{r}</TD></TR>' for r in rows
        )
        return f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
            <TR><TD BGCOLOR="{color}"><B>{name}</B></TD></TR>
            {rows_html}
        </TABLE>>'''

    g.node("orgao_superior", tbl("orgao_superior", "#1f4e79",
        ["<u>codigo</u> INTEGER", "nome TEXT NOT NULL"]))
    g.node("orgao_subordinado", tbl("orgao_subordinado", "#1f4e79", [
        "<u>codigo</u> INTEGER", "nome TEXT NOT NULL",
        "codigo_orgao_superior INTEGER (FK)"]))
    g.node("unidade_gestora", tbl("unidade_gestora", "#1f4e79", [
        "<u>codigo</u> INTEGER", "nome TEXT NOT NULL",
        "codigo_orgao_subordinado INTEGER (FK)"]))
    g.node("portador", tbl("portador", "#2e7d32", [
        "<u>cpf</u> TEXT", "nome TEXT NOT NULL"]))
    g.node("favorecido", tbl("favorecido", "#ef6c00", [
        "<u>cpf_cnpj</u> TEXT", "nome TEXT NOT NULL", "tipo CHAR(2) CHECK PF/PJ/NI"]))
    g.node("pessoa_fisica", tbl("pessoa_fisica", "#7b1fa2", [
        "<u>cpf_cnpj</u> TEXT (FK favorecido)"]))
    g.node("pessoa_juridica", tbl("pessoa_juridica", "#7b1fa2", [
        "<u>cpf_cnpj</u> TEXT (FK favorecido)"]))
    g.node("tipo_transacao", tbl("tipo_transacao", "#455a64", [
        "<u>codigo</u> SERIAL", "descricao TEXT UNIQUE"]))
    g.node("transacao", tbl("transacao", "#c0504d", [
        "<u>id</u> BIGSERIAL",
        "data_transacao DATE NOT NULL",
        "valor NUMERIC(14,2) CHECK &lt;&gt; 0",
        "ano_extrato SMALLINT",
        "mes_extrato SMALLINT CHECK 1..12",
        "codigo_ug INTEGER (FK)",
        "cpf_portador TEXT (FK)",
        "cpf_cnpj_favorecido TEXT (FK)",
        "codigo_tipo_transacao INTEGER (FK)"]))

    edges = [
        ("orgao_superior",    "orgao_subordinado"),
        ("orgao_subordinado", "unidade_gestora"),
        ("unidade_gestora",   "transacao"),
        ("portador",          "transacao"),
        ("favorecido",        "transacao"),
        ("tipo_transacao",    "transacao"),
        ("favorecido",        "pessoa_fisica"),
        ("favorecido",        "pessoa_juridica"),
    ]
    for a, b in edges:
        g.edge(a, b)
    return g


def main():
    import shutil, tempfile
    out = Path("docs")
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        er().render(filename=str(tmp_path / "diagrama_er"), cleanup=True)
        relacional().render(filename=str(tmp_path / "diagrama_relacional"), cleanup=True)
        shutil.copy(tmp_path / "diagrama_er.png", out / "diagrama_er.png")
        shutil.copy(tmp_path / "diagrama_relacional.png", out / "diagrama_relacional.png")
    print("OK — diagramas em docs/diagrama_er.png e docs/diagrama_relacional.png")


if __name__ == "__main__":
    main()
