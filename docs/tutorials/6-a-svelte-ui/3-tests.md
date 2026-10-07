---
abstract: |
  Step 3 of tutorial 6: the concept's ten rules as
  thirteen tests. Six call the notes through nginx;
  seven draw the dashboard in `ui/`'s own tests. One
  script runs both. Run it now, and every test fails.
date: 2026-10-07
keywords:
- tutorial
- ui
- tests
kind: reference
sources:
- services/py-api/main.py
- ui/app.js
status: draft
subtitle: Step 3, how we measure it
title: "6.3 A Svelte UI: the Tests"
version: v0.1.0
---

## 1 From the Rules to the Tests

Each rule of [the concept](1-concept.md), held to [the
contract](2-contract.md). The notes, with two people:
`t5-asha`, a member, and `t5-bhanu`, a reader and then
a member too:

- **T6.1, N1:** `t5-asha` writes a note? Expect `201`
- **T6.2, N1:** is it hers? Expect `200 true`
- **T6.3, N2:** `t5-bhanu` reads it: does he see it, as
  not his? Expect `200 true`
- **T6.4, N2:** `t5-bhanu`, a reader, writes one?
  Expect `403`
- **T6.5, N3:** `t5-bhanu`, a member now, edits hers?
  Expect `403 not your note`
- **T6.6, N4:** an empty note? Expect `422`

The dashboard, drawn with what `/users/me` answers
replaced by each case:

- **T6.7, D1:** signed out: a button `Sign in`, and no
  call made
- **T6.8, D2:** `403` from `/users/me`: the words
  `E-mail not verified`, and the address
- **T6.9, D3:** no permission: `with no role yet`, and
  no section but the profile
- **T6.10, D4:** `notes.read` alone: the notes, and no
  box to write in
- **T6.11, D4:** `notes.write` too: the box, and
  buttons on her own note alone
- **T6.12, D5:** `users.read`: the people, their
  checkboxes disabled; with `users.grant`, enabled
- **T6.13, D6:** the display name in the header; a
  change saved by `PUT /users/me/profile` as typed

## 2 The Dashboard's Tests

In `ui/test/dashboard.test.js`. Vitest runs them in
jsdom, a browser's document without a browser; `box.js`
is replaced, so there is no sign-in and no network.
They need the Svelte project of [the
implementation](4-implementation.md) §3 to run:

``` javascript
// Tutorial 6's tests of the dashboard, T6.7 to T6.13: what each person
// sees, by what /users/me answers. The components in jsdom; box.js
// replaced, so no sign-in and no network. `npm test`
import { test, expect, vi, beforeEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";

vi.mock("../src/lib/box.js", () => ({
  USERS: "py-api",
  staticBase: "",
  api: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
  signedIn: vi.fn(),
}));
const box = await import("../src/lib/box.js");
const { default: App } = await import("../src/App.svelte");

const me = (permissions, roles = []) => ({
  sub: "asha", email: "asha@example.org", provider: "Google",
  profile: { display_name: "", affiliation: "" }, roles, permissions,
});
const NOTES = [
  { id: 2, body: "mine", mine: true, created_at: "2026-10-07T10:00:00Z", updated_at: null },
  { id: 1, body: "theirs", mine: false, created_at: "2026-10-07T09:00:00Z", updated_at: null },
];

// The answers, by path; anything else 404
function answer(routes) {
  box.api.mockImplementation(async (service, path, opts = {}) => {
    const r = routes[`${opts.method ?? "GET"} ${path}`];
    return r ? { status: r[0], data: r[1] } : { status: 404, data: { error: "no route" } };
  });
}

let app;
async function show() {
  app = mount(App, { target: document.body });
  for (let i = 0; i < 5; i++) await tick();
  flushSync();
  return document.body;
}

beforeEach(() => {
  if (app) unmount(app);
  app = null;
  document.body.innerHTML = "";
  vi.clearAllMocks();
  box.signedIn.mockReturnValue(true);
});

test("T6.7 signed out: a button to sign in, and nothing asked", async () => {
  box.signedIn.mockReturnValue(false);
  const page = await show();
  expect(page.querySelector("button")?.textContent).toBe("Sign in");
  expect(box.api).not.toHaveBeenCalled();
});

test("T6.8 an unverified e-mail: refused, by name", async () => {
  answer({ "GET /users/me": [403, { error: "e-mail not verified", email: "esha@example.org" }] });
  expect((await show()).textContent).toContain("E-mail not verified: esha@example.org");
});

test("T6.9 no role: told so, and no notes or people", async () => {
  answer({ "GET /users/me": [200, me([])] });
  const page = await show();
  expect(page.textContent).toContain("with no role yet");
  expect([...page.querySelectorAll("h2")].map((h) => h.textContent)).toEqual(["Profile"]);
});

test("T6.10 a reader: the notes, and nothing to write with", async () => {
  answer({ "GET /users/me": [200, me(["notes.read"], ["reader"])], "GET /notes": [200, NOTES] });
  const page = await show();
  expect(page.textContent).toContain("theirs");
  expect(page.querySelector("textarea")).toBeNull();
});

test("T6.11 a member: a note to add, and buttons on their own alone", async () => {
  answer({ "GET /users/me": [200, me(["notes.read", "notes.write"], ["member"])], "GET /notes": [200, NOTES] });
  const page = await show();
  expect(page.querySelector("textarea")).not.toBeNull();
  const cards = [...page.querySelectorAll("li.card")];
  expect(cards.map((c) => c.querySelectorAll("button").length > 0)).toEqual([true, false]);
});

test("T6.12 the people: shown to users.read, changed by users.grant alone", async () => {
  const people = [[200, [{ sub: "asha", email: "asha@example.org", roles: [] }]],
    [200, [{ role: "reader", about: "", permissions: ["notes.read"] }]]];
  answer({ "GET /users/me": [200, me(["users.read"])], "GET /users/people": people[0], "GET /users/roles": people[1] });
  let box1 = (await show()).querySelector("input[type=checkbox]");
  expect(box1.disabled).toBe(true);
  unmount(app);
  document.body.innerHTML = "";
  answer({ "GET /users/me": [200, me(["users.read", "users.grant"])], "GET /users/people": people[0], "GET /users/roles": people[1] });
  box1 = (await show()).querySelector("input[type=checkbox]");
  expect(box1.disabled).toBe(false);
});

test("T6.13 the profile: shown, and saved as typed", async () => {
  const mine = me([]);
  mine.profile = { display_name: "Asha", affiliation: "" };
  answer({ "GET /users/me": [200, mine], "PUT /users/me/profile": [200, mine] });
  const page = await show();
  expect(page.textContent).toContain("Signed in as Asha");
  const [name, affiliation] = page.querySelectorAll("form input");
  affiliation.value = "Physics";
  affiliation.dispatchEvent(new Event("input"));
  page.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await tick();
  expect(box.api).toHaveBeenCalledWith("py-api", "/users/me/profile",
    { method: "PUT", body: { display_name: "Asha", affiliation: "Physics" } });
  expect(name.value).toBe("Asha");
});
```

## 3 The Script

Save it as `test-6.sh` at your fork's root, and make it
runnable. `USERS` is the service that serves `/users`,
`py-api` unless you set it. It gives roles, and takes
them back with the note it adds; then it runs `ui/`'s
tests and counts each as one of its own:

``` sh
#!/usr/bin/env bash
# Tutorial 6's tests, T6.1 to T6.13: py-api's notes through nginx, as
# the dashboard calls them, then the dashboard itself, by ui/'s npm
# test. Run from your fork's root, with H and MOCK_URL set, and USERS
# the service that serves /users. It gives t5-asha and t5-bhanu roles,
# and takes them back with the note it adds
set -uo pipefail
USERS=${USERS:-py-api}
FIRST_ADMIN=${FIRST_ADMIN:-you@example.org}

tok() { make -s dev-token MOCK_URL="${MOCK_URL}" "$@"; }
Y=$(tok SUB=you EMAIL="${FIRST_ADMIN}")
A=$(tok SUB=t5-asha)
B=$(tok SUB=t5-bhanu)

# call SERVICE METHOD PATH TOKEN [BODY] [JQ]: the status, and what JQ picks
call() {
  local out code
  out=$(curl -s -w '\n%{http_code}' -X "$2" -H "Authorization: Bearer $4" \
    ${5:+-H 'Content-Type: application/json' -d "$5"} "http://$1.${H}$3")
  code=${out##*$'\n'}
  if [ -n "${6:-}" ]; then echo "${code} $(echo "${out%$'\n'*}" | jq -rc "$6" 2> /dev/null)"; else echo "${code}"; fi
}

pass=0; all=0; failed=""
expect() {
  all=$((all + 1))
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); echo "ok   $1: want $2, got $3"
  else failed="${failed} $1"; echo "FAIL $1: want $2, got ${3:-nothing}"; fi
}

# Both seen, asha a member and bhanu a reader
call "${USERS}" GET /users/me "${A}" > /dev/null
call "${USERS}" GET /users/me "${B}" > /dev/null
call "${USERS}" PUT /users/people/t5-asha/roles/member "${Y}" > /dev/null
call "${USERS}" PUT /users/people/t5-bhanu/roles/reader "${Y}" > /dev/null

# N1: a member writes a note, and it is hers
note=$(call py-api POST /notes "${A}" '{"body": "t5: a first note"}' '.id')
expect T6.1 201 "${note%% *}"
id=${note#* }
expect T6.2 "200 true" "$(call py-api GET /notes "${A}" '' "any(.[]; .id == ${id:-0} and .mine)")"
# N2: a reader reads it, and learns it is not hers
expect T6.3 "200 true" "$(call py-api GET /notes "${B}" '' "any(.[]; .id == ${id:-0} and (.mine | not))")"
expect T6.4 403 "$(call py-api POST /notes "${B}" '{"body": "t5: not mine to write"}')"
# N3: another member may not change it
call "${USERS}" PUT /users/people/t5-bhanu/roles/member "${Y}" > /dev/null
expect T6.5 "403 not your note" "$(call py-api PUT "/notes/${id:-0}" "${B}" '{"body": "t5: bhanu was here"}' '.error')"
# N4: a body of 1 to 10,000 characters
expect T6.6 422 "$(call py-api POST /notes "${A}" '{"body": ""}')"

call py-api DELETE "/notes/${id:-0}" "${A}" > /dev/null
call "${USERS}" DELETE /users/people/t5-asha/roles/member "${Y}" > /dev/null
for r in reader member; do call "${USERS}" DELETE "/users/people/t5-bhanu/roles/${r}" "${Y}" > /dev/null; done

# D1 to D5: the dashboard, T6.7 to T6.13, each its own test in ui/
while read -r id status; do
  all=$((all + 1))
  if [ "${status}" = passed ]; then pass=$((pass + 1)); echo "ok   ${id}: the dashboard"
  else failed="${failed} ${id}"; echo "FAIL ${id}: the dashboard, ${status}"; fi
done < <(out=$(mktemp); (cd ui && npx vitest run test/dashboard.test.js --reporter=json --outputFile="${out}" > /dev/null 2>&1)
  jq -r '.testResults[].assertionResults[] | "\(.title | split(" ")[0]) \(.status)"' "${out}" | sort -V; rm -f "${out}")
[ "${all}" -ge 13 ] || { failed="${failed} ui"; echo "FAIL ui: npm test in ui/ did not run"; }

echo "${pass} of ${all} pass"
[ -z "${failed}" ] || { echo "failed:${failed}"; exit 3; }
```

## 4 Run It Now

Before any of tutorial 6's code, nginx knows no
`/notes` route, and `ui/` is the starter, with no tests
to run. Expect `FAIL` on every line, the notes with
`got 404`, then `FAIL ui`, and `0 of 6 pass`:

``` sh
./test-6.sh
```

## 5 See Also

- [The contract](2-contract.md): the step before
- [The implementation](4-implementation.md): what makes
  these pass
