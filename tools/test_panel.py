# -*- coding: utf-8 -*-
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))


def pasta_app(aqui):
    for c in (os.path.join(aqui, "..", "app"), os.path.join(aqui, "..")):
        if os.path.exists(os.path.join(c, "radai_watcher.py")):
            return os.path.abspath(c)
    return os.path.abspath(os.path.join(aqui, "..", "app"))


APP = pasta_app(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, APP)

VERBOSO = "-v" in sys.argv
_RESULTADOS = []
_TEMPS = []


def checar(nome, condicao, detalhe=""):
    ok = bool(condicao)
    _RESULTADOS.append((nome, ok, detalhe))
    if VERBOSO or not ok:
        print("  %s  %s%s" % ("OK   " if ok else "FALHA", nome,
                              ("  [%s]" % detalhe) if detalhe else ""))
    return ok


def secao(t):
    if VERBOSO:
        print("\n-- %s " % t + "-" * max(0, 58 - len(t)))


def porta_de_teste(preferida, quantas=12):
    import socket
    livre, ocupadas = None, []
    for p in range(int(preferida), int(preferida) + int(quantas)):
        s = socket.socket()
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            s.bind(("127.0.0.1", p))
            livre = p
            break
        except OSError:
            ocupadas.append(p)
        finally:
            s.close()
    if livre is None:
        raise RuntimeError(
            u"nenhuma porta livre entre %d e %d -- ha processo pendurado; "
            u"veja `netstat -ano | findstr %d`"
            % (preferida, preferida + quantas - 1, preferida))
    aviso = (u"" if not ocupadas else
             u"a porta %d estava OCUPADA (ha vigia pendurado de execucao "
             u"anterior); usando %d" % (ocupadas[0], livre))
    return livre, aviso


def novo_temp(prefixo="radai_p_"):
    d = tempfile.mkdtemp(prefix=prefixo)
    _TEMPS.append(d)
    return d


def novo_acervo():
    d = os.path.join(novo_temp(), "calibracao")
    os.environ["RADAI_CALIB_DIR"] = d
    return d


import radai_archive
import radai_config
import radai_panel
import _componentes


def reg(uid, **kw):
    dados = {"pasta": r"C:\fantasia\%s" % uid, "rs": "RS_RadAI_20260101_%s.dcm" % uid,
             "date": "20260101", "pid": "PAC_" + uid, "estruturas": 7, "secs": 60,
             "maquina": "PC_TESTE", "ver": "2.0"}
    dados.update(kw)
    return radai_archive.registrar_serie(uid=uid, **dados)


def teste_acervo_nasce_vazio():
    secao("acervo: instalação nova")
    novo_acervo()
    e = radai_archive.estado()
    checar("acervo novo nao existe em disco (nao criamos pasta a toa)", e["existe"] is False)
    checar("acervo novo tem zero series", e["series"] == 0)
    checar("acervo novo tem zero receitas", e["receitas"] == 0)
    checar("acervo novo tem zero versoes", e["versoes"] == 0)
    checar("acervo novo nao reporta erro", e["erro"] == "", e["erro"])
    checar("ler_acervo devolve lista vazia, nao None", radai_archive.ler_acervo() == [])


def teste_registrar_e_ler():
    secao("acervo: registrar e ler")
    novo_acervo()
    checar("registrar devolve True", reg("A") is True)
    reg("B")
    reg("C")
    regs = radai_archive.ler_acervo()
    checar("as tres series estao no acervo", len(regs) == 3, str(len(regs)))
    checar("a mais recente vem primeiro", [r["uid"] for r in regs] == ["C", "B", "A"],
           str([r["uid"] for r in regs]))
    checar("guarda a pasta para o calibrador reabrir a serie",
           regs[0]["pasta"].endswith("C"))
    checar("guarda o nome do RTSTRUCT", regs[0]["rs"].startswith("RS_RadAI_"))
    checar("carimba quando entrou", len(regs[0].get("quando", "")) >= 16, regs[0].get("quando"))
    checar("limite corta a lista", len(radai_archive.ler_acervo(limite=2)) == 2)
    checar("estado conta as series", radai_archive.estado()["series"] == 3)


def teste_serie_reprocessada_nao_duplica():
    secao("acervo: mesma serie duas vezes")
    novo_acervo()
    reg("X", estruturas=10)
    reg("X", estruturas=42)
    regs = radai_archive.ler_acervo()
    checar("serie reprocessada aparece uma vez so", len(regs) == 1, str(len(regs)))
    checar("o registro mais novo vence", regs and regs[0]["estruturas"] == 42,
           str(regs[0]["estruturas"]) if regs else "-")


def teste_linha_corrompida_nao_derruba():
    secao("acervo: linha truncada (queda de energia)")
    novo_acervo()
    reg("BOM1")
    with open(str(radai_archive.caminho_acervo()), "a", encoding="utf-8") as f:
        f.write('{"uid": "TRUNC", "past\n')
        f.write("\n")
    reg("BOM2")
    regs = radai_archive.ler_acervo()
    checar("lixo no meio do arquivo nao derruba a leitura", len(regs) == 2, str(len(regs)))
    checar("as series boas sobrevivem",
           sorted(r["uid"] for r in regs) == ["BOM1", "BOM2"])


def teste_registrar_nunca_levanta():
    secao("acervo: caminho impossivel")
    base = novo_temp()
    bloqueio = os.path.join(base, "bloqueio")
    with open(bloqueio, "w") as f:
        f.write("x")
    os.environ["RADAI_CALIB_DIR"] = os.path.join(bloqueio, "calibracao")
    try:
        r = reg("Y")
        ok = True
    except Exception as e:
        r, ok = None, False
        checar("registrar_serie levantou excecao", False, "%s: %s" % (type(e).__name__, e))
    if ok:
        checar("registrar_serie nao levanta com caminho impossivel", True)
        checar("registrar_serie devolve False quando nao consegue gravar", r is False, str(r))
    e = radai_archive.estado()
    checar("estado tambem sobrevive ao caminho impossivel", e["series"] == 0)


def teste_estado_conta_receitas_e_versoes():
    secao("acervo: receitas e versoes")
    novo_acervo()
    rec = radai_archive.pasta_receitas(criar=True)
    for nome in ("Parotid_L_ai", "Parotid_R_ai"):
        (rec / (nome + ".json")).write_text("{}", encoding="utf-8")
    ver = radai_archive.pasta_versoes(criar=True)
    for nome in ("v0001", "v0002"):
        (ver / (nome + ".json")).write_text("{}", encoding="utf-8")
    e = radai_archive.estado()
    checar("conta as receitas gravadas", e["receitas"] == 2, str(e["receitas"]))
    checar("conta as versoes compiladas", e["versoes"] == 2, str(e["versoes"]))
    checar("aponta a ultima versao", e["ultima_versao"] == "v0002", e["ultima_versao"])
    checar("a pasta existe depois de criada", e["existe"] is True)


def teste_estado_sem_vigia():
    secao("painel: estado sem o worker")
    novo_acervo()
    d = radai_panel.estado()
    for chave in ("versao_painel", "maquina", "vigia", "lote", "geom", "acervo"):
        checar("estado traz a chave %s" % chave, chave in d)
    for chave in ("calibrador", "compilador"):
        checar("estado NAO traz mais a chave %s" % chave, chave not in d)
    checar("sem worker, o cartao do vigia vem vazio (e nao inventado)", d["vigia"] == {})
    checar("maquina e preenchida", bool(d["maquina"]), str(d["maquina"]))


def teste_cartoes_refletem_o_que_existe():
    secao("painel: cartao reflete o que existe em disco")
    novo_acervo()
    d = radai_panel.estado()
    existe = radai_panel._tem_modulo("radai_batch")
    checar("lote: pronto acompanha o arquivo em disco",
           d["lote"]["pronto"] == (existe and not d["lote"]["falha"]),
           "arquivo=%s falha=%r" % (existe, d["lote"]["falha"]))
    checar("lote: o cartao aponta a tela", d["lote"]["url"] == "/lote",
           d["lote"]["url"])
    for modulo in ("radai_calibrator", "radai_compiler", "radai_crosscheck",
                   "radai_studio"):
        checar("%s nao esta mais ao lado do painel (v8.3)" % modulo,
               radai_panel._tem_modulo(modulo) is False)


def teste_cartao_liga_sozinho_quando_o_modulo_chegar():
    secao("painel: o cartao acende pela existencia do modulo")
    from pathlib import Path
    import importlib.util as _iu
    original = radai_panel.HERE
    find_spec_original = _iu.find_spec
    try:
        d = novo_temp()
        radai_panel.HERE = Path(d)

        def _find_spec(nome, *a, **k):
            if nome == "radai_batch" and not (Path(d) / "radai_batch.py").exists():
                return None
            return find_spec_original(nome, *a, **k)
        _iu.find_spec = _find_spec
        novo_acervo()
        checar("sem o arquivo, o cartao continua apagado",
               radai_panel.estado()["lote"]["pronto"] is False)
        (Path(d) / "radai_batch.py").write_text("# futuro", encoding="utf-8")
        checar("com o arquivo ao lado, o cartao acende sozinho",
               radai_panel.estado()["lote"]["pronto"] is True)
        (Path(d) / "radai_calibrator.py").write_text("# velho", encoding="utf-8")
        e = radai_panel.estado()
        checar("e um radai_calibrator.py VELHO ao lado nao reacende nada",
               "calibrador" not in e and "compilador" not in e, str(sorted(e)))
    finally:
        radai_panel.HERE = original
        _iu.find_spec = find_spec_original


def teste_estado_reflete_o_acervo():
    secao("painel: numero vem do disco")
    novo_acervo()
    d = radai_panel.estado()
    checar("acervo vazio -> zero series", d["acervo"]["series"] == 0)
    reg("S1")
    reg("S2")
    d = radai_panel.estado()
    checar("duas series registradas -> duas no acervo", d["acervo"]["series"] == 2,
           str(d["acervo"]["series"]))
    checar("o acervo sabe quando entrou a ultima", bool(d["acervo"]["ultima_serie"]))


def teste_vigia_que_explode_nao_derruba_o_painel():
    secao("painel: leitura do worker falhando")
    novo_acervo()

    def explode():
        raise RuntimeError("worker em chamas")

    try:
        d = radai_panel.estado(explode)
        checar("painel sobrevive a um worker que levanta", True)
        checar("e mostra o erro em vez de fingir que esta tudo bem",
               "chamas" in str(d["vigia"].get("erro", "")), str(d["vigia"]))
    except Exception as e:
        checar("painel sobrevive a um worker que levanta", False,
               "%s: %s" % (type(e).__name__, e))


def teste_geometria_carrega():
    secao("painel: biblioteca de geometria")
    g = radai_panel.estado_geom()
    checar("radai_geom carrega neste runtime", g["ok"] is True, g["erro"])
    checar("o painel expoe a versao da lib", bool(g["versao"]), str(g["versao"]))


def teste_pagina_tem_o_essencial():
    secao(u"a home e a mini-pagina do AutoContorno")
    import html as _html
    import radai_modules

    def plano(t):
        return u" ".join(_html.unescape(t).split()).lower()

    import re as _re
    import radai_porta
    h = radai_porta.pagina()
    hp = plano(_re.sub(r"<[^>]+>", u"", _re.sub(
        r"(?is)<(script|style)\b.*?</\1>", u"", h)))
    checar(u"a home diz que e ferramenta de apoio",
           u"ferramenta de apoio" in hp)
    checar(u"e que nao e validada para uso clinico",
           u"não validada para uso clínico" in hp)
    checar(u"e que toda estrutura sai como sugestao nao aprovada, uma vez",
           hp.count(u"sugestão não aprovada") == 1)
    import radai_menu as _rm
    _cartoes = h.count(u'class="ls-card tool-card"') \
        + h.count(u'class="ls-card tool-card ls-obra"')
    checar(u"a home tem uma linha por modulo",
           _cartoes >= len(_rm.MODULOS_HOME),
           u"%d cartoes para %d modulos" % (_cartoes, len(_rm.MODULOS_HOME)))
    checar(u"a home nao tem cartao de ferramenta",
           u'class="md-fer' not in h)
    checar(u"a home nao busca contagem no /api/painel",
           u"/api/painel" not in h)
    checar(u"e nao fica pedindo de tempos em tempos",
           u"setInterval" not in h)
    checar(u"a home nao tem portao embutido",
           u'id="portao"' not in h and u'id="cards_area"' not in h)

    p = radai_panel.pagina_inicial()
    pp = plano(p)
    checar(u"o marcador dos cartoes foi substituido", u"@CARDS@" not in p)
    checar(u"a mini-pagina diz que e material de estudo, 100% local",
           u"material de estudo" in pp and u"100% local" in pp)
    checar(u"e o `?` dela diz que nada e aprovado (UNAPPROVED)",
           u"unapproved" in pp)
    for rotulo in (u"O que não faz", u"Componentes de terceiros"):
        checar(u"a mini-pagina tem o balao `%s`" % rotulo, rotulo in p)
    checar(u"o balao diz que achado nao roda por omissao",
           any(m in pp for m in (u"por omissão", u"não vem ligada",
                                 u"ato declarado", u"escolha declarada")),
           u"o balao tem de responder «esta serie foi varrida procurando "
           u"achado?» sem o operador abrir o config")
    import radai_models as _mdl
    _reg = (getattr(_mdl, "MODELOS", None) or {})
    _faltam = [k for k, m in _reg.items()
               if (m.get("nome") or k).split(u" — ")[0].split(u" (")[0].lower() not in pp]
    checar(u"o balao lista TODO modelo do registro", not _faltam, str(_faltam))
    _nomes = u" ".join((m.get("nome") or u"").lower() for m in _reg.values())
    _so_texto = plano(_re.sub(r"<[^>]+>", u" ", p))
    checar(u"e nao anuncia componente fora do registro",
           (u"3.3" not in _so_texto)
           and (u"vista-3d" not in _so_texto or u"vista-3d" in _nomes),
           u"a clausula 3.3 saiu do pacote em 14/09/2026; o balao nao pode "
           u"continuar a declarando")
    import radai_modules as _MD
    _fers = _MD.FERRAMENTAS["autocontorno"]
    checar(u"a mini-pagina mostra exatamente as ferramentas declaradas",
           p.count(u'class="md-fer') == len(_fers),
           u"%d cartoes para %d declaradas" % (p.count(u'class="md-fer'),
                                               len(_fers)))
    for _f in _fers:
        checar(u"  e `%s` esta la" % _f[2],
               _f[2].lower() in plano(p), _f[2])
    for _fora, _rota in ((u"Calibrador", "/conferencia"),
                         (u"Compilador", "/compilador")):
        checar(u"  e o cartao `%s` nao esta mais aqui (foi para /config)" % _fora,
               (u'class="md-fer" href="%s"' % _rota) not in p, _rota)
    checar(u"a mini-pagina NAO oferece mais o cartao do vigia",
           u'class="md-fer" href="/vigia"' not in p)
    import radai_batch as _L
    checar(u"  e o cartao do estado NAO e mais link para /vigia",
           u'href="/vigia"' not in _L.PAGINA,
           u"`/vigia` redireciona para ca desde 21/09: um link daqui para la "
           u"e um clique que volta para onde ja se esta")
    import radai_todo as _todo
    _bar = _todo.barra()
    checar(u"  e a pergunta «o que esta maquina faz?» continua respondida",
           u'id="radai_fila_n"' in _bar and u'id="radai_pipe_est"' in _bar,
           u"o contador e o estado do pipeline vivem na barra da direita")
    checar(u"a mini-pagina busca o estado de verdade", u"/api/painel" in p)

    cfg = radai_panel.PAGINA_CONFIG
    for _rota, _rot in (("/conferencia", u"calibrador"),
                        ("/compilador", u"compilador")):
        checar(u"as configuracoes NAO levam mais ao %s" % _rot,
               (u'href="%s"' % _rota) not in cfg, _rota)
    checar(u"e ha o botao de atualizar o programa", u'id="lkAtu"' in cfg)
    checar(u"e o endereco dele vem de fora do codigo",
           u"@URL_VERSOES@" in cfg and u"drive.google.com" not in cfg)
    checar(u"e o subtitulo do cartao tem quem o preencha",
           u"@SUB_ATU@" in cfg)
    checar(u"e ele abre em outra aba, sem baixar nada",
           u'target="_blank"' in cfg and u'rel="noopener"' in cfg)
    checar(u"com caminho para os termos", u'href="/termos"' in cfg)
    checar(u"e para a politica de privacidade",
           u'href="/politica-privacidade"' in cfg)
    checar(u"e para os creditos de terceiros", u'href="/creditos"' in cfg)
    checar(u"e para a procedencia das estruturas",
           u'href="/procedencia"' in cfg)

    try:
        import radai_consent
        t = radai_consent.TERMOS
        tb = u" ".join(t.lower().split())
        checar(u"os TERMOS trazem a declaracao inteira",
               u"rascunho sujeito a revisão médica" in tb)
        checar(u"os TERMOS dizem que os modelos sao de terceiros",
               u"terceiros" in tb)
        checar(u"os TERMOS citam ApprovalStatus UNAPPROVED", u"UNAPPROVED" in t)
        checar(u"e que a revisao e ato medico",
               u"ato médico" in tb or u"ato medico" in tb)
    except Exception as e:
        checar(u"radai_consent importa", False, str(e)[:60])


CFG_CHATO = u"""# ─── Radioterapia.AI · Vigia de Auto-Contorno ───────────────────
# Pasta-raiz no servidor com as pastas dos pacientes.
# Preencha so depois de combinar com o TI.
ROOT=C:\\share\\pacientes

# Porta do painel local
PORT=8777 # comentario na mesma linha

  MIN_SLICES = 25

# chave que o vigia nao conhece
CHAVE_INVENTADA=x

OUT_DIR=
"""


def teste_leitura_do_config():
    secao("config: linhas chatas")
    v = radai_config.ler_bruto(CFG_CHATO)
    checar("le a chave normal", v.get("ROOT") == "C:\\share\\pacientes", repr(v.get("ROOT")))
    checar("mantem o comentario na mesma linha (quem trata isso e o vigia)",
           v.get("PORT") == "8777 # comentario na mesma linha", repr(v.get("PORT")))
    checar("aceita espaco em volta do =", v.get("MIN_SLICES") == "25", repr(v.get("MIN_SLICES")))
    checar("le valor vazio", v.get("OUT_DIR") == "", repr(v.get("OUT_DIR")))
    checar("le tambem a chave desconhecida (quem filtra e o vigia)",
           v.get("CHAVE_INVENTADA") == "x")
    checar("nao inventa chave a partir de comentario", len(v) == 5, str(sorted(v)))


_VIGIAS = [0]
_VIGIAS_CARREGADOS = []


def carregar_vigia(caminho_cfg, base, machine="PC_CFG"):
    import importlib.util
    _VIGIAS[0] += 1
    guardados = dict((k, os.environ.get(k))
                     for k in ("RADAI_CONFIG", "RADAI_MACHINE", "LOCALAPPDATA"))
    os.environ["RADAI_CONFIG"] = caminho_cfg
    os.environ["RADAI_MACHINE"] = machine
    os.environ["LOCALAPPDATA"] = os.path.join(base, "ad_%d" % _VIGIAS[0])
    try:
        spec = importlib.util.spec_from_file_location(
            "vigia_cfg_%d" % _VIGIAS[0], _componentes.fonte("app/radai_watcher.py"))
        mod = importlib.util.module_from_spec(spec)
        _VIGIAS_CARREGADOS.append(mod)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in guardados.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def teste_config_le_igual_ao_vigia():
    secao("config: a tela le exatamente o que o vigia carregou")
    base = novo_temp()
    caminho = os.path.join(base, "chato.config")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(CFG_CHATO)
    mod = carregar_vigia(caminho, base)

    do_arquivo = radai_config.ler_bruto(CFG_CHATO)
    divergentes = [k for k, v in do_arquivo.items()
                   if k in mod.DEFAULTS and str(mod.CFG[k]) != v]
    checar("radai_config le identico ao radai_watcher.load_cfg", not divergentes,
           str(divergentes))
    checar("o ROOT que a tela mostra e o que o vigia usa", mod.ROOT == do_arquivo["ROOT"],
           "%r vs %r" % (mod.ROOT, do_arquivo["ROOT"]))
    checar("o vigia ignora a chave que nao conhece", "CHAVE_INVENTADA" not in mod.CFG)
    checar("a tela oferece as mesmas chaves que o vigia aceita",
           "ROOT" in mod.DEFAULTS and "DRY_RUN" in mod.DEFAULTS and len(mod.DEFAULTS) >= 17,
           str(len(mod.DEFAULTS)))


def teste_bom_do_bloco_de_notas():
    secao("config: BOM do Bloco de Notas nao engole a primeira chave")
    base = novo_temp()
    caminho = os.path.join(base, "bom.config")
    alvo = os.path.join(base, "share")
    os.makedirs(alvo)
    with open(caminho, "w", encoding="utf-8-sig") as f:
        f.write("ROOT=%s\nDRY_RUN=1\nPORT=8799\n" % alvo)
    with open(caminho, "rb") as f:
        checar("o arquivo do teste tem mesmo BOM", f.read(3) == b"\xef\xbb\xbf")

    _, v = radai_config.ler_arquivo(caminho)
    checar("a tela le o ROOT apesar do BOM", v.get("ROOT") == alvo, str(sorted(v)))

    mod = carregar_vigia(caminho, base, machine="PC_BOM")
    checar("o vigia le o ROOT apesar do BOM", mod.ROOT == alvo, repr(mod.ROOT))
    checar("o vigia le a porta apesar do BOM", mod.PORT == 8799, str(mod.PORT))
    desconhecidas = [a for a in mod.AVISOS_CFG if "desconhecida" in a]
    checar("e nao reclama de chave desconhecida", not desconhecidas, str(desconhecidas))

    _ok, _erro = radai_config.escrever(caminho, {"DRY_RUN": "0"})
    checar("a tela conseguiu gravar o config", _ok, _erro)
    with open(caminho, "rb") as f:
        checar("salvar pela tela remove o BOM do arquivo", f.read(3) != b"\xef\xbb\xbf")


def teste_ajuda_vem_dos_comentarios():
    secao("config: a ajuda de cada campo sai do proprio arquivo")
    a = radai_config.comentarios(CFG_CHATO)
    checar("junta as linhas de comentario acima da chave",
           a.get("ROOT") == ("Pasta-raiz no servidor com as pastas dos pacientes. "
                             "Preencha so depois de combinar com o TI."), repr(a.get("ROOT")))
    checar("descarta a moldura de secao", "Radioterapia.AI" not in (a.get("ROOT") or ""))
    checar("cada chave pega o proprio bloco", a.get("PORT") == "Porta do painel local",
           repr(a.get("PORT")))
    checar("chave sem comentario fica sem ajuda", not a.get("MIN_SLICES"),
           repr(a.get("MIN_SLICES")))


def _config_temp():
    caminho = os.path.join(novo_temp(), "w.config")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(CFG_CHATO)
    return caminho


