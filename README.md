# Cinelume — dados sintéticos de um streaming por assinatura

A **Cinelume** é um serviço brasileiro de streaming por assinatura **fictício**, no estilo das grandes plataformas, porém menor. Este repositório gera o banco de dados completo da empresa entre **outubro de 2023 e outubro de 2026**:

- cadastro, assinatura e cobrança;
- catálogo de filmes e séries;
- logs de uso do app;
- marketing e atendimento.

O objetivo é praticar exploração de dados e machine learning (churn, LTV, CAC, recomendação, detecção de anomalias…) em dados com cara de produção.

> ⚠️ **Os dados contêm, de propósito, padrões, relações causais, pistas falsas, imperfeições e outliers que não estão documentados.** A documentação descreve o banco como ele foi *projetado*; descobrir onde o dado real se afasta do projeto faz parte do exercício.
>
> O gabarito fica em `_gabarito/` — **não abra antes de explorar.** O código do gerador (`gerador/`) também revela os padrões: trate-o como gabarito.

Tudo é inventado: títulos, estúdios, elenco, marcas, pessoas, e-mails (domínios `example`), CPFs, telefones, endereços e IPs. Os dados pessoais foram gerados do zero com Faker `pt_BR`.

## Conteúdo

| Caminho | O que é |
|---|---|
| `gerar_dados.py` | Gera os dados (Parquet + CSV gzip). |
| `gerador/` | Pacote com o processo gerador. |
| `schema.sql` | DDL MySQL 8: 29 tabelas, PKs, FKs, índices e constraints. |
| `docker-compose.yml`, `mysql/carregar.sh` | Sobe o MySQL 8 e carrega os CSV. |
| `docs/visao_geral.md` | Domínios, ligações entre tabelas e jornada de uma conta. |
| `docs/diagrama_er.md` | Diagrama ER (Mermaid). |
| `docs/dicionario_de_dados.md` | Dicionário de dados completo. |
| `docs/eventos_app.md` | Catálogo de eventos do app. |
| `dados/parquet/` | Um Parquet por tabela (formato principal para análise e ML). Gerado; fora do git. |
| `dados/csv/` | Um CSV gzip por tabela (usado na carga do MySQL). Gerado; fora do git. |
| `_gabarito/` | Gabarito e métricas internas. **Não abra antes de explorar.** Fora do git. |
| `relatorio/` | Gera o relatório gerencial (cubo mensal em DuckDB → HTML estilo Power BI + Markdown). |
| `docs/relatorio/index.html` | O relatório interativo, publicado no GitHub Pages. **Revela padrões dos dados.** |
| `docs/RELATORIO.md` | A leitura escrita do relatório. **Revela padrões dos dados.** |

## Relatório gerencial

> ⚠️ **Spoiler.** O relatório mostra padrões e imperfeições que este banco esconde de propósito. Se a ideia é praticar a
> exploração, leia depois de explorar.

