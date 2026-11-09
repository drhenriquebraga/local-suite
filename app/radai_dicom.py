# -*- coding: utf-8 -*-
import os

SINTAXES = {
    "1.2.840.10008.1.2": (u"Implicit VR Little Endian", False),
    "1.2.840.10008.1.2.1": (u"Explicit VR Little Endian", False),
    "1.2.840.10008.1.2.1.99": (u"Deflated Explicit VR Little Endian", False),
    "1.2.840.10008.1.2.2": (u"Explicit VR Big Endian", False),
    "1.2.840.10008.1.2.4.50": (u"JPEG Baseline (8 bits, com perda)", True),
    "1.2.840.10008.1.2.4.51": (u"JPEG Extended (12 bits, com perda)", True),
    "1.2.840.10008.1.2.4.57": (u"JPEG Lossless, não hierárquico", True),
    "1.2.840.10008.1.2.4.70": (u"JPEG Lossless, primeira ordem (SV1)", True),
    "1.2.840.10008.1.2.4.80": (u"JPEG-LS sem perda", True),
    "1.2.840.10008.1.2.4.81": (u"JPEG-LS quase sem perda", True),
    "1.2.840.10008.1.2.4.90": (u"JPEG 2000 sem perda", True),
    "1.2.840.10008.1.2.4.91": (u"JPEG 2000, com perda", True),
    "1.2.840.10008.1.2.5": (u"RLE Lossless", True),
}

SINTAXE_IMPLICITA = "1.2.840.10008.1.2"
SINTAXE_DESTINO = SINTAXE_IMPLICITA

SOP_CAPTURA = "1.2.840.10008.5.1.4.1.1.7"
CONVERSAO_PADRAO = "WSD"
PREFIXO_SAIDA = "DICOM_BRIDGE_"
PASTA_NOSSA = "_RadAI"


def sintaxe_de_saida(tps=None):
    # GUARDA: a mesma sintaxe nos dois TPS, a do RTSTRUCT do motor; o TPS escolhido decide so o desenho do furo.
    return SINTAXE_DESTINO


def pasta_pulada(nome):
    n = str(nome or "")
    return n == PASTA_NOSSA or n.startswith(PREFIXO_SAIDA)


def nomes_de_subpasta(uids):
    import hashlib
    fora, vistos = [], set()
    curtos = [str(u or "")[-8:] or "serie" for u in uids]
    for u, curto in zip(uids, curtos):
        nome = curto
        if curtos.count(curto) > 1 or nome in vistos:
            nome = u"%s_%s" % (curto, hashlib.sha1(
                str(u or "").encode("utf-8")).hexdigest()[:6])
        while nome in vistos:
            nome += u"_"
        vistos.add(nome)
        fora.append(nome)
    return fora


def _ascii(texto):
    import unicodedata
    t = unicodedata.normalize("NFKD", u"%s" % (texto or u""))
    t = t.replace(u"—", u"-").replace(u"–", u"-")
    return t.encode("ascii", "ignore").decode("ascii").replace(u"`", u"")

TOLERANCIA_ESPACO_MM = 0.01
FRACAO_DE_PIXEL_NO_PLANO = 0.1

SINTAXE_DEFLATED = "1.2.840.10008.1.2.1.99"
SINTAXE_BIG_ENDIAN = "1.2.840.10008.1.2.2"

PIXEL_TRUNCADO = "truncado"
PIXEL_CURTO = "curto"
PIXEL_AUSENTE = "ausente"
_VRS_DO_PIXEL = (b"OB", b"OW", b"OD", b"OF", b"OL", b"OV", b"UN")
TETO_DE_ITENS = 100000


def _num(v, padrao=None):
    try:
        return float(v)
    except Exception:
        return padrao


def _iop_valida(iop):
    try:
        v = [float(x) for x in (iop or [])][:6]
    except Exception:
        return False
    if len(v) < 6:
        return False
    r, c = v[:3], v[3:6]
    n = [r[1] * c[2] - r[2] * c[1], r[2] * c[0] - r[0] * c[2],
         r[0] * c[1] - r[1] * c[0]]
    nr = sum(x * x for x in r) ** 0.5
    nc = sum(x * x for x in c) ** 0.5
    # GUARDA: só o degenerado (vetor nulo ou paralelo) é inválido; IOP de pouca precisão continua valendo.
    return (0.5 <= nr <= 1.5 and 0.5 <= nc <= 1.5
            and sum(x * x for x in n) ** 0.5 >= 0.5)


def _bytes_esperados(ds):
    linhas = int(_num(getattr(ds, "Rows", None), 0) or 0)
    colunas = int(_num(getattr(ds, "Columns", None), 0) or 0)
    bits = int(_num(getattr(ds, "BitsAllocated", None), 0) or 0)
    if not (linhas and colunas and bits):
        return None
    amostras = int(_num(getattr(ds, "SamplesPerPixel", None), 1) or 1)
    quadros = int(_num(getattr(ds, "NumberOfFrames", None), 1) or 1)
    n = linhas * colunas * amostras * max(1, quadros)
    total = (n + 7) // 8 if bits == 1 else n * ((bits + 7) // 8)
    foto = str(getattr(ds, "PhotometricInterpretation", "") or "").upper()
    if amostras == 3 and foto == "YBR_FULL_422":
        total = total // 3 * 2
    return total


def _itens_inteiros(f, pos, tamanho):
    import struct
    for _i in range(TETO_DE_ITENS):
        f.seek(pos)
        cab = f.read(8)
        if len(cab) < 8:
            return PIXEL_TRUNCADO
        grupo, elemento, comp = struct.unpack("<HHI", cab)
        if (grupo, elemento) == (0xFFFE, 0xE0DD):
            return u""
        if (grupo, elemento) != (0xFFFE, 0xE000) or comp == 0xFFFFFFFF:
            return u""
        pos += 8 + comp
        if pos > tamanho:
            return PIXEL_TRUNCADO
    return u""


def _pixel_no_disco(f, ds):
    import struct
    sint = str(getattr(getattr(ds, "file_meta", None), "TransferSyntaxUID",
                       "") or "")
    # GUARDA: no Deflated a posição do arquivo não é a do conjunto inflado.
    if sint == SINTAXE_DEFLATED:
        return u""
    inicio = f.tell()
    tamanho = os.fstat(f.fileno()).st_size
    cab = f.read(12)
    imagem = bool(_num(getattr(ds, "Rows", None))
                  and _num(getattr(ds, "Columns", None)))
    if len(cab) < 8:
        return PIXEL_AUSENTE if imagem else u""
    ordem = ">" if sint == SINTAXE_BIG_ENDIAN else "<"
    grupo, elemento = struct.unpack(ordem + "HH", cab[:4])
    if (grupo, elemento) != (0x7FE0, 0x0010):
        return u""
    explicita = cab[4:6] in _VRS_DO_PIXEL and cab[6:8] == b"\x00\x00"
    if not explicita and sint and sint != SINTAXE_IMPLICITA:
        return u""
    if explicita:
        if len(cab) < 12:
            return PIXEL_TRUNCADO
        comp = struct.unpack(ordem + "I", cab[8:12])[0]
        valor = inicio + 12
    else:
        comp = struct.unpack(ordem + "I", cab[4:8])[0]
        valor = inicio + 8
    if comp == 0xFFFFFFFF:
        return _itens_inteiros(f, valor, tamanho)
    if valor + comp > tamanho:
        return PIXEL_TRUNCADO
    esperado = _bytes_esperados(ds)
    if esperado and comp < esperado:
        return PIXEL_CURTO
    return u""


def _pixel_incompleto(ds):
    if "PixelData" not in ds:
        if any(t in ds for t in ("FloatPixelData", "DoubleFloatPixelData")):
            return u""
        if _num(getattr(ds, "Rows", None)) and _num(getattr(ds, "Columns", None)):
            return u"o corte nao tem a imagem (sem PixelData)"
        return u""
    try:
        tem = len(ds.PixelData or b"")
    except Exception as e:
        return u"nao consegui ler a imagem do corte (%s)" % type(e).__name__
    esperado = _bytes_esperados(ds)
    if esperado and tem < esperado:
        return (u"a imagem do corte tem %d de %d bytes: arquivo truncado ou "
                u"corrompido" % (tem, esperado))
    return u""


def ler_cabecalho(caminho):
    import pydicom
    ds = pydicom.dcmread(caminho, stop_before_pixels=True, force=True)
    fora = []
    for elem in ds:
        try:
            valor = elem.value
            if elem.VR == "SQ":
                txt = u"%d item(ns)" % len(valor or [])
            elif isinstance(valor, bytes):
                txt = u"%d bytes" % len(valor)
            else:
                txt = str(valor)
            if len(txt) > 300:
                txt = txt[:300] + u"…"
        except Exception as e:
            txt = u"(não consegui ler: %s)" % type(e).__name__
        fora.append({
            "grupo": "%04X" % elem.tag.group,
            "elemento": "%04X" % elem.tag.element,
            "vr": str(elem.VR),
            "nome": str(elem.name),
            "valor": txt,
        })
    meta = []
    for elem in getattr(ds, "file_meta", []) or []:
        meta.append({
            "grupo": "%04X" % elem.tag.group,
            "elemento": "%04X" % elem.tag.element,
            "vr": str(elem.VR), "nome": str(elem.name),
            "valor": str(elem.value)[:300],
        })
    return {"meta": meta, "tags": fora, "n": len(fora)}


