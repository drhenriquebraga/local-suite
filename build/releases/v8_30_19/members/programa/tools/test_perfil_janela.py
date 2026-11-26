"""Migração e desinstalação do perfil somente em pastas de teste."""
import os
import json
import contextlib
import io
import shutil
import socket
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).absolute().parents[1] / "app"))
import radai_perfil_janela as perfil
import radai_janela as janela
import radai_lancador as lancador
import radai_pulso as pulso


class Perfil(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="local_suite_perfil_")
        self.addCleanup(t.cleanup)
        self.raiz = Path(t.name)
        self.amb = {"LOCALAPPDATA": str(self.raiz / "local"), "TEMP": str(self.raiz / "temp")}
        self.novo, self.antigo = perfil.caminhos(self.amb)

    def criar_anterior(self):
        self.antigo.mkdir(parents=True)
        (self.antigo / "Local State").write_text("{}")
        preferencias = self.antigo / "Default" / "Local Storage" / "dados"
        preferencias.parent.mkdir(parents=True)
        preferencias.write_text("pt-BR;protocolo-do-usuario")

    def test_migrar_e_reabrir(self):
        self.criar_anterior()
        self.assertEqual(perfil.preparar(self.amb, lambda _: True), str(self.antigo))
        self.assertFalse(self.novo.exists())
        self.assertEqual(perfil.preparar(self.amb, lambda _: False), str(self.novo))
        self.assertFalse(self.antigo.exists())
        self.assertEqual((self.novo / "Default/Local Storage/dados").read_text(), "pt-BR;protocolo-do-usuario")
        with patch.dict(os.environ, self.amb), patch.dict(os.environ, {"RADAI_TEMP_DO_USUARIO": ""}):
            self.assertEqual([lancador.perfil_da_janela(), pulso.perfil_da_janela(),
                              janela.perfil_esperado_do_app()], [str(self.novo)] * 3)
            self.assertTrue(janela.e_do_perfil_do_app('msedge.exe "--user-data-dir=%s"' % self.novo))
            self.assertFalse(janela.e_do_perfil_do_app('msedge.exe "--user-data-dir=%s"' % (self.raiz / "janela")))
        self.assertEqual(perfil.preparar(self.amb, lambda _: self.fail("nova inspeção")), str(self.novo))

    def test_primeira_abertura_e_limite_da_remocao(self):
        self.assertEqual(perfil.perfil_da_janela(self.amb), str(self.novo))
        self.assertFalse(self.novo.exists())
        self.assertEqual(perfil.preparar(self.amb), str(self.novo))
        pessoal = self.raiz / "janela"
        pessoal.mkdir()
        self.assertEqual(perfil.perfis_conhecidos(self.amb), [str(self.novo)])
        with patch.object(perfil, "em_uso", return_value=True):
            self.assertFalse(perfil.remover(str(self.novo), self.amb))
        with patch.object(perfil, "em_uso", return_value=False):
            self.assertFalse(perfil.remover(str(pessoal), self.amb))
            self.assertTrue(perfil.remover(str(self.novo), self.amb))
        self.assertTrue(pessoal.exists())
        self.assertFalse(self.novo.exists())

    def test_destino_preexistente_nao_e_sobrescrito(self):
        self.criar_anterior()
        self.novo.mkdir(parents=True)
        (self.novo / "pessoal").write_text("preservar")
        self.assertEqual(perfil.preparar(self.amb), str(self.antigo))
        self.assertEqual(perfil.perfis_conhecidos(self.amb), [str(self.antigo)])
        self.assertFalse(perfil.remover(str(self.novo), self.amb))
        self.assertEqual((self.novo / "pessoal").read_text(), "preservar")

    def test_queda_durante_troca_preserva_fonte(self):
        self.criar_anterior()
        with patch.object(Path, "rename", side_effect=PermissionError):
            self.assertEqual(perfil.preparar(self.amb, lambda _:False), str(self.antigo))
        self.assertTrue((self.antigo / "Default/Local Storage/dados").exists())
        self.assertFalse(self.novo.exists())
        self.assertEqual(perfil.preparar(self.amb, lambda _:False), str(self.novo))

    def test_bundle_mesma_versao_corrige_qualquer_modulo_e_preserva_pesos(self):
        pacote = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(pacote/"build"))
        try:
            import atualizar_carga_offline as offline
        finally:
            sys.path.pop(0)
        extracao = self.raiz / "extracao"
        carga = extracao / "LOCAL_SUITE"
        carga.mkdir(parents=True)
        (extracao/"INSTALL.ps1").write_text("# fixture")
        shutil.copy2(pacote/"entrega.txt", extracao/"entrega.txt")
        (carga/"ts_weights").mkdir()
        peso = carga/"ts_weights/peso-qa"
        peso.write_bytes(b"peso independente")
        tempo_peso = peso.stat().st_mtime_ns
        with patch.object(offline.galeria_publica, "instalar"), patch.object(offline.cfg, "validar_codigo_instalado") as validar, contextlib.redirect_stdout(io.StringIO()):
            offline.atualizar(extracao)
            validar.assert_called_once()
            igual = carga/"radai_perfil_janela.py"
            antes = igual.stat().st_mtime_ns
            divergente = carga/"engine.py"
            anterior = divergente.read_bytes()
            mtime = divergente.stat().st_mtime_ns
            divergente.write_bytes(bytes([anterior[0] ^ 1]) + anterior[1:])
            os.utime(divergente, ns=(mtime, mtime))
            offline.atualizar(extracao)
            self.assertEqual(divergente.read_bytes(), anterior)
            self.assertEqual(igual.stat().st_mtime_ns, antes)
            self.assertEqual(validar.call_count, 2)
            validar.reset_mock()
            offline.atualizar(extracao)
            validar.assert_not_called()
        self.assertEqual(peso.read_bytes(), b"peso independente")
        self.assertEqual(peso.stat().st_mtime_ns, tempo_peso)

    @unittest.skipUnless(os.name == "nt", "preparador Windows")
    def test_selecao_do_desinstalador_no_setup(self):
        pacote = Path(__file__).resolve().parents[1]
        script = r"""
$ErrorActionPreference = 'Stop'
$ast = [Management.Automation.Language.Parser]::ParseFile($env:QA_PREP, [ref]$null, [ref]$null)
foreach ($d in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]}, $false)) {
    if ($d.Name -in @('ComoNumero','MaisNovaQue','EscolherDesinstalador')) { . ([ScriptBlock]::Create($d.Extent.Text)) }
}
$ps = Join-Path $env:QA_BASE 'instalado.ps1'
$novo = Join-Path $env:QA_BASE 'pacote.ps1'
[IO.File]::WriteAllText($ps, 'throw "não executar"')
[IO.File]::WriteAllText($novo, 'throw "não executar"')
if ((EscolherDesinstalador $ps $novo '8.30.18' '8.30.19') -ne $novo) {exit 1}
if ((EscolherDesinstalador $ps $novo '8.30.19' '8.30.19') -ne $novo) {exit 2}
if ((EscolherDesinstalador $ps $novo '8.30.20' '8.30.19') -ne $ps) {exit 3}
if ((EscolherDesinstalador $ps ($novo + '.ausente') '8.30.18' '8.30.19') -ne $ps) {exit 4}
"""
        subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script],
            env={**os.environ,"QA_PREP":str(pacote/"packager/prepare.ps1"),"QA_BASE":str(self.raiz)},
            check=True, capture_output=True, timeout=15)

    @unittest.skipUnless(os.name == "nt", "atualizador Windows")
    def test_atualizacao_de_codigo_preserva_preferencias_e_atualiza_desinstalador(self):
        pacote = Path(__file__).resolve().parents[1]
        estacao = self.raiz / "estacao" / "LOCAL_SUITE"
        (estacao / "maintenance").mkdir(parents=True)
        (estacao / "python").mkdir()
        shutil.copy2(sys.executable, estacao / "python/python.exe")
        (estacao / "radai_watcher.py").write_text("# versao anterior")
        (estacao / "entrega.txt").write_text("PROJETO=LOCAL_SUITE\nVERSAO=8.30.18\n")
        (estacao / "maintenance/UNINSTALL.ps1").write_text("# anterior")
        (estacao / "UNINSTALL.cmd").write_text("@rem entrada legada")
        req = json.loads((pacote / "_requisitos.json").read_bytes())
        req["versao"] = "8.30.18"
        (estacao / "_requisitos.json").write_text(json.dumps(req))
        anterior = os.getenv("LOCAL_SUITE_QA_SETUP_ANTERIOR")
        if anterior:
            with zipfile.ZipFile(anterior) as z:
                for nome, destino in (("app/radai_watcher.py", "radai_watcher.py"),
                                      ("installer/UNINSTALL.ps1", "maintenance/UNINSTALL.ps1"),
                                      ("_requisitos.json", "_requisitos.json"), ("entrega.txt", "entrega.txt")):
                    (estacao / destino).write_bytes(z.read("programa/" + nome))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            porta = sock.getsockname()[1]
        dados = {"radai_watcher.config": f"PORT={porta}\nPROCESSING_EFFORT=high\n",
                 "nomes_proprios.json": '{"QA":"MeuNome"}', "protocolos_proprios.json": '{"QA":"MeuProtocolo"}',
                 "protocolos_neuro.json": '{"QA":"Neuro"}', "Plugins/dados-qa.txt": "pesos preservados",
                 "_dados.txt": "destino registrado", "bundle-origem.json": '{"qa":"8.30.9"}'}
        for nome, conteudo in dados.items():
            (estacao / nome).parent.mkdir(exist_ok=True)
            (estacao / nome).write_bytes(conteudo.encode())
        self.criar_anterior()
        recibo = self.raiz / "termos-qa.json"
        amb = {**os.environ, **self.amb, "TMP": self.amb["TEMP"], "QA_RECIBO": str(recibo),
               "RADAI_TEMP_DO_USUARIO": self.amb["TEMP"], "QA_PACOTE": str(pacote),
               "RADAI_ATALHOS_NA_RAIZ": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        powershell = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"]
        gerar_recibo = r"""
$ErrorActionPreference = 'Stop'
. (Join-Path $env:QA_PACOTE 'packager/TERMOS_SUITE.ps1')
function Caminho-ReciboInstalador($Catalogo) { return $env:QA_RECIBO }
$c = Ler-CatalogoSuite (Join-Path $env:QA_PACOTE 'app/data/licencas_suite.json') full
Gravar-DecisaoSuite $c | Out-Null
"""
        subprocess.run(powershell + ["-Command", gerar_recibo], env=amb, check=True, capture_output=True, timeout=30)
        # A estação sintética está ociosa. A fixture não enumera nem encerra
        # processos da máquina hospedeira; os atalhos ficam na raiz descartável.
        atualizar = r"""
$ErrorActionPreference = 'Stop'
function Get-CimInstance { return }
function Stop-Process { throw 'A estação de QA não tem um processo ativo' }
& (Join-Path $env:QA_PACOTE 'packager/UPDATE.ps1') -Destino $env:QA_ESTACAO -Python $env:QA_PYTHON -SemPerguntar -SomenteLocal -ReciboDoPreparo $env:QA_RECIBO
exit $LASTEXITCODE
"""
        resultado = subprocess.run(powershell + ["-Command", atualizar],
            env={**amb, "QA_ESTACAO": str(estacao), "QA_PYTHON": sys.executable}, capture_output=True, timeout=165)
        self.assertEqual(resultado.returncode, 0, (resultado.stdout + resultado.stderr)[-2600:].decode(errors="replace"))
        self.assertEqual((estacao / "entrega.txt").read_bytes(), (pacote / "entrega.txt").read_bytes())
        for nome in ("UNINSTALL.cmd", "UNINSTALL.ps1"):
            fonte = (pacote / "installer" / nome).read_bytes()
            self.assertEqual((estacao / "maintenance" / nome).read_bytes(), fonte)
            self.assertEqual((estacao / nome).read_bytes(), fonte)
        for nome, conteudo in dados.items():
            self.assertEqual((estacao / nome).read_bytes(), conteudo.encode(), nome)
        for nome in ("radai_perfil_janela.py", "radai_job.py", "launchers/open_browser.cmd"):
            self.assertEqual((estacao / nome).read_bytes(), (pacote / "app" / nome).read_bytes())
        cli = subprocess.run([sys.executable, "-I", "-B", str(estacao/"radai_perfil_janela.py"), "--listar"],
                             env=amb, check=True, capture_output=True, timeout=10)
        self.assertEqual(json.loads(cli.stdout), [str(self.antigo)])
        self.assertFalse(self.novo.exists())  # A atualização só copia código.


if __name__ == "__main__":
    unittest.main()
