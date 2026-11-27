import {pickLanguage, translator} from './i18n.js';
import {glance, inReturnOrder, isoDay, renewedIds} from './model.js';
import {columnsOf, markRoom, renderHeld, renderRoom, renderShelves, roomIndex, travel} from './views.js';

const $ = id => document.getElementById(id);
const i18n = translator(pickLanguage(localStorage.getItem('selectedLanguage'), navigator.language));
const {t} = i18n;
const shelves = $('shelves');
const held = $('held');
const feed = $('feed');
const strip = $('strip');
const room = $('room');
const state = {
  csrf: '',
  portalUrl: '',
  loans: [],
  holds: [],
  renewed: new Set(),
  shown: '',
  failed: false,
  busy: false,
  renewal: null,
  armed: null,
  armTimer: 0,
};

function view() {
  return {
    i18n,
    today: new Date(),
    renewed: state.renewed,
    open: openRoom,
    renewUrl: `${state.portalUrl}/checkouts/physical-materials`,
    manageUrl: `${state.portalUrl}/my-holds`,
  };
}

function say(message) {
  $('notice').hidden = !message;
  $('notice').textContent = message || '';
}

function glanceText(data, next) {
  if (!data.snapshot) {
    return t(data.credentials_configured || data.session_present ? 'glanceWaiting' : 'glanceConnect');
  }
  if (next.kind === 'none') return t('glanceNone');
  if (next.kind === 'overdue') {
    return next.count === 1 ? t('glanceOverdueOne') : t('glanceOverdueMany', {n: next.count});
  }
  if (next.kind === 'later') return t('glanceLater', {date: i18n.weekdayDate(next.loan.due_date)});
  if (next.count > 1) return t('glanceSoonMany', {n: next.count});
  if (next.days === 0) return t('glanceToday');
  return next.days === 1 ? t('glanceTomorrow') : t('glanceOn', {weekday: i18n.weekday(next.loan.due_date)});
}

// The second line names the one book the sentence above is about, then counts the reservations.
function showAlso(data, next) {
  const line = $('also');
  line.replaceChildren();
  if (!data.snapshot) {
    line.textContent = data.credentials_configured || data.session_present ? '' : t('needCredentials');
    return;
  }
  const parts = [];
  if (next.count === 1) {
    const title = document.createElement('button');
    title.type = 'button';
    title.textContent = next.loan.title;
    title.addEventListener('click', () => openRoom(next.loan.id));
    parts.push(title);
  }
  const phrase = text => {
    const span = document.createElement('span');
    span.textContent = text;
    return span;
  };
  const reserved = state.holds.length;
  if (reserved) parts.push(phrase(reserved === 1 ? t('reservedOne') : t('reservedMany', {n: reserved})));
  if (!parts.length && !state.loans.length) parts.push(phrase(t('shelfReady')));
  parts.forEach((part, index) => line.append(index ? ' · ' : '', part));
}

function syncText(data) {
  if (data.busy) return t('statusRefreshing');
  if (data.error) return t('statusAttention');
  return data.last_success ? t('statusSynced', {time: i18n.time(data.last_success)}) : t('statusNotConnected');
}

function waitingText(data) {
  if (data.last_success) return t('lastSync', {time: i18n.dateTime(data.last_success)});
  if (data.credentials_configured) return t('waitingCredentials');
  return t(data.session_present ? 'waitingSession' : 'needCredentials');
}

function connectionTitle(data) {
  if (data.credentials_configured) return t('connectConfigured');
  return t(data.session_present ? 'connectSession' : 'connectTitle');
}

function noticeText(data) {
  if (data.renewal?.state === 'failed') return data.renewal.message;
  if (!data.error) return '';
  return data.last_success ? `${data.error} ${t('stale', {time: i18n.dateTime(data.last_success)})}` : data.error;
}

function showBooks(snapshot) {
  const loans = inReturnOrder(snapshot.loans);
  const holds = snapshot.reservations;
  const moved = state.loans.length ? renewedIds(state.loans, loans) : [];
  const present = new Set(loans.map(loan => loan.id));
  state.renewed = new Set([...state.renewed, ...moved].filter(id => present.has(id)));
  const shown = JSON.stringify([loans, holds, [...state.renewed], isoDay(new Date()), columnsOf(shelves)]);
  state.loans = loans;
  state.holds = holds;
  if (shown === state.shown) return;
  state.shown = shown;
  const decorations = new Set();
  travel(shelves, () => renderShelves(shelves, loans, view(), decorations), moved);
  renderHeld(held, holds, view(), decorations);
  document.querySelector('.case').classList.toggle('has-corner-web', !decorations.has('cobweb'));
  $('reserved').hidden = !holds.length;
  $('loan-count').textContent = loans.length;
  $('hold-count').textContent = holds.length;
  if (room.open) fillRoom(feed.children[roomIndex(feed)]?.dataset.id);
}

