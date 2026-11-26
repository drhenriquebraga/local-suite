"""Adaptador local do modo dedicado. A prévia só inventaria; o controlador registra antes de agir."""
import ctypes
from ctypes import wintypes as W
from contextlib import contextmanager
from functools import lru_cache
from collections import OrderedDict
import json
import threading
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time

import radai_cleaner as limpeza
import radai_janela as janela

NAVEGADORES = frozenset("chrome msedge firefox opera brave vivaldi".split())
SINCRONIZADORES = frozenset("onedrive dropbox box googledrivefs".split())
# Atualizadores e instaladores ficam fora das ações em processos de desktop.
# Os serviços da lista curta têm suas próprias verificações de transferência e atualização.
PRESERVAR = tuple(limpeza.PROTEGIDOS) + tuple((
    "msedgewebview2 vsp mirada medis corridor neuroq olea tomtec onis digitalcore radiant weasis microdicom "
    "horos dicom pacs sectra ids7 tasy wheb epicsystems hyperspace powerchart cerner meditech soarian citrix "
    "wfica wfcrun cdviewer concentr sqlservr tomcat w3wp backup vpn tunnel wireguard forti anyconnect "
    "globalprotect tailscale zscaler anydesk teamviewer splashtop logmein screenconnect termserv remote "
    "atbroker narrator magnify nvda jaws speechaccess python node java powershell conemu codex winword "
    "excel powerpnt outlook msaccess msiexec trustedinstaller tiworker setup installer update orchestrator"
    ).split())
# União das listas de proteção dos Kits (D13). Compilada aqui para uso offline.
_PROTECAO_DO_KIT = re.compile(
    r"4dm|^claude$|^claude-code$|^cvd$|^cvmountd$|^epic$|^java$|^mfe|^mms$|^msra$|^mstsc$|"
    r"^olk$|^reflect|^services$|^vi\.|aadbroker|accuray|acrobat|acronis|acrord32|anyconnect|"
    r"anydesk|arcserve|aria|audiodg|authmansvr|autocontour|beyondtrust|bomgar|brainlab|"
    r"carbonite|catalina|ccmexec|ccmsetup|ccsvchst|cdviewer|centbrowser|cerner|citrix|"
    r"cmrcservice|cmrcviewer|commvault|concentr|conhost|corridor|cortex|csagent|csfalcon|"
    r"csrss|ctfmon|ctxcfrui|ctxwebhelper|cyserver|cytray|cyvera|dameware|datto|dicom|"
    r"digitalcore|dllhost|dsasvc|dwm|eclipse|elekta|epicsystems|excel|explorer|firebird|"
    r"focal|fontdrvhost|forcepoint|forti|forticlient|fortisslvpn|fortitray|globalprotect|"
    r"hdxrtcengine|horos|hyperspace|idle|idriveservice|ids7|idtnc|iexplore|igfx|impac|"
    r"inetinfo|iplan|ivanti|javaw|jp2launcher|landesk|limbus|lmiguardian|logmein|logonui|"
    r"lsagent|lsass|macmnsvc|macrium|masvc|mcshield|medis|meditech|microdicom|microsoft\.aad|"
    r"mim|mirada|monaco|mosaiq|msaccess|msmpeng|msmq|mysqld|neuroq|nissrv|notepad|nsdiag|"
    r"ntrtscan|nvcontainer|nxlog|odmactivedirectory|olea|oncentra|ondemand|onenote|"
    r"onis|openconsole|oracle|osirix|outlook|pacs|pccntmon|philips|pinnacle|postgres|"
    r"powerchart|powerpnt|powershell|precision|pulse|pwsh|qualysagent|quest|quickassist|"
    r"radiant|raycare|raysearch|raystation|rcagent|rdpclip|rdpinit|realtek|receiver|"
    r"redirector|registry|rtkaud|runtimebroker|rustdesk|savservice|screenconnect|searchfilterhost|"
    r"searchindexer|searchprotocolhost|sectra|secureconnector|securityhealth|selfservice|"
    r"sepmaster|shadowprotect|showmsg|sihost|smartscreen|smss|soarian|sophos|splashtop|"
    r"splunk|sqlservr|ssonsvr|stagent|stickynot|svchost|synaptics|system|taskhostw|"
    r"tasy|tasyagent|teamviewer|tmbm|tmlisten|tokenbroker|tomcat|tomotherapy|tomtec|"
    r"traps|trueimage|tv_w32|tv_x64|tvnserver|unsecapp|uvnc|varian|veeam|velocity|vitrea|"
    r"vncserver|vsp|w3wp|weasis|wfcrun32|wfica32|wheb|windowsterminal|wininit|winlogon|"
    r"winvnc|winword|wmiprvse|wordpad|xio|zohoassist|zsa", re.I)
_SERVICOS_SO_PARA_DEVOLVER = frozenset(("WSearch", "SysMain", "wuauserv", "UsoSvc", "DoSvc", "BITS"))
SERVICOS_PAUSAVEIS = frozenset(("DiagTrack",
    "gupdate", "gupdatem", "edgeupdate", "edgeupdatem", "AdobeARMservice", "MozillaMaintenance"))
SERVICOS_NUNCA = frozenset(("WinDefend","Sense","wscsvc","MpsSvc","BFE","LanmanWorkstation","LanmanServer",
    "Dnscache","Dhcp","NlaSvc","netprofm","Netlogon","RpcSs","DcomLaunch","EventLog","Winmgmt","CryptSvc",
    "TermService","Schedule","TrustedInstaller"))
_ATUALIZACOES = {"wuauserv","bits","dosvc","usosvc","gupdate","gupdatem","edgeupdate","edgeupdatem",
                 "adobearmservice","mozillamaintenance"}
_INSTALADORES = {"trustedinstaller","tiworker","msiexec","mousocoreworker","winget","setuphost"}
_ABAIXO = 0x4000
_PRIORIDADES = {0x20,0x8000,0x80}
_ECOSSISTEMA = ("radioterapia_ai", "ai_projetos", "local_suite", "local suite", "contourlab", "neuro_rt", "nidus_rt")

