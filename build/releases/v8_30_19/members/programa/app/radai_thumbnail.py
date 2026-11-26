# -*- coding: utf-8 -*-
import hashlib
import hmac
import os
import threading
import tempfile
from collections import OrderedDict

LADO = 192

LADO_VISOR = 512

_TETO_CACHE = 240
_TETO_PNG_BYTES = 32 * 1024 * 1024
_TETO_INDICES = 24000
_TETO_SERIES = 500
_TETO_BILHETES = 4096

SEM_IMAGEM = frozenset(["RTSTRUCT", "RTPLAN", "RTDOSE", "RTRECORD", "SR", "KO",
                        "PR", "REG", "SEG", "FID"])

_SEGREDO = os.urandom(32)
_MAPA = OrderedDict()
_CACHE = OrderedDict()
_SERIES = OrderedDict()
_TRAVA = threading.Lock()


def bilhete(pasta, uid):
    chave = u"%s\x00%s" % (pasta, uid)
    b = hmac.new(_SEGREDO, chave.encode("utf-8", "replace"),
                 hashlib.sha256).hexdigest()[:32]
    with _TRAVA:
        _MAPA[b] = (pasta, uid)
        _MAPA.move_to_end(b)
        if len(_MAPA) > _TETO_BILHETES:
            antigo, _ = _MAPA.popitem(last=False)
            _SERIES.pop(antigo, None)
            _JANELA_AUTO.pop(antigo, None)
            _FONTE_AUTO.pop(antigo, None)
    return b


def resolver(b):
    with _TRAVA:
        chave = str(b or "")
        if chave in _MAPA:
            _MAPA.move_to_end(chave)
            return _MAPA[chave]
        return None, None


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
    ds = pydicom.dcmread(caminho, force=True, defer_size=128 * 1024)
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
    frames = int(getattr(ds, "NumberOfFrames", 1) or 1)
    if frames > 1:
        from pydicom.pixels import pixel_array
        origem = getattr(ds, "filename", None) or ds
        a = pixel_array(origem, index=frames // 2,
                        transfer_syntax_uid=ds.file_meta.TransferSyntaxUID)
    else:
        a = ds.pixel_array
    foto = str(getattr(ds, "PhotometricInterpretation", "") or "").upper()
    if foto.startswith("PALETTE"):
        from pydicom.pixels import apply_color_lut
        a = apply_color_lut(a, ds)
    a = np.asarray(a, dtype=np.float32)
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


def _mesmo_corte(ds, serie, arquivo):
    if str(getattr(ds, "SeriesInstanceUID", "") or "") != str(serie["uid"]):
        return False
    return not arquivo.get("sop") or str(getattr(ds, "SOPInstanceUID", "") or "") == arquivo["sop"]


def _lembrar_serie(b, serie):
    _SERIES[b] = serie
    _SERIES.move_to_end(b)
    arquivos = sum(len(s.get("arquivos") or ()) for s in _SERIES.values())
    while len(_SERIES) > _TETO_SERIES or arquivos > _TETO_INDICES:
        antiga, removida = _SERIES.popitem(last=False)
        arquivos -= len(removida.get("arquivos") or ())
        _JANELA_AUTO.pop(antiga, None)
        _FONTE_AUTO.pop(antiga, None)


def _serie_do_bilhete(b, pasta, uid, parar=None):
    with _TRAVA:
        s = _SERIES.get(str(b))
        if s is not None:
            _SERIES.move_to_end(str(b))
            return s
    import radai_dicom
    r = radai_dicom.varrer(pasta, parar=parar) if parar else radai_dicom.varrer(pasta)
    for cand in r["series"]:
        if cand["uid"] == uid:
            with _TRAVA:
                if str(b) not in _SERIES:
                    _lembrar_serie(str(b), cand)
                else:
                    return _SERIES[str(b)]
            return cand
    return None


def png(b, corte, janela="mediastino", lado=LADO, parar=None):
    import radai_recon3d
    from radai_dicom import verificar_leitura
    verificar_leitura(parar)

    pasta, uid = resolver(b)
    if pasta is None:
        return b"", {"erro": u"bilhete desconhecido (o programa reiniciou?)"}

    s = _serie_do_bilhete(b, pasta, uid, parar)
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
    tag = etiqueta(s, i, lado, janela)
    if not tag:
        return b"", {"erro": u"o corte não está mais disponível"}
    chave = (str(b), tag)
    with _TRAVA:
        if chave in _CACHE:
            _CACHE.move_to_end(chave)
            return _CACHE[chave]

    from radai_pixels_lote import pixels
    try:
        verificar_leitura(parar)
        arr = pixels.corte(s, i)
        if arr is None:
            ds = _ler_corte(arqs[i]["caminho"])
            if not _mesmo_corte(ds, s, arqs[i]):
                return b"", {"erro": u"a série mudou desde a seleção"}
            verificar_leitura(parar)
            arr = _hu(ds)
    except Exception as e:
        return b"", {"erro": u"não consegui decodificar o pixel (%s): %s"
                             % (arqs[i].get("sintaxe") or u"sintaxe ausente",
                                type(e).__name__),
                     "cortes": n, "corte": i}

    verificar_leitura(parar)
    if str(janela) == "auto":
        limites = _janela_auto(b, s, arr if i == central(n) else None)
        if limites is None:
            return b"", {"erro": u"a série mudou desde a seleção"}
        centro, largura = limites
    else:
        centro, largura = radai_recon3d.JANELAS.get(
            janela, radai_recon3d.JANELAS["mediastino"])
    dados = radai_recon3d.para_png(_reduzir(arr, lado), centro, largura)
    info = {"cortes": n, "corte": i, "janela": janela, "etag": tag,
            "descricao": s["descricao"], "modalidade": s["modalidade"]}
    if tag != etiqueta(s, i, lado, janela):
        return b"", {"erro": u"a série mudou durante a leitura do corte"}
    with _TRAVA:
        _CACHE[chave] = (dados, info)
        _CACHE.move_to_end(chave)
        total = sum(len(v[0]) for v in _CACHE.values())
        while len(_CACHE) > _TETO_CACHE or total > _TETO_PNG_BYTES:
            _, removido = _CACHE.popitem(last=False)
            total -= len(removido[0])
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


