"""Constantes, calendário e parâmetros globais da simulação da Cinelume."""
import datetime as dt

import numpy as np

SEED_PADRAO = 20231001

INICIO = dt.date(2023, 10, 1)
FIM = dt.date(2026, 10, 31)
NDIAS = (FIM - INICIO).days + 1
T0 = int(dt.datetime(2023, 10, 1, tzinfo=dt.timezone.utc).timestamp())
DIA = 86400
EPOCH_DIA0 = (INICIO - dt.date(1970, 1, 1)).days

ESCALAS = {
    "small": {"contas": 6_000},
    "medium": {"contas": 30_000},
    "full": {"contas": 120_000},
}


def dia(s):
    """Índice do dia (0 = 2023-10-01) para uma data ISO."""
    return (dt.date.fromisoformat(s) - INICIO).days


# ---------------------------------------------------------------- datas-chave
TRIAL_ATE = dia("2024-04-01")          # cadastros antes desta data recebem trial de 7 dias
REAJUSTES = [dia("2024-08-01"), dia("2025-09-01")]
MEMBRO_EXTRA = dia("2025-03-10")       # início da cobrança de membro extra
PARCERIA_OPERADORA = dia("2024-03-01")  # início da parceria com operadora
SAIDA_LOTE = dia("2025-06-30")         # fim de contrato de licenciamento em lote
BUG_INI, BUG_FIM = dia("2024-05-14"), dia("2024-06-25")
FALHAS_PIPELINE = [dia(s) for s in ("2024-02-14", "2024-11-03", "2025-01-22", "2025-07-08", "2026-04-17")]

VERSOES_APP = [
    ("4.0.0", "2023-09-04"), ("4.1.0", "2023-11-20"), ("4.2.0", "2024-02-26"),
    ("4.3.0", "2024-05-14"), ("4.3.1", "2024-06-25"), ("4.4.0", "2024-09-16"),
    ("4.5.0", "2024-11-25"), ("5.0.0", "2025-02-04"), ("5.1.0", "2025-05-12"),
    ("5.2.0", "2025-08-19"), ("5.3.0", "2025-11-10"), ("6.0.0", "2026-02-03"),
    ("6.1.0", "2026-05-05"), ("6.2.0", "2026-08-24"),
]
VERSAO_NOMES = np.array([v for v, _ in VERSOES_APP])
VERSAO_DIAS = np.array([dia(d) for _, d in VERSOES_APP])
IDX_V430 = 3
IDX_V500 = 7
IDX_V600 = 11

# Lançamentos originais de grande porte (dia, gênero principal)
TENTPOLES = [
    ("2023-11-10", "Ficção Científica"), ("2024-01-19", "Drama"), ("2024-04-12", "Suspense"),
    ("2024-07-05", "Animação"), ("2024-10-18", "Terror"), ("2024-12-13", "Comédia"),
    ("2025-03-21", "Ação"), ("2025-06-13", "Romance"), ("2025-10-10", "Crime"),
    ("2025-12-12", "Fantasia"), ("2026-03-27", "Drama"), ("2026-07-03", "Aventura"),
]

GENEROS = [
    "Ação", "Aventura", "Animação", "Comédia", "Crime", "Documentário", "Drama", "Fantasia",
    "Ficção Científica", "Infantil", "Musical", "Romance", "Suspense", "Terror", "Reality", "Esporte",
]
G = {n: i for i, n in enumerate(GENEROS)}
GENEROS_INFANTIS = [G["Infantil"], G["Animação"]]

