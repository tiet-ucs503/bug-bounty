---
abstract: |
  Draft contract for the bug-bounty/testing platform's submitter,
  evaluator, and bug-report workflows. The routes and payloads are the
  agreement to review with the UI team before implementation.
date: 2026-10-10
keywords:
- bug-bounty
- api
- fastapi
- submissions
- evaluations
- bugs
kind: reference
sources:
- services/py-api/main.py
- services/py-api/test/test_main.py
- box/project.json
- docs/conduct/database.md
- docs/py-api/api.md
- migrations/schema.sql
status: draft
subtitle: v0.1.0; proposed routes and payloads, not yet frozen
title: Bug-Bounty Platform API Contract
version: v0.1.0
---

## 1. Purpose and Status

This contract defines the HTTP interface for the submitter and evaluator workflows, including versioned submissions, evaluation results, and bug reports. It is intended for review with the UI team before the implementation is written.

**Status: DRAFT — do not treat this as a frozen/released API yet.** The operations and JSON shapes below are proposed contract decisions where the supplied files do not specify behavior. Resolve the decisions in §12 with the lead before calling the contract frozen.

The current repository's `services/py-api/main.py` only implements `GET /health`, `GET /hello`, and `POST /echo`. None of the business endpoints in this document exists in the ZIP yet. The existing routes and the health check must remain working while the feature is added.

## 2. Proposed Service Boundaries

| Service | Owns these API operations |
|---|---|
| `submission-api` | Create/read submissions, list a team's versions, list current submissions for evaluators, switch the current version |
| `evaluation-api` | Evaluation queue, manual evaluations, automatic evaluations |
| `bug-api` | Create and retrieve bug reports |

These are **proposed service names**. They are not present in the current `box/project.json`; the ZIP presently declares `js-api` and `py-api`. If the lead prefers one initial FastAPI deployment, the same paths and JSON contract can be implemented as separate routers in `py-api` first. The UI must use environment configuration for service base URLs rather than hardcoding a deployment hostname.

The project's database conduct requires each service to own database objects under its manifest prefix and not read or write another unit's tables directly. The service split therefore needs an agreed data-ownership/accessor plan; see §12.

## 3. Common HTTP Rules

- **Encoding:** UTF-8 JSON request and response bodies unless an operation says it has no request body.
- **Authentication:** every business route requires `Authorization: Bearer <Cognito access token>`. Use an access token, not an ID token. The current `py-api` validates issuer, signing key, expiry, `token_use=access`, and the UI/probe client ID. Missing or invalid credentials return `401` with `WWW-Authenticate: Bearer`.
- **Authorization:** a signed-in identity is not by itself permission to access another team's submissions. Enforce team ownership and evaluator/admin capabilities in the service. Exact Cognito group/permission names are not defined in the supplied files and must be agreed before freeze (§12).
- **Caching:** private business responses include `Cache-Control: no-store`. The box owns CORS and adds `Vary: Origin`; services should not add their own CORS policy.
- **Body size:** the box currently caps request bodies at 1 MiB; clients should stay below this. The box may respond `413` before FastAPI sees the request.
- **Rate limits:** the box may respond `429` and `Retry-After: 1` for writes.
- **Timestamps:** return RFC 3339 timestamps in UTC, e.g. `2026-10-10T09:15:00.123Z`.
- **IDs:** `id` is a positive integer identifier. Clients must not construct IDs or assume there are no gaps.
- **Validation:** invalid fields return `422`. Unknown IDs or IDs of the wrong resource type return `404`.
- **Error shape for business endpoints:**

  ```json
  {
    "error": "TOO_MANY_CURRENT_SUBMISSIONS",
    "message": "A team may have only one current submission."
  }
  ```

  `error` is a stable machine-readable code; `message` is suitable for display. Validation errors may additionally include `details`. Do not expose SQL, tracebacks, credentials, or raw database messages.

## 4. Resource Shapes

The API deliberately presents typed resources; it does not require the UI to know how fields are packed into the database's JSON `header` and `TEXT body` columns.

### 4.1 Submission

```json
{
  "id": 42,
  "type": "submission",
  "team_id": "TEAM001",
  "team_name": "Team Alpha",
  "group": "CSE-A",
  "project_title": "AI Evaluation Platform",
  "deployment_url": "https://example.com",
  "site_map": ["/", "/login", "/dashboard"],
  "body": "Project description in Markdown or plain text.",
  "version": 4,
  "is_current": true,
  "created_at": "2026-10-10T09:15:00.123Z",
  "updated_at": "2026-10-10T09:15:00.123Z"
}
```

