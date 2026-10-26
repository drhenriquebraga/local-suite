# -*- coding: utf-8 -*-
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "build"))
import _componentes as C
import _cleanup
import baixar_componentes as B
OFICINA = C.oficina("componentes", __file__)

_cleanup.adotar_prefixo('radai_comp_')
_cleanup.adotar_prefixo('radai_baixa_')
_cleanup.adotar_prefixo('radai_exp_')

_RESULTADOS = []


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    print(u"  %s  %s%s" % (u"ok   " if ok else u"FALHA", nome,
                           (u"  [%s]" % detalhe) if detalhe and not ok else u""))


def secao(t):
    print(u"\n── %s " % t + u"─" * max(3, 60 - len(t)))


def gravar(caminho, texto):
    if not os.path.isdir(os.path.dirname(caminho)):
        os.makedirs(os.path.dirname(caminho))
    with io.open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)


def marca(pasta, nome, suite="local-suite"):
    gravar(os.path.join(pasta, "componente.json"),
           json.dumps({"suite": suite, "nome": nome, "app": [], "baterias": []}))


def mundo():
    base = tempfile.mkdtemp(prefix="radai_comp_")
    suite = os.path.join(base, "SUITE")
    gravar(os.path.join(suite, "app", "radai_comum.py"), u"X = 1\n")
    gravar(os.path.join(suite, "NOTAS.md"), u"suite\n")
    a = os.path.join(base, "APP_A")
    marca(a, "APP_A")
    gravar(os.path.join(a, "app", "radai_a.py"),
           u"import radai_comum\nY = radai_comum.X\n")
    gravar(os.path.join(a, "tools", "test_a.py"), u"print('OK: 1 checagens')\n")
    gravar(os.path.join(a, "NOTAS.md"), u"app a\n")
    outro = os.path.join(base, "OUTRO_PROJETO")
    marca(outro, "OUTRO", suite="outra-suite")
    gravar(os.path.join(outro, "app", "radai_x.py"), u"Z = 1\n")
    os.makedirs(os.path.join(base, "SEM_MARCA", "app"))
    return base, suite, a


@contextlib.contextmanager
def sem_a_variavel():
    antes = os.environ.pop(C.VARIAVEL_DA_PASTA, None)
    try:
        yield
    finally:
        if antes is not None:
            os.environ[C.VARIAVEL_DA_PASTA] = antes


def teste_o_mundo_falso_nao_ve_a_variavel():
    secao(u"a suíte de mentira não enxerga a pasta de RADAI_COMPONENTES_DIR")
    base, suite, a = mundo()
    outra = tempfile.mkdtemp(prefix="radai_comp_")
    antes = os.environ.get(C.VARIAVEL_DA_PASTA)
    try:
        marca(os.path.join(outra, "APP_REAL"), "APP_REAL")
        gravar(os.path.join(outra, "APP_REAL", "app", "radai_a.py"), u"W = 1\n")
        os.environ[C.VARIAVEL_DA_PASTA] = outra
        vazou = [d.get("nome") for _, d in C.componentes(suite)]
        checar(u"(isca) com a variável no ambiente, a suíte de mentira acha "
               u"os componentes da outra pasta", vazou == ["APP_REAL"], vazou)
        with sem_a_variavel():
            isolado = [d.get("nome") for _, d in C.componentes(suite)]
        checar(u"sem a variável, ela acha só os componentes ao lado dela",
               isolado == ["APP_A"], isolado)
        checar(u"  e a variável volta ao ambiente depois",
               os.environ.get(C.VARIAVEL_DA_PASTA) == outra)
    finally:
        if antes is None:
            os.environ.pop(C.VARIAVEL_DA_PASTA, None)
        else:
            os.environ[C.VARIAVEL_DA_PASTA] = antes
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(outra, ignore_errors=True)


_SUITE_DE_MENTIRA = ("teste_marca_e_resolvedor", "teste_programa_instalado",
                     "teste_montar_e_contratos",
                     "teste_montagem_sem_o_que_o_git_ignora",
                     "teste_o_carimbo_ve_o_app_alterado")


