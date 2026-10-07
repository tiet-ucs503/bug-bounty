---
abstract: |
  Who is signed in, and what your project keeps of
  them. The box signs people in; you read their token,
  ask Cognito for their e-mail, and record each person
  whose e-mail is verified, with a profile your project
  defines. What each person may do is tutorial 2's.
date: 2026-10-07
keywords:
- tutorial
- auth
- cognito
- profile
kind: tutorial
sources:
- dev/mock-auth/server.py
- services/py-api/main.py
- Makefile
status: draft
subtitle: Sign-in is the box's; the record is yours
title: "1 Who Is Signed In: Authentication"
version: v0.1.0
---

`[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](README.md) §5.

## 1 Before You Start

- [What you need](README.md) §2, installed and checked
- [The tutorials' conventions](README.md) §3, set in
  your shell
- A local stack, up

## 2 What the Box Sets Up

**The box signs people in; you do not.** It keeps one
Cognito pool, a store of accounts, for every project it
hosts. You never create or configure a pool. What the
pool does is the box owner's to decide, and every
project on the box shares it.

As the box is set up:

- **Google is the only way in.** The pool's own
  accounts exist, but only its owner can make them, for
  the probes. Nobody can sign up
- **Google may be limited to one organisation.** A
  Google sign-in can be set to accept only one
  organisation's accounts. Then every address is that
  organisation's, and Google has verified it. Ask the
  box's owner whether yours is
- **What Cognito keeps from Google:** the e-mail,
  whether it is verified, and Google's own ID for the
  person. Nothing else: not the name, not the picture
- **Your UI's client** signs in by PKCE, and asks for
  the scopes `openid email`. Its tokens last an hour; a
  sign-in lasts eight

What to ask the box's owner for:

- **A client for your UI,** with your site's address,
  and your localhost for development, as its callback
  URLs
- **A name or a picture from Google,** if your project
  needs them. The owner maps them in the pool and adds
  the `profile` scope. Every project on the box then
  receives them, so it is the owner's call

On your laptop, a mock stands in for Cognito. It hands
out tokens of the same shape, for any name you give it.

## 3 Two Questions, Two Places

A person using your project raises two questions:

- **Authentication: who is this?** This page. The token
  answers, and Cognito gives the e-mail
- **Authorisation: what may they do?** [Tutorial
  2](2-authorisation/README.md). The roles they hold
  answer

Signing in goes like this:

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
sequenceDiagram
  participant B as Browser
  participant C as Cognito
  participant U as Your service, /users
  participant D as Database
  B->>C: sign in, PKCE
  C-->>B: access token: sub, client_id
  B->>U: GET /users/me, Bearer token
  U->>U: check the token
  U->>C: userInfo, Bearer token
  C-->>U: email, email_verified
  U->>D: users_person_see(sub, email, verified, provider)
  D-->>U: recorded, or not
  U-->>B: who you are, or 403
```

The browser signs in by PKCE, a way for a page that can
keep no secret to prove that the token it collects is
the one it asked for. The UI does this; your service
only sees the token.

Your service checks the token: Cognito's signature, who
issued it, that it is an access token, and that it was
issued to your UI or to the box's probes. A token
issued to another project's UI is refused.

The token names the person by `sub`, short for subject:
an ID Cognito gives each account, which never changes.
An e-mail can change; `sub` cannot, so your database
keys people by `sub`.

`/users/me` is where a signed-in person is first seen.
Tutorial 4 builds it, in Python or in JavaScript. This
page builds what it calls: the records, in the
database.

## 4 Read a Token

A token is a JWT: three parts, joined by dots. The
first says how it is signed; the second holds its
claims, the facts it states; the third is the
signature.

Ask the mock for a token for asha:

``` sh
A=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=asha)
```

Decode its middle part. It is base64url: base64 with
`-` and `_` in place of `+` and `/`, so the command
swaps them back before decoding. Expect
`"token_use": "access"`, a `client_id`,
`"sub": "asha"`, a `username`, and **no e-mail**:

