"""Relatório gerencial da Cinelume (dados SINTÉTICOS): do Parquet ao HTML estilo Power BI.

Lê ``dados*/parquet`` com DuckDB, aplica as regras de limpeza (cada uma contada e documentada), monta um cubo
mensal aditivo (mês × canal × plano × método de pagamento) e grava:

* ``docs/relatorio/index.html``: o relatório interativo, um arquivo só, com o cubo embutido;
* ``docs/RELATORIO.md``: a leitura escrita do período inteiro, gerada do mesmo cubo.

O HTML recalcula tudo no navegador para o período e os filtros escolhidos. Por isso o cubo guarda só **somas**
(contagens, valores, assinantes-mês): toda taxa é razão de somas, calculada depois do filtro.

Uso: ``python relatorio/build.py [--dados dados_medium/parquet]``
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
SAIDA_HTML = RAIZ / "docs" / "relatorio" / "index.html"
SAIDA_MD = RAIZ / "docs" / "RELATORIO.md"
MODELO = Path(__file__).resolve().parent / "modelo.html"

INICIO, FIM = "2023-10-01", "2026-10-31"    # período do banco, em dias civis de Brasília
FUSO = "INTERVAL 3 HOUR"                     # UTC → Brasília (UTC−3, sem horário de verão desde 2019)

# faixas de leitura dos cards (regras de bolso declaradas, não benchmarks medidos): bom, ruim, maior é melhor
REFERENCIAS = {
    "cresc":   {"bom": 0.01, "ruim": 0, "alto": True, "txt": "≥ +1% ao mês bom · < 0 alerta"},
    "quick":   {"bom": 2, "ruim": 1, "alto": True, "txt": "≥ 2 saudável · < 1 encolhendo"},
    "churn":   {"bom": 0.04, "ruim": 0.06, "alto": False, "txt": "≤ 4% bom · > 6% alerta"},
    "payback": {"bom": 6, "ruim": 12, "alto": False, "txt": "≤ 6 meses bom · > 12 alerta"},
    "ltvcac":  {"bom": 3, "ruim": 1.5, "alto": True, "txt": "≥ 3x bom · < 1,5x alerta"},
    "invol":   {"bom": 0.25, "ruim": 0.35, "alto": False, "txt": "≤ 25% bom · > 35% alerta"},
    "ativ":    {"bom": 0.85, "ruim": 0.7, "alto": True, "txt": "≥ 85% bom · < 70% alerta"},
    "nps":     {"bom": 30, "ruim": 0, "alto": True, "txt": "≥ 30 bom · < 0 alerta"},
}

# categorias de ticket digitadas de várias formas → categoria canônica
CATEGORIAS = {
    "acesso_login": "acesso_login", "acesso/login": "acesso_login", "login": "acesso_login", "acesso": "acesso_login",
    "pagamento": "pagamento", "pagto": "pagamento",
    "cobranca": "cobranca", "cobrança": "cobranca",
    "cancelamento": "cancelamento", "cancelar": "cancelamento",
    "conteudo": "conteudo", "conteúdo": "conteudo",
    "reproducao": "reproducao", "reprodução": "reproducao",
    "outros": "outros", "outro": "outros",
}


def conectar(dados: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for f in sorted(dados.glob("*.parquet")):
        con.execute(f"CREATE VIEW raw_{f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    return con


def limpar(con) -> list[dict]:
    """Cria as views limpas e devolve o registro de qualidade: o que foi encontrado e o que foi feito."""
    q = []

    def conta(nome: str, sql: str, acao: str, total_sql: str | None = None):
        n = con.execute(sql).fetchone()[0]
        tot = con.execute(total_sql).fetchone()[0] if total_sql else None
        q.append({"achado": nome, "linhas": int(n), "de": int(tot) if tot is not None else None, "tratamento": acao})

    cat_map = ", ".join(f"('{k}', '{v}')" for k, v in CATEGORIAS.items())

    conta("Timestamps em UTC: cadastros que caem no mês seguinte quando lidos em UTC",
          f"SELECT COUNT(*) FROM raw_contas WHERE date_trunc('month', criada_em) <> date_trunc('month', criada_em - {FUSO})",
          "Todo corte de mês usa o horário de Brasília (UTC−3).", "SELECT COUNT(*) FROM raw_contas")
    con.execute(f"""
        CREATE VIEW contas AS
        SELECT c.conta_id, ch.codigo AS canal, c.criada_em - {FUSO} AS criada_brt
        FROM raw_contas c JOIN raw_canais ch ON ch.canal_id = c.canal_aquisicao_id""")

    conta("Assinaturas encerradas antes de começar",
          "SELECT COUNT(*) FROM raw_assinaturas WHERE encerrada_em < iniciada_em",
          "Excluídas de estoque e fluxo.", "SELECT COUNT(*) FROM raw_assinaturas")
    conta("Assinaturas sem evento de criação ou reativação",
          """SELECT COUNT(*) FROM raw_assinaturas a WHERE NOT EXISTS (SELECT 1 FROM raw_assinatura_eventos e
             WHERE e.assinatura_id = a.assinatura_id AND e.tipo IN ('assinatura_criada', 'reativada'))""",
          "Mantidas: a tabela de assinaturas é a fonte do início; o evento faltante é falha do log.")
    con.execute(f"""
        CREATE VIEW assinaturas AS
        SELECT a.assinatura_id, a.conta_id, c.canal, a.plano_id AS plano_final, a.periodicidade, a.metodo_pagamento AS metodo,
               a.iniciada_em - {FUSO} AS ini, a.encerrada_em - {FUSO} AS enc, a.tipo_encerramento, a.assinatura_anterior_id
        FROM raw_assinaturas a JOIN contas c USING (conta_id)
        WHERE a.encerrada_em IS NULL OR a.encerrada_em >= a.iniciada_em""")

    # plano ao longo do tempo: segmentos entre upgrades/downgrades
    con.execute(f"""
        CREATE VIEW mudancas AS
        SELECT assinatura_id, ocorrido_em - {FUSO} AS t, plano_anterior_id, plano_novo_id,
               row_number() OVER (PARTITION BY assinatura_id ORDER BY ocorrido_em, evento_id) AS k
        FROM raw_assinatura_eventos WHERE tipo IN ('upgrade', 'downgrade') AND plano_novo_id IS NOT NULL""")
    con.execute("""
        CREATE VIEW segmentos AS
        WITH s0 AS (
            SELECT a.assinatura_id, a.ini AS de, COALESCE(m.plano_anterior_id, a.plano_final) AS plano_id, 0 AS k
            FROM assinaturas a LEFT JOIN mudancas m ON m.assinatura_id = a.assinatura_id AND m.k = 1),
        sk AS (SELECT assinatura_id, t AS de, plano_novo_id AS plano_id, k FROM mudancas),
        s AS (SELECT * FROM s0 UNION ALL SELECT * FROM sk)
        SELECT s.assinatura_id, s.plano_id, s.de,
               COALESCE(LEAD(s.de) OVER (PARTITION BY s.assinatura_id ORDER BY s.k), a.enc, TIMESTAMP '2100-01-01') AS ate
        FROM s JOIN assinaturas a USING (assinatura_id)""")

    conta("Faturas marcadas como pagas sem pagamento aprovado registrado",
          """SELECT COUNT(*) FROM raw_faturas f WHERE status = 'paga' AND NOT EXISTS
             (SELECT 1 FROM raw_pagamentos p WHERE p.fatura_id = f.fatura_id AND p.status = 'aprovado')""",
          "Contadas como receita (a fatura é o livro-razão); o pagamento faltante é falha do log de cobrança.",
          "SELECT COUNT(*) FROM raw_faturas WHERE status = 'paga'")
    con.execute(f"""
        CREATE VIEW faturas AS
        SELECT f.fatura_id, f.assinatura_id, a.canal, a.metodo, p.plano_id, a.periodicidade,
               f.emitida_em - {FUSO} AS emitida_brt, f.periodo_inicio, f.periodo_fim,
               f.valor_bruto, f.valor_desconto, f.valor_membro_extra, f.valor_total, f.status
        FROM raw_faturas f JOIN assinaturas a USING (assinatura_id) JOIN raw_precos p USING (preco_id)""")

    # reproduções: unidade, duração negativa e duplicatas
    rep_tot = "SELECT COUNT(*) FROM raw_reproducoes"
    ms = "versao_app LIKE '6.%' AND date_diff('second', inicio_em, fim_em) > 0 AND segundos_assistidos > 100 * date_diff('second', inicio_em, fim_em)"
    conta("Reproduções com tempo gravado em milissegundos (app 6.x, celular e tablet)", f"SELECT COUNT(*) FROM raw_reproducoes WHERE {ms}",
          "Divididas por 1.000: a razão contra a duração de relógio é exatamente 1.000×.", rep_tot)
    conta("Reproduções com duração negativa (fim antes do início)",
          "SELECT COUNT(*) FROM raw_reproducoes WHERE segundos_assistidos < 0 OR fim_em < inicio_em",
          "Excluídas do tempo assistido.", rep_tot)
    conta("Reproduções duplicadas (mesmo perfil, título e início)",
          "SELECT COUNT(*) - COUNT(DISTINCT (perfil_id, titulo_id, inicio_em)) FROM raw_reproducoes",
          "Uma cópia mantida.", rep_tot)
    con.execute(f"""
        CREATE VIEW reproducoes AS
        WITH r AS (
            SELECT perfil_id, titulo_id, inicio_em, versao_app,
                   CASE WHEN {ms} THEN segundos_assistidos / 1000.0 ELSE segundos_assistidos END AS seg,
                   row_number() OVER (PARTITION BY perfil_id, titulo_id, inicio_em ORDER BY reproducao_id) AS dup
            FROM raw_reproducoes WHERE segundos_assistidos >= 0 AND fim_em >= inicio_em)
        SELECT p.conta_id, r.inicio_em - {FUSO} AS ini, r.seg
        FROM r JOIN raw_perfis p USING (perfil_id) WHERE r.dup = 1""")
    conta("Tipos de dispositivo escritos de várias formas (Celular, mobile, smartphone, TABLET, 'tv ', navegador…)",
          "SELECT COUNT(*) FROM raw_dispositivos WHERE tipo NOT IN ('celular', 'tablet', 'tv', 'web')",
          "Registrado; nenhuma métrica deste relatório usa o tipo de dispositivo. Para usar: mapear para celular, tablet, tv e web.",
          "SELECT COUNT(*) FROM raw_dispositivos")

    conta("Categorias de ticket escritas de várias formas (cobrança, COBRANCA, pagto, Acesso/Login…)",
          f"""SELECT COUNT(*) FROM raw_tickets_suporte t
              WHERE categoria NOT IN (SELECT DISTINCT v FROM (VALUES {cat_map}) m(k, v))""",
          "Mapeadas para 7 categorias canônicas.", "SELECT COUNT(*) FROM raw_tickets_suporte")
    con.execute(f"""
        CREATE VIEW tickets AS
        SELECT t.conta_id, t.aberto_em - {FUSO} AS t, COALESCE(m.v, 'outros') AS categoria
        FROM raw_tickets_suporte t LEFT JOIN (VALUES {cat_map}) m(k, v) ON m.k = lower(trim(t.categoria))""")

    conta("Ferramenta de atribuição: cadastros creditados à busca paga acima dos cadastros reais do canal",
          """SELECT (SELECT SUM(cadastros_atribuidos) FROM raw_investimento_diario WHERE canal_id = 2)
                   - (SELECT COUNT(*) FROM raw_contas WHERE canal_aquisicao_id = 2)""",
          "CAC calculado com o canal gravado na conta; a atribuição aparece ao lado, só para comparação.",
          "SELECT COUNT(*) FROM raw_contas WHERE canal_aquisicao_id = 2")
    return q


def cubo(con) -> dict:
    """Cubo aditivo por mês × canal × plano × método, mais mídia por mês × canal e tabelas longas de motivos e tickets."""
    con.execute(f"""
        CREATE VIEW meses AS
        SELECT m::DATE AS mes, (m + INTERVAL 1 MONTH)::TIMESTAMP AS fim_excl
        FROM range(DATE '{INICIO}', DATE '{FIM}' + INTERVAL 1 DAY, INTERVAL 1 MONTH) t(m)""")
    con.execute("""CREATE VIEW plano_em AS
        SELECT s.assinatura_id, s.plano_id, s.de, s.ate, a.canal, a.metodo, a.conta_id FROM segmentos s JOIN assinaturas a USING (assinatura_id)""")
    blocos = {
        # estoque no fim do mês (assinatura e segmento de plano vigentes no último instante do mês)
        "ativos_fim": """SELECT m.mes, p.canal, p.plano_id, p.metodo, COUNT(*) AS v
            FROM meses m JOIN plano_em p ON p.de < m.fim_excl AND p.ate >= m.fim_excl GROUP BY ALL""",
        "novas": """SELECT date_trunc('month', a.ini)::DATE, a.canal, s.plano_id, a.metodo, COUNT(*)
            FROM assinaturas a JOIN segmentos s ON s.assinatura_id = a.assinatura_id AND s.de = a.ini
            WHERE a.assinatura_anterior_id IS NULL GROUP BY ALL""",
        "reativacoes": """SELECT date_trunc('month', a.ini)::DATE, a.canal, s.plano_id, a.metodo, COUNT(*)
            FROM assinaturas a JOIN segmentos s ON s.assinatura_id = a.assinatura_id AND s.de = a.ini
            WHERE a.assinatura_anterior_id IS NOT NULL GROUP BY ALL""",
        "enc_vol": """SELECT date_trunc('month', enc)::DATE, canal, plano_final, metodo, COUNT(*) FROM assinaturas
            WHERE tipo_encerramento = 'voluntario' GROUP BY ALL""",
        "enc_invol": """SELECT date_trunc('month', enc)::DATE, canal, plano_final, metodo, COUNT(*) FROM assinaturas
            WHERE tipo_encerramento = 'involuntario' GROUP BY ALL""",
        "upgrades": """SELECT date_trunc('month', m.t)::DATE, a.canal, m.plano_novo_id, a.metodo, COUNT(*)
            FROM mudancas m JOIN assinaturas a USING (assinatura_id) JOIN raw_planos pn ON pn.plano_id = m.plano_novo_id
            JOIN raw_planos pa ON pa.plano_id = m.plano_anterior_id WHERE m.plano_novo_id > m.plano_anterior_id GROUP BY ALL""",
        "downgrades": """SELECT date_trunc('month', m.t)::DATE, a.canal, m.plano_novo_id, a.metodo, COUNT(*)
            FROM mudancas m JOIN assinaturas a USING (assinatura_id) WHERE m.plano_novo_id < m.plano_anterior_id GROUP BY ALL""",
        # receita faturada e paga, no mês de emissão
        "receita": """SELECT date_trunc('month', emitida_brt)::DATE, canal, plano_id, metodo, SUM(valor_total)
            FROM faturas WHERE status = 'paga' AND plano_id IS NOT NULL GROUP BY ALL""",
        "descontos": """SELECT date_trunc('month', emitida_brt)::DATE, canal, plano_id, metodo, SUM(valor_desconto)
            FROM faturas WHERE status = 'paga' AND plano_id IS NOT NULL GROUP BY ALL""",
        "membro_extra": """SELECT date_trunc('month', emitida_brt)::DATE, canal, plano_id, metodo, SUM(valor_membro_extra)
            FROM faturas WHERE status = 'paga' AND plano_id IS NOT NULL GROUP BY ALL""",
        "estornos": """SELECT date_trunc('month', emitida_brt)::DATE, canal, plano_id, metodo, SUM(valor_total)
            FROM faturas WHERE status IN ('reembolsada', 'estornada') AND plano_id IS NOT NULL GROUP BY ALL""",
        # receita recorrente reconhecida no mês: mensal no mês do ciclo; anual dividida em 12 meses
        "mrr": """SELECT mes, canal, plano_id, metodo, SUM(v) FROM (
                SELECT date_trunc('month', periodo_inicio)::DATE AS mes, canal, plano_id, metodo, valor_total AS v
                FROM faturas WHERE status = 'paga' AND periodicidade = 'mensal' AND plano_id IS NOT NULL
                UNION ALL
                SELECT (date_trunc('month', periodo_inicio) + INTERVAL (i) MONTH)::DATE, canal, plano_id, metodo, valor_total / 12.0
                FROM faturas, range(12) r(i) WHERE status = 'paga' AND periodicidade = 'anual' AND plano_id IS NOT NULL)
            GROUP BY ALL""",
        "faturas_vencidas": """SELECT date_trunc('month', emitida_brt)::DATE, canal, plano_id, metodo, COUNT(*)
            FROM faturas WHERE status = 'vencida' AND plano_id IS NOT NULL GROUP BY ALL""",
        "cobrancas": f"""SELECT date_trunc('month', p.processado_em - {FUSO})::DATE, f.canal, f.plano_id, p.metodo, COUNT(*)
            FROM raw_pagamentos p JOIN faturas f USING (fatura_id) WHERE p.tipo = 'cobranca' AND f.plano_id IS NOT NULL GROUP BY ALL""",
        "cobrancas_falhas": f"""SELECT date_trunc('month', p.processado_em - {FUSO})::DATE, f.canal, f.plano_id, p.metodo, COUNT(*)
            FROM raw_pagamentos p JOIN faturas f USING (fatura_id)
            WHERE p.tipo = 'cobranca' AND p.status IN ('recusado', 'expirado') AND f.plano_id IS NOT NULL GROUP BY ALL""",
        # aquisição: coorte do mês de cadastro, pelo canal gravado na conta
        "cadastros": """SELECT date_trunc('month', c.criada_brt)::DATE, c.canal, s.plano_id, a.metodo, COUNT(*)
            FROM contas c JOIN assinaturas a ON a.conta_id = c.conta_id AND a.assinatura_anterior_id IS NULL
            JOIN segmentos s ON s.assinatura_id = a.assinatura_id AND s.de = a.ini GROUP BY ALL""",
        "pagantes_30d": """SELECT date_trunc('month', c.criada_brt)::DATE, c.canal, s.plano_id, a.metodo, COUNT(*)
            FROM contas c JOIN assinaturas a ON a.conta_id = c.conta_id AND a.assinatura_anterior_id IS NULL
            JOIN segmentos s ON s.assinatura_id = a.assinatura_id AND s.de = a.ini
            WHERE EXISTS (SELECT 1 FROM faturas f WHERE f.assinatura_id = a.assinatura_id AND f.status IN ('paga', 'reembolsada', 'estornada')
                          AND f.emitida_brt < c.criada_brt + INTERVAL 30 DAY) GROUP BY ALL""",
        # uso: horas assistidas e contas que assistiram, pelo plano vigente no início da reprodução
        "horas": """SELECT date_trunc('month', r.ini)::DATE, p.canal, p.plano_id, p.metodo, SUM(r.seg) / 3600.0
            FROM reproducoes r JOIN plano_em p ON p.conta_id = r.conta_id AND r.ini >= p.de AND r.ini < p.ate GROUP BY ALL""",
        "contas_assistiram": """SELECT mes, canal, plano_id, metodo, COUNT(*) FROM (
                SELECT DISTINCT date_trunc('month', r.ini)::DATE AS mes, p.canal, p.plano_id, p.metodo, r.conta_id
                FROM reproducoes r JOIN plano_em p ON p.conta_id = r.conta_id AND r.ini >= p.de AND r.ini < p.ate) GROUP BY ALL""",
        "nps_promotores": f"""SELECT date_trunc('month', n.respondida_em - {FUSO})::DATE, p.canal, p.plano_id, p.metodo, COUNT(*)
            FROM raw_nps n JOIN plano_em p ON p.conta_id = n.conta_id AND n.respondida_em - {FUSO} >= p.de AND n.respondida_em - {FUSO} < p.ate
            WHERE n.nota >= 9 GROUP BY ALL""",
        "nps_detratores": f"""SELECT date_trunc('month', n.respondida_em - {FUSO})::DATE, p.canal, p.plano_id, p.metodo, COUNT(*)
            FROM raw_nps n JOIN plano_em p ON p.conta_id = n.conta_id AND n.respondida_em - {FUSO} >= p.de AND n.respondida_em - {FUSO} < p.ate
            WHERE n.nota <= 6 GROUP BY ALL""",
        "nps_respostas": f"""SELECT date_trunc('month', n.respondida_em - {FUSO})::DATE, p.canal, p.plano_id, p.metodo, COUNT(*)
            FROM raw_nps n JOIN plano_em p ON p.conta_id = n.conta_id AND n.respondida_em - {FUSO} >= p.de AND n.respondida_em - {FUSO} < p.ate
            GROUP BY ALL""",
        "tickets": """SELECT date_trunc('month', t.t)::DATE, p.canal, p.plano_id, p.metodo, COUNT(*)
            FROM tickets t JOIN plano_em p ON p.conta_id = t.conta_id AND t.t >= p.de AND t.t < p.ate GROUP BY ALL""",
    }
    linhas: dict[tuple, dict] = {}
    for medida, sql in blocos.items():
        for mes, canal, plano, metodo, v in con.execute(sql).fetchall():
            if mes is None or str(mes) < INICIO or str(mes) > FIM:
                continue
            k = (str(mes)[:7], canal, int(plano), metodo)
            linhas.setdefault(k, {})[medida] = float(v or 0)
    # ativos no início = ativos no fim do mês anterior (mesma célula)
    for (mes, canal, plano, metodo), d in list(linhas.items()):
        y, m = int(mes[:4]), int(mes[5:])
        prox = f"{y + (m == 12)}-{1 if m == 12 else m + 1:02d}"
        if prox <= FIM[:7]:
            linhas.setdefault((prox, canal, plano, metodo), {})["ativos_ini"] = d.get("ativos_fim", 0.0)

    midia = con.execute("""
        SELECT strftime(i.data, '%Y-%m'), c.codigo, SUM(i.investimento_brl), SUM(i.impressoes), SUM(i.cliques), SUM(i.cadastros_atribuidos)
        FROM raw_investimento_diario i JOIN raw_canais c USING (canal_id) GROUP BY ALL ORDER BY 1, 2""").fetchall()
    motivos = con.execute(f"""
        SELECT strftime(r.respondida_em - {FUSO}, '%Y-%m'), a.canal, a.plano_final, a.metodo, r.motivo_principal, COUNT(*)
        FROM raw_pesquisa_cancelamento r JOIN assinaturas a USING (assinatura_id) GROUP BY ALL""").fetchall()
    tickets = con.execute("""
        SELECT strftime(t.t, '%Y-%m'), p.canal, p.plano_id, p.metodo, t.categoria, COUNT(*)
        FROM tickets t JOIN plano_em p ON p.conta_id = t.conta_id AND t.t >= p.de AND t.t < p.ate GROUP BY ALL""").fetchall()

    medidas = sorted({m for d in linhas.values() for m in d})
    chaves = sorted(linhas)
    meses = [r[0] for r in con.execute("SELECT strftime(mes, '%Y-%m') FROM meses ORDER BY 1").fetchall()]
    canais = con.execute("SELECT codigo, nome, pago FROM raw_canais ORDER BY canal_id").fetchall()
    planos = con.execute("SELECT plano_id, nome FROM raw_planos ORDER BY plano_id").fetchall()
    reajustes = [str(r[0]) for r in con.execute(
        "SELECT DISTINCT vigencia_inicio FROM raw_precos WHERE item = 'assinatura' AND vigencia_inicio > DATE '2023-10-01' ORDER BY 1").fetchall()]
    return {
        "meses": meses,
        "canais": [{"codigo": c, "nome": n, "pago": bool(p)} for c, n, p in canais],
        "planos": [{"id": int(i), "nome": n} for i, n in planos],
        "metodos": sorted({k[3] for k in chaves}),
        "medidas": medidas,
        "cubo": {"chaves": [list(k) for k in chaves],
                 "valores": [[round(linhas[k].get(m, 0.0), 2) for m in medidas] for k in chaves]},
        "midia": [[r[0], r[1], round(r[2] or 0, 2), int(r[3] or 0), int(r[4] or 0), int(r[5] or 0)] for r in midia],
        "motivos": [[r[0], r[1], int(r[2]), r[3], r[4], int(r[5])] for r in motivos if r[0] and r[0] <= FIM[:7]],
        "tickets": [[r[0], r[1], int(r[2]), r[3], r[4], int(r[5])] for r in tickets if r[0] and r[0] <= FIM[:7]],
        "eventos": [{"mes": d[:7], "rotulo": f"reajuste de preço ({d[8:10]}/{d[5:7]})"} for d in reajustes]
                   + [{"mes": "2024-04", "rotulo": "fim do trial de 7 dias (31/03)"},
                      {"mes": "2025-03", "rotulo": "cobrança de membro extra (10/03)"}],
    }


def reconciliar(con, dados: dict) -> list[str]:
    """Confere o cubo contra as tabelas brutas; qualquer divergência interrompe o build."""
    M, V = dados["medidas"], dados["cubo"]["valores"]
    tot = {m: sum(v[i] for v in V) for i, m in enumerate(M)}
    ultimo = dados["meses"][-1]
    ativos_fim = sum(v[M.index("ativos_fim")] for k, v in zip(dados["cubo"]["chaves"], V, strict=True) if k[0] == ultimo)
    checks = {
        "receita paga = soma das faturas pagas": (tot["receita"], con.execute(
            "SELECT SUM(f.valor_total) FROM raw_faturas f JOIN assinaturas a USING (assinatura_id) WHERE f.status = 'paga'").fetchone()[0]),
        "cadastros = contas com 1ª assinatura válida": (tot["cadastros"], con.execute(
            "SELECT COUNT(*) FROM assinaturas WHERE assinatura_anterior_id IS NULL").fetchone()[0]),
        "assinantes ativos no último mês = assinaturas não encerradas": (ativos_fim, con.execute(
            "SELECT COUNT(*) FROM assinaturas WHERE enc IS NULL").fetchone()[0]),
        "encerramentos = assinaturas encerradas": (tot["enc_vol"] + tot["enc_invol"], con.execute(
            f"SELECT COUNT(*) FROM assinaturas WHERE enc IS NOT NULL AND enc < TIMESTAMP '{FIM}' + INTERVAL 1 DAY").fetchone()[0]),
        "investimento = soma do investimento diário": (sum(r[2] for r in dados["midia"]), con.execute(
            "SELECT SUM(investimento_brl) FROM raw_investimento_diario").fetchone()[0]),
    }
    erros = [f"{k}: cubo {a:,.2f} vs bruto {b:,.2f}" for k, (a, b) in checks.items() if abs(a - b) > 0.5]
    if erros:
        raise SystemExit("reconciliação falhou:\n  " + "\n  ".join(erros))
    return list(checks)


def main() -> None:
    ap = argparse.ArgumentParser()
    padrao = RAIZ / "dados_medium" / "parquet"
    ap.add_argument("--dados", type=Path, default=padrao if padrao.exists() else RAIZ / "dados" / "parquet")
    args = ap.parse_args()
    con = conectar(args.dados)
    qualidade = limpar(con)
    dados = cubo(con)
    n_contas = con.execute("SELECT COUNT(*) FROM raw_contas").fetchone()[0]
    dados["meta"] = {"fonte": args.dados.parent.name, "contas": int(n_contas), "gerado_em": date.today().isoformat(),
                     "inicio": INICIO, "fim": FIM}
    dados["qualidade"] = qualidade
    dados["referencias"] = REFERENCIAS
    dados["reconciliacao"] = reconciliar(con, dados)
    SAIDA_HTML.parent.mkdir(parents=True, exist_ok=True)
    simbolo = (Path(__file__).resolve().parent / "simbolo.svg").read_text(encoding="utf-8").replace('aria-label="ABADE symbol"', 'aria-label="ABADE"')
    html = (MODELO.read_text(encoding="utf-8").replace("<!--__SIMBOLO__-->", simbolo)
            .replace("/*__DADOS__*/null", json.dumps(dados, ensure_ascii=False, separators=(",", ":"))))
    SAIDA_HTML.write_text(html, encoding="utf-8")
    (RAIZ / "docs" / ".nojekyll").write_text("", encoding="utf-8")
    from relatorio_md import escrever  # noqa: PLC0415 (mesmo diretório)
    SAIDA_MD.write_text(escrever(dados), encoding="utf-8")
    print(f"{SAIDA_HTML.relative_to(RAIZ)} ({SAIDA_HTML.stat().st_size / 1024:,.0f} KB) · {SAIDA_MD.relative_to(RAIZ)} · "
          f"{len(dados['cubo']['chaves']):,} células · fonte {args.dados}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
