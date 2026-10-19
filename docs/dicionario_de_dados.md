# Dicionário de dados — Cinelume

## Convenções gerais

- **Tipos.**
  - "MySQL" é o tipo da coluna em [`schema.sql`](../schema.sql); "Parquet" é o tipo físico em `dados/parquet`.
  - No CSV, nulos aparecem como campo vazio; datas como `AAAA-MM-DD`; data-hora como `AAAA-MM-DD HH:MM:SS`.
- **Fuso.**
  - Toda coluna de data-hora (`DATETIME` / `timestamp[s]`) está em **UTC**, com precisão de segundos.
  - Colunas `DATE` representam o dia civil no horário de Brasília (UTC−3).
- **Moeda.** Valores monetários em **BRL**: `DECIMAL(10,2)` no MySQL, `double` arredondado a 2 casas no Parquet.
- **Flags.** `TINYINT`/`int8` com valores `0` (não) ou `1` (sim).
- **Chaves.**
  - **PK** = chave primária; **UK** = única; **FK → tabela** = chave estrangeira declarada.
  - **Lógica → tabela** = referência sem `FOREIGN KEY` declarada (ligações entre logs).
- **Volume.** Ordem de grandeza por escala de geração: `small` (≈6 mil contas), `medium` (≈30 mil) e `full` (≈120 mil). Os números exatos dependem da semente.

---

## 1. Aquisição

### `canais`
**Propósito:** canais de aquisição de clientes. **Granularidade:** uma linha por canal. **Volume:** 6 em todas as escalas.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| canal_id | SMALLINT / int16 | não | PK | — | 1–6 | Identificador do canal. |
| codigo | VARCHAR(30) / string | não | UK | — | `organico`, `busca_paga`, `social_pago`, `indicacao`, `parceria_operadora`, `tv` | Código estável do canal. |
| nome | VARCHAR(60) / string | não | — | — | — | Nome de exibição. |
| tipo | VARCHAR(20) / string | não | — | — | `organico`, `pago`, `indicacao`, `parceria` | Natureza do canal. |
| pago | TINYINT / int8 | não | — | flag | 0, 1 | 1 se o canal tem compra de mídia. |

**Índices e constraints:** PK(`canal_id`); UNIQUE(`codigo`); CHECK `pago IN (0,1)`.

### `investimento_diario`
**Propósito:** investimento de marketing e métricas de mídia por canal e dia. **Granularidade:** uma linha por canal × dia (o canal `parceria_operadora` só aparece a partir de 01/03/2024, início da parceria). **Volume:** ≈6,6 mil linhas em qualquer escala; os valores escalam com o número de contas.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| data | DATE / date32 | não | PK | dia (Brasília) | 2023-10-01 a 2026-10-31 | Dia de referência. |
| canal_id | SMALLINT / int16 | não | PK, FK → canais | — | 1–6 | Canal. |
| investimento_brl | DECIMAL(12,2) / double | não | — | BRL | ≥ 0 | Valor investido no dia: mídia (busca, social, TV), fee por cadastro (parceria) ou crédito de indicação. Zero no orgânico. |
| impressoes | BIGINT / int64 | sim | — | contagem | ≥ 0 | Impressões de anúncio. Nulo onde não se aplica (orgânico, indicação, parceria). |
| cliques | INT / int32 | sim | — | contagem | ≥ 0 | Cliques em anúncio. Nulo onde não se aplica (orgânico, indicação, parceria, TV). |
| cadastros_atribuidos | INT / int32 | não | — | contagem | ≥ 0 | Cadastros que a ferramenta de atribuição (último clique / código promocional) creditou ao canal no dia. |

**Índices e constraints:** PK(`data`, `canal_id`); INDEX(`canal_id`, `data`); FK `canal_id` → `canais`; CHECK `investimento_brl >= 0`.

---

## 2. Produto e preço

### `planos`
**Propósito:** planos comercializados. **Granularidade:** uma linha por plano. **Volume:** 3.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| plano_id | SMALLINT / int16 | não | PK | — | 1, 2, 3 | Identificador do plano. |
| codigo | VARCHAR(30) / string | não | UK | — | `basico_anuncios`, `padrao`, `premium` | Código do plano. |
| nome | VARCHAR(60) / string | não | — | — | — | Nome comercial. |
| com_anuncios | TINYINT / int8 | não | — | flag | 0, 1 | Plano exibe anúncios. |
| resolucao_maxima | VARCHAR(10) / string | não | — | — | `720p`, `1080p`, `4k` | Resolução máxima do plano. |
| telas_simultaneas | TINYINT / int8 | não | — | telas | 2, 4 | Reproduções simultâneas permitidas. |
| max_perfis | TINYINT / int8 | não | — | perfis | 5 | Perfis por conta. |
| permite_membro_extra | TINYINT / int8 | não | — | flag | 0, 1 | Plano aceita membro extra pago. |

**Índices e constraints:** PK(`plano_id`); UNIQUE(`codigo`).

