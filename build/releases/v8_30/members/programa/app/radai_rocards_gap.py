"""Interpolation of strictly internal axial gaps on the native LPS voxel lattice."""

import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator

MAX_PLANOS_VAZIOS = 4
MAX_ANCORAS_MM = 15.0


def _component(plane):
    labels, n = ndi.label(plane, np.ones((3, 3), bool))
    if n != 1:
        return None
    coords = np.argwhere(labels)
    center = coords.mean(axis=0)
    return center, coords


def _offsets(center, ct, chambers, k, spacing, reference_hu, taper):
    # Search a physical disk, favouring proximity to the arc and attenuation
    # similar to its two anchors. Bone-like peaks cannot dominate the score.
    offsets = np.array([(x, y) for x in range(-2, 3) for y in range(-2, 3)
                        if x*x + y*y <= 4], dtype=float) * taper
    xy = center + offsets / spacing
    hu = ndi.map_coordinates(ct[:, :, k], xy.T, order=1, mode="nearest",
                             output=np.float32)
    cost = np.minimum(np.abs(hu - reference_hu), 120) / 120
    cost += 0.20 * np.sum(offsets**2, axis=1)
    if chambers is not None:
        # Penalise chamber interiors softly: the chamber model can be inaccurate.
        inside = ndi.map_coordinates((chambers[:, :, k] > 0).astype(np.float32),
                                     xy.T, order=1, mode="nearest")
        cost += inside * 0.85
    return offsets[np.argmin(cost)]


def _section(coords, spacing):
    lo, hi = coords.min(axis=0) - 3, coords.max(axis=0) + 4
    mask = np.zeros(hi - lo, dtype=bool)
    mask[tuple((coords - lo).T)] = True
    sdf = ndi.distance_transform_edt(mask, sampling=spacing)
    sdf -= ndi.distance_transform_edt(~mask, sampling=spacing)
    return sdf, coords.mean(axis=0) - lo


def _paint(out, center, t, sections, radius):
    lo = np.maximum(0, np.floor(center - radius).astype(int))
    hi = np.minimum(out.shape, np.ceil(center + radius).astype(int) + 1)
    if np.any(hi <= lo):
        return
    grid = np.indices(hi-lo).reshape(2, -1) + (lo - center)[:, None]
    field = np.zeros(grid.shape[1])
    for (sdf, anchor), weight in zip(sections, (1-t, t)):
        field += weight * ndi.map_coordinates(sdf, grid + anchor[:, None], order=1,
                                              mode="constant", cval=-100.0)
    out[lo[0]:hi[0], lo[1]:hi[1]] |= (field.reshape(hi-lo) >= 0).astype(np.uint8)


