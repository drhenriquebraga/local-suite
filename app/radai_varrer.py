# -*- coding: utf-8 -*-
import os
import threading
import time
import uuid

DIAS_DO_FILTRO = (1, 3, 7, 30, 0)
DIAS_PADRAO = 7

TETO_PASTAS = 20000
TETO_SERIES = 500
TETO_ARQUIVOS = 200000
TETO_GUARDADAS = 8
TETO_RODANDO = 3
VALIDADE_S = 900.0

SEM_PASTA = u"informe a pasta"
PASTA_NAO_ENCONTRADA = u"Pasta não encontrada."
USO_DESCONHECIDO = u"esta tela não tem varredura de pasta"
VARREDURA_DESCONHECIDA = (u"Esta busca não existe mais — o programa pode ter "
                          u"sido reiniciado. Procure de novo.")
BUSCA_INTERROMPIDA = (u"A busca foi interrompida: a lista tem só o que foi "
                      u"achado até ali.")
BUSCA_CORTADA_PASTAS = (u"A busca parou depois de %d pastas olhadas. Aponte "
                        u"a pasta do exame, e não a raiz do disco.")
BUSCA_CORTADA_SERIES = (u"A busca parou em %d séries. Aponte uma pasta mais "
                        u"perto do exame.")
BUSCA_CORTADA_ARQUIVOS = (u"A busca parou depois de %d arquivos lidos. Aponte "
                          u"a pasta do exame, e não a raiz do disco.")
PASTAS_ILEGIVEIS = (u"%d pasta(s) não puderam ser lidas e ficaram de fora "
                    u"da lista.")
ZIPS_NAO_ABERTOS = (u"A busca não abre .zip, e esta pasta tem %d. Extraia o "
                    u"arquivo e aponte a pasta extraída.")

_USOS = {}
_VARREDURAS = {}
_TRAVA = threading.Lock()


class Uso(object):
    def __init__(self, nome, ler, linhas, fechar=None, iniciar=None,
                 pular=None, filtra=True):
        self.nome = str(nome)
        self.ler = ler
        self.linhas = linhas
        self.fechar = fechar
        self.iniciar = iniciar
        self.pular = pular or _pular_padrao
        self.filtra = bool(filtra)


def registrar(nome, ler, linhas, fechar=None, iniciar=None, pular=None,
              filtra=True):
    u = Uso(nome, ler, linhas, fechar=fechar, iniciar=iniciar, pular=pular,
            filtra=filtra)
    with _TRAVA:
        _USOS[u.nome] = u
    return u


def uso(nome):
    with _TRAVA:
        return _USOS.get(str(nome or u""))


def _pular_padrao(nome):
    import radai_dicom
    return radai_dicom.pular_na_busca(nome)


def normalizar_dias(valor):
    try:
        d = int(valor)
    except (TypeError, ValueError):
        return DIAS_PADRAO
    return d if d in DIAS_DO_FILTRO else DIAS_PADRAO


def limite_da_data(dias, agora=None):
    d = normalizar_dias(dias)
    if not d:
        return None
    return float(agora if agora is not None else time.time()) - d * 86400.0


def dentro_da_data(pasta, limite):
    if limite is None:
        return True
    try:
        return os.stat(pasta).st_mtime >= limite
    except OSError:
        # GUARDA: pasta que não responde ao stat não some calada da lista: ela é lida.
        return True


def _novo(nome, pasta, dias, opcoes):
    return {"v": uuid.uuid4().hex, "uso": nome, "pasta": pasta, "raiz": pasta,
            "dias": dias, "limite": limite_da_data(dias), "opcoes": opcoes,
            "inicio": time.time(), "fim_em": None, "fim": False,
            "parado": False, "erro": None, "pastas": 0, "arquivos": 0,
            "fora_da_data": 0, "falhas": 0, "zips": 0, "cortada": None,
            "versao": 0, "linhas": [], "extra": {}, "final": False,
            "etapa": "lendo", "dados": {}, "trava": threading.Lock()}


def publicar(job, linhas, extra=None, final=False):
    with job["trava"]:
        job["linhas"] = list(linhas or ())
        if extra:
            job["extra"] = dict(extra)
        job["final"] = bool(final) or job["final"]
        job["versao"] += 1


def contar_arquivo(job, n=1):
    job["arquivos"] += int(n)


def _falhou(job):
    def _f(_erro):
        job["falhas"] += 1
    return _f