### `precos`
**Propósito:** tabela de preços com vigência (os reajustes criam novas linhas). **Granularidade:** uma linha por item × plano × periodicidade × vigência. **Volume:** 20.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| preco_id | INT / int32 | não | PK | — | — | Identificador do preço. |
| plano_id | SMALLINT / int16 | sim | FK → planos | — | 1–3 | Plano. Nulo para o item `membro_extra`. |
| item | VARCHAR(20) / string | não | — | — | `assinatura`, `membro_extra` | O que é cobrado. |
| periodicidade | VARCHAR(10) / string | não | — | — | `mensal`, `anual` | Ciclo de cobrança. |
| valor_brl | DECIMAL(10,2) / double | não | — | BRL por ciclo | > 0 | Preço cheio do ciclo. |
| vigencia_inicio | DATE / date32 | não | — | dia (Brasília) | — | Primeiro dia de vigência (inclusive). |
| vigencia_fim | DATE / date32 | sim | — | dia (Brasília) | — | Último dia de vigência (inclusive). Nulo = vigente. |

**Índices e constraints:** PK(`preco_id`); INDEX(`plano_id`, `periodicidade`, `vigencia_inicio`); FK `plano_id` → `planos`; CHECK `valor_brl > 0`.

**Regra de negócio:** a fatura usa o preço vigente na data de início do ciclo cobrado.

---

## 3. Contas

### `contas`
**Propósito:** cadastro do titular. **Granularidade:** uma linha por conta (nunca é apagada). **Volume:** ≈6 mil / 30 mil / 120 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| conta_id | INT / int32 | não | PK | — | — | Identificador da conta (cresce com a data de cadastro). |
| email | VARCHAR(120) / string | não | UK | — | — | E-mail de login (fictício). |
| nome_titular | VARCHAR(120) / string | não | — | — | — | Nome do titular (fictício). |
| cpf | VARCHAR(14) / string | não | UK | — | formato `000.000.000-00` | CPF do titular (fictício). |
| telefone | VARCHAR(25) / string | sim | — | — | — | Telefone informado no cadastro (opcional). |
| data_nascimento | DATE / date32 | sim | — | dia | — | Data de nascimento informada (opcional). |
| cep | VARCHAR(9) / string | sim | — | — | formato `00000-000` | CEP de cobrança (opcional). |
| cidade | VARCHAR(80) / string | não | — | — | — | Cidade de cobrança. |
| uf | VARCHAR(30) / string | não | — | — | sigla da UF com 2 letras maiúsculas (`SP`, `RJ`, …) | Unidade da federação de cobrança. |
| criada_em | DATETIME / timestamp[s] | não | — | UTC | 2023-10-01 a 2026-10-31 | Momento do cadastro. |
| canal_aquisicao_id | SMALLINT / int16 | não | FK → canais | — | 1–6 | Canal de aquisição registrado no cadastro. |
| indicada_por_conta_id | INT / int32 | sim | FK → contas | — | — | Conta que fez a indicação (programa de indicação). |
| aceita_marketing | TINYINT / int8 | não | — | flag | 0, 1 | Consentimento para comunicações de marketing por e-mail. |

**Índices e constraints:** PK(`conta_id`); UNIQUE(`email`); UNIQUE(`cpf`); INDEX(`criada_em`); INDEX(`canal_aquisicao_id`); FK `canal_aquisicao_id` → `canais`; FK `indicada_por_conta_id` → `contas`.

### `perfis`
**Propósito:** perfis de uso dentro da conta. **Granularidade:** uma linha por perfil (perfis excluídos permanecem, com `excluido_em`). **Volume:** ≈15 mil / 77 mil / 300 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| perfil_id | INT / int32 | não | PK | — | — | Identificador do perfil. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta dona do perfil. |
| nome | VARCHAR(40) / string | não | — | — | — | Nome do perfil. |
| infantil | TINYINT / int8 | não | — | flag | 0, 1 | Perfil infantil (catálogo restrito). |
| principal | TINYINT / int8 | não | — | flag | 0, 1 | Perfil do titular, criado no cadastro (exatamente um por conta). |
| membro_extra | TINYINT / int8 | não | — | flag | 0, 1 | Perfil cadastrado como membro extra pago (fora do domicílio). |
| telemetria_detalhada | TINYINT / int8 | não | — | flag | 0, 1 | Perfil na amostra de telemetria detalhada; só esses perfis enviam `heartbeats_reproducao`. |
| criado_em | DATETIME / timestamp[s] | não | — | UTC | — | Criação do perfil. |
| excluido_em | DATETIME / timestamp[s] | sim | — | UTC | — | Exclusão do perfil. Nulo = ativo. |

**Índices e constraints:** PK(`perfil_id`); INDEX(`conta_id`); FK `conta_id` → `contas`.

### `dispositivos`
**Propósito:** dispositivos registrados na conta. **Granularidade:** uma linha por dispositivo. **Volume:** ≈15 mil / 73 mil / 290 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| dispositivo_id | INT / int32 | não | PK | — | — | Identificador do dispositivo. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta em que o dispositivo foi registrado. |
| tipo | VARCHAR(20) / string | não | — | — | `tv`, `celular`, `web`, `tablet` | Classe do dispositivo. |
| plataforma | VARCHAR(20) / string | não | — | — | `tv_os_a`, `tv_os_b`, `mobile_os_a`, `mobile_os_b`, `web` | Sistema/plataforma do app (nomes anonimizados). |
| registrado_em | DATETIME / timestamp[s] | não | — | UTC | — | Primeiro login do dispositivo. |

