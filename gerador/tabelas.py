"""Montagem das tabelas de negócio a partir dos registros da simulação."""
import numpy as np

from .config import CANAIS, DIA, NDIAS, PARCERIA_OPERADORA, PLANOS, T0, dia
from .simulacao import CAMPANHAS, CATEG_TICKET, CODIGOS_RECUSA, CUPONS, EV, MOTIVOS, ORIGENS

FIM_TS = T0 + NDIAS * DIA
COMENT_CANCEL = {
    0: ["Ficou caro depois do aumento.", "Preço alto pro quanto eu uso.", "Achei caro demais."],
    1: ["Quase não estou usando.", "Não tenho tempo de assistir.", "Uso muito pouco."],
    2: ["Faltam títulos que eu gosto.", "O catálogo está fraco.", "Tiraram o que eu assistia."],
    3: ["Terminei a série que queria ver.", "Já vi tudo que me interessava.", "Volto quando tiver temporada nova."],
    4: ["Trava muito.", "A qualidade cai toda hora.", "O app fica carregando sem parar."],
    5: ["Não concordo com a cobrança de membro extra.", "Minha família não consegue mais usar.", "Cobrança por perfil extra."],
    6: ["Cortando gastos.", "Estou sem renda no momento.", "Mês apertado."],
    7: ["Vou viajar.", "Pausa temporária.", "Volto depois das férias."],
    8: ["Assino outro serviço.", "Prefiro não dizer.", "Mudança de rotina."],
}
COMENT_NPS = {
    "detrator": ["O app trava toda hora.", "Caro para o que oferece.", "Catálogo fraco.", "Muitos anúncios.",
                 "A qualidade da imagem cai.", "Cobrança indevida."],
    "neutro": ["É ok.", "Bom, mas poderia ter mais lançamentos.", "Gosto das séries originais.", "Razoável."],
    "promotor": ["Adoro as séries originais!", "Ótimo custo-benefício.", "App muito bom.", "Recomendo para todos."],
}
VAR_CAT = {"pagamento": ["Pagamento", "pagto", "PAGAMENTO"], "reproducao": ["Reprodução", "reproducao ", "reprodução"],
           "acesso_login": ["login", "Acesso/Login", "acesso"], "cobranca": ["Cobrança", "cobrança", "COBRANCA"],
           "cancelamento": ["Cancelamento", "cancelar"], "conteudo": ["Conteúdo", "conteúdo"], "outros": ["Outros", "outro"]}


def nulo_se_neg(x):
    x = np.asarray(x)
    return (np.where(x < 0, 0, x), x < 0)


def tabelas_basicas(sim):
    out = {}
    out["canais"] = dict(canal_id=np.array([c[0] for c in CANAIS]), codigo=np.array([c[1] for c in CANAIS], dtype=object),
                         nome=np.array([c[2] for c in CANAIS], dtype=object), tipo=np.array([c[3] for c in CANAIS], dtype=object),
                         pago=np.array([1 if c[3] == "pago" else 0 for c in CANAIS]))
    out["planos"] = {k: np.array([p[i] for p in PLANOS], dtype=object if isinstance(PLANOS[0][i], str) else None)
                     for i, k in enumerate(["plano_id", "codigo", "nome", "com_anuncios", "resolucao_maxima",
                                            "telas_simultaneas", "max_perfis", "permite_membro_extra"])}
    pr = sim["precos_rows"]
    out["precos"] = dict(
        preco_id=np.array([r[0] for r in pr]), plano_id=nulo_se_neg([-1 if r[1] is None else r[1] for r in pr]),
        item=np.array([r[2] for r in pr], dtype=object), periodicidade=np.array([r[3] for r in pr], dtype=object),
        valor_brl=np.array([r[4] for r in pr]), vigencia_inicio=np.array([dia(r[5]) for r in pr]),
        vigencia_fim=(np.array([0 if r[6] is None else dia(r[6]) for r in pr]), np.array([r[6] is None for r in pr])))
    out["cupons"] = dict(
        cupom_id=np.arange(1, len(CUPONS) + 1), codigo=np.array([c[0] for c in CUPONS], dtype=object),
        descricao=np.array([c[1] for c in CUPONS], dtype=object), tipo_desconto=np.array([c[2] for c in CUPONS], dtype=object),
        valor_desconto=np.array([float(c[3]) for c in CUPONS]), duracao_ciclos=np.array([c[4] for c in CUPONS]),
        valido_de=np.array([dia(c[5]) for c in CUPONS]),
        valido_ate=(np.array([0 if c[6] is None else dia(c[6]) for c in CUPONS]), np.array([c[6] is None for c in CUPONS])),
        canal_id=nulo_se_neg([-1 if c[7] is None else c[7] for c in CUPONS]), apenas_novos=np.array([c[8] for c in CUPONS]))
    return out


