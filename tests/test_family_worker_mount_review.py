"""Synthetic checks for the one-shot Worker mount plan; no Docker connection."""
import copy
import unittest
from family_worker_mount_review import review


class TestFamilyWorkerMountReview(unittest.TestCase):
    def setUp(self):
        self.valid = [{
            "Name": "/mini-utopia-family-api-1",
            "State": {"Running": True},
            "Config": {"User": "family"},
            "Mounts": [
                {"Destination": "/data", "Type": "volume", "RW": True,
                 "Name": "synthetic-private-volume", "Source": "/private/a"},
                {"Destination": "/movies", "Type": "bind", "RW": False,
                 "Source": "/private/b"},
            ],
        }]

    def test_accept_and_redact(self):
        result = review(self.valid)
        self.assertEqual(result["movies_mount"], "bind_ro")
        self.assertFalse(result["production_deployed"])
        self.assertNotIn("/private/", repr(result))
        self.assertNotIn("synthetic-private-volume", repr(result))

    def test_wrong_mount_type_fails(self):
        data = copy.deepcopy(self.valid)
        data[0]["Mounts"][0]["Type"] = "bind"
        with self.assertRaises(ValueError):
            review(data)

    def test_movies_must_remain_read_only(self):
        data = copy.deepcopy(self.valid)
        data[0]["Mounts"][1]["RW"] = True
        with self.assertRaises(ValueError):
            review(data)

    def test_not_running_fails(self):
        data = copy.deepcopy(self.valid)
        data[0]["State"]["Running"] = False
        with self.assertRaises(ValueError):
            review(data)

    def test_ambiguous_bind_fails(self):
        data = copy.deepcopy(self.valid)
        data[0]["Mounts"].append(data[0]["Mounts"][1])
        with self.assertRaises(ValueError):
            review(data)
