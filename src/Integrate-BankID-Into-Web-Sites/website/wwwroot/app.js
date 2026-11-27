// The simple web site. It never talks to BankID. The browser calls the Backend API, which is the only part that talks to BankID.
//
//   POST {API}/bankid/start            -> { orderRef, mode, autoStartToken }   autoStartToken only on the same device
//   GET  {API}/bankid/qr/{orderRef}    -> { qrData }                           about every second, draws the animated QR code
//   GET  {API}/bankid/status/{orderRef}-> { status, message, sessionToken }    about every 2 seconds
//   GET  {API}/me                      -> the signed in user, with  Authorization: Bearer <sessionToken>
//
// /config.json (from the web site's server) says where the Backend API is, or that this is a fake sign in because the page runs on localhost.
const el = (id) => document.getElementById(id);
const onPhone = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

let config = {};                 // { backendApiUrl } from /config.json
// The order is kept in localStorage so the page can carry on when BankID returns the user in a new tab.
let orderRef = localStorage.getItem('orderRef');
// The session token is the proof of sign in. It is only kept for this tab.
let sessionToken = sessionStorage.getItem('sessionToken');
let statusTimer = null;
let qrTimer = null;

// ---- Test or production mode ----
// Test uses the Test BankID app and the BankID test environment. Production uses the real BankID.
const notes = {
  test: 'Test: the BankID app must be configured for test, with a Test BankID.',
  production: 'Production: the real BankID. Needs the production certificate in Key Vault.',
};

function currentMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function applyMode() {
  const mode = currentMode();
  localStorage.setItem('bankidMode', mode);
  el('mode-picker').classList.toggle('production', mode === 'production');
  el('mode-note').textContent = notes[mode];
}

for (const radio of document.querySelectorAll('input[name="mode"]')) {
  radio.addEventListener('change', applyMode);
}
const savedMode = localStorage.getItem('bankidMode');
if (savedMode) {
  document.querySelector(`input[name="mode"][value="${savedMode}"]`).checked = true;
}
applyMode();

function show(section) {
  for (const id of ['signed-out', 'waiting', 'signed-in']) {
    el(id).hidden = id !== section;
  }
  // The mode can only be changed between sign ins.
  for (const radio of document.querySelectorAll('input[name="mode"]')) {
    radio.disabled = section !== 'signed-out';
  }
}

// Everything goes to the Backend API in Azure. On localhost there is no Backend API: the sign in is fake, answered by this
// web site's own /api, and the page says so.
const apiBase = () => (config.fake ? '/api' : `${config.backendApiUrl}/api`);

async function api(path, options = {}) {
  const headers = { ...(options.headers ?? {}) };
  if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;
  const response = await fetch(`${apiBase()}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = '';
    try {
      detail = (await response.json()).message ?? '';
    } catch {
      // The response had no JSON body.
    }
    throw new Error(detail || `${path} returned ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}

function stopPolling() {
  clearInterval(statusTimer);
  clearInterval(qrTimer);
  statusTimer = qrTimer = null;
  localStorage.removeItem('orderRef');
  orderRef = null;
}

// 1. Ask the backend to start a sign in. "phone" is the same device, "pc" shows a QR code for another device.
async function start(device) {
  let order;
  try {
    order = await api('/bankid/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device, mode: currentMode() }),
    });
  } catch (error) {
    alert(error.message);
    return;
  }
  orderRef = order.orderRef;
  localStorage.setItem('orderRef', orderRef);
  waitForBankId(device === 'pc');
  if (order.autoStartToken) {
    // Same device: open the BankID app. A link with the autoStartToken starts it, and BankID returns the user to this
    // site through the returnUrl the backend sent (the WEBSITE_URL).
    window.location.href = `https://app.bankid.com/?autostarttoken=${order.autoStartToken}`;
  }
}

// 2. Poll the backend about every 2 seconds. The backend calls BankID /collect. Show a new QR code every second.
function waitForBankId(showQr) {
  show('waiting');
  el('qr').innerHTML = '';
  el('message').textContent = 'Waiting for BankID';
  statusTimer = setInterval(checkStatus, 2000);
  if (showQr) {
    refreshQr();
    qrTimer = setInterval(refreshQr, 1000);
  }
}

async function refreshQr() {
  if (!orderRef) return;
  try {
    const { qrData } = await api(`/bankid/qr/${orderRef}`);
    const qr = qrcode(0, 'M');
    qr.addData(qrData);
    qr.make();
    el('qr').innerHTML = qr.createSvgTag({ scalable: true });
  } catch {
    // The order ended. The status check shows why.
  }
}

async function checkStatus() {
  if (!orderRef) return;
  try {
    const result = await api(`/bankid/status/${orderRef}`);
    el('message').textContent = result.message;
    if (result.status === 'complete') {
      stopPolling();
      sessionToken = result.sessionToken;
      sessionStorage.setItem('sessionToken', sessionToken);
      showSignedIn();
    } else if (result.status === 'failed') {
      stopPolling();
      el('qr').innerHTML = '';
      show('signed-out');
      alert(result.message);
    }
  } catch (error) {
    stopPolling();
    show('signed-out');
    alert(error.message);
  }
}

async function showSignedIn() {
  try {
    const me = await api('/me');
    el('name').textContent = me.name;
    el('personal-number').textContent = me.personalNumber;
    el('signed-in-mode').textContent = me.mode === 'production' ? 'Production' : 'Test';
    show('signed-in');
  } catch {
    show('signed-out');
  }
}

el('start-phone').addEventListener('click', () => start('phone'));
el('start-pc').addEventListener('click', () => start('pc'));
el('cancel').addEventListener('click', async () => {
  const cancelled = orderRef;
  stopPolling();
  if (cancelled) await api(`/bankid/cancel/${cancelled}`, { method: 'POST' });
  show('signed-out');
});
el('signout').addEventListener('click', async () => {
  try {
    await api('/signout', { method: 'POST' });
  } finally {
    sessionToken = null;
    sessionStorage.removeItem('sessionToken');
    show('signed-out');
  }
});

// On a phone the main button is "on this device". On a PC the main button is the QR code.
if (onPhone) {
  el('signed-out').prepend(el('start-phone'));
} else {
  el('signed-out').append(el('start-phone'));
  el('signed-out').insertBefore(el('start-pc'), el('start-phone'));
}

// Find the Backend API first. Then, coming back from the BankID app on the same phone, carry on waiting, or show the
// signed in user.
(async function start_() {
  try {
    const response = await fetch('/config.json');
    config = await response.json();
    if (!response.ok) throw new Error(config.message);
  } catch (error) {
    alert(error.message || 'Could not load the page settings. Try reloading the page.');
    return;
  }
  if (config.fake) {
    el('fake-banner').hidden = false;
  }
  if (orderRef) {
    waitForBankId(false);
  } else if (sessionToken) {
    showSignedIn();
  }
})();