def teste_gravar_preserva_o_arquivo():
    secao("config: gravar preserva comentarios e o que nao foi pedido")
    caminho = _config_temp()
    ok, erro = radai_config.escrever(caminho, {"ROOT": "D:\\novo", "MIN_SLICES": "30"})
    checar("gravou", ok, erro)
    with open(caminho, encoding="utf-8") as f:
        novo = f.read()
    v = radai_config.ler_bruto(novo)
    checar("trocou o ROOT", v.get("ROOT") == "D:\\novo", repr(v.get("ROOT")))
    checar("trocou o MIN_SLICES", v.get("MIN_SLICES") == "30", repr(v.get("MIN_SLICES")))
    checar("nao mexeu na chave que nao foi pedida",
           v.get("PORT") == "8777 # comentario na mesma linha", repr(v.get("PORT")))
    checar("preservou os comentarios de ajuda",
           "Preencha so depois de combinar com o TI." in novo)
    checar("preservou a moldura das secoes", "───" in novo)
    linhas = [l for l in novo.splitlines() if l.strip().startswith("ROOT=")]
    checar("nao duplicou a chave", len(linhas) == 1, str(len(linhas)))

    ok, _ = radai_config.escrever(caminho, {"CHAVE_NOVA": "7"})
    with open(caminho, encoding="utf-8") as f:
        v2 = radai_config.ler_bruto(f.read())
    checar("chave ausente e acrescentada no fim", v2.get("CHAVE_NOVA") == "7")
    checar("e as antigas continuam la", v2.get("ROOT") == "D:\\novo")


def teste_gravar_recusa_quebra_de_linha():
    secao("config: valor com quebra de linha e recusado")
    caminho = _config_temp()
    with open(caminho, encoding="utf-8") as f:
        antes = f.read()
    ok, erro = radai_config.escrever(caminho, {"ROOT": "C:\\a\nDRY_RUN=1"})
    checar("recusa o valor", ok is False)
    checar("e diz por que", "quebra de linha" in erro, erro)
    with open(caminho, encoding="utf-8") as f:
        checar("nao encostou no arquivo", f.read() == antes)


def teste_validar_pasta():
    secao("config: laudo do caminho")
    v = radai_config.validar_pasta("")
    checar("caminho vazio nao e erro: e o padrao de fabrica",
           v["vazio"] is True and v["erro"] == "" and bool(v["aviso"]))
    v = radai_config.validar_pasta(os.path.join(novo_temp(), "nao_existe"))
    checar("pasta inexistente e apontada", v["existe"] is False and bool(v["erro"]))
    d = novo_temp()
    v = radai_config.validar_pasta(d)
    checar("pasta normal: existe, le e escreve",
           v["existe"] and v["leitura"] and v["escrita"], v["erro"])
    checar("o teste de escrita nao deixa lixo para tras",
           not [x for x in os.listdir(d) if "_radai_teste" in x], str(os.listdir(d)))


def teste_validar_pasta_sem_escrita():
    secao("config: share que le mas nao escreve")
    if os.name != "nt":
        checar("teste de somente-leitura (so no Windows)", True, "pulado")
        return
    d = novo_temp()
    user = os.environ.get("USERNAME", "")
    os.system('icacls "%s" /deny "%s":(WD) >nul 2>&1' % (d, user))
    try:
        v = radai_config.validar_pasta(d)
        checar("detecta que da para ler mas nao para escrever",
               v["leitura"] is True and v["escrita"] is False, v["erro"])
        checar("e explica que sem escrita nenhuma serie e processada",
               "_RadAI" in v["erro"] and "nenhuma serie" in v["erro"], v["erro"])
    finally:
        os.system('icacls "%s" /remove:d "%s" >nul 2>&1' % (d, user))


def teste_divergencia_pede_reinicio():
    secao("config: aviso de reiniciar o vigia")
    caminho = os.path.join(novo_temp(), "d.config")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("ROOT=C:\\a\nPORT=8777\n")
    cfg = {"caminho": caminho, "em_uso": {"ROOT": "C:\\a", "PORT": "8777"}}
    checar("sem mudanca, nada a avisar", radai_panel.divergencias(cfg) == [],
           str(radai_panel.divergencias(cfg)))
    _ok, _erro = radai_config.escrever(caminho, {"ROOT": "C:\\b"})
    checar("a tela conseguiu gravar o config", _ok, _erro)
    checar("mudanca no arquivo vira divergencia",
           radai_panel.divergencias(cfg) == ["ROOT"], str(radai_panel.divergencias(cfg)))
    checar("config ausente nao quebra a leitura",
           radai_panel.divergencias({"caminho": "Z:\\nao\\existe", "em_uso": {"ROOT": "x"}}) == [])
    checar("sem config, nada a avisar", radai_panel.divergencias(None) == [])


def teste_listar_pastas():
    secao("config: navegador de pastas")
    base = novo_temp()
    os.makedirs(os.path.join(base, "PAC_A", "CT"))
    os.makedirs(os.path.join(base, "PAC_B"))
    with open(os.path.join(base, "IM0001.dcm"), "w") as f:
        f.write("x")

    d = radai_config.listar_pastas(base)
    nomes = sorted(p["nome"] for p in d["pastas"])
    checar("lista as subpastas", nomes == ["PAC_A", "PAC_B"], str(nomes))
    checar("NAO lista arquivos (nome de DICOM nao vai para a tela)",
           "IM0001.dcm" not in nomes)
    checar("devolve o caminho completo de cada subpasta",
           all(os.path.isdir(p["caminho"]) for p in d["pastas"]))
    checar("oferece subir um nivel", d["pai"] == os.path.dirname(base), d["pai"])
    checar("nao reporta erro", d["erro"] == "", d["erro"])

    dentro = radai_config.listar_pastas(os.path.join(base, "PAC_A"))
    checar("navega para dentro", [p["nome"] for p in dentro["pastas"]] == ["CT"],
           str(dentro["pastas"]))

    vazio = radai_config.listar_pastas("")
    checar("caminho vazio devolve as unidades da maquina", len(vazio["unidades"]) >= 1,
           str(vazio["unidades"]))
    checar("e nao inventa pasta nenhuma", vazio["pastas"] == [])

    ruim = radai_config.listar_pastas(os.path.join(base, "nao_existe"))
    checar("caminho invalido e apontado sem levantar", bool(ruim["erro"]), ruim["erro"])
    checar("e ainda oferece as unidades para recomecar", len(ruim["unidades"]) >= 1)


def teste_porta_so_vale_reabrindo():
    secao("config: PORT fica de fora da recarga a quente")
    caminho = os.path.join(novo_temp(), "p.config")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("ROOT=C:\\a\nPORT=8777\n")
    cfg = {"caminho": caminho, "em_uso": {"ROOT": "C:\\a", "PORT": "8777"},
           "arranque": {"PORT": "8777"}, "so_no_arranque": ["PORT"]}
    checar("porta igual: nada a avisar", radai_panel.so_reabrindo(cfg) == [],
           str(radai_panel.so_reabrindo(cfg)))
    _ok, _erro = radai_config.escrever(caminho, {"PORT": "9001"})
    checar("a tela conseguiu gravar o config", _ok, _erro)
    checar("porta mudada exige reabrir o programa",
           radai_panel.so_reabrindo(cfg) == ["PORT"], str(radai_panel.so_reabrindo(cfg)))
    checar("e NAO e oferecida como recarregavel a quente",
           "PORT" not in radai_panel.divergencias(cfg),
           str(radai_panel.divergencias(cfg)))
    checar("comentario na mesma linha nao vira falsa divergencia de porta",
           radai_panel.so_reabrindo(
               {"caminho": caminho, "arranque": {"PORT": "9001"}}) == [])


def teste_aviso_some_depois_da_recarga():
    secao("config: o aviso some sozinho depois da recarga")
    caminho = os.path.join(novo_temp(), "e.config")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("ROOT=C:\\a\n")
    vivo = {"ROOT": "C:\\a"}
    cfg = {"caminho": caminho, "em_uso": lambda: vivo}
    _ok, _erro = radai_config.escrever(caminho, {"ROOT": "C:\\b"})
    checar("a tela conseguiu gravar o config", _ok, _erro)
    checar("antes da recarga o aviso aparece",
           radai_panel.divergencias(cfg) == ["ROOT"], str(radai_panel.divergencias(cfg)))
    vivo["ROOT"] = "C:\\b"
    checar("depois da recarga o aviso some",
           radai_panel.divergencias(cfg) == [], str(radai_panel.divergencias(cfg)))
    checar("em_uso que levanta nao derruba o painel",
           radai_panel.divergencias({"caminho": caminho,
                                      "em_uso": lambda: 1 / 0}) == [])


def teste_pagina_de_config_tem_o_essencial():
    secao("config: conteudo da tela")
    p = radai_panel.PAGINA_CONFIG
    checar("a tela diz qual arquivo edita (o caminho vem de /api/config)",
           "el('arq').textContent=d.caminho" in p and 'id="arq"' in p)
    import re as _re
    _aviso = p[p.index('<div class="aviso"'):]
    _aviso = _aviso[:_aviso.index("</div>")]
    _aviso = _re.sub(r"(?s)<!--.*?-->", u"", _aviso)
    checar("a tela avisa que salvar nao aplica sozinho, e aponta o botao",
           "Reiniciar agora" in _aviso, _aviso[-160:])
    checar("  e nao manda fechar a janela",
           "feche a janela" not in _aviso.lower(), _aviso[-160:])
    checar("a tela NAO tem mais o seletor de pasta do ROOT",
           "Testar este caminho" not in p and "fpAbrir" not in p
           and 'id="fpicker"' not in p)
    checar("a tela tem o botao de reiniciar agora", "Reiniciar agora" in p)
    checar("a tela volta para o inicio", 'href="/"' in p)
    checar("a landing tem o botao de configuracoes", 'href="/config"' in radai_panel.pagina_inicial())
    checar("a landing tem o botao de reiniciar agora",
           "Reiniciar agora" in radai_panel.pagina_inicial())


def teste_config_tem_as_acoes_no_topo():
    secao("config: salvar e faixa de recarga no topo fixo")
    p = radai_panel.PAGINA_CONFIG
    topo = p.split('<div class="topo">')[-1].split("</div>\n\n<div")[0]
    checar("existe um bloco de topo", '<div class="topo">' in p)
    checar("o topo e fixo na rolagem", "position:sticky" in p)
    checar("o botao Salvar esta DENTRO do topo", 'id="btsalvar"' in topo,
           topo[:200])
    checar("o Reiniciar agora tambem", 'id="btrei_cfg"' in topo)
    checar("e a faixa de recarga tambem", 'id="faixa"' in topo)
    checar("nao sobrou barra de acoes no rodape",
           p.count('id="btsalvar"') == 1 and '<div class="barra">\n <button class="pri"' not in p)
    checar("salvar responde na faixa, nao so no <span>",
           "faixa('Gravado no arquivo" in p)
    checar("a faixa diz que o vigia ainda usa os valores antigos",
           "ainda usa os valores antigos" in p)
    checar("e a recarga bem-sucedida pinta a faixa de verde",
           ".faixa.ok{" in p and "'ok'" in p)
    checar("carregar(manter) nao redeclara a funcao faixa",
           "var pintar = manter" in p and "if(manter) var faixa" not in p)


def aceitar_no_acervo(acervo):
    import radai_consent as CS
    os.makedirs(acervo, exist_ok=True)
    reg = CS.montar_registro(u"bateria", [k for k, _t, _d in CS.PONTOS])
    reg["maquina"] = "PC_TESTE"
    with open(os.path.join(acervo, CS.ARQUIVO_ACEITE), "w",
              encoding="utf-8") as f:
        json.dump(reg, f)


def conferir_portao(pegar, rotas):
    for rota in rotas:
        try:
            corpo = pegar(rota)
        except Exception as e:
            corpo = "ERRO %s" % e
        checar(u"sem aceite, `%s` cai no /aceite" % rota,
               u'id="ac_ok"' in corpo, corpo[:70])
    try:
        d = json.loads(pegar("/api/painel"))
    except Exception as e:
        d = None
        checar(u"sem aceite, a API do vigia continua respondendo", False, str(e)[:60])
    if d is not None:
        checar(u"sem aceite, a API do vigia continua respondendo", True)



def teste_landing_no_ar():
    secao("ponta a ponta: landing, painel do worker e DRY_RUN")
    import subprocess
    import urllib.request
    sys.path.insert(0, AQUI)
    from make_test_series import escreve_serie

    base = novo_temp()
    root = os.path.join(base, "share")
    escreve_serie(os.path.join(root, "PAC_L", "CT"), "PAC_L",
                  datetime.now() - timedelta(days=1), 8)
    acervo = os.path.join(base, "calibracao")
    porta, _aviso_porta = porta_de_teste(8791)
    if _aviso_porta:
        print(u"  AVISO  %s" % _aviso_porta)
    cfg = os.path.join(base, "landing.config")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("ROOT=%s\nDRY_RUN=1\nMIN_SLICES=5\nQUIET_MIN=0\nTPS_DESTINO=eclipse\nPORT=%d\nLOG_DIR=%s\n"
                % (root, porta, os.path.join(base, "log")))
    env = dict(os.environ, RADAI_CONFIG=cfg, RADAI_MACHINE="PC_LANDING",
               RADAI_CALIB_DIR=acervo, LOCALAPPDATA=os.path.join(base, "ad"),
               RADAI_REGISTRO_DIR=os.path.join(base, "registro"),
               PYTHONIOENCODING="utf-8:replace")
    proc = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def pegar(caminho):
        return urllib.request.urlopen("http://127.0.0.1:%d%s" % (porta, caminho),
                                      timeout=2).read().decode("utf-8", "replace")

    def _ligar_a_fila():
        for _ in range(60):
            try:
                urllib.request.urlopen(urllib.request.Request(
                    "http://127.0.0.1:%d/api/vigia/ligar" % porta,
                    data=b"", method="POST"), timeout=2).read()
                return True
            except Exception:
                time.sleep(0.5)
        return False

    try:
        pronto = False
        for _ in range(60):
            try:
                pegar("/api/painel")
                pronto = True
                break
            except Exception:
                time.sleep(0.5)
        checar(u"o vigia do teste subiu", pronto)
        if pronto:
            conferir_portao(pegar, ("/", "/lote", "/autocontorno"))
        aceitar_no_acervo(acervo)

        landing, vigia, dados = "", "", None
        for _ in range(60):
            try:
                landing = pegar("/")
                vigia = pegar("/lote")
                dados = json.loads(pegar("/api/painel"))
                if (dados.get("vigia") or {}).get("done_today"):
                    break
            except Exception:
                pass
            time.sleep(0.5)

        import radai_modules as _M
        nomes = [(_M.MODULOS[k]["titulo"] + _M.MODULOS[k]["destaque"])
                 for k in ("autocontorno", "bridge")]
        checar("com aceite, a raiz e a home dos modulos",
               all(n in landing for n in nomes),
               u"procurei %s · %s" % (nomes, landing[:60]))
        checar("a home avisa que nao e validada para uso clinico",
               "validada para uso cl" in landing.lower())
        checar("a tela do pipeline responde", bool(vigia) and len(vigia) > 4000,
               str(len(vigia or "")))
        checar("  e ela monta a fila E controla o processamento",
               "btrodar" in vigia and "radai_pipe_ini" in vigia,
               "o passo 2 enfileira; o controle acima da barra roda")
        checar("  e o «Iniciar» passa pela conferencia",
               "/api/pipeline/revisao" in vigia
               and "radaiRevAbrir" in vigia
               and "radai_rev_corpo" in vigia,
               "o dialogo esta costurado mas ninguem o abre")
        _js = vigia[vigia.index("function radaiPipe("):] if \
            "function radaiPipe(" in vigia else ""
        _jan = _js[:900]

        def _corpo_do_catch(js):
            i = js.find(".catch(")
            if i < 0:
                return u""
            abre = i + len(".catch")
            prof = 0
            for k in range(abre, len(js)):
                if js[k] == "(":
                    prof += 1
                elif js[k] == ")":
                    prof -= 1
                    if prof == 0:
                        return js[abre + 1:k]
            return u""

        checar("  e sem o dialogo ele comeca assim mesmo",
               "typeof radaiRevAbrir === 'function'" in _jan,
               "sem a guarda, o trilho chama um dialogo que so existe em /lote")
        checar("  e sem rede tambem",
               "radaiPipeMandar" in _corpo_do_catch(_jan),
               "revisao virou portao: um `fetch` que falha impede o lote")
        import radai_phrases as _fr
        _linha = [l for l in _fr.TABELA if l[0] == u"Fila de estudo"]
        checar("  e `Fila de estudo` esta no dicionario", len(_linha) == 1)
        checar("  com `Study Queue` no ingles",
               bool(_linha) and _linha[0][1] == u"Study Queue",
               u"e o nome internacional do produto")
        checar("e o painel do worker tem como voltar para a home",
               'href="/"' in vigia)
        checar("/api/painel responde", dados is not None)
        if dados is None:
            return
        checar("a rota de ligar a fila respondeu", _ligar_a_fila())
        for _ in range(60):
            try:
                dados = json.loads(pegar("/api/painel"))
                if (dados.get("vigia") or {}).get("done_today"):
                    break
            except Exception:
                pass
            time.sleep(0.5)
        v = dados.get("vigia") or {}
        checar("o cartao do vigia le o estado real do worker", v.get("versao") is not None,
               str(v.get("versao")))
        checar("o cartao do vigia sabe que esta em simulacao", v.get("dry_run") is True)
        checar("o vigia processou a serie com a landing no ar", v.get("done_today") == 1,
               str(v.get("done_today")))
        checar("o estado nao traz mais o calibrador nem o compilador",
               "calibrador" not in dados and "compilador" not in dados,
               str(sorted(dados)))
        _rotas = set(getattr(r, "path", "") for r in
                     _app_do_painel(os.path.join(novo_temp(), "t.config")).routes)
        checar("o app do painel tem rotas (a medida leu algo)", len(_rotas) > 20,
               str(len(_rotas)))
        for rota in ("/calibrador", "/conferencia", "/compilador"):
            checar("a rota %s nao existe mais no app que o painel monta" % rota,
                   rota not in _rotas)
        checar("serie em DRY_RUN NAO entra no acervo",
               dados["acervo"]["series"] == 0, str(dados["acervo"]["series"]))
        checar("e o arquivo do acervo nem chega a ser criado",
               not os.path.exists(os.path.join(acervo, "acervo.jsonl")))
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=15)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def teste_tela_de_config_no_ar():
    secao("ponta a ponta: salvar configuracao pela tela")
    import subprocess
    import urllib.request

    base = novo_temp()
    porta, _aviso_porta = porta_de_teste(8792)
    if _aviso_porta:
        print(u"  AVISO  %s" % _aviso_porta)
    cfg = os.path.join(base, "tela.config")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("# Pasta-raiz no servidor.\n# Preencha so depois de combinar com o TI.\n"
                "ROOT=\nDRY_RUN=1\nMIN_SLICES=5\nQUIET_MIN=0\nTPS_DESTINO=eclipse\nPORT=%d\nLOG_DIR=%s\n"
                % (porta, os.path.join(base, "log")))
    env = dict(os.environ, RADAI_CONFIG=cfg, RADAI_MACHINE="PC_TELA",
               RADAI_CALIB_DIR=os.path.join(base, "calibracao"),
               RADAI_REGISTRO_DIR=os.path.join(base, "registro"),
               LOCALAPPDATA=os.path.join(base, "ad"), PYTHONIOENCODING="utf-8:replace")
    proc = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def pegar(caminho):
        return urllib.request.urlopen("http://127.0.0.1:%d%s" % (porta, caminho),
                                      timeout=3).read().decode("utf-8", "replace")

    def postar(caminho, corpo):
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (porta, caminho),
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        return json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))

    alvo = os.path.join(base, "share_novo")
    os.makedirs(alvo)
    try:
        pronto = False
        for _ in range(60):
            try:
                pegar("/api/config")
                pronto = True
                break
            except Exception:
                time.sleep(0.5)
        checar(u"o vigia do teste subiu", pronto)
        if pronto:
            conferir_portao(pegar, ("/config",))
        aceitar_no_acervo(os.path.join(base, "calibracao"))

        tela, api = "", None
        for _ in range(60):
            try:
                tela = pegar("/config")
                api = json.loads(pegar("/api/config"))
                break
            except Exception:
                pass
            time.sleep(0.5)

        checar("a tela de configuracoes responde em /config",
               bool(tela) and "Configura" in tela)
        checar("/api/config responde", api is not None)
        if api is None:
            return
        checar("a API aponta o arquivo que edita", api["caminho"] == cfg, api["caminho"])
        checar("a API oferece as chaves do vigia",
               "ROOT" in api["chaves"] and "DEVICE" in api["chaves"],
               str(len(api["chaves"])))
        checar("  e nao oferece as que so se editam no arquivo",
               not (set(radai_panel.FORA_DA_TELA) & set(api["chaves"])),
               str(sorted(set(radai_panel.FORA_DA_TELA) & set(api["chaves"]))))
        checar("a API traz a ajuda tirada dos comentarios",
               "combinar com o TI" in (api["ajuda"].get("ROOT") or ""),
               repr(api["ajuda"].get("ROOT")))
        checar("a API marca a configuracao como editavel", api["editavel"] is True)

        r = postar("/api/config", {"valores": {"ROOT": alvo}, "confirmar_root": False})
        checar("mudar o ROOT exige confirmacao", r.get("precisa_confirmar") is True, str(r))
        checar("a confirmacao vem com o laudo do caminho",
               (r.get("validacao") or {}).get("escrita") is True, str(r.get("validacao")))
        checar("a confirmacao mostra o antes e o depois",
               r.get("root_atual") == "" and r.get("root_novo") == alvo, str(r))
        with open(cfg, encoding="utf-8") as f:
            checar("e o arquivo continua intocado",
                   radai_config.ler_bruto(f.read()).get("ROOT") == "")

        r = postar("/api/config", {"valores": {"ROOT": alvo}, "confirmar_root": True})
        checar("confirmado, grava", r.get("ok") is True, str(r))
        checar("e avisa que precisa reiniciar", r.get("reiniciar") is True)
        with open(cfg, encoding="utf-8") as f:
            texto = f.read()
        checar("o ROOT novo esta no arquivo",
               radai_config.ler_bruto(texto).get("ROOT") == alvo)
        checar("os comentarios sobreviveram a gravacao pela tela",
               "combinar com o TI" in texto)

        postar("/api/config", {"valores": {"CHAVE_PIRATA": "1"}, "confirmar_root": True})
        with open(cfg, encoding="utf-8") as f:
            checar("chave desconhecida enviada pela tela e ignorada",
                   "CHAVE_PIRATA" not in f.read())
        postar("/api/config", {"valores": {"SUAVIZAR_MM": "3.5", "DRY_RUN": "0"},
                               "confirmar_root": True})
        with open(cfg, encoding="utf-8") as f:
            _v = radai_config.ler_bruto(f.read())
        checar("SUAVIZAR_MM mandado a rota nao chega ao arquivo",
               "SUAVIZAR_MM" not in _v, repr(_v.get("SUAVIZAR_MM")))
        checar("  nem o DRY_RUN", _v.get("DRY_RUN") == "1", repr(_v.get("DRY_RUN")))

        painel = json.loads(pegar("/api/painel"))
        checar("a landing avisa que a configuracao mudou depois do arranque",
               "ROOT" in (painel.get("config_mudou") or []), str(painel.get("config_mudou")))
        checar("o cartao do vigia ainda mostra o estado antigo (nao aplicou sozinho)",
               (painel.get("vigia") or {}).get("root") == "",
               repr((painel.get("vigia") or {}).get("root")))
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=15)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def teste_reiniciar_aplica_sem_fechar_o_programa():
    secao("ponta a ponta: Reiniciar agora aplica de verdade")
    import subprocess
    import urllib.parse
    import urllib.request
    from make_test_series import escreve_serie

    base = novo_temp()
    porta, _aviso_porta = porta_de_teste(8793)
    if _aviso_porta:
        print(u"  AVISO  %s" % _aviso_porta)
    alvo = os.path.join(base, "share")
    escreve_serie(os.path.join(alvo, "PAC_R", "CT"), "PAC_R",
                  datetime.now() - timedelta(days=1), 8)
    cfg = os.path.join(base, "rec.config")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("ROOT=\nDRY_RUN=1\nMIN_SLICES=5\nQUIET_MIN=0\nSCAN_EVERY_MIN=1\n"
                "PORT=%d\nLOG_DIR=%s\n" % (porta, os.path.join(base, "log")))
    env = dict(os.environ, RADAI_CONFIG=cfg, RADAI_MACHINE="PC_REC",
               RADAI_CALIB_DIR=os.path.join(base, "calibracao"),
               RADAI_REGISTRO_DIR=os.path.join(base, "registro"),
               LOCALAPPDATA=os.path.join(base, "ad"), PYTHONIOENCODING="utf-8:replace")
    proc = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def pegar(caminho):
        return urllib.request.urlopen("http://127.0.0.1:%d%s" % (porta, caminho),
                                      timeout=3).read().decode("utf-8", "replace")

    def postar(caminho, corpo):
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (porta, caminho),
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        return json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))

    def painel():
        return json.loads(pegar("/api/painel"))

    def esperar(cond, voltas=90):
        for _ in range(voltas):
            try:
                if cond(painel()):
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    try:
        no_ar = esperar(lambda p: p.get("vigia") is not None, 60)
        checar("o vigia subiu", no_ar)
        if not no_ar:
            return
        checar("subiu inerte, sem ROOT", (painel().get("vigia") or {}).get("root") == "")

        pastas = postar("/api/pastas", {"caminho": alvo})
        checar("/api/pastas lista o paciente da pasta nova",
               [p["nome"] for p in pastas["pastas"]] == ["PAC_R"], str(pastas["pastas"]))

        r = postar("/api/config", {"valores": {"ROOT": alvo}, "confirmar_root": True})
        checar("gravou o ROOT novo", r.get("ok") is True, str(r))
        checar("a landing avisa que ha configuracao pendente",
               "ROOT" in (painel().get("config_mudou") or []))
        checar("e oferece a recarga", painel().get("pode_recarregar") is True)

        pid_antes = proc.pid
        rr = postar("/api/reiniciar", {})
        checar("a recarga foi aceita", rr.get("ok") is True, str(rr))

        aplicou = esperar(lambda p: (p.get("vigia") or {}).get("root") == alvo)
        checar("o vigia passou a usar o ROOT novo", aplicou,
               repr((painel().get("vigia") or {}).get("root")))
        checar("sem fechar o programa: e o mesmo processo",
               proc.poll() is None and proc.pid == pid_antes)
        checar("e o aviso de configuracao pendente some sozinho",
               "ROOT" not in (painel().get("config_mudou") or []),
               str(painel().get("config_mudou")))
        checar("a recarga fica registrada para o operador ver",
               "aplicada" in ((painel().get("vigia") or {}).get("recarga") or ""),
               repr((painel().get("vigia") or {}).get("recarga")))

        for _ in range(60):
            try:
                urllib.request.urlopen(urllib.request.Request(
                    "http://127.0.0.1:%d/api/vigia/ligar" % porta,
                    data=b"", method="POST"), timeout=2).read()
                break
            except Exception:
                time.sleep(0.5)
        processou = esperar(lambda p: ((p.get("vigia") or {}).get("done_today") or 0) >= 1)
        checar("e passou a processar a serie da pasta nova, sem reiniciar nada",
               processou, str((painel().get("vigia") or {}).get("done_today")))
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=15)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def teste_a_tela_do_vigia_fala_a_lingua_da_rota():
    secao("vigia: o passo 1 grava mesmo (a trava do ROOT e cumprida)")
    import re
    import radai_watcher

    pagina = radai_watcher.PAGE

    import inspect
    fonte_rota = inspect.getsource(radai_panel)
    checar("a rota ainda exige confirmacao para trocar o ROOT",
           "precisa_confirmar" in fonte_rota and "confirmar_root" in fonte_rota)

    chamadas = [pagina[i:i + 400]
                for i in range(len(pagina))
                if pagina.startswith("fetch('/api/config'", i)]
    checar("a pagina do vigia fala com /api/config", len(chamadas) >= 1,
           str(len(chamadas)))
    sem_chave = [c for c in chamadas
                 if "ROOT:" in c and "confirmar_root" not in c]
    checar("nenhum POST de ROOT sai sem confirmar_root", not sem_chave,
           (sem_chave[0][:120] + "...") if sem_chave else "")

    checar("a tela pergunta antes de mandar a chave", "confirm(" in pagina)
    for pedaco, rotulo in (("root_atual", "o caminho de antes"),
                           ("root_novo", "o caminho de depois"),
                           ("existe", "se a pasta existe"),
                           ("escrita", "se a pasta aceita escrita")):
        checar("a confirmacao mostra %s" % rotulo, pedaco in pagina)


