"""Preferências portáveis do plugin NEURO, inclusive quando ele está ausente."""
import json
import re
from pathlib import Path
import radai_config as C

ARQUIVO = "protocolos_neuro.json"
SCHEMA = "neuro-rt/protocols/1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")


def colecao(doc):
    def rejeitar():
        raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
    if (not isinstance(doc, dict) or set(doc) != {"schema", "protocols"} or doc["schema"] != SCHEMA
            or not isinstance(doc["protocols"],list) or len(doc["protocols"]) > 200
            or len(json.dumps(doc,ensure_ascii=False).encode("utf-8")) > 2*1024*1024):
        rejeitar()
    ids, nomes = set(), set()
    for row in doc["protocols"]:
        if not isinstance(row,dict) or set(row) != {"id","name","modality","plan"}:
            rejeitar()
        nome, ident, mod, plano = row["name"], row["id"], row["modality"], row["plan"]
        if (not isinstance(ident,str) or not re.fullmatch("p[a-f0-9]{32}",ident) or ident in ids
                or not isinstance(nome,str) or nome != nome.strip() or not 1 <= len(nome) <= 80
                or not nome.isprintable() or mod not in ("MR","CT") or (mod,nome.casefold()) in nomes):
            rejeitar()
        ids.add(ident)
        nomes.add((mod,nome.casefold()))
        if not isinstance(plano,dict) or set(plano) != {"anatomy","findings","rois"}:
            rejeitar()
        anat, achados, rois = plano["anatomy"],plano["findings"],plano["rois"]
        if (anat is not None and anat not in (("snc_rm_simples","snc_rm_avancado","anatomy_cerebra_ants")
                if mod == "MR" else ("cranio_buti",))):
            rejeitar()
        if (not isinstance(achados,list) or len(achados)>32 or (achados and mod != "MR")
                or not all(isinstance(k,str) and ID.fullmatch(k) and
                    (k.startswith("MRI_") or k == "glioma_attention_unet3d") for k in achados)
                or len(set(achados)) != len(achados) or not isinstance(rois,dict)):
            rejeitar()
        motores = set(achados)
        if anat:
            motores.add("anatomy_synthseg" if anat.startswith("snc_rm_") else anat)
        if set(rois) != motores or not any(rois.values()):
            rejeitar()
        for lista in rois.values():
            if (not isinstance(lista,list) or len(lista)>256 or
                    not all(isinstance(k,str) and ID.fullmatch(k) for k in lista) or len(set(lista))!=len(lista)):
                rejeitar()
    return doc


def ler(cfg):
    path = Path(cfg).with_name(ARQUIVO)
    if not path.exists():
        return {"schema":SCHEMA, "protocols":[]}
    if path.stat().st_size > 2*1024*1024:
        raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
    try:
        return colecao(json.loads(path.read_text(encoding="utf-8-sig")))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO) from exc


def mesclar(cfg, recebido, substituir):
    atuais = list(ler(cfg)["protocols"])
    grupos = {"iguais":[], "conflitos":[], "novos":[]}
    for row in colecao(recebido)["protocols"]:
        iguais = [n for n,old in enumerate(atuais) if row["id"] == old["id"] or
            (row["modality"],row["name"].casefold()) == (old["modality"],old["name"].casefold())]
        if len(iguais)>1:
            raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
        if iguais:
            n = iguais[0]
            novo = dict(row,id=atuais[n]["id"])
            grupo = "iguais" if atuais[n] == novo else "conflitos"
            if substituir:
                atuais[n] = novo
        else:
            grupo = "novos"
            atuais.append(row)
        grupos[grupo].append({"nome":row["name"], "modalidade":row["modality"]+" · NEURO"})
    return colecao({"schema":SCHEMA, "protocols":atuais}), grupos