**Índices e constraints:** PK(`dispositivo_id`); INDEX(`conta_id`); FK `conta_id` → `contas`.

---

## 4. Assinatura

### `assinaturas`
**Propósito:** períodos contínuos de assinatura. **Granularidade:** uma linha por período. O cadastro abre a primeira; cada reativação abre uma nova. **Volume:** ≈6,5 mil / 32 mil / 130 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| assinatura_id | INT / int32 | não | PK | — | — | Identificador da assinatura. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta assinante. |
| plano_id | SMALLINT / int16 | não | FK → planos | — | 1–3 | Plano atual (ou o último, se encerrada). O histórico está em `assinatura_eventos`. |
| periodicidade | VARCHAR(10) / string | não | — | — | `mensal`, `anual` | Ciclo de cobrança. |
| metodo_pagamento | VARCHAR(10) / string | não | — | — | `cartao`, `pix`, `boleto` | Método de pagamento atual (ou o último). |
| status | VARCHAR(25) / string | não | — | — | `trial`, `ativa`, `inadimplente`, `cancelamento_agendado`, `encerrada` | Situação em 31/10/2026 23:59:59 UTC. |
| iniciada_em | DATETIME / timestamp[s] | não | — | UTC | — | Início do período de assinatura. |
| trial_fim_em | DATETIME / timestamp[s] | sim | — | UTC | — | Fim do trial de 7 dias, se houve trial. |
| cancelamento_solicitado_em | DATETIME / timestamp[s] | sim | — | UTC | — | Momento em que o cliente pediu o cancelamento. |
| encerrada_em | DATETIME / timestamp[s] | sim | — | UTC | — | Fim do acesso (fim do ciclo pago, fim do trial ou encerramento por falta de pagamento). |
| tipo_encerramento | VARCHAR(15) / string | sim | — | — | `voluntario`, `involuntario` | Voluntário = pedido do cliente; involuntário = falta de pagamento. Nulo se não encerrada. |
| renovacao_automatica | TINYINT / int8 | não | — | flag | 0, 1 | 1 para cartão (cobrança automática); 0 para Pix/boleto (pagamento manual a cada ciclo). |
| assinatura_anterior_id | INT / int32 | sim | FK → assinaturas | — | — | Assinatura encerrada que esta reativa. |

**Índices e constraints:** PK(`assinatura_id`); INDEX(`conta_id`, `iniciada_em`); INDEX(`status`); INDEX(`encerrada_em`); FKs `conta_id` → `contas`, `plano_id` → `planos`, `assinatura_anterior_id` → `assinaturas`.

### `assinatura_eventos`
**Propósito:** histórico de eventos do ciclo de vida da assinatura. **Granularidade:** uma linha por evento. **Volume:** ≈23 mil / 115 mil / 450 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| evento_id | BIGINT / int64 | não | PK | — | — | Identificador do evento (ordem cronológica). |
| assinatura_id | INT / int32 | não | FK → assinaturas | — | — | Assinatura afetada. |
| tipo | VARCHAR(40) / string | não | — | — | `assinatura_criada`, `trial_iniciado`, `trial_convertido`, `upgrade`, `downgrade`, `metodo_pagamento_alterado`, `inadimplencia_iniciada`, `inadimplencia_resolvida`, `cancelamento_solicitado`, `encerrada`, `reativada`, `membro_extra_adicionado`, `membro_extra_removido` | Tipo do evento. |
| ocorrido_em | DATETIME / timestamp[s] | não | — | UTC | — | Momento do evento. |
| plano_anterior_id | SMALLINT / int16 | sim | FK → planos | — | 1–3 | Plano antes da mudança (`upgrade`/`downgrade`). |
| plano_novo_id | SMALLINT / int16 | sim | FK → planos | — | 1–3 | Plano após a mudança, ou plano contratado (`assinatura_criada`, `reativada`). |
| origem | VARCHAR(10) / string | não | — | — | `app`, `web`, `suporte`, `sistema` | Onde o evento foi originado. |

**Índices e constraints:** PK(`evento_id`); INDEX(`assinatura_id`, `ocorrido_em`); INDEX(`tipo`, `ocorrido_em`); FKs para `assinaturas` e `planos`.

### `pesquisa_cancelamento`
**Propósito:** respostas à pesquisa opcional exibida no fluxo de cancelamento. **Granularidade:** uma linha por resposta. **Volume:** ≈900 / 4,7 mil / 19 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| resposta_id | INT / int32 | não | PK | — | — | Identificador da resposta. |
| assinatura_id | INT / int32 | não | FK → assinaturas | — | — | Assinatura cancelada. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta. |
| respondida_em | DATETIME / timestamp[s] | não | — | UTC | — | Momento da resposta. |
| motivo_principal | VARCHAR(30) / string | não | — | — | `preco`, `pouco_uso`, `catalogo`, `terminei_o_que_queria`, `problemas_tecnicos`, `compartilhamento`, `financeiro`, `temporario`, `outro` | Motivo escolhido (opção única). |
| comentario | VARCHAR(300) / string | sim | — | — | texto livre | Comentário opcional. |
| probabilidade_voltar | TINYINT / int8 | sim | — | escala 0–10 | 0–10 | "De 0 a 10, qual a chance de voltar?" (opcional). |

