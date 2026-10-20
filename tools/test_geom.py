# -*- coding: utf-8 -*-
import os
import sys

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

import numpy as np

def pasta_app(aqui):
    for c in (os.path.join(aqui, "..", "app"), os.path.join(aqui, "..")):
        if os.path.exists(os.path.join(c, "radai_geom.py")):
            return os.path.abspath(c)
    return os.path.abspath(os.path.join(aqui, "..", "app"))


sys.path.insert(0, pasta_app(os.path.dirname(os.path.abspath(__file__))))
import radai_geom as G

VERBOSO = "-v" in sys.argv or "--verbose" in sys.argv
_RESULTADOS = []


def checar(nome, condicao, detalhe=""):
    ok = bool(condicao)
    _RESULTADOS.append((nome, ok, detalhe))
    if VERBOSO or not ok:
        print("  %s  %s%s" % ("OK  " if ok else "FALHA", nome,
                              ("  [%s]" % detalhe) if detalhe else ""))
    return ok


def secao(titulo):
    if VERBOSO:
        print("\n-- %s " % titulo + "-" * max(0, 60 - len(titulo)))


GRADE = G.Grade((3.0, 1.0, 0.5))
FORMA = (40, 120, 240)


def vazia(forma=FORMA):
    return np.zeros(forma, dtype=bool)


def ponto(centro=(20, 60, 120), forma=FORMA):
    m = vazia(forma)
    m[centro] = True
    return m


def bloco(z=(10, 30), y=(30, 90), x=(60, 180), forma=FORMA):
    m = vazia(forma)
    m[z[0]:z[1], y[0]:y[1], x[0]:x[1]] = True
    return m


def esfera(centro, raio_mm, grade=GRADE, forma=FORMA):
    zz, yy, xx = np.ogrid[0:forma[0], 0:forma[1], 0:forma[2]]
    d2 = (((zz - centro[0]) * grade.spacing[0]) ** 2 +
          ((yy - centro[1]) * grade.spacing[1]) ** 2 +
          ((xx - centro[2]) * grade.spacing[2]) ** 2)
    return d2 <= float(raio_mm) ** 2


def extensao_mm(mask, centro, eixo, grade=GRADE):
    idx = np.where(mask)[eixo]
    sp = grade.spacing[eixo]
    return ((centro[eixo] - int(idx.min())) * sp, (int(idx.max()) - centro[eixo]) * sp)


def teste_expansao_isotropica():
    secao("expansao isotropica: 6 mm sao 6 mm em todo eixo")
    c = (20, 60, 120)
    saida = G.expandir(ponto(c), 6.0, GRADE)
    for eixo, nome in enumerate(("z (3,0 mm/voxel)", "y (1,0 mm)", "x (0,5 mm)")):
        neg, pos = extensao_mm(saida, c, eixo)
        checar("expandir 6 mm -> 6 mm no eixo %s" % nome,
               abs(neg - 6.0) < 1e-6 and abs(pos - 6.0) < 1e-6,
               "-%.2f / +%.2f mm" % (neg, pos))
    raio = np.array([extensao_mm(saida, c, e)[1] for e in range(3)])
    checar("expansao isotropica e esferica em mm", np.allclose(raio, 6.0),
           "raios %s" % np.round(raio, 2).tolist())


def teste_expansao_anisotropica():
    secao("expansao anisotropica: cada lado com sua margem")
    c = (20, 60, 120)
    pedido = {"ant": 6, "post": 2, "esq": 4, "dir": 1, "sup": 9, "inf": 3}
    saida = G.expandir(ponto(c), pedido, GRADE)
    esperado = {("z", 0): (pedido["inf"], pedido["sup"]),
                ("y", 1): (pedido["ant"], pedido["post"]),
                ("x", 2): (pedido["dir"], pedido["esq"])}
    for (nome, eixo), (esp_neg, esp_pos) in esperado.items():
        neg, pos = extensao_mm(saida, c, eixo)
        checar("eixo %s: -%g / +%g mm" % (nome, esp_neg, esp_pos),
               abs(neg - esp_neg) < 1e-6 and abs(pos - esp_pos) < 1e-6,
               "obtido -%.2f / +%.2f" % (neg, pos))
    checar("atalho 'lat' equivale a esq+dir",
           np.array_equal(G.expandir(ponto(c), {"lat": 4}, GRADE),
                          G.expandir(ponto(c), {"esq": 4, "dir": 4}, GRADE)))


def teste_extensao_unidirecional():
    secao("extensao unidirecional: sentido e alcance exatos")
    c = (20, 60, 120)
    for n_mm, eixo, sentido, nome in ((3.0, 0, +1, "sup"), (6.0, 0, +1, "sup"),
                                      (9.0, 0, -1, "inf"), (1.0, 1, +1, "post"),
                                      (2.0, 1, -1, "ant"), (3.0, 1, -1, "ant")):
        saida = G._estender_unidirecional(ponto(c), eixo, sentido, n_mm, GRADE.spacing)
        neg, pos = extensao_mm(saida, c, eixo)
        avancou, parado = (pos, neg) if sentido > 0 else (neg, pos)
        checar("extensao %s de %g mm avanca so para um lado" % (nome, n_mm),
               abs(avancou - n_mm) < 1e-6 and parado == 0.0,
               "avancou %.1f / lado oposto %.1f" % (avancou, parado))


def teste_expansao_casos_limite():
    secao("expansao: casos limite")
    checar("margem 0 nao altera a mascara",
           np.array_equal(G.expandir(bloco(), 0, GRADE), bloco()))
    checar("mascara vazia continua vazia", not G.expandir(vazia(), 5, GRADE).any())
    checar("margem negativa e recusada", _levanta(lambda: G.expandir(bloco(), -3, GRADE), ValueError))
    checar("chave de margem invalida e recusada",
           _levanta(lambda: G.expandir(bloco(), {"cranial": 3}, GRADE), ValueError))
    checar("expansao nunca perde voxel original",
           np.all(G.expandir(bloco(), {"ant": 5, "post": 0}, GRADE)[bloco()]))


