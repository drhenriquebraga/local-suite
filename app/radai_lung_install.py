import hashlib
import http.client
import errno
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import socket
import ssl
import stat
import sys
import tempfile
import time
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid
import zipfile

PLUGIN_ID = 'lung-rt'
VERSION = '1.1.0'
CONSENT_POLICY = {'schema': 'lung-rt/consent-policy/1', 'version': '1.0', 'title': 'LUNG RT — fase de testes', 'clauses': ['LUNG RT está em fase de testes. As estruturas são sugestões UNAPPROVED e exigem revisão médica.', 'Pré-laudos experimentais podem omitir ou inventar achados e não constituem laudo final. O PDF é identificado como rascunho não verificado; o SR é PRELIMINARY/UNVERIFIED.', 'O processamento é local. NV-Reason-CT int4 requer GPU de pelo menos 6 GB e WebGPU; pode falhar ou ser truncado, com limite de uma hora.', 'O código usa MIT e os pesos NV-Reason-CT OpenMDW 1.1; cada recurso mantém sua licença. Sem serviço pago, nuvem ou fallback CPU.', 'Backup e sincronização são opcionais e devem usar uma pasta autorizada pelo serviço.'], 'digest': '5814e205a7647595e8b5ea5b29e44b7ceb988fe6953ca8e369694c9d48969918'}
TRUSTED_CODE_INVENTORIES = frozenset(['0f2a55cff22b15fb0b786784c0cd548b8d6946ab7eecf2c3b91c525b8defb782', '151c6bbb34f31385bee4edb5b34a2ae32ac76e4a5390c405db78297d56199ba2', '2f14ca1784ae6465f0b7f95020a850359ac80d95b3bdbf5f67165e9c270db4d3', '48d61bbfa8670dd3bca474cd5228f16800a46c47c8bbfdb2a3cbb28ba1954568', '4f7d98ce711a5d7852c69cfb8c8437f93ad2c63a9aacc960d6801e8939419a6a', '60b594f6b1a7c0d9a7fb05a91fd54cd4320f7d77059a00c95c33fc294b3639fd', '65238a8bdf7e1f786faaa4194689c9a3f4091ca690b19f19c928560afb1f0d7a', '8e488c48cd089096fd2d159d579b3c243e2042b4f0ec97d31a3c9b4c8bc224cc', 'a1f1439f83edf1007d3cdb2274f96d08ddfb1d82658a29f38a840bff1b9f1c24', 'acb4dd5473dea4bb328e0fce7b57e1fbcf5dc5435ce045f3d8910df1aa633008', 'b9de130360e87b82994c6773d6446ec71490d35fc1178ad522c9f3601e2049ad', 'e2831bb01be0ce0bcf98dba1b8eb827f7b801d09467e6f9c9011d0981607494d', 'e43df36e728292003401785e8e75d1b3eadc3e9cfdd26ac31b3788a4a1269f3b', 'fe1b5b7866940c7366f858cb20371d9d2c7dfab3a3dfc61078c0e107fa15bbd3'])
GITHUB = 'https://api.github.com/repos/drhenriquebraga/lung-rt/releases/latest'
MIRROR = 'https://drhenriquebraga.com.br/_distribuicao/radioterapia-ai/lung-rt/atualizacoes'
LATEST = 'LUNG_RT_SETUP_LATEST.zip'
MAX_SETUP = 256 * 1024**2
MAX_BUNDLE = 16 * 1024**3


class LungInstallError(ValueError):
    def __init__(self, code, message, *, reason=None, phase=None):
        super().__init__(message)
        self.error_code = code
        self.error_reason = reason
        self.error_phase = phase


def _failure_reason(error):
    if isinstance(error, HTTPError):
        return 'HTTP_%d' % error.code if 100 <= error.code <= 599 else 'HTTP_ERROR'
    cause = error.reason if isinstance(error, URLError) else error
    if isinstance(cause, (TimeoutError, socket.timeout)) or getattr(cause, 'errno', None) == errno.ETIMEDOUT:
        return 'TIMEOUT'
    if isinstance(cause, ssl.SSLError):
        return 'TLS_ERROR'
    if isinstance(cause, socket.gaierror):
        return 'DNS_ERROR'
    if getattr(cause, 'errno', None) == errno.ENOSPC:
        return 'DISK_FULL'
    return 'CONNECTION_FAILED' if isinstance(error, (URLError, http.client.HTTPException)) else 'IO_ERROR'


