"""Regression tests for AUTO / Customized and the two NEURO entry points."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_batch as batch
import radai_modules as modules

class NavigationAndEffort(unittest.TestCase):
    def test_auto_uses_preference_at_submission(self):
        with patch("radai_velocidade_tc.esforco_atual", return_value="alto"):
            for stale in ({}, {"esforco": "ultra"}):
                auto = batch._congelar_fast(dict(modo="auto", modalidade="CT", **stale))
                self.assertEqual(batch.escolha_da_serie(auto)["esforco"], "alto")
            custom = batch._congelar_fast(dict(modo="perso", modalidade="CT", esforco="extra"))
            self.assertEqual(batch.escolha_da_serie(custom)["esforco"], "extra")
            self.assertEqual(batch._congelar_fast({"modo":"auto","esforco":"ultra"}, legado=True)["esforco"], "ultra")

    def test_effort_only_rendered_in_custom_panel(self):
        self.assertNotIn("data-esforco-auto", batch.PAGINA)
        self.assertIn("seletorAcabamento(i,e)", batch.PAGINA.split("function painelPerso(i)",1)[1])

    def test_processing_and_results_cards(self):
        self.assertEqual({card[0] for card in modules.FERRAMENTAS["neuro"]}, {"neuro_anatomia","nidus"})
        self.assertIn("/recon3d/neuroanatomia", [card[3] for card in modules.FERRAMENTAS["recon3d"]])

if __name__ == "__main__":
    unittest.main()
