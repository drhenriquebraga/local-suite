"""Prepara uma bancada isolada a partir do BUNDLE 8.29 verificado, sem instalar na estação."""
import argparse
import hashlib
from pathlib import Path
import sys
import zipfile



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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--oficina", type=Path, required=True)
    p.add_argument("--empacotar", action="store_true")
    args = p.parse_args()
    import consentimento_instalador
    omitidos = consentimento_instalador.exigir("full")
    destino = args.oficina.resolve()
    destino.mkdir(parents=True, exist_ok=True)
    extrair(args.base.resolve(), destino)
    bundle = destino / "LOCAL_SUITE"
    python = bundle / "python" / "python.exe"
    sys.path.insert(0, str(RAIZ / "app"))
    import configurar_ambiente as cfg
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