# Nome completo do programa e trecho de diretório do fornecedor. O caminho e a assinatura de arquivo
# são conferidos de novo antes da reabertura. Nenhuma linha de comando antiga é executada.
_FORNECEDORES = {
    "chrome":("google/chrome",), "msedge":("microsoft/edge",), "firefox":("mozilla firefox",),
    "brave":("bravesoftware/brave-browser",), "opera":("opera",), "vivaldi":("vivaldi",),
    "onedrive":("microsoft onedrive","microsoft/onedrive"), "dropbox":("dropbox",),
    "googledrivefs":("google/drive file stream",), "box":("box/box",),
    "spotify":("spotify",), "zoom":("zoom",), "slack":("slack",), "discord":("discord",),
    "skype":("microsoft/skype","skype"), "steam":("steam",), "epicgameslauncher":("epic games/launcher",),
    "teams":("microsoft/teams",), "ms-teams":("windowsapps/msteams_",), "msteams":("microsoft/teams",),
    "ccxprocess":("adobe",), "cclibrary":("adobe",), "ituneshelper":("itunes",)
}

_ASSINANTES = {
    "spotify": ("Spotify AB", "Spotify USA Inc."),
    "onedrive": ("Microsoft Corporation",), "teams": ("Microsoft Corporation",),
    "ms-teams": ("Microsoft Corporation",), "msteams": ("Microsoft Corporation",),
    "skype": ("Microsoft Corporation", "Skype Software Sarl"),
    "slack": ("Slack Technologies, LLC", "Slack Technologies, Inc."),
    "zoom": ("Zoom Video Communications, Inc.", "Zoom Communications, Inc."),
    "dropbox": ("Dropbox, Inc", "Dropbox, Inc."), "box": ("Box, Inc.",),
    "googledrivefs": ("Google LLC",), "steam": ("Valve Corp.", "Valve Corporation"),
    "discord": ("Discord Inc.",), "epicgameslauncher": ("Epic Games, Inc.",),
    "ituneshelper": ("Apple Inc.",), "ccxprocess": ("Adobe Inc.",), "cclibrary": ("Adobe Inc.",),
    "chrome": ("Google LLC",), "msedge": ("Microsoft Corporation",),
    "firefox": ("Mozilla Corporation",), "brave": ("Brave Software, Inc.",),
    "opera": ("Opera Norway AS",), "vivaldi": ("Vivaldi Technologies AS",),
}

_ASSINATURAS = OrderedDict()
_TRAVA_ASSINATURAS = threading.Lock()


def _consultar_assinaturas(caminhos):
    # Get-AuthenticodeSignature também reconhece assinaturas por catálogo. Os
    # nomes de arquivos são dados JSON em stdin, sem interpolação no comando.
    sistema = ctypes.create_unicode_buffer(32768)
    if not ctypes.WinDLL("kernel32").GetSystemDirectoryW(sistema, len(sistema)):
        return {}
    ps = Path(sistema.value) / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    cmd = ("$ErrorActionPreference='Stop';"
           "[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);"
           "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
           "$paths=ConvertFrom-Json -InputObject ([Console]::In.ReadToEnd());"
           "$itens=@(foreach($p in $paths){try{"
           "$a=Microsoft.PowerShell.Security\\Get-AuthenticodeSignature -LiteralPath $p;"
           "if([int]$a.Status -eq 0 -and $a.SignerCertificate){"
           "[pscustomobject]@{p=$p;n=$a.SignerCertificate.GetNameInfo(0,$false)}}}catch{}});"
           "[Console]::Write((ConvertTo-Json -Compress -InputObject $itens))")
    try:
        r = subprocess.run([str(ps), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", cmd],
                           env=dict(os.environ, PSModulePath=str(ps.parent/"Modules")),
                           input=json.dumps(caminhos, ensure_ascii=False).encode("utf-8"),
                           capture_output=True, timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode:
            return {}
        return {item["p"]: item["n"] for item in json.loads(r.stdout) if
                isinstance(item, dict) and isinstance(item.get("p"), str) and isinstance(item.get("n"), str)}
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return {}


def guardar_certificados_da_previa(certificados, candidatos, certificados_servicos=()):
    # Reaproveitar exclusivamente os hashes de executáveis elegíveis que o filho
    # de prévia conferiu. A revalidação de identidade e hash continua obrigatória.
    elegiveis = {(i["identidade"].get("caminho"), i["identidade"].get("sha256"))
                 for i in candidatos if i.get("tipo") in ("app", "prioridade")}
    servicos = {(i["id"], i["identidade"]) for i in candidatos if i.get("tipo") == "servico"}
    for nome, identidade, path, sha in certificados_servicos:
        if (nome, identidade) in servicos:
            elegiveis.add((path, sha))
    with _TRAVA_ASSINATURAS:
        for path, sha, assinante in certificados:
            if (path, sha) in elegiveis and assinante:
                _ASSINATURAS[(path, sha)] = assinante
        while len(_ASSINATURAS) > 128:
            _ASSINATURAS.popitem(last=False)


def _assinantes_dos(chaves):
    chaves = list(dict.fromkeys(chaves))
    with _TRAVA_ASSINATURAS:
        resultado = {k: _ASSINATURAS[k] for k in chaves if k in _ASSINATURAS}
    novos = [k for k in chaves if k not in resultado]
    if novos:
        verificados = _consultar_assinaturas([p for p, _ in novos])
        for chave in novos:
            caminho, sha = chave
            assinante = verificados.get(caminho, "")
            try:
                resultado[chave] = assinante if assinante and _hash(caminho) == sha else ""
            except OSError:
                resultado[chave] = ""

        with _TRAVA_ASSINATURAS:
            for chave in novos:
                if resultado[chave]:
                    _ASSINATURAS[chave] = resultado[chave]
            while len(_ASSINATURAS) > 128:
                _ASSINATURAS.popitem(last=False)
    return resultado


def _assinante(caminho, hash_arquivo):
    chave = (caminho, hash_arquivo)
    return _assinantes_dos([chave])[chave]


def _desktop_registrado(nome, caminho):
    # App Paths em HKLM declara um app de entrada do desktop. Nunca reproduzir linha de comando.
    import winreg
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,79}", nome):
        return False
    if Path(caminho).name.lower()!=nome+".exe" or str(caminho).startswith(("\\\\","//")):
        return False
    p=_normal(caminho)
    if not any(os.environ.get(k) and _em_raiz(p,_normal(os.environ[k]))
               for k in ("ProgramW6432","ProgramFiles","ProgramFiles(x86)")):
        return False
    partes = Path(p).parts[2:]
    if any(_PROTECAO_DO_KIT.search(x) or any(k in x.lower() for k in PRESERVAR + _ECOSSISTEMA)
           for x in partes):
        return False
    chave=r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths" + "\\" + nome + ".exe"
    for visao in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,chave,0,winreg.KEY_READ|visao) as h:
                v,t=winreg.QueryValueEx(h,None)
            if t in (winreg.REG_EXPAND_SZ,winreg.REG_SZ) and _normal(os.path.expandvars(v).strip('"'))==p:
                return True
        except OSError:
            continue
    return False

