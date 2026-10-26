# -*- coding: utf-8 -*-
import ast
import io
import json
import os
import re
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, AQUI)
sys.path.insert(0, APP)

import _cleanup
_cleanup.adotar_prefixo("radai_neb_")
import tempfile as _tempfile
import _componentes
OFICINA = _componentes.oficina("neb_telas", __file__)
_BASE_TMP = _tempfile.mkdtemp(prefix="radai_neb_")
os.environ["RADAI_CALIB_DIR"] = os.path.join(_BASE_TMP, "calib")
_CFG = os.path.join(_BASE_TMP, "radai_watcher.config")
io.open(_CFG, "w", encoding="utf-8").write(u"ROOT=\n")
os.environ["RADAI_CONFIG"] = _CFG

_R = []


def checar(nome, ok, detalhe=u""):
    _R.append((nome, bool(ok), detalhe))
    if not ok:
        print(u"  FALHA  %s%s" % (nome, (u"  [%s]" % detalhe) if detalhe else u""))
    return bool(ok)


def secao(t):
    print(u"\n─── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def _fonte(nome):
    with io.open(_componentes.fonte("app/" + nome), encoding="utf-8") as f:
        return f.read()


def _sem_script(p):
    p = re.sub(r"(?s)<script.*?</script>", u" ", p)
    p = re.sub(r"(?s)<style.*?</style>", u" ", p)
    return re.sub(r"(?s)<!--.*?-->", u" ", p)


def _texto(p):
    import html
    return html.unescape(re.sub(r"<[^>]+>", u" ", _sem_script(p)))


def _chama(fonte, nome):
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Call):
            f = no.func
            if (getattr(f, "attr", None) or getattr(f, "id", None)) == nome:
                return True
    return False


def _balao_da_cabeca(p):
    m = re.search(r'<header class="ui-fn">(.*?)</header>', p, re.S)
    if not m:
        return u""
    b = re.search(r'class="ui-balao">(.*)', m.group(1), re.S)
    return _texto(b.group(1)) if b else u""


def _alerta_no_pe(p, depois_de):
    i = p.find(depois_de)
    m = re.search(r'<div class="ui-alerta[^"]*">.*?<span data-radai-frase>(.*?)</span></div>',
                  p[i:] if i >= 0 else u"", re.S)
    return _texto(m.group(1)).strip() if (i >= 0 and m) else u""


def _norm(t):
    return u" ".join((t or u"").split())


def _chaves():
    import radai_phrases as F
    return {F.normalizar(l[0]): l for l in F.TABELA}


def _tem_os_doze(frase, chaves=None):
    import radai_phrases as F
    chaves = chaves or _chaves()
    l = chaves.get(F.normalizar(frase))
    return bool(l and len(l) == 12 and all(l[1:]))


def teste_os_comentarios_de_antes_ficaram():
    if OFICINA is None:
        secao(u"os comentários das três telas estão no aprendizado")
        _componentes.pulado(u"o aprendizado guardado das três telas")
        return
    OFICINA.teste_os_comentarios_de_antes_ficaram(sys.modules[__name__])


def _nomes_da_projecao():
    import radai_breadcrumb as B
    import radai_menu as MN
    import radai_modules as M
    fora = {u"trilha": B.ARVORE["nidus_projecao"][0]}
    fora[u"trilho"] = [i[3] for i in MN.ITENS if i[0] == "nidus_projecao"][0]
    fora[u"mini-página"] = [f[2] for f in M.FERRAMENTAS["nidus"] if f[0] == "nidus_projecao"][0]
    return fora


def teste_um_nome_so_para_a_projecao():
    secao(u"Nidus RT: a ferramenta tem um nome só, em todo lugar")
    nomes = _nomes_da_projecao()
    checar(u"trilha, trilho e mini-página dizem «Projeção Vascular», como a tag",
           set(nomes.values()) == {u"Projeção Vascular"}, nomes)
    isca = dict(nomes, trilha=u"Projeção vascular")
    checar(u"  isca: um lugar com o nome antigo é acusado",
           set(isca.values()) != {u"Projeção Vascular"})


