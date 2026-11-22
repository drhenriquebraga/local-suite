"""Preferência de acabamento da estação e amostras geométricas de referência."""
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import radai_config
from radai_velocidade_tc import NIVEIS as STUDY_FAST


CHAVE = "FAST_NIVEL"
FABRICA = 2
VALORES = frozenset(("0", "1", "2", "3", "4"))
AMOSTRAS = ("thorax", "upper", "bowel")
ORIGEM_STUDY_PUBLICO = {
    "case_id": "s0102", "dataset_doi": "10.5281/zenodo.10047292", "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "source_url": "https://doi.org/10.5281/zenodo.10047292",
    "source_record_url": "https://zenodo.org/records/10047292",
    "source_archive_url": "https://zenodo.org/records/10047292/files/Totalsegmentator_dataset_v201.zip",
    "source_archive_member": "s0102/ct.nii.gz", "source_version": "2.0.1",
    "source_ct_sha256": "2faf3bbef8ea3a8fb33e51997524029aeadf3983ad062eb367050c3039988d97",
    "source_member_crc32": "df86b2b0", "source_member_size_bytes": 15717424,
    "source_paper_doi": "10.1148/ryai.230024",
}


def _paleta_study(rois):
    if not isinstance(rois, dict) or not rois:
        return None
    paleta = {}
    for ident, dados in rois.items():
        if not isinstance(ident, str) or not ident.isascii() or not ident.isdigit() or not isinstance(dados, dict):
            return None
        nome, rgb = dados.get("name"), dados.get("color")
        if (not isinstance(nome, str) or not nome.strip() or not isinstance(rgb, list) or len(rgb) != 3 or
                not all(type(n) is int and 0 <= n <= 255 for n in rgb)):
            return None
        paleta[ident] = {"name": nome, "color": rgb}
    return paleta


def _tempo_study(valor):
    if type(valor) in (int, float) and math.isfinite(valor) and valor >= 0:
        return valor
    return None


def dados_para_o_visor(estudo):
    """Compara a mesma soma de etapas estimadas para todos os esforços."""
    if not estudo:
        return {}
    perfis = estudo.get("profiles", {})
    referencia = _tempo_study(perfis.get("maximo", {}).get("estimated_s"))
    saida = {}
    for chave, perfil in perfis.items():
        estimativa = _tempo_study(perfil.get("estimated_s"))
        proporcao = None
        if referencia and estimativa:
            razao = Decimal(str(estimativa)) * 1000 / Decimal(str(referencia))
            proporcao = int(razao.to_integral_value(rounding=ROUND_HALF_UP))
        saida[chave] = {k: v for k, v in perfil.items() if k not in ("estimated_s", "time_s", "write_s")}
        saida[chave]["tempo_relativo_decimos"] = proporcao
    return dict(estudo, profiles=saida)


def ler_study_fast(pasta, *, completo=True):
    """Lê a comparação do protocolo de pulmão na TC pública fixa da suíte."""
    pasta = Path(pasta)
    try:
        arq = pasta / "tc-study.json"
        dados = _ler_study_fast(pasta, arq.read_bytes(), pasta.stat().st_mtime_ns)
    except OSError:
        return {}
    if completo and dados.get("profiles", {}).keys() != STUDY_FAST.keys():
        return {}
    return dados.copy()


@lru_cache(maxsize=4)
def _ler_study_fast(pasta, conteudo, pasta_mtime):
    try:
        d = json.loads(conteudo)
    except (OSError, ValueError):
        return {}
    if not isinstance(d, dict) or d.get("version") != 3 or d.get("protocol") != "sbrt_lung" or d.get("case_id") != "s0102":
        return {}
    campos = ("firstSlice", "lastSlice", "total_slices", "tileWidth", "tileHeight", "columns", "rowsPerPage")
    if not all(type(d.get(c)) is int and d[c] > 0 for c in campos):
        return {}
    inicio, fim = d["firstSlice"], d["lastSlice"]
    pos = d.get("positionsMm")
    if (not inicio <= fim <= d["total_slices"] or d.get("orientation") != "axial-radiological" or
            d.get("superiorAt") not in ("first", "last") or not isinstance(pos, list) or
            len(pos) != fim-inicio+1 or not all(type(z) in (int, float) and math.isfinite(z) for z in pos)):
        return {}
    sinal = 1 if d["superiorAt"] == "last" else -1
    if any((b-a)*sinal <= 0 for a,b in zip(pos, pos[1:])) or not isinstance(d.get("profiles"),dict):
        return {}
    slots = d["columns"] * d["rowsPerPage"]
    qtd = (len(pos) + slots - 1) // slots
    perfis = {}
    for ident, (mm, finish) in STUDY_FAST.items():
        perfil = d["profiles"].get(ident)
        if (not isinstance(perfil, dict) or perfil.get("source") != "RTSTRUCT_STUDY" or
                perfil.get("mm") != mm or type(perfil.get("finish")) is not int or perfil["finish"] != finish or
                perfil.get("body_mm") != (1.5 if ident == "ultra" else 6)):
            continue
        rois = _paleta_study(perfil.get("rois"))
        listas = perfil.get("labelsBySlice")
        paginas = [f"study-{ident}-stack-{n:03d}.webp" for n in range(1, qtd+1)]
        if (not rois or not isinstance(listas,list) or len(listas) != len(pos) or
                not all(isinstance(ls, list) and all(isinstance(k,str) and k in rois for k in ls)
                        and len(set(ls)) == len(ls) for ls in listas) or
                perfil.get("pages") != paginas or not all((pasta / p).is_file() for p in paginas)):
            continue
        perfis[ident] = {"mm": mm, "finish": finish, "body_mm": perfil["body_mm"], "source": "RTSTRUCT_STUDY", "rois": rois,
                         "labelsBySlice": listas, "pages": paginas, "time_s": _tempo_study(perfil.get("time_s")),
                         "write_s": _tempo_study(perfil.get("write_s")),
                         "estimated_s": _tempo_study(perfil.get("estimated_s")),
                         "used_cache": perfil.get("used_cache") is True}
        efetivo = perfil.get("effective_mm", mm)
        tentativas = perfil.get("base_attempts_mm", [mm])
        if (efetivo not in ("6", "3", "1.5") or not isinstance(tentativas, list) or not tentativas or
                tentativas[0] != mm or tentativas[-1] != efetivo or any(t not in ("6", "3", "1.5") for t in tentativas)):
            del perfis[ident]
            continue
        perfis[ident].update(effective_mm=efetivo, base_attempts_mm=tentativas)
        nomes = perfil.get("model_names", [])
        if isinstance(nomes, list) and all(isinstance(n,str) and n.strip() for n in nomes):
            perfis[ident]["model_names"] = nomes
    if not perfis:
        return {}
    saida = {k:d[k] for k in (*campos, "orientation", "superiorAt", "positionsMm", "protocol", "version")}
    if d.get("case_id") == "s0102":
        saida["case_id"] = "s0102"
    if type(d.get("source_member_size_bytes")) is int:
        saida["source_member_size_bytes"] = d["source_member_size_bytes"]
    for chave in ("source_record_url", "source_archive_url", "source_archive_member",
                  "source_version", "source_ct_sha256", "source_member_crc32", "source_paper_doi",
                  "source_url", "author", "dataset_doi", "license", "license_url"):
        if isinstance(d.get(chave), str):
            saida[chave] = d[chave]
    saida["profiles"] = perfis
    return saida


