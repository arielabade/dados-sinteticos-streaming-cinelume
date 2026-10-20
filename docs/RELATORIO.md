# Cinelume · Relatório gerencial

**out/2023 a out/2026** · preparado por ABADE (Strategy · Data · Growth) · fonte: `dados_medium` (29.829 contas)

> **Dados sintéticos.** A Cinelume é uma empresa fictícia; todo cliente, real e resultado foi gerado pelo simulador deste repositório.
> O relatório demonstra o método, não descreve um negócio real.

**Versão interativa: [relatório estilo Power BI](https://arielabade.github.io/dados-sinteticos-streaming-cinelume/relatorio/)**, com navegador de meses, comparação com o período anterior ou com o ano
anterior, e filtros de canal, plano e método de pagamento. Este texto e o relatório interativo saem do mesmo cubo de dados
(`python relatorio/build.py`); aqui a leitura é dos **últimos 12 meses (nov/2025 a out/2026) contra os 12 anteriores**.

---

## 1. Resumo

| Indicador | nov/2025–out/2026 | nov/2024–out/2025 | Variação |
|---|---:|---:|---:|
| Assinantes ativos (fim) | 16.370 | 11.208 | +46,1% |
| Receita recorrente (último mês) | R$ 720.405 | R$ 480.140 | +50,0% |
| Receita paga | R$ 7.619.203 | R$ 4.552.818 | +67,4% |
| Novas assinaturas | 11.202 | 10.096 | +11,0% |
| Churn mensal | 5,1% | 5,9% | -0,8 p.p. |
| Receita por assinante / mês | R$ 43,30 | R$ 39,29 | +10,2% |
| Investimento em aquisição | R$ 397.148 | R$ 378.345 | +5,0% |
| CAC dos canais pagos (busca, social, TV) | R$ 66 | R$ 71 | -7,5% |
| CAC médio, todos os canais (inclui orgânico) | R$ 36 | R$ 38 | -5,3% |
| LTV (receita) / CAC dos canais pagos | 12,8x | 9,3x | +38,0% |
| NPS | 28 | 18 | +10 pts |

**O que os dados mostram**

- **Base e receita.** 16.370 assinantes ativos em out/2026 (+46,1% em 12 meses) e R$ 7.619.203 de receita paga nos últimos 12 meses (+67,4% contra os 12 anteriores).
- **Churn.** 5,1% ao mês nos últimos 12 meses (-0,8 p.p.); o involuntário, falha de pagamento, é 35% dos encerramentos, e Boleto tem o maior churn involuntário (3,3% ao mês).
- **Canais.** Entre os canais pagos, TV tem o CAC mais alto (R$ 110) e Busca paga o mais baixo (R$ 46).
- **Atribuição.** A ferramenta de atribuição credita à busca paga +33% cadastros em relação ao canal gravado na conta, e à TV -55%: decidir verba pela atribuição superinveste em busca e subinveste em TV.
- **Cancelamento.** Pouco uso é o motivo mais citado (63% das 2.347 respostas em 12 meses).
- **Uso.** Quem assina Premium assiste 26,1 h por mês, contra 11,3 h no Básico com anúncios.

---

## 2. Aquisição (últimos 12 meses)

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

Receita por assinante e churn voluntário nos 3 meses antes e nos 3 meses depois de cada reajuste de preço:

| Reajuste | Receita / assinante antes | Depois | Variação | Churn voluntário antes | Depois | Variação |
|---|---:|---:|---:|---:|---:|---:|
| ago/2024 | R$ 33,26 | R$ 37,10 | +11,5% | 3,9% | 4,6% | +0,6 p.p. |
| set/2025 | R$ 39,33 | R$ 42,50 | +8,1% | 4,6% | 4,4% | -0,3 p.p. |

Cobrança de membro extra (desde 10/03/2025): R$ 38.447 nos últimos 12 meses, 0,5% da receita paga.

---

## 4. Planos e retenção (últimos 12 meses)

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
