# -*- coding: utf-8 -*-
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / name) for name in ("app", "build", "tools")]

import configurar_ambiente as preparo
import radai_consent
import radai_models as modelos
import radai_moose


class PesosDoStudy(unittest.TestCase):
    def test_motores_e_perfis_sao_independentes(self):
        self.assertEqual(set(radai_moose.MODELOS), {"cardiac", "body_composition"})
        self.assertEqual(radai_moose.RIBS["pasta"], "Dataset444_Ribs")
        self.assertEqual(preparo.modelos_do_perfil({"profile": "lung-rt"}), ("moose_ribs", "rocards_lad"))
        full = set(preparo.modelos_do_perfil({"profile": "full"}))
        self.assertTrue({"jhu_rectum", "moose_ribs", "rocards_lad"}.issubset(full))
        jhu = modelos.MODELOS["jhu_rectum"]
        nomes = {nome for nome, _ in jhu["arquivos"]}
        self.assertEqual(nomes, set(jhu["sha256"]))
        self.assertEqual(nomes, set(jhu["url_por_arquivo"]))
        self.assertNotIn("extrair", jhu)
        fontes = {f["chave"]: f for f in radai_consent.fontes_de_terceiros()}
        self.assertEqual(fontes["jhu_rectum"]["uso_permitido"], "nao_especificado")
        self.assertFalse(fontes["jhu_rectum"]["livre"])
        self.assertTrue(fontes["moose_ribs"]["livre"])

    def test_instala_e_repara_zip_com_a_mesma_assinatura_de_tamanho(self):
        ident = "ensaio_local"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache = base / "origem.zip"
            conteudo = {"Dataset/plans.json": b"grade", "Dataset/rede.pth": b"peso"}
            with zipfile.ZipFile(cache, "w") as z:
                for nome, dados in conteudo.items():
                    z.writestr(nome, dados)
            sha = {n: hashlib.sha256(v).hexdigest() for n, v in conteudo.items()}
            sha["peso.zip"] = hashlib.sha256(cache.read_bytes()).hexdigest()
            modelo = {
                "nome": ident, "motor": ident, "uso_permitido": "livre", "licenca": "teste",
                "arquivos": [("peso.zip", cache.stat().st_size)], "extrair": "peso.zip",
                "url_direta": cache.as_uri(), "sha256": sha,
                "conteudo": [(n, len(v)) for n, v in conteudo.items()],
            }
            with patch.dict(modelos.MODELOS, {ident: modelo}), patch.dict(
                os.environ, {"RADAI_MODELOS_DIR": str(base / "modelos")}
            ):
                destino = modelos.pasta_do_modelo(ident, criar=True)
                marca = destino / "pesos_extraidos.txt"
                marca.write_text("interrompido", encoding="utf-8")
                self.assertFalse(modelos.estado_do_modelo(ident)["instalado"])
                modelos.baixar(ident)
                self.assertFalse((destino / "peso.zip").exists())
                preparo.conferir_modelos_exigidos(base, exigidos=[ident])
                marca.unlink()
                self.assertTrue(modelos.estado_do_modelo(ident)["instalado"])
                with patch.object(modelos, "_baixar_arquivo", side_effect=AssertionError):
                    self.assertFalse(modelos.baixar(ident)["baixados"])
                peso = destino / "Dataset" / "rede.pth"
                peso.write_bytes(b"erro")
                with self.assertRaises(preparo.FaltaModeloExigido):
                    preparo.conferir_modelos_exigidos(base, exigidos=[ident])
                modelos.baixar(ident)
                self.assertEqual(peso.read_bytes(), b"peso")
                preparo.conferir_modelos_exigidos(base, exigidos=[ident])


if __name__ == "__main__":
    unittest.main()
