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

SERVICOS = (
    ("SysMain",
     u"SuperFetch — pré-carrega programas na RAM adivinhando o que você vai "
     u"abrir. Numa estação que vai usar toda a memória para segmentar, ele "
     u"disputa exatamente o que falta."),
    ("WSearch",
     u"Indexação do Windows — varre e indexa arquivos em segundo plano. Numa "
     u"estação apontada para uma pasta de exames, ele lê milhares de DICOM "
     u"sem necessidade nenhuma."),
    ("DiagTrack",
     u"Telemetria de diagnóstico da Microsoft. Não é usado por nada aqui."),
    ("dmwappushservice",
     u"Roteamento de mensagens WAP para gerência de dispositivo móvel. Uma "
     u"estação de trabalho não usa."),
    ("MapsBroker",
     u"Baixa mapas offline em segundo plano."),
    ("XblGameSave",
     u"Salvamento de jogos do Xbox Live."),
    ("WMPNetworkSvc",
     u"Compartilhamento de mídia do Windows Media Player pela rede."),
    ("Fax",
     u"Serviço de fax do Windows. Fax do serviço, se houver, é outro "
     u"programa — este é o do sistema operacional."),
    ("RetailDemo",
     u"Modo de demonstração de loja — usado por revendedor para exibir a "
     u"máquina na prateleira. Não tem função nenhuma numa estação instalada."),
    ("PcaSvc",
     u"Assistente de compatibilidade de programas — mostra o balão «este "
     u"programa pode não ter sido instalado corretamente»."),
)

_NOMES_SERVICOS = frozenset(n for n, _ in SERVICOS)


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


def estado_dos_servicos():
    fora = []
    for nome, porque in SERVICOS:
        fora.append({"nome": nome, "porque": porque,
                     "estado": _estado_do_servico(nome)})
    return fora


_ESTADOS = ((r"\bRUNNING\b", "rodando"),
            (r"\bSTOPPED\b", "parado"),
            (r"\bSTART_PENDING\b", "rodando"),
            (r"\bSTOP_PENDING\b", "parado"),
            (r"\bPAUSED\b", "parado"))


def _estado_do_servico(nome):
    ok, saida = _rodar(["sc", "query", str(nome)])
    for padrao, estado in _ESTADOS:
        if re.search(padrao, saida):
            return estado
    return "ausente"


def parar_servico(nome):
    nome = str(nome or "").strip()
    if nome not in _NOMES_SERVICOS:
        return {"ok": False,
                "msg": u"`%s` não está na lista de serviços que este programa "
                       u"pode parar. A lista é fechada de propósito." % nome[:40]}
    if _protegido(nome):
        return {"ok": False, "msg": u"`%s` está na lista de protegidos." % nome}
    ok, saida = _rodar(["sc", "stop", nome])
    if ok:
        return {"ok": True, "msg": u"%s: parado." % nome}
    baixa = saida.lower()
    if "1062" in saida or "not been started" in baixa or "nao foi iniciado" in baixa:
        return {"ok": True, "msg": u"%s: já estava parado." % nome}
    if "5" in saida and ("access is denied" in baixa or "acesso negado" in baixa):
        return {"ok": False,
                "msg": u"%s: o Windows negou. Este serviço precisa de "
                       u"administrador, e o programa roda sem." % nome}
    return {"ok": False, "msg": u"%s: não consegui parar (%s)"
                                % (nome, " ".join(saida.split())[:120])}


def iniciar_servico(nome):
    nome = str(nome or "").strip()
    if nome not in _NOMES_SERVICOS:
        return {"ok": False,
                "msg": u"`%s` não está na lista de serviços que este programa "
                       u"pode religar. A lista é fechada de propósito." % nome[:40]}
    if _protegido(nome):
        return {"ok": False, "msg": u"`%s` está na lista de protegidos." % nome}
    ok, saida = _rodar(["sc", "start", nome])
    if ok:
        return {"ok": True, "msg": u"%s: religado." % nome}
    baixa = saida.lower()
    if "1056" in saida or "already running" in baixa or "já está em execução" in baixa:
        return {"ok": True, "msg": u"%s: já estava rodando." % nome}
    if "1058" in saida or "disabled" in baixa or "desabilitado" in baixa:
        return {"ok": False,
                "msg": u"%s: está desabilitado nesta máquina. Só o TI religa, "
                       u"e este programa não mexe no tipo de inicialização." % nome}
    if "5" in saida and ("access is denied" in baixa or "acesso negado" in baixa):
        return {"ok": False,
                "msg": u"%s: o Windows negou. Este serviço precisa de "
                       u"administrador, e o programa roda sem. Ele volta "
                       u"sozinho no próximo arranque da estação." % nome}
    return {"ok": False, "msg": u"%s: não consegui religar (%s)"
                                % (nome, " ".join(saida.split())[:120])}


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


HORAS_TEMP = 6.0


def _tamanho_da_pasta(caminho, teto_itens=60000):
    total, n = 0, 0
    try:
        for raiz, dirs, arqs in os.walk(caminho):
            for a in arqs:
                try:
                    total += os.path.getsize(os.path.join(raiz, a))
                except OSError:
                    pass
                n += 1
                if n >= teto_itens:
                    return total, n
    except OSError:
        pass
    return total, n


def _mb(b):
    return int(b / (1024 * 1024))


def _idade_h(caminho):
    import time
    try:
        return (time.time() - os.path.getmtime(caminho)) / 3600.0
    except OSError:
        return 0.0


def _raizes_do_temp():
    import tempfile
    base = os.path.abspath(tempfile.gettempdir())
    saida = [(base, False)]
    try:
        import radai_archive as _arq
        for r in _arq.raizes_temporarias():
            r = os.path.abspath(r)
            if os.path.normcase(r) != os.path.normcase(base):
                saida.append((r, True))
    except Exception:
        pass
    return saida


