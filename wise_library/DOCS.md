# Setup

See the project README for the local installation and session helper. Configure your MQTT broker and the Library username/password in the app Configuration tab, then save and restart. Your credentials stay in Home Assistant app options. The password field is masked; backups may contain the password. Importing a session from the helper remains an optional fallback for additional sign-in verification.

Only Bibliotheek AanZet's Dutch Wise portal is currently supported. `branch_id` selects a portal route, not necessarily the physical branch where books were borrowed. `account_id` must be unique for each running add-on/account; keep it stable to preserve entity IDs.

Changing `account_id` creates a new MQTT device. Delete the old device manually from Home Assistant to remove its retained discovery entries. Do not share session exports or include them in support requests. Add-on backups can include its session and MQTT credentials; protect those backups accordingly.

For notifications, trigger an automation when “Due within three days” is greater than zero. Use the sensor's `loans` attribute to list titles and dates. Entity IDs are assigned by Home Assistant; select the actual entity from the device rather than assuming an ID.
