# -*- coding: utf-8 -*-
import os
import re
from pathlib import Path

VARIAVEL = "RADAI_RAIZ_DEPLOY"
POLITICA = "ENTREGA.md"
TETO_DA_SUBIDA = 4

_LINHA = re.compile(r"^\s*deploy\s*->\s*(.+?)[\\/]<PROJETO>", re.I | re.M)


def _politica(de):
    d = Path(str(de)).resolve()
    for _ in range(TETO_DA_SUBIDA + 1):
        p = d / POLITICA
        if p.is_file():
            return p
        if d.parent == d:
            break
        d = d.parent
    return None


def _da_politica(politica):
    try:
        m = _LINHA.search(politica.read_text(encoding="utf-8-sig",
                                             errors="replace"))
    except OSError:
        return None
    return Path(m.group(1).strip()) if m else None


def _por_marca(politica, projeto):
    if not projeto:
        return None
    ecossistema = politica.parent
    achadas = []
    try:
        irmas = sorted(os.listdir(str(ecossistema.parent)))
    except OSError:
        return None
    for nome in irmas:
        cand = ecossistema.parent / nome
        if cand == ecossistema or not cand.is_dir():
            continue
        proj = cand / projeto
        try:
            filhos = os.listdir(str(proj)) if proj.is_dir() else []
        except OSError:
            filhos = []
        if any(f == "latest" or re.match(r"^v\d+(\.\d+)*$", f) for f in filhos):
            achadas.append(cand)
    return achadas[0] if len(achadas) == 1 else None


def raiz_de_entrega(projeto=None, de=None):
    v = (os.environ.get(VARIAVEL) or "").strip().strip('"')
    if v:
        return Path(v), u"variavel %s" % VARIAVEL
    politica = _politica(de or Path(__file__).resolve().parent)
    if politica is not None:
        declarada = _da_politica(politica)
        if declarada is not None:
            return declarada, u"declarada em %s" % politica
        marcada = _por_marca(politica, projeto)
        if marcada is not None:
            return marcada, u"marca: %s\\%s ja tem entregas" % (marcada, projeto)
    raise SystemExit(
        u"PAREI: nao sei onde fica a raiz de entrega.\n"
        u"      Nao ha a variavel %s, nem um %s do ecossistema acima\n"
        u"      deste repositorio que a declare.\n"
        u"      Defina  %s=<pasta onde o instalador leve deve sair>  e rode\n"
        u"      de novo. (Esta pergunta so existe na maquina de quem\n"
        u"      PUBLICA; o preparo numa estacao nunca passa por aqui.)"
        % (VARIAVEL, POLITICA, VARIAVEL))
