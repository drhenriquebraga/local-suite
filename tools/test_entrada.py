# -*- coding: utf-8 -*-
import ast
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import sysconfig
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_entrada_')

ENTRADAS = ("radai_watcher.py", "radai_lancador.py")
VARIAVEL_PYTHON_DA_ESTACAO = "RADAI_PYTHON_DA_ESTACAO"
ARQUIVO_DO_BUNDLE = "_bundle.txt"
TETO_DO_TOPO_S = 180.0
TETO_DO_ARRANQUE_S = 240.0
TETO_DA_SERIE_S = 240.0
TETO_DA_SAIDA_S = 90.0
ASSINATURA_DO_DEFEITO = u"is not defined"

_RESULTADOS = []


def checar(nome, ok, detalhe=u""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    print(u"  %s  %s%s" % (u"ok   " if ok else u"FALHA", nome,
                           (u"  [%s]" % detalhe) if detalhe and not ok else u""))


def secao(t):
    print(u"\n── %s " % t + u"─" * max(3, 60 - len(t)))


def _instrucoes_do_modulo(corpo):
    for no in corpo or ():
        yield no
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for campo in ("body", "orelse", "finalbody"):
            filhos = getattr(no, campo, None)
            if isinstance(filhos, list):
                for f in _instrucoes_do_modulo(filhos):
                    yield f
        for h in getattr(no, "handlers", None) or ():
            for f in _instrucoes_do_modulo(h.body):
                yield f


def _menciona_o_arquivo(expr, nomes_do_arquivo):
    for no in ast.walk(expr):
        if isinstance(no, ast.Name) and (no.id == "__file__"
                                         or no.id in nomes_do_arquivo):
            return True
    return False


def _insercao_no_caminho(no):
    if not (isinstance(no, ast.Expr) and isinstance(no.value, ast.Call)):
        return None
    f = no.value.func
    if (isinstance(f, ast.Attribute) and f.attr == "insert"
            and isinstance(f.value, ast.Attribute) and f.value.attr == "path"
            and isinstance(f.value.value, ast.Name)
            and f.value.value.id == "sys" and len(no.value.args) == 2):
        return no.value.args[1]
    return None


def problemas_de_ordem(texto, nossos):
    arvore = ast.parse(texto)
    do_modulo = list(_instrucoes_do_modulo(arvore.body))
    ids = set(id(n) for n in do_modulo)
    nomes_do_arquivo = set()
    for n in do_modulo:
        if isinstance(n, ast.Assign) and _menciona_o_arquivo(n.value, nomes_do_arquivo):
            for alvo in n.targets:
                if isinstance(alvo, ast.Name):
                    nomes_do_arquivo.add(alvo.id)
    primeira = None
    for n in do_modulo:
        arg = _insercao_no_caminho(n)
        if arg is not None and _menciona_o_arquivo(arg, nomes_do_arquivo):
            primeira = n.lineno if primeira is None else min(primeira, n.lineno)
    fora = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [a.name.split(".")[0] for a in no.names]
        elif isinstance(no, ast.ImportFrom) and not no.level and no.module:
            nomes = [no.module.split(".")[0]]
        else:
            continue
        nomes = sorted(set(m for m in nomes if m in nossos))
        if not nomes:
            continue
        if primeira is None:
            fora.append(u"linha %d: import %s, e nenhum sys.path.insert da "
                        u"pasta do proprio arquivo no nivel do modulo"
                        % (no.lineno, u", ".join(nomes)))
        elif id(no) in ids and no.lineno < primeira:
            fora.append(u"linha %d: import %s antes do sys.path.insert da "
                        u"linha %d" % (no.lineno, u", ".join(nomes), primeira))
    return fora


def modulos_nossos():
    return set(os.path.splitext(n)[0] for n in _componentes.nomes("app")
               if n.endswith(".py"))


ISCA_DO_VIGIA = u"""
import os
import sys
try:
    import radai_archive as _arq
except Exception:
    pass
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import radai_config
"""

ISCA_DO_LANCADOR = u"""
import os
import sys

def _criado(pid):
    try:
        import radai_pulso
        return radai_pulso._criado_em(pid)
    except Exception:
        return None
"""

ISCA_DE_CAMINHO_FIXO = u"""
import sys
sys.path.insert(0, "C:/programa")
import radai_archive
"""

CERTO = u"""
import os
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import radai_archive as _arq

def f():
    import radai_pulso
    return radai_pulso
"""


def teste_a_ordem_pelo_ast():
    secao(u"nenhum import nosso antes do sys.path.insert, pelo ast")
    nossos = set([u"radai_archive", u"radai_config", u"radai_pulso"])
    checar(u"(isca) o import do radai_archive num try antes do caminho reprova",
           bool(problemas_de_ordem(ISCA_DO_VIGIA, nossos)),
           problemas_de_ordem(ISCA_DO_VIGIA, nossos))
    checar(u"(isca) o lancador sem caminho, so com import dentro de funcao, "
           u"reprova", bool(problemas_de_ordem(ISCA_DO_LANCADOR, nossos)))
    checar(u"(isca) caminho fixo no lugar da pasta do arquivo reprova",
           bool(problemas_de_ordem(ISCA_DE_CAMINHO_FIXO, nossos)))
    checar(u"a ordem certa passa", not problemas_de_ordem(CERTO, nossos),
           problemas_de_ordem(CERTO, nossos))
    nossos = modulos_nossos()
    checar(u"a lista dos modulos nossos sai das sete pastas",
           u"radai_archive" in nossos and u"radai_watcher" in nossos
           and u"engine" in nossos and u"json" not in nossos, len(nossos))
    for nome in ENTRADAS:
        cam = _componentes.fonte("app/" + nome)
        checar(u"%s existe" % nome, os.path.isfile(cam), cam)
        if not os.path.isfile(cam):
            continue
        texto = io.open(cam, encoding="utf-8").read()
        p = problemas_de_ordem(texto, nossos)
        checar(u"%s: nenhum import nosso antes do caminho" % nome, not p,
               u" | ".join(p))


def _pasta_da_bateria():
    base = (os.environ.get("RADAI_TMP") or u"").strip() or None
    if base and not os.path.isdir(base):
        os.makedirs(base)
    return tempfile.mkdtemp(prefix="radai_entrada_", dir=base)


def _site_packages():
    fora = []
    for k in ("purelib", "platlib"):
        p = sysconfig.get_paths().get(k)
        if p and os.path.isdir(p) and p not in fora:
            fora.append(p)
    return fora


def python_da_estacao():
    fixo = (os.environ.get(VARIAVEL_PYTHON_DA_ESTACAO) or u"").strip()
    candidatos = [fixo] if fixo else []
    marca = os.path.join(_componentes.raiz_da_suite(), ARQUIVO_DO_BUNDLE)
    if not fixo and os.path.isfile(marca):
        try:
            linha = io.open(marca, encoding="utf-8-sig").read().strip()
        except Exception:
            linha = u""
        if linha:
            candidatos.append(os.path.join(linha.strip('"'), "python",
                                           "python.exe"))
    for c in candidatos:
        pasta = os.path.dirname(c)
        if os.path.isfile(c) and any(n.endswith("._pth")
                                     for n in os.listdir(pasta)):
            return c
    return None


def interpretes():
    fora = [(u"o Python desta bateria com -I -S",
             [sys.executable, "-I", "-S"], _site_packages(), False)]
    est = python_da_estacao()
    if est:
        fora.append((u"o embeddable da montagem", [est], [], True))
    else:
        print(u"  PULADO: o embeddable da montagem (sem %s nem %s com um "
              u"python.exe ao lado de um ._pth)"
              % (VARIAVEL_PYTHON_DA_ESTACAO, ARQUIVO_DO_BUNDLE))
    return fora


BOOT = u"""
import importlib.util, json, os, runpy, sys
script, saida, modo, extra = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
for p in extra:
    if p not in sys.path:
        sys.path.append(p)
pasta = os.path.normcase(os.path.dirname(os.path.abspath(script)))
def _n(p):
    try:
        return os.path.normcase(os.path.abspath(p or os.getcwd()))
    except Exception:
        return ""
r = {"pasta_no_caminho": any(_n(p) == pasta for p in sys.path), "erro": ""}
sys.argv = [script]
if modo == "main":
    runpy.run_path(script, run_name="__main__")
    sys.exit(0)
try:
    g = runpy.run_path(script, run_name="radai_entrada_topo")
    nome = os.path.basename(script)
    if nome == "radai_watcher.py":
        r["arq"] = "_arq" in g
        r["archive"] = g.get("radai_archive") is not None
        r["painel_erro"] = str(g.get("_PAINEL_ERRO") or "")
    elif nome == "radai_lancador.py":
        r["criado"] = g["_criado"](os.getpid()) is not None
        r["processos"] = len(g["_lista_de_processos"]() or [])
        r["carregando"] = importlib.util.find_spec("radai_carregando") is not None
except BaseException as e:
    r["erro"] = "%s: %s" % (type(e).__name__, str(e)[:300])
with open(saida, "w", encoding="utf-8") as f:
    json.dump(r, f)
os._exit(0)
"""


def ambiente_isolado(base, porta=None, raiz=None):
    amb = dict(os.environ)
    for k in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE"):
        amb.pop(k, None)
    pastas = {}
    for nome in ("localappdata", "tmp", "acervo", "registro", "fila",
                 "tshome"):
        pastas[nome] = os.path.join(base, nome)
        if not os.path.isdir(pastas[nome]):
            os.makedirs(pastas[nome])
    cfg = os.path.join(base, "radai_watcher.config")
    if porta is not None:
        with io.open(cfg, "w", encoding="utf-8") as f:
            f.write(u"ROOT=%s\nDRY_RUN=1\nPORT=%d\nMIN_SLICES=20\nQUIET_MIN=0\n"
                    u"SCAN_EVERY_MIN=1\nMODALITIES=CT\nDAYS_BACK=0\n"
                    % (raiz or u"", int(porta)))
    amb.update({"LOCALAPPDATA": pastas["localappdata"],
                "RADAI_TMP": pastas["tmp"], "TEMP": pastas["tmp"],
                "TMP": pastas["tmp"], "RADAI_TEMP_DO_USUARIO": pastas["tmp"],
                "RADAI_CALIB_DIR": pastas["acervo"],
                "RADAI_REGISTRO_DIR": pastas["registro"],
                "RADAI_FILA_DIR": pastas["fila"],
                "TOTALSEG_HOME_DIR": pastas["tshome"],
                "RADAI_CONFIG": cfg, "RADAI_NOTIFICACAO": "0",
                "RADAI_URL_VERSOES": "0", "PYTHONIOENCODING": "utf-8:replace"})
    amb.pop("RADAI_MOTOR_OCULTO", None)
    return amb, pastas


def montar_programa(base):
    prog = os.path.join(base, "programa")
    _componentes.montar_app_limpo(prog)
    entrega = os.path.join(_componentes.raiz_da_suite(), "entrega.txt")
    if os.path.isfile(entrega):
        shutil.copy2(entrega, os.path.join(prog, "entrega.txt"))
    return prog


def teste_o_topo_como_a_estacao():
    secao(u"o topo dos scripts de entrada com a pasta do script FORA do caminho")
    base = _pasta_da_bateria()
    try:
        try:
            prog = montar_programa(base)
        except Exception as e:
            checar(u"o programa monta das sete pastas", False,
                   u"%s: %s" % (type(e).__name__, e))
            return
        checar(u"o programa monta das sete pastas, num lugar so",
               all(os.path.isfile(os.path.join(prog, n)) for n in ENTRADAS)
               and os.path.isfile(os.path.join(prog, "radai_archive.py")))
        neutra = os.path.join(base, "neutra")
        os.makedirs(neutra)
        amb, _ = ambiente_isolado(os.path.join(base, "isolado"))
        for rotulo, cmd, extra, _direto in interpretes():
            for nome in ENTRADAS:
                saida = os.path.join(base, "topo_%d_%s.json"
                                     % (len(cmd), nome.replace(".py", "")))
                try:
                    p = subprocess.run(
                        cmd + ["-c", BOOT, os.path.join(prog, nome), saida,
                               "topo", json.dumps(extra)],
                        cwd=neutra, env=amb, capture_output=True,
                        timeout=TETO_DO_TOPO_S)
                    resto = (p.stdout + p.stderr).decode("utf-8", "replace")
                except subprocess.TimeoutExpired:
                    resto = u"passou do teto de %d s" % TETO_DO_TOPO_S
                r = {}
                if os.path.isfile(saida):
                    r = json.load(io.open(saida, encoding="utf-8"))
                checar(u"%s, %s: o topo rodou" % (rotulo, nome),
                       bool(r) and not r.get("erro"),
                       (r.get("erro") if r else resto[-400:]))
                checar(u"  (isca do harness) a pasta do script nao estava no "
                       u"caminho antes do script", r.get("pasta_no_caminho")
                       is False, r)
                if nome == "radai_watcher.py":
                    checar(u"  o radai_archive carregou no topo (o _arq existe)",
                           r.get("arq") is True and r.get("archive") is True, r)
                    checar(u"  o painel montou no topo",
                           r.get("painel_erro") == u"", r.get("painel_erro"))
                else:
                    checar(u"  o radai_pulso responde (o PID tem instante de "
                           u"criacao e a lista de processos nao e vazia)",
                           r.get("criado") is True
                           and int(r.get("processos") or 0) > 0, r)
                    checar(u"  o radai_carregando e achado",
                           r.get("carregando") is True, r)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def porta_livre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


_ABRIDOR = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def pedir(porta, rota, corpo=None, teto=10.0):
    dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (porta, rota), data=dados,
        headers={"Content-Type": "application/json"},
        method="GET" if corpo is None else "POST")
    with _ABRIDOR.open(req, timeout=teto) as r:
        return json.loads(r.read().decode("utf-8"))


