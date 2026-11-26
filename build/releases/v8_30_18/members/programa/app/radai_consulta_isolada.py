"""Consultas de disco da interface. Um filho descartável possui os handles da leitura."""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

_VAGAS = threading.BoundedSemaphore(3)
_OPERACOES = {"pastas", "pastas_reserva", "lung_series", "historico_neuro", "mapear_unidade", "frota"}


def _consultar(operacao, dados):
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


async def ler(request, operacao, dados, prazo=120):
    if operacao not in _OPERACOES:
        raise ValueError("Consulta desconhecida.")
    entrada = json.dumps([operacao, dados], ensure_ascii=False).encode("utf-8")
    if len(entrada) > 2 * 1024 * 1024:
        raise ValueError("Seleção muito grande.")
    if not _VAGAS.acquire(blocking=False):
        raise ValueError("Há outras leituras em andamento. Tente novamente.")
    processo = None
    conversa = None
    try:
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
            await asyncio.wait([conversa, desconexao], timeout=prazo, return_when=asyncio.FIRST_COMPLETED)
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
            _VAGAS.release()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    operacao, dados = json.load(sys.stdin.buffer)
    try:
        with contextlib.redirect_stdout(sys.stderr):
            resposta = {"dados": _consultar(operacao, dados)}
    except Exception as exc:
        resposta = {"erro": str(exc)[:500]}
    sys.stdout.buffer.write(json.dumps(resposta, ensure_ascii=False).encode("utf-8"))
