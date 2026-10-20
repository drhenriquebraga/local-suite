# -*- coding: utf-8 -*-
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
_cleanup.adotar_prefixo('radai_ac_dicom')
_cleanup.adotar_prefixo('dcm_tilt')
_cleanup.adotar_prefixo('dcm_2s_')
_cleanup.adotar_prefixo('dcm_cab_')
_cleanup.adotar_prefixo('dcm_cv_')
_cleanup.adotar_prefixo('dcm_dup_')
_cleanup.adotar_prefixo('dcm_fr_')
_cleanup.adotar_prefixo('dcm_geo_')
_cleanup.adotar_prefixo('dcm_irr_')
_cleanup.adotar_prefixo('dcm_lixo_')
_cleanup.adotar_prefixo('dcm_meia_')
_cleanup.adotar_prefixo('dcm_ok_')
_cleanup.adotar_prefixo('dcm_rec_')
_cleanup.adotar_prefixo('dcm_vp_')
_cleanup.adotar_prefixo('dcm_bia_')
_cleanup.adotar_prefixo('dcm_junta_')


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


APP = pasta_app(AQUI)
sys.path.insert(0, APP)

import tempfile as _tempfile
import _componentes
os.environ["RADAI_CALIB_DIR"] = _tempfile.mkdtemp(prefix="radai_ac_dicom_")


_RESULTADOS = []


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    if not ok:
        print("  FALHA  %s%s" % (nome, ("  [%s]" % detalhe) if detalhe else ""))
    return bool(ok)


def secao(t):
    print("\n-- %s --" % t)


def escrever_serie(pasta, n=8, passo=3.0, uid_serie=None, frame_ref="1.2.3.4",
                   sem_pos=False, duplicar=None, passo_torto=None,
                   sem_frame_a_partir=None, pid=None, data=None, prefixo="IM",
                   modalidade="CT"):
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid
    os.makedirs(pasta, exist_ok=True)
    uid_serie = uid_serie or generate_uid()
    z = 0.0
    for i in range(n):
        ds = Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
        ds.SeriesInstanceUID = uid_serie
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.Modality = modalidade
        if pid is not None:
            ds.PatientID = pid
        if data is not None:
            ds.StudyDate = data
        ds.SeriesNumber = 1
        ds.InstanceNumber = i + 1
        ds.Rows, ds.Columns = 16, 16
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.SliceThickness = passo
        ds.PixelSpacing = [1.0, 1.0]
        ds.RescaleSlope = 1
        ds.RescaleIntercept = -1024
        ds.PatientPosition = "HFS"
        if not sem_pos:
            ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
            ds.ImagePositionPatient = [0.0, 0.0, z]
        if frame_ref and not (sem_frame_a_partir is not None
                              and i >= sem_frame_a_partir):
            ds.FrameOfReferenceUID = frame_ref
        ds.PixelData = (b"\x00\x00" * (16 * 16))
        ds.save_as(os.path.join(pasta, "%s%03d.dcm" % (prefixo, i)),
                   enforce_file_format=True)
        if duplicar is not None and i + 1 == duplicar:
            pass
        elif passo_torto and i + 1 == passo_torto[0]:
            z += passo_torto[1]
        else:
            z += passo


def teste_serie_limpa_nao_gera_achado():
    secao("serie limpa: nada a acusar")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_ok_")
    escrever_serie(os.path.join(base, "s"), n=8, passo=3.0)
    r = D.varrer(base)
    checar("achou uma serie", len(r["series"]) == 1, str(len(r["series"])))
    if not r["series"]:
        return
    s = r["series"][0]
    checar("com os 8 cortes", s["cortes"] == 8, str(s["cortes"]))
    checar("ordenada pela POSICAO, e nao pelo InstanceNumber",
           s["ordenado_por"] == "posicao", s["ordenado_por"])
    laudo = D.conferir(s)
    faltas = [a for a in laudo["achados"] if not a["ok"]]
    checar("nenhuma linha de falta", not faltas,
           "; ".join(a["titulo"] for a in faltas))
    checar("e o espacamento sai como constante",
           "constante" in laudo["encontrado"].get(u"Espaçamento entre cortes", ""),
           laudo["encontrado"].get(u"Espaçamento entre cortes", ""))
    checar("pode converter", laudo["pode_converter"])


def teste_espacamento_irregular_e_nomeado_com_os_cortes():
    secao("espacamento irregular: acusa, e diz entre quais cortes")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_irr_")
    escrever_serie(os.path.join(base, "s"), n=8, passo=3.0,
                   passo_torto=(4, 4.5))
    s = D.varrer(base)["series"][0]
    laudo = D.conferir(s)
    irr = [a for a in laudo["achados"] if "irregular" in a["titulo"].lower()]
    checar("acusa o espacamento irregular", len(irr) == 1,
           "; ".join(a["titulo"] for a in laudo["achados"]))
    if not irr:
        return
    checar("e diz entre QUAIS cortes", "cortes" in irr[0]["detalhe"],
           irr[0]["detalhe"][:70])
    checar("e o valor do passo torto aparece", "4,5" in irr[0]["detalhe"]
           or "4.5" in irr[0]["detalhe"], irr[0]["detalhe"][:70])
    checar("declara que a conversao NAO resolve", irr[0]["resolve"] is False)
    checar("e diz por que", "reamostra" in irr[0]["o_que_faz"].lower(),
           irr[0]["o_que_faz"][:70])


