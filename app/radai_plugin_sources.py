import asyncio
from contextlib import suppress
import errno
import http.client
import json
from pathlib import Path
import shutil
import socket
import ssl
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from radai_plugin_setup import PLUGINS, _plain


class SetupUploadError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def _discard(inbox, directory):
    inbox, directory = _plain(inbox).resolve(), _plain(directory).resolve()
    if directory.parent == inbox and directory.name.startswith('setup-'):
        shutil.rmtree(directory)


async def receive_setup(request, root, plugin_id, inspect, max_size):
    from starlette.concurrency import run_in_threadpool

    if request.headers.get('content-type', '').split(';')[0].lower() not in (
            'application/zip', 'application/x-zip-compressed', 'application/octet-stream'):
        raise SetupUploadError('EXPECTED_SETUP_ZIP', 'Selecione o arquivo ZIP do SETUP.', 415)
    try:
        length = int(request.headers.get('content-length', '0'))
    except ValueError:
        length = -1
    if not 0 <= length <= max_size:
        raise SetupUploadError('SETUP_TOO_LARGE', 'O ZIP excede o limite de um SETUP leve.', 413)
    inbox = _plain(Path(root) / 'Plugins' / PLUGINS[plugin_id][0] / 'staging/local-setup')
    inbox.mkdir(parents=True, exist_ok=True)
    if length and shutil.disk_usage(inbox).free < length + 256 * 1024**2:
        raise SetupUploadError('LOCAL_DISK_FULL', 'Não há espaço livre suficiente para copiar o ZIP local.', 507)
    # Uploads must survive the controlled shutdown. Retain them longer than source
    # IDs so an active transaction can still read the ZIP after the host exits.
    cutoff = time.time() - 24 * 60 * 60
    for old in inbox.glob('setup-*'):
        with suppress(OSError, ValueError):
            if old.is_dir() and old.stat().st_mtime < cutoff:
                _discard(inbox, old)
    directory = Path(tempfile.mkdtemp(prefix='setup-', dir=inbox))
    package = directory / 'setup.zip'
    try:
        count = 0
        with package.open('xb') as stream:
            async for chunk in request.stream():
                count += len(chunk)
                if count > max_size:
                    raise SetupUploadError('SETUP_TOO_LARGE', 'O ZIP excede o limite permitido para esta operação.', 413)
                stream.write(chunk)
        if not count:
            raise SetupUploadError('EXPECTED_SETUP_ZIP', 'O arquivo ZIP está vazio.')
        return await run_in_threadpool(inspect, package)
    except BaseException:
        with suppress(OSError, ValueError):
            _discard(inbox, directory)
        raise


def read_metadata(url):
    request = Request(url, headers={'User-Agent': 'Local-Suite-Plugin-Check',
                                   'Accept': 'application/json'})
    with urlopen(request, timeout=5) as response:
        if not response.geturl().startswith('https://'):
            raise ValueError('HTTPS obrigatório.')
        raw = response.read(2 * 1024**2 + 1)
    if len(raw) > 2 * 1024**2:
        raise ValueError('Metadados excedem o limite.')
    return json.loads(raw)


def _probe(lookup, origin):
    try:
        release = lookup(origin)
        return {'status': 'available', 'code': 'OK', 'version': release['version']}
    except HTTPError as error:
        code = 'HTTP_%d' % error.code
    except (URLError, OSError, http.client.HTTPException) as error:
        cause = getattr(error, 'reason', error)
        if isinstance(cause, (TimeoutError, socket.timeout)) or getattr(cause, 'errno', None) == errno.ETIMEDOUT:
            code = 'TIMEOUT'
        elif isinstance(cause, socket.gaierror):
            code = 'DNS_ERROR'
        elif isinstance(cause, ssl.SSLError):
            code = 'TLS_ERROR'
        else:
            code = 'NETWORK_ERROR'
    except (ValueError, KeyError, StopIteration, TypeError, AttributeError):
        code = 'RELEASE_INVALID'
    return {'status': 'unavailable', 'code': code}


async def connectivity(lookup):
    from starlette.concurrency import run_in_threadpool

    origins = ('github', 'mirror')
    results = await asyncio.gather(*(run_in_threadpool(_probe, lookup, name) for name in origins))
    return dict(zip(origins, results))
