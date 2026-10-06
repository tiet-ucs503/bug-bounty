---
abstract: |
  `/users` as routes of js-api, at
  `js-api.<zone>/users`: the same routes as tutorial
  4's Python, the same database, the same refusals.
  Fastify, jose and node-postgres, a plugin with its
  own hooks, tests that need no database, and the
  routes run behind the stack's nginx.
date: 2026-10-06
keywords:
- tutorial
- js-api
- node
- auth
- authz
- db
kind: tutorial
sources:
- services/js-api/server.js
- services/js-api/package.json
- box/project.json
status: draft
subtitle: Fastify, node-postgres, and the database
  deciding
title: 5 /users in JavaScript, in js-api
version: v0.1.0
---

`[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](README.md) §5.

## 1 Before You Start

- [What you need](README.md) §2, installed and checked
- [3 Make it a migration](3-the-migration.md), its
  migrations applied, with `users` among js-api's
  `prefixes` (§2 there)
- The Python version is [tutorial
  4](4-users-in-python.md): the same routes, in py-api;
  take one

## 2 The Routes

Tutorial 4's, §2, the same five under `/users`, but in
js-api's `routes` in the manifest, after the starter's
three. They answer at `js-api.<zone>/users`: the same
host, image and process as js-api's own routes.

## 3 Its Package

`pg`, node-postgres, by exact version, in
`services/js-api/`. Expect `added` and a changed
`package-lock.json`:

``` sh
cd services/js-api && npm install --save-exact --no-audit --no-fund pg@8.23.1 && cd ../..
```

`make check` holds the lockfile to `package.json`.

## 4 The Code

`services/js-api/server.js`, whole, as this page leaves
it: the starter, and what `/users` adds.

``` javascript
// A starter service in JavaScript, at js-api.<your zone>. The
// starter's three routes show the shape every service keeps; the rest
// are yours.
//
//   GET  /health   the box's and the probes' check; keep it
//   GET  /hello    anyone
//   POST /echo     a signed-in caller: the body back, with who sent it
//
// and who comes in, and what each may do, the database deciding
// (docs/tutorials/5-users-in-javascript.md):
//
//   GET    /users/me                          the door: admits the caller
//                                             if the rules let them in,
//                                             then says who they are and
//                                             what they may do
//   GET    /users/people                      everyone admitted: users.read
//   GET    /users/roles                       the matrix: users.read
//   PUT    /users/people/{sub}/roles/{role}   give a role: users.grant
//   DELETE /users/people/{sub}/roles/{role}   take it away: users.grant
//
// In front of this process, the box's nginx (rendered from
// box/project.json, docs/onboarding/README.md):
//   - an allow-list: a route added here is unreachable until
//     box/project.json names it, and the box's owner rolls it out;
//   - CORS for your www alone, and the rate of writes;
// so this process does neither.
//
// Who the caller is, this service decides itself: a Bearer access token
// from the box's Cognito pool, issued to your project's UI client or the
// box's probe client, verified against the pool's keys. What the caller
// may then do, the project's database decides: every accessor takes
// the caller first, and its refusals by SQLSTATE become 403, 404 and
// 409 here.

import Fastify from "fastify";
import { createRemoteJWKSet, jwtVerify } from "jose";
import pg from "pg";

const PORT = Number(process.env.PORT ?? 3000);
// Every address in a container; 127.0.0.1 alone when run as a program
// on a shared machine (tools/native-dev.sh)
const HOST = process.env.HOST ?? "0.0.0.0";
const SERVICE = process.env.SERVICE ?? "js-api";

// From the env file the box writes for your project at upload, from
// its Terraform's outputs. Unset, no token is accepted
const ISSUER = process.env.COGNITO_ISSUER ?? "";
const CLIENTS = [process.env.COGNITO_UI_CLIENT_ID, process.env.COGNITO_PROBE_CLIENT_ID].filter(Boolean);
// Cognito's userInfo, which answers a caller's e-mail to their own
// token: an access token carries none
const USERINFO = process.env.COGNITO_USERINFO_URL ?? "";

