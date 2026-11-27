# -*- coding: utf-8 -*-
"""Prioridade dos filhos de inferência. Usa apenas fantomas e diretórios temporários."""
from contextlib import ExitStack
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
sys.path[:0] = [str(TOOLS.parent / "app"), str(TOOLS)]
import numpy as np
import SimpleITK as sitk
import radai_config as config
import radai_devices as devices
import radai_phrases as phrases

KEY = "PRIORIDADE_BAIXA_CPU"
BELOW_NORMAL = 0x4000
HIDDEN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
WORK = re.compile(r"radai(?:_(?:moose|cads|cranio|hnlnl|jhu|nv)_|-rocards-)[a-z0-9_]+(?=[/\\]|$)", re.I)
WORKER = """
import ctypes
from ctypes import wintypes
import SimpleITK as sitk
k = ctypes.WinDLL("kernel32")
k.GetCurrentProcess.restype = wintypes.HANDLE
k.GetPriorityClass.argtypes = [wintypes.HANDLE]
k.GetPriorityClass.restype = wintypes.DWORD
img = sitk.ReadImage(ENTRADA)
registrar(priority=k.GetPriorityClass(k.GetCurrentProcess()), spacing=img.GetSpacing(),
          origin=img.GetOrigin(), direction=img.GetDirection(), size=img.GetSize(),
          threads={k: os.environ.get(k) for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                                   "ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS")},
          args=[os.path.basename(a) if a in (ENTRADA, SAIDA) else a for a in args])
gravar_saida()
"""


class LaunchCaptured(BaseException):
    """Para antes de importar os modelos ou executar uma inferência."""