**Índices e constraints:** PK(`resposta_id`); INDEX(`assinatura_id`); INDEX(`conta_id`); FKs para `assinaturas` e `contas`; CHECK `probabilidade_voltar BETWEEN 0 AND 10`.

---

## 5. Cobrança e promoções

### `cupons`
**Propósito:** cupons e promoções. **Granularidade:** uma linha por cupom. **Volume:** 14.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| cupom_id | INT / int32 | não | PK | — | — | Identificador do cupom. |
| codigo | VARCHAR(30) / string | não | UK | — | — | Código digitado/aplicado. |
| descricao | VARCHAR(120) / string | não | — | — | — | Descrição comercial. |
| tipo_desconto | VARCHAR(15) / string | não | — | — | `percentual`, `valor_fixo` | Forma do desconto. |
| valor_desconto | DECIMAL(10,2) / double | não | — | % ou BRL | — | Percentual (0–100) ou valor em BRL, conforme `tipo_desconto`. |
| duracao_ciclos | SMALLINT / int16 | não | — | ciclos de cobrança | ≥ 1 | Quantas faturas consecutivas recebem o desconto. |
| valido_de | DATE / date32 | não | — | dia (Brasília) | — | Início da janela de resgate. |
| valido_ate | DATE / date32 | sim | — | dia (Brasília) | — | Fim da janela de resgate. Nulo = sem prazo. |
| canal_id | SMALLINT / int16 | sim | FK → canais | — | — | Canal ao qual o cupom é restrito, se houver. |
| apenas_novos | TINYINT / int8 | não | — | flag | 0, 1 | Válido somente em novos cadastros. |

**Índices e constraints:** PK(`cupom_id`); UNIQUE(`codigo`); FK `canal_id` → `canais`.

### `cupom_resgates`
**Propósito:** aplicação de um cupom a uma assinatura. **Granularidade:** uma linha por resgate. **Volume:** ≈2 mil / 11 mil / 43 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| resgate_id | INT / int32 | não | PK | — | — | Identificador do resgate. |
| cupom_id | INT / int32 | não | FK → cupons | — | — | Cupom resgatado. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta. |
| assinatura_id | INT / int32 | não | FK → assinaturas | — | — | Assinatura que recebe o desconto. |
| resgatado_em | DATETIME / timestamp[s] | não | — | UTC | — | Momento do resgate. |

**Índices e constraints:** PK(`resgate_id`); INDEX(`cupom_id`); INDEX(`conta_id`); FKs para `cupons`, `contas` e `assinaturas`.

### `faturas`
**Propósito:** cobrança de cada ciclo da assinatura. **Granularidade:** uma linha por ciclo cobrado. **Volume:** ≈60 mil / 290 mil / 1,2 milhão.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| fatura_id | BIGINT / int64 | não | PK | — | — | Identificador da fatura. |
| assinatura_id | INT / int32 | não | FK → assinaturas | — | — | Assinatura cobrada. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta devedora. |
| preco_id | INT / int32 | não | FK → precos | — | — | Preço de tabela aplicado ao ciclo. |
| cupom_resgate_id | INT / int32 | sim | FK → cupom_resgates | — | — | Resgate de cupom que gerou o desconto. |
| periodo_inicio | DATE / date32 | não | — | dia (Brasília) | — | Primeiro dia do ciclo coberto. |
| periodo_fim | DATE / date32 | não | — | dia (Brasília) | ≥ `periodo_inicio` | Último dia do ciclo coberto. |
| emitida_em | DATETIME / timestamp[s] | não | — | UTC | — | Emissão da fatura. |
| vencimento_em | DATE / date32 | não | — | dia (Brasília) | — | Vencimento (cartão: dia da emissão; Pix/boleto: D+3). |
| valor_bruto | DECIMAL(10,2) / double | não | — | BRL | > 0 | Preço de tabela do plano no ciclo. |
| valor_desconto | DECIMAL(10,2) / double | não | — | BRL | ≥ 0 | Desconto de cupom. |
| valor_membro_extra | DECIMAL(10,2) / double | não | — | BRL | ≥ 0 | Cobrança de membro extra no ciclo. |
| valor_total | DECIMAL(10,2) / double | não | — | BRL | ≥ 0 | `valor_bruto − valor_desconto + valor_membro_extra`. |
| status | VARCHAR(15) / string | não | — | — | `paga`, `aberta`, `vencida`, `cancelada`, `reembolsada`, `estornada` | Situação em 31/10/2026. `vencida` = não paga no prazo; `estornada` = contestada pelo portador do cartão. |

**Índices e constraints:** PK(`fatura_id`); INDEX(`assinatura_id`, `periodo_inicio`); INDEX(`conta_id`, `emitida_em`); INDEX(`status`); FKs para `assinaturas`, `contas`, `precos` e `cupom_resgates`; CHECK `periodo_fim >= periodo_inicio`.

