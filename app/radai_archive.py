# -*- coding: utf-8 -*-
import io
import json
import os
from datetime import datetime
from pathlib import Path, PureWindowsPath

VERSAO_ACERVO = "1.0"

HERE = Path(__file__).resolve().parent


_MARCAS_NUVEM = ("onedrive", "google drive", "googledrive", "gdrive",
                 "dropbox", "icloud", "meu drive", "my drive", "sharepoint",
                 "nextcloud", "mega", "sync")


_DRIVE_DB = ("Google", "DriveFS", "root_preference_sqlite.db")
_CACHE_RAIZES = {"quando": None, "valor": ()}


def _raizes_declaradas():
    import os
    bruto = os.environ.get("RADAI_RAIZES_NUVEM") or ""
    return tuple(p.strip().strip('"') for p in bruto.split(";") if p.strip())


_LOCAL_DO_PERFIL = []


def _local_do_perfil():
    if _LOCAL_DO_PERFIL:
        return _LOCAL_DO_PERFIL[0]
    achada = ""
    try:
        import ctypes
        from ctypes import wintypes

        class _Guid(ctypes.Structure):
            _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD),
                        ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]
        local_app_data = _Guid(0xF1B32785, 0x6FBA, 0x4FCF, (ctypes.c_ubyte * 8)(
            0x9D, 0x55, 0x7B, 0x8E, 0x7F, 0x15, 0x70, 0x91))
        k32 = ctypes.WinDLL("kernel32")
        adv = ctypes.WinDLL("advapi32")
        shell = ctypes.WinDLL("shell32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                         ctypes.POINTER(wintypes.HANDLE)]
        shell.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(_Guid), wintypes.DWORD, wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p)]
        token = wintypes.HANDLE()
        if not adv.OpenProcessToken(k32.GetCurrentProcess(), 0x000E,
                                    ctypes.byref(token)):
            token = wintypes.HANDLE()
        saida = ctypes.c_wchar_p()
        try:
            # GUARDA: com o token, a pasta nao segue a LOCALAPPDATA nem o USERPROFILE trocados no processo.
            if shell.SHGetKnownFolderPath(ctypes.byref(local_app_data), 0,
                                          token, ctypes.byref(saida)) == 0:
                achada = saida.value or ""
        finally:
            ctypes.WinDLL("ole32").CoTaskMemFree(saida)
            if token.value:
                k32.CloseHandle(token)
    except Exception:
        achada = ""
    _LOCAL_DO_PERFIL.append(achada)
    return achada


def _bancos_do_drive():
    import os
    bancos = []
    for base in (os.environ.get("LOCALAPPDATA") or "", _local_do_perfil()):
        db = os.path.join(base, *_DRIVE_DB) if base else ""
        if db and os.path.normcase(db) not in [os.path.normcase(b)
                                               for b in bancos]:
            bancos.append(db)
    return bancos


def _raizes_do_banco(db):
    import sqlite3
    achadas = []
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    try:
        for (p,) in con.execute("select last_seen_absolute_path from roots"):
            if p:
                achadas.append(str(p).rstrip("\\/"))
    finally:
        con.close()
    return achadas


def raizes_espelhadas():
    import os
    fora = list(_raizes_declaradas())
    carimbos = []
    for db in _bancos_do_drive():
        try:
            carimbos.append((db, os.path.getmtime(db)))
        except OSError:
            continue
    if not carimbos:
        return tuple(fora)
    carimbo = tuple(carimbos)
    if _CACHE_RAIZES["quando"] != carimbo:
        achadas, falhou = [], False
        for db, _quando in carimbos:
            try:
                achadas.extend(_raizes_do_banco(db))
            except Exception:
                falhou = True
        if falhou:
            return tuple(fora) + tuple(achadas)
        _CACHE_RAIZES["quando"] = carimbo
        _CACHE_RAIZES["valor"] = tuple(achadas)
    return tuple(fora) + _CACHE_RAIZES["valor"]

