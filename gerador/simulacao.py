"""Simulação dia a dia do ciclo de vida das contas (processo gerador com variáveis latentes)."""
import numpy as np

from .config import (C_IND, C_OPER, C_SOCIAL, DIA, G, MEMBRO_EXTRA, NDIAS, REAJUSTES, SAIDA_LOTE,
                     T0, TABELA_PRECOS, PRECOS_EXTRA, TENTPOLES, BUG_INI, BUG_FIM, dia)

# parâmetros calibrados (ver _gabarito)
PARAM = dict(
    base_plays=0.128,     # taxa base de reproduções por perfil-dia
    base_browse=0.045,    # sessões só de navegação por perfil-dia
    h0=0.00024,           # hazard diário base de cancelamento voluntário
    r0=0.0017,            # hazard diário base de reativação
)

# códigos
ST_NADA, ST_TRIAL, ST_ATIVA, ST_INAD, ST_CANC, ST_FIM = range(6)
EV = ["assinatura_criada", "trial_iniciado", "trial_convertido", "upgrade", "downgrade",
      "metodo_pagamento_alterado", "inadimplencia_iniciada", "inadimplencia_resolvida",
      "cancelamento_solicitado", "encerrada", "reativada", "membro_extra_adicionado",
      "membro_extra_removido"]
E = {n: i for i, n in enumerate(EV)}
ORIGENS = ["app", "web", "suporte", "sistema"]
CUPONS = [
    # codigo, descricao, tipo, valor, ciclos, de, ate, canal_id, apenas_novos
    ("BLACK50-2023", "Black Friday 2023: 50% por 3 meses", "percentual", 50, 3, "2023-11-20", "2023-11-30", None, 1),
    ("BLACK50-2024", "Black Friday 2024: 50% por 3 meses", "percentual", 50, 3, "2024-11-20", "2024-11-30", None, 1),
    ("BLACK50-2025", "Black Friday 2025: 50% por 3 meses", "percentual", 50, 3, "2025-11-20", "2025-11-30", None, 1),
    ("FERIAS24", "Férias de julho: primeiro mês com 70% de desconto", "percentual", 70, 1, "2024-07-01", "2024-07-31", None, 1),
    ("VERAO25", "Verão: primeiro mês com 70% de desconto", "percentual", 70, 1, "2025-01-02", "2025-01-31", None, 1),
    ("FERIAS25", "Férias de julho: primeiro mês com 70% de desconto", "percentual", 70, 1, "2025-07-01", "2025-07-31", None, 1),
    ("VERAO26", "Verão: primeiro mês com 70% de desconto", "percentual", 70, 1, "2026-01-02", "2026-01-31", None, 1),
    ("FERIAS26", "Férias de julho: primeiro mês com 70% de desconto", "percentual", 70, 1, "2026-07-01", "2026-07-31", None, 1),
    ("PARCEIRO3M", "Parceria operadora: 50% por 3 meses", "percentual", 50, 3, "2024-03-01", None, 5, 1),
    ("INDICA30", "Indicação: 30% no primeiro mês", "percentual", 30, 1, "2023-10-01", None, 4, 1),
    ("CINE20", "Campanha social: 20% por 2 meses", "percentual", 20, 2, "2023-10-01", None, 3, 1),
    ("MARATONA20", "Campanha social: 20% por 2 meses", "percentual", 20, 2, "2024-01-15", None, 3, 1),
    ("VOLTA50", "Reconquista: 50% por 2 meses", "percentual", 50, 2, "2023-10-01", None, None, 0),
    ("COLABORADOR", "Benefício de colaborador", "percentual", 100, 999, "2023-10-01", None, None, 0),
]
CUP = {c[0]: (i, c[3] / 100, c[4]) for i, c in enumerate(CUPONS)}
MOTIVOS = ["preco", "pouco_uso", "catalogo", "terminei_o_que_queria", "problemas_tecnicos",
           "compartilhamento", "financeiro", "temporario", "outro"]
CODIGOS_RECUSA = ["saldo_insuficiente", "cartao_expirado", "nao_autorizado", "erro_emissor", "suspeita_fraude"]
CAMPANHAS = ["novo_episodio", "destaques_semana", "reengajamento", "falha_pagamento", "aviso_reajuste",
             "lancamento_original", "winback"]
CATEG_TICKET = ["pagamento", "cobranca", "reproducao", "acesso_login", "conteudo", "cancelamento", "outros"]


def tabela_precos():
    rows = []  # preco_id, plano, item, periodicidade, valor, ini, fim
    mapa = np.zeros((3, 3, 2), np.int32)
    val = np.zeros((3, 3, 2))
    pid = 1
    for v, (ini, fim, tab) in enumerate(TABELA_PRECOS):
        for pl in (1, 2, 3):
            for a, per in enumerate(("mensal", "anual")):
                rows.append((pid, pl, "assinatura", per, tab[pl][a], ini, fim))
                mapa[v, pl - 1, a] = pid
                val[v, pl - 1, a] = tab[pl][a]
                pid += 1
    extra_ids = []
    for ini, fim, vx in PRECOS_EXTRA:
        rows.append((pid, None, "membro_extra", "mensal", vx, ini, fim))
        extra_ids.append(pid)
        pid += 1
    return rows, mapa, val, extra_ids


def _sig(x):
    return 1 / (1 + np.exp(-x))


class Log:
    """Acumula colunas em listas de arrays e concatena no final."""

    def __init__(self, *cols):
        self.cols = cols
        self.d = {c: [] for c in cols}

    def add(self, **kw):
        tam = [len(kw[c]) for c in self.cols if np.ndim(kw[c]) > 0]
        n = max(tam) if tam else 1
        if not n:
            return
        for c in self.cols:
            v = kw[c]
            v = np.full(n, v) if np.ndim(v) == 0 else np.asarray(v)
            assert len(v) == n, (c, len(v), n)
            self.d[c].append(v)

    def cat(self):
        return {c: (np.concatenate(v) if v else np.array([])) for c, v in self.d.items()}

    def __len__(self):
        return sum(len(v) for v in self.d[self.cols[0]])


