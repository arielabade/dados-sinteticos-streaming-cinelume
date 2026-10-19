"""Aquisição (canais, investimento), contas, perfis e dispositivos, com variáveis latentes."""
import re
import unicodedata

import numpy as np

from .config import (C_BUSCA, C_IND, C_OPER, C_ORG, C_SOCIAL, C_TV, DIA, G, GENEROS_INFANTIS,
                     MEMBRO_EXTRA, NDIAS, PARCERIA_OPERADORA, REAJUSTES, T0, TENTPOLES, TRIAL_ATE,
                     UF_NOME, UF_PESO, UF_REGIAO, UF_SIGLA, UF_TZ, dia)

DOMINIOS = ["webmail.example.com", "correio.example.net", "caixapostal.example.org",
            "mail.example.com", "provedor.example.net", "net.example.org", "mensagens.example.com"]
DOMINIOS_P = np.array([.34, .22, .12, .1, .09, .07, .06])
DOMINIO_EMPRESA = "cinelume.example"

TIPOS_DISP = np.array(["tv", "celular", "web", "tablet"])
PLAT = {0: (["tv_os_a", "tv_os_b"], [.55, .45]), 1: (["mobile_os_a", "mobile_os_b"], [.7, .3]),
        2: (["web"], [1.0]), 3: (["mobile_os_a", "mobile_os_b"], [.6, .4])}


def _slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^(dr|dra|sr|sra|srta)\.? ", "", s)
    return re.sub(r"[^a-z]+", ".", s).strip(".")


def janela_promo(d_arr):
    """Retorna código da promoção vigente no dia (ou '')."""
    from .config import INICIO
    import datetime as dt
    out = np.full(len(d_arr), "", dtype=object)
    for ano in (2023, 2024, 2025):
        a, b = dia(f"{ano}-11-20"), dia(f"{ano}-11-30")
        out[(d_arr >= a) & (d_arr <= b)] = f"BLACK50-{ano}"
    for nome, ini, fim in (("FERIAS24", "2024-07-01", "2024-07-31"), ("VERAO25", "2025-01-02", "2025-01-31"),
                           ("FERIAS25", "2025-07-01", "2025-07-31"), ("VERAO26", "2026-01-02", "2026-01-31"),
                           ("FERIAS26", "2026-07-01", "2026-07-31")):
        out[(d_arr >= dia(ini)) & (d_arr <= dia(fim))] = nome
    return out


def demanda(cal, rng):
    """Cadastros esperados por canal x dia (antes de escalar)."""
    d = np.arange(NDIAS)
    cresc = 0.8 + 0.45 * d / NDIAS
    saz = 1 + 0.35 * cal["ferias"] * np.isin(cal["mes"], [12, 1]) + 0.18 * (cal["mes"] == 7) \
        - 0.18 * cal["carnaval"] + 0.08 * (cal["dow"] >= 5) - 0.2 * cal["feriados"]
    tent = np.zeros(NDIAS)
    for ds, _ in TENTPOLES:
        t = dia(ds)
        m = d >= t
        tent[m] += 0.6 * np.exp(-(d[m] - t) / 6)
    promo = janela_promo(d)
    bf = np.array([p.startswith("BLACK") for p in promo])
    ferias_promo = (promo != "") & ~bf
    voo_tv = np.zeros(NDIAS)
    for ds, _ in TENTPOLES[::2]:
        t = dia(ds) - 5
        voo_tv[max(t, 0):t + 21] = 1
    for ano in (2023, 2024, 2025):
        t = dia(f"{ano}-11-13")
        voo_tv[t:t + 18] = 1
    share = np.array([.30, .18, .20, .09, .13, .10])
    m = np.ones((6, NDIAS))
    m[C_ORG] += 0.9 * tent
    m[C_ORG] += 0.25 * ((d >= MEMBRO_EXTRA) & (d < MEMBRO_EXTRA + 90))
    m[C_BUSCA] += 0.5 * tent
    m[C_SOCIAL] += 2.0 * bf + 0.6 * ferias_promo
    m[C_OPER] = np.clip((d - PARCERIA_OPERADORA) / 60, 0, 1)
    m[C_TV] = 0.25 + 3.2 * voo_tv
    for r in REAJUSTES:
        m[:, r:r + 30] *= 0.9
    E = share[:, None] * m * (cresc * saz * (1 + 0.5 * bf))[None, :]
    return E, voo_tv, bf


