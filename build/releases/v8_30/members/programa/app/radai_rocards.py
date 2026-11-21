"""DA/ROCardS no recorte do Heart_ai acabado com margem física de 10 mm."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter

import numpy as np
import SimpleITK as sitk

MARGEM_MM = 10.0
MODELOS = ("HEART", "LV", "RV", "LA", "RA", "LV_RV_LA_RA", "LAD")


def _raiz(base):
    if base is not None:
        return Path(base)
    from radai_models import pasta_do_modelo
    return Path(pasta_do_modelo("rocards_lad"))


def _verificar(base):
    raiz = _raiz(base)
    for modelo in MODELOS:
        sub = raiz/"models"/modelo
        for rel in ("saved_model.pb", "keras_metadata.pb", "variables/variables.index",
                    "variables/variables.data-00000-of-00001"):
            arq = sub/rel
            if not arq.is_file() or arq.stat().st_size == 0:
                raise FileNotFoundError("Recurso ROCardS ausente ou vazio: " + modelo + "/" + rel)
    for pacote in ("tensorflow", "keras"):
        if not (raiz/"runtime"/pacote/"__init__.py").is_file():
            raise FileNotFoundError("Runtime ROCardS incompleto: " + pacote)
    return raiz


def disponivel(base=None):
    try:
        _verificar(base)
        return True, "ROCardS disponível."
    except (OSError, ValueError, TypeError, ImportError) as exc:
        return False, str(exc)


def _mesma_grade(a, b):
    if a.GetSize() != b.GetSize() or any(not np.allclose(x, y, rtol=0, atol=1e-4)
              for x, y in ((a.GetOrigin(), b.GetOrigin()), (a.GetSpacing(), b.GetSpacing()),
                           (a.GetDirection(), b.GetDirection()))):
        raise ValueError("TC e Heart_ai exigem a mesma grade física.")


def _preparar(ref, heart):
    if not isinstance(ref, sitk.Image) or ref.GetDimension() != 3 or ref.GetNumberOfComponentsPerPixel() != 1:
        raise ValueError("Esperada TC escalar tridimensional.")
    spacing = np.asarray(ref.GetSpacing())
    direction = np.asarray(ref.GetDirection()).reshape(3, 3)
    if (np.any(spacing <= 0) or not np.isfinite(spacing).all()
            or not np.isfinite(ref.GetOrigin()).all()
            or not np.allclose(direction.T @ direction, np.eye(3), rtol=0, atol=1e-4)):
        raise ValueError("TC com espaçamento, origem ou orientação inválidos.")
    if isinstance(heart, sitk.Image):
        _mesma_grade(ref, heart)
        if heart.GetNumberOfComponentsPerPixel() != 1:
            raise ValueError("O Heart_ai deve ser escalar.")
        src = sitk.GetArrayViewFromImage(heart)
    else:
        src = np.asarray(heart)
        if src.shape != ref.GetSize()[::-1]:
            raise ValueError("O Heart_ai deve ter a mesma grade ZYX da TC.")
    if not np.logical_or(src == 0, src == 1).all():
        raise ValueError("Esperada máscara binária Heart_ai.")
    if not src.any():
        raise ValueError("O Heart_ai acabado está vazio.")
    if not isinstance(heart, sitk.Image):
        heart = sitk.GetImageFromArray(src.astype(np.uint8, copy=False))
        heart.CopyInformation(ref)
    lps = sitk.DICOMOrient(ref, "LPS")
    heart_lps = sitk.DICOMOrient(heart, "LPS")
    mask = sitk.GetArrayViewFromImage(heart_lps).T
    pad = np.ceil(MARGEM_MM / np.asarray(lps.GetSpacing())).astype(int)
    roi = []
    for axis in range(3):
        ids = np.flatnonzero(mask.any(axis=tuple(i for i in range(3) if i != axis)))
        roi.append(slice(max(0, int(ids[0]-pad[axis])), min(mask.shape[axis], int(ids[-1]+1+pad[axis]))))
    vox = sitk.GetArrayViewFromImage(lps).T
    maximo = float(np.max(vox))
    if not np.isfinite(maximo) or maximo <= -350 or not np.isfinite(vox[tuple(roi)]).all():
        raise ValueError("A TC não permite a normalização em HU exigida pelo ROCardS.")
    return lps, tuple(roi), min(maximo, 1000)+350


def _repor(data, roi, lps, ref):
    shape = tuple(s.stop-s.start for s in roi)
    if (data.shape != shape or data.dtype != np.uint8 or not data.any()
            or data.max() > 1):
        raise ValueError("O worker ROCardS devolveu uma máscara inválida.")
    out = np.zeros(lps.GetSize()[::-1], np.uint8)
    out[roi[::-1]] = data.T
    image = sitk.GetImageFromArray(out)
    image.CopyInformation(lps)
    orient = sitk.DICOMOrientImageFilter_GetOrientationFromDirectionCosines(ref.GetDirection())
    image = sitk.DICOMOrient(image, orient)
    _mesma_grade(ref, image)
    return sitk.GetArrayFromImage(image)


def segmentar(ref_ct_sitk, heart_ai_zyx, *, base=None, log=None, dispositivo=None,
              interpolar_lacunas=False, timeout_s=900, python_exe=None):
    """Devolve (DA uint8 na grade ZYX da TC, proveniência). Entrada Heart_ai já acabada."""
    start = perf_counter()
    lps, roi, normalizador = _preparar(ref_ct_sitk, heart_ai_zyx)
    raiz = _verificar(base)
    device = str(dispositivo or "auto").lower()
    if device in ("cuda", "cuda:0"):
        device = "gpu"
    if device not in ("cpu", "gpu", "auto"):
        raise ValueError("Dispositivo ROCardS desconhecido.")
    threads = min(8, os.cpu_count() or 1)
    cfg = dict(pesos=str((raiz/"models").resolve()), runtime=str((raiz/"runtime").resolve()),
               normalizador=normalizador, spacing=lps.GetSpacing(), threads=threads,
               dispositivo=device, interpolar=bool(interpolar_lacunas))
    env = os.environ.copy()
    env["TF_CPP_MIN_LOG_LEVEL"] = "2"
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"):
        env[key] = str(threads)
    if device == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = "-1"
    if log:
        log("ROCardS • recorte direto do Heart_ai acabado com 10 mm de margem.")
    with tempfile.TemporaryDirectory(prefix="radai-rocards-") as temp:
        job = Path(temp)
        np.save(job/"tc.npy", sitk.GetArrayViewFromImage(lps).T[roi], allow_pickle=False)
        (job/"solicitacao.json").write_text(json.dumps(cfg), encoding="utf-8")
        proc = subprocess.run([str(python_exe or sys.executable), str(Path(__file__).with_name("radai_rocards_worker.py")),
                               str(job)], env=env, capture_output=True, timeout=timeout_s,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode:
            detail = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()
            raise RuntimeError("Falha na inferência ROCardS: " + (detail[-1][:500] if detail else str(proc.returncode)))
        info = json.loads((job/"relatorio.json").read_text(encoding="utf-8"))
        out = _repor(np.load(job/"da.npy", allow_pickle=False), roi, lps, ref_ct_sitk)
    for key in ("planos_preditos", "planos_interpolados"):
        info[key] = [int(k+roi[2].start) for k in info[key]]
    for gap in info["lacunas"]:
        for key in ("ancoras", "planos"):
            if key in gap:
                gap[key] = [int(k+roi[2].start) for k in gap[key]]
    info.update(modo="direto", margem_mm=MARGEM_MM, indices_planos="LPS, base zero", dispositivo_solicitado=device,
                caixa_LPS_exclusiva=[[s.start, s.stop] for s in roi], voxels=int(out.sum()),
                volume_ml=float(np.count_nonzero(out)*np.prod(ref_ct_sitk.GetSpacing())/1000),
                segundos_totais=perf_counter()-start)
    n = info["n_planos_interpolados"]
    info["descricao_dicom"] = (
        "DA ROCardS; Heart_ai + 10 mm; %d cortes axiais interpolados por arco "
        "PCHIP, secoes nativas e ajuste local TC/camaras." % n if n else
        "DA ROCardS; Heart_ai + 10 mm; 0 cortes interpolados."
    )
    if log:
        if device == "auto" and info["dispositivo"] == "CPU":
            log("DA ROCardS em CPU: o TensorFlow não detectou uma GPU compatível no modo automático.")
        log("DA ROCardS • %.2f mL • %d planos interpolados • %.1f s" %
            (info["volume_ml"], info["n_planos_interpolados"], info["segundos_totais"]))
    return out, info