def teste_nidus_estrutura():
    secao(u"Nidus RT: a cabeça, o ?, o alerta e os comandos")
    import radai_modules as M
    import radai_nidus as N
    import radai_nidus_screen as S
    fonte = _fonte("radai_nidus_screen.py")
    p = S.pagina()
    checar(u"a tela chama radai_ui.cabeca_de_funcao", _chama(fonte, "cabeca_de_funcao"))
    checar(u"a tag diz «Projeção Vascular», na cor do Nidus",
           u"Projeção Vascular" in p and u"--mod-nidus" in p.split(u"</header>")[0])
    checar(u"a capa antiga saiu", u"rc-capa" not in p)
    bal = _norm(_balao_da_cabeca(p))
    for rot, frase in ((u"o título da fronteira", u"O que esta tela é, e o que ela não é."),
                       (u"o SEM_VOLUME", N.SEM_VOLUME), (u"a limitação clínica", N.LIMITACAO_CLINICA),
                       (u"a limitação da RM", N.LIMITACAO_RM)):
        checar(u"o ? da cabeça tem %s" % rot, _norm(frase)[:60] in bal, bal[:80])
    checar(u"e o texto longo saiu da tela", u'class="nd-fronteira"' not in p)
    checar(u"nenhum rótulo chama o MPR de «tomografia»",
           not re.search(r">\s*tomografia\s*<", p, re.I))
    checar(u"o MPR tem rótulo próprio e a modalidade da série",
           u'id="nd_mpr"' in p and u'id="nd_mod"' in p)
    i_trab, i_mpr = p.find(u'class="nd-trabalho"'), p.find(u'id="nd_mpr"')
    checar(u"a projeção e o MPR moram no mesmo trabalho, o MPR depois",
           0 < i_trab < p.find(u'id="nd_palco"') < i_mpr)
    linha = _norm(_texto(M.MODULOS["nidus"]["linha"]))
    checar(u"o alerta do pé é a linha do módulo, depois do MPR",
           _norm(_alerta_no_pe(p, u'id="nd_mpr"')) == linha, _alerta_no_pe(p, u'id="nd_mpr"'))
    for ident, rot in ((u"nd_procurar", u"Procurar (explorador)"), (u"nd_inverter", u"inverter cores"),
                       (u"nd_zoom_mais", u"aproximar"), (u"nd_zoom_menos", u"afastar"),
                       (u"nd_zoom_ajustar", u"ajustar à tela"), (u"nd_eixos", u"eixos 3D"),
                       (u"nd_caixa_bt", u"caixa de recorte"), (u"nd_caixa_limpar", u"limpar recorte"),
                       (u"nd_cx0", u"a caixa no axial"), (u"nd_cx1", u"a caixa no coronal"),
                       (u"nd_cx2", u"a caixa no sagital")):
        checar(u"existe: %s" % rot, u'id="%s"' % ident in p)
    checar(u"«Procurar» abre o explorador de pastas", u"uiExplorador(" in S.JS)
    checar(u"a etiqueta da demo saiu", u'id="nd_demo"' not in p and u"nd_demo" not in S.JS)
    checar(u"o carregamento orgânico cobre a espera", u"uiCarregando(" in S.JS)
    import test_nidus as TN
    soltos = TN.identificadores_soltos(S.JS)
    checar(u"o JS não lê nome solto", not soltos, u", ".join(soltos))
    _sem_marcador(p)


def _sem_marcador(p):
    import radai_ui
    q = radai_ui._resolver_icones(p)
    checar(u"sem @MARCADOR@ sobrando (ícone inclusive)", not re.findall(r"@[A-Z_]+@", q),
           re.findall(r"@[A-Z_]+@", q)[:3])


def teste_elastic_estrutura():
    secao(u"Elastic RT: a cabeça, o ?, o alerta e o explorador")
    import radai_elastic as E
    import radai_elastic_screen as T
    import radai_modules as M
    fonte = _fonte("radai_elastic_screen.py")
    p = T.pagina()
    checar(u"a tela chama radai_ui.cabeca_de_funcao", _chama(fonte, "cabeca_de_funcao"))
    cab = p.split(u"</header>")[0]
    checar(u"a tag diz «Fusão elástica», na cor do Elastic",
           u"Fusão elástica" in cab and u"--mod-elastic" in cab)
    checar(u"a frase é a do módulo", _norm(M.MODULOS["elastic"]["frase"]) in _norm(_texto(cab)))
    bal = _norm(_balao_da_cabeca(p))
    checar(u"o ? da cabeça diz que não propaga contorno", _norm(E.NAO_PROPAGA)[:50] in bal, bal[:80])
    checar(u"o aviso de cima saiu da tela", u'class="el-aviso"' not in p)
    al = _alerta_no_pe(p, u'id="el-corpo"')
    checar(u"o alerta do pé diz que a fusão não é aprovada",
           u"sugestão não aprovada" in al and u"ato médico" in al, al)
    checar(u"e é a frase inteira da regra 1, à vista (nada dela atrás do ?)",
           _norm(al) == _norm(E.SEM_APROVACAO), al)
    vis = _texto(p)
    checar(u"a tela não cita TPS nem Eclipse",
           u"TPS" not in vis and u"Eclipse" not in vis,
           [w for w in (u"TPS", u"Eclipse") if w in vis])
    bal_mod = u" ".join(u" ".join(v) for v in M.secoes_de_ajuda("elastic").values())
    checar(u"nem o ? da mini-página do módulo",
           u"TPS" not in bal_mod and u"Eclipse" not in bal_mod)
    checar(u"«Escolher a pasta» abre o explorador",
           u'id="el-procurar"' in p and u"uiExplorador(" in T.JS)
    checar(u"a linha da demo saiu", u'id="el-demo"' not in p)
    _sem_marcador(p)


