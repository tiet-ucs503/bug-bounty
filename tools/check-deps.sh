#!/usr/bin/env bash
# What the tutorials and the stacks need, each tool present and new
# enough (docs/tutorials/README.md §2). One line a tool: ok, old or
# none. Exit 1 if any is old or none.
#
#   tools/check-deps.sh            the tools, for either stack
#   tools/check-deps.sh docker     and Docker with Compose
#   tools/check-deps.sh podman     and Podman with podman-compose
set -uo pipefail

bad=0

# The first version-like number in a command's output
version() { "$@" 2>&1 | grep -oE '[0-9]+(\.[0-9]+)+' | head -1; }

# at_least HAVE NEED: true if HAVE is NEED or later
at_least() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

# need NAME MINIMUM COMMAND...: ok, old or none
need() {
  local name=$1 min=$2; shift 2
  [ $# -gt 0 ] || set -- "$name"
  if ! command -v "${1}" > /dev/null; then
    printf 'none %s\n' "$name"; bad=1; return
  fi
  [ -z "$min" ] && { printf 'ok   %s\n' "$name"; return; }
  local v; v=$(version "$@")
  if [ -n "$v" ] && at_least "$v" "$min"; then
    printf 'ok   %s %s\n' "$name" "$v"
  else
    printf 'old  %s %s, needs %s or later\n' "$name" "${v:-unknown}" "$min"; bad=1
  fi
}

need git ""
need bash ""
need curl ""
need openssl ""
need base64 ""
need diff ""
need cmp ""
need grep ""
if command -v make > /dev/null && ! make --version 2>&1 | grep -q 'GNU Make'; then
  echo "old  make, not GNU's: install GNU make"; bad=1
else
  need make 4.0 make --version
fi
need jq 1.6 jq --version
need python3 3.12 python3 --version
if command -v python3 > /dev/null && ! python3 -c 'import venv, ensurepip' 2> /dev/null; then
  echo "none python3's venv: python3-venv, on Debian and Ubuntu"; bad=1
fi
need psql 17 psql --version
need pg_dump 17 pg_dump --version
need node 24 node --version
need npm "" npm --version

case ${1:-} in
  "") ;;
  docker)
    if command -v docker > /dev/null; then
      need "docker compose" 2.20 docker compose version
    else
      echo "none docker"; bad=1
    fi ;;
  podman)
    if command -v podman > /dev/null; then
      v=$(version podman --version)
      if [ -n "$v" ] && at_least "$v" 5; then echo "ok   podman $v"
      else echo "old  podman ${v:-unknown}, needs 5 or later: docs/onboarding/podman.md §2"; bad=1; fi
    else
      echo "none podman"; bad=1
    fi
    if command -v podman-compose > /dev/null; then
      v=$(podman-compose --version 2>&1 | grep -i 'podman-compose' | grep -oE '[0-9]+(\.[0-9]+)+' | head -1)
      if [ -n "$v" ] && at_least "$v" 1.5; then echo "ok   podman-compose $v"
      else echo "old  podman-compose ${v:-unknown}, needs 1.5 or later: docs/onboarding/podman.md §2"; bad=1; fi
    else
      echo "none podman-compose"; bad=1
    fi ;;
  *) echo "check-deps: STACK is docker, podman or empty, not ${1}" >&2; exit 2 ;;
esac

exit $bad