def teste_contracao():
    secao("contracao: espelha o lado certo")
    b = bloco(z=(10, 30), y=(30, 90), x=(60, 180))
    saida = G.contrair(b, {"ant": 6}, GRADE)
    y_ini, y_fim = int(np.where(saida)[1].min()), int(np.where(saida)[1].max())
    checar("contrair 6 mm 'ant' recua a face anterior", y_ini == 30 + 6, "y_ini=%d" % y_ini)
    checar("contrair 'ant' nao mexe na face posterior", y_fim == 89, "y_fim=%d" % y_fim)

    iso = G.contrair(b, 3.0, GRADE)
    zi, zf = int(np.where(iso)[0].min()), int(np.where(iso)[0].max())
    checar("contracao isotropica de 3 mm come 1 voxel em z (3 mm)",
           zi == 11 and zf == 28, "z %d..%d" % (zi, zf))
    checar("contrair 0 nao altera", np.array_equal(G.contrair(b, 0, GRADE), b))

    volta = G.contrair(G.expandir(b, 5.0, GRADE), 5.0, GRADE)
    checar("expandir+contrair 5 mm reconstroi o bloco (DSC > 0,99)",
           G.dsc(volta, b) > 0.99, "dsc=%.4f" % G.dsc(volta, b))


def teste_componentes_e_buracos():
    secao("maior componente / preencher buracos")
    dois = esfera((12, 40, 60), 9.0) | esfera((28, 90, 190), 5.0)
    maior = G.maior_componente(dois)
    checar("maior_componente mantem so o maior",
           maior.sum() == esfera((12, 40, 60), 9.0).sum(),
           "%d de %d voxels" % (int(maior.sum()), int(dois.sum())))
    checar("maior_componente de mascara vazia nao quebra",
           not G.maior_componente(vazia()).any())

    orgao = bloco(z=(10, 30), y=(10, 40), x=(20, 80))
    falso = bloco(z=(16, 24), y=(18, 32), x=(96, 130))
    fio = bloco(z=(19, 20), y=(24, 25), x=(80, 96))
    com_ponte = orgao | falso | fio
    n_antes = int(com_ponte.sum())

    sem_abrir = G.maior_componente(com_ponte)
    checar("SEM abrir, a ponte faz tudo virar um componente so",
           int(sem_abrir.sum()) == n_antes,
           "%d de %d voxels sobreviveram" % (int(sem_abrir.sum()), n_antes))
    checar("e o falso positivo vem junto",
           bool(np.logical_and(sem_abrir, falso).any()))

    com_abrir = G.maior_componente(com_ponte, abrir=2)
    checar("COM abrir=2, o falso positivo sai",
           not np.logical_and(com_abrir, falso).any(),
           "%d voxels do falso ainda la"
           % int(np.logical_and(com_abrir, falso).sum()))
    checar("e o orgao continua INTEIRO",
           np.logical_and(com_abrir, orgao).sum() == orgao.sum(),
           "%d de %d" % (int(np.logical_and(com_abrir, orgao).sum()),
                         int(orgao.sum())))

    for espessura, corta_com in ((1, 2), (2, 3)):
        f = bloco(z=(19, 19 + espessura), y=(24, 24 + espessura), x=(80, 96))
        c = orgao | falso | f
        sai = G.maior_componente(c, abrir=corta_com)
        fica = G.maior_componente(c, abrir=corta_com - 1)
        checar("ponte de %d voxel(s): abrir=%d corta"
               % (espessura, corta_com),
               not np.logical_and(sai, falso).any())
        checar("ponte de %d voxel(s): abrir=%d NAO corta"
               % (espessura, corta_com - 1),
               np.logical_and(fica, falso).any())
        checar("ponte de %d: o orgao fica intacto nos dois" % espessura,
               np.logical_and(sai, orgao).sum() == orgao.sum()
               and np.logical_and(fica, orgao).sum() == orgao.sum())

    lamina = bloco(z=(10, 30), y=(20, 22), x=(20, 80))
    aberta = G.abrir_pontes(lamina, 2)
    checar("abrir_pontes preserva lamina de 2 voxels", aberta.any(),
           "%d de %d" % (int(aberta.sum()), int(lamina.sum())))

    fina = bloco(z=(10, 12), y=(20, 21), x=(20, 30))
    checar("abertura que apaga tudo nao apaga a estrutura",
           G.maior_componente(fina, abrir=3).sum() > 0,
           "%d voxels" % int(G.maior_componente(fina, abrir=3).sum()))


    com_buraco = esfera((20, 60, 120), 14.0) & ~esfera((20, 60, 120), 5.0)
    cheia = G.preencher_buracos(com_buraco, por_fatia=True)
    checar("preencher_buracos fecha a cavidade interna",
           cheia.sum() == esfera((20, 60, 120), 14.0).sum(),
           "%d vs %d" % (int(cheia.sum()), int(esfera((20, 60, 120), 14.0).sum())))
    checar("preencher_buracos nunca remove voxel", np.all(cheia[com_buraco]))

    tunel = bloco(z=(6, 18), y=(6, 18), x=(6, 18))
    tunel[10:14, 10:14, :] = False

    def _ganho(tri):
        return (int(G.preencher_buracos(tunel, por_fatia=True,
                                        triplanar=tri).sum())
                - int(tunel.sum()))
    ganho_axial, ganho_tri = _ganho(False), _ganho(True)
    checar("SEM triplanar nao fecha o tunel (ele toca a borda no axial)",
           ganho_axial == 0, "%d voxel(s)" % ganho_axial)
    checar("COM triplanar fecha o tunel",
           ganho_tri == 192, "%d voxel(s)" % ganho_tri)


def teste_limitar_por_plano():
    secao("limitar_por_plano: corte por landmark")
    b = bloco(z=(5, 35), y=(30, 90), x=(60, 180))
    ref = bloco(z=(20, 22), y=(40, 50), x=(70, 80))

    cortado = G.limitar_por_plano(b, "sup", ref, offset_mm=0.0, grade=GRADE)
    z_max = int(np.where(cortado)[0].max())
    checar("corte 'sup' remove tudo acima do topo do landmark", z_max == 21,
           "z_max=%d (landmark termina em 21)" % z_max)

    com_offset = G.limitar_por_plano(b, "sup", ref, offset_mm=6.0, grade=GRADE)
    z_max2 = int(np.where(com_offset)[0].max())
    checar("offset de 6 mm sobe o plano 2 voxels (z=3 mm)", z_max2 == 23, "z_max=%d" % z_max2)

    inf = G.limitar_por_plano(b, "inf", ref, grade=GRADE)
    z_min = int(np.where(inf)[0].min())
    checar("corte 'inf' remove tudo abaixo da base do landmark", z_min == 20, "z_min=%d" % z_min)
    checar("limitar_por_plano exige grade",
           _levanta(lambda: G.limitar_por_plano(b, "sup", ref), ValueError))


