#!/usr/bin/env bash
# The project's stack without Docker and without root, for a shared
# machine or one you cannot install on (docs/onboarding/shared-box.md):
#
#   tools/native-dev.sh ports    your ports, from your user ID
#   tools/native-dev.sh init     once: the database, its logins, the
#                                services' packages
#   tools/native-dev.sh start    PostgreSQL, the migrations, the mock
#                                sign-in, the services, nginx
#   tools/native-dev.sh status   each process, and each service's health
#   tools/native-dev.sh stop     all of it
#
# The same pieces as the dev stack, as programs of yours: nginx with the
# box's servers on 127.0.0.1, each service on its own port, the mock
# sign-in, PostgreSQL with the project's database. Everything listens on
# 127.0.0.1, and everything it writes is in dev/out/native/.
#
# Needs on PATH: python3, node and npm, PostgreSQL's initdb, pg_ctl and
# psql, nginx, dbmate, curl. DEV_DB_PASSWORD, your own, at init and at
# start. DEV_BASE_PORT to choose your ports; else from your user ID.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
OUT=dev/out/native
ABS=$PWD/$OUT
VENV=$OUT/venv
base=${DEV_BASE_PORT:-$(( 20000 + ($(id -u) % 400) * 100 ))}

say() { echo "native-dev: $*"; }
die() { echo "native-dev: $*" >&2; exit 1; }
need() { for c in "$@"; do command -v "$c" > /dev/null || die "no $c on PATH (docs/onboarding/shared-box.md, §3)"; done; }
password() { [ -n "${DEV_DB_PASSWORD:-}" ] || die "DEV_DB_PASSWORD unset: export DEV_DB_PASSWORD=<your own, 8 or more letters and digits>"; }

render() {
  DEV_BASE_PORT=$base python3 box/render.py --native > /dev/null
  chmod 0600 "$OUT/env.sh" "$OUT/db-users.sql"
  # shellcheck source=/dev/null
  . "$OUT/env.sh"
}

units() { python3 -c 'import json; [print(s["name"], s["language"]) for s in json.load(open("box/project.json"))["services"]]'; }
database() { python3 -c 'import json; print(str(json.load(open("box/project.json")).get("database", False)).lower())'; }
port_of() { local v="PORT_$(echo "$1" | tr 'a-z-' 'A-Z_')"; echo "${!v}"; }

pg_start() {
  pg_ctl status -D "$OUT/pg" > /dev/null 2>&1 && return 0
  pg_ctl -s -w -D "$OUT/pg" -l "$OUT/pg.log" \
    -o "-p $PG_PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=" start
}

# A program in the background, its output to a log, its ID to a file
spawn() {
  local name=$1; shift
  nohup "$@" > "$OUT/$name.log" 2>&1 &
  echo $! > "$OUT/$name.pid"
}

alive() { [ -f "$OUT/$1.pid" ] && kill -0 "$(cat "$OUT/$1.pid")" 2> /dev/null; }

case ${1:-} in
ports)
  render
  say "base $base; set DEV_BASE_PORT to choose another"
  sed -n 's/^export \(.*_PORT[A-Z_]*\)=\(.*\)$/  \1 \2/p; s/^export \(PORT_[A-Z_]*\)=\(.*\)$/  \1 \2/p' "$OUT/env.sh"
  ;;

init)
  need python3 node npm initdb pg_ctl psql
  password
  render
  if [ "$(database)" = true ] && [ ! -d "$OUT/pg" ]; then
    pw=$(umask 077; mktemp "$OUT/.pw.XXXXXX")
    printf '%s\n' "$DEV_DB_PASSWORD" > "$pw"
    initdb -D "$OUT/pg" -U postgres --auth=scram-sha-256 --pwfile="$pw" > "$OUT/initdb.log"
    rm -f "$pw"
    say "PostgreSQL's data in $OUT/pg"
  fi
  if [ "$(database)" = true ]; then
    pg_start
    PGPASSWORD=$DEV_DB_PASSWORD psql -q -h 127.0.0.1 -p "$PG_PORT" -U postgres -v ON_ERROR_STOP=1 -f "$OUT/db-users.sql"
    pg_ctl -s -D "$OUT/pg" stop
    say "the database $PROJECT, and its logins ${PROJECT}_migrator and $PROJECT"
  fi
  [ -d "$VENV" ] || python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r dev/mock-auth/requirements.txt
  while read -r name lang; do
    case $lang in
      node) (cd "services/$name" && npm ci --no-audit --no-fund --silent) ;;
      python) "$VENV/bin/pip" install -q -r "services/$name/requirements.txt" ;;
    esac
    say "$name's packages, $lang"
  done < <(units)
  say "ready: tools/native-dev.sh start"
  ;;

