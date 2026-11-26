"""Offline startup, queue recovery and archive I/O regressions using synthetic paths."""
import os
import sys
import json
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))


class PararTeste(BaseException):
    pass


class EstacaoOciosa(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.base = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        paths = {"RADAI_TMP": "tmp", "RADAI_CALIB_DIR": "calib", "RADAI_FILA_DIR": "fila",
                 "RADAI_REGISTRO_DIR": "registro", "RADAI_CONFIG": "watcher.config",
                 "LOCALAPPDATA": "local", "APPDATA": "roaming"}
        self.stack.enter_context(patch.dict(os.environ, {k: str(self.base / v) for k,v in paths.items()}))
        for name in paths.values():
            if "." not in name:
                (self.base / name).mkdir()
        self.config = self.base / "watcher.config"
        self.config.write_text("ROOT=\nDRY_RUN=1\nLOG_DIR="+str(self.base/"log"), encoding="utf8")
        import radai_queue_state as F
        import radai_archive as A
        self.f, self.a = F, A
        for k, v in {"_CARDS": [], "_PERSISTIR":{"ligada":False,"gravacoes":0,"erro":""},
                     "_RECUPERACAO_ADIADA":False, "_GANCHOS":{}}.items():
            self.stack.enter_context(patch.object(F,k,v))

    def test_motor_ocioso_sem_inferencia_sonda_rede_ou_faxina(self):
        import radai_watcher as W
        if W._LOG_FH:
            W._LOG_FH.close()
            W._LOG_FH = None
        import radai_version as V
        forbidden = []
        def forbid(*args, **kw):
            forbidden.append("unsolicited")
            raise AssertionError("idle operation")
        for target, name in ((W, "_relatorio_de_arranque"), (V, "iniciar_consulta"),
                             (W, "limpar_temporarios"), (W, "soltar_travas_mortas_do_indice"),
                             (W, "_sondar_status_em_segundo_plano")):
            self.stack.enter_context(patch.object(target, name, side_effect=forbid))
        self.stack.enter_context(patch.object(W, "_uma_volta", side_effect=PararTeste))
        self.stack.enter_context(patch.object(W, "wlog"))
        self.stack.enter_context(patch.object(W, "migrar_config"))
        with self.assertRaises(PararTeste):
            W.worker_loop()
        with patch.object(W, "rm_no_disco", side_effect=AssertionError), patch.object(W,"ROOT",r"Z:/synthetic/offline"), patch.object(self.f, "_ler_metadados", side_effect=AssertionError):
            self.assertFalse(W.status()["ligado"])
            self.assertEqual(W._api_fora_da_fila()["n_nao_contornaveis"], 0)
            queue_route = next(r.endpoint for r in W.app.routes if r.path == "/api/fila")
            self.assertEqual(queue_route()["cards"], [])
        self.assertEqual(forbidden, [])
        import radai_cleaner as cleaner
        with patch.object(W,"quem_esta_segmentando",return_value=None), patch("radai_dedicado.sinalizacao",return_value=(False,None)), patch.object(cleaner,"gravar_em_uso",return_value=True) as marker:
            W._EM_USO_PARAR.clear()
            W._sinalizar_em_uso_uma_vez()
            self.assertEqual(marker.call_args.kwargs["procs"],[])
            self.assertEqual(marker.call_args.kwargs["saida_netstat"],"")

    def test_cinco_mil_series_restauradas_sem_testar_origens(self):
        F=self.f
        cards=[]; idx={}
        for i in range(5000):
            uid="1.2.3."+str(i)
            c=F.Q.novo_card(F.Q.SERIE,uid=uid,pasta="Z:/fake/"+str(i),origem=F.Q.RODAR_AGORA)
            cards.append(F._ao_arquivo(c)); idx[c["id"]]=F._ao_indice(c)
        Path(F.arquivo_da_fila()).parent.mkdir(exist_ok=True,parents=True)
        Path(F.arquivo_da_fila()).write_text(json.dumps({"cartoes":cards}))
        Path(F.arquivo_do_indice()).parent.mkdir(exist_ok=True,parents=True)
        Path(F.arquivo_do_indice()).write_text(json.dumps({"series":idx}))
        with patch.object(F,"_existe",side_effect=AssertionError), patch.object(F,"_achar_pasta",side_effect=AssertionError), patch.object(F,"_gravar",side_effect=AssertionError):
            r=F.restaurar_ao_abrir()
        self.assertEqual(r["voltaram"],5000)
        self.assertEqual(len(F._CARDS),5000)

    def test_retomar_restauradas_confere_so_a_selecao_e_le_o_indice_uma_vez(self):
        F = self.f
        origins = []
        for i in range(3):
            uid = "1.2.3." + str(i)
            card = F.Q.novo_card(F.Q.SERIE, uid=uid, pasta="Z:/antiga/" + str(i),
                                 origem=F.Q.RODAR_AGORA)
            card.update(_origem_restaurada=True, carga={"uid": uid, "pasta": card["pasta"]})
            F._CARDS.append(card)
            origins.append(card)
        moved = self.base / "remanejada"
        moved.mkdir()
        index = [{"uid":origins[0]["uid"], "pasta":str(moved)}]
        allowed = {c["id"]:F.assinatura_do_pedido(c) for c in origins[:2]}
        with patch.object(self.a, "ler_acervo", return_value=index) as read, patch.object(F, "_existe", return_value=False) as exist:
            F._validar_restauradas(allowed)
        self.assertEqual(exist.call_count, 2)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(F._CARDS[0]["pasta"], str(moved))
        self.assertEqual(F._CARDS[1]["estado"], F.Q.FALHOU)
        self.assertTrue(F._CARDS[2]["_origem_restaurada"])

    def test_metadados_remotos_apenas_sob_pedido_e_sem_sobrescrever_erro(self):
        F=self.f
        with patch.object(self.a,"_e_rede",return_value=True), patch.object(F,"_ler_metadados",side_effect=AssertionError):
            self.assertEqual(F.restaurar_ao_abrir(),{"adiada":True})
            self.assertFalse(F._gravar())
        with patch.object(F,"_ler_metadados",side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                F.restaurar_quando_solicitada()
        self.assertFalse(F._gravar())
        with patch.object(F,"_ler_metadados",return_value={}) as read:
            F.restaurar_quando_solicitada()
            F.restaurar_quando_solicitada()
            self.assertEqual(read.call_count,1)
        self.assertTrue(F._PERSISTIR["ligada"])

    def test_fechar_previa_do_vigia_interrompe_a_varredura(self):
        import asyncio
        import radai_watcher as W
        if W._LOG_FH:
            W._LOG_FH.close()
            W._LOG_FH = None
        entrou = threading.Event()
        encerrado = threading.Event()
        def scan(*, parar):
            entrou.set()
            try:
                while not parar():
                    time.sleep(0.005)
                return {}, []
            finally:
                encerrado.set()
        class Desconectada:
            async def is_disconnected(self):
                return entrou.is_set()
        with patch.object(W, "ROOT", str(self.base)), patch.object(W, "scan_root", side_effect=scan):
            asyncio.run(W.api_plano(Desconectada()))
        self.assertTrue(entrou.is_set())
        self.assertTrue(encerrado.wait(1))

    def test_cancelar_em_pasta_com_muitos_arquivos_poupa_o_cache(self):
        import radai_watcher as W
        if W._LOG_FH:
            W._LOG_FH.close()
            W._LOG_FH = None
        raiz = self.base / "exames"
        raiz.mkdir()
        for i in range(48):
            (raiz / str(i)).touch()
        chamadas = 0
        def parar():
            nonlocal chamadas
            chamadas += 1
            return chamadas >= 5
        with patch.object(W, "cache_load", return_value={}), patch.object(W, "cache_save") as salvar:
            self.assertEqual(W.scan_root([str(raiz)], parar=parar), ({}, []))
        salvar.assert_not_called()
        self.assertLess(chamadas, 10)

    def test_previa_do_vigia_reutiliza_gpu_sem_iniciar_diagnostico(self):
        import radai_watcher as W
        import radai_review as R
        import radai_cleaner as C
        import radai_arranque as A
        with ExitStack() as stack:
            stack.enter_context(patch.object(W, "ROOT", str(self.base)))
            stack.enter_context(patch.object(W, "scan_root", return_value=({}, [])))
            stack.enter_context(patch.dict(W.CFG, DEVICE="auto"))
            stack.enter_context(patch.dict(A.ULTIMO, torch={"disponivel": True}))
            stack.enter_context(patch.object(R, "_ULTIMOS_GANHOS", ("gpu", [{"chave":"energia"}])))
            stack.enter_context(patch.object(C, "ganhos_de_velocidade", side_effect=AssertionError))
            stack.enter_context(patch.dict(sys.modules, {"engine":None, "torch":None}))
            plano = W.plano_de_execucao()
            self.assertFalse(plano["erro"])
            self.assertEqual(plano["device"], "gpu")
            self.assertEqual(plano["estacao"]["ganhos"], [{"chave":"energia"}])
            self.assertEqual(plano["aviso"], R.FRASE_DA_FRONTEIRA)
            with patch.dict(A.ULTIMO, torch={}):
                self.assertEqual(W.plano_de_execucao()["device"], "GPU / CPU")

    def test_sondas_bloqueadas_nao_se_multiplicam_nem_seguem_apos_prazo(self):
        A=self.a
        gate=threading.Event()
        entered=[]
        def slow(path,rs):
            entered.append(path)
            gate.wait(5)
            return "sem_pasta"
        regs=[{"uid":str(i),"pasta":str(self.base/str(i))} for i in range(100)]
        with patch.object(A,"_estado_no_disco",side_effect=slow):
            try:
                A._sondar_acervo(regs,[],.12,self.base/"cursor")
                A._sondar_acervo(regs,[],.08,self.base/"cursor")
                self.assertTrue(0<len(entered)<=3)
                initial=len(entered)
            finally:
                gate.set()
                for t in threading.enumerate():
                    if t.name=="radai-sonda-acervo":
                        t.join(3)
                        self.assertFalse(t.is_alive())
            self.assertEqual(len(entered),initial)


if __name__=="__main__":
    unittest.main(verbosity=2)