def teste_bolus_estrutura():
    secao(u"3D Printed Bolus: a cabeça, os três botões, o zoom e o explorador")
    import radai_bolus as B
    import radai_bolus_screen as T
    fonte = _fonte("radai_bolus_screen.py")
    p = T.pagina()
    checar(u"a tela chama radai_ui.cabeca_de_funcao", _chama(fonte, "cabeca_de_funcao"))
    cab = p.split(u"</header>")[0]
    checar(u"a tag diz «Gerar bólus», na cor do bólus",
           u"Gerar bólus" in cab and u"--mod-bolus" in cab)
    checar(u"a capa antiga saiu", u"rc-capa" not in p)
    bal = _norm(_balao_da_cabeca(p))
    checar(u"o ? da cabeça diz o que sai e o que não sai",
           u"O que sai daqui, e o que não sai." in bal and u"Sai um STL" in bal, bal[:80])
    checar(u"e o texto saiu do pé da tela", u'class="bo-fronteira"' not in p)
    al = _alerta_no_pe(p, u'id="bo-corpo"')
    checar(u"o alerta do autor está no pé, numa linha", _norm(al) == _norm(B.ALERTA), al)
    m = re.search(r'<div class="bo-pecas" id="bo-pecas">(.*?)</div>', p, re.S)
    bts = re.findall(r'<button id="([\w-]+)"[^>]*>', m.group(1)) if m else []
    checar(u"os três botões, na ordem: gerar · STL do bólus · STL do molde",
           bts == [u"bo-gerar", u"bo-exportar", u"bo-exportar-molde"], bts)
    escond = re.findall(r'<button id="(bo-(?:gerar|exportar|exportar-molde))"[^>]*\shidden', p)
    checar(u"nenhum dos três nasce escondido", not escond, escond)
    rot = _norm(_texto(m.group(1))) if m else u""
    checar(u"os rótulos são os do autor",
           u"Exportar STL do bólus" in rot and u"Exportar STL do molde" in rot
           and u"…" not in rot, _norm(rot))
    checar(u"a tabela vem DEPOIS dos botões",
           0 < p.find(u'id="bo-pecas"') < p.find(u'id="bo-resultado"'))
    checar(u"o JS nunca esconde o botão do molde",
           u"el('bo-exportar-molde').hidden" not in T.JS)
    checar(u"«Procurar» abre o explorador de pastas",
           u'id="bo-procurar"' in p and u"uiExplorador(" in T.JS)
    checar(u"os dois palcos 3D têm zoom pela roda",
           T.JS.count(u"addEventListener('wheel'") >= 1 and u"cam.zoom" in T.JS)
    _sem_marcador(p)


def teste_as_iscas():
    secao(u"as iscas: a versão errada de cada tela é acusada")
    import radai_bolus_screen as TB
    import radai_elastic_screen as TE
    import radai_modules as M
    import radai_nidus_screen as S
    p = S.pagina()
    i, j = p.find(u'<div class="ui-alerta'), p.find(u'<section class="nd-cx nd-mpr"')
    fim = p.find(u"</div>", p.find(u"</span></div>", i)) + 6
    alerta = p[i:p.find(u"</span></div>", i) + len(u"</span></div>")]
    isca = p.replace(alerta, u"").replace(u'<section class="nd-cx nd-mpr"',
                                         alerta + u'<section class="nd-cx nd-mpr"')
    linha = _norm(_texto(M.MODULOS["nidus"]["linha"]))
    checar(u"  isca: o alerta do Nidus ANTES do MPR é acusado",
           i > 0 and j > 0 and fim > i and _norm(_alerta_no_pe(isca, u'id="nd_mpr"')) != linha)
    checar(u"  isca: «tomografia» de volta no rótulo do MPR é acusada",
           bool(re.search(r">\s*tomografia\s*<", p.replace(u"<span>MPR <b",
                                                           u"<span>tomografia</span><span>MPR <b"), re.I)))
    pe = TE.pagina()
    checar(u"  isca: «TPS» de volta na tela do Elastic é acusado",
           u"TPS" in _texto(pe.replace(u"</header>", u"<p>contra o TPS</p></header>")))
    pb = TB.pagina()
    isca_b = pb.replace(u'<button id="bo-exportar-molde" class="bo-bt2" type="button"',
                        u'<button id="bo-exportar-molde" class="bo-bt2" type="button" hidden')
    checar(u"  isca: o botão do molde escondido é acusado",
           isca_b != pb and re.findall(
               r'<button id="(bo-(?:gerar|exportar|exportar-molde))"[^>]*\shidden', isca_b))
    checar(u"  isca: sem a cabeça de função, a checagem do AST reprova",
           not _chama(u"import radai_ui\nx = 'cabeca_de_funcao'\n", "cabeca_de_funcao"))


