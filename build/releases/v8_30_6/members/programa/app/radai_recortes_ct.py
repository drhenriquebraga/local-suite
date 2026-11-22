"""Conservative external fields of view for secondary CT tasks after a whole-body base.

All stored bounds are array indices (z, y, x), start inclusive, stop exclusive.
Distances and margins are in millimetres. The native model keeps its localizer.
"""
import math

import numpy as np


LOBES = ("lung_upper_lobe_left", "lung_lower_lobe_left", "lung_upper_lobe_right",
         "lung_middle_lobe_right", "lung_lower_lobe_right")
THORAX = LOBES + ("sternum", "clavicula_left", "clavicula_right", "rib_left_1",
                  "rib_right_1", "rib_left_12", "rib_right_12", "vertebrae_L2")
HEAD = ("skull", "brain", "vertebrae_C1")
NECK = HEAD + ("vertebrae_C5", "vertebrae_C7", "vertebrae_T4", "clavicula_left", "clavicula_right")

# Required labels, cropped axes, context margin and minimum combined extent (z,y,x in mm).
# Breast fields always keep the entire original transverse plane, including arms and lateral tissue.
FIELDS = {
    "breasts": ("tórax bilateral até L2", THORAX, "z", 80, (140, 90, 100)),
    "lung_nodules": ("cinco lobos pulmonares", LOBES, "zyx", 60, (90, 70, 95)),
    "oculomotor_muscles": ("crânio e C1", HEAD, "zyx", 60, (70, 65, 65)),
    "craniofacial_structures": ("crânio e pescoço até T4", NECK, "z", 65, (100, 65, 65)),
    "head_glands_cavities": ("crânio e pescoço até T4", NECK, "z", 65, (100, 65, 65)),
    "head_muscles": ("crânio e pescoço até T4", NECK, "z", 65, (100, 65, 65)),
    "headneck_muscles": ("crânio e pescoço até T4", NECK, "z", 65, (100, 65, 65)),
    "headneck_bones_vessels": ("crânio e pescoço até T4", NECK, "z", 65, (100, 65, 65)),
}

PELVIC_FIELD = ("pelve óssea e bexiga", ("sacrum", "hip_left", "hip_right", "urinary_bladder"),
                "zyx", 80, (75, 65, 95))

# On the original CT grid these tasks obtain their exact anatomical crop from their native localizer.
# An external liver box changed the boundary between segments V and VI on the paired CT benchmark.
NATIVE = {"liver_segments"}

WIDE = {
    "total_v3": "base anatômica de TC",
    "total_v2": "base anatômica alternativa de TC",
    "trunk_cavities": "cavidades até a pelve; conserva o recorte corporal transversal habitual",
    "abdominal_muscles": "músculos extensos de tronco e dorso; conserva o recorte corporal transversal habitual",
    "vertebrae_body": "coluna e discos até os limites adquiridos",
    "lung_vessels": "vasos e traqueia podem ultrapassar o pulmão; mantém o localizador robusto",
    "pleural_pericard_effusion": "líquido extrapulmonar pode estender-se além do pulmão comprimido",
    "hip_implant": "artefatos e hastes longas tornam a anatomia do quadril uma âncora incerta",
    "liver_lesions": "lesões periféricas e exofíticas; mantém o localizador robusto",
    "teeth": "localizador craniofacial próprio em cascata",
}


class CampoCompletoNecessario(RuntimeError):
    """Only the proposed crop failed; repeat the same task on the original image."""


def tamanho_e_passo(ref):
    size = tuple(int(x) for x in reversed(ref.GetSize()))
    spacing = tuple(float(x) for x in reversed(ref.GetSpacing()))
    if (len(size) != 3 or len(spacing) != 3 or min(size) < 2
            or not all(math.isfinite(x) and x > 0 for x in spacing)):
        raise ValueError("dimensão ou espaçamento inválido")
    return size, spacing


def _limites(fonte, nome, shape):
    if nome not in fonte:
        return None
    if hasattr(fonte, "caixa_de"):
        if tuple(fonte.shape) != shape:
            raise ValueError("grade da base difere da TC")
        return fonte.caixa_de(nome)
    mascara = fonte[nome]
    if tuple(mascara.shape) != shape:
        raise ValueError("grade da máscara difere da TC")
    from radai_geom import _limites as limites_ativos
    return limites_ativos(mascara)


def propor_pericardio(ref, raw_da_base, masks_da_base=None, margem_mm=70):
    campo = ("coração do TotalSegmentator", ("heart",), "zyx", margem_mm, (50, 45, 45))
    caixa, motivo = propor("trunk_cavities", ref, raw_da_base, masks_da_base, campo=campo)
    if caixa:
        from totalsegmentator.map_to_binary import class_map
        ids = [i for i, nome in class_map.get("trunk_cavities", {}).items() if nome == "pericardium"]
        if len(ids) != 1:
            return None, "classe pericárdio indisponível"
        caixa.update(rotulo_unico=int(ids[0]))
    return caixa, motivo