### `pagamentos`
**Propósito:** movimentos financeiros: cada tentativa de cobrança, reembolso ou contestação (chargeback). **Granularidade:** uma linha por movimento. **Volume:** ≈63 mil / 310 mil / 1,25 milhão.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| pagamento_id | BIGINT / int64 | não | PK | — | — | Identificador do movimento (ordem cronológica). |
| fatura_id | BIGINT / int64 | sim | FK → faturas | — | — | Fatura a que o movimento se refere. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta. |
| metodo | VARCHAR(10) / string | não | — | — | `cartao`, `pix`, `boleto` | Meio de pagamento. |
| tipo | VARCHAR(15) / string | não | — | — | `cobranca`, `reembolso`, `chargeback` | Natureza do movimento. |
| tentativa | SMALLINT / int16 | não | — | nº de ordem | ≥ 1 | Nº da tentativa na fatura. Cartão: 1 = cobrança original; 2, 3, 4 = retentativas em D+1, D+3, D+7. |
| processado_em | DATETIME / timestamp[s] | não | — | UTC | — | Processamento pelo gateway / confirmação de pagamento. |
| valor_brl | DECIMAL(10,2) / double | não | — | BRL | — | Valor do movimento; negativo em reembolso e chargeback. |
| status | VARCHAR(15) / string | não | — | — | `aprovado`, `recusado`, `expirado`, `contestado`, `processado` | Resultado. `expirado` = Pix/boleto gerado e não pago; `contestado` = chargeback; `processado` = reembolso efetuado. |
| codigo_recusa | VARCHAR(30) / string | sim | — | — | `saldo_insuficiente`, `cartao_expirado`, `nao_autorizado`, `erro_emissor`, `suspeita_fraude` | Motivo informado pelo emissor quando `status = recusado`. |

**Índices e constraints:** PK(`pagamento_id`); INDEX(`fatura_id`); INDEX(`conta_id`, `processado_em`); FKs para `faturas` e `contas`; CHECK `tentativa >= 1`.

---

## 6. Catálogo

### `generos`
**Propósito:** gêneros do catálogo. **Granularidade:** uma linha por gênero. **Volume:** 16.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| genero_id | SMALLINT / int16 | não | PK | — | 1–16 | Identificador. |
| nome | VARCHAR(40) / string | não | UK | — | Ação, Aventura, Animação, Comédia, Crime, Documentário, Drama, Fantasia, Ficção Científica, Infantil, Musical, Romance, Suspense, Terror, Reality, Esporte | Nome do gênero. |

### `estudios`
**Propósito:** estúdios produtores ou licenciadores (fictícios). **Granularidade:** uma linha por estúdio. **Volume:** 45.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| estudio_id | INT / int32 | não | PK | — | — | Identificador. O id 1 é a produtora própria da Cinelume (originais). |
| nome | VARCHAR(80) / string | não | — | — | — | Nome do estúdio. |
| pais | CHAR(2) / string | não | — | ISO 3166-1 alfa-2 | — | País sede. |

### `pessoas`
**Propósito:** pessoas do elenco e direção (fictícias). **Granularidade:** uma linha por pessoa. **Volume:** 5 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| pessoa_id | INT / int32 | não | PK | — | — | Identificador. |
| nome | VARCHAR(120) / string | não | — | — | — | Nome artístico. |

### `titulos`
**Propósito:** filmes e séries do catálogo. **Granularidade:** uma linha por título. **Volume:** 3 mil (≈2,3 mil filmes e 700 séries) em todas as escalas.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| titulo_id | INT / int32 | não | PK | — | — | Identificador. |
| tipo | VARCHAR(10) / string | não | — | — | `filme`, `serie` | Tipo de título. |
| nome | VARCHAR(150) / string | não | UK | — | — | Título em português. |
| ano_lancamento | SMALLINT / int16 | não | — | ano | — | Ano de lançamento original. |
| duracao_min | SMALLINT / int16 | sim | — | minutos | > 0 | Duração do filme. Nulo para séries (ver `episodios`). |
| classificacao_indicativa | VARCHAR(3) / string | não | — | — | `L`, `10`, `12`, `14`, `16`, `18` | Classificação indicativa. |
| original | TINYINT / int8 | não | — | flag | 0, 1 | Produção original Cinelume (1) ou licenciada (0). |
| estudio_id | INT / int32 | não | FK → estudios | — | — | Estúdio produtor/licenciador. |
| idioma_original | CHAR(2) / string | não | — | ISO 639-1 | `pt`, `en`, `es`, `ko`, `ja`, `fr` | Idioma original. |
| pais_origem | CHAR(2) / string | não | — | ISO 3166-1 alfa-2 | — | País de origem. |
| sinopse | VARCHAR(400) / string | não | — | — | — | Sinopse curta. |

**Índices e constraints:** PK(`titulo_id`); UNIQUE(`nome`); INDEX(`tipo`); FK `estudio_id` → `estudios`; CHECK `tipo IN ('filme','serie')`.

### `titulo_generos`
**Propósito:** associação título–gênero. **Granularidade:** uma linha por título × gênero (1 principal + até 1 secundário). **Volume:** ≈4,5 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| titulo_id | INT / int32 | não | PK, FK → titulos | — | — | Título. |
| genero_id | SMALLINT / int16 | não | PK, FK → generos | — | — | Gênero. |
| principal | TINYINT / int8 | não | — | flag | 0, 1 | Gênero principal do título (exatamente um por título). |