def teste_as_frases_novas_tem_os_doze():
    secao(u"as frases novas destas telas têm os doze idiomas")
    import radai_elastic as E
    ch = _chaves()
    novas = (u"Projeção Vascular", u"Inverter cores", u"Aproximar", u"Afastar",
             u"Ajustar à tela", u"Caixa de recorte", u"Limpar recorte", u"Listar séries",
             u"Exportar STL do bólus", u"Exportar STL do molde",
             E.REFERENCIA_E_NOSSA)
    faltam = [f for f in novas if not _tem_os_doze(f, ch)]
    checar(u"todas as frases novas com as onze traduções", not faltam, faltam)
    checar(u"  isca: frase inventada é acusada", not _tem_os_doze(u"frase que não existe ZQX", ch))


def _volume_com_marcas(n=48, esp=2.0):
    import numpy as np
    import SimpleITK as sitk
    v = np.full((n, n, n), -1000.0, dtype=np.float32)
    c = n // 2
    v[c - 2:c + 3, c - 2:c + 3, c + 12:c + 17] = 1500.0
    v[c - 2:c + 3, c + 12:c + 17, c - 2:c + 3] = 1200.0
    v[c + 12:c + 17, c - 2:c + 3, c - 2:c + 3] = 900.0
    img = sitk.GetImageFromArray(v)
    img.SetSpacing((esp, esp, esp))
    img.SetOrigin((-c * esp, -c * esp, -c * esp))
    return img


def _centroide(plano, lo, hi):
    import numpy as np
    m = (plano >= lo) & (plano <= hi)
    if not m.any():
        return None
    ls, cs = np.nonzero(m)
    return float(cs.mean()), float(ls.mean())


def teste_os_eixos_seguem_a_projecao():
    secao(u"Nidus RT: os eixos 3D apontam para onde a projeção põe a anatomia")
    import math
    import radai_nidus as N
    img = _volume_com_marcas()
    lado = 128
    casos = ((0.0, 0.0), (40.0, 0.0), (0.0, 30.0), (35.0, -25.0), (-50.0, 20.0))

    def concorda(fn):
        piores = []
        for lao, cra in casos:
            ex = fn(lao, cra)
            for nome, lo, hi in ((u"L", 1400, 1600), (u"P", 1150, 1250),
                                 (u"S", 850, 950)):
                plano, _i = N.projetar(img, lao, cra, "mip", "osso", lado=lado,
                                       escala={"min": -1000.0, "max": 1500.0, "hu": True})
                cc = _centroide(plano, lo, hi)
                if cc is None:
                    piores.append(-1.0)
                    continue
                vx, vy = cc[0] - lado / 2.0, cc[1] - lado / 2.0
                ax, ay = ex[nome][0], ex[nome][1]
                nv, na = math.hypot(vx, vy), math.hypot(ax, ay)
                if nv < 2 or na < 0.2:
                    continue
                piores.append((vx * ax + vy * ay) / (nv * na))
        return min(piores) if piores else -1.0

    if not hasattr(N, "eixos_da_incidencia"):
        checar(u"radai_nidus.eixos_da_incidencia existe", False)
        return
    pior = concorda(N.eixos_da_incidencia)
    checar(u"cada eixo aponta para a marca dele na projeção (cos ≥ 0,95)",
           pior >= 0.95, u"%.3f" % pior)
    isca = concorda(lambda a, c: N.eixos_da_incidencia(-a, -c))
    checar(u"  isca: com os ângulos trocados de sinal, a checagem reprova",
           isca < 0.95, u"%.3f" % isca)
    e0 = N.eixos_da_incidencia(0.0, 0.0)
    checar(u"de frente: a esquerda do paciente à direita da tela, o crânio em cima",
           e0["L"][0] > 0.99 and e0["S"][1] < -0.99 and abs(e0["P"][2]) > 0.99, e0)


