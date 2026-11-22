# -*- coding: utf-8 -*-
"""Guia 2 e dicas em estações novas e atualizadas. Não requer pesos ou exames."""
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import radai_roteiro as guia
import radai_languages as idiomas


class TestDicas(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.cfg = Path(pasta.name) / "config"
        self.cfg.write_text("ROOT=R:\\Exames\nGUIA_VISTO=1\n", encoding="utf8")
        self.tab = "aba-interativa"

    def test_localizacao(self):
        entradas = guia._catalogo()
        self.assertEqual(set(entradas), {item[0] for item in idiomas.IDIOMAS})
        for lang, dados in entradas.items():
            with self.subTest(lang=lang):
                self.assertEqual(set(dados["tips"]), set(guia.DESTINOS))
                self.assertEqual(len(set(dados["tips"].values())), 30)
                self.assertEqual(set(dados["labels"]), set(entradas["en"]["labels"]))
                self.assertTrue(all(x.strip() for x in dados["labels"].values()))
                for passo in guia.PASSOS:
                    self.assertTrue(passo.get("nome") or dados["labels"][passo["titulo"]])
                    self.assertTrue(dados["tips" if "dica" in passo else "labels"][passo.get("dica", passo.get("texto"))])
                if lang != "pt-BR":
                    self.assertTrue(all(dados["tips"][k] != entradas["pt-BR"]["tips"][k] for k in guia.DESTINOS))

    def test_uma_por_abertura_e_apenas_apos_renderizar(self):
        s = guia.Sessao(self.cfg)
        self.assertEqual(s.agir("inicio", self.tab)["tipo"], "guia")
        self.assertEqual(s.agir("inicio", "outra-aba")["tipo"], "nada")
        self.assertFalse(s.historico.exists())
        self.assertEqual(s.agir("concluir", self.tab)["id"], "fast")
        self.assertEqual(s.agir("inicio", self.tab)["id"], "fast")
        self.assertFalse(s.historico.exists())
        self.assertEqual(s.agir("exibida", self.tab, "fast"), {"ok": True})
        self.assertEqual(s.agir("inicio", self.tab)["tipo"], "nada")
        self.assertEqual(s.lidos(), ["fast"])
        self.assertIn("ROOT=R:\\Exames", self.cfg.read_text(encoding="utf8"))
        self.assertTrue(s.agir("estado", None)["visto"])
        convite = s.convidar_reabertura()
        self.assertEqual(s.agir("inicio", "outra-aba", convite)["id"], "liver")
        self.assertEqual(s.agir("inicio", self.tab, convite)["tipo"], "nada")
        s.agir("exibida", "outra-aba", "liver")
        self.assertEqual(s.agir("inicio", self.tab, convite)["tipo"], "nada")

    def test_ciclo_e_preferencia(self):
        guia.gravar_marca(self.cfg)
        ids = []
        for _ in range(30):
            s = guia.Sessao(self.cfg)
            prox = s.agir("inicio", self.tab)["id"]
            s.agir("exibida", self.tab, prox)
            ids.append(prox)
        self.assertEqual(len(set(ids)), 30)
        s = guia.Sessao(self.cfg)
        with self.assertRaises(ValueError):
            s.agir("preferencia", self.tab, "0")
        s.agir("preferencia", self.tab, False)
        self.assertEqual(s.agir("inicio", self.tab)["tipo"], "nada")
        self.assertEqual(json.loads(s.historico.read_text()), ids)
        s.agir("preferencia", self.tab, True)
        s = guia.Sessao(self.cfg)
        reinicio = s.agir("inicio", self.tab)["id"]
        s.agir("exibida", self.tab, reinicio)
        self.assertEqual(reinicio, ids[0])
        self.assertEqual(s.lidos(), [reinicio])

    def test_transferencia_so_da_preferencia(self):
        import radai_config_transferencia as transferencia
        s = guia.Sessao(self.cfg)
        s.agir("preferencia", None, False)
        guia.gravar_marca(self.cfg)
        s.historico.write_text('["fast"]', encoding="utf8")
        chaves = ["DICAS_AO_INICIAR", "GUIA_VISTO"]
        pacote = transferencia.exportar(self.cfg, chaves, "", ["configuracao"], {})
        self.assertEqual(pacote["secoes"]["configuracao"], {"DICAS_AO_INICIAR":"0"})
        outra = self.cfg.parent / "segunda" / "config"
        outra.parent.mkdir()
        nova = guia.Sessao(outra)
        pedido = {"dados": pacote, "secoes": ["configuracao"]}
        previa = transferencia.transferir(pedido, outra, chaves, {}, "")
        transferencia.transferir(dict(pedido, revisao=previa["revisao"]), outra, chaves, {}, "", aplicar=True)
        self.assertEqual(nova.agir("estado", None), {"visto":False,"mostrar":False})
        self.assertEqual(nova.lidos(), [])
        self.assertEqual(s.lidos(), ["fast"])

    def test_abas_simultaneas(self):
        guia.gravar_marca(self.cfg)
        s = guia.Sessao(self.cfg)
        with ThreadPoolExecutor(4) as pool:
            tipos = list(pool.map(lambda i: s.agir("inicio", "aba-diferente-" + str(i))["tipo"], range(8)))
        self.assertEqual(tipos.count("dica"), 1)

    def test_api_consentimento_origem_e_plugins(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        guia.montar(app, self.cfg)
        with TestClient(app) as c:
            lingua = c.get("/api/roteiro/interface?idioma=ar").json()
            pedido = {"acao": "inicio", "aba": self.tab, "sessao": lingua["sessao"]}
            with patch("radai_consent.aceito", return_value=False):
                self.assertEqual(c.post(guia.ROTA_API,json=pedido).status_code, 409)
            with patch("radai_consent.aceito", return_value=True):
                self.assertEqual(c.post(guia.ROTA_API,json=pedido,headers={"origin":"https://other.example"}).status_code, 403)
                self.assertEqual(c.post(guia.ROTA_API,json=dict(pedido,sessao="anterior")).status_code, 409)
                self.assertEqual(c.post(guia.ROTA_API,json=pedido).json()["tipo"], "guia")
                self.assertIn("التالي", lingua["labels"].values())
                guia.gravar_marca(self.cfg)
                # Falta de plugin leva a seu card. A série e a fila de execução ficam livres.
                hist = self.cfg.with_name(guia.ARQUIVO_DICAS)
                hist.write_text(json.dumps(list(guia.DESTINOS)[:9]))
                self.assertEqual(c.post(guia.ROTA_API,json=dict(pedido,acao="concluir")).json()["url"], "/config#ps_neuro")
                token = app.state.radai_convite_guia()
                app.state.neuro_plugin_mount = {"mounted": True}
                self.assertEqual(c.post(guia.ROTA_API,json=dict(pedido,aba="nova-aba",valor=token)).json()["url"], "/neuro/nidus")

if __name__ == "__main__":
    unittest.main(verbosity=2)
