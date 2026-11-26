# 0.2.1

Fix automatic sign-in: the national login page has a hidden duplicate Continue button, and the add-on clicked it instead of the real one. If the button can't be pressed, nothing is submitted and the next refresh retries. A successful sync no longer fails when the login leaves cookies from unrelated hosts; those are dropped before the session is saved. Unexpected refresh failures now log their error type and location to the app log (never the message, which can contain sign-in URLs).
# 0.2.0

Add library username/password setup in Home Assistant Configuration. Reuse valid sessions and sign in again through the national library login when necessary. Credentials never appear in the panel API or logs. Rejected sign-ins pause automatic retries; manual session import remains available for additional verification.
# 0.1.0

Initial web-portal bridge: loan parsing, reservation reader, MQTT discovery, ingress panel and isolated session helper. Live login portability, populated reservation layouts and Home Assistant deployment remain to be verified.

