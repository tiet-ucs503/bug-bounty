"""A starter service in Python, at py-api.<your zone>

Stateless: the routes below show the shape every service keeps, and
are replaced by yours.

    GET  /health   the box's and the probes' check; keep it
    GET  /hello    anyone
    POST /echo     a signed-in caller: the body back, with who sent it

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
from fastapi.responses import JSONResponse
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


# No /docs, /redoc or /openapi.json: nginx's allow-list would refuse
# them in any case
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE}


@app.get("/hello")
def hello():
    return {"message": f"hello from {SERVICE}"}


# The token check may fetch the keys, so it runs in the thread pool;
# the body is read on the loop first. 1 MiB, as nginx's
# client_max_body_size for the host
@app.post("/echo")
async def echo(request: Request):
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
