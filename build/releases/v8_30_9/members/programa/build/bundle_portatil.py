"""Monta o ZIP por fluxo. Só arquivos de dependência identificados pela versão podem vir da estação."""
from collections import defaultdict
from contextlib import ExitStack
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

MIB = 1 << 20
BUILD = Path(__file__).resolve().parent


def digest(reader, output=None):
    state = hashlib.sha256()
    while chunk := reader.read(4 * MIB):
        state.update(chunk)
        if output is not None:
            output.write(chunk)
    return state.hexdigest()


def tamanho(path):
    try:
        return path.stat().st_size
    except OSError:
        return -1


def inventario(ctx, motor):
    import requisitos
    import radai_tasks
    with gzip.open(BUILD / 'inventario-portatil.json.gz', 'rt', encoding='utf8') as fp:
        catalogo = json.load(fp)
    if (catalogo['fingerprint'] != requisitos.calcular(str(motor.RAIZ))['impressao']):
        raise ValueError('O catálogo do pacote portátil deve ser atualizado para os requisitos desta versão.')
    tasks = motor.tasks_do_perfil(ctx)
    datasets = set(radai_tasks.datasets_do_pacote(list(tasks)))
    grupos = defaultdict(dict)
    for rel, info in catalogo['files'].items():
        parts = Path(rel).parts
        tipo = parts[0]
        if tipo == 'ts_weights' and int(parts[1].split('_')[0][7:]) not in datasets:
            continue
        if tipo == 'modelos' and (parts[1] in ctx['modelos_omitidos'] or
                ctx['profile'] == 'lung-rt' and parts[1] not in motor.modelos_do_perfil(ctx)):
            continue
        key = tipo if tipo == 'python' else '/'.join(parts[:2])
        grupos[key][rel] = info[:2]
    presentes = {int(k.split('/Dataset')[1].split('_')[0]) for k in grupos if k.startswith('ts_weights/')}
    if presentes != datasets:
        raise ValueError('O inventário de dependências não cobre o perfil solicitado: ' + str(datasets - presentes))
    return grupos


def catalogo_runtime():
    with gzip.open(BUILD / 'inventario-portatil.json.gz', 'rt', encoding='utf8') as reader:
        return json.load(reader)


def complemento_python(motor, rows, disponiveis, tmp, ctx, estacao, caches):
    # Os RECORDs do runtime publicado identificam o wheel que contém cada arquivo ausente.
    catalogo = catalogo_runtime()
    por_pacote = defaultdict(list)
    for rel in rows:
        if rel not in disponiveis:
            item = catalogo['files'][rel]
            dono = catalogo['distributions'][item[2]] if len(item) == 3 else 'python-embed'
            por_pacote[dono].append(rel)
    runtime = dict(ctx, bundle=tmp, py=tmp/'python/python.exe', destino=tmp, cache=tmp/'cache')
    runtime['cache'].mkdir()
    py = estacao/'python/python.exe' if estacao else None
    if not py or not py.is_file() or 'python-embed' in por_pacote:
        for base in caches:
            f = base/'python-embed.zip'
            if f.is_file():
                import artefatos
                if artefatos.conferir(str(f), 'cache/python-embed.zip')[0]:
                    shutil.copyfile(f, runtime['cache']/f.name)
                    break
        motor.etapa_runtime(runtime)
        for rel in por_pacote.pop('python-embed', ()):
            yield rel, tmp/rel, rows[rel][1]
        if not py or not py.is_file():
            motor.etapa_pip(runtime)
            py = runtime['py']
    for pacote, faltam in sorted(por_pacote.items()):
        with tempfile.TemporaryDirectory(prefix='wheel-', dir=tmp) as wheel_tmp:
            destino = Path(wheel_tmp)
            wheels = [f for cache in caches if cache.is_dir() for f in cache.glob('*.whl')]
            def instalar(indices):
                import subprocess
                comando = [str(py), '-B', '-m', 'pip', '--isolated', 'install', '--no-deps',
                           '--no-compile', '--ignore-installed', '--target', str(destino), *indices, pacote]
                return subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=3600,
                                      text=True, encoding='utf8', errors='replace')
            offline = ['--no-index']
            for folder in sorted(set(f.parent for f in wheels)):
                offline.extend(['--find-links', str(folder)])
            r = instalar(offline) if wheels else None
            if r is None or r.returncode:
                r = instalar(['--index-url', 'https://pypi.org/simple', '--extra-index-url',
                              'https://download.pytorch.org/whl/'+ctx['cuda']])
            if r.returncode:
                raise RuntimeError('Falha ao obter '+pacote+': '+r.stdout[-900:])
            for rel in faltam:
                path = Path(rel)
                if path.parts[:3] == ('python','Lib','site-packages'):
                    f = destino.joinpath(*path.parts[3:])
                else:
                    f = destino.joinpath(*path.parts[1:])
                    if not f.is_file():
                        f = destino/'bin'/path.name
                sha = rows[rel][1]
                if path.name in {'RECORD','INSTALLER','REQUESTED','direct_url.json'} or path.parts[1]=='Scripts':
                    # pip cria metadados e launchers com caminhos locais. Use os recém-gerados
                    # pelo wheel da distribuição/versionamento correspondente.
                    sha = None
                if not f.is_file():
                    raise ValueError('O wheel '+pacote+' não forneceu '+rel)
                yield rel, f, sha


