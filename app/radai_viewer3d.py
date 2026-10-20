# -*- coding: utf-8 -*-
import os

import numpy as np

MAX_PONTOS = 4000
MAX_ESTRUTURAS = 6


def _superficie(m):
    from scipy import ndimage
    return m & ~ndimage.binary_erosion(m)


_FOLGA = 3


def _caixa(m, folga=_FOLGA):
    fatias, origem = [], []
    for eixo in range(3):
        outros = tuple(a for a in range(3) if a != eixo)
        idx = np.flatnonzero(m.any(axis=outros))
        lo = max(0, int(idx[0]) - folga)
        hi = min(m.shape[eixo], int(idx[-1]) + 1 + folga)
        fatias.append(slice(lo, hi))
        origem.append(lo)
    return tuple(fatias), np.asarray(origem, dtype=np.int64)


def _normais_locais(m, idx, espacamento, fator=1.5):
    Z, Y, X = m.shape
    ez, ey, ex = [float(e) for e in espacamento]
    raio_mm = fator * max(ez, ey, ex)
    rz, ry, rx = [max(1, int(raio_mm // e)) for e in (ez, ey, ex)]
    acc = np.zeros((len(idx), 3), dtype=np.float64)
    iz, iy, ix = idx[:, 0], idx[:, 1], idx[:, 2]
    for dz in range(-rz, rz + 1):
        z = iz + dz
        vz = (z >= 0) & (z < Z)
        zc = np.clip(z, 0, Z - 1)
        for dy in range(-ry, ry + 1):
            y = iy + dy
            vy = vz & (y >= 0) & (y < Y)
            yc = np.clip(y, 0, Y - 1)
            for dx in range(-rx, rx + 1):
                if dz == 0 and dy == 0 and dx == 0:
                    continue
                if ((dz * ez) ** 2 + (dy * ey) ** 2 + (dx * ex) ** 2
                        > raio_mm ** 2):
                    continue
                x = ix + dx
                v = vy & (x >= 0) & (x < X)
                dentro = m[zc, yc, np.clip(x, 0, X - 1)] & v
                acc[dentro] -= (dz * ez, dy * ey, dx * ex)
    norma = np.linalg.norm(acc, axis=1)
    norma[norma < 1e-9] = 1.0
    acc /= norma[:, None]
    return acc[:, ::-1]


_SEMENTE_AMOSTRA = 20260922


def _amostrar(n_total, max_pontos):
    n_total = int(n_total)
    if n_total <= int(max_pontos):
        return None
    passo = int(np.ceil(n_total / float(max_pontos)))
    base = np.arange(0, n_total, passo)
    desvio = np.random.default_rng(_SEMENTE_AMOSTRA).integers(
        0, passo, size=len(base))
    return np.minimum(base + desvio, n_total - 1)


def nuvem_de_mascara(mask, grade, cor=(120, 170, 255), max_pontos=MAX_PONTOS,
                     normal="sdf"):
    import radai_geom
    m = np.asarray(mask, dtype=bool)
    vazio = {"pontos": [], "normais": [], "cor": list(cor), "n_total": 0,
             "centro_mm": None}
    if not m.any():
        return vazio
    fatias, origem = _caixa(m)
    sub = m[fatias]
    sup = _superficie(sub)
    idx_local = np.argwhere(sup)
    if not len(idx_local):
        return vazio
    n_total = int(len(idx_local))
    escolha = _amostrar(n_total, max_pontos)
    if escolha is not None:
        idx_local = idx_local[escolha]

    if normal == "local":
        normais = _normais_locais(sub, idx_local, grade.spacing)
    else:
        try:
            d = radai_geom.distancia_com_sinal(sub, grade)
            gz, gy, gx = np.gradient(d, *grade.spacing)
            nz = gz[tuple(idx_local.T)]
            ny = gy[tuple(idx_local.T)]
            nx = gx[tuple(idx_local.T)]
            norma = np.sqrt(nz * nz + ny * ny + nx * nx)
            norma[norma < 1e-9] = 1.0
            normais = np.stack([nx / norma, ny / norma, nz / norma], axis=1)
        except Exception:
            normais = np.zeros((len(idx_local), 3), dtype=np.float32)

    esp = np.asarray(grade.spacing, dtype=np.float64)
    pts = (idx_local + origem).astype(np.float64) * esp
    centro = pts.mean(axis=0)
    pts = pts - centro
    pts = pts[:, ::-1]
    return {"pontos": [[round(float(v), 2) for v in p] for p in pts],
            "normais": [[round(float(v), 3) for v in q] for q in normais],
            "cor": [int(c) for c in cor], "n_total": n_total,
            "amostrados": int(len(idx_local)),
            "centro_mm": [round(float(v), 3) for v in centro]}


def recentrar(itens):
    validos = [it for it in (itens or [])
               if it.get("pontos") and it.get("centro_mm") is not None]
    if not validos:
        return itens
    absolutos = []
    for it in validos:
        c = np.asarray(it["centro_mm"], dtype=np.float64)[::-1]
        absolutos.append(np.asarray(it["pontos"], dtype=np.float64) + c)
    tudo = np.concatenate(absolutos, axis=0)
    meio = (tudo.min(axis=0) + tudo.max(axis=0)) / 2.0
    for it, p in zip(validos, absolutos):
        q = p - meio
        it["pontos"] = [[round(float(v), 2) for v in r] for r in q]
    return itens


def nuvem_da_serie(pasta, rs, estruturas, max_pontos=MAX_PONTOS):
    import radai_rt
    import radai_geom
    import engine

    nomes = [str(x) for x in (estruturas or [])][:MAX_ESTRUTURAS]
    if not nomes:
        return {"itens": [], "erro": ""}
    caminho_rs = rs if os.path.isabs(rs) else os.path.join(pasta, rs)
    try:
        sessao = radai_rt.abrir(pasta, caminho_rs, None)
    except Exception as e:
        return {"itens": [], "erro": "não consegui abrir a série: %s" % str(e)[:160]}
    itens = []
    try:
        grade = sessao.grade
        for nome in nomes:
            try:
                m = sessao.mascara_de(nome, sufixo="")
            except Exception:
                m = None
            if m is None or not np.asarray(m).any():
                continue
            base = engine.sem_sufixo(nome) if hasattr(engine, "sem_sufixo") else nome
            try:
                cor = engine._color(base, False)
            except Exception:
                cor = (120, 170, 255)
            d = nuvem_de_mascara(m, grade, cor=cor, max_pontos=max_pontos)
            if d["pontos"]:
                d["nome"] = nome
                d["volume_cm3"] = round(radai_geom.volume_cm3(m, grade), 2)
                itens.append(d)
        eixos = None
        try:
            st = list(getattr(grade, "sentido", ()) or ())
            if len(st) == 3:
                eixos = [st[2], st[1], st[0]]
        except Exception:
            eixos = None
    finally:
        try:
            sessao.fechar()
        except Exception:
            pass
    recentrar(itens)
    return {"itens": itens, "erro": "", "eixos": eixos}
