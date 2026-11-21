# -*- coding: utf-8 -*-
"""Completa as extremidades costais solicitadas preservando o mapa original do TS."""
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

import radai_ribs_predict
import radai_cache_tasks as cache


LADOS = ("left", "right")
COSTELAS = tuple(f"rib_{lado}_{n}" for lado in LADOS for n in range(1, 13))
VERTEBRAS = tuple(f"vertebrae_T{n}" for n in range(1, 13))
_NOME = {n + delta: f"rib_{lado}_{n}" for lado, delta in (("left", 0), ("right", 13))
         for n in range(1, 13)}
_ESTRUTURA = np.ones((3, 3, 3), dtype=bool)


def _pedidos(destinos):
    if isinstance(destinos, str):
        destinos = [destinos]
    nomes = {str(x).strip().lower() for x in (destinos or ())}
    pedidos = set()
    for lado, abreviado in (("left", "l"), ("right", "r")):
        grupo = bool(nomes & {"ribs", "ribs_" + lado, "ribs_" + abreviado})
        for n in range(1, 13):
            rot = f"rib_{lado}_{n}"
            if grupo or rot in nomes or f"rib{n:02d}_{abreviado}" in nomes:
                pedidos.add(rot)
    return pedidos


def _limites(mask):
    if hasattr(type(mask), "limites_ativos"):
        lim = mask.limites_ativos()
        return None if lim is None else tuple(slice(int(a), int(b) + 1) for a, b in lim)
    arr = np.asarray(mask)
    caixa = ndimage.find_objects(arr.astype(bool, copy=False).view(np.uint8), max_label=1)
    return caixa[0] if caixa else None


def _parte(mask, caixa):
    if hasattr(type(mask), "recorte"):
        return np.asarray(mask.recorte(caixa), dtype=bool)
    return np.asarray(mask[caixa], dtype=bool)


def _grade(ref):
    sp = np.array(ref.GetSpacing(), dtype=float)
    forma = np.array(ref.GetSize()[::-1], dtype=int)
    dir_ = np.array(ref.GetDirection(), dtype=float).reshape(3, 3)
    origem = np.array(ref.GetOrigin(), dtype=float)
    if (np.any(~np.isfinite(sp)) or np.any(sp <= 0) or not np.all(np.isfinite(origem))
            or not np.allclose(dir_.T @ dir_, np.eye(3), atol=1e-4)):
        raise ValueError("Geometria física da TC inválida.")
    # As colunas abaixo recebem índices do array SimpleITK em ordem z, y, x.
    matriz = (dir_ * sp)[:, ::-1]
    return forma, sp[::-1], matriz, origem


def _pontas(mascaras, forma, esp, matriz, origem):
    pontas = {}
    for i, nome in _NOME.items():
        mask = mascaras.get(nome)
        if mask is None:
            continue
        if tuple(mask.shape) != tuple(forma):
            raise ValueError("Grade incompatível para " + nome)
        caixa = _limites(mask)
        if caixa is None:
            continue
        coords = np.column_stack(np.nonzero(_parte(mask, caixa)))
        if not len(coords):
            continue
        coords += [s.start for s in caixa]
        xyz = coords @ matriz.T + origem
        posterior = xyz[:, 1] >= np.quantile(xyz[:, 1], .70)
        post_x = xyz[posterior, 0]
        med = np.quantile(post_x, .02 if i < 13 else .98)
        parte = posterior & (xyz[:, 0] <= med if i < 13 else xyz[:, 0] >= med)
        ijk = np.median(coords[parte], axis=0)
        ponta = np.median(xyz[parte], axis=0)
        # Qualquer face da aquisição pode truncar um extremo, inclusive FOV
        # lateral/anterior ou volumes com ordem de aquisição invertida.
        borda = float(np.min(np.minimum(ijk, forma - 1 - ijk) * esp))
        pontas[i] = (ijk, ponta, borda)
    return pontas


def _caixa_posterior(pontas, forma, matriz):
    pts = np.array([p[0] for p in pontas.values()])
    folga = np.ceil(np.abs(np.linalg.inv(matriz)) @ [26., 42., 26.]).astype(int)
    lo = np.maximum(0, np.floor(pts.min(axis=0)).astype(int) - folga)
    hi = np.minimum(forma, np.ceil(pts.max(axis=0)).astype(int) + folga + 1)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def _mapa(mascaras, nomes, caixa, forma):
    vol = np.zeros(tuple(c.stop - c.start for c in caixa), dtype=np.uint8)
    for chave, nome in nomes.items():
        mask = mascaras.get(nome)
        if mask is None:
            continue
        if tuple(mask.shape) != tuple(forma):
            raise ValueError("Grade incompatível para " + nome)
        vol[_parte(mask, caixa)] = chave
    return vol


