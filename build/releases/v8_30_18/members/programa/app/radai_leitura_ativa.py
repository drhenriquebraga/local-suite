"""I/O solicitado pela interface. Somente requisições ativas ocupam uma vaga."""
import asyncio
from contextlib import asynccontextmanager, contextmanager
import os
import threading
import time


class LeituraCancelada(InterruptedError):
    pass


if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    _win = ctypes.WinDLL("kernel32", use_last_error=True)
    _win.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _win.OpenThread.restype = wintypes.HANDLE
    _win.CancelSynchronousIo.argtypes = (wintypes.HANDLE,)
    _win.CancelSynchronousIo.restype = wintypes.BOOL
    _win.CloseHandle.argtypes = (wintypes.HANDLE,)


class Leitura:
    def __init__(self):
        self.evento = threading.Event()
        self._trava = threading.Lock()
        self._handles = set()

    def parar(self):
        self.evento.set()
        if os.name == "nt":
            with self._trava:
                for handle in self._handles:
                    _win.CancelSynchronousIo(handle)

    @contextmanager
    def participante(self):
        handle = None
        with self._trava:
            if self.evento.is_set():
                raise LeituraCancelada("Leitura interrompida.")
            if os.name == "nt":
                handle = _win.OpenThread(0x0001, False, threading.get_native_id())  # THREAD_TERMINATE
                if handle:
                    self._handles.add(handle)
        try:
            yield
        finally:
            if handle:
                with self._trava:
                    self._handles.remove(handle)
                    _win.CloseHandle(handle)


_VAGAS = threading.BoundedSemaphore(4)
_ESPERAS = threading.BoundedSemaphore(8)


@asynccontextmanager
async def desconexao_do_pedido(request):
    """Depois de ler o corpo, escuta o canal ASGI até o socket fechar."""
    async def escutar():
        receber = getattr(request, "receive", None)
        if callable(receber):
            while (await receber())["type"] != "http.disconnect":
                pass
        else:
            while not await request.is_disconnected():
                await asyncio.sleep(0.1)
    escuta = asyncio.create_task(escutar())
    try:
        yield escuta
    finally:
        escuta.cancel()
        await asyncio.gather(escuta, return_exceptions=True)


async def executar(request, funcao, *args, prazo=None):
    async with desconexao_do_pedido(request) as desconexao:
        return await _executar(desconexao, funcao, args, prazo)


async def _executar(desconexao, funcao, args, prazo):
    # A vaga pertence ao worker até sair, inclusive se a requisição já terminou.
    inicio = time.monotonic()
    limite = inicio + prazo if prazo is not None else None
    if not _VAGAS.acquire(blocking=False):
        if not _ESPERAS.acquire(blocking=False):
            raise RuntimeError("Há outras leituras em andamento. Tente novamente.")
        try:
            while True:
                if desconexao.done():
                    raise LeituraCancelada("Leitura interrompida.")
                agora = time.monotonic()
                if agora >= inicio + 8 or (limite is not None and agora >= limite):
                    raise RuntimeError("Há outras leituras em andamento. Tente novamente.")
                if _VAGAS.acquire(blocking=False):
                    break
                await asyncio.sleep(0.1)
        finally:
            _ESPERAS.release()
    leitura = Leitura()
    def worker():
        try:
            with leitura.participante():
                return funcao(*args, parar=leitura.evento.is_set)
        finally:
            _VAGAS.release()
    try:
        futuro = asyncio.get_running_loop().run_in_executor(None, worker)
    except BaseException:
        _VAGAS.release()
        raise
    try:
        espera = max(0, limite - time.monotonic()) if limite is not None else None
        await asyncio.wait([futuro, desconexao], timeout=espera, return_when=asyncio.FIRST_COMPLETED)
        if not futuro.done():
            raise LeituraCancelada("Leitura interrompida.")
        return futuro.result()
    finally:
        leitura.parar()
        if not futuro.done():
            futuro.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