def interpolar(da, ct, spacing, chambers=None):
    """Return a copy plus a trace; input is XYZ in canonical LPS and CT in HU."""
    if da.ndim != 3 or da.shape != ct.shape or (chambers is not None and chambers.shape != da.shape):
        raise ValueError("A DA, a TC e as câmaras exigem a mesma grade XYZ.")
    spacing = np.asarray(spacing, dtype=float)
    if spacing.shape != (3,) or not np.isfinite(spacing).all() or np.any(spacing <= 0):
        raise ValueError("Espaçamento físico inválido.")
    if not np.logical_or(da == 0, da == 1).all():
        raise ValueError("A entrada DA exige uma máscara binária.")
    out = da.astype(np.uint8, copy=True)
    observed = np.flatnonzero(np.any(da, axis=(0, 1)))
    trace = {"planos_preditos": observed.tolist(), "planos_interpolados": [],
             "lacunas": [], "fonte": "ROCardS LAD",
             "metodo_interpolacao": "PCHIP e secções nativas com ajuste local TC/câmaras"}
    for a, b in zip(observed[:-1], observed[1:]):
        if b == a+1:
            continue
        row = {"ancoras": [int(a), int(b)], "distancia_axial_mm": float((b-a)*spacing[2])}
        trace["lacunas"].append(row)
        if b-a-1 > MAX_PLANOS_VAZIOS or row["distancia_axial_mm"] > MAX_ANCORAS_MM + 1e-4:
            row["estado"] = "lacuna extensa preservada"
            row["limite_planos_vazios"] = MAX_PLANOS_VAZIOS
            row["limite_ancoras_mm"] = MAX_ANCORAS_MM
            continue
        # Two consecutive, unambiguous observations on each side are required
        # to estimate endpoint direction, otherwise the gap stays open.
        knots = np.array([a-1, a, b, b+1])
        if knots[0] < 0 or knots[-1] >= da.shape[2]:
            row["estado"] = "sem trajetoria bilateral"
            continue
        anchors = [_component(da[:, :, z]) for z in knots]
        if any(anchor is None for anchor in anchors):
            row["estado"] = "ancoras ausentes ou ambiguas"
            continue
        centers = np.array([x[0] for x in anchors])
        curve_mm = centers*spacing[:2]
        displacement = curve_mm[2] - curve_mm[1]
        distance = np.linalg.norm(displacement)
        support_radius = max(np.sqrt(len(anchors[i][1])*spacing[:2].prod()/np.pi) for i in (1, 2))
        if distance > 2*support_radius:
            direction = displacement/distance
            tangents = np.array([curve_mm[1]-curve_mm[0], curve_mm[3]-curve_mm[2]])
            progress = tangents @ direction
            if np.any(progress < -support_radius) or np.max(progress) < 0.2*min(spacing[:2]):
                row["estado"] = "trajetorias vizinhas incompativeis"
                continue
        curve = PchipInterpolator(knots*spacing[2], curve_mm, axis=0)
        coords = [anchors[i][1] for i in (1, 2)]
        reference_hu = [float(np.median(ct[p[:, 0], p[:, 1], k])) for p, k in zip(coords, (a, b))]
        sections = [_section(c, spacing[:2]) for c in coords]
        radius = np.max([np.max(np.abs(p - p.mean(axis=0)), axis=0) for p in coords], axis=0) + 2
        ks = np.arange(a, b+1)
        shifts = np.zeros((len(ks), 2))
        for j, k in enumerate(ks[1:-1], 1):
            t = (k-a)/(b-a)
            center = curve(k*spacing[2]) / spacing[:2]
            shifts[j] = _offsets(center, ct, chambers, k, spacing[:2],
                                 np.interp(t, [0, 1], reference_hu), np.sin(t*np.pi))
        movement = PchipInterpolator(ks, shifts, axis=0)
        marks = []
        for k in ks[1:-1]:
            # Sweep physical cross sections through the slice thickness to
            # represent steep vessels, up to the first/last measured surface.
            left = a if k == a+1 else k-0.5
            right = b if k == b-1 else k+0.5
            sample = np.linspace(left, right, 9)
            midline = curve(sample*spacing[2]) + movement(sample)
            length = np.linalg.norm(np.diff(midline, axis=0), axis=1).sum()
            n = max(3, int(np.ceil(length / (0.35 * min(spacing[:2])))) + 1)
            for z in np.linspace(left, right, n):
                center = (curve(z*spacing[2]) + movement(z)) / spacing[:2]
                _paint(out[:, :, k], center, (z-a)/(b-a), sections, radius)
            if out[:, :, k].any():
                marks.append(int(k))
        row.update(estado="interpolada" if len(marks) == b-a-1 else "parcial",
                   planos=marks, ajuste_max_mm=float(np.linalg.norm(shifts, axis=1).max()),
                   camaras_usadas=chambers is not None)
        trace["planos_interpolados"].extend(marks)
    trace["n_planos_interpolados"] = len(trace["planos_interpolados"])
    trace["voxels_interpolados"] = int(np.count_nonzero(out) - np.count_nonzero(da))
    return out, trace

