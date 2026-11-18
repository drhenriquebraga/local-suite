# -*- coding: utf-8 -*-
import json
import os
import tempfile
import time
import zipfile

import numpy as np

VERSAO_FORMATO = 1
PASTA = "_RadAI"
PREFIXO = "rotulos_"
EXTENSAO = ".npz"
# GUARDA: as duas tasks de vasos e vias aereas do pulmao devolvem nomes
# iguais; a antiga sai com sufixo para nao colidir com a nova.
SUFIXO_POR_TASK = {"lung_vessels_LEGACY": "_legacy"}


def nome_do_arquivo(uid):
    u = str(uid or "")
    return "%s%s%s" % (PREFIXO, u[-8:] if u else "semuid", EXTENSAO)


def caminho(pasta_serie, uid):
    return os.path.join(str(pasta_serie), PASTA, nome_do_arquivo(uid))


def _nome(task, rotulo, usados):
    nome = "%s%s" % (rotulo, SUFIXO_POR_TASK.get(task, ""))
    if nome in usados:
        nome = "%s__%s" % (nome, task)
    k = 2
    base = nome
    while nome in usados:
        nome = "%s_%d" % (base, k)
        k += 1
    return nome


def _volume_da_task(mapa):
    arr = getattr(mapa, "_arr", None)
    nomes = getattr(mapa, "_nomes", None)
    if arr is not None and isinstance(nomes, dict):
        a = np.asarray(arr)
        keep = np.zeros(int(a.max()) + 1 if a.size else 1, dtype=np.uint16)
        idx = {}
        for i, (rot, v) in enumerate(sorted(nomes.items(),
                                            key=lambda kv: kv[1]), start=1):
            if 0 <= int(v) < keep.size:
                keep[int(v)] = i
                idx[i] = rot
        vol = np.empty(a.shape, dtype=np.uint16)
        for z in range(len(a)):
            vol[z] = keep[np.clip(a[z], 0, keep.size - 1).astype(np.intp, copy=False)]
        return vol, idx
    vol, idx = None, {}
    for i, rot in enumerate(sorted(mapa), start=1):
        m = np.asarray(mapa[rot], dtype=bool)
        if vol is None:
            vol = np.zeros(m.shape, dtype=np.uint16)
        vol[m] = i
        idx[i] = rot
    return vol, idx


def mascaras_compactas(rotulos, tabela, forma=None, inicio=(0, 0, 0)):
    from scipy.ndimage import find_objects
    from engine import MascaraCompacta
    import radai_geom
    if not tabela:
        return {}
    a = np.asarray(rotulos)
    forma = tuple(a.shape if forma is None else forma)
    caixas = (find_objects(a, max_label=max(tabela))
              if a.dtype.kind in "iu" else None)
    mascaras = {}
    for indice, nome in tabela.items():
        if caixas is None:
            parcial = a == indice
            caixa = radai_geom._bbox_folgado(parcial, (0, 0, 0))
        else:
            caixa = caixas[indice - 1]
        if caixa is not None:
            global_ = tuple(slice(c.start + i, c.stop + i) for c, i in zip(caixa, inicio))
            mascaras[nome] = MascaraCompacta(forma, global_, a[caixa] == indice)
    return mascaras


def _tasks_do_mapa(cruas, achados):
    achados = set(achados or ())
    usados = set()
    for n, task in enumerate(sorted(cruas or {})):
        mapa = cruas[task]
        if not mapa:
            continue
        vol, idx = _volume_da_task(mapa)
        if vol is None or not idx:
            continue
        chave = "t%d" % n
        tabela = []
        for i in sorted(idx):
            nome = _nome(task, idx[i], usados)
            usados.add(nome)
            tabela.append({"chave": chave, "indice": int(i), "nome": nome,
                           "task": task, "rotulo": idx[i],
                           "achado": task in achados})
        yield chave, vol, tabela
        del vol


def montar(cruas, achados=()):
    volumes, tabela = {}, []
    for chave, vol, entradas in _tasks_do_mapa(cruas, achados):
        volumes[chave] = vol
        tabela.extend(entradas)
    return volumes, tabela


def geometria_de(ref):
    if ref is None:
        return None
    try:
        return {"spacing": [float(v) for v in ref.GetSpacing()],
                "origin": [float(v) for v in ref.GetOrigin()],
                "direction": [float(v) for v in ref.GetDirection()],
                "size": [int(v) for v in ref.GetSize()]}
    except Exception:
        return None


