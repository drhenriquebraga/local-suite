"""Contratos do catálogo de ensino e pesquisa no início da suíte."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "programa" / "app"
sys.path.insert(0, str(APP))
from fastapi import FastAPI
from fastapi.testclient import TestClient
import radai_consent as consentimento
import radai_termos_catalogo as catalogo


class AceitePesquisa(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        env = patch.dict(os.environ, {"RADAI_CALIB_DIR":self.pasta.name})
        env.start()
        self.addCleanup(env.stop)
        app = FastAPI()
        consentimento.montar(app)
        app.post("/api/plugins/neuro-rt/install")(lambda: {"rede":"teste"})
        app.post("/api/lote/enfileirar")(lambda: {"ok":True})
        consentimento.montar_portao(app)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def corpo(self, ferramentas=()):
        return {"itens":[k for k,_,_ in consentimento.PONTOS], "ensino_pesquisa":True,
                "catalogo_sha256":catalogo.catalogo()[0],"ferramentas_opcionais":list(ferramentas)}

    def test_leitura_antes_e_depois(self):
        pagina = self.client.get("/aceite").text
        livro = self.client.get("/licencas-ferramentas").text
        for texto in (pagina,livro):
            self.assertIn("ROCardS",texto)
            self.assertIn("href=\"https://",texto)
            self.assertEqual(texto.count('class="lic-item"'),len(catalogo.catalogo()[1]))
            self.assertNotIn("@CATALOGO",texto)
        self.assertFalse(consentimento.aceito())
        self.assertEqual(self.client.post("/api/lote/enfileirar").status_code,409)
        self.assertEqual(self.client.post("/api/aceite",json=self.corpo()).json()["catalogo_sha256"],
                         hashlib.sha256(catalogo.ARQUIVO.read_bytes()).hexdigest())
        self.assertEqual(self.client.post("/api/lote/enfileirar").status_code,200)

    def test_aceite_local_so_com_ato_explicito_e_catalogo_atual(self):
        for mudanca in ({"ensino_pesquisa":False},{"itens":[]},{"catalogo_sha256":"antigo"},
                       {"ferramentas_opcionais":["ferramenta-inexistente"]}):
            with self.subTest(mudanca=mudanca):
                d=dict(self.corpo(),**mudanca)
                self.assertIn("erro",self.client.post("/api/aceite",json=d).json())
                self.assertFalse(consentimento.aceito())
        legado=consentimento._caminho()
        legado.parent.mkdir(parents=True,exist_ok=True)
        legado.write_text(json.dumps({"versao":"2.8","maquina":consentimento._maquina()}))
        self.assertFalse(consentimento.aceito())

    def test_opcional_exige_selecao_individual(self):
        self.assertIn("neuro-rt",catalogo.grupos_opcionais())
        self.client.post("/api/aceite",json=self.corpo())
        self.assertEqual(self.client.post("/api/plugins/neuro-rt/install").status_code,409)
        self.client.post("/api/aceite",json=self.corpo(["neuro-rt"]))
        self.assertEqual(self.client.post("/api/plugins/neuro-rt/install").status_code,200)
        self.assertFalse(consentimento.ferramenta_autorizada("lung-rt"))


if __name__=="__main__":
    unittest.main(verbosity=2)