def verificar_local(rel, info, pastas, zips, projeto):
    size, expected = info
    for base in pastas:
        f = base / rel
        # Os únicos bytes que podem entrar são os da lista fixa: a identidade
        # SHA também é verificada durante a gravação do ZIP.
        try:
            with f.open('rb') as reader:
                if os.fstat(reader.fileno()).st_size == size and digest(reader) == expected:
                    return f
        except (OSError, PermissionError):
            continue
    for z in zips:
        try:
            m = z.getinfo(projeto + '/' + rel)
            if m.file_size == size:
                with z.open(m) as reader:
                    if digest(reader) == expected:
                        return (z, m)
        except (KeyError, zipfile.BadZipFile, OSError):
            continue
    return None


def escrever(z, nome, origem, sha=None):
    if isinstance(origem, tuple):
        reader = origem[0].open(origem[1])
    else:
        reader = origem.open('rb')
    with reader, z.open(nome, 'w', force_zip64=True) as out:
        result = digest(reader, out)
    if sha and result != sha:
        raise ValueError('O arquivo foi alterado durante a montagem: ' + nome)
    return result


def conferir_espaco(destino, temporario, final, extra):
    volumes = {}
    for pasta, necessario in ((destino, final), (temporario, extra)):
        volume = pasta.stat().st_dev
        existente = volumes.get(volume, (pasta, 0))
        volumes[volume] = (pasta, existente[1] + necessario)
    for pasta, total in volumes.values():
        livre = shutil.disk_usage(pasta).free
        if livre < total:
            raise OSError(f'Espaço insuficiente em {pasta.anchor}: {livre / 2**30:.2f} GiB livres, '
                          f'{total / 2**30:.2f} GiB estimados (ZIP {final / 2**30:.2f}, '
                          f'temporários {extra / 2**30:.2f} GiB).')


def complemento_ts(motor, grupo, rows, disponiveis, caches, tmp):
    import artefatos
    dataset = grupo.split('/')[1]
    nome = dataset + '.zip'
    spec = artefatos.PESOS_TS[nome]
    arq = None
    for pasta in caches:
        candidato = pasta / nome
        if tamanho(candidato) == spec['bytes'] and artefatos.conferir_peso_ts(str(candidato), nome, dataset)[0]:
            arq = candidato
            break
    if arq is None:
        arq = tmp / nome
        url = 'https://github.com/wasserth/TotalSegmentator/releases/download/' + spec['release'] + '/' + nome
        motor._transferir(url, arq, motor._relogio_de_progresso())
        ok, msg, _ = artefatos.conferir_peso_ts(str(arq), nome, dataset)
        if not ok:
            raise ValueError(msg)
    with zipfile.ZipFile(arq) as z:
        for rel in rows:
            if rel not in disponiveis:
                m = z.getinfo(rel.split('/', 1)[1])
                # O membro veio do ZIP original autenticado (hash/tamanho do fabricante +
                # CRC inclusive nas versões que distribuem o otimizador junto dos tensores).
                with z.open(m) as reader:
                    original = digest(reader)
                yield rel, (z, m), original


