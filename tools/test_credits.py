# -*- coding: utf-8 -*-
import io
import os
import re
import sys

import _componentes
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

_RESULTADOS = []
VERBOSO = "-v" in sys.argv


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    if VERBOSO or not ok:
        print("  %-6s %s%s" % ("OK" if ok else "FALHA", nome,
                               ("  [%s]" % detalhe) if detalhe else ""))


def secao(t):
    if VERBOSO:
        print("\n-- %s %s" % (t, "-" * max(0, 58 - len(t))))


def ler(rel):
    p = _componentes.fonte(rel)
    return io.open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""


def teste_licenca_existe_e_e_a_certa():
    secao("licenca: LICENSE e NOTICE na raiz")
    lic = ler("LICENSE")
    checar("LICENSE existe", bool(lic))
    checar("e e o texto da Apache-2.0",
           "Apache License" in lic and "Version 2.0" in lic)
    checar("com o corpo inteiro, nao so o cabecalho", len(lic) > 10000, str(len(lic)))
    checar("NOTICE existe", bool(ler("NOTICE")))


def teste_notice_credita_cada_componente():
    secao("NOTICE: cada componente com autoria, licenca, versao e declaracao")
    n = ler("NOTICE")
    checar("credita o TotalSegmentator", "TotalSegmentator" in n)
    checar("com a autoria", "Wasserthal" in n)
    checar("com a licenca", "Apache License 2.0" in n)
    import re as _re
    _req = ler(os.path.join("build", "requirements-demo.txt"))
    _m = _re.search(r"^TotalSegmentator==([0-9.]+)", _req, _re.M)
    checar("o requirements pina o TotalSegmentator", _m is not None)
    checar("com a versao em uso", bool(_m) and _m.group(1) in n,
           "o NOTICE nao cita %r" % (_m.group(1) if _m else "?"))
    checar("e com a declaracao do proprio autor",
           "nao e dispositivo medico" in n.lower() or
           "não é dispositivo médico" in n.lower())
    checar("pede a citacao que os autores pedem", "Radiology" in n)

    checar("credita o nnU-Net, que os autores pedem junto", "nnU-Net" in n)
    checar("com a autoria", "Isensee" in n)

    checar("credita o segundo motor", "NV-Segment-CT" in n)
    checar("com a licenca que de fato vale",
           "NVIDIA Open Model License" in n)
    checar("e que o autor o declara para pesquisa", "pesquisa" in n.lower())
    checar("e que ele NAO e para uso clinico",
           "nao para uso clinico" in n.lower()
           or "não para uso clínico" in n.lower(), n[:0])
    sys.path.insert(0, APP)
    import radai_models as _RM
    restritos = sorted(k for k, m in _RM.MODELOS.items()
                       if (m.get("uso_permitido") or "") == "nao_comercial")
    plano = " ".join(n.split())
    if not restritos:
        checar("sem restrito no registro, o NOTICE diz que nenhum e nao "
               "comercial",
               "Nenhum componente deste pacote e de uso nao comercial"
               in plano)
    else:
        for k in restritos:
            marca = _dobrar(str(_RM.MODELOS[k].get("nome") or k).split()[0])
            checar("o NOTICE nomeia o restrito `%s` como NAO COMERCIAL" % k,
                   marca in _dobrar(plano) and "NAO COMERCIAL" in plano.upper())
    checar("e nao chama componente nenhum de «unico de uso restrito»",
           "UNICO COMPONENTE DE USO RESTRITO" not in plano.upper())

    for chave, m in sorted(_RM.MODELOS.items()):
        repo = str(m.get("repo") or "")
        if repo:
            checar("o NOTICE credita `%s` pela origem (%s)" % (chave, repo),
                   ("/" + repo) in plano, chave)
            continue
        marca = str(m.get("nome") or chave).split("(")[0].split(u"—")[0]
        marca = marca.strip().split()[0].strip(",;:")
        checar("o NOTICE credita `%s`" % marca,
               _dobrar(marca) in _dobrar(plano), chave)

    checar("o NOTICE cita os niveis cervicais como Weissmann et al.",
           "Weissmann T." in n and "10.3389/fonc.2023.1115258" in n)
    checar("e nao cita o artigo que nao existe",
           "Radiotherapy and Oncology" not in n and "Grigo" not in n)
    _putz = re.search(r"(?i)\bputz\s*(?:f\.?\s*)?et\s+al", plano)
    checar("e nao atribui a autoria a «Putz et al.»", _putz is None,
           _putz.group(0) if _putz else "")
    checar("e nao diz que os autores pedem a citacao (o repositorio nao pede)",
           "Os autores pedem a citacao do artigo" not in plano)

    checar("separa os dois regimes do mesmo codigo",
           "CODIGO PUBLICADO" in n.upper() and "BUILD INTERNO" in n.upper())
    checar("e cita a norma do build interno", "657/2022" in n)
    checar("a fronteira clinica esta escrita", "UNAPPROVED" in n)


_URL_DA_LICENCA = (
    (r"NVIDIA Open Model License", u"https://huggingface.co/%s/blob/main/LICENSE"),
    (r"CC BY-SA 4\.0", u"https://creativecommons.org/licenses/by-sa/4.0/"),
    (r"CC BY 4\.0", u"https://creativecommons.org/licenses/by/4.0/"),
    (r"CC0", u"https://creativecommons.org/publicdomain/zero/1.0/"),
    (r"Apache", u"https://www.apache.org/licenses/LICENSE-2.0"),
    (r"\bMIT\b", u"https://spdx.org/licenses/MIT.html"),
)
_SECAO_DO_MODELO = {
    "totalsegmentator": u"TotalSegmentator",
    "nv_segment_ct": u"NV-Segment-CT (NVIDIA)",
    "cads_open": u"CADS (variante `open`)",
    "moose": u"MOOSE (ENHANCE.PET)",
    "hnlnl": u"Niveis linfonodais de cabeca e pescoco",
    "cranio_buti": u"CT Brain Segmentation Radiotherapy (estruturas do encefalo em TC)",
}


def _secoes_do_notice(texto):
    linhas = (texto or u"").splitlines()
    fora, atual, corpo = {}, None, []
    i = 0
    while i < len(linhas):
        if (i + 2 < len(linhas) and set(linhas[i].strip()) == {u"-"}
                and set(linhas[i + 2].strip()) == {u"-"}
                and linhas[i + 1].strip()):
            if atual is not None:
                fora[atual] = u"\n".join(corpo)
            atual, corpo = linhas[i + 1].strip(), []
            i += 3
            continue
        if set(linhas[i].strip()) == {u"="} and atual is not None:
            fora[atual] = u"\n".join(corpo)
            atual, corpo = None, []
        elif atual is not None:
            corpo.append(linhas[i])
        i += 1
    if atual is not None:
        fora[atual] = u"\n".join(corpo)
    return fora