def _ancoras(pred, base):
    juntos = (pred > 0) & (pred <= 26) & (base > 0)
    votos = np.bincount(pred[juntos].astype(np.int32) * 27 + base[juntos],
                        minlength=27 * 27).reshape(27, 27)
    pares = []
    # A 13ª costela eventual não deve ser incorporada à 12ª do outro modelo.
    for i in _NOME:
        total = int(votos[i].sum())
        if total < 20:
            continue
        destino = int(np.argmax(votos[i]))
        if (i < 13) == (destino < 13) and votos[i, destino] >= .75 * total:
            pares.append((i, destino))
    return {dest: src for src, dest in pares if not any(
        outro != src and (outro < 13) == (src < 13) and
        (alvo == dest or (outro - src) * (alvo - dest) < 0)
        for outro, alvo in pares)}


def _eixo_fisico(coords, coef, zero):
    valor = zero
    for c, k in zip(coords, coef):
        if k:
            valor = valor + c * k
    return valor


def _mapa_unido(mask, acrescimo, caixa, forma):
    from engine import MascaraCompacta
    idx = np.column_stack(np.nonzero(acrescimo))
    ini = np.array([s.start for s in caixa])
    lo, hi = idx.min(axis=0) + ini, idx.max(axis=0) + ini + 1
    antes = _limites(mask)
    lo = np.minimum(lo, [s.start for s in antes])
    hi = np.maximum(hi, [s.stop for s in antes])
    uniao = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))
    arr = _parte(mask, uniao).copy()
    arr[tuple((idx + ini - lo).T)] = True
    return MascaraCompacta(tuple(forma), uniao, arr)


def _calcular(ref, mascaras, solicitados, info, dispositivo, python_exe, pasta_pesos, vetos):
    forma, esp, matriz, origem = _grade(ref)
    resumo = info["por_costela"]
    pontas = _pontas(mascaras, forma, esp, matriz, origem)
    elegiveis = {}
    for i, nome in _NOME.items():
        if nome not in solicitados:
            continue
        if i not in pontas:
            resumo[nome]["estado"] = "sem_mascara_ts"
        else:
            resumo[nome]["distancia_borda_mm"] = round(pontas[i][2], 2)
            if pontas[i][2] < 10.:
                resumo[nome]["estado"] = "limite_do_campo"
            else:
                elegiveis[i] = pontas[i][1]
    if not elegiveis:
        info["motivo"] = "Nenhuma ponta solicitada tem máscara e distância suficiente à borda da TC."
        return {}
    caixa = _caixa_posterior(pontas, forma, matriz)
    info["caixa_xyz"] = [[s.start, s.stop] for s in caixa[::-1]]
    base = _mapa(mascaras, _NOME, caixa, forma)
    vert = _mapa(mascaras, dict(enumerate(VERTEBRAS, 1)), caixa, forma)
    niveis_presentes = set(np.unique(vert)) - {0}
    for i in list(elegiveis):
        n = i if i < 13 else i - 13
        if not niveis_presentes.intersection((n, n - 1)):
            resumo[_NOME[i]]["estado"] = "sem_referencia_vertebral"
            del elegiveis[i]
    info["avaliaveis"] = len(elegiveis)
    if not elegiveis:
        info["motivo"] = "As vértebras necessárias para proteger a articulação estão ausentes."
        return {}
    inicio = np.array([s.start for s in caixa])
    def fontes():
        pasta = radai_ribs_predict.localizar(pasta_pesos)
        return [pasta / n for n in radai_ribs_predict.ARQUIVOS] + [Path(radai_ribs_predict.__file__)]

    def executar():
        mapa = radai_ribs_predict.predizer(ref[caixa[::-1]], dispositivo, python_exe, pasta_pesos)
        if mapa.shape != base.shape or mapa.dtype.kind not in "iu" or mapa.min() < 0 or mapa.max() > 27:
            raise ValueError("Predição incompatível com a caixa posterior.")
        return mapa.astype(np.uint8, copy=False)

    dados_cache = {}
    rot = cache.rotulos_de_motor("moose_ribs", [s.start for s in caixa] + [s.stop for s in caixa],
                                 base.shape, dispositivo, "MOOSE-Dataset444-v1", fontes, executar,
                                 dados=dados_cache)
    if dados_cache.get("do_cache"):
        info["do_cache"] = True
    if rot.shape != base.shape or rot.dtype.kind not in "iu" or rot.min() < 0 or rot.max() > 27:
        raise ValueError("Predição incompatível com a caixa posterior.")
    anc = _ancoras(rot, base)
    dist_comum = ndimage.distance_transform_edt(base == 0, sampling=esp).astype(np.float32)
    coords = np.ogrid[tuple(slice(0, n) for n in base.shape)]
    xyz0 = origem + matriz @ inicio
    x, y, z = [_eixo_fisico(coords, m, o) for m, o in zip(matriz, xyz0)]
    ocupados = (base != 0).copy()
    alteradas = {}
    for i, (px, py, pz) in elegiveis.items():
        nome = _NOME[i]
        entrada = resumo[nome]
        if i not in anc:
            entrada["estado"] = "ancora_ambigua"
            continue
        n = i if i < 13 else i - 13
        viz = vert == n
        if n > 1:
            viz |= vert == n - 1
        centro = float(np.median(np.column_stack(np.nonzero(viz)) @ matriz[0] + xyz0[0]))
        # Dois voxels no eixo esquerda-direita na grade de referência da bancada;
        # a tolerância clínica permanece física em aquisições oblíquas/anisotrópicas.
        lateral = ((x >= centro) & (x <= px + 3.125) if i < 13
                   else (x <= centro) & (x >= px - 3.125))
        dist = ndimage.distance_transform_edt(base != i, sampling=esp)
        ext = ((rot == anc[i]) & (base == 0) & lateral
               & (y >= py - 42.) & (y <= py + 12.) & (np.abs(z - pz) <= 18.)
               & (dist <= 43.) & (dist <= dist_comum + 3.)
               & (ndimage.distance_transform_edt(~viz, sampling=esp) <= 37.))
        info["voxels_vetados_vertebra"] += int(np.count_nonzero(ext & (vert != 0)))
        comp, count = ndimage.label(ext & (vert == 0) & ~ocupados, structure=_ESTRUTURA)
        if count:
            contato = np.unique(comp[ndimage.binary_dilation(base == i, structure=_ESTRUTURA)])
            contato = contato[contato > 0]
        if not count or not len(contato):
            entrada["estado"] = "sem_extensao_conectada"
            continue
        sizes = np.bincount(comp.ravel())
        escolhido = int(contato[np.argmax(sizes[contato])])
        keep = comp == escolhido
        if vetos is not None:
            # A guarda segue a extremidade que efetivamente cresceu. Inclui
            # a vizinhança lida pelo HU e pela suavização, sem vetar qualquer
            # voxel costal original do TS, mesmo onde os modelos discordam.
            from engine import BANDA_REFINO_MM, MascaraCompacta, SUAVIZACAO
            halo = np.ceil((BANDA_REFINO_MM + 3 * SUAVIZACAO[nome]) / esp).astype(int) + 2
            limites = ndimage.find_objects(keep.view(np.uint8), max_label=1)[0]
            janela = tuple(slice(max(0, s.start - h), min(k, s.stop + h))
                           for s, h, k in zip(limites, halo, keep.shape))
            proibido = (vert[janela] != 0) & (base[janela] == 0)
            if proibido.any():
                caixa_nativa = tuple(slice(s.start + j.start, s.start + j.stop)
                                     for s, j in zip(caixa, janela))
                vetos[nome] = MascaraCompacta(forma, caixa_nativa, proibido)
        voxels = int(sizes[escolhido])
        alteradas[nome] = _mapa_unido(mascaras[nome], keep, caixa, forma)
        ocupados |= keep
        entrada.update(estado="aplicado", voxels=voxels)
        info["voxels_acrescidos"] += voxels
    return alteradas


