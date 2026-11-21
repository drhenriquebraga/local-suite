"""Contratos da atualização de pesos e compatibilidade do pacote 8.30."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
import io
from unittest.mock import patch


RAIZ = Path(os.environ.get("SUITE_EM_TESTE", Path(__file__).resolve().parents[1] / "programa"))
sys.path.insert(0, str(RAIZ / "build"))
sys.path.insert(0, str(RAIZ / "app"))
import configurar_ambiente as preparo
import radai_models
import requisitos


class ContratoBundle830(unittest.TestCase):
    def test_instalacao_limpa_copia_ajuda_e_fontes(self):
        ajuda = RAIZ / "app/data/ajuda-tasks"
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            alvo = Path(tmp)
            ajuda_antiga = alvo / "data/ajuda-tasks"
            ajuda_antiga.mkdir(parents=True)
            (ajuda_antiga / "costelas-modelos.png").write_bytes(b"QA")
            preparo.etapa_app({"bundle": alvo, "versao": "8.30", "projeto": "LOCAL_SUITE",
                               "produto": "RADIOTERAPIA_AI_LOCAL_SUITE", "profile": "full"})
            self.assertFalse((ajuda_antiga / "costelas-modelos.png").exists())
            for origem in (p for p in ajuda.rglob("*") if p.is_file()):
                destino = alvo / "data/ajuda-tasks" / origem.relative_to(ajuda)
                self.assertEqual(destino.read_bytes(), origem.read_bytes())
            cat = alvo / "data/licencas_suite.json"
            self.assertEqual(cat.read_bytes(), (RAIZ / "app/data/licencas_suite.json").read_bytes())

    def test_carimbo_e_fingerprint(self):
        carimbo = (RAIZ / "entrega.txt").read_text(encoding="utf-8-sig").splitlines()
        self.assertIn("VERSAO=8.30", carimbo)
        self.assertIn("BUNDLE_MINIMO=8.30", carimbo)
        gravado = json.loads((RAIZ / "_requisitos.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(gravado["impressao"], requisitos.calcular(str(RAIZ))["impressao"])
        self.assertNotEqual(gravado["impressao"], "3f73d83811b252605f060d52435f6381802f8de7353641c34a86a4eb853a945a")

    def test_sete_redes_e_licenca(self):
        m = radai_models.MODELOS["rocards_lad"]
        pesos = dict(m["arquivos"])
        centros = {nome.split("/")[1] for nome in pesos if nome.endswith("/saved_model.pb")}
        self.assertEqual(centros, {"HEART", "LV", "RV", "LA", "RA", "LV_RV_LA_RA", "LAD"})
        self.assertEqual(len(pesos), 29)
        self.assertIn("models/LICENSE_WEIGHTS", pesos)
        self.assertEqual(sum(pesos.values()), 122188235)
        self.assertEqual(set(pesos), set(m["sha256"]))
        self.assertTrue(all(m["revisao"] in radai_models.url_do_arquivo(m, p) for p in pesos))

    def test_perfis(self):
        self.assertTrue({"rocards_lad", "jhu_rectum", "moose_ribs"} <= set(preparo.modelos_do_perfil({})))
        self.assertEqual(set(preparo.modelos_do_perfil({"profile":"lung-rt"})), {"rocards_lad","moose_ribs"})

    def test_zip_exclui_opcionais_presentes_no_cache(self):
        import itertools
        opcionais = {"cads_open", "moose", "nv_segment_ct"}
        obrigatorios = {"rocards", "jhu_rectum", "moose_ribs"}
        with tempfile.TemporaryDirectory() as pasta:
            tmp = Path(pasta)
            carga = tmp / "LOCAL_SUITE"
            for nome in opcionais | obrigatorios:
                arq = carga / "modelos" / nome / "peso-de-teste.bin"
                arq.parent.mkdir(parents=True)
                arq.write_bytes(b"QA")
            for n in range(len(opcionais) + 1):
                for selecao in itertools.combinations(sorted(opcionais), n):
                    omitidos = opcionais.difference(selecao)
                    pacote = tmp / "QA-NAO-INSTALAVEL.zip"
                    with zipfile.ZipFile(pacote, "w") as saida:
                        for arquivo in preparo._arquivos_do_bundle(carga, omitidos):
                            saida.write(arquivo, arquivo.relative_to(tmp))
                    with zipfile.ZipFile(pacote) as z:
                        presentes = {k.split("/")[2] for k in z.namelist()}
                    self.assertEqual(presentes, obrigatorios | set(selecao))

    def test_incompleto_e_termos(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, RADAI_MODELOS_DIR=tmp):
            estado = radai_models.estado_do_modelo("rocards_lad")
            self.assertFalse(estado["instalado"])
            self.assertEqual(Path(estado["pasta"]), Path(tmp) / "rocards")
            self.assertIn("runtime/tensorflow/python/_pywrap_tensorflow_internal.pyd", estado["faltando"])
            recibo = Path(tmp) / "LICENCAS_ACEITAS.txt"
            recibo.write_text("[ACEITA] Python\n[DISPENSADO] ROCardS\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                preparo._exigir_aceite_completo(recibo)
            recibo.write_text("[ACEITA] ROCardS — artéria descendente anterior\n", encoding="utf-8")
            preparo._exigir_aceite_completo(recibo)


if __name__ == "__main__":
    unittest.main()