def teste_marca_e_resolvedor():
    secao(u"a marca acha os componentes; o resolvedor acha a fonte")
    base, suite, a = mundo()
    try:
        achados = [d.get("nome") for _, d in C.componentes(suite)]
        checar(u"acha só o componente desta suíte", achados == ["APP_A"], achados)
        checar(u"fonte de app/ acha no componente",
               C.fonte("app/radai_a.py", suite) == os.path.join(a, "app", "radai_a.py"))
        checar(u"fonte da Suite vem antes",
               C.fonte("NOTAS.md", suite) == os.path.join(suite, "NOTAS.md"))
        checar(u"fonte de arquivo ausente devolve o caminho da Suite (a leitura falha alto)",
               C.fonte("app/nao_existe.py", suite) == os.path.join(suite, "app", "nao_existe.py"))
        checar(u"nomes() junta as pastas app/",
               C.nomes("app", suite) == ["radai_a.py", "radai_comum.py"], C.nomes("app", suite))
        juntos = C.ler_todos("NOTAS.md", suite)
        checar(u"ler_todos junta o arquivo da Suite e o do componente",
               u"suite" in juntos and u"app a" in juntos)
        checar(u"o dono de um arquivo é o componente dele",
               C.dono("app/radai_a.py", suite) == "APP_A"
               and C.dono("app/radai_comum.py", suite) == "SUITE")
        gravar(os.path.join(a, "app", "radai_comum.py"), u"X = 2\n")
        try:
            C.nomes("app", suite)
            dup = False
        except C.ComponenteDuplicado:
            dup = True
        checar(u"(isca) o mesmo módulo em duas pastas é recusado", dup)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_programa_instalado():
    secao(u"no programa instalado os módulos ficam soltos na raiz, sem app/")
    base = tempfile.mkdtemp(prefix="radai_comp_")
    try:
        prog = os.path.join(base, "PROGRAMA")
        gravar(os.path.join(prog, "radai_ui.py"), u"X = 1\n")
        gravar(os.path.join(prog, "engine.py"), u"Y = 1\n")
        os.makedirs(os.path.join(prog, "tools"))
        checar(u"fonte de app/ acha o módulo solto na raiz",
               C.fonte("app/engine.py", prog) == os.path.join(prog, "engine.py"))
        checar(u"nomes() lista os módulos soltos",
               C.nomes("app", prog) == ["engine.py", "radai_ui.py"], C.nomes("app", prog))
        os.remove(os.path.join(prog, "radai_ui.py"))
        checar(u"(isca) sem a marca, não confunde a raiz com o app",
               C.fonte("app/engine.py", prog) == os.path.join(prog, "app", "engine.py"))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_montar_e_contratos():
    secao(u"a montagem num app só, e os contratos medidos")
    base, suite, a = mundo()
    try:
        destino = os.path.join(base, "montado")
        feitos = C.montar_app_limpo(destino, suite)
        checar(u"a montagem leva os dois módulos",
               os.path.isfile(os.path.join(destino, "radai_a.py"))
               and os.path.isfile(os.path.join(destino, "radai_comum.py")), feitos)
        os.remove(os.path.join(a, "app", "radai_a.py"))
        C.montar_app_limpo(destino, suite)
        checar(u"o que saiu da origem sai da montagem na vez seguinte",
               not os.path.exists(os.path.join(destino, "radai_a.py")))
        gravar(os.path.join(a, "app", "radai_a.py"),
               u"import radai_comum\nY = radai_comum.X\n")
        usos = C.contratos(suite)
        checar(u"o contrato mede o que o componente usa da Suite",
               usos.get("APP_A", {}).get("SUITE", {}).get("radai_comum") == {"X"}, usos)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_pasta_alternativa():
    secao(u"RADAI_COMPONENTES_DIR troca a origem dos componentes")
    base, suite, a = mundo()
    antes = os.environ.get(C.VARIAVEL_DA_PASTA)
    try:
        baixados = os.path.join(base, "baixados")
        marca(os.path.join(baixados, "APP_B"), "APP_B")
        os.environ[C.VARIAVEL_DA_PASTA] = baixados
        achados = [d.get("nome") for _, d in C.componentes(suite)]
        checar(u"com a variável, os componentes vêm da pasta dela", achados == ["APP_B"], achados)
    finally:
        if antes is None:
            os.environ.pop(C.VARIAVEL_DA_PASTA, None)
        else:
            os.environ[C.VARIAVEL_DA_PASTA] = antes
        shutil.rmtree(base, ignore_errors=True)


