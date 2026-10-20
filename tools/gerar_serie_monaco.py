# -*- coding: utf-8 -*-
import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))


def pasta_app(aqui):
    for c in (os.path.join(aqui, "..", "app"), os.path.join(aqui, "..")):
        if os.path.exists(os.path.join(c, "radai_watcher.py")):
            return os.path.abspath(c)
    return os.path.abspath(os.path.join(aqui, "..", "app"))


sys.path.insert(0, pasta_app(AQUI))

import numpy as np
import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid

LADO = 256
PIXEL_MM = 1.5
CORTE_MM = 3.0
CORTES = 40
NOME = "FANTOMA^MONACO"
ID = "RADAI_MONACO_TESTE"


def _imagem(i):
    yy, xx = np.mgrid[0:LADO, 0:LADO]
    r = np.hypot((yy - LADO / 2.0) * PIXEL_MM, (xx - LADO / 2.0) * PIXEL_MM)
    img = np.full((LADO, LADO), -1000, dtype=np.int16)
    img[r <= 150.0] = 20
    img[r <= 60.0] = 55
    img[(r <= 60.0) & (r >= 35.0)] = 60
    img[r <= 12.0] = 300
    return img


def escrever_serie(pasta, quando):
    os.makedirs(pasta, exist_ok=True)
    estudo, serie, quadro = generate_uid(), generate_uid(), generate_uid()
    arquivos = []
    for i in range(CORTES):
        ds = Dataset()
        ds.SpecificCharacterSet = "ISO_IR 100"
        ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPInstanceUID = generate_uid()
        ds.StudyDate = ds.SeriesDate = ds.AcquisitionDate = \
            quando.strftime("%Y%m%d")
        ds.StudyTime = ds.SeriesTime = ds.AcquisitionTime = \
            quando.strftime("%H%M%S")
        ds.AccessionNumber = ""
        ds.Modality = "CT"
        ds.Manufacturer = "Radioterapia.AI (fantoma sintetico)"
        ds.ReferringPhysicianName = ""
        ds.StudyDescription = "FANTOMA SINTETICO - TESTE MONACO"
        ds.SeriesDescription = "CT fantoma sintetico"
        ds.PatientName = NOME
        ds.PatientID = ID
        ds.PatientBirthDate = ""
        ds.PatientSex = "O"
        ds.KVP = "120"
        ds.SliceThickness = CORTE_MM
        ds.PatientPosition = "HFS"
        ds.StudyInstanceUID = estudo
        ds.SeriesInstanceUID = serie
        ds.StudyID = "1"
        ds.SeriesNumber = 2
        ds.AcquisitionNumber = 1
        ds.InstanceNumber = i + 1
        z = -CORTES * CORTE_MM / 2.0 + i * CORTE_MM
        ds.ImagePositionPatient = [-LADO * PIXEL_MM / 2.0 + PIXEL_MM / 2.0,
                                   -LADO * PIXEL_MM / 2.0 + PIXEL_MM / 2.0, z]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.FrameOfReferenceUID = quadro
        ds.PositionReferenceIndicator = ""
        ds.SliceLocation = z
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.Rows = ds.Columns = LADO
        ds.PixelSpacing = [PIXEL_MM, PIXEL_MM]
        ds.BitsAllocated = ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        ds.RescaleIntercept = 0
        ds.RescaleSlope = 1
        ds.RescaleType = "HU"
        ds.PixelData = _imagem(i).tobytes()
        caminho = os.path.join(pasta, "CT_%s" % ds.SOPInstanceUID)
        pydicom.dcmwrite(caminho, ds, implicit_vr=True, little_endian=True,
                         enforce_file_format=False)
        arquivos.append(caminho)
    with open(os.path.join(pasta, "RTDIR.dir"), "w", encoding="ascii",
              newline="\r\n") as f:
        f.write("!Indice inventado pelo Radioterapia.AI para teste\n"
                "%s\n" % serie)
    with open(os.path.join(pasta, "CT_%s.dir" % serie), "w", encoding="ascii",
              newline="\r\n") as f:
        f.write("%s\n" % serie)
        for a in arquivos:
            f.write("%s\n" % os.path.basename(a))
    return serie, arquivos


def mascaras(forma, grade_z0=8, grade_z1=31):
    nz, ny, nx = forma
    zz, yy, xx = np.ogrid[0:nz, 0:ny, 0:nx]
    r = np.hypot((yy - ny / 2.0) * PIXEL_MM, (xx - nx / 2.0) * PIXEL_MM)
    faixa = (zz >= grade_z0) & (zz <= grade_z1)
    anel = ((r <= 60.0) & (r >= 35.0)) | (r <= 12.0)
    solido = np.hypot((yy - ny * 0.30) * PIXEL_MM,
                      (xx - nx * 0.70) * PIXEL_MM) <= 18.0
    return {"liver": np.ascontiguousarray(anel & faixa),
            "spleen": np.ascontiguousarray(solido & faixa)}


