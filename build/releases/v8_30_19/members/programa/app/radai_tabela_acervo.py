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


def linhas(limite=LIMITE, parar=None, com_arquivo=False):
    try:
        import radai_archive
        fora, sumiram = [], 0
        # O índice já contém a lista. Só se abre uma pasta ao pedir seu conteúdo.
        for reg in radai_archive.ler_acervo():
            if parar and parar():
                break
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
            if com_arquivo:
                fora[-1]["arquivo_indexado"] = os.path.basename(str(reg.get("rs") or ""))
            if len(fora) >= int(limite or LIMITE):
                break
        return {"series": fora, "sumiram": sumiram}
    except Exception as e:
        return {"series": [], "sumiram": 0,
                "erro": u"%s: %s" % (type(e).__name__, str(e)[:160])}


def resolver(bilhete, conhecidas=None):
    try:
        import radai_archive
        import radai_thumbnail
    except Exception:
        return None, None
    pasta, uid = radai_thumbnail.resolver(bilhete)
    if not pasta or not uid:
        return None, None
    if conhecidas is None:
        conhecidas = {_chave(r.get("pasta"), r.get("uid")) for r in radai_archive.ler_acervo()}
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


def _cabecalho_da_serie(pasta, uid, parar=None):
    try:
        import pydicom
        with os.scandir(pasta) as entradas:
            return _buscar_cabecalho(entradas, pasta, uid, pydicom, parar)
    except (ImportError, OSError):
        return u"", u"", None


def _buscar_cabecalho(entradas, pasta, uid, pydicom, parar):
    lidos = 0
    for entrada in entradas:
        if parar and parar():
            break
        n = entrada.name
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


def detalhe_da_serie(pasta, uid, parar=None):
    done = _ler_done(pasta, uid)
    if parar and parar():
        return _vazio()
    nome, mod, esp = _cabecalho_da_serie(pasta, uid, parar)
    tasks = (done.get("tasks_ok") or done.get("tasks_da_serie")
             or done.get("tasks") or [])
    try:
        cortes = int(done.get("cortes")) if done.get("cortes") else None
    except Exception:
        cortes = None
    return {"nome": nome,
                 "modalidade": mod or str(done.get("modalidade") or u""),
                 "espessura_mm": esp, "cortes": cortes,
                 "modo": str(done.get("modo") or u""),
                 "tasks": [str(t) for t in tasks if t][:60],
                 "protocolos": [str(p) for p in (done.get("protocolos")
                                                 or []) if p][:20],
                 "faltou": _faltou(done)[:60]}


def detalhes(bilhetes, parar=None):
    import radai_archive
    conhecidas = {_chave(r.get("pasta"), r.get("uid")) for r in radai_archive.ler_acervo()}
    fora = []
    for b in list(bilhetes or ())[:LOTE_DE_DETALHES]:
        if parar and parar():
            break
        pasta, uid = resolver(b, conhecidas)
        fora.append(detalhe_da_serie(pasta, uid, parar) if pasta else _vazio())
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
            from radai_leitura_ativa import executar
            return await executar(request, linhas, limite)
        except (OSError, RuntimeError) as e:
            return {"series": [], "erro": str(e)}

    @app.post(ROTA_DETALHES)
    async def _detalhes(request: Request):
        try:
            c = await request.json() or {}
            bs = [str(b) for b in list((c or {}).get("bilhetes") or [])
                  if isinstance(b, str)][:LOTE_DE_DETALHES]
        except Exception:
            return {"itens": [], "erro": u"pedido ilegível"}
        try:
            from radai_leitura_ativa import executar, bilhete_de_rede
            grupos = {False: [], True: []}
            for i, b in enumerate(bs):
                grupos[bilhete_de_rede(b)].append((i, b))
            itens = [_vazio() for _ in bs]
            for rede, grupo in grupos.items():
                if not grupo:
                    continue
                try:
                    dados = await executar(request, detalhes, [b for _, b in grupo],
                                           rede=rede, prazo=4 if rede else None)
                except (OSError, RuntimeError):
                    if rede:
                        break
                    raise
                for (i, _), linha in zip(grupo, dados):
                    itens[i] = linha
            return {"itens": itens}
        except Exception as e:
            return {"itens": [], "erro": type(e).__name__}

    return app
