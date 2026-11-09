# -*- coding: utf-8 -*-
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
_cleanup.adotar_prefixo('radai_conv_')

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "app"))
os.environ.setdefault("RADAI_CALIB_DIR",
                      tempfile.mkdtemp(prefix="radai_conv_acervo_"))

_ok = 0
_falhou = 0
_pulados = []
_falhas = []


def secao(t):
    print(u"")
    print(u"── %s %s" % (t, u"─" * max(0, 60 - len(t))))


def checar(rotulo, cond, detalhe=u""):
    global _ok, _falhou
    if cond:
        _ok += 1
        print(u"  OK     %s" % rotulo)
    else:
        _falhou += 1
        _falhas.append(rotulo)
        print(u"  FALHA  %s  %s" % (rotulo, str(detalhe).replace("\n", " | ")[:150]))


def pular(rotulo, porque):
    _pulados.append((rotulo, porque))
    print(u"  PULA   %s  — %s" % (rotulo, porque))


def _corte(uid_serie, uid_estudo, i, n, *, bits=16, sinal=1,
           foto="MONOCHROME2", espaco=(0.7, 0.7), espessura=2.0,
           fabricante="Canon Medical Systems", modelo="Aquilion Lightning",
           orientacao=True, privada=False, multivalor=False):
    import numpy as np
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    d = Dataset()
    d.file_meta = FileMetaDataset()
    d.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    d.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    sop = generate_uid()
    d.file_meta.MediaStorageSOPInstanceUID = sop
    d.file_meta.ImplementationClassUID = generate_uid()

    d.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    d.SOPInstanceUID = sop
    d.SeriesInstanceUID = uid_serie
    d.StudyInstanceUID = uid_estudo
    d.FrameOfReferenceUID = uid_estudo
    d.PatientID = "FANTOMA_CONV"
    d.PatientName = "FANTOMA^CONV"
    d.Modality = "CT"
    d.SeriesNumber = 2
    d.InstanceNumber = i + 1
    d.SeriesDate = "20260830"
    d.SeriesDescription = "PELVE"
    d.Manufacturer = fabricante
    d.ManufacturerModelName = modelo

    d.Rows = d.Columns = 48
    d.BitsAllocated = 16 if bits > 8 else 8
    d.BitsStored = bits
    d.HighBit = bits - 1
    d.PixelRepresentation = sinal
    d.SamplesPerPixel = 1
    d.PhotometricInterpretation = foto
    d.RescaleSlope = 1
    d.RescaleIntercept = -1024

    if espaco:
        d.PixelSpacing = [str(espaco[0]), str(espaco[1])]
    if espessura is not None:
        d.SliceThickness = str(espessura)
    if orientacao:
        d.ImageOrientationPatient = ["1", "0", "0", "0", "1", "0"]
    d.ImagePositionPatient = ["-100.0", "-100.0", "%.2f" % (i * (espessura or 2.0))]

    if multivalor:
        d.ConvolutionKernel = ["FC08", "FC18"]
    else:
        d.ConvolutionKernel = "FC08"

    if privada:
        bloco = d.private_block(0x0029, "SIEMENS CSA HEADER", create=True)
        bloco.add_new(0x10, "OB", b"\x00\x01\x02\x03" * 16)

    tipo = np.int16 if sinal else np.uint16
    if d.BitsAllocated == 8:
        tipo = np.int8 if sinal else np.uint8
    teto = (1 << (bits - (1 if sinal else 0))) - 1
    a = np.zeros((48, 48), dtype=tipo)
    a[8:40, 8:40] = min(400, teto)
    a[20:28, 20:28] = min(1000, teto)
    a[i % 40, :] = min(300, teto)
    d.PixelData = a.tobytes()
    return d, a


def escrever(pasta, n=6, sintaxe=None, sem_preambulo=False, **kw):
    import pydicom
    from pydicom.uid import generate_uid

    os.makedirs(pasta, exist_ok=True)
    us, ue = generate_uid(), generate_uid()
    arrays = []
    for i in range(n):
        d, a = _corte(us, ue, i, n, **kw)
        if sintaxe:
            _aplicar_sintaxe(d, sintaxe)
        alvo = os.path.join(pasta, "IM%05d.dcm" % i)
        d.save_as(alvo, enforce_file_format=not sem_preambulo)
        if sem_preambulo:
            _tirar_preambulo(alvo)
        arrays.append(a)
    return arrays


