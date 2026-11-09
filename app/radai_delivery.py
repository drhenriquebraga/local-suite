# -*- coding: utf-8 -*-
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = "entrega.txt"

_LIDO = None


def _candidatos():
    return (os.path.join(HERE, ARQUIVO),
            os.path.join(os.path.dirname(HERE), ARQUIVO))


def _ler_arquivo(caminho):
    campos = {}
    with io.open(caminho, encoding="utf-8-sig", errors="replace") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            campos[chave.strip().upper()] = valor.strip()
    return campos


def carimbo(recarregar=False):
    global _LIDO
    if _LIDO is not None and not recarregar:
        return _LIDO
    fora = {"projeto": u"", "versao": u"", "data": u"", "build": u"",
            "origem": u""}
    for c in _candidatos():
        try:
            if not os.path.isfile(c):
                continue
            campos = _ler_arquivo(c)
        except Exception:
            continue
        if not campos.get("PROJETO") and not campos.get("VERSAO"):
            continue
        fora = {"projeto": campos.get("PROJETO", u""),
                "versao": campos.get("VERSAO", u""),
                "data": campos.get("DATA", u""),
                "build": campos.get("BUILD", u""),
                "origem": c}
        break
    _LIDO = fora
    return fora


def e_repositorio():
    c = carimbo()
    if not c["origem"]:
        return False
    return os.path.isdir(os.path.join(os.path.dirname(c["origem"]), ".git"))


def rotulo():
    c = carimbo()
    if not c["versao"]:
        return u""
    partes = [u"%s v%s" % (c["projeto"] or u"AUTO_CONTORNO", c["versao"])]
    if c["build"]:
        partes.append(u"build %s" % c["build"])
    elif e_repositorio():
        partes.append(u"repositório (sem build)")
    elif c["data"]:
        partes.append(c["data"])
    return u" · ".join(partes)


def gerar(projeto, versao, data, build=u"", produto=u""):
    linhas = [u"# Identidade deste build. GERADO no empacotamento.",
              u"# Nao editar a mao: o que estiver aqui e o que a tela mostra",
              u"# e o que o campo vai relatar quando algo sair diferente.",
              u""]
    if produto:
        linhas.append(u"PRODUTO=%s" % produto)
    linhas += [u"PROJETO=%s" % projeto,
              u"VERSAO=%s" % versao,
              u"DATA=%s" % data]
    if build:
        linhas.append(u"BUILD=%s" % build)
    return u"\n".join(linhas) + u"\n"
