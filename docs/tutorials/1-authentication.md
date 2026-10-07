---
abstract: |
  Signing in and coming in are two steps. The box signs
  people in; your project decides which of them it lets
  in, and with which role. You read a token, ask
  Cognito for the person's e-mail, choose rules that
  match e-mails, and try the rules in the database.
date: 2026-10-07
keywords:
- tutorial
- auth
- cognito
- admission
kind: tutorial
sources:
- dev/mock-auth/server.py
- services/py-api/main.py
- Makefile
status: draft
subtitle: Sign-in is the box's; admission is yours
title: "1 Who Comes In: Authentication"
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

**The box signs people in; you do not.** The box keeps
one Cognito pool, a store of accounts, for every
project it hosts. People sign in to it with Google.
Its owner gives your project's UI a client of its own
in that pool. You never create or configure a pool,
and you cannot limit who signs in to it, because every
project on the box shares it.

**You decide who comes in.** Anyone with a Google
account can sign in. Which of them your project lets
in, and with which role, is yours to decide, and is
this page.

## 2 Two Questions, Two Places

A person coming into your project answers two
questions, in this order:

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
  U->>D: users_admit(sub, email, verified)
  D-->>U: in, or not
  U-->>B: who you are and what you may do, or 403
```

- **Authentication: who is this?** The token answers.
  Cognito signs it, and your service checks it: the
  signature, who issued it, that it is an access token,
  and that it was issued to your UI or to the box's
  probes. A token issued to another project's UI is
  refused
- **Admission: may they come in?** Your rules answer,
  in your database, from the person's verified e-mail

The browser signs in by PKCE, a way for a page that
can keep no secret to prove that the token it collects
is the one it asked for. The UI does this; your service
only sees the token.

The token names the person by `sub`, short for
subject: an ID Cognito gives each account, which never
changes. An e-mail can change; `sub` cannot, so your
database keys people by `sub`, and uses the e-mail only
at the door.

`/users/me` is the door. Tutorials 4 and 5 build it,
in Python and in JavaScript. This page builds what the
door asks: the rules, in the database.

## 3 Read a Token

A token is a JWT: three parts, joined by dots. The
first says how it is signed; the second holds its
claims, the facts it states; the third is the
signature. On the local stack, a mock stands in for
Cognito and hands out tokens of the same shape.

Ask the mock for a token for asha:

``` sh
A=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=asha)
```

Decode its middle part. It is base64url: base64 with
`-` and `_` in place of `+` and `/`, so the command
swaps them back before decoding. Expect
`"token_use": "access"`, a `client_id`,
`"sub": "asha"`, and **no e-mail**:

``` sh
echo "${A}" | jq -R 'split(".")[1] | gsub("-"; "+") | gsub("_"; "/") | @base64d | fromjson'
```

**An access token carries no e-mail.** Cognito leaves
it out, and the mock does too. Cognito's other token,
the ID token, has the e-mail, but the ID token is for
the browser to read. A service accepts access tokens
only.

## 4 Ask for the E-mail

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

## 5 Choose Your Rules

A rule says: an e-mail like this comes in with this
role. For example, `(10, '%@example.org', 'member')`
lets in anyone at example.org as a `member`. Each rule
has three parts:

- **A position,** 10 here. The rules are tried in
  order, lowest first, and the first that matches
  wins
- **A pattern,** matched with SQL's `LIKE`: `%` stands
  for any run of characters, including none, and `_`
  for any single character
- **A role,** given to the person when they come in

**No match, no entry.** An unverified e-mail matches
no rule.

Four sets of rules cover most projects:

  ---------------------------------------------------------------
  You want                 The rules
  ------------------------ --------------------------------------
  **Anyone in, rights      `(100, '%', 'deny-all')`
  later.** The default:    
  everyone comes in with   
  none, and an admin gives 
  roles                    

  **One organisation       `(10, '%@example.org', 'member')`, and
  only**                   no `%` rule

  **One organisation as    `(10, '%@example.org', 'member')`,
  members, everyone else   `(100, '%', 'deny-all')`
  in with none**           

  **A named list**         `(10, 'anu@example.org', 'member')`,
                           `(11, 'raj@example.net', 'reader')`,
                           ...
  ---------------------------------------------------------------

**The default is everyone in, as `deny-all`.**
`deny-all` is a role that may do nothing. A person who
holds only it is in, and known by name, but can do no
more than someone signed out. An admin then gives them
roles, one at a time. Rights are added by someone
allowed to add them, never handed out at the door.
Build up from nothing; never trim down from everything.

**`deny-all` is not a veto.** Roles add up: someone
who holds `deny-all` and `member` may do everything
`member` may. To shut out someone already in, take
their roles away (tutorial 2).

Try the third set on four addresses, without any
tables yet. Expect `member` for the two at example.org,
whatever their case, and `deny-all` for the other two:

``` sh
psql "${MIGRATOR_URL}" -c "WITH rules (position, pattern, role) AS (VALUES (10, '%@example.org', 'member'), (100, '%', 'deny-all'))
SELECT e AS email, (SELECT r.role FROM rules r WHERE lower(e) LIKE r.pattern ORDER BY r.position LIMIT 1) AS role
FROM unnest(ARRAY['asha@example.org', 'Chitra@Example.org', 'bhanu@elsewhere.net', 'manthara@evil-example.org']) AS e"
```

> [!WARNING]
> Mind the `@`. `'%example.org'`, without it, would
> also let in `manthara@evil-example.org`. And since
> `_` matches any character, write it `\_` in a
> pattern that means a real underscore.

## 6 Write the Rules Down

Now write the rules, and the tables that hold them, as
a draft: SQL you run by hand until tutorial 3 turns it
into a migration. Save it as `users-draft.sql` at the
root of your fork. Keep it out of `migrations/sql/`:
`make check` holds every file there to a migration's
naming rules, and a draft would fail them.

Every name in the draft starts `users_`. That is the
prefix of the `users` unit, the part of the project
that will own these tables; each unit keeps its names
under its own prefix ([Naming](../conduct/naming.md)).

``` sql
-- The roles. deny-all grants nothing: whoever holds it alone may do
-- nothing, as if signed out
CREATE TABLE IF NOT EXISTS users_roles (
  role text PRIMARY KEY CHECK (role ~ '^[a-z][a-z0-9-]{1,30}$'),
  about text NOT NULL DEFAULT ''
);

