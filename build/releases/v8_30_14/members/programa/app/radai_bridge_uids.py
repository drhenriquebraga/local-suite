"""Plan DICOM identities before converting a group of images for TPS import."""
import hashlib
import os
import json

import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import UID, generate_uid


CONFLITO = "Conflito de UID: arquivos diferentes usam o mesmo identificador de instância. Exporte as séries novamente na origem."
MISTURA = "Uma série contém imagens de estudos ou pacientes diferentes. Separe os exames e exporte novamente."
INVALIDO = "Uma imagem está sem identificador DICOM válido. Exporte a série novamente na origem."
MUDOU = "A série mudou após a seleção. Recarregue a pasta."
FRAME_AMBIGUO = "Há cortes sem referencial espacial e não foi possível vinculá-los com segurança aos demais. Exporte a série novamente na origem."
PROVENIENCIA = {"SourceImageSequence", "SourceInstanceSequence", "OriginalAttributesSequence",
                "ModifiedAttributesSequence", "PredecessorDocumentsSequence"}
REVISAO = "bridge-identity-v2"


def _uid(*valores):
    return str(generate_uid(entropy_srcs=[json.dumps([REVISAO, *valores], ensure_ascii=True)]))


def _sha(caminho):
    with open(caminho, "rb") as origem:
        resumo = hashlib.sha256()
        for bloco in iter(lambda: origem.read(1024 * 1024), b""):
            resumo.update(bloco)
        return resumo.hexdigest()


def _iguais(a, b):
    if os.path.samefile(a, b) or _sha(a) == _sha(b):
        return True
    import numpy as np
    from pydicom.pixels import pixel_array

    def atributos(caminho):
        ds = pydicom.dcmread(caminho, force=True)
        for tag in list(ds.keys()):
            if tag.element == 0 or tag in (0x7fe00010, 0xfffcfffc):
                del ds[tag]
        return ds.to_json_dict()

    if atributos(a) != atributos(b):
        return False
    return np.array_equal(pixel_array(a, raw=True), pixel_array(b, raw=True))


def _referencias(ds, raiz=True):
    for elemento in ds:
        if elemento.VR == "SQ" and elemento.keyword not in PROVENIENCIA:
            for sub in elemento.value:
                yield from _referencias(sub, False)
        elif elemento.keyword == "ReferencedSOPInstanceUID" or (
                not raiz and elemento.keyword == "SeriesInstanceUID"):
            yield elemento


def _assinatura(caminho):
    estado = os.stat(caminho)
    return (estado.st_size, estado.st_mtime_ns)


def _mesma_pilha(arquivos):
    import numpy as np
    primeiro = arquivos[0]
    try:
        pos = np.asarray([a["ipp"] for a in arquivos], dtype=float)
        ori = np.asarray([a["iop"] for a in arquivos], dtype=float)
        grade = np.asarray([a["pixel_spacing"] for a in arquivos], dtype=float)
    except (KeyError, TypeError, ValueError):
        return False
    n = len(arquivos)
    if (n < 2 or pos.shape != (n,3) or ori.shape != (n,6) or grade.shape != (n,2)
            or not all(np.isfinite(v).all() for v in (pos, ori, grade)) or not (grade > 0).all()
            or not np.allclose(ori, ori[0], atol=1e-4) or not np.allclose(grade, grade[0], atol=1e-4)
            or any((a["linhas"], a["colunas"]) != (primeiro["linhas"], primeiro["colunas"]) for a in arquivos)):
        return False
    normal = np.cross(ori[0,:3], ori[0,3:])
    if not np.isclose(np.linalg.norm(normal), 1.0, atol=1e-4):
        return False
    delta = pos - pos[0]
    altura = delta @ normal
    passos = np.diff(np.sort(altura))
    return (np.min(passos) > .01 and np.allclose(passos, np.median(passos), atol=.1, rtol=.05)
            and np.max(np.linalg.norm(delta - np.outer(altura, normal), axis=1)) < .5)