def _esperar(cond, teto_s, proc=None, passo=0.5):
    limite = time.time() + teto_s
    while time.time() < limite:
        try:
            v = cond()
        except Exception:
            v = None
        if v:
            return v
        if proc is not None and proc.poll() is not None:
            return None
        time.sleep(passo)
    return None


def _fantoma(raiz):
    try:
        from make_test_series import escreve_serie
    except Exception as e:
        return None, None, u"%s: %s" % (type(e).__name__, e)
    pasta = os.path.join(raiz, "PAC_ENTRADA", "CT_FANTOMA")
    quando = datetime.now() - timedelta(days=1)
    uid = escreve_serie(pasta, "PAC_ENTRADA", quando, 30)
    return pasta, uid, u""


def _cauda(caminho, n=1600):
    try:
        with io.open(caminho, encoding="utf-8", errors="replace") as f:
            return f.read()[-n:]
    except Exception:
        return u""


def _o_log_do_vigia(pastas):
    fora = []
    for raiz, _d, nomes in os.walk(pastas["acervo"]):
        for n in nomes:
            if n.endswith(".log") and "vigia" in n.lower():
                fora.append(os.path.join(raiz, n))
    return fora


def _encerrar(proc, porta):
    try:
        pedir(porta, "/api/encerrar", {"modo": "tudo"})
    except Exception:
        pass
    try:
        return proc.wait(timeout=TETO_DA_SAIDA_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=30)
        return None