def _temp_antigo():
    total, itens = 0, []
    candidatos = []
    for base, so_nossos in _raizes_do_temp():
        try:
            nomes = os.listdir(base)
        except OSError:
            continue
        for nome in nomes[:4000]:
            if so_nossos and not nome.lower().startswith(("radai_", "_radai")):
                continue
            candidatos.append((nome, os.path.join(base, nome)))
    for nome, p in candidatos:
        if _idade_h(p) < HORAS_TEMP:
            continue
        if _casa(WSRT_RAIZES_CLINICAS, p):
            continue
        if nome.lower().startswith(("radai_", "_radai")) and os.path.isdir(p):
            try:
                import radai_archive as _arq
                if _arq.pasta_temporaria_em_uso(p, HORAS_TEMP)[0]:
                    continue
            except Exception:
                continue
        try:
            if os.path.isdir(p):
                b, _ = _tamanho_da_pasta(p, teto_itens=4000)
            else:
                b = os.path.getsize(p)
        except OSError:
            continue
        total += b
        itens.append(p)
    return total, itens


def _pasta_do_usuario(*partes):
    base = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(base, *partes)


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


def espaco_recuperavel():
    itens = []

    b, lista = _temp_antigo()
    if b > 0:
        itens.append({
            "chave": "temp", "rotulo": u"Arquivos temporários do Windows",
            "mb": _mb(b), "apagavel": True, "sugerido": True,
            "n": len(lista),
            "porque": (u"Só o que tem mais de %d horas. O staging da série que "
                       u"está sendo processada AGORA fica de fora — apagá-lo "
                       u"mataria a segmentação no meio." % int(HORAS_TEMP))})

    pip = os.environ.get("LOCALAPPDATA") and os.path.join(
        os.environ["LOCALAPPDATA"], "pip", "Cache")
    if pip and os.path.isdir(pip):
        b, _ = _tamanho_da_pasta(pip)
        if b > 0:
            itens.append({
                "chave": "pip", "rotulo": u"Cache do pip (pacotes baixados)",
                "mb": _mb(b), "apagavel": True, "sugerido": True,
                "porque": (u"São cópias de instaladores de biblioteca. O "
                           u"programa já está instalado; isto só serve para "
                           u"reinstalar mais rápido, e ele volta sozinho.")})

    for chave, partes, rotulo, porque in (
            ("downloads", ("Downloads",), u"Pasta Downloads",
             u"Numa clínica é onde um estudo exportado aterrissa, e onde o "
             u"pacote do instalador fica guardado. O programa NÃO apaga: ele "
             u"mede e abre a pasta para você decidir."),
            ("lixeira", None, u"Lixeira",
             u"Arquivo na lixeira ainda é recuperável. Esvaziá-la é a última "
             u"chance indo embora, e essa decisão não é do programa.")):
        if chave == "lixeira":
            caminho = os.path.join(
                os.path.splitdrive(os.path.abspath(os.sep))[0] or "C:",
                os.sep, "$Recycle.Bin")
        else:
            caminho = _pasta_do_usuario(*partes)
        if not os.path.isdir(caminho):
            continue
        b, _ = _tamanho_da_pasta(caminho, teto_itens=20000)
        if b <= 0:
            continue
        itens.append({"chave": chave, "rotulo": rotulo, "mb": _mb(b),
                      "apagavel": False, "sugerido": False,
                      "caminho": caminho if chave != "lixeira" else "",
                      "porque": porque})

    itens.sort(key=lambda x: -x["mb"])
    return itens


_APAGAVEIS = ("temp", "pip")


def liberar(chave):
    import shutil
    import tempfile
    chave = str(chave or "").strip()
    if chave not in _APAGAVEIS:
        return {"ok": False, "mb": 0,
                "msg": u"`%s` não está na lista do que este programa pode "
                       u"apagar. Downloads e Lixeira são de quem usa a "
                       u"máquina — o programa mede e mostra, e você apaga."
                       % chave[:40]}

    apagados, erros, bytes_ = 0, 0, 0
    if chave == "temp":
        raizes = _raizes_do_temp()
        _b, lista = _temp_antigo()
        for p in lista:
            ap = os.path.abspath(p)
            if not any(os.path.dirname(ap) == r
                       and (not so or os.path.basename(ap).lower().startswith(
                           ("radai_", "_radai")))
                       for r, so in raizes):
                continue
            try:
                if os.path.isdir(p):
                    b, _ = _tamanho_da_pasta(p, teto_itens=4000)
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    b = os.path.getsize(p)
                    os.remove(p)
                bytes_ += b
                apagados += 1
            except Exception:
                erros += 1
    else:
        base = os.environ.get("LOCALAPPDATA") or ""
        alvo = os.path.join(base, "pip", "Cache")
        if not base or not os.path.isdir(alvo):
            return {"ok": True, "mb": 0, "msg": u"o cache do pip não existe "
                                                u"nesta máquina."}
        b, _ = _tamanho_da_pasta(alvo)
        try:
            shutil.rmtree(alvo, ignore_errors=True)
            bytes_, apagados = b, 1
        except Exception:
            erros += 1

    mb = _mb(bytes_)
    return {"ok": erros == 0 or apagados > 0, "mb": mb,
            "msg": (u"%s: %d MB liberados%s"
                    % (chave, mb,
                       (u" (%d em uso, não deu para apagar)" % erros)
                       if erros else u""))}


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
        "servicos": estado_dos_servicos(),
        "aplicacoes": aplicacoes_pesadas(),
        "piso_mb": PISO_MB,
        "disco": espaco_em_disco(),
        "recuperavel": espaco_recuperavel(),
        "ganhos": ganhos_de_velocidade(device),
        "device": device,
        "aviso": AVISO_DA_LISTA,
    }


AVISO_DA_LISTA = (u"A lista de aplicações por memória é só informação. O "
                  u"«Otimizar» fecha apenas o que casa com as listas fechadas "
                  u"e mostra antes o que vai fechar. Vitrea, Eclipse, ARIA, o "
                  u"navegador e o próprio Radioterapia.AI nunca são tocados.")



