---
abstract: |
  Step 4 of tutorial 4, in JavaScript: `/users` as
  routes of js-api, Fastify, jose and node-postgres.
  Its package, its code whole, its own tests, and how
  to run it.
date: 2026-10-07
keywords:
- tutorial
- js-api
- node
- auth
- db
kind: tutorial
sources:
- services/js-api/server.js
- services/js-api/package.json
- box/project.json
status: draft
subtitle: Step 4, the code, in js-api
title: "4.4 /users: the Implementation in JavaScript"
version: v0.1.0
---

## 1 Before You Start

- [The contract](2-contract.md): its routes added to
  js-api's in `box/project.json` (§3 there)
- [The tests](3-tests.md), saved as `test-4.sh`, run
  once and failing; run them as `SERVICE=js-api`
- `users` among js-api's `prefixes`: [tutorial
  3](../3-the-migration/4-implementation.md) §2

The Python version is [its own
page](4-implementation-python.md); take one.

## 2 Its Package

`pg`, node-postgres, by exact version, in
`services/js-api/`. Expect `added` and a changed
`package-lock.json`:

``` sh
cd services/js-api && npm install --save-exact --no-audit --no-fund pg@8.23.1 && cd ../..
```

`make check` holds the lockfile to `package.json`.

## 3 The Code

`services/js-api/server.js`, whole, as this page leaves
it: the starter, and what `/users` adds.

``` javascript
// A starter service in JavaScript, at js-api.<your zone>. The
// starter's three routes show the shape every service keeps; the rest
// are yours.
//
//   GET  /health        the box's and the probes' check; keep it
//   GET  /hello         anyone
//   POST /echo          a signed-in caller: the body back, with who sent it
//   GET  /openapi.json  the reference, made from the routes; keep it
//   GET  /scalar-ui     the reference as a page, by Scalar; keep it
//
// and who is signed in, and what each may do, the database deciding
// (docs/tutorials/4-users/):
//
//   GET    /users/me                          records the caller, then
//                                             says who they are, their
//                                             profile, and what they may do
//   PUT    /users/me/profile                  the caller's own profile
//   GET    /users/people                      everyone signed in: users.read
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
// the caller first, and its refusals by SQLSTATE become 400, 403, 404
// and 409 here.

import swagger from "@fastify/swagger";
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
    // Google_<number> for a Google sign-in; no prefix for the pool's own
    const username = payload.username ?? "";
    const provider = username.includes("_") ? username.split("_")[0] : "Cognito";
    return { sub: payload.sub, groups: payload["cognito:groups"] ?? [], provider, token: m[1] };
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

// /users: who is signed in, and what each person may do; the database
// decides. A plugin, so its hook and its error handler are its own
// The caller as /users/me and its profile answer them: who, their
// profile, their roles and permissions
async function you(sub) {
  const [p] = await db.query("SELECT * FROM users_profile_get($1)", [sub]);
  const [m] = await db.query("SELECT roles, permissions FROM users_me($1)", [sub]);
  return { sub: p.sub, email: p.email, provider: p.provider,
    profile: { display_name: p.display_name, affiliation: p.affiliation }, ...m };
}

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

  app.get("/me", {
    schema: {
      security: SIGNED_IN,
      description: "Signed in. Records the caller at their first call, if their e-mail is verified. `200` and `{sub, " +
      "email, provider, profile: {display_name, affiliation}, roles, permissions}`. `403` for an e-mail " +
      "not verified; `503` if Cognito's `userInfo` or the database does not answer",
    },
  }, async (req, reply) => {
    let who;
    try {
      who = await emailOf(req.who);
    } catch {
      return reply.code(503).send({ error: "Cognito's userInfo is not answering" });
    }
    const [{ seen }] = await db.query("SELECT users_person_see($1, $2, $3, $4) AS seen",
      [req.who.sub, who.email, who.verified, req.who.provider]);
    if (!seen) return reply.code(403).send({ error: "e-mail not verified", email: who.email });
    return you(req.who.sub);
  });

  app.put("/me/profile", {
    schema: {
      security: SIGNED_IN,
      description: "Signed in. `{display_name, affiliation}`, text, 80 and 120 characters at most. `200` and the " +
      "caller as `GET /users/me` answers. `400` for a value not text or too long; `404` if never " +
      "recorded",
    },
  }, async (req, reply) => {
    const { display_name: name = "", affiliation = "" } = req.body ?? {};
    if (typeof name !== "string" || typeof affiliation !== "string") {
      return reply.code(400).send({ error: "display_name and affiliation are text" });
    }
    await db.query("SELECT users_profile_set($1, $2, $3)", [req.who.sub, name, affiliation]);
    return you(req.who.sub);
  });

  app.get("/people", {
    schema: {
      security: SIGNED_IN,
      description: "`users.read`. `200` and a list of `{sub, email, roles, first_seen_at, seen_at}`, by e-mail, at " +
      "most 1000. `403` without it",
    },
  }, async (req) => db.query("SELECT * FROM users_list($1)", [req.who.sub]));

  app.get("/roles", {
    schema: {
      security: SIGNED_IN,
      description: "`users.read`. The access control matrix: `200` and a list of `{role, about, permissions}`. `403` " +
      "without it",
    },
  }, async (req) => db.query("SELECT * FROM users_matrix($1)", [req.who.sub]));

  app.put("/people/:sub/roles/:role", {
    schema: {
      security: SIGNED_IN,
      description: "`users.grant`. Gives a person a role. `200` and `{sub, role, granted: true}`; twice is once. " +
      "`403` without it; `404` for no such person or role",
    },
  }, async (req) => {
    const { sub, role } = req.params;
    await db.query("SELECT users_grant($1, $2, $3)", [req.who.sub, sub, role]);
    return { sub, role, granted: true };
  });

  app.delete("/people/:sub/roles/:role", {
    schema: {
      security: SIGNED_IN,
      description: "`users.grant`. Takes a role away. `200` and `{sub, role, granted: false}`. `403` without it; " +
      "`404` if the person lacks the role; `409` for the last `users.grant` there is",
    },
  }, async (req) => {
    const { sub, role } = req.params;
    await db.query("SELECT users_revoke($1, $2, $3)", [req.who.sub, sub, role]);
    return { sub, role, granted: false };
  });
}

