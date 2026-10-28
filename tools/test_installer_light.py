# -*- coding: utf-8 -*-
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
_cleanup.adotar_prefixo('radai_leve_')

os.environ["RADAI_CALIB_DIR"] = tempfile.mkdtemp(prefix="radai_leve_acervo_")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ok = 0
_falhou = 0
_falhas = []


def secao(t):
    print(u"")
    print(u"── %s %s" % (t, u"─" * max(0, 58 - len(t))))


def checar(rotulo, cond, detalhe=u""):
    global _ok, _falhou
    if cond:
        _ok += 1
        print(u"  OK     %s" % rotulo)
    else:
        _falhou += 1
        _falhas.append(rotulo)
        print(u"  FALHA  %s  %s" % (rotulo, str(detalhe).replace("\n", " | ")[:160]))


def montar_zip(destino):
    py = sys.executable
    amb = dict(os.environ)
    amb["RADAI_RAIZ_DEPLOY"] = tempfile.mkdtemp(prefix="radai_leve_deploy_")
    r = subprocess.run([py, os.path.join(RAIZ, "build",
                                         "empacotar_instalador.py")],
                       cwd=RAIZ, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, env=amb)
    saida = r.stdout.decode("utf-8", "replace")
    m = re.search(r"PRONTO:\s*(.+\.zip)", saida)
    if not m:
        return "", saida
    return m.group(1).strip(), saida