def suite_identity(root):
    return hashlib.sha256(str(Path(root).resolve()).casefold().encode('utf8')).hexdigest()


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}', value):
        raise ValueError('Versão inválida.')
    return tuple(int(x) for x in value.split('.'))


def _inside(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError('Caminho inválido.')
    parts = relative.replace(chr(92), '/').split('/')
    win = PureWindowsPath(relative)
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {p + str(i) for p in ('COM', 'LPT') for i in range(1,10)}
    if (win.drive or win.root or any(p in ('', '.', '..') or p.endswith((' ', '.')) or
            p.split('.')[0].upper() in reserved for p in parts) or
            any(ord(c) < 32 or c in '<>:"|?*' for c in relative)):
        raise ValueError('Caminho fora do pacote.')
    root = Path(root).absolute()
    path = root.joinpath(*parts)
    for parent in (path, *path.parents):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Links não são permitidos na instalação.')
        if parent == root:
            break
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Caminho fora da instalação.')
    return path


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024**2), b''):
            digest.update(data)
    return digest.hexdigest()


def _json(path, limit=8*1024**2):
    path = Path(path)
    if path.stat().st_size > limit:
        raise ValueError('Metadados excedem o limite.')
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Metadados inválidos.')
    return value


def _atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix='.lung-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _request(url, timeout=12):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password:
        raise ValueError('Endereço de download inválido.')
    return urlopen(Request(url, headers={'User-Agent':'LocalSuite-LungRT/1.0', 'Accept':'application/json'}), timeout=timeout)


def _remote_json(url):
    with _request(url) as stream:
        raw = stream.read(1024**2 + 1)
    if len(raw) > 1024**2:
        raise ValueError('Resposta de atualização excede o limite.')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Resposta de atualização inválida.')
    return value


def _release(version, size, digest, urls, origin):
    _version(version)
    if type(size) is not int or not 0 < size <= MAX_SETUP or not re.fullmatch('[0-9a-f]{64}', str(digest)):
        raise ValueError('Integridade da release não está disponível.')
    return {'version':version,'size':size,'sha256':digest,'urls':urls,'origin':origin}


def lookup_origin(source, fetch=_remote_json):
    if source == 'github':
        data = fetch(GITHUB)
        if data.get('draft') or data.get('prerelease'):
            raise ValueError('Release ainda não publicada.')
        version = str(data['tag_name']).lstrip('v')
        asset = next(a for a in data.get('assets', ()) if a.get('name') == LATEST)
        url = asset['browser_download_url']
        if not url.startswith('https://github.com/drhenriquebraga/lung-rt/releases/download/'):
            raise ValueError('Origem GitHub inválida.')
        return _release(version, asset['size'], str(asset.get('digest','')).removeprefix('sha256:'),
                        [url, MIRROR+'/v'+version+'/'+LATEST], source)
    data = fetch(MIRROR+'/latest.json')
    if data.get('schema') != 'lung-rt-update/1':
        raise ValueError('Manifesto do espelho inválido.')
    version = data['version']
    return _release(version,data['size'],data['sha256'],[MIRROR+'/v'+version+'/'+LATEST],source)


def check_latest(installed=None):
    errors = []
    for source in ('github', 'mirror'):
        try:
            release = lookup_origin(source, _remote_json)
            release['state'] = 'available' if not installed or _version(release['version']) > _version(installed) else 'current'
            return release
        except (OSError, ValueError, KeyError, StopIteration, TypeError):
            errors.append(source)
    return {'state':'unavailable','reason':'Não foi possível consultar os dois servidores. Use um SETUP local ou um bundle offline.','failed_origins':errors}