// The API's reference (docs/conduct/api.md): the OpenAPI document at
// /openapi.json, made from each route's schema and never written by
// hand, and Scalar's page of it at /scalar-ui. A route that needs a
// token says so with security: SIGNED_IN
export const SIGNED_IN = [{ bearer: [] }];
const REFERENCE = {
  openapi: {
    openapi: "3.1.0",
    info: { title: SERVICE, version: "0.1.0" },
    components: {
      securitySchemes: {
        bearer: {
          type: "http", scheme: "bearer", bearerFormat: "JWT",
          description: "An access token from the box's pool, for your UI's client or the probes'",
        },
      },
    },
  },
};

// Scalar's page: one file, by version and by its SHA-384, from jsDelivr;
// its settings are data: no telemetry, none of Scalar's fonts, and none
// of its own tools, the AI, the MCP and the sharing among them. The
// policy admits that script, the styles it injects, and calls to this
// host alone; nothing may frame the page
const SCALAR = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${SERVICE}: the API</title>
  <link rel="icon" href="data:,">
</head>
<body>
  <script id="api-reference" type="application/json" data-url="/openapi.json"
    data-configuration='{"telemetry": false, "withDefaultFonts": false, "showDeveloperTools": "never",
      "agent": {"disabled": true}, "mcp": {"disabled": true}, "hideClientButton": true}'></script>
  <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.73.1/dist/browser/standalone.js"
    integrity="sha384-kYDGzV91Jnn3TbHINV3nt54riK2uMJDfN5Al8dAkz4FssELTBWbD8rgw32sTKfOi"
    crossorigin="anonymous"></script>