WSRT_PROTEGIDOS = (
    "wfica32", "wfcrun32", "CDViewer", "SelfService", "Receiver", "concentr",
    "CtxWebHelper", "AuthManSvr", "redirector", "HdxRtcEngine", "CtxCFRUI",
    "Citrix", "tasy", "TasyAgent", "CentBrowser", "javaw", "^java$",
    "jp2launcher", "Wheb", "Philips", "CcmExec", "ntrtscan", "tmlisten", "TMBM",
    "PccNTMon", "ShowMsg", "smartscreen", "unsecapp", "SearchProtocolHost",
    "SearchFilterHost", "DSASvc", "QualysAgent", "stAgent", "Cortex",
    "cyserver", "cytray", "cyvera", "traps", "LsAgent", "Quest", "OnDemand",
    "ODMActiveDirectory", "SecureConnector", "ARIA", "Eclipse", "Varian",
    "Vitrea", "MIM", "MOSAIQ", "RayStation", "Monaco", "Velocity", "Osirix",
    "Horos", "Weasis", "dicom", "PACS", "EXCEL", "WINWORD", "POWERPNT",
    "OUTLOOK", "MSACCESS", "onenote", "StickyNot", "msedge", "chrome",
    "firefox", "iexplore", "notepad", "wordpad", "Acrobat", "AcroRd32",
    "AnyConnect", "GlobalProtect", "FortiClient", "Pulse", "CcmExec",
    "CmRcService", "ccmsetup", "CSFalcon", "CSAgent", "Sophos", "SAVService",
    "^mfe", "masvc", "macmnsvc", "McShield", "ccSvcHst", "SepMaster", "ZSA",
    "stAgent", "nsdiag", "ivanti", "LANDesk", "Forcepoint", "splunk", "nxlog",
    "MsMpEng", "NisSrv", "SecurityHealth",
    "Acronis", "^mms$", "Veeam", "CommVault", "^cvd$", "^CvMountd$",
    "TrueImage", "Macrium", "^Reflect", "ShadowProtect", "Arcserve", "Datto",
    "Carbonite", "IDriveService",
    "Realtek", "RtkAud", "IDTNC",
    "Synaptics", "igfx", "nvcontainer", "audiodg", "System", "Idle",
    "Registry", "smss", "csrss", "wininit", "winlogon", "^services$", "lsass",
    "svchost", "fontdrvhost", "dwm", "explorer", "RuntimeBroker", "sihost",
    "ctfmon", "taskhostw", "dllhost", "conhost", "WmiPrvSE", "powershell",
    "pwsh", "LogonUI", "SearchIndexer",
)

WSRT_SESSAO_AUDIO = (
    "RAVBg", "RAVCpl", "RtkNGUI", "RtkAudUService", "RtHDVBg", "RtHDVCpl",
    "RtlUpd", "RealtekAudio", "WavesSvc", "WavesSysSvc", "WavesAudio",
    "MaxxAudio", "Nahimic", "A-Volute", "AudioCenter", "DolbyDAX", "DAX3API",
    "DolbyAudio", "DTSAPO", "DTSAudio", "SonicStudio", "SonicSuite",
    "SmartAudio", "CxAudMsg", "CxUIU", "LogiOptions", "LogiLDA", "Logitech",
    "iCUE", "SteelSeries", "CorsairService", "WebcamService", "CameraHelper",
    "YourPhoneCamera", "fsquirt", "BTTray", "BTStackServer",
    "BluetoothUserService", "IntelBluetooth", "btplayerctrl",
    "BluetoothHeadset", "BtwRSupportService",
)

WSRT_SESSAO_ENFEITES = (
    "Widgets", "WidgetService", "SearchHost", "SearchApp", "SearchUI",
    "StartMenuExperienceHost", "ShellExperienceHost", "ShellHost",
    "TaskViewHost", "MultitaskingViewHost", "TextInputHost", "FeedbackHub",
    "PilotshubApp", "GetHelp", r"Windows\.Feedback", "jusched", "jucheck",
    "JavaUpdate", "JavaCheck", "OneDriveStandaloneUpdater", "GoogleUpdate",
    "MicrosoftEdgeUpdate", "EdgeUpdate", "SCNotification", "UserOOBEBroker",
    "CompPkgSrv", "WindowsInternal", "LockApp", "SystemSettingsBroker",
)

WSRT_SESSAO_REMOTO = (
    "TeamViewer", "tv_w32", "tv_x64", "uvnc", "winvnc", "vncserver",
    "tvnserver", "ScreenConnect", "AnyDesk", "RustDesk", "CmRcService",
    "CmRcViewer", "RcAgent", "DameWare", "BeyondTrust", "bomgar", "LogMeIn",
    "LMIGuardian", "Splashtop", "ZohoAssist", "quickassist", "^msra$",
    "^mstsc$", "RdpClip", "rdpinit",
)

_WSRT_PRESERVAR_PROPRIA = (
    "wfica32", "wfcrun32", "CDViewer", "SelfService", "Receiver", "concentr",
    "CtxWebHelper", "AuthManSvr", "redirector", "HdxRtcEngine", "CtxCFRUI",
    "Citrix", "CentBrowser", "msedge", "chrome", "firefox", "iexplore",
    "opera", "vivaldi", "brave", "ssonsvr", r"Microsoft\.AAD", "AADBroker",
    "TokenBroker", "WindowsTerminal", "OpenConsole", "FortiTray",
    "FortiClient", "FortiSSLVPN", "Forti", "EXCEL", "WINWORD", "POWERPNT",
    "OUTLOOK", "MSACCESS", "^olk$", "onenote", "StickyNot", "javaw", "^java$",
    "jp2launcher", "Wheb", "tasy",
    "^Epic$", "EpicSystems", "Hyperspace", "PowerChart", "Cerner", "MEDITECH",
    "Soarian", "Sectra",
    "Vitrea", "Vsp", r"^VI\.", "Mirada",
    "Medis", "4DM", "Corridor", "NeuroQ", "Olea", "TomTec", "ARIA", "Eclipse",
    "Varian", "MOSAIQ", "Monaco", "MIM", "RayStation", "Velocity", "Onis",
    "Digitalcore", "dicom", "PACS", "sqlservr", "Tomcat", "catalina", "w3wp",
    "inetinfo", "MSMQ", "postgres", "mysqld", "oracle", "firebird",
    "^claude$", "^claude-code$",
)
WSRT_SESSAO_PRESERVAR = _WSRT_PRESERVAR_PROPRIA + WSRT_SESSAO_REMOTO

