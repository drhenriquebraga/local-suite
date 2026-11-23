"""Verifica o aceite da estação para as condições efetivas dos recursos selecionados."""
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess


NOME = "LICENCAS_COMPONENTES.json"
RAIZ = Path(__file__).resolve().parents[1]


def carregar(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8-sig"))


def assinatura(item, condicao):
    dados = (item["id"], item["licenca_codigo"], item["licenca_pesos"],
             condicao["revisao"], condicao["url"], condicao["en"])
    return hashlib.sha256("\n".join(dados).encode("utf-8")).hexdigest()


def validar(catalogo, recibo, perfil, usuario_sid, maquina):
    catalogo = Path(catalogo)
    politica = carregar(catalogo.with_name("termos_instalador.json"))
    dados = carregar(catalogo)
    r = carregar(recibo)
    if (dados["schema"] != "local-suite/termos/1" or politica["schema"] != "local-suite/condicoes-instalador/1"
            or r["contexto"] != "instalador" or r["finalidade"] != "ensino-pesquisa"
            or r["perfil"] != perfil or r["usuario_sid"] != usuario_sid
            or r["maquina"].casefold() != maquina.casefold()):
        raise ValueError("O aceite pertence a outro operador, finalidade, perfil ou estação.")
    elegiveis = {it["id"]: it for it in dados["itens"] if perfil in it["perfis"]}
    if not elegiveis:
        raise ValueError("Perfil desconhecido.")
    opcionais = {i["ferramenta"] for i in elegiveis.values() if i["opcional"] and not perfil.startswith("plugin-")}
    aceitos = {i["id"]: i["sha256"] for i in r["itens"]}
    if len(aceitos) != len(r["itens"]):
        raise ValueError("Componente repetido no aceite.")
    condicoes = politica["condicoes"]
    if r["schema"] == "local-suite/aceite/1":
        if r["catalogo_sha256"] != politica["catalogo_830"]:
            raise ValueError("O catálogo do aceite anterior não é reconhecido.")
        if hashlib.sha256(catalogo.read_bytes()).hexdigest() == r["catalogo_sha256"]:
            obrigatorios = {k for k, i in elegiveis.items() if not i["opcional"]}
            if (not obrigatorios <= aceitos.keys() or not aceitos.keys() <= elegiveis.keys()
                    or any(elegiveis[k]["sha256"] != v for k, v in aceitos.items())):
                raise ValueError("O recibo da versão anterior está incompleto.")
        omitidos = set()
        for grupo in opcionais:
            ids = {k for k,i in elegiveis.items() if i["ferramenta"] == grupo}
            escolhidos = ids & aceitos.keys()
            if not escolhidos:
                omitidos.add(grupo)
            elif escolhidos != ids:
                raise ValueError("Seleção parcial de um comparador no aceite anterior.")
        aceitos = {k: c["condicao_830"] for k,c in condicoes.items()
                   if c.get("sha_item_830") and aceitos.get(k) == c["sha_item_830"]}
    elif r["schema"] == "local-suite/aceite/2" and r["revisao_finalidade"] == politica["revisao_finalidade"]:
        omitidos = set(r["omitidos"])
        if not omitidos <= opcionais or len(omitidos) != len(r["omitidos"]):
            raise ValueError("Seleção inválida de recursos opcionais.")
    else:
        raise ValueError("O registro de aceite não corresponde aos termos desta instalação.")
    for k, item in elegiveis.items():
        if k in condicoes and item["ferramenta"] not in omitidos:
            if aceitos.get(k) != assinatura(item, condicoes[k]):
                raise ValueError("Termos novos ou alterados para " + item["titulo"])
    return omitidos


def exigir(perfil, catalogo=None):
    cat = Path(catalogo) if catalogo else RAIZ / "app/data/licencas_suite.json"
    politica = carregar(cat.with_name("termos_instalador.json"))
    if perfil.startswith("plugin-"):
        itens = [i for i in carregar(cat)["itens"] if perfil in i["perfis"]]
        if itens and not any(i["id"] in politica["condicoes"] for i in itens):
            return set()
    base = Path(os.environ["LOCALAPPDATA"]) / "Radioterapia.AI/LocalSuite/Termos/instalador" / perfil
    novo = base / "vigente" / NOME
    recibo = novo if novo.exists() else base / politica["catalogo_830"] / NOME
    sid = next(csv.reader([subprocess.check_output(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                                                   text=True, errors="replace").strip()]))[-1]
    try:
        return validar(cat, recibo, perfil, sid, platform.node())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise SystemExit("Abra a tela de termos do instalador: " + str(exc)) from exc