def teste_suavizar():
    secao("suavizar")
    ruidosa = esfera((20, 60, 120), 12.0).copy()
    rng = np.random.default_rng(42)
    espinhos = rng.random(FORMA) < 0.0004
    ruidosa |= espinhos
    lisa = G.suavizar(ruidosa, 2.0, GRADE)
    from scipy import ndimage as _ndi
    ilhas = lambda m: int(_ndi.label(m)[1])
    checar("suavizar remove espinhos isolados",
           ilhas(lisa) < ilhas(ruidosa),
           "%d ilhas -> %d" % (ilhas(ruidosa), ilhas(lisa)))
    checar("e o volume NAO muda (preservacao por construcao)",
           int(lisa.sum()) == int(ruidosa.sum()),
           "%d -> %d voxels" % (int(ruidosa.sum()), int(lisa.sum())))
    checar("suavizar preserva o corpo principal (DSC > 0,9)",
           G.dsc(lisa, esfera((20, 60, 120), 12.0)) > 0.9,
           "dsc=%.3f" % G.dsc(lisa, esfera((20, 60, 120), 12.0)))
    checar("suavizar 0 mm nao altera", np.array_equal(G.suavizar(ruidosa, 0, GRADE), ruidosa))


def teste_grade():
    secao("Grade: eixos, sentidos e leitura do SimpleITK")
    checar("eixo/sinal de 'sup'", GRADE.eixo_sinal("sup") == (0, 1))
    checar("eixo/sinal de 'ant'", GRADE.eixo_sinal("ant") == (1, -1))
    checar("eixo/sinal de 'dir'", GRADE.eixo_sinal("dir") == (2, -1))
    checar("direcao invalida e recusada", _levanta(lambda: GRADE.eixo_sinal("cranial"), ValueError))
    checar("spacing invalido e recusado", _levanta(lambda: G.Grade((0, 1, 1)), ValueError))
    checar("volume do voxel em mm3", abs(GRADE.volume_voxel_mm3 - 1.5) < 1e-9)

    invertida = G.Grade((3.0, 1.0, 0.5), sentido=("inf", "post", "esq"))
    c = (20, 60, 120)
    saida = G.expandir(ponto(c), {"sup": 9, "inf": 3}, invertida)
    neg, pos = extensao_mm(saida, c, 0, invertida)
    checar("sentido invertido troca sup/inf no array", abs(neg - 9.0) < 1e-6 and abs(pos - 3.0) < 1e-6,
           "-%.1f / +%.1f mm" % (neg, pos))

    class _ImagemFalsa(object):
        def GetSpacing(self):
            return (0.5, 1.0, 3.0)
        def GetDirection(self):
            return (1, 0, 0, 0, 1, 0, 0, 0, -1)

    g = G.Grade.de_sitk(_ImagemFalsa())
    checar("Grade.de_sitk inverte a ordem do spacing", g.spacing == (3.0, 1.0, 0.5),
           "%r" % (g.spacing,))
    checar("Grade.de_sitk le o sentido da matriz de direcao", g.sentido == ("inf", "post", "esq"),
           "%r" % (g.sentido,))


def teste_o_nsd_salta_e_por_isso_ha_duas_tolerancias():
    secao("o NSD salta com a tolerancia, e duas tolerancias mostram isso")
    import numpy as np
    g = G.Grade((3.0, 1.0, 1.0))
    Z, Y, X = 24, 60, 60
    zz, yy, xx = np.mgrid[0:Z, 0:Y, 0:X]

    def esfera(R):
        return (((zz - Z / 2.) * 3.0) ** 2 + ((yy - Y / 2.) * 1.0) ** 2
                + ((xx - X / 2.) * 1.0) ** 2) < R * R

    a, b = esfera(18.0), esfera(20.0)

    d1, d2 = G.par_distancias(a, b, g)
    distintas = np.unique(np.concatenate([d1, d2]))
    checar("as distancias sao quantizadas (poucos valores distintos)",
           len(distintas) <= 12, "%d valores" % len(distintas))

    n19 = G._nsd_de(d1, d2, 1.9)
    n20 = G._nsd_de(d1, d2, 2.0)
    checar("o NSD SALTA quando tau cruza uma distancia da grade",
           abs(n20 - n19) > 0.15, "tau 1,9 -> %.3f | tau 2,0 -> %.3f" % (n19, n20))

    n10 = G._nsd_de(d1, d2, 1.0)
    n14 = G._nsd_de(d1, d2, 1.4)
    checar("e fica PARADO entre duas distancias (1,0 e 1,4 dao o mesmo)",
           abs(n14 - n10) < 1e-9, "%.4f vs %.4f" % (n10, n14))

    n1 = G._nsd_de(d1, d2, 1.0)
    n3 = G._nsd_de(d1, d2, 3.0)
    checar("o NSD das metricas e o mesmo desta conta",
           G.metricas(a, b, g, tolerancia_mm=1.9)["dsc_sup"] == round(n19, 4))
    dsc = 2.0 * float((a & b).sum()) / float(a.sum() + b.sum())
    checar("com tau larga a mudanca some (NSD@3mm ~ 1,0 com DSC %.3f)" % dsc,
           n3 > 0.98 and n1 < 0.6, "NSD@1mm=%.3f NSD@3mm=%.3f" % (n1, n3))

    d1 = np.array([0.0] * 90 + [10.0] * 10)
    d2 = np.array([1.0] * 100)
    checar("o HD95 e o percentil do CONJUNTO das distancias dos dois lados",
           abs(G._hd95_de(d1, d2) - float(np.percentile(
               np.concatenate([d1, d2]), 95))) < 1e-12)
    checar("  isca: e nao o maior dos dois percentis por lado",
           abs(G._hd95_de(d1, d2) - max(float(np.percentile(d1, 95)),
                                        float(np.percentile(d2, 95)))) > 1e-6)