def teste_o_zip_abre_e_tem_forma():
    secao(u"o .zip que a pessoa recebe abre, e tem a forma do contrato")
    caminho, log = montar_zip(None)
    checar(u"o empacotador monta o instalador", bool(caminho), log[-200:])
    if not caminho:
        return None
    checar(u"e o arquivo existe no disco", os.path.isfile(caminho), caminho)
    tam = os.path.getsize(caminho)
    checar(u"e ele cabe num e-mail (< 25 MB)", tam < 25e6,
           u"%.1f MB" % (tam / 1e6))

    base = tempfile.mkdtemp(prefix="radai_leve_")
    alvo = os.path.join(base, "extraido")
    with zipfile.ZipFile(caminho) as z:
        ruim = z.testzip()
        checar(u"nenhum membro corrompido", ruim is None, ruim)
        z.extractall(alvo)
    checar(u"ele extrai", os.path.isdir(alvo))

    ENTRADA = "START_HERE.cmd"
    cmds = set(f for f in os.listdir(alvo) if f.lower().endswith(".cmd"))
    checar(u"o START_HERE.cmd esta na raiz do extraido", ENTRADA in cmds,
           sorted(cmds))
    checar(u"e nao ha `.cmd` desconhecido ao lado dele",
           not (cmds - {ENTRADA}), sorted(cmds - {ENTRADA}))
    checar(u"a verificacao profunda saiu da instalacao: nao ha verify.cmd no "
           u"instalador leve", "verify.cmd" not in cmds, sorted(cmds))

    arquivos_raiz = {n for n in os.listdir(alvo) if os.path.isfile(os.path.join(alvo, n))}
    checar(u"a raiz contem apenas README.txt e START_HERE.cmd",
           arquivos_raiz == {"README.txt", "START_HERE.cmd"}, arquivos_raiz)
    alvo = os.path.join(alvo, "programa")
    checar(u"o conteudo do instalador fica em programa/", os.path.isdir(alvo))

    CLICAVEIS = {
        u"app/RADIOTERAPIA_AI_LOCAL_SUITE.cmd",
        u"app/launchers/open_browser.cmd",
        u"app/launchers/start_watcher.cmd",
        u"build/CONFIGURAR_AMBIENTE.cmd",
        u"installer/INSTALL.cmd",
        u"installer/UNINSTALL.cmd",
        u"packager/PREPARAR_AUTO_CONTORNO.cmd",
        u"packager/START_HERE.cmd",
    }
    achados = set()
    for raiz, _dirs, arqs in os.walk(alvo):
        for a in arqs:
            if a.lower().endswith((u".cmd", u".bat", u".hta")):
                rel = os.path.relpath(os.path.join(raiz, a), alvo)
                achados.add(rel.replace(os.sep, u"/"))
    checar(u"nenhum clicavel DESCONHECIDO na arvore do pacote",
           not (achados - CLICAVEIS),
           u"%s -- clicavel novo entra nesta lista de proposito"
           % sorted(achados - CLICAVEIS))
    checar(u"  e nenhum dos esperados sumiu",
           not (CLICAVEIS - achados),
           u"faltam: %s" % sorted(CLICAVEIS - achados))

    _ent_zip = io.open(os.path.join(alvo, "entrega.txt"),
                       encoding="utf-8-sig").read()
    _min_repo = re.search(r"^\s*BUNDLE_MINIMO\s*=\s*(.+?)\s*$",
                          io.open(os.path.join(RAIZ, "entrega.txt"),
                                  encoding="utf-8-sig").read(), re.M)
    checar(u"o entrega.txt do artefato traz o BUNDLE_MINIMO do repositorio",
           bool(_min_repo) and (u"BUNDLE_MINIMO=%s" % _min_repo.group(1))
           in _ent_zip, _ent_zip.strip().splitlines()[-2:])

    tam = os.path.join(alvo, "PACKAGE_SIZE.txt")
    checar(u"o PACKAGE_SIZE.txt viajou em programa/", os.path.isfile(tam))
    checar(u"o preparer_log.ps1 viajou ao lado do prepare.ps1",
           os.path.isfile(os.path.join(alvo, "packager", "preparer_log.ps1")))
    if os.path.isfile(tam):
        cru = io.open(tam, "rb").read()
        checar(u"  em ASCII, numa linha so' (o `set /p` le a primeira)",
               all(b < 128 for b in cru) and cru.strip().count(b"\n") == 0,
               repr(cru[:40]))
        try:
            cat = __import__("json").load(io.open(
                os.path.join(alvo, "packager", "catalogo.json"),
                encoding="utf-8"))
            esperado = u"%.0f" % cat["pacote"]["pacote_gib"]
        except Exception as e:
            esperado = u"(catalogo sem bloco pacote: %s)" % e
        lido = cru.decode("ascii", "replace").strip()
        checar(u"  e ele e' o numero do catalogo (%s GB)" % esperado,
               lido == esperado, u"PACKAGE_SIZE.txt diz %r" % lido)
        leia = io.open(os.path.join(os.path.dirname(alvo), "README.txt"),
                       encoding="utf-8", errors="replace").read()
        checar(u"  e o README.txt da raiz diz o mesmo",
               (u"ABOUT %s GB" % lido) in u" ".join(leia.split()),
               u"o LEIA-ME fala um numero e o .cmd outro")

    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import empacotar_instalador as _E
    try:
        _E.LEIA_ME_PASTA % {"projeto": u"X", "versao": u"9.9",
                            "pacote": u"P.zip", "mb": u"1.0 MB"}
        _falta = u""
    except KeyError as e:
        _falta = u"%s" % e
    checar(u"o LEIA-ME da pasta fecha com as QUATRO chaves de `test_delivery`",
           not _falta, u"o molde pede %s, que o outro leitor nao passa" % _falta)
    checar(u"  e o empacotador o reescreveu (sem AVISO)",
           u"LEIA-ME.txt da pasta reescrito" in log
           and u"nao consegui reescrever o LEIA-ME" not in log,
           [l for l in log.splitlines() if u"LEIA-ME" in l][:2])
    _pasta = os.path.join(os.path.dirname(os.path.dirname(caminho)), "README.txt")
    checar(u"  e ele esta la, sem marcador cru",
           os.path.isfile(_pasta) and u"%(" not in io.open(
               _pasta, encoding="ascii", errors="replace").read(), _pasta)
    return alvo