WSRT_RAIZES_CLINICAS = (
    "Vitrea", r"\\Patients\\", r"\\Patients$",
    r"\\radioterapia\\TC_DATA", "Mirada", "Medis", "INVIA", "Corridor4DM",
    "NeuroQ", "OleaSphere", "TomTec", r"\\ARIA", "MOSAIQ", "Monaco",
    "Eclipse", "RayStation", "Velocity", "VspApp", "VspMgmt", "Digitalcore",
    r"\\Onis",
)

WSRT_CATALOGO = (
    ("^OneDrive$|^FileCoAuth$", "Sempre", u"OneDrive (sincronismo)",
     u"Volta ao abrir o OneDrive ou no próximo logon."),
    ("^Teams$|^ms-teams$|^msteams", "Sempre", u"Microsoft Teams",
     u"As conversas ficam no servidor. Volta ao abrir."),
    ("Update$|Updater$|^GoogleUpdate|EdgeUpdate|^AdobeARM$|^AdobeGCClient$|"
     "^armsvc$|^jusched$|^SquirrelUpdate|^OfficeC2RClient$", "Sempre",
     u"Atualizadores automáticos",
     u"Voltam sozinhos quando houver atualização."),
    ("^CCXProcess$|^Creative Cloud|^CCLibrary|^AdobeIPCBroker$|"
     "^AdobeNotificationClient$", "Sempre", u"Adobe Creative Cloud (fundo)",
     u""),
    ("^GameBar|^XboxApp|^GamingServices|^XboxGame|^GameBarPresence", "Sempre",
     u"Xbox e Game Bar", u""),
    ("^NVIDIA Share$|^NVIDIA Web Helper", "Sempre", u"Sobreposição NVIDIA", u""),
    ("^YourPhone$|^PhoneExperienceHost$", "Sempre", u"Vincular ao telefone",
     u""),
    ("^Widgets$|^WidgetService$", "Sempre", u"Widgets do Windows", u""),
    ("^SearchApp$|^Cortana$|^Copilot", "Sempre", u"Pesquisa e Copilot",
     u"O Windows recarrega sozinho quando precisar."),
    ("^SupportAssist|^DellSupport|^HPSupport|^HPPrintScan|^Vantage|"
     "^ImController$|^McUICnt$|^HPNotifications", "Sempre",
     u"Assistentes do fabricante", u""),
    ("^iTunesHelper$|^AppleMobileDevice|^iPodService$", "Sempre",
     u"Serviços Apple", u""),
    ("^Spotify", "SemJanela", u"Spotify", u""),
    ("^Dropbox$|^Box$|^GoogleDriveFS$", "SemJanela", u"Nuvem pessoal",
     u"A sincronização para até ele voltar: o Restaurar reabre o Google "
     u"Drive."),
    ("^Zoom$|^Slack$|^Discord$|^Skype", "SemJanela", u"Comunicadores",
     u"Só é fechado sem janela aberta."),
    ("^Steam|^EpicGames", "SemJanela", u"Lojas de jogos", u""),
)

ORIGEM_WSRT = {
    "WSRT_PROTEGIDOS": ("$script:Protegidos", 904),
    "WSRT_SESSAO_AUDIO": ("$script:SessaoAudio", 4341),
    "WSRT_SESSAO_ENFEITES": ("$script:SessaoEnfeites", 4351),
    "WSRT_SESSAO_REMOTO": ("$script:SessaoRemoto", 4358),
    "WSRT_SESSAO_PRESERVAR": ("$script:SessaoPreservar", 4362),
    "WSRT_RAIZES_CLINICAS": ("$script:RaizesClinicas", 67),
    "WSRT_CATALOGO": ("Get-CatalogoProcessos", 906),
}
DATA_DA_COPIA_WSRT = "27/09/2026"

NAVEGADORES = ("msedge", "chrome", "firefox", "iexplore", "CentBrowser",
               "opera", "vivaldi", "brave")

MARCA_ECOSSISTEMA = "RADIOTERAPIA_AI"

ESPERA_JANELA_S = 0.5

NOME_EM_USO = "em_uso.json"
APP_EM_USO = "radioterapia-ai-local-suite"
VERSAO_EM_USO = 1
RENOVAR_EM_USO_S = 60
JANELA_DO_KIT_S = 300
RENOVACOES_NA_JANELA = 3

NOME_ESTADO_OTIMIZAR = "otimizar.json"

_LANCADORES = ("cmd", "py", "pyw", "python", "pythonw")

_REGEX = {}


def _regex(padroes):
    chave = padroes if isinstance(padroes, str) else tuple(padroes)
    r = _REGEX.get(chave)
    if r is None:
        texto = padroes if isinstance(padroes, str) else u"|".join(padroes)
        r = re.compile(texto, re.IGNORECASE)
        _REGEX[chave] = r
    return r


def _casa(padroes, texto):
    if not padroes or not texto:
        return False
    return _regex(padroes).search(str(texto)) is not None


def nome_do_processo(exe):
    n = os.path.basename(str(exe or u"").strip())
    return n[:-4] if n.lower().endswith(u".exe") else n


