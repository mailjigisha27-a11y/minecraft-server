import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import main


class LoadConfigTests(unittest.TestCase):
    """Tests for load_config(). They use temporary files, so your real
    config.json and manager.log are never touched."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config_path = os.path.join(self.tmp.name, "config.json")
        self.log_path = os.path.join(self.tmp.name, "manager.log")
        for name, value in (("CONFIG_FILE", self.config_path), ("LOG_FILE", self.log_path)):
            patcher = mock.patch.object(main, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_config(self, data):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self):
        # Hide the messages that load_config prints, so the test output stays clean
        with contextlib.redirect_stdout(io.StringIO()):
            return main.load_config()

    def test_missing_file_gives_defaults_and_creates_file(self):
        config = self.load()
        self.assertEqual(config, main.DEFAULTS)
        self.assertTrue(os.path.isfile(self.config_path))

    def test_valid_values_are_used(self):
        self.write_config({
            "keep_backups": 3,
            "backup_every_minutes": 15,
            "max_memory": "4G",
            "server_jar": "paper.jar",
        })
        config = self.load()
        self.assertEqual(config["keep_backups"], 3)
        self.assertEqual(config["backup_every_minutes"], 15)
        self.assertEqual(config["max_memory"], "4G")
        self.assertEqual(config["server_jar"], "paper.jar")

    def test_zero_backups_is_not_valid(self):
        self.write_config({"keep_backups": 0})
        self.assertEqual(self.load()["keep_backups"], main.DEFAULTS["keep_backups"])

    def test_true_is_not_a_number(self):
        self.write_config({"keep_backups": True})
        self.assertEqual(self.load()["keep_backups"], main.DEFAULTS["keep_backups"])

    def test_zero_restarts_is_allowed(self):
        self.write_config({"max_restarts": 0})
        self.assertEqual(self.load()["max_restarts"], 0)

    def test_memory_format(self):
        self.write_config({"max_memory": "2GB", "min_memory": "512M"})
        config = self.load()
        self.assertEqual(config["max_memory"], main.DEFAULTS["max_memory"])  # "2GB" is not valid
        self.assertEqual(config["min_memory"], "512M")                       # "512M" is valid

    def test_broken_json_uses_defaults(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("{ this is not json")
        self.assertEqual(self.load(), main.DEFAULTS)

    def test_json_that_is_not_an_object(self):
        self.write_config([1, 2, 3])
        self.assertEqual(self.load(), main.DEFAULTS)

    def test_empty_jar_name_is_not_valid(self):
        self.write_config({"server_jar": "   "})
        self.assertEqual(self.load()["server_jar"], main.DEFAULTS["server_jar"])

    def test_unknown_keys_are_ignored(self):
        self.write_config({"favorite_color": "blue", "keep_backups": 7})
        config = self.load()
        self.assertNotIn("favorite_color", config)
        self.assertEqual(config["keep_backups"], 7)


if __name__ == "__main__":
    unittest.main()