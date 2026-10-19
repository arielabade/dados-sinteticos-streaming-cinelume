-- =====================================================================
-- Cinelume — banco de dados do serviço de streaming (fictício)
-- DDL para MySQL 8 (InnoDB, utf8mb4). Todos os DATETIME estão em UTC.
-- A ordem das colunas é a mesma dos arquivos CSV/Parquet.
-- =====================================================================
CREATE DATABASE IF NOT EXISTS cinelume CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE cinelume;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------- aquisição
CREATE TABLE canais (
  canal_id      SMALLINT     NOT NULL,
  codigo        VARCHAR(30)  NOT NULL,
  nome          VARCHAR(60)  NOT NULL,
  tipo          VARCHAR(20)  NOT NULL COMMENT 'organico | pago | indicacao | parceria',
  pago          TINYINT      NOT NULL,
  PRIMARY KEY (canal_id),
  UNIQUE KEY uq_canais_codigo (codigo),
  CONSTRAINT ck_canais_pago CHECK (pago IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE investimento_diario (
  data                  DATE          NOT NULL,
  canal_id              SMALLINT      NOT NULL,
  investimento_brl      DECIMAL(12,2) NOT NULL,
  impressoes            BIGINT        NULL,
  cliques               INT           NULL,
  cadastros_atribuidos  INT           NOT NULL,
  PRIMARY KEY (data, canal_id),
  KEY ix_inv_canal (canal_id, data),
  CONSTRAINT fk_inv_canal FOREIGN KEY (canal_id) REFERENCES canais (canal_id),
  CONSTRAINT ck_inv_valor CHECK (investimento_brl >= 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- planos e preços
CREATE TABLE planos (
  plano_id              SMALLINT     NOT NULL,
  codigo                VARCHAR(30)  NOT NULL,
  nome                  VARCHAR(60)  NOT NULL,
  com_anuncios          TINYINT      NOT NULL,
  resolucao_maxima      VARCHAR(10)  NOT NULL,
  telas_simultaneas     TINYINT      NOT NULL,
  max_perfis            TINYINT      NOT NULL,
  permite_membro_extra  TINYINT      NOT NULL,
  PRIMARY KEY (plano_id),
  UNIQUE KEY uq_planos_codigo (codigo)
) ENGINE=InnoDB;

CREATE TABLE precos (
  preco_id         INT           NOT NULL,
  plano_id         SMALLINT      NULL COMMENT 'NULL para item membro_extra',
  item             VARCHAR(20)   NOT NULL COMMENT 'assinatura | membro_extra',
  periodicidade    VARCHAR(10)   NOT NULL COMMENT 'mensal | anual',
  valor_brl        DECIMAL(10,2) NOT NULL,
  vigencia_inicio  DATE          NOT NULL,
  vigencia_fim     DATE          NULL,
  PRIMARY KEY (preco_id),
  KEY ix_precos_plano (plano_id, periodicidade, vigencia_inicio),
  CONSTRAINT fk_precos_plano FOREIGN KEY (plano_id) REFERENCES planos (plano_id),
  CONSTRAINT ck_precos_valor CHECK (valor_brl > 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- contas
CREATE TABLE contas (
  conta_id               INT          NOT NULL,
  email                  VARCHAR(120) NOT NULL,
  nome_titular           VARCHAR(120) NOT NULL,
  cpf                    VARCHAR(14)  NOT NULL,
  telefone               VARCHAR(25)  NULL,
  data_nascimento        DATE         NULL,
  cep                    VARCHAR(9)   NULL,
  cidade                 VARCHAR(80)  NOT NULL,
  uf                     VARCHAR(30)  NOT NULL,
  criada_em              DATETIME     NOT NULL,
  canal_aquisicao_id     SMALLINT     NOT NULL,
  indicada_por_conta_id  INT          NULL,
  aceita_marketing       TINYINT      NOT NULL,
  PRIMARY KEY (conta_id),
  UNIQUE KEY uq_contas_email (email),
  UNIQUE KEY uq_contas_cpf (cpf),
  KEY ix_contas_criada (criada_em),
  KEY ix_contas_canal (canal_aquisicao_id),
  CONSTRAINT fk_contas_canal FOREIGN KEY (canal_aquisicao_id) REFERENCES canais (canal_id),
  CONSTRAINT fk_contas_indicacao FOREIGN KEY (indicada_por_conta_id) REFERENCES contas (conta_id)
) ENGINE=InnoDB;

CREATE TABLE perfis (
  perfil_id             INT         NOT NULL,
  conta_id              INT         NOT NULL,
  nome                  VARCHAR(40) NOT NULL,
  infantil              TINYINT     NOT NULL,
  principal             TINYINT     NOT NULL,
  membro_extra          TINYINT     NOT NULL,
  telemetria_detalhada  TINYINT     NOT NULL,
  criado_em             DATETIME    NOT NULL,
  excluido_em           DATETIME    NULL,
  PRIMARY KEY (perfil_id),
  KEY ix_perfis_conta (conta_id),
  CONSTRAINT fk_perfis_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id)
) ENGINE=InnoDB;

CREATE TABLE dispositivos (
  dispositivo_id  INT         NOT NULL,
  conta_id        INT         NOT NULL,
  tipo            VARCHAR(20) NOT NULL COMMENT 'tv | celular | web | tablet',
  plataforma      VARCHAR(20) NOT NULL,
  registrado_em   DATETIME    NOT NULL,
  PRIMARY KEY (dispositivo_id),
  KEY ix_disp_conta (conta_id),
  CONSTRAINT fk_disp_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- assinatura e cobrança
CREATE TABLE assinaturas (
  assinatura_id               INT         NOT NULL,
  conta_id                    INT         NOT NULL,
  plano_id                    SMALLINT    NOT NULL,
  periodicidade               VARCHAR(10) NOT NULL,
  metodo_pagamento            VARCHAR(10) NOT NULL,
  status                      VARCHAR(25) NOT NULL,
  iniciada_em                 DATETIME    NOT NULL,
  trial_fim_em                DATETIME    NULL,
  cancelamento_solicitado_em  DATETIME    NULL,
  encerrada_em                DATETIME    NULL,
  tipo_encerramento           VARCHAR(15) NULL,
  renovacao_automatica        TINYINT     NOT NULL,
  assinatura_anterior_id      INT         NULL,
  PRIMARY KEY (assinatura_id),
  KEY ix_ass_conta (conta_id, iniciada_em),
  KEY ix_ass_status (status),
  KEY ix_ass_encerrada (encerrada_em),
  CONSTRAINT fk_ass_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT fk_ass_plano FOREIGN KEY (plano_id) REFERENCES planos (plano_id),
  CONSTRAINT fk_ass_anterior FOREIGN KEY (assinatura_anterior_id) REFERENCES assinaturas (assinatura_id)
) ENGINE=InnoDB;

CREATE TABLE assinatura_eventos (
  evento_id          BIGINT      NOT NULL,
  assinatura_id      INT         NOT NULL,
  tipo               VARCHAR(40) NOT NULL,
  ocorrido_em        DATETIME    NOT NULL,
  plano_anterior_id  SMALLINT    NULL,
  plano_novo_id      SMALLINT    NULL,
  origem             VARCHAR(10) NOT NULL,
  PRIMARY KEY (evento_id),
  KEY ix_aev_ass (assinatura_id, ocorrido_em),
  KEY ix_aev_tipo (tipo, ocorrido_em),
  CONSTRAINT fk_aev_ass FOREIGN KEY (assinatura_id) REFERENCES assinaturas (assinatura_id),
  CONSTRAINT fk_aev_pant FOREIGN KEY (plano_anterior_id) REFERENCES planos (plano_id),
  CONSTRAINT fk_aev_pnov FOREIGN KEY (plano_novo_id) REFERENCES planos (plano_id)
) ENGINE=InnoDB;

CREATE TABLE cupons (
  cupom_id        INT           NOT NULL,
  codigo          VARCHAR(30)   NOT NULL,
  descricao       VARCHAR(120)  NOT NULL,
  tipo_desconto   VARCHAR(15)   NOT NULL,
  valor_desconto  DECIMAL(10,2) NOT NULL,
  duracao_ciclos  SMALLINT      NOT NULL,
  valido_de       DATE          NOT NULL,
  valido_ate      DATE          NULL,
  canal_id        SMALLINT      NULL,
  apenas_novos    TINYINT       NOT NULL,
  PRIMARY KEY (cupom_id),
  UNIQUE KEY uq_cupons_codigo (codigo),
  CONSTRAINT fk_cupons_canal FOREIGN KEY (canal_id) REFERENCES canais (canal_id)
) ENGINE=InnoDB;

CREATE TABLE cupom_resgates (
  resgate_id     INT      NOT NULL,
  cupom_id       INT      NOT NULL,
  conta_id       INT      NOT NULL,
  assinatura_id  INT      NOT NULL,
  resgatado_em   DATETIME NOT NULL,
  PRIMARY KEY (resgate_id),
  KEY ix_resg_cupom (cupom_id),
  KEY ix_resg_conta (conta_id),
  CONSTRAINT fk_resg_cupom FOREIGN KEY (cupom_id) REFERENCES cupons (cupom_id),
  CONSTRAINT fk_resg_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT fk_resg_ass FOREIGN KEY (assinatura_id) REFERENCES assinaturas (assinatura_id)
) ENGINE=InnoDB;

CREATE TABLE faturas (
  fatura_id           BIGINT        NOT NULL,
  assinatura_id       INT           NOT NULL,
  conta_id            INT           NOT NULL,
  preco_id            INT           NOT NULL,
  cupom_resgate_id    INT           NULL,
  periodo_inicio      DATE          NOT NULL,
  periodo_fim         DATE          NOT NULL,
  emitida_em          DATETIME      NOT NULL,
  vencimento_em       DATE          NOT NULL,
  valor_bruto         DECIMAL(10,2) NOT NULL,
  valor_desconto      DECIMAL(10,2) NOT NULL,
  valor_membro_extra  DECIMAL(10,2) NOT NULL,
  valor_total         DECIMAL(10,2) NOT NULL,
  status              VARCHAR(15)   NOT NULL,
  PRIMARY KEY (fatura_id),
  KEY ix_fat_ass (assinatura_id, periodo_inicio),
  KEY ix_fat_conta (conta_id, emitida_em),
  KEY ix_fat_status (status),
  CONSTRAINT fk_fat_ass FOREIGN KEY (assinatura_id) REFERENCES assinaturas (assinatura_id),
  CONSTRAINT fk_fat_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT fk_fat_preco FOREIGN KEY (preco_id) REFERENCES precos (preco_id),
  CONSTRAINT fk_fat_resg FOREIGN KEY (cupom_resgate_id) REFERENCES cupom_resgates (resgate_id),
  CONSTRAINT ck_fat_periodo CHECK (periodo_fim >= periodo_inicio)
) ENGINE=InnoDB;

CREATE TABLE pagamentos (
  pagamento_id   BIGINT        NOT NULL,
  fatura_id      BIGINT        NULL,
  conta_id       INT           NOT NULL,
  metodo         VARCHAR(10)   NOT NULL,
  tipo           VARCHAR(15)   NOT NULL,
  tentativa      SMALLINT      NOT NULL,
  processado_em  DATETIME      NOT NULL,
  valor_brl      DECIMAL(10,2) NOT NULL,
  status         VARCHAR(15)   NOT NULL,
  codigo_recusa  VARCHAR(30)   NULL,
  PRIMARY KEY (pagamento_id),
  KEY ix_pag_fatura (fatura_id),
  KEY ix_pag_conta (conta_id, processado_em),
  CONSTRAINT fk_pag_fatura FOREIGN KEY (fatura_id) REFERENCES faturas (fatura_id),
  CONSTRAINT fk_pag_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT ck_pag_tentativa CHECK (tentativa >= 1)
) ENGINE=InnoDB;

CREATE TABLE pesquisa_cancelamento (
  resposta_id           INT          NOT NULL,
  assinatura_id         INT          NOT NULL,
  conta_id              INT          NOT NULL,
  respondida_em         DATETIME     NOT NULL,
  motivo_principal      VARCHAR(30)  NOT NULL,
  comentario            VARCHAR(300) NULL,
  probabilidade_voltar  TINYINT      NULL,
  PRIMARY KEY (resposta_id),
  KEY ix_pesq_ass (assinatura_id),
  KEY ix_pesq_conta (conta_id),
  CONSTRAINT fk_pesq_ass FOREIGN KEY (assinatura_id) REFERENCES assinaturas (assinatura_id),
  CONSTRAINT fk_pesq_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT ck_pesq_prob CHECK (probabilidade_voltar BETWEEN 0 AND 10)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- catálogo
CREATE TABLE generos (
  genero_id  SMALLINT    NOT NULL,
  nome       VARCHAR(40) NOT NULL,
  PRIMARY KEY (genero_id),
  UNIQUE KEY uq_generos_nome (nome)
) ENGINE=InnoDB;

CREATE TABLE estudios (
  estudio_id  INT         NOT NULL,
  nome        VARCHAR(80) NOT NULL,
  pais        CHAR(2)     NOT NULL,
  PRIMARY KEY (estudio_id)
) ENGINE=InnoDB;

CREATE TABLE pessoas (
  pessoa_id  INT          NOT NULL,
  nome       VARCHAR(120) NOT NULL,
  PRIMARY KEY (pessoa_id)
) ENGINE=InnoDB;

CREATE TABLE titulos (
  titulo_id                 INT          NOT NULL,
  tipo                      VARCHAR(10)  NOT NULL COMMENT 'filme | serie',
  nome                      VARCHAR(150) NOT NULL,
  ano_lancamento            SMALLINT     NOT NULL,
  duracao_min               SMALLINT     NULL COMMENT 'somente filmes',
  classificacao_indicativa  VARCHAR(3)   NOT NULL,
  original                  TINYINT      NOT NULL,
  estudio_id                INT          NOT NULL,
  idioma_original           CHAR(2)      NOT NULL,
  pais_origem               CHAR(2)      NOT NULL,
  sinopse                   VARCHAR(400) NOT NULL,
  PRIMARY KEY (titulo_id),
  UNIQUE KEY uq_titulos_nome (nome),
  KEY ix_titulos_tipo (tipo),
  CONSTRAINT fk_titulos_estudio FOREIGN KEY (estudio_id) REFERENCES estudios (estudio_id),
  CONSTRAINT ck_titulos_tipo CHECK (tipo IN ('filme', 'serie'))
) ENGINE=InnoDB;

CREATE TABLE titulo_generos (
  titulo_id  INT      NOT NULL,
  genero_id  SMALLINT NOT NULL,
  principal  TINYINT  NOT NULL,
  PRIMARY KEY (titulo_id, genero_id),
  KEY ix_tg_genero (genero_id),
  CONSTRAINT fk_tg_titulo FOREIGN KEY (titulo_id) REFERENCES titulos (titulo_id),
  CONSTRAINT fk_tg_genero FOREIGN KEY (genero_id) REFERENCES generos (genero_id)
) ENGINE=InnoDB;

CREATE TABLE titulo_elenco (
  titulo_id  INT         NOT NULL,
  pessoa_id  INT         NOT NULL,
  funcao     VARCHAR(15) NOT NULL COMMENT 'elenco | direcao',
  ordem      SMALLINT    NOT NULL,
  PRIMARY KEY (titulo_id, pessoa_id, funcao),
  KEY ix_te_pessoa (pessoa_id),
  CONSTRAINT fk_te_titulo FOREIGN KEY (titulo_id) REFERENCES titulos (titulo_id),
  CONSTRAINT fk_te_pessoa FOREIGN KEY (pessoa_id) REFERENCES pessoas (pessoa_id)
) ENGINE=InnoDB;

CREATE TABLE episodios (
  episodio_id       INT          NOT NULL,
  titulo_id         INT          NOT NULL,
  temporada         SMALLINT     NOT NULL,
  numero            SMALLINT     NOT NULL,
  nome              VARCHAR(120) NOT NULL,
  duracao_min       SMALLINT     NOT NULL,
  disponivel_desde  DATETIME     NOT NULL,
  PRIMARY KEY (episodio_id),
  UNIQUE KEY uq_ep_titulo_temp_num (titulo_id, temporada, numero),
  CONSTRAINT fk_ep_titulo FOREIGN KEY (titulo_id) REFERENCES titulos (titulo_id)
) ENGINE=InnoDB;

CREATE TABLE catalogo_disponibilidade (
  disponibilidade_id  INT         NOT NULL,
  titulo_id           INT         NOT NULL,
  entrada_em          DATE        NOT NULL,
  saida_em            DATE        NULL,
  tipo_licenca        VARCHAR(15) NOT NULL COMMENT 'original | licenciado',
  PRIMARY KEY (disponibilidade_id),
  KEY ix_cd_titulo (titulo_id, entrada_em),
  CONSTRAINT fk_cd_titulo FOREIGN KEY (titulo_id) REFERENCES titulos (titulo_id),
  CONSTRAINT ck_cd_datas CHECK (saida_em IS NULL OR saida_em > entrada_em)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- logs de uso
-- Em tabelas de log, as ligações entre logs (sessao_id, reproducao_id) são
-- chaves lógicas, sem FOREIGN KEY: cada log chega por um pipeline próprio.
CREATE TABLE sessoes_app (
  sessao_id       BIGINT      NOT NULL,
  perfil_id       INT         NOT NULL,
  dispositivo_id  INT         NOT NULL,
  versao_app      VARCHAR(10) NOT NULL,
  inicio_em       DATETIME    NOT NULL,
  fim_em          DATETIME    NULL,
  ip              VARCHAR(45) NOT NULL,
  regiao          VARCHAR(20) NULL,
  PRIMARY KEY (sessao_id),
  KEY ix_ses_perfil (perfil_id, inicio_em),
  KEY ix_ses_disp (dispositivo_id),
  KEY ix_ses_inicio (inicio_em),
  CONSTRAINT fk_ses_perfil FOREIGN KEY (perfil_id) REFERENCES perfis (perfil_id),
  CONSTRAINT fk_ses_disp FOREIGN KEY (dispositivo_id) REFERENCES dispositivos (dispositivo_id)
) ENGINE=InnoDB;

CREATE TABLE eventos_app (
  evento_id     BIGINT       NOT NULL,
  sessao_id     BIGINT       NOT NULL COMMENT 'chave lógica -> sessoes_app',
  perfil_id     INT          NOT NULL,
  seq           INT          NOT NULL,
  tipo_evento   VARCHAR(40)  NOT NULL,
  ocorrido_em   DATETIME     NOT NULL,
  recebido_em   DATETIME     NOT NULL,
  titulo_id     INT          NULL,
  fileira       VARCHAR(40)  NULL,
  posicao       SMALLINT     NULL,
  termo_busca   VARCHAR(100) NULL,
  avaliacao     VARCHAR(10)  NULL,
  versao_app    VARCHAR(10)  NOT NULL,
  PRIMARY KEY (evento_id),
  KEY ix_ev_sessao (sessao_id, seq),
  KEY ix_ev_perfil (perfil_id, ocorrido_em),
  KEY ix_ev_tipo (tipo_evento, recebido_em),
  KEY ix_ev_titulo (titulo_id),
  CONSTRAINT fk_ev_perfil FOREIGN KEY (perfil_id) REFERENCES perfis (perfil_id),
  CONSTRAINT fk_ev_titulo FOREIGN KEY (titulo_id) REFERENCES titulos (titulo_id)
) ENGINE=InnoDB;

CREATE TABLE reproducoes (
  reproducao_id         BIGINT       NOT NULL,
  perfil_id             INT          NOT NULL,
  sessao_id             BIGINT       NULL COMMENT 'chave lógica -> sessoes_app',
  dispositivo_id        INT          NOT NULL,
  titulo_id             INT          NOT NULL,
  episodio_id           INT          NULL,
  inicio_em             DATETIME     NOT NULL,
  fim_em                DATETIME     NULL,
  segundos_assistidos   BIGINT       NOT NULL,
  percentual_concluido  DECIMAL(6,2) NOT NULL,
  qualidade_video       VARCHAR(10)  NULL,
  eventos_buffering     SMALLINT     NOT NULL,
  origem_autoplay       TINYINT      NOT NULL,
  origem_recomendacao   TINYINT      NOT NULL,
  versao_app            VARCHAR(10)  NOT NULL,
  PRIMARY KEY (reproducao_id),
  KEY ix_rep_perfil (perfil_id, inicio_em),
  KEY ix_rep_titulo (titulo_id, inicio_em),
  KEY ix_rep_episodio (episodio_id),
  KEY ix_rep_sessao (sessao_id),
  KEY ix_rep_disp (dispositivo_id),
  CONSTRAINT fk_rep_perfil FOREIGN KEY (perfil_id) REFERENCES perfis (perfil_id),
  CONSTRAINT fk_rep_disp FOREIGN KEY (dispositivo_id) REFERENCES dispositivos (dispositivo_id),
  CONSTRAINT fk_rep_titulo FOREIGN KEY (titulo_id) REFERENCES titulos (titulo_id),
  CONSTRAINT fk_rep_episodio FOREIGN KEY (episodio_id) REFERENCES episodios (episodio_id)
) ENGINE=InnoDB;

CREATE TABLE heartbeats_reproducao (
  heartbeat_id     BIGINT      NOT NULL,
  reproducao_id    BIGINT      NOT NULL COMMENT 'chave lógica -> reproducoes',
  enviado_em       DATETIME    NOT NULL,
  posicao_seg      BIGINT      NOT NULL,
  qualidade_video  VARCHAR(10) NOT NULL,
  em_buffering     TINYINT     NOT NULL,
  PRIMARY KEY (heartbeat_id),
  KEY ix_hb_repro (reproducao_id, enviado_em)
) ENGINE=InnoDB;

CREATE TABLE notificacoes (
  notificacao_id  BIGINT      NOT NULL,
  conta_id        INT         NOT NULL,
  perfil_id       INT         NULL,
  canal           VARCHAR(10) NOT NULL COMMENT 'push | email',
  campanha        VARCHAR(40) NOT NULL,
  titulo_id       INT         NULL,
  enviada_em      DATETIME    NOT NULL,
  aberta_em       DATETIME    NULL,
  clicada_em      DATETIME    NULL,
  PRIMARY KEY (notificacao_id),
  KEY ix_not_conta (conta_id, enviada_em),
  KEY ix_not_campanha (campanha, enviada_em),
  CONSTRAINT fk_not_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT fk_not_perfil FOREIGN KEY (perfil_id) REFERENCES perfis (perfil_id),
  CONSTRAINT fk_not_titulo FOREIGN KEY (titulo_id) REFERENCES titulos (titulo_id)
) ENGINE=InnoDB;

CREATE TABLE tickets_suporte (
  ticket_id          INT         NOT NULL,
  conta_id           INT         NOT NULL,
  aberto_em          DATETIME    NOT NULL,
  canal_atendimento  VARCHAR(10) NOT NULL,
  categoria          VARCHAR(30) NOT NULL,
  status             VARCHAR(25) NOT NULL,
  resolvido_em       DATETIME    NULL,
  nota_satisfacao    TINYINT     NULL,
  PRIMARY KEY (ticket_id),
  KEY ix_tk_conta (conta_id, aberto_em),
  CONSTRAINT fk_tk_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT ck_tk_nota CHECK (nota_satisfacao BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE nps (
  resposta_id     INT          NOT NULL,
  conta_id        INT          NOT NULL,
  respondida_em   DATETIME     NOT NULL,
  nota            TINYINT      NOT NULL,
  comentario      VARCHAR(300) NULL,
  canal_pesquisa  VARCHAR(10)  NOT NULL,
  PRIMARY KEY (resposta_id),
  KEY ix_nps_conta (conta_id, respondida_em),
  CONSTRAINT fk_nps_conta FOREIGN KEY (conta_id) REFERENCES contas (conta_id),
  CONSTRAINT ck_nps_nota CHECK (nota BETWEEN 0 AND 10)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;