def _fonte(a):
    caminho = os.path.normcase(os.path.abspath(a["caminho"]))
    st = os.stat(caminho)
    return caminho, a.get("sop") or "", st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino


def etiqueta(serie, corte, lado=LADO, janela=JANELA_GRADE):
    arqs = (serie or {}).get("arquivos") or []
    i = max(0, min(int(corte), len(arqs) - 1)) if arqs else 0
    try:
        fonte = _fonte(arqs[i])
        centro = central(len(arqs))
        meio = _fonte(arqs[centro]) if janela == "auto" and centro != i else fonte
    except (OSError, IndexError, TypeError, KeyError, ValueError):
        return ""
    crua = repr((serie.get("uid"), len(arqs), i, fonte, meio, lado, janela))
    return '"' + hashlib.sha256(crua.encode("utf-8", "surrogatepass")).hexdigest()[:32] + '"'


def _arquivo_no_cache(cache, serie, corte, lado, tag):
    return os.path.join(cache, "%s_c%d_%s_%d.png" % (
        _uid8(serie.get("uid")), corte, tag.strip('"'), lado))


def _do_disco(cache, serie, corte, lado, tag):
    if not cache or not tag:
        return b""
    try:
        arq = _arquivo_no_cache(cache, serie, corte, lado, tag)
        if os.path.getmtime(arq) < os.path.getmtime(serie["arquivos"][corte]["caminho"]):
            return b""
        with open(arq, "rb") as f:
            dados = f.read(1024 * 1024 + 1)
        return dados if len(dados) <= 1024 * 1024 and dados.startswith(b"\x89PNG\r\n\x1a\n") else b""
    except Exception:
        return b""


def _para_disco(cache, serie, corte, lado, tag, dados):
    if not cache or not tag or not dados:
        return
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=cache, suffix=".parcial", delete=False) as f:
            tmp = f.name
            f.write(dados)
        os.replace(tmp, _arquivo_no_cache(cache, serie, corte, lado, tag))
        tmp = None
    except Exception:
        pass
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def registrar_series(pasta, series):
    fora = {}
    for s in series or ():
        b = bilhete(pasta, s.get("uid"))
        with _TRAVA:
            _lembrar_serie(str(b), s)
        fora[s.get("uid")] = b
    return fora


def png_central(b, lado=LADO, parar=None):
    from radai_dicom import verificar_leitura
    verificar_leitura(parar)
    pasta, uid = resolver(b)
    if pasta is None:
        return b"", {"erro": u"bilhete desconhecido (o programa reiniciou?)"}
    s = _serie_do_bilhete(b, pasta, uid, parar)
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
    verificar_leitura(parar)
    guardado = _do_disco(cache, s, i, lado, info["etag"])
    if guardado:
        info["de"] = "disco"
        return guardado, info

    dados, info2 = png(b, i, janela, lado, parar=parar)
    if not dados:
        info2.setdefault("etag", info["etag"])
        return dados, info2
    info["etag"] = info2["etag"]
    verificar_leitura(parar)
    _para_disco(cache, s, i, lado, info["etag"], dados)
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
_FONTE_AUTO = {}


def _janela_auto(b, serie, arr_central=None):
    arqs = serie.get("arquivos") or []
    fonte = _fonte(arqs[central(len(arqs))]) if arqs else None
    with _TRAVA:
        if str(b) in _JANELA_AUTO and _FONTE_AUTO.get(str(b)) == fonte:
            return _JANELA_AUTO[str(b)]
    import numpy as np
    centro, largura = 0.0, 1.0
    if arqs:
        if arr_central is not None:
            a = arr_central
        else:
            from radai_pixels_lote import pixels
            i = central(len(arqs))
            a = pixels.corte(serie, i)
            if a is None:
                arquivo = arqs[i]
                ds = _ler_corte(arquivo["caminho"])
                if not _mesmo_corte(ds, serie, arquivo):
                    return None
                a = _hu(ds)
        if a.ndim == 2 and a.size:
            lo, hi = np.percentile(a, [1.0, 99.0])
            lo, hi = float(lo), float(hi)
            if hi <= lo:
                hi = lo + 1.0
            centro, largura = (lo + hi) / 2.0, hi - lo
    with _TRAVA:
        _JANELA_AUTO[str(b)] = (centro, largura)
        _FONTE_AUTO[str(b)] = fonte
    return centro, largura


def serie_do_bilhete(b, parar=None):
    pasta, uid = resolver(b)
    if pasta is None:
        return None
    return _serie_do_bilhete(b, pasta, uid, parar)


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
