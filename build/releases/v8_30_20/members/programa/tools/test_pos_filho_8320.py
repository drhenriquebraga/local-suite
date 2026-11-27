import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent/"app"), str(HERE)]
import numpy as np
import pydicom
import SimpleITK as sitk
import engine
from radai_output import Saida
from radai_pos_filho import executar
from test_engine import _serie_rm, _mascaras_de_pelve


def medir_memoria():
    import radai_memory_history
    return radai_memory_history._sample()["private_max_mib"] * 1048576


def contornos(path):
    ds=pydicom.dcmread(str(path))
    nomes={str(r.ROINumber):str(r.ROIName) for r in ds.StructureSetROISequence}
    return {nomes[str(r.ReferencedROINumber)]:[(str(c.ContourGeometricType),
            tuple(str(x) for x in c.ContourData),
            tuple(str(i.ReferencedSOPInstanceUID) for i in c.ContourImageSequence))
            for c in r.ContourSequence] for r in ds.ROIContourSequence}


class Pos(unittest.TestCase):
    def test_tc(self):
        self.comparar("CT")

    def test_rm(self):
        self.comparar("MR")

    def comparar(self, modalidade):
        with tempfile.TemporaryDirectory() as temp:
            raiz=Path(temp)
            serie=raiz/"serie"
            serie.mkdir()
            if modalidade=="MR":
                _serie_rm(str(serie))
            else:
                from test_engine import escreve_serie
                from datetime import datetime
                escreve_serie(str(serie), "FANTOMA_TC", datetime(2026,9,22,10,0), 24)
            ref=engine.load_sitk(str(serie))
            forma=tuple(reversed(ref.GetSize()))
            masks=_mascaras_de_pelve(forma)
            tags=dict(enumerate(masks,1))
            ml=np.zeros(forma,dtype=np.int16)
            for n,nome in tags.items():
                ml[masks[nome]]=n
            del masks
            resultados=[]
            lidos=[]
            for nome in ("pai","filho"):
                out=raiz/nome
                out.mkdir()
                task="total_mr" if modalidade=="MR" else "total_v3"
                saida=Saida(engine,serie,out,"RS_RadAI_teste.dcm",tasks=[task],modalidade=modalidade,
                            log=lambda s: print(s, flush=True) if "processo" in s else None)
                raw=engine.MasksCruas(ml,tags)
                args=dict(cruas={task:raw},modo="auto", volume_hu=(sitk.GetArrayViewFromImage(ref) if modalidade=="CT" else None), arcos_costais_moose=False,
                          reto_jhu=False,coronaria_rocards=False)
                t=time.monotonic()
                antes=medir_memoria()
                retorno=executar(saida,**args) if nome=="filho" else saida.full_e_oar(**args)
                print("POS",nome,"segundos",round(time.monotonic()-t,2),
                      "privados_delta_MiB",round((medir_memoria()-antes)/1048576,1),flush=True)
                resultados.append(contornos(retorno["entregue"]))
                lidos.append(sorted(k for i,k in saida.rotulos_para_cache if i==id(raw)))
                self.assertEqual(saida.gravados,["oar"])
                self.assertTrue(saida.tamanhos_publicados)
            self.assertTrue(resultados[0])
            self.assertEqual(resultados[0],resultados[1])
            self.assertEqual(lidos[0],lidos[1])


if __name__=="__main__":
    unittest.main(verbosity=2)

