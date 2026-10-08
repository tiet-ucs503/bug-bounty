---
abstract: |
  Step 4 of tutorial 4, in Python: `/users` as routes
  of py-api, FastAPI and psycopg. Its packages, its
  code whole, its own tests, and how to run it.
date: 2026-10-07
keywords:
- tutorial
- py-api
- python
- auth
- db
kind: tutorial
sources:
- services/py-api/main.py
- services/py-api/requirements.txt
- box/project.json
status: draft
subtitle: Step 4, the code, in py-api
title: "4.4 /users: the Implementation in Python"
version: v0.1.0
---

## 1 Before You Start

- [The contract](2-contract.md): its routes added to
  py-api's in `box/project.json` (§3 there)
- [The tests](3-tests.md), saved as `test-4.sh`, run
  once and failing
- `users` among py-api's `prefixes`: [tutorial
  3](../3-the-migration/4-implementation.md) §2

The JavaScript version is [its own
page](4-implementation-javascript.md); take one.

## 2 Its Packages

psycopg 3, the PostgreSQL driver, with its binary build
and its pool. In `services/py-api/requirements.txt`,
the three lines among the others, by version, as every
package there is:

``` text
psycopg[binary]==3.3.6
psycopg-binary==3.3.6
psycopg-pool==3.3.3
```

The binary build has wheels for arm64, the box's, and
x86-64, so nothing compiles.

## 3 The Code

`services/py-api/main.py`, whole, as this page leaves
it: the starter, and what `/users` adds.

