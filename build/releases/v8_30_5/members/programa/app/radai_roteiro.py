"""Guia da estação e uma dica por abertura interativa do motor local."""
import json
from functools import lru_cache
from pathlib import Path
from threading import RLock
from uuid import uuid4

import radai_config as config


CHAVE = "GUIA_VISTO"
VERSAO_DO_GUIA = "2"
ROTA_API = "/api/roteiro"
MARCA = "radai-roteiro-js"
DATA = Path(__file__).resolve().parent / "data"
ARQUIVO_DICAS = "local-suite-dicas-vistas.json"

# IDs persistentes independem da ordem visual e do idioma.
DESTINOS = {
    "fast": "/config#ps_fast", "liver": "/lote", "jpeg": "/bridge/laudo",
    "destination": "/lote", "custom": "/lote", "neck": "/lote", "motion": "/lote",
    "bolus": "/bolus/gerar", "cns": "/lote", "nidus": "/neuro/nidus",
    "compare": "/ver", "video": "/recon3d/anatomia", "names": "/config#ps_estruturas",
    "protocols": "/config#ps_estruturas", "overnight": "/vigia", "stations": "/vigia",
    "queue": "/vigia", "transfer": "/config", "offline": "", "references": "/bibliografia",
    "plugins": "", "glioma": "/neuro/glioma", "metastasis": "/neuro/metastasis",
    "anatomy": "/neuro/anatomia", "nodules": "/lung/nodulos", "brachy": "/bolus/aplicador",
    "disc": "/bridge/laudo", "mold": "/bolus/gerar", "meningioma": "/neuro/meningioma",
    "followup": "/lung/rastreio",
}

PASSOS = (
    {"rota": "/", "alvo": "", "titulo": "welcome", "texto": "greeting"},
    {"rota": "/bridge/laudo", "alvo": "", "nome": "DicomBridge", "dica": "jpeg"},
    {"rota": "/lote", "alvo": "", "titulo": "run", "texto": "runbody"},
    {"rota": "/config", "fragmento": "ps_fast", "alvo": 'a[href="#ps_fast"]',
     "titulo": "fast", "dica": "fast", "imagem": "/api/fast/preview/thorax/2"},
    {"rota": "/ver", "alvo": "", "titulo": "compare", "dica": "compare"},
    {"rota": "/recon3d/anatomia", "alvo": "", "nome": "3D", "dica": "video"},
    {"rota": "/vigia", "alvo": "", "titulo": "night", "dica": "overnight"},
)


@lru_cache(maxsize=1)
def _catalogo():
    return json.loads((DATA / "dicas-suite.json").read_text(encoding="utf8"))


def visto(valor):
    return str(valor or "").split("#")[0].strip() == VERSAO_DO_GUIA


def ler_marca(caminho=None):
    return config.ler_arquivo(caminho or config.caminho_padrao())[1].get(CHAVE, "")


def gravar_marca(caminho=None):
    return config.escrever(caminho or config.caminho_padrao(), {CHAVE: VERSAO_DO_GUIA})