def _aplicar_sintaxe(d, uid):
    from pydicom.uid import (ImplicitVRLittleEndian, ExplicitVRLittleEndian,
                             DeflatedExplicitVRLittleEndian,
                             ExplicitVRBigEndian)
    cruas = {str(ImplicitVRLittleEndian), str(ExplicitVRLittleEndian),
             str(DeflatedExplicitVRLittleEndian), str(ExplicitVRBigEndian)}
    if str(uid) in cruas:
        if str(uid) == str(ExplicitVRBigEndian):
            import numpy as np
            arr = d.pixel_array
            d.PixelData = arr.astype(arr.dtype.newbyteorder(">")).tobytes()
            d.set_original_encoding(False, False)
        d.file_meta.TransferSyntaxUID = uid
        return
    d.compress(uid)


def _tirar_preambulo(caminho):
    bruto = io.open(caminho, "rb").read()
    if bruto[128:132] == b"DICM":
        io.open(caminho, "wb").write(bruto[132:])


def _series(origem):
    import radai_dicom as D
    return (D.varrer(origem) or {}).get("series") or []


def _converter(origem, destino):
    import radai_dicom as D
    ss = _series(origem)
    if not ss:
        return None, u"a varredura nao achou serie nenhuma"
    try:
        return D.converter(ss[0], destino), u""
    except Exception as e:
        return None, u"%s: %s" % (type(e).__name__, str(e)[:120])


