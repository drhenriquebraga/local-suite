"""Regressão do executor da fila. Dados artificiais e GPU injetada."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import numpy as np
import SimpleITK as sitk
import engine
import radai_rotas as rt
import radai_output
import radai_devices
import radai_dedicado


def placa(i=0, livre=10000):
    return dict(indice=i, placa="teste", uuid="gpu_%d"%i, modo="gpu", driver="driver-a",
                precisa_tudo_mb=5000, precisa_rede_mb=2000, margem_mb=2000,
                margem_rede_mb=1000, vram_livre_mb=livre, capacidade="8.6")


MEM = dict(total_mb=32768, livre_mb=22000, commit_total_mb=50000, commit_livre_mb=30000)


class Rotas(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "rotas.sqlite3"
        self.patch = patch.object(rt, "arquivo", return_value=self.path)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.livro = rt.Livro(self.path, "teste", boot="boot", processo=lambda pid:"pid")
        self.ref = sitk.GetImageFromArray(np.arange(125, dtype=np.int16).reshape(5,5,5))

    def abrir(self, uid, task="total", planos=None):
        return self.livro.admitir(uid,task,rt.caminhos([placa()] if planos is None else planos),MEM,900)

    def rastros(self):
        with self.livro.transacao() as db:
            return [dict(row) for row in db.execute("select * from rota order by inicio")]

    def test_r1_recuo_no_executor_com_receita_congelada(self):
        jid = engine._job_new()
        self.addCleanup(engine._job_del, jid)
        engine.registrar_serie(jid,"1.2.1")
        calculos = []
        fantoma = np.arange(32, dtype=np.uint8).reshape(4,4,2)
        @engine._com_rotas
        def filho(ref, task, device, jid, **receita):
            estado = engine._rota_em_uso.get()
            plano = engine._admitir_rota(estado,ref,task,None,None,ref,[placa()],{},jid)
            calculos.append((task,plano["degrau"],receita))
            if task == "breasts" and plano["degrau"] == "D1":
                raise engine.FalhaDaTask(task,codigo=1,frase="CUDA out of memory")
            return fantoma > 8
        entrega = {}
        with patch.object(engine,"memoria_e_commit",return_value=MEM):
            for task in ("total","breasts"):
                entrega[task] = filho(self.ref,task,"gpu",jid,base_tc_mm="1.5",suavizar=True)
        self.assertEqual([(t,d) for t,d,_ in calculos],
                         [("total","D1"),("breasts","D1"),("breasts","D2")])
        self.assertEqual(calculos[1][2],calculos[2][2])
        np.testing.assert_array_equal(entrega["breasts"],fantoma>8)

    def test_runner_real_dois_processos_e_retomada(self):
        import contextlib
        import radai_cache_tasks as cache
        raiz = Path(self.temp.name)
        fake = raiz / "inferir.py"
        fake.write_text("""import os,sys
import SimpleITK as sitk
from pathlib import Path
log=Path(__file__).with_name('chamadas.txt')
with log.open('a') as f:
    f.write('%s/%s\\n'%(os.environ.get('CUDA_VISIBLE_DEVICES'),os.environ.get('RADAI_RESULTADOS_NA_CPU')))
if os.environ.get('RADAI_RESULTADOS_NA_CPU') != '1':
    print('CUDA out of memory',flush=True)
    sys.exit(1)