class Sessao:
    def __init__(self, caminho=None):
        self.cfg = Path(caminho or config.caminho_padrao())
        self.historico = self.cfg.with_name(ARQUIVO_DICAS)
        self.trava = RLock()
        self.id = uuid4().hex
        self.dono = None
        self.encerrada = False
        self.reserva = None
        self.convite = None

    def convidar_reabertura(self):
        # Ler a página de reabertura não consome uma dica. O clique em
        # Continuar leva o convite à aba escolhida, que o consome uma vez.
        with self.trava:
            self.convite = uuid4().hex
            return self.convite

    def habilitadas(self):
        valor = config.ler_arquivo(self.cfg)[1].get("DICAS_AO_INICIAR", "1")
        return valor.split("#")[0].strip() != "0"

    def lidos(self):
        try:
            ids = json.loads(self.historico.read_text(encoding="utf8"))
            if isinstance(ids, list):
                return [i for i in ids if isinstance(i, str) and i in DESTINOS]
        except (FileNotFoundError, json.JSONDecodeError, UnicodeError):
            pass
        return []

    def dica(self):
        if not self.habilitadas():
            self.encerrada = True
            return {"tipo": "nada"}
        if self.reserva is None:
            historico = self.lidos()
            restantes = [i for i in DESTINOS if i not in historico]
            if not restantes:
                restantes = [i for i in DESTINOS if i != historico[-1]]
            self.reserva = restantes[0]
        return {"tipo": "dica", "id": self.reserva, "url": DESTINOS[self.reserva]}

    def agir(self, acao, aba, ident=None):
        with self.trava:
            if acao == "preferencia":
                if not isinstance(ident, bool):
                    raise ValueError("preferencia")
                ok, erro = config.escrever(self.cfg, {"DICAS_AO_INICIAR": "1" if ident else "0"})
                if not ok:
                    raise OSError(erro)
                if not ident and self.reserva is not None:
                    self.encerrada = True
                return {"mostrar": ident}
            if acao == "estado":
                return {"visto": visto(ler_marca(self.cfg)), "mostrar": self.habilitadas()}
            if not isinstance(aba, str) or not (8 <= len(aba) <= 80) or not aba.isascii():
                raise ValueError("aba")
            if acao == "inicio" and self.convite and ident == self.convite:
                self.dono, self.encerrada, self.reserva, self.convite = aba, False, None, None
            if self.encerrada or self.dono not in (None, aba):
                return {"tipo": "nada"}
            if acao == "inicio":
                self.dono = aba
                if not visto(ler_marca(self.cfg)):
                    return {"tipo": "guia"}
                return self.dica()
            if self.dono != aba:
                return {"tipo": "nada"}
            if acao == "concluir":
                ok, erro = gravar_marca(self.cfg)
                if not ok:
                    raise OSError(erro)
                return self.dica()
            if acao == "exibida" and self.reserva and ident == self.reserva:
                historico = self.lidos()
                if all(i in historico for i in DESTINOS):
                    historico = []
                if ident not in historico:
                    historico.append(ident)
                config._gravar_bytes(self.historico, json.dumps(historico).encode("utf8"))
                self.encerrada = True
                return {"ok": True}
            raise ValueError("acao")


def montar(app, caminho=None):
    from fastapi import Request
    from fastapi.responses import FileResponse, JSONResponse
    import radai_consent
    import radai_languages

    sessao = Sessao(caminho)
    app.state.radai_convite_guia = sessao.convidar_reabertura
    sem_cache = {"Cache-Control": "no-store"}

    @app.get("/api/roteiro/interface")
    def interface(idioma: str = ""):
        lingua = radai_languages.canonico(idioma) or radai_languages.padrao_efetivo()
        dados = _catalogo().get(lingua, _catalogo()["en"])
        return JSONResponse(dict(dados, passos=PASSOS, sessao=sessao.id, idioma=lingua),
                            headers=sem_cache)

    @app.get("/api/roteiro/interface.js")
    def script():
        return FileResponse(DATA / "roteiro-suite.js", media_type="text/javascript",
                            headers={"Cache-Control": "no-cache"})

    @app.get("/api/roteiro/estilo.css")
    def estilo():
        return FileResponse(DATA / "roteiro-suite.css", media_type="text/css",
                            headers={"Cache-Control": "no-cache"})

    @app.post(ROTA_API)
    async def roteiro(request: Request):
        if (request.headers.get("sec-fetch-site") == "cross-site" or
                request.headers.get("origin", str(request.base_url).rstrip("/")).rstrip("/") != str(request.base_url).rstrip("/")):
            return JSONResponse({"ok": False}, status_code=403)
        if not radai_consent.aceito():
            return JSONResponse({"ok": False}, status_code=409)
        try:
            bruto = await request.body()
            if len(bruto) > 1024:
                raise ValueError("size")
            dados = json.loads(bruto)
            if not isinstance(dados, dict):
                raise ValueError("request")
            if dados.get("sessao") != sessao.id:
                return JSONResponse({"ok": False}, status_code=409)
            resposta = sessao.agir(dados.get("acao", "estado"), dados.get("aba"), dados.get("valor"))
            if resposta.get("tipo") == "dica":
                url = resposta["url"]
                for grupo in ("neuro", "lung"):
                    if url.startswith("/" + grupo + "/") and not (
                            getattr(app.state, grupo + "_plugin_mount", None) or {}).get("mounted"):
                        resposta["url"] = "/config#ps_" + grupo
            return JSONResponse(dict(resposta, versao=VERSAO_DO_GUIA), headers=sem_cache)
        except (ValueError, TypeError):
            return JSONResponse({"ok": False}, status_code=422)
        except OSError:
            return JSONResponse({"ok": False}, status_code=503)

    return app


PARA_A_CASCA = ('<link rel="stylesheet" href="/api/roteiro/estilo.css">'
                '<script id="radai-roteiro-js" src="/api/roteiro/interface.js" defer></script>')
