// Page behaviour. The browser does everything: it signs the user in with Entra (MSAL.js), then calls API Management
// directly with the access token. APIM checks the token, runs its policies and calls the Backend API.
//
//   POST {APIM}/chat            -> 202 {"jobId":...} while the agent works, or 200 with the reply if it was quick
//   GET  {APIM}/chat/{jobId}    -> {"status":"running"} | {"status":"done","reply":...} | {"status":"failed","error":...}
//
// /config.json (from the website's server) says where APIM is and which Entra app to sign in to.

const form = document.getElementById("chat-form");
const submit = document.getElementById("submit");
const cancelBtn = document.getElementById("cancel");
const statusEl = document.getElementById("status");
const responseEl = document.getElementById("response");
const loginBtn = document.getElementById("login");
const logoutBtn = document.getElementById("logout");

let config = {};          // { apimBaseUrl, tenantId, clientId } from /config.json
let msalApp = null;       // set when sign-in is configured
let account = null;       // the signed-in user

const apiBase = () => config.apimBaseUrl || "/api";   // no APIM configured: the website's local stand-in
const apiScopes = () => [`api://${config.clientId}/access_as_user`];

function setStatus(text, isError = false) {
    statusEl.textContent = text;
    statusEl.classList.toggle("error", isError);
}

// ---------- sign-in ----------
// A red banner under the header tells the user when signing in did not work.
const noticeEl = document.getElementById("notice");
function showNotice(text) {
    document.getElementById("notice-text").textContent = text;
    noticeEl.hidden = false;
}
document.getElementById("notice-close").addEventListener("click", () => { noticeEl.hidden = true; });

// Turns an MSAL/Entra error into a sentence the user can act on.
function signInMessage(e) {
    const detail = e?.errorMessage || e?.message || String(e);
    if (/AADSTS65001|consent_required/i.test(detail)) return "Sign-in failed: this app needs permission first. Ask an administrator to grant consent.";
    if (/AADSTS50011|redirect_uri/i.test(detail)) return "Sign-in failed: this web address is not registered for sign-in. Ask an administrator to add it to the app registration.";
    if (/AADSTS50105|AADSTS50020|AADSTS700016/i.test(detail)) return "Sign-in failed: your account is not allowed to use this app.";
    if (/user_cancelled|access_denied/i.test(detail)) return "Sign-in was cancelled.";
    return `Sign-in failed: ${detail}`;
}

// Login and Logout always bring the user back to the home page.
async function startSignIn() {
    try {
        config = await (await fetch("/config.json")).json();
    } catch (e) {
        showNotice("Could not load the page settings, so sign-in is unavailable. Try reloading the page.");
        return;
    }
    if (!config.clientId || !config.tenantId) {
        loginBtn.hidden = true;      // sign-in is not set up (for example a local run): nothing to show
        return;
    }
    if (typeof msal === "undefined") {
        showNotice("The sign-in library could not be loaded, so you cannot log in. Check your connection and reload the page.");
        return;
    }

    msalApp = new msal.PublicClientApplication({
        auth: {
            clientId: config.clientId,
            authority: `https://login.microsoftonline.com/${config.tenantId}`,
            redirectUri: `${location.origin}/`,
            postLogoutRedirectUri: `${location.origin}/`,
        },
        cache: { cacheLocation: "sessionStorage" },
    });
    // Back from the Entra login page: finish the sign-in. A failure (for example consent not granted) is shown, not hidden.
    let result = null;
    try {
        await msalApp.initialize();
        result = await msalApp.handleRedirectPromise();
    } catch (e) {
        console.error("Sign-in failed", e);
        showNotice(signInMessage(e));
    }
    account = result?.account ?? msalApp.getAllAccounts()[0] ?? null;
    if (account) msalApp.setActiveAccount(account);
    showUser();
}

// Signed in: the user icon and name replace the Login button. Signed out: the original Login button.
function showUser() {
    document.getElementById("user").textContent = account ? (account.name || account.username) : "";
    document.getElementById("user-box").hidden = !account;
    loginBtn.hidden = !!account;
    logoutBtn.hidden = !account;
}

loginBtn.addEventListener("click", async () => {
    if (!msalApp) { showNotice("Sign-in is not available right now. Reload the page and try again."); return; }
    noticeEl.hidden = true;
    try {
        await msalApp.loginRedirect({ scopes: apiScopes() });
    } catch (e) {
        console.error("Login could not start", e);
        showNotice(signInMessage(e));
    }
});
logoutBtn.addEventListener("click", async () => {
    try {
        await msalApp?.logoutRedirect({ account, postLogoutRedirectUri: `${location.origin}/` });
    } catch (e) {
        console.error("Logout failed", e);
        showNotice(`Logout failed: ${e.errorMessage || e.message}`);
    }
});

// The access token for APIM. Needs a signed-in user; renews silently, and sends the user to Entra if it must.
async function getToken() {
    if (!msalApp || !config.apimBaseUrl) return null;   // sign-in off, or the local stand-in: no token needed
    if (!account) throw new Error("Sign in first.");
    try {
        return (await msalApp.acquireTokenSilent({ scopes: apiScopes(), account })).accessToken;
    } catch (e) {
        if (e instanceof msal.InteractionRequiredAuthError) {
            await msalApp.acquireTokenRedirect({ scopes: apiScopes(), account });
            return null;   // the page is leaving for the Entra login page
        }
        throw e;
    }
}

