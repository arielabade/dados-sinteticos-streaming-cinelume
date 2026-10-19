"""Expansão dos agregados diários em logs: sessões, reproduções, eventos e heartbeats.

Processa um mês por vez para manter a memória limitada; os ids crescem com o tempo.
"""
import numpy as np

from .config import (DIA, FALHAS_PIPELINE, IDX_V430, IDX_V500, IDX_V600, NDIAS, T0, UF_TZ,
                     VERSAO_DIAS, VERSAO_NOMES, BUG_INI, BUG_FIM, REGIOES)

QUAL = np.array(["480p", "720p", "1080p", "4k"], dtype=object)
FILEIRAS = np.array(["em_alta", "continuar_assistindo", "recomendados_para_voce", "novidades",
                     "originais_cinelume", "porque_voce_assistiu", "top_10", "minha_lista"], dtype=object)
FIL_P = np.array([.18, .12, .2, .14, .1, .1, .1, .06])
TIPOS_EV = np.array(["impressao_titulo", "clique_titulo", "play_trailer", "busca", "adicionar_lista",
                     "avaliacao", "abrir_tela_planos", "tentativa_cancelamento"], dtype=object)
RENOMEADOS = {2: "trailer_play", 4: "lista_adicionar"}
FIM_TS = T0 + NDIAS * DIA


def _horas():
    """Distribuições de hora local por tipo de dispositivo [tv, celular, web, tablet] x [semana, fds]."""
    base = {
        0: ([1, .5, .3, .2, .1, .1, .2, .4, .5, .6, .7, .8, 1, 1, 1, 1.1, 1.3, 1.8, 2.6, 3.6, 5.2, 6, 5, 2.6],
            [1.6, .9, .5, .3, .1, .1, .2, .5, .9, 1.4, 1.8, 2, 2.2, 2.4, 2.6, 2.8, 3, 3.2, 3.6, 4.2, 5.4, 6, 5, 3]),
        1: ([1.6, .9, .4, .2, .1, .2, .6, 1.4, 1.6, 1.4, 1.3, 1.6, 2.4, 2.4, 1.6, 1.5, 1.6, 2, 2.6, 2.6, 2.8, 3.2, 3.4, 2.6],
            [2, 1.2, .6, .3, .1, .1, .3, .7, 1.1, 1.5, 1.8, 2, 2.4, 2.4, 2.2, 2.2, 2.3, 2.5, 2.7, 2.8, 3, 3.3, 3.4, 2.8]),
        2: ([.6, .3, .1, .1, .1, .1, .2, .6, 1.4, 2.2, 2.4, 2.2, 2, 2.4, 2.6, 2.4, 2.2, 2, 2, 2.2, 2.6, 2.8, 2.2, 1.2],
            [.8, .4, .2, .1, .1, .1, .2, .5, 1, 1.5, 1.8, 2, 2, 2, 2, 2, 2, 2, 2.2, 2.4, 2.6, 2.6, 2, 1.2]),
        3: ([.4, .2, .1, .1, .1, .1, .3, .8, 1.2, 1.4, 1.5, 1.6, 1.8, 2, 2.4, 2.8, 3, 3.2, 3.2, 3.2, 3.4, 3, 1.8, .9],
            [.6, .3, .1, .1, .1, .1, .3, 1, 1.8, 2.2, 2.4, 2.4, 2.4, 2.6, 2.8, 3, 3, 3, 3, 3.2, 3.2, 2.6, 1.6, .9]),
    }
    out = np.zeros((4, 2, 24))
    for t, (a, b) in base.items():
        out[t, 0] = np.cumsum(a) / np.sum(a)
        out[t, 1] = np.cumsum(b) / np.sum(b)
    return out


CUM_H = _horas()


def _rep(counts):
    return np.repeat(np.arange(len(counts)), counts)


def _rank(counts):
    st = np.cumsum(counts) - counts
    return np.arange(counts.sum()) - np.repeat(st, counts)


def _segcumsum(x, counts):
    """Soma acumulada exclusiva dentro de segmentos contíguos."""
    cs = np.cumsum(x)
    st = np.cumsum(counts) - counts
    base = np.repeat(cs[st] - x[st], counts)
    return cs - base - x


def _ip_casa(conta, periodo):
    h = (conta.astype(np.int64) * 2654435761 + periodo.astype(np.int64) * 40503) % (2 ** 24)
    return np.char.add(np.char.add(np.char.add("10.", (h >> 16).astype(str)), np.char.add(".", ((h >> 8) & 255).astype(str))),
                       np.char.add(".", (h & 255).astype(str)))


def _ip_movel(rng, n):
    a = rng.integers(64, 128, n)
    b = rng.integers(0, 256, n)
    c = rng.integers(1, 255, n)
    return np.char.add(np.char.add(np.char.add("100.", a.astype(str)), np.char.add(".", b.astype(str))),
                       np.char.add(".", c.astype(str)))