def investimento(E_real, cont, voo_tv, rng, cal):
    """Investimento diário, impressões, cliques e cadastros atribuídos por canal."""
    nc, nd = E_real.shape
    inv = np.zeros((nc, nd))
    imp = np.full((nc, nd), -1, np.int64)
    cli = np.full((nc, nd), -1, np.int64)
    atr = np.zeros((nc, nd), np.int64)
    ruido = lambda s: rng.lognormal(0, s, nd)
    # busca paga
    inv[C_BUSCA] = 46 * E_real[C_BUSCA] * ruido(.12)
    imp[C_BUSCA] = (inv[C_BUSCA] / 0.9 * 1000 / 30 * ruido(.1)).astype(np.int64)
    cli[C_BUSCA] = (imp[C_BUSCA] * 0.045 * ruido(.1)).astype(np.int64)
    # social pago (custo por cadastro sobe nos picos -> retorno decrescente)
    inv[C_SOCIAL] = 58 * E_real[C_SOCIAL] ** 1.08 * ruido(.15)
    imp[C_SOCIAL] = (inv[C_SOCIAL] / 11.5 * 1000 * ruido(.1)).astype(np.int64)
    cli[C_SOCIAL] = (imp[C_SOCIAL] * 0.009 * ruido(.15)).astype(np.int64)
    # TV: veiculação em flights, base pequena
    base_tv = 2500 * E_real.sum() / 120_000 / 1127 * 120
    inv[C_TV] = np.where(voo_tv > 0, 160 * E_real[C_TV] * ruido(.08), base_tv * ruido(.3) * 0.15)
    imp[C_TV] = (inv[C_TV] / 32 * 1000 * ruido(.1)).astype(np.int64)
    # parceria: fee por cadastro realizado
    inv[C_OPER] = 25.0 * cont[C_OPER]
    # indicação: crédito por cadastro indicado
    inv[C_IND] = 15.0 * cont[C_IND]
    # atribuição (last-click imperfeito)
    roubo = rng.binomial(cont[C_ORG], 0.22)
    atr[C_BUSCA] = rng.binomial(cont[C_BUSCA], 0.97) + roubo
    atr[C_SOCIAL] = rng.binomial(cont[C_SOCIAL], 0.78)
    atr[C_TV] = rng.binomial(cont[C_TV], 0.42)
    atr[C_OPER] = rng.binomial(cont[C_OPER], 0.96)
    atr[C_IND] = cont[C_IND] + rng.binomial(cont[C_ORG], 0.02)
    atr[C_ORG] = cont[C_ORG] - roubo + rng.binomial(cont[C_SOCIAL], 0.15) + rng.binomial(cont[C_TV], 0.3)
    # falhas de rastreamento
    for ds in ("2024-03-19", "2024-03-20", "2025-05-05", "2026-01-12"):
        k = dia(ds)
        atr[C_SOCIAL, k] = 0
        cli[C_SOCIAL, k] = 0
    return inv, imp, cli, atr


