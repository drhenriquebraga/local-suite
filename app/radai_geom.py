# -*- coding: utf-8 -*-
import numpy as np
from scipy import ndimage

VERSAO_LIB = "1.0"

LADOS = ("ant", "post", "esq", "dir", "sup", "inf")
_OPOSTO = {"ant": "post", "post": "ant", "esq": "dir", "dir": "esq",
           "sup": "inf", "inf": "sup"}
_ATALHOS = {"lat": ("esq", "dir"), "ap": ("ant", "post"), "si": ("sup", "inf"),
            "cc": ("sup", "inf")}


class Grade(object):

    def __init__(self, spacing_zyx, sentido=("sup", "post", "esq")):
        sp = tuple(float(v) for v in spacing_zyx)
        if len(sp) != 3 or min(sp) <= 0:
            raise ValueError("spacing_zyx invalido: %r" % (spacing_zyx,))
        st = tuple(str(s).lower() for s in sentido)
        if len(st) != 3 or any(s not in LADOS for s in st):
            raise ValueError("sentido invalido: %r" % (sentido,))
        self.spacing = sp
        self.sentido = st

    def eixo_sinal(self, lado):
        lado = str(lado).lower()
        if lado not in LADOS:
            raise ValueError("direcao desconhecida: %r (use %s)" % (lado, ", ".join(LADOS)))
        for eixo, s in enumerate(self.sentido):
            if s == lado:
                return eixo, 1
            if _OPOSTO[s] == lado:
                return eixo, -1
        raise ValueError("direcao %r nao mapeada pelo sentido %r" % (lado, self.sentido))

    def mm_para_voxels(self, mm, eixo):
        return int(round(float(mm) / self.spacing[eixo]))

    @property
    def volume_voxel_mm3(self):
        return self.spacing[0] * self.spacing[1] * self.spacing[2]

    @classmethod
    def de_sitk(cls, imagem):
        sp = imagem.GetSpacing()
        d = list(imagem.GetDirection())
        eixo_lps = ({1: "esq", -1: "dir"}, {1: "post", -1: "ant"}, {1: "sup", -1: "inf"})
        sentido_xyz = []
        for j in range(3):
            coluna = [d[0 * 3 + j], d[1 * 3 + j], d[2 * 3 + j]]
            i_dom = int(np.argmax(np.abs(coluna)))
            sentido_xyz.append(eixo_lps[i_dom][1 if coluna[i_dom] >= 0 else -1])
        return cls((sp[2], sp[1], sp[0]), tuple(reversed(sentido_xyz)))

    def __repr__(self):
        return "Grade(spacing_zyx=%r, sentido=%r)" % (self.spacing, self.sentido)


def _bool(mask):
    a = np.asarray(mask)
    if a.ndim != 3:
        raise ValueError("mascara deve ser 3D (z,y,x); recebi ndim=%d" % a.ndim)
    return a.astype(bool, copy=False)


def _normalizar_margem(mm, permitir_zero=True):
    lados = dict((l, 0.0) for l in LADOS)
    if isinstance(mm, (int, float)):
        for l in LADOS:
            lados[l] = float(mm)
    elif isinstance(mm, dict):
        for chave, valor in mm.items():
            k = str(chave).lower()
            if k in ("iso", "todos"):
                alvos = LADOS
            elif k in _ATALHOS:
                alvos = _ATALHOS[k]
            elif k in ("lat_esq", "lateral_esq"):
                alvos = ("esq",)
            elif k in ("lat_dir", "lateral_dir"):
                alvos = ("dir",)
            elif k in LADOS:
                alvos = (k,)
            else:
                raise ValueError("chave de margem desconhecida: %r" % (chave,))
            for a in alvos:
                lados[a] = float(valor)
    else:
        raise TypeError("margem deve ser numero ou dict; recebi %s" % type(mm).__name__)
    for l, v in lados.items():
        if v < 0:
            raise ValueError("margem negativa em %r (use contrair)" % l)
    if not permitir_zero and max(lados.values()) <= 0:
        raise ValueError("margem toda zero")
    return lados


def _espelhar_margem(lados):
    return dict((_OPOSTO[l], v) for l, v in lados.items())