def no_ecossistema(caminho):
    c = str(caminho or u"").strip()
    if not c:
        return False
    try:
        partes = os.path.normpath(c).split(os.sep)
    except Exception:
        return False
    alvo = MARCA_ECOSSISTEMA.upper()
    return any(p.upper() == alvo for p in partes)


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
    psapi_ok = hasattr(k32, "K32GetProcessMemoryInfo")

    class _PE(ctypes.Structure):
        _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD),
                    ("th32ProcessID", W.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", W.DWORD), ("cntThreads", W.DWORD),
                    ("th32ParentProcessID", W.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", W.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    class _PMC(ctypes.Structure):
        _fields_ = [("cb", W.DWORD), ("PageFaultCount", W.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]

    k32.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    k32.CreateToolhelp32Snapshot.restype = W.HANDLE
    k32.Process32FirstW.argtypes = [W.HANDLE, ctypes.POINTER(_PE)]
    k32.Process32FirstW.restype = W.BOOL
    k32.Process32NextW.argtypes = [W.HANDLE, ctypes.POINTER(_PE)]
    k32.Process32NextW.restype = W.BOOL
    k32.CloseHandle.argtypes = [W.HANDLE]
    k32.CloseHandle.restype = W.BOOL
    k32.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    k32.OpenProcess.restype = W.HANDLE
    k32.QueryFullProcessImageNameW.argtypes = [
        W.HANDLE, W.DWORD, ctypes.c_wchar_p, ctypes.POINTER(W.DWORD)]
    k32.QueryFullProcessImageNameW.restype = W.BOOL
    k32.ProcessIdToSessionId.argtypes = [W.DWORD, ctypes.POINTER(W.DWORD)]
    k32.ProcessIdToSessionId.restype = W.BOOL
    if psapi_ok:
        k32.K32GetProcessMemoryInfo.argtypes = [
            W.HANDLE, ctypes.POINTER(_PMC), W.DWORD]
        k32.K32GetProcessMemoryInfo.restype = W.BOOL

    INVALIDO = ctypes.c_void_p(-1).value
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)
    if not snap or snap == INVALIDO:
        return []
    brutos = []
    try:
        pe = _PE()
        pe.dwSize = ctypes.sizeof(_PE)
        ok = k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            brutos.append((int(pe.th32ProcessID), int(pe.th32ParentProcessID),
                           str(pe.szExeFile)))
            ok = k32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)

    janelas = _janelas_por_pid()
    fora = []
    for pid, ppid, exe in brutos:
        sessao = None
        s = W.DWORD(0)
        if k32.ProcessIdToSessionId(pid, ctypes.byref(s)):
            sessao = int(s.value)
        caminho, mem_mb = u"", None
        h = k32.OpenProcess(0x1000, False, pid)
        if h:
            try:
                buf = ctypes.create_unicode_buffer(1024)
                tam = W.DWORD(1024)
                if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(tam)):
                    caminho = buf.value
                if psapi_ok:
                    pmc = _PMC()
                    pmc.cb = ctypes.sizeof(_PMC)
                    if k32.K32GetProcessMemoryInfo(h, ctypes.byref(pmc),
                                                   pmc.cb):
                        mem_mb = int(pmc.WorkingSetSize / (1024 * 1024))
            finally:
                k32.CloseHandle(h)
        fora.append({"pid": pid, "ppid": ppid, "exe": exe,
                     "nome": nome_do_processo(exe), "caminho": caminho,
                     "sessao": sessao, "janela": pid in janelas,
                     "mem_mb": mem_mb})
    return fora


def _user32():
    import ctypes
    from ctypes import wintypes as W
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    u32.IsWindowVisible.argtypes = [W.HWND]
    u32.IsWindowVisible.restype = W.BOOL
    u32.GetWindow.argtypes = [W.HWND, W.UINT]
    u32.GetWindow.restype = W.HWND
    u32.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
    u32.GetWindowThreadProcessId.restype = W.DWORD
    u32.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    u32.PostMessageW.restype = W.BOOL
    return u32


def _janelas_por_pid():
    fora = {}
    try:
        import ctypes
        from ctypes import wintypes as W
        u32 = _user32()
        TIPO = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

        def _cada(hwnd, _l):
            try:
                if u32.IsWindowVisible(hwnd) and not u32.GetWindow(hwnd, 4):
                    pid = W.DWORD(0)
                    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    fora.setdefault(int(pid.value), []).append(hwnd)
            except Exception:
                pass
            return True

        u32.EnumWindows.argtypes = [TIPO, W.LPARAM]
        u32.EnumWindows.restype = W.BOOL
        u32.EnumWindows(TIPO(_cada), 0)
    except Exception:
        return {}
    return fora


def sessao_deste_processo():
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes as W
        s = W.DWORD(0)
        if ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),
                                                       ctypes.byref(s)):
            return int(s.value)
    except Exception:
        pass
    return None


def eh_administrador():
    if os.name != "nt":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


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


