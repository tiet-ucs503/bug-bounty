// The routes and the token check, against a pool of our own: a key
// pair made here, its public half served as the pool's JWKS on a local
// port. `npm test`; nothing leaves the machine
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { SignJWT, exportJWK, generateKeyPair } from "jose";

let pool, issuer, sign, other, app;

before(async () => {
  const { publicKey, privateKey } = await generateKeyPair("RS256");
  const jwk = { ...(await exportJWK(publicKey)), kid: "k1", alg: "RS256", use: "sig" };
  pool = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ keys: [jwk] }));
  });
  await new Promise((r) => pool.listen(0, "127.0.0.1", r));
  issuer = `http://127.0.0.1:${pool.address().port}`;
  sign = (claims, key = privateKey, iss = issuer) =>
    new SignJWT(claims).setProtectedHeader({ alg: "RS256", kid: "k1" })
      .setIssuer(iss).setSubject("user-1").setIssuedAt().setExpirationTime("5m").sign(key);
  other = (await generateKeyPair("RS256")).privateKey;

  process.env.COGNITO_ISSUER = issuer;
  process.env.COGNITO_UI_CLIENT_ID = "ui-client";
  process.env.COGNITO_PROBE_CLIENT_ID = "probe-client";
  app = (await import("../server.js")).build();
});

after(async () => {
  await app.close();
  pool.close();
});

const echo = (auth) =>
  app.inject({ method: "POST", url: "/echo", payload: { a: 1 }, headers: auth ? { authorization: auth } : {} });

test("health and hello answer anyone", async () => {
  assert.deepEqual((await app.inject("/health")).json(), { status: "ok", service: "js-api" });
  assert.equal((await app.inject("/hello")).statusCode, 200);
});

test("echo refuses no token, a bad one, and the wrong kind", async () => {
  assert.equal((await echo()).statusCode, 401);
  assert.equal((await echo("Bearer not.a.token")).statusCode, 401);
  assert.equal((await echo(`Bearer ${await sign({ token_use: "id", client_id: "ui-client" })}`)).statusCode, 401);
  assert.equal((await echo(`Bearer ${await sign({ token_use: "access", client_id: "neighbour" })}`)).statusCode, 401);
  assert.equal((await echo(`Bearer ${await sign({ token_use: "access", client_id: "ui-client" }, other)}`)).statusCode, 401);
  assert.equal((await echo(`Bearer ${await sign({ token_use: "access", client_id: "ui-client" }, undefined, "https://elsewhere")}`)).statusCode, 401);
  const r = await echo();
  assert.match(r.headers["www-authenticate"], /^Bearer/);
  assert.equal(r.headers["cache-control"], "no-store");
});

test("echo answers the UI's and the probes' access tokens", async () => {
  for (const c of ["ui-client", "probe-client"]) {
    const r = await echo(`Bearer ${await sign({ token_use: "access", client_id: c, "cognito:groups": ["admin"] })}`);
    assert.equal(r.statusCode, 200);
    assert.deepEqual(r.json(), { service: "js-api", caller: "user-1", groups: ["admin"], body: { a: 1 } });
  }
});

test("a body over 1 MiB is refused", async () => {
  const t = await sign({ token_use: "access", client_id: "ui-client" });
  const r = await app.inject({ method: "POST", url: "/echo", headers: { authorization: `Bearer ${t}`, "content-type": "application/json" },
    payload: JSON.stringify({ x: "y".repeat(1024 * 1024) }) });
  assert.equal(r.statusCode, 413);
});