def em_pasta_sincronizada(caminho=None):
    import os
    bruto = str(caminho if caminho is not None else HERE)
    try:
        pleno = os.path.abspath(bruto)
    except Exception:
        pleno = bruto
    baixo = pleno.replace("/", "\\").rstrip("\\").lower()
    for r in raizes_espelhadas():
        raiz_baixa = r.replace("/", "\\").rstrip("\\").lower()
        if baixo == raiz_baixa or baixo.startswith(raiz_baixa + "\\"):
            return True, "Google Drive espelha %s" % r
    alvo = bruto.lower()
    for m in _MARCAS_NUVEM:
        if m in alvo:
            return True, m
    return False, ""


def _do_dados_txt():
    for pasta in (HERE, HERE.parent):
        arq = pasta / "_dados.txt"
        try:
            if not arq.is_file():
                continue
            with open(str(arq), "r", encoding="utf-8-sig", errors="replace") as f:
                for linha in f:
                    linha = linha.strip().strip('"')
                    if linha and not linha.startswith("#"):
                        return linha
        except Exception:
            continue
    return ""


def raiz():
    bruto = (os.environ.get("RADAI_CALIB_DIR") or "").strip().strip('"')
    if not bruto:
        bruto = _do_dados_txt()
    return Path(bruto) if bruto else (HERE / "calibracao")


def resolver_guardado(caminho):
    bruto = str(caminho or "").strip().strip('"')
    if not bruto:
        return ""
    if os.path.isfile(bruto):
        return bruto
    velho = PureWindowsPath(bruto.replace("/", "\\"))
    nome = velho.name
    if not nome:
        return ""
    base = raiz()
    mae = velho.parent.name
    tentativas = []
    if mae:
        tentativas.append(base / mae / nome)
    tentativas.append(base / nome)
    for t in tentativas:
        if t.is_file():
            return str(t)
    return ""

def _root_configurado():
    try:
        alvo = os.environ.get("RADAI_CONFIG") or ""
        p = Path(alvo) if alvo else (HERE / "radai_watcher.config")
        if not p.is_file():
            return ""
        for linha in io.open(str(p), encoding="utf-8-sig",
                             errors="replace"):
            linha = linha.strip()
            if linha.startswith("#") or "=" not in linha:
                continue
            k, _, v = linha.partition("=")
            if k.strip().upper() == "ROOT":
                return v.strip().strip('"')
    except Exception:
        pass
    return ""


def resolver_pasta(pasta):
    bruto = str(pasta or "").strip().strip('"')
    if not bruto:
        return ""
    if os.path.isdir(bruto):
        return bruto
    nome = PureWindowsPath(bruto.replace("/", "\\")).name
    if not nome:
        return ""
    candidatos = []
    root = _root_configurado()
    if root:
        candidatos.append(Path(root) / nome)
    candidatos.append(raiz().parent / nome)
    for c in candidatos:
        try:
            if c.is_dir():
                return str(c)
        except OSError:
            continue
    return ""

def conferir_local():
    caminho = raiz()
    nuvem, motivo = em_pasta_sincronizada(caminho)
    aviso = ""
    if nuvem:
        aviso = (u"O acervo esta em %s, que SINCRONIZA com a nuvem (%s). "
                 u"Ele guarda mascara e imagem DE PACIENTE: isso sairia do "
                 u"hospital. Aponte RADAI_CALIB_DIR para uma pasta local."
                 % (caminho, motivo))
    return {"caminho": str(caminho), "nuvem": nuvem, "motivo": motivo,
            "aviso": aviso}


def _sub(nome, criar=False):
    d = raiz() / nome
    if criar:
        d.mkdir(parents=True, exist_ok=True)
    return d


def pasta_receitas(criar=False):
    return _sub("receitas", criar)


def pasta_versoes(criar=False):
    return _sub("versoes", criar)


def pasta_relatorios(criar=False):
    return _sub("relatorios", criar)


def pasta_nv(criar=False):
    return _sub("nv", criar)


def caminho_acervo(criar=False):
    r = raiz()
    if criar:
        r.mkdir(parents=True, exist_ok=True)
    return r / "acervo.jsonl"


def caminho_comparacoes(criar=False):
    r = raiz()
    if criar:
        r.mkdir(parents=True, exist_ok=True)
    return r / "comparacoes.jsonl"