def _bloco_licenca(corpo):
    m = re.search(r"(?ms)^  Licenca .*?(?=^  [A-Z][a-z]+ {2,}|\Z)", corpo or u"")
    return m.group(0) if m else u""


def _enderecos_que_faltam(texto_notice, modelos):
    secoes = _secoes_do_notice(texto_notice)
    faltam = []
    for chave, m in sorted(modelos.items()):
        titulo = _SECAO_DO_MODELO.get(chave)
        if not titulo:
            faltam.append((chave, u"sem secao declarada na bateria"))
            continue
        bloco = _bloco_licenca(secoes.get(titulo, u""))
        if not bloco:
            faltam.append((chave, u"secao %r sem linha Licenca" % titulo))
            continue
        lic = str(m.get("licenca") or "")
        achou = False
        for padrao, url in _URL_DA_LICENCA:
            if not re.search(padrao, lic):
                continue
            achou = True
            if "%s" in url:
                url = url % str(m.get("repo") or "?")
            if url not in bloco:
                faltam.append((chave, url))
        if not achou:
            faltam.append((chave, u"licenca sem endereco conhecido: %r"
                           % lic[:60]))
    return faltam


def teste_notice_da_o_endereco_de_cada_licenca():
    secao("NOTICE: o endereco da licenca de cada modelo do registro")
    import radai_models as _RM
    n = ler("NOTICE")
    faltam = _enderecos_que_faltam(n, _RM.MODELOS)
    checar("cada modelo do registro tem o endereco de cada licenca na secao "
           "dele (%d modelos)" % len(_RM.MODELOS), not faltam,
           "; ".join("%s: %s" % f for f in faltam)[:300])
    for chave in sorted(_RM.MODELOS):
        checar("  `%s` tem secao no NOTICE" % chave,
               _SECAO_DO_MODELO.get(chave) in _secoes_do_notice(n))
    apoio = _secoes_do_notice(n).get(u"Bibliotecas de apoio", u"")
    for nome, url in ((u"BSD-3-Clause", u"spdx.org/licenses/BSD-3-Clause"),
                      (u"MIT", u"spdx.org/licenses/MIT"),
                      (u"PSF", u"docs.python.org/3.10/license"),
                      (u"Apache-2.0", u"www.apache.org/licenses/LICENSE-2.0"),
                      (u"Matplotlib License",
                       u"matplotlib.org/stable/project/license")):
        checar("as bibliotecas de apoio: a licenca %s tem endereco" % nome,
               nome in apoio and url in apoio)
    checar("e o NOTICE diz que o endereco esta nele (a frase que os Termos "
           "e o README repetem)",
           "O nome e o endereco da licenca de cada componente estao aqui"
           in " ".join(n.split()))

    sem_cc = n.replace(u"https://creativecommons.org/licenses/by/4.0/", u"")
    f = _enderecos_que_faltam(sem_cc, _RM.MODELOS)
    cc_by = sorted(k for k, m in _RM.MODELOS.items()
                   if re.search(r"CC BY 4\.0", str(m.get("licenca") or "")))
    checar("  isca: tirar o endereco da CC BY 4.0 acusa o MOOSE (e todo "
           "modelo CC BY 4.0)",
           "moose" in cc_by and [c for c, _ in f] == cc_by, str(f))
    novo = dict(_RM.MODELOS)
    novo["modelo_novo"] = {"licenca": u"MIT", "repo": "x/y"}
    f = _enderecos_que_faltam(n, novo)
    checar("  isca: modelo novo sem secao reprova",
           ("modelo_novo", u"sem secao declarada na bateria") in f, str(f))
    novo = {"moose": dict(_RM.MODELOS["moose"], licenca=u"GPL-3.0")}
    f = _enderecos_que_faltam(n, novo)
    checar("  isca: licenca que a bateria nao sabe enderecar reprova",
           bool(f) and u"sem endereco conhecido" in f[0][1], str(f))
    trocado = n.replace(u"https://huggingface.co/nvidia/NV-Segment-CT/blob/"
                        u"main/LICENSE", u"https://huggingface.co/nvidia/"
                        u"NV-Segment-CT")
    f = _enderecos_que_faltam(trocado, _RM.MODELOS)
    checar("  isca: a Origem do NV no lugar do endereco da licenca reprova",
           [c for c, _ in f] == ["nv_segment_ct"], str(f))


def teste_notice_nao_reivindica_autoria():
    secao("NOTICE: diz o que e nosso, e o que nao e")
    n = ler("NOTICE").lower()
    checar("afirma que nao somos autores dos modelos",
           "nao somos autores" in n or "não somos autores" in n)
    checar("e nomeia o que construimos", "acessibilidade" in n)
    for proibido in ("nosso algoritmo", "nossa ia", "desenvolvemos o modelo",
                     "nosso modelo de segmentacao"):
        checar("nao diz %r" % proibido, proibido not in n)


def teste_tela_le_o_notice_em_vez_de_copiar():
    secao("tela: o conteudo vem do arquivo, nao de uma copia")
    import radai_credits as C
    fonte = io.open(_componentes.fonte("app/radai_credits.py"), encoding="utf-8").read()
    checar("a tela le o NOTICE", "def ler_notice" in fonte)
    checar("e nao carrega uma segunda lista de componentes",
           "Wasserthal" not in fonte and "Isensee" not in fonte)

    p = C.pagina()
    checar("a pagina traz o TotalSegmentator", "TotalSegmentator" in p)
    checar("e a declaracao do autor", "dispositivo" in p.lower())
    checar("e a declaracao de apoio", "Não validada para uso clínico" in p)
    checar("o NOTICE vai escapado, nao cru",
           "&lt;" in p or "<" not in C.ler_notice())


def teste_tela_grita_se_o_notice_sumir():
    secao("tela: NOTICE ausente e denunciado, nao escondido")
    import radai_credits as C
    orig = C.ler_notice
    C.ler_notice = lambda: ""
    try:
        p = C.pagina()
        checar("diz que o arquivo faltou", "NOTICE" in p and "não foi encontrado" in p)
        checar("explica que e condicao da licenca", "condição da Apache-2.0" in p)
        checar("e diz o que fazer", "Avise" in p)
    finally:
        C.ler_notice = orig


def teste_a_tela_e_alcancavel_pela_interface():
    secao("tela: alcancavel por link, nao so por URL decorada")
    import radai_credits as C
    checar("a rota e /creditos", C.ROTA == "/creditos", C.ROTA)


