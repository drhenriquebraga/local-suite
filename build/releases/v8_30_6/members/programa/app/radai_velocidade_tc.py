"""Resolução da rede de base em TC, congelada com a escolha da série."""
CHAVE = "FAST_TC_MM"
PADRAO = "1.5"
VALORES = frozenset((PADRAO, "3", "6"))


def mm_config(config):
    valor = str(config.get(CHAVE, PADRAO)).split("#", 1)[0].strip()
    return valor if valor in VALORES else PADRAO


def mm_atual(config_path=None):
    import radai_config
    _, valores = radai_config.ler_arquivo(config_path or radai_config.caminho_padrao())
    return mm_config(valores)


ESFORCO_PADRAO = "ESFORCO_PADRAO"
FABRICA = "maximo"
# (resolução do total_v3 em mm, nível de acabamento)
NIVEIS = {"leve": ("6", 0), "medio": ("3", 1), "alto": ("1.5", 2),
          "extra": ("1.5", 3), "maximo": ("1.5", 4), "ultra": ("1.5", 4)}


def normalizar_esforco(valor):
    valor = str(valor or "").split("#", 1)[0].strip().lower()
    return valor if valor in NIVEIS else FABRICA


def esforco_atual(config_path=None):
    import radai_config
    _, valores = radai_config.ler_arquivo(config_path or radai_config.caminho_padrao())
    return normalizar_esforco(valores.get(ESFORCO_PADRAO))


def esforco_legado(serie):
    if serie.get("esforco") in NIVEIS:
        return serie["esforco"]
    mm = serie.get("fast_tc_mm") if (serie.get("modo") == "auto" or serie.get("acabamento") == "fast") else None
    if mm in ("3", "6"):
        return "medio" if mm == "3" else "leve"
    if serie.get("acabamento") == "fast":
        from radai_fast_config import nivel
        return ("alto", "alto", "alto", "extra", FABRICA)[nivel({"FAST_NIVEL": serie.get("fast_nivel", 2)})]
    return FABRICA


def mm_da_escolha(escolha, base):
    if base != "total_v3" or escolha.get("modalidade") != "CT":
        return PADRAO
    return NIVEIS[normalizar_esforco(escolha.get("esforco"))][0]


def faltantes_no_campo(base, destinos):
    # As âncoras documentam a presença do andar superior do abdome. Uma TC
    # de tórax que só inclui a cúpula hepática não dispara a repetição.
    presentes = set(base or ())
    precisa_vesicula = {"gallbladder", "bag_bowel_oar", "bag_bowel", "abdominal_cavity"} & set(destinos)
    if precisa_vesicula and {"liver", "duodenum", "pancreas"} <= presentes and "gallbladder" not in presentes:
        return {"gallbladder"}
    return set()