``` python
"""A starter service in Python, at py-api.<your zone>

The starter's three routes show the shape every service keeps; the
rest are yours.

    GET  /health        the box's and the probes' check; keep it
    GET  /hello         anyone
    POST /echo          a signed-in caller: the body back, with who sent it
    GET  /openapi.json  the reference, made from the routes; keep it
    GET  /scalar-ui     the reference as a page, by Scalar; keep it

and who is signed in, and what each may do, the database deciding
(docs/tutorials/4-users/):

    GET    /users/me                          records the caller, then
                                              says who they are, their
                                              profile, and what they may do
    PUT    /users/me/profile                  the caller's own profile
    GET    /users/people                      everyone signed in: users.read
    GET    /users/roles                       the matrix: users.read
    PUT    /users/people/{sub}/roles/{role}   give a role: users.grant
    DELETE /users/people/{sub}/roles/{role}   take it away: users.grant

In front of this process, the box's nginx (rendered from
box/project.json, docs/onboarding/README.md):

- an allow-list: a route added here is unreachable until
  box/project.json names it, and the box's owner rolls it out;
- CORS for your www alone, and the rate of writes;

so this process does neither.

Who the caller is, this service decides itself: a Bearer access token
from the box's Cognito pool, issued to your project's UI client or the
box's probe client, verified against the pool's keys. What the caller
may then do, the project's database decides: every accessor takes the
caller first, and its refusals by SQLSTATE become 400, 403, 404 and
409 here.
"""

import json
import os
import re
import threading
import time
import urllib.request
from contextlib import asynccontextmanager

import jwt
import psycopg
from fastapi import APIRouter, Body, FastAPI, Header, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout
from starlette.concurrency import run_in_threadpool

SERVICE = os.environ.get("SERVICE", "py-api")
MAX_BODY = 1024 * 1024

# From the env file the box writes for your project at upload, from
# its Terraform's outputs. Unset, no token is accepted
ISSUER = os.environ.get("COGNITO_ISSUER", "")
CLIENTS = [c for c in (os.environ.get("COGNITO_UI_CLIENT_ID"), os.environ.get("COGNITO_PROBE_CLIENT_ID")) if c]

# Cognito's userInfo, which answers a caller's e-mail to their own
# token: an access token carries none
USERINFO = os.environ.get("COGNITO_USERINFO_URL", "")

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
    """The caller's sub, groups, provider and token, if the token is the pool's access
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
    # Google_<number> for a Google sign-in; no prefix for the pool's own
    username = claims.get("username", "")
    provider = username.split("_", 1)[0] if "_" in username else "Cognito"
    return {"sub": claims["sub"], "groups": claims.get("cognito:groups", []), "provider": provider, "token": m[1]}


# userInfo's answer for each sub, kept ten minutes: Cognito limits how
# often it may be asked, and an e-mail seldom changes
EMAIL_FOR = 600
_emails: dict[str, tuple[float, str, bool]] = {}


def email_of(who: dict) -> tuple[str, bool]:
    """The caller's e-mail and whether it is verified, from userInfo by
    their own token. Cognito answers email_verified as a string"""
    hit = _emails.get(who["sub"])
    if hit and time.monotonic() - hit[0] < EMAIL_FOR:
        return hit[1], hit[2]
    if not USERINFO:
        return "", False
    req = urllib.request.Request(USERINFO, headers={"Authorization": f"Bearer {who['token']}"})
    with urllib.request.urlopen(req, timeout=5) as r:
        info = json.load(r)
    if info.get("sub") != who["sub"]:
        return "", False
    email, verified = info.get("email", ""), str(info.get("email_verified", "")).lower() == "true"
    _emails[who["sub"]] = (time.monotonic(), email, verified)
    return email, verified


# The project's database, as its app login. Opened without waiting, so
# the service starts, and answers /health, whether or not it is up
pool = ConnectionPool(os.environ.get("DATABASE_URL", ""), min_size=1, max_size=4, open=False,
                      kwargs={"row_factory": dict_row, "autocommit": True})


def query(sql: str, args: tuple = ()) -> list[dict]:
    """One statement, its rows; the tests replace it"""
    with pool.connection(timeout=5) as conn:
        return conn.execute(sql, args).fetchall()


# The database's refusals, by SQLSTATE, as HTTP
STATUS = {"42501": 403, "P0002": 404, "23001": 409, "23514": 400, "22001": 400}
NOSTORE = {"Cache-Control": "no-store"}


def answer(data, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status, headers=NOSTORE)


def signed_out() -> JSONResponse:
    return JSONResponse({"error": "sign in first"}, 401, headers={**NOSTORE, "WWW-Authenticate": 'Bearer realm="py-api"'})


def run(sql: str, args: tuple) -> JSONResponse | list[dict]:
    """The accessor's rows, times as ISO 8601; or its refusal as an
    answer"""
    try:
        out = query(sql, args)
    except psycopg.Error as e:
        if e.sqlstate in STATUS:
            return answer({"error": e.diag.message_primary or str(e)}, STATUS[e.sqlstate])
        raise
    except PoolTimeout:
        return answer({"error": "the database is not answering"}, 503)
    for r in out:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return out


@asynccontextmanager
async def lifespan(_app):
    if pool.conninfo:
        pool.open(wait=False)
    yield
    pool.close()


# The API's reference (docs/conduct/api.md): the OpenAPI document at
# /openapi.json, made from the routes below and never written by hand,
# and Scalar's page of it at /scalar-ui. FastAPI's own /docs and /redoc
# stay off
app = FastAPI(title=SERVICE, version="0.1.0", docs_url=None, redoc_url=None, openapi_url="/openapi.json",
              lifespan=lifespan)

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
# its settings are data: no telemetry, none of Scalar's fonts, and none
# of its own tools, the AI, the MCP and the sharing among them. The
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
    data-configuration='{"telemetry": false, "withDefaultFonts": false, "showDeveloperTools": "never",
      "agent": {"disabled": true}, "mcp": {"disabled": true}, "hideClientButton": true}'></script>
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


# /users: who is signed in, and what each person may do; the database
# decides (docs/tutorials/4-users/). Sync routes: FastAPI runs each in
# its thread pool, so userInfo and the database may block
users = APIRouter(prefix="/users")


def you(sub: str) -> JSONResponse:
    """The caller as /users/me and its profile answer them: who, their
    profile, their roles and permissions"""
    r = run("SELECT * FROM users_profile_get(%s)", (sub,))
    if isinstance(r, JSONResponse):
        return r
    m = run("SELECT roles, permissions FROM users_me(%s)", (sub,))
    if isinstance(m, JSONResponse):
        return m
    p = r[0]
    return answer({"sub": p["sub"], "email": p["email"], "provider": p["provider"],
                   "profile": {"display_name": p["display_name"], "affiliation": p["affiliation"]}, **m[0]})


@users.get("/me")
def me(authorization: str | None = Header(default=None)):
    """Signed in. Records the caller at their first call, if their e-mail is verified. `200` and `{sub, email,
    provider, profile: {display_name, affiliation}, roles, permissions}`. `403` for an e-mail not verified;
    `503` if Cognito's `userInfo` or the database does not answer"""
    who = caller(authorization)
    if who is None:
        return signed_out()
    try:
        email, verified = email_of(who)
    except OSError:
        return answer({"error": "Cognito's userInfo is not answering"}, 503)
    r = run("SELECT users_person_see(%s, %s, %s, %s) AS seen", (who["sub"], email, verified, who["provider"]))
    if isinstance(r, JSONResponse):
        return r
    if not r[0]["seen"]:
        return answer({"error": "e-mail not verified", "email": email}, 403)
    return you(who["sub"])


@users.put("/me/profile")
def profile(body: dict = Body(default={}), authorization: str | None = Header(default=None)):
    """Signed in. `{display_name, affiliation}`, text, 80 and 120 characters at most. `200` and the caller as
    `GET /users/me` answers. `400` for a value not text or too long; `404` if never recorded"""
    who = caller(authorization)
    if who is None:
        return signed_out()
    name, affiliation = body.get("display_name", ""), body.get("affiliation", "")
    if not isinstance(name, str) or not isinstance(affiliation, str):
        return answer({"error": "display_name and affiliation are text"}, 400)
    r = run("SELECT users_profile_set(%s, %s, %s)", (who["sub"], name, affiliation))
    return r if isinstance(r, JSONResponse) else you(who["sub"])


@users.get("/people")
def people(authorization: str | None = Header(default=None)):
    """`users.read`. `200` and a list of `{sub, email, roles, first_seen_at, seen_at}`, by e-mail, at most
    1000. `403` without it"""
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM users_list(%s)", (who["sub"],))
    return r if isinstance(r, JSONResponse) else answer(r)


@users.get("/roles")
def roles(authorization: str | None = Header(default=None)):
    """`users.read`. The access control matrix: `200` and a list of `{role, about, permissions}`. `403` without
    it"""
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM users_matrix(%s)", (who["sub"],))
    return r if isinstance(r, JSONResponse) else answer(r)


@users.put("/people/{sub}/roles/{role}")
def grant(sub: str, role: str, authorization: str | None = Header(default=None)):
    """`users.grant`. Gives a person a role. `200` and `{sub, role, granted: true}`; twice is once. `403`
    without it; `404` for no such person or role"""
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT users_grant(%s, %s, %s)", (who["sub"], sub, role))
    return r if isinstance(r, JSONResponse) else answer({"sub": sub, "role": role, "granted": True})


@users.delete("/people/{sub}/roles/{role}")
def revoke(sub: str, role: str, authorization: str | None = Header(default=None)):
    """`users.grant`. Takes a role away. `200` and `{sub, role, granted: false}`. `403` without it; `404` if
    the person lacks the role; `409` for the last `users.grant` there is"""
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT users_revoke(%s, %s, %s)", (who["sub"], sub, role))
    return r if isinstance(r, JSONResponse) else answer({"sub": sub, "role": role, "granted": False})


app.include_router(users)
```

