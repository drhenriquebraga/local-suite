# -*- coding: utf-8 -*-
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_ent_')

os.environ["RADAI_CALIB_DIR"] = tempfile.mkdtemp(prefix="radai_ent_acervo_")
_TEMP_DA_BATERIA = os.path.dirname(os.environ["RADAI_CALIB_DIR"])


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


def ler(rel):
    p = os.path.join(RAIZ, rel)
    return io.open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else u""


def teste_formato():
    secao(u"gerar() e carimbo() falam a mesma lingua")
    import radai_delivery as E

    texto = E.gerar("AUTO_CONTORNO", "2.0", "2026-08-18", "2026-08-18.abc1234")
    for chave in ("PROJETO=AUTO_CONTORNO", "VERSAO=2.0", "DATA=2026-08-18",
                  "BUILD=2026-08-18.abc1234"):
        checar(u"gerar() escreve %s" % chave, chave in texto)

    tmp = tempfile.mkdtemp(prefix="radai_ent_")
    try:
        alvo = os.path.join(tmp, "entrega.txt")
        io.open(alvo, "w", encoding="utf-8").write(texto)
        campos = E._ler_arquivo(alvo)
        checar(u"a volta fecha: PROJETO", campos.get("PROJETO") == "AUTO_CONTORNO")
        checar(u"a volta fecha: VERSAO", campos.get("VERSAO") == "2.0")
        checar(u"a volta fecha: BUILD", campos.get("BUILD") == "2026-08-18.abc1234")

        com_bom = os.path.join(tmp, "bom.txt")
        io.open(com_bom, "w", encoding="utf-8-sig").write(texto)
        c2 = E._ler_arquivo(com_bom)
        checar(u"le arquivo com BOM sem perder a primeira chave",
               c2.get("PROJETO") == "AUTO_CONTORNO", str(sorted(c2))[:70])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_nao_inventa():
    secao(u"sem carimbo, diz que nao sabe -- nunca um numero plausivel")
    import radai_delivery as E

    salvo_here, salvo_cache = E.HERE, E._LIDO
    tmp = tempfile.mkdtemp(prefix="radai_ent_")
    try:
        vazio = os.path.join(tmp, "programa")
        os.makedirs(vazio)
        E.HERE, E._LIDO = vazio, None
        c = E.carimbo(recarregar=True)
        checar(u"sem arquivo, versao vem VAZIA", c["versao"] == u"", repr(c["versao"]))
        checar(u"sem arquivo, origem vem vazia", c["origem"] == u"")
        checar(u"sem arquivo, o rotulo e string VAZIA", E.rotulo() == u"",
               repr(E.rotulo()))

        io.open(os.path.join(vazio, "entrega.txt"), "w",
                encoding="utf-8").write(u"# so comentario\nLIXO=1\n")
        E._LIDO = None
        checar(u"arquivo sem PROJETO nem VERSAO nao conta",
               E.carimbo(recarregar=True)["versao"] == u"")

        io.open(os.path.join(vazio, "entrega.txt"), "w", encoding="utf-8").write(
            E.gerar("AUTO_CONTORNO", "2.0", "2026-08-18", "2026-08-18.abc1234"))
        E._LIDO = None
        E.carimbo(recarregar=True)
        r = E.rotulo()
        checar(u"com carimbo, o rotulo traz a versao", u"v2.0" in r, r)
        checar(u"com carimbo, o rotulo traz o build",
               u"build 2026-08-18.abc1234" in r, r)
    finally:
        E.HERE, E._LIDO = salvo_here, salvo_cache