def teste_os_empacotadores_levam_a_atribuicao():
    secao("empacotadores: LICENSE e NOTICE vao no pacote, ou nao ha pacote")
    if not os.path.isdir(os.path.join(RAIZ, "build")):
        if VERBOSO:
            print("  --     nao se aplica: arvore sem build/ (deploy)")
        return
    b = ler("build/configurar_ambiente.py")
    checar("o bundle copia os dois", '"LICENSE", "NOTICE"' in b)
    checar("e ABORTA se faltarem", "PAREI: falta o %s" in b)
    checar("dizendo que e da Apache-2.0", "Apache-2.0 exige" in b)

    p = ler("build/empacotar_instalador.py")
    checar("o instalador leve leva o LICENSE e o NOTICE",
           '"LICENSE", "NOTICE"' in p)
    checar("e a lista deles e obrigatoria, nao opcional",
           "ARQUIVOS" in p)
    import zipfile
    import glob
    _ent = ler("entrega.txt")
    _proj = ""
    for _l in _ent.splitlines():
        if _l.strip().startswith("PROJETO="):
            _proj = _l.split("=", 1)[1].strip()
    checar("li o PROJETO do entrega.txt", bool(_proj), _proj)
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import destino_de_entrega as _DE
    try:
        _raiz_ent = str(_DE.raiz_de_entrega(_proj or None, de=RAIZ)[0])
    except SystemExit:
        _raiz_ent = ""
    if not _raiz_ent:
        import _componentes
        _componentes.pulado(u"a conferencia do instalador publicado (a raiz "
                            u"de entrega so existe na maquina de quem publica, "
                            u"ou com %s)" % _DE.VARIAVEL)
        return
    zs = sorted(glob.glob(os.path.join(
        _raiz_ent, _proj, "v*",
        "RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_*.zip"))) if _proj and _raiz_ent else []
    checar("achei o instalador publicado para conferir o artefato",
           bool(zs),
           "sem .zip em <raiz de entrega>\\%s\\v* — a conferencia do ARTEFATO "
           "nao rodou (a da lista no codigo, acima, rodou)" % _proj)
    if zs:
        nomes = set(zipfile.ZipFile(zs[-1]).namelist())
        checar("e o .zip publicado tem os dois dentro",
               "LICENSE" in nomes and "NOTICE" in nomes,
               os.path.basename(zs[-1]))
    else:
        print("  (o .zip publicado nao existe nesta maquina)")


def teste_interface_nao_atribui_autoria_a_nos():
    secao("discurso: o que aparece na tela nao reivindica o modelo")
    import radai_panel
    telas = [("home", radai_panel.pagina_inicial())]
    try:
        import radai_credits
        telas.append(("creditos", radai_credits.pagina()))
    except Exception:
        pass

    proibidas = ("nossa ia", "nosso algoritmo", "desenvolvemos o modelo",
                 "nossa rede neural", "nosso modelo de ia", "ia proprietaria")
    for nome, html in telas:
        baixa = html.lower()
        achados = [p for p in proibidas if p in baixa]
        checar("a tela %s nao reivindica autoria de modelo" % nome,
               not achados, ", ".join(achados))

    home = telas[0][1]
    checar("a home nomeia o TotalSegmentator", "TotalSegmentator" in home)


def teste_declaracao_de_apoio_esta_visivel():
    secao("discurso: a declaracao obrigatoria aparece NO APP")
    import html as _html
    import radai_modules
    import radai_panel

    def plano(t):
        return " ".join(_html.unescape(t).lower().split())

    import re as _re
    import radai_porta
    home = plano(_re.sub(r"<[^>]+>", u"", _re.sub(
        r"(?is)<(script|style)\b.*?</\1>", u"", radai_porta.pagina())))
    checar("a home traz: ferramenta de apoio", "ferramenta de apoio" in home)
    checar("a home traz: nao validada para uso clinico",
           "não validada para uso clínico" in home)
    checar("a home traz, uma vez: toda estrutura sai como sugestao nao aprovada",
           home.count("toda estrutura sai como sugestão não aprovada") == 1)
    import radai_review
    dialogo = plano(radai_review.aplicar(
        u"<html><head></head><body></body></html>"))
    aviso = plano(radai_review.montar([], tasks=("total_v3",))["aviso"])
    checar("a confirmacao do INICIAR traz: sugestao nao aprovada",
           "sugestão não aprovada" in aviso
           and "sugestão não aprovada" in dialogo, aviso[:120])
    checar("e que revisar e ato medico", "ato médico" in aviso
           and "ato médico" in dialogo)
    # GUARDA: o vigia (AUTO) não passa pelo INICIAR; o `?` do ContourLab é o lugar à vista que sobra.
    def _nao_aprova(secoes):
        t = plano(u" ".join(u" ".join(v) for v in secoes.values()))
        return "não aprova nada" in t and "unapproved" in t
    checar("o `?` do ContourLab diz: nao aprova nada, UNAPPROVED",
           _nao_aprova(radai_modules.secoes_de_ajuda("autocontorno")))
    checar("  isca: um `?` sem a nao-aprovacao reprova",
           not _nao_aprova({u"O que não faz": (u"Não manda imagem para a nuvem.",)}))
    mini = plano(radai_panel.pagina_inicial())
    checar("a mini-pagina do ContourLab diz o material de estudo, 100% local",
           "material de estudo" in mini and "100% local" in mini)

    cfg = radai_panel.PAGINA_CONFIG
    checar("e o caminho para os termos", 'href="/termos"' in cfg)
    checar("e para os creditos", 'href="/creditos"' in cfg)

    import radai_consent
    termos = " ".join(radai_consent.TERMOS.lower().split())
    for f in ("não validada para uso clínico", "rascunho sujeito a revisão médica"):
        checar("os TERMOS trazem: %r" % f[:32], f in termos)




def teste_todo_doi_declara_onde_foi_lido():
    secao(u"todo DOI diz onde foi lido")
    import json
    p = os.path.join(RAIZ, "app", "data", "bibliography.json")
    if not os.path.isfile(p):
        checar(u"achei o bibliography.json", False, p)
        return
    d = json.load(io.open(p, encoding="utf-8"))
    arts = d.get("artigos") or []
    checar(u"ha artigos para conferir", bool(arts), u"%d" % len(arts))

    sem = [a.get("id") for a in arts
           if a.get("doi") and not a.get("doi_lido_em")]
    checar(u"toda entrada com DOI diz onde ele foi lido",
           not sem, u", ".join(str(x) for x in sem) or u"%d conferida(s)"
           % len(arts))
    novas = [a for a in arts
             if a.get("categoria") or a.get("precisa_conferir") is not None]

    ruido = [a.get("id") for a in novas
             if a.get("precisa_conferir") and a.get("doi")
             and a.get("doi_lido_em") and a.get("autores")
             and a.get("revista") and a.get("ano")]
    checar(u"e `precisa_conferir` so marca o que falta mesmo",
           not ruido, u", ".join(str(x) for x in ruido) or u"nenhum ruido")


    circ = [a.get("id") for a in arts
            if _doi_lido_no_nosso_codigo(a.get("doi_lido_em"))]
    checar(u"nenhum DOI diz ter sido lido numa linha do nosso codigo",
           not circ, u", ".join(str(x) for x in circ))
    checar(u"e a checagem reconhece o caso de 22/09 (`app/radai_elastic.py:58`)",
           _doi_lido_no_nosso_codigo(u"app/radai_elastic.py:58")
           and not _doi_lido_no_nosso_codigo(
               u"no próprio PDF (p. 173), e conferido no CrossRef"))


