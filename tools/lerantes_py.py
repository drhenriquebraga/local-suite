# -*- coding: utf-8 -*-
import ast, io, os, sys
sys.stdout.reconfigure(encoding="utf-8")


class _Escopo(ast.NodeVisitor):
    def __init__(self):
        self.liga = {}
        self.le = {}
        self.livres = set()

    def _ligar(self, nome, linha):
        if nome not in self.liga or self.liga[nome] > linha:
            self.liga[nome] = linha

    def _ler(self, nome, linha):
        if nome not in self.le or self.le[nome] > linha:
            self.le[nome] = linha

    def visit_FunctionDef(self, n):
        self._ligar(n.name, n.lineno)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, n):
        pass

    def visit_ClassDef(self, n):
        self._ligar(n.name, n.lineno)

    def visit_ListComp(self, n):
        pass

    visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_ListComp

    def visit_Global(self, n):
        self.livres.update(n.names)

    def visit_Nonlocal(self, n):
        self.livres.update(n.names)

    def visit_Import(self, n):
        for a in n.names:
            self._ligar((a.asname or a.name).split(".")[0], n.lineno)

    def visit_ImportFrom(self, n):
        for a in n.names:
            self._ligar(a.asname or a.name, n.lineno)

    def visit_Name(self, n):
        if isinstance(n.ctx, ast.Store):
            self._ligar(n.id, n.lineno)
        elif isinstance(n.ctx, ast.Load):
            self._ler(n.id, n.lineno)
        self.generic_visit(n)

    def visit_ExceptHandler(self, n):
        if n.name:
            self._ligar(n.name, n.lineno)
        self.generic_visit(n)


def achados(caminho):
    fonte = io.open(caminho, encoding="utf-8", errors="replace").read()
    try:
        arv = ast.parse(fonte)
    except SyntaxError as e:
        return [(e.lineno or 0, u"(sintaxe) %s" % e.msg)]
    fora = []
    for n in ast.walk(arv):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        e = _Escopo()
        for c in n.body:
            e.visit(c)
        params = set()
        a = n.args
        for p in (list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)):
            params.add(p.arg)
        if a.vararg:
            params.add(a.vararg.arg)
        if a.kwarg:
            params.add(a.kwarg.arg)
        for nome, lin in e.le.items():
            if nome in params or nome in e.livres:
                continue
            if nome not in e.liga:
                continue
            if lin < e.liga[nome]:
                fora.append((lin, u"%s (lido na %d, criado na %d, em `%s`)"
                             % (nome, lin, e.liga[nome], n.name)))
    return fora



def varrer(bases=("app", "build", "tools", "installer", "packager")):
    import os
    fora = []
    for base in bases:
        for r, _d, fs in os.walk(base):
            for f in fs:
                if f.endswith(".py"):
                    c = os.path.join(r, f)
                    for lin, txt in achados(c):
                        fora.append((c.replace("\\", "/"), lin, txt))
    return fora


if __name__ == "__main__":
    _r = varrer()
    for c, _l, t in _r:
        print(u"  %-34s %s" % (c, t))
    print(u"\nACHADOS: %d" % len(_r))
