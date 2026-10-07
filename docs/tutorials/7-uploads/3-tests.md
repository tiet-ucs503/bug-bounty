---
abstract: |
  Step 3 of tutorial 7: the concept's seven rules as
  eighteen tests. Eight in the database, seven through
  nginx, three in the dashboard; one script runs them
  all, after checking that the stack's store and nginx
  behave as the box's. Run it now, and every test
  fails.
date: 2026-10-07
keywords:
- tutorial
- uploads
- tests
kind: reference
sources:
- dev/mock-store/server.py
- services/py-api/main.py
status: draft
subtitle: Step 3, how we measure it
title: "7.3 Uploads: the Tests"
version: v0.1.0
---

## 1 From the Rules to the Tests

Each rule of [the concept](1-concept.md) §2, held to
[the contract](2-contract.md). Two people: `t7-asha`, a
member, and `t7-bhanu`, a reader.

**In the database,** in a transaction rolled back:

- **T7.1, O3:** `t7-asha` adds an object: its key, and
  stored yet? Expect `false true`: not stored, and the
  key `objects/<16 hex>/<the hash>`
- **T7.2, O3:** the same bytes again: how many objects?
  Expect `1`
- **T7.3, O2:** `t7-bhanu`, a reader, adds one? Expect
  `42501`
- **T7.4, O5, O6:** a note of hers refers to it: its
  references? Expect `1`
- **T7.5, O5:** `t7-bhanu`, a member now, refers to
  hers? Expect `P0002`
- **T7.6, O6, O7:** her note deleted: references, and
  to collect within the grace? Expect `0 0`
- **T7.7, O7:** seven hours on: to collect? Expect `1`
- **T7.8, O7:** forgotten once deleted? Expect `1`

**Through nginx,** at py-api and the static host:

- **T7.9, O2, O3:** `t7-asha` uploads a file: its
  status and key? Expect `201` and
  `objects/<her tag>/<its hash>`
- **T7.10, O2:** read back from the static host? Expect
  `same` bytes
- **T7.11, O3:** the same file again? Expect `201` and
  the same key
- **T7.12, O6:** a note of hers lists it: its
  references in `/objects/mine`? Expect `1`
- **T7.13, O4:** an HTML file? Expect `415`
- **T7.14, O2:** `t7-bhanu`, a reader, uploads? Expect
  `403`
- **T7.15, O7:** her note deleted, after the grace and
  a round of the collector: the file at the static
  host? Expect `404`

**In the dashboard,** by `ui/`'s tests:

- **T7.16, O4:** a file of a type not allowed: said so,
  and nothing sent
- **T7.17, O4:** a file over 1 MiB: said so, and
  nothing sent
- **T7.18, O2, O5:** a PNG: sent as itself, then the
  note's list saved with its key

Before any test, the script checks the stack: that its
store behaves as [the contract](2-contract.md) §4 says
the box's bucket does, and that nginx refuses a body
over 1 MiB. Both are the template's, so they hold
before any of tutorial 7's code; if either fails, the
script stops, since nothing after it would mean
anything.

## 2 The Files

`test-7.sql`, at your fork's root:

``` sql
-- Tutorial 7's database tests, T7.1 to T7.8: an object's life, from
-- its row to its collection. Run in a transaction that is rolled back
CREATE TEMP TABLE t6_results (id text PRIMARY KEY, ok boolean NOT NULL);
CREATE FUNCTION pg_temp.expect(p_id text, p_act text, p_ask text, p_want text) RETURNS text
  LANGUAGE plpgsql AS $$
DECLARE got text;
BEGIN
  BEGIN
    IF p_act IS NOT NULL THEN EXECUTE p_act; END IF;
    EXECUTE p_ask INTO got;
  EXCEPTION WHEN OTHERS THEN got := SQLSTATE;
  END;
  INSERT INTO t6_results VALUES (p_id, got IS NOT DISTINCT FROM p_want);
  RETURN format('%s %s: want %s, got %s',
    CASE WHEN got IS NOT DISTINCT FROM p_want THEN 'ok  ' ELSE 'FAIL' END, p_id, p_want, coalesce(got, 'nothing'));
END
$$;

-- Two people signed in: t7-asha a member, t7-bhanu a reader
SELECT users_person_see('t7-asha', 't7-asha@example.org', true, 'Google'),
       users_person_see('t7-bhanu', 't7-bhanu@example.org', true, 'Google');
DO $$ BEGIN
  INSERT INTO users_members (sub, role) VALUES ('t7-asha', 'member'), ('t7-bhanu', 'reader') ON CONFLICT DO NOTHING;
EXCEPTION WHEN undefined_table THEN NULL;
END $$;

-- O3: the key names its owner and its content; not stored until the bucket holds it
SELECT pg_temp.expect('T7.1', NULL,
  $$SELECT stored::text || ' ' || (key ~ '^objects/[0-9a-f]{16}/a{64}$')::text
    FROM py_api_object_add('t7-asha', repeat('a', 64), 10, 'image/png')$$, 'false true');
-- O3: the same bytes again are the same object
SELECT pg_temp.expect('T7.2', $$SELECT py_api_object_add('t7-asha', repeat('a', 64), 10, 'image/png')$$,
  $$SELECT count(*) FROM py_api_objects WHERE owner = 't7-asha'$$, '1');
-- O2: a reader may not upload
SELECT pg_temp.expect('T7.3', NULL,
  $$SELECT key FROM py_api_object_add('t7-bhanu', repeat('b', 64), 10, 'image/png')$$, '42501');
-- O5, O6: a note refers to it, counted
SELECT pg_temp.expect('T7.4',
  $$SELECT py_api_object_stored('t7-asha', (SELECT key FROM py_api_objects WHERE owner = 't7-asha'));
    SELECT py_api_note_objects_set('t7-asha', py_api_note_new('t7-asha', 't6: with an object'),
                                   ARRAY(SELECT key FROM py_api_objects WHERE owner = 't7-asha'))$$,
  $$SELECT refs FROM py_api_objects_mine('t7-asha')$$, '1');
-- O5: one owner's object is never another's to refer to
SELECT pg_temp.expect('T7.5',
  $$INSERT INTO users_members (sub, role) VALUES ('t7-bhanu', 'member')$$,
  $$SELECT py_api_note_objects_set('t7-bhanu', py_api_note_new('t7-bhanu', 't6: his'),
                                   ARRAY(SELECT key FROM py_api_objects WHERE owner = 't7-asha'))::text$$, 'P0002');
-- O6, O7: the note gone, nothing refers to it, and the grace holds it
SELECT pg_temp.expect('T7.6',
  $$SELECT py_api_note_drop('t7-asha', (SELECT max(id) FROM py_api_notes WHERE owner = 't7-asha'))$$,
  $$SELECT (SELECT refs FROM py_api_objects_mine('t7-asha')) || ' ' ||
           (SELECT count(*) FROM py_api_objects_to_collect('6 hours', 10))$$, '0 0');
-- O7: after the grace, it is to collect
SELECT pg_temp.expect('T7.7',
  $$UPDATE py_api_objects SET created_at = created_at - interval '7 hours',
      released_at = released_at - interval '7 hours' WHERE owner = 't7-asha'$$,
  $$SELECT count(*) FROM py_api_objects_to_collect('6 hours', 10) k
    WHERE k IN (SELECT key FROM py_api_objects WHERE owner = 't7-asha')$$, '1');
-- O7: forgotten once deleted
SELECT pg_temp.expect('T7.8', NULL,
  $$SELECT py_api_objects_forget(ARRAY(SELECT key FROM py_api_objects WHERE owner = 't7-asha'))$$, '1');

SELECT format('%s of %s pass', count(*) FILTER (WHERE ok), count(*)) FROM t6_results;
```

`ui/test/attach.test.js`, beside tutorial 6's tests:

``` javascript
// Tutorial 7's tests of the attachments, T7.16 to T7.18: what is sent,
// and what is refused before it is. Attach.svelte in jsdom; box.js
// replaced, so no network. `npm test`
import { test, expect, vi, beforeEach } from "vitest";
import { mount, unmount, tick } from "svelte";

vi.mock("../src/lib/box.js", () => ({ api: vi.fn() }));
const box = await import("../src/lib/box.js");
const { default: Attach } = await import("../src/Attach.svelte");

let app, changed;
beforeEach(() => {
  if (app) unmount(app);
  document.body.innerHTML = "";
  vi.clearAllMocks();
  changed = vi.fn();
  box.api.mockImplementation(async (service, path, opts) =>
    path === "/objects/new" ? { status: 201, data: { key: "objects/0123456789abcdef/" + "c".repeat(64) } } : { status: 200, data: {} });
  app = mount(Attach, { target: document.body, props: { note: { id: 5, objects: [] }, onchange: changed } });
});

// Files chosen in the picker, then a moment for the uploads
async function choose(...files) {
  const input = document.querySelector("input[type=file]");
  Object.defineProperty(input, "files", { value: files, configurable: true });
  input.dispatchEvent(new Event("change", { bubbles: true }));
  for (let i = 0; i < 5; i++) await tick();
}
const uploads = () => box.api.mock.calls.filter(([, path]) => path === "/objects/new");

test("T7.16 a type not allowed: said so, and nothing uploaded", async () => {
  await choose(new File(["<p>hi"], "page.html", { type: "text/html" }));
  expect(document.body.textContent).toContain("text/html is not allowed");
  expect(uploads()).toHaveLength(0);
});

test("T7.17 over 1 MiB: said so, and nothing uploaded", async () => {
  await choose(new File([new Uint8Array(1024 * 1024 + 1)], "big.png", { type: "image/png" }));
  expect(document.body.textContent).toContain("over 1 MiB");
  expect(uploads()).toHaveLength(0);
});

test("T7.18 a PNG: sent as itself, then the note's list saved with its key", async () => {
  const png = new File([new Uint8Array([137, 80, 78, 71])], "blue.png", { type: "image/png" });
  await choose(png);
  expect(uploads()[0]).toEqual(["py-api", "/objects/new", { method: "POST", raw: png }]);
  expect(box.api).toHaveBeenLastCalledWith("py-api", "/notes/5/objects",
    { method: "PUT", body: { keys: ["objects/0123456789abcdef/" + "c".repeat(64)] } });
  expect(changed).toHaveBeenCalled();
});
```

