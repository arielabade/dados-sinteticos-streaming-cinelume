"""Esquemas Arrow das tabelas e gravação incremental em Parquet e CSV gzip."""
import gzip
import os

import numpy as np
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from .config import EPOCH_DIA0

I8, I16, I32, I64 = pa.int8(), pa.int16(), pa.int32(), pa.int64()
F64, STR, TS, DATE = pa.float64(), pa.string(), pa.timestamp("s"), pa.date32()

ESQUEMAS = {
    "canais": [("canal_id", I16), ("codigo", STR), ("nome", STR), ("tipo", STR), ("pago", I8)],
    "investimento_diario": [("data", DATE), ("canal_id", I16), ("investimento_brl", F64),
                            ("impressoes", I64), ("cliques", I32), ("cadastros_atribuidos", I32)],
    "planos": [("plano_id", I16), ("codigo", STR), ("nome", STR), ("com_anuncios", I8),
               ("resolucao_maxima", STR), ("telas_simultaneas", I8), ("max_perfis", I8),
               ("permite_membro_extra", I8)],
    "precos": [("preco_id", I32), ("plano_id", I16), ("item", STR), ("periodicidade", STR),
               ("valor_brl", F64), ("vigencia_inicio", DATE), ("vigencia_fim", DATE)],
    "contas": [("conta_id", I32), ("email", STR), ("nome_titular", STR), ("cpf", STR),
               ("telefone", STR), ("data_nascimento", DATE), ("cep", STR), ("cidade", STR),
               ("uf", STR), ("criada_em", TS), ("canal_aquisicao_id", I16),
               ("indicada_por_conta_id", I32), ("aceita_marketing", I8)],
    "perfis": [("perfil_id", I32), ("conta_id", I32), ("nome", STR), ("infantil", I8),
               ("principal", I8), ("membro_extra", I8), ("telemetria_detalhada", I8),
               ("criado_em", TS), ("excluido_em", TS)],
    "dispositivos": [("dispositivo_id", I32), ("conta_id", I32), ("tipo", STR),
                     ("plataforma", STR), ("registrado_em", TS)],
    "assinaturas": [("assinatura_id", I32), ("conta_id", I32), ("plano_id", I16),
                    ("periodicidade", STR), ("metodo_pagamento", STR), ("status", STR),
                    ("iniciada_em", TS), ("trial_fim_em", TS), ("cancelamento_solicitado_em", TS),
                    ("encerrada_em", TS), ("tipo_encerramento", STR), ("renovacao_automatica", I8),
                    ("assinatura_anterior_id", I32)],
    "assinatura_eventos": [("evento_id", I64), ("assinatura_id", I32), ("tipo", STR),
                           ("ocorrido_em", TS), ("plano_anterior_id", I16), ("plano_novo_id", I16),
                           ("origem", STR)],
    "cupons": [("cupom_id", I32), ("codigo", STR), ("descricao", STR), ("tipo_desconto", STR),
               ("valor_desconto", F64), ("duracao_ciclos", I16), ("valido_de", DATE),
               ("valido_ate", DATE), ("canal_id", I16), ("apenas_novos", I8)],
    "cupom_resgates": [("resgate_id", I32), ("cupom_id", I32), ("conta_id", I32),
                       ("assinatura_id", I32), ("resgatado_em", TS)],
    "faturas": [("fatura_id", I64), ("assinatura_id", I32), ("conta_id", I32), ("preco_id", I32),
                ("cupom_resgate_id", I32), ("periodo_inicio", DATE), ("periodo_fim", DATE),
                ("emitida_em", TS), ("vencimento_em", DATE), ("valor_bruto", F64),
                ("valor_desconto", F64), ("valor_membro_extra", F64), ("valor_total", F64),
                ("status", STR)],
    "pagamentos": [("pagamento_id", I64), ("fatura_id", I64), ("conta_id", I32), ("metodo", STR),
                   ("tipo", STR), ("tentativa", I16), ("processado_em", TS), ("valor_brl", F64),
                   ("status", STR), ("codigo_recusa", STR)],
    "pesquisa_cancelamento": [("resposta_id", I32), ("assinatura_id", I32), ("conta_id", I32),
                              ("respondida_em", TS), ("motivo_principal", STR), ("comentario", STR),
                              ("probabilidade_voltar", I8)],
    "generos": [("genero_id", I16), ("nome", STR)],
    "estudios": [("estudio_id", I32), ("nome", STR), ("pais", STR)],
    "pessoas": [("pessoa_id", I32), ("nome", STR)],
    "titulos": [("titulo_id", I32), ("tipo", STR), ("nome", STR), ("ano_lancamento", I16),
                ("duracao_min", I16), ("classificacao_indicativa", STR), ("original", I8),
                ("estudio_id", I32), ("idioma_original", STR), ("pais_origem", STR),
                ("sinopse", STR)],
    "titulo_generos": [("titulo_id", I32), ("genero_id", I16), ("principal", I8)],
    "titulo_elenco": [("titulo_id", I32), ("pessoa_id", I32), ("funcao", STR), ("ordem", I16)],
    "episodios": [("episodio_id", I32), ("titulo_id", I32), ("temporada", I16), ("numero", I16),
                  ("nome", STR), ("duracao_min", I16), ("disponivel_desde", TS)],
    "catalogo_disponibilidade": [("disponibilidade_id", I32), ("titulo_id", I32),
                                 ("entrada_em", DATE), ("saida_em", DATE), ("tipo_licenca", STR)],
    "sessoes_app": [("sessao_id", I64), ("perfil_id", I32), ("dispositivo_id", I32),
                    ("versao_app", STR), ("inicio_em", TS), ("fim_em", TS), ("ip", STR),
                    ("regiao", STR)],
    "eventos_app": [("evento_id", I64), ("sessao_id", I64), ("perfil_id", I32), ("seq", I32),
                    ("tipo_evento", STR), ("ocorrido_em", TS), ("recebido_em", TS),
                    ("titulo_id", I32), ("fileira", STR), ("posicao", I16), ("termo_busca", STR),
                    ("avaliacao", STR), ("versao_app", STR)],
    "reproducoes": [("reproducao_id", I64), ("perfil_id", I32), ("sessao_id", I64),
                    ("dispositivo_id", I32), ("titulo_id", I32), ("episodio_id", I32),
                    ("inicio_em", TS), ("fim_em", TS), ("segundos_assistidos", I64),
                    ("percentual_concluido", F64), ("qualidade_video", STR),
                    ("eventos_buffering", I16), ("origem_autoplay", I8),
                    ("origem_recomendacao", I8), ("versao_app", STR)],
    "heartbeats_reproducao": [("heartbeat_id", I64), ("reproducao_id", I64), ("enviado_em", TS),
                              ("posicao_seg", I64), ("qualidade_video", STR), ("em_buffering", I8)],
    "notificacoes": [("notificacao_id", I64), ("conta_id", I32), ("perfil_id", I32),
                     ("canal", STR), ("campanha", STR), ("titulo_id", I32), ("enviada_em", TS),
                     ("aberta_em", TS), ("clicada_em", TS)],
    "tickets_suporte": [("ticket_id", I32), ("conta_id", I32), ("aberto_em", TS),
                        ("canal_atendimento", STR), ("categoria", STR), ("status", STR),
                        ("resolvido_em", TS), ("nota_satisfacao", I8)],
    "nps": [("resposta_id", I32), ("conta_id", I32), ("respondida_em", TS), ("nota", I8),
            ("comentario", STR), ("canal_pesquisa", STR)],
}


