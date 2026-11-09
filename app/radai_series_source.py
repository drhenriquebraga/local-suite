import atexit
import os
from pathlib import Path, PureWindowsPath
import shutil
import stat
import tempfile
import threading
import zipfile

_LOCK = threading.RLock()
_EXTRACTED = {}
MAX_FILES = 200000
MAX_BYTES = 40 * 1024**3


def _relative(name):
    win = PureWindowsPath(name)
    parts = name.replace(chr(92), '/').split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {p + str(n) for p in ('COM', 'LPT') for n in range(1, 10)}
    if (not name or win.drive or win.root or any(p in ('', '.', '..') or p.endswith((' ', '.'))
            or p.split('.')[0].upper() in reserved for p in parts)
            or any(ord(c) < 32 or c in '<>:"|?*' for c in name)):
        raise ValueError('O ZIP contém um caminho inválido.')
    return parts


def _dispose(record):
    folder, owner = record
    try:
        import radai_archive
        radai_archive.soltar_em_uso(folder)
    finally:
        pass


def close():
    with _LOCK:
        records = list(_EXTRACTED.values())
        _EXTRACTED.clear()
    for record in records:
        try:
            _dispose(record)
        except OSError:
            pass


atexit.register(close)


def resolve_folder(value, cancelled=None):
    text = str(value or '').strip().strip('"')
    if not text:
        return '', 'Pasta ou ZIP não encontrado.'
    path = Path(text)
    if path.is_dir():
        return str(path.resolve()), ''
    if not path.is_file() or path.suffix.lower() != '.zip':
        return '', 'Pasta ou ZIP não encontrado.'
    cancelled = cancelled or (lambda: False)
    owner = None
    try:
        info = path.stat()
        key = (str(path.resolve()), info.st_size, info.st_mtime_ns)
        with _LOCK:
            if key in _EXTRACTED:
                return _EXTRACTED[key][0], ''
            owner = tempfile.mkdtemp(prefix='radai_series_')
            target = Path(owner)
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) > MAX_FILES:
                    raise ValueError('O ZIP excede o limite de arquivos.')
                seen, total, files = set(), 0, []
                for entry in entries:
                    name = entry.filename.rstrip('/') if entry.is_dir() else entry.filename
                    parts = _relative(name)
                    norm = '/'.join(parts).casefold()
                    mode = entry.external_attr >> 16
                    if norm in seen or stat.S_ISLNK(mode) or entry.flag_bits & 1:
                        raise ValueError('O ZIP contém entradas repetidas, links ou arquivos protegidos.')
                    seen.add(norm)
                    if not entry.is_dir():
                        total += entry.file_size
                        files.append((entry, parts))
                if not files or total > MAX_BYTES or total > shutil.disk_usage(target).free - 256 * 1024**2:
                    raise ValueError('Não há espaço para extrair este ZIP ou seu tamanho excede o limite.')
                for entry, parts in files:
                    if cancelled():
                        raise ValueError('Busca interrompida.')
                    dest = target.joinpath(*parts)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as source, dest.open('xb') as output:
                        written = 0
                        while True:
                            if cancelled():
                                raise ValueError('Busca interrompida.')
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            written += len(chunk)
                            if written > entry.file_size:
                                raise ValueError('O tamanho extraído diverge do ZIP.')
                            output.write(chunk)
                    if written != entry.file_size:
                        raise ValueError('O ZIP está incompleto.')
            after = path.stat()
            if (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
                raise ValueError('O ZIP foi alterado durante a leitura. Procure novamente.')
            import radai_archive
            radai_archive.marcar_em_uso(str(target))
            _EXTRACTED[key] = (str(target), owner)
            owner = None
            return str(target), ''
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
        return '', 'Não foi possível abrir o ZIP com segurança. Confira o arquivo e o espaço disponível.'
    finally:
        if owner is not None:
            shutil.rmtree(owner)


def resolve_selection(selection):
    if not isinstance(selection, dict):
        raise ValueError('Escolha a série novamente.')
    scan = selection.get('scan_id')
    ticket = selection.get('bilhete')
    uid = selection.get('uid')
    if not all(isinstance(v, str) and v for v in (scan, ticket, uid)):
        raise ValueError('Escolha a série novamente.')
    import radai_varrer
    import radai_thumbnail
    state = radai_varrer.estado(scan)
    if state.get('erro') or not state.get('final'):
        raise ValueError('Aguarde a leitura terminar ou procure a série novamente.')
    row = next((r for r in state.get('linhas', ()) if r.get('bilhete') == ticket
                and r.get('uid') == uid and not r.get('carregando') and not r.get('recusa')), None)
    if row is None:
        raise ValueError('A série não pertence a esta busca.')
    folder, real_uid = radai_thumbnail.resolver(ticket)
    if not folder or uid != real_uid:
        raise ValueError('Bilhete expirado. Procure a série novamente.')
    series = radai_thumbnail._serie_do_bilhete(ticket, folder, uid)
    files = (series or {}).get('arquivos') or []
    paths = [f.get('caminho') if isinstance(f,dict) else f for f in files]
    if not series or series.get('uid') != uid or not Path(folder).is_dir() or not paths or any(not isinstance(f,(str,os.PathLike)) or not Path(f).is_file() for f in paths):
        raise ValueError('A série não está mais disponível.')
    with radai_varrer._TRAVA:
        job = radai_varrer._VARREDURAS.get(scan)
        if not job:
            raise ValueError('Busca expirada. Escolha a série novamente.')
        scan_root = job['pasta']
        original = job.get('source_original',scan_root)
    return dict(series, pasta=folder, uid=uid, bilhete=ticket, scan_root=scan_root,
                source_original=original)