def _download(urls, destination, size, digest, progress=None, cancelled=None):
    destination = Path(destination)
    if destination.is_file() and destination.stat().st_size == size and _sha(destination) == digest:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    cancelled = cancelled or (lambda: False)
    reason = 'DOWNLOAD_FAILED'
    for url in urls:
        temporary = destination.with_name(destination.name+'.part-'+uuid.uuid4().hex)
        try:
            h, total, reported = hashlib.sha256(), 0, 0.0
            with _request(url,timeout=45) as response, temporary.open('xb') as stream:
                if urlparse(response.geturl()).scheme != 'https':
                    raise LungInstallError('DOWNLOAD_FAILED', 'Redirecionamento inseguro.', reason='UNSAFE_REDIRECT')
                while True:
                    if cancelled():
                        raise ValueError('Instalação cancelada.')
                    data = response.read(1024**2)
                    if not data:
                        break
                    total += len(data)
                    if total > size:
                        raise LungInstallError('DOWNLOAD_FAILED', 'Download excede o tamanho publicado.', reason='SIZE_MISMATCH')
                    stream.write(data)
                    h.update(data)
                    if progress and time.monotonic() - reported > .3:
                        progress({'stage':'downloading','downloaded_bytes':total,'total_bytes':size})
                        reported = time.monotonic()
            if total != size:
                raise LungInstallError('DOWNLOAD_FAILED', 'Integridade do download não confirmada.', reason='SIZE_MISMATCH')
            if h.hexdigest() != digest:
                raise LungInstallError('DOWNLOAD_FAILED', 'Integridade do download não confirmada.', reason='HASH_MISMATCH')
            os.replace(temporary,destination)
            return destination
        except (OSError, ValueError, http.client.HTTPException) as error:
            reason = error.error_reason if isinstance(error, LungInstallError) else _failure_reason(error)
            if cancelled():
                raise ValueError('Instalação cancelada.') from None
        finally:
            if temporary.exists():
                temporary.unlink()
    raise LungInstallError('DOWNLOAD_FAILED', 'Não foi possível baixar um arquivo íntegro. Use o bundle offline.', reason=reason, phase='DOWNLOAD')


def archive_prefix(archive):
    candidates = [row.filename[:-len('release-manifest.json')]
                  for row in archive.infolist() if not row.is_dir()
                  and row.filename.split('/')[-1] == 'release-manifest.json'
                  and row.filename.count('/') <= 2]
    if len(candidates) != 1:
        raise ValueError('Escolha um ZIP que contenha apenas um plugin.')
    return candidates[0]


def package_root(path):
    path = Path(path).absolute()
    if path.is_file():
        return path
    candidates = [path, path/'programa']
    if path.is_dir():
        candidates.extend(child for child in path.iterdir() if child.is_dir())
        candidates.extend(child/'programa' for child in path.iterdir() if child.is_dir())
    matches = {candidate for candidate in candidates
               if _inside(candidate, 'release-manifest.json').is_file()}
    if len(matches) != 1:
        raise ValueError('Escolha a pasta completa de um único plugin.')
    return matches.pop()


class Package:
    def __init__(self,path):
        self.path = package_root(path)
        self.zip = zipfile.ZipFile(self.path) if self.path.is_file() else None
        self.prefix = ''
        if self.zip:
            try:
                entries = self.zip.infolist()
                if len(entries) > 20000 or sum(i.file_size for i in entries) > MAX_BUNDLE:
                    raise ValueError('O instalador excede o limite permitido.')
                if sum(i.file_size for i in entries) > MAX_SETUP:
                    self.prefix = archive_prefix(self.zip)
                    marker = self.zip.getinfo(self.prefix + '.lung-offline-preparation.json')
                    if marker.file_size > 8192:
                        raise ValueError('Metadados do bundle excedem o limite.')
                    record = json.loads(self.zip.read(marker))
                    if not isinstance(record,dict) or record.get('complete') is not True:
                        raise ValueError('Termine de preparar o bundle no START HERE.')
                seen = set()
                for item in entries:
                    name = item.filename.rstrip('/') if item.is_dir() else item.filename
                    _inside(Path(tempfile.gettempdir())/'lung-path-check', name)
                    folded = name.casefold()
                    if folded in seen or stat.S_ISLNK(item.external_attr>>16) or item.flag_bits & 1:
                        raise ValueError('Pacote contém entradas inválidas.')
                    seen.add(folded)
                self.prefix = archive_prefix(self.zip)
            except BaseException:
                self.zip.close()
                raise

    def read(self,name,limit=8*1024**2):
        if self.zip:
            name = self.prefix + name
            if self.zip.getinfo(name).file_size > limit:
                raise ValueError('Artefato excede o limite.')
            return self.zip.read(name)
        path = _inside(self.path,name)
        if path.stat().st_size > limit:
            raise ValueError('Artefato excede o limite.')
        return path.read_bytes()

    def close(self):
        if self.zip:
            self.zip.close()