def teste_o_vigia_grava_o_root_pela_pagina():
    secao("vigia: ponta a ponta, com o corpo que a pagina monta")
    import json as _json
    import re
    import subprocess
    import urllib.request
    import radai_watcher

    m = re.search(r"body:JSON\.stringify\(\{valores:\{ROOT:v\}([^}]*)\}\)",
                  radai_watcher.PAGE)
    checar("achei na pagina o corpo do POST que grava o ROOT", m is not None)
    if not m:
        return
    manda_a_chave = "confirmar_root" in m.group(1)

    base = novo_temp()
    porta, _aviso_porta = porta_de_teste(8795)
    if _aviso_porta:
        print(u"  AVISO  %s" % _aviso_porta)
    alvo = os.path.join(base, "share")
    os.makedirs(alvo)
    cfg = os.path.join(base, "p.config")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("ROOT=\nDRY_RUN=1\nQUIET_MIN=0\nSCAN_EVERY_MIN=99\n"
                "PORT=%d\nLOG_DIR=%s\n" % (porta, os.path.join(base, "log")))
    env = dict(os.environ, RADAI_CONFIG=cfg, RADAI_MACHINE="PC_P",
               RADAI_CALIB_DIR=os.path.join(base, "calibracao"),
               RADAI_REGISTRO_DIR=os.path.join(base, "registro"),
               LOCALAPPDATA=os.path.join(base, "ad"),
               PYTHONIOENCODING="utf-8:replace")
    proc = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                            env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT)

    def postar(corpo):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/config" % porta,
            data=_json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        return _json.loads(urllib.request.urlopen(req, timeout=20).read()
                           .decode("utf-8"))

    try:
        subiu = False
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/api/painel" % porta,
                                       timeout=3).read()
                subiu = True
                break
            except Exception:
                time.sleep(0.5)
        checar("o vigia subiu", subiu)
        checar("  e quem responde na porta e o vigia deste teste",
               proc.poll() is None, u"o processo saiu com %s" % proc.poll())
        if not subiu or proc.poll() is not None:
            return

        r = postar({"valores": {"ROOT": alvo}})
        checar("sem confirmar_root a rota recusa (a trava vale)",
               r.get("precisa_confirmar") is True, str(r)[:150])

        r = postar({"valores": {"ROOT": alvo}, "confirmar_root": manda_a_chave})
        checar("com o corpo da pagina, o ROOT e gravado", r.get("ok") is True,
               str(r)[:150])
        with open(cfg, encoding="utf-8-sig") as f:
            checar("e o arquivo passou a apontar para a pasta nova",
                   ("ROOT=%s" % alvo) in f.read())
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=15)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def teste_a_porta_e_so_a_porta():
    secao(u"a porta: um cartao por modulo, e nada mais")
    import radai_router
    p = radai_router.pagina()

    import radai_menu as _rm
    import radai_breadcrumb as _rt
    linhas = p.count(u'class="ls-card tool-card"') \
        + p.count(u'class="ls-card tool-card ls-obra"')
    checar(u"tem uma linha por modulo da home",
           linhas >= len(_rm.MODULOS_HOME),
           u"%d para %d" % (linhas, len(_rm.MODULOS_HOME)))
    import radai_modules as _md
    for _m in _rm.MODULOS_HOME:
        rota = (_rt.ARVORE.get(_m) or (None, "", None))[1]
        _est = (_md.MODULOS.get(_m) or {}).get("estado") or u""
        _em_obra = _md.nao_navega(_est)
        _leva = bool(rota) and rota != "/" and (u'href="%s"' % rota) in p
        _anuncia = _em_obra and _est in p
        checar(u"e uma delas leva a `%s` (ou diz que nao abriu)" % rota,
               _leva or _anuncia,
               u"%s -> rota=%s obra=%s anuncia=%s"
               % (_m, rota, _em_obra, _anuncia))

    for f in (u"Rodar agora", u"Ver segmenta", u"Calibrador", u"Compilador",
              u"Bibliografia"):
        checar(u"a porta NAO lista `%s`" % f[:14], f not in p,
               u"ferramenta na porta")
    checar(u"nem o cartao velho (a classe rt-mod)", u'class="rt-mod' not in p)

    checar(u"nenhum temporizador na porta", u"setInterval" not in p,
           u"porta nao tem painel")
    checar(u"nem pastilha de estado", u'class="est' not in p)
    checar(u"nem o portao embutido", u'id="portao"' not in p)

    checar(u"o Torax nao esta na porta",
           u"/torax" not in p and u"or\\u00e1cica" not in p)

    # GUARDA: a linha da porta é só a da não-validação clínica.
    checar(u"a linha clinica continua VISIVEL",
           u"validada para uso cl" in p,
           u"nao pode depender de qual tela se atravessou")
    _rod = p.split(u'<footer class="ls-rodape">')[-1].split(u"</footer>")[0]
    checar(u"e ela esta no rodape, fora de qualquer balao",
           u"validada para uso cl" in _rod and u"ui-balao" not in _rod
           and u"title=" not in _rod)
    checar(u"o rodape da porta nao tem `?`",
           _rod.count(u"ui-ajuda") == 0, str(_rod.count(u"ui-ajuda")))
    checar(u"  e ele tem a fronteira e a autoria",
           u"Henrique Braga" in _rod and u"sugest" in _rod)
    checar(u"  e mais nada alem delas",
           u"md-clin" not in _rod and u"ui-balao" not in _rod
           and _rod.count(u"<p") == 1)
    import radai_modules as _md2
    _sem = [c for c in _rm.MODULOS_HOME if not _md2.AJUDA.get(c)]
    checar(u"toda mini-pagina de modulo tem texto de balao", not _sem, str(_sem))
    checar(u"  e o `?` dela sai de balao_da_home",
           all(_md2.ajuda_do_modulo(c) == _md2.balao_da_home(c)
               for c in _rm.MODULOS_HOME))
    _sem_an = [a["chave"] for a in _md2.ANUNCIOS if not _md2.AJUDA.get(a["chave"])]
    checar(u"todo anuncio tem texto de balao", not _sem_an, str(_sem_an))
    checar(u"  (e o mecanismo de anuncio continua existindo)",
           isinstance(_md2.ANUNCIOS, (tuple, list)),
           u"com a tupla vazia o laco acima nao mede nada; o que resta medir "
           u"e' que a estrutura nao foi apagada junto com o ultimo anuncio")
    _fant = [{"chave": "xpto_sem_balao"}]
    _ruim = [a["chave"] for a in _fant if not _md2.AJUDA.get(a["chave"])]
    checar(u"  (fantoma) anuncio sem balao seria acusado", bool(_ruim))
    import radai_porta as _rp
    checar(u"a arte da porta tem seis vidros: anuncio novo espera decisao de "
           u"desenho", not _md2.ANUNCIOS
           and len(_rm.MODULOS_HOME) == len(_rp.ICONES) == 6,
           u"%d anuncios, %d modulos" % (len(_md2.ANUNCIOS), len(_rm.MODULOS_HOME)))


def teste_a_porta_de_reserva_lista_todo_modulo():
    secao(u"a porta de reserva: sem radai_porta, todo modulo da home")
    import html
    import radai_breadcrumb as _rt
    import radai_menu as _rm
    import radai_router
    _ausente = object()
    guardado = sys.modules.get("radai_porta", _ausente)
    sys.modules["radai_porta"] = None
    try:
        p = radai_router.pagina()
    finally:
        if guardado is _ausente:
            sys.modules.pop("radai_porta", None)
        else:
            sys.modules["radai_porta"] = guardado
    checar(u"sem `radai_porta`, a porta ainda abre",
           u"radioterapia.ai" in p and u"<a href=" in p)
    checar(u"  e e' a reserva, e nao a porta normal",
           u"ls-card" not in p, u"o import falhado nao chegou a pagina()")
    links = [l for l in re.findall(r'<a href="([^"]+)"', p) if l != u"/config"]
    checar(u"  na ordem aprovada, DicomBridge primeiro",
           links == [_rt.ARVORE[c][1] for c in _rm.MODULOS_HOME]
           and links[0] == u"/bridge", repr(links))
    for chave in _rm.MODULOS_HOME:
        nome, rota = (_rt.ARVORE.get(chave) or (u"", u""))[:2]
        checar(u"  a reserva leva a `%s`" % rota,
               bool(rota) and (u'href="%s"' % rota) in p, chave)
        checar(u"  com o nome da trilha (`%s`)" % nome,
               bool(nome) and html.escape(nome) in p, chave)


def teste_as_tres_mini_paginas():
    secao(u"nivel 2: cada modulo lista as ferramentas dele")
    import re
    import radai_modules as MD

    esperado = dict((k, len(v)) for k, v in MD.FERRAMENTAS.items())
    # GUARDA: regra CSS sem gerador fica parecendo que governa alguma coisa.
    _fonte_md = io.open(MD.__file__, encoding="utf-8").read()
    checar(u"a folha de radai_modules nao tem a regra `.md-rodape` sem gerador",
           u".md-rodape{" not in _fonte_md)
    for chave, n in esperado.items():
        p = MD.pagina(chave)
        checar(u"`%s` existe" % chave, bool(p))
        cartoes = p.count(u'class="md-fer')
        checar(u"`%s` lista %d ferramenta(s)" % (chave, n), cartoes == n,
               u"%d" % cartoes)
        checar(u"`%s` tem UMA lista (sem subgrupo)" % chave,
               p.count(u"md-grade") == 1)
        checar(u"`%s` tem o rotulo ESCOLHA A FERRAMENTA" % chave,
               u"ESCOLHA A FERRAMENTA" in p)
        checar(u"`%s` nao tem rodape" % chave, u"md-rodape" not in p)
        # GUARDA: o alerta de cada módulo é UMA linha com o ponto amarelo, no pé, depois dos cartões.
        checar(u"`%s` mostra a linha clinica" % chave, u'class="ui-alerta' in p)
        _cl = p[p.index(u'<div class="ui-alerta'):]
        _cl = _cl[:_cl.index(u"</div>") + 6]
        checar(u"  e ela esta fora de balao, com o marcador de traducao",
               u"ui-balao" not in _cl and u"data-radai-frase" in _cl, _cl[:120])
        checar(u"  e ela vem DEPOIS da lista de ferramentas (no rodape)",
               p.index(u'<div class="ui-alerta') > p.index(u"md-grade"))
        checar(u"`%s` tem UM `?`, junto do titulo" % chave,
               p.count(u"ui-ajuda") == 1, str(p.count(u"ui-ajuda")))
        checar(u"  e ele esta dentro do bloco do titulo",
               u"ui-ajuda" in p.split(u'class="md-tit"')[-1].split(u"</div>")[0]
               or u"ui-ajuda" in p.split(u'class="md-tit"')[-1][:1200])
        _sec = MD.secoes_de_ajuda(chave)
        for _t in (u"O que não faz", MD.TITULO_TERCEIROS):
            checar(u"  `%s`: o balao traz «%s»" % (chave, _t),
                   _t in _sec, str(sorted(_sec)))

    for chave in esperado:
        p = MD.pagina(chave)
        for m in re.finditer(r'<(a|div) class="md-fer([^"]*)"([^>]*)>', p):
            tag, classes, resto = m.group(1), m.group(2), m.group(3)
            if u"obra" in classes:
                checar(u"`%s`: cartao em obra NAO e link" % chave, tag == u"div",
                       m.group(0)[:60])
                checar(u"  e nao tem href", u"href" not in resto)

    # GUARDA: o texto longo mora no `?` ao lado do título; a tela fica com a tag, a frase, os cartões e o alerta.
    r = MD.pagina("recon3d")
    _bal = u"".join(re.findall(r"(?s)ui-balao.*?</span></span>", r))
    checar(u"a nao-exportacao das Reconstrucoes mora no `?` do titulo",
           u"o exporta" in _bal, _bal[:120])
    checar(u"e o paragrafo longo saiu da tela", u"md-semexp" not in r)


def teste_a_linha_clinica_do_contourlab_no_rodape():
    secao(u"ContourLab: o pe e UMA linha, depois da grade")
    import radai_modules as MD
    p = radai_panel.pagina_inicial()

    def medir(p):
        i_clin = p.find(u'<div class="ui-alerta')
        i_grade = p.find(u'class="md-grade"')
        notas = p.count(u'class="rc-nota"')
        linha = p[i_clin:p.index(u"</div>", i_clin)] if i_clin >= 0 else u""
        return i_clin, i_grade, notas, linha

    i_clin, i_grade, notas, linha = medir(p)
    checar(u"o alerta esta na mini-pagina do ContourLab", i_clin >= 0)
    checar(u"  depois da grade de ferramentas", i_grade >= 0 and i_clin > i_grade,
           u"grade=%d clin=%d" % (i_grade, i_clin))
    checar(u"  e e a unica nota do pe", notas == 0, str(notas))
    checar(u"  com o texto do autor (material de estudo, 100% local)",
           u"Material de estudo" in linha and u"100% local" in linha, linha[:160])
    checar(u"  fora de balao e com o marcador de traducao",
           u"ui-balao" not in linha and u"data-radai-frase" in linha)
    import radai_ui
    css = radai_ui.COMPONENTES
    regra = css[css.index(u".ui-alerta{"):]
    regra = regra[:regra.index(u"}")]
    checar(u"  e a folha nao a esconde", u"display:none" not in regra
           and u"visibility:hidden" not in regra, regra)
    checar(u"todo modulo leva o alerta para o rodape",
           MD.CLINICA_NO_RODAPE == frozenset(MD.MODULOS),
           str(sorted(MD.CLINICA_NO_RODAPE)))
    _conj = MD.CLINICA_NO_RODAPE
    try:
        MD.CLINICA_NO_RODAPE = frozenset()
        fora = MD.pagina(u"bridge")
    finally:
        MD.CLINICA_NO_RODAPE = _conj
    dentro = MD.pagina(u"bridge")
    checar(u"o conjunto decide o lugar: dentro dele, o alerta vem depois dos cartoes",
           dentro.index(u"ui-alerta") > dentro.index(u"md-grade"))
    checar(u"  (isca) fora dele, o alerta sobe para baixo da frase e continua na tela",
           u"ui-alerta" in fora and fora.index(u"ui-alerta") < fora.index(u"md-grade"))
    isca = p.replace(u"</body>", u'<p class="rc-nota"><b>100% local.</b></p></body>', 1)
    checar(u"  (isca) a nota velha de volta reprova", medir(isca)[2] != 0)


def teste_a_config_tem_cartoes_de_funcao():
    secao(u"config: cartoes de funcao no topo, opcoes recolhidas abaixo")
    import re as _re
    pag = radai_panel.PAGINA_CONFIG
    corpo = _re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<!--.*?-->",
                    u"", pag)
    alvos = _re.findall(r'<a class="cfg-card[^"]*" href="#([\w]+)" '
                        r'data-alvo="([\w]+)"', corpo)
    checar(u"ha oito cartoes de funcao", len(alvos) == 8, str(alvos))
    checar(u"  e o `href` de cada um e o `data-alvo` dele",
           all(a == b for a, b in alvos), str(alvos))
    secoes = _re.findall(r'<section class="ps-cx[^"]*" id="([\w]+)"', corpo)
    for a, _b in alvos:
        checar(u"o cartao `%s` aponta uma secao que existe" % a, a in secoes,
               str(secoes))
    checar(u"os cartoes seguem a ordem das secoes",
           [a for a, _b in alvos] == [x for x in secoes if x in dict(alvos)],
           u"%s | %s" % ([a for a, _b in alvos], secoes))
    checar(u"a ultima secao e o Desinstalar", secoes and secoes[-1] == "secDesinst",
           str(secoes))
    for fora, rot in (("ps_calib", u"Calibracao e relatorios"),
                      ("ps_procedencia", u"Procedencia das estruturas"),
                      ("ps_fechar", u"Encerrar o programa"),
                      ("mod_diag", u"Diagnostico do ambiente (como secao)")):
        checar(u"«%s» saiu da lista de secoes" % rot, fora not in secoes)
    checar(u"e a ancora do Fechar saiu da tela (o FECHAR APP mora na porta)",
           u"data-radai-encerrar" not in corpo)
    checar(u"e o grupo «O que o vigia varre» e o das bibliotecas sairam do JS",
           u"O que o vigia varre" not in pag.split(u"var GRUPOS=")[-1][:900]
           and u"Bibliotecas do TotalSegmentator" not in pag.split(u"var GRUPOS=")[-1][:900])
    nums = _re.findall(r'<span class="ps-num"[^>]*>(\d+)</span>', corpo)
    checar(u"os numeros do HTML ja nascem 1..8, sem repetir",
           nums == [str(i) for i in range(1, 9)], str(nums))
    cnums = _re.findall(r'<span class="n">(\d+)</span>', corpo)
    checar(u"  e os dos cartoes tambem", cnums == nums, str(cnums))
    checar(u"o seletor de idioma tem as duas ancoras no mesmo elemento",
           bool(_re.search(r"<div[^>]*data-radai-idiomas[^>]*data-radai-lang", corpo)))
    checar(u"e ele mora na secao Geral",
           corpo.index(u"data-radai-idiomas") > corpo.index(u'id="ps_geral"')
           and corpo.index(u"data-radai-idiomas") < corpo.index(u'id="ps_processamento"'))


def teste_a_recomendacao_de_device_e_auto():
    secao(u"processamento: a recomendacao e auto nos tres casos")
    import radai_watcher as W
    casos = (({"gpu": None, "escolhido": "cpu"}, u"sem placa"),
             ({"gpu": {"nome": "P2200", "memoria_gb": 5.0,
                       "memoria_livre_gb": 4.3}, "escolhido": "gpu"},
              u"placa pequena"),
             ({"gpu": {"nome": "RTX A4000", "memoria_gb": 16.0, "cuda": "12.1"},
               "escolhido": "auto"}, u"placa boa"))
    for laudo, rot in casos:
        r = W._recomendar_processamento(laudo)
        checar(u"%s: recomenda auto" % rot, r.get("device") == "auto", str(r)[:160])
        checar(u"  e diz se a estacao ja esta nele",
               r.get("ja_esta") is (laudo["escolhido"] == "auto"), str(r.get("ja_esta")))
        checar(u"  e explica por que", bool(r.get("porque")))


