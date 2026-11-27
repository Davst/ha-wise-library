# Wise Library for Home Assistant

A web-portal bridge for Bibliotheek AanZet, built while official Wise API access is being requested. It reads the Dutch Wise portal using a dedicated Playwright browser session and publishes Home Assistant entities through MQTT discovery. No borrowed application keys or private API calls.

## First release

- Borrowed-book list, return dates and borrowing branch.
- Sensors for borrowed books, overdue books, books due within three days, next return date and reservations.
- Home Assistant sidebar panel drawn as a bookcase: borrowed books in return order with their dates, a shelf for reservations, a one-book view, manual refresh, session import and connection status. English and Dutch, following the language Home Assistant stores in the browser; sync errors stay in English.
- Reservation lists for standard, first-available and sequential holds. Populated reservation layouts still need live verification.
- Renewing from the panel: Renew on a book, or Renew all, after a confirming second tap. The app drives the portal's own selection and renew button, so only books the library offers for renewal can be renewed, and it waits for the library's confirmation. Real covers are read from the loan pages and kept in the app's data folder. Open Library is checked once by exact ISBN for a higher-resolution cover; temporary failures retry on a later refresh. ISBNs are sent to [Open Library](https://openlibrary.org/dev/docs/api/covers) without library credentials. Placing and cancelling reservations still open Wise: the app has never seen a populated reservation list, so it does not act on one.

This is an early implementation, installed and running on Home Assistant OS. Library credentials must be entered in Home Assistant before live loan syncing can be verified. The loan selectors are based on an inspected AanZet portal. Only the Dutch layout and physical materials are supported. E-books and audiobooks are not included. Sessions expire; reconnect using the helper when prompted. Home Assistant reminders are automations you create from the sensors, not notifications automatically enabled by the add-on.

Local validation: the automated tests pass, including a real Chromium reader run with controlled network fixtures, HTTP ingress/session checks and browser tests of the panel. The container image built successfully on Home Assistant OS, the ingress panel loaded, MQTT connected and all five sensors were discovered. A real-account sign-in is still pending; browser authentication has been tested with controlled fixtures.

## Install in Home Assistant OS

1. Install/configure a broker (for example Mosquitto) and Home Assistant's MQTT integration.
2. Open **Settings → Apps → App store**, choose **⋮ → Repositories** and add `https://github.com/Davst/ha-wise-library`. Install **Wise Library** from the new repository section. Home Assistant builds the Chromium image on the device, which may take several minutes.
3. Set the MQTT host, port and credentials in the app's Configuration tab. Default host is `core-mosquitto`. The initial supported target is the AanZet portal with `branch_id: "2709"` (the route inspected during development; not an asserted physical-branch identifier).
4. In the same tab, enter **Library username** and **Library password** and save.
5. Start the app and open **Library** in the sidebar. The first sync runs about 30 seconds after the app starts, once its network has settled. It reuses the saved session and signs in again only when required. A successful read supplies all five sensors. If extra verification is required, use the optional session helper below instead.

The repository is public, so Home Assistant needs no GitHub credential. Updates are published to its `main` branch with a new version number. Home Assistant checks for them periodically; to install one straight away, choose **⋮ → Check for updates** in the App store, then **Update** on Wise Library. The image is rebuilt on the device.

## Sign in through Home Assistant

Open **Settings → Apps → Wise Library → Configuration**. Set **Library username** and **Library password**, save and restart. The password is masked in the form and stored only in local app options; it is never returned by the Library panel, logged or committed. App backups may contain it, so protect those backups.

The app follows the normal AanZet redirect to the national login at inloggen.kb.nl. It submits credentials only to that HTTPS host and checks the form destination first. It attempts one sign-in per refresh. A rejected login or additional verification pauses automatic retries; fix the settings and restart, or deliberately use Refresh library to retry. CAPTCHA and MFA are never bypassed.

## Optional: import a library session

From the project directory on a computer with Python 3.12+:

```powershell
python -m venv .venv
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\.browsers"
.\.venv\Scripts\python -m pip install -r wise_library\requirements.txt
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python tools\connect.py
```

A **new, isolated browser** opens the library website. Sign in there; do not send anyone your password. Return to the terminal and press Enter when your loan overview is visible. The helper saves `.data/storage-state.json`. Import that file through the add-on panel. Keep it private: it grants access to the library account. The helper exports only the supported library/login hosts, and the add-on will reject unrelated cookies. Delete the transfer copy after importing.

This helper does not read your normal browser profile. The session's portability and persistence across browser restarts must be verified with a real login; if the website changes its authentication mechanism, reconnecting may be necessary. Restoring a browser session is not equivalent to obtaining official API access.

## Development

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
$env:WISE_LOCAL = '1'
$env:WISE_DATA = '.data'
.\.venv\Scripts\python -m wise_library.app.server
```

Open http://127.0.0.1:8099. Local mode binds only to loopback. Without a broker the panel still works, but reports MQTT disconnected. In the add-on, HTTP is available only through Supervisor ingress; there is no exposed host port. Sessions and options remain in private `/data/session` files and are excluded from source control. The container runs the browser and HTTP service as a non-root user. No privileged mode, host network, Docker socket or Home Assistant access token is requested.

The add-on polls hourly by default (minimum 15 minutes). A failed read keeps the panel's last successful result visibly stale and marks MQTT entities unavailable. Manual refresh is limited to once per minute. A successful poll saves refreshed browser storage atomically; no cookies or token values are logged. When a refresh stalls, the app log records where it stopped; on the Wise portal that includes up to 1,200 characters of page text, which can show your name and loan titles. Nothing from the login page is logged beyond its address and title. A Home Assistant restart or broker reconnect republishes discovery. State has an expiry as an extra fallback when the bridge stops updating.

## Roadmap

1. Verify real-account automatic sign-in and live loans; Home Assistant installation and MQTT discovery have been verified.
2. Verify populated hold lists with a willing test account; preserve displayed status until pickup-state parsing is proven.
3. Cancel reservations from the panel once a populated reservation list has been inspected with a willing test account. Renewing was verified on a real account on 2026-11-27: the page opens with every loan selected, one press of the renew button needs no confirm step, and it shows "De geselecteerde exemplaren zijn verlengd".
4. Replace the portal reader with the official API when OCLC grants application access. See [API research](docs/api-research.md).