def _inventory(package):
    raw = package.read('release-manifest.json')
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or manifest.get('schema') != 'lung-rt/release-package/1' or manifest.get('plugin_id') != PLUGIN_ID:
        raise LungInstallError('WRONG_PLUGIN', 'Selecione um SETUP ou bundle do LUNG RT.')
    if digest not in TRUSTED_CODE_INVENTORIES:
        raise LungInstallError('PACKAGE_UNTRUSTED', 'O inventário não está autorizado nesta versão da Local Suite.')
    _version(manifest.get('version'))
    files = manifest.get('files')
    if not isinstance(files,list) or not files:
        raise ValueError('Inventário incompleto.')
    seen = set()
    for entry in files:
        name = entry.get('path','')
        if not name.startswith('code/') or name.casefold() in seen:
            raise ValueError('Inventário inválido.')
        _inside(Path(tempfile.gettempdir())/'lung-code-check',name)
        seen.add(name.casefold())
        if type(entry.get('size')) is not int or not 0 <= entry['size'] <= MAX_SETUP or not re.fullmatch('[0-9a-f]{64}',str(entry.get('sha256',''))):
            raise ValueError('Inventário inválido.')
    if not {'code/module.json','code/integration/local_suite.py','code/catalog/resource_recipe.json'}.issubset(seen):
        raise ValueError('O pacote não contém os componentes obrigatórios.')
    return manifest,digest,raw


def _offline(root, digest, package=None):
    marker = _inside(root, '.lung-offline-preparation.json') if root.is_dir() else None
    if marker is not None and marker.is_file():
        record = _json(marker, 8192)
    elif package is not None and package.zip and package.prefix + '.lung-offline-preparation.json' in package.zip.namelist():
        record = json.loads(package.read('.lung-offline-preparation.json', 8192))
    else:
        return False
    if not isinstance(record,dict):
        raise LungInstallError('BUNDLE_INCOMPLETE', 'Metadados do bundle inválidos.')
    if record is not None:
        if (record.get('schema') != 'lung-rt/offline-preparation/1' or
                record.get('complete') is not True or record.get('code_pin') != digest):
            raise LungInstallError('BUNDLE_INCOMPLETE', 'Termine de preparar o bundle no START HERE.')
        return True
    return False


def _code_bytes(package, entry):
    data = package.read(entry['path'], limit=entry['size'])
    if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise LungInstallError('PACKAGE_INTEGRITY', 'A integridade do código do LUNG RT não confere.')
    return data


def inspect_local_source(folder):
    root = Path(str(folder)).absolute()
    if root.is_dir() and not (root/'release-manifest.json').is_file():
        matches = sorted(root.glob('LUNG_RT_SETUP*.zip'))
        if len(matches) != 1:
            raise ValueError('Escolha a pasta do pacote ou uma pasta com apenas um instalador LUNG RT.')
        root = matches[0]
    package = None
    try:
        package = Package(root)
        root = package.path
        manifest,digest,_ = _inventory(package)
        offline = _offline(root, digest, package)
        for entry in manifest['files']:
            _code_bytes(package, entry)
        return {'state':'ready','source':'local','path':str(root),'version':manifest['version'],
                'inventory_sha256':digest,'offline':offline,
                'format':'offline_bundle' if offline else 'setup_zip' if root.is_file() else 'setup_folder'}
    except (zipfile.BadZipFile, KeyError, UnicodeError, TypeError):
        raise ValueError('Pacote LUNG RT incompleto ou corrompido. Selecione a pasta completa do instalador.') from None
    finally:
        if package is not None:
            package.close()