def teste_a_montagem_acha_tudo(alvo):
    secao(u"o motor acha, dentro do extraido, tudo o que ele le")
    if not alvo:
        return
    engine = os.path.join(alvo, "build", "configurar_ambiente.py")
    checar(u"o motor do preparo viajou", os.path.isfile(engine))
    if not os.path.isfile(engine):
        return
    fonte = io.open(engine, encoding="utf-8", errors="replace").read()

    lidos = set(re.findall(r'RAIZ / "([^"/]+\.[a-z]+)"', fonte))
    for _tupla in re.findall(r'for nome in \(([^)]*)\):\s*\n\s*origem = RAIZ / nome', fonte):
        lidos |= set(re.findall(r'"([^"/]+)"', _tupla))
    lidos = sorted(lidos)
    checar(u"ele le ao menos um arquivo da raiz", bool(lidos), lidos)
    for nome in lidos:
        p = os.path.join(alvo, nome)
        checar(u"  ele le `%s`, e ele esta la" % nome, os.path.isfile(p),
               u"%s -- e' o defeito de 30/08: FileNotFoundError na etapa 5, "
               u"depois de 12,6 GB baixados" % p)

    ESCRITAS = {"_montagem"}
    pastas = sorted(set(re.findall(r'RAIZ / "([a-z_]+)"', fonte)) - ESCRITAS)
    for nome in pastas:
        p = os.path.join(alvo, nome)
        checar(u"  e a pasta `%s/`" % nome, os.path.isdir(p), p)

    for rel in ("installer/INSTALL.cmd", "installer/INSTALL.ps1",
                "installer/UNINSTALL.cmd", "installer/UNINSTALL.ps1"):
        p = os.path.join(alvo, rel.replace("/", os.sep))
        checar(u"  o contrato: %s" % rel, os.path.isfile(p), p)


