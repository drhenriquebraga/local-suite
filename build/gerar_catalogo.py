# -*- coding: utf-8 -*-
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, os.path.join(RAIZ, "tools"))
import _componentes
_componentes.ligar_caminho(RAIZ)

DESTINO = os.path.join(RAIZ, "packager", "catalogo.json")


def _bytes_do_modelo(m):
    n = 0
    for chave in ("arquivos", "volumes"):
        for a in (m.get(chave) or []):
            if (isinstance(a, (tuple, list)) and len(a) >= 2
                    and isinstance(a[1], int)):
                n += a[1]
    return n


def montar():
    import radai_tasks
    import radai_models
    import engine

    reservas = getattr(radai_tasks, "RESERVAS", frozenset())
    tasks = []
    for d in radai_tasks.CATALOGO:
        if d["task"] in reservas:
            continue
        if not d.get("datasets"):
            continue
        tasks.append({
            "task": d["task"],
            "rotulo": d.get("rotulo", d["task"]),
            "mb": int(d.get("mb") or 0),
            "classes": int(d.get("classes") or 0),
            "modalidade": d.get("modalidade", "CT"),
            "nucleo": bool(engine.alimenta_o_entregue(d["task"])),
            "achado": "ACHADO" in (d.get("rotulo") or "").upper(),
        })

    modelos = []
    for ident, m in sorted(radai_models.MODELOS.items()):
        bytes_ = _bytes_do_modelo(m)
        modelos.append({
            "id": ident,
            "nome": m.get("nome") or ident,
            "licenca": m.get("licenca") or "",
            "nucleo": bool(m.get("embutido")),
            "gpu_min_gb": m.get("gpu_min_gb"),
            "mb": int(round(bytes_ / 1048576.0)),
            "sha256_conferidos": (len(m.get("sha256") or {})
                                  + len(m.get("sha256_dos_volumes") or {})),
        })

    sem_tamanho = [d["id"] for d in modelos if not d["nucleo"] and d["mb"] <= 0]
    if sem_tamanho:
        raise ValueError(
            "modelo(s) sem tamanho derivavel: %s. "
            "Declare `arquivos` ou `volumes` com pares (nome, bytes) em "
            "radai_models.MODELOS -- sem isso o tamanho do pacote "
            "(`pacote` no catalogo.json) subestima o download."
            % ", ".join(sem_tamanho))

    return {
        "_gerado_por": "build/gerar_catalogo.py",
        "_leia": ("Copia verificada de radai_tasks.CATALOGO e "
                  "radai_models.MODELOS. Nao editar a mao: "
                  "tools/test_packager.py recompara contra o Python vivo."),
        "tasks": tasks,
        "modelos": modelos,
        "pacote": tamanho_do_pacote(tasks, modelos),
    }


BASE_GIB = 5.72
FATOR_DISCO = 1.10
FOLGA_GIB = 2


def disco_para_preparar(pacote_gib):
    import math
    return float(math.ceil(2 * pacote_gib - 1e-9) + FOLGA_GIB)


def tamanho_do_pacote(tasks, modelos):
    comparacao = [m for m in modelos if not m["nucleo"]]
    mb = sum(t["mb"] for t in tasks) + sum(m["mb"] for m in comparacao)
    download = mb / 1024.0
    pacote = round(BASE_GIB + FATOR_DISCO * download, 1)
    return {
        "tarefas": len(tasks),
        "modelos": len(comparacao),
        "download_gib": round(download, 1),
        "pacote_gib": pacote,
        "disco_gib": disco_para_preparar(pacote),
        "folga_gib": FOLGA_GIB,
        "base_gib": BASE_GIB,
        "fator_disco": FATOR_DISCO,
        "_leia": ("pacote = base + fator x download, em GiB (o que o Explorer "
                  "mostra). base e fator medidos numa montagem completa do "
                  "pacote; download = soma do catalogo. disco = "
                  "teto(2 x pacote) + folga (montagem e .zip convivem; a "
                  "folga e nossa). Ver build/gerar_catalogo.py."),
    }


def main():
    dados = montar()
    texto = json.dumps(dados, ensure_ascii=False, indent=1, sort_keys=False)
    io.open(DESTINO, "w", encoding="utf-8", newline="\n").write(texto + "\n")
    nuc = [t for t in dados["tasks"] if t["nucleo"]]
    plug = [t for t in dados["tasks"] if not t["nucleo"]]
    print("catalogo.json: %d task(s), %d modelo(s)"
          % (len(dados["tasks"]), len(dados["modelos"])))
    print("  nucleo  %2d task(s)  %6.2f GB"
          % (len(nuc), sum(t["mb"] for t in nuc) / 1024.0))
    print("  plugin  %2d task(s)  %6.2f GB"
          % (len(plug), sum(t["mb"] for t in plug) / 1024.0))
    mplug = [m for m in dados["modelos"] if not m["nucleo"]]
    print("  plugin  %2d modelo(s) %5.2f GB"
          % (len(mplug), sum(m["mb"] for m in mplug) / 1024.0))
    p = dados["pacote"]
    print("  download          %6.2f GiB" % p["download_gib"])
    print("  PACOTE COMPLETO   %6.2f GiB   (disco para preparar: %.1f GiB)"
          % (p["pacote_gib"], p["disco_gib"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