def teste_o_torax_saiu_da_arvore():
    secao(u"o Torax saiu da arvore inteira")
    import io
    import radai_menu, radai_breadcrumb, radai_modules
    checar(u"nao esta em ITENS",
           "torax" not in [i[0] for i in radai_menu.ITENS])
    checar(u"nao esta na arvore da trilha", "torax" not in radai_breadcrumb.ARVORE)
    checar(u"nao esta no trilho",
           "torax" not in radai_menu.MODULOS + radai_menu.NO_PE)
    checar(u"nao esta nas mini-paginas", "torax" not in radai_modules.MODULOS)
    checar(u"e nao ha apelido apontando para ele",
           "torax" not in radai_menu.ALIAS.values())

    rot = io.open(_componentes.fonte("app/radai_router.py"),
                  encoding="utf-8").read()
    checar(u"`/torax` responde 410", u"status_code=410" in rot)
    checar(u"e diz para onde ele foi",
           u"projeto pr" in rot and u"/torax" in rot)


def _argumentos_do_fastapi_do_vigia():
    import ast
    fonte = io.open(_componentes.fonte("app/radai_watcher.py"), encoding="utf-8").read()
    for no in ast.parse(fonte).body:
        if (isinstance(no, ast.Assign) and len(no.targets) == 1
                and getattr(no.targets[0], "id", "") == "app"
                and isinstance(no.value, ast.Call)
                and getattr(no.value.func, "id", "") == "FastAPI"):
            try:
                return dict((k.arg, ast.literal_eval(k.value))
                            for k in no.value.keywords if k.arg)
            except Exception:
                return None
    return None


def _app_como_o_do_vigia(FastAPI, kw):
    return FastAPI(**(kw or {}))


_PADRAO_RECURSO_EXTERNO = re.compile(
    r"""@import\s+(?:url\(\s*)?['"]?\s*(?:https?:)?//"""
    r"""|<link\b[^>]*\bhref\s*=\s*['"]?(?:https?:)?//"""
    r"""|url\(\s*['"]?\s*(?:https?:)?//"""
    r"""|<script\b[^>]*\bsrc\s*=\s*['"]?(?:https?:)?//"""
    r"""|<img\b[^>]*\bsrc\s*=\s*['"]?(?:https?:)?//"""
    r"""|<iframe\b[^>]*\bsrc\s*=\s*['"]?(?:https?:)?//"""
    r"""|<source\b[^>]*\bsrc\s*=\s*['"]?(?:https?:)?//"""
    r"""|\bsrcset\s*=\s*['"]?[^'">]*(?:https?:)?//"""
    r"""|\bfetch\(\s*['"`](?:https?:)?//"""
    r"""|\bimport\(\s*['"`](?:https?:)?//"""
    r"""|\.src\s*=\s*['"`](?:https?:)?//""",
    re.IGNORECASE)

_ISCAS_RECURSO_EXTERNO = (
    (u"o atributo sem aspas (link)", u"<link rel=stylesheet href=https://fonts.x/a.css>"),
    (u"o atributo sem aspas (script)", u"<script src=//cdn.x/a.js></script>"),
    (u"o srcset", u'<img alt="" srcset="a.png 1x, https://cdn.x/b.png 2x">'),
    (u"o <iframe src>", u'<iframe src="https://x.y/z"></iframe>'),
    (u"o <source src>", u"<video><source src='//cdn.x/v.mp4'></video>"),
    (u"o fetch com URL absoluta", u"fetch('https://stats.x/y').then(f)"),
    (u"o import() com URL absoluta", u"import('https://cdn.x/m.js')"),
    (u"o .src montado por JS", u"var i = new Image(); i.src = 'https://x/p.gif';"),
    (u"o @import sem url()", u'@import "https://fonts.x/a.css";'),
    (u"o url() de protocolo relativo", u"src:url(//fonts.x/a.woff2)"),
)
_NAO_E_RECURSO_EXTERNO = (
    (u"um link de DOI (<a href>)", u'<a href="https://doi.org/10.1016/x">artigo</a>'),
    (u"um fetch da propria API", u"fetch('/api/status').then(f)"),
    (u"uma URL escrita em texto", u"<p>veja https://radioterapia.ai</p>"),
)


def teste_nenhuma_pagina_busca_recurso_na_internet():
    secao(u"nenhuma pagina referencia recurso externo (css/fonte/js/img)")
    try:
        from fastapi import FastAPI
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False,
               u"PULADO -- %s: %s" % (type(e).__name__, e))
        return
    import re
    import radai_panel as _rp

    kw_vigia = _argumentos_do_fastapi_do_vigia()
    checar(u"os argumentos do FastAPI(...) do vigia foram lidos",
           kw_vigia is not None, u"sem eles o app de teste nao e o da producao")
    app = _app_como_o_do_vigia(FastAPI, kw_vigia)
    try:
        _rp.montar(app)
    except Exception as e:
        checar(u"radai_panel.montar nao levantou (pre-condicao da checagem)",
               False, u"%s: %s" % (type(e).__name__, e))

    cliente = TestClient(app, raise_server_exceptions=False)

    rotas = sorted({
        r.path for r in app.routes
        if getattr(r, "methods", None) and "GET" in r.methods
        and "{" not in r.path
        and not r.path.startswith("/api")
    })
    checar(u"a varredura pegou pelo menos as paginas ja conhecidas",
           len(rotas) >= 25, u"%d rotas: %s" % (len(rotas), rotas))

    EXCECOES = {
        u"/torax": u"410 de proposito (radai_router.py, comentario "
                   u"\"RESPONDE 410, E DIZ PARA ONDE ELE FOI\") -- o modulo "
                   u"SAIU; nao e' rota quebrada.",
    }
    padrao = _PADRAO_RECURSO_EXTERNO

    for rotulo, isca in _ISCAS_RECURSO_EXTERNO:
        checar(u"a regex pega %s" % rotulo, padrao.search(isca) is not None,
               isca[:80])
    for rotulo, limpo in _NAO_E_RECURSO_EXTERNO:
        checar(u"e nao acusa %s" % rotulo, padrao.search(limpo) is None,
               limpo[:80])

    respostas = {}
    achados = []
    fora_da_tabela = []
    for rota in rotas:
        try:
            r = cliente.get(rota)
        except Exception as e:
            checar(u"`%s` respondeu (sem excecao no cliente)" % rota, False,
                   u"%s: %s" % (type(e).__name__, e))
            continue
        respostas[rota] = r
        motivo = EXCECOES.get(rota)
        if motivo:
            continue
        if r.status_code != 200:
            fora_da_tabela.append(u"%s: %d" % (rota, r.status_code))
            continue
        m = padrao.search(r.text)
        if m:
            achados.append(u"%s: ...%s..."
                           % (rota, r.text[max(0, m.start() - 15):m.start() + 55]))

    checar(u"toda rota fora da tabela de excecoes respondeu 200",
           not fora_da_tabela, u" | ".join(fora_da_tabela)[:300])
    checar(u"nenhuma pagina renderizada busca CSS/fonte/JS/imagem em "
           u"http(s):// ou // (fora das excecoes declaradas)",
           not achados, u" | ".join(achados)[:300])

    for rota, motivo in EXCECOES.items():
        r = respostas.get(rota)
        checar(u"a excecao declarada `%s` ainda tem rota no app (senao, tire "
               u"da tabela)" % rota, r is not None, motivo)
        if r is None:
            continue
        esperado = 410 if rota == u"/torax" else 200
        checar(u"a excecao `%s` continua com o status que o motivo descreve"
               % rota,
               r.status_code == esperado,
               u"esperava %d, veio %d -- motivo: %s"
               % (esperado, r.status_code, motivo))

    def _tokens(pilha_css):
        return [t.strip().strip(u"'\"") for t in pilha_css.split(u",")]

    def _pos(tokens, nome):
        try:
            return tokens.index(nome)
        except ValueError:
            return None

    corpo_auto = (respostas[u"/autocontorno"].text
                  if u"/autocontorno" in respostas else u"")
    disp = [m.group(1) for m in re.finditer(r"--font-display:([^;]+);", corpo_auto)]
    mono = [m.group(1) for m in re.finditer(r"--font-mono:([^;]+);", corpo_auto)]
    checar(u"a declaracao --font-display existe no CSS renderizado",
           bool(disp))
    ruins = []
    for pilha in disp:
        tk = _tokens(pilha)
        p_sys, p_segoe = _pos(tk, u"system-ui"), _pos(tk, u"Segoe UI")
        if not (p_sys is not None and p_segoe is not None and p_sys < p_segoe):
            ruins.append(pilha)
    checar(u"TODA pilha do titulo (%d declaracao/oes) cai em system-ui e "
           u"depois Segoe UI, nesta ordem" % len(disp),
           disp and not ruins, u" || ".join(ruins or disp))
    checar(u"a declaracao --font-mono existe no CSS renderizado",
           bool(mono))
    ruins = []
    for pilha in mono:
        tk = _tokens(pilha)
        p_cons, p_mono = _pos(tk, u"Consolas"), _pos(tk, u"monospace")
        if not (p_cons is not None and p_mono is not None and p_cons < p_mono):
            ruins.append(pilha)
    checar(u"TODA pilha de mono (%d declaracao/oes) cai em Consolas e depois "
           u"monospace, nesta ordem" % len(mono),
           mono and not ruins, u" || ".join(ruins or mono))


_PRIMEIRO_USO_VELHO = (u"No Vigia", u"Configurações, preencha a pasta",
                       u"Configuracoes, informe a pasta", u"mostra o tutorial",
                       u"Radioterapia.AI - Auto Contorno")


def _primeiro_uso_divergente(t, lote, modulos, atalho):
    fora = []
    tt = u" ".join((t or u"").split())
    for v in _PRIMEIRO_USO_VELHO:
        if v in tt:
            fora.append(u"cita «%s»" % v)
    if u"Incluir Overnight Run" not in tt:
        fora.append(u"nao nomeia o cartao «Incluir Overnight Run»")
    elif u"Incluir Overnight Run" not in lote:
        fora.append(u"o cartao «Incluir Overnight Run» nao existe no lote")
    if u"Rodar agora" not in tt:
        fora.append(u"nao nomeia a ferramenta «Rodar agora»")
    elif u"Rodar agora" not in modulos:
        fora.append(u"a ferramenta «Rodar agora» nao existe")
    if u"atalho" in tt and atalho and atalho not in tt:
        fora.append(u"o atalho nao e o que o INSTALL.ps1 grava (%s)" % atalho)
    if u"TPS de destino (Eclipse ou" in tt:
        fora.append(u"diz que o primeiro uso pede o TPS de destino (saiu na v8.7)")
    if u"pasta favorita" not in tt:
        fora.append(u"nao diz que o primeiro uso pede a pasta favorita")
    return fora


def teste_o_primeiro_uso_aponta_o_que_existe():
    secao("o primeiro uso aponta a pasta onde o campo existe")
    raiz = os.path.abspath(os.path.join(AQUI, ".."))
    lote = io.open(_componentes.fonte("app/radai_batch.py"),
                   encoding="utf-8").read()
    modulos = io.open(_componentes.fonte("app/radai_modules.py"),
                      encoding="utf-8").read()
    inst_p = os.path.join(raiz, "installer", "INSTALL.ps1")
    if not os.path.isfile(inst_p):
        checar("(layout instalado: sem installer\\, nada a conferir)", True)
        return
    inst = io.open(inst_p, encoding="utf-8-sig").read()
    m = re.search(r'Join-Path \$d\.pasta "([^"]+)\.lnk"', inst)
    atalho = m.group(1) if m else u""
    checar("li o nome do atalho que o INSTALL.ps1 grava (%s)" % atalho,
           bool(atalho))
    i = inst.find(u"PROXIMOS PASSOS")
    textos = [(u"INSTALL.ps1", u" ".join(
        re.findall(r'Diga "([^"]*)"', inst[i:])) if i >= 0 else u"")]
    ca = io.open(os.path.join(raiz, "build", "configurar_ambiente.py"),
                 encoding="utf-8").read()
    j = ca.find('LEIA_ME = """')
    textos.append((u"LEIA_ME", ca[j:ca.find('"""', j + 14)] if j >= 0
                   else u""))
    prep = io.open(os.path.join(raiz, "packager", "prepare.ps1"),
                   encoding="utf-8-sig").read()
    for k, bloco in enumerate(re.findall(r"PRIMEIRO USO(.*?)\"@", prep,
                                         re.S)):
        textos.append((u"prepare.ps1, tela 4 (%d)" % (k + 1), bloco))
    checar("achei os cinco textos de primeiro uso (o INSTALL, o LEIA-ME e as "
           "tres conclusoes que instalam: estacao, modo 3 e instalacao direta)",
           len(textos) == 5 and all(t for _n, t in textos),
           [n for n, t in textos])
    for nome, t in textos:
        div = _primeiro_uso_divergente(t, lote, modulos, atalho)
        checar("%s: aponta a pasta pelo Overnight Run do Rodar agora" % nome,
               not div, "; ".join(div))
    velho = textos[0][1] + u" No Vigia, passo 1, aponte a pasta."
    checar("  isca: o texto de antes («No Vigia») reprova",
           bool(_primeiro_uso_divergente(velho, lote, modulos, atalho)))
    checar("  isca: o cartao renomeado no lote reprova",
           bool(_primeiro_uso_divergente(
               textos[0][1], lote.replace(u"Incluir Overnight Run", u"X"),
               modulos, atalho)))
    v86 = (u"Logo depois, o primeiro uso pede o TPS de destino (Eclipse ou "
           u"Monaco) e a pasta favorita. No ContourLab, em Rodar agora, clique "
           u"em Incluir Overnight Run.")
    checar("  isca: o texto da v8.6, que manda escolher o TPS, reprova",
           bool(_primeiro_uso_divergente(v86, lote, modulos, atalho)))
    import radai_primeiro_uso as _pu
    consent = io.open(_componentes.fonte("app/radai_consent.py"), encoding="utf-8").read()
    checar("e a tela que o texto promete existe: o aceite leva a /primeiro-uso",
           _pu.ROTA == u"/primeiro-uso" and u"'/primeiro-uso?de='" in consent)


def _promete_a_profunda(pagina):
    return (u"Verificação profunda" in pagina or u"conferirProfunda" in pagina
            or u"/api/conferir/profunda" in pagina)


def teste_a_verificacao_profunda_saiu_da_instalacao():
    secao("a verificacao profunda saiu da instalacao: botao, rota e funcao")
    pag = radai_panel.PAGINA_CONFIG
    checar("a tela nao oferece mais a Verificacao profunda",
           not _promete_a_profunda(pag))
    checar("  (isca) a tela antiga e acusada",
           _promete_a_profunda(pag.replace(u"</section>",
                                           u"<summary>Verificação profunda</summary>"
                                           u"</section>", 1)))
    checar("a funcao que apontava o log do verify saiu",
           not hasattr(radai_panel, "resultado_do_verify"))
    fonte = io.open(_componentes.fonte("app/radai_panel.py"), encoding="utf-8").read()
    checar("e nenhuma rota procura o verify.cmd", u"verify.cmd" not in fonte)
    try:
        from fastapi import FastAPI
        app = FastAPI()
        radai_panel.montar(app, ler_vigia=lambda: {}, config={})
        rotas = set(getattr(r, "path", u"") for r in app.routes)
    except Exception as e:
        rotas = set()
        checar("o painel monta", False, "%s: %s" % (type(e).__name__, e))
    checar("as rotas sem tela /api/conferir/profunda, /api/conferir/rapida e "
           "/api/ferramenta/conferir sairam",
           rotas and not ({"/api/conferir/profunda", "/api/conferir/rapida",
                           "/api/ferramenta/conferir"} & rotas),
           sorted(r for r in rotas if "conferir" in r))
    checar("  e o Diagnosticar continua (rota e botao)",
           "/api/diagnosticar" in rotas and 'onclick="diagnosticar()"' in pag
           and u"Diagnósticos e Registros" in pag
           and u"Diagnosticar e otimizar" not in pag)

    raiz = os.path.dirname(AQUI)
    for rel, extrai in ((os.path.join("installer", "INSTALL.ps1"), None),
                        (os.path.join("build", "configurar_ambiente.py"),
                         "LEIA_ME")):
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            continue
        t = io.open(p, encoding="utf-8-sig", errors="replace").read()
        if extrai:
            i = t.find(extrai + ' = """')
            t = t[i:t.find('"""', i + len(extrai) + 6)] if i >= 0 else u""
        checar("%s: o texto de depois de instalar existe" % rel, bool(t))
        checar("  e nomeia o Diagnosticar", "Diagnosticar" in t)
        checar("  e o bloco pelo nome de agora (Diagnosticos e Registros), "
               "sem o Otimizar", "Diagnosticos e Registros" in t
               and "otimizar" not in t.lower())
        checar("  e nao manda rodar a Verificacao profunda, que saiu",
               "Verificacao profunda" not in t and u"Verificação profunda" not in t)


def teste_a_versao_das_bibliotecas_vem_do_pacote():
    secao(u"diagnostico: a versao vem do pacote instalado, e versao desconhecida nao e ok")
    import types
    from importlib import metadata
    checar(u"o painel le a versao pelo pacote (fastapi)",
           radai_panel.versao_da_biblioteca("fastapi")
           == metadata.version("fastapi"))
    checar(u"  e o rt_utils pelo nome da distribuicao (rt-utils)",
           radai_panel.DISTRIBUICAO.get("rt_utils") == "rt-utils"
           and radai_panel.DISTRIBUICAO.get("totalsegmentator")
           == "TotalSegmentator")
    sem = types.ModuleType("radai_sem_versao_de_teste")
    checar(u"  modulo sem pacote nem __version__ devolve vazio, e nao «presente»",
           radai_panel.versao_da_biblioteca("radai_sem_versao_de_teste", sem) == u"")
    d = radai_panel.diagnostico()
    libs = dict((k, v) for k, v in d["ambiente"].items() if k.startswith("lib "))
    checar(u"o ambiente do diagnostico nao diz «presente» nem «?»",
           libs and not [k for k, v in libs.items() if v in ("presente", "?")],
           libs)
    import radai_station_check as CE
    sec = CE._secao_bibliotecas()
    oks = [i for i in sec["itens"] if i["ok"] is True]
    checar(u"no Diagnosticar, toda biblioteca marcada ok tem versao de verdade",
           oks and all(i["valor"] and i["valor"] != u"?" for i in oks),
           [(i["nome"], i["valor"]) for i in oks])
    fast = next((i for i in sec["itens"] if i["nome"] == "fastapi"), {})
    checar(u"  e a do fastapi e a do pacote",
           fast.get("valor") == metadata.version("fastapi"), fast)
    velho = CE._versao
    CE._versao = lambda nome, mod=None: u""
    try:
        isca = CE._secao_bibliotecas()
    finally:
        CE._versao = velho
    importam = [i for i in isca["itens"] if i["valor"] != u"não importa"]
    checar(u"  (isca) sem versao, a biblioteca que importa vira aviso, e nao ok",
           importam and all(i["ok"] is None and i["valor"] == u"versão desconhecida"
                            for i in importam),
           [(i["nome"], i["ok"], i["valor"]) for i in importam][:4])
    nomes = [i["nome"] for i in CE._secao_estrutura()["itens"]]
    checar(u"a lista de arquivos do programa nao exige mais o verify.cmd",
           not [n for n in nomes if "verify" in n], nomes)


def teste_nomes_do_bridge_batem_cartao_trilha_h1():
    secao(u"bridge: um cartao, e cartao, trilha e h1 dizem o mesmo nome "
          u"(bridge_laudo; tps e imagem levam a ele)")
    try:
        from fastapi import FastAPI
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False,
               u"PULADO -- %s: %s" % (type(e).__name__, e))
        return
    import html as _html
    import radai_panel as _rp
    import radai_modules as _M
    import radai_breadcrumb as _bc

    app = _app_como_o_do_vigia(FastAPI, _argumentos_do_fastapi_do_vigia())
    try:
        _rp.montar(app)
    except Exception as e:
        checar(u"radai_panel.montar nao levantou (pre-condicao da checagem)",
               False, u"%s: %s" % (type(e).__name__, e))
        return
    cliente = TestClient(app, raise_server_exceptions=False)

    cartoes = {f[0]: f[2] for f in _M.FERRAMENTAS[u"bridge"]}
    rota_de = {u"bridge_laudo": u"/bridge/laudo"}
    checar(u"o DicomBridge tem UM cartão, o pipeline (a conversão de imagens mora nele)",
           sorted(cartoes) == sorted(rota_de), sorted(cartoes))
    checar(u"  e o cartão leva à rota da tela",
           all(f[3] == rota_de.get(f[0]) for f in _M.FERRAMENTAS[u"bridge"]),
           [(f[0], f[3]) for f in _M.FERRAMENTAS[u"bridge"]])
    checar(u"  com o ícone por nome (exportar)",
           dict((f[0], f[1]) for f in _M.FERRAMENTAS[u"bridge"])
           == {u"bridge_laudo": u"exportar"})
    checar(u"os passos antigos `bridge_tps` e `bridge_imagem` saíram da trilha",
           u"bridge_tps" not in _bc.ARVORE and u"bridge_imagem" not in _bc.ARVORE)
    for antiga in (u"/bridge/tps", u"/bridge/imagem"):
        r_ant = cliente.get(antiga, follow_redirects=False)
        checar(u"e %s leva ao pipeline (307 para /bridge/laudo)" % antiga,
               r_ant.status_code == 307
               and r_ant.headers.get(u"location", u"").endswith(u"/bridge/laudo"),
               u"%d %s" % (r_ant.status_code, r_ant.headers.get(u"location")))

    for chave in (u"bridge_laudo",):
        rota = rota_de[chave]
        nome_card = cartoes.get(chave)
        checar(u"`%s` tem nome no cartao" % chave, bool(nome_card))
        entrada_trilha = _bc.ARVORE.get(chave)
        nome_trilha = entrada_trilha[0] if entrada_trilha else None
        checar(u"`%s` tem o MESMO nome na trilha" % chave,
               bool(nome_card) and nome_trilha == nome_card,
               u"cartao=%r trilha=%r" % (nome_card, nome_trilha))
        if not nome_card:
            continue
        r = cliente.get(rota)
        if r.status_code != 200:
            checar(u"`%s` respondeu 200 para conferir o h1" % rota, False,
                   u"%d" % r.status_code)
            continue
        m = re.search(r"<h1[^>]*>(.*?)</h1>", r.text, re.DOTALL)
        h1 = (_html.unescape(re.sub(r"<span[^>]*aria-hidden[^>]*>.*?</span>|<[^>]+>",
                                    u"", m.group(1))).strip() if m else None)
        checar(u"`%s` tem o MESMO nome no <h1> da tela" % chave,
               h1 == nome_card,
               u"cartao=%r h1=%r" % (nome_card, h1))


