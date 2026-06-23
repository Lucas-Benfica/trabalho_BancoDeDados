# Roteiro da apresentação gravada

**Duração-alvo:** 13 minutos (entre 10 e 15 conforme o enunciado)
**Plataforma sugerida:** Google Meet ou Microsoft Teams (recurso "Gravar reunião")
**Tela compartilhada:** o arquivo `slides/Apresentacao_TP_BD.pptx` em modo apresentação.
**Lembrete:** todos os integrantes precisam aparecer/falar; câmeras ligadas ajudam.

---

## Divisão por integrante

| Integrante | Slides | Tema | Tempo |
|---|---|---|---|
| **Lucas Soares Benfica** | 1, 2, 3, 4, 5 | Capa, agenda, domínio (CPGF), Etapa 1 (modelo conceitual + restrições) | ~4 min |
| **Vinícius Cardoso Antunes** | 6, 7, 8 | Etapa 2 (relacional + normalização) e Etapa 3 (DDL/carga PostgreSQL) | ~4 min |
| **Pedro Soares Pinto** | 9-13 | Etapa 4 (P1-P5: consultas e insights) | ~4 min |
| **Lucas + todos** | 14, 15, 16, 17 | Bônus, conclusão, encerramento e declaração de IA | ~1 min |

> **Dica:** quem termina sua parte introduz o próximo: *"Agora o Vinícius vai mostrar como passamos do modelo conceitual para o relacional…"* — passa naturalmente.

---

## Bloco 1 — Lucas (slides 1-5) — ~4 min

### Slide 1 — Capa (~20s)
> "Boa tarde, professor. Somos o grupo formado por Lucas Soares Benfica, Vinícius Cardoso Antunes e Pedro Soares Pinto. Vamos apresentar nosso trabalho prático de Banco de Dados, intitulado *Do Mundo Real ao Insight*, em que modelamos, implementamos e analisamos a base do Cartão de Pagamento do Governo Federal — o CPGF."

### Slide 2 — Agenda (~20s)
> "Nos próximos quatorze minutos a gente vai passar por: por que escolhemos o CPGF, o modelo conceitual ER/EER, a tradução para o modelo relacional com normalização, a implementação SQL em PostgreSQL e, principalmente, as cinco perguntas analíticas que a gente respondeu — porque é onde os insights aparecem."

### Slide 3 — Domínio (~50s)
> "O CPGF é o cartão de crédito corporativo das Unidades Gestoras da Administração Pública Federal. Toda transação tem um órgão, um portador, um favorecido, uma data, um tipo e um valor. A gente escolheu essa base por quatro motivos: ela é pública via Portal da Transparência, tem volume — 50 a 100 mil transações por mês —, tem riqueza estrutural natural para mais de quatro entidades, e tem alto interesse social, porque é literalmente onde a gente pode acompanhar como o dinheiro público é gasto no dia a dia."

### Slide 4 — Modelo conceitual ER/EER (~80s)
> "Aqui está o nosso modelo conceitual. Identificamos sete entidades — bem acima do mínimo. Temos a hierarquia administrativa em três níveis: Órgão Superior, que é o ministério, supervisiona Órgão Subordinado, que possui Unidade Gestora. A Unidade Gestora é em nome de quem o cartão é emitido. Portador é o servidor que carrega o cartão. Favorecido é quem recebe o pagamento. E como Favorecido pode ser pessoa física com CPF ou pessoa jurídica com CNPJ, com semânticas diferentes, a gente aplicou uma especialização EER disjunta e total — esse é o pulo do EER que está no enunciado. E temos Tipo de Transação, separado em entidade própria, e a entidade central, Transação, que é o ato em si."

### Slide 5 — Restrições (~60s)
> "A gente identificou nove restrições de integridade do domínio. As mais importantes são: valor da transação diferente de zero — não pode haver transação de R$ 0,00; reversões e estornos têm valor negativo; mês entre 1 e 12, ano a partir de 2003; o CPF do portador segue uma máscara anonimizada por causa da LGPD; e a regra de discriminação PF versus PJ baseada na quantidade de dígitos do documento. Todas essas restrições foram para o schema do PostgreSQL como CHECK constraints — eu repasso para o Vinícius."

---

## Bloco 2 — Vinícius (slides 6-8) — ~4 min

### Slide 6 — Modelo relacional (~70s)
> "Obrigado, Lucas. A partir do modelo conceitual, a gente aplicou as regras canônicas de tradução ER para Relacional. Olhem aqui no diagrama: temos nove relações ao todo. Cada entidade virou uma tabela. Para a especialização EER, optamos pela estratégia clássica de superclasse mais subclasses — temos uma tabela favorecido com o discriminador 'tipo' e duas tabelas filhas, pessoa_fisica e pessoa_juridica, ambas referenciando favorecido. Cada relacionamento 1:N virou uma chave estrangeira no lado N. Todas as PKs e FKs estão explícitas, e estão materializadas no DDL real do PostgreSQL."

### Slide 7 — Normalização (~90s)
> "Aqui é onde a teoria do curso é aplicada. O CSV bruto do CPGF é uma tabela plana de quinze colunas. À primeira vista parece estar bem — mas viola a Terceira Forma Normal. Por quê? Tem várias dependências funcionais transitivas: por exemplo, código do órgão superior determina nome do órgão superior; código da UG determina nome da UG. Isso gera três anomalias graves: anomalia de atualização — renomear um ministério obriga a atualizar milhões de linhas; anomalia de inserção — não dá para cadastrar uma UG nova sem ter uma transação; e redundância massiva. A decomposição que a gente fez extraiu cada DF transitiva em uma tabela própria. Verificamos que o JOIN natural reconstrói exatamente o CSV original — preservação de dados confirmada. As nove relações finais estão em BCNF, que é mais forte que 3FN. A gente também considerou desnormalizar para ganhar performance e decidiu não fazer, porque consistência é mais importante que microsegundos."