def _limites(mask):
    m = np.asarray(mask)
    if m.ndim != 3:
        achou = np.where(m)
        if len(achou[0]) == 0:
            return None
        return tuple((int(a.min()), int(a.max())) for a in achou)
    zs = np.flatnonzero(m.any(axis=(1, 2)))
    if not len(zs):
        return None
    plano = m[int(zs[0]):int(zs[-1]) + 1].any(axis=0)
    ys = np.flatnonzero(plano.any(axis=1))
    xs = np.flatnonzero(plano.any(axis=0))
    return ((int(zs[0]), int(zs[-1])), (int(ys[0]), int(ys[-1])),
            (int(xs[0]), int(xs[-1])))


def _bbox_folgado(mask, folga_voxels):
    lim = _limites(mask)
    if lim is None:
        return None
    cortes = []
    for eixo in range(3):
        lo = lim[eixo][0] - int(folga_voxels[eixo])
        hi = lim[eixo][1] + int(folga_voxels[eixo]) + 1
        cortes.append(slice(max(0, lo), min(mask.shape[eixo], hi)))
    return tuple(cortes)


FOLGA_DA_CONFERENCIA = 1


def volume_de_voxels(n, grade):
    return float(n) * grade.volume_voxel_mm3 / 1000.0


class Caixas(object):

    def __init__(self, masks, folga=FOLGA_DA_CONFERENCIA):
        self._masks = masks
        self.folga = folga
        self._memo = {}

    def _calcular(self, nome):
        orig = self._masks[nome]
        m = _bool(orig)
        lim = _limites(m)
        if lim is None:
            cx = None
            n = 0
        elif self.folga is None:
            cx = (slice(None),) * m.ndim
            n = int(m.sum())
        else:
            f = int(self.folga)
            cx = tuple(slice(max(0, lim[e][0] - f),
                             min(m.shape[e], lim[e][1] + f + 1))
                       for e in range(3))
            n = int(m[cx].sum())
        self._memo[nome] = (orig, m, cx, n, lim)
        return self._memo[nome]

    def _item(self, nome):
        memo = self._memo.get(nome)
        if memo is not None and memo[0] is self._masks[nome]:
            return memo
        return self._calcular(nome)

    def de(self, nome):
        _o, m, cx, n, _l = self._item(nome)
        return m, cx, n

    def justa(self, nome):
        lim = self._item(nome)[4]
        if lim is None:
            return None
        return [(a, b + 1) for a, b in lim]

    def cru(self, nome):
        orig, _m, cx, _n, _l = self._item(nome)
        if cx is None:
            return None
        return np.asarray(orig)[cx]


def _caixa_comum(mascaras, folga_voxels):
    limites = None
    for m in mascaras:
        caixa = _bbox_folgado(m, folga_voxels)
        if caixa is None:
            continue
        if limites is None:
            limites = [[c.start, c.stop] for c in caixa]
        else:
            for eixo in range(3):
                limites[eixo][0] = min(limites[eixo][0], caixa[eixo].start)
                limites[eixo][1] = max(limites[eixo][1], caixa[eixo].stop)
    if limites is None:
        return None
    return tuple(slice(lo, hi) for lo, hi in limites)


def _dilatar_elipsoide(sub, raios_mm, spacing):
    if max(raios_mm) <= 0:
        return sub
    amostragem = []
    for eixo in range(3):
        r = raios_mm[eixo]
        amostragem.append(spacing[eixo] / r if r > 0 else 1.0e9)
    dist = ndimage.distance_transform_edt(~sub, sampling=amostragem)
    return dist <= 1.0


def _estender_unidirecional(sub, eixo, sinal, mm, spacing):
    n = int(round(float(mm) / spacing[eixo]))
    if n <= 0:
        return sub
    tam = n + 1
    origem = n - tam // 2 if sinal > 0 else -(tam // 2)
    saida = ndimage.maximum_filter1d(sub.astype(np.uint8), size=tam, axis=eixo,
                                     origin=origem, mode="constant", cval=0)
    return saida.astype(bool)