def teste_o_icone_do_produto_chega_a_tela():
    print(u"  -- o icone `.ai` e servido, apontado e embarcado --")
    import io as _io
    import os as _os

    RAIZ = _os.path.dirname(AQUI)
    APP = _os.path.join(RAIZ, "app")
    ARQUIVOS = ("favicon.svg", "favicon.ico", "favicon.png")

    for nome in ARQUIVOS:
        p = _os.path.join(APP, nome)
        tam = _os.path.getsize(p) if _os.path.isfile(p) else 0
        checar(u"app/%s existe e tem conteudo" % nome, tam > 500,
               u"%d bytes" % tam)

    ico = _os.path.join(APP, "favicon.ico")
    try:
        import struct
        with open(ico, "rb") as f:
            cab = f.read(6)
            n = struct.unpack("<H", cab[4:6])[0]
            larguras = []
            for _ in range(n):
                e = f.read(16)
                w = e[0] or 256
                larguras.append(w)
    except Exception as e:
        larguras = []
        checar(u"o favicon.ico abre", False, str(e))
    for esperado in (16, 32, 48, 256):
        checar(u"  o .ico traz %dx%d" % (esperado, esperado),
               esperado in larguras, str(sorted(larguras)))

    ui = _io.open(_os.path.join(APP, "radai_ui.py"), encoding="utf-8").read()
    import ast as _ast
    _chama = False
    try:
        for _n in _ast.walk(_ast.parse(ui)):
            if isinstance(_n, _ast.FunctionDef) and _n.name == "aplicar":
                for _m in _ast.walk(_n):
                    if (isinstance(_m, _ast.Call)
                            and getattr(_m.func, "id", "") == "_pendurar_icone"):
                        _chama = True
    except Exception:
        pass
    checar(u"`aplicar` CHAMA `_pendurar_icone`", _chama,
           u"sem isto nenhuma tela aponta para o desenho")
    i_pend = ui.find(u"pagina = _pendurar_icone(pagina)")
    i_guarda = ui.find(u"if not pagina or MARCA_CSS in pagina:")
    checar(u"  e ANTES da guarda do MARCA_CSS",
           i_pend > 0 and i_guarda > i_pend,
           u"a tela do aceite e costurada antes e sairia sem o icone")
    for rel in (u'rel="icon" href="/favicon.svg"',
                u'rel="alternate icon" href="/favicon.ico"'):
        checar(u"  declara %s" % rel[:28], rel in ui)

    checar(u"`montar_icone` existe", u"def montar_icone(app):" in ui)
    for rota in (u'@app.get("/favicon.svg")', u'@app.get("/favicon.ico")',
                 u'@app.get("/favicon.png")'):
        checar(u"  serve %s" % rota[10:-2], rota in ui)
    w = _io.open(_componentes.fonte("app/radai_watcher.py"),
                 encoding="utf-8").read()
    checar(u"o vigia monta a rota do icone",
           u"montar_icone(app)" in w,
           u"sem isto o `<link>` aponta para um 404")
    def _try_do_icone(fonte):
        for _t in _ast.walk(_ast.parse(fonte)):
            if not isinstance(_t, _ast.Try):
                continue
            _chamadas = [getattr(_c.func, "attr", "") for _s in _t.body
                         for _c in _ast.walk(_s) if isinstance(_c, _ast.Call)]
            if "montar_icone" in _chamadas:
                return _chamadas
        return None

    _ch = _try_do_icone(w)
    checar(u"  e num `try` proprio, nao no do dicionario",
           _ch is not None and "montar" not in _ch,
           u"falha do icone sairia como falha de idioma")
    checar(u"  isca: o icone no `try` do dicionario e acusado",
           "montar" in (_try_do_icone(
               u"try:\n    import radai_languages\n"
               u"    radai_languages.montar(app)\n"
               u"    _ui.montar_icone(app)\nexcept Exception:\n    pass\n")
               or ()))

    ca = _io.open(_os.path.join(RAIZ, "build", "configurar_ambiente.py"),
                  encoding="utf-8").read()
    checar(u"`etapa_app` leva os icones por GLOB, e nao por lista",
           u'if p.suffix.lower() in (".ico", ".png", ".svg")' in ca,
           u"lista a mao ao lado de um glob e a metade que envelhece")
    import sys as _sys
    if _os.path.join(RAIZ, "build") not in _sys.path:
        _sys.path.insert(0, _os.path.join(RAIZ, "build"))
    try:
        import empacotar_instalador as _emp
        faltam = [n for n in ARQUIVOS if not _emp.entra(n)]
        checar(u"o instalador leve leva os tres", not faltam, str(faltam))
    except Exception as e:
        checar(u"o empacotador do instalador leve foi lido", False, str(e))

    inst = _io.open(_os.path.join(RAIZ, "installer", "INSTALL.ps1"),
                    encoding="utf-8-sig").read()
    checar(u"o atalho procura `favicon.ico` PRIMEIRO",
           u'@("favicon.ico", "radioterapia_ai.ico")' in inst,
           u"atalho e aba com desenhos diferentes parecem dois programas")
    prep = _io.open(_os.path.join(RAIZ, "packager", "prepare.ps1"),
                    encoding="utf-8-sig").read()
    checar(u"  e a janela do preparador tambem",
           u"@('favicon.ico', 'radioterapia_ai.ico')" in prep)


def _defaults_do_vigia():
    import ast
    fonte = io.open(_componentes.fonte("app/radai_watcher.py"), encoding="utf-8").read()
    for no in ast.parse(fonte).body:
        if (isinstance(no, ast.Assign) and len(no.targets) == 1
                and getattr(no.targets[0], "id", "") == "DEFAULTS"):
            return ast.literal_eval(no.value)
    return {}


def _app_do_painel(caminho_cfg, em_uso=None):
    from fastapi import FastAPI
    padroes = _defaults_do_vigia()
    app = FastAPI()
    radai_panel.montar(app, ler_vigia=lambda: {}, config={
        "caminho": caminho_cfg, "chaves": list(padroes), "padroes": padroes,
        "modelo": u"", "em_uso": (lambda: dict(em_uso or padroes))})
    return app


def teste_a_suavizacao_nao_se_grava_pela_tela():
    secao(u"config: a suavizacao nao se ajusta pela tela")
    try:
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False, u"PULADO -- %s" % e)
        return
    base = novo_temp()
    arq = os.path.join(base, "t.config")
    with io.open(arq, "w", encoding="utf-8") as f:
        f.write(u"# teste\nSUAVIZAR_MM=1.0\nDRY_RUN=0\nDEVICE=auto\n")
    c = TestClient(_app_do_painel(arq), raise_server_exceptions=False)
    api = c.get("/api/config").json()
    checar(u"a tela nao recebe SUAVIZAR_MM", "SUAVIZAR_MM" not in api["chaves"],
           str(api["chaves"])[:120])
    checar(u"  nem DRY_RUN", "DRY_RUN" not in api["chaves"])
    c.post("/api/config", json={"valores": {"SUAVIZAR_MM": "3.0"}})
    _v = radai_config.ler_arquivo(arq)[1]
    checar(u"e um POST com SUAVIZAR_MM nao mexe no arquivo",
           _v.get("SUAVIZAR_MM") == "1.0", repr(_v.get("SUAVIZAR_MM")))
    c.post("/api/config", json={"valores": {"DEVICE": "cpu"}})
    _v = radai_config.ler_arquivo(arq)[1]
    checar(u"a mesma rota grava o que e da tela (DEVICE)",
           _v.get("DEVICE") == "cpu", repr(_v.get("DEVICE")))
    p = radai_panel.PAGINA_CONFIG
    import re as _re
    codigo = _re.sub(r"(?s)<!--.*?-->|/\*.*?\*/", u"", p)
    codigo = _re.sub(r"(?m)^\s*//.*$", u"", codigo)
    checar(u"a pagina nao tem mais cursor", u'type="range"' not in codigo
           and u"CURSORES" not in codigo and u"curMudou" not in codigo)
    import radai_provenance_screen as _PS
    checar(u"a Procedencia diz onde a suavizacao mora (SUAVIZAR_MM, no arquivo)",
           u"SUAVIZAR_MM" in _PS.PAGINA
           and u"arquivo de configura" in _PS.PAGINA)
    checar(u"  e a /config continua levando a ela, no pe",
           u'href="/procedencia"' in p[p.index(u'<footer class="cfg-docs">'):])


MODOS_QUE_SAIRAM = (u"modo completo", u"escolha o completo", u"modo padrao",
                    u"o padrao do")
PLUGINS_DESCRITOS_NO_TASKS = ("lung_vessels",)


def _norm_cfg(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t or u"")
    t = u"".join(c for c in t if not unicodedata.combining(c))
    return u" ".join(t.lower().split())


def _campos_que_citam_modo_sem_nota(ajudas):
    fora = []
    for k, h in sorted((ajudas or {}).items()):
        n = _norm_cfg(h)
        if any(f in n for f in MODOS_QUE_SAIRAM) and not (
                u"v8.2" in n and u"os modos sairam" in n):
            fora.append(k)
    return fora


FRASES_QUE_A_V82_DESMENTIU = (u"so nos conjuntos crus",
                              u"muda o contorno do coracao")


def _paragrafos_do_cfg(texto):
    fora, paras, atual = {}, [], []
    for linha in (texto or u"").splitlines():
        cru = linha.strip()
        if cru.startswith(u"#"):
            limpo = cru.lstrip(u"#").strip()
            if limpo:
                atual.append(limpo)
            elif atual:
                paras.append(u" ".join(atual))
                atual = []
        elif cru and u"=" in cru:
            if atual:
                paras.append(u" ".join(atual))
            fora[cru.split(u"=", 1)[0].strip()] = paras
            paras, atual = [], []
        else:
            paras, atual = [], []
    return fora


def _frases_velhas_sem_nota(texto_cfg, cods):
    fora = []
    validos = set([u"radai_oar"]) | set(u"study_%s" % c for c in cods)
    for chave, paras in sorted(_paragrafos_do_cfg(texto_cfg).items()):
        for par in paras:
            n = _norm_cfg(par)
            sem_citacao = re.sub(u"«[^»]*»", u" ", n)
            if u"v8.2" not in n:
                for f in FRASES_QUE_A_V82_DESMENTIU:
                    if f in sem_citacao:
                        fora.append((chave, f))
            for m in re.finditer(r"\b(RadAI_[A-Z]\w*|STUDY_\w+)", par):
                rot = m.group(1).lower().rstrip(u"_")
                depois = _norm_cfg(par[m.end():m.end() + 80])
                if rot not in validos and u"rotulo que nao existe" not in depois:
                    fora.append((chave, m.group(1)))
    return fora


def _plugins_sem_arquivo(ajuda_tasks, plugins):
    por_task = dict((p.get("task"), p.get("infixo")) for p in plugins or [])
    return [t for t in PLUGINS_DESCRITOS_NO_TASKS
            if not por_task.get(t)
            or (u"RS_RadAI_" + por_task[t]) not in (ajuda_tasks or u"")]


def teste_a_ajuda_do_config_diz_a_v82():
    secao(u"config: a ajuda dos campos nao promete os modos que sairam")
    import radai_watcher
    import radai_sets
    ajudas = radai_config.comentarios(radai_watcher.DEFAULT_CFG)
    checar(u"li a ajuda dos campos do DEFAULT_CFG (%d)" % len(ajudas),
           len(ajudas) > 10 and u"ROOT" in ajudas
           and u"TRAVA_SEM_PULSO_MIN" in ajudas)
    fora = _campos_que_citam_modo_sem_nota(ajudas)
    checar(u"todo campo que cita um modo traz a nota de que os modos sairam",
           not fora, u", ".join(fora))
    _velho = dict(ajudas)
    _velho[u"INCLUIR_HNLNL"] = (
        u"Com 1 aqui, o vigia os roda em toda serie, e o modo Padrao do "
        u"«Rodar agora» tambem -- o Padrao segue a estacao.")
    checar(u"  isca: o bloco do HNLNL de antes, sem a nota, e acusado",
           _campos_que_citam_modo_sem_nota(_velho) == [u"INCLUIR_HNLNL"])
    checar(u"o campo TASKS saiu do config (v8.4: o vigia e sempre AUTO)",
           u"TASKS" not in ajudas)
    checar(u"  isca: um DEFAULT_CFG com TASKS= de volta e acusado",
           u"TASKS" in radai_config.comentarios(
               radai_watcher.DEFAULT_CFG.replace(
                   u"ROOT=\n", u"ROOT=\n\n# tasks\nTASKS=total_v3\n", 1)))
    checar(u"  isca: o bloco de antes («so no RTSTRUCT de comparacao (_ts)») "
           u"e acusado",
           _plugins_sem_arquivo(
               u"lung_vessels ... sai nos conjuntos crus. "
               u"pleural_pericard_effusion ... as duas saem so no RTSTRUCT "
               u"de comparacao (_ts)", radai_sets.PLUGINS)
           == list(PLUGINS_DESCRITOS_NO_TASKS))
    cods = ([c["cod"] for c in radai_sets.CONJUNTOS]
            + [c["cod"] for c in radai_sets.PLUGINS])
    velhas = _frases_velhas_sem_nota(radai_watcher.DEFAULT_CFG, cods)
    checar(u"nenhuma frase que a v8.2 desmentiu fica sem nota, e nenhum "
           u"rotulo inexistente e citado como se existisse", not velhas,
           str(velhas[:4]))
    import ast as _ast
    import subprocess as _sp
    try:
        _src = _sp.check_output(
            ["git", "show", "025a1b4:app/radai_watcher.py"],
            cwd=os.path.dirname(APP), stderr=_sp.DEVNULL,
            timeout=30).decode("utf-8")
        _cfg_antes = next(
            n.value.value for n in _ast.parse(_src).body
            if isinstance(n, _ast.Assign)
            and getattr(n.targets[0], "id", "") == "DEFAULT_CFG")
    except Exception as e:
        _cfg_antes = None
        print(u"  (isca do DEFAULT_CFG de 025a1b4 pulada: %s)"
              % type(e).__name__)
    if _cfg_antes is not None:
        _ant = _frases_velhas_sem_nota(_cfg_antes, cods)
        checar(u"  isca: o DEFAULT_CFG de 025a1b4 e acusado (as tres partes: "
               u"conjuntos crus, pericardico, RadAI_Full)",
               set(f for _k, f in _ant) >= set([
                   u"so nos conjuntos crus", u"muda o contorno do coracao",
                   u"RadAI_Full"]), str(_ant[:6]))
    _forjado = radai_watcher.DEFAULT_CFG.replace(
        u"\nTIMEOUT_TASK_H=",
        u"\n# a entrega completa e o RadAI_Full.\nTIMEOUT_TASK_H=", 1)
    checar(u"  isca: o rotulo inexistente citado como se existisse e acusado",
           _forjado != radai_watcher.DEFAULT_CFG
           and u"RadAI_Full" in [f for _k, f in
                                 _frases_velhas_sem_nota(_forjado, cods)],
           str(_frases_velhas_sem_nota(_forjado, cods)[:4]))
    _sem_nota = radai_watcher.DEFAULT_CFG.replace(
        u"\nTIMEOUT_TASK_H=",
        u"\n\n# a lung_vessels sai so nos conjuntos crus.\nTIMEOUT_TASK_H=",
        1)
    checar(u"  isca: a frase desmentida sem a nota, num bloco que ficou, e "
           u"acusada (o bloco das TASKS saiu na v8.4)",
           _sem_nota != radai_watcher.DEFAULT_CFG
           and (u"TIMEOUT_TASK_H", u"so nos conjuntos crus")
           in _frases_velhas_sem_nota(_sem_nota, cods),
           str(_frases_velhas_sem_nota(_sem_nota, cods)[:4]))


def _hnlnl_diz_a_v82(t):
    if not t:
        return False
    return (u"série do vigia" in t
            and u"Estudo Cabeça e Pescoço" in t
            and u"não esta chave" in t
            and u"Padrão do «Rodar agora»" not in t
            and u"De fábrica desligado" in t)


def teste_o_recorte_no_corpo_segue_a_suavizacao():
    secao(u"config: o recorte no corpo segue a suavizacao")
    try:
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False, u"PULADO -- %s" % e)
        return
    base = novo_temp()
    arq = os.path.join(base, "t.config")
    with io.open(arq, "w", encoding="utf-8") as f:
        f.write(u"# teste\nRECORTE_NO_CORPO=1\nDEVICE=auto\n")
    c = TestClient(_app_do_painel(arq), raise_server_exceptions=False)
    api = c.get("/api/config").json()
    checar(u"a tela nao recebe RECORTE_NO_CORPO (nem como caixa de texto em "
           u"«Outras»)", "RECORTE_NO_CORPO" not in api["chaves"],
           str(api["chaves"])[:160])
    c.post("/api/config", json={"valores": {"RECORTE_NO_CORPO": "0"}})
    _v = radai_config.ler_arquivo(arq)[1]
    checar(u"e um POST com RECORTE_NO_CORPO nao mexe no arquivo",
           _v.get("RECORTE_NO_CORPO") == "1", repr(_v.get("RECORTE_NO_CORPO")))
    p = radai_panel.PAGINA_CONFIG
    import radai_provenance_screen as _PS
    checar(u"e a Procedencia diz o valor, onde ela esta, e onde se ve se valeu",
           u"RECORTE_NO_CORPO=" in _PS.JS
           and u"fica no arquivo de configura" in _PS.JS
           and u"o log de cada task diz se ele valeu" in _PS.JS)
    import re as _re
    lig = _re.search(r"var LIGADESLIGA=\{(.*?)\};", p, _re.S)
    checar(u"  e ela NAO e um liga-desliga da tela",
           lig is not None and u"RECORTE_NO_CORPO:" not in lig.group(1),
           (u"chaves: %s" % u", ".join(_re.findall(r"(?m)^\s*([A-Z_]+):",
                                                   lig.group(1))))
           if lig else u"o `var LIGADESLIGA` mudou de forma?")
    _saidas = (u"INCLUIR_NV", u"INCLUIR_CADS", u"INCLUIR_MOOSE",
               u"INCLUIR_HNLNL", u"ENTREGAR_TS")

    def _oferece_chave_que_saiu(corpo):
        return [k for k in _saidas
                if _re.search(r"(?m)^\s*%s\s*:" % k, corpo or u"")]
    checar(u"o liga-desliga da tela nao oferece nenhuma chave que saiu na "
           u"v8.3", lig is not None and not _oferece_chave_que_saiu(
               lig.group(1)),
           str(_oferece_chave_que_saiu(lig.group(1)) if lig else u"?"))
    _velho_lig = (u" INCLUIR_HNLNL: 'grava os 20 níveis linfonodais "
                  u"cervicais (_lnl) em toda série do vigia — No «Rodar "
                  u"agora» quem decide é a linha dos níveis cervicais do "
                  u"Estudo Cabeça e Pescoço, e não esta chave. De fábrica "
                  u"desligado'\n")
    checar(u"  isca: o bloco de 25/09 (o HNLNL, que dizia a v8.2) e acusado",
           _hnlnl_diz_a_v82(_velho_lig.split(u"'")[1])
           and _oferece_chave_que_saiu(_velho_lig) == [u"INCLUIR_HNLNL"])
    import radai_batch as _rb
    _cfg_antes = dict(_rb._CFG)
    try:
        _rb._CFG.update({"incluir_hnlnl": True, "incluir_moose": True,
                         "incluir_cads": True})
        _mot, _ori = _rb.motores_da_serie(
            {"modalidade": "CT", "modo": "perso",
             "protocolos": ["cabeca_pescoco"], "tasks": {"hnlnl": 0}})
    finally:
        _rb._CFG.clear()
        _rb._CFG.update(_cfg_antes)
    checar(u"  e o lote confirma: com INCLUIR_HNLNL=1 e a linha desligada, "
           u"o «Rodar agora» nao roda os niveis (a chave nao manda ali)",
           _ori == "perso" and _mot.get("hnlnl") is False
           and not _mot.get("mse") and not _mot.get("cads"),
           u"%s %s" % (_ori, _mot))


class _Arvore(object):

    def __init__(self, html_):
        from html.parser import HTMLParser
        pilha, self.anc, self.classes = [], {}, set()
        VAZIAS = {"input", "br", "img", "meta", "link", "hr", "source",
                  "col", "area", "base", "wbr", "path", "circle", "rect",
                  "line", "polyline", "polygon", "use"}

        class _P(HTMLParser):
            def handle_starttag(s, tag, attrs):
                a = dict(attrs)
                cls = (a.get("class") or u"").split()
                self.classes.update(cls)
                if a.get("id"):
                    self.anc[a["id"]] = [set(x[1]) for x in pilha] + [set(cls)]
                if tag not in VAZIAS:
                    pilha.append((tag, cls))

            def handle_endtag(s, tag):
                for i in range(len(pilha) - 1, -1, -1):
                    if pilha[i][0] == tag:
                        del pilha[i:]
                        break

        import re as _re
        corpo = _re.sub(r"(?s)<script.*?</script>|<style.*?</style>", u"", html_)
        _P().feed(corpo)

    def dentro_de(self, id_, classe):
        return any(classe in c for c in self.anc.get(id_, ())[:-1])


def teste_o_registro_de_casos_e_secao_e_nao_dialogo():
    secao(u"config: o registro de casos e uma secao, fora do topo")
    arv = _Arvore(radai_panel.PAGINA_CONFIG)
    checar(u"o botao de exportar existe", "reg_bt" in arv.anc)
    checar(u"  e mora numa secao da pagina",
           arv.dentro_de("reg_bt", "ps-cx"), str(arv.anc.get("reg_bt")))
    checar(u"  fora do topo fixo (o contexto z:5 que o escondia)",
           not arv.dentro_de("reg_bt", "topo")
           and not arv.dentro_de("ps_registro", "topo"),
           str(arv.anc.get("reg_bt")))
    checar(u"e nao existe mais veu de dialogo", "reg-fundo" not in arv.classes
           and u".reg-fundo" not in radai_panel.CSS_REGISTRO)
    checar(u"a contagem esta no titulo do bloco Registro de casos",
           arv.dentro_de("reg_n", "cfg-sub"), str(arv.anc.get("reg_n")))
    pg = radai_panel.PAGINA_CONFIG
    i7 = pg.find(u'id="ps_limpar"')
    fim7 = pg.find(u"</section>", i7)
    checar(u"o registro mora na secao 7 (Diagnosticos e Registros), depois do "
           u"Diagnosticar",
           0 <= i7 < pg.find(u'id="btDiag"') < pg.find(u'id="reg_bt"') < fim7
           and u'id="ps_registro"' not in pg, u"%d %d" % (i7, fim7))
    checar(u"  e a secao 5 virou Estruturas e Protocolos",
           u'data-alvo="ps_estruturas"' in pg and u'id="ps_estruturas"' in pg
           and u'data-alvo="ps_registro"' not in pg)

    try:
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False, u"PULADO -- %s" % e)
        return
    reg = novo_temp(u"radai_p_reg_")
    caso = os.path.join(reg, "casos", "2026-09-20_ab12cd34")
    os.makedirs(caso)
    with io.open(os.path.join(caso, "caso.json"), "w", encoding="utf-8") as f:
        f.write(u'{"versao": 1}')
    guardado = os.environ.get("RADAI_REGISTRO_DIR")
    os.environ["RADAI_REGISTRO_DIR"] = reg
    try:
        arq = os.path.join(novo_temp(), "t.config")
        c = TestClient(_app_do_painel(arq), raise_server_exceptions=False)
        d = c.get("/api/registro").json()
        checar(u"a rota conta o caso", d.get("casos") == 1, str(d))
        checar(u"  e nao manda mais a pasta nem o tamanho (foram para o arranque)",
               "pasta" not in d and "tamanho_kb" not in d, str(sorted(d)))
        L = radai_panel.linhas_do_registro_para_arranque()
        t = u"\n".join(L)
        checar(u"a linha do arranque e ASCII",
               all(ord(ch) < 128 for ch in t), t[:120])
        checar(u"  e diz quantos, desde quando e onde",
               u"1 caso(s)" in t and u"2026-09-20" in t
               and os.path.basename(reg) in t, t[:200])
    finally:
        if guardado is None:
            os.environ.pop("RADAI_REGISTRO_DIR", None)
        else:
            os.environ["RADAI_REGISTRO_DIR"] = guardado