-- Who may come in, and with which role: the first rule, by position,
-- whose pattern the verified e-mail is LIKE. No rule, no entry
CREATE TABLE IF NOT EXISTS users_admission (
  position bigint PRIMARY KEY,
  pattern text NOT NULL CHECK (pattern = lower(pattern)),
  role text NOT NULL REFERENCES users_roles (role)
);

-- The people admitted, by Cognito's sub
CREATE TABLE IF NOT EXISTS users_people (
  sub text PRIMARY KEY,
  email text NOT NULL,
  admitted_at timestamptz NOT NULL DEFAULT now(),
  seen_at timestamptz NOT NULL DEFAULT now()
);

-- Who holds which role
CREATE TABLE IF NOT EXISTS users_members (
  sub text NOT NULL REFERENCES users_people (sub) ON DELETE CASCADE,
  role text NOT NULL REFERENCES users_roles (role) ON DELETE CASCADE,
  PRIMARY KEY (sub, role)
);
CREATE INDEX IF NOT EXISTS users_members_role_idx ON users_members (role);

-- The door. Someone already in is seen again; someone new comes in if
-- their e-mail is verified and a rule matches it, with that rule's
-- role. True if the person is in
CREATE OR REPLACE FUNCTION users_admit(p_sub text, p_email text, p_verified boolean) RETURNS boolean
  LANGUAGE plpgsql AS $$
DECLARE
  v_role text;
BEGIN
  UPDATE users_people SET seen_at = now() WHERE sub = p_sub;
  IF FOUND THEN
    RETURN true;
  END IF;
  IF NOT p_verified OR coalesce(p_email, '') = '' THEN
    RETURN false;
  END IF;
  SELECT a.role INTO v_role FROM users_admission a
    WHERE lower(p_email) LIKE a.pattern ORDER BY a.position LIMIT 1;
  IF v_role IS NULL THEN
    RETURN false;
  END IF;
  INSERT INTO users_people (sub, email) VALUES (p_sub, lower(p_email)) ON CONFLICT (sub) DO NOTHING;
  INSERT INTO users_members (sub, role) VALUES (p_sub, v_role) ON CONFLICT DO NOTHING;
  RETURN true;
END
$$;

-- The roles the project starts with; what each may do is tutorial 2's
INSERT INTO users_roles (role, about) VALUES
  ('deny-all', 'admitted, and may do nothing: where everyone starts'),
  ('reader', 'reads notes'),
  ('member', 'reads and writes notes'),
  ('admin', 'reads the people and the matrix, grants and revokes roles')
ON CONFLICT DO NOTHING;

-- Everyone may come in, and starts as deny-all
INSERT INTO users_admission (position, pattern, role) VALUES
  (100, '%', 'deny-all')
ON CONFLICT DO NOTHING;
```

What each piece does:

- **`users_roles`:** the roles. What each may do is
  tutorial 2's
- **`users_admission`:** the rules, in lower case, so
  an address in any case matches
- **`users_people`:** everyone let in, by `sub`, with
  their e-mail as it was when they came in
- **`users_members`:** who holds which role
- **`users_admit`:** the door. Someone already in is
  marked as seen, and stays in. Someone new comes in by
  the first rule that matches, with its role

> [!NOTE]
> The rules are read only at a person's first sign-in.
> A rule changed later changes nothing for people
> already in; change their roles instead.

## 7 Try It

Run the draft inside a transaction and roll it back,
so the database is left as it was. Save this trial as
`try-1.sql`:

``` sql
-- One rule more: anyone at example.org comes in as a member
INSERT INTO users_admission (position, pattern, role) VALUES (10, '%@example.org', 'member');

SELECT users_admit('asha', 'Asha@Example.org', true) AS asha,
       users_admit('bhanu', 'bhanu@elsewhere.net', true) AS bhanu,
       users_admit('esha', 'esha@example.org', false) AS esha;

SELECT p.email, m.role FROM users_people p JOIN users_members m USING (sub) ORDER BY p.email;
```

Then run both. Expect `t`, `t` and `f`, then two
people: asha a `member`, and bhanu `deny-all`:

``` sh
psql "${MIGRATOR_URL}" -q -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f try-1.sql -c ROLLBACK
```

Esha's address matches a rule, but it is not verified,
so she stays out. Bhanu's matches only `%`, so he is
in, with nothing.

## 8 What Can Go Wrong

- **`"email_verified": "false"` for everyone on the
  box.** Cognito passes on what Google told it, but
  only if the pool maps that attribute. Ask the box's
  owner whether `email_verified` is mapped
- **`userInfo` answers `401`.** The token is not an
  access token, has expired, or lacks the `openid`
  scope. The UI asks for `openid email`; keep both
- **Everyone is let in.** A `%` rule has a lower
  position than the narrower ones. Rules are tried
  lowest first
- **Someone you shut out is still in.** The rules
  apply only at a first sign-in. Take their roles away
- **`relation "users_roles" already exists`.** Tutorial
  3's migration has run in this database. The draft is
  for before it; from then on, change the database by
  migrations

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
