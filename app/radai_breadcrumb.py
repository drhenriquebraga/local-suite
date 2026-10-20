# -*- coding: utf-8 -*-

ARVORE = {
    "inicio":       (u"Radioterapia.AI Local", "/",              ""),

    "bridge":       (u"DicomBridge",           "/bridge",        "inicio"),
    "autocontorno": (u"ContourLab",            "/autocontorno",  "inicio"),
    "recon3d":      (u"Reconstruções 3D",      "/recon3d",       "inicio"),
    "nidus":        (u"Nidus RT",              "/nidus",         "inicio"),
    "elastic":      (u"Elastic RT",            "/elastic",       "inicio"),
    "bolus":        (u"3D Printed Bolus",      "/bolus",         "inicio"),

    "config":       (u"Configurações",         "/config",        "inicio"),

    "lote":         (u"Rodar agora",           "/lote",          "autocontorno"),
    "ver":          (u"Ver segmentação",       "/ver",           "autocontorno"),
    "vigia":        (u"Fila de estudo",       "/vigia",         "autocontorno"),

    "nidus_projecao": (u"Projeção Vascular",  "/nidus/projecao", "nidus"),
    "elastic_fusao":  (u"Fusão elástica",     "/elastic/fusao",  "elastic"),
    "bolus_gerar":    (u"Gerar bólus",        "/bolus/gerar",    "bolus"),
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