def classificar(p, arvore=(), sessao=None, pid_proprio=None):
    pid = int(p.get("pid") or 0)
    nome = str(p.get("nome") or nome_do_processo(p.get("exe")))
    caminho = str(p.get("caminho") or u"")
    pid_proprio = os.getpid() if pid_proprio is None else int(pid_proprio)

    def _r(classe, fecha=False, marcado=False, rotulo=u"", nota=u""):
        return {"classe": classe, "fecha": bool(fecha),
                "marcado": bool(fecha and marcado),
                "rotulo": rotulo or nome, "nota": nota}

    if pid == pid_proprio:
        return _r("proprio")
    if pid <= 4:
        return _r("protegido")
    if (sessao is not None and p.get("sessao") is not None
            and int(p["sessao"]) != int(sessao)):
        return _r("outra_sessao")
    if pid in set(arvore or ()) or no_ecossistema(caminho):
        return _r("app")
    if _casa(NAVEGADORES, nome):
        return _r("navegador")
    if _casa(WSRT_RAIZES_CLINICAS, caminho):
        return _r("clinico")
    if _protegido(nome):
        return _r("protegido")
    if _casa(WSRT_SESSAO_AUDIO, nome):
        return _r("audio", True, True, rotulo=u"%s (áudio e periféricos)" % nome,
                  nota=u"O som continua: sai só a camada de realce e o ícone.")
    if _casa(WSRT_SESSAO_ENFEITES, nome):
        return _r("enfeite", True, True,
                  rotulo=u"%s (enfeite do Windows)" % nome,
                  nota=u"Volta sozinho quando o Windows precisar dele.")
    if _casa(WSRT_SESSAO_REMOTO, nome):
        return _r("remoto")
    if _casa(WSRT_SESSAO_PRESERVAR, nome):
        return _r("preservar")
    if _casa(WSRT_PROTEGIDOS, nome):
        return _r("protegido")
    janela = bool(p.get("janela"))
    for padrao, nivel, rotulo, nota in WSRT_CATALOGO:
        if _casa(padrao, nome):
            if nivel == "SemJanela" and janela:
                return _r("catalogo", True, False, rotulo,
                          u"Tem janela aberta: só fecha se você marcar.")
            return _r("catalogo", True, True, rotulo, nota)
    if janela:
        return _r("desconhecido", True, False,
                  nota=u"Tem janela aberta e o programa não o reconhece: "
                       u"desmarcado. Marque só se souber que pode fechar.")
    return _r("fora_das_listas")


_CLASSES_PROTEGIDAS = ("app", "navegador", "clinico", "protegido", "remoto",
                       "preservar")


def plano_de_otimizacao(procs=None, pid_app=None, admin=None,
                        com_disco=True):
    procs = processos() if procs is None else list(procs)
    admin = eh_administrador() if admin is None else bool(admin)
    fora = {"ok": bool(procs), "admin": admin, "itens": [], "servicos": [],
            "disco": [], "protegidos": {}, "aviso_servicos": u""}
    if not procs:
        fora["erro"] = (u"não consegui listar os processos desta sessão — "
                        u"nada será fechado.")
        return fora
    pid_proprio = os.getpid()
    sessao = _sessao_em(procs, pid_proprio)
    arvore = arvore_do_app(procs, pid_app)
    grupos, contagem = {}, {}
    for p in procs:
        c = classificar(p, arvore, sessao, pid_proprio)
        contagem[c["classe"]] = contagem.get(c["classe"], 0) + 1
        if not c["fecha"]:
            continue
        chave = str(p.get("nome") or u"").lower()
        g = grupos.get(chave)
        if g is None:
            g = grupos[chave] = {"nome": p.get("nome"), "rotulo": c["rotulo"],
                                 "classe": c["classe"], "n": 0, "mem_mb": 0,
                                 "janela": False, "marcado": True,
                                 "nota": c["nota"]}
        g["n"] += 1
        g["mem_mb"] += int(p.get("mem_mb") or 0)
        g["janela"] = g["janela"] or bool(p.get("janela"))
        if not c["marcado"]:
            g["marcado"] = False
            g["nota"] = c["nota"]
    fora["itens"] = sorted(grupos.values(),
                           key=lambda g: (not g["marcado"], -g["mem_mb"],
                                          str(g["nome"]).lower()))
    fora["protegidos"] = dict((k, v) for k, v in contagem.items()
                              if k in _CLASSES_PROTEGIDAS)
    if admin:
        fora["servicos"] = [dict(s, marcado=True) for s in estado_dos_servicos()
                            if s.get("estado") == "rodando"]
    else:
        fora["aviso_servicos"] = (
            u"Sem administrador: os serviços do Windows ficam como estão, e o "
            u"«Otimizar» age só nos processos desta sessão.")
    if com_disco:
        try:
            fora["disco"] = [dict(i, marcado=bool(i.get("sugerido")))
                             for i in espaco_recuperavel() if i.get("apagavel")]
        except Exception:
            fora["disco"] = []
    return fora


def _sessao_em(procs, pid):
    for p in procs or ():
        if int(p.get("pid") or 0) == int(pid) and p.get("sessao") is not None:
            return int(p["sessao"])
    return sessao_deste_processo()


def _fechar_pid(p, espera_s=ESPERA_JANELA_S):
    pid = int(p.get("pid") or 0)
    if pid <= 4 or pid == os.getpid():
        return {"ok": False, "como": u"recusado: é este programa"}
    try:
        hwnds = _janelas_por_pid().get(pid) or []
        if hwnds:
            for h in hwnds:
                _postar_fechar(h)
            if _esperar_saida(pid, espera_s):
                return {"ok": True, "como": u"fechado pela janela"}
        return _forcar(pid)
    except Exception as e:
        return {"ok": False, "como": u"não consegui (%s)" % type(e).__name__}


def _postar_fechar(hwnd):
    try:
        return bool(_user32().PostMessageW(hwnd, 0x0010, 0, 0))
    except Exception:
        return False


def _abrir_para(pid, direito):
    import ctypes
    from ctypes import wintypes as W
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    k32.OpenProcess.restype = W.HANDLE
    k32.CloseHandle.argtypes = [W.HANDLE]
    k32.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    k32.WaitForSingleObject.restype = W.DWORD
    k32.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
    k32.TerminateProcess.restype = W.BOOL
    h = k32.OpenProcess(direito, False, int(pid))
    return k32, h, ctypes.get_last_error()


def _esperar_saida(pid, espera_s):
    try:
        k32, h, err = _abrir_para(pid, 0x00100000)
        if not h:
            return err == 87
        try:
            return k32.WaitForSingleObject(h, int(espera_s * 1000)) == 0
        finally:
            k32.CloseHandle(h)
    except Exception:
        return False