def montar_rtstruct(engine, arquivos, tps):
    stage = tempfile.mkdtemp(prefix="radai_monaco_")
    antes = os.environ.get("RADAI_TPS_DESTINO")
    try:
        engine.copy_sorted(arquivos, stage)
        img = engine.load_sitk(stage)
        forma = tuple(int(v) for v in reversed(img.GetSize()))
        os.environ["RADAI_TPS_DESTINO"] = tps
        rs, _mapa = engine.build_rtstruct(stage, mascaras(forma),
                                          versao_worker="teste-monaco",
                                          descontar=False)
        saida = tempfile.mkdtemp(prefix="radai_monaco_rs_")
        final = os.path.join(saida, "RS.dcm")
        shutil.copy2(rs, final)
        shutil.rmtree(os.path.dirname(rs), ignore_errors=True)
        return final
    finally:
        if antes is None:
            os.environ.pop("RADAI_TPS_DESTINO", None)
        else:
            os.environ["RADAI_TPS_DESTINO"] = antes
        shutil.rmtree(stage, ignore_errors=True)


ROTEIRO = u"""TESTE DE IMPORTACAO NO MONACO - Radioterapia.AI Local Suite
==============================================================

Serie e estruturas SINTETICAS (FANTOMA^MONACO, ID {id}). Nenhum dado de
paciente. As estruturas sao sugestao nao aprovada (UNAPPROVED) e sufixo _ai.

O que foi gerado em {raiz}:

  SERIE\\                 {cortes} cortes CT_<UID> sem extensao e sem
                          preambulo, como a pasta da clinica, mais
                          RTDIR.dir e CT_<serie>.dir (INVENTADOS: o formato
                          real nao e publico)
  SERIE\\{rs}             posicao 1: o RTSTRUCT dentro da pasta da serie
  RTSTRUCT_AO_LADO\\{rs}  posicao 2: o MESMO RTSTRUCT numa pasta ao lado
  COMPARACAO_FURO_XOR\\   o mesmo conjunto gravado para o Eclipse (o furo
                          como contorno separado), so para comparar

As duas estruturas:
  Liver_ai   um ANEL (raio 35 a 60 mm) com uma ilha de 12 mm no meio. No
             Monaco o anel tem de chegar OCO (o furo pela fenda) e a ilha
             cheia. Anel preenchido = o furo nao foi lido.
  Spleen_ai  um cilindro solido, o caso simples.

Passo a passo
-------------
1. Pergunte ao fisico onde fica a pasta de recepcao do Monaco. Nao grave
   nada nela sem a combinacao com o fisico e a TI (regra 4 do projeto):
   este teste usa uma pasta PROPRIA.
2. No Monaco: Import New Data -> Browse -> a pasta SERIE.
   Anote: a serie aparece? O RTSTRUCT aparece junto (posicao 1)?
3. Repita apontando RTSTRUCT_AO_LADO depois de importar a serie
   (posicao 2). O RTSTRUCT entra sozinho, com as imagens ja no Monaco?
4. Abra as estruturas: Liver_ai oco com a ilha cheia? Spleen_ai cheio?
   Os nomes chegaram sem acento e com _ai?
5. (Opcional) Importe COMPARACAO_FURO_XOR e veja se o anel chega
   preenchido: e o que o arquivo do Eclipse faria no Monaco.
6. Anote tambem se o Monaco mostra a estrutura como nao aprovada.

Mande de volta: o que apareceu em cada passo e a mensagem de erro, se houver.
Apague a pasta {raiz} quando terminar.
"""


def main():
    ap = argparse.ArgumentParser(
        description="Serie sintetica para o teste de importacao no Monaco.")
    ap.add_argument("destino", help="pasta onde criar MONACO_TESTE")
    a = ap.parse_args()
    import engine
    raiz = os.path.join(os.path.abspath(a.destino), "MONACO_TESTE")
    if os.path.exists(raiz):
        sys.exit("ja existe: %s -- apague ou escolha outra pasta" % raiz)
    pasta = os.path.join(raiz, "SERIE")
    uid, arquivos = escrever_serie(pasta, datetime.now())
    nome_rs = "RS_RadAI_%s_%s.dcm" % (datetime.now().strftime("%Y%m%d"),
                                      uid[-8:])
    rs_monaco = montar_rtstruct(engine, arquivos, "monaco")
    rs_eclipse = montar_rtstruct(engine, arquivos, "eclipse")
    for sub, origem in (("SERIE", rs_monaco), ("RTSTRUCT_AO_LADO", rs_monaco),
                        ("COMPARACAO_FURO_XOR", rs_eclipse)):
        os.makedirs(os.path.join(raiz, sub), exist_ok=True)
        shutil.copy2(origem, os.path.join(raiz, sub, nome_rs))
    for origem in (rs_monaco, rs_eclipse):
        shutil.rmtree(os.path.dirname(origem), ignore_errors=True)
    with open(os.path.join(raiz, "ROTEIRO_MONACO.txt"), "w",
              encoding="utf-8", newline="\r\n") as f:
        f.write(ROTEIRO.format(id=ID, raiz=raiz, cortes=CORTES, rs=nome_rs))
    print("serie sintetica: %d cortes, RTSTRUCT nas duas posicoes" % CORTES)
    print("roteiro: %s" % os.path.join(raiz, "ROTEIRO_MONACO.txt"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