def _aplicar_margem(mask, lados, grade):
    mask = _bool(mask)
    if not mask.any() or max(lados.values()) <= 0:
        return mask.copy()

    raios = [0.0, 0.0, 0.0]
    extras = []
    for lado in LADOS:
        eixo, sinal = grade.eixo_sinal(lado)
        oposto = lados[_OPOSTO[lado]]
        raios[eixo] = min(lados[lado], oposto)
        if lados[lado] > oposto:
            extras.append((eixo, sinal, lados[lado] - oposto))

    folga = [int(np.ceil(max(lados.values()) / grade.spacing[e])) + 2 for e in range(3)]
    caixa = _bbox_folgado(mask, folga)
    sub = mask[caixa]

    sub = _dilatar_elipsoide(sub, raios, grade.spacing)
    for eixo, sinal, mm in extras:
        sub = _estender_unidirecional(sub, eixo, sinal, mm, grade.spacing)

    saida = np.zeros_like(mask)
    saida[caixa] = sub
    return saida


def expandir(mask, mm, grade):
    return _aplicar_margem(mask, _normalizar_margem(mm), grade)


def contrair(mask, mm, grade):
    mask = _bool(mask)
    lados = _normalizar_margem(mm)
    if max(lados.values()) <= 0 or not mask.any():
        return mask.copy()
    folga = [int(np.ceil(max(lados.values()) / grade.spacing[e])) + 2 for e in range(3)]
    caixa = _bbox_folgado(mask, folga)
    sub = mask[caixa]
    fora = _aplicar_margem(~sub, _espelhar_margem(lados), grade)
    saida = np.zeros_like(mask)
    saida[caixa] = ~fora
    return saida


def abrir_pontes(mask, tamanho=2):
    mask = _bool(mask)
    n = max(1, int(tamanho))
    if not mask.any():
        return mask.copy()
    saida = mask
    for eixo in (0, 1, 2):
        forma = [1, 1, 1]
        forma[eixo] = n
        el = np.ones(tuple(forma), dtype=bool)
        saida = ndimage.binary_opening(saida, structure=el)
    return saida


def maior_componente(mask, conectividade=1, abrir=0):
    mask = _bool(mask)
    if not mask.any():
        return mask.copy()
    if int(abrir or 0) > 0:
        aberta = abrir_pontes(mask, int(abrir))
        if aberta.any():
            mask = aberta
    estrutura = ndimage.generate_binary_structure(3, int(conectividade))
    rotulos, n = ndimage.label(mask, structure=estrutura)
    if n <= 1:
        return mask.copy()
    contagens = np.bincount(rotulos.ravel())
    contagens[0] = 0
    return rotulos == int(np.argmax(contagens))


def preencher_buracos(mask, por_fatia=True, triplanar=False):
    mask = _bool(mask)
    if not mask.any():
        return mask.copy()
    if triplanar:
        saida = mask.copy()
        for eixo in (0, 1, 2):
            v = np.moveaxis(saida, eixo, 0)
            cheio = np.zeros_like(v)
            for i in range(v.shape[0]):
                if v[i].any():
                    cheio[i] = ndimage.binary_fill_holes(v[i])
            saida = np.moveaxis(cheio, 0, eixo)
        return saida
    if not por_fatia:
        return ndimage.binary_fill_holes(mask)
    saida = np.zeros_like(mask)
    for z in range(mask.shape[0]):
        if mask[z].any():
            saida[z] = ndimage.binary_fill_holes(mask[z])
    return saida


def espessura_mm(mask, grade):
    m = _bool(mask)
    if not m.any():
        return 0.0
    caixa = _bbox_folgado(m, (1, 1, 1))
    d = ndimage.distance_transform_edt(m[caixa], sampling=grade.spacing)
    return float(d.max())


def _n_maiores(campo, alvo_voxels):
    n = int(alvo_voxels)
    plano = campo.ravel()
    if n <= 0:
        return np.zeros(campo.shape, dtype=bool)
    if n >= plano.size:
        return np.ones(campo.shape, dtype=bool)
    idx = np.argpartition(plano, plano.size - n)[plano.size - n:]
    fora = np.zeros(plano.size, dtype=bool)
    fora[idx] = True
    return fora.reshape(campo.shape)


def distancia_com_sinal(mask, grade):
    m = _bool(mask)
    fora = ndimage.distance_transform_edt(~m, sampling=grade.spacing)
    dentro = ndimage.distance_transform_edt(m, sampling=grade.spacing)
    return fora - dentro


