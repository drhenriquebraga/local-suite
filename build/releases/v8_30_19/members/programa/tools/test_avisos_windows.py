"""Validação do change notify em NTFS local e falhas de provedor inteiramente simuladas."""
import ctypes
from ctypes import wintypes as W
import gc
import os
from pathlib import Path
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_avisos_windows as aviso


class Recebidos:
    def __init__(self, raiz):
        self.fila = queue.Queue()
        self.assinatura = aviso.inscrever(raiz, lambda estado, nomes:self.fila.put((estado, nomes)))

    def estado(self, esperado, prazo=5):
        estado, nomes = self.fila.get(timeout=prazo)
        if estado != esperado:
            raise AssertionError(f"esperado {esperado}, recebido {estado}")
        return nomes

    def buscar(self, condicao, prazo=5):
        vistos = []
        limite = time.monotonic() + prazo
        while not condicao(vistos):
            vistos += self.estado("mudou", max(.001, limite-time.monotonic()))
        return vistos

    def fechar(self):
        self.assinatura.fechar()
        assert not self.assinatura._thread.is_alive()


def alcas():
    k = ctypes.WinDLL("kernel32")
    k.GetProcessHandleCount.argtypes = W.HANDLE, ctypes.POINTER(W.DWORD)
    total = W.DWORD()
    if not k.GetProcessHandleCount(W.HANDLE(-1), ctypes.byref(total)):
        raise ctypes.WinError()
    return total.value


def registro(nome, acao=1, ultimo=False):
    texto = nome.encode("utf-16-le")
    n = (12 + len(texto) + 3) & ~3
    return struct.pack("<III", 0 if ultimo else n, acao, len(texto)) + texto + bytes(n-12-len(texto))


