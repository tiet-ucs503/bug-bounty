# Big Bounty — Anonymous Peer Testing Contract

## Frontmatter
| Field | Specification |
| :--- | :--- |
| **title** | Big Bounty — Anonymous Peer Testing Contract |
| **subtitle** | API and UI layout contract for the Big Bounty anonymous testing platform |
| **date** | 2026-10-08 |
| **version** | v0.1.0 |
| **status** | draft |
| **kind** | contract |
| **sources** | `box/project.json` |
| **abstract** | Defines the API routes, data structures, and Svelte single-page interface layout for the Big Bounty anonymous peer testing system within the Example Project architecture. |

---

## 1. Architecture & Service Distribution
In accordance with the Example Project system layout:

* **UI Tier (`www.<zone>`)**: Single-page web application (SPA) hosting the Big Bounty peer testing user interface.
* **API Tier (`js-api.<zone>` / `py-api.<zone>`)**: Endpoints managing authentication, anonymous identity masking, bounty submissions, and peer review logs.
* **Database Tier (`database.<zone>`)**: Shared relational database utilizing prefixed tables (`bb_users`, `bb_bounties`, `bb_reviews`) to isolate service data.

---

## 2. UI & Interface Layout Contract (`www.<zone>`)

The layout directly mirrors the **Big Bounty | Anonymous Peer Testing** design structure:

### 2.1 Header & Authentication Navigation
* **Branding Area**: Displays the platform logo (`B`) and main title **Big Bounty — Anonymous Peer Testing Platform**.
* **Auth Switcher**: Unauthenticated state presents sign-in credentials alongside the `"Don't have an account?"` toggle link. Authenticated state replaces this with an anonymous handle selector and session management menu.

### 2.2 Screen Hierarchy & Component Views
1. **Authentication Card View**:
   * Centering layout offering dual modal views for user login and new account registration with handle anonymisation options.
2. **Peer Testing Dashboard View**:
   * **Top Navigation Bar**: Active testing bounties, masked reviewer rating, and reward status.
   * **Bounty Selection Panel**: Searchable list of open testing requests filtered by category and peer review requirements.
   * **Anonymous Testing Workspace**:
     * **Left Pane**: Submission payload and testing parameters (author identity masked).
     * **Center Pane**: Test execution logs, reproduction steps, and validation inputs.
     * **Right Pane**: Anonymous peer review form with verdict controls (`Pass` / `Fail` / `Needs Revision`).

---

## 3. API Contract Specifications (`js-api.<zone>` / `py-api.<zone>`)

### 3.1 Authentication & Anonymous Persona Routes
* **`POST /api/v1/auth/register`**
  * **Auth**: Public.
  * **Request Body**:
    ```json
    {
      "email": "user@example.com",
      "password": "string_hash",
      "anonymous_alias": "PeerTester_402"
    }
    ```
  * **Response (201 Created)**: `{ "user_id": "uuid", "token": "jwt_token" }`
* **`POST /api/v1/auth/login`**
  * **Auth**: Public.
  * **Request Body**: `{ "email": "user@example.com", "password": "string_hash" }`.
  * **Response (200 OK)**: `{ "token": "jwt_token", "anonymous_handle": "PeerTester_402" }`.

### 3.2 Bounty & Anonymous Peer Review Routes
* **`GET /api/v1/bounties`**
  * **Auth**: Bearer Token required (`2-authorisation`).
  * **Response (200 OK)**: Returns list of available peer testing targets with author details strictly anonymised.
* **`POST /api/v1/bounties/{bounty_id}/reviews`**
  * **Auth**: Bearer Token required.
  * **Request Body**:
    ```json
    {
      "verdict": "pass",
      "test_notes": "All assertions verified successfully.",
      "reproduction_steps": ["step_1", "step_2"]
    }
    ```
  * **Response (201 Created)**: `{ "review_id": "uuid", "status": "submitted_anonymously" }`

---

## 4. Workflow Alignment ("The Cycle")
Following Example Project's 5-step development cycle (`1-concept`, `2-contract`, `3-tests`, `4-implementation`, `5-refinement`):
1. **Contract Verification**: This contract establishes the interface and route schemas.
2. **Next Step (`3-tests`)**: Integration tests must be created to validate these API paths and UI component states before backend implementation begins.