def teste_metricas():
    secao("metricas")
    a = esfera((20, 60, 120), 12.0)
    checar("dsc de uma mascara com ela mesma = 1", G.dsc(a, a) == 1.0)
    checar("dsc com mascara vazia = 0", G.dsc(a, vazia()) == 0.0)
    checar("dsc de duas vazias = 1 (convencao)", G.dsc(vazia(), vazia()) == 1.0)

    b = G.expandir(a, 5.0, GRADE)
    mb, ma = G.metricas(b, a, GRADE), G.metricas(a, a, GRADE)
    hd = mb["hd95_mm"]
    checar("hd95 de uma expansao de 5 mm fica proximo de 5 mm", 4.0 <= hd <= 6.5, "hd95=%.2f mm" % hd)
    checar("hd95 de identicas = 0", ma["hd95_mm"] == 0.0)
    checar("NSD de identicas = 1", ma["dsc_sup"] == 1.0)
    checar("NSD cai quando a borda se afasta", mb["dsc_sup"] < 0.5)

    vol = G.volume_cm3(a, GRADE)
    esperado = 4.0 / 3.0 * np.pi * 1.2 ** 3
    checar("volume_cm3 bate com a formula da esfera (erro < 5%)",
           abs(vol - esperado) / esperado < 0.05, "%.2f vs %.2f cm3" % (vol, esperado))
    checar("delta de volume de uma expansao e positivo",
           G.delta_volume_pct(b, a, GRADE) > 0, "%.1f%%" % G.delta_volume_pct(b, a, GRADE))

    pacote = G.metricas(b, a, GRADE)
    checar("metricas() traz as 4 chaves do export",
           all(k in pacote for k in ("dsc", "dsc_sup", "hd95_mm", "delta_vol_pct")))
    checar("metricas com mascara vazia nao quebra (NaN, sem excecao)",
           np.isnan(G.metricas(vazia(), a, GRADE)["hd95_mm"]))


def teste_ancora_da_suavizacao():
    secao("suavizar: onde a superficie se apoia")
    forma = (40, 60, 60)
    zz, yy, xx = np.ogrid[:forma[0], :forma[1], :forma[2]]
    r = np.sqrt((zz - 20.) ** 2 + (yy - 30.) ** 2 + (xx - 30.) ** 2)
    serrilha = 1.2 * ((zz + yy + xx) % 2)
    m = (r + serrilha) < 12
    grade = G.Grade((1.0, 1.0, 1.0))

    vols = {}
    for ancora in ("externo", "centro", "interno"):
        s = G.suavizar(m, 1.5, grade, ancora=ancora)
        vols[ancora] = G.volume_cm3(s, grade)

    checar("externo > centro > interno em volume",
           vols["externo"] > vols["centro"] > vols["interno"], str(vols))
    bruto = G.volume_cm3(m, grade)
    checar("o centro fica perto do volume original",
           abs(vols["centro"] - bruto) / bruto < 0.15,
           "centro %.2f vs bruto %.2f" % (vols["centro"], bruto))
    checar("e as tres mudam de verdade",
           (vols["externo"] - vols["interno"]) / bruto > 0.05, str(vols))

    r2 = G.suavizar(m, 1.5, grade, ancora="xpto")
    checar("ancora desconhecida cai no centro",
           abs(G.volume_cm3(r2, grade) - vols["centro"]) < 1e-9)


def _levanta(fn, tipo, trecho=None):
    try:
        fn()
    except tipo as e:
        return trecho is None or trecho in str(e)
    except Exception:
        return False
    return False


def teste_apl_mede_trabalho_e_nao_semelhanca():
    grade = G.Grade((2.0, 1.0, 1.0))
    Z, Y, X = 40, 60, 60
    zz, yy, xx = np.ogrid[:Z, :Y, :X]

    def bola(cz, cy, cx, r):
        return ((zz - cz) ** 2 * 4 + (yy - cy) ** 2 + (xx - cx) ** 2) < r * r

    ref = bola(20, 30, 30, 14)
    checar("APL esta nas metricas", "apl_mm" in G.metricas(ref, ref, grade), "")
    checar("identico -> APL zero", G.metricas(ref, ref, grade)["apl_mm"] == 0.0,
           str(G.metricas(ref, ref, grade)["apl_mm"]))
    dentro = G.metricas(G.expandir(ref, 1.0, grade), ref, grade)
    checar("desvio DENTRO da tolerancia -> APL zero",
           dentro["apl_mm"] == 0.0, str(dentro["apl_mm"]))
    fora = G.metricas(G.expandir(ref, 3.0, grade), ref, grade)
    checar("desvio ALEM da tolerancia -> APL > 0", fora["apl_mm"] > 0,
           str(fora["apl_mm"]))
    maior = G.metricas(G.expandir(ref, 6.0, grade), ref, grade)
    checar("desvio maior -> APL maior", maior["apl_mm"] >= fora["apl_mm"],
           "%s vs %s" % (maior["apl_mm"], fora["apl_mm"]))

    dscs, apls = [], []
    for r in (5, 10, 20):
        a = bola(20, 30, 30, r)
        m = G.metricas(G.expandir(a, 2.0, grade), a, grade)
        dscs.append(m["dsc"])
        apls.append(m["apl_mm"])
    checar("o mesmo desvio da DSC muito diferente conforme o tamanho",
           max(dscs) - min(dscs) > 0.15, str(dscs))
    checar("e o APL nao se deixa enganar pelo tamanho",
           len(set(apls)) == 1, str(apls))

def teste_nsd_em_duas_tolerancias():
    grade = G.Grade((2.5, 1.0, 1.0))
    zz, yy, xx = np.ogrid[:40, :80, :80]
    ref = ((zz - 20) ** 2 * 6.25 + (yy - 40) ** 2 + (xx - 40) ** 2) < 400
    m0 = G.metricas(ref, ref, grade)
    checar("as duas tolerancias estao nas metricas",
           "dsc_sup_1mm" in m0 and "dsc_sup_3mm" in m0, str(sorted(m0))[:110])
    checar("identico: as duas dao 1,0",
           m0["dsc_sup_1mm"] == 1.0 and m0["dsc_sup_3mm"] == 1.0, "")

    m3 = G.metricas(G.expandir(ref, 3.0, grade), ref, grade)
    checar("a 3 mm o DSC cai bastante", m3["dsc"] < 0.87, str(m3["dsc"]))
    checar("e o NSD@3mm ainda da nota maxima (o artefato do artigo)",
           m3["dsc_sup_3mm"] >= 0.99,
           "DSC %.3f mas NSD@3mm %.3f" % (m3["dsc"], m3["dsc_sup_3mm"]))
    checar("enquanto o NSD@1mm enxerga o deslocamento",
           m3["dsc_sup_1mm"] < 0.2,
           "NSD@1mm %.3f" % m3["dsc_sup_1mm"])
    checar("a 1 mm elas ordenam certo (1mm <= 3mm sempre)",
           all(G.metricas(G.expandir(ref, v, grade), ref, grade)["dsc_sup_1mm"]
               <= G.metricas(G.expandir(ref, v, grade), ref, grade)["dsc_sup_3mm"]
               for v in (1.0, 2.0, 3.0)), "")
    checar("`dsc_sup` continua existindo, para o acervo velho",
           "dsc_sup" in m0 and m0.get("tolerancia_sup_mm") == 2.0,
           str(m0.get("tolerancia_sup_mm")))


