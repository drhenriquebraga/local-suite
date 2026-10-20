# -*- coding: utf-8 -*-
import atexit
import functools
import json
import os
import shutil
import stat
import sys
import tempfile
import time

_CRIADAS = []


def _tirar_somente_leitura(func, caminho, _exc):
    try:
        os.chmod(caminho, stat.S_IWRITE)
        func(caminho)
    except OSError:
        pass


def apagar_arvore(d):
    # GUARDA: o objeto do .git e somente leitura, e o rmtree sem isto deixa o repositorio inteiro no TEMP.
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(d, onexc=_tirar_somente_leitura)
        else:
            shutil.rmtree(d, onerror=_tirar_somente_leitura)
    except OSError:
        pass


def temporaria(prefixo="radai_teste_"):
    d = tempfile.mkdtemp(prefix=prefixo)
    _CRIADAS.append(d)
    return d


def limpar():
    while _CRIADAS:
        d = _CRIADAS.pop()
        try:
            apagar_arvore(d)
        except Exception:
            pass


atexit.register(limpar)


PASTA_DO_CADASTRO = "_radai_cleanup_execucoes"

FOLGA_S = 1.0

_ADOTADOS = []
_MINHAS = set()
_ESTADO = {"mkdtemp_original": None, "varredor": False, "registros": [],
           "desde": None, "criado": None}
_IMPORTADO_EM = time.time()


def _norm(p):
    try:
        return os.path.normcase(os.path.abspath(os.fsdecode(p)))
    except Exception:
        return u""


def _instalar_registro_de_mkdtemp():
    if _ESTADO["mkdtemp_original"] is not None:
        return
    original = tempfile.mkdtemp

    @functools.wraps(original)
    def _mkdtemp(*a, **k):
        d = original(*a, **k)
        try:
            _MINHAS.add(_norm(d))
        except Exception:
            pass
        return d

    _mkdtemp.__wrapped__ = original
    _ESTADO["mkdtemp_original"] = original
    tempfile.mkdtemp = _mkdtemp


def _processo(pid):
    try:
        pid = int(pid)
    except Exception:
        return True, None
    if pid <= 0:
        return True, None
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL,
                                        wintypes.DWORD)
            h = k32.OpenProcess(0x1000, False, pid)
            if not h:
                err = ctypes.get_last_error()
                if err == 87:
                    return False, None
                return True, None
            try:
                cod = wintypes.DWORD()
                if k32.GetExitCodeProcess(h, ctypes.byref(cod)) \
                        and cod.value != 259:
                    return False, None
                cria, fim, nuc, usu = (ctypes.c_ulonglong(),
                                       ctypes.c_ulonglong(),
                                       ctypes.c_ulonglong(),
                                       ctypes.c_ulonglong())
                if k32.GetProcessTimes(h, ctypes.byref(cria), ctypes.byref(fim),
                                       ctypes.byref(nuc), ctypes.byref(usu)):
                    return True, (cria.value - 116444736000000000) / 1e7
                return True, None
            finally:
                k32.CloseHandle(h)
        except Exception:
            return True, None
    try:
        os.kill(pid, 0)
        return True, None
    except PermissionError:
        return True, None
    except (ProcessLookupError, OSError):
        return False, None
    except Exception:
        return True, None


def _execucao_viva(reg):
    existe, nasceu = _processo(reg.get("pid"))
    if not existe:
        return False
    gravado = reg.get("criado")
    if nasceu is not None and gravado is not None:
        try:
            if abs(float(nasceu) - float(gravado)) > 2.0:
                return False
        except Exception:
            pass
    return True


def _desde():
    if _ESTADO["desde"] is None:
        _, nasceu = _processo(os.getpid())
        _ESTADO["criado"] = nasceu
        _ESTADO["desde"] = (nasceu if nasceu is not None
                            else _IMPORTADO_EM)
    return _ESTADO["desde"]