def _doi_lido_no_nosso_codigo(texto):
    import re
    return bool(re.search(
        r"(?:^|[\s(`'\"])(?:app|tools|build|packager|installer)/[\w./-]+"
        r"\.(?:py|ps1|cmd|json):\d+", str(texto or u"")))




def _dobrar(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(t or ""))
    return u"".join(c for c in t if not unicodedata.combining(c)).lower()


def _tokens_de(a):
    toks = []
    doi = str(a.get("doi") or "").strip()
    if doi:
        toks.append(doi)
        if "arxiv." in doi.lower():
            toks.append(doi.lower().split("arxiv.", 1)[1])
    autores = str(a.get("autores") or "").strip()
    if autores and autores not in (u"—", u"-"):
        toks.append(autores.split(",")[0].split()[0])
    toks.extend(str(x) for x in (a.get("cita_como") or []))
    return [_dobrar(x) for x in toks if str(x).strip()]


def _documentacao_do_simbolo(rel, simbolo):
    p = _componentes.fonte(rel)
    if not os.path.isfile(p):
        return False, u""
    src = io.open(p, encoding="utf-8", errors="replace").read()
    return _documentacao_no_fonte(src, simbolo)


def _documentacao_no_fonte(src, simbolo):
    import ast
    try:
        arv = ast.parse(src)
    except SyntaxError:
        return False, u""
    if simbolo == "__doc__":
        doc = ast.get_docstring(arv)
        return bool(doc), doc or u""
    alvo = None
    for no in arv.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if no.name == simbolo:
                alvo = no
        elif isinstance(no, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == simbolo
                   for t in no.targets):
                alvo = no
        elif isinstance(no, ast.AnnAssign):
            if isinstance(no.target, ast.Name) and no.target.id == simbolo:
                alvo = no
    if alvo is None:
        return False, u""
    trecho = ast.get_source_segment(src, alvo) or u""
    linhas = src.splitlines()
    primeira = min([alvo.lineno] + [d.lineno for d in
                                    getattr(alvo, "decorator_list", [])])
    i = primeira - 2
    bloco = []
    while i >= 0 and linhas[i].lstrip().startswith("#"):
        bloco.append(linhas[i])
        i -= 1
    return True, u"\n".join(reversed(bloco)) + u"\n" + trecho


def _falhas_da_bibliografia(d):
    falhas = []
    if d.get("a_ler") or d.get("a_ler_nota"):
        falhas.append((u"a_ler", u"a fila de leitura voltou para a "
                       u"bibliografia — fila e o que AINDA NAO foi lido"))
    fichas = {}
    for m in d.get("modelos") or []:
        if m.get("registro"):
            fichas[str(m.get("registro"))] = m
    for a in d.get("artigos") or []:
        i = str(a.get("id") or u"?")
        if not str(a.get("lido") or u"").strip():
            falhas.append((i, u"sem `lido`: onde o texto foi lido?"))
        if not str(a.get("doi") or u"").strip() \
                or not str(a.get("titulo") or u"").strip():
            falhas.append((i, u"sem `doi` ou `titulo`: qual e a referencia?"))
        anc = a.get("influencia")
        if not isinstance(anc, list) or not anc:
            falhas.append((i, u"sem `influencia`: o que ela mudou no programa?"))
            continue
        toks = _tokens_de(a)
        for x in anc:
            x = str(x)
            if x.startswith("modelo:"):
                reg = x.split(":", 1)[1]
                m = fichas.get(reg)
                if m is None:
                    falhas.append((i, u"%s: nao ha ficha com esse registro" % x))
                elif i == str(m.get("citar") or u""):
                    pass
                elif i == str(m.get("citar_tambem") or u""):
                    if not any(k in _dobrar(m.get("nota")) for k in toks):
                        falhas.append((i, u"%s: a ficha aponta para ela em "
                                       u"`citar_tambem`, e a `nota` da ficha "
                                       u"nao a cita (procurei %s)"
                                       % (x, u", ".join(toks))))
                else:
                    falhas.append((i, u"%s: a ficha nao cita esta "
                                   u"referencia" % x))
                continue
            if "::" not in x:
                falhas.append((i, u"%s: ancora sem `::simbolo`" % x))
                continue
            rel, simbolo = x.split("::", 1)
            if simbolo == "__doc__":
                falhas.append((i, u"%s: a ancora e um simbolo do codigo, "
                               u"e nao o docstring" % x))
                continue
            achou, _texto = _documentacao_do_simbolo(rel, simbolo)
            if not achou:
                falhas.append((i, u"%s: o simbolo nao existe mais — a "
                               u"referencia mudou algo que saiu do "
                               u"programa?" % x))
    return falhas


def teste_o_kong_fica_colado_na_tabela_de_margens():
    secao(u"o Kong 2011 fica colado na tabela de margens do motor")
    import json
    p = os.path.join(RAIZ, "app", "data", "bibliography.json")
    d = json.load(io.open(p, encoding="utf-8"))
    kong = [a for a in d.get("artigos") or [] if a.get("id") == "kong2011"]
    checar(u"a referencia `kong2011` esta na bibliografia", bool(kong))
    if not kong:
        return
    checar(u"  e a ancora dela e `app/engine.py::MARGEM_OAR_MM`",
           "app/engine.py::MARGEM_OAR_MM" in (kong[0].get("influencia") or []),
           str(kong[0].get("influencia")))
    src = io.open(_componentes.fonte("app/engine.py"),
                  encoding="utf-8").read()
    achou, _texto = _documentacao_no_fonte(src, "MARGEM_OAR_MM")
    checar(u"a tabela `MARGEM_OAR_MM` existe no motor", achou)
    import engine as E
    checar(u"e a tabela obedece: o esofago nao tem margem (a adventicia ja e "
           u"a borda que o modelo ve)", "esophagus" not in E.MARGEM_OAR_MM
           and float(E.MARGEM_OAR_MM.get("trachea", 0)) == 2.0)