def prepare_external_plan(payload, *, source_folder=None):
    if not isinstance(payload,dict):
        raise ValueError('Plano inválido.')
    resources_only = payload.get('resources_only', False)
    if type(resources_only) is not bool:
        raise ValueError('Operação de instalação inválida.')
    if resources_only and source_folder is None:
        _version(payload.get('installed_version'))
        return {'schema':'lung-rt/external-plan/1','source':'installed',
                'version':payload['installed_version'],'reports':True,'resources_only':True,'offline':False}
    if source_folder:
        source = inspect_local_source(source_folder)
    else:
        source = check_latest(payload.get('installed_version'))
        if source.get('state') not in ('available','current'):
            raise ValueError(source.get('reason','Release indisponível.'))
        source['source'] = 'online'
    return dict(source,schema='lung-rt/external-plan/1',
                reports=resources_only or payload.get('reports') is True,resources_only=resources_only)


def _install_resource(package, relative, dest, existing, resource, offline, progress):
    if relative.startswith('xray/'):
        filename = relative.rsplit('/', 1)[-1]
        component = 'medgemma-' + ('runtime' if filename.endswith('.zip') else 'mmproj' if filename.startswith('mmproj') else 'model')
    else:
        component = resource.get('id') or 'nv-reason-ct-' + relative.rsplit('/', 1)[-1]
    if not isinstance(component, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,159}', component):
        component = 'report-resource'
    def report(event):
        value = dict(event)
        action = value.get('resource_stage') or value.get('stage', 'preparing')
        value.update(stage='resources', resource_stage=action, component=component)
        if progress:
            progress(value)
    report({'stage':'checking'})
    try:
        return _install_resource_bytes(package, relative, dest, existing, resource, offline, report)
    except Exception as error:
        error.error_component = component
        if not getattr(error, 'error_phase', None):
            error.error_phase = 'RESOURCES'
        if not getattr(error, 'error_reason', None):
            error.error_reason = _failure_reason(error) if isinstance(error, OSError) else 'RESOURCE_INVALID'
        raise


def _install_resource_bytes(package, relative, dest, existing, resource, offline, progress):
    size, digest = resource['size'], resource['sha256']
    if type(size) is not int or size < 0 or not re.fullmatch('[0-9a-f]{64}', str(digest)):
        raise ValueError('Recurso sem integridade publicada.')
    if dest.is_file() and dest.stat().st_size == size and _sha(dest) == digest:
        return
    source = None
    if existing.is_file() and existing.stat().st_size == size and _sha(existing) == digest:
        source = existing.open('rb')
    elif package is not None and package.zip and package.prefix + 'resources/' + relative in package.zip.namelist():
        entry = package.zip.getinfo(package.prefix + 'resources/' + relative)
        if entry.file_size != size:
            raise ValueError('Recurso offline incompleto.')
        source = package.zip.open(entry)
    elif package is not None and not package.zip:
        local = _inside(package.path / 'resources', relative)
        if local.is_file():
            if local.stat().st_size != size:
                raise ValueError('Recurso offline incompleto.')
            source = local.open('rb')
    if source is None:
        if offline:
            raise LungInstallError('LOCAL_RESOURCES_MISSING', 'O bundle não tem todos os recursos de pré-laudo. Prepare o pacote com os modelos.')
        _download(resource.get('urls') or [resource['url']], dest, size, digest, progress)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_name(dest.name + '.part-' + uuid.uuid4().hex)
    try:
        actual = hashlib.sha256()
        total = 0
        with source, temporary.open('xb') as output:
            while block := source.read(1024**2):
                total += len(block)
                if total > size:
                    raise ValueError('Recurso offline excede o tamanho publicado.')
                actual.update(block)
                output.write(block)
        if total != size or actual.hexdigest() != digest:
            raise ValueError('Integridade do recurso offline não confere.')
        os.replace(temporary, dest)
    finally:
        if temporary.exists():
            temporary.unlink()