// The pool's keys, fetched on first use and cached; an unknown key ID
// refetches at most every 30 s, jose's cooldown, so a forged token
// cannot make this process fetch on every request
const keys = ISSUER ? createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks.json`)) : null;

// The caller, if the token is the pool's access token for one of our
// clients and unexpired; null otherwise. Cognito's access tokens carry
// client_id, not aud
export async function caller(header) {
  if (!keys || CLIENTS.length === 0) return null;
  const m = /^Bearer ([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)$/.exec(header ?? "");
  if (!m) return null;
  try {
    const { payload } = await jwtVerify(m[1], keys, { issuer: ISSUER, algorithms: ["RS256"] });
    if (payload.token_use !== "access" || !CLIENTS.includes(payload.client_id)) return null;
    return { sub: payload.sub, groups: payload["cognito:groups"] ?? [], token: m[1] };
  } catch {
    return null;
  }
}

// userInfo's answer for each sub, kept ten minutes: Cognito limits how
// often it may be asked, and an e-mail seldom changes
const EMAIL_FOR = 600_000;
const emails = new Map();

// The caller's e-mail and whether it is verified, from userInfo by
// their own token. Cognito answers email_verified as a string
export async function emailOf(who) {
  const hit = emails.get(who.sub);
  if (hit && Date.now() - hit.at < EMAIL_FOR) return hit;
  if (!USERINFO) return { email: "", verified: false };
  const r = await fetch(USERINFO, { headers: { Authorization: `Bearer ${who.token}` }, signal: AbortSignal.timeout(5000) });
  if (!r.ok) throw new Error(`userInfo: ${r.status}`);
  const info = await r.json();
  if (info.sub !== who.sub) return { email: "", verified: false };
  const out = { at: Date.now(), email: info.email ?? "", verified: String(info.email_verified).toLowerCase() === "true" };
  emails.set(who.sub, out);
  return out;
}

// The project's database, as its app login. Nothing connects until the
// first query, so the service starts, and answers /health, whether or
// not it is up
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 4, connectionTimeoutMillis: 5000 });

// One statement, its rows; the tests replace it
export const db = { query: async (sql, args) => (await pool.query(sql, args)).rows };

// The database's refusals, by SQLSTATE, as HTTP
const STATUS = { 42501: 403, P0002: 404, 23001: 409, 23514: 400, 22001: 400 };

// /users: who may come in, and what each person may do; the database
// decides. A plugin, so its hook and its error handler are its own
async function users(app) {
  // Every answer here is the caller's own: never cached
  app.addHook("onSend", async (req, reply) => {
    reply.header("Cache-Control", "no-store");
  });

  // The accessor's refusal as an answer; any other failure, 503 if the
  // database cannot be reached, else Fastify's 500
  app.setErrorHandler((err, req, reply) => {
    if (STATUS[err.code]) return reply.code(STATUS[err.code]).send({ error: err.message });
    if (err.code === "ECONNREFUSED" || /timeout/i.test(err.message)) {
      req.log.error(err);
      return reply.code(503).send({ error: "the database is not answering" });
    }
    throw err;
  });

  // Every route here: a signed-in caller, or 401
  app.addHook("preHandler", async (req, reply) => {
    req.who = await caller(req.headers.authorization);
    if (!req.who) {
      reply.header("WWW-Authenticate", 'Bearer realm="js-api"');
      return reply.code(401).send({ error: "sign in first" });
    }
  });

  app.get("/me", async (req, reply) => {
    let who;
    try {
      who = await emailOf(req.who);
    } catch {
      return reply.code(503).send({ error: "Cognito's userInfo is not answering" });
    }
    const [{ admitted }] = await db.query("SELECT users_admit($1, $2, $3) AS admitted", [req.who.sub, who.email, who.verified]);
    if (!admitted) return reply.code(403).send({ error: "not admitted", email: who.email, verified: who.verified });
    return (await db.query("SELECT * FROM users_me($1)", [req.who.sub]))[0];
  });

  app.get("/people", async (req) => db.query("SELECT * FROM users_list($1)", [req.who.sub]));

  app.get("/roles", async (req) => db.query("SELECT * FROM users_matrix($1)", [req.who.sub]));

  app.put("/people/:sub/roles/:role", async (req) => {
    const { sub, role } = req.params;
    await db.query("SELECT users_grant($1, $2, $3)", [req.who.sub, sub, role]);
    return { sub, role, granted: true };
  });

  app.delete("/people/:sub/roles/:role", async (req) => {
    const { sub, role } = req.params;
    await db.query("SELECT users_revoke($1, $2, $3)", [req.who.sub, sub, role]);
    return { sub, role, granted: false };
  });
}

// 1 MiB, as nginx's client_max_body_size for the host. The log is
// JSON on stdout, which Docker's awslogs driver sends on; Fastify's
// request lines carry no header, so no token reaches the log
export function build() {
  const app = Fastify({ logger: true, bodyLimit: 1024 * 1024 });

  app.get("/health", async () => ({ status: "ok", service: SERVICE }));

  app.get("/hello", async () => ({ message: `hello from ${SERVICE}` }));

  app.post("/echo", async (req, reply) => {
    reply.header("Cache-Control", "no-store");
    const who = await caller(req.headers.authorization);
    if (!who) {
      reply.header("WWW-Authenticate", 'Bearer realm="js-api"');
      return reply.code(401).send({ error: "sign in first" });
    }
    return { service: SERVICE, caller: who.sub, groups: who.groups, body: req.body ?? null };
  });

  app.register(users, { prefix: "/users" });

  return app;
}

// Started as a program, not when a test imports it. SIGTERM from
// `docker compose` closes the server and lets requests in flight end
if (import.meta.url === `file://${process.argv[1]}`) {
  const app = build();
  for (const s of ["SIGTERM", "SIGINT"]) {
    process.on(s, () => app.close().then(() => pool.end()).then(() => process.exit(0)));
  }
  await app.listen({ host: HOST, port: PORT });
}
```

What it adds to the starter:

- **`USERINFO`:** Cognito's userInfo, from
  `COGNITO_USERINFO_URL`
- **`caller`:** the starter's check of the token,
  keeping the token itself, which userInfo needs
- **`emailOf`:** asks userInfo with the caller's own
  token, with a five-second timeout, keeps the answer
  ten minutes, and reads `email_verified` as the string
  it is
- **`pool`:** node-postgres connects at the first
  query, not at start: the service answers `/health`
  with the database down
- **`db.query`:** one statement, its rows; the tests
  replace it
- **`users`, a Fastify plugin,** registered with the
  prefix `/users`. Fastify keeps a plugin's hooks and
  error handler to its own routes, so the starter's
  three answer as they did:
  - **its error handler:** node-postgres puts the
    SQLSTATE in `err.code`; `STATUS` turns a refusal
    into HTTP with its message. An unreachable database
    is `503`; anything else, Fastify's `500`
  - **a `preHandler` hook:** the token, on every route
    of the plugin, so none can forget it
  - **an `onSend` hook:** `Cache-Control: no-store`, as
    each answer is the caller's own
- **The shutdown** ends the pool after the server

## 5 Its Tests

Each test file runs in a process of its own, so this
one sets the pool's address before it imports
`server.js`. `services/js-api/test/users.test.js`:

``` javascript
// /users: the token check and the door, against a pool of our own: a
// key pair made here, its public half served as the pool's JWKS, and a
// userInfo, on a local port. The database is replaced by a function
// that answers as the accessors would. `npm test`, which runs each file
// in a process of its own; nothing leaves the machine
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { SignJWT, decodeJwt, exportJWK, generateKeyPair } from "jose";