</body>
</html>
`;
const SCALAR_POLICY = [
  "default-src 'none'", "script-src https://cdn.jsdelivr.net", "style-src 'unsafe-inline'",
  "img-src 'self' data: blob:", "font-src 'self' data:", "connect-src 'self'",
  "base-uri 'none'", "form-action 'none'", "frame-ancestors 'none'",
].join("; ");

// The starter's routes, a plugin, so the reference sees each as it is
// added. Yours go here, or in a plugin of their own beside it
async function starter(app) {
  app.get("/health", {
    schema: { description: "Anyone. The box's and the probes' check: that this service answers, and which it is" },
  }, async () => ({ status: "ok", service: SERVICE }));

  app.get("/hello", {
    schema: { description: "Anyone. A greeting, naming the service" },
  }, async () => ({ message: `hello from ${SERVICE}` }));

  app.post("/echo", {
    schema: {
      description: "Signed in. The JSON body back, with who sent it. `401` without a token; `413` over 1 MiB",
      security: SIGNED_IN,
    },
  }, async (req, reply) => {
    reply.header("Cache-Control", "no-store");
    const who = await caller(req.headers.authorization);
    if (!who) {
      reply.header("WWW-Authenticate", 'Bearer realm="js-api"');
      return reply.code(401).send({ error: "sign in first" });
    }
    return { service: SERVICE, caller: who.sub, groups: who.groups, body: req.body ?? null };
  });
}

// 1 MiB, as nginx's client_max_body_size for the host. The log is
// JSON on stdout, which Docker's awslogs driver sends on; Fastify's
// request lines carry no header, so no token reaches the log
export function build() {
  const app = Fastify({ logger: true, bodyLimit: 1024 * 1024 });

  app.register(swagger, REFERENCE);
  app.get("/openapi.json", { schema: { hide: true } }, async () => app.swagger());
  app.get("/scalar-ui", { schema: { hide: true } }, async (req, reply) =>
    reply.type("text/html; charset=utf-8").header("Content-Security-Policy", SCALAR_POLICY)
      .header("Referrer-Policy", "no-referrer").send(SCALAR));
  app.register(starter);
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

- **`USERINFO`:** Cognito's `userInfo`, from
  `COGNITO_USERINFO_URL`
- **`caller`:** the starter's check of the token (U1),
  keeping the token itself, which `userInfo` needs, and
  reading the provider from `username`: the part before
  `_`, or `Cognito` for the pool's own accounts
- **`emailOf`:** asks `userInfo` with the caller's own
  token, with a five-second timeout, keeps the answer
  ten minutes, and reads `email_verified` as the string
  it is
- **`pool`:** node-postgres connects at the first
  query, not at start: the service answers `/health`
  with the database down
- **`db.query`:** one statement, its rows; the tests
  replace it
- **`you`:** the answer of `/users/me` and of the
  profile's `PUT`: the record and profile, then the
  roles and permissions (U3)
- **`users`, a Fastify plugin,** registered with the
  prefix `/users`. Fastify keeps a plugin's hooks and
  error handler to its own routes, so the starter's
  three answer as they did:
  - **its error handler:** node-postgres puts the
    SQLSTATE in `err.code`; `STATUS` turns a refusal
    into HTTP with its message (U5). An unreachable
    database is `503`; anything else, Fastify's `500`
  - **a `preHandler` hook:** the token, on every route
    of the plugin, so none can forget it
  - **an `onSend` hook:** `Cache-Control: no-store`, as
    each answer is the caller's own (U8)
- **The shutdown** ends the pool after the server

**Each route describes itself** (U9, T4.15): the
`description` in its `schema`, says who may call it,
and what it answers and refuses; `security: SIGNED_IN`
marks it signed in. The starter makes `/openapi.json`
from these, and `/scalar-ui` shows it. Open
`http://js-api.localhost:8080/scalar-ui`, or your
`NGINX_PORT`, once §5 has it running.

**Document the routes.** In `docs/js-api/api.md`, after
the starter's in §2, the entries from [the
contract](2-contract.md) §2, in the page's own form;
the same words as each route's description, written
together:

``` markdown
GET /users/me
: Signed in. Records the caller at their first call,
  if their e-mail is verified. `200` and
  `{sub, email, provider, profile: {display_name, affiliation}, roles, permissions}`.
  `403` for an e-mail not verified; `503` if Cognito's
  `userInfo` or the database does not answer

PUT /users/me/profile
: Signed in. `{display_name, affiliation}`, text, 80
  and 120 characters at most. `200` and the caller as
  `GET /users/me` answers. `400` for a value not text
  or too long; `404` if never recorded

GET /users/people
: `users.read`. `200` and a list of
  `{sub, email, roles, first_seen_at, seen_at}`, by
  e-mail, at most 1000. `403` without it

GET /users/roles
: `users.read`. `200` and a list of
  `{role, about, permissions}`. `403` without it

PUT /users/people/{sub}/roles/{role}
: `users.grant`. `200` and
  `{sub, role, granted: true}`; twice is once. `403`
  without it; `404` for no such person or role

DELETE /users/people/{sub}/roles/{role}
: `users.grant`. `200` and
  `{sub, role, granted: false}`. `403` without it;
  `404` if the person lacks the role; `409` for the
  last `users.grant` there is
```

