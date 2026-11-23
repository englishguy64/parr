// WebAuthn client for the passkey demo.
//
// The key choice is `authenticatorAttachment`:
//   "platform"       -> the authenticator built into this PC. On Windows that is Windows Hello,
//                       and its private key is created and held in the TPM 2.0 chip.
//   "cross-platform" -> a roaming FIDO2 security key (USB / NFC / BLE).
// The private key never leaves the authenticator. Only the public key is sent to the server.

// The API lives on a different origin (backendapi). Change this if you host it elsewhere.
const API_BASE = 'http://localhost:5080';

const $ = (id) => document.getElementById(id);

const browserSupportsPasskeys =
    typeof navigator.credentials !== 'undefined' &&
    typeof window.PublicKeyCredential !== 'undefined' &&
    typeof PublicKeyCredential.parseCreationOptionsFromJSON === 'function' &&
    typeof PublicKeyCredential.parseRequestOptionsFromJSON === 'function';

const KINDS = {
    tpm: { attachment: 'platform', label: 'Windows Hello (TPM)' },
    fido2: { attachment: 'cross-platform', label: 'Security key (FIDO2)' }
};

function log(message, kind = '') {
    const line = document.createElement('div');
    line.className = kind;
    line.textContent = `${new Date().toLocaleTimeString()}  ${message}`;
    $('log').prepend(line);
}

async function api(url, options = {}) {
    const response = await fetch(API_BASE + url, {
        credentials: 'include',   // send the Identity auth cookie cross-origin
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `${response.status} ${response.statusText}`);
    }
    return response;
}

// ---- Registration: create a passkey for the signed-in user ----
async function createPasskey(kind) {
    const { attachment, label } = KINDS[kind];

    log('1. Asking the server for creation options (challenge, rp.id, user.id)...');
    const optionsJson = await (await api('/api/passkey/creation-options', { method: 'POST' })).json();

    // Choose where the private key will live.
    optionsJson.authenticatorSelection = {
        ...(optionsJson.authenticatorSelection ?? {}),
        authenticatorAttachment: attachment,   // platform = TPM / Windows Hello, cross-platform = FIDO2 key
        residentKey: 'required',               // discoverable passkey: sign in without typing a name
        userVerification: 'required'           // PIN, fingerprint or face is mandatory
    };

    log(`2. navigator.credentials.create() with attachment "${attachment}". Approve the ${label} prompt...`);
    const options = PublicKeyCredential.parseCreationOptionsFromJSON(optionsJson);
    const credential = await navigator.credentials.create({ publicKey: options });

    const response = credential.response;
    const transports = response.getTransports?.() ?? [];
    log(`3. Authenticator replied. attachment=${credential.authenticatorAttachment}, transports=[${transports.join(', ')}]`);

    log('4. Sending the attestation to the server. It stores the PUBLIC key only...');
    await api('/api/passkey/register', {
        method: 'POST',
        body: JSON.stringify({ credentialJson: JSON.stringify(credential), name: label })
    });
    log(`Passkey created: ${label}. The private key stays in the authenticator.`, 'ok');
}

// ---- Authentication: sign in with a passkey ----
async function signIn(username, mediation) {
    log('1. Asking the server for request options (a NEW random challenge)...');
    const query = username ? `?username=${encodeURIComponent(username)}` : '';
    const optionsJson = await (await api(`/api/passkey/request-options${query}`, { method: 'POST' })).json();

    log('2. navigator.credentials.get(). The authenticator signs the challenge...');
    const options = PublicKeyCredential.parseRequestOptionsFromJSON(optionsJson);
    const credential = await navigator.credentials.get({ publicKey: options, mediation });

    log('3. Sending the signature to the server. It verifies it with the stored public key...');
    await api('/api/passkey/login', {
        method: 'POST',
        body: JSON.stringify({ credentialJson: JSON.stringify(credential) })
    });
    log('Signed in with a passkey. No password was used.', 'ok');
}

// ---- UI ----
async function refresh() {
    const me = await (await api('/api/me')).json();
    $('signed-out').hidden = me.signedIn;
    $('signed-in').hidden = !me.signedIn;
    if (!me.signedIn) return;

    $('who').textContent = me.userName;
    const body = $('passkeys');
    body.replaceChildren();
    if (me.passkeys.length === 0) {
        body.innerHTML = '<tr><td colspan="5">No passkeys yet. Add one below.</td></tr>';
    }
    for (const p of me.passkeys) {
        const row = document.createElement('tr');
        const cells = [
            p.name ?? 'Passkey',
            (p.transports ?? []).join(', ') || '-',
            p.signCount,
            new Date(p.createdAt).toLocaleString()
        ];
        for (const value of cells) {
            const td = document.createElement('td');
            td.textContent = value;
            row.appendChild(td);
        }
        const del = document.createElement('button');
        del.textContent = 'Delete';
        del.className = 'secondary';
        del.onclick = () => run(async () => {
            await api(`/api/passkey/${p.credentialId}`, { method: 'DELETE' });
            log('Passkey deleted from the server.', 'ok');
        });
        const td = document.createElement('td');
        td.appendChild(del);
        row.appendChild(td);
        body.appendChild(row);
    }
}

async function run(action) {
    try {
        await action();
    } catch (error) {
        if (error.name === 'NotAllowedError') log('Cancelled, timed out, or no matching passkey was offered.', 'err');
        else if (error.name === 'InvalidStateError') log('This authenticator already has a passkey for this account.', 'err');
        else log(error.message, 'err');
    }
    await refresh();
}

async function registerAccount(kind) {
    const userName = $('username').value.trim();
    if (!userName) { log('Enter a user name first.', 'err'); return; }
    await api('/api/register', { method: 'POST', body: JSON.stringify({ userName }) });
    log(`Account "${userName}" created (no password).`);
    await createPasskey(kind);
}

async function init() {
    if (!browserSupportsPasskeys) {
        $('support').textContent = 'This browser does not support the WebAuthn JSON helpers. Use a current Edge, Chrome, Safari or Firefox.';
        $('support').className = 'err';
        return;
    }
    const hello = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable?.();
    $('support').textContent = hello
        ? 'A platform authenticator is available (on Windows this is Windows Hello, backed by the TPM).'
        : 'No platform authenticator found. Set up Windows Hello (and a TPM) or use a FIDO2 security key.';
    $('support').className = hello ? 'ok' : 'err';

    $('btn-reg-tpm').onclick = () => run(() => registerAccount('tpm'));
    $('btn-reg-fido2').onclick = () => run(() => registerAccount('fido2'));
    $('btn-login').onclick = () => run(() => signIn($('username').value.trim()));
    $('btn-add-tpm').onclick = () => run(() => createPasskey('tpm'));
    $('btn-add-fido2').onclick = () => run(() => createPasskey('fido2'));
    $('btn-logout').onclick = () => run(async () => { await api('/api/logout', { method: 'POST' }); log('Signed out.'); });

    await refresh();
}

init();