def _active_code(plugin):
    state = _json(_inside(plugin,'installation.json'))
    if state.get('schema') != 'lung-rt/installation/1' or state.get('state') != 'ready':
        raise ValueError('Atualize o código da Local Suite antes de preparar os pesos.')
    version = state.get('active_version')
    _version(version)
    relative = state.get('code_path','')
    if not (relative == 'versions/'+version or relative.startswith('versions/'+version+'/')):
        raise ValueError('A versão do código ativo não confere.')
    code = _inside(plugin,relative)
    class Current:
        def read(self,name,limit=8*1024**2):
            path = _inside(code,name[5:] if name.startswith('code/') else name)
            if path.stat().st_size > limit:
                raise ValueError('Artefato excede o limite.')
            return path.read_bytes()
    package = Current()
    manifest,digest,_ = _inventory(package)
    if state.get('inventory_sha256') != digest or manifest['version'] != version:
        raise ValueError('O código carregado não corresponde ao inventário autorizado.')
    for entry in manifest['files']:
        _code_bytes(package,entry)
    return state,code


def _prepare_report_resources(plugin, code, previous, package, offline, progress):
    recipe_file = code/'catalog/resource_recipe.json'
    recipe = _json(recipe_file)
    recipe_sha = _sha(recipe_file)
    old_path = previous.get('resources_path')
    old_resources = _inside(plugin,old_path) if old_path else plugin
    resource_path = old_path if old_path and Path(old_path).name.startswith(recipe_sha) else 'resources/'+recipe_sha
    resource_root = _inside(plugin,resource_path)
    files = recipe.get('files',[])
    if not files:
        raise ValueError('Receita de recursos de laudo ausente.')
    for resource in files:
        relative = resource['path']
        if not relative.startswith(('models/','runtimes/')):
            raise ValueError('Destino de recurso inválido.')
        _install_resource(package,relative,_inside(resource_root,relative),
                          _inside(old_resources,relative),resource,offline,progress)
        progress({'stage':'resources','resource_stage':'complete','component':resource.get('id','nv-reason-ct')})
    xray_file = code/'catalog/xray_resources.json'
    if xray_file.is_file():
        xray = _json(xray_file)
        revision = xray.get('revision','')
        if xray.get('schema') != 'lung-rt/xray-resources/1' or not re.fullmatch('[0-9a-f]{40}',revision):
            raise ValueError('Receita RX inválida.')
        for key in ('runtime','model','mmproj'):
            resource = xray[key]
            filename = resource.get('filename','')
            if not filename or '/' in filename or chr(92) in filename:
                raise ValueError('Nome de recurso RX inválido.')
            relative = 'xray/'+revision+'/'+filename
            dest = _inside(plugin,'data/'+relative)
            _install_resource(package,relative,dest,dest,resource,offline,progress)
            progress({'stage':'resources','resource_stage':'complete','component':'medgemma-'+key})
    return {'resources_path':resource_path,'resource_recipe_sha256':recipe_sha,
            'reports_installed':True,'weights_prepared_at':time.time()}


def _run_resources_only(plan, progress, root):
    plugin = _inside(root,'Plugins/LUNG RT')
    previous,code = _active_code(plugin)
    progress = progress or (lambda value:None)
    progress({'stage':'checking'})
    package = None
    version = None
    offline = False
    try:
        if plan.get('source') == 'local':
            package = Package(plan['path'])
            inventory,digest,_ = _inventory(package)
            if inventory['version'] != plan.get('version') or plan.get('inventory_sha256') != digest:
                raise ValueError('O pacote mudou desde a conferência.')
            offline = _offline(package.path,digest,package)
            if not offline:
                raise LungInstallError('EXPECTED_WEIGHT_BUNDLE','Escolha o bundle de pesos completo preparado para levar.')
            version = inventory['version']
        elif plan.get('source') != 'installed' or previous['active_version'] != plan.get('version'):
            raise ValueError('Confira novamente o código carregado antes de preparar os pesos.')
        updates = _prepare_report_resources(plugin,code,previous,package,offline,progress)
        if version:
            updates['resource_bundle_version'] = version
        updates['resource_source'] = 'offline_bundle' if offline else 'online'
        current = _json(plugin/'installation.json')
        for key in ('active_version','code_path','inventory_sha256'):
            if current.get(key) != previous.get(key):
                raise ValueError('O código ativo mudou durante o preparo. Reabra e confira a instalação.')
        if not version and previous.get('resource_recipe_sha256') != updates['resource_recipe_sha256']:
            current.pop('resource_bundle_version',None)
        _atomic(plugin/'installation.json',dict(current,**updates))
        progress({'stage':'complete'})
        return {'state':'ready','active_version':current['active_version'],'resource_bundle_version':version}
    finally:
        if package is not None:
            package.close()