The SQL stores `team_id`, `team_name`, `group`, `project_title`, `deployment_url`, and `site_map` in `header`; `body`, `version`, `is_current`, and timestamps are separate columns. `version` and `is_current` are controlled by the backend, not chosen by the submitter.

### 4.2 Manual evaluation

```json
{
  "id": 71,
  "type": "evaluation",
  "submission_id": 42,
  "team_id": "TEAM001",
  "student_id": "S1187",
  "evaluator_id": "cognito-subject-or-internal-id",
  "grade": "A-",
  "feedback": "Strong architecture; improve edge-case handling.",
  "created_at": "2026-10-10T10:00:00.000Z",
  "updated_at": "2026-10-10T10:00:00.000Z"
}
```

`evaluator_id` is derived from the authenticated caller on the server; clients must not impersonate an evaluator by submitting another ID. The exact mapping between Cognito `sub` and an internal evaluator ID needs agreement. The evaluation is linked to the exact submission version through `submission_id`.

### 4.3 Automatic evaluation

```json
{
  "id": 72,
  "type": "automatic_evaluation",
  "submission_id": 42,
  "evaluator": "schema-validator-v1",
  "checks_passed": 14,
  "checks_failed": 1,
  "summary": "14/15 checks passed; see the failure details.",
  "created_at": "2026-10-10T10:02:00.000Z",
  "updated_at": "2026-10-10T10:02:00.000Z"
}
```

The server runs checks and records their result. The client does not supply trusted check counts or claim that validation passed.

### 4.4 Bug report

```json
{
  "id": 83,
  "team_id": "TEAM001",
  "submission_id": 42,
  "severity": "high",
  "category": "authentication",
  "description": "Login returns HTTP 500 for a password containing '&'.",
  "created_at": "2026-10-10T10:05:00.000Z",
  "updated_at": "2026-10-10T10:05:00.000Z"
}
```

`submission_id` is optional in v0.1 to remain compatible with the supplied bug example, but the UI should provide it whenever a bug concerns a particular submission version. The agreed severity vocabulary is still an open decision; the current SQL only demonstrates `high`.

## 5. Submitter Workflow — `submission-api`

All routes in this section require a valid access token. A submitter may act only for a team they are authorised to represent; evaluator/admin access follows the approved role policy.

### `POST /submissions` — create a new version

**Request** (`application/json`):

```json
{
  "team_id": "TEAM001",
  "team_name": "Team Alpha",
  "group": "CSE-A",
  "project_title": "AI Evaluation Platform",
  "deployment_url": "https://example.com",
  "site_map": ["/", "/login", "/dashboard"],
  "body": "Project description in Markdown or plain text."
}
```

- The client does **not** send `id`, `version`, `is_current`, `created_at`, or `updated_at`.
- The server validates the fields and the caller's permission for `team_id`.
- The server calculates `next version = highest existing version + 1` using a concurrency-safe transaction.
- **Proposed v0.1 rule:** every accepted new submission becomes current. In one transaction, clear the previous current version and insert the new version as current.
- **`201 Created`** returns the created `Submission` resource.
- **`401`** unauthenticated; **`403`** caller cannot submit for that team; **`409`** state/current-version conflict; **`422`** invalid fields; **`413`** body too large; **`429`** write rate limit.
- A retry of this `POST` can create another version. The UI must not blindly retry after a timeout; idempotency support is not implemented in the supplied SQL and is an open decision (§12).

### `GET /submissions/{id}` — read one submission

- Returns **`200`** and the `Submission` resource.
- Returns **`404`** if the ID does not identify a submission.
- The service checks whether the caller may see the submission.

### `GET /teams/{team_id}/submissions` — submission history

- Returns **`200`** with `{ "items": [Submission, ...], "total": 3, "limit": 50, "offset": 0 }`.
- Versions are ordered by `version ASC` (oldest first), consistent with the supplied SQL demonstration query.
- Query parameters: `limit` defaults to `50`, range `1..100`; `offset` defaults to `0`, minimum `0`.
- Returns an empty `items` array if the team has no submissions; `403` if the caller may not view that team.

