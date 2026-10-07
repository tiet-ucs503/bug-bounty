---
abstract: |
  Step 4 of tutorial 6: what makes the seven tests
  pass. `ui/` made a Svelte project; the starter's
  sign-in carried over; the dashboard's five
  components; then run, built and released.
date: 2026-10-07
keywords:
- tutorial
- ui
- svelte
- py-api
kind: tutorial
sources:
- ui/app.js
- services/py-api/main.py
- .github/workflows/release.yml
- Makefile
status: draft
subtitle: Step 4, the code
title: "6.4 A Svelte UI: the Implementation"
version: v0.1.0
---

## 1 Before You Start

- [The contract](2-contract.md): what the dashboard
  relies on
- [The tests](3-tests.md), saved as `test-6.sh` and
  `ui/test/dashboard.test.js`, run once and failing

## 2 Make ui/ a Svelte Project

The starter's `ui/` is two files and no build. A Svelte
UI is built, by Vite, into `ui/dist/`; the template's
release builds it when `ui/package.json` exists, and
syncs `ui/dist/` to `www`.

Remove the starter's page and script; keep the two
config examples:

``` sh
git rm ui/index.html ui/app.js
mkdir -p ui/src/lib ui/public
```

`ui/package.json`, every package by exact version.
`vitest` and `jsdom` run the dashboard's tests:

``` json
{
  "name": "ui",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "7.3.1",
    "jsdom": "30.1.2",
    "svelte": "5.57.1",
    "vite": "8.3.2",
    "vitest": "5.0.3"
  }
}
```

`ui/vite.config.js`. The last two lines are for the
tests alone: Svelte's browser build, in jsdom:

``` javascript
// The UI's build: Svelte by Vite, into ui/dist/, which a release syncs
// to www (docs/tutorials/6-a-svelte-ui/). public/ is copied as it is;
// its config.js is read at run time, never bundled
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  build: { outDir: "dist", emptyOutDir: true },
  // npm test: the components in jsdom, Svelte's browser build
  resolve: process.env.VITEST ? { conditions: ["browser"] } : undefined,
  test: { environment: "jsdom" },
});
```

`ui/index.html`, the page Vite starts from:

``` html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Notes</title>
  <link rel="icon" href="data:,">
  <script type="module" src="/src/main.js"></script>
</head>
<body>
  <div id="app"></div>
</body>
</html>
```

Then install. Expect `added` and a `package-lock.json`:

``` sh
cd ui && npm install --no-audit --no-fund && cd ..
```

## 3 The Sign-in, Carried Over

The starter's `app.js`, as a module the components
share: the same PKCE sign-in, the same `api()` that
waits out a `429` and backs off a `503`. Three
additions: `USERS`, the service that serves `/users`;
`raw`, to send a file as itself (tutorial 7); and
`staticBase`, the static bucket's address.
`ui/src/lib/box.js`:

``` javascript
// The UI's meeting with the box, from the starter's app.js: sign in
// through Cognito by the authorisation code with PKCE, then call the
// services with the access token as a Bearer. What the box asks of a UI
// (docs/ui/README.md): the APIs at https://<service>.<zone>; the access
// token, not the ID token; 429 waited for and retried; 401 a new
// sign-in.

// config.js, read at run time from the site's root: the release writes
// it from the repository's variables; locally, public/config.js
export const config = (await import(/* @vite-ignore */ new URL("config.js", `${location.origin}/`).href)).default;

const authBase = config.authDomain.includes("://") ? config.authDomain : `https://${config.authDomain}`;
const apiBase = (service) => (config.apiUrl ? config.apiUrl(service) : `https://${service}.${config.zone}`);
// The service that holds /users: py-api, or js-api if you took
// JavaScript in tutorial 4
export const USERS = "py-api";
// The static bucket's objects/, public reads (docs/tutorials/7-uploads/)
export const staticBase = config.staticUrl ?? `https://static.${config.zone}`;

const redirectUri = `${location.origin}/`;
const store = sessionStorage;

const b64url = (bytes) =>
  btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const random = (n) => b64url(crypto.getRandomValues(new Uint8Array(n)));

export const signedIn = () => Boolean(store.getItem("access_token"));