def weights_status(suite_root):
    plugin = _inside(suite_root,'Plugins/LUNG RT')
    try:
        state,code = _active_code(plugin)
        recipe_file = code/'catalog/resource_recipe.json'
        recipe = _json(recipe_file)
        resource_root = _inside(plugin,state['resources_path']) if state.get('resources_path') else plugin
        rows = [(_inside(resource_root,row['path']),row) for row in recipe.get('files',[])]
        xray_file = code/'catalog/xray_resources.json'
        if xray_file.is_file():
            xray = _json(xray_file)
            rows += [(_inside(plugin,'data/xray/'+xray['revision']+'/'+xray[key]['filename']),xray[key])
                     for key in ('runtime','model','mmproj')]
        missing = [row.get('id') or row.get('filename') or row['path'] for path,row in rows
                   if not path.is_file() or path.stat().st_size != row['size']]
        version = state.get('resource_bundle_version')
        if version is not None:
            _version(version)
        return {'state':'ready' if rows and not missing else 'partial' if len(missing)<len(rows) else 'missing',
                'version':version,'recipe_sha256':_sha(recipe_file),'missing_components':missing}
    except (OSError,ValueError,KeyError,TypeError):
        return {'state':'checking','version':None,'recipe_sha256':None,'missing_components':[]}