**Índices e constraints:** PK(`titulo_id`, `genero_id`); INDEX(`genero_id`).

### `titulo_elenco`
**Propósito:** elenco e direção por título. **Granularidade:** uma linha por título × pessoa × função. **Volume:** ≈21 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| titulo_id | INT / int32 | não | PK, FK → titulos | — | — | Título. |
| pessoa_id | INT / int32 | não | PK, FK → pessoas | — | — | Pessoa. |
| funcao | VARCHAR(15) / string | não | PK | — | `elenco`, `direcao` | Papel no título. |
| ordem | SMALLINT / int16 | não | — | posição | ≥ 1 | Ordem de crédito. |

**Índices e constraints:** PK(`titulo_id`, `pessoa_id`, `funcao`); INDEX(`pessoa_id`).

### `episodios`
**Propósito:** episódios das séries. **Granularidade:** uma linha por episódio. **Volume:** ≈25 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| episodio_id | INT / int32 | não | PK | — | — | Identificador. |
| titulo_id | INT / int32 | não | FK → titulos | — | — | Série (`titulos.tipo = 'serie'`). |
| temporada | SMALLINT / int16 | não | — | nº | ≥ 1 | Temporada. |
| numero | SMALLINT / int16 | não | — | nº | ≥ 1 | Número do episódio na temporada. |
| nome | VARCHAR(120) / string | não | — | — | — | Título do episódio. |
| duracao_min | SMALLINT / int16 | não | — | minutos | > 0 | Duração. |
| disponivel_desde | DATETIME / timestamp[s] | não | — | UTC | — | Liberação do episódio no catálogo. Pode ser anterior a out/2023. |

**Índices e constraints:** PK(`episodio_id`); UNIQUE(`titulo_id`, `temporada`, `numero`); FK `titulo_id` → `titulos`.

### `catalogo_disponibilidade`
**Propósito:** janelas em que cada título esteve no catálogo. **Granularidade:** uma linha por janela; um título pode ter mais de uma. **Volume:** ≈3,1 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| disponibilidade_id | INT / int32 | não | PK | — | — | Identificador. |
| titulo_id | INT / int32 | não | FK → titulos | — | — | Título. |
| entrada_em | DATE / date32 | não | — | dia (Brasília) | — | Primeiro dia disponível (pode ser anterior a out/2023). |
| saida_em | DATE / date32 | sim | — | dia (Brasília) | > `entrada_em` | Primeiro dia **indisponível** (fim de licença). Nulo = ainda disponível em 31/10/2026. |
| tipo_licenca | VARCHAR(15) / string | não | — | — | `original`, `licenciado` | Tipo de direito. |

**Índices e constraints:** PK(`disponibilidade_id`); INDEX(`titulo_id`, `entrada_em`); FK `titulo_id` → `titulos`; CHECK `saida_em IS NULL OR saida_em > entrada_em`.

---

## 7. Logs de uso do produto

### `sessoes_app`
**Propósito:** sessões de uso do app (abertura até fechamento ou inatividade). **Granularidade:** uma linha por sessão. **Volume:** ≈1 milhão / 5 milhões / 20 milhões.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| sessao_id | BIGINT / int64 | não | PK | — | — | Identificador da sessão. |
| perfil_id | INT / int32 | não | FK → perfis | — | — | Perfil em uso. |
| dispositivo_id | INT / int32 | não | FK → dispositivos | — | — | Dispositivo. |
| versao_app | VARCHAR(10) / string | não | — | semver | ver tabela de versões abaixo | Versão do app na sessão. |
| inicio_em | DATETIME / timestamp[s] | não | — | UTC (servidor) | — | Início da sessão. |
| fim_em | DATETIME / timestamp[s] | sim | — | UTC (servidor) | ≥ `inicio_em` | Fim da sessão. |
| ip | VARCHAR(45) / string | não | — | IPv4 | — | IP de origem (fictício). |
| regiao | VARCHAR(20) / string | sim | — | — | `Norte`, `Nordeste`, `Centro-Oeste`, `Sudeste`, `Sul` | Região geográfica estimada pelo IP. |

**Índices e constraints:** PK(`sessao_id`); INDEX(`perfil_id`, `inicio_em`); INDEX(`dispositivo_id`); INDEX(`inicio_em`); FKs para `perfis` e `dispositivos`.

**Versões do app** (data de publicação nas lojas; a atualização de cada dispositivo ocorre depois): 4.0.0 (2023-09-04), 4.1.0 (2023-11-20), 4.2.0 (2024-02-26), 4.3.0 (2024-05-14), 4.3.1 (2024-06-25), 4.4.0 (2024-09-16), 4.5.0 (2024-11-25), 5.0.0 (2025-02-04), 5.1.0 (2025-05-12), 5.2.0 (2025-08-19), 5.3.0 (2025-11-10), 6.0.0 (2026-02-03), 6.1.0 (2026-05-05), 6.2.0 (2026-08-24).