What it adds to the starter:

- **`USERINFO`:** Cognito's `userInfo`, from
  `COGNITO_USERINFO_URL`
- **`caller`:** the starter's check of the token (U1),
  keeping the token itself, which `userInfo` needs, and
  reading the provider from `username`: the part before
  `_`, or `Cognito` for the pool's own accounts
- **`email_of`:** asks `userInfo` with the caller's own
  token, keeps the answer ten minutes, and reads
  `email_verified` as the string it is. The `sub` it
  answers must be the token's
- **`pool`:** four connections at most, as the
  project's login, `DATABASE_URL`. Opened without
  waiting, by `lifespan`: the service starts and
  answers `/health` with the database down, and a route
  that needs it answers `503`
- **`query`:** one statement, its rows. The tests
  replace it
- **`run` and `STATUS`:** an accessor's refusal, by its
  SQLSTATE, as HTTP, with its message (U5)
- **`you`:** the answer of `/users/me` and of the
  profile's `PUT`: the record and profile, then the
  roles and permissions (U3)
- **`users`, an `APIRouter` with the prefix `/users`:**
  the routes, each `def`, not `async def`. FastAPI runs
  them in its thread pool, where the token check and
  psycopg may block. Each passes the caller first; none
  checks a permission itself. `/me` records the caller
  before it answers (U2); `/me/profile` passes the
  caller's own `sub` (U4). `app.include_router` mounts
  them
