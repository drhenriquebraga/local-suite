"""Invariantes da rede da TC em filas, cache e chamada efetiva do TotalSegmentator."""
from pathlib import Path
from datetime import datetime
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
sys.path[:0] = [str(TOOLS.parent / "app"), str(TOOLS)]

import engine
import radai_batch as batch
import radai_cache_tasks as cache
import radai_queue_state as fila
import radai_tasks
import radai_velocidade_tc as velocidade
from test_engine import _rodar_falso


class VelocidadeTC(unittest.TestCase):
    def test_seis_esforcos_preservam_o_plano_e_os_complementos(self):
        solicitadas = {"trunk_cavities": 1, "breasts": 1, "moose_ribs": 1}
        serie = dict(modalidade="CT", modo="perso", protocolos=["sbrt_pulmao"],
                     tasks=solicitadas, oar_fora=["pancreas"])
        base = batch.escolha_da_serie(dict(serie, esforco="maximo"))
        for esforco, (mm, nivel) in velocidade.NIVEIS.items():
            atual = batch._com_escolhas_da_tela({"series": [dict(serie, esforco=esforco)]})[0]
            escolha = batch.escolha_da_serie(atual)
            for k in ("modo", "protocolos", "tasks", "tasks_marcadas", "comparacao", "oar_fora"):
                self.assertEqual(escolha[k], base[k])
            self.assertEqual(escolha["esforco"], esforco)
            self.assertEqual(velocidade.mm_da_escolha(escolha, "total_v3"), mm)
            self.assertEqual(velocidade.mm_da_escolha(dict(escolha, modalidade="MR"), "total_mr"), "1.5")
            self.assertFalse(batch.so_pericardio_na_serie(escolha, {"torax"}))
            self.assertEqual(batch._com_escolhas_da_tela({"series": [{"modo":"auto", "esforco":esforco}]})[0]["esforco"], esforco)

    def test_preferencia_congelada_e_configuracoes_anteriores_preservadas(self):
        import radai_config
        with tempfile.TemporaryDirectory() as temp:
            cfg = Path(temp)/"app.config"
            cfg.write_text("FAST_NIVEL=1\nPORT=8712\n", encoding="utf-8")
            with patch.dict(os.environ, RADAI_CONFIG=str(cfg)):
                self.assertEqual(velocidade.esforco_atual(), "maximo")
                self.assertTrue(radai_config.escrever(cfg, {"ESFORCO_PADRAO":"medio"})[0])
                serie = batch._congelar_fast({"modo":"auto"})
                self.assertFalse(radai_config.escrever(cfg, {"ESFORCO_PADRAO":"outro"})[0])
                self.assertTrue(radai_config.escrever(cfg, {"ESFORCO_PADRAO":"leve"})[0])
                self.assertEqual(batch._congelar_fast(serie, legado=True)["esforco"], "medio")
                self.assertEqual(batch._congelar_fast({"modo":"auto","fast_tc_mm":"3"}, legado=True)["esforco"], "medio")
                self.assertEqual(batch._congelar_fast({})["esforco"], "leve")
                self.assertEqual(radai_config.ler_arquivo(cfg)[1]["FAST_NIVEL"], "1")
                with patch.object(fila, "_CARDS", []):
                    fila._acrescentar([{"uid": "0.2.1", "pasta":"CT", "modo": "auto", "esforco":"extra"}], "lote")
                    self.assertEqual(fila._ao_arquivo(fila._CARDS[0])["escolha"]["esforco"], "extra")

    def test_repeticao_de_base_antes_da_topografia_e_motores(self):
        class Ref:
            def GetSize(self): return (10, 10, 10)
        entradas, entregues = [], []
        def rodar(ref, t, device, jid, **kw):
            entradas.append((t, kw.get("base_tc_mm", "1.5")))
            if t == "total_v3":
                presentes = dict.fromkeys(("liver", "duodenum", "pancreas"), True)
                if kw.get("base_tc_mm") == "3":
                    presentes["gallbladder"] = True
                kw["cruas"][t] = presentes
                return presentes
            return {}
        def depois(t, masks, cruas):
            if t == "total_v3":
                entregues.append(set(cruas[t]))
            return []
        out = engine.rodar_tasks(Ref(), ["total_v3", "breasts"], "cpu", "teste", rodar=rodar,
                                 depois_de=depois, recortar=False, portao=False, base_tc_mm="6",
                                 destinos_base={"gallbladder"})
        self.assertEqual(entradas, [("total_v3", "6"), ("total_v3", "3"), ("breasts", "1.5")])
        self.assertIn("gallbladder", entregues[0])
        self.assertEqual(out["base_tc_mm"], "3")
        self.assertEqual(velocidade.faltantes_no_campo({"heart", "liver"}, {"gallbladder"}), set())
        self.assertEqual(velocidade.faltantes_no_campo({"liver", "duodenum", "pancreas"}, {"heart"}), set())

    def test_so_pericardio_exige_destino_unico(self):
        auto = batch.escolha_da_serie({"modalidade":"CT","modo":"auto","esforco":"maximo"})
        self.assertTrue(batch.so_pericardio_na_serie(auto, {"torax"}))
        self.assertFalse(batch.so_pericardio_na_serie(auto, {"torax","abdome"}))
        self.assertFalse(batch.so_pericardio_na_serie(auto, {"torax"}, marcadas={"trunk_cavities"}))
        self.assertFalse(batch.so_pericardio_na_serie(dict(auto, anatomia_geral_full=True), {"torax"}))
        self.assertFalse(batch.so_pericardio_na_serie(dict(auto, comparacao={"ts":1}), {"torax"}))
        custom = dict(auto, modo="perso")
        self.assertTrue(batch.so_pericardio_na_serie(custom, {"torax"}, {"estruturas":["heart"]}))
        self.assertFalse(batch.so_pericardio_na_serie(custom, {"torax"}, {"estruturas":["heart", "bag_bowel_oar"]}))

    def test_campo_das_cavidades_segue_destinos_e_unioes(self):
        auxiliares = {"bag_bowel_oar", "anus", "Skin", "ChestWall_L", "ChestWall_R"}
        def usar(codigos=(), fora=(), *, proprio=None, marcadas=(), comp=None):
            s = dict(modo="perso", modalidade="CT", protocolos=list(codigos), oar_fora=list(fora),
                     tasks={k: 1 for k in marcadas}, tasks_marcadas=list(marcadas), comparacao=comp or {})
            return batch.so_pericardio_na_serie(batch.escolha_da_serie(s), {"torax", "abdome"}, proprio)
        for protocolo in ("sbrt_pulmao", "sbrt_figado"):
            self.assertFalse(usar([protocolo]))
            self.assertTrue(usar([protocolo], auxiliares))
            for destino in auxiliares:
                with self.subTest(protocolo=protocolo, destino=destino):
                    self.assertFalse(usar([protocolo], auxiliares - {destino}))
        preset = dict(modo="perso", modalidade="CT", protocolos=["torax_mama"])
        fabrica = batch.escolha_da_serie(preset)
        self.assertEqual(set(fabrica["oar_fora"]), {"bag_bowel_oar", "anus"})
        self.assertTrue(batch.so_pericardio_na_serie(fabrica, {"torax", "abdome"}))
        restaurado = batch._com_escolhas_da_tela({"series":[dict(preset, oar_fora=[])]})[0]
        self.assertFalse(batch.so_pericardio_na_serie(batch.escolha_da_serie(restaurado), {"torax", "abdome"}))
        self.assertTrue(usar(["torax_mama"], {"bag_bowel_oar", "anus"}))
        self.assertFalse(usar(["torax_mama"], {"bag_bowel_oar"}))
        coracao = {"estruturas": ["heart"]}
        self.assertTrue(usar(proprio={"estruturas":["great_arteries"]}))
        self.assertFalse(usar(proprio={"estruturas":["breast_left", "breast_right"]}))
        propria = dict(coracao, merges=[{"nome":"UniaoA", "de":["mediastinum", "heart"]}])
        self.assertFalse(usar(fora={"mediastinum"}, proprio=propria))
        self.assertTrue(usar(fora={"uniao:UniaoA", "mediastinum"}, proprio=propria))
        raw = {"abdominal_cavity", "thoracic_cavity", "mediastinum"}
        self.assertFalse(usar(proprio=coracao, marcadas=["trunk_cavities"]))
        self.assertTrue(usar(fora=raw, proprio=coracao, marcadas=["trunk_cavities"]))
        self.assertFalse(usar(proprio=coracao, comp={"ts":1}))
        self.assertTrue(usar(fora={"ts:"+k for k in raw}, proprio=coracao, comp={"ts":1}))
        self.assertTrue(usar(proprio=coracao, comp={"nv":1}))
        desligada = batch.escolha_da_serie({"modo":"perso", "tasks":{"trunk_cavities":0}})
        self.assertFalse(batch.so_pericardio_na_serie(desligada, {"torax"}, coracao))

    def test_referencias_de_todos_os_motores_do_visor(self):
        import radai_bibliography as bib
        with patch.object(bib, "_recibo", return_value=""):
            html = bib._pagina()
        self.assertEqual(html.count('id="modelos"'), 1)
        for modelo in ("total_v3", "trunk_cavities", "breasts", "pleural_pericard_effusion",
                       "lung_vessels", "Dataset444_Ribs"):
            self.assertIn(modelo, html)

    def test_argv_rede_secundaria_e_cache(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(radai_tasks, "exigir_peso_resolucao_ct",
                side_effect=lambda mm: {3: 836, 6: 837}[mm]), patch.object(cache, "armado", return_value=False):
            for task, mm, flag in (("total_v3", "3", "--fast"), ("total_v3", "6", "--fastest"),
                                    ("total_v3", "1.5", None), ("total_mr", "1.5", None)):
                resultado, _, registros, _ = _rodar_falso(tmp, "gravar_saida()\n", task, tmp, base_tc_mm=mm)
                self.assertIsInstance(resultado, dict, str(resultado))
                self.assertEqual(set(registros[0]["args"]) & {"--fast", "--fastest"}, {flag} if flag else set())
            for task in ("total_mr", "breasts", "trunk_cavities"):
                resultado, _, registros, _ = _rodar_falso(tmp, "gravar_saida()\n", task, tmp, base_tc_mm="6")
                self.assertIsInstance(resultado, ValueError, str(resultado))
                self.assertEqual(registros, [])
        with patch.object(radai_tasks, "pasta_pesos", return_value=""):
            chaves = [cache.chave("vol", "total_v3", cache.receita("total_v3", dataset_base=d))
                      for d in (None, 836, 837)]
        self.assertEqual(len(set(chaves)), 3)

    def test_estimativa_memoria_da_rede_real(self):
        tamanho = (144, 144, 144)
        spacing = (1.5, 1.5, 1.5)
        for mm in (3, 6):
            est = engine.estimativa_de_ram("total_v3", tamanho, spacing, partes=[117], grade_mm=mm)
            plano = engine.plano_de_dispositivo(tamanho, spacing, inv={"placas": []}, partes=[117], grade_mm=mm)
            esperado = int(144 * 1.5 / mm) ** 3
            self.assertEqual(est["voxels"], esperado)
            self.assertEqual(plano["voxels"], esperado)


if __name__ == "__main__":
    unittest.main()
