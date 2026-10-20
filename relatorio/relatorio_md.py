"""docs/RELATORIO.md: a leitura escrita do relatório, gerada do mesmo cubo que o HTML embute (dados SINTÉTICOS).

As agregações repetem as do HTML (razão de somas sobre o cubo filtrado), então os números batem com o relatório
interativo quando ele mostra o mesmo período sem filtros.
"""
from __future__ import annotations

import math
from collections import defaultdict

PAGINA = "https://arielabade.github.io/dados-sinteticos-streaming-cinelume/relatorio/"
MIN = 30
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MOTIVOS = {"pouco_uso": "Pouco uso", "preco": "Preço", "temporario": "Temporário", "financeiro": "Financeiro", "outro": "Outro",
           "problemas_tecnicos": "Problemas técnicos", "catalogo": "Catálogo", "terminei_o_que_queria": "Terminei o que queria",
           "compartilhamento": "Compartilhamento"}
CATS = {"acesso_login": "Acesso e login", "pagamento": "Pagamento", "cobranca": "Cobrança", "cancelamento": "Cancelamento",
        "conteudo": "Conteúdo", "reproducao": "Reprodução", "outros": "Outros"}
METODOS = {"cartao": "Cartão", "pix": "Pix", "boleto": "Boleto"}


def _n(v, d=0):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def brl(v, d=0):
    return "—" if v is None or (isinstance(v, float) and not math.isfinite(v)) else "R$ " + _n(v, d)


def pct(v, d=1):
    return "—" if v is None or (isinstance(v, float) and not math.isfinite(v)) else _n(v * 100, d) + "%"


def var(a, b, d=1):
    if not b or a is None or not math.isfinite(a) or not math.isfinite(b):
        return "—"
    r = a / b - 1
    return ("+" if r >= 0 else "") + _n(r * 100, d) + "%"


def pp(a, b):
    if a is None or b is None or not math.isfinite(a) or not math.isfinite(b):
        return "—"
    return ("+" if a - b >= 0 else "") + _n((a - b) * 100, 1) + " p.p."


def mes_longo(m):
    return f"{MESES_PT[int(m[5:]) - 1]}/{m[:4]}"


def tabela(cab, linhas, texto=()):
    """texto: índices de colunas de texto (alinhadas à esquerda)."""
    al = ["---" if i == 0 or i in texto else "---:" for i in range(len(cab))]
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join(al) + "|"]
    out += ["| " + " | ".join(str(x) for x in ln) + " |" for ln in linhas]
    return "\n".join(out)


class Cubo:
    def __init__(self, d):
        self.d, self.M = d, d["meses"]
        self.idx = {m: i for i, m in enumerate(d["medidas"])}

    def soma(self, a, b, chave=None, filtro=None):
        out = defaultdict(lambda: defaultdict(float))
        for k, v in zip(self.d["cubo"]["chaves"], self.d["cubo"]["valores"], strict=True):
            if k[0] < a or k[0] > b or (filtro and not filtro(k)):
                continue
            g = chave(k) if chave else "_"
            for m, i in self.idx.items():
                out[g][m] += v[i]
        return out if chave else out["_"]

    def midia(self, a, b, por_canal=False):
        out = defaultdict(lambda: defaultdict(float))
        for mes, canal, inv, imp, cli, att in self.d["midia"]:
            if a <= mes <= b:
                o = out[canal if por_canal else "_"]
                o["inv"] += inv
                o["imp"] += imp
                o["cli"] += cli
                o["att"] += att
        return out if por_canal else out["_"]

    def longa(self, tab, a, b):
        out = defaultdict(int)
        for mes, _c, _p, _m, cat, n in self.d[tab]:
            if a <= mes <= b:
                out[cat] += n
        return out

    def kpis(self, a, b):
        s, fim, md = self.soma(a, b), self.soma(b, b), self.midia(a, b)
        pagos = {x["codigo"] for x in self.d["canais"] if x["pago"]}
        sp = self.soma(a, b, filtro=lambda k: k[1] in pagos)
        inv_pago = sum(o["inv"] for k, o in self.midia(a, b, por_canal=True).items() if k in pagos)
        enc, base = s["enc_vol"] + s["enc_invol"], s["ativos_ini"]
        churn = enc / base if base else float("nan")
        arpu = s["mrr"] / s["ativos_fim"] if s["ativos_fim"] else float("nan")
        cac = md["inv"] / s["pagantes_30d"] if s["pagantes_30d"] else float("nan")
        ltv = arpu / churn if churn and math.isfinite(churn) else float("nan")
        return {"ativos": fim["ativos_fim"], "mrr": fim["mrr"], "receita": s["receita"], "novas": s["novas"], "reat": s["reativacoes"],
                "enc": enc, "vol": s["enc_vol"], "inv_enc": s["enc_invol"], "base": base, "churn": churn,
                "churn_vol": s["enc_vol"] / base if base else float("nan"), "churn_inv": s["enc_invol"] / base if base else float("nan"),
                "arpu": arpu, "ltv": ltv, "inv": md["inv"], "cad": s["cadastros"], "pag": s["pagantes_30d"], "cac": cac,
                "cac_pago": inv_pago / sp["pagantes_30d"] if sp["pagantes_30d"] else float("nan"),
                "nps": (s["nps_promotores"] - s["nps_detratores"]) / s["nps_respostas"] * 100 if s["nps_respostas"] else float("nan"),
                "npsN": s["nps_respostas"], "horas": s["horas"] / s["contas_assistiram"] if s["contas_assistiram"] else float("nan"),
                "extra": s["membro_extra"], "falha": s["cobrancas_falhas"] / s["cobrancas"] if s["cobrancas"] else float("nan"),
                "tickets": s["tickets"]}


