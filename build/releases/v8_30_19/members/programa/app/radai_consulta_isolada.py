"""Consultas de disco da interface. Um filho descartável possui os handles da leitura."""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

_VAGAS = threading.BoundedSemaphore(3)
# Pelo menos uma das três vagas permanece disponível para navegação local.
_EXTERNAS = threading.BoundedSemaphore(2)
_MAPEAMENTO = threading.BoundedSemaphore(1)
PRAZO_PASTA = 5
_OPERACOES = {"conferir_pasta", "validar_pasta", "config_ler", "config_avaliar", "dedicado_prever", "pastas", "pastas_reserva", "lung_series", "historico_neuro", "mapear_unidade", "frota"}


def _limitar_descendentes():
    from radai_job import vincular
    return vincular()


def _consultar(operacao, dados):
    if operacao == "dedicado_prever":
        _limitar_descendentes()
        import radai_dedicado_windows as dedicado
        return dedicado.prever_com_resumo(porta=dados["porta"], pid_motor=dados["pid_motor"])
    if operacao == "config_avaliar":
        import radai_config
        _, disco = radai_config.ler_arquivo(dados["arquivo"])
        padroes = dados["padroes"]
        mudou = {k: v for k, v in dados["novos"].items()
                 if str(v).strip() != str(disco.get(k, padroes.get(k, ""))).strip()}
        if "ROOT" in mudou and not dados["confirmar_root"]:
            return {"ok": False, "precisa_confirmar": True,
                    "root_atual": disco.get("ROOT", padroes.get("ROOT", "")),
                    "root_novo": mudou["ROOT"], "validacao": radai_config.validar_pasta(mudou["ROOT"])}
        return {"mudou": mudou}
    if operacao in {"conferir_pasta", "validar_pasta", "config_ler"}:
        import radai_config
        if operacao == "config_ler":
            return radai_config.ler_arquivo(dados["caminho"])
        return radai_config.validar_pasta(dados["caminho"], testar_escrita=(operacao == "validar_pasta"))
    if operacao == "frota":
        from radai_overnight import consultar_frota
        return consultar_frota(dados)
    if operacao == "pastas":
        import radai_batch
        return radai_batch.consultar_explorador(dados)
    if operacao == "pastas_reserva":
        import radai_config
        return radai_config.listar_pastas(dados.get("caminho", ""), dados.get("arquivos", ""), dados.get("busca", ""))
    if operacao == "mapear_unidade":
        import radai_varrer
        return radai_varrer.mapear_unidade()
    if operacao == "historico_neuro":
        import radai_historico_leitura
        return radai_historico_leitura.listar(dados)
    if operacao == "lung_series":
        import radai_lung_screen
        pedido = dados["pedido"]
        if "bilhete" in pedido:
            import radai_thumbnail
            pasta, uid = dados["referencia"]
            pedido["bilhete"] = radai_thumbnail.bilhete(pasta, uid)
        return radai_lung_screen._series_da_escolha(pedido, dados["cfg"])
    raise ValueError("Consulta desconhecida.")


class ConsultaOcupada(ValueError):
    pass


def erro_da_consulta(exc):
    if isinstance(exc, TimeoutError):
        codigo = "tempo_esgotado"
    elif isinstance(exc, ConsultaOcupada):
        codigo = "ocupado"
    elif isinstance(exc, ConnectionAbortedError):
        codigo = "cancelado"
    else:
        codigo = "leitura"
    return {"codigo": codigo, "erro": str(exc)}


async def consultar_pastas(request, dados, operacao):
    try:
        return await ler(request, operacao, dados, prazo=PRAZO_PASTA)
    except (OSError, ValueError) as exc:
        return {"caminho": dados.get("caminho", ""), "pastas": [], "arquivos": [],
                "unidades": [], **erro_da_consulta(exc)}


async def conferir_pasta(request, caminho, escrita=False):
    try:
        return await ler(request, "validar_pasta" if escrita else "conferir_pasta",
                         {"caminho": caminho}, prazo=PRAZO_PASTA)
    except (OSError, ValueError) as exc:
        return {"caminho": caminho, "vazio": False, "existe": False, "leitura": False,
                "escrita": False, "aviso": "", "detalhe": str(exc), **erro_da_consulta(exc)}


def _externa(operacao, dados):
    if operacao == "config_avaliar":
        from radai_archive import _parece_rede
        return (_parece_rede(dados["arquivo"]) or
                bool(dados["novos"].get("ROOT") and _parece_rede(dados["novos"]["ROOT"])))
    if operacao in {"pastas", "pastas_reserva", "conferir_pasta", "validar_pasta", "config_ler"}:
        caminho = str(dados.get("caminho") or "").strip().strip('"')
        if not caminho:
            return False
        from radai_archive import _parece_rede
        return _parece_rede(caminho)
    return True


async def ler(request, operacao, dados, prazo=120):
    limite = time.monotonic() + prazo
    if operacao not in _OPERACOES:
        raise ValueError("Consulta desconhecida.")
    entrada = json.dumps([operacao, dados], ensure_ascii=False).encode("utf-8")
    if len(entrada) > 2 * 1024 * 1024:
        raise ValueError("Seleção muito grande.")
    reservas = []
    processo = None
    conversa = None
    try:
        vagas = []
        if operacao == "mapear_unidade":
            vagas.append(_MAPEAMENTO)
        if _externa(operacao, dados):
            vagas.append(_EXTERNAS)
        vagas.append(_VAGAS)
        for vaga in vagas:
            if not vaga.acquire(blocking=False):
                raise ConsultaOcupada("Há outras leituras em andamento. Tente novamente.")
            reservas.append(vaga)
        from radai_leitura_ativa import desconexao_do_pedido
        async with desconexao_do_pedido(request) as desconexao:
            await asyncio.sleep(0)
            if desconexao.done():
                raise ConnectionAbortedError("Leitura cancelada.")
            ambiente = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
            processo = subprocess.Popen(
                [sys.executable, "-B", str(Path(__file__).resolve())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=ambiente)
            loop = asyncio.get_running_loop()
            conversa = loop.run_in_executor(None, processo.communicate, entrada)
            await asyncio.wait([conversa, desconexao], timeout=max(0, limite - time.monotonic()),
                               return_when=asyncio.FIRST_COMPLETED)
            if not conversa.done():
                if desconexao.done():
                    raise ConnectionAbortedError("Leitura cancelada.")
                raise TimeoutError("O tempo de leitura da pasta se esgotou.")
        saida, _ = conversa.result()
        if processo.returncode:
            raise ValueError("O processo de leitura foi interrompido.")
        resposta = json.loads(saida)
        if "erro" in resposta:
            raise ValueError(resposta["erro"])
        return resposta["dados"]
    finally:
        try:
            if processo is not None:
                if processo.poll() is None:
                    processo.kill()
                if conversa is not None:
                    await asyncio.shield(conversa)
                else:
                    processo.communicate()
        finally:
            for vaga in reversed(reservas):
                vaga.release()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    operacao, dados = json.load(sys.stdin.buffer)
    try:
        with contextlib.redirect_stdout(sys.stderr):
            resposta = {"dados": _consultar(operacao, dados)}
    except Exception as exc:
        resposta = {"erro": str(exc)[:500]}
    sys.stdout.buffer.write(json.dumps(resposta, ensure_ascii=False).encode("utf-8"))