def teste_tres_formas():
    secao(u"acha o carimbo nas tres formas: repo, deploy e estacao")
    import radai_delivery as E

    salvo_here, salvo_cache = E.HERE, E._LIDO
    tmp = tempfile.mkdtemp(prefix="radai_ent_")
    try:
        texto = E.gerar("AUTO_CONTORNO", "2.0", "2026-08-18", "b1")

        campo = os.path.join(tmp, "campo")
        os.makedirs(campo)
        io.open(os.path.join(campo, "entrega.txt"), "w", encoding="utf-8").write(texto)
        E.HERE, E._LIDO = campo, None
        checar(u"estacao: acha ao lado dos modulos",
               E.carimbo(recarregar=True)["build"] == "b1")

        for forma in ("repo", "deploy"):
            base = os.path.join(tmp, forma)
            os.makedirs(os.path.join(base, "app"))
            io.open(os.path.join(base, "entrega.txt"), "w",
                    encoding="utf-8").write(texto)
            E.HERE, E._LIDO = os.path.join(base, "app"), None
            checar(u"%s: acha um nivel acima" % forma,
                   E.carimbo(recarregar=True)["build"] == "b1")

        trab = os.path.join(tmp, "trabalho")
        os.makedirs(os.path.join(trab, "app"))
        os.makedirs(os.path.join(trab, ".git"))
        io.open(os.path.join(trab, "entrega.txt"), "w", encoding="utf-8").write(
            u"PROJETO=AUTO_CONTORNO\nVERSAO=2.0\n")
        E.HERE, E._LIDO = os.path.join(trab, "app"), None
        E.carimbo(recarregar=True)
        checar(u"arvore de trabalho e reconhecida pelo .git", E.e_repositorio())
        r = E.rotulo()
        checar(u"e o rotulo diz que nao ha build", u"sem build" in r, r)
        checar(u"mas ainda mostra a versao declarada", u"v2.0" in r, r)
    finally:
        E.HERE, E._LIDO = salvo_here, salvo_cache
        shutil.rmtree(tmp, ignore_errors=True)


def teste_rodape():
    secao(u"o rodape da home mostra o carimbo")
    p = ler("app/radai_panel.py")
    checar(u"a rota /api/painel devolve o carimbo", u'"entrega": _carimbo_entrega()' in p)
    checar(u"o leitor e protegido (rodape nao derruba pagina)",
           u"def _carimbo_entrega(" in p and u"except Exception:" in p)
    checar(u"o rodape imprime o rotulo", u"if(ent.rotulo) pes.push" in p)
    ok, ordem = _entrega_antes_dos_modulos(p)
    checar(u"a entrega vem antes das versoes de modulo, em todo rodape",
           ok, ordem)
    linha = u"if(ent.rotulo) pes.push('<b>'+esc(ent.rotulo)+'</b>');"
    fim = u": 'painel v' + esc(d.versao_painel));"
    n = p.count(linha)
    checar(u"  (isca) a linha da entrega e o fim da dos modulos estao onde a "
           u"isca os procura", n >= 2 and p.count(fim) == n,
           u"%d x %d" % (n, p.count(fim)))
    for k in range(n):
        checar(u"  isca: a entrega DEPOIS dos modulos no rodape %d reprova"
               % (k + 1), not _entrega_antes_dos_modulos(
                   _entrega_depois_no_rodape(p, linha, fim, k))[0])
    checar(u"  isca: a forma antiga (`'painel v'+...`) continua reconhecida",
           _entrega_antes_dos_modulos(
               linha + u"\npes.push('painel v'+esc(d.versao_painel));")[0])


def _entrega_antes_dos_modulos(p):
    marcos = []
    for ancora, tipo in ((u"if(ent.rotulo) pes.push", u"E"), (u"'painel v", u"M")):
        i = p.find(ancora)
        while i >= 0:
            marcos.append((i, tipo))
            i = p.find(ancora, i + 1)
    seq = u"".join(t for _i, t in sorted(marcos))
    ok = (seq.startswith(u"E") and u"M" in seq and u"EE" not in seq
          and not seq.endswith(u"E"))
    return ok, seq


def _entrega_depois_no_rodape(p, linha, fim, k):
    i = -1
    for _ in range(k + 1):
        i = p.find(linha, i + 1)
    q = p[:i] + p[i + len(linha):]
    j = -1
    for _ in range(k + 1):
        j = q.find(fim, j + 1)
    j += len(fim)
    return q[:j] + u"\n" + linha + q[j:]