start)
  need python3 node pg_ctl nginx curl
  password
  render
  mkdir -p "$OUT/tmp"
  if [ "$(database)" = true ]; then
    need dbmate
    [ -d "$OUT/pg" ] || die "no database yet: tools/native-dev.sh init"
    pg_start
    dbmate --url "$MIGRATOR_URL" -d migrations/sql --no-dump-schema up | grep -v '^$' || true
  fi
  alive mock-auth || BIND=127.0.0.1 PORT=$MOCK_PORT ISSUER=$COGNITO_ISSUER \
    ORIGINS="http://localhost:$UI_PORT,http://localhost:5173" \
    spawn mock-auth "$VENV/bin/python" dev/mock-auth/server.py
  while read -r name lang; do
    alive "$name" && continue
    p=$(port_of "$name")
    case $lang in
      node) SERVICE=$name HOST=127.0.0.1 PORT=$p spawn "$name" node "services/$name/server.js" ;;
      python) SERVICE=$name spawn "$name" "$VENV/bin/uvicorn" main:app --app-dir "services/$name" \
          --host 127.0.0.1 --port "$p" --workers 1 --no-server-header ;;
    esac
  done < <(units)
  if [ -f "$OUT/nginx.pid" ] && kill -0 "$(cat "$OUT/nginx.pid")" 2> /dev/null; then
    nginx -p "$ABS" -e "$ABS/nginx-error.log" -c "$ABS/nginx.conf" -s reload
  else
    nginx -p "$ABS" -e "$ABS/nginx-error.log" -c "$ABS/nginx.conf"
  fi
  for i in $(seq 20); do
    ok=1
    while read -r name _; do
      curl -sf -o /dev/null "http://$name.localhost:$NGINX_PORT/health" || ok=0
    done < <(units)
    [ $ok = 1 ] && break
    sleep 1
  done
  [ $ok = 1 ] || die "a service is not answering; tools/native-dev.sh status, and $OUT/*.log"
  say "up. Through nginx: http://<service>.localhost:$NGINX_PORT; the mock sign-in, http://localhost:$MOCK_PORT"
  say "the UI: cp $OUT/config.js ui/config.js; make ui UI_PORT=$UI_PORT"
  ;;

status)
  render
  for name in mock-auth $(units | cut -d' ' -f1); do
    if alive "$name"; then say "$name running"; else say "$name stopped"; fi
  done
  if [ -f "$OUT/nginx.pid" ] && kill -0 "$(cat "$OUT/nginx.pid")" 2> /dev/null; then say "nginx running"; else say "nginx stopped"; fi
  if [ "$(database)" = true ]; then
    if pg_ctl status -D "$OUT/pg" > /dev/null 2>&1; then say "PostgreSQL running"; else say "PostgreSQL stopped"; fi
  fi
  while read -r name _; do
    say "$name health $(curl -s -o /dev/null -w '%{http_code}' "http://$name.localhost:$NGINX_PORT/health" || true)"
  done < <(units)
  ;;

stop)
  render
  if [ -f "$OUT/nginx.pid" ] && kill -0 "$(cat "$OUT/nginx.pid")" 2> /dev/null; then
    nginx -p "$ABS" -e "$ABS/nginx-error.log" -c "$ABS/nginx.conf" -s quit
  fi
  for name in mock-auth $(units | cut -d' ' -f1); do
    if alive "$name"; then kill "$(cat "$OUT/$name.pid")"; fi
    rm -f "$OUT/$name.pid"
  done
  if [ "$(database)" = true ] && pg_ctl status -D "$OUT/pg" > /dev/null 2>&1; then pg_ctl -s -D "$OUT/pg" stop -m fast; fi
  say "stopped"
  ;;

*)
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
  ;;
esac
