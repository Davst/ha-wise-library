# 0.3.1

Add trailing pothos, fern, flowers, a glass garden, warm tea and a ceramic bird as shelf companions. Plants remain still; the glass garden glimmers, tea steam rises and fades, and the curled sleeping cat breathes gently. Decoration bases sit on the shelf at every screen size, and the candle flame stays attached to its wick. Reduced-motion preferences stop ambient animations.

# 0.3.0

The panel is redesigned as a bookcase, and it can now renew loans itself. Borrowed books stand face-out in return order, each over a label with its return date and the days left; books due within three days or overdue carry a red ribbon and say so in words. A sentence at the top says what goes back next, and the line under it names that book and counts the reservations. Reservations have their own shelf, each beside a slip with the portal's own text; no reservation state is parsed. Tapping a book, its date label or the book named under the sentence opens a view of one book per screen, which can be swiped or stepped through by a row of spines. Account connection, session import, the last sync time and MQTT status are in a sheet behind the library-card button in the header; a tap outside the sheet closes it, and the phone's back gesture closes the one-book view.

Renewing: a book the library offers for renewal shows Renew in its one-book view, and the shelf header offers Renew all. A second tap within four seconds confirms. The app opens the loans page with its saved sign-in, clears the page's default selection of every loan, selects only the chosen loans, presses the portal's renew button and waits for the library's confirmation; if none comes, the panel shows that and what the library said. A new endpoint, `POST /api/renew`, takes the app's own loan ids (up to 20 at once) and refuses any loan the library is not currently offering for renewal. A renewed book gets a green ribbon and moves to its new place in the order; the mark lasts until the panel is reloaded and gives way to the due-soon and overdue marks. A book the library does not offer for renewal links to Wise. Reservations still link to Wise to manage; nothing in the app places or cancels one.

The reader now collects each loan's author, ISBN, copy barcode and renewal offer, and each reservation's author and ISBN. A loan's id is its copy barcode, which stays the same after a renewal, so a renewed book is recognised by its id. Covers are the library's own: the reader fetches each cover by ISBN from inside the signed-in page, because the library refuses plain scripts, and stores it in the app's data folder (`covers/`); the app serves it at `/api/cover/<isbn>` with a one-week cache, which is the only response that is not `no-store`. The library's generic placeholder is recognised by comparing against its answer for an impossible ISBN, and such a book keeps a cover drawn from its title. That answer is remembered, so the library is not asked again; delete `covers/<isbn>.none` in the app's data folder to try again. A cover that fails to download is retried at the next refresh. The room behind a book and the spine in the row at the bottom take their colour from the cover.

The panel follows the language Home Assistant stores in the browser (`selectedLanguage`), in English or Dutch; messages that come from the app itself, such as sync errors, stay in English. The app serves its own fonts and two wood textures from `static/`: Libre Caslon Display, Figtree and Courier Prime, downloaded as woff2 from Google Fonts on 2026-11-27, with their SIL Open Font License texts from the google/fonts repository. A failed sync says when the last successful one was. If the panel cannot read its status, it says the panel is disconnected.

# 0.2.9

A page that changes while a stall is being described no longer replaces the refresh's own error, so a refused sign-in still pauses automatic refresh. Headings are now logged only from the Wise portal, never from the login hosts. A Refresh pressed during the 30-second startup delay is served by the first refresh instead of triggering a second one. The 0.2.6 retry of a first-load network error is removed: the startup delay is the real fix and the next refresh retries anyway. Reservation lists now require the signed-in menu and may each wait up to 35 seconds before failing.
# 0.2.8

An empty reservation list is recognised by the wording Wise actually shows, "Geen reserveringen gevonden", as well as "Je lijst is leeg". Before, an account without reservations failed every sync.
# 0.2.7

Reservation lists now wait until cards or the empty-list message have rendered, instead of a fixed five-second window, and a list that can't be verified logs which list failed with the same stall details. The first refresh after start waits 30 seconds so the app's network has settled; before, the portal's scripts failed with ERR_NETWORK_CHANGED and the login never loaded.
# 0.2.6

Fix sign-in succeeding but the loans page never being recognised. Wise keeps a hidden copy of the loan list ahead of the visible one, and the app waited for that copy to become visible. The app now checks rendered text and reads only rendered loan and reservation cards. The same flaw made a valid saved session look signed out. A network error on the first page load (such as ERR_NETWORK_CHANGED right after start) is retried once after 10 seconds.
# 0.2.5

If the portal can't be reached at all (DNS or connection failure, common right after Home Assistant starts), the refresh logs the network error code and retries at the next refresh instead of logging only an error type. Stall diagnostics on the Wise portal now log up to 1,200 characters of the main content.
# 0.2.4

When a page stalls, the app log also lists failed and still-pending requests (host and path only) and page script errors; on the Wise portal itself it adds the first 400 characters of the page text. Page text is never logged from the login host.
# 0.2.3

Fix automatic sign-in being reported as refused after it succeeded. The Wise portal shows its own alert region before the loans render, which was mistaken for a login error. Alerts now count only on the login page; once the library redirects back to Wise, the app waits for the loans to render, and a slow render retries at the next refresh instead of pausing automatic refresh.
# 0.2.2

The app log now records every refresh: start, success with counts, and each failure with its message. When sign-in stalls it logs where the browser stopped (host, path, page title, heading and the redirect chain with status codes and timings; never query strings or credentials), and a refused sign-in logs the login page's error text. A login page that never loads no longer pauses automatic refresh, since nothing was submitted.
# 0.2.1

Fix automatic sign-in: the national login page has a hidden duplicate Continue button, and the add-on clicked it instead of the real one. If the button can't be pressed, nothing is submitted and the next refresh retries. A successful sync no longer fails when the login leaves cookies from unrelated hosts; those are dropped before the session is saved. Unexpected refresh failures now log their error type and location to the app log (never the message, which can contain sign-in URLs).
# 0.2.0

Add library username/password setup in Home Assistant Configuration. Reuse valid sessions and sign in again through the national library login when necessary. Credentials never appear in the panel API or logs. Rejected sign-ins pause automatic retries; manual session import remains available for additional verification.
# 0.1.0

Initial web-portal bridge: loan parsing, reservation reader, MQTT discovery, ingress panel and isolated session helper. Live login portability, populated reservation layouts and Home Assistant deployment remain to be verified.

