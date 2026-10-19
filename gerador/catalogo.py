"""Catálogo fictício: gêneros, estúdios, pessoas, títulos, episódios e disponibilidade."""
import unicodedata

import numpy as np

from .config import (FIM, G, GENEROS, GENEROS_INFANTIS, INICIO, NDIAS, SAIDA_LOTE, TENTPOLES, dia)

SILABAS = ["ta", "ri", "lu", "mo", "ca", "be", "ra", "to", "ni", "va", "qui", "ma", "do", "rim",
           "sol", "bel", "tã", "nha", "ju", "pa", "zé", "lo", "ve", "dor", "fi", "gu", "ra", "xi",
           "ba", "nó", "te", "cri", "mau", "ló", "sa", "tu"]
SUBST_M = ["Segredo", "Silêncio", "Caminho", "Farol", "Destino", "Labirinto", "Inverno", "Retorno",
           "Horizonte", "Pacto", "Abismo", "Jardim", "Espelho", "Eco", "Oráculo", "Vento", "Rio",
           "Sertão", "Código", "Enigma", "Herdeiro", "Guardião", "Vale", "Porto", "Relógio",
           "Diário", "Baile", "Quintal", "Sobrado", "Circo", "Trem", "Navio", "Planeta", "Mapa",
           "Tesouro", "Sinal", "Bairro", "Morro", "Verão", "Juramento", "Desvio", "Atalho"]
SUBST_F = ["Sombra", "Ilha", "Noite", "Promessa", "Estrada", "Casa", "Fronteira", "Memória",
           "Tempestade", "Herança", "Cidade", "Floresta", "Maré", "Chave", "Carta", "Canção",
           "Ponte", "Lua", "Estação", "Fazenda", "Vila", "Escola", "Rua", "Praia", "Aldeia",
           "Torre", "Linha", "Missão", "Febre", "Dança", "Travessia", "Colheita", "Vigília"]
ADJ = [("Perdido", "Perdida"), ("Esquecido", "Esquecida"), ("Proibido", "Proibida"),
       ("Silencioso", "Silenciosa"), ("Invisível", "Invisível"), ("Eterno", "Eterna"),
       ("Escondido", "Escondida"), ("Selvagem", "Selvagem"), ("Distante", "Distante"),
       ("Dourado", "Dourada"), ("Vermelho", "Vermelha"), ("Último", "Última"),
       ("Quebrado", "Quebrada"), ("Submerso", "Submersa"), ("Noturno", "Noturna")]
LUGAR_PREF = ["Vila", "Serra", "Porto", "Lagoa", "Campo", "Morro", "Ribeira", "Ponta"]
PROFISSOES = ["uma detetive aposentada", "um professor de música", "uma jovem engenheira",
              "um pescador", "uma médica plantonista", "um ex-jogador", "uma cozinheira",
              "um astronauta", "uma advogada", "um motorista de aplicativo", "uma estudante",
              "um vigia noturno", "uma família inteira", "dois irmãos", "uma bióloga",
              "um mágico de circo", "uma repórter", "um robô doméstico", "um grupo de amigos"]
VERBOS = ["precisa encontrar", "tenta proteger", "descobre", "decide enfrentar", "investiga",
          "foge de", "herda", "tenta reconstruir", "se envolve com", "precisa esconder"]
OBJETOS = ["um segredo de família", "uma carta antiga", "um mapa incompleto", "um crime sem solução",
           "uma criatura misteriosa", "um amor do passado", "uma herança disputada",
           "um sinal vindo do espaço", "uma conspiração local", "uma competição impossível",
           "a verdade sobre o próprio pai", "um tesouro perdido"]
EP_PAL = ["Começo", "Chegada", "Desvio", "Encontro", "Fuga", "Ruptura", "Retorno", "Noite Longa",
          "Verdades", "Última Chance", "Pistas", "Despedida", "Recomeço", "Alerta", "Labirinto",
          "Fogo Cruzado", "Silêncio", "Promessas", "Raízes", "Tempestade", "Acerto de Contas"]