def teste_empacotadores():
    secao(u"os dois empacotadores carimbam DATA e BUILD")
    emp = ler("build/configurar_ambiente.py")
    checar(u"empacotador tem o gerador de carimbo", u"def _texto_entrega(" in emp)
    car = ler("build/carimbo.py")
    checar(u"ha um gerador de carimbo compartilhado", bool(car),
           u"build/carimbo.py")
    checar(u"ele calcula BUILD com o commit curto",
           u'"rev-parse", "--short", "HEAD"' in car)
    checar(u"sem git, fica so a data (nao inventa commit)",
           u'(u"%s.%s" % (marca, commit)) if commit else marca' in car)
    checar(u"o empacotador do bundle carimba por ele",
           u"import carimbo" in emp and u"carimbo.texto(" in emp)

    lev = ler("build/empacotar_instalador.py")
    checar(u"o empacotador leve tambem carimba, e nao copia",
           u"carimbo.texto(" in lev
           and u'"LICENSE", "NOTICE", "entrega.txt"' not in lev)
    checar(u"o carimbo tambem entra na pasta do programa",
           u'(ctx["bundle"] / "entrega.txt").write_text' in emp,
           u"sem isto o carimbo nao chega na estacao")

    pub = ler("build/empacotar_instalador.py")
    checar(u"o empacotador carimba o entrega.txt",
           u"entrega.txt" in pub)
    checar(u"e le PROJETO e VERSAO de la", u"ler_entrega" in pub)
    checar(u"e aborta sem o entrega.txt",
           u"nao esta em entrega.txt" in pub or u"SystemExit" in pub,
           u"sem o carimbo o pacote nao responde 'qual versao'")

    checar(u"o empacotador GERA o LEIA-ME da pasta",
           u"LEIA_ME_PASTA" in pub and u'"README.txt"' in pub)
    checar(u"e os fatos volateis dele sao marcadores, nao texto fixo",
           all(m in pub for m in (u"%(versao)s", u"%(pacote)s", u"%(mb)s")),
           u"versao, nome do pacote e tamanho foram os que envelheceram")
    checar(u"e o template e' string CRUA (caminho do Windows dentro)",
           u'LEIA_ME_PASTA = r"""' in pub,
           u"sem o `r`, um `\\t` num caminho vira tabulacao")

    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import empacotar_instalador as _E
    _t = _E.LEIA_ME_PASTA % {"projeto": u"X", "versao": u"9.9",
                             "pacote": u"P.zip", "mb": u"1.0 MB"}
    checar(u"o texto gerado aponta a pasta FORA da nuvem",
           u"C:\\RADIOTERAPIA_AI," in _t and u"fora de toda pasta que "
           u"sincroniza" in u" ".join(_t.split()),
           u"e' a separacao fisica que protege o dado de paciente")
    import re as _re
    _oficina = _re.compile(r"(?<![A-Za-z])[A-Za-z]:\\AI(?:_[A-Za-z_]+)?(?![A-Za-z0-9])")
    checar(u"e NAO cita raiz da oficina (o texto vai para o publico)",
           not _oficina.search(_t), _oficina.findall(_t)[:2])
    checar(u"  (isca: uma raiz da oficina no texto e' acusada)",
           bool(_oficina.search(u"guardar em D:" + u"\\AI_X\\exames")))
    checar(u"ele nao tem tabulacao (escape mal resolvido)",
           u"\t" not in _t)
    checar(u"e ele e' ASCII puro", all(ord(c) < 127 for c in _t),
           u"".join(sorted(set(c for c in _t if ord(c) > 126)))[:40])
    checar(u"e o empacotador o grava em CRLF",
           u'newline="\\r\\n"' in pub)


