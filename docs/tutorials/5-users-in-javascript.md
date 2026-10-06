---
abstract: |
  The users unit as a JavaScript service, from the
  js-api starter: the same routes as tutorial 4's
  Python, the same database, the same refusals.
  Fastify, jose and node-postgres, tests that need no
  database, and the service run behind the stack's
  nginx.
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
title: 5 The users Service in JavaScript
version: v0.1.0
---

## 1 Before You Start

- [3 Make it a migration](3-the-migration.md), with
  `services/users/` copied from `services/js-api/`, and
  its migrations applied
- Node 24, as the image's
- The Python version is [tutorial
  4](4-users-in-python.md): the same routes, take one

## 2 The Routes

Tutorial 4's, §2: the same table, and the same `routes`
in the manifest. The service's entry differs in two
keys, `"language": "node"` and `"port": 3000`.

## 3 Its Package

`pg`, node-postgres, by exact version, in
`services/users/`. Expect `added` and a new
`package-lock.json`:

``` sh
cd services/users && npm install --save-exact --no-audit --no-fund pg@8.23.1 && cd ../..
```

And name the package `users` in its `package.json`.
`make check` holds the lockfile to `package.json`.

## 4 The Code

`services/users/server.js`, whole:

``` javascript
// users, at users.<your zone>: who may come in, and what each person may
// do (docs/tutorials/5-users-in-javascript.md)
//
//   GET    /health                      the box's and the probes' check
//   GET    /me                          the door: admits the caller if the
//                                       rules let them in, then says who
//                                       they are and what they may do
//   GET    /people                      everyone admitted: users.read
//   GET    /roles                       the matrix, role by role: users.read
//   PUT    /people/{sub}/roles/{role}   give a role: users.grant
//   DELETE /people/{sub}/roles/{role}   take it away: users.grant
//
// Who the caller is, from their access token, as every starter checks
// it; their e-mail from Cognito's userInfo, since an access token
// carries none. What they may do, the database decides: every accessor
// takes the caller first and refuses with SQLSTATE 42501, which becomes
// 403 here.

import Fastify from "fastify";
import { createRemoteJWKSet, jwtVerify } from "jose";
import pg from "pg";

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "0.0.0.0";
const SERVICE = process.env.SERVICE ?? "users";

const ISSUER = process.env.COGNITO_ISSUER ?? "";
const CLIENTS = [process.env.COGNITO_UI_CLIENT_ID, process.env.COGNITO_PROBE_CLIENT_ID].filter(Boolean);
const USERINFO = process.env.COGNITO_USERINFO_URL ?? "";

const keys = ISSUER ? createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks.json`)) : null;