def teste_corte_duplicado_e_acusado():
    secao("corte duplicado: dois na mesma posicao")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_dup_")
    escrever_serie(os.path.join(base, "s"), n=8, passo=3.0, duplicar=4)
    s = D.varrer(base)["series"][0]
    laudo = D.conferir(s)
    dup = [a for a in laudo["achados"] if "mesma posi" in a["titulo"]]
    checar("acusa o corte duplicado", len(dup) == 1,
           "; ".join(a["titulo"] for a in laudo["achados"]))
    if dup:
        checar("e declara que NAO descarta sozinho", dup[0]["resolve"] is False)


def teste_frame_of_reference_ausente():
    secao("FrameOfReferenceUID ausente em parte dos cortes")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_fr_")
    escrever_serie(os.path.join(base, "s"), n=8, passo=3.0,
                   sem_frame_a_partir=5)
    s = D.varrer(base)["series"][0]
    laudo = D.conferir(s)
    fr = [a for a in laudo["achados"] if "FrameOfReference" in a["titulo"]]
    checar("acusa a ausencia", len(fr) == 1,
           "; ".join(a["titulo"] for a in laudo["achados"]))
    if fr:
        checar("e diz em quantos cortes", "3" in fr[0]["titulo"],
               fr[0]["titulo"])
        checar("cita a norma", "C.7.4.1" in fr[0]["detalhe"], fr[0]["detalhe"][:60])
        checar("e a conversao grava um FoR NOVO, como alerta",
               fr[0]["resolve"] is True and fr[0]["alerta"] is True
               and "NOVO" in fr[0]["o_que_faz"], fr[0]["o_que_faz"][:70])
        checar("dizendo que gerar seria uma afirmacao sobre a aquisicao",
               "aquisi" in fr[0]["o_que_faz"].lower(), fr[0]["o_que_faz"][:70])


def teste_serie_sem_geometria():
    secao("serie sem ImagePositionPatient")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_geo_")
    escrever_serie(os.path.join(base, "s"), n=6, passo=3.0, sem_pos=True)
    s = D.varrer(base)["series"][0]
    checar("cai para a ordem por InstanceNumber",
           s["ordenado_por"] == "instancia", s["ordenado_por"])
    laudo = D.conferir(s)
    geo = [a for a in laudo["achados"] if "ImagePositionPatient" in a["titulo"]]
    checar("acusa a falta de geometria", len(geo) == 1,
           "; ".join(a["titulo"] for a in laudo["achados"]))
    if geo:
        checar("cita a norma", "C.7.6.2" in geo[0]["detalhe"],
               geo[0]["detalhe"][:60])


def teste_o_cabecalho_sai_inteiro():
    secao("cabecalho: todas as tags, sem resumir")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_cab_")
    escrever_serie(os.path.join(base, "s"), n=1, passo=3.0)
    arq = os.path.join(base, "s", "IM000.dcm")
    c = D.ler_cabecalho(arq)
    checar("traz mais de 15 tags", c["n"] > 15, str(c["n"]))
    campos = c["tags"][0]
    for k in ("grupo", "elemento", "vr", "nome", "valor"):
        checar("cada tag traz `%s`" % k, k in campos, str(sorted(campos)))
    checar("o file_meta vem separado", len(c["meta"]) >= 3, str(len(c["meta"])))
    checar("e a sintaxe de transferencia esta nele",
           any("Transfer Syntax" in m["nome"] for m in c["meta"]),
           "; ".join(m["nome"] for m in c["meta"])[:90])
    checar("nao traz PixelData no cabecalho",
           not any(t["nome"] == "Pixel Data" for t in c["tags"]))


def teste_a_lista_de_sintaxes_e_por_NOME():
    secao("as sintaxes: por nome, e nao por prefixo")
    import radai_dicom as D
    checar("o RLE esta na tabela", "1.2.840.10008.1.2.5" in D.SINTAXES)
    checar("e marcado como comprimido", D.SINTAXES["1.2.840.10008.1.2.5"][1])
    checar("Explicit VR LE nao e comprimida",
           not D.SINTAXES["1.2.840.10008.1.2.1"][1])
    from pydicom.uid import UID as _UID
    for uid in sorted(D.SINTAXES):
        checar("  %s: comprimida bate com o pydicom" % uid,
               D.SINTAXES[uid][1] == bool(_UID(uid).is_compressed),
               "tabela=%s pydicom=%s"
               % (D.SINTAXES[uid][1], _UID(uid).is_compressed))
    checar("o destino e Implicit VR Little Endian, nos dois TPS",
           D.SINTAXE_DESTINO == "1.2.840.10008.1.2"
           and D.sintaxe_de_saida("eclipse") == D.sintaxe_de_saida("monaco")
           == D.sintaxe_de_saida() == D.SINTAXE_DESTINO, D.SINTAXE_DESTINO)


def teste_arquivo_que_nao_e_dicom_nao_derruba():
    secao("arquivo que nao e DICOM: contado, nao fatal")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_lixo_")
    escrever_serie(os.path.join(base, "s"), n=4, passo=3.0)
    with open(os.path.join(base, "s", "leiame.txt"), "w") as f:
        f.write("nao sou dicom")
    r = D.varrer(base)
    checar("a serie continua sendo achada", len(r["series"]) == 1)
    checar("e a serie tem os 4 cortes (o lixo nao entrou)",
           r["series"][0]["cortes"] == 4, str(r["series"][0]["cortes"]))
    checar("o que nao abriu foi CONTADO", len(r["ignorados"]) >= 1,
           str(r["ignorados"]))


