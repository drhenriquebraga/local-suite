import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "app"), str(RAIZ / "build")]
import configurar_ambiente as cfg
import pesos_ct_offline
import radai_tasks as tasks
import requisitos


def checkpoint(pesos, mm, plano="nnUNetPlans"):
    labels = {'background': 0, 'liver': 1}
    if mm == 1.5:
        pasta = pesos / 'Dataset299_body_1559subj'
        treino = pasta / 'nnUNetTrainer__nnUNetPlans__3d_fullres'
        labels = {'background': 0, 'body_trunc': 1, 'body_extremities': 2}
    else:
        dataset = tasks.DATASETS_RESOLUCAO_CT[mm]
        pasta = pesos / ("Dataset%d_TotalSegmentator_total_%dmm_1559subj" % (dataset, mm))
        treino = pasta / ("nnUNetTrainer_4000epochs_NoMirroring__%s__3d_fullres" % plano)
    fold = treino / "fold_0"
    fold.mkdir(parents=True)
    (treino / "plans.json").write_text(json.dumps({
        "dataset_name": pasta.name, "configurations": {"3d_fullres": {"spacing": [mm] * 3}}}))
    (treino / "dataset.json").write_text(json.dumps({'labels': labels}))
    peso = fold / "checkpoint_final.pth"
    with zipfile.ZipFile(peso, "w") as z:
        z.writestr("checkpoint/data.pkl", b"mock")
        z.writestr("checkpoint/data/0", b"mock")
    return peso


