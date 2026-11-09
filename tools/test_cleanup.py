# -*- coding: utf-8 -*-
import ast
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import _cleanup

VERBOSO = "-v" in sys.argv
_RESULTADOS = []
PREFIXO_BASE = "clupteste_%d_" % os.getpid()
_APAGADORES = ("apagar_arvore", "rmtree")


def checar(nome, condicao, detalhe=""):
    ok = bool(condicao)
    _RESULTADOS.append((nome, ok, detalhe))
    if VERBOSO or not ok:
        print(u"  %s  %s%s" % (u"OK   " if ok else u"FALHA", nome,
                               (u"  [%s]" % detalhe) if detalhe else u""))
    return ok


def secao(t):
    print(u"\n-- %s %s" % (t, u"-" * max(0, 60 - len(t))))


ADOTAR_ANTIGO = u'''
def adotar_antigo(prefixo):
    import time
    inicio = time.time()

    def _varrer():
        base = tempfile.gettempdir()
        try:
            nomes = os.listdir(base)
        except OSError:
            return
        for x in nomes:
            if not x.startswith(prefixo):
                continue
            d = os.path.join(base, x)
            try:
                if os.path.isdir(d) and os.path.getctime(d) >= inicio - 1:
                    shutil.rmtree(d, ignore_errors=True)
            except OSError:
                pass

    atexit.register(_varrer)
'''

FILHO = u'''
import atexit, json, os, shutil, subprocess, sys, tempfile, time
cfg = json.loads(sys.argv[1])
sys.path.insert(0, cfg["tools"])
import _cleanup
isca = cfg.get("isca") or ""
adotar = _cleanup.adotar_prefixo
if isca == "antigo":
    exec(cfg["antigo"])
    adotar = adotar_antigo
elif isca == "sem_registro":
    _cleanup._instalar_registro_de_mkdtemp = lambda: None
elif isca == "sem_cadastro":
    _cleanup._outras_execucoes = lambda bases: []
elif isca == "tudo_vivo":
    _cleanup._execucao_viva = lambda reg: True
adotar(cfg["prefixo"])
print("pronto", flush=True)
for linha in sys.stdin:
    cmd = linha.strip()
    if cmd == "criar":
        print(tempfile.mkdtemp(prefix=cfg["prefixo"] + "p_"), flush=True)
    elif cmd == "neto":
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys, tempfile; print(tempfile.mkdtemp(prefix=sys.argv[1]))",
             cfg["prefixo"] + "n_"],
            stdout=subprocess.PIPE, universal_newlines=True)
        print(r.stdout.strip(), flush=True)
    elif cmd == "cadastro":
        print(json.dumps(_cleanup._ESTADO.get("registros") or []), flush=True)
    elif cmd == "sair":
        break
'''