def propor(task, ref, raw, masks, campo=None):
    """Use only labels produced by the selected CT base for this series."""
    nome, required, axes, margin, min_extent = campo or (PELVIC_FIELD if task == "jhu_rectum" else FIELDS[task])
    try:
        shape, spacing = tamanho_e_passo(ref)
        direction = np.reshape(ref.GetDirection(), (3, 3))
        if (not np.isfinite(ref.GetOrigin()).all() or not np.isfinite(direction).all()
                or not np.allclose(direction.T @ direction, np.eye(3), atol=1e-4, rtol=0)
                or abs(direction[2, 2]) < 0.98):
            return None, "orientação não axial ou geometria inválida"
        if raw is None and not masks:
            return None, "base de TC indisponível"
        bounds = {}
        for label in required:
            source = raw if raw is not None and label in raw else masks
            box = _limites(source, label, shape) if source is not None else None
            if not box:
                return None, "âncora ausente: " + label
            if (len(box) != 3 or any(not 0 <= lo <= hi < n for (lo, hi), n in zip(box, shape))):
                return None, "limites da âncora incompatíveis com a grade"
            # A marker within 3 mm of the acquisition edge can be a partial organ.
            if any(min(lo, n - 1 - hi) * step <= 3.0 for (lo, hi), n, step in zip(box, shape, spacing)):
                return None, "âncora na borda da aquisição: " + label
            bounds[label] = box
        # LPS increases towards the patient's left even with an in-plane rotation or flipped axis.
        for structure in ("lung_upper_lobe", "lung_lower_lobe", "clavicula", "hip"):
            left = bounds.get(structure + "_left")
            right = bounds.get(structure + "_right")
            if left is not None and right is not None:
                delta = [(sum(l) - sum(r)) * step * .5 for l, r, step in zip(left, right, spacing)]
                if np.dot(direction[0], delta[::-1]) < 30:
                    return None, "lateralidade bilateral inconsistente: " + structure
        union = tuple((min(b[i][0] for b in bounds.values()), max(b[i][1] for b in bounds.values()))
                      for i in range(3))
        if any((hi + 1 - lo) * step < floor for (lo, hi), step, floor in zip(union, spacing, min_extent)):
            return None, "extensão insuficiente das âncoras"
        zyx = []
        for axis, (lo, hi), n, step in zip("zyx", union, shape, spacing):
            pad = math.ceil(margin / step)
            zyx.append((max(0, lo - pad), min(n, hi + 1 + pad)) if axis in axes else (0, n))
        fraction = math.prod(hi - lo for lo, hi in zyx) / math.prod(shape)
        if fraction > 0.85:
            return None, "o recorte pouparia menos de 15% dos voxels"
        return {"task": task, "zyx": tuple(zyx), "ancora": nome, "eixos": axes, "margem_mm": margin,
                "fracao": round(fraction, 4), "rotulos_da_ancora": len(bounds), "medido": False,
                "pelo_corpo": False, "vigiar_faces": True}, ""
    except (AttributeError, TypeError, ValueError, IndexError, ArithmeticError, RuntimeError) as exc:
        return None, "geometria da âncora indisponível (%s)" % type(exc).__name__


def suporte_transversal(ref, base):
    """Bound the imaged tissues and the CT base together, retaining every acquired axial plane."""
    try:
        if base is None or len(base) < 2 or not hasattr(base, "caixa_de"):
            return None, "base anatômica de TC indisponível"
        shape, spacing = tamanho_e_passo(ref)
        if tuple(base.shape) != shape:
            return None, "a base está em outra grade"
        caixas = [base.caixa_de(nome) for nome in base]
        caixas = [caixa for caixa in caixas if caixa is not None]
        if not caixas:
            return None, "sem rótulos da base"
        import SimpleITK as sitk
        hu = sitk.GetArrayViewFromImage(ref)
        suporte = np.zeros(shape[1:], dtype=bool)
        for i in range(0, shape[0], 8):
            suporte |= (hu[i:i + 8] > -700).any(axis=0)
        if not suporte.any():
            return None, "sem suporte de tecidos na TC"
        eixos = [(0, shape[0])]
        for eixo, ocupado in ((1, suporte.any(axis=1)), (2, suporte.any(axis=0))):
            ids = np.flatnonzero(ocupado)
            lo = min(int(ids[0]), min(cx[eixo][0] for cx in caixas))
            hi = max(int(ids[-1]), max(cx[eixo][1] for cx in caixas))
            margem = math.ceil(50.0 / spacing[eixo])
            eixos.append((max(0, lo - margem), min(shape[eixo], hi + margem + 1)))
        fracao = math.prod(b - a for a, b in eixos) / math.prod(shape)
        if fracao > .85:
            return None, "o campo de tecidos e anatomia já ocupa a aquisição transversal"
        return {"zyx": tuple(eixos), "ancora": "anatomia da TC e tecidos no campo transversal",
                "eixos": "yx", "margem_mm": 50, "fracao": round(fracao, 4),
                "medido": False, "vigiar_faces": True}, ""
    except (AttributeError, TypeError, ValueError, RuntimeError, ArithmeticError, IndexError) as exc:
        return None, "suporte transversal indisponível (%s)" % type(exc).__name__


def conferir_saida(rotulos, ref, caixa):
    """Reject empty results and labels within 5 mm of any artificial face, before caching."""
    shape, spacing = tamanho_e_passo(ref)
    zyx = caixa["zyx"]
    expected = tuple(hi - lo for lo, hi in zyx)
    if rotulos.ndim != 3 or rotulos.shape != expected:
        raise CampoCompletoNecessario("a saída diverge da grade proposta")
    if caixa.get("rotulo_unico"):
        rotulos = rotulos == caixa["rotulo_unico"]
    if not np.any(rotulos):
        raise CampoCompletoNecessario("saída vazia no recorte")
    for axis, ((lo, hi), n, step) in enumerate(zip(zyx, shape, spacing)):
        guard = max(1, math.ceil(5.0 / step))
        for artificial, bounds in ((lo > 0, slice(0, guard)), (hi < n, slice(-guard, None))):
            if artificial:
                slab = [slice(None)] * 3
                slab[axis] = bounds
                if np.any(rotulos[tuple(slab)]):
                    raise CampoCompletoNecessario("rótulo a até 5 mm da face artificial no eixo " + "zyx"[axis])