def investimento_diario(ct):
    inv, imp, cli, atr = ct["investimento"]
    nc, nd = inv.shape
    c = np.repeat(np.arange(nc), nd)
    d = np.tile(np.arange(nd), nc)
    keep = ~((c == 4) & (d < PARCERIA_OPERADORA))
    c, d = c[keep], d[keep]
    o = np.lexsort((c, d))
    c, d = c[o], d[o]
    return dict(data=d, canal_id=c + 1, investimento_brl=inv[c, d], impressoes=nulo_se_neg(imp[c, d]),
                cliques=nulo_se_neg(cli[c, d]), cadastros_atribuidos=atr[c, d])


def tabelas_negocio(rng, sim, ct, pf, dv):
    out = {}
    ns = sim["ns"]
    st_txt = np.array(["", "trial", "ativa", "inadimplente", "cancelamento_agendado", "encerrada"], dtype=object)
    met_txt = np.array(["cartao", "pix", "boleto"], dtype=object)
    s_ini = sim["s_ini"]
    out["assinaturas"] = dict(
        assinatura_id=np.arange(1, ns + 1), conta_id=sim["s_conta"] + 1, plano_id=sim["s_plano"],
        periodicidade=np.where(sim["s_anual"], "anual", "mensal").astype(object),
        metodo_pagamento=met_txt[sim["s_metodo"]], status=st_txt[sim["s_status"]], iniciada_em=s_ini,
        trial_fim_em=nulo_se_neg(sim["s_trial"]), cancelamento_solicitado_em=nulo_se_neg(sim["s_creq"]),
        encerrada_em=nulo_se_neg(sim["s_fim"]),
        tipo_encerramento=(np.array([None, "voluntario", "involuntario"], dtype=object)[sim["s_tfim"]], sim["s_tfim"] == 0),
        renovacao_automatica=(sim["s_metodo"] == 0).astype(np.int8),
        assinatura_anterior_id=nulo_se_neg(np.where(sim["s_ant"] >= 0, sim["s_ant"] + 1, -1)))

    ev = sim["ev"]
    m = ev["t"] < FIM_TS
    o = np.argsort(ev["t"][m], kind="stable")
    g = {k: v[m][o] for k, v in ev.items()}
    out["assinatura_eventos"] = dict(
        evento_id=np.arange(1, len(o) + 1), assinatura_id=g["sub"] + 1, tipo=np.array(EV, dtype=object)[g["tipo"]],
        ocorrido_em=g["t"], plano_anterior_id=nulo_se_neg(g["pa"]), plano_novo_id=nulo_se_neg(g["pn"]),
        origem=np.array(ORIGENS, dtype=object)[g["origem"]])

    r = sim["resg"]
    out["cupom_resgates"] = dict(resgate_id=np.arange(1, len(r["cupom"]) + 1), cupom_id=r["cupom"] + 1,
                                 conta_id=r["conta"] + 1, assinatura_id=r["sub"] + 1, resgatado_em=r["t"])

    # ---------------- faturas e pagamentos
    f = sim["fat"]
    o = np.argsort(f["idx"])
    f = {k: v[o] for k, v in f.items()}
    nf = len(f["idx"])
    p = sim["pag"]
    p = {k: v for k, v in p.items()}
    p["valor"] = p["valor"].astype(float)
    reemb = p["tipo"] == 1
    p["valor"][reemb] = -f["total"][p["fat"][reemb]]
    dentro = p["t"] < FIM_TS
    p = {k: v[dentro] for k, v in p.items()}
    status = np.full(nf, 1, np.int8)  # aberta
    aprov = (p["tipo"] == 0) & (p["status"] == 0)
    status[p["fat"][aprov]] = 0
    upd = sim["fat_upd"]
    for s_ in (2, 4, 5):
        sel = upd["idx"][upd["status"] == s_]
        if s_ == 2:
            status[sel] = np.where(status[sel] == 0, 0, 2)
        else:
            status[sel] = s_
    emit_ok = f["emit"] < FIM_TS
    st_f = np.array(["paga", "aberta", "vencida", "cancelada", "reembolsada", "estornada"], dtype=object)
    fid = f["idx"] + 1
    out["faturas"] = dict(
        fatura_id=fid[emit_ok], assinatura_id=f["sub"][emit_ok] + 1, conta_id=f["conta"][emit_ok] + 1,
        preco_id=f["preco"][emit_ok], cupom_resgate_id=nulo_se_neg(np.where(f["resg"] >= 0, f["resg"] + 1, -1)[emit_ok]),
        periodo_inicio=f["ini"][emit_ok], periodo_fim=f["fim"][emit_ok], emitida_em=f["emit"][emit_ok],
        vencimento_em=f["venc"][emit_ok], valor_bruto=f["bruto"][emit_ok], valor_desconto=f["desc"][emit_ok],
        valor_membro_extra=f["extra"][emit_ok], valor_total=f["total"][emit_ok], status=st_f[status[emit_ok]])
    stats = {}
    # imperfeições: fatura paga sem pagamento; pagamento sem fatura
    pagas = np.where(status == 0)[0]
    sem_pag = rng.choice(pagas, int(len(pagas) * 0.0025), replace=False)
    drop = np.isin(p["fat"], sem_pag)
    p = {k: v[~drop] for k, v in p.items()}
    o = np.argsort(p["t"], kind="stable")
    p = {k: v[o] for k, v in p.items()}
    npg = len(p["t"])
    sem_fat = rng.random(npg) < 0.0015
    stats["faturas_pagas_sem_pagamento"] = int(len(sem_pag))
    stats["pagamentos_sem_fatura"] = int(sem_fat.sum())
    stats["chargebacks"] = int((p["tipo"] == 2).sum())
    stats["reembolsos"] = int((p["tipo"] == 1).sum())
    fat_id = np.where(sem_fat, -1, p["fat"] + 1)
    out["pagamentos"] = dict(
        pagamento_id=np.arange(1, npg + 1), fatura_id=nulo_se_neg(fat_id), conta_id=p["conta"] + 1,
        metodo=met_txt[p["metodo"]], tipo=np.array(["cobranca", "reembolso", "chargeback"], dtype=object)[p["tipo"]],
        tentativa=p["tent"], processado_em=p["t"], valor_brl=p["valor"],
        status=np.array(["aprovado", "recusado", "expirado", "contestado", "processado"], dtype=object)[p["status"]],
        codigo_recusa=(np.array(CODIGOS_RECUSA, dtype=object)[np.maximum(p["codigo"], 0)], p["codigo"] < 0))

    # ---------------- pesquisa de cancelamento
    q = sim["pesq"]
    o = np.argsort(q["t"], kind="stable")
    q = {k: v[o] for k, v in q.items()}
    n = len(q["t"])
    com = np.array([COMENT_CANCEL[c // 10][c % 10] for c in q["coment"]], dtype=object)
    out["pesquisa_cancelamento"] = dict(
        resposta_id=np.arange(1, n + 1), assinatura_id=q["sub"] + 1, conta_id=q["conta"] + 1, respondida_em=q["t"],
        motivo_principal=np.array(MOTIVOS, dtype=object)[q["motivo"]], comentario=(com, rng.random(n) < 0.55),
        probabilidade_voltar=nulo_se_neg(q["prob"]))

    # ---------------- tickets
    t = sim["tick"]
    o = np.argsort(t["t"], kind="stable")
    t = {k: v[o] for k, v in t.items()}
    n = len(t["t"])
    catg = np.array(CATEG_TICKET, dtype=object)[t["cat"]]
    var = rng.random(n) < 0.04
    for i in np.where(var)[0]:
        catg[i] = VAR_CAT[catg[i]][int(rng.integers(len(VAR_CAT[catg[i]])))]
    stats["tickets_categoria_variante"] = int(var.sum())
    out["tickets_suporte"] = dict(
        ticket_id=np.arange(1, n + 1), conta_id=t["conta"] + 1, aberto_em=t["t"],
        canal_atendimento=np.array(["chat", "email", "telefone"], dtype=object)[t["canal"]], categoria=catg,
        status=np.array(["aberto", "resolvido", "fechado_sem_resolucao"], dtype=object)[t["status"]],
        resolvido_em=nulo_se_neg(t["res_t"]), nota_satisfacao=nulo_se_neg(t["nota"]))

    # ---------------- NPS
    z = sim["nps"]
    o = np.argsort(z["t"], kind="stable")
    z = {k: v[o] for k, v in z.items()}
    n = len(z["t"])
    nota = z["nota"].astype(int)
    grupo = np.where(nota <= 6, "detrator", np.where(nota <= 8, "neutro", "promotor"))
    com = np.array([COMENT_NPS[gp][int(rng.integers(len(COMENT_NPS[gp])))] for gp in grupo], dtype=object)
    out["nps"] = dict(resposta_id=np.arange(1, n + 1), conta_id=z["conta"] + 1, respondida_em=z["t"], nota=nota,
                      comentario=(com, rng.random(n) < 0.6), canal_pesquisa=np.array(["email", "app"], dtype=object)[z["canal"]])

    # ---------------- notificações
    nt = sim["notif"]
    m = nt["t"] < FIM_TS
    o = np.argsort(nt["t"][m], kind="stable")
    nt = {k: v[m][o] for k, v in nt.items()}
    n = len(nt["t"])
    ab = np.where(nt["ab"] >= FIM_TS, -1, nt["ab"])
    cl = np.where((nt["cl"] >= FIM_TS) | (ab < 0), -1, nt["cl"])
    out["notificacoes"] = dict(
        notificacao_id=np.arange(1, n + 1), conta_id=nt["conta"] + 1,
        perfil_id=nulo_se_neg(np.where(nt["perfil"] >= 0, nt["perfil"] + 1, -1)),
        canal=np.array(["push", "email"], dtype=object)[nt["canal"]], campanha=np.array(CAMPANHAS, dtype=object)[nt["camp"]],
        titulo_id=nulo_se_neg(np.where(nt["titulo"] >= 0, nt["titulo"] + 1, -1)), enviada_em=nt["t"],
        aberta_em=nulo_se_neg(ab), clicada_em=nulo_se_neg(cl))

    # ---------------- perfis (colunas definidas na simulação)
    tab = dict(pf["tabela"])
    exc = sim["excluido"]
    exc_ok = (exc < NDIAS) & (exc >= pf["criado_dia"])
    t_exc = np.where(exc_ok, T0 + exc * DIA + rng.integers(0, DIA, pf["P"]), -1)
    t_exc = np.where(t_exc <= tab["criado_em"], tab["criado_em"] + 3600, t_exc)
    tab["excluido_em"] = nulo_se_neg(np.where(exc_ok, t_exc, -1))
    tab["membro_extra"] = sim["membro_extra"]
    out["perfis"] = tab
    return out, stats