## 4 Its Tests

Each test file runs in a process of its own, so this
one sets the pool's address before it imports
`server.js`. `services/js-api/test/users.test.js`:

``` javascript
// /users: the token check, the door and the profile, against a pool of our own: a
// key pair made here, its public half served as the pool's JWKS, and a
// userInfo, on a local port. The database is replaced by a function
// that answers as the accessors would. `npm test`, which runs each file
// in a process of its own; nothing leaves the machine
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { SignJWT, decodeJwt, exportJWK, generateKeyPair } from "jose";

const EMAILS = { asha: ["asha@example.org", "true"], esha: ["esha@example.org", "false"] };
let pool, issuer, sign, app, server;
// What the fake database was last told, by accessor
const seen = {};

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
    if (sql.startsWith("SELECT users_person_see")) {
      seen.person = args;
      return [{ seen: args[2] }];
    }
    if (sql.startsWith("SELECT * FROM users_profile_get")) {
      const [name, affiliation] = seen.profile ?? ["", ""];
      return [{ sub: args[0], email: "asha@example.org", provider: seen.person?.[3] ?? "Cognito",
        display_name: name, affiliation }];
    }
    if (sql.startsWith("SELECT users_profile_set")) {
      if (args[1].length > 80) throw refused("23514", "value too long");
      seen.profile = args.slice(1);
      return [{}];
    }
    if (sql.startsWith("SELECT roles, permissions FROM users_me")) return [{ roles: [], permissions: [] }];
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
  assert.equal((await get("/users/me", "asha", { client_id: "neighbour" })).statusCode, 401);
});

test("the door records a verified e-mail, and answers with no roles yet", async () => {
  const r = await get("/users/me", "asha");
  assert.equal(r.statusCode, 200);
  assert.deepEqual([r.json().roles, r.json().profile.display_name], [[], ""]);
  assert.equal(r.headers["cache-control"], "no-store");
});

test("the provider comes from the token's username", async () => {
  await get("/users/me", "asha", { username: "Google_1234" });
  assert.equal(seen.person[3], "Google");
  await get("/users/me", "asha", { username: "asha" });
  assert.equal(seen.person[3], "Cognito");
});

test("the door refuses an unverified e-mail", async () => {
  const r = await get("/users/me", "esha");
  assert.deepEqual([r.statusCode, r.json().error], [403, "e-mail not verified"]);
});

test("the caller's own profile, changed", async () => {
  const put = async (body) => app.inject({ method: "PUT", url: "/users/me/profile", payload: body,
    headers: { authorization: `Bearer ${await sign("asha")}` } });
  const r = await put({ display_name: "Asha", affiliation: "Physics" });
  assert.deepEqual([r.statusCode, r.json().profile], [200, { display_name: "Asha", affiliation: "Physics" }]);
  assert.equal((await put({ display_name: 7 })).statusCode, 400);
  assert.equal((await put({ display_name: "a".repeat(81) })).statusCode, 400);
});

test("the database's refusals become 403 and 409", async () => {
  assert.equal((await get("/users/people", "asha")).statusCode, 403);
  const r = await app.inject({ method: "DELETE", url: "/users/people/asha/roles/admin",
    headers: { authorization: `Bearer ${await sign("asha")}` } });
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
Expect `pass 13` for js-api, the starter's six tests
and these seven:

``` sh
make test
```

## 5 Run It

On the dev stack, `make dev` builds it; on the native
stack, `stop`, `init` and `start`, where `init`
installs its packages with `npm ci`. Expect
`js-api health 200` from `tools/native-dev.sh status`.
Then [the refinement](5-refinement.md), with
`SERVICE=js-api`.

## 6 What Reaches the Box

As [the Python page](4-implementation-python.md)'s §6:
js-api's image built again, its allow-list rendered
again, no new host, and `COGNITO_USERINFO_URL` in the
project's `cognito.env`.

## 7 See Also

- [The refinement](5-refinement.md): next
- [Develop and change js-api](../../js-api/develop.md):
  the starter this came from
- [node-postgres](https://node-postgres.com/), read
  2026-10-06
- [Fastify's
  encapsulation](https://fastify.dev/docs/latest/Reference/Encapsulation/):
  why a plugin's hooks stay its own, read 2026-10-06