def teste_duas_series_na_mesma_pasta_nao_se_fundem():
    secao("duas series na mesma pasta")
    import radai_dicom as D
    from pydicom.uid import generate_uid
    base = tempfile.mkdtemp(prefix="dcm_2s_")
    a, b = generate_uid(), generate_uid()
    escrever_serie(os.path.join(base, "tudo"), n=5, passo=3.0, uid_serie=a)
    import shutil
    tmp = os.path.join(base, "tmp")
    escrever_serie(tmp, n=3, passo=5.0, uid_serie=b)
    for i, f in enumerate(sorted(os.listdir(tmp))):
        shutil.move(os.path.join(tmp, f),
                    os.path.join(base, "tudo", "B%03d.dcm" % i))
    shutil.rmtree(tmp)
    r = D.varrer(base)
    checar("as duas series aparecem separadas", len(r["series"]) == 2,
           str(len(r["series"])))
    tam = sorted(s["cortes"] for s in r["series"])
    checar("com 3 e 5 cortes", tam == [3, 5], str(tam))


def teste_conversao_limpa_grava_e_confere_no_disco():
    secao("conversao limpa: grava e confere contando o disco")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_cv_")
    escrever_serie(os.path.join(base, "s"), n=6, passo=3.0)
    s = D.varrer(base)["series"][0]
    saida = os.path.join(base, "out")
    r = D.converter(s, saida)
    checar("gravou os 6 cortes", r["cortes"] == 6, str(r["cortes"]))
    checar("em Implicit VR Little Endian (a sintaxe padrao do DICOM, nos "
           "dois TPS)", r["sintaxe"] == "1.2.840.10008.1.2", r["sintaxe"])
    checar("e o SeriesInstanceUID foi PRESERVADO",
           r["uid_preservado"] == s["uid"], r["uid_preservado"][:24])
    n_disco = len([f for f in os.listdir(saida) if f.endswith(".dcm")])
    checar("e ha mesmo 6 arquivos no disco", n_disco == 6, str(n_disco))
    de_volta = D.varrer(saida)["series"][0]
    checar("a serie de saida tem os mesmos 6 cortes", de_volta["cortes"] == 6)
    checar("e o mesmo UID", de_volta["uid"] == s["uid"])


def teste_recusa_gravar_com_anomalia_nao_decidida():
    secao("anomalia nao corrigida: alerta no DICOM, e a conversao segue")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_rec_")
    escrever_serie(os.path.join(base, "s"), n=8, passo=3.0,
                   passo_torto=(4, 4.5))
    s = D.varrer(base)["series"][0]
    laudo = D.conferir(s)
    saida = os.path.join(base, "out")

    r0 = D.converter(s, saida, laudo=laudo)
    checar("converte sem aceite", r0["cortes"] == 8, str(r0.get("cortes")))
    checar("e o resultado nomeia o alerta",
           any("irregular" in t.lower() for t in r0.get("alertas") or ()),
           str(r0.get("alertas"))[:100])
    import pydicom
    x = pydicom.dcmread(os.path.join(saida, "IM00000.dcm"))
    checar("e o alerta esta dentro do DICOM",
           "ALERTA" in str(x.SeriesDescription)
           and "irregular" in str(x.ImageComments).lower(),
           str(x.SeriesDescription))

    falso = dict(laudo)
    falso["achados"] = list(laudo["achados"]) + [D._achado(
        False, u"Este pacote não descomprime X.", resolve=False,
        alerta=True, impede=True)]
    try:
        D.converter(s, os.path.join(base, "out_impede"), laudo=falso)
        checar("decodificador ausente ainda impede", False, "passou")
    except D.Recusa as e:
        checar("decodificador ausente ainda impede", True)
        checar("e diz por que", "descomprime" in str(e), str(e)[:80])

    titulo = [a["titulo"] for a in laudo["achados"]
              if not a["ok"] and a["resolve"] is False][0]
    r = D.converter(s, saida, laudo=laudo, aceitar=[titulo])
    checar("com a decisao registrada, converte", r["cortes"] == 8,
           str(r.get("cortes")))
    checar("e a decisao aceita fica registrada no resultado",
           titulo in (r.get("aceitos") or []), str(r.get("aceitos"))[:80])


def teste_meia_serie_nao_fica_na_pasta():
    secao("meia serie: a pasta de destino e limpa")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_meia_")
    pasta = os.path.join(base, "s")
    escrever_serie(pasta, n=6, passo=3.0)
    s = D.varrer(base)["series"][0]
    alvo = s["arquivos"][3]["caminho"]
    with open(alvo, "wb") as f:
        f.write(b"nao sou mais dicom")
    saida = os.path.join(base, "out")
    try:
        D.converter(s, saida)
        parou, motivo = False, ""
    except D.Recusa as e:
        parou, motivo = True, str(e)
    checar("RECUSA, em vez de entregar 5 de 6", parou, motivo[:80])
    if parou:
        checar("e diz quantos falharam", "1 de 6" in motivo, motivo[:90])
    sobrou = (len([f for f in os.listdir(saida) if f.endswith(".dcm")])
              if os.path.isdir(saida) else 0)
    checar("e a pasta de destino ficou VAZIA", sobrou == 0, str(sobrou))


