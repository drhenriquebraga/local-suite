# -*- coding: utf-8 -*-
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import _componentes
_componentes.ligar_caminho(os.path.dirname(AQUI))
import _cleanup
_cleanup.adotar_prefixo('radai_est_')

_TEMPS = []


def novo_temp(prefixo="radai_est_"):
    d = tempfile.mkdtemp(prefix=prefixo)
    _TEMPS.append(d)
    return d


os.environ["RADAI_CALIB_DIR"] = novo_temp("radai_est_acervo_")
os.environ["RADAI_FILA_DIR"] = novo_temp("radai_est_fila_")
os.environ["RADAI_REGISTRO_DIR"] = novo_temp("radai_est_reg_")
os.environ["RADAI_URL_VERSOES"] = "0"

import radai_config as C

VERBOSO = "-v" in sys.argv
_RESULTADOS = []


def checar(nome, condicao, detalhe=""):
    ok = bool(condicao)
    _RESULTADOS.append((nome, ok, detalhe))
    if VERBOSO or not ok:
        print(u"  %s  %s%s" % ("OK   " if ok else "FALHA", nome,
                               (u"  [%s]" % detalhe) if detalhe else u""))
    return ok


def secao(t):
    print(u"\n-- %s " % t + u"-" * max(0, 58 - len(t)))


LINHAS = {
    "CT": [
        {"task": "total", "nome_padrao": "Liver_ai", "chave_anatomica": "liver",
         "no_study": True},
        {"task": "total", "nome_padrao": "Spleen_ai", "chave_anatomica": "spleen",
         "no_study": True},
        {"task": "total", "nome_padrao": "Lung_L_ai", "chave_anatomica": "lung_left",
         "no_study": True},
        {"task": "total", "nome_padrao": "Lung_R_ai", "chave_anatomica": "lung_right",
         "no_study": True},
        {"task": "total", "nome_padrao": "Rib01_L_ai", "chave_anatomica": "rib_left_1",
         "no_study": False},
        {"task": "lung_nodules", "nome_padrao": "LungNodules_nod",
         "chave_anatomica": "lung_nodules", "no_study": False},
    ],
    "MR": [
        {"task": "total_mr", "nome_padrao": "Liver_ai", "chave_anatomica": "liver",
         "no_study": True},
        {"task": "total_mr", "nome_padrao": "Kidney_L_ai",
         "chave_anatomica": "kidney_left", "no_study": True},
    ],
}
ACHADOS = frozenset(["lung_nodules", "liver_lesions", "liver_lesions_mr"])


class ListaFalsa(object):
    def __enter__(self):
        import radai_sets
        self.mod = radai_sets
        self.havia = hasattr(radai_sets, "estruturas_para_tabela")
        self.antes = getattr(radai_sets, "estruturas_para_tabela", None)
        radai_sets.estruturas_para_tabela = lambda m: [dict(l) for l in LINHAS.get(m, [])]
        return self

    def __exit__(self, *a):
        if self.havia:
            self.mod.estruturas_para_tabela = self.antes
        else:
            try:
                delattr(self.mod, "estruturas_para_tabela")
            except Exception:
                pass


def config_novo(texto=u"ROOT=\nDEVICE=auto\nPORT=8777\nPASTA_FAVORITA=\n"):
    d = novo_temp()
    p = os.path.join(d, "radai_watcher.config")
    io.open(p, "w", encoding="utf-8").write(texto)
    return p


def teste_o_motivo_de_cada_nome():
    secao(u"a tag propria: as regras tecnicas e o motivo na linha")
    casos = [
        (u"", u""), (u"Figado", u""), (u"Liver A", u""), (u"ABCDEFGHIJKLMNOP", u""),
        (u" Figado", C.MOTIVO_ESPACO), (u"Figado ", C.MOTIVO_ESPACO),
        (u"Fígado", C.MOTIVO_ASCII), (u"ABCDEFGHIJKLMNOPQ", C.MOTIVO_LIMITE),
        (u"Liv\\er", C.MOTIVO_CONTRABARRA), (u"PTV_70", C.MOTIVO_RESERVADO),
        (u"ctv_alto", C.MOTIVO_RESERVADO), (u"BODY", C.MOTIVO_RESERVADO),
        (u"External", C.MOTIVO_RESERVADO), (u"Liv\ter", C.MOTIVO_ASCII),
    ]
    errados = [(n, C.motivo_do_nome(n), m) for n, m in casos if C.motivo_do_nome(n) != m]
    checar(u"cada nome recebe o motivo certo (16 caracteres, ASCII, sem espaco nas "
           u"pontas, sem contrabarra, nem alvo nem corpo)", not errados, repr(errados))
    checar(u"  (isca) o limite e 16, e nao 15 nem 17",
           C.motivo_do_nome(u"A" * 16) == u"" and C.motivo_do_nome(u"A" * 17) == C.MOTIVO_LIMITE)


