import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))


def collect(path, plugin_id):
    import radai_plugin_bootstrap as bootstrap
    import tempfile
    if Path(path).is_dir():
        folder = Path(path)
        raw_manifest = (folder / 'release-manifest.json').read_bytes()
        manifest = json.loads(raw_manifest)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as output:
            output.writestr('release-manifest.json', raw_manifest)
            for record in manifest['files']:
                output.write(folder / record['path'], record['path'])
        buffer.seek(0)
        path = buffer
    with zipfile.ZipFile(path) as package, tempfile.TemporaryDirectory(prefix='suite-seed-check-') as temporary:
        from radai_lung_install import archive_prefix
        prefix = archive_prefix(package)
        bootstrap._extract(package, Path(temporary), plugin_id, code_only=True)
        manifest = json.loads(package.read(prefix+'release-manifest.json'))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
            for name in ['release-manifest.json'] + sorted(row['path'] for row in manifest['files']):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                output.writestr(info, package.read(prefix+name), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    raw = stream.getvalue()
    if plugin_id == 'neuro-rt':
        import radai_neuro_install as sdk
        sdk._load_private_installer()
        policy = sys.modules['_radai_neuro_bootstrap.plugin_consent'].policy()
    else:
        import radai_lung_install as sdk
        policy = sdk.CONSENT_POLICY
    return {'version': manifest['version'], 'sha256': hashlib.sha256(raw).hexdigest(),
            'policy': policy, 'archive': base64.b64encode(zlib.compress(raw, 9)).decode('ascii')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--neuro', required=True)
    parser.add_argument('--lung', required=True)
    args = parser.parse_args()
    seeds = {key: collect(path, key) for key, path in [('neuro-rt', args.neuro), ('lung-rt', args.lung)]}
    (ROOT / 'app/radai_plugin_seeds.py').write_text('SEEDS = ' + repr(seeds) + '\n', encoding='utf8')
    catalog = {'schema': 'local-suite/plugin-options/1', 'plugins': {}}
    details = {
        'neuro-rt': {'models': ['Glioma – Attention U-Net 3D', 'Glioblastoma pós-operatório (3 sequências)', 'Anatomia – SynthSeg', 'Anatomia – CerebrA / ANTs', 'Máscara cerebral auxiliar (MRI_Brain)', 'Glioblastoma pré-operatório (MRI_GBM)', 'Glioblastoma pós-operatório (1 sequência)', 'Glioma de baixo grau pré-operatório', 'Meningioma pré-operatório', 'Metástase pré-operatório'],
                     'disk_bytes_max': 1543736488, 'payload_bytes': 823872930, 'cache_bytes': 719863558},
        'lung-rt': {'models': ['NV-Reason-CT int4 (TC)', 'MedGemma 1.5 4B Q4_K_M (RX)'],
                    'disk_bytes_max': 6376654748, 'payload_bytes': 6376654748, 'cache_bytes': 0}}
    for key, seed in seeds.items():
        catalog['plugins'][key] = dict(seed['policy'], **details[key])
    (ROOT / 'packager/plugin-options.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: {'version': value['version'], 'sha256': value['sha256']} for key, value in seeds.items()}))


if __name__ == '__main__':
    main()