const EMAILS = { alice: ["alice@example.org", "true"], eve: ["eve@example.org", "false"] };
let pool, issuer, sign, app, server;

// A refusal as node-postgres raises one, with its SQLSTATE
const refused = (code, message) => Object.assign(new Error(message), { code });

before(async () => {
  const { publicKey, privateKey } = await generateKeyPair("RS256");
  const jwk = { ...(await exportJWK(publicKey)), kid: "k1", alg: "RS256", use: "sig" };
  pool = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");
    if (req.url === "/.well-known/jwks.json") return res.end(JSON.stringify({ keys: [jwk] }));
    const { sub } = decodeJwt(req.headers.authorization.slice(7));
    res.end(JSON.stringify({ sub, email: EMAILS[sub][0], email_verified: EMAILS[sub][1] }));
  });
  await new Promise((r) => pool.listen(0, "127.0.0.1", r));
  issuer = `http://127.0.0.1:${pool.address().port}`;
  sign = (sub, claims = {}) =>
    new SignJWT({ token_use: "access", client_id: "ui-client", ...claims }).setProtectedHeader({ alg: "RS256", kid: "k1" })
      .setIssuer(issuer).setSubject(sub).setIssuedAt().setExpirationTime("5m").sign(privateKey);

  process.env.COGNITO_ISSUER = issuer;
  process.env.COGNITO_UI_CLIENT_ID = "ui-client";
  process.env.COGNITO_PROBE_CLIENT_ID = "probe-client";
  process.env.COGNITO_USERINFO_URL = `${issuer}/oauth2/userInfo`;
  server = await import("../server.js");
  server.db.query = async (sql, args) => {
    if (sql.startsWith("SELECT users_admit")) return [{ admitted: args[2] && args[1].endsWith("@example.org") }];
    if (sql.startsWith("SELECT * FROM users_me")) return [{ sub: args[0], roles: ["deny-all"], permissions: [] }];
    if (sql.startsWith("SELECT * FROM users_list")) throw refused("42501", "users.read needed");
    if (sql.startsWith("SELECT users_revoke")) throw refused("23001", "the last users.grant");
    throw new Error(sql);
  };
  app = server.build();
});

