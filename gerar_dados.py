#!/usr/bin/env python3
"""Gera o banco sintético da Cinelume (streaming fictício) em Parquet e CSV gzip.

Uso:
    python gerar_dados.py --scale small|medium|full [--seed N] [--saida dados]

Atenção: este código é o processo gerador dos dados. Lê-lo revela os padrões
embutidos — se o objetivo é explorar os dados às cegas, não leia o pacote `gerador/`.
"""
import argparse
import json
import os
import shutil
import time

import numpy as np
from faker import Faker

from gerador.catalogo import gerar_catalogo, tabelas_catalogo
from gerador.config import ESCALAS, FIM, INICIO, NDIAS, SEED_PADRAO, calendario
from gerador.contas import gerar_contas, gerar_perfis_dispositivos
from gerador.expansao import Expansor
from gerador.saida import Tabela, gravar
from gerador.simulacao import simular
from gerador.tabelas import investimento_diario, tabelas_basicas, tabelas_negocio

LOGS = ["sessoes_app", "eventos_app", "reproducoes", "heartbeats_reproducao"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", choices=list(ESCALAS), default="small")
    ap.add_argument("--seed", type=int, default=SEED_PADRAO)
    ap.add_argument("--saida", default="dados")
    ap.add_argument("--gabarito", default="_gabarito", help="pasta onde ficam métricas internas da geração")
    args = ap.parse_args()

    t0 = time.time()
    log = lambda msg: print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)
    base = args.saida
    for sub in ("parquet", "csv"):
        shutil.rmtree(os.path.join(base, sub), ignore_errors=True)
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    os.makedirs(args.gabarito, exist_ok=True)

    seed = args.seed
    rng = lambda k: np.random.default_rng([seed, k])
    Faker.seed(seed)
    fake = Faker("pt_BR")
    n_contas = ESCALAS[args.scale]["contas"]
    log(f"escala={args.scale} contas≈{n_contas} seed={seed} período={INICIO}..{FIM} ({NDIAS} dias)")

    cal = calendario()
    cat = gerar_catalogo(rng(1), fake)
    log(f"catálogo: {cat['N']} títulos, {len(cat['ep'])} episódios")
    ct = gerar_contas(rng(2), fake, n_contas, cal)
    pf, dv = gerar_perfis_dispositivos(rng(3), fake, ct, cat)
    log(f"contas={ct['n']} perfis={pf['P']} dispositivos={dv['D']}")

    sim = simular(rng(4), cal, cat, ct, pf, dv, log=log)
    log(f"simulação concluída: {sim['ns']} assinaturas")

    contagem = {}
    for nome, cols in {**tabelas_basicas(sim), **tabelas_catalogo(cat, rng(5))}.items():
        contagem[nome] = gravar(base, nome, cols)
    contagem["investimento_diario"] = gravar(base, "investimento_diario", investimento_diario(ct))
    contagem["contas"] = gravar(base, "contas", ct["tabela"])
    contagem["dispositivos"] = gravar(base, "dispositivos", dv["tabela"])
    neg, stats = tabelas_negocio(rng(6), sim, ct, pf, dv)
    for nome, cols in neg.items():
        contagem[nome] = gravar(base, nome, cols)
    log("tabelas de negócio gravadas")

    saidas = {n: Tabela(base, n) for n in LOGS}
    exp = Expansor(seed, cat, ct, pf, dv, sim, saidas, stats, log=log)
    meses = np.array([d.year * 12 + d.month for d in cal["datas"]])
    limites = np.r_[0, np.where(np.diff(meses))[0] + 1, NDIAS]
    for k in range(len(limites) - 1):
        d0, d1 = int(limites[k]), int(limites[k + 1])
        npl, nss, nhb = exp.processar(k, d0, d1)
        if k % 6 == 0 or k == len(limites) - 2:
            log(f"  logs {cal['datas'][d0]}: reproduções={npl} sessões={nss} heartbeats={nhb}")
    for n, t in saidas.items():
        contagem[n] = t.fechar()
    log("logs gravados")

    _metricas_internas(args, ct, pf, dv, sim, stats, contagem)
    log("contagem de linhas:")
    for n in sorted(contagem):
        print(f"    {n:28s} {contagem[n]:>12,d}")
    log("fim")


def _metricas_internas(args, ct, pf, dv, sim, stats, contagem):
    """Grava, apenas na pasta do gabarito, contagens e latentes usados na verificação interna."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    g = args.gabarito
    stats = {k: int(v) if isinstance(v, (int, np.integer)) else v for k, v in stats.items()}
    esp = ct["especial"]
    stats.update(
        contas=int(ct["n"]), perfis=int(pf["P"]), funcionarios=int((esp == 1).sum()), contas_teste=int((esp == 2).sum()),
        bots=int((esp == 3).sum()), extremos=int(ct["extremo"].sum()), compartilhadas=int(ct["compartilha"].sum()),
        dispositivos_relogio_errado=int((dv["relogio"] != 0).sum()), dispositivos=int(dv["D"]),
        contas_uf_variante=int(sum(1 for u in ct["tabela"]["uf"] if len(u) != 2 or u != u.upper())),
        sh_status={str(k): int(v) for k, v in zip(*np.unique(sim["sh_status"][ct["compartilha"]], return_counts=True))},
        linhas=contagem)
    with open(os.path.join(g, f"metricas_{args.scale}.json"), "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    lat = pa.table(dict(
        conta_id=np.arange(1, ct["n"] + 1), eng_mu=ct["eng_mu"], drift=ct["drift"], sens_preco=ct["ps"],
        conexao=ct["conn"], risco_pag=ct["risco_pag"], esquecido=ct["esquecido"], compartilha=ct["compartilha"],
        especial=esp, extremo=ct["extremo"], eng_final=sim["eng_final"]))
    pq.write_table(lat, os.path.join(g, f"latentes_{args.scale}.parquet"))
    ch = sim["churn"]
    pq.write_table(pa.table(dict(conta_id=ch["conta"] + 1, dia=ch["dia"], tipo=ch["tipo"])),
                   os.path.join(g, f"fins_{args.scale}.parquet"))
    cz = sim["causas"]
    pq.write_table(pa.table(dict(conta_id=cz["conta"] + 1, dia=cz["dia"], causa=cz["causa"])),
                   os.path.join(g, f"causas_cancelamento_{args.scale}.parquet"))


if __name__ == "__main__":
    main()