def complemento_modelo(motor, grupo, rows, disponiveis, tmp):
    import radai_models
    ident = grupo.split('/')[1]
    for rel in rows:
        if rel in disponiveis:
            target = tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            source = disponiveis[rel]
            reader = source[0].open(source[1]) if isinstance(source, tuple) else source.open('rb')
            with reader, target.open('wb') as out:
                if digest(reader, out) != rows[rel][1]:
                    raise ValueError('Cópia local do modelo mudou: ' + rel)
    anterior = os.environ.get('RADAI_MODELOS_DIR')
    try:
        os.environ['RADAI_MODELOS_DIR'] = str(tmp / 'modelos')
        radai_models.baixar(ident)
        motor.conferir_modelos_exigidos(tmp, [ident])
        for rel in rows:
            if rel not in disponiveis:
                # O catálogo prevê versões enxutas, enquanto a origem de alguns modelos
                # distribui o checkpoint original. Ambas possuem hash publicado.
                modelo = radai_models.MODELOS[ident]
                local = tmp/rel
                esperado = rows[rel][1]
                relativo = rel.split('/',2)[2]
                oficial = (modelo.get('sha256') or {}).get(relativo)
                if oficial and oficial != esperado:
                    with local.open('rb') as fp:
                        if digest(fp) == oficial:
                            esperado = oficial
                yield rel, local, esperado
    finally:
        if anterior is None:
            os.environ.pop('RADAI_MODELOS_DIR', None)
        else:
            os.environ['RADAI_MODELOS_DIR'] = anterior