class Prioridade(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.cfg = self.root / "config.txt"
        self.cfg.write_text("ESFORCO_PADRAO=extra\nDEVICE=cpu\n", encoding="utf-8")
        self.stack.enter_context(patch.dict(os.environ, {
            "RADAI_CONFIG": str(self.cfg), "RADAI_TMP": str(self.root),
        }))
        self.stack.enter_context(patch.object(tempfile, "tempdir", str(self.root)))
        os.environ.pop("OPENBLAS_NUM_THREADS", None)
        devices.limitar_openblas()

    def setting(self, value):
        ok, error = config.escrever(str(self.cfg), {KEY: value})
        self.assertTrue(ok, error)

    def test_lancador_entrega_openblas_antes_de_importar_o_motor(self):
        from radai_lancador import ambiente_do_motor
        base = dict(os.environ, OMP_NUM_THREADS="5", MKL_NUM_THREADS="4")
        base.pop("OPENBLAS_NUM_THREADS", None)
        for declarado, esperado in ((None, "1"), ("2", "2")):
            with self.subTest(declarado=declarado):
                origem = dict(base)
                if declarado is not None:
                    origem["OPENBLAS_NUM_THREADS"] = declarado
                ambiente = ambiente_do_motor(origem)
                self.assertEqual(origem.get("OPENBLAS_NUM_THREADS"), declarado)
                # O filho lê as variáveis sem importar o motor nem as bibliotecas numéricas.
                codigo = ("import json, os; print(json.dumps([os.environ.get(k) for k in "
                          "('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')]))")
                valores = subprocess.check_output([sys.executable, "-B", "-c", codigo],
                                                  env=ambiente, text=True, timeout=15)
                self.assertEqual(json.loads(valores), [esperado, "5", "4"])

    def test_openblas_respeita_escolha_e_preserva_os_outros_controles(self):
        explicito = {"OPENBLAS_NUM_THREADS":"3", "OMP_NUM_THREADS":"6", "MKL_NUM_THREADS":"4",
                     "RADAI_THREADS":"8", "CUDA_VISIBLE_DEVICES":"0"}
        ambiente = dict(explicito)
        devices.limitar_openblas(ambiente)
        self.assertEqual(ambiente, explicito)
        del ambiente["OPENBLAS_NUM_THREADS"]
        devices.limitar_openblas(ambiente)
        self.assertEqual(ambiente, dict(explicito, OPENBLAS_NUM_THREADS="1"))

    def test_painel_define_openblas_antes_de_numpy_e_o_filho_herda(self):
        codigo = """
import json, os, subprocess, sys
sys.path.insert(0, sys.argv[1])
antes = []
def captar(evento, args):
    if evento == "import" and args[0] == "numpy" and not antes:
        antes.append(os.environ.get("OPENBLAS_NUM_THREADS"))
sys.addaudithook(captar)
import radai_watcher
import numpy
filho = subprocess.check_output([sys.executable, "-B", "-c",
    "import json,os,numpy; from threadpoolctl import threadpool_info; "
    "print(json.dumps([os.getenv('OPENBLAS_NUM_THREADS'),[x['num_threads'] "
    "for x in threadpool_info() if x.get('internal_api')=='openblas']]))"], text=True)
print(json.dumps([antes,json.loads(filho),os.getenv("OMP_NUM_THREADS"),os.getenv("MKL_NUM_THREADS")]))
"""
        for especifico in (None, "3"):
            env = dict(os.environ, LOCALAPPDATA=str(self.root), APPDATA=str(self.root),
                       RADAI_REGISTRO_DIR=str(self.root), OMP_NUM_THREADS="5", MKL_NUM_THREADS="4")
            if especifico:
                env["OPENBLAS_NUM_THREADS"] = especifico
            else:
                env.pop("OPENBLAS_NUM_THREADS",None)
            res = subprocess.run([sys.executable, "-B", "-c", codigo, str(TOOLS.parent / "app")],
                                 cwd=self.root, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(res.returncode,0,res.stderr)
            escolhido = especifico or "1"
            captado, herdado, omp, mkl = json.loads(res.stdout.strip().splitlines()[-1])
            self.assertEqual(captado,[escolhido])
            self.assertEqual(herdado, [escolhido,[int(escolhido)]])
            self.assertEqual((omp,mkl), ("5","4"))

    def test_config_esta_estacao(self):
        self.assertEqual(devices.opcoes_de_prioridade_da_inferencia(), {})
        import radai_config_transferencia as transfer
        import radai_panel as panel
        fields = [KEY, "ESFORCO_PADRAO", "DEVICE"]
        # O botão Salvar das Configurações passa por esta transação conjunta.
        saved = transfer.salvar({"valores": {KEY: "1"}}, str(self.cfg), fields,
                                {KEY: "0"}, {}, "")
        self.assertTrue(saved["ok"], saved)
        self.assertEqual(saved["salvos"], [KEY])
        self.assertEqual(panel.divergencias({"em_uso": {KEY: "0"}}, {KEY: "1"}), [])
        self.assertEqual(config.chave_configurada("ESFORCO_PADRAO"), "extra")
        self.assertEqual(config.chave_configurada("DEVICE"), "cpu")
        original = self.cfg.read_bytes()
        ok, reason = config.escrever(str(self.cfg), {KEY: "prioridade-invalida"})
        self.assertFalse(ok)
        self.assertIn("CPU", reason)
        self.assertEqual(self.cfg.read_bytes(), original)
        self.assertEqual(config.chave_configurada(KEY), "1")
        exported = config.exportar(str(self.cfg), fields)
        self.assertNotIn(KEY, exported["secoes"]["configuracao"])
        exported["secoes"]["configuracao"][KEY] = "0"
        imported = config.importar(exported, ["configuracao"], str(self.cfg), fields, {})
        self.assertTrue(imported["ok"], imported)
        self.assertEqual(config.chave_configurada(KEY), "1")
        with patch.object(devices.os, "name", "posix"):
            self.assertEqual(devices.opcoes_de_prioridade_da_inferencia(), {})
        self.setting("0")
        self.assertEqual(devices.opcoes_de_prioridade_da_inferencia(), {})
        translations = phrases.construir()
        for label in (reason, "Usar prioridade de CPU abaixo do normal na segmentação",
                      "No Windows, outros programas ganham preferência quando disputam a CPU com os motores do ContourLab. A escolha vale para a próxima inferência."):
            self.assertEqual(len(translations), 11)
            self.assertTrue(all(phrases.normalizar(label) in t for t in translations.values()))

    @unittest.skipUnless(os.name == "nt", "Classe real de prioridade do Windows")
    def test_total_filho_windows_e_geometria(self):
        import test_ts_runner as ts
        import ctypes.wintypes as wt
        k = ctypes.WinDLL("kernel32")
        k.GetCurrentProcess.restype = wt.HANDLE
        k.GetPriorityClass.argtypes = [wt.HANDLE]
        k.GetPriorityClass.restype = wt.DWORD
        parent_before = k.GetPriorityClass(k.GetCurrentProcess())
        ref = ts._ref()
        ref.SetOrigin((12.5, -8.0, 7.0))
        ref.SetDirection((0, -1, 0, 1, 0, 0, 0, 0, 1))
        first = None
        for level, expected in (("0", 0x20), ("1", BELOW_NORMAL), ("0", 0x20)):
            self.setting(level)
            result, log, records, _ = ts._rodar_task(str(self.root), WORKER, ref=ref)
            self.assertIsInstance(result, dict, str(result) + "\n" + "\n".join(log[-5:]))
            data = next(d for d in records if "priority" in d)
            self.assertEqual(data.pop("priority"), expected)
            self.assertEqual(data["threads"]["OPENBLAS_NUM_THREADS"], "1")
            self.assertEqual(data["origin"], list(ref.GetOrigin()))
            self.assertEqual(data["spacing"], list(ref.GetSpacing()))
            self.assertEqual(data["direction"], list(ref.GetDirection()))
            self.assertEqual(data["size"], list(ref.GetSize()))
            self.assertEqual({name: int(mask.sum()) for name, mask in result.items()},
                             {"parotid_gland_left": 144, "parotid_gland_right": 100})
            if first is None:
                first = data, result
            else:
                self.assertEqual(first[0], data)
                for name in first[1]:
                    np.testing.assert_array_equal(first[1][name], result[name])
        self.assertEqual(k.GetPriorityClass(k.GetCurrentProcess()), parent_before)

    @unittest.skipUnless(os.name == "nt", "Flags de criação de processo no Windows")
    def test_outras_sete_rotas(self):
        import radai_moose_engine as moose
        import radai_cads_engine as cads
        import radai_cranio_engine as buti
        import radai_hnlnl_engine as hnlnl
        import radai_rectum_jhu as jhu
        import radai_rocards as roc
        import radai_nv_engine as nv
        import radai_study_modelos

        for m in (moose, cads, buti, jhu):
            self.stack.enter_context(patch.object(m, "disponivel", return_value=(True, str(self.root))))
        for m in (moose, cads):
            self.stack.enter_context(patch.object(m, "pasta_do_peso", return_value=str(self.root)))
        self.stack.enter_context(patch.object(roc, "_verificar", return_value=self.root))
        self.stack.enter_context(patch.object(radai_study_modelos, "exigir_plugin_coronarias"))
        self.stack.enter_context(patch.object(nv.radai_models, "pasta_do_modelo", return_value=self.root))
        (self.root / "configs").mkdir()
        (self.root / "configs" / "inference.json").write_text("{}", encoding="utf-8")
        mask = np.zeros((16, 20, 24), dtype=np.uint8)
        mask[4:8, 4:10, 4:12] = 1
        ref = sitk.GetImageFromArray(mask)
        source, dest = str(self.root / "in.nii"), str(self.root / "out.nii")
        sitk.WriteImage(ref, source)
        routes = [
            ("MOOSE", "Popen", 0, lambda: moose.rodar("ribs", source, dest, base=self.root)),
            ("CADS", "Popen", 0, lambda: cads.rodar(source, dest, base=self.root)),
            ("Buti", "Popen", 0, lambda: buti.rodar(source, dest, base=self.root)),
            ("HNLNL", "Popen", 0, lambda: hnlnl.inferir_em_processo_separado(str(self.root), mask)),
            ("JHU", "run", HIDDEN, lambda: jhu._segmentar_novo(ref, "cpu", sys.executable, self.root, None, set())),
            ("ROCardS", "run", HIDDEN, lambda: roc.segmentar(ref, mask, base=self.root, dispositivo="cpu")),
            ("VISTA", "run", 0, lambda: nv.rodar(source, points=[[3, 4, 5]])),
        ]
        for name, method, original_flags, run in routes:
            with self.subTest(route=name):
                seen = []
                def capture(args, **kwargs):
                    command = [WORK.sub("@diretorio", str(a)) for a in args]
                    threads = {k: v for k, v in kwargs.get("env", os.environ).items()
                               if "THREAD" in k or k == "CUDA_VISIBLE_DEVICES"}
                    extra = {}
                    if name == "ROCardS":
                        extra = json.loads((Path(args[-1]) / "solicitacao.json").read_text("utf-8"))
                    seen.append((kwargs.get("creationflags", 0), command, threads, extra))
                    raise LaunchCaptured()
                for level in ("0", "1"):
                    self.setting(level)
                    with patch.object(subprocess, method, side_effect=capture), self.assertRaises(LaunchCaptured):
                        run()
                self.assertEqual([s[0] for s in seen], [original_flags, original_flags | BELOW_NORMAL])
                self.assertEqual(seen[0][1:], seen[1][1:])
                self.assertEqual(seen[0][2].get("OPENBLAS_NUM_THREADS"), "1")
                # Isca: se uma rota deixar de aplicar a preferência, o mesmo teste detecta.
                with patch.object(devices, "opcoes_de_prioridade_da_inferencia",
                                  side_effect=lambda flags=0: {"creationflags": flags} if flags else {}):
                    with patch.object(subprocess, method, side_effect=capture), self.assertRaises(LaunchCaptured):
                        run()
                self.assertNotEqual(seen[-1][0], original_flags | BELOW_NORMAL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
