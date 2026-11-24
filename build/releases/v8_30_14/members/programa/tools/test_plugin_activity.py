"""Plugin events through the station log, offline and without loading model weights."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))


class PluginActivity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.env = patch.dict(os.environ, RADAI_CONFIG=str(Path(cls.directory.name) / 'fixture.config'),
            RADAI_CALIB_DIR=cls.directory.name, RADAI_FILA_DIR=cls.directory.name,
            RADAI_REGISTRO_DIR=cls.directory.name, RADAI_TMP=cls.directory.name)
        cls.env.start()
        import radai_watcher, radai_queue_state, radai_todo
        cls.w, cls.q, cls.ui = radai_watcher, radai_queue_state, radai_todo

    @classmethod
    def tearDownClass(cls):
        if cls.w._LOG_FH and Path(cls.w._LOG_FH.name).parent == Path(cls.directory.name):
            cls.w._LOG_FH.close()
            cls.w._LOG_FH = None
            cls.w._LOG_TENTADO = False
        cls.env.stop()
        cls.directory.cleanup()

    def setUp(self):
        self.old_console = self.w._CONSOLE.copy()
        self.old_fh = self.w._LOG_FH, self.w._LOG_TENTADO
        self.console, self.file = io.StringIO(), io.StringIO()
        self.w._CONSOLE.update(saida=self.console, ate_o_painel=False)
        self.w._LOG_FH, self.w._LOG_TENTADO = self.file, True
        self.q.limpar()
        self.q.ligar_ganchos(log_plugin=self.w.wlog)
        self.cursor = self.w.LOGSEQ[0]

    def tearDown(self):
        self.w._CONSOLE.update(self.old_console)
        self.w._LOG_FH, self.w._LOG_TENTADO = self.old_fh
        self.q.ligar_ganchos(log_plugin=None)

    def entries(self):
        rows, _, _ = self.ui._fatia_do_log(self.cursor)
        return rows

    def test_neuro_events_are_private_idempotent_and_match_console_file_and_sidebar(self):
        q = self.q
        mid = 'anatomy_synthseg'
        def enqueue():
            return q.enqueue_neuro('a' * 64, 'b' * 64, model_ids=[mid, 'PRIVATE_LABEL'])
        card = enqueue()['id']
        self.assertEqual(enqueue()['id'], card)
        self.assertTrue(q.try_neuro_turn(card))
        q.report_neuro(card, {'stage': 'preparing'})
        def report(state, **extra):
            q.report_neuro(card, {'stage': 'running', 'model': {'id': mid, 'status': state, **extra},
                                  'path': 'C:/PRIVATE_SERIES', 'patient': 'PRIVATE_NAME'})
        report('preparing')
        report('running', fraction=.12)
        report('running', fraction=.13)
        report('completed', roi_count=10)
        report('completed', roi_count=10)
        q.report_neuro(card, {'stage': 'exporting'})
        q.report_neuro(card, {'stage': 'visualizing'})
        self.assertTrue(q.finish_neuro(card, 'completed'))
        self.assertFalse(q.finish_neuro(card, 'completed'))
        rows = self.entries()
        self.assertEqual(len(rows), 9, rows)
        self.assertEqual(rows[4]['txt'], '[NEURO RT] SynthSeg · segmentando.')
        self.assertIn('10', rows[5]['txt'])
        self.assertEqual([row['nivel'] for row in rows], ['atividade']*5 + ['ok','atividade','atividade','ok'])
        self.assertEqual(self.file.getvalue(), self.console.getvalue())
        for row in rows:
            self.assertIn(row['txt'], self.file.getvalue())
        self.assertNotIn('PRIVATE', self.file.getvalue())
        self.assertNotIn('%', self.file.getvalue())

    def test_empty_failure_and_queued_cancellation(self):
        for i, (outcome, level) in enumerate((('empty','aviso'), ('failed','erro'), ('cancelled','atividade'))):
            card = self.q.enqueue_neuro(str(i) * 64, 'f' * 64)['id']
            if outcome == 'cancelled':
                self.assertTrue(self.q.cancel_neuro(card))
            else:
                self.assertTrue(self.q.try_neuro_turn(card))
                self.assertTrue(self.q.finish_neuro(card, outcome))
                self.assertEqual(self.q.para_tela(self.q.cards())[0]['neuro_desfecho'], outcome)
            self.assertEqual(self.entries()[-1]['nivel'], level)

    def test_lung_manual_and_screening_stages(self):
        import radai_lung_screen as lung
        series = {'series':[{'uid':'PRIVATE_UID'}], 'protocolo':'nodulos'}
        with patch.object(lung.L, 'rodar_nodulos', return_value=False):
            lung._trabalho('uma', series, {'log':self.w.wlog})
        self.assertEqual([r['nivel'] for r in self.entries()], ['atividade','atividade','aviso'])
        self.q.rastreio_status('watching')
        self.q.rastreio_status('watching')
        self.q.rastreio_status('waiting')
        self.q.rastreio_status('segmenting')
        self.q.rastreio_status('watching', 1, 1)
        self.q.rastreio_status('stopped')
        self.q.rastreio_status('stopped')
        self.assertEqual(len(self.entries()), 8)
        self.assertIn('1 TC processadas · 1 com achados', self.entries()[-2]['txt'])
        self.assertNotIn('PRIVATE', self.file.getvalue())

    def test_browser_pulses_collapsed_then_acknowledges_log(self):
        from playwright.sync_api import sync_playwright
        import radai_ui
        html = radai_ui.aplicar('<!doctype html><html><head><meta charset="utf-8">'
            '</head><body>' + self.ui.barra() + self.ui._resto() + '</body></html>')
        def route(req):
            url = urlparse(req.request.url)
            if url.path == '/':
                req.fulfill(content_type='text/html; charset=utf-8', body=html)
            elif url.path == '/api/log':
                cursor = int(parse_qs(url.query).get('desde', ['0'])[0])
                rows, end, state = self.ui._fatia_do_log(self.cursor + cursor)
                req.fulfill(content_type='application/json', body=json.dumps(dict(linhas=rows, proximo=end-self.cursor, estado=state)))
            else:
                req.fulfill(content_type='application/json', body='{}')
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE'), timeout=15000)
            try:
                page = browser.new_page()
                page.route('**/*', route)
                page.goto('http://fixture.test/', timeout=10000)
                page.wait_for_function('window.RADAI_TF_LOG_PRIMEIRA === false', timeout=10000)
                page.evaluate("document.documentElement.classList.add('dir-recolhida')")
                card = self.q.enqueue_neuro('d' * 64, 'e' * 64, model_ids=['anatomy_synthseg'])
                page.wait_for_selector('#radai_tf_ic_log .ui-ponto', state='attached', timeout=9000)
                self.assertEqual(page.locator('#radai_tf_ic_log').get_attribute('aria-label'), 'Log — atividade nova')
                self.assertIn('SynthSeg', page.locator('#radai_tf_log').text_content())
                page.evaluate("radaiTfAbrirAba('log', true)")
                self.assertEqual(page.locator('#radai_tf_ic_log .ui-ponto').count(), 0)
                self.q.cancel_neuro(card['id'])
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
