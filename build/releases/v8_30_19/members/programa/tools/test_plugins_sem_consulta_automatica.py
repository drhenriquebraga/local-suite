"""Offline regression for plugin status and opt-in version checks."""
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

here = Path(__file__).resolve().parent
# A second source tree can be passed to demonstrate the original behavior.
appdir = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else here.parent / "app"
sys.path.insert(0, str(appdir))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import radai_lung_plugin as lung
import radai_lung_install as lung_sdk
import radai_plugins as neuro
import radai_neuro_install as neuro_sdk
import radai_plugin_bootstrap as bootstrap


class IdleUpdates(unittest.TestCase):
    def test_version_checks_require_an_explicit_action(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                'LOCALAPPDATA': directory, 'APPDATA': directory, 'RADAI_CALIB_DIR': directory,
                'RADAI_REGISTRO_DIR': directory, 'RADAI_FILA_DIR': directory,
            }))
            app = FastAPI()
            version = {"state": "current", "version": "1.2.3"}
            provider = Mock(wraps=neuro_sdk.build_provider(Path(directory), {"version":"8.30.19","python_executable":sys.executable}, {}))
            provider.check_plugin_release.return_value = version
            provider.refresh_plugin_release.return_value = version
            stack.enter_context(patch.object(neuro_sdk, "build_provider", return_value=provider))
            stack.enter_context(patch.object(bootstrap, "ensure_base"))
            stack.enter_context(patch.object(neuro, "discover_plugin", return_value={"state":"absent","active_version":None}))
            stack.enter_context(patch.object(lung, "install_queue_status", return_value={"active":False,"pending":0}))
            check_lung = stack.enter_context(patch.object(lung_sdk, "check_latest", return_value=version))
            options = {"suite_root":directory,"neuro_host_version":"8.30.19"}
            neuro_entry = neuro.montar(app, options)
            lung_entry = lung.montar(app, options)
            with TestClient(app, base_url="http://localhost") as client:
                for entry in (neuro_entry, lung_entry):
                    self.assertTrue(entry["load_complete"].wait(8))
                for name in ("lung", "neuro"):
                    for _ in range(2):
                        response = client.get("/api/plugins/" + name + "-rt")
                        self.assertEqual(response.status_code, 200)
                release_thread = neuro_entry.get("release_thread")
                if release_thread is not None:
                    release_thread.join(1)
                idle_calls = (check_lung.call_count, provider.check_plugin_release.call_count)
                for name, entry in (("lung", lung_entry), ("neuro", neuro_entry)):
                    headers = {"origin":"http://localhost","x-"+name+"-plugin-token":entry["token"]}
                    response = client.post("/api/plugins/"+name+"-rt/refresh", json={}, headers=headers)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), version)
                self.assertEqual(idle_calls, (0, 0), "automatic LUNG, NEURO release checks")
                check_lung.assert_called_once()
                provider.refresh_plugin_release.assert_called_once()


if __name__ == "__main__":
    unittest.main()