def simular(rng, cal, cat, ct, pf, dv, log=print):
    N, P = ct["n"], pf["P"]
    pc = pf["pc"]
    precos_rows, pmapa, pval, extra_ids = tabela_precos()
    vig = np.zeros(NDIAS, np.int8)
    vig[REAJUSTES[0]:] = 1
    vig[REAJUSTES[1]:] = 2
    extra_val = np.where(np.arange(NDIAS) >= REAJUSTES[1], 13.90, 12.90)
    extra_pid = np.where(np.arange(NDIAS) >= REAJUSTES[1], extra_ids[1], extra_ids[0])
    price_win = np.zeros(NDIAS, bool)
    for r in REAJUSTES:
        price_win[r - 30:r + 45] = True
    saz_view = 1 + np.select([cal["dow"] == 4, cal["dow"] == 5, cal["dow"] == 6], [0.15, 0.3, 0.25], 0) \
        + 0.12 * cal["ferias"] - 0.22 * cal["carnaval"] - 0.3 * cal["feriados"] + 0.08 * np.isin(cal["mes"], [6, 7, 8])
    saz_churn = 0.22 * np.isin(cal["mes"], [2, 3]) - 0.15 * (cal["mes"] == 12)
    tent_dias = np.array([dia(t) for t, _ in TENTPOLES])
    tent_gen = np.array([G[g] for _, g in TENTPOLES])

    # ------------------------------------------------------------------ estado por conta
    st = np.zeros(N, np.int8)
    sub = np.full(N, -1, np.int32)
    plano = ct["plano"].astype(np.int8).copy()
    anual = ct["anual"].copy()
    metodo = ct["metodo"].astype(np.int8).copy()
    prox = np.full(N, 10 ** 6, np.int32)
    trial_fim = np.full(N, -1, np.int32)
    res_dia = np.full(N, -1, np.int32)
    res_ok = np.zeros(N, bool)
    res_fat = np.full(N, -1, np.int64)
    cup_cic = np.zeros(N, np.int16)
    cup_pct = np.zeros(N)
    cup_resg = np.full(N, -1, np.int32)
    promo_fim = np.full(N, -999, np.int32)
    eng = ct["eng_mu"].copy()
    buf = np.full(N, 0.35)
    last_inv_dia = np.full(N, -999, np.int32)
    last_inv_idx = np.full(N, -1, np.int64)
    last_inv_pago = np.zeros(N, bool)
    fim_dia = np.full(N, -1, np.int32)
    tipo_fim = np.zeros(N, np.int8)  # 1 voluntário, 2 involuntário
    extra_ativo = np.zeros(N, np.int8)
    sh_status = np.zeros(N, np.int8)  # 0 pendente, 1 pagou, 2 removeu, 3 bloqueado
    sh_dec = np.where(ct["compartilha"], MEMBRO_EXTRA + rng.integers(0, 45, N), 10 ** 6)
    perda_sh_ate = np.full(N, -1, np.int32)
    ticket_ate = np.full(N, -1, np.int32)
    winback_ate = np.full(N, -1, np.int32)
    last_play = np.full(N, -999, np.int32)
    ten0 = ct["dia_cad"]
    canal = ct["canal"]
    esp = ct["especial"]
    ps_pos = np.clip(ct["ps"], 0, None)
    ch_eff = np.array([0.0, 0.06, 0.38, -0.38, -1.25, 0.02])[canal]
    has_tv = np.zeros(N, bool)
    has_tv[dv["conta"][dv["tipo"] == 0]] = True
    # perfil principal de cada conta
    princ = np.where(pf["principal"])[0]
    pref_acc = pf["pref"][princ]
    mobile_first = np.isin(pf["dev_tipo_principal"][princ], [1, 3])
    devf = np.array([0.8, 1.3, 1.0, 1.1])[pf["dev_tipo_principal"][princ]]
    buf_base = 0.35 * np.exp(2.2 * (0.75 - ct["conn"])) * devf
    lote_fa = pref_acc[:, G["Comédia"]] > np.quantile(pref_acc[:, G["Comédia"]], 0.72)
    sharer_idx = np.full(N, -1, np.int64)
    sharer_idx[pc[pf["sharer"]]] = np.where(pf["sharer"])[0]

    # ------------------------------------------------------------------ estado por perfil
    cur = np.full(P, -1, np.int32)
    ptr = np.zeros(P, np.int32)
    aguarda = np.full(P, -1, np.int32)
    last_ser = np.full(P, -1, np.int32)
    fim_ser = np.full(P, -999, np.int32)
    perdeu_ate = np.full(P, -1, np.int32)
    boost_ate = np.full(P, -1, np.int32)
    boost_f = np.ones(P)
    excluido = np.full(P, 10 ** 6, np.int32)
    membro_extra = np.zeros(P, np.int8)
    bloqueado = np.zeros(P, bool)
    log_peso = np.log(pf["peso"])
    binge = pf["binge"]
    pref = pf["pref"]
    # exclusões aleatórias de perfis (não principais)
    r = rng.random(P)
    exc = (~pf["principal"]) & (~pf["sharer"]) & (r < 0.04)
    excluido[exc] = pf["criado_dia"][exc] + rng.integers(20, 500, exc.sum())

    # séries
    S = cat["S"]
    ser_gen = cat["gen"][cat["ser_tit"]]
    ser_pop = cat["pop"][cat["ser_tit"]]
    ser_orig = cat["original"][cat["ser_tit"]]
    ser_lanc = cat["lanc"][cat["ser_tit"]]
    eps_disp = cat["eps_disp"]
    n_tot = cat["n_eps_total"]
    ser_fim = cat["ser_fim"]
    rel_last = np.full(S, -999, np.int32)

    # ------------------------------------------------------------------ registros
    S_CAP = int(N * 2.2) + 100
    s_conta = np.zeros(S_CAP, np.int32)
    s_plano = np.zeros(S_CAP, np.int8)
    s_anual = np.zeros(S_CAP, bool)
    s_metodo = np.zeros(S_CAP, np.int8)
    s_ini = np.zeros(S_CAP, np.int64)
    s_trial = np.full(S_CAP, -1, np.int64)
    s_creq = np.full(S_CAP, -1, np.int64)
    s_fim = np.full(S_CAP, -1, np.int64)
    s_tfim = np.zeros(S_CAP, np.int8)
    s_ant = np.full(S_CAP, -1, np.int32)
    ns = 0
    ev = Log("sub", "tipo", "t", "pa", "pn", "origem")
    fat = Log("idx", "sub", "conta", "preco", "resg", "ini", "fim", "emit", "venc", "bruto", "desc", "extra", "total")
    fat_n = [0]
    fat_upd = Log("idx", "status")  # 0 paga 1 aberta 2 vencida 3 cancelada 4 reembolsada 5 estornada
    pag = Log("fat", "conta", "metodo", "tipo", "tent", "t", "valor", "status", "codigo")
    resg = Log("cupom", "conta", "sub", "t")
    resg_n = [0]
    pesq = Log("sub", "conta", "t", "motivo", "coment", "prob")
    tick = Log("conta", "t", "canal", "cat", "status", "res_t", "nota")
    nps = Log("conta", "t", "nota", "canal")
    notif = Log("conta", "perfil", "canal", "camp", "titulo", "t", "ab", "cl")
    agg = Log("perfil", "dia", "n", "nser", "ser", "ptr0", "plano")
    browse = Log("perfil", "dia", "n")
    acoes = Log("conta", "dia", "tipo")  # 0 abrir_tela_planos, 1 tentativa_cancelamento
    esp_dias = Log("conta", "dia")
    churn_log = Log("conta", "dia", "tipo")  # fim de assinatura (1 vol, 2 inv) — uso interno p/ gabarito
    cancel_causa = Log("conta", "dia", "causa")

    def hora(n, ini=9, fim=23):
        return rng.integers(ini * 3600, fim * 3600, n)

    def tloc(idx, d, seg):
        """segundos locais do dia -> epoch UTC"""
        return T0 + d * DIA + seg - ct["tz"][idx] * 3600

    def nova_sub(idx, d, t, ant=None):
        nonlocal ns
        k = len(idx)
        ids = np.arange(ns, ns + k)
        ns += k
        s_conta[ids] = idx
        s_plano[ids] = plano[idx]
        s_anual[ids] = anual[idx]
        s_metodo[ids] = metodo[idx]
        s_ini[ids] = t
        if ant is not None:
            s_ant[ids] = ant
        sub[idx] = ids
        return ids

    def evento(idx, tipo, t, pa=-1, pn=-1, origem=3):
        if len(idx):
            ev.add(sub=sub[idx], tipo=E[tipo], t=t, pa=pa, pn=pn, origem=origem)

    def resgatar(idx, codigo, t):
        if not len(idx):
            return
        cid, pct, cic = CUP[codigo]
        ids = np.arange(resg_n[0], resg_n[0] + len(idx))
        resg_n[0] += len(idx)
        resg.add(cupom=cid, conta=idx, sub=sub[idx], t=t)
        cup_cic[idx] = cic
        cup_pct[idx] = pct
        cup_resg[idx] = ids

    def notificar(idx, perfil, canal_n, camp, titulo, t, p_ab, p_cl):
        k = len(idx)
        if not k:
            return
        ab = rng.random(k) < p_ab
        cl = ab & (rng.random(k) < p_cl)
        t_ab = np.where(ab, t + rng.exponential(5 * 3600, k).astype(np.int64) + 30, -1)
        t_cl = np.where(cl, t_ab + rng.integers(2, 120, k), -1)
        notif.add(conta=idx, perfil=perfil, canal=canal_n, camp=CAMPANHAS.index(camp), titulo=titulo,
                  t=t, ab=t_ab, cl=t_cl)

    def ticket(idx, d, categoria, canal_p=None):
        k = len(idx)
        if not k:
            return
        t = tloc(idx, d, hora(k, 8, 23))
        c = rng.choice(3, k, p=[.55, .3, .15]) if canal_p is None else np.full(k, canal_p)
        u = rng.random(k)
        status = np.where(u < 0.84, 1, 2)  # 1 resolvido, 2 fechado sem resolução
        res_t = np.where(status == 1, t + (rng.lognormal(2.6, 1.1, k) * 3600).astype(np.int64), -1)
        aberto = res_t > T0 + NDIAS * DIA
        status = np.where(aberto, 0, status)
        res_t = np.where(aberto, -1, res_t)
        nota = np.where(status == 1, rng.choice([2, 3, 4, 5, 5], k), rng.choice([1, 1, 2, 3], k))
        nota = np.where(rng.random(k) < 0.55, -1, nota)
        tick.add(conta=idx, t=t, canal=c, cat=CATEG_TICKET.index(categoria), status=status, res_t=res_t, nota=nota)
        sem_sol = idx[status != 1]
        ticket_ate[sem_sol] = d + 30

    def cobrar(idx, d, t_emit=None):
        """Emite fatura do ciclo que começa em d e simula o pagamento."""
        k = len(idx)
        if not k:
            return
        v = vig[d]
        an = anual[idx].astype(int)
        pid = pmapa[v, plano[idx] - 1, an]
        bruto = pval[v, plano[idx] - 1, an]
        tem_cup = cup_cic[idx] > 0
        desc = np.where(tem_cup, np.round(bruto * cup_pct[idx], 2), 0.0)
        resg_id = np.where(tem_cup, cup_resg[idx], -1)
        cup_cic[idx] = np.where(tem_cup, cup_cic[idx] - 1, 0)
        fimp = np.where(an == 1, cal["prox_ano"][d], cal["prox_mes"][d])
        acabou = tem_cup & (cup_cic[idx] == 0)
        promo_fim[idx[acabou]] = fimp[acabou]
        extra = extra_ativo[idx] * extra_val[d]
        total = np.round(bruto - desc + extra, 2)
        if t_emit is None:
            t_emit = T0 + d * DIA + rng.integers(3 * 3600, 7 * 3600, k)
        venc = np.where(metodo[idx] == 0, d, d + 3)
        fidx = np.arange(fat_n[0], fat_n[0] + k)
        fat_n[0] += k
        fat.add(idx=fidx, sub=sub[idx], conta=idx, preco=pid, resg=resg_id, ini=d, fim=fimp - 1,
                emit=t_emit, venc=venc, bruto=bruto, desc=desc, extra=extra, total=total)
        prox[idx] = fimp
        last_inv_dia[idx] = d
        last_inv_idx[idx] = fidx
        pago_agora = np.zeros(k, bool)
        u = rng.random(k)
        # -------- cartão
        mc = metodo[idx] == 0
        zero = total <= 0
        bot = esp[idx] == 3
        p1 = _sig(-3.3 + 0.95 * ct["risco_pag"][idx] + 0.5 * (cal["dom"][d] >= 25))
        p1 = np.where(bot, 0.02, p1)
        falha = mc & ~zero & (u < p1)
        ok1 = mc & ~falha
        ii = np.where(ok1)[0]
        pag.add(fat=fidx[ii], conta=idx[ii], metodo=0, tipo=0, tent=1, t=t_emit[ii] + rng.integers(5, 90, len(ii)),
                valor=total[ii], status=0, codigo=-1)
        pago_agora[ii] = True
        ii = np.where(falha)[0]
        if len(ii):
            cod = rng.choice(5, len(ii), p=[.45, .2, .2, .1, .05])
            pag.add(fat=fidx[ii], conta=idx[ii], metodo=0, tipo=0, tent=1, t=t_emit[ii] + rng.integers(5, 90, len(ii)),
                    valor=total[ii], status=1, codigo=cod)
            p_rec = np.where(cod == 1, 0.15, np.where(cod == 4, 0.08, 0.36)) + 0.06 * (ct["risco_pag"][idx[ii]] < 0)
            ok_at = np.full(len(ii), -1)
            for j, dd in enumerate((1, 3, 7)):
                pend = ok_at < 0
                suc = pend & (rng.random(len(ii)) < p_rec)
                tt = T0 + (d + dd) * DIA + rng.integers(6 * 3600, 14 * 3600, len(ii))
                sel = np.where(pend)[0]
                pag.add(fat=fidx[ii[sel]], conta=idx[ii[sel]], metodo=0, tipo=0, tent=j + 2, t=tt[sel],
                        valor=total[ii[sel]], status=np.where(suc[sel], 0, 1),
                        codigo=np.where(suc[sel], -1, cod[sel]))
                ok_at[suc] = dd
            a = idx[ii]
            st[a] = ST_INAD
            res_dia[a] = d + np.where(ok_at > 0, ok_at, 7)
            res_ok[a] = ok_at > 0
            res_fat[a] = fidx[ii]
            evento(a, "inadimplencia_iniciada", t_emit[ii] + 120)
            notificar(a, -1, 1, "falha_pagamento", -1, t_emit[ii] + 600, _sig(0.5 + 0.4 * eng[a]), 0.5)
            tk = a[rng.random(len(a)) < 0.12]
            ticket(tk, d, "pagamento")
        # -------- pix / boleto
        mm = (~mc) & ~zero
        ii = np.where(mm)[0]
        if len(ii):
            a = idx[ii]
            pp = _sig(4.25 + 1.0 * eng[a] - 0.95 * ct["esquecido"][a] - 0.6 * ps_pos[a] * price_win[d]
                      - 0.5 * (metodo[a] == 2))
            paga = rng.random(len(ii)) < pp
            atraso = np.where(rng.random(len(ii)) < 0.13, rng.integers(4, 10, len(ii)), rng.integers(0, 4, len(ii)))
            tpay = tloc(a, d + atraso, hora(len(ii), 7, 23))
            sel = np.where(paga)[0]
            pag.add(fat=fidx[ii[sel]], conta=a[sel], metodo=metodo[a[sel]], tipo=0, tent=1, t=tpay[sel],
                    valor=total[ii[sel]], status=0, codigo=-1)
            pago_agora[ii[sel[atraso[sel] <= 3]]] = True
            tarde = paga & (atraso > 3)
            st[a[tarde]] = ST_INAD
            res_dia[a[tarde]] = d + atraso[tarde]
            res_ok[a[tarde]] = True
            res_fat[a[tarde]] = fidx[ii[tarde]]
            evento(a[tarde], "inadimplencia_iniciada", T0 + (d + 4) * DIA + 3 * 3600)
            sel = np.where(~paga)[0]
            pag.add(fat=fidx[ii[sel]], conta=a[sel], metodo=metodo[a[sel]], tipo=0, tent=1,
                    t=T0 + (d + 4) * DIA + 3 * 3600 + rng.integers(0, 600, len(sel)),
                    valor=total[ii[sel]], status=2, codigo=-1)
            st[a[sel]] = ST_INAD
            res_dia[a[sel]] = d + 10
            res_ok[a[sel]] = False
            res_fat[a[sel]] = fidx[ii[sel]]
            evento(a[sel], "inadimplencia_iniciada", T0 + (d + 4) * DIA + 3 * 3600)
        # zero (colaborador)
        ii = np.where(zero)[0]
        pag.add(fat=fidx[ii], conta=idx[ii], metodo=metodo[idx[ii]], tipo=0, tent=1, t=t_emit[ii] + 30,
                valor=0.0, status=0, codigo=-1)
        pago_agora[ii] = True
        last_inv_pago[idx] = pago_agora
        # chargebacks (bots e raros legítimos)
        cb = np.where(mc & ~zero & (pago_agora | falha) & ((bot & (rng.random(k) < 0.45)) | (rng.random(k) < 0.0012)))[0]
        if len(cb):
            tcb = t_emit[cb] + rng.integers(20, 75, len(cb)) * DIA
            dentro = tcb < T0 + NDIAS * DIA
            cb = cb[dentro]
            tcb = tcb[dentro]
            # só para faturas que de fato foram pagas
            pagas = pago_agora[cb]
            cb, tcb = cb[pagas], tcb[pagas]
            pag.add(fat=fidx[cb], conta=idx[cb], metodo=0, tipo=2, tent=1, t=tcb, valor=-total[cb], status=3, codigo=-1)
            fat_upd.add(idx=fidx[cb], status=5)

    def encerrar(idx, d, tipo, t):
        st[idx] = ST_FIM
        fim_dia[idx] = d
        tipo_fim[idx] = tipo
        s_fim[sub[idx]] = t
        s_tfim[sub[idx]] = tipo
        evento(idx, "encerrada", t)
        churn_log.add(conta=idx, dia=d, tipo=tipo)

    # ordem de cadastro
    ini_dia = np.searchsorted(ten0, np.arange(NDIAS + 1))
    tz_off = -ct["tz"] * 3600

    for d in range(NDIAS):
        # ============================================================== A. novos cadastros
        novos = np.arange(ini_dia[d], ini_dia[d + 1])
        if len(novos):
            t = ct["t_cad"][novos] + rng.integers(30, 600, len(novos))
            nova_sub(novos, d, t)
            evento(novos, "assinatura_criada", t, pn=plano[novos], origem=1)
            eng[novos] = ct["eng_mu"][novos] + 0.35
            tr = novos[ct["trial"][novos]]
            st[tr] = ST_TRIAL
            trial_fim[tr] = d + 7
            s_trial[sub[tr]] = t[ct["trial"][novos]] + 7 * DIA
            evento(tr, "trial_iniciado", t[ct["trial"][novos]] + 5)
            pg = novos[~ct["trial"][novos]]
            st[pg] = ST_ATIVA
            for codigo in np.unique(ct["cupom"][pg]):
                if codigo:
                    sel = pg[ct["cupom"][pg] == codigo]
                    resgatar(sel, codigo, ct["t_cad"][sel] + 200)
            cobrar(pg, d, t_emit=ct["t_cad"][pg] + 240)

        vivo = st > 0
        ativo = (st >= ST_TRIAL) & (st <= ST_CANC)
        ia = np.where(ativo)[0]

        # ============================================================== B. engajamento latente
        iv = np.where(vivo)[0]
        ten = d - ten0[iv]
        m = ct["eng_mu"][iv] + ct["drift"][iv] * ten / 30
        tb = (d >= tent_dias) & (d < tent_dias + 21)
        if tb.any():
            m += 2.5 * pref_acc[iv][:, tent_gen[tb]].sum(1)
        if SAIDA_LOTE <= d < SAIDA_LOTE + 60:
            m -= 0.3 * lote_fa[iv]
        eng[iv] += 0.06 * (m - eng[iv]) + 0.075 * rng.standard_normal(len(iv))

        # ============================================================== C. lançamentos de séries
        if d > 0:
            novas = np.where(eps_disp[:, d] > eps_disp[:, d - 1])[0]
        else:
            novas = np.array([], int)
        if len(novas):
            rel_last[novas] = d
            mark = np.zeros(S, bool)
            mark[novas] = True
            pw = np.where((aguarda >= 0))[0]
            pw = pw[mark[aguarda[pw]]]
            if len(pw):
                sers_pw = aguarda[pw].copy()
                acc_ok = ativo[pc[pw]] & (excluido[pw] > d) & ~bloqueado[pw]
                notificado = acc_ok & (rng.random(len(pw)) < 0.8)
                boost_ate[pw] = d + 5
                boost_f[pw] = np.where(notificado, 2.0, 1.3)
                retomar = pw[cur[pw] < 0]
                cur[retomar] = aguarda[retomar]
                aguarda[pw] = -1
                np_ = pw[notificado]
                tt = T0 + d * DIA + 7 * 3600 + rng.integers(0, 4 * 3600, len(np_))
                notificar(pc[np_], np_, 0, "novo_episodio", cat["ser_tit"][sers_pw[notificado]], tt, 0.55, 0.6)

        # ============================================================== D. reproduções por perfil
        pa = np.where(ativo[pc] & (pf["criado_dia"] <= d) & (excluido > d) & ~bloqueado)[0]
        pa = pa[esp[pc[pa]] < 2]
        nada = (cur[pa] < 0) & (d - fim_ser[pa] <= 21) & (binge[pa] > 0.4)
        lam = PARAM["base_plays"] * np.exp(eng[pc[pa]] + log_peso[pa]) * saz_view[d]
        lam *= np.where(nada, 0.6, 1.0) * np.where(boost_ate[pa] >= d, boost_f[pa], 1.0)
        lam *= rng.gamma(3.0, 1 / 3.0, len(pa))
        n_play = np.minimum(rng.poisson(lam), 28)
        # navegação sem reprodução
        lb = PARAM["base_browse"] * np.exp(0.3 * eng[pc[pa]]) * (1 + 2.2 * nada + 1.5 * (perdeu_ate[pa] >= d))
        nb = rng.poisson(lb)
        sel = nb > 0
        browse.add(perfil=pa[sel], dia=d, n=nb[sel])

        tem = n_play > 0
        pp = pa[tem]
        npp = n_play[tem]
        # início de nova série
        sem = cur[pp] < 0
        ini = pp[sem & (rng.random(len(pp)) < 0.35 * binge[pp])]
        if len(ini):
            disp_s = eps_disp[:, d] > 0
            pesos = np.log(ser_pop * (1 + 3 * ser_orig * np.exp(-np.clip(d - ser_lanc, 0, None) / 30))) \
                + np.where(disp_s, 0, -1e9)
            lg = np.log(pref[ini][:, ser_gen] + 1e-4) + pesos[None, :] - np.log(-np.log(rng.random((len(ini), S))))
            ch = lg.argmax(1)
            cur[ini] = ch
            ptr[ini] = 0
        # progresso
        cs = cur[pp]
        com = cs >= 0
        nser = np.zeros(len(pp), np.int64)
        ptr0 = np.zeros(len(pp), np.int64)
        if com.any():
            q = np.where(com)[0]
            s_ = cs[q]
            disp_eps = eps_disp[s_, d].astype(np.int64)
            fora = disp_eps == 0
            if fora.any():
                lost = pp[q[fora]]
                perdeu_ate[lost] = d + 30
                cur[lost] = -1
            q, s_, disp_eps = q[~fora], s_[~fora], disp_eps[~fora]
            want = rng.binomial(npp[q], np.clip(binge[pp[q]] + 0.15, 0, 0.98))
            restante = np.maximum(disp_eps - ptr[pp[q]], 0)
            k = np.minimum(want, restante)
            nser[q] = k
            ptr0[q] = ptr[pp[q]]
            ptr[pp[q]] += k
            acabou = ptr[pp[q]] >= disp_eps
            if acabou.any():
                pq_ = pp[q[acabou]]
                sq = s_[acabou]
                fim_ser[pq_] = d
                last_ser[pq_] = sq
                definitivo = (disp_eps[acabou] >= n_tot[sq]) & ser_fim[sq]
                aguarda[pq_[~definitivo]] = sq[~definitivo]
                cur[pq_] = -1
        # abandono de série
        ab = np.where((cur >= 0) & (rng.random(P) < 0.006))[0]
        cur[ab] = -1
        agg.add(perfil=pp, dia=d, n=npp, nser=nser, ser=np.where(nser > 0, cs, -1), ptr0=ptr0,
                plano=plano[pc[pp]])
        contas_play = np.unique(pc[pp])
        last_play[contas_play] = d
        # buffering experimentado (EWMA)
        bug = (BUG_INI <= d < BUG_FIM + 10) & mobile_first[contas_play]
        r_exp = buf_base[contas_play] * np.where(bug, 3.0, 1.0) * rng.lognormal(0, 0.25, len(contas_play))
        buf[contas_play] = 0.9 * buf[contas_play] + 0.1 * r_exp
        alto = contas_play[(r_exp > 1.0) & (rng.random(len(contas_play)) < 0.012)]
        ticket(alto, d, "reproducao")

        # flags por conta
        nada_acc = np.zeros(N, bool)
        nada_acc[pc[pa[nada]]] = True
        perdeu_acc = np.zeros(N, bool)
        pl = np.where(perdeu_ate >= d)[0]
        perdeu_acc[pc[pl]] = True

        # ============================================================== E. compartilhamento (membro extra)
        dec = np.where((sh_dec <= d) & (sh_status == 0) & ativo & ct["compartilha"])[0]
        if len(dec):
            pode = plano[dec] >= 2
            u = rng.random(len(dec))
            paga = pode & (u < _sig(-0.55 - 0.9 * ct["ps"][dec]))
            remove = ~paga & (rng.random(len(dec)) < 0.6)
            blo = ~paga & ~remove
            sp = sharer_idx[dec]
            sh_status[dec[paga]] = 1
            extra_ativo[dec[paga]] = 1
            membro_extra[sp[paga]] = 1
            evento(dec[paga], "membro_extra_adicionado", tloc(dec[paga], d, hora(paga.sum())), origem=0)
            sh_status[dec[remove]] = 2
            excluido[sp[remove]] = d
            sh_status[dec[blo]] = 3
            bloqueado[sp[blo]] = True
            perda_sh_ate[dec[remove | blo]] = d + 60
        rem = np.where((extra_ativo > 0) & ativo & (rng.random(N) < 0.0015))[0]
        if len(rem):
            extra_ativo[rem] = 0
            excluido[sharer_idx[rem]] = d
            membro_extra[sharer_idx[rem]] = 1
            evento(rem, "membro_extra_removido", tloc(rem, d, hora(len(rem))), origem=0)

        # ============================================================== F. fim de trial
        tf = np.where((st == ST_TRIAL) & (trial_fim == d))[0]
        if len(tf):
            pconv = _sig(0.5 + 1.1 * eng[tf] + 0.4 * (canal[tf] == C_IND) - 0.45 * (canal[tf] == C_SOCIAL)
                         - 0.3 * ct["ps"][tf])
            conv = rng.random(len(tf)) < pconv
            a = tf[conv]
            st[a] = ST_ATIVA
            evento(a, "trial_convertido", T0 + d * DIA + 3 * 3600)
            cobrar(a, d)
            b = tf[~conv]
            treq = s_ini[sub[b]] + rng.integers(3600, 7 * DIA - 3600, len(b))
            s_creq[sub[b]] = treq
            evento(b, "cancelamento_solicitado", treq, origem=0)
            dreq = ((treq - T0) // DIA).astype(int)
            acoes.add(conta=b, dia=dreq, tipo=1)
            encerrar(b, d, 1, s_trial[sub[b]])

        # ============================================================== G. inadimplência
        rs = np.where((st == ST_INAD) & (res_dia == d))[0]
        if len(rs):
            ok = res_ok[rs]
            a = rs[ok]
            st[a] = ST_ATIVA
            evento(a, "inadimplencia_resolvida", T0 + d * DIA + rng.integers(6 * 3600, 20 * 3600, len(a)))
            last_inv_pago[a] = True
            b = rs[~ok]
            fat_upd.add(idx=res_fat[b], status=2)
            encerrar(b, d, 2, T0 + d * DIA + 23 * 3600)

        # ============================================================== H. cancelamento voluntário
        ca = np.where(st == ST_ATIVA)[0]
        ca = ca[esp[ca] == 0]
        if len(ca):
            ten = d - ten0[ca]
            f_fin = nada_acc[ca]
            f_perd = perdeu_acc[ca]
            f_preco = ps_pos[ca] * price_win[d]
            f_promo = (d >= promo_fim[ca] - 10) & (d <= promo_fim[ca] + 20)
            f_buf = np.log(buf[ca] / 0.35)
            f_sh = perda_sh_ate[ca] >= d
            f_tk = ticket_ate[ca] >= d
            f_lote = lote_fa[ca] & (SAIDA_LOTE - 5 <= d < SAIDA_LOTE + 45)
            lp = (-2.2 * eng[ca] + 0.55 * np.exp(-ten / 45) + ch_eff[ca] + 0.95 * f_fin + 0.6 * f_perd
                  + 0.9 * f_preco + f_promo * (1.05 + 0.35 * ps_pos[ca]) + 0.6 * f_buf + 0.85 * f_sh
                  + 0.5 * f_tk + 0.7 * f_lote + saz_churn[d] + 0.15 * (plano[ca] == 1))
            h = PARAM["h0"] * np.exp(lp)
            dias_ren = prox[ca] - d
            h = np.where(anual[ca], h * np.where(dias_ren <= 30, 2.2, 0.1), h)
            u = rng.random(len(ca))
            canc = u < h
            # tentativas abandonadas (retidas)
            tent = (~canc) & (u < h * 1.25) & (u > h)
            acoes.add(conta=ca[tent], dia=d, tipo=1)
            acoes.add(conta=ca[tent], dia=d, tipo=0)
            a = ca[canc]
            if len(a):
                causas = np.stack([-2.2 * eng[a], 0.95 * f_fin[canc], 0.6 * f_perd[canc], 0.9 * f_preco[canc],
                                   f_promo[canc] * 1.05, 0.6 * f_buf[canc], 0.85 * f_sh[canc],
                                   0.7 * f_lote[canc]], 1)
                causa = causas.argmax(1)
                cancel_causa.add(conta=a, dia=d, causa=causa)
                origem = rng.choice([0, 1, 2], len(a), p=[.68, .22, .10])
                treq = tloc(a, d, hora(len(a), 7, 24))
                st[a] = ST_CANC
                s_creq[sub[a]] = treq
                evento(a, "cancelamento_solicitado", treq, origem=origem)
                ticket(a[origem == 2], d, "cancelamento", canal_p=2)
                acoes.add(conta=a, dia=d, tipo=0)
                acoes.add(conta=a, dia=d, tipo=1)
                pre = a[rng.random(len(a)) < 0.55]
                acoes.add(conta=pre, dia=np.maximum(d - rng.integers(1, 11, len(pre)), ten0[pre]), tipo=0)
                pre = a[rng.random(len(a)) < 0.4]
                acoes.add(conta=pre, dia=np.maximum(d - rng.integers(1, 11, len(pre)), ten0[pre]), tipo=1)
                # pesquisa de motivo
                resp = rng.random(len(a)) < 0.42
                mapa_motivo = np.array([1, 3, 2, 0, 0, 4, 5, 2])
                mot = mapa_motivo[causa]
                ruido = rng.random(len(a))
                mot = np.where(ruido < 0.22, 0, mot)  # "preço" é resposta socialmente fácil
                mot = np.where((ruido >= 0.22) & (ruido < 0.32), rng.choice([6, 7, 8], len(a)), mot)
                mot = np.where(mot == 3, np.where(rng.random(len(a)) < .5, 3, 2), mot)
                ar = np.where(resp)[0]
                prob_v = np.clip(np.round(5 + 2 * eng[a[ar]] + rng.normal(0, 2.2, len(ar))), 0, 10)
                prob_v = np.where(rng.random(len(ar)) < 0.3, -1, prob_v)
                pesq.add(sub=sub[a[ar]], conta=a[ar], t=treq[ar] + rng.integers(20, 300, len(ar)),
                         motivo=mot[ar], coment=mot[ar] * 10 + rng.integers(0, 3, len(ar)), prob=prob_v)
                # reembolso: cancelou logo após cobrança paga
                rf = a[(d - last_inv_dia[a] <= 3) & last_inv_pago[a] & (rng.random(len(a)) < 0.3)]
                if len(rf):
                    fat_upd.add(idx=last_inv_idx[rf], status=4)
                    pag.add(fat=last_inv_idx[rf], conta=rf, metodo=metodo[rf], tipo=1, tent=1,
                            t=tloc(rf, d, hora(len(rf), 9, 23)) + 3600, valor=-1.0, status=4, codigo=-1)
                    encerrar(rf, d, 1, tloc(rf, d, hora(len(rf), 9, 23)) + 7200)
        # navegação na tela de planos sem intenção (ruído)
        bp = ia[rng.random(len(ia)) < 0.0018]
        acoes.add(conta=bp, dia=d, tipo=0)

        # ============================================================== I. cobrança / renovação
        due = np.where(((st == ST_ATIVA) | (st == ST_CANC)) & (prox == d))[0]
        if len(due):
            fimv = due[st[due] == ST_CANC]
            encerrar(fimv, d, 1, T0 + d * DIA + rng.integers(0, 3 * 3600, len(fimv)))
            ren = due[st[due] == ST_ATIVA]
            cobrar(ren, d)

        # ============================================================== J. mudanças de plano e método
        ac = np.where(st == ST_ATIVA)[0]
        if len(ac):
            u = rng.random(len(ac))
            hup = 0.0009 * np.exp(0.45 * eng[ac] + 0.7 * has_tv[ac] - 0.5 * ct["ps"][ac]) * (plano[ac] < 3)
            hdn = 0.00035 * np.exp(0.6 * ct["ps"][ac] + 1.4 * price_win[d]) * (plano[ac] > 1)
            up = ac[u < hup]
            dn = ac[(u >= hup) & (u < hup + hdn)]
            for grupo, nome, delta in ((up, "upgrade", 1), (dn, "downgrade", -1)):
                if len(grupo):
                    t = tloc(grupo, d, hora(len(grupo)))
                    antes = plano[grupo].copy()
                    plano[grupo] = antes + delta
                    s_plano[sub[grupo]] = plano[grupo]
                    evento(grupo, nome, t, pa=antes, pn=plano[grupo], origem=rng.choice([0, 1], len(grupo), p=[.7, .3]))
                    acoes.add(conta=grupo, dia=d, tipo=0)
            # extra perde sentido no básico
            dnb = dn[(plano[dn] == 1) & (extra_ativo[dn] > 0)]
            extra_ativo[dnb] = 0
            troca = ac[(metodo[ac] > 0) & (rng.random(len(ac)) < 0.0006)]
            if len(troca):
                metodo[troca] = 0
                s_metodo[sub[troca]] = 0
                evento(troca, "metodo_pagamento_alterado", tloc(troca, d, hora(len(troca))), origem=0)

        # ============================================================== K. reativação
        ch = np.where((st == ST_FIM) & (esp == 0))[0]
        if len(ch):
            since = d - fim_dia[ch]
            # sinal de nova temporada de série acompanhada (qualquer perfil)
            sers = np.where(aguarda >= 0, aguarda, last_ser)
            okp = sers >= 0
            flag_p = np.zeros(P, bool)
            flag_p[okp] = (d - rel_last[sers[okp]] <= 14) & (d - rel_last[sers[okp]] >= 0)
            flag_acc = np.zeros(N, bool)
            flag_acc[pc[flag_p]] = True
            tent_win = ((d - tent_dias >= 0) & (d - tent_dias < 14)).any()
            lp = (0.45 * ct["eng_mu"][ch] + 1.4 * ((tipo_fim[ch] == 2) & (since < 30)) + 1.5 * flag_acc[ch]
                  + 1.35 * (winback_ate[ch] >= d) + 0.45 * tent_win - since / 220 - 0.35 * (since < 7)
                  - 0.4 * np.clip(ct["ps"][ch], 0, None))
            h = PARAM["r0"] * np.exp(lp)
            re = ch[rng.random(len(ch)) < h]
            if len(re):
                antiga = sub[re].copy()
                t = tloc(re, d, hora(len(re), 8, 24))
                inv = tipo_fim[re] == 2
                novo_met = np.where(inv & (rng.random(len(re)) < 0.7), 0, metodo[re])
                metodo[re] = novo_met
                anual[re] = anual[re] & (rng.random(len(re)) < 0.6)
                cup_cic[re] = 0
                nova_sub(re, d, t, ant=antiga)
                evento(re, "assinatura_criada", t, pn=plano[re], origem=1)
                evento(re, "reativada", t + 2, pn=plano[re], origem=1)
                st[re] = ST_ATIVA
                wb = re[(winback_ate[re] >= d) & (rng.random(len(re)) < 0.7)]
                resgatar(wb, "VOLTA50", tloc(wb, d, hora(len(wb), 8, 24)) + 100)
                eng[re] = np.maximum(eng[re], ct["eng_mu"][re]) + 0.25
                cobrar(re, d, t_emit=t + 60)
            # e-mails de reconquista (A/B: 60% recebem)
            alvo = ch[((tipo_fim[ch] == 1) & np.isin(since, [30, 90])) | ((tipo_fim[ch] == 2) & (since == 7))]
            alvo = alvo[(ct["aceita_mkt"][alvo] == 1) & (rng.random(len(alvo)) < 0.6)]
            if len(alvo):
                winback_ate[alvo] = d + 14
                notificar(alvo, -1, 1, "winback", -1, T0 + d * DIA + 13 * 3600 + rng.integers(0, 3600, len(alvo)),
                          _sig(-1.0 + 0.5 * ct["eng_mu"][alvo]), 0.35)

        # ============================================================== L. notificações sem efeito causal
        if cal["dow"][d] == 4:
            pdz = pa[rng.random(len(pa)) < 0.08]
            if len(pdz):
                tit = rng.choice(cat["N"], len(pdz), p=cat["pop"] / cat["pop"].sum())
                notificar(pc[pdz], pdz, 0, "destaques_semana", tit, T0 + d * DIA + 21 * 3600 + rng.integers(0, 3600, len(pdz)),
                          _sig(-1.6 + 0.6 * eng[pc[pdz]]), 0.3)
        if cal["dom"][d] == 1:
            inat = ia[(d - last_play[ia] > 14) & (esp[ia] == 0) & (ct["aceita_mkt"][ia] == 1)]
            inat = inat[rng.random(len(inat)) < 0.5]
            notificar(inat, -1, 1, "reengajamento", -1, T0 + d * DIA + 14 * 3600 + rng.integers(0, 7200, len(inat)),
                      _sig(-1.3 + 0.7 * eng[inat]), 0.25)
        for r in REAJUSTES:
            if d == r - 30:
                notificar(ia, -1, 1, "aviso_reajuste", -1, T0 + d * DIA + 12 * 3600 + rng.integers(0, 7200, len(ia)),
                          0.45, 0.1)
        if (tent_dias == d).any():
            alvo = ia[ct["aceita_mkt"][ia] == 1]
            tid = cat["tent_ids"][np.where(tent_dias == d)[0][0]]
            notificar(alvo, -1, 1, "lancamento_original", tid, T0 + d * DIA + 15 * 3600 + rng.integers(0, 7200, len(alvo)),
                      _sig(-0.8 + 0.5 * eng[alvo]), 0.4)

        # ============================================================== M. tickets aleatórios, NPS, especiais
        tk = ia[rng.random(len(ia)) < 0.0005]
        cats = rng.choice(["acesso_login", "conteudo", "outros", "cobranca"], len(tk), p=[.45, .2, .2, .15])
        for c in np.unique(cats):
            ticket(tk[cats == c], d, c)
        if price_win[d]:
            ticket(ia[rng.random(len(ia)) < 0.0007], d, "cobranca")
        if cal["mes"][d] in (1, 4, 7, 10) and 5 <= cal["dom"][d] <= 18:
            am = ia[(rng.random(len(ia)) < 0.15 / 14) & (esp[ia] == 0)]
            resp = am[rng.random(len(am)) < _sig(-0.9 + 0.5 * eng[am])]
            if len(resp):
                sat = (7.9 + 1.0 * eng[resp] - 0.9 * np.log(buf[resp] / 0.35) - 0.7 * ps_pos[resp] * price_win[d]
                       - 0.9 * nada_acc[resp] - 0.8 * (ticket_ate[resp] >= d) + rng.normal(0, 1.7, len(resp)))
                nota = np.clip(np.round(sat), 0, 10)
                nps.add(conta=resp, t=tloc(resp, d, hora(len(resp), 8, 23)), nota=nota,
                        canal=rng.choice([0, 1], len(resp), p=[.6, .4]))
        eb = ia[esp[ia] >= 2]
        esp_dias.add(conta=eb, dia=d)

        if d % 100 == 0:
            log(f"  dia {d:4d}/{NDIAS}  ativas={len(ia):7d}  assinaturas={ns:7d}  perfis-dia c/ play={len(agg):9d}")

    # ------------------------------------------------------------------ fechamento
    status_sub = np.full(ns, 5, np.int8)
    status_sub[sub[st > 0]] = st[st > 0]
    return dict(
        ns=ns, s_conta=s_conta[:ns], s_plano=s_plano[:ns], s_anual=s_anual[:ns], s_metodo=s_metodo[:ns],
        s_ini=s_ini[:ns], s_trial=s_trial[:ns], s_creq=s_creq[:ns], s_fim=s_fim[:ns], s_tfim=s_tfim[:ns],
        s_ant=s_ant[:ns], s_status=status_sub,
        ev=ev.cat(), fat=fat.cat(), fat_upd=fat_upd.cat(), pag=pag.cat(), resg=resg.cat(), pesq=pesq.cat(),
        tick=tick.cat(), nps=nps.cat(), notif=notif.cat(), agg=agg.cat(), browse=browse.cat(),
        acoes=acoes.cat(), esp_dias=esp_dias.cat(), churn=churn_log.cat(), causas=cancel_causa.cat(),
        excluido=excluido, membro_extra=membro_extra, bloqueado=bloqueado, sh_status=sh_status,
        precos_rows=precos_rows, eng_final=eng, plano_final=plano, st_final=st,
    )
