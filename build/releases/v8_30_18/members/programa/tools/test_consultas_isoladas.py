"""Exercita o ciclo de vida dos leitores da interface em processos reais, sem dados de pacientes."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_consulta_isolada as consulta


class Pedido:
    cancelado = False

    async def is_disconnected(self):
        return self.cancelado


class Consultas(unittest.IsolatedAsyncioTestCase):
    async def test_listagem_local_no_filho(self):
        with tempfile.TemporaryDirectory() as pasta:
            (Path(pasta) / "Cortes").mkdir()
            resultado = await consulta.ler(Pedido(), "pastas_reserva", {"caminho": pasta})
            self.assertFalse(resultado["erro"])
            self.assertIn("Cortes", str(resultado["pastas"]))

    async def test_tc_do_lung_no_processo_descartavel(self):
        from datetime import datetime
        import make_test_series
        with tempfile.TemporaryDirectory() as pasta:
            make_test_series.escreve_serie(pasta, 'FANTOMA', datetime(2026, 11, 26), 12)
            origem, series = await consulta.ler(Pedido(), "lung_series", {
                "pedido": {"pasta": pasta}, "cfg": {"min_cortes": 5}})
            self.assertEqual(Path(origem), Path(pasta))
            self.assertEqual(len(series), 1)
            self.assertEqual(series[0]["pid"], "FANTOMA")
            self.assertTrue(series[0]["axial"])

    async def test_cancelamento_e_limite_sem_processos_residuais(self):
        filhos = []
        iniciar = subprocess.Popen

        def ocupar(args, **kwargs):
            filho = iniciar([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
            filhos.append(filho)
            return filho

        pedidos = [Pedido() for _ in range(3)]
        with patch.object(consulta.subprocess, "Popen", side_effect=ocupar):
            tarefas = [asyncio.create_task(consulta.ler(p, "pastas", {})) for p in pedidos]
            try:
                for tentativa in range(100):
                    if len(filhos) == 3:
                        break
                    await asyncio.sleep(.02)
                self.assertEqual(len(filhos), 3)
                with self.assertRaisesRegex(ValueError, "outras leituras"):
                    await consulta.ler(Pedido(), "pastas", {})
                pedidos[0].cancelado = True
                with self.assertRaises(ConnectionAbortedError):
                    await asyncio.wait_for(tarefas[0], 3)
                self.assertIsNotNone(filhos[0].poll())
                self.assertTrue(all(p.poll() is None for p in filhos[1:]))
            finally:
                for pedido in pedidos:
                    pedido.cancelado = True
                await asyncio.gather(*tarefas, return_exceptions=True)
            self.assertTrue(all(p.poll() is not None for p in filhos))
            with self.assertRaises(TimeoutError):
                await consulta.ler(Pedido(), "pastas", {}, prazo=.05)
            self.assertIsNotNone(filhos[-1].poll())

    async def test_cancelado_antes_do_primeiro_acesso(self):
        pedido = Pedido()
        pedido.cancelado = True
        with patch.object(consulta.subprocess, "Popen") as inicio:
            with self.assertRaises(ConnectionAbortedError):
                await consulta.ler(pedido, "pastas", {})
            inicio.assert_not_called()


if __name__ == "__main__":
    unittest.main()
