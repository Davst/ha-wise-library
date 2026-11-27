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

