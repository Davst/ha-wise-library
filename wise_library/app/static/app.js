let csrf = '';
let busy = false;
const el = id => document.getElementById(id);
const dateText = value => value ? new Date(value + 'T12:00:00').toLocaleDateString(undefined, {day:'numeric',month:'short'}) : '—';
function node(tag, text, cls) { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; }
async function status() {
  try {
    const response = await fetch('./api/status');
    if (!response.ok) throw new Error('Panel connection unavailable. Reopen it through Home Assistant.');
    const data = await response.json(); csrf = data.csrf; busy = data.busy;
    el('connection').textContent = busy ? 'Refreshing library…' : data.error ? 'Needs attention' : data.last_success ? 'Library connected' : 'Not connected';
    el('connection').classList.toggle('online', !!data.last_success && !data.error);
    el('mqtt').textContent = 'Home Assistant · MQTT ' + (data.mqtt_connected ? 'connected' : 'disconnected');
    el('notice').hidden = !data.error;
    el('notice').textContent = data.error ? data.error + (data.last_success ? ' The books below are from the last successful sync.' : '') : '';
    el('refresh').disabled = busy || (!data.session_present && !data.credentials_configured);
    el('manage').hidden = false; el('manage').href = data.portal_url + '/my-holds';
    el('session-title').textContent = data.credentials_configured ? 'Automatic sign-in is configured.' : data.session_present ? 'Your session is saved.' : 'Connect in Home Assistant settings.';
    el('updated').textContent = data.last_success ? 'Last successful sync · ' + new Date(data.last_success).toLocaleString() : data.credentials_configured ? 'Credentials configured. Waiting for the first successful sync…' : data.session_present ? 'Session imported. Waiting for the first successful sync…' : 'Enter your library credentials in the app Configuration tab to connect.';
    if (!data.snapshot) return;
    const s = data.snapshot;
    el('loan-count').textContent = s.loan_count; el('due-count').textContent = s.due_soon_count;
    el('overdue-count').textContent = s.overdue_count; el('next-date').textContent = dateText(s.next_due_date);
    el('reservation-count').textContent = s.reservation_count;
    el('loans').replaceChildren();
    for (const book of s.loans) {
      const row = node('article', '', 'book-row'); const details = node('div', '');
      details.append(node('h3', book.title, 'book-name'), node('span', book.branch, 'book-meta'));
      row.append(details, node('span', 'Return ' + dateText(book.due_date), 'due-badge'));
      el('loans').append(row);
    }
    if (!s.loans.length) el('loans').append(node('p', 'Nothing borrowed right now. Your shelf is ready for something new.', 'muted'));
    el('holds').replaceChildren();
    for (const hold of s.reservations) {const detail = node('details', '', 'hold'); detail.append(node('summary', hold.title), node('p', hold.details)); el('holds').append(detail);}
    if (!s.reservations.length) el('holds').append(node('p', 'No reservations at the moment.', 'muted'));
  } catch (error) { el('notice').hidden = false; el('notice').textContent = error.message; el('connection').textContent = 'Panel disconnected'; el('connection').classList.remove('online'); }
}
async function post(path, body) {
  const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)});
  if (!response.ok) throw new Error(await response.text());
}
el('refresh').addEventListener('click', async () => {try {el('refresh').disabled = true; await post('./api/refresh', {}); await status();} catch(error) {el('notice').hidden = false;el('notice').textContent = error.message;}});
el('session-form').addEventListener('submit', async event => {
  event.preventDefault(); const file = el('session-file').files[0]; const button = event.submitter;
  try {if (!file || file.size > 2 * 1024 * 1024) throw new Error('Choose a session JSON file smaller than 2 MB.'); button.disabled = true; await post('./api/session', JSON.parse(await file.text()));el('upload-message').textContent = 'Session imported. Checking your library…';el('session-file').value = '';await status();}
  catch(error){el('upload-message').textContent = error.message;} finally {button.disabled = false;}
});
status(); setInterval(status, 5000);
