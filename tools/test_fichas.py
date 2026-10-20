# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
APP = os.path.join(RAIZ, "app") if os.path.isdir(os.path.join(RAIZ, "app")) \
    else RAIZ
sys.path.insert(0, APP)

OK = 0
FALHOU = []


def secao(t):
    print(u"\n-- %s --" % t)


def checar(rotulo, cond, detalhe=""):
    global OK
    if cond:
        OK += 1
        print(u"  ok     %s" % rotulo)
    else:
        FALHOU.append(rotulo)
        print(u"  FALHA  %s  [%s]" % (rotulo, detalhe))


def teste_a_ficha_vai_e_volta():
    secao(u"a ficha guarda e devolve, e vence")
    import radai_fichas as F
    dados = {"series": [{"pasta": "C:\\x\\y", "uid": "1.2.3"}]}
    f = F.guardar(dados)
    checar(u"a ficha é curta e não leva o caminho",
           isinstance(f, str) and 8 <= len(f) <= 16 and "\\" not in f
           and "1.2.3" not in f,
           f)
    checar(u"ler devolve os mesmos dados", F.ler(f) == dados)
    checar(u"ficha desconhecida devolve None",
           F.ler("naoexiste") is None and F.ler("") is None and F.ler(None) is None)
    velho = F.VALIDADE_S
    try:
        F.VALIDADE_S = -1
        checar(u"a ficha vencida devolve None", F.ler(f) is None)
    finally:
        F.VALIDADE_S = velho
    fs = [F.guardar(i) for i in range(F.MAXIMO + 10)]
    checar(u"o guardado tem teto", len(F._FICHAS) <= F.MAXIMO, str(len(F._FICHAS)))
    checar(u"a mais recente continua lá", F.ler(fs[-1]) == F.MAXIMO + 9)
    checar(u"duas fichas nunca são iguais", len(set(fs)) == len(fs))


def main():
    print(u"=" * 64)
    print(u"test_fichas | a passagem entre telas sem caminho na URL")
    print(u"=" * 64)
    for t in (teste_a_ficha_vai_e_volta,):
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    print()
    if FALHOU:
        print(u"FALHOU: %d de %d checagens" % (len(FALHOU), OK + len(FALHOU)))
        for f in FALHOU:
            print(u"  - %s" % f)
        return 1
    print(u"OK: %d checagens, todas passaram" % OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
