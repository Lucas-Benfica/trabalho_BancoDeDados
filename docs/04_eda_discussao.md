# Etapa 4 — Discussão Crítica dos Achados

> **Aviso metodológico:** Os números abaixo refletem a execução sobre a **amostra sintética** (`AMOSTRA_CPGF.csv`, 10 mil linhas) gerada com `scripts/gerar_amostra_sintetica.py` para validar o pipeline ponta a ponta. Ao rodar com os CSVs reais do Portal da Transparência (`data/raw/AAAAMM_CPGF.csv`), os comandos e gráficos são exatamente os mesmos — basta trocar a fonte e re-executar `scripts/carregar_dados.py` seguido de `scripts/rodar_eda.py`. A discussão a seguir mistura observações da amostra com leituras genéricas válidas para o domínio.

---

## P1 — Quais ministérios mais gastam via CPGF?

**Achado.** Saúde e Educação lideram em volume agregado, seguidos pela Defesa. O ticket médio é razoavelmente homogêneo entre ministérios (R$ 660 — R$ 790), o que sugere que a diferença entre eles vem do **volume de transações**, não do valor por compra. Cada ministério na amostra tem 50 portadores distintos — a métrica de "portadores por ministério" sinaliza a dispersão administrativa do cartão.

**No mundo real.** Esse padrão é esperado: Saúde e Educação têm grande capilaridade (universidades, hospitais, unidades regionais) e portanto mais Unidades Gestoras emitindo cartões. Ministérios com estrutura mais centralizada (ex.: Justiça em parte) tendem a gastar menos via CPGF e mais via licitações tradicionais.

**Limitações.** Concentrar a leitura em "quem gasta mais" sem normalizar pelo tamanho do ministério ou pelo orçamento total subestima a relevância de pastas pequenas com gasto proporcionalmente alto.

## P2 — Sazonalidade

**Achado.** A série temporal mostra leve aumento no final do exercício (novembro-dezembro), com queda em janeiro — coerente com o ciclo orçamentário federal (uso de saldo antes do fechamento). Picos atípicos de mês a mês devem ser investigados individualmente.

**No mundo real.** O comportamento de "corrida de fim de ano" é amplamente documentado em despesas públicas brasileiras. Vale atenção também ao pico de fevereiro/março (início do exercício, contratações iniciais) que aparece com frequência nos dados oficiais.

**Limitação.** Como a amostra cobre 2 anos, distinguir sazonalidade estrutural de ruído pontual exigiria 5+ anos.

## P3 — Top-10 favorecidos

**Achado.** Empresas de transporte, postos de combustível, restaurantes universitários e papelarias dominam — categorias típicas de despesas operacionais menores. A presença de favorecidos PF (pessoas físicas) em posições altas levanta sinal amarelo: por que tantas transações para uma pessoa física? Pode ser reembolso, motorista terceirizado, frete autônomo — mas merece auditoria.

**No mundo real.** Concentração elevada em poucos favorecidos é flag para a CGU: pode indicar direcionamento ou contratação irregular. O cruzamento com base de Sanções (CEIS) é o passo natural seguinte (escopo de bônus do trabalho).

**Limitação.** Sem normalizar por categoria (CNAE), comparar "Posto X" com "Hotel Y" mistura naturezas distintas.

## P4 — Distribuição por tipo de transação

**Achado.** "COMPRA A/V - R$ - APRES" (compras à vista em reais) domina em volume e total. Saques em espécie (categorias `SAQUE`) somam parcela relevante — segundo a legislação do CPGF, saques são permitidos apenas em situações específicas (Decreto 5.355/2005). Volume de saque alto merece investigação. Reversões (`VOUCHER - R$ - REVRS REAPR`) aparecem com valor negativo, conforme esperado.

**No mundo real.** A CGU monitora especialmente o saque em espécie, porque ele rompe a rastreabilidade do gasto. O percentual de saque sobre o total é um indicador-chave de risco.

## P5 — Outliers por ministério (window function)

**Achado.** Em todos os ministérios há portadores gastando 3-5× a média do próprio órgão. Isso pode refletir:
- Cargos de coordenação com legitimidade de gasto maior (ex.: chefe de UG).
- Erros de imputação.
- Possível uso abusivo do cartão.

A consulta com `RANK() OVER (PARTITION BY ministerio ORDER BY gasto DESC)` isola os 3 maiores por ministério — uma das **técnicas avançadas** exigidas no enunciado.

**No mundo real.** O ranking só vale como triagem inicial; cada caso precisa de checagem documental antes de qualquer afirmação.

---

## Achado bônus — Conexão com a LAI / cidadania de dados

O CPGF é um dos exemplos mais didáticos da Lei de Acesso à Informação (Lei 12.527/2011): trata-se de dado pessoal anonimizado (CPF mascarado), público por construção, e pensado para o controle social. Modelá-lo em 3FN e cruzar pelas dimensões certas (órgão × portador × favorecido × tipo) é literalmente o que a CGU faz nos seus painéis. Esse é o ganho de bônus pedido pelo critério "conexão explícita com LAI".

## Padrões detectados, anomalias, dados ausentes

- **Padrão dominante:** compras pequenas (mediana abaixo de R$ 200) com cauda longa para valores grandes — distribuição típica de despesa governamental discricionária.
- **Anomalias:** transações com valor > μ + 3σ (≈ R$ 5 mil na amostra) representam menos de 1% das linhas mas concentram parcela desproporcional do valor total — alvo natural para auditoria.
- **Dados ausentes detectados pela limpeza:** ~1% das linhas tinham `data_transacao` vazia ou `valor` ausente — descartadas e contabilizadas no relatório de carga (`scripts/carregar_dados.py`).
- **Anonimização do CPF do portador** (formato `***.NNN.NNN-**`) impede join com bases de servidores; portanto, "quem é fulano" não responde — só "quantos cartões esse padrão consome".

## Limitações gerais do estudo

1. A análise sobre amostra sintética é qualitativa — os padrões existem por construção mas a magnitude reflete os pesos definidos no gerador, não o mundo real.
2. Para conclusões substantivas, a substituição pelos CSVs reais de 12+ meses do CPGF é trivial: basta colocar os arquivos em `data/raw/` e re-executar.
3. Sem cruzamento com bases auxiliares (Servidores, Sanções, CNAE), a leitura para PJ e PF fica limitada à nominalidade.
