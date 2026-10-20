# -*- coding: utf-8 -*-


# GUARDA: rota que trabalha (disco, rede, modelo) roda no threadpool, e nunca
# dentro do laço de eventos: trabalho no laço congela todas as telas.
def no_threadpool(fn, *a, **kw):
    from starlette.concurrency import run_in_threadpool
    return run_in_threadpool(fn, *a, **kw)