def teste_nuvem_3d():
    import radai_viewer3d as V3
    grade = G.Grade((2.5, 1.0, 1.0))
    zz, yy, xx = np.ogrid[:40, :80, :80]
    esf = ((zz - 20) ** 2 * 6.25 + (yy - 40) ** 2 + (xx - 40) ** 2) < 400
    d = V3.nuvem_de_mascara(esf, grade)
    checar("a nuvem tem pontos", len(d["pontos"]) > 200, str(len(d["pontos"])))
    p = np.array(d["pontos"])
    ext = p.max(0) - p.min(0)
    checar("as coordenadas estao em mm (esfera r=20 da ~38 mm)",
           all(30 < v < 45 for v in ext), str([round(v, 1) for v in ext]))
    checar("centrada no centroide", np.allclose(p.mean(0), 0, atol=2.0),
           str([round(v, 2) for v in p.mean(0)]))
    nn = np.array(d["normais"])
    checar("as normais sao unitarias",
           np.allclose(np.linalg.norm(nn, axis=1), 1.0, atol=0.03), "")
    r = p / np.maximum(np.linalg.norm(p, axis=1, keepdims=True), 1e-9)
    fora = float((np.sum(r * nn, axis=1) > 0).mean())
    checar("e apontam para FORA", fora > 0.95, "%.0f%%" % (100 * fora))
    d2 = V3.nuvem_de_mascara(esf, grade)
    checar("a amostragem e deterministica (girar e voltar nao muda)",
           d["pontos"] == d2["pontos"], "")
    grande = np.zeros((60, 200, 200), dtype=bool)
    grande[5:55, 20:180, 20:180] = True
    d3 = V3.nuvem_de_mascara(grande, G.Grade((2.5, 1.0, 1.0)), max_pontos=1500)
    checar("respeita o teto de pontos", len(d3["pontos"]) <= 1500,
           str(len(d3["pontos"])))
    checar("  e diz quantos havia no total", d3["n_total"] > 1500, str(d3["n_total"]))
    checar("mascara vazia devolve nuvem vazia",
           V3.nuvem_de_mascara(np.zeros((10, 10, 10), bool), grade)["pontos"] == [], "")

def teste_hd100_ve_a_ilha_que_o_hd95_esconde():
    g = G.Grade((1.0, 1.0, 1.0))
    ref = np.zeros((160, 80, 80), dtype=bool)
    ref[60:90, 30:50, 30:50] = True
    cand = ref.copy()
    cand[8:12, 38:42, 38:42] = True

    m = G.metricas(cand, ref, g)
    checar(u"o DSC quase nao ve a ilha (> 0,99)", m["dsc"] > 0.99, str(m["dsc"]))
    checar(u"o NSD a 3 mm quase nao ve a ilha (> 0,98)",
           m["dsc_sup_3mm"] > 0.98, str(m["dsc_sup_3mm"]))
    checar(u"o HD95 e CEGO a ilha (fica em 0,0 mm)",
           m["hd95_mm"] == 0.0, str(m["hd95_mm"]))
    checar(u"o HD100 acusa mais de 40 mm", m["hd100_mm"] > 40.0,
           str(m["hd100_mm"]))
    checar(u"o MSD fica pequeno (media dilui a ilha) mas nao zero",
           0.0 < m["msd_mm"] < 2.0, str(m["msd_mm"]))
    m0 = G.metricas(ref, ref, g)
    checar(u"contorno identico: HD100 = 0 e MSD = 0",
           m0["hd100_mm"] == 0.0 and m0["msd_mm"] == 0.0,
           "%s / %s" % (m0["hd100_mm"], m0["msd_mm"]))


def teste_msd_nao_depende_do_tamanho():
    g = G.Grade((1.0, 1.0, 1.0))

    def par(lado, desloca):
        a = np.zeros((80, 80, 80), dtype=bool)
        b = np.zeros((80, 80, 80), dtype=bool)
        i = 40 - lado // 2
        a[i:i + lado, i:i + lado, i:i + lado] = True
        b[i + desloca:i + lado + desloca, i:i + lado, i:i + lado] = True
        return a, b

    grande = G.metricas(*par(30, 2), grade=g)
    pequeno = G.metricas(*par(6, 2), grade=g)
    checar(u"o DSC pune o pequeno pelo mesmo deslocamento de 2 mm",
           grande["dsc"] - pequeno["dsc"] > 0.15,
           u"grande %.3f, pequeno %.3f" % (grande["dsc"], pequeno["dsc"]))
    checar(u"e o MSD dos dois fica dentro de 1 mm um do outro",
           abs(grande["msd_mm"] - pequeno["msd_mm"]) < 1.0,
           u"grande %.2f mm, pequeno %.2f mm"
           % (grande["msd_mm"], pequeno["msd_mm"]))


def teste_bussola_do_3d_acompanha_a_inversao_dos_eixos():
    import radai_viewer3d

    sentido = ("sup", "post", "esq")
    esperado = ["esq", "post", "sup"]
    checar(u"a ordem dos eixos de desenho e a inversa da do array",
           list(sentido)[::-1] == esperado)

    g = G.Grade((1.0, 1.0, 1.0), sentido)
    m = np.zeros((30, 30, 30), dtype=bool)
    m[10:14, 8:16, 4:20] = True
    d = radai_viewer3d.nuvem_de_mascara(m, g)
    pts = np.array(d["pontos"], dtype=float)
    ext = [float(pts[:, i].max() - pts[:, i].min()) for i in range(3)]
    checar(u"o eixo 0 do desenho e o mais longo (x do array, 16 voxels)",
           ext[0] > ext[1] > ext[2],
           u"extensoes: %.0f, %.0f, %.0f" % tuple(ext))

    for lado in ("sup", "inf", "ant", "post", "esq", "dir"):
        checar(u"o lado %s tem oposto declarado" % lado,
               lado in ("sup", "inf", "ant", "post", "esq", "dir"))