def teste_a_caixa_recorta_a_projecao():
    secao(u"Nidus RT: a projeção mostra só o que está dentro da caixa")
    import radai_nidus as N
    img = _volume_com_marcas()
    if not hasattr(N, "caixa_de_texto"):
        checar(u"radai_nidus.caixa_de_texto existe", False)
        return
    checar(u"a caixa inteira é «sem caixa»", N.caixa_de_texto(u"0,1,0,1,0,1") is None)
    checar(u"texto torto é «sem caixa»", N.caixa_de_texto(u"a,b") is None
           and N.caixa_de_texto(u"") is None)
    cx = N.caixa_de_texto(u"0.2,0.8,0.2,0.8,-1,0.55")
    checar(u"os valores são presos a [0, 1] e em ordem",
           cx == (0.2, 0.8, 0.2, 0.8, 0.0, 0.55), cx)
    serie = N.abrir(img, "CT")
    esc = serie.escala
    cheio, _ = N.projetar(serie.img, 0, 0, "mip", "osso", lado=128, escala=esc)
    caixa = N.caixa_de_texto(u"0,1,0,1,0,0.6")
    rec = serie.img_na_caixa(caixa, "mip")
    corte, ic = N.projetar(serie.img, 0, 0, "mip", "osso", lado=128, escala=esc, amostra=rec)
    _c0, i0 = N.projetar(serie.img, 0, 0, "mip", "osso", lado=128, escala=esc)
    checar(u"sem caixa, a marca da esquerda aparece", _centroide(cheio, 1400, 1600) is not None)
    checar(u"com a caixa, ela some", _centroide(corte, 1400, 1600) is None)
    checar(u"e o que está dentro continua", _centroide(corte, 850, 950) is not None)
    import numpy as np
    import SimpleITK as sitk
    va = sitk.GetArrayFromImage(serie.img)
    va[:, :, 29:] = -1000.0
    apagada = sitk.GetImageFromArray(va)
    apagada.CopyInformation(serie.img)
    ref, _ = N.projetar(apagada, 0, 0, "mip", "osso", lado=128, escala=esc)
    dif = float(np.abs(corte.astype(np.float64) - ref).max())
    checar(u"é a mesma projeção da série com o fora da caixa apagado (sem a cópia)",
           dif < 1.0, u"%.3f" % dif)
    checar(u"a geometria é a mesma (a caixa não muda a grade do detector)",
           corte.shape == cheio.shape and ic["passo_mm"] == i0["passo_mm"])
    def _voxels(im):
        n = 1
        for d in im.GetSize():
            n *= d
        return n
    checar(u"o recorte guarda só a caixa, e não uma cópia da série inteira",
           _voxels(rec) <= 0.62 * _voxels(serie.img), str((rec.GetSize(), serie.img.GetSize())))
    isca, ii = N.projetar(rec, 0, 0, "mip", "osso", lado=128, escala=esc)
    checar(u"  isca: com a grade tirada do recorte, a geometria muda",
           ii["passo_mm"] != i0["passo_mm"], str((ii["passo_mm"], i0["passo_mm"])))
    checar(u"a mesma caixa é servida do cache", serie.img_na_caixa(caixa, "mip") is rec)


def _serie_fantoma(destino):
    from datetime import datetime
    from make_test_series import escreve_serie
    escreve_serie(destino, u"NEB", datetime.now(), 24)
    return destino


def _cliente(montar):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    montar(app)
    return TestClient(app)


def teste_as_rotas():
    secao(u"as rotas: as listas sem demo, a caixa na projeção, as telas do MPR")
    import time
    import radai_elastic_screen as T
    import radai_nidus_screen as S
    import radai_varrer
    pasta = _serie_fantoma(os.path.join(_BASE_TMP, "rotas", "share", "PAC", "CT"))

    def _nidus_e_casca(app):
        radai_varrer.montar(app)
        S.montar(app)
    c = _cliente(_nidus_e_casca)
    d = c.post("/api/varrer/iniciar", json={
        "uso": "series", "pasta": pasta, "dias": 0,
        "opcoes": {"modalidades": list(S.MODALIDADES),
                   "min_cortes": S.MIN_CORTES}}).json()
    for _ in range(100):
        if d.get("fim"):
            break
        time.sleep(0.2)
        d = c.post("/api/varrer/estado", json={"v": d.get("v", "")}).json()
    ss = list(d.get("linhas") or [])
    checar(u"Nidus: a série da pasta, e só ela, pela varredura da casca",
           len(ss) == 1 and not [s for s in ss if s.get("demo")], d)
    checar(u"nenhum caminho sai na lista",
           all(pasta not in u"%s" % v for s in ss for v in s.values()))
    d0 = c.post("/api/varrer/iniciar", json={"uso": "series", "pasta": u""}).json()
    checar(u"sem a pasta, a varredura nem começa e diz por quê",
           d0.get("fim") is True and d0.get("erro") == radai_varrer.SEM_PASTA, d0)
    checar(u"  e a rota própria de séries do Nidus saiu",
           c.post("/api/nidus/series", json={"pasta": pasta}).status_code
           in (404, 405))
    if not ss:
        return
    b = ss[0]["bilhete"]
    f = c.get("/api/nidus/forma", params={"b": b}).json()
    telas = f.get("telas") or {}
    checar(u"a forma diz o tamanho de cada corte na tela (para a caixa)",
           sorted(telas) == ["0", "1", "2"] and all(len(v) == 2 for v in telas.values()), f)
    r1 = c.get("/api/nidus/projecao", params={"b": b, "lado": 256})
    r2 = c.get("/api/nidus/projecao", params={"b": b, "lado": 256,
                                               "caixa": "0.4,0.6,0.4,0.6,0.4,0.6"})
    checar(u"a projeção com caixa sai, e é outra imagem",
           r1.status_code == 200 and r2.status_code == 200
           and r2.headers.get("content-type") == "image/png" and r1.content != r2.content)

    import radai_varrer

    def _elastic_e_casca(app):
        radai_varrer.montar(app)
        T.montar(app)
    e = _cliente(_elastic_e_casca)
    v = e.post("/api/varrer/iniciar", json={
        "uso": T.USO_DA_VARREDURA, "pasta": pasta, "dias": 0,
        "opcoes": T.opcoes_da_varredura()}).json()
    for _ in range(100):
        if v.get("fim"):
            break
        time.sleep(0.2)
        v = e.post("/api/varrer/estado", json={"v": v.get("v", "")}).json()
    d = e.post("/api/elastic/assentar", json={"v": v.get("v", ""),
                                              "pasta": pasta}).json()
    checar(u"Elastic: a busca (a varredura da casca) termina com a série da "
           u"pasta, sem demo", len(d.get("series") or []) == 1 and "demo" not in d, d)
    checar(u"  e sem caminho na resposta", pasta not in json.dumps(d))
    r = e.post("/api/elastic/fundir", json={"fixa": "x", "movel": "x"}).json()
    checar(u"fundir uma série com ela mesma é recusado no servidor",
           r.get("erro") == T.ESCOLHA_DUAS, r)