def nivel(v, r):
    if v is None or not math.isfinite(v):
        return "—"
    if r["alto"]:
        return "Saudável" if v >= r["bom"] else ("Alerta" if v < r["ruim"] else "Atenção")
    return "Saudável" if v <= r["bom"] else ("Alerta" if v > r["ruim"] else "Atenção")


def saude(c: "Cubo", a: str, b: str) -> dict:
    """As mesmas métricas do painel 'Saúde do negócio' do HTML, para o período [a, b]."""
    M = c.M
    i0, i1 = M.index(a), M.index(b)
    n = i1 - i0 + 1
    K = c.kpis(a, b)
    s = c.soma(a, b)
    ini = c.soma(M[i0 - 1], M[i0 - 1]) if i0 > 0 else None
    at0, mrr0 = (ini["ativos_fim"], ini["mrr"]) if ini else (float("nan"), float("nan"))
    entra = s["ativos_ini"] + s["novas"] + s["reativacoes"]
    return {
        "cresc_at": K["ativos"] / at0 - 1, "cresc_at_mes": (K["ativos"] / at0) ** (1 / n) - 1 if at0 else float("nan"),
        "cresc_mrr": K["mrr"] / mrr0 - 1, "cresc_mrr_mes": (K["mrr"] / mrr0) ** (1 / n) - 1 if mrr0 else float("nan"),
        "liquido": K["novas"] + K["reat"] - K["enc"], "quick": (K["novas"] + K["reat"]) / K["enc"] if K["enc"] else float("nan"),
        "churn": K["churn"], "payback": K["cac_pago"] / K["arpu"], "ltvcac": K["ltv"] / K["cac_pago"],
        "invol": K["inv_enc"] / K["enc"] if K["enc"] else float("nan"),
        "ativ": s["contas_assistiram"] / entra if entra else float("nan"), "nps": K["nps"], "at0": at0, "K": K,
    }