def suavizar(mask, mm, grade, limiar=None, preservar_volume=True,
             ancora="centro", mediana=False):
    mask = _bool(mask)
    if not mask.any() or float(mm) <= 0:
        return mask.copy()

    efetivo = float(mm)
    anc = str(ancora or "centro").lower()
    desloca_mm = 0.0
    if anc == "externo":
        desloca_mm = efetivo / 2.0
    elif anc == "interno":
        desloca_mm = -efetivo / 2.0

    folga = [int(np.ceil(3 * efetivo / grade.spacing[e])) + 2 for e in range(3)]
    caixa = _bbox_folgado(mask, folga)
    recorte = mask[caixa]
    alvo = int(recorte.sum())
    if desloca_mm:
        sup = int(_superficie(recorte).sum())
        alvo = max(1, int(round(alvo + sup * desloca_mm /
                                float(min(grade.spacing)))))

    campo = distancia_com_sinal(recorte, grade)
    if mediana:
        k = [max(1, int(round(efetivo / grade.spacing[e]))) for e in range(3)]
        k = [v + 1 if v % 2 == 0 else v for v in k]
        if max(k) > 1:
            campo = ndimage.median_filter(campo, size=k, mode="nearest")
    sigma = [efetivo / grade.spacing[e] for e in range(3)]
    campo = ndimage.gaussian_filter(campo, sigma=sigma)

    if preservar_volume:
        saida_caixa = _n_maiores(-campo, alvo)
    else:
        saida_caixa = campo < 0.0

    if not saida_caixa.any():
        return mask.copy()

    saida = np.zeros_like(mask)
    saida[caixa] = saida_caixa
    return saida


TAUBIN_LAMBDA = 0.60
TAUBIN_MU = -0.64
TAUBIN_PASSOS = 8
MIN_PONTOS_SUAVIZAR = 8


def suavizar_poligono(pontos, passos=TAUBIN_PASSOS, lam=TAUBIN_LAMBDA,
                      mu=TAUBIN_MU, fechado=True):
    p = np.asarray(pontos, dtype=np.float64)
    if p.ndim != 2 or p.shape[0] < MIN_PONTOS_SUAVIZAR:
        return np.asarray(pontos, dtype=np.float64)
    ordem = np.arange(p.shape[0])
    ant, prox = np.roll(ordem, 1), np.roll(ordem, -1)
    for _ in range(int(passos)):
        for fator in (lam, mu):
            if fechado:
                viz = (p[ant] + p[prox]) / 2.0
                p = p + fator * (viz - p)
            else:
                viz = p.copy()
                viz[1:-1] = (p[:-2] + p[2:]) / 2.0
                d = fator * (viz - p)
                d[0] = d[-1] = 0.0
                p = p + d
    return p


MITER_MAX = 2.0


def expandir_meio_pixel(pontos, dx, dy, fechado=True, furo=False):
    p = np.asarray(pontos, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] < 3:
        return np.asarray(pontos, dtype=np.float64)
    dx, dy = abs(float(dx)) / 2.0, abs(float(dy)) / 2.0
    if dx <= 0 and dy <= 0:
        return p.copy()

    esc = np.array([dx if dx > 0 else 1.0, dy if dy > 0 else 1.0])
    q = p / esc

    giro = sentido_poligono(q)
    if not giro:
        return p.copy()
    fora = float(giro)
    # GUARDA: o contorno de um furo passa pelos centros do material; o fora
    # dele e para dentro do proprio poligono, senao o anel perde uma volta.
    if furo:
        fora = -fora

    d = np.roll(q, -1, axis=0) - q if fechado else np.vstack(
        [q[1:] - q[:-1], (q[-1] - q[-2])[None, :]])
    comp = np.hypot(d[:, 0], d[:, 1])
    bom = comp > 1e-12
    if not bom.any():
        return p.copy()
    n = np.zeros_like(d)
    n[bom, 0] = fora * d[bom, 1] / comp[bom]
    n[bom, 1] = -fora * d[bom, 0] / comp[bom]
    if not bom.all():
        for i in range(len(n)):
            if not bom[i]:
                n[i] = n[i - 1]

    ant = np.roll(n, 1, axis=0)
    soma = ant + n
    denom = 1.0 + (ant * n).sum(axis=1)
    desl = np.zeros_like(soma)
    seguro = denom > 1e-6
    desl[seguro] = soma[seguro] / denom[seguro][:, None]
    desl[~seguro] = ant[~seguro]
    comp_d = np.hypot(desl[:, 0], desl[:, 1])
    corta = comp_d > MITER_MAX
    if corta.any():
        desl[corta] = desl[corta] / comp_d[corta][:, None] * MITER_MAX
    return (q + desl) * esc


