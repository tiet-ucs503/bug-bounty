// The UI's starter: sign in through the box's Cognito by the
// authorisation code with PKCE, then call your services with the access
// token as a Bearer. No build step and no package: ui/ is what is
// released, synced to your www bucket (docs/how-the-box-works.md §5).
//
// What the box asks of a UI (docs/how-the-box-works.md §4):
//   - call the APIs at https://<service>.<zone>, never the box itself;
//   - send the access token, not the ID token, as Authorization: Bearer;
//   - expect 429 with Retry-After on writes, and wait and retry;
//   - expect 401 when the token has lapsed, and sign in again.

const out = document.getElementById("out");
const show = (x) => (out.textContent = typeof x === "string" ? x : JSON.stringify(x, null, 2));

let config;
try {
  config = (await import("./config.js")).default;
} catch {
  show("No ui/config.js: copy ui/config.example.js and fill it in.");
  throw new Error("no config.js");
}

// The callback is the page's own root, on www or a developer's
// localhost: both are the client's callbacks, from box/project.json
const redirectUri = `${location.origin}/`;
const store = sessionStorage;

const b64url = (bytes) =>
  btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const random = (n) => b64url(crypto.getRandomValues(new Uint8Array(n)));

async function signIn() {
  const verifier = random(48);
  const state = random(16);
  store.setItem("pkce_verifier", verifier);
  store.setItem("pkce_state", state);
  const challenge = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const q = new URLSearchParams({
    response_type: "code",
    client_id: config.clientId,
    redirect_uri: redirectUri,
    scope: "openid email",
    code_challenge_method: "S256",
    code_challenge: challenge,
    state,
  });
  location.assign(`https://${config.authDomain}/oauth2/authorize?${q}`);
}

function signOut() {
  store.clear();
  const q = new URLSearchParams({ client_id: config.clientId, logout_uri: redirectUri });
  location.assign(`https://${config.authDomain}/logout?${q}`);
}

// Back from the sign-in: the code for tokens, the state checked, the
// URL cleaned so a reload does not replay it
async function callback() {
  const q = new URLSearchParams(location.search);
  if (!q.has("code")) return;
  history.replaceState(null, "", location.pathname);
  if (q.get("state") !== store.getItem("pkce_state")) return show("Sign-in refused: the state does not match.");
  const r = await fetch(`https://${config.authDomain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: config.clientId,
      code: q.get("code"),
      redirect_uri: redirectUri,
      code_verifier: store.getItem("pkce_verifier") ?? "",
    }),
  });
  store.removeItem("pkce_verifier");
  store.removeItem("pkce_state");
  if (!r.ok) return show(`Sign-in failed: ${r.status} ${await r.text()}`);
  const t = await r.json();
  store.setItem("access_token", t.access_token);
  store.setItem("id_token", t.id_token);
}

const claims = (jwt) => {
  try {
    return JSON.parse(atob(jwt.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// A call to one of your services. A 429 waits for its Retry-After, a
// 502 or 503 or a lost connection backs off; three tries, then the
// answer as it stands. A 401 drops the token: sign in again
export async function api(service, path, { method = "GET", body } = {}) {
  const token = store.getItem("access_token");
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  for (let attempt = 1; ; attempt++) {
    let r;
    try {
      r = await fetch(`https://${service}.${config.zone}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (e) {
      if (attempt >= 3) throw e;
      await sleep(500 * 2 ** attempt);
      continue;
    }
    if (r.status === 429 && attempt < 3) {
      await sleep((Number(r.headers.get("Retry-After")) || 1) * 1000 + Math.random() * 500);
      continue;
    }
    if ((r.status === 502 || r.status === 503) && attempt < 3) {
      await sleep(500 * 2 ** attempt);
      continue;
    }
    if (r.status === 401) {
      store.removeItem("access_token");
      render();
    }
    const text = await r.text();
    let data = text;
    try {
      data = JSON.parse(text);
    } catch {}
    return { status: r.status, data };
  }
}

function render() {
  const id = claims(store.getItem("id_token") ?? "");
  const signedIn = Boolean(store.getItem("access_token"));
  document.getElementById("who").textContent = signedIn ? `Signed in as ${id?.email ?? id?.sub ?? "someone"}` : "Not signed in";
  document.getElementById("sign-in").hidden = signedIn;
  document.getElementById("sign-out").hidden = !signedIn;
}

function buttons() {
  const row = document.getElementById("calls");
  for (const s of config.apis) {
    for (const [label, path, opts] of [
      ["hello", "/hello", {}],
      ["echo", "/echo", { method: "POST", body: { from: "the UI", at: new Date().toISOString() } }],
    ]) {
      const b = document.createElement("button");
      b.textContent = `${s} ${label}`;
      b.onclick = async () => {
        show("…");
        try {
          show(await api(s, path, opts));
        } catch (e) {
          show(`${s}: ${e}`);
        }
      };
      row.append(b);
    }
  }
}

document.getElementById("sign-in").onclick = signIn;
document.getElementById("sign-out").onclick = signOut;
await callback();
render();
buttons();
