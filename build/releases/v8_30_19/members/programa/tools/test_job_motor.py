"""Árvore sintética de inferência. Não abre nem encerra programas da estação."""
import ctypes
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

APP = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP))
import radai_job


def publicar(pasta, nome, valor):
    temp = pasta / (nome + ".parcial")
    temp.write_text(json.dumps(valor), encoding="utf-8")
    temp.replace(pasta / nome)


def subir(modo, pasta, flags=0):
    return subprocess.Popen([sys.executable, "-B", __file__, modo, str(pasta)],
                            creationflags=flags | getattr(subprocess, "CREATE_NO_WINDOW", 0),
                            close_fds=True, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def fantoma(modo, pasta):
    if modo in ("motor", "controle"):
        if modo == "motor":
            aviso = radai_job.armar_motor()
            if aviso:
                publicar(pasta, "erro", aviso)
                return
        worker = subir("worker", pasta)
        vigia = subir("vigia", pasta, radai_job.flags_de_saida())
        publicar(pasta, "motor", [worker.pid, vigia.pid])
    elif modo == "worker":
        neto = subir("neto", pasta)
        publicar(pasta, "worker", neto.pid)
    else:
        publicar(pasta, modo, os.getpid())
    time.sleep(30)


@unittest.skipUnless(os.name == "nt", "Job Objects do Windows")
class TestJob(unittest.TestCase):
    def observar(self, nome):
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.argtypes, k.OpenProcess.restype = [W.DWORD, W.BOOL, W.DWORD], W.HANDLE
        k.WaitForSingleObject.argtypes, k.WaitForSingleObject.restype = [W.HANDLE, W.DWORD], W.DWORD
        k.TerminateProcess.argtypes, k.TerminateProcess.restype = [W.HANDLE, W.UINT], W.BOOL
        k.CloseHandle.argtypes, k.CloseHandle.restype = [W.HANDLE], W.BOOL
        handles = []
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            motor = subir(nome, pasta)
            try:
                for _ in range(200):
                    if all((pasta / item).exists() for item in ["motor", "worker", "neto", "vigia"]):
                        break
                    if (pasta / "erro").exists():
                        self.fail((pasta / "erro").read_text(encoding="utf-8"))
                    if motor.poll() is not None:
                        self.fail("motor de teste saiu antes de produzir a árvore")
                    time.sleep(.025)
                worker, vigia = json.loads((pasta / "motor").read_text())
                neto = json.loads((pasta / "worker").read_text())
                self.assertEqual([neto, vigia], [json.loads((pasta / n).read_text()) for n in ["neto", "vigia"]])
                for pid in (worker, neto, vigia):
                    h = k.OpenProcess(0x00100001, False, pid)
                    self.assertTrue(h)
                    handles.append(h)
                self.assertTrue(all(k.WaitForSingleObject(h, 0) == 258 for h in handles))
                inicio = time.monotonic()
                motor.kill()
                motor.wait(timeout=2)
                for h in handles[:2]:
                    limite = max(0, int(1000 * (inicio + 2 - time.monotonic())))
                    self.assertEqual(k.WaitForSingleObject(h, limite if nome == "motor" else 100),
                                     0 if nome == "motor" else 258)
                self.assertEqual(k.WaitForSingleObject(handles[2], 0), 258,
                                 "o vigia independente precisa sobreviver ao motor")
                print("%s: filho e neto %s, supervisor vivo, %.3f s" %
                      (nome, "encerrados" if nome == "motor" else "vivos", time.monotonic() - inicio))
            finally:
                if motor.poll() is None:
                    motor.kill()
                motor.wait(timeout=3)
                for h in handles:
                    if k.WaitForSingleObject(h, 0) == 258:
                        k.TerminateProcess(h, 0)
                        k.WaitForSingleObject(h, 1500)
                    k.CloseHandle(h)

    def test_encerramento_anormal(self):
        self.observar("motor")

    def test_controle_sem_job(self):
        self.observar("controle")

    def test_termino_normal_poupa_apenas_instancia_do_supervisor(self):
        import radai_pulso
        supervisor = mock.Mock(pid=71)
        supervisor.poll.return_value = None
        lista = [(71, 19, "python.exe"), (72, 19, "python.exe")]
        with mock.patch.dict(radai_pulso._VIGIAS_POUPADOS, clear=True):
            radai_pulso.poupar_enquanto_vivo(supervisor)
            criacao = lambda pid: pid
            self.assertEqual(radai_pulso.filhos_do_motor(19, lista, criacao), [72])
            supervisor.poll.return_value = 0
            self.assertEqual(radai_pulso.filhos_do_motor(19, lista, criacao), [71, 72])

    def test_sucessor_nao_e_lancado_preso_ao_job_do_motor(self):
        import radai_lancador
        popen = mock.Mock(side_effect=PermissionError("simulado"))
        with mock.patch.object(radai_job, "_HANDLE", 100):
            with self.assertRaises(PermissionError):
                radai_lancador.subir_sucessor(8031, pid=71, popen=popen)
            popen.assert_called_once()
            self.assertTrue(popen.call_args.kwargs["creationflags"] & radai_job.flags_de_saida())
        popen.reset_mock()
        with mock.patch.object(radai_job, "_HANDLE", None):
            with self.assertRaises(PermissionError):
                radai_lancador.subir_sucessor(8031, pid=71, popen=popen)
            self.assertEqual(popen.call_count, 2)
            self.assertFalse(popen.call_args.kwargs["creationflags"] & 0x01000000)

    def test_job_negado_preserva_a_inicializacao(self):
        with mock.patch.multiple(radai_job, _HANDLE=None, _TENTADO=False, _AVISO=None), mock.patch.object(
                radai_job, "vincular", side_effect=PermissionError(5, "restrito")) as criar:
            self.assertIn("convencional", radai_job.armar_motor())
            self.assertEqual(radai_job.armar_motor(), radai_job._AVISO)
            self.assertEqual(radai_job.flags_de_saida(), 0)
            criar.assert_called_once_with(permitir_saida=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in ("motor", "controle", "worker", "neto", "vigia"):
        fantoma(sys.argv[1], Path(sys.argv[2]))
    else:
        unittest.main()