def teste_a_etapa_5_roda_de_verdade(alvo):
    secao(u"a etapa 5 monta o programa a partir do extraido")
    if not alvo:
        return
    trab = tempfile.mkdtemp(prefix="radai_leve_")

    io.open(os.path.join(trab, "LICENCAS_ACEITAS.txt"), "w",
            encoding="utf-8").write(
        u"[ACEITA] Python (PSF)\n[ACEITA] TotalSegmentator (Apache-2.0)\n"
        u"[ACEITA] MONAI VISTA-3D (NVIDIA License, clausula 3.3)\n"
        u"[ACEITA] PyTorch (BSD-3)\n[ACEITA] pydicom (MIT)\n"
        u"[ACEITA] SimpleITK (Apache-2.0)\n")

    r = subprocess.run(
        [sys.executable, os.path.join(alvo, "build", "configurar_ambiente.py"),
         "--etapas", "5", "--preparo", trab],
        cwd=alvo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    saida = r.stdout.decode("utf-8", "replace")
    checar(u"a etapa 5 termina sem erro", r.returncode == 0,
           saida[-300:])
    checar(u"e nao foi por falta de arquivo",
           u"FileNotFoundError" not in saida and u"No such file" not in saida,
           [l for l in saida.splitlines() if u"Error" in l][:2])

    prog = None
    for raiz, dirs, arqs in os.walk(trab):
        if "radai_watcher.py" in arqs:
            prog = raiz
            break
    checar(u"o programa foi montado", bool(prog), trab)
    if not prog:
        return
    cmds = sorted(f for f in os.listdir(prog) if f.lower().endswith(".cmd"))
    checar(u"a raiz do programa tem UM clicavel", len(cmds) == 1, cmds)
    checar(u"e ele e' o lancador",
           cmds == ["RADIOTERAPIA_AI_LOCAL_SUITE.cmd"], cmds)

    lanc = os.path.join(prog, "launchers")
    ferr = os.path.join(prog, "maintenance")
    checar(u"os lancadores foram para `launchers/`", os.path.isdir(lanc))
    checar(u"e a manutencao para `maintenance/`", os.path.isdir(ferr))
    if os.path.isdir(lanc):
        tem = sorted(os.listdir(lanc))
        for nome in ("start_watcher.cmd", "open_browser.cmd"):
            checar(u"  launchers/%s" % nome, nome in tem, tem)
        checar(u"  e launchers/start_engine.cmd NAO existe mais (o servidor "
               u"que ele subia saiu na v8.2)", "start_engine.cmd" not in tem,
               tem)
    if os.path.isdir(ferr):
        tem = sorted(os.listdir(ferr))
        for nome in ("UNINSTALL.cmd", "UNINSTALL.ps1"):
            checar(u"  maintenance/%s" % nome, nome in tem, tem)
        checar(u"  e maintenance/verify.cmd NAO existe (a verificacao profunda "
               u"saiu da instalacao)", "verify.cmd" not in tem, tem)
    checar(u"a forma montada e' a da estacao: sem `app\\`",
           not os.path.isdir(os.path.join(prog, "app")), prog)
    checar(u"a pasta demo/ nao nasce no programa montado",
           not os.path.exists(os.path.join(prog, "demo")))

    imp = os.path.join(prog, "_requisitos.json")
    checar(u"a impressao de requisitos viajou", os.path.isfile(imp),
           u"sem ela a atualizacao manda SEMPRE preparar pacote com internet")
    if os.path.isfile(imp):
        try:
            d = __import__("json").load(io.open(imp, encoding="utf-8"))
        except Exception as e:
            d = {}
            checar(u"  e ela e' JSON legivel", False, str(e)[:90])
        checar(u"  e tem impressao", len(str(d.get("impressao", ""))) >= 16,
               d.get("impressao"))
        checar(u"  e ela sai de fontes de verdade",
               int(d.get("linhas_requirements") or 0) > 0
               and bool(d.get("tasks")) and bool(d.get("versoes")),
               u"linhas=%s tasks=%s versoes=%s"
               % (d.get("linhas_requirements"), len(d.get("tasks") or []),
                  len(d.get("versoes") or {})))

    checar(u"o favicon.ico chegou ao programa montado",
           os.path.isfile(os.path.join(prog, "favicon.ico")),
           u"sem ele o atalho da area de trabalho fica com o icone antigo")

    checar(u"a conferencia da estacao viajou",
           os.path.isfile(os.path.join(prog, "radai_station_check.py")))
    checar(u"e o dicionario de idiomas tambem",
           os.path.isfile(os.path.join(prog, "radai_phrases.py")))
    return prog


NAO_VAO_PELO_ATUALIZAR = {
    u"VERSION.txt": u"o carimbo para quem le; o `entrega.txt` e' o de codigo",
    u"PACKAGE_SIZE.txt": u"o tamanho do pacote completo, lido pelo START_HERE",
    u"entrega.txt": u"o ATUALIZAR o copia a parte, junto com o "
                    u"`_requisitos.json` (passo 6)",
    u"packager/": u"o preparador: roda da pasta extraida do pacote leve (o "
                  u"botao Atualizar le o `UPDATE.ps1` dali), e o programa "
                  u"instalado nao le nada dele",
    u"build/": u"o motor do preparo e o empacotador; a estacao nao monta pacote",
    u"installer/": u"o contrato de instalacao: o `INSTALL.ps1` roda uma vez, "
                   u"de dentro do pacote, e o `UNINSTALL` vai para "
                   u"`maintenance\\` na etapa 5 -- que o ATUALIZAR nunca traz",
    u"tools/data/": u"fixture das baterias do repositorio (`test_nv_segment`); "
                    u"a estacao nao roda bateria, e a etapa 5 copia so' "
                    u"`tools/*.py`",
    u"tools/check_ps1_members.ps1": u"guarda de `test_packager`, que nao roda "
                                    u"na estacao (ver `tools/data/`)",
    u"tools/lerantes.ps1": u"guarda do `check_project`, que nao roda na "
                           u"estacao (ver `tools/data/`)",
}


def _lista_do_atualizar(texto, nome):
    for l in texto.splitlines():
        m = re.match(r'^\$%s\s*=\s*@\((.*)\)\s*$' % re.escape(nome), l.strip())
        if m:
            return [d.replace(u"\\", u"/") for d in re.findall(r'"([^"]+)"',
                                                               m.group(1))]
    return None


def _documentos_do_atualizar(texto):
    return _lista_do_atualizar(texto, u"DOCUMENTOS")


def _declarado(rel, declarados):
    return rel in declarados or any(
        k.endswith(u"/") and rel.startswith(k) for k in declarados)


def _vai_pelo_atualizar(rel, copiadas, docs):
    topo = rel.split(u"/")[0]
    if topo in copiadas and u"/" in rel:
        return os.path.splitext(rel)[1].lower() in set(
            e.lower() for e in copiadas[topo])
    return rel in docs


def _copia_so_app_e_tools(texto):
    chamadas = re.findall(r'(?m)^\s*Aplicar \(Join-Path \$PACOTE "(\w+)"\)', texto)
    return (sorted(chamadas) == [u"app", u"tools"]
            and re.search(r'(?m)^\s*Aplicar \(Join-Path \$PACOTE "app"\) '
                          r'\$INST \$EXT_APP\s*$', texto) is not None
            and re.search(r'(?m)^\s*Aplicar \(Join-Path \$PACOTE "tools"\) '
                          r'\(Join-Path \$INST "tools"\) \$EXT_TOOLS\s*$',
                          texto) is not None)


def _sem_destino(todos, copiadas, docs, declarados=None):
    declarados = NAO_VAO_PELO_ATUALIZAR if declarados is None else declarados
    return sorted(a for a in todos
                  if not _vai_pelo_atualizar(a, copiadas, docs)
                  and not _declarado(a, declarados))


def teste_o_atualizar_leva_o_que_o_zip_leva_fora_das_pastas(alvo):
    secao(u"o ATUALIZAR leva o que o .zip leva, ou o que fica esta declarado")
    if not alvo:
        return
    up = os.path.join(alvo, "packager", "UPDATE.ps1")
    checar(u"o UPDATE.ps1 viajou no .zip", os.path.isfile(up))
    if not os.path.isfile(up):
        return
    texto = io.open(up, encoding="utf-8-sig").read()
    docs = _documentos_do_atualizar(texto)
    checar(u"achei o `$DOCUMENTOS` do atualizador", bool(docs), docs)
    docs = docs or []
    for d in docs:
        checar(u"  `%s` esta no .zip, no caminho que o atualizador copia" % d,
               os.path.isfile(os.path.join(alvo, d.replace(u"/", os.sep))),
               u"o atualizador so' copia o que o pacote traz -- sem o arquivo, "
               u"a copia simplesmente nao acontece")
    ext_app = _lista_do_atualizar(texto, u"EXT_APP")
    ext_tools = _lista_do_atualizar(texto, u"EXT_TOOLS")
    checar(u"achei `$EXT_APP` e `$EXT_TOOLS` do atualizador",
           bool(ext_app) and bool(ext_tools), (ext_app, ext_tools))
    copiadas = {u"app": ext_app or [], u"tools": ext_tools or []}
    checar(u"  e ele copia as duas pastas com essas listas, e nenhuma outra",
           _copia_so_app_e_tools(texto),
           re.findall(r'(?m)^\s*Aplicar .*$', texto))
    checar(u"  (isca: uma terceira pasta copiada e' acusada)",
           not _copia_so_app_e_tools(
               texto + u'\nAplicar (Join-Path $PACOTE "build") $INST $EXT_APP\n'))

    todos = set()
    for raiz, _dirs, arqs in os.walk(alvo):
        for a in arqs:
            todos.add(os.path.relpath(os.path.join(raiz, a), alvo)
                      .replace(os.sep, u"/"))
    checar(u"o .zip leva o que ele copia (o programa) e o que ele leva a "
           u"parte (o NOTICE)",
           _vai_pelo_atualizar(u"app/radai_watcher.py", copiadas, docs)
           and u"app/radai_watcher.py" in todos and u"NOTICE" in todos,
           sorted(todos)[:8])

    soltos = _sem_destino(todos, copiadas, docs)
    checar(u"todo arquivo do .zip vai pelo ATUALIZAR, ou esta declarado "
           u"fora dele com o motivo", not soltos,
           u"%s -- ponha no `$DOCUMENTOS` do UPDATE.ps1 (texto aceito, "
           u"procedencia) ou em NAO_VAO_PELO_ATUALIZAR, com o porque" % soltos)
    for nome in (u"NOTICE", u"LICENSE"):
        checar(u"  e `%s` esta entre os que ele leva" % nome, nome in docs, docs)
    def contradiz(declarados):
        return sorted(k for k in declarados
                      if any(_declarado(a, {k: u""})
                             and _vai_pelo_atualizar(a, copiadas, docs)
                             for a in todos))
    checar(u"nenhuma declaracao cobre arquivo que o ATUALIZAR copia",
           not contradiz(NAO_VAO_PELO_ATUALIZAR), contradiz(NAO_VAO_PELO_ATUALIZAR))
    checar(u"  (isca: declarar `app/radai_watcher.py` como fora e' acusado)",
           contradiz({u"app/radai_watcher.py": u"x"}) == [u"app/radai_watcher.py"])
    def velhas(declarados):
        return sorted(k for k in declarados
                      if not any(_declarado(a, {k: u""}) for a in todos))
    checar(u"toda declaracao ainda existe no .zip",
           not velhas(NAO_VAO_PELO_ATUALIZAR), velhas(NAO_VAO_PELO_ATUALIZAR))

    checar(u"  (isca: um arquivo novo na raiz, fora das duas listas, e' acusado)",
           u"dados/nova_fonte.json" in _sem_destino(
               todos | {u"dados/nova_fonte.json"}, copiadas, docs))
    checar(u"  (isca: o `$DOCUMENTOS` so' com o NOTICE deixa o LICENSE de fora)",
           u"LICENSE" in _sem_destino(
               todos, copiadas, _documentos_do_atualizar(
                   u'$DOCUMENTOS = @("NOTICE")') or []))
    checar(u"  (isca: um `.css` novo em `app/`, que o `$EXT_APP` nao cobre, "
           u"e' acusado)",
           u"app/estilo.css" in _sem_destino(
               todos | {u"app/estilo.css"}, copiadas, docs))
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import empacotar_instalador as _E
    cinco = set(dentro for _o, dentro in _E.PASTAS)
    velha = sorted(a for a in todos | {u"app/estilo.css"}
                   if a.split(u"/")[0] not in cinco
                   and a not in docs and a not in NAO_VAO_PELO_ATUALIZAR)
    checar(u"  (isca: com a premissa antiga -- as cinco pastas do pacote, "
           u"sem extensao -- o mesmo `.css` passaria calado)",
           len(cinco) == 5 and u"app/estilo.css" not in velha, sorted(cinco))
    checar(u"  (isca: uma declaracao que o .zip nao leva mais e' acusada)",
           velhas(dict(NAO_VAO_PELO_ATUALIZAR,
                       **{u"tools/nao_existe_mais.ps1": u"x"}))
           == [u"tools/nao_existe_mais.ps1"])


def _git(pasta, *args):
    try:
        r = subprocess.run(["git", "-C", pasta] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def _novos_desde_a_ultima_tag(pasta):
    tag = (_git(pasta, "describe", "--tags", "--abbrev=0") or u"").strip()
    if not tag:
        return u"", None
    lista = _git(pasta, "diff", "--name-only", "--diff-filter=A", tag, "HEAD",
                 "--", "app", "tools")
    if lista is None:
        return tag, None
    return tag, sorted(l.strip() for l in lista.splitlines() if l.strip())


def _novos_que_nao_chegam(novos, todos, copiadas, docs):
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import empacotar_instalador as _E
    return sorted(n for n in novos
                  if _E.entra(n)
                  and not (n in todos
                           and (_vai_pelo_atualizar(n, copiadas, docs)
                                or _declarado(n, NAO_VAO_PELO_ATUALIZAR))))


def teste_os_arquivos_novos_chegam_pelo_atualizar(alvo):
    secao(u"os arquivos novos desde a ultima versao vao no .zip e pelo ATUALIZAR")
    if not alvo:
        return
    texto = io.open(os.path.join(alvo, "packager", "UPDATE.ps1"),
                    encoding="utf-8-sig").read()
    docs = _documentos_do_atualizar(texto) or []
    copiadas = {u"app": _lista_do_atualizar(texto, u"EXT_APP") or [],
                u"tools": _lista_do_atualizar(texto, u"EXT_TOOLS") or []}
    todos = set()
    for raiz, _dirs, arqs in os.walk(alvo):
        for a in arqs:
            todos.add(os.path.relpath(os.path.join(raiz, a), alvo)
                      .replace(os.sep, u"/"))
    sys.path.insert(0, os.path.join(RAIZ, "tools"))
    import _componentes
    pastas = [(RAIZ, u"Suite")] + [
        (p, d.get("nome") or os.path.basename(p))
        for p, d in _componentes.componentes(RAIZ)]
    novos, sem_git = [], []
    for pasta, nome in pastas:
        tag, lista = _novos_desde_a_ultima_tag(pasta)
        if lista is None:
            sem_git.append(nome)
            continue
        novos += lista
    if sem_git:
        _componentes.pulado(u"arquivos novos sem Git ou sem tag em %s"
                            % u", ".join(sem_git))
    if not novos:
        print(u"  (nenhum arquivo novo em app/ ou tools/ desde a ultima tag)")
    faltam = _novos_que_nao_chegam(novos, todos, copiadas, docs)
    checar(u"todo arquivo novo de app/ e tools/ das sete pastas esta no .zip "
           u"e vai pelo ATUALIZAR (%d novos)" % len(novos), not faltam,
           u"%s -- o pacote ou o `$EXT_APP`/`$EXT_TOOLS` do UPDATE.ps1 nao o "
           u"levam, e a estacao que so atualiza fica sem ele" % faltam)
    checar(u"  (isca: um `.css` novo em `app/` seria acusado)",
           _novos_que_nao_chegam([u"app/radai_novo.css"],
                                 todos | {u"app/radai_novo.css"}, copiadas,
                                 docs) == [u"app/radai_novo.css"])
    checar(u"  (isca: um `.py` novo que o .zip nao leva seria acusado)",
           _novos_que_nao_chegam([u"app/radai_nao_empacotado.py"], todos,
                                 copiadas, docs)
           == [u"app/radai_nao_empacotado.py"])
    checar(u"  (isca: o que o empacotador recusa de proposito nao e' acusado)",
           _novos_que_nao_chegam([u"tools/__pycache__/x.pyc"], todos,
                                 copiadas, docs) == [])


def teste_o_lancador_alcanca_o_preparador(alvo):
    secao(u"o START_HERE alcanca o preparador")
    if not alvo:
        return
    com = io.open(os.path.join(os.path.dirname(alvo), "START_HERE.cmd"),
                  encoding="utf-8", errors="replace").read()
    checar(u"ele chama o prepare.ps1", u"prepare.ps1" in com)
    checar(u"e o prepare.ps1 esta no extraido",
           os.path.isfile(os.path.join(alvo, "packager", "prepare.ps1")))
    checar(u"e o dicionario do preparador viajou",
           os.path.isfile(os.path.join(alvo, "packager", "languages.json")))

    ps1 = io.open(os.path.join(alvo, "packager", "prepare.ps1"),
                  encoding="utf-8-sig", errors="replace").read()
    checar(u"o preparador nao passa `--destino pendrive`",
           u"'--destino', 'pendrive'" not in ps1,
           u"a raiz foi apagada; escrever nela a recria em silencio")
    engine = io.open(os.path.join(alvo, "build", "configurar_ambiente.py"),
                    encoding="utf-8", errors="replace").read()
    checar(u"e o motor tem UMA raiz de entrega, achada por marca e sem "
           u"caminho absoluto",
           engine.count(u'Path(r"C:\\') == 0
           and u"destino_de_entrega.raiz_de_entrega(" in engine,
           u"PENDRIVE_AI_EXPORT saiu; so a raiz de entrega ficou")


def main():
    print(u"=" * 66)
    print(u"test_installer_light | o unico artefato que se entrega")
    print(u"=" * 66)
    alvo = teste_o_zip_abre_e_tem_forma()
    teste_a_montagem_acha_tudo(alvo)
    teste_o_atualizar_leva_o_que_o_zip_leva_fora_das_pastas(alvo)
    teste_os_arquivos_novos_chegam_pelo_atualizar(alvo)
    teste_o_lancador_alcanca_o_preparador(alvo)
    teste_a_etapa_5_roda_de_verdade(alvo)
    print(u"\n" + u"=" * 66)
    if _falhou:
        print(u"FALHOU: %d de %d checagens" % (_falhou, _ok + _falhou))
        for f in _falhas:
            print(u"  - %s" % f)
    else:
        print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 66)
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
