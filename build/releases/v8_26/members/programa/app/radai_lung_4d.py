import re
import numpy as np
from scipy import ndimage
from scipy.optimize import linear_sum_assignment


def fase_respiratoria(ds):
    texto = ' '.join(str(ds.get(k, '')) for k in ('SeriesDescription', 'ProtocolName', 'ImageType'))
    if re.search(r'\b(AVG|AVERAGE|MIP|MINIP|CONTRAST|CONTRASTADA|VENOUS|ARTERIAL)\b', texto, re.I):
        return None
    if str(ds.get('ContrastBolusAgent', '')).strip():
        return None
    m = re.search(r'(\d{1,3}(?:[.,]\d+)?)\s*%', texto)
    if m and 0 <= float(m[1].replace(',', '.')) <= 100:
        return float(m[1].replace(',', '.'))
    for key in ('NominalPercentageOfRespiratoryPhase', 'RespiratoryTriggerDelayThreshold'):
        if ds.get(key) is not None:
            try:
                value = float(ds.get(key))
                if 0 <= value <= 100:
                    return value
            except (TypeError, ValueError):
                pass
    if re.search(r'respir|\b4d\b|\bphase\b|\bfase\b', texto, re.I):
        value = ds.get('TemporalPositionIdentifier')
        if value is not None:
            return float(value)
    return None


def componentes(mask, ref, teto=None):
    from engine import MascaraCompacta, _compacta_terminal
    from radai_geom import rotular
    m = _compacta_terminal(mask)
    if m is None or m.caixa is None:
        return
    labels, count = rotular(m._sub)
    if teto is not None and count > teto:
        raise ValueError('As lesões excedem o limite de componentes para o consenso 4D.')
    for component, caixa in enumerate(ndimage.find_objects(labels, max_label=count), 1):
        if caixa is None:
            continue
        sub = labels[caixa] == component
        n = int(np.count_nonzero(sub))
        global_ = tuple(slice(s.start + o.start, s.stop + o.start)
                        for s, o in zip(caixa, m.caixa))
        centro = []
        for eixo in range(3):
            pesos = sub.sum(axis=tuple(j for j in range(3) if j != eixo), dtype=np.int64)
            soma_global = global_[eixo].start * n + int(np.dot(pesos, np.arange(len(pesos))))
            centro.append(soma_global / n)
        center = np.asarray(ref.TransformContinuousIndexToPhysicalPoint(tuple(centro[::-1])))
        yield component, center, n, MascaraCompacta(m.shape, global_, sub)