def teste_sintaxes():
    from pydicom.uid import (ImplicitVRLittleEndian, ExplicitVRLittleEndian,
                             DeflatedExplicitVRLittleEndian,
                             ExplicitVRBigEndian, RLELossless,
                             JPEGLSLossless, JPEG2000Lossless,
                             JPEGLosslessSV1)
    import pydicom
    secao(u"as sintaxes: entram diferentes, saem Implicit VR Little Endian "
          u"(nos dois TPS)")

    casos = [
        (u"Implicit VR LE (a mais comum em aparelho antigo)", ImplicitVRLittleEndian),
        (u"Explicit VR LE (o proprio destino)", ExplicitVRLittleEndian),
        (u"Deflated Explicit VR LE", DeflatedExplicitVRLittleEndian),
        (u"Explicit VR Big Endian (aposentada, e existe em campo)", ExplicitVRBigEndian),
        (u"RLE Lossless", RLELossless),
        (u"JPEG-LS sem perda", JPEGLSLossless),
        (u"JPEG 2000 sem perda", JPEG2000Lossless),
        (u"JPEG Lossless SV1 (o do Canon do servico)", JPEGLosslessSV1),
    ]
    base = tempfile.mkdtemp(prefix="radai_conv_sint_")
    try:
        for rotulo, uid in casos:
            org = os.path.join(base, "org_%s" % str(uid).replace(".", "_"))
            dst = os.path.join(base, "dst_%s" % str(uid).replace(".", "_"))
            try:
                arrays = escrever(org, n=5, sintaxe=uid)
            except Exception as e:
                pular(rotulo, u"sem codificador aqui (%s)"
                      % str(e).split(":")[0][:48])
                continue
            try:
                laudo, erro = _converter(org, dst)
            except Exception as e:
                checar(rotulo, False, u"%s: %s" % (type(e).__name__, e))
                continue
            if erro:
                checar(rotulo, False, erro)
                continue
            saiu = (sorted(f for f in os.listdir(dst)
                           if f.lower().endswith(".dcm"))
                    if os.path.isdir(dst) else [])
            ok = len(saiu) == len(arrays)
            checar(u"%s: %d cortes entram, %d saem" % (rotulo, len(arrays), len(saiu)),
                   ok, u"%s" % (laudo or erro))
            if not saiu:
                continue
            d = pydicom.dcmread(os.path.join(dst, saiu[0]))
            checar(u"  ...e a saida e Implicit VR LE",
                   str(d.file_meta.TransferSyntaxUID) == str(ImplicitVRLittleEndian)
                   and d.is_implicit_VR and d.is_little_endian,
                   str(d.file_meta.TransferSyntaxUID))
            if uid == ExplicitVRLittleEndian:
                import radai_dicom as D
                por_tps = {}
                for tps in (u"eclipse", u"monaco"):
                    dt = os.path.join(base, "dst_%s" % tps)
                    try:
                        D.converter(_series(org)[0], dt, tps=tps)
                        n1 = sorted(f for f in os.listdir(dt)
                                    if f.lower().endswith(".dcm"))[0]
                        por_tps[tps] = str(pydicom.dcmread(os.path.join(
                            dt, n1)).file_meta.TransferSyntaxUID)
                    except Exception as e:
                        por_tps[tps] = u"%s: %s" % (type(e).__name__, e)
                checar(u"  ...e com Eclipse / Monaco ou com Xio / Focal a "
                       u"sintaxe e a mesma, Implicit VR LE",
                       por_tps == {u"eclipse": str(ImplicitVRLittleEndian),
                                   u"monaco": str(ImplicitVRLittleEndian)},
                       str(por_tps))
            try:
                import numpy as np
                igual = np.array_equal(d.pixel_array, arrays[0])
                checar(u"  ...e o pixel sobrevive intacto", igual,
                       u"o conteudo mudou na conversao")
            except Exception as e:
                pular(u"  o pixel de %s" % rotulo,
                      u"sem decodificador aqui (%s)" % str(e)[:44])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_variacoes_do_aparelho():
    import pydicom
    secao(u"o que varia entre aparelhos, do recente ao obsoleto")

    casos = [
        (u"16 bits com sinal (o normal em TC)", dict(bits=16, sinal=1)),
        (u"16 bits SEM sinal", dict(bits=16, sinal=0)),
        (u"12 bits armazenados em 16", dict(bits=12, sinal=0)),
        (u"MONOCHROME1 (branco invertido, aparelho antigo)",
         dict(foto="MONOCHROME1")),
        (u"sem PixelSpacing (o TPS precisa saber, e ele nao tem)",
         dict(espaco=None)),
        (u"sem SliceThickness", dict(espessura=None)),
        (u"sem ImageOrientationPatient", dict(orientacao=False)),
        (u"com tag privada de fabricante", dict(privada=True)),
        (u"ConvolutionKernel multivalorado", dict(multivalor=True)),
        (u"GE Discovery de 2006", dict(fabricante="GE MEDICAL SYSTEMS",
                                       modelo="Discovery ST")),
        (u"Siemens Somatom de 2009", dict(fabricante="SIEMENS",
                                          modelo="Sensation 64")),
        (u"Philips Brilliance", dict(fabricante="Philips",
                                     modelo="Brilliance 64")),
        (u"Toshiba (antes de virar Canon)", dict(fabricante="TOSHIBA",
                                                 modelo="Aquilion ONE")),
    ]
    base = tempfile.mkdtemp(prefix="radai_conv_var_")
    try:
        for rotulo, kw in casos:
            org = os.path.join(base, "o_%d" % len(os.listdir(base)))
            dst = org + "_d"
            try:
                arrays = escrever(org, n=5, **kw)
                laudo, erro = _converter(org, dst)
            except Exception as e:
                checar(rotulo, False, u"%s: %s" % (type(e).__name__, e))
                continue
            saiu = sorted(f for f in os.listdir(dst)
                          if f.lower().endswith(".dcm")) if os.path.isdir(dst) else []
            checar(u"%s: converte ou recusa, sem meia serie" % rotulo,
                   len(saiu) in (0, len(arrays)),
                   u"%d de %d gravados" % (len(saiu), len(arrays)))
            if saiu:
                d = pydicom.dcmread(os.path.join(dst, saiu[0]))
                checar(u"  ...e o que saiu tem a geometria que entrou",
                       hasattr(d, "ImagePositionPatient"),
                       u"posicao perdida na conversao")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_dicom_de_cd():
    secao(u"o DICOM de CD: sem preambulo e sem extensao")
    import radai_dicom as D

    base = tempfile.mkdtemp(prefix="radai_conv_cd_")
    try:
        org = os.path.join(base, "DICOMDIR_FAKE")
        escrever(org, n=5, sem_preambulo=True)
        for f in sorted(os.listdir(org)):
            os.rename(os.path.join(org, f),
                      os.path.join(org, f.replace(".dcm", "")))
        arqs = sorted(os.listdir(org))
        vale, porque = D.vale_abrir(os.path.join(org, arqs[0]))
        checar(u"o sniff aceita DICOM sem preambulo", vale, porque)
        series = _series(org)
        checar(u"e a varredura acha a serie",
               len(series) == 1 and series[0]["cortes"] == 5,
               u"%s" % [(x["cortes"]) for x in series])

        dst = os.path.join(base, "saida")
        laudo, erro = _converter(org, dst)
        saiu = [f for f in os.listdir(dst)] if os.path.isdir(dst) else []
        checar(u"e a conversao entrega os 5 cortes",
               len([f for f in saiu if f.lower().endswith(".dcm")]) == 5,
               u"%s | %s" % (erro, saiu[:4]))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_o_que_nao_e_dicom():
    secao(u"o que NAO e' DICOM, e nao pode custar minutos")
    import radai_dicom as D
    import time

    base = tempfile.mkdtemp(prefix="radai_conv_lixo_")
    try:
        org = os.path.join(base, "misturado")
        escrever(org, n=5)
        for nome, tam in (("app.dll", 400000), ("log.etl", 200000),
                          ("estudo.zip", 300000), ("cor.dds", 120000),
                          ("leia.txt", 2000)):
            io.open(os.path.join(org, nome), "wb").write(os.urandom(tam))
        t0 = time.time()
        series = _series(org)
        dt = time.time() - t0
        checar(u"a serie e' achada no meio do lixo",
               len(series) == 1 and series[0]["cortes"] == 5,
               u"%s" % [(x["cortes"]) for x in series])
        checar(u"e a varredura e' rapida (< 5 s)", dt < 5.0, u"%.2f s" % dt)
        for nome in ("app.dll", "log.etl", "cor.dds"):
            vale, _p = D.vale_abrir(os.path.join(org, nome))
            checar(u"  %s e' recusado antes de abrir" % nome, not vale)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_o_destino_nao_destroi():
    secao(u"o destino: converter duas vezes nao destroi a primeira")
    import radai_dicom as D

    base = tempfile.mkdtemp(prefix="radai_conv_dst_")
    try:
        a = os.path.join(base, "serie_a")
        b = os.path.join(base, "serie_b")
        escrever(a, n=5)
        escrever(b, n=7)
        dst = os.path.join(base, "destino")
        _converter(a, dst)
        n1 = len([f for f in os.listdir(dst) if f.lower().endswith(".dcm")])
        checar(u"a primeira gravou", n1 == 5, u"%d" % n1)
        laudo, erro = _converter(b, dst)
        arqs = [f for f in os.listdir(dst) if f.lower().endswith(".dcm")]
        import pydicom
        uids = set()
        for f in arqs:
            try:
                uids.add(str(pydicom.dcmread(os.path.join(dst, f),
                                             stop_before_pixels=True,
                                             specific_tags=["SeriesInstanceUID"]
                                             ).SeriesInstanceUID))
            except Exception:
                pass
        checar(u"a segunda nao destrui a primeira em silencio",
               bool(erro) or len(uids) <= 1 or len(arqs) == 12,
               u"%d arquivo(s), %d UID(s), erro=%s" % (len(arqs), len(uids), erro))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _regravar(caminho, mexer):
    import pydicom
    d = pydicom.dcmread(caminho)
    mexer(d)
    d.save_as(caminho)