def escrever(d: dict) -> str:
    c = Cubo(d)
    M = c.M
    ini, fim = M[0], M[-1]
    a12, b12 = M[-12], M[-1]
    a24, b24 = M[-24], M[-13]
    P, Q, T = c.kpis(a12, b12), c.kpis(a24, b24), c.kpis(ini, fim)
    R = d["referencias"]
    H, HQ = saude(c, a12, b12), saude(c, a24, b24)
    linhas_s = [
        ["Crescimento de assinantes no período", ("+" if H["cresc_at"] >= 0 else "") + pct(H["cresc_at"]), ("+" if HQ["cresc_at"] >= 0 else "") + pct(HQ["cresc_at"]),
         f"{pct(H['cresc_at_mes'])} ao mês · " + R["cresc"]["txt"], nivel(H["cresc_at_mes"], R["cresc"])],
        ["Crescimento da receita recorrente", ("+" if H["cresc_mrr"] >= 0 else "") + pct(H["cresc_mrr"]), ("+" if HQ["cresc_mrr"] >= 0 else "") + pct(HQ["cresc_mrr"]),
         f"{pct(H['cresc_mrr_mes'])} ao mês · " + R["cresc"]["txt"], nivel(H["cresc_mrr_mes"], R["cresc"])],
        ["Quick ratio (entradas / saídas)", _n(H["quick"], 2), _n(HQ["quick"], 2), R["quick"]["txt"], nivel(H["quick"], R["quick"])],
        ["Churn mensal", pct(H["churn"]), pct(HQ["churn"]), R["churn"]["txt"], nivel(H["churn"], R["churn"])],
        ["Payback do CAC (canais pagos)", _n(H["payback"], 1) + " meses", _n(HQ["payback"], 1) + " meses", R["payback"]["txt"], nivel(H["payback"], R["payback"])],
        ["LTV (receita) / CAC (canais pagos)", _n(H["ltvcac"], 1) + "x", _n(HQ["ltvcac"], 1) + "x", R["ltvcac"]["txt"], nivel(H["ltvcac"], R["ltvcac"])],
        ["Parcela involuntária do churn", pct(H["invol"], 0), pct(HQ["invol"], 0), R["invol"]["txt"], nivel(H["invol"], R["invol"])],
        ["Ativação (assinantes que assistiram no mês)", pct(H["ativ"], 0), pct(HQ["ativ"], 0), R["ativ"]["txt"], nivel(H["ativ"], R["ativ"])],
        ["NPS", _n(H["nps"], 0), _n(HQ["nps"], 0), R["nps"]["txt"], nivel(H["nps"], R["nps"])],
    ]
    vigiar = [x for x in linhas_s if x[4] == "Alerta"] + [x for x in linhas_s if x[4] == "Atenção"]
    def min1(t):  # baixa só a primeira palavra, e só se não for sigla
        w, _, resto = t.split(" (")[0].partition(" ")
        return (w if w.isupper() else w.lower()) + (" " + resto if resto else "")
    fortes = [min1(x[0]) for x in linhas_s if x[4] == "Saudável"]
    ritmo = ""
    if math.isfinite(HQ["cresc_at"]) and HQ["cresc_at"] > 0:
        ritmo = (f" O ritmo {'desacelerou' if H['cresc_at'] < HQ['cresc_at'] else 'acelerou'}: nos 12 meses anteriores a base tinha crescido "
                 f"{pct(HQ['cresc_at'])}, e a receita recorrente {pct(HQ['cresc_mrr'])}.")
    resumo_s = (f"Nos últimos 12 meses a base cresceu **{pct(H['cresc_at'])}** ({_n(H['liquido'])} assinantes líquidos) e a receita recorrente "
                f"**{pct(H['cresc_mrr'])}**: para cada assinante que saiu, entraram **{_n(H['quick'], 1)}**.{ritmo} "
                + (f"Pontos fortes: {', '.join(fortes[:4])}. " if fortes else "")
                + (f"Ponto a vigiar: **{min1(vigiar[0][0])}** ({vigiar[0][1]})." if vigiar else "Nenhuma métrica fora da faixa saudável."))
    nome_c = {x["codigo"]: x["nome"] for x in d["canais"]}
    pago_c = {x["codigo"]: x["pago"] for x in d["canais"]}
    nome_p = {x["id"]: x["nome"] for x in d["planos"]}

    # canais (últimos 12 meses)
    s_c, m_c = c.soma(a12, b12, chave=lambda k: k[1]), c.midia(a12, b12, por_canal=True)
    lin_c, cac_pago = [], {}
    for cod in nome_c:
        o, m = s_c.get(cod, defaultdict(float)), m_c.get(cod, defaultdict(float))
        base, enc = o["ativos_ini"], o["enc_vol"] + o["enc_invol"]
        churn = enc / base if base else float("nan")
        arpu = o["mrr"] / o["ativos_fim"] if o["ativos_fim"] else float("nan")
        cac = m["inv"] / o["pagantes_30d"] if o["pagantes_30d"] else float("nan")
        ltv = arpu / churn if churn and math.isfinite(churn) else float("nan")
        if pago_c[cod] and math.isfinite(cac):
            cac_pago[cod] = (cac, ltv / cac if cac else float("nan"), o["pagantes_30d"])
        star = " *" if o["pagantes_30d"] < MIN else ""
        lin_c.append([f"**{nome_c[cod]}**", brl(m["inv"]), _n(o["cadastros"]), _n(m["att"]),
                      var(m["att"], o["cadastros"], 0) if o["cadastros"] else "—", _n(o["pagantes_30d"]) + star,
                      (brl(cac) + star) if m["inv"] else "R$ 0", pct(churn), brl(ltv),
                      (_n(ltv / cac, 2) + "x") if m["inv"] and math.isfinite(ltv) and cac else "—"])
    caros = sorted(cac_pago.items(), key=lambda kv: -kv[1][0])

    # planos e métodos (últimos 12 meses)
    s_p = c.soma(a12, b12, chave=lambda k: k[2])
    f_p = c.soma(b12, b12, chave=lambda k: k[2])
    lin_p = []
    horas_p = {}
    for pid, nome in nome_p.items():
        o, f = s_p.get(pid, defaultdict(float)), f_p.get(pid, defaultdict(float))
        enc = o["enc_vol"] + o["enc_invol"]
        h = o["horas"] / o["contas_assistiram"] if o["contas_assistiram"] else float("nan")
        horas_p[nome] = h
        nps = (o["nps_promotores"] - o["nps_detratores"]) / o["nps_respostas"] * 100 if o["nps_respostas"] else float("nan")
        lin_p.append([f"**{nome}**", _n(f["ativos_fim"]), brl(o["receita"]), brl(o["mrr"] / o["ativos_fim"] if o["ativos_fim"] else float("nan"), 2),
                      pct(enc / o["ativos_ini"] if o["ativos_ini"] else float("nan")), _n(h, 1) + " h",
                      _n(nps, 0) + (" *" if o["nps_respostas"] < MIN else "")])
    s_m = c.soma(a12, b12, chave=lambda k: k[3])
    lin_m, inv_m = [], {}
    for met in d["metodos"]:
        o = s_m.get(met, defaultdict(float))
        ci = o["enc_invol"] / o["ativos_ini"] if o["ativos_ini"] else float("nan")
        inv_m[met] = ci
        lin_m.append([f"**{METODOS.get(met, met)}**", _n(o["ativos_fim"] / 12), pct(ci),
                      pct(o["cobrancas_falhas"] / o["cobrancas"] if o["cobrancas"] else float("nan")),
                      pct(o["enc_vol"] / o["ativos_ini"] if o["ativos_ini"] else float("nan"))])
    pior_met = max(inv_m, key=lambda k: inv_m[k] if math.isfinite(inv_m[k]) else -1)

    # reajustes: receita por assinante nos 3 meses antes e depois de cada um
    reaj = []
    for e in d["eventos"]:
        if not e["rotulo"].startswith("reajuste"):
            continue
        i = M.index(e["mes"])
        if i < 3 or i + 3 > len(M):
            continue
        antes, depois = c.kpis(M[i - 3], M[i - 1]), c.kpis(M[i], M[i + 2])
        reaj.append([mes_longo(e["mes"]), brl(antes["arpu"], 2), brl(depois["arpu"], 2), var(depois["arpu"], antes["arpu"]),
                     pct(antes["churn_vol"]), pct(depois["churn_vol"]), pp(depois["churn_vol"], antes["churn_vol"])])

    mot = c.longa("motivos", a12, b12)
    mt = sorted(mot.items(), key=lambda kv: -kv[1])
    mtot = sum(mot.values())
    tk = c.longa("tickets", a12, b12)
    tt = sorted(tk.items(), key=lambda kv: -kv[1])
    ttot = sum(tk.values())
    busca = next((x for x in lin_c if x[0] == "**Busca paga**"), None)
    tv = next((x for x in lin_c if x[0] == "**TV**"), None)
    h_ord = sorted(((k, v) for k, v in horas_p.items() if math.isfinite(v)), key=lambda kv: -kv[1])

    achados = [
        f"**Base e receita.** {_n(P['ativos'])} assinantes ativos em {mes_longo(b12)} ({var(P['ativos'], Q['ativos'])} em 12 meses) e "
        f"{brl(P['receita'])} de receita paga nos últimos 12 meses ({var(P['receita'], Q['receita'])} contra os 12 anteriores).",
        f"**Churn.** {pct(P['churn'])} ao mês nos últimos 12 meses ({pp(P['churn'], Q['churn'])}); o involuntário, falha de pagamento, "
        f"é {pct(P['inv_enc'] / P['enc'], 0)} dos encerramentos, e {METODOS[pior_met]} tem o maior churn involuntário ({pct(inv_m[pior_met])} ao mês).",
        f"**Canais.** Entre os canais pagos, {nome_c[caros[0][0]]} tem o CAC mais alto ({brl(caros[0][1][0])}) e {nome_c[caros[-1][0]]} o mais baixo "
        f"({brl(caros[-1][1][0])})." if len(caros) >= 2 else "",
        f"**Atribuição.** A ferramenta de atribuição credita à busca paga {busca[4]} cadastros em relação ao canal gravado na conta, "
        f"e à TV {tv[4]}: decidir verba pela atribuição superinveste em busca e subinveste em TV." if busca and tv else "",
        f"**Cancelamento.** {MOTIVOS.get(mt[0][0], mt[0][0])} é o motivo mais citado ({pct(mt[0][1] / mtot, 0)} das {_n(mtot)} respostas em 12 meses)." if mtot else "",
        f"**Uso.** Quem assina {h_ord[0][0]} assiste {_n(h_ord[0][1], 1)} h por mês, contra {_n(h_ord[-1][1], 1)} h no {h_ord[-1][0]}." if len(h_ord) > 1 else "",
    ]

    quali = [[q["achado"], _n(q["linhas"]), (_n(q["de"]) + f" ({pct(q['linhas'] / q['de'])})") if q["de"] else "—", q["tratamento"]] for q in d["qualidade"]]

    return f"""# Cinelume · Relatório gerencial

**{mes_longo(ini)} a {mes_longo(fim)}** · preparado por ABADE (Strategy · Data · Growth) · fonte: `{d['meta']['fonte']}` ({_n(d['meta']['contas'])} contas)

> **Dados sintéticos.** A Cinelume é uma empresa fictícia; todo cliente, real e resultado foi gerado pelo simulador deste repositório.
> O relatório demonstra o método, não descreve um negócio real.

**Versão interativa: [relatório estilo Power BI]({PAGINA})**, com navegador de meses, comparação com o período anterior ou com o ano
anterior, e filtros de canal, plano e método de pagamento. Este texto e o relatório interativo saem do mesmo cubo de dados
(`python relatorio/build.py`); aqui a leitura é dos **últimos 12 meses ({mes_longo(a12)} a {mes_longo(b12)}) contra os 12 anteriores**.

---

## 1. Resumo

{tabela(["Indicador", f"{mes_longo(a12)}–{mes_longo(b12)}", f"{mes_longo(a24)}–{mes_longo(b24)}", "Variação"], [
    ["Assinantes ativos (fim)", _n(P['ativos']), _n(Q['ativos']), var(P['ativos'], Q['ativos'])],
    ["Receita recorrente (último mês)", brl(P['mrr']), brl(Q['mrr']), var(P['mrr'], Q['mrr'])],
    ["Receita paga", brl(P['receita']), brl(Q['receita']), var(P['receita'], Q['receita'])],
    ["Novas assinaturas", _n(P['novas']), _n(Q['novas']), var(P['novas'], Q['novas'])],
    ["Churn mensal", pct(P['churn']), pct(Q['churn']), pp(P['churn'], Q['churn'])],
    ["Receita por assinante / mês", brl(P['arpu'], 2), brl(Q['arpu'], 2), var(P['arpu'], Q['arpu'])],
    ["Investimento em aquisição", brl(P['inv']), brl(Q['inv']), var(P['inv'], Q['inv'])],
    ["CAC dos canais pagos (busca, social, TV)", brl(P['cac_pago']), brl(Q['cac_pago']), var(P['cac_pago'], Q['cac_pago'])],
    ["CAC médio, todos os canais (inclui orgânico)", brl(P['cac']), brl(Q['cac']), var(P['cac'], Q['cac'])],
    ["LTV (receita) / CAC dos canais pagos", _n(P['ltv'] / P['cac_pago'], 1) + "x", _n(Q['ltv'] / Q['cac_pago'], 1) + "x", var(P['ltv'] / P['cac_pago'], Q['ltv'] / Q['cac_pago'])],
    ["NPS", _n(P['nps'], 0), _n(Q['nps'], 0), ("+" if P['nps'] >= Q['nps'] else "") + _n(P['nps'] - Q['nps'], 0) + " pts"],
])}

### Saúde do negócio

{resumo_s}

{tabela(["Métrica", f"{mes_longo(a12)}–{mes_longo(b12)}", f"{mes_longo(a24)}–{mes_longo(b24)}", "Faixa de leitura", "Leitura"], linhas_s, texto=(3, 4))}

As faixas são regras de bolso declaradas (as mesmas do relatório interativo), não benchmarks medidos. LTV e payback usam receita,
não margem: com custo de conteúdo, os dois ficam piores.

**O que os dados mostram**

{chr(10).join("- " + a for a in achados if a)}

---

## 2. Aquisição (últimos 12 meses)

*A pergunta: cada real investido está trazendo assinantes que pagam e ficam?*

O canal de cada cadastro é o gravado na conta. A coluna "atribuição" mostra o que a ferramenta de último clique creditou ao canal;
a diferença é a distorção que ela introduz. CAC = investimento / contas novas que pagaram a primeira fatura em até 30 dias.

{tabela(["Canal", "Investimento", "Cadastros (conta)", "Cadastros (atribuição)", "Atribuição vs conta", "Pagantes 30d", "CAC", "Churn mensal", "LTV (receita)", "LTV / CAC"], lin_c)}

\\* menos de {MIN} pagantes: direção, não ranking. Orgânico não tem investimento; indicação é o crédito pago ao indicador; parceria é o fee
por cadastro. LTV usa receita, não margem: não desconta custo de conteúdo.

---

## 3. Receita e reajustes

*A pergunta: a receita cresce por mais assinantes, por mais receita por assinante, ou pelos dois?*

Receita por assinante e churn voluntário nos 3 meses antes e nos 3 meses depois de cada reajuste de preço:

{tabela(["Reajuste", "Receita / assinante antes", "Depois", "Variação", "Churn voluntário antes", "Depois", "Variação"], reaj)}

Cobrança de membro extra (desde 10/03/2025): {brl(P['extra'])} nos últimos 12 meses, {pct(P['extra'] / P['receita'])} da receita paga.

---

## 4. Planos e retenção (últimos 12 meses)

*A pergunta: quem está saindo, por quê, e quanto disso dá para evitar?* O churn involuntário (falha de pagamento) foi
**{pct(P['inv_enc'] / P['enc'], 0)}** das saídas, cerca de **{brl(P['inv_enc'] / 12 * P['arpu'])}** de receita recorrente perdida por mês: é a parte
mais evitável, com retentativa no cartão, lembrete no boleto e migração para cobrança automática.

{tabela(["Plano", "Assinantes (fim)", "Receita paga", "Receita / assinante / mês", "Churn mensal", "Horas / conta / mês", "NPS"], lin_p)}

{tabela(["Método de pagamento", "Assinantes (média)", "Churn involuntário", "Falha de cobrança", "Churn voluntário"], lin_m)}

Motivos de cancelamento (pesquisa opcional, 12 meses): {"; ".join(f"{MOTIVOS.get(k, k)} {pct(v / mtot, 0)}" for k, v in mt[:5])}.

Tickets de suporte (12 meses, categorias normalizadas): {"; ".join(f"{CATS.get(k, k)} {pct(v / ttot, 0)}" for k, v in tt[:5])}.

---

## 5. Qualidade dos dados

O banco tem imperfeições de propósito. Cada uma foi encontrada nos dados, contada e tratada antes de virar métrica:

{tabela(["Achado", "Linhas", "De", "Tratamento"], quali, texto=(3,))}

---

## 6. Método

- Datas em horário de Brasília (UTC−3). Assinantes ativos = assinaturas vigentes no último instante do mês; o plano é o vigente naquele
  momento, reconstruído dos upgrades e downgrades.
- Churn mensal = encerramentos / assinantes ativos no início de cada mês, somados no período. Toda taxa é razão de somas.
- Receita paga = faturas quitadas, pelo mês de emissão. Receita recorrente = faturas mensais no mês do ciclo; anuais divididas em 12.
- LTV (receita) = receita por assinante / churn mensal. Período inteiro ({mes_longo(ini)}–{mes_longo(fim)}): {_n(T['novas'])} novas assinaturas,
  {_n(T['enc'])} encerramentos, {brl(T['receita'])} de receita paga.
- Um número sobre menos de {MIN} eventos é marcado com \\* e não sustenta conclusão.
- O build confere o cubo contra as tabelas brutas e para se algo divergir: {"; ".join(d.get("reconciliacao", []))}.
"""