def teste_toda_referencia_foi_lida_e_mudou_o_programa():
    secao(u"toda referencia foi lida E mudou o programa")
    import copy
    import json
    p = os.path.join(RAIZ, "app", "data", "bibliography.json")
    if not os.path.isfile(p):
        checar(u"achei o bibliography.json", False, p)
        return
    d = json.load(io.open(p, encoding="utf-8"))
    arts = d.get("artigos") or []
    checar(u"ha artigos para conferir", bool(arts), u"%d" % len(arts))

    falhas = _falhas_da_bibliografia(d)
    por_id = {}
    for i, motivo in falhas:
        por_id.setdefault(i, []).append(motivo)
    checar(u"a fila de leitura nao mora mais aqui",
           u"a_ler" not in por_id, u"; ".join(por_id.get(u"a_ler", [])))
    for a in arts:
        i = str(a.get("id"))
        checar(u"`%s` foi lida e o que ela mudou ainda existe" % i,
               i not in por_id, u"; ".join(por_id.get(i, [])))

    alvo = next((a for a in arts
                 if any("::" in str(x) for x in (a.get("influencia") or []))),
                None)
    checar(u"ha um artigo com ancora em codigo para forjar", alvo is not None)
    if alvo is None:
        return

    def forjar(mexer):
        dd = copy.deepcopy(d)
        for a in dd["artigos"]:
            if a.get("id") == alvo.get("id"):
                mexer(a)
        return [f for f in _falhas_da_bibliografia(dd)
                if f[0] == str(alvo.get("id"))]

    f1 = forjar(lambda a: a.__setitem__(
        "influencia", ["app/engine.py::entregar_torax"]))
    checar(u"reprova ancora num simbolo que saiu do codigo", bool(f1),
           f1[0][1] if f1 else
           u"aceitou engine.entregar_torax, que nao existe desde 06/09")
    f2 = forjar(lambda a: a.__setitem__(
        "influencia", ["app/engine.py::__doc__"]))
    checar(u"reprova ancora no docstring (o vinculo mora no simbolo)",
           bool(f2), f2[0][1] if f2 else u"aceitou `engine.__doc__`")
    f2b = forjar(lambda a: a.__setitem__("doi", u""))
    checar(u"reprova entrada sem `doi` (a referencia some do dado)",
           bool(f2b), f2b[0][1] if f2b else u"aceitou entrada sem `doi`")
    f3 = forjar(lambda a: a.pop("lido", None))
    checar(u"reprova entrada sem `lido`", bool(f3),
           f3[0][1] if f3 else u"aceitou entrada sem `lido`")
    dd = copy.deepcopy(d)
    dd["a_ler"] = [{"titulo": u"qualquer", "doi": u"10.0000/x"}]
    checar(u"reprova a fila de leitura de volta",
           any(f[0] == u"a_ler" for f in _falhas_da_bibliografia(dd)))

    fichas = [m for m in (d.get("modelos") or []) if m.get("registro")]
    checar(u"ha uma ficha com registro para forjar", bool(fichas))
    if not fichas:
        return
    reg = str(fichas[0].get("registro"))

    def forjar_ficha(nota):
        dd = copy.deepcopy(d)
        for a in dd["artigos"]:
            if a.get("id") == alvo.get("id"):
                a["influencia"] = [u"modelo:%s" % reg]
        for m in dd["modelos"]:
            if str(m.get("registro")) == reg:
                m["citar"] = u""
                m["citar_tambem"] = alvo.get("id")
                m["nota"] = nota
        return [f for f in _falhas_da_bibliografia(dd)
                if f[0] == str(alvo.get("id"))]
    f5 = forjar_ficha(u"Uma nota que nao diz de onde veio a limitacao.")
    checar(u"reprova `citar_tambem` sem a frase na nota da ficha", bool(f5),
           f5[0][1] if f5 else
           u"aceitou o ponteiro sozinho como influencia de %s"
           % alvo.get("id"))
    f6 = forjar_ficha(u"A limitacao vem de doi:%s." % alvo.get("doi"))
    checar(u"e aceita quando a nota da ficha cita a referencia", not f6,
           f6[0][1] if f6 else u"")


def teste_a_tela_da_bibliografia_sai_do_dado():
    secao(u"a tela da bibliografia sai do dado")
    sys.path.insert(0, APP)
    try:
        import radai_bibliography as B
    finally:
        sys.path.pop(0)
    d = B._dados()
    html = B._pagina()
    arts = list(d.get("artigos") or [])
    faltam = [a.get("id") for a in arts
              if a.get("doi") and ("doi:%s" % a.get("doi")) not in html]
    checar(u"todo artigo do dado aparece na tela", not faltam, str(faltam))
    checar(u"a secao da fila de leitura saiu", u"Fila de leitura" not in html)

    orig = B._dados
    B._dados = lambda: {"artigos": [
        {"id": "x1", "titulo": "X1", "peso": "fundamental", "doi": "10.1/a"},
        {"id": "x2", "titulo": "X2", "peso": "contexto", "doi": "10.1/b"},
        {"id": "x3", "titulo": "X3", "peso": "fundamental", "doi": "10.1/c",
         "categoria": "diretriz"}],
        "modelos": []}
    try:
        h2 = B._pagina()
    finally:
        B._dados = orig
    checar(u"a contagem de referencias sai do dado e inclui a diretriz "
           u"(3 com 2 artigos e 1 diretriz)",
           u"<b>3</b>referências" in h2 and u"<b>2</b>fundamentais" in h2,
           h2[h2.find(u'class="bi-conta"'):h2.find(u'class="bi-conta"') + 200])
    checar(u"e a tela real conta o dado inteiro (%d)" % len(arts),
           u"<b>%d</b>referências" % len(arts) in html)

def _o_que_a_bibliografia_erra_nos_niveis(mudou, ordem, gravada):
    erros = []
    tupla = u"(" + u", ".join(ordem) + u")"
    if ordem and tupla not in mudou:
        erros.append(u"nao cita a ordem do codigo %s" % tupla)
    if gravada and u"ainda não é gravada" in mudou:
        erros.append(u"diz que a descricao neutra nao e gravada, e ela e")
    if not gravada and u"cada ROI leva" in mudou:
        erros.append(u"diz que cada ROI leva a descricao, e ninguem a grava")
    return erros


