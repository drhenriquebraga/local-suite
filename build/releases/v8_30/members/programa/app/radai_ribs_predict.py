# -*- coding: utf-8 -*-
"""Inferência isolada do clin_ct_ribs em uma única caixa posterior."""
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np


DATASET = "Dataset444_Ribs"
TREINADOR = "nnUNetTrainer_2000epochs_NoMirroring"
PASTA = TREINADOR + "__nnUNetPlans__3d_fullres"
ARQUIVOS = ("dataset.json", "plans.json", "fold_all/checkpoint_final.pth")
PASSO_MM = 1.5


def localizar(pasta_pesos=None):
    if pasta_pesos is None:
        import radai_models
        pasta_pesos = radai_models.pasta_do_modelo("moose_ribs")
    pasta = Path(pasta_pesos) / DATASET / PASTA
    if not all((pasta / arquivo).is_file() for arquivo in ARQUIVOS):
        raise FileNotFoundError("Dataset444_Ribs: arquivo de inferência ausente na instalação.")
    return pasta


def _grade_igual(a, b):
    return (a.GetSize() == b.GetSize()
            and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=1e-5, rtol=0)
            and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=1e-3, rtol=0)
            and np.allclose(a.GetDirection(), b.GetDirection(), atol=1e-5, rtol=0))


def predizer(recorte, dispositivo="cpu", python_exe=None, pasta_pesos=None):
    import SimpleITK as sitk
    from radai_moose_engine import _torch_device
    pasta = localizar(pasta_pesos)
    with tempfile.TemporaryDirectory(prefix="radai_costelas_") as tmp:
        entrada = Path(tmp) / "entrada.mha"
        saida = Path(tmp) / "rotulos.mha"
        sitk.WriteImage(recorte, str(entrada))
        ambiente = dict(os.environ)
        for chave in ("nnUNet_raw", "nnUNet_preprocessed", "nnUNet_results"):
            ambiente[chave] = tmp
        proc = subprocess.run(
            [str(python_exe or sys.executable), str(Path(__file__).resolve()), str(pasta),
             str(entrada), str(saida), _torch_device(dispositivo)],
            env=ambiente, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=7200, check=False)
        if proc.returncode:
            linhas = proc.stdout.decode("utf-8", errors="replace").splitlines()
            raise RuntimeError("MOOSE costelas: " + (linhas[-1][:320] if linhas else str(proc.returncode)))
        rotulos = sitk.ReadImage(str(saida))
        if not _grade_igual(recorte, rotulos):
            raise ValueError("A grade da predição de costelas difere da TC.")
        return sitk.GetArrayFromImage(rotulos)


