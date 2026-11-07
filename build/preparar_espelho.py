import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

PRODUTO = "RADIOTERAPIA_AI_LOCAL_SUITE"
LATEST = PRODUTO + "_SETUP_LATEST.zip"
SUBPASTA = Path("_distribuicao/radioterapia-ai/local-suite/atualizacoes")
CABECALHOS = """Options -Indexes
<IfModule mod_headers.c>
    Header always set X-Robots-Tag "noindex, nofollow, noarchive"
    <Files "latest.json">
        Header always set Cache-Control "no-store, must-revalidate"
    </Files>
</IfModule>
"""


def preparar(arquivo, destino):
    arquivo, destino = Path(arquivo), Path(destino)
    m = re.fullmatch(PRODUTO + r"_SETUP_v([0-9]{1,4}(?:\.[0-9]{1,4}){1,3})\.zip",
                     arquivo.name)
    if not m or not 0 < arquivo.stat().st_size <= 256 * 1024 * 1024:
        raise ValueError("A entrada deve ser o SETUP leve e versionado da Local Suite.")
    v = m.group(1)
    with zipfile.ZipFile(arquivo) as z:
        if ("START_HERE.cmd" not in z.namelist()
                or "programa/packager/UPDATE.ps1" not in z.namelist()
                or any(x.lower().startswith(("programa/python/", "programa/ts_weights/",
                                             "programa/modelos/")) for x in z.namelist())
                or z.testzip()):
            raise ValueError("O arquivo não é um SETUP leve íntegro.")
        entrega = z.read("programa/entrega.txt").decode("utf-8-sig").splitlines()
        if "PROJETO=LOCAL_SUITE" not in entrega or ("VERSAO=" + v) not in entrega:
            raise ValueError("O carimbo do SETUP não corresponde ao nome.")
    raiz = destino / SUBPASTA
    if raiz.exists():
        raise FileExistsError("Use uma pasta de publicação local nova.")
    p = raiz / ("v" + v)
    p.mkdir(parents=True)
    shutil.copyfile(arquivo, p / LATEST)
    sha = hashlib.sha256()
    with (p / LATEST).open("rb") as f:
        for bloco in iter(lambda: f.read(256 * 1024), b""):
            sha.update(bloco)
    (raiz / ".htaccess").write_text(CABECALHOS, encoding="ascii", newline="\n")
    (raiz / "latest.json").write_text(json.dumps(
        {"schema": "local-suite-update/1", "version": v,
         "size": (p / LATEST).stat().st_size, "sha256": sha.hexdigest()},
        separators=(",", ":")) + "\n", encoding="ascii", newline="\n")
    return raiz, sha.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Prepara a cópia HTTP do SETUP leve.")
    ap.add_argument("setup")
    ap.add_argument("destino")
    args = ap.parse_args()
    raiz, sha = preparar(args.setup, args.destino)
    print(f"{raiz}\nSHA-256 {sha}")


if __name__ == "__main__":
    main()
