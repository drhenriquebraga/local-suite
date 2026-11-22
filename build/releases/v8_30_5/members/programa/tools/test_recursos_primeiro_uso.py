"""Exercita a cópia do código em uma estação isolada e a seleção offline de recursos."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
import configurar_ambiente as preparar
from empacotar_instalador import entra


class RecursosDoPrimeiroUso(unittest.TestCase):
    def test_montagem_preserva_estacao_e_transfere_as_previas(self):
        recursos = {
            "data/dicas-suite.json", "data/roteiro-suite.css", "data/roteiro-suite.js",
            "radai_fast_ui.py", "radai_fast_i18n.py", "radai_fast_config.py", "radai_roteiro.py",
        }
        recursos.update(
            f"data/fast_previews/{caso}-{nivel}.png"
            for caso in ("thorax", "bowel") for nivel in range(5)
        )
        privados = {
            "radai_watcher.config": b"GUIA_VISTO=1\n",
            "local-suite-dicas-vistas.json": b'["fast"]',
            "nomes_proprios.json": b'{"exemplo":"nome-de-teste"}',
            "protocolos_proprios.json": b'[{"nome":"protocolo-de-teste"}]',
        }
        with tempfile.TemporaryDirectory() as tmp, patch.object(preparar, "log"):
            alvo = Path(tmp)
            for nome, antes in privados.items():
                (alvo / nome).write_bytes(antes)
            preparar._montar_codigo({"instalar": True, "bundle": alvo})
            extra = alvo / "data/fast_previews/arquivo-da-estacao.png"
            extra.write_bytes(b"isca")
            portateis = {p.relative_to(alvo).as_posix() for p in preparar._arquivos_do_bundle(alvo)}
            self.assertTrue(recursos.issubset(portateis), recursos - portateis)
            self.assertFalse(privados.keys() & portateis)
            self.assertNotIn(extra.relative_to(alvo).as_posix(), portateis)
            for nome, antes in privados.items():
                self.assertEqual((alvo / nome).read_bytes(), antes, nome)
                self.assertFalse(entra(nome), nome)
            for nome in recursos:
                self.assertEqual((ROOT / "app" / nome).read_bytes(), (alvo / nome).read_bytes(), nome)


if __name__ == "__main__":
    unittest.main()
