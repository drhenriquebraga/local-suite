from pathlib import Path
import sys
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import radai_plugin_setup_ui as ui
import radai_plugin_setup as setup
import radai_lung_plugin as lung
import radai_queue_state as queue


class PluginOffline(unittest.TestCase):
    def test_feedback_next_to_action_and_zip_only(self):
        for slug in ("neuro", "lung"):
            html = ui.controls(True, plugin=slug)
            self.assertNotIn("Usar uma pasta já extraída", html)
            self.assertNotIn("data-pi-folder ", html)
            self.assertGreater(html.index("data-pi-feedback"), html.index("data-pi-weights-drop"))
            self.assertIn("data-pi-change", html)

    def test_window_failure_prevents_shutdown(self):
        with patch("radai_janela.fechar_para_atualizar", return_value={"ok": False, "pendentes": 1}):
            with self.assertRaises(setup.SetupError):
                setup.close_suite_windows()

    def test_queue_waiting_and_running_are_distinct(self):
        with patch.object(queue, "quem_tem_a_vez", return_value={}), patch.object(queue, "resumo", return_value={"esperando":2}), patch("radai_atualizar.o_que_segura",return_value=None):
            self.assertEqual(lung.install_queue_status(), {"active":False, "pending":2})
        with patch.object(queue, "quem_tem_a_vez", return_value={"dono":"lung"}), patch.object(queue, "resumo", return_value={"rodando":1}):
            self.assertTrue(lung.install_queue_status()["active"])

    def test_coronary_choices_use_same_controls(self):
        import radai_coronarias_ui as cor
        html = cor._coronary()
        for label in ('pi-options','pi-option','pi-drop','ui-envio','cor-file','data-cor-choice'):
            self.assertIn(label, html)

    def test_coronary_upload_size_requires_current_local_consent(self):
        import radai_watcher as watcher
        import radai_plugin_coronarias as policy
        gate = watcher.PortaoDoHost(None, porta=8777)
        scope = {"path":"/api/plugins/coronarias/importar", "method":"POST", "client":("127.0.0.1",1),"scheme":"http"}
        headers = {"host":"127.0.0.1:8777","origin":"http://127.0.0.1:8777","content-type":"application/zip",
                   "x-radai-aceito":"1","x-radai-termos-versao":policy.VERSAO,"x-radai-termos-sha256":policy.IMPRESSAO}
        self.assertEqual(gate._teto_do_pedido(scope,headers),policy.MAX_PACOTE)
        for other in (dict(headers,origin=""),dict(headers,origin="http://outro"),dict(headers,**{"x-radai-aceito":"0"})):
            self.assertEqual(gate._teto_do_pedido(scope,other),gate.teto)