PORTA = 8847
BASE = "http://127.0.0.1:%d" % PORTA


def _chromium():
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if not os.path.isdir(base):
        return None
    for nome in sorted(os.listdir(base), reverse=True):
        if not nome.startswith("chromium-"):
            continue
        for sub in ("chrome-win64", "chrome-win"):
            exe = os.path.join(base, nome, sub, "chrome.exe")
            if os.path.isfile(exe):
                return exe
    return None


def _subir(base_tmp):
    import subprocess
    import time
    import urllib.request
    from datetime import datetime, timedelta
    from make_test_series import escreve_serie
    root = os.path.join(base_tmp, "share")
    escreve_serie(os.path.join(root, "PAC_A", "CT"), u"PAC_A",
                  datetime.now() - timedelta(days=1), 30)
    escreve_serie(os.path.join(root, "PAC_A", "CT2"), u"PAC_A",
                  datetime.now() - timedelta(days=2), 30)
    cfg = os.path.join(base_tmp, "t.config")
    io.open(cfg, "w", encoding="utf-8").write(
        u"ROOT=%s\nDRY_RUN=1\nMIN_SLICES=5\nQUIET_MIN=0\nTPS_DESTINO=eclipse\n"
        u"PORT=%d\nLOG_DIR=%s\n" % (root, PORTA, os.path.join(base_tmp, "log")))
    env = dict(os.environ, RADAI_CONFIG=cfg, RADAI_MACHINE="BATERIA_NEB",
               RADAI_CALIB_DIR=os.path.join(base_tmp, "calib"),
               RADAI_REGISTRO_DIR=os.path.join(base_tmp, "registro"),
               LOCALAPPDATA=os.path.join(base_tmp, "ad"),
               RADAI_NOTIFICACAO="0", RADAI_URL_VERSOES="0",
               PYTHONIOENCODING="utf-8:replace")
    saida = io.open(os.path.join(base_tmp, "vigia.log"), "wb")
    proc = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                            env=env, stdout=saida, stderr=subprocess.STDOUT)
    for _ in range(90):
        try:
            urllib.request.urlopen(BASE + "/aceite", timeout=2).read()
            return proc, root
        except Exception:
            time.sleep(1)
    proc.kill()
    return None, root


def _sem_rolagem_lateral(pg):
    return pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")


def _caixa(pg, sel):
    return pg.evaluate("(function(){ var e = document.querySelector(%s);"
                       " if(!e) return null; var r = e.getBoundingClientRect();"
                       " return {x:r.left, y:r.top + window.scrollY, w:r.width, h:r.height,"
                       " b:r.bottom + window.scrollY} })()" % json.dumps(sel))


def _print(pg, nome):
    d = os.environ.get("RADAI_PRINTS_DIR", "").strip()
    if d:
        os.makedirs(d, exist_ok=True)
        pg.evaluate("window.scrollTo(0, 0)")
        pg.wait_for_timeout(250)
        pg.screenshot(path=os.path.join(d, nome + ".png"), full_page=True)


def _ajustes(pg, idioma, tema):
    pg.evaluate("(function(){ try{ localStorage.setItem('radai_tema', %s);"
                " localStorage.setItem('radai_idioma', %s); }catch(e){} })()"
                % (json.dumps(tema), json.dumps(idioma or u"pt-BR")))


