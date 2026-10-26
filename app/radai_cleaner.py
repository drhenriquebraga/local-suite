# -*- coding: utf-8 -*-
import os
import re
import subprocess
import sys

VERSAO_LIMPADOR = "1.0"

PROTEGIDOS = (
    "vitrea", "varian", "eclipse", "aria", "velocity", "vmsdbd", "vmsfs",
    "somavision", "dicomdb",
    "elekta", "mosaiq", "monaco", "xio", "focal", "impac", "clinac",
    "pinnacle", "oncentra", "iplan", "brainlab", "precision", "tomotherapy",
    "accuray", "raystation", "raycare", "raysearch", "limbus", "autocontour",
    "radioterapia", "radai", "totalsegmentator",
    "system", "registry", "smss", "csrss", "wininit", "winlogon", "services",
    "lsass", "svchost", "fontdrvhost", "dwm", "sihost", "ctfmon",
    "explorer", "runtimebroker", "shellexperiencehost", "searchhost",
    "startmenuexperiencehost", "textinputhost", "audiodg", "conhost",
    "memory compression", "idle",
    "msmpeng", "mssense", "sensecncproxy", "windefend", "sophos", "crowdstrike",
    "carbonblack", "mcafee", "symantec", "trendmicro", "sentinel",
    "ntrtscan", "tmlisten", "tmccsf", "pccntmon", "tmpfw", "dsasvc",
    "qualys", "netskope", "stagent", "secureconnector", "forescout",
    "ccmexec", "cmrcservice",
    "csfalcon",
)

def _protegido(nome):
    n = str(nome or "").lower()
    return any(p in n for p in PROTEGIDOS)


def _rodar(args, timeout=25):
    try:
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = 0x08000000
        p = subprocess.run(args, capture_output=True, timeout=timeout, **kw)
        bruto = (p.stdout or b"") + (p.stderr or b"")
        for cod in ("cp850", "cp1252", "utf-8"):
            try:
                return p.returncode == 0, bruto.decode(cod)
            except Exception:
                continue
        return p.returncode == 0, bruto.decode("cp850", errors="replace")
    except Exception as e:
        return False, u"%s: %s" % (type(e).__name__, e)


def memoria_da_estacao():
    fora = {"total_mb": 0, "livre_mb": 0, "usada_mb": 0, "pct": 0,
            "commit_total_mb": 0, "commit_livre_mb": 0}
    try:
        import ctypes

        class _MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        m = _MS()
        m.dwLength = ctypes.sizeof(_MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        fora["total_mb"] = int(m.ullTotalPhys / (1024 * 1024))
        fora["livre_mb"] = int(m.ullAvailPhys / (1024 * 1024))
        fora["usada_mb"] = fora["total_mb"] - fora["livre_mb"]
        fora["pct"] = int(m.dwMemoryLoad)
        fora["commit_total_mb"] = int(m.ullTotalPageFile / (1024 * 1024))
        fora["commit_livre_mb"] = int(m.ullAvailPageFile / (1024 * 1024))
    except Exception:
        pass
    try:
        teto = teto_do_commit_mb(
            fora["total_mb"], _arquivos_de_paginacao(),
            atual_mb=fora["commit_total_mb"] - fora["total_mb"])
        if teto and teto > fora["commit_total_mb"] > 0:
            fora["commit_teto_mb"] = teto
            fora["commit_livre_no_teto_mb"] = (
                fora["commit_livre_mb"] + teto - fora["commit_total_mb"])
    except Exception:
        pass
    return fora


def _arquivos_de_paginacao():
    if os.name != "nt":
        return []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session "
                            r"Manager\Memory Management") as k:
            v, _t = winreg.QueryValueEx(k, "PagingFiles")
        return [str(x) for x in (v if isinstance(v, (list, tuple)) else [v])
                if str(x).strip()]
    except Exception:
        return []


def teto_do_commit_mb(ram_mb, linhas, livre_mb=None, atual_mb=0):
    if not ram_mb or not linhas:
        return None
    livre_mb = livre_mb or _livre_do_disco_mb
    atual = int(atual_mb or 0) if len(linhas) == 1 else 0
    total = 0
    for linha in linhas:
        partes = str(linha).split()
        if not partes:
            continue
        caminho = partes[0]
        try:
            minimo, maximo = int(partes[1]), int(partes[2])
        except (IndexError, ValueError):
            minimo, maximo = 0, 0
        if caminho.startswith("?:") or (minimo == 0 and maximo == 0):
            disco = (os.environ.get("SystemDrive") or "C:") \
                if caminho.startswith("?:") else caminho[:2]
            maximo = 3 * int(ram_mb)
            livre = livre_mb(disco)
            if livre is not None:
                maximo = min(maximo, int(livre) + max(0, atual))
        total += max(0, maximo)
    return int(ram_mb) + total if total else None


