"""A starter service in Python, at py-api.<your zone>

Stateless: the routes below show the shape every service keeps, and
are replaced by yours.

    GET  /health        the box's and the probes' check; keep it
    GET  /hello         anyone
    POST /echo          a signed-in caller: the body back, with who sent it
    GET  /openapi.json  the reference, made from the routes; keep it
    GET  /scalar-ui     the reference as a page, by Scalar; keep it

In front of this process, the box's nginx (rendered from
box/project.json, docs/onboarding/README.md):

- an allow-list: a route added here is unreachable until
  box/project.json names it, and the box's owner rolls it out;
- CORS for your www alone, and the rate of writes;

so this process does neither.

Who the caller is, this service decides itself: a Bearer access token
from the box's Cognito pool, issued to your project's UI client or the
box's probe client, verified against the pool's keys. What the caller
may then do is yours to decide. No database yet: state waits for the
box's PostgreSQL.
"""

import json
import os
import re
import threading
import time
import urllib.request

import jwt
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

SERVICE = os.environ.get("SERVICE", "py-api")
MAX_BODY = 1024 * 1024

# From the env file the box writes for your project at upload, from
# its Terraform's outputs. Unset, no token is accepted
ISSUER = os.environ.get("COGNITO_ISSUER", "")
CLIENTS = [c for c in (os.environ.get("COGNITO_UI_CLIENT_ID"), os.environ.get("COGNITO_PROBE_CLIENT_ID")) if c]

# The pool's signing keys, fetched once and again only for a key ID not
# yet seen, at most every five minutes: a forged token with a new key ID each time cannot make
# this process fetch on every request
REFETCH_AFTER = 300
_keys: dict[str, jwt.PyJWK] = {}
_fetched = -REFETCH_AFTER
_lock = threading.Lock()

BEARER = re.compile(r"^Bearer ([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)$")


def _key(kid: str) -> jwt.PyJWK | None:
    global _keys, _fetched
    with _lock:
        if kid not in _keys and time.monotonic() - _fetched > REFETCH_AFTER:
            _fetched = time.monotonic()
            with urllib.request.urlopen(f"{ISSUER}/.well-known/jwks.json", timeout=5) as r:
                _keys = {k.key_id: k for k in jwt.PyJWKSet.from_dict(json.load(r)).keys}
        return _keys.get(kid)


def caller(header: str | None) -> dict | None:
    """The caller's sub and groups, if the token is the pool's access
    token for one of our clients and unexpired; None otherwise.
    Cognito's access tokens carry client_id, not aud. Blocking: the
    first call fetches the keys, so run it off the event loop"""
    if not ISSUER or not CLIENTS:
        return None
    m = BEARER.match(header or "")
    if not m:
        return None
    try:
        key = _key(jwt.get_unverified_header(m[1]).get("kid", ""))
        if key is None:
            return None
        claims = jwt.decode(
            m[1], key, algorithms=["RS256"], issuer=ISSUER, options={"require": ["exp", "iat", "sub"], "verify_aud": False}
        )
    except Exception:
        return None
    if claims.get("token_use") != "access" or claims.get("client_id") not in CLIENTS:
        return None
    return {"sub": claims["sub"], "groups": claims.get("cognito:groups", [])}


# The API's reference (docs/conduct/api.md): the OpenAPI document at
# /openapi.json, made from the routes below and never written by hand,
# and Scalar's page of it at /scalar-ui. FastAPI's own /docs and /redoc
# stay off
app = FastAPI(title=SERVICE, version="0.1.0", docs_url=None, redoc_url=None, openapi_url="/openapi.json")

# A route that needs a token says so with openapi_extra=SIGNED_IN, or
# by taking the Authorization header as a parameter
SIGNED_IN = {"security": [{"bearer": []}]}


def reference() -> dict:
    """FastAPI's document of the routes, with the token as a scheme the
    page can fill: an Authorization parameter becomes that scheme"""
    if app.openapi_schema:
        return app.openapi_schema
    doc = get_openapi(title=app.title, version=app.version, routes=app.routes)
    doc.setdefault("components", {})["securitySchemes"] = {
        "bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                   "description": "An access token from the box's pool, for your UI's client or the probes'"}
    }
    for path in doc["paths"].values():
        for op in path.values():
            given = op.get("parameters", [])
            kept = [p for p in given if (p["in"], p["name"].lower()) != ("header", "authorization")]
            if len(kept) < len(given):
                op.update(SIGNED_IN)
                op["parameters"] = kept
    app.openapi_schema = doc
    return doc


app.openapi = reference

# Scalar's page: one file, by version and by its SHA-384, from jsDelivr;
# its settings are data, with telemetry and Scalar's own fonts off. The
# policy admits that script, the styles it injects, and calls to this
# host alone; nothing may frame the page
SCALAR = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>%s: the API</title>
  <link rel="icon" href="data:,">
</head>
<body>
  <script id="api-reference" type="application/json" data-url="/openapi.json"
    data-configuration='{"telemetry": false, "withDefaultFonts": false}'></script>
  <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.73.1/dist/browser/standalone.js"
    integrity="sha384-kYDGzV91Jnn3TbHINV3nt54riK2uMJDfN5Al8dAkz4FssELTBWbD8rgw32sTKfOi"
    crossorigin="anonymous"></script>
</body>
</html>
""" % SERVICE
SCALAR_POLICY = "; ".join([
    "default-src 'none'", "script-src https://cdn.jsdelivr.net", "style-src 'unsafe-inline'",
    "img-src 'self' data: blob:", "font-src 'self' data:", "connect-src 'self'",
    "base-uri 'none'", "form-action 'none'", "frame-ancestors 'none'",
])


@app.get("/scalar-ui", include_in_schema=False)
def scalar_ui():
    return HTMLResponse(SCALAR, headers={"Content-Security-Policy": SCALAR_POLICY, "Referrer-Policy": "no-referrer"})


@app.get("/health")
def health():
    """Anyone. The box's and the probes' check: that this service answers, and which it is"""
    return {"status": "ok", "service": SERVICE}


@app.get("/hello")
def hello():
    """Anyone. A greeting, naming the service"""
    return {"message": f"hello from {SERVICE}"}


# The token check may fetch the keys, so it runs in the thread pool;
# the body is read on the loop first. 1 MiB, as nginx's
# client_max_body_size for the host
@app.post("/echo", openapi_extra=SIGNED_IN)
async def echo(request: Request):
    """Signed in. The JSON body back, with who sent it. `400` for a body that is not JSON; `401` without a
    token; `413` over 1 MiB"""
    nostore = {"Cache-Control": "no-store"}
    body = await request.body()
    if len(body) > MAX_BODY:
        return JSONResponse({"error": "body too large"}, 413, headers=nostore)
    who = await run_in_threadpool(caller, request.headers.get("authorization"))
    if who is None:
        return JSONResponse(
            {"error": "sign in first"}, 401, headers={**nostore, "WWW-Authenticate": 'Bearer realm="py-api"'}
        )
    try:
        parsed = json.loads(body) if body else None
    except ValueError:
        return JSONResponse({"error": "body is not JSON"}, 400, headers=nostore)
    return JSONResponse(
        {"service": SERVICE, "caller": who["sub"], "groups": who["groups"], "body": parsed}, headers=nostore
    )
