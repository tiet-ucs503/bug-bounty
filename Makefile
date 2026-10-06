# Local work only: nothing here talks to AWS, Cloudflare or the box.
#
#   make check     the manifest, and what the box will refuse
#   make render    the box's pieces, into box/out/<name>/
#   make test      each service's tests, offline
#   make ui        the UI on http://localhost:5173/, for development
#   make dev       the dev stack: nginx, the services, a mock sign-in,
#                  PostgreSQL, the buckets as folders (needs Docker)
#   make dev-down  stop it; make dev-token, a token from the mock
#   make db-new    a migration: SVC=py-api NAME=add_title
#   make db-lint   every migration, by Squawk
#   make db        dbmate in the dev stack: SVC=py-api CMD=status
#                  (or rollback, or dump, which writes schema.sql)
#
# The outside probes, against your live hosts, are probes/Makefile.

SHELL       := /bin/bash
.SHELLFLAGS := -o pipefail -c
SERVICES    := $(notdir $(wildcard services/*))
PY_VENV     := services/py-api/.venv

.PHONY: check render test test-js test-py ui dev dev-down dev-token db-new db-lint db
.DEFAULT_GOAL := check

# The manifest, each service folder named in it and each in it a
# folder, the build the box's own in every folder, and each Node
# lockfile matching its package.json
check:
	@python3 box/render.py --check
	@m=$$(jq -r '.services[].name' box/project.json | sort | paste -sd' '); f=$$(echo $(SERVICES) | tr ' ' '\n' | sort | paste -sd' '); \
	  [ "$$m" = "$$f" ] && echo "services/ and box/project.json agree: $$m" \
	  || { echo "box/project.json names $$m; services/ holds $$f" >&2; exit 1; }
	@for s in $(SERVICES); do cmp -s services/$$s/build.sh box/build.sh && cmp -s services/$$s/buildspec.yml box/buildspec.yml \
	  || { echo "services/$$s: build.sh or buildspec.yml is not box/'s" >&2; exit 1; }; done; \
	  echo "build.sh and buildspec.yml the box's in every service"
	@for s in $$(jq -r '.services[] | select(.database) | .name' box/project.json); do [ -d db/$$s/migrations ] \
	  || { echo "$$s: database true in box/project.json, and no db/$$s/migrations/" >&2; exit 1; }; done; \
	  for d in db/*/; do [ -d "$$d" ] || continue; s=$$(basename $$d); \
	  jq -e --arg s $$s '.services[] | select(.name == $$s and .database)' box/project.json > /dev/null \
	  || { echo "db/$$s/: no service $$s with database true in box/project.json" >&2; exit 1; }; done; \
	  echo "db/ and the manifest's databases agree"
	@for d in services/*/package-lock.json; do d=$${d%/*}; \
	  r=$$(jq -r --slurpfile p $$d/package.json '. as $$l | [$$p[0].dependencies // {} | to_entries[] | select($$l.packages["node_modules/\(.key)"].version != .value) | .key] | join(" ")' $$d/package-lock.json); \
	  [ -z "$$r" ] || { echo "$$d: package-lock.json differs from package.json for $$r: npm install" >&2; exit 1; }; \
	  echo "$$d: lockfile matches"; done

render: check
	@python3 box/render.py

test: test-js test-py

test-js:
	cd services/js-api && npm ci --no-audit --no-fund && npm test

$(PY_VENV):
	python3 -m venv $@ && $@/bin/pip install -q -r services/py-api/requirements.txt httpx

test-py: $(PY_VENV)
	cd services/py-api && .venv/bin/python -m unittest discover -s test

ui:
	@[ -f ui/config.js ] || { echo "no ui/config.js: copy ui/config.example.js" >&2; exit 1; }
	python3 -m http.server 5173 --bind 127.0.0.1 -d ui


# The dev stack, rendered from the manifest (docs/onboarding/local-dev.md).
# docs/_site/ is mounted as docs.localhost; md-preview builds it if it
# is there, and an empty folder stands in if not
dev: check
	@python3 box/render.py --dev
	@mkdir -p docs/_site; command -v md-preview > /dev/null && md-preview build docs > /dev/null || true
	docker compose -f dev/out/compose.yml up --build -d

dev-down:
	docker compose -f dev/out/compose.yml down

# An access token from the mock, for curl, as the probe client:
#   make dev-token SUB=alice GROUPS=admin
SUB    ?= dev-user
GROUPS ?=
dev-token:
	@curl -s -H 'Content-Type: application/json' \
	  -d "$$(jq -nc --arg s '$(SUB)' --arg g '$(GROUPS)' '{sub: $$s, client_id: "dev-probe", groups: ($$g | split(",") | map(select(. != "")))}')" \
	  http://localhost:9000/dev/token | jq -r .access_token

# Migrations (docs/onboarding/write-a-migration.md). dbmate's form: one
# file, its up and its down, named by the time it was made
SVC  ?=
NAME ?=
db-new:
	@case "$(SVC)" in '') echo "SVC=<service>" >&2; exit 1;; esac; [ -d db/$(SVC)/migrations ] \
	  || { echo "no db/$(SVC)/migrations: database true for $(SVC) in box/project.json, and make check" >&2; exit 1; }
	@echo "$(NAME)" | grep -qE '^[a-z][a-z0-9_]{2,60}$$' || { echo "NAME=<lower_case_words>" >&2; exit 1; }
	@f=db/$(SVC)/migrations/$$(date -u +%Y%m%d%H%M%S)_$(NAME).sql; \
	  printf -- "-- migrate:up\nSET lock_timeout = '2s';\nSET statement_timeout = '30s';\n\n-- migrate:down\nSET lock_timeout = '2s';\nSET statement_timeout = '30s';\n" > $$f; \
	  echo "$$f"

# Squawk, by version, from npm: it fetches its own binary
SQUAWK := npx --yes squawk-cli@2.67.0
db-lint:
	$(SQUAWK) db/*/migrations/*.sql

# dbmate, in the dev stack, as the service's migrator
CMD ?= status
db:
	@case "$(SVC)" in '') echo "SVC=<service>" >&2; exit 1;; esac
	docker compose -f dev/out/compose.yml run --rm migrate-$(SVC) $(CMD)