def montar(motor, ctx, estacao=None, caches=()):
    import artefatos
    grupos = inventario(ctx, motor)
    base = Path(ctx['preparo'])
    target = ctx['saida'] / (ctx['produto'] + '_BUNDLE_v' + ctx['versao'] + '.zip')
    target.parent.mkdir(parents=True, exist_ok=True)
    extras = [Path(p) for p in os.environ.get('LOCAL_SUITE_BUNDLE_CACHE','').split(os.pathsep) if p]
    cache_paths = [Path(x).resolve() for x in (*caches, *extras)]
    downloads = Path.home()/'Downloads'
    if downloads.is_dir():
        cache_paths.append(downloads)
    pastas = [p.resolve() for p in (estacao, base / '_montagem' / ctx['projeto'], *cache_paths) if p and p.is_dir()]
    arquivos = {p for p in cache_paths if p.is_file() and p.suffix.lower() == '.zip'}
    for path in [base, *cache_paths]:
        if path.is_dir():
            arquivos.update(path.glob('*BUNDLE*.zip'))
            arquivos.update(path.glob(ctx['projeto'] + '_v*/*BUNDLE*.zip'))
    caches_ts = [*cache_paths, base / '_montagem/cache/pesos_ts']
    if estacao:
        caches_ts.append(estacao / '_instalacao/cache/pesos_ts')
    scratch_base = Path(tempfile.gettempdir())
    with ExitStack() as life:
        scratch = Path(life.enter_context(tempfile.TemporaryDirectory(prefix='suite-portatil-', dir=scratch_base)))
        # Os zips antigos são somente leitura, inclusive quando um deles será substituído.
        zips = []
        for p in sorted(arquivos):
            try:
                zips.append(life.enter_context(zipfile.ZipFile(p)))
            except (OSError, zipfile.BadZipFile):
                continue
        fontes = {}
        faltas = {}
        final = 0
        extra = 0
        for grupo, rows in grupos.items():
            size = sum(r[0] for r in rows.values())
            final += size + len(rows) * 400
            for numero, (rel, info) in enumerate(rows.items(), 1):
                if numero % 2500 == 0:
                    motor.log(f'  {grupo}: conferindo arquivo {numero} de {len(rows)}.')
                f = verificar_local(rel, info, pastas, zips, ctx['projeto'])
                if f is not None:
                    fontes[rel] = f
            faltas[grupo] = sum(r[0] for rel, r in rows.items() if rel not in fontes)
            if faltas[grupo]:
                if grupo == 'python':
                    catalogo = catalogo_runtime()
                    por_dono = defaultdict(int)
                    donos_ausentes = set()
                    for rel, (n, _) in rows.items():
                        file_info = catalogo['files'][rel]
                        dono = file_info[2] if len(file_info) == 3 else -1
                        por_dono[dono] += n
                        if rel not in fontes:
                            donos_ausentes.add(dono)
                    extra = max(extra, max(por_dono[k] for k in donos_ausentes) * 2)
                elif grupo.startswith('ts_weights/'):
                    archive_size = artefatos.PESOS_TS[grupo.split('/')[1]+'.zip']['bytes']
                    extra = max(extra, archive_size)
                    final += archive_size  # alguns pesos oficiais incluem o estado do otimizador
                else:
                    extra = max(extra, size * 2)
            motor.log(f'  {grupo}: {sum(rel in fontes for rel in rows)}/{len(rows)} arquivos locais conferidos.')
        motor.log(f'ZIP no destino ~{final/2**30:.2f} GiB. Temporários em {scratch.anchor} '
                  f'~{extra/2**30:.2f} GiB + código e galeria.')
        conferir_espaco(target.parent, scratch, final + 128*MIB, extra + 128*MIB)
        work = dict(ctx, destino=scratch, bundle=scratch/'app', cache=scratch/'cache',
                    reutilizar_instalacao=estacao)
        work['cache'].mkdir()
        import galeria_publica
        galeria, _ = galeria_publica.catalogo(motor.RAIZ/'app/data')
        for cache_dir in [*cache_paths, base/'_montagem/cache',
                          *((estacao/'_instalacao/cache',) if estacao else ())]:
            fonte = cache_dir/galeria['filename'] if cache_dir.is_dir() else cache_dir
            if tamanho(fonte) == galeria['bytes'] and galeria_publica.confere(fonte, galeria['sha256']):
                shutil.copyfile(fonte, work['cache']/galeria['filename'])
                break
        work['bundle'].mkdir()
        motor._montar_codigo(work)
        motor._gravar_selecao_modelos(work, work['bundle'])
        instaladores = motor._avulsos_do_pacote(work)
        with tempfile.TemporaryDirectory(prefix='.suite-zip-', dir=target.parent) as output_tmp:
            partial = Path(output_tmp) / target.name
            hashes = {}
            with zipfile.ZipFile(partial, 'w', allowZip64=True) as out:
                prefixo = ctx['projeto'] + '/'
                for grupo, rows in grupos.items():
                    for rel, (size, sha) in rows.items():
                        if rel in fontes:
                            hashes[rel] = escrever(out, prefixo+rel, fontes[rel], sha)
                    if not faltas[grupo]:
                        continue
                    motor.log('  Completando recursos ausentes de ' + grupo)
                    with tempfile.TemporaryDirectory(dir=scratch, prefix='componente-') as folder:
                        sub = Path(folder)
                        if grupo == 'python':
                            novos = complemento_python(motor, rows, fontes, sub, work, estacao, caches_ts)
                        elif grupo.startswith('ts_weights/'):
                            novos = complemento_ts(motor, grupo, rows, fontes, caches_ts, sub)
                        else:
                            novos = complemento_modelo(motor, grupo, rows, fontes, sub)
                        for rel, src, sha in novos:
                            hashes[rel] = escrever(out, prefixo+rel, src, sha)
                with (work['bundle']/'plugins.txt').open('a', encoding='utf8') as fp:
                    fp.write('LEVADO='+','.join(motor.tasks_do_perfil(ctx))+'\n')
                    fp.write('MODELOS_LEVADOS='+','.join(sorted(g.split('/')[1] for g in grupos if g.startswith('modelos/')))+'\n')
                for p in motor._arquivos_do_bundle(work['bundle'], ctx['modelos_omitidos']):
                    out.write(p, prefixo+p.relative_to(work['bundle']).as_posix())
                for name, source in instaladores:
                    if name == 'MANIFESTO.txt':
                        # O manifesto deve descrever o ZIP, não a pequena pasta temporária do app.
                        with source.open('w', encoding='utf8') as fp:
                            fp.write('Local Suite '+ctx['versao']+'\nComponentes conferidos e gravados no pacote:\n')
                            for rel, sha in sorted(hashes.items()):
                                fp.write(sha+'  '+rel+'\n')
                    out.write(source, name)
            # Verifica o arquivo temporário antes da substituição do último ZIP utilizável.
            motor.etapa_distribuir(dict(ctx, pacote=partial))
            for z in zips:
                z.close()
            os.replace(partial, target)
    motor.log('Pacote completo: ' + str(target))
    return target
