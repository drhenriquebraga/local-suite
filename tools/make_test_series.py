# -*- coding: utf-8 -*-
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

try:
    import numpy as np
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid
except ImportError as e:
    sys.exit("Falta dependência (%s). Rode com o python do bundle:\n"
             r"  C:\RADIOTERAPIA_AI\AUTO_CONTORNO\python\python.exe tools\make_test_series.py ..." % e)

ROWS = COLS = 128
PIXEL_MM = 2.0
THICK_MM = 3.0


def fatia(z_idx, n):
    yy, xx = np.mgrid[0:ROWS, 0:COLS]
    cy = cx = ROWS / 2.0
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    img = np.full((ROWS, COLS), -1000, dtype=np.int16)
    img[r < ROWS * 0.40] = 0
    img[(yy - cy * 0.6) ** 2 + (xx - cx) ** 2 < 90] = -900
    img[(yy - cy * 1.4) ** 2 + (xx - cx) ** 2 < 90] = 900
    img[r < ROWS * 0.40] += int(20 * np.sin(3.14 * z_idx / max(1, n)))
    return img


def escreve_serie(destino, pid, quando, n_cortes):
    study_uid = generate_uid()
    series_uid = generate_uid()
    frame_uid = generate_uid()
    os.makedirs(destino, exist_ok=True)

    for i in range(n_cortes):
        meta = Dataset()
        meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        meta.MediaStorageSOPInstanceUID = generate_uid()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        meta.ImplementationClassUID = generate_uid()

        ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
        ds.SOPClassUID = meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
        ds.Modality = "CT"

        ds.PatientName = "FANTOMA^TESTE"
        ds.PatientID = pid
        ds.PatientBirthDate = ""
        ds.PatientSex = "O"

        ds.StudyInstanceUID = study_uid
        ds.SeriesInstanceUID = series_uid
        ds.FrameOfReferenceUID = frame_uid
        ds.StudyID = "1"
        ds.SeriesNumber = 1
        ds.InstanceNumber = i + 1
        ds.StudyDescription = "FANTOMA SINTETICO - TESTE RadAI"
        ds.SeriesDescription = "CT fantoma sintetico"

        ds.StudyDate = ds.SeriesDate = ds.AcquisitionDate = quando.strftime("%Y%m%d")
        ds.StudyTime = ds.SeriesTime = ds.AcquisitionTime = quando.strftime("%H%M%S")

        ds.ImagePositionPatient = [-COLS * PIXEL_MM / 2.0,
                                   -ROWS * PIXEL_MM / 2.0,
                                   i * THICK_MM]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.PatientPosition = "HFS"
        ds.SliceThickness = THICK_MM
        ds.SpacingBetweenSlices = THICK_MM
        ds.PixelSpacing = [PIXEL_MM, PIXEL_MM]
        ds.Rows, ds.Columns = ROWS, COLS
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.RescaleIntercept = 0
        ds.RescaleSlope = 1
        ds.PixelData = fatia(i, n_cortes).tobytes()

        caminho = os.path.join(destino, "CT_%04d.dcm" % (i + 1))
        try:
            ds.save_as(caminho, enforce_file_format=True)
        except TypeError:
            ds.save_as(caminho, write_like_original=False)
    return series_uid


def main():
    ap = argparse.ArgumentParser(description="Gera séries DICOM sintéticas para teste do vigia.")
    ap.add_argument("destino", help="pasta onde criar a árvore de teste")
    ap.add_argument("--pacientes", type=int, default=3, help="quantas séries criar (padrão 3)")
    ap.add_argument("--cortes", type=int, default=30, help="cortes por série (padrão 30; o vigia exige >= 20)")
    a = ap.parse_args()

    if a.cortes < 20:
        print("AVISO: com menos de 20 cortes o vigia ignora a série (MIN_SLICES).")

    random.seed(42)
    base = datetime.now()
    print("Gerando %d série(s) sintética(s) em %s" % (a.pacientes, a.destino))
    for k in range(a.pacientes):
        quando = base - timedelta(days=random.randint(1, 400), hours=random.randint(0, 23))
        pid = "PAC_%04d" % (k + 1)
        pasta = os.path.join(a.destino, pid, "CT_" + quando.strftime("%Y%m%d"))
        uid = escreve_serie(pasta, pid, quando, a.cortes)
        print("  %s  %s  %d cortes  ...%s" % (pid, quando.strftime("%d/%m/%Y"), a.cortes, uid[-8:]))

    print("\nPronto. Aponte o ROOT do radai_watcher.config para:\n  %s" % os.path.abspath(a.destino))
    print("Lembre: fantoma geométrico não tem anatomia — serve para testar o\n"
          "encanamento (varredura, ordem da fila, locks), não a segmentação.")


if __name__ == "__main__":
    main()
