# Catálogo de eventos — `eventos_app`

O SDK de telemetria do app emite os eventos abaixo em todas as plataformas: TV, celular, tablet e web.

**Campos comuns a todo evento:**

| Campo | Significado |
|---|---|
| `evento_id` | Id único, atribuído na ingestão. |
| `sessao_id` | Sessão do app em que o evento ocorreu. |
| `perfil_id` | Perfil ativo no momento. |
| `seq` | Ordem do evento dentro da sessão. |
| `ocorrido_em` | Momento no dispositivo, em UTC. |
| `recebido_em` | Momento em que o coletor recebeu o evento, em UTC. |
| `versao_app` | Versão do app que emitiu o evento. |

Os parâmetros específicos de cada evento ocupam as colunas `titulo_id`, `fileira`, `posicao`, `termo_busca` e `avaliacao`. Parâmetros que não se aplicam ao evento ficam nulos.

Reproduções não são eventos desta tabela: são consolidadas em `reproducoes`, e o progresso do player está em `heartbeats_reproducao`.

| Evento (`tipo_evento`) | Gatilho | `titulo_id` | `fileira` | `posicao` | `termo_busca` | `avaliacao` |
|---|---|---|---|---|---|---|
| `impressao_titulo` | Um título fica visível (≥ 50% da arte por ≥ 1 s) numa fileira da home ou da tela de categoria. | obrigatório | obrigatório | obrigatório | — | — |
| `clique_titulo` | Usuário seleciona um título (abre a página de detalhes ou inicia o play direto). | obrigatório | — | — | — | — |
| `play_trailer` | Trailer começa a tocar (manual ou pré-visualização automática na página de detalhes). | obrigatório | — | — | — | — |
| `busca` | Usuário confirma uma busca (tecla buscar ou pausa de digitação ≥ 1,5 s). | — | — | — | obrigatório | — |
| `adicionar_lista` | Título adicionado a "Minha lista". | obrigatório | — | — | — | — |
| `avaliacao` | Usuário avalia um título com polegar para cima ou para baixo. | obrigatório | — | — | — | obrigatório (`positiva` / `negativa`) |
| `abrir_tela_planos` | Abertura da tela "Plano e assinatura" (ver, trocar ou cancelar plano). | — | — | — | — | — |
| `tentativa_cancelamento` | Usuário toca em "Cancelar assinatura" e entra no fluxo de cancelamento. O pedido efetivo, se concluído, é registrado em `assinatura_eventos` (`cancelamento_solicitado`). | — | — | — | — | — |

## Valores de `fileira`

| Valor | Fileira da home |
|---|---|
| `em_alta` | Em alta agora |
| `continuar_assistindo` | Continuar assistindo |
| `recomendados_para_voce` | Recomendados para você |
| `novidades` | Novidades na Cinelume |
| `originais_cinelume` | Originais Cinelume |
| `porque_voce_assistiu` | Porque você assistiu… |
| `top_10` | Top 10 da semana |
| `minha_lista` | Minha lista |

## Regras de emissão

- `posicao` começa em 1 no primeiro título à esquerda da fileira.
- `seq` é atribuído pelo SDK, na ordem em que os eventos acontecem no dispositivo.
- O SDK envia eventos em lotes. Quando o dispositivo está sem conexão, os eventos ficam em fila local e são enviados depois. `recebido_em` reflete a chegada ao servidor.
