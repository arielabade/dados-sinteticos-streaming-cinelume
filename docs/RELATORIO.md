# Cinelume · Relatório gerencial

**out/2023 a out/2026** · preparado por ABADE (Strategy · Data · Growth) · fonte: `dados_medium` (29.829 contas)

> **Dados sintéticos.** A Cinelume é uma empresa fictícia; todo cliente, real e resultado foi gerado pelo simulador deste repositório.
> O relatório demonstra o método, não descreve um negócio real.

**Versão interativa: [relatório estilo Power BI](https://arielabade.github.io/dados-sinteticos-streaming-cinelume/relatorio/)**, com navegador de meses, comparação com o período anterior ou com o ano
anterior, e filtros de canal, plano e método de pagamento. Este texto e o relatório interativo saem do mesmo cubo de dados
(`python relatorio/build.py`); aqui a leitura é dos **últimos 12 meses (nov/2025 a out/2026) contra os 12 anteriores**.

---

## 1. Resumo

Base **+46,1%** (+5.162 líquidos), mas para cada saída entram só **1,6**: **35%** das saídas são falha de pagamento.

Nos últimos 12 meses a base cresceu **46,1%** (5.162 assinantes líquidos) e a receita recorrente **50,0%**: para cada assinante que saiu, entraram **1,6**. O ritmo desacelerou: nos 12 meses anteriores a base tinha crescido 86,0%. Pontos fortes: crescimento de assinantes, crescimento da receita recorrente, payback do CAC. Ponto a vigiar: **churn involuntário** (35%). A aquisição já se paga em 1,5 meses; a próxima alavanca é reter: **cobrança (35% das saídas) e reengajamento (63% de quem cancela cita pouco uso)**.

### O que decidir

1. **Recuperar a cobrança: 35% das saídas são falha de pagamento** (Alerta · churn involuntário). 3.003 assinaturas encerradas por pagamento não concretizado: cerca de R$ 10.836 de receita recorrente perdida por mês. Boleto perde 2,1x mais por pagamento que Cartão (3,3% contra 1,6% ao mês). *O que fazer:* retentativa inteligente no cartão, lembrete antes do vencimento e migração de quem paga com Boleto para cobrança automática.
2. **Reengajar antes do cancelamento: 63% de quem cancela cita pouco uso** (Atenção · motivo de cancelamento). Pouco uso lidera as 2.347 respostas da pesquisa de cancelamento; preço é citado por 22%. *O que fazer:* reengajar quem não assiste há 14 dias (push com recomendação) antes de oferecer desconto.
3. **Realocar verba de Social pago para Busca paga, em degraus** (Saudável · payback do CAC). LTV/CAC (receita) de 20,4x em Busca paga contra 7,6x em Social pago; os canais pagos, juntos, se pagam em 1,5 meses. *O que fazer:* mover verba aos poucos, lendo o CAC marginal a cada passo.

### Indicadores do período

| Indicador | nov/2025–out/2026 | nov/2024–out/2025 | Variação | Faixa de leitura | Leitura |
|---|---:|---:|---:|---|---|
| Assinantes ativos (fim) | 16.370 | 11.208 | +46,1% | — | — |
| Crescimento de assinantes | +46,1% | +86,0% | -39,9 p.p. | +3,2% ao mês · ≥ +1% ao mês bom · < 0 alerta | Saudável |
| Receita recorrente (último mês) | R$ 720.405 | R$ 480.140 | +50,0% | — | — |
| Crescimento da receita recorrente | +50,0% | +114,0% | -64,0 p.p. | +3,4% ao mês · ≥ +1% ao mês bom · < 0 alerta | Saudável |
| Receita paga | R$ 7.619.203 | R$ 4.552.818 | +67,4% | — | — |
| Novas assinaturas | 11.202 | 10.096 | +11,0% | — | — |
| Quick ratio | 1,60 | 1,82 | -0,21 | ≥ 2 saudável · < 1 encolhendo | Atenção |
| Churn mensal | 5,1% | 5,9% | -0,8 p.p. | ≤ 4% bom · > 6% alerta | Atenção |
| Churn involuntário (parcela das saídas) | 35% | 33% | +2,4 p.p. | ≤ 25% bom · > 35% alerta | Alerta |
| Receita por assinante / mês (média do período) | R$ 43,30 | R$ 39,29 | +10,2% | — | — |
| Investimento em aquisição | R$ 397.148 | R$ 378.345 | +5,0% | — | — |
| CAC dos canais pagos (busca, social, TV) | R$ 66 | R$ 71 | -7,5% | — | — |
| CAC médio, todos os canais (inclui orgânico) | R$ 36 | R$ 38 | -5,3% | — | — |
| Payback do CAC | 1,5 meses | 1,8 meses | -0,3 meses | ≤ 6 meses bom · > 12 alerta | Saudável |
| LTV / CAC (receita) | 12,8x | 9,3x | +38,0% | ≥ 3x bom · < 1,5x alerta | Saudável |
| Ativação (assinantes que assistiram no mês) | 96% | 96% | -0,3 p.p. | ≥ 85% bom · < 70% alerta | Saudável |
| NPS | 28 | 18 | +10 pts | ≥ 30 bom · < 0 alerta | Atenção |

As faixas são regras de bolso declaradas (as mesmas do relatório interativo), não benchmarks medidos. LTV e payback usam receita,
não margem: com custo de conteúdo, os dois ficam piores. A receita por assinante da tabela é a média do período contra a média da
comparação; a variação da receita recorrente nos achados abaixo compara o último mês com o mês anterior ao início do período.

**O que os dados mostram**

- **Base e receita.** 16.370 assinantes ativos em out/2026 (+46,1% em 12 meses) e R$ 7.619.203 de receita paga nos últimos 12 meses (+67,4% contra os 12 anteriores). A receita recorrente cresceu 50,0% de out/2025 a out/2026: 93% do aumento veio de mais assinantes (+46,1% na base, +2,7% por assinante).
- **Churn.** 5,1% ao mês nos últimos 12 meses (-0,8 p.p.); o involuntário, falha de pagamento, é 35% dos encerramentos, e Boleto tem o maior churn involuntário (3,3% ao mês).
- **Canais.** Entre os canais pagos, TV tem o CAC mais alto (R$ 110) e Busca paga o mais baixo (R$ 46).
- **Atribuição.** Contra o canal gravado na conta, a ferramenta de atribuição credita Busca paga +33%, Social pago -22%, TV -55%: decidir verba pela atribuição superinveste em Busca paga e subinveste em TV, Social pago.
- **Cancelamento.** Pouco uso é o motivo mais citado (63% das 2.347 respostas em 12 meses).
- **Uso por plano.** Quem assina Premium assiste 26,1 h por mês, contra 11,3 h no Básico com anúncios.
- **Uso.** As horas por conta que assistiu cresceram +45,1% contra os 12 meses anteriores, puxadas pelo Premium (+67,6%: de 15,6 para 26,1 h). Nele, as reproduções por conta foram de 18,6 para 28,1 por mês (+50,6%) e a duração por reprodução de 50 para 56 min (+11,3%): a variação vem da frequência, não de sessões mais longas. Nenhum evento registrado explica a mudança: a causa de negócio ainda precisa ser registrada.

---

## 2. Aquisição (últimos 12 meses)

*A pergunta: cada real investido está trazendo assinantes que pagam e ficam?*

O canal de cada cadastro é o gravado na conta. A coluna "atribuição" mostra o que a ferramenta de último clique creditou ao canal;
a diferença é a distorção que ela introduz. CAC = investimento / contas novas que pagaram a primeira fatura em até 30 dias.

| Canal | Investimento | Cadastros (conta) | Cadastros (atribuição) | Atribuição vs conta | Pagantes 30d | CAC | Churn mensal | LTV (receita) | LTV / CAC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Orgânico** | R$ 0 | 3.388 | 3.179 | -6% | 3.304 | R$ 0 | 4,5% | R$ 1.002 | — |
| **Busca paga** | R$ 93.527 | 2.100 | 2.803 | +33% | 2.055 | R$ 46 | 4,8% | R$ 928 | 20,38x |
| **Social pago** | R$ 182.909 | 2.622 | 2.048 | -22% | 2.559 | R$ 71 | 7,7% | R$ 546 | 7,63x |
| **Indicação** | R$ 15.060 | 1.004 | 1.090 | +9% | 984 | R$ 15 | 4,1% | R$ 1.064 | 69,50x |
| **Parceria com operadora** | R$ 35.975 | 1.439 | 1.379 | -4% | 1.407 | R$ 26 | 4,3% | R$ 861 | 33,67x |
| **TV** | R$ 69.677 | 649 | 292 | -55% | 635 | R$ 110 | 5,3% | R$ 844 | 7,69x |

\* menos de 30 pagantes: direção, não ranking. Orgânico não tem investimento; indicação é o crédito pago ao indicador; parceria é o fee
por cadastro. LTV usa receita, não margem: não desconta custo de conteúdo.

---

## 3. Receita e reajustes

*A pergunta: a receita cresce por mais assinantes, por mais receita por assinante, ou pelos dois?*

Receita por assinante e churn voluntário nos 3 meses antes e nos 3 meses depois de cada reajuste de preço:

| Reajuste | Receita / assinante antes | Depois | Variação | Churn voluntário antes | Depois | Variação |
|---|---:|---:|---:|---:|---:|---:|
| ago/2024 | R$ 33,26 | R$ 37,10 | +11,5% | 3,9% | 4,6% | +0,6 p.p. |
| set/2025 | R$ 39,33 | R$ 42,50 | +8,1% | 4,6% | 4,4% | -0,3 p.p. |

Cobrança de membro extra (desde 10/03/2025): R$ 38.447 nos últimos 12 meses, 0,5% da receita paga.
Descontos de cupom: R$ 226.456, 2,9% do preço de tabela (receita paga + descontos − membro extra),
contra 3,5% nos 12 meses anteriores.

---

## 4. Planos e retenção (últimos 12 meses)

*A pergunta: quem está saindo, por quê, e quanto disso dá para evitar?* O churn involuntário (falha de pagamento) foi
**35%** das saídas, cerca de **R$ 10.836** de receita recorrente perdida por mês: é a parte
mais evitável, com retentativa no cartão, lembrete no boleto e migração para cobrança automática.

| Plano | Assinantes (fim) | Receita paga | Receita / assinante / mês | Churn mensal | Horas / conta / mês | NPS |
|---|---:|---:|---:|---:|---:|---:|
| **Básico com anúncios** | 5.282 | R$ 1.296.184 | R$ 22,09 | 6,2% | 11,3 h | 25 |
| **Padrão** | 4.388 | R$ 2.207.726 | R$ 46,23 | 5,3% | 13,7 h | 22 |
| **Premium** | 6.700 | R$ 4.115.293 | R$ 59,66 | 4,0% | 26,1 h | 36 |

| Método de pagamento | Assinantes (média) | Churn involuntário | Falha de cobrança | Churn voluntário |
|---|---:|---:|---:|---:|
| **Boleto** | 1.063 | 3,3% | 3,2% | 3,2% |
| **Cartão** | 11.195 | 1,6% | 11,2% | 3,3% |
| **Pix** | 2.098 | 2,2% | 2,2% | 3,5% |

Motivos de cancelamento (pesquisa opcional, 12 meses): Pouco uso 63%; Preço 22%; Financeiro 4%; Outro 4%; Temporário 3%.

Tickets de suporte (12 meses, categorias normalizadas): Acesso e login 29%; Pagamento 17%; Cancelamento 13%; Outros 13%; Conteúdo 12%.

---

## 5. Qualidade dos dados

O banco tem imperfeições de propósito. Cada uma foi encontrada nos dados, contada e tratada antes de virar métrica:

| Achado | Linhas | De | Tratamento |
|---|---:|---:|---|
| Timestamps em UTC: cadastros que caem no mês seguinte quando lidos em UTC | 218 | 29.829 (0,7%) | Todo corte de mês usa o horário de Brasília (UTC−3). |
| Assinaturas encerradas antes de começar | 1 | 34.345 (0,0%) | Excluídas de estoque e fluxo. |
| Assinaturas sem evento de criação ou reativação | 12 | — | Mantidas: a tabela de assinaturas é a fonte do início; o evento faltante é falha do log. |
| Faturas marcadas como pagas sem pagamento aprovado registrado | 1.173 | 296.458 (0,4%) | Contadas como receita (a fatura é o livro-razão); o pagamento faltante é falha do log de cobrança. |
| Reproduções com tempo gravado em milissegundos (app 6.x, celular e tablet) | 1.171.812 | 5.662.065 (20,7%) | Divididas por 1.000: a razão contra a duração de relógio é exatamente 1.000×. |
| Reproduções com duração negativa (fim antes do início) | 2.728 | 5.662.065 (0,0%) | Excluídas do tempo assistido. |
| Reproduções duplicadas (mesmo perfil, título e início) | 1 | 5.662.065 (0,0%) | Uma cópia mantida. |
| Tipos de dispositivo escritos de várias formas (Celular, mobile, smartphone, TABLET, 'tv ', navegador…) | 1.832 | 72.902 (2,5%) | Registrado; nenhuma métrica deste relatório usa o tipo de dispositivo. Para usar: mapear para celular, tablet, tv e web. |
| Categorias de ticket escritas de várias formas (cobrança, COBRANCA, pagto, Acesso/Login…) | 331 | 8.923 (3,7%) | Mapeadas para 7 categorias canônicas. |
| Ferramenta de atribuição: cadastros creditados à busca paga acima dos cadastros reais do canal | 1.878 | 5.463 (34,4%) | CAC calculado com o canal gravado na conta; a atribuição aparece ao lado, só para comparação. |

---

## 6. Método

- Datas em horário de Brasília (UTC−3). Assinantes ativos = assinaturas vigentes no último instante do mês; o plano é o vigente naquele
  momento, reconstruído dos upgrades e downgrades.
- Churn mensal = encerramentos / assinantes ativos no início de cada mês, somados no período. Toda taxa é razão de somas.
- Receita paga = faturas quitadas, pelo mês de emissão. Receita recorrente = faturas mensais no mês do ciclo; anuais divididas em 12.
- LTV (receita) = receita por assinante / churn mensal. Período inteiro (out/2023–out/2026): 29.828 novas assinaturas,
  17.974 encerramentos, R$ 13.749.309 de receita paga.
- Um número sobre menos de 30 eventos é marcado com \* e não sustenta conclusão.
- O build confere o cubo contra as tabelas brutas e para se algo divergir: receita paga = soma das faturas pagas; cadastros = contas com 1ª assinatura válida; assinantes ativos no último mês = assinaturas não encerradas; encerramentos = assinaturas encerradas; investimento = soma do investimento diário.