def gravar(pasta_serie, uid, cruas, ref=None, protocolos=(), modalidade="",
           achados=(), versao=""):
    tabela = []
    meta = {"formato": VERSAO_FORMATO, "uid": str(uid or ""),
            "protocolos": [str(p) for p in (protocolos or ())],
            "modalidade": str(modalidade or ""),
            "geometria": geometria_de(ref), "versao": str(versao or ""),
            "gravado": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tabela": tabela}
    alvo = caminho(pasta_serie, uid)
    os.makedirs(os.path.dirname(alvo), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(alvo), suffix=".parcial")
    try:
        with os.fdopen(fd, "wb") as f, zipfile.ZipFile(
                f, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as pacote:
            for chave, vol, entradas in _tasks_do_mapa(cruas, achados):
                with pacote.open(chave + ".npy", "w", force_zip64=True) as dest:
                    np.lib.format.write_array(dest, vol, allow_pickle=False)
                tabela.extend(entradas)
                del vol
            if not tabela:
                raise ValueError(u"nenhuma task com rótulo para gravar")
            dados = json.dumps(meta, ensure_ascii=True).encode("ascii")
            with pacote.open("_meta.npy", "w") as dest:
                np.lib.format.write_array(dest, np.frombuffer(dados, np.uint8),
                                          allow_pickle=False)
        os.replace(tmp, alvo)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return alvo


class Mapa(object):

    def __init__(self, meta, volumes):
        self.meta = meta
        self.tabela = list(meta.get("tabela") or ())
        self._vol = volumes
        self._por_nome = dict((t["nome"], t) for t in self.tabela)
        self.nomes = [t["nome"] for t in self.tabela]

    def mascara(self, nome):
        t = self._por_nome[nome]
        return np.asarray(self._vol[t["chave"]]) == int(t["indice"])

    def achados(self):
        return [t["nome"] for t in self.tabela if t.get("achado")]


def _ler_volume(pacote, nome, limite_em_ram):
    from math import prod
    from radai_geom import _campo
    fmt = np.lib.format
    with pacote.open(nome) as arq:
        versao = fmt.read_magic(arq)
        if versao == (1, 0):
            forma, fortran, dtype = fmt.read_array_header_1_0(arq)
        elif versao == (2, 0):
            forma, fortran, dtype = fmt.read_array_header_2_0(arq)
        else:
            raise ValueError("versao NPY nao suportada")
        if len(forma) != 3 or any(n < 0 for n in forma) or dtype.kind not in "iu":
            raise ValueError("mapa de rotulos invalido")
        total = prod(forma)
        if arq.tell() + total * dtype.itemsize != pacote.getinfo(nome).file_size:
            raise ValueError("tamanho de mapa invalido")
        dados = _campo((total,), dtype, limite_em_ram=limite_em_ram)
        destino = memoryview(dados).cast("B")
        pos = 0
        while pos < len(destino):
            n = arq.readinto(destino[pos:pos + (1 << 20)])
            if not n:
                raise ValueError("mapa de rotulos incompleto")
            pos += n
        return dados.reshape(forma, order="F" if fortran else "C")


def ler(pasta_serie, uid):
    alvo = caminho(pasta_serie, uid)
    if not os.path.isfile(alvo):
        return None
    try:
        with zipfile.ZipFile(alvo) as pacote:
            with pacote.open("_meta.npy") as cab:
                meta = json.loads(bytes(np.lib.format.read_array(cab, allow_pickle=False)).decode("ascii"))
            if not _meta_compativel(meta, uid):
                return None
            volumes = {}
            disponivel = 64 << 20
            for nome in pacote.namelist():
                if nome != "_meta.npy" and nome.endswith(".npy"):
                    vol = _ler_volume(pacote, nome, min(disponivel, 32 << 20))
                    if not isinstance(vol, np.memmap):
                        disponivel -= vol.nbytes
                    volumes[nome[:-4]] = vol
    except MemoryError:
        raise
    except Exception:
        return None
    return Mapa(meta, volumes)


def existe(pasta_serie, uid):
    return ler(pasta_serie, uid) is not None


def _meta_compativel(m, uid):
    return (isinstance(m, dict)
            and int(m.get("formato") or 0) == VERSAO_FORMATO
            and (not uid or not m.get("uid") or str(m["uid"]) == str(uid)))


def meta(pasta_serie, uid):
    alvo = caminho(pasta_serie, uid)
    if not os.path.isfile(alvo):
        return None
    try:
        with np.load(alvo, allow_pickle=False) as z:
            m = json.loads(bytes(z["_meta"]).decode("ascii"))
            return m if _meta_compativel(m, uid) else None
    except Exception:
        return None
