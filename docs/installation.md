# Installation verification

Verified 26 November 2026 on Nicole's Home Assistant:

- Home Assistant Core 2026.11.3, OS 18.4, amd64.
- Private GitHub source repository; no GitHub credential stored in Home Assistant.
- Published add-on source copied into `/local_apps/wise_library` and built locally.
- `local_wise_library` version 0.1.0 running, automatic startup, watchdog and sidebar enabled.
- Mosquitto 7.1.3 installed with automatic startup and a dedicated bridge login. Credentials remain in Home Assistant add-on options only.
- MQTT integration configured; Wise Library device and all five sensors discovered.
- Library ingress panel loaded and reported MQTT connected.
- Repository CI passed on Ubuntu 24.04.

Library session import is still pending. Sensors correctly remain unavailable until the first verified library sync. Populated reservations and automatic session refresh still require live testing. No existing library loans or reservations were changed. No Home Assistant Core restart was required.

## 27 November 2026

- Installed from the GitHub repository (`03bd3b95_wise_library`), not from a local copy; the repository is public, so no GitHub credential is stored in Home Assistant.
- Version 0.2.9 running. Automatic sign-in through inloggen.kb.nl verified with real credentials: the first sync published 4 loans and 0 reservations, and the next refresh reused the saved session without signing in again.
- Empty reservation lists verified. Populated reservations remain untested.

For updates, push a new version to `main`, choose **⋮ → Check for updates** in the App store, then **Update** on Wise Library. The image is rebuilt on the device.
