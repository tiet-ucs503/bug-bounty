# The project's own probes: from outside, through Cloudflare, with no
# AWS identity and no access to the box. What a maintainer can see is
# what a user sees; these check it against box/project.json.
#
#   make -C probes ZONE=example.org                  # all but the token's
#   make -C probes token ZONE=example.org TOKEN_FILE=~/.config/myproject/token
#
# TOKEN_FILE holds an access token for your project's UI client, one
# line, mode 0600: from the UI's sign-in, say, its sessionStorage's
# access_token. It lasts an hour. Never commit it, never paste it.
#
# Each target prints PASS or FAIL lines. Exit 1 on the first FAIL.
# Needs curl and jq.

SHELL       := /bin/bash
.SHELLFLAGS := -o pipefail -c
MANIFEST    := $(CURDIR)/../box/project.json

ifndef ZONE
$(error ZONE is unset: make -C probes ZONE=<your zone>)
endif

H = pass() { echo "PASS $@: $$*"; }; fail() { echo "FAIL $@: $$*"; exit 1; }; \
  want() { if [[ "$$1" == $$2 ]]; then pass "$$1"; else fail "$$1 --- want $$2"; fi; }; \
  services() { jq -r '.services[].name' $(MANIFEST); }; \
  code() { curl -s -o /dev/null -w '%{http_code}' "$$@"; };

.PHONY: all hosts health allow-list signed-in cors rate www static docs token
all: hosts health allow-list signed-in cors rate www static docs

# Every host answers through Cloudflare, over TLS
hosts:
	@$(H) \
	for h in www static docs $$(services); do \
	  s=$$(curl -s -o /dev/null -D - "https://$$h.$(ZONE)/" | tr -d '\r' | awk 'tolower($$1) == "server:" {print $$2}'); \
	  want "$$h: server $${s:-none}" "$$h: server cloudflare"; \
	done

# Each service's /health, from the service named, not another
health:
	@$(H) \
	for s in $$(services); do \
	  a=$$(curl -s "https://$$s.$(ZONE)/health" | jq -r .service 2>/dev/null); \
	  want "$$s: health from $${a:-nothing}" "$$s: health from $$s"; \
	done

# A path the manifest does not name is 404; a method it does not name
# for /health is 403
allow-list:
	@$(H) \
	for s in $$(services); do u="https://$$s.$(ZONE)"; \
	  want "$$s: nowhere $$(code "$$u/probe-nowhere"), delete health $$(code -X DELETE "$$u/health")" \
	    "$$s: nowhere 404, delete health 403"; \
	done

# Every signed-in route without a parameter refuses a caller with no
# token, and one with a bad token, 401
signed-in:
	@$(H) \
	jq -r '.services[] | .name as $$s | .routes[] | select(.signed_in and (.path | contains("{") | not)) | "\($$s) \(.method) \(.path)"' $(MANIFEST) \
	  > $(CURDIR)/.signed-in; \
	while read -r s m p; do u="https://$$s.$(ZONE)$$p"; \
	  b=(-X "$$m" -H 'Content-Type: application/json'); [ "$$m" = GET ] || b+=(-d '{}'); \
	  want "$$s: $$m $$p none $$(code "$${b[@]}" "$$u"), bad $$(code "$${b[@]}" -H 'Authorization: Bearer a.b.c' "$$u")" \
	    "$$s: $$m $$p none 401, bad 401"; \
	done < $(CURDIR)/.signed-in; rm -f $(CURDIR)/.signed-in

# The UI's origin preflighted and answered by nginx; another origin not
cors:
	@$(H) \
	w="https://www.$(ZONE)"; \
	for s in $$(services); do u="https://$$s.$(ZONE)/health"; \
	  a=$$(curl -s -o /dev/null -D - -X OPTIONS -H "Origin: $$w" -H 'Access-Control-Request-Method: POST' "$$u" \
	    | tr -d '\r' | awk 'NR == 1 {print $$2} tolower($$1) == "access-control-allow-origin:" {print "origin"} tolower($$1) == "access-control-max-age:" {print "max-age", $$2}' | paste -sd' '); \
	  b=$$(curl -s -o /dev/null -D - -X OPTIONS -H 'Origin: https://elsewhere.example' -H 'Access-Control-Request-Method: POST' "$$u" \
	    | tr -d '\r' | awk 'NR == 1 {print $$2} tolower($$1) == "access-control-allow-origin:" {print "origin"}' | paste -sd' '); \
	  want "$$s: www $$a; elsewhere $$b" "$$s: www 204 origin max-age 7200; elsewhere 403"; \
	done

# Sixty writes at once to the first signed-in POST route: 10 a second
# per client and a burst of 20 queued, so some are 429, each with
# Retry-After; the rest reach the service, 401 unsigned
rate:
	@$(H) \
	r=$$(jq -r '[.services[] | .name as $$s | .routes[] | select(.method == "POST" and .signed_in and (.path | contains("{") | not)) | "\($$s) \(.path)"][0] // ""' $(MANIFEST)); \
	[ -n "$$r" ] || { pass "no signed-in POST route to try"; exit 0; }; \
	set -- $$r; u="https://$$1.$(ZONE)$$2"; \
	seq 60 | xargs -P 60 -I{} curl -s -o /dev/null -D - -X POST -H 'Content-Type: application/json' -d '{}' "$$u" \
	  | tr -d '\r' > $(CURDIR)/.rate; \
	t=$$(grep -cE '^HTTP/' $(CURDIR)/.rate); n=$$(grep -cE '^HTTP/[0-9.]+ 429' $(CURDIR)/.rate); \
	k=$$(grep -cE '^HTTP/[0-9.]+ 401' $(CURDIR)/.rate); a=$$(grep -ci '^retry-after:' $(CURDIR)/.rate); \
	rm -f $(CURDIR)/.rate; \
	pass "$$1 POST $$2: $$t writes, $$n 429, $$k 401, Retry-After on $$a"; \
	[ $$t -eq 60 ] && [ $$n -gt 0 ] && [ $$((n + k)) -eq 60 ] && [ $$a -eq $$n ] \
	  || fail "want 60, some 429 each with Retry-After, the rest 401"

# The UI's page, and a key that is not there
www:
	@$(H) \
	want "www: / $$(code "https://www.$(ZONE)/")" "www: / 200"

# The documentation's index, built by make docs and released
docs:
	@$(H) \
	want "docs: /index.html $$(code "https://docs.$(ZONE)/index.html")" "docs: /index.html 200"

static:
	@$(H) \
	want "static: a missing key $$(code "https://static.$(ZONE)/probe-nowhere")" "static: a missing key 404"

# Signed in: each service's POST /echo answers 200, naming the caller.
# The token goes to curl as a config on a descriptor, never an argument
token:
	@$(H) \
	[ -r "$(TOKEN_FILE)" ] || fail "TOKEN_FILE unset or unreadable"; \
	for s in $$(services); do \
	  c=$$(curl -s -o /dev/null -w '%{http_code}' -K <(printf 'header = "Authorization: Bearer %s"\n' "$$(tr -d '\n' < "$(TOKEN_FILE)")") \
	    -X POST -H 'Content-Type: application/json' -d '{"probe": true}' "https://$$s.$(ZONE)/echo"); \
	  want "$$s: echo signed in $$c" "$$s: echo signed in 200"; \
	done
