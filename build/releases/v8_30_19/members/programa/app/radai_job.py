"""Vínculo dos trabalhadores à vida do motor no Windows."""
import os

_HANDLE = None
_TENTADO = False
_AVISO = None


def vincular(permitir_saida=False):
    """O handle não herdável pertence ao processo atual e dura até sua saída."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes as W
    class Basicos(ctypes.Structure):
        _fields_ = [("cpu_processo", ctypes.c_int64), ("cpu_job", ctypes.c_int64), ("flags", W.DWORD),
                    ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t), ("ativos", W.DWORD),
                    ("afinidade", ctypes.c_size_t), ("prioridade", W.DWORD), ("agenda", W.DWORD)]
    class Estendidos(ctypes.Structure):
        _fields_ = [("basicos", Basicos), ("contadores", ctypes.c_uint64 * 6),
                    ("limites_e_picos", ctypes.c_size_t * 4)]
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    criar = k.CreateJobObjectW
    criar.argtypes, criar.restype = [ctypes.c_void_p, W.LPCWSTR], W.HANDLE
    definir = k.SetInformationJobObject
    definir.argtypes, definir.restype = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD], W.BOOL
    ingressar = k.AssignProcessToJobObject
    ingressar.argtypes, ingressar.restype = [W.HANDLE, W.HANDLE], W.BOOL
    job = criar(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limites = Estendidos()
    limites.basicos.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if permitir_saida:
        limites.basicos.flags |= 0x0800  # JOB_OBJECT_LIMIT_BREAKAWAY_OK, somente quando solicitado.
    if not (definir(job, 9, ctypes.byref(limites), ctypes.sizeof(limites)) and ingressar(job, W.HANDLE(-1))):
        erro = ctypes.get_last_error()
        k.CloseHandle(W.HANDLE(job))
        raise ctypes.WinError(erro)
    return job


def armar_motor():
    """Em estação que proíbe um Job aninhado, conservar o encerramento convencional."""
    global _HANDLE, _TENTADO, _AVISO
    if not _TENTADO:
        _TENTADO = True
        try:
            _HANDLE = vincular(permitir_saida=True)
        except OSError as exc:
            codigo = getattr(exc, "winerror", None) or exc.errno
            _AVISO = "Job do motor indisponível (%s). Encerramento convencional ativo." % codigo
    return _AVISO


def flags_de_saida():
    """Somente processos de manutenção e restauração sobrevivem à saída do motor."""
    return 0x01000000 if _HANDLE else 0  # CREATE_BREAKAWAY_FROM_JOB