def teste_a_bibliografia_diz_o_que_o_codigo_faz_nos_niveis():
    secao("bibliografia: a gregoire2014 diz a ordem e a costura que o codigo tem")
    import json as _json
    bib = _json.loads(ler(os.path.join("app", "data", "bibliography.json")))
    greg = [a for a in bib.get("artigos") or [] if a.get("id") == "gregoire2014"]
    checar("a gregoire2014 esta na bibliografia", bool(greg))
    mudou = str((greg[0] if greg else {}).get("mudou") or "")
    m = re.search(r"(?m)^ORDEM_BILATERAL = \(([^)]*)\)", ler("app/radai_hnlnl.py"))
    ordem = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    checar("li `ORDEM_BILATERAL` do radai_hnlnl", len(ordem) == 8, repr(ordem))
    gravada = any(
        "observacoes_dos_niveis(" in ler(os.path.join("app", f))
        for f in _componentes.nomes("app")
        if f.endswith(".py") and f != "radai_hnlnl.py")
    erros = _o_que_a_bibliografia_erra_nos_niveis(mudou, ordem, gravada)
    checar("o texto da tela concorda com o codigo", not erros, "; ".join(erros))
    if len(ordem) == 8:
        trocada = list(ordem)
        trocada[2], trocada[3] = trocada[3], trocada[2]
        checar("  isca: a ordem velha (Ib antes do II) e acusada",
               bool(_o_que_a_bibliografia_erra_nos_niveis(
                   mudou, trocada, gravada)))
    checar("  isca: a frase «ainda nao e gravada» e acusada com a costura viva",
           bool(_o_que_a_bibliografia_erra_nos_niveis(
               mudou + u" E essa descrição ainda não é gravada.", ordem, True)))
    checar("  isca: «cada ROI leva» e acusado sem ninguem gravar",
           bool(_o_que_a_bibliografia_erra_nos_niveis(mudou, ordem, False)))


def teste_bibliografia_concorda_com_o_registro():
    secao(u"a bibliografia concorda com o registro de modelos")
    sys.path.insert(0, APP)
    try:
        import radai_bibliography as B
        import radai_models as RM
    finally:
        sys.path.pop(0)

    d = B._dados()
    mods = list(d.get("modelos") or [])
    checar(u"a bibliografia tem modelos", len(mods) >= 4, str(len(mods)))

    ligados = [m for m in mods if m.get("registro")]
    checar(u"mais de um traz a chave `registro` (senao nada e comparado)",
           len(ligados) >= 2, str(len(ligados)))

    for m in ligados:
        chave = str(m.get("registro"))
        reg = RM.MODELOS.get(chave)
        checar(u"`%s` existe no registro de modelos" % chave, reg is not None,
               u"a bibliografia cita um modelo que o pacote nao tem")
        if reg is None:
            continue
        checar(u"  e o `uso` concorda (%s)" % chave,
               str(m.get("uso") or "") == str(reg.get("uso_permitido") or ""),
               u"bibliografia=%s registro=%s"
               % (m.get("uso"), reg.get("uso_permitido")))

    citados = {str(m.get("registro")) for m in ligados}
    for chave in sorted(RM.MODELOS):
        checar(u"o registro cita `%s`, e a bibliografia tambem" % chave,
               chave in citados,
               u"motor embarcado fora da tela de procedencia")

    nc = [m.get("nome") for m in mods if m.get("uso") == "nao_comercial"]
    reais = [k for k, v in RM.MODELOS.items()
             if str(v.get("uso_permitido")) != "livre"]
    checar(u"o numero de NAO COMERCIAIS bate com o registro (%d)" % len(reais),
           len(nc) == len(reais), u"bibliografia=%s registro=%s" % (nc, reais))
    html = B._pagina()
    checar(u"e o selo «nao comercial» so aparece se houver algum",
           (u"não comercial</span>" in html) == bool(reais),
           u"selo na tela=%s, restritos no registro=%d"
           % (u"não comercial</span>" in html, len(reais)))


_NOME_NO_NOTICE = {"torch": u"PyTorch"}


def _pinos(texto_req):
    fora = []
    for linha in (texto_req or u"").splitlines():
        linha = linha.split(u"#")[0].strip()
        m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)", linha)
        if m:
            fora.append((m.group(1), m.group(2).split(u"+")[0]))
    return fora


def _pinos_do_runtime():
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import artefatos as _A
    fora = [("Python", _A.VERSOES["python"])]
    for chave, a in sorted(_A.ARTEFATOS.items()):
        m = re.match(r"^cache/pip-([0-9][^-]*)-", chave)
        if m and a.get("componente") == "pip":
            fora.append(("pip", m.group(1)))
    return fora


def _bibliotecas_fora_do_notice(texto_notice, pinos):
    apoio = _secoes_do_notice(texto_notice).get(u"Bibliotecas de apoio", u"")
    linhas = apoio.splitlines()
    faltam = []
    for nome, versao in pinos:
        rot = _NOME_NO_NOTICE.get(nome.lower(), nome)
        padrao = re.compile(r"^\s+%s(?![\w-])" % re.escape(rot), re.I)
        achou = [i for i, l in enumerate(linhas) if padrao.match(l)]
        if not achou:
            faltam.append((nome, u"sem linha"))
            continue
        i = achou[0]
        if versao not in u" ".join(linhas[i:i + 2]):
            faltam.append((nome, u"sem a versao %s" % versao))
    return faltam


def teste_notice_cobre_cada_biblioteca_fixada():
    secao("NOTICE: cada biblioteca que o pacote fixa, com versao e licenca")
    n = ler("NOTICE")
    pinos = _pinos(ler(os.path.join("build", "requirements-demo.txt")))
    checar("li os pinos do requirements (%d)" % len(pinos), len(pinos) >= 15,
           str(pinos[:3]))
    faltam = _bibliotecas_fora_do_notice(n, pinos)
    checar("cada pino esta nas bibliotecas de apoio, com a versao fixada",
           not faltam, "; ".join("%s: %s" % f for f in faltam))
    checar("e o NOTICE diz qual e o conjunto (modelos e o que o requirements "
           "fixa)", "cada biblioteca que o pacote fixa em "
           "build/requirements-demo.txt" in " ".join(n.split()))

    runtime = _pinos_do_runtime()
    checar("li o Python e o pip de build/artefatos.py (%s)"
           % ", ".join("%s %s" % p for p in runtime),
           sorted(k for k, _v in runtime) == ["Python", "pip"], str(runtime))
    faltam = _bibliotecas_fora_do_notice(n, runtime)
    checar("o Python e o pip estao nas bibliotecas de apoio, com a versao "
           "fixada", not faltam, "; ".join("%s: %s" % f for f in faltam))
    checar("e o NOTICE diz que eles vem de build/artefatos.py",
           "mais o Python e o pip que build/artefatos.py fixa"
           in " ".join(n.split()))
    checar("  isca: tirar a linha do pip reprova",
           ("pip", u"sem linha") in _bibliotecas_fora_do_notice(
               n.replace(u"  pip 26.2.1", u"  (sem)"), runtime))

    import radai_consent as _CS
    termos = " ".join(re.sub(r"<[^>]+>", " ", _CS.TERMOS).split())
    readme = " ".join(ler("README.md").split())
    _FRASES = (
        ("os Termos",
         u"endereço da licença de cada componente estão no NOTICE",
         u"endereço da licença de cada modelo e de cada biblioteca que o "
         u"pacote fixa estão no NOTICE"),
        ("o README",
         u"the name and address of every third-party licence",
         u"of every library the package pins"))

    def _conjunto_errado(textos):
        return [nome for (nome, larga, estreita) in _FRASES
                if larga in textos[nome] or estreita not in textos[nome]]
    textos = {"os Termos": termos, "o README": readme}
    errados = _conjunto_errado(textos)
    checar("os Termos e o README dizem o conjunto que o NOTICE cobre, e nao "
           "«cada componente»", not errados, ", ".join(errados))
    checar("e os Termos dizem onde esta a licenca das transitivas",
           u"levam a licença delas no metadado do pacote instalado" in termos)
    velho = dict(textos, **{"os Termos": termos.replace(
        _FRASES[0][2], _FRASES[0][1])})
    checar("  isca: os Termos voltam a «cada componente»: reprova",
           _conjunto_errado(velho) == ["os Termos"])
    sem_monai = n.replace(u"  MONAI 1.4.0", u"  (sem)")
    checar("  isca: tirar a linha do MONAI reprova",
           ("monai", u"sem linha") in _bibliotecas_fora_do_notice(sem_monai,
                                                                  pinos))
    checar("  isca: pino novo sem linha no NOTICE reprova",
           ("pacote-novo", u"sem linha") in _bibliotecas_fora_do_notice(
               n, pinos + [("pacote-novo", "1.0")]))
    checar("  isca: versao do pino que mudou reprova",
           ("dipy", u"sem a versao 9.9.9") in _bibliotecas_fora_do_notice(
               n, [("dipy", "9.9.9")]))
    checar("  isca: `pylibjpeg` nao se acha dentro de `pylibjpeg-openjpeg`",
           ("pylibjpeg", u"sem linha") in _bibliotecas_fora_do_notice(
               n.replace(u"  pylibjpeg 2.1.0", u"  (sem)"),
               [("pylibjpeg", "2.1.0")]))