def trabalhar(job, u):
    try:
        if u.iniciar is not None:
            u.iniciar(job)
        if job["erro"]:
            return
        raiz = job["raiz"]
        if not os.path.isdir(raiz):
            job["erro"] = PASTA_NAO_ENCONTRADA
            return
        limite = job["limite"] if u.filtra else None
        for atual, dirs, arqs in os.walk(raiz, onerror=_falhou(job)):
            if job["parado"]:
                break
            dirs[:] = sorted(d for d in dirs if not u.pular(d))
            job["pastas"] += 1
            if arqs:
                if not dentro_da_data(atual, limite):
                    job["fora_da_data"] += 1
                elif u.ler(job, atual, sorted(arqs)):
                    publicar(job, u.linhas(job))
            if job["parado"]:
                break
            if job["pastas"] >= TETO_PASTAS:
                job["cortada"] = "pastas"
                break
            if job["arquivos"] >= TETO_ARQUIVOS:
                job["cortada"] = "arquivos"
                break
            if len(job["linhas"]) >= TETO_SERIES:
                job["cortada"] = "series"
                break
        job["etapa"] = "fechando"
        if u.fechar is not None:
            linhas, extra = u.fechar(job)
        else:
            linhas, extra = u.linhas(job), {}
        publicar(job, linhas, extra, final=True)
    except Exception as e:
        job["erro"] = u"%s: %s" % (type(e).__name__, str(e)[:200])
    finally:
        job["fim_em"] = time.time()
        job["fim"] = True


def avisos(job):
    fora = []
    if job.get("parado"):
        fora.append(BUSCA_INTERROMPIDA)
    c = job.get("cortada")
    if c == "pastas":
        fora.append(BUSCA_CORTADA_PASTAS % int(job.get("pastas") or 0))
    elif c == "series":
        fora.append(BUSCA_CORTADA_SERIES % len(job.get("linhas") or ()))
    elif c == "arquivos":
        fora.append(BUSCA_CORTADA_ARQUIVOS % int(job.get("arquivos") or 0))
    if job.get("zips"):
        fora.append(ZIPS_NAO_ABERTOS % int(job["zips"]))
    if job.get("falhas"):
        fora.append(PASTAS_ILEGIVEIS % int(job["falhas"]))
    return fora


def _faxina(agora=None):
    agora = time.time() if agora is None else agora
    for v, j in list(_VARREDURAS.items()):
        if j["fim"] and agora - float(j["fim_em"] or agora) > VALIDADE_S:
            _VARREDURAS.pop(v, None)
    prontas = sorted((j for j in _VARREDURAS.values() if j["fim"]),
                     key=lambda j: j["inicio"])
    while prontas and len(_VARREDURAS) >= TETO_GUARDADAS:
        _VARREDURAS.pop(prontas.pop(0)["v"], None)
    rodando = sorted((j for j in _VARREDURAS.values() if not j["fim"]),
                     key=lambda j: j["inicio"])
    while len(rodando) >= TETO_RODANDO:
        rodando.pop(0)["parado"] = True


def iniciar(nome, pasta, dias=None, opcoes=None, em_segundo_plano=True):
    u = uso(nome)
    if u is None:
        return {"erro": USO_DESCONHECIDO, "fim": True}
    pasta = str(pasta or u"").strip().strip('"')
    if not pasta:
        return {"erro": SEM_PASTA, "fim": True}
    dias = normalizar_dias(dias) if u.filtra else 0
    job = _novo(u.nome, pasta, dias, dict(opcoes or {}))
    with _TRAVA:
        _faxina()
        _VARREDURAS[job["v"]] = job
    if em_segundo_plano:
        threading.Thread(target=trabalhar, args=(job, u), daemon=True,
                         name="radai_varrer").start()
    else:
        trabalhar(job, u)
    return estado(job["v"])


def estado(v, versao=None):
    with _TRAVA:
        job = _VARREDURAS.get(str(v or u""))
    if job is None:
        return {"erro": VARREDURA_DESCONHECIDA, "fim": True,
                "desconhecida": True}
    with job["trava"]:
        d = {"v": job["v"], "uso": job["uso"], "fim": job["fim"],
             "final": job["final"], "parado": job["parado"],
             "erro": job["erro"], "etapa": job["etapa"],
             "pastas": job["pastas"],
             "arquivos": job["arquivos"], "fora_da_data": job["fora_da_data"],
             "dias": job["dias"], "series": len(job["linhas"]),
             "versao": job["versao"], "avisos": avisos(job),
             "segundos": round(time.time() - job["inicio"], 1)}
        if versao is None or str(versao) != str(job["versao"]):
            d["linhas"] = list(job["linhas"])
        if job["final"]:
            d["extra"] = dict(job["extra"])
    return d