def _eixos_da_reamostragem(tamanho, espacamento):
    # Convenção MOOSE 3.2.2: blocos iguais com pelo menos 150 voxels quando divisíveis.
    n = max(1, tamanho // 150)
    while tamanho % n:
        n -= 1
    entrada = tamanho // n
    saida = max(1, round(entrada * espacamento / PASSO_MM))
    return [(slice(i * entrada, (i + 1) * entrada), slice(i * saida, (i + 1) * saida))
            for i in range(n)]


def _reamostrar_tc(imagem):
    import SimpleITK as sitk
    dados = sitk.GetArrayViewFromImage(imagem)
    eixos = [_eixos_da_reamostragem(n, esp) for n, esp in zip(dados.shape, imagem.GetSpacing()[::-1])]
    novo = np.empty(tuple(e[-1][1].stop for e in eixos), dtype=dados.dtype)
    for bloco in itertools.product(*eixos):
        origem, destino = zip(*bloco)
        sub = sitk.GetImageFromArray(np.ascontiguousarray(dados[origem]))
        sub.SetSpacing(imagem.GetSpacing())
        tamanho = [s.stop - s.start for s in destino[::-1]]
        amostra = sitk.Resample(sub, tamanho, sitk.Transform(), sitk.sitkBSpline,
                               sub.GetOrigin(), [PASSO_MM] * 3, sub.GetDirection(), 0, sub.GetPixelID())
        novo[destino] = sitk.GetArrayViewFromImage(amostra)
    return novo


def _eixo_de_inferencia(n):
    # Cada bloco recebe contexto de 20 voxels em cada fronteira interna. Apenas
    # seu interior é copiado de volta; a grade final preserva o espaço físico.
    partes = (n + 349) // 350
    largura, sobra = divmod(n, partes)
    inicio = 0
    for i in range(partes):
        fim = inicio + largura + int(i < sobra)
        de, ate = max(0, inicio - 20), min(n, fim + 20)
        yield slice(de, ate), slice(inicio - de, fim - de), slice(inicio, fim)
        inicio = fim


def _predizer_bloco(preditor, entrada):
    # MOOSE exporta os logits como NumPy. A mesma conversão pode rodar no
    # processo atual, sem abrir o pool de exportação para uma única caixa.
    import torch
    from nnunetv2.inference.export_prediction import convert_predicted_logits_to_segmentation_with_correct_shape
    config = preditor.configuration_manager
    pre = config.preprocessor_class(verbose=False)
    dados, _, props = pre.run_case_npy(entrada, None, {"spacing": [PASSO_MM] * 3},
                                       preditor.plans_manager, config, preditor.dataset_json)
    tensor = torch.from_numpy(dados).contiguous()
    if preditor.device.type == "cuda":
        tensor = tensor.pin_memory()
    logits = preditor.predict_logits_from_preprocessed_data(tensor).cpu().detach().numpy()
    return convert_predicted_logits_to_segmentation_with_correct_shape(
        logits, preditor.plans_manager, config, preditor.label_manager, props,
        return_probabilities=False)


def aplicar_modelo(recorte, predizer_bloco):
    import SimpleITK as sitk
    ras = sitk.DICOMOrient(recorte, "RAS")
    dados = _reamostrar_tc(ras)
    rotulos = np.empty(dados.shape, dtype=np.uint8)
    for bloco in itertools.product(*[_eixo_de_inferencia(n) for n in dados.shape]):
        entrada, miolo, destino = zip(*bloco)
        sub = np.ascontiguousarray(dados[entrada][None])
        pred = predizer_bloco(sub)
        if pred.shape != sub.shape[1:] or pred.dtype.kind not in "iu" or pred.min() < 0 or pred.max() > 27:
            raise ValueError("Saída incompatível com os 27 rótulos do Dataset444_Ribs.")
        rotulos[destino] = pred[miolo]
    imagem = sitk.GetImageFromArray(rotulos)
    imagem.SetOrigin(ras.GetOrigin())
    imagem.SetDirection(ras.GetDirection())
    imagem.SetSpacing([PASSO_MM] * 3)
    # O MOOSE primeiro restaura os rótulos na referência ainda em RAS e só
    # depois desfaz as trocas de eixo. Uma interpolação direta na grade de
    # entrada tem outra ordem de operações nos empates de meio voxel.
    restaurada = sitk.Resample(imagem, ras, sitk.Transform(), sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
    orientacao = sitk.DICOMOrientImageFilter_GetOrientationFromDirectionCosines(recorte.GetDirection())
    return sitk.DICOMOrient(restaurada, orientacao)


def _executar(pasta, entrada, saida, dispositivo):
    import SimpleITK as sitk
    import torch
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
    pasta = Path(pasta)
    dataset = json.loads((pasta / "dataset.json").read_text(encoding="utf-8"))
    esperados = {"background": 0, "sternum": 27}
    for lado, deslocamento in (("left", 0), ("right", 13)):
        esperados.update({f"rib_{lado}_{n}": n + deslocamento for n in range(1, 14)})
    if {k: int(v) for k, v in dataset["labels"].items()} != esperados:
        raise ValueError("Tabela anatômica inesperada no Dataset444_Ribs.")
    device = torch.device(dispositivo)
    if device.type == "cpu":
        torch.set_num_threads(min(8, torch.get_num_threads()))
    p = nnUNetPredictor(tile_step_size=.5, use_gaussian=True, use_mirroring=False, device=device,
                        perform_everything_on_device=device.type == "cuda",
                        verbose=False, verbose_preprocessing=False, allow_tqdm=False)
    p.initialize_from_trained_model_folder(str(pasta), use_folds=("all",), checkpoint_name="checkpoint_final.pth")
    if not np.allclose(p.configuration_manager.spacing, [PASSO_MM] * 3):
        raise ValueError("Espaçamento inesperado no Dataset444_Ribs.")
    sitk.WriteImage(aplicar_modelo(sitk.ReadImage(entrada), lambda sub: _predizer_bloco(p, sub)), saida)


if __name__ == "__main__":
    _executar(*sys.argv[1:])