def _gravar_no_cadastro():
    reg = {"pid": os.getpid(), "desde": _desde(), "criado": _ESTADO["criado"],
           "adotados": [[p, ini] for p, ini, _b in _ADOTADOS]}
    feitos = []
    for base in sorted(set(b for _p, _i, b in _ADOTADOS)):
        pasta = os.path.join(base, PASTA_DO_CADASTRO)
        alvo = os.path.join(pasta, "%d_%d.json"
                            % (os.getpid(), int(_desde() * 1000)))
        try:
            os.makedirs(pasta, exist_ok=True)
            tmp = alvo + ".%d.tmp" % os.getpid()
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(reg, fh)
            os.replace(tmp, alvo)
            feitos.append(alvo)
        except OSError:
            pass
    _ESTADO["registros"] = feitos


def _outras_execucoes(bases):
    meus = set(_norm(r) for r in _ESTADO["registros"])
    vivas = []
    for base in bases:
        pasta = os.path.join(base, PASTA_DO_CADASTRO)
        try:
            nomes = os.listdir(pasta)
        except OSError:
            continue
        for x in nomes:
            cam = os.path.join(pasta, x)
            try:
                pid = int(x.split("_", 1)[0])
            except ValueError:
                continue
            if x.endswith(".tmp"):
                if not _processo(pid)[0]:
                    try:
                        os.remove(cam)
                    except OSError:
                        pass
                continue
            if not x.endswith(".json") or _norm(cam) in meus:
                continue
            try:
                with open(cam, encoding="utf-8") as fh:
                    reg = json.load(fh)
            except Exception:
                reg = None
            if reg is None:
                reg = {"pid": pid, "criado": None, "desde": 0.0,
                       "adotados": [["", 0.0]]}
            reg["pid"] = pid
            if _execucao_viva(reg):
                vivas.append(reg)
            else:
                try:
                    os.remove(cam)
                except OSError:
                    pass
    return vivas


def _pode_ser_de(reg, nome, ctime):
    try:
        desde = float(reg.get("desde") or 0.0)
    except Exception:
        desde = 0.0
    for par in reg.get("adotados") or ():
        try:
            p = par[0]
        except Exception:
            continue
        if nome.startswith(p) and ctime >= desde - FOLGA_S:
            return True
    return False


def _varrer():
    bases = set(b for _p, _i, b in _ADOTADOS)
    try:
        bases.add(tempfile.gettempdir())
    except Exception:
        pass
    candidatas = []
    for base in sorted(bases):
        try:
            nomes = os.listdir(base)
        except OSError:
            continue
        for x in nomes:
            inis = [ini for p, ini, _b in _ADOTADOS if x.startswith(p)]
            if not inis:
                continue
            d = os.path.join(base, x)
            try:
                if not os.path.isdir(d):
                    continue
                ct = os.path.getctime(d)
            except OSError:
                continue
            if any(ct >= ini - FOLGA_S for ini in inis):
                candidatas.append((d, x, ct))
    outras = _outras_execucoes(bases) if candidatas else []
    for d, x, ct in candidatas:
        if _norm(d) not in _MINHAS and \
                any(_pode_ser_de(r, x, ct) for r in outras):
            continue
        apagar_arvore(d)
    for cam in _ESTADO["registros"]:
        try:
            os.remove(cam)
        except OSError:
            pass
    _ESTADO["registros"] = []


def adotar_prefixo(prefixo):
    inicio = time.time()
    try:
        base = tempfile.gettempdir()
    except Exception:
        base = None
    _instalar_registro_de_mkdtemp()
    _desde()
    if base:
        _ADOTADOS.append((prefixo, inicio, base))
        _gravar_no_cadastro()
    if not _ESTADO["varredor"]:
        _ESTADO["varredor"] = True
        atexit.register(_varrer)


def sobraram(prefixos=("radai_", "lk_", "zp_")):
    base = tempfile.gettempdir()
    n = 0
    try:
        for x in os.listdir(base):
            if any(x.startswith(p) for p in prefixos) and \
                    os.path.isdir(os.path.join(base, x)):
                n += 1
    except OSError:
        pass
    return n