``` sh
echo "${A}" | jq -R 'split(".")[1] | gsub("-"; "+") | gsub("_"; "/") | @base64d | fromjson'
```

**An access token carries no e-mail.** Cognito leaves
it out, and the mock does too. Cognito's other token,
the ID token, has the e-mail, but the ID token is for
the browser to read. A service accepts access tokens
only.

**The `username` names the way in.** On the box,
someone who signed in by Google has a `username` like
`Google_<number>`: the part before `_` is the provider.
One of the pool's own accounts has no prefix. The
mock's `username` is the `sub` you gave it.

## 5 Ask for the E-mail

Cognito's `userInfo` endpoint gives the e-mail. Send it
a person's access token, and it answers with that
person's e-mail and whether it is verified. Expect
asha's address and `"email_verified": "true"`:

``` sh
curl -s -H "Authorization: Bearer ${A}" "${MOCK_URL}/oauth2/userInfo" | jq .
```

> [!WARNING]
> `email_verified` is a string, `"true"` or `"false"`,
> not a boolean. Compare it with `"true"`. Tested for
> truth, `"false"` is a non-empty string, and so true
> in Python and JavaScript alike.

Now a person whose address is not verified. Expect
`"email_verified": "false"`:

``` sh
E=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=esha VERIFIED=false)
curl -s -H "Authorization: Bearer ${E}" "${MOCK_URL}/oauth2/userInfo" | jq .email_verified
```

Cognito limits how often `userInfo` may be called. So
your service asks once for each person, and keeps the
answer for ten minutes.

## 6 Record the People

Write the tables and the functions as a draft: SQL you
run by hand until tutorial 3 turns it into a migration.
Save it as `users-draft.sql` at the root of your fork.
Keep it out of `migrations/sql/`: `make check` holds
every file there to a migration's naming rules, and a
draft would fail them.

Every name in the draft starts `users_`. That is the
prefix of the `users` unit, the part of the project
that will own these tables; each unit keeps its names
under its own prefix ([Naming](../conduct/naming.md)).

Two tables, because the data has two owners:

- **`users_people`: what the sign-in says.** `sub`, the
  e-mail and the provider, as Cognito gave them.
  Cognito is their source, so each sign-in writes them
  afresh
- **`users_profiles`: what your project keeps.** Its
  columns are yours to choose, from your project's
  requirements. A display name and an affiliation here,
  for the example. The person fills them in; a sign-in
  never touches them

``` sql
-- The people who have signed in, one row each, by Cognito's sub: what
-- the sign-in says of them. Rewritten at every sign-in, since Cognito
-- is its source of truth
CREATE TABLE IF NOT EXISTS users_people (
  sub text PRIMARY KEY,
  email text NOT NULL CHECK (email = lower(email)),
  provider text NOT NULL,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  seen_at timestamptz NOT NULL DEFAULT now()
);

-- What the project keeps of each person beyond the sign-in. Its columns
-- are the project's to choose; a sign-in never writes them
CREATE TABLE IF NOT EXISTS users_profiles (
  sub text PRIMARY KEY REFERENCES users_people (sub) ON DELETE CASCADE,
  display_name text NOT NULL DEFAULT '' CHECK (length(display_name) <= 80),
  affiliation text NOT NULL DEFAULT '' CHECK (length(affiliation) <= 120),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- At every sign-in: a person whose e-mail is verified is recorded, or
-- their record brought up to date, and given an empty profile the first
-- time. True if recorded; anyone else is not kept
CREATE OR REPLACE FUNCTION users_person_see(p_sub text, p_email text, p_verified boolean, p_provider text)
  RETURNS boolean LANGUAGE plpgsql AS $$
BEGIN
  IF NOT coalesce(p_verified, false) OR coalesce(p_email, '') = '' THEN
    RETURN false;
  END IF;
  INSERT INTO users_people (sub, email, provider) VALUES (p_sub, lower(p_email), p_provider)
    ON CONFLICT (sub) DO UPDATE SET email = EXCLUDED.email, provider = EXCLUDED.provider, seen_at = now();
  INSERT INTO users_profiles (sub) VALUES (p_sub) ON CONFLICT DO NOTHING;
  RETURN true;
END
$$;

-- A person's record and profile together; no row if never recorded
CREATE OR REPLACE FUNCTION users_profile_get(p_sub text)
  RETURNS TABLE (sub text, email text, provider text, display_name text, affiliation text)
  LANGUAGE sql STABLE AS $$
  SELECT p.sub, p.email, p.provider, f.display_name, f.affiliation
  FROM users_people p JOIN users_profiles f ON f.sub = p.sub WHERE p.sub = p_sub
$$;

-- A person's own profile, changed. The service passes the caller's own
-- sub; who may change another's is tutorial 2's
CREATE OR REPLACE FUNCTION users_profile_set(p_sub text, p_display_name text, p_affiliation text) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  UPDATE users_profiles SET display_name = p_display_name, affiliation = p_affiliation, updated_at = now()
    WHERE sub = p_sub;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'no such person' USING ERRCODE = 'no_data_found';
  END IF;
END
$$;
```

