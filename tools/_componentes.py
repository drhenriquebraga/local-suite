# -*- coding: utf-8 -*-
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import sysconfig

MARCA = "componente.json"
SUITE = "local-suite"
NOME_DO_PTH = "radai_componentes.pth"
IGNORAR = ("__pycache__",)
COMPONENTES_FORA_DA_BASE = frozenset(("NIDUS_RT",))
_EXTRAS = {}


class ComponenteDuplicado(Exception):
    pass


def raiz_da_suite():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ler_marca(pasta):
    caminho = os.path.join(pasta, MARCA)
    if not os.path.isfile(caminho):
        return None
    try:
        with io.open(caminho, encoding="utf-8-sig") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        return None
    if dados.get("suite") != SUITE:
        return None
    return dados


VARIAVEL_DA_PASTA = "RADAI_COMPONENTES_DIR"


def pasta_dos_componentes(suite=None):
    alternativa = os.environ.get(VARIAVEL_DA_PASTA, "").strip()
    if alternativa:
        return os.path.abspath(alternativa)
    return os.path.dirname(os.path.abspath(suite or raiz_da_suite()))


def componentes(suite=None):
    suite = suite or raiz_da_suite()
    mae = pasta_dos_componentes(suite)
    if not os.path.isdir(mae):
        return []
    achados = []
    for nome in sorted(os.listdir(mae)):
        pasta = os.path.join(mae, nome)
        if not os.path.isdir(pasta) or (
                os.path.exists(suite) and os.path.samefile(pasta, suite)):
            continue
        dados = _ler_marca(pasta)
        if dados is not None and dados.get("nome") not in COMPONENTES_FORA_DA_BASE:
            achados.append((pasta, dados))
    return achados


MARCA_DO_APP_SOLTO = "radai_ui.py"


def _pasta_de(raiz, sub):
    p = os.path.join(raiz, sub)
    if (sub == "app" and not os.path.isdir(p)
            and os.path.isfile(os.path.join(raiz, MARCA_DO_APP_SOLTO))):
        return raiz
    return p


def pastas_base(sub, suite=None):
    suite = suite or raiz_da_suite()
    saida = [_pasta_de(suite, sub)]
    for pasta, _ in componentes(suite):
        p = os.path.join(pasta, sub)
        if os.path.isdir(p):
            saida.append(p)
    return saida


def pastas(sub, suite=None):
    saida = pastas_base(sub, suite)
    if sub == "app":
        for pasta in _EXTRAS.get(os.path.normcase(os.path.abspath(suite or raiz_da_suite())), ()):
            if pasta not in saida:
                saida.append(pasta)
    return saida


def pastas_de(subs, suite=None, app_rel="app"):
    suite = suite or raiz_da_suite()
    saida = [(sub, os.path.join(suite, app_rel if sub == "app" else sub))
             for sub in subs]
    for pasta, _ in componentes(suite):
        for sub in subs:
            p = os.path.join(pasta, sub)
            if sub in ("app", "tools") and os.path.isdir(p):
                saida.append((sub, p))
    return saida


def arquivos(sub, padrao="*.py", suite=None):
    vistos = {}
    for pasta in pastas(sub, suite):
        for caminho in glob.glob(os.path.join(pasta, padrao)):
            nome = os.path.basename(caminho)
            if nome in vistos:
                raise ComponenteDuplicado(
                    u"%s existe em dois lugares: %s e %s"
                    % (nome, vistos[nome], caminho))
            vistos[nome] = caminho
    return [vistos[n] for n in sorted(vistos)]


def nomes(sub="app", suite=None):
    vistos = {}
    for pasta in pastas(sub, suite):
        for nome in os.listdir(pasta):
            caminho = os.path.join(pasta, nome)
            if not os.path.isfile(caminho):
                continue
            if nome in vistos:
                raise ComponenteDuplicado(
                    u"%s existe em dois lugares: %s e %s"
                    % (nome, vistos[nome], caminho))
            vistos[nome] = caminho
    return sorted(vistos)


def fonte(relativo, suite=None):
    if os.path.isabs(relativo):
        return relativo
    suite = suite or raiz_da_suite()
    rel = os.path.normpath(relativo.replace("\\", "/"))
    for raiz in [suite] + [p for p, _ in componentes(suite)] + [os.path.dirname(p) for p in _EXTRAS.get(os.path.normcase(os.path.abspath(suite)), ())]:
        caminho = os.path.join(raiz, rel)
        if os.path.exists(caminho):
            return caminho
    partes = rel.split(os.sep, 1)
    if len(partes) == 2 and partes[0] == "app":
        solto = os.path.join(_pasta_de(suite, "app"), partes[1])
        if os.path.exists(solto):
            return solto
    return os.path.join(suite, rel)


def ler(relativo, suite=None):
    with io.open(fonte(relativo, suite), encoding="utf-8") as f:
        return f.read()


