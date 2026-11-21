"""Regression coverage for SNC MR routing and the ten shared anatomical groups."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian, MRImageStorage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup/programa/app"))
import radai_snc_rm as snc


class TestAnatomiaSNC(unittest.TestCase):
    def test_t1_contraste_e_modalidade(self):
        ds = Dataset()
        ds.Modality = "MR"
        for text, expected in (("SAG T1W 3D pos contraste", True), ("T1_MPRAGE_1MM", True),
                               ("AX T2FLAIR", False), ("T1 perfusion", False),
                               ("T1 map", False), ("T1 localizer", False), ("MRA TOF", False)):
            with self.subTest(text=text):
                ds.SeriesDescription = text
                self.assertEqual(snc._eh_t1(ds), expected)
        ds.Modality = "CT"
        ds.SeriesDescription = "T1"
        self.assertFalse(snc._eh_t1(ds))

    def test_t1_anonimizada_conserva_os_parametros(self):
        ds = Dataset()
        ds.Modality = "MR"
        ds.MRAcquisitionType = "3D"
        ds.ScanningSequence = ["GR", "IR"]
        ds.EchoTime, ds.InversionTime, ds.FlipAngle = 2.8, 900, 8
        self.assertTrue(snc._eh_t1(ds))
        ds.InversionTime = 2500
        self.assertFalse(snc._eh_t1(ds))

    def test_uid_da_referencia_selecionada(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "1.dcm")
            meta = FileMetaDataset()
            meta.TransferSyntaxUID = ExplicitVRLittleEndian
            meta.MediaStorageSOPClassUID = MRImageStorage
            meta.MediaStorageSOPInstanceUID = generate_uid()
            ds = FileDataset(str(path), {}, file_meta=meta, preamble=bytes(128))
            ds.SOPClassUID, ds.SOPInstanceUID = MRImageStorage, meta.MediaStorageSOPInstanceUID
            ds.SeriesInstanceUID, ds.Modality, ds.SeriesDescription = generate_uid(), "MR", "T1"
            ds.save_as(path, enforce_file_format=True)
            self.assertTrue(snc.sequencia_t1(tmp, ds.SeriesInstanceUID))
            self.assertFalse(snc.sequencia_t1(tmp, generate_uid()))
            self.assertFalse(snc.sequencia_t1(Path(tmp, "inexistente")))

    def test_nao_dispara_modelo_sem_plugin_sem_t1_ou_sem_roi(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(snc.subprocess, "run") as launch:
            self.assertFalse(snc.disponivel(tmp))
            with self.assertRaisesRegex(RuntimeError, "NEURO RT"):
                snc.segmentar(tmp, "", raiz_suite=tmp)
            with patch.object(snc,"disponivel",return_value=True):
                with self.assertRaisesRegex(ValueError, "T1"):
                    snc.segmentar(tmp, "", raiz_suite=tmp)
                masks, meta = snc.segmentar(tmp, "", raiz_suite=tmp, estruturas=[])
                self.assertEqual(masks, {})
            launch.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_grupos_anatomicos_comuns_sem_sobreposicao_de_labels(self):
        self.assertEqual(len(snc.NOMES_TPS), 10)
        for model, groups in snc.GRUPOS.items():
            with self.subTest(model=model):
                self.assertEqual(len(groups), 10)
                flattened = [label for group in groups for label in group]
                self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(snc.GRUPOS[snc.SYNTHSEG][-1], (13, 52))
        self.assertEqual(snc.GRUPOS[snc.CEREBRA][-1], (27, 78))


if __name__ == "__main__":
    unittest.main()

