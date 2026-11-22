"""Preferência de acabamento da estação e amostras geométricas de referência."""
from pathlib import Path

import radai_config


CHAVE = "FAST_NIVEL"
FABRICA = 2
VALORES = frozenset(("0", "1", "2", "3", "4"))


def nivel(config):
    valor = str(config.get(CHAVE, FABRICA)).split("#", 1)[0].strip()
    return int(valor) if valor in VALORES else FABRICA


def nivel_atual(config_path=None):
    _, valores = radai_config.ler_arquivo(config_path or radai_config.caminho_padrao())
    return nivel(valores)


def montar(app):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    raiz = Path(__file__).resolve().parent / "data" / "fast_previews"

    @app.get("/api/fast/preview/{sample}/{level}")
    def preview(sample: str, level: int):
        if sample not in ("thorax", "bowel") or not 0 <= level <= 4:
            raise HTTPException(404)
        arquivo = raiz / ("%s-%d.png" % (sample, level))
        if not arquivo.is_file():
            raise HTTPException(404)
        return FileResponse(arquivo, media_type="image/png", headers={"Cache-Control": "private, no-cache"})
