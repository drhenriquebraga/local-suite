# -*- coding: utf-8 -*-
import ast
import shutil
import io
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
OFICINA = _componentes.oficina("consent", __file__)
_cleanup.adotar_prefixo('radai_aceite_')


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

_ok = _falhou = 0
_falhas = []


def secao(t):
    print(u"\n── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def checar(rotulo, cond, detalhe=u""):
    global _ok, _falhou
    if cond:
        _ok += 1
        print(u"  OK     %s" % rotulo)
    else:
        _falhou += 1
        _falhas.append(rotulo)
        print(u"  FALHA  %s  %s" % (rotulo, detalhe))


# GUARDA: divergencias conhecidas entre o codigo e uma versao PUBLICADA dos
# documentos (nao se retoca versao publicada). Enquanto VERSAO_DOCS for a de
# `VERSAO_DOS_PENDENTES`, a checagem exige que a divergencia CONTINUE
# (resolvida, a linha tem de sair daqui); em qualquer outra versao, ou com o
# dicionario vazio, a checagem vale como sempre. Vazio e `None`: nenhuma
# divergencia pendente.
PENDENTES_DOS_DOCUMENTOS = {}
VERSAO_DOS_PENDENTES = None


def checar_doc(cod, rotulo, cond, detalhe=u""):
    import radai_consent as _CS
    if (cod in PENDENTES_DOS_DOCUMENTOS and VERSAO_DOS_PENDENTES
            and _CS.VERSAO_DOCS == VERSAO_DOS_PENDENTES):
        checar(u"%s [PENDENTE dos documentos %s: %s]"
               % (rotulo, VERSAO_DOS_PENDENTES, PENDENTES_DOS_DOCUMENTOS[cod]),
               not cond,
               u"a divergencia sumiu: tire `%s` de PENDENTES_DOS_DOCUMENTOS"
               % cod)
    else:
        checar(rotulo, cond, detalhe)


def ler(rel):
    p = _componentes.fonte(rel)
    if not os.path.isfile(p):
        return u""
    return io.open(p, encoding="utf-8", errors="replace").read()


def _portao_por_comportamento():
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except ImportError:
        checar(u"fastapi nesta maquina (o portao se prova rodando)", False)
        return
    import radai_consent as CS

    def _cliente():
        app = FastAPI()

        @app.get("/tela")
        def _tela():
            return {"ok": 1}

        @app.get("/api/lote")
        def _api():
            return {"ok": 1}

        CS.montar_portao(app)
        return TestClient(app)

    def _quebra():
        raise OSError("registro ilegivel")

    class _Livres(object):
        def __contains__(self, x):
            raise RuntimeError("o proprio portao quebrou")

    guardado_aceito, guardado_livres = CS.aceito, CS.LIVRES
    try:
        CS.aceito = _quebra
        cli = _cliente()
        r = cli.get("/tela", follow_redirects=False)
        checar(u"registro ilegivel: a tela vai para /aceite (FECHA)",
               r.status_code == 303
               and r.headers.get("location", "").startswith("/aceite?de="),
               u"%s %s" % (r.status_code, r.headers.get("location")))
        r = cli.get("/api/lote", follow_redirects=False)
        checar(u"e a API passa sem aceite (o lote da noite segue)",
               r.status_code == 200, str(r.status_code))
        CS.aceito = lambda: True
        CS.LIVRES = _Livres()
        r = _cliente().get("/tela", follow_redirects=False)
        checar(u"falha do proprio portao nao tranca a estacao",
               r.status_code == 200, str(r.status_code))
        CS.aceito, CS.LIVRES = (lambda: False), guardado_livres
        r = _cliente().get("/tela", follow_redirects=False)
        checar(u"  isca: sem aceite e com o portao inteiro, a tela FECHA",
               r.status_code == 303, str(r.status_code))
    finally:
        CS.aceito, CS.LIVRES = guardado_aceito, guardado_livres


def teste_falha_fechado():
    secao(u"o portao falha FECHADO, e ele e do SERVIDOR")
    c = ler("app/radai_consent.py")

    checar(u"existe `montar_portao`", u"def montar_portao(" in c)
    checar(u"e ele e um middleware, nao um `if` por rota",
           u'@app.middleware("http")' in c,
           u"um `if` por rota e uma linha para esquecer a cada tela nova")

    corpo = c[c.index(u"def montar_portao("):]
    checar(u"nao conseguir ler o registro FECHA",
           u"em_dia = False" in corpo,
           u"o except do `aceito()` precisa fechar, nao liberar")
    checar(u"e o motivo fica num GUARDA: no ponto",
           u"GUARDA: sem conseguir ler o aceite" in corpo)
    checar(u"sem aceite ele redireciona para /aceite",
           u'"/aceite?de="' in corpo)
    checar(u"com 303, e nao 302",
           u"status_code=303" in corpo,
           u"303 troca o metodo para GET; 302 pode repetir um POST")

    import radai_consent as CS
    for rota in ("/aceite", "/termos", "/politica-privacidade", "/creditos"):
        checar(u"`%s` passa sem aceite" % rota, rota in CS.LIVRES,
               u"e o que a pessoa precisa LER para poder aceitar")
    checar(u"e nenhuma tela que nao seja de leitura passa sem aceite",
           set(CS.LIVRES) <= {"/aceite", "/termos", "/politica-privacidade",
                              "/creditos", "/favicon.ico",
                              "/radai-idiomas.js"}, str(CS.LIVRES))
    checar(u"a API passa sempre", u'caminho.startswith("/api/")' in corpo,
           u"o lote da noite nao para por documento novo")
    _portao_por_comportamento()

    v = ler("app/radai_watcher.py")
    checar(u"o vigia monta o portao", u"montar_portao(app)" in v)
    checar(u"e ele e o ULTIMO middleware registrado",
           v.index(u"montar_portao(app)") > v.index(u"radai_credits.montar(app)"),
           u"middleware roda na ordem inversa do registro")

    p = ler("app/radai_panel.py")
    for morto in (u'id="portao"', u'id="cards_area"', u"function liberarCartoes(",
                  u"function mostrarPortao(", u"function conferirAceite("):
        checar(u"a mini-pagina nao tem mais `%s`" % morto[:26],
               morto not in p)


def teste_documento_honesto():
    secao(u"os documentos descrevem o pacote que existe")
    termos = ler("app/radai_consent.py")
    creditos = ler("app/radai_credits.py")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import radai_models as M
    try:
        import artefatos as A
        restritas_build = [l for l in A.restritivas()]
    except Exception:
        restritas_build = None

    restritos = sorted(k for k, m in M.MODELOS.items()
                       if (m.get("uso_permitido") or u"") == u"nao_comercial")
    if restritas_build is not None:
        checar(u"o registro e o preparador contam o mesmo numero de restritos",
               len(restritos) == len(restritas_build),
               u"registro: %d · artefatos: %d" % (len(restritos),
                                                  len(restritas_build)))

    for nome, txt in ((u"termos", termos), (u"creditos", creditos)):
        plano = u" ".join(txt.split())
        for chave, m in sorted(M.MODELOS.items()):
            marca = str(m.get("nome") or chave).split(u"(")[0].split(u"—")[0]
            marca = marca.strip().split()[0].strip(u",;:")
            checar(u"%s: nomeia `%s`" % (nome, marca),
                   marca.lower() in plano.lower(), chave)

    import re
    AFIRMA = re.compile(
        u"(?i)(este pacote|o pacote)[^.]{0,40}"
        u"(embarca|traz|tem|carrega|contém|contem)[^.]{0,60}"
        u"não[- ]comercial")
    import radai_consent as _CS
    import radai_credits as _CR
    lidos = ((u"termos", _plano(_CS.TERMOS) + u" " + _plano(_CS.POLITICA)
              + u" " + u" ".join(t + u" " + d for (_c, t, d) in _CS.PONTOS)),
             (u"creditos", _plano(_CR.pagina())))
    for nome, txt in lidos:
        plano = u" ".join(txt.split())
        achou = AFIRMA.search(plano)
        if restritos:
            checar(u"%s: com componente restrito, ele e ANUNCIADO" % nome,
                   bool(achou), u"%d restrito(s) no registro" % len(restritos))
        else:
            checar(u"%s: sem componente restrito, nada e anunciado" % nome,
                   not achou, (achou.group(0)[:80] if achou else u""))

    for nome, txt in lidos + ((u"NOTICE", ler("NOTICE")),):
        plano = u" ".join(txt.split())
        frase = _afirma_fora_do_pacote(plano)
        checar(u"%s: nao diz embarcado/restrito um componente que saiu" % nome,
               frase is None, frase or u"")

    for nome, txt in ((u"termos", termos), (u"creditos", creditos)):
        plano = u" ".join(txt.split())
        checar(u"%s: separa o TotalSegmentator, que e Apache-2.0" % nome,
               u"TotalSegmentator" in plano and u"Apache-2.0" in plano)

    for nome, txt in ((u"termos", termos), (u"creditos", creditos)):
        plano = u" ".join(txt.split())
        checar(u"%s: nao diz que peso de terceiro nao vem no pacote" % nome,
               u"não vem no pacote" not in plano.lower()
               and u"nao vem no pacote" not in plano.lower())
        checar(u"%s: nao diz que nao-comercial NUNCA e embarcado" % nome,
               u"não-comercial nunca é embarcado" not in plano.lower()
               and u"nao-comercial nunca e embarcado" not in plano.lower())


def teste_pontos_e_versao():
    secao(u"o ponto da licenca, e a versao que forca aceitar de novo")
    import radai_consent as C

    chaves = [c for (c, _, _) in C.PONTOS]
    checar(u"existe o ponto das licencas de peso", "licenca_pesos" in chaves,
           str(chaves))
    ponto = [p for p in C.PONTOS if p[0] == "licenca_pesos"]
    if ponto:
        texto = u" ".join((ponto[0][1] + u" " + ponto[0][2]).split())
        import radai_models as _M
        for chave, m in sorted(_M.MODELOS.items()):
            marca = str(m.get("nome") or chave).split(u"(")[0]
            marca = marca.split(u"—")[0].strip().split()[0].strip(u",;:")
            checar(u"o ponto nomeia `%s`" % marca,
                   marca.lower() in texto.lower(), chave)
        for lic in (u"Open Model License", u"CC BY-SA 4.0", u"CC BY 4.0",
                    u"CC0-1.0"):
            checar(u"e declara a licenca %s" % lic, lic in texto, texto[:70])
        checar(u"e separa o TotalSegmentator, que e Apache-2.0",
               u"TotalSegmentator" in texto and u"Apache-2.0" in texto)
        checar(u"e cita os niveis cervicais como Weissmann et al.",
               u"Weissmann et al." in texto, texto[-160:])
        checar(u"e diz que NENHUM componente e nao comercial",
               u"NENHUM" in texto and u"comercial" in texto, texto[-90:])
        checar(u"e nao cita a clausula 3.3, de um componente que nao vem",
               u"3.3" not in texto, texto[-120:])

    checar(u"a versao dos documentos passou de 1.0", C.VERSAO_DOCS != "1.0",
           C.VERSAO_DOCS)
    checar(u"e passou da 1.3, cujo texto mudou sem a versao subir",
           C.VERSAO_DOCS not in ("1.0", "1.1", "1.2", "1.3"), C.VERSAO_DOCS)
    fonte = ler("app/radai_consent.py")
    corpo = fonte[fonte.index(u"def aceito("):fonte.index(u"def montar_registro(")]
    checar(u"`aceito()` compara a versao EXATA (nao 'existe aceite')",
           u'a.get("versao") != VERSAO_DOCS' in corpo)
    checar(u"e a impressao do texto, que tambem tem de existir",
           u"impressao_dos_documentos()" in corpo and u"bool(feita)" in corpo)


def teste_privacidade_descreve_o_log_que_existe():
    secao(u"privacidade: o log, como ele e")
    import radai_consent as C
    pol = u" ".join(C.politica().split()) if hasattr(C, "politica") else u""
    if not pol:
        pol = u" ".join(ler("app/radai_consent.py").split())

    checar(u"a politica NAO diz que o log ignora o nome do paciente",
           u"log não registra nome do paciente" not in pol,
           u"era a frase de ate 15/09/2026")

    checar(u"ela diz que o log guarda o caminho RELATIVO da serie",
           u"relativo" in pol.lower())
    checar(u"e avisa que essa pasta costuma ter o nome do paciente",
           u"nome do paciente" in pol.lower())
    checar(u"e o `registro\\` aparece em «onde os dados ficam»",
           u"registro de casos" in pol.lower())
    checar(u"com o pseudonimo dito, e que ele nao se reverte",
           u"pseud" in pol.lower() and u"revert" in pol.lower())

    vig = ler("app/radai_watcher.py")
    checar(u"e o vigia continua logando o caminho RELATIVO",
           "rel_root(sdir)" in vig)


_MARCA_SEM_ESCOLHA = u"Nenhuma rota nem tela do programa elege modelo."
_MARCA_CAMPO_DA_LICENCA = (u"o campo que diz o que a licença do peso permite "
                           u"— é ele que a tela do aceite lê")


def _trava_do_modelo_divergente(modelos, tem_escolher, src_consent, termos):
    fora = []
    t = u" ".join(_visivel_de_teste(termos).split())
    if tem_escolher is (_MARCA_SEM_ESCOLHA in t):
        fora.append(u"o registro %s funcao de escolha, e os Termos dizem que "
                    u"%s" % (u"tem" if tem_escolher else u"NAO tem",
                             u"nenhuma rota elege modelo"
                             if _MARCA_SEM_ESCOLHA in t else u"ha uma"))
    if u"a função de escolha usa" in t:
        fora.append(u"os Termos ainda citam a funcao de escolha que saiu")
    sem_campo = sorted(k for k, m in modelos.items() if "uso_permitido" not in m)
    if sem_campo:
        fora.append(u"modelo sem `uso_permitido`: %s" % u", ".join(sem_campo))
    le = u'm.get("uso_permitido")' in _fonte_da_funcao(src_consent,
                                                       "fontes_de_terceiros")
    if le is not (_MARCA_CAMPO_DA_LICENCA in t):
        fora.append(u"a tela do aceite %s o campo da licenca, e os Termos %s"
                    % (u"le" if le else u"NAO le",
                       u"dizem" if _MARCA_CAMPO_DA_LICENCA in t
                       else u"nao dizem"))
    restritos = sorted(k for k, m in modelos.items()
                       if m.get("uso_permitido") != "livre")
    if restritos and u"Nenhum componente deste pacote é de uso não comercial" in t:
        fora.append(u"os Termos dizem que nenhum e de uso nao comercial, e o "
                    u"registro tem %s" % u", ".join(restritos))
    return fora


def _visivel_de_teste(html):
    import radai_consent as _CS
    return _CS._visivel(html)


def teste_trava_do_modelo():
    secao(u"o campo da licenca no registro, sem funcao de escolha (Termos 4)")
    import radai_consent as CS
    import radai_models as V
    src_cs = ler("app/radai_consent.py")
    tem = hasattr(V, "escolher")
    div = _trava_do_modelo_divergente(V.MODELOS, tem, src_cs, CS.TERMOS)
    checar(u"o registro e os Termos dizem a mesma coisa (medido: escolher=%s, "
           u"%d modelos)" % (tem, len(V.MODELOS)), not div, u" | ".join(div))
    checar(u"  isca: a funcao de escolha volta ao registro: reprova",
           bool(_trava_do_modelo_divergente(V.MODELOS, True, src_cs,
                                            CS.TERMOS)))
    checar(u"  isca: os Termos de antes (a funcao de escolha usa o campo): "
           u"reprova", _MARCA_SEM_ESCOLHA in _plano(CS.TERMOS)
           and bool(_trava_do_modelo_divergente(
               V.MODELOS, tem, src_cs, _plano(CS.TERMOS).replace(
                   _MARCA_SEM_ESCOLHA, u"A função de escolha usa o campo."))))
    _rest = dict(V.MODELOS)
    _rest["_veiculo_restrito"] = {"nome": u"veiculo do teste",
                                  "licenca": u"teste — nao comercial",
                                  "uso_permitido": "nao_comercial"}
    checar(u"  isca: um modelo nao comercial no registro: reprova",
           bool(_trava_do_modelo_divergente(_rest, tem, src_cs, CS.TERMOS)))
    _sem = dict(V.MODELOS)
    _sem["_veiculo_sem_campo"] = {"nome": u"veiculo sem campo"}
    checar(u"  isca: um modelo sem o campo: reprova",
           bool(_trava_do_modelo_divergente(_sem, tem, src_cs, CS.TERMOS)))
    checar(u"  isca: a tela do aceite deixa de ler o campo: reprova",
           bool(_trava_do_modelo_divergente(
               V.MODELOS, tem, src_cs.replace(u'm.get("uso_permitido")',
                                              u'm.get("x")'), CS.TERMOS)))
    restritos = [k for k, m in V.MODELOS.items()
                 if m["uso_permitido"] == "nao_comercial"]
    checar(u"o pacote de hoje nao tem componente nao comercial",
           not restritos, str(restritos))


def teste_registro():
    secao(u"o aceite fica gravado, e a versao anterior nao vale")
    import radai_archive
    import radai_consent as C

    antes = os.environ.get("RADAI_CALIB_DIR")
    tmp = tempfile.mkdtemp(prefix="radai_aceite_")
    os.environ["RADAI_CALIB_DIR"] = tmp
    try:
        checar(u"o acervo seguiu a variavel de ambiente",
               os.path.normcase(str(radai_archive.raiz()))
               == os.path.normcase(tmp), str(radai_archive.raiz()))
        checar(u"estacao nova comeca SEM aceite", not C.aceito())

        d = C.registrar_aceite(quem="Fulano", itens=["todos"])
        checar(u"registrar devolve a versao atual", d["versao"] == C.VERSAO_DOCS)
        checar(u"registrar guarda quem", d["quem"] == "Fulano")
        checar(u"registrar guarda quando", bool(d["quando"]))
        checar(u"registrar guarda a impressao do texto aceito",
               d.get("impressao") == C.impressao_dos_documentos(),
               str(d.get("impressao"))[:16])
        checar(u"depois de registrar, aceito() e verdadeiro", C.aceito())

        arq = os.path.join(tmp, C.ARQUIVO_ACEITE)
        checar(u"o arquivo existe no acervo", os.path.isfile(arq), arq)
        if os.path.isfile(arq):
            g = json.load(io.open(arq, encoding="utf-8"))
            checar(u"o arquivo guarda a maquina", "maquina" in g)

            def _grava(reg):
                json.dump(reg, io.open(arq, "w", encoding="utf-8"),
                          ensure_ascii=False)

            h = dict(g)
            h["impressao"] = u"0" * 64
            _grava(h)
            checar(u"mesma versao com OUTRA impressao NAO vale",
                   not C.aceito())
            h = dict(g)
            h.pop("impressao", None)
            _grava(h)
            checar(u"registro SEM impressao (so a versao) NAO vale",
                   not C.aceito())
            _grava(g)
            _termos = C.TERMOS
            try:
                C.TERMOS = _termos.replace(u"Uso responsável",
                                           u"Uso responsável e atento")
                checar(u"texto mudado depois do aceite pede aceite de novo",
                       not C.aceito())
            finally:
                C.TERMOS = _termos
            checar(u"  e o texto de volta volta a valer", C.aceito())
            _imp = C.impressao_dos_documentos

            def _quebra():
                raise RuntimeError("isca")
            try:
                C.impressao_dos_documentos = _quebra
                checar(u"impressao que nao se calcula FECHA o portao",
                       C.aceito() is False)
            finally:
                C.impressao_dos_documentos = _imp

            g["versao"] = "0.9"
            _grava(g)
            checar(u"aceite de versao anterior NAO vale", not C.aceito())
    finally:
        if antes is None:
            os.environ.pop("RADAI_CALIB_DIR", None)
        else:
            os.environ["RADAI_CALIB_DIR"] = antes


def teste_texto_do_portao():
    secao(u"a tela /aceite mostra o que se esta aceitando")
    import radai_consent as CS
    p = CS.pagina_aceite()
    plano = u" ".join(p.split())

    checar(u"a tela existe e tem corpo", len(p) > 3000, str(len(p)))
    checar(u"tem a caixa de marcar", u'id="ac_ok"' in p)
    checar(u"o botao nasce desabilitado", u'id="ac_bt" disabled' in p)
    checar(u"e a caixa o habilita", u"ac_bt').disabled = !this.checked" in p)

    import radai_models as _M
    checar(u"a splash tem onde pendurar as fontes",
           u'id="ac_fontes"' in p and u"d.fontes" in p,
           u"sem o gancho, a lista servida nao aparece")
    fontes = CS.fontes_de_terceiros()
    nomes = u" ".join((f.get("nome") or u"") + u" " + (f.get("licenca") or u"")
                      for f in fontes)
    checar(u"e ela traz TODO peso do registro",
           len(fontes) == len(_M.MODELOS),
           u"%d de %d" % (len(fontes), len(_M.MODELOS)))
    for chave, m in sorted(_M.MODELOS.items()):
        marca = str(m.get("nome") or chave).split(u"(")[0]
        marca = marca.split(u"\u2014")[0].strip().split()[0].strip(u",;:")
        checar(u"  com `%s`" % marca, marca.lower() in nomes.lower(), chave)
    checar(u"e o TotalSegmentator aparece como permissivo",
           u"apache" in nomes.lower())
    checar(u"cada ponto sai com um sinal", u"p.sinal" in p)
    ESPERADO = {u"unapproved": u"nao",
                u"inventa": u"atencao", u"remove": u"atencao",
                u"deteccao": u"atencao", u"exportar": u"atencao",
                u"local": u"sim",
                u"uso_estudo": u"sim", u"revisao": u"sim",
                u"responsavel": u"sim", u"licenca_pesos": u"sim"}
    for chave, _tit, _d in CS.PONTOS:
        esperado = ESPERADO.get(chave)
        if esperado is None:
            continue
        checar(u"  `%s` e `%s`" % (chave, esperado),
               CS.sinal_do_ponto(chave) == esperado,
               CS.sinal_do_ponto(chave))
    for chave in (u"local", u"exportar"):
        checar(u"  a garantia `%s` NAO sai com ✗" % chave,
               CS.sinal_do_ponto(chave) != u"nao")

    for rota in ("/termos", "/politica-privacidade", "/creditos"):
        checar(u"leva a %s" % rota, (u'href="%s"' % rota) in p)

    checar(u"diz o que NAO bloqueia",
           u"interrompe um vigia" in plano)

    checar(u"os pontos vem do /api/aceite", u"fetch('/api/aceite')" in p)
    for chave, titulo, _d in CS.PONTOS:
        checar(u"o ponto `%s` NAO esta escrito no HTML" % chave,
               titulo not in p,
               u"lista fixa na pagina envelhece sem ninguem notar")

    import re as _re
    _sem_estilo = _re.sub(r"(?is)<style.*?</style>", " ", p)
    _sem_estilo = _re.sub(r"(?is)<script.*?</script>", " ", _sem_estilo)
    checar(u"a tela nao tem trilho",
           not _re.search(r"class=\"[^\"]*radai-menu", _sem_estilo),
           u"a folha do radai_ui pode citar a classe; o DOM nao pode te-la")
    checar(u"nem barra da direita",
           not _re.search(r"class=\"[^\"]*radai-tarefas", _sem_estilo))
    checar(u"e a checagem ainda reprova casca de verdade",
           bool(_re.search(r"class=\"[^\"]*radai-menu",
                           u'<nav class="radai-menu"></nav>')))

    checar(u"devolve para a rota que trouxe", u"get('de')" in p)
    checar(u"e recusa `//` (endereco absoluto disfarcado)",
           u"charAt(1) !== '/'" in p,
           u"sem isso, ?de=//site.com sai da estacao")

    def _guarda(alvo):
        n = u""
        for ch in alvo:
            cc = ord(ch)
            if cc in (9, 10, 13):
                continue
            n += u"/" if cc == 92 else ch
        return n if (n[:1] == u"/" and n[1:2] != u"/") else u"/"

    CONTRA = chr(92)
    for alvo, esperado, porque in (
            (u"/vigia", u"/vigia", u"caminho normal passa"),
            (u"/lote", u"/lote", u"idem"),
            (u"//outro.site", u"/", u"endereco absoluto disfarcado"),
            (u"https://outro.site", u"/", u"endereco absoluto"),
            (u"/" + CONTRA + u"outro.site", u"/", u"contrabarra vale barra"),
            (u"/" + chr(13) + u"/host", u"/", u"CR e removido antes"),
            (u"/" + chr(10) + u"/host", u"/", u"LF e removido antes"),
            (u"/" + chr(9) + u"/host", u"/", u"TAB e removido antes"),
            (u"", u"/", u"vazio vai para a porta")):
        checar(u"`?de=` %s -> %s (%s)" % (repr(alvo), esperado, porque),
               _guarda(alvo) == esperado, repr(_guarda(alvo)))

    checar(u"a pagina normaliza por codigo de caractere",
           u"charCodeAt(k)" in p and u"cc === 92" in p,
           u"tab/LF/CR/contrabarra, sem regex")




def _sufixos_do_registro():
    import radai_sets
    vistos = []
    for c in radai_sets.CONJUNTOS:
        s = c.get("sufixo") or u""
        if s and s not in vistos:
            vistos.append(s)
    return vistos


# GUARDA: ponto do aceite com texto novo, ainda sem as doze traducoes; a
# checagem exige que continue sem traducao, e traduzido o ponto sai daqui.
PONTOS_PENDENTES_DA_TRADUCAO = {}


def _pontos_pendentes(pontos, pendentes=None):
    pendentes = (PONTOS_PENDENTES_DA_TRADUCAO if pendentes is None
                 else pendentes)
    fora = []
    for (c, t, d) in pontos:
        parte = pendentes.get(c)
        if parte == "titulo":
            fora.append(t)
        elif parte == "detalhe":
            fora.append(d)
    return fora


def _sem_traducao(frases):
    import radai_phrases as F
    tab = {}
    for t in F.TABELA:
        tab[F.normalizar(t[0])] = t
    fora = []
    for f in frases:
        t = tab.get(F.normalizar(f))
        if t is None or len(t) != 12 or not all(
                (c or u"").strip() for c in t[1:]):
            fora.append(f)
    return fora


def _nos_de_texto(h):
    import html as _html
    fora = []
    for pedaco in re.split(r"<[^>]+>", h or u""):
        t = u" ".join(_html.unescape(pedaco).split())
        if t:
            fora.append(t)
    return fora


_ACEITE_DUBLES_JS = u"""
var ORDEM = [], EL = {};
function _el(id){
 if(!EL[id]) EL[id] = {id: id, innerHTML: '', textContent: '', style: {},
                       disabled: false, checked: false,
                       addEventListener: function(){}};
 return EL[id];
}
var document = {getElementById: _el};
var PAYLOAD = @PAYLOAD@;
var RESPOSTA_POST = {erro: 'faltam confirmar: deteccao'};
function fetch(url, opt){
 var post = !!(opt && opt.method === 'POST');
 ORDEM.push('fetch:' + url + (post ? ':POST' : ''));
 return Promise.resolve({json: function(){ return post ? RESPOSTA_POST : PAYLOAD; }});
}
var window = {
 radaiRetraduzir: function(){
  ORDEM.push('retraduzir:' + (EL.ac_fo_linhas ? EL.ac_fo_linhas.innerHTML.length : 0));
 },
 uiTexto: function(e, t){ ORDEM.push('uiTexto:' + t); e.textContent = t; },
 uiHTML: function(e, h){ ORDEM.push('uiHTML'); e.innerHTML = h; }
};
var location = {search: '', href: ''};
function URLSearchParams(){ this.get = function(){ return null; }; }
"""

_ACEITE_RODA_JS = u"""
setTimeout(function(){
 var R = {fontes: _el('ac_fo_linhas').innerHTML,
          mudou: _el('ac_mudou').innerHTML,
          pontos: _el('ac_pontos').innerHTML,
          carga: ORDEM.slice()};
 ORDEM = [];
 acEntrar();
 setTimeout(function(){
  R.falha = _el('ac_msg').innerHTML;
  R.bt_religado = !_el('ac_bt').disabled;
  R.entrar = ORDEM.slice();
  console.log('JSON:' + JSON.stringify(R));
 }, 30);
}, 30);
"""


def _rodar_aceite_no_node(payload):
    import shutil as _sh
    import subprocess
    node = _sh.which("node")
    if not node:
        return None, u"PULADO -- sem node"
    import radai_consent as CS
    blocos = re.findall(r"(?s)<script>(.*?)</script>", CS.PAGINA_ACEITE)
    if len(blocos) != 1:
        return None, u"a pagina tem %d <script>, esperava 1" % len(blocos)
    js = (_ACEITE_DUBLES_JS.replace(u"@PAYLOAD@",
                                    json.dumps(payload, ensure_ascii=False))
          + blocos[0] + _ACEITE_RODA_JS)
    d = tempfile.mkdtemp(prefix="radai_aceite_js_")
    alvo = os.path.join(d, "aceite.js")
    try:
        io.open(alvo, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, alvo], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        for ln in reversed((r.stdout or u"").splitlines()):
            if ln.startswith(u"JSON:"):
                return json.loads(ln[5:]), None
        return None, ((r.stderr or u"") + (r.stdout or u""))[-400:]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def teste_o_aceite_fala_o_idioma_da_tela():
    secao(u"o aceite fala o idioma da tela (e nao cita sufixo que saiu)")
    import radai_consent as CS

    suf = _sufixos_do_registro()
    det = [d for (c, _t, d) in CS.PONTOS if c == u"unapproved"]
    lista = u"(" + u", ".join(suf) + u")"
    checar(u"o ponto `unapproved` lista os sufixos do registro %s" % lista,
           bool(det) and lista in det[0],
           (det[0][60:140] if det else u"sem o ponto"))
    todos = u" ".join(t + u" " + d for (_c, t, d) in CS.PONTOS)
    import radai_sets
    velhos = [s for s in getattr(radai_sets, "SUFIXOS_APOSENTADOS", ())
              if re.search(re.escape(s) + r"\b", todos)]
    checar(u"  e nenhum ponto cita sufixo aposentado",
           not velhos and u"_v3D" not in todos, u", ".join(velhos))

    fontes = CS.fontes_de_terceiros()
    frases = [x for (_c, t, d) in CS.PONTOS for x in (t, d)]
    frases += [x for f in fontes for x in (f["nome"], f["licenca"])]
    pend = _pontos_pendentes(CS.PONTOS)
    faltam = [f for f in _sem_traducao(frases) if f not in pend]
    checar(u"os %d textos de /api/aceite tem chave nos doze idiomas (fora "
           u"%d pendente(s) da onda de traducao)" % (len(frases), len(pend)),
           not faltam, u" | ".join(f[:48] for f in faltam[:3]))
    traduzidos = [f for f in pend if not _sem_traducao([f])]
    checar(u"  e cada pendente continua sem traducao (traduzido, o ponto "
           u"sai de PONTOS_PENDENTES_DA_TRADUCAO)", not traduzidos,
           u" | ".join(f[:48] for f in traduzidos[:3]))
    checar(u"  isca: um ponto que nao existe na lista de pendentes nao "
           u"isenta nada", _pontos_pendentes(
               CS.PONTOS, {"zz_nao_existe": "detalhe"}) == [])
    checar(u"  e a checagem ainda sabe reprovar (isca)",
           _sem_traducao([u"ZZQX licenca que ninguem traduziu ZZQX"])
           == [u"ZZQX licenca que ninguem traduziu ZZQX"])

    payload = {"aceito": False, "versao": CS.VERSAO_DOCS,
               "data": CS.DATA_DOCS,
               "pontos": [{"chave": c, "titulo": t, "detalhe": d,
                           "sinal": CS.sinal_do_ponto(c)}
                          for (c, t, d) in CS.PONTOS],
               "fontes": fontes,
               "registro": {"versao": u"0.9", "quando": u"2026-01-02 03:04"}}
    d, erro = _rodar_aceite_no_node(payload)
    checar(u"o script da pagina executa no node", d is not None, erro or u"")
    if d is None:
        return

    nos = _nos_de_texto(d["fontes"])
    checar(u"a caixa pinta nome e licenca em nos separados (%d nos)" % len(nos),
           len(nos) == 2 * len(fontes), str(nos[:4])[:120])
    sem = _sem_traducao(nos)
    checar(u"  e cada no casa uma chave traduzida (a licenca em ingles)",
           not sem, u" | ".join(s[:50] for s in sem[:3]))

    nos = _nos_de_texto(d["mudou"])
    rotulos = [n for n in nos if not _sem_traducao([n])]
    resto = [n for n in nos if _sem_traducao([n])]
    for v in (u"0.9", u"2026-01-02 03:04", CS.VERSAO_DOCS, CS.DATA_DOCS):
        resto = [r.replace(v, u"") for r in resto]
    com_letra = [r for r in resto if re.search(u"[A-Za-zÀ-ÿ]", r)]
    checar(u"o aviso de versao tem os rotulos com chave (%d)" % len(rotulos),
           len(rotulos) >= 3, str(nos)[:160])
    checar(u"  e fora deles so ha valor (versao, data, pontuacao)",
           not com_letra, str(com_letra)[:120])

    depois = [o for o in d["carga"] if o.startswith(u"retraduzir:")
              and int(o.split(u":")[1]) > 0]
    checar(u"o tradutor e chamado depois de a caixa ser pintada",
           bool(depois), str(d["carga"]))

    checar(u"«registrando…» passa por uiTexto e tem chave",
           u"uiTexto:registrando…" in d["entrar"]
           and not _sem_traducao([u"registrando…"]), str(d["entrar"])[:120])
    frase = u"Não consegui registrar o aceite."
    checar(u"a falha escreve a frase num no marcado, pelo uiHTML",
           u"uiHTML" in d["entrar"]
           and (u"<span data-radai-frase>%s</span>" % frase) in d["falha"]
           and not _sem_traducao([frase]), d["falha"][:120])
    checar(u"  e o motivo vai sozinho no <code>, que nao se traduz",
           u"<code>faltam confirmar: deteccao</code>" in d["falha"],
           d["falha"][:120])
    checar(u"  e o botao volta a ligar", d["bt_religado"])



def _plano(html):
    import radai_consent as CS
    return CS._visivel(html)


def _documentos():
    import radai_consent as CS
    import radai_credits as CR
    pontos = u" ".join(t + u" " + d for (_c, t, d) in CS.PONTOS)
    pesos = u" ".join((f.get("nome") or u"") + u" " + (f.get("licenca") or u"")
                      for f in CS.fontes_de_terceiros())
    return [(u"termos", _plano(CS.TERMOS)),
            (u"politica", _plano(CS.POLITICA)),
            (u"creditos", _plano(CR.pagina())),
            (u"NOTICE", u" ".join(ler("NOTICE").split())),
            (u"README", u" ".join(ler("README.md").split())),
            (u"aceite", _plano(CS.PAGINA_ACEITE)),
            (u"pontos", pontos),
            (u"pesos", pesos)]


FORA_DO_PACOTE = (u"nninteractive", u"vista-3d", u"vista3d")
_EMBARCADO_FORA = re.compile(
    u"(?i)\\b(?:%s)\\b[^.;!?]{0,80}\\bembarcad" % u"|".join(
        re.escape(x) for x in FORA_DO_PACOTE))
_RESTRITO_UNICO = re.compile(
    u"(?i)\\b(?:[úu]nico|outro) componente (?:de uso )?restrito")


def _afirma_fora_do_pacote(texto):
    m = _EMBARCADO_FORA.search(texto) or _RESTRITO_UNICO.search(texto)
    return m.group(0) if m else None


_AUTORIA_ERRADA = re.compile(
    u"(?i)\\bputz\\b\\.?\\s*(?:f\\.?\\s*)?(?:et\\s+al|e\\s+col|and\\s+col|i\\s+wsp)"
    u"|(?:modelo|model|pesos|weights|artigo)\\s+(?:de|do|of|by)\\s+putz\\b"
    u"|\\bgrigo\\b")


def _cita_putz_como_autor(texto):
    m = _AUTORIA_ERRADA.search(texto or u"")
    return m.group(0) if m else None


def teste_documentos_nao_dizem_o_que_saiu():
    secao(u"documentos: o que saiu nao e dito embarcado, e a citacao e Weissmann")
    docs = _documentos()
    for nome, txt in docs:
        achou = _afirma_fora_do_pacote(txt)
        checar(u"%s: nao diz embarcado um componente que saiu" % nome,
               achou is None, achou or u"")
        achou = _cita_putz_como_autor(txt)
        checar(u"%s: nao cita «Putz et al.» como autoria" % nome,
               achou is None, achou or u"")
    bib = json.load(io.open(os.path.join(RAIZ, "app", "data",
                                         "bibliography.json"),
                            encoding="utf-8"))
    nomes = u" ".join((m.get("nome") or u"") for m in bib.get("modelos") or [])
    checar(u"bibliografia: o nome dos modelos nao cita «Putz et al.»",
           _cita_putz_como_autor(nomes) is None, nomes[-120:])
    hnl = [a for a in bib.get("artigos") or []
           if "1115258" in str(a.get("doi") or "")]
    checar(u"bibliografia: o artigo dos niveis tem Weissmann como 1o autor",
           bool(hnl) and str(hnl[0].get("autores") or "").startswith(
               u"Weissmann T"), str(hnl[:1])[:120])
    for nome, txt in docs:
        if nome in (u"termos", u"creditos", u"NOTICE", u"README", u"pontos"):
            checar(u"%s: cita Weissmann et al." % nome,
                   u"Weissmann et al." in txt)
    checar(u"NOTICE: com a revista e o DOI do artigo",
           u"Frontiers in Oncology" in ler("NOTICE")
           and u"10.3389/fonc.2023.1115258" in ler("NOTICE"))

    for frase in (u"nnInteractive (DKFZ) — embarcado, e é o outro componente "
                  u"restrito.",
                  u"E O UNICO COMPONENTE DE USO RESTRITO DESTE PACOTE",
                  u"a inferência do VISTA-3D, embarcado, roda dos pesos"):
        checar(u"  isca: acusa %r" % frase[:40],
               _afirma_fora_do_pacote(u" ".join(frase.split())) is not None)
    checar(u"  e nao acusa o que diz que ficou fora",
           _afirma_fora_do_pacote(
               u"nnInteractive (DKFZ) — pesos CC BY-NC-SA 4.0. Fica fora do "
               u"pacote. NV-Segment-CT — embarcado, 832 MB.") is None)
    for frase in (u"Níveis linfonodais (Putz et al.)",
                  u"Putz F. et al. Deep learning-based autosegmentation",
                  u"o modelo de Putz", u"Putz F, Grigo J, Weissmann T"):
        checar(u"  isca: acusa %r" % frase[:40],
               _cita_putz_como_autor(frase) is not None)
    checar(u"  e nao acusa a lista de autores nem o repositorio",
           _cita_putz_como_autor(
               u"Bert C., Fietkau R., Putz F. Deep learning ... "
               u"https://github.com/putzfn/HNLNL") is None)


def teste_impressao_publicada():
    secao(u"a impressao do texto aceito e a publicada para a versao")
    import radai_consent as CS
    atual = CS.impressao_dos_documentos()
    pub = CS.IMPRESSOES_PUBLICADAS.get(CS.VERSAO_DOCS)
    checar(u"ha impressao publicada para a versao %s" % CS.VERSAO_DOCS,
           bool(pub) and len(str(pub)) == 64, repr(pub)[:30])
    checar_doc("impressao", u"e ela e a do texto atual",
           pub == atual,
           u"atual %s — o texto aceito mudou: suba VERSAO_DOCS e acrescente "
           u"a impressao nova em IMPRESSOES_PUBLICADAS, ou troque a da versao "
           u"atual com o porque escrito ao lado" % atual)
    checar(u"a impressao e SHA-256 (64 hex)",
           bool(re.match(u"^[0-9a-f]{64}$", atual)), atual[:20])

    def muda(nome, attr, novo_valor):
        antigo = getattr(CS, attr)
        try:
            setattr(CS, attr, novo_valor)
            outra = CS.impressao_dos_documentos()
        finally:
            setattr(CS, attr, antigo)
        checar(u"  mudar %s muda a impressao" % nome, outra != atual)

    muda(u"uma palavra dos Termos", "TERMOS",
         CS.TERMOS.replace(u"Uso responsável", u"Uso atento"))
    muda(u"uma palavra da Politica", "POLITICA",
         CS.POLITICA.replace(u"Direitos do titular", u"Direitos"))
    muda(u"o detalhe de um ponto", "PONTOS",
         [(c, t, d + u" x") if c == u"local" else (c, t, d)
          for (c, t, d) in CS.PONTOS])
    muda(u"a frase da tela do aceite", "PAGINA_ACEITE",
         CS.PAGINA_ACEITE.replace(u"Entrar", u"Continuar"))
    import radai_credits as CR
    _ler = CR.ler_notice
    try:
        CR.ler_notice = lambda: _ler() + u"\nlinha nova do NOTICE"
        checar(u"  mudar o NOTICE muda a impressao",
               CS.impressao_dos_documentos() != atual)
    finally:
        CR.ler_notice = _ler

    def nao_muda(nome, attr, novo_valor):
        antigo = getattr(CS, attr)
        try:
            setattr(CS, attr, novo_valor)
            outra = CS.impressao_dos_documentos()
        finally:
            setattr(CS, attr, antigo)
        checar(u"  %s NAO muda a impressao" % nome, outra == atual)

    nao_muda(u"folha de estilo", "TERMOS",
             CS.TERMOS.replace(u"</style>", u".x{color:red}</style>", 1))
    nao_muda(u"comentario de HTML", "PAGINA_ACEITE",
             CS.PAGINA_ACEITE.replace(u"<div class=\"ac-lang\">",
                                      u"<!-- nota --><div class=\"ac-lang\">"))
    nao_muda(u"JavaScript", "PAGINA_ACEITE",
             CS.PAGINA_ACEITE.replace(u"var AC_PONTOS = [];",
                                      u"var AC_PONTOS = []; var AC_X = 1;"))
    nao_muda(u"quebra de linha e espaco", "POLITICA",
             CS.POLITICA.replace(u"Direitos do titular",
                                 u"Direitos\n   do   titular"))


def _url_versoes_de_fabrica():
    try:
        import radai_version as RV
    except Exception:
        return None
    u = str(getattr(RV, "URL_VERSOES", "") or "").strip()
    return u or None


_URL_HOST = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://(?:[^/\s@'\"<>|]*@)?([^/\s:'\"<>|)\]]+)")
_NOME_COM_PONTO = re.compile(
    r"(?i)(?<![\w.@/\\-])((?:[a-z0-9-]+\.)+[a-z][a-z0-9-]*[a-z0-9])(?![\w-])")
_IPV4 = re.compile(r"(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?![\d.])")
_EXTENSOES = frozenset((
    "py", "pyc", "json", "jsonl", "txt", "log", "dcm", "zip", "gz", "nii",
    "cmd", "bat", "ps1", "md", "html", "htm", "js", "css", "exe", "dll",
    "cfg", "config", "ini", "yaml", "yml", "xml", "csv", "pt", "pth", "png",
    "jpg", "jpeg", "pdf", "whl", "tmp", "lock"))


def _destinos(texto):
    t = texto or u""
    fora = set(h.lower().rstrip(u".") for h in _URL_HOST.findall(t))
    for h in _NOME_COM_PONTO.findall(t):
        if h.rsplit(u".", 1)[-1].lower() not in _EXTENSOES:
            fora.add(h.lower())
    fora.update(_IPV4.findall(t))
    return fora


def _divergencia(politica, arranque):
    return sorted(arranque - politica), sorted(politica - arranque)


def teste_conexoes_da_politica():
    secao(u"a Politica declara as conexoes que o codigo faz sozinho")
    import radai_consent as CS
    m = re.search(r'(?s)<ul id="conexoes-automaticas">(.*?)</ul>', CS.POLITICA)
    checar(u"a Politica tem a lista de conexoes automaticas", m is not None)
    pol = _destinos(_plano(m.group(1))) if m else set()
    checar(u"  e ela nao esta vazia", bool(pol), str(pol))

    url = _url_versoes_de_fabrica()
    checar(u"li o URL_VERSOES de fabrica (radai_version.URL_VERSOES)",
           bool(url), repr(url))
    _velho_env = os.environ.pop("RADAI_URL_VERSOES", None)
    try:
        import radai_arranque
        linhas = radai_arranque.chamadas_de_rede({})
    except Exception as e:
        linhas = None
        checar(u"`radai_arranque.chamadas_de_rede` roda", False,
               u"%s: %s" % (type(e).__name__, str(e)[:100]))
    finally:
        if _velho_env is not None:
            os.environ["RADAI_URL_VERSOES"] = _velho_env
    if linhas is not None:
        arr = _destinos(u" ".join(linhas))
        checar(u"o codigo declara destinos", bool(arr), u" | ".join(linhas)[:160])
        faltam, sobram = _divergencia(pol, arr)
        checar(u"todo destino do codigo esta na Politica", not faltam,
               u"faltam na Politica: %s" % faltam)
        checar(u"e todo destino da Politica existe no codigo", not sobram,
               u"a Politica declara o que o codigo nao faz: %s" % sobram)
        checar(u"nenhuma linha do codigo diz «nao sei»",
               not [l for l in linhas if u"nao sei" in l],
               u" | ".join(l for l in linhas if u"nao sei" in l)[:160])

    base = {u"api.github.com", u"pypi.org", u"github.com"}
    f, s = _divergencia(base, base | {u"stats.totalsegmentator.com"})
    checar(u"  isca: conexao nova no codigo e acusada", f == [
        u"stats.totalsegmentator.com"], str(f))
    f, s = _divergencia(base | {u"exemplo.org"}, base)
    checar(u"  isca: destino a mais na Politica e acusado",
           s == [u"exemplo.org"], str(s))

    for linha, esperado in (
            (u"telemetria: POST https://telemetria.exemplo.de/x | quando: "
             u"a cada serie", {u"telemetria.exemplo.de"}),
            (u"envia a 10.0.0.5:8080 o radai_version.py e o index.json",
             {u"10.0.0.5"}),
            (u"DNS + TCP 443 a coleta.exemplo.health e a status.exemplo.dev",
             {u"coleta.exemplo.health", u"status.exemplo.dev"}),
            (u"le o radai_records.py, grava o caso.json e o log.txt "
             u"(TotalSegmentator 2.18.0, v8.1)", set())):
        achou = _destinos(linha)
        checar(u"  isca: o leitor acha %s" % (sorted(esperado) or u"nada"),
               achou == esperado, u"achou %s" % sorted(achou))
    if linhas is not None:
        f, s = _divergencia(pol, _destinos(u" ".join(
            list(linhas) + [u"telemetria: POST https://telemetria.exemplo.de/x"])))
        checar(u"  isca: uma linha nova de verdade no codigo, com host .de, "
               u"reprova a Politica", f == [u"telemetria.exemplo.de"], str(f))

    _estr = getattr(sys.modules.get("radai_arranque"), "destinos_de_rede", None)
    if _estr is not None and linhas is not None:
        try:
            est = set(h.lower() for h in _estr({"url_versoes": url or u""}))
            checar(u"os destinos estruturados do arranque sao os do texto",
                   est == _destinos(u" ".join(linhas)),
                   u"%s x %s" % (sorted(est), sorted(_destinos(u" ".join(linhas)))))
        except Exception as e:
            checar(u"radai_arranque.destinos_de_rede roda", False,
                   u"%s: %s" % (type(e).__name__, str(e)[:100]))

    lista = _plano(m.group(1)) if m else u""
    try:
        import radai_version as RV
        import radai_records as RR
        checar(u"o User-Agent declarado e o que a consulta manda",
               RV.USER_AGENT in lista, RV.USER_AGENT)
        mins = int(round(RR._INTERNET_VALIDADE_S / 60.0))
        checar(u"a frequencia do teste de internet e a do codigo (%d min)"
               % mins, (u"%d minutos" % mins) in lista, lista[-200:])
        checar(u"e a porta tambem (%d)" % RR.INTERNET_PORTA,
               (u"porta %d" % RR.INTERNET_PORTA) in lista)
    except Exception as e:
        checar(u"radai_version e radai_records importam", False,
               u"%s: %s" % (type(e).__name__, str(e)[:80]))

    pol_txt = _plano(CS.POLITICA)
    checar(u"a Politica diz que a estatistica do TotalSegmentator fica "
           u"desligada",
           u"stats.totalsegmentator.com" in pol_txt
           and u"fica desligada" in pol_txt)
    checar(u"  e o envelope troca a funcao de envio",
           u"FUNCOES_DE_ENVIO" in ler("app/radai_ts_runner.py"))
    checar(u"  e o motor grava send_usage_stats=false no arquivo dela",
           u'"send_usage_stats"] = False' in ler("app/engine.py"))

    for velha in (u"As únicas conexões de saída possíveis",
                  u"sempre por ação explícita sua"):
        checar(u"a Politica nao diz %r" % velha[:36],
               velha.lower() not in pol_txt.lower())


def _tasks_de_achado_do_motor():
    m = re.search(r"(?ms)^TASKS_DE_ACHADO = frozenset\(\[(.*?)\]\)",
                  ler("app/engine.py"))
    if not m:
        return None
    corpo = u"\n".join(l.split(u"#")[0] for l in m.group(1).splitlines())
    return sorted(set(re.findall(r'"([a-z0-9_]+)"', corpo)))


def _achado_e_permitidas_do_motor():
    try:
        import engine as _eng
        return (sorted(_eng.TASKS_DE_ACHADO), dict(_eng.TASKS_PERMITIDAS),
                u"o objeto do motor")
    except Exception:
        pass
    permitidas = {}
    try:
        arv = ast.parse(ler("app/engine.py"))
        for no in arv.body:
            if (isinstance(no, ast.Assign) and len(no.targets) == 1
                    and getattr(no.targets[0], "id", None)
                    == "TASKS_PERMITIDAS"
                    and isinstance(no.value, ast.Dict)):
                for k in no.value.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value,
                                                                  str):
                        permitidas[k.value] = u""
    except SyntaxError:
        permitidas = {}
    return (_tasks_de_achado_do_motor() or [], permitidas,
            u"o fonte do motor, sem importa-lo")


def _vigia_le_o_tasks(src_vigia):
    src = src_vigia or u""
    obs = re.search(r"(?ms)^CHAVES_OBSOLETAS\s*=\s*\{(.*?)^\}", src)
    obsoleta = bool(obs and re.search(r'"TASKS"\s*:', obs.group(1)))
    return bool(re.search(r"(?m)^TASKS=", src)) and not obsoleta


def _tasks_como_ato_divergente(le, textos):
    return [u"%s %s o TASKS, e o vigia %s" % (
                nome, u"cita" if u"TASKS" in (t or u"") else u"nao cita",
                u"o le" if le else u"NAO o le")
            for nome, t in textos if (u"TASKS" in (t or u"")) is not le]


_MARCA_ATO_ESTUDO = u"protocolo de estudo das Reconstruções 3D"


def _ato_do_estudo_divergente(e_ato, textos):
    return [u"%s %s o estudo 3D como ato, e o codigo %s" % (
                nome, u"diz" if _MARCA_ATO_ESTUDO in (t or u"") else
                u"nao diz", u"o aceita" if e_ato else u"NAO o aceita")
            for nome, t in textos
            if (_MARCA_ATO_ESTUDO in (t or u"")) is not e_ato]


def _pre_marcacao_com_achado(pre, achados):
    fora = {}
    for cod, tasks in sorted((pre or {}).items()):
        intr = sorted(set(tasks or ()) & set(achados or ()))
        if intr:
            fora[cod] = intr
    return fora


def teste_o_que_os_documentos_afirmam():
    secao(u"os documentos descrevem o que o codigo faz (auditoria de 23/09)")
    import radai_consent as CS
    termos = _plano(CS.TERMOS)
    politica = _plano(CS.POLITICA)
    pontos = dict((c, t + u" " + d) for (c, t, d) in CS.PONTOS)
    todos = u" ".join(txt for _n, txt in _documentos())

    for velha in (u"Este programa não faz isso",
                  u"não exporta caso nenhum",
                  u"Não existe aqui função que copie imagem",
                  u"Não há função aqui que copie imagem",
                  u"É o único caminho pelo qual algo derivado de paciente",
                  u"As imagens não saem da estação"):
        checar(u"nenhum documento diz %r" % velha[:40],
               velha.lower() not in todos.lower())
    ferramentas = _ferramentas_do_bridge()
    checar(u"li o nome da ferramenta do DicomBridge, uma so desde o "
           u"pipeline unico (radai_modules)",
           len(ferramentas) == 1, repr(ferramentas))
    # GUARDA: o nome casa inteiro, entre as aspas angulares; um nome contido no antigo passaria por substring.
    nomeia = lambda doc, n: n is not None and u"«%s»" % n in doc
    for chave, nome in sorted(ferramentas.items()):
        antigo = NOMES_ATE_OS_DOCUMENTOS_1_7.get(chave)
        checar(u"a Politica nomeia a ferramenta «%s» (%s)" % (nome, chave),
               nomeia(politica, nome) or nomeia(politica, antigo),
               u"nome novo sem documento novo: declare em NOMES_ATE_OS_DOCUMENTOS_1_7")
    for chave, antigo in sorted(NOMES_ATE_OS_DOCUMENTOS_1_7.items()):
        checar(u"  a pendencia «%s» ainda e pendencia (a 1.6 diz o nome antigo)"
               % antigo, not nomeia(politica, ferramentas.get(chave))
               and nomeia(politica, antigo),
               u"a Politica ja diz o nome novo: tire a entrada da lista")
    checar(u"  (isca) o nome contido no antigo nao conta como nomeado",
           not nomeia(u"«Conversão de imagens para o TPS»",
                      u"Conversão de imagens"))
    for saida in (u"registro de casos", u"OUT_DIR", u"STATUS_DIR"):
        checar(u"a Politica nomeia a saida «%s»" % saida, saida in politica)
    checar(u"e diz que a exportacao leva nome, registro e nascimento",
           u"nome, o registro e a data de nascimento" in politica)
    for mod in ("radai_dicom.py", "radai_image.py"):
        checar(u"  e o %s recusa destino que sincroniza (o que a Politica "
               u"afirma)" % mod,
               u"em_pasta_sincronizada(destino)" in ler("app/" + mod))
    checar(u"o ponto `exportar` diz que o que sai identifica",
           u"identificar o paciente" in pontos.get(u"exportar", u""))

    checar(u"a Politica cita o indice em %LOCALAPPDATA%",
           u"%LOCALAPPDATA%\\RadAI_Watcher\\index.json" in politica)
    vig = ler("app/radai_watcher.py")
    checar(u"  e e la que o vigia o grava",
           u'"RadAI_Watcher"' in vig and u'"index.json"' in vig)
    un = ler("installer/UNINSTALL.ps1")
    div = _desinstalador_divergente(un, politica)
    checar(u"o desinstalador: o que ele lista fora da pasta e o -ApagarFora "
           u"sao os do UNINSTALL.ps1, e a Politica (secao 6) diz",
           not div, u" | ".join(div))
    checar(u"  isca: o UNINSTALL sem o cache deslocado, com a Politica de "
           u"hoje: reprova", bool(_desinstalador_divergente(
               un.replace(u'"cache_tasks"', u'"x"'), politica)))
    checar(u"  isca: o UNINSTALL sem o -ApagarFora: reprova",
           bool(_desinstalador_divergente(
               un.replace(u"[switch]$ApagarFora", u"[switch]$Outro"),
               politica)))
    checar(u"  isca: a Politica cala os motor_<porta>.json: reprova",
           bool(_desinstalador_divergente(un, politica.replace(
               _MARCAS_DO_DESINSTALADOR["motor_json"], u"X"))))
    for guardado in (u"calibracao", u"registro", u"radai_watcher.config"):
        checar(u"  e o que ele oferece guardar e o que o UNINSTALL guarda "
               u"(%s)" % guardado, (u'"%s"' % guardado) in un)
    checar(u"os Termos nao dizem que desinstalar nao deixa rastro",
           u"não deixa rastro" not in termos)

    for velha in (u"roda sempre o modo Padrão", u"usa o modo Padrão",
                  u"lote da noite roda sempre",
                  u"modo Completo", u"como ela está escrita",
                  u"Complete mode"):
        checar(u"nenhum documento diz %r" % velha[:36],
               velha.lower() not in todos.lower())
    _tem_estudos = u"ESTUDOS = (" in ler("app/radai_modes.py")
    checar(u"nenhum documento manda marcar a caixa «dentro do estudo» se, e "
           u"so se, os estudos sairam do «Rodar agora»",
           (u"dentro do estudo" in todos) is _tem_estudos,
           u"estudos no codigo=%s" % _tem_estudos)
    _marca_ato = {u"termos": u"ligar a chave da tarefa no PERSONALIZADO",
                  u"deteccao": u"ligar a chave dela no PERSONALIZADO"}
    # GUARDA: o TASKS do config so pode aparecer como ato se o vigia o le; a
    # lista das chaves obsoletas dos Termos e o unico lugar em que ele fica.
    _le = _vigia_le_o_tasks(vig)
    _sem_obsoletas = termos.replace(
        _trecho(termos, _INICIO_OBSOLETAS, _FIM_OBSOLETAS) or u"\x00", u"")
    _textos_do_ato = [(u"termos", _sem_obsoletas),
                      (u"deteccao", pontos.get(u"deteccao", u""))]
    div = _tasks_como_ato_divergente(_le, _textos_do_ato)
    checar(u"os Termos (fora das obsoletas) e o ponto citam o TASKS do config "
           u"se, e so se, o vigia o le (medido: %s)" % _le, not div,
           u" | ".join(div))
    for nome, txt in _textos_do_ato:
        checar(u"%s: diz que a CHAVE da tarefa no PERSONALIZADO liga" % nome,
               _marca_ato[nome] in txt, _marca_ato[nome])
        checar(u"%s: diz que a noite decide pela anatomia que a base "
               u"desenhou, e nunca por achado" % nome,
               u"anatomia" in txt and u"base" in txt
               and (u"nenhuma de achado" in txt
                    or u"nunca uma de achado" in txt))
    _vig_le = re.sub(r'(?m)^    "TASKS": u"[^\n]*\n[^\n]*\n', u"", vig, count=1)
    _vig_le = _vig_le.replace(u"ROOT=\n", u"ROOT=\nTASKS=total_v3\n", 1)
    checar(u"  isca: o vigia volta a ler o TASKS (fora das obsoletas e no "
           u"DEFAULT_CFG), com os textos de hoje: reprova",
           _vigia_le_o_tasks(_vig_le)
           and bool(_tasks_como_ato_divergente(True, _textos_do_ato)))
    checar(u"  isca: so no DEFAULT_CFG, e ainda obsoleta, nao conta como lida",
           not _vigia_le_o_tasks(vig.replace(u"ROOT=\n",
                                             u"ROOT=\nTASKS=total_v3\n", 1)))
    checar(u"  isca: o ponto volta a mandar escrever na lista TASKS, com o "
           u"vigia de hoje: reprova", bool(_tasks_como_ato_divergente(
               _le, [(u"deteccao", pontos.get(u"deteccao", u"")
                      + u" escrever o nome dela na lista TASKS")])))
    _achados, _permitidas, _de_onde = _achado_e_permitidas_do_motor()
    checar(u"li a lista de achado e a de permitidas do motor (%s)" % _de_onde,
           bool(_achados) and bool(_permitidas))
    try:
        import radai_modes as MD
        import radai_tasks as RT
        esc = MD.tasks_do_personalizado((), {"liver_lesions_mr": 1}, "MR",
                                        permitidas=_permitidas,
                                        achados=_achados,
                                        catalogo=RT.CATALOGO)
        checar(u"  e e verdade: a caixa marcada (RM, liver_lesions_mr) roda "
               u"a task de achado junto da base",
               tuple(esc) == ("total_mr", "liver_lesions_mr"), str(esc))
        pre = dict((p["cod"], tuple(p.get("tasks") or ()))
                   for p in MD.PROTOCOLOS)
        intrusas = _pre_marcacao_com_achado(pre, _achados)
        checar(u"  e nenhum protocolo arrasta achado sozinho (%d protocolos)"
               % len(pre), bool(pre) and not intrusas, str(intrusas))
        levantou = False
        try:
            MD.conferir_regra_a(MD.ANATOMIA,
                                ["total_v3", "trunk_cavities", "lung_nodules"],
                                _achados)
        except MD.AchadoSemPedido:
            levantou = True
        checar(u"  e a tabela da noite (origem ANATOMIA) recusa achado",
               levantou)
        _forjada = dict(pre)
        _forjada["torax_mama"] = (tuple(pre.get("torax_mama", ()))
                                  + ("lung_nodules",))
        checar(u"  isca: o protocolo Torax / Mama forjado arrastando "
               u"lung_nodules e acusado pela mesma conta",
               _pre_marcacao_com_achado(_forjada, _achados)
               == {"torax_mama": ["lung_nodules"]},
               str(_pre_marcacao_com_achado(_forjada, _achados)))
        _ato_ok = True
        try:
            MD.conferir_regra_a(MD.MARCADO,
                                ["total_v3", "lung_nodules"], _achados)
        except MD.AchadoSemPedido:
            _ato_ok = False
        checar(u"  isca: a MESMA lista com a origem do ato (a caixa) passa — "
               u"a trava julga quem montou, e nao a lista", _ato_ok)
        _estudo = getattr(MD, "ESTUDO", None)
        _e_ato = bool(_estudo)
        try:
            MD.conferir_regra_a(_estudo, ["total_v3", "lung_nodules"],
                                _achados)
        except MD.AchadoSemPedido:
            _e_ato = False
        _txt_estudo = [(u"termos", termos),
                       (u"deteccao", pontos.get(u"deteccao", u""))]
        div = _ato_do_estudo_divergente(_e_ato, _txt_estudo)
        checar(u"o protocolo de estudo das Reconstrucoes 3D e ato declarado "
               u"(medido: %s), e os Termos e o ponto dizem" % _e_ato, not div,
               u" | ".join(div))
        checar(u"  isca: o estudo deixa de ser ato no codigo, com os textos de "
               u"hoje: reprova", bool(_ato_do_estudo_divergente(
                   not _e_ato, _txt_estudo)))
        checar(u"  isca: os Termos calam o estudo 3D: reprova",
               bool(_ato_do_estudo_divergente(_e_ato, [(u"termos", termos.replace(
                   _MARCA_ATO_ESTUDO, u"X"))])))
    except Exception as e:
        checar(u"  radai_modes responde", False,
               u"%s: %s" % (type(e).__name__, str(e)[:80]))

    for nome, txt in ((u"termos", termos), (u"deteccao",
                                            pontos.get(u"deteccao", u""))):
        checar(u"%s: diz que os cistos renais vem de fabrica" % nome,
               u"cistos renais" in txt and u"desenhar não é afirmar"
               in txt.lower())
    checar(u"  e e verdade: a base de anatomia os mapeia",
           u'"kidney_cyst_left": {"total"' in ler("app/engine.py"))

    achado = _tasks_de_achado_do_motor()
    checar(u"li `TASKS_DE_ACHADO` do motor", bool(achado), repr(achado))
    for t in achado or ():
        checar(u"os Termos listam a tarefa de achado `%s`" % t,
               (u"<code>%s</code>" % t) in CS.TERMOS)
    for velha in (u"cerebral_bleed", u"liver_vessels"):
        checar(u"os Termos nao listam `%s`, que saiu" % velha,
               velha not in CS.TERMOS)

    checar(u"os Termos nao dizem que as calibracoes sao todas de literatura",
           u"As calibrações são regras de literatura publicada" not in termos)
    checar(u"e dizem que ha parametro nosso, declarado",
           u"declarados como nossos" in termos)
    checar(u"os Termos dizem codigo ABERTO, e nao «publico»",
           u"O código é público" not in termos
           and u"código é aberto" in termos)
    checar(u"os Termos nao dizem que a licenca integra viaja em cada pasta",
           u"íntegra de cada um viaja" not in termos)

    for nome, txt in ((u"termos", termos), (u"NOTICE", ler("NOTICE"))):
        checar(u"%s: descreve o recorte no corpo (body_seg, 6 mm)" % nome,
               u"body_seg" in txt and u"6 mm" in txt)
        checar(u"%s: e a chave que o liga (RECORTE_NO_CORPO)" % nome,
               u"RECORTE_NO_CORPO" in txt)
    checar(u"  e e verdade: o config de fabrica nasce com RECORTE_NO_CORPO=1",
           bool(re.search(r"(?m)^RECORTE_NO_CORPO=1\s*$", vig)))
    _obs = re.search(r"(?ms)^CHAVES_OBSOLETAS\s*=\s*\{(.*?)^\}", vig)
    _gatilho = _corpo_da_funcao(vig, "_niveis_cervicais_nesta_serie")
    checar(u"  e os niveis cervicais rodam pela anatomia, sem chave na "
           u"estacao (INCLUIR_HNLNL em CHAVES_OBSOLETAS)",
           not re.search(r"(?m)^INCLUIR_HNLNL=", vig)
           and bool(_obs) and u'"INCLUIR_HNLNL"' in _obs.group(1)
           and u"pescoco_no_campo(" in _gatilho,
           u"obsoleta=%s gatilho=%s" % (bool(_obs and u'"INCLUIR_HNLNL"'
                                             in _obs.group(1)),
                                        u"pescoco_no_campo(" in _gatilho))

    _pelo_pescoco = (u"pescoco_no_campo(" in _gatilho
                     and not re.search(r"(?m)^INCLUIR_HNLNL=", vig))
    for nome, txt, marca in (
            (u"termos", termos, u"quando o pescoço é detectado"),
            (u"NOTICE", u" ".join(ler("NOTICE").split()),
             u"quando o pescoco e detectado")):
        checar(u"%s: niveis com nome neutro LNL01..LNL20" % nome,
               u"LNL01" in txt and u"LNL20" in txt)
        checar(u"%s: diz que rodam quando o pescoco e detectado se, e so se, "
               u"o vigia os roda pela anatomia" % nome,
               (marca in txt) is _pelo_pescoco,
               u"codigo pelo pescoco=%s" % _pelo_pescoco)
    checar(u"NOTICE: nao cita INCLUIR_HNLNL, que saiu do config",
           u"INCLUIR_HNLNL" not in ler("NOTICE"))


# GUARDA: documento publicado não se retoca; o nome novo do cartão espera a versão seguinte, e a checagem reprova a entrada que deixou de ser pendência.
NOMES_ATE_OS_DOCUMENTOS_1_7 = {}


def _ferramentas_do_bridge():
    src = ler("app/radai_modules.py")
    return dict(re.findall(
        r'\("(bridge_[a-z]+)",\s*u"[^"]*",\s*u"([^"]+)"', src))


def _corpo_da_funcao(src, nome):
    m = re.search(r"(?ms)^def %s\(.*?(?=^def |^class |\Z)" % re.escape(nome),
                  src or u"")
    return m.group(0) if m else u""


def _status_dir_coerente(corpo_salvar_status, politica):
    cru = u'"worker_erro": STATE["worker_erro"]' in corpo_salvar_status
    declara = u"mensagem do erro" in politica
    return cru == declara, (u"o vigia grava o erro %s e a Politica %s o declara"
                            % (u"cru" if cru else u"higienizado",
                               u"" if declara else u"NAO"))


def _referencias(no, nome):
    return [n for n in ast.walk(no)
            if isinstance(getattr(n, "ctx", None), ast.Load)
            and ((isinstance(n, ast.Name) and n.id == nome)
                 or (isinstance(n, ast.Attribute) and n.attr == nome))]


def _testa_root(expr):
    return any(isinstance(n, ast.Name) and n.id == "ROOT"
               for n in ast.walk(expr))


def _depende_do_root(ref, pais, dono):
    no, topo = ref, ref
    while no is not None and no is not dono:
        if (isinstance(no, (ast.If, ast.While, ast.IfExp))
                and _testa_root(no.test)):
            return True
        topo, no = no, pais.get(no)
    corpo = [st for st in getattr(dono, "body", [])]
    for st in corpo:
        if st is topo:
            break
        if (isinstance(st, ast.If) and _testa_root(st.test)
                and any(isinstance(n, ast.Return) for n in ast.walk(st))):
            return True
    return False


def _faxina_do_arranque(vig):
    r = {"chamada": False, "sem_root": False, "horas": None,
         "prefixo": None, "olha_pasta": False, "apaga_arquivo": []}
    try:
        arv = ast.parse(vig)
    except SyntaxError:
        return r
    pais = {}
    for no in ast.walk(arv):
        for filho in ast.iter_child_nodes(no):
            pais[filho] = no
    defs = dict((n.name, n) for n in arv.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    lt = defs.get("limpar_temporarios")
    wl = defs.get("worker_loop")

    if lt is not None:
        for n in ast.walk(lt):
            if (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult)
                    and all(isinstance(x, ast.Constant)
                            and type(x.value) is int
                            for x in (n.left, n.right))
                    and 3600 in (n.left.value, n.right.value)):
                r["horas"] = (n.right.value if n.left.value == 3600
                              else n.left.value)
            elif (isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "glob" and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str)):
                v = n.args[0].value
                if v.endswith("*") and len(v) > 1 and "*" not in v[:-1]:
                    r["prefixo"] = v[:-1]
            if isinstance(n, ast.Attribute) and n.attr == "is_dir":
                r["olha_pasta"] = True
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Attribute) and (
                        f.attr == "unlink"
                        or (f.attr == "remove"
                            and isinstance(f.value, ast.Name)
                            and f.value.id == "os")):
                    r["apaga_arquivo"].append(ast.unparse(f))
                elif isinstance(f, ast.Name) and f.id in ("remove",
                                                          "unlink"):
                    r["apaga_arquivo"].append(f.id)

    if wl is not None:
        refs = _referencias(wl, "limpar_temporarios")

        def _dentro_do_laco(no):
            while no is not None:
                if no is wl:
                    return True
                no = pais.get(no)
            return False

        def _dono(no):
            while pais.get(no) is not None and pais.get(no) is not arv:
                no = pais.get(no)
            return no if isinstance(no, (ast.FunctionDef,
                                         ast.AsyncFunctionDef)) else arv

        sobe = [x for x in _referencias(arv, "worker_loop")
                if not _dentro_do_laco(x)]
        r["chamada"] = bool(refs) and bool(sobe)
        r["sem_root"] = (
            any(not _depende_do_root(x, pais, wl) for x in refs)
            and any(not _depende_do_root(x, pais, _dono(x)) for x in sobe))
    return r


_FAXINA_DECLARA = u"no arranque do programa"
_FAXINA_SEM_ROOT = u"mesmo com o ROOT vazio"


def _faxina_coerente(vig, politica):
    f = _faxina_do_arranque(vig)
    declara = _FAXINA_DECLARA in politica
    if not f["chamada"]:
        return (not declara,
                u"nao achei referencia a limpar_temporarios dentro do "
                u"worker_loop (que o main sobe), e a Politica %s a declara. "
                u"Se ela saiu do arranque, tire a frase da Politica; se foi "
                u"para uma funcao auxiliar, ensine _faxina_do_arranque a "
                u"segui-la" % (u"ainda" if declara else u"nao"))
    if f["horas"] is None or not f["prefixo"]:
        return False, (u"nao consegui ler do fonte as horas (%s) ou o prefixo "
                       u"(%s) de limpar_temporarios"
                       % (f["horas"], f["prefixo"]))
    if not f["olha_pasta"] or f["apaga_arquivo"]:
        return False, (u"limpar_temporarios nao apaga so pasta (consulta "
                       u"is_dir: %s; apaga arquivo: %s), e a Politica diz "
                       u"«toda pasta»" % (f["olha_pasta"],
                                          u", ".join(f["apaga_arquivo"])
                                          or u"nao"))
    faltam = [x for x in (_FAXINA_DECLARA,
                          u"toda pasta cujo nome começa com %s" % f["prefixo"],
                          u"há mais de %d horas" % f["horas"])
              if x not in politica]
    diz_root = _FAXINA_SEM_ROOT in politica
    if diz_root != f["sem_root"]:
        faltam.append(u"a Politica %s «%s», e a faxina %s do ROOT" % (
            u"diz" if diz_root else u"nao diz", _FAXINA_SEM_ROOT,
            u"depende" if not f["sem_root"] else u"nao depende"))
    return (not faltam,
            u"o vigia apaga pasta %s* com mais de %d h%s; o que diverge da "
            u"Politica: %s" % (f["prefixo"], f["horas"],
                               u"" if f["sem_root"] else u" (so com ROOT)",
                               u" | ".join(faltam) or u"nada"))


_VIGIA_FANTOMA = u'''
import os, shutil, tempfile, threading, time
from pathlib import Path
ROOT = ""


def limpar_temporarios():
    raiz = Path(tempfile.gettempdir())
    limite = time.time() - 24 * 3600
    for p in raiz.glob("radai_*"):
@APAGA@


def worker_loop():
    wlog("arranque")
@CHAMA@
    while True:
        _uma_volta()


def main():
@SOBE@
'''
_FANT_APAGA = (u"        if p.is_dir() and p.stat().st_mtime < limite:\n"
               u"            shutil.rmtree(str(p), ignore_errors=True)")
_FANT_CHAMA = u"    limpar_temporarios()"
_FANT_SOBE = u"    threading.Thread(target=worker_loop, daemon=True).start()"


def _fantoma(apaga=_FANT_APAGA, chama=_FANT_CHAMA, sobe=_FANT_SOBE,
             extra=u""):
    return (_VIGIA_FANTOMA.replace(u"@APAGA@", apaga)
            .replace(u"@CHAMA@", chama).replace(u"@SOBE@", sobe) + extra)


_POR_EXTENSO = {5: u"cinco", 10: u"dez", 15: u"quinze", 30: u"trinta"}


def teste_as_saidas_e_o_descarte():
    secao(u"as saidas e o descarte: o que a revisao de 23/09 achou")
    import radai_consent as CS
    politica = _plano(CS.POLITICA)
    termos = _plano(CS.TERMOS)
    pontos = dict((c, t + u" " + d) for (c, t, d) in CS.PONTOS)
    vig = ler("app/radai_watcher.py")
    bridge = u" ".join(ler("app/radai_bridge.py").split())

    rotas_bridge = _rotas_servidas(ler("app/radai_bridge.py")
                                   + ler("app/radai_image_screen.py"))
    mortas = [r for r in _ROTAS_DO_BRIDGE_QUE_SAIRAM if r in rotas_bridge]
    checar(u"o DicomBridge nao serve mais a entrega pelo navegador nem as "
           u"rotas sem tela (li %d rotas)" % len(rotas_bridge),
           bool(rotas_bridge) and not mortas, u", ".join(mortas))
    checar(u"  isca: a rota /api/bridge/entregar de volta: a medida acusa",
           u"/api/bridge/entregar" in _rotas_servidas(
               u'@app.post("/api/bridge/entregar")'))
    citadas = [r for r in _ROTAS_DO_BRIDGE_QUE_SAIRAM if r in politica]
    checar(u"a Politica nao descreve rota do DicomBridge que saiu", not citadas,
           u", ".join(citadas))
    checar(u"  e nao fala mais da entrega pelo navegador",
           u"entrega pelo navegador" not in politica)
    _tela_entrega = _tela_chama_a_entrega_pelo_navegador(
        ler("app/radai_bridge.py") + ler("app/radai_image_screen.py"))
    checar(u"o ponto `exportar` diz o .zip que o navegador baixa se, e so "
           u"se, uma tela chama a entrega pelo navegador (medido: %s)"
           % _tela_entrega,
           (u".zip que o navegador baixa" in pontos.get(u"exportar", u""))
           is _tela_entrega)
    checar(u"  isca: uma tela volta a chamar /api/bridge/entregar: a "
           u"medida vira", _tela_chama_a_entrega_pelo_navegador(
               u"fetch('/api/bridge/entregar', {method:'POST'})") is True)
    checar(u"  e a medida nao conta a rota servida, so a chamada da tela",
           _tela_chama_a_entrega_pelo_navegador(
               u'@app.post("/api/bridge/entregar")') is False)
    checar(u"a frase velha do ponto nao volta (so pasta, sempre recusando)",
           u"na pasta que você escolher, e recusam pasta"
           not in pontos.get(u"exportar", u""))
    textos_bridge = u" ".join(_strings_do_fonte(ler("app/radai_bridge.py"))
                              + _strings_do_fonte(
                                  ler("app/radai_image_screen.py")))
    div = _botoes_do_bridge_divergentes(textos_bridge, politica)
    checar(u"os botoes do DicomBridge que a Politica cita sao os da tela, nos "
           u"dois sentidos", not div, u" | ".join(div))
    checar(u"  e a tela tem os botoes de hoje (li %d)"
           % sum(1 for r in _BOTOES_DO_BRIDGE if _tela_tem_o_botao(
               textos_bridge, r)),
           _tela_tem_o_botao(textos_bridge, u"Entregar")
           and not any(_tela_tem_o_botao(textos_bridge, r) for r in (
               u"Ajustar e finalizar", u"Baixar de novo")))
    checar(u"  isca: a Politica volta a citar «Baixar de novo»: reprova",
           bool(_botoes_do_bridge_divergentes(
               textos_bridge, politica + u" «Baixar de novo»")))
    checar(u"  isca: a tela perde «Entregar», com a Politica de hoje: "
           u"reprova", bool(_botoes_do_bridge_divergentes(
               textos_bridge.replace(u">Entregar<", u">X<"), politica)))
    src_e = ler("app/radai_bridge_entrada.py")
    v_e = _valores_do_modulo(src_e)
    nova = (u"_nome_livre(" in _fonte_da_funcao(src_e, "entregar")
            and u'"DICOM_BRIDGE_%Y%m%d_%H%M%S"' in src_e)
    checar(u"o DicomBridge entrega numa pasta nova, DICOM_BRIDGE_ com a data "
           u"e a hora (medido: %s), e a Politica diz" % nova,
           nova and u"numa pasta nova" in politica
           and u"DICOM_BRIDGE_ com a data e a hora" in politica
           and u"Não há .zip" in politica)
    checar(u"  e a Politica nao diz mais que o nome leva a descricao da serie",
           u"descrição da série, que é texto livre" not in politica)
    checar(u"a serie convertida espera a entrega em %s, e sai no descarte e "
           u"no fim do processo; a Politica (secoes 3 e 6) diz"
           % v_e.get("PASTA"),
           v_e.get("PASTA") == u"radai_bridge_entrada"
           and u"esquecer_conversao" in src_e
           and u"_CONVERSOES.values()" in _fonte_da_funcao(
               src_e, "_apagar_aberturas")
           and u"série que o DicomBridge converte" in politica
           and u"quando você a descarta" in politica)
    usam_entrega_tps = [n for n in _componentes.nomes("app")
                        if n.endswith(u".py") and n != u"radai_delivery_tps.py"
                        and _importa(ler(u"app/" + n), "radai_delivery_tps")]
    checar(u"nenhum modulo do app usa mais a entrega pelo navegador "
           u"(radai_delivery_tps)", not usam_entrega_tps,
           u", ".join(usam_entrega_tps))

    corpo = _corpo_da_funcao(vig, u"salvar_status")
    checar(u"li `salvar_status` do vigia", bool(corpo))
    ok, det = _status_dir_coerente(corpo, politica)
    checar(u"o STATUS_DIR: a Politica e o vigia concordam sobre a mensagem "
           u"de erro", ok, det)
    for rot, c, p, esperado in (
            (u"erro cru, Politica calada: reprova",
             u'"worker_erro": STATE["worker_erro"]', u"sem nada", False),
            (u"erro higienizado, Politica ainda avisando: reprova",
             u'"worker_erro": _higienizar(STATE["worker_erro"])',
             u"vai a mensagem do erro", False),
            (u"erro cru, Politica avisando: passa",
             u'"worker_erro": STATE["worker_erro"]',
             u"vai a mensagem do erro", True)):
        checar(u"  isca: %s" % rot, _status_dir_coerente(c, p)[0] is esperado)

    rr = ler("app/radai_records.py")
    checar(u"a exportacao do registro confere o caso.json (o que a Politica "
           u"diz)", u'os.path.join(pcasos, c, "caso.json")' in rr)
    checar(u"a Politica diz que antes de selar confere o caso.json",
           u"confere de novo o caso.json" in politica
           and u"deixa fora do pacote" in politica)
    checar(u"  e nao promete conferir cada caso inteiro de novo",
           u"confere cada caso de novo e recusa o que tiver identificador"
           not in politica)

    checar(u"o vigia imprime o erro de gravacao com a excecao (que cita o "
           u"arquivo)", u"sem permissao de escrita em %s (%s)" in vig)
    checar(u"  e a Politica diz que o caminho absoluto aparece nas mensagens "
           u"de erro", u"nas mensagens de erro" in politica)

    m = re.search(r"st_size > (\d+) \* 1024 \* 1024", vig)
    checar(u"o vigia faz o rodizio do log por tamanho",
           bool(m) and u"radai_vigia.anterior.log" in vig)
    if m:
        checar(u"  e a Politica o declara entre o que o programa apaga "
               u"(%s MB)" % m.group(1),
               u"radai_vigia.anterior.log" in politica
               and (u"%s MB" % m.group(1)) in politica)
    checar(u"o vigia apaga os marcadores de trabalho (lock e falha)",
           (u'"lock").unlink()' in vig
            or (u'".soltando.' in vig and u"soltando.unlink()" in vig))
           and u'"fail").unlink()' in vig)
    checar(u"  e a Politica os declara", u"marcadores de trabalho" in politica)
    _conv_nova = u"os.makedirs(pasta)" in _fonte_da_funcao(
        ler("app/radai_bridge_entrada.py"), "nova_conversao")
    checar(u"o DicomBridge converte sempre numa pasta de trabalho nova, e "
           u"nenhuma tela converte por cima de uma conversao anterior "
           u"(medido: %s)" % _conv_nova, _conv_nova)
    checar(u"  e a Politica nao declara mais o apagar dos cortes de uma "
           u"conversao anterior, nem o .zip vencido pelo link",
           u"apaga antes os cortes da conversão anterior" not in politica
           and u"o .zip sai quando o link" not in politica
           and u"não apaga nenhuma anterior" in politica)
    ok, det = _faxina_coerente(vig, politica)
    checar(u"a faxina do arranque do vigia: a Politica e o codigo concordam",
           ok, det)
    _sem_chamada = re.sub(r"(?m)^([ \t]+)limpar_temporarios\(\)", r"\1pass",
                          vig)
    checar(u"  (a isca do vigia real conseguiu tirar a chamada)",
           _sem_chamada != vig)
    _sem_frase = politica.replace(_FAXINA_DECLARA, u"no arranque")
    _sem_root = politica.replace(_FAXINA_SEM_ROOT, u"mesmo assim")
    for rot, v, p, esperado in (
            (u"o vigia chama, a Politica calada: reprova",
             vig, _sem_frase, False),
            (u"a Politica declara, o vigia nao chama: reprova",
             _sem_chamada, politica, False),
            (u"48 h no codigo, 24 na Politica: reprova",
             vig.replace(u"time.time() - 24 * 3600",
                         u"time.time() - 48 * 3600"), politica, False),
            (u"nem chamada nem frase: passa", _sem_chamada, _sem_frase, True),
            (u"a faxina nao depende do ROOT, e a Politica nao o diz: reprova",
             vig, _sem_root, False)):
        checar(u"  isca: %s" % rot, _faxina_coerente(v, p)[0] is esperado)
    for rot, v, esperado in (
            (u"o fantoma sem mutacao passa", _fantoma(), True),
            (u"`n = limpar_temporarios()` no worker_loop: passa",
             _fantoma(chama=u"    n = limpar_temporarios()"), True),
            (u"`if True: limpar_temporarios()`: passa",
             _fantoma(chama=u"    if True: limpar_temporarios()"), True),
            (u"a funcao passada como passo do arranque: passa",
             _fantoma(chama=u"    passos = [(\"faxina\", limpar_temporarios)]"
                            u"\n    for _nome, passo in passos:"
                            u"\n        passo()"), True),
            (u"apaga ARQUIVO tambem, mantendo is_dir(): reprova",
             _fantoma(apaga=u"        if p.stat().st_mtime < limite:\n"
                            u"            if p.is_dir():\n"
                            u"                shutil.rmtree(str(p))\n"
                            u"            else:\n"
                            u"                p.unlink()"), False),
            (u"apaga ARQUIVO com os.remove, mantendo is_dir(): reprova",
             _fantoma(apaga=u"        if p.is_dir():\n"
                            u"            shutil.rmtree(str(p))\n"
                            u"        elif p.stat().st_mtime < limite:\n"
                            u"            os.remove(str(p))"), False),
            (u"a chamada so numa funcao que ninguem chama: reprova",
             _fantoma(chama=u"    pass",
                      extra=u"\n\ndef _nunca():\n    limpar_temporarios()\n"),
             False),
            (u"o worker_loop chama, e ninguem sobe o worker_loop: reprova",
             _fantoma(sobe=u"    pass"), False),
            (u"a faxina so com o ROOT preenchido (`if ROOT:`): reprova",
             _fantoma(chama=u"    if ROOT:\n        limpar_temporarios()"),
             False),
            (u"`if not ROOT: return` antes da faxina: reprova",
             _fantoma(chama=u"    if not ROOT:\n        return\n"
                            u"    limpar_temporarios()"), False),
            (u"o main so sobe o laco com ROOT: reprova",
             _fantoma(sobe=u"    if ROOT:\n" + _FANT_SOBE.replace(
                 u"    ", u"        ", 1)), False)):
        checar(u"  isca: %s" % rot,
               _faxina_coerente(v, politica)[0] is esperado,
               _faxina_coerente(v, politica)[1])
    for velha in (u"com três exceções",
                  u"Marcadores, contornos, acervo, log e registro permanecem",
                  u"O programa não apaga dado de paciente por conta própria"):
        checar(u"a Politica nao diz %r" % velha[:40], velha not in politica)

    bloqueia = bool(re.search(r"""["']download_pretrained_weights["']""",
                              ler("app/radai_ts_runner.py")))
    frase_pt = u"tenta baixá-lo da origem dela"
    for nome, txt in ((u"Politica", politica),
                      (u"ponto `local`", pontos.get(u"local", u"")),
                      (u"README", u" ".join(ler("README.md").split()))):
        diz = (frase_pt in txt) or (u"tries to download it" in txt)
        checar(u"%s: declara o download de peso faltante se, e so se, o "
               u"envelope nao o bloqueia" % nome, diz is (not bloqueia),
               u"envelope bloqueia=%s, documento diz=%s" % (bloqueia, diz))

    checar(u"os Termos dizem que o pacote traz as tarefas de achado",
           u"traz as tarefas de achado" in termos)
    for velha in (u"sai de fábrica sem nenhuma tarefa de achado",
                  u"o catálogo de tarefas do programa"):
        checar(u"os Termos nao dizem %r" % velha[:40], velha not in termos)
    checar(u"  e os Creditos dizem o mesmo (vem no pacote, nao rodam)",
           u"Vêm no pacote e não rodam de fábrica" in _plano(
               __import__("radai_credits").pagina()))



def _fonte_da_funcao(src, nome):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return u""
    for no in ast.walk(arv):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and no.name == nome:
            return ast.get_source_segment(src, no) or u""
    return u""


def _prefixo_do_mkdtemp(src, nome):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return None
    funcs = [no for no in ast.walk(arv)
             if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
             and no.name == nome]
    if not funcs:
        return None
    for no in ast.walk(funcs[0]):
        if isinstance(no, ast.Call):
            f = no.func
            if (getattr(f, "attr", None) or getattr(f, "id", None)) == "mkdtemp":
                for kw in no.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                        return str(kw.value.value)
                return u""
    return None


_APAGA = re.compile(r"\b(rmtree|unlink|remove)\s*\(")

_FUNCOES_DE_APAGAR = ("rmtree", "unlink", "remove", "rmdir")
_MODULOS = frozenset(("os", "shutil", "_os", "_sh", "Path", "pathlib"))


def _nomes(no):
    return set(n.id for n in ast.walk(no) if isinstance(n, ast.Name)) \
        - _MODULOS


def _apagados(src):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return set()
    fora = set()
    for no in ast.walk(arv):
        if not isinstance(no, ast.Call):
            continue
        f = no.func
        nome = getattr(f, "attr", None) or getattr(f, "id", None)
        if nome not in _FUNCOES_DE_APAGAR:
            continue
        for a in list(no.args) + [k.value for k in no.keywords]:
            fora |= _nomes(a)
        if isinstance(f, ast.Attribute):
            fora |= _nomes(f.value)
    return fora


def _rodar_aninha_na_entrega(src_rodar, src_entrega):
    try:
        r = ast.parse(src_rodar or u"")
        e = ast.parse(src_entrega or u"")
    except SyntaxError:
        return False
    params = set()
    for no in ast.walk(r):
        if isinstance(no, ast.Call) and (getattr(no.func, "attr", None) or
                                         getattr(no.func, "id", None)) \
                == "mkdtemp":
            for kw in no.keywords:
                if kw.arg == "dir" and isinstance(kw.value, ast.Name):
                    params.add(kw.value.id)
    if not params:
        return False
    for no in ast.walk(e):
        if isinstance(no, ast.Call) and getattr(no.func, "attr", None) \
                == "rodar":
            for kw in no.keywords:
                if kw.arg in params and isinstance(kw.value, ast.Name) \
                        and kw.value.id == "trabalho":
                    return True
    return False


_COPIAS_DE_ARQUIVO = ("copy2", "copyfile", "copy", "move")


def _gravadores_do_rs(fontes):
    fora = []
    for qual, modulo in (("watcher", "radai_watcher"),
                         ("output", "radai_output"), ("batch", "radai_batch")):
        src = fontes.get(qual) or u""
        try:
            arv = ast.parse(src)
        except SyntaxError:
            return []

        def _andar(no, pref):
            for c in ast.iter_child_nodes(no):
                if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield pref + c.name, c
                    for x in _andar(c, pref + c.name + u"."):
                        yield x
                elif isinstance(c, ast.ClassDef):
                    for x in _andar(c, pref + c.name + u"."):
                        yield x
                else:
                    for x in _andar(c, pref):
                        yield x
        for nome, fn in _andar(arv, u""):
            params = set(a.arg for a in fn.args.args)
            copias = [c for c in ast.walk(fn) if isinstance(c, ast.Call)
                      and isinstance(c.func, ast.Attribute)
                      and c.func.attr in _COPIAS_DE_ARQUIVO
                      and isinstance(c.func.value, ast.Name)
                      and c.func.value.id in ("shutil", "_sh")]
            if not copias:
                continue
            origem = set()
            for c in copias:
                if c.args:
                    origem |= (_nomes(c.args[0]) & params)
            apagados = _apagados(ast.get_source_segment(src, fn) or u"")
            fora.append((modulo + u"." + nome,
                         bool(origem) and origem <= apagados))
    return sorted(fora)


_HIGIENIZADORES_DE_ERRO = ("erro_sem_caminho_nem_uid", "sem_caminho_nem_uid",
                           "sem_caminhos")


def _escritas_de_marcador(fontes, tipo):
    fora = []
    for qual, modulo in (("watcher", "radai_watcher"), ("batch", "radai_batch")):
        src = fontes.get(qual) or u""
        try:
            arv = ast.parse(src)
        except SyntaxError:
            continue
        pais = {}
        for no in ast.walk(arv):
            for filho in ast.iter_child_nodes(no):
                pais[filho] = no
        for no in ast.walk(arv):
            if not (isinstance(no, ast.Call)
                    and isinstance(no.func, ast.Attribute)
                    and no.func.attr == "write_text" and no.args):
                continue
            rec = no.func.value
            if not (isinstance(rec, ast.Call) and any(
                    isinstance(a, ast.Constant) and a.value == tipo
                    for a in rec.args)):
                continue
            arg = no.args[0]
            if not (isinstance(arg, ast.Call) and arg.args
                    and isinstance(arg.func, ast.Attribute)
                    and arg.func.attr == "dumps"):
                continue
            dono = pais.get(no)
            while dono is not None and not isinstance(
                    dono, (ast.FunctionDef, ast.AsyncFunctionDef)):
                dono = pais.get(dono)
            if dono is not None:
                fora.append((modulo + u"." + dono.name, dono, arg.args[0]))
    return sorted(fora, key=lambda x: x[0])


def _chaves_gravadas(dono, expr):
    chaves = {}

    def _do_dict(d):
        for k, v in zip(d.keys, d.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                chaves.setdefault(k.value, []).append(v)
    if isinstance(expr, ast.Dict):
        _do_dict(expr)
        return chaves
    if not isinstance(expr, ast.Name):
        return chaves
    nome = expr.id

    def _e_o_nome(x):
        return isinstance(x, ast.Name) and x.id == nome
    for no in ast.walk(dono):
        if isinstance(no, ast.Assign):
            for t in no.targets:
                if _e_o_nome(t):
                    if isinstance(no.value, ast.Dict):
                        _do_dict(no.value)
                    elif isinstance(no.value, ast.BoolOp):
                        for v in no.value.values:
                            if isinstance(v, ast.Dict):
                                _do_dict(v)
                elif (isinstance(t, ast.Subscript) and _e_o_nome(t.value)
                      and isinstance(t.slice, ast.Constant)
                      and isinstance(t.slice.value, str)):
                    chaves.setdefault(t.slice.value, []).append(no.value)
        elif (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
              and _e_o_nome(no.func.value) and no.args):
            if no.func.attr == "update" and isinstance(no.args[0], ast.Dict):
                _do_dict(no.args[0])
            elif (no.func.attr == "setdefault"
                  and isinstance(no.args[0], ast.Constant)
                  and isinstance(no.args[0].value, str)):
                chaves.setdefault(no.args[0].value, []).extend(no.args[1:2])
    return chaves


def _entradas_da_lista(dono, lista):
    fora = []
    for no in ast.walk(dono):
        if (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                and no.func.attr == "append" and no.args
                and isinstance(no.args[0], ast.Dict)
                and any(isinstance(c, ast.Constant) and c.value == lista
                        for c in ast.walk(no.func.value))):
            fora.append(no.args[0])
    return fora


def _entradas_pelo_chamador(src, dono, valores):
    posicionais = [a.arg for a in dono.args.args]
    params = set(posicionais + [a.arg for a in dono.args.kwonlyargs])
    usados = set(n.id for v in valores or () for n in ast.walk(v)
                 if isinstance(n, ast.Name) and n.id in params)
    if not usados:
        return []
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return []
    pais = {}
    for no in ast.walk(arv):
        for filho in ast.iter_child_nodes(no):
            pais[filho] = no
    fora = []
    for no in ast.walk(arv):
        if not (isinstance(no, ast.Call) and (
                (isinstance(no.func, ast.Name) and no.func.id == dono.name)
                or (isinstance(no.func, ast.Attribute)
                    and no.func.attr == dono.name))):
            continue
        chamador = pais.get(no)
        while chamador is not None and not isinstance(
                chamador, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chamador = pais.get(chamador)
        if chamador is None or chamador is dono:
            continue
        for param in sorted(usados):
            passado = None
            for kw in no.keywords:
                if kw.arg == param:
                    passado = kw.value
            if passado is None and param in posicionais:
                i = posicionais.index(param)
                if i < len(no.args):
                    passado = no.args[i]
            if passado is None:
                continue
            if not isinstance(passado, ast.Name):
                fora.append((chamador, []))
                continue
            fora.append((chamador, [
                c.args[0] for c in ast.walk(chamador)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr == "append" and c.args
                and isinstance(c.func.value, ast.Name)
                and c.func.value.id == passado.id
                and isinstance(c.args[0], ast.Dict)]))
    return fora


def _passa_por_higienizador(dono, valores):
    atrib = {}
    for no in ast.walk(dono):
        if isinstance(no, ast.Assign):
            for t in no.targets:
                if isinstance(t, ast.Name):
                    atrib.setdefault(t.id, []).append(no.value)
        elif (isinstance(no, (ast.AugAssign, ast.AnnAssign))
              and isinstance(no.target, ast.Name)
              and no.value is not None):
            atrib.setdefault(no.target.id, []).append(no.value)
    vistos, pilha = set(), list(valores)
    while pilha:
        v = pilha.pop()
        for n in ast.walk(v):
            if ((isinstance(n, ast.Name) and n.id in _HIGIENIZADORES_DE_ERRO)
                    or (isinstance(n, ast.Attribute)
                        and n.attr in _HIGIENIZADORES_DE_ERRO)):
                return True
            if (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                    and n.id not in vistos):
                vistos.add(n.id)
                pilha.extend(atrib.get(n.id, []))
    return False


def _fatos_dos_marcadores(fontes):
    conclusao = _escritas_de_marcador(fontes, "done")
    falha = _escritas_de_marcador(fontes, "fail")
    leva_pid = leva_uid = erro_task_cru = erro_falha_cru = False
    _fonte_do = {"radai_watcher": "watcher", "radai_batch": "batch"}
    for _q, dono, expr in conclusao:
        ch = _chaves_gravadas(dono, expr)
        leva_pid = leva_pid or ("pid" in ch)
        leva_uid = leva_uid or ("uid" in ch)
        if "tasks_falharam" in ch:
            entradas = _entradas_da_lista(dono, "tasks_falharam")
            onde = [(dono, entradas)] if entradas else _entradas_pelo_chamador(
                fontes.get(_fonte_do.get(_q.split(u".")[0])), dono,
                ch["tasks_falharam"])
            if not onde or any(not dicts for _c, dicts in onde):
                erro_task_cru = True
            else:
                for quem, dicts in onde:
                    vals = [v for d in dicts
                            for k, v in zip(d.keys, d.values)
                            if isinstance(k, ast.Constant)
                            and k.value == "erro"]
                    erro_task_cru = erro_task_cru or (
                        bool(vals) and not _passa_por_higienizador(quem,
                                                                   vals))
    for _q, dono, expr in falha:
        ch = _chaves_gravadas(dono, expr)
        if "last_error" in ch:
            erro_falha_cru = erro_falha_cru or not _passa_por_higienizador(
                dono, ch["last_error"])
    return {"conclusao_leva_pid": leva_pid,
            "conclusao_leva_uid": leva_uid,
            "conclusao_leva_erro_cru": erro_task_cru,
            "falha_leva_erro_cru": erro_falha_cru}


def _apaga_o_oar_no_finally(src_funcao, produtor="selecionar_do_full"):
    try:
        arv = ast.parse(src_funcao or u"")
    except SyntaxError:
        return False
    nomes_oar = set()
    for no in ast.walk(arv):
        if (isinstance(no, ast.Assign) and isinstance(no.value, ast.Call)
                and (getattr(no.value.func, "attr", None)
                     or getattr(no.value.func, "id", None))
                == produtor):
            for t in no.targets:
                alvo = (t.elts[0] if isinstance(t, (ast.Tuple, ast.List))
                        and t.elts else t)
                if isinstance(alvo, ast.Name):
                    nomes_oar.add(alvo.id)
    if not nomes_oar:
        return False
    tipos = (ast.Try,) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())
    for no in ast.walk(arv):
        if not isinstance(no, tipos):
            continue
        if not any(_referencias(s, "_gravar_arquivo") for s in no.body):
            continue
        for s in no.finalbody:
            for c in ast.walk(s):
                if (isinstance(c, ast.Call)
                        and (getattr(c.func, "id", None)
                             or getattr(c.func, "attr", None))
                        == "_apagar_temp_do_oar"
                        and c.args and isinstance(c.args[0], ast.Name)
                        and c.args[0].id in nomes_oar):
                    return True
    return False


def _fatos_da_pasta_de_trabalho(fontes):
    pref = _prefixo_do_mkdtemp(fontes["engine"], "build_rtstruct")
    gravadores = _gravadores_do_rs(fontes)
    apagam_todos = bool(gravadores) and all(ap for _q, ap in gravadores)
    limpa_arq = _fonte_da_funcao(fontes["archive"], "limpar_temporaria")
    limpa_vig = _fonte_da_funcao(fontes["watcher"], "limpar_temporarios")
    src_nv_rodar = _fonte_da_funcao(fontes["nv"], "rodar")
    src_entrega = _fonte_da_funcao(fontes["compare"], "rodar_para_entrega")
    nv_rodar = _apagados(src_nv_rodar)
    nv_entrega = _apagados(src_entrega)
    fatos = {
        "rs_fica": (pref is not None and not str(pref).startswith("radai_")
                    and not apagam_todos),
        "ts_fica": not str(_prefixo_do_mkdtemp(fontes["engine"], "run_ts_task")
                           or u"").startswith("radai_"),
        "portal_na_faxina": (u'"radai_portal_"' in fontes["batch"]
                             and u"gettempdir()" in fontes["batch"]
                             and u"portal" not in limpa_arq
                             and u"portal" not in limpa_vig),
        "nv_fica": ("trabalho" not in nv_rodar
                    and not (nv_entrega - {"trabalho"})
                    and not _rodar_aninha_na_entrega(src_nv_rodar,
                                                     src_entrega)),
        "moose_fica": "trab" not in _apagados(_fonte_da_funcao(
            fontes["moose"], "rodar")),
        "nv_no_acervo": u"pasta_nv(" in _fonte_da_funcao(
            fontes["compare"], "rodar_para_entrega"),
        "nv_compara_no_acervo": (
            _referencias_no_fonte(_fonte_da_funcao(
                fontes["compare"], "rodar_para_entrega"), "_enfileirar")
            and _referencias_no_fonte(_fonte_da_funcao(
                fontes["compare"], "_enfileirar"), "registrar_comparacao")),
        "oar_sai": (_apaga_o_oar_no_finally(_fonte_da_funcao(
                        fontes["output"], "full_e_oar"))
                    and bool(_apagados(_fonte_da_funcao(
                        fontes["output"], "_apagar_temp_do_oar")))
                    and _referencias_no_fonte(_fonte_da_funcao(
                        fontes["engine"], "selecionar_do_full"),
                        "PREFIXO_TEMP_DO_OAR")),
        "fast_sai": (_apaga_o_oar_no_finally(_fonte_da_funcao(
                         fontes["output"], "_oar_fast"), "build_rtstruct")
                     and bool(_apagados(_fonte_da_funcao(
                         fontes["output"], "_apagar_temp_do_oar")))
                     and _referencias_no_fonte(_fonte_da_funcao(
                         fontes["engine"], "build_rtstruct"),
                         "PREFIXO_TEMP_DO_OAR")),
        "faxinas_em_uso": all(
            _referencias_no_fonte(_fonte_da_funcao(fontes[q], f),
                                  "pasta_temporaria_em_uso")
            for q, f in (("archive", "limpar_temporaria"),
                         ("watcher", "limpar_temporarios"))),
        "limpador_apaga_temp": (
            bool(re.search(r'(?m)^_APAGAVEIS\s*=\s*\([^)]*"temp"',
                           fontes.get("cleaner") or u""))
            and _referencias_no_fonte(
                _fonte_da_funcao(fontes.get("cleaner") or u"", "liberar"),
                "_temp_antigo")
            and bool(_apagados(_fonte_da_funcao(
                fontes.get("cleaner") or u"", "liberar")))),
    }
    fatos.update(_fatos_dos_marcadores(fontes))
    fatos["serie_numa_pasta_propria"] = _serie_numa_pasta_propria(fontes)
    return fatos


_ABSORVIDOS_PELA_PASTA_DA_SERIE = ("rs_fica", "nv_fica", "moose_fica")


def _fecha_a_pasta_da_serie_no_finally(src):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    for fn in ast.walk(arv):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nomes = set()
        for n in ast.walk(fn):
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                    and (getattr(n.value.func, "attr", None)
                         or getattr(n.value.func, "id", None))
                    == "TemporariaDaSerie"):
                nomes |= set(t.id for t in n.targets
                             if isinstance(t, ast.Name))
        if not nomes:
            continue

        def _chama(no, metodo):
            return (isinstance(no, ast.Call)
                    and getattr(no.func, "attr", None) == metodo
                    and isinstance(no.func.value, ast.Name)
                    and no.func.value.id in nomes)
        abre = any(_chama(n, "abrir") for n in ast.walk(fn))
        fecha = any(_chama(c, "fechar")
                    for t in ast.walk(fn) if isinstance(t, ast.Try)
                    for st in t.finalbody for c in ast.walk(st))
        if abre and fecha:
            return True
    return False


def _serie_numa_pasta_propria(fontes):
    try:
        arv = ast.parse(fontes.get("archive") or u"")
    except SyntaxError:
        return False
    apaga = False
    for c in arv.body:
        if isinstance(c, ast.ClassDef) and c.name == "TemporariaDaSerie":
            for f in c.body:
                if isinstance(f, ast.FunctionDef) and f.name == "fechar":
                    apaga = any(isinstance(n, ast.Call)
                                and getattr(n.func, "attr", None) == "rmtree"
                                for n in ast.walk(f))
    return bool(apaga and all(
        _fecha_a_pasta_da_serie_no_finally(fontes.get(q) or u"")
        for q in ("watcher", "batch")))


def _sem_a_pasta_da_serie(fontes):
    f2 = dict(fontes)
    for q in ("watcher", "batch"):
        f2[q] = (fontes.get(q) or u"").replace(u"_tmp_serie.fechar()",
                                                u"pass")
    return f2


_MARCAS_DO_DESCARTE = {
    "serie_numa_pasta_propria": u"a pasta própria de cada série",
    "rs_fica": u"A cópia de cada RTSTRUCT montada ali (seção 3) fica",
    "ts_fica": u"o que sobra de uma tarefa do TotalSegmentator interrompida "
               u"no meio também",
    "portal_na_faxina": u"a extração de um exame que chegou em .zip e os "
                        u"RTSTRUCT gravados nela",
    "nv_fica": u"a saída do NV-Segment-CT fica na pasta de trabalho",
    "moose_fica": u"a saída do MOOSE fica na pasta de trabalho",
    "nv_no_acervo": u"as máscaras do NV-Segment-CT, uma por série, com o UID "
                    u"inteiro no nome do arquivo",
    "nv_compara_no_acervo": u"uma linha por estrutura comparada com o "
                            u"TotalSegmentator",
    "oar_sai": u"a do RadAI_STUDY, que sai logo depois de gravada",
    "fast_sai": u"a do RadAI_STUDY_Fast, que sai logo depois de gravada",
    "faxinas_em_uso": u"ninguém está usando",
    "limpador_apaga_temp": u"em Configurações (Diagnosticar e otimizar), só "
                           u"depois de você confirmar a lista",
    "conclusao_leva_pid": u"o de conclusão guarda o PatientID",
    "conclusao_leva_uid": (u"inteiro no nome dos marcadores e dentro do de "
                           u"conclusão",
                           u"a data do exame e o UID inteiro da série"),
    "conclusao_leva_erro_cru": u"quando uma tarefa falhou sem derrubar a "
                               u"série, o texto do erro dela, como a "
                               u"exceção o escreveu",
    "falha_leva_erro_cru": u"o de falha guarda o texto do último erro, "
                           u"como a exceção o escreveu, que pode citar o "
                           u"caminho da pasta da série",
}


def _referencias_no_fonte(src, nome):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    return bool(_referencias(arv, nome))


def _descarte_coerente(fatos, politica):
    fora = []
    fatos = dict(fatos)
    if fatos.get("serie_numa_pasta_propria"):
        for k in _ABSORVIDOS_PELA_PASTA_DA_SERIE:
            fatos[k] = False
    for fato, marca in sorted(_MARCAS_DO_DESCARTE.items()):
        marcas = (marca,) if isinstance(marca, str) else tuple(marca)
        presentes = [m in politica for m in marcas]
        diz = all(presentes)
        meio = any(presentes) and not diz
        if meio or diz != bool(fatos.get(fato)):
            fora.append(u"%s: o codigo %s, e a Politica %s «%s»" % (
                fato, u"o faz" if fatos.get(fato) else u"NAO o faz mais",
                u"diz so em parte" if meio else
                (u"diz" if diz else u"nao diz"), marcas[0][:50]))
    return fora


def _fontes_do_descarte():
    return {"engine": ler("app/engine.py"),
            "watcher": ler("app/radai_watcher.py"),
            "output": ler("app/radai_output.py"),
            "batch": ler("app/radai_batch.py"),
            "archive": ler("app/radai_archive.py"),
            "nv": ler("app/radai_nv_engine.py"),
            "moose": ler("app/radai_moose_engine.py"),
            "compare": ler("app/radai_compare.py"),
            "cleaner": ler("app/radai_cleaner.py")}


def teste_o_que_a_pasta_de_trabalho_guarda():
    secao(u"a pasta de trabalho: o que fica, o que sai, e a Politica")
    import radai_consent as CS
    politica = _plano(CS.POLITICA)
    fontes = _fontes_do_descarte()
    fatos = _fatos_da_pasta_de_trabalho(fontes)
    checar(u"li o gravador do RTSTRUCT (build_rtstruct usa mkdtemp)",
           _prefixo_do_mkdtemp(fontes["engine"], "build_rtstruct")
           is not None)
    for fato in sorted(_MARCAS_DO_DESCARTE):
        checar(u"  fato lido do codigo: %s = %s" % (fato, fatos[fato]), True)
    fora = _descarte_coerente(fatos, politica)
    checar(u"a Politica declara, fato a fato, o que o codigo faz com a pasta "
           u"de trabalho", not fora, u" | ".join(fora))
    for velha in (u"O programa apaga tudo isso sozinho",
                  u"o que o NV-Segment-CT e o MOOSE gravam",
                  u"e o que os modelos gravam a partir dela, sai quando a "
                  u"segmentação termina",
                  u"leva, por série, os oito últimos dígitos do UID e as "
                  u"métricas"):
        checar(u"a Politica nao diz %r" % velha[:40], velha not in politica)
    m = re.search(r"def limpar_temporaria\(caminho=None, idade_h=(\d+)[,)]",
                  fontes["archive"])
    checar(u"a faxina do «Rodar agora» e de %s h, e a Politica diz o mesmo"
           % (m.group(1) if m else u"?"),
           bool(m) and (u"há mais de %s horas" % m.group(1)) in politica)

    consertos = {
        "rs_fica": ("engine", u"rt_path = Path(tempfile.mkdtemp()) / \"RS.dcm\"",
                    u"rt_path = Path(tempfile.mkdtemp(prefix=\"radai_rs_\")) "
                    u"/ \"RS.dcm\""),
        "portal_na_faxina": ("archive", u'nome.startswith("radai_")',
                             u'nome.startswith("radai_") and not '
                             u'nome.startswith("radai_portal_")'),
        "moose_fica": ("moose", u"        shutil.copy2(os.path.join("
                       u"saida_dir, gerados[0]), destino_nii)",
                       u"        shutil.copy2(os.path.join(saida_dir, "
                       u"gerados[0]), destino_nii)\n        "
                       u"shutil.rmtree(trab)"),
        "nv_fica": ("compare", u"        nv = masks_do_nv(saida, forma, "
                    u"classes, log=log)\n",
                    u"        nv = masks_do_nv(saida, forma, classes, "
                    u"log=log)\n        shutil.rmtree(pasta_do_nv, "
                    u"ignore_errors=True)\n"),
        "nv_no_acervo": ("compare", u"radai_archive.pasta_nv(criar=True)",
                         u"radai_archive.raiz()"),
        "nv_compara_no_acervo": ("compare",
                                 u"resumo[\"comparadas\"] = _enfileirar(",
                                 u"resumo[\"comparadas\"] = (lambda *a, "
                                 u"**k: 0)("),
        "oar_sai": ("output", u"_apagar_temp_do_oar(rt_oar, engine)",
                    u"pass"),
        "fast_sai": ("output", u"_apagar_temp_do_oar(rt, engine)", u"pass"),
        "faxinas_em_uso": ("watcher",
                           u"em_uso = _arq_uso.pasta_temporaria_em_uso",
                           u"em_uso = (lambda _p, _h: (False, u\"\"))"),
        "falha_leva_erro_cru": ("watcher", u'"last_error": limpo[:500]',
                                u'"last_error": '
                                u'erro_sem_caminho_nem_uid(limpo)[:500]'),
        "conclusao_leva_erro_cru": (
            "*", u'"erro": _motivo_t[:300],',
            u'"erro": erro_sem_caminho_nem_uid(_motivo_t)[:300],'),
    }
    checar(u"a serie roda numa pasta propria, apagada no fim pelas duas "
           u"portas (medido: %s)" % fatos["serie_numa_pasta_propria"],
           fatos["serie_numa_pasta_propria"] is True)
    checar(u"  isca: o vigia sem fechar a pasta da serie: o fato cai",
           _serie_numa_pasta_propria(_sem_a_pasta_da_serie(fontes)) is False)
    for fato in _ABSORVIDOS_PELA_PASTA_DA_SERIE:
        fora = _descarte_coerente(_fatos_da_pasta_de_trabalho(
            _sem_a_pasta_da_serie(fontes)), politica)
        checar(u"  isca: sem a pasta propria da serie, %s volta a valer, e "
               u"a Politica calada reprova" % fato,
               any(x.startswith(fato + u":") for x in fora),
               u" | ".join(fora))
        fora = _descarte_coerente(fatos, politica + u" "
                                  + _MARCAS_DO_DESCARTE[fato])
        checar(u"  isca: com a pasta da serie, a Politica volta a dizer que "
               u"%s fica: reprova" % fato,
               any(x.startswith(fato + u":") for x in fora))
    checar(u"a pasta de trabalho do TotalSegmentator cai na faxina (ts_fica "
           u"= %s), e a Politica nao diz que ela fica" % fatos["ts_fica"],
           fatos["ts_fica"] is False
           and _MARCAS_DO_DESCARTE["ts_fica"] not in politica)
    f_ts = dict(fontes)
    f_ts["engine"] = fontes["engine"].replace(u'mkdtemp(prefix=\"radai_ts_\")',
                                              u'mkdtemp(prefix=\"ts_\")')
    fora = _descarte_coerente(_fatos_da_pasta_de_trabalho(f_ts), politica)
    checar(u"  isca: com o prefixo que a faxina nao conhece, ts_fica volta a "
           u"valer, e a Politica calada reprova",
           f_ts["engine"] != fontes["engine"]
           and any(x.startswith(u"ts_fica:") for x in fora),
           u" | ".join(fora))
    for fato, (qual, velho, novo) in sorted(consertos.items()):
        if fato in _ABSORVIDOS_PELA_PASTA_DA_SERIE:
            continue
        f2 = dict(fontes)
        quais = sorted(fontes) if qual == "*" else [qual]
        for q in quais:
            f2[q] = fontes[q].replace(velho, novo)
        checar(u"  (a isca de %s achou o trecho no codigo)" % fato,
               any(f2[q] != fontes[q] for q in quais))
        fora = _descarte_coerente(_fatos_da_pasta_de_trabalho(f2), politica)
        checar(u"  isca: o codigo conserta %s e a Politica nao muda: reprova"
               % fato, any(x.startswith(fato + u":") for x in fora),
               u" | ".join(fora))
        sem = politica.replace(_MARCAS_DO_DESCARTE[fato], u"")
        fora = _descarte_coerente(fatos, sem)
        checar(u"  isca: a Politica cala %s com o codigo igual: reprova"
               % fato, any(x.startswith(fato + u":") for x in fora))

    _erro_velho, _erro_novo = consertos["conclusao_leva_erro_cru"][1:]
    _fonte_min = (
        u"def _marcar_done(s, tasks_falharam=None):\n"
        u"    done = {\"pid\": 1, \"tasks_falharam\": "
        u"list(tasks_falharam or [])}\n"
        u"    marcador(\"done\").write_text(json.dumps(done))\n"
        u"def _uma_serie():\n"
        u"    _tf = []\n"
        u"    _tf.append({\"task\": t, " + _erro_velho + u" \"c\": 1})\n"
        u"    _marcar_done(s, tasks_falharam=_tf)\n")
    _fm = lambda src: _fatos_dos_marcadores({"batch": src})[
        "conclusao_leva_erro_cru"]
    checar(u"  isca: escritor por parametro, erro cru no chamador: o fato "
           u"e verdadeiro", _fm(_fonte_min) is True)
    checar(u"  isca: o mesmo, com o erro higienizado no chamador: o fato "
           u"vira", _fm(_fonte_min.replace(_erro_velho, _erro_novo)) is False)
    checar(u"  isca: o chamador passa a lista de um jeito que nao se segue: "
           u"na duvida, cru", _fm(_fonte_min.replace(
               _erro_velho, _erro_novo).replace(u"tasks_falharam=_tf",
                                                u"tasks_falharam=list(_tf)"))
           is True)

    def _depois(qual, trecho, *novas):
        for linha in fontes[qual].split(u"\n"):
            if trecho in linha:
                recuo = linha[:len(linha) - len(linha.lstrip())]
                return (linha + u"\n", linha + u"\n" + u"".join(
                    recuo + n + u"\n" for n in novas))
        return (u"\x00(trecho ausente) " + trecho, u"")
    _rs = _depois("watcher", u"shutil.copy2(str(origem), parcial)",
                  u"shutil.rmtree(Path(origem).parent, ignore_errors=True)")
    _out = _depois("output", u"os.replace(parcial, alvo)",
                   u"shutil.rmtree(os.path.dirname(rt_local), "
                   u"ignore_errors=True)")

    def _com(trocas):
        f2 = dict(fontes)
        for qual, (velho, novo) in trocas:
            checar(u"  (a isca achou o trecho em %s)" % qual,
                   velho in f2[qual])
            f2[qual] = f2[qual].replace(velho, novo, 1)
            try:
                ast.parse(f2[qual])
                compila = True
            except SyntaxError:
                compila = False
            checar(u"  (e o fonte da isca em %s continua compilando)" % qual,
                   compila)
        return _fatos_da_pasta_de_trabalho(f2)
    checar(u"os gravadores do RTSTRUCT sao dois, lidos do codigo: o do vigia e "
           u"o da Saida (a copia do lote saiu na v8.2)",
           [q for q, _a in _gravadores_do_rs(fontes)] == [
               u"radai_output.Saida._gravar_arquivo",
               u"radai_watcher._copiar_atomico"],
           str(_gravadores_do_rs(fontes)))
    checar(u"  isca: so o vigia apaga a origem — a copia da Saida fica, e "
           u"rs_fica continua",
           _com([("watcher", _rs)])["rs_fica"] is True)
    checar(u"  isca: os dois apagam a origem — rs_fica cai",
           _com([("watcher", _rs), ("output", _out)])["rs_fica"] is False)
    checar(u"  isca: um `os.remove(parcial)` num caminho de erro nao e "
           u"apagar a origem — rs_fica continua",
           _com([("watcher", _depois("watcher",
                                     u"shutil.copy2(str(origem), parcial)",
                                     u"os.remove(parcial)")),
                 ("output", _depois("output", u"os.replace(parcial, alvo)",
                                    u"os.remove(parcial)"))])["rs_fica"]
           is True)
    _volta = (u"import os\n",
              u"import os\n\n\ndef _copia_do_lote(rt_local, destino):\n"
              u"    shutil.copy2(rt_local, destino + '.tmp')\n"
              u"    os.replace(destino + '.tmp', destino)\n\n")
    checar(u"  isca: um gravador proprio de volta no lote, sem apagar a "
           u"origem — rs_fica continua",
           _com([("watcher", _rs), ("output", _out),
                 ("batch", _volta)])["rs_fica"] is True)
    checar(u"  isca: consertar so o MOOSE nao tira a frase do NV",
           _com([("moose", consertos["moose_fica"][1:])]) == dict(
               fatos, moose_fica=False))
    _morto = (u"    presentes = rotulos_da_saida(caminho)\n",
              u"    presentes = rotulos_da_saida(caminho)\n"
              u"    shutil.rmtree(os.path.dirname(caminho))\n")
    checar(u"  isca: apagar em `segmentar_varias` (sem chamador) nao conserta "
           u"a entrega — nv_fica continua",
           _com([("nv", _morto)])["nv_fica"] is True)
    _ninho_rodar = (u'    trabalho = tempfile.mkdtemp(prefix=\"radai_nv_\")\n',
                    u'    trabalho = tempfile.mkdtemp(prefix=\"radai_nv_\", '
                    u'dir=dentro_de)\n')
    _ninho_entrega = (u"        saida = vm.rodar(nifti, ident=ident, "
                      u"label_prompt=ids,\n",
                      u"        saida = vm.rodar(nifti, dentro_de=trabalho, "
                      u"ident=ident, label_prompt=ids,\n")
    checar(u"  isca: o `rodar` cria a pasta dentro da `trabalho` que a entrega "
           u"apaga — nv_fica cai",
           _com([("nv", _ninho_rodar),
                 ("compare", _ninho_entrega)])["nv_fica"] is False)
    checar(u"  isca: so o `rodar` aceita a pasta, e a entrega nao a passa — "
           u"nv_fica continua",
           _com([("nv", _ninho_rodar)])["nv_fica"] is True)

    _base = (u"def full_e_oar(self):\n"
             u"    rt_oar, nomes, fora = engine.selecionar_do_full(a, b, c)\n"
             u"    try:\n"
             u"        self._gravar_arquivo(rt_oar, alvo)\n"
             u"    finally:\n"
             u"        %s\n")
    checar(u"oar_sai lido do ast: a chamada no finally do try que grava o OAR",
           _apaga_o_oar_no_finally(
               _base % u"_apagar_temp_do_oar(rt_oar, engine)") is True)
    checar(u"  isca: a chamada so num comentario do finally: o fato cai",
           _apaga_o_oar_no_finally(
               _base % u"pass  # _apagar_temp_do_oar(rt_oar, engine)")
           is False)
    checar(u"  isca: o finally apaga OUTRO caminho (o do FULL): o fato cai",
           _apaga_o_oar_no_finally(
               _base % u"_apagar_temp_do_oar(rt_full, engine)") is False)
    checar(u"  isca: a chamada DEPOIS do try, fora do finally: o fato cai",
           _apaga_o_oar_no_finally(
               (_base % u"pass") + u"    _apagar_temp_do_oar(rt_oar, engine)\n")
           is False)
    checar(u"  isca: o finally de um try que NAO grava: o fato cai",
           _apaga_o_oar_no_finally((_base % u"_apagar_temp_do_oar(rt_oar, "
                                    u"engine)").replace(
               u"self._gravar_arquivo(rt_oar, alvo)", u"x = 1")) is False)
    _f_oar = dict(fontes)
    _f_oar["output"] = fontes["output"].replace(
        u"_apagar_temp_do_oar(rt_oar, engine)",
        u"pass  # _apagar_temp_do_oar(rt_oar, engine)")
    try:
        ast.parse(_f_oar["output"])
        _compila = True
    except SyntaxError:
        _compila = False
    checar(u"  (a isca do OAR achou as chamadas e o fonte continua compilando)",
           _f_oar["output"] != fontes["output"] and _compila)
    _oar_comentado = _fatos_da_pasta_de_trabalho(_f_oar)
    checar(u"  isca: no codigo de verdade, a chamada vira comentario: oar_sai "
           u"cai", _oar_comentado["oar_sai"] is False)
    fora = _descarte_coerente(_oar_comentado, politica)
    checar(u"  isca: e a Politica de hoje, que diz que a copia do OAR sai, "
           u"reprova", any(x.startswith(u"oar_sai:") for x in fora),
           u" | ".join(fora))
    _sem_prefixo = _com([("engine", (
        u"tempfile.mkdtemp(prefix=PREFIXO_TEMP_DO_OAR)",
        u"tempfile.mkdtemp()"))])
    checar(u"  isca: o motor monta o OAR sem o prefixo (o nome so fica nos "
           u"comentarios): oar_sai cai", _sem_prefixo["oar_sai"] is False)

    esc_c = [q for q, _d, _e in _escritas_de_marcador(fontes, "done")]
    esc_f = [q for q, _d, _e in _escritas_de_marcador(fontes, "fail")]
    checar(u"li quem escreve o marcador de conclusao: os dois do vigia (a "
           u"serie e a readocao) e o do «Rodar agora»",
           esc_c == [u"radai_batch._marcar_done",
                     u"radai_watcher.process_series",
                     u"radai_watcher.readotar_entrega"], str(esc_c))
    checar(u"li quem escreve o marcador de falha: a serie do vigia, a "
           u"recusa da serie nao contornavel e a espera pela assinatura",
           esc_f == [u"radai_watcher._por_em_espera",
                     u"radai_watcher._recusar_serie",
                     u"radai_watcher.process_series"], str(esc_f))
    _pid_rd = ("watcher", (u'"date": s.get("date", ""), "pid": s.get("pid", ""),',
                          u'"date": s.get("date", ""),'))
    _pid_ps = ("watcher", (u'"date": s["date"], "pid": s.get("pid", ""),',
                          u'"date": s["date"],'))
    _pid_lt = ("batch", (u'"date": s.get("date", ""), "pid": s.get("pid", ""),',
                        u'"date": s.get("date", ""),'))
    checar(u"  isca: o PatientID sai so do `done` da serie do vigia — a "
           u"readocao e o «Rodar agora» ainda o gravam, e o fato continua",
           _com([_pid_ps])["conclusao_leva_pid"] is True)
    _sem_pid = _com([_pid_rd, _pid_ps, _pid_lt])
    checar(u"  isca: o PatientID sai dos tres — o fato cai",
           _sem_pid["conclusao_leva_pid"] is False)
    fora = _descarte_coerente(_sem_pid, politica)
    checar(u"  isca: o codigo tira o PatientID e a Politica nao muda: reprova",
           any(x.startswith(u"conclusao_leva_pid:") for x in fora),
           u" | ".join(fora))
    fora = _descarte_coerente(fatos, politica.replace(
        _MARCAS_DO_DESCARTE["conclusao_leva_pid"], u""))
    checar(u"  isca: a Politica cala o PatientID com o codigo igual: reprova",
           any(x.startswith(u"conclusao_leva_pid:") for x in fora))
    _sem_uid = _com([("watcher", (u'done = {"uid": uid, ', u'done = {')),
                     ("watcher", (u'done = {"uid": uid, ', u'done = {')),
                     ("batch", (u'done = {"uid": s["uid"], ', u'done = {'))])
    fora = _descarte_coerente(_sem_uid, politica)
    checar(u"  isca: o codigo tira o UID dos tres e a Politica nao muda: "
           u"reprova", _sem_uid["conclusao_leva_uid"] is False
           and any(x.startswith(u"conclusao_leva_uid:") for x in fora),
           u" | ".join(fora))
    for i, m in enumerate(_MARCAS_DO_DESCARTE["conclusao_leva_uid"]):
        fora = _descarte_coerente(fatos, politica.replace(m, u""))
        checar(u"  isca: a Politica tira o UID do de conclusao so da secao "
               u"%d: reprova" % (2 + i),
               any(x.startswith(u"conclusao_leva_uid:") for x in fora))
    checar(u"  isca: higienizar ANTES (`limpo = erro_sem_caminho_nem_uid("
           u"limpar_erro(e))`) tambem conserta — o fato cai",
           _com([("watcher", (u"        limpo = limpar_erro(e)",
                              u"        limpo = erro_sem_caminho_nem_uid("
                              u"limpar_erro(e))"))])["falha_leva_erro_cru"]
           is False)
    checar(u"  isca: o higienizador aplicado a OUTRO nome, que nao chega ao "
           u"`last_error`, nao conserta — o fato continua",
           _com([("watcher", _depois("watcher", u"        limpo = limpar_erro(e)",
                                     u"_so_para_a_tela = "
                                     u"erro_sem_caminho_nem_uid(limpo)"))])
           ["falha_leva_erro_cru"] is True)
    checar(u"  isca: o higienizador so num comentario ao lado do valor nao "
           u"conserta — o fato continua",
           _com([("watcher", (u'"last_error": limpo[:500],',
                              u'"last_error": limpo[:500],  '
                              u'# erro_sem_caminho_nem_uid'))])
           ["falha_leva_erro_cru"] is True)


def _rota_ou_link_do_onboarding(fontes):
    achados = []
    for nome, src in sorted(fontes.items()):
        if u"/onboarding" in _rotas_servidas(src):
            achados.append(u"%s serve /onboarding" % nome)
        if re.search(r"""href\s*=\s*\\?["']/onboarding\b""", src or u""):
            achados.append(u"%s linka /onboarding" % nome)
    return achados


def teste_o_onboarding_saiu_e_so_o_aceite_grava():
    secao(u"a tela de primeiros passos saiu, e so o aceite grava o aceite")
    import radai_consent as CS
    fontes = dict((n, ler(u"app/" + n)) for n in _componentes.nomes("app")
                  if n.endswith(u".py"))
    checar(u"li o app das sete pastas (%d modulos)" % len(fontes),
           len(fontes) > 60 and u"radai_consent.py" in fontes)
    achados = _rota_ou_link_do_onboarding(fontes)
    checar(u"nenhum modulo serve nem linka /onboarding, e a pagina saiu do "
           u"radai_consent", not achados and not hasattr(CS, "ONBOARDING"),
           u" | ".join(achados))
    checar(u"  isca: a rota de volta: reprova",
           bool(_rota_ou_link_do_onboarding({u"x.py": u'@app.get("/onboarding",'
                                             u' response_class=H)'})))
    checar(u"  isca: um link de volta numa tela (com e sem a contrabarra do "
           u"literal): reprova",
           bool(_rota_ou_link_do_onboarding({u"x.py": u'P = "<a href=\\"/'
                                             u'onboarding\\">x</a>"'}))
           and bool(_rota_ou_link_do_onboarding({u"y.py": u"P = '<a href=\"/"
                                                 u"onboarding\">x</a>'"})))
    checar(u"  e o link e a rota de outra tela nao reprovam",
           not _rota_ou_link_do_onboarding({u"z.py": u"P = '<a href=\"/termos\">'"
                                            u"\n@app.get(\"/aceite\")"}))
    checar(u"`/onboarding` nao esta entre as rotas que passam sem aceite",
           u"/onboarding" not in CS.LIVRES, str(CS.LIVRES))
    posts = []
    for nome, src in sorted(fontes.items()):
        n = len(re.findall(r"fetch\(\s*'/api/aceite'\s*,\s*\{\s*method\s*:"
                           r"\s*'POST'", src))
        if n:
            posts.append((nome, n))
    checar(u"so a tela do aceite faz POST em /api/aceite",
           posts == [(u"radai_consent.py", 1)]
           and u"fetch('/api/aceite', {method:'POST'" in CS.PAGINA_ACEITE,
           str(posts))


def _portao_recusa_notice_mudado(chave=None):
    import radai_consent as CS
    import radai_credits as CR
    from pathlib import Path
    tmp = tempfile.mkdtemp(prefix="radai_aceite_")
    notice = os.path.join(tmp, "NOTICE")
    io.open(notice, "w", encoding="utf-8").write(CR.ler_notice())
    antes = os.environ.get("RADAI_CALIB_DIR")
    _cam, _chave, _txt = CR.caminho_notice, CS._chave_da_impressao, \
        CS.texto_canonico
    contas = [0]

    def _contada():
        contas[0] += 1
        return _txt()
    try:
        os.environ["RADAI_CALIB_DIR"] = tmp
        CR.caminho_notice = lambda: Path(notice)
        CS.texto_canonico = _contada
        if chave is not None:
            CS._chave_da_impressao = chave
        CS._IMPRESSAO["par"] = None
        CS.registrar_aceite(u"bateria", [k for k, _t, _d in CS.PONTOS])
        if not CS.aceito():
            return None, 0
        n = contas[0]
        with io.open(notice, "a", encoding="utf-8") as f:
            f.write(u"\nlinha nova do NOTICE\n")
        return (not CS.aceito()), contas[0] - n
    finally:
        CR.caminho_notice, CS._chave_da_impressao, CS.texto_canonico = \
            _cam, _chave, _txt
        CS._IMPRESSAO["par"] = None
        if antes is None:
            os.environ.pop("RADAI_CALIB_DIR", None)
        else:
            os.environ["RADAI_CALIB_DIR"] = antes


def teste_a_impressao_e_calculada_uma_vez():
    secao(u"a impressao e guardada, e o portao continua recusando texto mudado")
    import radai_consent as CS
    _txt = CS.texto_canonico
    contas = [0]

    def _contada():
        contas[0] += 1
        return _txt()
    antes = os.environ.get("RADAI_CALIB_DIR")
    tmp = tempfile.mkdtemp(prefix="radai_aceite_")
    try:
        os.environ["RADAI_CALIB_DIR"] = tmp
        CS.texto_canonico = _contada
        CS._IMPRESSAO["par"] = None
        a = CS.impressao_dos_documentos()
        b = CS.impressao_dos_documentos()
        checar(u"a primeira pergunta monta o texto uma vez", contas[0] == 1,
               str(contas[0]))
        checar(u"a segunda devolve a guardada, sem montar de novo",
               a == b and contas[0] == 1, str(contas[0]))
        CS.registrar_aceite(u"bateria", [k for k, _t, _d in CS.PONTOS])
        n = contas[0]
        em_dia = all(CS.aceito() for _ in range(20))
        checar(u"vinte telas com aceite em dia: nenhuma monta o texto",
               em_dia and contas[0] == n, u"%s montagens" % (contas[0] - n))
        _t = CS.TERMOS
        try:
            CS.TERMOS = _t.replace(u"Uso responsável", u"Uso responsável e "
                                   u"atento")
            checar(u"TERMOS mudados em memoria: o portao recusa",
                   not CS.aceito())
        finally:
            CS.TERMOS = _t
        checar(u"  e com o texto de volta, aceita", CS.aceito())
        _p = CS.PONTOS
        try:
            CS.PONTOS = [(c, t, d + u" x") if c == u"local" else (c, t, d)
                         for (c, t, d) in _p]
            checar(u"um ponto mudado: o portao recusa", not CS.aceito())
        finally:
            CS.PONTOS = _p
    finally:
        CS.texto_canonico = _txt
        CS._IMPRESSAO["par"] = None
        if antes is None:
            os.environ.pop("RADAI_CALIB_DIR", None)
        else:
            os.environ["RADAI_CALIB_DIR"] = antes

    recusou, montou = _portao_recusa_notice_mudado()
    checar(u"o NOTICE mudou no disco: o portao recusa", recusou is True,
           repr(recusou))
    checar(u"  e a impressao foi refeita uma vez so", montou == 1, str(montou))
    recusou, _m = _portao_recusa_notice_mudado(chave=lambda: u"sempre igual")
    checar(u"  isca: com a chave que nao ve o disco, o portao NAO recusaria",
           recusou is False, repr(recusou))
    checar(u"o portao calcula a impressao ao ser montado (fora do laco de "
           u"eventos)",
           u"impressao_dos_documentos()" in _fonte_da_funcao(
               ler("app/radai_consent.py"), "montar_portao").split(
               u"@app.middleware")[0])


def teste_a_guarda_de_rede_e_o_que_os_documentos_dizem():
    secao(u"a guarda de rede e o que os documentos dizem dela")
    import radai_consent as CS
    politica = _plano(CS.POLITICA)
    pontos = dict((c, t + u" " + d) for (c, t, d) in CS.PONTOS)
    readme = u" ".join(ler("README.md").split())
    guarda = _corpo_da_funcao(ler("tools/check_project.py"),
                              u"checar_consulta_de_versao_nao_leva_nada")
    checar(u"li a guarda de rede do check_project", bool(guarda))

    def coerente(guarda, politica, readme):
        fora = []
        lista = u"PERMITIDOS = {" in guarda
        if lista != (u"fora de uma lista curta de módulos autorizados"
                     in politica):
            fora.append(u"a lista de modulos autorizados")
        ve_sub = u"subprocess" in guarda
        cego = (u"e não o que faz um programa de terceiro que ele executa"
                in politica)
        if cego == ve_sub:
            fora.append(u"o limite: a guarda %s subprocesso e a Politica %s "
                        u"diz que nao ve" % (u"ve" if ve_sub else u"nao ve",
                                            u"" if cego else u"nao"))
        if lista != (u"outside a short list of authorised modules" in readme):
            fora.append(u"o README")
        return fora
    fora = coerente(guarda, politica, readme)
    checar(u"a Politica e o README dizem o que a guarda mede", not fora,
           u" | ".join(fora))
    checar(u"  isca: a guarda passa a ver subprocesso e a Politica nao muda: "
           u"reprova", bool(coerente(guarda + u"\nsubprocess\n", politica,
                                     readme)))
    checar(u"  isca: a Politica volta a nao dizer a lista: reprova",
           bool(coerente(guarda, politica.replace(
               u"fora de uma lista curta de módulos autorizados", u""),
               readme)))
    for nome, txt, velha in (
            (u"Politica", politica, u"reprova qualquer módulo que abra "
                                    u"conexão para fora sem estar declarado"),
            (u"ponto `local`", pontos.get(u"local", u""),
             u"há teste automatizado que quebra se alguém acrescentar uma"),
            (u"README", readme, u"a test fails if any module opens an "
                                u"undeclared outbound connection")):
        checar(u"%s: nao promete mais do que a guarda mede" % nome,
               velha not in txt)
    checar(u"o ponto `local` diz o que a guarda faz",
           u"reprova chamada de rede escrita fora dos poucos módulos "
           u"autorizados" in pontos.get(u"local", u""))


_CLI_DA_BIBLIOTECA = u"totalsegmentator.bin.totalseg_download_weights"
_EXE_DA_BIBLIOTECA = (u"totalseg_download_weights",
                      u"totalseg_download_weights.exe")
_FUNCAO_DA_BIBLIOTECA = u"download_pretrained_weights"
_MOLDE = re.compile(r"%[-#0 +]*\d*(?:\.\d+)?[sdrif]")


class _Fonte(object):

    def __init__(self, arv):
        self.pais = {}
        for p in ast.walk(arv):
            for f in ast.iter_child_nodes(p):
                self.pais[id(f)] = p
        self.atrib = {}
        for no in ast.walk(arv):
            if isinstance(no, ast.Assign):
                alvos, tipo, valor = no.targets, u"=", no.value
            elif isinstance(no, ast.AnnAssign) and no.value is not None:
                alvos, tipo, valor = [no.target], u"=", no.value
            elif isinstance(no, ast.AugAssign) and isinstance(no.op, ast.Add):
                alvos, tipo, valor = [no.target], u"+=", no.value
            else:
                continue
            chave = self._chave(self.escopo(no))
            for a in alvos:
                if isinstance(a, ast.Name):
                    self.atrib.setdefault((chave, a.id), []).append(
                        ((no.lineno, no.col_offset), tipo, valor))

    @staticmethod
    def _chave(esc):
        return None if esc is None else id(esc)

    def escopo(self, no):
        p = self.pais.get(id(no))
        while p is not None:
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.Lambda)):
                return p
            p = self.pais.get(id(p))
        return None

    @staticmethod
    def _parametros(func):
        a = func.args
        nomes = [x.arg for x in (list(getattr(a, "posonlyargs", []))
                                 + list(a.args) + list(a.kwonlyargs))]
        nomes += [x.arg for x in (a.vararg, a.kwarg) if x is not None]
        return set(nomes)

    def textos_do_nome(self, nome, prof):
        esc = self.escopo(nome)
        while True:
            lista = self.atrib.get((self._chave(esc), nome.id))
            if lista:
                break
            if esc is None:
                return []
            if (not isinstance(esc, ast.Lambda)
                    and nome.id in self._parametros(esc)):
                return []
            esc = self.escopo(esc)
        fora, acum = [], None
        for _pos, tipo, valor in sorted(lista, key=lambda x: x[0]):
            cands = self.textos(valor, prof + 1)
            fora.extend(cands)
            primeiro = cands[0] if cands else None
            if tipo == u"=" or acum is None:
                acum = primeiro
            elif primeiro is not None:
                acum = acum + primeiro
            if acum is not None:
                fora.append(acum)
        vistos, unicos = set(), []
        for t in fora:
            if t not in vistos:
                vistos.add(t)
                unicos.append(t)
        return unicos

    def textos(self, no, prof=0):
        if no is None or prof > 8:
            return []
        if isinstance(no, ast.Constant):
            return [no.value] if isinstance(no.value, str) else []
        if isinstance(no, ast.JoinedStr):
            return [u"".join(v.value if isinstance(v, ast.Constant) else u"0"
                             for v in no.values)]
        if isinstance(no, ast.BinOp):
            if isinstance(no.op, ast.Mod):
                return self.textos(no.left, prof + 1)
            if isinstance(no.op, ast.Add):
                e = self.textos(no.left, prof + 1)
                d = self.textos(no.right, prof + 1)
                if not e and not d:
                    return []
                return [a + b for a in (e or [u"0"])
                        for b in (d or [u"0"])][:16]
            return []
        if isinstance(no, ast.Name):
            return self.textos_do_nome(no, prof + 1)
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
            if no.func.attr == u"join" and len(no.args) == 1:
                seps = self.textos(no.func.value, prof + 1)
                arg = no.args[0]
                if not seps:
                    return []
                if isinstance(arg, (ast.List, ast.Tuple)):
                    return [seps[0].join((self.textos(x, prof + 1)
                                          or [u"0"])[0] for x in arg.elts)]
                if isinstance(arg, (ast.GeneratorExp, ast.ListComp,
                                    ast.SetComp)):
                    return self.textos(arg.elt, prof + 1)
                return []
            if no.func.attr == u"format":
                return [re.sub(r"\{[^{}]*\}", u"0", t)
                        for t in self.textos(no.func.value, prof + 1)]
        return []


def _roteiro_chama(texto, prof, solto):
    codigo = _MOLDE.sub(u"0", texto)
    try:
        sub = ast.parse(codigo)
    except (SyntaxError, ValueError):
        return (not solto) and bool(re.search(
            r"\b%s\s*\(" % _FUNCAO_DA_BIBLIOTECA, codigo))
    return _examina(sub, prof + 1)


def _examina(arv, prof=0):
    if prof > 2:
        return False
    fonte = _Fonte(arv)
    soltas = set(id(n.value) for n in ast.walk(arv)
                 if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
    for n in ast.walk(arv):
        if isinstance(n, ast.Call) and (getattr(n.func, "attr", None)
                                        or getattr(n.func, "id", None)) \
                == _FUNCAO_DA_BIBLIOTECA:
            return True
        if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                and id(n) not in soltas):
            v = n.value.strip()
            if re.split(r"[\\/]", v)[-1].lower() in _EXE_DA_BIBLIOTECA:
                return True
            cru = n.value
            if ((_FUNCAO_DA_BIBLIOTECA in cru or u"totalseg_download_weights"
                 in cru) and _roteiro_chama(cru, prof, solto=True)):
                return True
        if isinstance(n, (ast.List, ast.Tuple)):
            elts = n.elts
            for i, e in enumerate(elts[:-1]):
                if not (isinstance(e, ast.Constant)
                        and e.value in (u"-m", u"-c")):
                    continue
                for t in fonte.textos(elts[i + 1]):
                    if e.value == u"-m":
                        if t.strip() == _CLI_DA_BIBLIOTECA:
                            return True
                    elif _roteiro_chama(t, prof, solto=False):
                        return True
    return False


def _roteiros_sem_leitura(src):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return [0]
    fonte, fora = _Fonte(arv), []
    for n in ast.walk(arv):
        if not isinstance(n, (ast.List, ast.Tuple)):
            continue
        for i, e in enumerate(n.elts[:-1]):
            if not (isinstance(e, ast.Constant) and e.value == u"-c"):
                continue
            lidos = 0
            for t in fonte.textos(n.elts[i + 1]):
                try:
                    ast.parse(_MOLDE.sub(u"0", t))
                    lidos += 1
                except (SyntaxError, ValueError):
                    pass
            if not lidos:
                fora.append(n.elts[i + 1].lineno)
    return sorted(fora)


def _usa_o_baixador_da_biblioteca(src):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    return _examina(arv)


def _baixador_coerente(usa, readme):
    fora = []
    nega = u"not by the library's own downloader" in readme
    if usa:
        if nega:
            fora.append(u"o README diz que o baixador da biblioteca nao e' "
                        u"usado, e o preparador o chama")
        if u"checks no hash" not in readme:
            fora.append(u"o preparador chama o baixador da biblioteca e o "
                        u"README nao diz que ele nao confere hash")
    elif not nega:
        fora.append(u"o preparador baixa os pesos ele mesmo e o README nao "
                    u"diz que nao e' pelo baixador da biblioteca")
    return fora


_ISCAS_QUE_CHAMAM = (
    (u"o roteiro do `-c` numa CONSTANTE DE MÓDULO (a forma do "
     u"`_SCRIPT_TABELA`)", r'''

_SCRIPT_BAIXA = (
    "import sys\n"
    "from totalsegmentator.libs import download_pretrained_weights\n"
    "download_pretrained_weights(int(sys.argv[1]))\n"
)


def _isca(py, n):
    rodar([py, "-c", _SCRIPT_BAIXA, str(n)])
'''),
    (u"o roteiro do `-c` numa VARIAVEL LOCAL (a forma do `script` e do "
     u"`conviver`)", r'''

def _isca(py, n):
    script = ("from totalsegmentator.libs import download_pretrained_weights; "
              "download_pretrained_weights(%d)" % n)
    rodar([py, "-c", script])
'''),
    (u"COMPOSTA: constante de modulo feita de outras duas, que sozinhas nao "
     u"compilam", r'''

_BAIXA_CABECA = ("import sys\n"
                 "from totalsegmentator.libs import download_pretrained_weights\n"
                 "for n in map(int, sys.argv[1:]):\n")
_BAIXA_CORPO = "    download_pretrained_weights(n)\n"
_SCRIPT_BAIXA = _BAIXA_CABECA + _BAIXA_CORPO


def _isca(py, ns):
    rodar([py, "-c", _SCRIPT_BAIXA] + [str(n) for n in ns])
'''),
    (u"COMPOSTA: variavel local montada por `+=` (a forma da etapa 6)", r'''

def _isca(py, ns):
    script = "import sys\nfrom totalsegmentator.libs import download_pretrained_weights\n"
    script += "for n in map(int, sys.argv[1:]):\n"
    script += "    download_pretrained_weights(n)\n"
    rodar([py, "-c", script] + [str(n) for n in ns])
'''),
    (u"o `-m` com o CLI numa constante de modulo", r'''

_CLI_TS = "totalsegmentator.bin.totalseg_download_weights"


def _isca(py, t):
    rodar([py, "-m", _CLI_TS, "-t", t])
'''),
    (u"o EXECUTAVEL do CLI", r'''

def _isca(py, t):
    rodar([str(Path(py).parent / "Scripts" / "totalseg_download_weights.exe"),
           "-t", t])
'''),
    (u"o roteiro gravado num `.py` e rodado (sem `-c`)", r'''

_BAIXA_PY = ("from totalsegmentator.libs import download_pretrained_weights\n"
             "download_pretrained_weights(291)\n")


def _isca(py, pasta):
    alvo = os.path.join(pasta, "baixa.py")
    with open(alvo, "w") as f:
        f.write(_BAIXA_PY)
    rodar([py, alvo])
'''),
)

_ISCA_ESCOPO = r'''

def _isca_a(py):
    script = "from totalsegmentator.libs import download_pretrained_weights\n"
    script += "for n in (291,):\n"
    script += "    download_pretrained_weights(n)\n"
    return len(script)


def _isca_b(py):
    script = "print(1)"
    rodar([py, "-c", script])
'''
_ISCA_ESCOPO_CONTRAPROVA = _ISCA_ESCOPO.replace(
    u"    return len(script)\n", u"    rodar([py, \"-c\", script])\n")

_ISCA_SEM_LEITURA = r'''

def _isca(py, roteiro):
    rodar([py, "-c", roteiro])
'''
_ISCA_LIDO_SO_JUNTO = r'''

def _isca(py):
    script = "for i in range(2):\n"
    script += "    print(i)\n"
    rodar([py, "-c", script])
'''


def teste_o_readme_diz_o_que_o_preparador_confere():
    secao(u"o README diz o que o preparador confere, e contra o que")
    readme = u" ".join(ler("README.md").split())
    prep = ler("build/configurar_ambiente.py")
    checar(u"o README nao diz que todo peso e conferido por SHA-256",
           u"checks each SHA" not in readme)
    sem_leitura = _roteiros_sem_leitura(prep)
    checar(u"todo `-c` do preparador tem o roteiro LIDO (resolvido por nome "
           u"e compilado), e o `chama` abaixo e' medida e nao omissao",
           not sem_leitura,
           u"sem leitura na(s) linha(s) %s: estenda `_Fonte.textos` para a "
           u"forma nova, em vez de deixar o `-c` contar como «nao chama»"
           % sem_leitura)
    usa = _usa_o_baixador_da_biblioteca(prep)
    fora = _baixador_coerente(usa, readme)
    checar(u"o README diz de quem sao os pesos do TotalSegmentator se, e so "
           u"se, o preparador chama o baixador da biblioteca (medido por ast: "
           u"chama=%s)" % usa, not fora, u" | ".join(fora))
    for nome, trecho in _ISCAS_QUE_CHAMAM:
        try:
            ast.parse(prep + trecho)
            compila = True
        except SyntaxError:
            compila = False
        chama = compila and _usa_o_baixador_da_biblioteca(prep + trecho)
        checar(u"  isca: %s: e' chamada, e o README de hoje reprova" % nome,
               compila and chama and bool(_baixador_coerente(chama, readme)),
               u"" if compila else u"a isca nao compila")
    for nome, trecho, esperado in (
            (u"PRECISAO: o `script` que chama fica noutra funcao, fora de "
             u"`-c`: nao e' chamada", _ISCA_ESCOPO, False),
            (u"  e a contraprova: a mesma funcao manda o seu `script` para "
             u"um `-c`: e' chamada", _ISCA_ESCOPO_CONTRAPROVA, True)):
        try:
            ast.parse(prep + trecho)
            compila = True
        except SyntaxError:
            compila = False
        checar(u"  isca: %s" % nome,
               compila and _usa_o_baixador_da_biblioteca(prep + trecho)
               == esperado, u"" if compila else u"a isca nao compila")
    checar(u"  isca: um `-c` com o roteiro chegando por ARGUMENTO: a leitura "
           u"reprova, e diz a linha",
           len(_roteiros_sem_leitura(prep + _ISCA_SEM_LEITURA))
           == len(sem_leitura) + 1)
    checar(u"  isca: um roteiro que so' compila JUNTO (`=` e `+=`) e' lido",
           _roteiros_sem_leitura(prep + _ISCA_LIDO_SO_JUNTO) == sem_leitura)
    _cli = (u"\n\ndef _isca(py, t):\n"
            u"    rodar([py, \"-m\", "
            u"\"totalsegmentator.bin.totalseg_download_weights\", \"-t\", t])\n")
    _dash_c = (u"\n\ndef _isca(py, n):\n"
               u"    rodar([py, \"-c\", "
               u"\"from totalsegmentator.libs import "
               u"download_pretrained_weights; \"\n"
               u"               \"download_pretrained_weights(%d)\" % n])\n")
    checar(u"  isca: o preparador volta a chamar o CLI (`-m`): e' chamada",
           _usa_o_baixador_da_biblioteca(prep + _cli))
    checar(u"  isca: ou um `-c` que chama download_pretrained_weights: e' "
           u"chamada", _usa_o_baixador_da_biblioteca(prep + _dash_c))
    checar(u"  isca: um comentario que cita o CLI NAO e' chamada",
           not _usa_o_baixador_da_biblioteca(
               prep + u"\n# rodar totalseg_download_weights -t total\n"))
    checar(u"  isca: o CLI volta e o README nao muda: reprova",
           bool(_baixador_coerente(
               _usa_o_baixador_da_biblioteca(prep + _cli), readme)))
    checar(u"  isca: o README perde a frase de que o baixador da biblioteca "
           u"nao e' usado: reprova",
           bool(_baixador_coerente(usa, readme.replace(
               u"not by the library's own downloader", u""))))
    import subprocess
    try:
        v81 = subprocess.run(
            ["git", "show", "v8.1:build/configurar_ambiente.py"], cwd=RAIZ,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60)
        v81 = v81.stdout.decode("utf-8", "replace") if v81.returncode == 0 \
            else u""
    except Exception:
        v81 = u""
    if v81:
        checar(u"  e o preparador da v8.1 (tag), que chamava o CLI, e' lido "
               u"como chamada", _usa_o_baixador_da_biblioteca(v81))
    else:
        checar(u"  (sem git ou sem a tag v8.1: a medida no preparador de "
               u"antes foi pulada)", True)
    for chave in (u'chave="cache/python-embed.zip"', u'chave="cache/" + '
                  u'PIP_RODA'):
        checar(u"  e o runtime e o pip passam pela tabela (%s)" % chave[7:30],
               chave in prep)
    try:
        import radai_models as RM
        com_sha = sorted(k for k, m in RM.MODELOS.items() if m.get("sha256"))
        checar(u"os modelos com SHA-256 no registro sao os que o README "
               u"diz (%s)" % u", ".join(com_sha),
               com_sha == [u"cranio_buti", u"hnlnl", u"moose",
                           u"nv_segment_ct"]
               and (u"NV‑Segment‑CT, MOOSE, CT brain structures, head & neck "
                    u"nodal levels | SHA‑256 on download") in readme,
               str(com_sha))
    except Exception as e:
        checar(u"radai_models importa", False,
               u"%s: %s" % (type(e).__name__, str(e)[:80]))

    corpo = _fonte_da_funcao(prep, "_escrever_manifesto")
    checar(u"li o `_escrever_manifesto` do preparador", bool(corpo))

    import textwrap

    def manifesto_coerente(corpo, readme):
        try:
            arv = ast.parse(textwrap.dedent(corpo or u""))
        except SyntaxError:
            arv = ast.parse(u"")
        soma = False
        for laco in ast.walk(arv):
            if not isinstance(laco, ast.For) or u"ARTEFATOS" not in \
                    ast.dump(laco.iter):
                continue
            soma = soma or any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr == u"linha_manifesto"
                for c in ast.walk(laco))
        nomeia = any(isinstance(c, ast.Constant) and isinstance(c.value, str)
                     and u"NO PACOTE SEM CONFERENCIA" in c.value
                     for c in ast.walk(arv))
        fora = []
        if (u"sums the files on disk that `build/artefatos.py` lists"
                in readme) != soma:
            fora.append(u"o README %s que o manifesto soma o que a tabela "
                        u"lista, e o codigo %s" % (
                            u"nao diz" if soma else u"diz",
                            u"soma" if soma else u"nao soma"))
        if (u"names any weight folder that was already on disk"
                in readme) != nomeia:
            fora.append(u"o README %s que o manifesto nomeia o peso nao "
                        u"conferido, e o codigo %s" % (
                            u"nao diz" if nomeia else u"diz",
                            u"nomeia" if nomeia else u"nao nomeia"))
        if nomeia and u"the other weights do not appear in it" in readme:
            fora.append(u"o README diz que o resto nao aparece, e o manifesto "
                        u"o nomeia")
        return fora
    fora = manifesto_coerente(corpo, readme)
    checar(u"o README diz o que o manifesto soma (a tabela) e o que ele "
           u"nomeia (o peso nao conferido)", not fora, u" | ".join(fora))
    sem_nome = corpo.replace(u"NO PACOTE SEM CONFERENCIA", u"NO PACOTE")
    checar(u"  (a isca achou o bloco que nomeia)", sem_nome != corpo)
    checar(u"  isca: o manifesto deixa de nomear e o README nao muda: reprova",
           bool(manifesto_coerente(sem_nome, readme)))
    sem_soma = corpo.replace(u"artefatos.linha_manifesto(", u"str(")
    checar(u"  (a isca achou a soma da tabela)", sem_soma != corpo)
    checar(u"  isca: o manifesto deixa de somar e o README nao muda: reprova",
           bool(manifesto_coerente(sem_soma, readme)))
    checar(u"  isca: o README perde a frase da soma: reprova",
           bool(manifesto_coerente(corpo, readme.replace(
               u"sums the files on disk that", u"lists the files that"))))
    checar(u"  isca: o README volta a dizer que o resto nao aparece: reprova",
           bool(manifesto_coerente(corpo, readme + u" the other weights do "
                                   u"not appear in it")))
    checar(u"  isca: um comentario com o texto do bloco nao e' nomear",
           bool(manifesto_coerente(
               sem_nome + u"\n    # NO PACOTE SEM CONFERENCIA\n", readme)))

    usa_indice = u"download.pytorch.org" in prep

    def indice_coerente(prep, readme):
        return (u"from PyTorch's own index" in readme) is \
            (u"download.pytorch.org" in prep)
    checar(u"o README diz de onde vem o torch com CUDA se, e so se, o "
           u"preparador usa o indice do PyTorch",
           indice_coerente(prep, readme),
           u"preparador usa o indice=%s" % usa_indice)
    checar(u"  isca: o README volta a dizer so «from PyPI»: reprova",
           not indice_coerente(prep, readme.replace(
               u"from PyTorch's own index", u"from PyPI")))
    checar(u"  isca: o preparador deixa o indice do PyTorch e o README nao "
           u"muda: reprova",
           not indice_coerente(prep.replace(u"download.pytorch.org", u""),
                               readme))


def teste_o_aceite_diz_quando_o_texto_mudou():
    secao(u"a tela do aceite avisa quando o TEXTO mudou, com a versao igual")
    import radai_consent as CS
    imp = CS.impressao_dos_documentos()
    base = {"aceito": False, "versao": CS.VERSAO_DOCS, "data": CS.DATA_DOCS,
            "impressao": imp,
            "pontos": [{"chave": c, "titulo": t, "detalhe": d,
                        "sinal": CS.sinal_do_ponto(c)}
                       for (c, t, d) in CS.PONTOS],
            "fontes": CS.fontes_de_terceiros()}
    outro = dict(base, registro={"versao": CS.VERSAO_DOCS,
                                 "impressao": u"0" * 64,
                                 "quando": u"2026-09-23 10:00"})
    d, erro = _rodar_aceite_no_node(outro)
    if d is None:
        checar(u"o script da pagina executa no node", False, erro or u"")
        return
    checar(u"mesma versao, texto mudado: a tela diz que os documentos mudaram",
           u"Os documentos mudaram" in d["mudou"], d["mudou"][:80])
    igual = dict(base, registro={"versao": CS.VERSAO_DOCS, "impressao": imp,
                                 "quando": u"2026-09-23 10:00"})
    d, erro = _rodar_aceite_no_node(igual)
    checar(u"mesma versao e mesmo texto: a tela NAO diz que mudou",
           d is not None and not d["mudou"], (d or {}).get("mudou", erro))



_IMPRESSAO_DA_14 = (u"8c43155546aca32895fd4bf306267582a2cf6cd0ab2376f6939ddff6"
                    u"18b78108")
_IMPRESSAO_DA_15 = (u"73fece8185e4971da0902397c44d6e5a0c5510a6253439eab070ad71"
                    u"24f56489")



def _constante_do_modulo(src, nome):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return None
    valor = None
    for no in arv.body:
        alvos = []
        if isinstance(no, ast.Assign):
            alvos = no.targets
        elif isinstance(no, ast.AnnAssign) and no.value is not None:
            alvos = [no.target]
        if any(isinstance(t, ast.Name) and t.id == nome for t in alvos):
            try:
                valor = ast.literal_eval(no.value)
            except Exception:
                valor = None
    return valor


def _rota_da_funcao(src, nome):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return None
    for no in ast.walk(arv):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and no.name == nome:
            for d in no.decorator_list:
                if (isinstance(d, ast.Call) and d.args
                        and isinstance(d.args[0], ast.Constant)
                        and isinstance(d.args[0].value, str)):
                    return d.args[0].value
    return None


def _bolus_exporta(src_tela):
    corpo = _fonte_da_funcao(src_tela, "_stl")
    return (_rota_da_funcao(src_tela, "_stl") == u"/api/bolus/stl"
            and _referencias_no_fonte(corpo, "conferir_ato")
            and _referencias_no_fonte(corpo, "_gravar_ato"))


_MARCA_STL = u"O STL do 3D Printed Bolus"


def _bolus_coerente(src_tela, politica):
    return _bolus_exporta(src_tela) is (_MARCA_STL in politica)


def _arquivo_dos_atos(src_tela):
    v = _constante_do_modulo(src_tela, "ARQUIVO_ATOS")
    return v if isinstance(v, str) and v else None


def _nomeia_arquivo_dos_atos(arq, texto):
    return bool(arq) and arq in (texto or u"")


_FRAGMENTOS_DO_ALERTA = (u"Não é para uso clínico", u"filamento",
                         u"dosimetria do material é obrigatória")
_FRAGMENTO_DO_ATO = u"rascunho sujeito a revisão física e médica"


def _alerta_que_falta(alerta, frase_do_ato, termos):
    al = u" ".join((alerta or u"").split())
    ato = u" ".join((frase_do_ato or u"").split())
    fora = [f for f in _FRAGMENTOS_DO_ALERTA
            if not (f in al and f in (termos or u""))]
    if not (_FRAGMENTO_DO_ATO in ato and _FRAGMENTO_DO_ATO in (termos or u"")):
        fora.append(_FRAGMENTO_DO_ATO)
    return fora


_MARCA_SEM_RS_DE_BOLUS = u"Não há RTSTRUCT de bólus"


def _bolus_grava_rtstruct(*fontes):
    return any(_referencias_no_fonte(s, "build_rtstruct") for s in fontes)


def _sem_rtstruct_coerente(grava, termos):
    return (_MARCA_SEM_RS_DE_BOLUS in (termos or u"")) is (not grava)


_TAGS_DO_INDICE = (("SeriesDescription", u"da descrição da série"),
                   ("StudyInstanceUID", u"o UID da série e o do estudo"))


def _tags_da_varredura(src_vigia):
    v = _constante_do_modulo(src_vigia, "TAGS_UTEIS")
    return set(v) if isinstance(v, (list, tuple)) else set()


def _indice_divergente(tags, politica):
    return [t for t, frase in _TAGS_DO_INDICE
            if (t in tags) is not (frase in (politica or u""))]


def _chave_de_dicionario(src_funcao, chave):
    try:
        arv = ast.parse(src_funcao or u"")
    except SyntaxError:
        return False
    for no in ast.walk(arv):
        if isinstance(no, ast.Dict) and any(
                isinstance(k, ast.Constant) and k.value == chave
                for k in no.keys):
            return True
        if (isinstance(no, ast.Assign) and any(
                isinstance(t, ast.Subscript)
                and isinstance(t.slice, ast.Constant) and t.slice.value == chave
                for t in no.targets)):
            return True
    return False


def _adiadas_coerente(src_vigia, politica):
    grava = _chave_de_dicionario(_fonte_da_funcao(src_vigia, "salvar_status"),
                                 "adiadas")
    return grava is (u"adiadas" in (politica or u""))


def _plugins_divergentes(tem_plugin, ponto_unapproved, termos):
    fora = []
    if bool(tem_plugin) is not (u"cada plugin" in (ponto_unapproved or u"")):
        fora.append(u"ponto unapproved")
    if bool(tem_plugin) is not (u"Cada plugin" in (termos or u"")):
        fora.append(u"Termos")
    return fora


_MARCA_DA_ORDEM = u"só então ele apaga os que esta execução não produziu"


def _ordem_coerente(ordem, politica):
    return (ordem is True) is (_MARCA_DA_ORDEM in (politica or u""))


def _marco_do_pescoco(src_motor):
    v = _constante_do_modulo(src_motor, "VERTEBRAS_DO_PESCOCO")
    if not isinstance(v, (list, tuple)):
        return []
    return [m.group(1) for m in (re.match(r"vertebrae_(C\d)$", str(x))
                                 for x in v) if m]


def _frase_do_marco(marco):
    if not marco:
        return u""
    if len(marco) == 1:
        return marco[0]
    return u", ".join(marco[:-1]) + u" e " + marco[-1]


def _marco_nos_termos(marco, termos):
    return bool(marco) and (u"vértebras cervicais %s" % _frase_do_marco(marco)) \
        in (termos or u"")


def _decide_depois_da_base(src_vigia):
    return _referencias_no_fonte(_fonte_da_funcao(src_vigia, "process_series"),
                                 "_tasks_pela_anatomia")


_MARCA_DOS_BACKENDS = u"existem no código, em pesquisa, e não vêm no pacote"
_BACKENDS_EM_PESQUISA = ("xpu", "openvino_gpu")


def _backends_fora_do_pacote(pol):
    pol = pol or {}
    return all(pol.get(b) not in (None, "producao")
               for b in _BACKENDS_EM_PESQUISA)


def _backends_coerente(pol, termos):
    return _backends_fora_do_pacote(pol) is (_MARCA_DOS_BACKENDS
                                             in (termos or u""))


_MARCA_ACHADO_NO_TS = u"também no conjunto do TotalSegmentator"
_MARCA_ACHADO_FORA_DO_FULL = u"nunca no conjunto completo"


def _onde_sai_o_achado(saida_cls, task_do_full, src_output, achados):
    capt = {}

    class _Dublada(saida_cls):
        def __init__(self):
            pass

        def conjunto(self, cod, masks, *a, **k):
            capt[cod] = set(masks)
            return None
    cruas = {u"total_v3": {u"liver": 1}}
    for t in achados:
        cruas[t] = {u"rotulo_de_" + t: 1}
    try:
        _Dublada().totalsegmentator_cru(cruas)
    except Exception:
        capt = {}
    no_ts = bool(achados) and all((u"rotulo_de_" + t) in capt.get("ts", ())
                                  for t in achados)
    filtra = _referencias_no_fonte(
        _fonte_da_funcao(src_output, "vocabulario_do_full"), "task_do_full")
    no_full = (not filtra) or any(task_do_full(t) for t in achados)
    return {"no_ts": no_ts, "no_full": no_full}


_MARCAS_ACHADO_README = (u"raw, to the TotalSegmentator set",
                         u"never to the complete set")


def _achado_divergente(fatos, texto, marcas=None):
    texto = texto or u""
    m_ts, m_full = marcas or (_MARCA_ACHADO_NO_TS, _MARCA_ACHADO_FORA_DO_FULL)
    fora = []
    if bool(fatos.get("no_ts")) is not (m_ts in texto):
        fora.append(u"TS cru: o codigo %s, o texto %s" % (
            u"entrega" if fatos.get("no_ts") else u"NAO entrega",
            u"diz" if m_ts in texto else u"nao diz"))
    if bool(fatos.get("no_full")) is (m_full in texto):
        fora.append(u"FULL: o codigo %s, o texto %s «nunca»" % (
            u"entrega" if fatos.get("no_full") else u"NAO entrega",
            u"diz" if m_full in texto else u"nao diz"))
    return fora


_MARCA_MAMA_SAIU = u"A mama de restrição saiu."
_FRASES_DA_MAMA_DE_RESTRICAO = (
    u"partem do contorno da mama do RTOG",
    u"seguem os limites do contorno da mama do RTOG",
    u"preenchem até esses limites",
    u"A glândula fica sempre inteira dentro de cada uma",
    u"Sem a tarefa dos músculos do tronco elas não saem",
    u"ao lado da mama de restrição")


def _fatos_da_mama(src_mama, v_sets, v_engine):
    oar = set((v_sets or {}).get("PERMITIDOS_NO_OAR") or ())
    return {"existe": bool((src_mama or u"").strip())
            or bool(set(("breast_oar_left", "breast_oar_right")) & oar),
            "mais_mm": (v_engine or {}).get("SUAVIZACAO_A_MAIS_DA_MAMA_MM")}


def _mama_de_restricao_divergente(f, termos):
    t = termos or u""
    fora = []
    if f["existe"]:
        if _MARCA_MAMA_SAIU in t:
            fora.append(u"a mama de restricao existe no codigo, e os Termos "
                        u"dizem que saiu")
        return fora
    if _MARCA_MAMA_SAIU not in t:
        fora.append(u"a mama de restricao saiu do codigo, e os Termos nao "
                    u"dizem")
    for frase in _FRASES_DA_MAMA_DE_RESTRICAO:
        if frase in t:
            fora.append(u"os Termos ainda descrevem a mama de restricao: «%s»"
                        % frase)
    mais = f.get("mais_mm")
    marca = u"com %s mm a mais de suavização" % _num_pt(mais)
    if not isinstance(mais, (int, float)):
        fora.append(u"o motor sem SUAVIZACAO_A_MAIS_DA_MAMA_MM literal")
    elif t.count(marca) < 2:
        fora.append(u"os Termos nao dizem, na 1.2 e na mama que saiu, «%s»"
                    % marca)
    return fora


_NUMERO_EN = {1: u"one", 2: u"two", 3: u"three", 4: u"four", 5: u"five",
              6: u"six", 7: u"seven", 8: u"eight", 9: u"nine", 10: u"ten"}
_NUMERO_PT = {1: u"UMA", 2: u"DUAS", 3: u"TRÊS", 4: u"QUATRO", 5: u"CINCO",
              6: u"SEIS", 7: u"SETE", 8: u"OITO", 9: u"NOVE", 10: u"DEZ"}


def _tasks_medidas(src_tasks):
    try:
        arv = ast.parse(src_tasks or u"")
    except SyntaxError:
        return [], None
    medidas, base = [], None
    for no in arv.body:
        if not isinstance(no, ast.Assign):
            continue
        nomes = [t.id for t in no.targets if isinstance(t, ast.Name)]
        if u"TEMPO_MEDIDO" in nomes and isinstance(no.value, ast.Dict):
            medidas = [k.value for k in no.value.keys
                       if isinstance(k, ast.Constant)
                       and isinstance(k.value, str)]
        if (u"REFERENCIA_DE_VELOCIDADE" in nomes
                and isinstance(no.value, ast.Constant)):
            base = no.value.value
    return medidas, base


def _paragrafo(texto, inicio):
    texto = texto or u""
    i = texto.find(inicio)
    if i < 0:
        return u""
    j = texto.find(u"\n\n", i)
    return texto[i:(j if j >= 0 else len(texto))]


def _velocidades_divergentes(medidas, base, paragrafo, numero, molde,
                             a_base):
    p = u" ".join((paragrafo or u"").split())
    fora = []
    n = len(medidas or ())
    if not n or (molde % numero.get(n, u"\x00")) not in p:
        fora.append(u"o numero (%s)" % (molde % numero.get(n, n)))
    for t in medidas or ():
        if t == base:
            if a_base not in p:
                fora.append(u"a base (%s)" % t)
        elif u"`%s`" % t not in p:
            fora.append(t)
    return fora


def _substitui_depois_de_gravar(src_lote):
    try:
        arv = ast.parse(src_lote or u"")
    except SyntaxError:
        return None
    for fn in ast.walk(arv):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nomes = set(n.id for n in ast.walk(fn) if isinstance(n, ast.Name))
        if u"_velhos" not in nomes:
            continue
        grava = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                 and getattr(c.func, "attr", None) == "full_e_oar"]
        apaga = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                 and getattr(c.func, "attr", None) == "remove"
                 and u"_v" in _nomes(c)]
        if grava and apaga:
            return min(grava) < min(apaga)
    return None


def teste_o_que_a_v82_mudou_nos_documentos():
    secao(u"documentos 1.5: o que a v8.2 mudou, amarrado ao codigo")
    import radai_consent as CS
    import radai_credits as CR
    politica = _plano(CS.POLITICA)
    termos = _plano(CS.TERMOS)
    creditos = _plano(CR.pagina())
    pontos = dict((c, t + u" " + d) for (c, t, d) in CS.PONTOS)

    def _publicadas_intactas(tabela, versao, atual):
        return (tabela.get(u"1.4") == _IMPRESSAO_DA_14
                and (versao != u"1.4" or atual == _IMPRESSAO_DA_14))
    atual = CS.impressao_dos_documentos()
    checar(u"a 1.4 continua em IMPRESSOES_PUBLICADAS como foi publicada, e o "
           u"texto de hoje nao esta sob o numero dela",
           _publicadas_intactas(CS.IMPRESSOES_PUBLICADAS, CS.VERSAO_DOCS,
                                atual),
           u"1.4=%s, versao=%s" % (str(CS.IMPRESSOES_PUBLICADAS.get(u"1.4"))[:16],
                                   CS.VERSAO_DOCS))
    checar(u"  isca: a 1.4 retocada com a impressao de hoje e acusada",
           not _publicadas_intactas(
               dict(CS.IMPRESSOES_PUBLICADAS, **{u"1.4": atual}), u"1.4",
               atual))
    checar(u"  isca: o texto de hoje publicado como 1.4 (versao que nao "
           u"subiu) e acusado",
           not _publicadas_intactas(CS.IMPRESSOES_PUBLICADAS, u"1.4",
                                    u"0" * 64))

    def _quinze_intacta(tabela, versao, atual):
        return (tabela.get(u"1.5") == _IMPRESSAO_DA_15
                and (versao != u"1.5" or atual == _IMPRESSAO_DA_15))
    checar(u"a 1.5 continua em IMPRESSOES_PUBLICADAS como foi publicada, e o "
           u"texto de hoje nao esta sob o numero dela",
           _quinze_intacta(CS.IMPRESSOES_PUBLICADAS, CS.VERSAO_DOCS, atual),
           u"1.5=%s, versao=%s" % (str(CS.IMPRESSOES_PUBLICADAS.get(u"1.5"))[:16],
                                   CS.VERSAO_DOCS))
    checar(u"  isca: a 1.5 retocada com a impressao de hoje e acusada",
           not _quinze_intacta(
               dict(CS.IMPRESSOES_PUBLICADAS, **{u"1.5": atual}), u"1.6",
               atual))
    checar(u"  isca: o texto de hoje sob o numero 1.5 (versao que nao subiu) "
           u"e acusado",
           not _quinze_intacta(CS.IMPRESSOES_PUBLICADAS, u"1.5", u"0" * 64))

    tela = ler("app/radai_bolus_screen.py")
    src_bolus = ler("app/radai_bolus.py")
    checar(u"a Politica nomeia o STL do bolus se, e so se, a rota exporta "
           u"com o ato", _bolus_coerente(tela, politica),
           u"rota exporta=%s" % _bolus_exporta(tela))
    checar(u"  isca: a rota sem a conferencia do ato, com a Politica de hoje: "
           u"reprova", not _bolus_coerente(tela.replace(
               u"radai_bolus.conferir_ato(", u"(lambda *a: True)("), politica))
    checar(u"  isca: a rota que nao registra o ato, com a Politica de hoje: "
           u"reprova", not _bolus_coerente(tela.replace(
               u"_gravar_ato(linha)", u"(lambda *a: None)(linha)"), politica))
    checar(u"  isca: a rota so num comentario (sem o decorador) nao exporta",
           not _bolus_exporta(tela.replace(u'@app.post("/api/bolus/stl")',
                                           u'# @app.post("/api/bolus/stl")')))
    checar(u"  isca: a Politica cala o STL com a rota de hoje: reprova",
           not _bolus_coerente(tela, politica.replace(_MARCA_STL, u"")))
    arq = _arquivo_dos_atos(tela)
    checar(u"li o arquivo do registro dos atos pelo ast (%s)" % arq, bool(arq))
    for nome, txt in ((u"Politica", politica), (u"Termos", termos)):
        checar(u"%s: nomeia o arquivo dos atos do bolus" % nome,
               _nomeia_arquivo_dos_atos(arq, txt))
        checar(u"  isca: %s sem o nome do arquivo dos atos: reprova" % nome,
               not _nomeia_arquivo_dos_atos(arq, txt.replace(arq or u"\x00",
                                                             u"")))
    _outro = _arquivo_dos_atos(tela.replace(
        u'ARQUIVO_ATOS = "%s"' % arq, u'ARQUIVO_ATOS = "outro_atos.log"'))
    checar(u"  isca: o codigo troca o nome do arquivo e os Termos de hoje "
           u"reprovam", _outro == u"outro_atos.log"
           and not _nomeia_arquivo_dos_atos(_outro, termos), str(_outro))
    alerta = _constante_do_modulo(src_bolus, "ALERTA")
    ato = _constante_do_modulo(src_bolus, "FRASE_DO_ATO")
    checar(u"li o alerta e a frase do ato do FONTE de radai_bolus (sem "
           u"importa-lo)", isinstance(alerta, str) and isinstance(ato, str))
    falta = _alerta_que_falta(alerta, ato, termos)
    checar(u"os Termos dizem o alerta do autor e a frase do ato, na letra do "
           u"codigo", not falta, u" | ".join(falta))
    checar(u"  isca: os Termos sem «filamento»: reprova",
           u"filamento" in _alerta_que_falta(alerta, ato,
                                             termos.replace(u"filamento", u"")))
    checar(u"  isca: o ALERTA do codigo sem a dosimetria: reprova",
           u"dosimetria do material é obrigatória" in _alerta_que_falta(
               (alerta or u"").replace(u"dosimetria", u"medida"), ato, termos))
    checar(u"  isca: a frase do ato sem «rascunho»: reprova",
           _FRAGMENTO_DO_ATO in _alerta_que_falta(
               alerta, (ato or u"").replace(u"rascunho", u"arquivo"), termos))
    grava = _bolus_grava_rtstruct(tela, src_bolus)
    checar(u"os Termos dizem que nao ha RTSTRUCT de bolus se, e so se, o "
           u"modulo nao grava um", _sem_rtstruct_coerente(grava, termos),
           u"grava=%s" % grava)
    _grava = src_bolus + (u"\n\ndef _isca_grava(engine, d, m):\n"
                          u"    return engine.build_rtstruct(d, m)\n")
    checar(u"  isca: o modulo passa a chamar build_rtstruct, com os Termos de "
           u"hoje: reprova",
           not _sem_rtstruct_coerente(_bolus_grava_rtstruct(tela, _grava),
                                      termos))
    checar(u"  isca: build_rtstruct so num comentario nao e gravar",
           not _bolus_grava_rtstruct(
               tela, src_bolus + u"\n# engine.build_rtstruct(d, m)\n"))
    checar(u"  isca: os Termos calam a frase com o modulo de hoje: reprova",
           not _sem_rtstruct_coerente(grava, termos.replace(
               _MARCA_SEM_RS_DE_BOLUS, u"")))

    vig = ler("app/radai_watcher.py")
    tags = _tags_da_varredura(vig)
    checar(u"li as tags que a varredura do vigia le, pelo ast (%d)" % len(tags),
           bool(tags))
    div = _indice_divergente(tags, politica)
    checar(u"a Politica declara no indice o estudo e a descricao se, e so se, "
           u"a varredura os le", not div, u", ".join(div))
    for tag, frase in _TAGS_DO_INDICE:
        checar(u"  isca: a varredura sem %s, com a Politica de hoje: reprova"
               % tag, tag in _indice_divergente(tags - {tag}, politica))
        checar(u"  isca: a Politica cala %s com a varredura de hoje: reprova"
               % tag, tag in _indice_divergente(
                   tags, politica.replace(frase, u"")))

    checar(u"a Politica declara as adiadas no STATUS_DIR se, e so se, o "
           u"vigia as grava (chave do dicionario, pelo ast)",
           _adiadas_coerente(vig, politica))
    _sem = vig.replace(u'"adiadas": int(STATE.get("adiadas") or 0),', u"")
    checar(u"  (a isca achou a chave no salvar_status)", _sem != vig)
    checar(u"  isca: salvar_status sem a chave (o comentario fica), com a "
           u"Politica de hoje: reprova", not _adiadas_coerente(_sem, politica))
    checar(u"  isca: a Politica cala as adiadas com o vigia de hoje: reprova",
           not _adiadas_coerente(vig, politica.replace(u"adiadas", u"")))

    try:
        import radai_sets as RS
        tem_plugin = bool(getattr(RS, "PLUGINS", ()))
    except Exception:
        RS = None
        tem_plugin = None
    uap = pontos.get(u"unapproved", u"")
    div = _plugins_divergentes(tem_plugin, uap, termos)
    checar(u"o ponto `unapproved` e os Termos falam dos plugins se, e so se, "
           u"o registro tem plugin", tem_plugin is not None and not div,
           u", ".join(div) or uap[-160:])
    checar(u"  isca: um registro sem plugin, com o texto de hoje: reprova nos "
           u"dois", _plugins_divergentes(False, uap, termos)
           == [u"ponto unapproved", u"Termos"])
    checar(u"  isca: o texto cala os plugins com o registro de hoje: reprova "
           u"nos dois", _plugins_divergentes(
               True, uap.replace(u"cada plugin", u""),
               termos.replace(u"Cada plugin", u""))
           == [u"ponto unapproved", u"Termos"])

    ordem = _substitui_depois_de_gravar(ler("app/radai_batch.py"))
    checar(u"a Politica diz que o novo entra antes de o antigo sair se, e so "
           u"se, o lote faz nessa ordem", _ordem_coerente(ordem, politica),
           u"lote=%s" % ordem)
    _inv = (u"def f(s):\n    _velhos = []\n    for _v in _velhos:\n"
            u"        os.remove(_v)\n    sd.full_e_oar()\n")
    checar(u"  isca: um lote que apaga antes de gravar, com a Politica de "
           u"hoje: reprova", _substitui_depois_de_gravar(_inv) is False
           and not _ordem_coerente(_substitui_depois_de_gravar(_inv),
                                   politica))
    checar(u"  isca: a Politica cala a ordem com o lote de hoje: reprova",
           not _ordem_coerente(ordem, politica.replace(_MARCA_DA_ORDEM, u"")))

    eng = ler("app/engine.py")
    marco = _marco_do_pescoco(eng)
    checar(u"li o marco do pescoco do motor pelo ast (%s)" % u", ".join(marco),
           bool(marco))
    checar(u"os Termos dizem o marco do pescoco que o vigia usa (%s)"
           % _frase_do_marco(marco), _marco_nos_termos(marco, termos))
    _so_c3c4 = _marco_do_pescoco(eng.replace(
        u'VERTEBRAS_DO_PESCOCO = ("vertebrae_C2", ',
        u'VERTEBRAS_DO_PESCOCO = ('))
    checar(u"  isca: o vigia volta ao marco de C3 e C4, com os Termos de "
           u"hoje: reprova", _so_c3c4 == [u"C3", u"C4"]
           and not _marco_nos_termos(_so_c3c4, termos), str(_so_c3c4))
    checar(u"  isca: os Termos calam o marco com o vigia de hoje: reprova",
           not _marco_nos_termos(marco, termos.replace(
               u"vértebras cervicais", u"vértebras")))
    checar(u"o vigia decide a regiao DEPOIS da base (process_series chama "
           u"_tasks_pela_anatomia, pelo ast)", _decide_depois_da_base(vig))
    _sem_anat = vig.replace(u"_novas = _tasks_pela_anatomia(",
                            u"_novas = (lambda *a, **k: [])(")
    checar(u"  (a isca achou a chamada em process_series)", _sem_anat != vig)
    checar(u"  isca: process_series sem a chamada (o nome so em comentario) "
           u"nao decide pela anatomia", not _decide_depois_da_base(_sem_anat))

    try:
        import radai_devices as RD
        pol = dict(getattr(RD, "POLITICA_DE_ADOCAO", {}) or {})
    except Exception as e:
        pol = {}
        checar(u"radai_devices importa", False,
               u"%s: %s" % (type(e).__name__, str(e)[:80]))
    checar(u"os Termos dizem que XPU e OpenVINO nao vem no pacote se, e so "
           u"se, a politica do codigo nao os pos em producao (%s)"
           % u", ".join(u"%s=%s" % (b, pol.get(b))
                        for b in _BACKENDS_EM_PESQUISA),
           _backends_coerente(pol, termos))
    checar(u"  isca: a XPU promovida a producao, com a frase de hoje: reprova "
           u"(a checagem de verdade, e nao a expressao recalculada)",
           not _backends_coerente(dict(pol, xpu="producao"), termos))
    checar(u"  isca: a politica sem o OpenVINO (ausente nao e «fora»): "
           u"reprova", not _backends_coerente(
               dict((k, v) for k, v in pol.items() if k != "openvino_gpu"),
               termos))
    checar(u"  isca: os Termos calam os backends com a politica de hoje: "
           u"reprova", not _backends_coerente(pol, termos.replace(
               _MARCA_DOS_BACKENDS, u"")))

    try:
        import radai_output as RO
    except Exception as e:
        RO = None
        checar(u"radai_output importa (so biblioteca padrao no topo)", False,
               u"%s: %s" % (type(e).__name__, str(e)[:80]))
    achados = _tasks_de_achado_do_motor() or []
    checar(u"li as tasks de achado do fonte do motor (%d)" % len(achados),
           len(achados) >= 1, u", ".join(achados))
    if RO is not None and RS is not None and achados:
        src_out = ler("app/radai_output.py")
        fatos = _onde_sai_o_achado(RO.Saida, RS.task_do_full, src_out,
                                   achados)
        checar(u"medido executando o TS cru: o rotulo de achado chega ao "
               u"STUDY_ts=%s, ao FULL=%s" % (fatos["no_ts"], fatos["no_full"]),
               True)
        _pt = (_MARCA_ACHADO_NO_TS, _MARCA_ACHADO_FORA_DO_FULL)
        for nome, txt, marcas in (
                (u"Creditos", creditos, _pt), (u"Termos", termos, _pt),
                (u"ponto deteccao", pontos.get(u"deteccao", u""), _pt),
                (u"README", u" ".join(ler("README.md").split()),
                 _MARCAS_ACHADO_README)):
            div = _achado_divergente(fatos, txt, marcas)
            checar(u"%s: dizem onde sai o achado (TS cru sim, FULL e OAR "
                   u"nunca) se, e so se, o codigo faz assim" % nome, not div,
                   u" | ".join(div))
            checar(u"  isca: %s calam o TS cru com o codigo de hoje: reprova"
                   % nome, bool(_achado_divergente(
                       fatos, txt.replace(marcas[0], u""), marcas)))
            checar(u"  isca: %s calam o «nunca no conjunto completo»: reprova"
                   % nome, bool(_achado_divergente(
                       fatos, txt.replace(marcas[1], u""), marcas)))

        class _TsQueFiltra(RO.Saida):
            def totalsegmentator_cru(self, cruas):
                return RO.Saida.totalsegmentator_cru(self, dict(
                    (t, m) for t, m in (cruas or {}).items()
                    if t not in achados))
        _f2 = _onde_sai_o_achado(_TsQueFiltra, RS.task_do_full, src_out,
                                 achados)
        checar(u"  isca: um TS cru que filtra o achado, com os Creditos de "
               u"hoje: reprova", _f2["no_ts"] is False
               and bool(_achado_divergente(_f2, creditos)), str(_f2))
        _f3 = _onde_sai_o_achado(RO.Saida, lambda t: True, src_out, achados)
        checar(u"  isca: uma task de achado que alimenta o FULL, com os "
               u"Creditos de hoje: reprova", _f3["no_full"] is True
               and bool(_achado_divergente(_f3, creditos)), str(_f3))
        _sem_filtro = src_out.replace(u"radai_sets.task_do_full(task)",
                                      u"True")
        checar(u"  (a isca achou o filtro em vocabulario_do_full)",
               _sem_filtro != src_out)
        _f4 = _onde_sai_o_achado(RO.Saida, RS.task_do_full, _sem_filtro,
                                 achados)
        checar(u"  isca: vocabulario_do_full sem o filtro por task: o achado "
               u"chegaria ao FULL", _f4["no_full"] is True, str(_f4))
    checar(u"  isca: o ponto `deteccao` de antes (so «arquivo proprio») "
           u"reprova", bool(_achado_divergente(
               {"no_ts": True, "no_full": False},
               u"o que ela devolve sai num arquivo próprio, e o registro do "
               u"caso guarda quais rodaram.")))

    fm = _fatos_da_mama(ler("app/radai_breast.py"),
                        _valores_do_modulo(ler("app/radai_sets.py")),
                        _valores_do_modulo(ler("app/engine.py")))
    div = _mama_de_restricao_divergente(fm, termos)
    checar(u"Termos: a mama de restricao (existe no codigo: %s) e a glandula "
           u"com %s mm a mais de suavizacao — o codigo e os Termos (1.2)"
           % (fm["existe"], fm["mais_mm"]), not div, u" | ".join(div))
    checar(u"  isca: a mama de restricao de volta no codigo, com os Termos de "
           u"hoje: reprova", bool(_mama_de_restricao_divergente(
               dict(fm, existe=True), termos)))
    checar(u"  isca: os Termos voltam a descrever os limites dela: reprova",
           bool(_mama_de_restricao_divergente(
               fm, termos + u" As mamas de restrição partem do contorno da "
                            u"mama do RTOG.")))
    checar(u"  isca: os Termos calam que ela saiu: reprova",
           bool(_mama_de_restricao_divergente(
               fm, termos.replace(_MARCA_MAMA_SAIU, u"X"))))
    checar(u"  isca: outra suavizacao a mais da glandula no motor: reprova",
           bool(_mama_de_restricao_divergente(dict(fm, mais_mm=5.0),
                                              termos)))

    medidas, base = _tasks_medidas(ler("app/radai_tasks.py"))
    checar(u"li as tasks medidas do fonte de radai_tasks (%d, base %s)"
           % (len(medidas), base), bool(medidas) and bool(base),
           u", ".join(medidas))
    textos = [
        (u"README", _paragrafo(ler("README.md"), u"**Choosing what runs.**"),
         _NUMERO_EN, u"%s tasks so far", u"the base itself"),
    ]
    if OFICINA is None:
        _componentes.pulado(u"as tasks medidas no documento de engenharia")
    else:
        textos.append(OFICINA.velocidades_no_documento(
            sys.modules[__name__], base))
    for nome, par, tab, molde, a_base in textos:
        div = _velocidades_divergentes(medidas, base, par, tab, molde, a_base)
        checar(u"%s: diz quantas e quais tasks tem a etiqueta MEDIDA (as de "
               u"TEMPO_MEDIDO)" % nome, bool(par) and not div,
               u", ".join(div) or u"paragrafo nao achado")
        checar(u"  isca: uma task medida a mais no codigo, com o %s de hoje: "
               u"reprova" % nome, bool(_velocidades_divergentes(
                   medidas + [u"lung_vessels"], base, par, tab, molde,
                   a_base)))
        if len(medidas) > 1:
            _outra = [t for t in medidas if t != base][0]
            checar(u"  isca: o %s cala uma medida (%s): reprova"
                   % (nome, _outra), _outra in _velocidades_divergentes(
                       medidas, base, par.replace(u"`%s`" % _outra, u""),
                       tab, molde, a_base))


_VERSAO_DOS_REGISTROS = u"1.5"


def teste_os_registros_citam_a_impressao_publicada():
    secao(u"os registros dizem a impressao publicada da %s e quantas vezes "
          u"ela foi selada" % _VERSAO_DOS_REGISTROS)
    import radai_consent as CS
    pub = CS.IMPRESSOES_PUBLICADAS.get(_VERSAO_DOS_REGISTROS) or u""
    n = CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get(_VERSAO_DOS_REGISTROS)
    checar(u"li a impressao publicada e as resselagens do dado de "
           u"radai_consent (%s…, %s)" % (pub[:8], n), len(pub) == 64 and bool(n))
    checar(u"toda versao publicada tem o numero de resselagens no dado",
           set(CS.IMPRESSOES_PUBLICADAS) <= set(
               CS.RESSELAGENS_ANTES_DA_PUBLICACAO),
           str(sorted(set(CS.IMPRESSOES_PUBLICADAS)
                      - set(CS.RESSELAGENS_ANTES_DA_PUBLICACAO))))
    if OFICINA is None:
        _componentes.pulado(u"os registros de engenharia que citam a impressao")
        return
    OFICINA.registros_citam_a_impressao(sys.modules[__name__], pub, n)


def teste_o_aceite_tem_o_seletor_com_bandeira():
    secao(u"o aceite tem o seletor com bandeira, e a impressao nao muda")
    import hashlib
    import radai_consent as CS

    marc = re.sub(r"(?s)<!--.*?-->", u" ", CS.PAGINA_ACEITE)
    marc = re.sub(r"(?s)<script.*?</script>", u" ", marc)
    checar(u"a ancora de hoje esta no canto do aceite (fora de comentario)",
           u'<div class="ac-lang"><span data-radai-idiomas></span></div>'
           in marc)
    checar(u"  e a de ontem saiu da marcacao", u"data-radai-lang" not in marc)
    checar(u"a pagina servida costura o dicionario que monta o seletor",
           u'src="/radai-idiomas.js"' in CS.pagina_aceite())

    def impressao_com(pagina):
        real = CS.PAGINA_ACEITE
        try:
            CS.PAGINA_ACEITE = pagina
            return hashlib.sha256(
                CS.texto_canonico().encode("utf-8")).hexdigest()
        finally:
            CS.PAGINA_ACEITE = real
    hoje = impressao_com(CS.PAGINA_ACEITE)
    ontem = impressao_com(CS.PAGINA_ACEITE.replace(
        u"<span data-radai-idiomas></span>", u"<span data-radai-lang></span>"))
    checar(u"trocar a ancora nao muda a impressao dos documentos",
           hoje == ontem == CS.impressao_dos_documentos(), hoje[:12])
    checar_doc("impressao", u"  e ela e a publicada da versao em vigor",
           CS.IMPRESSOES_PUBLICADAS.get(CS.VERSAO_DOCS) == hoje,
           u"%s != %s" % (str(CS.IMPRESSOES_PUBLICADAS.get(CS.VERSAO_DOCS))[:12],
                          hoje[:12]))
    isca = impressao_com(CS.PAGINA_ACEITE.replace(
        u"<span data-radai-idiomas></span>",
        u"<span data-radai-idiomas>Idioma</span>"))
    checar(u"  (isca) uma palavra dentro da ancora muda a impressao",
           isca != hoje)



_VALORES = {}


def _valores_do_modulo(src):
    chave = hash(src or u"")
    if chave in _VALORES:
        return _VALORES[chave]
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        _VALORES[chave] = {}
        return {}
    env = {}

    def _av(n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name) and n.id in env:
            return env[n.id]
        if isinstance(n, (ast.Tuple, ast.List)):
            return tuple(_av(e) for e in n.elts)
        if isinstance(n, ast.Dict):
            if any(k is None for k in n.keys):
                raise ValueError(u"dicionario com **")
            return dict((_av(k), _av(v)) for k, v in zip(n.keys, n.values))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -_av(n.operand)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            return _av(n.left) + _av(n.right)
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id in ("frozenset", "set", "tuple") and n.args):
            return frozenset(_av(n.args[0]))
        raise ValueError(u"nao e constante")

    for no in arv.body:
        if isinstance(no, ast.Assign):
            alvos = no.targets
        elif isinstance(no, ast.AnnAssign) and no.value is not None:
            alvos = [no.target]
        else:
            continue
        for t in alvos:
            if isinstance(t, ast.Name):
                try:
                    env[t.id] = _av(no.value)
                except Exception:
                    env.pop(t.id, None)
    _VALORES[chave] = env
    return env


def _nomes_de_topo(src, tipo):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return set()
    cls = ((ast.FunctionDef, ast.AsyncFunctionDef) if tipo == "def"
           else (ast.ClassDef,))
    return set(n.name for n in arv.body if isinstance(n, cls))


def _importa(src, modulo):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    for n in ast.walk(arv):
        if isinstance(n, ast.Import) and any(a.name == modulo
                                             for a in n.names):
            return True
        if isinstance(n, ast.ImportFrom) and n.module == modulo:
            return True
        if isinstance(n, ast.Constant) and n.value == modulo:
            return True
    return False


def _strings_do_fonte(src):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return []
    return [n.value for n in ast.walk(arv)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _chamada_sob_condicao(src, chamada, condicao):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    pais = {}
    for no in ast.walk(arv):
        for f in ast.iter_child_nodes(no):
            pais[f] = no
    achou = False
    for no in ast.walk(arv):
        if not (isinstance(no, ast.Call) and (
                getattr(no.func, "attr", None) == chamada
                or getattr(no.func, "id", None) == chamada)):
            continue
        achou = True
        p, ok = pais.get(no), False
        while p is not None:
            if isinstance(p, ast.If) and _referencias(p.test, condicao):
                ok = True
                break
            p = pais.get(p)
        if not ok:
            return False
    return achou


def _num_pt(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return u"\x00"
    if f == int(f):
        return u"%d" % int(f)
    return (u"%g" % f).replace(u".", u",")


def _trecho(texto, ini, fim):
    t = texto or u""
    i = t.find(ini)
    if i < 0:
        return u""
    j = t.find(fim, i + len(ini))
    return t[i:(j if j >= 0 else len(t))]


_MARCA_VIGIA_AUTO = u"O vigia da noite roda sempre o AUTO"
_MARCA_VIGIA_AUTO_PONTO = u"o vigia roda sempre o AUTO"


def _modos_divergentes(v_modes, v_vigia, termos, ponto):
    fora = []
    modos = tuple(v_modes.get("MODOS_DA_SERIE") or ())
    tres = modos == ("fast", "auto", "perso")
    sec = _trecho(termos, u"1.1 · Os três modos", u"1.2 · O que sai")
    diz_tres = bool(sec) and all(m in sec for m in (u"FAST", u"AUTO",
                                                     u"PERSONALIZADO"))
    if tres is not diz_tres:
        fora.append(u"o codigo tem os modos %s, e a secao 1.1 %s os tres"
                    % (modos, u"diz" if diz_tres else u"nao diz"))
    auto = v_vigia.get("MODO_DO_VIGIA") == "auto"
    if auto is not (_MARCA_VIGIA_AUTO in termos):
        fora.append(u"Termos: o vigia %s AUTO no codigo" % (
            u"e" if auto else u"NAO e"))
    if auto is not (_MARCA_VIGIA_AUTO_PONTO in (ponto or u"")):
        fora.append(u"ponto deteccao: o vigia %s AUTO no codigo" % (
            u"e" if auto else u"NAO e"))
    return fora


_NOMES_FORA_DO_FAST = {"pelvic_muscles": u"Muscles_ai",
                       "bag_bowel": u"Bag_Bowel_ai",
                       "bag_bowel_oar": u"Bag_Bowel_OAR_ai",
                       "anus": u"Anus_ai", "Skin": u"Skin_ai",
                       "ChestWall_L": u"ChestWall_L_ai", "ChestWall_R": u"ChestWall_R_ai",
                       "ribs_left": u"Ribs_L_ai", "ribs_right": u"Ribs_R_ai",
                       "costal_cartilages": u"Cartilage_Costal_ai"}


def _cita_nome(nome, texto):
    return bool(re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])"
                          % re.escape(nome), texto or u""))


def _fast_divergente(v_sets, v_engine, termos):
    par = _trecho(termos, u"O entregue do FAST",
                  u"Não há conjunto completo ao lado dele")
    if not par:
        return [u"os Termos nao descrevem o entregue do FAST"]
    fora = []
    tira = set(v_sets.get("FORA_DO_OAR_FAST") or ())
    for k in sorted(tira):
        nome = _NOMES_FORA_DO_FAST.get(k)
        if not nome or not _cita_nome(nome, par):
            fora.append(u"o FAST tira %s no codigo, e o texto nao diz" % k)
    for k, nome in sorted(_NOMES_FORA_DO_FAST.items()):
        if _cita_nome(nome, par) and k not in tira:
            fora.append(u"o texto tira %s do FAST, e o codigo nao" % nome)
    for frase in (u"tolerância de %s mm" % _num_pt(
                      v_engine.get("DECIMACAO_FAST_MM")),
                  u"pelo menos %s pontos" % _num_pt(
                      v_engine.get("MIN_PONTOS_DECIMADO")),
                  u"menos de %s cm²" % _num_pt(
                      (v_engine.get("AREA_MINIMA_DECIMADA_MM2") or 0) / 100.0),
                  u"em mais de %s%%" % _num_pt(
                      (v_engine.get("PERDA_MAXIMA_DECIMACAO") or 0) * 100.0)):
        if frase not in par:
            fora.append(u"o paragrafo do FAST nao diz «%s»" % frase)
    return fora


_MARCA_CLIP = u"O recorte nas laterais, e nenhum por âncora."
_FIM_CLIP = u"A base nunca é recortada."
_MARCA_CLIP_CORPO = u"pelo recorte no corpo"
_MARCA_CLIP_SEM_ANCORA = (u"Nenhuma tarefa roda em volta de uma estrutura que "
                          u"a série já desenhou")
_NOMES_DO_RECORTE = {"trunk_cavities": u"a cavidade do tronco",
                     "breasts": u"a glândula mamária",
                     "abdominal_muscles": u"os músculos do tronco",
                     "lung_vessels": u"os vasos pulmonares"}
_CONTAGEM_PT = {1: u"uma", 2: u"duas", 3: u"três", 4: u"quatro",
                5: u"cinco"}


def _recortes_do_registro(v_engine):
    reg = v_engine.get("RECORTE_POR_TASK") or {}
    ancora = sorted(t for t, e in reg.items()
                    if isinstance(e, dict) and (
                        e.get("medido")
                        or (isinstance(e.get("fast"), dict)
                            and e["fast"].get("medido"))))
    laterais = sorted(t for t, e in reg.items()
                      if isinstance(e, dict) and e.get("lateral_pelo_corpo"))
    return ancora, laterais


def _clip_divergente(v_engine, termos, v_vigia=None):
    ancora, laterais = _recortes_do_registro(v_engine)
    esperado = (not ancora) and bool(laterais)
    diz = _MARCA_CLIP in termos
    fora = []
    if esperado is not diz:
        fora.append(u"recorte no codigo: por ancora=%s, nas laterais=%s; os "
                    u"Termos %s a frase" % (ancora, laterais,
                                            u"dizem" if diz else u"nao dizem"))
    if not (esperado and diz):
        return fora
    par = _trecho(termos, _MARCA_CLIP, _FIM_CLIP)
    n = _CONTAGEM_PT.get(len(laterais), u"%d" % len(laterais))
    frases = [u"%s tarefas" % n,
              u"%s mm de margem" % _num_pt(v_engine.get("MARGEM_DO_CORPO_MM")),
              u"mais de −%s HU" % _num_pt(
                  -float(v_engine.get("LIMIAR_DO_CORPO_HU") or 0)),
              _MARCA_CLIP_SEM_ANCORA]
    frases += [_NOMES_DO_RECORTE.get(t, t) for t in laterais]
    for frase in frases:
        if frase not in par:
            fora.append(u"o paragrafo do recorte nao diz «%s»" % frase)
    for t, nome in sorted(_NOMES_DO_RECORTE.items()):
        if t not in laterais and nome in par:
            fora.append(u"o paragrafo cita %s, que o codigo nao recorta" % t)
    if v_vigia is not None:
        corpo = str((v_vigia.get("DEFAULTS") or {}).get(
            "RECORTE_NO_CORPO")) == "1"
        if corpo is not (_MARCA_CLIP_CORPO in par):
            fora.append(u"o recorte no corpo %s ligado de fabrica, e o "
                        u"paragrafo do recorte %s"
                        % (u"vem" if corpo else u"NAO vem",
                           u"o cita" if _MARCA_CLIP_CORPO in par
                           else u"nao o cita"))
    return fora


_MARCA_TS_PEDIDO = u"quando ele é pedido"
_MARCA_TS_TERMOS = u"Ele só sai quando pedido, no PERSONALIZADO"


def _ts_so_por_pedido(src_batch, src_vigia):
    corpo = _fonte_da_funcao(src_batch, "ts_cru_pedido")
    pede = (bool(corpo) and _referencias_no_fonte(corpo, "MODO_PERSO")
            and u"ts" in _strings_do_fonte(corpo))
    return (pede and _chamada_sob_condicao(src_batch, "totalsegmentator_cru",
                                           "ts_cru_pedido")
            and not _referencias_no_fonte(src_vigia, "totalsegmentator_cru"))


def _ts_divergente(por_pedido, textos):
    return [u"%s: o codigo %s, o texto %s «%s»" % (
                nome, u"so grava por pedido" if por_pedido
                else u"NAO grava so por pedido",
                u"diz" if marca in (txt or u"") else u"nao diz", marca)
            for nome, txt, marca in textos
            if (marca in (txt or u"")) is not por_pedido]


_INICIO_OBSOLETAS = u"O arquivo de configuração de uma versão anterior"
_FIM_OBSOLETAS = u"«chave obsoleta ignorada»"


def _obsoletas_divergentes(v_vigia, src_vigia, docs):
    d = v_vigia.get("CHAVES_OBSOLETAS") or {}
    principais = sorted(k for k, v in d.items()
                        if not str(v).startswith(u"nome antigo"))
    todas = sorted(d)
    termos = dict(docs).get(u"termos", u"")
    par = _trecho(termos, _INICIO_OBSOLETAS, _FIM_OBSOLETAS)
    fora = []
    if not d:
        return [u"nao li CHAVES_OBSOLETAS do vigia"]
    if not par:
        fora.append(u"os Termos nao tem o paragrafo das chaves obsoletas")
    for k in principais:
        if k not in par:
            fora.append(u"os Termos nao listam %s entre as obsoletas" % k)
        if re.search(r"(?m)^%s=" % re.escape(k), src_vigia or u""):
            fora.append(u"%s ainda esta no DEFAULT_CFG" % k)
    for nome, txt in docs:
        t = (txt or u"").replace(par, u"") if (nome == u"termos" and par) \
            else (txt or u"")
        for k in todas:
            if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(k),
                         t):
                fora.append(u"%s cita %s fora da lista das obsoletas"
                            % (nome, k))
    if u"chave obsoleta ignorada" not in (src_vigia or u""):
        fora.append(u"o vigia nao diz «chave obsoleta ignorada» no arranque")
    return fora


def _trava_divergente(v_vigia, src_engine, termos):
    d = v_vigia.get("DEFAULTS") or {}
    par = _trecho(termos, u"Quando uma tarefa trava.", u"TIMEOUT_TASK_H")
    fora = []
    for frase in (u"depois de %s minutos sem sinal de vida"
                  % d.get("TRAVA_SEM_PULSO_MIN"),
                  u"de %s minutos sem andar" % d.get("TRAVA_PAGINANDO_MIN"),
                  u"em %s%% ou mais" % d.get("TRAVA_RAM_PCT")):
        if frase not in par:
            fora.append(u"o paragrafo do travamento nao diz «%s»" % frase)
    for k in ("TRAVA_SEM_PULSO_MIN", "TRAVA_PAGINANDO_MIN", "TRAVA_RAM_PCT"):
        if k not in d:
            fora.append(u"%s nao esta em DEFAULTS" % k)
        elif k not in par:
            fora.append(u"os Termos nao nomeiam a chave %s" % k)
    if "TaskTravada" not in _nomes_de_topo(src_engine, "class"):
        fora.append(u"o motor nao tem TaskTravada, e os Termos descrevem a "
                    u"trava")
    return fora


_SECAO_REGRAS = (u"1.3 · O que o programa tira antes de gravar",
                 u"1.4 · Onde roda")


def _regras_divergentes(v_engine, src_engine, termos, chaves_dos_pontos):
    par = _trecho(termos, *_SECAO_REGRAS)
    ordem = v_engine.get("ORDEM_DO_FULL") or ()
    tem = ("aplicar_regras_de_gravacao" in _nomes_de_topo(src_engine, "def")
           and bool(ordem) and ordem[0][0] == "regras")
    fora = []
    if tem is not bool(par):
        fora.append(u"as regras %s no codigo, e os Termos %s a secao 1.3"
                    % (u"rodam" if tem else u"NAO rodam",
                       u"tem" if par else u"nao tem"))
    if tem is not (u"remove" in chaves_dos_pontos):
        fora.append(u"as regras %s no codigo, e o ponto `remove` %s"
                    % (u"rodam" if tem else u"NAO rodam",
                       u"existe" if u"remove" in chaves_dos_pontos
                       else u"nao existe"))
    if not (tem and par):
        return fora
    pisos = [x[2] for x in (v_engine.get("MARCOS_DE_REGIAO") or ())
             if x and x[0] == "cabeca_pescoco"]
    for frase in (
            u"menos de %s cm³" % _num_pt(
                v_engine.get("VOLUME_MAXIMO_NA_BORDA_CM3")),
            u"o maior entre %s mm e %s cortes" % (
                _num_pt(v_engine.get("FAIXA_DA_BORDA_MM")),
                _num_pt(v_engine.get("FAIXA_DA_BORDA_CORTES"))),
            u"menos de %s%% do volume" % _num_pt(
                (v_engine.get("FRACAO_DA_PODA") or 0) * 100.0),
            u"menos de %s cm³" % _num_pt(v_engine.get("VOLUME_DA_PODA_CM3")),
            u"coração de %s cm³ ou mais" % _num_pt(
                v_engine.get("VOLUME_MINIMO_CORACAO_CM3")),
            u"encéfalo com %s cm³ ou mais" % _num_pt(
                pisos[0] if pisos else None)):
        if frase not in par:
            fora.append(u"a secao 1.3 nao diz «%s»" % frase)
    ao_lado = _chamada_sob_condicao(_fonte_da_funcao(src_engine,
                                                     "build_rtstruct"),
                                    "limpar_fora_do_corpo", "cru")
    if ao_lado is not (_MARCA_R3_AO_LADO in par):
        fora.append(u"a R3 %s nos arquivos ao lado, e a secao 1.3 %s"
                    % (u"vale" if ao_lado else u"NAO vale",
                       u"diz" if _MARCA_R3_AO_LADO in par else u"nao diz"))
    return fora


_MARCA_R3_AO_LADO = (u"Esta regra vale também nos arquivos de plugin e de "
                     u"comparação")

_MARCA_PULMAO_UNIAO = u"O pulmão é medido pela união dos"
_MARCA_PULMAO_ILHA = u"No pulmão, o pedaço solto é do"


def _pulmao_pela_uniao_divergente(v_engine, termos):
    par = _trecho(termos, *_SECAO_REGRAS)
    if not par:
        return []
    uniao = {"lung_left", "lung_right"} <= set(
        v_engine.get("ORGAOS_POR_PARTES") or ())
    fora = []
    for marca in (_MARCA_PULMAO_UNIAO, _MARCA_PULMAO_ILHA):
        if uniao is not (marca in par):
            fora.append(u"o motor %s o pulmao pela uniao dos lobos, e a secao "
                        u"1.3 %s «%s»"
                        % (u"julga" if uniao else u"NAO julga",
                           u"diz" if marca in par else u"nao diz", marca))
    if uniao and u"pulmão e lobos" in par:
        fora.append(u"a secao 1.3 ainda diz «pulmão e lobos» (o lobo julgado "
                    u"sozinho)")
    return fora


def _pescoco_divergente(v_engine, termos):
    v = v_engine.get("VOLUME_MINIMO_VERTEBRA_CERVICAL_CM3")
    frase = u"com %s cm³ cada" % _num_pt(v)
    return [] if frase in (termos or u"") else [
        u"os Termos nao dizem «%s»" % frase]


_NOMES_DA_PELVE = {"pelvic_muscles": u"Muscles_ai",
                   "bone_pelvic": u"Bone_Pelvic_ai",
                   "iliac_crest_left": u"IliacCrest_L_ai",
                   "iliac_crest_right": u"IliacCrest_R_ai",
                   "anus": u"Anus_ai"}
_MARCA_PELVE = u"só com a pelve identificada"


def _pelve_divergente(v_engine, termos):
    d = v_engine.get("REGIAO_EXIGIDA_NO_OAR") or {}
    par = _trecho(termos, u"O conjunto entregue", u"O entregue do FAST")
    exige = sorted(k for k, v in d.items() if v == "pelve")
    fora = []
    if bool(exige) is not (_MARCA_PELVE in par):
        fora.append(u"o codigo %s o composto da pelve a ela, e o texto %s"
                    % (u"prende" if exige else u"NAO prende",
                       u"diz" if _MARCA_PELVE in par else u"nao diz"))
    for k in exige:
        if _NOMES_DA_PELVE.get(k, u"\x00") not in par:
            fora.append(u"o texto nao nomeia %s" % k)
    return fora


def _pele_e_parede_divergentes(v_skin, termos):
    fora = []
    e = v_skin.get("ESPESSURA_PELE_MM")
    ditas = set(re.findall(u"casca de (\\d+) mm", termos or u""))
    if not ditas or ditas != {_num_pt(e)}:
        fora.append(u"a pele tem %s mm no codigo, e os Termos dizem %s"
                    % (_num_pt(e), sorted(ditas)))
    par = _trecho(termos, u"A parede torácica", u"A pele")
    base = v_skin.get("BASE_DA_PAREDE") or ()
    na_cavidade = "thoracic_cavity" in base
    if na_cavidade is not (u"parte da cavidade torácica de cada lado" in par):
        fora.append(u"a base da parede %s a cavidade no codigo"
                    % (u"tem" if na_cavidade else u"NAO tem"))
    for frase in (u"expandida em %s mm" % _num_pt(
                      v_skin.get("MARGEM_PAREDE_MM")),
                  u"suavizada em %s mm" % _num_pt(
                      v_skin.get("SUAVIZACAO_PAREDE_MM"))):
        if frase not in par:
            fora.append(u"o paragrafo da parede nao diz «%s»" % frase)
    cob = v_skin.get("COBERTURA_MINIMA_DAS_COSTELAS")
    if cob:
        frase = u"cobre ao menos %s%% das costelas" % _num_pt(cob * 100.0)
        if frase not in par:
            fora.append(u"a parede cobre %s das costelas no codigo, e o "
                        u"paragrafo nao diz «%s»" % (cob, frase))
    elif u"das costelas: onde a suavização" in par:
        fora.append(u"o codigo nao confere a cobertura das costelas, e os "
                    u"Termos dizem")
    fecho = v_skin.get("FECHAMENTO_ANTERIOR_MM")
    alcance = v_skin.get("ALCANCE_DO_FECHAMENTO_MM")
    pele = _trecho(termos, u"A pele ( Skin ) é uma casca", u"1.3 ·")
    if fecho and alcance:
        for frase in (u"um corpo que leva todas as estruturas já segmentadas",
                      u"o tecido a até %s mm" % _num_pt(alcance),
                      u"um fechamento de %s mm" % _num_pt(fecho)):
            if frase not in pele:
                fora.append(u"o paragrafo da pele nao diz «%s»" % frase)
    elif u"um corpo que leva todas as estruturas" in pele:
        fora.append(u"o codigo nao monta o corpo da pele, e os Termos dizem")
    return fora


def _valores_da_pele(src):
    v = dict(_valores_do_modulo(src))
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return v

    def _av(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name) and isinstance(v.get(n.id), (int, float)):
            return float(v[n.id])
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mult, ast.Add)):
            a, b = _av(n.left), _av(n.right)
            return a * b if isinstance(n.op, ast.Mult) else a + b
        raise ValueError(u"nao e numero")

    for no in arv.body:
        if (isinstance(no, ast.Assign) and len(no.targets) == 1
                and isinstance(no.targets[0], ast.Name)
                and no.targets[0].id not in v):
            try:
                v[no.targets[0].id] = _av(no.value)
            except Exception:
                pass
    return v


_MARCA_RETO = u"O reto sai como Rectum_ai"


def _reto_divergente(v_sets, termos):
    aposentado = "_der" in tuple(v_sets.get("SUFIXOS_APOSENTADOS") or ())
    if aposentado is not (_MARCA_RETO in termos):
        return [u"o sufixo da derivada %s aposentado, e os Termos %s"
                % (u"esta" if aposentado else u"NAO esta",
                   u"dizem Rectum_ai" if _MARCA_RETO in termos
                   else u"nao dizem")]
    return []


_MODULOS_APAGADOS = (("radai_compiler.py", u"compilador"),
                     ("radai_calibrator.py", u"calibrador"))


def _apagados_citados(existe, docs):
    fora = []
    for arq, palavra in _MODULOS_APAGADOS:
        if existe(arq):
            continue
        for nome, txt in docs:
            if palavra in (txt or u"").lower():
                fora.append(u"%s fala do %s, e %s nao existe"
                            % (nome, palavra, arq))
    return fora


_MARCA_TREINO_SAIDA = u"O acervo de treino : grava"
_MARCA_TREINO_LEGADO = u"esta versão não grava mais neles"
_MARCA_TREINO_TERMOS = (u"Esta versão não grava pares de imagem e máscara "
                        u"para treino")


def _saidas_do_ciclo(fontes_app):
    treino = any(_importa(s, "radai_training") for n, s in fontes_app.items()
                 if n not in ("radai_training.py",))
    feedback = any(u"mailto:" in s for n, s in fontes_app.items()
                   if n not in ("radai_consent.py", "radai_credits.py"))
    return treino, feedback


def _ciclo_divergente(treino_vivo, feedback, politica, chaves_dos_pontos,
                      termos=None):
    fora = []
    if termos is not None and (_MARCA_TREINO_TERMOS in termos) is treino_vivo:
        fora.append(u"os Termos %s que esta versao nao grava para treino"
                    % (u"dizem" if treino_vivo else u"nao dizem"))
    if (_MARCA_TREINO_SAIDA in politica) is not treino_vivo:
        fora.append(u"o acervo de treino %s gravado, e a Politica %s como "
                    u"saida" % (u"e" if treino_vivo else u"NAO e",
                               u"o declara" if not treino_vivo
                               else u"nao o declara"))
    if (_MARCA_TREINO_LEGADO in politica) is treino_vivo:
        fora.append(u"a Politica %s que esta versao nao grava o acervo de "
                    u"treino" % (u"diz" if treino_vivo else u"nao diz"))
    if (u"acervo" in chaves_dos_pontos) is not treino_vivo:
        fora.append(u"o ponto `acervo` %s, e o acervo de treino %s gravado"
                    % (u"existe" if u"acervo" in chaves_dos_pontos
                       else u"nao existe",
                       u"e" if treino_vivo else u"NAO e"))
    if (u"e-mail de feedback" in politica) is not feedback:
        fora.append(u"o e-mail de feedback %s no codigo, e a Politica %s"
                    % (u"existe" if feedback else u"NAO existe",
                       u"o cita" if u"e-mail de feedback" in politica
                       else u"nao o cita"))
    return fora


_MARCA_SEM_BOTAO = (u"O programa não tem tela nem rota que baixe peso de "
                    u"modelo")
_MARCA_ROTA_BAIXAR = u"POST /api/modelos/baixar"


def _baixar_modelo(fontes_app):
    rota = (_rota_da_funcao(fontes_app.get("radai_models.py", u""), "_baixar")
            == u"/api/modelos/baixar")
    botao = any(u"/api/modelos/baixar" in s for n, s in fontes_app.items()
                if n not in ("radai_models.py", "radai_consent.py"))
    return rota, botao


def _baixar_divergente(rota, botao, politica):
    fora = []
    if (_MARCA_SEM_BOTAO in politica) is (botao or rota):
        fora.append(u"o botao ou a rota de baixar %s, e a Politica %s "
                    u"que nao ha"
                    % (u"existe" if (botao or rota) else u"NAO existe",
                       u"diz" if _MARCA_SEM_BOTAO in politica else u"nao diz"))
    if (_MARCA_ROTA_BAIXAR in politica) is not rota:
        fora.append(u"a rota de baixar %s, e a Politica %s"
                    % (u"existe" if rota else u"NAO existe",
                       u"a cita" if _MARCA_ROTA_BAIXAR in politica
                       else u"nao a cita"))
    return fora


_CAMPOS_DO_EM_USO = {"versao": u"a versão do formato",
                     "app": u"o nome do programa", "atualizado": u"a hora",
                     "pids": u"os números de processo", "porta": u"a porta",
                     "segmentando": u"se há uma série sendo segmentada"}
_O_QUE_O_OTIMIZAR_DESCREVIA = (
    (u"Termos", u"fecha programas"),
    (u"Termos", u"O «Restaurar» reabre"),
    (u"Termos", u"ele pausa serviços do Windows"),
    (u"Termos", u"Diagnosticar e otimizar"),
    (u"Politica", u"que o «Otimizar» grava"),
    (u"Politica", u"Diagnosticar e otimizar"),
    (u"Politica", u"apaga o cache do pip"),
)


def _otimizar_descrito(textos, marcas=_O_QUE_O_OTIMIZAR_DESCREVIA):
    return [u"%s: «%s»" % (nome, marca) for nome, marca in marcas
            if marca in (textos.get(nome) or u"")]


def _em_uso_divergente(chaves, v_cleaner, src_vigia, politica):
    par = _trecho(politica, u"em_uso.json , que o programa grava",
                  u"nada de paciente")
    fora = []
    if not par:
        return [u"a Politica nao descreve o em_uso.json"]
    for k in sorted(chaves):
        frase = _CAMPOS_DO_EM_USO.get(k)
        if not frase or frase not in par:
            fora.append(u"o em_uso.json leva `%s`, e a Politica nao diz" % k)
    for k, frase in sorted(_CAMPOS_DO_EM_USO.items()):
        if frase in par and k not in chaves:
            fora.append(u"a Politica diz «%s», e o arquivo nao o leva" % frase)
    if (u"renova a cada %s segundos" % _num_pt(
            v_cleaner.get("RENOVAR_EM_USO_S"))) not in par:
        fora.append(u"a Politica nao diz a renovacao do codigo (%s s)"
                    % v_cleaner.get("RENOVAR_EM_USO_S"))
    apaga = _referencias_no_fonte(
        _fonte_da_funcao(src_vigia, "encerrar_sinalizacao"), "apagar_em_uso")
    if apaga is not (u"apaga quando fecha normalmente" in par):
        fora.append(u"o vigia %s o arquivo na saida limpa"
                    % (u"apaga" if apaga else u"NAO apaga"))
    pasta = u"%%LOCALAPPDATA%%\\%s" % v_cleaner.get("MARCA_ECOSSISTEMA")
    if pasta not in politica:
        fora.append(u"a Politica nao diz a pasta %s" % pasta)
    return fora


_MARCA_DUAS_PORTAS = u"no vigia e no «Rodar agora»"
_MARCA_HISTORICO = u"A central de notificações do Windows guarda o histórico"


def _notificacao_divergente(src_vigia, src_batch, src_notify, src_todo,
                            frases, politica):
    par = _trecho(politica, u"Na central de notificações do Windows.",
                  u"desliga a do Windows")
    fora = []
    if not par:
        return [u"a Politica nao descreve as notificacoes"]
    duas = (_importa(src_vigia, "radai_notify")
            and _importa(src_batch, "radai_notify"))
    if duas is not (_MARCA_DUAS_PORTAS in par):
        fora.append(u"o toast %s sai nas duas portas, e a Politica %s"
                    % (u"" if duas else u"NAO", u"diz" if
                       _MARCA_DUAS_PORTAS in par else u"nao diz"))
    so_o_fim = (bool(frases) and all(
        f.startswith(u"Série …{0}") for k, f in frases.items()
        if not k.startswith(u"titulo"))
        and u"'…' + uid" in (src_todo or u""))
    if so_o_fim is not (u"só os oito últimos dígitos do UID" in par):
        fora.append(u"as notificacoes %s so o fim do UID"
                    % (u"levam" if so_o_fim else u"NAO levam"))
    if _MARCA_HISTORICO not in par:
        fora.append(u"a Politica nao declara o historico da central")
    env = u"RADAI_NOTIFICACAO" in _strings_do_fonte(src_notify)
    if env is not (u"RADAI_NOTIFICACAO=0" in politica):
        fora.append(u"a variavel que desliga o toast %s no codigo"
                    % (u"existe" if env else u"NAO existe"))
    return fora


def _idioma_divergente(src_lang, politica):
    rota = _rota_da_funcao(src_lang, "_gravar_idioma") == u"/api/idioma"
    grava = (_valores_do_modulo(src_lang).get("CHAVE_CONFIG") == u"IDIOMA"
             and _referencias_no_fonte(
                 _fonte_da_funcao(src_lang, "gravar_na_estacao"),
                 "CHAVE_CONFIG"))
    diz = (u"POST /api/idioma" in politica and u"IDIOMA" in politica)
    if (rota and grava) is not diz:
        return [u"a rota do idioma %s e grava %s; a Politica %s"
                % (u"existe" if rota else u"NAO existe",
                   u"IDIOMA" if grava else u"outra coisa",
                   u"a declara" if diz else u"nao a declara")]
    return []


_CHAVES_DA_CONCLUSAO = {"modo": u"o modo em que ela rodou",
                        "gravados": u"os conjuntos gravados",
                        "regioes": u"as regiões que a anatomia mostrou",
                        "plano_dispositivo": u"o dispositivo em que rodou",
                        "travamentos": u"as tarefas que travaram"}


def _chaves_da_funcao_comum(src_records):
    try:
        arv = ast.parse(src_records or u"")
    except SyntaxError:
        return set()
    for no in ast.walk(arv):
        if isinstance(no, ast.FunctionDef) and no.name == "campos_do_done":
            for r in ast.walk(no):
                if isinstance(r, ast.Return) and isinstance(r.value, ast.Dict):
                    return set(k.value for k in r.value.keys
                               if isinstance(k, ast.Constant)
                               and isinstance(k.value, str))
    return set()


def _chama_a_funcao_comum(no):
    return any(isinstance(c, ast.Call) and (
        (isinstance(c.func, ast.Attribute) and c.func.attr == "campos_do_done")
        or (isinstance(c.func, ast.Name) and c.func.id == "campos_do_done"))
        for c in ast.walk(no))


def _grava_pela_funcao_comum(src, dono, expr):
    if not isinstance(expr, ast.Name):
        return False
    params = set(a.arg for a in dono.args.args + dono.args.kwonlyargs)
    via_param = set()
    for no in ast.walk(dono):
        if not (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                and no.func.attr == "update" and no.args
                and isinstance(no.func.value, ast.Name)
                and no.func.value.id == expr.id):
            continue
        if _chama_a_funcao_comum(no.args[0]):
            return True
        via_param |= set(n.id for n in ast.walk(no.args[0])
                         if isinstance(n, ast.Name) and n.id in params)
    if not via_param:
        return False
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    for chamador in ast.walk(arv):
        if not isinstance(chamador, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for ch in ast.walk(chamador):
            if not (isinstance(ch, ast.Call) and (
                    (isinstance(ch.func, ast.Name) and ch.func.id == dono.name)
                    or (isinstance(ch.func, ast.Attribute)
                        and ch.func.attr == dono.name))):
                continue
            for kw in ch.keywords:
                if kw.arg in via_param and isinstance(kw.value, ast.Name):
                    for a in ast.walk(chamador):
                        if (isinstance(a, ast.Assign)
                                and any(isinstance(t, ast.Name)
                                        and t.id == kw.value.id
                                        for t in a.targets)
                                and _chama_a_funcao_comum(a.value)):
                            return True
    return False


def _conclusao_divergente(fontes, politica):
    chaves = set()
    comuns = _chaves_da_funcao_comum(fontes.get("records"))
    for _q, dono, expr in _escritas_de_marcador(fontes, "done"):
        chaves |= set(_chaves_gravadas(dono, expr))
        _mod = u"watcher" if _q.startswith(u"radai_watcher.") else u"batch"
        if comuns and _grava_pela_funcao_comum(fontes.get(_mod), dono, expr):
            chaves |= comuns
    return [u"o de conclusao %s `%s`, e a Politica %s «%s»" % (
                u"guarda" if k in chaves else u"NAO guarda", k,
                u"diz" if frase in politica else u"nao diz", frase)
            for k, frase in sorted(_CHAVES_DA_CONCLUSAO.items())
            if (k in chaves) is not (frase in politica)]


_MARCA_AVISO_NA_PORTA = u"com um aviso e um ponto na engrenagem"


def _versao_divergente(v_version, src_vigia, src_router, texto_conexao):
    fora = []
    url = str(v_version.get("URL_VERSOES") or u"")
    var = str(v_version.get("VARIAVEL_URL_VERSOES") or u"\x00")
    if not url.startswith(u"http"):
        fora.append(u"radai_version nao tem o endereco no codigo")
    if var not in texto_conexao:
        fora.append(u"a Politica nao nomeia a variavel %s" % var)
    no_config = bool(re.search(r"(?m)^URL_VERSOES=", src_vigia or u""))
    cita_chave = (u"chave URL_VERSOES" in texto_conexao
                  or u"URL_VERSOES vazia" in texto_conexao)
    if no_config is not cita_chave:
        fora.append(u"o endereco %s no config, e a Politica %s"
                    % (u"esta" if no_config else u"NAO esta",
                       u"cita a chave" if cita_chave else u"nao cita"))
    aviso = (u"Versão nova disponível" in (src_router or u"")
             and u"/api/versao" in (src_router or u""))
    if aviso is not (_MARCA_AVISO_NA_PORTA in texto_conexao):
        fora.append(u"a porta %s o aviso de versao nova"
                    % (u"mostra" if aviso else u"NAO mostra"))
    return fora


def _turno_divergente(src_batch, src_queue, termos):
    fora = []
    par = _trecho(termos, u"O Overnight Run", u"</ul>")
    folha = _fonte_da_funcao_js(src_batch, u"folhaOvernight")
    for rotulo in (u"Salvar e incluir na fila", u"Salvar e iniciar",
                   u"Iniciar sem salvar", u"Cancelar"):
        tem = (u"'%s'" % rotulo) in folha
        diz = (u"«%s»" % rotulo) in par
        if tem is not diz:
            fora.append(u"a folha do turno %s «%s», e os Termos %s"
                        % (u"tem" if tem else u"NAO tem", rotulo,
                           u"dizem" if diz else u"nao dizem"))
    return fora


def _fonte_da_funcao_js(src, nome):
    t = src or u""
    i = t.find(u"function %s(" % nome)
    if i < 0:
        return u""
    j = t.find(u"\nfunction ", i + 1)
    return t[i:(j if j >= 0 else len(t))]


_MARCAS_SEM_MOTOR_NO_VIGIA = ((u"Termos", u"O vigia não os roda."),
                              (u"Creditos", u"o vigia não os roda"))


def _comparacao_so_no_perso(src_batch, src_vigia):
    pede = _referencias_no_fonte(_fonte_da_funcao(src_batch,
                                                  "motores_da_serie"),
                                 "MODO_PERSO")
    try:
        arv = ast.parse(src_vigia or u"")
    except SyntaxError:
        return False
    grava = any(isinstance(n, ast.Call)
                and getattr(n.func, "attr", None) in ("nv", "cads", "moose",
                                                      "rodar_para_entrega")
                for n in ast.walk(arv))
    return pede and not grava


def _comparacao_divergente(so_no_perso, textos):
    return [u"%s: o vigia %s motor de comparacao, e o texto %s «%s»" % (
                nome, u"nao roda" if so_no_perso else u"RODA",
                u"diz" if marca in (txt or u"") else u"nao diz", marca)
            for nome, txt, marca in textos
            if (marca in (txt or u"")) is not so_no_perso]


def teste_o_que_a_v83_mudou_nos_documentos():
    secao(u"documentos 1.6: o que a v8.3 mudou, amarrado ao codigo")
    import radai_consent as CS
    import radai_credits as CR
    politica = _plano(CS.POLITICA)
    termos = _plano(CS.TERMOS)
    creditos = _plano(CR.pagina())
    pontos = dict((c, t + u" " + d) for (c, t, d) in CS.PONTOS)
    chaves = set(pontos)
    src = dict((n, ler(u"app/" + n)) for n in (
        "engine.py", "radai_watcher.py", "radai_batch.py", "radai_modes.py",
        "radai_sets.py", "radai_skin.py", "radai_breast.py",
        "radai_cleaner.py", "radai_notify.py", "radai_todo.py",
        "radai_languages.py", "radai_version.py", "radai_router.py",
        "radai_queue_state.py", "radai_output.py"))
    v = dict((n, _valores_do_modulo(s)) for n, s in src.items())
    fontes_app = {}
    for n in _componentes.nomes("app"):
        if n.endswith(u".py"):
            fontes_app[n] = ler(u"app/" + n)

    div = _modos_divergentes(v["radai_modes.py"], v["radai_watcher.py"],
                             termos, pontos.get(u"deteccao"))
    checar(u"os tres modos (FAST, AUTO, PERSONALIZADO) e o vigia sempre no "
           u"AUTO: o codigo e os Termos concordam", not div, u" | ".join(div))
    checar(u"  isca: o vigia no FAST, com os Termos de hoje: reprova",
           bool(_modos_divergentes(v["radai_modes.py"],
                                   dict(v["radai_watcher.py"],
                                        MODO_DO_VIGIA="fast"),
                                   termos, pontos.get(u"deteccao"))))
    checar(u"  isca: os Termos calam o vigia no AUTO: reprova",
           bool(_modos_divergentes(v["radai_modes.py"], v["radai_watcher.py"],
                                   termos.replace(_MARCA_VIGIA_AUTO, u""),
                                   pontos.get(u"deteccao"))))

    div = _fast_divergente(v["radai_sets.py"], v["engine.py"], termos)
    checar(u"o entregue do FAST: o que ele nao leva e a decimacao (0,2 mm, "
           u"1 cm², 1%) sao os do codigo", not div, u" | ".join(div))
    checar(u"  isca: a tolerancia da decimacao em 0,5 mm no codigo: reprova",
           bool(_fast_divergente(v["radai_sets.py"],
                                 dict(v["engine.py"], DECIMACAO_FAST_MM=0.5),
                                 termos)))
    checar(u"  isca: o FAST tira mais uma estrutura no codigo: reprova",
           bool(_fast_divergente(
               dict(v["radai_sets.py"], FORA_DO_OAR_FAST=frozenset(
                   ["pelvic_muscles", "bag_bowel", "stomach"])),
               v["engine.py"], termos)))
    checar(u"  isca: os Termos calam a Bag_Bowel_OAR_ai: reprova",
           bool(_fast_divergente(v["radai_sets.py"], v["engine.py"],
                                 termos.replace(u"Bag_Bowel_OAR_ai",
                                                u"X"))))
    checar(u"  isca: os Termos calam o Anus_ai fora do FAST: reprova",
           bool(_fast_divergente(v["radai_sets.py"], v["engine.py"],
                                 termos.replace(u"e o ânus ( Anus_ai )",
                                                u"X"))))
    checar(u"  isca: o FAST volta a levar o ânus, com os Termos de hoje: "
           u"reprova", bool(_fast_divergente(
               dict(v["radai_sets.py"], FORA_DO_OAR_FAST=frozenset(
                   ["bag_bowel_oar"])), v["engine.py"], termos)))

    div = _clip_divergente(v["engine.py"], termos, v["radai_watcher.py"])
    checar(u"o recorte por task: nenhum por ancora, as laterais pelo corpo "
           u"nas tasks do registro, com a margem e o limiar do motor, e o "
           u"recorte no corpo dito ao lado", not div, u" | ".join(div))
    _vcorpo = dict(v["radai_watcher.py"])
    _vcorpo["DEFAULTS"] = dict(_vcorpo.get("DEFAULTS") or {},
                               RECORTE_NO_CORPO="0")
    checar(u"  isca: o recorte no corpo desligado de fabrica, com o paragrafo "
           u"de hoje: reprova",
           bool(_clip_divergente(v["engine.py"], termos, _vcorpo)))
    checar(u"  isca: o paragrafo cala o recorte no corpo: reprova",
           bool(_clip_divergente(v["engine.py"], termos.replace(
               _MARCA_CLIP_CORPO, u"pelo X"), v["radai_watcher.py"])))
    _reg = dict(v["engine.py"].get("RECORTE_POR_TASK") or {})
    _br = dict(_reg.get("breasts") or {}, medido=True)
    checar(u"  isca: a breasts recortada pela ancora no codigo: reprova",
           bool(_clip_divergente(dict(v["engine.py"], RECORTE_POR_TASK=dict(
               _reg, breasts=_br)), termos)))
    _am = dict(_reg.get("abdominal_muscles") or {})
    _am["fast"] = {"medido": True, "ancora": "glandula"}
    checar(u"  isca: a ancora da abdominal_muscles de volta, so no FAST: "
           u"reprova", bool(_clip_divergente(dict(
               v["engine.py"], RECORTE_POR_TASK=dict(
                   _reg, abdominal_muscles=_am)), termos)))
    _tc = dict(_reg.get("trunk_cavities") or {}, lateral_pelo_corpo=False)
    checar(u"  isca: a cavidade do tronco sem o recorte lateral: reprova",
           bool(_clip_divergente(dict(v["engine.py"], RECORTE_POR_TASK=dict(
               _reg, trunk_cavities=_tc)), termos)))
    checar(u"  isca: outra margem do corpo no motor: reprova",
           bool(_clip_divergente(dict(v["engine.py"],
                                      MARGEM_DO_CORPO_MM=20.0), termos)))
    checar(u"  isca: outro limiar do corpo no motor: reprova",
           bool(_clip_divergente(dict(v["engine.py"],
                                      LIMIAR_DO_CORPO_HU=-300.0), termos)))
    checar(u"  isca: os Termos calam a frase do recorte: reprova",
           bool(_clip_divergente(v["engine.py"],
                                 termos.replace(_MARCA_CLIP, u""))))

    por_pedido = _ts_so_por_pedido(src["radai_batch.py"],
                                   src["radai_watcher.py"])
    textos = ((u"Termos", termos, _MARCA_TS_PEDIDO),
              (u"Termos (1.2)", termos, _MARCA_TS_TERMOS),
              (u"Creditos", creditos, _MARCA_TS_PEDIDO),
              (u"ponto deteccao", pontos.get(u"deteccao", u""),
               _MARCA_TS_PEDIDO))
    div = _ts_divergente(por_pedido, textos)
    checar(u"o TS cru so sai por pedido (medido: %s), e os documentos dizem"
           % por_pedido, not div, u" | ".join(div))
    _vig_ts = src["radai_watcher.py"] + (u"\n\ndef _isca_ts(sd, c):\n"
                                         u"    sd.totalsegmentator_cru(c)\n")
    checar(u"  isca: o vigia volta a gravar o TS cru, com os textos de hoje: "
           u"reprova", bool(_ts_divergente(
               _ts_so_por_pedido(src["radai_batch.py"], _vig_ts), textos)))
    _lote_ts = src["radai_batch.py"].replace(u"if ts_cru_pedido(s):",
                                             u"if True:")
    checar(u"  (a isca do lote achou o `if ts_cru_pedido(s):`)",
           _lote_ts != src["radai_batch.py"])
    checar(u"  isca: o lote grava o TS cru sem a chave: reprova",
           bool(_ts_divergente(_ts_so_por_pedido(_lote_ts,
                                                  src["radai_watcher.py"]),
                               textos)))
    checar(u"  isca: os Creditos calam o «quando ele e pedido»: reprova",
           bool(_ts_divergente(por_pedido, (
               (u"Creditos", creditos.replace(_MARCA_TS_PEDIDO, u""),
                _MARCA_TS_PEDIDO),))))

    docs = [(u"termos", termos), (u"politica", politica),
            (u"creditos", creditos), (u"NOTICE", u" ".join(ler("NOTICE").split())),
            (u"pontos", u" ".join(pontos.values()))]
    div = _obsoletas_divergentes(v["radai_watcher.py"],
                                 src["radai_watcher.py"], docs)
    checar(u"as chaves que sairam do config: os Termos as listam, e nenhum "
           u"documento as cita como viva", not div, u" | ".join(div))
    _vobs = dict(v["radai_watcher.py"])
    _vobs["CHAVES_OBSOLETAS"] = dict(_vobs.get("CHAVES_OBSOLETAS") or {},
                                     INCLUIR_XPTO=u"isca")
    checar(u"  isca: uma chave obsoleta nova no codigo: reprova",
           bool(_obsoletas_divergentes(_vobs, src["radai_watcher.py"], docs)))
    checar(u"  isca: os Creditos voltam a citar INCLUIR_NV: reprova",
           bool(_obsoletas_divergentes(
               v["radai_watcher.py"], src["radai_watcher.py"],
               docs + [(u"creditos", creditos + u" pela chave INCLUIR_NV")])))
    checar(u"  isca: a chave volta ao DEFAULT_CFG: reprova",
           bool(_obsoletas_divergentes(
               v["radai_watcher.py"],
               src["radai_watcher.py"] + u"\nENTREGAR_TS=1\n", docs)))

    div = _trava_divergente(v["radai_watcher.py"], src["engine.py"], termos)
    checar(u"o travamento: os tres numeros e as tres chaves sao os do codigo",
           not div, u" | ".join(div))
    _vtr = dict(v["radai_watcher.py"])
    _vtr["DEFAULTS"] = dict(_vtr.get("DEFAULTS") or {},
                            TRAVA_SEM_PULSO_MIN="20")
    checar(u"  isca: TRAVA_SEM_PULSO_MIN = 20 no codigo: reprova",
           bool(_trava_divergente(_vtr, src["engine.py"], termos)))
    checar(u"  isca: o motor sem TaskTravada: reprova",
           bool(_trava_divergente(v["radai_watcher.py"],
                                  src["engine.py"].replace(
                                      u"class TaskTravada(",
                                      u"class _SemTrava("), termos)))

    div = _regras_divergentes(v["engine.py"], src["engine.py"], termos, chaves)
    checar(u"as regras R1 a R4: a secao 1.3 e o ponto `remove` existem se, e "
           u"so se, o motor as roda, com os numeros dele", not div,
           u" | ".join(div))
    checar(u"  isca: a poda com 20 cm³ no codigo: reprova",
           bool(_regras_divergentes(dict(v["engine.py"],
                                         VOLUME_DA_PODA_CM3=20.0),
                                    src["engine.py"], termos, chaves)))
    checar(u"  isca: o motor sem as regras, com os documentos de hoje: "
           u"reprova", bool(_regras_divergentes(
               v["engine.py"], src["engine.py"].replace(
                   u"def aplicar_regras_de_gravacao(",
                   u"def _sem_regras("), termos, chaves)))
    checar(u"  isca: o ponto `remove` some, com as regras de hoje: reprova",
           bool(_regras_divergentes(v["engine.py"], src["engine.py"], termos,
                                    chaves - {u"remove"})))
    _sem_r3 = src["engine.py"].replace(
        u"limpar_fora_do_corpo(masks, _img_densidade",
        u"(lambda *a, **k: None)(masks, _img_densidade")
    checar(u"  isca: a R3 some dos arquivos ao lado, com a secao de hoje: "
           u"reprova", _sem_r3 != src["engine.py"] and bool(
               _regras_divergentes(v["engine.py"], _sem_r3, termos, chaves)))
    div = _pulmao_pela_uniao_divergente(v["engine.py"], termos)
    checar(u"a R1 e a R2 julgam o pulmao pela uniao dos lobos: o codigo e a "
           u"secao 1.3", not div, u" | ".join(div))
    checar(u"  isca: o motor volta a julgar o lobo, com a secao de hoje: "
           u"reprova", bool(_pulmao_pela_uniao_divergente(
               dict(v["engine.py"], ORGAOS_POR_PARTES=()), termos)))
    checar(u"  isca: a secao volta a dizer «pulmão e lobos»: reprova",
           bool(_pulmao_pela_uniao_divergente(v["engine.py"], termos.replace(
               u"(o pulmão de cada lado,", u"(pulmão e lobos,", 1))))
    div = _pescoco_divergente(v["engine.py"], termos)
    checar(u"o marco do pescoco: o volume de cada vertebra e o do codigo",
           not div, u" | ".join(div))
    checar(u"  isca: 7 cm³ no codigo: reprova",
           bool(_pescoco_divergente(dict(
               v["engine.py"], VOLUME_MINIMO_VERTEBRA_CERVICAL_CM3=7.0),
               termos)))

    div = _pelve_divergente(v["engine.py"], termos)
    checar(u"Muscles_ai e Bone_Pelvic_ai so com a pelve: o codigo e os Termos",
           not div, u" | ".join(div))
    checar(u"  isca: o codigo deixa de prender o composto a pelve: reprova",
           bool(_pelve_divergente(dict(v["engine.py"],
                                       REGIAO_EXIGIDA_NO_OAR={}), termos)))

    v["radai_skin.py"] = _valores_da_pele(src["radai_skin.py"])
    div = _pele_e_parede_divergentes(v["radai_skin.py"], termos)
    checar(u"a pele (%s mm, o corpo com as estruturas, o fechamento de %s mm "
           u"a ate %s mm) e a parede (cavidade, %s mm, %s mm, %s das costelas) "
           u"sao as do codigo" % (
               _num_pt(v["radai_skin.py"].get("ESPESSURA_PELE_MM")),
               _num_pt(v["radai_skin.py"].get("FECHAMENTO_ANTERIOR_MM")),
               _num_pt(v["radai_skin.py"].get("ALCANCE_DO_FECHAMENTO_MM")),
               _num_pt(v["radai_skin.py"].get("MARGEM_PAREDE_MM")),
               _num_pt(v["radai_skin.py"].get("SUAVIZACAO_PAREDE_MM")),
               v["radai_skin.py"].get("COBERTURA_MINIMA_DAS_COSTELAS")),
           not div, u" | ".join(div))
    checar(u"  isca: a parede cobrindo 80% das costelas no codigo: reprova",
           bool(_pele_e_parede_divergentes(dict(
               v["radai_skin.py"], COBERTURA_MINIMA_DAS_COSTELAS=0.8),
               termos)))
    checar(u"  isca: o fechamento da pele em 8 mm no codigo: reprova",
           bool(_pele_e_parede_divergentes(dict(
               v["radai_skin.py"], FECHAMENTO_ANTERIOR_MM=8.0), termos)))
    checar(u"  isca: o alcance do fechamento sem a erosao da mesa (5 mm): "
           u"reprova", bool(_pele_e_parede_divergentes(dict(
               v["radai_skin.py"], ALCANCE_DO_FECHAMENTO_MM=5.0), termos)))
    checar(u"  isca: os Termos de antes (a pele so casca, sem o corpo): "
           u"reprova", bool(_pele_e_parede_divergentes(
               v["radai_skin.py"], termos.replace(
                   u"um corpo que leva todas as estruturas já segmentadas",
                   u"X"))))
    checar(u"  isca: o codigo sem a cobertura, com os Termos de hoje: reprova",
           bool(_pele_e_parede_divergentes(dict(
               (k, x) for k, x in v["radai_skin.py"].items()
               if k != "COBERTURA_MINIMA_DAS_COSTELAS"), termos)))
    checar(u"  isca: a pele de volta a 6 mm no codigo: reprova",
           bool(_pele_e_parede_divergentes(dict(v["radai_skin.py"],
                                                ESPESSURA_PELE_MM=6.0),
                                           termos)))
    checar(u"  isca: a parede sem a cavidade na base: reprova",
           bool(_pele_e_parede_divergentes(dict(v["radai_skin.py"],
                                                BASE_DA_PAREDE=()), termos)))
    checar(u"  isca: a suavizacao da parede em 3 mm: reprova",
           bool(_pele_e_parede_divergentes(dict(v["radai_skin.py"],
                                                SUAVIZACAO_PAREDE_MM=3.0),
                                           termos)))

    div = _mama_de_restricao_divergente(_fatos_da_mama(
        src["radai_breast.py"], v["radai_sets.py"], v["engine.py"]),
        termos)
    checar(u"a mama de restricao e o que os Termos dizem dela (a v8.5 a "
           u"tirou): o codigo e os Termos concordam", not div,
           u" | ".join(div))

    div = _reto_divergente(v["radai_sets.py"], termos)
    checar(u"o reto sai Rectum_ai se, e so se, o sufixo da derivada foi "
           u"aposentado", not div, u" | ".join(div))
    checar(u"  isca: o sufixo da derivada de volta: reprova",
           bool(_reto_divergente(dict(v["radai_sets.py"],
                                      SUFIXOS_APOSENTADOS=("_v3D",)), termos)))

    _existe = lambda a: os.path.isfile(_componentes.fonte("app/" + a))
    docs_lidos = [(u"termos", termos), (u"politica", politica),
                  (u"creditos", creditos), (u"pontos",
                                           u" ".join(pontos.values()))]
    div = _apagados_citados(_existe, docs_lidos)
    checar(u"nenhum documento fala do calibrador nem do compilador, que "
           u"foram apagados", not div, u" | ".join(div))
    checar(u"  isca: a Politica volta a citar o relatorio do Compilador: "
           u"reprova", bool(_apagados_citados(
               _existe, docs_lidos + [(u"politica", politica
                                       + u" o relatório do Compilador")])))

    treino, feedback = _saidas_do_ciclo(fontes_app)
    div = _ciclo_divergente(treino, feedback, politica, chaves, termos)
    checar(u"o acervo de treino e o e-mail de feedback (medido: treino=%s, "
           u"e-mail=%s) sao declarados se, e so se, existem"
           % (treino, feedback), not div, u" | ".join(div))
    _fa = dict(fontes_app)
    _fa["radai_isca.py"] = u"import radai_training\n"
    checar(u"  isca: um modulo volta a usar o acervo de treino: reprova",
           bool(_ciclo_divergente(_saidas_do_ciclo(_fa)[0], feedback,
                                  politica, chaves)))
    _fa["radai_isca.py"] = u"X = 'mailto:alguem@exemplo.org'\n"
    checar(u"  isca: uma tela volta a abrir e-mail: reprova",
           bool(_ciclo_divergente(treino, _saidas_do_ciclo(_fa)[1],
                                  politica, chaves)))
    checar(u"  isca: o ponto `acervo` volta sem o acervo de treino: reprova",
           bool(_ciclo_divergente(treino, feedback, politica,
                                  chaves | {u"acervo"})))
    checar(u"  isca: os Termos calam que esta versao nao grava para treino: "
           u"reprova", bool(_ciclo_divergente(treino, feedback, politica,
                                             chaves, termos.replace(
                                                 _MARCA_TREINO_TERMOS, u""))))

    rota, botao = _baixar_modelo(fontes_app)
    div = _baixar_divergente(rota, botao, politica)
    checar(u"baixar peso de modelo (rota=%s, botao=%s): a Politica diz o que "
           u"existe" % (rota, botao), not div, u" | ".join(div))
    checar(u"  isca: uma tela volta a ter o botao: reprova",
           bool(_baixar_divergente(rota, True, politica)))
    checar(u"  isca: a rota volta: reprova",
           bool(_baixar_divergente(True, botao, politica)))

    import radai_cleaner as RC
    restos = [n for n in ("classificar", "otimizar", "restaurar",
                          "parar_servico", "iniciar_servico", "liberar")
              if hasattr(RC, n)]
    checar(u"o «Otimizar» e a pausa de servicos sairam do codigo",
           not restos, u", ".join(restos))
    div = _otimizar_descrito({u"Termos": termos, u"Politica": politica})
    checar(u"os documentos em vigor nao descrevem o «Otimizar», o "
           u"otimizar.json nem a pausa de servicos do turno, que sairam",
           not div, u" | ".join(div))
    checar(u"  isca: um documento que volta a descrever o Restaurar: reprova",
           bool(_otimizar_descrito({u"Termos": u"x O «Restaurar» reabre y"})))

    try:
        cont = RC.conteudo_em_uso(8777, True, pid_app=os.getpid(), procs=[],
                                  saida_netstat=u"")
        chaves_uso = set(cont)
    except Exception as e:
        chaves_uso = set()
        checar(u"radai_cleaner.conteudo_em_uso roda", False,
               u"%s: %s" % (type(e).__name__, str(e)[:80]))
    div = _em_uso_divergente(chaves_uso, v["radai_cleaner.py"],
                             src["radai_watcher.py"], politica)
    checar(u"o em_uso.json: o que ele leva (executado), a renovacao e a saida "
           u"limpa sao o que a Politica diz", not div, u" | ".join(div))
    checar(u"  isca: um campo a mais no arquivo: reprova",
           bool(_em_uso_divergente(chaves_uso | {"paciente"},
                                   v["radai_cleaner.py"],
                                   src["radai_watcher.py"], politica)))
    checar(u"  isca: a renovacao a cada 120 s: reprova",
           bool(_em_uso_divergente(chaves_uso, dict(v["radai_cleaner.py"],
                                                    RENOVAR_EM_USO_S=120),
                                   src["radai_watcher.py"], politica)))
    import radai_notify as RN
    frases = dict(getattr(RN, "FRASES", {}) or {})
    div = _notificacao_divergente(src["radai_watcher.py"], src["radai_batch.py"],
                                  src["radai_notify.py"], src["radai_todo.py"],
                                  frases, politica)
    checar(u"as notificacoes: as duas portas, so o fim do UID, o historico da "
           u"central e a variavel que desliga", not div, u" | ".join(div))
    checar(u"  isca: o «Rodar agora» sem o toast: reprova",
           bool(_notificacao_divergente(
               src["radai_watcher.py"], u"", src["radai_notify.py"],
               src["radai_todo.py"], frases, politica)))
    checar(u"  isca: uma frase do toast que leva outra coisa: reprova",
           bool(_notificacao_divergente(
               src["radai_watcher.py"], src["radai_batch.py"],
               src["radai_notify.py"], src["radai_todo.py"],
               dict(frases, ok=u"Paciente {0}: pronta"), politica)))
    checar(u"  isca: a Politica cala o historico: reprova",
           bool(_notificacao_divergente(
               src["radai_watcher.py"], src["radai_batch.py"],
               src["radai_notify.py"], src["radai_todo.py"], frases,
               politica.replace(_MARCA_HISTORICO, u""))))

    div = _idioma_divergente(src["radai_languages.py"], politica)
    checar(u"o idioma: POST /api/idioma grava IDIOMA, e a Politica diz",
           not div, u" | ".join(div))
    checar(u"  isca: a rota sai: reprova",
           bool(_idioma_divergente(src["radai_languages.py"].replace(
               u'@app.post("/api/idioma")', u'@app.post("/api/outra")'),
               politica)))

    fontes_m = {"watcher": src["radai_watcher.py"],
                "batch": src["radai_batch.py"],
                "records": fontes_app.get("radai_records.py") or u""}
    div = _conclusao_divergente(fontes_m, politica)
    checar(u"o de conclusao: o modo, os conjuntos, as regioes, o dispositivo "
           u"e as travas sao ditos se, e so se, o codigo os grava", not div,
           u" | ".join(div))
    _sem_comum = dict(fontes_m)
    _sem_comum["watcher"] = _sem_comum["watcher"].replace(
        u"done.update(_rg_done.campos_do_done(", u"done.update(dict(")
    _sem_comum["batch"] = _sem_comum["batch"].replace(
        u"_campos_done = _rg_done.campos_do_done(", u"_campos_done = dict(")
    checar(u"  isca: as duas portas sem a funcao comum dos campos: reprova",
           _sem_comum != fontes_m
           and bool(_conclusao_divergente(_sem_comum, politica)))
    _sem_trava = dict(fontes_m)
    _sem_trava["records"] = _sem_trava["records"].replace(
        u'        "travamentos": [\n', u'        "_travamentos": [\n', 1)
    checar(u"  isca: a funcao comum sem as travas: reprova",
           _sem_trava != fontes_m
           and bool(_conclusao_divergente(_sem_trava, politica)))
    _min = (u"def _marcar_done(s):\n"
            u"    done = {\"pid\": 1, \"uid\": 2}\n"
            u"    marcador(\"done\").write_text(json.dumps(done))\n")
    checar(u"  isca: um escritor sem os campos novos, com a Politica de "
           u"hoje: reprova", bool(_conclusao_divergente({"batch": _min},
                                                         politica)))
    checar(u"  isca: a Politica cala as travas: reprova",
           bool(_conclusao_divergente(fontes_m, politica.replace(
               u"as tarefas que travaram", u""))))

    m = re.search(r'(?s)<ul id="conexoes-automaticas">(.*?)</ul>', CS.POLITICA)
    conexao = _plano(m.group(1)) if m else u""
    div = _versao_divergente(v["radai_version.py"], src["radai_watcher.py"],
                             src["radai_router.py"], conexao)
    checar(u"a consulta de versao: o endereco no codigo, a variavel que o "
           u"troca e o aviso na porta", not div, u" | ".join(div))
    checar(u"  isca: a chave volta ao DEFAULT_CFG: reprova",
           bool(_versao_divergente(v["radai_version.py"],
                                   src["radai_watcher.py"]
                                   + u"\nURL_VERSOES=\n",
                                   src["radai_router.py"], conexao)))
    checar(u"  isca: a porta sem o aviso: reprova",
           bool(_versao_divergente(v["radai_version.py"],
                                   src["radai_watcher.py"], u"", conexao)))

    div = _turno_divergente(src["radai_batch.py"], src["radai_queue_state.py"],
                            termos)
    checar(u"o Overnight Run: os botoes de incluir e cancelar, sem os antigos "
           u"atalhos de iniciar, sao os do codigo", not div, u" | ".join(div))
    checar(u"  isca: a folha volta a ter «Iniciar sem salvar»: reprova",
           bool(_turno_divergente(src["radai_batch.py"].replace(
               u"  cancelar: 'Cancelar',",
               u"  cancelar: 'Cancelar', sem: 'Iniciar sem salvar',"),
               src["radai_queue_state.py"], termos)))
    checar(u"  isca: os Termos de antes («Iniciar sem salvar»): reprova",
           bool(_turno_divergente(src["radai_batch.py"],
                                  src["radai_queue_state.py"],
                                  termos + u" «Iniciar sem salvar»")))

    so_perso = _comparacao_so_no_perso(src["radai_batch.py"],
                                       src["radai_watcher.py"])
    textos_m = [(n, {u"Termos": termos, u"Creditos": creditos}[n], m)
                for n, m in _MARCAS_SEM_MOTOR_NO_VIGIA]
    div = _comparacao_divergente(so_perso, textos_m)
    checar(u"os motores de comparacao so no PERSONALIZADO (medido: %s), e o "
           u"vigia nao os roda" % so_perso, not div, u" | ".join(div))
    checar(u"  isca: o vigia volta a gravar o NV, com os textos de hoje: "
           u"reprova", bool(_comparacao_divergente(
               _comparacao_so_no_perso(src["radai_batch.py"],
                                       src["radai_watcher.py"]
                                       + u"\n\ndef _isca(sd, x):\n"
                                         u"    sd.nv(x)\n"), textos_m)))
    checar(u"  isca: os Creditos calam que o vigia nao os roda: reprova",
           bool(_comparacao_divergente(so_perso, [
               (u"Creditos", creditos.replace(u"o vigia não os roda", u""),
                u"o vigia não os roda")])))



_MARCA_NAO_E_TETO = (u"não são o teto da diferença entre os dois "
                     u"entregues")
_PARAMETROS_DA_MEDIDA = (("tol_mm", "DECIMACAO_FAST_MM"),
                         ("min_pontos", "MIN_PONTOS_DECIMADO"),
                         ("area_min_mm2", "AREA_MINIMA_DECIMADA_MM2"),
                         ("perda_max", "PERDA_MAXIMA_DECIMACAO"))


def _medida_fast_divergente(v_engine, termos):
    med = v_engine.get("MEDIDA_DO_FAST_CONTRA_O_AUTO") or {}
    if not med:
        return [u"o motor nao tem MEDIDA_DO_FAST_CONTRA_O_AUTO, e os Termos "
                u"citam a medida"] if _MARCA_NAO_E_TETO in termos else []
    fora = []
    dec = med.get("decimacao") or {}
    for k_med, k_motor in _PARAMETROS_DA_MEDIDA:
        if dec.get(k_med) != v_engine.get(k_motor):
            fora.append(u"a medida do FAST e de %s=%s, e o motor usa %s=%s: "
                        u"remeça, e troque os numeros do registro e dos Termos"
                        % (k_med, dec.get(k_med), k_motor,
                           v_engine.get(k_motor)))
    par = _trecho(termos, u"O entregue do FAST",
                  u"Não há conjunto completo ao lado dele")
    for frase in (_MARCA_NAO_E_TETO,
                  u"TC de tórax de teste, de %s mm" % _num_pt(
                      med.get("espessura_mm")),
                  u"DSC de %s ou mais por estrutura" % _num_pt(
                      med.get("dsc_min")),
                  u"a maior diferença de volume foi de %s%%" % _num_pt(
                      med.get("volume_dif_max_pct")),
                  u"%s" % (med.get("estrutura_pior") or u"\x00")):
        if frase not in par:
            fora.append(u"o paragrafo do FAST nao diz «%s»" % frase)
    return fora


_MARCA_SEM_MODO_AUTO = (u"Uma série pedida sem modo e sem lista de tarefas "
                        u"— por uma página de versão anterior, por exemplo — "
                        u"roda como AUTO")
_MARCA_SEM_MODO_LISTA = (u"a que chega sem modo e com uma lista de tarefas, "
                         u"de um roteiro, roda a lista, e nela toda tarefa é "
                         u"obrigatória")


def _quem_decide(src_batch):
    ns = {}
    try:
        for nome in ("tela_declarou", "quem_decide_as_tasks"):
            fonte = _fonte_da_funcao(src_batch, nome)
            if not fonte:
                return None
            exec(compile(fonte, u"<%s>" % nome, "exec"), ns)
        return ns["quem_decide_as_tasks"]
    except Exception:
        return None


def _lista_obrigatoria_no_lote(src_batch):
    try:
        arv = ast.parse(src_batch or u"")
    except SyntaxError:
        return False
    pela_lista = any(
        isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_obrig"
                for t in n.targets)
        and isinstance(n.value, ast.IfExp)
        and any(isinstance(c, ast.Constant) and c.value == "lista"
                for c in ast.walk(n.value.test))
        for n in ast.walk(arv))
    passa = any(isinstance(n, ast.keyword) and n.arg == "obrigatorias"
                and isinstance(n.value, ast.Name) and n.value.id == "_obrig"
                for n in ast.walk(arv))
    return pela_lista and passa


def _sem_modo_divergente(quem, lista_obrig, termos):
    fora = []
    try:
        sem_nada = quem([], {})
        com_lista = quem(["total_v3"], {})
        com_modo = quem(["total_v3"], {"modo": "perso"})
    except Exception as e:
        return [u"quem_decide_as_tasks levantou (%s)" % type(e).__name__]
    auto = sem_nada != "lista"
    if auto is not (_MARCA_SEM_MODO_AUTO in termos):
        fora.append(u"sem modo e sem lista a serie %s pelo modo, e os Termos "
                    u"%s" % (u"vai" if auto else u"NAO vai",
                             u"dizem AUTO" if _MARCA_SEM_MODO_AUTO in termos
                             else u"nao dizem"))
    lista = (com_lista == "lista" and com_modo != "lista" and lista_obrig)
    if lista is not (_MARCA_SEM_MODO_LISTA in termos):
        fora.append(u"a serie sem modo com lista %s a lista (obrigatoria), e "
                    u"os Termos %s" % (u"roda" if lista else u"NAO roda",
                                       u"dizem" if _MARCA_SEM_MODO_LISTA
                                       in termos else u"nao dizem"))
    return fora


_MARCA_TASKS_SO_VIGIA = u"continua sendo lida, e só pelo vigia"
_MARCA_AUTO_NAO_LE = u"O AUTO do «Rodar agora» não lê essa lista"


def _tasks_do_config_so_no_vigia(src_vigia, src_batch):
    vigia = _referencias_no_fonte(src_vigia, "tasks_do_config_no_vigia")
    lote = (_referencias_no_fonte(src_batch, "tasks_do_config_no_vigia")
            or _referencias_no_fonte(
                _fonte_da_funcao(src_batch, "tasks_depois_da_base"), "TASKS"))
    return vigia and not lote


def _tasks_so_no_vigia_divergente(so_vigia, termos):
    fora = []
    for marca in (_MARCA_TASKS_SO_VIGIA, _MARCA_AUTO_NAO_LE):
        if (marca in termos) is not so_vigia:
            fora.append(u"o TASKS do config %s so pelo vigia, e os Termos "
                        u"%s «%s»" % (u"e lido" if so_vigia else u"NAO e lido",
                                      u"dizem" if marca in termos
                                      else u"nao dizem", marca))
    return fora


_MARCA_OBRIG_VIGIA = u"no vigia, a escrita no TASKS do arquivo de configuração"
_MARCA_OBRIG_LOTE = u"no «Rodar agora», toda tarefa da lista de um roteiro"


def _vigia_passa_obrigatorias(src_vigia):
    try:
        arv = ast.parse(src_vigia or u"")
    except SyntaxError:
        return False
    return any(isinstance(n, ast.keyword) and n.arg == "obrigatorias"
               and isinstance(n.value, ast.Name)
               for n in ast.walk(arv))


def _obrigatorias_divergente(vigia, lote, termos):
    par = _trecho(termos, u"Quando uma tarefa trava.", u"TIMEOUT_TASK_H")
    fora = []
    for tem, marca, quem in ((vigia, _MARCA_OBRIG_VIGIA, u"o vigia"),
                             (lote, _MARCA_OBRIG_LOTE, u"o lote")):
        if tem is not (marca in par):
            fora.append(u"%s %s tarefa obrigatoria alem da base, e o "
                        u"paragrafo da trava %s «%s»"
                        % (quem, u"tem" if tem else u"NAO tem",
                           u"diz" if marca in par else u"nao diz", marca))
    return fora


_MARCA_HNL_LIGA = (u"os níveis cervicais passam a rodar no AUTO e a entrar "
                   u"no conjunto completo quando o pescoço é detectado")


def _hnl_obsoleta_divergente(v_vigia, termos):
    nota = str((v_vigia.get("CHAVES_OBSOLETAS") or {}).get(
        "INCLUIR_HNLNL") or u"")
    rodam = u"rodam no AUTO" in nota
    par = _trecho(termos, _INICIO_OBSOLETAS, _FIM_OBSOLETAS)
    if rodam is not (_MARCA_HNL_LIGA in par):
        return [u"a chave INCLUIR_HNLNL saiu e os niveis %s no AUTO, e o "
                u"paragrafo das obsoletas %s" % (
                    u"rodam" if rodam else u"NAO rodam",
                    u"diz" if _MARCA_HNL_LIGA in par else u"nao diz")]
    return []


_MARCA_R3_SO_LOG = (u"a dos arquivos de plugin e de comparação vai só ao "
                    u"log")


def _r3_ao_lado_descartada(src_engine):
    corpo = _fonte_da_funcao(src_engine, "build_rtstruct")
    try:
        arv = ast.parse(corpo or u"")
    except SyntaxError:
        return None
    pais = {}
    for no in ast.walk(arv):
        for f in ast.iter_child_nodes(no):
            pais[f] = no
    chamadas = [n for n in ast.walk(arv) if isinstance(n, ast.Call)
                and (getattr(n.func, "id", None) == "limpar_fora_do_corpo"
                     or getattr(n.func, "attr", None)
                     == "limpar_fora_do_corpo")]
    if not chamadas:
        return None
    return all(isinstance(pais.get(c), ast.Expr) for c in chamadas)


def _r3_log_divergente(descartada, termos):
    par = _trecho(termos, *_SECAO_REGRAS)
    diz = _MARCA_R3_SO_LOG in par
    if bool(descartada) is not diz:
        return [u"a R3 dos arquivos ao lado %s ao registro do caso, e a secao "
                u"1.3 %s que vai so ao log"
                % (u"NAO chega" if descartada else u"pode chegar",
                   u"diz" if diz else u"nao diz")]
    return []


_MARCA_NAV_AVISO = (u"os oito últimos dígitos do UID e a hora do aviso, que "
                    u"nada apaga")
_MARCA_NAV_LOTE = u"guarda a pasta varrida no «Rodar agora»"
_MARCA_NAV_VER = (u"o caminho da pasta dela e o UID inteiro, que essa tela "
                  u"apaga assim que os lê")


def _fatos_do_navegador(src_todo, src_queue, src_batch, src_view):
    t, b, w = src_todo or u"", src_batch or u"", src_view or u""
    uid8 = u"uid[-8:]" in _fonte_da_funcao(src_queue, "para_tela")
    todos = u"\n".join((t, b, w))
    return {"aviso": (u"'radai_aviso_' + uid" in t
                      and u"localStorage.setItem(k" in t and uid8),
            "nada_apaga": not re.search(
                r"removeItem\([^)]*radai_aviso", todos),
            "lote": u"sessionStorage.setItem('radai_lote_pasta'" in b,
            "ver": (u"sessionStorage.setItem('radai_ver_pasta'" in b
                    and u"sessionStorage.setItem('radai_ver_uid'" in b),
            "ver_apaga": (u"sessionStorage.removeItem('radai_ver_pasta')" in w
                          and u"sessionStorage.removeItem('radai_ver_uid')"
                          in w)}


def _navegador_divergente(f, politica):
    fora = []
    for tem, marca in ((f["aviso"] and f["nada_apaga"], _MARCA_NAV_AVISO),
                       (f["lote"], _MARCA_NAV_LOTE),
                       (f["ver"] and f["ver_apaga"], _MARCA_NAV_VER)):
        if tem is not (marca in politica):
            fora.append(u"o navegador %s, e a Politica %s «%s»"
                        % (u"guarda isto" if tem else u"NAO guarda isto assim",
                           u"diz" if marca in politica else u"nao diz", marca))
    return fora


_MARCA_FAST_APAGA = (u"Refazer no FAST uma série que já saiu no AUTO ou no "
                     u"PERSONALIZADO apaga o entregue e o completo dela")


def _fast_regrava_divergente(v_sets, substitui, politica):
    fast = any(isinstance(c, dict) and c.get("modo") == "fast"
               for c in (v_sets.get("SAIDAS_DE_MODO") or ()))
    tem = fast and bool(substitui)
    if tem is not (_MARCA_FAST_APAGA in politica):
        return [u"refazer no FAST %s a entrega do AUTO, e a Politica %s"
                % (u"apaga" if tem else u"NAO apaga",
                   u"diz" if _MARCA_FAST_APAGA in politica else u"nao diz")]
    return []


_MARCA_RETO_DERIVADO = u"«derivada por marco anatômico»"


def _reto_derivado_divergente(src_engine, termos):
    grava = any(u"derivada por marco anatomico" in s
                for s in _strings_do_fonte(src_engine))
    if grava is not (_MARCA_RETO_DERIVADO in termos):
        return [u"o motor %s a procedencia de derivada no reto, e os Termos "
                u"%s" % (u"grava" if grava else u"NAO grava",
                         u"a citam" if _MARCA_RETO_DERIVADO in termos
                         else u"nao a citam")]
    return []


def _titulo_bolus_divergente(src_bolus, termos):
    molde = "linha_do_ato_molde" in _nomes_de_topo(src_bolus, "def")
    um = u"4.2 · O 3D Printed Bolus exporta um arquivo" in termos
    varios = u"4.2 · O 3D Printed Bolus exporta arquivos" in termos
    if molde and (um or not varios):
        return [u"o bolus exporta tambem o molde, e o titulo da 4.2 diz um "
                u"arquivo so"]
    if not molde and varios:
        return [u"o bolus nao exporta molde, e o titulo da 4.2 diz arquivos"]
    return []


_RE_BAIXA_PESOS_TS = re.compile(
    u"Os pesos do TotalSegmentator, desde ([^,]+),")


def _desde_divergente(prep_baixa, docs):
    fora = []
    for nome, txt in docs:
        achadas = _RE_BAIXA_PESOS_TS.findall(txt or u"")
        if prep_baixa and not achadas:
            fora.append(u"%s nao diz desde quando o preparador baixa os pesos"
                        % nome)
        for a in achadas:
            if not prep_baixa:
                fora.append(u"%s diz que o preparador baixa os pesos, e ele "
                            u"nao tem baixar_pesos_ts" % nome)
            elif a.strip() != u"a v8.2":
                fora.append(u"%s diz «desde %s», e o preparador baixa desde "
                            u"a v8.2" % (nome, a.strip()))
    return fora


_CAMPOS_DO_ACERVO = {"pid": u"o PatientID", "date": u"a data do exame",
                     "uid": u"o UID inteiro",
                     "pasta": u"o caminho da pasta de cada uma",
                     "rs": u"o nome do RTSTRUCT", "maquina": u"a máquina"}


def _chaves_do_acervo(src_archive):
    try:
        arv = ast.parse(_fonte_da_funcao(src_archive, "registrar_serie")
                        or u"")
    except SyntaxError:
        return set()
    for n in ast.walk(arv):
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
                and any(isinstance(t, ast.Name) and t.id == "reg"
                        for t in n.targets)):
            return set(k.value for k in n.value.keys
                       if isinstance(k, ast.Constant))
    return set()


def _acervo_divergente(chaves, politica):
    par = _trecho(politica, u"o índice das séries contornadas",
                  u"é dele que sai")
    if not par:
        return [u"a Politica nao descreve o indice do acervo"]
    return [u"o acervo.jsonl %s `%s`, e a Politica %s «%s»"
            % (u"grava" if k in chaves else u"NAO grava", k,
               u"diz" if frase in par else u"nao diz", frase)
            for k, frase in sorted(_CAMPOS_DO_ACERVO.items())
            if (k in chaves) is not (frase in par)]


def teste_os_consertos_da_revisao_da_16():
    secao(u"documentos 1.6: os consertos da revisao adversarial, amarrados "
          u"ao codigo")
    import radai_consent as CS
    import radai_credits as CR
    politica = _plano(CS.POLITICA)
    termos = _plano(CS.TERMOS)
    creditos = _plano(CR.pagina())
    src = dict((n, ler(u"app/" + n)) for n in (
        "engine.py", "radai_watcher.py", "radai_batch.py", "radai_sets.py",
        "radai_cleaner.py", "radai_todo.py", "radai_queue_state.py",
        "radai_view.py", "radai_archive.py", "radai_bolus.py"))
    v = dict((n, _valores_do_modulo(s)) for n, s in src.items())

    div = _medida_fast_divergente(v["engine.py"], termos)
    checar(u"o FAST contra o AUTO: os Termos dizem que as guardas nao sao o "
           u"teto, e a diferenca medida e a do registro do motor", not div,
           u" | ".join(div))
    checar(u"  isca: a tolerancia da decimacao muda no motor, com o registro "
           u"de hoje: reprova (a medida e de outro FAST)",
           bool(_medida_fast_divergente(dict(v["engine.py"],
                                             DECIMACAO_FAST_MM=0.3), termos)))
    _mf = dict(v["engine.py"].get("MEDIDA_DO_FAST_CONTRA_O_AUTO") or {},
               dsc_min=0.95)
    checar(u"  isca: outro DSC no registro: reprova",
           bool(_medida_fast_divergente(dict(
               v["engine.py"], MEDIDA_DO_FAST_CONTRA_O_AUTO=_mf), termos)))
    checar(u"  isca: os Termos calam que as guardas nao sao o teto: reprova",
           bool(_medida_fast_divergente(v["engine.py"], termos.replace(
               _MARCA_NAO_E_TETO, u""))))

    quem = _quem_decide(src["radai_batch.py"])
    obrig = _lista_obrigatoria_no_lote(src["radai_batch.py"])
    checar(u"  (executei quem_decide_as_tasks do fonte do lote: %s; a lista "
           u"do chamador obrigatoria: %s)" % (quem is not None, obrig),
           quem is not None and obrig)
    div = _sem_modo_divergente(quem or (lambda *a: None), obrig, termos)
    checar(u"a serie sem modo: sem lista roda como AUTO, com lista roda a "
           u"lista (obrigatoria) — o codigo e os Termos", not div,
           u" | ".join(div))
    checar(u"  isca: a lista do chamador perde para o AUTO, com os Termos de "
           u"hoje: reprova", bool(_sem_modo_divergente(
               lambda lista, serie: "modo", obrig, termos)))
    checar(u"  isca: a lista do chamador deixa de ser obrigatoria: reprova",
           bool(_sem_modo_divergente(quem or (lambda *a: None),
                                     _lista_obrigatoria_no_lote(
                                         src["radai_batch.py"].replace(
                                             u'_origem == "lista"',
                                             u'_origem == "nunca"')),
                                     termos)))
    checar(u"  isca: os Termos voltam a dizer que o roteiro roda AUTO: "
           u"reprova", bool(_sem_modo_divergente(
               quem or (lambda *a: None), obrig,
               termos.replace(_MARCA_SEM_MODO_LISTA, u""))))

    so_vigia = _tasks_do_config_so_no_vigia(src["radai_watcher.py"],
                                            src["radai_batch.py"])
    div = _tasks_so_no_vigia_divergente(so_vigia, termos)
    checar(u"o TASKS do config e lido so pelo vigia (medido: %s), e a 4.1 "
           u"diz se, e so se, ele e" % so_vigia, not div,
               u" | ".join(div))
    _isca_le = (u"\n\ndef _isca_le(t, m):\n"
                u"    return _tp.tasks_do_config_no_vigia(t, m)\n")
    checar(u"  isca: o vigia volta a ler o TASKS, com a 4.1 de hoje: reprova",
           bool(_tasks_so_no_vigia_divergente(_tasks_do_config_so_no_vigia(
               src["radai_watcher.py"] + _isca_le, src["radai_batch.py"]),
               termos)))
    checar(u"  isca: o vigia e o lote leem o TASKS: nao e «so pelo vigia»",
           not _tasks_do_config_so_no_vigia(src["radai_watcher.py"] + _isca_le,
                                            src["radai_batch.py"] + _isca_le))
    checar(u"  isca: a 4.1 volta a dizer que o TASKS «continua sendo lida, e "
           u"so pelo vigia», com o vigia de hoje: reprova",
           bool(_tasks_so_no_vigia_divergente(
               so_vigia, termos + u" " + _MARCA_TASKS_SO_VIGIA)))

    vig_ob = _vigia_passa_obrigatorias(src["radai_watcher.py"])
    div = _obrigatorias_divergente(vig_ob, obrig, termos)
    checar(u"a trava repetida numa tarefa obrigatoria derruba a serie (no "
           u"vigia so a base; no lote, a lista do roteiro), e a 1.4 diz",
           not div, u" | ".join(div))
    _vig_obrig = src["radai_watcher.py"].replace(
        u"obrigatorias=(), modo=MODO_DO_VIGIA",
        u"obrigatorias=_obrigatorias, modo=MODO_DO_VIGIA")
    checar(u"  isca: o vigia volta a passar obrigatorias (o TASKS), com a 1.4 "
           u"de hoje: reprova", _vig_obrig != src["radai_watcher.py"]
           and bool(_obrigatorias_divergente(
               _vigia_passa_obrigatorias(_vig_obrig), obrig, termos)))
    checar(u"  isca: a 1.4 volta a dizer o TASKS do vigia: reprova",
           bool(_obrigatorias_divergente(vig_ob, obrig, termos.replace(
               u"Quando uma tarefa trava.",
               u"Quando uma tarefa trava. " + _MARCA_OBRIG_VIGIA, 1))))
    checar(u"  isca: a 1.4 cala a lista do roteiro no lote: reprova",
           bool(_obrigatorias_divergente(vig_ob, obrig, termos.replace(
               _MARCA_OBRIG_LOTE, u"X"))))

    div = _hnl_obsoleta_divergente(v["radai_watcher.py"], termos)
    checar(u"INCLUIR_HNLNL saiu e os niveis rodam no AUTO: o paragrafo das "
           u"obsoletas diz o que passa a sair", not div, u" | ".join(div))
    _vh = dict(v["radai_watcher.py"])
    _vh["CHAVES_OBSOLETAS"] = dict(_vh.get("CHAVES_OBSOLETAS") or {},
                                   INCLUIR_HNLNL=u"os niveis sairam")
    checar(u"  isca: os niveis deixam de rodar no AUTO, com o paragrafo de "
           u"hoje: reprova", bool(_hnl_obsoleta_divergente(_vh, termos)))
    checar(u"  isca: o paragrafo cala o que passa a sair: reprova",
           bool(_hnl_obsoleta_divergente(v["radai_watcher.py"],
                                         termos.replace(_MARCA_HNL_LIGA,
                                                        u""))))

    desc = _r3_ao_lado_descartada(src["engine.py"])
    div = _r3_log_divergente(desc, termos)
    checar(u"a R3 dos arquivos ao lado nao chega ao registro do caso "
           u"(medido: %s), e a 1.3 diz que vai so ao log" % desc, not div,
           u" | ".join(div))
    _guarda = src["engine.py"].replace(
        u"limpar_fora_do_corpo(masks, _img_densidade",
        u"_r3_ao_lado = limpar_fora_do_corpo(masks, _img_densidade")
    checar(u"  isca: build_rtstruct guarda o que a R3 tirou, com a 1.3 de "
           u"hoje: reprova", _guarda != src["engine.py"] and bool(
               _r3_log_divergente(_r3_ao_lado_descartada(_guarda), termos)))
    checar(u"  isca: a 1.3 volta a dizer que tudo vai ao registro: reprova",
           bool(_r3_log_divergente(desc, termos.replace(_MARCA_R3_SO_LOG,
                                                        u""))))

    fn = _fatos_do_navegador(src["radai_todo.py"], src["radai_queue_state.py"],
                             src["radai_batch.py"], src["radai_view.py"])
    div = _navegador_divergente(fn, politica)
    checar(u"o navegador: o aviso por serie (8 ultimos do UID, sem prazo), a "
           u"pasta do lote e a pasta e o UID do «Ver segmentacao» (%s)"
           % u", ".join(k for k, x in sorted(fn.items()) if x), not div,
           u" | ".join(div))
    checar(u"  isca: a tela do «Ver segmentacao» deixa de apagar o UID: "
           u"reprova", bool(_navegador_divergente(
               _fatos_do_navegador(src["radai_todo.py"],
                                   src["radai_queue_state.py"],
                                   src["radai_batch.py"],
                                   src["radai_view.py"].replace(
                                       u"removeItem('radai_ver_uid')",
                                       u"getItem('radai_ver_uid')")),
               politica)))
    checar(u"  isca: um roteiro que apaga as marcas de aviso: reprova",
           bool(_navegador_divergente(
               _fatos_do_navegador(src["radai_todo.py"]
                                   + u"\nlocalStorage.removeItem("
                                     u"'radai_aviso_x');\n",
                                   src["radai_queue_state.py"],
                                   src["radai_batch.py"],
                                   src["radai_view.py"]), politica)))
    checar(u"  isca: a Politica cala o UID inteiro do «Ver segmentacao»: "
           u"reprova", bool(_navegador_divergente(fn, politica.replace(
               _MARCA_NAV_VER, u""))))

    subst = _substitui_depois_de_gravar(src["radai_batch.py"])
    div = _fast_regrava_divergente(v["radai_sets.py"], subst, politica)
    checar(u"refazer no FAST apaga o entregue e o completo do AUTO, e a "
           u"Politica diz", not div, u" | ".join(div))
    checar(u"  isca: sem o modo FAST no registro, com a Politica de hoje: "
           u"reprova", bool(_fast_regrava_divergente(
               dict(v["radai_sets.py"], SAIDAS_DE_MODO=()), subst, politica)))
    checar(u"  isca: a Politica cala: reprova",
           bool(_fast_regrava_divergente(v["radai_sets.py"], subst,
                                         politica.replace(_MARCA_FAST_APAGA,
                                                          u""))))

    div = _reto_derivado_divergente(src["engine.py"], termos)
    checar(u"o reto: a procedencia «derivada por marco anatomico» e dita nos "
           u"Termos", not div, u" | ".join(div))
    checar(u"  isca: o motor deixa de gravar a procedencia: reprova",
           bool(_reto_derivado_divergente(src["engine.py"].replace(
               u"derivada por marco anatomico", u"segmentada"), termos)))
    checar(u"  isca: os Termos a calam: reprova",
           bool(_reto_derivado_divergente(src["engine.py"], termos.replace(
               _MARCA_RETO_DERIVADO, u""))))

    div = _titulo_bolus_divergente(src["radai_bolus.py"], termos)
    checar(u"o titulo da 4.2 diz os arquivos que o bolus exporta", not div,
           u" | ".join(div))
    checar(u"  isca: o titulo de antes («um arquivo»): reprova",
           bool(_titulo_bolus_divergente(src["radai_bolus.py"], termos.replace(
               u"exporta arquivos", u"exporta um arquivo"))))
    checar(u"  isca: o bolus sem o molde, com o titulo de hoje: reprova",
           bool(_titulo_bolus_divergente(src["radai_bolus.py"].replace(
               u"def linha_do_ato_molde(", u"def _sem_molde("), termos)))

    prep = "baixar_pesos_ts" in _nomes_de_topo(
        ler(u"build/configurar_ambiente.py"), "def")
    docs_d = [(u"politica", politica), (u"creditos", creditos)]
    div = _desde_divergente(prep, docs_d)
    checar(u"o preparador baixa os pesos do TotalSegmentator desde a v8.2 "
           u"(medido: %s), e os documentos dizem desde quando" % prep,
           not div, u" | ".join(div))
    checar(u"  isca: a Politica volta a «desde esta versao»: reprova",
           bool(_desde_divergente(prep, [(u"politica", politica.replace(
               u"TotalSegmentator, desde a v8.2,",
               u"TotalSegmentator, desde esta versão,"))])))
    checar(u"  isca: o preparador sem baixar_pesos_ts: reprova",
           bool(_desde_divergente(False, docs_d)))

    chaves_ac = _chaves_do_acervo(src["radai_archive.py"])
    div = _acervo_divergente(chaves_ac, politica)
    checar(u"o indice do acervo (acervo.jsonl): o que ele grava (%s) e o que "
           u"a Politica diz" % u", ".join(sorted(chaves_ac)), bool(chaves_ac)
           and not div, u" | ".join(div))
    _sem_pid = politica.replace(u"acervo.jsonl ), com o PatientID,",
                                u"acervo.jsonl ), com")
    checar(u"  isca: a Politica cala o PatientID do acervo: reprova",
           _sem_pid != politica and bool(_acervo_divergente(chaves_ac,
                                                            _sem_pid)))
    checar(u"  isca: o acervo deixa de gravar o PatientID, com a Politica de "
           u"hoje: reprova", bool(_acervo_divergente(chaves_ac - {"pid"},
                                                      politica)))


_MARCA_HEART_CONDICAO = u"com o pericárdio quando a cavidade do tronco rodou"
_MARCA_HEART_RM = (u"na RM, porque ela é um modelo de TC e nenhum modo a pede "
                   u"ali")
_MARCA_HEART_PERSO = (u"no PERSONALIZADO de uma TC, quando nem um protocolo "
                      u"nem a chave dela a ligam")
_MARCA_HEART_PERSO_ATO = (u"no PERSONALIZADO de uma TC, só quando você desliga "
                          u"a chave dela, que nasce ligada")
_MARCA_PERSO_LIGADA = u"Na TC, a chave da cavidade do tronco nasce ligada"
_MARCA_PERSO_LIGADA_41 = u"a chave que nasce ligada nele"
_HEART_SEM_CONDICAO = u"o coração de radioterapia com o pericárdio"
_README_HEART_CONDICAO = (u"with its pericardium when the body cavity task "
                          u"ran")
_README_HEART_RM = u"on MR it never runs"
_README_HEART_PERSO = u"in CUSTOM only if a protocol or its own switch"
_README_HEART_PERSO_ATO = (u"in CUSTOM its switch starts on, and only "
                           u"switching it off")
_README_HEART_SEM_CONDICAO = u"the radiotherapy heart with its pericardium"
_DOC_HEART_TODA_SERIE = (u"No FAST e no AUTO ela roda em toda série em que o "
                         u"coração sai")
_DOC_NADA_NASCE_LIGADO = u"nada nasce ligado"


def _cavidade_do_tronco_roda():
    import radai_modes as MO
    t = u"trunk_cavities"
    rm = (t in MO.tasks_do_fast({MO.TORAX}, 600, "MR")
          or t in MO.tasks_da_topografia({MO.TORAX}, "MR", coracao_cm3=600)
          or t in MO.tasks_do_fast(set(), 600, "MR")
          or t in MO.tasks_da_topografia(set(), "MR", coracao_cm3=600)
          or t in MO.tasks_do_personalizado(
              tuple(p["cod"] for p in MO.PROTOCOLOS
                    if p.get("modalidade") == "MR"), None, "MR"))
    perso_ct = t in MO.tasks_do_personalizado((), None, "CT")
    return rm, perso_ct


def _heart_divergente(rm_roda, perso_roda, termos, readme, docs):
    fora = []
    t = u" ".join((termos or u"").split())
    r = u" ".join((readme or u"").split())
    if _HEART_SEM_CONDICAO in t:
        fora.append(u"termos: o Heart_ai com o pericardio, sem condicao")
    if _MARCA_HEART_CONDICAO not in t:
        fora.append(u"termos: calam a condicao (a cavidade do tronco)")
    if (_MARCA_HEART_RM in t) == bool(rm_roda):
        fora.append(u"termos: a RM (a cavidade roda nela: %s)" % rm_roda)
    if (_MARCA_HEART_PERSO in t) == bool(perso_roda):
        fora.append(u"termos: o PERSONALIZADO sem protocolo (a cavidade roda "
                    u"nele: %s)" % perso_roda)
    for marca, onde in ((_MARCA_HEART_PERSO_ATO, u"1.2"),
                        (_MARCA_PERSO_LIGADA, u"1.1"),
                        (_MARCA_PERSO_LIGADA_41, u"4.1")):
        if (marca in t) != bool(perso_roda):
            fora.append(u"termos %s: «%s» (a cavidade nasce ligada no "
                        u"PERSONALIZADO: %s)" % (onde, marca, perso_roda))
    if _README_HEART_SEM_CONDICAO in r:
        fora.append(u"README: the heart with its pericardium, sem condicao")
    if _README_HEART_CONDICAO not in r:
        fora.append(u"README: cala a condicao")
    if (_README_HEART_RM in r) == bool(rm_roda):
        fora.append(u"README: a RM (a cavidade roda nela: %s)" % rm_roda)
    if (_README_HEART_PERSO in r) == bool(perso_roda):
        fora.append(u"README: CUSTOM «only if a protocol or its own switch» "
                    u"(a cavidade nasce ligada: %s)" % perso_roda)
    if (_README_HEART_PERSO_ATO in r) != bool(perso_roda):
        fora.append(u"README: CUSTOM «its switch starts on» (a cavidade "
                    u"nasce ligada: %s)" % perso_roda)
    for nome, d in docs:
        dd = u" ".join((d or u"").replace(u"**", u"").split())
        if not rm_roda and _DOC_HEART_TODA_SERIE in dd:
            fora.append(u"%s: «em toda serie», e na RM ela nao roda" % nome)
        if perso_roda and _DOC_NADA_NASCE_LIGADO in dd:
            fora.append(u"%s: «nada nasce ligado», e a cavidade do tronco "
                        u"nasce ligada no PERSONALIZADO da TC" % nome)
    return fora


def teste_o_heart_ai_diz_quando_sai_sem_pericardio():
    secao(u"o Heart_ai sem pericardio: quando, nos Termos, no README e nos "
          u"registros")
    import radai_consent as CS
    termos = _plano(CS.TERMOS)
    readme = ler(u"README.md")
    docs = (OFICINA.documentos_do_heart(sys.modules[__name__])
            if OFICINA is not None else [])
    rm, perso = _cavidade_do_tronco_roda()
    checar(u"  (executei o radai_modes: a cavidade do tronco roda na RM por "
           u"algum modo: %s; no PERSONALIZADO da TC sem protocolo: %s)"
           % (rm, perso), True)
    div = _heart_divergente(rm, perso, termos, readme, docs)
    checar(u"os documentos dizem quando o Heart_ai sai sem pericardio (a RM "
           u"e o PERSONALIZADO sem o tronco)", not div, u" | ".join(div))
    _antes = termos.replace(
        u"coração de radioterapia ( Heart_ai ), " + _MARCA_HEART_CONDICAO,
        u"coração de radioterapia com o pericárdio ( Heart_ai )")
    checar(u"  isca: a frase de antes nos Termos («com o pericárdio», sem "
           u"condicao): reprova", _antes != termos and bool(
               _heart_divergente(rm, perso, _antes, readme, docs)))
    checar(u"  isca: a RM passa a rodar a cavidade, com os Termos de hoje: "
           u"reprova", bool(_heart_divergente(True, perso, termos, readme,
                                              docs)))
    checar(u"  isca: o PERSONALIZADO deixa de ligar a cavidade de fabrica, "
           u"com os Termos de hoje: reprova", bool(_heart_divergente(
               rm, not perso, termos, readme, docs)))
    _antes_perso = termos.replace(
        _MARCA_HEART_PERSO_ATO, _MARCA_HEART_PERSO)
    checar(u"  isca: a frase de antes da onda 4b («quando nem um protocolo "
           u"nem a chave dela a ligam»), com a cavidade ligada de fabrica: "
           u"reprova", _antes_perso != termos and bool(_heart_divergente(
               rm, perso, _antes_perso, readme, docs)))
    checar(u"  isca: o README de antes: reprova", bool(_heart_divergente(
        rm, perso, termos, readme.replace(
            _README_HEART_CONDICAO, u"with its pericardium"), docs)))
    _readme_1l = u" ".join(readme.split())
    checar(u"  isca: o README de antes da onda 4b (CUSTOM «only if a "
           u"protocol»): reprova", _README_HEART_PERSO_ATO in _readme_1l
           and bool(_heart_divergente(rm, perso, termos, _readme_1l.replace(
               _README_HEART_PERSO_ATO, _README_HEART_PERSO), docs)))
    if OFICINA is None:
        _componentes.pulado(u"os registros de engenharia do Heart_ai")
    else:
        OFICINA.iscas_do_heart(sys.modules[__name__], rm, perso, termos,
                               readme, docs)


_MARCA_R3_METADE = u"todo pedaço com pelo menos metade do volume dele"
_MARCA_R3_PELE = u"A pele continua sendo só a do maior pedaço"
_R3_SO_O_MAIOR = (u"O contorno externo é o maior pedaço do corpo: um braço "
                  u"separado do tronco fica fora dele")
_MARCA_TETO_TS = (u"continua sendo o teto de cada tarefa do TotalSegmentator, "
                  u"e também o do NV-Segment-CT e o do MOOSE")
_TETO_QUALQUER = u"continua sendo o teto de qualquer tarefa"
_MARCA_SUBST_DONE = (u"O marcador de conclusão anterior da série sai do lugar "
                     u"logo antes da gravação nova")
_MARCA_SUBST_QUEDA = (u"a próxima varredura do vigia, ou o próximo «Rodar "
                      u"agora» da série, o devolve ao lugar")
_MARCA_OV_INICIA = u"mas não inicia o turno nem a fila"
_MARCA_MAQ_CASO = (u"O nome da máquina também entra por pseudônimo, inclusive "
                   u"em cada etapa")
_MARCA_MAQ_PACOTE = (u"com o nome da máquina cru nas etapas, entra no pacote "
                     u"com o pseudônimo")


def _horas_da_constante_pt(src, nome):
    m = re.search(r"^%s\s*=\s*([0-9 *]+?)\s*(?:#.*)?$" % re.escape(nome),
                  src or u"", re.M)
    if not m:
        return None
    v = 1
    for p in m.group(1).split("*"):
        if not p.strip().isdigit():
            return None
        v *= int(p.strip())
    return v / 3600.0


def _horas_pt(h):
    return u"%s hora%s" % (_num_pt(h), u"" if h == 1 else u"s")


def _chama_dentro(src, funcao, chamada):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    for no in arv.body:
        if (isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
                and no.name == funcao):
            for n in ast.walk(no):
                if isinstance(n, ast.Call):
                    f = n.func
                    nome = getattr(f, "id", None) or getattr(f, "attr", None)
                    if nome == chamada:
                        return True
    return False


def _r3_membros_divergente(v_skin, src_skin, src_engine, termos):
    fora = []
    par = u" ".join(_trecho(termos, *_SECAO_REGRAS).split())
    fr = v_skin.get("FRACAO_DO_MAIOR_NO_CORPO")
    par_corpo = (u"com_o_corpo" in src_skin
                 and u"_corpo_da_serie" in _nomes_de_topo(src_engine, "def"))
    metade = par_corpo and fr == 0.5
    if metade is not (_MARCA_R3_METADE in par):
        fora.append(u"o corpo da R3 %s os pedacos com metade do maior "
                    u"(fracao %r), e a secao 1.3 %s" % (
                        u"leva" if metade else u"NAO leva", fr,
                        u"diz" if _MARCA_R3_METADE in par else u"nao diz"))
    if par_corpo and _R3_SO_O_MAIOR in par:
        fora.append(u"a secao 1.3 ainda diz que o contorno externo (o maior "
                    u"pedaco) e o corpo da R3")
    if par_corpo is not (_MARCA_R3_PELE in par):
        fora.append(u"a pele %s o corpo da R3, e a secao 1.3 %s" % (
            u"separa-se de" if par_corpo else u"e o mesmo que",
            u"diz que ela fica no maior" if _MARCA_R3_PELE in par
            else u"cala"))
    return fora


def _teto_divergente(src_hnl, src_cads, termos, src_cranio=None):
    fora = []
    t = u" ".join((termos or u"").split())
    if src_cranio is None:
        src_cranio = ler(u"app/radai_cranio_engine.py")
    hh, hc, hr = (_horas_da_constante_pt(src_hnl, "TEMPO_LIMITE_S"),
                  _horas_da_constante_pt(src_cads, "TETO_S"),
                  _horas_da_constante_pt(src_cranio, "TETO_S"))
    if hh is None or hc is None or hr is None:
        return [u"nao li os tetos fixos (niveis %r, CADS %r, encefalo %r)"
                % (hh, hc, hr)]
    if _TETO_QUALQUER in t:
        fora.append(u"a secao 1.4 diz «teto de qualquer tarefa»")
    if _MARCA_TETO_TS not in t:
        fora.append(u"a secao 1.4 nao diz o que o TIMEOUT_TASK_H cobre")
    frase = (u"os níveis cervicais têm teto fixo de %s, o CADS, de %s, e o "
             u"modelo do encéfalo em TC, de %s"
             % (_horas_pt(hh), _horas_pt(hc), _horas_pt(hr)))
    if frase not in t:
        fora.append(u"a secao 1.4 nao diz «%s»" % frase)
    return fora


def _substituir_done_divergente(src_batch, src_watcher, politica):
    fora = []
    p = u" ".join((politica or u"").split())
    defs = _nomes_de_topo(src_batch, "def")
    troca = {"_afastar_o_done", "_devolver_o_done"} <= defs
    if troca is not (_MARCA_SUBST_DONE in p):
        fora.append(u"o «Substituir» %s o marcador de conclusao, e a Politica "
                    u"%s" % (u"troca" if troca else u"NAO troca",
                             u"diz" if _MARCA_SUBST_DONE in p else u"cala"))
    queda = _chama_dentro(src_watcher, "scan_root", "resolver_done_afastado")
    if queda is not (_MARCA_SUBST_QUEDA in p):
        fora.append(u"a varredura %s o rastro de uma queda, e a Politica %s"
                    % (u"resolve" if queda else u"NAO resolve",
                       u"diz" if _MARCA_SUBST_QUEDA in p else u"cala"))
    return fora


def _overnight_inicia_divergente(src_batch, termos):
    t = u" ".join((termos or u"").split())
    incluir = _fonte_da_funcao_js(src_batch, "_ovPorNaFila")
    aguarda = (u"return filaOvernight(true)" in incluir
               and u"Na fila, aguardando INICIAR." in incluir
               and u"/api/pipeline/iniciar" not in incluir
               and u"_ovIniciarAFila(" not in (src_batch or u""))
    fora = []
    if aguarda is not (_MARCA_OV_INICIA in t):
        fora.append(u"o modal %s sem iniciar, e os Termos %s" % (
            u"inclui" if aguarda else u"NAO inclui",
            u"dizem" if _MARCA_OV_INICIA in t else u"calam"))
    if u"«Salvar e iniciar»" in t:
        fora.append(u"os Termos ainda prometem iniciar ao salvar")
    return fora


def _maquina_do_caso_divergente(src_records, politica):
    fora = []
    p = u" ".join((politica or u"").split())
    try:
        arv = ast.parse(src_records or u"")
        etapa = [f for c in arv.body if isinstance(c, ast.ClassDef)
                 and c.name == "Caso" for f in c.body
                 if isinstance(f, ast.FunctionDef) and f.name == "etapa"]
        no_caso = bool(etapa) and any(
            isinstance(n, ast.Call) and getattr(n.func, "id", None)
            == "pseudonimo_de_uma_maquina" for n in ast.walk(etapa[0]))
    except SyntaxError:
        no_caso = False
    if no_caso is not (_MARCA_MAQ_CASO in p):
        fora.append(u"o caso %s a maquina por pseudonimo, e a Politica %s"
                    % (u"grava" if no_caso else u"NAO grava",
                       u"diz" if _MARCA_MAQ_CASO in p else u"cala"))
    no_pacote = _chama_dentro(src_records, "exportar",
                              "_maquinas_por_pseudonimo")
    if no_pacote is not (_MARCA_MAQ_PACOTE in p):
        fora.append(u"o exportador %s o caso antigo, e a Politica %s"
                    % (u"troca a maquina do" if no_pacote else u"NAO troca",
                       u"diz" if _MARCA_MAQ_PACOTE in p else u"cala"))
    return fora


def teste_o_que_a_onda_4b_mudou_na_16():
    secao(u"documentos 1.6: o que a onda 4b da v8.3 mudou, amarrado ao codigo")
    import radai_consent as CS
    termos = _plano(CS.TERMOS)
    politica = _plano(CS.POLITICA)
    src = dict((n, ler(u"app/" + n)) for n in (
        "engine.py", "radai_skin.py", "radai_batch.py", "radai_watcher.py",
        "radai_records.py", "radai_hnlnl_engine.py", "radai_cads_engine.py"))
    v_skin = _valores_do_modulo(src["radai_skin.py"])

    div = _r3_membros_divergente(v_skin, src["radai_skin.py"],
                                 src["engine.py"], termos)
    checar(u"a R3: o corpo leva os pedacos com metade do maior, a pele fica "
           u"no maior — o codigo e a secao 1.3", not div, u" | ".join(div))
    checar(u"  isca: so o maior no codigo (fracao 1.01), com a secao de hoje: "
           u"reprova", bool(_r3_membros_divergente(
               dict(v_skin, FRACAO_DO_MAIOR_NO_CORPO=1.01),
               src["radai_skin.py"], src["engine.py"], termos)))
    _r3_antes = termos.replace(u"O corpo, para esta regra, é o maior pedaço e "
                               + _MARCA_R3_METADE, _R3_SO_O_MAIOR)
    checar(u"  isca: a frase de antes («o maior pedaço do corpo»), com o "
           u"codigo de hoje: reprova", _r3_antes != termos and bool(
               _r3_membros_divergente(v_skin, src["radai_skin.py"],
                                      src["engine.py"], _r3_antes)))

    div = _teto_divergente(src["radai_hnlnl_engine.py"],
                           src["radai_cads_engine.py"], termos)
    checar(u"o TIMEOUT_TASK_H: o que ele cobre, e os tetos fixos dos niveis "
           u"cervicais e do CADS lidos do codigo", not div, u" | ".join(div))
    checar(u"  isca: o CADS com 2 h no codigo, com a secao de hoje: reprova",
           bool(_teto_divergente(src["radai_hnlnl_engine.py"],
                                 u"TETO_S = 7200\n", termos)))
    checar(u"  isca: a frase de antes («teto de qualquer tarefa»): reprova",
           bool(_teto_divergente(src["radai_hnlnl_engine.py"],
                                 src["radai_cads_engine.py"], termos.replace(
                                     _MARCA_TETO_TS, _TETO_QUALQUER))))
    checar(u"  isca: o modelo do encefalo com 3 h no codigo, com a secao de "
           u"hoje: reprova",
           bool(_teto_divergente(src["radai_hnlnl_engine.py"],
                                 src["radai_cads_engine.py"], termos,
                                 u"TETO_S = 3 * 3600" + chr(10))))

    div = _substituir_done_divergente(src["radai_batch.py"],
                                      src["radai_watcher.py"], politica)
    checar(u"o «Substituir» troca o marcador de conclusao, e a varredura "
           u"resolve o rastro de uma queda: o codigo e a Politica (secao 6)",
           not div, u" | ".join(div))
    checar(u"  isca: o lote sem devolver o marcador, com a Politica de hoje: "
           u"reprova", bool(_substituir_done_divergente(
               src["radai_batch.py"].replace(u"def _devolver_o_done(",
                                             u"def _sem_devolver("),
               src["radai_watcher.py"], politica)))
    checar(u"  isca: a varredura sem resolver o rastro: reprova",
           bool(_substituir_done_divergente(
               src["radai_batch.py"], src["radai_watcher.py"].replace(
                   u"resolver_done_afastado(", u"_nada("), politica)))
    checar(u"  isca: a Politica de antes (sem o marcador): reprova",
           bool(_substituir_done_divergente(
               src["radai_batch.py"], src["radai_watcher.py"],
               politica.replace(_MARCA_SUBST_DONE, u"X"))))

    div = _overnight_inicia_divergente(src["radai_batch.py"], termos)
    checar(u"o Overnight Run entra na fila e aguarda INICIAR: o codigo e os "
           u"Termos (secao 4.3)", not div, u" | ".join(div))
    checar(u"  isca: o modal volta a iniciar a fila ao salvar: reprova",
           bool(_overnight_inicia_divergente(
               src["radai_batch.py"].replace(u"return filaOvernight(true)",
                   u"return _ovIniciarAFila(d)"), termos)))
    checar(u"  isca: os Termos de antes: reprova",
           bool(_overnight_inicia_divergente(
               src["radai_batch.py"], termos.replace(_MARCA_OV_INICIA,
                                                     u"X"))))

    div = _maquina_do_caso_divergente(src["radai_records.py"], politica)
    checar(u"o nome da maquina no caso e no pacote: por pseudonimo, o codigo "
           u"e a Politica (secoes 3 e 5)", not div, u" | ".join(div))
    checar(u"  isca: o Caso.etapa sem a troca, com a Politica de hoje: "
           u"reprova", bool(_maquina_do_caso_divergente(
               src["radai_records.py"].replace(
                   u"pseudonimo_de_uma_maquina(e[\"maquina\"], self.base)",
                   u"(e[\"maquina\"])", 1), politica)))
    checar(u"  isca: o exportador sem a troca do caso antigo: reprova",
           bool(_maquina_do_caso_divergente(
               src["radai_records.py"].replace(
                   u"_maquinas_por_pseudonimo(\n", u"_nada(\n").replace(
                   u"and _maquinas_por_pseudonimo(", u"and _nada("),
               politica)))
    checar(u"  isca: a Politica de antes (sem a maquina): reprova",
           bool(_maquina_do_caso_divergente(
               src["radai_records.py"], politica.replace(_MARCA_MAQ_CASO,
                                                         u"X"))))


_DERRAME = "pleural_pericard_effusion"
_ROTULOS_DO_DERRAME = ("pleural_effusion_left", "pleural_effusion_right",
                       "pericardial_effusion")
_MARCA_DERRAME_TERMOS = u"O derrame pleural e o pericárdico também são da anatomia"
_MARCA_DERRAME_FAST = u"ao entregue do FAST"
_MARCA_DERRAME_SO_FULL = u"sai só no conjunto completo"
_MARCA_DERRAME_NO_CORACAO = (u"o pericárdico entra no coração de "
                             u"radioterapia")
_MARCA_DERRAME_CORACAO_CREDITOS = (u"o pericárdico vai dentro do coração "
                                   u"de radioterapia")
_MARCA_DERRAME_LIGADA = u"A do derrame pleural e pericárdico também nasce ligada"
_MARCA_DERRAME_PONTO = u"O derrame pleural e o pericárdico são anatomia do tórax"
_MARCA_DERRAME_CREDITOS = u"O derrame pleural e pericárdico é anatomia do tórax"
_MARCA_DERRAME_README = u"effusion task is anatomy of the chest"
_MARCA_MAPA_POLITICA = u"o mapa de rótulos de um estudo das Reconstruções 3D"
_MARCA_MAPA_UID = u"com o UID inteiro dentro"


def _fatos_do_derrame(achados, v_sets, v_modes, src_constructs=None):
    oar = set(v_sets.get("PERMITIDOS_NO_OAR") or ())
    fora_fast = set(v_sets.get("FORA_DO_OAR_FAST") or ())
    achado = _DERRAME in set(achados or ())
    no_full = _DERRAME in tuple(v_sets.get("TASKS_DO_FULL") or ())
    no_oar = set(_ROTULOS_DO_DERRAME) <= oar
    torax = v_modes.get("TORAX")
    roda_no_fast = _DERRAME in tuple((v_modes.get("TASKS_DO_FAST") or {})
                                     .get(torax) or ())
    fast = (no_oar and not (set(_ROTULOS_DO_DERRAME) & fora_fast)
            and roda_no_fast)
    no_coracao = bool(_referencias_no_fonte(
        _fonte_da_funcao(src_constructs or u"", "coracao_ai"),
        "_derrame_pericardico"))
    ligada = _DERRAME in tuple((v_modes.get("LIGADAS_DE_FABRICA_NO_PERSO")
                                or {}).get("CT") or ())
    plugin = any((p or {}).get("task") == _DERRAME
                 for p in (v_sets.get("PLUGINS") or ()))
    return {"anatomia": (not achado) and no_full, "achado": achado,
            "no_oar": no_oar, "fast": fast, "roda_no_fast": roda_no_fast,
            "no_coracao": no_coracao, "ligada": ligada, "plugin": plugin}


def _derrame_divergente(f, termos, ponto, creditos, readme):
    fora = []
    lista_41 = _trecho(termos, u"No TotalSegmentator — as tarefas de achado",
                       u"No NV-Segment-CT")
    if not lista_41:
        fora.append(u"os Termos nao tem a lista das tarefas de achado (4.1)")
    elif (u"pleural_pericard_effusion" in lista_41) is not f["achado"]:
        fora.append(u"o derrame %s achado no motor, e a 4.1 %s" % (
            u"e" if f["achado"] else u"NAO e",
            u"o lista" if f["achado"] is False else u"nao o lista"))
    par = _trecho(termos, _MARCA_DERRAME_TERMOS, u"O que muda para quem liga")
    for tem, marca, onde in (
            (f["anatomia"], _MARCA_DERRAME_TERMOS, u"os Termos (4.1)"),
            (f["anatomia"] and f["fast"], _MARCA_DERRAME_FAST,
             u"o paragrafo do derrame"),
            (f["anatomia"] and not f.get("no_oar"), _MARCA_DERRAME_SO_FULL,
             u"o paragrafo do derrame"),
            (f["anatomia"] and not f.get("no_oar"), _MARCA_DERRAME_SO_FULL,
             u"os Creditos"),
            (f.get("no_coracao"), _MARCA_DERRAME_NO_CORACAO,
             u"o paragrafo do derrame"),
            (f.get("no_coracao"), _MARCA_DERRAME_CORACAO_CREDITOS,
             u"os Creditos"),
            (f["ligada"], _MARCA_DERRAME_LIGADA, u"os Termos (1.1)"),
            (f["anatomia"], _MARCA_DERRAME_PONTO, u"o ponto deteccao"),
            (f["anatomia"], _MARCA_DERRAME_CREDITOS, u"os Creditos"),
            (f["anatomia"], _MARCA_DERRAME_README, u"o README")):
        txt = {u"os Termos (4.1)": termos, u"o paragrafo do derrame": par,
               u"os Termos (1.1)": termos, u"o ponto deteccao": ponto,
               u"os Creditos": creditos, u"o README": readme}[onde]
        if bool(tem) is not (marca in (txt or u"")):
            fora.append(u"o codigo %s, e %s %s «%s»" % (
                u"faz" if tem else u"NAO faz", onde,
                u"diz" if marca in (txt or u"") else u"nao diz", marca))
    exemplos = (ponto or u"").split(u"Nenhuma roda por omissão")[0]
    if f["anatomia"] and u"derrame" in exemplos:
        fora.append(u"o ponto deteccao da o derrame como exemplo de achado")
    bullet = _trecho(creditos, u"Tarefas de achado do TotalSegmentator",
                     u"O derrame pleural e pericárdico")
    if (u"pleural_pericard_effusion" in bullet) is not f["achado"]:
        fora.append(u"os Creditos %s o derrame entre as tarefas de achado" % (
            u"listam" if u"pleural_pericard_effusion" in bullet
            else u"nao listam"))
    return fora


def _mapa_divergente(src_output, src_rotulos, politica):
    grava = (u"def mapa_de_rotulos(" in (src_output or u"")
             and u'PASTA = "_RadAI"' in (src_rotulos or u""))
    com_uid = u'"uid": str(uid' in (src_rotulos or u"")
    fora = []
    if grava is not (_MARCA_MAPA_POLITICA in politica):
        fora.append(u"o estudo 3D %s um mapa em _RadAI, e a Politica %s" % (
            u"grava" if grava else u"NAO grava",
            u"o cita" if _MARCA_MAPA_POLITICA in politica else u"nao o cita"))
    par = _trecho(politica, _MARCA_MAPA_POLITICA, u"Trate a subpasta")
    if grava and com_uid is not (_MARCA_MAPA_UID in par):
        fora.append(u"o mapa %s o UID inteiro, e a Politica %s" % (
            u"leva" if com_uid else u"NAO leva",
            u"diz" if _MARCA_MAPA_UID in par else u"nao diz"))
    return fora


def teste_o_que_a_v84_mudou_na_17():
    secao(u"documentos 1.7: o derrame, o vigia sem o TASKS e o mapa do "
          u"estudo 3D, amarrados ao codigo")
    import radai_consent as CS
    import radai_credits as CR
    termos = _plano(CS.TERMOS)
    politica = _plano(CS.POLITICA)
    creditos = _plano(CR.pagina())
    readme = u" ".join(ler("README.md").split())
    ponto = dict((c, t + u" " + d) for (c, t, d) in CS.PONTOS).get(
        u"deteccao", u"")
    v_sets = _valores_do_modulo(ler(u"app/radai_sets.py"))
    v_modes = _valores_do_modulo(ler(u"app/radai_modes.py"))
    achados = _tasks_de_achado_do_motor() or []
    src_cons = ler(u"app/radai_constructs.py")
    f = _fatos_do_derrame(achados, v_sets, v_modes, src_cons)
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % kv for kv in sorted(f.items())),
        bool(v_sets.get("TASKS_DO_FULL")) and bool(v_modes.get("TORAX")))
    div = _derrame_divergente(f, termos, ponto, creditos, readme)
    checar(u"o derrame: anatomia do torax no codigo (no FULL; no OAR so "
           u"dentro do coracao; ligado no PERSONALIZADO), e os documentos "
           u"dizem", not div, u" | ".join(div))
    checar(u"  isca: os rotulos do derrame de volta no OAR, com os textos de "
           u"hoje: reprova", bool(_derrame_divergente(
               dict(f, no_oar=True, fast=f["roda_no_fast"]), termos, ponto,
               creditos, readme)))
    _sem_coracao = src_cons.replace(u"_derrame_pericardico(masks, cru)",
                                    u"None")
    checar(u"  isca: o coracao deixa de levar o derrame pericardico no "
           u"fonte: reprova", _sem_coracao != src_cons and bool(
               _derrame_divergente(_fatos_do_derrame(
                   achados, v_sets, v_modes, _sem_coracao), termos, ponto,
                   creditos, readme)))
    checar(u"  isca: os Creditos calam o derrame so no completo: reprova",
           bool(_derrame_divergente(f, termos, ponto, creditos.replace(
               _MARCA_DERRAME_SO_FULL, u"X"), readme)))
    checar(u"  e o plugin do derrame saiu do registro", not f["plugin"])
    _f_achado = dict(f, anatomia=False, achado=True)
    checar(u"  isca: o derrame volta a ser achado no motor, com os textos de "
           u"hoje: reprova", bool(_derrame_divergente(
               _f_achado, termos, ponto, creditos, readme)))
    _f2 = _fatos_do_derrame(achados + [_DERRAME], v_sets, v_modes)
    checar(u"  isca: a mesma conta, com o derrame em TASKS_DE_ACHADO, muda",
           _f2["achado"] and not _f2["anatomia"])
    _vs = dict(v_sets, TASKS_DO_FULL=tuple(
        t for t in v_sets.get("TASKS_DO_FULL") or () if t != _DERRAME))
    checar(u"  isca: o derrame fora do FULL deixa de ser anatomia",
           not _fatos_do_derrame(achados, _vs, v_modes)["anatomia"])
    checar(u"  isca: os Termos calam o derrame como anatomia: reprova",
           bool(_derrame_divergente(f, termos.replace(_MARCA_DERRAME_TERMOS,
                                                      u"X"),
                                    ponto, creditos, readme)))
    checar(u"  isca: o ponto volta a dar o derrame como achado: reprova",
           bool(_derrame_divergente(f, termos, u"nódulo pulmonar, derrame. "
                                    u"Nenhuma roda por omissão. "
                                    + _MARCA_DERRAME_PONTO, creditos, readme)))
    _t41 = termos.replace(u"achado lung_nodules ,",
                          u"achado lung_nodules , pleural_pericard_effusion ,")
    checar(u"  isca: a 4.1 volta a listar o derrame entre os achados: reprova",
           _t41 != termos and bool(_derrame_divergente(
               f, _t41, ponto, creditos, readme)))

    src_out = ler(u"app/radai_output.py")
    src_rot = ler(u"app/radai_rotulos.py")
    div = _mapa_divergente(src_out, src_rot, politica)
    checar(u"o estudo das Reconstrucoes 3D grava o mapa de rotulos em _RadAI "
           u"com o UID inteiro, e a Politica (secao 3) diz", not div,
           u" | ".join(div))
    checar(u"  isca: o mapa sem o UID no codigo, com a Politica de hoje: "
           u"reprova", bool(_mapa_divergente(
               src_out, src_rot.replace(u'"uid": str(uid', u'"x": str(0'),
               politica)))
    checar(u"  isca: a Politica cala o mapa: reprova", bool(_mapa_divergente(
        src_out, src_rot, politica.replace(_MARCA_MAPA_POLITICA, u"X"))))

    src_reg = ler(u"app/radai_records.py")
    grava_prot = u'{"protocolos": _prot}' in src_reg
    _marca_prot = u"os protocolos pedidos no PERSONALIZADO"
    checar(u"o marcador de conclusao guarda os protocolos (medido: %s), e a "
           u"Politica (secao 3) diz" % grava_prot,
           grava_prot is (_marca_prot in politica))
    checar(u"  isca: a Politica cala os protocolos: reprova",
           grava_prot is not (_marca_prot in politica.replace(_marca_prot,
                                                                u"X")))




_PRIMEIRA_COM_TROCAS_NO_DADO = (1, 7)


def _versao_em_tupla(v):
    try:
        return tuple(int(x) for x in str(v).split(u"."))
    except ValueError:
        return (0,)


def _trocas_divergentes(trocadas, resselagens, publicadas):
    fora = []
    for v, n in sorted((resselagens or {}).items()):
        if (_versao_em_tupla(v) >= _PRIMEIRA_COM_TROCAS_NO_DADO
                and n and v not in (trocadas or {})):
            fora.append(u"a %s tem %s resselagem(ns) e nenhuma troca no "
                        u"dado" % (v, n))
    for v, lista in sorted((trocadas or {}).items()):
        if len(lista) != (resselagens or {}).get(v):
            fora.append(u"a %s tem %d troca(s) no dado e %s resselagem(ns)"
                        % (v, len(lista), (resselagens or {}).get(v)))
        vigor = (publicadas or {}).get(v) or u""
        for h, motivo in lista:
            if not re.match(r"^[0-9a-f]{12}$", h or u""):
                fora.append(u"a %s: a impressao trocada %r nao e um "
                            u"prefixo de 12 hex" % (v, h))
            if h and vigor.startswith(h):
                fora.append(u"a %s: a trocada %s e a impressao em vigor"
                            % (v, h))
            if len(u" ".join((motivo or u"").split())) < 20:
                fora.append(u"a %s: a troca %s nao diz o que entrou no "
                            u"texto" % (v, h))
    return fora


_MARCAS_DO_DESINSTALADOR = {
    "tmp_dos_discos": u"de cada disco e no %TEMP%",
    "motor_json": u"motor_<porta>.json que ficam em",
    "cache_deslocado": (u"o cache por tarefa posto fora da pasta do programa "
                        u"junto com o acervo"),
    "apagar_fora": u"-ApagarFora",
}


def _fatos_do_desinstalador(un):
    u = un or u""
    return {
        "tmp_dos_discos": (u'"RADIOTERAPIA_AI") "tmp"' in u
                           and u'-Filter "radai_*"' in u),
        "motor_json": u'"motor_*.json"' in u,
        "cache_deslocado": u'"cache_tasks"' in u,
        "apagar_fora": u"[switch]$ApagarFora" in u,
    }


def _desinstalador_divergente(un, politica):
    fatos = _fatos_do_desinstalador(un)
    par = _trecho(politica, u"O desinstalador.", u"Apagá-los é ato do serviço")
    fora = []
    if not par:
        return [u"a Politica nao tem o paragrafo do desinstalador"]
    for k, marca in sorted(_MARCAS_DO_DESINSTALADOR.items()):
        if fatos[k] is not (marca in par):
            fora.append(u"%s: o UNINSTALL %s, e a Politica %s" % (
                k, u"o faz" if fatos[k] else u"NAO o faz",
                u"diz" if marca in par else u"nao diz"))
    return fora


_BOTOES_DO_BRIDGE = (u"Converter esta série", u"Converter as marcadas",
                     u"Exportar as marcadas (.zip)", u"Ajustar e entregar",
                     u"Converter e Salvar", u"Entregar",
                     u"Ajustar e finalizar", u"Baixar de novo")
_ROTAS_DO_BRIDGE_QUE_SAIRAM = (u"/api/bridge/entregar",
                               u"/api/bridge/converter",
                               u"/api/bridge/baixar",
                               u"/api/bridge/corpus",
                               u"/api/bridge/salvar",
                               u"/api/imagem/converter",
                               u"/api/imagem/varrer",
                               u"/api/imagem/identidade")


def _rotas_servidas(src):
    return set(re.findall(
        r"@app\.(?:get|post|put|delete|api_route)\(\s*[\"']([^\"']+)"
        r"[\"']", src or u""))


def _tela_tem_o_botao(textos, rotulo):
    return (u">%s<" % rotulo) in (textos or u"")


def _botoes_do_bridge_divergentes(bridge, politica):
    fora = []
    for r in _BOTOES_DO_BRIDGE:
        tem = _tela_tem_o_botao(bridge, r)
        diz = (u"«%s»" % r) in (politica or u"")
        if tem is not diz:
            fora.append(u"«%s»: a tela %s, e a Politica %s" % (
                r, u"tem" if tem else u"NAO tem",
                u"cita" if diz else u"nao cita"))
    return fora


def _tela_chama_a_entrega_pelo_navegador(src):
    return bool(re.search(
        r"fetch\(\s*['\"]/api/(?:bridge/entregar|imagem/converter)['\"]",
        src or u""))


_MARCA_CACHE_NAO_SAI = u"é dado derivado de paciente, e não sai da estação"


def _fatos_do_cache(src_ct, src_un):
    v = _valores_do_modulo(src_ct)
    conf = _fonte_da_funcao(src_ct, "conferir_pasta")
    return {"existe": u"def gravar(" in (src_ct or u""),
            "pasta": v.get("NOME_DA_PASTA"), "ttl": v.get("TTL_DIAS"),
            "teto": v.get("TETO_GB"),
            "variavel": u"RADAI_CACHE_TASKS_DIR" in (src_ct or u""),
            "nuvem": u"em_pasta_sincronizada" in conf,
            "rede": u"_e_rede(" in conf,
            "clinicas": u"_pastas_clinicas(" in conf,
            "desinstalar": u'"cache_tasks"' in (src_un or u"")}


def _cache_divergente(f, politica):
    par = _trecho(politica, u"O cache por tarefa ,", u"O log")
    sec6 = _trecho(politica, u"sai a entrada que não é lida", u";")
    fora = []
    if f["existe"] is not bool(par):
        return [u"o cache %s no codigo, e a Politica (secao 3) %s" % (
            u"existe" if f["existe"] else u"NAO existe",
            u"o descreve" if par else u"cala")]
    if not f["existe"]:
        return fora
    if not f["pasta"] or (u"%s\\" % f["pasta"]) not in par:
        fora.append(u"a pasta do cache e %s no codigo" % f["pasta"])
    for k, marca in (("variavel", u"RADAI_CACHE_TASKS_DIR"),
                     ("nuvem", u"numa pasta que sincroniza com a nuvem"),
                     ("rede", u"numa pasta de rede"),
                     ("clinicas", u"dentro da pasta dos exames")):
        if f[k] is not (marca in par):
            fora.append(u"%s: o codigo %s, e a Politica %s" % (
                k, u"o faz" if f[k] else u"NAO o faz",
                u"diz" if marca in par else u"nao diz"))
    if _MARCA_CACHE_NAO_SAI not in par:
        fora.append(u"a Politica nao diz que o cache e dado derivado de "
                    u"paciente e nao sai da estacao")
    if (u"há %s dias" % _num_pt(f["ttl"])) not in sec6:
        fora.append(u"o cache vive %s dias no codigo, e a secao 6 nao diz"
                    % _num_pt(f["ttl"]))
    if (u"passar de %s GB" % _num_pt(f["teto"])) not in sec6:
        fora.append(u"o teto do cache e %s GB no codigo, e a secao 6 nao diz"
                    % _num_pt(f["teto"]))
    return fora


_MARCAS_DOS_NIVEIS = {
    "termos_oar": u"vão ao entregue só a união e as parótidas do nível VIII",
    "termos_nao_e": u"não é OAR nem CTV",
    "creditos_oar": u"LNL_UNION_ai, que não é OAR nem CTV",
    "notice_oar": u"LNL_UNION_ai, que NAO E OAR NEM CTV",
    "termos_parotida": u"menos o esternocleidomastoideo",
}
_FRASES_DOS_NIVEIS_DE_ANTES = (
    u"Os vinte níveis saem com nome neutro",
    u"os vinte níveis saem com nome neutro",
    u"O NOME DE CADA NIVEL NAO ESTA PUBLICADO",
    u"e nunca no entregue; o arquivo próprio deles",
    u"e nunca no entregue (OAR)",
    u"(OAR); o arquivo proprio deles")


def _fatos_dos_niveis(v_sets, v_hn):
    perm = set(v_sets.get("PERMITIDOS_NO_OAR") or ())
    mapa = v_hn.get("MAPA_DOS_PESOS") or {}
    return {"uniao_no_oar": "LNL_UNION" in perm,
            "parotida_no_oar": bool(perm & {"parotid_lnl_left",
                                            "parotid_lnl_right"}),
            "nivel_no_oar": any(str(k).startswith(("Lvl_", "LNL0", "LNL1",
                                                   "LNL2")) for k in perm),
            "nomes_de_gregoire": (bool(mapa)
                                  and v_hn.get("ORDEM_CONFERIDA") is True)}


def _niveis_divergentes(f, termos, creditos, notice):
    n = u" ".join((notice or u"").split())
    fora = []
    if f["nivel_no_oar"]:
        fora.append(u"um nivel cervical (Lvl_ ou LNL) esta em "
                    u"PERMITIDOS_NO_OAR: os documentos dizem que nao")
    pares = ((u"Termos", termos, "termos_oar"),
             (u"Termos", termos, "termos_nao_e"),
             (u"Creditos", creditos, "creditos_oar"),
             (u"NOTICE", n, "notice_oar"))
    for nome, txt, k in pares:
        diz = _MARCAS_DOS_NIVEIS[k] in (txt or u"")
        if diz is not f["uniao_no_oar"]:
            fora.append(u"a uniao %s ao OAR no codigo, e %s %s" % (
                u"vai" if f["uniao_no_oar"] else u"NAO vai", nome,
                u"diz" if diz else u"nao diz"))
    diz = _MARCAS_DOS_NIVEIS["termos_parotida"] in (termos or u"")
    if diz is not f["parotida_no_oar"]:
        fora.append(u"a parotida do nivel VIII %s ao OAR no codigo, e os "
                    u"Termos %s" % (u"vai" if f["parotida_no_oar"]
                                    else u"NAO vai",
                                    u"dizem" if diz else u"nao dizem"))
    for nome, txt in ((u"Termos", termos), (u"Creditos", creditos),
                      (u"NOTICE", n)):
        diz = u"Lvl_Ia" in (txt or u"")
        if diz is not f["nomes_de_gregoire"]:
            fora.append(u"os nomes de Gregoire %s no codigo, e %s %s" % (
                u"valem" if f["nomes_de_gregoire"] else u"NAO valem", nome,
                u"os diz" if diz else u"nao os diz"))
        for velha in _FRASES_DOS_NIVEIS_DE_ANTES:
            if velha in (txt or u""):
                fora.append(u"%s ainda diz %r" % (nome, velha[:40]))
    return fora


_MARCA_L6 = u"O índice 26 entra no sacro."
_MARCA_L6_CRU = u"também no TotalSegmentator cru"
_MARCA_L6_NOTICE = u"so o indice 26 fundido"


def _fatos_do_indice_26(v_engine, src_engine):
    ordem = [p[0] for p in (v_engine.get("ORDEM_DO_FULL") or ())
             if isinstance(p, tuple) and p]
    build = _fonte_da_funcao(src_engine, "build_rtstruct")
    return {"full": "fusao_do_indice_26" in ordem,
            "cru": u"vista_com_indice_26_fundido(" in build}


def _indice_26_divergente(f, termos, notice):
    n = u" ".join((notice or u"").split())
    fora = []
    for k, txt, marca, nome in (("full", termos, _MARCA_L6, u"Termos"),
                                ("cru", termos, _MARCA_L6_CRU, u"Termos"),
                                ("cru", n, _MARCA_L6_NOTICE, u"NOTICE")):
        diz = marca in (txt or u"")
        if diz is not f[k]:
            fora.append(u"a fusao do indice 26 (%s) %s no codigo, e %s %s"
                        % (k, u"existe" if f[k] else u"NAO existe", nome,
                           u"diz" if diz else u"nao diz"))
    return fora


_CAMPOS_NOVOS_DO_DONE = ("faltou", "tasks_sem_estrutura", "tasks_do_cache",
                         "cache_das_tasks", "receita_pos",
                         "motores_fora_do_ts")
_CAMPOS_NOVOS_DO_FAIL = ("assinatura", "turno", "versao_do_app", "cortes",
                         "adiada", "em_espera", "inelegivel")
_MARCA_REFEITO_POS = u"a origem refeito_pos"


def _chaves_do_campos_do_done(src_records):
    try:
        arv = ast.parse(src_records or u"")
    except SyntaxError:
        return set()
    fora = set()
    for fn in ast.walk(arv):
        if not (isinstance(fn, ast.FunctionDef)
                and fn.name == "campos_do_done"):
            continue
        for r in ast.walk(fn):
            if not (isinstance(r, ast.Return) and isinstance(r.value,
                                                             ast.Dict)):
                continue
            for k, v in zip(r.value.keys, r.value.values):
                if isinstance(k, ast.Constant):
                    fora.add(k.value)
                elif k is None:
                    for d in ast.walk(v):
                        if isinstance(d, ast.Dict):
                            fora.update(x.value for x in d.keys
                                        if isinstance(x, ast.Constant))
    return fora


def _chaves_do_fail(fontes):
    consts = dict((k, v) for k, v in _valores_do_modulo(
        ler(u"app/radai_falhas.py")).items() if isinstance(v, str))
    consts.update((k, v) for k, v in _valores_do_modulo(
        fontes.get("watcher") or u"").items() if isinstance(v, str))
    consts.setdefault("INELEGIVEL", _valores_do_modulo(
        ler(u"app/radai_falhas.py")).get("INELEGIVEL"))
    fora = set()
    for _q, dono, expr in _escritas_de_marcador(fontes, "fail"):
        fora.update(_chaves_gravadas(dono, expr))
        for no in ast.walk(dono):
            if isinstance(no, ast.Dict):
                for k in no.keys:
                    if isinstance(k, ast.Name) and k.id in consts:
                        fora.add(consts[k.id])
    return fora


def _campos_dos_marcadores_divergentes(done, fail, refeito, politica):
    fora = []
    for campos, chaves, nome in ((_CAMPOS_NOVOS_DO_DONE, done, u"conclusao"),
                                 (_CAMPOS_NOVOS_DO_FAIL, fail, u"falha")):
        for c in campos:
            diz = (u"( %s )" % c) in (politica or u"")
            if diz is not (c in chaves):
                fora.append(u"%s.%s: o codigo %s, e a Politica %s" % (
                    nome, c, u"grava" if c in chaves else u"NAO grava",
                    u"diz" if diz else u"nao diz"))
    diz = _MARCA_REFEITO_POS in (politica or u"")
    if diz is not refeito:
        fora.append(u"a origem refeito_pos %s no codigo, e a Politica %s" % (
            u"existe" if refeito else u"NAO existe",
            u"diz" if diz else u"nao diz"))
    return fora


_MARCA_VIDEO = u"radai_recon3d_atos.log"


def _video_divergente(src_recon, termos, politica):
    grava = (u"MediaRecorder" in (src_recon or u"")
             and (u'ARQUIVO_ATOS_DO_VIDEO = "%s"' % _MARCA_VIDEO)
             in (src_recon or u""))
    fora = []
    for nome, txt in ((u"Termos", termos), (u"Politica", politica)):
        diz = _MARCA_VIDEO in (txt or u"") and u"rosto" in (txt or u"")
        if diz is not grava:
            fora.append(u"a gravacao do visor 3D %s no codigo, e %s %s" % (
                u"existe" if grava else u"NAO existe", nome,
                u"diz" if diz else u"nao diz"))
    return fora


_MARCA_TPS = u"TPS_DESTINO"
_MARCA_MONACO = u"Implicit VR Little Endian"
_MARCA_ASCII = u"sai em ASCII, sem acento"


def _tps_divergente(src_engine, termos):
    fora = []
    escolhe = (u'TPS_MONACO = "monaco"' in (src_engine or u"")
               and u'"TPS_DESTINO"' in (src_engine or u""))
    implicito = u"ImplicitVRLittleEndian" in _fonte_da_funcao(
        src_engine, "acabamento_para_o_tps")
    ascii_todos = u"_texto_ascii_no_dataset(ds" in _fonte_da_funcao(
        src_engine, "acabamento_para_o_tps").split(u"if tps ==")[0]
    for fato, marca in ((escolhe, _MARCA_TPS), (implicito, _MARCA_MONACO),
                        (ascii_todos, _MARCA_ASCII)):
        diz = marca in (termos or u"")
        if diz is not fato:
            fora.append(u"«%s»: o codigo %s, e os Termos %s" % (
                marca, u"o faz" if fato else u"NAO o faz",
                u"dizem" if diz else u"nao dizem"))
    return fora


_MARCA_INICIAR = (u"o diálogo do «Iniciar», em toda tela que tem a fila, e a "
                  u"folha do turno da noite repetem")


def _iniciar_divergente(src_review, src_batch, termos):
    frase = u"ApprovalStatus = UNAPPROVED" in (src_review or u"")
    folha = u'"fronteira": tag_da_fronteira()' in (src_batch or u"")
    fato = frase and folha
    diz = _MARCA_INICIAR in (termos or u"")
    if diz is not fato:
        return [u"a frase UNAPPROVED %s no dialogo e na folha, e os Termos %s"
                % (u"esta" if fato else u"NAO esta",
                   u"dizem" if diz else u"nao dizem")]
    return []


def teste_o_que_a_v84_fecha_na_17():
    secao(u"documentos 1.7, o fechamento: cache, niveis no OAR, indice 26, "
          u"marcadores, video, TPS e o dialogo do Iniciar")
    import radai_consent as CS
    import radai_credits as CR
    termos = _plano(CS.TERMOS)
    politica = _plano(CS.POLITICA)
    creditos = _plano(CR.pagina())
    notice = ler(u"NOTICE")
    src = dict((n, ler(u"app/" + n)) for n in (
        "radai_cache_tasks.py", "radai_sets.py", "radai_hnlnl.py",
        "engine.py", "radai_records.py", "radai_recon3d_screen.py",
        "radai_review.py", "radai_batch.py"))
    un = ler(u"installer/UNINSTALL.ps1")

    div = _trocas_divergentes(CS.IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO,
                              CS.RESSELAGENS_ANTES_DA_PUBLICACAO,
                              CS.IMPRESSOES_PUBLICADAS)
    checar(u"cada resselagem de uma versao nao publicada esta no dado, com o "
           u"que entrou no texto (%s)" % u", ".join(
               u"%s: %d" % (v, len(l)) for v, l in sorted(
                   CS.IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO.items())),
           not div, u" | ".join(div))
    checar(u"  isca: uma resselagem a mais no contador, sem a troca no dado: "
           u"reprova", bool(_trocas_divergentes(
               CS.IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO,
               dict(CS.RESSELAGENS_ANTES_DA_PUBLICACAO, **{
                   CS.VERSAO_DOCS: CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get(
                       CS.VERSAO_DOCS, 0) + 1}),
               CS.IMPRESSOES_PUBLICADAS)))
    checar(u"  isca: a impressao em vigor listada como trocada: reprova",
           bool(_trocas_divergentes(
               {CS.VERSAO_DOCS: ((CS.IMPRESSOES_PUBLICADAS[CS.VERSAO_DOCS][:12],
                                  u"x" * 30),)},
               {CS.VERSAO_DOCS: 1}, CS.IMPRESSOES_PUBLICADAS)))

    fc = _fatos_do_cache(src["radai_cache_tasks.py"], un)
    checar(u"  (li do codigo: o cache em %s, %s dias, %s GB)"
           % (fc["pasta"], fc["ttl"], fc["teto"]),
           fc["existe"] and bool(fc["pasta"]) and bool(fc["ttl"]))
    div = _cache_divergente(fc, politica)
    checar(u"o cache por tarefa: onde mora, o que guarda, a recusa, o prazo e "
           u"o teto sao os do codigo, e a Politica (secoes 3 e 6) diz",
           not div, u" | ".join(div))
    checar(u"  isca: 30 dias no codigo: reprova",
           bool(_cache_divergente(dict(fc, ttl=30), politica)))
    checar(u"  isca: o cache sem a recusa de nuvem: reprova",
           bool(_cache_divergente(dict(fc, nuvem=False), politica)))
    checar(u"  isca: o modulo do cache some, com a Politica de hoje: reprova",
           bool(_cache_divergente(_fatos_do_cache(u"", un), politica)))
    checar(u"  isca: a Politica cala a variavel da pasta: reprova",
           bool(_cache_divergente(fc, politica.replace(
               u"RADAI_CACHE_TASKS_DIR", u"X"))))

    v_sets = _valores_do_modulo(src["radai_sets.py"])
    v_hn = _valores_do_modulo(src["radai_hnlnl.py"])
    fn = _fatos_dos_niveis(v_sets, v_hn)
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % kv for kv in sorted(fn.items())),
        bool(v_sets.get("PERMITIDOS_NO_OAR")) and bool(
            v_hn.get("MAPA_DOS_PESOS")))
    div = _niveis_divergentes(fn, termos, creditos, notice)
    checar(u"os niveis cervicais: os nomes de Gregoire, e no OAR so a uniao "
           u"e a parotida do VIII — o codigo, os Termos, os Creditos e o "
           u"NOTICE", not div, u" | ".join(div))
    _sem_uniao = dict(v_sets, PERMITIDOS_NO_OAR=frozenset(
        set(v_sets.get("PERMITIDOS_NO_OAR") or ()) - {"LNL_UNION"}))
    checar(u"  isca: a uniao sai do OAR no codigo, com os textos de hoje: "
           u"reprova", bool(_niveis_divergentes(
               _fatos_dos_niveis(_sem_uniao, v_hn), termos, creditos,
               notice)))
    checar(u"  isca: um Lvl_ entra no OAR: reprova",
           bool(_niveis_divergentes(dict(fn, nivel_no_oar=True), termos,
                                    creditos, notice)))
    checar(u"  isca: o mapa dos nomes deixa de valer: reprova",
           bool(_niveis_divergentes(
               _fatos_dos_niveis(v_sets, dict(v_hn, ORDEM_CONFERIDA=False)),
               termos, creditos, notice)))
    checar(u"  isca: os Creditos voltam a dizer o nome neutro: reprova",
           bool(_niveis_divergentes(fn, termos, creditos + u" os vinte "
                                    u"níveis saem com nome neutro", notice)))

    v_eng = _valores_do_modulo(src["engine.py"])
    f26 = _fatos_do_indice_26(v_eng, src["engine.py"])
    div = _indice_26_divergente(f26, termos, notice)
    checar(u"o indice 26 fundido ao sacro, no completo e no cru (medido: "
           u"%s) — o codigo, os Termos e o NOTICE" % f26, not div,
           u" | ".join(div))
    checar(u"  isca: o passo sai do ORDEM_DO_FULL: reprova",
           bool(_indice_26_divergente(dict(f26, full=False), termos,
                                      notice)))
    checar(u"  isca: o cru deixa de fundir, no fonte do build_rtstruct: "
           u"reprova", bool(_indice_26_divergente(_fatos_do_indice_26(
               v_eng, src["engine.py"].replace(
                   u"vista_com_indice_26_fundido(masks)", u"(masks)")),
               termos, notice)))

    fontes = _fontes_do_descarte()
    done = _chaves_do_campos_do_done(src["radai_records.py"])
    fail = _chaves_do_fail(fontes)
    refeito = u'"refeito_pos"' in fontes["batch"]
    checar(u"  (li do codigo: %d campo(s) do campos_do_done e %d do fail)"
           % (len(done), len(fail)),
           u"faltou" in done and u"assinatura" in fail)
    div = _campos_dos_marcadores_divergentes(done, fail, refeito, politica)
    checar(u"os campos novos dos marcadores de conclusao e de falha: o "
           u"codigo e a Politica (secao 3), nos dois sentidos", not div,
           u" | ".join(div))
    checar(u"  isca: o done deixa de gravar receita_pos: reprova",
           bool(_campos_dos_marcadores_divergentes(
               done - {u"receita_pos"}, fail, refeito, politica)))
    checar(u"  isca: o fail deixa de gravar o turno (no fonte): reprova",
           bool(_campos_dos_marcadores_divergentes(
               done, _chaves_do_fail(dict(fontes, watcher=fontes[
                   "watcher"].replace(u'"turno": STATE.get("turno_id")',
                                      u'"x": 0'))),
               refeito, politica)))
    checar(u"  isca: a Politica cala a assinatura: reprova",
           bool(_campos_dos_marcadores_divergentes(
               done, fail, refeito, politica.replace(u"( assinatura )",
                                                     u"X"))))

    div = _video_divergente(src["radai_recon3d_screen.py"], termos, politica)
    checar(u"a gravacao do visor das Reconstrucoes 3D: o codigo, os Termos "
           u"(4.4) e a Politica (secao 5)", not div, u" | ".join(div))
    checar(u"  isca: a Politica cala o registro do ato: reprova",
           bool(_video_divergente(src["radai_recon3d_screen.py"], termos,
                                  politica.replace(_MARCA_VIDEO, u"X"))))
    checar(u"  isca: o codigo sem a gravacao, com os textos de hoje: "
           u"reprova", bool(_video_divergente(u"", termos, politica)))

    div = _tps_divergente(src["engine.py"], termos)
    checar(u"o TPS de destino: a chave, o Monaco e o ASCII para todo TPS — o "
           u"codigo e os Termos (1.5)", not div, u" | ".join(div))
    checar(u"  isca: o Monaco sem Implicit VR no codigo: reprova",
           bool(_tps_divergente(src["engine.py"].replace(
               u"ImplicitVRLittleEndian", u"ExplicitVRLittleEndian"),
               termos)))

    div = _iniciar_divergente(src["radai_review.py"], src["radai_batch.py"],
                              termos)
    checar(u"a frase UNAPPROVED no dialogo do Iniciar e na folha do turno: "
           u"o codigo e os Termos", not div, u" | ".join(div))
    checar(u"  isca: a folha do turno sem a frase: reprova",
           bool(_iniciar_divergente(src["radai_review.py"],
                                    src["radai_batch.py"].replace(
                                        u'"fronteira": tag_da_fronteira()',
                                        u'"fronteira": u""'), termos)))


_MARCA_FILA_SEM_PHI = u"Sem nome de paciente e sem caminho"
_MARCA_FILA_INDICE = u"o caminho da pasta da série, o rótulo que a barra mostra"
_MARCA_FILA_DESINSTALA = u"a fila ( C:\\RADIOTERAPIA_AI\\fila )"


def _fatos_da_fila(src_fila, src_un):
    v = _valores_do_modulo(src_fila)
    arq = set(v.get("CAMPOS_DO_ARQUIVO") or ())
    ind = set(v.get("CAMPOS_DO_INDICE") or ())
    pasta = _fonte_da_funcao(src_fila, "pasta_da_fila")
    return {"arquivo": v.get("NOME_DO_ARQUIVO"),
            "indice": v.get("NOME_DO_INDICE"),
            "variavel": v.get("VARIAVEL_DA_PASTA"),
            "no_c": u'"RADIOTERAPIA_AI", u"fila"' in pasta,
            "com_acervo": u"RADAI_CALIB_DIR" in pasta,
            "sem_phi": not ({"pasta", "rotulo"} & arq),
            "phi_no_indice": {"pasta", "rotulo"} <= ind,
            "uid_inteiro": "uid" in arq,
            "desinstala": u"fila" in (src_un or u"").lower()}


def _fila_divergente(f, politica):
    fora = []
    if not (f["arquivo"] and f["indice"] and f["variavel"]):
        return [u"nao li a fila do codigo"]
    for frase, quando in (
            (u"C:\\RADIOTERAPIA_AI\\fila\\%s" % f["arquivo"], f["no_c"]),
            (f["variavel"], True),
            (u"RADAI_CALIB_DIR", f["com_acervo"]),
            (u"( %s )" % f["indice"], True),
            (_MARCA_FILA_SEM_PHI, f["sem_phi"]),
            (_MARCA_FILA_INDICE, f["phi_no_indice"]),
            (u"o UID inteiro da série", f["uid_inteiro"]),
            (_MARCA_FILA_DESINSTALA, not f["desinstala"])):
        if bool(quando) is not (frase in politica):
            fora.append(u"«%s»: o codigo %s, e a Politica %s" % (
                frase, u"pede" if quando else u"NAO pede",
                u"diz" if frase in politica else u"nao diz"))
    return fora


def _numero_do_teto_do_log(src):
    m = re.search(r"(?m)^TETO_DO_LOG\s*=\s*(\d+)\s*\*\s*1024\s*$", src or u"")
    return int(m.group(1)) if m else None


def _abertura_divergente(v_car, src_lanc, v_pulso, politica, termos):
    fora = []
    v_lanc = _valores_do_modulo(src_lanc)
    for nome in (v_car.get("NOME_DA_PAGINA"), v_car.get("NOME_DO_ESTADO")):
        alvo = (nome or u"\x00").replace(u"%d", u"<porta>")
        if alvo not in politica:
            fora.append(u"a Politica nao cita %s" % alvo)
    log = v_lanc.get("NOME_DO_LOG")
    if not log or (u"%s , na pasta do programa" % log) not in politica:
        fora.append(u"a Politica nao diz onde mora o %s" % log)
    kb = _numero_do_teto_do_log(src_lanc)
    if not kb or (u"Passando de %d kB" % kb) not in politica:
        fora.append(u"o teto do registro do lancador (%s kB) nao e o da "
                    u"Politica" % kb)
    graca = v_pulso.get("GRACA_DO_FECHAR_S")
    tol = v_pulso.get("TOLERANCIA_S")
    for frase in (u"nenhuma outra responde em %s segundos" % _num_pt(graca),
                  u"depois de %s minutos sem sinal" % _POR_EXTENSO_MIN.get(
                      int((tol or 0) // 60), u"\x00")):
        if frase not in termos:
            fora.append(u"os Termos (1.5) nao dizem «%s»" % frase)
    return fora


_POR_EXTENSO_MIN = {1: u"um", 2: u"dois", 3: u"três", 5: u"cinco"}


def _aplicador_divergente(src_ap, src_tela, termos, politica):
    fora = []
    v = _valores_do_modulo(src_ap)
    ato = u" ".join(str(v.get("FRASE_DO_ATO") or u"").split())
    corpo = ato.split(u"é um ", 1)[1].rstrip(u".") if u"é um " in ato else u""
    if not corpo or corpo not in termos:
        fora.append(u"os Termos (4.2) nao trazem o ato do aplicador como o "
                    u"codigo o exige")
    curva = u" ".join(str(v.get("FRASE_DA_CURVA") or u"").split())
    for trecho in (u"conferidas por radiografia",
                   u"nenhuma parada ativa ficará dentro da curva",
                   u"instruções de uso do cateter e do afterloader serão "
                   u"conferidas"):
        if trecho not in curva:
            fora.append(u"o segundo ato do codigo nao diz mais «%s»" % trecho)
        elif trecho not in termos:
            fora.append(u"os Termos nao trazem o segundo ato: «%s»" % trecho)
    rota = u"/api/bolus/aplicador/exportar" in _rotas_servidas(src_tela)
    zipa = u"zipfile.ZipFile" in _fonte_da_funcao(src_ap, "pacote")
    atos = _valores_do_modulo(src_tela).get("ARQUIVO_ATOS")
    for frase, quando, onde, txt in (
            (u"O aplicador de superfície para braquiterapia", rota,
             u"os Termos", termos),
            (u"O aplicador de braquiterapia do 3D Printed Bolus", rota,
             u"a Politica", politica),
            (u"um .zip com o STL do aplicador e a ficha", rota and zipa,
             u"a Politica", politica),
            (u"Sai um .zip com o STL e uma ficha", rota and zipa,
             u"os Termos", termos),
            (u"raio padrão de %s mm" % _num_pt(v.get("RAIO_PADRAO_MM")), rota,
             u"os Termos", termos),
            (u"folga menor que %s mm" % _num_pt(v.get("FOLGA_SEM_ALERTA_MM")),
             rota, u"os Termos", termos)):
        if bool(quando) is not (frase in txt):
            fora.append(u"%s %s «%s», e o codigo %s" % (
                onde, u"diz" if frase in txt else u"nao diz", frase,
                u"exporta" if quando else u"NAO exporta"))
    if rota and (not atos or atos not in _trecho(
            politica, u"O aplicador de braquiterapia do 3D Printed Bolus",
            u"O pacote do registro de casos")):
        fora.append(u"a Politica nao diz que o aplicador registra o ato em %s"
                    % atos)
    selo = b"DRAFT UNAPPROVED" in (v.get("CABECALHO_STL") or b"")
    if rota and selo is not (u"DRAFT UNAPPROVED" in _trecho(
            politica, u"O aplicador de braquiterapia do 3D Printed Bolus",
            u"O pacote do registro de casos")):
        fora.append(u"o cabecalho do STL do aplicador e o da Politica "
                    u"divergem")
    return fora


def _bag_oar_divergente(v_cons, v_sets, termos):
    fora = []
    par = _trecho(termos, u"A cavidade intestinal do entregue",
                  u"fica no completo.")
    if not par:
        return [u"os Termos nao descrevem a Bag_Bowel_OAR_ai"]
    for frase in (
            u"tira também %s mm em volta" % _num_pt(
                v_cons.get("FOLGA_DOS_VIZINHOS_DA_BAG_MM")),
            u"suavizada em %s mm" % _num_pt(v_cons.get("SUAVIZACAO_BAG_OAR_MM")),
            u"o psoas com %s mm a mais para trás" % _num_pt(
                v_cons.get("RECUO_ATRAS_DO_PSOAS_MM")),
            u"passa de %s mm da parede anterior" % _num_pt(
                v_cons.get("FAIXA_ANTERIOR_CAUDAL_MM"))):
        if frase not in par:
            fora.append(u"o paragrafo da Bag_Bowel_OAR_ai nao diz «%s»"
                        % frase)
    porta = bool(v_cons.get("VEIA_PORTA"))
    if porta is not (u"A veia porta fica fora de toda conta" in par):
        fora.append(u"a veia porta: o codigo %s, e o paragrafo %s" % (
            u"a deixa fora" if porta else u"NAO a deixa fora",
            u"diz" if u"veia porta" in par else u"nao diz"))
    oar = set(v_sets.get("PERMITIDOS_NO_OAR") or ())
    so_a_oar = "bag_bowel_oar" in oar and "bag_bowel" not in oar
    if so_a_oar is not (u"só a Bag_Bowel_OAR_ai vai ao entregue" in termos):
        fora.append(u"no OAR do codigo: bag_bowel_oar=%s, bag_bowel=%s; os "
                    u"Termos nao concordam" % ("bag_bowel_oar" in oar,
                                               "bag_bowel" in oar))
    return fora


_MARCA_CAROTIDA = (u"carótidas ( A_Carotid_ai ) ficam como estrutura própria "
                   u"só no completo")
_MARCA_TRAVA_PESCOCO = u"só roda com o pescoço confirmado pela anatomia"
_MARCA_CRANIO_NAO_CONFIRMA = u"o crânio não confirma o pescoço"
_MARCA_VIGIA_PELO_CRANIO = (u"pela mandíbula na faixa do C1 ao C4, ou pelo "
                            u"crânio acima do C1")


def _pescoco_e_carotida_divergentes(v_eng, src_eng, v_sets, termos):
    fora = []
    for frase in (u"com %s cm³ cada" % _num_pt(
                      v_eng.get("VOLUME_MINIMO_VERTEBRA_CERVICAL_CM3")),
                  u"com %s cm³ ou mais" % _num_pt(
                      v_eng.get("VOLUME_MINIMO_DA_MANDIBULA_CM3"))):
        if frase not in termos:
            fora.append(u"os Termos (4) nao dizem o gatilho do pescoco: «%s»"
                        % frase)
    cranio = v_eng.get("VOLUME_MINIMO_DO_CRANIO_ACIMA_DO_C1_CM3")
    frase_cr = (u"o crânio acima do topo dessa faixa, com %s cm³ ou mais"
                % _num_pt(cranio))
    if cranio:
        if frase_cr not in termos:
            fora.append(u"o motor confirma o pescoco tambem pelo cranio acima "
                        u"do C1, e os Termos (4) nao dizem «%s»" % frase_cr)
        if _MARCA_CRANIO_NAO_CONFIRMA in termos:
            fora.append(u"o motor confirma pelo cranio, e os Termos dizem que "
                        u"o cranio nao confirma o pescoco")
        if _MARCA_VIGIA_PELO_CRANIO not in termos:
            fora.append(u"o que o vigia roda nao diz o pescoco pelo cranio")
    elif u"o crânio acima do topo dessa faixa" in termos:
        fora.append(u"o motor nao confirma pelo cranio, e os Termos dizem")
    fora_do_oar = "carotids" not in set(v_sets.get("PERMITIDOS_NO_OAR") or ())
    if fora_do_oar is not (_MARCA_CAROTIDA in termos):
        fora.append(u"as carotidas %s no OAR do codigo, e os Termos %s" % (
            u"NAO estao" if fora_do_oar else u"estao",
            u"dizem que nao" if _MARCA_CAROTIDA in termos else u"calam"))
    trava = bool(re.search(r'"headneck_muscles"\s*:\s*"pescoco"', src_eng or u""))
    if trava is not (_MARCA_TRAVA_PESCOCO in termos):
        fora.append(u"a trava do pescoco na task dos constritores %s, e os "
                    u"Termos %s" % (u"existe" if trava else u"NAO existe",
                                    u"dizem" if _MARCA_TRAVA_PESCOCO in termos
                                    else u"nao dizem"))
    return fora


_MARCA_PULADA = u"Quando uma tarefa não cabe na memória."
_MARCA_OAR_ANTES = u"o entregue é gravado antes do completo"


def _memoria_divergente(f, termos, politica):
    fora = []
    if f["pula"] is not (_MARCA_PULADA in termos):
        fora.append(u"a task que nao cabe %s pulada no motor, e os Termos "
                    u"(1.4) %s" % (u"e" if f["pula"] else u"NAO e",
                                   u"dizem" if _MARCA_PULADA in termos
                                   else u"nao dizem"))
    par = _trecho(termos, _MARCA_PULADA, u"O arquivo de configuração")
    if f["pula"]:
        for frase in (u"A cada %s minutos" % _num_pt((f["relogio_s"] or 0)
                                                    / 60.0),
                      u"mais de %s hora" % _num_pt((f["intervalo_s"] or 0)
                                                   / 3600.0)):
            if frase not in par:
                fora.append(u"o paragrafo da memoria nao diz «%s»" % frase)
    if f["oar_antes"] is not (_MARCA_OAR_ANTES in par):
        fora.append(u"o OAR %s gravado antes do FULL, e os Termos %s" % (
            u"e" if f["oar_antes"] else u"NAO e",
            u"dizem" if _MARCA_OAR_ANTES in par else u"nao dizem"))
    for chave in ("tasks_puladas_por_memoria", "parcial"):
        grava = f["done"].get(chave, False)
        diz = (u"( %s )" % chave) in politica
        if grava is not diz:
            fora.append(u"done.%s: o vigia %s, e a Politica %s" % (
                chave, u"grava" if grava else u"NAO grava",
                u"diz" if diz else u"nao diz"))
    return fora


def _fatos_da_memoria(src_eng, src_out, src_vig, v_batch, v_fila):
    return {"pula": u"tasks_puladas_por_memoria" in (src_eng or u"")
                    and u"pulada_por_memoria(" in (src_eng or u""),
            "relogio_s": v_batch.get("INTERVALO_DO_RELOGIO_S"),
            "intervalo_s": v_fila.get("INTERVALO_DO_COMPLEMENTO_S"),
            "oar_antes": u'"conjunto": "full"' in (src_out or u""),
            "done": dict((k, (u'done["%s"]' % k) in (src_vig or u""))
                         for k in ("tasks_puladas_por_memoria", "parcial"))}


_MARCAS_DA_DEMO_NOS_DOCUMENTOS = (u"demonstração", u"DEMO", u"LCTSC",
                                  u"LIDC-IDRI", u"RIRE")


_MARCA_OV_SO_LE = (u"Ao abrir a folha, o programa só confere que as pastas "
                    u"existem e leem, sem gravar nelas")
_MARCA_OV_ESCRITA_AO_SALVAR = (u"Ao salvar, o programa confere a leitura e a "
                               u"escrita de todas as pastas")
_MARCA_OV_ROOT_NO_SEGUINTE = (u"Trocar ROOT ou ROOTS com o turno aberto vale a "
                              u"partir do turno seguinte")


def _fatos_da_folha_do_turno(src_batch, src_vig):
    escrita = _fonte_da_funcao_js(src_batch, "_ovConferirEscrita")
    return {"so_le": u"/api/lote/conferir_pasta" in (src_batch or u"")
                     and u"def conferir_pasta_sem_gravar(" in (src_batch or u""),
            "escrita_ao_salvar": u"/api/config/testar" in escrita
                                 and u"_ovConferirEscrita(v).then(" in (
                                     src_batch or u""),
            "root_no_seguinte": u"ROOT_DO_TURNO" in (src_vig or u"")
                                and u"root_no_proximo_turno" in (src_vig
                                                                 or u"")}


def _folha_do_turno_divergente(f, termos):
    fora = []
    for chave, marca in (("so_le", _MARCA_OV_SO_LE),
                         ("escrita_ao_salvar", _MARCA_OV_ESCRITA_AO_SALVAR),
                         ("root_no_seguinte", _MARCA_OV_ROOT_NO_SEGUINTE)):
        if bool(f[chave]) is not (marca in termos):
            fora.append(u"%s: o codigo %s, e os Termos (4.3) %s" % (
                chave, u"faz" if f[chave] else u"NAO faz",
                u"dizem" if marca in termos else u"nao dizem"))
    if u"Essa conferência é feita ao abrir a folha" in termos:
        fora.append(u"os Termos ainda dizem que a pasta e testada ao abrir")
    return fora


def _demo_nos_documentos(textos):
    return [u"%s cita «%s»" % (n, m) for n, t in textos
            for m in _MARCAS_DA_DEMO_NOS_DOCUMENTOS if m in (t or u"")]


def teste_o_que_a_v85_muda_na_18():
    secao(u"documentos 1.8: a fila em disco, a abertura, a demo que saiu, o "
          u"DicomBridge, o aplicador, os conjuntos e a memoria")
    import radai_consent as CS
    import radai_credits as CR
    termos = _plano(CS.TERMOS)
    politica = _plano(CS.POLITICA)
    creditos = _plano(CR.pagina())
    pontos = dict((c, t + u" " + d) for (c, t, d) in CS.PONTOS)
    checar(u"a versao dos documentos e a 1.8 ou posterior, de outubro de 2026",
           tuple(int(x) for x in CS.VERSAO_DOCS.split(u".")) >= (1, 8)
           and CS.DATA_DOCS.startswith(u"2026-10"),
           u"%s %s" % (CS.VERSAO_DOCS, CS.DATA_DOCS))

    un = ler(u"installer/UNINSTALL.ps1")
    ff = _fatos_da_fila(ler(u"app/radai_queue_state.py"), un)
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % kv for kv in sorted(ff.items())), bool(ff["arquivo"]))
    div = _fila_divergente(ff, politica)
    checar(u"a fila em disco: onde mora, o que o arquivo leva e o que fica no "
           u"indice do acervo — o codigo e a Politica (secoes 3 e 6)", not div,
           u" | ".join(div))
    checar(u"  isca: a pasta da serie passa a ir ao arquivo da fila: reprova",
           bool(_fila_divergente(dict(ff, sem_phi=False), politica)))
    checar(u"  isca: o desinstalador passa a levar a fila: reprova",
           bool(_fila_divergente(dict(ff, desinstala=True), politica)))
    checar(u"  isca: a Politica cala a variavel da pasta: reprova",
           bool(_fila_divergente(ff, politica.replace(u"RADAI_FILA_DIR",
                                                      u"X"))))

    v_car = _valores_do_modulo(ler(u"app/radai_carregando.py"))
    src_lanc = ler(u"app/radai_lancador.py")
    v_pulso = _valores_do_modulo(ler(u"app/radai_pulso.py"))
    div = _abertura_divergente(v_car, src_lanc, v_pulso, politica, termos)
    checar(u"a pagina de carregamento, o registro do lancador e o fechar em "
           u"%s s: o codigo, a Politica e os Termos" % v_pulso.get(
               "GRACA_DO_FECHAR_S"), not div, u" | ".join(div))
    checar(u"  isca: a graca do fechar em 30 s no codigo: reprova",
           bool(_abertura_divergente(v_car, src_lanc,
                                     dict(v_pulso, GRACA_DO_FECHAR_S=30.0),
                                     politica, termos)))
    checar(u"  isca: o teto do registro do lancador muda: reprova",
           bool(_abertura_divergente(v_car, src_lanc.replace(
               u"TETO_DO_LOG = 512 * 1024", u"TETO_DO_LOG = 256 * 1024"),
               v_pulso, politica, termos)))
    checar(u"  isca: a pagina de carregamento com outro nome: reprova",
           bool(_abertura_divergente(dict(v_car,
                                          NOME_DA_PAGINA=u"radai_x_%d.html"),
                                     src_lanc, v_pulso, politica, termos)))

    textos = ((u"Termos", termos), (u"Politica", politica),
              (u"Creditos", creditos))
    demo = _demo_nos_documentos(textos)
    usam = [n for n in _componentes.nomes("app") if n.endswith(u".py")
            and n not in (u"radai_demo.py", u"radai_phrases.py")
            and _importa(ler(u"app/" + n), "radai_demo")]
    checar(u"a demo saiu: nenhum modulo do app a usa, e nenhum documento a "
           u"descreve", not demo and not usam, u" | ".join(demo + usam))
    checar(u"  isca: os Termos voltam a citar as series de demonstracao: "
           u"reprova", bool(_demo_nos_documentos(
               ((u"Termos", termos + u" séries de demonstração"),))))

    v_img = _valores_do_modulo(ler(u"app/radai_image.py"))
    faltam = []
    for nome, txt in ((u"Termos", termos), (u"Politica", politica),
                      (u"ponto exportar", pontos.get(u"exportar", u""))):
        for k in ("DESCONHECIDO", "PREFIXO_DO_ID", "NOME_DO_LEIA_ME"):
            alvo = v_img.get(k)
            if k == "PREFIXO_DO_ID" and alvo:
                alvo = alvo + u"-"
            if nome == u"ponto exportar" and k != "DESCONHECIDO":
                continue
            if not alvo or alvo not in txt:
                faltam.append(u"%s sem %s" % (nome, alvo))
    checar(u"a imagem sem dono: paciente %s, ID %s, %s — o codigo, os Termos "
           u"(4.5), a Politica e o ponto do aceite"
           % (v_img.get("DESCONHECIDO"), v_img.get("PREFIXO_DO_ID"),
              v_img.get("NOME_DO_LEIA_ME")), bool(v_img) and not faltam,
           u" | ".join(faltam))
    checar(u"  e os Termos dizem de quem e a atribuicao",
           u"Atribuir a série ao paciente certo é ato de quem a importa"
           in termos)

    src_tela = ler(u"app/radai_bolus_screen.py")
    src_ap = ler(u"app/radai_bolus_aplicador.py")
    div = _aplicador_divergente(src_ap, src_tela, termos, politica)
    checar(u"o aplicador de braquiterapia: os dois atos, o .zip com a ficha, "
           u"o registro do ato e os padroes — o codigo, os Termos (4.2) e a "
           u"Politica (secoes 3 e 5)", not div, u" | ".join(div))
    checar(u"  isca: o codigo sem a rota de exportacao, com os textos de "
           u"hoje: reprova", bool(_aplicador_divergente(
               src_ap, src_tela.replace(u"/api/bolus/aplicador/exportar",
                                        u"/api/x"), termos, politica)))
    checar(u"  isca: o ato muda no codigo: reprova",
           src_ap.count(u"haverá segunda TC") == 1
           and bool(_aplicador_divergente(src_ap.replace(
               u"haverá segunda TC", u"haverá uma TC"),
               src_tela, termos, politica)))
    checar(u"  isca: os Termos calam o segundo ato: reprova",
           bool(_aplicador_divergente(src_ap, src_tela, termos.replace(
               u"nenhuma parada ativa ficará dentro da curva", u"X"),
               politica)))

    v_cons = _valores_do_modulo(ler(u"app/radai_constructs.py"))
    v_sets = _valores_do_modulo(ler(u"app/radai_sets.py"))
    div = _bag_oar_divergente(v_cons, v_sets, termos)
    checar(u"a Bag_Bowel_OAR_ai: a receita e o lugar dela no OAR — o codigo e "
           u"os Termos (1.2)", not div, u" | ".join(div))
    checar(u"  isca: a suavizacao da bag em 10 mm no codigo: reprova",
           bool(_bag_oar_divergente(dict(v_cons, SUAVIZACAO_BAG_OAR_MM=10.0),
                                    v_sets, termos)))
    checar(u"  isca: a Bag_Bowel_ai de volta no OAR: reprova",
           bool(_bag_oar_divergente(v_cons, dict(
               v_sets, PERMITIDOS_NO_OAR=frozenset(
                   set(v_sets.get("PERMITIDOS_NO_OAR") or ())
                   | {"bag_bowel"})), termos)))

    src_eng = ler(u"app/engine.py")
    v_eng = _valores_do_modulo(src_eng)
    div = _pescoco_e_carotida_divergentes(v_eng, src_eng, v_sets, termos)
    checar(u"o pescoco pela mandibula (%s cm3), as carotidas so no FULL e a "
           u"trava dos constritores — o codigo e os Termos"
           % v_eng.get("VOLUME_MINIMO_DA_MANDIBULA_CM3"), not div,
           u" | ".join(div))
    checar(u"  isca: as carotidas de volta no OAR: reprova",
           bool(_pescoco_e_carotida_divergentes(v_eng, src_eng, dict(
               v_sets, PERMITIDOS_NO_OAR=frozenset(
                   set(v_sets.get("PERMITIDOS_NO_OAR") or ())
                   | {"carotids"})), termos)))
    checar(u"  isca: outro piso da mandibula: reprova",
           bool(_pescoco_e_carotida_divergentes(dict(
               v_eng, VOLUME_MINIMO_DA_MANDIBULA_CM3=60.0), src_eng, v_sets,
               termos)))
    checar(u"  (li do motor o piso do cranio acima do C1: %s cm3)"
           % v_eng.get("VOLUME_MINIMO_DO_CRANIO_ACIMA_DO_C1_CM3"),
           bool(v_eng.get("VOLUME_MINIMO_DO_CRANIO_ACIMA_DO_C1_CM3")))
    checar(u"  isca: outro piso do cranio acima do C1: reprova",
           bool(_pescoco_e_carotida_divergentes(dict(
               v_eng, VOLUME_MINIMO_DO_CRANIO_ACIMA_DO_C1_CM3=60.0), src_eng,
               v_sets, termos)))
    checar(u"  isca: os Termos de antes (o cranio nao confirma): reprova",
           bool(_pescoco_e_carotida_divergentes(
               v_eng, src_eng, v_sets, termos + u" — acima dela o osso é "
               u"crânio, e " + _MARCA_CRANIO_NAO_CONFIRMA)))
    checar(u"  isca: o motor sem o caminho do cranio, com os Termos de hoje: "
           u"reprova", bool(_pescoco_e_carotida_divergentes(
               dict((k, x) for k, x in v_eng.items()
                    if k != "VOLUME_MINIMO_DO_CRANIO_ACIMA_DO_C1_CM3"),
               src_eng, v_sets, termos)))
    checar(u"  isca: a trava dos constritores sai do motor: reprova",
           bool(_pescoco_e_carotida_divergentes(
               v_eng, re.sub(r'"headneck_muscles"\s*:\s*"pescoco"', u"",
                             src_eng), v_sets, termos)))

    fm = _fatos_da_memoria(src_eng, ler(u"app/radai_output.py"),
                           ler(u"app/radai_watcher.py"),
                           _valores_do_modulo(ler(u"app/radai_batch.py")),
                           _valores_do_modulo(ler(u"app/radai_queue_state.py")))
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % kv for kv in sorted(fm.items())), fm["pula"])
    div = _memoria_divergente(fm, termos, politica)
    checar(u"a task que nao cabe na memoria, o complemento e o OAR antes do "
           u"FULL — o codigo, os Termos (1.4) e a Politica (secao 3)", not div,
           u" | ".join(div))
    checar(u"  isca: o relogio do complemento a cada 10 min: reprova",
           bool(_memoria_divergente(dict(fm, relogio_s=600.0), termos,
                                    politica)))
    checar(u"  isca: o done deixa de gravar o parcial: reprova",
           bool(_memoria_divergente(dict(fm, done=dict(fm["done"],
                                                       parcial=False)),
                                    termos, politica)))

    src_batch = ler(u"app/radai_batch.py")
    ft = _fatos_da_folha_do_turno(src_batch, ler(u"app/radai_watcher.py"))
    div = _folha_do_turno_divergente(ft, termos)
    checar(u"a folha do Overnight Run so le a pasta ao abrir, o teste de "
           u"escrita vai ao salvar e o ROOT trocado vale no turno seguinte "
           u"(medido: %s) — o codigo e os Termos (4.3)" % u", ".join(
               u"%s=%s" % kv for kv in sorted(ft.items())),
           all(ft.values()) and not div, u" | ".join(div))
    checar(u"  isca: a folha volta a testar a escrita ao abrir: reprova",
           bool(_folha_do_turno_divergente(dict(ft, so_le=False), termos)))
    checar(u"  isca: os Termos de antes (o teste ao abrir): reprova",
           bool(_folha_do_turno_divergente(ft, termos + u" Essa conferência "
                                           u"é feita ao abrir a folha")))
    checar(u"  isca: os Termos calam o ROOT do turno seguinte: reprova",
           bool(_folha_do_turno_divergente(ft, termos.replace(
               _MARCA_OV_ROOT_NO_SEGUINTE, u"X"))))

    atualiza = u"[switch]$SoEncerrar" in ler(u"packager/UPDATE.ps1")
    src_inst = ler(u"installer/INSTALL.ps1")
    instala = (u"function EncerrarOApp(" in src_inst
               and u"EncerrarOApp $DESTINO" in src_inst)
    div = _encerra_antes_divergente(atualiza, instala, termos)
    checar(u"o atualizador e o instalador do pacote encerram o app aberto "
           u"antes de copiar (medido: atualizador=%s, instalador=%s), e os "
           u"Termos (1.5) dizem" % (atualiza, instala), not div,
           u" | ".join(div))
    checar(u"  isca: o instalador deixa de encerrar, com os Termos de hoje: "
           u"reprova", bool(_encerra_antes_divergente(atualiza, False,
                                                       termos)))
    checar(u"  isca: os Termos de antes (so o atualizador): reprova",
           bool(_encerra_antes_divergente(atualiza, instala, termos.replace(
               _MARCA_ENCERRAM_OS_DOIS, _MARCA_ENCERRA_SO_O_ATUALIZADOR))))

    fontes_cod = _fontes_que_gravam()
    docs_html = (CS.POLITICA, CS.TERMOS)
    nomes, sem_codigo = _arquivos_nomeados_sem_codigo(docs_html, fontes_cod)
    checar(u"todo arquivo que a Politica e os Termos nomeiam (%d) aparece no "
           u"codigo que grava (%d fontes)" % (len(nomes), len(fontes_cod)),
           len(nomes) > 20 and len(fontes_cod) > 60 and not sem_codigo,
           u", ".join(sem_codigo))
    checar(u"  e ainda sabe aprovar: o acervo.jsonl e o fila.json sao achados",
           u"acervo.jsonl" in nomes and u"acervo.jsonl" not in sem_codigo
           and any(n.endswith(u"fila.json") for n in nomes))
    checar(u"  isca: a Politica com o corpus_recusa.jsonl de antes: reprova",
           u"corpus_recusa.jsonl" in _arquivos_nomeados_sem_codigo(
               (CS.POLITICA + u" <code>corpus_recusa.jsonl</code>",),
               fontes_cod)[1])
    checar(u"  isca: um arquivo com marcador de porta que ninguem grava: "
           u"reprova", u"radai_ninguem_<porta>.log"
           in _arquivos_nomeados_sem_codigo(
               (u"<code>radai_ninguem_&lt;porta&gt;.log</code>",),
               fontes_cod)[1])

    fb = _fatos_da_ponte(ler(u"app/radai_bridge.py"),
                         ler(u"app/radai_bridge_entrada.py"),
                         ler(u"app/radai_image.py"),
                         ler(u"app/radai_queue_state.py"))
    checar(u"  (li do codigo do DicomBridge: %s)" % u", ".join(
        u"%s=%s" % kv for kv in sorted(fb.items())),
        bool(fb["teto"] and fb["guardas"] and fb["validade_h"]))
    div = _ponte_divergente(fb, politica, termos)
    checar(u"o DicomBridge: a pasta pela metade, o teto e a conferencia das "
           u"copias do RTSTRUCT, a lista na memoria, a sessao da aba e o "
           u"sufixo do EXTERNO — o codigo, a Politica (3 e 5) e os Termos "
           u"(4.5)", not div, u" | ".join(div))
    for rotulo, fatos in (
            (u"o teto das copias passa a 9", dict(fb, teto=9)),
            (u"a pasta pela metade deixa de ser apagada",
             dict(fb, metade=False)),
            (u"a lista guarda 128 entregas", dict(fb, guardas=128)),
            (u"a lista vale 12 h", dict(fb, validade_h=12.0)),
            (u"o ID perde o sufixo", dict(fb, sufixo=False)),
            (u"a tela deixa de conferir as copias", dict(fb, confere=False)),
            (u"a aba deixa de guardar o bilhete", dict(fb, bilhete=False))):
        checar(u"  isca: %s: reprova" % rotulo,
               bool(_ponte_divergente(fatos, politica, termos)))

    src_n = ler(u"app/radai_nidus_screen.py")
    fn = _fatos_do_nidus(src_n)
    div = _nidus_divergente(fn, politica)
    checar(u"o Nidus RT guarda na aba sob a impressao do UID (%s caracteres), "
           u"com os campos de hoje — o codigo e a Politica (3)" % fn["digitos"],
           bool(fn["digitos"]) and not div, u" | ".join(div))
    checar(u"  isca: a impressao com 16 caracteres: reprova",
           bool(_nidus_divergente(dict(fn, digitos=16), politica)))
    checar(u"  isca: a chave volta a ser o bilhete do processo: reprova",
           bool(_nidus_divergente(dict(fn, pelo_uid=False), politica)))
    checar(u"  isca: a Politica cala a laje e o traco: reprova",
           bool(_nidus_divergente(fn, politica.replace(
               u"a laje, o inverter", u"X"))))

    nav = (u"radai_nidus_" in src_n, u"DC_SESSAO" in ler(u"app/radai_bridge.py"))
    diz_nav = (u"no Nidus RT, o desenho e os parâmetros" in politica,
               u"os identificadores dos cartões que ele pôs na fila"
               in politica)
    checar(u"o armazenamento da aba do Nidus RT e do DicomBridge (medido: %s): "
           u"a Politica diz" % (nav,), nav == diz_nav,
           u"codigo=%s, Politica=%s" % (nav, diz_nav))

    v_ver = _valores_do_modulo(ler(u"app/radai_version.py"))
    div = _contato_divergente(((u"Politica", CS.POLITICA),
                               (u"Termos", CS.TERMOS),
                               (u"aceite", CS.PAGINA_ACEITE)),
                              v_ver.get("URL_VERSOES"), CS.VERSAO_DOCS)
    checar(u"o contato dos documentos e o canal publicado (radioterapia.ai e "
           u"o relato privado do repositorio de %s), sem e-mail"
           % v_ver.get("URL_VERSOES"), not div, u" | ".join(div))
    doc_antes = (u'<a href="https://radioterapia.ai">x</a> '
                 u'<a href="%s/security">x</a>' % _DONO_RENOMEADO["antes"])
    url_depois = _DONO_RENOMEADO["depois"] + u"/releases"
    checar(u"  isca: o link do dono anterior com os documentos da versao "
           u"seguinte: reprova",
           bool(_contato_divergente(((u"Politica", doc_antes),), url_depois,
                                    u"2.1")))
    checar(u"  controle: o link do dono anterior com os documentos %s e o "
           u"repositorio sucessor: passa" % _DONO_RENOMEADO["versao_docs"],
           not _contato_divergente(((u"Politica", doc_antes),), url_depois,
                                   _DONO_RENOMEADO["versao_docs"]))
    checar(u"  isca: um e-mail pessoal de volta na Politica: reprova",
           bool(_contato_divergente(((u"Politica", CS.POLITICA
                                      + u" fulano" + u"@" + u"gmail.com"),),
                                    v_ver.get("URL_VERSOES"))))
    checar(u"  isca: o repositorio da versao muda e o link nao: reprova",
           bool(_contato_divergente(((u"Politica", CS.POLITICA),),
                                    u"https://github.com/outro/repo/releases",
                                    CS.VERSAO_DOCS)))

    src_ap = ler(u"app/radai_bolus_aplicador.py")
    fa = _fatos_do_aplicador(src_ap)
    div = _aplicador_face_divergente(fa, termos, politica)
    checar(u"o aplicador: a face de entrada e o raio padrao no registro do "
           u"ato e na ficha, e o padrao como campo (medido: %s) — o codigo, "
           u"os Termos (4.2) e a Politica (3)" % u", ".join(
               u"%s=%s" % kv for kv in sorted(fa.items())),
           not div, u" | ".join(div))
    checar(u"  isca: a linha do ato deixa de dizer a face: reprova",
           bool(_aplicador_face_divergente(_fatos_do_aplicador(
               src_ap.replace(u"pela face %s", u"X")), termos, politica)))
    checar(u"  isca: os Termos calam a face da ficha: reprova",
           bool(_aplicador_face_divergente(fa, termos.replace(
               _MARCA_FACE_NA_FICHA, u"X"), politica)))
    checar(u"  isca: o padrao volta a ser fixo: reprova",
           bool(_aplicador_face_divergente(dict(fa, padrao_campo=False),
                                           termos, politica)))
    checar(u"  (li do aplicador: o padrao so sobe = %s)" % fa.get("so_sobe"),
           fa.get("so_sobe") is True)
    checar(u"  isca: o padrao volta a descer ate o piso no codigo, com os "
           u"Termos de hoje: reprova", bool(_aplicador_face_divergente(
               _fatos_do_aplicador(src_ap.replace(
                   u"pedido < RAIO_PADRAO_MM", u"pedido < piso")),
               termos, politica)))
    checar(u"  isca: os Termos de antes (o padrao desce ate o piso): reprova",
           bool(_aplicador_face_divergente(fa, termos + u" o físico pode "
                                           u"subi-lo " + _MARCA_PADRAO_DESCE,
                                           politica)))
    checar(u"  isca: os Termos calam a curva sempre amarela abaixo de 35 mm: "
           u"reprova", bool(_aplicador_face_divergente(fa, termos.replace(
               u"a curva abaixo de 35 mm é sempre amarela", u"X"), politica)))

    v_eng = _valores_do_modulo(ler(u"app/engine.py"))
    div = _faixa_da_mandibula_divergente(v_eng, termos)
    checar(u"a mandibula do pescoco e medida so na faixa do %s ao %s — o "
           u"motor e os Termos (4)" % (
               (v_eng.get("TOPO_DA_FAIXA_DA_MANDIBULA") or (u"?",))[0],
               v_eng.get("FIM_DA_FAIXA_DA_MANDIBULA")), not div,
           u" | ".join(div))
    checar(u"  isca: a faixa vai ao C5 no motor: reprova",
           bool(_faixa_da_mandibula_divergente(dict(
               v_eng, FIM_DA_FAIXA_DA_MANDIBULA=u"vertebrae_C5"), termos)))
    checar(u"  isca: os Termos de antes (o cranio inteiro): reprova",
           bool(_faixa_da_mandibula_divergente(v_eng, termos.replace(
               u"só na faixa", u"em todo o"))))


_MARCA_AORTA = u"a aorta sai recortada dos pulmões, do esôfago e da traqueia"
_MARCA_CRISTAS_NO_OAR = (u"as cristas ilíacas ( IliacCrest_L_ai e "
                         u"IliacCrest_R_ai ) e o ânus ( Anus_ai ) seguem a "
                         u"mesma regra: vão ao entregue só quando a anatomia "
                         u"identifica a pelve na série")
_MARCA_CRISTAS_SEMPRE = u"vão ao entregue sempre que saem"
_MARCA_OAR_DAS_MASCARAS = (u"gravadas das máscaras finais do completo, antes "
                           u"dele, e iguais às do completo")
_MARCA_OAR_SEM_REESCRITA = u"copiadas do completo sem nenhuma reescrita"
_MARCA_SEM_RTSTRUCT_TERMOS = (u"o marcador %s (o arquivo <UID>.%s.json em "
                              u"_RadAI )")
_MARCA_TRAVA_CRIADO = u"o instante de criação dele (o campo criado"
_MARCA_MARCADOR_DE_OUTRA_ESTACAO = (u"só se afasta o marcador que esta estação "
                                    u"gravou: o de outra estação fica como "
                                    u"está")
_MARCA_MARCADOR_DE_OUTRA_ESTACAO_POLITICA = (u"só o que ela mesma gravou, e o "
                                             u"de outra estação fica onde "
                                             u"está")
_MARCA_TETO_DO_RECURSO = (u"Com %s faltas de recurso seguidas no mesmo "
                          u"processo, sem nenhuma série concluída entre elas, "
                          u"o vigia para de pegar série nova")
_MARCA_TURNO_AGENDADO_NO_X = (u"Com o turno da noite agendado na fila e o "
                              u"lote do «Rodar agora» andando até ele")
_MARCA_LOTE_RETOMADO = (u"o lote que parou entre séries por causa do fechar "
                        u"volta a andar sozinho")
_MARCA_REABRIR_COM_TURNO = (u"ou com o turno da noite aberto ou agendado na "
                            u"fila, pergunta")
_MARCA_FAXINA_COM_TETO = u"Cada faxina dura no máximo %s segundos"
_RECURSO_NOS_TERMOS = ("can't start new thread", "virtualalloc",
                       "commit limit", "memory allocation failed")
_MARCA_RECURSO = (u"«can't start new thread» e as mensagens de memória de "
                  u"commit esgotada (VirtualAlloc, commit limit , memory "
                  u"allocation failed ) contam como falta de recurso")
_MARCA_CRISTAS_CONSTRUCAO = u"são só recorte do completo, sem modelo novo"
_MARCA_PANCREAS_NA_BAG = (u"A Bag_Bowel_ai , da receita anterior, também "
                          u"leva o pâncreas inteiro")
_MARCA_FECHA_AO_FIM = u"Isso não interrompe a série em curso"
_MARCA_FECHA_INTERROMPE = (u"inclusive com a fila rodando: a série em curso "
                           u"é interrompida")
_MARCA_FECHAR_TUDO_NA_HORA = u"O «Fechar tudo» do botão é o que encerra na hora"
_MARCA_TRAVA_SOLTA_AO_ABRIR = (u"é solta, e a série volta para a fila do "
                               u"vigia, com uma linha no cartão")
_MARCA_RTSTRUCT_TERMOS = u"Pronta ou parcial, só com o arquivo no disco."
_MARCA_RTSTRUCT_POLITICA = (u"RTSTRUCT do programa daquela série está gravado "
                            u"e conferido no disco")
_MARCA_SUBSTITUIR_FILA = (u"quando você confirmou que a entrega anterior da "
                          u"série seja substituída")
_MARCA_SUBSTITUIR_NIDUS = u"pode pedir que ela seja refeita em AUTO"
_BOTAO_DO_PREPARADOR = u"Instalar / Atualizar app nesta máquina"
_MARCA_ATUALIZAR_APP = u"E o «%s» do preparador." % _BOTAO_DO_PREPARADOR
_MARCA_TEMA_SISTEMA = u"o tema (claro, escuro ou o do sistema)"
_MARCA_PIXEL_INCOMPLETO = (u"A série com um corte de imagem incompleta no "
                           u"arquivo (truncado, curto ou sem a imagem) não é "
                           u"convertida")


def _fatos_do_retorno_de_campo():
    src_eng = ler(u"app/engine.py")
    v_eng = _valores_do_modulo(src_eng)
    v_sets = _valores_do_modulo(ler(u"app/radai_sets.py"))
    v_cons = _valores_do_modulo(ler(u"app/radai_constructs.py"))
    src_rec = ler(u"app/radai_records.py")
    v_rec = _valores_do_modulo(src_rec)
    src_qs = ler(u"app/radai_queue_state.py")
    src_prep = ler(u"packager/prepare.ps1")
    src_ui = ler(u"app/radai_ui.py")
    src_wat = ler(u"app/radai_watcher.py")
    v_wat = _valores_do_modulo(src_wat)
    src_lan = ler(u"app/radai_lancador.py")
    v_fal = _valores_do_modulo(ler(u"app/radai_falhas.py"))
    oar = set(v_sets.get("PERMITIDOS_NO_OAR") or ())
    inteiros = [x[0] if isinstance(x, tuple) else x
                for x in (v_cons.get("INTEIROS_NA_BAG") or ())]
    teto = _numero_do_modulo(src_rec, "TETO_DO_LOG_DA_SERIE")
    return {
        "aorta": tuple(v_eng.get("RECORTE_DA_AORTA_DEPOIS_DA_MARGEM") or ()),
        "cristas_no_oar": {"iliac_crest_left", "iliac_crest_right",
                           "anus"} <= oar,
        "cristas_construidas": (u"def crista_iliaca(" in ler(
            u"app/radai_constructs.py") and u"def anus(" in ler(
            u"app/radai_constructs.py")),
        "pancreas_na_bag": u"pancreas" in inteiros,
        "fecha_ao_fim": (u"def _adiar(" in ler(u"app/radai_pulso.py")
                         and u"def pedir_fechar_ao_fim(" in src_qs),
        "trava_solta_ao_abrir": u"def soltar_travas_mortas_ao_abrir(" in ler(
            u"app/radai_watcher.py"),
        "log_da_serie": v_rec.get("NOME_DO_LOG_DA_SERIE"),
        "log_da_serie_mb": (teto / 1048576.0) if teto else None,
        "em_andamento": v_rec.get("PASTA_EM_ANDAMENTO"),
        "rtstruct_no_disco": (
            u"def exigir_rtstruct_no_disco(" in ler(u"app/radai_batch.py")
            and u"exigir_rtstruct_no_disco(" in ler(u"app/radai_watcher.py")),
        "substituir_na_fila": u"substituir" in tuple(
            _valores_do_modulo(src_qs).get("ESCOLHA_PERSISTIDA") or ()),
        "atualizar_app": (u"radioterapia-ai-preparador" in src_prep
                          and u"_SETUP_LATEST.zip" in src_prep
                          and (u"'%s'" % _BOTAO_DO_PREPARADOR) in src_prep),
        "tema_sistema": (u"radai_tema" in src_ui
                         and u"prefers-color-scheme" in src_ui),
        "pixel_incompleto": u"def _pixel_incompleto(" in ler(
            u"app/radai_dicom.py"),
        "cristas_so_com_pelve": all(
            (v_eng.get("REGIAO_EXIGIDA_NO_OAR") or {}).get(k) == "pelve"
            for k in ("iliac_crest_left", "iliac_crest_right", "anus")),
        "oar_das_mascaras": u"preparo.gravar_selecao(" in src_eng,
        "marcador_sem_rtstruct": v_wat.get("MARCADOR_SEM_RTSTRUCT"),
        "trava_criado": (u"def _dono_da_trava_vivo(" in src_wat
                         and u'meta.setdefault("criado"' in src_wat),
        "turno_agendado_no_x": u"def _turno_segue_na_fila(" in src_wat,
        "lote_retomado": u"def retomar_o_lote_que_parou_ao_fechar(" in ler(
            u"app/radai_batch.py"),
        "reabrir_com_turno": (u's.get("turno_agendado")' in src_lan
                              and u's.get("overnight")' in src_lan),
        "faxina_teto_s": _valores_do_modulo(ler(u"app/radai_archive.py")).get(
            "TETO_DA_FAXINA_S"),
        "recurso_thread": [x for x in _RECURSO_NOS_TERMOS
                           if x in tuple(v_fal.get("FRASES_DE_RECURSO") or ())],
        "marcador_de_outra_estacao": (
            u"def marcador_de_outra_estacao(" in src_wat
            and u"if quem != MACHINE:" in src_wat),
        "teto_do_recurso": v_wat.get("TETO_DE_RECURSO_SEGUIDO"),
        "frase_do_recurso": v_wat.get("FRASE_DO_RECURSO_ESGOTADO"),
    }


def _retorno_de_campo_divergente(f, termos, politica):
    fora = []

    def par(fato, marca, texto, onde, o_que):
        diz = marca in (texto or u"")
        if bool(fato) is not diz:
            fora.append(u"%s: o codigo %s, e %s %s" % (
                o_que, u"faz" if fato else u"NAO faz", onde,
                u"diz" if diz else u"cala"))

    aorta = set(f["aorta"])
    par({"esophagus", "trachea"} <= aorta and any(
            a.startswith(u"lung") for a in aorta),
        _MARCA_AORTA, termos, u"os Termos (1.2)",
        u"a aorta recortada dos vizinhos depois da margem")
    par(f["cristas_no_oar"] and f.get("cristas_so_com_pelve"),
        _MARCA_CRISTAS_NO_OAR, termos, u"os Termos (1.1)",
        u"as cristas iliacas e o anus no entregue so com a pelve")
    par(f["cristas_no_oar"] and not f.get("cristas_so_com_pelve"),
        _MARCA_CRISTAS_SEMPRE, termos, u"os Termos (1.1)",
        u"as cristas iliacas e o anus no entregue sempre que saem")
    par(f.get("oar_das_mascaras"), _MARCA_OAR_DAS_MASCARAS, termos,
        u"os Termos (1.1)", u"o entregue gravado das mascaras finais do "
        u"completo")
    if f.get("oar_das_mascaras") and _MARCA_OAR_SEM_REESCRITA in termos:
        fora.append(u"o entregue sai das mascaras finais do completo, e os "
                    u"Termos dizem «%s»" % _MARCA_OAR_SEM_REESCRITA)
    msr = f.get("marcador_sem_rtstruct")
    _nome_msr = msr or u"done_sem_rtstruct"
    marca_msr = _MARCA_SEM_RTSTRUCT_TERMOS % (_nome_msr, _nome_msr)
    par(bool(msr), u"o vigia o afasta para " + marca_msr, termos,
        u"os Termos (1.4)",
        u"o marcador de pronta sem RTSTRUCT afastado e refeito")
    par(bool(msr), u"é afastado para " + marca_msr, politica,
        u"a Politica (3)", u"o marcador afastado como uma morada nova")
    par(f.get("trava_criado"), _MARCA_TRAVA_CRIADO, politica,
        u"a Politica (3)", u"o instante de criacao do dono na trava")
    par(f.get("marcador_de_outra_estacao"), _MARCA_MARCADOR_DE_OUTRA_ESTACAO,
        termos, u"os Termos (1.4)",
        u"o marcador de outra estacao com destino proprio fica")
    par(f.get("marcador_de_outra_estacao"),
        _MARCA_MARCADOR_DE_OUTRA_ESTACAO_POLITICA, politica,
        u"a Politica (3)", u"o marcador de outra estacao nao e afastado")
    teto_r = f.get("teto_do_recurso")
    frase_r = f.get("frase_do_recurso")
    if teto_r:
        par(True, _MARCA_TETO_DO_RECURSO % teto_r, termos,
            u"os Termos (1.4)", u"o teto de faltas de recurso seguidas")
        par(bool(frase_r), u"«%s»" % (frase_r or u"\x00"), termos,
            u"os Termos (1.4)", u"a linha do cartao do teto do recurso")
    elif u"faltas de recurso seguidas no mesmo processo" in (termos or u""):
        fora.append(u"o teto de faltas de recurso seguidas: o codigo NAO "
                    u"faz, e os Termos (1.4) dizem")
    par(f.get("turno_agendado_no_x"), _MARCA_TURNO_AGENDADO_NO_X, termos,
        u"os Termos (1.5)", u"o X com o turno da noite agendado")
    par(f.get("lote_retomado"), _MARCA_LOTE_RETOMADO, termos,
        u"os Termos (1.5)", u"a tela que volta relanca o lote")
    par(f.get("reabrir_com_turno"), _MARCA_REABRIR_COM_TURNO, termos,
        u"os Termos (1.5)", u"a reabertura que pergunta com o turno")
    teto = f.get("faxina_teto_s")
    marca_teto = _MARCA_FAXINA_COM_TETO % (_num_pt(teto) if teto else u"?")
    par(bool(teto), marca_teto, politica, u"a Politica (6)",
        u"a faxina do Rodar agora com teto de tempo")
    rec = f.get("recurso_thread") or ()
    par(len(rec) == len(_RECURSO_NOS_TERMOS), _MARCA_RECURSO, termos,
        u"os Termos (1.4)", u"can't start new thread e o commit como recurso")
    par(f["cristas_construidas"], _MARCA_CRISTAS_CONSTRUCAO, termos,
        u"os Termos (1.2)", u"as cristas iliacas e o anus por recorte")
    par(f["pancreas_na_bag"], _MARCA_PANCREAS_NA_BAG, termos,
        u"os Termos (1.2)", u"o pancreas inteiro na Bag_Bowel_ai")
    par(f["fecha_ao_fim"], _MARCA_FECHA_AO_FIM, termos, u"os Termos (1.5)",
        u"fechar pelo X termina a serie em curso")
    par(f["fecha_ao_fim"], _MARCA_FECHAR_TUDO_NA_HORA, termos,
        u"os Termos (1.5)", u"o Fechar tudo como o que interrompe")
    if f["fecha_ao_fim"] and _MARCA_FECHA_INTERROMPE in termos:
        fora.append(u"fechar pelo X nao interrompe a serie no codigo, e os "
                    u"Termos dizem que interrompe")
    par(f["trava_solta_ao_abrir"], _MARCA_TRAVA_SOLTA_AO_ABRIR, termos,
        u"os Termos (1.5)", u"a trava morta solta ao abrir")
    log = (f["log_da_serie"] or u"").replace(u"%s", u"<UID>")
    par(bool(log), (u"_RadAI\\" + log) if log else u"_RadAI\\<UID>.log.txt",
        politica, u"a Politica (3)", u"o log da serie em _RadAI")
    if log and f["log_da_serie_mb"]:
        teto = u"Ele tem teto de %s MB" % _num_pt(f["log_da_serie_mb"])
        if teto not in politica:
            fora.append(u"o log da serie tem teto de %s MB, e a Politica nao "
                        u"diz «%s»" % (f["log_da_serie_mb"], teto))
        rodizio = u"se ele chegou a %s MB" % _num_pt(f["log_da_serie_mb"])
        if rodizio not in politica:
            fora.append(u"a Politica (6) nao diz o rodizio do log da serie "
                        u"«%s»" % rodizio)
    pasta = u"registro\\%s\\" % (f["em_andamento"] or u"\x00")
    par(bool(f["em_andamento"]), pasta, politica, u"a Politica (3)",
        u"o caso em andamento do registro")
    par(f["rtstruct_no_disco"], _MARCA_RTSTRUCT_TERMOS, termos,
        u"os Termos (1.4)", u"o marcador so com o RTSTRUCT no disco")
    par(f["rtstruct_no_disco"], _MARCA_RTSTRUCT_POLITICA, politica,
        u"a Politica (3)", u"o marcador so com o RTSTRUCT no disco")
    par(f["substituir_na_fila"], _MARCA_SUBSTITUIR_FILA, politica,
        u"a Politica (3)", u"o substituir gravado na fila")
    par(f["substituir_na_fila"], _MARCA_SUBSTITUIR_NIDUS, politica,
        u"a Politica (6)", u"o Nidus RT que pede a substituicao")
    par(f["atualizar_app"], _MARCA_ATUALIZAR_APP, politica,
        u"a Politica (4)", u"o Atualizar app que consulta e baixa a release")
    par(f["tema_sistema"], _MARCA_TEMA_SISTEMA, politica, u"a Politica (3)",
        u"o tema claro, escuro ou do sistema no navegador")
    par(f["pixel_incompleto"], _MARCA_PIXEL_INCOMPLETO, termos,
        u"os Termos (4.5)", u"a recusa do corte incompleto")
    return fora


def teste_o_retorno_de_campo_na_18():
    secao(u"documentos 1.8: o retorno de campo de 16/10 (o fechar que espera "
          u"a serie, o log da serie, o caso em andamento, o marcador com "
          u"arquivo, as estruturas novas, o tema e o Atualizar app)")
    import radai_consent as CS
    termos = _plano(CS.TERMOS)
    politica = _plano(CS.POLITICA)
    f = _fatos_do_retorno_de_campo()
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % kv for kv in sorted(f.items())),
        all(f[k] for k in f if k != "aorta") and bool(f["aorta"]))
    div = _retorno_de_campo_divergente(f, termos, politica)
    checar(u"o retorno de campo: o codigo, os Termos e a Politica dizem o "
           u"mesmo", not div, u" | ".join(div))
    for rotulo, fatos in (
            (u"a aorta deixa de ser recortada", dict(f, aorta=())),
            (u"as cristas e o anus saem do entregue",
             dict(f, cristas_no_oar=False)),
            (u"a Bag_Bowel_ai sem o pancreas inteiro",
             dict(f, pancreas_na_bag=False)),
            (u"fechar pelo X volta a interromper", dict(f, fecha_ao_fim=False)),
            (u"a trava morta nao e mais solta ao abrir",
             dict(f, trava_solta_ao_abrir=False)),
            (u"o log da serie com teto de 8 MB",
             dict(f, log_da_serie_mb=8.0)),
            (u"o log da serie com outro nome",
             dict(f, log_da_serie=u"%s.serie.log")),
            (u"o caso em andamento em outra pasta",
             dict(f, em_andamento=u"abertos")),
            (u"o marcador volta a sair sem o arquivo",
             dict(f, rtstruct_no_disco=False)),
            (u"a fila deixa de gravar o substituir",
             dict(f, substituir_na_fila=False)),
            (u"o preparador sem o Atualizar app", dict(f, atualizar_app=False)),
            (u"o tema sem o do sistema", dict(f, tema_sistema=False)),
            (u"a conversao volta a gravar o corte incompleto",
             dict(f, pixel_incompleto=False)),
            (u"as cristas e o anus no entregue sem depender da pelve",
             dict(f, cristas_so_com_pelve=False)),
            (u"o entregue deixa de sair das mascaras finais",
             dict(f, oar_das_mascaras=False)),
            (u"o marcador sem RTSTRUCT com outro nome",
             dict(f, marcador_sem_rtstruct=u"done_vazio")),
            (u"o marcador sem RTSTRUCT volta a valer",
             dict(f, marcador_sem_rtstruct=None)),
            (u"a trava sem o instante de criacao", dict(f, trava_criado=False)),
            (u"o X volta a segurar a fila com o turno agendado",
             dict(f, turno_agendado_no_x=False)),
            (u"a tela que volta nao relanca o lote",
             dict(f, lote_retomado=False)),
            (u"a reabertura encerra o turno sem perguntar",
             dict(f, reabrir_com_turno=False)),
            (u"a faxina com teto de 5 s", dict(f, faxina_teto_s=5.0)),
            (u"o can't start new thread deixa de ser recurso",
             dict(f, recurso_thread=[u"virtualalloc"])),
            (u"o marcador de outra estacao volta a ser afastado",
             dict(f, marcador_de_outra_estacao=False)),
            (u"o teto do recurso em 5", dict(f, teto_do_recurso=5)),
            (u"sem o teto do recurso", dict(f, teto_do_recurso=None,
                                            frase_do_recurso=None)),
            (u"a linha do cartao do teto com outra frase",
             dict(f, frase_do_recurso=u"sem memoria"))):
        checar(u"  isca: %s, com os documentos de hoje: reprova" % rotulo,
               bool(_retorno_de_campo_divergente(fatos, termos, politica)))
    for rotulo, t, p in (
            (u"os Termos de antes do fechar (a serie e interrompida)",
             termos + u" " + _MARCA_FECHA_INTERROMPE, politica),
            (u"os Termos calam o ânus e as cristas no entregue",
             termos.replace(_MARCA_CRISTAS_NO_OAR, u"X"), politica),
            (u"a Politica cala o log da serie",
             termos, politica.replace(u"<UID>.log.txt", u"X")),
            (u"a Politica cala o caso em andamento",
             termos, politica.replace(u"registro\\em_andamento\\", u"X")),
            (u"a Politica cala o Atualizar app",
             termos, politica.replace(_MARCA_ATUALIZAR_APP, u"X")),
            (u"os Termos de antes (as cristas vao ao entregue sempre)",
             termos.replace(_MARCA_CRISTAS_NO_OAR, _MARCA_CRISTAS_SEMPRE),
             politica),
            (u"os Termos de antes (o entregue copiado sem reescrita)",
             termos + u" " + _MARCA_OAR_SEM_REESCRITA, politica),
            (u"a Politica cala o marcador afastado",
             termos, politica.replace(u"é afastado para", u"X")),
            (u"a Politica cala o instante de criacao da trava",
             termos, politica.replace(_MARCA_TRAVA_CRIADO, u"X")),
            (u"os Termos de antes da reabertura (so a serie pergunta)",
             termos.replace(_MARCA_REABRIR_COM_TURNO, u"X"), politica),
            (u"os Termos calam o recurso do can't start new thread",
             termos.replace(_MARCA_RECURSO, u"X"), politica),
            (u"os Termos de antes (todo marcador sem arquivo e afastado)",
             termos.replace(_MARCA_MARCADOR_DE_OUTRA_ESTACAO, u"X"), politica),
            (u"a Politica de antes (todo marcador sem arquivo e afastado)",
             termos, politica.replace(
                 _MARCA_MARCADOR_DE_OUTRA_ESTACAO_POLITICA, u"X")),
            (u"os Termos calam o teto do recurso",
             termos.replace(u"faltas de recurso seguidas", u"X"), politica)):
        checar(u"  isca: %s: reprova" % rotulo,
               bool(_retorno_de_campo_divergente(f, t, p)))


_MARCA_ENCERRAM_OS_DOIS = (u"E o atualizador e o instalador do pacote, antes "
                           u"de trocar o código, encerram o programa aberto "
                           u"daquela pasta")
_MARCA_ENCERRA_SO_O_ATUALIZADOR = (u"E o atualizador, antes de trocar o "
                                   u"código, encerra o programa aberto "
                                   u"daquela pasta")
_MARCA_NADA_POR_CIMA = u"nada é copiado por cima do programa aberto"


def _encerra_antes_divergente(atualiza, instala, termos):
    fora = []
    dois = _MARCA_ENCERRAM_OS_DOIS in termos
    so = _MARCA_ENCERRA_SO_O_ATUALIZADOR in termos
    if atualiza and instala:
        if not (dois and _MARCA_NADA_POR_CIMA in termos):
            fora.append(u"os dois encerram, e os Termos nao dizem os dois "
                        u"nem que nada e copiado por cima")
    elif atualiza:
        if not so or dois:
            fora.append(u"so o atualizador encerra, e os Termos dizem outra "
                        u"coisa")
    elif dois or so:
        fora.append(u"nenhum encerra, e os Termos dizem que sim")
    return fora


_EXTENSOES_NOMEADAS = r"\.(?:jsonl|json|log|txt|npz|dcm|md|html|js)$"


def _fontes_que_gravam():
    fora = []
    docs = (u"radai_consent.py", u"radai_phrases.py", u"radai_credits.py")
    pastas = list(_componentes.pastas("app")) + [
        os.path.join(RAIZ, u"packager"), os.path.join(RAIZ, u"installer")]
    for base in pastas:
        for raiz, ds, fs in os.walk(base):
            ds[:] = [d for d in ds if d != u"__pycache__"]
            for f in fs:
                if f in docs or not f.endswith((u".py", u".ps1", u".cmd",
                                                u".js")):
                    continue
                fora.append(io.open(os.path.join(raiz, f), encoding="utf-8",
                                    errors="replace").read())
    return fora


def _arquivos_nomeados_sem_codigo(docs_html, fontes):
    import html as _h
    nomes = set()
    for doc in docs_html:
        for c in re.findall(r"(?s)<code[^>]*>(.*?)</code>", doc or u""):
            n = _h.unescape(c).replace(u"\\\\", u"\\").strip()
            if re.search(_EXTENSOES_NOMEADAS, n):
                nomes.add(n)
    sem = []
    for n in sorted(nomes):
        partes = [x.split(u"\\")[-1] for x in re.split(r"<[^>]*>|\*", n) if x]
        partes = [x for x in partes if x]
        if not any(all(x in t for x in partes) for t in fontes):
            sem.append(n)
    return nomes, sem


def _numero_do_modulo(src, nome):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return None

    def _av(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mult, ast.Add)):
            a, b = _av(n.left), _av(n.right)
            return a * b if isinstance(n.op, ast.Mult) else a + b
        raise ValueError(u"nao e numero")

    for no in arv.body:
        if (isinstance(no, ast.Assign) and len(no.targets) == 1
                and getattr(no.targets[0], "id", None) == nome):
            try:
                return _av(no.value)
            except Exception:
                return None
    return None


def _fatos_da_ponte(src_b, src_e, src_img, src_fila):
    validade = _numero_do_modulo(src_b, "VALIDADE_DA_GUARDA_S")
    return {
        "metade": u"apagar(p)" in _fonte_da_funcao(src_e, "entregar"),
        "teto": _valores_do_modulo(src_fila).get("TETO_DE_COPIAS"),
        "confere": u"_rs_ao_lado(" in _fonte_da_funcao(src_b,
                                                       "conferir_guarda"),
        "guardas": _valores_do_modulo(src_b).get("TETO_DE_GUARDAS"),
        "validade_h": (validade / 3600.0) if validade else None,
        "sufixo": u"secrets.token_hex(" in _fonte_da_funcao(
            src_img, "identidade_externa"),
        "bilhete": u"guarda: e.guarda" in _fonte_da_funcao_js(
            src_b, "dcFilaGuardar"),
    }


def _ponte_divergente(f, politica, termos):
    fora = []
    par = _trecho(politica, u"O DicomBridge é uma ferramenta de pipeline único",
                  u"O vídeo do visor das Reconstruções 3D")
    if f["metade"] is not (u"a pasta que ficou pela metade nele é apagada"
                           in par):
        fora.append(u"a pasta pela metade %s apagada, e a Politica (5) %s"
                    % (u"e" if f["metade"] else u"NAO e",
                       u"diz" if u"pela metade" in par else u"cala"))
    descarte = _trecho(politica, u"6 · Retenção e descarte",
                       u"7 · Direitos do titular")
    diz_descarte = u"a pasta que ficou pela metade da própria entrega" in descarte
    if f["metade"] is not diz_descarte:
        fora.append(u"a pasta pela metade %s apagada, e o descarte da "
                    u"Politica (6) %s" % (u"e" if f["metade"] else u"NAO e",
                                          u"diz" if diz_descarte else u"cala"))
    if not f["teto"] or (u"no máximo %d" % f["teto"]) not in par:
        fora.append(u"a Politica (5) nao diz o teto de %s copias do RTSTRUCT"
                    % f["teto"])
    diz_confere = u"o programa confere no disco se as cópias chegaram" in par
    if f["confere"] is not diz_confere:
        fora.append(u"a conferencia das copias no disco: codigo=%s, "
                    u"Politica=%s" % (f["confere"], diz_confere))
    mem = _trecho(politica, u"Na memória do programa, enquanto ele roda.",
                  u"No navegador desta estação.")
    frase = u"por até %s horas e no máximo %s entregas" % (
        _num_pt(f["validade_h"]), _num_pt(f["guardas"]))
    if frase not in mem or u"nunca em disco" not in mem:
        fora.append(u"a Politica (3) nao diz a lista na memoria «%s»" % frase)
    nav = _trecho(politica, u"No navegador desta estação.",
                  u"Aberto pelo atalho")
    diz_bilhete = u"e um bilhete opaco — sem caminho e sem a descrição" in nav
    if f["bilhete"] is not diz_bilhete:
        fora.append(u"a sessao da aba do DicomBridge: codigo guarda o "
                    u"bilhete=%s, Politica=%s" % (f["bilhete"], diz_bilhete))
    for nome, txt in ((u"Politica", politica), (u"Termos", termos)):
        diz = u"a data, a hora e um sufixo aleatório curto" in txt
        if f["sufixo"] is not diz:
            fora.append(u"o sufixo do EXTERNO: codigo=%s, %s=%s"
                        % (f["sufixo"], nome, diz))
    return fora


def _fatos_do_nidus(src):
    chave = _fonte_da_funcao(src, "chave_da_serie")
    m = re.search(r"hexdigest\(\)\[:(\d+)\]", chave)
    foto = _fonte_da_funcao_js(src, "ndFoto")
    return {"digitos": int(m.group(1)) if m else None,
            "pelo_uid": (u"hashlib.sha256(" in chave and u'u"uid:"' in chave
                         and u"ND.chave" in _fonte_da_funcao_js(
                             src, "ndChaveSalva")),
            "campos": all(k in foto for k in (u"modo:", u"laje:",
                                              u"inverter:", u"osso:",
                                              u"pontos:", u"guardadas:"))}


def _nidus_divergente(f, politica):
    fora = []
    nav = _trecho(politica, u"No navegador desta estação.",
                  u"Aberto pelo atalho")
    frase = u"sob uma impressão SHA-256 do UID da série, de %s caracteres" % (
        f["digitos"],)
    if not f["pelo_uid"] or frase not in nav:
        fora.append(u"a chave da aba do Nidus: codigo pelo UID=%s, a Politica "
                    u"%s «%s»" % (f["pelo_uid"],
                                  u"diz" if frase in nav else u"nao diz",
                                  frase))
    campos = (u"MIP ou MinIP, a laje, o inverter, o osso ligado ou desligado"
              in nav and u"o traço em curso" in nav)
    if f["campos"] is not campos:
        fora.append(u"os campos que o Nidus guarda: codigo=%s, Politica=%s"
                    % (f["campos"], campos))
    return fora


_RE_EMAIL_NO_DOC = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


_DONO_RENOMEADO = {"versao_docs": u"2.0",
                   "antes": u"https://github.com/radioterapia-ai/local-suite",
                   "depois": u"https://github.com/drhenriquebraga/local-suite"}


def _contato_divergente(docs, url_versoes, versao_docs=None):
    fora = []
    m = re.match(r"(https://github\.com/[^/]+/[^/?#]+)", url_versoes or u"")
    repo = m.group(1) if m else u""
    aceitos = [repo]
    if (versao_docs == _DONO_RENOMEADO["versao_docs"]
            and repo == _DONO_RENOMEADO["depois"]):
        aceitos.append(_DONO_RENOMEADO["antes"])
    for nome, html in docs:
        for e in _RE_EMAIL_NO_DOC.findall(html or u""):
            fora.append(u"%s traz um e-mail (%s…)" % (nome, e[:3]))
        if nome == u"aceite":
            continue
        if u'href="https://radioterapia.ai"' not in (html or u""):
            fora.append(u"%s nao aponta a pagina do projeto" % nome)
        if not repo or not any((u'href="%s/security"' % r) in (html or u"")
                               for r in aceitos):
            fora.append(u"%s nao aponta o relato privado do repositorio da "
                        u"versao (%s)" % (nome, repo))
    return fora


_MARCA_FACE_NA_FICHA = u"A ficha nomeia a face de entrada do cateter"


def _fatos_do_aplicador(src):
    ato = _fonte_da_funcao(src, "linha_do_ato")
    return {"registra_face": u"pela face %s" in ato,
            "registra_padrao": u"padrao %s mm" in ato,
            "ficha_face": u"Face de entrada do cateter" in src,
            "padrao_campo": (u'q["raio_padrao_mm"]' in src
                             and u"if padrao < piso:" in src),
            "so_sobe": (u"pedido < RAIO_PADRAO_MM" in src
                        and u"return max(p, RAIO_PADRAO_MM)"
                        in _fonte_da_funcao(src, "limiar_amarelo")),
            "sugerido": _valores_do_modulo(src).get("RAIO_PADRAO_MM")}


_MARCA_PADRAO_DESCE = u"e descê-lo só até o piso do afterloader"


def _aplicador_face_divergente(f, termos, politica):
    fora = []
    reg = _trecho(politica, u"registro dos atos de exportação do 3D Printed "
                  u"Bolus", u"registro dos atos de gravação de vídeo")
    for chave, frase in ((u"registra_face", u"a face de entrada do cateter"),
                         (u"registra_padrao", u"o raio padrão escolhido")):
        if f[chave] is not (frase in reg):
            fora.append(u"o registro do ato %s «%s», e a Politica %s" % (
                u"grava" if f[chave] else u"NAO grava", frase,
                u"diz" if frase in reg else u"cala"))
    if f["ficha_face"] is not (_MARCA_FACE_NA_FICHA in termos):
        fora.append(u"a ficha %s a face de entrada, e os Termos %s" % (
            u"nomeia" if f["ficha_face"] else u"NAO nomeia",
            u"dizem" if _MARCA_FACE_NA_FICHA in termos else u"calam"))
    if f.get("so_sobe"):
        campo = (u"O raio padrão começa em %s mm e é um campo do formulário "
                 u"que só sobe" % _num_pt(f["sugerido"]))
    else:
        campo = (u"O raio padrão vem sugerido em %s mm e é um campo do "
                 u"formulário" % _num_pt(f["sugerido"]))
    if f["padrao_campo"] is not (campo in termos):
        fora.append(u"o raio padrao %s campo do formulario%s, e os Termos %s"
                    % (u"e" if f["padrao_campo"] else u"NAO e",
                       u" que so sobe" if f.get("so_sobe") else u"",
                       u"dizem" if campo in termos else u"calam"))
    abaixo = (u"a curva abaixo de %s mm é sempre amarela"
              % _num_pt(f["sugerido"]))
    if f.get("so_sobe") and abaixo not in termos:
        fora.append(u"o codigo poe a curva abaixo do padrao sempre amarela, "
                    u"e os Termos nao dizem «%s»" % abaixo)
    if f.get("so_sobe") and _MARCA_PADRAO_DESCE in termos:
        fora.append(u"o padrao so sobe no codigo, e os Termos dizem que ele "
                    u"desce ate o piso")
    return fora


def _faixa_da_mandibula_divergente(v_eng, termos):
    topo = tuple(v_eng.get("TOPO_DA_FAIXA_DA_MANDIBULA") or ())
    fim = v_eng.get("FIM_DA_FAIXA_DA_MANDIBULA")

    def curto(n):
        return str(n or u"").split(u"_")[-1]

    if len(topo) == 2 and fim:
        frase = (u"só na faixa do topo do %s (sem ele, do topo do %s) ao fim "
                 u"do %s" % (curto(topo[0]), curto(topo[1]), curto(fim)))
        if frase not in termos:
            return [u"os Termos (4) nao dizem a faixa da mandibula «%s»"
                    % frase]
        return []
    if u"só na faixa" in termos:
        return [u"o motor nao tem faixa da mandibula, e os Termos dizem"]
    return []

_MARCAS_DA_19 = {
    "parotida_ts_fora": (u"termos", u"A parótida do TotalSegmentator nunca "
                                    u"vai ao entregue"),
    "parotida_risco": (u"termos", u"a parótida do TotalSegmentator não vai ao "
                                  u"entregue"),
    "contornos": (u"termos", u"nenhum contorno sai com área nula, com vértice "
                             u"repetido ou cruzando a si mesmo"),
    "implicito_em_todo": (u"termos", u"a sintaxe padrão do DICOM, e declara "
                                     u"o repertório de caracteres"),
    "charset_da_tc": (u"termos", u"então, o mesmo da TC, com os mesmos bytes "
                                 u"do nome"),
    "bridge_implicito_nos_dois": (u"termos", u"O que o DicomBridge exporta — "
                                             u"as séries DICOM e as imagens "
                                             u"que ele converte — sai também "
                                             u"em Implicit VR Little Endian"),
    "cd_uma_vez": (u"politica", u"O disco é lido uma vez: o que a leitura "
                                u"achou fica na memória do processo"),
    "imagem_no_pipeline": (u"politica", u"entra no mesmo pipeline, sem "
                                        u"segmentação"),
    "imagem_no_pipeline_termos": (u"termos", u"entra no mesmo pipeline, sem "
                                             u"segmentação"),
    "cd": (u"politica", u"O CD não é oferecido como destino da entrega"),
    "elastic_sem_abrir": (u"politica", u"a Fusão elástica não lê nenhuma "
                                       u"pasta"),
    "bolus_no_acervo": (u"politica", u"e o «Gerar bólus» mostram na aba do "
                                     u"acervo local"),
    "barra_na_aba": (u"politica", u"se a barra da fila foi aberta ou recolhida "
                                  u"à mão nesta aba"),
    "tema_no_aceite": (u"politica", u"no canto das telas do aceite e do "
                                    u"primeiro uso, onde ele é gravado antes "
                                    u"mesmo do aceite"),
}
_FRASES_DA_18_QUE_SAIRAM = (
    (u"termos", u"no lugar da parótida do TotalSegmentator"),
    (u"termos", u"senão, fica a do TotalSegmentator"),
    (u"termos", u"é ligado à borda externa por uma fenda"),
    (u"politica", u"tem duas ferramentas, e as duas gravam no servidor"),
    (u"politica", u"a guarda ali para «Baixar de novo»"),
    (u"politica", u"converte uma série de JPEG ou PNG por vez"),
)
_FRASES_DA_19_QUE_SAIRAM_ANTES_DA_PUBLICACAO = (
    (u"termos", u"exporta sai em Explicit VR Little Endian"),
    (u"termos", u"e a sintaxe do que o DicomBridge exporta"),
)


def _sintaxe_do_bridge_nos_dois():
    import radai_dicom
    implicita = u"1.2.840.10008.1.2"
    return (all(radai_dicom.sintaxe_de_saida(t) == implicita
                for t in (u"eclipse", u"monaco", None))
            and u"radai_dicom.sintaxe_de_saida()" in ler(u"app/radai_image.py"))


def _fora_do_bloco(src_funcao, cabeca, alvo):
    linhas = (src_funcao or u"").splitlines()
    dentro, recuo = False, None
    for linha in linhas:
        tira = linha.lstrip()
        r = len(linha) - len(tira)
        if dentro and tira and r <= recuo:
            dentro = False
        if tira.startswith(cabeca):
            dentro, recuo = True, r
            continue
        if alvo in linha and not dentro:
            return True
    return False


def _fatos_da_19():
    src_eng = ler(u"app/engine.py")
    v_eng = _valores_do_modulo(src_eng)
    oar = set(_valores_do_modulo(ler(u"app/radai_sets.py")).get(
        "PERMITIDOS_NO_OAR") or ())
    acab = _fonte_da_funcao(src_eng, "acabamento_para_o_tps")
    rotulos = _valores_do_modulo(ler(u"app/radai_config.py")).get(
        "TPS_ROTULOS") or {}
    src_dicom = ler(u"app/radai_dicom.py")
    v_dicom = _valores_do_modulo(src_dicom)
    src_ent = ler(u"app/radai_bridge_entrada.py")
    src_ui = ler(u"app/radai_ui.py")
    m_hist = re.search(r"HIST_MAX = (\d+)", src_ui)
    src_bridge = ler(u"app/radai_bridge.py")
    return {
        "parotida_ts_fora": (not oar & {"parotid_gland_left",
                                        "parotid_gland_right"}
                             and {"parotid_lnl_left",
                                  "parotid_lnl_right"} <= oar),
        "contornos": (u"def acabar_contornos(" in src_eng
                      and u"acabar_contornos(ds" in acab),
        "implicito_em_todo": _fora_do_bloco(
            acab, u"if tps == TPS_MONACO", u"ImplicitVRLittleEndian"),
        "charset_da_tc": u"ds.SpecificCharacterSet = charset" in acab,
        "rotulos": tuple(sorted((rotulos or {}).items())),
        "bridge_implicito_nos_dois": (
            v_dicom.get("SINTAXE_IMPLICITA") == u"1.2.840.10008.1.2"
            and _sintaxe_do_bridge_nos_dois()),
        "imagem_no_pipeline": u"def para_a_grade(" in ler(
            u"app/radai_image_screen.py"),
        "cd": (u"def drives_de_cd(" in src_ent and u"def e_cd(" in src_ent
               and u"E.e_cd(" in src_bridge),
        "cd_uma_vez": (u"def varredura_do_cd(" in src_ent
                       and u"E.varredura_do_cd" in src_bridge
                       and u"dcCarregar(cd.drive, cd.leitura)" in src_bridge),
        "elastic_sem_abrir": u"uiPopupSerie('el_escolha'" in ler(
            u"app/radai_elastic_screen.py"),
        "bolus_no_acervo": u'@app.post("/api/bolus/acervo")' in ler(
            u"app/radai_bolus_screen.py"),
        "barra_na_aba": (u"radai_dir_usuario" in src_ui
                         and u"radai_dir_vista" in src_ui
                         and u"radai_dir_recolhido" not in src_ui),
        "hist_max": int(m_hist.group(1)) if m_hist else None,
        "tema_no_aceite": u"data-ui-tema" in ler(
            u"app/radai_primeiro_uso.py"),
    }


def _divergencias_da_19(f, termos, politica):
    docs = {u"termos": termos or u"", u"politica": politica or u""}
    fora = []
    for chave, (doc, marca) in sorted(_MARCAS_DA_19.items()):
        fato = f.get(chave.replace(u"_termos", u"").replace(
            u"parotida_risco", u"parotida_ts_fora"))
        diz = marca in docs[doc]
        if bool(fato) is not diz:
            fora.append(u"%s: o codigo %s, e %s %s" % (
                chave, u"faz" if fato else u"NAO faz",
                u"os Termos" if doc == u"termos" else u"a Politica",
                u"diz" if diz else u"cala"))
    for _tps, rotulo in f.get("rotulos") or ():
        if (u"«%s" % rotulo) not in docs[u"termos"]:
            fora.append(u"o botao «%s» do primeiro uso nao esta nos Termos (1.5)"
                        % rotulo)
    if not f.get("rotulos"):
        fora.append(u"nao li radai_config.TPS_ROTULOS")
    hist = f.get("hist_max")
    if not hist or (u"(até %d, sem a busca do endereço)" % hist) not in docs[
            u"politica"]:
        fora.append(u"o historico da aba guarda ate %s telas, e a Politica "
                    u"nao diz o numero" % hist)
    for doc, velha in (_FRASES_DA_18_QUE_SAIRAM
                       + _FRASES_DA_19_QUE_SAIRAM_ANTES_DA_PUBLICACAO):
        if velha in docs[doc]:
            fora.append(u"%s ainda diz %r" % (doc, velha[:48]))
    return fora


def teste_o_que_a_v86_muda_na_19():
    secao(u"documentos 1.9: o retorno de campo de 19/10 (a parotida so dos "
          u"niveis, o RTSTRUCT limpo e em Implicit VR, os aneis renomeados, o "
          u"DicomBridge em um pipeline e o CD, o Elastic e o bolus no acervo, "
          u"a barra na aba; o Heart_ai e as estruturas finas mudaram na 2.0)")
    import radai_consent as CS
    termos = _plano(CS.TERMOS)
    politica = _plano(CS.POLITICA)
    checar(u"a versao dos documentos e a 1.9 ou posterior, de outubro de 2026",
           tuple(int(x) for x in CS.VERSAO_DOCS.split(u".")) >= (1, 9)
           and CS.DATA_DOCS.startswith(u"2026-10"),
           u"%s %s" % (CS.VERSAO_DOCS, CS.DATA_DOCS))
    checar(u"  e a 1.8 continua em IMPRESSOES_PUBLICADAS como foi publicada",
           CS.IMPRESSOES_PUBLICADAS.get(u"1.8", u"").startswith(u"3d4a4f87")
           and CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get(u"1.8") == 6)
    f = _fatos_da_19()
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % kv for kv in sorted(f.items())),
        all(f[k] for k in f))
    div = _divergencias_da_19(f, termos, politica)
    checar(u"o retorno de 19/10: o codigo, os Termos e a Politica dizem o "
           u"mesmo", not div, u" | ".join(div))
    for chave in sorted(k for k in f if k not in (u"rotulos", u"hist_max")):
        checar(u"  isca: o codigo deixa de fazer «%s», com os documentos de "
               u"hoje: reprova" % chave,
               bool(_divergencias_da_19(dict(f, **{chave: False}), termos,
                                        politica)))
    for chave, (doc, marca) in sorted(_MARCAS_DA_19.items()):
        t = termos.replace(marca, u"X") if doc == u"termos" else termos
        p = politica.replace(marca, u"X") if doc == u"politica" else politica
        checar(u"  isca: %s cala «%s»: reprova" % (
            u"os Termos" if doc == u"termos" else u"a Politica", chave),
            bool(_divergencias_da_19(f, t, p)))
    checar(u"  isca: o botao Xio / Focal com outro nome na tela: reprova",
           bool(_divergencias_da_19(dict(f, rotulos=((u"monaco",
                                                       u"Monaco (Elekta)"),)),
                                    termos, politica)))
    checar(u"  isca: o historico da aba com 50 telas: reprova",
           bool(_divergencias_da_19(dict(f, hist_max=50), termos, politica)))
    for doc, velha in _FRASES_DA_18_QUE_SAIRAM:
        t = termos + u" " + velha if doc == u"termos" else termos
        p = politica + u" " + velha if doc == u"politica" else politica
        checar(u"  isca: a frase da 1.8 %r de volta: reprova" % velha[:40],
               bool(_divergencias_da_19(f, t, p)))
    for doc, velha in _FRASES_DA_19_QUE_SAIRAM_ANTES_DA_PUBLICACAO:
        t = termos + u" " + velha if doc == u"termos" else termos
        p = politica + u" " + velha if doc == u"politica" else politica
        checar(u"  isca: a frase da 1.9 antes da ressalagem %r de volta: "
               u"reprova" % velha[:40], bool(_divergencias_da_19(f, t, p)))
    checar(u"  isca: o Implicit so dentro do ramo do Monaco nao conta como "
           u"em todo sistema",
           not _fora_do_bloco(u"    if tps == TPS_MONACO:\n"
                              u"        x = ImplicitVRLittleEndian\n"
                              u"    return x\n",
                              u"if tps == TPS_MONACO",
                              u"ImplicitVRLittleEndian")
           and _fora_do_bloco(u"    if tps == TPS_MONACO:\n"
                              u"        x = 1\n"
                              u"    y = ImplicitVRLittleEndian\n",
                              u"if tps == TPS_MONACO",
                              u"ImplicitVRLittleEndian"))


def _compacto(texto):
    return re.sub(r"\s+", u"", texto or u"")


_MARCAS_DA_20 = {
    "rotulos_novos": (
        (u"termos", u"(rótulo RadAI_FULL ) leva tudo"),
        (u"termos", u"(rótulo RadAI_STUDY ) é uma"),
        (u"termos", u"(rótulo RadAI_STUDY_Fast , arquivo"),
        (u"termos", u"O TotalSegmentator cru (rótulo RadAI_TS )"),
        (u"termos", u"(rótulo RadAI_ e o código dele, como RadAI_ORB )"),
        (u"politica", u"a do RadAI_STUDY, que sai logo depois de gravada"),
        (u"creditos", u"conjunto do TotalSegmentator ( RadAI_TS )"),
        (u"creditos", u"nunca no conjunto completo ( RadAI_FULL )"),
        (u"creditos", u"entregue ao TPS ( RadAI_STUDY )"),
        (u"notice", u"conjunto completo (RadAI_FULL)"),
        (u"pontos", u"conjunto do TotalSegmentator (RadAI_TS)")),
    "rotulos_antigos": (
        (u"termos", u"Os rótulos de antes."),
        (u"termos", u"continuam legíveis com os nomes que têm"),
        (u"termos", u"a série segmentada com os rótulos antigos conta como "
                    u"pronta")),
    "tags_no_study": (
        (u"termos", u"As tags próprias."),
        (u"termos", u"o nome padrão e «sugestao IA nao aprovada»"),
        (u"termos", u"com o algoritmo de geração AUTOMATIC"),
        (u"pontos", u"Com as tags próprias da estação, uma estrutura do "
                    u"entregue pode sair sem o sufixo"),
        (u"notice", u"guarda o nome padrao e \"sugestao IA nao aprovada\"")),
    "tags_recusam_alvo_e_corpo": (
        (u"termos", u"começar por GTV, CTV, ITV ou PTV"),
        (u"termos", u"nem de contorno externo (BODY, External)"),
        (u"termos", u"sem espaço no começo nem no fim e sem contrabarra")),
    "moradas_novas": (
        (u"politica", u"( nomes_proprios.json :"),
        (u"politica", u"( protocolos_proprios.json :"),
        (u"politica", u"o desinstalador oferece guardá-los"),
        (u"politica", u"os nomes próprios e os protocolos próprios, o "
                      u"acervo")),
    "protocolo_proprio": (
        (u"termos", u"Ligar é um ato, e os três que existem"),
        (u"termos", u"Um protocolo próprio pode incluir achado"),
        (u"termos", u"a declaração é pedida a cada envio à fila"),
        (u"termos", u"os protocolos RT e a seleção livre se desligam"),
        (u"termos", u"Cada protocolo vale para uma modalidade"),
        (u"pontos", u"protocolo próprio da estação que inclua achado"),
        (u"creditos", u"um protocolo próprio da estação que inclua achado")),
    "protocolo_fora_do_fast": (
        (u"termos", u"e o FAST também não"),),
    "exportar_config": (
        (u"politica", u"menos as que são desta máquina ( DEVICE , PORT e "
                      u"GUIA_VISTO )"),
        (u"politica", u"Ele não leva a chave do pseudônimo, o acervo, a fila "
                      u"nem dado de paciente"),
        (u"politica", u"não grava o caminho que não existe nesta máquina"),
        (u"termos", u"não viajam a chave do pseudônimo, o acervo nem a "
                    u"fila")),
    "sem_otimizar": (
        (u"termos", u"Ele não fecha programa nenhum e não para nem religa "
                    u"serviço do Windows"),
        (u"termos", u"( _overnight_servicos.json , na pasta do programa)"),
        (u"politica", u"o otimizar.json que o «Otimizar» de antes deixou")),
    "primeiro_uso_sem_tps": (
        (u"termos", u"O primeiro uso não pergunta o sistema de "
                    u"planejamento"),
        (u"termos", u"«Pular por agora»")),
    "anel_em_geral": (
        (u"termos", u"«Ajuste de contornos em anel»"),),
    "tema_escuro": (
        (u"termos", u"sem escolha o tema abre escuro"),
        (u"politica", u"que sem escolha abre escuro")),
    "guia": (
        (u"termos", u"«Ver o guia de novo»"),
        (u"politica", u"foi visto nesta estação ( GUIA_VISTO )")),
    "tela_cheia": (
        (u"termos", u"em modo de aplicativo, maximizado com as barras do "
                    u"Windows visíveis"),
        (u"termos", u"confere a linha de comando do processo do navegador"),
        (u"termos", u"O F11 só é enviado por pedido explícito")),
    "atualizar_um_clique": (
        (u"termos", u"A atualização com um clique."),
        (u"politica", u"Sozinha, ela não baixa nada"),
        (u"politica", u"recusa a release que não publica a soma SHA-256 do "
                      u"arquivo"),
        (u"politica", u"a pasta radai_atualizar"),
        (u"politica", u"( radai_atualizar.log , na pasta do programa)"),
        (u"politica", u"pede uma segunda confirmação")),
    "mapear": (
        (u"politica", u"abre o diálogo de mapeamento do próprio Windows"),
        (u"politica", u"o programa não os vê")),
    "varredura": (
        (u"politica", u"no «Rodar agora», no «Ver segmentação», no "
                      u"DicomBridge, na Fusão elástica e no «Gerar bólus»"),
        (u"politica", u"cada uma com o corte central primeiro"),
        (u"politica", u"pela data de modificação da pasta, sem abrir DICOM "
                      u"nenhum")),
    "importar_imagem": (
        (u"termos", u"«Importar imagem», o quarto botão do cartão de "
                    u"carregar"),
        (u"politica", u"«Importar imagem», que abre o explorador de arquivos "
                      u"do navegador")),
    "cava_separada": (
        (u"termos", u"A regra que retira a cava quando separada do coração "
                    u"continua"),),
    "esofago_fora": (
        (u"termos", u"recorte do esôfago e dos vizinhos de fora do pericárdio"),),
    "bag_furos": (
        (u"termos", u"depois de todas as subtrações, o furo de cada corte "
                    u"axial é preenchido"),),
    "delgadas": (
        (u"termos", u"Os nervos ópticos, o quiasma, os constritores da "
                    u"faringe e a tireoide saem sem suavização da máscara"),
        (u"termos", u"menos nas estruturas finas — os nervos ópticos, o "
                    u"quiasma, os constritores da faringe e a tireoide —")),
    "mandibula_cheia": (
        (u"termos", u"A mandíbula sai cheia."),
        (u"termos", u"a suavização dela nunca tira área")),
    "ventriculos": (
        (u"termos", u"são recortados para dentro do encéfalo"),),
    "ivb": (
        (u"termos", u"o nível IVb de cada lado perde a clavícula do mesmo "
                    u"lado"),
        (u"notice", u"o nivel IVb de cada lado perde a clavicula do mesmo "
                    u"lado")),
    "estruturas_novas": (
        (u"termos", u"A laringe ( Larynx_ai )"),
        (u"termos", u"( TMJ_L_ai e TMJ_R_ai )"),
        (u"termos", u"A soma dos pulmões ( Lungs_ai )")),
    "lungs_no_pescoco": (
        (u"termos", u"vai ao entregue no lugar dos dois pulmões"),),
    "brain_rm_fora": (
        (u"termos", u"O encéfalo de uma RM ( Brain_ai ) fica só no "
                    u"completo"),),
    "study_vazio": (
        (u"termos", u"«STUDY: saiu vazio»"),),
    "plano_da_serie": (
        (u"termos", u"esse acabamento é feito no plano dos cortes da "
                    u"própria série"),),
    "sem_otimizador": (
        (u"termos", u"o preparador tira dos checkpoints dos pesos dele o "
                    u"estado do otimizador"),
        (u"creditos", u"os checkpoints dele saem sem o estado do "
                      u"otimizador"),
        (u"notice", u"MODIFICACAO DOS PESOS (Apache License 2.0, secao 4, "
                    u"item b)"),
        (u"notice", u"vai sem as bibliotecas de ligacao (.lib)")),
    "chave_fora_da_nuvem": (
        (u"politica", u"numa pasta que o programa reconhece como "
                      u"sincronizada com a nuvem ela não é gravada"),),
    "aplicador": (
        (u"termos", u"Um canal que cai no meio, com canais aceitos dos dois "
                    u"lados, também impede a geração"),
        (u"termos", u"o melhor canal — o de menos trajeto sem pele"),
        (u"termos", u"a borda do volume parcial dos voxels do cruzamento")),
    "turno_acordado": (
        (u"termos", u"Com o turno aberto, o programa pede ao Windows para não "
                    u"suspender a estação"),),
    "rm_sugerida": (
        (u"termos", u"num exame sem TC, a RM do exame"),),
    "instalador_fecha_janelas": (
        (u"termos", u"fecha as janelas do navegador do programa"),),
    "elastic_pede_pasta": (
        (u"politica", u"com o campo vazio, a tela pede a pasta"),),
    "diagnosticos_e_registros": (
        (u"termos", u"em Diagnósticos e Registros"),),
    "nova_tentativa": (
        (u"politica", u"«Tentar novamente»; para atender esse botão, o "
                      u"lançador escuta só nesta estação ( 127.0.0.1 )"),),
}

_FRASES_DA_19_QUE_SAIRAM = (
    (u"termos", u"sai o que cruza a veia cava inferior e fica o do ápice"),
    (u"termos", u"Os nervos ópticos e os constritores da faringe saem sem "
                u"suavização"),
    (u"termos", u"planejamento de destino e a pasta dos exames, na tela do "
                u"primeiro uso"),
    (u"termos", u"fecha programas"),
    (u"termos", u"Diagnosticar e otimizar"),
    (u"termos", u"(rótulo STUDY_full )"),
    (u"termos", u"(rótulo RadAI_OAR )"),
    (u"termos", u"O TotalSegmentator cru ( STUDY_ts )"),
    (u"termos", u"Ligar é um ato, e os dois que existem"),
    (u"termos", u"imagem JPEG ou PNG"),
    (u"politica", u"Não baixa nada"),
    (u"politica", u"com o campo vazio, a pasta dos exames configurada"),
    (u"politica", u"a do RadAI_OAR, que sai"),
    (u"politica", u"imagens JPEG ou PNG"),
    (u"pontos", u"(STUDY_ts)"),
    (u"pontos", u"a imagem convertida de JPEG ou PNG"),
    (u"creditos", u"STUDY_ts"),
    (u"creditos", u"STUDY_full"),
    (u"creditos", u"RadAI_OAR"),
    (u"notice", u"Listas copiadas do Workstation RT"),
    (u"notice", u"rotulo STUDY_ e o codigo dele"),
)

_FORMATOS_DA_IMAGEM = ((u"JPEG", (u".jpg", u".jpeg")), (u"PNG", (u".png",)),
                       (u"TIFF", (u".tif", u".tiff")), (u"BMP", (u".bmp",)))
_POR_EXTENSO_DA_20 = {8: u"oito"}


def _docs_da_20():
    import radai_consent as CS
    import radai_credits as CR
    return {u"termos": _plano(CS.TERMOS), u"politica": _plano(CS.POLITICA),
            u"creditos": _plano(CR.pagina()), u"notice": CR.ler_notice(),
            u"pontos": u" ".join(t + u" " + d for (_c, t, d) in CS.PONTOS)}


def _fatos_da_20():
    src_eng = ler(u"app/engine.py")
    v_eng = _valores_do_modulo(src_eng)
    v_sets = _valores_do_modulo(ler(u"app/radai_sets.py"))
    src_cfg = ler(u"app/radai_config.py")
    v_cfg = _valores_do_modulo(src_cfg)
    src_cons = ler(u"app/radai_constructs.py")
    v_cons = _valores_do_modulo(src_cons)
    src_batch = ler(u"app/radai_batch.py")
    src_hnl = ler(u"app/radai_hnlnl.py")
    src_clean = ler(u"app/radai_cleaner.py")
    src_ov = ler(u"app/radai_overnight.py")
    src_pu = ler(u"app/radai_primeiro_uso.py")
    src_est = ler(u"app/radai_config_estacao.py")
    src_lanc = ler(u"app/radai_lancador.py")
    src_jan = ler(u"app/radai_janela.py")
    src_ver = ler(u"app/radai_version.py")
    src_atu = ler(u"app/radai_atualizar.py")
    src_var = ler(u"app/radai_varrer.py")
    v_var = _valores_do_modulo(src_var)
    src_ap = ler(u"app/radai_bolus_aplicador.py")
    src_upd = ler(u"packager/UPDATE.ps1")
    src_prep = ler(u"build/configurar_ambiente.py")
    v_nid = _valores_do_modulo(ler(u"app/radai_nidus.py"))
    v_nids = _valores_do_modulo(ler(u"app/radai_nidus_screen.py"))
    inst = ler(u"installer/INSTALL.ps1")
    un = ler(u"installer/UNINSTALL.ps1")
    coracao = _fonte_da_funcao(src_eng, "_acabamento_do_coracao")
    rot_antigos = v_sets.get("ROTULOS_DE_GERACOES_ANTERIORES") or {}
    contidas = v_eng.get("CONTIDAS_EM") or {}
    telas_da_varredura = [ler(u"app/" + n) for n in (
        "radai_batch.py", "radai_view.py", "radai_bridge.py",
        "radai_elastic_screen.py", "radai_bolus_screen.py")]
    exporta = _fonte_da_funcao(src_cfg, "exportar")
    m_log = re.search(r"radai_atualizar\.log.*?Length -gt (\d+)MB", src_upd,
                      re.S)
    incid = dict((str(i[0]), (i[1], i[2]))
                 for i in (v_nid.get("INCIDENCIAS") or ()) if len(i) == 3)
    return {
        "rotulos_novos": (
            v_sets.get("ROTULO_FULL") == u"RadAI_FULL"
            and v_sets.get("ROTULO_STUDY") == u"RadAI_STUDY"
            and v_sets.get("ROTULO_STUDY_FAST") == u"RadAI_STUDY_Fast"
            and v_sets.get("PREFIXO_DO_ROTULO") == u"RadAI_"),
        "rotulos_antigos": (
            {u"RadAI_OAR", u"RadAI_OAR_Fast", u"STUDY_full"} <= set(rot_antigos)
            and v_sets.get("PREFIXO_DE_ROTULO_ANTERIOR") == u"STUDY_"),
        "tags_no_study": (
            v_sets.get("DESCRICAO_DA_ROI") == u"%s - sugestao IA nao aprovada"
            and u'roi.ROIGenerationAlgorithm = "AUTOMATIC"' in src_eng
            and u"def _nomes_do_entregue(" in src_eng),
        "tags_recusam_alvo_e_corpo": (
            tuple(v_cfg.get("PREFIXOS_DE_ALVO") or ())
            == (u"GTV", u"CTV", u"ITV", u"PTV")
            and tuple(v_cfg.get("NOMES_DE_CORPO") or ())
            == (u"BODY", u"EXTERNAL")
            and bool(v_cfg.get("MOTIVO_CONTRABARRA"))),
        "moradas_novas": (
            v_cfg.get("NOME_DOS_NOMES") == u"nomes_proprios.json"
            and v_cfg.get("NOME_DOS_PROTOCOLOS") == u"protocolos_proprios.json"
            and all(n in t for n in (u"nomes_proprios.json",
                                     u"protocolos_proprios.json")
                    for t in (inst, un))),
        "protocolo_proprio": (
            u'escolha.get("achado_declarado")' in _fonte_da_funcao(
                src_batch, "tasks_do_perso")
            and u"function _pedirADeclaracao(" in src_batch
            and u'e["protocolos"] = (() if e["protocolo_proprio"] else'
            in src_batch
            and tuple(v_cfg.get("MODALIDADES") or ()) == (u"CT", u"MR")),
        "protocolo_fora_do_fast": any(
            u"o protocolo proprio vale so no PERSONALIZADO" in s
            for s in _strings_do_fonte(ler(u"app/radai_output.py"))),
        "exportar_config": (
            tuple(v_cfg.get("DA_MAQUINA") or ())
            == (u"DEVICE", u"PORT", u"GUIA_VISTO")
            and u"não será gravado" in (v_cfg.get("MOTIVO_CAMINHO") or u"")
            and bool(exporta)
            and not any(x in exporta for x in (u"segredo", u"pseudonimo",
                                               u"acervo", u"fila"))),
        "sem_otimizar": (
            u"def liberar(" not in src_clean
            and u"_APAGAVEIS" not in src_clean
            and u"def apagar_estado_antigo_do_otimizar(" in src_clean
            and u"def apagar_registro_antigo(" in src_ov
            and u"def pausar" not in src_ov),
        "primeiro_uso_sem_tps": (
            u"radai_config.TPS_PADRAO" in _fonte_da_funcao(src_pu, "gravar")
            and u'id="pu_pular"' in src_pu and u"data-tps=" not in src_pu
            and v_cfg.get("TPS_PADRAO") == u"eclipse"),
        "anel_em_geral": (u"Ajuste de contornos em anel" in src_est
                          and u'data-tps="monaco"' in src_est),
        "tema_escuro": _valores_do_modulo(ler(u"app/radai_ui.py")).get(
            "TEMA_PADRAO") == u"escuro",
        "guia": (_valores_do_modulo(ler(u"app/radai_roteiro.py")).get("CHAVE")
                 == u"GUIA_VISTO" and u"Ver o guia de novo" in src_est),
        "tela_cheia": (u'"--app=" + alvo' in src_lanc
                       and u'"--start-maximized"' in src_lanc
                       and u"VK_F11" in src_jan
                       and u"PROCESS_COMMAND_LINE_INFORMATION" in src_jan),
        "atualizar_um_clique": (
            u"def baixar_instalador(" in src_ver
            and u"a release não publica a soma SHA-256" in src_ver
            and _valores_do_modulo(src_atu).get("PASTA_DE_TRABALHO")
            == u"radai_atualizar"
            and u"def lancar_preparador(" in src_atu
            and u"def limpar_o_baixado(" in src_atu
            and m_log is not None),
        "mapear": u"WNetConnectionDialog" in src_var,
        "varredura": (
            all(u"uiVarrer" in s or u"/api/varrer" in s
                for s in telas_da_varredura)
            and u"st_mtime" in _fonte_da_funcao(src_var, "dentro_da_data")),
        "importar_imagem": (u"Importar imagem" in ler(u"app/radai_ui.py")
                            and u"imagens=" in ler(u"app/radai_bridge.py")),
        "cava_separada": (u"def _sem_a_cava_separada(" in src_eng
                          and u"protegido=prot" in coracao),
        "esofago_fora": (u"esophagus" in tuple(
            v_eng.get("FORA_DO_PERICARDIO") or ())
            and u"_vizinhos_de_fora_do_pericardio(" in coracao),
        "bag_furos": u"_sem_furo_nos_cortes(" in _fonte_da_funcao(
            src_cons, "bag_bowel_oar"),
        "delgadas": {u"optic_nerve_left", u"optic_nerve_right",
                     u"optic_chiasm", u"pharyngeal_constrictor_superior",
                     u"pharyngeal_constrictor_middle",
                     u"pharyngeal_constrictor_inferior",
                     u"thyroid_gland"} <= set(
                         v_eng.get("ESTRUTURAS_DELGADAS") or ()),
        "mandibula_cheia": (u"def mandibula_cheia(" in src_cons
                            and tuple(v_cons.get("DENTES_DA_MANDIBULA") or ())
                            == (u"teeth_lower",)
                            and u'"sem_perder_area": True' in src_eng),
        "ventriculos": (contidas.get(u"brain_ventricles") == u"brain"
                        and contidas.get(u"brain_midline") == u"brain"),
        "ivb": (u"def acabamento_do_ivb(" in src_hnl
                and u"def acabamento_da_uniao_sem_a_clavicula(" in src_hnl),
        "estruturas_novas": {u"larynx", u"tmj_left", u"tmj_right",
                             u"lungs"} <= set(
                                 v_sets.get("PERMITIDOS_NO_OAR") or ()),
        "lungs_no_pescoco": {u"lung_left", u"lung_right"} <= set(
            v_eng.get("FORA_DO_OAR_NO_PESCOCO_SEM_TORAX") or ()),
        "brain_rm_fora": tuple((v_eng.get("FORA_DO_OAR_NA_MODALIDADE")
                                or {}).get(u"MR") or ()) == (u"brain",),
        "study_vazio": u"STUDY: saiu vazio" in ler(u"app/radai_output.py"),
        "plano_da_serie": (u"def plano_da_serie(" in src_eng
                           and u"para_o_plano_da_serie(" in src_eng),
        "sem_otimizador": (u"optimizer_state" in src_prep
                           and u"def tirar_lib_do_torch(" in src_prep),
        "chave_fora_da_nuvem": all(
            u"em_pasta_sincronizada" in s for s in (
                ler(u"app/radai_records.py"), ler(u"app/radai_validation.py"))),
        "aplicador": (u"def recusa_canal_no_meio(" in src_ap
                      and u'"motivo": "nenhum_canal"' in src_ap
                      and u"def borda_por_volume_parcial(" in src_ap),
        "turno_acordado": u'STATE.get("overnight")' in _fonte_da_funcao(
            ler(u"app/radai_watcher.py"), "fila_ocupada"),
        "rm_sugerida": u"RM do exame" in ler(u"app/radai_triage.py"),
        "instalador_fecha_janelas": (
            u"function FecharJanelasDoApp" in ler(u"packager/prepare.ps1")
            and u"radai_janela" in ler(u"packager/prepare.ps1")),
        "elastic_pede_pasta": u"ESCOLHA_A_PASTA = " in ler(
            u"app/radai_elastic_screen.py"),
        "diagnosticos_e_registros": u"Diagnósticos e Registros" in ler(
            u"app/radai_panel.py"),
        "nova_tentativa": (u'srv.bind(("127.0.0.1", 0))' in src_lanc
                           and u"Tentar novamente" in ler(
                               u"app/radai_carregando.py")),
        "_teto_nova_tentativa_s": _valores_do_modulo(src_lanc).get(
            "TETO_DA_NOVA_TENTATIVA_S"),
        "_limite_do_nome": v_cfg.get("LIMITE_DO_NOME"),
        "_dias": tuple(v_var.get("DIAS_DO_FILTRO") or ()),
        "_dias_padrao": v_var.get("DIAS_PADRAO"),
        "_validade_s": v_var.get("VALIDADE_S"),
        "_teto_guardadas": v_var.get("TETO_GUARDADAS"),
        "_extensoes": tuple(_valores_do_modulo(ler(u"app/radai_image.py")).get(
            "EXTENSOES") or ()),
        "_towne": incid.get(u"Towne"),
        "_caldwell": incid.get(u"Caldwell"),
        "_malhas_mb": v_nids.get("TETO_MALHAS_MB"),
        "_soltar_s": v_nids.get("SOLTAR_APOS_S"),
        "_fechamento_laringe": v_cons.get("FECHAMENTO_DA_LARINGE_MM"),
        "_margem_atm": v_cons.get("ATM_ALEM_DO_CONDILO_MM"),
        "_limiar_hu": _valores_do_modulo(ler(u"app/radai_skin.py")).get(
            "LIMIAR_AR_HU"),
        "_log_atualizar_mb": int(m_log.group(1)) if m_log else None,
    }


def _medidas_da_20(f):
    fora, marcas = [], []

    def exige(chave, doc, montar):
        v = f.get(chave)
        try:
            marca = montar(v) if v is not None else None
        except Exception:
            marca = None
        if not marca:
            fora.append(u"nao li %s do codigo (%r)" % (chave, v))
            return
        marcas.append((doc, marca))

    exige("_limite_do_nome", u"termos",
          lambda v: u"O nome próprio tem até %d caracteres" % int(v))

    def _dias(v):
        dias = [int(d) for d in v if int(d)]
        pad = int(f.get("_dias_padrao"))
        rot = [u"%d (de partida)" % d if d == pad else u"%d" % d for d in dias]
        t = u", ".join(rot[:-1]) + u" ou " + rot[-1]
        return t + (u", ou todas" if 0 in [int(d) for d in v] else u"")
    exige("_dias", u"politica", _dias)
    exige("_validade_s", u"politica",
          lambda v: u"até %d minutos depois de ela terminar" % int(
              round(float(v) / 60.0)))
    exige("_teto_guardadas", u"politica",
          lambda v: u"no máximo %s leituras" % _POR_EXTENSO_DA_20.get(
              int(v), u"%d" % int(v)))

    def _formatos(v):
        ext = set(e.lower() for e in v)
        conhecidas = set(e for _n, es in _FORMATOS_DA_IMAGEM for e in es)
        if not ext or ext - conhecidas:
            return None
        nomes = [n for n, es in _FORMATOS_DA_IMAGEM if ext & set(es)]
        return u", ".join(nomes[:-1]) + u" ou " + nomes[-1]
    for doc in (u"termos", u"politica", u"pontos"):
        exige("_extensoes", doc, _formatos)
    exige("_towne", u"termos", lambda v: u"Towne é CRA %d" % int(v[1])
          if float(v[0]) == 0 and float(v[1]) > 0 else None)
    exige("_caldwell", u"termos", lambda v: u"Caldwell, CAU %d" % abs(
        int(v[1])) if float(v[0]) == 0 and float(v[1]) < 0 else None)
    for doc in (u"termos", u"politica"):
        exige("_malhas_mb", doc, lambda v: u"no máximo %d MB" % int(v))
        exige("_soltar_s", doc, lambda v: u"depois de %d minutos sem uso"
              % int(round(float(v) / 60.0)))
    exige("_fechamento_laringe", u"termos",
          lambda v: u"com um fechamento de %s mm" % _num_pt(v))
    exige("_margem_atm", u"termos",
          lambda v: u"com margem total de %s mm no plano axial e para cranial" % _num_pt(v))
    exige("_limiar_hu", u"termos",
          lambda v: u"cruzamento de −%d HU" % abs(int(v)) if v < 0 else None)
    exige("_log_atualizar_mb", u"politica",
          lambda v: u"recomeça quando passa de %d MB" % int(v))
    exige("_teto_nova_tentativa_s", u"politica",
          lambda v: u"com uma ficha no endereço, por até %d minutos" % int(
              round(float(v) / 60.0)))
    return fora, marcas


def _divergencias_da_20(f, docs):
    d = dict((k, _compacto(v)) for k, v in docs.items())
    fora = []
    for chave, marcas in sorted(_MARCAS_DA_20.items()):
        fato = bool(f.get(chave))
        for doc, marca in marcas:
            diz = _compacto(marca) in d[doc]
            if fato is not diz:
                fora.append(u"%s: o codigo %s, e %s %s «%s»" % (
                    chave, u"faz" if fato else u"NAO faz", doc,
                    u"diz" if diz else u"cala", marca[:60]))
    falta, medidas = _medidas_da_20(f)
    fora.extend(falta)
    for doc, marca in medidas:
        if _compacto(marca) not in d[doc]:
            fora.append(u"%s nao diz «%s», que e o que o codigo faz"
                        % (doc, marca))
    for doc, velha in _FRASES_DA_19_QUE_SAIRAM:
        if _compacto(velha) in d[doc]:
            fora.append(u"%s ainda diz %r" % (doc, velha[:60]))
    return fora


def teste_o_que_a_v87_muda_na_20():
    secao(u"documentos 2.0: o que a versao muda (os conjuntos "
          u"RadAI_FULL e RadAI_STUDY, as tags e os protocolos proprios, o "
          u"Otimizar que saiu, o primeiro acesso, a janela, a atualizacao "
          u"com um clique, a varredura, o motor, o Nidus RT e o pacote)")
    import radai_consent as CS
    checar(u"a versao dos documentos e a 2.2, de 28/10/2026",
           CS.VERSAO_DOCS == u"2.2" and CS.DATA_DOCS == u"2026-10-28",
           u"%s %s" % (CS.VERSAO_DOCS, CS.DATA_DOCS))
    checar(u"  e a 1.9 continua em IMPRESSOES_PUBLICADAS como foi publicada",
           CS.IMPRESSOES_PUBLICADAS.get(u"1.9", u"").startswith(u"087a47ba")
           and CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get(u"1.9") == 2)
    docs = _docs_da_20()
    f = _fatos_da_20()
    bools = sorted(k for k in f if not k.startswith(u"_"))
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % (k, f[k]) for k in sorted(f)),
        all(f[k] for k in bools) and sorted(_MARCAS_DA_20) == bools,
        u"sem fato ou sem marca: %s" % sorted(set(bools)
                                              ^ set(_MARCAS_DA_20)))
    div = _divergencias_da_20(f, docs)
    checar(u"o que a 2.0 muda: o codigo, os Termos, a Politica, os "
           u"pontos do aceite, os Creditos e o NOTICE dizem o mesmo",
           not div, u" | ".join(div))
    for chave in bools:
        checar(u"  isca: o codigo deixa de fazer «%s», com os documentos de "
               u"hoje: reprova" % chave,
               bool(_divergencias_da_20(dict(f, **{chave: False}), docs)))
    for chave, marcas in sorted(_MARCAS_DA_20.items()):
        for doc, marca in marcas:
            d2 = dict(docs)
            d2[doc] = _compacto(docs[doc]).replace(_compacto(marca), u"X")
            checar(u"  isca: %s cala «%s» de %s: reprova" % (
                doc, marca[:40], chave), bool(_divergencias_da_20(f, d2)))
    for doc, velha in _FRASES_DA_19_QUE_SAIRAM:
        d2 = dict(docs)
        d2[doc] = docs[doc] + u" " + velha
        checar(u"  isca: %s volta a dizer %r: reprova" % (doc, velha[:40]),
               bool(_divergencias_da_20(f, d2)))
    for chave, novo in (("_limite_do_nome", 20), ("_dias_padrao", 3),
                        ("_dias", (1, 3, 7, 14, 0)), ("_validade_s", 1800.0),
                        ("_teto_guardadas", 9),
                        ("_extensoes", (u".png", u".jpg", u".gif")),
                        ("_towne", (0.0, 35.0)), ("_caldwell", (0.0, -20.0)),
                        ("_malhas_mb", 32), ("_soltar_s", 300.0),
                        ("_fechamento_laringe", 5.0), ("_margem_atm", 2.0),
                        ("_limiar_hu", -400.0), ("_log_atualizar_mb", 2),
                        ("_teto_nova_tentativa_s", 300.0),
                        ("_limiar_hu", None)):
        checar(u"  isca: o codigo muda %s para %r, com os documentos de "
               u"hoje: reprova" % (chave, novo),
               bool(_divergencias_da_20(dict(f, **{chave: novo}), docs)))


_MARCAS_DA_20_RESSELADA = {
    "janela_pelo_titulo": (
        (u"termos", u"motor a acha pelo título que termina na ficha da tela"),
        (u"termos", u"se isso não basta, confere a linha de comando do "
                    u"processo do navegador"),
        (u"termos", u"O log informa o método de identificação sem título "
                    u"nem ficha")),
    "janela_reconferida": (
        (u"termos", u"a janela guardada é reconferida pelo processo e classe"),),
    "f11_por_pedido": (
        (u"termos", u"«Maximizar» da porta pede explicitamente a tela cheia "
                    u"pelo F11"),
        (u"termos", u"«Restaurar»; o F11 também permite sair dela")),
    "enxugar_no_registro": (
        (u"termos", u"o preparador tira o estado do otimizador também dos "
                    u"checkpoints dos níveis cervicais, do modelo do encéfalo "
                    u"em TC, do MOOSE e do CADS"),
        (u"termos", u"e não na instalação direta numa estação"),
        (u"termos", u"conferido pela soma SHA-256 que o registro de modelos "
                    u"guarda para ele"),
        (u"creditos", u"os checkpoints dos níveis cervicais, do encéfalo em "
                      u"TC, do MOOSE e do CADS também saem sem o estado do "
                      u"otimizador"),
        (u"notice", u"MODIFICACAO DO PESO (CC BY-SA 4.0, secao 3(a)(1)(B))"),
        (u"notice", u"MODIFICACAO DOS PESOS (CC BY 4.0, secao 3(a)(1)(B))"),
        (u"notice", u"MODIFICACAO DOS PESOS. A CC0 nao pede que ela seja "
                    u"indicada")),
    "estacao_aceita_os_dois": (
        (u"termos", u"A estação aceita, de cada um, o arquivo da origem ou o "
                    u"enxuto"),),
    "vascular_pela_segmentacao": (
        (u"termos", u"tira o osso da projeção pela segmentação que o "
                    u"ContourLab gravou para a série"),
        (u"termos", u"lida só na memória do programa, como no Nidus RT"),
        (u"termos", u"sem HU, como na RM, e sem segmentação, o osso fica na "
                    u"projeção")),
    "atm_plano_medio": (
        (u"termos", u"O lado sai de um plano médio que passa pelo centro do "
                    u"crânio sem a mandíbula"),
        (u"termos", u"do encéfalo, da vértebra C1 ou da C2"),
        (u"termos", u"o log da série diz qual referência valeu")),
    "aplicador_dois_eixos": (
        (u"termos", u"traça os canais nas duas direções perpendiculares à "
                    u"colocação e fica com a que acomoda mais canais"),),
    "caixa_sugerida": (
        (u"termos", u"a recusa propõe uma caixa aparada"),
        (u"termos", u"«Usar a caixa sugerida»: a caixa só muda com esse "
                    u"clique")),
    "fundo_cego_ate_o_fundo": (
        (u"termos", u"No canal de fundo cego, a pele é exigida só até o fundo "
                    u"do canal"),),
    "imagem_medida_e_ordem": (
        (u"termos", u"a escala medida por você com dois cliques numa "
                    u"distância conhecida da própria imagem"),
        (u"termos", u"A ordem dos cortes é a dos arquivos, e só você a "
                    u"inverte"),
        (u"termos", u"a tela só converte depois que você confere"),
        (u"politica", u"digitada ou medida numa distância conhecida da própria "
                      u"imagem"),
        (u"politica", u"se a ordem dos cortes foi invertida")),
    "rt_utils_reproduzido": (
        (u"notice", u"A montagem da ROI do rt-utils, reproduzida no motor"),
        (u"notice", u"Copyright (c) 2021 Qurit")),
}

_FRASES_DA_20_QUE_SAIRAM_ANTES_DA_PUBLICACAO = (
    (u"termos", u"nenhuma outra janela do navegador é tocada"),
    (u"termos", u"o motor procura a janela do programa pelo título, confere"),
    (u"termos", u"A escala e a espessura dela são digitadas por você"),
    (u"politica", u"a escala, confirmada ao lado do MPR"),
    (u"politica", u"guarda a geometria que você digitou e o ID gerado"),
)

_DO_REGISTRO_ENXUTO = ("hnlnl", "cranio_buti", "moose", "cads_open")
_POR_EXTENSO_DA_20R = {10: u"dez"}


def _toda_chamada_sob_teste(src, chamada, teste):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return False
    pais = dict((f, no) for no in ast.walk(arv)
                for f in ast.iter_child_nodes(no))
    achou = False
    for no in ast.walk(arv):
        if not (isinstance(no, ast.Call)
                and getattr(no.func, "id", None) == chamada):
            continue
        achou = True
        p = pais.get(no)
        while p is not None and not (
                isinstance(p, ast.If) and u" ".join(
                    (ast.get_source_segment(src, p.test) or u"").split())
                == teste):
            p = pais.get(p)
        if p is None:
            return False
    return achou


def _f11_por_ato_explicito(src):
    def chamadas_guardadas(nome, teste):
        trecho = _fonte_da_funcao(src, nome)
        try:
            arv = ast.parse(trecho)
        except SyntaxError:
            return False
        pais = {f: n for n in ast.walk(arv) for f in ast.iter_child_nodes(n)}
        chamadas = [n for n in ast.walk(arv) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "tecla_f11"]
        for n in chamadas:
            n = pais.get(n)
            while n is not None:
                if isinstance(n, ast.If) and ast.unparse(n.test) == teste:
                    break
                n = pais.get(n)
            if n is None:
                return False
        return bool(chamadas)
    return (chamadas_guardadas("tela_cheia", "alternar")
            and chamadas_guardadas("registrar", "not pf.tem_barra(h)")
            and '"tela_cheia_pedida": False' in _fonte_da_funcao(src, "registrar")
            and "SW_MAXIMIZE" in _fonte_da_funcao(src, "registrar"))


def _fatos_da_20_resselada():
    import radai_models as RM
    src_jan = ler(u"app/radai_janela.py")
    v_jan = _valores_do_modulo(src_jan)
    volta = _fonte_da_funcao(src_jan, "_uma_volta")
    tela_cheia = _fonte_da_funcao(src_jan, "tela_cheia")
    src_prep = ler(u"build/configurar_ambiente.py")
    src_mod = ler(u"app/radai_models.py")
    v_hnl = _valores_do_modulo(ler(u"app/radai_hnlnl.py"))
    src_vas = ler(u"app/radai_recon3d_vascular.py")
    v_vas = _valores_do_modulo(src_vas)
    src_cons = ler(u"app/radai_constructs.py")
    v_cons = _valores_do_modulo(src_cons)
    src_ap = ler(u"app/radai_bolus_aplicador.py")
    src_ims = ler(u"app/radai_image_screen.py")
    v_ims = _valores_do_modulo(src_ims)
    src_eng = ler(u"app/engine.py")
    adic = _fonte_da_funcao(src_eng, "_adicionar_roi")
    modelos = getattr(RM, "MODELOS", None) or {}
    enxutos = [k for k in _DO_REGISTRO_ENXUTO
               if (modelos.get(k) or {}).get("enxuto")]
    return {
        "janela_pelo_titulo": (
            u"def pelo_titulo(" in src_jan and bool(volta)
            and volta.find(u"pelo_titulo(") < volta.find(u"janela_do_app(")
            and u"LOG_PELO_TITULO" in volta and u"LOG_PELA_LINHA" in volta
            and bool(v_jan.get("LOG_PELO_TITULO"))),
        "janela_reconferida": (
            u"def ainda_e_a_mesma(" in src_jan
            and u"ainda_e_a_mesma(h, d, pf)" in src_jan),
        "f11_por_pedido": (
            _f11_por_ato_explicito(src_jan)
            and u"trazer_para_frente(h)" in tela_cheia
            and tela_cheia.find(u"trazer_para_frente(h)")
            < tela_cheia.find(u"tecla_f11(h)")),
        "enxugar_no_registro": (
            u"def enxugar_modelo_do_registro(" in src_prep
            and _toda_chamada_sob_teste(src_prep, "enxugar_modelo_do_registro",
                                        u'not ctx.get("instalar")')
            and len(enxutos) == len(_DO_REGISTRO_ENXUTO)),
        "estacao_aceita_os_dois": (
            u"def _e_o_enxuto(" in src_mod
            and bool(v_hnl.get("VERSAO_DOS_PESOS", {}).get(
                "fold0_bytes_enxuto"))),
        "vascular_pela_segmentacao": (
            u"NS.osso_da_segmentacao(" in _fonte_da_funcao(src_vas, "ler_osso")
            and tuple(v_vas.get("MODOS_DO_OSSO") or ())
            == (u"segmentacao", u"limiar", u"fica")),
        "atm_plano_medio": (
            u"def plano_medio_da_atm(" in src_cons
            and tuple(a[0] for a in (v_cons.get(
                "ANCORAS_DO_PLANO_MEDIO_DA_ATM") or ()))
            == (u"skull", u"brain", u"vertebrae_C1", u"vertebrae_C2")
            and u"(ac & mc)" in _fonte_da_funcao(src_cons,
                                                 "plano_medio_da_atm")),
        "aplicador_dois_eixos": (u"def escolher_eixo(" in src_ap
                                 and u"def eixos_do_canal(" in src_ap),
        "caixa_sugerida": (u"def caixa_sugerida(" in src_ap
                           and u"Usar a caixa sugerida" in ler(
                               u"app/radai_bolus_screen.py")),
        "fundo_cego_ate_o_fundo": u'P["trajeto"] != "cego"' in _fonte_da_funcao(
            src_ap, "trecho_exigido"),
        "imagem_medida_e_ordem": (
            v_ims.get("BOTAO_MEDIR") == u"Medir uma distância conhecida"
            and v_ims.get("BOTAO_INVERTER") == u"Inverter a ordem dos cortes"
            and u"ordem_invertida" in ler(u"app/radai_image.py")),
        "rt_utils_reproduzido": (
            u"ds_helper.create_structure_set_roi(" in adic
            and u"image_helper.get_contours_coords(" in adic),
        "_osso_hu": v_vas.get("OSSO_HU"),
        "_osso_margem_mm": v_vas.get("OSSO_MARGEM_MM"),
        "_n_hnlnl": len((modelos.get("hnlnl") or {}).get("enxuto") or {}),
        "_rt_utils": _valores_do_modulo(src_eng).get(
            "RT_UTILS_DA_MONTAGEM_RAPIDA"),
    }


def _medidas_da_20_resselada(f):
    fora, marcas = [], []

    def exige(chave, doc, montar):
        v = f.get(chave)
        try:
            marca = montar(v) if v is not None else None
        except Exception:
            marca = None
        if not marca:
            fora.append(u"nao li %s do codigo (%r)" % (chave, v))
            return
        marcas.append((doc, marca))

    exige("_osso_hu", u"termos", lambda v: u"um limiar de %d HU" % int(v))
    exige("_osso_margem_mm", u"termos",
          lambda v: u"o vaso a menos de %s mm do osso" % _num_pt(v))
    exige("_n_hnlnl", u"notice", lambda v: u"dos %s checkpoints do ensemble"
          % _POR_EXTENSO_DA_20R[int(v)])
    exige("_rt_utils", u"notice",
          lambda v: u"a montagem da ROI do rt-utils %s" % v)
    return fora, marcas


def _divergencias_da_20_resselada(f, docs):
    d = dict((k, _compacto(v)) for k, v in docs.items())
    fora = []
    for chave, marcas in sorted(_MARCAS_DA_20_RESSELADA.items()):
        fato = bool(f.get(chave))
        for doc, marca in marcas:
            diz = _compacto(marca) in d[doc]
            if fato is not diz:
                fora.append(u"%s: o codigo %s, e %s %s «%s»" % (
                    chave, u"faz" if fato else u"NAO faz", doc,
                    u"diz" if diz else u"cala", marca[:60]))
    falta, medidas = _medidas_da_20_resselada(f)
    fora.extend(falta)
    for doc, marca in medidas:
        if _compacto(marca) not in d[doc]:
            fora.append(u"%s nao diz «%s», que e o que o codigo faz"
                        % (doc, marca))
    for doc, velha in _FRASES_DA_20_QUE_SAIRAM_ANTES_DA_PUBLICACAO:
        if _compacto(velha) in d[doc]:
            fora.append(u"%s ainda diz %r" % (doc, velha[:60]))
    return fora


def teste_o_que_a_resselagem_muda_na_20():
    secao(u"documentos 2.0, a resselagem antes da publicacao: a janela pelo "
          u"titulo, o enxugar dos modelos do registro, o Vascular pela "
          u"segmentacao, o plano medio da ATM, o aplicador, a imagem do "
          u"DicomBridge e o rt-utils no NOTICE")
    import radai_consent as CS
    trocas = CS.IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO.get(u"2.0") or ()
    checar(u"a primeira resselagem da 2.0 trocou a impressao da primeira "
           u"selagem (4ed91a7fa1c7)",
           len(trocas) >= 1 and trocas[0][0] == u"4ed91a7fa1c7",
           u"%s" % [t[0] for t in trocas])
    docs = _docs_da_20()
    f = _fatos_da_20_resselada()
    bools = sorted(k for k in f if not k.startswith(u"_"))
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % (k, f[k]) for k in sorted(f)),
        all(f[k] for k in bools) and sorted(_MARCAS_DA_20_RESSELADA) == bools,
        u"sem fato ou sem marca: %s" % sorted(
            set(bools) ^ set(_MARCAS_DA_20_RESSELADA)))
    div = _divergencias_da_20_resselada(f, docs)
    checar(u"a resselagem: o codigo, os Termos, a Politica, os Creditos e o "
           u"NOTICE dizem o mesmo", not div, u" | ".join(div))
    for chave in bools:
        checar(u"  isca: o codigo deixa de fazer «%s», com os documentos de "
               u"hoje: reprova" % chave,
               bool(_divergencias_da_20_resselada(dict(f, **{chave: False}),
                                                  docs)))
    for chave, marcas in sorted(_MARCAS_DA_20_RESSELADA.items()):
        for doc, marca in marcas:
            d2 = dict(docs)
            d2[doc] = _compacto(docs[doc]).replace(_compacto(marca), u"X")
            checar(u"  isca: %s cala «%s» de %s: reprova" % (
                doc, marca[:40], chave),
                bool(_divergencias_da_20_resselada(f, d2)))
    for doc, velha in _FRASES_DA_20_QUE_SAIRAM_ANTES_DA_PUBLICACAO:
        d2 = dict(docs)
        d2[doc] = docs[doc] + u" " + velha
        checar(u"  isca: %s volta a dizer %r: reprova" % (doc, velha[:40]),
               bool(_divergencias_da_20_resselada(f, d2)))
    for chave, novo in (("_osso_hu", 500.0), ("_osso_margem_mm", 3.0),
                        ("_n_hnlnl", 5), ("_rt_utils", u"1.2.8"),
                        ("_osso_hu", None)):
        checar(u"  isca: o codigo muda %s para %r, com os documentos de "
               u"hoje: reprova" % (chave, novo),
               bool(_divergencias_da_20_resselada(dict(f, **{chave: novo}),
                                                  docs)))
    _so_no_pacote = u'not ctx.get("instalar")'
    checar(u"  isca: o enxugar do registro fora do teste da instalacao "
           u"direta nao conta como so no pacote novo",
           not _toda_chamada_sob_teste(
               u"enxugar_modelo_do_registro(a)\n",
               "enxugar_modelo_do_registro", _so_no_pacote)
           and not _toda_chamada_sob_teste(
               u'if ctx.get("instalar"):\n    enxugar_modelo_do_registro(a)\n',
               "enxugar_modelo_do_registro", _so_no_pacote)
           and _toda_chamada_sob_teste(
               u'if not ctx.get("instalar"):\n'
               u'    enxugar_modelo_do_registro(a)\n',
               "enxugar_modelo_do_registro", _so_no_pacote))


_MARCAS_DA_20_SEGUNDA_RESSELAGEM = {
    "ts_enxuga_na_instalacao_direta": (
        (u"termos", u"A partir da versão 8.7, nos pacotes montados e também "
                    u"na instalação direta numa estação, o preparador tira "
                    u"dos checkpoints dos pesos dele o estado do otimizador"),
        (u"creditos", u"nos pacotes montados e também na instalação direta, "
                      u"os checkpoints dele saem sem o estado do otimizador"),
        (u"notice", u"nos pacotes montados e tambem na instalacao direta numa "
                    u"estacao, o preparador tira dos checkpoints dos pesos do "
                    u"TotalSegmentator")),
    "mapa_nv_viaja_sob_apache": (
        (u"notice", u"O MAPA DE ROTULOS VIAJA NO INSTALADOR LEVE, sob a "
                    u"Apache License 2.0"),
        (u"notice", u"a NVIDIA Open Model License vale so para os pesos")),
    "cads_da_publicacao_open": (
        (u"notice", u"A CC BY-SA 4.0 DA VARIANTE `open` E A QUE A PUBLICACAO "
                    u"DELA DECLARA"),),
}

_FRASES_DA_20_QUE_SAIRAM_NA_SEGUNDA_RESSELAGEM = (
    (u"termos", u"Nos pacotes montados a partir da versão 8.7, o preparador "
                u"tira dos checkpoints dos pesos dele"),
    (u"creditos", u"Nos pacotes montados a partir da versão 8.7, os "
                  u"checkpoints dele saem"),
    (u"notice", u"Nos pacotes montados a partir da v8.7, o preparador tira "
                u"dos checkpoints dos pesos do TotalSegmentator"),
)


def _alguma_chamada_sob_instalar(src, chamada):
    try:
        arv = ast.parse(src or u"")
    except SyntaxError:
        return True
    pais = dict((f, no) for no in ast.walk(arv)
                for f in ast.iter_child_nodes(no))
    for no in ast.walk(arv):
        if not (isinstance(no, ast.Call)
                and getattr(no.func, "id", None) == chamada):
            continue
        p = pais.get(no)
        while p is not None:
            if isinstance(p, ast.If) and u"instalar" in (
                    ast.get_source_segment(src, p.test) or u""):
                return True
            p = pais.get(p)
    return False


def _fatos_da_20_segunda_resselagem():
    import radai_models as RM
    src_prep = ler(u"build/configurar_ambiente.py")
    src_emp = ler(u"build/empacotar_instalador.py")
    v_emp = _valores_do_modulo(src_emp)
    modelos = getattr(RM, "MODELOS", None) or {}
    nv = modelos.get("nv_segment_ct") or {}
    cads = modelos.get("cads_open") or {}
    mapa = os.path.isfile(_componentes.fonte(
        u"tools/data/nv_segment_ct_labels.json"))
    return {
        "ts_enxuga_na_instalacao_direta": (
            u"enxugar_pasta_de_peso(py_do_pacote" in _fonte_da_funcao(
                src_prep, "instalar_peso_ts")
            and u'("pesos", "etapa_pesos")' in _fonte_da_funcao(
                src_prep, "etapas_do_modo")
            and not _alguma_chamada_sob_instalar(src_prep,
                                                 "enxugar_pasta_de_peso")),
        "mapa_nv_viaja_sob_apache": (
            mapa and nv.get("derivar_labels_de") == u"configs/metadata.json"
            and (u"tools", u"tools") in tuple(v_emp.get("PASTAS") or ())
            and u"data" not in set(v_emp.get("FORA") or ())),
        "cads_da_publicacao_open": (
            u"cads-model-open_v1.0.0" in u"".join(
                cads.get("url_direta") or ())),
    }


def _divergencias_da_20_segunda_resselagem(f, docs):
    d = dict((k, _compacto(v)) for k, v in docs.items())
    fora = []
    for chave, marcas in sorted(_MARCAS_DA_20_SEGUNDA_RESSELAGEM.items()):
        fato = bool(f.get(chave))
        for doc, marca in marcas:
            diz = _compacto(marca) in d[doc]
            if fato is not diz:
                fora.append(u"%s: o codigo %s, e %s %s «%s»" % (
                    chave, u"faz" if fato else u"NAO faz", doc,
                    u"diz" if diz else u"cala", marca[:60]))
    for doc, velha in _FRASES_DA_20_QUE_SAIRAM_NA_SEGUNDA_RESSELAGEM:
        if _compacto(velha) in d[doc]:
            fora.append(u"%s ainda diz %r" % (doc, velha[:60]))
    return fora


def teste_o_que_a_segunda_resselagem_muda_na_20():
    secao(u"documentos 2.0, a segunda resselagem antes da publicacao: o "
          u"enxugar do TotalSegmentator tambem na instalacao direta, o mapa "
          u"de rotulos do NV-Segment-CT sob a Apache-2.0 e a licenca do CADS "
          u"pela publicacao da variante")
    import radai_consent as CS
    trocas = CS.IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO.get(u"2.0") or ()
    checar(u"a 2.0 foi resselada duas vezes, e as impressoes trocadas sao a "
           u"da primeira selagem (4ed91a7fa1c7) e a da primeira resselagem "
           u"(a876f8e0154f)",
           CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get(u"2.0") == 2
           and [t[0] for t in trocas] == [u"4ed91a7fa1c7", u"a876f8e0154f"],
           u"%s %s" % (CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get(u"2.0"),
                       [t[0] for t in trocas]))
    checar(u"  e a impressao em vigor nao e nenhuma das trocadas",
           not any(CS.IMPRESSOES_PUBLICADAS.get(u"2.0", u"").startswith(t[0])
                   for t in trocas))
    docs = _docs_da_20()
    f = _fatos_da_20_segunda_resselagem()
    checar(u"  (li do codigo: %s)" % u", ".join(
        u"%s=%s" % (k, f[k]) for k in sorted(f)),
        all(f.values()) and sorted(f) == sorted(
            _MARCAS_DA_20_SEGUNDA_RESSELAGEM),
        u"sem fato ou sem marca: %s" % sorted(
            set(f) ^ set(_MARCAS_DA_20_SEGUNDA_RESSELAGEM)))
    div = _divergencias_da_20_segunda_resselagem(f, docs)
    checar(u"a segunda resselagem: o codigo, os Termos, os Creditos e o "
           u"NOTICE dizem o mesmo", not div, u" | ".join(div))
    for chave in sorted(f):
        checar(u"  isca: o codigo deixa de fazer «%s», com os documentos de "
               u"hoje: reprova" % chave,
               bool(_divergencias_da_20_segunda_resselagem(
                   dict(f, **{chave: False}), docs)))
    for chave, marcas in sorted(_MARCAS_DA_20_SEGUNDA_RESSELAGEM.items()):
        for doc, marca in marcas:
            d2 = dict(docs)
            d2[doc] = _compacto(docs[doc]).replace(_compacto(marca), u"X")
            checar(u"  isca: %s cala «%s» de %s: reprova" % (
                doc, marca[:40], chave),
                bool(_divergencias_da_20_segunda_resselagem(f, d2)))
    for doc, velha in _FRASES_DA_20_QUE_SAIRAM_NA_SEGUNDA_RESSELAGEM:
        d2 = dict(docs)
        d2[doc] = docs[doc] + u" " + velha
        checar(u"  isca: %s volta a dizer %r: reprova" % (doc, velha[:40]),
               bool(_divergencias_da_20_segunda_resselagem(f, d2)))
    checar(u"  isca: o enxugar do TotalSegmentator sob um teste da "
           u"instalacao conta como fora da instalacao direta",
           _alguma_chamada_sob_instalar(
               u'if not ctx.get("instalar"):\n    enxugar_pasta_de_peso(a)\n',
               "enxugar_pasta_de_peso")
           and not _alguma_chamada_sob_instalar(
               u"def f(a):\n    enxugar_pasta_de_peso(a)\n",
               "enxugar_pasta_de_peso"))


_MARCAS_DA_21 = {
    "rgb_study": (("termos", u"RGB de cada estrutura do STUDY, mesmo sem trocar seu nome"),
                  ("termos", u"São três inteiros de 0 a 255"),
                  ("termos", u"modo «Tags próprias»; em «Padrão» fica guardada sem valer"),
                  ("termos", u"O FULL mantém as cores padrão"),
                  ("politica", u"o nome e a cor RGB que a estação escolheu")),
    "roots": (("politica", u"lista de pastas do turno ( ROOTS )"),
              ("termos", u"O botão «Adicionar pasta» permite escolher mais de uma origem"),
              ("termos", _MARCA_OV_ROOT_NO_SEGUINTE)),
    "aguarda_iniciar": (("termos", _MARCA_OV_INICIA),
                        ("termos", u"clicar em INICIAR"),
                        ("termos", u"um cartão novo ou recuperado sem essa autorização espera")),
    "janela": (("termos", u"maximizado com as barras do Windows visíveis"),
               ("termos", u"O F11 só é enviado por pedido explícito")),
    "tmj": (("termos", u"com margem total de 3 mm no plano axial e para cranial"),),
    "heart": (("termos", u"somente nos cortes em que existe máscara da veia cava inferior"),
              ("termos", u"Nos outros cortes essa restrição não é aplicada"),
              ("termos", u"A cartilagem costal sai do coração, inclusive após o preenchimento"),
              ("termos", u"a do parênquima mais 3 mm fixos — 5,5 mm com o padrão")),
    "bag": (("termos", u"cartilagem costal é retirada também depois desse preenchimento"),),
    "lnl": (("termos", u"a união perde as intersecções com a mandíbula, os escalenos anteriores, médios e posteriores"),
            ("termos", u"as clavículas e o hioide"),
            ("termos", u"A união não desconta mais os esternocleidomastoideos nem os platismas bilaterais")),
    "vasos_sem_pa": (("termos", u"As tarefas atuais não fornecem máscaras separadas das artérias pulmonares e do tronco pulmonar"),),
    "moose_opcional": (("termos", u"programa não inventa essas partes nem aciona o MOOSE para desmembrá-la"),
                       ("termos", u"O MOOSE continua como comparação opcional, fora do FAST e do AUTO")),
}
_FRASES_REVOGADAS_NA_21 = (
    ("termos", u"«Salvar e iniciar»"),
    ("termos", u"em modo de aplicativo e em tela cheia"),
    ("termos", u"manda o F11 uma vez por janela"),
    ("termos", u"nenhum pixel desses três sai"),
    ("termos", u"com 1 mm de margem em 3D"),
    ("termos", u"com margem total de 1 mm em 3D"),
    ("termos", u"As artérias pulmonares e o tronco pulmonar entram nesse composto apenas quando as tarefas já pedidas fornecerem máscaras com esses nomes"),
)


def _fontes_da_21():
    return {n: ler(u"app/" + n + u".py") for n in (
        "radai_config", "radai_watcher", "radai_batch", "radai_queue_state",
        "radai_todo", "radai_janela", "radai_lancador", "radai_constructs",
        "radai_hnlnl", "radai_moose", "engine")}


def _fatos_da_21(src=None):
    src = _fontes_da_21() if src is None else src
    cfg, vig, batch, fila = (src[n] for n in (
        "radai_config", "radai_watcher", "radai_batch", "radai_queue_state"))
    cons, eng = src["radai_constructs"], src["engine"]
    antes = _fonte_da_funcao(cons, "coracao_antes_da_suavizacao")
    modelos = _valores_do_modulo(src["radai_moose"]).get("MODELOS") or {}
    tabelas = _valores_do_modulo(eng)
    arterias = set((tabelas.get("COMPOSTOS") or {}).get("great_arteries") or ())
    pulmonares = {"pulmonary_artery", "pulmonary_artery_left",
                  "pulmonary_artery_right", "pulmonary_trunk"}
    return {
        "rgb_study": ('"cores": _limpar_cores' in cfg
                      and 'd.get("modo") != "proprios"' in _fonte_da_funcao(cfg, "cor_propria")
                      and "_cfg.cor_propria(nome_final" in _fonte_da_funcao(eng, "_nomes_do_entregue")),
        "roots": ('ROOTS' in _valores_do_modulo(cfg).get("CHAVES_DE_PASTA", ())
                  and "def _normalizar_raizes(" in vig
                  and "ROOTS" in _fonte_da_funcao(vig, "root_para_o_proximo_turno")),
        "aguarda_iniciar": ('"iniciar_pedido": False' in _fonte_da_funcao(fila, "overnight")
                            and 'not turno[0].get("iniciar_pedido")' in _fonte_da_funcao(fila, "turno_na_vez")
                            and 'c["iniciar_pedido"] = True' in _fonte_da_funcao(fila, "autorizar_turno")
                            and "_fila.autorizar_turno()" in batch
                            and "iniciar_pedido" in src["radai_todo"]
                            and not _overnight_inicia_divergente(batch, _MARCA_OV_INICIA)),
        "janela": ('"--start-maximized"' in src["radai_lancador"]
                   and _f11_por_ato_explicito(src["radai_janela"])),
        "tmj": _valores_do_modulo(cons).get("ATM_ALEM_DO_CONDILO_MM") == 3.0,
        "heart": ("novo & (~fatias | peri)" in antes
                  and "cava.any(axis=outros)" in antes
                  and "sem_cartilagem_costal(m, masks, cru)" in antes
                  and "sem_cartilagem_costal(" in _fonte_da_funcao(eng, "_acabamento_do_coracao")
                  and _valores_do_modulo(eng).get("SUAVIZACAO_A_MAIS_DO_CORACAO_MM") == 3.0),
        "bag": ("sem_cartilagem_costal(novo, masks)" in _fonte_da_funcao(cons, "acabamento_da_bag_oar")
                and _fonte_da_funcao(cons, "acabamento_da_bag_oar").find("_sem_furo_nos_cortes(")
                < _fonte_da_funcao(cons, "acabamento_da_bag_oar").find("sem_cartilagem_costal(")),
        "lnl": {"mandible", "anterior_scalene_left", "anterior_scalene_right",
                "middle_scalene_left", "middle_scalene_right", "posterior_scalene_left", "posterior_scalene_right",
                "clavicula_left", "clavicula_right", "hyoid"} == set(
                    _valores_do_modulo(src["radai_hnlnl"]).get("FORA_DA_UNIAO") or ()),
        "vasos_sem_pa": ({"common_carotid_artery_left", "common_carotid_artery_right",
                           "internal_carotid_artery_left", "internal_carotid_artery_right"} <= arterias
                         and not (pulmonares & arterias)
                         and not (pulmonares & set(tabelas.get("_ARTERIAS_COM_MARGEM") or ()))),
        "moose_opcional": (_comparacao_so_no_perso(batch, vig)
                           and "moose" not in _fonte_da_funcao(eng, "_construir_coracao").lower()
                           and {k: v.get("id_moose") for k, v in modelos.items()} == {
                               "cardiac": "clin_ct_cardiac", "body_composition": "clin_ct_body_composition"}),
    }


def _divergencias_da_21(f, docs):
    fora = []
    d = {k: _compacto(v) for k, v in docs.items()}
    for chave, marcas in sorted(_MARCAS_DA_21.items()):
        for doc, marca in marcas:
            if bool(f.get(chave)) is not (_compacto(marca) in d[doc]):
                fora.append(u"%s: %s diverge de «%s»" % (chave, doc, marca))
    for doc, marca in _FRASES_REVOGADAS_NA_21:
        if _compacto(marca) in d[doc]:
            fora.append(u"%s ainda promete «%s»" % (doc, marca))
    return fora


def teste_o_que_o_retorno_de_campo_muda_na_21():
    secao(u"documentos atuais: garantias herdadas da 2.1 e recortes atualizados na 2.2")
    import radai_consent as CS
    import radai_config as CFG
    docs, src = _docs_da_20(), _fontes_da_21()
    f = _fatos_da_21(src)
    checar(u"a 2.2 e de 28/10/2026; a 2.0 publicada permanece intacta",
           CS.VERSAO_DOCS == "2.2" and CS.DATA_DOCS == "2026-10-28"
           and CS.IMPRESSOES_PUBLICADAS.get("2.0") ==
               "c6b3c126af07cd56a14230008af944a09824c7d7f9ed51b834dcfdca4728aa97"
           and CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get("2.0") == 2)
    trocas = CS.IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO.get("2.1") or ()
    checar(u"a segunda resselagem da 2.1 registra o selo substituido e o motivo",
           CS.RESSELAGENS_ANTES_DA_PUBLICACAO.get("2.1") == 2
           and [h for h, _ in trocas] == ["fedb3e1174c9", "6c55fafa4fb4"]
           and not _trocas_divergentes(CS.IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO,
                                      CS.RESSELAGENS_ANTES_DA_PUBLICACAO,
                                      CS.IMPRESSOES_PUBLICADAS))
    checar(u"li os fatos correntes do codigo", all(f.values()) and set(f) == set(_MARCAS_DA_21), repr(f))
    div = _divergencias_da_21(f, docs)
    checar(u"as novas regras do codigo concordam com os documentos 2.1", not div, u" | ".join(div))
    for chave in sorted(f):
        checar(u"  isca 2.1: o codigo deixa de fazer %s: reprova" % chave,
               bool(_divergencias_da_21(dict(f, **{chave: False}), docs)))
    for chave, marcas in sorted(_MARCAS_DA_21.items()):
        for doc, marca in marcas:
            d = dict(docs)
            d[doc] = _compacto(d[doc]).replace(_compacto(marca), "X")
            checar(u"  isca 2.1: %s cala %s: reprova" % (doc, marca[:48]),
                   bool(_divergencias_da_21(f, d)))
    for doc, marca in _FRASES_REVOGADAS_NA_21:
        d = dict(docs, **{doc: docs[doc] + " " + marca})
        checar(u"  isca 2.1: volta a promessa revogada %s: reprova" % marca,
               bool(_divergencias_da_21(f, d)))
    rgb = {"Heart_ai": [0, 128, 255]}
    checar(u"RGB exato so vale em proprios; padrao conserva e ignora a escolha",
           CFG.cor_propria("Heart_ai", cfg={"modo": "proprios", "cores": rgb}) == (0, 128, 255)
           and CFG.cor_propria("Heart_ai", cfg={"modo": "padrao", "cores": rgb}) is None
           and rgb == {"Heart_ai": [0, 128, 255]})
    for valor in ([256, 0, 0], [-1, 0, 0], [1.0, 2, 3], [True, 2, 3], [1, 2]):
        checar(u"  isca 2.1: RGB invalido %r nao vale" % (valor,),
               CFG.cor_propria("Heart_ai", cfg={"modo": "proprios", "cores": {"Heart_ai": valor}}) is None)
    janela = src["radai_janela"]
    checar(u"  isca 2.1: F11 automatico fora do pedido explicito reprova",
           not _f11_por_ato_explicito(janela.replace("if alternar:", "if True:")))
    for nome, chave, antes, depois in (
            ("MOOSE conserva os modelos de comparacao", "radai_moose", "clin_ct_cardiac", "clin_ct_outro"),
            ("TMJ nao volta a 1 mm", "radai_constructs", "ATM_ALEM_DO_CONDILO_MM = 3.0", "ATM_ALEM_DO_CONDILO_MM = 1.0"),
            ("composto nao promete rotulo pulmonar sem produtor", "engine", "'great_arteries': ['aorta'", "'great_arteries': ['pulmonary_trunk', 'aorta'"),
            ("cartao nao nasce autorizado", "radai_queue_state", '"iniciar_pedido": False', '"iniciar_pedido": True')):
        alteradas = dict(src, **{chave: src[chave].replace(antes, depois)})
        checar(u"  isca 2.1 no codigo: %s: reprova" % nome,
               alteradas != src and not all(_fatos_da_21(alteradas).values()))
    links = [("termos", CS.TERMOS), ("politica", CS.POLITICA)]
    div_links = _contato_divergente(links,
        "https://github.com/drhenriquebraga/local-suite/releases", "2.1")
    checar(u"os links atuais usam o repositorio sucessor; a excecao antiga so vale na 2.0",
           not div_links, u" | ".join(div_links))
    velhos = [(k, v.replace(_DONO_RENOMEADO["depois"], _DONO_RENOMEADO["antes"]))
              for k, v in links]
    checar(u"  isca 2.1: links do dono antigo reprovam a nova versao",
           bool(_contato_divergente(velhos,
                "https://github.com/drhenriquebraga/local-suite/releases", "2.1")))


_HASHES_DAS_TABELAS_ATE_21 = {
    "IMPRESSOES_PUBLICADAS": "cb56d48a93a987bad90e9b5e8876e9a7d7adacc592170bee98ef39b675a5116a",
    "RESSELAGENS_ANTES_DA_PUBLICACAO": "453f0902cb5d33ca9eeddbd8eebd73b2ded2651ccf331532be78f6c89bc3e341",
    "IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO": "433d09c5a5310ffbe5df3c7ba925f56107bd2bc3593260cb5b851d09d21e8763",
}


def _hash_da_tabela_ate_21(tabela):
    import hashlib
    historico = {v: d for v, d in tabela.items()
                 if tuple(int(x) for x in v.split(".")) <= (2, 1)}
    return hashlib.sha256(json.dumps(historico, ensure_ascii=False,
                                     sort_keys=True).encode("utf-8")).hexdigest()


_MARCAS_DA_22 = {
    "fast_enxuto": (u"Não constrói pele nem parede torácica",
                    u"as costelas individuais e unidas",
                    u"cartilagem costal ( Cartilage_Costal_ai )"),
    "fast_cranio": (u"Na TC com crânio ou cabeça e pescoço identificados",
                    u"olhos, cristalinos e nervos ópticos bilaterais, tronco encefálico e quiasma"),
    "insumos_osseos": (u"Os insumos ósseos compartilhados, incluindo costelas e cartilagem costal, permanecem internamente até o acabamento do coração de radioterapia",
                     u"retirar essas ROIs não elimina a inferência desse bloco"),
    "tmj_semcaudal": (u"com margem total de 3 mm no plano axial e para cranial, sem expansão caudal",
                      u"o limite inferior fica antes do primeiro corte caudal com contorno único por hemimandíbula e é reaplicado após o acabamento"),
    "lnl": (u"A união não desconta mais os esternocleidomastoideos nem os platismas bilaterais",
            u"A regra própria das parótidas do VIII menos o esternocleidomastoideo continua"),
    "cauda": (u"incluindo o próprio corte de L2",
              u"como CaudaEquina_ai , no completo, no entregue e no FAST",
              u"Sem L2 válida na mesma grade, a medula permanece inteira"),
    "atualizador_confirmado": (u"abre uma console com cinco etapas",
                              u"Só anuncia «ATUALIZADO» depois de confirmar o painel da versão esperada em um processo novo e numa janela própria visível",
                              u"Uma cópia incompleta não é reaberta automaticamente"),
    "great_residuo": (u"o composto atual recebe a união com Heart_Model_ai menos o Heart_ai final",
                      u"somente com as duas máscaras válidas na mesma grade, sem mudar o coração",
                      u"Sem uma das duas máscaras, o composto anterior é preservado",
                      u"Essa diferença é uma operação geométrica, não uma identificação exclusiva dessas artérias nem a execução de outro modelo"),
    "medida_historica": (u"Essa medição usou a seleção anterior do FAST e não comprova equivalência da seleção atual",),
}


_MARCAS_POLITICA_DA_22 = {
    "atualizador_confirmado": (u"uma janela de console mostra cinco etapas",
                              u"O atualizador só anuncia «ATUALIZADO» depois de confirmar a versão esperada num processo novo e numa janela própria visível",
                              u"se a cópia ficou incompleta, não reabre o código parcial",
                              u"oferece «R» para reabrir o programa"),
}


def _fatos_da_22(src=None):
    src = _fontes_da_21() if src is None else src
    eng, cons = src["engine"], src["radai_constructs"]
    modes = _valores_do_modulo(ler(u"app/radai_modes.py"))
    sets = _valores_do_modulo(ler(u"app/radai_sets.py"))
    v = _valores_do_modulo(eng)
    alvo = set(sets.get("FORA_DO_OAR_FAST") or ())
    exigidos = {"bag_bowel_oar", "anus", "Skin", "ChestWall_L", "ChestWall_R",
                "ribs_left", "ribs_right", "costal_cartilages"}
    cranio = modes.get("TASKS_DO_FAST") or {}
    motores = modes.get("MOTORES_DO_FAST_POR_REGIAO") or {}
    terminal = _fonte_da_funcao(eng, "acabamentos_terminais")
    partir = _fonte_da_funcao(eng, "partir_medula_em_l2")
    upd = ler(u"packager/UPDATE.ps1")
    jan = src["radai_janela"]
    pronto = _fonte_da_funcao(jan, "pronta_para_atualizacao")
    return {
        "atualizador_confirmado": (
            all("%d/5" % n in upd for n in range(1, 6))
            and 'if (-not (AguardarPainelNovo ' in upd
            and upd.index('if (-not (AguardarPainelNovo ') < upd.index('Diga ("  ATUALIZADO.')
            and '[int]$d.pid -eq [int]$antigo' in upd
            and '$d.aqui' in upd and '$d.janela_pronta -eq $true' in upd
            and 'pf.visivel(h) and not pf.minimizada(h)' in pronto
            and 'get("versao") == VERSAO_DA_TELA' in pronto
            and 'if ($script:CodigoEmTroca -and -not $script:CodigoCompleto)' in upd
            and 'if (-not $script:CodigoEmTroca -or $script:CodigoCompleto)' in upd
            and 'CreateFile("CONIN$"' in upd and 'CreateFile("CONOUT$"' in upd),
        "fast_enxuto": alvo == exigidos,
        "fast_cranio": all("head_glands_cavities" in cranio.get(k, ())
                            and motores.get(k) == ("cranio_ct",)
                            for k in ("cranio", "cabeca_pescoco")),
        "insumos_osseos": (u'fora.add("costal_cartilages")' in _fonte_da_funcao(eng, "insumos_dos_terminais")
                           and u"insumos_dos_terminais" in _fonte_da_funcao(eng, "_filtrar_para")
                           and u"sem_cartilagem_costal" in _fonte_da_funcao(eng, "_acabamento_do_coracao")
                           and all(c in _fonte_da_funcao(eng, "_suporte_esqueletico_do_heart_fast")
                                   for c in ('"ribs_left"', '"ribs_right"'))
                           and u"_suporte_esqueletico_do_heart_fast" in _fonte_da_funcao(eng, "build_rtstruct")),
        "tmj_semcaudal": (_referencias_no_fonte(_fonte_da_funcao(cons, "atms"), "_expandir_atm_sem_caudal")
                          and bool(_fonte_da_funcao(cons, "limitar_atm_caudal"))
                          and u"limitar_atm_caudal" in terminal),
        "lnl": _fatos_da_21(src)["lnl"],
        "cauda": (v.get("CHAVE_CAUDA_EQUINA") == "cauda_equina"
                  and u"cauda = m & caudal.reshape(forma)" in partir
                  and u"cord = m & ~caudal.reshape(forma)" in partir
                  and u"partir_medula_em_l2" in terminal
                  and "cauda_equina" in set(sets.get("PERMITIDOS_NO_OAR") or ())),
        "great_residuo": (u'if modelo is not None and modelo.any() and cor is not None and cor.any():' in terminal
                          and u'masks["great_arteries"] = antes | (modelo & ~cor)' in terminal
                          and u'residuo cardiaco nao acrescentado' in terminal
                          and _fatos_da_21(src)["moose_opcional"]),
        "medida_historica": bool(v.get("MEDIDA_DO_FAST_CONTRA_O_AUTO")),
    }


def _divergencias_da_22(fatos, termos, politica):
    texto = _compacto(_plano(termos))
    priv = _compacto(_plano(politica))
    fora = []
    for chave, marcas in sorted(_MARCAS_POLITICA_DA_22.items()):
        for marca in marcas:
            if bool(fatos.get(chave)) is not (_compacto(marca).lower() in priv.lower()):
                fora.append(u"politica: %s diverge de «%s»" % (chave, marca))
    for chave, marcas in sorted(_MARCAS_DA_22.items()):
        for marca in marcas:
            if bool(fatos.get(chave)) is not (_compacto(marca).lower() in texto.lower()):
                fora.append(u"%s diverge de «%s»" % (chave, marca))
    for velha in (u"com margem total de 3 mm em 3D além do côndilo",
                  u"a união perde as intersecções com os esternocleidomastoideos",
                  u"essas estruturas não são acrescentadas ao composto"):
        if _compacto(velha).lower() in texto.lower():
            fora.append(u"promessa revogada: %s" % velha)
    return fora


def teste_o_que_a_v89_muda_na_22():
    secao(u"documentos 2.2: regras da 8.9 e tabelas publicadas ate 2.1 intactas")
    import radai_consent as CS
    checar(u"versao 2.2 pede novo aceite com data 28/10/2026",
           CS.VERSAO_DOCS == "2.2" and CS.DATA_DOCS == "2026-10-28")
    for nome, esperado in sorted(_HASHES_DAS_TABELAS_ATE_21.items()):
        tabela = getattr(CS, nome)
        checar(u"%s: todas as entradas publicadas ate 2.1 permanecem intactas" % nome,
               _hash_da_tabela_ate_21(tabela) == esperado)
        isca = dict(tabela, **{"2.1": "alterada"})
        checar(u"  isca: alterar qualquer dado da 2.1 em %s reprova" % nome,
               _hash_da_tabela_ate_21(isca) != esperado)
    f = _fatos_da_22()
    checar(u"fatos 8.9 lidos dos pontos de processamento e cadastro", all(f.values()), repr(f))
    div = _divergencias_da_22(f, CS.TERMOS, CS.POLITICA)
    checar(u"Termos 2.2 dizem o comportamento 8.9", not div, u" | ".join(div))
    for chave in sorted(f):
        checar(u"  isca: codigo sem %s diverge do documento" % chave,
               bool(_divergencias_da_22(dict(f, **{chave: False}), CS.TERMOS, CS.POLITICA)))
    for chave, marcas in sorted(_MARCAS_DA_22.items()):
        for marca in marcas:
            sem = _compacto(_plano(CS.TERMOS)).lower().replace(_compacto(marca).lower(), "X")
            checar(u"  isca: documento cala %s: reprova" % marca[:65],
                   bool(_divergencias_da_22(f, sem, CS.POLITICA)))
    for chave, marcas in sorted(_MARCAS_POLITICA_DA_22.items()):
        for marca in marcas:
            sem = _compacto(_plano(CS.POLITICA)).lower().replace(_compacto(marca).lower(), "X")
            checar(u"  isca: politica cala %s: reprova" % marca[:65],
                   bool(_divergencias_da_22(f, CS.TERMOS, sem)))
    for velha in (u"com margem total de 3 mm em 3D além do côndilo",
                  u"a união perde as intersecções com os esternocleidomastoideos",
                  u"essas estruturas não são acrescentadas ao composto"):
        checar(u"  isca: volta regra revogada: reprova",
               bool(_divergencias_da_22(f, CS.TERMOS + velha, CS.POLITICA)))


def main():
    print(u"=" * 68)
    print(u"test_consent | o portao, os documentos e a trava do modelo")
    print(u"=" * 68)
    teste_falha_fechado()
    teste_documento_honesto()
    teste_pontos_e_versao()
    teste_privacidade_descreve_o_log_que_existe()
    teste_trava_do_modelo()
    teste_registro()
    teste_texto_do_portao()
    teste_o_aceite_fala_o_idioma_da_tela()
    teste_o_aceite_tem_o_seletor_com_bandeira()
    teste_documentos_nao_dizem_o_que_saiu()
    teste_impressao_publicada()
    teste_conexoes_da_politica()
    teste_o_que_os_documentos_afirmam()
    teste_as_saidas_e_o_descarte()
    teste_o_que_a_pasta_de_trabalho_guarda()
    teste_o_onboarding_saiu_e_so_o_aceite_grava()
    teste_a_impressao_e_calculada_uma_vez()
    teste_a_guarda_de_rede_e_o_que_os_documentos_dizem()
    teste_o_readme_diz_o_que_o_preparador_confere()
    teste_o_aceite_diz_quando_o_texto_mudou()
    teste_o_que_a_v82_mudou_nos_documentos()
    teste_o_que_a_v83_mudou_nos_documentos()
    teste_os_consertos_da_revisao_da_16()
    teste_o_heart_ai_diz_quando_sai_sem_pericardio()
    teste_o_que_a_onda_4b_mudou_na_16()
    teste_o_que_a_v84_mudou_na_17()
    teste_o_que_a_v84_fecha_na_17()
    teste_o_que_a_v85_muda_na_18()
    teste_o_retorno_de_campo_na_18()
    teste_o_que_a_v86_muda_na_19()
    teste_o_que_a_v87_muda_na_20()
    teste_o_que_a_resselagem_muda_na_20()
    teste_o_que_a_segunda_resselagem_muda_na_20()
    teste_o_que_o_retorno_de_campo_muda_na_21()
    teste_o_que_a_v89_muda_na_22()
    teste_os_registros_citam_a_impressao_publicada()
    print(u"\n" + u"=" * 68)
    if _falhou:
        print(u"FALHOU: %d de %d checagens" % (_falhou, _ok + _falhou))
        for f in _falhas:
            print(u"  - %s" % f)
    else:
        print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 68)
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