async function callApi(path, options = {}) {
    const token = await getToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    return fetch(`${apiBase()}${path}`, { ...options, headers });
}

// ---------- results ----------
// The Backend API answers { reply }, { error } or { status, reply, error }: show whichever is there.
function readableReply(text) {
    try {
        const data = JSON.parse(text);
        if (data.reply) return data.reply;
        if (data.error) return `Error: ${data.error}`;
        const out = data.output?.[0]?.content?.[0]?.text;
        if (out) return out;
        return JSON.stringify(data, null, 2);
    } catch (e) {
        return text;
    }
}

// ---------- long-running requests ----------
// The wait happens here in the browser, so no request is held open while the agent works.
const JOB_KEY = "chat-job";                 // survives a page refresh: the job keeps running on the server
const MAX_WAIT_MS = 10 * 60 * 1000;         // stop waiting after 10 minutes (the job may still finish)
const MAX_POLL_FAILURES = 5;                // network blips are retried; this many in a row ends the wait

let polling = null;                         // { cancelled } for the wait in progress

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const nextDelay = (attempt) => Math.min(1000 + attempt * 500, 5000);   // 1s, 1.5s, ... then 5s

function rememberJob(jobId) {
    try { sessionStorage.setItem(JOB_KEY, jobId); } catch (e) { /* storage unavailable: no resume after refresh */ }
}
function forgetJob() {
    try { sessionStorage.removeItem(JOB_KEY); } catch (e) { /* ignore */ }
}

function finish(text, isError) {
    responseEl.textContent = text;
    setStatus(isError ? "Failed." : "Done.", isError);
    submit.disabled = false;
    cancelBtn.hidden = true;
    polling = null;
    forgetJob();
}

async function waitForJob(jobId) {
    const state = { cancelled: false };
    polling = state;
    submit.disabled = true;
    cancelBtn.hidden = false;

    const started = Date.now();
    let failures = 0;
    for (let attempt = 0; ; attempt++) {
        const seconds = Math.round((Date.now() - started) / 1000);
        setStatus(`Working... ${seconds}s`);
        await sleep(nextDelay(attempt));
        if (state.cancelled) return;

        if (Date.now() - started > MAX_WAIT_MS) {
            finish(`Still running after ${Math.round(MAX_WAIT_MS / 60000)} minutes. Job id: ${jobId}`, true);
            return;
        }

        let res, text;
        try {
            res = await callApi(`/chat/${encodeURIComponent(jobId)}`);
            text = await res.text();
        } catch (e) {
            if (++failures >= MAX_POLL_FAILURES) { finish("Lost contact with the service.", true); return; }
            continue;
        }
        if (state.cancelled) return;

        if (res.status === 401) { finish("Your sign-in has expired. Login again.", true); return; }
        if (res.status === 404) { finish("The job was not found. It may have expired.", true); return; }
        if (!res.ok) {
            if (++failures >= MAX_POLL_FAILURES) { finish(readableReply(text), true); return; }
            continue;
        }
        failures = 0;

        let data;
        try { data = JSON.parse(text); } catch (e) { finish(text, true); return; }
        if (data.status === "done") { finish(readableReply(text), false); return; }
        if (data.status === "failed") { finish(`Error: ${data.error ?? "the agent run failed."}`, true); return; }
        // "running": ask again
    }
}

cancelBtn.addEventListener("click", () => {
    if (polling) polling.cancelled = true;
    polling = null;
    forgetJob();
    cancelBtn.hidden = true;
    submit.disabled = false;
    setStatus("Stopped waiting. The agent may still finish in the background.");
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.getElementById("message").value.trim();
    if (!message) {
        setStatus("Enter a message.", true);
        return;
    }
    if (msalApp && config.apimBaseUrl && !account) {
        setStatus("Login first.", true);
        return;
    }

    submit.disabled = true;
    setStatus("Sending...");
    responseEl.textContent = "";
    try {
        const res = await callApi("/chat", { method: "POST", body: new FormData(form) });
        const text = await res.text();

        if (res.status === 202) {
            const { jobId } = JSON.parse(text);
            rememberJob(jobId);
            await waitForJob(jobId);
            return;
        }
        if (res.status === 401) { finish("Login to use the agents.", true); return; }

        // 200: the answer was ready at once. Anything else is an error.
        let failed = !res.ok;
        try { failed = failed || JSON.parse(text).status === "failed"; } catch (e) { /* not JSON */ }
        finish(readableReply(text), failed);
    } catch (e) {
        finish(e.message === "Sign in first." ? "Login first." : "Could not reach the service.", true);
    }
});

// ---------- start ----------
(async () => {
    await startSignIn();
    // After a refresh, pick up a job that was still running.
    let pendingJob = null;
    try { pendingJob = sessionStorage.getItem(JOB_KEY); } catch (e) { /* ignore */ }
    if (pendingJob && (account || !config.clientId)) waitForJob(pendingJob);
})();