def escrever_serie_inclinada(pasta, n=60, tilt_graus=20.0, passo=3.0,
                             lado=32):
    import math
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid
    os.makedirs(pasta, exist_ok=True)
    uid_serie = generate_uid()
    frame = generate_uid()
    t = math.radians(tilt_graus)
    for i in range(n):
        ds = Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
        ds.SeriesInstanceUID = uid_serie
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.FrameOfReferenceUID = frame
        ds.Modality = "CT"
        ds.SeriesNumber = 1
        ds.InstanceNumber = i + 1
        ds.Rows, ds.Columns = lado, lado
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.SliceThickness = passo
        ds.PixelSpacing = [1.0, 1.0]
        ds.RescaleSlope = 1
        ds.RescaleIntercept = -1024
        ds.PatientPosition = "HFS"
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        if tilt_graus:
            ds.GantryDetectorTilt = float(tilt_graus)
        avanco = i * passo
        ds.ImagePositionPatient = [0.0,
                                   avanco * math.sin(t),
                                   avanco * math.cos(t)]
        ds.PixelData = (b"\x00\x04" * (lado * lado))
        ds.save_as(os.path.join(pasta, "IM%03d.dcm" % i),
                   enforce_file_format=True)
    return uid_serie


def teste_inclinacao_de_gantry_e_medida():
    secao("inclinacao de gantry: medida pela geometria")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_tilt_")

    for graus, espera in ((0.0, False), (10.0, True), (20.0, True)):
        p = os.path.join(base, "t%02d" % int(graus))
        escrever_serie_inclinada(p, n=60, tilt_graus=graus)
        r = D.varrer(p, relembrar=False)
        arqs = r["series"][0]["arquivos"]
        medido, desvio, declarado = D.inclinacao_de_gantry(arqs)
        checar("tilt %2.0f: mede %.1f graus" % (graus, medido),
               abs(medido - graus) < 0.6, "%.2f" % medido)
        checar("tilt %2.0f: %s desvio" % (graus, "acusa" if espera else "sem"),
               (desvio > 2.0) == espera, "%.1f mm" % desvio)
        checar("tilt %2.0f: le a tag declarada" % graus,
               (declarado or 0) == graus, str(declarado))

    import pydicom
    p = os.path.join(base, "sem_tag")
    escrever_serie_inclinada(p, n=60, tilt_graus=20.0)
    for nome in sorted(os.listdir(p)):
        c = os.path.join(p, nome)
        ds = pydicom.dcmread(c)
        del ds.GantryDetectorTilt
        ds.save_as(c, enforce_file_format=True)
    r = D.varrer(p, relembrar=False)
    medido, desvio, declarado = D.inclinacao_de_gantry(r["series"][0]["arquivos"])
    checar("SEM a tag no cabecalho, a geometria continua acusando",
           abs(medido - 20.0) < 0.6 and desvio > 2.0,
           "%.1f graus, %.1f mm, tag=%s" % (medido, desvio, declarado))

    p = os.path.join(base, "curta")
    escrever_serie_inclinada(p, n=2, tilt_graus=20.0)
    r = D.varrer(p, relembrar=False)
    m, d, _ = D.inclinacao_de_gantry(r["series"][0]["arquivos"])
    checar("serie de 2 cortes devolve zero, sem levantar", m == 0.0 and d == 0.0)
    checar("lista vazia devolve zero, sem levantar",
           D.inclinacao_de_gantry([]) == (0.0, 0.0, None))

    shutil.rmtree(base, ignore_errors=True)


def teste_o_laudo_nomeia_a_inclinacao():
    secao("o laudo nomeia a inclinacao, e nao promete corrigir")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_tiltl_")

    p = os.path.join(base, "reta")
    escrever_serie_inclinada(p, n=40, tilt_graus=0.0)
    laudo = D.conferir(D.varrer(p, relembrar=False)["series"][0])
    tit = [a["titulo"] for a in laudo["achados"]]
    checar("serie reta: diz que os cortes sao perpendiculares",
           any("perpendicular" in t for t in tit), str(tit)[:80])
    checar("e nao acusa inclinacao",
           not any("inclinado" in t for t in tit))
    checar("o encontrado registra a ausencia",
           laudo["encontrado"].get(u"Inclinação de gantry") == u"nenhuma",
           str(laudo["encontrado"].get(u"Inclinação de gantry")))

    p = os.path.join(base, "torta")
    escrever_serie_inclinada(p, n=60, tilt_graus=20.0)
    laudo = D.conferir(D.varrer(p, relembrar=False)["series"][0])
    tortos = [a for a in laudo["achados"] if "inclinado" in a["titulo"]]
    checar("serie torta: o laudo acusa", len(tortos) == 1, str(len(tortos)))
    if tortos:
        a = tortos[0]
        checar("e a conversao NAO promete corrigir", a["resolve"] is False)
        checar("o titulo tem o angulo", "20" in a["titulo"], a["titulo"])
        checar("o detalhe tem o desvio em mm", "mm" in a["detalhe"])
        checar("e diz por que nao corrige",
               "reamostrar" in a["o_que_faz"] and "interpola" in a["o_que_faz"])
        checar("e avisa que o contorno sai plausivel",
               "plaus" in a["o_que_faz"], a["o_que_faz"][-70:])
    checar("o encontrado traz o angulo e o desvio",
           "mm" in str(laudo["encontrado"].get(u"Inclinação de gantry", "")),
           str(laudo["encontrado"].get(u"Inclinação de gantry")))

    shutil.rmtree(base, ignore_errors=True)


