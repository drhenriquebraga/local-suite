"""Verifica os recursos obrigatórios da estação antes de aceitar um bundle portátil."""
import hashlib
import json
import os
from pathlib import Path
import sys


def validar(raiz):
    sys.path.insert(0, str(raiz))
    import radai_models

    os.environ["RADAI_MODELOS_DIR"] = str(raiz / "modelos")
    perfil = raiz / "suite-profile.json"
    dados = json.loads(perfil.read_text(encoding="utf-8-sig")) if perfil.exists() else {}
    modelos = ["rocards_lad", "moose_ribs"]
    if dados.get("profile", "full") != "lung-rt":
        modelos.append("jhu_rectum")
    for ident in modelos:
        m = radai_models.MODELOS[ident]
        estado = radai_models.estado_do_modelo(ident)
        if not estado["instalado"]:
            raise ValueError(f"{ident}: faltam {', '.join(estado['faltando'])}")
        pasta = Path(estado["pasta"])
        for nome, _ in m.get("conteudo") or m["arquivos"]:
            sha = hashlib.sha256()
            with (pasta / nome).open("rb") as f:
                for bloco in iter(lambda: f.read(4 << 20), b""):
                    sha.update(bloco)
            if sha.hexdigest() != m["sha256"][nome]:
                raise ValueError(f"{ident}: falha de integridade em {nome}")
    runtime = raiz / "modelos" / "rocards" / "runtime"
    sys.path.insert(0, str(runtime))
    import tensorflow
    import keras
    for modulo in (tensorflow, keras):
        if modulo.__version__ != "2.10.0" or not Path(modulo.__file__).resolve().is_relative_to(runtime.resolve()):
            raise ValueError(f"Runtime ROCardS inválido: {modulo.__name__}")


if __name__ == "__main__":
    validar(Path(sys.argv[1]).resolve())