def _posicao(ds):
    ipp = getattr(ds, "ImagePositionPatient", None)
    iop = getattr(ds, "ImageOrientationPatient", None)
    if not ipp or not iop or len(ipp) < 3 or not _iop_valida(iop):
        return None
    r = [_num(x, 0.0) for x in iop[:3]]
    c = [_num(x, 0.0) for x in iop[3:6]]
    n = [r[1] * c[2] - r[2] * c[1],
         r[2] * c[0] - r[0] * c[2],
         r[0] * c[1] - r[1] * c[0]]
    p = [_num(x, 0.0) for x in ipp[:3]]
    return p[0] * n[0] + p[1] * n[1] + p[2] * n[2]



TOLERANCIA_TILT_GRAUS = 0.5


def inclinacao_de_gantry(arquivos):
    import math
    arqs = [a for a in (arquivos or ()) if a.get("caminho")]
    if len(arqs) < 3:
        return 0.0, 0.0, None
    try:
        import pydicom
        primeiro = pydicom.dcmread(arqs[0]["caminho"], stop_before_pixels=True,
                                   force=True)
        ultimo = pydicom.dcmread(arqs[-1]["caminho"], stop_before_pixels=True,
                                 force=True)
    except Exception:
        return 0.0, 0.0, None

    declarado = _num(getattr(primeiro, "GantryDetectorTilt", None))

    iop = getattr(primeiro, "ImageOrientationPatient", None)
    p0 = getattr(primeiro, "ImagePositionPatient", None)
    p1 = getattr(ultimo, "ImagePositionPatient", None)
    if not iop or not p0 or not p1 or not _iop_valida(iop):
        return 0.0, 0.0, declarado

    r = [_num(x, 0.0) for x in iop[:3]]
    c = [_num(x, 0.0) for x in iop[3:6]]
    n = [r[1] * c[2] - r[2] * c[1],
         r[2] * c[0] - r[0] * c[2],
         r[0] * c[1] - r[1] * c[0]]
    d = [_num(b, 0.0) - _num(a, 0.0) for a, b in zip(p0[:3], p1[:3])]

    ln = math.sqrt(sum(x * x for x in n))
    ld = math.sqrt(sum(x * x for x in d))
    if ln <= 0 or ld <= 0:
        return 0.0, 0.0, declarado

    cos = max(-1.0, min(1.0, sum(a * b for a, b in zip(n, d)) / (ln * ld)))
    graus = abs(math.degrees(math.acos(abs(cos))))
    desvio = ld * math.sin(math.radians(graus))
    return graus, desvio, declarado




GRUPOS_DE_ABERTURA = (b"\x02\x00", b"\x08\x00")


def vale_abrir(caminho):
    try:
        with open(caminho, "rb") as f:
            cabeca = f.read(132)
    except Exception as e:
        return False, u"%s" % type(e).__name__
    if len(cabeca) >= 132 and cabeca[128:132] == b"DICM":
        return True, u""
    if cabeca[:2] in GRUPOS_DE_ABERTURA:
        return True, u""
    return False, u"não é DICOM (sem preâmbulo DICM e sem grupo de abertura)"


def caminho_longo(caminho):
    try:
        bruto = str(caminho)
        if os.path.isabs(bruto):
            p = os.path.normpath(bruto)
        else:
            # GUARDA: o abspath do Windows come o ponto e o espaço do fim do nome; a cauda volta.
            cauda = bruto[len(bruto.rstrip(". ")):]
            p = os.path.abspath(bruto) + cauda
    except Exception:
        return str(caminho)
    if os.name != "nt" or p.startswith(u"\\\\?\\"):
        return p
    if p.startswith(u"\\\\"):
        return u"\\\\?\\UNC" + p[1:]
    return u"\\\\?\\" + p


def sem_prefixo(caminho):
    c = str(caminho)
    if c.startswith(u"\\\\?\\UNC\\"):
        return u"\\\\" + c[8:]
    if c.startswith(u"\\\\?\\"):
        return c[4:]
    return c


_VARREDURAS = {}
_TETO_VARREDURAS = 8


def _carimbo_da_arvore(pasta):
    try:
        marcas = []
        for raiz, dirs, _arqs in os.walk(pasta):
            dirs[:] = sorted(d for d in dirs if not pasta_pulada(d))
            marcas.append((raiz, os.path.getmtime(raiz)))
        return tuple(marcas)
    except Exception:
        return None


def esquecer_varredura(pasta=None):
    if pasta is None:
        _VARREDURAS.clear()
    else:
        _VARREDURAS.pop(os.path.abspath(pasta), None)


ESPESSURA_REFERENCIA_MM = 3.0
ESPESSURA_MUITO_ALTA_MM = 6.0


def laudo_de_espessura(espessura_mm):
    fonte = (u"Huang et al., J Appl Clin Med Phys 2021;22(2):168-174 "
             u"(doi:10.1002/acm2.13207)")
    try:
        e = float(espessura_mm)
    except (TypeError, ValueError):
        return {"nivel": "desconhecida", "fonte": fonte,
                "frase": u"espessura de corte desconhecida"}
    if e <= 0:
        return {"nivel": "desconhecida", "fonte": fonte,
                "frase": u"espessura de corte desconhecida"}
    if e <= ESPESSURA_REFERENCIA_MM:
        return {"nivel": "boa", "fonte": fonte,
                "frase": u"%.2f mm — dentro dos 3 mm que a literatura "
                         u"recomenda para simulação" % e}
    if e <= ESPESSURA_MUITO_ALTA_MM:
        return {"nivel": "acima", "fonte": fonte,
                "frase": u"%.2f mm — acima dos 3 mm de referência. O contorno "
                         u"automático piora progressivamente a partir daí, e "
                         u"**estrutura pequena sofre mais**" % e}
    return {"nivel": "muito_acima", "fonte": fonte,
            "frase": u"%.2f mm — bem acima dos 3 mm de referência; acima de "
                     u"6 mm o desvio medido é maior ainda" % e}


def _e_colorida(arquivo):
    foto = str(arquivo.get("fotometrica") or "")
    return (int(arquivo.get("amostras") or 1) > 1
            or foto.startswith(("RGB", "YBR", "PALETTE")))


def _ler_arquivo(caminho, nome, series, ignorados):
    import pydicom
    vale, porque = vale_abrir(caminho)
    if not vale:
        ignorados.append((nome, porque))
        return
    try:
        with open(caminho, "rb") as f:
            ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
            try:
                pixel = _pixel_no_disco(f, ds)
            except Exception:
                pixel = u""
        uid = str(getattr(ds, "SeriesInstanceUID", "") or "")
        if not uid:
            ignorados.append((nome, u"sem SeriesInstanceUID"))
            return
    except Exception as e:
        ignorados.append((nome, u"%s" % type(e).__name__))
        return
    s = series.setdefault(uid, {
        "uid": uid,
        "descricao": str(getattr(ds, "SeriesDescription", "") or ""),
        "modalidade": str(getattr(ds, "Modality", "") or ""),
        "numero": str(getattr(ds, "SeriesNumber", "") or ""),
        "data": str(getattr(ds, "SeriesDate", "")
                    or getattr(ds, "StudyDate", "") or ""),
        "pid": str(getattr(ds, "PatientID", "") or ""),
        "arquivos": [],
    })
    s["arquivos"].append({
        "caminho": caminho,
        "pos": _posicao(ds),
        "instancia": _num(getattr(ds, "InstanceNumber", None)),
        "sop": str(getattr(ds, "SOPInstanceUID", "") or ""),
        "sintaxe": str(getattr(getattr(ds, "file_meta", None),
                               "TransferSyntaxUID", "") or ""),
        "espessura": _num(getattr(ds, "SliceThickness", None)),
        "frame_ref": str(getattr(ds, "FrameOfReferenceUID", "") or ""),
        "linhas": _num(getattr(ds, "Rows", None)),
        "colunas": _num(getattr(ds, "Columns", None)),
        "slope": _num(getattr(ds, "RescaleSlope", None)),
        "intercept": _num(getattr(ds, "RescaleIntercept", None)),
        "orientacao": str(getattr(ds, "PatientPosition", "") or ""),
        "pixel_spacing": [_num(x) for x in
                          (getattr(ds, "PixelSpacing", None) or [])],
        "amostras": int(_num(getattr(ds, "SamplesPerPixel", None), 1) or 1),
        "fotometrica": str(getattr(ds, "PhotometricInterpretation",
                                   "") or "").upper(),
        "sop_classe": str(getattr(ds, "SOPClassUID", "") or ""),
        "conversao": str(getattr(ds, "ConversionType", "") or ""),
        "local": _num(getattr(ds, "SliceLocation", None)),
        "entre": _num(getattr(ds, "SpacingBetweenSlices", None)),
        "iop": [_num(x) for x in
                (getattr(ds, "ImageOrientationPatient", None) or [])],
        "ipp": [_num(x) for x in
                (getattr(ds, "ImagePositionPatient", None) or [])],
        "pixel": pixel,
        "anotacao": str(getattr(ds, "BurnedInAnnotation", "") or "")
                    .strip().upper(),
    })