def teste_a_leitura_recusa_a_serie_inclinada():
    secao("load_sitk recusa a serie que sairia torta")
    try:
        import engine
    except Exception as e:
        checar("motor importa neste runtime", False, str(e)[:60])
        return
    base = tempfile.mkdtemp(prefix="dcm_tiltm_")

    p = os.path.join(base, "reta")
    escrever_serie_inclinada(p, n=40, tilt_graus=0.0)
    try:
        engine.load_sitk(p)
        checar("serie reta passa", True)
    except Exception as e:
        checar("serie reta passa", False, "%s: %s" % (type(e).__name__, e))

    p = os.path.join(base, "torta")
    escrever_serie_inclinada(p, n=60, tilt_graus=20.0)
    try:
        engine.load_sitk(p)
        checar("serie torta e RECUSADA", False, "passou")
    except RuntimeError as e:
        m = str(e)
        checar("serie torta e RECUSADA", True)
        checar("a mensagem tem o angulo", "20" in m, m[:70])
        checar("e o desvio em mm", "mm" in m)
        checar("e diz que o contorno sairia plausivel", "plaus" in m)
        checar("e oferece a saida consciente", "RADAI_ACEITA_TILT_MM" in m)
    except Exception as e:
        checar("serie torta e RECUSADA com RuntimeError", False,
               "%s: %s" % (type(e).__name__, e))

    guardado = os.environ.get("RADAI_ACEITA_TILT_MM")
    os.environ["RADAI_ACEITA_TILT_MM"] = "999"
    try:
        engine.load_sitk(p)
        checar("com RADAI_ACEITA_TILT_MM alto, ela passa", True)
    except Exception as e:
        checar("com RADAI_ACEITA_TILT_MM alto, ela passa", False, str(e)[:60])
    finally:
        if guardado is None:
            os.environ.pop("RADAI_ACEITA_TILT_MM", None)
        else:
            os.environ["RADAI_ACEITA_TILT_MM"] = guardado

    fonte = io.open(_componentes.fonte("app/engine.py"), encoding="utf-8").read()
    corpo = fonte[fonte.index("def load_sitk("):]
    corpo = corpo[:corpo.index("def resample(")]
    checar("`load_sitk` CHAMA a conferencia",
           "_conferir_inclinacao(" in corpo,
           "a funcao existir nao basta: ela tem de estar no caminho")
    checar("e ANTES de montar o volume",
           corpo.index("_conferir_inclinacao(") < corpo.index("r.Execute()"))
    todos = fonte.count("sitk.ImageSeriesReader()")
    checar("ha UM leitor de serie no motor", todos == 1, str(todos))


def teste_toda_sintaxe_tem_decodificador():
    secao("toda sintaxe com Pixel Data tem decodificador")
    import pydicom
    try:
        from pydicom.pixels.decoders.base import _PIXEL_DATA_DECODERS
    except Exception as e:
        checar("o registro de decodificadores existe", False, str(e)[:60])
        return

    try:
        import openjpeg
        tem_openjpeg = True
    except Exception:
        tem_openjpeg = False
    if not tem_openjpeg:
        print("  PULADA  o decodificador HTJ2K nao esta neste runtime "
              "(e do bundle, nao do .venv) -- o pino de versao continua "
              "sendo conferido abaixo")
        _conferir_pino_do_numpy()
        return

    sem = []
    for uid, par in _PIXEL_DATA_DECODERS.items():
        dec = par[0] if isinstance(par, tuple) else par
        try:
            if not dec.is_available:
                sem.append(str(uid))
        except Exception:
            sem.append(str(uid))
    checar("nenhuma sintaxe sem decodificador", not sem,
           ", ".join(sorted(sem)[:4]))
    checar("e o registro tem as 16 esperadas",
           len(_PIXEL_DATA_DECODERS) >= 16, str(len(_PIXEL_DATA_DECODERS)))

    for uid in ("1.2.840.10008.1.2.4.201", "1.2.840.10008.1.2.4.202",
                "1.2.840.10008.1.2.4.203"):
        par = _PIXEL_DATA_DECODERS.get(pydicom.uid.UID(uid))
        dec = (par[0] if isinstance(par, tuple) else par) if par else None
        checar("HTJ2K %s decodifica" % uid.rsplit(".", 1)[-1],
               dec is not None and bool(dec.is_available))

    try:
        import numpy as _np
        from openjpeg import encode as _encode
        alvo = (_np.arange(64 * 64, dtype=_np.int16).reshape(64, 64) % 2048) - 1024
        bruto = _encode(alvo, photometric_interpretation=2, use_mct=False,
                        compression_ratios=[1], codec_format=0)
        ds = pydicom.Dataset()
        ds.file_meta = pydicom.dataset.FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = pydicom.uid.UID("1.2.840.10008.1.2.4.90")
        ds.Rows, ds.Columns = 64, 64
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 16, 15
        ds.PixelRepresentation = 1
        ds.PixelData = pydicom.encaps.encapsulate([bruto])
        volta = ds.pixel_array.astype(_np.int16)
        checar("ida e volta em JPEG 2000 devolve os mesmos pixels",
               bool(_np.array_equal(volta, alvo)))
    except ImportError:
        checar("openjpeg presente neste runtime", False,
               "o .venv nao tem: esta checagem e do bundle")
    except Exception as e:
        checar("ida e volta em JPEG 2000", False,
               "%s: %s" % (type(e).__name__, str(e)[:70]))

    _conferir_pino_do_numpy()


