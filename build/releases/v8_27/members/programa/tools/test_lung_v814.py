import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
_PROFILE = tempfile.TemporaryDirectory(prefix='radai_lung_test_profile_')
for _key in ('LOCALAPPDATA', 'APPDATA', 'RADAI_TMP', 'RADAI_CALIB_DIR', 'RADAI_REGISTRO_DIR'):
    os.environ[_key] = str(Path(_PROFILE.name) / _key)
    Path(os.environ[_key]).mkdir()
os.environ.update(RADAI_URL_VERSOES='0', RADAI_NOTIFICACAO='0')
sys.path[:0] = [str(ROOT / 'app'), str(ROOT.parent / 'AUTO_CONTORNO' / 'tools')]
import _componentes
_componentes.ligar_caminho()
import numpy as np
import SimpleITK as sitk
import radai_lung as L


class Lung814(unittest.TestCase):
    def test_vigia_nodules_default_choice_and_restart_requires_start(self):
        import ast
        import radai_queue_state as Q
        import radai_topography as T
        import radai_batch as B
        tree = ast.parse((ROOT / 'app' / 'radai_watcher.py').read_text(encoding='utf-8'))
        names = {'_tasks_pela_anatomia', '_ligar_a_fila_da_estacao'}
        selected = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
        ns = {'STATE': {'overnight': False}, 'TURNO_TEMPORARIO': {}, 'wlog': lambda *a: None,
              'tasks_pela_modalidade': lambda tasks, *a, **kw: tasks,
              'soltar_trava_morta': lambda *a: None, 'serie_da_varredura': lambda *a: (None, None)}
        exec(compile(selected, str(ROOT / 'app' / 'radai_watcher.py'), 'exec'), ns)
        ref = sitk.Image([4, 4, 4], sitk.sitkInt16)
        anatomy = {'regioes': ['torax'], 'laudo': [], 'coracao_cm3': 0}
        ns['lung_instalado_para_turno'] = lambda: True
        with patch.object(T, 'anatomia_da_base', return_value=anatomy), patch.object(T, 'tasks_da_anatomia', return_value=([], [], 'synthetic')):
            fn = ns['_tasks_pela_anatomia']
            argumentos = (Mock(TASKS_DE_ACHADO=set()), {}, {}, ref)
            self.assertNotIn('lung_nodules', fn(*argumentos, {'modalidade':'CT'}, []))
            ns['STATE']['overnight'] = True
            self.assertNotIn('lung_nodules', fn(*argumentos, {'modalidade':'CT', 'vigia_nodulos':False}, []))
            self.assertIn('lung_nodules', fn(*argumentos, {'modalidade':'CT', 'vigia_nodulos':True}, []))
            ns['lung_instalado_para_turno'] = lambda: False
            self.assertNotIn('lung_nodules', fn(*argumentos, {'modalidade':'CT', 'vigia_nodulos':True}, []))
        Q.overnight(True, temporarios={'LUNG_NODULES':'0'})
        Q.autorizar_turno()
        self.assertTrue(next(c for c in Q.cards() if c['tipo'] == 'overnight')['iniciar_pedido'])
        with patch.object(Q, 'carregar', return_value={}), patch.object(B, 'armar_relogio_do_complemento'):
            ns['_ligar_a_fila_da_estacao']()
        self.assertFalse(next(c for c in Q.cards() if c['tipo'] == 'overnight')['iniciar_pedido'])
        self.assertEqual(Q.config_do_turno()['temporarios']['LUNG_NODULES'], '0')
        Q.overnight(False)

    def test_vigia_ui_sends_the_explicit_nodule_choice_to_queue(self):
        import json
        import shutil
        import subprocess
        import radai_batch as B
        node = shutil.which('node')
        self.assertIsNotNone(node)
        def fonte(nome):
            inicio = 'function ' + nome + '('
            return inicio + B.JS_VIGIA.split(inicio, 1)[1].split('\nfunction ', 1)[0]
        program = """
let NIGHT_ON=false, chave=null;
function _ovQ(sel){return sel==='#ov_lung'?chave:null}
const document={querySelectorAll:()=>[]};
function filaEstadoPintar(){}
function fetch(url,o){console.log(o.body);return Promise.resolve({json:()=>Promise.resolve({})})}
""" + '\n'.join(fonte(n) for n in ('_ovValores','_ovValorLung','filaOvernight')) + """
for(chave of [null,{disabled:true,checked:true},{disabled:false,checked:false},{disabled:false,checked:true}]){
 filaOvernight(true,_ovValores());
}
"""
        result = subprocess.run([node, '-e', program], text=True, capture_output=True, check=True)
        escolhas = [json.loads(linha)['temporarios']['LUNG_NODULES'] for linha in result.stdout.splitlines()]
        self.assertEqual(escolhas, ['0','0','0','1'])
        from html.parser import HTMLParser
        class Campo(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == 'input' and dict(attrs).get('id') == 'ov_lung':
                    self.chave = dict(attrs)
        campo = Campo()
        campo.feed(B._corpo_da_folha_do_turno())
        self.assertIn('disabled', campo.chave)
        self.assertNotIn('checked', campo.chave)

    def test_mr_full_study_actual_rtstruct_and_custom_union(self):
        import engine
        import pydicom
        import make_test_series
        import radai_output as O
        from datetime import datetime
        with tempfile.TemporaryDirectory() as folder:
            serie = Path(folder) / 'MR'
            make_test_series.escreve_serie(str(serie), 'SYNTHETIC-MR', datetime(2026, 11, 8), 12)
            for file in serie.glob('*.dcm'):
                ds = pydicom.dcmread(file)
                ds.Modality = 'MR'
                ds.SOPClassUID = pydicom.uid.MRImageStorage
                ds.file_meta.MediaStorageSOPClassUID = pydicom.uid.MRImageStorage
                ds.save_as(file, enforce_file_format=True)
            def box(z, y, x):
                a = np.zeros((12, 128, 128), bool)
                a[z:z+4, y:y+12, x:x+12] = True
                return a
            raw = {'total_mr': {'liver': box(4, 40, 40), 'iliopsoas_left': box(3, 70, 70)},
                   'liver_segments_mr': {'liver_segment_1': box(4, 40, 40)},
                   'liver_lesions_mr': {'liver_lesions': box(5, 43, 43)}}
            out = Path(folder) / 'output'
            out.mkdir()
            sd = O.Saida(engine, str(serie), str(out), 'RS_RadAI_SYNTHETIC.dcm',
                         tasks=list(raw), versao='synthetic', modalidade='MR', suavizar_mm=0)
            sd.full_e_oar(raw, protocolo={'modalidade':'MR', 'estruturas':['liver', 'iliopsoas_left'],
                                          'merges':[{'nome':'CustomUnion','de':['liver','iliopsoas_left']}]})
            files = list(out.glob('*.dcm'))
            full = pydicom.dcmread(next(p for p in files if 'FULL_' in p.name))
            study = pydicom.dcmread(next(p for p in files if 'FULL_' not in p.name))
            names_full = {str(r.ROIName) for r in full.StructureSetROISequence}
            names_study = {str(r.ROIName) for r in study.StructureSetROISequence}
            self.assertTrue(any('Iliops' in n for n in names_full), names_full)
            self.assertFalse(any('Iliops' in n for n in names_study), names_study)
            for name in ('liver_seg', 'liver_lesions'):
                self.assertTrue(any(n.startswith(name) for n in names_full), names_full)
                self.assertTrue(any(n.startswith(name) for n in names_study), names_study)
            self.assertEqual(study.ApprovalStatus, 'UNAPPROVED')

    def test_receipt_copy_to_other_station_and_tampering(self):
        import shutil
        import make_test_series
        import radai_lung_receipts as R
        from datetime import datetime
        with tempfile.TemporaryDirectory() as base:
            folder = Path(base) / 'station_a'
            folder.mkdir()
            make_test_series.escreve_serie(str(folder), 'SYNTHETIC', datetime(2026, 11, 8), 12)
            markers = {k: Mock(return_value=True) for k in ('claim', 'renovar', 'unclaim')}
            markers['lock_e_meu'] = Mock(return_value=(True, 'synthetic'))
            cfg = {'min_cortes': 5, 'marcadores': markers}
            s = L.varrer(str(folder), cfg)[0]
            mask = np.zeros((12, 128, 128), bool)
            mask[4:7, 40:45, 40:45] = True
            with patch.object(L, 'inferir', return_value=mask):
                receipt = L.processar_serie(s, cfg)
            copied = Path(base) / 'station_b'
            shutil.copytree(folder, copied)
            for n, p in enumerate(copied.glob('CT*.dcm')):
                p.rename(p.with_name('renamed_%d.dcm' % n))
            other = L.varrer(str(copied), cfg)[0]
            received = []
            with patch.object(L, 'inferir', side_effect=AssertionError('must reuse')):
                r = L.processar_serie(other, dict(cfg, receber_resultado=lambda ref, m, lungs: received.append(m)))
            self.assertTrue(r['reutilizado'])
            np.testing.assert_array_equal(received[0], mask)
            output = copied / receipt['outputs'][0]['name']
            output.write_bytes(output.read_bytes() + b'tamper')
            self.assertIsNone(R.ler(other, receipt['assinatura']))

    def test_export_individual_itvs_with_gap_is_unapproved_and_referenced(self):
        import pydicom
        import make_test_series
        import radai_lung_4d as F
        from datetime import datetime
        with tempfile.TemporaryDirectory() as folder:
            make_test_series.escreve_serie(folder, 'SYNTHETIC', datetime(2026, 11, 8), 12)
            markers = {k: Mock(return_value=True) for k in ('claim', 'renovar', 'unclaim')}
            markers['lock_e_meu'] = Mock(return_value=(True, 'synthetic'))
            cfg = {'min_cortes': 5, 'marcadores': markers}
            s = L.varrer(folder, cfg)[0]
            with L.abrir_serie(s) as (_, ref, signature):
                a = np.zeros((12, 128, 128), bool)
                a[4:7, 30:35, 30:35] = True
                a[4:7, 70:75, 70:75] = True
                masks, curves = F.associar([a, None, np.roll(a, 1, axis=2)], ref)
            L.exportar(s, signature, masks, cfg, curves)
            path = next(Path(folder).glob('RS_RadAI_ITV4D_*.dcm'))
            ds = pydicom.dcmread(path)
            self.assertEqual(ds.ApprovalStatus, 'UNAPPROVED')
            names = {str(r.ROIName) for r in ds.StructureSetROISequence}
            self.assertIn('ITV_N001_ai', names)
            self.assertIn('ITV_N002_ai', names)
            refs = ds.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0]
            self.assertEqual(str(refs.SeriesInstanceUID), s['uid'])
            notes = [str(getattr(o, 'ROIObservationDescription', '')) for o in ds.RTROIObservationsSequence]
            self.assertTrue(any('Lacunas: 1' in n for n in notes), notes)

    def test_phase_and_reference_roles_are_separate_and_frame_is_verified(self):
        import pydicom
        import make_test_series
        from datetime import datetime
        with tempfile.TemporaryDirectory() as folder:
            study, frame = pydicom.uid.generate_uid(), pydicom.uid.generate_uid()
            for phase in ('Respiratory 0%', 'Respiratory 50%', 'AVG'):
                path = Path(folder) / phase.replace('%', '')
                make_test_series.escreve_serie(str(path), 'SYNTHETIC', datetime(2026, 11, 8), 12)
                for file in path.glob('*.dcm'):
                    ds = pydicom.dcmread(file)
                    ds.StudyInstanceUID, ds.FrameOfReferenceUID = study, frame
                    ds.SeriesDescription = phase
                    ds.save_as(file, enforce_file_format=True)
            series = L.varrer(folder, {'min_cortes': 5})
            phases = [s for s in series if s['fase_respiratoria'] is not None]
            avg = next(s for s in series if s['fase_respiratoria'] is None)
            self.assertEqual(len(L.validar_grupo(phases, avg['uid'], avg['uid'], [avg])), 3)
            with self.assertRaises(ValueError):
                L.validar_grupo(series, avg['uid'], avg['uid'])
            new_frame = pydicom.uid.generate_uid()
            for file in Path(avg['pasta']).glob('*.dcm'):
                ds = pydicom.dcmread(file)
                ds.FrameOfReferenceUID = new_frame
                ds.save_as(file, enforce_file_format=True)
            with self.assertRaises(ValueError):
                L.validar_grupo(phases, avg['uid'], avg['uid'], [avg])

    def test_receipt_empty_positive_failure_and_reuse_are_independent_of_anatomy(self):
        import make_test_series
        import radai_lung_receipts as R
        from datetime import datetime
        with tempfile.TemporaryDirectory() as folder:
            make_test_series.escreve_serie(folder, 'SYNTHETIC', datetime(2026, 11, 8), 12)
            markers = {k: Mock(return_value=True) for k in ('claim', 'renovar', 'unclaim')}
            markers['lock_e_meu'] = Mock(return_value=(True, 'synthetic'))
            cfg = {'min_cortes': 5, 'marcadores': markers, 'device': 'cpu'}
            s = L.varrer(folder, cfg)[0]
            with patch.object(L, 'inferir', return_value=None) as infer:
                result = L.processar_serie(s, cfg)
                self.assertEqual(result['estado'], 'vazio')
                self.assertTrue(L.processar_serie(s, cfg)['reutilizado'])
                self.assertEqual(infer.call_count, 1)
            self.assertFalse(any('done' in p.name for p in Path(folder).rglob('*')))
            R.caminho(s).unlink()
            mask = np.zeros((12, 128, 128), bool)
            mask[4:7, 60:65, 60:65] = True
            with patch.object(L, 'inferir', return_value=mask):
                result = L.processar_serie(s, cfg)
            self.assertEqual(result['estado'], 'positivo')
            self.assertEqual(len(result['lesoes']), 1)
            output = Path(folder) / result['outputs'][0]['name']
            self.assertTrue(output.exists())
            original = output.read_bytes()
            R.caminho(s).unlink()
            with patch.object(L, 'inferir', side_effect=RuntimeError('synthetic failure')):
                with self.assertRaises(RuntimeError):
                    L.processar_serie(s, cfg)
            self.assertIsNone(R.ler(s, result['assinatura']))
            self.assertEqual(output.read_bytes(), original)

    def test_mr_liver_gate_and_study_exclusion_in_custom_union(self):
        import radai_modes as M
        import radai_output as O
        import radai_sets as S
        mask = np.ones((2, 2, 2), bool)
        cruas = {'total_mr': {'liver': mask}}
        self.assertEqual(M.complementos_hepaticos_mr(cruas, 'MR'), ('liver_segments_mr', 'liver_lesions_mr'))
        self.assertFalse(M.complementos_hepaticos_mr(cruas, 'MR', 'fast'))
        self.assertFalse(M.complementos_hepaticos_mr({'total_mr': {}}, 'MR'))
        allowed, unions = O.filtro_study_modalidade({'liver', 'iliopsoas_left'},
            [{'nome': 'custom', 'de': ['liver', 'iliopsoas_left', 'iliopsoas_right']}], 'MR')
        self.assertEqual(allowed, {'liver'})
        self.assertEqual(unions[0]['de'], ['liver'])
        for task in M.complementos_hepaticos_mr(cruas, 'MR'):
            self.assertTrue(S.task_do_full(task))

    def test_toracic_tasks_reach_delivery(self):
        import radai_batch as B
        tasks, mode = B.tasks_iniciais({'modo': 'perso', 'modalidade': 'CT',
                                      'protocolos_3d': ['anatomia_toracica']})
        required = {'trunk_cavities', 'breasts', 'pleural_pericard_effusion', 'lung_vessels',
                    'abdominal_muscles', 'vertebrae_body', 'lung_nodules'}
        self.assertTrue(required.issubset(set(tasks)))
        cruas = {task: {'synthetic': np.ones((1, 1, 1), bool)} for task in required}
        self.assertEqual(set(B.cruas_do_entregue(cruas, required)), required)

    def test_individual_itv_and_gaps_and_manual_association(self):
        import radai_lung_4d as F
        ref = sitk.Image([20, 20, 20], sitk.sitkInt16)
        ref.SetSpacing((2, 2, 2))
        a = np.zeros((20, 20, 20), bool)
        a[2:4, 2:4, 2:4] = True
        a[14:16, 14:16, 14:16] = True
        b = np.roll(a, 1, axis=2)
        masks, tracks = F.associar([a, None, b], ref)
        self.assertEqual({k for k in masks if k.startswith('ITV')}, {'ITV_N001', 'ITV_N002'})
        self.assertTrue(all(t['lacunas'] == [1] for t in tracks))
        self.assertTrue(all(t['fases'][1] is None for t in tracks))
        self.assertEqual(tracks[0]['fases'][2]['deslocamento_lps_mm'], [2, 0, 0])
        self.assertEqual(tracks[0]['fases'][2]['volume_mm3'], 64)
        masks, tracks = F.associar([a, None, b], ref, associacoes={'2:1': 'N003'})
        self.assertIn('ITV_N003', masks)

    def test_phase_classifier_excludes_derived_and_contrast(self):
        import radai_lung_4d as F
        self.assertEqual(F.fase_respiratoria({'SeriesDescription': 'Respiratory 40%'}), 40)
        for name in ('AVG 40%', 'MIP 40%', 'conventional', 'CONTRAST 40%'):
            self.assertIsNone(F.fase_respiratoria({'SeriesDescription': name}))

    def test_lock_tuple_false_never_confirms_or_releases_foreign_lock(self):
        markers = {k: Mock(return_value=True) for k in ('claim', 'renovar', 'unclaim')}
        markers['lock_e_meu'] = Mock(return_value=(False, 'outra-estacao'))
        with tempfile.TemporaryDirectory() as folder, patch('radai_archive.conferir_escrita_no_destino'):
            with L._trava_serie({'pasta': folder, 'uid': '1.2.3'}, {'marcadores': markers}) as confirm:
                with self.assertRaises(RuntimeError):
                    confirm()
        markers['unclaim'].assert_not_called()

    def test_valid_ct_without_preamble_and_sidecars(self):
        import pydicom
        import make_test_series
        from datetime import datetime
        with tempfile.TemporaryDirectory() as folder:
            make_test_series.escreve_serie(folder, 'SYNTHETIC', datetime(2026, 11, 8), 12)
            for path in Path(folder).glob('*.dcm'):
                ds = pydicom.dcmread(path)
                ds.preamble = None
                pydicom.dcmwrite(path, ds, enforce_file_format=False)
            (Path(folder) / 'sidecar.json').write_text('{"SeriesInstanceUID":"1.2.3"}')
            (Path(folder) / 'garbage.dcm').write_bytes(b'not a dicom')
            series = L.varrer(folder, {'min_cortes': 5})
            self.assertEqual(len(series), 1)
            files, identity, signature = L._inspecionar(series[0])
            self.assertEqual(len(files), 12)
            self.assertEqual(len(signature), 64)


if __name__ == '__main__':
    unittest.main(verbosity=2)
