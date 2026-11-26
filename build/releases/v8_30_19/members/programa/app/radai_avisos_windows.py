"""Avisos de pasta do Vigia. O Windows mantém um buffer por raiz, sem inventário em repouso."""
import ctypes
from ctypes import wintypes as W
import ntpath
import os
import struct
import subprocess
import sys
import threading


_BUFFER = 64 * 1024  # limite aceito também pelo SMB
_MAX_EVENTOS = 512
_PRAZO_ABRIR = 5.0
_INVALIDO = ctypes.c_void_p(-1).value


class _Overlapped(ctypes.Structure):
    _fields_ = [("interno", ctypes.c_size_t), ("quantidade", ctypes.c_size_t),
                ("offset", W.DWORD), ("offset_alto", W.DWORD), ("evento", W.HANDLE)]


def _kernel():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    def assinatura(nome, resultado, *tipos):
        f = getattr(k, nome)
        f.argtypes, f.restype = tipos, resultado
    assinatura("CreateFileW", W.HANDLE, W.LPCWSTR, W.DWORD, W.DWORD, W.LPVOID, W.DWORD, W.DWORD, W.HANDLE)
    assinatura("CreateEventW", W.HANDLE, W.LPVOID, W.BOOL, W.BOOL, W.LPCWSTR)
    assinatura("SetEvent", W.BOOL, W.HANDLE)
    assinatura("ResetEvent", W.BOOL, W.HANDLE)
    assinatura("CloseHandle", W.BOOL, W.HANDLE)
    assinatura("DuplicateHandle", W.BOOL, W.HANDLE, W.HANDLE, W.HANDLE, ctypes.POINTER(W.HANDLE),
               W.DWORD, W.BOOL, W.DWORD)
    assinatura("ReadDirectoryChangesW", W.BOOL, W.HANDLE, W.LPVOID, W.DWORD, W.BOOL, W.DWORD,
               ctypes.POINTER(W.DWORD), ctypes.POINTER(_Overlapped), W.LPVOID)
    assinatura("GetOverlappedResult", W.BOOL, W.HANDLE, ctypes.POINTER(_Overlapped), ctypes.POINTER(W.DWORD), W.BOOL)
    assinatura("CancelIoEx", W.BOOL, W.HANDLE, ctypes.POINTER(_Overlapped))
    assinatura("WaitForMultipleObjects", W.DWORD, W.DWORD, ctypes.POINTER(W.HANDLE), W.BOOL, W.DWORD)
    return k


def _erro(codigo):
    if codigo == 1022:  # ERROR_NOTIFY_ENUM_DIR
        return "overflow"
    if codigo in (1, 50, 87, 120):  # provedor sem suporte a change notify
        return "sem_suporte"
    return "desconectado"


def _eventos(bloco):
    """Decodificar FILE_NOTIFY_INFORMATION com teto e validação antes de entregar o lote."""
    if len(bloco) > _BUFFER:
        raise ValueError("buffer maior que o admitido pelo provedor")
    eventos = []
    cursor = 0
    while cursor + 12 <= len(bloco):
        seguinte, acao, tamanho = struct.unpack_from("<III", bloco, cursor)
        if (not tamanho or tamanho % 2 or acao not in range(1, 6) or len(eventos) >= _MAX_EVENTOS
                or cursor + 12 + tamanho > len(bloco)):
            break
        nome = bloco[cursor+12:cursor+12+tamanho].decode("utf-16-le", "surrogatepass")
        if "\x00" in nome or ntpath.isabs(nome) or ntpath.splitdrive(nome)[0] or any(
                parte in ("", ".", "..") for parte in nome.replace("/", "\\").split("\\")):
            break
        eventos.append((acao, nome))
        if not seguinte:
            return tuple(eventos)
        if seguinte % 4 or seguinte < 12 + tamanho or cursor + seguinte >= len(bloco):
            break
        cursor += seguinte
    raise ValueError("buffer de notificações incompleto")


def _abrir_no_filho(raiz):
    # O CreateFileW pode esperar pelo redirecionador de rede antes de produzir um
    # handle cancelável. O pai pode encerrar este auxiliar a qualquer momento.
    k = _kernel()
    h = k.CreateFileW(raiz, 1, 7, None, 3, 0x42000000, None)
    # FILE_LIST_DIRECTORY, compartilhamento de leitura/escrita/exclusão,
    # OPEN_EXISTING, BACKUP_SEMANTICS | OVERLAPPED.
    if h == _INVALIDO:
        print("erro", ctypes.get_last_error(), flush=True)
        return
    try:
        print("aberto", h, flush=True)
        sys.stdin.buffer.read(1)  # a duplicação no pai precisa ocorrer antes da saída
    finally:
        k.CloseHandle(h)


def _iniciar_abridor(raiz):
    return subprocess.Popen([sys.executable, "-S", "-B", __file__, "--abrir", raiz],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)