def teste_a_varredura_de_uma_pasta_nao_desce():
    secao("varrer_pasta: so a propria pasta, com progresso e parada")
    import radai_dicom as D
    checar("o filtro de arquivo e publico, e o nome antigo saiu",
           callable(getattr(D, "vale_abrir", None))
           and not hasattr(D, "_vale_abrir"))
    base = tempfile.mkdtemp(prefix="dcm_vp_")
    a = os.path.join(base, "A")
    escrever_serie(a, n=8, uid_serie="9.9.1.1", pid="FANTOMA-1",
                   data="20240115")
    escrever_serie(os.path.join(a, "SUB"), n=6, uid_serie="9.9.1.2")
    with open(os.path.join(a, "leiame.txt"), "w") as f:
        f.write("texto")
    lidos = []
    r = D.varrer_pasta(a, ao_ler=lambda: lidos.append(1))
    uids = sorted(s["uid"] for s in r["series"])
    checar("le a serie da pasta e nao a da subpasta", uids == ["9.9.1.1"],
           str(uids))
    checar("  (isca) a varredura da arvore ve as duas",
           sorted(s["uid"] for s in D.varrer(a, relembrar=False)["series"])
           == ["9.9.1.1", "9.9.1.2"])
    checar("o progresso conta cada arquivo olhado, DICOM ou nao",
           len(lidos) == 9, str(len(lidos)))
    s = r["series"][0] if r["series"] else {}
    checar("a serie traz a data e o ID do paciente, para a tela",
           s.get("data") == "20240115" and s.get("pid") == "FANTOMA-1",
           "%s %s" % (s.get("data"), s.get("pid")))
    checar("e nao foi parada", r.get("parado") is False)
    vistos = []

    def parar():
        return len(vistos) >= 3
    r2 = D.varrer_pasta(a, parar=parar, ao_ler=lambda: vistos.append(1))
    checar("a parada interrompe no meio da pasta",
           r2.get("parado") is True and len(vistos) == 3
           and sum(x["cortes"] for x in r2["series"]) <= 3,
           "%s %d" % (r2.get("parado"), len(vistos)))
    r3 = D.varrer_pasta(os.path.join(base, "NAO_EXISTE"))
    checar("pasta que nao abre volta vazia e diz o erro, sem levantar",
           not r3["series"] and bool(r3.get("erro")), str(r3.get("erro")))


def teste_a_busca_pela_arvore_le_cada_arquivo_uma_vez():
    secao("buscar_series: pasta a pasta, cada arquivo uma vez, com tetos")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_vp_")
    escrever_serie(os.path.join(base, "P", "TC"), n=10, uid_serie="9.9.2.1")
    escrever_serie(os.path.join(base, "P", "RM"), n=9, uid_serie="9.9.2.2",
                   modalidade="MR")
    escrever_serie(os.path.join(base, "P", "POUCOS"), n=3,
                   uid_serie="9.9.2.3")
    escrever_serie(os.path.join(base, "P", "_RadAI"), n=10,
                   uid_serie="9.9.2.4")
    misto = os.path.join(base, "P", "MISTO")
    escrever_serie(misto, n=4, uid_serie="9.9.2.5")
    escrever_serie(os.path.join(misto, "MAIS"), n=7, uid_serie="9.9.2.5",
                   prefixo="JM")
    with open(os.path.join(base, "P", "estudo.zip"), "wb") as f:
        f.write(b"PK\x05\x06" + b"\0" * 18)
    lidas = []
    original = D.varrer_pasta

    def espiao(pasta, *a, **k):
        lidas.append(os.path.normcase(pasta))
        return original(pasta, *a, **k)
    D.varrer_pasta = espiao
    try:
        b = D.buscar_series(base, modalidades=("CT", "MR"), min_cortes=5)
    finally:
        D.varrer_pasta = original
    por = dict((s["uid"], s) for s in b["series"])
    checar("acha a TC e a RM das subpastas",
           "9.9.2.1" in por and "9.9.2.2" in por, str(sorted(por)))
    checar("a serie de 3 cortes fica de fora (minimo pedido)",
           "9.9.2.3" not in por)
    checar("a pasta _RadAI e pulada", "9.9.2.4" not in por)
    m = por.get("9.9.2.5") or {}
    checar("a serie repartida em duas pastas fica na que tem mais cortes",
           m.get("cortes") == 7 and os.path.basename(m.get("pasta") or "")
           == "MAIS", str(m)[:140])
    checar("cada pasta vai uma vez so a leitura", len(lidas) == len(set(lidas)),
           str(len(lidas)))
    checar("e cada arquivo e lido uma vez (10+9+3+4+7+1 zip)",
           b["arquivos"] == 34, str(b["arquivos"]))
    checar("o .zip e contado, e nao aberto", b["zips"] == 1, str(b["zips"]))
    checar("sem corte nem parada", b["cortada"] is None and not b["parado"])
    av = D.avisos_da_busca(b)
    checar("o aviso da busca diz que o .zip nao foi aberto, e so isso",
           len(av) == 1 and ".zip" in av[0], " | ".join(av))
    c = D.buscar_series(base, teto_pastas=2)
    checar("o teto de pastas corta a busca e diz",
           c["cortada"] == "pastas" and c["pastas"] == 2,
           "%s %s" % (c["cortada"], c["pastas"]))
    checar("  e o aviso conta as pastas olhadas",
           any("2 pastas olhadas" in a for a in D.avisos_da_busca(c)),
           " | ".join(D.avisos_da_busca(c)))
    p = D.nova_busca()
    p["parado"] = True
    D.buscar_series(base, busca=p)
    checar("a busca parada antes de comecar nao le nada",
           p["arquivos"] == 0 and not p["series"], str(p["arquivos"]))