def preparar(series, laudo):
    """Validate the whole selection before opening a destination or creating any UID map."""
    import radai_dicom as D
    planos, instancias, assinaturas = {}, {}, {}
    for serie in series:
        chave = str(serie.get("uid", ""))
        vistos, unicos, cabecalhos, pessoas = set(), [], [], set()
        for arq in serie.get("arquivos", ()):
            caminho = arq["caminho"]
            assinatura = _assinatura(caminho)
            ds = pydicom.dcmread(caminho, stop_before_pixels=True, force=True)
            sop = str(ds.get("SOPInstanceUID", ""))
            estudo = str(ds.get("StudyInstanceUID", ""))
            if not all(v and UID(v).is_valid for v in (chave, sop, estudo, str(ds.get("SOPClassUID", "")))):
                raise D.Recusa(INVALIDO)
            if sop != arq.get("sop") or chave != str(ds.get("SeriesInstanceUID", "")):
                raise D.Recusa(MUDOU)
            pessoas.add((estudo, str(ds.get("PatientID", "")), str(ds.get("IssuerOfPatientID", ""))))
            if len(pessoas) != 1:
                raise D.Recusa(MISTURA)
            if sop in instancias:
                outra, anterior = instancias[sop]
                if outra != chave or not _iguais(anterior, caminho):
                    raise D.Recusa(CONFLITO)
            if sop not in vistos:
                vistos.add(sop)
                instancias[sop] = (chave, caminho)
                assinaturas[caminho] = assinatura
                unicos.append(arq)
                cabecalhos.append(ds)
        if not unicos:
            raise D.Recusa(INVALIDO)
        # A series can be picked twice through overlapping source directories.
        # Different selections with the same Series UID must not overwrite each other.
        if chave in planos:
            if {a["sop"] for a in planos[chave]["serie"]["arquivos"]} != vistos:
                raise D.Recusa(CONFLITO)
            continue
        limpa = dict(serie, arquivos=unicos, cortes=len(unicos))
        if len(unicos) != len(serie["arquivos"]):
            D._fechar({chave: limpa}, [])
        diag = laudo(limpa)
        plano = D._plano_de_saida(limpa, diag)
        refs = {str(el.value) for ds in cabecalhos for el in _referencias(ds)}
        prefixo = "[%d ALERTA%s] " % (plano["n_alertas"], "S" if plano["n_alertas"] > 1 else "")
        anotar = plano["n_alertas"] and any(
            ds.get("ImageComments") != plano["comentario"] or
            not str(ds.get("SeriesDescription", "")).startswith(prefixo) for ds in cabecalhos)
        plano["anotar"] = bool(anotar)
        motivos = [v for v in (plano["uid_regerado"], "referencial acrescentado" if plano["frame_novo"] else "",
                  "reescala acrescentada" if plano["sem_reescala"] else "",
                  "tipo de captura acrescentado" if plano["captura"] and any(
                      not ds.get("ConversionType") for ds in cabecalhos) else "",
                  "alerta no cabeçalho" if anotar else "") if v]
        planos[chave] = dict(serie=limpa, laudo=diag, plano=plano, motivos=motivos, refs=refs,
                             ignorados=len(serie["arquivos"]) - len(unicos))
    proprietarios = {**{s: s for s in planos}, **{s: v[0] for s, v in instancias.items()}}
    if set(planos) & set(instancias):
        raise D.Recusa(CONFLITO)
    modificadas = {s for s, p in planos.items() if p["motivos"]}
    for p in planos.values():
        p["ligacoes"] = {proprietarios[r] for r in p["refs"] if r in proprietarios}
    while True:
        novas = modificadas | {s for s, p in planos.items() if p["ligacoes"] & modificadas}
        if novas == modificadas:
            break
        modificadas = novas
    assinadas = {}
    for s in modificadas:
        p = planos[s]
        arquivos = sorted((a["sop"], _sha(a["caminho"])) for a in p["serie"]["arquivos"])
        assinadas[s] = _uid(s, arquivos, p["motivos"], p["plano"]["comentario"])
    mapa = {}
    for s in modificadas:
        pendentes, alcancadas = [s], set()
        while pendentes:
            atual = pendentes.pop()
            if atual not in alcancadas:
                alcancadas.add(atual)
                pendentes.extend(planos[atual]["ligacoes"] & modificadas)
        p = planos[s]
        nova = _uid("serie", s, sorted(assinadas[a] for a in alcancadas))
        mapa[s] = nova
        for arq in p["serie"]["arquivos"]:
            mapa[arq["sop"]] = _uid("instancia", nova, arq["sop"])
        if not p["motivos"]:
            p["motivos"].append("referências atualizadas")
    for s, p in planos.items():
        plano = p["plano"]
        plano.update(derivada=s in modificadas, serie_uid=mapa.get(s,s),
                     uid_regerado="; ".join(p["motivos"]), mapa=mapa, assinaturas=assinaturas)
        if plano["frame_novo"]:
            arquivos = p["serie"]["arquivos"]
            frames = {str(a.get("frame_ref") or "") for a in arquivos}
            conhecidos = frames - {""}
            if "" in frames and conhecidos:
                if len(conhecidos) != 1 or not _mesma_pilha(arquivos):
                    raise D.Recusa(FRAME_AMBIGUO)
                plano["frame_novo"] = {f: next(iter(conhecidos)) for f in frames}
                p["serie"]["_bridge_identidade"] = plano
                continue
            tem_ancora = (any(a.get("frame_ref") and len(a.get("ipp", ())) == 3 for a in arquivos)
                          and any(D._iop_valida(a.get("iop")) for a in arquivos))
            conservar = not plano["geometria"] or (tem_ancora and len(frames - {""}) == 1)
            plano["frame_novo"] = {f: f if f and conservar else _uid("frame", plano["serie_uid"], f)
                                   for f in frames}
        p["serie"]["_bridge_identidade"] = plano
    return planos