def estudo_de_referencia(pasta, fontes, *, completo=True):
    """Confere a ficha de procedência da mesma TC antes de expor o visor."""
    dados = ler_study_fast(pasta, completo=completo)
    registro = fontes.get("study_public") if isinstance(fontes, dict) else None
    if not isinstance(registro, dict):
        return {}
    if (any(registro.get(k) != v or dados.get(k) != v for k, v in ORIGEM_STUDY_PUBLICO.items())
            or not dados.get("author", "").strip()):
        return {}
    dados.update(kind="reference_ct", source=dados["author"]+" · TotalSegmentator CT v"+dados["source_version"]+" · "+dados["case_id"],
                 url=dados["source_url"])
    return dados




def nivel(config):
    valor = str(config.get(CHAVE, FABRICA)).split("#", 1)[0].strip()
    return int(valor) if valor in VALORES else FABRICA


def nivel_atual(config_path=None):
    _, valores = radai_config.ler_arquivo(config_path or radai_config.caminho_padrao())
    return nivel(valores)


def montar(app):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse, JSONResponse

    raiz = Path(__file__).resolve().parent / "data" / "fast_previews"
    ficha = raiz.parent / "fast_preview_sources.json"
    try:
        fontes = json.loads(ficha.read_text(encoding="utf-8")) if ficha.is_file() else {}
    except (OSError, ValueError):
        fontes = {}

    def credito_publico(amostra):
        item = fontes.get(amostra, {}) if isinstance(fontes, dict) else {}
        if not isinstance(item, dict) or item.get("kind") != "reference_ct":
            return {"kind": "phantom"}
        campos = ("source", "url", "license", "license_url")
        if not all(isinstance(item.get(k), str) and item[k].strip() for k in campos):
            return {"kind": "reference_ct"}
        if not all(urlsplit(item[k]).scheme == "https" and urlsplit(item[k]).hostname
                   for k in ("url", "license_url")):
            return {"kind": "reference_ct"}
        dados = {"kind": "reference_ct", **{k: item[k] for k in campos}}
        if amostra == "upper" and item.get("source_labels") == ["liver", "stomach", "duodenum", "spleen", "pancreas"]:
            dados["organ_masks"] = "atlas"
        return dados

    @app.get("/api/fast/galeria")
    def galeria():
        return JSONResponse({s: credito_publico(s) for s in AMOSTRAS}, headers={"Cache-Control": "no-store"})

    def estudo_publico():
        return estudo_de_referencia(raiz, fontes, completo=False)

    @app.get("/api/fast/study")
    def estudo():
        return JSONResponse(dados_para_o_visor(estudo_publico()), headers={"Cache-Control":"no-store"})

    @app.get("/api/fast/study/{ident}/{page}")
    def imagem_study(ident: str, page: int, local: bool = False):
        if ident not in STUDY_FAST or local:
            raise HTTPException(404)
        pasta = raiz
        estudo = estudo_publico()
        paginas = estudo.get("profiles", {}).get(ident, {}).get("pages", [])
        if not 1 <= page <= len(paginas):
            raise HTTPException(404)
        return FileResponse(pasta / paginas[page-1], media_type="image/webp", headers={
            "Cache-Control":"no-store" if local else "private, no-cache", "Cross-Origin-Resource-Policy":"same-origin"})

    @app.get("/api/fast/preview/{sample}/{level}")
    def preview(sample: str, level: int, local: bool = False):
        if sample not in AMOSTRAS or not 0 <= level <= 4:
            raise HTTPException(404)
        pasta = raiz
        if local:
            raise HTTPException(404)
        arquivo = pasta / ("%s-%d.png" % (sample, level))
        if not arquivo.is_file():
            raise HTTPException(404)
        return FileResponse(arquivo, media_type="image/png", headers={
            "Cache-Control": "no-store" if local else "private, no-cache",
            "Cross-Origin-Resource-Policy": "same-origin"})