def _livre_do_disco_mb(disco):
    try:
        import shutil
        return shutil.disk_usage(disco + "\\").free / (1024 * 1024)
    except Exception:
        return None


def memoria_do_processo_mb(pid=None):
    try:
        import ctypes
        from ctypes import wintypes

        class _PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                    wintypes.DWORD]
        try:
            f = k32.K32GetProcessMemoryInfo
        except AttributeError:
            f = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        f.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PMC), wintypes.DWORD]
        f.restype = wintypes.BOOL
        aberto = None
        if pid is None or int(pid) == os.getpid():
            h = k32.GetCurrentProcess()
        else:
            aberto = h = k32.OpenProcess(0x1000 | 0x0010, False, int(pid))
            if not h:
                return None
        try:
            p = _PMC()
            p.cb = ctypes.sizeof(_PMC)
            if f(h, ctypes.byref(p), p.cb):
                return int(p.WorkingSetSize // (1024 * 1024))
        finally:
            if aberto:
                k32.CloseHandle(aberto)
    except Exception:
        return None
    return None


PISO_MB = 300


def aplicacoes_pesadas(piso_mb=PISO_MB, limite=12):
    ok, saida = _rodar(
        ["tasklist", "/fo", "csv", "/nh"], timeout=30)
    if not ok or not saida.strip():
        return []
    por_nome = {}
    for linha in saida.splitlines():
        partes = [c.strip('" ') for c in linha.split('","')]
        if len(partes) < 5:
            continue
        nome = partes[0].strip('"')
        if not nome or _protegido(nome):
            continue
        bruto = partes[4].strip('"').replace(".", "").replace(",", "")
        digitos = "".join(c for c in bruto if c.isdigit())
        if not digitos:
            continue
        kb = int(digitos)
        d = por_nome.setdefault(nome, {"nome": nome, "kb": 0, "n": 0})
        d["kb"] += kb
        d["n"] += 1
    fora = []
    for d in por_nome.values():
        mb = int(d["kb"] / 1024)
        if mb < int(piso_mb):
            continue
        fora.append({"nome": d["nome"], "memoria_mb": mb, "instancias": d["n"]})
    fora.sort(key=lambda x: -x["memoria_mb"])
    return fora[:int(limite)]


from radai_archive import GB_POR_SERIE, GB_POR_TASK, GB_FOLGA


def disco_necessario_gb(n_series=1, n_tasks=1):
    n_series = max(1, int(n_series or 1))
    # GUARDA: as tasks rodam em serie e cada uma apaga a sua pasta: o pico e
    # UMA task em voo, e nao a soma das pedidas.
    return GB_FOLGA + (min(2, n_series) * GB_POR_SERIE) + GB_POR_TASK


def espaco_em_disco(caminhos=None, n_series=1, n_tasks=1):
    preciso = disco_necessario_gb(n_series, n_tasks)
    import shutil
    import tempfile
    alvos = list(caminhos or [])
    if not alvos:
        alvos = [tempfile.gettempdir(), os.path.dirname(os.path.abspath(__file__))]
    vistas, fora = set(), []
    for c in alvos:
        try:
            u = os.path.splitdrive(os.path.abspath(c))[0].upper() or c
            if u in vistas:
                continue
            vistas.add(u)
            t, _usado, livre = shutil.disk_usage(c)
            fora.append({"unidade": u, "livre_gb": round(livre / 1e9, 1),
                         "total_gb": round(t / 1e9, 1),
                         "preciso_gb": round(preciso, 1),
                         "aperta": (livre / 1e9) < preciso})
        except Exception:
            continue
    return fora


def ganhos_de_velocidade(device=""):
    fora = []

    tem_gpu, nome_gpu = _tem_gpu()
    dev = str(device or "").strip().lower() or "auto"
    usando_cpu = dev == "cpu"
    if tem_gpu and not usando_cpu:
        tr = _torch_do_arranque()
        if tr and tr.get("importa") and tr.get("disponivel") is False:
            fora.append({
                "chave": "gpu", "peso": 1,
                "rotulo": u"A GPU existe e o torch não a alcança",
                "ganho": u"uma a duas ordens de grandeza",
                "detalhe": (u"Esta máquina tem %s, e o torch deste Python não "
                            u"a alcança (torch %s, CUDA %s): o processamento "
                            u"vai para a CPU. O caso mais comum é o driver da "
                            u"placa mais velho que o CUDA do torch — "
                            u"atualizá-lo é com o TI."
                            % (nome_gpu or u"GPU NVIDIA",
                               tr.get("versao") or u"?",
                               tr.get("cuda") or u"?")),
                "onde": u"o bloco de diagnóstico do arranque (linha «Driver»)"})
    elif tem_gpu and usando_cpu:
        fora.append({
            "chave": "gpu", "peso": 1, "rotulo": u"Usar a GPU desta estação",
            "ganho": u"uma a duas ordens de grandeza",
            "detalhe": (u"Esta máquina tem %s, e o processamento está "
                        u"configurado para CPU. É de longe o maior ganho "
                        u"possível — maior que tudo o mais desta tela "
                        u"somado." % (nome_gpu or u"GPU")),
            "onde": u"Configurações → o campo DEVICE"})
    elif not tem_gpu:
        outras = [p for p in _placas_do_windows()
                  if p.get("vendor") not in ("nvidia", "microsoft", "vmware",
                                             "virtual", "parallels",
                                             "virtualbox")]
        if outras:
            nomes = u", ".join(p.get("nome") or u"?" for p in outras)
            abre = (u"Esta estação tem %s, que o TotalSegmentator não usa: "
                    u"só placa NVIDIA roda a rede neste pacote." % nomes)
        else:
            abre = u"Não achei GPU NVIDIA aqui."
        fora.append({
            "chave": "gpu", "peso": 1,
            "rotulo": (u"Sem GPU NVIDIA nesta estação" if outras
                       else u"Sem GPU nesta estação"),
            "ganho": u"—",
            "detalhe": (abre + u" Na CPU, conte ~1,1 min "
                        u"por milhão de voxels no espaço do modelo: uma TC de "
                        u"planejamento de corpo inteiro leva perto de 40 min "
                        u"só na task `total`."),
            "placas": [p.get("nome") for p in outras],
            "onde": u""})

    plano = _plano_de_energia()
    if plano and u"economia" in plano.lower():
        fora.append({
            "chave": "energia", "peso": 2,
            "rotulo": u"Plano de energia em «%s»" % plano,
            "ganho": u"dezenas de por cento na CPU",
            "detalhe": (u"O plano de economia limita o clock do processador. "
                        u"Numa inferência de 40 minutos isso é tempo de "
                        u"parede, não teoria."),
            "onde": u"Painel de Controle → Opções de Energia"})
    return fora


def _tem_gpu():
    try:
        import radai_devices
        r = radai_devices.placas_nvidia(timeout=12)
        if r.get("placas"):
            return True, (r["placas"][0].get("nome") or u"").strip()
        return False, ""
    except Exception:
        ok, saida = _rodar(["nvidia-smi", "--query-gpu=name",
                            "--format=csv,noheader"], timeout=12)
        if ok and saida.strip():
            return True, saida.strip().splitlines()[0].strip()
        return False, ""


def _placas_do_windows():
    try:
        import radai_devices
        return list(radai_devices.placas_rapidas() or [])
    except Exception:
        return []


def _torch_do_arranque():
    try:
        import radai_arranque
        return dict(radai_arranque.ULTIMO.get("torch") or {}) or None
    except Exception:
        return None


def _device_do_config():
    try:
        import radai_config
        return (radai_config.chave_configurada("DEVICE") or "auto").strip() \
            or "auto"
    except Exception:
        return "auto"


def _plano_de_energia():
    ok, saida = _rodar(["powercfg", "/getactivescheme"], timeout=12)
    if not ok:
        return ""
    m = re.search(r"\(([^)]+)\)", saida)
    return m.group(1).strip() if m else ""


def laudo(device=None):
    if device is None:
        device = _device_do_config()
    mem = memoria_da_estacao()
    return {
        "versao": VERSAO_LIMPADOR,
        "memoria": mem,
        "aplicacoes": aplicacoes_pesadas(),
        "piso_mb": PISO_MB,
        "disco": espaco_em_disco(),
        "ganhos": ganhos_de_velocidade(device),
        "device": device,
    }


MARCA_ECOSSISTEMA = "RADIOTERAPIA_AI"

NOME_EM_USO = "em_uso.json"
APP_EM_USO = "radioterapia-ai-local-suite"
VERSAO_EM_USO = 1
RENOVAR_EM_USO_S = 60
JANELA_DO_KIT_S = 300
RENOVACOES_NA_JANELA = 3

_LANCADORES = ("cmd", "py", "pyw", "python", "pythonw")


def nome_do_processo(exe):
    n = os.path.basename(str(exe or u"").strip())
    return n[:-4] if n.lower().endswith(u".exe") else n


def processos():
    if os.name != "nt":
        return []
    try:
        return _processos_nt()
    except Exception:
        return []


def _processos_nt():
    import ctypes
    from ctypes import wintypes as W

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _PE(ctypes.Structure):
        _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD),
                    ("th32ProcessID", W.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", W.DWORD), ("cntThreads", W.DWORD),
                    ("th32ParentProcessID", W.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", W.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    k32.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    k32.CreateToolhelp32Snapshot.restype = W.HANDLE
    k32.Process32FirstW.argtypes = [W.HANDLE, ctypes.POINTER(_PE)]
    k32.Process32FirstW.restype = W.BOOL
    k32.Process32NextW.argtypes = [W.HANDLE, ctypes.POINTER(_PE)]
    k32.Process32NextW.restype = W.BOOL
    k32.CloseHandle.argtypes = [W.HANDLE]
    k32.CloseHandle.restype = W.BOOL

    INVALIDO = ctypes.c_void_p(-1).value
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)
    if not snap or snap == INVALIDO:
        return []
    fora = []
    try:
        pe = _PE()
        pe.dwSize = ctypes.sizeof(_PE)
        ok = k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            exe = str(pe.szExeFile)
            fora.append({"pid": int(pe.th32ProcessID),
                         "ppid": int(pe.th32ParentProcessID), "exe": exe,
                         "nome": nome_do_processo(exe)})
            ok = k32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    return fora


def arvore_do_app(procs, pid_app=None, max_subida=8):
    try:
        pid_app = os.getpid() if pid_app is None else int(pid_app)
        por_pid = dict((int(p["pid"]), p) for p in procs or ())
        raizes, vistos = [pid_app], {pid_app}
        atual, n = por_pid.get(pid_app), 0
        while atual is not None and n < int(max_subida):
            pai = por_pid.get(int(atual.get("ppid") or 0))
            if pai is None or int(pai["pid"]) in vistos or int(pai["pid"]) <= 4:
                break
            nm = str(pai.get("nome") or u"").lower()
            if nm not in _LANCADORES:
                break
            raizes.append(int(pai["pid"]))
            vistos.add(int(pai["pid"]))
            if nm == u"cmd":
                avo = por_pid.get(int(pai.get("ppid") or 0))
                if avo is None or str(avo.get("nome") or u"").lower() != u"cmd":
                    break
            atual, n = pai, n + 1
        filhos = {}
        for p in por_pid.values():
            filhos.setdefault(int(p.get("ppid") or 0), []).append(int(p["pid"]))
        arvore, fila = set(raizes), list(raizes)
        while fila:
            x = fila.pop()
            for f in filhos.get(x, ()):
                if f not in arvore and f != x and f > 4:
                    arvore.add(f)
                    fila.append(f)
        return arvore
    except Exception:
        return {os.getpid() if pid_app is None else pid_app}


def pasta_de_estado():
    base = str(os.environ.get("LOCALAPPDATA") or u"").strip()
    return os.path.join(base, MARCA_ECOSSISTEMA) if base else u""


NOME_ESTADO_ANTIGO = "otimizar.json"


def apagar_estado_antigo_do_otimizar(log=None):
    d = pasta_de_estado()
    c = os.path.join(d, NOME_ESTADO_ANTIGO) if d else u""
    if not c or not os.path.isfile(c):
        return False
    try:
        os.remove(c)
    except Exception:
        return False
    if log:
        try:
            log(u"apagado o %s de uma versao anterior: os programas que o "
                u"Otimizar fechou voltam no proximo logon, e os servicos que "
                u"ele parou, no proximo arranque do Windows" % NOME_ESTADO_ANTIGO)
        except Exception:
            pass
    return True


def caminho_em_uso():
    d = pasta_de_estado()
    return os.path.join(d, NOME_EM_USO) if d else u""


def navegadores_conectados(porta, procs=None, saida_netstat=None):
    try:
        porta = int(porta or 0)
        if porta <= 0:
            return []
        if saida_netstat is None:
            ok, saida_netstat = _rodar(["netstat", "-ano"], timeout=20)
            if not ok:
                return []
        meus = set([os.getpid()])
        fora = set()
        alvos = ("127.0.0.1:%d" % porta, "[::1]:%d" % porta,
                 "localhost:%d" % porta)
        for linha in str(saida_netstat).splitlines():
            partes = linha.split()
            if len(partes) < 4 or partes[0].upper() != "TCP":
                continue
            local, remoto, pid = partes[1], partes[2], partes[-1]
            if remoto.lower() not in alvos or local.lower() in alvos:
                continue
            if not pid.isdigit() or int(pid) <= 4 or int(pid) in meus:
                continue
            fora.add(int(pid))
        if fora and procs:
            por_pid = dict((int(p["pid"]), p) for p in procs)
            for pid in list(fora):
                atual = por_pid.get(pid)
                n = 0
                while atual is not None and n < 6:
                    pai = por_pid.get(int(atual.get("ppid") or 0))
                    if (pai is None or str(pai.get("nome") or u"").lower()
                            != str(atual.get("nome") or u"").lower()):
                        break
                    fora.add(int(pai["pid"]))
                    atual, n = pai, n + 1
        return sorted(fora)
    except Exception:
        return []


def conteudo_em_uso(porta, segmentando, pid_app=None, procs=None,
                    saida_netstat=None, agora=None):
    import datetime as _dt
    procs = processos() if procs is None else procs
    arvore = arvore_do_app(procs, pid_app)
    nav = navegadores_conectados(porta, procs=procs,
                                 saida_netstat=saida_netstat)
    quando = agora or _dt.datetime.now().astimezone()
    return {"versao": VERSAO_EM_USO, "app": APP_EM_USO,
            "atualizado": quando.isoformat(timespec="seconds"),
            "pids": sorted(set(int(x) for x in arvore) | set(nav)),
            "porta": int(porta or 0), "segmentando": bool(segmentando)}


def gravar_em_uso(porta, segmentando=False, pid_app=None, caminho=None,
                  procs=None, saida_netstat=None):
    import json
    try:
        c = caminho or caminho_em_uso()
        if not c:
            return False
        d = conteudo_em_uso(porta, segmentando, pid_app=pid_app, procs=procs,
                            saida_netstat=saida_netstat)
        os.makedirs(os.path.dirname(c), exist_ok=True)
        tmp = c + ".parcial"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, c)
        return True
    except Exception:
        return False