def teste_uma_raiz_so():
    secao(u"uma raiz de entrega, e o bundle fora dela")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import configurar_ambiente as _C

    checar(u"ha UMA raiz de entrega", len(_C.RAIZES_DE_ENTREGA) == 1,
           list(_C.RAIZES_DE_ENTREGA))
    checar(u"e o destino e' `deploy`, SEM caminho escrito ao lado",
           tuple(_C.RAIZES_DE_ENTREGA) == ("deploy",)
           and not isinstance(_C.RAIZES_DE_ENTREGA, dict),
           _C.RAIZES_DE_ENTREGA)
    import ast as _ast

    import re as _re
    _raiz_de_disco = _re.compile(r"^[A-Za-z]:\\[A-Za-z0-9_]+\\?$")

    def _literais_da_raiz(fonte):
        return [n.value for n in _ast.walk(_ast.parse(fonte))
                if isinstance(n, _ast.Constant) and isinstance(n.value, str)
                and _raiz_de_disco.match(n.value.strip())]
    for _rel in ("build/configurar_ambiente.py", "build/empacotar_instalador.py"):
        _lits = _literais_da_raiz(ler(_rel))
        checar(u"%s nao tem pasta de raiz de disco como literal de codigo"
               % _rel, not _lits, _lits)
    checar(u"  (isca: `Path(r\"X:\\PASTA\")` e' acusado)",
           bool(_literais_da_raiz(
               u'RAIZES = {"deploy": Path(r"E:\\ENTREGAS")}\n')))

    try:
        _C.pasta_de_entrega(u"pendrive", u"X", u"1.0")
        checar(u"`--destino pendrive` e' recusado", False, u"aceitou")
    except SystemExit as e:
        msg = str(e)
        checar(u"`--destino pendrive` e' recusado", True)
        checar(u"e a recusa DIZ que a raiz foi apagada",
               u"apagada" in msg.lower(), msg[:90])
        checar(u"e aponta para onde o bundle nasce agora",
               u"_montagem" in msg, msg[:120])

    fonte = ler("build/configurar_ambiente.py")
    corpo = fonte[fonte.find("def main("):]
    checar(u"o bundle NAO chama pasta_de_entrega",
           u"saida = pasta_de_entrega(" not in corpo,
           u"12,6 GB numa raiz que sincroniza")
    checar(u"ele nasce dentro de _montagem",
           u'saida = oficina / ("%s_v%s" % (projeto, versao))' in corpo)

    cmdt = ler("build/CONFIGURAR_AMBIENTE.cmd")
    checar(u"e o .cmd nao declara DESTINO", u'set "DESTINO=' not in cmdt)
    checar(u"nem passa --destino", u"--destino" not in cmdt)


def teste_o_que_foi_removido_nao_volta():
    secao(u"o que foi removido por decisao continua removido")
    REMOVIDOS = [
        (u"publicar.cmd", u"30/08/2026: um empacotador so; ele gerava um "
                          u".zip com 464 bytes de diferenca do instalador"),
    ]
    for nome, porque in REMOVIDOS:
        no_disco = os.path.isfile(os.path.join(RAIZ, nome))
        checar(u"`%s` continua fora do repositorio" % nome, not no_disco,
               porque)


