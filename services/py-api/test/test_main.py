"""The routes and the token check, against a pool of our own: a key
pair made here, its public half served as the pool's JWKS on a local
port. Nothing leaves the machine. Needs requirements.txt and httpx,
for FastAPI's test client:

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
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _pair():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return k, json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(k.public_key()))


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key, jwk = _pair()
        cls.other, _ = _pair()
        body = json.dumps({"keys": [{**jwk, "kid": "k1", "alg": "RS256", "use": "sig"}]}).encode()

        class Pool(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        cls.pool = HTTPServer(("127.0.0.1", 0), Pool)
        threading.Thread(target=cls.pool.serve_forever, daemon=True).start()
        cls.issuer = f"http://127.0.0.1:{cls.pool.server_port}"
        os.environ.update(
            COGNITO_ISSUER=cls.issuer, COGNITO_UI_CLIENT_ID="ui-client", COGNITO_PROBE_CLIENT_ID="probe-client"
        )
        from fastapi.testclient import TestClient

        cls.main = importlib.import_module("main")
        cls.client = TestClient(cls.main.app)

    @classmethod
    def tearDownClass(cls):
        cls.pool.shutdown()

    def sign(self, key=None, iss=None, **claims):
        now = int(time.time())
        c = {"iss": iss or self.issuer, "sub": "user-1", "iat": now, "exp": now + 300, **claims}
        return jwt.encode(c, key or self.key, algorithm="RS256", headers={"kid": "k1"})

    def echo(self, auth=None, **kw):
        h = {"Authorization": auth} if auth else {}
        return self.client.post("/echo", headers=h, **({"json": {"a": 1}} | kw))

    def test_health_and_hello_answer_anyone(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok", "service": "py-api"})
        self.assertEqual(self.client.get("/hello").status_code, 200)
        self.assertEqual(self.client.get("/docs").status_code, 404)

    def test_echo_refuses_no_token_a_bad_one_and_the_wrong_kind(self):
        self.assertEqual(self.echo().status_code, 401)
        self.assertEqual(self.echo("Bearer not.a.token").status_code, 401)
        self.assertEqual(self.echo(f"Bearer {self.sign(token_use='id', client_id='ui-client')}").status_code, 401)
        self.assertEqual(self.echo(f"Bearer {self.sign(token_use='access', client_id='neighbour')}").status_code, 401)
        self.assertEqual(
            self.echo(f"Bearer {self.sign(self.other, token_use='access', client_id='ui-client')}").status_code, 401
        )
        self.assertEqual(
            self.echo(f"Bearer {self.sign(iss='https://elsewhere', token_use='access', client_id='ui-client')}").status_code,
            401,
        )
        r = self.echo()
        self.assertTrue(r.headers["www-authenticate"].startswith("Bearer"))
        self.assertEqual(r.headers["cache-control"], "no-store")

    def test_echo_answers_the_uis_and_the_probes_access_tokens(self):
        for c in ("ui-client", "probe-client"):
            t = self.sign(token_use="access", client_id=c, **{"cognito:groups": ["admin"]})
            r = self.echo(f"Bearer {t}")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), {"service": "py-api", "caller": "user-1", "groups": ["admin"], "body": {"a": 1}})

    def test_a_body_over_1_mib_is_refused(self):
        t = self.sign(token_use="access", client_id="ui-client")
        r = self.echo(f"Bearer {t}", json=None, content=b"x" * (1024 * 1024 + 1))
        self.assertEqual(r.status_code, 413)


if __name__ == "__main__":
    unittest.main()
