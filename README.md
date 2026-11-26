# Wise Library for Home Assistant

A web-portal bridge for Bibliotheek AanZet, built while official Wise API access is being requested. It reads the Dutch Wise portal using a dedicated Playwright browser session and publishes Home Assistant entities through MQTT discovery. No borrowed application keys or private API calls.

## First release

- Borrowed-book list, return dates and borrowing branch.
- Sensors for borrowed books, overdue books, books due within three days, next return date and reservations.
- Home Assistant sidebar panel, manual refresh, session import and connection status.
- Reservation lists for standard, first-available and sequential holds. Populated reservation layouts still need live verification.
- Links to Wise to renew books and manage reservations. This version never renews, places or cancels anything itself.

This is an early implementation, installed and running on Home Assistant OS. A real library session import is still required before live loan syncing is verified. The loan selectors are based on an inspected AanZet portal. Only the Dutch layout and physical materials are supported. E-books and audiobooks are not included. Sessions expire; reconnect using the helper when prompted. Home Assistant reminders are automations you create from the sensors, not notifications automatically enabled by the add-on.

Local validation: 14 automated tests passed, including a real Chromium reader run with controlled network fixtures and HTTP ingress/session checks. The container image built successfully on Home Assistant OS, the ingress panel loaded, MQTT connected and all five sensors were discovered. No real account session has been imported into this add-on yet.

## Install locally in Home Assistant OS

1. Install/configure a broker (for example Mosquitto) and Home Assistant's MQTT integration.
2. Copy the `wise_library` directory into `/local_apps/wise_library` on current Home Assistant OS (`/addons/wise_library` on older versions). Reload the app/add-on store and install **Wise Library** from the local section. The initial Chromium image build may take several minutes.
3. Set the MQTT host, port and credentials in add-on options. Default host is `core-mosquitto`. The initial supported target is the AanZet portal with `branch_id: "2709"` (the route inspected during development; not an asserted physical-branch identifier).
4. Start the add-on and open **Library** in the sidebar.
5. Generate a session file on your own computer using the helper below, then import it in the Library panel. A successful read creates one MQTT device with five sensors. Refresh failures mark the sensors unavailable rather than reporting zero books.

Source is maintained in the private repository https://github.com/Davst/ha-wise-library. Install the add-on from a local copy of the source so Home Assistant does not need a GitHub credential. Updates must be copied from the private repository and rebuilt locally.

## Connect your library session

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

The add-on polls hourly by default (minimum 15 minutes). A failed read keeps the panel's last successful result visibly stale and marks MQTT entities unavailable. Manual refresh is limited to once per minute. A successful poll saves refreshed browser storage atomically; no cookies or token values are logged. A Home Assistant restart or broker reconnect republishes discovery. State has an expiry as an extra fallback when the bridge stops updating.

## Roadmap

1. Verify a real login export/import and live loans; the Home Assistant installation and MQTT discovery have been verified.
2. Verify populated hold lists with a willing test account; preserve displayed status until pickup-state parsing is proven.
3. Add explicit, confirmed reservation/renewal actions using verified portal flows.
4. Replace the portal reader with the official API when OCLC grants application access. See [API research](docs/api-research.md).
