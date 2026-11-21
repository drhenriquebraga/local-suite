"""Valida o recibo individual do preparador antes da primeira operação em rede."""
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess


NOME = "LICENCAS_COMPONENTES.json"
RAIZ = Path(__file__).resolve().parents[1]


def validar(catalogo, recibo, perfil, usuario_sid, maquina):
    fonte = Path(catalogo).read_bytes()
    dados = json.loads(fonte.decode("utf-8-sig"))
    r = json.loads(Path(recibo).read_text(encoding="utf-8-sig"))
    if (dados["schema"] != "local-suite/termos/1" or r["schema"] != "local-suite/aceite/1"
            or r["catalogo_sha256"] != hashlib.sha256(fonte).hexdigest()
            or r["contexto"] != "instalador" or r["finalidade"] != "ensino-pesquisa"
            or r["perfil"] != perfil or r["usuario_sid"] != usuario_sid
            or r["maquina"].casefold() != maquina.casefold()):
        raise ValueError("O recibo pertence a outro catálogo, perfil, operador ou estação.")
    elegiveis = {it["id"]: it for it in dados["itens"] if perfil in it["perfis"]}
    obrigatorios = {ident for ident, it in elegiveis.items() if not it["opcional"]}
    aceitos = {it["id"]: it["sha256"] for it in r["itens"]}
    if (not obrigatorios or len(aceitos) != len(r["itens"]) or not obrigatorios <= aceitos.keys()
            or not aceitos.keys() <= elegiveis.keys()
            or any(elegiveis[ident]["sha256"] != sha for ident, sha in aceitos.items())):
        raise ValueError("O aceite individual das ferramentas está incompleto.")
    grupos = {it["ferramenta"] for it in elegiveis.values()}
    aceitas = {elegiveis[ident]["ferramenta"] for ident in aceitos}
    if any(ident not in aceitos for ident,it in elegiveis.items() if it["ferramenta"] in aceitas):
        raise ValueError("Falta o aceite dos componentes vinculados a uma ferramenta selecionada.")
    return grupos - aceitas


def exigir(perfil):
    cat = RAIZ / "app" / "data" / "licencas_suite.json"
    fingerprint = hashlib.sha256(cat.read_bytes()).hexdigest()
    recibo = Path(os.environ["LOCALAPPDATA"]) / "Radioterapia.AI/LocalSuite/Termos/instalador" / perfil / fingerprint / NOME
    sid = next(csv.reader([subprocess.check_output(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                                                   text=True, errors="replace").strip()]))[-1]
    try:
        return validar(cat, recibo, perfil, sid, platform.node())
    except (ValueError, KeyError, OSError) as e:
        raise SystemExit("Abra o instalador e indique os termos que aceita para esta montagem: " + str(e)) from e