PAIS_POR_IDIOMA = {"pt": ["BR", "BR", "BR", "PT"], "en": ["US", "US", "GB", "CA", "AU"],
                   "es": ["ES", "MX", "AR", "CO"], "ko": ["KR"], "ja": ["JP"], "fr": ["FR", "BE"]}


def _inventado(rng, n_sil=None):
    n = n_sil or rng.choice([2, 3, 3])
    s = "".join(rng.choice(SILABAS) for _ in range(n))
    return s[0].upper() + s[1:]


def _nome_titulo(rng, primeiros_nomes):
    t = rng.integers(0, 8)
    sm, sf = rng.choice(SUBST_M), rng.choice(SUBST_F)
    am, af = ADJ[rng.integers(len(ADJ))]
    inv = _inventado(rng)
    lugar = f"{rng.choice(LUGAR_PREF)} {_inventado(rng)}"
    nome = rng.choice(primeiros_nomes)
    if t == 0:
        return f"O {sm} de {inv}"
    if t == 1:
        return f"A {sf} {af} de {inv}"
    if t == 2:
        return f"{nome} e o {sm} {am}"
    if t == 3:
        return f"Operação {inv}"
    if t == 4:
        return f"{lugar}"
    if t == 5:
        return f"{inv}: A {sf} {af}"
    if t == 6:
        return f"As Noites de {nome}" if rng.random() < .5 else f"Os Dias de {nome} {inv}"
    return f"{lugar}: O {sm} {am}"