def parar(v):
    with _TRAVA:
        job = _VARREDURAS.get(str(v or u""))
    if job is None:
        return estado(v)
    job["parado"] = True
    return estado(v)


MODALIDADES_DAS_SERIES = ("CT", "MR")
TETO_MIN_CORTES = 1000


def _opcoes_das_series(job):
    o = job.get("opcoes") or {}
    mods = o.get("modalidades")
    if isinstance(mods, (list, tuple)) and mods:
        mods = tuple(str(m).upper()[:8] for m in mods if str(m).strip())[:8]
    else:
        mods = MODALIDADES_DAS_SERIES
    try:
        piso = max(1, min(TETO_MIN_CORTES, int(o.get("min_cortes") or 1)))
    except (TypeError, ValueError):
        piso = 1
    return mods, piso


def _iniciar_series(job, resolver=None):
    import radai_dicom
    if resolver is not None:
        alvo, erro = resolver(job["pasta"])
        if erro or not alvo:
            job["erro"] = erro or PASTA_NAO_ENCONTRADA
            return
        job["pasta"] = alvo
    job["raiz"] = radai_dicom.caminho_longo(job["pasta"])
    mods, piso = _opcoes_das_series(job)
    job["dados"] = {"por_uid": {}, "mods": mods, "piso": piso}


def linha_da_serie(pasta, s, bilhete):
    import radai_dicom
    linha = radai_dicom._linha_da_serie(pasta, s)
    uid = linha["uid"]
    linha.pop("pasta", None)
    linha.update({"bilhete": bilhete, "curto": uid[-12:],
                  "desc": linha.get("descricao") or u"",
                  "date": linha.get("data") or u""})
    return linha


def _ler_series(job, pasta, nomes, enriquecer=None):
    import radai_dicom
    import radai_thumbnail
    d = job["dados"]
    r = radai_dicom.varrer_pasta(pasta, parar=lambda: job["parado"],
                                 ao_ler=lambda: contar_arquivo(job),
                                 nomes=nomes)
    if r.get("erro"):
        job["falhas"] += 1
    job["zips"] += sum(1 for n, _p in r.get("ignorados") or ()
                       if str(n).lower().endswith(u".zip"))
    mudou = False
    irmas = tuple(str(x.get("uid") or u"") for x in r.get("series") or ())
    for s in r.get("series") or ():
        mod = str(s.get("modalidade") or u"").upper()
        if mod not in d["mods"] or int(s.get("cortes") or 0) < d["piso"]:
            continue
        velha = d["por_uid"].get(s["uid"])
        # GUARDA: série repartida em pastas fica na pasta que tem mais cortes dela.
        if velha is not None and velha["cortes"] >= int(s.get("cortes") or 0):
            continue
        b = radai_thumbnail.registrar_series(pasta, [s]).get(s["uid"])
        linha = linha_da_serie(pasta, s, b)
        if enriquecer is not None and enriquecer(
                linha, pasta, dict(s, irmas=irmas)) is False:
            continue
        d["por_uid"][s["uid"]] = linha
        mudou = True
    return mudou


def _linhas_series(job):
    return list(job["dados"].get("por_uid", {}).values())


def registrar_series_de_pasta(nome, enriquecer=None, resolver=None):
    return registrar(
        nome, lambda job, pasta, nomes: _ler_series(job, pasta, nomes,
                                                    enriquecer),
        _linhas_series, iniciar=lambda job: _iniciar_series(job, resolver))


registrar_series_de_pasta("series")


RESOURCETYPE_DISK = 1
DRIVE_REMOTE = 4
SEM_DIALOGO = u"o mapeamento de unidade só existe no Windows"
MAPEAMENTO_CANCELADO = u"nenhuma unidade foi mapeada"


def letras_de_rede():
    if os.name != "nt":
        return []
    try:
        import ctypes
        k = ctypes.windll.kernel32
        mapa = int(k.GetLogicalDrives())
        fora = []
        for i in range(26):
            if mapa & (1 << i):
                raiz = u"%s:\\" % chr(65 + i)
                if int(k.GetDriveTypeW(raiz)) == DRIVE_REMOTE:
                    fora.append(raiz)
        return fora
    except Exception:
        return []