### `GET /teams/{team_id}/submissions/current` — current submission

- Returns **`200`** and the one `Submission` whose `is_current` is true.
- Returns **`404`** if the team has no current submission.
- “Current” means `is_current = 1`; it is not defined as the highest version number. “Latest” means greatest `version`.

### `GET /submissions` — list current submissions for the evaluator queue

This supporting operation is added because an evaluator queue spans multiple teams; the team-scoped history route alone cannot supply that list.

- Requires evaluator/admin capability.
- `GET /submissions?limit=50&offset=0` returns a paginated list of current submissions across teams. V0.1 does not expose a global historical-submissions listing; use the team-scoped history endpoint for that.

### `PUT /submissions/{id}/current` — select a current version

- No request body.
- Returns **`200`** and the target `Submission` after the transaction commits.
- The server identifies the target's team, clears that team's old current version, then marks the target version current in the **same transaction**.
- The target must exist and have type `submission`; otherwise `404`.
- `409` if a concurrent state change prevents a safe transition; `403` if the caller is not allowed to change the team's current version.
- Repeating the request for the already-current version is successful and leaves the state unchanged.

## 6. Evaluator Workflow — `evaluation-api`

All routes require authentication and evaluator/admin capability. The service must check the right to evaluate the specific submission, not merely that the caller is signed in.

### `GET /evaluations/queue` — pending manual evaluations

- Query parameters: `limit` defaults to `50`, range `1..100`; `offset` defaults to `0`, minimum `0`.
- Returns **`200`** with the same paginated shape as submission history; each item is a `Submission`.
- **Proposed v0.1 queue rule:** include current submissions for which no manual evaluation is recorded against that exact `submission_id`. An automatic evaluation alone does not remove an item from the manual queue.
- This definition depends on each new manual evaluation storing `submission_id` in its JSON header. The supplied sample manual-evaluation row has no `submission_id`, so it cannot reliably mark a particular version as evaluated without updating the seed/data rule.

### `POST /submissions/{id}/evaluations` — record a manual evaluation

**Request**:

```json
{
  "student_id": "S1187",
  "grade": "A-",
  "feedback": "Strong architecture; improve edge-case handling."
}
```

- The path `id` identifies the exact submission version. The server fetches its `team_id` and writes it into the evaluation metadata; clients cannot override the relationship.
- The server obtains `evaluator_id` from the authenticated identity.
- **`201 Created`** returns the `Manual evaluation` resource.
- **`404`** submission not found; **`403`** caller cannot evaluate it; **`409`** if the agreed policy permits only one final manual evaluation and one already exists; **`422`** invalid input.
- **Proposed v0.1 rule:** one final manual evaluation per submission version. If multiple independent evaluators must review one version, that policy and queue semantics need to be revised before freeze.

### `GET /submissions/{id}/evaluations` — retrieve manual results

This supporting read operation is included so the UI can show saved feedback after navigation or refresh.

- Returns **`200`** with `{ "items": [ManualEvaluation, ...], "total": 1 }`.
- Returns an empty list if no manual evaluation is recorded. `404` if the submission does not exist.
- Only authorised submitters for that team and evaluators/admins may read results.

### `POST /submissions/{id}/automatic-evaluations` — run automatic checks

- No client-supplied scores or results; no request body is required in v0.1.
- The service loads the specified submission, runs the configured checks, records an immutable `automatic_evaluation` document, and returns **`201 Created`** with the `Automatic evaluation` resource.
- Re-running creates another result record, so history can be retained. Clients should not automatically retry after an ambiguous timeout until idempotency is defined.
- Returns **`404`** if the submission does not exist; **`403`** if the caller lacks permission; **`503`** if the evaluation engine is temporarily unavailable.

### `GET /submissions/{id}/automatic-evaluations` — retrieve automatic results

- Returns **`200`** with `{ "items": [AutomaticEvaluation, ...], "total": n }`, newest first.
- Returns an empty list if no automatic run exists; `404` if the submission does not exist.

## 7. Bug Reporting Workflow — `bug-api`

### `POST /bugs` — create a bug report

**Request**:

```json
{
  "team_id": "TEAM001",
  "submission_id": 42,
  "severity": "high",
  "category": "authentication",
  "description": "Login returns HTTP 500 for a password containing '&'. Reproduced on staging."
}
```