_GREGOIRE_2013 = re.compile(
    r"Gr[eé]goire(?:\s+et\s+al\.?)?\s*[,(]?\s*2013")
_GREGOIRE_CERTO = u"Grégoire et al. 2014 (a atualização de 2013)"
_GREGOIRE_PENDENTE = ("app/radai_models.py",)


def _literais_de_tela(src):
    import ast
    try:
        arv = ast.parse(src)
    except SyntaxError:
        return []
    docs = set()
    for no in ast.walk(arv):
        corpo = getattr(no, "body", None)
        if isinstance(corpo, list) and corpo:
            c = corpo[0]
            if (isinstance(c, ast.Expr) and isinstance(c.value, ast.Constant)
                    and isinstance(c.value.value, str)):
                docs.add(id(c.value))
    return [no.value for no in ast.walk(arv)
            if isinstance(no, ast.Constant) and isinstance(no.value, str)
            and id(no) not in docs]


def _citam_gregoire_2013(textos):
    return sorted(nome for nome, t in textos
                  if _GREGOIRE_2013.search(u" ".join((t or u"").split())))


def teste_gregoire_com_o_ano_da_publicacao():
    secao("citacao: o consenso de Gregoire com o ano em que saiu (2014)")
    textos = []
    for nome in _componentes.nomes("app"):
        if nome.endswith(".py"):
            rel = "app/" + nome
            textos.append((rel, u"\n".join(_literais_de_tela(ler(rel)))))
    textos.append(("build/artefatos.py", u"\n".join(
        _literais_de_tela(ler(os.path.join("build", "artefatos.py"))))))
    for rel in ("NOTICE", "README.md"):
        textos.append((rel, ler(rel)))
    achados = _citam_gregoire_2013(textos)
    novos = [a for a in achados if a not in _GREGOIRE_PENDENTE]
    checar("nenhum texto de tela cita «Grégoire (2013)»", not novos,
           ", ".join(novos))
    for p in _GREGOIRE_PENDENTE:
        checar("  pendencia declarada ainda pendente (%s) — consertou? tire "
               "da lista" % p, p in achados)
    for rel, texto in (("app/radai_credits.py", ler("app/radai_credits.py")),
                       ("app/radai_sets.py", ler("app/radai_sets.py")),
                       ("build/artefatos.py",
                        ler(os.path.join("build", "artefatos.py")))):
        plano = u" ".join(u"\n".join(_literais_de_tela(texto)).split())
        checar("%s: cita «%s»" % (rel, _GREGOIRE_CERTO), _GREGOIRE_CERTO in plano)
    for frase in (u"treinado pelo consenso de Grégoire et al. (2013)",
                  u"treinados pelo consenso de Grégoire et al.\n (2013), que",
                  u"posição publicada (Grégoire 2013, doi:...)",
                  u"Gregoire, 2013"):
        checar("  isca: acusa %r" % frase[:40],
               _citam_gregoire_2013([("x", frase)]) == ["x"])
    for frase in (_GREGOIRE_CERTO, u"Gregoire 2014", u"a 2013 update",
                  u"o «2013 update» de Grégoire 2014"):
        checar("  e nao acusa %r" % frase[:40],
               _citam_gregoire_2013([("x", frase)]) == [])


_LINHA_DE_SUFIXO = re.compile(r"(?m)^ {2}(_[A-Za-z0-9]{2,3}) {2,}\S")


def _sufixos_do_registro():
    import radai_sets as RS
    fora = []
    for c in list(RS.CONJUNTOS) + list(getattr(RS, "PLUGINS", ()) or ()):
        s = c.get("sufixo") or ""
        if s and s not in fora:
            fora.append(s)
    return fora


def _sufixos_divergentes(texto_notice, sufixos):
    no_notice = set(_LINHA_DE_SUFIXO.findall(texto_notice or u""))
    return (sorted(set(sufixos) - no_notice), sorted(no_notice - set(sufixos)))


def teste_o_notice_declara_todo_sufixo():
    secao("NOTICE: todo sufixo de procedencia do registro, e so eles")
    try:
        suf = _sufixos_do_registro()
    except Exception as e:
        checar("radai_sets importa", False, "%s: %s" % (type(e).__name__, e))
        return
    n = ler("NOTICE")
    checar("li os sufixos do registro (conjuntos e plugins: %d)" % len(suf),
           len(suf) >= 7, ", ".join(suf))
    faltam, sobram = _sufixos_divergentes(n, suf)
    checar("todo sufixo do registro tem linha no NOTICE", not faltam,
           "faltam: %s" % ", ".join(faltam))
    checar("e toda linha de sufixo do NOTICE e do registro", not sobram,
           "sobram: %s" % ", ".join(sobram))
    f2, _s2 = _sufixos_divergentes(n, suf + ["_zzz"])
    checar("  isca: plugin novo (_zzz) sem linha no NOTICE e acusado",
           f2 == ["_zzz"], str(f2))
    _f3, s3 = _sufixos_divergentes(
        n + u"\n  _v3D   VISTA-3D (saiu em 14/09/2026)\n", suf)
    checar("  isca: linha de sufixo aposentado (_v3D) no NOTICE e acusada",
           s3 == ["_v3D"], str(s3))