- **The starter's three,** `/health`, `/hello` and
  `/echo`, as they were

Tutorial 5's notes use the same `pool`, `run` and
`answer`.

**Each route describes itself** (U9, T4.15): its first
lines, a docstring, says who may call it, and what it
answers and refuses; taking the `Authorization` header
as a parameter is what marks it signed in. The starter
makes `/openapi.json` from these, and `/scalar-ui`
shows it. Open
`http://py-api.localhost:8080/scalar-ui`, or your
`NGINX_PORT`, once §5 has it running.

**Document the routes.** In `docs/py-api/api.md`, after
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

Offline: a key pair and a `userInfo` of their own on a
local port, and the database replaced by what the
accessors would answer. The starter's tests share
`main` in the same process, so these set the pool's
address and the database on it, and put them back.
`services/py-api/test/test_users.py`:

``` python
"""/users: the token check, the door and the profile, against a pool of our own: a
key pair made here, its public half served as the pool's JWKS, and a
userInfo, on a local port. The database is replaced by a function that
answers as the accessors would. Nothing leaves the machine:

    python -m unittest discover -s test

main is shared with the other tests in this process, so the pool's
address and the database are set on it here, and put back after
"""

import importlib
import json
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
EMAILS = {"asha": ("asha@example.org", "true"), "esha": ("esha@example.org", "false")}


class Pool(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/.well-known/jwks.json":
            body = {"keys": [{**JWK, "kid": "users-k1", "alg": "RS256", "use": "sig"}]}
        else:
            sub = jwt.decode(self.headers["Authorization"][7:], options={"verify_signature": False})["sub"]
            email, verified = EMAILS[sub]
            body = {"sub": sub, "email": email, "email_verified": verified}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def refused(sqlstate, message):
    """A refusal as psycopg raises one, by its SQLSTATE"""
    return psycopg.errors.lookup(sqlstate)(message)


# What the fake database was last told, by accessor
seen = {}


def database(sql, args):
    """The accessors, as the tests need them"""
    if sql.startswith("SELECT users_person_see"):
        sub, email, verified, provider = args
        seen["person"] = args
        return [{"seen": verified}]
    if sql.startswith("SELECT * FROM users_profile_get"):
        provider = seen.get("person", ("", "", True, "Cognito"))[3]
        name, affiliation = seen.get("profile", ("", ""))
        return [{"sub": args[0], "email": "asha@example.org", "provider": provider,
                 "display_name": name, "affiliation": affiliation}]
    if sql.startswith("SELECT users_profile_set"):
        if len(args[1]) > 80:
            raise refused("23514", "value too long")
        seen["profile"] = args[1:]
        return [{"users_profile_set": None}]
    if sql.startswith("SELECT roles, permissions FROM users_me"):
        return [{"roles": [], "permissions": []}]
    if sql.startswith("SELECT * FROM users_list"):
        raise refused("42501", "users.read needed")
    if sql.startswith("SELECT users_revoke"):
        raise refused("23001", "the last users.grant: grant it to someone else first")
    raise AssertionError(sql)


SET = ("ISSUER", "CLIENTS", "USERINFO", "query", "_keys", "_fetched", "_emails")


class Users(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = HTTPServer(("127.0.0.1", 0), Pool)
        threading.Thread(target=cls.pool.serve_forever, daemon=True).start()
        cls.issuer = f"http://127.0.0.1:{cls.pool.server_port}"
        from fastapi.testclient import TestClient

        cls.main = importlib.import_module("main")
        cls.saved = {k: getattr(cls.main, k) for k in SET}
        for k, v in {"ISSUER": cls.issuer, "CLIENTS": ["ui-client", "probe-client"],
                     "USERINFO": f"{cls.issuer}/oauth2/userInfo", "query": database,
                     "_keys": {}, "_fetched": -cls.main.REFETCH_AFTER, "_emails": {}}.items():
            setattr(cls.main, k, v)
        cls.client = TestClient(cls.main.app)

    @classmethod
    def tearDownClass(cls):
        for k, v in cls.saved.items():
            setattr(cls.main, k, v)
        cls.pool.shutdown()

    def token(self, sub, **over):
        now = int(time.time())
        claims = {"iss": self.issuer, "sub": sub, "iat": now, "exp": now + 300, "token_use": "access",
                  "client_id": "ui-client", **over}
        return {"Authorization": "Bearer " + jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": "users-k1"})}

    def test_me_signed_out(self):
        self.assertEqual(self.client.get("/users/me").status_code, 401)

    def test_me_another_client(self):
        self.assertEqual(self.client.get("/users/me", headers=self.token("asha", client_id="other")).status_code, 401)

    def test_me_recorded(self):
        r = self.client.get("/users/me", headers=self.token("asha"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["roles"], r.json()["profile"]["display_name"]), ([], ""))

    def test_me_provider_from_username(self):
        self.client.get("/users/me", headers=self.token("asha", username="Google_1234"))
        self.assertEqual(seen["person"][3], "Google")
        self.client.get("/users/me", headers=self.token("asha", username="asha"))
        self.assertEqual(seen["person"][3], "Cognito")

    def test_me_unverified(self):
        r = self.client.get("/users/me", headers=self.token("esha"))
        self.assertEqual((r.status_code, r.json()["error"]), (403, "e-mail not verified"))

    def test_profile(self):
        r = self.client.put("/users/me/profile", headers=self.token("asha"),
                            json={"display_name": "Asha", "affiliation": "Physics"})
        self.assertEqual((r.status_code, r.json()["profile"]), (200, {"display_name": "Asha", "affiliation": "Physics"}))
        r = self.client.put("/users/me/profile", headers=self.token("asha"), json={"display_name": 7})
        self.assertEqual(r.status_code, 400)
        r = self.client.put("/users/me/profile", headers=self.token("asha"), json={"display_name": "a" * 81})
        self.assertEqual(r.status_code, 400)

    def test_refusals_by_sqlstate(self):
        self.assertEqual(self.client.get("/users/people", headers=self.token("asha")).status_code, 403)
        r = self.client.delete("/users/people/asha/roles/admin", headers=self.token("asha"))
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
```