def teste_a_procedencia_tem_secao_propria():
    secao(u"config: a procedencia e informacao, no pe da tela")
    pagina = radai_panel.PAGINA_CONFIG
    arv = _Arvore(pagina)
    checar(u"a secao da procedencia SAIU da lista (e informacao, nao opcao)",
           "ps_procedencia" not in arv.anc)
    checar(u"  e as bibliotecas tambem (o TASKS fica no arquivo, sem tela)",
           u'id="cx_TASKS"' not in pagina and u"function bibliotecas(" not in pagina
           and "TASKS" in radai_panel.FORA_DA_TELA)
    pe = pagina[pagina.index(u'<footer class="cfg-docs">'):]
    pe = pe[:pe.index(u"</footer>")]
    checar(u"o pe da tela leva a /procedencia", u'href="/procedencia"' in pe)
    import radai_provenance_screen as _PS
    checar(u"e a Procedencia tem o bloco das bibliotecas",
           u'id="pr_bibliotecas"' in _PS.PAGINA and u"function prBib(" in _PS.JS)
    checar(u"  e diz que nada ali e configuravel",
           u"Nada aqui é configurável" in _PS.PAGINA)


def _chromium_da_maquina():
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if not os.path.isdir(base):
        return None
    for nome in sorted(os.listdir(base), reverse=True):
        if nome.startswith("chromium-"):
            for sub in ("chrome-win64", "chrome-win"):
                exe = os.path.join(base, nome, sub, "chrome.exe")
                if os.path.isfile(exe):
                    return exe
    return None


_MEDIR_REGISTRO = u"""() => {
  if (window.cfgMostrar) { window.cfgMostrar('ps_limpar'); }
  else {
    const s = document.getElementById('ps_limpar');
    if (s) s.classList.remove('fechado');
  }
  const b = document.getElementById('reg_bt');
  const bar = document.querySelector('.radai-tarefas');
  if (!b) return {erro: 'sem #reg_bt'};
  b.scrollIntoView({block: 'center'});
  const r = b.getBoundingClientRect();
  const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const cx = document.querySelector('.reg-cx') || document.getElementById('ps_limpar');
  const c = cx.getBoundingClientRect();
  let topoFim = 0;
  document.querySelectorAll('.topo, .rc-topo').forEach(function(t){
    const cs = getComputedStyle(t);
    if ((cs.position === 'sticky' || cs.position === 'fixed')
        && !t.contains(cx)) {
      const rt = t.getBoundingClientRect();
      if (rt.top <= 1) topoFim = Math.max(topoFim, rt.bottom);
    }
  });
  const x0 = Math.max(c.left, 0) + 4, x1 = Math.min(c.right, innerWidth) - 4;
  const y0 = Math.max(c.top, 0, topoFim) + 4, y1 = Math.min(c.bottom, innerHeight) - 4;
  const cobertos = [];
  for (let i = 0; i <= 6; i++) for (let j = 0; j <= 3; j++) {
    const x = x0 + (x1 - x0) * i / 6, y = y0 + (y1 - y0) * j / 3;
    const q = document.elementFromPoint(x, y);
    if (!q || !cx.contains(q))
      cobertos.push([Math.round(x), Math.round(y), q ? (q.id || q.className || q.tagName) : null]);
  }
  const rb = bar ? bar.getBoundingClientRect() : null;
  const vis = bar ? getComputedStyle(bar).display !== 'none' : false;
  return {e_o_botao: !!e && (e === b || b.contains(e)),
          no_ponto: e ? (e.id || e.className || e.tagName) : null,
          cobertos: cobertos.length, exemplo: cobertos.slice(0, 2),
          area_medida: [x0, y0, x1, y1].map(Math.round),
          caixa: [c.left, c.top, c.width, c.height].map(Math.round),
          barra_visivel: vis && !!rb && rb.width > 0 && rb.height > 0,
          botao: [r.left, r.top, r.width, r.height].map(Math.round),
          barra: rb ? [rb.left, rb.top, rb.width, rb.height].map(Math.round) : null};
}"""

_MEDIR_BLOCOS = u"""() => {
  const sec = (id) => { const e = document.getElementById(id);
                        return e ? e.closest('section') : null; };
  const dev = sec('f_DEVICE');
  const saidas = ['INCLUIR_NV','INCLUIR_CADS','INCLUIR_MOOSE','INCLUIR_HNLNL',
                  'ENTREGAR_TS','URL_VERSOES','TIMEOUT_NV_H']
                 .filter(function(k){ return !!document.getElementById('f_'+k); });
  return {
    tem_device: !!document.getElementById('f_DEVICE'),
    sem_suavizacao: !document.getElementById('f_SUAVIZAR_MM')
                    && !document.querySelector('#campos input[type=range]'),
    sem_dry_run: !document.getElementById('f_DRY_RUN'),
    sem_chaves_que_sairam: saidas.length === 0,
    chaves_que_sairam: saidas,
    trava_no_ritmo: sec('f_TRAVA_SEM_PULSO_MIN') !== null
                    && sec('f_TRAVA_SEM_PULSO_MIN') === sec('f_HEARTBEAT_MIN')
                    && sec('f_TRAVA_RAM_PCT') === sec('f_HEARTBEAT_MIN'),
    sem_idioma_texto: !document.getElementById('f_IDIOMA'),
    lock_parado_no_ritmo: sec('f_LOCK_PARADO_MIN') !== null
                          && sec('f_LOCK_PARADO_MIN') === sec('f_HEARTBEAT_MIN'),
    favorita_nas_pastas: sec('f_PASTA_FAVORITA') !== null
                         && sec('f_PASTA_FAVORITA') === sec('f_OUT_DIR'),
    estrela_na_favorita: (function(){
      const b = document.getElementById('cfg_fav_estrela'),
            c = document.getElementById('f_PASTA_FAVORITA');
      return !!b && !!c && b.getAttribute('data-ui-fav') === 'f_PASTA_FAVORITA'
             && b.closest('.campo') === c.closest('.campo') && !!b._uiFav
             && !!document.getElementById('fav_procurar'); })(),
    processamento_so_device: !!dev && dev.id === 'ps_processamento'
                             && dev.querySelectorAll('input,select').length === 1,
    sem_varredura: !document.getElementById('f_ROOT')
                   && !document.getElementById('f_MODALITIES')
                   && !document.getElementById('f_DAYS_BACK')
                   && !document.getElementById('f_TASKS')
                   && !document.getElementById('fpicker'),
    min_slices_no_ritmo: sec('f_MIN_SLICES') !== null
                         && sec('f_MIN_SLICES') === sec('f_HEARTBEAT_MIN'),
    sem_outras: !document.getElementById('ps_outras'),
    topo_posicao: (function(){ const t = document.querySelector('.topo');
                               return t ? getComputedStyle(t).position : null; })(),
    links_crus: Array.prototype.filter.call(document.querySelectorAll('a.bt'),
      function(a){ const c = getComputedStyle(a);
        return c.textDecorationLine.indexOf('underline') >= 0
               || c.color === 'rgb(0, 0, 238)'; })
      .map(function(a){ return a.getAttribute('href') })
  };
}"""


_MEDIR_SO_CARTOES = u"""async () => {
  const espera = (ms) => new Promise(function(r){ setTimeout(r, ms) });
  const vis = (e) => !!e && e.getClientRects().length > 0
                     && getComputedStyle(e).visibility !== 'hidden';
  const secoes = () => Array.prototype.filter.call(
    document.querySelectorAll('section.ps-cx'), vis).map(function(e){ return e.id });
  const cartoes = Array.prototype.filter.call(
    document.querySelectorAll('a.cfg-card[data-alvo]'), vis).length;
  const aviso0 = vis(document.getElementById('cfgAviso'));
  const antes = secoes();
  const c = document.querySelector('a.cfg-card[data-alvo="ps_ritmo"]');
  if (c) c.click();
  await espera(300);
  const depois = secoes();
  const atual = c ? c.getAttribute('aria-current') : null;
  const aviso1 = vis(document.getElementById('cfgAviso'));
  const g = document.querySelector('a.cfg-card[data-alvo="ps_geral"]');
  if (g) g.click();
  await espera(300);
  return {cartoes: cartoes, antes: antes, depois: depois, atual: atual,
          aviso0: aviso0, aviso1: aviso1, geral: secoes(),
          aviso2: vis(document.getElementById('cfgAviso'))};
}"""


_MEDIR_CARTOES = u"""async () => {
  const espera = (ms) => new Promise(function(r){ setTimeout(r, ms) });
  const cartoes = Array.prototype.slice.call(
    document.querySelectorAll('a.cfg-card[data-alvo]'));
  const nums = Array.prototype.map.call(document.querySelectorAll('.ps-num'),
    function(e){ return e.textContent.trim(); });
  const topo = document.querySelector('.topo');
  const out = [];
  for (const c of cartoes) {
    const id = c.getAttribute('data-alvo');
    const s = document.getElementById(id);
    if (s) s.classList.add('fechado');
    c.click();
    let ult = -1;
    for (let k = 0; k < 40 && ult !== scrollY; k++) { ult = scrollY; await espera(120); }
    const cab = s ? s.querySelector('.ps-cab') : null;
    const r = cab ? cab.getBoundingClientRect() : null;
    const tb = (topo && getComputedStyle(topo).position === 'sticky')
               ? topo.getBoundingClientRect().bottom : 0;
    out.push({id: id, existe: !!s,
              aberta: !!s && !s.classList.contains('fechado'),
              visivel: !!r && r.top >= tb - 2 && r.top < innerHeight,
              num_igual: !!s && c.querySelector('.n').textContent.trim()
                         === s.querySelector('.ps-num').textContent.trim()});
    window.scrollTo(0, 0);
  }
  let aplicou = null;
  const bt = document.getElementById('procAplicar');
  const f = document.getElementById('f_DEVICE');
  if (bt && f) { bt.click(); await espera(200); aplicou = f.value; }
  const diag = {btDiag: !!document.getElementById('btDiag'),
                btOtim: !!document.getElementById('btOtimPlano'),
                iframe: !!document.getElementById('if_diag')
                        || !!document.getElementById('mod_diag')};
  return {n: cartoes.length, cartoes: out, nums: nums, recomendacao: aplicou,
          diag: diag};
}"""


def _servir(app, porta):
    import threading
    import uvicorn
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=porta,
                                        log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(200):
        if getattr(srv, "started", False):
            break
        time.sleep(0.05)
    return srv, th


def medir_config_no_navegador(pagina_config=None):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    chrome = _chromium_da_maquina()
    if not chrome:
        return None
    arq = os.path.join(novo_temp(), "t.config")
    with io.open(arq, "w", encoding="utf-8") as f:
        f.write(u"# teste\nROOT=\nDRY_RUN=1\nDEVICE=cpu\n")
    guardado = radai_panel.PAGINA_CONFIG
    if pagina_config is not None:
        radai_panel.PAGINA_CONFIG = pagina_config
    _laudo = {"escolhido": "cpu", "resolve_em": "cpu", "gpu": None,
              "cpu": {"nucleos": 4}, "aviso": "", "estimativa": {},
              "recomendacao": {"device": "auto", "porque": "teste",
                               "ganho": "", "risco": "", "ja_esta": False}}
    reg = os.environ.get("RADAI_REGISTRO_DIR")
    os.environ["RADAI_REGISTRO_DIR"] = novo_temp(u"radai_p_reg_")
    srv = th = None
    fora = {}
    try:
        app = _app_do_painel(arq)
        app.add_api_route("/api/processamento", lambda: _laudo, methods=["GET"])
        porta, _aviso = porta_de_teste(8798)
        if _aviso:
            print(u"  AVISO  %s" % _aviso)
        srv, th = _servir(app, porta)
        with sync_playwright() as p:
            nav = p.chromium.launch(executable_path=chrome)
            try:
                for rot, vp in (("1280", {"width": 1280, "height": 800}),
                                ("375", {"width": 375, "height": 812})):
                    ctx = nav.new_context(viewport=vp)
                    pg = ctx.new_page()
                    pg.goto("http://127.0.0.1:%d/config" % porta,
                            wait_until="networkidle")
                    for _sel in ("#f_DEVICE", ".radai-tarefas"):
                        try:
                            pg.wait_for_selector(_sel, state="attached",
                                                 timeout=15000)
                        except Exception:
                            pass
                    pg.wait_for_timeout(500)
                    if rot == "1280":
                        fora["so_cartoes"] = pg.evaluate(_MEDIR_SO_CARTOES)
                    fora["blocos_" + rot] = pg.evaluate(_MEDIR_BLOCOS)
                    fora["registro_" + rot] = pg.evaluate(_MEDIR_REGISTRO)
                    if rot == "1280":
                        try:
                            pg.wait_for_selector("#procLaudo .proc-rec",
                                                 state="attached", timeout=20000)
                        except Exception:
                            pass
                        fora["cartoes_1280"] = pg.evaluate(_MEDIR_CARTOES)
                    ctx.close()
            finally:
                nav.close()
    finally:
        radai_panel.PAGINA_CONFIG = guardado
        if srv is not None:
            srv.should_exit = True
            th.join(10)
        if reg is None:
            os.environ.pop("RADAI_REGISTRO_DIR", None)
        else:
            os.environ["RADAI_REGISTRO_DIR"] = reg
    return fora


def teste_config_no_navegador():
    secao(u"config no navegador: registro na frente, blocos no lugar")
    m = medir_config_no_navegador()
    if m is None:
        print(u"  PULADO  sem Playwright ou sem Chromium nesta maquina")
        return
    for rot in ("1280", "375"):
        r = m.get("registro_" + rot) or {}
        checar(u"[%s px] o botao de exportar recebe o clique (nada por cima)" % rot,
               r.get("e_o_botao") is True, str(r))
        checar(u"[%s px] e nenhum ponto da caixa do registro fica sob outra coisa"
               % rot, r.get("cobertos") == 0
               and (r.get("area_medida") or [0, 0, 0, 0])[3]
               - (r.get("area_medida") or [0, 0, 0, 0])[1] > 20, str(r))
        b = m.get("blocos_" + rot) or {}
        checar(u"[%s px] o formulario foi montado" % rot, b.get("tem_device"), str(b))
        for k, rotulo in (("sem_suavizacao", u"sem cursor de suavizacao"),
                          ("sem_dry_run", u"sem DRY_RUN"),
                          ("sem_chaves_que_sairam",
                           u"nenhum campo das chaves que sairam na v8.3"),
                          ("trava_no_ritmo",
                           u"as chaves do travamento no ritmo, com o batimento"),
                          ("sem_idioma_texto",
                           u"o IDIOMA nao vira caixa de texto (FORA_DA_TELA)"),
                          ("lock_parado_no_ritmo", u"LOCK_PARADO_MIN no ritmo do vigia"),
                          ("favorita_nas_pastas", u"PASTA_FAVORITA nas pastas"),
                          ("estrela_na_favorita",
                           u"a PASTA_FAVORITA tem a estrela da casca, ligada, ao "
                           u"lado do Procurar (o explorador com o Mapear)"),
                          ("processamento_so_device",
                           u"o Processamento e so o DEVICE (v8.3)"),
                          ("sem_varredura",
                           u"ROOT, MODALITIES, DAYS_BACK e TASKS fora da tela (v8.3)"),
                          ("min_slices_no_ritmo",
                           u"o MIN_SLICES no ritmo da automacao"),
                          ("sem_outras",
                           u"nenhuma chave caiu em «Outras»")):
            checar(u"[%s px] %s" % (rot, rotulo), b.get(k) is True, str(b))
        checar(u"[%s px] nenhum link-botao com a cara do navegador" % rot,
               b.get("links_crus") == [], str(b.get("links_crus")))
    sc = m.get("so_cartoes") or {}
    checar(u"[1280 px] a pagina abre so com os oito cartoes, nenhuma secao a vista",
           sc.get("cartoes") == 8 and sc.get("antes") == [], str(sc))
    checar(u"  e sem o aviso do Reiniciar", sc.get("aviso0") is False, str(sc))
    checar(u"  o cartao do Ritmo mostra so a secao dele, e fica marcado",
           sc.get("depois") == [u"ps_ritmo"] and sc.get("atual") == u"true",
           str(sc))
    checar(u"  e o aviso do Reiniciar vem junto (secao que se salva)",
           sc.get("aviso1") is True, str(sc))
    checar(u"  o da Geral troca: mostra a Geral e esconde o Ritmo, sem o aviso",
           sc.get("geral") == [u"ps_geral"] and sc.get("aviso2") is False, str(sc))
    cc = m.get("cartoes_1280") or {}
    checar(u"[1280 px] ha os oito cartoes de funcao", cc.get("n") == 8, str(cc)[:200])
    for c in cc.get("cartoes") or []:
        checar(u"[1280 px] o cartao `%s` abre a secao e leva ate ela, fora do "
               u"topo fixo" % c.get("id"),
               c.get("existe") and c.get("aberta") and c.get("visivel"), str(c))
        checar(u"  e o numero dele e o da secao", c.get("num_igual") is True,
               str(c))
    _nums = cc.get("nums") or []
    checar(u"[1280 px] as secoes sao numeradas 1..N, sem repetir",
           _nums == [str(i) for i in range(1, len(_nums) + 1)] and len(_nums) >= 8,
           str(_nums))
    checar(u"[1280 px] o «Usar este valor» da recomendacao troca o DEVICE "
           u"para auto (ele procurava `[name=DEVICE]`, e o campo tem `id`)",
           cc.get("recomendacao") == "auto", str(cc.get("recomendacao")))
    _dg = cc.get("diag") or {}
    checar(u"[1280 px] a secao do Diagnosticar tem o botao dele e nao tem "
           u"mais o Otimizar, e o iframe do log do ambiente nao voltou",
           _dg.get("btDiag") is True and _dg.get("btOtim") is False
           and _dg.get("iframe") is False, str(_dg))
    checar(u"[1280 px] o topo fica colado (o Salvar sempre a mao)",
           (m.get("blocos_1280") or {}).get("topo_posicao") == "sticky",
           str((m.get("blocos_1280") or {}).get("topo_posicao")))
    checar(u"[375 px] e no celular ele rola junto, e nao cobre a secao",
           (m.get("blocos_375") or {}).get("topo_posicao") not in
           ("sticky", "fixed", None),
           str((m.get("blocos_375") or {}).get("topo_posicao")))
    r = m.get("registro_1280") or {}
    rb = r.get("barra") or [0, 0, 0, 0]
    checar(u"[1280 px] com a barra direita visivel, a direita",
           r.get("barra_visivel") is True and rb[0] > 1280 / 2,
           str(r))
    isca = radai_panel.PAGINA_CONFIG.replace(
        u"  x.hidden = !s || (x !== s && !(x.id === 'ps_outras' && id === 'ps_pastas'));",
        u"  x.hidden = false;")
    checar(u"  (isca) a troca existe no fonte", isca != radai_panel.PAGINA_CONFIG)
    sem_estrela = isca.replace(u" cfgFavoritaEstrela();\n", u"\n", 1)
    checar(u"  (isca) a chamada da estrela existe no fonte", sem_estrela != isca)
    mi = medir_config_no_navegador(sem_estrela) or {}
    si = mi.get("so_cartoes") or {}
    checar(u"  (isca) sem o esconder, o cartao deixa as outras secoes a vista",
           len(si.get("depois") or []) > 1, str(si)[:300])
    checar(u"  (isca) sem ligar a estrela, a medida da favorita reprova",
           (mi.get("blocos_1280") or {}).get("estrela_na_favorita") is False,
           str((mi.get("blocos_1280") or {}).get("estrela_na_favorita")))


def _sessao_inventada():
    vig = os.getpid()

    def _p(pid, exe, ppid=100, janela=False, caminho=u"", sessao=1, mem=40):
        return {"pid": pid, "ppid": ppid, "exe": exe,
                "nome": exe[:-4] if exe.lower().endswith(".exe") else exe,
                "caminho": caminho, "sessao": sessao, "janela": janela,
                "mem_mb": mem}
    return [_p(100, "explorer.exe", ppid=50, janela=True),
            _p(200, "cmd.exe", janela=True),
            _p(vig, "python.exe", ppid=200),
            _p(300, "python.exe", ppid=vig),
            _p(400, "OneDrive.exe", mem=120),
            _p(700, "Foo.exe", janela=True, mem=80),
            _p(600, "chrome.exe", janela=True, mem=900),
            _p(1000, "Vitrea.exe", janela=True, mem=2000)]


class _Dublagem(object):
    def __init__(self, trocas):
        self.trocas, self.velhos = trocas, []

    def __enter__(self):
        for mod, nome, valor in self.trocas:
            self.velhos.append((mod, nome, getattr(mod, nome)))
            setattr(mod, nome, valor)
        return self

    def __exit__(self, *a):
        for mod, nome, valor in reversed(self.velhos):
            setattr(mod, nome, valor)
        return False


_CONFERENCIA_FIXA = {"secoes": [{"titulo": u"Pesos", "itens": [
    {"nome": u"total_v3", "ok": True, "valor": u"ok", "detalhe": u"",
     "grave": True, "nota": False},
    {"nome": u"trunk_cavities", "ok": False, "valor": u"ausente",
     "detalhe": u"", "grave": True, "nota": False}]}],
    "resumo": {"ok": 1, "faltam": 1, "avisos": 0}, "segundos": 0.1}
_LAUDO_FIXO = {"memoria": {"total_mb": 16000, "livre_mb": 5000,
                           "usada_mb": 11000, "pct": 69},
               "aplicacoes": [], "disco": [], "ganhos": []}


def _dublagem_do_limpador():
    import radai_cleaner as LP
    import radai_station_check as CE
    return _Dublagem([
        (LP, "processos", _sessao_inventada),
        (LP, "laudo", lambda device=None: dict(_LAUDO_FIXO)),
        (LP, "ler_em_uso", lambda caminho=None: {}),
        (CE, "conferir", lambda root=u"", porta=0: dict(_CONFERENCIA_FIXA))])


def _app_com_registro(caminho_cfg, linhas):
    from fastapi import FastAPI
    padroes = _defaults_do_vigia()
    app = FastAPI()
    radai_panel.montar(app, ler_vigia=lambda: {}, config={
        "caminho": caminho_cfg, "chaves": list(padroes), "padroes": padroes,
        "modelo": u"", "em_uso": (lambda: dict(padroes)),
        "registrar": linhas.append})
    return app


_ROTAS_DO_OTIMIZAR = ("/api/otimizar/plano", "/api/otimizar/aplicar",
                      "/api/otimizar/restaurar", "/api/limpador",
                      "/api/limpador/parar", "/api/limpador/liberar")