def _retrato_da_varredura(r):
    return ([(s["uid"], s["cortes"], s.get("espessura_mm"), s["modalidade"],
              [os.path.normcase(a["caminho"]) for a in s["arquivos"]])
             for s in r["series"]],
            sorted(n for n, _p in r["ignorados"]))


def teste_a_juncao_da_busca_e_a_varredura_da_pasta():
    secao("buscar_series com juncao: o que a busca leu e o que varrer() leria")
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_junta_")
    escrever_serie(os.path.join(base, "A", "TC"), n=6, uid_serie="9.9.3.1")
    escrever_serie(os.path.join(base, "A", "RM"), n=5, uid_serie="9.9.3.2",
                   modalidade="MR")
    escrever_serie(os.path.join(base, "A", "_RadAI"), n=4, uid_serie="9.9.3.4")
    escrever_serie(os.path.join(base, "A", "Windows", "TC"), n=4,
                   uid_serie="9.9.3.3")
    with open(os.path.join(base, "A", "leia.txt"), "w") as f:
        f.write("nao sou dicom")
    ref = _retrato_da_varredura(D.varrer(base, relembrar=False))
    j = D.nova_juncao()
    b = D.buscar_series(base, pular=D.pasta_pulada, juncao=j)
    junta = _retrato_da_varredura(D.varredura_da_juncao(j))
    checar("a juncao da busca e a varredura da pasta: as mesmas series, "
           "cortes, espessuras e arquivos na mesma ordem, e os mesmos ignorados",
           junta == ref and len(ref[0]) == 3, "%s | %s" % (junta, ref))
    checar("  e a busca segue contando o que leu (a juncao nao muda o progresso)",
           b["arquivos"] == 6 + 5 + 4 + 1 and len(b["series"]) == 3,
           "%s %s" % (b["arquivos"], len(b["series"])))
    checar("  e varredura_da_juncao devolve copia: chamar duas vezes da o mesmo",
           _retrato_da_varredura(D.varredura_da_juncao(j)) == junta)
    j2 = D.nova_juncao()
    D.buscar_series(base, juncao=j2)
    checar("  (isca) com o pular da busca comum, a pasta Windows fica de fora "
           "e a juncao diverge -- a comparacao discrimina",
           _retrato_da_varredura(D.varredura_da_juncao(j2)) != ref)
    j3 = D.nova_juncao()
    original = D.juntar_varredura
    vistos = []

    def _pula_a_primeira(juncao, r):
        if r.get("series") and not vistos:
            vistos.append(1)
            return
        original(juncao, r)
    D.juntar_varredura = _pula_a_primeira
    try:
        D.buscar_series(base, pular=D.pasta_pulada, juncao=j3)
    finally:
        D.juntar_varredura = original
    checar("  (isca) a juncao que perde uma pasta diverge",
           _retrato_da_varredura(D.varredura_da_juncao(j3)) != ref)
    D.esquecer_varredura(base)
    car = D.carimbo_da_arvore(base)
    r = D.varredura_da_juncao(j)
    checar("lembrar_varredura guarda com o carimbo, e varrer() a devolve sem ler",
           D.lembrar_varredura(base, car, r) and D.varrer(base) is r)
    escrever_serie(os.path.join(base, "A", "NOVA"), n=3, uid_serie="9.9.3.5")
    checar("  e a arvore que mudou depois do carimbo e lida de novo",
           D.varrer(base) is not r
           and "9.9.3.5" in [s["uid"] for s in D.varrer(base)["series"]])
    checar("  e sem carimbo nada se guarda", not D.lembrar_varredura(base, None, r))
    D.esquecer_varredura(base)