def associar(fases, ref, distancia_mm=30.0, associacoes=None, medidas_nativas=None):
    from engine import MascaraCompacta, _uniao_compacta
    tracks, previous, masks_out = {}, {}, {}
    nphases = len(fases)
    voxel = float(np.prod(ref.GetSpacing()))
    next_id = 1
    for phase, mask in enumerate(fases):
        if mask is None:
            continue
        components, masks_da_fase = [], {}
        for component, center, n, pedaco in componentes(mask, ref, teto=128):
            components.append((component, center, float(n * voxel)))
            masks_da_fase[component] = pedaco
        native = (medidas_nativas or {}).get(phase, [])
        if native:
            if len(native) != len(components):
                raise ValueError('A referência não preservou as lesões medidas na grade nativa.')
            distance_native = np.linalg.norm(np.array([c[1] for c in components])[:, None, :]
                                            - np.array([n['centro_lps_mm'] for n in native])[None, :, :], axis=2)
            for j, k in zip(*linear_sum_assignment(distance_native)):
                components[j] = (components[j][0], np.asarray(native[k]['centro_lps_mm']), native[k]['volume_mm3'])
        assigned = {}
        keys = list(previous)
        if keys and components:
            distance = np.linalg.norm(np.array([previous[k] for k in keys])[:, None, :]
                                      - np.array([c[1] for c in components])[None, :, :], axis=2)
            for i, j in zip(*linear_sum_assignment(distance)):
                if distance[i, j] <= distancia_mm:
                    assigned[j] = keys[i]
        used = set()
        for j, (component, center, volume) in enumerate(components):
            override = (associacoes or {}).get('%d:%d' % (phase, component))
            if override is not None and (not isinstance(override, str) or not re.fullmatch(r'N\d{3}', override)):
                raise ValueError('Identidade de lesão inválida.')
            key = override or assigned.get(j)
            if key is None:
                while 'N%03d' % next_id in tracks:
                    next_id += 1
                key = 'N%03d' % next_id
                next_id += 1
            if key in used:
                raise ValueError('Duas lesões da mesma fase não podem ter a mesma identidade.')
            used.add(key)
            tracks.setdefault(key, [None] * nphases)[phase] = {
                'fase': phase, 'componente': component, 'centro_lps_mm': center.tolist(),
                'volume_mm3': volume, 'associacao': 'manual' if override else 'sugerida'}
            previous[key] = center
            one = masks_da_fase[component]
            masks_out['GTV_%s_F%02d' % (key, phase + 1)] = one
            name = 'ITV_' + key
            if name in masks_out:
                anterior = masks_out[name]
                caixa = tuple(max(c.stop, d.stop) - min(c.start, d.start)
                              for c, d in zip(anterior.caixa, one.caixa))
                necessario = int(np.prod(caixa))
                if sum(m.bytes_guardados() for m in masks_out.values()) + necessario > 512 << 20:
                    raise ValueError('As lesões excedem a memória reservada para o consenso 4D.')
                masks_out[name] = _uniao_compacta([anterior, one], one.shape)
            else:
                masks_out[name] = MascaraCompacta(one.shape, one.caixa, one._sub.copy())
            if sum(m.bytes_guardados() for m in masks_out.values()) > 512 << 20:
                raise ValueError('As lesões excedem a memória reservada para o consenso 4D.')
    summaries = []
    for key, rows in tracks.items():
        baseline = rows[0]
        for row in rows:
            if row is not None:
                delta = (np.array(row['centro_lps_mm']) - baseline['centro_lps_mm']) if baseline else None
                row['deslocamento_lps_mm'] = delta.tolist() if delta is not None else None
                row['vetor_mm'] = float(np.linalg.norm(delta)) if delta is not None else None
        summaries.append({'id': key, 'fases': rows,
                          'contribuintes': [i for i, x in enumerate(rows) if x is not None],
                          'lacunas': [i for i, x in enumerate(rows) if x is None]})
    return masks_out, summaries


def previa(ref, nodulos=None, pulmoes=None, centro_lps=None):
    import base64
    import io
    from PIL import Image
    import SimpleITK as sitk
    hu = sitk.GetArrayViewFromImage(ref)
    center = np.array(hu.shape) // 2
    if centro_lps is not None:
        center = np.asarray(ref.TransformPhysicalPointToIndex(centro_lps)[::-1])
        center = np.clip(center, 0, np.asarray(hu.shape) - 1)
    views = {}
    for axis, name in enumerate(('axial', 'coronal', 'sagital')):
        cut = np.take(hu, center[axis], axis=axis)
        grey = np.clip((cut + 1000) / 1400 * 255, 0, 255).astype(np.uint8)
        rgb = np.repeat(grey[..., None], 3, axis=2)
        for mask, color in ((pulmoes, (70, 180, 255)), (nodulos, (255, 180, 20))):
            if mask is not None:
                contour = np.take(mask, center[axis], axis=axis).astype(bool)
                contour ^= ndimage.binary_erosion(contour)
                rgb[contour] = color
        image = Image.fromarray(rgb)
        spacing = np.asarray(ref.GetSpacing())[::-1]
        dims = [d for d in range(3) if d != axis]
        width = max(1, int(rgb.shape[1] * spacing[dims[1]] / min(spacing[dims])))
        height = max(1, int(rgb.shape[0] * spacing[dims[0]] / min(spacing[dims])))
        image = image.resize((width, height))
        image.thumbnail((256, 256))
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        views[name] = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
    points = {}
    for mask, name in ((pulmoes, 'pulmoes'), (nodulos, 'nodulos')):
        if mask is not None and np.any(mask):
            from radai_geom import _campo
            boundary = _campo(mask.shape, np.bool_)
            ndimage.binary_erosion(mask, output=boundary)
            n = 0
            for z, plano in enumerate(boundary):
                np.logical_xor(mask[z], plano, out=plano)
                n += np.count_nonzero(plano)
            passo = max(1, n // 1800)
            vistos = 0
            pontos = []
            for z, plano in enumerate(boundary):
                ys, xs = np.nonzero(plano)
                primeiro = -vistos % passo
                for y, x in zip(ys[primeiro::passo], xs[primeiro::passo]):
                    pontos.append(list(ref.TransformIndexToPhysicalPoint((int(x), int(y), z))))
                vistos += len(xs)
            points[name] = pontos
    return {'mpr': views, 'pontos_lps': points}
