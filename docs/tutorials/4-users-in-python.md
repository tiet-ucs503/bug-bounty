---
abstract: |
  `/users` as routes of py-api, at
  `py-api.<zone>/users`: the door at `/users/me`, which
  asks Cognito's userInfo and the database who may come
  in, and the people and their roles for whoever may
  run them. FastAPI and psycopg, the database's
  refusals turned into HTTP, tests that need no
  database, and the routes run behind the stack's
  nginx.
date: 2026-10-06
keywords:
- tutorial
- py-api
- python
- auth
- authz
- db
kind: tutorial
sources:
- services/py-api/main.py
- services/py-api/requirements.txt
- box/project.json
status: draft
subtitle: FastAPI, psycopg, and the database deciding
title: 4 /users in Python, in py-api
version: v0.1.0
---

`[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](README.md) §5.

## 1 Before You Start

- [What you need](README.md) §2, installed and checked
- [3 Make it a migration](3-the-migration.md), its
  migrations applied, with `users` among py-api's
  `prefixes` (§2 there)
- The JavaScript version is [tutorial
  5](5-users-in-javascript.md): the same routes, in
  js-api; take one

## 2 The Routes

`/users` is a part of py-api, not a service of its own:
the same host, `py-api.<zone>`, the same image and the
same process, its routes under `/users`. Its tables are
its own, `users_*`, by the prefix py-api owns beside
`py_api`.

- **`GET /users/me`,** signed in: the door. It admits
  you if the rules let you in, then answers who you
  are, your roles and your permissions
- **`GET /users/people`,** `users.read`: everyone in,
  with their roles
- **`GET /users/roles`,** `users.read`: the matrix,
  role by role
- **`PUT /users/people/{sub}/roles/{role}`,**
  `users.grant`: give a role
- **`DELETE /users/people/{sub}/roles/{role}`,**
  `users.grant`: take it away

Add them to py-api's `routes` in the manifest, after
the starter's three:

``` json
[
  {
    "method": "GET",
    "path": "/users/me",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/users/people",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/users/roles",
    "signed_in": true
  },
  {
    "method": "PUT",
    "path": "/users/people/{sub}/roles/{role}",
    "signed_in": true
  },
  {
    "method": "DELETE",
    "path": "/users/people/{sub}/roles/{role}",
    "signed_in": true
  }
]
```

nginx passes these and nothing else. A `{sub}` or
`{role}` is letters, digits, `-` and `_`, up to 64: a
Cognito `sub` is a UUID, and fits.

## 3 Its Packages

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

## 4 The Code

`services/py-api/main.py`, whole, as this page leaves
it: the starter, and what `/users` adds.

``` python
"""A starter service in Python, at py-api.<your zone>

The starter's three routes show the shape every service keeps; the
rest are yours.

    GET  /health   the box's and the probes' check; keep it
    GET  /hello    anyone
    POST /echo     a signed-in caller: the body back, with who sent it

and who comes in, and what each may do, the database deciding
(docs/tutorials/4-users-in-python.md):

    GET    /users/me                          the door: admits the caller
                                              if the rules let them in,
                                              then says who they are and
                                              what they may do
    GET    /users/people                      everyone admitted: users.read
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
caller first, and its refusals by SQLSTATE become 403, 404 and 409
here.
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
from fastapi import APIRouter, FastAPI, Header, Request
from fastapi.responses import JSONResponse
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
    """The caller's sub, groups and token, if the token is the pool's access
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
    return {"sub": claims["sub"], "groups": claims.get("cognito:groups", []), "token": m[1]}


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


# No /docs, /redoc or /openapi.json: nginx's allow-list would refuse
# them in any case
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


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


# /users: who may come in, and what each person may do; the database
# decides (docs/tutorials/4-users-in-python.md). Sync routes: FastAPI
# runs each in its thread pool, so userInfo and the database may block
users = APIRouter(prefix="/users")