def teste_disco():
    secao(u"o que foi publicado nesta maquina, se houver")
    import glob
    import zipfile
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import destino_de_entrega as _DE
    try:
        pasta = str(_DE.raiz_de_entrega(u"AUTO_CONTORNO", de=RAIZ)[0]
                    / u"AUTO_CONTORNO")
    except SystemExit:
        pasta = u""
    if not pasta or not os.path.isdir(pasta):
        print(u"  (pulado: nao ha deploy nesta maquina)")
        return

    def _chave_de_versao(caminho):
        v = os.path.basename(os.path.dirname(caminho)).lstrip("vV")
        partes = []
        for p in v.split("."):
            partes.append(int(p) if p.isdigit() else 0)
        return partes
    zs = sorted(glob.glob(os.path.join(pasta, "v*", "*_SETUP_*.zip"))
                + glob.glob(os.path.join(pasta, "v*", "*INSTALADOR*.zip")),
                key=_chave_de_versao)
    checar(u"ha um instalador publicado", bool(zs),
           u"procurei em %s\\v*\\" % pasta)
    if not zs:
        return
    import collections
    por_versao = collections.defaultdict(list)
    for p in glob.glob(os.path.join(pasta, "v*", "*.zip")):
        por_versao[os.path.basename(os.path.dirname(p))].append(
            os.path.basename(p))
    repetidas = {v: sorted(a) for v, a in por_versao.items() if len(a) > 1}
    import hashlib
    def _sha(c):
        h = hashlib.sha256()
        with io.open(c, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()

    apelidos = glob.glob(os.path.join(pasta, "latest", "*_SETUP_LATEST.zip"))
    if zs and apelidos:
        atual = zs[-1]
        checar(u"o apelido `latest/` e identico ao artefato mais novo",
               _sha(apelidos[0]) == _sha(atual),
               u"%s != %s -- o hiperlink do site serviria a versao anterior "
               u"sem erro nenhum" % (os.path.basename(apelidos[0]),
                                     os.path.basename(atual)))
    elif zs:
        checar(u"ha o apelido `latest/` para o hiperlink do site",
               False, u"sem ele a URL releases/latest/download/<nome> quebra")

    checar(u"cada versao publicada tem UM artefato so'", not repetidas,
           u"; ".join(u"%s: %s" % (v, u", ".join(a))
                      for v, a in sorted(repetidas.items())))

    import radai_delivery as E
    with zipfile.ZipFile(zs[-1]) as z:
        bruto = z.read("entrega.txt").decode("utf-8-sig", "replace")
    tmp = os.path.join(tempfile.mkdtemp(prefix="radai_ent_"), "entrega.txt")
    io.open(tmp, "w", encoding="utf-8").write(bruto)
    campos = E._ler_arquivo(tmp)
    checar(u"o pacote publicado tem PROJETO",
           campos.get("PROJETO") == "AUTO_CONTORNO", str(campos.get("PROJETO")))
    checar(u"e tem VERSAO", bool(campos.get("VERSAO")))

    lm = os.path.join(pasta, "README.txt")
    if not os.path.isfile(lm):
        print(u"  (a pasta nao tem LEIA-ME.txt)")
        return
    txt = io.open(lm, encoding="ascii", errors="replace").read()
    nome = os.path.basename(zs[-1])
    checar(u"o LEIA-ME da pasta nomeia o pacote que esta la",
           nome in txt, nome)
    checar(u"e a versao dele bate com a do pacote",
           (u"v%s" % campos.get("VERSAO", "?")) in txt,
           u"o pacote e' v%s" % campos.get("VERSAO"))
    checar(u"e ele esta em CRLF (o Bloco de Notas do 14393 nao le LF)",
           io.open(lm, "rb").read().count(b"\n")
           == io.open(lm, "rb").read().count(b"\r\n"))


def teste_raiz_de_entrega_por_marca():
    secao(u"a raiz de entrega: variavel, politica, marca -- e para sem elas")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import destino_de_entrega as D
    base = tempfile.mkdtemp(prefix="radai_ent_raiz_")
    velho = os.environ.pop(D.VARIAVEL, None)
    try:
        eco = os.path.join(base, "ECO")
        repo = os.path.join(eco, "PROJ", "build")
        os.makedirs(repo)
        try:
            D.raiz_de_entrega("PROJ", de=repo)
            checar(u"sem politica nem marca, PARA", False, u"devolveu algo")
        except SystemExit as e:
            checar(u"sem politica nem marca, PARA", True)
            checar(u"  e diz qual variavel definir", D.VARIAVEL in str(e),
                   str(e)[:120])
        io.open(os.path.join(eco, D.POLITICA), "w", encoding="utf-8").write(
            u"# politica sem a linha da conta\n")
        dep = os.path.join(base, "ENTREGAS_X")
        os.makedirs(os.path.join(dep, "PROJ", "v1.0"))
        r, de_onde = D.raiz_de_entrega("PROJ", de=repo)
        checar(u"a MARCA acha a irma que ja tem entregas do projeto",
               os.path.normcase(str(r)) == os.path.normcase(dep), (r, de_onde))
        os.makedirs(os.path.join(base, "OUTRA", "PROJ", "latest"))
        try:
            D.raiz_de_entrega("PROJ", de=repo)
            checar(u"  e com DUAS irmas com entrega, PARA (nao escolhe)",
                   False, u"escolheu por ordem alfabetica")
        except SystemExit:
            checar(u"  e com DUAS irmas com entrega, PARA (nao escolhe)", True)
        io.open(os.path.join(eco, D.POLITICA), "w", encoding="utf-8").write(
            u"deploy    ->  Q:\\ENTREGA_DECLARADA\\<PROJETO>\\v<VERSAO>\\\n")
        r, de_onde = D.raiz_de_entrega("PROJ", de=repo)
        checar(u"a POLITICA declarada vence a marca",
               str(r).rstrip("\\/").upper() == u"Q:\\ENTREGA_DECLARADA",
               (r, de_onde))
        os.environ[D.VARIAVEL] = os.path.join(base, "da_variavel")
        r, de_onde = D.raiz_de_entrega("PROJ", de=repo)
        checar(u"a VARIAVEL vence a politica",
               str(r).endswith("da_variavel") and D.VARIAVEL in de_onde,
               (r, de_onde))
    finally:
        os.environ.pop(D.VARIAVEL, None)
        if velho is not None:
            os.environ[D.VARIAVEL] = velho
        shutil.rmtree(base, ignore_errors=True)


def teste_link_permanente():
    secao(u"o link permanente do instalador (README, preparador, app)")
    import re as _re
    import radai_version as V
    emp = ler("build/empacotar_instalador.py")
    checar(u"o empacotador publica a copia de nome fixo com o MESMO sufixo "
           u"que o app monta",
           (u'"%s' + V.SUFIXO_DO_INSTALADOR + u'"') in emp,
           V.SUFIXO_DO_INSTALADOR)
    nome = V.nome_do_instalador_latest()
    checar(u"o nome sai do PRODUTO do entrega.txt",
           nome == u"RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_LATEST.zip", nome)
    url = str(getattr(V, "URL_VERSOES", "") or "").strip()
    checar(u"achei o URL_VERSOES de fabrica (radai_version.URL_VERSOES)",
           bool(url), url)
    link = V.link_do_instalador(url)
    checar(u"o link e' o `/releases/latest/download/<nome>`",
           link.endswith(u"/releases/latest/download/" + nome)
           and u"/releases/download/v" not in link, link)
    checar(u"  e e' o MESMO link que a tela mostra (sem argumento)",
           link == V.link_do_instalador(), V.link_do_instalador())
    checar(u"  e endereco fora do GitHub nao inventa link",
           V.link_do_instalador(u"https://espelho.hospital/versoes.json") == u"")
    readme = ler("README.md")
    checar(u"o README carrega o link permanente", link and link in readme,
           link)
    checar(u"  e NAO o link preso a uma tag",
           not _re.search(r"/releases/download/v\d", readme),
           _re.findall(r"\S*/releases/download/v\d\S*", readme)[:2])
    prep = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                   encoding="utf-8-sig").read()
    checar(u"o preparador monta o mesmo link (LinkDoInstalador)",
           u"function LinkDoInstalador" in prep
           and u"'/releases/latest/download/'" in prep
           and u"'_SETUP_LATEST.zip'" in prep)
    checar(u"  e o repositorio dele e' o mesmo do URL_VERSOES",
           (u"$script:URL_REPOSITORIO = '%s'" % url.rsplit(u"/releases", 1)[0])
           in prep, url)
    checar(u"  e o botao de «baixar a mais nova» usa o link, e nao a pagina",
           u"$conf.url = LinkDoInstalador" in prep)


