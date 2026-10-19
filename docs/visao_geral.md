# Visão geral do banco da Cinelume

A Cinelume é um serviço brasileiro **fictício** de streaming por assinatura. Este banco reúne os dados operacionais da empresa entre **01/10/2023 e 31/10/2026**: cadastro, assinatura, cobrança, catálogo, uso do produto, marketing e atendimento.

- Banco relacional MySQL 8, esquema `cinelume`, com 29 tabelas (DDL em [`../schema.sql`](../schema.sql)).
- Todos os campos `DATETIME`/`timestamp` estão em **UTC** e têm precisão de **segundos**.
- Campos `DATE` representam o dia civil (calendário de Brasília para datas de negócio, como vencimento e vigência).
- Valores monetários estão em **reais (BRL)**.
- Flags booleanas são `TINYINT` com valores `0`/`1`.
- Os mesmos dados existem em Parquet (`dados/parquet/<tabela>.parquet`) e em CSV gzip (`dados/csv/<tabela>.csv.gz`), com as colunas na mesma ordem do DDL.

Detalhes por coluna: [`dicionario_de_dados.md`](dicionario_de_dados.md). Diagrama: [`diagrama_er.md`](diagrama_er.md). Eventos do app: [`eventos_app.md`](eventos_app.md).

## Domínios

| Domínio | Tabelas | O que guarda |
|---|---|---|
| **Aquisição** | `canais`, `investimento_diario` | Canais de marketing e investimento diário com impressões, cliques e cadastros atribuídos. |
| **Contas** | `contas`, `perfis`, `dispositivos` | Titular da conta, até 5 perfis por conta e os dispositivos registrados. |
| **Produto e preço** | `planos`, `precos` | Planos (Básico com anúncios, Padrão, Premium) e tabela de preços com vigência. |
| **Assinatura** | `assinaturas`, `assinatura_eventos`, `pesquisa_cancelamento` | Cada período contínuo de assinatura, seu histórico de eventos e a pesquisa opcional de motivo de cancelamento. |
| **Cobrança** | `faturas`, `pagamentos`, `cupons`, `cupom_resgates` | Faturas por ciclo, tentativas de pagamento, reembolsos e contestações, e promoções. |
| **Catálogo** | `titulos`, `episodios`, `generos`, `titulo_generos`, `estudios`, `pessoas`, `titulo_elenco`, `catalogo_disponibilidade` | Filmes e séries, episódios, gêneros, elenco e as janelas de disponibilidade no catálogo. |
| **Uso do produto (logs)** | `sessoes_app`, `eventos_app`, `reproducoes`, `heartbeats_reproducao` | Sessões do app, eventos de interface, reproduções e pings de reprodução. |
| **Relacionamento** | `notificacoes`, `tickets_suporte`, `nps` | Push e e-mail enviados, atendimento ao cliente e pesquisa NPS. |

## Como as tabelas se conectam

- **`contas`** é o centro do modelo. Cada conta tem um canal de aquisição (`canais`) e, quando veio por indicação, aponta para a conta que a indicou (`indicada_por_conta_id`).
- Uma conta tem **perfis** (1 a 5) e **dispositivos**. As sessões e reproduções registram **qual perfil** usou **qual dispositivo**.
- Uma conta tem uma ou mais **assinaturas**. Cada assinatura é um período contínuo: começa no cadastro (ou numa reativação) e termina num encerramento. Uma reativação cria **nova** assinatura, ligada à anterior por `assinatura_anterior_id`.
- O histórico de cada assinatura (trial, mudança de plano, inadimplência, cancelamento, membro extra) fica em **`assinatura_eventos`**.
- Cada ciclo de cobrança gera uma **fatura**, que aponta para o **preço** vigente (`precos`) e, se houver, para o **resgate de cupom** usado. Cada tentativa de cobrança, reembolso ou contestação é uma linha em **`pagamentos`**.
- O catálogo é independente das contas: **`titulos`** (filme ou série) tem **`episodios`** (séries), gêneros, elenco, estúdio e janelas de disponibilidade em **`catalogo_disponibilidade`**.
- Os logs de uso referenciam perfis, dispositivos e títulos com chaves estrangeiras. Entre si, ligam-se por **chaves lógicas**:
  - `eventos_app.sessao_id` → `sessoes_app`;
  - `reproducoes.sessao_id` → `sessoes_app`;
  - `heartbeats_reproducao.reproducao_id` → `reproducoes`.

  Cada log chega por um pipeline de ingestão próprio, por isso essas ligações não têm `FOREIGN KEY` declarada.

