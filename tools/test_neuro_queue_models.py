import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import radai_queue_state as fila


class NeuroQueueModelsTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix='radai_neuro_fila_')
        self.addCleanup(tmp.cleanup)
        for configuracao in (
            patch.dict(os.environ, {'RADAI_FILA_DIR': tmp.name}),
            patch.object(fila, '_sincroniza', return_value=False),
            patch.object(fila, '_CARDS', []),
            patch.object(fila, '_NEURO_CANCEL', {}),
            patch.object(fila, '_VEZ', dict(fila._VEZ, dono=None, ticket=None)),
            patch.object(fila, '_PERSISTIR', dict(fila._PERSISTIR)),
            patch.object(fila, '_NEURO_PAUSA', False),
            patch.object(fila, '_FECHAR_AO_FIM', {'pedido': False}),
        ):
            configuracao.start()
            self.addCleanup(configuracao.stop)
        fila.carregar()

    def detalhe(self, cid):
        return next(c for c in fila.para_tela(fila.cards()) if c['id'] == cid)['detalhe']

    def test_models_progress_stays_inside_one_card_and_preserves_lease(self):
        self.assertEqual(getattr(fila, 'NEURO_QUEUE_MODELS_API', None), 1)
        ids = ('anatomy_synthseg', 'anatomy_cerebra_ants', 'synthetic_ct_totalsynth',
               'cranio_buti_sct', 'cranio_buti', 'nidus_consensus')
        key, fingerprint = 'a' * 64, 'b' * 64
        cid = fila.enqueue_neuro(key, fingerprint, model_ids=ids)['id']
        self.assertEqual(fila.enqueue_neuro(key, fingerprint)['id'], cid)
        self.assertEqual(fila.resumo()['total'], 1)
        self.assertEqual([m['id'] for m in self.detalhe(cid)['modelos']], list(ids))
        self.assertTrue(all(m['status'] == 'queued' for m in self.detalhe(cid)['modelos']))
        self.assertTrue(fila.try_neuro_turn(cid))
        self.assertTrue(fila.report_neuro(cid, {'stage': 'running', 'model': {
            'id': ids[0], 'status': 'completed', 'roi_count': 32,
            'descricao': 'PRIVATE_NAME', 'error': 'C:/PRIVATE_EXAM'}}))
        fila.report_neuro(cid, {'stage': 'running', 'model': {
            'id': ids[1], 'status': 'running', 'fraction': 0.3}})
        fila.report_neuro(cid, {'stage': 'running', 'model': {
            'id': ids[0], 'status': 'preparing', 'fraction': 0.1}})
        fila.report_neuro(cid, {'stage': 'running', 'model': {
            'id': 'PRIVATE_NAME', 'status': 'completed'}})
        modelos = self.detalhe(cid)['modelos']
        self.assertEqual(modelos[0]['status'], 'completed')
        self.assertEqual(modelos[0]['roi_count'], 32)
        self.assertEqual(modelos[1]['fraction'], 0.3)
        self.assertTrue(all(m['rotulo'] and m['descricao'] for m in modelos))
        publico = json.dumps(fila.para_tela(fila.cards()))
        for dado in (key, fingerprint, 'PRIVATE_NAME', 'PRIVATE_EXAM'):
            self.assertNotIn(dado, publico)
        self.assertEqual(fila.quem_tem_a_vez()['dono'], 'neuro')
        self.assertTrue(fila.cancel_neuro(cid))
        self.assertEqual(fila.quem_tem_a_vez()['dono'], 'neuro')
        self.assertTrue(fila.finish_neuro(cid, 'cancelled'))
        self.assertEqual([m['status'] for m in self.detalhe(cid)['modelos']],
                         ['completed'] + ['cancelled'] * (len(ids) - 1))
        self.assertIsNone(fila.quem_tem_a_vez()['dono'])

    def test_restart_preserves_only_sanitized_models_and_marks_remaining(self):
        ids = ('anatomy_synthseg', 'anatomy_cerebra_ants', 'cranio_buti')
        cid = fila.enqueue_neuro('a' * 64, 'b' * 64, model_ids=ids)['id']
        self.assertTrue(fila.try_neuro_turn(cid))
        fila.report_neuro(cid, {'model': {'id': ids[0], 'status': 'empty', 'roi_count': 0}})
        fila.report_neuro(cid, {'model': {'id': ids[1], 'status': 'running',
                                        'fraction': float('nan'), 'roi_count': True,
                                        'path': 'C:/PRIVATE_EXAM'}})
        dados = Path(fila.arquivo_da_fila()).read_text(encoding='utf-8')
        self.assertNotIn('PRIVATE_EXAM', dados)
        self.assertNotIn('NaN', dados)
        fila._CARDS.clear()
        fila._VEZ.update(dono=None, ticket=None)
        fila.carregar()
        card = fila.cartao(cid)
        self.assertEqual(card['estado'], 'falhou')
        self.assertEqual(card['rotulo'], 'NEURO RT')
        modelos = self.detalhe(cid)['modelos']
        self.assertEqual([m['status'] for m in modelos], ['empty', 'interrupted', 'not_run'])
        self.assertEqual(modelos[0]['roi_count'], 0)
        self.assertNotIn('fraction', modelos[1])
        self.assertNotIn('roi_count', modelos[1])

    def test_graceful_shutdown_persists_interrupted_model_states(self):
        ids = ('MRI_GBM', 'MRI_Meningioma')
        cid = fila.enqueue_neuro('a' * 64, 'b' * 64, model_ids=ids)['id']
        self.assertTrue(fila.try_neuro_turn(cid))
        fila.report_neuro(cid, {'model': {'id': ids[0], 'status': 'running'}})
        self.assertTrue(fila.ao_fechar())
        fila._CARDS.clear()
        fila._VEZ.update(dono=None, ticket=None)
        fila.carregar()
        self.assertEqual([(m['id'], m['status']) for m in self.detalhe(cid)['modelos']],
                         [('MRI_GBM', 'interrupted'), ('MRI_Meningioma', 'not_run')])

    def test_legacy_and_unknown_models_do_not_break_submission(self):
        legado = fila.enqueue_neuro('a' * 64, 'b' * 64)['id']
        self.assertNotIn('modelos', self.detalhe(legado))
        cid = fila.enqueue_neuro('c' * 64, 'd' * 64, model_ids=(
            'unknown', 'anatomy_synthseg', 'anatomy_synthseg'))['id']
        self.assertTrue(fila.cancel_neuro(cid))
        self.assertEqual([(m['id'], m['status']) for m in self.detalhe(cid)['modelos']],
                         [('anatomy_synthseg', 'cancelled')])


if __name__ == '__main__':
    unittest.main()