def teste_as_rotas_de_diagnosticar():
    secao(u"config: a rota de Diagnosticar, e as do Otimizar sairam")
    try:
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False, u"PULADO -- %s" % e)
        return
    arq = os.path.join(novo_temp(), "t.config")
    with io.open(arq, "w", encoding="utf-8") as f:
        f.write(u"# teste\nROOT=\nDEVICE=auto\n")
    velho = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = novo_temp(u"radai_p_lad_")
    linhas = []
    try:
        with _dublagem_do_limpador():
            app = _app_com_registro(arq, linhas)
            rotas = set(getattr(r, "path", u"") for r in app.routes)
            checar(u"as rotas do Otimizar e do limpador nao estao montadas",
                   "/api/diagnosticar" in rotas
                   and not (set(_ROTAS_DO_OTIMIZAR) & rotas),
                   sorted(set(_ROTAS_DO_OTIMIZAR) & rotas))
            c = TestClient(app, raise_server_exceptions=False)
            d = c.post("/api/diagnosticar").json()
            checar(u"o Diagnosticar devolve o resumo da conferencia",
                   d.get("resumo") == {"ok": 1, "faltam": 1, "avisos": 0}, d)
            checar(u"  e escreve o relatorio no log do vigia, do comeco ao fim",
                   linhas and u"começo" in linhas[0] and u"fim" in linhas[-1]
                   and any(u"[FALTA]" in x for x in linhas), linhas[:4])
            checar(u"  e o relatorio nao fala mais do Otimizar nem de servico",
                   not any(u"Otimizar" in x or u"servi" in x for x in linhas),
                   [x for x in linhas if u"Otimizar" in x or u"servi" in x])
            checar(u"  e uma rota do Otimizar pedida responde que nao existe",
                   c.post("/api/otimizar/plano").status_code in (404, 405))
            from fastapi import FastAPI
            padroes = _defaults_do_vigia()
            app2 = FastAPI()
            radai_panel.montar(app2, ler_vigia=lambda: {}, config={
                "caminho": arq, "chaves": list(padroes), "padroes": padroes,
                "modelo": u"", "em_uso": (lambda: dict(padroes))})
            n1 = len(linhas)
            TestClient(app2, raise_server_exceptions=False).post(
                "/api/diagnosticar")
            checar(u"ISCA: sem `registrar`, nenhuma linha chega ao log",
                   len(linhas) == n1)
    finally:
        if velho is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = velho


_AJUDA_JS = u"""
  const espera = (ms) => new Promise(function(r){ setTimeout(r, ms) });
  const ate = async (f, ms) => { for (let i = 0; i < ms / 100; i++) {
      if (f()) return true; await espera(100); } return false; };
  const out = {};
  const txt = (id) => (document.getElementById(id) || {}).textContent || '';
"""

_FLUXO_DIAG = u"""
  if (window.uiDireita) window.uiDireita('1');
  out.recolhida_antes = document.documentElement.classList.contains('dir-recolhida')
                        || document.documentElement.classList.contains('dir-fechando');
  const card = document.querySelector('a.cfg-card[data-alvo="ps_limpar"]');
  if (card) card.click();
  await espera(600);
  document.getElementById('btDiag').click();
  out.diag_ok = await ate(() => /em ordem/.test(txt('cfBarra')), 15000);
  out.barra = txt('cfBarra');
  out.aberta_depois = !document.documentElement.classList.contains('dir-recolhida');
  out.falta_na_tela = /trunk_cavities/.test(txt('cfRel'));
  out.ok_fora_da_tela = !/total_v3/.test(txt('cfRel'));
  const secao = document.getElementById('ps_limpar');
  out.botoes = secao ? Array.prototype.map.call(
      secao.querySelectorAll('button'), function(b){
        return (b.textContent || '').trim(); }) : null;
  return out;
"""


def medir_diagnosticar_no_navegador(prints=None):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    chrome = _chromium_da_maquina()
    if not chrome:
        return None
    arq = os.path.join(novo_temp(), "t.config")
    with io.open(arq, "w", encoding="utf-8") as f:
        f.write(u"# teste\nROOT=\nDEVICE=auto\n")
    velho = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = novo_temp(u"radai_p_lad_")
    linhas = []
    srv = th = None
    fora = {}
    try:
        with _dublagem_do_limpador():
            app = _app_com_registro(arq, linhas)
            porta, _aviso = porta_de_teste(8799)
            srv, th = _servir(app, porta)
            with sync_playwright() as p:
                nav = p.chromium.launch(executable_path=chrome)
                try:
                    ctx = nav.new_context(viewport={"width": 1280, "height": 860})
                    pg = ctx.new_page()
                    if prints:
                        os.makedirs(prints, exist_ok=True)
                    pg.goto("http://127.0.0.1:%d/config" % porta,
                            wait_until="networkidle")
                    try:
                        pg.wait_for_selector("#btDiag", state="attached",
                                             timeout=15000)
                    except Exception:
                        pass
                    for passo, nome in ((_FLUXO_DIAG, "1_diagnosticar"),):
                        fora.update(pg.evaluate(
                            u"async () => {" + _AJUDA_JS + passo + u"}") or {})
                        if prints:
                            pg.screenshot(path=os.path.join(prints, nome + ".png"))
                    ctx.close()
                finally:
                    nav.close()
    finally:
        if srv is not None:
            srv.should_exit = True
            th.join(10)
        if velho is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = velho
    fora["linhas"] = linhas
    return fora


def teste_diagnosticar_no_navegador():
    secao(u"config no navegador: Diagnosticar, sem o Otimizar")
    m = medir_diagnosticar_no_navegador()
    if m is None:
        print(u"  PULADO  sem Playwright ou sem Chromium nesta maquina")
        return
    checar(u"a barra estava recolhida antes do clique (o cenario da medida)",
           m.get("recolhida_antes") is True, m.get("recolhida_antes"))
    checar(u"o Diagnosticar responde com o resumo", m.get("diag_ok") is True,
           m.get("barra"))
    checar(u"  e ABRE a barra da direita, onde o log mostra o relatorio",
           m.get("aberta_depois") is True, m.get("aberta_depois"))
    checar(u"  e ao lado do botao fica so o que falta (e nao o que esta em "
           u"ordem)", m.get("falta_na_tela") is True
           and m.get("ok_fora_da_tela") is True, m)
    checar(u"  e o relatorio foi para o log do vigia",
           any(u"diagnostico: [FALTA]" in x for x in m.get("linhas") or []),
           (m.get("linhas") or [])[:3])
    checar(u"a secao abre com o Diagnosticar e nao tem o Otimizar (o Otimizar "
           u"saiu; o registro de casos vem depois, na mesma secao)",
           (m.get("botoes") or [])[:1] == [u"Diagnosticar"]
           and u"Otimizar" not in (m.get("botoes") or []), m.get("botoes"))


def teste_o_cartao_de_atualizar_da_o_link_permanente():
    secao(u"o cartao de atualizar da o link permanente")
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
    except ImportError as e:
        checar(u"a rota responde (fastapi ausente)", True, str(e))
        return
    import radai_version as RV

    def _config(url, no_config=None):
        velha = RV.URL_VERSOES
        RV.URL_VERSOES = url
        try:
            app = FastAPI()
            radai_panel.montar(app, None, {"em_uso": (
                {"URL_VERSOES": no_config} if no_config is not None else {})})
            return TestClient(app).get("/config").text
        finally:
            RV.URL_VERSOES = velha

    gh = u"https://github.com/drhenriquebraga/local-suite/releases"
    checar(u"a constante de fabrica e a do repositorio do projeto",
           RV.URL_VERSOES == gh, RV.URL_VERSOES)
    t = _config(gh)
    link = RV.link_do_instalador(gh)
    checar(u"o link e o permanente (`/releases/latest/download/`)",
           u"/releases/latest/download/" in link
           and link.endswith(u"_SETUP_LATEST.zip"), link)
    checar(u"  e a pagina o serve, no botao `lkInst`",
           (u'id="lkInst"' in t) and (u'href="%s"' % link) in t, link)
    checar(u"  e sem o aviso de repositorio privado: o repositorio e "
           u"publico, e o link baixa sem conta",
           u"Enquanto o repositório for privado" not in t)

    def _sobra(texto):
        return [m for m in (u"@BT_INSTALADOR@", u"@AVISO_INSTALADOR@",
                            u"@URL_VERSOES@", u"@BT_ATU_AGORA@") if m in texto]
    checar(u"  e nenhum marcador sobra na pagina servida", not _sobra(t),
           str(_sobra(t)))
    checar(u"  (isca) um marcador que sobrasse seria acusado",
           bool(_sobra(t + u"@BT_INSTALADOR@")))
    t2 = _config(u"https://espelho.hospital.local/radai/versoes")
    checar(u"um espelho que nao e do GitHub NAO ganha botao nem aviso",
           u'id="lkInst"' not in t2
           and u"Enquanto o repositório for privado" not in t2
           and not _sobra(t2), str(_sobra(t2)))
    t3 = _config(u"")
    checar(u"  e o URL_VERSOES vazio tambem nao",
           u'id="lkInst"' not in t3 and not _sobra(t3), str(_sobra(t3)))
    t4 = _config(u"https://espelho.hospital.local/radai/versoes",
                 no_config=gh)
    checar(u"  isca: o `URL_VERSOES` do config nao manda no cartao",
           u'id="lkInst"' not in t4
           and u'href="https://espelho.hospital.local/radai/versoes"' in t4,
           str(_sobra(t4)))
    real = RV.para_a_tela
    try:
        RV.para_a_tela = lambda: {"estado": "nova", "nova": True,
                                  "publicada": u"9.9", "aqui": u"8.7",
                                  "link": link}
        t5 = _config(gh)
        RV.para_a_tela = lambda: {"estado": "atual", "nova": False,
                                  "publicada": u"", "aqui": u"8.7", "link": u""}
        t6 = _config(gh)
    finally:
        RV.para_a_tela = real
    checar(u"com versao nova, o cartao tem o «Atualizar agora», que chama a "
           u"atualizacao com um clique", u'id="btAtuAgora"' in t5
           and u"window.radaiAtualizarAgora()" in t5 and not _sobra(t5),
           str(_sobra(t5)))
    checar(u"  e o instalador vira o caminho a mao, em botao secundario",
           u'class="bt sec" id="lkInst"' in t5)
    checar(u"  (isca) sem versao nova o «Atualizar agora» nao aparece, e o "
           u"instalador continua o principal", u'id="btAtuAgora"' not in t6
           and u'class="bt pri" id="lkInst"' in t6)
    checar(u"o balao diz que «Atualizar agora» baixa e reabre por ato, e nao "
           u"que a pessoa baixa e roda o instalador sozinha",
           u"baixa e roda o instalador quando voc&ecirc; clica" in t5
           and u"Voc&ecirc; escolhe, baixa e roda" not in t5)


def teste_o_primeiro_uso_grava_tps_e_pasta():
    secao(u"o primeiro uso: sem a pergunta do TPS, e a pasta favorita opcional")
    import radai_primeiro_uso as PU
    base = novo_temp(u"radai_p_pu_")
    cfg = os.path.join(base, "radai_watcher.config")
    io.open(cfg, "w", encoding="utf-8").write(
        u"# a pasta do share\nROOT=\n\n# idioma da tela\nIDIOMA=\nPASTA_FAVORITA=\n")
    checar(u"sem TPS_DESTINO no arquivo, o primeiro uso nao rodou",
           PU.estado(cfg)["feito"] is False)
    ok, r = PU.gravar(cfg, u"")
    texto = io.open(cfg, encoding="utf-8").read()
    checar(u"«Salvar e continuar» com o campo vazio avanca e grava o padrao "
           u"Eclipse / Monaco, com os comentarios preservados",
           ok and u"TPS_DESTINO=eclipse" in texto and u"# a pasta do share" in texto,
           texto)
    checar(u"  e o estado diz que o primeiro uso rodou",
           PU.estado(cfg)["feito"] is True and PU.estado(cfg)["tps"] == u"eclipse")
    checar(u"  e nao mexe no ROOT nem na favorita",
           u"ROOT=\n" in texto and u"PASTA_FAVORITA=\n" in texto, texto)
    io.open(cfg, "w", encoding="utf-8").write(u"TPS_DESTINO=monaco\nPASTA_FAVORITA=\n")
    ok, r = PU.gravar(cfg, u"", pular=True)
    checar(u"a estacao que ja escolheu continua com a escolha (o pular nao troca "
           u"Xio / Focal pelo padrao)",
           ok and PU.estado(cfg)["tps"] == u"monaco" and r.get("mudou") == [], repr(r))
    pasta = os.path.join(base, u"share")
    os.makedirs(pasta)
    ok, r = PU.gravar(cfg, pasta)
    checar(u"pasta que existe e le: vira a PASTA_FAVORITA, e o ROOT nao entra",
           ok and PU.estado(cfg)["pasta"] == pasta
           and u"ROOT" not in io.open(cfg, encoding="utf-8").read(), repr(r))
    ok, r = PU.gravar(cfg, os.path.join(base, u"nao_existe"))
    checar(u"pasta que nao existe: recusa com o codigo do laudo, e nada muda",
           not ok and (r.get("laudo") or {}).get("codigo") == u"nao_existe"
           and PU.estado(cfg)["pasta"] == pasta, repr(r))
    ok, r = PU.gravar(cfg, u"", pular=True)
    checar(u"«Pular por agora» nao apaga a favorita que ja existe",
           ok and PU.estado(cfg)["pasta"] == pasta, repr(r))
    ok, r = PU.gravar(cfg, u"")
    checar(u"«Salvar e continuar» com o campo esvaziado apaga a favorita",
           ok and PU.estado(cfg)["pasta"] == u"", repr(r))
    linha = PU.linha_do_registro({"tps": u"eclipse", "pasta": pasta,
                                  "mudou": ["PASTA_FAVORITA", "TPS_DESTINO"]})
    checar(u"a linha do log diz o TPS gravado e nao leva o caminho da favorita "
           u"(a pasta pode ter nome de paciente)",
           u"TPS_DESTINO=eclipse (Eclipse / Monaco" in linha and pasta not in linha
           and u"share" not in linha, linha)

    try:
        from fastapi import FastAPI
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False, u"PULADO -- %s" % e)
        return
    io.open(cfg, "w", encoding="utf-8").write(u"# x\nROOT=\n")
    app = FastAPI()
    log, rec = [], []
    PU.montar(app, cfg, registrar=log.append, recarregar=lambda: rec.append(1))
    c = TestClient(app, raise_server_exceptions=False)
    checar(u"GET /api/primeiro-uso diz que o primeiro uso nao rodou",
           c.get(u"/api/primeiro-uso").json().get("feito") is False)
    r = c.post(u"/api/primeiro-uso", json={u"pasta": os.path.join(base, u"nao_existe")})
    checar(u"POST com pasta que nao existe: 400, com o laudo, e o TPS nao e gravado",
           r.status_code == 400 and (r.json().get("laudo") or {}).get("codigo")
           == u"nao_existe" and PU.estado(cfg)["feito"] is False, r.status_code)
    r = c.post(u"/api/primeiro-uso", json={u"pular": True})
    checar(u"POST de pular: grava o padrao, registra no log e pede a recarga",
           r.status_code == 200 and PU.estado(cfg)["tps"] == u"eclipse"
           and any(u"primeiro uso: TPS_DESTINO=eclipse" in l for l in log)
           and rec == [1], u"%s %r %r" % (r.status_code, log, rec))
    r = c.post(u"/api/primeiro-uso", json={u"pular": u"sim"})
    checar(u"  e so o true literal pula (texto vira o salvar com o campo vazio)",
           r.status_code == 200 and r.json().get("pulou") is False, r.text)
    tela = c.get(u"/primeiro-uso").text
    checar(u"a tela do primeiro uso nao pergunta mais o TPS: a pasta, o pular e o "
           u"salvar", all(m in tela for m in (u'id="pu_pasta"', u'id="pu_pular"',
                                               u'id="pu_salvar"'))
           and u"data-tps=" not in tela and u'id="pu_root"' not in tela)
    checar(u"  o campo da favorita tem a estrela da casca e o Procurar abre o "
           u"explorador da casca (com o Mapear nova unidade de rede)",
           u'data-ui-fav="pu_pasta"' in tela and u"window.uiExplorador({" in tela
           and u"Mapear nova unidade de rede" in tela
           and u"fetch('/api/pastas'" not in tela, u"")
    import radai_ui as _ui
    _real = _ui.botao_favorita
    try:
        _ui.botao_favorita = lambda campo: u""
        sem_estrela = PU.pagina()
    finally:
        _ui.botao_favorita = _real
    checar(u"  (isca) com a casca sem a estrela, a pagina perde a estrela e a "
           u"checagem acusa", u'data-ui-fav="pu_pasta"' not in sem_estrela
           and u'id="pu_pasta"' in sem_estrela)

    wat = io.open(_componentes.fonte("app/radai_watcher.py"), encoding="utf-8").read()
    import check_project as _cp
    falta = _cp._chave_nova_nas_tres_casas("TPS_DESTINO", wat)
    checar(u"TPS_DESTINO esta nas tres casas do vigia", not falta, u"; ".join(falta))
    c3 = _cp._config_do_vigia(wat)
    checar(u"  e nasce vazio (nao escolhido) nas duas que tem valor",
           c3["texto"].get("TPS_DESTINO") == u""
           and c3["defaults"].get("TPS_DESTINO") == u"")
    checar(u"a tela de config nao mostra a chave como caixa de texto",
           u"TPS_DESTINO" in radai_panel.FORA_DA_TELA)
    checar(u"  e oferece «Configurar pasta favorita» na secao Geral (o refazer "
           u"saiu)", u'href="/primeiro-uso?de=/config"' in radai_panel.PAGINA_CONFIG
           and u"Configurar pasta favorita" in radai_panel.PAGINA_CONFIG
           and u"Refazer o primeiro uso" not in radai_panel.PAGINA_CONFIG)
    import radai_consent as _cs
    checar(u"o aceite leva ao primeiro uso quando ele nao rodou",
           u"'/primeiro-uso?de=' + encodeURIComponent(destino)" in _cs.PAGINA_ACEITE
           and u"pu.feito === false" in _cs.PAGINA_ACEITE)


def teste_a_porta_leva_ao_primeiro_uso_sem_tps():
    secao(u"a porta leva ao primeiro uso enquanto o TPS de destino nao foi escolhido")
    import radai_primeiro_uso as PU
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False, u"PULADO -- %s" % e)
        return
    base = novo_temp(u"radai_p_pu_porta_")
    cfg = os.path.join(base, "radai_watcher.config")
    io.open(cfg, "w", encoding="utf-8").write(u"ROOT=\nTPS_DESTINO=\n")
    app = FastAPI()

    @app.get(u"/", response_class=HTMLResponse)
    def _porta():
        return u"PORTA"

    @app.get(u"/config", response_class=HTMLResponse)
    def _cfg():
        return u"CONFIG"

    @app.get(u"/suite", response_class=HTMLResponse)
    def _suite():
        return u"PORTA"

    PU.montar(app, cfg)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get(u"/suite", follow_redirects=False)
    checar(u"a porta em /suite tambem desvia ao primeiro uso (C12: / e /suite)",
           r.status_code in (302, 303, 307)
           and r.headers.get(u"location", u"").startswith(u"/primeiro-uso?de=/suite"),
           u"%s %s" % (r.status_code, r.headers.get(u"location")))
    r = c.get(u"/", follow_redirects=False)
    checar(u"aceite em dia e TPS vazio: a porta redireciona ao primeiro uso",
           r.status_code in (302, 303, 307)
           and r.headers.get(u"location", u"").startswith(u"/primeiro-uso?de=/"),
           u"%s %s" % (r.status_code, r.headers.get(u"location")))
    r = c.get(u"/", follow_redirects=False)
    checar(u"  e de novo na abertura seguinte, se saiu sem salvar",
           r.status_code in (302, 303, 307))
    checar(u"  a /config nao e desviada (o refazer mora la)",
           c.get(u"/config", follow_redirects=False).status_code == 200)
    checar(u"  a API nao e desviada",
           c.get(u"/api/primeiro-uso", follow_redirects=False).status_code == 200)
    PU.gravar(cfg, u"", pular=True)
    r = c.get(u"/", follow_redirects=False)
    checar(u"depois do pular (que grava o padrao), a porta abre",
           r.status_code == 200 and r.text == u"PORTA", r.status_code)


FRASES_DO_JS_DA_CASCA = (
    u"O programa não está respondendo.",
    u"Isso costuma ser trabalho pesado em curso — uma varredura, uma série "
    u"sendo aberta. A tela volta sozinha quando ele terminar.",
    u"O programa roda em segundo plano, sem janela. Se isto durar mais que "
    u"alguns minutos, o log está em Configurações › Diagnóstico.",
    u"conexão com o programa restabelecida",
    u"escolha eclipse ou monaco",
    u"pasta recusada",
    u"A pasta não existe ou não está acessível desta máquina.",
    u"Sem permissão para ler esta pasta.",
    u"Nada foi gravado: confira a pasta acima.",
    u"Gravado: vale para o próximo RTSTRUCT.",
    u"Nada foi gravado: confira as linhas marcadas.",
    u"Gravado: vale para a próxima série.",
    u"Nada foi gravado: confira os campos marcados.",
    u"Importado. Clique em Reiniciar agora para o vigia reler o arquivo.",
    u"O arquivo foi para a pasta de downloads do navegador.",
)


def _faltam_no_dicionario(frases, tabela):
    import radai_phrases as _f
    linhas = dict((_f.normalizar(l[0]), l) for l in tabela)
    return [f for f in frases
            if len([x for x in (linhas.get(_f.normalizar(f)) or ())[1:] if x])
            < len(_f.CODIGOS)]


def teste_as_frases_do_js_da_casca_tem_os_doze_idiomas():
    secao(u"as frases que o JS escreve (aviso de conexao, erro do primeiro uso) nos doze idiomas")
    import radai_phrases as _f
    import radai_ui as _ui
    import radai_primeiro_uso as PU
    falta = _faltam_no_dicionario(FRASES_DO_JS_DA_CASCA, _f.TABELA)
    checar(u"cada frase tem as onze traducoes", not falta, repr(falta))
    checar(u"  (isca) frase sem entrada e acusada",
           _faltam_no_dicionario((u"frase que ninguem escreveu",), _f.TABELA)
           == [u"frase que ninguem escreveu"])
    checar(u"a nota do aviso de conexao fecha antes do detalhe (no de texto proprio)",
           u"Configurações › Diagnóstico.</span>'" in _ui.JS)
    fonte = io.open(_componentes.fonte("app/radai_primeiro_uso.py"), encoding="utf-8").read()
    cfg_src = io.open(_componentes.fonte("app/radai_config.py"), encoding="utf-8").read()
    checar(u"as mensagens do servidor do primeiro uso e do anel sao as do dicionario",
           u'u"pasta recusada"' in fonte and u'u"escolha eclipse ou monaco"' in cfg_src)


def _primeiro_uso_no_navegador(pagina=None):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    chrome = _chromium_da_maquina()
    if not chrome:
        return None
    import radai_primeiro_uso as PU
    arq = os.path.join(novo_temp(), "t.config")
    io.open(arq, "w", encoding="utf-8").write(u"# teste\nROOT=\nDEVICE=auto\n")
    guardada = PU.PAGINA
    if pagina is not None:
        PU.PAGINA = pagina
    srv = th = None
    medida = {}
    try:
        app = _app_do_painel(arq)
        porta, _aviso = porta_de_teste(8811)
        srv, th = _servir(app, porta)
        with sync_playwright() as p:
            nav = p.chromium.launch(executable_path=chrome)
            try:
                pg = nav.new_page()
                pg.goto(u"http://127.0.0.1:%d/primeiro-uso?de=/config" % porta,
                        wait_until="networkidle")
                medida["salvar_antes"] = pg.locator(u"#pu_salvar").is_disabled()
                medida["pular_antes"] = pg.locator(u"#pu_pular").is_disabled()
                medida["botoes_tps"] = pg.locator(u"[data-tps]").count()
                medida["passos"] = pg.evaluate(
                    u"Array.prototype.map.call(document.querySelectorAll('.pu-passos li'),"
                    u" function(l){ return l.className })")
                medida["procurar_visivel"] = pg.locator(u"#pu_procurar").is_visible()
                if medida["procurar_visivel"]:
                    pg.locator(u"#pu_procurar").click()
                    try:
                        pg.wait_for_selector(u".ui-fp-modal", state="visible",
                                             timeout=5000)
                        medida["explorador"] = True
                    except Exception:
                        medida["explorador"] = False
                    pg.keyboard.press(u"Escape")
                    pg.wait_for_timeout(400)
                pg.locator(u"#pu_pular").click()
                try:
                    from urllib.parse import urlsplit as _us
                    pg.wait_for_url(lambda u: _us(u).path == u"/config", timeout=6000)
                    medida["foi_para"] = pg.url
                except Exception:
                    medida["foi_para"] = pg.url
            finally:
                nav.close()
        medida["arquivo"] = io.open(arq, encoding="utf-8").read()
    finally:
        PU.PAGINA = guardada
        if srv is not None:
            srv.should_exit = True
            th.join(timeout=10)
    return medida


