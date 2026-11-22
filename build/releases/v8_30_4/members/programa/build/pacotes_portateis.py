"""Prepara os plugins escolhidos para transporte sem alterar a instalação desta máquina."""
import argparse
import hashlib
import json
import os
from pathlib import Path
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


def recursos_neuro(source, cache, recipe):
    """Obtenha os modelos e wheels originais; as bibliotecas serão instaladas no destino."""
    sys.path.insert(0, str(source/"code"))
    try:
        from neuro_rt import resource_preparation as rp
        stage = cache/"pendentes"
        stage.mkdir(parents=True)
        downloads = cache/"cache/resources/downloads"
        downloads.mkdir(parents=True)
        for model in recipe["models"]:
            print(model["id"], flush=True)
            rel = rp._prepare_model(model, recipe, cache, stage, downloads, None, None)
            for name, info in sorted(model["files"].items()):
                yield rel+"/"+name, cache/rel/name, info, "models"
            if "provenance.json" not in model["files"]:
                data = canonico(model.get("provenance", {}))
                yield rel+"/provenance.json", cache/rel/"provenance.json", {"size":len(data),"sha256":hashlib.sha256(data).hexdigest()}, "models"
        for info in rp.prepare_offline_archives(recipe, plugin_root=cache):
            name = info["filename"]
            yield "downloads/"+info["sha256"]+"/"+name, rp.resource_cache_path(cache,info), info, "wheels" if name.endswith(".whl") else "notices"
    finally:
        sys.path.remove(str(source/"code"))


def recursos_lung(source, cache, recipe):
    rows = [(row["path"],row) for row in recipe["files"]]
    xray = ler(source/"code/catalog/xray_resources.json")
    for key in ("runtime","model","mmproj"):
        row = xray[key]
        rows.append(("xray/"+xray["revision"]+"/"+row["filename"],row))
    for name,row in rows:
        print(name,flush=True)
        f = lung._download([row["url"]], cache/row["sha256"], row["size"],row["sha256"])
        yield "resources/"+name, f, row, "models"


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


def montar(plugin, output):
    with seed_source(plugin) as source, tempfile.TemporaryDirectory(prefix=".pacote-",dir=output) as temp:
        work = Path(temp)
        manifest_file = source/"release-manifest.json"
        meta = ler(manifest_file)
        recipe = ler(source/"code/catalog/resource_recipe.json")
        target = output/(plugin.upper().replace("-","_")+"_OFFLINE_v"+meta["version"]+".zip")
        temporary = work/"plugin.zip"
        neuro = plugin == "neuro-rt"
        materials = recursos_neuro if neuro else recursos_lung
        categories = {k:{"files":0,"bytes":0} for k in ("code","models","wheels","notices","launchers","metadata")}
        inventory = []
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
            for row in materials(source, work, recipe):
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
                marker = dict(schema="lung-rt/offline-preparation/1", complete=True, code_pin=pin)
                name = ".lung-offline-preparation.json"
            archive.writestr(zipfile.ZipInfo(name,(1980,1,1,0,0,0)),canonico(marker))
        os.replace(temporary,target)
        return target


def preparar(plugins, output):
    """Nenhum plugin é inferido da escolha de outro item."""
    if not plugins or len(set(plugins)) != len(plugins) or set(plugins)-PROFILES.keys():
        raise ValueError("Seleção de plugins inválida.")
    for plugin in plugins:
        consentimento_instalador.exigir(PROFILES[plugin])
    output.mkdir(parents=True,exist_ok=True)
    for plugin in plugins:
        if plugin == "coronarias":
            subprocess.run([sys.executable, "-B", str(APP/"radai_rocards_offline.py"), "montar", "--saida", str(output)],check=True)
        else:
            print(montar(plugin,output),flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida",type=Path,required=True)
    parser.add_argument("plugins",nargs="+",choices=PROFILES)
    args = parser.parse_args()
    preparar(args.plugins,args.saida)

