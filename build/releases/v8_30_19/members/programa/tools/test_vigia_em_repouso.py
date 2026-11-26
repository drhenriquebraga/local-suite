"""Espera sem temporizador e cancelamento do controle real do Vigia e da fila."""
from contextlib import ExitStack
from pathlib import Path
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))


class EsperaObservavel(threading.Event):
    def __init__(self):
        super().__init__()
        self.entrou = threading.Event()
        self.prazos = []

    def wait(self, timeout=None):
        self.prazos.append(timeout)
        self.entrou.set()
        return super().wait(timeout)


class Repouso(unittest.TestCase):
    def setUp(self):
        self.guardas = ExitStack()
        self.addCleanup(self.guardas.close)
        self.raiz = Path(self.guardas.enter_context(tempfile.TemporaryDirectory()))
        cfg = self.raiz / "radai.config"
        cfg.write_text("ROOT=" + str(self.raiz) + "\nDRY_RUN=1\nLOG_DIR=" + str(self.raiz / "logs"), "utf-8")
        self.guardas.enter_context(patch.dict(os.environ, LOCALAPPDATA=str(self.raiz),
            APPDATA=str(self.raiz), RADAI_TMP=str(self.raiz), RADAI_CONFIG=str(cfg),
            RADAI_FILA_DIR=str(self.raiz), RADAI_REGISTRO_DIR=str(self.raiz), RADAI_CALIB_DIR=str(self.raiz)))
        import radai_watcher as w
        self.w = w
        self.guardas.enter_context(patch.dict(w.STATE, ligado=False, overnight=False, paused=False,
                                    current=None, n_queue=0, adiadas=0, ambiente_erro=""))
        self.guardas.enter_context(patch.dict(w.STATE["arranque"], fila_liberada=True))
        self.acao = self.trocar("_ACAO_DO_OPERADOR", EsperaObservavel())
        for nome in ("ENCERRANDO", "RECARREGAR", "RESCAN_NOW", "_ACORDAR_VIGIA", "_VIGIA_EM_REPOUSO"):
            self.trocar(nome, threading.Event())
        self.trocar("ROOT", str(self.raiz))
        self.trocar("CACHE_PATH", self.raiz / "indice.json")
        self.trocar("CFG_PATH", cfg)
        self.trocar("STATUS_DIR", "")
        self.trocar("_AVISOS_ATIVOS", None)
        self.trocar("VARREDURA_DO_TURNO", [None])
        self.trocar("_LEITURA_DIRETA_DO_TURNO", [None])
        self.trocar("_STATUS_EM_CURSO", set())
        self.trocar("_STATUS_SONDA_ATIVA", None)
        self.trocar("wlog", Mock())
        self.trocar("migrar_config", Mock())
        self.trocar("_fila_da_estacao", lambda nome, *a, padrao=None: padrao)
        self.trocar("preparar_primeiro_processamento", Mock())
        self.trocar("abrir_turno_das_assinaturas", Mock())
        self.trocar("_pre_carga", Mock())
        self.periodico = self.trocar("_status_periodico", Mock())
        self.volta = self.trocar("_uma_volta", Mock(wraps=w._uma_volta))
        self.trocar("process_series", Mock(side_effect=AssertionError("nenhuma inferência no ensaio")))
        if w._LOG_FH:
            w._LOG_FH.close()
            w._LOG_FH = None

    def trocar(self, nome, valor):
        return self.guardas.enter_context(patch.object(self.w,nome,valor))

    def esperar(self, pronto, segundos=4):
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            if pronto():
                return
            time.sleep(.01)
        self.fail("o evento esperado não chegou")

    def iniciar(self):
        w = self.w
        worker = threading.Thread(target=w.worker_loop, daemon=True)
        worker.start()
        def fechar():
            w.ENCERRANDO.set()
            w._interromper_leitura_do_turno(w.VARREDURA_DO_TURNO[0])
            w._acordar_controle_vigia()
            worker.join(3)
            self.assertFalse(worker.is_alive())
        self.addCleanup(fechar)
        self.assertTrue(self.acao.entrou.wait(4))
        return worker

    def test_repouso_sem_timeout_mesmo_quando_ha_notificacao_de_arquivo_antiga(self):
        w = self.w
        self.iniciar()
        w._ACORDAR_VIGIA.set()
        self.assertEqual(self.acao.prazos, [None])
        time.sleep(.15)
        self.assertEqual(self.volta.call_count, 1)
        self.periodico.assert_not_called()
        w.preparar_primeiro_processamento.assert_not_called()
        self.acao.entrou.clear()
        with patch.object(w, "recarregar_cfg", return_value=[]):
            w.pedir_recarga()
            self.assertTrue(self.acao.entrou.wait(2))
        self.assertEqual(self.volta.call_count, 2)
        self.assertEqual(self.acao.prazos, [None, None])
        self.assertFalse(w.recarga_pendente())
        self.assertTrue(w._VIGIA_EM_REPOUSO.is_set())

    def test_pause_da_fila_interrompe_descida_e_retomada_acorda_o_turno(self):
        w = self.w
        rodando, cancelada = threading.Event(), threading.Event()
        def escanear(*args, **kwargs):
            leitura = w._LEITURA_DIRETA_DO_TURNO[0]
            rodando.set()
            if not leitura.evento.wait(4):
                self.fail("a pausa deveria interromper a descida em curso")
            cancelada.set()
            return {}, []
        self.trocar("_primeira_descida", Mock(side_effect=escanear))
        self.iniciar()
        w.vigia_ligar()
        self.assertTrue(rodando.wait(4))
        pausar = next(r.endpoint for r in w.app.routes if r.path == "/api/pipeline/pausar")
        self.assertTrue(pausar()["ok"])
        self.assertTrue(cancelada.wait(1))
        self.esperar(lambda: w._VIGIA_EM_REPOUSO.is_set() and w._AVISOS_ATIVOS is None)
        congelado = self.volta.call_count, self.periodico.call_count
        time.sleep(.12)
        self.assertEqual((self.volta.call_count, self.periodico.call_count), congelado)
        w.process_series.assert_not_called()
        rodando.clear()
        cancelada.clear()
        retomar = next(r.endpoint for r in w.app.routes if r.path == "/api/pipeline/iniciar")
        retomar()
        self.assertTrue(rodando.wait(4))
        w.vigia_desligar()
        self.assertTrue(cancelada.wait(1))
        self.esperar(lambda: w._VIGIA_EM_REPOUSO.is_set() and w._AVISOS_ATIVOS is None)

    def test_pausa_entre_inventario_e_fila_interrompe_leitura_dos_marcadores(self):
        w = self.w
        series = {str(n):{"uid":str(n), "dir":str(self.raiz), "date":"", "count":10}
                  for n in range(100)}
        self.trocar("_primeira_descida", Mock(return_value=(series, [])))
        self.trocar("soltar_travas_mortas_ao_abrir", Mock())
        self.trocar("escolher_simulacao", Mock(return_value={}))
        esperando = threading.Event()
        chamadas = []
        def ler(pasta, uid):
            chamadas.append(uid)
            esperando.set()
            if not w._LEITURA_DIRETA_DO_TURNO[0].evento.wait(3):
                self.fail("a escolha da fila não recebeu cancelamento")
            return ""
        self.trocar("ler_decisao", Mock(side_effect=ler))
        self.iniciar()
        w.vigia_ligar()
        self.assertTrue(esperando.wait(2))
        w.pause()
        self.esperar(lambda: w._VIGIA_EM_REPOUSO.is_set() and w._AVISOS_ATIVOS is None)
        self.assertEqual(len(chamadas), 1)
        w.process_series.assert_not_called()

    def test_sonda_status_em_andamento_respeita_pausa(self):
        w = self.w
        self.trocar("STATUS_DIR",str(self.raiz/"frota"))
        w.STATE["ligado"] = True
        entrou, saiu = threading.Event(), threading.Event()
        def sonda(geracao, parar):
            entrou.set()
            self.esperar(parar)
            saiu.set()
        self.trocar("conferir_status_dir",Mock(side_effect=sonda))
        w._sondar_status_em_segundo_plano()
        self.assertTrue(entrou.wait(1))
        w.pause()
        self.assertTrue(saiu.wait(1))
        self.esperar(lambda: not w._STATUS_EM_CURSO)
        w._sondar_status_em_segundo_plano()
        self.assertEqual(w.conferir_status_dir.call_count, 1)

    def test_pausa_interrompe_workers_da_precarga_sem_ler_os_demais_arquivos(self):
        import engine
        import radai_archive as acervo
        import radai_batch as lote
        pre = acervo.PreCarga()
        serie = {"uid":"1.2.3", "dir":str(self.raiz)}
        arquivos = [self.raiz/("f%d" % i) for i in range(40)]
        for f in arquivos:
            f.write_bytes(b"teste")
        iniciou = threading.Event()
        ativos = []
        trava = threading.Lock()
        def copiar(origem, destino):
            with trava:
                ativos.append(origem)
                if len(ativos) == 4:
                    iniciou.set()
            if not pre.atual["leitura"].evento.wait(3):
                raise AssertionError("a pausa não cancelou a cópia especulativa")
            raise InterruptedError("cancelamento simulado durante cópia")
        with ExitStack() as g:
            g.enter_context(patch.object(acervo, "pasta_temporaria_local",return_value=str(self.raiz)))
            g.enter_context(patch.object(acervo, "_e_rede",return_value=False))
            g.enter_context(patch.object(acervo, "em_pasta_sincronizada",return_value=(False,"")))
            g.enter_context(patch.object(acervo, "conferir_espaco_da_serie",return_value=(1,1000)))
            g.enter_context(patch.object(engine.shutil,"copy",side_effect=copiar))
            g.enter_context(patch.object(lote,"_pre_carga",pre))
            pre.iniciar("lote",serie,lambda s: arquivos,engine.copy_sorted,0)
            self.assertTrue(iniciou.wait(3))
            item = pre.atual
            if os.name == "nt":
                self.assertGreaterEqual(len(item["leitura"]._handles), 5)
            lote.pausar(True)
            try:
                self.assertTrue(item["fim"].wait(2))
                self.assertIsNone(pre.atual)
                self.assertGreaterEqual(len(ativos),4)
                self.assertLessEqual(len(ativos),8)
                self.assertFalse(list(self.raiz.glob("radai_precarga_*")))
                pre.iniciar("lote",serie,Mock(),Mock(),0,permitido=lambda:False)
                self.assertIsNone(pre.atual)
            finally:
                lote.pausar(False)
        # A cópia em primeiro plano segue disponível depois da interrupção.
        normal = Mock(return_value="concluida")
        self.assertEqual(pre.copiar("lote",serie,arquivos,str(self.raiz/"saida"),normal), "concluida")

    def test_pedido_de_energia_segue_trabalho_real(self):
        import radai_batch
        w = self.w
        with patch.object(radai_batch,"atividade",return_value={"rodando":False,"fila":True}):
            self.assertFalse(w.fila_ocupada())
            w.STATE.update(ligado=True,overnight=True)
            self.assertTrue(w.fila_ocupada())
            w.pause()
            self.assertFalse(w.fila_ocupada())
            w.STATE["current"] = {"uid":"1.2.3"}
            self.assertTrue(w.fila_ocupada())
            w.STATE["current"] = None
            self.assertFalse(w.fila_ocupada())


if __name__ == "__main__":
    unittest.main(verbosity=2)
