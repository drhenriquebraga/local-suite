"""Instala o recorte público do visor de esforços a partir da estação, do cache ou da origem."""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

URL_BASE = "https://drhenriquebraga.com.br/_distribuicao/radioterapia-ai/local-suite/recursos/"
MEMBRO = re.compile(r"tc-study\.json|study-(?:ct|leve|medio|alto|extra|maximo|ultra)-stack-[0-9]{3}\.webp")
HEX = re.compile(r"[0-9a-f]{64}")


def catalogo(dados):
    recibo = json.loads((dados / "fast_preview_sources.json").read_bytes())["study_public"]
    recurso, arquivos = recibo["resource"], recibo["sha256"]
    nome = recurso["filename"]
    if (recibo.get("version") != 4 or recibo.get("case_id") != "s0102"
            or not re.fullmatch(r"galeria-esforcos-s0102-v[1-9][0-9]*\.zip", nome)
            or recurso.get("url") != URL_BASE + nome or not HEX.fullmatch(recurso["sha256"])
            or type(recurso["bytes"]) is not int or not 0 < recurso["bytes"] < 128 * 1024**2
            or "tc-study.json" not in arquivos or "study-ct-stack-001.webp" not in arquivos
            or not all(MEMBRO.fullmatch(n) and HEX.fullmatch(h) for n,h in arquivos.items())):
        raise ValueError("O catálogo do recorte da TC pública é inválido.")
    return recurso, arquivos


def confere(p, digest):
    return p.is_file() and not p.is_symlink() and sha256(p.read_bytes()).hexdigest() == digest


class GaleriaAusente(FileNotFoundError):
    pass


def arquivo_local(recurso, pastas):
    for pasta in pastas:
        if not pasta:
            continue
        arquivo = Path(pasta) / recurso["filename"]
        if arquivo.is_file() and arquivo.stat().st_size == recurso["bytes"] and confere(arquivo, recurso["sha256"]):
            return arquivo
    return None


def sem_rede(url, destino):
    raise GaleriaAusente("O pacote anterior não contém o recorte atual do visor de esforços. "
                         "Leve galeria-esforcos-s0102-v1.zip junto ao bundle ou atualize a estação com internet.")


def obter_pacote(recurso, cache, baixar, log):
    nome = recurso["filename"]
    pacote = cache / nome
    if pacote.is_file() and pacote.stat().st_size == recurso["bytes"] and confere(pacote, recurso["sha256"]):
        return pacote
    if baixar is sem_rede:
        sem_rede(recurso["url"], pacote)
    log("  Galeria de esforços: obtendo o recorte público s0102 (%.1f MB)." % (recurso["bytes"]/1e6))
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="s0102-", dir=cache) as temporario:
        obtido = Path(temporario) / nome
        baixar(recurso["url"], obtido)
        if obtido.stat().st_size != recurso["bytes"] or not confere(obtido, recurso["sha256"]):
            raise ValueError("O tamanho ou o SHA-256 do pacote da galeria pública diverge.")
        os.replace(obtido, pacote)
    return pacote


def instalar(dados, destino, candidatas, cache, baixar, log, *, diretorios_de_pacotes=()):
    recurso, arquivos = catalogo(dados)
    destino.mkdir(parents=True, exist_ok=True)
    fontes = [destino, *(p for p in candidatas if p is not None)]
    if all(confere(destino / n, h) for n,h in arquivos.items()):
        return
    with tempfile.TemporaryDirectory(prefix="galeria-", dir=destino.parent) as temporario:
        preparo = Path(temporario)
        faltam = {}
        for nome,h in arquivos.items():
            origem = next((p/nome for p in fontes if confere(p/nome, h)), None)
            if origem is None:
                faltam[nome] = h
            else:
                shutil.copyfile(origem, preparo/nome)
        if faltam:
            pacote = arquivo_local(recurso, diretorios_de_pacotes)
            if pacote is None:
                pacote = obter_pacote(recurso, cache or preparo, baixar, log)
            with ZipFile(pacote) as zip_:
                if sorted(zip_.namelist()) != sorted(arquivos):
                    raise ValueError("O pacote da galeria tem entradas divergentes do catálogo.")
                for n,h in faltam.items():
                    data = zip_.read(n)
                    if sha256(data).hexdigest() != h:
                        raise ValueError(f"SHA-256 divergente para a imagem pública {n}.")
                    (preparo/n).write_bytes(data)
        anteriores = preparo / "anteriores"
        anteriores.mkdir()
        alterados = []
        try:
            for n in sorted(arquivos, key=lambda n:n=="tc-study.json"):
                alvo = destino/n
                if confere(alvo, arquivos[n]):
                    continue
                if alvo.is_file():
                    shutil.copy2(alvo, anteriores/n)
                os.replace(preparo/n, alvo)
                alterados.append(n)
        except BaseException:
            for n in reversed(alterados):
                if (anteriores/n).is_file():
                    os.replace(anteriores/n, destino/n)
                else:
                    (destino/n).unlink(missing_ok=True)
            raise
        log("  Galeria de esforços pronta: recorte público s0102 verificado.")


if __name__ == "__main__":
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from configurar_ambiente import baixar

    parser = argparse.ArgumentParser()
    parser.add_argument("acao", choices=["conferir", "instalar"])
    parser.add_argument("estacao", type=Path)
    args = parser.parse_args()
    dados = Path(__file__).resolve().parents[1] / "app/data"
    destino = args.estacao / "data/fast_previews"
    cache = args.estacao / "_instalacao/cache"
    recurso, arquivos = catalogo(dados)
    vizinhas = [dados.parents[1], dados.parents[2]]
    pacotes = [item for p in vizinhas for item in (p, p/"recursos")]
    if args.acao == "conferir":
        if (not all(confere(destino / n, h) or confere(dados / "fast_previews" / n, h)
                       for n,h in arquivos.items()) and not arquivo_local(recurso, pacotes)):
            obter_pacote(recurso, cache, baixar, print)
    else:
        instalar(dados, destino, [dados / "fast_previews"], cache, baixar, print, diretorios_de_pacotes=pacotes)