def area_poligono(pontos):
    p = np.asarray(pontos, dtype=np.float64)[:, :2]
    if p.shape[0] < 3:
        return 0.0
    x, y = p[:, 0], p[:, 1]
    return float(0.5 * np.abs(np.dot(x, np.roll(y, -1)) -
                              np.dot(y, np.roll(x, -1))))

def sentido_poligono(pontos):
    p = np.asarray(pontos, dtype=np.float64)[:, :2]
    if p.shape[0] < 3:
        return 0
    x, y = p[:, 0], p[:, 1]
    s = float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return 0 if s == 0.0 else (1 if s > 0 else -1)


def douglas_peucker_fechado(pontos, tol, minimo=3):
    p = np.asarray(pontos, dtype=np.float64)
    n = int(p.shape[0]) if p.ndim == 2 else 0
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    if tol is None or float(tol) <= 0 or n <= max(int(minimo), 3):
        return np.arange(n, dtype=np.int64)
    xy = p[:, :2]
    tol = float(tol)
    d0 = np.hypot(xy[:, 0] - xy[0, 0], xy[:, 1] - xy[0, 1])
    b = int(np.argmax(d0))
    if b == 0:
        return np.arange(min(n, max(int(minimo), 3)), dtype=np.int64)
    manter = np.zeros(n + 1, dtype=bool)
    manter[0] = manter[b] = manter[n] = True
    ext = np.vstack([xy, xy[:1]])
    pilha = [(0, b), (b, n)]
    while pilha:
        i, j = pilha.pop()
        if j - i < 2:
            continue
        a, c = ext[i], ext[j]
        seg = ext[i + 1:j]
        dx, dy = c[0] - a[0], c[1] - a[1]
        comp = np.hypot(dx, dy)
        if comp == 0.0:
            dist = np.hypot(seg[:, 0] - a[0], seg[:, 1] - a[1])
        else:
            dist = np.abs(dy * (seg[:, 0] - a[0]) - dx * (seg[:, 1] - a[1])) \
                / comp
        k = int(np.argmax(dist))
        if dist[k] > tol:
            m = i + 1 + k
            manter[m] = True
            pilha.append((i, m))
            pilha.append((m, j))
    idx = np.nonzero(manter[:n])[0]
    if idx.size < int(minimo):
        a, c = xy[0], xy[b]
        dx, dy = c[0] - a[0], c[1] - a[1]
        comp = np.hypot(dx, dy) or 1.0
        dist = np.abs(dy * (xy[:, 0] - a[0]) - dx * (xy[:, 1] - a[1])) / comp
        dist[idx] = -1.0
        faltam = int(minimo) - idx.size
        extra = np.argsort(-dist)[:faltam]
        idx = np.unique(np.concatenate([idx, extra]))
    return idx.astype(np.int64)


def indice_do_extremo(mask, direcao, grade, offset_mm=0.0):
    m = _bool(mask)
    if not m.any():
        raise ValueError("mascara vazia em indice_do_extremo")
    eixo, sinal = grade.eixo_sinal(direcao)
    onde = np.where(m)[eixo]
    limite = int(onde.max()) if sinal > 0 else int(onde.min())
    return limite + sinal * grade.mm_para_voxels(offset_mm, eixo)

SENTIDO_CANONICO = ("sup", "post", "esq")


def eixos_invertidos(grade):
    fora = []
    for eixo, alvo in enumerate(SENTIDO_CANONICO):
        s = grade.sentido[eixo]
        if s == alvo:
            continue
        if _OPOSTO[s] == alvo:
            fora.append(eixo)
            continue
        raise ValueError("a serie nao e axial (sentido %r): os eixos nao se "
                         "levam a %r so por inversao" % (grade.sentido,
                                                         SENTIDO_CANONICO))
    return tuple(fora)


def grade_canonica(grade):
    eixos_invertidos(grade)
    return Grade(grade.spacing, SENTIDO_CANONICO)


