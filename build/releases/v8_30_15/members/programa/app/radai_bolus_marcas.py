"""Localized external face marks for the print preview and exported mesh."""
from pathlib import Path
import base64
import io
import json
from functools import lru_cache

TEXTOS = {
    "pt-BR": [
        "CABEÇA",
        "ESTE LADO PARA CIMA",
        "Posição no tomógrafo",
        "Cabeça primeiro",
        "Pés primeiro",
        "Cabeça primeiro (assumido)"
    ],
    "en": [
        "HEAD",
        "THIS SIDE UP",
        "Position in the scanner",
        "Head first",
        "Feet first",
        "Head first (assumed)"
    ],
    "es": [
        "CABEZA",
        "ESTE LADO ARRIBA",
        "Posición en el tomógrafo",
        "Cabeza primero",
        "Pies primero",
        "Cabeza primero (supuesta)"
    ],
    "de": [
        "KOPF",
        "DIESE SEITE OBEN",
        "Position im CT",
        "Kopf zuerst",
        "Füße zuerst",
        "Kopf zuerst (angenommen)"
    ],
    "fr": [
        "TÊTE",
        "CE CÔTÉ EN HAUT",
        "Position dans le scanner",
        "Tête en premier",
        "Pieds en premier",
        "Tête en premier (supposé)"
    ],
    "it": [
        "TESTA",
        "QUESTO LATO IN ALTO",
        "Posizione nello scanner",
        "Testa per prima",
        "Piedi per primi",
        "Testa per prima (presunta)"
    ],
    "pl": [
        "GŁOWA",
        "TĄ STRONĄ DO GÓRY",
        "Pozycja w tomografie",
        "Głową do przodu",
        "Stopami do przodu",
        "Głową do przodu (założono)"
    ],
    "ar": [
        "الرأس",
        "هذا الجانب للأعلى",
        "الوضع في جهاز التصوير",
        "الرأس أولاً",
        "القدمان أولاً",
        "الرأس أولاً (مفترض)"
    ],
    "bn": [
        "মাথা",
        "এই দিক উপরে",
        "স্ক্যানারে অবস্থান",
        "মাথা আগে",
        "পা আগে",
        "মাথা আগে (অনুমিত)"
    ],
    "ko": [
        "머리",
        "이쪽이 위",
        "스캐너 내 위치",
        "머리부터",
        "발부터",
        "머리부터 (추정)"
    ],
    "zh-CN": [
        "头部",
        "此面朝上",
        "扫描时体位",
        "头先进",
        "足先进",
        "头先进（假定）"
    ],
    "ja": [
        "頭側",
        "この面を上に",
        "撮影時の体位",
        "頭から",
        "足から",
        "頭から（推定）"
    ]
}


def chave_idioma(idioma):
    base = str(idioma or "").replace("_", "-").split("-")[0].lower()
    return next((chave for chave in TEXTOS if chave.split("-")[0] == base), "en")


def texto(idioma):
    return TEXTOS[chave_idioma(idioma)]


@lru_cache(maxsize=1)
def _linhas():
    # Fixed, shaped artwork at 32 pixels per em. No workstation font or
    # shaping engine is required, including for Arabic and Bengali.
    with (Path(__file__).parent / "data" / "bolus_marcas.json").open(encoding="utf-8") as f:
        return json.load(f)


def bitmap(idioma, mm, com_cabeca):
    import numpy as np
    from PIL import Image
    try:
        encoded = _linhas()[chave_idioma(idioma)]
        rows = []
        for row in (encoded if com_cabeca else encoded[1:]):
            with Image.open(io.BytesIO(base64.b64decode(row, validate=True))) as img:
                w, h = img.size
                scale = 7.5 / (32 * mm)
                dims = (max(1, round(w * scale)), max(1, round(h * scale)))
                rows.append(np.asarray(img.convert("L").resize(dims, Image.Resampling.LANCZOS)) >= 96)
    except (KeyError, OSError, ValueError):
        return None
    if not rows or any(not row.any() for row in rows):
        return None
    spacing = max(1, round(1.0 / mm))
    height = sum(row.shape[0] for row in rows) + spacing * (len(rows) - 1)
    width = max(row.shape[1] for row in rows)
    result = np.zeros((height, width), dtype=bool)
    y = 0
    for row in rows:
        h, w = row.shape
        x = (width - w) // 2
        result[y:y+h, x:x+w] = row
        y += h + spacing
    return result


def posicao_da_serie(pasta, uid):
    import pydicom
    import SimpleITK as sitk
    import engine
    caminho = engine._pasta_para_o_gdcm(str(pasta))
    if caminho is not None:
        reader = sitk.ImageSeriesReader()
        files = (reader.GetGDCMSeriesFileNames(caminho, str(uid)) if uid else
                 reader.GetGDCMSeriesFileNames(caminho))
    else:
        # Extended Windows paths unsupported by GDCM. Match the selected DICOM UID.
        if not uid:
            return ""
        files = (f for f in Path(pasta).iterdir() if f.is_file())
    tags = ["SeriesInstanceUID", "PatientPosition"]
    for source in files:
        try:
            ds = pydicom.dcmread(source, stop_before_pixels=True, specific_tags=tags)
        except (pydicom.errors.InvalidDicomError, OSError, EOFError):
            continue
        if uid and str(ds.get("SeriesInstanceUID", "")) != str(uid):
            continue
        return str(ds.get("PatientPosition", "") or "").strip().upper()
    return ""