class Expansor:
    def __init__(self, seed, cat, ct, pf, dv, sim, saidas, stats, log=print):
        self.seed, self.cat, self.ct, self.pf, self.dv, self.sim = seed, cat, ct, pf, dv, sim
        self.out = saidas
        self.stats = stats
        self.log = log
        self.next_id = dict(sessao=1, evento=1, repro=1, hb=1)
        a = sim["agg"]
        o = np.argsort(a["dia"], kind="stable")
        self.agg = {k: v[o] for k, v in a.items()}
        b = sim["browse"]
        o = np.argsort(b["dia"], kind="stable")
        self.browse = {k: v[o] for k, v in b.items()}
        c = sim["acoes"]
        o = np.argsort(c["dia"], kind="stable")
        self.acoes = {k: v[o].astype(np.int64) for k, v in c.items()}
        e = sim["esp_dias"]
        o = np.argsort(e["dia"], kind="stable")
        self.esp = {k: v[o].astype(np.int64) for k, v in e.items()}
        self.princ = np.where(pf["principal"])[0]
        self.p_tz = UF_TZ[pf["uf"]]
        self.filmes = np.where(cat["tipo"] == 0)[0]
        self.conn = ct["conn"]
        self.devf = np.array([0.8, 1.3, 1.0, 1.1])
        nomes = cat["nomes"]
        tok = set()
        for n in nomes:
            for w in str(n).replace(":", " ").split():
                if len(w) > 3:
                    tok.add(w.lower())
        self.tokens = np.array(sorted(tok), dtype=object)
        self.nomes_low = np.array([str(n).lower() for n in nomes], dtype=object)
        self.ep_dur = cat["ep"][:, 3] * 60
        self.ep_tit = cat["ep"][:, 0]
        self.lanc = cat["lanc"]

    # ------------------------------------------------------------------ utilidades
    def _versao(self, dev, d):
        return np.clip(np.searchsorted(VERSAO_DIAS, d - self.dv["atraso_versao"][dev], side="right") - 1, 0, None)

    def _termo(self, rng, tit):
        n = len(tit)
        u = rng.random(n)
        nm = self.nomes_low[tit]
        k = rng.integers(4, 14, n)
        t = np.array([s[:kk] for s, kk in zip(nm, k)], dtype=object)
        gen = np.array(["terror", "comedia", "comédia", "documentario", "acao", "ação", "romance", "suspense",
                        "infantil", "anime", "serie nova", "filme de natal", "drama"], dtype=object)
        t[u < .25] = gen[rng.integers(0, len(gen), (u < .25).sum())]
        m = (u >= .25) & (u < .4)
        tk = self.tokens[rng.integers(0, len(self.tokens), m.sum())]
        tt = []
        for s in tk:
            if len(s) > 4 and rng.random() < .6:
                i = int(rng.integers(1, len(s) - 1))
                s = s[:i] + s[i + 1:]
            tt.append(s)
        t[m] = np.array(tt, dtype=object) if len(tt) else t[m]
        return t

    def _pop_mes(self, d0, d1):
        cat = self.cat
        disp = cat["disp_dia"][:, d0] & cat["disp_dia"][:, d1 - 1]
        mid = (d0 + d1) // 2
        rec = np.where(cat["original"] & (self.lanc <= mid), 1 + 5 * np.exp(-np.clip(mid - self.lanc, 0, None) / 25), 1.0)
        return np.where(disp, cat["pop"] * rec, 0.0)

    # ------------------------------------------------------------------ processamento de um mês
    def processar(self, k, d0, d1):
        rng = np.random.default_rng([self.seed, 7000 + k])
        cat, ct, pf, dv = self.cat, self.ct, self.pf, self.dv
        pop = self._pop_mes(d0, d1)
        gen_f = cat["gen"]
        # listas por gênero (filmes disponíveis)
        filmes_disp = self.filmes[pop[self.filmes] > 0]
        por_gen = []
        for g in range(16):
            ids = filmes_disp[gen_f[filmes_disp] == g]
            w = pop[ids]
            por_gen.append((ids, np.cumsum(w) / w.sum() if len(ids) else None))
        todos = np.where(pop > 0)[0]
        cum_todos = np.cumsum(pop[todos]) / pop[todos].sum()

        A = self.agg
        lo, hi = np.searchsorted(A["dia"], [d0, d1])
        a_p, a_d, a_n = A["perfil"][lo:hi].astype(np.int64), A["dia"][lo:hi].astype(np.int64), A["n"][lo:hi].astype(np.int64)
        a_ns, a_s, a_ptr, a_pl = A["nser"][lo:hi], A["ser"][lo:hi], A["ptr0"][lo:hi], A["plano"][lo:hi]
        B = self.browse
        lo, hi = np.searchsorted(B["dia"], [d0, d1])
        b_p, b_d, b_n = B["perfil"][lo:hi].astype(np.int64), B["dia"][lo:hi].astype(np.int64), B["n"][lo:hi].astype(np.int64)
        C = self.acoes
        lo, hi = np.searchsorted(C["dia"], [d0, d1])
        c_c, c_d, c_t = C["conta"][lo:hi], C["dia"][lo:hi], C["tipo"][lo:hi]

        # ================= sessões com reprodução
        R = len(a_p)
        ns_row = 1 + np.minimum(rng.binomial(np.maximum(a_n - 1, 0), 0.12), 2)
        s_row = _rep(ns_row)
        s_p = a_p[s_row]
        s_d = a_d[s_row]
        # sessões de navegação
        bs_row = _rep(b_n)
        s_p = np.concatenate([s_p, b_p[bs_row]])
        s_d = np.concatenate([s_d, b_d[bs_row]])
        n_play_s = len(s_row)
        # sessões de ações (planos/cancelamento) no perfil principal
        ac_p = self.princ[c_c]
        s_p = np.concatenate([s_p, ac_p])
        s_d = np.concatenate([s_d, c_d])
        n_br = len(bs_row)
        NS = len(s_p)
        kind = np.concatenate([np.zeros(n_play_s, np.int8), np.ones(n_br, np.int8), np.full(len(ac_p), 2, np.int8)])
        # dispositivo
        u = rng.random(NS)
        cw = np.cumsum(pf["pw"][s_p], 1)
        col = (u[:, None] > cw).sum(1).clip(0, 3)
        s_dev = pf["pdev"][s_p, col]
        bad = s_dev < 0
        s_dev[bad] = pf["pdev"][s_p[bad], 0]
        s_dt = dv["tipo"][s_dev]
        # hora local
        fds = np.isin((s_d + 6) % 7, [5, 6]).astype(int)  # 2023-10-01 é domingo -> (d+6)%7 = weekday
        uh = rng.random(NS)
        hh = (uh[:, None] > CUM_H[s_dt, fds]).sum(1).clip(0, 23)
        inf = pf["infantil"][s_p]
        hh[inf] = np.clip(rng.normal(16, 2.5, inf.sum()), 7, 21).astype(int)
        tz = self.p_tz[s_p]
        s_ini = T0 + s_d * DIA + hh * 3600 + rng.integers(0, 3600, NS) - tz * 3600
        s_ver = self._versao(s_dev, s_d)
        conta_s = pf["pc"][s_p]

        # ================= reproduções
        P_ = int(a_n.sum())
        r_row = _rep(a_n)
        r_k = _rank(a_n)
        r_p = a_p[r_row]
        r_d = a_d[r_row]
        # sessão de cada play (blocos contíguos)
        sess_in_row = (r_k * ns_row[r_row]) // a_n[r_row]
        first_sess = np.cumsum(ns_row) - ns_row
        r_s = first_sess[r_row] + sess_in_row
        is_ser = r_k < a_ns[r_row]
        ser = a_s[r_row]
        ep_idx = np.where(is_ser, cat["ep_off"][np.maximum(ser, 0)] + a_ptr[r_row] + r_k, -1)
        tit = np.empty(P_, np.int64)
        dur = np.empty(P_, np.int64)
        tit[is_ser] = self.ep_tit[ep_idx[is_ser]]
        dur[is_ser] = self.ep_dur[ep_idx[is_ser]]
        # filmes
        fm = np.where(~is_ser)[0]
        pr = pf["pref"][r_p[fm]]
        g = (rng.random(len(fm))[:, None] > np.cumsum(pr, 1)).sum(1).clip(0, 15)
        for gg in range(16):
            sel = fm[g == gg]
            ids, cw_ = por_gen[gg]
            if not len(sel):
                continue
            if ids is None or not len(ids):
                tit[sel] = todos[np.searchsorted(cum_todos, rng.random(len(sel)))]
            else:
                tit[sel] = ids[np.minimum(np.searchsorted(cw_, rng.random(len(sel))), len(ids) - 1)]
        # filmes caindo em série (gênero sem filme) -> trata como episódio 1
        ser_fm = cat["tipo"][tit[fm]] == 1
        if ser_fm.any():
            ii = fm[ser_fm]
            sp = np.array([cat["pos_ser"][t] for t in tit[ii]])
            ep_idx[ii] = cat["ep_off"][sp]
            dur[ii] = self.ep_dur[ep_idx[ii]]
        ok = ~is_ser & (ep_idx < 0)
        dur[ok] = cat["dur"][tit[ok]].astype(np.int64) * 60
        # colaboradores assistem originais antes da estreia
        emp = (ct["especial"][pf["pc"][r_p]] == 1) & ~is_ser & (rng.random(P_) < 0.12)
        if emp.any():
            fut = np.where(cat["original"] & (cat["tipo"] == 0) & (self.lanc > d0) & (self.lanc < d1 + 45))[0]
            if len(fut):
                ii = np.where(emp)[0]
                tit[ii] = rng.choice(fut, len(ii))
                dur[ii] = cat["dur"][tit[ii]].astype(np.int64) * 60
                self.stats["repro_pre_estreia"] = self.stats.get("repro_pre_estreia", 0) + len(ii)
        r_dev = s_dev[r_s]
        r_dt = s_dt[r_s]
        # fração assistida
        conta_r = pf["pc"][r_p]
        bufrate = 0.35 * np.exp(2.2 * (0.75 - self.conn[conta_r])) * self.devf[r_dt]
        bug = (s_ver[r_s] == IDX_V430) & np.isin(r_dt, [1, 3])
        bufrate = bufrate * np.where(bug, 3.0, 1.0)
        pc_ = 0.15 + 0.55 * (r_dt == 0) + 0.6 * is_ser + 0.3 * inf[r_s] + 0.8 * pf["binge"][r_p] - 0.5 * (bufrate > 0.8)
        compl = rng.random(P_) < 1 / (1 + np.exp(-pc_))
        frac = np.where(compl, rng.uniform(0.93, 1.0, P_), rng.beta(1.1, 2.6, P_))
        watched = np.maximum((frac * dur).astype(np.int64), 1)
        pct = np.clip(frac * 100 + rng.normal(0, 1.2, P_), 0, 100)
        nbuf = rng.poisson(bufrate * watched / 3600)
        # qualidade
        maxq = np.where(a_pl[r_row] == 3, 3, a_pl[r_row].astype(int))  # 1->720p(1) 2->1080p(2) 3->4k(3)
        maxq = np.where((r_dt != 0) & (maxq == 3), 2, maxq)
        sc = self.conn[conta_r] + rng.normal(0, 0.12, P_)
        q = maxq - (sc < 0.65) - (sc < 0.45)
        q = np.clip(q, 0, 3)
        # autoplay / recomendação
        prev_same = np.r_[False, (r_s[1:] == r_s[:-1])]
        prev_ser = np.r_[False, is_ser[:-1]]
        auto = prev_same & is_ser & prev_ser & (rng.random(P_) < 0.8)
        rec = (~auto) & (rng.random(P_) < np.where(pop[tit] > np.quantile(pop[pop > 0], .9), 0.5, 0.28))

        # ===== maratonas noturnas em TV sem aviso de "ainda está aí?" (plataforma tv_os_b)
        ult = np.r_[r_s[1:] != r_s[:-1], True]
        cand = np.where(ult & (r_dt == 0) & (dv["plat"][r_dev] == "tv_os_b") & ((hh[r_s] >= 21) | (hh[r_s] <= 1))
                        & (rng.random(P_) < 0.04))[0]
        extra_rows = []
        if len(cand):
            ne = rng.integers(6, 18, len(cand))
            base_ser = np.where(is_ser[cand], ser[cand], rng.choice(cat["S"], len(cand)))
            base_ep = np.where(is_ser[cand], ep_idx[cand] - cat["ep_off"][np.maximum(base_ser, 0)] + 1, 0)
            for c_, n_, s_, e_ in zip(cand, ne, base_ser, base_ep):
                tot = cat["n_eps_total"][s_]
                eps = cat["ep_off"][s_] + (np.arange(e_, e_ + n_) % max(tot, 1))
                extra_rows.append((np.full(n_, c_), eps))
            self.stats["maratonas_noturnas"] = self.stats.get("maratonas_noturnas", 0) + len(cand)
        if extra_rows:
            src = np.concatenate([x[0] for x in extra_rows])
            eps = np.concatenate([x[1] for x in extra_rows])
            m = len(src)
            ne_ = np.array([len(x[0]) for x in extra_rows])
            chave = np.concatenate([np.arange(P_, dtype=float), src + 0.5 + _rank(ne_) / 1000.0])
            order = np.argsort(chave, kind="stable")

            def ext(x, novo):
                return np.concatenate([x, novo])[order]
            fr = rng.uniform(0.97, 1.0, m)
            r_p, r_d, r_s = ext(r_p, r_p[src]), ext(r_d, r_d[src]), ext(r_s, r_s[src])
            is_ser = ext(is_ser, np.ones(m, bool))
            ep_idx, tit = ext(ep_idx, eps), ext(tit, self.ep_tit[eps])
            watched = ext(watched, (fr * self.ep_dur[eps]).astype(np.int64))
            dur = ext(dur, self.ep_dur[eps])
            pct = ext(pct, fr * 100)
            nbuf = ext(nbuf, rng.poisson(0.2, m))
            q, auto, rec = ext(q, q[src]), ext(auto, np.ones(m, bool)), ext(rec, np.zeros(m, bool))
            r_dev, r_dt, conta_r = ext(r_dev, r_dev[src]), ext(r_dt, r_dt[src]), ext(conta_r, conta_r[src])
            compl = ext(compl, np.ones(m, bool))
            P_ = len(r_p)

        # ===== tempos dentro da sessão
        gap = np.where(auto, rng.integers(5, 16, P_), rng.integers(20, 420, P_))
        pausa = np.where(rng.random(P_) < 0.18, rng.exponential(400, P_).astype(np.int64), 0)
        bloco = watched + pausa + nbuf * rng.integers(2, 12, P_)
        cnt = np.bincount(r_s, minlength=NS)
        assert (np.diff(r_s) >= 0).all()
        off = _segcumsum(gap + bloco, cnt[cnt > 0]) + gap
        r_ini = s_ini[r_s] + off
        r_fim = r_ini + bloco
        s_fim = s_ini + rng.integers(20, 400, NS)
        last_end = np.zeros(NS, np.int64)
        np.maximum.at(last_end, r_s, r_fim)
        s_fim = np.where(last_end > 0, last_end + rng.integers(5, 300, NS), s_ini + np.exp(rng.normal(5.2, 0.8, NS)).astype(np.int64))

        # ================= anomalias em reproducoes
        an = rng.random(P_)
        z = an < 0.004
        watched_out = watched.copy()
        fim_out = r_fim.copy()
        pct_out = pct.copy()
        watched_out[z] = 0; fim_out[z] = r_ini[z]; pct_out[z] = 0
        neg = (an >= 0.004) & (an < 0.0045)
        fim_out[neg] = r_ini[neg] - rng.integers(60, 3600, neg.sum())
        watched_out[neg] = fim_out[neg] - r_ini[neg]
        lng = (an >= 0.0045) & (an < 0.007)
        watched_out[lng] = (dur[lng] * rng.uniform(1.1, 3.0, lng.sum())).astype(np.int64)
        pct_out[lng] = np.round(rng.uniform(100.5, 140, lng.sum()), 2)
        fim_nulo = (an >= 0.007) & (an < 0.0095)
        r_ver = s_ver[r_s]
        ms = (r_ver >= IDX_V600) & np.isin(r_dt, [1, 3])
        watched_out[ms] *= 1000
        q_nulo = rng.random(P_) < 0.01
        st = self.stats
        st["repro_total"] = st.get("repro_total", 0) + P_
        for nome, m_ in (("repro_zero", z), ("repro_negativa", neg), ("repro_maior_que_titulo", lng),
                         ("repro_fim_nulo", fim_nulo), ("repro_ms", ms), ("repro_qualidade_nula", q_nulo)):
            st[nome] = st.get(nome, 0) + int(m_.sum())

        # ================= heartbeats
        tel = pf["telemetria"][r_p]
        hb_n = np.where(tel & (watched > 0), watched // 60 + 1, 0)
        # TV: pings continuam durante pausa
        pausa_hb = tel & (r_dt == 0) & (pausa > 0)
        hb_n = hb_n + np.where(pausa_hb, pausa // 60, 0)
        H = int(hb_n.sum())
        h_r = _rep(hb_n)
        h_j = _rank(hb_n)
        h_true = r_ini[h_r] + h_j * 60 + rng.integers(-2, 4, H)
        h_pos = np.minimum(h_j * 60, watched[h_r])
        h_buf = (rng.random(H) < np.clip(nbuf[h_r] / np.maximum(hb_n[h_r], 1), 0, 1)).astype(np.int8)
        h_q = q[h_r]
        # perdas em segundo plano (celular)
        perda = np.zeros(H, bool)
        mob = np.isin(r_dt[h_r], [1, 3])
        rr = np.random.default_rng([self.seed, 9100 + k]).random(P_)
        gap_play = (rr < 0.07) & tel & np.isin(r_dt, [1, 3])
        if gap_play.any():
            a0 = rng.uniform(0.1, 0.5, P_)
            frac_j = h_j / np.maximum(hb_n[h_r], 1)
            perda = gap_play[h_r] & mob & (frac_j > a0[h_r]) & (frac_j < a0[h_r] + 0.35)
        st["hb_perdidos_segundo_plano"] = st.get("hb_perdidos_segundo_plano", 0) + int(perda.sum())
        st["hb_pausa_tv"] = st.get("hb_pausa_tv", 0) + int(np.where(pausa_hb, pausa // 60, 0).sum())
        keep = ~perda
        h_r, h_true, h_pos, h_buf, h_q = h_r[keep], h_true[keep], h_pos[keep], h_buf[keep], h_q[keep]
        h_ms = ms[h_r]
        h_pos = np.where(h_ms, h_pos * 1000, h_pos)
        # duplicados
        dup = rng.random(len(h_r)) < 0.015
        st["hb_duplicados"] = st.get("hb_duplicados", 0) + int(dup.sum())
        di = np.where(dup)[0]
        h_r = np.concatenate([h_r, h_r[di]]); h_true = np.concatenate([h_true, h_true[di]])
        h_pos = np.concatenate([h_pos, h_pos[di]]); h_buf = np.concatenate([h_buf, h_buf[di]])
        h_q = np.concatenate([h_q, h_q[di]])
        h_dev = r_dev[h_r]
        h_env = self._relogio(h_true, h_dev)
        falha = self._em_falha(h_true)
        st["hb_falha_pipeline"] = st.get("hb_falha_pipeline", 0) + int(falha.sum())
        h_r, h_env, h_pos, h_buf, h_q, h_true = h_r[~falha], h_env[~falha], h_pos[~falha], h_buf[~falha], h_q[~falha], h_true[~falha]

        # ================= eventos
        evs = []  # (sessao_idx, tipo, t_true, titulo, fileira, posicao, termo, avaliacao)
        # impressões gerais
        lam_imp = np.where(kind == 0, 1.3, np.where(kind == 1, 4.5, 0.8))
        ni = rng.poisson(lam_imp)
        e_s = _rep(ni)
        fp = np.full(NS, np.iinfo(np.int64).max)
        np.minimum.at(fp, r_s, r_ini)
        fim_janela = np.where(fp < np.iinfo(np.int64).max, fp, s_fim)
        t_imp = s_ini[e_s] + (rng.random(len(e_s)) * np.maximum(fim_janela[e_s] - s_ini[e_s], 1)).astype(np.int64)
        tit_imp = todos[np.minimum(np.searchsorted(cum_todos, rng.random(len(e_s))), len(todos) - 1)]
        fil = rng.choice(len(FILEIRAS), len(e_s), p=FIL_P)
        pos = np.minimum(rng.geometric(0.16, len(e_s)), 40)
        evs.append(dict(s=e_s, tipo=np.zeros(len(e_s), np.int8), t=t_imp, tit=tit_imp, fil=fil, pos=pos))
        # cliques (plays não-autoplay) + impressão de origem / busca
        na = np.where(~auto)[0]
        t_cl = r_ini[na] - rng.integers(3, 40, len(na))
        evs.append(dict(s=r_s[na], tipo=np.ones(len(na), np.int8), t=t_cl, tit=tit[na], fil=-1, pos=-1))
        rr_ = na[rec[na]]
        t_ri = r_ini[rr_] - rng.integers(45, 120, len(rr_))
        evs.append(dict(s=r_s[rr_], tipo=np.zeros(len(rr_), np.int8), t=t_ri, tit=tit[rr_],
                        fil=rng.choice([2, 5, 6], len(rr_), p=[.5, .3, .2]), pos=np.minimum(rng.geometric(0.3, len(rr_)), 40)))
        nr = na[~rec[na]]
        bsc = nr[rng.random(len(nr)) < 0.3]
        evs.append(dict(s=r_s[bsc], tipo=np.full(len(bsc), 3, np.int8), t=r_ini[bsc] - rng.integers(50, 200, len(bsc)),
                        tit=-1, fil=-1, pos=-1, termo=self._termo(rng, tit[bsc])))
        outros = np.setdiff1d(nr, bsc)
        evs.append(dict(s=r_s[outros], tipo=np.zeros(len(outros), np.int8), t=r_ini[outros] - rng.integers(45, 120, len(outros)),
                        tit=tit[outros], fil=rng.choice([1, 7], len(outros), p=[.75, .25]),
                        pos=np.minimum(rng.geometric(0.4, len(outros)), 40)))
        # buscas em navegação
        sb = np.where((kind == 1) & (rng.random(NS) < 0.45))[0]
        nbq = rng.integers(1, 4, len(sb))
        sb2 = np.repeat(sb, nbq)
        tb = todos[np.minimum(np.searchsorted(cum_todos, rng.random(len(sb2))), len(todos) - 1)]
        evs.append(dict(s=sb2, tipo=np.full(len(sb2), 3, np.int8),
                        t=s_ini[sb2] + (rng.random(len(sb2)) * np.maximum(s_fim[sb2] - s_ini[sb2], 1)).astype(np.int64),
                        tit=-1, fil=-1, pos=-1, termo=self._termo(rng, tb)))
        # trailer e lista
        for tipo_e, p0, p1 in ((2, 0.08, 0.2), (4, 0.06, 0.18)):
            ss = np.where(rng.random(NS) < np.where(kind == 1, p1, np.where(kind == 0, p0, 0)))[0]
            tt = todos[np.minimum(np.searchsorted(cum_todos, rng.random(len(ss))), len(todos) - 1)]
            evs.append(dict(s=ss, tipo=np.full(len(ss), tipo_e, np.int8),
                            t=s_ini[ss] + (rng.random(len(ss)) * np.maximum(fim_janela[ss] - s_ini[ss], 1)).astype(np.int64),
                            tit=tt, fil=-1, pos=-1))
        # avaliações
        av = np.where(rng.random(P_) < np.where(compl, 0.06, 0.02))[0]
        pos_av = np.where(compl[av], rng.random(len(av)) < 0.86, rng.random(len(av)) < 0.35)
        evs.append(dict(s=r_s[av], tipo=np.full(len(av), 5, np.int8), t=r_fim[av] + rng.integers(2, 30, len(av)),
                        tit=tit[av], fil=-1, pos=-1, aval=np.where(pos_av, 1, 2)))
        # ações de planos / cancelamento
        sa = np.arange(n_play_s + n_br, NS)
        evs.append(dict(s=sa, tipo=np.where(c_t == 0, 6, 7).astype(np.int8), t=s_ini[sa] + rng.integers(5, 60, len(sa)),
                        tit=-1, fil=-1, pos=-1))
        # monta
        def col(nome, padrao):
            out = []
            for e in evs:
                v = e.get(nome, padrao)
                out.append(np.full(len(e["s"]), v, np.int64) if np.ndim(v) == 0 else np.asarray(v, np.int64))
            return np.concatenate(out)
        e_s = col("s", 0)
        e_tipo = col("tipo", 0).astype(np.int8)
        e_t = col("t", 0)
        e_tit = col("tit", -1)
        e_fil = col("fil", -1)
        e_pos = col("pos", -1)
        e_aval = col("aval", 0)
        e_termo = np.concatenate([e["termo"] if "termo" in e else np.full(len(e["s"]), None, dtype=object) for e in evs])
        e_t = np.maximum(e_t, s_ini[e_s])

        # ================= sessões especiais: bots e QA
        bs = self._especiais(rng, d0, d1)

        # ================= ordenação e ids: sessões
        o_s = np.argsort(s_ini, kind="stable")
        sid = np.empty(NS, np.int64)
        sid[o_s] = self.next_id["sessao"] + np.arange(NS)
        self.next_id["sessao"] += NS

        # IP / região
        casa = rng.random(NS) < np.where(np.isin(s_dt, [1]), 0.6, 0.97)
        ip = np.where(casa, _ip_casa(np.where(pf["sharer"][s_p], s_p + 10 ** 7, conta_s), s_d // 120), _ip_movel(rng, NS)).astype(object)
        reg = pf["regiao"][s_p].copy()
        wrong = rng.random(NS) < np.where(casa, 0.02, 0.12)
        reg[wrong] = rng.integers(0, 5, wrong.sum())
        reg_txt = np.array(REGIOES, dtype=object)[reg]
        reg_nulo = rng.random(NS) < 0.04
        # falha de pipeline: parte das sessões nunca chega
        s_falha = self._em_falha(s_ini) & (rng.random(NS) < 0.6)
        st["sessoes_perdidas_falha"] = st.get("sessoes_perdidas_falha", 0) + int(s_falha.sum())
        keep_s = ~s_falha
        o2 = o_s[keep_s[o_s]]
        self.out["sessoes_app"].escrever(dict(
            sessao_id=sid[o2], perfil_id=s_p[o2] + 1, dispositivo_id=s_dev[o2] + 1,
            versao_app=VERSAO_NOMES[s_ver[o2]].astype(object), inicio_em=s_ini[o2], fim_em=s_fim[o2],
            ip=ip[o2], regiao=(reg_txt[o2], reg_nulo[o2])))

        # ================= reproduções
        o_r = np.argsort(r_ini, kind="stable")
        rid = np.empty(P_, np.int64)
        rid[o_r] = self.next_id["repro"] + np.arange(P_)
        self.next_id["repro"] += P_
        self.out["reproducoes"].escrever(dict(
            reproducao_id=rid[o_r], perfil_id=r_p[o_r] + 1, sessao_id=sid[r_s[o_r]], dispositivo_id=r_dev[o_r] + 1,
            titulo_id=tit[o_r] + 1, episodio_id=(ep_idx[o_r] + 1, ep_idx[o_r] < 0), inicio_em=r_ini[o_r],
            fim_em=(fim_out[o_r], fim_nulo[o_r]), segundos_assistidos=watched_out[o_r],
            percentual_concluido=pct_out[o_r], qualidade_video=(QUAL[q[o_r]], q_nulo[o_r]),
            eventos_buffering=nbuf[o_r], origem_autoplay=auto[o_r].astype(np.int8),
            origem_recomendacao=rec[o_r].astype(np.int8), versao_app=VERSAO_NOMES[r_ver[o_r]].astype(object)))

        # ================= heartbeats
        o_h = np.argsort(h_true, kind="stable")
        Hn = len(o_h)
        self.out["heartbeats_reproducao"].escrever(dict(
            heartbeat_id=self.next_id["hb"] + np.arange(Hn), reproducao_id=rid[h_r[o_h]], enviado_em=h_env[o_h],
            posicao_seg=h_pos[o_h], qualidade_video=QUAL[h_q[o_h]], em_buffering=h_buf[o_h]))
        self.next_id["hb"] += Hn

        # ================= eventos (com imperfeições) + bots/QA
        self._escrever_eventos(rng, e_s, e_tipo, e_t, e_tit, e_fil, e_pos, e_termo, e_aval,
                               sid, s_p, s_dev, s_ver, s_dt, bs)
        return P_, NS, Hn

    # ------------------------------------------------------------------ relógio do dispositivo
    def _relogio(self, t, dev):
        off = self.dv["relogio"][dev]
        out = t + np.where(off > 0, off, np.where(off < -1, off, 0))
        reset = off == -1
        out[reset] = 946684800 + (t[reset] - T0) % (40 * DIA)
        return out

    def _em_falha(self, t):
        d = (t - T0) // DIA
        h = ((t - T0) % DIA) // 3600
        m = np.zeros(len(t), bool)
        for f in FALHAS_PIPELINE:
            m |= ((d == f) & (h >= 4)) | ((d == f + 1) & (h < 8))
        return m

    # ------------------------------------------------------------------ bots e contas de QA
    def _especiais(self, rng, d0, d1):
        E_ = self.esp
        lo, hi = np.searchsorted(E_["dia"], [d0, d1])
        c, d = E_["conta"][lo:hi], E_["dia"][lo:hi]
        if not len(c):
            return None
        tipo = self.ct["especial"][c]
        ns = np.where(tipo == 3, rng.integers(4, 12, len(c)), rng.integers(2, 7, len(c)))
        row = _rep(ns)
        cc, dd, tp = c[row], d[row], tipo[row]
        n = len(row)
        p = self.princ[cc]
        dev = self.pf["pdev"][p, 0]
        alt = (tp == 2)
        k = rng.integers(0, 4, n)
        dev2 = self.pf["pdev"][p, k]
        dev = np.where(alt & (dev2 >= 0), dev2, dev)
        hh = np.where(tp == 3, rng.integers(0, 24, n), rng.integers(9, 18, n))
        ini = T0 + dd * DIA + hh * 3600 + rng.integers(0, 3600, n) + 3 * 3600
        dur = np.where(tp == 3, rng.integers(60, 900, n), rng.integers(120, 2400, n))
        return dict(c=cc, d=dd, tipo=tp, p=p, dev=dev, ini=ini, fim=ini + dur)

    def _escrever_eventos(self, rng, e_s, e_tipo, e_t, e_tit, e_fil, e_pos, e_termo, e_aval,
                          sid, s_p, s_dev, s_ver, s_dt, bs):
        st = self.stats
        e_sid = sid[e_s]
        e_p = s_p[e_s]
        e_dev = s_dev[e_s]
        e_ver = s_ver[e_s]
        e_dt = s_dt[e_s]
        extra = None
        if bs is not None:
            n = len(bs["c"])
            sid_b = self.next_id["sessao"] + np.arange(n)
            self.next_id["sessao"] += n
            ver_b = self._versao(bs["dev"], bs["d"])
            ip_b = np.where(bs["tipo"] == 3,
                            np.char.add("203.0.113.", rng.integers(1, 255, n).astype(str)),
                            np.char.add("10.250.0.", rng.integers(1, 255, n).astype(str))).astype(object)
            self.out["sessoes_app"].escrever(dict(
                sessao_id=sid_b, perfil_id=bs["p"] + 1, dispositivo_id=bs["dev"] + 1,
                versao_app=VERSAO_NOMES[ver_b].astype(object), inicio_em=bs["ini"], fim_em=bs["fim"], ip=ip_b,
                regiao=(np.full(n, "Sudeste", dtype=object), bs["tipo"] == 3)))
            ne = np.where(bs["tipo"] == 3, rng.integers(10, 35, n), rng.integers(3, 12, n))
            r = _rep(ne)
            m = len(r)
            tb = np.where(bs["tipo"][r] == 3, np.where(rng.random(m) < 0.55, 3, 0), rng.choice([0, 1, 2, 3, 4, 5], m))
            tt = bs["ini"][r] + (rng.random(m) * (bs["fim"][r] - bs["ini"][r])).astype(np.int64)
            tit = rng.integers(0, self.cat["N"], m)
            termo = np.where(tb == 3, self._termo(rng, tit), None).astype(object)
            extra = dict(sid=sid_b[r], p=bs["p"][r], dev=bs["dev"][r], ver=ver_b[r], dt=self.dv["tipo"][bs["dev"][r]],
                         tipo=tb.astype(np.int8), t=tt, tit=np.where(np.isin(tb, [0, 1, 2, 4, 5]), tit, -1),
                         fil=np.where(tb == 0, rng.integers(0, 8, m), -1), pos=np.where(tb == 0, rng.integers(1, 41, m), -1),
                         termo=termo, aval=np.where(tb == 5, rng.integers(1, 3, m), 0))
            # reproduções de teste (QA): muitas e curtas
            qa = np.where(bs["tipo"] == 2)[0]
            nq = rng.integers(2, 10, len(qa))
            rq = np.repeat(qa, nq)
            if len(rq):
                q_ini = bs["ini"][rq] + rng.integers(0, 600, len(rq))
                w = rng.integers(3, 90, len(rq))
                o = np.argsort(q_ini, kind="stable")
                Q = len(rq)
                tq = rng.integers(0, self.cat["N"], Q)
                is_s = self.cat["tipo"][tq] == 1
                epq = np.where(is_s, self.cat["ep_off"][np.array([self.cat["pos_ser"].get(t, 0) for t in tq])], -1)
                rid = self.next_id["repro"] + np.arange(Q)
                self.next_id["repro"] += Q
                self.out["reproducoes"].escrever(dict(
                    reproducao_id=rid, perfil_id=bs["p"][rq][o] + 1, sessao_id=sid_b[rq][o],
                    dispositivo_id=bs["dev"][rq][o] + 1, titulo_id=tq[o] + 1, episodio_id=(epq[o] + 1, epq[o] < 0),
                    inicio_em=q_ini[o], fim_em=q_ini[o] + w[o], segundos_assistidos=w[o],
                    percentual_concluido=np.round(w[o] / 3600 * 100 / 1.5, 2), qualidade_video=QUAL[rng.integers(0, 4, Q)],
                    eventos_buffering=np.zeros(Q, np.int64), origem_autoplay=np.zeros(Q, np.int8),
                    origem_recomendacao=np.zeros(Q, np.int8), versao_app=VERSAO_NOMES[ver_b[rq][o]].astype(object)))
                st["repro_qa"] = st.get("repro_qa", 0) + Q
            st["sessoes_bot"] = st.get("sessoes_bot", 0) + int((bs["tipo"] == 3).sum())
            st["eventos_bot"] = st.get("eventos_bot", 0) + int((bs["tipo"][r] == 3).sum())
        if extra is not None:
            e_sid = np.concatenate([e_sid, extra["sid"]]); e_p = np.concatenate([e_p, extra["p"]])
            e_dev = np.concatenate([e_dev, extra["dev"]]); e_ver = np.concatenate([e_ver, extra["ver"]])
            e_dt = np.concatenate([e_dt, extra["dt"]]); e_tipo = np.concatenate([e_tipo, extra["tipo"]])
            e_t = np.concatenate([e_t, extra["t"]]); e_tit = np.concatenate([e_tit, extra["tit"]])
            e_fil = np.concatenate([e_fil, extra["fil"]]); e_pos = np.concatenate([e_pos, extra["pos"]])
            e_termo = np.concatenate([e_termo, extra["termo"]]); e_aval = np.concatenate([e_aval, extra["aval"]])
        n = len(e_sid)
        # seq por sessão segundo o tempo real
        o = np.lexsort((e_t, e_sid))
        e_sid, e_p, e_dev, e_ver, e_dt, e_tipo, e_t, e_tit, e_fil, e_pos, e_termo, e_aval = (
            x[o] for x in (e_sid, e_p, e_dev, e_ver, e_dt, e_tipo, e_t, e_tit, e_fil, e_pos, e_termo, e_aval))
        cnt = np.unique(e_sid, return_counts=True)[1]
        seq = _rank(cnt) + 1
        # horário registrado pelo dispositivo
        plat = self.dv["plat"][e_dev]
        local = (plat == "tv_os_a") & (e_ver < IDX_V500)
        tz = self.p_tz[e_p]
        oc = self._relogio(e_t, e_dev)
        oc = np.where(local, oc + tz * 3600, oc)
        # fora de ordem: troca de timestamp com o vizinho na mesma sessão
        sw = np.where((rng.random(n) < 0.006) & np.r_[e_sid[1:] == e_sid[:-1], False])[0]
        oc[sw], oc[sw + 1] = oc[sw + 1].copy(), oc[sw].copy()
        # recebimento no servidor (UTC)
        lat = rng.lognormal(0.7, 0.8, n).astype(np.int64)
        late = (np.isin(e_dt, [1, 3]) & (rng.random(n) < 0.025)) | (rng.random(n) < 0.004)
        lat[late] += (rng.exponential(1.5, late.sum()) * DIA).astype(np.int64) + 3600
        rec = e_t + lat
        # nomes de evento (renomeados a partir da 6.0 no app móvel)
        nome = TIPOS_EV[e_tipo].copy()
        ren = (e_ver >= IDX_V600) & np.isin(e_dt, [1, 3])
        for k, v in RENOMEADOS.items():
            nome[ren & (e_tipo == k)] = v
        # duplicados (retentativa do cliente)
        dup = np.where(rng.random(n) < 0.012)[0]
        idx = np.concatenate([np.arange(n), dup])
        rec_all = np.concatenate([rec, rec[dup] + rng.integers(1, 90, len(dup))])
        # falha de pipeline
        falha = self._em_falha(rec_all)
        idx, rec_all = idx[~falha], rec_all[~falha]
        o = np.argsort(rec_all, kind="stable")
        idx, rec_all = idx[o], rec_all[o]
        m = len(idx)
        aval = np.array([None, "positiva", "negativa"], dtype=object)[e_aval[idx]]
        self.out["eventos_app"].escrever(dict(
            evento_id=self.next_id["evento"] + np.arange(m), sessao_id=e_sid[idx], perfil_id=e_p[idx] + 1,
            seq=seq[idx], tipo_evento=nome[idx], ocorrido_em=oc[idx], recebido_em=rec_all,
            titulo_id=(e_tit[idx] + 1, e_tit[idx] < 0), fileira=(FILEIRAS[np.maximum(e_fil[idx], 0)], e_fil[idx] < 0),
            posicao=(e_pos[idx], e_pos[idx] < 0), termo_busca=e_termo[idx], avaliacao=aval,
            versao_app=VERSAO_NOMES[e_ver[idx]].astype(object)))
        self.next_id["evento"] += m
        for nome_s, v in (("eventos_total", m), ("eventos_duplicados", len(dup)), ("eventos_atrasados", int(late.sum())),
                          ("eventos_fora_ordem", 2 * len(sw)), ("eventos_horario_local", int(local.sum())),
                          ("eventos_falha_pipeline", int(falha.sum())), ("eventos_renomeados", int((ren & np.isin(e_tipo, [2, 4])).sum())),
                          ("eventos_relogio_errado", int((self.dv["relogio"][e_dev] != 0).sum()))):
            st[nome_s] = st.get(nome_s, 0) + v