def teste_a_varredura_le_o_texto_declarado_de_cada_corte():
    secao("BurnedInAnnotation: lido em todo corte, na mesma leitura")
    import pydicom
    import radai_dicom as D
    base = tempfile.mkdtemp(prefix="dcm_bia_")
    pasta = os.path.join(base, "s")
    escrever_serie(pasta, n=30)
    nomes = sorted(os.listdir(pasta))
    alvo = os.path.join(pasta, nomes[25])
    ds = pydicom.dcmread(alvo)
    ds.BurnedInAnnotation = "YES"
    ds.save_as(alvo, enforce_file_format=True)
    D.esquecer_varredura()
    lidos = []
    original = pydicom.dcmread

    def espiao(*a, **k):
        lidos.append(1)
        return original(*a, **k)
    pydicom.dcmread = espiao
    try:
        s = D.varrer(pasta)["series"][0]
    finally:
        pydicom.dcmread = original
    marcas = [a.get("anotacao") for a in s["arquivos"]]
    checar("o corte 26 de 30 sai com YES, e so ele",
           marcas[25] == "YES" and marcas.count("YES") == 1
           and all(m == "" for i, m in enumerate(marcas) if i != 25),
           str(marcas))
    checar("  e a varredura abre cada arquivo uma vez so", len(lidos) == 30,
           str(len(lidos)))
    passo = max(1, 30 // 12)
    amostra = list(range(30))[::passo][:12] + [29]
    checar("  (isca) a amostra de 12 cortes mais o ultimo nao o veria",
           25 not in amostra)
    D.esquecer_varredura()


def teste_o_caminho_longo_e_comum():
    secao("caminho_longo: o prefixo do Windows, num lugar so")
    import radai_dicom as D
    if os.name != "nt":
        checar("(fora do Windows o caminho fica como esta)",
               D.caminho_longo("/tmp/x") == "/tmp/x")
        return
    longo = D.caminho_longo(u"C:\\EXAMES\\PAC")
    checar("o caminho ganha o prefixo de caminho longo",
           longo == u"\\\\?\\C:\\EXAMES\\PAC", longo)
    checar("o de rede ganha o prefixo UNC",
           D.caminho_longo(u"\\\\srv\\share\\x") == u"\\\\?\\UNC\\srv\\share\\x")
    checar("o que ja tem prefixo fica como esta", D.caminho_longo(longo) == longo)
    checar("a pasta terminada em ponto continua terminada em ponto",
           D.caminho_longo(u"C:\\EXAMES\\SERIE_0.").endswith(u"SERIE_0."))
    rel = D.caminho_longo(u"pasta_relativa_0.")
    checar("  inclusive a relativa (o abspath do Windows come o ponto)",
           rel.endswith(u"pasta_relativa_0.") and rel.startswith(u"\\\\?\\"),
           rel)
    checar("e sem_prefixo desfaz os dois prefixos",
           D.sem_prefixo(longo) == u"C:\\EXAMES\\PAC"
           and D.sem_prefixo(u"\\\\?\\UNC\\srv\\share\\x")
           == u"\\\\srv\\share\\x")
    fundo = D.caminho_longo(tempfile.mkdtemp(prefix="dcm_vp_"))
    for k in range(9):
        fundo = os.path.join(fundo, u"subpasta_comprida_%02d_%s" % (k, u"x" * 18))
    escrever_serie(fundo, n=6, uid_serie="9.9.3.1")
    checar("a pasta funda do fantoma passa de 260 caracteres", len(fundo) > 300,
           str(len(fundo)))
    raiz = fundo
    for _ in range(9):
        raiz = os.path.dirname(raiz)
    b = D.buscar_series(raiz)
    checar("e a busca pelo caminho longo acha a serie la no fundo",
           [s["uid"] for s in b["series"]] == ["9.9.3.1"],
           str([s["uid"] for s in b["series"]]))
    shutil.rmtree(raiz, ignore_errors=True)


def _conferir_pino_do_numpy():
    req = io.open(os.path.join(os.path.dirname(APP), "build",
                               "requirements-demo.txt"),
                  encoding="utf-8", errors="replace").read()
    checar("o requirements pina o openjpeg", "pylibjpeg-openjpeg==" in req)
    checar("e explica por que NAO e a versao mais nova",
           "numpy" in req[max(0, req.index("pylibjpeg-openjpeg==") - 900):
                          req.index("pylibjpeg-openjpeg==")],
           "2.4.0+ exige numpy>=2, e o TotalSegmentator exige numpy<2")


def main():
    print("test_dicom | conversor: leitura, laudo e conferencia")
    try:
        import pydicom
    except Exception as e:
        print("  pydicom ausente neste runtime (%s) — a bateria nao roda aqui"
              % type(e).__name__)
        print("\n" + "=" * 64)
        print("OK: 0 checagens (runtime sem pydicom)")
        print("=" * 64)
        return 0
    testes = [teste_toda_sintaxe_tem_decodificador,
              teste_inclinacao_de_gantry_e_medida,
              teste_o_laudo_nomeia_a_inclinacao,
              teste_a_leitura_recusa_a_serie_inclinada,
              teste_serie_limpa_nao_gera_achado,
              teste_espacamento_irregular_e_nomeado_com_os_cortes,
              teste_corte_duplicado_e_acusado,
              teste_frame_of_reference_ausente,
              teste_serie_sem_geometria,
              teste_o_cabecalho_sai_inteiro,
              teste_a_lista_de_sintaxes_e_por_NOME,
              teste_arquivo_que_nao_e_dicom_nao_derruba,
              teste_duas_series_na_mesma_pasta_nao_se_fundem,
              teste_conversao_limpa_grava_e_confere_no_disco,
              teste_recusa_gravar_com_anomalia_nao_decidida,
              teste_meia_serie_nao_fica_na_pasta,
              teste_a_varredura_de_uma_pasta_nao_desce,
              teste_a_busca_pela_arvore_le_cada_arquivo_uma_vez,
              teste_a_juncao_da_busca_e_a_varredura_da_pasta,
              teste_a_varredura_le_o_texto_declarado_de_cada_corte,
              teste_o_caminho_longo_e_comum]
    todos = set(k for k, v in globals().items()
                if k.startswith("teste_") and callable(v))
    fora = sorted(todos - set(f.__name__ for f in testes))
    checar("todo teste do arquivo esta na lista do main()", not fora,
           ", ".join(fora))
    for t in testes:
        try:
            t()
        except Exception as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    falhas = [(n, d) for n, ok, d in _RESULTADOS if not ok]
    print("\n" + "=" * 64)
    if falhas:
        print("FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n, d in falhas:
            print("  - %s%s" % (n, ("  [%s]" % d) if d else ""))
    else:
        print("OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print("=" * 64)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