function apply(data) {
  state.csrf = data.csrf;
  state.failed = !!data.error;
  state.busy = data.busy;
  state.renewal = data.renewal;
  state.portalUrl = data.portal_url;
  document.body.classList.toggle('busy', data.busy);
  showBooks(data.snapshot || {loans: [], reservations: []});
  const next = glance(state.loans, new Date());
  $('sync').textContent = syncText(data);
  $('glance').textContent = glanceText(data, next);
  showAlso(data, next);
  say(noticeText(data));
  $('refresh').disabled = data.busy || (!data.session_present && !data.credentials_configured);
  $('attention').hidden = !data.error && (data.session_present || data.credentials_configured);
  $('renew-all').hidden = !state.loans.some(loan => loan.renew_until);
  paintRenew();
  $('manage').href = view().manageUrl;
  $('session-title').textContent = connectionTitle(data);
  $('how').hidden = data.credentials_configured;
  $('updated').textContent = waitingText(data);
  $('mqtt').textContent = t(data.mqtt_connected ? 'mqttOn' : 'mqttOff');
}

async function status() {
  let data;
  try {
    const response = await fetch('./api/status');
    if (!response.ok) throw new Error(`status ${response.status}`);
    data = await response.json();
  } catch {
    // An unreachable or unreadable status keeps the last books on screen and says the panel lost its connection.
    say(t('panelUnavailable'));
    $('sync').textContent = t('statusOffline');
    return;
  }
  apply(data);
}

async function post(path, body) {
  const headers = {'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf};
  const response = await fetch(path, {method: 'POST', headers, body: JSON.stringify(body)});
  if (!response.ok) throw new Error(await response.text());
}

const renewing = () => state.busy && state.renewal?.state === 'running';

function paintRenew() {
  for (const button of document.querySelectorAll('[data-renew]')) {
    const all = button.dataset.renew === 'all';
    const armed = state.armed === button.dataset.renew;
    const label = button.querySelector('span:not(.ic)') || button;
    button.disabled = state.busy;
    label.textContent = renewing()
      ? t('renewing')
      : armed
        ? t(all ? 'renewAllConfirm' : 'renewConfirm')
        : (button.dataset.label ?? t('renewAll'));
  }
}

// One tap asks, a second tap within four seconds renews; the library renews only what is offered.
async function askRenew(key) {
  if (state.busy) return;
  if (state.armed !== key) {
    state.armed = key;
    clearTimeout(state.armTimer);
    state.armTimer = setTimeout(() => {
      state.armed = null;
      paintRenew();
    }, 4000);
    paintRenew();
    return;
  }
  state.armed = null;
  const ids = key === 'all' ? state.loans.filter(loan => loan.renew_until).map(loan => loan.id) : [key];
  state.busy = true;
  state.renewal = {state: 'running'};
  paintRenew();
  try {
    await post('./api/renew', {ids});
  } catch (error) {
    state.busy = false;
    state.renewal = null;
    say(error.message);
  }
  await status();
}

async function refresh() {
  $('refresh').disabled = true;
  try {
    await post('./api/refresh', {});
    await status();
  } catch (error) {
    say(error.message);
  }
}

function fillRoom(id) {
  renderRoom(feed, strip, state.loans, state.holds, view());
  paintRenew();
  const index = Math.max(0, [...feed.children].findIndex(page => page.dataset.id === id));
  feed.scrollTop = index * feed.clientHeight;
  markPosition();
}

function markPosition() {
  const index = roomIndex(feed);
  markRoom(strip, index);
  const inLoans = index < state.loans.length;
  const at = inLoans ? index + 1 : index - state.loans.length + 1;
  const total = inLoans ? state.loans.length : state.holds.length;
  $('position').textContent = `${t(inLoans ? 'borrowed' : 'reserved')} · ${t('position', {at, total})}`;
}

// The room gets a history entry, so the phone's back gesture closes it instead of leaving the panel.
function openRoom(id) {
  room.showModal();
  fillRoom(id);
  history.pushState({room: true}, '');
}

function leaveRoom() {
  if (history.state?.room) history.back();
  else room.close();
}

async function importSession(event) {
  event.preventDefault();
  const file = $('session-file').files[0];
  const button = event.submitter;
  const message = $('upload-message');
  if (!file || file.size > 2 * 1024 * 1024) {
    message.textContent = t('importTooLarge');
    return;
  }
  button.disabled = true;
  try {
    await post('./api/session', JSON.parse(await file.text()));
    message.textContent = t('importDone');
    $('session-file').value = '';
    await status();
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

document.documentElement.lang = i18n.language;
for (const element of document.querySelectorAll('[data-t]')) element.textContent = t(element.dataset.t);
$('refresh').setAttribute('aria-label', t('refresh'));
$('open-connection').setAttribute('aria-label', t('openConnection'));
$('close-connection').setAttribute('aria-label', t('close'));
$('glance').textContent = t('glanceOpening');

$('refresh').addEventListener('click', refresh);
$('open-connection').addEventListener('click', () => $('connection').showModal());
$('close-connection').addEventListener('click', () => $('connection').close());
// A tap outside the sheet closes it, as Escape does.
$('connection').addEventListener('click', event => {
  const box = $('connection').getBoundingClientRect();
  const inside = event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top;
  if (!inside || event.clientY > box.bottom) $('connection').close();
});
$('leave').addEventListener('click', leaveRoom);
room.addEventListener('cancel', event => {
  event.preventDefault();
  leaveRoom();
});
addEventListener('popstate', () => {
  if (room.open) room.close();
});
$('session-form').addEventListener('submit', importSession);
feed.addEventListener('scroll', markPosition, {passive: true});
document.addEventListener('click', event => {
  const button = event.target.closest('[data-renew]');
  if (button) askRenew(button.dataset.renew);
});

status();
setInterval(status, 5000);
