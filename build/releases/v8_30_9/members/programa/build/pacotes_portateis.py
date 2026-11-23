"""Prepara os plugins escolhidos para transporte sem alterar a instalação desta máquina."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from collections import Counter
from contextlib import ExitStack
import shutil
import subprocess
import sys
import tempfile
import zipfile


APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import consentimento_instalador
import radai_lung_install as lung
from radai_plugin_bootstrap import seed_source


PROFILES = {"neuro-rt":"plugin-neuro", "lung-rt":"plugin-lung", "coronarias":"plugin-coronarias"}


def ler(f):
    return json.loads(f.read_text(encoding="utf-8-sig"))


def canonico(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))+"\n").encode()


def local_valido(candidatos, info):
    for path in candidatos:
        if not path.is_file() or path.stat().st_size != info['size']:
            continue
        with path.open('rb') as source:
            sha = hashlib.sha256()
            while chunk := source.read(4<<20):
                sha.update(chunk)
        if sha.hexdigest() == info['sha256']:
            return path
    return None


class MembroLocal:
    def __init__(self, archive, member):
        self.archive = archive
        self.member = member

    def open(self, mode):
        return self.archive.open(self.member)


def no_zip(pacotes, nome, info):
    for arq in pacotes:
        try:
            m = arq.getinfo(nome)
            if m.file_size == info['size']:
                ref = MembroLocal(arq, m)
                with ref.open('rb') as reader:
                    from bundle_portatil import digest
                    if digest(reader) == info['sha256']:
                        return ref
        except (KeyError, OSError, zipfile.BadZipFile):
            continue
    return None


def recursos_neuro(source, cache, recipe, station=None, pacotes=()):
    sys.path.insert(0, str(source/'code'))
    try:
        from neuro_rt import resource_preparation as rp
        root = station/'Plugins/NEURO RT' if station else None
        downloads = cache/'downloads'
        downloads.mkdir()
        def arquivo(row):
            original = local_valido([rp.resource_cache_path(root, row)] if root else [], row)
            return original or rp._fetch(row, downloads, None, None)
        usos = Counter(info['download'] for model in recipe['models'] for info in model['files'].values())
        for model in recipe['models']:
            rel = 'models/'+model['id']+'/'+model['revision']+'/'
            for name, info in sorted(model['files'].items()):
                path = local_valido([root/rel/name] if root else [], info) or no_zip(pacotes,rel+name,info)
                if path is None:
                    path = arquivo(recipe['downloads'][info['download']])
                    if 'member' in info:
                        with zipfile.ZipFile(path) as z, z.open(info['member']) as reader:
                            path = cache/'membro'
                            with path.open('wb') as writer:
                                shutil.copyfileobj(reader,writer,4<<20)
                yield rel+name, path, info, 'models'
                chave = info['download']
                usos[chave] -= 1
                if not usos[chave]:
                    spec = recipe['downloads'][chave]
                    (downloads/spec['sha256']/spec['filename']).unlink(missing_ok=True)
                if path == cache/'membro':
                    path.unlink(missing_ok=True)
            if 'provenance.json' not in model['files']:
                data = canonico(model.get('provenance', {}))
                f = cache/'provenance.json'
                f.write_bytes(data)
                yield rel+'provenance.json', f, {'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}, 'models'
        extra = [recipe['downloads'][r['download']] for r in recipe.get('extra_files', {}).values()]
        for name, info in {r['filename']:r for r in [*recipe['wheels'],*extra]}.items():
            local = no_zip(pacotes,'downloads/'+info['sha256']+'/'+name,info) or arquivo(info)
            yield 'downloads/'+info['sha256']+'/'+name, local, info, 'wheels' if name.endswith('.whl') else 'notices'
            if isinstance(local, Path) and local.is_relative_to(downloads):
                local.unlink(missing_ok=True)
    finally:
        sys.path.remove(str(source/'code'))


def recursos_lung(source, cache, recipe, station=None, pacotes=()):
    rows = [(row['path'],row) for row in recipe['files']]
    xray = ler(source/'code/catalog/xray_resources.json')
    for key in ('runtime','model','mmproj'):
        row = xray[key]
        rows.append(('xray/'+xray['revision']+'/'+row['filename'],row))
    root = station/'Plugins/LUNG RT' if station else None
    sources = [root/'data', *sorted((root/'resources').glob('*'))] if root else []
    for name,row in rows:
        f = local_valido([p/name for p in sources],row) or no_zip(pacotes,'resources/'+name,row)
        if not f:
            f = lung._download([row['url']], cache/row['sha256'], row['size'],row['sha256'])
        yield 'resources/'+name, f, row, 'models'
        if isinstance(f, Path) and f.parent == cache:
            f.unlink(missing_ok=True)


def adicionar(archive, name, source, size, expected):
    entry = zipfile.ZipInfo(name, (1980,1,1,0,0,0))
    entry.file_size = size
    digest = hashlib.sha256()
    written = 0
    with source.open("rb") as reader, archive.open(entry,"w",force_zip64=True) as output:
        while data := reader.read(4<<20):
            output.write(data)
            digest.update(data)
            written += len(data)
    if written != size or digest.hexdigest() != expected:
        raise ValueError("Integridade inválida em "+name)


def montar(plugin, output, station=None):
    with ExitStack() as stack:
        source = stack.enter_context(seed_source(plugin))
        temp = stack.enter_context(tempfile.TemporaryDirectory(prefix="suite-plugin-"))
        output_temp = stack.enter_context(tempfile.TemporaryDirectory(prefix=".pacote-",dir=output))
        work = Path(temp)
        manifest_file = source/"release-manifest.json"
        meta = ler(manifest_file)
        recipe = ler(source/"code/catalog/resource_recipe.json")
        target = output/(plugin.upper().replace("-","_")+"_OFFLINE_v"+meta["version"]+".zip")
        acervo = Path(os.environ.get('SystemDrive', 'C:') + '/')/'AI_BUNDLES'
        fontes = [target, acervo/target.name, Path.home()/'Downloads'/target.name]
        for item in os.environ.get('LOCAL_SUITE_BUNDLE_CACHE','').split(os.pathsep):
            if item:
                path = Path(item)
                fontes.append(path/target.name if path.is_dir() else path)
        pacotes = []
        for p in dict.fromkeys(fontes):
            if p.is_file():
                try:
                    pacotes.append(stack.enter_context(zipfile.ZipFile(p)))
                except zipfile.BadZipFile:
                    pass
        temporary = Path(output_temp)/"plugin.zip" 
        neuro = plugin == "neuro-rt"
        materials = recursos_neuro if neuro else recursos_lung
        categories = {k:{"files":0,"bytes":0} for k in ("code","models","wheels","notices","launchers","metadata")}
        inventory = []
        from bundle_portatil import conferir_espaco
        code_size = manifest_file.stat().st_size + sum(r['size'] for r in meta['files'] + meta.get('launchers',[]))
        root = station / 'Plugins' / ('NEURO RT' if neuro else 'LUNG RT') if station else None
        if neuro:
            models = [(model, name, info) for model in recipe['models'] for name, info in model['files'].items()]
            extra = [recipe['downloads'][r['download']] for r in recipe.get('extra_files', {}).values()]
            downloads = {r['filename']:r for r in [*recipe['wheels'],*extra]}
            size = code_size + sum(i['size'] for _,_,i in models) + sum(i['size'] for i in downloads.values())
            # O arquivo compactado e seu maior membro podem coexistir; ambos ficam fora do ZIP final.
            faltantes = [recipe['downloads'][i['download']]['size'] + i['size'] for m,n,i in models
                         if not (local_valido([root/'models'/m['id']/m['revision']/n] if root else [],i) or no_zip(pacotes,'models/'+m['id']+'/'+m['revision']+'/'+n,i))]
            faltantes.extend(i['size'] for n,i in downloads.items()
                            if not (local_valido([root/'cache/resources/downloads'/i['sha256']/n] if root else [],i) or no_zip(pacotes,'downloads/'+i['sha256']+'/'+n,i)))
        else:
            xray = ler(source/'code/catalog/xray_resources.json')
            recursos = [(i['path'],i) for i in recipe['files']]
            recursos.extend(('xray/'+xray['revision']+'/'+xray[k]['filename'],xray[k]) for k in ('runtime','model','mmproj'))
            size = code_size + sum(i['size'] for _,i in recursos)
            roots = [root/'data', *sorted((root/'resources').glob('*'))] if root else []
            faltantes = [i['size'] for n,i in recursos if not (local_valido([r/n for r in roots],i) or no_zip(pacotes,'resources/'+n,i))]
        scratch = max(faltantes, default=0)
        print(f"{plugin}: ZIP {size/2**30:.2f} GiB em {output.anchor}; temporários {scratch/2**30:.2f} GiB em {work.anchor}.", flush=True)
        conferir_espaco(output, work, size+8*1024**2, scratch+8*1024**2)
        with zipfile.ZipFile(temporary,"w",allowZip64=True) as archive:
            def put(name, f, info, category):
                adicionar(archive,name,f,info["size"],info["sha256"])
                inventory.append(dict(path=name,size=info["size"],sha256=info["sha256"],category=category))
                categories[category]["files"] += 1
                categories[category]["bytes"] += info["size"]
            raw = manifest_file.read_bytes()
            pin = hashlib.sha256(raw).hexdigest()
            put("release-manifest.json",manifest_file,{"sha256":pin,"size":len(raw)},"metadata")
            for row in sorted(meta["files"],key=lambda r:r["path"]):
                put(row["path"],source/row["path"],row,"code")
            for row in meta.get("launchers",[]):
                put(row["path"],source/"code/installer"/row["path"],row,"launchers")
            for row in materials(source, work, recipe, station, pacotes):
                put(*row)
            if neuro:
                import radai_neuro_install as sdk
                code_pin = sdk.inspect_local_source(source)["code_inventory_sha256"]
                marker = dict(schema="neuro-rt/local-bundle/1",version=meta["version"],code_inventory_sha256=code_pin,
                              recipe_digest=hashlib.sha256(canonico(recipe)).hexdigest(), resources_resolved_for_target=False,
                              python_included=False, categories=categories, files=sorted(inventory,key=lambda r:r["path"]),
                              payload_bytes=sum(r["size"] for r in inventory),receipt_excludes_itself=True)
                name = "offline-bundle.json"
            else:
                for name, info in lung.HAI_DEF_NOTICES.items():
                    put(name, APP / 'data' / 'licencas_lung' / Path(name).name, info, 'notices')
                marker = dict(schema="lung-rt/offline-preparation/1", complete=True, code_pin=pin,
                              suite_notices=lung.HAI_DEF_REVISION)
                name = ".lung-offline-preparation.json"
            archive.writestr(zipfile.ZipInfo(name,(1980,1,1,0,0,0)),canonico(marker))
        for arq in pacotes:
            arq.close()
        os.replace(temporary,target)
        return target


def preparar(plugins, output, station=None):
    """Nenhum plugin é inferido da escolha de outro item."""
    if not plugins or len(set(plugins)) != len(plugins) or set(plugins)-PROFILES.keys():
        raise ValueError("Seleção de plugins inválida.")
    for plugin in plugins:
        consentimento_instalador.exigir(PROFILES[plugin])
    output.mkdir(parents=True,exist_ok=True)
    for plugin in plugins:
        if plugin == "coronarias":
            subprocess.run([sys.executable, "-B", str(APP/"radai_rocards_offline.py"), "montar", "--saida", str(output)]+(['--base',str(station)] if station else []),check=True)
        else:
            print(montar(plugin,output,station),flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida",type=Path,required=True)
    parser.add_argument("--reutilizar-instalacao",type=Path)
    parser.add_argument("plugins",nargs="+",choices=PROFILES)
    args = parser.parse_args()
    preparar(args.plugins,args.saida,args.reutilizar_instalacao)