def _caos_grade(org, arqs):
    def _ps(d):
        d.PixelSpacing = ["0.9", "0.9"]
    for f in arqs[3:]:
        _regravar(os.path.join(org, f), _ps)


def _caos_matriz(org, arqs):
    def _rows(d):
        d.Rows = 64
    _regravar(os.path.join(org, arqs[2]), _rows)


def _caos_deslocamento(org, arqs):
    def _meio_pixel(d):
        ipp = [float(x) for x in d.ImagePositionPatient]
        ipp[0] += 0.35
        d.ImagePositionPatient = ["%.2f" % v for v in ipp]
    _regravar(os.path.join(org, arqs[3]), _meio_pixel)


def _caos_sem_direcao(org, arqs):
    def _sem(d):
        del d.ImageOrientationPatient
    for f in arqs:
        _regravar(os.path.join(org, f), _sem)


def _caos_direcao_nula(org, arqs):
    def _nula(d):
        d.ImageOrientationPatient = ["0"] * 6
    for f in arqs:
        _regravar(os.path.join(org, f), _nula)


def _caos_pixel_curto(org, arqs):
    def _metade(d):
        d.PixelData = d.PixelData[:len(d.PixelData) // 2]
    _regravar(os.path.join(org, arqs[2]), _metade)


def _caos_falta_corte(org, arqs):
    os.remove(os.path.join(org, arqs[3]))


def _caos_arquivo_cortado(org, arqs):
    p = os.path.join(org, arqs[4])
    bruto = io.open(p, "rb").read()
    io.open(p, "wb").write(bruto[:len(bruto) - 2000])


CAOS = (
    (u"grade que nao bate: o PixelSpacing muda no meio da serie",
     _caos_grade, (u"pixelspacing", u"espaçamento no plano")),
    (u"grade que nao bate: um corte com outra matriz",
     _caos_matriz, (u"matriz", u"matrizes")),
    (u"deslocamento fracionario: um corte meio pixel ao lado",
     _caos_deslocamento, (u"deslocad", u"imagepositionpatient", u"origem")),
    (u"direcao ausente: sem ImageOrientationPatient",
     _caos_sem_direcao, (u"imageorientationpatient", u"orientação")),
    (u"direcao ausente: ImageOrientationPatient toda zero",
     _caos_direcao_nula, (u"imageorientationpatient", u"orientação")),
    (u"tamanho errado: o pixel de um corte tem metade dos bytes",
     _caos_pixel_curto, (u"pixel", u"bytes", u"tamanho")),
    (u"serie truncada: falta um corte no meio",
     _caos_falta_corte, (u"espaçamento irregular",)),
    (u"serie truncada: o arquivo de um corte cortado no fim",
     _caos_arquivo_cortado, (u"truncad", u"incomplet", u"bytes", u"pixel")),
)

INCOMPLETOS = (
    u"tamanho errado: o pixel de um corte tem metade dos bytes",
    u"serie truncada: o arquivo de um corte cortado no fim",
)


def _dcms(pasta):
    if not os.path.isdir(pasta):
        return []
    return sorted(f for f in os.listdir(pasta) if f.lower().endswith(".dcm"))


def _caso(nome):
    return [c for c in CAOS if c[0] == nome][0]


def _veredito_do_caos(laudo, recusa, palavras):
    if recusa:
        return True, u"recusou: %s" % recusa[:90]
    if laudo and not laudo.get("pode_converter", True):
        return True, u"o laudo impede a conversao"
    for a in (laudo or {}).get("achados") or ():
        if a.get("ok"):
            continue
        txt = (u"%s %s %s" % (a.get("titulo"), a.get("detalhe"),
                              a.get("o_que_faz"))).lower()
        if a.get("alerta") and any(p in txt for p in palavras):
            return True, u"avisa: %s" % a.get("titulo")
    return False, u"converte calado: %s" % u"; ".join(
        a.get("titulo") for a in (laudo or {}).get("achados") or ()
        if not a.get("ok"))[:120]


def teste_geometria_caos():
    secao(u"geometria caos: o que nao fecha recusa ou avisa, sem traceback")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="radai_conv_caos_")
    try:
        for rotulo, mexer, palavras in CAOS:
            org = os.path.join(base, "c%d" % CAOS.index((rotulo, mexer, palavras)))
            escrever(org, n=6)
            mexer(org, sorted(os.listdir(org)))
            laudo, recusa, cru = None, u"", u""
            try:
                ss = _series(org)
                if not ss:
                    recusa = u"a varredura nao achou a serie"
                else:
                    laudo = D.conferir(ss[0])
                    try:
                        r = D.converter(ss[0], org + "_d", laudo=laudo)
                        saiu = [f for f in os.listdir(org + "_d")
                                if f.lower().endswith(".dcm")]
                        if len(saiu) != r.get("cortes"):
                            cru = u"meia serie: %d de %d" % (len(saiu),
                                                            r.get("cortes"))
                    except D.Recusa as e:
                        recusa = str(e)
            except Exception as e:
                cru = u"%s: %s" % (type(e).__name__, str(e)[:100])
            checar(u"%s: sem traceback nem meia serie" % rotulo, not cru, cru)
            ok, porque = _veredito_do_caos(laudo, recusa, palavras)
            checar(u"  recusa ou avisa com a causa no texto", ok, porque)
            if rotulo in INCOMPLETOS:
                checar(u"  o laudo impede e nada vai ao destino",
                       laudo is not None and not laudo["pode_converter"]
                       and not _dcms(org + "_d"),
                       u"%s | %d gravado(s)" % (porque, len(_dcms(org + "_d"))))
        checar(u"(isca) laudo sem alerta e sem recusa e reprovado",
               not _veredito_do_caos({"achados": [], "pode_converter": True},
                                     u"", (u"pixel",))[0])
        checar(u"(isca) alerta sobre OUTRA coisa nao conta como aviso claro",
               not _veredito_do_caos(
                   {"achados": [{"ok": False, "alerta": True,
                                 "titulo": u"Sem RescaleSlope"}],
                    "pode_converter": True}, u"", (u"pixel",))[0])
        checar(u"todo incompleto e um caso da lista",
               all(p in [c[0] for c in CAOS] for p in INCOMPLETOS))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _serie_do_caos(base, rotulo, n=6, **kw):
    import radai_dicom as D
    org = os.path.join(base, u"s%d" % len(os.listdir(base)))
    escrever(org, n=n, **kw)
    _caso(rotulo)[1](org, sorted(os.listdir(org)))
    D.esquecer_varredura()
    return org, _series(org)[0]


