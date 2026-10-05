// A starter service in JavaScript, at js-api.<your zone>. Stateless:
// the routes below show the shape every service keeps, and are
// replaced by yours.
//
//   GET  /health   the box's and the probes' check; keep it
//   GET  /hello    anyone
//   POST /echo     a signed-in caller: the body back, with who sent it
//
// In front of this process, the box's nginx (rendered from
// box/project.json, box/how-the-box-works.md):
//   - an allow-list: a route added here is unreachable until
//     box/project.json names it, and the box's owner rolls it out;
//   - CORS for your www alone, and the rate of writes;
// so this process does neither.
//
// Who the caller is, this service decides itself: a Bearer access token
// from the box's Cognito pool, issued to your project's UI client or the
// box's probe client, verified against the pool's keys. What the caller
// may then do is yours to decide. No database yet: state waits for the
// box's PostgreSQL.

import Fastify from "fastify";
import { createRemoteJWKSet, jwtVerify } from "jose";

const PORT = Number(process.env.PORT ?? 3000);
const SERVICE = process.env.SERVICE ?? "js-api";

// From the env file the box writes for your project at upload, from
// its Terraform's outputs. Unset, no token is accepted
const ISSUER = process.env.COGNITO_ISSUER ?? "";
const CLIENTS = [process.env.COGNITO_UI_CLIENT_ID, process.env.COGNITO_PROBE_CLIENT_ID].filter(Boolean);

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
    return { sub: payload.sub, groups: payload["cognito:groups"] ?? [] };
  } catch {
    return null;
  }
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

  return app;
}

// Started as a program, not when a test imports it. SIGTERM from
// `docker compose` closes the server and lets requests in flight end
if (import.meta.url === `file://${process.argv[1]}`) {
  const app = build();
  for (const s of ["SIGTERM", "SIGINT"]) {
    process.on(s, () => app.close().then(() => process.exit(0)));
  }
  await app.listen({ host: "0.0.0.0", port: PORT });
}