// The caller's sub and token, if the token is the pool's access token
// for one of our clients and unexpired; null otherwise
export async function caller(header) {
  if (!keys || CLIENTS.length === 0) return null;
  const m = /^Bearer ([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)$/.exec(header ?? "");
  if (!m) return null;
  try {
    const { payload } = await jwtVerify(m[1], keys, { issuer: ISSUER, algorithms: ["RS256"] });
    if (payload.token_use !== "access" || !CLIENTS.includes(payload.client_id)) return null;
    return { sub: payload.sub, token: m[1] };
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

export function build() {
  const app = Fastify({ logger: true, bodyLimit: 1024 * 1024 });

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

  // Every route but /health: a signed-in caller, or 401
  async function signedIn(req, reply) {
    req.who = await caller(req.headers.authorization);
    if (!req.who) {
      reply.header("WWW-Authenticate", 'Bearer realm="users"');
      return reply.code(401).send({ error: "sign in first" });
    }
  }

  app.get("/health", async () => ({ status: "ok", service: SERVICE }));

  app.get("/me", { preHandler: signedIn }, async (req, reply) => {
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

  app.get("/people", { preHandler: signedIn }, async (req) => db.query("SELECT * FROM users_list($1)", [req.who.sub]));

  app.get("/roles", { preHandler: signedIn }, async (req) => db.query("SELECT * FROM users_matrix($1)", [req.who.sub]));

  app.put("/people/:sub/roles/:role", { preHandler: signedIn }, async (req) => {
    const { sub, role } = req.params;
    await db.query("SELECT users_grant($1, $2, $3)", [req.who.sub, sub, role]);
    return { sub, role, granted: true };
  });

  app.delete("/people/:sub/roles/:role", { preHandler: signedIn }, async (req) => {
    const { sub, role } = req.params;
    await db.query("SELECT users_revoke($1, $2, $3)", [req.who.sub, sub, role]);
    return { sub, role, granted: false };
  });

  return app;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const app = build();
  for (const s of ["SIGTERM", "SIGINT"]) {
    process.on(s, () => app.close().then(() => pool.end()).then(() => process.exit(0)));
  }
  await app.listen({ host: HOST, port: PORT });
}
```

What each part does:

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
- **The error handler:** node-postgres puts the
  SQLSTATE in `err.code`; `STATUS` turns a refusal into
  HTTP with its message. An unreachable database is
  `503`; anything else, Fastify's `500`
- **`signedIn`:** a `preHandler` on every route but
  `/health`, so no route can forget the token
- **`Cache-Control: no-store`** on every answer, by one
  hook: each is the caller's own

## 5 Its Tests

`services/users/test/server.test.js`:

``` javascript
// The routes, the token check and the door, against a pool of our own:
// a key pair made here, its public half served as the pool's JWKS, and
// a userInfo, on a local port. The database is replaced by a function
// that answers as the accessors would. `npm test`; nothing leaves the
// machine
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

test("health answers anyone", async () => {
  assert.deepEqual((await app.inject("/health")).json(), { status: "ok", service: "users" });
});

test("the door refuses no token and another client's", async () => {
  assert.equal((await get("/me")).statusCode, 401);
  assert.equal((await get("/me", "alice", { client_id: "neighbour" })).statusCode, 401);
});

test("the door admits a verified e-mail the rules match", async () => {
  const r = await get("/me", "alice");
  assert.equal(r.statusCode, 200);
  assert.deepEqual(r.json().roles, ["deny-all"]);
  assert.equal(r.headers["cache-control"], "no-store");
});

test("the door refuses an unverified e-mail", async () => {
  const r = await get("/me", "eve");
  assert.deepEqual([r.statusCode, r.json().error], [403, "not admitted"]);
});

test("the database's refusals become 403 and 409", async () => {
  assert.equal((await get("/people", "alice")).statusCode, 403);
  const r = await app.inject({ method: "DELETE", url: "/people/alice/roles/admin",
    headers: { authorization: `Bearer ${await sign("alice")}` } });
  assert.equal(r.statusCode, 409);
});
```

Expect `pass 5` for users among the others:

``` sh
make test
```

## 6 Run It, and Call It

As tutorial 4's §6 and §7, word for word: the same
calls, the same answers. On the dev stack, `make dev`
builds it; on the native stack, `stop`, `init` and
`start`, where `init` installs its packages with
`npm ci`.

One difference you may see: times. node-postgres
answers a `timestamptz` as a JavaScript `Date`, which
becomes UTC, `...Z`; psycopg keeps the database's
offset. Both are the same instant.

## 7 What Reaches the Box

As tutorial 4's §8: a new host, image and build for the
box's owner to roll out, and `COGNITO_USERINFO_URL` in
the project's `cognito.env`.

## 8 What Can Go Wrong

- **Tutorial 4's §9,** all of it
- **`make check`:
  `package-lock.json differs from package.json for pg`.**
  `pg` was added by hand; run §3's `npm install`
- **`500` with `ECONNREFUSED` not caught.** The
  database's address is wrong rather than down: the
  handler answers `503` for a refused connection and a
  timeout, not for a name that does not resolve

## 9 See Also

- [6 A Svelte UI](6-a-svelte-ui.md): next
- [Develop and change js-api](../js-api/develop.md):
  the starter this came from
- [node-postgres](https://node-postgres.com/), read
  2026-10-06