def refinar(ref, mascaras, destinos, *, dispositivo="cpu", python_exe=None, pasta_pesos=None, log=None,
            vetos=None):
    """Retorna somente as máscaras individuais alteradas. Nenhuma entrada é modificada."""
    ini = time.monotonic()
    solicitados = _pedidos(destinos)
    info = dict(estado="ignorado", motivo="", solicitadas=len(solicitados), avaliaveis=0, corrigidas=0,
                voxels_acrescidos=0, voxels_vetados_vertebra=0,
                por_costela={s: dict(estado="pendente", voxels=0) for s in sorted(solicitados)})
    alteradas = {}
    try:
        if solicitados:
            locais = {} if vetos is not None else None
            alteradas = _calcular(ref, mascaras, solicitados, info, dispositivo, python_exe, pasta_pesos, locais)
            if locais:
                from engine import _uniao_compacta
                for lado in LADOS:
                    grupo = [m for k, m in locais.items() if k.startswith("rib_" + lado + "_")]
                    if grupo:
                        locais["ribs_" + lado] = _uniao_compacta(grupo, grupo[0].shape)
                vetos.update(locais)
        else:
            info["motivo"] = "Sem costelas no destino."
        info["corrigidas"] = len(alteradas)
        if alteradas:
            info["estado"] = "aplicado" if len(alteradas) == len(solicitados) else "parcial"
        if not info["motivo"]:
            info["motivo"] = f"{len(alteradas)} de {len(solicitados)} extremidades costais complementadas."
    except cache.ReprocessamentoSemMapa:
        raise
    except Exception as exc:
        alteradas = {}
        info.update(estado="falha", motivo=f"{type(exc).__name__}: {str(exc)[:320]}",
                    corrigidas=0, voxels_acrescidos=0)
        for item in info["por_costela"].values():
            if item["estado"] in ("aplicado", "pendente"):
                item.update(estado="falha", voxels=0)
    info["segundos"] = round(time.monotonic() - ini, 3)
    if log:
        log("MOOSE costelas: " + info["motivo"])
    return alteradas, info