def _janelas_deste_processo():
    import ctypes
    from ctypes import wintypes
    u32 = ctypes.windll.user32
    meu = os.getpid()
    fora = []
    CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _ver(h, _l):
        pid = wintypes.DWORD(0)
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value == meu and u32.IsWindowVisible(h):
            fora.append(h)
        return True
    u32.EnumWindows(CB(_ver), 0)
    return fora


def _trazer_para_frente(fim, prazo_s=6.0):
    try:
        import ctypes
        u32 = ctypes.windll.user32
        HWND_TOPMOST = -1
        SWP = 0x0001 | 0x0002 | 0x0040
        t0 = time.time()
        vistas = set()
        while not fim.is_set() and time.time() - t0 < prazo_s:
            for h in _janelas_deste_processo():
                if h in vistas:
                    continue
                vistas.add(h)
                # GUARDA: o motor não tem o primeiro plano; sem topmost o diálogo nasce atrás do navegador.
                u32.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0, SWP)
                u32.SetForegroundWindow(h)
            time.sleep(0.15)
    except Exception:
        pass


def _dialogo_do_windows():
    import ctypes
    from ctypes import wintypes
    resultado = {}

    def _abrir():
        ole = None
        try:
            ole = ctypes.windll.ole32
            ole.CoInitializeEx(None, 2)
        except Exception:
            ole = None
        try:
            f = ctypes.WinDLL("mpr").WNetConnectionDialog
            f.argtypes = [wintypes.HWND, wintypes.DWORD]
            f.restype = wintypes.DWORD
            resultado["codigo"] = int(f(None, RESOURCETYPE_DISK))
        except Exception as e:
            resultado["erro"] = u"%s: %s" % (type(e).__name__, str(e)[:160])
        finally:
            if ole is not None:
                try:
                    ole.CoUninitialize()
                except Exception:
                    pass

    fim = threading.Event()
    frente = threading.Thread(target=_trazer_para_frente, args=(fim,),
                              daemon=True, name="radai_mapear_frente")
    frente.start()
    t = threading.Thread(target=_abrir, daemon=True, name="radai_mapear")
    t.start()
    t.join()
    fim.set()
    if "erro" in resultado:
        raise OSError(resultado["erro"])
    return resultado.get("codigo", -1)


def mapear_unidade(dialogo=None, letras=None):
    if dialogo is None and os.name != "nt":
        return {"ok": False, "erro": SEM_DIALOGO, "novas": []}
    dialogo = dialogo or _dialogo_do_windows
    letras = letras or letras_de_rede
    antes = set(letras())
    try:
        codigo = int(dialogo())
    except Exception as e:
        return {"ok": False, "erro": u"%s" % str(e)[:200], "novas": []}
    novas = sorted(set(letras()) - antes)
    if codigo == 0:
        return {"ok": True, "novas": novas}
    if codigo in (-1, 0xFFFFFFFF):
        return {"ok": False, "cancelado": True, "novas": novas,
                "erro": MAPEAMENTO_CANCELADO if not novas else u""}
    return {"ok": False, "novas": novas,
            "erro": u"o Windows recusou o mapeamento (código %d)" % codigo}


def montar(app):
    from fastapi import Request

    async def _corpo(request):
        try:
            c = await request.json()
        except Exception:
            c = None
        return c if isinstance(c, dict) else {}

    def _erro(e):
        return {"erro": u"%s: %s" % (type(e).__name__, str(e)[:200]),
                "fim": True}

    @app.post("/api/varrer/iniciar")
    async def _iniciar(request: Request):
        try:
            c = await _corpo(request)
            return iniciar(c.get("uso") or u"series", c.get("pasta"),
                           c.get("dias"), c.get("opcoes"))
        except Exception as e:
            return _erro(e)

    @app.post("/api/varrer/estado")
    async def _estado(request: Request):
        try:
            c = await _corpo(request)
            return estado(c.get("v"), c.get("versao"))
        except Exception as e:
            return _erro(e)

    @app.post("/api/varrer/parar")
    async def _parar(request: Request):
        try:
            c = await _corpo(request)
            return parar(c.get("v"))
        except Exception as e:
            return _erro(e)

    @app.post("/api/pastas/mapear")
    async def _mapear():
        try:
            import radai_web
            return await radai_web.no_threadpool(mapear_unidade)
        except Exception as e:
            return {"ok": False, "erro": u"%s: %s" % (type(e).__name__,
                                                      str(e)[:200])}

    return app
