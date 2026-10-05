# Local work only: nothing here talks to AWS, Cloudflare or the box.
#
#   make check     the manifest, and what the box will refuse
#   make render    the box's pieces, into box/out/<name>/
#   make test      each service's tests, offline
#   make ui        the UI on http://localhost:5173/, for development
#   make docs      the documentation, docs/*.md to build/docs/*.html
#
# The outside probes, against your live hosts, are probes/Makefile.

SHELL       := /bin/bash
.SHELLFLAGS := -o pipefail -c
SERVICES    := $(notdir $(wildcard services/*))
PY_VENV     := services/py-api/.venv

.PHONY: check render test test-js test-py ui docs
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

# Every page standalone, its links to .md pages made .html, anything
# that is not Markdown copied as it is. Needs pandoc. The release is a
# sync of build/docs/ to the docs bucket, as ui/ is to www's
DOCS_MD := $(shell find docs -name '*.md')
docs:
	@rm -rf build/docs && mkdir -p build/docs
	@for f in $(DOCS_MD); do o=build/$${f%.md}.html; mkdir -p "$$(dirname "$$o")"; \
	  pandoc -s --lua-filter tools/md-links.lua -f markdown -t html5 "$$f" -o "$$o" || exit 1; done
	@find docs -type f ! -name '*.md' -exec sh -c 'mkdir -p "build/$$(dirname "$$1")" && cp "$$1" "build/$$1"' _ {} \;
	@echo "build/docs/: $$(find build/docs -type f | wc -l) files"
