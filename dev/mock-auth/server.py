"""A stand-in for the box's Cognito pool, for local development only.

The parts of Cognito the project touches, and no more:

    GET  /.well-known/jwks.json   the pool's public keys
    GET  /oauth2/authorize        the hosted sign-in: a form, then a code
    POST /oauth2/token            the code and its PKCE verifier for tokens
    GET  /logout                  back to the logout URI
    POST /dev/token               a token for curl and the tests:
                                  {"sub", "groups", "client_id", "email"}

Its tokens have Cognito's shape: an access token with token_use
"access", client_id, cognito:groups and username; an ID token with
token_use "id", aud and email. Both signed RS256 by a key made at
start, so a restart signs out everyone. The issuer is ISSUER, the
name the services reach this server by, whatever name the browser
used.

Anyone can sign in as anyone: never run it anywhere but a developer's
machine.
"""

import base64
import hashlib
import html
import json
import os
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = os.environ.get("ISSUER", "http://localhost:9000")
PORT = int(os.environ.get("PORT", "9000"))
# This machine alone, unless told: the dev stack's container is told
# 0.0.0.0, so the services reach it on the stack's network
BIND = os.environ.get("BIND", "127.0.0.1")
CLIENTS = {c for c in os.environ.get("CLIENTS", "dev-ui,dev-probe").split(",") if c}
# Origins whose pages may call the token endpoint, as Cognito allows a
# public client's own
ORIGINS = {o for o in os.environ.get("ORIGINS", "http://localhost:5173").split(",") if o}
LIFE = 3600

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KID = secrets.token_hex(8)
JWKS = {"keys": [{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key())), "kid": KID, "alg": "RS256",
                  "use": "sig"}]}
CODES: dict[str, dict] = {}


def tokens(sub: str, client_id: str, groups: list[str], email: str) -> dict:
    now = int(time.time())
    base = {"iss": ISSUER, "sub": sub, "iat": now, "exp": now + LIFE}
    access = {**base, "token_use": "access", "client_id": client_id, "username": sub, "cognito:groups": groups,
              "scope": "openid email"}
    ident = {**base, "token_use": "id", "aud": client_id, "email": email, "email_verified": True,
             "cognito:groups": groups}
    sign = lambda c: jwt.encode(c, KEY, algorithm="RS256", headers={"kid": KID})  # noqa: E731
    return {"access_token": sign(access), "id_token": sign(ident), "token_type": "Bearer", "expires_in": LIFE}


def challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


FORM = """<!doctype html><meta charset="utf-8"><title>Mock sign-in</title>
<style>body{{font:16px system-ui;max-width:24rem;margin:3rem auto;padding:0 1rem}}
input{{font:inherit;width:100%;margin:.25rem 0 1rem}}</style>
<h1>Mock sign-in</h1><p>Local development only: any name is accepted.</p>
<form method="post" action="/oauth2/authorize?{query}">
<label>User <input name="sub" value="dev-user"></label>
<label>Email <input name="email" value="dev-user@example.org"></label>
<label>Groups, comma-separated <input name="groups" value=""></label>
<button>Sign in</button></form>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes = b"", ctype: str = "application/json", headers: dict | None = None):
        self.send_response(code)
        origin = self.headers.get("Origin", "")
        if origin in ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        if body:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj).encode())

    def _form(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode() if n else ""
        if self.headers.get("Content-Type", "").startswith("application/json"):
            return json.loads(raw or "{}")
        return {k: v[0] for k, v in parse_qs(raw).items()}

    def do_OPTIONS(self):
        self._send(204, headers={"Access-Control-Allow-Methods": "GET, POST",
                                 "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "7200"})

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/.well-known/jwks.json":
            return self._json(200, JWKS)
        if u.path == "/oauth2/authorize":
            if q.get("client_id") not in CLIENTS or q.get("response_type") != "code":
                return self._json(400, {"error": "unauthorized_client"})
            return self._send(200, FORM.format(query=html.escape(u.query)).encode(), "text/html; charset=utf-8")
        if u.path == "/logout":
            return self._send(302, headers={"Location": q.get("logout_uri", "/")})
        if u.path == "/health":
            return self._json(200, {"status": "ok", "service": "mock-auth"})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        f = self._form()
        if u.path == "/oauth2/authorize":
            code = secrets.token_urlsafe(24)
            CODES[code] = {"sub": f.get("sub") or "dev-user", "email": f.get("email", ""),
                           "groups": [g.strip() for g in f.get("groups", "").split(",") if g.strip()],
                           "client_id": q.get("client_id"), "redirect_uri": q.get("redirect_uri"),
                           "challenge": q.get("code_challenge", ""), "at": time.time()}
            back = f"{q.get('redirect_uri', '/')}?{urlencode({'code': code, 'state': q.get('state', '')})}"
            return self._send(302, headers={"Location": back})
        if u.path == "/oauth2/token":
            c = CODES.pop(f.get("code", ""), None)
            if (not c or time.time() - c["at"] > 300 or f.get("grant_type") != "authorization_code"
                    or f.get("client_id") != c["client_id"] or f.get("redirect_uri") != c["redirect_uri"]
                    or challenge(f.get("code_verifier", "")) != c["challenge"]):
                return self._json(400, {"error": "invalid_grant"})
            return self._json(200, tokens(c["sub"], c["client_id"], c["groups"], c["email"]))
        if u.path == "/dev/token":
            client = f.get("client_id", "dev-probe")
            if client not in CLIENTS:
                return self._json(400, {"error": "unauthorized_client"})
            return self._json(200, tokens(f.get("sub", "dev-user"), client, list(f.get("groups", [])),
                                          f.get("email", "dev-user@example.org")))
        self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print(json.dumps({"mock-auth": fmt % args}), flush=True)


if __name__ == "__main__":
    print(json.dumps({"mock-auth": f"issuer {ISSUER}, {BIND}:{PORT}, clients {sorted(CLIENTS)}"}), flush=True)
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