def _aprovado(nome,caminho,hash_arquivo,assinante=None):
    if nome in _FORNECEDORES:
        if not _caminho_conhecido(nome,caminho):
            return False
        if assinante is None:
            assinante = _assinante(caminho,hash_arquivo)
        return assinante in _ASSINANTES.get(nome,())
    if not _desktop_registrado(nome,caminho):
        return False
    assinatura=(assinante if assinante is not None else _assinante(caminho,hash_arquivo)).lower()
    return bool(assinatura and not _PROTECAO_DO_KIT.search(assinatura)
                and not any(k in assinatura for k in PRESERVAR + _ECOSSISTEMA))

def _instalacao_do_servico(nome,comando,pendencias=None):
    # O SCM é consultado de novo antes de controlar um serviço. Uma entrada com o nome
    # de um atualizador substituída por um binário de outro produto não é elegível.
    sysdir=ctypes.create_unicode_buffer(32768)
    if not ctypes.WinDLL("kernel32").GetSystemDirectoryW(sysdir,len(sysdir)):return False
    cmd=os.path.expandvars(comando or "").strip()
    m=re.match(r'^"([^"]+\.exe)"(?:\s|$)|^(.+?\.exe)(?:\s|$)',cmd,flags=re.I)
    if not m:return False
    path=_normal(m.group(1) or m.group(2))
    if nome in ("WSearch","SysMain","DiagTrack","DoSvc","wuauserv","UsoSvc","BITS"):
        exe="SearchIndexer.exe" if nome=="WSearch" else "svchost.exe"
        return path==_normal(Path(sysdir.value)/exe)
    externos={"gupdate":("google","googleupdate.exe","Google LLC"),
              "gupdatem":("google","googleupdate.exe","Google LLC"),
              "edgeupdate":("microsoft","microsoftedgeupdate.exe","Microsoft Corporation"),
              "edgeupdatem":("microsoft","microsoftedgeupdate.exe","Microsoft Corporation"),
              "AdobeARMservice":("adobe","armsvc.exe","Adobe Inc."),
              "MozillaMaintenance":("mozilla maintenance service","maintenanceservice.exe","Mozilla Corporation")}
    if nome not in externos:return False
    pasta,exe,assinante=externos[nome]
    if Path(path).name.lower()!=exe:return False
    raizes=[_normal(Path(os.environ[k])/pasta) for k in ("ProgramFiles","ProgramFiles(x86)","CommonProgramFiles","CommonProgramFiles(x86)") if os.environ.get(k)]
    if not any(_em_raiz(path,r) for r in raizes):
        return False
    sha = _hash(path)
    if pendencias is not None:
        pendencias[nome] = (path, sha, assinante)
        return True  # apenas coleta local da prévia; o filtro de assinatura vem antes da seleção
    return _assinante(path,sha) == assinante

def _normal(p):
    return os.path.normcase(os.path.realpath(str(p)))

def _em_raiz(p, raiz):
    try:
        return os.path.commonpath([p,raiz])==raiz
    except ValueError:
        return False

def _caminho_conhecido(nome, caminho):
    if nome not in _FORNECEDORES or not caminho or str(caminho).startswith(("\\\\","//")):
        return False
    p = _normal(caminho)
    if Path(p).name.lower() != nome + ".exe" or any(s in p.lower() for s in _ECOSSISTEMA):
        return False
    for k in ("ProgramW6432", "ProgramFiles","ProgramFiles(x86)","LOCALAPPDATA","APPDATA"):
        raiz = os.environ.get(k)
        if not raiz or not _em_raiz(p, _normal(raiz)):
            continue
        rel = os.path.relpath(p,_normal(raiz)).replace("\\","/").lower()
        partes = "/"+rel+"/"
        for fornecedor in _FORNECEDORES[nome]:
            if "/"+fornecedor+"/" in partes or (fornecedor.endswith("_") and partes.startswith("/"+fornecedor)):
                return True
    return False