def registrar_comparacao(uid, estrutura, ts_nome, nv_nome, metricas=None,
                         relacao="", pasta="", rs="", segundos=0.0, avisos=None,
                         nv_arquivo="", nv_ids=None,
                         gabarito_nome="", gabarito_rs="", motor_b="nv"):
    reg = {"uid": str(uid or ""), "estrutura": str(estrutura or ""),
           "ts_nome": str(ts_nome or ""), "nv_nome": str(nv_nome or ""),
           "gabarito_nome": str(gabarito_nome or ""),
           "gabarito_rs": str(gabarito_rs or ""),
           "relacao": str(relacao or ""), "pasta": str(pasta or ""),
           "rs": str(rs or ""), "metricas": dict(metricas or {}),
           "nv_arquivo": str(nv_arquivo or ""),
           "nv_ids": [int(v) for v in (nv_ids or [])],
           "motor_b": str(motor_b or "nv"),
           "segundos": round(float(segundos or 0), 1),
           "avisos": list(avisos or []),
           "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    try:
        with open(str(caminho_comparacoes(criar=True)), "a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def _chave_comp(reg):
    return (reg.get("uid", ""), reg.get("estrutura", ""))


_CAMPOS_DE_ONTEM = {"nv_nome": "vista_nome", "nv_arquivo": "vista_arquivo",
                    "nv_ids": "vista_ids"}


def _com_nomes_de_hoje(reg):
    if not isinstance(reg, dict):
        return reg
    for hoje, ontem in _CAMPOS_DE_ONTEM.items():
        if hoje not in reg and ontem in reg:
            reg[hoje] = reg[ontem]
    if str(reg.get("motor_b") or "") in ("", "vista", "v3d"):
        reg["motor_b"] = "nv"
    return reg


def ler_comparacoes(limite=None):
    p = caminho_comparacoes()
    if not p.exists():
        return []
    ultimo, ordem = {}, []
    try:
        with open(str(p), "r", encoding="utf-8", errors="replace") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    reg = _com_nomes_de_hoje(json.loads(linha))
                except Exception:
                    continue
                if not isinstance(reg, dict):
                    continue
                k = _chave_comp(reg)
                if k in ultimo:
                    ordem.remove(k)
                ultimo[k] = reg
                ordem.append(k)
    except Exception:
        return []
    regs = [ultimo[k] for k in reversed(ordem)]
    return regs[:limite] if limite else regs


def registrar_serie(uid, pasta, rs, date="", pid="", estruturas=0, secs=0,
                    maquina="", ver=""):
    reg = {"uid": str(uid or ""), "pasta": str(pasta or ""), "rs": str(rs or ""),
           "date": str(date or ""), "pid": str(pid or ""),
           "estruturas": int(estruturas or 0), "secs": int(secs or 0),
           "maquina": str(maquina or ""), "ver": str(ver or ""),
           "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    try:
        with open(str(caminho_acervo(criar=True)), "a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def ler_acervo(limite=None):
    p = caminho_acervo()
    if not p.exists():
        return []
    ultimo, ordem = {}, []
    try:
        with open(str(p), "r", encoding="utf-8", errors="replace") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    reg = json.loads(linha)
                except Exception:
                    continue
                if not isinstance(reg, dict):
                    continue
                uid = reg.get("uid") or ""
                if uid in ultimo:
                    ordem.remove(uid)
                ultimo[uid] = reg
                ordem.append(uid)
    except Exception:
        return []
    regs = [ultimo[u] for u in reversed(ordem)]
    return regs[:limite] if limite else regs


def conferir_acervo(podar=False, limite=None, log=None):
    regs = ler_acervo()
    fora = []
    for reg in regs:
        pasta = str(reg.get("pasta") or "")
        rs = str(reg.get("rs") or "")
        item = dict(reg)
        try:
            if not pasta or not os.path.isdir(pasta):
                item["estado"] = "sem_pasta"
            elif rs and not os.path.exists(os.path.join(pasta, rs)):
                item["estado"] = "sem_rs"
            else:
                item["estado"] = "ok"
        except Exception:
            item["estado"] = "ok"
        fora.append(item)

    if podar:
        mortos = [x for x in fora if x.get("estado") == "sem_pasta"]
        if mortos:
            vivos = [x for x in fora if x.get("estado") != "sem_pasta"]
            try:
                p = caminho_acervo(criar=True)
                tmp = str(p) + ".novo"
                with open(tmp, "w", encoding="utf-8") as f:
                    for x in reversed(vivos):
                        y = dict(x)
                        y.pop("estado", None)
                        f.write(json.dumps(y, ensure_ascii=False) + "\n")
                os.replace(tmp, str(p))
                fora = vivos
                if log:
                    log("acervo: %d serie(s) sem pasta saíram do índice, %d "
                        "continuam" % (len(mortos), len(vivos)))
            except Exception as e:
                if log:
                    log("acervo: nao consegui podar (%s) — o indice segue "
                        "como estava" % str(e)[:120])
    return fora[:limite] if limite else fora


def _contar(pasta, padrao="*.json"):
    try:
        return len(list(pasta.glob(padrao))) if pasta.exists() else 0
    except Exception:
        return 0


def estado():
    info = {"versao": VERSAO_ACERVO, "raiz": str(raiz()), "existe": False,
            "series": 0, "ultima_serie": "", "receitas": 0, "versoes": 0,
            "ultima_versao": "", "comparacoes": 0, "erro": ""}
    try:
        info["existe"] = raiz().exists()
        regs = ler_acervo()
        info["series"] = len(regs)
        if regs:
            info["ultima_serie"] = regs[0].get("quando", "")
        info["comparacoes"] = len(ler_comparacoes())
        info["receitas"] = _contar(pasta_receitas())
        versoes = sorted(pasta_versoes().glob("*.json")) if pasta_versoes().exists() else []
        info["versoes"] = len(versoes)
        if versoes:
            info["ultima_versao"] = versoes[-1].stem
    except Exception as e:
        info["erro"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    return info


def pasta_temporaria_local(marcar_ambiente=True):
    import tempfile
    explicita = (os.environ.get("RADAI_TMP") or "").strip()
    chave = (explicita,
             (os.environ.get("RADAI_RAIZ_INSTALACAO") or "").strip())
    # GUARDA: uma escolha por processo. Refeita a cada chamada, ela trocava
    # de disco no meio do trabalho, e as faxinas viam so o disco da vez.
    with _ESCOLHA_TRAVA:
        alvo = _ESCOLHA.get("alvo") if _ESCOLHA.get("chave") == chave else None
        if not alvo:
            if explicita:
                alvo = escolher_temporaria([explicita], livre=lambda c: 1.0)
            if not alvo:
                alvo = escolher_temporaria(candidatos_temporarios())
            if not alvo:
                alvo = tempfile.gettempdir()
            _ESCOLHA["chave"], _ESCOLHA["alvo"] = chave, alvo
    if marcar_ambiente:
        _marcar_ambiente(alvo)
    return alvo


import threading as _threading
_ESCOLHA = {"chave": None, "alvo": None}
_ESCOLHA_TRAVA = _threading.Lock()


def esquecer_temporaria():
    with _ESCOLHA_TRAVA:
        _ESCOLHA["chave"], _ESCOLHA["alvo"] = None, None


def raizes_temporarias():
    import tempfile
    vistos, saida = set(), []

    def _mais(c):
        try:
            c = str(c)
            chave = os.path.normcase(os.path.abspath(c))
        except Exception:
            return
        if chave not in vistos and os.path.isdir(c):
            vistos.add(chave)
            saida.append(c)

    _mais(pasta_temporaria_local(marcar_ambiente=False))
    try:
        _mais(tempfile.gettempdir())
    except Exception:
        pass
    if not (os.environ.get("RADAI_TMP") or "").strip():
        try:
            for c in candidatos_temporarios():
                _mais(c)
        except Exception:
            pass
    return saida


def _marcar_ambiente(caminho):
    import tempfile
    # GUARDA: o %TEMP% do usuario fica guardado; o perfil da janela do
    # navegador mora nele (radai_pulso.perfil_da_janela).
    original = os.environ.get("TEMP") or os.environ.get("TMP")
    if original and not os.environ.get("RADAI_TEMP_DO_USUARIO"):
        os.environ["RADAI_TEMP_DO_USUARIO"] = original
    for k in ("TMPDIR", "TEMP", "TMP"):
        os.environ[k] = caminho
    tempfile.tempdir = None


import threading as _threading

_EM_USO = set()
_EM_USO_TRAVA = _threading.Lock()

TETO_DA_BUSCA_EM_USO = 20000


def _normal(caminho):
    return os.path.normcase(os.path.abspath(str(caminho)))


def marcar_em_uso(caminho):
    with _EM_USO_TRAVA:
        _EM_USO.add(_normal(caminho))


def soltar_em_uso(caminho):
    with _EM_USO_TRAVA:
        _EM_USO.discard(_normal(caminho))


def _dentro(filho, pai):
    try:
        f, p = _normal(filho), _normal(pai)
        return f == p or f.startswith(p.rstrip(os.sep) + os.sep)
    except Exception:
        return False


PREFIXO_DA_EXTRACAO = "radai_portal_"


def nome_da_extracao_do_zip(caminho_zip):
    try:
        import hashlib
        caminho = str(caminho_zip)
        st = os.stat(caminho)
        chave = (os.path.abspath(caminho), int(st.st_mtime), st.st_size)
        return PREFIXO_DA_EXTRACAO + hashlib.sha1(
            ("%s|%d|%d" % chave).encode("utf-8")).hexdigest()[:12]
    except Exception:
        return ""


def pasta_da_extracao_do_zip(caminho_zip, temp=None):
    nome = nome_da_extracao_do_zip(caminho_zip)
    if not nome:
        return ""
    import tempfile
    return os.path.join(temp or tempfile.gettempdir(), nome)


def _pastas_da_fila_pendente():
    import sys as _sys
    fila = _sys.modules.get("radai_queue_state")
    if fila is None:
        return []
    try:
        cards = fila.cards()
    except Exception:
        return []
    vivos = []
    for c in cards or ():
        if not isinstance(c, dict):
            continue
        if str(c.get("estado") or "") not in ("esperando", "rodando"):
            continue
        carga = c.get("carga") or {}
        if not isinstance(carga, dict):
            carga = {}
        for v in (c.get("pasta"), carga.get("pasta")):
            if v and os.path.isabs(str(v)):
                vivos.append(str(v))
        zip_ = carga.get("zip") or c.get("zip")
        if zip_:
            vivos.append(str(zip_))
            extracao = pasta_da_extracao_do_zip(zip_)
            if extracao:
                vivos.append(extracao)
    return vivos


def _e_a_mesma_extracao(pendente, caminho):
    try:
        a = os.path.basename(_normal(pendente))
        return (a.startswith(PREFIXO_DA_EXTRACAO)
                and a == os.path.basename(_normal(caminho)))
    except Exception:
        return False


def mudou_depois(caminho, corte, teto=None):
    teto = int(teto or TETO_DA_BUSCA_EM_USO)
    try:
        if os.path.getmtime(str(caminho)) > corte:
            return True
        if not os.path.isdir(str(caminho)):
            return False
        vistos = 0
        for raiz, dirs, arqs in os.walk(str(caminho)):
            for n in list(dirs) + list(arqs):
                vistos += 1
                if vistos > teto:
                    return True
                try:
                    if os.path.getmtime(os.path.join(raiz, n)) > corte:
                        return True
                except OSError:
                    continue
        return False
    except Exception:
        return True


def pasta_temporaria_em_uso(caminho, idade_h):
    import time as _t
    with _EM_USO_TRAVA:
        declarados = list(_EM_USO)
    for d in declarados:
        if _dentro(d, caminho) or _dentro(caminho, d):
            return True, u"declarada em uso por este processo"
    for p in _pastas_da_fila_pendente():
        if _dentro(p, caminho) or _e_a_mesma_extracao(p, caminho):
            return True, u"uma serie da fila que ainda vai rodar esta dentro dela"
    if mudou_depois(caminho, _t.time() - float(idade_h) * 3600.0):
        return True, u"algo dentro dela mudou ha menos de %g h" % float(idade_h)
    return False, u""


TETO_DA_FAXINA_S = 2.0


def _tirar_somente_leitura(func, caminho, _exc):
    import stat
    os.chmod(caminho, stat.S_IWRITE)
    func(caminho)


def apagar_arvore(caminho):
    import shutil
    import sys
    if sys.version_info >= (3, 12):
        shutil.rmtree(str(caminho), onexc=_tirar_somente_leitura)
    else:
        shutil.rmtree(str(caminho), onerror=_tirar_somente_leitura)


def limpar_temporaria(caminho=None, idade_h=6, teto_s=None, relogio=None):
    import stat
    import time as _t
    relogio = relogio or _t.monotonic
    teto = TETO_DA_FAXINA_S if teto_s is None else float(teto_s)
    fim = relogio() + teto
    raizes = [caminho] if caminho else raizes_temporarias()
    apagados, erros = 0, 0
    corte = _t.time() - (idade_h * 3600.0)
    filhos = []
    for raiz in raizes:
        try:
            filhos.extend(Path(raiz).iterdir())
        except Exception:
            pass
    for f in filhos:
        nome = f.name
        if not (nome.startswith("radai_") or nome.startswith("_radai")):
            continue
        # GUARDA: a faxina roda antes de cada serie do lote; o que passa do teto fica para a proxima.
        if relogio() >= fim:
            break
        try:
            if f.stat().st_mtime > corte:
                continue
            if pasta_temporaria_em_uso(f, idade_h)[0]:
                continue
            if f.is_dir():
                apagar_arvore(f)
            else:
                try:
                    f.unlink()
                except PermissionError:
                    os.chmod(str(f), stat.S_IWRITE)
                    f.unlink()
            apagados += 1
        except Exception:
            erros += 1
    return apagados, erros


NOME_DA_TEMPORARIA = "tmp"
RAIZ_DE_DADOS = "RADIOTERAPIA_AI"
_SISTEMAS_LOCAIS = ("NTFS", "REFS")
_AMBIENTE_ORIGINAL = dict((k, os.environ.get(k)) for k in ("TEMP", "TMP", "TMPDIR"))


def _e_rede(caminho):
    c = str(caminho).replace("/", "\\")
    if c.startswith("\\\\"):
        return not c.startswith("\\\\?\\") or c.upper().startswith("\\\\?\\UNC\\")
    if os.name != "nt":
        return False
    try:
        import ctypes
        raiz = os.path.splitdrive(os.path.abspath(c))[0] + "\\"
        return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(raiz)) == 4
    except Exception:
        return False


_BARRAMENTOS_EXTERNOS = (7, 4, 12, 13)


def _unidade_externa(raiz):
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.CreateFileW.restype = wintypes.HANDLE
        h = k32.CreateFileW(u"\\\\.\\%s" % raiz.rstrip(u"\\/"), 0, 3, None,
                            3, 0, None)
        if h in (None, wintypes.HANDLE(-1).value):
            return None
        try:
            consulta = (ctypes.c_ulong * 3)(0, 0, 0)
            saida = ctypes.create_string_buffer(1024)
            lidos = wintypes.DWORD(0)
            ok = k32.DeviceIoControl(wintypes.HANDLE(h), 0x2D1400,
                                     consulta, ctypes.sizeof(consulta), saida,
                                     ctypes.sizeof(saida),
                                     ctypes.byref(lidos), None)
            if not ok or lidos.value < 32:
                return None
            removivel = bool(saida.raw[10])
            barramento = int.from_bytes(saida.raw[28:32], "little")
            return removivel or barramento in _BARRAMENTOS_EXTERNOS
        finally:
            k32.CloseHandle(wintypes.HANDLE(h))
    except Exception:
        return None


def _unidades_locais(e_externa=None):
    if os.name != "nt":
        return []
    if e_externa is None:
        e_externa = _unidade_externa
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        mapa = k32.GetLogicalDrives()
    except Exception:
        return []
    saida = []
    for i in range(26):
        if not mapa & (1 << i):
            continue
        raiz = u"%s:\\" % chr(65 + i)
        try:
            if k32.GetDriveTypeW(ctypes.c_wchar_p(raiz)) != 3:
                continue
            fs = ctypes.create_unicode_buffer(64)
            ok = k32.GetVolumeInformationW(ctypes.c_wchar_p(raiz), None, 0,
                                           None, None, None, fs, 64)
            if not ok or fs.value.upper() not in _SISTEMAS_LOCAIS:
                continue
            # GUARDA: HD externo USB aparece como FIXED; se sair no meio da
            # serie, a serie cai.
            if e_externa(raiz):
                continue
            saida.append(raiz)
        except Exception:
            continue
    return saida


def _livre_gb(caminho):
    import shutil
    p = os.path.abspath(str(caminho))
    for _ in range(64):
        if os.path.exists(p):
            try:
                return shutil.disk_usage(p).free / 1e9
            except Exception:
                return None
        pai = os.path.dirname(p)
        if pai == p:
            break
        p = pai
    return None


def candidatos_temporarios():
    import tempfile
    vistos, saida = set(), []

    def _mais(c):
        chave = os.path.normcase(os.path.abspath(str(c)))
        if chave not in vistos:
            vistos.add(chave)
            saida.append(str(c))

    v = (os.environ.get("RADAI_RAIZ_INSTALACAO") or "").strip()
    if v:
        _mais(Path(v) / NOME_DA_TEMPORARIA)
    try:
        _mais(Path(__file__).resolve().parent.parent / NOME_DA_TEMPORARIA)
    except Exception:
        pass
    try:
        _mais(_temp_do_sistema())
    except Exception:
        pass
    for raiz in _unidades_locais():
        _mais(Path(raiz) / RAIZ_DE_DADOS / NOME_DA_TEMPORARIA)
    return saida


def _temp_do_sistema():
    import tempfile
    for k in ("TEMP", "TMP", "TMPDIR"):
        v = _AMBIENTE_ORIGINAL.get(k)
        if v:
            return v
    return tempfile.gettempdir()


def _provar_escrita(cand):
    try:
        cand = Path(str(cand))
        cand.mkdir(parents=True, exist_ok=True)
        teste = cand / ".radai_escrita"
        teste.write_text("ok", encoding="ascii")
        teste.unlink()
        return True
    except Exception:
        return False


def escolher_temporaria(candidatos, livre=None, sincroniza=None, provar=None):
    livre = livre or _livre_gb
    provar = provar or _provar_escrita
    if sincroniza is None:
        def sincroniza(c):
            return em_pasta_sincronizada(str(c))[0]
    medidos = []
    for ordem, c in enumerate(candidatos):
        try:
            if _e_rede(c) or sincroniza(c):
                continue
        except Exception:
            continue
        gb = livre(c)
        if gb is None:
            continue
        medidos.append((-float(gb), ordem, c))
    for _gb, _ordem, c in sorted(medidos):
        if provar(c):
            return str(c)
    return None


PREFIXO_DA_SERIE = "radai_serie_"
_DA_SERIE = _threading.local()
_DESVIO = {"instalado": False, "mkdtemp": None, "mkstemp": None}
_DESVIO_TRAVA = _threading.Lock()


def pasta_da_serie_atual():
    return getattr(_DA_SERIE, "pasta", None)


def _instalar_desvio():
    import tempfile
    with _DESVIO_TRAVA:
        if _DESVIO["instalado"]:
            return
        mkdtemp_de_antes, mkstemp_de_antes = tempfile.mkdtemp, tempfile.mkstemp

        def mkdtemp(suffix=None, prefix=None, dir=None):
            if dir is None:
                dir = pasta_da_serie_atual()
                if dir is not None and (isinstance(prefix, bytes)
                                        or isinstance(suffix, bytes)):
                    dir = os.fsencode(dir)
            return mkdtemp_de_antes(suffix, prefix, dir)

        def mkstemp(suffix=None, prefix=None, dir=None, text=False):
            if dir is None:
                dir = pasta_da_serie_atual()
                # GUARDA: o scipy pede prefixo bytes; o dir injetado precisa do mesmo tipo.
                if dir is not None and (isinstance(prefix, bytes)
                                        or isinstance(suffix, bytes)):
                    dir = os.fsencode(dir)
            return mkstemp_de_antes(suffix, prefix, dir, text)

        # GUARDA: o desvio so age na thread com a serie aberta; nas outras e o
        # tempfile de sempre (duas series em paralelo nao se misturam).
        tempfile.mkdtemp = mkdtemp
        tempfile.mkstemp = mkstemp
        _DESVIO.update({"instalado": True, "mkdtemp": mkdtemp_de_antes,
                        "mkstemp": mkstemp_de_antes})


class TemporariaDaSerie(object):

    def __init__(self):
        self.pasta = None
        self.apagada = False
        self._dona = False

    def abrir(self):
        atual = pasta_da_serie_atual()
        if atual:
            self.pasta = atual
            return atual
        _instalar_desvio()
        self.pasta = _DESVIO["mkdtemp"](prefix=PREFIXO_DA_SERIE)
        marcar_em_uso(self.pasta)
        _DA_SERIE.pasta = self.pasta
        self._dona = True
        return self.pasta

    def fechar(self):
        if not self._dona or not self.pasta:
            return False
        import shutil
        _DA_SERIE.pasta = None
        self._dona = False
        shutil.rmtree(self.pasta, ignore_errors=True)
        soltar_em_uso(self.pasta)
        self.apagada = not os.path.exists(self.pasta)
        return self.apagada

    def __enter__(self):
        self.abrir()
        return self

    def __exit__(self, *_exc):
        self.fechar()
        return False


def ambiente_da_serie(env=None):
    saida = dict(os.environ if env is None else env)
    p = pasta_da_serie_atual()
    if p:
        for k in ("TEMP", "TMP", "TMPDIR"):
            saida[k] = p
    return saida


class TemporarioCurto(RuntimeError):
    pass


class DestinoSemEscrita(RuntimeError):
    pass


VEZES_O_TAMANHO_DA_SERIE = 3.0
GB_POR_SERIE = 0.5
GB_POR_TASK = 1.5
GB_FOLGA = 5.0


def espaco_da_serie_gb(bytes_da_serie, n_tasks=1):
    copia = VEZES_O_TAMANHO_DA_SERIE * float(bytes_da_serie or 0) / 1e9
    # GUARDA: uma task em voo por vez; `n_tasks` nao multiplica.
    return GB_FOLGA + max(GB_POR_SERIE, copia) + GB_POR_TASK


def conferir_espaco_da_serie(arquivos, pasta=None, n_tasks=1):
    import tempfile
    total = 0
    for a in arquivos or ():
        try:
            total += os.path.getsize(str(a))
        except OSError:
            continue
    precisa = espaco_da_serie_gb(total, n_tasks)
    alvo = pasta or pasta_da_serie_atual() or tempfile.gettempdir()
    livre = _livre_gb(alvo)
    if livre is not None and livre < precisa:
        raise TemporarioCurto(
            u"adiada: o temporario tem %.1f GB livres e a serie pede ~%.1f GB "
            u"(a copia local e o volume de cada task). Libere "
            u"espaco no disco; nada foi gravado" % (livre, precisa))
    return precisa, livre


def conferir_escrita_no_destino(pasta, subir=False):
    pasta = str(pasta)
    if subir:
        while not os.path.isdir(pasta):
            pai = os.path.dirname(pasta)
            if pai == pasta:
                break
            pasta = pai
    nome = os.path.join(pasta, ".radai_escrita_%d_%d"
                        % (os.getpid(), _threading.get_ident()))
    criado = False
    try:
        fd = os.open(nome, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        criado = True
        try:
            os.write(fd, b"ok")
        finally:
            os.close(fd)
        os.remove(nome)
        criado = False
    except OSError as e:
        if criado:
            try:
                os.remove(nome)
            except OSError:
                pass
        raise DestinoSemEscrita(
            u"nao consigo gravar na pasta da serie (%s): o RTSTRUCT nao teria "
            u"onde ser entregue. Confira a permissao de escrita; nada foi "
            u"processado" % (e.strerror or type(e).__name__))