### Slide 8 — Implementação SQL (~80s)
> "Para a Etapa 3, o DDL está em sql/01_ddl.sql. Ele cria as nove tabelas com PKs, FKs e CHECK constraints — todas as nove restrições de integridade do domínio viraram CHECKs ou FKs. A carga foi automatizada em um pipeline Python — scripts/carregar_dados.py — que lê o CSV em LATIN1 com separador ponto-e-vírgula, tipa as colunas, aplica as regras de limpeza e popula as nove tabelas em ordem topológica respeitando as FKs. O script é idempotente, e suporta dois backends: PostgreSQL para produção e SQLite para validação rápida. Documentamos todos os descartes: na nossa amostra de validação de 10 mil linhas, descartamos 101 linhas com chaves nulas e carregamos 9.898 transações em todas as nove tabelas. Pedro, sua vez."

---

## Bloco 3 — Pedro (slides 9-13) — ~4 min

### Slide 9 — P1 Ministérios (~50s)
> "Valeu, Vinícius. Agora os insights. Formulamos cinco perguntas e respondemos cada uma com SQL e visualização. A pergunta um: quais ministérios mais gastam via CPGF? A consulta usa um JOIN de três tabelas — transacao, unidade_gestora, orgao_subordinado e orgao_superior. O resultado: Saúde e Educação lideram em volume, seguidos por Defesa. Curiosamente, o ticket médio é parecido entre eles — cerca de setecentos reais. A diferença vem do volume de transações, que reflete a maior capilaridade administrativa dessas pastas, com várias UFs e universidades distribuindo cartões."

### Slide 10 — P2 Sazonalidade (~40s)
> "Pergunta dois: há sazonalidade? A gente agrupou por ano e mês do extrato. O gráfico mostra um padrão típico de despesa pública brasileira: leve aumento no fim do exercício, com queda em janeiro, e um pico em fevereiro-março quando o orçamento novo começa. É o famoso ciclo orçamentário."

### Slide 11 — P3 Top favorecidos (~45s)
> "Pergunta três: top dez favorecidos por valor recebido. Usa JOIN, GROUP BY, HAVING para filtrar quem tem pelo menos cinco transações, e LIMIT 10. Empresas de transporte, postos, restaurantes e papelarias dominam — categorias clássicas de despesa operacional. Mas a gente identificou pessoas físicas no top — verde é PJ, laranja é PF — e isso merece atenção. Pode ser reembolso legítimo, motorista terceirizado, ou caso a ser investigado."

### Slide 12 — P4 Tipos (~40s)
> "Pergunta quatro: distribuição por tipo de transação. Compras à vista em reais dominam. Mas saques em espécie aparecem com participação relevante — e saques são problemáticos: rompem a rastreabilidade. O Decreto 5.355/2005 só permite saques em situações específicas, então isso é um indicador-chave de risco para a CGU. Reversões aparecem com valor negativo, como esperado pelo modelo."

### Slide 13 — P5 Window Function (~60s)
> "Pergunta cinco — a consulta avançada exigida pelo enunciado. A gente quer responder: quais portadores estão muito acima da média do próprio ministério? Usamos uma CTE com Window Function — RANK OVER PARTITION BY ministério ORDER BY gasto descendente. Resultado: em todos os ministérios há servidores gastando três a cinco vezes a média do próprio órgão. Isso pode ser legítimo — chefes de UG concentram gasto — ou pode ser alvo de auditoria. A window function ali permite detectar isso em uma única query, sem precisar fazer subqueries correlacionadas."

---

## Bloco 4 — Lucas + grupo (slides 14-17) — ~1 min

### Slide 14 — Bônus (~25s)
**(Lucas)** > "Para fechar, dois pontos de bônus: implementamos uma consulta extra que retorna transações fora do padrão estatístico — média mais três desvios-padrão — que é uma triagem clássica de outliers. E fizemos a conexão explícita com a LAI — o CPGF é literalmente o exemplo didático perfeito da Lei de Acesso à Informação."

### Slide 15 — Conclusão (~30s)
**(Vinícius)** > "Concluindo: cobrimos o ciclo completo, do ER até a EDA. O aprendizado central foi entender, na prática, que a qualidade da modelagem conceitual determina a clareza das consultas — um modelo mal normalizado teria nos forçado a workarounds em toda query. A próxima etapa natural seria integrar a base de Sanções da CGU para detecção automatizada de PJ irregulares."

### Slide 16 — Obrigado (~10s)
**(Pedro)** > "Obrigado! Estamos abertos para perguntas."

### Slide 17 — Declaração de IA (~10s)
**(Lucas)** > "Por fim, conforme o enunciado, declaramos: utilizamos assistente de IA generativa para apoio na redação, sugestões de SQL e geração de código boilerplate. Decisões de modelagem e análise foram do grupo."

---

## Checklist final antes de gravar

- [ ] Todos os integrantes aparecem (vídeo ou áudio identificado).
- [ ] Slides em modo apresentação (full screen).
- [ ] Microfone testado, sem eco.
- [ ] Tempo total entre 10 e 15 minutos (alvo: 13).
- [ ] Após a gravação, exportar o vídeo (.mp4) e salvar em `video/`.
- [ ] Subir os 4 entregáveis no Moodle: slides, código, relatório PDF, vídeo.
