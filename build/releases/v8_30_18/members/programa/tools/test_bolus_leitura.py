"""Regressões de memória e cancelamento do carregador da TC no bólus."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]

import numpy as np
import pydicom
import SimpleITK as sitk
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid
import radai_bolus as bolus
import radai_bolus_leitura as leitura
import radai_bolus_screen as tela


def slices(pasta, count=24, rows=40, columns=40, frames=1, pixels=True):
    uid = generate_uid()
    study, frame = generate_uid(), generate_uid()
    for i in range(count):
        sop = generate_uid()
        meta = Dataset()
        meta.MediaStorageSOPClassUID, meta.MediaStorageSOPInstanceUID = CTImageStorage, sop
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0"*128)
        ds.SOPClassUID, ds.SOPInstanceUID = CTImageStorage, sop
        ds.Modality, ds.SeriesInstanceUID, ds.StudyInstanceUID = "CT", uid, study
        ds.FrameOfReferenceUID, ds.InstanceNumber = frame, i+1
        ds.Rows, ds.Columns = rows, columns
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = ds.BitsStored = 16
        ds.HighBit, ds.PixelRepresentation = 15, 1
        ds.ImageOrientationPatient = [1,0,0,0,1,0]
        ds.ImagePositionPatient = [0,0,2*i]
        ds.PatientPosition, ds.PixelSpacing = "HFS", [1,1]
        if frames > 1:
            ds.NumberOfFrames = frames
        ds.PixelData = (np.full((rows, columns), i, np.int16).tobytes() if pixels else b"\0\0")
        ds.save_as(str(Path(pasta)/("%04d.dcm"%i)))
    return uid


class Carregamento(unittest.TestCase):
    def test_recusa_1024_com_160_quadros_antes_dos_pixels_e_copia(self):
        with TemporaryDirectory() as folder:
            uid = slices(folder, 1, 1024, 1024, 160, pixels=False)
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            import engine
            app = FastAPI()
            tela.montar(app)
            tela._lembrar("sintetico", {"uid":uid, "modalidade":"CT","pasta":folder,"cortes":160})
            caminhos = [folder] + ([engine._PREFIXO_LONGO + folder] if os.name == "nt" else [])
            for caminho in caminhos:
                tela._lembrar("sintetico", {"uid":uid, "modalidade":"CT","pasta":caminho,"cortes":160})
                with self.subTest(caminho=caminho), patch.object(leitura,"ler_pixels",side_effect=AssertionError("decode")), patch.object(leitura,"TemporaryDirectory",side_effect=AssertionError("stage")):
                    response = TestClient(app).post("/api/bolus/abrir",json={"b":"sintetico"})
                    self.assertIn("grande demais", response.json().get("erro",""))

    def test_interrompe_cabecalhos_e_descarta_stage(self):
        import engine
        with TemporaryDirectory() as folder:
            uid = slices(folder)
            chamadas = []
            original = pydicom.dcmread
            def ler(*a, **kw):
                chamadas.append(1)
                return original(*a, **kw)
            with patch.object(pydicom,"dcmread",ler):
                with self.assertRaises(InterruptedError):
                    leitura.selecionar(folder, uid, lambda: len(chamadas) >= 2)
            self.assertEqual(len(chamadas),2)
            selecao = leitura.selecionar(folder, uid)[:-1] + (True,)
            calls = []
            def parar():
                calls.append(1)
                return len(calls)>=4
            with patch.object(leitura,"TemporaryDirectory", side_effect=lambda **kw: TemporaryDirectory(dir=folder, **kw)):
                with self.assertRaises(InterruptedError):
                    with leitura.arquivos_para_leitura(selecao, parar):
                        self.fail("abriu stage cancelado")
            self.assertFalse(any(d.is_dir() for d in Path(folder).iterdir()))

    def test_recusa_160_cortes_individuais_e_interrompe_geracao_por_bloco(self):
        with TemporaryDirectory() as folder:
            uid = slices(folder, 160, 1024, 1024, pixels=False)
            with self.assertRaisesRegex(bolus.Recusa, "grande demais"):
                leitura.selecionar(folder, uid)
        visitas = []
        def trabalho(_):
            for i in range(100):
                bolus.conferir_geracao()
                visitas.append(i)
        with self.assertRaises(InterruptedError):
            bolus.gerar_enquanto_aberto(trabalho, {}, parar=lambda: len(visitas) == 2)
        self.assertEqual(visitas, [0,1])
        bolus.conferir_geracao()  # o cancelamento pertence apenas a este pedido

    def test_volume_geometria_posicao_uma_normalizacao_e_liberacao(self):
        with TemporaryDirectory() as folder:
            uid = slices(folder)
            fonte = leitura.selecionar(folder, uid)
            img = leitura.ler_pixels(fonte, folder)
            self.assertEqual(img.GetSize(), (40,40,24))
            self.assertEqual(img.GetSpacing(), (1.,1.,2.))
            self.assertEqual(fonte[2], "HFS")
            self.assertEqual(img.GetPixel(1,1,17),17)
            with patch.object(bolus,"_int16_lps",wraps=bolus._int16_lps) as norm:
                serie = bolus.abrir(img)
                self.assertEqual(norm.call_count,1)
            with tela._TRAVA:
                tela._S.update(b="x",dono="janela-atual",serie=serie)
            tela._soltar_dono("janela-antiga")
            self.assertIs(tela._S["serie"],serie)
            tela._soltar_dono("janela-atual")
            self.assertIsNone(tela._S["serie"])

if __name__ == "__main__":
    unittest.main()
