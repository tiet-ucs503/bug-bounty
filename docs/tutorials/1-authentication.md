---
abstract: |
  Who is signed in, and who may come in. The box's
  Cognito pool signs people in; your project decides
  who of them it admits, by rules on their verified
  e-mail, and with which role. Read a token, ask
  Cognito's userInfo for the e-mail, choose your rules
  from four common patterns, and try them in the
  database. The default this template takes: anyone in,
  as `deny-all`, and build up from there.
date: 2026-10-06
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

## 1 Before You Start

- [What you need](README.md) §2, installed and checked
- [The tutorials' conventions](README.md) §3, set in
  your shell
- A local stack, up

You need no pool of your own. The box keeps **one
Cognito pool** for every project on it, with a client
for each project's UI; its owner makes yours. People
sign in through it, on the box by Google. You never
create, configure or administer a pool, and you cannot
restrict who signs in to it: the pool is shared by
everyone the box serves.

What you decide is who of them **your project lets
in**. That is this page.

## 2 Two Questions, Two Places

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
  participant U as users
  participant D as Database
  B->>C: sign in, PKCE
  C-->>B: access token: sub, client_id
  B->>U: GET /me, Bearer
  U->>U: the token's signature, issuer, client
  U->>C: userInfo, Bearer
  C-->>U: email, email_verified
  U->>D: users_admit(sub, email, verified)
  D-->>U: in, or not
  U-->>B: who you are and what you may do, or 403
```

- **Authentication: who is this?** The token answers.
  Every starter service already checks it: the pool's
  signature, its issuer, `token_use` of `access`, and
  `client_id` your UI's or the box's probe client's. A
  token from another project's client is refused. `sub`
  names the person, for good
- **Admission: may they come in?** Your rules answer,
  in your database, from their verified e-mail

## 3 Read a Token

Ask the mock for one, as alice:

``` sh
A=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=alice)
```

Its claims are the token's middle part. Expect
`"token_use": "access"`, a `client_id`, `sub` alice,
and **no e-mail**:

``` sh
echo "${A}" | jq -R 'split(".")[1] | gsub("-"; "+") | gsub("_"; "/") | @base64d | fromjson'
```

Cognito's access tokens carry no e-mail, and the
mock's, made in their shape, carry none either. The ID
token has it, but the ID token is for the browser: a
service accepts only access tokens.

## 4 Ask userInfo

Cognito answers a person's e-mail to anyone holding
their access token, at its `userInfo` endpoint. Expect
alice's address and `"email_verified": "true"`:

``` sh
curl -s -H "Authorization: Bearer ${A}" "${MOCK_URL}/oauth2/userInfo" | jq .
```

`email_verified` is a **string**, `"true"` or
`"false"`, as Cognito sends it. Test it as one:
`"false"` is a non-empty string, true to any language
that tests strings for truth.

Now an unverified address. Expect
`"email_verified": "false"`:

``` sh
E=$(make -s dev-token MOCK_URL=${MOCK_URL} SUB=eve VERIFIED=false)
curl -s -H "Authorization: Bearer ${E}" "${MOCK_URL}/oauth2/userInfo" | jq .email_verified
```

The service asks once a person and keeps the answer ten
minutes: Cognito limits how often it may be asked.

## 5 Choose Your Rules

A rule is a position, a pattern and a role. A new
person's verified e-mail is matched against the rules
in order of position, with SQL's `LIKE`; the first
match lets them in with its role. **No match, no
entry.** An unverified e-mail never matches.

Four patterns cover most projects:

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

  **A named list**         `(10, 'ana@example.org', 'member')`,
                           `(11, 'raj@example.net', 'reader')`,
                           ...
  ---------------------------------------------------------------

**Why `deny-all` by default.** A role that grants
nothing makes a person who is in, and may do nothing:
exactly as if they were signed out, but known by name.
Rights are then given, one role at a time, by someone
who may give them, and never taken for granted by the
door. Build up from nothing; never trim down from
everything.

`deny-all` is not a veto. Roles add up: whoever holds
`deny-all` and `member` may do what `member` may. To
shut out someone already in, take their roles away
(tutorial 2).

Try the patterns on some addresses, with no tables at
all. Expect `member` for both example.org addresses,
whatever their case, and `deny-all` for the other two:

``` sh
psql "${MIGRATOR_URL}" -c "WITH rules (position, pattern, role) AS (VALUES (10, '%@example.org', 'member'), (100, '%', 'deny-all'))
SELECT e AS email, (SELECT r.role FROM rules r WHERE lower(e) LIKE r.pattern ORDER BY r.position LIMIT 1) AS role
FROM unnest(ARRAY['alice@example.org', 'Carol@Example.org', 'bob@elsewhere.net', 'mallory@evil-example.org']) AS e"
```

Mind the `@`: `'%example.org'` would let in
`mallory@evil-example.org`. And `_` in `LIKE` matches
any one character; a domain with one in it wants `\_`.

## 6 Write the Rules Down

The draft that tutorial 3 turns into a migration. Save
it as `users-draft.sql` at the root of your fork,
outside `migrations/sql/`, where `make check` would
hold it to a migration's name. Every name in it carries
`users_`, the prefix of the unit that will own it:

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

- **`users_roles`:** the roles. What each may do is
  tutorial 2's
- **`users_admission`:** the rules, lower case, so an
  address in any case matches
- **`users_people`:** everyone admitted, by `sub`,
  which never changes; the e-mail as it was at the door
- **`users_members`:** who holds which role
- **`users_admit`:** the door. Someone already in is
  seen again, and stays in; someone new comes in by the
  first rule that matches, with its role. The rules are
  read once a person, at their first sign-in: a rule
  changed later changes nothing for people already in

## 7 Try It

The draft in a transaction that is rolled back, so the
database is as it was after. Save the trial as
`try-1.sql`:

``` sql
-- One rule more: anyone at example.org comes in as a member
INSERT INTO users_admission (position, pattern, role) VALUES (10, '%@example.org', 'member');

SELECT users_admit('alice', 'Alice@Example.org', true) AS alice,
       users_admit('bob', 'bob@elsewhere.net', true) AS bob,
       users_admit('eve', 'eve@example.org', false) AS eve;

SELECT p.email, m.role FROM users_people p JOIN users_members m USING (sub) ORDER BY p.email;
```

Then expect `t`, `t` and `f`, and two people, alice a
`member` and bob `deny-all`:

``` sh
psql "${MIGRATOR_URL}" -q -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f try-1.sql -c ROLLBACK
```

Eve's address matches, but it is not verified: she
stays out. Bob matches only `%`: he is in, with
nothing.

## 8 What Can Go Wrong

- **`"email_verified": "false"` for everyone on the
  box.** Cognito says what Google told it, if the pool
  maps the attribute. Ask the box's owner whether
  `email_verified` is mapped
- **userInfo answers `401`.** The token is not an
  access token, has expired, or lacks the `openid`
  scope. The UI asks for `openid email`; keep both
- **Everyone is let in.** A `%` rule sits before the
  narrower ones. Rules are read by position, lowest
  first
- **Someone you shut out is still in.** The rules are
  read at a first sign-in alone. Take their roles away
- **`relation "users_roles" already exists`.** Tutorial
  3's migration has run in this database. The draft is
  for before it; from here on, change the database by
  migrations

## 9 See Also

- [2 What each may do](2-authorisation.md): next
- [How the project meets the
  box](../onboarding/README.md) §3: what nginx checks,
  and what your service does
- [Cognito's userInfo
  endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/userinfo-endpoint.html),
  read 2026-10-06