def teste_os_nomes_e_o_modo():
    secao(u"o modo, os nomes e o arquivo ao lado do config")
    cfg = config_novo()
    checar(u"sem arquivo, o modo e o padrao e nao ha nome proprio",
           C.modo_dos_nomes(cfg) == u"padrao" and C.nomes_proprios(cfg) == {})
    with ListaFalsa():
        ok, r = C.gravar_nomes(u"proprios", {u"Liver_ai": u"Figado"},
                               C.estruturas_por_modalidade(), caminho_cfg=cfg)
    alvo = os.path.join(os.path.dirname(cfg), C.NOME_DOS_NOMES)
    checar(u"grava nomes_proprios.json ao lado do radai_watcher.config",
           ok and os.path.isfile(alvo), repr(r))
    checar(u"  e o contrato devolve {nome_padrao: nome_proprio}",
           C.modo_dos_nomes(cfg) == u"proprios"
           and C.nomes_proprios(cfg) == {u"Liver_ai": u"Figado"})
    with ListaFalsa():
        ok, r = C.gravar_nomes(u"padrao", {u"Liver_ai": u"Figado"},
                               C.estruturas_por_modalidade(), caminho_cfg=cfg)
    checar(u"no modo Padrao o contrato devolve vazio, e o nome editado fica guardado",
           ok and C.nomes_proprios(cfg) == {}
           and C.ler_nomes(cfg)["nomes"] == {u"Liver_ai": u"Figado"})
    io.open(alvo, "w", encoding="utf-8").write(json.dumps(
        {"modo": "proprios", "nomes": {"Liver_ai": "Figado", "Spleen_ai": u"Baço",
                                       "Lung_L_ai": "PTV_mama"}}))
    checar(u"nome editado a mao que a tela recusaria nao chega ao contrato",
           C.nomes_proprios(cfg) == {u"Liver_ai": u"Figado"}, repr(C.nomes_proprios(cfg)))


def teste_a_conferencia_da_tabela():
    secao(u"a validacao da tabela: repetido, desconhecido e uniao")
    with ListaFalsa():
        est = C.estruturas_por_modalidade()
    e = C.conferir_nomes({u"Liver_ai": u"Baco", u"Spleen_ai": u"baco"}, est)
    checar(u"dois nomes proprios iguais (maiuscula nao importa): as duas linhas acusam",
           e.get(u"Liver_ai") == C.MOTIVO_REPETIDO and e.get(u"Spleen_ai") == C.MOTIVO_REPETIDO,
           repr(e))
    e = C.conferir_nomes({u"Liver_ai": u"Spleen_ai"}, est)
    checar(u"nome proprio igual ao padrao de outra estrutura: acusa so a linha editada",
           e == {u"Liver_ai": C.MOTIVO_REPETIDO}, repr(e))
    e = C.conferir_nomes({u"Inventada_ai": u"X"}, est)
    checar(u"estrutura que a lista nao tem e recusada",
           e.get(u"Inventada_ai") == C.MOTIVO_DESCONHECIDA, repr(e))
    e = C.conferir_nomes({u"Kidney_L_ai": u"Rim_E"}, est)
    checar(u"a estrutura que so existe na RM vale (a lista e a das duas modalidades)",
           e == {}, repr(e))
    prot = [{"modalidade": "CT", "merges": [{"nome": "Pulmoes", "de": ["Lung_L_ai", "Lung_R_ai"]}]}]
    e = C.conferir_nomes({u"Liver_ai": u"pulmoes"}, est, prot)
    checar(u"nome proprio igual ao de uma uniao de protocolo da mesma modalidade e recusado",
           e.get(u"Liver_ai") == C.MOTIVO_REPETE_UNIAO, repr(e))
    e = C.conferir_nomes({u"Liver_ai": u"X"}, {"CT": [], "MR": []})
    checar(u"sem a lista do motor nada se grava (e o motivo diz por que)",
           e.get(u"") == C.MOTIVO_SEM_LISTA, repr(e))
    checar(u"  (isca) sem nome nenhum, a lista vazia nao reprova",
           C.conferir_nomes({}, {"CT": [], "MR": []}) == {})


