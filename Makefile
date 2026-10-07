# Local work only: nothing here talks to AWS, Cloudflare or the box. A
# release is a tag, vX.Y.Z, and GitHub's workflow
# (.github/workflows/release.yml, docs/onboarding/ci-cd.md).
#
#   make install-deps  the tools the tutorials need, by your system's
#                  packages: STACK=docker or STACK=podman adds the engine
#   make check-deps    each tool present and new enough
#   make check     the manifest, and what the box will refuse
#   make render    the box's pieces, into box/out/<name>/
#   make test      every service's tests, offline, by its language
#   make ui        the UI on http://localhost:5173/, for development
#   make dev       the dev stack: nginx, the services, a mock sign-in,
#                  PostgreSQL, the buckets as folders (needs Docker)
#   make dev-down  stop it; make dev-token, a token from the mock
#   make db-new    a migration: PREFIX=py_api NAME=notes_add_title
#   make db-lint   every migration, by Squawk
#   make db        dbmate in the dev stack: CMD=status (or up,
#                  rollback, or dump, which writes migrations/schema.sql)
#   make docs-build  the pages, by md-preview, into docs/_site/
#   make plan TAG=v0.2.0  what a release of that tag would do
#
# The outside probes, against your live hosts, are probes/Makefile.

# The compose command: Docker's, or rootless Podman's,
# make dev COMPOSE=podman-compose (docs/onboarding/podman.md)
COMPOSE     ?= docker compose
SHELL       := /bin/bash
.SHELLFLAGS := -o pipefail -c
SERVICES    := $(notdir $(wildcard services/*))

.PHONY: install-deps check-deps check render test ui dev dev-down dev-token db-new db-lint db docs-build plan
.DEFAULT_GOAL := check

# The tools of docs/tutorials/README.md §2, by the system's own package
# manager, sudo unless root; then check-deps. The system by uname and
# /etc/os-release, its ID first, then each it is like: Linux Mint is
# Ubuntu's, Manjaro Arch's. STACK adds Docker or Podman; never the
# docker group, which is root (§6 there)
STACK    ?=
SUDO     := $(shell [ "$$(id -u)" = 0 ] || echo sudo)
PLATFORM := $(shell if [ "$$(uname -s)" = Darwin ]; then echo macos; \
  elif [ -r /etc/os-release ]; then . /etc/os-release; for d in $$ID $$ID_LIKE; do \
  case $$d in (arch|alpine|ubuntu|debian) echo $$d; break ;; esac; done; fi)

ENGINE_arch_docker   := docker docker-compose
ENGINE_arch_podman   := podman podman-compose
ENGINE_debian_docker := docker.io docker-cli docker-compose
ENGINE_debian_podman := podman podman-compose uidmap passt slirp4netns
ENGINE_ubuntu_docker := docker.io docker-compose-v2
ENGINE_ubuntu_podman := podman podman-compose uidmap passt slirp4netns
ENGINE_alpine_docker := docker docker-cli-compose
ENGINE_alpine_podman := podman podman-compose
ENGINE_macos_podman  := podman podman-compose
ENGINE := $(ENGINE_$(PLATFORM)_$(STACK))

install-deps:
	@case "$(STACK)" in ""|docker|podman) ;; *) echo "STACK=docker, STACK=podman, or none" >&2; exit 1 ;; esac
	@[ -n "$(PLATFORM)" ] || { echo "install-deps: no recipe for this system; docs/tutorials/README.md §2 lists what to install" >&2; exit 1; }
	@echo "install-deps: $(PLATFORM)$(if $(STACK), with $(STACK))"
	@$(MAKE) --no-print-directory install-deps-$(PLATFORM)
	@$(MAKE) --no-print-directory check-deps

check-deps:
	@tools/check-deps.sh $(STACK)

install-deps-arch:
	$(SUDO) pacman -S --needed --noconfirm git bash make curl jq openssl coreutils diffutils grep \
	  python postgresql nodejs-lts-krypton npm $(ENGINE)

install-deps-alpine:
	$(SUDO) apk add --no-cache git bash make curl jq openssl coreutils diffutils grep \
	  python3 postgresql17-client nodejs npm $(ENGINE)

# Debian 13 and Ubuntu 24.04 have neither Node 24 nor, on Ubuntu,
# PostgreSQL 17: both from their makers' own apt repositories, each key
# trusted for its repository alone. PostgreSQL's key as the system's
# own postgresql-common ships it; NodeSource's fetched, and refused
# unless its fingerprint is the one first read, 2026-10-06. Nothing
# merely recommended: logrotate's would bring a mail server
NODESOURCE_KEY := 6F71F525282841EEDAF851B42F59B5F99B1BE0B4
APT := $(SUDO) env DEBIAN_FRONTEND=noninteractive apt-get --no-install-recommends
install-deps-debian install-deps-ubuntu:
	$(APT) update
	$(APT) install -y ca-certificates curl gnupg git bash make jq openssl coreutils diffutils grep \
	  python3 python3-venv postgresql-common
	echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] https://apt.postgresql.org/pub/repos/apt $$(. /etc/os-release; echo $$VERSION_CODENAME)-pgdg main" \
	  | $(SUDO) tee /etc/apt/sources.list.d/pgdg.list > /dev/null
	@g=$$(mktemp -d); trap 'rm -rf "$$g"' EXIT; export GNUPGHOME=$$g; k=$$g/key; \
	  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key > "$$k"; \
	  f=$$(gpg --show-keys --with-colons "$$k" 2> /dev/null | awk -F: '/^fpr/ {print $$10; exit}'); \
	  [ "$$f" = $(NODESOURCE_KEY) ] || { echo "install-deps: NodeSource's key is $$f, not $(NODESOURCE_KEY): stopped" >&2; exit 1; }; \
	  $(SUDO) install -d -m 0755 /etc/apt/keyrings; \
	  gpg --dearmor < "$$k" | $(SUDO) tee /etc/apt/keyrings/nodesource.gpg > /dev/null
	echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" \
	  | $(SUDO) tee /etc/apt/sources.list.d/nodesource.list > /dev/null
	$(APT) update
	$(APT) install -y postgresql-client-17 nodejs $(ENGINE)

# Homebrew's, as you: GNU make as gmake, and libpq and node@24 kept off
# PATH until you add them. Docker on a Mac is Docker Desktop, by hand
install-deps-macos:
	@command -v brew > /dev/null || { echo "install-deps: Homebrew first, https://brew.sh" >&2; exit 1; }
	@[ "$(STACK)" != docker ] || echo "install-deps: Docker Desktop is yours to install: https://docs.docker.com/desktop/setup/install/mac-install/"
	brew install git bash make curl jq openssl coreutils diffutils grep python@3.12 libpq node@24 $(ENGINE)
	@echo "install-deps: add to your shell's startup file, then open a new shell:"
	@echo '  export PATH="$$(brew --prefix)/opt/make/libexec/gnubin:$$(brew --prefix)/opt/libpq/bin:$$(brew --prefix)/opt/node@24/bin:$$(brew --prefix)/opt/python@3.12/libexec/bin:$$PATH"'
	@[ "$(STACK)" != podman ] || echo "install-deps: then, once: podman machine init && podman machine start"

# The manifest and the migrations' prefixes (render --check), each
# service folder named in it and each in it a folder, the build the
# box's own in every image's folder, and each Node lockfile matching its
# package.json
check:
	@python3 box/render.py --check
	@m=$$(jq -r '.services[].name' box/project.json | sort | paste -sd' '); f=$$(echo $(SERVICES) | tr ' ' '\n' | sort | paste -sd' '); \
	  [ "$$m" = "$$f" ] && echo "services/ and box/project.json agree: $$m" \
	  || { echo "box/project.json names $$m; services/ holds $$f" >&2; exit 1; }
	@for d in $(addprefix services/,$(SERVICES)) migrations; do [ -d $$d ] || continue; \
	  cmp -s $$d/build.sh box/build.sh && cmp -s $$d/buildspec.yml box/buildspec.yml \
	  || { echo "$$d: build.sh or buildspec.yml is not box/'s" >&2; exit 1; }; done; \
	  echo "build.sh and buildspec.yml the box's in every image's folder"
	@for d in services/*/package-lock.json; do d=$${d%/*}; \
	  r=$$(jq -r --slurpfile p $$d/package.json '. as $$l | [$$p[0].dependencies // {} | to_entries[] | select($$l.packages["node_modules/\(.key)"].version != .value) | .key] | join(" ")' $$d/package-lock.json); \
	  [ -z "$$r" ] || { echo "$$d: package-lock.json differs from package.json for $$r: npm install" >&2; exit 1; }; \
	  echo "$$d: lockfile matches"; done

render: check
	@python3 box/render.py

# Every service's tests, by its language in the manifest: Node's by
# npm test, Python's by unittest in a venv of the service's own, with
# httpx for FastAPI's test client
test:
	@set -e; jq -r '.services[] | "\(.name) \(.language)"' box/project.json | while read -r name lang; do \
	  echo "== $$name ($$lang)"; \
	  case $$lang in \
	    node) (cd services/$$name && npm ci --no-audit --no-fund --silent && npm test) ;; \
	    python) (cd services/$$name && { [ -d .venv ] || python3 -m venv .venv; } \
	      && .venv/bin/pip install -q -r requirements.txt httpx \
	      && .venv/bin/python -m unittest discover -s test) ;; \
	  esac; done

# 5173, a callback and an origin in the manifest; the native stack's
# own, UI_PORT from tools/native-dev.sh ports. The starter, ui/ as it
# is; or, once ui/ has a package.json (docs/tutorials/6-a-svelte-ui.md),
# its dev server, the config in ui/public/
UI_PORT ?= 5173
ui:
	@if [ -f ui/package.json ]; then \
	  [ -f ui/public/config.js ] || { echo "no ui/public/config.js: copy ui/config.dev.example.js" >&2; exit 1; }; \
	  cd ui && npm ci --no-audit --no-fund --silent && npx vite --host 127.0.0.1 --port $(UI_PORT) --strictPort; \
	else \
	  [ -f ui/config.js ] || { echo "no ui/config.js: copy ui/config.example.js" >&2; exit 1; }; \
	  python3 -m http.server $(UI_PORT) --bind 127.0.0.1 -d ui; \
	fi


# The dev stack, rendered from the manifest (docs/onboarding/local-dev.md).
# docs/_site/ is mounted as docs.localhost; md-preview builds it if it
# is there, and an empty folder stands in if not
dev: check
	@python3 box/render.py --dev
	@mkdir -p docs/_site; command -v md-preview > /dev/null && md-preview build docs > /dev/null || true
	$(COMPOSE) -f dev/out/compose.yml up --build -d

dev-down:
	$(COMPOSE) -f dev/out/compose.yml down

# An access token from the mock, for curl, as the probe client, with
# the e-mail its userInfo answers:
#   make dev-token SUB=asha EMAIL=asha@example.org GROUPS=admin
SUB      ?= dev-user
EMAIL    ?= $(SUB)@example.org
VERIFIED ?= true
GROUPS   ?=
MOCK_URL ?= http://localhost:9000
dev-token:
	@curl -s -H 'Content-Type: application/json' \
	  -d "$$(jq -nc --arg s '$(SUB)' --arg e '$(EMAIL)' --argjson v $(VERIFIED) --arg g '$(GROUPS)' '{sub: $$s, email: $$e, email_verified: $$v, client_id: "dev-probe", groups: ($$g | split(",") | map(select(. != "")))}')" \
	  $(MOCK_URL)/dev/token | jq -r .access_token

# Migrations (docs/migrations/write-a-migration.md): the project's one
# database, every file named for the service whose objects it makes.
# dbmate's form: one file, its up and its down, named by its time
PREFIX ?=
NAME   ?=
# Every prefix the manifest names: a service's prefix, or its prefixes
PREFIXES := [.services[] | (.prefixes // [.prefix // (.name | gsub("-"; "_"))])[]]
db-new:
	@jq -e --arg p '$(PREFIX)' '$(PREFIXES) | index($$p)' box/project.json > /dev/null \
	  || { echo "PREFIX=<a service's prefix>: $$(jq -r '$(PREFIXES) | join(", ")' box/project.json)" >&2; exit 1; }
	@echo "$(NAME)" | grep -qE '^[a-z][a-z0-9_]{2,60}$$' || { echo "NAME=<lower_case_words>" >&2; exit 1; }
	@f=migrations/sql/$$(date -u +%Y%m%d%H%M%S)_$(PREFIX)_$(NAME).sql; \
	  printf -- "-- migrate:up\nSET lock_timeout = '2s';\nSET statement_timeout = '30s';\n\n-- migrate:down\nSET lock_timeout = '2s';\nSET statement_timeout = '30s';\n" > $$f; \
	  echo "$$f"

# Squawk, by version, from npm: it fetches its own binary. From
# migrations/, where its settings are
SQUAWK := npx --yes squawk-cli@2.67.0
db-lint:
	cd migrations && $(SQUAWK) sql/*.sql

# dbmate, in the dev stack, as the database's migrator
CMD ?= status
db:
	$(COMPOSE) -f dev/out/compose.yml run --rm migrate $(CMD)

docs-build:
	md-preview build docs

# What a release of TAG would build and sync, against the tag before it
TAG ?=
plan:
	@tools/release-plan.sh $(TAG)
