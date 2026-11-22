"""A seleção da quarta coluna e o destino dos contornos usam o mesmo protocolo."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hn_study_protocol import series, cube, rois, E, OUTPUT
import pydicom
import radai_batch as batch
import radai_modes as modes
import radai_sets as sets


def previa(cod, modalidade="CT", **opcoes):
    dados = {"modo": "perso", "modalidade": modalidade, "protocolos": [cod], **opcoes}
    grupos = batch.previa_da_entrega(dados)["oar"]
    return [{r["chave"] for r in grupos[g]} for g in ("estruturas", "fora")]


class EscopoProtocolos(unittest.TestCase):
    def test_todos_os_presets_visiveis_tem_destinos(self):
        matriz = {
            "cranio": ("optic_chiasm", "heart"), "cabeca_pescoco_simples": ("LNL_UNION", "Lvl_IVa_L"),
            "cabeca_pescoco": ("Lvl_IVa_L", "kidney_left"), "torax_mama": ("heart", "bag_bowel_oar"),
            "sbrt_pulmao": ("ChestWall_R", "liver"), "sbrt_figado": ("liver_segment_8", "anus"),
            "abdome": ("liver_segment_1", "rectum"), "pelve": ("rectum", "heart"),
            "coluna": ("intervertebral_discs", "urinary_bladder"),
            "snc_rm": ("brainstem", "liver"), "coluna_rm": ("vertebrae_T4", "liver"),
            "abdome_rm": ("liver_segment_8", "sacrum"), "anatomia_toracica": ("lung_arteries", "abdominal_cavity"),
        }
        protocolos = [p for p in modes.PROTOCOLOS if not p.get("legado")] + list(modes.PROTOCOLOS_3D)
        self.assertEqual(set(matriz), {p["cod"] for p in protocolos})
        for p in protocolos:
            cod = p["cod"]
            with self.subTest(protocolo=cod):
                opts = {"protocolos": [], "protocolos_3d": [cod]} if cod in modes.PROT_3D_POR_COD else {}
                incluir, recusar = matriz[cod]
                sim, fora = previa(cod, p["modalidade"], oar_fora=[recusar], **opts)
                self.assertIn(incluir, sim)
                self.assertNotIn(recusar, sim | fora)

    def test_fila_sem_lista_de_marcadas_e_exclusao_manual(self):
        opcoes = {"tasks": {"trunk_cavities": 1, "breasts": 1}, "oar_fora": ["heart", "anus"]}
        sim, fora = previa("torax_mama", **opcoes)
        self.assertIn("heart", fora)
        self.assertNotIn("anus", sim | fora)
        self.assertNotIn("abdominal_cavity", sim | fora)
        e = batch.escolha_da_serie(dict(modo="perso", modalidade="CT", protocolos=["torax_mama"], **opcoes))
        self.assertNotIn("gallbladder", batch.destinos_do_esforco(e))
        self.assertTrue(batch.so_pericardio_na_serie(e, {"torax", "abdome"}))

    def test_tarefa_marcada_a_mao_e_full(self):
        opcoes = dict(personalizado_derivado=True, origem_personalizada={"protocolos": ["torax_mama"]},
                      tasks={"trunk_cavities": 1}, tasks_marcadas=["trunk_cavities"])
        sim, _ = previa("torax_mama", **opcoes)
        self.assertIn("abdominal_cavity", sim)
        self.assertNotIn("urinary_bladder", sim)
        full, _ = previa("torax_mama", anatomia_geral_full=True)
        self.assertIn("urinary_bladder", full)
        comparacao, _ = previa("torax_mama", comparacao={"ts": 1})
        self.assertIn("ts:urinary_bladder", comparacao)
        self.assertNotIn("urinary_bladder", comparacao)

    def test_protocolo_da_estacao_pode_incluir_todas_as_estruturas_reservadas(self):
        p = {"estruturas": list(sets.SO_NOS_SBRT | {"heart"}), "modalidade": "CT"}
        with patch.object(batch, "protocolo_proprio_da_escolha", return_value=p):
            sim, _ = previa(None, protocolos=[], protocolo_proprio="estacao")
        self.assertTrue(sets.SO_NOS_SBRT <= sim)
        e = batch.escolha_da_serie(dict(modo="perso", modalidade="CT", protocolo_proprio="estacao"))
        self.assertFalse(batch.so_pericardio_na_serie(e, {"torax", "abdome"}, p))

    def test_gravador_rele_dicom_com_bexiga_incidental(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            series(root / "tc")
            mapas = {"total_v3": {"esophagus": cube(5, 20, 20),
                                  "urinary_bladder": cube(5, 40, 40)}}
            saida = OUTPUT.Saida(E, root / "tc", root, "RS_RadAI_20200101_12345678.dcm",
                                 tasks=["total_v3"], versao="teste", suavizar_mm=0, modalidade="CT")
            with patch.object(E, "preparar_full", side_effect=lambda masks, **kw: (dict(masks), {})) as preparo:
                res = saida.full_e_oar(mapas, modo="perso", protocolos=["torax_mama"],
                                       regioes=["torax", "pelve"], coronaria_rocards=False)
            self.assertNotIn("urinary_bladder", preparo.call_args.kwargs["para"])
            gravadas, _, _ = rois(pydicom.dcmread(res["entregue"]))
            self.assertEqual(gravadas, {E.nome_clinico("esophagus")})


if __name__ == "__main__":
    unittest.main()