def apagar_em_uso(caminho=None):
    try:
        c = caminho or caminho_em_uso()
        if not c:
            return True
        if os.path.exists(c):
            os.remove(c)
        return not os.path.exists(c)
    except Exception:
        return False


def ler_em_uso(caminho=None):
    import json
    try:
        with open(caminho or caminho_em_uso(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def linhas_do_diagnostico(conferencia=None, laudo_=None, em_uso=None):
    L = []
    L.append(u"diagnostico: ---- começo ----")
    cf = conferencia or {}
    for s in cf.get("secoes") or ():
        for i in s.get("itens") or ():
            if i.get("nota"):
                continue
            marca = (u"ok" if i.get("ok") is True else
                     (u"FALTA" if (i.get("ok") is False and i.get("grave"))
                      else u"aviso"))
            L.append(u"diagnostico: [%s] %s — %s: %s"
                     % (marca, s.get("titulo") or u"", i.get("nome") or u"",
                        i.get("valor") or u""))
    r = cf.get("resumo") or {}
    if cf:
        L.append(u"diagnostico: instalação — %d em ordem, %d faltando, %d "
                 u"avisos" % (r.get("ok", 0), r.get("faltam", 0),
                              r.get("avisos", 0)))
    ld = laudo_ or {}
    m = ld.get("memoria") or {}
    if m.get("total_mb"):
        L.append(u"diagnostico: memória — %d MB livres de %d MB (%d%% em uso)"
                 % (m.get("livre_mb", 0), m.get("total_mb", 0),
                    m.get("pct", 0)))
    for u in ld.get("disco") or ():
        L.append(u"diagnostico: disco %s — %s GB livres de %s GB%s"
                 % (u.get("unidade"), u.get("livre_gb"), u.get("total_gb"),
                    u" (aperta para uma noite de lote)" if u.get("aperta")
                    else u""))
    for g in ld.get("ganhos") or ():
        L.append(u"diagnostico: velocidade — %s" % g.get("rotulo"))
    for a in ld.get("aplicacoes") or ():
        L.append(u"diagnostico: memória por programa — %s %d MB"
                 % (a.get("nome"), int(a.get("memoria_mb") or 0)))
    eu = em_uso or {}
    if eu:
        L.append(u"diagnostico: sinalização para o Workstation RT — %d PID(s) "
                 u"protegidos, atualizada em %s"
                 % (len(eu.get("pids") or ()), eu.get("atualizado") or u"?"))
    L.append(u"diagnostico: ---- fim ----")
    return L
