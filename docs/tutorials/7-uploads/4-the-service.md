---
abstract: |
  Step 4 of tutorial 7, part 3. py-api's half of the
  uploads: a route that takes a file's bytes, names
  them, writes the row, stores the object and confirms
  it; a route that sets a note's objects; and the
  collector, which deletes from the bucket what no note
  needs, then forgets it. Tested offline, then end to
  end through nginx, with a collector made quick.
date: 2026-10-06
keywords:
- tutorial
- uploads
- py-api
- python
- s3
kind: tutorial
sources:
- services/py-api/main.py
- box/project.json
status: draft
subtitle: Upload, link, collect
title: "7.4 Uploads: the Service"
version: v0.1.0
---

## 1 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [The database](4-the-database.md), applied
- py-api with tutorial 5's notes routes

## 2 The Routes

  --------------------------------------------------------
  Route                       Who               What
  --------------------------- ----------------- ----------
  `POST /objects/new`         `objects.write`   the body
                                                is the
                                                file;
                                                answers
                                                its key
                                                and URL

  `GET /objects/mine`         signed in         your
                                                objects,
                                                each with
                                                its refs

  `PUT /notes/{id}/objects`   `notes.write`,    the note's
                              the owner         whole list
                                                of keys
  --------------------------------------------------------

Under `/objects/`, where the box's zone counts requests
against Cloudflare's rate limit. Add them to py-api's
routes in the manifest:

``` json
[
  {
    "method": "POST",
    "path": "/objects/new",
    "signed_in": true
  },
  {
    "method": "GET",
    "path": "/objects/mine",
    "signed_in": true
  },
  {
    "method": "PUT",
    "path": "/notes/{id}/objects",
    "signed_in": true
  }
]
```

The body of an upload **is** the file, with its own
type in `Content-Type`: no form, no multipart, nothing
to parse.

## 3 The Code

To `services/py-api/main.py`'s imports, from the
standard library:

``` python
import base64
import hashlib
import logging
import urllib.error
```

The collector starts with the pool, in `lifespan`:

``` python
@asynccontextmanager
async def lifespan(_app):
    if pool.conninfo:
        pool.open(wait=False)
        threading.Thread(target=collector, daemon=True).start()
    yield
    pool.close()
```

`GET /notes` now calls `py_api_notes_page`, so each
note brings its objects:

``` python
    r = run("SELECT * FROM py_api_notes_page(%s, %s)", (who["sub"], before))
```

And at the end of the file:

``` python
# The static bucket: written at S3's path-style address, from the box,
# unsigned; read through Cloudflare at static.<zone>. From the box's
# store.env, or the dev stack's mock
STORE_URL = os.environ.get("STORE_URL", "")
STATIC_URL = os.environ.get("STATIC_URL", "")

# What may be uploaded, by the type the browser gives. Never HTML or
# SVG: static.<zone> would serve them as pages, scripts and all
TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf", "text/plain"}


def store(method: str, key: str, body: bytes = b"", headers: dict | None = None) -> int:
    """One unsigned request to the bucket; its status"""
    req = urllib.request.Request(f"{STORE_URL}/{key}", data=body if method == "PUT" else None, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def keep(who: str, body: bytes, ctype: str) -> JSONResponse:
    """The row first, then the bytes, then the row marked stored: no
    object is ever in the bucket without its row"""
    sha = hashlib.sha256(body)
    r = run("SELECT * FROM py_api_object_add(%s, %s, %s, %s)", (who, sha.hexdigest(), len(body), ctype))
    if isinstance(r, JSONResponse):
        return r
    key, stored = r[0]["key"], r[0]["stored"]
    if not stored:
        status = store("PUT", key, body, {
            "Content-Type": ctype,
            # S3 checks the body against it, and refuses a mismatch
            "x-amz-checksum-sha256": base64.b64encode(sha.digest()).decode(),
            # The key changes with the content: cache it for good
            "Cache-Control": "public, max-age=31536000, immutable",
        })
        if status != 200:
            return answer({"error": f"the bucket answered {status}"}, 502)
        run("SELECT py_api_object_stored(%s, %s)", (who, key))
    return answer({"key": key, "url": f"{STATIC_URL}/{key}", "size": len(body), "type": ctype}, 201)


@app.post("/objects/new")
async def object_new(request: Request):
    body = await request.body()
    if len(body) > MAX_BODY:
        return answer({"error": "body too large"}, 413)
    if not body:
        return answer({"error": "no body: send the file's bytes"}, 400)
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype not in TYPES:
        return answer({"error": f"type {ctype or 'none'}: one of {sorted(TYPES)}"}, 415)
    who = await run_in_threadpool(caller, request.headers.get("authorization"))
    if who is None:
        return signed_out()
    return await run_in_threadpool(keep, who["sub"], body, ctype)


@app.get("/objects/mine")
def objects_mine(authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM py_api_objects_mine(%s)", (who["sub"],))
    if isinstance(r, JSONResponse):
        return r
    return answer([{**o, "url": f"{STATIC_URL}/{o['key']}"} for o in r])


class Objects(BaseModel):
    keys: list[str] = Field(max_length=20)


@app.put("/notes/{id}/objects")
def note_objects(id: int, objects: Objects, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT py_api_note_objects_set(%s, %s, %s)", (who["sub"], id, objects.keys))
    return r if isinstance(r, JSONResponse) else answer({"id": id, "keys": objects.keys})


# The collector: every COLLECT_EVERY seconds, the objects no note has
# referred to for COLLECT_GRACE, deleted from the bucket, then
# forgotten, all in one transaction, which holds them against any note
# meanwhile. A delete the bucket refuses is kept for the next round
COLLECT_EVERY = int(os.environ.get("COLLECT_EVERY", "3600"))
COLLECT_GRACE = os.environ.get("COLLECT_GRACE", "6 hours")
log = logging.getLogger("uvicorn.error")


def collect() -> int:
    with pool.connection(timeout=5) as conn, conn.transaction():
        keys = [r["k"] for r in conn.execute(
            "SELECT k FROM py_api_objects_to_collect(%s::interval, 50) AS k", (COLLECT_GRACE,)).fetchall()]
        gone = [k for k in keys if store("DELETE", k) in (200, 204)]
        if gone:
            conn.execute("SELECT py_api_objects_forget(%s)", (gone,))
        return len(gone)


def collector():
    while True:
        time.sleep(COLLECT_EVERY)
        if not STORE_URL:
            continue
        try:
            n = collect()
            if n:
                log.info("collector: %d objects deleted", n)
        except Exception:
            log.exception("collector")
```