def _marca_bytes(nome):
    return json.dumps({"suite": "local-suite", "nome": nome}).encode("utf-8")


def _zipball(caminho, nome, arquivos, topo="org-repo-abc123", ordem=1,
             compressao=zipfile.ZIP_STORED, data=(1980, 1, 1, 0, 0, 0)):
    todos = [("componente.json", _marca_bytes(nome))] + sorted(arquivos.items())
    with zipfile.ZipFile(caminho, "w", compressao) as z:
        for rel, conteudo in todos[::ordem]:
            info = zipfile.ZipInfo(topo + "/" + rel, date_time=data)
            info.compress_type = compressao
            z.writestr(info, conteudo)


def _arvore(nome, arquivos):
    todos = dict(arquivos)
    todos["componente.json"] = _marca_bytes(nome)
    linhas = sorted((rel, hashlib.sha256(c).hexdigest()) for rel, c in todos.items())
    texto = u"".join(u"%s  %s\n" % (s, r) for r, s in linhas)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _sha(caminho):
    return hashlib.sha256(io.open(caminho, "rb").read()).hexdigest()


def _bytes(caminho):
    try:
        return io.open(caminho, "rb").read()
    except OSError:
        return None


def _origem(servidor):
    return "file:///" + servidor.replace("\\", "/") + "/{repositorio}-{tag}.zip"


_SEM = object()


