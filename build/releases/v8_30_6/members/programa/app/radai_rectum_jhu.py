# -*- coding: utf-8 -*-
"""Segmentação local do reto em TC com os checkpoints públicos do JHU/MICA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from zipfile import ZipFile

# O Python embutido no Windows usa python310._pth e ignora o diretório do script.
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from radai_rectum_jhu_manifest import ARQUIVOS, IDENT

ORGAOS_AUXILIARES = {"prostate", "urinary_bladder"}
SAIDA_SEM_LOCALIZACAO = 3


class SemLocalizacao(ValueError):
    """The coarse/refinement model could not locate its target in this field."""


ESPACAMENTO = (1.7, 1.7, 3.0)
# dimensões XYZ de patch, canais de saída, profundidade, encoder, convoluções por bloco
REDES = {
    "coarse": ((112, 112, 48), 7, 4, "axial", 3),
    "rectum": ((64, 96, 64), 2, 5, "dense", 4),
    "prostate": ((64, 64, 48), 2, 5, "conv", 2),
}


def _pasta(pasta_pesos=None):
    if pasta_pesos is not None:
        return Path(pasta_pesos)
    import radai_models
    return Path(radai_models.pasta_do_modelo(IDENT))


def _arquivos_usados(confirmados):
    nomes = ["model_coarse.pt", "model_fine_rectum.pt", "data_fingerprints.zip"]
    if "prostate" in confirmados:
        nomes.append("model_fine_prostate.pt")
    return nomes


def disponivel(pasta_pesos=None, orgaos_confirmados=()):
    pasta = _pasta(pasta_pesos)
    for nome in _arquivos_usados(orgaos_confirmados):
        arq = pasta / nome
        if not arq.is_file() or arq.stat().st_size != ARQUIVOS[nome]["bytes"]:
            return False, "JHU indisponível: arquivo ausente ou incompleto (%s)." % nome
    return True, ""


def _conferir_pesos(pasta, confirmados):
    for nome in _arquivos_usados(confirmados):
        digest = hashlib.sha256()
        with (pasta / nome).open("rb") as f:
            for bloco in iter(lambda: f.read(1 << 20), b""):
                digest.update(bloco)
        if digest.hexdigest() != ARQUIVOS[nome]["sha256"]:
            raise ValueError("Integridade dos pesos JHU: %s." % nome)


def _estatisticas(pasta, nome):
    with ZipFile(pasta / "data_fingerprints.zip") as z:
        texto = z.read("data_fingerprints/" + nome + "_fingerprint.txt").decode("ascii")
    campos = (linha.split(":", 1) for linha in texto.splitlines() if linha.strip())
    return {chave.strip(): float(valor) for chave, valor in campos}


def _normalizar(tensor, est):
    return (tensor.clamp(est["0.5 percentile"], est["99.5 percentile"]) - est["mean"]) / est["std"]


def _carregar_rede(nome, pasta, dispositivo):
    import torch
    from radai_rectum_jhu_rede import GenericUnet
    dim, saidas, niveis, bloco, repeticoes = REDES[nome]
    modelo = GenericUnet(in_channels=1, out_channels=saidas, img_size=dim, norm_name="INSTANCE",
                         num_layers=niveis, encoder_block=bloco, encoder_units=repeticoes)
    arq = "model_coarse.pt" if nome == "coarse" else "model_fine_" + nome + ".pt"
    modelo.load_state_dict(torch.load(pasta / arq, map_location="cpu", weights_only=True), strict=True)
    return modelo.eval().to(dispositivo)


def _maior_componente(mascara):
    import numpy as np
    from scipy import ndimage as ndi
    fatias = ndi.find_objects(mascara, max_label=1)[0]
    if fatias is None:
        return np.zeros_like(mascara, dtype=bool)
    rotulos, _ = ndi.label(mascara[fatias], np.ones((3,) * mascara.ndim, dtype=bool))
    maior = int(np.bincount(rotulos.ravel())[1:].argmax()) + 1
    saida = np.zeros_like(mascara, dtype=bool)
    saida[fatias] = rotulos == maior
    return saida


def _corpo(volume):
    from scipy.ndimage import binary_fill_holes
    from skimage.filters import threshold_otsu
    import numpy as np
    proj = volume.max(axis=2)
    if proj.max() == proj.min():
        raise SemLocalizacao("TC uniforme no localizador de corpo JHU.")
    corpo = _maior_componente(binary_fill_holes(proj > threshold_otsu(proj)))
    x, y = np.where(corpo)
    if not x.size or x.min() == x.max() or y.min() == y.max():
        raise SemLocalizacao("Sem corpo na projeção da TC para o localizador JHU.")
    # Mesmo extremo superior exclusivo do body_crop dos autores.
    return (slice(int(x.min()), int(x.max())), slice(int(y.min()), int(y.max())), slice(None))


def _refinar(nome, volume, prob, localizacao, pasta, dispositivo):
    import numpy as np
    import torch
    from scipy.ndimage import gaussian_filter
    pontos = np.where(_maior_componente(localizacao))
    if not pontos[0].size:
        raise SemLocalizacao("Localizador JHU sem volume de %s." % nome)
    dim = np.array(REDES[nome][0], dtype=int)
    shape = np.array(volume.shape, dtype=int)
    centro = np.rint([v.mean() for v in pontos]).astype(int)
    comeco = np.clip(centro - dim // 2, 0, np.maximum(shape - dim, 0))
    fim = np.minimum(comeco + dim, shape)
    caixa = tuple(slice(int(a), int(b)) for a, b in zip(comeco, fim))
    # ROI pode atravessar uma aquisição parcial: preenche apenas o espaço fora do
    # campo com ar; o retorno conserva exclusivamente os voxels adquiridos.
    regiao = tuple(slice(0, int(n)) for n in fim - comeco)
    realce = 0.5 - np.abs(gaussian_filter(prob, 5) - 0.5).round(3)
    maximo = float(realce.max())
    if maximo <= 0:
        raise SemLocalizacao("Mapa de probabilidade do refinamento JHU degenerado.")
    patch = np.full(tuple(dim), -1000., dtype=np.float32)
    patch[regiao] = volume[caixa] * (0.5 + 1.5 * (realce[caixa] - realce.min()) / maximo)
    entrada = _normalizar(torch.from_numpy(patch), _estatisticas(pasta, nome + "_enhanced"))
    rede = _carregar_rede(nome, pasta, dispositivo)
    pred = rede(entrada[None, None].to(dispositivo)).argmax(dim=1)[0].cpu().numpy()
    saida = np.zeros(volume.shape, dtype=bool)
    saida[caixa] = pred[regiao] != 0
    return saida, bool(np.any(shape < dim))


def _inferir(entrada, destino, pasta, dispositivo, confirmados):
    import numpy as np
    import torch
    import nibabel as nib
    from nibabel.processing import resample_from_to
    import monai.transforms as mt
    from monai.inferers import sliding_window_inference
    transform = mt.Compose([mt.LoadImage(image_only=True), mt.EnsureChannelFirst(),
                            mt.Orientation(axcodes="RAS"), mt.Spacing(pixdim=ESPACAMENTO, mode="bilinear"),
                            mt.EnsureType()])
    image = transform(str(entrada))
    affine = image.affine.cpu().numpy().copy()
    full = image[0].cpu().numpy()
    corpo = _corpo(full)
    volume = np.ascontiguousarray(full[corpo])
    if not np.isfinite(volume).all():
        raise ValueError("A TC contém valores não finitos no localizador pélvico.")
    with torch.inference_mode():
        coarse = _carregar_rede("coarse", pasta, dispositivo)
        ent = _normalizar(torch.from_numpy(volume), _estatisticas(pasta, "five_label"))
        logits = sliding_window_inference(ent[None, None], REDES["coarse"][0], 1, coarse, overlap=0.5,
                                          mode="gaussian", sw_device=dispositivo, device="cpu")[0]
        probs = logits.softmax(dim=0).numpy()
        hard = logits.argmax(dim=0).numpy()
        del coarse, logits, ent
        reto, parcial = _refinar("rectum", volume, probs[3], hard == 3, pasta, dispositivo)
        aplicados = set()
        if "prostate" in confirmados and np.any(hard == 1):
            prostata, _ = _refinar("prostate", volume, probs[1], hard == 1, pasta, dispositivo)
            reto &= ~prostata
            aplicados.add("prostate")
        if "urinary_bladder" in confirmados and np.any(hard == 2):
            reto &= hard != 2
            aplicados.add("urinary_bladder")
    resolucao_modelo = np.zeros(full.shape, dtype="uint8")
    resolucao_modelo[corpo] = reto
    img = nib.Nifti1Image(resolucao_modelo, affine)
    original = nib.load(str(entrada))
    nat = resample_from_to(img, (original.shape, original.affine), order=0)
    final = _maior_componente(np.asarray(nat.dataobj, dtype=np.uint8))
    if not final.any():
        raise SemLocalizacao("Refinador JHU sem volume de reto na TC.")
    nib.save(nib.Nifti1Image(final.astype(np.uint8), original.affine), str(destino))
    return {
        "dispositivo_usado": str(dispositivo),
        "regiao_fina_com_padding": parcial,
        "orgaos_confirmados": sorted(confirmados),
        "orgaos_auxiliares_aplicados": sorted(aplicados),
        "espacamento_rede_xyz_mm": list(ESPACAMENTO),
    }


def _dispositivo(pedido):
    import torch
    nome = str(pedido or "cpu").strip().lower().replace("gpu", "cuda")
    if nome in ("auto", "cuda"):
        nome = "cuda:0" if torch.cuda.is_available() else "cpu"
    if nome.startswith("cuda") and not torch.cuda.is_available():
        return torch.device("cpu")
    if nome == "mps" and not torch.backends.mps.is_available():
        return torch.device("cpu")
    return torch.device(nome)


def _worker(entrada, destino, pasta, dispositivo, confirmados):
    import gc
    import torch
    try:
        threads = max(1, int(os.environ.get("RADAI_THREADS") or os.environ.get("OMP_NUM_THREADS") or min(6, os.cpu_count() or 1)))
        torch.set_num_threads(threads)
    except ValueError:
        pass
    _conferir_pesos(pasta, confirmados)
    dev = _dispositivo(dispositivo)
    try:
        return _inferir(entrada, destino, pasta, dev, confirmados)
    except RuntimeError as exc:
        motivo = str(exc)
        if dev.type == "cpu" or not any(k in motivo.lower() for k in ("cuda","mps","out of memory","cudnn")):
            raise
    gc.collect()
    if dev.type == "cuda":
        torch.cuda.empty_cache()
    resultado = _inferir(entrada, destino, pasta, torch.device("cpu"), confirmados)
    resultado["recuo_cpu"] = motivo[:200]
    return resultado


def segmentar(ref, dispositivo="cpu", python_exe=None, pasta_pesos=None, log=None, orgaos_confirmados=(), base_ts=None):
    """Retorna máscara booleana ZYX e metadados físicos, na grade de ref (SimpleITK).

    A função espera uma TC em HU já identificada como pelve. O refinador usa o
    mapa do próprio reto. Somente órgãos explicitamente confirmados pelo chamador
    podem participar da precedência opcional do executor masculino publicado.
    """
    import numpy as np
    import radai_cache_tasks as cache
    if ref.GetDimension() != 3 or ref.GetNumberOfComponentsPerPixel() != 1 or min(ref.GetSize()) < 2:
        raise ValueError("O motor JHU requer TC volumétrica escalar 3D.")
    confirmados = set(orgaos_confirmados or ())
    if confirmados - ORGAOS_AUXILIARES:
        raise ValueError("Órgão de arbitragem desconhecido para o JHU.")
    pasta = _pasta(pasta_pesos).resolve()
    def fontes():
        app = Path(__file__).parent
        return ([pasta / nome for nome in _arquivos_usados(confirmados)] +
                [Path(__file__), app / "radai_rectum_jhu_rede.py", app / "radai_rectum_jhu_manifest.py"])

    versao = "JHU-nativo-v1:" + ",".join(sorted(confirmados))
    import radai_recortes_ct as campos
    def predizer(imagem, caixa=None):
        dados = {}
        forma = tuple(reversed(imagem.GetSize()))
        limites = ((0, 0, 0, *forma) if caixa is None else
                   tuple(a for a, _ in caixa["zyx"]) + tuple(b for _, b in caixa["zyx"]))
        def executar():
            mask, detalhes = _segmentar_novo(imagem, dispositivo, python_exe, pasta, log, confirmados)
            if caixa:
                campos.conferir_saida(mask, ref, caixa)
            dados.update(detalhes)
            return mask.astype(np.uint8, copy=False)
        mask = cache.rotulos_de_motor("jhu_rectum", limites, forma, dispositivo, versao,
                                     fontes, executar, dados=dados)
        if mask.shape != forma or mask.dtype != np.uint8 or mask.max() != 1:
            raise ValueError("Mapa de reto JHU vazio ou incompatível com a TC.")
        if dados.get("do_cache") and log:
            log("Reto Johns Hopkins recuperado do cache desta TC.")
        return mask.astype(bool, copy=False), dados

    if base_ts is not None and not confirmados:
        caixa, motivo = campos.propor("jhu_rectum", ref, base_ts, None)
        if caixa:
            cortes = tuple(slice(a, b) for a, b in caixa["zyx"])
            try:
                mask, dados = predizer(ref[cortes[::-1]], caixa)
                campos.conferir_saida(mask, ref, caixa)
                inteira = np.zeros(tuple(reversed(ref.GetSize())), dtype=bool)
                inteira[cortes] = mask
                dados["recorte_pelve"] = caixa
                if log:
                    log("Reto Johns Hopkins: pelve com 80 mm de margem, %.1f%% dos voxels." % (100 * caixa["fracao"]))
                return inteira, dados
            except (ValueError, campos.CampoCompletoNecessario, cache.ReprocessamentoSemMapa) as exc:
                motivo = str(exc)
        if log:
            log("Reto Johns Hopkins: campo completo — " + motivo)
    return predizer(ref)


def _segmentar_novo(ref, dispositivo, python_exe, pasta, log, confirmados):
    import numpy as np
    import SimpleITK as sitk
    ok, erro = disponivel(pasta, confirmados)
    if not ok:
        raise RuntimeError(erro)
    if log:
        log("JHU/MICA: localizando a pelve e refinando o reto.")
    inicio = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="radai_jhu_") as temp:
        raiz = Path(temp)
        entrada, saida, info = raiz / "tc.nii", raiz / "reto.nii.gz", raiz / "detalhes.json"
        sitk.WriteImage(ref, str(entrada))
        cmd = [str(python_exe or sys.executable), str(Path(__file__).resolve()), str(entrada), str(saida),
               str(info), str(pasta), str(dispositivo or "cpu")] + sorted(confirmados)
        ambiente = dict(os.environ, PYTHONIOENCODING="utf-8:replace")
        registro = raiz / "worker.log"
        with registro.open("wb") as err:
            proc = subprocess.run(cmd, stdout=err, stderr=subprocess.STDOUT, env=ambiente,
                                  cwd=str(raiz), timeout=7200,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode or not info.is_file() or not saida.is_file():
            linhas = registro.read_text(encoding="utf8", errors="replace").strip().splitlines()
            if proc.returncode == SAIDA_SEM_LOCALIZACAO:
                raise SemLocalizacao(linhas[-1][:380] if linhas else "Localizador JHU sem volume.")
            raise RuntimeError("Falha do motor de reto JHU: " + (linhas[-1][:380] if linhas else "sem máscara."))
        dados = json.loads(info.read_text(encoding="utf8"))
        imagem = sitk.ReadImage(str(saida))
        if (imagem.GetSize() != ref.GetSize()
                or not np.allclose(imagem.GetOrigin(), ref.GetOrigin(), rtol=0, atol=.001)
                or not np.allclose(imagem.GetSpacing(), ref.GetSpacing(), rtol=0, atol=.0001)
                or not np.allclose(imagem.GetDirection(), ref.GetDirection(), rtol=0, atol=.0001)):
            raise ValueError("Máscara JHU em grade física diferente da TC.")
        mask = sitk.GetArrayFromImage(imagem).astype(bool, copy=False)
    iz, iy, ix = np.where(mask)
    if not len(iz):
        raise ValueError("Máscara JHU sem reto na grade da TC.")
    origem = ref.GetOrigin()
    direcao = np.asarray(ref.GetDirection()).reshape(3, 3)
    esp = np.asarray(ref.GetSpacing())
    eixos = direcao[2] * esp
    zi = origem[2] + ix * eixos[0] + iy * eixos[1] + iz * eixos[2]
    toca_borda = any(v.min() == 0 or v.max() == n - 1 for v, n in zip((ix, iy, iz), ref.GetSize()))
    dados.update(
        segundos=round(time.perf_counter() - inicio, 3),
        dispositivo_solicitado=str(dispositivo or "cpu"),
        voxels=int(len(iz)),
        volume_ml=round(len(iz) * float(np.prod(esp)) * .001, 3),
        z_lps_caudal_mm=float(zi.min()),
        z_lps_cranial_mm=float(zi.max()),
        toca_borda_da_TC=toca_borda,
    )
    if log:
        log("Reto JHU: %.1f mL em %.1f s (%s)." % (dados["volume_ml"],dados["segundos"],dados["dispositivo_usado"]))
    return mask, dados


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for nome in ("entrada", "saida", "info", "pasta", "dispositivo"):
        parser.add_argument(nome)
    parser.add_argument("orgaos", nargs="*")
    args = parser.parse_args()
    try:
        res = _worker(Path(args.entrada), Path(args.saida), Path(args.pasta), args.dispositivo, set(args.orgaos))
    except SemLocalizacao as exc:
        print(str(exc), flush=True)
        sys.exit(SAIDA_SEM_LOCALIZACAO)
    Path(args.info).write_text(json.dumps(res, ensure_ascii=False), encoding="utf8")

