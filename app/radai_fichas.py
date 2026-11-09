# -*- coding: utf-8 -*-
import secrets
import threading
import time

VALIDADE_S = 2 * 60 * 60
MAXIMO = 256

_TRAVA = threading.Lock()
_FICHAS = {}


def _limpar(agora):
    vencidas = [k for k, (t, _d) in _FICHAS.items() if agora - t > VALIDADE_S]
    for k in vencidas:
        del _FICHAS[k]
    while len(_FICHAS) >= MAXIMO:
        del _FICHAS[min(_FICHAS, key=lambda k: _FICHAS[k][0])]


def guardar(dados):
    agora = time.time()
    ficha = secrets.token_urlsafe(9)
    with _TRAVA:
        _limpar(agora)
        _FICHAS[ficha] = (agora, dados)
    return ficha


def ler(ficha):
    if not isinstance(ficha, str) or not ficha:
        return None
    with _TRAVA:
        item = _FICHAS.get(ficha)
        if item is None:
            return None
        if time.time() - item[0] > VALIDADE_S:
            del _FICHAS[ficha]
            return None
        return item[1]
