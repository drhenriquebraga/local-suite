# -*- coding: utf-8 -*-
import ast
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_laco_')

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "app")

_ok = 0
_falhou = 0
_falhas = []

PESADO = {
    "varrer": u"abre o cabecalho de cada arquivo da pasta",
    "series_contornadas": u"idem, e ainda procura RTSTRUCT",
    "load_sitk": u"le a serie inteira para a memoria",
    "abrir_serie": u"idem",
    "nuvem_da_serie": u"constroi a malha de superficie",
    "contornar_no_clique": u"roda o nnInteractive",
    "converter": u"reescreve a serie inteira em disco",
    "previa": u"aplica a receita e desenha o corte",
    "projetar": u"MIP sobre o volume",
    "registrar_aceite": u"grava o aceite em disco",
    "fundir": u"o ciclo de fusao elastica: 75 s medidos",
}

ISENTAS = {("radai_panel.py", "_api_salvar")}


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
        print(u"  FALHA  %s  %s"
              % (rotulo, str(detalhe).replace("\n", " | ")[:170]))


def _rotas_async(arv):
    for no in ast.walk(arv):
        if not isinstance(no, ast.AsyncFunctionDef):
            continue
        if any("app" in ast.dump(d) for d in no.decorator_list):
            yield no


def _chamadas(no):
    aninhadas = set()
    for c in ast.walk(no):
        if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.Lambda)) and c is not no:
            for d in ast.walk(c):
                aninhadas.add(id(d))
    for c in ast.walk(no):
        if not isinstance(c, ast.Call) or id(c) in aninhadas:
            continue
        if isinstance(c.func, ast.Name):
            yield c.func.id, c
        elif isinstance(c.func, ast.Attribute):
            yield c.func.attr, c


def _protegida(no, alvo):
    for c in ast.walk(no):
        if not isinstance(c, ast.Call):
            continue
        nome = (c.func.attr if isinstance(c.func, ast.Attribute)
                else getattr(c.func, "id", ""))
        if nome != "no_threadpool":
            continue
        if alvo in ast.dump(c):
            return True
    return False


def teste_nenhuma_rota_trabalha_no_laco():
    secao(u"nenhuma rota async trabalha dentro do laco de eventos")
    arquivos = sorted(n for n in _componentes.nomes("app") if n.endswith(".py"))
    checar(u"ha modulos para olhar", len(arquivos) > 10, len(arquivos))

    referidas = 0
    culpadas = []
    for nome in arquivos:
        try:
            fonte = io.open(_componentes.fonte("app/" + nome), encoding="utf-8").read()
            arv = ast.parse(fonte)
        except Exception:
            continue
        for no in _rotas_async(arv):
            dump = ast.dump(no)
            for alvo in PESADO:
                if alvo not in dump:
                    continue
                referidas += 1
            for alvo, _c in _chamadas(no):
                if alvo not in PESADO:
                    continue
                if (nome, no.name) in ISENTAS:
                    continue
                if not _protegida(no, alvo):
                    culpadas.append((nome, no.name, alvo))

    checar(u"as rotas referem trabalho pesado (a lista nao envelheceu)",
           referidas > 0,
           u"nenhum nome de `PESADO` aparece em rota async — ou a lista "
           u"envelheceu, ou as rotas mudaram de nome")
    checar(u"e TODA chamada passa pelo threadpool", not culpadas,
           u"; ".join(u"%s %s -> %s() [%s]"
                      % (a, f, al, PESADO.get(al, u""))
                      for a, f, al in culpadas[:4]))


def teste_a_checagem_sabe_reprovar():
    secao(u"a checagem ainda sabe reprovar")
    ISCA = (
        "app = 1\n"
        "@app.post('/x')\n"
        "async def _falsa(request):\n"
        "    c = await request.json()\n"
        "    return load_sitk(c['p'])\n")
    arv = ast.parse(ISCA)
    pegou = False
    for no in _rotas_async(arv):
        for alvo, _c in _chamadas(no):
            if alvo in PESADO and not _protegida(no, alvo):
                pegou = True
    checar(u"rota que trabalha no laco e' pega", pegou)

    BOA = (
        "app = 1\n"
        "@app.post('/x')\n"
        "async def _boa(request):\n"
        "    c = await request.json()\n"
        "    return await radai_web.no_threadpool(load_sitk, c['p'])\n")
    arv2 = ast.parse(BOA)
    acusou = False
    for no in _rotas_async(arv2):
        for alvo, _c in _chamadas(no):
            if alvo in PESADO and not _protegida(no, alvo):
                acusou = True
    checar(u"e a protegida NAO e' acusada", not acusou,
           u"guarda que acusa o certo ensina a ignora-la")

    MEIA = (
        "app = 1\n"
        "@app.post('/x')\n"
        "async def _meia(request):\n"
        "    c = await request.json()\n"
        "    a = await radai_web.no_threadpool(load_sitk, c['p'])\n"
        "    return varrer(c['q'])\n")
    arv3 = ast.parse(MEIA)
    faltou = []
    for no in _rotas_async(arv3):
        for alvo, _c in _chamadas(no):
            if alvo in PESADO and not _protegida(no, alvo):
                faltou.append(alvo)
    checar(u"e pega a segunda chamada de uma rota meio consertada",
           faltou == ["varrer"], faltou)


def teste_todo_modulo_compila():
    secao(u"todo modulo de app compila (nao so' faz parse)")
    ruins = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        p = _componentes.fonte("app/" + nome)
        try:
            compile(io.open(p, encoding="utf-8").read(), p, "exec")
        except SyntaxError as e:
            ruins.append(u"%s:%s %s" % (nome, e.lineno, e.msg))
    checar(u"nenhum modulo com erro de compilacao", not ruins,
           u"; ".join(ruins[:3]))

    frouxo = True
    try:
        ast.parse("async def f():\n pass\ndef g():\n await f()\n")
    except SyntaxError:
        frouxo = False
    checar(u"e `ast.parse` sozinho NAO pegaria isto", frouxo,
           u"se o parse passou a pegar, esta checagem pode simplificar")


def teste_o_helper_mora_num_lugar_so():
    secao(u"o helper mora num lugar so")
    p = _componentes.fonte("app/radai_web.py")
    checar(u"radai_web existe", os.path.isfile(p))
    if not os.path.isfile(p):
        return
    t = io.open(p, encoding="utf-8").read()
    checar(u"e traz o `no_threadpool`", u"def no_threadpool(" in t)
    checar(u"e o GUARDA: explica POR QUE ele existe",
           any(u"GUARDA:" in l and u"threadpool" in l for l in t.splitlines())
           and (u"laco" in t.lower() or u"laço" in t.lower()))
    arv = ast.parse(t)
    topo = [n for n in arv.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    checar(u"e nao importa nada no topo", not topo,
           [getattr(n, "module", "") or "" for n in topo])


def main():
    print(u"=" * 66)
    print(u"test_loop | nenhuma rota trabalha dentro do laco de eventos")
    print(u"=" * 66)
    teste_nenhuma_rota_trabalha_no_laco()
    teste_a_checagem_sabe_reprovar()
    teste_todo_modulo_compila()
    teste_o_helper_mora_num_lugar_so()
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
