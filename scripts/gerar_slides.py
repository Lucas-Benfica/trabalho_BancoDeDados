"""
gerar_slides.py
===============
Gera apresentação .pptx do TP (10-15 minutos de conteúdo).
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


# Paleta — azul UFMG / cinza profissional
COR_PRIMARIA  = RGBColor(0x1F, 0x3A, 0x5F)  # azul escuro
COR_SECUNDARIA = RGBColor(0xE8, 0xB4, 0x0F)  # amarelo UFMG
COR_TEXTO     = RGBColor(0x33, 0x33, 0x33)
COR_CLARO     = RGBColor(0xF5, 0xF7, 0xFA)

LARGURA = Inches(13.333)
ALTURA  = Inches(7.5)


def add_titulo_pagina(slide, texto, *, subtitulo=None):
    # barra superior
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                                  LARGURA, Inches(0.8))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COR_PRIMARIA
    bar.line.fill.background()

    # texto do título
    txt = slide.shapes.add_textbox(Inches(0.5), Inches(0.1), Inches(12), Inches(0.7))
    tf = txt.text_frame
    tf.margin_left = Inches(0.1)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = texto
    r.font.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    if subtitulo:
        sub = slide.shapes.add_textbox(Inches(0.5), Inches(0.85), Inches(12), Inches(0.4))
        sp = sub.text_frame.paragraphs[0]
        sr = sp.add_run()
        sr.text = subtitulo
        sr.font.italic = True
        sr.font.size = Pt(14)
        sr.font.color.rgb = COR_PRIMARIA


def add_bullet_list(slide, items, *, left=0.6, top=1.5, width=12.0, height=5.5,
                     font_size=20):
    box = slide.shapes.add_textbox(Inches(left), Inches(top),
                                    Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = "• " + item
        r.font.size = Pt(font_size)
        r.font.color.rgb = COR_TEXTO


def add_imagem_centralizada(slide, path, *, top=1.5, height=5.5):
    pic = slide.shapes.add_picture(str(path), Inches(0), Inches(top), height=Inches(height))
    pic.left = int((LARGURA - pic.width) / 2)


def add_imagem_lateral(slide, path, *, left=7.0, top=1.5, height=5.5):
    slide.shapes.add_picture(str(path), Inches(left), Inches(top), height=Inches(height))


def add_footer(slide, num_total, n_atual):
    box = slide.shapes.add_textbox(Inches(0.4), Inches(7.0), Inches(12.5), Inches(0.4))
    p = box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    r = p.add_run()
    r.text = f"TP Banco de Dados · DCC/UFMG · {n_atual}/{num_total}"
    r.font.size = Pt(9)
    r.font.color.rgb = COR_PRIMARIA
    r.font.italic = True


def build(out: Path):
    prs = Presentation()
    prs.slide_width = LARGURA
    prs.slide_height = ALTURA
    blank = prs.slide_layouts[6]

    # ===== Slide 1: CAPA =====
    s = prs.slides.add_slide(blank)
    # fundo
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), LARGURA, ALTURA)
    bg.fill.solid(); bg.fill.fore_color.rgb = COR_PRIMARIA; bg.line.fill.background()
    # faixa amarela
    faixa = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(4.2), LARGURA, Inches(0.08))
    faixa.fill.solid(); faixa.fill.fore_color.rgb = COR_SECUNDARIA; faixa.line.fill.background()
    # título
    tb = s.shapes.add_textbox(Inches(0.7), Inches(1.7), Inches(12), Inches(2.0))
    tf = tb.text_frame
    p = tf.paragraphs[0]; r = p.add_run()
    r.text = "Do Mundo Real ao Insight"
    r.font.size = Pt(54); r.font.bold = True
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p2 = tf.add_paragraph(); r2 = p2.add_run()
    r2.text = "Modelagem, implementação e análise do CPGF"
    r2.font.size = Pt(24); r2.font.italic = True
    r2.font.color.rgb = COR_SECUNDARIA
    # autores
    autores = s.shapes.add_textbox(Inches(0.7), Inches(4.6), Inches(12), Inches(2.0))
    tf2 = autores.text_frame
    for i, nome in enumerate(["Lucas Soares Benfica",
                              "Vinícius Cardoso Antunes",
                              "Pedro Soares Pinto"]):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        rr = p.add_run(); rr.text = nome
        rr.font.size = Pt(22); rr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    rod = s.shapes.add_textbox(Inches(0.7), Inches(6.8), Inches(12), Inches(0.4))
    rrr = rod.text_frame.paragraphs[0].add_run()
    rrr.text = "DCC/UFMG · Banco de Dados · Prof. Pedro H. Barros · 2026"
    rrr.font.size = Pt(13); rrr.font.italic = True
    rrr.font.color.rgb = COR_SECUNDARIA

    # ===== Slide 2: AGENDA =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Agenda", subtitulo="Como vamos conduzir os próximos ~14 minutos")
    add_bullet_list(s, [
        "Domínio escolhido e justificativa — CPGF",
        "Etapa 1 — Modelo Conceitual (ER/EER)",
        "Etapa 2 — Modelo Relacional + Normalização",
        "Etapa 3 — Implementação SQL + carga em PostgreSQL",
        "Etapa 4 — 5 perguntas analíticas e os insights encontrados",
        "Conclusão, limitações e próximos passos",
    ])

    # ===== Slide 3: DOMÍNIO =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "O que é o CPGF — por que essa base?",
                      subtitulo="Cartão de Pagamento do Governo Federal · Portal da Transparência")
    add_bullet_list(s, [
        "Cartão de crédito corporativo de Unidades Gestoras da Administração Pública Federal.",
        "Cada transação registra órgão, portador, favorecido, data, tipo e valor.",
        "Base pública (LAI), volume robusto — 50-100 mil transações por mês.",
        "Riqueza estrutural natural: 4+ entidades, hierarquia em 3 níveis, especialização PF/PJ.",
        "Domínio de alto interesse social — controle de gastos públicos.",
    ])

    # ===== Slide 4: ETAPA 1 — ER =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Etapa 1 — Modelo Conceitual (ER/EER)",
                      subtitulo="7 entidades, notação ER clássica + extensão EER (especialização)")
    add_imagem_centralizada(s, "docs/diagrama_er.png", top=1.4, height=5.6)

    # ===== Slide 5: ETAPA 1 — restrições =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Etapa 1 — Restrições de integridade do domínio")
    add_bullet_list(s, [
        "R1. valor ≠ 0; reversões/estornos têm valor negativo (R2).",
        "R3. data_transacao válida e próxima do mês-ano do extrato.",
        "R4. mes_extrato ∈ {1..12}; ano_extrato ∈ [2003, atual].",
        "R5. cpf_portador na máscara anonimizada ***.NNN.NNN-**.",
        "R6. cpf_cnpj_favorecido: 11 dígitos = PF, 14 = PJ.",
        "R7-R8. Integridade referencial entre os 4 níveis da hierarquia.",
        "R9. Discriminador de especialização EER: tipo ∈ {PF, PJ, NI}.",
    ], font_size=18)

    # ===== Slide 6: ETAPA 2 — RELACIONAL =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Etapa 2 — Esquema relacional",
                      subtitulo="9 relações com PK/FK explícitas em PostgreSQL")
    add_imagem_centralizada(s, "docs/diagrama_relacional.png", top=1.4, height=5.6)

    # ===== Slide 7: ETAPA 2 — NORMALIZAÇÃO =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Etapa 2 — Normalização até BCNF",
                      subtitulo="Por quê: o CSV bruto viola 3FN com várias DFs transitivas")
    add_bullet_list(s, [
        "CSV bruto = tabela plana de 15 colunas — viola 3FN.",
        "DFs transitivas como codigo_orgao_superior → nome_orgao_superior geravam:",
        "    · anomalias de atualização (renomear ministério = atualizar milhões de linhas)",
        "    · anomalias de inserção (criar UG sem ter transação)",
        "    · redundância massiva (nome de ministério repetido N vezes)",
        "Decomposição: cada DF transitiva virou tabela própria.",
        "Resultado: 9 relações em BCNF (e portanto 3FN). JOIN natural reconstrói o CSV.",
    ], font_size=18)

    # ===== Slide 8: ETAPA 3 — DDL/CARGA =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Etapa 3 — Implementação em PostgreSQL")
    add_bullet_list(s, [
        "sql/01_ddl.sql — CREATE TABLE com PKs, FKs, CHECKs e índices.",
        "Restrições de domínio embarcadas no schema (CHECK valor <> 0, mês 1..12...).",
        "scripts/carregar_dados.py — pipeline Python que lê CSV (LATIN1, sep=;),",
        "    tipa, limpa e popula em ordem topológica. Suporta PostgreSQL e SQLite.",
        "Limpeza documentada: chaves nulas, valor 0, mês inválido, duplicatas.",
        "Sobre amostra de 10 mil linhas: 9.898 carregadas (101 descartes auditados).",
        "Tudo idempotente — re-executar não polui dados.",
    ], font_size=18)

    # ===== Slide 9: P1 =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "P1 — Quais ministérios mais gastam via CPGF?",
                      subtitulo="JOIN 3 tabelas + GROUP BY + agregações")
    add_imagem_centralizada(s, "docs/graficos/q1_gasto_por_ministerio.png", top=1.4, height=5.6)

    # ===== Slide 10: P2 =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "P2 — Há sazonalidade nos gastos?",
                      subtitulo="GROUP BY composto + agregação temporal")
    add_imagem_centralizada(s, "docs/graficos/q2_serie_temporal.png", top=1.4, height=5.6)

    # ===== Slide 11: P3 =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "P3 — Top-10 favorecidos e concentração",
                      subtitulo="JOIN + GROUP BY + HAVING + LIMIT")
    add_imagem_centralizada(s, "docs/graficos/q3_top_favorecidos.png", top=1.4, height=5.6)

    # ===== Slide 12: P4 =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "P4 — Distribuição por tipo de transação",
                      subtitulo="Saques em espécie merecem monitoramento")
    add_imagem_centralizada(s, "docs/graficos/q4_tipo_transacao.png", top=1.4, height=5.6)

    # ===== Slide 13: P5 — Avançada =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "P5 — Outliers por ministério (Window Function)",
                      subtitulo="CTE + RANK() OVER (PARTITION BY ministerio ORDER BY gasto DESC)")
    add_imagem_centralizada(s, "docs/graficos/q5_top_portadores.png", top=1.4, height=5.6)

    # ===== Slide 14: Bônus =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Bônus — Detecção de anomalias e ligação com a LAI")
    add_bullet_list(s, [
        "Consulta extra: transações fora do padrão estatístico (μ + 3σ).",
        "Triagem inicial automatizada — útil ao controle interno.",
        "Atende critério bônus: 'técnicas além do escopo'.",
        "CPGF é exemplo didático da Lei de Acesso à Informação (LAI):",
        "    · dado pessoal anonimizado, público por construção, pensado para controle social.",
        "Cruzar dimensões (órgão × portador × favorecido × tipo) = trabalho da CGU.",
    ], font_size=18)

    # ===== Slide 15: Conclusão =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Conclusão e próximos passos")
    add_bullet_list(s, [
        "Cobrimos o ciclo completo: ER → Relacional → SQL → EDA.",
        "Aprendemos: qualidade da modelagem conceitual = clareza das consultas.",
        "Resultado: 9 relações em BCNF, 5 consultas analíticas + 1 bônus, todos os requisitos cobertos.",
        "Limitações: resultados mostrados sobre amostra de validação — pipeline pronto para os CSVs reais.",
        "Próximos passos: cruzamento com CEIS (Sanções), carga incremental, dashboard interativo.",
    ], font_size=18)

    # ===== Slide 16: Obrigado =====
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), LARGURA, ALTURA)
    bg.fill.solid(); bg.fill.fore_color.rgb = COR_PRIMARIA; bg.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.7), Inches(2.4), Inches(12), Inches(2.0))
    p = tb.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = "Obrigado!"
    r.font.size = Pt(72); r.font.bold = True
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p2 = tb.text_frame.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run(); r2.text = "Perguntas?"
    r2.font.size = Pt(32); r2.font.italic = True
    r2.font.color.rgb = COR_SECUNDARIA

    # ===== Slide 17: Declaração de IA =====
    s = prs.slides.add_slide(blank)
    add_titulo_pagina(s, "Declaração de uso de IA",
                      subtitulo="Conforme permitido pelo enunciado")
    add_bullet_list(s, [
        "Ferramenta utilizada: assistente de IA generativa.",
        "Onde foi usada:",
        "    · apoio na redação do relatório técnico e destes slides;",
        "    · sugestões de boas práticas em SQL e modelagem ER/EER;",
        "    · geração de código boilerplate para o pipeline ETL;",
        "    · revisão ortográfica.",
        "O que NÃO foi delegado à IA:",
        "    · decisões de modelagem e normalização;",
        "    · interpretação dos resultados e discussão crítica.",
        "Bibliotecas utilizadas: pandas, matplotlib, graphviz, python-docx, python-pptx.",
    ], font_size=17)

    prs.save(str(out))
    print(f"OK — apresentação gerada em {out} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    out = Path("slides/Apresentacao_TP_BD.pptx")
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out)