class Execucao(object):

    def __init__(self, prefixo, isca=None):
        cfg = {"tools": AQUI, "prefixo": prefixo, "isca": isca,
               "antigo": ADOTAR_ANTIGO}
        self.p = subprocess.Popen(
            [sys.executable, "-c", FILHO, json.dumps(cfg)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            universal_newlines=True, bufsize=1)
        self.pronto = self.p.stdout.readline().strip() == "pronto"

    def pedir(self, cmd):
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()
        return self.p.stdout.readline().strip()

    def sair(self):
        try:
            self.p.stdin.write("sair\n")
            self.p.stdin.flush()
        except OSError:
            pass
        try:
            self.p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
        return self.p.returncode


def _existe(d):
    return bool(d) and os.path.isdir(d)


def teste_duas_execucoes_do_mesmo_prefixo():
    secao(u"duas execucoes do mesmo prefixo: cada uma leva so o que e dela")
    pref = PREFIXO_BASE + "a_"
    A = Execucao(pref)
    checar(u"a execucao A subiu e adotou", A.pronto)
    a1 = A.pedir("criar")
    a2 = A.pedir("neto")
    checar(u"A criou uma pasta sua e o neto dela outra",
           _existe(a1) and _existe(a2), "%s | %s" % (a1, a2))
    time.sleep(1.6)
    B = Execucao(pref)
    checar(u"a execucao B subiu e adotou o MESMO prefixo", B.pronto)
    b1 = B.pedir("criar")
    b2 = B.pedir("neto")
    checar(u"B criou uma pasta sua e o neto dela outra",
           _existe(b1) and _existe(b2), "%s | %s" % (b1, b2))
    a3 = A.pedir("criar")
    cad_a = json.loads(A.pedir("cadastro") or "[]")
    cad_b = json.loads(B.pedir("cadastro") or "[]")
    checar(u"as duas se inscreveram no cadastro",
           cad_a and cad_b and all(os.path.isfile(c) for c in cad_a + cad_b),
           "%s | %s" % (cad_a, cad_b))
    A.sair()
    checar(u"A terminou: a pasta que o mkdtemp de A criou saiu", not _existe(a1))
    checar(u"  e a do neto de A, nascida antes de B, tambem", not _existe(a2))
    checar(u"  e a de A criada DEPOIS de B comecar tambem (e de A pelo "
           u"registro)", not _existe(a3))
    checar(u"  e o registro de A saiu do cadastro",
           not any(os.path.isfile(c) for c in cad_a))
    checar(u"B CONTINUA RODANDO: a pasta do mkdtemp de B ficou", _existe(b1),
           b1)
    checar(u"  e a do neto de B (que B nao registrou) tambem ficou",
           _existe(b2), b2)
    B.sair()
    checar(u"B terminou: as duas pastas de B sairam",
           not _existe(b1) and not _existe(b2))
    checar(u"  e o registro de B saiu do cadastro",
           not any(os.path.isfile(c) for c in cad_b))


def teste_prefixo_dentro_de_prefixo():
    secao(u"um prefixo que cobre o de OUTRA bateria")
    curto = PREFIXO_BASE + "c_"
    longo = curto + "longo_"
    A = Execucao(curto)
    time.sleep(1.2)
    B = Execucao(longo)
    checar(u"as duas subiram", A.pronto and B.pronto)
    b2 = B.pedir("neto")
    A.sair()
    checar(u"a execucao do prefixo curto terminou e NAO levou a pasta do "
           u"neto da outra bateria, viva", _existe(b2), b2)
    B.sair()
    checar(u"  e a dona a levou ao terminar", not _existe(b2))


def teste_iscas():
    secao(u"iscas: sem cada peca, o cenario reprova")
    pref = PREFIXO_BASE + "i1_"
    A = Execucao(pref, isca="antigo")
    time.sleep(1.2)
    B = Execucao(pref, isca="antigo")
    b1 = B.pedir("criar")
    A.sair()
    checar(u"isca: com o corte SO por horario (o codigo de antes), a "
           u"execucao que sai primeiro apaga a pasta da viva",
           not _existe(b1), b1)
    B.sair()

    pref = PREFIXO_BASE + "i2_"
    A = Execucao(pref, isca="sem_cadastro")
    time.sleep(1.2)
    B = Execucao(pref)
    b2 = B.pedir("neto")
    A.sair()
    checar(u"isca: sem consultar o cadastro, a pasta do neto da viva some",
           not _existe(b2), b2)
    B.sair()

    pref = PREFIXO_BASE + "i3_"
    A = Execucao(pref, isca="sem_registro")
    time.sleep(1.2)
    B = Execucao(pref)
    a3 = A.pedir("criar")
    A.sair()
    checar(u"isca: sem o registro do mkdtemp, A nao leva a propria pasta "
           u"criada depois de B", _existe(a3), a3)
    B.sair()
    checar(u"  e a ultima a terminar a leva (nada sobra)", not _existe(a3), a3)


def _pid_morto():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p, p.pid


def teste_registro_de_execucao_morta():
    secao(u"registro de execucao que morreu nao segura pasta")
    pref = PREFIXO_BASE + "m_"
    base = tempfile.gettempdir()
    pasta = os.path.join(base, _cleanup.PASTA_DO_CADASTRO)
    os.makedirs(pasta, exist_ok=True)
    proc, pid = _pid_morto()
    falso = os.path.join(pasta, "%d_1.json" % pid)
    with open(falso, "w", encoding="utf-8") as fh:
        json.dump({"pid": pid, "criado": None, "desde": 0.0,
                   "adotados": [[pref, 0.0]]}, fh)
    A = Execucao(pref)
    c = A.pedir("neto")
    A.sair()
    checar(u"a execucao viva levou a pasta do neto, apesar do registro de "
           u"uma execucao morta que cobria o prefixo", not _existe(c), c)
    checar(u"  e o registro da morta saiu do cadastro",
           not os.path.isfile(falso))
    proc2, pid2 = _pid_morto()
    falso2 = os.path.join(pasta, "%d_1.json" % pid2)
    with open(falso2, "w", encoding="utf-8") as fh:
        json.dump({"pid": pid2, "criado": None, "desde": 0.0,
                   "adotados": [[pref, 0.0]]}, fh)
    A = Execucao(pref, isca="tudo_vivo")
    c2 = A.pedir("neto")
    A.sair()
    checar(u"isca: se todo registro valesse como vivo, a pasta ficaria",
           _existe(c2), c2)
    shutil.rmtree(c2, ignore_errors=True)
    try:
        os.remove(falso2)
    except OSError:
        pass
    del proc, proc2


def teste_pid_reaproveitado():
    secao(u"PID reaproveitado nao ressuscita registro velho")
    existe, nasceu = _cleanup._processo(os.getpid())
    checar(u"o proprio processo existe", existe is True)
    if os.name == "nt":
        checar(u"e a hora de nascimento e medida (e recente)",
               nasceu is not None and time.time() - 86400 < nasceu
               <= time.time() + 1, str(nasceu))
    checar(u"registro com o MEU pid e a minha hora de nascimento: vivo",
           _cleanup._execucao_viva({"pid": os.getpid(), "criado": nasceu}))
    if os.name == "nt":
        checar(u"registro com o meu pid e OUTRA hora de nascimento (o PID foi "
               u"reaproveitado): morto",
               not _cleanup._execucao_viva({"pid": os.getpid(),
                                            "criado": 0.0}))
    proc, pid = _pid_morto()
    checar(u"processo que terminou: morto, mesmo com o handle aberto",
           _cleanup._processo(pid)[0] is False)
    del proc


def teste_perguntar_nao_mata():
    secao(u"perguntar se um processo vive nao manda sinal nenhum")
    chamadas = []

    class _OsFalso(object):
        name = "nt"

        def __getattr__(self, n):
            return getattr(os, n)

        @staticmethod
        def kill(*a):
            chamadas.append(a)

    fonte = textwrap.dedent(inspect.getsource(_cleanup._processo))

    def _rodar(src):
        ns = {"os": _OsFalso()}
        exec(compile(src, "<_processo>", "exec"), ns)
        del chamadas[:]
        for pid in (os.getpid(), _pid_morto()[1], 0, "x"):
            ns["_processo"](pid)
        return list(chamadas)

    checar(u"no Windows, `_processo` nunca chega ao `os.kill`",
           _rodar(fonte) == [], str(chamadas))
    isca = fonte.replace(u'if os.name == "nt":', u"if False:", 1)
    checar(u"  (a isca achou o ramo do Windows)", isca != fonte)
    checar(u"isca: sem o ramo do OpenProcess, a pergunta vira sinal",
           bool(_rodar(isca)))


def _predicados(fonte):
    arv = ast.parse(fonte)
    funcs = dict((n.name, n) for n in ast.walk(arv)
                 if isinstance(n, ast.FunctionDef))

    def _chama(fn, nome):
        return fn in funcs and any(
            isinstance(n, ast.Call)
            and (getattr(n.func, "id", None) == nome
                 or getattr(n.func, "attr", None) == nome)
            for n in ast.walk(funcs[fn]))

    ordem = False
    for n in ast.walk(funcs.get("_varrer", ast.Module(body=[]))):
        if not isinstance(n, ast.For):
            continue
        idx_se = [i for i, s in enumerate(n.body) if isinstance(s, ast.If)
                  and any(isinstance(m, ast.Continue) for m in ast.walk(s))
                  and "_pode_ser_de" in ast.dump(s)]
        idx_rm = [i for i, s in enumerate(n.body)
                  if any(isinstance(m, ast.Call)
                         and (getattr(m.func, "id", None) in _APAGADORES
                              or getattr(m.func, "attr", None) in _APAGADORES)
                         for m in ast.walk(s))]
        if idx_se and idx_rm and idx_se[0] < idx_rm[0]:
            ordem = True
    return {
        "getctime": "_varrer" in funcs and "getctime" in ast.dump(
            funcs["_varrer"]),
        "cadastro": _chama("_varrer", "_outras_execucoes")
        and _chama("_varrer", "_pode_ser_de"),
        "inscreve": _chama("adotar_prefixo", "_gravar_no_cadastro"),
        "um_varredor": _chama("adotar_prefixo", "register")
        and "varredor" in (ast.get_source_segment(
            fonte, funcs["adotar_prefixo"]) or u""),
        "ordem": ordem,
    }


def teste_estrutura():
    secao(u"estrutura do _cleanup")
    fonte = open(os.path.join(AQUI, "_cleanup.py"), encoding="utf-8").read()
    p = _predicados(fonte)
    checar(u"o corte por horario continua (getctime; o check_project [21] o "
           u"pede)", p["getctime"])
    checar(u"a varredura consulta o cadastro antes de apagar", p["cadastro"])
    checar(u"adotar inscreve a execucao ANTES de devolver", p["inscreve"])
    checar(u"o varredor e registrado uma vez so", p["um_varredor"])
    checar(u"o apagar (apagar_arvore) vem depois da pergunta ao cadastro, no "
           u"mesmo laco", p["ordem"])
    pergunta = (u"        if _norm(d) not in _MINHAS and \\\n"
                u"                any(_pode_ser_de(r, x, ct) for r in outras):"
                u"\n            continue\n")
    apaga = u"        apagar_arvore(d)\n"
    trocas = (
        (u"sem a peca", "cadastro",
         u"outras = _outras_execucoes(bases) if candidatas else []",
         u"outras = []"),
        (u"sem a peca", "ordem", pergunta, u""),
        (u"o apagar antes da pergunta", "ordem", pergunta + apaga,
         apaga + pergunta),
        (u"o laco sem o apagar", "ordem", pergunta + apaga, pergunta),
        (u"sem a peca", "inscreve", u"        _gravar_no_cadastro()\n",
         u"        pass\n"),
    )
    for rotulo, chave, velho, novo in trocas:
        isca = fonte.replace(velho, novo, 1)
        checar(u"  (a isca de %s, %s, achou o trecho)" % (chave, rotulo),
               isca != fonte)
        checar(u"  isca: %s, «%s» reprova" % (rotulo, chave),
               not _predicados(isca)[chave])


def _limpar_o_que_sobrou():
    base = tempfile.gettempdir()
    try:
        for x in os.listdir(base):
            if x.startswith(PREFIXO_BASE):
                shutil.rmtree(os.path.join(base, x), ignore_errors=True)
    except OSError:
        pass


def main():
    print(u"=" * 68)
    print(u"test_cleanup | a limpeza das baterias so apaga o que e dela")
    print(u"=" * 68)
    try:
        teste_duas_execucoes_do_mesmo_prefixo()
        teste_prefixo_dentro_de_prefixo()
        teste_iscas()
        teste_registro_de_execucao_morta()
        teste_pid_reaproveitado()
        teste_perguntar_nao_mata()
        teste_estrutura()
        carregados = sorted(m for m in sys.modules
                            if m.startswith("radai_") or m == "engine")
        checar(u"a bateria nao carregou modulo do programa (nao alcanca o "
               u"acervo)", not carregados, ", ".join(carregados[:5]))
    finally:
        _limpar_o_que_sobrou()
    falhas = [r for r in _RESULTADOS if not r[1]]
    print(u"\n" + u"=" * 68)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for nome, _ok, det in falhas:
            print(u"  - %s  %s" % (nome, det))
    else:
        print(u"OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print(u"=" * 68)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