def _forcar(pid):
    k32, h, err = _abrir_para(pid, 0x0001 | 0x00100000)
    if not h:
        if err == 87:
            return {"ok": True, "como": u"já tinha fechado"}
        if err == 5:
            return {"ok": False, "como": u"o Windows negou (acesso negado)"}
        return {"ok": False, "como": u"não consegui abrir (erro %d)" % err}
    try:
        import ctypes
        if not k32.TerminateProcess(h, 1):
            return {"ok": False, "como": u"o Windows recusou (erro %d)"
                                         % ctypes.get_last_error()}
        if k32.WaitForSingleObject(h, 3000) != 0:
            return {"ok": False, "como": u"pedi e ele não saiu em 3 s"}
        return {"ok": True, "como": u"forçado"}
    finally:
        k32.CloseHandle(h)


def fechar_processos(nomes, procs_fn=None, pid_app=None, log=None,
                     espera_s=ESPERA_JANELA_S, pid_proprio=None):
    log = log or (lambda m: None)
    pedidos = set(str(n or u"").strip().lower() for n in (nomes or ())
                  if str(n or u"").strip())
    fora = {"fechados": [], "ficaram": [], "mb": 0}
    if not pedidos:
        return fora
    procs = (procs_fn or processos)()
    pid_proprio = os.getpid() if pid_proprio is None else int(pid_proprio)
    sessao = _sessao_em(procs, pid_proprio)
    arvore = arvore_do_app(procs, pid_app)
    achados = set()
    for p in sorted(procs, key=lambda x: (str(x.get("nome") or u"").lower(),
                                          int(x.get("pid") or 0))):
        nome = str(p.get("nome") or u"")
        if nome.lower() not in pedidos:
            continue
        achados.add(nome.lower())
        c = classificar(p, arvore, sessao, pid_proprio)
        if not c["fecha"]:
            fora["ficaram"].append({"nome": nome, "pid": p.get("pid"),
                                    "motivo": _MOTIVO.get(c["classe"],
                                                          c["classe"])})
            _log(log, u"otimizar: %s (PID %s) ficou aberto — %s"
                 % (p.get("exe") or nome, p.get("pid"),
                    _MOTIVO.get(c["classe"], c["classe"])))
            continue
        r = _fechar_pid(p, espera_s)
        mb = int(p.get("mem_mb") or 0)
        if r.get("ok"):
            fora["fechados"].append(nome)
            fora["mb"] += mb
        else:
            fora["ficaram"].append({"nome": nome, "pid": p.get("pid"),
                                    "motivo": r.get("como")})
        _log(log, u"otimizar: %s (PID %s) %s — %d MB"
             % (p.get("exe") or nome, p.get("pid"), r.get("como"), mb))
    for n in sorted(pedidos - achados):
        _log(log, u"otimizar: %s já não estava aberto" % n)
    fora["fechados"] = sorted(set(fora["fechados"]), key=lambda x: x.lower())
    return fora


_MOTIVO = {
    "proprio": u"é este programa",
    "outra_sessao": u"é de outra sessão do Windows",
    "app": u"faz parte do Radioterapia.AI",
    "navegador": u"é o navegador",
    "clinico": u"roda de uma pasta clínica",
    "protegido": u"está na lista de protegidos",
    "remoto": u"é acesso remoto do TI",
    "preservar": u"está na lista de preservados",
    "fora_das_listas": u"não está em lista fechada nenhuma",
}


def _log(log, msg):
    try:
        log(msg)
    except Exception:
        pass


def pasta_de_estado():
    base = str(os.environ.get("LOCALAPPDATA") or u"").strip()
    return os.path.join(base, MARCA_ECOSSISTEMA) if base else u""


def _caminho_estado():
    d = pasta_de_estado()
    return os.path.join(d, NOME_ESTADO_OTIMIZAR) if d else u""


def ler_estado_otimizar():
    import json
    c = _caminho_estado()
    try:
        with open(c, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _gravar_estado_otimizar(d):
    import json
    c = _caminho_estado()
    if not c:
        return False
    try:
        os.makedirs(os.path.dirname(c), exist_ok=True)
        tmp = c + ".parcial"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, c)
        return True
    except Exception:
        return False


def otimizar(nomes=(), servicos=(), discos=(), log=None, admin=None,
             procs_fn=None, pid_app=None):
    import time as _t
    log = log or (lambda m: None)
    admin = eh_administrador() if admin is None else bool(admin)
    _log(log, u"otimizar: começou — %d programa(s), %d serviço(s), %d item(ns) "
              u"de disco pedidos" % (len(nomes or ()), len(servicos or ()),
                                     len(discos or ())))
    r = fechar_processos(nomes, procs_fn=procs_fn, pid_app=pid_app, log=log)
    parados = []
    if not admin:
        _log(log, u"otimizar: sem administrador — os serviços do Windows não "
                  u"foram tocados; só processos desta sessão")
    elif servicos:
        for s in servicos:
            rs = parar_servico(s)
            _log(log, u"otimizar: serviço %s" % rs.get("msg"))
            if rs.get("ok") and u"já estava" not in (rs.get("msg") or u""):
                parados.append(str(s))
    mb_disco = 0
    for chave in discos or ():
        rd = liberar(chave)
        mb_disco += int(rd.get("mb") or 0)
        _log(log, u"otimizar: disco %s" % rd.get("msg"))
    estado = ler_estado_otimizar()
    estado["fechados"] = sorted(set(list(estado.get("fechados") or [])
                                    + r["fechados"]), key=lambda x: x.lower())
    estado["servicos"] = sorted(set(list(estado.get("servicos") or [])
                                    + parados))
    estado["quando"] = _t.strftime("%Y-%m-%dT%H:%M:%S")
    gravou = _gravar_estado_otimizar(estado)
    _log(log, u"otimizar: pronto — %d programa(s) fechado(s), %d MB de memória, "
              u"%d serviço(s) parado(s), %d MB de disco%s"
         % (len(r["fechados"]), r["mb"], len(parados), mb_disco,
            u"" if gravou else u" (o registro do Restaurar não foi gravado: "
                               u"reabra à mão pelo menu Iniciar)"))
    return {"ok": True, "fechados": r["fechados"], "ficaram": r["ficaram"],
            "mb": r["mb"], "servicos_parados": parados, "mb_disco": mb_disco,
            "admin": admin, "restauravel": bool(r["fechados"] or parados)}


