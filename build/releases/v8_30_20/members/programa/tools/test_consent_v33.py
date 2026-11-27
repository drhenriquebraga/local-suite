"""Migração de recibos da 3.2 publicada para a Política 3.3 em estações isoladas."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_consent as cs


class Consentimento33(unittest.TestCase):
    def test_recibos_32_e_configuracao_da_estacao(self):
        for legado in (False, True):
            with self.subTest(legado=legado), tempfile.TemporaryDirectory() as tmp, patch.object(
                    cs.radai_archive, "raiz", return_value=Path(tmp)), patch.object(cs, "_maquina", return_value="FANTOMA"):
                pasta = Path(tmp)
                caminho = cs._caminho()
                anterior = pasta / cs.ARQUIVO_ACEITE if legado else caminho
                anterior.parent.mkdir(parents=True, exist_ok=True)
                recibo = {"versao": "3.2", "maquina": "FANTOMA", "impressao": cs.IMPRESSOES_PUBLICADAS["3.2"]}
                dados = json.dumps(recibo, indent=4).encode()
                anterior.write_bytes(dados)
                self.assertFalse(cs.aceito())
                self.assertEqual(cs.aceite(), recibo)
                chave = cs.catalogo_termos.catalogo()[0]
                itens = [p[0] for p in cs.PONTOS]
                opcionais = cs.catalogo_termos.grupos_opcionais()
                for _ in range(2):
                    cs.registrar_aceite("", itens, chave, True, opcionais)
                    self.assertTrue(cs.aceito())
                copias = list((caminho.parent / "historico").glob("*.json"))
                esperado = caminho.parent / "historico" / (hashlib.sha256(dados).hexdigest() + ".json")
                self.assertEqual(copias, [esperado])
                self.assertEqual(copias[0].read_bytes(), dados)
                if legado:
                    self.assertEqual(anterior.read_bytes(), dados)
                self.assertEqual(cs.aceite()["impressao"], cs.IMPRESSOES_PUBLICADAS["3.3"])
                with patch.object(cs, "_maquina", return_value="OUTRA"):
                    self.assertFalse(cs.aceito())


if __name__ == "__main__":
    unittest.main()