def para_canonico(arr, grade):
    eixos = eixos_invertidos(grade)
    a = np.asarray(arr)
    return np.ascontiguousarray(np.flip(a, eixos)) if eixos else a


def do_canonico(arr, grade):
    return para_canonico(arr, grade)


def suavizar_conjunto(partes, mm, grade, limiar=0.5, so_no_plano=False):
    nomes = [k for k in partes if _bool(partes[k]).any()]
    if not nomes:
        return dict((k, _bool(v).copy()) for k, v in partes.items())
    mm_de = ((lambda k: float(mm.get(k, 0.0))) if isinstance(mm, dict)
             else (lambda k: float(mm)))
    if max([mm_de(k) for k in nomes]) <= 0:
        return dict((k, _bool(v).copy()) for k, v in partes.items())

    lim_de = dict((k, _limites(_bool(partes[k]))) for k in nomes)
    for i, a in enumerate(nomes):
        la = lim_de[a]
        for b in nomes[i + 1:]:
            lb = lim_de[b]
            ib = tuple(slice(max(la[e][0], lb[e][0]),
                             min(la[e][1], lb[e][1]) + 1) for e in range(3))
            if any(s.start >= s.stop for s in ib):
                continue
            if (_bool(partes[a])[ib] & _bool(partes[b])[ib]).any():
                raise ValueError(
                    "suavizar_conjunto exige mascaras disjuntas: %r e %r se "
                    "sobrepoem" % (a, b))

    sig_de = dict((k, [0.0 if (so_no_plano and e == 0)
                       else mm_de(k) / grade.spacing[e] for e in range(3)])
                  for k in nomes)
    folga = [int(np.ceil(3 * max(sig_de[k][e] for k in nomes))) + 2
             for e in range(3)]
    uniao = _bool(partes[nomes[0]]).copy()
    for k in nomes[1:]:
        uniao |= _bool(partes[k])
    caixa = _bbox_folgado(uniao, folga)

    melhor = None
    quem = None
    for i, k in enumerate(nomes):
        b = ndimage.gaussian_filter(
            _bool(partes[k])[caixa].astype(np.float32), sigma=sig_de[k])
        if melhor is None:
            melhor = b
            quem = np.zeros(b.shape, dtype=np.int16)
        else:
            troca = b > melhor
            melhor = np.where(troca, b, melhor)
            quem[troca] = i

    crus = (~uniao)[caixa].astype(np.float32)
    fundo = np.zeros_like(melhor)
    vistos = {}
    for i, k in enumerate(nomes):
        chave = tuple(sig_de[k])
        if chave not in vistos:
            vistos[chave] = ndimage.gaussian_filter(crus, sigma=sig_de[k])
        onde = (quem == i)
        if onde.any():
            fundo[onde] = vistos[chave][onde]
    vence = _n_maiores(melhor - fundo, int(uniao[caixa].sum()))
    fora = {}
    for i, k in enumerate(nomes):
        m = np.zeros_like(uniao)
        m[caixa] = vence & (quem == i)
        fora[k] = m
    for k in partes:
        if k not in fora:
            fora[k] = _bool(partes[k]).copy()
    return fora

def limitar_por_plano(mask, direcao, referencia, offset_mm=0.0, grade=None):
    if grade is None:
        raise ValueError("limitar_por_plano exige grade")
    mask = _bool(mask)
    eixo, sinal = grade.eixo_sinal(direcao)
    if isinstance(referencia, np.ndarray):
        ref = _bool(referencia)
        if not ref.any():
            raise ValueError("referencia vazia em limitar_por_plano")
        onde = np.where(ref)[eixo]
        limite = int(onde.max()) if sinal > 0 else int(onde.min())
    else:
        limite = int(referencia)
    limite += sinal * grade.mm_para_voxels(offset_mm, eixo)

    saida = mask.copy()
    fatia = [slice(None)] * 3
    if sinal > 0:
        fatia[eixo] = slice(limite + 1, None)
    else:
        fatia[eixo] = slice(None, limite)
    saida[tuple(fatia)] = False
    return saida


