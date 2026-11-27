"""Regressões do esforço entregue, da leitura local e dos monitores contínuos."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_archive as archive
import radai_dedicado as dedicado
import radai_queue as q
import radai_tabela_acervo as tabela

class Acervo(unittest.TestCase):
    def test_novo_legado_e_cancelamento(self):
        with tempfile.TemporaryDirectory() as d, patch.object(archive, "caminho_acervo", return_value=Path(d)/"indice"):
            p = archive.caminho_acervo()
            uid = "1.2.3"
            for n in range(1500):
                with p.open("ab") as f:
                    f.write((json.dumps({"uid":str(n), "pasta":d, "pid":"A"*70})+chr(10)).encode())
            self.assertTrue(archive.registrar_serie(uid,d,"RS.dcm",modalidade="CT",esforco="extra"))
            self.assertTrue(archive.registrar_serie("2.3",d,"MR.dcm",modalidade="MR",esforco="maximo"))
            self.assertTrue(archive.registrar_serie("2.4",d,"L.dcm"))
            with p.open("ab") as f:
                f.write(b"truncated")
            lista=tabela.linhas(3)["series"]
            self.assertEqual([x["esforco"] for x in lista],[None,None,"extra"])
            self.assertEqual(len(archive.ler_acervo()),1503)
            self.assertEqual(len(archive.ler_acervo(4)),4)
            self.assertEqual(list(archive.iterar_acervo(lambda: True)),[])
            self.assertEqual(archive.ler_acervo(1)[0]["uid"],"2.4")
            with patch.object(tabela,"_ler_done",return_value={"uid":uid,"rs":"RS.dcm","esforco":"medio","modalidade":"CT"}), patch.object(tabela,"_cabecalho_da_serie",return_value=("","CT",None)):
                self.assertEqual(tabela.detalhe_da_serie(d,uid,registro={"rs":"RS.dcm"})["esforco"],"medio")
                self.assertIsNone(tabela.detalhe_da_serie(d,uid,registro={"rs":"outro.dcm"})["esforco"])

class Continuos(unittest.TestCase):
    def test_finaliza_somente_quando_os_monitores_tambem_terminam(self):
        class Fila:
            Q=q
            atual=[]
            @classmethod
            def cards(cls): return cls.atual
        estado={"overnight":False}
        snap=lambda:dedicado._snapshot(Fila,lambda:estado)
        serie=q.novo_card(q.SERIE,uid="u")
        Fila.atual=[serie]
        inicial=snap()
        self.assertFalse(inicial["encerrada"](inicial))
        Fila.atual=[]
        self.assertTrue(snap()["encerrada"](inicial))
        for monitor in [q.novo_card(q.OVERNIGHT),dict(q.novo_card("lung_screening"),id="lung-screening")]:
            Fila.atual=[monitor]
            self.assertFalse(snap()["encerrada"](inicial))
            self.assertTrue(snap()["continuo"])
        Fila.atual=[]
        estado["overnight"]=True
        self.assertFalse(snap()["encerrada"](inicial))
        estado["overnight"]=False
        self.assertTrue(snap()["encerrada"](inicial))

if __name__=="__main__":
    unittest.main()