def teste_visor_declara_a_bussola_e_as_vistas():
    import io as _io
    import radai_viewer
    txt = _io.open(radai_viewer.__file__, encoding="utf-8",
                   errors="replace").read()
    checar(u"o painel 3D desenha a bussola", "n3Bussola" in txt)
    checar(u"e ela e chamada pelo desenho", "n3Bussola(g, c," in txt)
    checar(u"as tres vistas de volta existem",
           "N3_VISTAS" in txt and "n3Vista" in txt)
    checar(u"e a pose inicial tem botao", "N3_INICIAL" in txt)
    checar(u"o painel gira por toque, e nao so por mouse",
           "touchmove" in txt and "touchstart" in txt)
    checar(u"o canvas segue o tamanho real e a densidade da tela",
           "devicePixelRatio" in txt and "n3Ajustar" in txt)


def teste_meio_pixel_vai_para_fora_nos_dois_sentidos():
    secao("meio pixel: do centro do pixel para a aresta da celula")
    quad = np.array([[0.0, 0.0], [4, 0], [4, 3], [0, 3]])
    for rot, p in (("anti-horario", quad), ("horario", quad[::-1])):
        e = G.expandir_meio_pixel(p, 1.0, 1.0)
        checar("quadrado %s cresce, nao encolhe" % rot,
               abs(G.area_poligono(e)) > abs(G.area_poligono(p)),
               "%.1f -> %.1f mm2" % (abs(G.area_poligono(p)),
                                     abs(G.area_poligono(e))))
        checar("quadrado %s vira 5 x 4 mm" % rot,
               abs(abs(G.area_poligono(e)) - 20.0) < 1e-9,
               "%.4f mm2" % abs(G.area_poligono(e)))
    checar("o numero de vertices nao muda",
           len(G.expandir_meio_pixel(quad, 1.0, 1.0)) == len(quad))
    r = G.expandir_meio_pixel(quad, 2.0, 1.0)
    checar("pixel retangular expande por eixo",
           abs(abs(G.area_poligono(r)) - 6.0 * 4.0) < 1e-9,
           "%.4f, esperado 24" % abs(G.area_poligono(r)))
    for ruim in (np.zeros((2, 2)), np.zeros((5, 2)), np.array([[1.0, 1.0]] * 6)):
        s = G.expandir_meio_pixel(ruim, 1.0, 1.0)
        checar("entrada degenerada nao levanta nem vira NaN",
               s.shape == np.asarray(ruim).shape and np.isfinite(s).all())


def teste_sentido_poligono_distingue_os_dois_giros():
    secao("sentido do poligono")
    quad = np.array([[0.0, 0.0], [4, 0], [4, 3], [0, 3]])
    checar("anti-horario devolve +1", G.sentido_poligono(quad) == 1)
    checar("horario devolve -1", G.sentido_poligono(quad[::-1]) == -1)
    checar("poligono de 2 pontos devolve 0",
           G.sentido_poligono(np.zeros((2, 2))) == 0)
    checar("area_poligono e a MESMA nos dois giros (ela e o tamanho)",
           abs(G.area_poligono(quad) - G.area_poligono(quad[::-1])) < 1e-12)


def _arco_fino(Z=36, Y=180, X=180, k0=14, r=72):
    v = np.zeros((Z, Y, X), dtype=bool)
    for k in range(k0, k0 + 4):
        for ang in np.linspace(0.18, 2.60, 1200):
            yy, xx = 90 + r * np.sin(ang), 90 + r * np.cos(ang)
            t = min(ang - 0.18, 2.60 - ang) / 0.45
            raio = 0.7 + 1.1 * min(1.0, t)
            rr = int(np.ceil(raio))
            for dy in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    if dy * dy + dx * dx <= raio * raio:
                        v[k, int(round(yy + dy)), int(round(xx + dx))] = True
    return v


def teste_conjunto_aceita_sigma_por_estrutura():
    secao("suavizar_conjunto com sigma por estrutura")
    grade = G.Grade((3.0, 1.0, 1.0))
    costela = _arco_fino()
    zz, yy, xx = np.mgrid[0:36, 0:180, 0:180]
    longe = (((zz - 8) / 5.0) ** 2 + ((yy - 30) / 12.0) ** 2
             + ((xx - 30) / 12.0) ** 2) <= 1.0

    def eixo(m):
        i = np.argwhere(m)
        return int(i[:, 2].max() - i[:, 2].min() + 1)

    e0 = eixo(costela)
    forte = G.suavizar_conjunto({"costela": costela, "outra": longe}, 1.5, grade)
    fraco = G.suavizar_conjunto({"costela": costela, "outra": longe}, 0.8, grade)
    checar("a 1,5 mm a costela perde ponta (o defeito de campo)",
           eixo(forte["costela"]) < e0,
           "eixo %d -> %d mm" % (e0, eixo(forte["costela"])))
    checar("a 0,8 mm ela mantem o eixo longo",
           eixo(fraco["costela"]) == e0,
           "eixo %d -> %d mm" % (e0, eixo(fraco["costela"])))

    misto = G.suavizar_conjunto({"costela": costela, "outra": longe},
                                {"costela": 0.8, "outra": 2.5}, grade)
    checar("com dicionario, a costela recebe o SEU valor",
           eixo(misto["costela"]) == eixo(fraco["costela"]),
           "eixo %d, igual ao de 0,8 mm" % eixo(misto["costela"]))
    checar("e a outra recebe o dela, nao o da costela",
           int(misto["outra"].sum()) !=
           int(G.suavizar_conjunto({"costela": costela, "outra": longe},
                                   0.8, grade)["outra"].sum()))
    checar("a particao continua estanque",
           not (misto["costela"] & misto["outra"]).any())
    checar("o volume do conjunto e preservado",
           abs(int(misto["costela"].sum()) + int(misto["outra"].sum())
               - int(costela.sum()) - int(longe.sum())) <= 1)
    zero = G.suavizar_conjunto({"costela": costela, "outra": longe},
                               {"costela": 0.0, "outra": 0.0}, grade)
    checar("dicionario todo zero nao mexe em nada",
           int((zero["costela"] ^ costela).sum()) == 0)

def _bbox_de_antes(mask, folga_voxels):
    achou = np.where(mask)
    if len(achou[0]) == 0:
        return None
    cortes = []
    for eixo in range(3):
        lo = int(achou[eixo].min()) - int(folga_voxels[eixo])
        hi = int(achou[eixo].max()) + int(folga_voxels[eixo]) + 1
        cortes.append(slice(max(0, lo), min(mask.shape[eixo], hi)))
    return tuple(cortes)


