"""Isolated inference worker for the seven ROCardS SavedModels used by LAD."""

import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parent))

MODELOS = ("HEART", "LV", "RV", "LA", "RA", "LV_RV_LA_RA", "LAD")
CANAIS = MODELOS[:5]
GRADE_REDE = (128, 128, 64)


def carregar_runtime(runtime):
    # O Python hospedeiro também contém NumPy: importe a cópia do TensorFlow
    # antes de qualquer biblioteca científica que possa preencher sys.modules.
    runtime = Path(runtime).resolve()
    sys.path.insert(0, str(runtime))
    import numpy
    import tensorflow
    import keras
    from google import protobuf

    for modulo in (numpy, tensorflow, keras, protobuf):
        if not Path(modulo.__file__).resolve().is_relative_to(runtime):
            raise RuntimeError("Dependência usada fora do runtime ROCardS: " + modulo.__name__)
    return tensorflow


def reamostrar(a, shape, interpolator=None):
    import SimpleITK as sitk
    if interpolator is None:
        interpolator = sitk.sitkLinear
    img = sitk.GetImageFromArray(a)
    size = tuple(int(v) for v in reversed(shape))
    spacing = tuple(x/y for x, y in zip(img.GetSize(), size))
    result = sitk.Resample(img, size, sitk.Transform(3, sitk.sitkIdentity), interpolator,
                           img.GetOrigin(), spacing, img.GetDirection(), 0, img.GetPixelID())
    return sitk.GetArrayFromImage(result)


def postprocess(pred, smooth=False):
    import numpy as np
    from scipy import ndimage, signal
    mask = pred > 0.5
    if not mask.any():
        return mask
    for k in np.flatnonzero(mask.any(axis=(0, 1))):
        mask[:, :, k] = ndimage.binary_fill_holes(mask[:, :, k])
    comp, n = ndimage.label(mask, structure=np.ones((3, 3, 3), bool))
    if n > 1:
        mask = comp == (np.bincount(comp.ravel())[1:].argmax() + 1)
    if smooth:
        gx, gy, gz = np.ogrid[-3:4, -3:4, -3:4]
        kernel = np.exp(-0.5*(gx**2 + gy**2 + gz**2))
        mask = signal.convolve(mask, kernel / kernel.sum(), mode="same") > 0.5
    return mask


def acabado(rede, shape):
    import numpy as np
    native = reamostrar(rede.astype("uint8"), shape)
    if not native.any():
        raise ValueError("ROCardS não encontrou DA com volume no recorte cardíaco.")
    lo, hi = [], []
    for axis, length in enumerate(native.shape):
        used = np.flatnonzero(native.any(axis=tuple(i for i in range(3) if i != axis)))
        lo.append(max(0, int(used[0])-4))
        hi.append(min(length, int(used[-1])+5))
    region = tuple(slice(a, b) for a, b in zip(lo, hi))
    local = postprocess(native[region])
    native[region] = postprocess(local.T, smooth=True).T
    if not native.any():
        raise ValueError("A DA ficou vazia após o acabamento do ROCardS.")
    return native


class Motor:
    def __init__(self, pesos, runtime, dispositivo, n_threads):
        from radai_study_modelos import exigir_plugin_coronarias
        exigir_plugin_coronarias()
        tf = carregar_runtime(runtime)
        import SimpleITK as sitk
        tf.config.threading.set_inter_op_parallelism_threads(1)
        tf.config.threading.set_intra_op_parallelism_threads(n_threads)
        sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(n_threads)
        gpus = tf.config.list_physical_devices("GPU")
        if dispositivo == "gpu" and not gpus:
            raise RuntimeError("GPU solicitada para a DA, mas o TensorFlow não encontrou uma GPU compatível. Use Auto ou CPU.")
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        self.dispositivo = "GPU" if gpus else "CPU"
        self.redes = {name: tf.keras.models.load_model(str(pesos/name), compile=False)
                      for name in MODELOS}

    def executar(self, ct, normalizador, spacing, interpolar_lacunas):
        import numpy as np
        import SimpleITK as sitk
        from radai_rocards_gap import interpolar
        started = perf_counter()
        image = np.clip(ct.astype(np.float32), -350, 1000)
        image += np.float32(350)
        image /= np.float32(normalizador)
        patch = reamostrar(image, GRADE_REDE)
        masks, timing = {}, {}
        for name, model in self.redes.items():
            t = perf_counter()
            canais = () if name == "HEART" else ("HEART",) if name in CANAIS else CANAIS
            data = np.stack([patch] + [masks[c] for c in canais], axis=-1)[None]
            pred = model.predict(data, verbose=0)[0]
            if not np.isfinite(pred).all():
                raise ValueError("Predição ROCardS inválida em " + name)
            if name == "LV_RV_LA_RA":
                labels = np.argmax(pred, axis=-1)
                for i, c in enumerate(CANAIS[1:], 1):
                    masks[c] = postprocess(labels == i)
            else:
                masks[name] = postprocess(pred[..., 0])
            timing[name] = perf_counter()-t
        raw = acabado(masks["LAD"], ct.shape)
        occupied = np.flatnonzero(raw.any(axis=(0, 1)))
        if interpolar_lacunas and np.any(np.diff(occupied) > 1):
            labels = np.zeros(GRADE_REDE, np.uint8)
            for i, c in enumerate(CANAIS[1:], 1):
                labels[masks[c]] = i
            chambers = reamostrar(labels, ct.shape, sitk.sitkNearestNeighbor)
            out, trace = interpolar(raw, ct, spacing, chambers)
        else:
            out = raw
            trace = {"fonte": "ROCardS LAD", "planos_preditos": occupied.tolist(),
                     "planos_interpolados": [], "n_planos_interpolados": 0,
                     "voxels_interpolados": 0, "lacunas": []}
        trace.update(dispositivo=self.dispositivo, segundos_etapas=timing,
                     segundos_campo_ate_mascara=perf_counter()-started)
        return out, raw, trace


def main():
    from radai_study_modelos import exigir_plugin_coronarias
    exigir_plugin_coronarias()
    job_dir = Path(sys.argv[1])
    cfg = json.loads((job_dir/"solicitacao.json").read_text(encoding="utf-8"))
    t = perf_counter()
    motor = Motor(Path(cfg["pesos"]), Path(cfg["runtime"]), cfg["dispositivo"], cfg["threads"])
    load_s = perf_counter()-t
    import numpy as np
    ct = np.load(job_dir/"tc.npy", mmap_mode="r", allow_pickle=False)
    out, raw, trace = motor.executar(ct, cfg["normalizador"], cfg["spacing"], cfg["interpolar"])
    trace["segundos_carga"] = load_s
    np.save(job_dir/"da.npy", out, allow_pickle=False)
    if cfg.get("comparar_bruta"):
        np.save(job_dir/"bruta.npy", raw, allow_pickle=False)
    (job_dir/"relatorio.json").write_text(json.dumps(trace), encoding="utf-8")


if __name__ == "__main__":
    main()