@unittest.skipUnless(os.name == "nt", "ReadDirectoryChangesW do Windows")
class Avisos(unittest.TestCase):
    def test_multiplas_raizes_subarvore_gravacao_rename_exclusao_e_rajada(self):
        with tempfile.TemporaryDirectory() as tmp:
            raizes = [Path(tmp)/x for x in ["a", "b"]]
            for raiz in raizes:
                (raiz/"serie").mkdir(parents=True)
            a,b = (Recebidos(r) for r in raizes)
            try:
                a.estado("pronto")
                b.estado("pronto")
                for i in range(100):
                    (raizes[0]/"serie"/f"{i:03}.dcm").write_bytes(b"teste")
                p=raizes[1]/"serie"/"inicial.dcm"
                p.write_bytes(b"T")
                b.buscar(lambda ev: (1,r"serie\inicial.dcm") in ev)
                with p.open("ab") as f:
                    f.write(b"nova gravacao")
                b.buscar(lambda ev: (3,r"serie\inicial.dcm") in ev)
                destino = p.with_name("final.dcm")
                p.rename(destino)
                eventos = b.buscar(lambda ev: (5,r"serie\final.dcm") in ev)
                self.assertIn((4,r"serie\inicial.dcm"), eventos)
                self.assertLess(eventos.index((4,r"serie\inicial.dcm")),eventos.index((5,r"serie\final.dcm")))
                destino.unlink()
                b.buscar(lambda ev: (2,r"serie\final.dcm") in ev)
                esperados = {f"serie\\{i:03}.dcm" for i in range(100)}
                a.buscar(lambda ev: esperados <= {nome for acao,nome in ev if acao==1})
                a.fechar()
                (raizes[0]/"ignorado.dcm").write_bytes(b"T")
                (raizes[1]/"serie"/"vivo.dcm").write_bytes(b"T")
                b.buscar(lambda ev: (1,r"serie\vivo.dcm") in ev)
                while not a.fila.empty():
                    self.assertNotIn((1,"ignorado.dcm"),a.fila.get_nowait()[1])
            finally:
                a.fechar()
                b.fechar()

    def test_repouso_sem_auxiliar_sem_enumeracao_sem_vazamento(self):
        real = aviso._iniciar_abridor
        with tempfile.TemporaryDirectory() as tmp:
            observados = []
            def spawn(p):
                filho=real(p)
                observados.append(filho)
                return filho
            # Após o primeiro ciclo, os imports e as DLLs do interpretador já aqueceram.
            primeiro = Recebidos(tmp)
            primeiro.estado("pronto")
            primeiro.fechar()
            del primeiro
            gc.collect()
            inicial = alcas()
            with mock.patch.object(aviso, "_iniciar_abridor", side_effect=spawn), mock.patch(
                    "os.scandir", side_effect=AssertionError("descida inesperada")):
                for _ in range(8):
                    recebidos = Recebidos(tmp)
                    recebidos.estado("pronto")
                    self.assertIsNotNone(observados[-1].poll())
                    recebidos.fechar()
                ativo = Recebidos(tmp)
                ativo.estado("pronto")
                tic = time.process_time()
                time.sleep(.5)
                cpu=time.process_time()-tic
                self.assertLess(cpu, .08)
                self.assertTrue(ativo.fila.empty())
                self.assertTrue(all(p.poll() is not None for p in observados))
                ativo.fechar()
            observados.clear()
            del recebidos, ativo
            gc.collect()
            self.assertLessEqual(alcas(), inicial+2)
            print(f"Repouso 0,5 s: {cpu:.4f} s de CPU no teste, nenhum auxiliar vivo. Handles {inicial} -> {alcas()}")

    def test_fecha_abertura_travada_antes_do_handle_e_respeita_outra_raiz(self):
        real = aviso._iniciar_abridor
        iniciou=threading.Event()
        filhos=[]
        def travar(raiz):
            if raiz != "arquivo-compartilhado-simulado":
                return real(raiz)
            proc=subprocess.Popen([sys.executable,"-c","import time; time.sleep(12)"],
                                  stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                  close_fds=True,creationflags=subprocess.CREATE_NO_WINDOW)
            filhos.append(proc)
            iniciou.set()
            return proc
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(aviso, "_iniciar_abridor", side_effect=travar):
            lento=Recebidos("arquivo-compartilhado-simulado")
            outra=Recebidos(tmp)
            try:
                self.assertTrue(iniciou.wait(3))
                outra.estado("pronto")
                tic=time.monotonic()
                lento.fechar()
                self.assertLess(time.monotonic()-tic, 1.5)
                self.assertTrue(lento.fila.empty())
                self.assertIsNotNone(filhos[0].poll())
                (Path(tmp)/"teste.dcm").touch()
                outra.buscar(lambda ev:(1,"teste.dcm") in ev)
            finally:
                outra.fechar()
                lento.fechar()
            with mock.patch.object(aviso,"_PRAZO_ABRIR",.12):
                tardia=Recebidos("arquivo-compartilhado-simulado")
                try:
                    tardia.estado("desconectado")
                finally:
                    tardia.fechar()
                self.assertIsNotNone(filhos[-1].poll())
                self.assertEqual(len(filhos),2)

    def test_overflow_real_do_ntfs_com_consumidor_suspenso(self):
        pronta = threading.Event()
        liberar = threading.Event()
        fila = queue.Queue()
        def receber(estado, nomes):
            fila.put(estado)
            if estado == "pronto":
                pronta.set()
                liberar.wait(8)
        with tempfile.TemporaryDirectory() as tmp:
            sub = aviso.inscrever(tmp,receber)
            try:
                self.assertTrue(pronta.wait(3))
                for i in range(900):
                    (Path(tmp)/(str(i)+"_"+"z"*100)).touch()
                liberar.set()
                limite = time.monotonic()+4
                while fila.get(timeout=max(.01,limite-time.monotonic())) != "overflow":
                    pass
            finally:
                liberar.set()
                self.assertTrue(sub.fechar())

    def test_overflow_queda_e_provedor_sem_suporte(self):
        real=aviso._kernel
        for esperado,codigo in [("overflow",0),("overflow",1022),("desconectado",64),("sem_suporte",50)]:
            with self.subTest(esperado=esperado,codigo=codigo), tempfile.TemporaryDirectory() as tmp:
                k=real()
                fachada=mock.Mock(wraps=k)
                if codigo==50:
                    def recusar(*args):
                        ctypes.set_last_error(50)
                        return False
                    fachada.ReadDirectoryChangesW.side_effect=recusar
                else:
                    def concluir(h,op,n,esperar):
                        ok=k.GetOverlappedResult(h,op,n,esperar)
                        if not ok or esperar:
                            return ok
                        if codigo:
                            ctypes.set_last_error(codigo)
                            return False
                        ctypes.cast(n,ctypes.POINTER(W.DWORD))[0]=0
                        return True
                    fachada.GetOverlappedResult.side_effect=concluir
                with mock.patch.object(aviso,"_kernel",return_value=fachada):
                    observado=Recebidos(tmp)
                    try:
                        if codigo!=50:
                            observado.estado("pronto")
                            (Path(tmp)/"teste").touch()
                        observado.estado(esperado)
                    finally:
                        observado.fechar()
                    self.assertTrue(observado.fila.empty())
                    self.assertEqual(fachada.CloseHandle.call_count,3)

    def test_limites_estrutura_de_eventos(self):
        n=aviso._MAX_EVENTOS
        lote=registro("a")*(n-1)+registro("b",ultimo=True)
        self.assertEqual(len(aviso._eventos(lote)), n)
        for invalido in [registro("a")+lote, b"", registro(r"..\fora",ultimo=True),
                         registro(r"C:\fora",ultimo=True), registro("x",acao=9,ultimo=True),
                         registro("a")[:-2], struct.pack("<III",4,1,2)+b"a\\0"]:
            with self.assertRaises(ValueError):
                aviso._eventos(invalido)


if __name__ == "__main__":
    unittest.main()
