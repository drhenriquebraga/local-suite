# -*- coding: utf-8 -*-
import hashlib
import hmac
import os
import threading

LADO = 192

LADO_VISOR = 512

_TETO_CACHE = 240

SEM_IMAGEM = frozenset(["RTSTRUCT", "RTPLAN", "RTDOSE", "RTRECORD", "SR", "KO",
                        "PR", "REG", "SEG", "FID"])

_SEGREDO = os.urandom(32)
_MAPA = {}
_CACHE = {}
_SERIES = {}
_ORDEM = []
_TRAVA = threading.Lock()


def bilhete(pasta, uid):
    chave = u"%s\x00%s" % (pasta, uid)
    b = hmac.new(_SEGREDO, chave.encode("utf-8", "replace"),
                 hashlib.sha256).hexdigest()[:32]
    with _TRAVA:
        _MAPA[b] = (pasta, uid)
    return b


def resolver(b):
    with _TRAVA:
        return _MAPA.get(str(b or ""), (None, None))


def _reduzir(arr, lado):
    import numpy as np
    a = np.asarray(arr)
    alt, larg = a.shape[:2]
    if alt <= lado and larg <= lado:
        return a
    fator = max(alt, larg) / float(lado)
    ys = (np.arange(int(alt / fator)) * fator).astype(np.int32)
    xs = (np.arange(int(larg / fator)) * fator).astype(np.int32)
    ys = np.clip(ys, 0, alt - 1)
    xs = np.clip(xs, 0, larg - 1)
    return a[ys][:, xs]


def _ler_corte(caminho):
    import pydicom
    from pydicom.dataset import FileMetaDataset
    from pydicom.uid import (ImplicitVRLittleEndian, ExplicitVRLittleEndian,
                             ExplicitVRBigEndian)
    ds = pydicom.dcmread(caminho, force=True)
    # GUARDA: corte sem preâmbulo chega sem `TransferSyntaxUID`, e sem ela o pixel não decodifica.
    meta = getattr(ds, "file_meta", None)
    if meta is None or not getattr(meta, "TransferSyntaxUID", None):
        implicito, little = getattr(ds, "original_encoding", (True, True))
        meta = meta if isinstance(meta, FileMetaDataset) else FileMetaDataset()
        meta.TransferSyntaxUID = (ImplicitVRLittleEndian if implicito else
                                  ExplicitVRLittleEndian if little else
                                  ExplicitVRBigEndian)
        ds.file_meta = meta
    return ds


