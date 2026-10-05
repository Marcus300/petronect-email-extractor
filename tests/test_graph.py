import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from email_extractor.graph import EMBEDDED_GRAPH_CONFIG, GraphEmailSource, load_graph_config


class GraphTests(unittest.TestCase):
    def test_msal_cache_lock_dependency_is_available(self) -> None:
        from msal_extensions.cache_lock import CrossPlatLock

        self.assertTrue(callable(CrossPlatLock))

    def test_missing_config_uses_embedded_distribution_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "graph_config.json"
            config = load_graph_config(path)
            self.assertFalse(path.exists())
            self.assertEqual(config, EMBEDDED_GRAPH_CONFIG)
            self.assertNotIn("client_secret", config)
            self.assertEqual(len(config["shared_mailboxes"]), 2)

    def test_placeholder_local_config_falls_back_to_embedded_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "graph_config.json"
            path.write_text(
                json.dumps(
                    {
                        "client_id": "COLE_AQUI_O_APPLICATION_CLIENT_ID",
                        "tenant_id": "COLE_AQUI_O_DIRECTORY_TENANT_ID",
                        "shared_mailboxes": [],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(load_graph_config(path), EMBEDDED_GRAPH_CONFIG)

    def test_valid_local_config_can_override_embedded_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "graph_config.json"
            local = {"client_id": "local-client", "tenant_id": "local-tenant", "shared_mailboxes": []}
            path.write_text(json.dumps(local), encoding="utf-8")
            self.assertEqual(load_graph_config(path), local)

    def test_graph_received_time_is_converted_to_local_naive_datetime(self) -> None:
        converted = GraphEmailSource._received_at("2026-09-18T12:00:00Z")
        expected = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
        self.assertEqual(converted, expected)

    def test_graph_folder_path_round_trip(self) -> None:
        path = GraphEmailSource._folder_path("shared@example.com", "A+/= folder")
        self.assertEqual(GraphEmailSource._parse_folder_path(path), ("shared@example.com", "A+/= folder"))


if __name__ == "__main__":
    unittest.main()
