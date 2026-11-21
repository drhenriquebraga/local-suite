"""Anatomy of a native MR series using the installed NEURO RT scientific worker.

The host writer consumes masks in GDCM slice order (z,y,x), exactly as read
by engine.read_series. Every mask belongs to the selected native T1.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

SYNTHSEG = 'anatomy_synthseg'
CEREBRA = 'anatomy_cerebra_ants'
NOMES_TPS = {
    'brainstem': 'Brainstem', 'hippocampus_left': 'Hippocampus_L',
    'hippocampus_right': 'Hippocampus_R', 'cerebellum': 'Cerebellum',
    'ventricular_system': 'Ventricles', 'thalamus_left': 'Thalamus_L',
    'thalamus_right': 'Thalamus_R', 'amygdala_left': 'Amygdala_L',
    'amygdala_right': 'Amygdala_R', 'globus_pallidus': 'GlobusPallidus',
}
# IDs are native anatomical labels, not positions in a model output tensor.
GRUPOS = {
    SYNTHSEG: ((16,), (17,), (53,), (7, 8, 46, 47), (4, 5, 14, 15, 43, 44),
               (10,), (49,), (18,), (54,), (13, 52)),
    CEREBRA: ((62, 11), (99,), (48,), (2, 20, 39, 46, 50, 53, 71, 90, 97, 101),
              (5, 29, 37, 41, 56, 80, 88, 92), (91,), (40,), (70,), (19,), (27, 78)),
}
_CAMPOS = ('Modality', 'SeriesDescription', 'ProtocolName', 'SequenceName',
           'AcquisitionContrast', 'ScanningSequence', 'SequenceVariant',
           'MRAcquisitionType', 'EchoTime', 'InversionTime', 'FlipAngle',
           'ImageType', 'SOPClassUID', 'SeriesInstanceUID')


def _raiz(raiz_suite):
    return Path(raiz_suite or os.environ.get('RADAI_RAIZ_INSTALACAO') or Path(__file__).parent).resolve()


def _eh_t1(ds):
    import re
    if ds.get('Modality') != 'MR':
        return False
    text = ' '.join(str(ds.get(key, '')).upper().replace('_', ' ')
                    for key in ('SeriesDescription', 'ProtocolName', 'SequenceName', 'ImageType', 'AcquisitionContrast'))
    if re.search(r'\b(?:FLAIR\w*|T2\w*|T1\s*MAP\w*|SWI|DWI|ADC|TOF|MRA|PERFUSION|DIFFUSION|LOCALIZER|SURVEY|SCOUT)\b', text):
        return False
    if re.search(r'\b(?:T1(?:W|C|CE)?|MPRAGE|MP[\s-]?RAGE|BRAVO|SPGR)\b', text):
        return True
    # Inversion-prepared 3D gradient echo. Deidentification may remove the
    # sequence name but preserve these acquisition parameters.
    try:
        return (ds.get('MRAcquisitionType') == '3D' and 'GR' in ds.get('ScanningSequence', ())
                and 'IR' in ds.get('ScanningSequence', ())
                and 0 < float(ds.EchoTime) < 10 and 400 <= float(ds.InversionTime) <= 1500
                and 0 < float(ds.FlipAngle) < 30)
    except (KeyError, AttributeError, TypeError, ValueError):
        return False


def sequencia_t1(stage, uid=None):
    import pydicom
    if not Path(stage).is_dir():
        return False
    for entry in Path(stage).iterdir():
        if not entry.is_file():
            continue
        try:
            ds = pydicom.dcmread(str(entry), specific_tags=_CAMPOS, stop_before_pixels=True, force=True)
        except (OSError, ValueError, EOFError):
            continue
        if ds.get('Modality') == 'MR' and (not uid or str(ds.get('SeriesInstanceUID')) == str(uid)):
            return _eh_t1(ds)
    return False


def disponivel(raiz_suite=None, modelo=SYNTHSEG):
    """Cheap indicator for the form. Verify the code and weights before use."""
    import radai_plugins as plugins
    if modelo not in GRUPOS:
        return False
    try:
        root = _raiz(raiz_suite)
        state = plugins._json(plugins._inside(root, 'Plugins/NEURO RT/installation.json'))
        if state.get('schema') != 'neuro-rt/installation/1' or state.get('state') not in ('ready', 'installed_pending_restart'):
            return False
        version = state['active_version']
        plugins._version(version)
        code = plugins._inside(root, 'Plugins/NEURO RT/versions/' + version)
        resources = state.get('resources') or {}
        adapter = 'synthseg' if modelo == SYNTHSEG else 'cerebra_ants'
        folder = plugins._inside(root / 'Plugins/NEURO RT', resources['model_relative_paths'][modelo])
        required = (('synthseg_model_weights.pth',) if modelo == SYNTHSEG else
                    ('atlas_labels.nii', 'template_t1.nii', 'template_mask.nii'))
        return ((code / 'module.json').is_file() and
                resources.get('capabilities', {}).get(adapter, {}).get('available') is True and
                all((folder / name).is_file() for name in required))
    except (OSError, ValueError, TypeError, KeyError):
        return False


def segmentar(stage, uid, log=None, *, modelo=SYNTHSEG, raiz_suite=None, pasta_trabalho=None, estruturas=None):
    """Run one local model and return only requested, nonempty anatomical ROIs."""
    import numpy as np
    if modelo not in GRUPOS:
        raise ValueError('Modelo de anatomia SNC desconhecido.')
    destinos = list(NOMES_TPS) if estruturas is None else [key for key in NOMES_TPS if key in estruturas]
    meta = {'modelo': modelo, 'faltantes': [], 'nomes': {k: NOMES_TPS[k] for k in destinos}}
    if not destinos:
        return {}, meta
    root = _raiz(raiz_suite)
    if not disponivel(root, modelo):
        raise RuntimeError('NEURO RT ou os pesos de anatomia estão indisponíveis.')
    if not sequencia_t1(stage, uid):
        raise ValueError('A série de RM não contém uma sequência T1 reconhecida para anatomia do SNC.')
    started = time.monotonic()
    if pasta_trabalho is not None:
        Path(pasta_trabalho).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='snc-rm-', dir=pasta_trabalho) as tmp:
        job = Path(tmp)
        data = dict(stage=str(Path(stage).resolve()), uid=str(uid or ''), modelo=modelo,
                    destinos=destinos, raiz_suite=str(root))
        (job / 'entrada.json').write_text(json.dumps(data), encoding='utf-8')
        executable = root / 'python/python.exe'
        if not executable.is_file():
            raise RuntimeError('Python da instalação da Local Suite indisponível.')
        if log:
            log('NEURO RT: ' + modelo)
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        with (job / 'processo.log').open('wb') as stream:
            result = subprocess.run([str(executable), '-I', '-B', str(Path(__file__).resolve()), str(job)],
                                    stdout=stream, stderr=subprocess.STDOUT, creationflags=flags)
        if result.returncode:
            motivo = job / 'erro.txt'
            raise RuntimeError(motivo.read_text(encoding='utf-8') if motivo.is_file()
                               else 'O processo da anatomia SNC foi interrompido.')
        meta.update(json.loads((job / 'resultado.json').read_text(encoding='utf-8')))
        masks = {key: np.load(job / (key + '.npy'), allow_pickle=False)
                 for key in destinos if key not in meta['faltantes']}
    meta['segundos'] = round(time.monotonic() - started, 3)
    return masks, meta


def _executar(job, pedido):
    """Run inside the trusted host Python, isolated from the UI process."""
    import numpy as np
    import SimpleITK as sitk
    import radai_plugins as plugins
    root = Path(pedido['raiz_suite'])
    modelo = pedido['modelo']
    installation = plugins.discover_plugin(root, host_info=plugins._host_info(root, {}))
    if installation['state'] != 'ready':
        raise RuntimeError(installation.get('reason') or 'NEURO RT indisponível.')
    code = Path(installation['code_dir'])
    sys.path.insert(0, str(code))
    from neuro_rt import plugin_consent
    from neuro_rt.contracts import validate_model_result
    from neuro_rt.imaging import geometry, load_input, validate_mask
    from neuro_rt.model_registry import get_model_spec
    from neuro_rt.plugin_paths import resolve_plugin_paths
    from neuro_rt.service import Settings
    from neuro_rt.study_types import SeriesDescriptor
    paths = resolve_plugin_paths(root, installation['installation_state'], host_python=sys.executable)
    if not (plugin_consent.accepted(paths.config_dir, 'first_use') or
            plugin_consent.accepted(paths.config_dir, 'installation')):
        raise RuntimeError('O primeiro uso do NEURO RT requer aceite na tela do plugin.')
    if (code / 'integration/testing_access.py').is_file():
        from integration.testing_access import TestingAccess
        if not TestingAccess(paths.config_dir).allowed(None, 'anatomia'):
            raise RuntimeError('Abra Anatomia no NEURO RT para confirmar o acesso nesta instalação.')
    settings = Settings(code, plugin_paths=paths)
    spec = get_model_spec(modelo)
    if not settings.model_runtime_status(spec)['available']:
        raise RuntimeError('O runtime de anatomia do NEURO RT está indisponível.')
    image, src = load_input(pedido['stage'], pedido['uid'], allowed_modalities=('MR',))
    ref = SeriesDescriptor('T1', src['series_uid'], 'reference', 'study', 'MR',
                           geometry(image), frame_of_reference_uid=src['frame_uid'],
                           sop_instance_uids=src['sop_uids']).to_dict()
    volume = job / 'T1.nii'
    sitk.WriteImage(image, str(volume))
    ident = job / 'identity.tfm'
    sitk.WriteTransform(sitk.Transform(3, sitk.sitkIdentity), str(ident))
    context = dict(model_spec=spec, bindings=[dict(role='T1', series_ticket='T1', association_source='suggested')],
                   reference=ref, series_index={'T1': ref}, authorized_inputs={'T1': str(volume)},
                   source_to_reference={'T1': str(ident)}, models_dir=str(paths.models_dir), device='cpu',
                   allow_legacy_models=False, host_app=str(root), host_python=sys.executable, study_id='snc')
    (job / 'model-context.json').write_text(json.dumps(context), encoding='utf-8')
    command = settings.worker_command('study', ['--task', 'model', '--job-dir', str(job)],
                                      runtime_id=spec['runtime_id'])
    started = time.monotonic()
    with (job / 'modelo.log').open('wb') as out:
        status = subprocess.run(command, cwd=code, stdout=out, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if status.returncode:
        tail = (job / 'modelo.log').read_text(encoding='utf-8', errors='replace').splitlines()
        raise RuntimeError('Falha no motor de anatomia SNC. ' + (tail[-1][:220] if tail else ''))
    inference_seconds = round(time.monotonic() - started, 3)
    result = validate_model_result(json.loads((job / 'model-result.json').read_text(encoding='utf-8')), spec)
    indices = {c['class_id']: c['value'] for c in spec['classes']}
    by_value = {indices[mask.class_id]: mask for mask in result.masks}
    faltantes = []
    for key, group in zip(NOMES_TPS, GRUPOS[modelo]):
        if key not in pedido['destinos']:
            continue
        bits = None
        for index in group:
            mask = by_value.get(index)
            if mask is None:
                continue
            path = Path(mask.path).resolve()
            if not path.is_relative_to(job):
                raise ValueError('Máscara SNC fora da pasta da operação.')
            block = sitk.ReadImage(str(path))
            validate_mask(block, image)
            if bits is None:
                bits = sitk.GetArrayFromImage(block).astype(bool)
            else:
                np.logical_or(bits, sitk.GetArrayViewFromImage(block), out=bits)
        if bits is None or not bits.any():
            faltantes.append(key)
        else:
            np.save(job / (key + '.npy'), bits, allow_pickle=False)
    meta = dict(faltantes=faltantes, versao_neuro=installation['active_version'],
                segundos_motor=inference_seconds, cortes=len(src['sop_uids']))
    (job / 'resultado.json').write_text(json.dumps(meta), encoding='utf-8')


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    pasta = Path(sys.argv[1]).resolve()
    try:
        _executar(pasta, json.loads((pasta / 'entrada.json').read_text(encoding='utf-8')))
    except Exception as exc:
        (pasta / 'erro.txt').write_text(str(exc)[:500], encoding='utf-8')
        raise