def teste_o_protocolo_proprio():
    secao(u"o protocolo proprio, as unioes e o achado")
    ls = LINHAS["CT"]
    p, e = C.conferir_protocolo({"nome": "", "modalidade": "TC", "estruturas": []}, ls,
                                achados=ACHADOS)
    checar(u"sem nome e sem estrutura: os dois motivos, e a modalidade TC vira CT",
           e.get("nome") == C.MOTIVO_SEM_NOME_PROT and e.get("estruturas") == C.MOTIVO_VAZIO
           and p["modalidade"] == "CT", repr(e))
    p, e = C.conferir_protocolo({"nome": "Torax", "modalidade": "PET",
                                 "estruturas": ["Liver_ai"]}, ls, achados=ACHADOS)
    checar(u"modalidade que nao e TC nem RM e recusada", e.get("modalidade") == C.MOTIVO_MODALIDADE)
    p, e = C.conferir_protocolo({"nome": "Torax", "modalidade": "CT",
                                 "estruturas": ["Liver_ai", "Inventada"]}, ls, achados=ACHADOS)
    checar(u"estrutura desconhecida diz qual", (e.get("estruturas") or u"").endswith(u"Inventada"),
           repr(e))
    bruto = {"nome": "Torax", "modalidade": "CT", "estruturas": ["Liver_ai"],
             "merges": [{"nome": "Pulmoes", "de": ["Lung_L_ai"]},
                        {"nome": "Figado", "de": ["Lung_L_ai", "Lung_R_ai"]},
                        {"nome": "PTV_x", "de": ["Lung_L_ai", "Lung_R_ai"]},
                        {"nome": "Pulmoes", "de": ["Lung_L_ai", "Lung_R_ai"]}]}
    p, e = C.conferir_protocolo(bruto, ls, nomes={u"Liver_ai": u"Figado"}, achados=ACHADOS)
    checar(u"uniao com uma estrutura so e recusada", e.get("uniao:0") == C.MOTIVO_UNIAO_CURTA,
           repr(e))
    checar(u"uniao com o nome proprio de uma estrutura do protocolo e recusada",
           e.get("uniao:1") == C.MOTIVO_UNIAO_REPETIDA, repr(e))
    checar(u"uniao com nome de alvo e recusada", e.get("uniao:2") == C.MOTIVO_RESERVADO, repr(e))
    checar(u"uniao valida passa", "uniao:3" not in e, repr(e))
    p, e = C.conferir_protocolo({"nome": "Nodulos", "modalidade": "CT",
                                 "estruturas": ["LungNodules_nod"], "tem_achado": False},
                                ls, achados=ACHADOS)
    checar(u"o achado e medido pela task, e nao confiado ao que veio no pedido",
           not e and p["tem_achado"] is True, repr(p))
    p, e = C.conferir_protocolo({"nome": "Nodulos", "modalidade": "CT",
                                 "merges": [{"nome": "Mix", "de": ["Liver_ai", "LungNodules_nod"]}]},
                                ls, achados=ACHADOS)
    checar(u"  e vale tambem para o achado que entra por uma uniao",
           not e and p["tem_achado"] is True, repr((p, e)))
    p, e = C.conferir_protocolo({"nome": "Abdome", "modalidade": "CT",
                                 "estruturas": ["Liver_ai"]}, ls, achados=ACHADOS)
    checar(u"  (isca) protocolo sem achado nao e marcado", not e and p["tem_achado"] is False)
    marcadas = ls + [{"task": "task_nova", "nome_padrao": "Achado_novo",
                      "chave_anatomica": "x", "no_study": False, "achado": True}]
    p, e = C.conferir_protocolo({"nome": "Novo", "modalidade": "CT",
                                 "estruturas": ["Achado_novo"]}, marcadas, achados=ACHADOS)
    checar(u"  e a linha que a lista do motor marca como achado tambem conta",
           not e and p["tem_achado"] is True, repr((p, e)))
    fora = ls + [{"task": "total", "nome_padrao": "So_leitura", "chave_anatomica": "y",
                  "no_study": False, "protocolo": False}]
    p, e = C.conferir_protocolo({"nome": "Novo", "modalidade": "CT",
                                 "estruturas": ["So_leitura"]}, fora, achados=ACHADOS)
    checar(u"  e a linha que o motor diz que nao entra em protocolo e recusada",
           (e.get("estruturas") or u"").endswith(u"So_leitura"), repr(e))
    outros = [{"id": "p1", "nome": "abdome", "modalidade": "CT"},
              {"id": "p2", "nome": "Abdome", "modalidade": "MR"}]
    p, e = C.conferir_protocolo({"nome": "Abdome", "modalidade": "CT",
                                 "estruturas": ["Liver_ai"]}, ls, outros=outros, achados=ACHADOS)
    checar(u"nome repetido na mesma modalidade e recusado (na outra, vale)",
           e.get("nome") == C.MOTIVO_NOME_PROT_REPETIDO, repr(e))
    cfg = config_novo()
    ok, r = C.gravar_protocolo({"nome": "Abdome", "modalidade": "CT",
                                "estruturas": ["Liver_ai"]}, ls, caminho_cfg=cfg, achados=ACHADOS)
    pid = (r.get("protocolo") or {}).get("id")
    ok2, r2 = C.gravar_protocolo({"id": pid, "nome": "Abdome superior", "modalidade": "CT",
                                  "estruturas": ["Liver_ai", "Spleen_ai"]}, ls,
                                 caminho_cfg=cfg, achados=ACHADOS)
    lista = C.protocolos_proprios("CT", cfg)
    checar(u"gravar de novo com o mesmo id substitui, sem duplicar",
           ok and ok2 and len(lista) == 1 and lista[0]["nome"] == u"Abdome superior"
           and os.path.isfile(os.path.join(os.path.dirname(cfg), C.NOME_DOS_PROTOCOLOS)),
           repr(lista))
    checar(u"protocolos_proprios filtra pela modalidade (RM ou MR)",
           C.protocolos_proprios("RM", cfg) == [] and C.protocolos_proprios(None, cfg) == lista)
    ok3, _ = C.apagar_protocolo(pid, cfg)
    checar(u"apagar tira o protocolo", ok3 and C.protocolos_proprios(None, cfg) == [])