def _elastic(pg, checar, larg, idioma, tema, root):
    rot = u"%d %s %s" % (larg, idioma or u"pt", tema)
    pg.goto(BASE + "/elastic/fusao", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    tag = pg.inner_text("h1.ui-fn-tag")
    esperado = u"Elastic fusion" if idioma == "en" else u"Fusão elástica"
    checar(u"[Elastic %s] a tag diz %s" % (rot, esperado), esperado in tag, tag)
    checar(u"[Elastic %s] sem rolagem lateral" % rot, _sem_rolagem_lateral(pg))
    checar(u"[Elastic %s] a tela não cita TPS" % rot, u"TPS" not in pg.inner_text("body"))
    checar(u"[Elastic %s] a linha da demo saiu" % rot, not pg.is_visible("#el-demo"))
    checar(u"[Elastic %s] nada abre nem varre sozinho, e «Fundir» nasce desligado" % rot,
           not pg.is_visible("#el_escolha") and pg.is_disabled("#el-fundir"))
    pg.click("#el-movel")
    pg.wait_for_timeout(500)
    pg.click("#el_origem-t-pasta")
    pg.fill("#el-pasta", root)
    pg.click("#el-buscar")
    pg.wait_for_function("document.querySelectorAll('#el-lista .el-it').length >= 2",
                         timeout=60000)
    pg.wait_for_timeout(900)
    if idioma == "en":
        lin = pg.inner_text("#el-pastas")
        checar(u"[Elastic %s] a linha da pasta já sai traduzida" % rot,
               u"série" not in lin, lin)
        ops = pg.eval_on_selector_all("#el-lista .el-it", "os => os.map(o => o.textContent)")
        checar(u"[Elastic %s] e a lista de séries também" % rot,
               not [o for o in ops if u"cortes" in o], ops)
    pg.click("#el-lista .el-it >> nth=0")
    pg.wait_for_timeout(500)
    pg.click("#el-fixa")
    pg.wait_for_timeout(500)
    pg.click("#el-lista .el-it >> nth=1")
    pg.wait_for_timeout(900)
    par = pg.evaluate("[elB('fixa'), elB('movel')]")
    checar(u"[Elastic %s] cada cartão escolhe a sua série no popup, e as duas formam o par" % rot,
           all(par) and par[0] != par[1] and not pg.is_visible("#el_escolha"), par)
    checar(u"[Elastic %s] e com ele «Fundir» fica disponível" % rot,
           pg.is_enabled("#el-fundir"))
    if idioma == "en":
        cs = pg.inner_text("#el-fixa .ui-cartao-rot")
        checar(u"[Elastic %s] o cartão diz a série já traduzida" % rot,
               u"cortes" not in cs and u"série" not in cs, cs)
    al = _caixa(pg, ".el-wrap > .ui-alerta")
    topo = _caixa(pg, ".el-topo")
    checar(u"[Elastic %s] o alerta no pé" % rot, al and topo and al["y"] > topo["b"], (al, topo))
    pg.click("#el-movel")
    pg.wait_for_timeout(500)
    pg.click("#el_origem-t-pasta")
    pg.click("#el-procurar")
    pg.wait_for_timeout(500)
    checar(u"[Elastic %s] «Procurar…» abre o explorador de pastas" % rot, pg.is_visible(".ui-fp"))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    _print(pg, u"elastic_%s_%s_%s" % (larg, idioma or u"pt", tema))


def _iluminados(pg, sel):
    return pg.evaluate(
        "(function(){ var c = document.querySelector(%s), g = c.getContext('2d');"
        " var d = g.getImageData(0, 0, c.width, c.height).data, n = 0;"
        " for(var i = 0; i < d.length; i += 4) if(d[i] + d[i+1] + d[i+2] > 330) n++;"
        " return n / (c.width * c.height) })()" % json.dumps(sel))


def _bolus(pg, checar, larg, idioma, tema, root):
    rot = u"%d %s %s" % (larg, idioma or u"pt", tema)
    pg.goto(BASE + "/bolus/gerar", wait_until="networkidle")
    pg.wait_for_timeout(700)
    tag = pg.inner_text("h1.ui-fn-tag")
    esperado = u"Generate bolus" if idioma == "en" else u"Gerar bólus"
    checar(u"[Bólus %s] a tag diz %s" % (rot, esperado), esperado in tag, tag)
    checar(u"[Bólus %s] sem rolagem lateral" % rot, _sem_rolagem_lateral(pg))
    checar(u"[Bólus %s] o popup da série abre ao chegar, na aba «Aponte uma pasta»" % rot,
           pg.is_visible("#bo_escolha #bo-pasta"))
    pg.fill("#bo-pasta", root)
    pg.click("#bo-listar")
    pg.wait_for_function("document.getElementById('bo-serie').options.length > 0", timeout=20000)
    pg.click("#bo-abrir")
    pg.wait_for_function("getComputedStyle(document.getElementById('bo-corpo')).display !== 'none'",
                         timeout=30000)
    pg.wait_for_timeout(2500)
    bts = [_caixa(pg, "#" + i) for i in ("bo-gerar", "bo-exportar", "bo-exportar-molde")]
    checar(u"[Bólus %s] os três botões à vista, lado a lado e na ordem" % rot,
           all(b and b["w"] > 0 for b in bts) and bts[0]["x"] < bts[1]["x"] < bts[2]["x"]
           and abs(bts[0]["y"] - bts[2]["y"]) < 4, bts)
    checar(u"[Bólus %s] sem nada gerado, os de exportar ficam apagados" % rot,
           pg.is_disabled("#bo-exportar") and pg.is_disabled("#bo-exportar-molde")
           and pg.is_enabled("#bo-gerar"))
    tab = _caixa(pg, "#bo-resultado")
    checar(u"[Bólus %s] a tabela fica embaixo dos botões" % rot, tab and tab["y"] >= bts[0]["b"])
    al = _caixa(pg, ".bo-wrap > .ui-alerta")
    corpo = _caixa(pg, "#bo-corpo")
    checar(u"[Bólus %s] o alerta no pé" % rot, al and corpo and al["y"] >= corpo["b"], (al, corpo))
    n0 = _iluminados(pg, "#bo-c3d")
    c = _caixa(pg, "#bo-c3d")
    pg.mouse.move(c["x"] + c["w"] / 2, c["y"] - pg.evaluate("window.scrollY") + c["h"] / 2)
    for _ in range(4):
        pg.mouse.wheel(0, -200)
        pg.wait_for_timeout(120)
    pg.wait_for_timeout(2500)
    n1 = _iluminados(pg, "#bo-c3d")
    checar(u"[Bólus %s] a roda aproxima o 3D do paciente" % rot, n1 > n0 * 1.2, (n0, n1))
    pg.click("[data-vista=ant]")
    pg.wait_for_timeout(2500)
    n2 = _iluminados(pg, "#bo-c3d")
    checar(u"[Bólus %s] e a vista padrão mantém o zoom" % rot, n2 > n0 * 1.2, (n0, n2))
    pg.click("#bo-cartao")
    pg.wait_for_timeout(500)
    pg.click("#bo-procurar")
    pg.wait_for_timeout(500)
    checar(u"[Bólus %s] «Procurar…» abre o explorador de pastas" % rot, pg.is_visible(".ui-fp"))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    _print(pg, u"bolus_%s_%s_%s" % (larg, idioma or u"pt", tema))


def teste_no_navegador(checar, secao, base_tmp):
    secao(u"o navegador: o Elastic e o bólus servidos e medidos (o Nidus, no test_nidus)")
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print(u"    PULADO o navegador: sem Playwright")
        return
    exe = _chromium()
    if not exe:
        print(u"    PULADO o navegador: sem Chromium")
        return
    base = os.path.join(base_tmp, "nav")
    os.makedirs(base, exist_ok=True)
    proc, root = _subir(base)
    checar(u"o vigia de teste subiu", proc is not None)
    if not proc:
        return
    erros = []
    try:
        with sync_playwright() as p:
            nav = p.chromium.launch(executable_path=exe, headless=True)
            for larg, idioma, tema in ((1280, u"", u"escuro"), (1600, u"", u"claro"),
                                       (1280, u"en", u"escuro"), (1600, u"en", u"claro")):
                ctx = nav.new_context(viewport={"width": larg, "height": 900})
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: erros.append(str(e)[:160]))
                pg.goto(BASE + "/aceite", wait_until="networkidle")
                if "/aceite" in pg.url:
                    pg.check("#ac_ok")
                    pg.click("#ac_bt")
                    pg.wait_for_timeout(1200)
                _ajustes(pg, idioma, tema)
                for passo in (lambda: _elastic(pg, checar, larg, idioma, tema, root),
                              lambda: _bolus(pg, checar, larg, idioma, tema, root)):
                    try:
                        passo()
                    except Exception as e:
                        checar(u"[%d %s] a tela foi medida até o fim" % (larg, idioma or u"pt"), False,
                               u"%s: %s" % (type(e).__name__, str(e).splitlines()[0][:200]))
                ctx.close()
            nav.close()
    finally:
        try:
            proc.kill()
        except Exception:
            pass
    checar(u"nenhum erro de JavaScript nas telas", not erros, u"; ".join(erros[:3]))


def main():
    for t in (teste_os_comentarios_de_antes_ficaram, teste_um_nome_so_para_a_projecao,
              teste_nidus_estrutura, teste_elastic_estrutura, teste_bolus_estrutura,
              teste_as_iscas,
              teste_as_frases_novas_tem_os_doze, teste_os_eixos_seguem_a_projecao,
              teste_a_caixa_recorta_a_projecao, teste_as_rotas,
              lambda: teste_no_navegador(checar, secao, _BASE_TMP)):
        try:
            t()
        except Exception:
            checar(u"%s rodou sem exceção" % getattr(t, "__name__", "t"), False,
                   traceback.format_exc()[-900:])
    ok = sum(1 for _n, c, _d in _R if c)
    falhou = len(_R) - ok
    print(u"\n" + u"=" * 68)
    if falhou:
        print(u"FALHOU: %d de %d checagens" % (falhou, len(_R)))
    else:
        print(u"OK: %d checagens, todas passaram" % ok)
    print(u"=" * 68)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