def _faltas_da_porta(notice, lock):
    faltas = []
    for chave, info in sorted((lock.get("packages") or {}).items()):
        if not chave.startswith("node_modules/"):
            continue
        nome = chave[len("node_modules/"):]
        if nome == "esbuild" or nome.startswith("@esbuild/"):
            continue
        if (u"%s %s" % (nome, info.get("version"))) not in notice:
            faltas.append(u"%s %s" % (nome, info.get("version")))
    for marca in (u"SIL Open Font License",
                  u"Copyright 2020 The Anton Project Authors "
                  u"(https://github.com/googlefonts/AntonFont.git)",
                  u"Copyright (c) 2024 Motion B.V.",
                  u"Copyright (c) 2018 Framer B.V.",
                  u"Copyright (c) Microsoft Corporation."):
        if marca not in notice:
            faltas.append(marca)
    return faltas


def teste_notice_cobre_os_componentes_da_porta():
    secao("NOTICE: os componentes da porta (Motion, tslib e a fonte Anton)")
    import json
    with io.open(os.path.join(RAIZ, "build", "porta", "package-lock.json"),
                 encoding="utf-8") as f:
        lock = json.load(f)
    n = ler("NOTICE")
    faltas = _faltas_da_porta(n, lock)
    checar("o NOTICE cita cada pacote embutido, com a versao do lockfile, e a OFL",
           not faltas, repr(faltas))
    checar("  e diz que o esbuild so prepara e nao viaja",
           "esbuild 0.28.2" in n and "nao viaja" in n)
    checar("  (isca) sem o motion-dom no NOTICE reprova",
           bool(_faltas_da_porta(n.replace("motion-dom 14.1.0", "motion-dom"), lock)))
    lock2 = json.loads(json.dumps(lock))
    lock2["packages"]["node_modules/motion"]["version"] = "14.2.0"
    checar("  (isca) outra versao do motion no lockfile reprova",
           bool(_faltas_da_porta(n, lock2)))


_MARCAS_DA_DEMO = ("LCTSC", "LIDC-IDRI", "RIRE", "dados de demonstra",
                   "Os dados de demonstração", "séries de demonstração",
                   "DEMO_LATEST")


def _a_demo_ainda_mora(textos):
    fora = []
    for nome, txt in textos:
        for m in _MARCAS_DA_DEMO:
            if m in (txt or ""):
                fora.append("%s cita %r" % (nome, m))
    return fora


def teste_a_demo_saiu_dos_creditos_e_do_notice():
    secao("a demo saiu: nem o NOTICE nem os Creditos atribuem series de "
          "demonstracao, e o gerador nao existe")
    import radai_credits as CR
    textos = (("NOTICE", ler("NOTICE")),
              ("Creditos", CR.pagina()),
              ("app/radai_credits.py", ler("app/radai_credits.py")))
    fora = _a_demo_ainda_mora(textos)
    checar("nenhum documento atribui dado de demonstracao", not fora,
           " | ".join(fora))
    checar("  isca: o NOTICE com o trecho da demo de volta: reprova",
           bool(_a_demo_ainda_mora((("NOTICE", ler("NOTICE")
                                     + "\nLCTSC — CC BY 3.0\n"),))))
    checar("  isca: os Creditos com a secao da demo de volta: reprova",
           bool(_a_demo_ainda_mora((("Creditos", "<h3>Os dados de "
                                     "demonstração</h3>"),))))
    for rel in ("tools/demos.py", "tools/notice_da_demo.py"):
        checar("%s nao existe (o gerador saiu com a demo)" % rel,
               not os.path.isfile(os.path.join(RAIZ, rel)))


def _rotas_da_bibliografia(src):
    return sorted(set(re.findall(r"@app\.(?:get|post|api_route)\(\s*"
                                 r"[\"']([^\"']+)[\"']", src or "")))


def teste_a_bibliografia_nao_tem_rota_sem_tela():
    secao("a bibliografia: so a tela, sem a rota de dados que nenhuma tela "
          "chama")
    src = ler("app/radai_bibliography.py")
    rotas = _rotas_da_bibliografia(src)
    checar("o modulo serve so /bibliografia (li %s)" % rotas,
           rotas == ["/bibliografia"], str(rotas))
    checar("  isca: a rota /api/bibliografia de volta: reprova",
           _rotas_da_bibliografia(src + '\n    @app.get("/api/bibliografia")'
                                  '\n') != ["/bibliografia"])
    chamam = []
    for _sub, pasta in _componentes.pastas_de(["app"]):
        for raiz, _ds, arqs in os.walk(pasta):
            if "__pycache__" in raiz:
                continue
            for a in arqs:
                if not a.endswith((".py", ".js", ".html")):
                    continue
                with io.open(os.path.join(raiz, a), encoding="utf-8",
                             errors="replace") as f:
                    if "/api/bibliografia" in f.read():
                        chamam.append(a)
    checar("e nenhum arquivo dos sete apps cita /api/bibliografia", not chamam,
           ", ".join(chamam))


def main():
    print("=" * 64)
    print(" test_credits — atribuicao de terceiros e discurso de autoria")
    print("=" * 64)
    testes = [teste_licenca_existe_e_e_a_certa,
              teste_notice_credita_cada_componente,
              teste_notice_da_o_endereco_de_cada_licenca,
              teste_notice_nao_reivindica_autoria,
              teste_tela_le_o_notice_em_vez_de_copiar,
              teste_tela_grita_se_o_notice_sumir,
              teste_a_tela_e_alcancavel_pela_interface,
              teste_os_empacotadores_levam_a_atribuicao,
              teste_interface_nao_atribui_autoria_a_nos,
              teste_declaracao_de_apoio_esta_visivel,
              teste_todo_doi_declara_onde_foi_lido,
              teste_toda_referencia_foi_lida_e_mudou_o_programa,
              teste_o_kong_fica_colado_na_tabela_de_margens,
              teste_a_tela_da_bibliografia_sai_do_dado,
              teste_a_bibliografia_diz_o_que_o_codigo_faz_nos_niveis,
              teste_bibliografia_concorda_com_o_registro,
              teste_notice_cobre_cada_biblioteca_fixada,
              teste_gregoire_com_o_ano_da_publicacao,
              teste_o_notice_declara_todo_sufixo,
              teste_notice_cobre_os_componentes_da_porta,
              teste_a_demo_saiu_dos_creditos_e_do_notice,
              teste_a_bibliografia_nao_tem_rota_sem_tela]
    for t in testes:
        try:
            t()
        except (Exception, SystemExit) as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
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