def teste_exportar_e_importar():
    secao(u"exportar e importar: o que viaja e o que nao viaja")
    origem = config_novo(u"ROOT=\nDEVICE=gpu\nPORT=9999\nGUIA_VISTO=1\nSCAN_EVERY_MIN=5\n"
                         u"OUT_DIR=Z:\\inexistente\\saida\nTPS_DESTINO=monaco\n")
    chaves = ["ROOT", "DEVICE", "PORT", "GUIA_VISTO", "SCAN_EVERY_MIN", "OUT_DIR", "TPS_DESTINO",
              "LOG_DIR"]
    with ListaFalsa():
        C.gravar_nomes(u"proprios", {u"Liver_ai": u"Figado"}, C.estruturas_por_modalidade(),
                       caminho_cfg=origem)
        C.gravar_protocolo({"nome": "Abdome", "modalidade": "CT", "estruturas": ["Liver_ai"]},
                           LINHAS["CT"], caminho_cfg=origem, achados=ACHADOS)
    reg = os.environ["RADAI_REGISTRO_DIR"]
    io.open(os.path.join(reg, "_pseudonimo.chave"), "w", encoding="utf-8").write(u"x" * 64)
    ex = C.exportar(origem, chaves, versao=u"8.7")
    conf = ex["secoes"]["configuracao"]
    checar(u"a exportacao nao leva placa, dispositivo, porta nem a marca do guia",
           not set(conf) & {"DEVICE", "PORT", "GUIA_VISTO"}, repr(sorted(conf)))
    checar(u"  e leva a configuracao da estacao, os nomes e os protocolos",
           conf.get("SCAN_EVERY_MIN") == u"5" and conf.get("TPS_DESTINO") == u"monaco"
           and ex["secoes"]["nomes"]["nomes"] == {u"Liver_ai": u"Figado"}
           and len(ex["secoes"]["protocolos"]) == 1, repr(ex["secoes"]))
    texto = json.dumps(ex, ensure_ascii=False)
    checar(u"  e nada da chave do pseudonimo, do acervo ou da fila",
           u"x" * 32 not in texto and u"_pseudonimo" not in texto and u"fila" not in texto)
    checar(u"  (isca) a regra de fora alcanca o que existe no arquivo",
           "DEVICE" in C.ler_arquivo(origem)[1])

    destino = config_novo(u"ROOT=\nDEVICE=cpu\nPORT=8777\nSCAN_EVERY_MIN=10\nLOG_DIR=\n")
    with ListaFalsa():
        pv = C.previa_da_importacao(ex, destino, chaves, C.estruturas_por_modalidade(),
                                    achados=ACHADOS)
    itens = dict((i["chave"], i) for i in pv["configuracao"]["itens"])
    checar(u"a previa avisa o caminho que nao existe nesta maquina",
           itens.get("OUT_DIR", {}).get("aviso") == C.MOTIVO_CAMINHO, repr(itens.get("OUT_DIR")))
    checar(u"  e mostra o que muda", itens.get("SCAN_EVERY_MIN", {}).get("muda") is True)
    with ListaFalsa():
        r = C.importar(ex, ["configuracao"], destino, chaves, C.estruturas_por_modalidade(),
                       achados=ACHADOS)
    _t, v = C.ler_arquivo(destino)
    checar(u"importar so a configuracao: grava o que muda e nao grava o caminho inexistente",
           r.get("ok") and v.get("SCAN_EVERY_MIN") == u"5" and "OUT_DIR" not in v
           and v.get("DEVICE") == u"cpu" and v.get("PORT") == u"8777", repr(v))
    checar(u"  e as secoes nao marcadas ficam como estavam",
           C.ler_nomes(destino)["nomes"] == {} and C.protocolos_proprios(None, destino) == [])
    with ListaFalsa():
        r = C.importar(ex, ["nomes", "protocolos"], destino, chaves,
                       C.estruturas_por_modalidade(), achados=ACHADOS)
    checar(u"importar os nomes e os protocolos grava os dois",
           r.get("ok") and C.nomes_proprios(destino) == {u"Liver_ai": u"Figado"}
           and len(C.protocolos_proprios("CT", destino)) == 1, repr(r))
    ruim = json.loads(json.dumps(ex))
    ruim["secoes"]["configuracao"]["TPS_DESTINO"] = u"varian"
    ruim["secoes"]["configuracao"]["SCAN_EVERY_MIN"] = u"5\nROOT=C:\\"
    ruim["secoes"]["configuracao"]["INCLUIR_NV"] = u"1"
    with ListaFalsa():
        pv = C.previa_da_importacao(ruim, destino, chaves, C.estruturas_por_modalidade())
    itens = dict((i["chave"], i) for i in pv["configuracao"]["itens"])
    checar(u"TPS que esta versao nao aceita e valor com quebra de linha nao se gravam",
           itens["TPS_DESTINO"]["aviso"] == C.MOTIVO_TPS
           and itens["SCAN_EVERY_MIN"]["aviso"] == C.MOTIVO_QUEBRA, repr(itens))
    checar(u"  e a chave que esta versao nao conhece fica de fora",
           u"INCLUIR_NV" in pv["configuracao"]["ignoradas"])
    checar(u"arquivo que nao e exportacao e recusado",
           C.previa_da_importacao({"formato": "outro"}, destino, chaves, {})["erro"]
           == C.MOTIVO_NAO_E_EXPORTACAO)
    novo = dict(ex, versao=C.VERSAO_DA_EXPORTACAO + 1)
    checar(u"  e a exportacao de uma versao mais nova tambem",
           C.previa_da_importacao(novo, destino, chaves, {})["erro"] == C.MOTIVO_EXPORTACAO_NOVA)
    root = config_novo(u"ROOT=\n")
    so_root = json.loads(json.dumps(ex))
    so_root["secoes"]["configuracao"] = {"ROOT": novo_temp()}
    pv = C.previa_da_importacao(so_root, root, ["ROOT"], {},
                                validar=lambda c: {"existe": True, "leitura": True,
                                                   "escrita": False})
    checar(u"o ROOT sem escrita (o vigia grava na pasta da serie) nao se grava",
           pv["configuracao"]["itens"][0]["aviso"] == C.MOTIVO_ROOT, repr(pv))


