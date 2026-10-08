---
abstract: |
  Step 3 of tutorial 4: the concept's nine rules as
  fifteen tests in one script, calling `/users`
  through nginx. The same script tests either language.
  Run it now, and every test fails.
date: 2026-10-07
keywords:
- tutorial
- api
- tests
kind: reference
sources:
- services/py-api/main.py
- services/js-api/server.js
status: draft
subtitle: Step 3, how we measure it
title: "4.3 /users: the Tests"
version: v0.1.0
---

## 1 From the Rules to the Tests

Each rule of [the concept](1-concept.md) §3, held to
[the contract](2-contract.md). Three people: you, the
first admin, by tutorial 3's migration; `t4-asha`; and
`t4-esha`, whose e-mail is not verified. The tests
expect no starting role but the first admin's.

- **T4.1, T4.2, U1:** no token, and a token that is not
  one? Expect `401`, twice
- **T4.3, U2:** `t4-esha` calls `/users/me`? Expect
  `403`
- **T4.4, U2, U3:** `t4-asha` calls it the first time:
  how many roles? Expect `200 0`
- **T4.5, U3:** you call it? Expect `200 admin`
- **T4.6, U5:** `t4-asha` lists the people? Expect
  `403`
- **T4.7, U5:** you list them: is `t4-asha` there?
  Expect `200 true`
- **T4.8, U5:** you give `t4-asha` `reader`: what roles
  does she hold? Expect `200 reader`. Not what she may
  do: `reader` holds nothing until a unit brings its
  permissions, as tutorial 5's notes do
- **T4.9, U5:** a role for someone never seen? Expect
  `404 no such person`, the database's own message, not
  nginx's page
- **T4.10, U5:** `t4-asha` takes your `admin`? Expect
  `403`
- **T4.11, U4:** `t4-asha` sets her profile: her name
  after? Expect `200 Asha`
- **T4.12, U4:** a name of 81 characters? Expect `400`
- **T4.13, U6:** `/users/me` without a token, and a
  route the manifest does not name? Expect `401 404`:
  the first reaches the service, the second does not
- **T4.14, U8:** the `Cache-Control` of `/users/me`?
  Expect `no-store`
- **T4.15, U9:** the service's reference, through
  nginx: how many `/users` routes does it name, and how
  many of them ask for a token? Expect `6 6`

The service's own tests cover what this cannot reach
from outside: a token issued to another client, and the
provider read from `username`.

## 2 The File

Save it as `test-4.sh` at your fork's root, and make it
runnable. `SERVICE` is the service you take, `py-api`
unless you set it; `FIRST_ADMIN`, as in tutorial 3. It
gives `t4-asha` `reader` and takes it back at the end.

``` sh
#!/usr/bin/env bash
# Tutorial 4's tests, T4.1 to T4.15: /users through nginx, as the UI
# will call it. Run from your fork's root, with H and MOCK_URL set, and
# SERVICE the one that serves /users: py-api, or js-api. It signs in
# t4-asha and t4-esha by the mock, and takes back the role it gives
set -uo pipefail
SERVICE=${SERVICE:-py-api}
FIRST_ADMIN=${FIRST_ADMIN:-you@example.org}
U=http://${SERVICE}.${H}/users

tok() { make -s dev-token MOCK_URL="${MOCK_URL}" "$@"; }
Y=$(tok SUB=you EMAIL="${FIRST_ADMIN}")
A=$(tok SUB=t4-asha)
E=$(tok SUB=t4-esha VERIFIED=false)

# call METHOD PATH TOKEN [BODY] [JQ]: the status, and what JQ picks
call() {
  local out code
  out=$(curl -s -w '\n%{http_code}' -X "$1" ${3:+-H "Authorization: Bearer $3"} \
    ${4:+-H 'Content-Type: application/json' -d "$4"} "${U}$2")
  code=${out##*$'\n'}
  if [ -n "${5:-}" ]; then echo "${code} $(echo "${out%$'\n'*}" | jq -rc "$5" 2> /dev/null)"; else echo "${code}"; fi
}

pass=0; all=0; failed=""
expect() {
  all=$((all + 1))
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); echo "ok   $1: want $2, got $3"
  else failed="${failed} $1"; echo "FAIL $1: want $2, got ${3:-nothing}"; fi
}

# U1: a token, or nothing
expect T4.1 401 "$(call GET /me "")"
expect T4.2 401 "$(call GET /me not-a-token)"
# U2: an unverified e-mail is not kept
expect T4.3 403 "$(call GET /me "${E}")"
# U2, U3: recorded at the first call, with no role yet
expect T4.4 "200 0" "$(call GET /me "${A}" '' '.roles | length')"
expect T4.5 "200 admin" "$(call GET /me "${Y}" '' '.roles | join(",")')"
# U5: the database decides, by the caller's roles
expect T4.6 403 "$(call GET /people "${A}")"
expect T4.7 "200 true" "$(call GET /people "${Y}" '' 'any(.[]; .sub == "t4-asha")')"
call PUT /people/t4-asha/roles/reader "${Y}" > /dev/null
expect T4.8 "200 reader" "$(call GET /me "${A}" '' '.roles | join(",")')"
expect T4.9 "404 no such person" "$(call PUT /people/nobody/roles/reader "${Y}" '' '.error')"
expect T4.10 403 "$(call DELETE /people/you/roles/admin "${A}")"
# U4: your own profile
expect T4.11 "200 Asha" "$(call PUT /me/profile "${A}" '{"display_name": "Asha", "affiliation": "Physics"}' '.profile.display_name')"
expect T4.12 400 "$(call PUT /me/profile "${A}" "{\"display_name\": \"$(printf 'a%.0s' $(seq 81))\"}")"
# U6: nginx passes the manifest's routes, and only those
expect T4.13 "401 404" "$(call GET /me "") $(call GET /secret "${Y}")"
# U8: never cached
expect T4.14 no-store "$(curl -s -o /dev/null -D - -H "Authorization: Bearer ${A}" "${U}/me" | tr -d '\r' | sed -n 's/^cache-control: //Ip')"
# U9: the reference, made from the routes, names each and its token
expect T4.15 "6 6" "$(curl -s "${U%/users}/openapi.json" | jq -r '[.paths | to_entries[] | select(.key | startswith("/users")) | .value[]] | "\(length) \(map(select(.security)) | length)"' 2> /dev/null)"

call DELETE /people/t4-asha/roles/reader "${Y}" > /dev/null
echo "${pass} of ${all} pass"
[ -z "${failed}" ] || { echo "failed:${failed}"; exit 3; }
```

## 3 Run It Now

Before any of tutorial 4's code, nginx knows no
`/users` route, and answers `404` to every one. Expect
`FAIL` on every line, most with `got 404`, T4.15 with
`got 0 0`, and `0 of 15 pass`:

``` sh
./test-4.sh
```

## 4 See Also

- [The contract](2-contract.md): the step before
- The implementation, [in
  Python](4-implementation-python.md) or [in
  JavaScript](4-implementation-javascript.md): what
  makes these pass