export async function signIn() {
  const verifier = random(48);
  const state = random(16);
  store.setItem("pkce_verifier", verifier);
  store.setItem("pkce_state", state);
  const challenge = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const q = new URLSearchParams({
    response_type: "code",
    client_id: config.clientId,
    redirect_uri: redirectUri,
    scope: "openid email",
    code_challenge_method: "S256",
    code_challenge: challenge,
    state,
  });
  location.assign(`${authBase}/oauth2/authorize?${q}`);
}

export function signOut() {
  store.clear();
  const q = new URLSearchParams({ client_id: config.clientId, logout_uri: redirectUri });
  location.assign(`${authBase}/logout?${q}`);
}

// Back from the sign-in: the code for tokens, the state checked, the URL
// cleaned so a reload does not replay it
export async function start() {
  const q = new URLSearchParams(location.search);
  if (!q.has("code")) return;
  history.replaceState(null, "", location.pathname);
  if (q.get("state") !== store.getItem("pkce_state")) return;
  const r = await fetch(`${authBase}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: config.clientId,
      code: q.get("code"),
      redirect_uri: redirectUri,
      code_verifier: store.getItem("pkce_verifier") ?? "",
    }),
  });
  store.removeItem("pkce_verifier");
  store.removeItem("pkce_state");
  if (!r.ok) return;
  const t = await r.json();
  store.setItem("access_token", t.access_token);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// A call to one of the services. A 429 waits for its Retry-After, a 502
// or 503 or a lost connection backs off; three tries, then the answer as
// it stands. A 401 drops the token. body is sent as JSON; raw, a File or
// Blob, as itself, with its own type
export async function api(service, path, { method = "GET", body, raw } = {}) {
  const token = store.getItem("access_token");
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (raw !== undefined) headers["Content-Type"] = raw.type || "application/octet-stream";
  const payload = raw ?? (body === undefined ? undefined : JSON.stringify(body));
  for (let attempt = 1; ; attempt++) {
    let r;
    try {
      r = await fetch(`${apiBase(service)}${path}`, { method, headers, body: payload });
    } catch (e) {
      if (attempt >= 3) throw e;
      await sleep(500 * 2 ** attempt);
      continue;
    }
    if (r.status === 429 && attempt < 3) {
      await sleep((Number(r.headers.get("Retry-After")) || 1) * 1000 + Math.random() * 500);
      continue;
    }
    if ((r.status === 502 || r.status === 503) && attempt < 3) {
      await sleep(500 * 2 ** attempt);
      continue;
    }
    if (r.status === 401) store.removeItem("access_token");
    const text = await r.text();
    let data = text;
    try {
      data = JSON.parse(text);
    } catch {}
    return { status: r.status, data };
  }
}
```

`config.js` is read **at run time**, from the site's
root, never bundled. `/* @vite-ignore */` tells Vite to
leave the import alone.

`ui/src/main.js`, which finishes a sign-in before the
page draws:

``` javascript
import { mount } from "svelte";
import App from "./App.svelte";
import { start } from "./lib/box.js";
import "./app.css";

// The sign-in's callback first, so the page renders signed in
await start();
mount(App, { target: document.getElementById("app") });
```

`ui/src/app.css`, the starter's look:

``` css
:root { --bg: #fff; --fg: #1d1d1f; --muted: #6e6e73; --line: #d2d2d7; --accent: #0a66c2; --bad: #b42318; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161617; --fg: #f5f5f7; --muted: #a1a1a6; --line: #3a3a3c; --accent: #4c9aff; --bad: #f97066; }
}
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; }
main { max-width: 44rem; margin: 0 auto; padding: 2rem 1rem; }
h1 { font-size: 1.4rem; margin: 0 0 .25rem; }
h2 { font-size: 1.1rem; margin: 2rem 0 .5rem; }
.muted { color: var(--muted); }
.bad { color: var(--bad); }
.row { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; margin: .5rem 0; }
button { font: inherit; padding: .35rem .75rem; border: 1px solid var(--line); border-radius: .4rem;
         background: transparent; color: var(--fg); cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
textarea { font: inherit; width: 100%; box-sizing: border-box; padding: .5rem; border: 1px solid var(--line);
           border-radius: .4rem; background: transparent; color: var(--fg); min-height: 4rem; }
ul.plain { list-style: none; padding: 0; margin: 0; }
li.card { border: 1px solid var(--line); border-radius: .5rem; padding: .75rem; margin: .5rem 0; }
.chip { font-size: .85rem; border: 1px solid var(--line); border-radius: 1rem; padding: 0 .5rem; }
```

## 4 The Dashboard

`ui/src/App.svelte`: what `/users/me` answers decides
what the page shows (D1 to D3):

``` svelte
<script>
  // The dashboard: who you are, by /users/me, which records you; your
  // profile; the notes, by py-api; the people and their roles, if you
  // may read them
  import { USERS, api, signIn, signOut, signedIn } from "./lib/box.js";
  import Notes from "./Notes.svelte";
  import People from "./People.svelte";
  import Profile from "./Profile.svelte";

  let me = $state(null);
  let refused = $state("");

  async function load() {
    const r = await api(USERS, "/users/me");
    if (r.status === 200) me = r.data;
    else refused = r.status === 403 ? `E-mail not verified: ${r.data.email || "no e-mail"}` : `users: ${r.status}`;
  }

  const may = (p) => me?.permissions.includes(p) ?? false;

  if (signedIn()) load();
</script>

<main>
  <h1>Notes</h1>
  {#if !signedIn()}
    <p class="muted">Not signed in</p>
    <button class="primary" onclick={signIn}>Sign in</button>
  {:else if refused}
    <p class="bad">{refused}</p>
    <button onclick={signOut}>Sign out</button>
  {:else if me}
    <div class="row">
      <span class="muted">Signed in as {me.profile.display_name || me.email}</span>
      {#each me.roles as role}<span class="chip">{role}</span>{/each}
      <button onclick={signOut}>Sign out</button>
    </div>
    {#if me.permissions.length === 0}
      <p class="muted">You are signed in, with no role yet: ask an admin for one.</p>
    {/if}
    <Profile {me} />
    {#if may("notes.read")}
      <Notes canWrite={may("notes.write")} />
    {/if}
    {#if may("users.read")}
      <People canGrant={may("users.grant")} />
    {/if}
  {:else}
    <p class="muted">…</p>
  {/if}
</main>
```

`ui/src/Profile.svelte`: your own profile, saved by
`PUT /users/me/profile` (D6). Its fields are the
profile's columns of tutorial 1; change both together:

``` svelte
<script>
  // Your own profile: what the project keeps of you beyond the sign-in.
  // Its fields are the project's own (docs/tutorials/1-authentication.md)
  import { untrack } from "svelte";
  import { USERS, api } from "./lib/box.js";

  let { me } = $props();
  // The form's starting values, taken once; then the form's own
  let name = $state(untrack(() => me.profile.display_name));
  let affiliation = $state(untrack(() => me.profile.affiliation));
  let note = $state("");

  async function save(event) {
    event.preventDefault();
    const r = await api(USERS, "/users/me/profile", { method: "PUT", body: { display_name: name, affiliation } });
    note = r.status === 200 ? "Saved" : (r.data.error ?? `users: ${r.status}`);
  }
</script>

<h2>Profile</h2>
<form class="row" onsubmit={save}>
  <input aria-label="Display name" placeholder="Display name" maxlength="80" bind:value={name} />
  <input aria-label="Affiliation" placeholder="Affiliation" maxlength="120" bind:value={affiliation} />
  <button class="primary">Save</button>
  {#if note}<span class="muted">{note}</span>{/if}
</form>
```

`ui/src/Notes.svelte`: every note; the add box and the
buttons only where the permissions and the owner allow
(D4):

``` svelte
<script>
  // Every note, (u=rw, a=r): yours to change, the rest to read. The
  // buttons follow the permissions; the database decides regardless
  import { api } from "./lib/box.js";

  let { canWrite } = $props();
  let notes = $state([]);
  let draft = $state("");
  let editing = $state(null);
  let error = $state("");

  async function load() {
    const r = await api("py-api", "/notes");
    if (r.status === 200) notes = r.data;
    else error = r.data.error ?? `py-api: ${r.status}`;
  }

  async function call(path, opts) {
    error = "";
    const r = await api("py-api", path, opts);
    if (r.status >= 400) error = r.data.error ?? `py-api: ${r.status}`;
    await load();
    return r.status < 400;
  }

  async function add() {
    if (await call("/notes", { method: "POST", body: { body: draft } })) draft = "";
  }

  async function save() {
    if (await call(`/notes/${editing.id}`, { method: "PUT", body: { body: editing.body } })) editing = null;
  }

  load();
</script>

<h2>Notes</h2>
{#if error}<p class="bad">{error}</p>{/if}
{#if canWrite}
  <textarea bind:value={draft} placeholder="A new note" aria-label="A new note"></textarea>
  <div class="row"><button class="primary" onclick={add} disabled={!draft.trim()}>Add</button></div>
{/if}
<ul class="plain">
  {#each notes as note (note.id)}
    <li class="card">
      {#if editing?.id === note.id}
        <textarea bind:value={editing.body} aria-label="Edit the note"></textarea>
        <div class="row">
          <button class="primary" onclick={save}>Save</button>
          <button onclick={() => (editing = null)}>Cancel</button>
        </div>
      {:else}
        <div>{note.body}</div>
        <div class="row muted">
          <span>{note.mine ? "yours" : "another's"}, {new Date(note.created_at).toLocaleString()}</span>
          {#if note.mine && canWrite}
            <button onclick={() => (editing = { id: note.id, body: note.body })}>Edit</button>
            <button onclick={() => call(`/notes/${note.id}`, { method: "DELETE" })}>Delete</button>
          {/if}
        </div>
      {/if}
    </li>
  {:else}
    <li class="muted">No notes yet.</li>
  {/each}
</ul>
```

`ui/src/People.svelte`: a checkbox a role, its
permissions in its tooltip (D5):

``` svelte
<script>
  // The people signed in and their roles, users.read; a role given or
  // taken, users.grant. The matrix says what each role may do
  import { USERS, api } from "./lib/box.js";

  let { canGrant } = $props();
  let people = $state([]);
  let roles = $state([]);
  let error = $state("");

  async function load() {
    const [p, r] = await Promise.all([api(USERS, "/users/people"), api(USERS, "/users/roles")]);
    if (p.status === 200) people = p.data;
    if (r.status === 200) roles = r.data;
  }

  async function toggle(person, role) {
    error = "";
    const has = person.roles.includes(role);
    const r = await api(USERS, `/users/people/${encodeURIComponent(person.sub)}/roles/${role}`, { method: has ? "DELETE" : "PUT" });
    if (r.status >= 400) error = r.data.error ?? `users: ${r.status}`;
    await load();
  }

  load();
</script>

<h2>People</h2>
{#if error}<p class="bad">{error}</p>{/if}
<ul class="plain">
  {#each people as person (person.sub)}
    <li class="card">
      <div>{person.email}</div>
      <div class="row">
        {#each roles as r (r.role)}
          <label class="chip" title={r.permissions.join(", ") || "nothing"}>
            <input type="checkbox" checked={person.roles.includes(r.role)} disabled={!canGrant}
                   onchange={() => toggle(person, r.role)} />
            {r.role}
          </label>
        {/each}
      </div>
    </li>
  {/each}
</ul>
```

Run the tests: `./test-6.sh`, or the dashboard's alone,
`cd ui && npm test`.

## 5 Run It

The config for your stack, into `ui/public/`, which
Vite serves at the root. For the dev stack:

``` sh
cp ui/config.dev.example.js ui/public/config.js
make ui
```

For the native stack, with your own ports:

``` sh
cp dev/out/native/config.js ui/public/config.js
make ui UI_PORT=${UI_PORT}
```

Open `http://localhost:5173/`, or your `UI_PORT`. Then,
in turn:

1.  **Sign in as `you`,** `you@example.org`: `admin`,
    and the people; no notes, since `admin` does not
    read them
2.  **Sign out, and in as `zed`:** signed in, no role,
    and the profile alone. Fill in a display name, and
    save
3.  **As `you` again,** tick `reader` for zed
4.  **As `zed`:** the notes, to read, no add box; the
    header by the name you saved
5.  **As `asha`,** a member: add a note, edit it,
    delete it. Another's note has no buttons

## 6 Build and Release

Expect `dist/index.html` and `built in`:

``` sh
cd ui && npm run build && cd ..
```

`ui/dist/` is what a release syncs to `www`, with a
`config.js` written beside it from the repository's
variables; `ui/public/config.js` and `ui/dist/` are
ignored by git. A tag whose changes include `ui/` does
it ([Release the UI](../../ui/release.md)); CI builds
the UI on every push, so a broken build fails before a
tag.

## 7 See Also

- [The refinement](5-refinement.md): next
- [Svelte](https://svelte.dev/docs/svelte/overview),
  [Vite](https://vite.dev/guide/) and
  [Vitest](https://vitest.dev/guide/), read 2026-10-07