- `team_id`, `severity`, `category`, and `description` are required. `submission_id` is optional for compatibility with the supplied SQL sample; if supplied, it must identify a submission belonging to `team_id`.
- The server validates caller permissions and stores metadata in the JSON header and description in the body.
- Returns **`201 Created`** with the `Bug report` resource.
- Returns **`403`** if the caller may not report on that team; **`404`** if the referenced submission does not exist or does not belong to the team; **`422`** invalid input.

### `GET /teams/{team_id}/bugs` — list a team's bug reports

- Returns **`200`** with `{ "items": [BugReport, ...], "total": 4, "limit": 50, "offset": 0 }`.
- Query parameters: `limit` defaults to `50`, range `1..100`; `offset` defaults to `0`, minimum `0`.
- Results are ordered newest first. Returns an empty `items` array when no bug reports exist; `403` if the caller may not view that team's reports.
- This endpoint follows the SQL's demonstrated use case for retrieving all bugs for a team; it is added so the UI can populate a report list without already knowing every bug ID.

### `GET /bugs/{id}` — read a bug report

- Returns **`200`** and the bug report resource.
- Returns **`404`** if no bug with that ID exists.
- The service checks whether the caller may view the report/team.

## 8. Error Codes

| HTTP | Stable `error` code | Meaning |
|---:|---|---|
| `400` | `BAD_REQUEST` | Malformed request that is not a field-validation failure |
| `401` | `UNAUTHENTICATED` | Missing, invalid, expired, or wrong-kind token; include `WWW-Authenticate: Bearer` |
| `403` | `FORBIDDEN` | Signed-in caller lacks permission for this action/resource |
| `404` | `NOT_FOUND` | Resource missing or wrong resource type |
| `409` | `TOO_MANY_CURRENT_SUBMISSIONS` or `STATE_CONFLICT` | Current-submission invariant or another state conflict |
| `413` | `BODY_TOO_LARGE` | Request exceeds the box's 1 MiB limit; may originate at the proxy |
| `422` | `VALIDATION_ERROR` | Fields fail request validation |
| `429` | `RATE_LIMITED` | Box rate limit; include `Retry-After: 1` when provided by the box |
| `500` | `INTERNAL_ERROR` | Unexpected server failure; don't include internal details |
| `503` | `DEPENDENCY_UNAVAILABLE` | Database or evaluator dependency temporarily unavailable |

The supplied MySQL SQL signals `MYSQL_ERRNO=30001` and `SQLSTATE=45000` for the current-submission conflict. That database-specific error must map to the **stable HTTP contract code** `TOO_MANY_CURRENT_SUBMISSIONS`. The repository currently targets PostgreSQL, so the implementation cannot rely on MySQL error number `30001` without first resolving the database mismatch.

## 9. Route Allow-List for the Box

The box refuses routes absent from `box/project.json`. Every new business route must be added to the manifest with `signed_in: true`. Keep `GET /health` public for each service. The three proposed services do not currently exist in the manifest; if approved, add their service entries and folders before the UI depends on their hosts.

Proposed route entries (grouped by the proposed owner):

```json
{
  "submission-api": [
    {"method": "GET", "path": "/health", "signed_in": false},
    {"method": "POST", "path": "/submissions", "signed_in": true},
    {"method": "GET", "path": "/submissions", "signed_in": true},
    {"method": "GET", "path": "/submissions/{id}", "signed_in": true},
    {"method": "GET", "path": "/teams/{team_id}/submissions", "signed_in": true},
    {"method": "GET", "path": "/teams/{team_id}/submissions/current", "signed_in": true},
    {"method": "PUT", "path": "/submissions/{id}/current", "signed_in": true}
  ],
  "evaluation-api": [
    {"method": "GET", "path": "/health", "signed_in": false},
    {"method": "GET", "path": "/evaluations/queue", "signed_in": true},
    {"method": "POST", "path": "/submissions/{id}/evaluations", "signed_in": true},
    {"method": "GET", "path": "/submissions/{id}/evaluations", "signed_in": true},
    {"method": "POST", "path": "/submissions/{id}/automatic-evaluations", "signed_in": true},
    {"method": "GET", "path": "/submissions/{id}/automatic-evaluations", "signed_in": true}
  ],
  "bug-api": [
    {"method": "GET", "path": "/health", "signed_in": false},
    {"method": "POST", "path": "/bugs", "signed_in": true},
    {"method": "GET", "path": "/teams/{team_id}/bugs", "signed_in": true},
    {"method": "GET", "path": "/bugs/{id}", "signed_in": true}
  ]
}
```

