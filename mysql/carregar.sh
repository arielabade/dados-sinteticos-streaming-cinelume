#!/usr/bin/env bash
# Carrega os CSV gzip de /dados/csv no banco cinelume (MySQL 8).
# Variáveis: MYSQL_HOST, MYSQL_PWD, FK_CHECKS (1 = valida chaves estrangeiras durante a carga).
set -euo pipefail
HOST=${MYSQL_HOST:-127.0.0.1}
DIR=${CSV_DIR:-/dados/csv}
FK=${FK_CHECKS:-1}
MYSQL=(mysql -h "$HOST" -uroot --local-infile=1 cinelume)

# ordem respeitando as chaves estrangeiras
TABELAS="canais investimento_diario planos precos generos estudios pessoas titulos titulo_generos
titulo_elenco episodios catalogo_disponibilidade contas perfis dispositivos assinaturas
assinatura_eventos cupons cupom_resgates faturas pagamentos pesquisa_cancelamento
sessoes_app eventos_app reproducoes heartbeats_reproducao notificacoes tickets_suporte nps"

for t in $TABELAS; do
  arq="$DIR/$t.csv.gz"
  [ -f "$arq" ] || { echo "faltando: $arq" >&2; exit 1; }
  cab=$(set +o pipefail; gzip -dc "$arq" 2>/dev/null | head -1 | tr -d '"\r')
  vars=""; sets=""
  IFS=',' read -ra cols <<< "$cab"
  for c in "${cols[@]}"; do
    vars+="@$c,"
    sets+="\`$c\` = NULLIF(@$c, ''),"
  done
  vars=${vars%,}; sets=${sets%,}
  fifo=$(mktemp -u /tmp/carga_XXXX); mkfifo "$fifo"
  gzip -dc "$arq" > "$fifo" &
  inicio=$(date +%s)
  "${MYSQL[@]}" -e "SET SESSION foreign_key_checks=0; TRUNCATE TABLE \`$t\`;
    SET SESSION foreign_key_checks=$FK;
    LOAD DATA LOCAL INFILE '$fifo' INTO TABLE \`$t\` CHARACTER SET utf8mb4
      FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' ESCAPED BY ''
      LINES TERMINATED BY '\n' IGNORE 1 LINES ($vars) SET $sets;
    SHOW WARNINGS LIMIT 5;"
  wait
  rm -f "$fifo"
  n=$("${MYSQL[@]}" -N -e "SELECT COUNT(*) FROM \`$t\`")
  esperado=$(( $(gzip -dc "$arq" | wc -l) - 1 ))
  echo "$(date +%T) $t: $n linhas ($(( $(date +%s) - inicio ))s)"
  if [ "$n" != "$esperado" ]; then
    echo "ERRO: $t tem $esperado linhas no CSV e $n no banco" >&2; exit 2
  fi
done
echo "carga concluída"