def teste_baixador():
    secao(u"o baixador: trava pela árvore extraída, zip slip e marca")
    base = tempfile.mkdtemp(prefix="radai_baixa_")
    try:
        servidor = os.path.join(base, "servidor")
        os.makedirs(servidor)
        arquivos = {"app/radai_a.py": b"Y = 1\n",
                    "verify.cmd": b"@echo off\r\npause\r\n"}
        bom = os.path.join(servidor, "APP_A-v1.zip")
        _zipball(bom, "APP_A", arquivos)
        mesmo = os.path.join(servidor, "APP_A-v1b.zip")
        _zipball(mesmo, "APP_A", arquivos, topo="org-repo-def456", ordem=-1,
                 compressao=zipfile.ZIP_DEFLATED, data=(2026, 10, 20, 12, 0, 0))
        origem = _origem(servidor)
        trava = os.path.join(base, "trava.json")
        certa = _arvore("APP_A", arquivos)

        def escrever_trava(**kw):
            item = {"nome": "APP_A", "repositorio": "APP_A", "tag": "v1",
                    "arvore_sha256": certa}
            item.update(kw)
            item = dict((k, v) for k, v in item.items() if v is not _SEM)
            gravar(trava, json.dumps({"componentes": [item]}))

        destino = os.path.join(base, "baixados")
        escrever_trava()
        feitos = B.baixar_todos(destino, trava, origem, avisar=lambda *_: None)
        checar(u"baixa, confere a árvore e extrai sem a pasta de topo",
               feitos and os.path.isfile(os.path.join(destino, "APP_A", "app", "radai_a.py")), feitos)
        checar(u"a árvore é o sha256 do manifesto: cada arquivo pelo caminho sem a pasta "
               u"de topo, em ordem, com os bytes como o zip os entrega",
               B.arvore_sha256(os.path.join(destino, "APP_A")) == certa)
        linhas = B.manifesto_da_arvore(os.path.join(destino, "APP_A")).splitlines()
        checar(u"o manifesto tem uma linha legível por arquivo, em ordem",
               [l.split(u"  ", 1)[1] for l in linhas]
               == [u"app/radai_a.py", u"componente.json", u"verify.cmd"], linhas)

        def parou(**kw):
            escrever_trava(**kw)
            try:
                B.baixar_todos(destino, trava, origem, avisar=lambda *_: None)
            except B.Parei as e:
                return str(e)
            return ""
        checar(u"(isca) o mesmo conteúdo em outro zip tem outros bytes",
               _sha(mesmo) != _sha(bom))
        checar(u"  e passa pela mesma trava (outra pasta de topo, outra ordem, "
               u"outra compressão, outra data)", parou(tag="v1b") == u"")

        _zipball(os.path.join(servidor, "APP_A-v4.zip"), "APP_A",
                 dict(arquivos, **{"app/radai_a.py": b"Y = 2\n"}))
        erro = parou(tag="v4")
        checar(u"(isca) um arquivo trocado reprova", u"árvore" in erro, erro)
        checar(u"  e a pasta final continua a conferida (a reprovada não chega a ela)",
               _bytes(os.path.join(destino, "APP_A", "app", "radai_a.py"))
               == b"Y = 1\n"
               and not os.path.exists(os.path.join(destino, "APP_A.baixando")))
        _zipball(os.path.join(servidor, "APP_A-v5.zip"), "APP_A",
                 dict(arquivos, **{"verify.cmd": b"@echo off\npause\n"}))
        checar(u"(isca) o fim de linha conta: o .cmd em LF no lugar do CRLF reprova",
               u"árvore" in parou(tag="v5"))
        _zipball(os.path.join(servidor, "APP_A-v6.zip"), "APP_A",
                 dict(arquivos, **{"app/radai_extra.py": b""}))
        checar(u"(isca) um arquivo a mais reprova", u"árvore" in parou(tag="v6"))
        checar(u"(isca) sem tag, para", u"sem versão" in parou(tag=None))
        checar(u"(isca) sem a árvore na trava, para e diz como travar",
               u"--travar" in parou(arvore_sha256=_SEM))
        checar(u"(isca) o sha256 dos bytes do zip, sozinho, não basta",
               u"--travar" in parou(arvore_sha256=_SEM, sha256=_sha(bom)))

        mal = os.path.join(servidor, "APP_A-v2.zip")
        with zipfile.ZipFile(mal, "w") as z:
            z.writestr("org-repo-x/componente.json",
                       json.dumps({"suite": "local-suite", "nome": "APP_A"}))
            z.writestr("org-repo-x/../../fora.txt", "x")
        checar(u"(isca) zip que grava fora da pasta, para",
               u"fora da pasta" in parou(tag="v2"))
        checar(u"  e nada foi gravado fora",
               not os.path.exists(os.path.join(base, "fora.txt")))

        outro = os.path.join(servidor, "APP_A-v3.zip")
        _zipball(outro, "OUTRO_NOME", {"app/x.py": b"x"})
        checar(u"(isca) pacote com a marca de outro app, para",
               u"marca" in parou(tag="v3",
                                 arvore_sha256=_arvore("OUTRO_NOME", {"app/x.py": b"x"})))
        checar(u"  e a pasta final continua a conferida",
               _bytes(os.path.join(destino, "APP_A", "app", "radai_a.py"))
               == b"Y = 1\n")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_travar():
    secao(u"--travar escreve a trava com a árvore do que o repositório serve")
    base = tempfile.mkdtemp(prefix="radai_baixa_")
    try:
        servidor = os.path.join(base, "servidor")
        os.makedirs(servidor)
        de_a = {"app/radai_a.py": b"Y = 9\n"}
        de_b = {"app/radai_b.py": b"Z = 9\n"}
        _zipball(os.path.join(servidor, "APP_A-v9.zip"), "APP_A", de_a)
        _zipball(os.path.join(servidor, "APP_B-v9.zip"), "APP_B", de_b)
        origem = _origem(servidor)
        trava = os.path.join(base, "trava.json")
        gravar(trava, json.dumps({"_leia": u"antigo", "componentes": [
            {"nome": "APP_A", "repositorio": "APP_A", "tag": "v1", "sha256": "0" * 64},
            {"nome": "APP_B", "repositorio": "APP_B", "tag": None}]}))
        r = B.main(["--travar", "v9", "--trava", trava, "--origem", origem])
        dados = json.load(io.open(trava, encoding="utf-8-sig"))
        a, b = dados["componentes"]
        checar(u"a linha de comando --travar <tag> termina com 0", r == 0, r)
        checar(u"a tag nova e a árvore de cada app vão para a trava",
               a.get("tag") == "v9" and a.get("arvore_sha256") == _arvore("APP_A", de_a)
               and b.get("tag") == "v9" and b.get("arvore_sha256") == _arvore("APP_B", de_b),
               dados)
        checar(u"o sha256 dos bytes do zip sai da trava",
               "sha256" not in a and "sha256" not in b, dados)
        checar(u"a ordem, os repositórios e o texto que explica a trava ficam",
               [c["nome"] for c in dados["componentes"]] == ["APP_A", "APP_B"]
               and a.get("repositorio") == "APP_A"
               and dados.get("_leia") == B.LEIA_DA_TRAVA, dados)
        feitos = B.baixar_todos(os.path.join(base, "baixados"), trava, origem,
                                avisar=lambda *_: None)
        checar(u"e a trava escrita passa no baixador", len(feitos) == 2, feitos)

        _zipball(os.path.join(servidor, "APP_A-v10.zip"), "OUTRO", de_a)
        _zipball(os.path.join(servidor, "APP_B-v10.zip"), "APP_B", de_b)
        antes = io.open(trava, "rb").read()
        try:
            B.travar("v10", trava, origem, avisar=lambda *_: None)
            erro = u""
        except B.Parei as e:
            erro = u"%s" % e
        checar(u"(isca) pacote com a marca de outro app não trava, e a trava fica "
               u"como estava", u"marca" in erro and io.open(trava, "rb").read() == antes,
               erro)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_empacotador_confere_a_arvore():
    secao(u"o empacotador confere de novo a árvore do que veio da trava")
    import empacotar_instalador as E
    base = tempfile.mkdtemp(prefix="radai_baixa_")
    antes = os.environ.get(C.VARIAVEL_DA_PASTA)
    try:
        servidor = os.path.join(base, "servidor")
        os.makedirs(servidor)
        arquivos = {"app/radai_a.py": b"Y = 1\n"}
        _zipball(os.path.join(servidor, "APP_A-v1.zip"), "APP_A", arquivos)
        trava = os.path.join(base, "trava.json")
        gravar(trava, json.dumps({"componentes": [
            {"nome": "APP_A", "repositorio": "APP_A", "tag": "v1",
             "arvore_sha256": _arvore("APP_A", arquivos)}]}))
        baixados = os.path.join(base, "baixados")
        B.baixar_todos(baixados, trava, _origem(servidor), avisar=lambda *_: None)
        os.environ[C.VARIAVEL_DA_PASTA] = baixados
        suite = os.path.join(base, "SUITE")
        os.makedirs(suite)
        modulo = os.path.join(baixados, "APP_A", "app", "radai_a.py")

        def coletou():
            try:
                return [n for n, _ in E.coletar_componentes(set(), suite=suite,
                                                            trava=trava)], u""
            except SystemExit as e:
                return [], u"%s" % e
        nomes, erro = coletou()
        checar(u"a pasta baixada, com a árvore da trava, entra no instalador",
               u"app/radai_a.py" in nomes and not erro, erro)
        io.open(modulo, "wb").write(b"Y = 2\n")
        nomes, erro = coletou()
        checar(u"(isca) um arquivo mexido depois do download PARA o pacote",
               not nomes and u"arvore" in erro, erro)
        io.open(modulo, "wb").write(b"Y = 1\n")
        nomes, erro = coletou()
        checar(u"  e, desfeito, volta a passar", u"app/radai_a.py" in nomes, erro)
        io.open(os.path.join(baixados, "APP_A", "app", "radai_novo.py"), "wb").write(b"")
        nomes, erro = coletou()
        checar(u"(isca) um arquivo a mais na pasta baixada PARA o pacote",
               not nomes and u"arvore" in erro, erro)
        os.remove(os.path.join(baixados, "APP_A", "app", "radai_novo.py"))
        gravar(trava, json.dumps({"componentes": [
            {"nome": "APP_A", "repositorio": "APP_A", "tag": "v1",
             "arvore_sha256": _arvore("APP_A", arquivos)},
            {"nome": "APP_B", "repositorio": "APP_B", "tag": "v1",
             "arvore_sha256": "0" * 64}]}))
        nomes, erro = coletou()
        checar(u"(isca) um app da trava que não está ao lado PARA o pacote, "
               u"com o nome dele", not nomes and u"APP_B" in erro, erro)
    finally:
        if antes is None:
            os.environ.pop(C.VARIAVEL_DA_PASTA, None)
        else:
            os.environ[C.VARIAVEL_DA_PASTA] = antes
        shutil.rmtree(base, ignore_errors=True)