def teste_o_corte_incompleto_nunca_e_gravado():
    secao(u"o corte incompleto nunca chega ao destino, nem sem o laudo")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="radai_conv_inc_")
    try:
        for rotulo in INCOMPLETOS:
            org, s = _serie_do_caos(base, rotulo)
            codigos = [a.get("pixel") for a in s["arquivos"]]
            checar(u"%s: a varredura marca so o corte ruim" % rotulo,
                   len([c for c in codigos if c]) == 1, str(codigos))
            dst = org + "_forjado"
            try:
                D.converter(s, dst, laudo={"achados": []})
                recusou = u""
            except D.Recusa as e:
                recusou = str(e)
            checar(u"  laudo forjado sem o achado: recusa e nao grava nada",
                   recusou and not _dcms(dst), u"%s | %d gravado(s)"
                   % (recusou[:60], len(_dcms(dst))))
            for a in s["arquivos"]:
                a["pixel"] = u""
            dst = org + "_varredura_velha"
            try:
                D.converter(s, dst, laudo={"achados": []})
                recusou = u""
            except D.Recusa as e:
                recusou = str(e)
            checar(u"  varredura velha e laudo forjado: os bytes do corte "
                   u"recusam e nada fica", recusou and not _dcms(dst)
                   and u"bytes" in recusou, u"%s | %d gravado(s)"
                   % (recusou[:80], len(_dcms(dst))))
            velho = D._pixel_incompleto
            D._pixel_incompleto = lambda ds: u""
            try:
                dst = org + "_isca"
                try:
                    D.converter(s, dst, laudo={"achados": []})
                except D.Recusa:
                    pass
                checar(u"  (isca) sem a conferencia dos bytes, o corte ruim "
                       u"seria gravado", len(_dcms(dst)) == 6,
                       u"%d gravado(s)" % len(_dcms(dst)))
            finally:
                D._pixel_incompleto = velho
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_a_varredura_le_o_pixel_no_disco():
    secao(u"a varredura confere o tamanho da imagem em toda sintaxe")
    import radai_dicom as D
    from pydicom.uid import (ImplicitVRLittleEndian, ExplicitVRBigEndian,
                             DeflatedExplicitVRLittleEndian, RLELossless)
    base = tempfile.mkdtemp(prefix="radai_conv_pix_")
    try:
        for rotulo, uid in ((u"Explicit VR LE", None),
                            (u"Implicit VR LE", ImplicitVRLittleEndian),
                            (u"Explicit VR Big Endian", ExplicitVRBigEndian),
                            (u"Deflated", DeflatedExplicitVRLittleEndian),
                            (u"RLE (encapsulado)", RLELossless)):
            org = os.path.join(base, u"p%d" % len(os.listdir(base)))
            try:
                escrever(org, n=3, sintaxe=uid)
            except Exception as e:
                pular(rotulo, u"sem codificador aqui (%s)" % str(e)[:40])
                continue
            D.esquecer_varredura()
            s = _series(org)[0]
            checar(u"%s inteiro: nenhum corte marcado" % rotulo,
                   not any(a.get("pixel") for a in s["arquivos"]),
                   str([a.get("pixel") for a in s["arquivos"]]))
            if uid == DeflatedExplicitVRLittleEndian:
                continue
            nome = sorted(os.listdir(org))[1]
            p = os.path.join(org, nome)
            bruto = io.open(p, "rb").read()
            io.open(p, "wb").write(bruto[:len(bruto) - 600])
            D.esquecer_varredura()
            s = _series(org)[0]
            checar(u"%s cortado no fim: o corte 2 sai truncado" % rotulo,
                   [a.get("pixel") for a in s["arquivos"]]
                   == [u"", D.PIXEL_TRUNCADO, u""],
                   str([a.get("pixel") for a in s["arquivos"]]))
        org = os.path.join(base, u"sem_pixel")
        escrever(org, n=3)
        p = os.path.join(org, sorted(os.listdir(org))[2])
        import pydicom
        d = pydicom.dcmread(p)
        del d.PixelData
        d.save_as(p)
        D.esquecer_varredura()
        s = _series(org)[0]
        checar(u"corte sem PixelData: marcado ausente",
               [a.get("pixel") for a in s["arquivos"]][2] == D.PIXEL_AUSENTE,
               str([a.get("pixel") for a in s["arquivos"]]))
        checar(u"  e o laudo impede", not D.conferir(s)["pode_converter"])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _palavras_acusam(laudo, palavras):
    return _veredito_do_caos(laudo, u"", palavras)[0]