def ler_todos(relativo, suite=None):
    suite = suite or raiz_da_suite()
    partes = []
    for raiz in [suite] + [p for p, _ in componentes(suite)] + [os.path.dirname(p) for p in _EXTRAS.get(os.path.normcase(os.path.abspath(suite)), ())]:
        caminho = os.path.join(raiz, relativo)
        if os.path.isfile(caminho):
            with io.open(caminho, encoding="utf-8", errors="replace") as f:
                partes.append(f.read())
    return u"\n".join(partes)


PASTA_DA_OFICINA = "oficina"


class OficinaIncompleta(Exception):
    pass


def oficina(nome, de):
    pasta = os.path.join(os.path.dirname(os.path.abspath(de)), PASTA_DA_OFICINA)
    if not os.path.isdir(pasta):
        return None
    caminho = os.path.join(pasta, nome + ".py")
    if not os.path.isfile(caminho):
        raise OficinaIncompleta(
            u"a arvore e de engenharia (a pasta %s existe), e o modulo %s nao: "
            u"a checagem que ele faria nao pode pular calada" % (pasta, nome))
    import importlib.util
    spec = importlib.util.spec_from_file_location("radai_oficina_" + nome,
                                                  caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def arvore_de_engenharia(de):
    return os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(de)),
                                      PASTA_DA_OFICINA))


def pulado(o_que):
    sys.stdout.write(u"  PULADO  %s: arvore publica -- as checagens que amarram "
                     u"documento a codigo, ou que dependem da maquina de quem "
                     u"publica, ficam fora dela\n" % o_que)
    sys.stdout.flush()


def caminho_python(suite=None):
    return os.pathsep.join(pastas("app", suite) + pastas("tools", suite))


def ambiente(suite=None):
    env = dict(os.environ)
    atual = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = caminho_python(suite) + (
        os.pathsep + atual if atual else "")
    return env


def dono(relativo, suite=None):
    caminho = os.path.normcase(os.path.abspath(fonte(relativo, suite)))
    suite = suite or raiz_da_suite()
    for pasta, dados in componentes(suite):
        if caminho.startswith(os.path.normcase(os.path.abspath(pasta)) + os.sep):
            return dados.get("nome")
    return "SUITE"


def rodar(bateria, suite=None):
    nome = os.path.basename(bateria)
    caminho = fonte("tools/" + nome, suite)
    if not os.path.isfile(caminho):
        print(u"ERRO: a bateria %s nao existe em nenhum componente." % nome)
        return 2
    raiz = os.path.dirname(os.path.dirname(caminho))
    sys.stdout.flush()
    return subprocess.call([sys.executable, caminho], cwd=raiz,
                           env=ambiente(suite))


def verificar(pasta, suite=None):
    dados = _ler_marca(pasta)
    if dados is None:
        print(u"ERRO: %s nao tem %s desta suite." % (pasta, MARCA))
        return 2
    falhas = []
    for bateria in dados.get("baterias", []):
        print(u"\n=== %s / %s" % (dados.get("nome"), bateria))
        caminho = os.path.join(pasta, "tools", bateria)
        sys.stdout.flush()
        rc = subprocess.call([sys.executable, caminho], cwd=pasta,
                             env=ambiente(suite))
        if rc != 0:
            falhas.append(u"%s (codigo %s)" % (bateria, rc))
    print(u"\n=== %s: %d baterias, %d com falha"
          % (dados.get("nome"), len(dados.get("baterias", [])), len(falhas)))
    for f in falhas:
        print(u"  FALHOU: " + f)
    return 1 if falhas else 0


def ligar(suite=None):
    destino = os.path.join(sysconfig.get_paths()["purelib"], NOME_DO_PTH)
    linhas = pastas_base("app", suite) + pastas_base("tools", suite)
    with io.open(destino, "w", encoding="utf-8") as f:
        f.write(u"\n".join(linhas) + u"\n")
    return destino, linhas


def ligar_caminho(suite=None, extras=()):
    suite = suite or raiz_da_suite()
    chave = os.path.normcase(os.path.abspath(suite))
    novos = list(_EXTRAS.get(chave, ()))
    for pasta in extras:
        pasta = os.path.abspath(pasta)
        if not os.path.isdir(pasta):
            raise ValueError("pasta extra do plugin ausente: %s" % pasta)
        if pasta not in novos:
            novos.append(pasta)
    _EXTRAS[chave] = tuple(novos)
    for pasta in list(sys.path):
        dados = _ler_marca(os.path.dirname(os.path.abspath(pasta)))
        if dados and dados.get("nome") in COMPONENTES_FORA_DA_BASE:
            sys.path.remove(pasta)
    arquivos("app", suite=suite)
    for p in reversed(pastas("app", suite)):
        if p not in sys.path:
            sys.path.insert(0, p)


MANIFESTO_DA_MONTAGEM = "_montado.json"