def teste_exportador():
    if OFICINA is None:
        secao(u"o exportador do componente")
        C.pulado(u"o exportador dos componentes")
        return
    OFICINA.teste_exportador(sys.modules[__name__])


def teste_trava_do_repositorio():
    secao(u"a trava versionada lista os seis apps")
    lista = B.ler_trava()
    nomes = sorted(c["nome"] for c in lista)
    checar(u"os seis componentes estão na trava",
           nomes == sorted(["CONTOURLAB", "DICOM_BRIDGE", "RECON_3D", "NIDUS_RT",
                            "ELASTIC_RT", "3D_PRINTED_BOLUS"]), nomes)
    reais = sorted(d.get("nome") for _, d in C.componentes())
    checar(u"e são os mesmos que a marca acha nesta máquina (quando há irmãs)",
           not reais or reais == nomes, reais)
    import re
    sem = [c["nome"] for c in lista
           if not re.match(r"^[0-9a-f]{64}$", c.get("arvore_sha256") or "")]
    checar(u"cada componente traz a árvore (64 hexa)", not sem, sem)
    checar(u"e nenhum traz o sha256 dos bytes do zip, que o GitHub não promete estável",
           not [c["nome"] for c in lista if "sha256" in c])


def _confere_antes_do_nome(fonte):
    import ast
    try:
        arv = ast.parse(fonte)
    except SyntaxError:
        return False
    principal = next((n for n in arv.body if isinstance(n, ast.FunctionDef)
                      and n.name == "main"), None)
    if principal is None:
        return False
    confere = troca = copia = None
    for no in ast.walk(principal):
        if not isinstance(no, ast.Call):
            continue
        nome = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
        if nome == "conferir_montado" and confere is None:
            confere = no.lineno
        elif nome == "replace" and troca is None:
            troca = no.lineno
        elif nome == "copy2" and copia is None:
            copia = no.lineno
    return bool(confere and troca and copia and confere < troca < copia)