Expect `OK` for each service, py-api's with the
starter's tests and these:

``` sh
make test
```

## 5 Run It

**The dev stack:** `make dev` builds py-api again and
starts it. **The native stack:** stop, install its
packages, and start:

``` sh
tools/native-dev.sh stop
tools/native-dev.sh init
tools/native-dev.sh start
```

Expect `py-api health 200`:

``` sh
tools/native-dev.sh status
```

Then [the refinement](5-refinement.md).

## 6 What Reaches the Box

A tag: py-api's image is built again, and the
manifest's change handed to the box's owner. No new
host, image or build: `/users` is py-api's, so the
owner renders its allow-list again and the new routes
answer ([Hand a change to the box's
owner](../../onboarding/hand-over.md)).

The box must also give py-api **`userInfo`'s address**,
`COGNITO_USERINFO_URL`, with the issuer, in the
project's `cognito.env`: Cognito's own domain, not the
issuer's. Until the owner adds it, `/users/me` records
no one, since it cannot learn an e-mail. And the
database waits for the box's `feature/postgres`.

## 7 See Also

- [The refinement](5-refinement.md): next
- [Develop and change py-api](../../py-api/develop.md):
  the starter this came from
- [psycopg 3](https://www.psycopg.org/psycopg3/docs/),
  read 2026-10-06
- [FastAPI's bigger
  applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/):
  `APIRouter` and its prefix, read 2026-10-06
