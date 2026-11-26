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

For updates, copy a fresh source archive from the private repository into the local app directory, reload the store and rebuild the local app. Repository access on GitHub does not automatically provide an update channel to this local installation.