def teste_o_empacotador_confere_antes_do_nome_oficial():
    secao(u"o empacotador confere o .zip antes de dar o nome oficial e o LATEST")
    fonte = io.open(os.path.join(RAIZ, "build", "empacotar_instalador.py"),
                    encoding="utf-8").read()
    checar(u"o main confere o .parcial antes do os.replace e da cópia para "
           u"o LATEST", _confere_antes_do_nome(fonte))
    isca = (u"def main():\n    os.replace(tmp, saida)\n"
            u"    shutil.copy2(saida, fixo)\n    conferir_montado(saida, m)\n")
    checar(u"  (isca) a conferência depois do nome oficial reprova",
           not _confere_antes_do_nome(isca))


def teste_o_carimbo_ve_o_app_alterado():
    secao(u"o carimbo diz +alterado quando um app irmão tem alteração")
    import subprocess
    if not shutil.which("git"):
        print(u"  PULADO: sem git no PATH")
        return
    import carimbo as K
    base, suite, a = mundo()
    try:
        os.makedirs(os.path.join(suite, "tools"), exist_ok=True)
        shutil.copy2(os.path.join(AQUI, "_componentes.py"),
                     os.path.join(suite, "tools", "_componentes.py"))

        def git(pasta, *args):
            return subprocess.run(
                ["git", "-c", "user.name=bateria",
                 "-c", "user.email=bateria@exemplo.invalid"] + list(args),
                cwd=pasta, capture_output=True, timeout=60)
        for pasta in (suite, a):
            git(pasta, "init", "-q")
            git(pasta, "add", "-A")
            git(pasta, "commit", "-q", "-m", "fantoma")
        limpo = K._commit_curto(suite)
        checar(u"a Suite e o app limpos: o BUILD sem a marca",
               bool(limpo) and not limpo.endswith(K.MARCA_DE_ARVORE_SUJA),
               limpo)
        gravar(os.path.join(a, "app", "radai_a.py"), u"Y = 2\n")
        sujo = K._commit_curto(suite)
        checar(u"o app com arquivo versionado alterado: o BUILD da Suite "
               u"limpa sai com %s" % K.MARCA_DE_ARVORE_SUJA,
               sujo == limpo + K.MARCA_DE_ARVORE_SUJA, sujo)
        checar(u"  e o carimbo diz qual app", K.componentes_sujos(suite)
               == ["APP_A"], K.componentes_sujos(suite))
        checar(u"  (isca) olhando só a Suite, a alteração do app passaria",
               not K._arvore_suja(suite))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_montagem_sem_o_que_o_git_ignora():
    secao(u"a montagem deixa de fora o estado de execução que o .gitignore ignora")
    import subprocess
    if not shutil.which("git"):
        print(u"  PULADO: sem git no PATH, a montagem copia tudo (como antes)")
        return
    base, suite, a = mundo()
    try:
        gravar(os.path.join(a, ".gitignore"), u"app/registro/\napp/modelos/\n")
        gravar(os.path.join(a, "app", "registro", "segredo.chave"), u"x\n")
        gravar(os.path.join(a, "app", "modelos", "escolhido.txt"), u"a\n")
        gravar(os.path.join(suite, "app", "modelos", "escolhido.txt"), u"s\n")
        gravar(os.path.join(a, "app", "radai_novo.py"), u"Z = 1\n")
        subprocess.run(["git", "init", "-q", a], capture_output=True,
                       timeout=60)
        checar(u"(isca) sem Git na pasta da Suite, o estado dela entra",
               C.nao_ignorados(os.path.join(suite, "app")) is None)
        destino = os.path.join(base, "montado")
        try:
            feitos = C.montar_app_limpo(destino, suite)
            dup = u""
        except C.ComponenteDuplicado as e:
            feitos, dup = [], u"%s" % e
        checar(u"o arquivo de execução nas duas pastas não para a montagem",
               not dup, dup)
        checar(u"o que o .gitignore do app ignora não é montado",
               not os.path.exists(os.path.join(destino, "registro",
                                               "segredo.chave")), feitos)
        checar(u"  e o escolhido.txt que monta é o da pasta sem Git",
               io.open(os.path.join(destino, "modelos", "escolhido.txt"),
                       encoding="utf-8").read().strip() == u"s"
               if os.path.isfile(os.path.join(destino, "modelos",
                                              "escolhido.txt")) else False)
        checar(u"o arquivo novo, ainda fora do Git e não ignorado, entra",
               os.path.isfile(os.path.join(destino, "radai_novo.py")))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    print(u"=" * 66 + u"\ntest_componentes | o integrador e o baixador\n" + u"=" * 66)
    for t in (teste_o_mundo_falso_nao_ve_a_variavel,
              teste_marca_e_resolvedor, teste_programa_instalado, teste_montar_e_contratos,
              teste_montagem_sem_o_que_o_git_ignora,
              teste_pasta_alternativa, teste_baixador, teste_travar,
              teste_empacotador_confere_a_arvore,
              teste_o_empacotador_confere_antes_do_nome_oficial,
              teste_o_carimbo_ve_o_app_alterado, teste_exportador,
              teste_trava_do_repositorio):
        try:
            if t.__name__ in _SUITE_DE_MENTIRA:
                with sem_a_variavel():
                    t()
            else:
                t()
        except Exception as e:
            import traceback
            checar(u"%s (exceção inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    falhas = [n for n, ok, _ in _RESULTADOS if not ok]
    print(u"\n" + u"=" * 66)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n in falhas:
            print(u"  - " + n)
    else:
        print(u"OK: %d checagens, todas passaram" % len(_RESULTADOS))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
