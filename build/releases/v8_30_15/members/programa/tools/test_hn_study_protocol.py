"""Synthetic delivery regression; no model inference or patient input."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HOST = Path(os.environ.get('LOCAL_SUITE_TEST_SOURCE', str(ROOT.parent / 'AUTO_CONTORNO')))
sys.path[:0] = [str(ROOT / 'app'), str(HOST / 'app')]
_CONTEXT = tempfile.TemporaryDirectory(prefix='hn-study-config-synthetic-')
for key in ('RADAI_CALIB_DIR', 'RADAI_REGISTRO_DIR', 'TOTALSEG_HOME_DIR'):
    os.environ[key] = str(Path(_CONTEXT.name) / key)

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
import engine as E
import radai_hnlnl as HN
import radai_output as OUTPUT
import radai_sets as SETS


def series(folder, modality='CT'):
    folder.mkdir()
    study, serie, frame = (generate_uid() for _ in range(3))
    for z in range(16):
        meta = Dataset()
        meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        meta.MediaStorageSOPInstanceUID = generate_uid()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        meta.ImplementationClassUID = generate_uid()
        ds = FileDataset(None, {}, file_meta=meta, preamble=b'\0' * 128)
        ds.SOPClassUID, ds.SOPInstanceUID = meta.MediaStorageSOPClassUID, meta.MediaStorageSOPInstanceUID
        ds.Modality = modality
        ds.PatientName, ds.PatientID = 'SYNTHETIC^PHANTOM', 'HN_STUDY_TEST_ONLY'
        ds.PatientBirthDate, ds.PatientSex = '', 'O'
        ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.FrameOfReferenceUID = study, serie, frame
        ds.StudyID, ds.SeriesNumber, ds.InstanceNumber = '1', 1, z + 1
        ds.StudyDescription, ds.SeriesDescription = 'SYNTHETIC TEST ONLY', 'Synthetic delivery fixture'
        ds.StudyDate = ds.SeriesDate = '20200101'
        ds.StudyTime = ds.SeriesTime = '120000'
        ds.ImagePositionPatient = [-64.0, -64.0, z * 3.0]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.PatientPosition = 'HFS'
        ds.SliceThickness = ds.SpacingBetweenSlices = 3.0
        ds.PixelSpacing, ds.Rows, ds.Columns = [2.0, 2.0], 64, 64
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, 'MONOCHROME2'
        ds.BitsAllocated = ds.BitsStored = 16
        ds.HighBit, ds.PixelRepresentation = 15, 1
        ds.RescaleIntercept, ds.RescaleSlope = 0, 1
        ds.PixelData = np.zeros((64, 64), np.int16).tobytes()
        ds.save_as(folder / ('CT_%03d.dcm' % z), enforce_file_format=True)


def cube(z, y, x):
    mask = np.zeros((16, 64, 64), bool)
    mask[z:z+4, y:y+6, x:x+6] = True
    return mask


def rois(dataset):
    names = {int(row.ROINumber): str(row.ROIName) for row in dataset.StructureSetROISequence}
    contours = {names[int(row.ReferencedROINumber)]: row for row in dataset.ROIContourSequence}
    observations = {names[int(row.ReferencedROINumber)]: row for row in dataset.RTROIObservationsSequence}
    return set(names.values()), contours, observations


class HeadNeckStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix='hn-study-rtstruct-synthetic-')
        cls.base = Path(cls.workspace.name)
        cls.input = cls.base / 'series'
        series(cls.input)
        cls.levels = {HN.nome_do_nivel(index): cube(3 + index % 4, 6 + index // 6 * 12, 6 + index % 6 * 8)
                      for index in HN.ROTULOS_DA_UNIAO}
        cls.levels[HN.NOME_DA_UNIAO] = np.logical_or.reduce(list(cls.levels.values()))
        cls.levels['parotid_lnl_left'] = cube(5, 42, 43)
        cls.levels['parotid_lnl_right'] = cube(5, 42, 10)
        cls.crude = {'total_v3': {'brain': cube(9, 26, 26)},
                     'head_glands_cavities': {'parotid_gland_left': cube(4, 43, 44),
                                             'parotid_gland_right': cube(4, 43, 11)}}

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def deliver(self, *, mode='perso', protocols=('cabeca_pescoco',), modality='CT', exclusions=(), levels=None):
        output = self.base / ('output-%s' % len(list(self.base.iterdir())))
        output.mkdir()
        logs = []
        writer = OUTPUT.Saida(E, self.input, output, 'RS_RadAI_20200101_12345678.dcm',
                              tasks=('total_v3', 'head_glands_cavities'), versao='SYNTHETIC TEST', suavizar_mm=0,
                              log=logs.append, modalidade=modality)
        cervical = self.levels if levels is None else levels
        with patch.object(E, 'curar', side_effect=lambda masks, extras, log=None: (dict(masks), {name: 'ts' for name in masks})), \
             patch.object(E, 'preparar_full', side_effect=lambda masks, **kw: (dict(masks), {})):
            result = writer.full_e_oar(self.crude, cervicais=cervical,
                                       modo=mode, protocolos=protocols, oar_fora=exclusions)
            # A edição atual entrega STUDY e FULL em pedidos distintos.
            # O FULL de comparação é uma execução personalizada e explícita.
            self.assertIsNone(result.get("full"))
            study = pydicom.dcmread(result["entregue"])
            full = writer.full_e_oar(self.crude, cervicais=cervical, modo="perso",
                                     protocolos=protocols, anatomia_geral_full=True)
        return pydicom.dcmread(full["entregue"]), study, result

    def test_advanced_protocol_delivers_levels_union_and_current_parotids_in_both_files(self):
        full, study, result = self.deliver()
        full_names, full_contours, full_observations = rois(full)
        study_names, study_contours, study_observations = rois(study)
        level_names = {E.nome_clinico(name) for name in self.levels if name.startswith('Lvl_')}
        self.assertEqual(len(level_names), 18)
        self.assertTrue(level_names <= study_names, sorted(level_names - study_names))
        self.assertTrue(level_names <= full_names)
        self.assertIn('LNL_UNION_ai', study_names)
        self.assertIn('Parotid_L_ai', study_names)
        self.assertIn('Parotid_R_ai', study_names)
        self.assertIn('Parotid_L_ts', full_names)
        self.assertNotIn('Parotid_L_ts', study_names)
        self.assertNotEqual(full_contours['Parotid_L_ai'].ContourSequence,
                            full_contours['Parotid_L_ts'].ContourSequence)
        self.assertNotIn('Lvl_VIII_L_ai', study_names)
        self.assertEqual(study.ApprovalStatus, 'UNAPPROVED')
        self.assertEqual(full.ApprovalStatus, 'UNAPPROVED')
        for name in level_names | {'LNL_UNION_ai', 'Parotid_L_ai', 'Parotid_R_ai'}:
            self.assertEqual(study_contours[name].ContourSequence, full_contours[name].ContourSequence, name)
            self.assertEqual(study_observations[name].ROIObservationDescription,
                             full_observations[name].ROIObservationDescription, name)
            if name.startswith(('Lvl_', 'LNL')):
                self.assertEqual(study_observations[name].RTROIInterpretedType, 'CONTROL')

    def test_additional_study_delivery_preserves_full_geometry_colors_and_descriptions(self):
        advanced, _, _ = self.deliver()
        baseline, _, _ = self.deliver(protocols=())
        advanced_names, advanced_contours, advanced_observations = rois(advanced)
        baseline_names, baseline_contours, baseline_observations = rois(baseline)
        self.assertEqual(advanced_names, baseline_names)
        for name in advanced_names:
            self.assertEqual(advanced_contours[name].ContourSequence, baseline_contours[name].ContourSequence, name)
            self.assertEqual(list(advanced_contours[name].ROIDisplayColor), list(baseline_contours[name].ROIDisplayColor), name)
            self.assertEqual(advanced_observations[name].get('ROIObservationDescription'),
                             baseline_observations[name].get('ROIObservationDescription'), name)

    def test_normal_auto_and_manual_hnl_do_not_add_individual_levels_to_study(self):
        for mode, protocols in [('auto', ('cabeca_pescoco',)), ('perso', ()), ('perso', ('cranio',))]:
            with self.subTest(mode=mode, protocols=protocols):
                full, study, _ = self.deliver(mode=mode, protocols=protocols)
                names = rois(study)[0]
                self.assertFalse(any(name.startswith('Lvl_') for name in names))
                self.assertTrue(any(name.startswith('Lvl_') for name in rois(full)[0]))
                self.assertEqual('LNL_UNION_ai' in names, protocols != ('cranio',))

    def test_user_exclusions_by_internal_or_final_name_stay_full_only(self):
        for excluded in ('Lvl_III_L', 'Lvl_III_L_ai'):
            with self.subTest(excluded=excluded):
                full, study, result = self.deliver(exclusions=(excluded,))
                self.assertNotIn('Lvl_III_L_ai', rois(study)[0])
                self.assertIn('Lvl_III_L_ai', rois(full)[0])
                self.assertIn('Lvl_III_L', result['oar_fora'])
                self.assertIn('Lvl_III_R_ai', rois(study)[0])

    def test_existing_marked_union_guard_is_preserved(self):
        class Marked(dict):
            extensao = {'ok': False, 'motivo': 'SYNTHETIC EXTENSION GUARD'}
        full, study, result = self.deliver(levels=Marked(self.levels))
        self.assertIn('LNL_UNION_ai', rois(full)[0])
        self.assertNotIn('LNL_UNION_ai', rois(study)[0])
        self.assertTrue({E.nome_clinico(HN.nome_do_nivel(index)) for index in HN.ROTULOS_DA_UNIAO}
                        <= rois(study)[0])
        self.assertIn('LNL_UNION', result['oar_fora_por_substituicao'])

    def test_mr_scope_does_not_add_levels_and_missing_model_is_not_fabricated(self):
        _, study, _ = self.deliver(modality='MR')
        self.assertFalse(any(name.startswith('Lvl_') for name in rois(study)[0]))
        _, study, _ = self.deliver(levels={})
        self.assertFalse(any(name.startswith(('Lvl_', 'LNL')) for name in rois(study)[0]))

    def test_fast_and_default_whitelist_do_not_acquire_cervical_levels(self):
        self.assertFalse(OUTPUT.niveis_no_study('fast', 'CT', ('cabeca_pescoco',), self.levels))
        individuals = {HN.nome_do_nivel(index, fixed) for index in range(1, 21) for fixed in (True, False)}
        self.assertTrue(individuals.isdisjoint(SETS.PERMITIDOS_NO_OAR))
        self.assertTrue(individuals.isdisjoint(SETS.PERMITIDOS_NO_OAR_FAST))

    def test_unknown_level_names_are_not_promoted_and_neutral_names_are_preserved(self):
        supplied = {name: cube(3, 10, 10) for name in ('LNL01', 'LNL20', 'LNL99', 'Lvl_unknown')}
        self.assertEqual(set(OUTPUT.niveis_no_study('perso', 'CT', ('cabeca_pescoco',), supplied)), {'LNL01', 'LNL20'})

    def test_preview_lists_individual_levels_and_respects_exclusions_and_disabled_motor(self):
        import radai_batch as batch
        selected = {'modo': 'perso', 'modalidade': 'CT', 'protocolos': ['cabeca_pescoco']}
        result = batch.previa_da_entrega(selected)
        included = {row['chave'] for row in result['oar']['estruturas']}
        expected = {HN.nome_do_nivel(index) for index in HN.ROTULOS_DA_UNIAO}
        self.assertTrue(expected <= included, sorted(expected - included))
        self.assertNotIn('Lvl_VIII_L', included)
        for excluded in ('Lvl_III_L', 'Lvl_III_L_ai'):
            with self.subTest(excluded=excluded):
                result = batch.previa_da_entrega(dict(selected, oar_fora=[excluded]))
                self.assertNotIn('Lvl_III_L', {row['chave'] for row in result['oar']['estruturas']})
                self.assertIn('Lvl_III_L', {row['chave'] for row in result['oar']['fora']})
        result = batch.previa_da_entrega(dict(selected, tasks={'hnlnl': False}))
        self.assertFalse(expected & {row['chave'] for row in result['oar']['estruturas']})


if __name__ == '__main__':
    unittest.main(verbosity=2)
