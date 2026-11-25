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
    def test_alto_extra_e_maximo_partem_do_mesmo_acabamento(self):
        from radai_fast_config import nivel
        for esforco in ("alto", "extra", "maximo"):
            self.assertEqual(velocidade.NIVEIS[esforco], ("1.5", 4))
        # Configurações antigas de acabamento são independentes dos novos esforços.
        self.assertEqual(nivel({"FAST_NIVEL": "2"}), 2)
        self.assertEqual(nivel({"FAST_NIVEL": "3"}), 3)

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
            with patch.object(velocidade, "esforco_atual", return_value="medio"):
                auto = batch._com_escolhas_da_tela({"series": [{"modo":"auto", "esforco":esforco}]})[0]
                self.assertEqual(auto["esforco"], "medio")

    def test_preferencia_congelada_e_configuracoes_anteriores_preservadas(self):
        import radai_config
        with tempfile.TemporaryDirectory() as temp:
            cfg = Path(temp)/"app.config"
            cfg.write_text("FAST_NIVEL=1\nPORT=8712\n", encoding="utf-8")
            with patch.dict(os.environ, RADAI_CONFIG=str(cfg)):
                self.assertEqual(velocidade.esforco_atual(), "extra")
                self.assertTrue(radai_config.escrever(cfg, {"ESFORCO_PADRAO":"maximo"})[0])
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

    def test_base_nativa_unica_antes_da_topografia_e_motores(self):
        class Ref:
            def GetSize(self): return (10, 10, 10)
        entradas, entregues = [], []
        def rodar(ref, t, device, jid, **kw):
            entradas.append((t, kw.get("base_tc_mm", "1.5")))
            if t == "total_v3":
                presentes = dict.fromkeys(("liver", "duodenum", "pancreas"), True)
                kw["cruas"][t] = presentes
                return presentes
            return {}
        def depois(t, masks, cruas):
            if t == "total_v3":
                entregues.append(set(cruas[t]))
            return []
        def portao(task, *args, **kwargs):
            return "sem marcos cervicais" if task == "head_glands_cavities" else None
        for mm in ("6", "3"):
            entradas.clear()
            entregues.clear()
            with self.subTest(mm=mm), patch.object(engine, "portao_da_regiao", side_effect=portao):
                out = engine.rodar_tasks(Ref(), ["total_v3", "head_glands_cavities", "breasts"], "cpu",
                        "teste", rodar=rodar, depois_de=depois, recortar=False, base_tc_mm=mm,
                        destinos_base={"gallbladder"}, selecionadas={"head_glands_cavities"})
                self.assertEqual(entradas, [("total_v3", mm), ("breasts", "1.5")])
                self.assertEqual(entregues, [{"liver", "duodenum", "pancreas"}])
                self.assertEqual(out["base_tc_mm"], mm)
                self.assertEqual([p["task"] for p in out["puladas"]], ["head_glands_cavities"])
                self.assertIn("gallbladder", out["ausentes"][0]["motivo"])
                self.assertIn(mm + " mm", out["ausentes"][0]["motivo"])
        self.assertEqual(velocidade.faltantes_no_campo({"heart", "liver"}, {"gallbladder"}), set())
        self.assertEqual(velocidade.faltantes_no_campo({"liver", "duodenum", "pancreas"}, {"heart"}), set())

    def test_base_v2_legada_e_cache_de_repeticao(self):
        for esforco, mm in (("leve", "6"), ("medio", "3"), ("maximo", "1.5")):
            escolha = {"modalidade": "CT", "esforco": esforco}
            base = velocidade.base_para_o_esforco(escolha, "total_v2")
            self.assertEqual(base, "total_v2" if mm == "1.5" else "total_v3")
            self.assertEqual(velocidade.mm_da_escolha(escolha, base), mm)
            self.assertEqual(velocidade.base_para_o_esforco(escolha, "breasts"), "breasts")
            self.assertEqual(velocidade.incompatibilidade_do_cache(escolha, mm), "")
            for outra in {"6", "3", "1.5", "?"} - {mm}:
                motivo = velocidade.incompatibilidade_do_cache(escolha, outra)
                self.assertIn(mm + " mm", motivo)
                self.assertIn(outra + " mm", motivo)
        rm = {"modalidade": "MR", "esforco": "leve"}
        self.assertEqual(velocidade.base_para_o_esforco(rm, "total_mr"), "total_mr")
        self.assertEqual(velocidade.incompatibilidade_do_cache(rm, "1.5"), "")
        with self.assertRaisesRegex(ValueError, "total_v3"):
            engine.rodar_tasks(None, ["total_v2"], "cpu", "teste", base_tc_mm="6", portao=False)

    def test_refazer_pos_verifica_resolucao_efetiva_antes_da_fila(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        antigo_leve = {"modo": "auto", "esforco": "leve", "base_tc_mm": "3"}
        marcadores = {"read_marker": lambda *args: antigo_leve}
        serie = {"uid": "0.1.2", "pasta": "TC", "modo": "auto", "modalidade": "CT", "esforco": "leve"}
        with patch.dict(batch._CFG), patch.object(batch, "pos_refazivel", return_value={"refazivel": True}), \
                patch.object(batch, "por_na_fila", return_value={"ok": True}) as enfileirar, \
                patch.object(batch, "coronaria_solicitada", return_value=False):
            batch.montar(app, {"marcadores": marcadores})
            with TestClient(app) as cliente, patch.object(velocidade, "esforco_atual", return_value="leve"):
                recusado = cliente.post("/api/lote/refazer_pos", json={"series": [serie]})
                self.assertEqual(recusado.status_code, 409)
                self.assertIn("3 mm", recusado.json()["erro"])
                self.assertIn("6 mm", recusado.json()["erro"])
                enfileirar.assert_not_called()
                aceito = cliente.post("/api/lote/refazer_pos", json={"series": [dict(serie, modo="perso", esforco="medio")]})
                self.assertTrue(aceito.json()["ok"])
                self.assertEqual(enfileirar.call_args.args[0][0]["so_pos_base_mm"], "3")

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
                    # Estes destinos intestinais só abrem o campo quando fazem
                    # parte do protocolo. O ânus fica no protocolo da pelve.
                    usa_campo_cardio = destino == "anus" or (
                        destino == "bag_bowel_oar" and protocolo == "sbrt_pulmao")
                    self.assertEqual(usar([protocolo], auxiliares - {destino}), usa_campo_cardio)
        preset = dict(modo="perso", modalidade="CT", protocolos=["torax_mama"])
        fabrica = batch.escolha_da_serie(preset)
        self.assertEqual(fabrica["oar_fora"], ())
        self.assertTrue(batch.so_pericardio_na_serie(fabrica, {"torax", "abdome"}))
        restaurado = batch._com_escolhas_da_tela({"series":[dict(preset, oar_fora=[])]})[0]
        self.assertTrue(batch.so_pericardio_na_serie(batch.escolha_da_serie(restaurado), {"torax", "abdome"}))
        self.assertTrue(usar(["torax_mama"], {"bag_bowel_oar", "anus"}))
        self.assertTrue(usar(["torax_mama"], {"bag_bowel_oar"}))
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
                # Uma estação com só a base V2 em alta resolução ainda pode
                # ter os pesos rápidos V3 instalados.
                opcoes = {"base_eleita": lambda *a, **k: "total_v2"} if flag else {}
                resultado, _, registros, _ = _rodar_falso(tmp, "gravar_saida()\n", task, tmp,
                                                         base_tc_mm=mm, **opcoes)
                self.assertIsInstance(resultado, dict, str(resultado))
                self.assertEqual(set(registros[0]["args"]) & {"--fast", "--fastest"}, {flag} if flag else set())
                self.assertEqual(registros[0]["task"], task)
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

    def test_peso_nativo_ausente_corrompido_ou_rejeitado_no_motor(self):
        import json
        with tempfile.TemporaryDirectory() as tmp, patch.object(cache, "armado", return_value=False):
            dataset = "Dataset837_TotalSegmentator_total_6mm_1559subj"
            treino = Path(tmp) / dataset / "nnUNetTrainer_4000epochs_NoMirroring__nnUNetPlans__3d_fullres"
            for danificado in (False, True):
                if danificado:
                    (treino / "fold_0").mkdir(parents=True)
                    (treino / "plans.json").write_text(json.dumps({"dataset_name": dataset,
                        "configurations": {"3d_fullres": {"spacing": [6, 6, 6]}}}), encoding="utf-8")
                    (treino / "dataset.json").write_text('{"labels":{"liver":1}}', encoding="utf-8")
                    (treino / "fold_0" / "checkpoint_final.pth").write_bytes(b"truncado")
                with self.subTest(danificado=danificado):
                    erro, _, chamadas, _ = _rodar_falso(tmp, "gravar_saida()\n", "total_v3", tmp, base_tc_mm="6")
                    self.assertIsInstance(erro, RuntimeError)
                    self.assertIn("Dataset837", str(erro))
                    self.assertIn("6 mm", str(erro))
                    self.assertEqual(chamadas, [])
            with patch.object(radai_tasks, "exigir_peso_resolucao_ct", return_value=837):
                from totalsegmentator.map_tasks_config import TASK_CONFIGS
                # A biblioteca oficial escolhe 'fast' se não encontrar 'fastest'.
                v3_incompleta = {"sub_modes": {"fast": {"task_id": 836, "resample": 3.0}}}
                with patch.dict(TASK_CONFIGS, {"total_v3": v3_incompleta}):
                    erro, _, chamadas, _ = _rodar_falso(tmp, "gravar_saida()\n", "total_v3", tmp, base_tc_mm="6")
                    self.assertIsInstance(erro, RuntimeError)
                    self.assertIn("não declara", str(erro))
                    self.assertEqual(chamadas, [])
                erro, _, chamadas, _ = _rodar_falso(tmp, "raise RuntimeError('checkpoint invalido')\n",
                        "total_v3", tmp, base_tc_mm="6")
                self.assertIsInstance(erro, RuntimeError)
                self.assertEqual(len(chamadas), 1)
                self.assertIn("--fastest", chamadas[0]["args"])


if __name__ == "__main__":
    unittest.main()