def teste_o_vigia_de_verdade_com_um_fantoma():
    secao(u"o vigia como script, sem a pasta no caminho: turno, serie, pronta")
    base = _pasta_da_bateria()
    try:
        try:
            prog = montar_programa(base)
        except Exception as e:
            checar(u"o programa monta das sete pastas", False,
                   u"%s: %s" % (type(e).__name__, e))
            return
        for k, (rotulo, cmd, extra, direto) in enumerate(interpretes()):
            casa = os.path.join(base, "e2e_%d" % k)
            raiz = os.path.join(casa, "ROOT")
            os.makedirs(raiz)
            pasta, uid, erro = _fantoma(raiz)
            checar(u"%s: o fantoma foi gravado" % rotulo, bool(uid), erro)
            if not uid:
                continue
            porta = porta_livre()
            amb, pastas = ambiente_isolado(casa, porta, raiz)
            script = os.path.join(prog, "radai_watcher.py")
            if direto:
                comando, cwd = cmd + [script], prog
            else:
                comando = cmd + ["-c", BOOT, script, "-", "main",
                                 json.dumps(extra)]
                cwd = casa
            console = os.path.join(casa, "console.txt")
            with open(console, "wb") as saida:
                proc = subprocess.Popen(comando, cwd=cwd, env=amb,
                                        stdin=subprocess.DEVNULL,
                                        stdout=saida, stderr=subprocess.STDOUT)
            try:
                st = _esperar(lambda: pedir(porta, "/api/status"),
                              TETO_DO_ARRANQUE_S, proc)
                checar(u"%s: o painel respondeu" % rotulo, bool(st),
                       _cauda(console, 600))
                if not st:
                    continue
                r = pedir(porta, "/api/fila/overnight",
                          {"ligado": True, "pausar_servicos": False})
                checar(u"  o card do turno entrou na fila",
                       any(c.get("tipo") == "overnight"
                           for c in (r or {}).get("cards") or []), r)
                r = pedir(porta, "/api/overnight/iniciar", {}, teto=60.0)
                checar(u"  o turno abriu", bool(r and r.get("ok")), r)

                def _card_do_turno():
                    d = pedir(porta, "/api/fila")
                    return [c for c in (d or {}).get("cards") or []
                            if c.get("tipo") == "overnight"]
                cards = _card_do_turno()
                checar(u"  o card do turno fica rodando enquanto o turno "
                       u"esta aberto", bool(cards)
                       and cards[0].get("estado") == "rodando", cards)
                marca = os.path.join(pasta, "_RadAI", "%s.done.json" % uid)
                feito = _esperar(lambda: os.path.isfile(marca),
                                 TETO_DA_SERIE_S, proc)
                falha = os.path.join(pasta, "_RadAI", "%s.fail.json" % uid)
                checar(u"  o vigia achou o fantoma, segmentou (simulacao) e "
                       u"marcou pronta", bool(feito),
                       _cauda(falha, 300) or _cauda(console, 600))
                simulado = [n for n in os.listdir(os.path.join(pasta, "_RadAI"))
                            if n.endswith(".SIMULACAO.txt")] \
                    if os.path.isdir(os.path.join(pasta, "_RadAI")) else []
                checar(u"  e gravou o resultado da simulacao ao lado da serie",
                       bool(simulado) or bool(
                           [n for _r, _d, ns in os.walk(pasta) for n in ns
                            if n.endswith(".SIMULACAO.txt")]))
                checar(u"  nenhuma falha marcada", not os.path.isfile(falha),
                       _cauda(falha, 300))
                r = pedir(porta, "/api/overnight/encerrar", {}, teto=30.0)
                checar(u"  o turno encerrou", bool(r and r.get("ok")), r)
                cards = _card_do_turno()
                checar(u"  e o card do turno saiu da fila", not cards, cards)
            finally:
                rc = _encerrar(proc, porta)
            checar(u"  o motor saiu limpo pelo /api/encerrar", rc == 0,
                   u"rc=%s | %s" % (rc, _cauda(console, 600)))
            textos = _cauda(console, 200000)
            for lg in _o_log_do_vigia(pastas):
                textos += _cauda(lg, 400000)
            checar(u"  nenhum nome indefinido no log nem no console",
                   ASSINATURA_DO_DEFEITO not in textos,
                   [l for l in textos.splitlines()
                    if ASSINATURA_DO_DEFEITO in l][:3])
            uso = os.path.join(pastas["localappdata"], "RADIOTERAPIA_AI",
                               "em_uso.json")
            checar(u"  o em_uso.json saiu com a saida limpa (e ficou na "
                   u"pasta isolada)", not os.path.isfile(uso), uso)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    print(u"=" * 64)
    print(u"test_entrada | os scripts de entrada como a estacao os roda")
    print(u"=" * 64)
    for t in (teste_a_ordem_pelo_ast, teste_o_topo_como_a_estacao,
              teste_o_vigia_de_verdade_com_um_fantoma):
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    falhas = [r for r in _RESULTADOS if not r[1]]
    print()
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for nome, _ok, det in falhas:
            print(u"  - %s  [%s]" % (nome, det))
        return 1
    print(u"OK: %d checagens, todas passaram" % len(_RESULTADOS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