## Caminho típico de uma conta

1. **Cadastro.**
   - A pessoa cria a conta (`contas.criada_em`) vinda de um canal de aquisição.
   - O primeiro perfil (`principal = 1`) é criado junto.
   - Nasce a primeira assinatura (`assinaturas`, evento `assinatura_criada`).
   - Até 31/03/2024, cadastros com cartão recebiam **trial de 7 dias** (`trial_iniciado`, `assinaturas.trial_fim_em`); depois o trial foi descontinuado.
   - Cupons aplicados no cadastro geram um registro em `cupom_resgates`.
2. **Assinatura e cobrança.**
   - Ao fim do trial (`trial_convertido`), ou no cadastro quando não há trial, é emitida a primeira fatura.
   - Planos mensais renovam no mesmo dia de cada mês; planos anuais, a cada 12 meses.
   - **Cartão:** cobrança automática. Se recusada, há retentativas em D+1, D+3 e D+7 (`pagamentos.tentativa`), e a assinatura fica `inadimplente` enquanto isso.
   - **Pix e boleto:** a pessoa paga manualmente a cada ciclo; o vencimento é D+3. Um Pix ou boleto não pago aparece como pagamento `expirado`.
   - Faturas podem ter desconto de cupom e, a partir de 10/03/2025, cobrança de **membro extra** (perfil usado fora do domicílio, nos planos que permitem).
3. **Uso.**
   - Cada abertura do app gera uma **sessão** (`sessoes_app`).
   - Dentro dela, o app registra **eventos** de interface (`eventos_app`) e **reproduções** (`reproducoes`).
   - Para perfis com `telemetria_detalhada = 1`, o player também envia **heartbeats** a cada 60 s (`heartbeats_reproducao`).
   - A empresa envia **notificações** (push e e-mail), recebe **tickets de suporte** e coleta **NPS** de uma amostra trimestral de contas.
4. **Mudanças.**
   - Upgrade ou downgrade de plano (`assinatura_eventos.tipo = upgrade/downgrade`, com plano anterior e novo).
   - Troca de método de pagamento e adição ou remoção de membro extra.
   - Os reajustes de preço entram em vigor em **01/08/2024** e **01/09/2025** (ver `precos`).
5. **Cancelamento ou encerramento.**
   - **Voluntário:** a pessoa solicita o cancelamento (`cancelamento_solicitado`, `assinaturas.cancelamento_solicitado_em`) e pode responder à pesquisa de motivo. O acesso segue até o fim do ciclo pago, quando a assinatura é encerrada (`encerrada`, `tipo_encerramento = voluntario`).
   - **Involuntário:** o pagamento não se concretiza após as retentativas ou após o prazo do Pix/boleto, e a assinatura é encerrada com `tipo_encerramento = involuntario`.
6. **Reativação.** A conta pode voltar a assinar a qualquer momento. Isso gera uma nova linha em `assinaturas` (evento `reativada`) apontando para a anterior. Campanhas de reconquista por e-mail podem oferecer cupom.

## Convenções

- Chaves primárias são inteiros sequenciais a partir de 1. Nos logs, a ordem dos ids acompanha aproximadamente a ordem temporal de ingestão.
- O estado de cada assinatura em `assinaturas.status` é uma foto em **31/10/2026 23:59:59 UTC**.
- Nomes, e-mails, CPFs, telefones, endereços e IPs foram gerados sinteticamente. Títulos, estúdios e pessoas do elenco são inventados.