def teste_o_dicionario_anatomico():
    secao(u"o nome anatomico nos doze idiomas (app/data/nomes_anatomicos.json)")
    import radai_languages as L
    caminho = os.path.join(os.path.dirname(C.__file__), *C.ARQUIVO_DOS_NOMES_ANATOMICOS)
    d = json.load(io.open(caminho, encoding="utf-8"))
    codigos = [c for c, _b, _n, _r in L.IDIOMAS]
    checar(u"os doze idiomas do seletor, com o portugues de base",
           sorted(d.get("idiomas") or []) == sorted(codigos) and C.IDIOMA_BASE in codigos)
    nomes = d.get("nomes") or {}
    buracos = [(k, c) for k, v in nomes.items() for c in codigos
               if not (v.get(c) or u"").strip() or v.get(c) != v.get(c).strip()]
    checar(u"nenhuma estrutura sem nome em algum idioma (%d estruturas)" % len(nomes),
           len(nomes) >= 250 and not buracos, repr(buracos[:6]))
    try:
        import engine
        import radai_sets
        import radai_hnlnl
        catalogo = set(engine.TS_MAP) | set(engine.COMPOSTOS) | set(radai_sets.PERMITIDOS_NO_OAR)
        catalogo |= set("Lvl_" + n for n in radai_hnlnl.MAPA_DOS_PESOS.values())
    except Exception as e:
        catalogo = None
        checar(u"o catalogo do motor carrega", False, u"%s: %s" % (type(e).__name__, e))
    if catalogo is not None:
        falta = sorted(k for k in catalogo if k not in nomes)
        checar(u"toda estrutura do catalogo do motor tem nome anatomico", not falta,
               repr(falta[:8]))
        checar(u"  (isca) uma chave inventada e acusada",
               u"orgao_inventado" not in nomes)
    import radai_sets as RS
    sem = []
    for mod in C.MODALIDADES:
        for l in RS.estruturas_para_tabela(mod) or []:
            if l.get("chave_anatomica") and l["chave_anatomica"] not in nomes:
                sem.append(l["chave_anatomica"])
    checar(u"toda chave_anatomica de radai_sets.estruturas_para_tabela tem nome",
           not sem, repr(sorted(set(sem))[:8]))
    checar(u"o nome sai no idioma pedido, e o portugues responde por idioma desconhecido",
           C.nome_anatomico(u"liver", u"en") == u"Liver"
           and C.nome_anatomico(u"liver", u"xx") == u"Fígado"
           and C.nome_anatomico(u"kidney_left", u"de") == u"Niere links")


def teste_a_chave_da_favorita_e_o_anel():
    secao(u"a pasta favorita e o anel: a chave da favorita e o TPS validado")
    cfg = config_novo(u"PASTA_FAVORITA=Z:\\algum\\lugar\n")
    antes = os.environ.get("RADAI_CONFIG")
    os.environ["RADAI_CONFIG"] = cfg
    try:
        checar(u"radai_config.pasta_favorita() le a chave PASTA_FAVORITA do config",
               C.pasta_favorita() == u"Z:\\algum\\lugar")
    finally:
        if antes is None:
            os.environ.pop("RADAI_CONFIG", None)
        else:
            os.environ["RADAI_CONFIG"] = antes
    ok, erro = C.gravar_tps(cfg, u"varian")
    checar(u"o anel so aceita eclipse ou monaco", not ok and u"eclipse" in erro)
    ok, _ = C.gravar_tps(cfg, u"Monaco")
    checar(u"  e grava o valor canonico", ok and C.ler_arquivo(cfg)[1].get("TPS_DESTINO") == u"monaco")
    checar(u"a validacao da favorita pede so que exista e se leia (nao escreve nela)",
           C.validar_favorita(novo_temp()).get("leitura") is True
           and C.validar_favorita(u"Z:\\nao\\existe").get("codigo") == u"nao_existe")


def teste_as_listas_de_preservados():
    secao(u"os dois arquivos sobrevivem a reinstalacao (as tres listas)")
    raiz = os.path.dirname(AQUI)
    arqs = ((u"installer/INSTALL.ps1", r"\$PRESERVAR\s*=\s*@\((.*?)\)"),
            (u"installer/UNINSTALL.ps1", r"\$PRESERVAVEL\s*=\s*@\((.*?)\)"),
            (u"packager/prepare.ps1", r"\$preserv\s*=\s*@\((.*?)\)"))
    for rel, padrao in arqs:
        p = os.path.join(raiz, rel.replace(u"/", os.sep))
        if not os.path.isfile(p):
            print(u"    PULADO %s (arvore sem o instalador)" % rel)
            continue
        m = re.search(padrao, io.open(p, encoding="utf-8-sig").read(), re.S)
        lista = set(re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))) if m else set()
        checar(u"%s preserva nomes_proprios.json e protocolos_proprios.json" % rel,
               {C.NOME_DOS_NOMES, C.NOME_DOS_PROTOCOLOS} <= lista, repr(sorted(lista)))


def _app(cfg, log=None):
    from fastapi import FastAPI
    import radai_panel
    app = FastAPI()
    radai_panel.montar(app, ler_vigia=lambda: {}, config={
        "caminho": cfg, "chaves": ["ROOT", "DEVICE", "PORT", "PASTA_FAVORITA",
                                   "TPS_DESTINO", "SCAN_EVERY_MIN", "OUT_DIR"],
        "padroes": {}, "modelo": u"", "registrar": (log.append if log is not None else None)})
    return app