`test-7.sh`, at your fork's root, runnable. T7.15 needs
a quick collector, which [the
service](4-the-service.md) §5 sets in `dev/dev.env`:

``` sh
#!/usr/bin/env bash
# Tutorial 7's tests, T7.1 to T7.18: the database's, by test-7.sql;
# py-api's uploads and the collector, through nginx; and the
# attachments in the dashboard, by ui/'s npm test. First, that the
# stack's store behaves as the box's bucket. Run from your fork's root
# with the conventions' six settings, and a quick collector in
# dev/dev.env. Its rows are rolled back, its notes deleted, its roles
# taken back
set -uo pipefail
USERS=${USERS:-py-api}
FIRST_ADMIN=${FIRST_ADMIN:-you@example.org}
P=http://py-api.${H}
work=$(mktemp -d); trap 'rm -rf "${work}"' EXIT
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

# Before any test: the stack's store behaves as the box's bucket, and
# its nginx as the box's. Both are the template's, so these hold before
# tutorial 7's code; a failure here is the stack's, and nothing after it
# means anything
printf 'hello, objects\n' > "${work}/hello.txt"
sum=$(openssl dgst -sha256 -binary "${work}/hello.txt" | base64)
store=$(code -X PUT -H 'Content-Type: text/plain' -H "x-amz-checksum-sha256: ${sum}" \
    --data-binary @"${work}/hello.txt" "${STORE_URL}/objects/t6/hello"
  echo " $(curl -s "${STATIC_URL}/objects/t6/hello")"
  echo " $(code -X PUT -H "x-amz-checksum-sha256: ${sum}" --data-binary 'other bytes' "${STORE_URL}/objects/t6/hello")"
  echo " $(code -X PUT --data-binary x "${STATIC_URL}/objects/t6/hello")"
  echo " $(code -X DELETE "${STORE_URL}/objects/t6/hello") $(code "${STATIC_URL}/objects/t6/hello")")
if [ "$(echo ${store})" != "200 hello, objects 400 403 204 404" ]; then
  echo "the store is not the box's bucket: want 200 hello, objects 400 403 204 404, got $(echo ${store})"
  echo "see 4-the-store.md"; exit 3
fi
echo "the store: as the box's bucket"
# And nginx, as the box's: 1 MiB a body at most, on every route
head -c $((1024 * 1024 + 1)) /dev/zero > "${work}/big.txt"
big=$(code -X POST --data-binary @"${work}/big.txt" "http://py-api.${H}/objects/new")
[ "${big}" = 413 ] || { echo "nginx took a body over 1 MiB: want 413, got ${big}"; exit 3; }
echo "nginx: 1 MiB a body"

pass=0; all=0; failed=""
expect() {
  all=$((all + 1))
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); echo "ok   $1: want $2, got $3"
  else failed="${failed} $1"; echo "FAIL $1: want $2, got ${3:-nothing}"; fi
}

# T7.1 to T7.8: the database, as test-7.sql prints them
while read -r line; do
  all=$((all + 1)); echo "${line}"
  case ${line} in ok*) pass=$((pass + 1)) ;; *) failed="${failed} $(echo "${line}" | cut -d' ' -f2 | tr -d :)" ;; esac
done < <(psql "${MIGRATOR_URL}" -X -q -t -A -c BEGIN -f test-7.sql -c ROLLBACK 2>&1 | grep -E '^(ok|FAIL) ')
[ "${all}" -ge 8 ] || { failed="${failed} sql"; echo "FAIL sql: test-7.sql did not run"; }

# O1 to O7: py-api's uploads, through nginx
tok() { make -s dev-token MOCK_URL="${MOCK_URL}" "$@"; }
Y=$(tok SUB=you EMAIL="${FIRST_ADMIN}")
A=$(tok SUB=t7-asha)
B=$(tok SUB=t7-bhanu)
for t in "${A}" "${B}"; do curl -s -o /dev/null -H "Authorization: Bearer ${t}" "http://${USERS}.${H}/users/me"; done
curl -s -o /dev/null -X PUT -H "Authorization: Bearer ${Y}" "http://${USERS}.${H}/users/people/t7-asha/roles/member"
curl -s -o /dev/null -X PUT -H "Authorization: Bearer ${Y}" "http://${USERS}.${H}/users/people/t7-bhanu/roles/reader"
head -c 4096 /dev/urandom > "${work}/bytes.txt"
up() { curl -s -w '\n%{http_code}' -X POST -H "Authorization: Bearer $1" -H "Content-Type: $2" --data-binary @"$3" "${P}/objects/new"; }
r=$(up "${A}" text/plain "${work}/bytes.txt"); key=$(echo "${r%$'\n'*}" | jq -r .key 2> /dev/null)
tag=$(printf '%s' t7-asha | sha256sum | cut -c1-16); sha=$(sha256sum "${work}/bytes.txt" | cut -c1-64)
expect T7.9 "201 objects/${tag}/${sha}" "${r##*$'\n'} ${key}"
curl -s -o "${work}/back.txt" "${STATIC_URL}/${key}"
expect T7.10 same "$(cmp -s "${work}/bytes.txt" "${work}/back.txt" && echo same || echo different)"
r=$(up "${A}" text/plain "${work}/bytes.txt")
expect T7.11 "201 ${key}" "${r##*$'\n'} $(echo "${r%$'\n'*}" | jq -r .key 2> /dev/null)"
note=$(curl -s -X POST -H "Authorization: Bearer ${A}" -H 'Content-Type: application/json' -d '{"body": "t6: with a file"}' "${P}/notes" | jq -r .id 2> /dev/null)
curl -s -o /dev/null -X PUT -H "Authorization: Bearer ${A}" -H 'Content-Type: application/json' -d "{\"keys\": [\"${key}\"]}" "${P}/notes/${note}/objects"
expect T7.12 1 "$(curl -s -H "Authorization: Bearer ${A}" "${P}/objects/mine" | jq -r --arg k "${key}" '.[] | select(.key == $k) | .refs' 2> /dev/null)"
printf '<p>hi' > "${work}/page.html"
expect T7.13 415 "$(up "${A}" text/html "${work}/page.html" | tail -1)"
expect T7.14 403 "$(up "${B}" text/plain "${work}/bytes.txt" | tail -1)"

# O7: let go, then collected after the grace
curl -s -o /dev/null -X DELETE -H "Authorization: Bearer ${A}" "${P}/notes/${note}"
every=$(sed -n 's/^COLLECT_EVERY=//p' dev/dev.env 2> /dev/null); grace=$(sed -n 's/^COLLECT_GRACE=\([0-9]*\) seconds$/\1/p' dev/dev.env 2> /dev/null)
if [ -n "${every}" ] && [ -n "${grace}" ]; then
  sleep $((every + grace + 2))
  expect T7.15 404 "$(code "${STATIC_URL}/${key}")"
else
  expect T7.15 404 "no quick collector in dev/dev.env"
fi
curl -s -o /dev/null -X DELETE -H "Authorization: Bearer ${Y}" "http://${USERS}.${H}/users/people/t7-asha/roles/member"
curl -s -o /dev/null -X DELETE -H "Authorization: Bearer ${Y}" "http://${USERS}.${H}/users/people/t7-bhanu/roles/reader"

# A1 to A3: the attachments, T7.16 to T7.18, each its own test in ui/
n=${all}
while read -r id status; do
  all=$((all + 1))
  if [ "${status}" = passed ]; then pass=$((pass + 1)); echo "ok   ${id}: the attachments"
  else failed="${failed} ${id}"; echo "FAIL ${id}: the attachments, ${status}"; fi
done < <(out=$(mktemp); (cd ui && npx vitest run test/attach.test.js --reporter=json --outputFile="${out}" > /dev/null 2>&1)
  jq -r '.testResults[].assertionResults[] | "\(.title | split(" ")[0]) \(.status)"' "${out}" 2> /dev/null | sort -V; rm -f "${out}")
[ "${all}" -gt "${n}" ] || { failed="${failed} ui"; echo "FAIL ui: ui/test/attach.test.js did not run"; }

echo "${pass} of ${all} pass"
[ -z "${failed}" ] || { echo "failed:${failed}"; exit 3; }
```

## 3 Run It Now

Before any of tutorial 7's code. Expect the two checks
of the stack to pass, then `FAIL` on every line:
`42883` or `42P01` from the database, `404` from nginx,
`FAIL ui` for the missing component, and
`0 of 15 pass`:

``` sh
./test-7.sh
```

## 4 See Also

- [The contract](2-contract.md): the step before
- [The store](4-the-store.md): the implementation's
  first part
