"""Regressões de leitura interativa em arquivos sintéticos, sem estação clínica."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import radai_leitura_ativa as ativa
import radai_tabela_acervo as tabela
import radai_varrer as scans


class Buscas(unittest.TestCase):
    def test_parar_em_serie_parcial_nao_le_os_outros_98_cortes(self):
        import radai_dicom
        job = scans._novo("series", "x", 0, {})
        scans._iniciar_series(job)
        lidos = []
        def varrer(pasta, parar, ao_ler, nomes, ao_atualizar):
            for i in range(100):
                if parar(): break
                ao_ler()
                lidos.append(i)
                if i == 1:
                    ao_atualizar({"series": [{"uid": "1.2", "modalidade": "CT", "cortes": 2}]})
                    scans._interromper(job)
            return {"series": []}
        with patch.object(radai_dicom,"varrer_pasta",varrer), patch.object(scans,"_aceitar_series"):
            scans._ler_series(job,"x",[])
        self.assertEqual(len(lidos), 2)

    def test_limite_segura_vaga_ate_retornar_e_nao_inicia_fechamento(self):
        entrar = threading.Semaphore(0)
        liberar = threading.Event()
        finais = []
        def ler(job,pasta,nomes):
            entrar.release()
            liberar.wait(5)
        scans.registrar("teste-limite", ler, lambda j: [], fechar=lambda j: finais.append(1))
        with tempfile.TemporaryDirectory() as root:
            Path(root,"x").touch()
            ids = [scans.iniciar("teste-limite",root)["v"] for _ in range(scans.TETO_RODANDO)]
            try:
                for _ in ids: self.assertTrue(entrar.acquire(timeout=3))
                for v in ids: scans.parar(v)
                self.assertNotIn("v",scans.iniciar("teste-limite",root))
            finally:
                liberar.set()
            for v in ids:
                self.assertTrue(scans._VARREDURAS[v]["concluida"].wait(2))
                self.assertEqual(scans._VARREDURAS[v]["dados"],{})
            self.assertFalse(finais)

    def test_desconexao_sem_pagehide_interrompe_busca(self):
        with tempfile.TemporaryDirectory() as root:
            def ler(job,pasta,nomes):
                job["leitura"].evento.wait(4)
            Path(root,"x").touch()
            scans.registrar("teste-orfa",ler,lambda j:[])
            with patch.object(scans,"PRAZO_DA_INTERFACE_S",0.2):
                v = scans.iniciar("teste-orfa",root,interface=True)["v"]
                self.assertTrue(scans._VARREDURAS[v]["concluida"].wait(2))
                self.assertTrue(scans.estado(v)["parado"])

    @unittest.skipUnless(os.name=="nt","I/O síncrono do Windows")
    def test_cancelar_readfile_bloqueado_no_windows(self):
        inicio = threading.Event()
        terminou = threading.Event()
        leitura = ativa.Leitura()
        rd,wr = os.pipe()
        def ler():
            try:
                with leitura.participante():
                    inicio.set()
                    os.read(rd,1)
            except OSError:
                pass
            finally:
                terminou.set()
        fio=threading.Thread(target=ler)
        try:
            fio.start()
            self.assertTrue(inicio.wait(2))
            time.sleep(.1)
            leitura.parar()
            self.assertTrue(terminou.wait(2),"ReadFile ficou bloqueada após a janela cancelar")
        finally:
            os.close(wr)
            fio.join(2)
            os.close(rd)

    def test_5000_registros_zero_sondagens_e_um_indice_por_lote(self):
        import radai_archive
        import radai_thumbnail
        regs=[{"pasta":"Z:/teste/"+str(i),"uid":"1."+str(i)} for i in range(5000)]
        with patch.object(radai_archive,"ler_acervo",return_value=regs) as indice, patch.object(
              radai_archive,"conferir_acervo",side_effect=AssertionError("sondagem remota")):
            out=tabela.linhas(60)
            self.assertEqual(len(out["series"]),60)
            self.assertEqual(indice.call_count,1)
            with patch.object(tabela,"detalhe_da_serie",return_value=tabela._vazio()) as detalhe:
                bs=[x["bilhete"] for x in out["series"][:12]]
                tabela.detalhes(bs)
                self.assertEqual(indice.call_count,2)
                self.assertEqual(detalhe.call_count,12)

    def test_seis_pedidos_visiveis_esperam_quatro_vagas(self):
        class Aberto:
            async def is_disconnected(self):
                return False
        liberar = threading.Event()
        atual = maximo = 0
        trava = threading.Lock()

        def ler(i, parar):
            nonlocal atual, maximo
            with trava:
                atual += 1
                maximo = max(atual, maximo)
            try:
                liberar.wait(2)
                return i
            finally:
                with trava:
                    atual -= 1

        async def teste():
            grupo = asyncio.gather(*(ativa.executar(Aberto(), ler, i) for i in range(6)))
            await asyncio.sleep(.2)
            liberar.set()
            return await grupo

        self.assertEqual(asyncio.run(teste()), list(range(6)))
        self.assertEqual(maximo, 4)

    def test_cd_abandonado_sem_novas_consultas_termina(self):
        import radai_bridge_entrada as entrada
        import radai_dicom
        def ler(raiz, busca, **kwargs):
            busca["io"].evento.wait(3)
        with patch.object(entrada, "drives_de_cd", return_value=["D:"]), patch.object(
                radai_dicom, "buscar_series", ler), patch.object(scans, "PRAZO_DA_INTERFACE_S", .2):
            v = entrada.ler_cd("D:")
            self.assertTrue(entrada._LEITURAS_DE_CD[v]["concluida"].wait(2))
            self.assertTrue(entrada.estado_do_cd(v)["parado"])

    def test_laudo_interrompido_apos_2_de_100_cortes_nao_abre_os_outros(self):
        import radai_bridge
        vistos = []
        casos = {"arquivos": [{"caminho": i} for i in range(100)]}
        def ler(caminho):
            vistos.append(caminho)
            return ""
        with patch.object(radai_bridge, "_anotacao_queimada", ler):
            with self.assertRaises(InterruptedError):
                radai_bridge.texto_no_pixel(casos, parar=lambda: len(vistos) >= 2)
        self.assertEqual(vistos, [0, 1])

    def test_inclinacao_nao_abre_ultimo_corte_apos_cancelar(self):
        import pydicom
        import radai_dicom
        with patch.object(pydicom, "dcmread", return_value={}) as abrir:
            with self.assertRaises(InterruptedError):
                radai_dicom.inclinacao_de_gantry(
                    [{"caminho": i} for i in range(1, 5)], parar=lambda: abrir.call_count > 0)
        self.assertEqual(abrir.call_count, 1)

    def test_http_desconectado_libera_vaga_e_para_trabalho(self):
        fim = threading.Event()
        class Desconectado:
            async def is_disconnected(self): return True
        def lento(parar):
            try:
                while not parar(): time.sleep(.01)
            finally:
                fim.set()
        with self.assertRaises(ativa.LeituraCancelada):
            asyncio.run(ativa.executar(Desconectado(),lento))
        self.assertTrue(fim.wait(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