def teste_as_rotas():
    secao(u"as rotas da tela: anel, estruturas, nomes, protocolos, exportar e importar")
    try:
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False, u"PULADO -- %s" % e)
        return
    cfg = config_novo()
    log = []
    with ListaFalsa():
        c = TestClient(_app(cfg, log), raise_server_exceptions=False)
        e = c.get(u"/api/config/estacao").json()
        checar(u"/api/config/estacao: sem TPS no arquivo vale o padrao Eclipse / Monaco",
               e.get("tps") == u"" and e.get("tps_em_vigor") == u"eclipse", repr(e))
        r = c.post(u"/api/config/tps", json={"tps": "xio"})
        checar(u"/api/config/tps recusa o que nao e eclipse nem monaco (400)", r.status_code == 400)
        r = c.post(u"/api/config/tps", json={"tps": "monaco"})
        checar(u"  e grava monaco, com a linha no log (valor e nome da tela)",
               r.status_code == 200 and C.ler_arquivo(cfg)[1].get("TPS_DESTINO") == u"monaco"
               and any(u"TPS_DESTINO=monaco (Xio / Focal)" in l for l in log), repr(log))
        r = c.get(u"/api/config/estruturas?modalidade=TC&idioma=en").json()
        ls = dict((l["nome_padrao"], l) for l in r.get("linhas") or [])
        checar(u"/api/config/estruturas: a lista do motor com o nome anatomico no idioma",
               ls.get("Liver_ai", {}).get("anatomico") == u"Liver" and r.get("modalidade") == "CT",
               repr(r)[:200])
        checar(u"  e marca o achado pela task", ls.get("LungNodules_nod", {}).get("achado") is True
               and ls.get("Liver_ai", {}).get("achado") is False)
        r = c.post(u"/api/config/nomes", json={"modo": "proprios",
                                               "nomes": {"Liver_ai": "Baco", "Spleen_ai": "Baco"}})
        checar(u"/api/config/nomes recusa o repetido com o motivo na linha, e nao grava",
               r.json().get("ok") is False and r.json()["erros"].get("Spleen_ai")
               == C.MOTIVO_REPETIDO and C.ler_nomes(cfg)["nomes"] == {}, r.text)
        r = c.post(u"/api/config/nomes", json={"modo": "proprios", "nomes": {"Liver_ai": "Figado"}})
        checar(u"  e grava o valido", r.json().get("ok") is True
               and C.nomes_proprios(cfg) == {u"Liver_ai": u"Figado"})
        r = c.post(u"/api/config/protocolos", json={"protocolo": {
            "nome": "Nodulos", "modalidade": "CT", "estruturas": ["LungNodules_nod"]}})
        p = r.json().get("protocolo") or {}
        checar(u"/api/config/protocolos grava, e o achado vem medido pelo servidor",
               r.json().get("ok") is True and p.get("tem_achado") is True
               and any(u"procura ACHADO" in l for l in log), r.text)
        r = c.post(u"/api/config/protocolos/apagar", json={"id": p.get("id")})
        checar(u"  e apaga", r.json().get("ok") is True and C.protocolos_proprios(None, cfg) == [])
        ex = c.post(u"/api/config/exportar").json()
        checar(u"/api/config/exportar devolve o envelope, sem DEVICE nem PORT",
               ex.get("formato") == C.FORMATO_DA_EXPORTACAO
               and not set(ex["secoes"]["configuracao"]) & {"DEVICE", "PORT"}, repr(ex)[:200])
        ex["secoes"]["configuracao"]["SCAN_EVERY_MIN"] = u"7"
        pv = c.post(u"/api/config/importar/previa", json={"dados": ex}).json()
        checar(u"/api/config/importar/previa lista o que muda",
               any(i["chave"] == "SCAN_EVERY_MIN" and i["muda"] for i in
                   pv["configuracao"]["itens"]), repr(pv)[:200])
        r = c.post(u"/api/config/importar", json={"dados": ex, "secoes": ["configuracao"]}).json()
        checar(u"/api/config/importar grava a secao marcada",
               r.get("ok") and C.ler_arquivo(cfg)[1].get("SCAN_EVERY_MIN") == u"7", repr(r))
        r = c.post(u"/api/config/nomes", content=b"x" * (C_TETO + 1),
                   headers={"Content-Type": "application/json"})
        checar(u"pedido grande demais e recusado (413)", r.status_code == 413)


C_TETO = 2 * 1024 * 1024


def teste_a_tela():
    secao(u"a tela: Geral, os cartoes 5 e 7 e a secao nova")
    import radai_panel
    import radai_config_estacao as CE
    p = radai_panel.PAGINA_CONFIG
    checar(u"nenhuma marca de costura sobrou na pagina", not [m for m in CE.MARCAS if m in p])
    i5 = p.find(u'data-alvo="ps_estruturas"')
    i7 = p.find(u'data-alvo="ps_limpar"')
    checar(u"o cartao 5 e Estruturas e Protocolos e o 7 e Diagnosticos e Registros",
           0 < i5 < i7 and u"Estruturas e Protocolos" in p[i5:p.find(u"</a>", i5)]
           and u"Diagnósticos e Registros" in p[i7:p.find(u"</a>", i7)])
    g = p[p.find(u'id="ps_geral"'):p.find(u'id="ps_processamento"')]
    checar(u"a Geral tem o anel (dois botoes), a favorita, o exportar e o importar",
           g.count(u'class="an-op"') == 2 and u"Configurar pasta favorita" in g
           and u'id="exi_exportar"' in g and u'id="exi_importar"' in g, g[:200])
    checar(u"  e o «Ver o guia de novo» so aparece quando o guia existe na tela",
           u'id="gu_bloco" hidden' in g and u"typeof window.radaiGuiaAbrir !== 'function'" in CE.JS)
    checar(u"o TPS continua fora da caixa de texto da tela", u"TPS_DESTINO" in radai_panel.FORA_DA_TELA)
    checar(u"a tabela tem as quatro colunas e o editor de protocolo",
           all(x in p for x in (u">Task<", u">Nome anatômico<", u">Nome no STUDY<",
                                u">Nome próprio<", u'id="prot_editor"')))
    checar(u"identificador da tabela nao passa pelo tradutor (data-radai-t)",
           CE.JS.count(u'data-radai-t="1" translate="no"') >= 4)