# --------------------------------------------------------------- geografia
UFS = [
    # uf, peso populacional, região, offset UTC (horas)
    ("SP", .220, "Sudeste", -3), ("MG", .100, "Sudeste", -3), ("RJ", .080, "Sudeste", -3),
    ("ES", .020, "Sudeste", -3), ("BA", .068, "Nordeste", -3), ("PE", .045, "Nordeste", -3),
    ("CE", .043, "Nordeste", -3), ("MA", .033, "Nordeste", -3), ("PB", .019, "Nordeste", -3),
    ("RN", .016, "Nordeste", -3), ("AL", .015, "Nordeste", -3), ("PI", .016, "Nordeste", -3),
    ("SE", .011, "Nordeste", -3), ("PR", .055, "Sul", -3), ("RS", .053, "Sul", -3),
    ("SC", .037, "Sul", -3), ("GO", .033, "Centro-Oeste", -3), ("DF", .014, "Centro-Oeste", -3),
    ("MT", .018, "Centro-Oeste", -4), ("MS", .013, "Centro-Oeste", -4), ("PA", .040, "Norte", -3),
    ("AM", .019, "Norte", -4), ("RO", .008, "Norte", -4), ("TO", .007, "Norte", -3),
    ("AP", .004, "Norte", -3), ("AC", .004, "Norte", -5), ("RR", .003, "Norte", -4),
]
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
UF_SIGLA = np.array([u[0] for u in UFS])
UF_PESO = np.array([u[1] for u in UFS]) / sum(u[1] for u in UFS)
UF_REGIAO = np.array([REGIOES.index(u[2]) for u in UFS])
UF_TZ = np.array([u[3] for u in UFS])
UF_NOME = {
    "SP": "São Paulo", "MG": "Minas Gerais", "RJ": "Rio de Janeiro", "ES": "Espírito Santo",
    "BA": "Bahia", "PE": "Pernambuco", "CE": "Ceará", "MA": "Maranhão", "PB": "Paraíba",
    "RN": "Rio Grande do Norte", "AL": "Alagoas", "PI": "Piauí", "SE": "Sergipe", "PR": "Paraná",
    "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "GO": "Goiás", "DF": "Distrito Federal",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "PA": "Pará", "AM": "Amazonas",
    "RO": "Rondônia", "TO": "Tocantins", "AP": "Amapá", "AC": "Acre", "RR": "Roraima",
}

# --------------------------------------------------------------- canais
CANAIS = [
    # id, codigo, nome, tipo
    (1, "organico", "Orgânico", "organico"),
    (2, "busca_paga", "Busca paga", "pago"),
    (3, "social_pago", "Social pago", "pago"),
    (4, "indicacao", "Indicação", "indicacao"),
    (5, "parceria_operadora", "Parceria com operadora", "parceria"),
    (6, "tv", "TV", "pago"),
]
C_ORG, C_BUSCA, C_SOCIAL, C_IND, C_OPER, C_TV = range(6)

# --------------------------------------------------------------- planos e preços
PLANOS = [
    # id, codigo, nome, anuncios, resolucao, telas, max_perfis, permite_extra
    (1, "basico_anuncios", "Básico com anúncios", 1, "720p", 2, 5, 0),
    (2, "padrao", "Padrão", 0, "1080p", 2, 5, 1),
    (3, "premium", "Premium", 0, "4k", 4, 5, 1),
]
# preços por vigência: (inicio, fim, {plano: (mensal, anual)}, membro_extra)
TABELA_PRECOS = [
    ("2023-01-01", "2024-07-31", {1: (18.90, 189.00), 2: (39.90, 399.00), 3: (55.90, 559.00)}),
    ("2024-08-01", "2025-08-31", {1: (20.90, 209.00), 2: (44.90, 449.00), 3: (59.90, 599.00)}),
    ("2025-09-01", None, {1: (22.90, 229.00), 2: (47.90, 479.00), 3: (64.90, 649.00)}),
]
PRECOS_EXTRA = [("2025-03-10", "2025-08-31", 12.90), ("2025-09-01", None, 13.90)]


def calendario():
    """Arrays por dia: data, dia da semana, mês, sazonalidades."""
    datas = np.array([INICIO + dt.timedelta(days=i) for i in range(NDIAS)])
    dow = np.array([d.weekday() for d in datas])
    mes = np.array([d.month for d in datas])
    dom = np.array([d.day for d in datas])
    ano = np.array([d.year for d in datas])
    carnaval = set()
    for s in ("2024-02-10", "2025-03-01", "2026-02-14"):
        b = dia(s)
        carnaval.update(range(b, b + 5))
    ferias = (mes == 1) | (mes == 7) | ((mes == 12) & (dom >= 20))
    feriados = np.zeros(NDIAS, bool)
    for i, d in enumerate(datas):
        if (d.month, d.day) in {(12, 24), (12, 25), (12, 31), (1, 1)}:
            feriados[i] = True
    carn = np.array([i in carnaval for i in range(NDIAS)])
    # proxima cobrança (mesmo dia do mês seguinte / ano seguinte)
    prox_mes = np.empty(NDIAS, np.int32)
    prox_ano = np.empty(NDIAS, np.int32)
    for i, d in enumerate(datas):
        y, m = (d.year, d.month + 1) if d.month < 12 else (d.year + 1, 1)
        dd = min(d.day, [31, 29 if y % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
        prox_mes[i] = (dt.date(y, m, dd) - INICIO).days
        dd = min(d.day, 28) if d.month == 2 else d.day
        prox_ano[i] = (dt.date(d.year + 1, d.month, dd) - INICIO).days
    return dict(datas=datas, dow=dow, mes=mes, dom=dom, ano=ano, ferias=ferias,
                feriados=feriados, carnaval=carn, prox_mes=prox_mes, prox_ano=prox_ano)