- **`store`:** one unsigned request to the bucket, its
  status. On the box, S3's; here, the mock's
- **`keep`, in order:** the row, by the accessor, which
  makes the key and refuses without `objects.write`;
  the bytes, only if the bucket does not hold them yet,
  with the checksum S3 checks and a `Cache-Control`
  that never expires; then the row marked stored. A
  failure between leaves a row unstored, which the
  collector clears after the grace
- **`object_new`:** `async`, to read the body; the
  rest, which blocks, in the thread pool. The size and
  type checked before the token, so a refusal costs
  nothing
- **The collector:** a thread, every `COLLECT_EVERY`
  seconds. Its round is one transaction: the objects to
  collect, locked; each deleted from the bucket; those
  the bucket confirmed, forgotten. A delete the bucket
  refuses stays for the next round. Its failures are
  logged, and it goes on

**Document the routes.** In `docs/py-api/api.md`, after
the starter's three in §2, the entries from [the
contract](2-contract.md) §2, in the page's own form:

``` markdown
POST /objects/new
: `objects.write`. The body is the file, its type in
  `Content-Type`: PNG, JPEG, GIF, WebP, PDF or plain
  text, 1 MiB at most. `201` and
  `{key, url, size, type}`; the same bytes again, the
  same key. `400` for no body; `403` without it; `413`
  over 1 MiB; `415` for another type; `502` if the
  bucket refuses

GET /objects/mine
: Signed in. `200` and a list of the caller's
  `{key, size, type, created_at, refs, url}`, newest
  first, 500 at most

PUT /notes/{id}/objects
: `notes.write`, and the note your own. `{keys}`, the
  note's whole list, 20 at most. `200` and
  `{id, keys}`. `403`; `404` for no such note, or an
  object not yours or not stored; `422` for more than
  20
```

And in the entry for `GET /notes`, at its end: "Each
note also has `objects`, a list of `{key, type}`".

## 4 Its Tests

Beside tutorial 5's, in `test/test_main.py`. Its
`database` answers for `py_api_notes_all`, which
`GET /notes` no longer calls; make it answer for the
new one, each note with its objects:

``` python
        if sql.startswith("SELECT * FROM py_api_notes_page"):
            return [{"id": 1, "body": "hi", "mine": True, "created_at": None, "updated_at": None, "objects": []}]
```

Then the uploads' own test, after the last:

``` python
    def test_an_upload_of_a_type_not_allowed_is_refused(self):
        for t in ("text/html", "image/svg+xml", ""):
            r = self.client.post("/objects/new", headers={**self.bearer(), "Content-Type": t}, content=b"<p>")
            self.assertEqual(r.status_code, 415, t)
        r = self.client.post("/objects/new", headers={**self.bearer(), "Content-Type": "image/png"}, content=b"")
        self.assertEqual(r.status_code, 400)
```

Expect `OK`:

``` sh
make test
```

## 5 Run It, With a Quick Collector

Six hours is long to watch. In `dev/dev.env`, which git
ignores and both stacks read:

``` sh
printf 'COLLECT_EVERY=5\nCOLLECT_GRACE=4 seconds\n' > dev/dev.env
```

Then restart: `make dev`, or the native stack's `stop`
and `start`. Delete `dev/dev.env` when you are done.

## 6 Upload, Link, Collect

Asha, made a member by you, the first admin ([tutorial
4](../4-users/2-contract.md) §2), and an image of hers.
Any PNG will do; this one is made here:

``` sh
A=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=asha)
python3 -c "import zlib,struct; c=lambda t,d: struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)); open('/tmp/blue.png','wb').write(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',64,48,8,2,0,0,0))+c(b'IDAT',zlib.compress(b''.join(b'\x00'+bytes((40,90,200))*64 for _ in range(48))))+c(b'IEND',b''))"
```

Upload it. Expect `201`, its key and its URL:

``` sh
R=$(curl -s -X POST -H "Authorization: Bearer ${A}" -H 'Content-Type: image/png' --data-binary @/tmp/blue.png http://py-api.${H}/objects/new)
echo "${R}"
```

Read it back from the static host. Expect `200`,
`image/png`, and the same bytes:

``` sh
curl -s -o /tmp/back.png -w '%{http_code} %{content_type}\n' "$(echo "${R}" | jq -r .url)"
cmp /tmp/blue.png /tmp/back.png && echo same
```

A note that refers to it. Expect the key back, then
`"refs":1`:

``` sh
N=$(curl -s -X POST -H "Authorization: Bearer ${A}" -H 'Content-Type: application/json' -d '{"body": "with a picture"}' http://py-api.${H}/notes | jq .id)
curl -s -X PUT -H "Authorization: Bearer ${A}" -H 'Content-Type: application/json' -d "{\"keys\": [$(echo "${R}" | jq .key)]}" http://py-api.${H}/notes/${N}/objects
curl -s -H "Authorization: Bearer ${A}" http://py-api.${H}/objects/mine
```

What is refused. Expect `415` for HTML, and `403`,
`objects.write needed`, for a reader:

``` sh
curl -s -w ' %{http_code}\n' -X POST -H "Authorization: Bearer ${A}" -H 'Content-Type: text/html' --data-binary '<p>hi' http://py-api.${H}/objects/new
Z=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=zed)
curl -s -w ' %{http_code}\n' -X POST -H "Authorization: Bearer ${Z}" -H 'Content-Type: image/png' --data-binary @/tmp/blue.png http://py-api.${H}/objects/new
```

Zed must have come through the door once, by `/me`, to
be refused as a reader; else he is refused as no one,
the same `403`.

Now let go. The note deleted, wait out the quick grace
and a round, and expect `404` from the static host, and
the object gone from `/objects/mine`:

``` sh
curl -s -X DELETE -H "Authorization: Bearer ${A}" http://py-api.${H}/notes/${N}
sleep 12
curl -s -o /dev/null -w '%{http_code}\n' "$(echo "${R}" | jq -r .url)"
curl -s -H "Authorization: Bearer ${A}" http://py-api.${H}/objects/mine
```

## 7 What Reaches the Box

A tag builds py-api and the migrations; the manifest's
new routes are handed over. Before the uploads work on
the box, its owner adds what [the
contract](2-contract.md) §5 lists: the bucket's policy
for `objects/*` and `store.env`. Until then a
`POST /objects/new` answers `502`,
`the bucket answered 403`, and its row is collected
after the grace.

## 8 What Can Go Wrong

- **`502`, `the bucket answered ...`.** The store
  refused or is not there: `STORE_URL`, or, on the box,
  the bucket's policy
- **`413`, an HTML page.** Over 1 MiB: nginx refuses it
  before py-api sees it. py-api's own `413` is the same
  limit, kept for a request that reaches it some other
  way
- **An object is gone that a note showed a moment
  ago.** The grace is too short for how long people
  take to save. Six hours is the default for a reason
- **Nothing is ever collected.** `STORE_URL` is unset,
  and the collector skips its rounds; or its log, at
  `collector`, says why

## 9 See Also

- [The UI](4-the-ui.md): next