def _versoes_do_drive():
    fora = []
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        if not base:
            continue
        raiz = os.path.join(base, "Google", "Drive File Stream")
        try:
            nomes = os.listdir(raiz)
        except OSError:
            continue
        for n in nomes:
            if os.path.isdir(os.path.join(raiz, n)):
                fora.append((_versao(n), os.path.join(raiz, n,
                                                      "GoogleDriveFS.exe")))
    fora.sort(key=lambda x: x[0], reverse=True)
    return [c for _v, c in fora]


def _versao(texto):
    try:
        return tuple(int(x) for x in str(texto).split("."))
    except Exception:
        return (0,)


def _em(var, *partes):
    base = os.environ.get(var)
    return os.path.join(base, *partes) if base else u""


def mapa_de_reabertura():
    return [
        ("^GoogleDriveFS$", u"Google Drive", _versoes_do_drive(), []),
        ("OneDrive", u"OneDrive",
         [_em("LOCALAPPDATA", "Microsoft", "OneDrive", "OneDrive.exe"),
          _em("ProgramFiles", "Microsoft OneDrive", "OneDrive.exe"),
          _em("ProgramFiles(x86)", "Microsoft OneDrive", "OneDrive.exe")],
         ["/background"]),
        ("ms-teams|msteams|^Teams$", u"Microsoft Teams",
         [_em("LOCALAPPDATA", "Microsoft", "WindowsApps",
              "MSTeams_8wekyb3d8bbwe", "ms-teams.exe")], []),
        ("soffice", u"LibreOffice",
         [_em("ProgramFiles", "LibreOffice", "program", "soffice.exe"),
          _em("ProgramFiles(x86)", "LibreOffice", "program", "soffice.exe")],
         []),
    ]


def _abrir_programa(exe, args):
    try:
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = 0x00000008 | 0x00000200
        subprocess.Popen([exe] + list(args or ()), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         close_fds=True, **kw)
        return True
    except Exception:
        return False


def restaurar(log=None, admin=None, procs_fn=None):
    log = log or (lambda m: None)
    admin = eh_administrador() if admin is None else bool(admin)
    estado = ler_estado_otimizar()
    fechados = list(estado.get("fechados") or [])
    servicos = list(estado.get("servicos") or [])
    if not fechados and not servicos:
        _log(log, u"restaurar: nada registrado — o «Otimizar» não fechou nada "
                  u"nesta sessão")
        return {"ok": True, "reabertos": [], "nao_achados": [],
                "no_logon": [], "servicos": []}
    rodando = set(str(p.get("nome") or u"").lower()
                  for p in (procs_fn or processos)())
    reabertos, nao_achados, cobertos = [], [], set()
    for padrao, rotulo, exes, args in mapa_de_reabertura():
        foram = [n for n in fechados if _casa(padrao, n)]
        if not foram:
            continue
        cobertos.update(n.lower() for n in foram)
        if any(_casa(padrao, n) for n in rodando):
            _log(log, u"restaurar: %s já está aberto" % rotulo)
            continue
        abriu = False
        for exe in exes:
            if exe and os.path.isfile(exe) and _abrir_programa(exe, args):
                abriu = True
                break
        if abriu:
            reabertos.append(rotulo)
            _log(log, u"restaurar: %s reaberto" % rotulo)
        else:
            nao_achados.append(rotulo)
            _log(log, u"restaurar: %s — não achei o executável; abra pelo menu "
                      u"Iniciar" % rotulo)
    no_logon = [n for n in fechados if n.lower() not in cobertos]
    if no_logon:
        _log(log, u"restaurar: voltam sozinhos no próximo logon (ou quando o "
                  u"Windows precisar): %s" % u", ".join(no_logon[:20]))
    religados = []
    if servicos and not admin:
        _log(log, u"restaurar: sem administrador — os serviços parados voltam "
                  u"no próximo arranque do Windows")
    for s in (servicos if admin else ()):
        rs = iniciar_servico(s)
        _log(log, u"restaurar: serviço %s" % rs.get("msg"))
        if rs.get("ok"):
            religados.append(s)
    try:
        c = _caminho_estado()
        if c and os.path.exists(c):
            os.remove(c)
    except Exception:
        pass
    return {"ok": True, "reabertos": reabertos, "nao_achados": nao_achados,
            "no_logon": no_logon, "servicos": religados}


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


def linhas_do_diagnostico(conferencia=None, laudo_=None, plano=None,
                          em_uso=None):
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
    rod = [s.get("nome") for s in (ld.get("servicos") or ())
           if s.get("estado") == "rodando"]
    if rod:
        L.append(u"diagnostico: serviços da lista rodando — %s"
                 % u", ".join(rod))
    pl = plano or {}
    if pl:
        marc = [i for i in pl.get("itens") or () if i.get("marcado")]
        desm = [i for i in pl.get("itens") or () if not i.get("marcado")]
        L.append(u"diagnostico: o «Otimizar» fecharia %d programa(s) (%d MB)%s"
                 % (len(marc), sum(int(i.get("mem_mb") or 0) for i in marc),
                    (u" e oferece mais %d desmarcado(s)" % len(desm))
                    if desm else u""))
        pr = pl.get("protegidos") or {}
        if pr:
            L.append(u"diagnostico: nunca tocados — %s"
                     % u", ".join(u"%s %d" % (k, v) for k, v in sorted(pr.items())))
        if pl.get("aviso_servicos"):
            L.append(u"diagnostico: " + pl["aviso_servicos"])
    eu = em_uso or {}
    if eu:
        L.append(u"diagnostico: sinalização para o Workstation RT — %d PID(s) "
                 u"protegidos, atualizada em %s"
                 % (len(eu.get("pids") or ()), eu.get("atualizado") or u"?"))
    L.append(u"diagnostico: ---- fim ----")
    return L
