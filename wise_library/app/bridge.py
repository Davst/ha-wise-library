def discovery_messages(account_id, interval):
    base = f"wise_library/{account_id}"
    device = {"identifiers": [f"wise_library_{account_id}"], "name": "Wise Library",
              "manufacturer": "Community", "model": "Wise portal bridge"}
    fields = {"loan_count": "Borrowed books", "overdue_count": "Overdue books",
              "due_soon_count": "Due within three days", "next_due_date": "Next return date",
              "reservation_count": "Reservations"}
    messages = []
    for field, name in fields.items():
        payload = {"name": name, "unique_id": f"wise_library_{account_id}_{field}",
                   "state_topic": f"{base}/state", "value_template": "{{ value_json." + field + " }}",
                   "availability_topic": f"{base}/availability", "device": device,
                   "expire_after": interval * 2 + 300,
                   "json_attributes_topic": f"{base}/attributes", "icon": "mdi:bookshelf"}
        if field == "next_due_date":
            payload["device_class"] = "date"
            payload["value_template"] = "{{ value_json.next_due_date if value_json.next_due_date else none }}"
        messages.append((f"homeassistant/sensor/wise_library_{account_id}/{field}/config", payload))
    return messages


class MqttBridge:
    def __init__(self, options):
        import paho.mqtt.client as mqtt
        import threading
        self.options = options
        self.base = f"wise_library/{options['account_id']}"
        self.snapshot = None
        self.lock = threading.Lock()
        self.connected = False
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"wise-library-{options['account_id']}")
        if options.get("mqtt_username"):
            self.client.username_pw_set(options['mqtt_username'], options.get('mqtt_password', ''))
        self.client.will_set(f"{self.base}/availability", "offline", qos=1, retain=True)
        self.client.on_connect = self._connected
        self.client.on_disconnect = self._disconnected
        self.client.on_message = self._message
        self.client.reconnect_delay_set(5, 120)

    def start(self):
        self.client.connect_async(self.options['mqtt_host'], self.options['mqtt_port'], 60)
        self.client.loop_start()

    def _connected(self, client, userdata, flags, reason_code, properties):
        self.connected = not reason_code.is_failure
        if self.connected:
            client.subscribe('homeassistant/status')
            self._publish()

    def _disconnected(self, client, userdata, flags, reason_code, properties):
        self.connected = False

    def _message(self, client, userdata, message):
        if message.payload == b'online':
            self._publish()

    def _publish(self):
        import json
        import time
        with self.lock:
            for topic, payload in discovery_messages(self.options['account_id'], self.options['poll_interval_minutes'] * 60):
                self.client.publish(topic, json.dumps(payload), qos=1, retain=True)
            fresh = self.snapshot and time.time() - self.snapshot[0] < self.options['poll_interval_minutes'] * 120 + 300
            if fresh:
                _, state, attributes = self.snapshot
                self.client.publish(f"{self.base}/state", json.dumps(state), qos=1, retain=True)
                self.client.publish(f"{self.base}/attributes", json.dumps(attributes), qos=1, retain=True)
            self.client.publish(f"{self.base}/availability", 'online' if fresh else 'offline', qos=1, retain=True)

    def update(self, state, attributes):
        import time
        with self.lock:
            self.snapshot = (time.time(), state, attributes)
        self._publish()

    def unavailable(self):
        with self.lock:
            self.snapshot = None
        self.client.publish(f"{self.base}/availability", 'offline', qos=1, retain=True)

    def stop(self):
        self.unavailable()
        self.client.disconnect()
        self.client.loop_stop()
