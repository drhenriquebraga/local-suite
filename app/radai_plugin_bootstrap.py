import argparse
import base64
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import threading
import time
import zipfile
import zlib

_LOCK = threading.RLock()
_IDS = {'neuro-rt': 'NEURO RT', 'lung-rt': 'LUNG RT'}


def _version(root):
    text = (Path(root) / 'entrega.txt').read_text(encoding='utf-8-sig')
    return next(line.split('=', 1)[1].strip() for line in text.splitlines() if line.startswith('VERSAO='))


def _seed(plugin_id):
    from radai_plugin_seeds import SEEDS
    return SEEDS[plugin_id]


@contextmanager
def seed_source(plugin_id):
    record = _seed(plugin_id)
    raw = zlib.decompress(base64.b64decode(record['archive']))
    if hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise ValueError('Código integrado não corresponde ao instalador da Suite.')
    with tempfile.TemporaryDirectory(prefix='suite-plugin-code-') as folder:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            _extract(archive, Path(folder), plugin_id, code_only=True)
        yield Path(folder)


def _extract(archive, destination, plugin_id, code_only=False):
    import radai_lung_install as safe
    records = archive.infolist()
    if len(records) > 20000 or sum(row.file_size for row in records) > 16 * 1024**3:
        raise ValueError('O pacote excede o tamanho permitido.')
    seen = set()
    for row in records:
        name = row.filename.rstrip('/') if row.is_dir() else row.filename
        safe._inside(destination, name)
        if name.casefold() in seen or stat.S_ISLNK(row.external_attr >> 16) or row.flag_bits & 1:
            raise ValueError('O pacote contém entradas inválidas.')
        seen.add(name.casefold())
    prefix = safe.archive_prefix(archive)
    manifest_name = prefix + 'release-manifest.json'
    if archive.getinfo(manifest_name).file_size > 8 * 1024**2:
        raise ValueError('Inventário excede o limite permitido.')
    manifest_raw = archive.read(manifest_name)
    manifest = json.loads(manifest_raw)
    if manifest.get('plugin_id') != plugin_id:
        raise ValueError('Escolha o pacote correspondente ao plugin.')
    if plugin_id == 'neuro-rt':
        import radai_neuro_install as sdk
        sdk._load_private_installer()
        external = sys.modules['_radai_neuro_bootstrap.external_install']
        sdk._load_private_installer().install_state._manifest_shape(manifest)
        if external.code_inventory_sha256(manifest) not in sdk.TRUSTED_CODE_INVENTORIES:
            raise ValueError('Atualize a Suite para reconhecer este pacote NEURO RT.')
    elif hashlib.sha256(manifest_raw).hexdigest() not in safe.TRUSTED_CODE_INVENTORIES:
        raise ValueError('Atualize a Suite para reconhecer este pacote LUNG RT.')
    code = {row['path']: row for row in manifest['files']}
    assets = {} if code_only else _assets(archive, prefix, code, plugin_id)
    for row in records:
        if not row.filename.startswith(prefix):
            continue
        expected = code.get(row.filename[len(prefix):]) or assets.get(row.filename[len(prefix):])
        if expected and row.file_size != expected['size']:
            raise ValueError('Tamanho do arquivo não corresponde à receita autenticada.')
    for row in records:
        if row.is_dir() or not row.filename.startswith(prefix):
            continue
        name = row.filename[len(prefix):]
        selected = name in code or name == 'release-manifest.json'
        if not code_only:
            selected |= name in assets or name in ('offline-bundle.json', '.lung-offline-preparation.json')
        if not selected:
            continue
        expected = code.get(name) or assets.get(name)
        if expected is None and row.file_size > 8 * 1024**2:
            raise ValueError('Metadados do pacote excedem o limite.')
        target = safe._inside(destination, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with archive.open(row) as source, target.open('xb') as output:
            while block := source.read(1024**2):
                digest.update(block)
                output.write(block)
        if expected and digest.hexdigest() != expected['sha256']:
            raise ValueError('Integridade do arquivo não confirmada.')
    if any(not safe._inside(destination, name).is_file() for name in code):
        raise ValueError('Código incompleto no pacote.')


def _assets(archive, prefix, code, plugin_id):
    def read(name):
        record = code['code/' + name]
        entry = archive.getinfo(prefix + 'code/' + name)
        if entry.file_size != record['size'] or entry.file_size > 8 * 1024**2:
            raise ValueError('Receita de recursos inválida.')
        raw = archive.read(entry)
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Receita de recursos não corresponde ao código autenticado.')
        return json.loads(raw)
    recipe = read('catalog/resource_recipe.json')
    result = {}
    if plugin_id == 'lung-rt':
        result.update(('resources/' + row['path'], row) for row in recipe.get('files', []))
        if 'code/catalog/xray_resources.json' in code:
            xray = read('catalog/xray_resources.json')
            for key in ('runtime', 'model', 'mmproj'):
                row = xray[key]
                result['resources/xray/' + xray['revision'] + '/' + row['filename']] = row
    else:
        for model in recipe['models']:
            relative = 'models/' + model['id'] + '/' + model['revision'] + '/'
            result.update((relative + name, row) for name, row in model['files'].items())
            if 'provenance.json' not in model['files']:
                raw = (json.dumps(model.get('provenance', {}), sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()
                result[relative + 'provenance.json'] = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        downloads = list(recipe['wheels']) + [recipe['downloads'][row['download']] for row in recipe.get('extra_files', {}).values()]
        for row in downloads:
            result['downloads/' + row['sha256'] + '/' + row['filename']] = row
    return result


@contextmanager
def local_source(source, plugin_id):
    path = Path(source).absolute()
    if path.is_file():
        with tempfile.TemporaryDirectory(prefix='suite-plugin-offline-') as folder:
            with zipfile.ZipFile(path) as archive:
                _extract(archive, Path(folder), plugin_id)
            yield Path(folder)
    elif path.is_dir():
        yield path
    else:
        raise ValueError('O pacote selecionado não foi encontrado.')


def _install_code(root, plugin_id, source, progress):
    if plugin_id == 'neuro-rt':
        import radai_neuro_install as sdk
        description = sdk.inspect_local_source(source)
        plan = sdk.prepare_external_plan(dict(description, action='install', code_only=True), source_folder=source)
    else:
        import radai_lung_install as sdk
        plan = sdk.prepare_external_plan({'reports': False}, source_folder=source)
    return sdk.run_external(plan, progress, suite_root=root, host_python=sys.executable)


def seed_for_install(root, plugin_id):
    import radai_lung_install as safe
    record = _seed(plugin_id)
    target = safe._inside(root,'Plugins/'+_IDS[plugin_id]+'/staging/host-code-'+record['sha256'])
    with _LOCK:
        if target.is_dir():
            if plugin_id == 'neuro-rt':
                import radai_neuro_install as sdk
            else:
                sdk = safe
            sdk.inspect_local_source(target)
            return target
        target.parent.mkdir(parents=True,exist_ok=True)
        with seed_source(plugin_id) as source:
            temporary = target.with_name(target.name+'-'+str(time.time_ns()))
            shutil.copytree(source,temporary)
            os.replace(temporary,target)
    return target


def ensure_base(root, plugin_id, *, progress=None, installed_only=True):
    root = Path(root).absolute()
    if plugin_id not in _IDS:
        raise ValueError('Plugin desconhecido.')
    if installed_only and (not (root / 'python/python.exe').is_file() or
            Path(sys.executable).resolve() != (root / 'python/python.exe').resolve()):
        return False
    from radai_plugins import discover_plugin, HOST_CONTRACT
    record = _seed(plugin_id)
    with _LOCK:
        state = discover_plugin(root, plugin_id, {'contract': HOST_CONTRACT, 'version': _version(root)})
        if state['state'] == 'ready':
            current = tuple(map(int, state['active_version'].split('.')))
            if current >= tuple(map(int, record['version'].split('.'))):
                return True
        if state.get('state') not in ('absent', 'ready', 'failed'):
            return False
        with seed_source(plugin_id) as source:
            _install_code(root, plugin_id, source, progress)
        return True


def _accept(root, row):
    record = _seed(row['id'])
    policy = record['policy']
    consent = row.get('consent') or {}
    if row.get('accepted') is not True or consent.get('accepted') is not True or any(
            consent.get(key) != policy[key] for key in ('version', 'digest')):
        raise ValueError('Leia e aceite os termos atuais deste plugin no instalador.')
    if row['id'] == 'neuro-rt':
        import radai_neuro_install as sdk
        provider = sdk.build_provider(root, {'version': _version(root), 'python_executable': sys.executable}, {})
        provider.accept_consent(consent)
    else:
        import radai_lung_install as sdk
        sdk._atomic(sdk._inside(root, 'Plugins/LUNG RT/config/consent.json'), {
            'schema': 'lung-rt/consent-receipt/1', 'accepted': True,
            'version': policy['version'], 'digest': policy['digest'], 'accepted_at': time.time()})


def install_selection(root, selection, progress=None):
    root = Path(root).absolute()
    rows = selection.get('plugins') if isinstance(selection, dict) else None
    if not isinstance(rows, list) or len(rows) > 2:
        raise ValueError('Seleção de plugins inválida.')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get('id') not in _IDS or row['id'] in seen or not isinstance(row.get('source'), str):
            raise ValueError('Seleção de plugins inválida.')
        seen.add(row['id'])
    results = []
    for row in rows:
        plugin_id = row['id']
        emit = lambda event: progress(dict(event, plugin_id=plugin_id)) if progress else None
        try:
            ensure_base(root,plugin_id,progress=emit,installed_only=False)
            _accept(root, row)
            context = seed_source(plugin_id) if row['source'] == 'online' else local_source(row['source'], plugin_id)
            with context as source:
                if plugin_id == 'neuro-rt':
                    import radai_neuro_install as sdk
                    description = sdk.inspect_local_source(source)
                    if row['source'] != 'online' and description.get('kind') != 'offline_bundle':
                        raise ValueError('Escolha o bundle offline completo do NEURO RT, preparado em Pacote para levar.')
                    plan = sdk.prepare_external_plan(dict(description,action='install',resources_only=True),source_folder=source)
                else:
                    import radai_lung_install as sdk
                    if row['source']=='online':
                        state,_ = sdk._active_code(sdk._inside(root,'Plugins/LUNG RT'))
                        plan = sdk.prepare_external_plan({'resources_only':True,'installed_version':state['active_version']})
                    else:
                        plan = sdk.prepare_external_plan({'resources_only':True},source_folder=source)
                    if row['source'] != 'online' and not plan.get('offline'):
                        raise ValueError('Escolha o bundle offline completo do LUNG RT, preparado em Pacote para levar.')
                result = sdk.run_external(plan, emit, suite_root=root, host_python=sys.executable)
            results.append({'id': plugin_id, 'ok': True, 'result': result})
        except Exception as error:
            results.append({'id': plugin_id, 'ok': False, 'reason': str(error)})
            emit({'stage': 'failed', 'reason': str(error)})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite-root', required=True)
    parser.add_argument('--selection')
    parser.add_argument('--base-only', action='store_true')
    args = parser.parse_args()
    def progress(event):
        print(json.dumps(event, ensure_ascii=True), flush=True)
    if args.base_only:
        for plugin_id in _IDS:
            ensure_base(args.suite_root, plugin_id, progress=progress)
        return 0
    if not args.selection:
        parser.error('--selection ou --base-only é obrigatório')
    path = Path(args.selection)
    if path.stat().st_size > 64 * 1024:
        raise ValueError('Seleção excede o limite permitido.')
    results = install_selection(args.suite_root, json.loads(path.read_text(encoding='utf-8-sig')), progress)
    print(json.dumps({'plugins': results}, ensure_ascii=True), flush=True)
    return 0 if all(row['ok'] for row in results) else 1


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
