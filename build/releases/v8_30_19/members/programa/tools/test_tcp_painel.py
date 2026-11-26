"""Somente servidor local e cliente sintético; nenhum tráfego externo."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_cleaner


@unittest.skipUnless(os.name == "nt", "tabela TCP local do Windows")
class Proprietario(unittest.TestCase):
    def exercitar(self, familia, endereco):
        with socket.socket(familia, socket.SOCK_STREAM) as srv:
            srv.settimeout(5)
            srv.bind((endereco,0))
            srv.listen()
            porta = srv.getsockname()[1]
            py = ("import socket,sys; "
                  "s=socket.socket(int(sys.argv[1]),socket.SOCK_STREAM); "
                  "s.settimeout(6); s.connect((sys.argv[2],int(sys.argv[3]))); s.recv(1)")
            with subprocess.Popen([sys.executable, "-B", "-c", py, str(int(familia)), endereco, str(porta)],
                                  close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW) as filho:
                with srv.accept()[0] as cliente:
                    self.assertIn(filho.pid, radai_cleaner.navegadores_conectados(porta))
                    self.assertNotIn(os.getpid(), radai_cleaner.navegadores_conectados(porta))
                    cliente.sendall(b"!")
                filho.wait(timeout=2)

    def test_ipv4(self):
        self.exercitar(socket.AF_INET, "127.0.0.1")

    def test_ipv6(self):
        self.exercitar(socket.AF_INET6, "::1")


if __name__ == "__main__":
    unittest.main()
