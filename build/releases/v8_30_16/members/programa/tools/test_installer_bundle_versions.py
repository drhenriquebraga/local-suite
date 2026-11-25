"""Check that the setup cover describes the plugin code included in the ZIP."""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

PROGRAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM / "build"))
import empacotar_instalador as pack


class InstallerBundleVersions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((PROGRAM / "packager/plugin-options.json").read_bytes())
        cls.seeds = (PROGRAM / "app/radai_plugin_seeds.py").read_bytes()

    def validate(self, catalog):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("programa/packager/plugin-options.json", json.dumps(catalog))
            archive.writestr("programa/app/radai_plugin_seeds.py", self.seeds)
        with zipfile.ZipFile(buffer) as archive:
            pack.conferir_versoes_da_capa(archive)

    def test_catalog_and_shipped_seeds_match(self):
        self.validate(self.catalog)

    def test_incorrect_code_or_bundle_label_prevents_release(self):
        for plugin in ("lung-rt", "neuro-rt"):
            for field in ("code_version", "minimum_offline_bundle_version"):
                with self.subTest(plugin=plugin, field=field):
                    bad = deepcopy(self.catalog)
                    bad["plugins"][plugin][field] = "0.0.0"
                    with self.assertRaisesRegex(ValueError, plugin):
                        self.validate(bad)


if __name__ == "__main__":
    unittest.main()
