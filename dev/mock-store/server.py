"""A stand-in for the project's static bucket, for local development only.

The parts of S3 a service touches when it stores an upload, and no
more, at S3's path-style address, /<bucket>/<key>:

    PUT    /<bucket>/objects/<key>   the body, unsigned, as the box's own
                                     uploads go; x-amz-checksum-sha256,
                                     if sent, matched to the body, else
                                     400 BadDigest, as S3 does
    DELETE /<bucket>/objects/<key>   204, whether or not it was there
    GET    /<bucket>/objects/<key>   the object, with the Content-Type and
                                     Cache-Control it was stored with

Only keys under objects/: the rest of the bucket is the release's
static/, which the dev stack's nginx serves from the folder. Writes go
to ROOT, which nothing else writes. Python's standard library alone.

Anyone who reaches it can write: never run it anywhere but a
developer's machine.
"""

import base64
import hashlib
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BUCKET = os.environ.get("BUCKET", "static.localhost")
PORT = int(os.environ.get("PORT", "9100"))
# This machine alone, unless told: the dev stack's container is told
# 0.0.0.0, so the services and nginx reach it on the stack's network
BIND = os.environ.get("BIND", "127.0.0.1")
ROOT = Path(os.environ.get("ROOT", "store")).resolve()
MAX = 10 * 1024 * 1024
KEY = re.compile(r"^/([^/]+)/(objects/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*)$")


def error(code: str, message: str) -> bytes:
    return f"<Error><Code>{code}</Code><Message>{message}</Message></Error>".encode()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes = b"", headers: dict | None = None):
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _key(self) -> Path | None:
        m = KEY.match(self.path.split("?")[0])
        if not m or m[1] != BUCKET or ".." in m[2].split("/"):
            self._send(404, error("NoSuchKey", "only objects/ in this bucket"), {"Content-Type": "application/xml"})
            return None
        return Path(m[2])

    def do_PUT(self):
        key = self._key()
        if key is None:
            return
        n = int(self.headers.get("Content-Length") or -1)
        if not 0 <= n <= MAX:
            return self._send(400, error("EntityTooLarge", "a length, and at most 10 MiB"), {"Content-Type": "application/xml"})
        body = self.rfile.read(n)
        digest = hashlib.sha256(body).digest()
        sent = self.headers.get("x-amz-checksum-sha256")
        if sent is not None and sent != base64.b64encode(digest).decode():
            return self._send(400, error("BadDigest", "the body does not match x-amz-checksum-sha256"),
                              {"Content-Type": "application/xml"})
        (ROOT / "data" / key).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / "meta" / key).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / key).write_bytes(body)
        meta = {"Content-Type": self.headers.get("Content-Type", "binary/octet-stream"),
                "ETag": f'"{hashlib.md5(body).hexdigest()}"'}
        if self.headers.get("Cache-Control"):
            meta["Cache-Control"] = self.headers["Cache-Control"]
        (ROOT / "meta" / key).write_text(json.dumps(meta))
        self._send(200, headers={"ETag": meta["ETag"]})

    def do_DELETE(self):
        key = self._key()
        if key is None:
            return
        for d in ("data", "meta"):
            (ROOT / d / key).unlink(missing_ok=True)
        self._send(204)

    def do_GET(self):
        key = self._key()
        if key is None:
            return
        f = ROOT / "data" / key
        if not f.is_file():
            return self._send(404, error("NoSuchKey", "no such key"), {"Content-Type": "application/xml"})
        self._send(200, f.read_bytes(), json.loads((ROOT / "meta" / key).read_text()))

    do_HEAD = do_GET

    def log_message(self, fmt, *args):
        print(json.dumps({"mock-store": fmt % args}), flush=True)


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"mock-store": f"bucket {BUCKET}, {BIND}:{PORT}, into {ROOT}"}), flush=True)
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