def gerar_catalogo(rng, fake, n_titulos=3000, n_series=700, alvo_eps=25000):
    primeiros = sorted({fake.first_name() for _ in range(1500)})

    # ---------------- estúdios e pessoas
    estudios = ["Cinelume Produções"]
    sufx = ["Filmes", "Produções", "Studios", "Audiovisual", "Entretenimento", "Pictures", "Media"]
    while len(estudios) < 45:
        e = f"{_inventado(rng, 3)} {rng.choice(sufx)}"
        if e not in estudios:
            estudios.append(e)
    est_pais = ["BR"] + list(rng.choice(["BR", "US", "GB", "ES", "MX", "KR", "JP", "FR", "AR"],
                                        size=len(estudios) - 1,
                                        p=[.3, .3, .08, .06, .06, .06, .05, .05, .04]))
    pessoas = []
    vistos = set()
    while len(pessoas) < 5000:
        nm = fake.name()
        if nm not in vistos:
            vistos.add(nm)
            pessoas.append(nm)

    # ---------------- títulos
    N = n_titulos
    tipo = np.zeros(N, np.int8)
    tipo[rng.choice(N, n_series, replace=False)] = 1
    gpesos_f = np.array([10, 5, 6, 14, 6, 8, 15, 4, 5, 6, 1.5, 8, 10, 8, 0, 1.5])
    gpesos_s = np.array([7, 4, 7, 14, 8, 7, 16, 5, 5, 6, .5, 6, 9, 4, 6, 1.5])
    gen = np.where(tipo == 0, rng.choice(16, N, p=gpesos_f / gpesos_f.sum()),
                   rng.choice(16, N, p=gpesos_s / gpesos_s.sum()))
    original = np.where(tipo == 0, rng.random(N) < .12, rng.random(N) < .30)
    pop = rng.lognormal(0, 1.4, N) * np.where(original, 2.5, 1.0) * np.where(tipo == 1, 1.3, 1.0)

    # lançamento dos originais (dia relativo; negativo = antes do período)
    lanc = np.full(N, -10_000, np.int32)
    io = np.where(original)[0]
    lanc[io] = rng.integers(dia("2021-03-01"), NDIAS - 20, len(io))
    # tentpoles: originais escolhidos com gênero coerente, popularidade alta
    tent_ids = []
    for (ds, gnome) in TENTPOLES:
        cand = np.where(original & (gen == G[gnome]) & ~np.isin(np.arange(N), tent_ids))[0]
        if len(cand) == 0:
            cand = np.where(original & ~np.isin(np.arange(N), tent_ids))[0]
            gen_force = True
        else:
            gen_force = False
        # preferir séries
        cs = cand[tipo[cand] == 1]
        i = int(rng.choice(cs if len(cs) else cand))
        if gen_force:
            gen[i] = G[gnome]
        tent_ids.append(i)
        lanc[i] = dia(ds)
        pop[i] = np.quantile(pop, .995) * rng.uniform(1.0, 1.6)
    tent_ids = np.array(tent_ids)

    # ano de lançamento
    ano_lanc = (np.datetime64(INICIO.isoformat()) + lanc.astype("timedelta64[D]")).astype("datetime64[Y]").astype(int) + 1970
    ano = np.where(original, ano_lanc, np.clip(2025 - rng.exponential(9, N).astype(int), 1960, 2025))
    ano = np.where(original, np.clip(ano, 2021, FIM.year), ano)

    # gênero secundário
    sec = np.where(rng.random(N) < .5, rng.integers(0, 16, N), -1)
    sec = np.where(sec == gen, -1, sec)

    # duração dos filmes
    base_dur = {G["Animação"]: 88, G["Infantil"]: 82, G["Documentário"]: 95, G["Ação"]: 116,
                G["Drama"]: 112, G["Comédia"]: 100, G["Terror"]: 97, G["Ficção Científica"]: 118,
                G["Fantasia"]: 120, G["Musical"]: 110}
    dur = np.array([base_dur.get(g, 106) for g in gen]) + rng.normal(0, 13, N)
    dur = np.clip(dur, 68, 195).astype(np.int16)

    # classificação indicativa
    classes = np.array(["L", "10", "12", "14", "16", "18"])
    cprob = {
        "kids": [.7, .3, 0, 0, 0, 0], "Terror": [0, 0, .05, .25, .45, .25],
        "Crime": [0, 0, .1, .4, .4, .1], "Ação": [0, .05, .3, .45, .2, 0],
        "Suspense": [0, 0, .2, .45, .3, .05], "Drama": [.05, .1, .3, .35, .17, .03],
        "Comédia": [.1, .3, .35, .2, .05, 0], "Romance": [.05, .15, .4, .35, .05, 0],
        "Documentário": [.4, .3, .2, .1, 0, 0], "Reality": [.1, .2, .4, .3, 0, 0],
        "Esporte": [.6, .3, .1, 0, 0, 0], "outros": [.05, .2, .35, .3, .1, 0],
    }
    clas = []
    for g in gen:
        nome = GENEROS[g]
        k = "kids" if g in GENEROS_INFANTIS else (nome if nome in cprob else "outros")
        clas.append(classes[rng.choice(6, p=cprob[k])])
    clas = np.array(clas)

    idiomas = np.array(["pt", "en", "es", "ko", "ja", "fr"])
    idi = np.where(original, "pt", idiomas[rng.choice(6, N, p=[.25, .5, .1, .06, .05, .04])])
    idi = np.where((gen == G["Animação"]) & ~original & (rng.random(N) < .3), "ja", idi)
    pais = np.array([rng.choice(PAIS_POR_IDIOMA[i]) for i in idi])
    pais = np.where(original, "BR", pais)

    # estúdio
    w_est = 1 / np.arange(1, len(estudios)) ** .9
    est = np.where(original, 0, 1 + rng.choice(len(estudios) - 1, N, p=w_est / w_est.sum()))

    # nomes únicos
    nomes, usados = [], set()
    for i in range(N):
        while True:
            nm = _nome_titulo(rng, primeiros)
            chave = unicodedata.normalize("NFKD", nm).encode("ascii", "ignore").decode().lower()
            if chave not in usados:
                usados.add(chave)
                nomes.append(nm)
                break
    sinopses = [f"{rng.choice(PROFISSOES).capitalize()} {rng.choice(VERBOS)} {rng.choice(OBJETOS)}."
                for _ in range(N)]

    # ---------------- disponibilidade no catálogo (intervalos [entrada, saida) em dias relativos)
    disp = []  # (titulo_idx, entrada, saida or None, tipo)
    lote = np.zeros(N, bool)
    lic = np.where(~original)[0]
    # lote de licenciamento que sai em SAIDA_LOTE: 150 títulos, maioria comédia popular, estúdio 2
    com = lic[gen[lic] == G["Comédia"]]
    com = com[np.argsort(-pop[com])][: int(len(com) * .6)]
    n_lote = min(150, len(lic))
    n_com = min(len(com), int(n_lote * .75))
    lote_ids = list(rng.choice(com, n_com, replace=False))
    resto = np.setdiff1d(lic, lote_ids)
    lote_ids += list(rng.choice(resto, n_lote - n_com, replace=False))
    lote[lote_ids] = True
    est[lote] = 2
    for i in range(N):
        if original[i]:
            disp.append((i, int(lanc[i]), None, "original"))
            continue
        if lote[i]:
            disp.append((i, int(rng.integers(dia("2020-01-01"), -30)), SAIDA_LOTE, "licenciado"))
            continue
        if rng.random() < .72:
            ent = int(rng.integers(dia("2019-06-01"), -1))
        else:
            ent = int(rng.integers(0, NDIAS - 30))
        dur_lic = int(rng.integers(540, 1460))
        sai = ent + dur_lic
        if sai < 0:  # licença já vencida antes do início -> nova janela
            ent, sai = int(rng.integers(-200, 60)), None
        if sai is not None and sai >= NDIAS:
            sai = None
        disp.append((i, ent, sai, "licenciado"))
        if sai is not None and rng.random() < .10:
            ent2 = sai + int(rng.integers(90, 365))
            if ent2 < NDIAS - 10:
                disp.append((i, ent2, None, "licenciado"))

    # disponibilidade mensal (para escolha de filmes) e diária (séries)
    ent_arr = np.array([d[1] for d in disp])
    sai_arr = np.array([NDIAS + 10_000 if d[2] is None else d[2] for d in disp])
    tid_arr = np.array([d[0] for d in disp])
    disp_dia = np.zeros((N, NDIAS), bool)
    for t, e, s in zip(tid_arr, ent_arr, sai_arr):
        disp_dia[t, max(e, 0):max(min(s, NDIAS), 0)] = True

    # ---------------- séries: temporadas e episódios
    sidx = np.where(tipo == 1)[0]
    ep_base = {G["Comédia"]: 26, G["Animação"]: 23, G["Infantil"]: 14, G["Drama"]: 50,
               G["Suspense"]: 47, G["Crime"]: 50, G["Ação"]: 45, G["Ficção Científica"]: 52,
               G["Fantasia"]: 54, G["Terror"]: 44, G["Romance"]: 42, G["Documentário"]: 44,
               G["Reality"]: 52, G["Musical"]: 40, G["Aventura"]: 46, G["Esporte"]: 38}

    def eps_por_temp(g):
        if g in (G["Comédia"],):
            return int(rng.integers(10, 23))
        if g in GENEROS_INFANTIS:
            return int(rng.integers(10, 27))
        if g == G["Reality"]:
            return int(rng.integers(8, 15))
        return int(rng.integers(6, 11))

    temporadas = {}
    for i in sidx:
        if original[i]:
            nt = int(rng.choice([1, 2, 3, 4], p=[.4, .3, .2, .1]))
        else:
            nt = int(min(1 + rng.poisson(1.6), 9))
        temporadas[i] = [eps_por_temp(gen[i]) for _ in range(nt)]
    tot = sum(sum(v) for v in temporadas.values())
    lic_s = [i for i in sidx if not original[i]]
    while tot > alvo_eps * 1.01:
        i = rng.choice(lic_s)
        if len(temporadas[i]) > 1:
            tot -= temporadas[i].pop()
    while tot < alvo_eps * .99:
        i = rng.choice(lic_s)
        e = eps_por_temp(gen[i])
        temporadas[i].append(e)
        tot += e
    # tentpoles série: garantir 2ª temporada dentro do período para os primeiros
    for k, i in enumerate(tent_ids):
        if tipo[i] == 1 and lanc[i] < NDIAS - 420 and len(temporadas[i]) < 2:
            temporadas[i].append(eps_por_temp(gen[i]))

    ep_rows = []  # titulo_idx, temporada, numero, dur_min, disponivel_dia
    ser_rel = {}  # titulo_idx -> lista de dias de lançamento das temporadas
    for i in sidx:
        dbase = ep_base.get(gen[i], 45) * rng.uniform(.85, 1.15)
        first_ent = min(d[1] for d in disp if d[0] == i)
        dias_t = []
        for t, ne in enumerate(temporadas[i]):
            if original[i]:
                dt_ = int(lanc[i]) + t * int(rng.integers(300, 460)) if t else int(lanc[i])
            else:
                dt_ = first_ent
            dias_t.append(dt_)
        # descartar temporadas originais que estreariam depois do fim do período
        keep = [t for t, d_ in enumerate(dias_t) if d_ < NDIAS]
        temporadas[i] = [temporadas[i][t] for t in keep]
        dias_t = [dias_t[t] for t in keep]
        ser_rel[i] = dias_t
        for t, ne in enumerate(temporadas[i]):
            for e in range(ne):
                ep_rows.append((i, t + 1, e + 1, max(8, int(round(dbase * rng.uniform(.92, 1.08)))),
                                dias_t[t]))
    ep = np.array(ep_rows, dtype=np.int64)
    # status de produção: original com nova temporada pendente fora do período conta como "em andamento"
    finalizada = {i: (not original[i]) or rng.random() < .5 for i in sidx}

    # ---------------- estruturas para a simulação
    ser_tit = sidx
    S = len(sidx)
    pos_ser = {t: s for s, t in enumerate(sidx)}
    ep_tit = ep[:, 0]
    ordem = np.lexsort((ep[:, 2], ep[:, 1], ep_tit))
    ep = ep[ordem]
    ep_off = np.zeros(S + 1, np.int64)
    for s, t in enumerate(sidx):
        ep_off[s + 1] = ep_off[s] + sum(temporadas[t])
    n_eps_total = np.diff(ep_off)
    ep_disp = ep[:, 4]
    eps_disp = np.zeros((S, NDIAS), np.int16)
    for s in range(S):
        d_eps = np.sort(ep_disp[ep_off[s]:ep_off[s + 1]])
        c = np.searchsorted(d_eps, np.arange(NDIAS), side="right")
        eps_disp[s] = c
    eps_disp = np.where(disp_dia[sidx], eps_disp, 0).astype(np.int16)
    ser_fim = np.array([finalizada[t] for t in sidx])

    return dict(
        N=N, tipo=tipo, gen=gen, sec=sec, original=original, pop=pop, lanc=lanc, ano=ano, dur=dur,
        clas=clas, idioma=idi, pais=pais, est=est, nomes=np.array(nomes, dtype=object),
        sinopses=sinopses, estudios=estudios, est_pais=est_pais, pessoas=pessoas,
        disp=disp, disp_dia=disp_dia, lote=lote, tent_ids=tent_ids,
        ser_tit=ser_tit, S=S, pos_ser=pos_ser, ep=ep, ep_off=ep_off, n_eps_total=n_eps_total,
        eps_disp=eps_disp, ser_fim=ser_fim, ser_rel=ser_rel, primeiros=primeiros,
        ep_nomes=EP_PAL,
    )