### `eventos_app`
**Propósito:** eventos de interface emitidos pelo app. O catálogo de eventos está em [`eventos_app.md`](eventos_app.md). **Granularidade:** uma linha por evento recebido. **Volume:** ≈5 milhões / 25–29 milhões / 100–115 milhões.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| evento_id | BIGINT / int64 | não | PK | — | — | Identificador (ordem de recebimento). |
| sessao_id | BIGINT / int64 | não | lógica → sessoes_app | — | — | Sessão em que o evento ocorreu. |
| perfil_id | INT / int32 | não | FK → perfis | — | — | Perfil. |
| seq | INT / int32 | não | — | nº de ordem | ≥ 1 | Sequência do evento dentro da sessão (1, 2, 3…). |
| tipo_evento | VARCHAR(40) / string | não | — | — | ver [`eventos_app.md`](eventos_app.md) | Nome do evento. |
| ocorrido_em | DATETIME / timestamp[s] | não | — | UTC (relógio do dispositivo, normalizado pelo SDK) | — | Momento em que o evento aconteceu no dispositivo. |
| recebido_em | DATETIME / timestamp[s] | não | — | UTC (servidor) | — | Momento em que o coletor recebeu o evento. |
| titulo_id | INT / int32 | sim | FK → titulos | — | — | Título envolvido, quando aplicável. |
| fileira | VARCHAR(40) / string | sim | — | — | `em_alta`, `continuar_assistindo`, `recomendados_para_voce`, `novidades`, `originais_cinelume`, `porque_voce_assistiu`, `top_10`, `minha_lista` | Fileira da home onde o título foi exibido (`impressao_titulo`). |
| posicao | SMALLINT / int16 | sim | — | posição (1 = mais à esquerda) | 1–40 | Posição do título na fileira. |
| termo_busca | VARCHAR(100) / string | sim | — | — | texto livre | Texto digitado (`busca`). |
| avaliacao | VARCHAR(10) / string | sim | — | — | `positiva`, `negativa` | Polegar para cima/baixo (`avaliacao`). |
| versao_app | VARCHAR(10) / string | não | — | semver | ver versões | Versão do app que emitiu o evento. |

**Índices e constraints:** PK(`evento_id`); INDEX(`sessao_id`, `seq`); INDEX(`perfil_id`, `ocorrido_em`); INDEX(`tipo_evento`, `recebido_em`); INDEX(`titulo_id`); FKs para `perfis` e `titulos`.

### `reproducoes`
**Propósito:** cada reprodução de um filme ou episódio, consolidada pelo serviço de playback. **Granularidade:** uma linha por reprodução (de play até stop, fim do conteúdo ou troca de conteúdo). **Volume:** ≈1,1 milhão / 5,4 milhões / 20–22 milhões.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| reproducao_id | BIGINT / int64 | não | PK | — | — | Identificador (ordem de início). |
| perfil_id | INT / int32 | não | FK → perfis | — | — | Perfil. |
| sessao_id | BIGINT / int64 | sim | lógica → sessoes_app | — | — | Sessão do app. |
| dispositivo_id | INT / int32 | não | FK → dispositivos | — | — | Dispositivo. |
| titulo_id | INT / int32 | não | FK → titulos | — | — | Filme ou série. |
| episodio_id | INT / int32 | sim | FK → episodios | — | — | Episódio (nulo para filmes). |
| inicio_em | DATETIME / timestamp[s] | não | — | UTC (servidor) | — | Início da reprodução. |
| fim_em | DATETIME / timestamp[s] | sim | — | UTC (servidor) | ≥ `inicio_em` | Fim da reprodução. |
| segundos_assistidos | BIGINT / int64 | não | — | **segundos** | ≥ 0 | Tempo efetivamente reproduzido (sem pausas). |
| percentual_concluido | DECIMAL(6,2) / double | não | — | % | 0–100 | Posição final / duração do conteúdo × 100. |
| qualidade_video | VARCHAR(10) / string | sim | — | — | `480p`, `720p`, `1080p`, `4k` | Qualidade predominante. |
| eventos_buffering | SMALLINT / int16 | não | — | contagem | ≥ 0 | Interrupções por rebuffering. |
| origem_autoplay | TINYINT / int8 | não | — | flag | 0, 1 | Iniciada automaticamente (próximo episódio). |
| origem_recomendacao | TINYINT / int8 | não | — | flag | 0, 1 | Iniciada a partir de fileira de recomendação. |
| versao_app | VARCHAR(10) / string | não | — | semver | ver versões | Versão do app. |

**Índices e constraints:** PK(`reproducao_id`); INDEX(`perfil_id`, `inicio_em`); INDEX(`titulo_id`, `inicio_em`); INDEX(`episodio_id`); INDEX(`sessao_id`); INDEX(`dispositivo_id`); FKs para `perfis`, `dispositivos`, `titulos` e `episodios`.

