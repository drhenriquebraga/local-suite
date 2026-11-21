# -*- coding: utf-8 -*-
from contextlib import contextmanager

import os
import re
import sys
import threading
import time
import traceback

MARCA = "RADAI|"
PULSO_PADRAO_S = 15.0
_MB = 1024 * 1024

_SAIR = os._exit

_ESTADO = {"dataset": None, "redes": 0}
_TRAVA_SAIDA = threading.Lock()


def _linha(texto):
    try:
        with _TRAVA_SAIDA:
            sys.stdout.write(texto + "\n")
            sys.stdout.flush()
    except Exception:
        pass


def _saida_sem_buffer():
    for canal in (sys.stdout, sys.stderr):
        try:
            canal.reconfigure(encoding="utf-8", errors="replace",
                              line_buffering=True)
        except Exception:
            try:
                canal.reconfigure(line_buffering=True)
            except Exception:
                pass


_PMC = None


def _rss_mb():
    return _memoria_do_processo()[0]


def versao_do_pacote(dist, mod=None):
    try:
        from importlib import metadata
        return metadata.version(dist)
    except Exception:
        pass
    v = getattr(mod, "__version__", None) if mod is not None else None
    return str(v) if v else u"?"


def pico_do_processo_mb():
    if os.name != "nt":
        return None, None
    try:
        import ctypes
        from ctypes import wintypes
        _memoria_do_processo()
        if _PMC is None:
            return None, None
        PMC, f, k32 = _PMC
        p = PMC()
        p.cb = ctypes.sizeof(PMC)
        if not f(k32.GetCurrentProcess(), ctypes.byref(p), p.cb):
            return None, None
        commit = int(p.PeakPagefileUsage // _MB) or None
        ws = int(p.PeakWorkingSetSize // _MB) or None
        return commit, ws
    except Exception:
        return None, None


def _memoria_do_processo():
    global _PMC
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            if _PMC is None:
                class PMC(ctypes.Structure):
                    _fields_ = [("cb", wintypes.DWORD),
                                ("PageFaultCount", wintypes.DWORD),
                                ("PeakWorkingSetSize", ctypes.c_size_t),
                                ("WorkingSetSize", ctypes.c_size_t),
                                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                                ("PagefileUsage", ctypes.c_size_t),
                                ("PeakPagefileUsage", ctypes.c_size_t)]
                k32 = ctypes.WinDLL("kernel32")
                k32.GetCurrentProcess.restype = wintypes.HANDLE
                try:
                    f = k32.K32GetProcessMemoryInfo
                except AttributeError:
                    f = ctypes.WinDLL("psapi").GetProcessMemoryInfo
                f.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC),
                              wintypes.DWORD]
                f.restype = wintypes.BOOL
                _PMC = (PMC, f, k32)
            PMC, f, k32 = _PMC
            p = PMC()
            p.cb = ctypes.sizeof(PMC)
            if f(k32.GetCurrentProcess(), ctypes.byref(p), p.cb):
                return (int(p.WorkingSetSize // _MB), int(p.PageFaultCount))
            return None, None
        except Exception:
            return None, None
    try:
        with open("/proc/self/statm") as fh:
            paginas = int(fh.read().split()[1])
        return int(paginas * os.sysconf("SC_PAGE_SIZE") // _MB), None
    except Exception:
        return None, None


def amostra():
    campos = ["parte=?"]
    if _ESTADO.get("dataset"):
        campos.append("dataset=%s" % _ESTADO["dataset"])
    t = sys.modules.get("torch")
    if t is not None:
        try:
            cuda = t.cuda
            if cuda.is_initialized():
                livre, total = cuda.mem_get_info()
                campos.append("vram_mb=%d/%d" % ((total - livre) // _MB,
                                                 total // _MB))
                campos.append("torch_mb=%d/%d"
                              % (cuda.memory_allocated() // _MB,
                                 cuda.memory_reserved() // _MB))
        except Exception as e:
            campos.append("vram_mb=?(%s)" % type(e).__name__)
    rss, pf = _memoria_do_processo()
    campos.append("rss_mb=%s" % (rss if rss is not None else "?"))
    campos.append("pf=%s" % (pf if pf is not None else "?"))
    return "|".join(campos)


def _pulsar(intervalo_s, parar):
    disse_erro = False
    while not parar.wait(intervalo_s):
        try:
            _linha(MARCA + "pulso|" + amostra())
        except Exception as e:
            try:
                if not disse_erro:
                    disse_erro = True
                    _linha(MARCA + "pulso|erro=%s: %s" % (type(e).__name__, e))
                else:
                    _linha(MARCA + "pulso|erro=repetido")
            except Exception:
                pass


def _intervalo_do_pulso():
    bruto = (os.environ.get("RADAI_PULSO_S") or "").strip()
    if not bruto:
        return PULSO_PADRAO_S
    try:
        v = float(bruto.replace(",", "."))
        return v if v > 0 else PULSO_PADRAO_S
    except ValueError:
        _linha(MARCA + "aviso|RADAI_PULSO_S=%r nao e numero; usando %.0f s"
               % (bruto, PULSO_PADRAO_S))
        return PULSO_PADRAO_S


def _ligada(valor):
    return str(valor or "").strip().lower() in ("1", "sim", "true", "yes",
                                                "on")



def _remendar_predicao_sequencial(mod):
    """Usa a exportação sequencial da biblioteca nas chamadas simples da suíte."""
    from functools import wraps
    from inspect import signature
    cls = mod.nnUNetPredictor
    original = cls.predict_from_files
    if getattr(original, "_radai_sequencial", False):
        return
    sequencial = getattr(cls, "predict_from_files_sequential", None)
    sig = signature(original)
    nomes = {"self", "list_of_lists_or_source_folder", "output_folder_or_list_of_truncated_output_files",
             "save_probabilities", "overwrite", "num_processes_preprocessing",
             "num_processes_segmentation_export", "folder_with_segs_from_prev_stage", "num_parts", "part_id"}
    conhecidos = set(sig.parameters)
    if sequencial is None or conhecidos not in (nomes, nomes | {"use_cropped_logits_resampling"}):
        raise ValueError("assinatura do nnU-Net sem equivalência sequencial confirmada")

    @wraps(original)
    def predict_from_files(self, *args, **kwargs):
        a = sig.bind(self, *args, **kwargs)
        a.apply_defaults()
        k = a.arguments
        destino = k["output_folder_or_list_of_truncated_output_files"]
        if (k["save_probabilities"] or k.get("use_cropped_logits_resampling")
                or k["num_parts"] != 1 or k["part_id"] != 0
                or destino is None or k["folder_with_segs_from_prev_stage"] is not None
                or self.configuration_manager.previous_stage_name is not None):
            return original(self, *args, **kwargs)
        pasta = destino if isinstance(destino, str) else None
        if isinstance(destino, list) and destino:
            pasta = os.path.dirname(destino[0])
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        return sequencial(self, k["list_of_lists_or_source_folder"], destino,
                          save_probabilities=False, overwrite=k["overwrite"],
                          folder_with_segs_from_prev_stage=None)

    predict_from_files._radai_sequencial = True
    cls.predict_from_files = predict_from_files


def _remendar_localizador(pasta, chave, modulo=None):
    """O python_api importa este símbolo a cada chamada. Só o mapa auxiliar é compartilhado."""
    import hashlib
    import inspect
    import json
    from functools import wraps
    import nibabel as nib
    import numpy as np
    if modulo is None:
        import totalsegmentator.nnunet as modulo
    original = modulo.nnUNet_predict_image
    if getattr(original, "_radai_localizador", False):
        return
    sig = inspect.signature(original)
    versao = versao_do_pacote("TotalSegmentator")

    @wraps(original)
    def prever(*args, **kwargs):
        k = dict(sig.bind(*args, **kwargs).arguments)
        tarefa = k.get("task_id")
        gravar_entrega = k.get("file_out") is not None
        craniofacial = ((os.environ.get("RADAI_ENSAIO_T4") == "1"
                         or os.environ.get("RADAI_REUSAR_CRANIOFACIAL") == "1")
                        and k.get("task_name") == "craniofacial_structures"
                        and tarefa == 115)
        localizador = (not gravar_entrega and isinstance(tarefa, int)
                       and tarefa in (297, 298, 300, 852) and k.get("crop") is None)
        if (not (craniofacial or localizador) or k.get("cascade") is not None
                or k.get("statistics") or k.get("save_probabilities") or k.get("preview")
                or k.get("vertebrae_body_mask") is not None or k.get("remove_outside_mask") is not None):
            return original(*args, **kwargs)
        if craniofacial:
            chamada = sig.bind(*args, **kwargs)
            chamada.apply_defaults()
            k = dict(chamada.arguments)
            crop = k.get("crop")
            if not isinstance(crop, nib.Nifti1Image):
                return original(*args, **kwargs)
            # Com crop em memória o TS ignora crop_path. A identidade inclui
            # inclusive um único voxel diferente no mapa usado para o recorte.
            digest = hashlib.sha256(np.asarray(crop.affine, dtype="<f8").tobytes())
            for z in range(crop.shape[2]):
                digest.update(np.ascontiguousarray(crop.dataobj[:, :, z]).tobytes())
            k["crop"] = (crop.shape, str(crop.get_data_dtype()), digest.hexdigest())
            for campo in ("crop_path", "multilabel_image", "nr_threads_saving", "quiet",
                          "verbose", "nora_tag"):
                k.pop(campo, None)
        entrada = k.pop("file_in")
        k.pop("file_out", None)
        if "device" in k:
            k["device"] = str(k["device"])
        backend = [os.environ.get(v) for v in
                   ("CUDA_VISIBLE_DEVICES", "RADAI_SEM_AUTOCAST", "RADAI_RESULTADOS_NA_CPU",
                    "RADAI_EXECUTOR", "RADAI_EXECUTOR_PRECISAO", "RADAI_EXECUTOR_CONFERIR",
                    "RADAI_THREADS")]
        try:
            receita = json.dumps([chave, versao, k, backend], sort_keys=True, separators=(",", ":"))
            identificador = hashlib.sha256(receita.encode("utf-8")).hexdigest()
        except (TypeError, ValueError):
            return original(*args, **kwargs)
        destino = os.path.join(pasta, "radai_loc_" + identificador + ".npy")
        if not gravar_entrega:
            try:
                dados = np.load(destino, mmap_mode="r", allow_pickle=False)
                imagem = entrada if isinstance(entrada, nib.Nifti1Image) else nib.load(str(entrada))
                if dados.dtype == np.uint8 and tuple(dados.shape) == tuple(imagem.shape):
                    _linha(MARCA + "localizador|dataset=%d|cache=1" % tarefa)
                    return nib.Nifti1Image(dados, imagem.affine), imagem, None
            except (ValueError, OSError, EOFError):
                pass
        seg, ct, est = original(*args, **kwargs)
        valores = np.asanyarray(seg.dataobj)
        imagem = entrada if isinstance(entrada, nib.Nifti1Image) else ct
        if (valores.dtype == np.uint8 and imagem is not None
                and np.array_equal(seg.affine, imagem.affine) and seg.shape == imagem.shape):
            import tempfile
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(dir=pasta, prefix="radai_loc_", suffix=".tmp",
                                                 delete=False) as f:
                    tmp = f.name
                    np.save(f, valores, allow_pickle=False)
                os.replace(tmp, destino)
            except OSError:
                pass
            finally:
                if tmp and os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
        return seg, ct, est

    prever._radai_localizador = True
    modulo.nnUNet_predict_image = prever


def _remendar_resultados_na_cpu(mod):
    import inspect
    cls = mod.nnUNetPredictor
    orig = cls.__init__
    if getattr(orig, "_radai_resultados_na_cpu", False):
        return
    sig = inspect.signature(orig)
    campos = [n for n in ("perform_everything_on_device",
                          "perform_everything_on_gpu") if n in sig.parameters]
    if not campos:
        raise RuntimeError("nnUNetPredictor.__init__ nao tem "
                           "perform_everything_on_device nesta versao")
    campo = campos[0]
    avisou = []

    def __init__(self, *a, **kw):
        b = sig.bind(self, *a, **kw)
        b.arguments[campo] = False
        orig(*b.args, **b.kwargs)
        if not avisou:
            avisou.append(1)
            _linha(MARCA + "remendo|resultados_na_cpu=1|%s=False" % campo)

    __init__._radai_resultados_na_cpu = True
    cls.__init__ = __init__


class _TorchSemAutocast(object):

    def __init__(self, real):
        self._real = real

    def __getattr__(self, nome):
        return getattr(self._real, nome)

    def autocast(self, *a, **kw):
        import contextlib
        return contextlib.nullcontext()


def _remendar_autocast(mod):
    if isinstance(getattr(mod, "torch", None), _TorchSemAutocast):
        return
    mod.torch = _TorchSemAutocast(mod.torch)



def _instalar_medidas(cls):
    """Observa as chamadas e os slicers reais, sem recalcular a grade."""
    from functools import wraps

    def instalar(nome, envolver):
        original = getattr(cls, nome, None)
        if original is not None and not getattr(original, "_radai_medida", False):
            novo = wraps(original)(envolver(original))
            novo._radai_medida = True
            setattr(cls, nome, novo)

    def emitir(inst, fase, extra=""):
        chave = getattr(inst, "_radai_chamada", None)
        if chave:
            dataset, ordem, inicio = chave
            _linha(MARCA + "%s|dataset=%s|ordem=%d|segundos=%.6f%s"
                   % (fase, dataset, ordem, time.perf_counter() - inicio, extra))

    def chamada(original):
        def medir(inst, *args, **kwargs):
            if getattr(inst, "_radai_chamada", None):
                return original(inst, *args, **kwargs)
            inst._radai_chamada = (_ESTADO["dataset"], _ESTADO["redes"], time.perf_counter())
            try:
                emitir(inst, "medida", "|fase=inicio")
                resultado = original(inst, *args, **kwargs)
                emitir(inst, "medida", "|fase=exportado")
                return resultado
            finally:
                inst._radai_chamada = None
        return medir

    def predicao(original):
        def medir(inst, *args, **kwargs):
            emitir(inst, "medida", "|fase=preprocessado")
            resultado = original(inst, *args, **kwargs)
            emitir(inst, "medida", "|fase=fim_rede")
            return resultado
        return medir

    def janelas(original):
        def medir(inst, image_size, *args, **kwargs):
            fatias = original(inst, image_size, *args, **kwargs)
            emitir(inst, "janelas", "|n=%d|forma=%s" % (
                len(fatias), "x".join(str(int(n)) for n in image_size)))
            return fatias
        return medir

    for nome in ("predict_from_files", "predict_from_files_sequential"):
        instalar(nome, chamada)
    instalar("predict_logits_from_preprocessed_data", predicao)
    instalar("_internal_get_sliding_window_slicers", janelas)


def _remendar_rede_carregada(mod):
    cls = mod.nnUNetPredictor
    orig = cls.initialize_from_trained_model_folder
    if getattr(orig, "_radai_rede", False):
        return

    def initialize_from_trained_model_folder(self, pasta, *a, **kw):
        m = re.search(r"Dataset(\d+)", str(pasta))
        _ESTADO["redes"] = _ESTADO.get("redes", 0) + 1
        _ESTADO["dataset"] = m.group(1) if m else "?"
        _linha(MARCA + "rede|dataset=%s|ordem=%d|device=%s|resultados=%s"
               % (_ESTADO["dataset"], _ESTADO["redes"],
                  getattr(self, "device", "?"),
                  "placa" if getattr(self, "perform_everything_on_device",
                                     False) else "ram"))
        return orig(self, pasta, *a, **kw)

    initialize_from_trained_model_folder._radai_rede = True
    cls.initialize_from_trained_model_folder = \
        initialize_from_trained_model_folder


EXECUTORES = ("openvino_cpu", "openvino_gpu", "xpu")
_EXECUTOR = {"desligado": None, "redes": 0}


def _dispositivo_do_argv(argv):
    argv = list(argv or [])
    for i, a in enumerate(argv):
        if a in ("-d", "--device") and i + 1 < len(argv):
            return str(argv[i + 1]).strip().lower()
        if a.startswith("--device="):
            return a.split("=", 1)[1].strip().lower()
    return ""


_DEVICES_CARREGADO = {}


def _carregar_radai_devices():
    mod = sys.modules.get("radai_devices")
    if mod is not None:
        return mod
    mod = _DEVICES_CARREGADO.get("mod")
    if mod is not None:
        return mod
    import importlib.util
    cam = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "radai_devices.py")
    spec = importlib.util.spec_from_file_location("radai_devices", cam)
    if spec is None or spec.loader is None or not os.path.isfile(cam):
        raise ImportError("sem %s" % os.path.basename(cam))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _DEVICES_CARREGADO["mod"] = mod
    return mod


def _regra_de_threads():
    try:
        mod = _carregar_radai_devices()
        r = mod.regra_de_threads()
        return r.get("n"), str(r.get("motivo") or "?")
    except Exception as e:
        return None, ("radai_devices nao carregou (%s: %s): fica o 8 da "
                      "biblioteca" % (type(e).__name__, str(e)[:80]))


def _teto_de_threads(ambiente=None, argv=None):
    amb = os.environ if ambiente is None else ambiente
    bruto = str(amb.get("RADAI_THREADS") or "").strip()
    origem = "RADAI_THREADS"
    if not bruto:
        if _dispositivo_do_argv(argv) != "cpu":
            return None
        ja = str(amb.get("nnUNet_def_n_proc") or "").strip()
        if ja:
            _linha(MARCA + "remendo|threads=%s|origem=nnUNet_def_n_proc ja "
                   "estava no ambiente (o padrao nao passa por cima)" % ja)
            return None
        n_regra, motivo = _regra_de_threads()
        if not n_regra:
            _linha(MARCA + "remendo|threads=biblioteca|origem=%s" % motivo)
            return None
        bruto = str(n_regra)
        origem = "regra de radai_devices: %s" % motivo
    try:
        n = int(bruto)
        if n < 1:
            raise ValueError(bruto)
    except ValueError:
        _linha(MARCA + "aviso|RADAI_THREADS=%r nao e inteiro positivo; o teto "
               "fica o da biblioteca (nnUNet_def_n_proc)" % bruto)
        return None
    if "nnunetv2.configuration" in sys.modules:
        _linha(MARCA + "aviso|RADAI_THREADS=%d chegou depois de o nnU-Net "
               "ser importado; o teto fica o que ele ja leu" % n)
        return None
    amb["nnUNet_def_n_proc"] = str(n)
    _linha(MARCA + "remendo|threads=%d|origem=%s" % (n, origem))
    return n


def _regua_da_conferencia():
    d = _carregar_radai_devices()
    return {"limiar": float(d.LIMIAR_CONCORDANCIA),
            "estruturas": int(d.ESTRUTURAS_MINIMAS_NO_PATCH),
            "fracao": float(d.FRACAO_MINIMA_DE_ESTRUTURA_NO_PATCH),
            "patches": int(d.PATCHES_MAXIMOS_PARA_CONFERIR)}


def _argmax_concorda(a, b):
    m = _medir_patch(a, b)
    return m["concordancia"], m["max_dif"]


def _medir_patch(a, b):
    import numpy as np
    x = a.detach().float().cpu().numpy() if hasattr(a, "detach") else np.asarray(a)
    y = b.detach().float().cpu().numpy() if hasattr(b, "detach") else np.asarray(b)
    ruim = {"concordancia": 0.0, "concordancia_estrutura": 0.0,
            "max_dif": float("inf"), "estruturas": 0, "fracao": 0.0,
            "voxels": 0}
    if x.shape != y.shape:
        return ruim
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        return ruim
    ax = np.argmax(x[0], axis=0)
    ay = np.argmax(y[0], axis=0)
    igual = ax == ay
    onde = (ax != 0) | (ay != 0)
    n_onde = int(onde.sum())
    classes = np.unique(ay)
    return {"concordancia": float(igual.mean()),
            "concordancia_estrutura": (float(igual[onde].mean()) if n_onde
                                       else 0.0),
            "max_dif": float(np.max(np.abs(x.astype(np.float64) - y))),
            "estruturas": int((classes != 0).sum()),
            "fracao": float((ay != 0).mean()),
            "voxels": int(ay.size)}


class _RedeOpenVINO(object):

    def __init__(self, rede, executor, dataset="?", precisao=None,
                 conferir=True, pasta_cache=None, ov=None, chave_pesos=None,
                 torch_mod=None, regua=None):
        self._rede = rede
        self._torch = torch_mod
        self._executor = executor
        self._disp = "GPU" if executor == "openvino_gpu" else "CPU"
        self._prec = (precisao or "f32").lower()
        self._conferir = bool(conferir)
        self._conferido = False
        self._regua = regua
        self._tentativas = 0
        self._so_pytorch = False
        self._compilados = {}
        self._dataset = dataset
        self._cache = pasta_cache
        self._ov = ov
        self._versao_pesos = 0
        self._chave_pesos = chave_pesos

    def load_state_dict(self, sd, *a, **kw):
        r = self._rede.load_state_dict(sd, *a, **kw)
        self._compilados.clear()
        self._conferido = False
        self._tentativas = 0
        self._so_pytorch = False
        self._versao_pesos += 1
        return r

    def to(self, *a, **kw):
        return self

    def eval(self):
        self._rede.eval()
        return self

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        return getattr(self._rede, nome)

    def _compilado(self, x):
        forma = tuple(int(s) for s in x.shape)
        c = self._compilados.get(forma)
        if c is not None:
            return c
        import time as _t
        ov = self._ov
        if ov is None:
            import openvino as ov
            self._ov = ov
        t0 = _t.time()
        core = ov.Core()
        if self._cache:
            try:
                core.set_property({"CACHE_DIR": os.path.join(self._cache,
                                                             "kernels")})
            except Exception:
                pass
        modelo, origem = self._modelo(ov, core, x, forma)
        t1 = _t.time()
        conf = {"INFERENCE_PRECISION_HINT": self._prec}
        if self._disp == "CPU":
            try:
                conf["INFERENCE_NUM_THREADS"] = int(
                    self._torch_de_verdade().get_num_threads())
            except Exception:
                pass
        c = core.compile_model(modelo, self._disp, conf)
        _linha(MARCA + "executor|dataset=%s|backend=%s|precisao=%s|ir=%s|"
               "preparar_s=%.1f|compilar_s=%.1f|threads=%s"
               % (self._dataset, self._executor, self._prec, origem, t1 - t0,
                  _t.time() - t1, conf.get("INFERENCE_NUM_THREADS", "-")))
        self._compilados[forma] = c
        return c

    def _modelo(self, ov, core, x, forma):
        import hashlib
        xml = None
        if self._cache and self._chave_pesos:
            chave = hashlib.sha1(("%s|%s|%d|%s|%s" % (
                self._chave_pesos, forma, self._versao_pesos,
                versao_do_pacote("openvino", ov), 1)).encode("utf-8")
            ).hexdigest()[:20]
            xml = os.path.join(self._cache, "ir_%s.xml" % chave)
            if os.path.isfile(xml):
                try:
                    return core.read_model(xml), "cache"
                except Exception as e:
                    _linha(MARCA + "aviso|IR guardado ilegivel (%s) - "
                           "convertendo de novo" % type(e).__name__)
                    for p in (xml, xml[:-4] + ".bin"):
                        try:
                            os.remove(p)
                        except OSError:
                            pass
        modelo = ov.convert_model(self._rede, example_input=x)
        if xml:
            try:
                os.makedirs(self._cache, exist_ok=True)
                tmp = xml[:-4] + ".tmp%d.xml" % os.getpid()
                ov.save_model(modelo, tmp, compress_to_fp16=False)
                os.replace(tmp[:-4] + ".bin", xml[:-4] + ".bin")
                os.replace(tmp, xml)
            except Exception:
                pass
        return modelo, "convertido"

    def _torch_de_verdade(self):
        if self._torch is None:
            import torch
            self._torch = torch
        return self._torch

    def _cair(self, motivo):
        _EXECUTOR["desligado"] = motivo
        _linha(MARCA + "aviso|executor %s falhou na rede %s (%s) - recuo para "
               "o PyTorch CPU nesta rede e nas seguintes deste processo"
               % (self._executor, self._dataset, motivo))

    def _passada(self, x):
        import numpy as np
        c = self._compilado(x)
        xn = (x.detach().cpu().numpy() if hasattr(x, "detach")
              else np.asarray(x))
        return self._torch_de_verdade().from_numpy(
            np.array(c(xn)[0], dtype=np.float32, copy=True))

    def __call__(self, x):
        if _EXECUTOR.get("desligado") or self._so_pytorch:
            return self._rede(x)
        import time as _t
        try:
            t0 = _t.time()
            y = self._passada(x)
            s_ov = _t.time() - t0
        except Exception as e:
            self._cair("%s: %s" % (type(e).__name__, str(e)[:200]))
            return self._rede(x)
        if self._conferir and not self._conferido:
            try:
                regua = self._regua or _regua_da_conferencia()
                self._regua = regua
            except Exception as e:
                self._cair("a regua da conferencia (radai_devices) nao "
                           "carregou: %s: %s" % (type(e).__name__, str(e)[:120]))
                return self._rede(x)
            self._tentativas += 1
            try:
                t0 = _t.time()
                ref = self._rede(x)
                s_torch = _t.time() - t0
                m = _medir_patch(y, ref)
            except Exception as e:
                self._cair("a conferencia levantou %s: %s"
                           % (type(e).__name__, str(e)[:160]))
                return self._rede(x)
            conc, dif = m["concordancia"], m["max_dif"]
            medivel = dif != float("inf")
            if medivel and (m["estruturas"] < regua["estruturas"]
                            or m["fracao"] < regua["fracao"]):
                if self._tentativas >= regua["patches"]:
                    self._so_pytorch = True
                    _linha(MARCA + "aviso|executor %s na rede %s: nenhum dos "
                           "%d primeiros patches tinha estrutura para conferir "
                           "(a referencia pede %d classe(s) de estrutura em "
                           "%.0f%% do patch) - ESTA rede fica no PyTorch CPU; "
                           "o executor segue para as outras"
                           % (self._executor, self._dataset, self._tentativas,
                              regua["estruturas"], regua["fracao"] * 100.0))
                return ref
            self._conferido = True
            if (conc < regua["limiar"]
                    or m["concordancia_estrutura"] < regua["limiar"]):
                self._cair("patch conferido discorda do PyTorch: argmax "
                           "%.4f%% (%.4f%% onde ha estrutura), maior "
                           "diferenca de logit %.3g"
                           % (conc * 100.0, m["concordancia_estrutura"] * 100.0,
                              dif))
                return ref
            _linha(MARCA + "executor|dataset=%s|conferido=1|concordancia=%.5f"
                   "|concordancia_estrutura=%.5f|estruturas=%d|fracao=%.3f"
                   "|patch=%d|max_dif_logit=%.3g|primeira_s=%.1f"
                   "|referencia_torch_s=%.1f"
                   % (self._dataset, conc, m["concordancia_estrutura"],
                      m["estruturas"], m["fracao"], self._tentativas, dif,
                      s_ov, s_torch))
        return y


class _RedeXPU(_RedeOpenVINO):

    def __init__(self, rede, executor="xpu", dataset="?", conferir=True,
                 torch_mod=None, regua=None, **_kw):
        _RedeOpenVINO.__init__(self, rede, executor, dataset=dataset,
                               conferir=conferir, torch_mod=torch_mod,
                               regua=regua)
        self._disp = "xpu"
        self._na_placa = None

    def load_state_dict(self, sd, *a, **kw):
        r = _RedeOpenVINO.load_state_dict(self, sd, *a, **kw)
        self._na_placa = None
        return r

    def _passada(self, x):
        import copy
        import time as _t
        torch = self._torch_de_verdade()
        if self._na_placa is None:
            t0 = _t.time()
            self._na_placa = copy.deepcopy(self._rede).to(self._disp).eval()
            _linha(MARCA + "executor|dataset=%s|backend=xpu|mover_s=%.1f"
                   % (self._dataset, _t.time() - t0))
        with torch.no_grad():
            y = self._na_placa(x.to(self._disp))
        return y.float().cpu()


def _chave_dos_pesos(pasta):
    try:
        base = os.path.abspath(str(pasta))
        partes = [base]
        for d in sorted(os.listdir(base)):
            if not d.startswith("fold_"):
                continue
            for f in sorted(os.listdir(os.path.join(base, d))):
                if f.endswith(".pth"):
                    st = os.stat(os.path.join(base, d, f))
                    partes.append("%s/%s:%d:%d" % (d, f, st.st_size,
                                                   int(st.st_mtime)))
        return "|".join(partes) if len(partes) > 1 else None
    except Exception:
        return None


def _remendar_executor(mod, executor, precisao=None, conferir=True,
                       pasta_cache=None, ov=None, regua=None):
    cls = mod.nnUNetPredictor
    orig = cls.initialize_from_trained_model_folder
    if getattr(orig, "_radai_executor", False):
        return

    def initialize_from_trained_model_folder(self, pasta, *a, **kw):
        r = orig(self, pasta, *a, **kw)
        dev = getattr(getattr(self, "device", None), "type",
                      str(getattr(self, "device", "")))
        m = re.search(r"Dataset(\d+)", str(pasta))
        ds = m.group(1) if m else "?"
        if _EXECUTOR.get("desligado"):
            return r
        if str(dev) != "cpu":
            _linha(MARCA + "aviso|executor %s ignorado na rede %s: o predictor "
                   "esta em %s (o executor so troca a passada em CPU)"
                   % (executor, ds, dev))
            return r
        rede = getattr(self, "network", None)
        if rede is None or isinstance(rede, _RedeOpenVINO):
            return r
        if executor == "xpu":
            self.network = _RedeXPU(rede, executor, dataset=ds,
                                    conferir=conferir, regua=regua)
        else:
            self.network = _RedeOpenVINO(rede, executor, dataset=ds,
                                         precisao=precisao, conferir=conferir,
                                         pasta_cache=pasta_cache, ov=ov,
                                         chave_pesos=_chave_dos_pesos(pasta),
                                         regua=regua)
        _EXECUTOR["redes"] = _EXECUTOR.get("redes", 0) + 1
        return r

    initialize_from_trained_model_folder._radai_executor = True
    cls.initialize_from_trained_model_folder = \
        initialize_from_trained_model_folder


def _executor_pedido(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    ex = str(amb.get("RADAI_EXECUTOR") or "").strip().lower()
    if not ex or ex in ("torch", "pytorch", "torch_cpu"):
        return None, u""
    if ex not in EXECUTORES:
        _linha(MARCA + "aviso|RADAI_EXECUTOR=%r desconhecido (conhecidos: %s); "
               "a rede e a do PyTorch" % (ex, ", ".join(EXECUTORES)))
        return None, u"desconhecido"
    conferir = (str(amb.get("RADAI_EXECUTOR_CONFERIR") or "1").strip()
                not in ("0", "nao", "false", "off"))
    regua = None
    if conferir:
        try:
            regua = _regua_da_conferencia()
        except Exception as e:
            _linha(MARCA + "aviso|executor %s pedido e a regua da conferencia "
                   "(radai_devices) nao carregou (%s: %s); a rede e a do "
                   "PyTorch" % (ex, type(e).__name__, str(e)[:120]))
            return None, u"sem regua"
    if ex == "xpu":
        try:
            import torch
            ok = bool(getattr(torch, "xpu", None) and torch.xpu.is_available())
        except Exception as e:
            _linha(MARCA + "aviso|executor xpu pedido e o torch nao responde "
                   "(%s: %s); a rede e a do PyTorch CPU" % (type(e).__name__,
                                                          str(e)[:120]))
            return None, u"sem torch"
        if not ok:
            _linha(MARCA + "aviso|executor xpu pedido e este torch (%s) nao "
                   "tem XPU disponivel; a rede e a do PyTorch CPU"
                   % versao_do_pacote("torch", torch))
            return None, u"sem xpu"
        return ex, {"conferir": conferir, "regua": regua,
                    "versao": "torch %s" % versao_do_pacote("torch", torch),
                    "precisao": "fp32"}
    extra = str(amb.get("RADAI_EXECUTOR_PASTA") or "").strip()
    if extra and os.path.isdir(extra) and extra not in sys.path:
        sys.path.append(extra)
    try:
        import openvino as ov
    except Exception as e:
        _linha(MARCA + "aviso|executor %s pedido e o openvino nao importa "
               "(%s: %s); a rede e a do PyTorch" % (ex, type(e).__name__,
                                                   str(e)[:120]))
        return None, u"sem openvino"
    cache = str(amb.get("RADAI_EXECUTOR_CACHE") or "").strip()
    if not cache:
        import tempfile
        cache = os.path.join(tempfile.gettempdir(), "radai_openvino_cache")
    return ex, {"precisao": str(amb.get("RADAI_EXECUTOR_PRECISAO") or "f32"),
                "conferir": conferir, "regua": regua,
                "pasta_cache": cache, "ov": ov,
                "versao": versao_do_pacote("openvino", ov).split("-")[0]}


LIMIAR_EXPORTACAO_NO_PROCESSO_MB = 2048
_EXPORTACAO = {"no_processo": 0, "limiar_bytes": None}


def _bytes_de(obj):
    try:
        n = getattr(obj, "nbytes", None)
        if isinstance(n, int) and not isinstance(n, bool):
            return n
        if hasattr(obj, "element_size") and hasattr(obj, "nelement"):
            return int(obj.element_size()) * int(obj.nelement())
    except Exception:
        pass
    return 0


def _bytes_dos_argumentos(args=(), kwds=None):
    total = 0
    for a in list(args or ()):
        total += _bytes_de(a)
    for v in dict(kwds or {}).values():
        total += _bytes_de(v)
    return total


def _limiar_de_exportacao(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    bruto = str(amb.get("RADAI_EXPORTACAO_LIMIAR_MB") or "").strip()
    padrao = LIMIAR_EXPORTACAO_NO_PROCESSO_MB * _MB
    if not bruto:
        return padrao, "fabrica"
    try:
        mb = int(bruto)
        if mb < 0:
            raise ValueError(bruto)
    except ValueError:
        _linha(MARCA + "aviso|RADAI_EXPORTACAO_LIMIAR_MB=%r nao e inteiro >= 0; "
               "o limiar fica o de fabrica (%d MiB)"
               % (bruto, LIMIAR_EXPORTACAO_NO_PROCESSO_MB))
        return padrao, "fabrica"
    return mb * _MB, "RADAI_EXPORTACAO_LIMIAR_MB"


class _ResultadoPronto(object):

    def __init__(self, valor=None, erro=None):
        self._valor = valor
        self._erro = erro

    def ready(self):
        return True

    def successful(self):
        return self._erro is None

    def wait(self, timeout=None):
        return None

    def get(self, timeout=None):
        if self._erro is not None:
            raise self._erro
        return self._valor


def _exportar_aqui(func, chamadas, n_bytes, limiar, varias=False,
                   callback=None, error_callback=None):
    nome = getattr(func, "__name__", "?")
    _EXPORTACAO["no_processo"] = _EXPORTACAO.get("no_processo", 0) + 1
    _linha(MARCA + "remendo|exportacao=no_processo|funcao=%s|matriz_mb=%d|"
           "limiar_mb=%d|motivo=matriz acima do limiar (o pipe do "
           "multiprocessing quebrou com 4,24 GiB); a mesma funcao roda neste "
           "processo, sem pipe" % (nome, n_bytes // _MB, limiar // _MB))
    t0 = time.time()
    try:
        valores = [func(*a, **k) for a, k in chamadas]
    except Exception as e:
        _linha(MARCA + "aviso|exportacao no processo levantou %s: %s"
               % (type(e).__name__, str(e)[:200]))
        if error_callback is not None:
            try:
                error_callback(e)
            except Exception:
                pass
        return _ResultadoPronto(erro=e)
    rss = _rss_mb()
    _linha(MARCA + "remendo|exportacao=no_processo|feita_s=%.1f|rss_mb=%s"
           % (time.time() - t0, rss if rss is not None else "?"))
    valor = valores if varias else valores[0]
    if callback is not None:
        callback(valor)
    return _ResultadoPronto(valor=valor)


class _PoolComExportacaoNoProcesso(object):

    def __init__(self, real, limiar):
        self._real = real
        self._limiar = int(limiar)

    def __getattr__(self, nome):
        if nome in ("_real", "_limiar"):
            raise AttributeError(nome)
        return getattr(self._real, nome)

    def __enter__(self):
        self._real.__enter__()
        return self

    def __exit__(self, *exc):
        return self._real.__exit__(*exc)

    def apply_async(self, func, args=(), kwds=None, callback=None,
                    error_callback=None):
        kwds = {} if kwds is None else kwds
        n = _bytes_dos_argumentos(args, kwds)
        if n <= self._limiar:
            return self._real.apply_async(func, args, kwds, callback=callback,
                                          error_callback=error_callback)
        return _exportar_aqui(func, [(tuple(args), dict(kwds))], n,
                              self._limiar, varias=False, callback=callback,
                              error_callback=error_callback)

    def starmap_async(self, func, iterable, chunksize=None, callback=None,
                      error_callback=None):
        lista = [tuple(a) for a in iterable]
        n = max([_bytes_dos_argumentos(a) for a in lista] or [0])
        if n <= self._limiar:
            return self._real.starmap_async(func, lista, chunksize,
                                            callback=callback,
                                            error_callback=error_callback)
        return _exportar_aqui(func, [(a, {}) for a in lista], n, self._limiar,
                              varias=True, callback=callback,
                              error_callback=error_callback)


class _ContextoComExportacaoNoProcesso(object):

    def __init__(self, real, limiar):
        self._real = real
        self._limiar = limiar

    def __getattr__(self, nome):
        if nome in ("_real", "_limiar"):
            raise AttributeError(nome)
        return getattr(self._real, nome)

    def Pool(self, *a, **kw):
        return _PoolComExportacaoNoProcesso(self._real.Pool(*a, **kw),
                                            self._limiar)


class _MultiprocessingComExportacaoNoProcesso(object):

    def __init__(self, real, limiar):
        self._real = real
        self._limiar = limiar

    def __getattr__(self, nome):
        if nome in ("_real", "_limiar"):
            raise AttributeError(nome)
        return getattr(self._real, nome)

    def get_context(self, *a, **kw):
        return _ContextoComExportacaoNoProcesso(
            self._real.get_context(*a, **kw), self._limiar)

    def Pool(self, *a, **kw):
        return _PoolComExportacaoNoProcesso(self._real.Pool(*a, **kw),
                                            self._limiar)


def _remendar_exportacao(mod, limiar_bytes):
    atual = getattr(mod, "multiprocessing", None)
    if atual is None:
        raise RuntimeError("o modulo do predictor nao tem `multiprocessing` "
                           "nesta versao")
    if isinstance(atual, _MultiprocessingComExportacaoNoProcesso):
        atual._limiar = int(limiar_bytes)
    else:
        mod.multiprocessing = _MultiprocessingComExportacaoNoProcesso(
            atual, int(limiar_bytes))
    _EXPORTACAO["limiar_bytes"] = int(limiar_bytes)


def aplicar_remendos(resultados_na_cpu=None, sem_autocast=None, modulo=None,
                     executor=None, exportacao=None):
    if resultados_na_cpu is None:
        resultados_na_cpu = _ligada(os.environ.get("RADAI_RESULTADOS_NA_CPU"))
    if sem_autocast is None:
        sem_autocast = _ligada(os.environ.get("RADAI_SEM_AUTOCAST"))
    ex_nome, ex_op = None, None
    if executor is None:
        ex_nome, ex_op = _executor_pedido()
    elif executor:
        ex_nome, ex_op = executor
    feitos = []
    if modulo is None:
        if not os.environ.get("nnUNet_results"):
            if resultados_na_cpu or sem_autocast or ex_nome:
                _linha(MARCA + "aviso|remendos NAO aplicados: nnUNet_results "
                       "nao definido (importar o nnU-Net agora o quebraria)")
            return feitos
        try:
            import nnunetv2.inference.predict_from_raw_data as modulo
        except Exception as e:
            if resultados_na_cpu or sem_autocast or ex_nome:
                _linha(MARCA + "aviso|nao consegui importar o predictor do "
                       "nnU-Net para os remendos (%s: %s)"
                       % (type(e).__name__, e))
            return feitos
    try:
        _remendar_rede_carregada(modulo)
        _instalar_medidas(modulo.nnUNetPredictor)
        feitos.append("rede")
    except Exception as e:
        _linha(MARCA + "aviso|remendo rede falhou (%s: %s)"
               % (type(e).__name__, e))
    if _ligada(os.environ.get("RADAI_PREDICAO_SEQUENCIAL", "1")):
        try:
            _remendar_predicao_sequencial(modulo)
            feitos.append("sequencial")
            _linha(MARCA + "remendo|predicao=sequencial")
        except (AttributeError, ValueError, TypeError):
            _linha(MARCA + "aviso|predicao sequencial indisponivel; usando os pools")
    if exportacao is not False:
        try:
            if exportacao is None:
                limiar, _origem = _limiar_de_exportacao()
            else:
                limiar = int(exportacao)
            _remendar_exportacao(modulo, limiar)
            feitos.append("exportacao")
        except Exception as e:
            _linha(MARCA + "aviso|remendo exportacao FALHOU (%s: %s) - a "
                   "matriz grande vai pelo pipe da biblioteca, que quebrou "
                   "com 4,24 GiB (medido)" % (type(e).__name__, e))
    if resultados_na_cpu:
        try:
            _remendar_resultados_na_cpu(modulo)
            feitos.append("resultados_na_cpu")
        except Exception as e:
            _linha(MARCA + "aviso|remendo resultados_na_cpu FALHOU (%s: %s) "
                   "- a biblioteca vai tentar o resultado na placa"
                   % (type(e).__name__, e))
    if sem_autocast:
        try:
            _remendar_autocast(modulo)
            feitos.append("sem_autocast")
            _linha(MARCA + "remendo|autocast=0")
        except Exception as e:
            _linha(MARCA + "aviso|remendo autocast FALHOU (%s: %s)"
                   % (type(e).__name__, e))
    if ex_nome:
        try:
            op = dict(ex_op or {})
            _remendar_executor(modulo, ex_nome, precisao=op.get("precisao"),
                               conferir=op.get("conferir", True),
                               pasta_cache=op.get("pasta_cache"),
                               ov=op.get("ov"), regua=op.get("regua"))
            feitos.append("executor")
            _linha(MARCA + "remendo|executor=%s|versao=%s|precisao=%s|"
                   "conferir=%d" % (ex_nome, op.get("versao", "?"),
                                    op.get("precisao", "f32"),
                                    1 if op.get("conferir", True) else 0))
        except Exception as e:
            _linha(MARCA + "aviso|remendo executor %s FALHOU (%s: %s) - a rede "
                   "e a do PyTorch" % (ex_nome, type(e).__name__, e))
    return feitos


def _sem_estatistica(*a, **kw):
    return None


_sem_estatistica._radai_sem_estatistica = True

FUNCOES_DE_ENVIO = ("send_usage_stats", "send_usage_stats_application")


def remendar_estatistica(modulos=None):
    feitos = []
    try:
        if modulos is None:
            modulos = [(n, m) for n, m in list(sys.modules.items())
                       if m is not None
                       and (n == "totalsegmentator"
                            or n.startswith("totalsegmentator."))]
        for nome, mod in modulos:
            for fn in FUNCOES_DE_ENVIO:
                atual = getattr(mod, fn, None)
                if atual is None or getattr(atual, "_radai_sem_estatistica",
                                            False):
                    continue
                setattr(mod, fn, _sem_estatistica)
                feitos.append("%s.%s" % (nome, fn))
    except Exception as e:
        _linha(MARCA + "aviso|remendo estatistica FALHOU (%s: %s) - so o "
               "config.json segura o envio" % (type(e).__name__, e))
        return feitos
    if not feitos and not _ja_remendada(modulos):
        _linha(MARCA + "aviso|remendo estatistica: nenhuma funcao de envio "
               "achada nos modulos do TotalSegmentator - so o config.json "
               "segura o envio")
    return feitos


def _ja_remendada(modulos):
    try:
        return any(getattr(getattr(m, fn, None), "_radai_sem_estatistica",
                           False)
                   for _n, m in modulos for fn in FUNCOES_DE_ENVIO)
    except Exception:
        return False


@contextmanager
def _recorte_dental_cpu(argv):
    """O TS 2.18 pode perder o nome da CPU ao chamar a craniofacial dentro de teeth."""
    tarefa = dispositivo = None
    for i, argumento in enumerate(argv):
        chave, separador, valor = argumento.partition("=")
        if not separador:
            valor = argv[i + 1] if i + 1 < len(argv) else ""
        if chave in ("-ta", "--task"):
            tarefa = valor
        elif chave in ("-d", "--device"):
            dispositivo = valor
    api = sys.modules.get("totalsegmentator.python_api")
    converter = getattr(api, "convert_device_to_string", None)
    if tarefa != "teeth" or dispositivo != "cpu" or converter is None:
        yield
        return

    def converter_recorte(device):
        convertido = converter(device)
        if convertido is None and isinstance(device, str) and device == "cpu":
            return "cpu"
        return convertido

    api.convert_device_to_string = converter_recorte
    try:
        yield
    finally:
        api.convert_device_to_string = converter


def rodar(main, argv, prog="TotalSegmentator"):
    antigo = sys.argv
    sys.argv = [prog] + list(argv or [])
    try:
        with _recorte_dental_cpu(sys.argv[1:]):
            r = main()
        return r if isinstance(r, int) and not isinstance(r, bool) else 0
    except SystemExit as e:
        c = e.code
        if c is None:
            return 0
        if isinstance(c, int):
            return c
        try:
            sys.stderr.write("%s\n" % (c,))
        except Exception:
            pass
        return 1
    except BaseException:
        traceback.print_exc()
        return 1
    finally:
        sys.argv = antigo


def _fim(codigo):
    for canal in (sys.stdout, sys.stderr):
        try:
            canal.flush()
        except Exception:
            pass
    try:
        commit, ws = pico_do_processo_mb()
        _linha(MARCA + "pico|commit_mb=%s|ws_mb=%s"
               % ("?" if commit is None else commit,
                  "?" if ws is None else ws))
    except Exception:
        pass
    _linha(MARCA + "fim|codigo=%d" % codigo)
    for canal in (sys.stdout, sys.stderr):
        try:
            canal.flush()
        except Exception:
            pass
    _SAIR(codigo)


def executar(main, argv, prog="TotalSegmentator"):
    parar = threading.Event()
    t = threading.Thread(target=_pulsar, args=(_intervalo_do_pulso(), parar),
                         name="radai-pulso")
    t.daemon = True
    t.start()
    codigo = rodar(main, argv, prog=prog)
    parar.set()
    _fim(codigo)


def _preparar_nnunet():
    try:
        from totalsegmentator.config import setup_nnunet
        setup_nnunet()
    except Exception as e:
        _linha(MARCA + "aviso|nao consegui preparar as pastas do nnU-Net "
               "(%s: %s) - remendos desligados" % (type(e).__name__, e))
        return False
    return bool(os.environ.get("nnUNet_results"))


def principal(argv=None):
    _saida_sem_buffer()
    argv = list(sys.argv[1:] if argv is None else argv)
    espera = argv == ["--aguardar-ensaio"]
    _teto_de_threads(argv=argv)
    try:
        from totalsegmentator.bin.TotalSegmentator import main as ts_main
    except BaseException:
        traceback.print_exc()
        _fim(1)
        return
    preparado = _preparar_nnunet()
    if preparado:
        # O TS 2.18 substitui os dois predict_from_files ao importar este módulo.
        # Instale as marcas e o seletor de executor sobre os métodos efetivos.
        try:
            import totalsegmentator.nnunet
        except ImportError:
            pass
    if espera:
        import json
        import torch
        if torch.cuda.is_initialized():
            _linha(MARCA + "preaquecer|descartar=cuda_inicializado")
            _fim(75)
            return
        threads = os.environ.get("nnUNet_def_n_proc", "")
        _linha(MARCA + "preaquecer|pronto=1|threads=%s|ws_mb=%s" % (threads, _rss_mb()))
        sys.stdout.flush()
        linha = sys.stdin.readline(65537)
        if not linha or len(linha) > 65536:
            _fim(75)
            return
        try:
            pedido = json.loads(linha)
            argv = pedido["argv"]
            if str(pedido["threads"]) != threads:
                raise ValueError("teto de threads mudou")
            if (not isinstance(argv, list) or not argv
                    or not all(isinstance(x, str) for x in argv)):
                raise ValueError("argumentos inválidos")
            ambiente = pedido.get("ambiente", {})
            permitidas = {"CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER", "RADAI_SEM_AUTOCAST",
                          "RADAI_RESULTADOS_NA_CPU", "RADAI_CACHE_LOCALIZADOR", "RADAI_CHAVE_DA_ENTRADA"}
            if not isinstance(ambiente, dict) or set(ambiente) - permitidas:
                raise ValueError("variável não prevista para uma task")
            if not all(v is None or isinstance(v, str) for v in ambiente.values()):
                raise ValueError("valor de ambiente inválido")
            for nome in ("CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER"):
                if nome in ambiente and ambiente[nome] != os.environ.get(nome):
                    raise ValueError("afinidade da placa mudou")
            for k, v in ambiente.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        except (KeyError, TypeError, ValueError) as erro:
            _linha(MARCA + "preaquecer|descartar=%s" % type(erro).__name__)
            _fim(75)
            return
    remendar_estatistica()
    if preparado:
        aplicar_remendos()
    pasta = os.environ.get("RADAI_CACHE_LOCALIZADOR")
    chave = os.environ.get("RADAI_CHAVE_DA_ENTRADA")
    if pasta and chave and os.path.isdir(pasta):
        try:
            _remendar_localizador(pasta, chave)
        except (ImportError, AttributeError, TypeError, ValueError):
            _linha(MARCA + "aviso|cache de localizador indisponivel")
    executar(ts_main, argv)


if __name__ == "__main__":
    principal()