class _Assinatura:
    def __init__(self, raiz, avisar):
        self._raiz = os.fsdecode(raiz)
        self._avisar = avisar
        self._trava = threading.RLock()
        self._fechada = False
        self._parar = None
        self._abridor = None
        self._k = None
        self._thread = threading.Thread(target=self._acompanhar, name="aviso de pasta do Vigia", daemon=True)

    def _entregar(self, estado, eventos=()):
        with self._trava:
            if self._fechada:
                return
            destino = self._avisar
        destino(estado, eventos)

    def _cancelar_abertura(self, proc):
        with self._trava:
            if self._abridor is proc and proc.poll() is None:
                proc.kill()

    def solicitar_fechamento(self):
        """Sinaliza todas as raízes antes de aguardar a liberação de cada uma."""
        with self._trava:
            self._fechada = True
            if self._parar:
                self._k.SetEvent(self._parar)
            if self._abridor:
                self._cancelar_abertura(self._abridor)

    def fechar(self):
        self.solicitar_fechamento()
        if self._thread is not threading.current_thread():
            self._thread.join(2)
            return not self._thread.is_alive()
        return True  # a própria thread libera os handles ao retornar deste callback

    def _abrir(self, k):
        with self._trava:
            if self._fechada:
                return None
            proc = self._abridor = _iniciar_abridor(self._raiz)
        prazo = threading.Timer(_PRAZO_ABRIR, self._cancelar_abertura, args=(proc,))
        prazo.daemon = True
        prazo.start()
        try:
            resposta = proc.stdout.readline(96).split()
            if len(resposta) != 2 or not resposta[1].isdigit():
                raise OSError("abertura da raiz interrompida")
            if resposta[0] == b"erro":
                raise ctypes.WinError(int(resposta[1]))
            if resposta[0] != b"aberto":
                raise OSError("resposta do leitor inválida")
            with self._trava:
                if self._fechada:
                    return None
                handle = W.HANDLE()
                if not k.DuplicateHandle(int(proc._handle), int(resposta[1]), W.HANDLE(-1),
                                         ctypes.byref(handle), 0, False, 2):
                    raise ctypes.WinError(ctypes.get_last_error())
            return handle.value
        finally:
            prazo.cancel()
            proc.stdin.close()
            proc.stdout.close()
            try:
                proc.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                self._cancelar_abertura(proc)
                proc.wait()
            with self._trava:
                self._abridor = None

    def _acompanhar(self):
        raiz = evento = None
        pendente = False
        try:
            if os.name != "nt":
                self._entregar("sem_suporte")
                return
            self._k = k = _kernel()
            with self._trava:
                if self._fechada:
                    return
                self._parar = k.CreateEventW(None, True, False, None)
                if not self._parar:
                    raise ctypes.WinError(ctypes.get_last_error())
            raiz = self._abrir(k)
            if not raiz:
                return
            evento = k.CreateEventW(None, True, False, None)
            if not evento:
                raise ctypes.WinError(ctypes.get_last_error())
            buf = ctypes.create_string_buffer(_BUFFER)
            sinais = (W.HANDLE * 2)(self._parar, evento)
            pronto = False
            dados = None
            while True:
                with self._trava:
                    if self._fechada:
                        return
                op = _Overlapped(evento=evento)
                k.ResetEvent(evento)
                if not k.ReadDirectoryChangesW(raiz, buf, len(buf), True, 0x13, None, ctypes.byref(op), None):
                    erro = ctypes.get_last_error()
                    if erro != 997:  # ERROR_IO_PENDING também confirma a operação overlapped
                        raise ctypes.WinError(erro)
                pendente = True
                if not pronto:
                    self._entregar("pronto")
                    pronto = True
                if dados is not None:
                    self._entregar("mudou", _eventos(dados))
                    dados = None
                # O kernel retém mudanças desde o primeiro pedido. Rearmar antes
                # de invocar o consumidor diminui a janela de estouro em rajadas.
                sinal = k.WaitForMultipleObjects(2, sinais, False, 0xffffffff)
                if sinal == 0:
                    return
                if sinal != 1:
                    raise ctypes.WinError(ctypes.get_last_error())
                quantidade = W.DWORD()
                ok = k.GetOverlappedResult(raiz, ctypes.byref(op), ctypes.byref(quantidade), False)
                pendente = False
                if not ok:
                    raise ctypes.WinError(ctypes.get_last_error())
                if not 0 < quantidade.value <= len(buf):
                    raise ValueError("notificações excederam o buffer")
                dados = ctypes.string_at(buf, quantidade.value)
        except ValueError:
            self._entregar("overflow")
        except (OSError, AttributeError) as e:
            self._entregar(_erro(getattr(e, "winerror", None)))
        finally:
            if pendente:
                k.CancelIoEx(raiz, ctypes.byref(op))
                # O buffer e OVERLAPPED devem permanecer vivos até a conclusão.
                k.GetOverlappedResult(raiz, ctypes.byref(op), ctypes.byref(W.DWORD()), True)
            if evento:
                k.CloseHandle(evento)
            if raiz:
                k.CloseHandle(raiz)
            with self._trava:
                if self._parar:
                    k.CloseHandle(self._parar)
                    self._parar = None
                self._avisar = None


def inscrever(raiz, avisar):
    """Após 'pronto', chama avisar(estado, tupla_de_(ação,nome_relativo)). Sem retry interno."""
    entrada = _Assinatura(raiz, avisar)
    entrada._thread.start()
    return entrada


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--abrir":
    _abrir_no_filho(sys.argv[2])
