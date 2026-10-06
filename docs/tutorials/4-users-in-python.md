---
abstract: |
  The users unit as a Python service, from the py-api
  starter: the door at `/me`, which asks Cognito's
  userInfo and the database who may come in, and the
  people and their roles for whoever may run them.
  FastAPI and psycopg, the database's refusals turned
  into HTTP, tests that need no database, and the
  service run behind the stack's nginx.
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
title: 4 The users Service in Python
version: v0.1.0
---

## 1 Before You Start

- [3 Make it a migration](3-the-migration.md), with
  `services/users/` copied from `services/py-api/`, and
  its migrations applied
- Python 3.12, as the image's
- The JavaScript version is [tutorial
  5](5-users-in-javascript.md): the same routes, take
  one

## 2 The Routes

- **`GET /health`,** anyone: the box's check
- **`GET /me`,** signed in: the door. It admits you if
  the rules let you in, then answers who you are, your
  roles and your permissions
- **`GET /people`,** `users.read`: everyone in, with
  their roles
- **`GET /roles`,** `users.read`: the matrix, role by
  role
- **`PUT /people/{sub}/roles/{role}`,** `users.grant`:
  give a role
- **`DELETE /people/{sub}/roles/{role}`,**
  `users.grant`: take it away

Put them in the manifest, as the users service's
`routes`, in place of tutorial 3's `/health` alone:

``` json
[
  {
    "method": "GET",
    "path": "/health",
    "signed_in": false
  },
  {
    "method": "GET",
    "path": "/me",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/people",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/roles",
    "signed_in": true
  },
  {
    "method": "PUT",
    "path": "/people/{sub}/roles/{role}",
    "signed_in": true
  },
  {
    "method": "DELETE",
    "path": "/people/{sub}/roles/{role}",
    "signed_in": true
  }
]
```

nginx passes these and nothing else. A `{sub}` or
`{role}` is letters, digits, `-` and `_`, up to 64: a
Cognito `sub` is a UUID, and fits.

## 3 Its Packages

psycopg 3, the PostgreSQL driver, with its binary build
and its pool. In `services/users/requirements.txt`, the
three lines among the others, by version, as every
package there is:

``` text
psycopg[binary]==3.3.6
psycopg-binary==3.3.6
psycopg-pool==3.3.3
```

The binary build has wheels for arm64, the box's, and
x86-64, so nothing compiles.

## 4 The Code

`services/users/main.py`, whole:

``` python
"""users, at users.<your zone>: who may come in, and what each person
may do (docs/tutorials/4-users-in-python.md)

    GET    /health                      the box's and the probes' check
    GET    /me                          the door: admits the caller if the
                                        rules let them in, then says who
                                        they are and what they may do
    GET    /people                      everyone admitted: users.read
    GET    /roles                       the matrix, role by role: users.read
    PUT    /people/{sub}/roles/{role}   give a role: users.grant
    DELETE /people/{sub}/roles/{role}   take it away: users.grant

Who the caller is, from their access token, as every starter checks it;
their e-mail from Cognito's userInfo, since an access token carries
none. What they may do, the database decides: every accessor takes the
caller first and refuses with SQLSTATE 42501, which becomes 403 here.
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
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

SERVICE = os.environ.get("SERVICE", "users")

ISSUER = os.environ.get("COGNITO_ISSUER", "")
CLIENTS = [c for c in (os.environ.get("COGNITO_UI_CLIENT_ID"), os.environ.get("COGNITO_PROBE_CLIENT_ID")) if c]
USERINFO = os.environ.get("COGNITO_USERINFO_URL", "")

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
    """The caller's sub and token, if the token is the pool's access
    token for one of our clients and unexpired; None otherwise"""
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
    return {"sub": claims["sub"], "token": m[1]}


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

@asynccontextmanager
async def lifespan(_app):
    if pool.conninfo:
        pool.open(wait=False)
    yield
    pool.close()


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


NOSTORE = {"Cache-Control": "no-store"}


def answer(data, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status, headers=NOSTORE)


def signed_out() -> JSONResponse:
    return JSONResponse({"error": "sign in first"}, 401, headers={**NOSTORE, "WWW-Authenticate": 'Bearer realm="users"'})


def run(sql: str, args: tuple) -> JSONResponse | list[dict]:
    """The accessor's rows, or its refusal as an answer"""
    try:
        return query(sql, args)
    except psycopg.Error as e:
        if e.sqlstate in STATUS:
            return answer({"error": e.diag.message_primary or str(e)}, STATUS[e.sqlstate])
        raise
    except PoolTimeout:
        return answer({"error": "the database is not answering"}, 503)


def rows(x):
    if isinstance(x, JSONResponse):
        return x
    for r in x:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return x


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE}


@app.get("/me")
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
    r = rows(run("SELECT * FROM users_me(%s)", (who["sub"],)))
    return r if isinstance(r, JSONResponse) else answer(r[0])


@app.get("/people")
def people(authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = rows(run("SELECT * FROM users_list(%s)", (who["sub"],)))
    return r if isinstance(r, JSONResponse) else answer(r)


@app.get("/roles")
def roles(authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM users_matrix(%s)", (who["sub"],))
    return r if isinstance(r, JSONResponse) else answer(r)


@app.put("/people/{sub}/roles/{role}")
def grant(sub: str, role: str, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT users_grant(%s, %s, %s)", (who["sub"], sub, role))
    return r if isinstance(r, JSONResponse) else answer({"sub": sub, "role": role, "granted": True})


@app.delete("/people/{sub}/roles/{role}")
def revoke(sub: str, role: str, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT users_revoke(%s, %s, %s)", (who["sub"], sub, role))
    return r if isinstance(r, JSONResponse) else answer({"sub": sub, "role": role, "granted": False})
```

What each part does:

- **`caller`:** the starter's check of the token,
  unchanged but for keeping the token itself, which
  userInfo needs
- **`email_of`:** asks userInfo with the caller's own
  token, keeps the answer ten minutes, and reads
  `email_verified` as the string it is. The `sub` it
  answers must be the token's
- **`pool`:** four connections at most, as the
  project's login, `DATABASE_URL`. Opened without
  waiting: the service starts and answers `/health`
  with the database down, and a route that needs it
  answers `503`
- **`query`:** one statement, its rows. The tests
  replace it
- **`run` and `STATUS`:** an accessor's refusal, by its
  SQLSTATE, as HTTP, with its message
- **The routes:** each `def`, not `async def`. FastAPI
  runs them in its thread pool, where the token check
  and psycopg may block. Each passes the caller first;
  none checks a permission itself

## 5 Its Tests

Offline: a key pair and a userInfo of their own on a
local port, and the database replaced by what the
accessors would answer.
`services/users/test/test_main.py`:

``` python
"""The routes, the token check and the door, against a pool of our own:
a key pair made here, its public half served as the pool's JWKS, and a
userInfo, on a local port. The database is replaced by a function that
answers as the accessors would. Nothing leaves the machine:

    python -m unittest discover -s test
"""

import importlib
import json
import os
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
            body = {"keys": [{**JWK, "kid": "k1", "alg": "RS256", "use": "sig"}]}
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


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = HTTPServer(("127.0.0.1", 0), Pool)
        threading.Thread(target=cls.pool.serve_forever, daemon=True).start()
        cls.issuer = f"http://127.0.0.1:{cls.pool.server_port}"
        os.environ.update(COGNITO_ISSUER=cls.issuer, COGNITO_UI_CLIENT_ID="ui-client",
                          COGNITO_PROBE_CLIENT_ID="probe-client", COGNITO_USERINFO_URL=f"{cls.issuer}/oauth2/userInfo")
        os.environ.pop("DATABASE_URL", None)
        from fastapi.testclient import TestClient

        cls.main = importlib.import_module("main")
        cls.main.query = database
        cls.client = TestClient(cls.main.app)

    @classmethod
    def tearDownClass(cls):
        cls.pool.shutdown()

    def token(self, sub, **over):
        now = int(time.time())
        claims = {"iss": self.issuer, "sub": sub, "iat": now, "exp": now + 300, "token_use": "access",
                  "client_id": "ui-client", **over}
        return {"Authorization": "Bearer " + jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": "k1"})}

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok", "service": "users"})

    def test_me_signed_out(self):
        self.assertEqual(self.client.get("/me").status_code, 401)

    def test_me_another_client(self):
        self.assertEqual(self.client.get("/me", headers=self.token("alice", client_id="other")).status_code, 401)

    def test_me_admitted(self):
        r = self.client.get("/me", headers=self.token("alice"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["roles"], ["deny-all"])

    def test_me_unverified(self):
        r = self.client.get("/me", headers=self.token("eve"))
        self.assertEqual((r.status_code, r.json()["error"]), (403, "not admitted"))

    def test_refusals_by_sqlstate(self):
        self.assertEqual(self.client.get("/people", headers=self.token("alice")).status_code, 403)
        r = self.client.delete("/people/alice/roles/admin", headers=self.token("alice"))
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
```

