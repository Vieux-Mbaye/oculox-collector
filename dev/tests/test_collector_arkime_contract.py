#!/usr/bin/env python3

"""Regression tests for Collector Arkime reachback and shared secrets."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_configurator():
    path = ROOT / "dev/scripts/configure-collector-arkime.py"
    spec = importlib.util.spec_from_file_location("configure_collector_arkime", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


CONFIGURATOR = load_configurator()


class CollectorArkimeTests(unittest.TestCase):
    def make_tree(self, root: Path, live: bool, host: str = "") -> Path:
        bundle = root / "bundle"
        config = root / "project/config"
        bundle.mkdir(parents=True)
        config.mkdir(parents=True)
        (bundle / "arkime-viewer.env").write_text(
            "ARKIME_PASSWORD_SECRET=shared-secret-at-least-16\n", encoding="utf-8"
        )
        (config / "arkime-secret.env").write_text(
            "MAXMIND_GEOIP_DB_ACCOUNT_ID=0\nARKIME_PASSWORD_SECRET=temporary\n",
            encoding="utf-8",
        )
        (config / "arkime-live.env").write_text(
            f"ARKIME_LIVE_CAPTURE={'true' if live else 'false'}\n"
            f"ARKIME_LIVE_NODE_HOST={host}\n",
            encoding="utf-8",
        )
        return bundle

    def test_imports_shared_secret_and_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self.make_tree(root, True, "collector.example.test")
            enabled, host = CONFIGURATOR.configure(bundle, root / "project")
            values = CONFIGURATOR.read_env(root / "project/config/arkime-secret.env")
            self.assertTrue(enabled)
            self.assertEqual("collector.example.test", host)
            self.assertEqual("shared-secret-at-least-16", values["ARKIME_PASSWORD_SECRET"])
            self.assertEqual("0", values["MAXMIND_GEOIP_DB_ACCOUNT_ID"])

    def test_live_capture_requires_reachable_node_host(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self.make_tree(root, True)
            with self.assertRaises(SystemExit):
                CONFIGURATOR.configure(bundle, root / "project")
            values = CONFIGURATOR.read_env(root / "project/config/arkime-secret.env")
            self.assertEqual("temporary", values["ARKIME_PASSWORD_SECRET"])

    def test_disabled_live_capture_accepts_empty_node_host(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self.make_tree(root, False)
            enabled, host = CONFIGURATOR.configure(bundle, root / "project")
            self.assertFalse(enabled)
            self.assertEqual("", host)

    def test_reachback_uses_host_network_without_port_mapping(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
        overlay = (ROOT / "dev/compose/docker-compose.dev.yml").read_text(encoding="utf-8")
        self.assertEqual("host", compose["services"]["arkime-live"]["network_mode"])
        arkime_live_overlay = overlay.split("  arkime-live:\n", 1)[1].split("\n  dashboards:", 1)[0]
        self.assertNotIn("ports:", arkime_live_overlay)


if __name__ == "__main__":
    unittest.main()
