# -*- coding: utf-8 -*-

import datetime
import os
import subprocess

CABECA = (
    u"# Identidade deste build. GERADO no empacotamento.",
    u"# Nao editar a mao: o que estiver aqui e o que a tela mostra",
    u"# e o que o campo vai relatar quando algo sair diferente.",
    u"",
)


MARCA_DE_ARVORE_SUJA = u"+alterado"


def _arvore_suja(raiz):
    try:
        saida = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(raiz),
            stderr=subprocess.DEVNULL, timeout=30)
        return bool(saida.strip())
    except Exception:
        return False


def _raiz_do_git(pasta):
    try:
        saida = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=str(pasta),
            stderr=subprocess.DEVNULL, timeout=30)
        topo = saida.decode("utf-8", "replace").strip()
        return bool(topo) and os.path.samefile(topo, str(pasta))
    except Exception:
        return False


def componentes_sujos(raiz):
    ferramentas = os.path.join(str(raiz), "tools")
    if not os.path.isfile(os.path.join(ferramentas, "_componentes.py")):
        return []
    try:
        import sys
        if ferramentas not in sys.path:
            sys.path.insert(0, ferramentas)
        import _componentes
        pastas = [p for p, _d in _componentes.componentes(str(raiz))]
    except Exception:
        return []
    sujos = []
    for pasta in pastas:
        # GUARDA: app baixado da trava nao tem Git proprio; a arvore dele ja foi conferida pela trava.
        if not _raiz_do_git(pasta):
            continue
        try:
            saida = subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=str(pasta), stderr=subprocess.DEVNULL, timeout=30)
        except Exception:
            continue
        if saida.strip():
            sujos.append(os.path.basename(os.path.normpath(pasta)))
    return sujos


def _commit_curto(raiz):
    try:
        saida = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(raiz),
            stderr=subprocess.DEVNULL, timeout=10)
        commit = saida.decode("ascii", "replace").strip()
    except Exception:
        return u""
    if commit and (_arvore_suja(raiz) or componentes_sujos(raiz)):
        commit += MARCA_DE_ARVORE_SUJA
    return commit


AVISO_DE_ARVORE_SUJA = (u"ATENCAO: arvore com alteracao nao commitada; o "
                        u"BUILD diz +alterado; nao publique esta montagem")


def aviso_de_arvore_suja(texto_da_entrega):
    try:
        for linha in str(texto_da_entrega or u"").splitlines():
            if (linha.startswith(u"BUILD=")
                    and linha.strip().endswith(MARCA_DE_ARVORE_SUJA)):
                return AVISO_DE_ARVORE_SUJA
    except Exception:
        pass
    return u""


def dados(raiz, hoje=None):
    marca = (hoje or datetime.datetime.now()).strftime("%Y-%m-%d")
    commit = _commit_curto(raiz)
    return marca, (u"%s.%s" % (marca, commit)) if commit else marca


VERSION_CABECA = (
    u"# Generated at packaging time. Do not edit.",
    u"# This is the same stamp the installer reads from entrega.txt.",
    u"",
)


def version_txt(projeto, versao, produto=u"", raiz=None, hoje=None):
    data, build = dados(raiz or os.getcwd(), hoje)
    linhas = list(VERSION_CABECA)
    if produto:
        linhas.append(u"PRODUCT   %s" % produto)
    linhas.append(u"PROJECT   %s" % projeto)
    linhas.append(u"VERSION   %s" % versao)
    linhas.append(u"BUILT     %s" % data)
    if build:
        linhas.append(u"BUILD     %s" % build)
    return u"\n".join(linhas) + u"\n"


def texto(projeto, versao, produto=u"", raiz=None, hoje=None):
    data, build = dados(raiz or os.getcwd(), hoje)
    linhas = list(CABECA)
    if produto:
        linhas.append(u"PRODUTO=%s" % produto)
    linhas.append(u"PROJETO=%s" % projeto)
    linhas.append(u"VERSAO=%s" % versao)
    linhas.append(u"DATA=%s" % data)
    if build:
        linhas.append(u"BUILD=%s" % build)
    return u"\n".join(linhas) + u"\n"