def montar_app_limpo(destino, suite=None):
    if not os.path.isdir(destino):
        os.makedirs(destino)
    manifesto = os.path.join(destino, MANIFESTO_DA_MONTAGEM)
    antes = []
    if os.path.isfile(manifesto):
        with io.open(manifesto, encoding="utf-8") as f:
            antes = json.load(f)
    agora = sorted(montar_app(destino, suite))
    for rel in antes:
        if rel not in agora and os.path.isfile(os.path.join(destino, rel)):
            os.remove(os.path.join(destino, rel))
    with io.open(manifesto, "w", encoding="utf-8") as f:
        json.dump(agora, f, ensure_ascii=False, indent=0)
    return agora


def nao_ignorados(pasta):
    try:
        r = subprocess.run(["git", "-C", pasta, "ls-files", "-co",
                            "--exclude-standard", "-z"],
                           capture_output=True, timeout=120)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return set(os.path.normcase(os.path.normpath(rel))
               for rel in r.stdout.decode("utf-8", "replace").split("\0")
               if rel)


def montar_app(destino, suite=None):
    copiados = {}
    for pasta in pastas_base("app", suite):
        # GUARDA: o que o .gitignore da pasta ignora e estado de execucao (config, registro, modelos) e nao entra na montagem.
        permitidos = nao_ignorados(pasta)
        for atual, dirs, nomes in os.walk(pasta):
            dirs[:] = [d for d in dirs if d not in IGNORAR]
            for nome in nomes:
                origem = os.path.join(atual, nome)
                rel = os.path.relpath(origem, pasta)
                chave = os.path.normcase(rel)
                if permitidos is not None and chave not in permitidos:
                    continue
                if chave in copiados:
                    raise ComponenteDuplicado(
                        u"app/%s existe em dois lugares: %s e %s"
                        % (rel, copiados[chave], origem))
                copiados[chave] = origem
                alvo = os.path.join(destino, rel)
                pasta_alvo = os.path.dirname(alvo)
                if not os.path.isdir(pasta_alvo):
                    os.makedirs(pasta_alvo)
                shutil.copy2(origem, alvo)
    return copiados


def _donos_dos_modulos(suite=None):
    donos = {}
    for caminho in arquivos("app", "*.py", suite):
        nome = os.path.basename(caminho)[:-3]
        donos[nome] = (dono("app/" + nome + ".py", suite), caminho)
    return donos


def contratos(suite=None):
    import ast
    donos = _donos_dos_modulos(suite)
    usos = {}
    for modulo, (meu, caminho) in sorted(donos.items()):
        with io.open(caminho, encoding="utf-8") as f:
            arvore = ast.parse(f.read())
        apelidos = {}
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for a in no.names:
                    raiz = a.name.split(".")[0]
                    if raiz in donos:
                        apelidos[a.asname or raiz] = raiz
            elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
                raiz = no.module.split(".")[0]
                if raiz in donos and donos[raiz][0] != meu:
                    alvo = usos.setdefault(meu, {}).setdefault(
                        donos[raiz][0], {}).setdefault(raiz, set())
                    alvo.update(a.name for a in no.names)
        for no in ast.walk(arvore):
            if (isinstance(no, ast.Attribute)
                    and isinstance(no.value, ast.Name)
                    and no.value.id in apelidos):
                raiz = apelidos[no.value.id]
                if donos[raiz][0] != meu:
                    usos.setdefault(meu, {}).setdefault(
                        donos[raiz][0], {}).setdefault(raiz, set()).add(no.attr)
        for apelido, raiz in apelidos.items():
            if donos[raiz][0] != meu:
                usos.setdefault(meu, {}).setdefault(
                    donos[raiz][0], {}).setdefault(raiz, set())
    return usos


def imprimir_contratos(usos):
    for consumidor in sorted(usos):
        for fornecedor in sorted(usos[consumidor]):
            print(u"%s usa %s:" % (consumidor, fornecedor))
            for modulo in sorted(usos[consumidor][fornecedor]):
                nomes = sorted(usos[consumidor][fornecedor][modulo])
                print(u"  %s: %s" % (modulo, u", ".join(nomes) or u"(o módulo)"))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--contratos"]:
        imprimir_contratos(contratos())
        return 0
    if argv[:1] == ["--rodar"] and len(argv) == 2:
        return rodar(argv[1])
    if argv[:1] == ["--verificar"] and len(argv) == 2:
        return verificar(os.path.abspath(argv[1]))
    if argv[:1] == ["--montar"] and len(argv) == 2:
        feitos = montar_app_limpo(os.path.abspath(argv[1]))
        print(u"montado: %d arquivo(s) em %s" % (len(feitos), argv[1]))
        return 0
    if argv == ["--pythonpath"]:
        print(caminho_python())
        return 0
    if argv == ["--ligar"]:
        destino, linhas = ligar()
        print(u"gravado: %s" % destino)
        for l in linhas:
            print(u"  " + l)
        return 0
    if argv == ["--listar"]:
        print(u"SUITE  %s" % raiz_da_suite())
        for pasta, dados in componentes():
            print(u"%-6s %s" % (dados.get("nome"), pasta))
        return 0
    print(u"uso: _componentes.py --listar | --contratos | --ligar | "
          u"--pythonpath | --rodar <test_x.py> | --verificar <pasta>")
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
