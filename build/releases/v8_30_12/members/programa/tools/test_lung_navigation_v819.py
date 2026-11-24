from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = Path(os.environ.get('LOCAL_SUITE_TEST_SOURCE', ROOT.parent / 'AUTO_CONTORNO'))
sys.path[:0] = [str(ROOT / 'app'), str(HOST / 'app')]
from fastapi import FastAPI
import radai_lung_screen as L


class LungNavigation(unittest.TestCase):
    def test_four_d_uses_common_header_without_duplicate_backlink(self):
        app = FastAPI()
        L.montar(app, {})
        page = next(route.endpoint for route in app.routes if route.path == '/lung/4d')()
        self.assertNotIn('<a href="/lung">← LUNG RT</a>', page)
        self.assertIn('4D CT &amp; ITV', page)
        self.assertIn('class="ui-ic"', page)

    def test_single_nodule_uses_common_header_and_protocol_chooser(self):
        app = FastAPI()
        L.montar(app, {})
        page = next(route.endpoint for route in app.routes if route.path == '/lung/nodulos')()
        self.assertNotIn('<a href="/lung">← LUNG RT</a>', page)
        self.assertIn('Contorno de Nódulo Pulmonar', page)
        self.assertIn('id="protocolo"', page)
        self.assertIn('id="effort-modal"', page)


if __name__ == '__main__':
    unittest.main(verbosity=2)