def schema(nome):
    return pa.schema([pa.field(c, t) for c, t in ESQUEMAS[nome]])


def ts(x, nulo=None):
    """Segundos desde epoch (int64) -> timestamp[s]; `nulo` é máscara booleana."""
    x = np.asarray(x, dtype=np.int64)
    return pa.array(x, type=TS, mask=None if nulo is None else np.asarray(nulo, bool))


def data(d, nulo=None):
    """Índice de dia da simulação -> date32."""
    x = np.asarray(d, dtype=np.int64) + EPOCH_DIA0
    return pa.array(x.astype(np.int32), type=DATE, mask=None if nulo is None else np.asarray(nulo, bool))


def num(x, tipo, nulo=None):
    x = np.asarray(x)
    if tipo == F64:
        x = np.round(x.astype(np.float64), 2)
    return pa.array(x, type=tipo, mask=None if nulo is None else np.asarray(nulo, bool))


def txt(x, nulo=None):
    x = np.asarray(x, dtype=object)
    if nulo is not None:
        x = x.copy()
        x[np.asarray(nulo, bool)] = None
    return pa.array(x, type=STR)


def converter(v, tipo):
    """Converte array numpy (ou tupla (valores, máscara_nula)) para o tipo Arrow da coluna.

    Convenções: DATE recebe índice de dia da simulação; TS recebe segundos desde epoch."""
    if isinstance(v, (pa.Array, pa.ChunkedArray)):
        return v if v.type == tipo else v.cast(tipo)
    nulo = None
    if isinstance(v, tuple):
        v, nulo = v
    if tipo == TS:
        return ts(v, nulo)
    if tipo == DATE:
        return data(v, nulo)
    if tipo == STR:
        return txt(v, nulo)
    return num(v, tipo, nulo)


class Tabela:
    """Escreve uma tabela em pedaços: um Parquet e um CSV gzip."""

    def __init__(self, base, nome):
        self.nome = nome
        self.schema = schema(nome)
        os.makedirs(f"{base}/parquet", exist_ok=True)
        os.makedirs(f"{base}/csv", exist_ok=True)
        self.pq = pq.ParquetWriter(f"{base}/parquet/{nome}.parquet", self.schema, compression="zstd")
        self._raw = open(f"{base}/csv/{nome}.csv.gz", "wb")
        self.gz = gzip.GzipFile(filename="", mode="wb", compresslevel=5, fileobj=self._raw, mtime=0)
        self.csv = pacsv.CSVWriter(self.gz, self.schema)
        self.linhas = 0

    def escrever(self, cols):
        arrays = []
        n = None
        for f in self.schema:
            v = converter(cols[f.name], f.type)
            n = len(v) if n is None else n
            arrays.append(v)
        if not n:
            return
        t = pa.Table.from_arrays(arrays, schema=self.schema)
        self.pq.write_table(t, row_group_size=500_000)
        self.csv.write_table(t)
        self.linhas += t.num_rows

    def fechar(self):
        self.pq.close()
        self.csv.close()
        self.gz.close()
        self._raw.close()
        return self.linhas


def gravar(base, nome, cols):
    t = Tabela(base, nome)
    t.escrever(cols)
    return t.fechar()