This is a grouped illustration, not valid `box/project.json` replacement content: copy each route list into the matching service's `routes` array after the proposed service names and architecture are approved. Keep existing `js-api` and `py-api` entries until the lead directs otherwise.

## 10. Data and Consistency Rules

1. Only records with `type = submission` participate in submission versioning/current selection.
2. A team may have many versions and at most one current version. `latest` is greatest `version`; `current` is `is_current = true`.
3. Creating a version and changing `is_current` is atomic. Concurrent submissions for one team must not receive the same version or leave two current versions.
4. Current-submission uniqueness must be guaranteed by the database, not only a `SELECT COUNT(*)` application pre-check.
5. Each new manual evaluation stores `submission_id` and the resolved `team_id`; each automatic evaluation stores `submission_id`.
6. `evaluator_id` is derived from the authenticated identity. Never trust a caller-supplied evaluator identity.
7. Detailed JSON/header validation happens in the API/schema layer before writes.
8. A successful `POST` creates a new record; a `PUT .../current` changes which existing version is current without creating another version.

## 11. What the UI Can Rely On

- Field names and types in §§4–7 are the UI contract; the UI must not depend on SQL column names or trigger implementation details.
- Do not infer the current version from the largest version number; use `is_current` and the current endpoint.
- Treat `error` as the stable machine-readable code; display `message` to people.
- Do not hardcode service hostnames. Obtain base URLs from environment-specific UI configuration.
- The live box has no public FastAPI `/docs`, `/redoc`, or `/openapi.json`; this contract and `bug-bounty-openapi.yaml` are the integration reference.

## 12. Decisions Required Before Freeze

1. **Database dialect (blocking):** the supplied SQL declares MySQL 8.x and uses MySQL triggers/`JSON` operators/`DELIMITER`; this repository uses PostgreSQL with dbmate (`migrations/schema.sql` identifies PostgreSQL 17.11). Decide whether to port the schema and invariant to PostgreSQL or change the project's database target. Do not run the supplied SQL unchanged against this repository.
2. **Service/data ownership (blocking):** the SQL uses one generic `documents` table for all types; repository conduct requires each service to own prefixed database objects and access other units through published functions/APIs. Decide whether to keep one owning service for the generic document store or split storage by service and define cross-service calls/accessors. If the evaluation service calls the submission service to build its queue, define the service-to-service authentication method; the current starter only accepts the UI/probe Cognito clients.
3. **Authorization (blocking for live data):** decide role/group names, team-membership source, whether submitters can switch to historical versions, and who may report/read bugs.
4. **Evaluation queue (blocking for queue implementation):** approve the proposed definition (current submission with no manual evaluation for that exact `submission_id`), and whether exactly one or multiple manual evaluations are allowed per submission.
5. **Manual evaluation identity:** confirm whether SQL `evaluator_id` stores Cognito `sub` or an internal evaluator ID.
6. **Bug association/severity:** decide whether `submission_id` must be required, and freeze the severity vocabulary.
7. **Retry/idempotency:** decide whether submission and automatic-evaluation POSTs need an idempotency key; v0.1 does not promise deduplication on retry.
8. **Service deployment:** confirm the proposed `submission-api`, `evaluation-api`, `bug-api` hosts versus an initial single `py-api` deployment. If split, add the folders, manifest entries, route allow-lists, and migration prefixes required by the repo.

Once these are resolved, update this contract and the OpenAPI document in the same change as the contract tests. Breaking changes after the contract is frozen should be introduced alongside a new version rather than silently changing an existing promise.

## 13. Source Notes

The endpoint payloads use the supplied SQL's document types and sample metadata: submission headers (`team_id`, `team_name`, `group`, `project_title`, `deployment_url`, `site_map`), bug headers (`team_id`, `severity`, `category`), manual evaluation headers (`team_id`, `student_id`, `evaluator_id`), and automatic-evaluation headers (`submission_id`, `evaluator`, `checks_passed`, `checks_failed`). The version/current and conflict requirements follow its backend rules. The service, authentication, manifest, and database-ownership constraints come from the repository in the ZIP. Where the sources do not decide behavior, this contract labels a proposed rule or lists the decision in §12.