@users.get("/me")
def me(authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    try:
        email, verified = email_of(who)
    except OSError:
        return answer({"error": "Cognito's userInfo is not answering"}, 503)
    r = run("SELECT users_admit(%s, %s, %s) AS admitted", (who["sub"], email, verified))
    if isinstance(r, JSONResponse):
        return r
    if not r[0]["admitted"]:
        return answer({"error": "not admitted", "email": email, "verified": verified}, 403)
    r = run("SELECT * FROM users_me(%s)", (who["sub"],))
    return r if isinstance(r, JSONResponse) else answer(r[0])


@users.get("/people")
def people(authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM users_list(%s)", (who["sub"],))
    return r if isinstance(r, JSONResponse) else answer(r)


@users.get("/roles")
def roles(authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM users_matrix(%s)", (who["sub"],))
    return r if isinstance(r, JSONResponse) else answer(r)


@users.put("/people/{sub}/roles/{role}")
def grant(sub: str, role: str, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT users_grant(%s, %s, %s)", (who["sub"], sub, role))
    return r if isinstance(r, JSONResponse) else answer({"sub": sub, "role": role, "granted": True})


@users.delete("/people/{sub}/roles/{role}")
def revoke(sub: str, role: str, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT users_revoke(%s, %s, %s)", (who["sub"], sub, role))
    return r if isinstance(r, JSONResponse) else answer({"sub": sub, "role": role, "granted": False})


app.include_router(users)
```

What it adds to the starter:

- **`USERINFO`:** Cognito's userInfo, from
  `COGNITO_USERINFO_URL`
- **`caller`:** the starter's check of the token,
  unchanged but for keeping the token itself, which
  userInfo needs
- **`email_of`:** asks userInfo with the caller's own
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
  SQLSTATE, as HTTP, with its message
- **`users`, an `APIRouter` with the prefix `/users`:**
  the routes, each `def`, not `async def`. FastAPI runs
  them in its thread pool, where the token check and
  psycopg may block. Each passes the caller first; none
  checks a permission itself. `app.include_router`
  mounts them
- **The starter's three,** `/health`, `/hello` and
  `/echo`, as they were

Tutorial 6's notes use the same `pool`, `run` and
`answer`.

## 5 Its Tests

Offline: a key pair and a userInfo of their own on a
local port, and the database replaced by what the
accessors would answer. The starter's tests share
`main` in the same process, so these set the pool's
address and the database on it, and put them back.
`services/py-api/test/test_users.py`:

``` python
"""/users: the token check and the door, against a pool of our own: a
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
EMAILS = {"alice": ("alice@example.org", "true"), "eve": ("eve@example.org", "false")}


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


def database(sql, args):
    """The accessors, as the tests need them"""
    if sql.startswith("SELECT users_admit"):
        sub, email, verified = args
        return [{"admitted": verified and email.endswith("@example.org")}]
    if sql.startswith("SELECT * FROM users_me"):
        return [{"sub": args[0], "email": "alice@example.org", "roles": ["deny-all"], "permissions": []}]
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
        self.assertEqual(self.client.get("/users/me", headers=self.token("alice", client_id="other")).status_code, 401)

    def test_me_admitted(self):
        r = self.client.get("/users/me", headers=self.token("alice"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["roles"], ["deny-all"])

    def test_me_unverified(self):
        r = self.client.get("/users/me", headers=self.token("eve"))
        self.assertEqual((r.status_code, r.json()["error"]), (403, "not admitted"))

    def test_refusals_by_sqlstate(self):
        self.assertEqual(self.client.get("/users/people", headers=self.token("alice")).status_code, 403)
        r = self.client.delete("/users/people/alice/roles/admin", headers=self.token("alice"))
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
```

Expect `OK` for each service, py-api's with the
starter's tests and these:

``` sh
make test
```

## 6 Run It

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

## 7 Call It

Three people: you, the first admin by tutorial 3's
migration; alice; and eve, whose e-mail is not
verified:

``` sh
Y=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=you EMAIL=you@example.org)
A=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=alice)
E=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=eve VERIFIED=false)
```

The door. Expect you with `["admin"]`, alice with
`["deny-all"]` and no permissions, and eve `403`,
`not admitted`:

``` sh
curl -s -H "Authorization: Bearer ${Y}" http://py-api.${H}/users/me
curl -s -H "Authorization: Bearer ${A}" http://py-api.${H}/users/me
curl -s -H "Authorization: Bearer ${E}" http://py-api.${H}/users/me
```

The people, which alice may not read,
`users.read needed`, and you may:

``` sh
curl -s -H "Authorization: Bearer ${A}" http://py-api.${H}/users/people
curl -s -H "Authorization: Bearer ${Y}" http://py-api.${H}/users/people
```

Alice a member. Expect `"granted":true`, then alice
with `notes.read` and `notes.write`:

``` sh
curl -s -X PUT -H "Authorization: Bearer ${Y}" http://py-api.${H}/users/people/alice/roles/member
curl -s -H "Authorization: Bearer ${A}" http://py-api.${H}/users/me
```

And the refusals. Expect `no such person` (`404`), then
`the last users.grant` (`409`):

``` sh
curl -s -X PUT -H "Authorization: Bearer ${Y}" http://py-api.${H}/users/people/nobody/roles/member
curl -s -X DELETE -H "Authorization: Bearer ${Y}" http://py-api.${H}/users/people/you/roles/admin
```

## 8 What Reaches the Box

A tag: py-api's image is built again, and the
manifest's change handed to the box's owner. No new
host, image or build: `/users` is py-api's, so the
owner renders its allow-list again and the new routes
answer ([Hand a change to the box's
owner](../onboarding/hand-over.md)).

The box must also give py-api **`userInfo`'s address**,
`COGNITO_USERINFO_URL`, with the issuer, in the
project's `cognito.env`: Cognito's own domain, not the
issuer's. Until the owner adds it, `/users/me` admits
no one, since it cannot learn an e-mail. And the
database waits for the box's `feature/postgres`.

## 9 What Can Go Wrong

- **`/users/me` says `not admitted`,
  `"verified": false`, for everyone.**
  `COGNITO_USERINFO_URL` is unset: the service asks no
  one, and admits no one. Or the box's pool does not
  map `email_verified`
- **`503`, `the database is not answering`.** The pool
  could not connect within five seconds:
  `DATABASE_URL`, or the database is down
- **`500`, and
  `function users_admit(...) does not exist` in the
  log.** The migrations have not run:
  `make db CMD=status`
- **Every `/users` route `404`.** The manifest does not
  name them for py-api, or nginx was not rendered
  again: `make dev`, or the native stack's `start`
- **`make check` refuses a `users_` migration.**
  `users` is not among py-api's `prefixes`: tutorial 3
  §2
- **`403` from nginx, an HTML page, not JSON.** A
  method the manifest does not name for that path

## 10 See Also

- [6 A Svelte UI](6-a-svelte-ui.md): next
- [Develop and change py-api](../py-api/develop.md):
  the starter this came from
- [psycopg 3](https://www.psycopg.org/psycopg3/docs/),
  read 2026-10-06
- [FastAPI's bigger
  applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/):
  `APIRouter` and its prefix, read 2026-10-06