def _acervo_isolado(env):
    d = env.get("RADAI_CALIB_DIR") or u""
    base = os.path.normcase(os.path.abspath(_TEMP_DA_BATERIA))
    return (bool(d) and os.path.isdir(d)
            and os.path.normcase(os.path.abspath(d)).startswith(base)
            and os.path.basename(d).startswith("radai_ent_acervo_"))


def teste_acervo_isolado():
    secao(u"o acervo de quem roda a bateria nao e tocado")
    checar(u"RADAI_CALIB_DIR aponta para uma pasta temporaria desta execucao",
           _acervo_isolado(os.environ), os.environ.get("RADAI_CALIB_DIR"))
    checar(u"  isca: sem a variavel, reprova", not _acervo_isolado({}))
    checar(u"  isca: apontando para fora do %TEMP%, reprova",
           not _acervo_isolado({"RADAI_CALIB_DIR": RAIZ}))
    if "radai_archive" in sys.modules:
        raiz = sys.modules["radai_archive"].raiz()
        checar(u"um modulo importado carregou o acervo, e ele caiu no "
               u"temporario", os.path.normcase(str(raiz)).startswith(
                   os.path.normcase(os.environ["RADAI_CALIB_DIR"])), str(raiz))
    else:
        checar(u"nenhum modulo importado por esta bateria carregou o acervo "
               u"(medido pelo sys.modules)", True)