ref=sitk.ReadImage(sys.argv[sys.argv.index('-i')+1])
sitk.WriteImage(sitk.Cast(ref>9,sitk.sitkUInt8),sys.argv[sys.argv.index('-o')+1])
""",encoding="utf-8")
        with contextlib.ExitStack() as s:
            for chave,valor in dict(TS_CMD=[sys.executable, str(fake)],
                                    TS_CLASS_MAP={"breasts":{1:"breast_left"}}).items():
                s.enter_context(patch.object(engine,chave,valor))
            for chave,valor in dict(_vram_por_placa={"placas":[{"indice":0,"nome":"teste",
                                          "total_mb":20000,"livre_mb":19000,"uuid":"id","driver":"a",
                                          "capacidade":"8.6"}]},
                                     memoria_e_commit=MEM, conferir_tasks=None,
                                     conferir_volume_contornavel=None,
                                     _contexto_do_cache=None,_plano_de_ram=None).items():
                s.enter_context(patch.object(engine,chave,return_value=valor))
            s.enter_context(patch.object(cache,"conferir_pasta",return_value=(True,"")))
            s.enter_context(patch.object(cache,"impressao_dos_pesos",return_value="fixture"))
            def rodar(raw):
                j=engine._job_new()
                try:
                    engine.registrar_serie(j,"1.2.99")
                    engine.run_ts_task(self.ref,"breasts","gpu",j,timeout_s=20,cruas=raw,
                                       suavizar=False,recorte_no_corpo=False)
                finally:
                    engine._job_del(j)
            original,retomada={},{}
            rodar(original)
            rodar(retomada)
            self.assertEqual((raiz/"chamadas.txt").read_text().splitlines(),["0/None","0/1"])
            np.testing.assert_array_equal(original["breasts"]["breast_left"],retomada["breasts"]["breast_left"])
            np.testing.assert_array_equal(original["breasts"]["breast_left"],sitk.GetArrayFromImage(self.ref)>9)
            self.assertEqual([x["motivo"] for x in self.rastros()],["oom_gpu","concluida"])

    def test_r2_reabertura_e_caminho_fisico(self):
        a,p = self.abrir("1.2.2")
        self.livro.terminar(a,"oom_gpu")
        self.livro = rt.Livro(self.path,"teste",boot="boot",processo=lambda pid:"pid")
        ident,p2 = self.abrir("1.2.2",planos=[placa(1),placa(0)])
        self.assertNotEqual((rt._hardware(p2),p2["modo"]),(rt._hardware(p),p["modo"]))

    def test_r3_pausa_nao_condena(self):
        a,p = self.abrir("1.2.3")
        self.livro.terminar(a,"pausa")
        _,nova = self.abrir("1.2.3")
        self.assertEqual(nova,p)

    def test_r4_queda_motor_energia_e_dono_vivo(self):
        self.abrir("1.2.4")
        self.assertFalse(self.livro.retomar("1.2.4"))
        self.livro.processo=lambda pid:""
        self.assertTrue(self.livro.retomar("1.2.4"))
        self.assertEqual(self.rastros()[-1]["motivo"],"motor")
        ident,plano=self.abrir("1.2.4")
        self.assertEqual(plano["degrau"],"D2")
        self.livro.boot="reiniciou"
        self.assertTrue(self.livro.retomar("1.2.4"))
        self.assertEqual(self.rastros()[-1]["motivo"],"reinicio")
        _, retoma=self.abrir("1.2.4")
        self.assertEqual(retoma["degrau"],"D2")

    def test_r5_aprendizado_driver_prazo_e_esquecer(self):
        for uid in ("1.2.51","1.2.52"):
            ident,plano=self.abrir(uid)
            self.livro.terminar(ident,"oom_gpu")
        ident,plano=self.abrir("1.2.53")
        self.assertEqual(plano["degrau"],"D2")
        self.livro.terminar(ident,"concluida")
        ident,p=self.abrir("1.2.54",planos=[dict(placa(), driver="novo")])
        self.assertEqual(p["degrau"],"D1")
        self.livro.terminar(ident,"concluida")
        self.assertEqual(len(rt.diagnostico()),1)
        self.assertFalse(rt.diagnostico(esquecer=True))
        ident,p=self.abrir("1.2.55")
        self.assertEqual(p["degrau"],"D1")
        self.livro.terminar(ident,"concluida")
        self.assertEqual(self.abrir("1.2.51")[1]["degrau"],"D2")

    def test_reserva_pos_usa_grade_original(self):
        from unittest.mock import Mock
        livro = Mock()
        livro.admitir.return_value = ("t", {"indice":None, "modo":"cpu", "degrau":"D4"})
        estado = {"livro":livro, "uid":"1.2.99", "task":"breasts"}
        grade_completa = Mock()
        grade_completa.GetSize.return_value = (512,512,256)
        with patch.object(engine,"estimativa_de_ram",return_value={"precisa_mb":200}), patch.object(engine,"memoria_e_commit",return_value=MEM):
            engine._admitir_rota(estado,self.ref,"breasts",None,None,grade_completa,[],{},"inativo")
        self.assertEqual(livro.admitir.call_args.args[-1],200+768)

    def test_pressao_libera_ao_baixar_de_80_sem_timer(self):
        p = rt.PressaoDeMemoria()
        cheio = dict(MEM, commit_livre_mb=2000)
        self.assertFalse(p.avaliar(cheio, 0))
        self.assertTrue(p.avaliar(cheio, 6))
        self.assertTrue(p.avaliar(dict(MEM, commit_livre_mb=7500), 7))
        self.assertFalse(p.avaliar(MEM, 8))
        self.assertTrue(p.avaliar(dict(MEM, livre_mb=2048), 9))

    def test_r6_segunda_placa_vitrea_commit(self):
        self.abrir("1.2.61")
        with self.assertRaises(rt.Ocupada):
            self.abrir("1.2.62",planos=[placa(),placa(1,livre=2000)])
        with self.assertRaises(rt.Ocupada):
            self.livro.admitir("1.2.62","total",rt.caminhos([placa(1)]),
                              dict(MEM,commit_livre_mb=1500),900)
        _,p=self.abrir("1.2.62",planos=[placa(),placa(1)])
        self.assertEqual(p["indice"],1)
        self.assertEqual([r["na_maquina"] for r in self.rastros()],[1,2])

    def test_piloto_d0_falha_enquanto_outra_serie_termina(self):
        primeira, p0 = self.livro.admitir("1.2.71", "total",
            rt.caminhos([placa(0), placa(1)], piloto=0), MEM, 900)
        segunda, p1 = self.livro.admitir("1.2.72", "total",
            rt.caminhos([placa(0), placa(1)], piloto=1), MEM, 900)
        self.assertEqual((p0["degrau"], p0["indice"], p1["degrau"], p1["indice"]), ("D0",0,"D0",1))
        self.livro.terminar(segunda, "oom_gpu")
        with self.assertRaises(rt.AguardarSozinha):
            self.livro.admitir("1.2.72", "total", rt.caminhos([placa(0),placa(1)],piloto=1),MEM,900)
        self.livro.terminar(primeira, "concluida")
        _, retoma=self.livro.admitir("1.2.72","total", rt.caminhos([placa(0),placa(1)],piloto=1),MEM,900)
        self.assertEqual((retoma["degrau"], retoma["indice"]), ("D1", 1))

    def test_r7_promocao_perdeu_dono(self):
        raiz=Path(self.temp.name)
        antes,src=raiz/"out.dcm",raiz/"draft.dcm"
        antes.write_bytes(b"primeira entrega")
        src.write_bytes(b"novo estudo")
        sd=radai_output.Saida(None,raiz,raiz,antes.name)
        def perdeu():
            raise RuntimeError("reserva mudou durante a cópia")
        sd.conferir_promocao=perdeu
        with self.assertRaisesRegex(RuntimeError,"reserva"):
            sd._gravar_arquivo(src, str(antes))
        self.assertEqual(antes.read_bytes(),b"primeira entrega")
        self.assertEqual(len(list(raiz.glob("*.dcm"))),2)

    def test_checkpoint_distingue_grade_e_crc(self):
        mapa=rt.caminho_do_mapa("1.2.8","b"*64)
        arr=np.arange(60,dtype=np.int16).reshape(3,4,5)
        self.assertTrue(rt.guardar_mapa(mapa,arr,False))
        np.testing.assert_array_equal(rt.ler_mapa(mapa,arr.shape)[0],arr)
        self.assertIsNone(rt.ler_mapa(mapa,(2,4,5)))
        mapa.write_bytes(mapa.read_bytes()[:32])
        self.assertIsNone(rt.ler_mapa(mapa,arr.shape))
        rt.encerrar_mapas("1.2.8")
        self.assertFalse(mapa.exists())

    @unittest.skipUnless(os.name == "nt","prioridade do Windows")
    def test_dedicado_so_muda_classe_do_filho(self):
        import radai_config
        with patch.object(radai_dedicado,"sinalizacao",return_value=(True,None)):
            self.assertEqual(radai_devices.opcoes_de_prioridade_da_inferencia(0x8000000),
                             {"creationflags":0x8008000})
        with patch.object(radai_dedicado,"sinalizacao",return_value=(False,None)), patch.object(
                radai_config,"chave_configurada",return_value="1"):
            self.assertEqual(radai_devices.opcoes_de_prioridade_da_inferencia(),
                             {"creationflags":0x4000})


if __name__ == "__main__":
    unittest.main(verbosity=2)