Expect `OK` for each service, users among them:

``` sh
make test
```

## 6 Run It

**The dev stack:** `make dev` builds the new service
and starts it. **The native stack:** stop, install its
packages, and start:

``` sh
tools/native-dev.sh stop
tools/native-dev.sh init
tools/native-dev.sh start
```

Expect `users health 200`:

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
curl -s -H "Authorization: Bearer ${Y}" http://users.${H}/me
curl -s -H "Authorization: Bearer ${A}" http://users.${H}/me
curl -s -H "Authorization: Bearer ${E}" http://users.${H}/me
```

The people, which alice may not read,
`users.read needed`, and you may:

``` sh
curl -s -H "Authorization: Bearer ${A}" http://users.${H}/people
curl -s -H "Authorization: Bearer ${Y}" http://users.${H}/people
```

Alice a member. Expect `"granted":true`, then alice
with `notes.read` and `notes.write`:

``` sh
curl -s -X PUT -H "Authorization: Bearer ${Y}" http://users.${H}/people/alice/roles/member
curl -s -H "Authorization: Bearer ${A}" http://users.${H}/me
```

And the refusals. Expect `no such person` (`404`), then
`the last users.grant` (`409`):

``` sh
curl -s -X PUT -H "Authorization: Bearer ${Y}" http://users.${H}/people/nobody/roles/member
curl -s -X DELETE -H "Authorization: Bearer ${Y}" http://users.${H}/people/you/roles/admin
```

## 8 What Reaches the Box

A tag: the `users` image is built, and the manifest's
change handed to the box's owner. A new service is a
new host, `users.<zone>`, a new image and a new build,
so the owner rolls it out before the routes answer
([Hand a change to the box's
owner](../onboarding/hand-over.md)).

The box must also give the service **`userInfo`'s
address**, `COGNITO_USERINFO_URL`, with the issuer, in
the project's `cognito.env`: Cognito's own domain, not
the issuer's. Until the owner adds it, `/me` admits no
one, since it cannot learn an e-mail. And the database
waits for the box's `feature/postgres`.

## 9 What Can Go Wrong

- **`/me` says `not admitted`, `"verified": false`, for
  everyone.** `COGNITO_USERINFO_URL` is unset: the
  service asks no one, and admits no one. Or the box's
  pool does not map `email_verified`
- **`503`, `the database is not answering`.** The pool
  could not connect within five seconds:
  `DATABASE_URL`, or the database is down
- **`500`, and
  `function users_admit(...) does not exist` in the
  log.** The migrations have not run:
  `make db CMD=status`
- **Every route `404` but `/health`.** The manifest
  still names `/health` alone, or nginx was not
  rendered again: `make dev`, or the native stack's
  `start`
- **`403` from nginx, an HTML page, not JSON.** A
  method the manifest does not name for that path

## 10 See Also

- [6 A Svelte UI](6-a-svelte-ui.md): next
- [Develop and change py-api](../py-api/develop.md):
  the starter this came from
- [psycopg 3](https://www.psycopg.org/psycopg3/docs/),
  read 2026-10-06