@lru_cache(maxsize=128)
def _hash_estavel(caminho, tamanho, alterado, criado):
    h=hashlib.sha256()
    with open(caminho,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    s=os.stat(caminho)
    if (s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(tamanho,alterado,criado):
        raise OSError("O programa foi atualizado")
    return h.hexdigest()

def _hash(caminho):
    s=os.stat(caminho)
    return _hash_estavel(caminho,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def _descendentes(procs, raizes):
    filhos={}
    for p in procs: filhos.setdefault(p["ppid"],[]).append(p["pid"])
    vistos=set(raizes)
    fila=list(vistos)
    while fila:
        for pid in filhos.get(fila.pop(),()):
            if pid not in vistos:
                vistos.add(pid)
                fila.append(pid)
    return vistos

_CATEGORIAS = {
    "TPS / PACS": re.compile(r"vitrea|varian|eclipse|raystation|monaco|mosaiq|sectra|dicom|^epic$|pacs", re.I),
    "Banco de dados": re.compile(r"^sqlservr$|^sqlagent|^mssql|^postgres|^mysqld$|^oracle|^firebird", re.I),
    "Servidor de aplicações": re.compile(r"tomcat|catalina|^w3wp$|^inetinfo$|^w3svc$|^httpd$|^apache", re.I),
    "Rede / acesso remoto": re.compile(r"wireguard|forti|anyconnect|globalprotect|citrix|teamviewer|anydesk|^mstsc$", re.I),
    "Local Suite": re.compile(r"radai|local_suite|contourlab|totalsegmentator", re.I),
}
# A evidência vem de um processo servidor em execução, não de um visualizador ou cliente SQL.
_HOSPEDAGEM = re.compile(r"^sqlservr$|^sqlagent|^mssql|^postgres|^mysqld$|^oracle|^firebird|"
                        r"tomcat|catalina|^w3wp$|^inetinfo$|^w3svc$|^httpd$|^apache|^orthanc$|^dcmqrscp$", re.I)

def _perfil_do_navegador(nome, args):
    """None indica identidade ambígua; string vazia é a inicialização normal sem perfil explícito."""
    if not args or Path(args[0]).name.lower()!=nome+".exe":
        return None
    chaves=("-profile","--profile") if nome=="firefox" else ("--user-data-dir",)
    valores=[]
    for i, arg in enumerate(args[1:],1):
        if arg.lower().startswith(("--type","--kiosk","-kiosk","--app","-contentproc","-marionette",
                                   "--marionette","--headless","-headless","--remote-debugging")):
            return None
        for chave in chaves:
            if arg.lower()==chave:
                if i+1==len(args):
                    return None
                valores.append(args[i+1])
            elif arg.lower().startswith(chave+"="):
                valores.append(arg.split("=",1)[1])
    if not valores:
        # Só o lançamento convencional. Perfis nomeados, URLs, switches de
        # integração e argumentos ilegíveis não demonstram um navegador pessoal.
        return "" if len(args)==1 else None
    if len(valores)!=1 or not os.path.isabs(valores[0]):
        return None
    return valores[0]

def _navegador_pessoal(plataforma, pid, nome, janelas):
    if not janelas:
        return False
    linha=plataforma.linha_de_comando(pid)
    perfil=_perfil_do_navegador(nome,janela.argumentos_windows(linha))
    if perfil is None or (perfil and _normal(perfil)==_normal(janela.perfil_esperado_do_app())):
        return False
    for hw in janelas:
        titulo=(plataforma.titulo(hw) or "").strip().lower()
        if not titulo or _PROTECAO_DO_KIT.search(titulo) or any(k in titulo for k in PRESERVAR + _ECOSSISTEMA):
            return False
    return True

def _resumo(processos):
    nomes = [p["nome"] for p in processos]
    return {"preservados": [grupo for grupo, expr in _CATEGORIAS.items()
                            if any(expr.search(nome) for nome in nomes)],
            "hospeda_servicos": any(_HOSPEDAGEM.search(nome) for nome in nomes)}

def _ancestrais(procs, pids):
    pais = {p["pid"]: p["ppid"] for p in procs}
    vistos = set()
    for filho in pids:
        while filho in pais and filho > 4 and filho not in vistos:
            vistos.add(filho)
            filho = pais[filho]
    return vistos

def selecionar(inventario, porta):
    """Monta somente propostas com identidade positiva e host da Suite reconhecido."""
    if not inventario.get("pronto") or not porta: return []
    itens=[]
    for p in inventario["processos"]:
        nome=p["nome"].lower()
        if (not p.get("identidade") or not p.get("mesmo_usuario") or p.get("protegido")
                or nome=="epic" or _PROTECAO_DO_KIT.search(nome) or any(s in nome for s in PRESERVAR) or not (p.get("conhecido") or p.get("desktop_verificado"))):
            continue
        nav=nome in NAVEGADORES
        if nav and (not p.get("perfil_independente") or not p.get("janelas")):
            continue
        tem_janelas=bool(p.get("janelas"))
        mb=p.get("memoria_mb")
        marcado=bool(nav or p.get("conhecido") or (not tem_janelas and mb is not None and mb <= 300))
        principal={"id":p["pid"],"nome":nome,"identidade":p["identidade"],"porta":int(porta),
                   "navegador":nav,"automatico":nome in SINCRONIZADORES,"selecionado":marcado,"memoria_mb":int(mb or 0),"janelas":len(p.get("janelas") or []),"conhecido":bool(p.get("conhecido"))}
        if (tem_janelas or (not nav and mb is not None)) and inventario.get("explorer_interativo"):
            itens.append(dict(principal,tipo="app"))
        if nav:
            continue
        if p.get("prioridade") in _PRIORIDADES:
            itens.append(dict(principal,tipo="prioridade",original=p["prioridade"],automatico=True))
    if inventario.get("elevado"):
        for nome,estado in inventario.get("servicos",{}).items():
            if (nome in SERVICOS_PAUSAVEIS and nome not in SERVICOS_NUNCA and estado["estado"]==4
                    and estado.get("identidade") and not estado.get("bloqueado")):
                itens.append({"tipo":"servico","id":nome,"nome":nome,"identidade":estado["identidade"],
                    "original":4,"porta":int(porta),"automatico":True,"selecionado":True})
    return itens

def _api(lib, nome, retorno, *argumentos):
    fn=getattr(lib,nome)
    fn.restype=retorno
    fn.argtypes=list(argumentos)
    return fn

class _Status(ctypes.Structure):
    _fields_=[(n,W.DWORD) for n in ("tipo","estado","aceita","codigo","especifico","checkpoint","espera","pid","flags")]

class _Config(ctypes.Structure):
    _fields_=[("tipo",W.DWORD),("inicio",W.DWORD),("erro",W.DWORD),("binario",W.LPWSTR),
              ("grupo",W.LPWSTR),("tag",W.DWORD),("deps",ctypes.c_void_p),("conta",W.LPWSTR),("nome",W.LPWSTR)]

class _ServicoComProcesso(ctypes.Structure):
    _fields_ = [("nome",W.LPWSTR),("descricao",W.LPWSTR),("estado",_Status)]

class _Memoria(ctypes.Structure):
    _fields_=[("cb",W.DWORD),("faltas",W.DWORD)]+[(k,ctypes.c_size_t) for k in
              ("pico","trabalho","nppico","np","ppico","p","paginacao","pico_paginacao")]

class Plataforma:
    def __init__(self):
        self.k=ctypes.WinDLL("kernel32",use_last_error=True)
        self.a=ctypes.WinDLL("advapi32",use_last_error=True)
        self.p=ctypes.WinDLL("psapi",use_last_error=True)
        self.j=janela.plataforma()
        self.open=_api(self.k,"OpenProcess",W.HANDLE,W.DWORD,W.BOOL,W.DWORD)
        self.close=_api(self.k,"CloseHandle",W.BOOL,W.HANDLE)
        self.prio=_api(self.k,"GetPriorityClass",W.DWORD,W.HANDLE)
        self.mudar_prio=_api(self.k,"SetPriorityClass",W.BOOL,W.HANDLE,W.DWORD)
        self.tempo=_api(self.k,"GetProcessTimes",W.BOOL,W.HANDLE,*([ctypes.POINTER(W.FILETIME)]*4))
        self.path=_api(self.k,"QueryFullProcessImageNameW",W.BOOL,W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD))
        self.sess=_api(self.k,"ProcessIdToSessionId",W.BOOL,W.DWORD,ctypes.POINTER(W.DWORD))
        self.token=_api(self.a,"OpenProcessToken",W.BOOL,W.HANDLE,W.DWORD,ctypes.POINTER(W.HANDLE))
        self.tokeninfo=_api(self.a,"GetTokenInformation",W.BOOL,W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD))
        self.sidtexto=_api(self.a,"ConvertSidToStringSidW",W.BOOL,ctypes.c_void_p,ctypes.POINTER(W.LPWSTR))
        self.libera=_api(self.k,"LocalFree",ctypes.c_void_p,ctypes.c_void_p)
        self.espera=_api(self.k,"WaitForSingleObject",W.DWORD,W.HANDLE,W.DWORD)
        self.memoria=_api(self.p,"GetProcessMemoryInfo",W.BOOL,W.HANDLE,ctypes.c_void_p,W.DWORD)
        self.terminar=_api(self.k,"TerminateProcess",W.BOOL,W.HANDLE,W.UINT)
        self.scopen=_api(self.a,"OpenSCManagerW",W.HANDLE,W.LPCWSTR,W.LPCWSTR,W.DWORD)
        self.listar_servicos=_api(self.a,"EnumServicesStatusExW",W.BOOL,W.HANDLE,ctypes.c_int,W.DWORD,W.DWORD,
                                 ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.POINTER(W.DWORD),
                                 ctypes.POINTER(W.DWORD),W.LPCWSTR)
        self.svcopen=_api(self.a,"OpenServiceW",W.HANDLE,W.HANDLE,W.LPCWSTR,W.DWORD)
        self.scclose=_api(self.a,"CloseServiceHandle",W.BOOL,W.HANDLE)
        self.query=_api(self.a,"QueryServiceStatusEx",W.BOOL,W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD))
        self.config=_api(self.a,"QueryServiceConfigW",W.BOOL,W.HANDLE,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD))
        self.deps=_api(self.a,"EnumDependentServicesW",W.BOOL,W.HANDLE,W.DWORD,ctypes.c_void_p,W.DWORD,ctypes.POINTER(W.DWORD),ctypes.POINTER(W.DWORD))
        self.control=_api(self.a,"ControlService",W.BOOL,W.HANDLE,W.DWORD,ctypes.c_void_p)
        self.start=_api(self.a,"StartServiceW",W.BOOL,W.HANDLE,W.DWORD,ctypes.c_void_p)
        self.admin=bool(ctypes.WinDLL("shell32").IsUserAnAdmin())
        import sys
        self.compartilhada=(sys.getwindowsversion().product_type!=1
                            or bool(ctypes.WinDLL("user32").GetSystemMetrics(0x1000)))

    @contextmanager
    def processo(self,pid,acesso=0):
        h=self.open(0x1000|0x100000|acesso,False,int(pid))
        try: yield h
        finally:
            if h: self.close(h)

    def usuario(self,h):
        t=W.HANDLE()
        if not self.token(h,8,ctypes.byref(t)):return ""
        try:
            n=W.DWORD()
            self.tokeninfo(t,1,None,0,ctypes.byref(n))
            if not 0<n.value<65536:return ""
            dados=ctypes.create_string_buffer(n.value)
            if not self.tokeninfo(t,1,dados,n,ctypes.byref(n)):return ""
            ptr=ctypes.cast(dados,ctypes.POINTER(ctypes.c_void_p))[0]
            texto=W.LPWSTR()
            if not self.sidtexto(ptr,ctypes.byref(texto)):return ""
            try:return hashlib.sha256(texto.value.encode("ascii")).hexdigest()
            finally:self.libera(ctypes.cast(texto,ctypes.c_void_p))
        finally:self.close(t)

    def identidade(self,h,pid):
        sess=W.DWORD()
        tamanho=W.DWORD(32768)
        buf=ctypes.create_unicode_buffer(tamanho.value)
        t=[W.FILETIME() for _ in range(4)]
        if not (h and self.sess(pid,ctypes.byref(sess)) and self.tempo(h,*(ctypes.byref(v) for v in t))
                and self.path(h,0,buf,ctypes.byref(tamanho))):return None
        dono=self.usuario(h)
        if not dono:return None
        return {"sessao":int(sess.value),"usuario":dono,"criado":(t[0].dwHighDateTime<<32)|t[0].dwLowDateTime,
                "caminho":_normal(buf.value)}

    @contextmanager
    def servico(self,nome,acesso=0):
        scm=self.scopen(None,None,1)
        h=None
        try:
            if scm:h=self.svcopen(scm,nome,1|4|8|acesso)
            yield h
        finally:
            if h:self.scclose(h)
            if scm:self.scclose(scm)

    def estado_servico(self,h,nome,pendencias=None):
        st=_Status();n=W.DWORD();ativos=W.DWORD()
        if not h or not self.query(h,0,ctypes.byref(st),ctypes.sizeof(st),ctypes.byref(n)):return None
        self.config(h,None,0,ctypes.byref(n))
        if not 0<n.value<32768:return None
        buf=ctypes.create_string_buffer(n.value)
        if not self.config(h,buf,n,ctypes.byref(n)):return None
        cfg=ctypes.cast(buf,ctypes.POINTER(_Config)).contents
        # Usa a configuração registrada diretamente no SCM. A identidade não inclui argumentos no diário.
        if not _instalacao_do_servico(nome,cfg.binario,pendencias):return None
        identidade=hashlib.sha256(repr((nome,cfg.tipo,cfg.inicio,cfg.binario,cfg.conta)).encode()).hexdigest()
        sem_deps=bool(self.deps(h,1,None,0,ctypes.byref(n),ctypes.byref(ativos))) and ativos.value==0
        return {"estado":st.estado,"identidade":identidade,"bloqueado":not sem_deps or not (st.aceita&1)}

    def servicos_ativos(self):
        scm=self.scopen(None,None,4)
        if not scm:
            return None
        resume=W.DWORD()
        saida=[]
        try:
            while True:
                # O limite de 256 KiB é o máximo documentado do EnumServicesStatusExW por página.
                buf=ctypes.create_string_buffer(256*1024)
                necessidade=W.DWORD()
                n=W.DWORD()
                ok=self.listar_servicos(scm,0,0x30,1,buf,len(buf),ctypes.byref(necessidade),
                                        ctypes.byref(n),ctypes.byref(resume),None)
                codigo=0 if ok else ctypes.get_last_error()
                if (not ok and (codigo!=234 or not n.value)) or n.value>len(buf)//ctypes.sizeof(_ServicoComProcesso):
                    return None
                itens=ctypes.cast(buf,ctypes.POINTER(_ServicoComProcesso))
                saida.extend((itens[i].estado.pid,itens[i].nome or "") for i in range(n.value))
                if ok:
                    return saida
        finally:
            self.scclose(scm)

    def _servicos_disponiveis(self, servicos_alvo, lista, pendencias=None):
        serv={}
        if self.admin and servicos_alvo:
            atualizando=any(n.lower() in _ATUALIZACOES for n in servicos_alvo) and self.atualizando(lista)
            transferindo=set()
            if servicos_alvo & {"BITS","DoSvc"}:
                transferindo=self.transferencias_em_curso() if not atualizando else {"BITS","DoSvc"}
            for nome in servicos_alvo:
                if nome in transferindo or (nome.lower() in _ATUALIZACOES and atualizando):continue
                with self.servico(nome) as h:
                    estado=self.estado_servico(h,nome,pendencias)
                    if estado:serv[nome]=estado
        return serv

    def inventario(self,porta,alvo=None,pid_motor=None):
        lista=limpeza.processos()
        resumo=_resumo(lista or []) if alvo is None else {}
        if self.compartilhada or not lista or not isinstance(porta,int) or not 0<porta<65536:return {"resumo":resumo}
        nav=limpeza.navegadores_conectados(porta,procs=lista)
        if not nav:return {"resumo":resumo}
        with self.processo(os.getpid()) as h: proprio=self.identidade(h,os.getpid())
        if not proprio or not proprio["sessao"] or self.j is None:return {"resumo":resumo}
        if alvo and alvo["tipo"] == "servico":
            # A autorização para controlar o serviço exige seu estado, sessão local,
            # painel conectado e transferências/atualizações verificados agora.
            return {"pronto":True, "processos":[], "elevado":self.admin,
                    "servicos":self._servicos_disponiveis({alvo["id"]} & SERVICOS_PAUSAVEIS, lista)}
        ativos=self.servicos_ativos()
        if ativos is None:return {"resumo":resumo}
        # PID do serviço e todos os seus trabalhadores são excluídos antes da seleção de apps.
        # O texto exibido usa exclusivamente os nomes públicos de categorias.
        if alvo is None:
            resumo=_resumo(lista+[{"nome":n} for _,n in ativos])
        raizes=set(limpeza.arvore_do_app(lista,pid_motor or os.getpid())) | set(nav)
        raizes.update(pid for pid,n in ativos if pid>4)
        sinal=limpeza.ler_em_uso() or {}
        raizes.update(v for v in sinal.get("pids",()) if isinstance(v,int))
        for p in lista:
            n=p["nome"].lower()
            # Processos auxiliares de aplicações clínicas e navegadores conectados também são protegidos.
            if n in _FORNECEDORES:continue
            if n=="epic" or _HOSPEDAGEM.search(n) or _CATEGORIAS["TPS / PACS"].search(n) or any(k in n for k in PRESERVAR if k not in ("explorer","system","services","wininit","winlogon","svchost","sihost","registry")):
                raizes.add(p["pid"])
        guardados=_descendentes(lista,raizes) | _ancestrais(lista,raizes)
        janelas={}
        for h in self.j.janelas():
            pid_janela = self.j.pid(h)
            if (alvo is None or pid_janela == alvo["id"]) and self.j.visivel(h):
                janelas.setdefault(pid_janela,[]).append(h)

        proc=[]
        for dado in lista:
            pid,nome=dado["pid"],dado["nome"].lower()
            if alvo and (alvo["tipo"]=="servico" or pid!=alvo["id"]):
                continue
            if (pid in guardados or _PROTECAO_DO_KIT.search(nome)
                    or any(k in nome for k in PRESERVAR)):continue
            if nome in NAVEGADORES and not _navegador_pessoal(self.j,pid,nome,janelas.get(pid,())):
                continue
            with self.processo(pid,0x400) as h:
                idn=self.identidade(h,pid)
                if not idn or self.elevado(h) is not False:continue
                conhecido=nome in _FORNECEDORES
                if conhecido and not _caminho_conhecido(nome,idn["caminho"]):continue
                if not conhecido and not _desktop_registrado(nome,idn["caminho"]):continue
                if (idn["usuario"],idn["sessao"])!=(proprio["usuario"],proprio["sessao"]):continue
                prioridade=self.prio(h)
                mem=_Memoria()
                mem.cb=ctypes.sizeof(mem)
                mb=(mem.trabalho+1048575)//1048576 if self.memoria(h,ctypes.byref(mem),mem.cb) else None
                try:idn["sha256"]=_hash(idn["caminho"])
                except OSError:continue
                if alvo and idn != alvo.get("identidade"):
                    continue
            proc.append(dict(pid=pid,nome=nome,identidade=idn,mesmo_usuario=True,protegido=False,
                             conhecido=conhecido,desktop_verificado=True,janelas=janelas.get(pid,[]),prioridade=prioridade,
                             memoria_mb=mb,perfil_independente=True))
        pendencias = {}
        serv = self._servicos_disponiveis(SERVICOS_PAUSAVEIS, lista, pendencias) if alvo is None and self.admin else {}
        chaves = [(p["identidade"]["caminho"], p["identidade"]["sha256"]) for p in proc]
        chaves.extend((path, sha) for path, sha, _ in pendencias.values())
        assinaturas = _assinantes_dos(chaves)
        proc = [p for p in proc if _aprovado(p["nome"], p["identidade"]["caminho"], p["identidade"]["sha256"],
                                            assinaturas[(p["identidade"]["caminho"], p["identidade"]["sha256"])])]
        for nome, (path, sha, esperado) in pendencias.items():
            if assinaturas.get((path,sha)) != esperado:
                serv.pop(nome, None)
        precisa_shell = alvo is None or alvo["tipo"]=="app"
        if alvo is None:
            # Só via IPC local processo->motor. O formulário recebe IDs aleatórios.
            resumo["_certificados"] = [[path, sha, dono] for (path,sha),dono in assinaturas.items() if dono]
            resumo["_certificados_servicos"] = [[nome,serv[nome]["identidade"],path,sha]
                                                for nome,(path,sha,_) in pendencias.items() if nome in serv]
        return {"pronto":True,"processos":proc,"servicos":serv,"elevado":self.admin,"resumo":resumo,
                "explorer_interativo":precisa_shell and bool(self.explorer_interativo(proprio))}

    def verificar_item(self,item):
        return selecionar(self.inventario(item["porta"],alvo=item),item["porta"])

    def explorer_interativo(self, proprio):
        # O shell da área de trabalho também pode hospedar a reabertura
        # quando todas as janelas de pasta foram fechadas.
        raiz=ctypes.create_unicode_buffer(32768)
        if not self.k.GetWindowsDirectoryW(raiz,len(raiz)):
            return []
        esperado=_normal(Path(raiz.value)/"explorer.exe")
        desktop = ctypes.WinDLL("user32").GetShellWindow
        desktop.restype = W.HWND
        shell = desktop()
        candidatos = [hw for hw in self.j.janelas()
                      if self.j.classe(hw) in ("CabinetWClass","ExploreWClass")]
        if shell and shell not in candidatos:
            candidatos.append(shell)
        alvos=[]
        for hw in candidatos:
            pid=self.j.pid(hw)
            with self.processo(pid) as h:
                idn=self.identidade(h,pid)
                if (not idn or idn["caminho"]!=esperado or idn["usuario"]!=proprio["usuario"]
                        or idn["sessao"]!=proprio["sessao"] or self.elevado(h) is not False):
                    continue
            alvos.append(int(hw))
        return alvos

    def elevado(self,h):
        tok=W.HANDLE()
        if not self.token(h,8,ctypes.byref(tok)):
            return None
        try:
            nivel=W.DWORD()
            n=W.DWORD()
            if self.tokeninfo(tok,20,ctypes.byref(nivel),ctypes.sizeof(nivel),ctypes.byref(n)):
                return bool(nivel.value)
            return None
        finally:
            self.close(tok)

    def transferencias_em_curso(self):
        pasta=ctypes.create_unicode_buffer(32768)
        if not self.k.GetSystemDirectoryW(pasta,len(pasta)):
            return {"BITS","DoSvc"}
        ps=Path(pasta.value)/"WindowsPowerShell"/"v1.0"/"powershell.exe"
        teste=("$ErrorActionPreference='Stop';$codigo=0;"
               "try { if (@(BitsTransfer\\Get-BitsTransfer -AllUsers).Count){$codigo+=1} } catch {$codigo+=1};"
               "try { if (@(DeliveryOptimization\\Get-DeliveryOptimizationStatus).Count){$codigo+=2} }"
               " catch {$codigo+=2};exit $codigo")
        env=os.environ.copy()
        env["PSModulePath"]=str(ps.parent/"Modules")
        try:
            r=subprocess.run([str(ps),"-NoLogo","-NoProfile","-NonInteractive","-Command",teste],
                             env=env,timeout=4,creationflags=subprocess.CREATE_NO_WINDOW,
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except (OSError,subprocess.TimeoutExpired):
            return {"BITS","DoSvc"}
        if r.returncode not in range(4):
            return {"BITS","DoSvc"}
        return {nome for bit,nome in ((1,"BITS"),(2,"DoSvc")) if r.returncode&bit}

    def atualizando(self, lista):
        if not lista or any(p["nome"].lower() in _INSTALADORES for p in lista):
            return True
        with self.servico("TrustedInstaller") as h:
            estado = _Status()
            n = W.DWORD()
            # Sem consulta verificável, não oferecer os serviços de atualização.
            return not (h and self.query(h,0,ctypes.byref(estado),ctypes.sizeof(estado),ctypes.byref(n))
                        and estado.estado == 1)

    def _mesma_instancia(self,h,item):
        atual=self.identidade(h,item["id"])
        if atual is None:return False
        salvo=item["identidade"]
        return all(atual[k]==salvo.get(k) for k in atual) and _hash(atual["caminho"])==salvo.get("sha256")

    def fechar_app(self,item):
        tinha_janela=item["janelas"]
        with self.processo(item["id"],0 if tinha_janela else 1) as h:
            if not h or not self._mesma_instancia(h,item):return False
            if not tinha_janela:
                # Se aparecer janela neste intervalo, o consentimento para instância sem janela expirou.
                if any(self.j.visivel(hw) and self.j.pid(hw)==item["id"] for hw in self.j.janelas()):
                    return False
                if self.espera(h,0)!=258 or not self.terminar(h,0):
                    return False
                if self.espera(h,1200)!=0:
                    raise RuntimeError("Término da instância ainda pendente")
                return True
            enviou=False
            for hw in self.j.janelas():
                if self.j.pid(hw)==item["id"] and self.j.existe(hw) and self.j.visivel(hw):
                    if self.espera(h,0)!=258:return False
                    enviou=self.j.fechar(hw) or enviou
            if not enviou:return False
            if self.espera(h,9500)==0:return True
            if not any(self.j.visivel(hw) and self.j.pid(hw)==item["id"] for hw in self.j.janelas()):
                raise RuntimeError("Pedido de fechamento aceito e ainda em transição")
            self.janela_ainda_aberta = True
            return False

    def ajustar_prioridade(self,item,restaurando=False):
        with self.processo(item["id"],0x200) as h:
            if not h:
                # Acesso negado nunca é confirmação de restauração.
                return bool(restaurando and ctypes.get_last_error()==87)
            if not self._mesma_instancia(h,item):
                atual=self.identidade(h,item["id"])
                return bool(restaurando and atual and atual["criado"]!=item["identidade"].get("criado"))
            atual=self.prio(h)
            if restaurando and atual!=_ABAIXO:return True
            if not restaurando and atual!=item["original"]:return False
            nova=item["original"] if restaurando else _ABAIXO
            return bool(self.mudar_prio(h,nova) and self.prio(h)==nova)

    def alterar_servico(self,item,restaurando=False):
        nome=item["id"]
        permitido = nome in SERVICOS_PAUSAVEIS or (restaurando and nome in _SERVICOS_SO_PARA_DEVOLVER)
        if not self.admin or not permitido or nome in SERVICOS_NUNCA:return False
        if not restaurando and nome.lower() in _ATUALIZACOES:
            lista=limpeza.processos()
            if self.atualizando(lista):return False
            if nome in ("BITS","DoSvc") and nome in self.transferencias_em_curso():return False
        with self.servico(nome,0x10 if restaurando else 0x20) as h:
            e=self.estado_servico(h,nome)
            if not e or e["identidade"]!=item["identidade"]:return False
            if restaurando:
                if e["estado"]==4:return True
                if e["estado"] in (2, 3):
                    raise BlockingIOError("O serviço ainda está mudando de estado.")
                if e["estado"] != 1:
                    return False
                if not self.start(h,0,None):
                    if ctypes.get_last_error() in (1053, 1055, 1061):
                        raise BlockingIOError("O gerenciador de serviços está ocupado.")
                    return False
            else:
                if e["estado"]!=4 or e["bloqueado"]:return False
                temp=_Status()
                if not self.control(h,1,ctypes.byref(temp)):return False
            fim=time.monotonic()+6
            while time.monotonic()<fim:
                atual=self.estado_servico(h,nome)
                if atual and atual["estado"]==(4 if restaurando else 1):return True
                time.sleep(.15)
            if restaurando:
                raise TimeoutError("O serviço aceitou a restauração e ainda está iniciando.")
            raise RuntimeError("O serviço aceitou o pedido mas a transição ainda não terminou")

    def reabrir(self,item):
        salvo=item["identidade"];nome=item["nome"]
        caminho=salvo["caminho"]
        with self.processo(os.getpid()) as h: proprio=self.identidade(h,os.getpid())
        if not proprio or (proprio["usuario"],proprio["sessao"])!=(salvo["usuario"],salvo["sessao"]):return False
        elegivel = _caminho_conhecido(nome,caminho) if nome in _FORNECEDORES else _desktop_registrado(nome,caminho)
        if not elegivel or _hash(caminho)!=salvo["sha256"]:return False
        if not _aprovado(nome,caminho,salvo["sha256"]):return False
        presente=_presenca_app(self,item)
        if presente is not False:
            return presente is True
        # A reabertura é sempre via shell interativo. O programa nunca é um filho do motor,
        # mesmo quando a Suite já está no token comum.
        hw=self.explorer_interativo(proprio)
        if not hw:
            return False
        # A janela do Explorer (já verificada no token interativo) abre o app. O filho nunca
        # recebe o token do Python elevado. Valores entram no ambiente, não em código PowerShell.
        pasta=ctypes.create_unicode_buffer(32768)
        if not self.k.GetSystemDirectoryW(pasta,len(pasta)):
            return False
        ps=Path(pasta.value)/"WindowsPowerShell"/"v1.0"/"powershell.exe"
        env=os.environ.copy()
        env.update(RADAI_REABRIR=caminho,RADAI_JANELAS=",".join(map(str,hw)))
        script=("$ErrorActionPreference='Stop';$alvos=$env:RADAI_JANELAS.Split(',');"
                "$shell=New-Object -ComObject Shell.Application;$janelas=$shell.Windows();"
                "$candidatas=@($janelas);try{$desktop=$janelas.Item([uint32]8);"
                "if($desktop){$candidatas+=@($desktop)}}catch{};foreach ($jan in $candidatas) {"
                "if($alvos -contains ([string][int64]$jan.HWND)){"
                "$jan.Document.Application.ShellExecute($env:RADAI_REABRIR,'','','open',1);exit 0}};exit 2")
        r=subprocess.run([str(ps),"-NoLogo","-NoProfile","-NonInteractive","-Command",script],env=env,
                         timeout=5,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        if r.returncode!=0:
            return False
        # ShellExecute confirma recebimento, não que o aplicativo subiu. A dúvida mantém a
        # restauração pendente no diário, sem bloquear o uso da Suite.
        limite=time.monotonic()+2.0
        while True:
            presente=_presenca_app(self,item)
            if presente is not False or time.monotonic()>=limite:
                return presente is True
            time.sleep(.12)


def _presenca_app(pf,item):
    vivos=limpeza.processos()
    if not vivos:
        return None
    salvo=item["identidade"]
    duvida=False
    for p in vivos:
        if p["nome"].lower()!=item["nome"]:
            continue
        with pf.processo(p["pid"]) as h:
            atual=pf.identidade(h,p["pid"])
            if not atual:
                duvida=True
            elif all(atual.get(k)==salvo[k] for k in ("sessao","usuario","caminho")):
                return True
    return None if duvida else False


def _plataforma():
    return Plataforma() if os.name=="nt" else None

def prever_com_resumo(porta=0,pf=None,pid_motor=None):
    resumo = {"preservados": [], "hospeda_servicos": False}
    try:
        pf=pf or _plataforma()
        inventario = {}
        if pf:
            inventario = pf.inventario(porta, pid_motor=pid_motor) if pid_motor is not None else pf.inventario(porta)
        resumo=dict(inventario.get("resumo",resumo),administrador=inventario.get("elevado"),
                    identificacao_pronta=bool(inventario.get("pronto")),
                    sem_shell=bool(inventario.get("pronto") and not inventario.get("explorer_interativo")))
        return selecionar(inventario,porta),resumo
    except (OSError,ValueError,TypeError,AttributeError,KeyError,subprocess.TimeoutExpired):
        return [],resumo

def prever(porta=0,pf=None):
    return prever_com_resumo(porta,pf)[0]

def aplicar(item,pf=None):
    try:
        pf=pf or _plataforma()
        if not pf:return False
        atuais = pf.verificar_item(item) if hasattr(pf,"verificar_item") else prever(item["porta"],pf)
        for atual in atuais:
            # O working set pode mudar entre o clique e a ação. A classe de seleção, inclusive o limite
            # de 300 MB e o estado das janelas, continua parte da comparação.
            if {k:v for k,v in atual.items() if k!="memoria_mb"} != {k:v for k,v in item.items() if k!="memoria_mb"}:
                continue
            if item["tipo"]=="app":return pf.fechar_app(item)
            if item["tipo"]=="servico":return pf.alterar_servico(item)
            if item["tipo"]=="prioridade":return pf.ajustar_prioridade(item)
        return False
    except (OSError,ValueError,TypeError,AttributeError,KeyError,subprocess.TimeoutExpired):
        return False

def aplicar_com_detalhe(item, pf=None):
    pf = pf or _plataforma()
    if pf is None:
        return False, False
    pf.janela_ainda_aberta = False
    return aplicar(item, pf), pf.janela_ainda_aberta


def restaurar(item,pf=None):
    try:
        pf=pf or _plataforma()
        if not pf:return False
        tipo,nome=item["tipo"],item["nome"]
        if tipo=="servico":
            return bool(item.get("original")==4 and nome==item["id"] and pf.alterar_servico(item,True))
        if _PROTECAO_DO_KIT.search(nome) or any(k in nome for k in PRESERVAR):return False
        if tipo=="prioridade" and item.get("original") in _PRIORIDADES:return pf.ajustar_prioridade(item,True)
        if tipo=="app":return pf.reabrir(item)
        return tipo=="memoria"
    except (BlockingIOError, TimeoutError):
        raise
    except (OSError,ValueError,TypeError,AttributeError,KeyError,subprocess.TimeoutExpired):
        return False