def _erro_da_pasta_em_ingles(pagina=None):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    chrome = _chromium_da_maquina()
    if not chrome:
        return None
    import radai_primeiro_uso as PU
    arq = os.path.join(novo_temp(), "t.config")
    io.open(arq, "w", encoding="utf-8").write(u"# teste\nROOT=\nDEVICE=auto\n")
    falta = os.path.join(novo_temp(), u"nao_existe_aqui")
    guardada = PU.PAGINA
    if pagina is not None:
        PU.PAGINA = pagina
    srv = th = None
    m = {}
    try:
        app = _app_do_painel(arq)
        import radai_languages as _I
        from fastapi.responses import Response as _Resp

        @app.get(u"/radai-idiomas.js")
        def _js_idiomas():
            return _Resp(_I.corpo_js(), media_type=u"application/javascript")
        porta, _aviso = porta_de_teste(8812)
        srv, th = _servir(app, porta)
        with sync_playwright() as p:
            nav = p.chromium.launch(executable_path=chrome)
            try:
                pg = nav.new_page()
                pg.add_init_script(u"try{localStorage.setItem('radai_idioma','en')}catch(e){}")
                pg.goto(u"http://127.0.0.1:%d/primeiro-uso?de=/config" % porta,
                        wait_until="networkidle")
                pg.fill(u"#pu_pasta", falta)
                pg.locator(u"#pu_salvar").click()
                pg.wait_for_function(
                    u"document.getElementById('pu_msg').innerText.trim().length>0"
                    u" && document.getElementById('pu_laudo').innerText.trim().length>0",
                    timeout=6000)
                pg.wait_for_timeout(400)
                m["laudo"] = pg.locator(u"#pu_laudo").inner_text()
                m["msg"] = pg.locator(u"#pu_msg").inner_text()
                m["cor_msg"] = pg.evaluate(
                    u"getComputedStyle(document.getElementById('pu_msg')).color")
                m["cor_corpo"] = pg.evaluate(u"getComputedStyle(document.body).color")
            finally:
                nav.close()
    except Exception as e:
        m["erro"] = u"%s: %s" % (type(e).__name__, e)
    finally:
        PU.PAGINA = guardada
        if srv is not None:
            srv.should_exit = True
            th.join(timeout=10)
    return m


def teste_o_erro_da_pasta_no_primeiro_uso_se_traduz():
    secao(u"o primeiro uso: o erro da pasta sai pela chave do codigo, traduzido")
    import radai_primeiro_uso as PU
    laudo = radai_config.validar_favorita(os.path.join(novo_temp(), u"nao_existe"))
    checar(u"validar_favorita devolve o codigo do erro (nao_existe)",
           laudo.get("codigo") == u"nao_existe", repr(laudo))
    m = _erro_da_pasta_em_ingles()
    if m is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    checar(u"em ingles, o laudo da pasta que falta sai em ingles",
           u"does not exist" in m.get("laudo", u"")
           and u"nao existe" not in m.get("laudo", u""), repr(m))
    checar(u"  e a mensagem de baixo nao repete o laudo",
           m.get("msg", u"").strip() and m.get("msg") != m.get("laudo"), repr(m))
    checar(u"  e fica na cor de erro (nao na cor do texto)",
           m.get("cor_msg") and m.get("cor_msg") != m.get("cor_corpo"), repr(m))
    isca = PU.PAGINA.replace(u"ERRO_DA_PASTA[l.codigo] ||", u"l.erro ||")
    checar(u"  (isca) a troca existe no fonte", isca != PU.PAGINA)
    mi = _erro_da_pasta_em_ingles(isca) or {}
    checar(u"  (isca) sem a frase pelo codigo, o laudo deixa de dizer que a pasta "
           u"nao existe", mi.get("laudo") and u"does not exist" not in mi.get("laudo", u""),
           repr(mi))


def teste_o_primeiro_uso_no_navegador():
    secao(u"o primeiro uso no navegador: sem o TPS, a favorita opcional e o pular")
    m = _primeiro_uso_no_navegador()
    if m is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    checar(u"o salvar e o pular nascem ligados (a pasta e opcional)",
           m.get("salvar_antes") is False and m.get("pular_antes") is False, repr(m))
    checar(u"  e nao ha mais botao de TPS na tela", m.get("botoes_tps") == 0, repr(m))
    checar(u"os passos: Termos feito, Pasta favorita agora",
           m.get("passos") == [u"feito", u"agora"], repr(m.get("passos")))
    checar(u"o Procurar abre o explorador da casca (com a estrela e o mapear dela)",
           m.get("procurar_visivel") is True and m.get("explorador") is True, repr(m))
    checar(u"«Pular por agora» grava o padrao TPS_DESTINO=eclipse e nenhuma pasta",
           u"TPS_DESTINO=eclipse" in m.get("arquivo", u"")
           and u"PASTA_FAVORITA" not in m.get("arquivo", u""), m.get("arquivo"))
    from urllib.parse import urlsplit as _us
    checar(u"  e volta para de onde veio (/config)",
           _us(m.get("foi_para", u"")).path == u"/config", m.get("foi_para"))
    import radai_primeiro_uso as PU
    isca = PU.PAGINA.replace(
        u"pular.addEventListener('click', function(){ enviar({pular: true}) });",
        u"0;")
    checar(u"  (isca) a troca existe no fonte", isca != PU.PAGINA)
    mi = _primeiro_uso_no_navegador(isca)
    checar(u"  (isca) sem o clique ligado ao pular, nada grava e a tela nao sai",
           mi is not None and u"TPS_DESTINO" not in mi.get("arquivo", u"")
           and _us(mi.get("foi_para", u"")).path == u"/primeiro-uso", repr(mi))
    import re as _re
    corpo = _re.sub(u"(?s)<script.*?</script>", u"", PU.PAGINA)
    checar(u"a tela diz onde se ajusta o anel (Xio / Focal em Configuracoes > Geral)",
           u"Usa Xio / Focal? Ajuste em Configurações, na seção Geral." in corpo)
    checar(u"  e diz que a favorita nao muda a pasta que o vigia varre",
           u"Ela não muda a pasta que o vigia varre." in corpo)


def _canto_no_navegador(largura=1280):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    chrome = _chromium_da_maquina()
    if not chrome:
        return None
    import radai_primeiro_uso as PU
    import radai_consent as CS
    import radai_languages as _I
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, Response as _Resp
    app = FastAPI()

    @app.get(u"/primeiro-uso", response_class=HTMLResponse)
    def _pu():
        return PU.pagina()

    @app.get(u"/aceite", response_class=HTMLResponse)
    def _ac():
        return CS.pagina_aceite()

    @app.get(u"/radai-idiomas.js")
    def _js_idiomas():
        return _Resp(_I.corpo_js(), media_type=u"application/javascript")

    @app.get(u"/api/primeiro-uso")
    def _estado_pu():
        return {u"feito": False, u"tps": u"", u"pasta": u""}

    @app.get(u"/api/aceite")
    def _estado_ac():
        return {u"pontos": [], u"fontes": [], u"registro": {}, u"versao": u"x"}

    medir = u"""() => {
      var c = document.querySelector('.ac-lang'), r = c ? c.getBoundingClientRect() : null;
      var rot = document.querySelector('.ac .rot') || document.querySelector('.ac h1');
      return {
        bandeiras: document.querySelectorAll('.ac-lang .radai-lang .rl-op .rl-band svg').length,
        temas: document.querySelectorAll('.ac-lang .ui-seg button[role=radio]').length,
        direita: r ? Math.round(innerWidth - r.right) : null,
        topo: r ? Math.round(r.top) : null,
        abaixo_do_canto: (r && rot) ? (rot.getBoundingClientRect().top >= r.bottom) : null,
        rolagem: document.documentElement.scrollWidth - innerWidth,
        tema0: document.documentElement.getAttribute('data-tema')};
    }"""
    srv = th = None
    m = {}
    try:
        porta, _aviso = porta_de_teste(8813)
        srv, th = _servir(app, porta)
        with sync_playwright() as p:
            nav = p.chromium.launch(executable_path=chrome)
            try:
                for rota in (u"/primeiro-uso", u"/aceite"):
                    pg = nav.new_page(viewport={u"width": largura, u"height": 800},
                                      color_scheme=u"dark")
                    pg.goto(u"http://127.0.0.1:%d%s" % (porta, rota),
                            wait_until="networkidle")
                    pg.wait_for_timeout(300)
                    d = pg.evaluate(medir)
                    claro = pg.locator(u'.ac-lang .ui-seg button[data-v="claro"]')
                    if claro.count():
                        fundo0 = pg.evaluate(u"getComputedStyle(document.body).backgroundColor")
                        claro.click()
                        pg.wait_for_timeout(200)
                        d[u"tema1"] = pg.evaluate(
                            u"document.documentElement.getAttribute('data-tema')")
                        d[u"fundo_mudou"] = fundo0 != pg.evaluate(
                            u"getComputedStyle(document.body).backgroundColor")
                    m[rota] = d
                    pg.close()
            finally:
                nav.close()
    except Exception as e:
        m[u"erro"] = u"%s: %s" % (type(e).__name__, e)
    finally:
        if srv is not None:
            srv.should_exit = True
            th.join(timeout=10)
    return m


def teste_os_botoes_de_anel_e_o_canto():
    secao(u"os dois aneis em Configuracoes > Geral, e o canto do primeiro uso com idioma e tema")
    import radai_primeiro_uso as PU
    import radai_config_estacao as CE
    import radai_consent as CS
    import radai_dicom as D
    import re as _re
    corpo = _re.sub(u"(?s)<script.*?</script>", u"", CE.GERAL)
    checar(u"os dois aneis sairam do primeiro uso", u"data-tps=" not in PU.PAGINA)

    def nomes_batem(pagina, rotulos):
        for v in radai_config.TPS_VALIDOS:
            b = _re.search(u'(?s)<button[^>]*data-tps="%s"[^>]*>(.*?)</button>' % v, pagina)
            if not b or (u'<b translate="no">%s</b>' % rotulos[v]) not in b.group(1):
                return False
        return True
    checar(u"cada botao mostra o nome do radai_config.TPS_ROTULOS (o valor gravado nao muda)",
           nomes_batem(corpo, radai_config.TPS_ROTULOS)
           and radai_config.TPS_ROTULOS == {u"eclipse": u"Eclipse / Monaco",
                                            u"monaco": u"Xio / Focal"},
           repr(radai_config.TPS_ROTULOS))
    trocados = {u"eclipse": u"Xio / Focal", u"monaco": u"Eclipse / Monaco"}
    checar(u"  (isca) os nomes trocados entre os botoes reprovam",
           not nomes_batem(corpo, trocados))
    checar(u"  e o anel com linha divisoria diz para quem serve",
           u"Versões anteriores, ou outros que precisem de linha divisória nos anéis" in corpo)
    checar(u"os nomes antigos sairam da tela (Varian, Elekta, «Com o Monaco»)",
           u"<span>Varian</span>" not in corpo and u"<span>Elekta</span>" not in corpo
           and u"Com o Monaco" not in corpo)
    balao = _re.search(u'(?s)id="an_rot".*?<span class="ui-balao">(.*?)</span></span></div>',
                       corpo)
    balao = balao.group(1) if balao else u""
    checar(u"o «?» explica os dois", u"<b>Eclipse / Monaco</b>" in balao
           and u"<b>Xio / Focal</b>" in balao, balao[:120])

    frase_dos_dois = (u"Nos dois, o RTSTRUCT e o que o DicomBridge exporta "
                      u"saem em Implicit VR Little Endian")

    def sintaxe_confere(sintaxe, b=None):
        b = balao if b is None else b
        return (frase_dos_dois in b
                and sintaxe(u"monaco") == D.SINTAXE_IMPLICITA
                and sintaxe(u"eclipse") == D.SINTAXE_IMPLICITA)
    checar(u"  e a frase da sintaxe diz o que o radai_dicom faz: Implicit VR "
           u"Little Endian nas duas escolhas, como o RTSTRUCT",
           sintaxe_confere(D.sintaxe_de_saida))
    checar(u"  (isca) se Eclipse / Monaco exportasse Explicit, a frase reprova",
           not sintaxe_confere(lambda t: D.SINTAXE_IMPLICITA if t == u"monaco"
                               else u"1.2.840.10008.1.2.1"))
    checar(u"  (isca) o «?» de antes, que dava Implicit só ao Xio / Focal, reprova",
           not sintaxe_confere(D.sintaxe_de_saida, u"<p>Com Xio / Focal, o que o "
                               u"DicomBridge exporta sai também em Implicit VR "
                               u"Little Endian.</p>"))
    linha = PU.linha_do_registro({u"tps": u"eclipse", u"mudou": [u"TPS_DESTINO"]})
    checar(u"o registro do primeiro uso diz o valor padrao e o nome da tela",
           u"TPS_DESTINO=eclipse (Eclipse / Monaco" in linha, linha)
    checar(u"o canto entra so ao servir: o texto selado do aceite nao muda",
           u"data-ui-tema" not in CS.PAGINA_ACEITE
           and PU.ANCORA_DO_CANTO in CS.PAGINA_ACEITE)
    for nome, servida in ((u"primeiro uso", PU.pagina()), (u"aceite", CS.pagina_aceite())):
        checar(u"[%s] a pagina servida tem o seletor de idioma e o de tema no canto" % nome,
               PU.CANTO in servida and u'src="/radai-idiomas.js"' in servida)

    m = _canto_no_navegador()
    if m is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    for rota in (u"/primeiro-uso", u"/aceite"):
        d = m.get(rota) or {}
        checar(u"[%s] doze idiomas com bandeira e os tres temas no canto" % rota,
               d.get(u"bandeiras") == 12 and d.get(u"temas") == 3, repr(d or m))
        checar(u"[%s]   no canto superior direito, acima do conteudo" % rota,
               d.get(u"direita") is not None and 0 <= d[u"direita"] <= 40
               and 0 <= d.get(u"topo", -1) <= 30 and d.get(u"abaixo_do_canto") is True,
               repr(d))
        checar(u"[%s]   e o tema claro vale na hora" % rota,
               d.get(u"tema0") == u"escuro" and d.get(u"tema1") == u"claro"
               and d.get(u"fundo_mudou") is True, repr(d))
    mc = _canto_no_navegador(375)
    for rota in (u"/primeiro-uso", u"/aceite"):
        d = (mc or {}).get(rota) or {}
        checar(u"[%s] no celular o canto cabe, sem rolagem lateral" % rota,
               d.get(u"rolagem") == 0 and d.get(u"abaixo_do_canto") is True, repr(d))
    guardado = PU.CANTO
    try:
        PU.CANTO = PU.ANCORA_DO_CANTO
        mi = _canto_no_navegador()
    finally:
        PU.CANTO = guardado
    checar(u"  (isca) sem o canto, nenhuma das duas telas tem o seletor de tema",
           all(((mi or {}).get(r) or {}).get(u"temas") == 0
               for r in (u"/primeiro-uso", u"/aceite")), repr(mi))


def teste_o_diagnostico_le_o_registro_da_regra_unica():
    secao(u"pre-requisitos: a raiz e o registro sao os da pasta instalada")
    import importlib.util
    base = novo_temp(u"radai_p_prereq_")
    raiz = os.path.join(base, u"D_ESTACAO", u"RADIOTERAPIA_AI")
    prog = os.path.join(raiz, u"LOCAL_SUITE")
    os.makedirs(prog)
    for nome in (u"radai_version.py", u"radai_prerequisites.py"):
        shutil.copy2(_componentes.fonte(u"app/" + nome), prog)
    io.open(os.path.join(prog, u"entrega.txt"), u"w", encoding=u"utf-8").write(
        u"PROJETO=LOCAL_SUITE\nVERSAO=8.5\n")
    io.open(os.path.join(raiz, u"_instalados.json"), u"w",
            encoding=u"utf-8").write(json.dumps(
                {u"LOCAL_SUITE": {u"versao": u"8.5", u"caminho": prog},
                 u"FACILITA_RT": {u"versao": u"2.8", u"caminho": u"X"}}))
    sysd = os.path.join(base, u"SYSDRIVE")
    os.makedirs(os.path.join(sysd, u"RADIOTERAPIA_AI", u"PROJETO_DE_OUTRA_RAIZ"))
    io.open(os.path.join(sysd, u"RADIOTERAPIA_AI", u"_instalados.json"), u"w",
            encoding=u"utf-8").write(u"{isto nao e json")
    guardado = dict(os.environ)
    mods = dict((k, sys.modules.pop(k)) for k in (u"radai_version",)
                if k in sys.modules)
    sys.path.insert(0, prog)
    try:
        os.environ.pop(u"RADAI_RAIZ_INSTALACAO", None)
        os.environ[u"SystemDrive"] = sysd
        spec = importlib.util.spec_from_file_location(
            u"rp_fantoma", os.path.join(prog, u"radai_prerequisites.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        pr = m.conferir()
        itens = dict((i[u"titulo"], i) for i in pr[u"itens"])
        checar(u"a raiz e o PAI da pasta do programa, e nao o "
               u"SystemDrive\\RADIOTERAPIA_AI",
               os.path.normcase(pr[u"raiz"]) == os.path.normcase(raiz),
               pr[u"raiz"].replace(base, u"<tmp>"))
        r = itens.get(u"Registro de instalados") or {}
        checar(u"  o registro lido e o dela (2 projetos)",
               r.get(u"ok") and u"2 projeto" in r.get(u"valor", u""), r)
        checar(u"  (isca) o registro ilegivel do SystemDrive nao foi lido",
               u"NÃO abre" not in r.get(u"valor", u""), r)
        j = itens.get(u"Já instalado aqui") or {}
        checar(u"  e «Já instalado aqui» lista a pasta dela",
               u"LOCAL_SUITE" in j.get(u"valor", u"")
               and u"PROJETO_DE_OUTRA_RAIZ" not in j.get(u"valor", u""), j)
        os.environ[u"RADAI_RAIZ_INSTALACAO"] = os.path.join(sysd,
                                                            u"RADIOTERAPIA_AI")
        pr2 = m.conferir()
        checar(u"com RADAI_RAIZ_INSTALACAO, vale ela (a mesma regra do "
               u"radai_version)", os.path.normcase(pr2[u"raiz"])
               == os.path.normcase(os.path.join(sysd, u"RADIOTERAPIA_AI")),
               pr2[u"raiz"].replace(base, u"<tmp>"))
    finally:
        sys.path.remove(prog)
        sys.modules.pop(u"radai_version", None)
        sys.modules.update(mods)
        os.environ.clear()
        os.environ.update(guardado)


def main():
    print("test_panel | acervo + mini-pagina do ContourLab + /config (cartoes de funcao)")
    guardado = os.environ.get("RADAI_CALIB_DIR")
    testes = [teste_o_icone_do_produto_chega_a_tela,
              teste_acervo_nasce_vazio, teste_registrar_e_ler,
              teste_serie_reprocessada_nao_duplica, teste_linha_corrompida_nao_derruba,
              teste_registrar_nunca_levanta, teste_estado_conta_receitas_e_versoes,
              teste_estado_sem_vigia, teste_cartoes_refletem_o_que_existe,
              teste_cartao_liga_sozinho_quando_o_modulo_chegar,
              teste_estado_reflete_o_acervo, teste_vigia_que_explode_nao_derruba_o_painel,
              teste_geometria_carrega, teste_pagina_tem_o_essencial,
              teste_leitura_do_config, teste_config_le_igual_ao_vigia,
              teste_bom_do_bloco_de_notas,
              teste_ajuda_vem_dos_comentarios, teste_gravar_preserva_o_arquivo,
              teste_gravar_recusa_quebra_de_linha, teste_validar_pasta,
              teste_validar_pasta_sem_escrita, teste_divergencia_pede_reinicio,
              teste_listar_pastas, teste_porta_so_vale_reabrindo,
              teste_aviso_some_depois_da_recarga,
              teste_pagina_de_config_tem_o_essencial,
              teste_config_tem_as_acoes_no_topo,
              teste_a_suavizacao_nao_se_grava_pela_tela,
              teste_o_recorte_no_corpo_segue_a_suavizacao,
              teste_a_ajuda_do_config_diz_a_v82,
              teste_o_registro_de_casos_e_secao_e_nao_dialogo,
              teste_a_procedencia_tem_secao_propria,
              teste_a_config_tem_cartoes_de_funcao,
              teste_a_recomendacao_de_device_e_auto,
              teste_a_linha_clinica_do_contourlab_no_rodape,
              teste_o_cartao_de_atualizar_da_o_link_permanente,
              teste_config_no_navegador,
              teste_as_rotas_de_diagnosticar,
              teste_diagnosticar_no_navegador,
              teste_landing_no_ar, teste_tela_de_config_no_ar,
              teste_a_tela_do_vigia_fala_a_lingua_da_rota,
              teste_o_vigia_grava_o_root_pela_pagina,
              teste_reiniciar_aplica_sem_fechar_o_programa,
              teste_a_porta_e_so_a_porta,
              teste_a_porta_de_reserva_lista_todo_modulo,
              teste_as_tres_mini_paginas,
              teste_o_torax_saiu_da_arvore,
              teste_nenhuma_pagina_busca_recurso_na_internet,
              teste_nomes_do_bridge_batem_cartao_trilha_h1,
              teste_a_verificacao_profunda_saiu_da_instalacao,
              teste_a_versao_das_bibliotecas_vem_do_pacote,
              teste_o_primeiro_uso_aponta_o_que_existe,
              teste_o_primeiro_uso_grava_tps_e_pasta,
              teste_a_porta_leva_ao_primeiro_uso_sem_tps,
              teste_as_frases_do_js_da_casca_tem_os_doze_idiomas,
              teste_o_primeiro_uso_no_navegador,
              teste_os_botoes_de_anel_e_o_canto,
              teste_o_erro_da_pasta_no_primeiro_uso_se_traduz,
              teste_o_diagnostico_le_o_registro_da_regra_unica]
    for t in testes:
        try:
            t()
        except Exception as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    if guardado is None:
        os.environ.pop("RADAI_CALIB_DIR", None)
    else:
        os.environ["RADAI_CALIB_DIR"] = guardado
    for _w in [sys.modules.get("radai_watcher")] + _VIGIAS_CARREGADOS:
        _fh = getattr(_w, "_LOG_FH", None) if _w is not None else None
        if _fh is None:
            continue
        try:
            _fh.close()
        except Exception as _e:
            print(u"  AVISO  o log do vigia nao fechou (%s): a pasta dele "
                  u"pode sobrar em %%TEMP%%" % _e)
        _w._LOG_FH = None
    for d in _TEMPS:
        shutil.rmtree(d, ignore_errors=True)

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