def _servidor(app, porta):
    import threading
    import uvicorn
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(200):
        if getattr(srv, "started", False):
            break
        time.sleep(0.05)
    return srv, th


def _porta(preferida):
    import socket
    for p in range(preferida, preferida + 20):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError(u"sem porta livre")


def _chromium():
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if not os.path.isdir(base):
        return None
    for nome in sorted(os.listdir(base), reverse=True):
        if nome.startswith("chromium-"):
            for sub in ("chrome-win64", "chrome-win"):
                exe = os.path.join(base, nome, sub, "chrome.exe")
                if os.path.isfile(exe):
                    return exe
    return None


_JS_TABELA = u"""async () => {
  const espera = (ms) => new Promise(function(r){ setTimeout(r, ms) });
  window.cfgMostrar('ps_estruturas');
  for (let k = 0; k < 40 && !document.querySelector('#est_corpo input[data-n]'); k++) await espera(100);
  const linhas = document.querySelectorAll('#est_corpo tr').length;
  const desligado = document.querySelector('#est_corpo input[data-n="Liver_ai"]').disabled;
  const anat = document.querySelector('#est_corpo tr td:nth-child(2) span').textContent;
  const seg = document.getElementById('est_modo').previousElementSibling;
  seg.querySelector('button[data-v="proprios"]').click();
  await espera(600);
  const ligado = !document.querySelector('#est_corpo input[data-n="Liver_ai"]').disabled;
  const a = document.querySelector('#est_corpo input[data-n="Liver_ai"]');
  const b = document.querySelector('#est_corpo input[data-n="Spleen_ai"]');
  a.value = 'Baco'; a.dispatchEvent(new Event('input', {bubbles: true}));
  b.value = 'baco'; b.dispatchEvent(new Event('input', {bubbles: true}));
  await espera(500);
  const erro = b.nextElementSibling.textContent.trim();
  const invalido = b.getAttribute('aria-invalid');
  b.value = 'Baco2'; b.dispatchEvent(new Event('input', {bubbles: true}));
  await espera(400);
  document.getElementById('est_salvar').click();
  await espera(900);
  const msg = document.getElementById('est_msg').textContent.trim();
  document.getElementById('prot_novo').click();
  for (let k = 0; k < 30 && !document.querySelector('#prot_corpo input[data-sel]'); k++) await espera(100);
  document.getElementById('prot_nome').value = 'Torax';
  const marca = (n) => { const x = document.querySelector('#prot_corpo input[data-sel="' + n + '"]');
                         x.checked = true; x.dispatchEvent(new Event('change', {bubbles: true})); };
  marca('Liver_ai'); marca('LungNodules_nod');
  await espera(200);
  const achado = !document.getElementById('prot_achado').hidden;
  document.getElementById('prot_unir').click();
  await espera(300);
  const u = (n) => { const x = document.querySelector('#prot_corpo input[data-unir="' + n + '"]');
                     x.checked = true; x.dispatchEvent(new Event('change', {bubbles: true})); };
  u('Lung_L_ai'); u('Lung_R_ai');
  document.getElementById('prot_uniao_nome').value = 'Pulmoes';
  document.getElementById('prot_uniao_criar').click();
  await espera(300);
  const unioes = document.querySelectorAll('#prot_unioes .prot-uniao').length;
  document.getElementById('prot_salvar').click();
  await espera(900);
  const lista = document.querySelectorAll('#prot_lista .prot-item').length;
  const fav = document.getElementById('fav_procurar');
  const favAoLado = !!fav && fav.previousElementSibling === document.getElementById('f_PASTA_FAVORITA');
  return {fav: favAoLado, linhas: linhas, desligado: desligado, ligado: ligado, anat: anat, erro: erro,
          invalido: invalido, msg: msg, achado: achado, unioes: unioes, lista: lista,
          editor_fechou: document.getElementById('prot_editor').hidden,
          erros_js: window.__erros || []};
}"""