def _hu(ds):
    import numpy as np
    a = ds.pixel_array
    foto = str(getattr(ds, "PhotometricInterpretation", "") or "").upper()
    if foto.startswith("PALETTE"):
        from pydicom.pixels import apply_color_lut
        a = apply_color_lut(a, ds)
    a = np.asarray(a).astype(np.float32)
    if a.ndim >= 3 and a.shape[-1] == 3 and (
            int(getattr(ds, "SamplesPerPixel", 1) or 1) > 1
            or foto.startswith("PALETTE")):
        a = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    if a.ndim == 3:
        a = a[a.shape[0] // 2]
    s = getattr(ds, "RescaleSlope", None)
    i = getattr(ds, "RescaleIntercept", None)
    if s is not None:
        a = a * float(s)
    if i is not None:
        a = a + float(i)
    return a


def _serie_do_bilhete(b, pasta, uid):
    with _TRAVA:
        s = _SERIES.get(str(b))
    if s is not None:
        return s
    import radai_dicom
    r = radai_dicom.varrer(pasta)
    for cand in r["series"]:
        if cand["uid"] == uid:
            with _TRAVA:
                _SERIES[str(b)] = cand
            return cand
    return None


def png(b, corte, janela="mediastino", lado=LADO):
    import radai_recon3d

    pasta, uid = resolver(b)
    if pasta is None:
        return b"", {"erro": u"bilhete desconhecido (o programa reiniciou?)"}

    chave = (str(b), int(corte), str(janela), int(lado))
    with _TRAVA:
        if chave in _CACHE:
            return _CACHE[chave]

    s = _serie_do_bilhete(b, pasta, uid)
    if s is None:
        return b"", {"erro": u"a série não está mais nesta pasta"}

    if (s.get("modalidade") or "").upper() in SEM_IMAGEM:
        return b"", {"sem_imagem": True, "modalidade": s.get("modalidade"),
                     "erro": u"%s não é série de imagem — não há corte para "
                             u"mostrar" % (s.get("modalidade") or u"esta série")}

    arqs = s["arquivos"]
    n = len(arqs)
    if not n:
        return b"", {"erro": u"série sem cortes"}
    i = int(corte)
    i = 0 if i < 0 else (n - 1 if i >= n else i)

    import pydicom
    ds = _ler_corte(arqs[i]["caminho"])
    try:
        arr = _hu(ds)
    except Exception as e:
        return b"", {"erro": u"não consegui decodificar o pixel (%s): %s"
                             % (arqs[i].get("sintaxe") or u"sintaxe ausente",
                                type(e).__name__),
                     "cortes": n, "corte": i}

    if str(janela) == "auto":
        centro, largura = _janela_auto(
            b, s, arr if i == central(n) else None)
    else:
        centro, largura = radai_recon3d.JANELAS.get(
            janela, radai_recon3d.JANELAS["mediastino"])
    dados = radai_recon3d.para_png(_reduzir(arr, lado), centro, largura)
    info = {"cortes": n, "corte": i, "janela": janela,
            "descricao": s["descricao"], "modalidade": s["modalidade"]}

    with _TRAVA:
        _CACHE[chave] = (dados, info)
        _ORDEM.append(chave)
        while len(_ORDEM) > _TETO_CACHE:
            _CACHE.pop(_ORDEM.pop(0), None)
    return dados, info


# GUARDA: o cache mora no temporário local, nunca na pasta do exame (gravar
# lá muda o carimbo da varredura e cada miniatura revarre o estudo), e é
# chaveado pelo UID inteiro, não pelos 8 últimos caracteres.
# GUARDA: a janela da grade é a da modalidade (`janela_do_visor`); a de TC
# sobre RM pinta a imagem de branco.
JANELA_GRADE = "mediastino"


def _pasta_cache(serie):
    del serie
    try:
        import radai_archive
        # GUARDA: uma rota nunca reaponta o TEMP do processo.
        alvo = os.path.join(radai_archive.pasta_temporaria_local(
            marcar_ambiente=False), PASTA_DO_CACHE)
        os.makedirs(alvo, exist_ok=True)
        return alvo
    except Exception:
        return ""


PASTA_DO_CACHE = "radai_miniaturas"


def _uid8(uid):
    u = str(uid or "")
    if not u:
        return "sem_uid"
    return hashlib.sha256(u.encode("utf-8", "replace")).hexdigest()[:24]


def etiqueta(serie, corte, lado=LADO, janela=JANELA_GRADE):
    arqs = (serie or {}).get("arquivos") or []
    i = max(0, min(int(corte), len(arqs) - 1)) if arqs else 0
    try:
        carimbo = int(os.path.getmtime(arqs[i]["caminho"]))
    except Exception:
        carimbo = 0
    crua = u"%s|%d|%d|%d|%s" % (_uid8((serie or {}).get("uid")), i, carimbo,
                                int(lado), str(janela or JANELA_GRADE))
    return u'"%s"' % hashlib.sha256(crua.encode("utf-8")).hexdigest()[:20]


def _arquivo_no_cache(cache, serie, corte, janela, lado):
    return os.path.join(cache, "%s_c%d_%s_%d.png" % (
        _uid8(serie.get("uid")), int(corte), str(janela), int(lado)))


def _do_disco(cache, serie, corte, janela=JANELA_GRADE, lado=LADO):
    if not cache:
        return b""
    arq = _arquivo_no_cache(cache, serie, corte, janela, lado)
    try:
        arqs = serie.get("arquivos") or []
        i = max(0, min(int(corte), len(arqs) - 1))
        if os.path.getmtime(arq) < os.path.getmtime(arqs[i]["caminho"]):
            return b""
        with open(arq, "rb") as f:
            return f.read()
    except Exception:
        return b""


def _para_disco(cache, serie, corte, dados, janela=JANELA_GRADE, lado=LADO):
    if not cache or not dados:
        return
    arq = _arquivo_no_cache(cache, serie, corte, janela, lado)
    try:
        tmp = arq + ".parcial"
        with open(tmp, "wb") as f:
            f.write(dados)
        os.replace(tmp, arq)
    except Exception:
        pass


def registrar_series(pasta, series):
    fora = {}
    for s in series or ():
        b = bilhete(pasta, s.get("uid"))
        with _TRAVA:
            _SERIES[str(b)] = s
        fora[s.get("uid")] = b
    return fora


def png_central(b, lado=LADO):
    pasta, uid = resolver(b)
    if pasta is None:
        return b"", {"erro": u"bilhete desconhecido (o programa reiniciou?)"}
    s = _serie_do_bilhete(b, pasta, uid)
    if s is None:
        return b"", {"erro": u"a série não está mais nesta pasta"}
    if (s.get("modalidade") or "").upper() in SEM_IMAGEM:
        return b"", {"sem_imagem": True, "modalidade": s.get("modalidade"),
                     "erro": u"%s não é série de imagem — não há corte para "
                             u"mostrar" % (s.get("modalidade") or u"esta série")}
    n = len(s.get("arquivos") or [])
    if not n:
        return b"", {"erro": u"série sem cortes"}
    i = central(n)
    janela = janela_do_visor(s.get("modalidade"))
    info = {"cortes": n, "corte": i, "janela": janela,
            "descricao": s.get("descricao"), "modalidade": s.get("modalidade"),
            "colorida": bool(s.get("colorida")),
            "captura": bool(s.get("captura")),
            "etag": etiqueta(s, i, lado, janela)}

    cache = _pasta_cache(s)
    guardado = _do_disco(cache, s, i, janela, lado)
    if guardado:
        info["de"] = "disco"
        return guardado, info

    dados, info2 = png(b, i, janela, lado)
    if not dados:
        info2.setdefault("etag", info["etag"])
        return dados, info2
    _para_disco(cache, s, i, dados, janela, lado)
    info["de"] = "lido"
    return dados, info


def central(n):
    return max(0, int(n) // 2)




def ordem_de_bisseccao(n):
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return []
    if n <= 0:
        return []
    fora = []
    fila = [(0, n)]
    k = 0
    while k < len(fila):
        lo, hi = fila[k]
        k += 1
        if lo >= hi:
            continue
        meio = (lo + hi) // 2
        fora.append(meio)
        fila.append((lo, meio))
        fila.append((meio + 1, hi))
    return fora


_JANELA_AUTO = {}


def _janela_auto(b, serie, arr_central=None):
    with _TRAVA:
        if str(b) in _JANELA_AUTO:
            return _JANELA_AUTO[str(b)]
    import numpy as np
    import pydicom
    arqs = serie.get("arquivos") or []
    centro, largura = 0.0, 1.0
    if arqs:
        if arr_central is not None:
            a = arr_central
        else:
            ds = _ler_corte(arqs[central(len(arqs))]["caminho"])
            a = _hu(ds)
        if a.ndim == 2 and a.size:
            lo, hi = np.percentile(a, [1.0, 99.0])
            lo, hi = float(lo), float(hi)
            if hi <= lo:
                hi = lo + 1.0
            centro, largura = (lo + hi) / 2.0, hi - lo
    with _TRAVA:
        _JANELA_AUTO[str(b)] = (centro, largura)
    return centro, largura


def serie_do_bilhete(b):
    pasta, uid = resolver(b)
    if pasta is None:
        return None
    return _serie_do_bilhete(b, pasta, uid)


def etiqueta_do_corte(b, corte, janela, lado=LADO_VISOR):
    pasta, uid = resolver(b)
    if pasta is None:
        return u""
    s = _serie_do_bilhete(b, pasta, uid)
    if s is None or not (s.get("arquivos") or []):
        return u""
    return etiqueta(s, corte, lado, janela)


def janela_do_visor(modalidade):
    return "mediastino" if str(modalidade or "").upper() == "CT" else "auto"


def preparar_visor(pasta, uid):
    pasta = str(pasta or "")
    uid = str(uid or "")
    if not pasta or not os.path.isdir(pasta):
        return {"erro": u"a pasta da série não está acessível"}
    b = bilhete(pasta, uid)
    s = _serie_do_bilhete(b, pasta, uid)
    if s is None:
        return {"erro": u"a série não está mais nesta pasta"}
    mod = (s.get("modalidade") or "").upper()
    if mod in SEM_IMAGEM:
        return {"sem_imagem": True, "modalidade": mod,
                "erro": u"esta série não tem imagem para mostrar"}
    n = len(s.get("arquivos") or [])
    if not n:
        return {"erro": u"série sem cortes"}
    return {"b": b, "cortes": n, "central": central(n),
            "janela": janela_do_visor(mod), "modalidade": mod,
            "cranial": sentido_cranial(s)}


def _z_do_corte(a):
    ipp = (a or {}).get("ipp")
    if not isinstance(ipp, (list, tuple)) or len(ipp) < 3:
        return None
    try:
        return float(ipp[2])
    except (TypeError, ValueError):
        return None


def sentido_cranial(serie):
    arqs = (serie or {}).get("arquivos") or ()
    if len(arqs) < 2:
        return 0
    z0, z1 = _z_do_corte(arqs[0]), _z_do_corte(arqs[-1])
    if z0 is None or z1 is None or abs(z1 - z0) < 1e-3:
        return 0
    # GUARDA: em LPS o +z e cranial; 1 quer dizer que o indice do corte cresce para cranial.
    return 1 if z1 > z0 else -1


_JA_REGISTRADAS = set()
_ORDEM_REGISTRADAS = []
_TETO_REGISTRADAS = 2000


def _log_da_estacao():
    import sys
    m = sys.modules.get("__main__")
    f = getattr(m, "wlog", None)
    if callable(f):
        return f

    def _stderr(linha):
        try:
            sys.stderr.write(u"%s\n" % linha)
        except Exception:
            pass
    return _stderr


_MARCA_CAMINHO = u"<caminho>"


def _linha_sem_caminho(linha, higienizar):
    limpa = higienizar(linha, ())[0]
    i = limpa.find(_MARCA_CAMINHO)
    if i < 0:
        return limpa
    antes = limpa[:i]
    resto = limpa[i + len(_MARCA_CAMINHO):]
    if antes.endswith(u'"'):
        j = resto.find(u'"')
        if j >= 0:
            return (antes + _MARCA_CAMINHO
                    + _linha_sem_caminho(resto[j:], higienizar))
    return antes + _MARCA_CAMINHO


def _sem_caminho(texto):
    try:
        import radai_records
        higienizar = radai_records.higienizar
        return u"\n".join(_linha_sem_caminho(ln, higienizar)
                          for ln in (u"%s" % (texto,)).split(u"\n"))
    except Exception:
        return u"(mensagem omitida: sem o higienizador de caminho)"


def _impressao_da_serie(serie):
    s = u"%s" % (serie if serie is not None else u"")
    if not s:
        return u""
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:16]


def registrar_falha(onde, exc, log=None, bilhete=u""):
    chave = (str(onde), type(exc).__name__, _impressao_da_serie(bilhete))
    with _TRAVA:
        if chave in _JA_REGISTRADAS:
            return False
        _JA_REGISTRADAS.add(chave)
        _ORDEM_REGISTRADAS.append(chave)
        while len(_ORDEM_REGISTRADAS) > _TETO_REGISTRADAS:
            _JA_REGISTRADAS.discard(_ORDEM_REGISTRADAS.pop(0))
    import traceback
    escrever = log or _log_da_estacao()
    quadros = traceback.extract_tb(getattr(exc, "__traceback__", None))
    linhas = [u"%s: falhou com %s (a causa sai uma vez so)"
              % (onde, type(exc).__name__)]
    for q in quadros[-8:]:
        linhas.append(u"    %s:%s %s" % (os.path.basename(q.filename or ""),
                                         q.lineno, q.name))
    linhas.append(u"    %s: %s" % (type(exc).__name__,
                                   _sem_caminho(str(exc))[:300]))
    for ln in linhas:
        try:
            escrever(ln)
        except Exception:
            pass
    return True
