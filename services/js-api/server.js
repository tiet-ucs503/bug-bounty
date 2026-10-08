// A starter service in JavaScript, at js-api.<your zone>. Stateless:
// the routes below show the shape every service keeps, and are
// replaced by yours.
//
//   GET  /health        the box's and the probes' check; keep it
//   GET  /hello         anyone
//   POST /echo          a signed-in caller: the body back, with who sent it
//   GET  /openapi.json  the reference, made from the routes; keep it
//   GET  /scalar-ui     the reference as a page, by Scalar; keep it
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
// may then do is yours to decide. No database yet: state waits for the
// box's PostgreSQL.

import swagger from "@fastify/swagger";
import Fastify from "fastify";
import { createRemoteJWKSet, jwtVerify } from "jose";

const PORT = Number(process.env.PORT ?? 3000);
// Every address in a container; 127.0.0.1 alone when run as a program
// on a shared machine (tools/native-dev.sh)
const HOST = process.env.HOST ?? "0.0.0.0";
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

  return app;
}

// Started as a program, not when a test imports it. SIGTERM from
// `docker compose` closes the server and lets requests in flight end
if (import.meta.url === `file://${process.argv[1]}`) {
  const app = build();
  for (const s of ["SIGTERM", "SIGINT"]) {
    process.on(s, () => app.close().then(() => process.exit(0)));
  }
  await app.listen({ host: HOST, port: PORT });
}