def _fechar(series, ignorados):
    for s in series.values():
        com_pos = [a for a in s["arquivos"] if a["pos"] is not None]
        if len(com_pos) == len(s["arquivos"]):
            s["arquivos"].sort(key=lambda a: a["pos"])
            s["ordenado_por"] = "posicao"
        else:
            s["arquivos"].sort(key=lambda a: (a["instancia"] or 0))
            s["ordenado_por"] = "instancia"
        s["cortes"] = len(s["arquivos"])

        s["espessura_mm"] = None
        s["espessura_declarada_mm"] = None
        decl = [a["espessura"] for a in s["arquivos"] if a["espessura"]]
        if decl:
            s["espessura_declarada_mm"] = round(float(decl[0]), 2)
        _pos = [a["pos"] for a in s["arquivos"] if a["pos"] is not None]
        if len(_pos) >= 2:
            _passos = sorted(abs(_pos[i + 1] - _pos[i])
                             for i in range(len(_pos) - 1))
            _m = _passos[len(_passos) // 2]
            if _m > 0:
                s["espessura_mm"] = round(float(_m), 2)
        if s["espessura_mm"] is None and s["espessura_declarada_mm"]:
            s["espessura_mm"] = s["espessura_declarada_mm"]
        s["colorida"] = any(_e_colorida(a) for a in s["arquivos"])
        s["captura"] = any(a.get("sop_classe", "").startswith(SOP_CAPTURA)
                           for a in s["arquivos"])
    return {"series": sorted(series.values(),
                             key=lambda s: (s["numero"], s["uid"])),
            "ignorados": ignorados}


def _ler_nomes(pasta, nomes, series, ignorados, parar=None, ao_ler=None,
               ao_atualizar=None):
    import time
    ultimo = 0.0
    for nome in sorted(nomes):
        if parar is not None and parar():
            return True
        if nome.startswith(PREFIXO_SAIDA):
            continue
        _ler_arquivo(os.path.join(pasta, nome), nome, series, ignorados)
        if ao_ler is not None:
            ao_ler()
        if ao_atualizar is not None and any(len(s["arquivos"]) >= 2 for s in series.values()):
            agora = time.monotonic()
            if agora - ultimo >= 0.25:
                copia = {k: dict(v, arquivos=list(v["arquivos"])) for k, v in series.items()}
                ao_atualizar(_fechar(copia, list(ignorados)))
                ultimo = agora
    return False


def varrer(pasta, relembrar=True):
    chave = os.path.abspath(pasta)
    carimbo = _carimbo_da_arvore(pasta)
    if relembrar and carimbo is not None:
        guardado = _VARREDURAS.get(chave)
        if guardado is not None and guardado[0] == carimbo:
            return guardado[1]
    series, ignorados = {}, []
    for raiz, _dirs, arqs in os.walk(pasta):
        _dirs[:] = sorted(d for d in _dirs if not pasta_pulada(d))
        _ler_nomes(raiz, arqs, series, ignorados)
    r = _fechar(series, ignorados)
    if relembrar and carimbo is not None:
        _VARREDURAS[chave] = (carimbo, r)
        while len(_VARREDURAS) > _TETO_VARREDURAS:
            _VARREDURAS.pop(next(iter(_VARREDURAS)), None)
    return r


def _arquivos_da_pasta(pasta):
    nomes = []
    for nome in os.listdir(pasta):
        try:
            if os.path.isfile(os.path.join(pasta, nome)):
                nomes.append(nome)
        except OSError:
            continue
    return nomes


def varrer_pasta(pasta, parar=None, ao_ler=None, nomes=None, ao_atualizar=None):
    series, ignorados = {}, []
    try:
        if nomes is None:
            nomes = _arquivos_da_pasta(pasta)
    except OSError as e:
        r = _fechar(series, ignorados)
        r.update(parado=False, erro=u"%s" % type(e).__name__)
        return r
    parado = _ler_nomes(pasta, nomes, series, ignorados, parar, ao_ler,
                         ao_atualizar=ao_atualizar)
    r = _fechar(series, ignorados)
    r["parado"] = parado
    return r


PASTAS_DE_SISTEMA = frozenset((
    "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information", "recovery", "msocache",
    "perflogs", "appdata", "site-packages", "__pycache__", ".git",
    "node_modules"))


def pular_na_busca(nome):
    n = str(nome or u"")
    return pasta_pulada(n) or n.lower() in PASTAS_DE_SISTEMA


def varrer_arvore(raiz, parar=None, ao_ler=None, pular=pular_na_busca):
    falhas = []
    for atual, dirs, arqs in os.walk(raiz, onerror=falhas.append):
        if parar is not None and parar():
            return
        dirs[:] = sorted(d for d in dirs if not pular(d))
        yield atual, varrer_pasta(atual, parar, ao_ler, nomes=arqs)
    for e in falhas:
        r = _fechar({}, [])
        r.update(parado=False, erro=u"%s" % type(e).__name__)
        yield str(getattr(e, "filename", "") or u""), r


TETO_PASTAS = 20000
TETO_SERIES = 500


def nova_busca():
    return {"pastas": 0, "arquivos": 0, "zips": 0, "falhas": 0,
            "series": [], "cortada": None, "parado": False}


def _linha_da_serie(pasta, s):
    return {"uid": str(s.get("uid") or u""), "pasta": pasta,
            "modalidade": str(s.get("modalidade") or u"").upper(),
            "descricao": str(s.get("descricao") or u""),
            "numero": s.get("numero") or u"",
            "cortes": int(s.get("cortes") or 0),
            "espessura_mm": s.get("espessura_mm"),
            "data": str(s.get("data") or u""),
            "pid": str(s.get("pid") or u"")}


BUSCA_INTERROMPIDA = (u"A busca foi interrompida: a lista tem só o que foi "
                      u"achado até ali.")
BUSCA_CORTADA_PASTAS = (u"A busca parou depois de %d pastas olhadas. Aponte "
                        u"a pasta do exame, e não a raiz do disco.")
BUSCA_CORTADA_SERIES = (u"A busca parou em %d séries. Aponte uma pasta mais "
                        u"perto do exame.")
ZIPS_NAO_ABERTOS = (u"A busca não abre .zip, e esta pasta tem %d. Extraia o "
                    u"arquivo e aponte a pasta extraída.")
PASTAS_ILEGIVEIS = (u"%d pasta(s) não puderam ser lidas e ficaram de fora "
                    u"da lista.")


def avisos_da_busca(b):
    fora = []
    if b.get("parado"):
        fora.append(BUSCA_INTERROMPIDA)
    if b.get("cortada") == "pastas":
        fora.append(BUSCA_CORTADA_PASTAS % int(b.get("pastas") or 0))
    elif b.get("cortada") == "series":
        fora.append(BUSCA_CORTADA_SERIES % len(b.get("series") or ()))
    if b.get("zips"):
        fora.append(ZIPS_NAO_ABERTOS % int(b["zips"]))
    if b.get("falhas"):
        fora.append(PASTAS_ILEGIVEIS % int(b["falhas"]))
    return fora


def nova_juncao():
    return {"series": {}, "ignorados": []}


def juntar_varredura(juncao, r):
    for s in r.get("series") or ():
        alvo = juncao["series"].get(s["uid"])
        if alvo is None:
            alvo = juncao["series"][s["uid"]] = dict(
                (k, s.get(k)) for k in ("uid", "descricao", "modalidade",
                                        "numero", "data", "pid"))
            alvo["arquivos"] = []
        alvo["arquivos"].extend(s.get("arquivos") or ())
    juncao["ignorados"].extend(r.get("ignorados") or ())


def varredura_da_juncao(juncao):
    series = dict((u, dict(s, arquivos=list(s["arquivos"])))
                  for u, s in juncao["series"].items())
    return _fechar(series, list(juncao["ignorados"]))


def carimbo_da_arvore(pasta):
    return _carimbo_da_arvore(pasta)


def lembrar_varredura(pasta, carimbo, r):
    if carimbo is None:
        return False
    _VARREDURAS.pop(os.path.abspath(pasta), None)
    _VARREDURAS[os.path.abspath(pasta)] = (carimbo, r)
    while len(_VARREDURAS) > _TETO_VARREDURAS:
        _VARREDURAS.pop(next(iter(_VARREDURAS)), None)
    return True


def buscar_series(raiz, busca=None, modalidades=None, min_cortes=1,
                  teto_pastas=TETO_PASTAS, teto_series=TETO_SERIES,
                  pular=pular_na_busca, juncao=None):
    b = busca if busca is not None else nova_busca()
    for k, v in nova_busca().items():
        b.setdefault(k, v)
    mods = (set(str(m).upper() for m in modalidades)
            if modalidades else None)
    por_uid = {}

    def parar():
        return bool(b.get("parado"))

    def lido():
        b["arquivos"] += 1

    for pasta, r in varrer_arvore(raiz, parar=parar, ao_ler=lido, pular=pular):
        if juncao is not None:
            juntar_varredura(juncao, r)
        if r.get("erro"):
            b["falhas"] += 1
        else:
            b["pastas"] += 1
        b["zips"] += sum(1 for n, _p in r.get("ignorados") or ()
                         if str(n).lower().endswith(u".zip"))
        mudou = False
        for s in r.get("series") or ():
            linha = _linha_da_serie(pasta, s)
            if mods is not None and linha["modalidade"] not in mods:
                continue
            if linha["cortes"] < int(min_cortes or 1):
                continue
            # GUARDA: série repartida em pastas fica na pasta que tem mais cortes dela.
            velha = por_uid.get(linha["uid"])
            if velha is None or linha["cortes"] > velha["cortes"]:
                por_uid[linha["uid"]] = linha
                mudou = True
        if mudou:
            b["series"] = list(por_uid.values())
        if r.get("parado") or parar():
            b["parado"] = True
            break
        if len(por_uid) >= int(teto_series):
            b["cortada"] = "series"
            break
        if b["pastas"] >= int(teto_pastas):
            b["cortada"] = "pastas"
            break
    return b


def _achado(ok, titulo, detalhe=u"", resolve=None, o_que_faz=u"",
            alerta=None, impede=False):
    if alerta is None:
        alerta = (not ok) and resolve is False
    return {"ok": bool(ok), "titulo": titulo, "detalhe": detalhe,
            "resolve": resolve, "o_que_faz": o_que_faz,
            "alerta": bool(alerta) and not ok, "impede": bool(impede)}


def _tem_decodificador(uid):
    try:
        from pydicom.pixels.decoders.base import _PIXEL_DATA_DECODERS
    except Exception:
        return True
    try:
        par = _PIXEL_DATA_DECODERS.get(uid)
        if par is None:
            return True
        dec = par[0] if isinstance(par, tuple) else par
        return bool(dec.is_available)
    except Exception:
        return True


def _laudo_inclinacao(arqs, enc, achados):
    if arqs and not _iop_valida(arqs[0].get("iop")):
        enc[u"Inclinação de gantry"] = (u"não dá para medir sem a orientação "
                                        u"dos cortes")
        return
    graus, desvio, declarado = inclinacao_de_gantry(arqs)
    if graus <= TOLERANCIA_TILT_GRAUS:
        enc[u"Inclinação de gantry"] = (
            u"nenhuma" if declarado in (None, 0) else
            u"%.1f° declarada, geometria ortogonal" % declarado)
        achados.append(_achado(
            True, u"Cortes empilhados perpendicularmente ao plano."))
        return
    enc[u"Inclinação de gantry"] = u"%.1f°  ·  desvio de %.1f mm no total" % (
        graus, desvio)
    achados.append(_achado(
        False,
        u"Gantry inclinado em %s°." % (u"%.1f" % graus),
        (u"Os cortes não são empilhados perpendicularmente ao plano: do "
         u"primeiro ao último há %s mm de desvio. Quem lê a série como um "
         u"volume regular — e é assim que todo leitor a lê — empilha as fatias "
         u"como se não houvesse inclinação, e o volume sai torto."
         % (u"%.1f" % desvio)) if declarado in (None, 0) else
        (u"Os cortes não são empilhados perpendicularmente ao plano: do "
         u"primeiro ao último há %s mm de desvio. Quem lê a série como um "
         u"volume regular — e é assim que todo leitor a lê — empilha as fatias "
         u"como se não houvesse inclinação, e o volume sai torto. O cabeçalho "
         u"declara %s°." % (u"%.1f" % desvio, u"%.1f" % declarado)),
        resolve=False,
        o_que_faz=u"a conversão NÃO corrige: corrigir é reamostrar, e "
                  u"reamostrar interpola o pixel do paciente — a série que "
                  u"sairia deixaria de ser a que o equipamento produziu. "
                  u"Contorno automático sobre esta série sai deslocado, e sai "
                  u"plausível."))



def conferir(serie):
    arqs = serie.get("arquivos") or []
    achados, enc = [], {}
    if not arqs:
        return {"achados": [_achado(False, u"A série está vazia.")],
                "encontrado": {}, "pode_converter": False}

    primeiro = arqs[0]
    enc[u"Modalidade"] = serie.get("modalidade") or u"—"
    enc[u"Cortes"] = len(arqs)

    incompletos = [(k, a.get("pixel")) for k, a in enumerate(arqs)
                   if a.get("pixel")]
    if incompletos:
        porque = {
            PIXEL_TRUNCADO: u"o arquivo acaba antes do fim da imagem "
                            u"(truncado)",
            PIXEL_CURTO: u"a imagem tem menos bytes do que Rows × Columns "
                         u"pede",
            PIXEL_AUSENTE: u"o arquivo não tem a imagem (sem PixelData)"}
        onde = u"; ".join(u"corte %d: %s" % (k + 1, porque.get(m, m))
                          for k, m in incompletos[:3])
        if len(incompletos) > 3:
            onde += u"; e mais %d" % (len(incompletos) - 3)
        achados.append(_achado(
            False, u"%d corte(s) com a imagem incompleta no arquivo."
            % len(incompletos), onde,
            resolve=False, alerta=True, impede=True,
            o_que_faz=u"a conversão PARA: o corte incompleto chegaria ao TPS "
                      u"como imagem corrompida, e tirá-lo abriria um buraco "
                      u"na série. Copie ou exporte a série de novo da "
                      u"origem."))

    _saida = sintaxe_de_saida()
    _nome_saida = SINTAXES.get(_saida, (_saida, False))[0]
    sintaxes = sorted(set(a["sintaxe"] for a in arqs if a["sintaxe"]))
    if len(sintaxes) == 1:
        uid = sintaxes[0]
        nome, comprimida = SINTAXES.get(uid, (u"desconhecida", True))
        enc[u"Sintaxe de transferência"] = u"%s  (%s)" % (uid, nome)
        if comprimida:
            if _tem_decodificador(uid):
                achados.append(_achado(
                    False,
                    u"Sintaxe comprimida ou não nativa: %s." % nome,
                    u"O sistema de planejamento não importa comprimido.",
                    resolve=True,
                    o_que_faz=u"a conversão descomprime para %s (%s)"
                              % (_nome_saida, _saida)))
            else:
                achados.append(_achado(
                    False,
                    u"Este pacote não descomprime %s." % nome,
                    u"A sintaxe é válida — falta o decodificador NESTA "
                    u"instalação. Não é defeito da série.",
                    resolve=False, alerta=True, impede=True,
                    o_que_faz=u"a conversão PARA aqui. Para habilitar, o "
                              u"pacote precisa ser montado com o "
                              u"decodificador desta família — é troca de "
                              u"pacote, não opção de configuração. Fale com "
                              u"quem preparou a instalação."))
        else:
            achados.append(_achado(True, u"Sintaxe de transferência aceita "
                                         u"pelo TPS (%s)." % nome))
    elif len(sintaxes) > 1:
        enc[u"Sintaxe de transferência"] = u"%d diferentes na mesma série" % len(sintaxes)
        achados.append(_achado(
            False, u"A série tem %d sintaxes diferentes." % len(sintaxes),
            u"; ".join(SINTAXES.get(u, (u, True))[0] for u in sintaxes),
            resolve=True,
            o_que_faz=u"todas saem em %s — mas confira a origem: série com "
                      u"duas sintaxes costuma ter sido remontada de fontes "
                      u"diferentes" % _nome_saida))
    else:
        enc[u"Sintaxe de transferência"] = u"ausente"
        achados.append(_achado(
            False, u"Nenhum corte declara sintaxe de transferência.",
            u"Sem o `file_meta`, o arquivo não é DICOM válido (PS3.10 §7).",
            resolve=True, alerta=True,
            o_que_faz=u"a conversão lê assumindo Implicit VR Little Endian, "
                      u"que é o padrão de PS3.5 §10 — é SUPOSIÇÃO, e segue "
                      u"como alerta gravado no DICOM"))

    _laudo_inclinacao(arqs, enc, achados)

    esp = [a["espessura"] for a in arqs if a["espessura"]]
    if esp:
        enc[u"Espessura"] = (u"%.2f mm" % esp[0] if len(set(esp)) == 1
                             else u"varia: %.2f a %.2f mm" % (min(esp), max(esp)))
    pos = [a["pos"] for a in arqs if a["pos"] is not None]
    if len(pos) >= 2 and len(pos) == len(arqs):
        passos = [round(pos[i + 1] - pos[i], 4) for i in range(len(pos) - 1)]
        d_min, d_max = min(passos), max(passos)
        constante = (d_max - d_min) <= TOLERANCIA_ESPACO_MM
        enc[u"Espaçamento entre cortes"] = (
            u"%s mm · constante" % (u"%.2f" % d_min) if constante
            else u"%s a %s mm · IRREGULAR" % (u"%.2f" % d_min, u"%.2f" % d_max))
        if not constante:
            piores = sorted(range(len(passos)),
                            key=lambda i: -abs(passos[i] - d_min))[:3]
            onde = u"; ".join(
                u"cortes %d e %d (%.2f mm)" % (i + 1, i + 2, passos[i])
                for i in sorted(piores))
            achados.append(_achado(
                False, u"Espaçamento irregular entre os cortes.",
                u"%s — o resto da série está em %s mm." % (onde, u"%.2f" % d_min),
                resolve=False,
                o_que_faz=u"a conversão NÃO reamostra: reamostrar aqui "
                          u"inventaria corte que não foi adquirido. A série "
                          u"segue como veio, com o alerta gravado no DICOM — "
                          u"o TPS pode distorcer a reconstrução"))
        else:
            achados.append(_achado(True, u"Espaçamento constante (%s mm)."
                                   % (u"%.2f" % d_min)))
        repetidos = [i for i, d in enumerate(passos)
                     if abs(d) <= TOLERANCIA_ESPACO_MM]
        if repetidos:
            achados.append(_achado(
                False, u"%d corte(s) na mesma posição." % len(repetidos),
                u"a partir do corte %d" % (repetidos[0] + 1),
                resolve=False,
                o_que_faz=u"a conversão NÃO descarta duplicata: escolher qual "
                          u"corte fica não é dela. Os dois seguem, com o "
                          u"alerta gravado no DICOM"))
        desl = deslocamento_no_plano(arqs)
        if desl:
            achados.append(_achado(
                False, u"%d corte(s) deslocado(s) no plano: a origem "
                       u"(`ImagePositionPatient`) não segue a dos outros."
                % len(desl["fora"]),
                u"corte %d: %s mm fora da linha dos outros (tolerância de %s "
                u"mm)" % (desl["pior"] + 1, u"%.2f" % desl["mm"],
                          u"%.2f" % desl["tol"]),
                resolve=False,
                o_que_faz=u"a conversão NÃO corrige: corrigir é reamostrar. "
                          u"Cada corte segue na posição que declara, com o "
                          u"alerta gravado no DICOM — na fusão, esse corte "
                          u"aparece deslocado em relação aos vizinhos"))
    elif arqs:
        enc[u"Espaçamento entre cortes"] = u"não dá para calcular"
        _geo = geometria_assumida(serie)
        _sem_ipp = sum(1 for a in arqs if _ipp_de(a) is None)
        _iop_ruim = [_iop_de(a) for a in arqs
                     if _iop_de(a) is not None and not _iop_valida(_iop_de(a))]
        if _sem_ipp == len(arqs):
            _titulo = (u"Sem `ImagePositionPatient` — não dá para saber onde "
                       u"cada corte está.")
        elif _sem_ipp:
            _titulo = (u"`ImagePositionPatient` ausente em %d de %d cortes."
                       % (_sem_ipp, len(arqs)))
        elif _iop_ruim and len(_iop_ruim) == len(arqs) and all(
                not any(v) for v in _iop_ruim):
            _titulo = (u"`ImageOrientationPatient` toda zero — a orientação "
                       u"dos cortes não se lê.")
        elif _iop_ruim:
            _titulo = (u"`ImageOrientationPatient` inválida em %d de %d "
                       u"cortes: os dois vetores não formam um plano, e a "
                       u"orientação não se lê." % (len(_iop_ruim), len(arqs)))
        else:
            _titulo = (u"Sem `ImageOrientationPatient` — a orientação dos "
                       u"cortes não é declarada.")
        achados.append(_achado(
            False, _titulo,
            u"PS3.3 C.7.6.2. Sem ela, a série não tem geometria.",
            resolve=True, alerta=True,
            o_que_faz=u"a conversão ASSUME a geometria: %s. O TPS pode girar "
                      u"e transladar na fusão; a série sai com UID novo, para "
                      u"nunca se misturar com a original" % _geo["criterio"]))

    enc[u"Orientação do paciente"] = primeiro.get("orientacao") or u"—"
    slope, inter = primeiro.get("slope"), primeiro.get("intercept")
    if slope is None and inter is None:
        enc[u"Reescala (slope/intercept)"] = u"ausente"
        _mod = str(serie.get("modalidade") or primeiro.get("modalidade") or "").upper()
        _quantitativa = _mod in ("CT", "PT")
        achados.append(_achado(
            not _quantitativa,
            u"Sem `RescaleSlope`/`RescaleIntercept`.",
            (u"PS3.3 C.11.1 — sem elas o valor do pixel não vira Hounsfield."
             if _quantitativa else
             u"PS3.3 C.11.1. Em %s isso é o esperado: o valor do pixel não é "
             u"grandeza física e não há unidade para reescalar. Para fusão "
             u"não faz falta." % (_mod or u"série não quantitativa")),
            resolve=(True if _quantitativa else None),
            alerta=_quantitativa,
            o_que_faz=(u"a conversão grava RescaleSlope 1 e RescaleIntercept "
                       u"0, com RescaleType US: o número NÃO é Hounsfield. "
                       u"Numa CT isso costuma significar que a série não é de "
                       u"aquisição — confira a origem" if _quantitativa
                       else u"")))
    else:
        enc[u"Reescala (slope/intercept)"] = u"%s / %s" % (
            u"%g" % slope if slope is not None else u"—",
            u"%g" % inter if inter is not None else u"—")

    fr = sorted(set(a["frame_ref"] for a in arqs))
    sem_fr = sum(1 for a in arqs if not a["frame_ref"])
    if sem_fr:
        enc[u"Frame of Reference UID"] = u"ausente em %d corte(s)" % sem_fr
        achados.append(_achado(
            False, u"`FrameOfReferenceUID` ausente em %d corte(s)." % sem_fr,
            u"PS3.3 C.7.4.1 — sem ele o TPS não registra a série com nenhuma "
            u"outra.",
            resolve=True, alerta=True,
            o_que_faz=(u"a conversão grava um FrameOfReferenceUID NOVO por "
                       u"referencial de origem: os cortes que já tinham FoR "
                       u"diferentes continuam separados, e os sem FoR ganham "
                       u"um próprio — nenhum referencial comum é afirmado"
                       if len([x for x in fr if x]) > 1 else
                       u"a conversão grava um FrameOfReferenceUID NOVO, o "
                       u"mesmo em todos os cortes: a série passa a ser um "
                       u"referencial próprio, separado das outras do estudo, "
                       u"e a fusão com elas é registro, nunca uma afirmação "
                       u"sobre a aquisição")))
    elif len([x for x in fr if x]) > 1:
        enc[u"Frame of Reference UID"] = u"%d diferentes" % len(fr)
        achados.append(_achado(
            False, u"A série tem %d `FrameOfReferenceUID` diferentes." % len(fr),
            u"Isso quer dizer que ela junta aquisições que não compartilham "
            u"referencial.",
            resolve=False,
            o_que_faz=u"a conversão preserva, com o alerta gravado no DICOM"))
    else:
        enc[u"Frame of Reference UID"] = u"presente"

    formas = sorted(set((a["linhas"], a["colunas"]) for a in arqs))
    if len(formas) == 1 and formas[0][0]:
        enc[u"Matriz"] = u"%d × %d" % (int(formas[0][1]), int(formas[0][0]))
    elif len(formas) > 1:
        enc[u"Matriz"] = u"%d tamanhos diferentes" % len(formas)
        achados.append(_achado(
            False, u"Cortes com matrizes diferentes na mesma série.",
            u"; ".join(u"%sx%s" % (int(c or 0), int(l or 0)) for l, c in formas),
            resolve=False,
            o_que_faz=u"a conversão preserva. Um volume com matriz variável "
                      u"não é um volume — o alerta vai gravado no DICOM"))

    grades = [_grade_de(a) for a in arqs]
    ps = primeiro.get("pixel_spacing") or []
    if len(set(grades)) > 1:
        k = next(i for i, g in enumerate(grades) if g != grades[0])
        enc[u"Espaçamento no plano"] = u"varia: %d grades na série" % len(
            set(grades))
        achados.append(_achado(
            False, u"O `PixelSpacing` muda entre os cortes.",
            u"corte 1: %s; corte %d: %s — %d grades diferentes na série."
            % (_texto_da_grade(grades[0]), k + 1, _texto_da_grade(grades[k]),
               len(set(grades))),
            resolve=False,
            o_que_faz=u"a conversão NÃO reamostra: cada corte segue com a "
                      u"grade que trouxe, com o alerta gravado no DICOM. Um "
                      u"volume tem uma grade só: o TPS pode recusar a série "
                      u"ou montar fora de escala o corte de outra grade"))
    elif len(ps) >= 2 and ps[0]:
        enc[u"Espaçamento no plano"] = u"%.3f × %.3f mm" % (ps[0], ps[1])

    if primeiro.get("pos") is not None:
        enc[u"Posição do primeiro corte"] = u"%.2f mm" % primeiro["pos"]
    enc[u"Ordenado por"] = (u"posição no paciente"
                            if serie.get("ordenado_por") == "posicao"
                            else u"InstanceNumber (a posição não veio)")

    sops = [a["sop"] for a in arqs if a["sop"]]
    if len(sops) != len(set(sops)):
        achados.append(_achado(
            False, u"O mesmo `SOPInstanceUID` aparece mais de uma vez.",
            u"PS3.5 §10.1: o UID de instância é único. Repetido, é o MESMO "
            u"corte contado duas vezes.",
            resolve=False,
            o_que_faz=u"a conversão preserva os dois, com o alerta gravado "
                      u"no DICOM"))

    if serie.get("colorida"):
        foto = sorted(set(a.get("fotometrica") or u"" for a in arqs))
        enc[u"Cor"] = u", ".join(f for f in foto if f) or u"colorida"
        achados.append(_achado(
            False, u"Imagem colorida (%s)." % (enc[u"Cor"]),
            u"O Eclipse recusa SamplesPerPixel 3, e nenhum TPS funde imagem "
            u"colorida.",
            resolve=True, alerta=True,
            o_que_faz=u"a conversão grava em escala de cinza (MONOCHROME2, "
                      u"luminância), com UID novo: a cor se perde"))
    if serie.get("captura") and any(not a.get("conversao") for a in arqs):
        achados.append(_achado(
            False, u"Captura secundária sem `ConversionType`.",
            u"PS3.3 C.8.6.1: o ConversionType é obrigatório (Tipo 1) na "
            u"Secondary Capture.",
            resolve=True, alerta=False,
            o_que_faz=u"a conversão preenche ConversionType = %s"
                      % CONVERSAO_PADRAO))

    alertas = [a["titulo"] for a in achados if a.get("alerta")]
    return {"achados": achados, "encontrado": enc,
            "pode_converter": not any(a.get("impede") for a in achados),
            "resolvidos": sum(1 for a in achados if a["resolve"]),
            "precisam_decisao": 0,
            "alertas": alertas, "n_alertas": len(alertas),
            "ok": sum(1 for a in achados if a["ok"])}


def _ipp_de(a):
    v = [x for x in (a.get("ipp") or []) if x is not None]
    return [float(x) for x in v[:3]] if len(v) >= 3 else None


def _iop_de(a):
    v = [x for x in (a.get("iop") or []) if x is not None]
    return [float(x) for x in v[:6]] if len(v) >= 6 else None


def _grade_de(a):
    v = [x for x in (a.get("pixel_spacing") or []) if x is not None]
    return tuple(round(float(x), 4) for x in v[:2]) if len(v) >= 2 else ()


def _texto_da_grade(g):
    if len(g) < 2:
        return u"sem PixelSpacing"
    return u"%.3f × %.3f mm" % (g[0], g[1])


def _mediana(v):
    s = sorted(v)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2.0


def deslocamento_no_plano(arqs):
    pontos = []
    for a in arqs or ():
        ipp, iop = _ipp_de(a), _iop_de(a)
        if ipp is None or not _iop_valida(iop):
            return None
        pontos.append(ipp)
    if len(pontos) < 3:
        return None
    iop = _iop_de(arqs[0])
    r, c = iop[:3], iop[3:6]
    n = [r[1] * c[2] - r[2] * c[1], r[2] * c[0] - r[0] * c[2],
         r[0] * c[1] - r[1] * c[0]]

    def _dot(p, d):
        return p[0] * d[0] + p[1] * d[1] + p[2] * d[2]

    t = [_dot(p, n) for p in pontos]

    # GUARDA: reta pela mediana dos passos; o gantry inclinado desloca em linha e não é corte fora do lugar.
    def _resto(y):
        incl = [(y[k + 1] - y[k]) / (t[k + 1] - t[k])
                for k in range(len(t) - 1)
                if abs(t[k + 1] - t[k]) > TOLERANCIA_ESPACO_MM]
        b = _mediana(incl) if incl else 0.0
        a0 = _mediana([y[k] - b * t[k] for k in range(len(t))])
        return [y[k] - (a0 + b * t[k]) for k in range(len(t))]

    ru = _resto([_dot(p, r) for p in pontos])
    rv = _resto([_dot(p, c) for p in pontos])
    desvios = [(ru[k] ** 2 + rv[k] ** 2) ** 0.5 for k in range(len(t))]
    ps = [x for x in (arqs[0].get("pixel_spacing") or []) if x]
    tol = max(TOLERANCIA_ESPACO_MM,
              FRACAO_DE_PIXEL_NO_PLANO * (min(ps) if ps else 1.0))
    fora = [k for k, d in enumerate(desvios) if d > tol]
    if not fora:
        return None
    pior = max(fora, key=lambda k: desvios[k])
    return {"fora": fora, "pior": pior, "mm": desvios[pior], "tol": tol}


def geometria_assumida(serie):
    arqs = serie.get("arquivos") or []
    n = len(arqs)
    if not n:
        return {"ordem": [], "posicoes": [], "orientacao": [1, 0, 0, 0, 1, 0],
                "espacamento": [1.0, 1.0], "passo": 1.0, "criterio": u""}
    frases = []
    ipps = [_ipp_de(a) for a in arqs]
    iop = next((_iop_de(a) for a in arqs if _iop_valida(_iop_de(a))), None)
    if iop is None:
        iop = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        frases.append(u"orientação axial assumida")
    r = [float(x) for x in iop[:3]]
    c = [float(x) for x in iop[3:6]]
    nn = [r[1] * c[2] - r[2] * c[1], r[2] * c[0] - r[0] * c[2],
          r[0] * c[1] - r[1] * c[0]]

    def _proj(p):
        return p[0] * nn[0] + p[1] * nn[1] + p[2] * nn[2]

    com_ps = next((a for a in arqs if len(
        [x for x in (a.get("pixel_spacing") or []) if x]) >= 2), arqs[0])
    ps = [x for x in (com_ps.get("pixel_spacing") or []) if x]
    if len(ps) < 2:
        ps = [1.0, 1.0]
        frases.append(u"pixel de 1 mm assumido")

    if all(p is not None for p in ipps):
        ordem = sorted(range(n), key=lambda i: _proj(ipps[i]))
        zs = [_proj(ipps[i]) for i in ordem]
        passos = sorted(abs(zs[k + 1] - zs[k]) for k in range(n - 1))
        passo = None
        if passos and passos[len(passos) // 2] > 0:
            passo = passos[len(passos) // 2]
        frases.append(u"posição medida de cada corte (ImagePositionPatient), "
                      u"ordem pela projeção na normal do plano")
        return {"ordem": ordem, "posicoes": [list(ipps[i]) for i in ordem],
                "orientacao": [float(x) for x in iop[:6]],
                "espacamento": [float(ps[0]), float(ps[1])],
                "passo": passo, "criterio": u"; ".join(frases)}

    locais = [a.get("local") for a in arqs]
    if all(x is not None for x in locais) and len(set(locais)) == n:
        ordem = sorted(range(n), key=lambda i: locais[i])
        frases.append(u"ordem e distância entre cortes pelo SliceLocation")
    else:
        ordem = list(range(n))
        frases.append(u"ordem pelo InstanceNumber" if serie.get(
            "ordenado_por") == "instancia" else u"ordem do arquivo")
        locais = None
    primeiro = arqs[ordem[0]]
    if locais is None:
        passo = primeiro.get("entre") or primeiro.get("espessura")
        if passo:
            frases.append(u"distância entre cortes de %.2f mm pelo %s" % (
                float(passo), u"SpacingBetweenSlices" if primeiro.get("entre")
                else u"SliceThickness"))
        else:
            passo = 1.0
            frases.append(u"distância entre cortes de 1 mm assumida")
        t = [k * float(passo) for k in range(n)]
    else:
        passo = None
        t = [float(locais[i]) for i in ordem]

    medidos = [k for k, i in enumerate(ordem) if ipps[i] is not None]
    posicoes = []
    if medidos:
        direcao = list(nn)
        if len(medidos) >= 2 and t[medidos[-1]] != t[medidos[0]]:
            a = ipps[ordem[medidos[0]]]
            b = ipps[ordem[medidos[-1]]]
            dt = t[medidos[-1]] - t[medidos[0]]
            direcao = [(b[j] - a[j]) / dt for j in range(3)]
        for k, i in enumerate(ordem):
            if ipps[i] is not None:
                posicoes.append(list(ipps[i]))
                continue
            kr = min(medidos, key=lambda m: abs(m - k))
            ref = ipps[ordem[kr]]
            posicoes.append([ref[j] + (t[k] - t[kr]) * direcao[j]
                             for j in range(3)])
        if len(medidos) >= 2:
            frases.append(u"posição medida em %d de %d cortes; os outros "
                          u"pela reta entre os medidos" % (len(medidos), n))
        else:
            frases.append(u"posição medida em 1 de %d cortes; os outros a "
                          u"partir dele, pela normal do plano" % n)
    else:
        kc = max(0, n // 2)
        linhas = float(primeiro.get("linhas") or 1)
        colunas = float(primeiro.get("colunas") or 1)
        a_col = (colunas - 1.0) / 2.0 * float(ps[1])
        a_lin = (linhas - 1.0) / 2.0 * float(ps[0])
        for k, i in enumerate(ordem):
            z = t[k] - t[kc]
            posicoes.append([-a_col * r[j] - a_lin * c[j] + z * nn[j]
                             for j in range(3)])
        frases.append(u"origem no centro geométrico do corte central")
    return {"ordem": ordem, "posicoes": posicoes,
            "orientacao": [float(x) for x in iop[:6]],
            "espacamento": [float(ps[0]), float(ps[1])],
            "passo": passo, "criterio": u"; ".join(frases)}


class Recusa(Exception):
    pass


_ELEMENTOS_DE_COR = (0x00280006, 0x00281101, 0x00281102, 0x00281103,
                     0x00281199, 0x00281201, 0x00281202, 0x00281203,
                     0x00281221, 0x00281222, 0x00281223)


def _uid_derivado(uid, papel):
    from pydicom.uid import generate_uid
    return str(generate_uid(entropy_srcs=[str(uid or ""), u"radai-dicombridge",
                                          str(papel)]))


def _frames_novos(uid, arqs):
    originais = set(str(a.get("frame_ref") or "") for a in arqs)
    presentes = set(f for f in originais if f)
    if len(presentes) <= 1:
        novo = _uid_derivado(uid, "for")
        return dict((f, novo) for f in originais)
    return dict((f, _uid_derivado(uid + "|" + f, "for")) for f in originais)


def _plano_de_saida(serie, laudo):
    arqs = serie.get("arquivos") or []
    uid = str(serie.get("uid") or "")
    sem_pos = any(a.get("pos") is None for a in arqs)
    geo = geometria_assumida(serie) if sem_pos else None
    colorida = bool(serie.get("colorida"))
    mod = str(serie.get("modalidade") or "").upper()
    sem_reescala = (mod in ("CT", "PT") and all(
        a.get("slope") is None and a.get("intercept") is None for a in arqs))
    sem_for = any(not a.get("frame_ref") for a in arqs)
    motivos = []
    if geo is not None:
        motivos.append(u"geometria assumida")
    if colorida:
        motivos.append(u"cor convertida para escala de cinza")
    derivada = bool(motivos)
    alertas = [a for a in (laudo or {}).get("achados") or ()
               if a.get("alerta")]
    textos = [_ascii(u"%s %s" % (a["titulo"], a.get("o_que_faz") or u""))
              for a in alertas]
    return {
        "ordem": geo["ordem"] if geo else list(range(len(arqs))),
        "geometria": geo,
        "colorida": colorida,
        "sem_reescala": sem_reescala,
        "frame_novo": (_frames_novos(uid, arqs) if (sem_for or geo)
                       else None),
        "derivada": derivada,
        "serie_uid": _uid_derivado(uid, "serie") if derivada else uid,
        "uid_regerado": u"; ".join(motivos),
        "captura": bool(serie.get("captura")),
        "n_alertas": len(alertas),
        "comentario": (u"Radioterapia.AI DicomBridge - %d alerta(s): %s"
                       % (len(alertas), u" | ".join(
                           u"%d) %s" % (j + 1, t)
                           for j, t in enumerate(textos))))[:10000]
                      if alertas else u"",
    }


def _para_cinza(ds):
    import numpy as np
    foto = str(getattr(ds, "PhotometricInterpretation", "") or "").upper()
    arr = ds.pixel_array
    if foto.startswith("PALETTE"):
        from pydicom.pixels import apply_color_lut
        arr = apply_color_lut(arr, ds)
    arr = np.asarray(arr)
    if arr.shape[-1] == 3 and int(getattr(ds, "SamplesPerPixel", 1) or 1) > 1 \
            or foto.startswith("PALETTE"):
        rgb = arr.astype(np.float32)
        topo = float(rgb.max()) if rgb.size else 0.0
        if topo > 255.0:
            rgb = rgb * (255.0 / (65535.0 if topo > 4095.0 else 4095.0))
        y = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])
        arr = y
    cinza = np.clip(np.rint(arr), 0, 255).astype(np.uint8)
    for tag in _ELEMENTOS_DE_COR:
        if tag in ds:
            del ds[tag]
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    if "WindowCenter" not in ds:
        ds.WindowCenter = 128
        ds.WindowWidth = 256
    ds.PixelData = np.ascontiguousarray(cinza).tobytes()


def _aplicar_plano(ds, plano, i):
    if plano["colorida"]:
        _para_cinza(ds)
    if plano["captura"] and not str(getattr(ds, "ConversionType", "") or ""):
        ds.ConversionType = CONVERSAO_PADRAO
    if plano["sem_reescala"]:
        ds.RescaleSlope = 1
        ds.RescaleIntercept = 0
        ds.RescaleType = "US"
    if plano["frame_novo"]:
        mapa = plano["frame_novo"]
        velho_for = str(getattr(ds, "FrameOfReferenceUID", "") or "")
        ds.FrameOfReferenceUID = mapa.get(
            velho_for, mapa.get("") or next(iter(mapa.values())))
    geo = plano["geometria"]
    if geo is not None:
        if not _iop_valida(getattr(ds, "ImageOrientationPatient", None)):
            ds.ImageOrientationPatient = list(geo["orientacao"])
        if len(getattr(ds, "ImagePositionPatient", None) or []) < 3:
            ds.ImagePositionPatient = [round(float(x), 6)
                                       for x in geo["posicoes"][i]]
        if not getattr(ds, "PixelSpacing", None):
            ds.PixelSpacing = list(geo["espacamento"])
        if geo.get("passo") and not getattr(ds, "SliceThickness", None):
            ds.SliceThickness = float(geo["passo"])
    if plano["derivada"]:
        velho = str(getattr(ds, "SOPInstanceUID", "") or "%d" % i)
        ds.SeriesInstanceUID = plano["serie_uid"]
        ds.SOPInstanceUID = _uid_derivado(velho, "sop")
        tipo = list(getattr(ds, "ImageType", None) or ["ORIGINAL", "PRIMARY"])
        tipo[0] = "DERIVED"
        if len(tipo) > 1:
            tipo[1] = "SECONDARY"
        ds.ImageType = tipo
        ds.DerivationDescription = _ascii(
            u"Radioterapia.AI DicomBridge: %s. Nao usar para calculo de dose "
            u"sem conferir." % plano["uid_regerado"])[:1024]
    if plano["n_alertas"]:
        desc = _ascii(str(getattr(ds, "SeriesDescription", "") or ""))
        ds.SeriesDescription = (u"[%d ALERTA%s] %s" % (
            plano["n_alertas"], u"S" if plano["n_alertas"] > 1 else u"",
            desc)).strip()[:64]
        ds.ImageComments = plano["comentario"]
    meta = getattr(ds, "file_meta", None)
    if meta is None:
        from pydicom.dataset import FileMetaDataset
        meta = ds.file_meta = FileMetaDataset()
    if getattr(ds, "SOPClassUID", None):
        meta.MediaStorageSOPClassUID = ds.SOPClassUID
    if getattr(ds, "SOPInstanceUID", None):
        meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID


def _gravar_na_sintaxe(ds, saida, sintaxe):
    from pydicom.uid import UID
    ds.file_meta.TransferSyntaxUID = UID(sintaxe)
    ds.save_as(saida, enforce_file_format=True,
               implicit_vr=(sintaxe == SINTAXE_IMPLICITA), little_endian=True)


def converter(serie, destino, laudo=None, aceitar=None, log=None,
              quem=u"", renomeados=None, tps=None):
    import pydicom
    from pydicom.uid import ExplicitVRLittleEndian

    def _diz(m):
        if log:
            try:
                log(m)
            except Exception:
                pass

    laudo = laudo or conferir(serie)
    aceitos = set(aceitar or ())

    impedem = [a for a in laudo["achados"] if a.get("impede")]
    if impedem:
        raise Recusa(
            u"a conversao nao e possivel: %s"
            % u" | ".join(a["titulo"] for a in impedem))
    alertas = [a for a in laudo["achados"] if a.get("alerta")]
    sintaxe = sintaxe_de_saida(tps)

    try:
        import radai_archive
        _nuvem, _motivo = radai_archive.em_pasta_sincronizada(destino)
    except Exception as _e:
        _nuvem, _motivo = False, u""
        if log:
            try:
                log(u"nao consegui conferir se o destino sincroniza (%s) — "
                    u"vou gravar assim mesmo" % str(_e)[:120])
            except Exception:
                pass
    if _nuvem:
        raise Recusa(
            u"o destino sincroniza com a nuvem (%s). A serie convertida leva "
            u"nome, registro e nascimento do paciente em cada corte — escolha "
            u"uma pasta fora dessa raiz." % (_motivo or u"raiz espelhada"))

    arqs = serie.get("arquivos") or []
    if not arqs:
        raise Recusa(u"a serie esta vazia")
    # GUARDA: o corte incompleto não chega ao destino, nem com laudo que não o acusa.
    _incompletos = [k for k, a in enumerate(arqs) if a.get("pixel")]
    if _incompletos:
        raise Recusa(
            u"%d corte(s) com a imagem incompleta no arquivo (o primeiro e o "
            u"corte %d): nada foi gravado. Copie ou exporte a serie de novo "
            u"da origem." % (len(_incompletos), _incompletos[0] + 1))

    _pastas = set()
    for _a in arqs:
        try:
            _pastas.add(os.path.dirname(os.path.realpath(str(_a["caminho"]))))
        except Exception:
            pass
    if _pastas:
        try:
            _d = os.path.realpath(destino)
            _dentro = any((_d == _o or _d.startswith(_o + os.sep))
                          and not any(pasta_pulada(p) for p in
                                      os.path.relpath(_d, _o).split(os.sep))
                          for _o in _pastas)
        except Exception:
            _dentro = False
        if _dentro:
            raise Recusa(
                u"o destino fica DENTRO da pasta da série de origem. A "
                u"conversão preserva o `SeriesInstanceUID`, então os cortes "
                u"convertidos voltariam como parte da MESMA série — a série "
                u"passaria a ter o dobro de cortes, com posições repetidas, e "
                u"a partir daí nem esta nem outra conversão dela funcionaria. "
                u"Escolha uma pasta fora da árvore do exame.")

    os.makedirs(destino, exist_ok=True)

    plano = _plano_de_saida(serie, laudo)

    velhos = [os.path.join(destino, f) for f in os.listdir(destino)
              if f.lower().endswith(".dcm")]
    meu_uid = plano["serie_uid"]
    outra = None
    for v in velhos:
        try:
            d = pydicom.dcmread(v, stop_before_pixels=True, force=True)
            u = str(getattr(d, "SeriesInstanceUID", "") or "")
        except Exception:
            u = u""
        if u and meu_uid and u != meu_uid:
            outra = (v, u)
            break
    if outra is not None:
        raise Recusa(
            u"a pasta de destino ja tem OUTRA serie dentro (%d arquivo(s), "
            u"começando por %s). Duas series na mesma pasta se "
            u"sobrescrevem pelo nome, e a conferência da segunda contaria "
            u"os arquivos da primeira junto. Escolha uma pasta vazia, ou "
            u"marque as duas series e use «Converter as marcadas», que cria "
            u"uma subpasta por série."
            % (len(velhos), os.path.basename(outra[0])))
    for v in velhos:
        try:
            os.remove(v)
        except Exception:
            pass

    escritos, erros = [], []
    for i, k in enumerate(plano["ordem"]):
        a = arqs[k]
        try:
            ds = pydicom.dcmread(a["caminho"], force=True)
            sint = str(getattr(getattr(ds, "file_meta", None),
                               "TransferSyntaxUID", "") or "")
            _nome, comprimida = SINTAXES.get(sint, (u"?", bool(sint)))
            try:
                from pydicom.uid import UID as _UID
                if sint in SINTAXES:
                    comprimida = bool(_UID(sint).is_compressed)
            except Exception:
                pass
            if comprimida:
                ds.decompress(generate_instance_uid=False)
            try:
                era_be = (str(sint) == "1.2.840.10008.1.2.2")
            except Exception:
                era_be = False
            if era_be:
                try:
                    arr = ds.pixel_array
                    ds.PixelData = arr.astype(
                        arr.dtype.newbyteorder("<")).tobytes()
                    ds.set_original_encoding(False, True)
                except Exception as _e:
                    raise ValueError(
                        u"nao consegui reordenar os bytes do Big "
                        u"Endian: %s" % _e)
            _falta = _pixel_incompleto(ds)
            if _falta:
                raise ValueError(_falta)
            _aplicar_plano(ds, plano, i)
            saida = os.path.join(destino, "IM%05d.dcm" % i)
            _gravar_na_sintaxe(ds, saida, sintaxe)
            escritos.append(saida)
        except Exception as e:
            erros.append((os.path.basename(a["caminho"]),
                          u"%s: %s" % (type(e).__name__, str(e)[:120])))

    if erros:
        for x in escritos:
            try:
                os.remove(x)
            except Exception:
                pass
        raise Recusa(
            u"%d de %d corte(s) nao converteram, e a pasta de destino foi "
            u"limpa: meia serie e pior que nenhuma, porque o TPS importa a "
            u"metade sem reclamar. %s"
            % (len(erros), len(arqs),
               u" | ".join(u"%s (%s)" % e for e in erros[:3])))

    n_saida = len([f for f in os.listdir(destino) if f.lower().endswith(".dcm")])
    if n_saida != len(arqs):
        for x in escritos:
            try:
                os.remove(x)
            except Exception:
                pass
        raise Recusa(
            u"a saida tem %d corte(s) e a entrada tinha %d. A pasta NAO esta "
            u"confiavel, e o que esta conversao gravou foi apagado."
            % (n_saida, len(arqs)))

    _diz(u"convertida: %d corte(s) em %s, %d alerta(s)"
         % (n_saida, SINTAXES.get(sintaxe, (sintaxe, False))[0],
            len(alertas)))
    r = {"destino": destino, "cortes": n_saida,
         "sintaxe": sintaxe,
         "uid_preservado": ("" if plano["uid_regerado"]
                            else serie.get("uid", "")),
         "uid_regerado": plano["uid_regerado"],
         "alertas": [a["titulo"] for a in alertas],
         "aceitos": sorted(aceitos),
         "conferido": u"%d de entrada, %d gravados, contados no disco"
                      % (len(arqs), n_saida)}

    entrada = recibo(serie, r, laudo=laudo, aceitos=sorted(aceitos),
                     quem=quem, renomeados=renomeados, destino=destino)
    r["recibo"] = entrada
    r["recibo_arquivo"] = gravar_recibo(entrada, destino, log=log)
    return r


NOME_RECIBO = "recibo_conversao.json"
VERSAO_RECIBO = 1


def _agora_local():
    from datetime import datetime
    return datetime.now().astimezone().isoformat(timespec="seconds")


def recibo(serie, resultado, laudo=None, aceitos=None, quem=u"",
           renomeados=None, destino=None):
    laudo = laudo or {}
    achados = laudo.get("achados") or []
    resolvidos = [a["titulo"] for a in achados
                  if (not a.get("ok")) and a.get("resolve") is True]
    aceitos = sorted(set(aceitos or resultado.get("aceitos") or ()))
    return {
        "versao_recibo": VERSAO_RECIBO,
        "quando": _agora_local(),
        "maquina": os.environ.get("COMPUTERNAME", ""),
        "quem": str(quem or "")[:80],
        "serie": {
            "uid8": str(serie.get("uid") or "")[-8:],
            "modalidade": serie.get("modalidade") or "",
            "cortes": int(serie.get("cortes") or 0),
        },
        "origem": {"sintaxe": _sintaxe_da_serie(serie)},
        "destino": {"sintaxe": resultado.get("sintaxe") or SINTAXE_DESTINO},
        "resolvidos": resolvidos,
        "alertas": list(resultado.get("alertas") or ()),
        "uid_regerado": resultado.get("uid_regerado") or u"",
        "aceitos": aceitos,
        "renomeados": list(renomeados or ()),
        "conferido": resultado.get("conferido") or "",
    }


def _sintaxe_da_serie(serie):
    arqs = serie.get("arquivos") or []
    return str((arqs[0].get("sintaxe") if arqs else "") or "")


def gravar_recibo(entrada, destino, log=None):
    import json
    caminho = ""
    try:
        pasta = os.path.join(destino, "_RadAI")
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, NOME_RECIBO)
        antigos = []
        if os.path.exists(caminho):
            try:
                with open(caminho, encoding="utf-8") as f:
                    d = json.load(f)
                antigos = d if isinstance(d, list) else [d]
            except Exception:
                try:
                    os.replace(caminho, caminho + ".ilegivel")
                except Exception:
                    pass
        antigos.append(entrada)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(antigos, f, ensure_ascii=False, indent=1)
        if log:
            log(u"recibo: %s · %d aceite(s) · %s"
                % (entrada.get("quando"), len(entrada.get("aceitos") or ()),
                   os.path.join("_RadAI", NOME_RECIBO)))
    except Exception as e:
        if log:
            log(u"nao consegui gravar o recibo (%s) — a conversao ESTA feita"
                % type(e).__name__)
    return caminho
