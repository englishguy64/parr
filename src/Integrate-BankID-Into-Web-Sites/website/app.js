// The simple web site. It never talks to BankID. It only talks to the C# backend API on the same address.
const el = (id) => document.getElementById(id);
const onPhone = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

let orderRef = sessionStorage.getItem('orderRef');
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

async function api(path, options) {
  const response = await fetch(path, options);
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
  sessionStorage.removeItem('orderRef');
  orderRef = null;
}

// 1. Ask the backend to start a sign in. "phone" is the same device, "pc" shows a QR code for another device.
async function start(device) {
  let order;
  try {
    order = await api('/api/bankid/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device, mode: currentMode() }),
    });
  } catch (error) {
    alert(error.message);
    return;
  }
  orderRef = order.orderRef;
  sessionStorage.setItem('orderRef', orderRef);
  waitForBankId(device === 'pc');
  if (order.launchUrl) {
    // Same device: open the BankID app. A link with the autoStartToken starts it.
    window.location.href = order.launchUrl;
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
    const { qrData } = await api(`/api/bankid/qr/${orderRef}`);
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
    const result = await api(`/api/bankid/status/${orderRef}`);
    el('message').textContent = result.message;
    if (result.status === 'complete') {
      stopPolling();
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
    const me = await api('/api/me');
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
  if (cancelled) await api(`/api/bankid/cancel/${cancelled}`, { method: 'POST' });
  show('signed-out');
});
el('signout').addEventListener('click', async () => {
  await api('/api/signout', { method: 'POST' });
  show('signed-out');
});

// On a phone the main button is "on this device". On a PC the main button is the QR code.
if (onPhone) {
  el('signed-out').prepend(el('start-phone'));
} else {
  el('signed-out').append(el('start-phone'));
  el('signed-out').insertBefore(el('start-pc'), el('start-phone'));
}

// Coming back from the BankID app on the same phone: carry on waiting, or show the signed in user.
if (orderRef) {
  waitForBankId(false);
} else {
  showSignedIn();
}
