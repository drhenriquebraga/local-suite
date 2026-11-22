"""Opt-in de pesquisa do ROCardS, vinculado à instalação e à estação."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import threading
from datetime import datetime, timezone

import radai_archive

VERSAO = "1.0"
REVISAO = "40b80a6d6f76b1e72877a139b711bb0a345519d7"
FONTE = "https://github.com/AIM-Harvard/ROCardS"
TERMOS_URL = FONTE + "/blob/" + REVISAO + "/LICENSE"
PESOS_URL = FONTE + "/blob/" + REVISAO + "/ROCardS/data/models/LICENSE_WEIGHTS"
TEXTO = (
    "I authorize this installation to obtain and verify the ROCardS research resources "
    "and their runtime dependencies, using the official online sources or the offline "
    "research package I selected. I accept the authors' license "
    "for the code and model weights (CC BY-NC 4.0) and their research-only terms. "
    "By activating the Coronaries plugin I designate this Local Suite station exclusively "
    "for noncommercial research and teaching in that context. Commercial and clinical use "
    "of this station are prohibited while this plugin is activated. "
    "This workflow estimates the left anterior descending artery. "
    "Code: " + TERMOS_URL + " Weights: " + PESOS_URL
)
IMPRESSAO = hashlib.sha256(TEXTO.encode("utf-8")).hexdigest()
REGISTRO = Path(__file__).resolve().parent / "registro" / "aceites"
_mutex = threading.Lock()
_preparando = False
_erro = ""
# O transporte tem 646.539.220 bytes nesta revisão. O importador também
# confere o tamanho exato de cada membro antes da instalação.
MAX_PACOTE = 650 * 1024 ** 2


def _estacao():
    identificador = socket.gethostname().casefold()
    if os.name == "nt":
        import winreg
        # O nome da estação pode mudar. A chave acompanha a instalação do Windows.
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as chave:
            identificador = winreg.QueryValueEx(chave, "MachineGuid")[0].strip().casefold()
    if not identificador:
        raise ValueError("Identificação da estação indisponível.")
    return hashlib.sha256(("Local Suite - ROCardS - " + identificador).encode()).hexdigest()


def _caminho():
    return REGISTRO / _estacao() / ("coronarias-" + VERSAO + "-" + IMPRESSAO + ".json")


def ativado():
    try:
        caminho = _caminho()
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return (isinstance(dados, dict) and dados.get("schema") == "local-suite/rocards/1"
                and dados.get("aceito") is True and dados.get("estacao") == caminho.parent.name
                and dados.get("termos_versao") == VERSAO and dados.get("termos_sha256") == IMPRESSAO
                and dados.get("termos_texto") == TEXTO and dados.get("revisao_modelo") == REVISAO
                and dados.get("regime") == "pesquisa-nao-comercial"
                and bool(dados.get("aceito_utc")) and bool(dados.get("ativado_utc")))
    except (OSError, ValueError, TypeError):
        return False


def _disponivel():
    try:
        from radai_rocards import disponivel
    except ImportError:
        return False
    return disponivel()[0]


def _preparar_recursos():
    from radai_rocards_dependencies import preparar
    preparar()


def _importar_recursos(pacote):
    from radai_rocards_offline import instalar
    instalar(pacote)


def _hora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _gravar(caminho, aceito_em, origem):
    dados = dict(schema="local-suite/rocards/1", aceito=True, estacao=caminho.parent.name,
                 aceito_utc=aceito_em, ativado_utc=_hora(), termos_versao=VERSAO,
                 termos_sha256=IMPRESSAO, termos_texto=TEXTO, revisao_modelo=REVISAO,
                 regime="pesquisa-nao-comercial", origem=origem, termos_url=TERMOS_URL, pesos_url=PESOS_URL)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=caminho.parent,
                                         prefix=".coronarias-", delete=False) as arquivo:
            temp = Path(arquivo.name)
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temp, caminho)
    finally:
        if temp:
            temp.unlink(missing_ok=True)


def _executar(aceito_em, pacote=None):
    global _preparando, _erro
    erro = ""
    try:
        caminho = _caminho()
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with radai_archive._travar_indice(caminho):
            if pacote is None:
                _preparar_recursos()
            else:
                _importar_recursos(pacote)
            if not _disponivel():
                raise RuntimeError("Recursos do ROCardS indisponíveis após a verificação.")
            if not ativado():
                _gravar(caminho, aceito_em, "pacote-offline" if pacote is not None else "origem-online")
    except Exception as exc:
        erro = str(exc).strip()[:500] or type(exc).__name__
    finally:
        try:
            if pacote is not None:
                pacote.unlink(missing_ok=True)
        finally:
            with _mutex:
                _erro, _preparando = erro, False


def estado():
    with _mutex:
        preparando, erro = _preparando, _erro
    return dict(ativado=ativado(), disponivel=_disponivel(), preparando=preparando, erro=erro,
                termos_versao=VERSAO, termos_sha256=IMPRESSAO, termos_texto=TEXTO,
                termos_url=TERMOS_URL, pesos_url=PESOS_URL)


def _conferir_aceite(dados):
    if not isinstance(dados, dict) or dados.get("aceito") is not True:
        raise ValueError("Aceite explícito obrigatório.")
    if dados.get("termos_versao") != VERSAO or dados.get("termos_sha256") != IMPRESSAO:
        raise ValueError("Os termos mudaram. Reabra o formulário.")


def _iniciar(aceito_em, pacote=None):
    threading.Thread(target=_executar, args=(aceito_em, pacote),
                     name="local-suite-rocards", daemon=True).start()


def solicitar(dados):
    global _preparando, _erro
    _conferir_aceite(dados)
    with _mutex:
        if not _preparando and not (ativado() and _disponivel()):
            _preparando, _erro = True, ""
            try:
                _iniciar(_hora())
            except RuntimeError:
                _preparando = False
                raise
    return dict(ok=True, **estado())


def _local(request):
    try:
        return (request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
                and request.url.hostname in ("localhost", "127.0.0.1", "::1")
                and request.headers.get("origin") == "%s://%s" % (request.url.scheme, request.url.netloc))
    except ValueError:
        return False


def montar_rotas(app):
    from fastapi import Request
    from starlette.responses import JSONResponse

    def resposta(dados, status=200):
        return JSONResponse(dados, status_code=status, headers={"Cache-Control": "no-store"})

    @app.get("/api/plugins/coronarias")
    def consultar():
        return resposta(estado())

    @app.post("/api/plugins/coronarias/ativar")
    async def ativar(request: Request):
        from starlette.concurrency import run_in_threadpool
        if not _local(request):
            return resposta({"erro": "Abra as configurações nesta estação."}, 403)
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            return resposta({"erro": "Formato inválido."}, 415)
        corpo = bytearray()
        async for bloco in request.stream():
            if len(corpo) + len(bloco) > 4096:
                return resposta({"erro": "Formulário inválido."}, 413)
            corpo.extend(bloco)
        try:
            resultado = await run_in_threadpool(solicitar, json.loads(corpo))
        except ValueError as exc:
            return resposta({"erro": str(exc)}, 400)
        return resposta(resultado, 202 if resultado["preparando"] else 200)

    @app.post("/api/plugins/coronarias/importar")
    async def importar(request: Request):
        from starlette.concurrency import run_in_threadpool
        from starlette.requests import ClientDisconnect
        global _preparando, _erro
        if not _local(request):
            return resposta({"erro": "Abra as configurações nesta estação."}, 403)
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/zip":
            return resposta({"erro": "Selecione o ZIP do plugin Coronárias."}, 415)
        try:
            _conferir_aceite(dict(aceito=request.headers.get("x-radai-aceito") == "1",
                                  termos_versao=request.headers.get("x-radai-termos-versao"),
                                  termos_sha256=request.headers.get("x-radai-termos-sha256")))
            tamanho = int(request.headers.get("content-length", 0))
        except ValueError as exc:
            return resposta({"erro": str(exc)}, 400)
        if not 0 <= tamanho <= MAX_PACOTE:
            return resposta({"erro": "Tamanho de pacote inválido."}, 413)
        with _mutex:
            if _preparando:
                return resposta({"erro": "Há um preparo em andamento."}, 409)
            _preparando, _erro = True, ""
        pacote = None
        iniciado = False
        try:
            if tamanho and tamanho > shutil.disk_usage(tempfile.gettempdir()).free:
                return resposta({"erro": "Espaço insuficiente para receber o pacote."}, 507)
            total = 0
            aceito_em = _hora()
            with tempfile.NamedTemporaryFile(prefix="local-suite-rocards-", suffix=".zip", delete=False) as arquivo:
                pacote = Path(arquivo.name)
                async for bloco in request.stream():
                    total += len(bloco)
                    if total > MAX_PACOTE:
                        return resposta({"erro": "Pacote excede o tamanho permitido."}, 413)
                    if bloco:
                        await run_in_threadpool(arquivo.write, bloco)
            if not total or (tamanho and tamanho != total):
                return resposta({"erro": "A transferência do pacote ficou incompleta."}, 400)
            _iniciar(aceito_em, pacote)
            iniciado = True
            resultado = await run_in_threadpool(estado)
            return resposta(dict(ok=True, **resultado), 202 if resultado["preparando"] else 200)
        except ClientDisconnect:
            return resposta({"erro": "Transferência interrompida."}, 400)
        except OSError:
            return resposta({"erro": "Falha ao receber o arquivo temporário na estação."}, 507)
        finally:
            if not iniciado:
                try:
                    if pacote is not None:
                        pacote.unlink(missing_ok=True)
                finally:
                    with _mutex:
                        _preparando = False
