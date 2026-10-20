# -*- coding: utf-8 -*-
import json
import os

COLUNAS = (u"Data do exame", u"Paciente", u"ID", u"Modalidade", u"Cortes",
           u"Espessura", u"Estruturas", u"Modo", u"Tasks", u"Contornada em",
           u"Levou", u"Abrir")

ROTA = u"/api/acervo/tabela"
ROTA_DETALHES = u"/api/acervo/tabela/detalhes"

LIMITE = 60
LOTE_DE_DETALHES = 12
TETO_DE_ARQUIVOS_LIDOS = 400


def _bilhete(pasta, uid):
    import radai_thumbnail
    return radai_thumbnail.bilhete(pasta, uid)


def _chave(pasta, uid):
    return (os.path.normcase(os.path.abspath(str(pasta or u""))), str(uid or u""))


def linhas(limite=LIMITE):
    try:
        import radai_archive
        fora, sumiram = [], 0
        for reg in radai_archive.conferir_acervo():
            estado = str(reg.get("estado") or "ok")
            if estado == "sem_pasta":
                sumiram += 1
                continue
            pasta, uid = str(reg.get("pasta") or u""), str(reg.get("uid") or u"")
            if not pasta or not uid:
                continue
            fora.append({"bilhete": _bilhete(pasta, uid),
                         "uid8": uid[-8:],
                         "pid": str(reg.get("pid") or u""),
                         "date": str(reg.get("date") or u""),
                         "estruturas": int(reg.get("estruturas") or 0),
                         "secs": int(reg.get("secs") or 0),
                         "quando": str(reg.get("quando") or u""),
                         "estado": estado})
            if len(fora) >= int(limite or LIMITE):
                break
        return {"series": fora, "sumiram": sumiram}
    except Exception as e:
        return {"series": [], "sumiram": 0,
                "erro": u"%s: %s" % (type(e).__name__, str(e)[:160])}


def resolver(bilhete):
    try:
        import radai_archive
        import radai_thumbnail
    except Exception:
        return None, None
    pasta, uid = radai_thumbnail.resolver(bilhete)
    if not pasta or not uid:
        return None, None
    conhecidas = set(_chave(r.get("pasta"), r.get("uid"))
                     for r in radai_archive.ler_acervo())
    if _chave(pasta, uid) not in conhecidas:
        return None, None
    return pasta, uid


def _ler_done(pasta, uid):
    uid = str(uid or u"")
    if not uid or any(c in uid for c in ("/", "\\", ":", "\x00")):
        return {}
    try:
        with open(os.path.join(pasta, "_RadAI", uid + ".done.json"),
                  encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _cabecalho_da_serie(pasta, uid):
    try:
        import pydicom
    except Exception:
        return u"", u"", None
    try:
        nomes = sorted(os.listdir(pasta))
    except Exception:
        return u"", u"", None
    lidos = 0
    for n in nomes:
        if n.startswith(("RS_", "_RadAI", ".")) or n.lower().endswith(
                (".json", ".txt", ".npz", ".zip", ".dir")):
            continue
        fp = os.path.join(pasta, n)
        if not os.path.isfile(fp):
            continue
        lidos += 1
        if lidos > TETO_DE_ARQUIVOS_LIDOS:
            break
        try:
            ds = pydicom.dcmread(fp, stop_before_pixels=True, force=True,
                                 specific_tags=["SeriesInstanceUID",
                                                "PatientName", "Modality",
                                                "SliceThickness",
                                                "SpacingBetweenSlices"])
        except Exception:
            continue
        if str(getattr(ds, "SeriesInstanceUID", "") or "") != str(uid):
            continue
        nome = u" ".join(str(getattr(ds, "PatientName", "") or "")
                         .replace("^", " ").split())
        esp = None
        for k in ("SpacingBetweenSlices", "SliceThickness"):
            try:
                v = float(getattr(ds, k, 0) or 0)
            except Exception:
                v = 0.0
            if v > 0:
                esp = round(v, 2)
                break
        return nome, str(getattr(ds, "Modality", "") or "").upper(), esp
    return u"", u"", None


def _faltou(done):
    try:
        import radai_records
        return list(radai_records.nomes_do_faltou(done) or [])
    except Exception:
        return []


def _vazio():
    return {"nome": u"", "modalidade": u"", "espessura_mm": None,
            "cortes": None, "modo": u"", "tasks": [], "protocolos": [],
            "faltou": []}


def detalhes(bilhetes):
    fora = []
    for b in list(bilhetes or ())[:LOTE_DE_DETALHES]:
        pasta, uid = resolver(b)
        if not pasta:
            fora.append(_vazio())
            continue
        done = _ler_done(pasta, uid)
        nome, mod, esp = _cabecalho_da_serie(pasta, uid)
        tasks = (done.get("tasks_ok") or done.get("tasks_da_serie")
                 or done.get("tasks") or [])
        try:
            cortes = int(done.get("cortes")) if done.get("cortes") else None
        except Exception:
            cortes = None
        fora.append({"nome": nome,
                     "modalidade": mod or str(done.get("modalidade") or u""),
                     "espessura_mm": esp, "cortes": cortes,
                     "modo": str(done.get("modo") or u""),
                     "tasks": [str(t) for t in tasks if t][:60],
                     "protocolos": [str(p) for p in (done.get("protocolos")
                                                     or []) if p][:20],
                     "faltou": _faltou(done)[:60]})
    return fora


def html(ident, classe=u""):
    import html as _h
    return (u'<div class="ui-acervo%s" id="%s" data-ui-acervo>'
            u'<div class="ui-esqueleto ui-esq-l"></div>'
            u'<div class="ui-esqueleto ui-esq-l"></div>'
            u'<div class="ui-esqueleto ui-esq-l"></div></div>'
            % ((u" " + _h.escape(classe, quote=True)) if classe else u"",
               _h.escape(ident or u"", quote=True)))


def montar(app):
    from fastapi import Request

    @app.post(ROTA)
    async def _linhas(request: Request):
        try:
            c = await request.json() or {}
        except Exception:
            c = {}
        try:
            limite = max(1, min(200, int((c or {}).get("limite") or LIMITE)))
        except Exception:
            limite = LIMITE
        try:
            import radai_web
            return await radai_web.no_threadpool(linhas, limite)
        except Exception:
            return linhas(limite)

    @app.post(ROTA_DETALHES)
    async def _detalhes(request: Request):
        try:
            c = await request.json() or {}
            bs = [str(b) for b in list((c or {}).get("bilhetes") or [])
                  if isinstance(b, str)][:LOTE_DE_DETALHES]
        except Exception:
            return {"itens": [], "erro": u"pedido ilegível"}
        try:
            import radai_web
            return {"itens": await radai_web.no_threadpool(detalhes, bs)}
        except Exception as e:
            return {"itens": [], "erro": type(e).__name__}

    return app