def tabelas_catalogo(cat, rng):
    """Monta as colunas das tabelas de catálogo (ids começam em 1)."""
    from .config import T0, DIA
    N = cat["N"]
    out = {}
    out["generos"] = dict(genero_id=np.arange(1, 17), nome=np.array(GENEROS, dtype=object))
    ne = len(cat["estudios"])
    out["estudios"] = dict(estudio_id=np.arange(1, ne + 1), nome=np.array(cat["estudios"], dtype=object),
                           pais=np.array(cat["est_pais"], dtype=object))
    npes = len(cat["pessoas"])
    out["pessoas"] = dict(pessoa_id=np.arange(1, npes + 1), nome=np.array(cat["pessoas"], dtype=object))
    tipo_txt = np.where(cat["tipo"] == 0, "filme", "serie")
    out["titulos"] = dict(
        titulo_id=np.arange(1, N + 1), tipo=tipo_txt, nome=cat["nomes"], ano_lancamento=cat["ano"],
        duracao_min=(cat["dur"], cat["tipo"] == 1), classificacao_indicativa=cat["clas"],
        original=cat["original"].astype(np.int8), estudio_id=cat["est"] + 1,
        idioma_original=cat["idioma"], pais_origem=cat["pais"],
        sinopse=np.array(cat["sinopses"], dtype=object))
    tg_t, tg_g, tg_p = [], [], []
    for i in range(N):
        tg_t.append(i + 1); tg_g.append(cat["gen"][i] + 1); tg_p.append(1)
        if cat["sec"][i] >= 0:
            tg_t.append(i + 1); tg_g.append(cat["sec"][i] + 1); tg_p.append(0)
    out["titulo_generos"] = dict(titulo_id=np.array(tg_t), genero_id=np.array(tg_g), principal=np.array(tg_p))
    te_t, te_p, te_f, te_o = [], [], [], []
    w = 1 / np.arange(1, npes + 1) ** .6
    w /= w.sum()
    for i in range(N):
        k = int(rng.integers(4, 9))
        ps = rng.choice(npes, k + 1, replace=False, p=w)
        for o, p in enumerate(ps[:-1]):
            te_t.append(i + 1); te_p.append(p + 1); te_f.append("elenco"); te_o.append(o + 1)
        te_t.append(i + 1); te_p.append(ps[-1] + 1); te_f.append("direcao"); te_o.append(1)
    out["titulo_elenco"] = dict(titulo_id=np.array(te_t), pessoa_id=np.array(te_p),
                                funcao=np.array(te_f, dtype=object), ordem=np.array(te_o))
    ep = cat["ep"]
    nomes_ep = []
    for t, temp, num in ep[:, :3]:
        r = rng.random()
        nomes_ep.append(f"Episódio {num}" if r < .35 else
                        f"{rng.choice(cat['ep_nomes'])}" if r < .75 else
                        f"{rng.choice(cat['ep_nomes'])} (Parte {1 + (num % 2)})")
    disp_ts = T0 + ep[:, 4] * DIA + 7 * 3600  # liberação às 04:00 de Brasília (07:00 UTC)
    out["episodios"] = dict(episodio_id=np.arange(1, len(ep) + 1), titulo_id=ep[:, 0] + 1,
                            temporada=ep[:, 1], numero=ep[:, 2], nome=np.array(nomes_ep, dtype=object),
                            duracao_min=ep[:, 3], disponivel_desde=disp_ts)
    d = cat["disp"]
    out["catalogo_disponibilidade"] = dict(
        disponibilidade_id=np.arange(1, len(d) + 1), titulo_id=np.array([x[0] + 1 for x in d]),
        entrada_em=np.array([x[1] for x in d]),
        saida_em=(np.array([0 if x[2] is None else x[2] for x in d]), np.array([x[2] is None for x in d])),
        tipo_licenca=np.array([x[3] for x in d], dtype=object))
    return out