def run_external(plan, progress, *, suite_root, host_python):
    if not isinstance(plan,dict) or plan.get('schema') != 'lung-rt/external-plan/1':
        raise ValueError('Plano inválido.')
    root = Path(suite_root).absolute()
    if Path(host_python).resolve() != Path(sys.executable).resolve() or sys.version_info[:2] < (3,10):
        raise ValueError('Use o Python existente da Local Suite 8.14 ou posterior.')
    if type(plan.get('resources_only',False)) is not bool:
        raise ValueError('Operação de instalação inválida.')
    if plan.get('resources_only'):
        return _run_resources_only(plan,progress,root)
    plugin = _inside(root,'Plugins/LUNG RT')
    plugin.mkdir(parents=True,exist_ok=True)
    progress = progress or (lambda value:None)
    progress({'stage':'checking'})
    source = plan.get('path')
    if plan.get('source') == 'online':
        current = check_latest()
        if current.get('state') != 'available' or current.get('version') != plan.get('version'):
            raise ValueError('A versão disponível mudou. Confira novamente antes de instalar.')
        source = _inside(plugin,'staging/downloads/'+uuid.uuid4().hex+'.zip')
        _download(current['urls'],source,current['size'],current['sha256'],progress)
    elif plan.get('source') != 'local':
        raise ValueError('Origem inválida.')
    package = Package(source)
    stage = None
    resource_root = None
    active = None
    committed = False
    try:
        inventory,digest,raw = _inventory(package)
        version = inventory['version']
        if version != plan.get('version') or (plan.get('inventory_sha256') and plan['inventory_sha256'] != digest):
            raise ValueError('O pacote mudou desde a confirmação.')
        stage = _inside(plugin,'staging/code-'+uuid.uuid4().hex)
        stage.mkdir(parents=True)
        for count,entry in enumerate(inventory['files'],1):
            data = _code_bytes(package, entry)
            dest = _inside(stage,entry['path'][5:])
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
            progress({'stage':'verifying','completed_files':count,'total_files':len(inventory['files'])})
        (stage/'release-manifest.json').write_bytes(raw)
        module = _json(stage/'module.json')
        if module.get('version') != version or module.get('id') != PLUGIN_ID or module.get('host_contract') != 'local-suite/plugins/1':
            raise ValueError('Contrato do plugin incompatível.')
        stamp = (root/'entrega.txt').read_text(encoding='utf-8-sig')
        host_version = next((line.split('=',1)[1].strip() for line in stamp.splitlines() if line.startswith('VERSAO=')), '')
        if _version(host_version) < _version(module.get('host_min_version','8.14')):
            raise LungInstallError('HOST_INCOMPATIBLE', 'Atualize a Local Suite para a versão exigida pelo LUNG RT.')
        previous = {}
        pointer = _inside(plugin,'installation.json')
        if pointer.is_file():
            previous = _json(pointer)
        if previous.get('active_version') and _version(version) < _version(previous['active_version']):
            raise LungInstallError('CODE_DOWNGRADE_BLOCKED',
                'O código deste pacote é mais antigo. Use o pacote de pesos offline ou um SETUP atualizado.')
        resource_path = previous.get('resources_path')
        old_resources = _inside(plugin,resource_path) if resource_path else plugin
        if plan.get('reports'):
            recipe_file = stage/'catalog/resource_recipe.json'
            recipe = _json(recipe_file)
            resource_path = 'resources/' + _sha(recipe_file) + '-' + uuid.uuid4().hex
            resource_root = _inside(plugin,resource_path)
            files = recipe.get('files',[])
            if not files:
                raise ValueError('Receita de recursos de laudo ausente.')
            for resource in files:
                relative = resource['path']
                if not relative.startswith(('models/','runtimes/')):
                    raise ValueError('Destino de recurso inválido.')
                dest = _inside(resource_root,relative)
                _install_resource(package, relative, dest, _inside(old_resources,relative),
                                  resource, bool(plan.get('offline')), progress)
                progress({'stage':'resources','resource_stage':'complete','component':resource.get('id','nv-reason-ct')})
            xray_file = stage/'catalog/xray_resources.json'
            if xray_file.is_file():
                xray = _json(xray_file)
                revision = xray.get('revision', '')
                if xray.get('schema') != 'lung-rt/xray-resources/1' or not re.fullmatch('[0-9a-f]{40}', revision):
                    raise ValueError('Receita RX inválida.')
                for key in ('runtime','model','mmproj'):
                    resource = xray[key]
                    filename = resource.get('filename', '')
                    if not filename or '/' in filename or chr(92) in filename:
                        raise ValueError('Nome de recurso RX inválido.')
                    relative = 'xray/' + revision + '/' + filename
                    dest = _inside(plugin, 'data/' + relative)
                    _install_resource(package, relative, dest, dest, resource, bool(plan.get('offline')), progress)
                    progress({'stage':'resources','resource_stage':'complete','component':'medgemma-' + key})
        progress({'stage':'activating'})
        code_path = 'versions/' + version + '/' + digest + '-' + uuid.uuid4().hex
        active = _inside(plugin,code_path)
        active.parent.mkdir(parents=True,exist_ok=True)
        os.replace(stage,active)
        stage = None
        state = {'schema':'lung-rt/installation/1','state':'ready','active_version':version,
                 'code_path':code_path,'inventory_sha256':digest,
                 'reports_installed':bool(plan.get('reports') or previous.get('reports_installed')),
                 'activated_at':time.time()}
        for key in ('resource_bundle_version','resource_recipe_sha256','resource_source','weights_prepared_at'):
            if key in previous:
                state[key] = previous[key]
        if plan.get('reports'):
            recipe_sha = _sha(active/'catalog/resource_recipe.json')
            state.update(resource_recipe_sha256=recipe_sha,
                         resource_source='offline_bundle' if plan.get('offline') else 'online',
                         weights_prepared_at=time.time())
            if plan.get('offline'):
                state['resource_bundle_version']=version
            elif previous.get('resource_recipe_sha256') != recipe_sha:
                state.pop('resource_bundle_version',None)
        if resource_path:
            state['resources_path'] = resource_path
        _atomic(pointer,state)
        committed = True
        progress({'stage':'complete'})
        return {'state':'ready','active_version':version}
    finally:
        package.close()
        if stage is not None and stage.exists():
            shutil.rmtree(_inside(plugin,stage.relative_to(plugin).as_posix()))
        if not committed:
            try:
                live = _json(plugin/'installation.json') if (plugin/'installation.json').exists() else {}
            except (OSError, ValueError):
                live = None
            if live is not None:
                for owned, key in ((active,'code_path'), (resource_root,'resources_path')):
                    if owned is None:
                        continue
                    relative = owned.relative_to(plugin).as_posix()
                    if live.get(key) == relative:
                        continue
                    try:
                        checked = _inside(plugin,relative)
                        if checked.is_dir():
                            shutil.rmtree(checked)
                    except (OSError, ValueError):
                        pass