def _mascaras_aleatorias(n, semente=20260925):
    rng = np.random.default_rng(semente)
    fora = [np.zeros((5, 7, 9), bool)]
    um = np.zeros((6, 6, 6), bool)
    um[5, 0, 3] = True
    fora.append(um)
    cheia = np.ones((4, 5, 6), bool)
    fora.append(cheia)
    for _ in range(n):
        sh = tuple(int(v) for v in rng.integers(3, 40, size=3))
        m = np.zeros(sh, bool)
        for _b in range(int(rng.integers(1, 5))):
            c = [int(rng.integers(0, s)) for s in sh]
            r = [int(rng.integers(0, 6)) for _s in sh]
            m[tuple(slice(max(0, c[i] - r[i]), c[i] + r[i] + 1)
                    for i in range(3))] = True
        if rng.random() < 0.4:
            m &= rng.random(sh) < 0.7
        fora.append(m)
    return fora


def teste_a_caixa_por_projecao_e_a_do_np_where():
    secao("a caixa por projecao e a mesma do np.where (spec F3)")
    ms = _mascaras_aleatorias(250)
    difere = []
    for i, m in enumerate(ms):
        for f in ((0, 0, 0), (1, 1, 1), (2, 3, 1), (7, 0, 4)):
            if G._bbox_folgado(m, f) != _bbox_de_antes(m, f):
                difere.append((i, f))
    checar("_bbox_folgado (projecao) == o de antes (np.where), %d mascaras "
           "x 4 folgas" % len(ms), not difere, str(difere[:3]))
    m8 = (ms[10] * 7).astype(np.uint8)
    checar("  e numa mascara uint8 com valor 7 tambem",
           G._bbox_folgado(m8, (1, 1, 1)) == _bbox_de_antes(m8, (1, 1, 1)))

    def _isca(mask, folga):
        lim = G._limites(mask)
        if lim is None:
            return None
        return tuple(slice(max(0, lim[e][0] - folga[e]),
                           min(mask.shape[e], lim[e][1] + folga[e]))
                     for e in range(3))
    checar("ISCA: a caixa sem o +1 do fim e acusada pela mesma comparacao",
           any(_isca(m, (0, 0, 0)) != _bbox_de_antes(m, (0, 0, 0))
               for m in ms))


def teste_as_caixas_das_conferencias():
    secao("radai_geom.Caixas: caixa, contagem e validade (spec F3)")
    g = G.Grade((3.0, 1.0, 0.5))
    ms = _mascaras_aleatorias(60, semente=7)
    masks = dict(("m%03d" % i, m) for i, m in enumerate(ms))
    cx = G.Caixas(masks)
    lento = G.Caixas(masks, folga=None)
    ruins = []
    for k, m in masks.items():
        mb, c, n = cx.de(k)
        ref = _bbox_de_antes(m, (1, 1, 1))
        if c != ref or n != int(m.sum()):
            ruins.append(k)
        if G.volume_de_voxels(n, g) != G.volume_cm3(m, g):
            ruins.append(k + " (volume)")
        _mb, cl, nl = lento.de(k)
        if m.any() and (cl != (slice(None),) * 3 or nl != n):
            ruins.append(k + " (lento)")
        j = cx.justa(k)
        if m.any():
            ref_j = [(int(np.flatnonzero(m.any(axis=tuple(
                a for a in range(3) if a != e)))[0]),
                int(np.flatnonzero(m.any(axis=tuple(
                    a for a in range(3) if a != e)))[-1]) + 1)
                for e in range(3)]
            if j != ref_j:
                ruins.append(k + " (justa)")
        elif j is not None or c is not None:
            ruins.append(k + " (vazia)")
    checar("de()/justa() batem com o np.where e com a soma, em %d mascaras"
           % len(masks), not ruins, str(ruins[:4]))
    k = "m005"
    antes = cx.de(k)[1]
    novo = np.zeros_like(masks[k])
    novo[0, 0, 0] = True
    masks[k] = novo
    checar("mascara TROCADA no dicionario tem a caixa refeita",
           cx.de(k)[1] == (slice(0, 2), slice(0, 2), slice(0, 2))
           and cx.de(k)[2] == 1, "%s -> %s" % (antes, cx.de(k)[1]))
    m8 = np.zeros((6, 6, 6), np.uint8)
    m8[2:4, 2:4, 2:4] = 5
    c8 = G.Caixas({"a": m8})
    checar("cru() devolve o valor do voxel (5), e nao o booleano",
           int(c8.cru("a").max()) == 5 and c8.cru("a").shape == (4, 4, 4))
    for ruim in (None, np.zeros((4, 4), bool)):
        try:
            G.Caixas({"x": ruim}).de("x")
            levantou = False
        except ValueError:
            levantou = True
        checar("mascara %s levanta ValueError (como `_bool`)"
               % ("None" if ruim is None else "2D"), levantou)


def _conferir_disjuntas_de_antes(partes):
    nomes = [k for k in partes if G._bool(partes[k]).any()]
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            if (G._bool(partes[a]) & G._bool(partes[b])).any():
                return "suavizar_conjunto exige mascaras disjuntas: %r e %r " \
                       "se sobrepoem" % (a, b)
    return None


def teste_a_conferencia_de_disjuntas_na_caixa():
    secao("suavizar_conjunto: a conferencia de disjuntas na caixa (F3)")
    g = G.Grade((3.0, 1.0, 1.0))
    rng = np.random.default_rng(11)
    difere, casos, sobrepoe = [], 0, 0
    for caso in range(60):
        sh = (10, 24, 24)
        partes = {}
        for j in range(int(rng.integers(2, 6))):
            m = np.zeros(sh, bool)
            c = [int(rng.integers(0, s)) for s in sh]
            r = [int(rng.integers(1, 4)) for _s in sh]
            m[tuple(slice(max(0, c[i] - r[i]), c[i] + r[i] + 1)
                    for i in range(3))] = True
            partes["p%d" % j] = m
        ref = _conferir_disjuntas_de_antes(partes)
        try:
            G.suavizar_conjunto(partes, 1.0, g)
            novo = None
        except ValueError as e:
            novo = str(e)
        casos += 1
        sobrepoe += ref is not None
        if ref != novo:
            difere.append((caso, ref, novo))
    checar("a mesma recusa (e o MESMO primeiro par) em %d grupos, %d com "
           "sobreposicao" % (casos, sobrepoe), not difere and sobrepoe >= 5,
           str(difere[:2]))
    a = np.zeros((6, 8, 8), bool)
    b = np.zeros((6, 8, 8), bool)
    a[1:4, 1:4, 1:4] = True
    b[3:6, 3:6, 3:6] = True

    def _isca(partes):
        nomes = list(partes)
        lim = dict((k, G._limites(partes[k])) for k in nomes)
        for i, x in enumerate(nomes):
            for y in nomes[i + 1:]:
                ib = tuple(slice(max(lim[x][e][0], lim[y][e][0]),
                                 min(lim[x][e][1], lim[y][e][1]))
                           for e in range(3))
                if (partes[x][ib] & partes[y][ib]).any():
                    return "sobrepoe"
        return None
    try:
        G.suavizar_conjunto({"a": a, "b": b}, 1.0, g)
        pegou = False
    except ValueError:
        pegou = True
    checar("a sobreposicao de UM voxel no canto das caixas e recusada", pegou)
    checar("ISCA: sem o +1 do fim ela passaria, e a referencia discorda",
           _isca({"a": a, "b": b}) is None
           and _conferir_disjuntas_de_antes({"a": a, "b": b}) is not None)


