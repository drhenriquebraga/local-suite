"""Compare RTSTRUCT references with original and imported DICOM headers, read-only."""
import argparse
import json
from pathlib import Path
import re

import pydicom
from pydicom.uid import RTStructureSetStorage


def referencias(rs):
    esperado = {}
    contornos = set()
    for frame in rs.ReferencedFrameOfReferenceSequence:
        for estudo in getattr(frame, "RTReferencedStudySequence", ()):
            for serie in estudo.RTReferencedSeriesSequence:
                for corte in serie.ContourImageSequence:
                    esperado.setdefault(str(corte.ReferencedSOPInstanceUID), set()).add((
                        str(corte.ReferencedSOPClassUID), str(estudo.ReferencedSOPInstanceUID),
                        str(serie.SeriesInstanceUID), str(frame.FrameOfReferenceUID)))
    for roi in getattr(rs, "ROIContourSequence", None) or ():
        for contorno in getattr(roi, "ContourSequence", None) or ():
            for corte in getattr(contorno, "ContourImageSequence", None) or ():
                contornos.add((str(corte.ReferencedSOPInstanceUID), str(corte.ReferencedSOPClassUID)))
    if not esperado:
        raise ValueError("O RTSTRUCT não declara as imagens da série referenciada.")
    return esperado, contornos


def inventario(pasta):
    campos = ("SOPInstanceUID", "SOPClassUID", "StudyInstanceUID",
              "SeriesInstanceUID", "FrameOfReferenceUID")
    if not pasta.is_dir():
        raise ValueError("A pasta de imagens não está disponível.")
    imagens, ilegíveis = {}, 0
    for arq in pasta.rglob("*"):
        if not arq.is_file():
            continue
        try:
            ds = pydicom.dcmread(arq, stop_before_pixels=True, specific_tags=campos, force=True)
        except (OSError, ValueError):
            ilegíveis += 1
            continue
        if not getattr(ds, "SOPInstanceUID", None) or not getattr(ds, "SOPClassUID", None):
            if arq.suffix.lower() == ".dcm":
                ilegíveis += 1
            continue
        if ds.SOPClassUID == RTStructureSetStorage:
            continue
        uid, *atributos = (str(getattr(ds, campo, "")) for campo in campos)
        imagens.setdefault(uid, set()).add(tuple(atributos))
    return imagens, ilegíveis


def conferir(pasta, esperado, contornos, uid_do_erro=None):
    imagens, ilegiveis = inventario(pasta)
    contornos_sem_serie = {(u, c) for u, c in contornos
                           if not any(ref[0] == c for ref in esperado.get(u, ()))}
    return {
        "instancias_na_pasta": len(imagens),
        "arquivos_ilegiveis": ilegiveis,
        "imagens_referenciadas": len(esperado),
        "referencias_ausentes_na_pasta": len(esperado.keys() - imagens.keys()),
        "referencias_com_metadados_divergentes": sum(imagens[u] != esperado[u]
            for u in esperado.keys() & imagens.keys()),
        "referencias_de_contorno_fora_da_serie_declarada": len(contornos_sem_serie),
        "imagem_do_erro_presente_na_pasta": uid_do_erro in imagens if uid_do_erro else None,
        "imagem_do_erro_referenciada_no_rtstruct": uid_do_erro in esperado if uid_do_erro else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rtstruct", type=Path, help="O RTSTRUCT que falhou, em cópia local")
    parser.add_argument("imagens_originais", type=Path, help="Pasta apontada na segmentação")
    parser.add_argument("--imagens-exportadas", type=Path, help="Pasta de imagens levada ao Eclipse")
    parser.add_argument("--log", type=Path, help="Log do Eclipse contendo o SOP UID ausente")
    args = parser.parse_args()
    try:
        ds = pydicom.dcmread(args.rtstruct, stop_before_pixels=True)
        if ds.SOPClassUID != RTStructureSetStorage:
            raise ValueError("O primeiro arquivo precisa ser um RTSTRUCT DICOM.")
        esperado, contornos = referencias(ds)
        uid = None
        if args.log:
            log = args.log.read_text(encoding="utf-8-sig", errors="replace")
            achado = re.search(r"Image with UID\s+['\"]*([\d.]+)['\"]*\s+not present", log)
            uid = achado.group(1) if achado else None
        resultado = {"originais": conferir(args.imagens_originais, esperado, contornos, uid)}
        if args.imagens_exportadas:
            resultado["exportadas"] = conferir(args.imagens_exportadas, esperado, contornos, uid)
    except (OSError, ValueError, AttributeError) as exc:
        parser.exit(2, "Não foi possível conferir as referências (%s).\n" % type(exc).__name__)
    print(json.dumps(resultado, indent=2))


if __name__ == "__main__":
    main()