def partir_no_plano(mask, direcao, indice, grade):
    m = _bool(mask)
    eixo, sinal = grade.eixo_sinal(direcao)
    limite = int(indice)
    a = np.zeros_like(m)
    b = np.zeros_like(m)
    fatia_a = [slice(None)] * 3
    fatia_b = [slice(None)] * 3
    if sinal > 0:
        fatia_a[eixo] = slice(limite, None)
        fatia_b[eixo] = slice(None, limite)
    else:
        fatia_a[eixo] = slice(None, limite + 1)
        fatia_b[eixo] = slice(limite + 1, None)
    a[tuple(fatia_a)] = m[tuple(fatia_a)]
    b[tuple(fatia_b)] = m[tuple(fatia_b)]
    return a, b


def volume_cm3(mask, grade):
    return volume_de_voxels(_bool(mask).sum(), grade)


def delta_volume_pct(candidato, referencia, grade):
    v_ref = volume_cm3(referencia, grade)
    if v_ref <= 0:
        return float("nan")
    return (volume_cm3(candidato, grade) - v_ref) / v_ref * 100.0


def dsc(a, b):
    a, b = _bool(a), _bool(b)
    soma = int(a.sum()) + int(b.sum())
    if soma == 0:
        return 1.0
    return 2.0 * float(np.logical_and(a, b).sum()) / float(soma)


def _superficie(mask):
    mask = _bool(mask)
    if not mask.any():
        return mask.copy()
    est = ndimage.generate_binary_structure(3, 1)
    return mask & ~ndimage.binary_erosion(mask, structure=est, border_value=0)


_VAZIO = np.array([], dtype=np.float64)


def par_distancias(a, b, grade):
    a, b = _bool(a), _bool(b)
    if not a.any() or not b.any():
        return _VAZIO, _VAZIO
    caixa = _caixa_comum([a, b], (2, 2, 2))
    sup_a, sup_b = _superficie(a[caixa]), _superficie(b[caixa])
    if not sup_a.any() or not sup_b.any():
        return _VAZIO, _VAZIO
    ate_b = ndimage.distance_transform_edt(~sup_b, sampling=grade.spacing)
    ate_a = ndimage.distance_transform_edt(~sup_a, sampling=grade.spacing)
    return ate_b[sup_a], ate_a[sup_b]


def _hd95_de(d1, d2):
    if d1.size == 0 or d2.size == 0:
        return float("nan")
    return float(np.percentile(np.concatenate([d1, d2]), 95))


def _hd100_de(d1, d2):
    if d1.size == 0 or d2.size == 0:
        return float("nan")
    return float(max(d1.max(), d2.max()))


def _msd_de(d1, d2):
    if d1.size == 0 or d2.size == 0:
        return float("nan")
    return float((d1.sum() + d2.sum()) / (d1.size + d2.size))


def _nsd_de(d1, d2, tolerancia_mm):
    if d1.size == 0 or d2.size == 0:
        return float("nan")
    dentro = float((d1 <= tolerancia_mm).sum() + (d2 <= tolerancia_mm).sum())
    return dentro / float(d1.size + d2.size)


def _apl_de(d2, grade, tolerancia_mm):
    if d2.size == 0:
        return float("nan")
    fora = int((d2 > float(tolerancia_mm)).sum())
    passo = float(min(grade.spacing))
    return fora * passo

def metricas(candidato, referencia, grade, tolerancia_mm=2.0):
    d1, d2 = par_distancias(candidato, referencia, grade)
    return {"dsc": round(dsc(candidato, referencia), 4),
            "dsc_sup": round(_nsd_de(d1, d2, tolerancia_mm), 4),
            "dsc_sup_1mm": round(_nsd_de(d1, d2, 1.0), 4),
            "dsc_sup_3mm": round(_nsd_de(d1, d2, 3.0), 4),
            "hd95_mm": round(_hd95_de(d1, d2), 2),
            "hd100_mm": round(_hd100_de(d1, d2), 2),
            "msd_mm": round(_msd_de(d1, d2), 2),
            "apl_mm": round(_apl_de(d2, grade, tolerancia_mm), 1),
            "delta_vol_pct": round(delta_volume_pct(candidato, referencia, grade), 2),
            "vol_candidato_cm3": round(volume_cm3(candidato, grade), 2),
            "vol_referencia_cm3": round(volume_cm3(referencia, grade), 2),
            "tolerancia_sup_mm": tolerancia_mm}
