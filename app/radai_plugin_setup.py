import argparse
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

SCHEMA = 'local-suite/plugin-install/1'
LIMIT = 64 * 1024
PLUGINS = {'neuro-rt': ('NEURO RT', 'radai_neuro_install.py', '/neuro'),
           'lung-rt': ('LUNG RT', 'radai_lung_install.py', '/lung')}


def _plain(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Atalho ou redirecionamento de pasta não permitido.')
    return path


def _json(path):
    path = _plain(path)
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('Estado da instalação inválido.')
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Estado da instalação inválido.')
    return value


def _write(path, value):
    path = _plain(path)
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True).encode('utf-8')
    if len(raw) > LIMIT:
        raise ValueError('Plano da instalação excede o limite.')
    handle, temporary = tempfile.mkstemp(prefix='.install-', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class InvalidReadiness(ValueError):
    pass


class SetupError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.error_code = code


def _external_root(root, plugin_id):
    return _plain(Path(root) / 'Plugins' / PLUGINS[plugin_id][0] / 'staging/external')


def last_result(root, plugin_id):
    try:
        return _json(_external_root(root, plugin_id) / 'latest-result.json')
    except (OSError, ValueError):
        return None


def _finish(work, result):
    _write(work / 'result.json', result)
    _write(work.parent / 'latest-result.json', result)


def _cleanup_uploaded_source(root, plugin_id, payload):
    source = payload.get('source')
    path = payload.get('path') or (source.get('folder') if isinstance(source,dict) else None)
    if not isinstance(path,str):
        return
    inbox = _plain(Path(root)/'Plugins'/PLUGINS[plugin_id][0]/'staging/local-setup')
    selected = _plain(path)
    for candidate in (selected,*selected.parents):
        if candidate.parent == inbox and candidate.name.startswith('setup-'):
            if candidate.is_dir():
                shutil.rmtree(candidate)
            return


def _protect(pid):
    import radai_pulso
    radai_pulso.poupar(pid)


def _schedule(callback):
    def finish():
        time.sleep(.75)
        callback()
    worker = threading.Thread(target=finish, name='radai-plugin-shutdown', daemon=False)
    worker.start()


def _environment():
    import radai_lancador
    return radai_lancador.ambiente_do_sucessor()


def _powershell():
    root = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    path = root / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    return str(path) if path.is_file() else 'powershell.exe'


class ExternalInstaller:
    def __init__(self, suite_root, port, shutdown, *, popen=None, protect=None,
                 schedule=None, wait_s=20, plugin_id='neuro-rt'):
        if type(port) is not int or not 0 < port < 65536 or not callable(shutdown):
            raise ValueError('Reabertura controlada indisponível.')
        if plugin_id not in PLUGINS:
            raise ValueError('Plugin não autorizado.')
        self.plugin_id = plugin_id
        self.root = _plain(suite_root).resolve()
        self.port, self.shutdown = port, shutdown
        self.popen, self.protect = popen or subprocess.Popen, protect or _protect
        self.schedule, self.wait_s = schedule or _schedule, wait_s
        self.lock, self.request = threading.Lock(), None

    def launch(self, payload):
        if not isinstance(payload, dict):
            raise ValueError('Plano do plugin inválido.')
        with self.lock:
            if self.request:
                return dict(self.request)
            transaction = uuid.uuid4().hex
            work = _plain(_external_root(self.root, self.plugin_id) / transaction)
            work.mkdir(parents=True, exist_ok=False)
            plan = work / 'plan.json'
            nonce = secrets.token_hex(32)
            envelope = {'schema': SCHEMA, 'plugin_id': self.plugin_id, 'transaction_id': transaction,
                        'nonce': nonce, 'old_pid': os.getpid(), 'port': self.port,
                        'suite_root': str(self.root), 'python': sys.executable, 'payload': payload}
            _write(plan, envelope)
            digest = hashlib.sha256(plan.read_bytes()).hexdigest()
            source = Path(__file__).resolve()
            scripts = (source.parent / 'maintenance/PLUGIN_INSTALL.ps1',
                       source.parent.parent / 'packager/PLUGIN_INSTALL.ps1',
                       source.parent / 'packager/PLUGIN_INSTALL.ps1')
            script = next((p for p in scripts if p.is_file()), None)
            if script is None:
                code = 'HOST_INSTALLER_MISSING'
                message = 'O iniciador do PowerShell está ausente. Repare a instalação da Local Suite com o SETUP da suíte.'
                _message(work, message)
                _finish(work, _diagnostic(work, self.plugin_id, code, 'handoff'))
                raise SetupError(code, message)
            command = [_powershell(), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                       str(script), '-PluginName', PLUGINS[self.plugin_id][0], '-PythonPath', sys.executable, '-WorkerPath', str(source),
                       '-PlanPath', str(plan), '-PlanSha256', digest]
            process = None
            try:
                flags = 0x10 if os.name == 'nt' else 0
                options = {'cwd': str(script.parent), 'close_fds': True, 'env': _environment()}
                try:
                    process = self.popen(command, creationflags=flags | (0x01000000 if os.name == 'nt' else 0), **options)
                except OSError:
                    process = self.popen(command, creationflags=flags, **options)
                self.protect(process.pid)
                worker_pid = self._ready(process, work, nonce)
                self.protect(worker_pid)
                self.schedule(self.shutdown)
            except Exception as error:
                try:
                    _write(work / 'cancel.json', {'nonce': nonce})
                except (OSError, ValueError):
                    pass
                if isinstance(error, InvalidReadiness) and process is not None and process.poll() is None:
                    try:
                        process.terminate()
                    except OSError:
                        pass
                code = ('INSTALLER_INVALID_READY' if isinstance(error, InvalidReadiness) else
                        'INSTALLER_NOT_READY' if process is not None else 'INSTALLER_LAUNCH_FAILED')
                message = 'O instalador externo não confirmou prontidão. A suíte continua aberta.'
                _message(work, message + ' Código: ' + code)
                _finish(work, _diagnostic(work, self.plugin_id, code, 'handoff'))
                raise SetupError(code, message) from None
            self.request = {'ok': True, 'scheduled': True, 'transaction_id': transaction,
                            'state': 'external_install', 'pid': os.getpid()}
            return dict(self.request)

    def _ready(self, process, work, nonce):
        deadline = time.monotonic() + self.wait_s
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            path = work / 'ready.json'
            if path.is_file():
                try:
                    value = _json(path)
                except (OSError, ValueError) as error:
                    raise InvalidReadiness('Sinal do instalador ilegível.') from error
                if (value.get('ready') is True and value.get('nonce') == nonce and
                        value.get('supervisor_pid') == process.pid and
                        type(value.get('worker_pid')) is int and value['worker_pid'] > 0):
                    return value['worker_pid']
                raise InvalidReadiness('Sinal do instalador inválido.')
            time.sleep(.05)
        raise ValueError('O instalador não respondeu.')


def _load_sdk(root, plugin_id='neuro-rt'):
    path = Path(__file__).resolve().with_name(PLUGINS[plugin_id][1])
    spec = importlib.util.spec_from_file_location('_radai_external_installer_sdk', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    runner = getattr(module, 'run_external', None)
    if not callable(runner):
        raise ValueError('O instalador do plugin precisa ser atualizado.')
    return lambda plan, progress: runner(plan, progress, suite_root=root, host_python=sys.executable)


def _wait_old(pid, cancelled):
    import radai_lancador
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if cancelled():
            return False
        if radai_lancador.esperar_sair(pid, .2):
            return True
    return False


def _reopen(root, port, old_pid, plugin_id='neuro-rt'):
    launcher = Path(__file__).resolve().with_name('radai_lancador.py')
    command = [sys.executable, str(launcher), '--url', 'http://127.0.0.1:%d%s' % (port, PLUGINS[plugin_id][2]),
               '--sucessor', str(old_pid), '--abrir-janela']
    process = subprocess.run(command, cwd=launcher.parent, env=_environment(), check=False)
    return process.returncode == 0


def _message(work, text):
    try:
        print(text, flush=True)
    except (OSError, ValueError, UnicodeError):
        pass
    try:
        with _plain(work / 'progress.log').open('a', encoding='utf-8') as stream:
            stream.write(text + '\n')
    except (OSError, ValueError):
        pass


def _diagnostic(work, plugin_id, code='', stage=''):
    return {'ok': False, 'reopened': False, 'error_code': code, 'stage': stage,
            'transaction_id': work.name, 'log': (Path('Plugins') / PLUGINS[plugin_id][0] /
                       'staging/external' / work.name / 'progress.log').as_posix()}


def run_worker(plan_path, expected_sha, supervisor_pid, *, runner=None, wait_old=None, reopen=None):
    plan_path = _plain(plan_path)
    if (not re.fullmatch('[0-9a-f]{64}', expected_sha) or not plan_path.is_file() or
            plan_path.stat().st_size > LIMIT):
        raise ValueError('Integridade do plano não confirmada.')
    raw = plan_path.read_bytes()
    if len(raw) > LIMIT or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha):
        raise ValueError('Integridade do plano não confirmada.')
    envelope = json.loads(raw.decode('utf-8-sig'))
    required = {'schema', 'plugin_id', 'transaction_id', 'nonce', 'old_pid', 'port', 'suite_root', 'python', 'payload'}
    if (not isinstance(envelope, dict) or set(envelope) != required or envelope['schema'] != SCHEMA or envelope['plugin_id'] not in PLUGINS or
            not isinstance(envelope['transaction_id'], str) or not re.fullmatch('[0-9a-f]{32}', envelope['transaction_id']) or
            not isinstance(envelope['nonce'], str) or not re.fullmatch('[0-9a-f]{64}', envelope['nonce']) or
            type(envelope['old_pid']) is not int or envelope['old_pid'] <= 0 or
            type(envelope['port']) is not int or not 0 < envelope['port'] < 65536 or
            not isinstance(envelope['payload'], dict) or type(supervisor_pid) is not int or supervisor_pid <= 0):
        raise ValueError('Plano da instalação inválido.')
    root = _plain(envelope['suite_root']).resolve()
    expected = root / ('Plugins/' + PLUGINS[envelope['plugin_id']][0] + '/staging/external') / envelope['transaction_id'] / 'plan.json'
    if plan_path.resolve() != expected or Path(envelope['python']).resolve() != Path(sys.executable).resolve():
        raise ValueError('O plano não corresponde à suíte ou ao Python em uso.')
    runner = runner or _load_sdk(root, envelope['plugin_id'])
    work = plan_path.parent
    def cancelled():
        path = work / 'cancel.json'
        if not path.exists():
            return False
        try:
            return _json(path).get('nonce') == envelope['nonce']
        except (OSError, ValueError):
            return True
    _message(work, PLUGINS[envelope['plugin_id']][0] + ': usando o Python existente; instalador externo pronto.')
    _write(work / 'ready.json', {'ready': True, 'nonce': envelope['nonce'],
                                'supervisor_pid': supervisor_pid, 'worker_pid': os.getpid()})
    _message(work, 'Aguardando o encerramento controlado da Local Suite...')
    result = _diagnostic(work, envelope['plugin_id'], stage='handoff')
    if not (wait_old or _wait_old)(envelope['old_pid'], cancelled):
        result['error_code'] = 'HOST_STILL_RUNNING'
        _message(work, 'O app não encerrou. Nenhuma instalação foi executada.')
        _finish(work, result)
        return 1
    context = {}
    def progress(value):
        if isinstance(value, dict):
            component = value.get('component')
            if isinstance(component, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,159}', component):
                context['error_component'] = component
            phase = value.get('resource_stage') or value.get('stage')
            if isinstance(phase, str) and re.fullmatch(r'[a-z_]{2,32}', phase):
                context['error_phase'] = phase.upper()
        stages = {'downloading': 'Baixando componentes necessários', 'extracting': 'Copiando arquivos',
                  'verifying': 'Conferindo a instalação', 'validating': 'Conferindo integridade',
                  'preparing': 'Preparando o plugin', 'activating': 'Ativando o plugin',
                  'models': 'Preparando pesos', 'dependencies': 'Preparando ferramentas',
                  'checking': 'Conferindo a base existente', 'resources': 'Preparando recursos do plugin',
                  'complete': 'Conferência concluída'}
        stage = stages.get(value.get('stage')) if isinstance(value, dict) else None
        if stage:
            result['stage'] = value['stage']
            if value.get('stage') == 'resources':
                actions = {'checking': 'Conferindo recurso', 'preparing': 'Preparando recurso',
                           'downloading': 'Baixando recurso', 'extracting': 'Extraindo componente',
                           'validating': 'Conferindo componente', 'complete': 'Componente pronto'}
                resource_action = actions.get(value.get('resource_stage'))
                component = value.get('component')
                if resource_action:
                    stage = resource_action
                if isinstance(component, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,159}', component):
                    stage += ': ' + component
            completed, total = value.get('completed_files'), value.get('total_files')
            suffix = (' (%d/%d arquivos)' % (completed, total) if type(completed) is int and
                      type(total) is int and 0 <= completed <= total <= 1000000 else '')
            for copied_key, total_key in (('downloaded_bytes', 'total_bytes'),
                                           ('processed_bytes', 'total_unpacked_bytes')):
                copied_bytes, total_bytes = value.get(copied_key), value.get(total_key)
                if (type(copied_bytes) is int and type(total_bytes) is int and
                        0 <= copied_bytes <= total_bytes <= 1024 ** 5 and total_bytes > 0):
                    suffix += ' (%.1f/%.1f MB)' % (copied_bytes / 1024 ** 2, total_bytes / 1024 ** 2)
                    break
            _message(work, stage + suffix + '...')
    try:
        if cancelled():
            raise SetupError('INSTALL_CANCELLED', 'Instalação cancelada.')
        prepared = runner(envelope['payload'], progress)
        if (not isinstance(prepared, dict) or prepared.get('state') != 'ready' or
                not isinstance(prepared.get('active_version'), str) or
                not re.fullmatch(r'\d+(?:\.\d+)*', prepared['active_version'])):
            raise ValueError('O preparo não confirmou a ativação.')
        result.update(ok=True, version=prepared['active_version'])
        if prepared.get('resource_bundle_version'):
            result['resource_bundle_version']=prepared['resource_bundle_version']
        try:
            _cleanup_uploaded_source(root,envelope['plugin_id'],envelope['payload'])
        except (OSError,ValueError):
            pass
        _message(work, 'Instalação conferida e ativada.')
    except Exception as error:
        code = getattr(error, 'error_code', '')
        result['error_code'] = code if isinstance(code, str) and re.fullmatch('[A-Z][A-Z0-9_]{2,63}', code) else 'INSTALL_FAILED'
        for field, pattern in (('error_component', r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,159}'),
                               ('error_phase', r'[A-Z_]{2,32}')):
            value = getattr(error, field, None) or context.get(field)
            if isinstance(value, str) and re.fullmatch(pattern, value):
                result[field] = value
        reason = getattr(error, 'error_reason', None)
        allowed = {'TIMEOUT', 'TLS_ERROR', 'DNS_ERROR', 'DISK_FULL', 'CONNECTION_FAILED', 'IO_ERROR',
                   'HASH_MISMATCH', 'SIZE_MISMATCH', 'UNSAFE_REDIRECT', 'RESOURCE_INVALID',
                   'VALIDATION_FAILED', 'PACKAGE_INVALID', 'INVALID_PLAN', 'FILE_NOT_FOUND', 'DOWNLOAD_FAILED', 'HTTP_ERROR'}
        if not isinstance(reason, str) or (reason not in allowed and not re.fullmatch(r'HTTP_[1-5][0-9]{2}', reason)):
            reason = ('FILE_NOT_FOUND' if isinstance(error, FileNotFoundError) else
                      'IO_ERROR' if isinstance(error, OSError) else
                      'VALIDATION_FAILED' if isinstance(error, ValueError) else 'INSTALL_FAILED')
        result['error_reason'] = reason
        detail = ' / '.join(result[field] for field in ('error_component', 'error_phase', 'error_reason') if result.get(field))
        _message(work, 'A instalação não foi concluída. Código: ' + result['error_code'] + '.')
        _message(work, 'Diagnóstico: ' + detail + '.')
    _finish(work, result)
    _message(work, 'Reabrindo a Local Suite em uma nova janela...')
    try:
        callback = reopen or (lambda r, p, old: _reopen(r, p, old, envelope['plugin_id']))
        result['reopened'] = callback(root, envelope['port'], envelope['old_pid']) is True
    except Exception:
        result['reopened'] = False
    if not result['reopened']:
        _message(work, 'Não foi possível confirmar a nova janela. Abra o atalho Local Suite para continuar.')
        if result['ok']:
            result.update(error_code='REOPEN_FAILED', stage='restart')
    _finish(work, result)
    return 0 if result['ok'] and result['reopened'] else 1


def open_settings(suite_root, port=None, *, alive=None, open_browser=None, launch=None):
    root = _plain(suite_root).resolve()
    worker = Path(__file__).resolve()
    if worker.parent not in (root, root / 'app'):
        raise ValueError('O comando não pertence à suíte selecionada.')
    metadata = root / 'entrega.txt'
    values = {}
    if metadata.is_file() and metadata.stat().st_size <= LIMIT:
        for line in metadata.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip()
    version = values.get('VERSAO', '')
    if (values.get('PROJETO') != 'LOCAL_SUITE' or not re.fullmatch(r'\d+(?:\.\d+)*', version) or
            tuple(map(int, version.split('.'))) < (8, 12)):
        raise ValueError('Atualize a Local Suite para 8.12 antes de preparar o plugin.')
    if port is None:
        port = 8777
        config = Path(os.environ.get('RADAI_CONFIG') or worker.parent / 'radai_watcher.config')
        if config.is_file() and config.stat().st_size <= LIMIT:
            with config.open(encoding='utf-8-sig', errors='replace') as stream:
                for line in stream:
                    match = re.match(r'^\s*PORT\s*=\s*([^#\r\n]+)', line)
                    if match:
                        port = int(match.group(1).strip().strip('\'"'))
                        break
    if type(port) is not int or not 0 < port < 65536:
        raise ValueError('A porta da Local Suite é inválida.')
    import radai_lancador
    url = 'http://127.0.0.1:%d/config#ps_neuro' % port
    if (alive or radai_lancador.e_o_nosso_painel)(port):
        return (open_browser or radai_lancador.abrir_navegador)(url) is True
    command = [sys.executable, str(worker.with_name('radai_lancador.py')), '--url', url, '--abrir-janela']
    if launch:
        return launch(command) is True
    process = subprocess.run(command, cwd=worker.parent, env=_environment(), check=False)
    return process.returncode == 0


def main():
    # PowerShell captures UTF-8; isolated Python ignores PYTHONIOENCODING.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', type=Path)
    mode.add_argument('--open-settings', action='store_true')
    parser.add_argument('--suite-root', type=Path)
    parser.add_argument('--port', type=int)
    parser.add_argument('--sha256')
    parser.add_argument('--supervisor-pid', type=int)
    args = parser.parse_args()
    try:
        if args.open_settings:
            if args.suite_root is None:
                raise ValueError('Selecione a Local Suite instalada.')
            return 0 if open_settings(args.suite_root, args.port) else 1
        if not args.sha256 or not args.supervisor_pid:
            raise ValueError('Plano incompleto.')
        return run_worker(args.plan, args.sha256, args.supervisor_pid)
    except Exception:
        if args.open_settings:
            print('Abra a Local Suite e escolha Configurações, Plugin NEURO RT. A base precisa estar na versão 8.12 ou posterior.', flush=True)
        else:
            print('O instalador não pôde iniciar com segurança. A suíte existente foi preservada.', flush=True)
        return 1


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