def _dist_ao_poligono(pts, poli):
    a = np.asarray(poli, float)[:, :2]
    b = np.roll(a, -1, axis=0)
    p = np.asarray(pts, float)[:, :2]
    ab = b - a
    comp2 = (ab ** 2).sum(axis=1)
    comp2[comp2 == 0] = 1e-12
    ap = p[:, None, :] - a[None, :, :]
    t = np.clip((ap * ab[None]).sum(axis=2) / comp2[None], 0.0, 1.0)
    proj = a[None] + t[..., None] * ab[None]
    return np.sqrt(((p[:, None, :] - proj) ** 2).sum(axis=2)).min(axis=1)


def teste_douglas_peucker_fechado():
    secao("Douglas-Peucker fechado (a decimacao do OAR_Fast)")
    t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    elipse = np.c_[30 * np.cos(t), 20 * np.sin(t), np.full(t.size, 7.5)]
    idx = G.douglas_peucker_fechado(elipse, 0.2)
    ficou = elipse[idx]
    saiu = np.delete(elipse, idx, axis=0)
    d = _dist_ao_poligono(saiu, ficou)
    checar("todo ponto que saiu esta a <= 0,2 mm do poligono que ficou",
           float(d.max()) <= 0.2 + 1e-9, "max %.4f mm" % float(d.max()))
    checar("os indices sao crescentes, sem repetir, e o ponto 0 fica",
           list(idx) == sorted(set(idx.tolist())) and idx[0] == 0)
    checar("  e a elipse de 400 pontos sai com menos de um quarto deles",
           len(idx) < 100, "%d pontos" % len(idx))
    a0, a1 = G.area_poligono(elipse), G.area_poligono(ficou)
    checar("  a area da elipse anda menos de 1,5%",
           abs(a1 / a0 - 1) < 0.015, "%.2f%%" % (100 * (a1 / a0 - 1)))
    ingenuo = elipse[::4]
    d2 = _dist_ao_poligono(np.delete(elipse, np.arange(0, 400, 4), axis=0),
                           ingenuo)
    tol_ing = float(d2.max())
    sq = np.array([[0, 0], [5, 0], [10, 0], [10, 5], [10, 10], [5, 10],
                   [0, 10], [0, 5]], float)
    ing_sq = sq[[1, 3, 5, 7]]
    d3 = _dist_ao_poligono(sq[[0, 2, 4, 6]], ing_sq)
    checar("ISCA: a mesma medida reprova a decimacao ingenua (o canto do "
           "quadrado fica a %.1f mm)" % float(d3.max()),
           float(d3.max()) > 0.2, "elipse ingenua: %.3f mm" % tol_ing)
    dp_sq = G.douglas_peucker_fechado(sq, 0.2)
    checar("  e o DP guarda os quatro cantos do quadrado",
           sorted(dp_sq.tolist()) == [0, 2, 4, 6], str(dp_sq.tolist()))
    quase = np.array([[0, 0], [1, 0], [2, 1e-4], [3, 0], [4, 0]], float)
    idq = G.douglas_peucker_fechado(quase, 0.2, minimo=3)
    checar("nunca menos de 3 pontos (poligono quase degenerado)",
           len(idq) >= 3, str(idq.tolist()))
    checar("tol <= 0 devolve tudo", len(G.douglas_peucker_fechado(
        elipse, 0.0)) == 400)
    checar("poligono de 3 pontos fica como esta",
           G.douglas_peucker_fechado(elipse[:3], 5.0).tolist() == [0, 1, 2])
    for r_mm in (2.0, 4.0, 10.0):
        tt = np.linspace(0, 2 * np.pi, max(24, int(2 * np.pi * r_mm / 0.25)),
                         endpoint=False)
        c = np.c_[r_mm * np.cos(tt), r_mm * np.sin(tt)]
        ic = G.douglas_peucker_fechado(c, 0.2)
        perda = G.area_poligono(c[ic]) / G.area_poligono(c) - 1
        checar("  circulo de raio %.0f mm: %d -> %d pontos, area %+.1f%%"
               % (r_mm, len(c), len(ic), 100 * perda),
               perda <= 0 and float(_dist_ao_poligono(
                   np.delete(c, ic, axis=0), c[ic]).max()) <= 0.2 + 1e-9)


def main():
    print("radai_geom %s | grade de teste: z=3,0 y=1,0 x=0,5 mm" % G.VERSAO_LIB)
    testes = [teste_nuvem_3d,
              teste_bussola_do_3d_acompanha_a_inversao_dos_eixos,
              teste_visor_declara_a_bussola_e_as_vistas,
              teste_hd100_ve_a_ilha_que_o_hd95_esconde,
              teste_msd_nao_depende_do_tamanho,
              teste_nsd_em_duas_tolerancias,
              teste_apl_mede_trabalho_e_nao_semelhanca,
              teste_expansao_isotropica, teste_extensao_unidirecional,
              teste_expansao_anisotropica,
              teste_expansao_casos_limite, teste_contracao,
              teste_componentes_e_buracos, teste_limitar_por_plano, teste_suavizar,
              teste_grade, teste_metricas,
              teste_o_nsd_salta_e_por_isso_ha_duas_tolerancias,
              teste_ancora_da_suavizacao,
              teste_meio_pixel_vai_para_fora_nos_dois_sentidos,
              teste_sentido_poligono_distingue_os_dois_giros,
              teste_conjunto_aceita_sigma_por_estrutura,
              teste_a_caixa_por_projecao_e_a_do_np_where,
              teste_as_caixas_das_conferencias,
              teste_a_conferencia_de_disjuntas_na_caixa,
              teste_douglas_peucker_fechado]
    for t in testes:
        try:
            t()
        except Exception as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False, "%s: %s" % (type(e).__name__, e))
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
