#!/bin/bash
set -euo pipefail
export MYSQL_PWD="${STARROCKS_PASSWORD:?Required}"
[[ "$STARROCKS_PASSWORD" =~ ^[a-zA-Z0-9]{32,}$ ]] || exit 1

mkdir -p /persist/fe /persist/be
sed -i 's/-Xmx8192m/-Xmx1024m/' "$SR_HOME/fe/conf/fe.conf"
printf '\nmeta_dir = /persist/fe\n' >> "$SR_HOME/fe/conf/fe.conf"
printf '\nstorage_root_path = /persist/be\nmem_limit = 2G\n' >> "$SR_HOME/be/conf/be.conf"
sed -i '2a while [ ! -f /run/fluxyz-ready ]; do sleep 1; done' "$SR_HOME/director/run.sh"

(
  for attempt in $(seq 1 120); do
    if MYSQL_PWD='' mysql -h 127.0.0.1 -P 9030 -u root -e 'SELECT 1' >/dev/null 2>&1; then
      MYSQL_PWD='' mysql -h 127.0.0.1 -P 9030 -u root \
        -e "SET PASSWORD FOR 'root' = PASSWORD('${STARROCKS_PASSWORD:?Required}');"
      touch /run/fluxyz-ready
      exit 0
    fi
    if MYSQL_PWD="$STARROCKS_PASSWORD" mysql -h 127.0.0.1 -P 9030 -u root \
      -e 'SELECT 1' >/dev/null 2>&1; then
      touch /run/fluxyz-ready
      exit 0
    fi
    sleep 2
  done
  echo 'StarRocks password initialization did not complete' >&2
) &

exec /data/deploy/entrypoint.sh
