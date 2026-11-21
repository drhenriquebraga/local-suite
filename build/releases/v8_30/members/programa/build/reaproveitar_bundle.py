"""Prepara uma bancada isolada a partir do BUNDLE 8.29 verificado, sem instalar na estação."""
import argparse
import base64
import hashlib
from importlib import metadata
from pathlib import Path
import shutil
import sys
import zipfile

import runtime_rocards


BASE_SHA256 = "086bdd4d4b8e2a0e9af2101c7b724778b46cd05abc019c97948dfd74a21d541f"
RAIZ = Path(__file__).resolve().parents[1]


def digest(arquivo):
    sha = hashlib.sha256()
    with arquivo.open("rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""):
            sha.update(b)
    return sha.hexdigest()


def extrair(base, destino):
    selo = destino / ".base-829.sha256"
    if selo.exists() and selo.read_text(encoding="ascii") == BASE_SHA256:
        return
    if any(destino.iterdir()) and not (destino / ".extraindo-829").is_file():
        raise ValueError("Selecione uma pasta nova para a montagem de avaliação.")
    if digest(base) != BASE_SHA256:
        raise ValueError("O SHA-256 do arquivo de origem difere do BUNDLE 8.29 verificado.")
    (destino / ".extraindo-829").touch()
    with zipfile.ZipFile(base) as z:
        # A origem é uma versão específica conferida pelo digest acima.
        z.extractall(destino)
    selo.write_text(BASE_SHA256, encoding="ascii")
    (destino / ".extraindo-829").unlink()


def copiar_runtime(origem, alvo):
    lock = runtime_rocards.LOCK
    esperado = {linha.split("==")[0]: linha.split("==")[1]
                for linha in lock.read_text(encoding="utf-8").splitlines()
                if linha.strip() and not linha.startswith("#")}
    dists = {d.metadata["Name"].lower().replace("_", "-"): d
             for d in metadata.distributions(path=[str(origem)])}
    alvo.mkdir(parents=True, exist_ok=True)
    for nome, versao in esperado.items():
        d = dists.get(nome)
        if d is None or d.version != versao or not d.files:
            raise ValueError(f"Distribuição para cópia não confere: {nome}=={versao}")
        for arquivo in d.files:
            fonte = Path(d.locate_file(arquivo)).resolve()
            if not fonte.is_relative_to(origem) or "__pycache__" in fonte.parts or fonte.suffix == ".pyc":
                continue
            if not fonte.is_file():
                raise ValueError(f"Arquivo do runtime ausente: {arquivo}")
            rel = fonte.relative_to(origem)
            destino = alvo / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fonte, destino)
            if arquivo.hash and arquivo.hash.mode == "sha256":
                assinatura = base64.urlsafe_b64encode(bytes.fromhex(digest(destino))).decode().rstrip("=")
                if assinatura != arquivo.hash.value:
                    raise ValueError(f"Conteúdo diferente do RECORD de {nome}: {rel}")
    (alvo / runtime_rocards.RECIBO).write_text(digest(lock), encoding="ascii")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--oficina", type=Path, required=True)
    p.add_argument("--pesos", type=Path, required=True, help="Pasta models do checkout oficial ROCardS")
    p.add_argument("--runtime", type=Path, help="Dependências já obtidas na bancada, CPython 3.10")
    p.add_argument("--empacotar", action="store_true")
    args = p.parse_args()
    if args.empacotar or not args.runtime:
        import consentimento_instalador
        omitidos = consentimento_instalador.exigir("full")
    else:
        omitidos = set()
    destino = args.oficina.resolve()
    destino.mkdir(parents=True, exist_ok=True)
    extrair(args.base.resolve(), destino)
    bundle = destino / "LOCAL_SUITE"
    python = bundle / "python" / "python.exe"
    sys.path.insert(0, str(RAIZ / "app"))
    import radai_models
    import configurar_ambiente as cfg
    modelo = radai_models.MODELOS["rocards_lad"]
    motor = bundle / "modelos" / modelo["pasta"]
    for nome, tamanho in modelo["arquivos"]:
        rel = Path(nome).relative_to("models")
        fonte = args.pesos / rel
        arquivo = motor / nome
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        if nome.endswith("LICENSE_WEIGHTS"):
            arquivo.write_bytes(fonte.read_bytes().replace(b"\r\n", b"\n"))
        else:
            shutil.copy2(fonte, arquivo)
        if arquivo.stat().st_size != tamanho or digest(arquivo) != modelo["sha256"][nome]:
            raise ValueError(f"Peso ROCardS diferente do manifesto: {nome}")
    runtime = motor / "runtime"
    if args.runtime:
        if not (runtime / runtime_rocards.RECIBO).exists():
            copiar_runtime(args.runtime.resolve(), runtime)
        runtime_rocards.verificar(python, runtime)
    else:
        runtime_rocards.preparar(python, motor)
    ctx = dict(bundle=bundle, destino=destino, saida=destino / "avaliacao-pesquisa", py=python,
               profile="full", projeto="LOCAL_SUITE", versao="8.30", cache=destino / "cache",
               produto="RADIOTERAPIA_AI_LOCAL_SUITE", finalidade="pesquisa", idioma="pt-BR", preparo=None,
               instalar=False, so_cpu=False, cuda="CUDA 12.1", modelos_omitidos=omitidos)
    cfg.etapa_app(ctx)
    cfg.conferir_modelos_exigidos(bundle)
    if args.empacotar:
        cfg.etapa_empacotar(ctx)
        print(ctx["pacote"], digest(ctx["pacote"]))
    else:
        print("Montagem de avaliação verificada:", bundle)


if __name__ == "__main__":
    main()
