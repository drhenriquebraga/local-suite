# -*- coding: utf-8 -*-
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


def _zipball(caminho, nome, arquivos, topo="org-repo-abc123"):
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr(topo + "/componente.json",
                   json.dumps({"suite": "local-suite", "nome": nome}))
        for rel, texto in arquivos.items():
            z.writestr(topo + "/" + rel, texto)


def _sha(caminho):
    return hashlib.sha256(io.open(caminho, "rb").read()).hexdigest()


def teste_baixador():
    secao(u"o baixador: trava, sha256, zip slip e marca")
    base = tempfile.mkdtemp(prefix="radai_baixa_")
    try:
        servidor = os.path.join(base, "servidor")
        os.makedirs(servidor)
        bom = os.path.join(servidor, "APP_A-v1.zip")
        _zipball(bom, "APP_A", {"app/radai_a.py": "Y = 1\n"})
        origem = "file:///" + servidor.replace("\\", "/") + "/{repositorio}-{tag}.zip"
        trava = os.path.join(base, "trava.json")

        def escrever_trava(**kw):
            item = {"nome": "APP_A", "repositorio": "APP_A", "tag": "v1", "sha256": _sha(bom)}
            item.update(kw)
            gravar(trava, json.dumps({"componentes": [item]}))

        destino = os.path.join(base, "baixados")
        escrever_trava()
        feitos = B.baixar_todos(destino, trava, origem, avisar=lambda *_: None)
        checar(u"baixa, confere o sha256 e extrai sem a pasta de topo",
               feitos and os.path.isfile(os.path.join(destino, "APP_A", "app", "radai_a.py")), feitos)

        def parou(**kw):
            escrever_trava(**kw)
            try:
                B.baixar_todos(destino, trava, origem, avisar=lambda *_: None)
            except B.Parei as e:
                return str(e)
            return ""
        checar(u"(isca) sem tag, para", u"sem versão" in parou(tag=None))
        checar(u"(isca) sha256 diferente da trava, para", u"sha256" in parou(sha256="0" * 64))

        mal = os.path.join(servidor, "APP_A-v2.zip")
        with zipfile.ZipFile(mal, "w") as z:
            z.writestr("org-repo-x/componente.json",
                       json.dumps({"suite": "local-suite", "nome": "APP_A"}))
            z.writestr("org-repo-x/../../fora.txt", "x")
        checar(u"(isca) zip que grava fora da pasta, para",
               u"fora da pasta" in parou(tag="v2", sha256=_sha(mal)))
        checar(u"  e nada foi gravado fora",
               not os.path.exists(os.path.join(base, "fora.txt")))

        outro = os.path.join(servidor, "APP_A-v3.zip")
        _zipball(outro, "OUTRO_NOME", {"app/x.py": "x"})
        checar(u"(isca) pacote com a marca de outro app, para",
               u"marca" in parou(tag="v3", sha256=_sha(outro)))
    finally:
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


def main():
    print(u"=" * 66 + u"\ntest_componentes | o integrador e o baixador\n" + u"=" * 66)
    for t in (teste_marca_e_resolvedor, teste_programa_instalado, teste_montar_e_contratos,
              teste_pasta_alternativa, teste_baixador, teste_exportador,
              teste_trava_do_repositorio):
        try:
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