**[Abrir o relatório interativo](https://arielabade.github.io/dados-sinteticos-streaming-cinelume/relatorio/)** ·
[leitura escrita](docs/RELATORIO.md)

Um relatório estilo Power BI num único arquivo HTML, sem servidor:

- **navegador de meses:** clique num mês, em dois meses com "Selecionar intervalo" (ou Shift+clique), use os atalhos
  (último mês, 3, 6 e 12 meses, ano atual, tudo) ou as setas para deslizar o período;
- **comparação** com o período anterior de mesmo tamanho ou com o mesmo período do ano anterior;
- **filtros** de canal, plano e método de pagamento, que recalculam tudo;
- **páginas:** visão geral, aquisição, receita, retenção, uso e atendimento, qualidade dos dados e método.

Os títulos dos gráficos dizem a conclusão e mudam com o período. Toda taxa é razão de somas, e um número sobre poucos eventos
aparece em cinza, sem virar destaque. Antes de virar métrica, cada imperfeição encontrada nos dados (fuso UTC, milissegundos no
app 6.x, distorção da ferramenta de atribuição, faturas pagas sem pagamento, categorias sujas…) é contada e tratada. O build
confere o resultado contra as tabelas brutas e para se algo divergir.

Para regerar (o relatório publicado usa a escala `medium`):

```bash
pip install numpy pandas pyarrow faker duckdb
python gerar_dados.py --scale medium --saida dados_medium
python relatorio/build.py            # usa dados_medium/ se existir; senão dados/
```

## Como gerar

Requisitos: Python 3.10+ com `numpy`, `pandas`, `pyarrow` e `faker`.

```bash
pip install numpy pandas pyarrow faker
python gerar_dados.py --scale small     # ≈6 mil contas,   ~1 min,   ~0,3 GB
python gerar_dados.py --scale medium    # ≈30 mil contas,  ~5 min,   ~1,7 GB
python gerar_dados.py --scale full      # ≈120 mil contas, ~20+ min, ~7 GB
```

Opções:
- `--seed N`: semente. O padrão é fixo, e a mesma semente gera exatamente os mesmos dados.
- `--saida DIR`: pasta de saída (padrão `dados`).

Cada execução apaga e recria `dados/parquet` e `dados/csv`.

Volume aproximado na escala `full`:

| Tabela | Linhas |
|---|---|
| `contas` | 120 mil |
| `perfis` | 300 mil |
| `titulos` / `episodios` | 3 mil / 25 mil |
| `reproducoes` | ~21 milhões |
| `eventos_app` | ~110 milhões |

As escalas menores mantêm o catálogo inteiro e reduzem contas e logs na mesma proporção.

## Como subir o MySQL

Requisitos: Docker com Compose v2.

```bash
docker compose up -d mysql                 # cria o banco `cinelume` com o schema.sql
docker compose --profile carga run --rm carga   # carrega dados/csv/*.csv.gz
```

- **Conexão:** `localhost:3307`, usuário `root`, senha `cinelume` (variáveis `MYSQL_PORT` e `MYSQL_ROOT_PASSWORD`).
- **Validação na carga:** o script compara a contagem de cada tabela com o CSV e falha se alguma linha for rejeitada.
- **Chaves estrangeiras:** são validadas durante a carga (`FK_CHECKS=1`). Para acelerar a escala `full`, use `FK_CHECKS=0 docker compose --profile carga run --rm carga`.
- **Tempo de carga:** a `small` leva cerca de 5 minutos; a `full` pode levar horas. Aumente a memória do InnoDB com `MYSQL_BUFFER_POOL=4G`.
- **Recomeçar do zero:** `docker compose down -v` apaga o volume do banco.

## Como ler os Parquet

```python
import pandas as pd

contas = pd.read_parquet("dados/parquet/contas.parquet")
repro = pd.read_parquet(
    "dados/parquet/reproducoes.parquet",
    columns=["perfil_id", "titulo_id", "inicio_em", "segundos_assistidos"],
)
```

Para as tabelas grandes da escala `full`, prefira ler só as colunas necessárias ou usar ferramentas que leem o arquivo de forma preguiçosa:

```python
import duckdb
duckdb.sql("""
    SELECT date_trunc('month', inicio_em) AS mes, count(*) AS reproducoes
    FROM 'dados/parquet/reproducoes.parquet'
    GROUP BY 1 ORDER BY 1
""")

import polars as pl
eventos = pl.scan_parquet("dados/parquet/eventos_app.parquet")
```

Timestamps vêm como `timestamp[s]` sem fuso, em UTC. Flags são inteiros 0/1. Valores monetários são `double` em BRL.

## Contexto do negócio

- **Planos:** Básico com anúncios, Padrão e Premium; mensal ou anual. Os preços em BRL tiveram reajustes em 01/08/2024 e 01/09/2025.
- **Pagamento:**
  - cartão: renovação automática, com retentativas em caso de recusa;
  - Pix e boleto: pagamento manual a cada ciclo.
- **Promoções:**
  - trial de 7 dias para cadastros até 31/03/2024, depois descontinuado;
  - cupons de Black Friday e de férias (primeiro mês);
  - cupons de parceria com operadora, de indicação e de reconquista.
- **Contas:**
  - até 5 perfis por conta, usados em TV, celular, web e tablet;
  - desde 10/03/2025, os planos Padrão e Premium cobram por **membro extra** (perfil usado fora do domicílio).
- **Aquisição:** canais orgânico, busca paga, social pago, indicação, parceria com operadora e TV. O investimento diário por canal está em `investimento_diario`, para cálculo de CAC.
