import base64
from contextlib import redirect_stdout
import csv
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from pastas_teste_coronarias import PROGRAMA
sys.path.insert(0, str(PROGRAMA / "app"))
import radai_rocards_offline as off


def digest(data):
    return hashlib.sha256(data).hexdigest()


class PacoteOffline(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.pkg = self.root / "plugin.zip"
        self.dados = {"models/LAD/model.pb": b"modelo", "wheels/qa.whl": b"wheel"}
        self.catalogo = {k:(len(v),digest(v),None) for k,v in self.dados.items()}

    def zip(self, itens):
        with zipfile.ZipFile(self.pkg, "w") as z:
            for k,v in itens:
                z.writestr(k, v)

    def extrair(self):
        with tempfile.TemporaryDirectory() as temp:
            off._extrair(self.pkg, Path(temp), self.catalogo)
            for k,v in self.dados.items():
                self.assertEqual((Path(temp) / k).read_bytes(),v)

    def test_pins_oficiais_e_zip_valido(self):
        oficial = off._catalogo()
        self.assertEqual(len(oficial),72)
        self.assertTrue(all(len(item[1]) == 64 and item[2].startswith("https://") for item in oficial.values()))
        self.zip(self.dados.items())
        self.extrair()

    def test_recusa_traversal_wheel_modificado_duplicado_e_link(self):
        chave, valor = next(iter(self.dados.items()))
        outro = list(self.dados.items())[1]
        link = zipfile.ZipInfo(chave)
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        for itens in ([("../modelo",valor),outro], [(chave,valor), ("wheels/qa.whl",b"xheel")],
                      [(chave,valor), (chave,valor)], [(link,valor),outro],
                      list(self.dados.items()) + [("runtime/x.dll",b"DLL")]):
            with self.subTest(nomes=[str(i[0]) for i in itens]):
                self.zip(itens)
                with self.assertRaises(ValueError):
                    self.extrair()

    def test_tamanho_declarado_e_fim_do_zip(self):
        self.zip(self.dados.items())
        dados = self.pkg.read_bytes()
        for corrompido in (dados[:-2], dados + b"A", dados[:-10] + b"\xff\xff" + dados[-8:]):
            self.pkg.write_bytes(corrompido)
            with self.assertRaises(ValueError):
                self.extrair()

    def test_restauro_conjunto_na_falha_de_promocao(self):
        destino, novo = self.root / "estacao", self.root / "novo"
        for pasta,conteudo in ((destino,b"antes"),(novo,b"depois")):
            for nome in off._PARTES:
                (pasta / nome).mkdir(parents=True)
                (pasta / nome / "dado").write_bytes(conteudo)
        original = Path.rename
        def renomear(origem, alvo):
            if origem == novo / "runtime":
                raise PermissionError("falha de publicação")
            return original(origem, alvo)
        with patch.object(Path,"rename",renomear), self.assertRaises(PermissionError):
            off._publicar(novo,destino)
        for nome in off._PARTES:
            self.assertEqual((destino/nome/"dado").read_bytes(),b"antes")
        self.assertFalse((destino/".transferencia-offline").exists())

    def test_reuso_exclui_extras_e_rejeita_codigo_instalado_modificado(self):
        wheels, fonte, alvo = self.root/"wheels", self.root/"runtime", self.root/"novo"
        wheels.mkdir()
        fonte.mkdir()
        nome = "teste.py"
        original = b"atividade = 1"
        registro = "teste-1.dist-info/RECORD"
        meta = "teste-1.dist-info/METADATA"
        arquivos = {nome:original, meta:b"Name: teste\nVersion: 1\n"}
        indice = io.StringIO()
        writer = csv.writer(indice)
        with zipfile.ZipFile(wheels/"teste.whl","w") as z:
            for rel, data in arquivos.items():
                p = fonte / rel
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(data)
                z.writestr(rel,data)
                sha = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
                writer.writerow([rel, "sha256="+sha, len(data)])
            writer.writerow([registro,"",""])
            z.writestr(registro,indice.getvalue().encode())
        (fonte/"extra.dll").write_bytes(b"externo")
        self.assertTrue(off._reaproveitar(fonte,wheels,alvo))
        self.assertFalse((alvo/"extra.dll").exists())
        (fonte/nome).write_bytes(b"atividade = 2")
        self.assertFalse(off._reaproveitar(fonte,wheels,self.root/"outra"))
        self.assertFalse((self.root/"outra").exists())

    def test_primeira_verificacao_apos_queda_restaura_geracao_anterior(self):
        from radai_rocards import _verificar
        destino = self.root / "estacao"
        backup = destino / ".transferencia-offline"
        backup.mkdir(parents=True)
        (backup/"pendente.json").write_text(json.dumps(["models","runtime"]), encoding="utf8")
        for nome in off._PARTES:
            (backup/nome).mkdir()
            (backup/nome/"origem").write_text("anterior")
        (destino/"models").mkdir()  # O processo parou antes de publicar o runtime.
        with self.assertRaises(FileNotFoundError):  # Fixture mínima, sem pesos reais.
            _verificar(destino)
        self.assertFalse(backup.exists())
        self.assertTrue(all((destino/nome/"origem").read_text()=="anterior" for nome in off._PARTES))

    def test_falha_no_runtime_nunca_publica(self):
        self.zip(self.dados.items())
        destino = self.root/"modelo"
        destino.mkdir()
        with patch.object(off.radai_models,"pasta_do_modelo",return_value=destino), patch.object(
                off,"_catalogo",return_value=self.catalogo), patch.object(off,"_runtime",side_effect=ValueError(
                    "runtime recusado")), patch.object(off,"_publicar") as publicar, self.assertRaises(ValueError):
            off.instalar(self.pkg)
        publicar.assert_not_called()
        self.assertFalse((destino/"models").exists())

    def test_carga_cuda_opcional_so_e_omitida_quando_a_cpu_passou(self):
        import radai_rocards_dependencies as deps
        (self.root / deps.RECIBO).write_text(digest(deps.LOCK.read_bytes()), encoding="ascii")
        driver = "tensorflow/stream_executor/cuda/cuda_driver.cc: failed call to cuInit"
        ok = subprocess.CompletedProcess([], 0, driver + "\nROCardS runtime OK (CPU)")
        erro = subprocess.CompletedProcess([], 1, driver + "\nFalha de importação")
        for resultado in (ok, erro):
            log = io.StringIO()
            with patch.object(deps.subprocess, "run", return_value=resultado), redirect_stdout(log):
                if resultado.returncode:
                    with self.assertRaises(subprocess.CalledProcessError):
                        deps.verificar(sys.executable, self.root)
                else:
                    deps.verificar(sys.executable,self.root)
            self.assertEqual(driver in log.getvalue(), bool(resultado.returncode))


if __name__ == "__main__":
    unittest.main(verbosity=2)