def teste_o_bundle_carimba_o_produto():
    secao(u"o bundle carimba o PRODUTO, e o botao acha o instalador")
    import ast as _ast
    import importlib.util as _iu
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import configurar_ambiente as _C
    import carimbo as _car
    projeto, versao, produto = _C.ler_entrega(_C.RAIZ)
    checar(u"(o repositorio declara um PRODUTO diferente do PROJETO)",
           produto and produto != projeto, u"%s / %s" % (projeto, produto))
    texto = _C._texto_entrega(projeto, versao, produto)
    checar(u"o `entrega.txt` do bundle leva `PRODUTO=`",
           (u"PRODUTO=%s" % produto) in texto, texto[:200])

    def _nome_na_estacao(txt):
        casa = tempfile.mkdtemp(prefix="radai_ent_estacao_")
        try:
            os.makedirs(os.path.join(casa, "app"))
            shutil.copy2(_componentes.fonte("app/radai_version.py"),
                         os.path.join(casa, "app", "radai_version.py"))
            with io.open(os.path.join(casa, "entrega.txt"), "w",
                         encoding="utf-8") as f:
                f.write(txt)
            sp = _iu.spec_from_file_location(
                "radai_version_estacao",
                os.path.join(casa, "app", "radai_version.py"))
            m = _iu.module_from_spec(sp)
            sp.loader.exec_module(m)
            return m.nome_do_instalador_latest()
        finally:
            shutil.rmtree(casa, ignore_errors=True)
    publicado = produto + u"_SETUP_LATEST.zip"
    checar(u"na estacao instalada pelo bundle, o botao aponta para o asset "
           u"PUBLICADO", _nome_na_estacao(texto) == publicado,
           _nome_na_estacao(texto))
    antigo = _car.texto(projeto, versao, raiz=_C.RAIZ)
    checar(u"ISCA: com o carimbo de antes (sem o produto), o botao aponta "
           u"para um asset que nao existe",
           _nome_na_estacao(antigo) == projeto + u"_SETUP_LATEST.zip"
           and _nome_na_estacao(antigo) != publicado,
           _nome_na_estacao(antigo))
    fonte = ler("build/configurar_ambiente.py")
    fn = next(n for n in _ast.parse(fonte).body
              if isinstance(n, _ast.FunctionDef)
              and n.name == "_avulsos_do_pacote")
    chamadas = [n for n in _ast.walk(fn) if isinstance(n, _ast.Call)
                and getattr(n.func, "id", None) == "_texto_entrega"]
    checar(u"(ast) `_avulsos_do_pacote` chama `_texto_entrega` com o produto",
           chamadas and all(len(c.args) >= 3 for c in chamadas)
           and u'"produto"' in _ast.get_source_segment(fonte, chamadas[0]),
           [_ast.get_source_segment(fonte, c) for c in chamadas])