### `heartbeats_reproducao`
**Propósito:** pings do player a cada **60 segundos** durante a reprodução; é a fonte bruta do tempo assistido. Enviados apenas por perfis com `perfis.telemetria_detalhada = 1` (amostra de perfis). **Granularidade:** uma linha por ping. **Volume:** ≈2,5 milhões / 14 milhões / 55 milhões.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| heartbeat_id | BIGINT / int64 | não | PK | — | — | Identificador (ordem de envio). |
| reproducao_id | BIGINT / int64 | não | lógica → reproducoes | — | — | Reprodução. |
| enviado_em | DATETIME / timestamp[s] | não | — | UTC (relógio do dispositivo) | — | Momento do ping. |
| posicao_seg | BIGINT / int64 | não | — | **segundos** | ≥ 0 | Posição de reprodução relativa ao início da reprodução. |
| qualidade_video | VARCHAR(10) / string | não | — | — | `480p`, `720p`, `1080p`, `4k` | Qualidade no momento do ping. |
| em_buffering | TINYINT / int8 | não | — | flag | 0, 1 | Houve rebuffering no intervalo desde o ping anterior. |

**Índices e constraints:** PK(`heartbeat_id`); INDEX(`reproducao_id`, `enviado_em`).

---

## 8. Relacionamento

### `notificacoes`
**Propósito:** push e e-mails enviados, com abertura e clique. **Granularidade:** uma linha por envio. **Volume:** ≈75 mil / 370 mil / 1,5 milhão.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| notificacao_id | BIGINT / int64 | não | PK | — | — | Identificador (ordem de envio). |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta destinatária. |
| perfil_id | INT / int32 | sim | FK → perfis | — | — | Perfil destinatário (push). Nulo em e-mails à conta. |
| canal | VARCHAR(10) / string | não | — | — | `push`, `email` | Canal. |
| campanha | VARCHAR(40) / string | não | — | — | `novo_episodio`, `destaques_semana`, `reengajamento`, `falha_pagamento`, `aviso_reajuste`, `lancamento_original`, `winback` | Campanha/gatilho. |
| titulo_id | INT / int32 | sim | FK → titulos | — | — | Título divulgado, quando houver. |
| enviada_em | DATETIME / timestamp[s] | não | — | UTC | — | Envio. |
| aberta_em | DATETIME / timestamp[s] | sim | — | UTC | — | Primeira abertura. |
| clicada_em | DATETIME / timestamp[s] | sim | — | UTC | — | Primeiro clique. |

**Campanhas:**
- `novo_episodio`: push quando sai nova temporada de série acompanhada.
- `destaques_semana`: push semanal.
- `reengajamento`: e-mail mensal a contas sem uso recente.
- `falha_pagamento`: e-mail de cobrança recusada.
- `aviso_reajuste`: aviso de reajuste com 30 dias de antecedência.
- `lancamento_original`: estreia de grande original.
- `winback`: e-mail a ex-assinantes, com oferta.

**Índices e constraints:** PK(`notificacao_id`); INDEX(`conta_id`, `enviada_em`); INDEX(`campanha`, `enviada_em`); FKs para `contas`, `perfis` e `titulos`.

### `tickets_suporte`
**Propósito:** atendimentos abertos pelo cliente. **Granularidade:** uma linha por ticket. **Volume:** ≈1,6 mil / 8 mil / 33 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| ticket_id | INT / int32 | não | PK | — | — | Identificador. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta. |
| aberto_em | DATETIME / timestamp[s] | não | — | UTC | — | Abertura. |
| canal_atendimento | VARCHAR(10) / string | não | — | — | `chat`, `email`, `telefone` | Canal de contato. |
| categoria | VARCHAR(30) / string | não | — | — | `pagamento`, `cobranca`, `reproducao`, `acesso_login`, `conteudo`, `cancelamento`, `outros` | Categoria atribuída pelo atendente. |
| status | VARCHAR(25) / string | não | — | — | `aberto`, `resolvido`, `fechado_sem_resolucao` | Situação em 31/10/2026. |
| resolvido_em | DATETIME / timestamp[s] | sim | — | UTC | — | Resolução. |
| nota_satisfacao | TINYINT / int8 | sim | — | escala 1–5 | 1–5 | Avaliação do atendimento (opcional). |

**Índices e constraints:** PK(`ticket_id`); INDEX(`conta_id`, `aberto_em`); FK `conta_id` → `contas`; CHECK `nota_satisfacao BETWEEN 1 AND 5`.

### `nps`
**Propósito:** respostas à pesquisa NPS. A pesquisa é enviada a uma amostra aleatória de contas ativas nas ondas trimestrais (dias 5 a 18 de janeiro, abril, julho e outubro). **Granularidade:** uma linha por resposta. **Volume:** ≈800 / 4 mil / 16 mil.

| Coluna | MySQL / Parquet | Nulo | Chave | Unidade / fuso | Valores permitidos | Significado |
|---|---|---|---|---|---|---|
| resposta_id | INT / int32 | não | PK | — | — | Identificador. |
| conta_id | INT / int32 | não | FK → contas | — | — | Conta respondente. |
| respondida_em | DATETIME / timestamp[s] | não | — | UTC | — | Momento da resposta. |
| nota | TINYINT / int8 | não | — | escala 0–10 | 0–10 | "Qual a chance de recomendar a Cinelume?" |
| comentario | VARCHAR(300) / string | sim | — | — | texto livre | Comentário opcional. |
| canal_pesquisa | VARCHAR(10) / string | não | — | — | `email`, `app` | Onde foi respondida. |

**Índices e constraints:** PK(`resposta_id`); INDEX(`conta_id`, `respondida_em`); FK `conta_id` → `contas`; CHECK `nota BETWEEN 0 AND 10`.