after(async () => {
  await app.close();
  pool.close();
});

const get = async (url, sub, claims) =>
  app.inject({ url, headers: sub ? { authorization: `Bearer ${await sign(sub, claims)}` } : {} });

test("the door refuses no token and another client's", async () => {
  assert.equal((await get("/users/me")).statusCode, 401);
  assert.equal((await get("/users/me", "alice", { client_id: "neighbour" })).statusCode, 401);
});

test("the door admits a verified e-mail the rules match", async () => {
  const r = await get("/users/me", "alice");
  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json().roles, ["deny-all"]);
  assert.equal(r.headers["cache-control"], "no-store");
});

test("the door refuses an unverified e-mail", async () => {
  const r = await get("/users/me", "eve");
  assert.deepEqual([r.statusCode, r.json().error], [403, "not admitted"]);
});

test("the database's refusals become 403 and 409", async () => {
  assert.equal((await get("/users/people", "alice")).statusCode, 403);
  const r = await app.inject({ method: "DELETE", url: "/users/people/alice/roles/admin",
    headers: { authorization: `Bearer ${await sign("alice")}` } });
  assert.equal(r.statusCode, 409);
});

test("the starter's routes keep their own answers", async () => {
  const r = await app.inject("/health");
  assert.deepEqual(r.json(), { status: "ok", service: "js-api" });
  assert.equal(r.headers["cache-control"], undefined);
});
```

The last test holds the plugin to its own routes:
`/health` answers as the starter's, without `no-store`.
Expect `pass 9` for js-api, the starter's four tests
and these five:

``` sh
make test
```

## 6 Run It, and Call It

As tutorial 4's §6 and §7, with `js-api` for `py-api`:
`js-api health 200`, then the same calls at
`http://js-api.${H}/users/...`, and the same answers.
On the dev stack, `make dev` builds it; on the native
stack, `stop`, `init` and `start`, where `init`
installs its packages with `npm ci`.

One difference you may see: times. node-postgres
answers a `timestamptz` as a JavaScript `Date`, which
becomes UTC, `...Z`; psycopg keeps the database's
offset. Both are the same instant.

## 7 What Reaches the Box

As tutorial 4's §8: js-api's image built again, its
allow-list rendered again, no new host, and
`COGNITO_USERINFO_URL` in the project's `cognito.env`.

## 8 What Can Go Wrong

- **Tutorial 4's §9,** all of it, with js-api for
  py-api
- **`make check`:
  `package-lock.json differs from package.json for pg`.**
  `pg` was added by hand; run §3's `npm install`
- **`500` with `ECONNREFUSED` not caught.** The
  database's address is wrong rather than down: the
  handler answers `503` for a refused connection and a
  timeout, not for a name that does not resolve
- **The starter's routes answer `no-store`, or its
  errors as the database's.** A hook or the error
  handler was set on `app`, not inside the plugin

## 9 See Also

- [6 A Svelte UI](6-a-svelte-ui.md): next
- [Develop and change js-api](../js-api/develop.md):
  the starter this came from
- [node-postgres](https://node-postgres.com/), read
  2026-10-06
- [Fastify's
  encapsulation](https://fastify.dev/docs/latest/Reference/Encapsulation/):
  why a plugin's hooks stay its own, read 2026-10-06