def teste_a_arvore_suja_se_declara_no_build():
    secao(u"a arvore suja se declara no BUILD")
    import inspect as _insp
    import subprocess as _sp
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import carimbo as _car
    casa = tempfile.mkdtemp(prefix="radai_ent_git_")
    try:
        def git(*a):
            return _sp.check_output(
                ["git", "-c", "user.name=bateria",
                 "-c", "user.email=bateria@exemplo.invalid"] + list(a),
                cwd=casa, stderr=_sp.STDOUT, timeout=30)
        try:
            git("init", "-q")
            with io.open(os.path.join(casa, "a.txt"), "w") as f:
                f.write(u"um\n")
            git("add", "a.txt")
            git("commit", "-q", "-m", "fantoma")
        except Exception as e:
            checar(u"(o git desta maquina monta o repositorio fantoma)", False,
                   str(e)[:120])
            return
        limpo = _car._commit_curto(casa)
        checar(u"arvore limpa: o commit puro, sem marca",
               limpo and not limpo.endswith(_car.MARCA_DE_ARVORE_SUJA), limpo)
        checar(u"  e sem aviso no log (a arvore limpa nao grita)",
               _car.aviso_de_arvore_suja(
                   _car.texto(u"PROJ", u"9.9", u"PROD", raiz=casa)) == u"")
        with io.open(os.path.join(casa, "a.txt"), "w") as f:
            f.write(u"dois\n")
        sujo = _car._commit_curto(casa)
        checar(u"arquivo alterado e nao commitado: o commit sai com "
               u"`%s`" % _car.MARCA_DE_ARVORE_SUJA,
               sujo == limpo + _car.MARCA_DE_ARVORE_SUJA, sujo)
        data, build = _car.dados(casa)
        checar(u"  e o BUILD do `entrega.txt` diz isso",
               build.endswith(_car.MARCA_DE_ARVORE_SUJA), build)
        txt_sujo = _car.texto(u"PROJ", u"9.9", u"PROD", raiz=casa)
        checar(u"  e o aviso sai do `entrega.txt` montado com a arvore suja "
               u"(ASCII, para o console do preparador)",
               _car.aviso_de_arvore_suja(txt_sujo)
               == _car.AVISO_DE_ARVORE_SUJA
               and all(ord(c) < 128 for c in _car.AVISO_DE_ARVORE_SUJA),
               txt_sujo)
        import ast as _ast
        for arq, saida in (("empacotar_instalador.py", "print"),
                           ("configurar_ambiente.py", "log")):
            fonte = io.open(os.path.join(RAIZ, "build", arq),
                            encoding="utf-8").read()

            def _liga(texto_, _saida=saida):
                arv = _ast.parse(texto_)
                chama = any(isinstance(n, _ast.Call)
                            and getattr(n.func, "attr", None)
                            == "aviso_de_arvore_suja"
                            for n in _ast.walk(arv))
                diz = any(isinstance(n, _ast.If) and any(
                    isinstance(c, _ast.Call)
                    and getattr(c.func, "id", None) == _saida
                    for c in _ast.walk(n)) and "aviso" in _ast.dump(n.test)
                    for n in _ast.walk(arv))
                return chama and diz
            checar(u"  e `%s` chama o aviso e o poe no log (%s)" % (arq, saida),
                   _liga(fonte))
            forjada = fonte.replace(u"aviso_de_arvore_suja(", u"dados(")
            checar(u"  (isca) `%s` sem a chamada do aviso: a checagem acusa"
                   % arq, forjada != fonte and not _liga(forjada))
        git("checkout", "-q", "--", "a.txt")
        with io.open(os.path.join(casa, "novo.py"), "w") as f:
            f.write(u"x = 1\n")
        checar(u"arquivo NOVO nao ignorado (um modulo que ainda nao entrou "
               u"no commit) tambem marca",
               _car._commit_curto(casa).endswith(_car.MARCA_DE_ARVORE_SUJA))
        src = _insp.getsource(_car._commit_curto)
        alvo = (u"    if commit and (_arvore_suja(raiz) or "
                u"componentes_sujos(raiz)):\n"
                u"        commit += MARCA_DE_ARVORE_SUJA\n")
        checar(u"  (isca) a marca esta onde a isca a procura", alvo in src)
        ns = dict(vars(_car))
        exec(compile(src.replace(alvo, u""), "<isca-carimbo>", "exec"), ns)
        checar(u"ISCA: o `_commit_curto` de antes carimba a arvore suja com o "
               u"commit puro (o defeito da revisao, reproduzido)",
               ns["_commit_curto"](casa) == limpo)
    finally:
        def _tirar_so_leitura(fn, caminho, _exc):
            try:
                os.chmod(caminho, 0o700)
                fn(caminho)
            except Exception:
                pass
        shutil.rmtree(casa, onerror=_tirar_so_leitura)


def main():
    print(u"=" * 68)
    print(u"test_delivery | o carimbo do build e o rodape que o mostra")
    print(u"=" * 68)
    teste_formato()
    teste_nao_inventa()
    teste_tres_formas()
    teste_rodape()
    teste_empacotadores()
    teste_uma_raiz_so()
    teste_raiz_de_entrega_por_marca()
    teste_link_permanente()
    teste_o_bundle_carimba_o_produto()
    teste_a_arvore_suja_se_declara_no_build()
    teste_o_que_foi_removido_nao_volta()
    teste_disco()
    teste_acervo_isolado()
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
