"""Observa a trava do dono. Quando liberada após queda, restaura só a rodada correspondente."""
import os
import sys
import time

sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))

import radai_dedicado as modo
import radai_dedicado_windows as windows


def vigiar(sessao, pasta, plataforma, intervalo=3):
    import json
    caminho=pasta / "dedicado.json"
    pronto = pasta / ("dedicado-vigia-" + sessao + ".ok")
    confirmou = False
    try:
        while caminho.is_file():
            try:
                reg=json.loads(caminho.read_text(encoding="utf-8"))
                if reg["sessao"] != sessao:
                    return
                falta_devolver = any(modo._automatico(a["item"]) for a in modo.pendentes(reg))
                if reg.get("terminou") and not falta_devolver:
                    return
                if not confirmou:
                    modo.gravar(pronto, {"sessao": sessao, "pid": os.getpid()})
                    confirmou = True
                if modo.recuperar(pasta,plataforma,sessao):
                    return
            except (ValueError, KeyError, OSError):
                pass
            time.sleep(intervalo)
    finally:
        pronto.unlink(missing_ok=True)


if __name__=="__main__":
    if len(sys.argv)!=2 or len(sys.argv[1])!=32:
        raise SystemExit(2)
    vigiar(sys.argv[1],modo.pasta_local(),windows)
