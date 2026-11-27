"""A estrutura ausente não condena o caso. Uma falha de execução continua parcial."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROGRAM = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROGRAM / "app"), str(PROGRAM / "tools")]
import radai_queue as Q
import radai_queue_state as fila


class Cartoes(unittest.TestCase):
    def test_detalhe_apenas_dados_locais_permitidos(self):
        fonte = dict(pid="QA-17", modalidade="CT", cortes=210, pasta="Q:/exames", nascimento="19000101")
        self.assertEqual(fila.detalhe_publico(fonte), {"pid": "QA-17", "modalidade": "CT", "cortes": 210})
        self.assertNotIn("pid", fila.detalhe_publico({"pid": "Q:\\exames"}))
        self.assertNotIn("pid", fila.CAMPOS_DO_ARQUIVO)

    def test_migracao_conservadora(self):
        c = dict(estado=Q.PARCIAL, tipo=Q.SERIE, origem=Q.RODAR_AGORA,
                 mensagem="ROI sem contorno válido: zygomatic_arch_left")
        self.assertTrue(fila._parcial_antiga_so_anatomica(c))
        for extra in ({"estado": Q.FALHOU}, {"motivo": "modelo indisponível"}, {"nao_contornavel":"TC inválida"},
                      {"faltou": ["mandible"]}, {"pendentes_por_memoria": [{"task": "total_v3"}]},
                      {"mensagem": c["mensagem"]+". Falha na conexão."},
                      {"mensagem": "Reto Johns Hopkins indisponível"}):
            self.assertFalse(fila._parcial_antiga_so_anatomica(dict(c, **extra)))

    def test_rede_vazia_difere_de_formato_invalido(self):
        import numpy as np
        from radai_rocards import _repor
        from radai_study_modelos import _SemContorno
        roi = (slice(0, 2),) * 3
        with self.assertRaises(_SemContorno):
            _repor(np.zeros((2, 2, 2), np.uint8), roi, None, None)
        with self.assertRaisesRegex(ValueError, "inválida"):
            _repor(np.ones((2, 2, 2), np.float32), roi, None, None)

    def test_vigia_nao_mistura_series(self):
        cards=[dict(id=i, estado=Q.RODANDO, tipo=Q.SERIE, executor=Q.VIGIA, origem=Q.VIGIA, uid=i)
               for i in ("A","B")]
        with patch.object(fila,"_CARDS",cards), patch.object(fila,"_mudou"):
            fila.progresso_vigia("A",["hnlnl"],"running")
            fila.progresso_vigia("A",["hnlnl"],"completed")
            fila.progresso_vigia("A",["__pos"],"running")
            self.assertEqual(cards[0]["andamento"]["tarefas"], {"hnlnl":"completed","__pos":"running"})
            self.assertNotIn("andamento",cards[1])

    def test_entrega_real_com_roi_ausente_e_falha_independente(self):
        import engine
        import pydicom
        from radai_output import Saida
        from test_hn_study_protocol import series, cube
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            series(raiz / "CT")
            out = raiz / "out"
            out.mkdir()
            s = Saida(engine, raiz / "CT", out, "RS_RadAI_qa.dcm", tasks=["total_v3"], modalidade="CT")
            eventos = []
            s.ao_progresso = lambda nome, estado: eventos.append((nome,estado))
            with patch.object(engine,"curar",side_effect=lambda m, extras, log=None:(dict(m),{k:"ts" for k in m})), \
                 patch.object(engine,"preparar_full",side_effect=lambda m,**kwargs:(dict(m),{})):
                res = s.full_e_oar({"total_v3":{"brain":cube(8,25,25)}}, modo="perso",
                                    protocolo={"modalidade":"CT","estruturas":["brain","zygomatic_arch_left"]},
                                    coronaria_rocards=False, arcos_costais_moose=False, reto_jhu=False)
            ds = pydicom.dcmread(res["entregue"])
            self.assertTrue(ds.ROIContourSequence)
            self.assertIn("zygomatic_arch_left",res["rois_sem_contorno"])
            self.assertIsNone(res["parcial"])
            self.assertEqual(eventos[-2:],[("__pos","completed"),("__gravar","running")])
            nome_gravado = str(ds.StructureSetROISequence[0].ROIName)
            propostas = {"brain": nome_gravado, "estrutura_esperada": "ausente_no_DICOM"}
            conferidas = s._publicar_entrega(res["entregue"], out / "releitura.dcm", propostas)
            self.assertEqual(conferidas, {"brain": nome_gravado})
            self.assertEqual(s.ausentes_no_rt, ["estrutura_esperada"])
            c = Q.novo_card(Q.SERIE, uid="1.2.3")
            self.assertEqual(fila._aplicar_desfecho(c,Q.PRONTO,sem_estrutura=res["rois_sem_contorno"])["estado"],Q.PRONTO)
            self.assertEqual(fila._aplicar_desfecho(c,Q.PRONTO,faltou=["hnlnl"])["estado"],Q.PARCIAL)

if __name__=="__main__":
    unittest.main(verbosity=2)