def medir_a_tela(js=None):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    exe = _chromium()
    if not exe:
        return None
    cfg = config_novo()
    m = {}
    srv = th = None
    with ListaFalsa():
        try:
            porta = _porta(8851)
            srv, th = _servidor(_app(cfg), porta)
            with sync_playwright() as pw:
                nav = pw.chromium.launch(executable_path=exe, headless=True)
                try:
                    pg = nav.new_page(viewport={"width": 1280, "height": 800},
                                      color_scheme="dark", accept_downloads=True)
                    erros = []
                    pg.on("pageerror", lambda e: erros.append(str(e)[:160]))
                    pg.goto(u"http://127.0.0.1:%d/config" % porta, wait_until="networkidle")
                    m = pg.evaluate(js or _JS_TABELA) or {}
                    pg.evaluate(u"window.cfgMostrar('ps_geral')")
                    pg.wait_for_timeout(300)
                    pg.click(u'.an-op[data-tps="monaco"]')
                    pg.wait_for_timeout(600)
                    m["anel_msg"] = pg.locator(u"#an_msg").inner_text().strip()
                    m["anel_marcado"] = pg.get_attribute(u'.an-op[data-tps="monaco"]',
                                                         u"aria-checked")
                    with pg.expect_download() as baixado:
                        pg.click(u"#exi_exportar")
                    ex = json.load(io.open(baixado.value.path(), encoding="utf-8"))
                    m["exportou"] = ex.get("formato")
                    m["nome_baixado"] = baixado.value.suggested_filename
                    ex["secoes"]["configuracao"]["SCAN_EVERY_MIN"] = u"9"
                    ex["secoes"]["configuracao"]["OUT_DIR"] = u"Z:\\nao\\existe\\aqui"
                    arq = os.path.join(novo_temp(), u"importar.json")
                    io.open(arq, "w", encoding="utf-8").write(json.dumps(ex))
                    pg.set_input_files(u"#exi_arquivo", arq)
                    pg.wait_for_selector(u"#exi_aplicar", timeout=6000)
                    m["previa_aviso"] = pg.locator(u"#exi_previa .exi-aviso").count()
                    pg.click(u"#exi_aplicar")
                    pg.wait_for_timeout(900)
                    m["importou_msg"] = pg.locator(u"#exi_msg").inner_text().strip()
                    m["erros_pagina"] = erros
                finally:
                    nav.close()
        except Exception as e:
            m["excecao"] = u"%s: %s" % (type(e).__name__, e)
        finally:
            if srv is not None:
                srv.should_exit = True
                th.join(10)
    m["nomes"] = C.ler_nomes(cfg)
    m["protocolos"] = C.ler_protocolos(cfg)
    m["config"] = C.ler_arquivo(cfg)[1]
    return m


def teste_a_tela_no_navegador():
    secao(u"a tela no navegador: a tabela de tags e o editor de protocolo")
    m = medir_a_tela()
    if m is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    checar(u"a pagina abre sem erro de JS", not m.get("erros_pagina") and not m.get("excecao"),
           repr([m.get("erros_pagina"), m.get("excecao")]))
    checar(u"em Pastas e porta, a PASTA_FAVORITA ganha o Procurar (o explorador da casca)",
           m.get("fav") is True, repr(m))
    checar(u"a tabela mostra as linhas do STUDY (as so do FULL ficam escondidas)",
           m.get("linhas") == 4, repr(m))
    checar(u"  com o nome anatomico na lingua da tela", m.get("anat") == u"Fígado", repr(m))
    checar(u"em Padrao a coluna propria fica apagada; em Tags proprias, liga",
           m.get("desligado") is True and m.get("ligado") is True, repr(m))
    checar(u"o nome repetido acusa na linha, com o motivo",
           m.get("erro") == u"repete o nome de outra estrutura" and m.get("invalido") == u"true",
           repr(m))
    checar(u"salvar grava os nomes proprios no modo proprio",
           (m.get("nomes") or {}).get("modo") == u"proprios"
           and (m.get("nomes") or {}).get("nomes") == {u"Liver_ai": u"Baco", u"Spleen_ai": u"Baco2"}
           and m.get("msg") == u"Gravado: vale para a próxima série.", repr(m))
    checar(u"o editor avisa que o protocolo procura achado ao marcar o achado",
           m.get("achado") is True, repr(m))
    checar(u"a uniao entra no editor e o protocolo se grava com ela",
           m.get("unioes") == 1 and m.get("lista") == 1 and m.get("editor_fechou") is True
           and (m.get("protocolos") or [{}])[0].get("merges") == [
               {"nome": u"Pulmoes", "de": [u"Lung_L_ai", u"Lung_R_ai"]}]
           and (m.get("protocolos") or [{}])[0].get("tem_achado") is True, repr(m))
    checar(u"o anel grava no clique e diz quando vale",
           m.get("anel_marcado") == u"true"
           and m.get("anel_msg") == u"Gravado: vale para o próximo RTSTRUCT."
           and (m.get("config") or {}).get("TPS_DESTINO") == u"monaco", repr(m))
    checar(u"exportar baixa o .json da exportacao",
           m.get("exportou") == C.FORMATO_DA_EXPORTACAO
           and (m.get("nome_baixado") or u"").startswith(u"radai_configuracao_")
           and (m.get("nome_baixado") or u"").endswith(u".json"), repr(m))
    checar(u"importar mostra a previa com o caminho inexistente avisado, e grava o resto",
           m.get("previa_aviso") == 1 and (m.get("config") or {}).get("SCAN_EVERY_MIN") == u"9"
           and "OUT_DIR" not in (m.get("config") or {})
           and m.get("importou_msg", u"").startswith(u"Importado."), repr(m))


def main():
    print(u"test_estacao | configuracoes da estacao: anel, favorita, nomes, protocolos, exportar")
    testes = [teste_o_motivo_de_cada_nome, teste_os_nomes_e_o_modo,
              teste_a_conferencia_da_tabela, teste_o_protocolo_proprio,
              teste_exportar_e_importar, teste_o_dicionario_anatomico,
              teste_a_chave_da_favorita_e_o_anel, teste_as_listas_de_preservados,
              teste_as_rotas, teste_a_tela, teste_a_tela_no_navegador]
    for t in testes:
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao inesperada)" % t.__name__, False, u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    for d in _TEMPS:
        shutil.rmtree(d, ignore_errors=True)
    falhas = [(n, d) for n, ok, d in _RESULTADOS if not ok]
    print(u"\n" + u"=" * 64)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n, d in falhas:
            print(u"  - %s%s" % (n, (u"  [%s]" % d) if d else u""))
    else:
        print(u"OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print(u"=" * 64)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
