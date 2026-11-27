import unittest

from wise_library.app.bridge import discovery_messages


class DiscoveryTests(unittest.TestCase):
    def test_sensors_have_stable_identity_and_expiry(self):
        messages = discovery_messages("home", 3600)
        self.assertEqual(len(messages), 5)
        due = next(payload for topic, payload in messages if topic.endswith("/next_due_date/config"))
        self.assertEqual(due["device_class"], "date")
        self.assertEqual(due["expire_after"], 7500)
        self.assertEqual(due["availability_topic"], "wise_library/home/availability")
        self.assertEqual(due["unique_id"], "wise_library_home_next_due_date")
        self.assertTrue(all(p["device"]["identifiers"] == ["wise_library_home"] for _, p in messages))