What each piece does:

- **`users_person_see`,** at every sign-in: records a
  person whose e-mail is verified, brings their record
  up to date, and gives them an empty profile the first
  time. Anyone else is not kept, and the answer is
  `false`
- **`users_profile_get`:** a person's record and
  profile together
- **`users_profile_set`:** changes a profile. Your
  service passes the caller's own `sub`, so each person
  changes their own

> [!NOTE]
> Only verified e-mails are kept. If the box limits
> Google to one organisation, every e-mail is verified,
> and the check costs nothing. It stays, because the
> pool's own accounts, and the box's set-up, may
> change.

To fit the profile to your project, change the columns
of `users_profiles`, and the two functions that read
and write them, together.

## 7 Try It

Run the draft inside a transaction and roll it back, so
the database is left as it was. Save this trial as
`try-1.sql`:

``` sql
-- Three sign-ins: two verified, one not
SELECT users_person_see('asha', 'Asha@Example.org', true, 'Google') AS asha,
       users_person_see('bhanu', 'bhanu@elsewhere.net', true, 'Google') AS bhanu,
       users_person_see('esha', 'esha@example.org', false, 'Google') AS esha;

-- Asha fills in her profile, then signs in again
SELECT users_profile_set('asha', 'Asha', 'Physics');
SELECT users_person_see('asha', 'asha@example.org', true, 'Google');

SELECT * FROM users_profile_get('asha');
SELECT sub, email, provider FROM users_people ORDER BY sub;
```

Then run both. Expect, in order:

- `t`, `t` and `f`: esha's e-mail is not verified
- asha's record and profile: `Asha`, `Physics`. Her
  second sign-in left her profile alone
- two people, asha and bhanu, both by `Google`

``` sh
psql "${MIGRATOR_URL}" -q -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f try-1.sql -c ROLLBACK
```

## 8 What Can Go Wrong

- **`"email_verified": "false"` for everyone on the
  box.** Cognito passes on what Google told it, but
  only if the pool maps that attribute. Ask the box's
  owner whether `email_verified` is mapped
- **`userInfo` answers `401`.** The token is not an
  access token, has expired, or lacks the `openid`
  scope. The UI asks for `openid email`; keep both
- **A profile's change is lost at the next sign-in.**
  It was written to `users_people`, which each sign-in
  rewrites. Keep it in `users_profiles`
- **`no such person` from `users_profile_set`.** The
  person has not been seen: `users_person_see` runs
  first, at their sign-in
- **`relation "users_people" already exists`.**
  Tutorial 3's migration has run in this database. The
  draft is for before it; from then on, change the
  database by migrations

## 9 See Also

- [2 What each may do](2-authorisation/README.md): next
- [How the project meets the
  box](../onboarding/README.md) §3 and §4: what nginx
  checks, and what your service does
- [The glossary](../glossary.md): JWT, claim, `sub`,
  access token, `userInfo`
- [Cognito's userInfo
  endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/userinfo-endpoint.html),
  read 2026-10-06
