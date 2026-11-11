# -*- coding: utf-8 -*-

ARVORE = {
    "inicio":       (u"Radioterapia.AI Local", "/",              ""),

    "bridge":       (u"DicomBridge",           "/bridge",        "inicio"),
    "autocontorno": (u"ContourLab",            "/autocontorno",  "inicio"),
    "recon3d":      (u"Reconstruções 3D",      "/recon3d",       "inicio"),
    "neuro":        (u"NEURO RT",              "/neuro",         "inicio"),
    "nidus":        (u"Nidus RT",              "/neuro/nidus",   "neuro"),
    "neuro_glioma": (u"Glioma RT",             "/neuro/glioma",  "neuro"),
    "neuro_metastasis": (u"Metastasis RT",     "/neuro/metastasis", "neuro"),
    "neuro_meningioma": (u"Meningioma RT",     "/neuro/meningioma", "neuro"),
    "neuro_anatomia": (u"AutoContorno Neuro",         "/neuro/anatomia", "neuro"),
    "elastic":      (u"Fusão elástica",         "/bridge/elastic", "bridge"),
    "lung":         (u"LUNG RT",               "/lung",          "inicio"),
    "lung_nodulos": (u"Rastreio de nódulos pulmonares", "/lung/nodulos", "lung"),
    "lung_rastreio": (u"Rastreio populacional", "/lung/rastreio", "lung"),
    "lung_laudo": (u"Laudo sintético", "/lung/laudo", "lung"),
    "lung_laudo_rx": (u"Laudo sintético de raios X", "/lung/laudo/rx", "lung"),
    "lung_4d":      (u"4D CT & ITV", "/lung/4d", "lung"),
    "bolus":        (u"3D Printed Bolus",      "/bolus",         "inicio"),

    "config":       (u"Configurações",         "/config",        "inicio"),

    "lote":         (u"Rodar agora",           "/lote",          "autocontorno"),
    "ver":          (u"Ver segmentações",       "/ver",           "autocontorno"),
    "vigia":        (u"Overnight Run · Vigia", "/vigia",         "autocontorno"),

    "nidus_projecao": (u"NIDUS RT",  "/nidus/projecao", "neuro"),
    "elastic_fusao":  (u"Fusão elástica",     "/bridge/elastic", "bridge"),
    "bolus_gerar":    (u"Bólus e caixa",      "/bolus/gerar",    "bolus"),
    "bolus_aplicador": (u"Aplicador de braquiterapia de superfície", "/bolus/aplicador", "bolus"),
    "bibliografia": (u"Bibliografia",          "/bibliografia",  "inicio"),

    "bridge_laudo": (u"Converter imagens para o TPS",
                     "/bridge/laudo",  "bridge"),
    "recon_anatomia": (u"Anatomia geral",      "/recon3d/anatomia", "recon3d"),
    "recon_torax":    (u"Anatomia torácica",   "/recon3d/toracica", "recon3d"),
    "recon_vascular": (u"Vascular",            "/recon3d/vascular", "recon3d"),
    "procedencia":  (u"Procedência",           "/procedencia",   "config"),
    "creditos":     (u"Créditos e licenças",    "/creditos",      "config"),
    "termos":       (u"Termos de Uso",          "/termos",        "config"),
    "politica":     (u"Política de Privacidade",
                     "/politica-privacidade", "config"),
    "diagnostico":  (u"Diagnóstico",           "/diagnostico",   "config"),
}

RAIZ = "inicio"


def trilha(chave):
    caminho, visto = [], set()
    c = str(chave or "")
    while c and c in ARVORE and c not in visto:
        visto.add(c)
        rot, rota, pai = ARVORE[c]
        caminho.append((rot, rota))
        c = pai
    caminho.reverse()
    return caminho


def pai(chave):
    c = str(chave or "")
    if c not in ARVORE:
        return None
    p = ARVORE[c][2]
    if not p or p not in ARVORE:
        return None
    rot, rota, _ = ARVORE[p]
    return (rot, rota)


def filhos(chave):
    return [k for k, v in ARVORE.items() if v[2] == str(chave or "")]


def rota(chave):
    return ARVORE.get(str(chave or ""), (u"", "", ""))[1]


def rotulo(chave):
    return ARVORE.get(str(chave or ""), (u"", "", ""))[0]