def teste_as_iscas_da_geometria():
    secao(u"geometria: a versao de antes reprova, e a serie sa nao alarma")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="radai_conv_geo_")
    try:
        _org, s = _serie_do_caos(base, CAOS[0][0])
        laudo = D.conferir(s)
        checar(u"a grade que muda vem com as duas grades no texto",
               any(u"0.700" in (a.get("detalhe") or u"")
                   and u"0.900" in (a.get("detalhe") or u"")
                   for a in laudo["achados"]), str(laudo["achados"])[:160])
        velho = D._grade_de
        D._grade_de = lambda a: ()
        try:
            checar(u"(isca) sem ler a grade de cada corte, o caso passaria "
                   u"calado", not _palavras_acusam(D.conferir(s), CAOS[0][2]))
        finally:
            D._grade_de = velho

        _org, s = _serie_do_caos(base, CAOS[2][0])
        laudo = D.conferir(s)
        desl = [a for a in laudo["achados"] if u"deslocad" in a["titulo"]]
        checar(u"o corte meio pixel ao lado e o corte 4, com 0.35 mm",
               desl and u"corte 4:" in desl[0]["detalhe"]
               and u"0.35" in desl[0]["detalhe"], str(desl)[:160])
        velho = D.deslocamento_no_plano
        D.deslocamento_no_plano = lambda arqs: None
        try:
            checar(u"(isca) sem medir o plano, o caso passaria calado",
                   not _palavras_acusam(D.conferir(s), CAOS[2][2]))
        finally:
            D.deslocamento_no_plano = velho

        org, s = _serie_do_caos(base, CAOS[4][0])
        laudo = D.conferir(s)
        titulos = [a["titulo"] for a in laudo["achados"]]
        checar(u"a IOP toda zero diz a causa, e nao 'na mesma posicao'",
               any(u"toda zero" in t for t in titulos)
               and not any(u"mesma posi" in t for t in titulos), str(titulos))
        checar(u"  e nao afirma que os cortes sao perpendiculares",
               not any(u"perpendicular" in t for t in titulos))
        r = D.converter(s, org + "_d", laudo=laudo)
        import pydicom
        x = pydicom.dcmread(os.path.join(org + "_d", _dcms(org + "_d")[0]))
        checar(u"  a saida leva a orientacao assumida e UID novo",
               [float(v) for v in x.ImageOrientationPatient]
               == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
               and str(x.SeriesInstanceUID) != s["uid"] and r["uid_regerado"],
               str(list(x.ImageOrientationPatient)))
        velho = D._iop_valida
        D._iop_valida = lambda iop: len(list(iop or [])) >= 6
        try:
            D.esquecer_varredura()
            s_velha = _series(org)[0]
            checar(u"(isca) com a regra antiga, a IOP zero volta a dizer "
                   u"so 'na mesma posicao'",
                   not _palavras_acusam(D.conferir(s_velha), CAOS[4][2]))
        finally:
            D._iop_valida = velho
            D.esquecer_varredura()

        limpa = os.path.join(base, u"limpa")
        escrever(limpa, n=6)
        D.esquecer_varredura()
        laudo = D.conferir(_series(limpa)[0])
        checar(u"a serie sa nao recebe alerta nenhum",
               not laudo["alertas"] and laudo["pode_converter"],
               str(laudo["alertas"]))
        torta = os.path.join(base, u"gantry")
        escrever(torta, n=6)
        import math
        cos, sen = math.cos(math.radians(12)), math.sin(math.radians(12))
        for k, f in enumerate(sorted(os.listdir(torta))):
            def _inclinar(d, k=k):
                d.ImageOrientationPatient = ["1", "0", "0", "0", "%.6f" % cos,
                                             "%.6f" % -sen]
                d.ImagePositionPatient = ["-100.0", "-100.0", "%.2f" % (k * 2.0)]
            _regravar(os.path.join(torta, f), _inclinar)
        D.esquecer_varredura()
        titulos = [a["titulo"] for a in D.conferir(_series(torta)[0])["achados"]]
        checar(u"o gantry inclinado acusa a inclinacao e nao o deslocamento",
               any(u"inclinado" in t for t in titulos)
               and not any(u"deslocad" in t for t in titulos), str(titulos))
        checar(u"a IOP de pouca precisao continua valendo",
               D._iop_valida(["0.99", "0.1", "0", "-0.1", "0.99", "0"])
               and not D._iop_valida([0] * 6)
               and not D._iop_valida([1, 0, 0, 1, 0, 0]))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    print(u"=" * 68)
    print(u"test_conversion | do tomografo novo ao CD de 2006")
    print(u"=" * 68)
    for t in (teste_sintaxes, teste_variacoes_do_aparelho, teste_dicom_de_cd,
              teste_o_que_nao_e_dicom, teste_o_destino_nao_destroi,
              teste_geometria_caos, teste_o_corte_incompleto_nunca_e_gravado,
              teste_a_varredura_le_o_pixel_no_disco,
              teste_as_iscas_da_geometria):
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    print(u"\n" + u"=" * 68)
    if _pulados:
        print(u"PULADOS (o que este runtime nao consegue escrever):")
        for r, p in _pulados:
            print(u"  — %s: %s" % (r.strip(), p))
        print(u"")
    if _falhou:
        print(u"FALHOU: %d de %d checagens" % (_falhou, _ok + _falhou))
        for f in _falhas:
            print(u"  - %s" % f)
    else:
        print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 68)
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
