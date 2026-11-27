// The page. It never sees the qrStartSecret: the Backend API builds each QR code and sends only the finished text.
const $ = id => document.getElementById(id);
const isLocal = ['localhost', '127.0.0.1'].includes(location.hostname);
const tokenKey = 'bankid-session-token';
const orderKey = 'bankid-order-ref'; // survives the trip to the BankID app and back on the same device
let backend = '';
let order = null; // { orderRef, qrTimer, statusTimer }

// What to tell the user for each BankID hintCode (see developers.bankid.com, "Collect response").
const hints = {
  outstandingTransaction: 'Start the BankID app.',
  noClient: 'Start the BankID app.',
  started: 'Searching for BankID. It may take a few seconds. If you scanned the QR code, wait for the app.',
  userMrtd: 'Check the document in the BankID app.',
  userCallConfirm: 'Confirm the phone call.',
  userSign: 'Enter your security code in the BankID app and select Identify.',
  expiredTransaction: 'The BankID app did not respond. Try again.',
  certificateErr: 'This BankID cannot be used. Get a new one.',
  userCancel: 'Cancelled.',
  cancelled: 'Cancelled.',
  startFailed: 'The BankID app did not start in time. Try again.',
  ipMismatch: 'The BankID app is on a different network from this browser. Try again, or set BANKID_CHECK_IP to false for the demo.',
  internalError: 'Something went wrong. Try again.'
};

function show(section) {
  for (const id of ['signed-out', 'waiting', 'signed-in']) $(id).hidden = id !== section;
}

function stopPolling() {
  if (order) {
    clearInterval(order.qrTimer);
    clearInterval(order.statusTimer);
  }
  sessionStorage.removeItem(orderKey);
}

function fail(message) {
  stopPolling();
  $('error').textContent = message;
  $('error').hidden = false;
  show('signed-out');
}

async function api(path, options = {}) {
  const token = sessionStorage.getItem(tokenKey);
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: 'Bearer ' + token } : {}) };
  const response = await fetch(backend + path, { ...options, headers });
  if (!response.ok && response.status !== 401 && response.status !== 404) throw new Error(`${response.status} ${(await response.text()).slice(0, 200)}`);
  return response;
}

function drawQr(text) {
  const qr = qrcode(0, 'M');
  qr.addData(text);
  qr.make();
  const canvas = $('qr');
  const ctx = canvas.getContext('2d');
  const count = qr.getModuleCount();
  const cell = Math.floor(canvas.width / count);
  const offset = Math.floor((canvas.width - cell * count) / 2);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#000';
  for (let r = 0; r < count; r++) for (let c = 0; c < count; c++) if (qr.isDark(r, c)) ctx.fillRect(offset + c * cell, offset + r * cell, cell, cell);
}

function pollStatus(orderRef) {
  order = { ...order, orderRef };
  order.statusTimer = setInterval(checkStatus, 2000);
}

async function startSignIn(sameDevice) {
  $('error').hidden = true;
  if (isLocal) return showUser({ name: 'Fake User (localhost)', personalNumber: '199001019999' });
  show('waiting');
  $('qr').hidden = sameDevice;
  $('status').textContent = 'Starting BankID...';
  try {
    const start = await (await api('/api/bankid/start', { method: 'POST', body: JSON.stringify({ sameDevice }) })).json();
    sessionStorage.setItem(orderKey, start.orderRef);
    order = {};
    if (sameDevice) {
      pollStatus(start.orderRef);
      location.href = start.autoStartUrl; // opens the BankID app on this phone, which returns here when done
    } else {
      const refreshQr = async () => {
        const r = await api('/api/bankid/qr/' + start.orderRef);
        if (r.ok) drawQr((await r.json()).qr);
      };
      await refreshQr();
      order.qrTimer = setInterval(() => refreshQr().catch(() => {}), 1000); // BankID wants a new QR code every second
      pollStatus(start.orderRef);
    }
  } catch (e) {
    fail(e.message);
  }
}

async function checkStatus() {
  try {
    const r = await api('/api/bankid/status/' + order.orderRef);
    if (r.status === 404) return fail('The sign in expired. Try again.');
    const result = await r.json();
    if (result.status === 'pending') {
      $('status').textContent = hints[result.hintCode] ?? 'Waiting for BankID...';
    } else if (result.status === 'complete') {
      stopPolling();
      sessionStorage.setItem(tokenKey, result.sessionToken);
      showUser(result.user);
    } else {
      fail(hints[result.hintCode] ?? 'Sign in failed. Try again.');
    }
  } catch (e) {
    fail(e.message);
  }
}

function showUser(user) {
  $('user-name').textContent = user.name;
  $('user-pnr').textContent = user.personalNumber;
  show('signed-in');
}

async function cancel() {
  const orderRef = order?.orderRef;
  stopPolling();
  if (orderRef && !isLocal) await api('/api/bankid/cancel/' + orderRef, { method: 'POST' }).catch(() => {});
  show('signed-out');
}

async function signOut() {
  if (!isLocal) await api('/api/signout', { method: 'POST' }).catch(() => {});
  sessionStorage.removeItem(tokenKey);
  show('signed-out');
}

async function init() {
  backend = (await (await fetch('config.json')).json()).backendUrl;
  $('local-warning').hidden = !isLocal;
  $('sign-in-pc').onclick = () => startSignIn(false);
  $('sign-in-same').onclick = () => startSignIn(true);
  $('cancel').onclick = cancel;
  $('sign-out').onclick = signOut;
  if (isLocal) return show('signed-out');

  // Already signed in (page reload)?
  if (sessionStorage.getItem(tokenKey)) {
    const me = await api('/api/me').catch(() => null);
    if (me?.ok) return showUser(await me.json());
    sessionStorage.removeItem(tokenKey);
  }
  // Back from the BankID app on the same device: carry on polling the order that was started before leaving.
  const pending = sessionStorage.getItem(orderKey);
  if (pending) {
    show('waiting');
    $('qr').hidden = true;
    $('status').textContent = 'Checking BankID...';
    order = {};
    return pollStatus(pending);
  }
  show('signed-out');
}

init().catch(e => fail(e.message));