def gerar_contas(rng, fake, n_contas, cal):
    E, voo_tv, bf = demanda(cal, rng)
    E *= n_contas / E.sum()
    cont = rng.poisson(E)
    n = int(cont.sum())
    canal = np.repeat(np.tile(np.arange(6), NDIAS), cont.T.ravel())
    dia_cad = np.repeat(np.repeat(np.arange(NDIAS), 6), cont.T.ravel())
    # hora local do cadastro: pico noturno
    hora_loc = rng.choice(24, n, p=_dist_hora_cadastro())
    seg_loc = hora_loc * 3600 + rng.integers(0, 3600, n)
    uf = rng.choice(len(UF_SIGLA), n, p=UF_PESO)
    tz = UF_TZ[uf]
    regiao = UF_REGIAO[uf]
    t_cad = T0 + dia_cad * DIA + seg_loc - tz * 3600
    ordem = np.lexsort((t_cad,))
    canal, dia_cad, uf, tz, regiao, t_cad = canal[ordem], dia_cad[ordem], uf[ordem], tz[ordem], regiao[ordem], t_cad[ordem]
    dia_cad = ((t_cad - T0) // DIA).clip(0, NDIAS - 1)

    inv = investimento(E, cont, voo_tv, rng, cal)

    # ---------------------------------------------------------- latentes
    ch_mu = np.array([0.05, 0.0, -0.38, 0.28, -0.30, -0.05])
    eng_mu = rng.normal(ch_mu[canal], 0.72)
    extremo = rng.random(n) < 0.001
    eng_mu[extremo] += 2.6
    idade = np.clip(18 + rng.gamma(4.0, 5.2, n) - 5 * (canal == C_SOCIAL) + 6 * (canal == C_OPER), 18, 82).astype(int)
    ps = rng.normal(0, 1, n) + 0.25 * np.isin(regiao, [0, 1])
    promo = janela_promo(dia_cad)
    conn_mu = np.array([0.58, 0.66, 0.74, 0.80, 0.81])[regiao]
    conn = np.clip(rng.beta(conn_mu * 14, (1 - conn_mu) * 14), 0.05, 0.99)
    risco_pag = 0.4 * ps + rng.normal(0, 0.9, n)
    esquecido = rng.normal(0, 1, n)
    drift = rng.normal(-0.035, 0.07, n)
    compartilha = rng.random(n) < (0.12 * np.where(idade < 35, 1.35, 0.85))
    especial = np.zeros(n, np.int8)  # 1 funcionário, 2 teste, 3 bot
    r = rng.random(n)
    especial[r < 0.004] = 1
    especial[(r >= 0.004) & (r < 0.005)] = 2
    especial[(r >= 0.005) & (r < 0.007)] = 3
    compartilha &= especial == 0

    # ---------------------------------------------------------- plano, método, cupom
    cupom = np.full(n, "", dtype=object)
    u = rng.random(n)
    is_bf = np.array([p.startswith("BLACK") for p in promo])
    cupom[is_bf & (u < 0.7)] = promo[is_bf & (u < 0.7)]
    fp = (promo != "") & ~is_bf
    cupom[fp & (u < 0.5)] = promo[fp & (u < 0.5)]
    cupom[canal == C_OPER] = "PARCEIRO3M"
    sel = (canal == C_IND) & (rng.random(n) < 0.8)
    cupom[sel] = "INDICA30"
    sel = (canal == C_SOCIAL) & (cupom == "") & (rng.random(n) < 0.35)
    cupom[sel] = np.where(rng.random(sel.sum()) < .5, "CINE20", "MARATONA20")
    cupom[especial == 1] = "COLABORADOR"
    cupom[especial >= 2] = ""
    ps += 0.55 * (cupom != "") * (especial == 0)  # caçadores de promoção
    lg = np.stack([0.9 * ps + 0.1, np.zeros(n), -0.8 * ps - 0.35 + 0.45 * eng_mu], 1)
    pr = np.exp(lg)
    pr /= pr.sum(1, keepdims=True)
    plano = 1 + (rng.random(n)[:, None] > pr.cumsum(1)).sum(1)
    plano[especial == 1] = 3
    anual = (rng.random(n) < 1 / (1 + np.exp(2.3 + 0.8 * ps - 0.4 * eng_mu))) & (cupom == "") & (especial == 0)
    p_cartao = np.array([0.52, 0.56, 0.70, 0.76, 0.77])[regiao]
    um = rng.random(n)
    metodo = np.where(um < p_cartao, 0, np.where(um < p_cartao + (1 - p_cartao) * 0.65, 1, 2))
    metodo[especial > 0] = 0
    trial = (dia_cad < TRIAL_ATE) & (metodo == 0) & (cupom == "") & (especial == 0)

    # indicação: quem indicou (conta anterior com engajamento alto)
    promotor = np.where(eng_mu > np.quantile(eng_mu, 0.6))[0]
    indicada = np.full(n, -1)
    ii = np.where(canal == C_IND)[0]
    k = np.searchsorted(promotor, ii)  # promotores com índice menor
    ok = k > 0
    indicada[ii[ok]] = promotor[(rng.random(ok.sum()) * k[ok]).astype(int)]

    # ---------------------------------------------------------- dados pessoais (Faker pt_BR)
    nomes = np.empty(n, dtype=object)
    emails = np.empty(n, dtype=object)
    cpfs = np.empty(n, dtype=object)
    tels = np.empty(n, dtype=object)
    ceps = np.empty(n, dtype=object)
    cidades = np.empty(n, dtype=object)
    usados_e, usados_c = set(), set()
    dom = rng.choice(len(DOMINIOS), n, p=DOMINIOS_P)
    seps = rng.choice([".", "_", ""], n, p=[.5, .2, .3])
    nums = rng.integers(1, 9999, n)
    for i in range(n):
        if especial[i] == 2:
            nm = f"QA Teste {i:05d}"
            em = f"qa+{i:05d}@{DOMINIO_EMPRESA}"
        else:
            nm = fake.name()
            base = _slug(nm).split(".")
            if especial[i] == 1:
                em = f"{base[0]}.{base[-1]}@{DOMINIO_EMPRESA}"
            else:
                em = f"{base[0]}{seps[i]}{base[-1]}{nums[i] if rng.random() < .6 else ''}@{DOMINIOS[dom[i]]}"
        while em in usados_e:
            em = em.replace("@", f"{rng.integers(10, 99)}@")
        usados_e.add(em)
        c = fake.cpf()
        while c in usados_c:
            c = fake.cpf()
        usados_c.add(c)
        nomes[i], emails[i], cpfs[i] = nm, em, c
        tels[i] = fake.cellphone_number() if rng.random() < .8 else fake.phone_number()
        ceps[i] = fake.postcode()
        cidades[i] = fake.city()
    nasc_dia = (dia_cad - idade * 365.25 - rng.integers(0, 365, n)).astype(np.int64)
    uf_txt = UF_SIGLA[uf].astype(object)
    v = rng.random(n)
    var = v < 0.035
    for i in np.where(var)[0]:
        s = uf_txt[i]
        uf_txt[i] = [s.lower(), UF_NOME[s], f" {s}", f"{s} "][int(rng.integers(4))]
    nulos = dict(telefone=rng.random(n) < 0.08, data_nascimento=rng.random(n) < 0.12,
                 cep=rng.random(n) < 0.05)
    aceita_mkt = (rng.random(n) < 0.68).astype(np.int8)

    contas = dict(
        n=n, canal=canal, dia_cad=dia_cad, t_cad=t_cad, uf=uf, tz=tz, regiao=regiao,
        eng_mu=eng_mu, extremo=extremo, idade=idade, ps=ps, conn=conn, risco_pag=risco_pag,
        esquecido=esquecido, drift=drift, compartilha=compartilha, especial=especial,
        cupom=cupom, plano=plano, anual=anual, metodo=metodo, trial=trial, indicada=indicada,
        aceita_mkt=aceita_mkt, investimento=inv, cont=cont,
        tabela=dict(conta_id=np.arange(1, n + 1), email=emails, nome_titular=nomes, cpf=cpfs,
                    telefone=(tels, nulos["telefone"]),
                    data_nascimento=(nasc_dia, nulos["data_nascimento"]),
                    cep=(ceps, nulos["cep"]), cidade=cidades, uf=uf_txt, criada_em=t_cad,
                    canal_aquisicao_id=canal + 1,
                    indicada_por_conta_id=(indicada + 1, indicada < 0), aceita_marketing=aceita_mkt),
    )
    return contas


def _dist_hora_cadastro():
    w = np.array([2, 1.2, .7, .4, .3, .4, .8, 1.5, 2.5, 3, 3.2, 3.3, 3.6, 3.4, 3.2, 3.2, 3.4, 3.8,
                  4.5, 5.2, 6, 6.3, 5.5, 3.6])
    return w / w.sum()


def gerar_perfis_dispositivos(rng, fake, ct, cat):
    n = ct["n"]
    plano, comp, esp = ct["plano"], ct["compartilha"], ct["especial"]
    probs = {1: [.35, .35, .18, .08, .04], 2: [.2, .32, .26, .14, .08], 3: [.1, .25, .3, .2, .15]}
    n_hh = np.empty(n, int)
    for p in (1, 2, 3):
        m = plano == p
        n_hh[m] = 1 + rng.choice(5, m.sum(), p=probs[p])
    n_hh[comp] = np.minimum(n_hh[comp], 4)
    n_hh[esp >= 2] = 1
    n_prof = n_hh + comp
    P = int(n_prof.sum())
    pc = np.repeat(np.arange(n), n_prof)
    pos = np.arange(P) - np.repeat(np.cumsum(n_prof) - n_prof, n_prof)
    principal = pos == 0
    sharer = comp[pc] & (pos == n_prof[pc] - 1)
    infantil = np.zeros(P, bool)
    cand = (~principal) & (~sharer) & (n_hh[pc] >= 3)
    first_cand = cand & (pos == 1)
    infantil[first_cand] = rng.random(first_cand.sum()) < 0.45
    peso = np.where(principal, 1.0, rng.lognormal(-0.6, 0.6, P))
    peso[infantil] = 0.6 * rng.lognormal(0, .3, infantil.sum())
    peso[sharer] = 1.3 * rng.lognormal(0, .3, sharer.sum())
    # criação
    d0 = ct["dia_cad"][pc]
    atraso = np.where(rng.random(P) < 0.7, rng.integers(0, 3, P), rng.exponential(60, P).astype(int))
    criado_dia = np.where(principal, d0, d0 + atraso)
    criado_dia[sharer] = d0[sharer] + rng.integers(0, 20, sharer.sum())
    fora = criado_dia >= NDIAS
    criado_dia[fora] = d0[fora] + (rng.random(fora.sum()) * (NDIAS - d0[fora])).astype(int)
    t_criado = np.where(principal, ct["t_cad"][pc] + 60, T0 + criado_dia * DIA + rng.integers(0, DIA, P))
    # preferências de gênero (conta + perfil)
    base = np.array([1.1, .7, .6, 1.3, .8, .5, 1.4, .6, .7, .3, .15, .8, 1.0, .6, .4, .3])
    acc_pref = rng.dirichlet(base * 1.2, n)
    soc = ct["canal"] == C_SOCIAL
    acc_pref[soc, G["Terror"]] += 0.12
    acc_pref /= acc_pref.sum(1, keepdims=True)
    own = rng.dirichlet(base * 0.8, P)
    pref = 0.55 * acc_pref[pc] + 0.45 * own
    kid = np.full(16, 0.01)
    kid[GENEROS_INFANTIS] = [0.55, 0.4]
    pref[infantil] = rng.dirichlet(kid * 20, infantil.sum())
    pref /= pref.sum(1, keepdims=True)
    binge = rng.beta(2.2, 2.0, P)
    binge[infantil] = np.clip(binge[infantil] + .15, 0, .95)
    telemetria = rng.random(P) < 0.05
    nomes = np.array(cat["primeiros"], dtype=object)[rng.integers(0, len(cat["primeiros"]), P)]
    alt = rng.random(P)
    nomes[infantil] = rng.choice(["Infantil", "Kids", "Crianças", "Pequenos"], infantil.sum())
    nomes[(~principal) & (~infantil) & (alt < .06)] = "Sala"

    # região do perfil compartilhado (outro domicílio)
    reg_perfil = ct["regiao"][pc].copy()
    uf_perfil = ct["uf"][pc].copy()
    ufs_sh = rng.choice(len(UF_SIGLA), sharer.sum(), p=UF_PESO)
    mesma = rng.random(sharer.sum()) < 0.35
    uf_perfil[sharer] = np.where(mesma, uf_perfil[sharer], ufs_sh)
    reg_perfil = UF_REGIAO[uf_perfil]

    # ---------------------------------------------------------- dispositivos
    reg = ct["regiao"]
    p_tv = np.where(np.isin(reg, [0, 1]), 0.62, 0.8)
    p_web = np.where(ct["canal"] == C_SOCIAL, 0.62, 0.3)
    has = np.stack([rng.random(n) < p_tv, rng.random(n) < 0.92, rng.random(n) < p_web,
                    rng.random(n) < 0.22], 1)
    has[~has.any(1), 1] = True
    has[esp == 3] = [False, False, True, False]
    has[esp == 2] = [True, True, True, True]
    dev_conta, dev_tipo, dev_dono = [], [], []
    for t in range(4):
        idx = np.where(has[:, t])[0]
        dev_conta.append(idx); dev_tipo.append(np.full(len(idx), t)); dev_dono.append(np.full(len(idx), -1))
    sh_idx = np.where(sharer)[0]
    dev_conta.append(pc[sh_idx]); dev_tipo.append(np.full(len(sh_idx), 1)); dev_dono.append(sh_idx)
    tv_sh = sh_idx[rng.random(len(sh_idx)) < 0.5]
    dev_conta.append(pc[tv_sh]); dev_tipo.append(np.full(len(tv_sh), 0)); dev_dono.append(tv_sh)
    dc, dt_, dd = np.concatenate(dev_conta), np.concatenate(dev_tipo), np.concatenate(dev_dono)
    o = np.lexsort((dt_, dc))
    dc, dt_, dd = dc[o], dt_[o], dd[o]
    D = len(dc)
    plat = np.empty(D, dtype=object)
    for t in range(4):
        m = dt_ == t
        nomes_p, pp = PLAT[t]
        plat[m] = np.array(nomes_p, dtype=object)[rng.choice(len(nomes_p), m.sum(), p=pp)]
    reg_dia = ct["dia_cad"][dc] + np.where(rng.random(D) < .6, 0, rng.exponential(45, D).astype(int))
    reg_dia = np.where(dd >= 0, criado_dia[np.maximum(dd, 0)], reg_dia)
    reg_dia = np.minimum(reg_dia, NDIAS - 1)
    t_reg = T0 + reg_dia * DIA + rng.integers(0, DIA, D)
    relogio = np.zeros(D, np.int64)  # deslocamento de relógio (s) — imperfeição
    ruim = rng.random(D) < 0.015
    tipo_off = rng.choice(4, ruim.sum(), p=[.35, .3, .2, .15])
    off = np.select([tipo_off == 0, tipo_off == 1, tipo_off == 2],
                    [rng.choice([-1, 1], ruim.sum()) * 3600,
                     rng.choice([-1, 1], ruim.sum()) * rng.integers(2, 13, ruim.sum()) * 3600,
                     rng.integers(1, 40, ruim.sum()) * DIA * rng.choice([-1, 1], ruim.sum())],
                    -1)  # -1 => reset para 2000-01-01
    relogio[ruim] = off
    atraso_versao = np.where(dt_ == 2, 0, np.where(dt_ == 0, rng.exponential(22, D), rng.exponential(7, D))).astype(int)
    atraso_versao[rng.random(D) < 0.03] += 200  # dispositivos que quase nunca atualizam

    # mapa perfil -> até 4 dispositivos com pesos
    first_dev = np.searchsorted(dc, np.arange(n))
    n_dev = np.bincount(dc, minlength=n)
    pdev = np.full((P, 4), -1, np.int64)
    pw = np.zeros((P, 4))
    tw = np.array([0.5, 0.3, 0.12, 0.08])
    hh_dev_mask = dd < 0
    for p in range(P):
        c = pc[p]
        idx = np.arange(first_dev[c], first_dev[c] + n_dev[c])
        if sharer[p]:
            idx = idx[dd[idx] == p]
        else:
            idx = idx[hh_dev_mask[idx]][:4]
        w = tw[dt_[idx]] * rng.lognormal(0, .5, len(idx))
        if infantil[p]:
            w = w * np.where(np.isin(dt_[idx], [0, 3]), 3, .3)
        pdev[p, :len(idx)] = idx
        pw[p, :len(idx)] = w / w.sum()
    principal_tipo = dt_[pdev[np.arange(P), pw.argmax(1)]]

    tipo_txt = TIPOS_DISP[dt_].astype(object)
    var = rng.random(D) < 0.025
    variantes = {"tv": ["TV", "Smart TV", "tv "], "celular": ["Celular", "smartphone", "mobile"],
                 "web": ["WEB", "navegador", "Web"], "tablet": ["Tablet", "tablet ", "TABLET"]}
    for i in np.where(var)[0]:
        tipo_txt[i] = variantes[tipo_txt[i]][int(rng.integers(3))]

    perfis = dict(
        P=P, pc=pc, principal=principal, sharer=sharer, infantil=infantil, peso=peso,
        criado_dia=criado_dia, pref=pref, binge=binge, telemetria=telemetria, uf=uf_perfil,
        regiao=reg_perfil, pdev=pdev, pw=pw, dev_tipo_principal=principal_tipo,
        tabela=dict(perfil_id=np.arange(1, P + 1), conta_id=pc + 1, nome=nomes,
                    infantil=infantil.astype(np.int8), principal=principal.astype(np.int8),
                    telemetria_detalhada=telemetria.astype(np.int8), criado_em=t_criado),
    )
    disp = dict(D=D, conta=dc, tipo=dt_, dono=dd, plat=plat, relogio=relogio, atraso_versao=atraso_versao,
                tabela=dict(dispositivo_id=np.arange(1, D + 1), conta_id=dc + 1, tipo=tipo_txt,
                            plataforma=plat, registrado_em=t_reg))
    return perfis, disp