def aplicar(ds, plano, arq):
    """Set identity and remap selected reference targets; preserve source-image provenance."""
    origem = arq["sop"]
    for el in _referencias(ds):
        if str(el.value) in plano["mapa"]:
            el.value = plano["mapa"][str(el.value)]
    if plano["derivada"]:
        ds.SeriesInstanceUID = plano["serie_uid"]
        ds.SOPInstanceUID = plano["mapa"][origem]
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
        tipo = list(ds.get("ImageType", ["ORIGINAL", "PRIMARY"]))
        ds.ImageType = ["DERIVED", "SECONDARY", *tipo[2:]]
        ds.DerivationDescription = ("Local Suite DICOM Bridge: " + plano["uid_regerado"]).encode(
            "ascii", errors="replace").decode("ascii")[:1024]
        fontes = list(ds.get("SourceImageSequence", []))
        if not any(str(f.get("ReferencedSOPInstanceUID", "")) == origem for f in fontes):
            fonte = Dataset()
            fonte.ReferencedSOPClassUID = ds.SOPClassUID
            fonte.ReferencedSOPInstanceUID = origem
            ds.SourceImageSequence = fontes + [fonte]
    if plano["frame_novo"]:
        ds.FrameOfReferenceUID = plano["frame_novo"][str(arq.get("frame_ref") or "")]


def conferir_arquivo(arq, plano):
    import radai_dicom as D
    if _assinatura(arq["caminho"]) != plano["assinaturas"][arq["caminho"]]:
        raise D.Recusa(MUDOU)


def converter_preparada(preparada, destino):
    """Older shared shells wrote the image before the component could apply its UID map."""
    import radai_dicom as D
    s, plano = preparada["serie"], preparada["plano"]
    if getattr(D, "IDENTIDADE_BRIDGE", False):
        return D.converter(s, destino, laudo=preparada["laudo"])
    for a in s["arquivos"]:
        conferir_arquivo(a, plano)
    diag = preparada["laudo"]
    if plano["n_alertas"] and not plano["anotar"]:
        diag = dict(diag, achados=[dict(x, alerta=False) for x in diag["achados"]])
    r = D.converter(s, destino, laudo=diag)
    if plano["derivada"]:
        for i, k in enumerate(plano["ordem"]):
            caminho = os.path.join(destino, "IM%05d.dcm" % i)
            ds = pydicom.dcmread(caminho)
            aplicar(ds, plano, s["arquivos"][k])
            D._gravar_na_sintaxe(ds, caminho, r["sintaxe"])
        r.update(uid_preservado="", uid_regerado=plano["uid_regerado"])
        r["recibo"]["uid_regerado"] = plano["uid_regerado"]
        caminho = r.get("recibo_arquivo")
        if caminho:
            with open(caminho, encoding="utf-8") as stream:
                recibos = json.load(stream)
            recibos[-1] = r["recibo"]
            with open(caminho, "w", encoding="utf-8") as stream:
                json.dump(recibos, stream, ensure_ascii=False, indent=1)
    return r