class ResolucaoCT(unittest.TestCase):
    def test_selecao_que_viaja_no_bundle(self):
        self.assertEqual([831, 832, 833, 834, 835, 300, 836, 837, 299], tasks.datasets_do_pacote(["total_v3"]))
        self.assertEqual([850, 851], tasks.datasets_do_pacote(["total_mr"]))
        self.assertEqual([291, 292, 293, 294, 295, 300, 299], tasks.datasets_do_pacote(["total_v2"]))
        self.assertNotIn(836, tasks.datasets_necessarios("total_v3"))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for nome in ("Dataset299_body_1559subj", "Dataset300_body_6mm_1559subj"):
                pasta = base / "ts_weights" / nome
                pasta.mkdir(parents=True)
                (pasta / "exemplo").touch()
            with patch.object(cfg, "_previas_publicadas", return_value=set()):
                self.assertEqual(["Dataset299_body_1559subj", "Dataset300_body_6mm_1559subj"],
                                 [p.parent.name for p in cfg._arquivos_do_bundle(base)])

    def test_exige_o_checkpoint_do_plano_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            pesos = Path(tmp)
            outro = checkpoint(pesos, 3, "nnUNetResEncUNetLPlans_8")
            self.assertFalse(cfg._peso_completo(outro.parents[2]))
            with self.assertRaisesRegex(RuntimeError, "Dataset836"):
                tasks.exigir_peso_resolucao_ct(3, pesos)
            correto = checkpoint(pesos, 3)
            self.assertTrue(cfg._peso_completo(correto.parents[2]))
            self.assertEqual(tasks.exigir_peso_resolucao_ct(3, pesos), 836)
            planos = correto.parents[1] / "plans.json"
            original = planos.read_text()
            planos.write_text(original.replace("[3, 3, 3]", "[6, 6, 6]"))
            self.assertFalse(cfg._peso_completo(correto.parents[2]))
            planos.write_text(original)
            correto.write_bytes(correto.read_bytes()[:25])
            self.assertFalse(cfg._peso_completo(correto.parents[2]))
            self.assertEqual(tasks.exigir_peso_resolucao_ct(3, pesos, "small"), 836)

    def test_atualizacao_antiga_precisa_dos_pesos_fisicos(self):
        pacote = requisitos.calcular(str(RAIZ))
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            recibo = pasta / "_requisitos.json"
            for fingerprint in (pacote["impressao"], pacote["base_sem_perfis_ct"]):
                recibo.write_text(json.dumps(dict(pacote, impressao=fingerprint)))
                self.assertFalse(requisitos.comparar_estacao(str(RAIZ), tmp)[0])
            checkpoint(pasta / "ts_weights", 6)
            self.assertFalse(requisitos.comparar_estacao(str(RAIZ), tmp)[0])
            checkpoint(pasta / "ts_weights", 3)
            self.assertFalse(requisitos.comparar_estacao(str(RAIZ), tmp)[0])
            checkpoint(pasta / 'ts_weights', 1.5)
            self.assertTrue(requisitos.comparar_estacao(str(RAIZ), tmp)[0])
            recibo.write_text(json.dumps(dict(pacote, impressao="incompativel")))
            self.assertFalse(requisitos.comparar_estacao(str(RAIZ), tmp)[0])

    def test_v2_de_contingencia_usa_so_body_ultra_e_nao_as_redes_v3(self):
        pacote = requisitos.calcular(str(RAIZ))
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / '_requisitos.json').write_text(json.dumps(dict(pacote, impressao=pacote['base_sem_perfis_ct'])))
            for ident in range(291, 296):
                (pasta / 'ts_weights' / f'Dataset{ident}_modelo').mkdir(parents=True)
            self.assertFalse(requisitos.comparar_estacao(str(RAIZ),tmp)[0])
            checkpoint(pasta / 'ts_weights', 1.5)
            self.assertTrue(requisitos.comparar_estacao(str(RAIZ),tmp)[0])

    def test_suplemento_recusa_arquivo_alterado(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            mm, nome, _ = next(pesos_ct_offline.origens())
            (pasta / nome).write_bytes(b"arquivo incorreto")
            with self.assertRaises(ValueError):
                pesos_ct_offline.importar(pasta, pasta / "destino")
            self.assertEqual([], list((pasta / "destino").iterdir()))

    def test_runner_envia_o_mapa_299_para_o_predictor_principal(self):
        import radai_ts_runner as runner
        from totalsegmentator.map_tasks_config import TASK_CONFIGS
        for interno, nativo, ids in [('total_v3','total_v3',[831,832,833,834,835]),
                                     ('total_v2','total',[291,292,293,294,295])]:
            self.assertEqual(tasks.nome_na_biblioteca(interno),nativo)
            self.assertEqual(TASK_CONFIGS[nativo]['sub_modes']['default']['task_id'],ids)
            runner._validar_argv_body_ultra(['--task',nativo,'--body_seg'])
            runner._validar_argv_body_ultra(['-ta='+nativo,'--body_seg'])
        with self.assertRaises(ValueError):
            runner._validar_argv_body_ultra(['--task','total_mr','--body_seg'])
        saida = object()
        chamadas = []
        def predict(file_in, file_out, task_id, task_name, resample, trainer, save_binary, crop=None):
            chamadas.append((task_id, resample, save_binary, crop))
            return saida
        downloads = []
        mod = SimpleNamespace(nnUNet_predict_image=predict)
        api = SimpleNamespace(download_pretrained_weights=downloads.append)
        with runner._body_ultra(mod, api) as usado:
            api.download_pretrained_weights(300)
            mapa = mod.nnUNet_predict_image('ct', None, 300, 'body', 6, 'nnUNetTrainer', True)
            api.download_pretrained_weights(831)
            mod.nnUNet_predict_image('ct', 'resultado', 831, 'total', 1.5, 'outra_rede', False, crop=mapa)
            self.assertTrue(usado)
        self.assertEqual(downloads, [299, 831])
        self.assertEqual(chamadas, [(299, 1.5, True, None), (831, 1.5, False, saida)])
        self.assertIs(mod.nnUNet_predict_image, predict)

    def test_recorte_do_ultra_independe_da_chave_e_do_cache_antigo(self):
        import engine
        import radai_cache_tasks as cache
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', TOTALSEG_WEIGHTS_PATH=tmp):
            amb = {'TOTALSEG_WEIGHTS_PATH': tmp}
            with self.assertRaisesRegex(RuntimeError,'Dataset299'):
                engine._recorte_no_corpo('total_v3', False, amb, body_ultra=True)
            checkpoint(Path(tmp), 1.5)
            decisao = engine._recorte_no_corpo('total_v3', False, amb, body_ultra=True)
            self.assertEqual((decisao['dataset'], decisao['flag']), (299, True))
            self.assertFalse(engine._recorte_no_corpo('total_v3',False,amb)['flag'])
            with self.assertRaises(ValueError):
                engine._recorte_no_corpo('total_mr',False,amb,body_ultra=True)
            padrao = cache.receita('total_v3', recorte_no_corpo=True)
            ultra = cache.receita('total_v3', recorte_no_corpo=True, body_ultra=True)
            self.assertEqual(ultra['body_dataset'], 299)
            self.assertNotEqual(ultra['pesos'], padrao['pesos'])
            self.assertNotEqual(cache.chave('caso','total_v3',padrao),cache.chave('caso','total_v3',ultra))


if __name__ == "__main__":
    unittest.main()
