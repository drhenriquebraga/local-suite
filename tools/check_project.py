# -*- coding: utf-8 -*-
import ast
import io
import os
import re
import warnings
import sys
import _componentes

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

NL = chr(10)

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

OF = _componentes.oficina("check_project", __file__)
FORA = ("node_modules",) + (tuple(OF.PASTAS_ALHEIAS) if OF else ())
APP = "app" if (os.path.isfile(os.path.join(RAIZ, "app", _componentes.MARCA_DO_APP_SOLTO))
                or os.path.exists(os.path.join(RAIZ, "app", "radai_watcher.py"))
                or os.path.exists(_componentes.fonte("app/radai_watcher.py", RAIZ))) else "."


def no_app(nome):
    return "%s/%s" % (APP, nome) if APP != "." else nome


_RESULTADOS = []


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    print("  %s  %s%s" % ("OK   " if ok else "FALHA", nome,
                          ("  [%s]" % detalhe) if detalhe else ""))
    return bool(ok)


def _importar_do_app(nome):
    import importlib
    caminho = os.path.join(RAIZ, "app")
    if caminho not in sys.path:
        sys.path.insert(0, caminho)
    try:
        mod = importlib.import_module(nome)
        return importlib.reload(mod)
    except Exception:
        return None


def ler(rel):
    with io.open(_componentes.fonte(rel), encoding="utf-8", errors="replace") as f:
        return f.read()


def arvore(rel):
    return ast.parse(ler(rel), filename=rel)


def so_codigo(txt):
    import tokenize
    try:
        saida, ultimo = [], (1, 0)
        for tok in tokenize.generate_tokens(io.StringIO(txt).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            if tok.start[0] != ultimo[0]:
                saida.append("\n" * (tok.start[0] - ultimo[0]))
                saida.append(" " * tok.start[1])
            elif tok.start[1] > ultimo[1]:
                saida.append(" " * (tok.start[1] - ultimo[1]))
            saida.append(tok.string)
            ultimo = tok.end
        return "".join(saida)
    except Exception:
        return txt


def checar_engine_no_escopo():
    print("\n[35] Funcao de modulo que usa `engine.` liga o nome")
    import ast

    alvo = _componentes.fonte(os.path.join(APP, "radai_watcher.py"))
    try:
        arv = ast.parse(io.open(alvo, encoding="utf-8", errors="replace").read())
    except Exception as e:
        checar("radai_watcher.py parseia", False, str(e)[:120])
        return

    def _liga(f):
        if any(a.arg == "engine" for a in f.args.args):
            return True
        for n in ast.walk(f):
            if isinstance(n, ast.Import):
                if any(a.name == "engine" and a.asname is None for a in n.names):
                    return True
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == "engine":
                        return True
        return False

    def _usa(f):
        for n in ast.walk(f):
            if (isinstance(n, ast.Attribute)
                    and isinstance(n.value, ast.Name)
                    and n.value.id == "engine"):
                return n.lineno
        return 0

    soltas, conferidas = [], 0
    for f in arv.body:
        if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        ln = _usa(f)
        if not ln:
            continue
        conferidas += 1
        if not _liga(f):
            soltas.append("%s (linha %d)" % (f.name, ln))

    checar("ha funcao de modulo usando `engine.` (a checagem nao e inerte)",
           conferidas > 0, "%d funcao(oes)" % conferidas)
    checar("nenhuma delas usa `engine.` sem ligar o nome",
           not soltas, " | ".join(soltas[:6]))


def checar_sintaxe():
    print("\n[1] Sintaxe")
    alvos = []
    for pasta in (APP, "tools"):
        d = os.path.join(RAIZ, pasta)
        if not os.path.isdir(d):
            continue
        nomes = (_componentes.nomes(pasta, RAIZ) if pasta in ("app", "tools")
                 else sorted(os.listdir(d)))
        for f in nomes:
            if not f.endswith(".py"):
                continue
            rel = f if pasta == "." else os.path.join(pasta, f)
            if rel not in alvos:
                alvos.append(rel)
    for rel in alvos:
        try:
            compile(ler(rel), rel, "exec")
            checar("compila: %s" % rel, True)
        except SyntaxError as e:
            checar("compila: %s" % rel, False, "linha %s: %s" % (e.lineno, e.msg))


def _nomes_do_alvo(alvo, achados):
    if isinstance(alvo, ast.Name):
        achados.add(alvo.id)
    elif isinstance(alvo, (ast.Tuple, ast.List)):
        for e in alvo.elts:
            _nomes_do_alvo(e, achados)
    elif isinstance(alvo, ast.Starred):
        _nomes_do_alvo(alvo.value, achados)


def nomes_de_modulo(arv):
    achados = set()
    pilha = list(arv.body)
    blocos = (ast.Try,) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())
    while pilha:
        no = pilha.pop(0)
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            achados.add(no.name)
        elif isinstance(no, ast.Assign):
            for alvo in no.targets:
                _nomes_do_alvo(alvo, achados)
        elif isinstance(no, (ast.AnnAssign, ast.AugAssign)):
            _nomes_do_alvo(no.target, achados)
        elif isinstance(no, ast.Import):
            for a in no.names:
                achados.add(a.asname or a.name.split(".")[0])
        elif isinstance(no, ast.ImportFrom):
            for a in no.names:
                if a.name != "*":
                    achados.add(a.asname or a.name)
        elif isinstance(no, blocos):
            pilha.extend(no.body)
            for h in no.handlers:
                pilha.extend(h.body)
            pilha.extend(no.orelse)
            pilha.extend(no.finalbody)
        elif isinstance(no, ast.If):
            pilha.extend(no.body)
            pilha.extend(no.orelse)
        elif isinstance(no, (ast.With, ast.AsyncWith)):
            pilha.extend(no.body)
    return achados


def atributos_de(arv, modulo):
    usos = {}
    for no in ast.walk(arv):
        if (isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name)
                and no.value.id == modulo):
            usos.setdefault(no.attr, no.lineno)
    return usos


def usos_do_modulo(arv, modulo):
    nomes = set()
    usos = {}
    for no in ast.walk(arv):
        if isinstance(no, ast.Import):
            for a in no.names:
                if a.name == modulo:
                    nomes.add(a.asname or a.name)
        elif (isinstance(no, ast.ImportFrom) and no.module == modulo
              and not no.level):
            for a in no.names:
                usos.setdefault(a.name, no.lineno)
    for nome in nomes:
        for attr, linha in atributos_de(arv, nome).items():
            usos.setdefault(attr, linha)
    return usos


def importados_por(rel, so_topo=False):
    try:
        arv = arvore(rel)
    except Exception:
        return set()
    nos = arv.body if so_topo else list(ast.walk(arv))
    nomes = set()
    for no in nos:
        if isinstance(no, ast.Import):
            nomes.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
            nomes.add(no.module.split(".")[0])
    return nomes


def _onde_mora_o_toast(fontes):
    donos = sorted(n for n, t in fontes.items()
                   if "ToastNotificationManager" in (t or ""))
    portas = sorted(n for n, t in fontes.items()
                    if n != "radai_notify.py"
                    and re.search(r"\bimport radai_notify\b", t or ""))
    return donos, portas


def checar_acoplamento():
    print("\n[2] Acoplamento vigia x motor")
    try:
        engine, vigia = arvore(no_app("engine.py")), arvore(no_app("radai_watcher.py"))
    except Exception as e:
        checar("le os dois modulos", False, str(e))
        return
    definidos = nomes_de_modulo(engine)
    usados = atributos_de(vigia, "engine")
    checar("o vigia usa pelo menos uma funcao do motor", len(usados) > 0,
           "%d referencias" % len(usados))
    for nome in sorted(usados):
        checar("motor.%s existe" % nome, nome in definidos,
               "usado em radai_watcher.py:%d" % usados[nome])

    if os.path.exists(_componentes.fonte(no_app("radai_geom.py"))):
        geom = arvore(no_app("radai_geom.py"))
        checar("radai_geom nao importa o motor (evita dependencia circular)",
               "engine" not in [n.names[0].name for n in ast.walk(geom)
                               if isinstance(n, ast.Import)])
        definidos_geom = nomes_de_modulo(geom)
        usos_geom = {}
        for nome in _componentes.nomes("app"):
            if not nome.endswith(".py") or nome == "radai_geom.py":
                continue
            try:
                arv_m = arvore(no_app(nome))
            except Exception:
                continue
            for attr, linha in usos_do_modulo(arv_m, "radai_geom").items():
                usos_geom.setdefault(attr, "%s:%d" % (nome, linha))
        checar("os apps chamam o radai_geom (a geometria nao se duplica)",
               len(usos_geom) >= 10, "%d nome(s) usados" % len(usos_geom))
        for attr in sorted(usos_geom):
            checar("radai_geom.%s existe" % attr, attr in definidos_geom,
                   "usado em %s" % usos_geom[attr])
        isca = ast.parse("import radai_geom as G" + NL + "def f():" + NL
                         + "    from radai_geom import receita_nova" + NL
                         + "    return G.aplicar_receita(1, 2)" + NL)
        achados_isca = usos_do_modulo(isca, "radai_geom")
        checar("  (isca) o uso de uma funcao que saiu e achado, com alias e "
               "com from-import",
               "aplicar_receita" in achados_isca
               and "receita_nova" in achados_isca
               and not ({"aplicar_receita", "receita_nova"} & definidos_geom))

    PESADOS = {"numpy", "scipy", "fastapi", "uvicorn", "pydicom", "SimpleITK",
               "torch", "rt_utils", "nibabel", "engine", "radai_geom", "radai_watcher"}
    for modulo in ("radai_archive", "radai_config", "radai_notify",
                   "radai_falhas"):
        if os.path.exists(_componentes.fonte(no_app(modulo + ".py"))):
            pesados = importados_por(no_app(modulo + ".py")) & PESADOS
            checar("%s importa so biblioteca padrao" % modulo, not pesados,
                   "arrasta: %s" % sorted(pesados))

    fontes = {}
    for _n in _componentes.nomes("app"):
        if _n.endswith(".py"):
            try:
                fontes[_n] = io.open(_componentes.fonte("app/" + _n),
                                     encoding="utf-8").read()
            except Exception:
                pass
    donos, portas = _onde_mora_o_toast(fontes)
    checar("o toast do Windows mora num lugar so (`radai_notify`)",
           donos == ["radai_notify.py"], str(donos))
    checar("  e as duas portas o chamam (o vigia e o «Rodar agora»)",
           {"radai_watcher.py", "radai_batch.py"} <= set(portas), str(portas))
    forjadas = dict(fontes)
    forjadas["radai_batch.py"] = (fontes.get("radai_batch.py", "")
                                  + "\n# [Windows.UI.Notifications."
                                    "ToastNotificationManager]\n")
    checar("  isca: uma copia do script do toast no lote e acusada",
           _onde_mora_o_toast(forjadas)[0]
           == ["radai_batch.py", "radai_notify.py"],
           str(_onde_mora_o_toast(forjadas)[0]))
    sem = dict(fontes)
    sem["radai_batch.py"] = re.sub(r"\bimport radai_notify\b", "import os",
                                   fontes.get("radai_batch.py", ""))
    checar("  isca: o lote que nao chama o modulo e acusado",
           "radai_batch.py" not in _onde_mora_o_toast(sem)[1],
           str(_onde_mora_o_toast(sem)[1]))

    for modulo in ("radai_rt",):
        caminho = no_app(modulo + ".py")
        if not os.path.exists(os.path.join(RAIZ, caminho)):
            continue
        importados = importados_por(caminho)
        checar("%s nao importa o vigia (evita dependencia circular)" % modulo,
               "radai_watcher" not in importados)
        if modulo != "radai_rt":
            checar("%s usa a lib de geometria em vez de refazer a conta" % modulo,
                   "radai_geom" in importados)
        usa_scipy = atributos_de(arvore(caminho), "ndimage")
        checar("%s nao chama ndimage direto (isso e papel do radai_geom)" % modulo,
               not usa_scipy or modulo == "radai_calibrator",
               "usa: %s" % sorted(usa_scipy))

    if os.path.exists(_componentes.fonte(no_app("radai_panel.py"))):
        do_painel = importados_por(no_app("radai_panel.py"))
        checar("radai_panel nao importa o vigia (evita dependencia circular)",
               "radai_watcher" not in do_painel)
        checar("radai_panel nao importa fastapi no topo do modulo",
               "fastapi" not in importados_por(no_app("radai_panel.py"), so_topo=True))


def checar_config():
    print("\n[3] Chaves de configuracao do vigia")
    try:
        arv = arvore(no_app("radai_watcher.py"))
    except Exception as e:
        checar("le o vigia", False, str(e))
        return

    texto_default, defaults_dict = None, None
    for no in ast.walk(arv):
        if isinstance(no, ast.Assign):
            for alvo in no.targets:
                if not isinstance(alvo, ast.Name):
                    continue
                if alvo.id == "DEFAULT_CFG" and isinstance(no.value, ast.Constant):
                    texto_default = no.value.value
                if alvo.id == "DEFAULTS" and isinstance(no.value, ast.Dict):
                    defaults_dict = set(k.value for k in no.value.keys
                                        if isinstance(k, ast.Constant))
    if texto_default is None or defaults_dict is None:
        checar("acha DEFAULT_CFG e o dicionario DEFAULTS",
               False, "DEFAULT_CFG=%s DEFAULTS=%s" % (texto_default is not None,
                                                      defaults_dict is not None))
        return

    no_arquivo = set()
    for linha in texto_default.splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            no_arquivo.add(linha.split("=", 1)[0].strip())

    lidas = set()
    for no in ast.walk(arv):
        if (isinstance(no, ast.Subscript) and isinstance(no.value, ast.Name)
                and no.value.id == "CFG" and isinstance(no.slice, ast.Constant)):
            lidas.add(no.slice.value)

    checar("toda chave do config modelo tem default no codigo",
           no_arquivo <= defaults_dict, "faltam: %s" % sorted(no_arquivo - defaults_dict))
    checar("todo default do codigo aparece no config modelo",
           defaults_dict <= no_arquivo, "so no codigo: %s" % sorted(defaults_dict - no_arquivo))
    checar("toda chave lida com CFG[...] esta declarada",
           lidas <= defaults_dict, "nao declaradas: %s" % sorted(lidas - defaults_dict))
    print("       (%d chaves: %s)" % (len(no_arquivo), ", ".join(sorted(no_arquivo))))


CHAVES_QUE_SAIRAM_V83 = ("INCLUIR_NV", "INCLUIR_CADS", "INCLUIR_MOOSE",
                         "INCLUIR_HNLNL", "ENTREGAR_TS", "URL_VERSOES",
                         "TIMEOUT_NV_H")
CHAVE_QUE_O_MOTOR_TINHA = {"cads": "INCLUIR_CADS", "nv": "INCLUIR_NV",
                           "mse": "INCLUIR_MOOSE", "hnlnl": "INCLUIR_HNLNL"}
CHAVES_QUE_ENTRARAM_V83 = {"IDIOMA": "", "TRAVA_SEM_PULSO_MIN": "15",
                           "TRAVA_PAGINANDO_MIN": "30", "TRAVA_RAM_PCT": "95"}


def _config_do_vigia(fonte):
    fora = {"texto": {}, "defaults": {}, "aplicar": set(),
            "obsoletas": set(), "alias": {}}
    try:
        arv = ast.parse(fonte)
    except SyntaxError:
        return fora
    for no in arv.body:
        if isinstance(no, ast.Assign):
            for alvo in no.targets:
                if not isinstance(alvo, ast.Name):
                    continue
                v = no.value
                if alvo.id == "DEFAULT_CFG" and isinstance(v, ast.Constant):
                    for linha in str(v.value).splitlines():
                        linha = linha.strip()
                        if linha and not linha.startswith("#") and "=" in linha:
                            k, val = linha.split("=", 1)
                            fora["texto"][k.strip()] = val.strip()
                if alvo.id == "DEFAULTS" and isinstance(v, ast.Dict):
                    for k, val in zip(v.keys, v.values):
                        if isinstance(k, ast.Constant):
                            fora["defaults"][k.value] = (
                                val.value if isinstance(val, ast.Constant)
                                else None)
                if alvo.id == "CHAVES_OBSOLETAS" and isinstance(v, ast.Dict):
                    fora["obsoletas"] = set(k.value for k in v.keys
                                            if isinstance(k, ast.Constant))
                if alvo.id == "ALIAS_CFG" and isinstance(v, ast.Dict):
                    fora["alias"] = dict(
                        (k.value, x.value) for k, x in zip(v.keys, v.values)
                        if isinstance(k, ast.Constant)
                        and isinstance(x, ast.Constant))
        if isinstance(no, ast.FunctionDef) and no.name == "aplicar_cfg":
            fora["aplicar"] = set(
                n.value for n in ast.walk(no)
                if isinstance(n, ast.Constant) and isinstance(n.value, str))
    return fora


def _motor_volta_ao_config(chave, fonte, ramo=True):
    c = _config_do_vigia(fonte)
    fora = []
    if chave in c["defaults"]:
        fora.append(u"%s voltou ao DEFAULTS" % chave)
    if chave in c["texto"]:
        fora.append(u"%s voltou ao texto do DEFAULT_CFG" % chave)
    if chave in c["aplicar"]:
        fora.append(u"aplicar_cfg le %s" % chave)
    codigo = u"\n".join(l for l in fonte.splitlines()
                        if not l.lstrip().startswith("#"))
    if ramo and re.search(r"\bif\s+%s\b" % re.escape(chave), codigo):
        fora.append(u"o vigia tem um ramo `if %s:`" % chave)
    if chave not in c["obsoletas"]:
        fora.append(u"%s fora de CHAVES_OBSOLETAS (o config antigo cairia em "
                    u"«chave desconhecida»)" % chave)
    return fora


def _chave_nova_nas_tres_casas(chave, fonte):
    c = _config_do_vigia(fonte)
    fora = []
    if chave not in c["defaults"]:
        fora.append(u"%s fora do DEFAULTS" % chave)
    if chave not in c["texto"]:
        fora.append(u"%s fora do texto do DEFAULT_CFG" % chave)
    if chave not in c["aplicar"]:
        fora.append(u"aplicar_cfg nao le %s (vale no arranque e some na "
                    u"recarga a quente)" % chave)
    return fora


def _horas_da_constante(fonte, nome):
    m = re.search(r"^%s\s*=\s*([0-9 *]+?)\s*(?:#.*)?$" % re.escape(nome),
                  fonte or u"", re.M)
    if not m:
        return None
    v = 1
    for p in m.group(1).split("*"):
        p = p.strip()
        if not p.isdigit():
            return None
        v *= int(p)
    return v / 3600.0


def _ajuda_do_teto_divergente(fonte, hnl=None, cads=None, cranio=None):
    fora = []
    try:
        hnl = hnl if hnl is not None else ler(no_app("radai_hnlnl_engine.py"))
        cads = cads if cads is not None else ler(no_app("radai_cads_engine.py"))
        cranio = (cranio if cranio is not None
                  else ler(no_app("radai_cranio_engine.py")))
    except Exception as e:
        return [u"nao li os motores: %s" % e]
    m = re.search(r"((?:^#[^\n]*\n)+)TIMEOUT_TASK_H=", fonte, re.M)
    if not m:
        return [u"nao achei o comentario do TIMEOUT_TASK_H"]
    txt = u" ".join(l.lstrip(u"#").strip() for l in m.group(1).splitlines())
    if u"QUALQUER task" in txt:
        fora.append(u"a ajuda diz «QUALQUER task»")
    for k in (u"TotalSegmentator", u"NV-Segment-CT", u"MOOSE"):
        if k not in txt:
            fora.append(u"a ajuda nao diz que cobre o %s" % k)
    for nome, src, const in ((u"niveis cervicais", hnl, "TEMPO_LIMITE_S"),
                             (u"CADS", cads, "TETO_S"),
                             (u"modelo do encefalo em TC", cranio, "TETO_S")):
        h =_horas_da_constante(src, const)
        if h is None:
            fora.append(u"nao li o %s do motor dos %s" % (const, nome))
            continue
        frase = u"%s (teto fixo de %g h" % (nome, h)
        if frase not in txt:
            fora.append(u"a ajuda nao diz «%s»" % frase)
    o = re.search(r'"TIMEOUT_NV_H":\s*u"([^"]*)"', fonte)
    if not o or u"qualquer task" in o.group(1).lower():
        fora.append(u"a linha de arranque do TIMEOUT_NV_H obsoleto diz "
                    u"«teto de qualquer task»")
    return fora


def checar_chaves_da_v83():
    print("\n[3b] As chaves do config que sairam e entraram na v8.3")
    try:
        fonte = ler(no_app("radai_watcher.py"))
    except Exception as e:
        checar("le o vigia", False, str(e))
        return False
    c = _config_do_vigia(fonte)
    for k in CHAVES_QUE_SAIRAM_V83:
        p = _motor_volta_ao_config(k, fonte, ramo=(k != "URL_VERSOES"))
        checar(u"`%s` saiu das tres casas e esta em CHAVES_OBSOLETAS" % k,
               not p, "; ".join(p))
    for k, fab in sorted(CHAVES_QUE_ENTRARAM_V83.items()):
        p = _chave_nova_nas_tres_casas(k, fonte)
        checar(u"`%s` esta nas tres casas" % k, not p, "; ".join(p))
        checar(u"  e nasce %r nas duas que tem valor" % fab,
               c["texto"].get(k) == fab and c["defaults"].get(k) == fab,
               u"texto=%r DEFAULTS=%r" % (c["texto"].get(k),
                                          c["defaults"].get(k)))
    alvos_fora = sorted(v for v in c["alias"].values()
                        if v not in c["defaults"])
    checar(u"todo alvo de ALIAS_CFG existe em DEFAULTS", not alvos_fora,
           str(alvos_fora))
    dupla = sorted(set(c["alias"]) & c["obsoletas"])
    checar(u"  e nenhuma chave e apelido e obsoleta ao mesmo tempo",
           not dupla, str(dupla))
    div = _ajuda_do_teto_divergente(fonte)
    checar(u"a ajuda do `TIMEOUT_TASK_H` diz o que ele cobre, e os tetos "
           u"fixos dos niveis cervicais e do CADS lidos do codigo",
           not div, u"; ".join(div))
    m = re.search(r"((?:^#[^\n]*\n)+)TIMEOUT_TASK_H=", fonte, re.M)
    if m:
        velho = fonte.replace(m.group(1), (
            u"# Teto ABSOLUTO de tempo para UMA task (horas) -- QUALQUER "
            u"task: a base e as\n# complementares do TotalSegmentator, os "
            u"niveis cervicais e os motores de\n# comparacao pedidos no "
            u"PERSONALIZADO.\n"), 1)
        checar(u"  (isca) a ajuda de antes («QUALQUER task») e acusada",
               bool(_ajuda_do_teto_divergente(velho)))
    checar(u"  (isca) o CADS com outro teto no codigo, e a ajuda de hoje, e "
           u"acusado", bool(_ajuda_do_teto_divergente(
               fonte, cads=u"TETO_S = 7200\n")))
    checar(u"  (isca) o modelo do encefalo com outro teto no codigo e "
           u"acusado", bool(_ajuda_do_teto_divergente(
               fonte, cranio=u"TETO_S = 3 * 3600\n")))
    checar(u"  (isca) a linha de arranque do TIMEOUT_NV_H de antes e acusada",
           bool(_ajuda_do_teto_divergente(fonte.replace(
               u'"TIMEOUT_NV_H": u"o TIMEOUT_TASK_H e o teto do NV tambem"',
               u'"TIMEOUT_NV_H": u"o TIMEOUT_TASK_H e o teto de qualquer '
               u'task"', 1))))
    isca1 = re.sub(r'"TRAVA_RAM_PCT",\s*float', '"TRAVA_RAM_PC_X", float',
                   fonte, count=1)
    checar(u"  (isca) a chave nova sem a leitura em aplicar_cfg e acusada",
           isca1 != fonte
           and any(u"aplicar_cfg nao le" in x
                   for x in _chave_nova_nas_tres_casas("TRAVA_RAM_PCT", isca1)),
           str(_chave_nova_nas_tres_casas("TRAVA_RAM_PCT", isca1)))
    isca2 = fonte.replace('DEFAULTS = {"ROOT": ""',
                          'DEFAULTS = {"ENTREGAR_TS": "1", "ROOT": ""', 1)
    checar(u"  (isca) a chave velha de volta ao DEFAULTS e acusada",
           isca2 != fonte and bool(_motor_volta_ao_config("ENTREGAR_TS",
                                                          isca2)))
    return None


NUCLEO = [
    no_app("radai_watcher.py"), no_app("engine.py"), no_app("radai_geom.py"),
    no_app("radai_archive.py"), no_app("radai_panel.py"), no_app("radai_config.py"),
    no_app("radai_rt.py"),
    no_app("radai_models.py"), no_app("radai_nv_engine.py"), no_app("radai_terms.py"),
    no_app("radai_compare.py"), no_app("radai_batch.py"),
    no_app("RADIOTERAPIA_AI_LOCAL_SUITE.cmd"),
    no_app("launchers/start_watcher.cmd"),
    no_app("launchers/open_browser.cmd"),
    "tools/make_test_series.py", "tools/test_geom.py", "tools/test_engine.py",
    "tools/test_watcher.py", "tools/test_panel.py", "tools/test_rt.py",
]
SO_NO_REPO = [
    "build/requirements-demo.txt", ".gitignore",
] + (list(OF.SO_NA_OFICINA) if OF else [])


def checar_arquivos():
    no_repo = (os.path.isdir(os.path.join(RAIZ, "build"))
               and os.path.isdir(os.path.join(RAIZ, "installer")))
    print("\n[4] Arquivos esperados (%s)" % ("repositorio" if no_repo else "deploy"))
    if no_repo and OF is None:
        _componentes.pulado(u"[4] os arquivos que so a oficina tem")
    for rel in NUCLEO + (SO_NO_REPO if no_repo else []):
        checar("existe: %s" % rel, os.path.exists(_componentes.fonte(rel, RAIZ)))


CICLO_APAGADO = ("radai_calibrator", "radai_compiler", "radai_crosscheck",
                 "radai_studio")
ORFAOS_DA_V85 = ("radai_anatomy_base", "radai_breast", "radai_deface",
                 "radai_delivery_tps", "radai_demo", "radai_internal",
                 "radai_nninteractive", "radai_pelvis", "radai_png",
                 "radai_policy",
                 "radai_reference", "radai_roadmap", "radai_suggestion",
                 "radai_suite",
                 "radai_thorax", "radai_thorax_screen",
                 "radai_thorax_session", "radai_training", "radai_wanted",
                 "radai_weights")


def _defeitos_do_ciclo_apagado(fontes, orfaos, apagados=CICLO_APAGADO):
    defeitos = []
    for m in apagados:
        if ("app/%s.py" % m) in fontes:
            defeitos.append("o arquivo app/%s.py existe" % m)
        for nome, txt in sorted(fontes.items()):
            if nome == "app/%s.py" % m:
                continue
            cod = so_codigo(txt)
            achou = ("import %s" % m) in cod or ("from %s import" % m) in cod
            if not achou and nome.startswith("app/"):
                try:
                    achou = any(isinstance(no, ast.Constant) and no.value == m
                                for no in ast.walk(ast.parse(txt)))
                except SyntaxError:
                    achou = ('"%s"' % m) in txt or ("'%s'" % m) in txt
            if achou:
                defeitos.append("%s importa %s" % (nome, m))
    for rel, lista in sorted(orfaos.items()):
        falta = [m + ".py" for m in apagados if (m + ".py") not in lista]
        if falta:
            defeitos.append("o $ORFAOS de %s nao tem %s" % (rel, ", ".join(falta)))
    return defeitos


def _fontes_e_orfaos_da_limpeza():
    fontes = {}
    for pasta, d in _componentes.pastas_de(("app", "tools", "build"), RAIZ, no_app("")):
        if not os.path.isdir(d):
            continue
        for nome in sorted(os.listdir(d)):
            if nome.endswith(".py") and not (pasta == "tools"
                                             and nome == "check_project.py"):
                try:
                    fontes[pasta + "/" + nome] = io.open(
                        os.path.join(d, nome), encoding="utf-8",
                        errors="replace").read()
                except Exception:
                    pass
    orfaos = {}
    for rel in ("packager/UPDATE.ps1", "installer/INSTALL.ps1"):
        try:
            t = io.open(os.path.join(RAIZ, rel), encoding="utf-8-sig").read()
            mm = re.search(r"\$ORFAOS\s*=\s*@\((.*?)\)", t, re.S)
            orfaos[rel] = re.findall(r'"([^"]+)"', mm.group(1)) if mm else []
        except Exception:
            orfaos[rel] = []
    return fontes, orfaos


def checar_orfaos_da_v85_apagados():
    print(NL + "[4c] Os orfaos que a v8.5 tirou nao voltam")
    fontes, orfaos = _fontes_e_orfaos_da_limpeza()
    d = _defeitos_do_ciclo_apagado(fontes, orfaos, ORFAOS_DA_V85)
    checar("nenhum orfao da v8.5 volta (arquivo, import e $ORFAOS)",
           not d, "; ".join(d[:6]))
    orf = dict((rel, [m + ".py" for m in ORFAOS_DA_V85]) for rel in orfaos)
    c1 = {"app/radai_batch.py": u"def f():" + NL + u"    import radai_demo" + NL}
    checar("  (isca) um import do modulo da demo reprova",
           bool(_defeitos_do_ciclo_apagado(c1, orf, ORFAOS_DA_V85)))
    o2 = dict(orf)
    o2["packager/UPDATE.ps1"] = [x for x in orf.get("packager/UPDATE.ps1", [])
                                 if x != "radai_thorax.py"]
    checar("  (isca) um nome a menos no $ORFAOS reprova",
           bool(_defeitos_do_ciclo_apagado({}, o2, ORFAOS_DA_V85)))


def _saidos_desde_a_ultima_tag(pasta):
    import subprocess

    def g(*args):
        try:
            p = subprocess.run(["git", "-C", pasta] + list(args),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL,
                               universal_newlines=True, timeout=30)
        except Exception:
            return None
        return p.stdout if p.returncode == 0 else None
    tag = (g("describe", "--tags", "--abbrev=0") or "").strip()
    saida = g("diff", "--name-status", "-M", tag, "HEAD", "--", "app",
              "tools") if tag else None
    if saida is None:
        return None
    return [l.split("\t")[1] for l in saida.splitlines()
            if l[:1] in ("D", "R") and "\t" in l]


def _no_orfaos(rel):
    if rel.startswith("app/"):
        return rel[4:].replace("/", "\\")
    if rel.startswith("tools/"):
        return rel.replace("/", "\\")
    return None


def _saidos_sem_orfao(saidos, orfaos, vivos):
    defeitos = []
    for rel in sorted(set(saidos)):
        alvo = _no_orfaos(rel)
        if alvo is None or alvo.lower() in vivos:
            continue
        for arq, lista in sorted(orfaos.items()):
            if alvo.lower() not in set(x.lower() for x in lista):
                defeitos.append("%s saiu e o $ORFAOS de %s nao tem %s"
                                % (rel, arq, alvo))
    return defeitos


def checar_o_que_saiu_vai_ao_orfaos():
    print(NL + "[4d] O que saiu de app/ e tools/ desde a ultima tag esta no $ORFAOS")
    _fontes, orfaos = _fontes_e_orfaos_da_limpeza()
    a, b = orfaos.get("installer/INSTALL.ps1"), orfaos.get("packager/UPDATE.ps1")
    checar("o $ORFAOS e' o mesmo no INSTALL.ps1 e no UPDATE.ps1",
           bool(a) and a == b, "INSTALL=%d UPDATE=%d nomes" % (len(a or []),
                                                                len(b or [])))
    pastas = [(RAIZ, "Suite")] + [(p, d.get("nome") or os.path.basename(p))
                                  for p, d in _componentes.componentes(RAIZ)]
    saidos, vivos, sem_git = [], set(), []
    for pasta, nome in pastas:
        lista = _saidos_desde_a_ultima_tag(pasta)
        if lista is None:
            sem_git.append(nome)
        else:
            saidos += lista
        for sub in ("app", "tools"):
            base = os.path.join(pasta, sub)
            for raiz, dirs, arqs in os.walk(base):
                dirs[:] = [x for x in dirs if x != "__pycache__"]
                for x in arqs:
                    rel = os.path.relpath(os.path.join(raiz, x), pasta)
                    alvo = _no_orfaos(rel.replace(os.sep, "/"))
                    if alvo:
                        vivos.add(alvo.lower())
    if sem_git:
        _componentes.pulado(u"[4d] sem Git ou sem tag em %s" % ", ".join(sem_git))
    d = _saidos_sem_orfao(saidos, orfaos, vivos)
    checar("todo arquivo que saiu desde a ultima tag esta no $ORFAOS dos dois "
           "(%d saido(s))" % len(set(saidos)), not d, "; ".join(d[:6]))
    orf = {"packager/UPDATE.ps1": ["radai_x.py"],
           "installer/INSTALL.ps1": ["radai_x.py"]}
    checar("  (isca) um modulo que saiu e nao esta no $ORFAOS reprova",
           bool(_saidos_sem_orfao(["app/radai_y.py"], orf, set())))
    checar("  (isca) uma bateria que saiu de tools/ e falta num dos dois reprova",
           bool(_saidos_sem_orfao(["tools/test_y.py"],
                                  {"packager/UPDATE.ps1": ["tools\\test_y.py"],
                                   "installer/INSTALL.ps1": []}, set())))
    checar("  (isca) o que saiu e esta nos dois passa",
           not _saidos_sem_orfao(["app/radai_x.py"], orf, set()))
    checar("  (isca) o que so' mudou de pasta (continua em app/) passa",
           not _saidos_sem_orfao(["app/radai_y.py"], orf, {"radai_y.py"}))


def checar_ciclo_de_calibracao_apagado():
    print(NL + "[4b] O ciclo de calibracao foi apagado (v8.3)")
    fontes, orfaos = _fontes_e_orfaos_da_limpeza()
    d = _defeitos_do_ciclo_apagado(fontes, orfaos)
    checar("o ciclo de calibracao nao volta (arquivo, import e $ORFAOS)",
           not d, "; ".join(d))
    checar("  (a medida leu fontes de verdade)", len(fontes) > 50,
           "%d arquivo(s)" % len(fontes))

    base = {"app/radai_batch.py": u"import radai_geom" + NL,
            "app/radai_panel.py": u'for nome in ("radai_todo",):' + NL}
    orf = {"packager/UPDATE.ps1": [m + ".py" for m in CICLO_APAGADO],
           "installer/INSTALL.ps1": [m + ".py" for m in CICLO_APAGADO]}
    checar("  (isca) a fonte limpa passa",
           not _defeitos_do_ciclo_apagado(dict(base), dict(orf)))
    c1 = dict(base)
    c1["app/radai_batch.py"] = u"def f():" + NL + u"    import radai_calibrator" + NL
    checar("  (isca) um import preguicoso do calibrador reprova",
           bool(_defeitos_do_ciclo_apagado(c1, dict(orf))))
    c2 = dict(base)
    c2["app/radai_panel.py"] = u'for nome in ("radai_todo", "radai_studio"):' + NL
    checar("  (isca) o nome na lista do __import__ do painel reprova",
           bool(_defeitos_do_ciclo_apagado(c2, dict(orf))))
    c3 = dict(base)
    c3["app/radai_compiler.py"] = u"# voltou" + NL
    checar("  (isca) o arquivo de volta em app/ reprova",
           bool(_defeitos_do_ciclo_apagado(c3, dict(orf))))
    o4 = dict(orf)
    o4["packager/UPDATE.ps1"] = [x for x in orf["packager/UPDATE.ps1"]
                                 if x != "radai_crosscheck.py"]
    checar("  (isca) um nome a menos no $ORFAOS reprova",
           bool(_defeitos_do_ciclo_apagado(dict(base), o4)))


_EXT_IMAGEM = (".dcm", ".dicom", ".nii", ".nii.gz")


def _git(args, entrada=None):
    import subprocess
    try:
        p = subprocess.run(["git"] + args, cwd=RAIZ, input=entrada,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           universal_newlines=True, timeout=30)
        return p.returncode, p.stdout
    except Exception:
        return None, ""


def checar_dicom():
    print("\n[5] PHI: nenhum DICOM no repositorio")
    achados = []
    ignoradas = _NAO_VARRER
    for base, dirs, arquivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in ignoradas]
        for a in arquivos:
            if a.lower().endswith(_EXT_IMAGEM):
                achados.append(os.path.relpath(os.path.join(base, a), RAIZ))

    cod, saida = _git(["ls-files", "-z"])
    rastreados = [p for p in saida.split("\0")
                  if p.lower().endswith(_EXT_IMAGEM)] if cod == 0 else []
    conhecidas = pastas_conhecidas() if (rastreados or achados) else set()
    seguro = lambda lista: [_caminho_seguro(p.replace("\\", "/"),
                                            conhecidas) for p in lista[:5]]
    checar("nenhum .dcm/.nii RASTREADO pelo git", not rastreados,
           "ACHADOS: %s" % seguro(rastreados) if rastreados else "")

    expostos = []
    for a in achados:
        c2, _ = _git(["check-ignore", "-q", a.replace("\\", "/")])
        if c2 != 0:
            expostos.append(a)

    checar("nenhum .dcm/.nii solto onde o git alcanca", not expostos,
           "ACHADOS: %s" % seguro(expostos) if expostos else "")
    if expostos or rastreados:
        print("       >>> PARE. Imagem de paciente nao entra no repositorio. <<<")
    elif achados:
        print("       (%d imagem(ns) no disco, todas ignoradas pelo git — "
              "saida de execucao real, nao vao para commit)" % len(achados))


PACIENTE_EXTENSOES = (
    (".dcm", u"DICOM"),
    (".dicom", u"DICOM"),
    (".nii", u"NIfTI: o volume da serie"),
    (".nii.gz", u"NIfTI comprimido"),
    (".nrrd", u"NRRD: cabecalho e voxels num arquivo so"),
    (".nhdr", u"NRRD destacado: o cabecalho; os voxels moram ao lado"),
    (".mha", u"MetaImage: cabecalho e voxels num arquivo so"),
    (".mhd", u"MetaImage destacado: o cabecalho; os voxels moram ao lado"),
    (".raw", u"os voxels do .mhd e do .nhdr"),
    (".raw.gz", u"os voxels do .nhdr, comprimidos"),
    (".zraw", u"os voxels do .mhd, comprimidos"),
    (".hdr", u"Analyze 7.5: o cabecalho; os voxels moram no .img"),
    (".img", u"Analyze 7.5: os voxels"),
    (".img.gz", u"Analyze 7.5: os voxels, comprimidos"),
    (".mgz", u"FreeSurfer: volume comprimido"),
)
PACIENTE_EXT = tuple(e for e, _pq in PACIENTE_EXTENSOES)

PACIENTE_PASTAS = {
    "registro": u"registro de casos: o segredo do pseudonimo e o log de cada "
                u"serie",
    "calibracao": u"acervo da calibracao: o indice guarda caminho da serie e "
                  u"PatientID",
    "_radai": u"os marcadores gravados ao lado da serie do paciente",
    "validacao": u"o registro da RDC 657/2022, caso a caso",
}

PACIENTE_NOMES = (
    (r"^rs_radai_", "rtstruct_do_app",
     u"RTSTRUCT gravado ao lado de uma serie de paciente"),
    (r"\.log$", "log_de_execucao",
     u"o log do vigia e do motor cita a serie e o PatientID"),
    (r"_log\.txt$", "log_de_execucao",
     u"log de bateria ou de instalacao: caminhos desta maquina"),
    (r"^arranque_.*\.txt$", "estado_da_estacao",
     u"o bloco do arranque: caminhos e o retrato da estacao"),
    (r"^radai_status\.json$", "estado_da_estacao",
     u"o sinal de vida do vigia: a serie em processamento"),
    (r"^radai_watcher\.config$", "estado_da_estacao",
     u"o config da estacao: o ROOT aponta a arvore de pacientes"),
    (r"^_dados\.txt$", "estado_da_estacao",
     u"aponta onde o dado de paciente mora nesta maquina"),
    (r"^_pseudonimo\.chave$", "segredo_do_pseudonimo",
     u"com ele, todo pseudonimo publicado volta a ser testavel"),
)
_PACIENTE_NOMES_RX = tuple((re.compile(rx, re.I), cat, pq)
                           for rx, cat, pq in PACIENTE_NOMES)

_GRUPOS_DE_ABERTURA = (b"\x02\x00", b"\x08\x00")
_VRS = frozenset(v.encode("ascii") for v in (
    "AE AS AT CS DA DS DT FD FL IS LO LT OB OD OF OL OV OW PN SH SL SQ SS "
    "ST SV TM UC UI UL UN UR US UT UV").split())


def _dicom_sem_preambulo(dados):
    if len(dados) < 8 or dados[:2] not in _GRUPOS_DE_ABERTURA:
        return False
    if dados[4:6] in _VRS:
        return True
    n = int.from_bytes(dados[4:8], "little")
    return (dados[:2] == b"\x08\x00" and 0 < n <= 1024 and n % 2 == 0
            and len(dados) >= 8 + n)


RAIZES_DE_FABRICANTE = (
    ("1.2.840.113619", u"GE"),
    ("1.3.12.2.1107", u"Siemens"),
    ("1.2.392.200036", u"Canon/Toshiba"),
    ("1.3.46.670589", u"Philips"),
    ("1.2.840.113704", u"Philips"),
    ("1.2.246.352", u"Varian"),
    ("1.2.840.113845", u"Elekta"),
)
_RE_UID_FABRICANTE = re.compile(
    r"(?<![0-9.])(?:%s)(?:\.[0-9]+)+"
    % "|".join(re.escape(r) for r, _q in RAIZES_DE_FABRICANTE))

EXCECOES_DE_RAIZ = {}

_RE_NOME_PN = re.compile(r"(?<![A-Za-z0-9_])([A-Z][A-Za-z]+)\^([A-Z][A-Za-z]+)")
_RE_NOME_PASTA = re.compile(
    r"(?<![A-Za-z0-9])([A-Z]{3,})_([A-Z]{3,})(?:_([A-Z]{2,}))?_[0-9]{3,}"
    r"|(?<![A-Za-z0-9])([A-Z]{3,})[ _]([A-Z]{3,})(?:[ _]([A-Z]{2,}))? "
    r"(?!(?:19|20)[0-9]{2}(?![0-9]))[0-9]{4,}")
SOBRENOMES_COMUNS = (
    "SILVA", "SANTOS", "OLIVEIRA", "SOUZA", "SOUSA", "PEREIRA", "LIMA",
    "COSTA", "FERREIRA", "RODRIGUES", "ALVES", "CARVALHO", "GOMES",
    "MARTINS", "ARAUJO", "RIBEIRO", "ALMEIDA", "LOPES", "SOARES", "BARBOSA",
    "MOREIRA", "ROCHA", "CARDOSO", "TEIXEIRA", "MELO", "BARROS", "FREITAS",
    "MENDES", "NUNES", "VIEIRA", "MONTEIRO", "MOURA", "FERNANDES",
    "MARQUES", "CASTRO", "ANDRADE", "MACHADO", "CAVALCANTI")
_SEP_NOME = r"(?:, ?|[ _^])"
_RE_NOME_SOBRENOME = re.compile(
    r"(?<![A-Za-z0-9])(?:([A-Z]{2,})" + _SEP_NOME + r")?("
    + "|".join(SOBRENOMES_COMUNS) + r")(?:" + _SEP_NOME
    + r"([A-Z]{2,}))?(?![A-Za-z0-9])")
_FANTOMA = frozenset((
    "FANTOMA", "FANTASMA", "TESTE", "TEST", "SINTETICO", "SINTETICA",
    "SYNTHETIC", "PHANTOM", "ANON", "ANONIMO", "ANONYMOUS", "ANONIMIZADO",
    "SOBRENOME", "NOME", "PACIENTE", "PATIENT", "DOE", "JOHN", "JANE",
    "FULANO", "SICRANO", "BELTRANO", "EXEMPLO", "EXAMPLE", "ISCA", "DUMMY",
    "FAKE", "CONV", "LAST", "FIRST", "NAME", "XXX", "ZZZ"))
_VOCABULARIO_DICOM = frozenset(("YBR",))


def _fantoma(*partes):
    return any((p or "").upper() in _FANTOMA
               or (p or "").upper() in _VOCABULARIO_DICOM for p in partes)


def parece_nome_de_paciente(texto):
    for m in _RE_NOME_PN.finditer(texto):
        if not _fantoma(*m.groups()):
            return True
    for m in _RE_NOME_PASTA.finditer(texto):
        if not _fantoma(*m.groups()):
            return True
    for m in _RE_NOME_SOBRENOME.finditer(texto):
        if (m.group(1) or m.group(3)) and not _fantoma(m.group(1),
                                                       m.group(3)):
            return True
    return False


def _texto_de(dados):
    if dados[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return dados.decode("utf-16")
        except Exception:
            return None
    if b"\0" in dados[:8192]:
        return None
    return dados.decode("utf-8", "replace")


def varrer_dado_de_paciente(itens):
    achados = []
    for rel, dados in itens:
        rel = rel.replace("\\", "/")
        originais = [p for p in rel.split("/") if p]
        partes = [p.lower() for p in originais]
        if not partes:
            continue
        nome = partes[-1]
        for p in partes[:-1]:
            if p in PACIENTE_PASTAS:
                achados.append((rel, 0, "pasta_de_execucao"))
                break
        if any(parece_nome_de_paciente(p) for p in originais):
            achados.append((rel, 0, "parece_nome_de_paciente"))
        if nome.endswith(PACIENTE_EXT):
            achados.append((rel, 0, "volume_medico"))
        for rx, cat, _pq in _PACIENTE_NOMES_RX:
            if rx.search(nome):
                achados.append((rel, 0, cat))
                break
        if dados is None:
            continue
        if dados[128:132] == b"DICM" or _dicom_sem_preambulo(dados):
            achados.append((rel, 0, "dicom"))
            continue
        if rel in EXCECOES_DE_RAIZ:
            continue
        texto = _texto_de(dados)
        if texto is None or not _RE_UID_FABRICANTE.search(texto):
            continue
        for i, linha in enumerate(texto.split("\n"), 1):
            if _RE_UID_FABRICANTE.search(linha):
                achados.append((rel, i, "uid_de_fabricante"))
    return achados


def _env_git_isolado():
    return dict(os.environ, GIT_CONFIG_NOSYSTEM="1",
                GIT_CONFIG_GLOBAL=os.devnull)


def _git_bytes(args, entrada=None, cwd=None, env=None):
    import subprocess
    try:
        p = subprocess.run(["git"] + args, cwd=cwd or RAIZ, input=entrada,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           env=env, timeout=120)
        return p.returncode, p.stdout
    except Exception:
        return None, b""


def _nomes_z(saida):
    return [n.decode("utf-8", "replace") for n in saida.split(b"\0") if n]


def arquivos_que_o_git_alcanca(raiz=None):
    c1, s1 = _git_bytes(["ls-files", "-z"], cwd=raiz)
    c2, s2 = _git_bytes(["ls-files", "-z", "--others", "--exclude-standard"],
                        cwd=raiz)
    if c1 != 0 or c2 != 0:
        return None
    return _nomes_z(s1), _nomes_z(s2)


def _temporaria(prefixo):
    import tempfile
    return tempfile.mkdtemp(prefix=prefixo)


def _apagar(pasta):
    import shutil
    shutil.rmtree(pasta, ignore_errors=True)


def _como_um_clone_novo_veria(raiz=None):
    raiz = raiz or RAIZ
    gd = _temporaria("radai_cp_gitdir_")
    try:
        cod, _s = _git_bytes(["init", "-q", "--bare", gd], cwd=gd,
                             env=_env_git_isolado())
        if cod != 0:
            return None
        cod, s = _git_bytes(["--git-dir=" + gd, "--work-tree=" + raiz,
                             "-c", "core.excludesFile=", "ls-files", "-z",
                             "--others", "--exclude-standard"],
                            cwd=raiz, env=_env_git_isolado())
        return _nomes_z(s) if cod == 0 else None
    finally:
        _apagar(gd)


_NAO_VARRER = (".git", ".venv", "__pycache__", "_RadAI", "python",
               "site-packages", "ts_weights", "nnUNet_results") + FORA


def _arvore_em_disco(raiz=None):
    raiz = raiz or RAIZ
    pular = tuple(x for x in _NAO_VARRER if x != "_RadAI")
    saida = []
    for base, dirs, arqs in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in pular]
        for a in arqs:
            saida.append(os.path.relpath(os.path.join(base, a), raiz)
                         .replace(os.sep, "/"))
    return saida


def arvore_alcancavel(raiz=None):
    listas = arquivos_que_o_git_alcanca(raiz)
    if listas is not None:
        return listas[0], listas[1], "git"
    soltos = _como_um_clone_novo_veria(raiz)
    if soltos is not None:
        return [], soltos, "clone_novo"
    return None


def conteudo_do_stage(raiz=None):
    cod, s = _git_bytes(["diff", "--cached", "--name-only", "-z",
                         "--diff-filter=ACMRT"], cwd=raiz)
    if cod != 0:
        return None
    nomes = _nomes_z(s)
    if not nomes:
        return []
    entrada = b"".join((u":%s\n" % n).encode("utf-8") for n in nomes)
    cod, s = _git_bytes(["cat-file", "--batch"], entrada=entrada, cwd=raiz)
    if cod != 0:
        return None
    saida, pos = [], 0
    for n in nomes:
        fim = s.index(b"\n", pos)
        cab = s[pos:fim].split()
        pos = fim + 1
        if len(cab) < 3 or cab[-1] == b"missing":
            saida.append((n, None))
            continue
        tam = int(cab[2])
        saida.append((n, s[pos:pos + tam]))
        pos += tam + 1
    return saida


def pastas_conhecidas(raiz=None):
    cod, s = _git_bytes(["ls-tree", "-r", "-d", "-z", "--name-only", "HEAD"],
                        cwd=raiz)
    if cod == 0:
        return set(_nomes_z(s))
    import json
    conhecidas = set()
    try:
        with io.open(os.path.join(raiz or RAIZ, "build", "publico.json"),
                     encoding="utf-8") as f:
            man = json.load(f)
    except Exception:
        return conhecidas
    for e in man.get("vai", ()):
        cam = e.get("caminho") or ""
        base = cam.rstrip("/") if cam.endswith("/") else cam.rpartition("/")[0]
        partes = [p for p in base.split("/") if p]
        for i in range(1, len(partes) + 1):
            conhecidas.add("/".join(partes[:i]))
    return conhecidas


def _escondido(componente, tipo):
    import hashlib
    return u"<%s#%s>" % (tipo, hashlib.sha1(
        componente.encode("utf-8")).hexdigest()[:4])


def _caminho_seguro(rel, conhecidas=None):
    conhecidas = conhecidas or set()
    partes = [p for p in rel.replace("\\", "/").split("/") if p]
    saida, prefixo, fora = [], u"", False
    for i, p in enumerate(partes):
        pasta = i < len(partes) - 1
        prefixo = p if not prefixo else prefixo + u"/" + p
        if pasta and prefixo not in conhecidas:
            fora = True
        if fora or parece_nome_de_paciente(p):
            saida.append(_escondido(p, u"pasta" if pasta else u"arquivo"))
        else:
            saida.append(p)
    return u"/".join(saida)


def _o_que_fazer(achados):
    cats = set(c for _r, _l, c in achados)
    linhas = [u">>> PARE. Dado de paciente nao entra no repositorio. <<<"]
    if cats - {"uid_de_fabricante", "parece_nome_de_paciente"}:
        linhas.append(u"  arquivo de execucao ou de imagem: tire do stage "
                      u"(git restore --staged <arquivo>) e mova para fora "
                      u"do repositorio e de qualquer pasta que sincronize")
    if "parece_nome_de_paciente" in cats:
        linhas.append(u"  caminho com forma de nome de paciente: tire do "
                      u"stage e renomeie; em fixture, use um nome que se "
                      u"prove fantoma (FANTOMA^TESTE)")
    if "uid_de_fabricante" in cats:
        linhas.append(u"  UID sob raiz de fabricante num texto: troque por "
                      u"um UID do fantoma (pydicom.uid.generate_uid, raiz "
                      u"1.2.826.0.1.3680043.8.498) ou por <uid>")
    return linhas


def _laudo_de_achados(achados, limite=40, conhecidas=None):
    if conhecidas is None:
        conhecidas = pastas_conhecidas()
    linhas = [u"%s:%d  [%s]" % (_caminho_seguro(r, conhecidas), l, c)
              for r, l, c in achados[:limite]]
    if len(achados) > limite:
        linhas.append(u"... e mais %d" % (len(achados) - limite))
    if any(u"<pasta#" in x or u"<arquivo#" in x for x in linhas):
        linhas.append(u"(<pasta#....>: pasta que o HEAD nao conhece, ou "
                      u"componente com forma de nome -- o caminho nao e "
                      u"impresso. Quem esta na maquina localiza com "
                      u"`git diff --cached --name-only` ou `git status`.)")
    return linhas


_IGNORADOS_EXIGIDOS = (
    "serie/IM000001.dcm", "serie/IM000001.DCM", "serie/x.dicom",
    "vol/x.nii", "vol/x.nii.gz", "vol/x.NII.GZ", "vol/x.nrrd", "vol/x.nhdr",
    "vol/x.mha", "vol/x.mhd", "vol/x.raw", "vol/x.raw.gz", "vol/x.zraw",
    "vol/x.hdr", "vol/x.img", "vol/x.img.gz", "vol/x.mgz",
    "serie/RS_RadAI_20260923.SIMULACAO.txt",
    "app/registro/casos/x/caso.json", "app/calibracao/acervo.jsonl",
    "p/_RadAI/serie.lock.json", "acervo/VALIDACAO/indice.json",
    "app/radai_vigia.log", "verify_log.txt",
    "calibracao2/arranque_20260923_101010.txt", "arranque_20260923_101010.txt",
    "radai_status.json", "app/radai_watcher.config", "_dados.txt",
    "app/_pseudonimo.chave",
)


def _entradas_sem_amostra(amostras, extensoes=None, pastas=None, nomes=None):
    extensoes = PACIENTE_EXT if extensoes is None else extensoes
    pastas = PACIENTE_PASTAS if pastas is None else pastas
    nomes = PACIENTE_NOMES if nomes is None else nomes
    achados = set(varrer_dado_de_paciente([(a, None) for a in amostras]))
    faltam = []
    for e in extensoes:
        if not any(a.lower().endswith(e)
                   and (a, 0, "volume_medico") in achados for a in amostras):
            faltam.append(u"extensao %s" % e)
    for p in pastas:
        if not any(p in [c.lower() for c in a.split("/")[:-1]]
                   and (a, 0, "pasta_de_execucao") in achados
                   for a in amostras):
            faltam.append(u"pasta %s/" % p)
    for rx, cat, _pq in nomes:
        r = re.compile(rx, re.I)
        if not any(r.search(a.split("/")[-1]) and (a, 0, cat) in achados
                   for a in amostras):
            faltam.append(u"nome %s" % rx)
    return faltam


def _ignorados_pelo_gitignore(rels, gitignores, raiz=None):
    raiz = raiz or RAIZ
    d = _temporaria("radai_cp_ignore_")
    try:
        cod, _s = _git_bytes(["init", "-q", d], cwd=d, env=_env_git_isolado())
        if cod != 0:
            return None
        for g in gitignores:
            alvo = os.path.join(d, g.replace("/", os.sep))
            os.makedirs(os.path.dirname(alvo), exist_ok=True)
            with open(os.path.join(raiz, g.replace("/", os.sep)), "rb") as f:
                dados = f.read()
            with open(alvo, "wb") as f:
                f.write(dados)
        with open(os.path.join(d, ".git", "info", "exclude"), "wb"):
            pass
        res = {}
        for rel in rels:
            cod, _s = _git_bytes(["-c", "core.excludesFile=", "check-ignore",
                                  "--no-index", "-q", rel], cwd=d,
                                 env=_env_git_isolado())
            res[rel] = {0: True, 1: False}.get(cod)
        return res
    except OSError:
        return None
    finally:
        _apagar(d)


def _padroes_no_info_exclude(raiz=None):
    cod, s = _git_bytes(["rev-parse", "--git-path", "info/exclude"], cwd=raiz)
    if cod != 0:
        return 0
    caminho = s.decode("utf-8", "replace").strip()
    if not os.path.isabs(caminho):
        caminho = os.path.join(raiz or RAIZ, caminho)
    try:
        with io.open(caminho, encoding="utf-8", errors="replace") as f:
            return sum(1 for ln in f
                       if ln.strip() and not ln.lstrip().startswith("#"))
    except OSError:
        return 0


def checar_sem_dado_de_paciente_no_repositorio():
    print(NL + "[5b] PHI: nada que o git alcanca parece dado de paciente")

    raiz_real = RAIZES_DE_FABRICANTE[0][0]
    nome_isca = u"_".join((u"SOU" + u"ZA", u"A" + u"NA", u"987" + u"65"))
    isca = [
        ("cd/IM000001", b"\0" * 128 + b"DICM" + b"\0" * 32),
        ("cd/IM000002", b"\x08\x00\x05\x00CS\x0a\x00ISO_IR 100"),
        ("cd/IM000003", b"\x08\x00\x16\x00\x1a\x00\x00\x00"
                        b"1.2.840.10008.5.1.4.1.1.2\0"),
        ("vol/ct.nii.gz", b""),
        ("vol/ct.raw", b""),
        ("serie/RS_RadAI_20260923.dcm", b""),
        ("app/registro/casos/c/caso.json", b"{}"),
        ("arranque_20260923_101010.txt", b"x"),
        ("radai_status.json", b"{}"),
        ("app/radai_watcher.config", b"ROOT="),
        ("_dados.txt", b"x"),
        ("app/_pseudonimo.chave", b"x"),
        ("app/radai_vigia.log", b"x"),
        (nome_isca + "/notas.txt", b"x"),
        ("tools/fixture.py",
         (u"UID = '%s.2.55.3.9'\n" % raiz_real).encode("utf-8")),
    ]
    esperado = {"dicom", "volume_medico", "rtstruct_do_app",
                "pasta_de_execucao", "estado_da_estacao",
                "segredo_do_pseudonimo", "log_de_execucao",
                "uid_de_fabricante", "parece_nome_de_paciente"}
    ach_isca = varrer_dado_de_paciente(isca)
    achou = set(c for _r, _l, c in ach_isca)
    checar(u"  (isca) a varredura acha cada categoria", achou == esperado,
           u"faltou: %s" % sorted(esperado - achou))
    checar(u"  (isca) o DICOM sem preambulo, com VR explicita e implicita",
           ("cd/IM000002", 0, "dicom") in ach_isca
           and ("cd/IM000003", 0, "dicom") in ach_isca)
    uid_linha = [(r, l) for r, l, c in ach_isca if c == "uid_de_fabricante"]
    checar(u"  (isca) e diz a LINHA do UID, sem o valor",
           uid_linha == [("tools/fixture.py", 1)], str(uid_linha))
    permitidos = [
        ("tools/fantoma.py", b"UID = '1.2.826.0.1.3680043.8.498.1234567'\n"),
        ("tools/raizes.py", (u"GE = '%s'\n" % raiz_real).encode("utf-8")),
        ("app/radai_doc.py", b"# o registro de casos mora em registro\\\n"),
        ("app/data/icone.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 200),
        ("app/data/outro.bin", b"\x08\x00\x00\x00\xff\xff\xff\xff" * 8),
        ("tools/sop.txt", b"SOP 1.2.840.10008.5.1.4.1.1.481.3\n"),
        ("tools/FANTOMA_TESTE_00001/notas.txt", b"x"),
    ]
    falsos = varrer_dado_de_paciente(permitidos)
    checar(u"  (isca) e NAO acusa fantoma, raiz nua, palavra nem binario",
           not falsos,
           u"; ".join(_laudo_de_achados(falsos, conhecidas={"tools"})))
    conh = {"app", "tools"}
    s1 = _caminho_seguro(nome_isca + "/CT/IM000001", conh)
    s2 = _caminho_seguro("tools/" + nome_isca + ".txt", conh)
    s3 = _caminho_seguro("app/data/x.py", conh)
    checar(u"  (isca) o caminho impresso esconde a pasta nova e o nome, e "
           u"mostra o resto",
           nome_isca not in s1 + s2 and u"987" not in s1 + s2
           and s1.startswith(u"<pasta#") and s2.startswith(u"tools/<arquivo#")
           and _caminho_seguro("app/ok.py", conh) == u"app/ok.py"
           and s3.startswith(u"app/<pasta#"), u"%s | %s | %s" % (s1, s2, s3))

    arv = arvore_alcancavel()
    if arv is not None:
        rastreados, soltos, como = arv
        rels = rastreados + soltos
        if como == "git":
            print(u"       (varri %d arquivo(s): %d rastreado(s) e %d nao "
                  u"rastreado(s) nem ignorado(s))"
                  % (len(rels), len(rastreados), len(soltos)))
        else:
            print(u"       (esta arvore NAO e um repositorio git -- o ZIP do "
                  u"GitHub, por exemplo. Varri o que um `git add -A` levaria "
                  u"num clone NOVO dela: o .gitignore vale, as exclusoes "
                  u"pessoais nao. %d arquivo(s))" % len(rels))
    else:
        como = "disco"
        rels = _arvore_em_disco()
        print(u"       (sem git nesta maquina: varri a arvore em DISCO, menos "
              u"runtime e pesos -- as exclusoes do [5], sem a `_RadAI`. Sem "
              u"git o .gitignore nao se aplica, e isto varre MAIS do que um "
              u"commit levaria. %d arquivo(s))" % len(rels))
    itens = []
    for rel in rels:
        caminho = os.path.join(RAIZ, rel)
        if not os.path.isfile(caminho):
            continue
        try:
            with open(caminho, "rb") as f:
                itens.append((rel, f.read()))
        except OSError:
            itens.append((rel, None))
    achados = varrer_dado_de_paciente(itens)
    checar(u"nada do que o git alcanca parece dado de paciente", not achados,
           u"%d achado(s)" % len(achados))
    for linha in _laudo_de_achados(achados):
        print(u"         " + linha)
    if achados:
        for linha in _o_que_fazer(achados):
            print(u"       " + linha)
    for pasta_c, dados_c in _componentes.componentes(RAIZ):
        arv_c = arvore_alcancavel(pasta_c)
        rels_c = (arv_c[0] + arv_c[1]) if arv_c is not None else _arvore_em_disco(pasta_c)
        itens_c = []
        for rel in rels_c:
            caminho = os.path.join(pasta_c, rel)
            if not os.path.isfile(caminho):
                continue
            try:
                with open(caminho, "rb") as f:
                    itens_c.append((rel, f.read()))
            except OSError:
                itens_c.append((rel, None))
        achados_c = varrer_dado_de_paciente(itens_c)
        checar(u"nada do que o git de %s alcanca parece dado de paciente (%d arquivo(s))"
               % (dados_c.get("nome"), len(itens_c)), not achados_c,
               u"%d achado(s)" % len(achados_c))
        for linha in _laudo_de_achados(achados_c):
            print(u"         " + linha)
    for rel, motivo in sorted(EXCECOES_DE_RAIZ.items()):
        checar(u"a excecao `%s` existe e diz por que" % rel,
               os.path.isfile(os.path.join(RAIZ, rel)) and bool(motivo))

    faltam = _entradas_sem_amostra(_IGNORADOS_EXIGIDOS)
    checar(u"cada extensao, pasta e nome das tabelas tem amostra no "
           u"`_IGNORADOS_EXIGIDOS`", not faltam, u", ".join(faltam))
    checar(u"  (isca) extensao nova sem amostra e acusada",
           _entradas_sem_amostra(_IGNORADOS_EXIGIDOS,
                                 extensoes=PACIENTE_EXT + (".isca_nova",))
           == [u"extensao .isca_nova"])
    gitignores = [r for r in rels if r.rsplit("/", 1)[-1] == ".gitignore"]
    codigo = no_app("radai_watcher.py")
    medida = (_ignorados_pelo_gitignore(list(_IGNORADOS_EXIGIDOS) + [codigo],
                                        gitignores)
              if gitignores and como != "disco" else None)
    if medida is None:
        print(u"       (sem git, ou sem .gitignore na arvore: a cobertura do "
              u".gitignore nao se mede aqui -- e sem git nenhum commit sai "
              u"desta maquina)")
        if como != "disco":
            checar(u"o .gitignore existe e o git o le", False,
                   u"%d .gitignore na arvore" % len(gitignores))
    else:
        fora = [rel for rel in _IGNORADOS_EXIGIDOS if medida.get(rel) is not True]
        checar(u"o .gitignore cobre cada categoria que tem nome (medido num "
               u"repositorio descartavel, sem a configuracao de quem roda)",
               not fora, u"nao ignorados: %s" % u", ".join(fora))
        checar(u"  (isca) e o codigo continua fora do .gitignore",
               medida.get(codigo) is False,
               u"check-ignore respondeu %r" % (medida.get(codigo),))
    if como == "git":
        n = _padroes_no_info_exclude()
        if n:
            print(u"       (aviso: o .git/info/exclude DESTE clone tem %d "
                  u"padrao(oes). Eles protegem so este clone -- a cobertura "
                  u"acima foi medida sem eles, e e ela que vale para quem "
                  u"clonar)" % n)

    gancho = os.path.join(RAIZ, ".githooks", "pre-commit")
    if APP == "app":
        try:
            with open(gancho, "rb") as f:
                g = f.read()
        except OSError:
            g = b""
        checar(u"o gancho .githooks/pre-commit existe", bool(g))
        if g:
            checar(u"  e e sh, LF e ASCII (o Git for Windows o roda com o "
                   u"sh dele)",
                   g.startswith(b"#!/bin/sh") and b"\r" not in g
                   and all(b < 128 for b in g))
            checar(u"  e chama a varredura do stage",
                   b"--paciente-no-stage" in g)


def main_do_stage():
    print(u"pre-commit: procurando dado de paciente no stage...")
    # GUARDA: o stage é o da pasta onde o Git roda o gancho; o padrão do
    # _git_bytes é a Suite, e um componente passaria lendo o stage dela.
    itens = conteudo_do_stage(os.getcwd())
    if itens is None:
        print(u"pre-commit: nao consegui ler o stage do git. O commit foi "
              u"RECUSADO -- na duvida, a checagem recusa.")
        return 1
    achados = varrer_dado_de_paciente(itens)
    if not achados:
        print(u"pre-commit: %d arquivo(s) no stage, nenhum parece dado de "
              u"paciente." % len(itens))
        return 0
    print(u"")
    print(u"pre-commit: COMMIT RECUSADO. %d achado(s) que parecem dado de "
          u"paciente:" % len(achados))
    for linha in _laudo_de_achados(achados, limite=200):
        print(u"   " + linha)
    print(u"")
    for linha in _o_que_fazer(achados):
        print(u"  " + linha)
    print(u"  NAO use --no-verify para passar isto: o que entra num commit "
          u"fica no historico.")
    print(u"  Categorias e excecoes: tools/check_project.py, bloco 5b.")
    return 1


_RE_LITERAL = re.compile(
    r"(?<=[(,=:\[!&|?{;\s])/(?:[^/\\\n\[]|\\.|\[(?:[^\]\\]|\\.)*\])+/[gimsuy]*")


def _sem_regex(linha):
    return _RE_LITERAL.sub("RE", linha)


def _paginas_do_modulo(caminho):
    try:
        arvore = ast.parse(io.open(caminho, encoding="utf-8").read())
    except Exception:
        return []
    fora = []
    for no in arvore.body:
        if not isinstance(no, ast.Assign):
            continue
        nomes = [a.id for a in no.targets if isinstance(a, ast.Name)]
        if not any(n.startswith(("PAGINA", "PAGE", "HTML", "CSS")) for n in nomes):
            continue
        v = no.value
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            fora.append(v.value)
    return fora


def _strings_quebradas(js):
    problemas = []
    dentro_de_bloco = False
    for n, bruta in enumerate(js.splitlines(), 1):
        linha = _sem_regex(bruta)
        if dentro_de_bloco:
            if "*/" not in linha:
                continue
            linha = linha.split("*/", 1)[1]
            dentro_de_bloco = False
        antes, sobra = linha, ""
        i, aspa, esc = 0, None, False
        while i < len(linha):
            c = linha[i]
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif aspa:
                if c == aspa:
                    aspa = None
            elif c in "'\"":
                aspa = c
            elif c == "/" and linha[i:i + 2] == "/*":
                fim = linha.find("*/", i + 2)
                if fim < 0:
                    antes, dentro_de_bloco = linha[:i], True
                    break
                linha = linha[:i] + " " + linha[fim + 2:]
                continue
            i += 1
        linha = antes if dentro_de_bloco else linha
        if sobra:
            linha += sobra
        if linha.lstrip().startswith("//"):
            continue
        aspa, escapado = None, False
        for ch in linha:
            if escapado:
                escapado = False
            elif ch == "\\":
                escapado = True
            elif aspa:
                if ch == aspa:
                    aspa = None
            elif ch in "'\"":
                aspa = ch
        if aspa:
            problemas.append((n, bruta.strip()[:90]))
    return problemas


def checar_js_das_telas():
    print("\n[6] Telas: nenhum literal de string JS partido por linha")
    achados = 0
    for rel in _componentes.nomes("app"):
        if not rel.endswith(".py"):
            continue
        for pagina in _paginas_do_modulo(_componentes.fonte("app/" + rel)):
            for js in re.findall(r"<script>(.*?)</script>", pagina, re.S):
                for n, linha in _strings_quebradas(js):
                    achados += 1
                    print("       %s, linha %d do script: %s" % (rel, n, linha))
    checar("nenhuma string JS aberta no fim da linha", achados == 0,
           "%d ocorrencia(s) — provavelmente \\n que virou quebra de verdade"
           % achados if achados else "")

    colados = 0
    for rel in _componentes.nomes("app"):
        if not rel.endswith(".py"):
            continue
        for pagina in _paginas_do_modulo(_componentes.fonte("app/" + rel)):
            for js in re.findall(r"<script>(.*?)</script>", pagina, re.S):
                for n, linha in _strings_coladas(js):
                    colados += 1
                    print("       %s, linha %d do script: %s" % (rel, n, linha))
    checar("nenhuma string JS colada em outra", colados == 0,
           "%d ocorrencia(s) — aspa que o Python engoliu (\\' vira ')"
           % colados if colados else "")


def _strings_coladas(js):
    fora = []
    for n, bruta in enumerate(js.splitlines(), 1):
        linha = bruta.split("//")[0]
        i, aberta, fim_anterior = 0, None, -1
        while i < len(linha):
            c = linha[i]
            if aberta is None:
                if c in "'\"":
                    if fim_anterior >= 0 and not linha[fim_anterior + 1:i].strip():
                        fora.append((n, bruta.strip()[:96]))
                        break
                    aberta = c
            elif c == "\\":
                i += 1
            elif c == aberta:
                aberta, fim_anterior = None, i
            i += 1
    return fora


def checar_escapes_invalidos():
    print("\n[7] Codigo: nenhum escape invalido em string nao-raw")
    achados = []
    for sub in ("app", "tools", "build"):
        pasta = os.path.join(RAIZ, sub)
        if not os.path.isdir(pasta):
            continue
        for rel in sorted(os.listdir(pasta)):
            if not rel.endswith(".py"):
                continue
            caminho = os.path.join(pasta, rel)
            with warnings.catch_warnings(record=True) as capturados:
                warnings.simplefilter("always")
                try:
                    compile(io.open(caminho, encoding="utf-8").read(), caminho, "exec")
                except SyntaxError:
                    continue
                for w in capturados:
                    if issubclass(w.category, SyntaxWarning):
                        achados.append((os.path.join(sub, rel), w.lineno,
                                        str(w.message)[:48]))
    for arq, linha, msg in achados:
        print("       %s:%s  %s" % (arq, linha, msg))
    checar("nenhum escape invalido (use \\\\s ou string raw)", not achados,
           "%d ocorrencia(s)" % len(achados) if achados else "")


def checar_escape_que_o_python_come():
    print("\n[7b] Codigo: nenhuma contrabarra solta em literal de tela")

    COME = set("nrtbfav01234567") | set(["'", '"'])

    def sem_comentario(txt):
        fora, i, n = [], 0, len(txt)
        while i < n:
            if txt.startswith("/*", i):
                j = txt.find("*/", i + 2)
                i = (j + 2) if j >= 0 else n
                continue
            if txt.startswith("//", i) and (i == 0 or txt[i - 1] != ":"):
                j = txt.find("\n", i)
                i = j if j >= 0 else n
                continue
            fora.append(txt[i])
            i += 1
        return "".join(fora)

    achados = []
    for sub in ("app",):
        pasta = os.path.join(RAIZ, sub)
        for rel in sorted(os.listdir(pasta)):
            if not rel.endswith(".py"):
                continue
            caminho = os.path.join(pasta, rel)
            fonte = io.open(caminho, encoding="utf-8").read()
            try:
                arvore = ast.parse(fonte)
            except SyntaxError:
                continue
            for no in ast.walk(arvore):
                if not isinstance(no, ast.Constant):
                    continue
                if not isinstance(no.value, str):
                    continue
                if "function " not in no.value and "<script" not in no.value \
                        and "::before" not in no.value:
                    continue
                try:
                    bruto = ast.get_source_segment(fonte, no)
                except Exception:
                    bruto = None
                if not bruto or bruto.lstrip("uUbB")[:1] in ("r", "R"):
                    continue
                bruto = sem_comentario(bruto)
                i, n = 0, len(bruto)
                while i < n - 1:
                    if bruto[i] != "\\":
                        i += 1
                        continue
                    if bruto[i + 1] == "\\":
                        i += 2
                        continue
                    if bruto[i + 1] in COME:
                        achados.append((
                            os.path.join(sub, rel),
                            no.lineno + bruto[:i].count("\n"),
                            bruto[i:i + 4].replace("\n", "<NL>")))
                    i += 2
    for arq, linha, seq in achados[:20]:
        print("       %s:%s  %s" % (arq, linha, seq))
    checar("nenhuma contrabarra solta (dobre-a, ou use o caractere)",
           not achados,
           "%d ocorrencia(s)" % len(achados) if achados else "")


def checar_ts_map():
    print("\n[9] TS_MAP: nenhum rotulo cru em dois nomes amigaveis da mesma task")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    try:
        import engine
    except Exception as e:
        checar("engine.py importa", False, "%s: %s" % (type(e).__name__, e))
        return
    dono, conflitos = {}, []
    for amigavel, taskmap in engine.TS_MAP.items():
        for task, labels in taskmap.items():
            for l in labels:
                k = (task, l)
                if k in dono:
                    conflitos.append("%s: %r em %s e %s" % (task, l, dono[k], amigavel))
                dono[k] = amigavel
    checar("nenhum rotulo disputado", not conflitos, " | ".join(conflitos[:4]))

    comp = getattr(engine, "COMPOSTOS", {})
    try:
        import radai_tasks as _rtk
        familia = _rtk.familia_da_task
    except Exception as e:
        checar("radai_tasks importa (a familia de cada task)", False,
               "%s: %s" % (type(e).__name__, e))
        familia = (lambda t: t)
    disputas = []
    for c, partes in sorted(comp.items()):
        if c not in engine.TS_MAP:
            continue
        diretas = set(familia(t) for t in engine.TS_MAP[c])
        for p in partes:
            das_partes = set(familia(t) for t in engine.TS_MAP.get(p, {}))
            comuns = sorted(diretas & das_partes)
            if comuns:
                disputas.append("%s direto e a parte %s na familia %s"
                                % (c, p, "/".join(comuns)))
                break
    checar("composto so esta no TS_MAP numa familia sem as partes dele",
           not disputas, " | ".join(disputas[:4]))
    orfas = [p for partes in comp.values() for p in partes if p not in engine.TS_MAP]
    checar("toda parte de um composto existe no TS_MAP", not orfas, ", ".join(orfas))

    lobos = ["lung_upper_lobe_right", "lung_middle_lobe_right", "lung_lower_lobe_right",
             "lung_upper_lobe_left", "lung_lower_lobe_left"]
    faltam = [l for l in lobos if l not in engine.TS_MAP]
    checar("os cinco lobos estao separados no TS_MAP", not faltam, ", ".join(faltam))
    sem_tg = [l for l in lobos if l not in engine.TG263]
    checar("e cada um com nome TG-263", not sem_tg, ", ".join(sem_tg))


def checar_runner():
    print("\n[8] Runner: cada bateria com sua propria variavel, e todas conferidas")
    caminho = os.path.join(RAIZ, "verify.cmd")
    if not os.path.isfile(caminho):
        checar("verify.cmd existe", False, caminho)
        return
    txt = io.open(caminho, encoding="utf-8", errors="replace").read()

    pares = re.findall(r'tools[\\/](\w+\.py)"(?: --rodar (\w+\.py))?[^\n]*\n\s*set\s+"(RC\d+)=', txt)
    vistos, repetidas = {}, []
    for script, rodado, var in pares:
        script = rodado or script
        if var in vistos:
            repetidas.append("%s usa %s, ja usada por %s" % (script, var, vistos[var]))
        vistos[var] = script
    checar("nenhuma variavel RC repetida", not repetidas, " | ".join(repetidas))

    atribuidas = set(re.findall(r'set\s+"(RC\d+)=', txt))
    conferidas = set(re.findall(r'if\s+not\s+"%(RC\d+)%"=="0"', txt))
    sem_conferencia = sorted(atribuidas - conferidas)
    checar("toda variavel atribuida e conferida", not sem_conferencia,
           ", ".join(sem_conferencia))

    tools = set(f for f in _componentes.nomes("tools", RAIZ)
                if f.startswith("test_") and f.endswith(".py"))
    fora = sorted(tools - set(vistos.values()))
    checar("toda bateria de tools/ esta no runner", not fora, ", ".join(fora))

    quebrados = [l.strip()[:70] for l in txt.splitlines()
                 if "tools" in l and "\t" in l]
    checar("nenhum caminho com TAB no lugar de \\t", not quebrados,
           " | ".join(quebrados))


def checar_classes_css():
    print("\n[11] CSS: nenhuma classe generica definida duas vezes")
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        txt = ler(os.path.join("app", nome))
        if "<style>" not in txt:
            continue
        repetidas = []
        for css in re.findall(r"<style>(.*?)</style>", txt, re.S):
            css = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css)
            vistas = set()
            for bruto in re.findall(r"(?m)^([^{@\n][^{]*)\{", css):
                for sel in bruto.split(","):
                    m = re.match(r"^\.([\w-]+)$", sel.strip())
                    if not m:
                        continue
                    if m.group(1) in vistas:
                        repetidas.append(m.group(1))
                    vistas.add(m.group(1))
        checar("%s: sem classe repetida" % nome, not repetidas,
               ", ".join(sorted(set(repetidas))))


def checar_fim_de_linha():
    print("\n[10] Fim de linha: .cmd, .bat e .ps1 em CRLF no disco")
    ruins, dobrados = [], []
    for raiz, dirs, arquivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs
                   if d not in ("_montagem", ".venv", ".git", "__pycache__",
                                "arquivo") + FORA]
        for nome in arquivos:
            if os.path.splitext(nome)[1].lower() not in (".cmd", ".bat", ".ps1"):
                continue
            fp = os.path.join(raiz, nome)
            try:
                b = open(fp, "rb").read()
            except Exception:
                continue
            if b.count(b"\n") != b.count(b"\r\n"):
                ruins.append(os.path.relpath(fp, RAIZ))
            if b.count(b"\r\r\n"):
                dobrados.append("%s (%d linha(s))"
                                % (os.path.relpath(fp, RAIZ),
                                   b.count(b"\r\r\n")))
    checar("nenhum lote com LF solto", not ruins, ", ".join(ruins))
    checar("e nenhum com CR duplo (\\r\\r\\n)", not dobrados,
           ", ".join(dobrados[:5]))


def checar_testes_mortos():
    print("\n[12] Nenhum teste escrito e nunca chamado")
    mortos = []
    for f in _componentes.nomes("tools", RAIZ):
        if not (f.startswith("test_") and f.endswith(".py")):
            continue
        txt = io.open(_componentes.fonte("tools/" + f, RAIZ), encoding="utf-8",
                      errors="replace").read()
        for nome in re.findall(r"(?m)^def (teste_\w+)", txt):
            if len(re.findall(r"\b" + nome + r"\b", txt)) < 2:
                mortos.append("%s: %s" % (f, nome))
    checar("todo teste definido e chamado pela propria bateria", not mortos,
           " | ".join(mortos[:8]))


def checar_lateralidade_e_resolucao():
    print("\n[13] Nenhum motor espelha na inferencia nem roda reduzido")
    arquivos = []
    for sub in ("app", "tools", "build"):
        d = os.path.join(RAIZ, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith((".py", ".hta")):
                arquivos.append((os.path.join(sub, f), os.path.join(d, f)))

    espelham, reduzem = [], []
    for rel, caminho in arquivos:
        bruto = io.open(caminho, encoding="utf-8", errors="replace").read()
        if "check_project" in rel:
            continue
        txt = so_codigo(bruto) if rel.endswith(".py") else bruto
        for m in re.finditer(r"(?:use_mirroring|do_mirroring)\s*=\s*True", txt):
            espelham.append("%s: %s" % (rel, m.group(0)))
        for m in re.finditer(r"mirror_axes\s*=\s*\(\s*\d", txt):
            espelham.append("%s: %s" % (rel, m.group(0)))
        for m in re.finditer(r"nnUNetPredictor\s*\(", txt):
            trecho = txt[m.end():m.end() + 900]
            fecha = trecho.find(")")
            args = trecho[:fecha if fecha > 0 else 900]
            if not re.search(r"use_mirroring\s*=\s*False", args):
                espelham.append(
                    "%s: nnUNetPredictor sem `use_mirroring=False` literal "
                    "(o padrao dele e True)" % rel)
        for m in re.finditer(r"nnUNetv2_predict", txt):
            if "--disable_tta" not in txt:
                espelham.append("%s: nnUNetv2_predict sem --disable_tta" % rel)
                break
        for linha in txt.splitlines():
            if ("--fast" not in linha) or ("not in cmd" in linha):
                continue
            if linha.strip().startswith("#"):
                continue
            if "download_weights" in txt and re.search(
                    r"dl\s*\(|download_weights", linha):
                continue
            reduzem.append("%s: %s" % (rel, linha.strip()[:64]))
        for m in re.finditer(r"\b(fast|fastest)\s*=\s*True", txt):
            reduzem.append("%s: %s (a API de Python nao tem hifen)"
                           % (rel, m.group(0)))

    checar("nenhum motor liga espelhamento na inferencia", not espelham,
           " | ".join(sorted(set(espelham))[:6]))
    checar("nenhuma chamada usa --fast ou --fastest", not reduzem,
           " | ".join(reduzem[:6]))

    try:
        sys.path.insert(0, os.path.join(RAIZ, "app"))
        import radai_tasks as _rt
        REDUZIDOS = {297: "total 3 mm", 298: "total 6 mm", 732: "total_mr 3 mm",
                     733: "total_mr 6 mm", 300: "body 6 mm"}
        RECORTE = {int(getattr(_rt, "DATASET_RECORTE", 298)), 300}
        maus = []
        for d in _rt.CATALOGO:
            for n in d.get("datasets", ()):
                if n in REDUZIDOS and n not in RECORTE:
                    maus.append("%s declara Dataset%d (%s)"
                                % (d["task"], n, REDUZIDOS[n]))
        checar("nenhuma task declara peso de resolucao reduzida",
               not maus, " | ".join(maus[:4]))
        for _b, _esp in (("total_v3", [831, 832, 833, 834, 835]),
                         ("total_v2", [291, 292, 293, 294, 295])):
            checar("e a `%s` continua com os cinco de 1,5 mm" % _b,
                   sorted(_rt.POR_NOME.get(_b, {}).get("datasets") or []) == _esp,
                   str(_rt.POR_NOME.get(_b, {}).get("datasets")))
        checar("  e `total` nao e mais nome de catalogo",
               "total" not in _rt.POR_NOME,
               "ela e apelido de `total_v3`, traduzido na leitura do config")
    except Exception as _exc:
        checar("o catalogo de pesos pode ser lido", False, str(_exc)[:120])
    faltando = []
    for rel, caminho in arquivos:
        if "check_project" in rel:
            continue
        txt = io.open(caminho, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"`(tools[\\/][\w_]+\.py)`", txt):
            alvo = os.path.join(RAIZ, m.group(1).replace("\\", os.sep))
            if not os.path.isfile(alvo):
                faltando.append("%s cita %s, que nao existe" % (rel, m.group(1)))
    checar("nenhum comentario cita bateria inexistente", not faltando,
           " | ".join(sorted(set(faltando))[:5]))


def _chamadas_da_regra_a(src):
    fora = {}
    try:
        arv = ast.parse(src)
    except SyntaxError:
        return fora
    for no in arv.body:
        if not isinstance(no, ast.FunctionDef):
            continue
        achou = set()
        for c in ast.walk(no):
            if not isinstance(c, ast.Call) or not c.args:
                continue
            alvo = (getattr(c.func, "attr", None)
                    or getattr(c.func, "id", None))
            if alvo != "conferir_regra_a":
                continue
            a0 = c.args[0]
            nome = (getattr(a0, "id", None) or getattr(a0, "attr", None)
                    or (a0.value if isinstance(a0, ast.Constant) else None))
            if nome:
                achou.add(str(nome))
        if achou:
            fora[no.name] = achou
    return fora


def _corpo_de_funcao_js(pag, nome):
    i = (pag or u"").find(u"function %s(" % nome)
    if i < 0:
        return u""
    j = pag.find(NL + u"}", i)
    return pag[i:j + 2] if j > 0 else pag[i:]


def _sem_comentario_js(txt):
    txt = re.sub(r"/\*.*?\*/", u"", txt or u"", flags=re.S)
    return NL.join(l for l in txt.split(NL) if not l.lstrip().startswith("//"))


def _usos_da_chave_topo(src):
    try:
        arv = ast.parse(src)
    except SyntaxError:
        return [u"(o fonte nao compila)"]
    fora = []
    for no in ast.walk(arv):
        if isinstance(no, ast.Subscript) and isinstance(no.ctx, ast.Store):
            sl = no.slice
            if isinstance(sl, ast.Constant) and sl.value == "topo":
                fora.append(u"linha %d" % no.lineno)
        if (isinstance(no, ast.Call) and getattr(no.func, "attr", None) == "get"
                and no.args and isinstance(no.args[0], ast.Constant)
                and no.args[0].value == "topo"):
            fora.append(u"linha %d (.get)" % no.lineno)
    return fora


def checar_padrao_de_fabrica():
    print("\n[14b] O padrao de fabrica e um so, e nao procura achado")
    eng = _importar_do_app("engine")
    tk = _importar_do_app("radai_tasks")
    md = _importar_do_app("radai_modes")
    if eng is None or tk is None or md is None:
        checar("engine, radai_tasks e radai_modes importam",
               False, "sem os tres nao da para comparar as fontes")
        return

    achado = set(getattr(eng, "TASKS_DE_ACHADO", ()) or ())
    padrao_cat = list(getattr(tk, "PADRAO", []) or [])

    # GUARDA: o vigia nao le task do config. O DEFAULT_CFG nao declara TASKS=,
    # o DEFAULTS nao tem a chave, ela esta em CHAVES_OBSOLETAS, e a lista do
    # vigia nasce da base fixa (`base_do_vigia`).
    vig = io.open(_componentes.fonte(no_app("radai_watcher.py")),
                  encoding="utf-8", errors="replace").read()

    def _vigia_sem_tasks(fonte):
        sem_linha = not re.search(r"^TASKS=", fonte, re.M)
        sem_dict = not re.search(r'^\s+"TASKS"\s*:\s*"', fonte, re.M)
        obs = re.search(r"(?ms)^CHAVES_OBSOLETAS\s*=\s*\{(.*?)^\}", fonte)
        obsoleta = bool(obs and re.search(r'"TASKS"\s*:', obs.group(1)))
        base_fixa = "TASKS = [base_do_vigia()]" in fonte
        return sem_linha and sem_dict and obsoleta and base_fixa
    checar("o vigia nao le TASKS do config (DEFAULT_CFG, DEFAULTS, "
           "CHAVES_OBSOLETAS e a base fixa)", _vigia_sem_tasks(vig))
    checar("  (isca) um TASKS= de volta no DEFAULT_CFG reprova",
           not _vigia_sem_tasks(vig.replace("ROOT=\n", "ROOT=\nTASKS=total_v3\n", 1)
                                 if "ROOT=\n" in vig else
                                 vig.replace("ROOT=\r\n", "ROOT=\r\nTASKS=total_v3\r\n", 1)))
    checar("  (isca) a lista do config de volta no aplicar_cfg reprova",
           not _vigia_sem_tasks(vig.replace("TASKS = [base_do_vigia()]",
                                            "TASKS = list(CFG['TASKS'])")))
    do_cfg = [md.base_de("CT")]

    try:
        do_modo = list(md.tasks_da_topografia(
            (), "CT", permitidas=eng.TASKS_PERMITIDAS, achados=achado))
    except Exception as e:
        checar("radai_modes monta a tabela por topografia sem regiao", False,
               str(e))
        return

    checar("as tres fontes do padrao concordam",
           padrao_cat == do_cfg == do_modo,
           "catalogo=%r cfg=%r tabela=%r" % (padrao_cat, do_cfg, do_modo))

    for rotulo, lista in (("radai_tasks.PADRAO", padrao_cat),
                          ("a base do vigia", do_cfg),
                          ("a tabela por topografia (sem regiao)", do_modo)):
        intrusas = sorted(set(lista) & achado)
        checar("%s nao traz task de achado" % rotulo, not intrusas,
               ", ".join(intrusas))
    # GUARDA: os oculomotores so rodam por ato declarado (PERSONALIZADO).
    _ocu = [o for o, tab in (("topografia", md.TASKS_POR_TOPOGRAFIA),
                             ("topografia MR", md.TASKS_POR_TOPOGRAFIA_MR),
                             ("ligadas de fabrica",
                              md.LIGADAS_DE_FABRICA_NO_PERSO))
            if any("oculomotor_muscles" in tuple(v) for v in tab.values())]
    _ocu += [p.get("cod") for p in md.PROTOCOLOS
             if "oculomotor_muscles" in tuple(p.get("tasks") or ())]
    checar("oculomotor_muscles fora do AUTO, do FAST, dos protocolos e das "
           "chaves ligadas de fabrica", not _ocu, ", ".join(map(str, _ocu)))

    _topos = tuple(getattr(md, "TOPOGRAFIAS", ()) or ())
    checar("radai_modes declara as topografias da tabela", bool(_topos))
    for _mod in ("CT", "MR"):
        for _t in _topos + (_topos,):
            _reg = _t if isinstance(_t, tuple) else (_t,)
            try:
                _saiu = md.tasks_da_topografia(
                    _reg, _mod, permitidas=eng.TASKS_PERMITIDAS,
                    achados=achado)
                _intr = sorted(set(_saiu) & achado)
                checar("  a tabela (%s, %s) nao monta achado"
                       % (_mod, "todas" if isinstance(_t, tuple) else _t),
                       not _intr, ", ".join(_intr))
            except Exception as _e:
                checar("  a tabela (%s, %s) monta"
                       % (_mod, "todas" if isinstance(_t, tuple) else _t),
                       False, "%s: %s" % (type(_e).__name__, _e))

    checar("radai_modes.conferir_regra_a existe",
           hasattr(md, "conferir_regra_a"))
    for _orig, _deve in ((getattr(md, "ANATOMIA", "anatomia"), True),
                         ("pre_marcacao", True),
                         (getattr(md, "PADRAO", "padrao"), True),
                         ("origem_que_ninguem_conhece", True),
                         (getattr(md, "MARCADO", "marcado"), False),
                         ("config", True)):
        try:
            md.conferir_regra_a(_orig, ("total_v3", "lung_nodules"), achado)
            _levantou, _nome = False, ""
        except Exception as e:
            _levantou, _nome = True, e.__class__.__name__
        checar("  a origem `%s` %s levantar com achado"
               % (_orig, "DEVE" if _deve else "NAO deve"),
               _levantou == _deve
               and (not _deve or _nome == "AchadoSemPedido"),
               "levantou=%s (%s)" % (_levantou, _nome))

    checar("  a REGRA B tem dois atos: a chave da task (MARCADO) e o estudo 3D "
           "(ESTUDO); o config nao e ato",
           tuple(getattr(md, "ATOS_DECLARADOS", ()))
           == (md.MARCADO, getattr(md, "ESTUDO", None))
           and not hasattr(md, "CONFIG"),
           str(getattr(md, "ATOS_DECLARADOS", None)))
    _tab = getattr(md, "TASKS_POR_TOPOGRAFIA", None)
    if isinstance(_tab, dict):
        _velha = _tab.get("torax")
        try:
            _tab["torax"] = tuple(_velha or ()) + ("lung_nodules",)
            try:
                md.tasks_da_topografia(("torax",), "CT",
                                       permitidas=eng.TASKS_PERMITIDAS,
                                       achados=achado)
                checar("  (isca) achado forjado na tabela do torax PARA a "
                       "lista do vigia", False, "devolveu a lista")
            except Exception as e:
                checar("  (isca) achado forjado na tabela do torax PARA a "
                       "lista do vigia",
                       e.__class__.__name__ == "AchadoSemPedido",
                       e.__class__.__name__)
        finally:
            _tab["torax"] = _velha
    _src_md = io.open(_componentes.fonte(no_app("radai_modes.py")),
                      encoding="utf-8", errors="replace").read()
    _anc = _chamadas_da_regra_a(_src_md)
    checar("  `tasks_da_topografia` chama a trava com a origem ANATOMIA",
           "ANATOMIA" in _anc.get("tasks_da_topografia", ()),
           str(_anc.get("tasks_da_topografia")))
    checar("  e a API dos estudos da v8.2 saiu de `radai_modes`",
           not [n for n in ("ESTUDOS", "EST_POR_COD", "estudos_de",
                            "conferir_estudos", "pre_marcadas",
                            "tasks_da_escolha", "normalizar_estudos",
                            "PRE_MARCACAO") if hasattr(md, n)],
           ", ".join(n for n in ("ESTUDOS", "EST_POR_COD", "estudos_de",
                                 "conferir_estudos", "pre_marcadas",
                                 "tasks_da_escolha", "normalizar_estudos",
                                 "PRE_MARCACAO") if hasattr(md, n)))
    _sem = _src_md.replace("conferir_regra_a(ANATOMIA, fora, achados)",
                           "pass")
    checar("  (isca) sem a chamada em `tasks_da_topografia`, a ancora acusa",
           "ANATOMIA" not in _chamadas_da_regra_a(_sem).get(
               "tasks_da_topografia", ()),
           "a leitura por ast nao distingue a funcao?")

    for _orig in (getattr(md, "PROTOCOLO", None), getattr(md, "FAST", None)):
        try:
            md.conferir_regra_a(_orig, ("total_v3", "lung_nodules"), achado)
            _lev, _nome = False, ""
        except Exception as e:
            _lev, _nome = True, e.__class__.__name__
        checar("  a origem `%s` DEVE levantar com achado" % _orig,
               _orig is not None and _lev and _nome == "AchadoSemPedido",
               "levantou=%s (%s)" % (_lev, _nome))
    checar("  `tasks_do_fast` chama a trava com a origem FAST",
           "FAST" in _anc.get("tasks_do_fast", ()),
           str(_anc.get("tasks_do_fast")))
    for _fn in ("tasks_dos_protocolos", "tasks_do_personalizado",
                "conferir_protocolos"):
        checar("  `%s` chama a trava com a origem PROTOCOLO" % _fn,
               "PROTOCOLO" in _anc.get(_fn, ()), str(_anc.get(_fn)))
    try:
        md.conferir_protocolos(getattr(tk, "CATALOGO", None), achado)
        checar("  os protocolos do PERSONALIZADO conferem (catalogo, "
               "modalidade, motor, REGRA A)", True)
    except Exception as e:
        checar("  os protocolos do PERSONALIZADO conferem (catalogo, "
               "modalidade, motor, REGRA A)", False,
               "%s: %s" % (type(e).__name__, str(e)[:200]))
    for _mod in ("CT", "MR"):
        for _t in _topos + (_topos,):
            _reg = _t if isinstance(_t, tuple) else (_t,)
            try:
                _saiu = md.tasks_do_fast(_reg, 900.0, _mod,
                                         permitidas=eng.TASKS_PERMITIDAS,
                                         achados=achado)
                checar("  o FAST (%s, %s) nao roda achado"
                       % (_mod, "todas" if isinstance(_t, tuple) else _t),
                       not (set(_saiu) & achado), str(_saiu))
            except Exception as _e:
                checar("  o FAST (%s, %s) monta"
                       % (_mod, "todas" if isinstance(_t, tuple) else _t),
                       False, "%s: %s" % (type(_e).__name__, _e))
    _p = (getattr(md, "PROT_POR_COD", {}) or {}).get("torax_mama")
    if isinstance(_p, dict):
        _vt = _p.get("tasks")
        try:
            _p["tasks"] = tuple(_vt or ()) + ("lung_nodules",)
            try:
                md.tasks_do_personalizado(["torax_mama"], {}, "CT",
                                          achados=achado)
                checar("  (isca) achado forjado no protocolo PARA a lista",
                       False, "devolveu a lista")
            except Exception as e:
                checar("  (isca) achado forjado no protocolo PARA a lista",
                       e.__class__.__name__ == "AchadoSemPedido",
                       e.__class__.__name__)
        finally:
            _p["tasks"] = _vt
    else:
        checar("  radai_modes declara o protocolo `torax_mama`", False)
    _tf = getattr(md, "TASKS_DO_FAST", None)
    if isinstance(_tf, dict):
        _vf = _tf.get("torax")
        try:
            _tf["torax"] = tuple(_vf or ()) + ("lung_nodules",)
            try:
                md.tasks_do_fast(("torax",), None, "CT", achados=achado)
                checar("  (isca) achado forjado no FAST PARA a lista", False,
                       "devolveu a lista")
            except Exception as e:
                checar("  (isca) achado forjado no FAST PARA a lista",
                       e.__class__.__name__ == "AchadoSemPedido",
                       e.__class__.__name__)
        finally:
            _tf["torax"] = _vf
    else:
        checar("  radai_modes declara `TASKS_DO_FAST`", False)

    _lf = getattr(md, "LIGADAS_DE_FABRICA_NO_PERSO", None)
    if isinstance(_lf, dict):
        for _mod in ("CT", "MR"):
            _l = tuple(md.ligadas_de_fabrica(_mod))
            checar("  a chave que nasce ligada no PERSONALIZADO (%s) nao e "
                   "achado" % _mod, not (set(_l) & set(achado)), str(_l))
        try:
            md.LIGADAS_DE_FABRICA_NO_PERSO = dict(
                _lf, CT=tuple(_lf.get("CT", ())) + ("lung_nodules",))
            try:
                md.tasks_do_personalizado([], {}, "CT", achados=achado)
                checar("  (isca) achado forjado na chave que nasce ligada "
                       "PARA a lista", False, "devolveu a lista")
            except Exception as e:
                checar("  (isca) achado forjado na chave que nasce ligada "
                       "PARA a lista",
                       e.__class__.__name__ == "AchadoSemPedido",
                       e.__class__.__name__)
        finally:
            md.LIGADAS_DE_FABRICA_NO_PERSO = _lf
    else:
        checar("  radai_modes declara `LIGADAS_DE_FABRICA_NO_PERSO`", False)


    _rs = _importar_do_app("radai_sets")
    if _rs is not None and isinstance(_tab, dict):
        _full = set(getattr(_rs, "TASKS_DO_FULL", ()) or ())
        _fora = sorted(set(t for v in _tab.values() for t in v) - _full)
        checar("toda task da tabela por topografia alimenta o FULL",
               not _fora, ", ".join(_fora))
        _isca = set(t for v in _tab.values() for t in v) | {"hip_implant"}
        checar("  (isca) uma task de plugin na tabela seria acusada",
               bool(_isca - _full))
    else:
        checar("radai_sets e a tabela por topografia existem", False)

    no_catalogo = set(d.get("task") for d in (getattr(tk, "CATALOGO", []) or []))
    faltam = sorted(t for t in getattr(eng, "TASKS_PERMITIDAS", {})
                    if t not in no_catalogo)
    checar("toda task PERMITIDA tem entrada no catalogo da tela",
           not faltam, ", ".join(faltam))
    _prot = dict((p["cod"], p) for p in getattr(md, "PROTOCOLOS", ()))
    _tm = _prot.get("torax_mama") or {}
    checar("o protocolo «Torax / Mama» existe e arrasta a cavidade, a mama e "
           "o derrame (a `abdominal_muscles` saiu com a Breast_OAR)",
           tuple(_tm.get("tasks") or ()) == ("trunk_cavities", "breasts",
                                             "pleural_pericard_effusion"),
           str(_tm.get("tasks")))
    _lote = _importar_do_app("radai_batch")
    try:
        _opc_t = _lote.opcoes_da_tela("CT")
        _oferta = set(t["task"] for t in (_opc_t.get("tasks") or ()))
    except Exception as _e:
        _opc_t, _oferta = {}, set()
        checar("radai_batch.opcoes_da_tela responde", False,
               "%s: %s" % (type(_e).__name__, _e))
    for _t in ("lung_vessels_LEGACY", "lung_vessels", "lung_nodules",
               "pleural_pericard_effusion"):
        checar("  e a tela continua OFERECENDO `%s` (task avulsa)" % _t,
               _t in _oferta, ", ".join(sorted(_oferta)))
    _ordem_ct = [p["cod"] for p in md.protocolos_de("CT")]
    checar("os protocolos da TC estao na ordem da spec 1.2",
           _ordem_ct == ["cranio", "cabeca_pescoco", "torax_mama", "sbrt",
                         "abdome", "pelve", "coluna"], str(_ordem_ct))
    _ordem_mr = [p["cod"] for p in md.protocolos_de("MR")]
    checar("  e os da RM sao Coluna e Abdomen",
           _ordem_mr == ["coluna_rm", "abdome_rm"], str(_ordem_mr))
    _cmp = [c["cod"] for c in (_opc_t.get("comparacao") or ())]
    checar("  a Comparacao de modelos traz o TS cru, o NV-Segment-CT, o CADS "
           "e o MOOSE", _cmp == ["ts", "nv", "cads", "mse"], str(_cmp))
    _cpe = _prot.get("cabeca_pescoco") or {}
    checar("  o Cabeca e Pescoco avancado liga os niveis cervicais como motor",
           "hnlnl" in tuple(_cpe.get("motores") or ()),
           str(_cpe.get("motores")))
    if _lote is not None and isinstance(_tm, dict):
        _vt = _tm.get("tasks")
        try:
            _tm["tasks"] = tuple(_vt or ()) + ("lung_nodules",)
            try:
                _lote.opcoes_da_tela("CT")
                checar("  (isca) achado forjado num protocolo PARA a tela",
                       False, "a tela montou com o protocolo arrastando achado")
            except Exception as e:
                checar("  (isca) achado forjado num protocolo PARA a tela",
                       e.__class__.__name__ == "AchadoSemPedido",
                       e.__class__.__name__)
        finally:
            _tm["tasks"] = _vt
    _pag = getattr(_lote, "PAGINA", u"") if _lote is not None else u""
    _corpo_pm = _corpo_de_funcao_js(_pag, "_arrastavel")
    _corpo_tl = _corpo_de_funcao_js(_pag, "tasksLigadas")

    def _arrasto_seguro(corpo):
        return "!t.achado" in corpo and "t.permitida !== false" in corpo

    checar("  o JS nao arrasta task de achado por protocolo (`_arrastavel`)",
           _arrasto_seguro(_corpo_pm), _corpo_pm[:120] or "(funcao ausente)")
    checar("  e as chaves que o protocolo liga passam por ele (`tasksLigadas`)",
           _corpo_tl.count("_arrastavel(") >= 2,
           _corpo_tl[:160] or "(funcao ausente)")
    checar("  (isca) sem o `!t.achado`, a checagem acusa",
           not _arrasto_seguro(_corpo_pm.replace("!t.achado", "true")),
           "a regra passaria com a task de achado arrastavel")
    _js = _sem_comentario_js(_pag)
    checar("  a tela do «Rodar agora» nao tem «selecionar tudo»",
           "selecionar tudo" not in _js.lower()
           and "marcar tudo" not in _js.lower(),
           "«não incluir esse botão Selecionar tudo» -- Q19")
    _src_lote = io.open(_componentes.fonte(no_app("radai_batch.py")),
                        encoding="utf-8", errors="replace").read()
    _topo = _usos_da_chave_topo(_src_lote)
    checar("  e a varredura nao cola mais a sugestao de topografia por texto",
           not _topo, ", ".join(_topo))
    checar("  (isca) `x[\"topo\"] = cod` seria acusado",
           bool(_usos_da_chave_topo(u"def f(x, cod):\n    x['topo'] = cod\n")))
    checar("  `torax_pedido` le o `cod` do protocolo Torax / Mama da tabela",
           getattr(_lote, "PROTOCOLO_TORAX", None) in _prot,
           str(getattr(_lote, "PROTOCOLO_TORAX", None)))

    try:
        _opc = _importar_do_app("radai_batch").opcoes_da_tela("CT")
        _itens = [i for i in (_opc.get("tasks") or ())
                  if not i.get("motor")]
        _graus = set(i.get("contraste") or "" for i in _itens)
        checar("a tag de contraste chega a tela COM VALOR",
               len(_graus - set([""])) >= 2, str(sorted(_graus)))
        _ll = [i for i in _itens if i["task"] == "liver_lesions"]
        checar("  e a lesao hepatica chega como `exige`",
               bool(_ll) and _ll[0].get("contraste") == "exige",
               str(_ll[0].get("contraste")) if _ll else "(ausente)")
        checar("  e o numero do dataset chega em toda task",
               all(i.get("datasets") for i in _itens),
               str([i["task"] for i in _itens if not i.get("datasets")]))
        checar("  e a velocidade chega em toda task (fast/regular/slow/"
               "ultra-slow)",
               all(i.get("velocidade") in ("fast", "regular", "slow",
                                           "ultra-slow") for i in _itens),
               str([i["task"] for i in _itens
                    if i.get("velocidade") not in ("fast", "regular", "slow",
                                                   "ultra-slow")]))
        _bi = _opc.get("base_item") or {}
        checar("  e a base chega com a etiqueta dela (a regua: slow)",
               _bi.get("velocidade") == "slow", str(_bi.get("velocidade")))
    except Exception as _e:
        checar("as tags de task chegam a tela", False, str(_e))
    _tab_ct = getattr(md, "TASKS_POR_TOPOGRAFIA", {}) or {}
    padrao_torax = _tab_ct.get("torax", ())
    checar("`trunk_cavities` esta na tabela do torax",
           "trunk_cavities" in padrao_torax, str(padrao_torax))
    checar("  e `breasts` tambem (as mamas do TotalSegmentator)",
           "breasts" in padrao_torax, str(padrao_torax))
    checar("  e a `abdominal_muscles` NAO (saiu do AUTO com a Breast_OAR)",
           "abdominal_muscles" not in padrao_torax, str(padrao_torax))
    checar("  e `trunk_cavities` esta na tabela do abdome",
           "trunk_cavities" in _tab_ct.get("abdome", ()),
           str(_tab_ct.get("abdome")))
    checar("  e `trunk_cavities` esta na tabela da pelve (a Bag_Bowel na "
           "pelve pura)", tuple(_tab_ct.get("pelve", ())) == ("trunk_cavities",),
           str(_tab_ct.get("pelve")))
    checar("  o piso do coracao fora do torax e o do motor",
           float(getattr(md, "CORACAO_MINIMO_CM3", -1))
           == float(getattr(eng, "VOLUME_MINIMO_CORACAO_CM3", -2)),
           "%r x %r" % (getattr(md, "CORACAO_MINIMO_CM3", None),
                        getattr(eng, "VOLUME_MINIMO_CORACAO_CM3", None)))
    try:
        _com = md.tasks_da_topografia(("abdome",), "CT",
                                      permitidas=eng.TASKS_PERMITIDAS,
                                      achados=achado, coracao_cm3=150.0)
        _sem_c = md.tasks_da_topografia(("cabeca_pescoco",), "CT",
                                        permitidas=eng.TASKS_PERMITIDAS,
                                        achados=achado, coracao_cm3=40.0)
        checar("  coracao de 150 cm3 sem torax traz `trunk_cavities`; de 40 "
               "numa cabeca, nao",
               "trunk_cavities" in _com and "trunk_cavities" not in _sem_c,
               "%s | %s" % (_com, _sem_c))
    except Exception as _e:
        checar("  a tabela com o coracao monta", False, str(_e))

    _cods = set(_prot)
    for _t in ("oculomotor_muscles", "teeth"):
        checar("a tela oferece `%s` como task avulsa" % _t, _t in _oferta,
               "sem ela a promessa de «sob demanda» nao tem onde ser exercida")
        _arrastam = sorted(c for c, p in _prot.items()
                           if _t in (p.get("tasks") or ()))
        checar("  e nenhum protocolo arrasta `%s`" % _t, not _arrastam,
               ", ".join(_arrastam))
    checar("  e nao sobrou protocolo separado de dentes nem de orbita",
           "dentes" not in _cods and "orbita" not in _cods,
           ", ".join(sorted(_cods)))
    try:
        _sem_uma = md.tasks_do_personalizado(
            ["torax_mama"], {"breasts": 0}, "CT",
            permitidas=eng.TASKS_PERMITIDAS, achados=achado)
        checar("  o protocolo arrasta, e a chave da task desliga",
               "breasts" not in _sem_uma and "trunk_cavities" in _sem_uma,
               str(_sem_uma))
    except Exception as _e:
        checar("  o protocolo arrasta, e a chave da task desliga", False,
               "%s: %s" % (type(_e).__name__, _e))
    padrao_cp = _tab_ct.get("cabeca_pescoco", ())
    for _t in ("oculomotor_muscles", "teeth"):
        checar("  e `%s` NAO esta na tabela de cabeca e pescoco" % _t,
               _t not in padrao_cp and _t not in _tab_ct.get("cranio", ()),
               "o modelo pede corte fino e a rotina e de 3 a 5 mm; e ele "
               "nao alimenta o FULL")
    for _t in ("craniofacial_structures", "head_glands_cavities",
               "headneck_muscles", "headneck_bones_vessels", "head_muscles"):
        checar("  `%s` continua na tabela da regiao" % _t, _t in padrao_cp,
               str(padrao_cp))

    checar("`hip_implant` NAO esta na tabela por topografia",
           not any("hip_implant" in v for v in _tab_ct.values()),
           str(dict((k, v) for k, v in _tab_ct.items() if "hip_implant" in v)))
    checar("  e ela tem caixa como task avulsa, fora do protocolo Pelve",
           "hip_implant" in _oferta and "hip_implant" not in (
               (_prot.get("pelve") or {}).get("tasks") or ()),
           str((_prot.get("pelve") or {}).get("tasks")))
    checar("  e o vigia numa pelve NAO a roda",
           "hip_implant" not in md.tasks_da_topografia(
               ("pelve",), "CT", permitidas=eng.TASKS_PERMITIDAS,
               achados=achado),
           "inferencia inteira para um plugin que ninguem pediu")
    com_chave = sorted(d["task"] for d in (getattr(tk, "CATALOGO", []) or [])
                       if d.get("comercial"))
    checar("nenhuma task do catalogo exige chave de licenca",
           not com_chave, ", ".join(com_chave))
    _achado = set(getattr(eng, "TASKS_DE_ACHADO", ()) or ()) if eng else set()
    so_com_contraste = sorted(
        t for t, v in (getattr(tk, "CONTRASTE_TASK", {}) or {}).items()
        if v == "exige" and t in no_catalogo and t not in _achado)
    checar("nenhuma task de ANATOMIA do catalogo SO funciona com contraste",
           not so_com_contraste, ", ".join(so_com_contraste))
    _anatomia_disfarcada = sorted(
        t for t in _achado
        if (getattr(tk, "CONTRASTE_TASK", {}) or {}).get(t) == "exige"
        and t in no_catalogo
        and not any(p in t for p in ("lesion", "nodule", "aneurysm",
                                     "effusion", "bleed")))
    checar("  e a isencao nao virou porta para anatomia",
           not _anatomia_disfarcada, ", ".join(_anatomia_disfarcada))
    pnl = io.open(_componentes.fonte(no_app("radai_panel.py")),
                  encoding="utf-8", errors="replace").read()
    checar("a tela de configuracoes nao oferece caminho de chave",
           "pedirLicenca(" not in so_codigo(pnl)
           if "so_codigo" in globals() else "function pedirLicenca" not in pnl)
    checar("e a rota /api/tasks/licenca saiu",
           '"/api/tasks/licenca"' not in pnl)


def checar_contratos_de_motor():
    print("\n[14e] Os tres contratos de um motor concordam")
    vi = _importar_do_app("radai_models")
    md = _importar_do_app("radai_modes")
    st = _importar_do_app("radai_sets")
    if vi is None or md is None or st is None:
        checar("radai_models, radai_modes e radai_sets importam", False)
        return

    modelos = dict(getattr(vi, "MODELOS", {}) or {})
    checar("o registro de modelos nao esta vazio", bool(modelos),
           "%d" % len(modelos))

    for ident, m in sorted(modelos.items()):
        for campo in ("nome", "motor", "licenca", "uso_permitido"):
            checar("`%s` declara `%s`" % (ident, campo), bool(m.get(campo)))
        ult = str(m.get("licenca") or u"").split(u"·")[-1]
        checar("`%s` declara a licenca dos PESOS" % ident,
               u"peso" in ult.lower(),
               "o preparador registra a ULTIMA metade da licenca; ela tem de "
               "nomear o peso, com separador ou sem ele")
        if not m.get("embutido"):
            checar("`%s` tem rota de download" % ident,
                   bool(m.get("repo") or m.get("url_direta")),
                   "sem `repo` nem `url_direta`, `baixar()` nao tem de onde")

    tamanhos = set()
    for m in modelos.values():
        for _n, t in (m.get("volumes") or ()):
            if t:
                tamanhos.add(int(t))
    registro = os.path.basename(getattr(vi, "__file__", "") or "")
    outros = []
    for pasta in ("app", "tools", "build"):
        d = os.path.join(RAIZ, pasta)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if not n.endswith(".py") or n == registro:
                continue
            txt = io.open(os.path.join(d, n), encoding="utf-8",
                          errors="replace").read()
            for t in tamanhos:
                if str(t) in txt.replace("_", ""):
                    outros.append("%s/%s (%d)" % (pasta, n, t))
    checar("o tamanho de origem dos volumes so existe no registro",
           not outros, ", ".join(outros) or
           "segunda copia do numero que decide se o download veio inteiro")

    prep = os.path.join(RAIZ, "build", "configurar_ambiente.py")
    if os.path.isfile(prep):
        txt = io.open(prep, encoding="utf-8", errors="replace").read()
        m = re.search(r"^TASKS\s*=\s*(.+)$", txt, re.M)
        checar("o preparador declara TASKS", m is not None)
        if m:
            checar("e ela e DERIVADA do catalogo, nao escrita a mao",
                   "(" not in m.group(1).split("#")[0].strip()[:1]
                   and "_tasks_do_catalogo" in m.group(1),
                   m.group(1).strip()[:70])
        ta = _importar_do_app("radai_tasks")
        if ta is not None:
            reservas = set(getattr(ta, "RESERVAS", frozenset()))
            no_catalogo = set(d["task"] for d in getattr(ta, "CATALOGO", ())
                              if d.get("datasets"))
            oferecidas = no_catalogo - reservas
            try:
                sys.path.insert(0, os.path.join(RAIZ, "build"))
                import configurar_ambiente as _ca
                trazidas = set(getattr(_ca, "TASKS", ()))
            except Exception as e:
                trazidas, oferecidas = set(), set()
                checar("o preparador importa", False, "%s" % e)
            sem_peso = sorted(oferecidas - trazidas)
            checar("toda task oferecida tem peso no pacote", not sem_peso,
                   ", ".join(sem_peso) or
                   "task na tela sem peso falha offline, no primeiro clique")
            for _r in sorted(reservas):
                checar("a reserva `%s` existe no catalogo, com datasets" % _r,
                       _r in no_catalogo,
                       "sem datasets `garantir_base` nao tem o que baixar")
                checar("  e ela NAO vem no pacote por omissao",
                       _r not in trazidas,
                       "reserva no pacote e peso morto em toda instalacao")

    vig = io.open(_componentes.fonte(no_app("radai_watcher.py")),
                  encoding="utf-8", errors="replace").read()
    checar("os motores das chaves que sairam continuam no registro",
           set(CHAVE_QUE_O_MOTOR_TINHA) <= set(m["cod"] for m in
                                             getattr(md, "MOTORES", ())),
           sorted(CHAVE_QUE_O_MOTOR_TINHA))
    for cod, chave in sorted(CHAVE_QUE_O_MOTOR_TINHA.items()):
        problemas = _motor_volta_ao_config(chave, vig)
        checar("o motor `%s` nao tem chave de config na estacao (v8.3)"
               % cod, not problemas,
               "; ".join(problemas) or
               "comparacao so no PERSONALIZADO; os niveis, pela anatomia")
    _isca = vig.replace('DEFAULTS = {"ROOT": ""',
                        'DEFAULTS = {"INCLUIR_NV": "0", "ROOT": ""', 1)
    _isca = _isca.replace("def process_series(s):",
                          "def process_series(s):\n    if INCLUIR_NV:\n"
                          "        pass", 1)
    checar("  (isca) a chave de volta no DEFAULTS e o ramo `if` sao acusados",
           _isca != vig
           and len(_motor_volta_ao_config("INCLUIR_NV", _isca)) >= 2,
           str(_motor_volta_ao_config("INCLUIR_NV", _isca)))

    cods = set(c["cod"] for c in getattr(st, "CONJUNTOS", ()))
    infixos = [c["infixo"] for c in getattr(st, "CONJUNTOS", ()) if c["infixo"]]
    checar("nenhum infixo de conjunto se repete",
           len(infixos) == len(set(infixos)), ", ".join(sorted(infixos)))
    sufixos = [c["sufixo"] for c in getattr(st, "CONJUNTOS", ()) if c["sufixo"]]
    checar("e nenhum sufixo de procedencia se repete alem do `_ai`",
           len([s for s in sufixos if s != "_ai"])
           == len(set(s for s in sufixos if s != "_ai")),
           ", ".join(sorted(sufixos)))
    for m in getattr(md, "MOTORES", ()):
        if m.get("regiao"):
            continue
        if m.get("no_full"):
            continue
        checar("o motor `%s` tem conjunto de saida" % m["cod"],
               m["cod"] in cods,
               "sem entrada em CONJUNTOS, o RTSTRUCT dele nao tem infixo")

    app = os.path.join(RAIZ, "app")
    engines = set(n for n in _componentes.nomes("app") if n.endswith("_engine.py"))
    checar("ha motores com engine proprio", bool(engines),
           ", ".join(sorted(engines)))
    for n in sorted(engines):
        txt = io.open(_componentes.fonte("app/" + n), encoding="utf-8",
                      errors="replace").read()
        checar("`%s` tem uma funcao `conferir_*`" % n,
               re.search(r"^def conferir_\w+\(", txt, re.M) is not None,
               "a trava mora na funcao que executa, e nao na bateria")


def checar_todo_import_aponta_para_arquivo():
    print("\n[14d] Todo import de radai_* aponta para arquivo que existe")
    app = os.path.join(RAIZ, "app")
    existem = set(n[:-3] for n in _componentes.nomes("app") if n.endswith(".py"))
    de_fora = set()
    quebrados = []
    lidos = 0
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        caminho = _componentes.fonte("app/" + nome)
        try:
            arv = ast.parse(io.open(caminho, encoding="utf-8",
                                    errors="replace").read())
        except Exception:
            continue
        lidos += 1
        for no in ast.walk(arv):
            alvos = []
            if isinstance(no, ast.Import):
                alvos = [a.name.split(".")[0] for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
                alvos = [no.module.split(".")[0]]
            for a in alvos:
                if not a.startswith("radai_"):
                    continue
                if a in existem or a in de_fora:
                    continue
                quebrados.append("%s:%d importa `%s`"
                                 % (nome, getattr(no, "lineno", 0), a))
    checar("li os modulos de app/", lidos > 40, "%d" % lidos)
    checar("nenhum import de radai_* aponta para arquivo ausente",
           not quebrados, " | ".join(sorted(set(quebrados))[:4]))

    ess = os.path.join(RAIZ, "build", "configurar_ambiente.py")
    if os.path.isfile(ess):
        txt = io.open(ess, encoding="utf-8", errors="replace").read()
        import ast as _ast
        _obr = []
        for _no in _ast.walk(_ast.parse(txt)):
            if isinstance(_no, _ast.Assign):
                for _t in _no.targets:
                    if isinstance(_t, _ast.Name) and _t.id == "obrigatorios":
                        try:
                            _obr = list(_ast.literal_eval(_no.value))
                        except Exception:
                            pass
        checar("  li a lista de obrigatorios do preparador", len(_obr) >= 3,
               str(_obr))
        _app_py = sorted(n for n in _componentes.nomes("app")
                         if n.endswith(".py"))
        _fora = [n for n in _app_py
                 if n not in set(_obr) and not n.startswith("radai_")]
        checar("todo `app/*.py` cai num glob do preparador ou na lista",
               not _fora,
               "%s — o preparador copia `radai_*.py` e a lista; o que nao "
               "casa nenhum dos dois nao chega a estacao" % _fora[:4])


def checar_motor_que_alimenta_vem_ligado():
    print("\n[14c] Motor que alimenta a entrega nasce ligado; o resto, nao")
    eng = _importar_do_app("engine")
    md = _importar_do_app("radai_modes")
    if eng is None or md is None:
        checar("engine e radai_modes importam", False)
        return
    alimentam = eng.motores_que_alimentam()
    candidatas = getattr(eng, "CANDIDATAS_AO_FULL", None)

    checar("existe a tabela `CANDIDATAS_AO_FULL`", isinstance(candidatas, dict),
           "e ela que guarda o que saiu de `MELHOR_FONTE`, e por que -- sem "
           "ela, a proxima sessao devolve as entradas achando que corrige um "
           "esquecimento")
    checar("`MELHOR_FONTE` vazia so com o registro do que saiu",
           bool(alimentam) or bool(candidatas),
           "as duas vazias querem dizer que a medida parou de medir")
    if isinstance(candidatas, dict):
        dentro = sorted(set(candidatas) & set(getattr(eng, "MELHOR_FONTE", {})))
        checar("nenhuma candidata esta nas duas tabelas", not dentro, str(dentro))
        checar("cada candidata diz motor, por que interessa e o que foi decidido",
               all(isinstance(v, tuple) and len(v) == 3
                   for v in candidatas.values()),
               "registro sem o porque envelhece calado")

    vig = io.open(_componentes.fonte(no_app("radai_watcher.py")),
                  encoding="utf-8", errors="replace").read()
    for m in getattr(md, "MOTORES", ()):
        chave = CHAVE_QUE_O_MOTOR_TINHA.get(m["cod"])
        if not chave:
            continue
        achou = re.search(r"^%s\s*=\s*(\S+)\s*$" % re.escape(chave), vig, re.M)
        ligado = bool(achou) and achou.group(1).strip() in ("1", "true", "True")
        quantas = len(alimentam.get(m["cod"], ()))
        if not achou:
            checar("`%s` nao tem chave na estacao, e nao alimenta a entrega"
                   % m["cod"], not quantas,
                   "motor que alimenta o FULL precisa rodar no vigia; sem "
                   "chave, ele nunca roda la")
            continue
        if quantas:
            checar("`%s` alimenta a entrega (%d estrutura(s)) e nasce LIGADO"
                   % (m["cod"], quantas), ligado,
                   "desligado, o arquivo que a revisao usa sai sem elas")
        else:
            checar("`%s` nao alimenta a entrega e nasce DESLIGADO" % m["cod"],
                   not ligado,
                   "ele custa tempo e produz arquivo de comparacao; ligar e "
                   "escolha de quem opera")

    fonte_md = io.open(_componentes.fonte(no_app("radai_modes.py")),
                       encoding="utf-8", errors="replace").read()
    checar("`ajuda_do_motor` existe e deriva de `alimentam`",
           "def ajuda_do_motor" in fonte_md,
           "sem ela a tela volta a repetir uma frase escrita a mao")
    for m in md.MOTORES:
        txt = (m.get("ajuda") or "").lower()
        checar("a ajuda de `%s` nao afirma nem nega que alimenta a entrega"
               % m["cod"],
               "alimenta a entrega" not in txt and "modo padr" not in txt,
               "isso e medido de `MELHOR_FONTE`; escrito aqui, e uma segunda "
               "copia da verdade -- e a copia e a que envelhece primeiro")
        checar("  e nao se apresenta por numero de ordem",
               not re.search(r"\b(primeiro|segundo|terceiro|quarto) motor\b",
                             txt),
               "a ordem dos motores muda; a ajuda nomeia o motor, e nao a posicao dele")

    lote = io.open(_componentes.fonte(no_app("radai_batch.py")),
                   encoding="utf-8", errors="replace").read()
    checar("radai_batch decide o recuo pelo criterio, e nao por literal",
           "_liga_por_omissao" in lote and "motores_que_alimentam" in lote)
    _cod_vig = NL.join(l for l in vig.splitlines()
                       if not l.lstrip().startswith("#"))
    for chave in ("incluir_cads", "incluir_hnlnl", "incluir_vista",
                  "incluir_nv", "incluir_moose"):
        checar("o vigia nao injeta `%s` no lote (a chave saiu na v8.3)"
               % chave, ('"%s"' % chave) not in _cod_vig,
               "chave que nenhum config produz; o lote le a ausencia como "
               "desligada, pelo criterio")


def _chamadas_sem_kw(funcao, kw, fontes):
    sem, vistas = [], 0
    for nome, texto in sorted(fontes.items()):
        try:
            arv = ast.parse(texto)
        except SyntaxError:
            continue
        for no in ast.walk(arv):
            if not isinstance(no, ast.Call):
                continue
            alvo = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
            if alvo != funcao:
                continue
            vistas += 1
            kws = [k.arg for k in no.keywords]
            if kw not in kws and None not in kws:
                sem.append(u"%s:%d" % (nome, no.lineno))
    return sem, vistas


def checar_recorte_no_corpo():
    print(NL + "[14h] O recorte no corpo: a decisao do autor nas duas pontas")
    valor = u"(nao achei)"
    try:
        for no in arvore(no_app("engine.py")).body:
            if (isinstance(no, ast.Assign)
                    and any(getattr(a, "id", None) == "RECORTE_NO_CORPO_PADRAO"
                            for a in no.targets)):
                valor = (no.value.value if isinstance(no.value, ast.Constant)
                         else u"(nao e literal)")
    except Exception as e:
        valor = u"(%s)" % type(e).__name__
    checar(u"`engine.RECORTE_NO_CORPO_PADRAO` e True", valor is True,
           u"le-se %r -- a decisao de 23/09/2026 e LIGADO" % (valor,))

    vig = ler(no_app("radai_watcher.py"))
    m = re.search(r"^RECORTE_NO_CORPO\s*=\s*(\S+)\s*$", vig, re.M)
    checar(u"o `DEFAULT_CFG` escreve `RECORTE_NO_CORPO=1`",
           bool(m) and m.group(1) == "1",
           u"le-se %r" % (m.group(1) if m else None))
    m2 = re.search(r'"RECORTE_NO_CORPO"\s*:\s*"([^"]*)"', vig)
    checar(u"  e o dicionario `DEFAULTS` diz o mesmo",
           bool(m2) and m2.group(1) == "1",
           u"le-se %r -- DEFAULT_CFG e DEFAULTS sao a mesma verdade"
           % (m2.group(1) if m2 else None))

    fontes = _fontes_do_app()
    fontes.pop("engine.py", None)
    sem, vistas = _chamadas_sem_kw("run_ts_task", "recorte_no_corpo", fontes)
    checar(u"toda chamada de `run_ts_task` fora do motor passa "
           u"`recorte_no_corpo=`", not sem,
           u"; ".join(sem[:4]) + u" -- a chave do config seria ignorada "
           u"calada, e valeria o padrao do motor")
    portas = set(n for n, t in fontes.items()
                 if _chamadas_sem_kw("run_ts_task", "recorte_no_corpo",
                                     {n: t})[1])
    checar(u"  e as duas portas de hoje chamam o motor (vigia e lote)",
           {"radai_watcher.py", "radai_batch.py"} <= portas,
           u"vi chamadas em: %s" % (u", ".join(sorted(portas)) or u"nenhum"))
    _isca = {"isca.py": "engine.run_ts_task(ref, t, device=d, jid=j)\n"
                        "engine.run_ts_task(ref, t, recorte_no_corpo=True)\n"}
    checar(u"  (isca) a chamada sem a chave e acusada, e a com ela nao",
           _chamadas_sem_kw("run_ts_task", "recorte_no_corpo", _isca)
           == ([u"isca.py:1"], 2))


def checar_full_antes_dos_plugins():
    print(NL + "[14f] O Full fecha em disco antes de qualquer plugin")
    PLUGINS = ("sd.vista3d(", "sd.cads(", "sd.moose(", "sd.niveis_cervicais(",
               "sd.plugins(", "sd.totalsegmentator_cru(")
    for arq in ("radai_watcher.py", "radai_batch.py"):
        try:
            txt = io.open(_componentes.fonte(no_app(arq)),
                          encoding="utf-8", errors="replace").read()
        except Exception:
            checar("%s pode ser lido" % arq, False)
            continue
        codigo = NL.join(l for l in txt.splitlines()
                         if not l.lstrip().startswith("#"))
        i_full = codigo.find("sd.full_e_oar(")
        checar("[%s] grava o Full (e o OAR, pela porta unica)" % arq,
               i_full >= 0)
        if i_full < 0:
            continue
        checar("[%s] e uma vez so" % arq,
               codigo.count("sd.full_e_oar(") == 1,
               "%d chamadas" % codigo.count("sd.full_e_oar("))
        for _velha in ("engine.para_oar(", "sd.ai_completo("):
            checar("[%s] nao chama `%s` (a porta antiga do entregue)"
                   % (arq, _velha[:-1]), _velha not in codigo,
                   "o entregue voltaria a ter dois pos-processamentos")
        for chamada in PLUGINS:
            i_p = codigo.find(chamada)
            if i_p < 0:
                continue
            nome = chamada[3:-1]
            checar("[%s] `%s` vem DEPOIS do Full" % (arq, nome),
                   i_full < i_p,
                   "plugin em %d, Full em %d -- se um plugin travar, o dia "
                   "termina sem o arquivo que a revisao usa" % (i_p, i_full))


def _retirados_do_output():
    import ast
    METODO = {"nv": "nv", "cads": "cads", "mse": "moose",
              "hnl": "niveis_cervicais", "pel": "pelvicos"}
    try:
        arv = ast.parse(io.open(_componentes.fonte(no_app("radai_output.py")),
                                encoding="utf-8", errors="replace").read())
    except Exception:
        return set()
    corpos = {}
    for no in ast.walk(arv):
        if isinstance(no, ast.FunctionDef):
            corpos[no.name] = no
    saida = set()
    for cod, nome in METODO.items():
        f = corpos.get(nome)
        if f is None:
            continue
        rets = [n for n in ast.walk(f) if isinstance(n, ast.Return)]
        if not rets:
            continue
        so_none = all(
            r.value is None
            or (isinstance(r.value, ast.Constant) and r.value.value is None)
            for r in rets)
        if so_none:
            saida.add(cod)
    return saida


def checar_promessa_bate_com_quem_grava():
    print(NL + "[14g] O que a revisao promete e' o que aquela porta grava")
    sys.path.insert(0, APP)
    try:
        import radai_review as RV
        import radai_sets as RS
    except Exception as e:
        checar("radai_review e radai_sets importam", False, str(e)[:120])
        return
    finally:
        sys.path.pop(0)

    GRAVA = {"nv": "sd.vista3d(", "cads": "sd.cads(", "mse": "sd.moose(",
             "hnl": "sd.niveis_cervicais(", "pel": "sd.pelvicos("}
    OUTRO_NOME = {"nv": "sd.nv("}
    PORTA = {"radai_batch.py": "lote", "radai_watcher.py": "vigia"}

    for arq, origem in sorted(PORTA.items()):
        try:
            txt = io.open(_componentes.fonte(no_app(arq)),
                          encoding="utf-8", errors="replace").read()
        except Exception:
            checar("%s pode ser lido" % arq, False)
            continue
        codigo = NL.join(l for l in txt.splitlines()
                         if not l.lstrip().startswith("#"))
        _comp = origem != "vigia"
        prometidos = RV._conjuntos_previstos(
            incluir_nv=_comp, incluir_cads=_comp, incluir_hnlnl=True,
            elegivel_tx=True, incluir_moose=_comp, origem=origem)
        vistos = set()
        for item in prometidos:
            cod = str(item["cod"])
            vistos.add(cod)
            chamada = GRAVA.get(cod)
            if chamada is None:
                continue
            if not item.get("sai"):
                continue
            checar(u"[%s] promete `%s` e chama `%s`"
                   % (arq, cod, chamada[3:-1]), chamada in codigo
                   or OUTRO_NOME.get(cod, u"\0") in codigo,
                   u"a tela diz que sai e o arquivo nao grava — o operador "
                   u"procura defeito numa serie que esta certa")
        for cod, chamada in sorted(GRAVA.items()):
            if (chamada not in codigo
                    and OUTRO_NOME.get(cod, u"\0") not in codigo):
                continue
            if cod in _retirados_do_output():
                continue
            item = [i for i in prometidos if str(i["cod"]) == cod]
            checar(u"[%s] grava `%s` e a revisao o promete" % (arq, cod),
                   bool(item) and bool(item[0].get("sai")),
                   u"o arquivo sai e a tela disse que nao sairia")
        if origem == "vigia":
            _h = [i for i in prometidos if str(i["cod"]) == "hnl"]

            def _hnl_so_no_full(cod_):
                return (bool(_h) and not _h[0].get("sai")
                        and GRAVA["hnl"] not in cod_)
            checar(u"[%s] o `hnl` NAO sai no vigia (o AUTO: os niveis vao so "
                   u"ao FULL), e a revisao diz isso" % arq,
                   _hnl_so_no_full(codigo),
                   str(_h[0] if _h else u"a revisao nao descreve o `hnl`"))
            checar(u"  isca: o vigia gravando o `HNL_` de novo e acusado",
                   not _hnl_so_no_full(codigo + NL + u"    sd.niveis_cervicais("
                                                u"_HNLNL_DA_VEZ[\"masks\"])"))
        checar(u"[%s] a revisao descreve os %d conjuntos do registro"
               % (arq, len(RS.CONJUNTOS)),
               vistos == set(str(c["cod"]) for c in RS.CONJUNTOS),
               u"faltou: %s" % sorted(set(str(c["cod"])
                                          for c in RS.CONJUNTOS) - vistos))


def checar_todo_gravador_declara_o_desconto():
    import ast as _ast
    achados = []
    for rel in _componentes.nomes("app"):
        if not rel.endswith(".py"):
            continue
        cam = "app/" + rel
        try:
            arv = arvore(cam)
        except Exception:
            continue
        for no in _ast.walk(arv):
            if not isinstance(no, _ast.Call):
                continue
            f = no.func
            nome = (f.attr if isinstance(f, _ast.Attribute)
                    else getattr(f, "id", ""))
            if nome != "build_rtstruct":
                continue
            tem = any(k.arg == "descontar" for k in no.keywords)
            curado = any(k.arg == "derivar"
                         and isinstance(k.value, _ast.Constant)
                         and k.value.value is True
                         for k in no.keywords)
            lit = curado and any(
                k.arg == "descontar" and isinstance(k.value, _ast.Constant)
                for k in no.keywords)
            achados.append((cam, no.lineno, tem, lit))

    checar("achei os chamadores de `build_rtstruct`", len(achados) >= 2,
           "%d chamada(s)" % len(achados))
    mudos = ["%s:%d" % (c, l) for c, l, tem, _lit in achados if not tem]
    checar("todo chamador de `build_rtstruct` declara `descontar=`",
           not mudos, ", ".join(mudos))

    literais = ["%s:%d" % (c, l) for c, l, _tem, lit in achados if lit]
    checar("quem grava o entregue tira `descontar` do registro, e nao de um "
           "literal", not literais, ", ".join(literais))

    out = ler("app/radai_output.py")
    checar("e `radai_output` ainda repassa a chave do registro",
           "descontar=bool(reg.get(" in out)


def _funcoes_que_nao_consultam(fonte, nomes, modulo_alvo):
    import ast as _ast
    try:
        arv = _ast.parse(fonte)
    except Exception:
        return list(nomes)
    achadas = {}
    for no in _ast.walk(arv):
        if isinstance(no, _ast.FunctionDef) and no.name in nomes:
            achadas[no.name] = no
    fora = []
    for n in nomes:
        f = achadas.get(n)
        if f is None:
            fora.append(n + " (nao existe)")
            continue
        usa = False
        for sub in _ast.walk(f):
            if (isinstance(sub, _ast.Attribute)
                    and isinstance(sub.value, _ast.Name)
                    and sub.value.id in modulo_alvo):
                usa = True
                break
        if not usa:
            fora.append(n)
    return fora


def _curar_com_a_forma_do_cads(fonte):
    import ast as _ast
    fora = []
    try:
        arv = _ast.parse(fonte)
    except Exception:
        return fora
    for no in _ast.walk(arv):
        if not isinstance(no, _ast.Call):
            continue
        f = no.func
        nome = f.attr if isinstance(f, _ast.Attribute) else getattr(f, "id", "")
        if nome != "curar":
            continue
        seg = no.args[1] if len(no.args) > 1 else None
        ok = (isinstance(seg, _ast.Dict)
              and any(isinstance(k, _ast.Constant) and k.value == "cads"
                      for k in seg.keys))
        fora.append((no.lineno, ok))
    return fora


def _cru_nao_le_a_imagem(fonte):
    import ast as _ast
    try:
        arv = _ast.parse(fonte)
    except Exception:
        return False
    for no in _ast.walk(arv):
        if isinstance(no, _ast.FunctionDef) and no.name == "build_rtstruct":
            for sub in _ast.walk(no):
                if not isinstance(sub, _ast.If):
                    continue
                le_cru = any(isinstance(n, _ast.Name) and n.id == "cru"
                             for n in _ast.walk(sub.test))
                if not le_cru:
                    continue
                for dentro in sub.body:
                    for c in _ast.walk(dentro):
                        if (isinstance(c, _ast.Call)
                                and getattr(c.func, "id", "") == "load_sitk"):
                            return True
    return False


def checar_cadeia_do_full():
    print(NL + "[14i] A cadeia do FULL: permitidos, plugins, tradutor, cru")
    sys.path.insert(0, os.path.join(RAIZ, APP))
    try:
        import radai_sets as RS
        import radai_names as RN
        import radai_tasks as RT
        import engine as E
    except Exception as e:
        checar("os modulos da cadeia importam", False,
               "%s: %s" % (type(e).__name__, e))
        return

    derivadas = set()
    for regra in E.DERIVADAS.values():
        for _m, _e, _o, filha in regra["planos"]:
            derivadas.add(filha)
    reservadas_onda2 = {"bag_bowel"}
    conhecidos = (set(E.TS_MAP) | set(E.COMPOSTOS)
                  | set(E.CONSTRUCOES_POR_SAIDA()) | derivadas
                  | reservadas_onda2
                  | set(getattr(E, "CHAVES_GLANDULA_POR_LADO", {}).values())
                  | set(getattr(E, "CHAVES_DERRAME_POR_LADO", {}).values()))
    try:
        import radai_motores_full as _MF
        for _ks in _MF.estruturas_no_full().values():
            conhecidos |= set(_ks)
    except Exception as e:
        checar("radai_motores_full importa", False,
               "%s: %s" % (type(e).__name__, e))
    try:
        import radai_hnlnl as _HN
        conhecidos |= set(_HN.CHAVES_NO_OAR)
    except Exception as e:
        _HN = None
        checar("radai_hnlnl importa", False, "%s: %s" % (type(e).__name__, e))
    fantasmas = sorted(RS.PERMITIDOS_NO_OAR - conhecidos)
    checar("todo permitido do OAR e um nome que o FULL pode produzir",
           not fantasmas, ", ".join(fantasmas[:6]))
    _isca = set(RS.PERMITIDOS_NO_OAR) | {"small_bowel_inventado"}
    checar("  (isca) um nome inventado na lista e acusado",
           bool(_isca - conhecidos))
    partes = E.partes_de_composto()
    checar("nenhuma PARTE de composto no OAR (lobos, costelas, vasos, "
           "gluteos): o composto vai, a parte fica no FULL",
           not (RS.PERMITIDOS_NO_OAR & partes),
           ", ".join(sorted(RS.PERMITIDOS_NO_OAR & partes)[:6]))
    tirados = ({"mediastinum", "thoracic_cavity", "pericardium",
                "abdominal_cavity", "femur_left", "femur_right", "breast",
                "atrial_appendage_left", RN.CHAVE_DO_CORACAO_DO_MODELO,
                "LNL_Union"} | set("LNL%02d" % i for i in range(1, 21))
               # GUARDA: nivel cervical nenhum vai ao OAR; so a uniao e as
               # parotidas do VIII (`radai_hnlnl.CHAVES_NO_OAR`)
               | (set(_HN.nome_do_nivel(i) for i in range(1, 21))
                  if _HN is not None else set())
               | {"gluteus_muscles"}
               # GUARDA: so no FULL (adrenais, Muscles_ai) e o indice 26,
               # fundido ao sacro
               | {"adrenal_gland_left", "adrenal_gland_right",
                  "pelvic_muscles", "vertebrae_L6", "vertebrae_S1"}
               # GUARDA: o OAR leva so a Bag_Bowel_OAR; a Breast_OAR saiu
               | {"bag_bowel", "bag_bowel_test", "breast_oar_left",
                  "breast_oar_right"})
    checar("o que a spec A5, a v8.3 e a v8.5 tiraram do OAR esta fora da "
           "lista",
           not (RS.PERMITIDOS_NO_OAR & tirados),
           ", ".join(sorted(RS.PERMITIDOS_NO_OAR & tirados)))
    for obrig in ("heart", "femur_oar_left", "femur_oar_right", "Skin",
                  "ChestWall_L", "ChestWall_R", "bag_bowel_oar",
                  "bone_pelvic", "breast_left",
                  "breast_right", "rectum", "colon",
                  # GUARDA: dos niveis, so a uniao e as parotidas do VIII
                  "LNL_UNION", "parotid_lnl_left", "parotid_lnl_right"):
        checar("  e o que ela pos esta dentro: %s" % obrig,
               obrig in RS.PERMITIDOS_NO_OAR)
    checar("[v8.3] `ROTULOS_FORA_DO_FULL` so tem a `head` da "
           "craniofacial_structures",
           RS.ROTULOS_FORA_DO_FULL == {"craniofacial_structures": ("head",)},
           str(RS.ROTULOS_FORA_DO_FULL))
    checar("[v8.3] a `abdominal_muscles` alimenta o FULL inteira (sem "
           "`ROTULOS_SO_NO_FULL` e sem plugin)",
           "abdominal_muscles" not in RS.ROTULOS_SO_NO_FULL
           and "abdominal_muscles" not in RS.PLUGIN_DA_TASK)
    checar("[v8.3] o sufixo de derivada e o do plugin do tronco estao "
           "aposentados (lidos, nunca escritos)",
           {"_der", "_abm"} <= set(RS.SUFIXOS_APOSENTADOS)
           and not ({"_der", "_abm"} & set(RS.SUFIXOS_VIVOS)))
    for c in ("pelvic_muscles", "bone_pelvic", "atrial_appendage_left"):
        nome_tps = E.nome_clinico(c)
        checar("[v8.3] `%s` sai como `%s` (<=16, nome do TG263, a conferir)"
               % (c, nome_tps),
               len(nome_tps) <= 16 and c in E.TG263
               and c in E.TG263_A_CONFERIR)
    for nome in sorted(set(E.CONSTRUCOES_POR_SAIDA()) | reservadas_onda2):
        final = E.nome_clinico(nome)
        checar("  a construcao `%s` sai como `%s` (<=16)" % (nome, final),
               len(final) <= 16 and (nome in E.TG263
                                     or nome in ("Skin", "ChestWall_L",
                                                 "ChestWall_R")),
               "sem entrada em TG263, o nome no TPS seria o recorte do "
               "nome interno")

    catalogo = [d["task"] for d in RT.CATALOGO]
    orfas = [t for t in catalogo
             if not RS.task_do_full(t) and t not in RS.PLUGIN_DA_TASK]
    checar("toda task do catalogo alimenta o FULL ou tem plugin proprio",
           not orfas, ", ".join(orfas))
    fora_do_catalogo = [p["task"] for p in RS.PLUGINS
                        if p["task"] not in catalogo]
    checar("  e todo plugin e de uma task do catalogo", not fora_do_catalogo,
           ", ".join(fora_do_catalogo))
    achados = sorted(set(getattr(E, "TASKS_DE_ACHADO", ())))
    checar("REGRA A: nenhuma task de ACHADO alimenta o FULL",
           not [t for t in achados if RS.task_do_full(t)],
           ", ".join(t for t in achados if RS.task_do_full(t)))
    checar("  e todo plugin de ACHADO se declara achado",
           all(RS.PLUGIN_DA_TASK[t].get("achado") for t in achados
               if t in RS.PLUGIN_DA_TASK),
           ", ".join(t for t in achados if t in RS.PLUGIN_DA_TASK
                     and not RS.PLUGIN_DA_TASK[t].get("achado")))
    todos = list(RS.CONJUNTOS) + list(RS.PLUGINS)
    sufixos = [c["sufixo"] for c in todos if c["cod"] != "oar"]
    infixos = [c["infixo"] for c in todos if c["infixo"]]
    checar("sufixos unicos entre conjuntos e plugins (o OAR divide o do FULL)",
           len(sufixos) == len(set(s.lower() for s in sufixos)),
           ", ".join(sorted(sufixos)))
    checar("  e o OAR usa o MESMO sufixo do FULL (e uma copia dele)",
           RS.POR_COD["oar"]["sufixo"] == RS.POR_COD["full"]["sufixo"])
    checar("infixos unicos entre conjuntos e plugins",
           len(infixos) == len(set(infixos)), ", ".join(sorted(infixos)))
    longos = [c["cod"] for c in RS.PLUGINS
              if len(RS.rotulo_dicom(c["cod"])) > 16]
    checar("o rotulo `RadAI_<COD>` de todo plugin cabe no SH de 16",
           not longos, ", ".join(longos))
    checar("todo plugin tem sufixo de 3 letras (a cauda de 16 e inviolavel)",
           all(len(p["sufixo"]) == 4 for p in RS.PLUGINS),
           ", ".join(p["sufixo"] for p in RS.PLUGINS if len(p["sufixo"]) != 4))

    checar("o `full` desconta o cisto (Q6: rim descontado + cisto no FULL)",
           bool(RS.POR_COD["full"].get("desconta")))
    checar("  e o `oar` tambem (ele e uma selecao do FULL)",
           bool(RS.POR_COD["oar"].get("desconta")))

    fontes = _fontes_do_app()
    quem = dict((n, _curar_com_a_forma_do_cads(t)) for n, t in fontes.items()
                if n != "engine.py")
    chamam = sorted(n for n, cs in quem.items() if cs)
    checar("so `radai_output` chama `curar` (as portas nao a chamam direto)",
           chamam == ["radai_output.py"], ", ".join(chamam))
    ruins = ["%s:%d" % (n, l) for n, cs in quem.items() for l, ok in cs
             if not ok]
    checar("  e com `{\"cads\": ...}`, a forma que `curar` entende",
           not ruins, ", ".join(ruins))
    _isca = "engine.curar(masks, cads_da_vez, log=log)\n"
    checar("  (isca) a forma do «Rodar agora» ate a v8.1 e acusada",
           _curar_com_a_forma_do_cads(_isca) == [(1, False)])

    mt = ler(no_app("engine.py"))
    checar("o `build_rtstruct` so le a imagem fora do conjunto cru (A1)",
           _cru_nao_le_a_imagem(mt))
    checar("  (isca) sem o `if not cru`, acusa",
           not _cru_nao_le_a_imagem(
               "def build_rtstruct(a, cru=False):\n    x = load_sitk(a)\n"))

    fun_motor = ("suavizacao_de", "_familia_para_refino", "implausiveis",
                 "nome_clinico", "aplicar_desconto", "aplicar_contencao",
                 "_volume_cm3", "_color", "aplicar_margens_de_oar",
                 "aplicar_recorte_de_oar")
    sem = _funcoes_que_nao_consultam(mt, fun_motor, ("_nomes",))
    checar("as tabelas do motor passam pelo tradutor (radai_names)",
           not sem, ", ".join(sem))
    pl = ler(no_app("radai_plausibility.py"))
    sem = _funcoes_que_nao_consultam(pl, ("janela_de", "_declarada"),
                                     ("radai_names",))
    checar("  e a janela de densidade tambem", not sem, ", ".join(sem))
    _isca = ("def suavizacao_de(nome, padrao=None):\n"
             "    return SUAVIZACAO.get(str(nome))\n")
    checar("  (isca) a consulta direta de 22/09 e acusada",
           _funcoes_que_nao_consultam(_isca, ("suavizacao_de",),
                                      ("_nomes",)) == ["suavizacao_de"])

    import ast as _ast
    arv = _ast.parse(mt)
    defs = set(n.name for n in _ast.walk(arv)
               if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)))
    checar("o `_worker` legado saiu do motor", "_worker" not in defs)
    rotas = []
    for n in _ast.walk(arv):
        if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            for d in n.decorator_list:
                if (isinstance(d, _ast.Call) and d.args
                        and isinstance(d.args[0], _ast.Constant)):
                    rotas.append(str(d.args[0].value))
    checar("  e a rota `POST /segment` tambem", "/segment" not in rotas,
           ", ".join(rotas))
    f_b = [n for n in _ast.walk(arv)
           if isinstance(n, _ast.FunctionDef) and n.name == "build_rtstruct"]
    flip = bool(f_b) and any(
        isinstance(c, _ast.Attribute) and c.attr == "flip"
        for c in _ast.walk(f_b[0]))
    checar("a retentativa com a mascara ESPELHADA saiu do `build_rtstruct`",
           bool(f_b) and not flip)

    checar("a parede recebe `cru=` e `torax=` (`_construir_pele_e_parede`)",
           _chama_com(mt, "_construir_pele_e_parede", "parede_toracica",
                      ("cru", "torax")))
    checar("  (isca) a chamada sem os dois e acusada",
           not _chama_com("def _construir_pele_e_parede(m):\n"
                          "    radai_skin.parede_toracica(v, e, g, log=l)\n",
                          "_construir_pele_e_parede", "parede_toracica",
                          ("cru", "torax")))
    ro = ler(no_app("radai_output.py"))
    checar("  e a porta unica os entrega a `preparar_full`",
           _chama_com(ro, "full_e_oar", "insumos_fora_do_full", ())
           and "torax" in _parametros(ro, "full_e_oar"))
    checar("o femur sem recorte tem a descricao que diz isso "
           "(`DESCRICAO_FEMUR_SEM_RECORTE`)",
           _usa_nome(mt, "_construir_femur_oar",
                     "DESCRICAO_FEMUR_SEM_RECORTE"))
    checar("  (isca) a construcao que so devolve a mascara e acusada",
           not _usa_nome("def _construir_femur_oar(m, g):\n"
                         "    return {'femur_oar_left': m}\n",
                         "_construir_femur_oar",
                         "DESCRICAO_FEMUR_SEM_RECORTE"))
    checar("a falha do entregue encadeia a causa (`raise ... from e`) e diz "
           "o tipo (`motivo_do_erro`)",
           _levanta_encadeado(ro, "full_e_oar")
           and _usa_nome(ro, "full_e_oar", "motivo_do_erro"))
    checar("  (isca) o `raise` sem `from` e acusado",
           not _levanta_encadeado(
               "def full_e_oar(s):\n    try:\n        x()\n"
               "    except Exception as e:\n"
               "        raise RuntimeError(str(e))\n", "full_e_oar"))


def _funcao_ast(fonte, nome):
    import ast as _ast
    try:
        arv = _ast.parse(fonte)
    except SyntaxError:
        return None
    for n in _ast.walk(arv):
        if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)) \
                and n.name == nome:
            return n
    return None


def _usa_nome(fonte, funcao, nome):
    import ast as _ast
    f = _funcao_ast(fonte, funcao)
    if f is None:
        return False
    return any(isinstance(n, _ast.Name) and n.id == nome
               for n in _ast.walk(f))


def _chama_com(fonte, funcao, alvo, kws):
    import ast as _ast
    f = _funcao_ast(fonte, funcao)
    if f is None:
        return False
    for c in _ast.walk(f):
        if not isinstance(c, _ast.Call):
            continue
        nome = getattr(c.func, "attr", None) or getattr(c.func, "id", None)
        if nome != alvo:
            continue
        tem = set(k.arg for k in c.keywords if k.arg)
        if all(k in tem for k in kws):
            return True
    return False


def _parametros(fonte, funcao):
    f = _funcao_ast(fonte, funcao)
    if f is None:
        return ()
    a = f.args
    return tuple(x.arg for x in (a.args + a.kwonlyargs))


def _levanta_encadeado(fonte, funcao):
    import ast as _ast
    f = _funcao_ast(fonte, funcao)
    if f is None:
        return False
    achou = False
    for h in _ast.walk(f):
        if not isinstance(h, _ast.ExceptHandler):
            continue
        for r in _ast.walk(h):
            if isinstance(r, _ast.Raise) and r.exc is not None:
                achou = True
                if r.cause is None:
                    return False
    return achou


def _fontes_do_app(fontes=None):
    if fontes is not None:
        return dict(fontes)
    saida = {}
    for nome in _componentes.nomes("app", RAIZ):
        if nome.endswith(".py"):
            saida[nome] = io.open(_componentes.fonte("app/" + nome, RAIZ),
                                  encoding="utf-8-sig", errors="replace").read()
    return saida


def _quem_importa_no_app(modulo, fontes=None):
    achados = []
    for nome, texto in sorted(_fontes_do_app(fontes).items()):
        if nome == modulo + ".py":
            continue
        try:
            arv = ast.parse(texto)
        except SyntaxError:
            continue
        for no in ast.walk(arv):
            if ((isinstance(no, ast.Import)
                 and any(a.name == modulo for a in no.names))
                    or (isinstance(no, ast.ImportFrom) and no.module == modulo)
                    or (isinstance(no, ast.Call)
                        and getattr(no.func, "id", "") == "__import__"
                        and no.args
                        and getattr(no.args[0], "value", None) == modulo)):
                achados.append(nome)
                break
    return achados


def _literal_vivo_com(agulhas, fontes=None):
    achados = []
    for nome, texto in sorted(_fontes_do_app(fontes).items()):
        try:
            arv = ast.parse(texto)
        except SyntaxError:
            continue
        soltas = set()
        for no in ast.walk(arv):
            if (isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant)
                    and isinstance(no.value.value, str)):
                soltas.add(id(no.value))
        for no in ast.walk(arv):
            if (isinstance(no, ast.Constant) and isinstance(no.value, str)
                    and id(no) not in soltas):
                for ag in agulhas:
                    if ag in no.value:
                        achados.append(u"%s: %s" % (nome, ag))
    return sorted(set(achados))


def _funcao(arv, nome):
    for no in ast.walk(arv):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and no.name == nome:
            return no
    return None


def _chama(funcao, nome):
    if funcao is None:
        return False
    for c in ast.walk(funcao):
        if isinstance(c, ast.Call):
            alvo = getattr(c.func, "id", None) or getattr(c.func, "attr", None)
            if alvo == nome:
                return True
    return False


def checar_regra_seis():
    print("\n[16] A regra 6 tem trava, e ela e chamada por quem executa")
    caminho = _componentes.fonte(no_app("engine.py"))
    txt = io.open(caminho, encoding="utf-8", errors="replace").read()
    arv = ast.parse(txt)
    definidos = nomes_de_modulo(arv)

    checar("engine.TASKS_PERMITIDAS existe", "TASKS_PERMITIDAS" in definidos)
    checar("engine.conferir_tasks existe", "conferir_tasks" in definidos)

    eng = _importar_do_app("engine")
    if eng is None:
        checar("engine importa (para ler o VALOR das listas)", False,
               "sem importar, so da para medir texto -- e texto sobrevive a "
               "mudanca de sentido")
    else:
        achado = set(getattr(eng, "TASKS_DE_ACHADO", ()) or ())
        perm = set(getattr(eng, "TASKS_PERMITIDAS", {}) or {})
        checar("engine.TASKS_DE_ACHADO existe e nao esta vazia", bool(achado),
               "e ela que separa «permitido» de «padrao»; vazia, a regra A "
               "nao tem sobre o que agir")
        checar("toda task de achado esta entre as PERMITIDAS",
               achado <= perm,
               "achado fora das permitidas seria recusa por omissao, e a "
               "regra B diz que elas rodam por ato declarado")
        checar("`lung_nodules` esta declarada como ACHADO",
               "lung_nodules" in achado)
        checar("nenhuma permitida e nome que o TotalSegmentator nao conhece",
               "lung_nodules_1_5mm" not in perm,
               "nome plausivel que nao resolve em lugar nenhum -- a mesma "
               "familia do DOI inventado de 04/09/2026")
        checar("a lista continua sendo de PERMITIDOS (nome inventado cai fora)",
               "totalmente_inventada_xyz" not in perm)

    checar("run_ts_task chama conferir_tasks",
           _chama(_funcao(arv, "run_ts_task"), "conferir_tasks"),
           "a lista sem a chamada e enfeite")
    _isca_doc = ast.parse(
        'def porta():\n'
        '    """Esta porta passa por conferir_registro antes de tudo."""\n'
        '    return 1\n'
        'def porta2():\n'
        '    """Idem."""\n'
        '    modulo.conferir_registro()\n'
        '    return 1\n')
    checar("  (isca) a docstring que cita a trava NAO conta como chamada; "
           "a chamada conta",
           not _chama(_funcao(_isca_doc, "porta"), "conferir_registro")
           and _chama(_funcao(_isca_doc, "porta2"), "conferir_registro")
           and "conferir_registro" in ast.dump(_funcao(_isca_doc, "porta")),
           "a guarda antiga, por `ast.dump`, passava na primeira")

    vig = io.open(_componentes.fonte(no_app("radai_watcher.py")),
                  encoding="utf-8", errors="replace").read()
    checar("o vigia confere as tasks no arranque",
           "conferir_tasks" in vig)

    vm = io.open(_componentes.fonte(no_app("radai_nv_engine.py")),
                 encoding="utf-8", errors="replace").read()
    arv_vm = ast.parse(vm)
    def_vm = nomes_de_modulo(arv_vm)

    checar("radai_nv_engine.CLASSES_PERMITIDAS existe",
           "CLASSES_PERMITIDAS" in def_vm)
    checar("radai_nv_engine.conferir_classes existe",
           "conferir_classes" in def_vm)

    vme = _importar_do_app("radai_nv_engine")
    if vme is None:
        checar("radai_nv_engine importa (para ler o VALOR das listas)",
               False, "regex sobre o literal nao ve a segunda atribuicao")
    else:
        entrega = set(getattr(vme, "CLASSES_DE_ENTREGA", ()) or ())
        permitidas = set(getattr(vme, "CLASSES_PERMITIDAS", ()) or ())
        de_achado = set(getattr(vme, "CLASSES_DE_ACHADO", {}) or {})
        SETE = ("lung tumor", "pancreatic tumor", "hepatic tumor",
                "colon cancer primaries", "bone lesion",
                "left kidney cyst", "right kidney cyst")
        checar("CLASSES_DE_ENTREGA existe e e menor que as permitidas",
               bool(entrega) and entrega < permitidas,
               "sao DUAS listas de proposito: filtro se esquece de aplicar, e "
               "foi assim que as 124 foram pedidas por tres meses")
        for n in SETE:
            checar("`%s` e ACHADO e NAO entra no prompt da entrega" % n,
                   (n in de_achado) and (n not in entrega))
        checar("e as sete SAO permitidas (regra B)",
               all(n in permitidas for n in SETE),
               "permitido e pedido sao coisas diferentes")
        try:
            mapa = dict((n, i) for i, n in
                        enumerate(sorted(permitidas | set(SETE)), start=1))
            ids = set(vme.ids_permitidos(por_nome=mapa))
            achado_ids = set(mapa[n] for n in SETE if n in mapa)
            checar("`ids_permitidos` nao devolve nenhum id de achado",
                   not (ids & achado_ids),
                   "e ela que monta o label_prompt da entrega")
        except Exception as e:
            checar("`ids_permitidos` roda com mapa de fantoma", False, str(e))

    checar("`rodar` chama conferir_classes",
           _chama(_funcao(arv_vm, "rodar"), "conferir_classes"),
           "a lista sem a chamada e enfeite")

    cmp_ = io.open(_componentes.fonte(no_app("radai_compare.py")),
                   encoding="utf-8", errors="replace").read()
    checar("o chamador NAO pede o labels.json inteiro",
           "sorted(set(classes.values()))" not in cmp_,
           "voltaria a pedir as 124, e a trava mataria toda serie")
    checar("o chamador monta o prompt por `ids_permitidos`",
           "ids_permitidos" in cmp_)

    nni = _componentes.fonte(no_app("radai_nninteractive.py"))
    checar("`radai_nninteractive` saiu do app (licenca nao comercial; "
           "volta so por decisao escrita do autor)",
           not os.path.isfile(nni), nni)

    hm = _componentes.fonte(no_app("radai_hnlnl_engine.py"))
    hn = _componentes.fonte(no_app("radai_hnlnl.py"))
    checar("`radai_hnlnl_engine` existe", os.path.isfile(hm))
    checar("`radai_hnlnl` existe", os.path.isfile(hn))
    if os.path.isfile(hm) and os.path.isfile(hn):
        t_hm = io.open(hm, encoding="utf-8", errors="replace").read()
        t_hn = io.open(hn, encoding="utf-8", errors="replace").read()
        def_hm = nomes_de_modulo(ast.parse(t_hm))
        def_hn = nomes_de_modulo(ast.parse(t_hn))
        checar("`INDICES_PERMITIDOS` existe (lista de PERMITIDOS)",
               "INDICES_PERMITIDOS" in def_hm)
        checar("`conferir_niveis` existe", "conferir_niveis" in def_hm)
        checar("`conferir_saida` existe", "conferir_saida" in def_hn)
        f_h = _funcao(ast.parse(t_hn), "rodar_na_serie")
        checar("`rodar_na_serie` chama `conferir_niveis`",
               _chama(f_h, "conferir_niveis"),
               "a lista sem a chamada e enfeite")
        checar("`rodar_na_serie` chama `conferir_saida`",
               _chama(f_h, "conferir_saida"),
               "a lista sem a chamada e enfeite")
        checar("ha teto de classes do modelo", "TETO_DE_CLASSES" in def_hm,
               "modelo com 40 saidas nao pode carregar em silencio")
        checar("o recorte por marcos e exigido", "OBRIGATORIOS" in def_hn)
        checar("e `caixa` levanta quando falta marco",
               "raise ValueError" in t_hn and "recorte do artigo" in t_hn)

    imp_nni = _quem_importa_no_app("radai_nninteractive")
    checar("nenhum modulo de app/ importa `radai_nninteractive`", not imp_nni,
           ", ".join(imp_nni) + " -- a porta do clique foi fechada em "
           "23/09/2026; reabrir e decisao escrita, com a licenca na mesa")
    rotas_nni = _literal_vivo_com(("/api/verseg/contornar_ponto",
                                   "/nni_estado"))
    checar("nenhum literal vivo de app/ nomeia as rotas do clique",
           not rotas_nni, "; ".join(rotas_nni[:3]))
    _isca = ("import radai_nninteractive\n"
             "R = '/api/verseg/contornar_ponto'\n")
    checar("  (isca) a guarda acha o import e a rota num fonte que os tem",
           bool(_quem_importa_no_app("radai_nninteractive",
                                     fontes={"isca.py": _isca}))
           and bool(_literal_vivo_com(("/api/verseg/contornar_ponto",),
                                      fontes={"isca.py": _isca})))
    _nota = ('"""A rota /api/verseg/contornar_ponto saiu em 23/09."""\n'
             'X = 1\n')
    checar("  (isca) e NAO acusa a nota que conta que a rota saiu",
           not _literal_vivo_com(("/api/verseg/contornar_ponto",),
                                 fontes={"nota.py": _nota}))

    em_laco = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        try:
            arv = ast.parse(io.open(_componentes.fonte(no_app(nome)),
                                    encoding="utf-8", errors="replace").read())
        except SyntaxError:
            continue
        for no in ast.walk(arv):
            if not isinstance(no, (ast.For, ast.While, ast.AsyncFor)):
                continue
            for dentro in ast.walk(no):
                if not isinstance(dentro, ast.Call):
                    continue
                f = dentro.func
                alvo = (getattr(f, "attr", "") or getattr(f, "id", ""))
                if alvo == "contornar":
                    em_laco.append("%s linha %d" % (nome, dentro.lineno))
    checar("ninguem chama `contornar` dentro de um laco", not em_laco,
           "; ".join(em_laco[:3]) + " — laco sobre pontos e um DETECTOR")

    sus = _componentes.fonte(no_app("radai_plausibility.py"))
    checar("`radai_plausibility` existe", os.path.isfile(sus))
    if os.path.isfile(sus):
        t_s = io.open(sus, encoding="utf-8", errors="replace").read()
        arv_s = ast.parse(t_s)
        def_s = nomes_de_modulo(arv_s)
        checar("`conferir_ancoragem` existe", "conferir_ancoragem" in def_s)
        checar("`conferir_motivo` existe", "conferir_motivo" in def_s)
        checar("`JANELAS_HU` existe (lista de PERMITIDOS)",
               "JANELAS_HU" in def_s)
        checar("`COBERTURA` diz o que a medida NAO enxerga",
               "COBERTURA" in def_s and "gordura" in t_s.lower())

        f_s = _funcao(arv_s, "conferir_sustentacao")
        checar("`conferir_sustentacao` chama `conferir_ancoragem`",
               _chama(f_s, "conferir_ancoragem"),
               "sem ancoragem ela pode julgar nome que ninguem desenhou")
        checar("e passa toda frase por `frase`/`conferir_motivo`",
               _chama(f_s, "frase") or _chama(f_s, "conferir_motivo"),
               "frase montada em vez de escolhida abre a porta do veredito")

        proibidas = ("ausente", "ausencia", "nao ha", "n\u00e3o h\u00e1",
                     "removido", "nefrectomia", "ressecado", "tumor",
                     "lesao", "les\u00e3o", "maligno", "neoplasia")
        motivos = ""
        for no in ast.walk(arv_s):
            if (isinstance(no, ast.Assign)
                    and any(getattr(a, "id", "") == "MOTIVOS" for a in no.targets)):
                motivos = ast.dump(no).lower()
        achadas = [w for w in proibidas if w in motivos]
        checar("nenhuma frase do vocabulario AFIRMA um achado", not achadas,
               "as frases dizem %s — isso e veredito, nao medida"
               % ", ".join(achadas[:3]))

        for no in ast.walk(arv_s):
            if isinstance(no, ast.FunctionDef) and no.name == "conferir_sustentacao":
                checar("`conferir_sustentacao` NAO mexe nas mascaras",
                       "del " not in ast.unparse(no)
                       and ".pop(" not in ast.unparse(no),
                       "ela mede e descreve; quem entrega continua entregando")

        mt = io.open(_componentes.fonte(no_app("engine.py")),
                     encoding="utf-8", errors="replace").read()
        f_b = _funcao(ast.parse(mt), "build_rtstruct")
        checar("`build_rtstruct` chama `conferir_sustentacao`",
               _chama(f_b, "conferir_sustentacao"),
               "o laudo existiria sem chegar a ninguem")
        checar("e a marca vai na observacao, NAO na procedencia",
               f_b is not None
               and any(isinstance(n, ast.Attribute)
                       and n.attr == "ROIObservationDescription"
                       for n in ast.walk(f_b))
               and "ROIGenerationDescription" in mt,
               "escrever por cima da procedencia apaga de qual motor veio")


def checar_quem_cria_job_le_o_log():
    print(chr(10) + "[22] Quem abre um job do motor le o log dele")
    import re as _re
    achou, faltando = 0, []
    for nome in _componentes.nomes("app", RAIZ):
        if not nome.endswith(".py"):
            continue
        txt = _io_ler(_componentes.fonte("app/" + nome, RAIZ))
        asp3 = chr(34) * 3
        apo3 = chr(39) * 3
        codigo = _re.sub(asp3 + ".*?" + asp3, "", txt, flags=_re.S)
        codigo = _re.sub(apo3 + ".*?" + apo3, "", codigo, flags=_re.S)
        codigo = _re.sub("(?m)^[ \t]*#.*$", "", codigo)
        if "_job_new()" not in codigo:
            continue
        achou += 1
        if "drenar_log" not in codigo:
            faltando.append(nome)
    if achou < 2:
        print("  FALHA  esperava ao menos dois modulos abrindo job do motor")
        print("         achei %d -- a checagem perdeu o alvo" % achou)
        return False
    print("  ok     %d modulo(s) abrem job do motor" % achou)
    if faltando:
        print("  FALHA  abre o job e NAO le o batimento: %s"
              % ", ".join(faltando))
        print("         `run_ts_task` bate ponto a cada 10s em _JOBS[jid];")
        print("         sem drenar, a tela fica uma hora sem uma linha e nao")
        print("         ha como distinguir trabalhando de travado.")
        return False
    print("  ok     todos drenam o log do job que abrem")
    mot = _io_ler(_componentes.fonte("app/engine.py", RAIZ))
    if "def drenar_log(" not in mot:
        print("  FALHA  `engine.drenar_log` sumiu -- e o motor e quem escreve")
        return False
    if "class FiltroProgresso(" not in mot:
        print("  FALHA  o filtro que segura a enxurrada saiu de junto do motor")
        return False
    print("  ok     engine.drenar_log e FiltroProgresso moram com quem escreve")
    return True


def checar_variaveis_de_ambiente():
    print("\n[17] Variavel de ambiente definida e variavel lida por alguem")
    lidas, definidas = set(), {}
    alvos = []
    for pasta, d in _componentes.pastas_de(
            ("app", "tools", "installer", "build", "packager"), RAIZ, no_app("")):
        if not os.path.isdir(d):
            continue
        for nome in sorted(os.listdir(d)):
            if nome.endswith((".py", ".ps1", ".cmd", ".bat")):
                alvos.append((pasta, nome, os.path.join(d, nome)))

    for pasta, nome, cam in alvos:
        try:
            txt = io.open(cam, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in re.finditer(r'environ(?:\.get)?[\(\[]\s*["\']'
                             r'(RADAI_[A-Z0-9_]+)["\']', txt):
            lidas.add(m.group(1))
        for m in re.finditer(r'\$env:(RADAI_[A-Z0-9_]+)', txt):
            lidas.add(m.group(1))
        for m in re.finditer(r'%(RADAI_[A-Z0-9_]+)%', txt):
            lidas.add(m.group(1))
        for m in re.finditer(r'(?:environ|env)\[\s*["\']'
                             r'(RADAI_[A-Z0-9_]+)["\']\s*\]\s*=', txt):
            definidas.setdefault(m.group(1), set()).add(
                "%s/%s" % (pasta, nome))
        for m in re.finditer(r'set\s+"(RADAI_[A-Z0-9_]+)=', txt):
            definidas.setdefault(m.group(1), set()).add(
                "%s/%s" % (pasta, nome))
        for m in re.finditer(r'\$env:(RADAI_[A-Z0-9_]+)\s*=', txt):
            definidas.setdefault(m.group(1), set()).add(
                "%s/%s" % (pasta, nome))

    checar("achei variaveis RADAI_* lidas", len(lidas) >= 3,
           ", ".join(sorted(lidas)))
    orfas = sorted(v for v in definidas if v not in lidas)
    for v in orfas:
        checar("`%s` e definida mas ninguem a le" % v, False,
               "definida em %s" % ", ".join(sorted(definidas[v])))
    checar("nenhuma variavel RADAI_* e definida sem leitor", not orfas,
           ", ".join(orfas))

    enc = io.open(os.path.join(RAIZ, "tools", "test_shutdown.py"),
                  encoding="utf-8", errors="replace").read()
    checar("test_shutdown isola o acervo com RADAI_CALIB_DIR",
           "RADAI_CALIB_DIR" in enc,
           "sem isso o fantoma escreve no acervo do operador")
    checar("e nao ATRIBUI mais o nome que ninguem le",
           not re.search(r'env\[\s*["\']RADAI_DADOS["\']\s*\]\s*=', enc),
           "citar no comentario e registro; atribuir e o defeito")


def _getattr_inventados(fontes):
    arvores = {}
    for nome, texto in sorted(fontes.items()):
        if not nome.endswith(".py"):
            continue
        try:
            arvores[nome] = ast.parse(texto)
        except SyntaxError:
            continue
    modulos = dict((nome[:-3], nomes_de_modulo(arv))
                   for nome, arv in arvores.items())
    achados, olhados = [], 0
    for nome, arv in sorted(arvores.items()):
        for no in ast.walk(arv):
            if not (isinstance(no, ast.Call)
                    and getattr(no.func, "id", "") == "getattr"):
                continue
            if len(no.args) < 2:
                continue
            alvo, atrib = no.args[0], no.args[1]
            mod = getattr(alvo, "id", "")
            if mod not in modulos:
                continue
            if not (isinstance(atrib, ast.Constant)
                    and isinstance(atrib.value, str)):
                continue
            olhados += 1
            if atrib.value not in modulos[mod]:
                achados.append("%s linha %d: getattr(%s, %r)"
                               % (nome, no.lineno, mod, atrib.value))
    return achados, olhados


def checar_getattr_de_nome_inventado():
    print("\n[22] `getattr` de nome que existe no modulo")
    fontes = {}
    for nome in _componentes.nomes("app"):
        if nome.endswith(".py"):
            fontes[nome] = io.open(_componentes.fonte("app/" + nome),
                                   encoding="utf-8", errors="replace").read()
    achados, olhados = _getattr_inventados(fontes)
    isca = {"m.py": u"try:\n    from x import mapa as MAPA\n"
                    u"except Exception:\n    MAPA = {}\n"
                    u"import os as _os\nimport a.b\n"
                    u"if _os.name == 'nt':\n    def so_no_windows():\n"
                    u"        pass\nA, (B, *C) = 1, (2, 3)\n",
            "u.py": u"import m\n"
                    u"getattr(m, 'MAPA'); getattr(m, '_os'); getattr(m, 'a')\n"
                    u"getattr(m, 'so_no_windows'); getattr(m, 'C')\n"
                    u"getattr(m, 'INVENTADO')\n"}
    ach_isca, olh_isca = _getattr_inventados(isca)
    checar("  (isca) nome definido no try/except, no if e por import com alias "
           "passa; o inventado reprova",
           olh_isca == 6 and ach_isca == ["u.py linha 4: getattr(m, 'INVENTADO')"],
           "%d olhados: %s" % (olh_isca, ach_isca))

    checar("achei `getattr` sobre modulo do projeto", olhados >= 1, str(olhados))
    for a in achados:
        checar("nome inventado em %s" % a, False)
    checar("todo `getattr` sobre modulo nosso usa nome que EXISTE", not achados,
           "; ".join(achados[:3]))


def checar_rotas_vivas():
    import re as _re
    print("")
    print("[32] Toda rota que a tela chama existe depois de montada")

    app_dir = os.path.join(RAIZ, "app")
    if not os.path.isdir(app_dir):
        print("  ok     (sem app/ nesta arvore)")
        return True
    try:
        import sys as _s
        if app_dir not in _s.path:
            _s.path.insert(0, app_dir)
        from fastapi import FastAPI
        import radai_panel
    except Exception as e:
        print("  ok     PULADO: %s" % str(e)[:80])
        print("         rode a bateria num ambiente com fastapi antes de "
              "empacotar")
        return True

    app = FastAPI()
    try:
        radai_panel.montar(app, ler_vigia=lambda: {},
                            config={"caminho": "x", "chaves": [],
                                    "padroes": {}, "em_uso": {}})
    except Exception as e:
        print("  FALHA  a montagem levantou: %s: %s"
              % (type(e).__name__, str(e)[:120]))
        return False
    vivas = set()
    for r in app.routes:
        vivas.add(getattr(r, "path", ""))

    for extra in ("radai_watcher.py", "radai_shutdown.py", "radai_pulso.py"):
        t = _io_ler(_componentes.fonte("app/" + extra))
        for m in _re.finditer(r'@app\.(?:get|post)\("(/api/[^"]+)"', t):
            vivas.add(m.group(1))
    print("  ok     %d rota(s) registradas" % len(vivas))

    # GUARDA: rota prometida por outro componente que ainda nao a registra; sai daqui quando ela existir (reprova nos dois sentidos).
    de_outra_trilha = {}
    ja_existem = sorted(r for r in de_outra_trilha if r in vivas)
    if ja_existem:
        print("  FALHA  rota(s) na lista de outra trilha que JA existem: %s"
              % ", ".join(ja_existem))
        print("         tire-as de `de_outra_trilha`")
        return False
    vivas = vivas | set(de_outra_trilha)

    ruins = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        t = _io_ler(_componentes.fonte("app/" + nome))
        for m in _re.finditer(r"fetch\(\s*'(/api/[a-zA-Z0-9_/-]+)'", t):
            alvo = m.group(1)
            if alvo not in vivas:
                ruins.append((nome, alvo))
        for m in _re.finditer(r'fetch\(\s*"(/api/[a-zA-Z0-9_/-]+)"', t):
            alvo = m.group(1)
            if alvo not in vivas:
                ruins.append((nome, alvo))
    vistos = set()
    unicos = []
    for x in ruins:
        if x[1] not in vistos:
            vistos.add(x[1])
            unicos.append(x)
    if unicos:
        print("  FALHA  %d rota(s) que a tela chama e o app NAO tem:"
              % len(unicos))
        for n, a in unicos[:10]:
            print("           %-28s %s" % (a, n))
        print("         Escrita no arquivo e registrada no app sao coisas")
        print("         diferentes: uma funcao na coluna errada engole as")
        print("         rotas que vem depois dela, sem erro de sintaxe.")
        return False
    print("  ok     toda rota chamada pelo JavaScript existe no app")

    faltam = [r for r in ("/api/varrer/iniciar", "/api/varrer/estado",
                          "/api/pipeline/iniciar", "/api/fila/estado",
                          "/api/fila/cancelar")
              if r not in vivas]
    if faltam:
        print("  FALHA  o «Rodar agora» esta sem API: %s" % ", ".join(faltam))
        return False
    print("  ok     e o «Rodar agora» tem as rotas dele")
    return True


def _io_ler(caminho):
    import io as _io
    try:
        return _io.open(caminho, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def _funcao_ps(pt, nome):
    i = pt.find("function %s {" % nome)
    if i < 0:
        return ""
    fim = pt.find("\n}", i)
    return pt[i:] if fim < 0 else pt[i:fim]


def _tela_zero_divergente(pt):
    fora = []
    for alvo, porque in (
            ("function AcharInstalacao", "a tela nao procura a instalacao"),
            ("$p.Value.caminho",
             "a busca ignora o `caminho` gravado no registro"),
            ("function MarcaDeInstalacao", "a busca nao resolve por marca"),
            ("$btModo1.Enabled = $true",
             "o botao Instalar / Atualizar nasce apagado quando a busca falha"),
            ("$btModo5.Enabled = $temInst",
             "o botao de desinstalar nao segue a deteccao"),
            ("FolderBrowserDialog",
             "nao ha como apontar a pasta quando a busca nao acha"),
            ("function GarantirInstalacao",
             "os botoes nao pedem a pasta antes de agir"),
            ("$btModo1.Add_Click({ [void](InstalarOuAtualizar) })",
             "o botao Instalar / Atualizar nao passa pela decisao")):
        if alvo not in pt:
            fora.append(porque)
    if "$btModo4" in pt:
        fora.append("a tela 0 voltou a ter o botao de atualizar separado "
                    "($btModo4)")
    dec = _funcao_ps(pt, "InstalarOuAtualizar")
    if not (dec and "ConferirInstalacao" in dec
            and "IniciarAtualizarApp" in dec and "MarcarModo '1'" in dec
            and "GarantirInstalacao" not in dec):
        fora.append("o Instalar / Atualizar nao confere a instalacao no "
                    "clique (ConferirInstalacao), seguindo a cascata com ela "
                    "e instalando tudo (o modo 1) sem ela")
    # GUARDA: o modo 7, a retomada da cascata e o desinstalar agem sobre a pasta instalada e pedem a pasta quando a busca falha.
    n = pt.count("GarantirInstalacao (T ")
    if (n != 3 or "GarantirInstalacao (T " not in _funcao_ps(pt, "MarcarModo")
            or "GarantirInstalacao (T " not in _funcao_ps(
                pt, "RetomarAtualizarApp")):
        fora.append("o modo 7, a retomada da cascata e o desinstalar tem de "
                    "passar por GarantirInstalacao (achei %d chamada(s))" % n)
    return fora


def checar_pacote_leve_completo():
    import io as _io
    import re as _re
    print("")
    print("[31] O pacote leve leva o que o motor de preparo le")

    engine = os.path.join(RAIZ, "build", "configurar_ambiente.py")
    emp = os.path.join(RAIZ, "build", "empacotar_instalador.py")
    if not (os.path.isfile(engine) and os.path.isfile(emp)):
        print("  ok     (sem motor ou sem empacotador nesta arvore)")
        return True
    m = _io.open(engine, encoding="utf-8", errors="replace").read()
    e = _io.open(emp, encoding="utf-8", errors="replace").read()

    lidas = set(_re.findall(r'RAIZ / "([a-z_]+)"', m)) - {"_montagem"}
    if not lidas:
        print("  FALHA  nao achei o que o motor le da raiz (regex vazia?)")
        return False

    levadas = set(_re.findall(r'\(\s*"([a-z_]+)"\s*,\s*"[a-z_]+"\s*\)', e))
    levadas |= set(x.split("/")[0] for x in _re.findall(r'"([a-z_/.-]+)"', e)
                   if "/" in x)
    faltam = sorted(lidas - levadas)
    if faltam:
        print("  FALHA  o motor le %d pasta(s) que o pacote leve nao leva:"
              % len(faltam))
        for f in faltam:
            print("           %s/" % f)
        print("         O preparo aborta no ULTIMO passo, depois de baixar")
        print("         12 GB -- por um arquivo que faltava desde o comeco.")
        return False
    print("  ok     %d pasta(s) lidas pelo motor, todas no pacote: %s"
          % (len(lidas), ", ".join(sorted(lidas))))

    if '"START_HERE.cmd"' not in e:
        print("  FALHA  o START_HERE.cmd nao vai para a raiz do zip")
        return False
    if not os.path.isfile(os.path.join(RAIZ, "packager", "START_HERE.cmd")):
        print("  FALHA  packager/START_HERE.cmd nao existe na arvore")
        return False
    if 'z.write(str(de), "UPDATE.cmd")' in e:
        print("  FALHA  o UPDATE.cmd voltou para a raiz do zip")
        print("         A tela ja descobre se ha instalacao; um segundo")
        print("         clique pede que a pessoa descubra sozinha.")
        return False
    print("  ok     um ponto de entrada na raiz do zip, e so um")

    prep = os.path.join(RAIZ, "packager", "prepare.ps1")
    if os.path.isfile(prep):
        pt = _io.open(prep, encoding="utf-8", errors="replace").read()
        falhas = _tela_zero_divergente(pt)
        for f in falhas:
            print("  FALHA  %s" % f)
        if falhas:
            return False
        print("  ok     a tela procura por registro e por marca, o botao "
              "unico confere a instalacao no clique, e os outros pedem a "
              "pasta quando nao acham")
        iscas = (
            ("o botao unico que nasce apagado sem instalacao",
             pt.replace("$btModo1.Enabled = $true",
                        "$btModo1.Enabled = $temInst")),
            ("o botao unico que pede a pasta em vez de instalar",
             pt.replace("    $inst = ConferirInstalacao\n",
                        "    $inst = GarantirInstalacao (T 'Aponte a pasta')\n")),
            ("o clique do botao unico sem a decisao",
             pt.replace("$btModo1.Add_Click({ [void](InstalarOuAtualizar) })",
                        "$btModo1.Add_Click({ MarcarModo '1' })")),
            ("a tela 0 antiga, com o $btModo4 de atualizar",
             pt.replace("$btModo1.Enabled = $true",
                        "$btModo4.Enabled = $true")),
            ("o desinstalar sem pedir a pasta",
             pt.replace("$inst = GarantirInstalacao (T 'Aponte a pasta do "
                        "programa que voce quer remover')",
                        "$inst = $script:Instalado")))
        for nome, txt in iscas:
            if txt == pt or not _tela_zero_divergente(txt):
                print("  FALHA  (isca) %s passaria na checagem" % nome)
                return False
        print("  ok     (isca) %d versoes erradas da tela 0 reprovam"
              % len(iscas))

    atz = os.path.join(RAIZ, "packager", "UPDATE.ps1")
    if os.path.isfile(atz):
        at = _io.open(atz, encoding="utf-8", errors="replace").read()
        if "$p.Value.caminho" not in at:
            print("  FALHA  o UPDATE.ps1 ignora o `caminho` do registro")
            print("         Montar o caminho pela CHAVE do registro falha")
            print("         quando a pessoa escolhe outro nome de pasta,")
            print("         e foi o que aconteceu em campo em 02/09/2026.")
            return False
        print("  ok     e o UPDATE.ps1 le o caminho gravado")

    for nome in ("UNINSTALL.cmd", "UNINSTALL.ps1"):
        if not os.path.isfile(os.path.join(RAIZ, "installer", nome)):
            print("  FALHA  installer/%s nao existe" % nome)
            return False
        if nome not in m:
            print("  FALHA  a etapa 5 nao copia o %s para o programa" % nome)
            print("         Ele tem de estar ONDE a pessoa procura: dentro")
            print("         da pasta que ela quer remover.")
            return False
    print("  ok     o desinstalador viaja e e copiado para o programa")
    return True


def _marca_canonica_da_capa(fonte):
    import xml.etree.ElementTree as ET
    try:
        arv = ast.parse(fonte)
        funcao = next(n for n in arv.body
                      if isinstance(n, ast.FunctionDef) and n.name == "marca")
        retornos = [n for n in ast.walk(funcao) if isinstance(n, ast.Return)]
        if len(retornos) != 1:
            return None
        html = ast.literal_eval(retornos[0].value)
        marca = ET.fromstring(html)
        nome = marca.find("./span[@class='rc-nome']")
        gradiente = None if nome is None else nome.find("./span[@class='g']")
        if (marca.tag != "a" or marca.get("class") != "rc-marca"
                or marca.get("href") != "/" or marca.get("title") != "Local Suite"
                or len(marca) != 1 or nome is None or len(nome) != 1
                or (nome.text or "").strip() != "Local"
                or gradiente is None or len(gradiente) != 0
                or (gradiente.text or "") != "Suite"
                or " ".join("".join(marca.itertext()).split()) != "Local Suite"):
            return None
        return html
    except (SyntaxError, ValueError, TypeError, StopIteration, ET.ParseError):
        return None


def checar_marca_unica():
    import io as _io
    import re as _re
    print("")
    print("[30] A marca e uma so em toda tela")

    capa = _componentes.fonte("app/radai_cover.py")
    if not os.path.isfile(capa):
        print("  ok     (sem radai_cover nesta arvore)")
        return True

    fonte = _io.open(capa, encoding="utf-8", errors="replace").read()
    canonica = _marca_canonica_da_capa(fonte)
    if canonica is None:
        print("  FALHA  marca() precisa devolver o link Local Suite, com rc-nome")
        print("         e gradiente somente em Suite; o retorno deve ser literal.")
        return False

    gancho = 'class="rc-nome"'
    ok = True
    ruins = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py") or nome == "radai_cover.py":
            continue
        t = _io.open(_componentes.fonte("app/" + nome),
                     encoding="utf-8", errors="replace").read()
        for achado in _re.finditer(r'<(?:a|span)\s+class="rc-marca"', t):
            trecho = t[achado.start():achado.start() + 260]
            if gancho not in trecho:
                linha = t[:achado.start()].count("\n") + 1
                ruins.append((nome, linha, trecho[:90]))
    if ruins:
        print("  FALHA  %d marca(s) sem o `%s` de dentro:" % (len(ruins), gancho))
        for n, l, tr in ruins[:8]:
            print("           %s:%d  %s" % (n, l, tr))
        print("         Sem esse gancho a folha nao alcanca o texto, e o")
        print("         cabecalho abre com a fonte da pagina. A marca boa e:")
        print("           %s" % canonica[:100])
        ok = False
    else:
        print("  ok     toda marca a mao tem o `rc-nome` que a folha procura")

    velhos = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        t = _io.open(_componentes.fonte("app/" + nome),
                     encoding="utf-8", errors="replace").read()
        if '<span class="g">Contorno RT</span>' in t:
            velhos.append(nome)
    if velhos:
        print("  FALHA  a marca velha (Auto Contorno RT) ainda esta em: %s"
              % ", ".join(velhos))
        ok = False
    else:
        print("  ok     nenhuma tela carrega a marca de antes de 26/08/2026")
    return ok


def checar_lancador_acha_o_pacote():
    import io as _io
    import re as _re
    print("")
    print("[29] O lancador leve entende os dois layouts")

    lan = os.path.join(RAIZ, "packager", "START_HERE.cmd")
    emp = os.path.join(RAIZ, "build", "empacotar_instalador.py")
    pub = os.path.join(RAIZ, "publicar.cmd")
    if not os.path.isfile(lan):
        print("  ok     (sem lancador nesta arvore)")
        return True
    t = _io.open(lan, encoding="utf-8", errors="replace").read()
    B = chr(92)
    ok = True

    layouts = {}
    if os.path.isfile(emp):
        e = _io.open(emp, encoding="utf-8", errors="replace").read()
        m = _re.search(r'\(\s*"packager"\s*,\s*"([^"]*)"\s*\)', e)
        dentro = m.group(1) if m else None
        if dentro is None:
            print("  FALHA  nao achei onde o empacotar_instalador poe o "
                  "packager/")
            ok = False
        else:
            layouts["empacotar_instalador.py"] = (
                "" if dentro == "packager" else dentro.split("/")[0] + B)
    if os.path.isfile(pub):
        p = _io.open(pub, encoding="utf-8", errors="replace").read()
        if ("%PREP%" + B + "programa" + B) in p:
            layouts["publicar.cmd"] = "programa" + B
        elif "%PREP%" + B in p:
            layouts["publicar.cmd"] = ""
    if not layouts:
        print("  FALHA  nao achei empacotador nenhum para comparar")
        return False

    if ":achar_sub" not in t:
        print("  FALHA  o lancador nao tem :achar_sub -- ele supoe um layout")
        print("         Os dois circulam. Ver o cabecalho deste guarda.")
        return False

    for quem, pref in sorted(layouts.items()):
        if pref and ("SUB=" + pref) not in t:
            print("  FALHA  o %s grava em `%s` e o lancador nao conhece esse"
                  % (quem, pref))
            print("         prefixo (`set \"SUB=%s\"` nao esta la)" % pref)
            ok = False
        else:
            print("  ok     %-28s grava em `%s`, e o lancador conhece"
                  % (quem, pref or "(raiz)"))

    cravadas = []
    for m in _re.finditer(r"%(AQUI|CASA)%" + _re.escape(B)
                          + r"(?!%SUB_)([A-Za-z_0-9.%" + _re.escape(B)
                          + r"-]+)", t):
        alvo = m.group(2)
        if alvo.lower().endswith((".ps1", ".py")) and "%" not in alvo:
            cravadas.append("%" + m.group(1) + "%" + B + alvo)
    if cravadas:
        print("  FALHA  %d caminho(s) com o layout cravado:" % len(cravadas))
        for c in sorted(set(cravadas)):
            print("           %s" % c)
        print("         Componha com %SUB_AQUI% / %SUB_CASA%, que a rotina")
        print("         :achar_sub preenche a partir do que existe no disco.")
        ok = False
    else:
        print("  ok     nenhuma composicao com o layout cravado")

    ent = os.path.join(RAIZ, "entrega.txt")
    if os.path.isfile(ent) and "PRODUTO" in _io.open(
            ent, encoding="utf-8-sig", errors="replace").read():
        if "RADIOTERAPIA_AI_LOCAL_SUITE" not in t:
            print("  FALHA  o lancador nao procura o nome do produto no .zip")
            ok = False
        elif "_v*.zip" not in t:
            print("  FALHA  a busca do .zip e por nome exato -- ela envelhece")
            print("         a cada versao. Procure por padrao.")
            ok = False
        else:
            print("  ok     e procura o pacote por padrao, pelo nome do "
                  "produto")
    return ok


def checar_cmd_chama_o_que_embarca():
    import io as _io
    import re as _re
    print("")
    print("[28] `.cmd` chama arquivo que embarca")
    d = os.path.join(RAIZ, "app")
    if not os.path.isdir(d):
        return True
    CODIGO = (".cmd", ".ps1", ".py")
    faltando = []
    vistos = 0
    for nome in sorted(os.listdir(d)):
        if not nome.lower().endswith(".cmd"):
            continue
        t = _io.open(os.path.join(d, nome), encoding="utf-8",
                     errors="replace").read()
        for ref in _re.findall(r"%~dp0([A-Za-z_0-9.\-]+)", t):
            if not ref.lower().endswith(CODIGO):
                continue
            vistos += 1
            achou = os.path.isfile(os.path.join(d, ref))
            if not achou:
                for sub in sorted(os.listdir(d)):
                    p_sub = os.path.join(d, sub)
                    if os.path.isdir(p_sub) and sub != "__pycache__" \
                            and os.path.isfile(os.path.join(p_sub, ref)):
                        achou = True
                        break
            if not achou:
                faltando.append((nome, ref, "nao existe em app/ nem em subpasta"))
    if faltando:
        print("  FALHA  %d chamada(s) para arquivo ausente:" % len(faltando))
        for a, b, pq in faltando:
            print("           %s chama %s  (%s)" % (a, b, pq))
        return False
    print("  ok     %d chamada(s) entre `.cmd`, todas resolvem em app/"
          % vistos)

    emp = os.path.join(RAIZ, "build", "configurar_ambiente.py")
    if not os.path.isfile(emp):
        print("  ok     (sem empacotador nesta arvore)")
        return True
    fonte = _io.open(emp, encoding="utf-8", errors="replace").read()
    tem_glob = 'glob("*.cmd")' in fonte
    if not tem_glob:
        print("  FALHA  o empacotador nao leva `app/*.cmd` por glob.")
        print("         Lista a mao ao lado de um glob e a metade que")
        print("         envelhece -- foi assim que o open_browser.cmd ficou")
        print("         de fora por dois dias.")
        return False
    print("  ok     o empacotador leva `app/*.cmd` por glob")

    LANCADOR = "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"
    if not os.path.isfile(os.path.join(d, LANCADOR)):
        print("  FALHA  falta app/%s (o alvo do atalho)" % LANCADOR)
        return False
    if LANCADOR not in fonte:
        print("  FALHA  %s nao esta entre os `obrigatorios` do empacotador."
              % LANCADOR)
        print("         Ele e o alvo do atalho: depender so do glob deixa a")
        print("         unica coisa que a pessoa clica sem guarda que aborte.")
        return False
    print("  ok     %s e obrigatorio no empacotador" % LANCADOR)

    inst = os.path.join(RAIZ, "installer", "INSTALL.ps1")
    if os.path.isfile(inst):
        ps = _io.open(inst, encoding="utf-8", errors="replace").read()
        if LANCADOR not in ps:
            print("  FALHA  o INSTALL.ps1 nao aponta o atalho para %s"
                  % LANCADOR)
            return False
        print("  ok     o atalho aponta para %s" % LANCADOR)
        if "Radioterapia.ai Local Suite.lnk" not in ps:
            print("  FALHA  o atalho nao usa o nome do produto")
            return False
        print("  ok     e o atalho leva o nome do produto")
    return True


def checar_acervo_isolado_nas_baterias():
    import io as _io
    print("")
    print("[26] Bateria que alcanca o acervo isola o acervo")
    d = os.path.join(RAIZ, "tools")
    if not os.path.isdir(d):
        return True
    ALCANCA = ("radai_dicom", "radai_archive", "radai_watcher")
    faltando = []
    olhadas = 0
    for nome in _componentes.nomes("tools", RAIZ):
        if not (nome.startswith("test_") and nome.endswith(".py")):
            continue
        t = _io.open(_componentes.fonte("tools/" + nome, RAIZ), encoding="utf-8",
                     errors="replace").read()
        if not any(m in t for m in ALCANCA):
            continue
        olhadas += 1
        if "RADAI_CALIB_DIR" not in t:
            faltando.append(nome)
    if faltando:
        print("  FALHA  %d bateria(s) alcancam o acervo e NAO o isolam:"
              % len(faltando))
        for n in faltando:
            print("           %s" % n)
        print("         Ponha `os.environ[\"RADAI_CALIB_DIR\"] = "
              "tempfile.mkdtemp(...)` no topo.")
        return False
    print("  ok     %d bateria(s) alcancam o acervo, e as %d isolam"
          % (olhadas, olhadas))
    return True


def _vigias_filhos_sem_localappdata(fonte, nome=u"?", chave="LOCALAPPDATA"):
    try:
        arv = ast.parse(fonte)
    except SyntaxError as e:
        return 0, [u"%s nao compila: %s" % (nome, e)]
    herda_do_topo = chave != "LOCALAPPDATA" and any(
        isinstance(no, ast.Assign) and any(
            isinstance(a, ast.Subscript) and isinstance(a.slice, ast.Constant)
            and a.slice.value == chave
            and isinstance(a.value, ast.Attribute) and a.value.attr == "environ"
            for a in no.targets)
        for no in arv.body)
    pai = {}
    for no in ast.walk(arv):
        for filho in ast.iter_child_nodes(no):
            pai[filho] = no

    def funcao_de(no):
        while no in pai:
            no = pai[no]
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return no
        return arv

    def dict_com_lad(v):
        return (isinstance(v, ast.Call)
                and getattr(v.func, "id", None) == "dict"
                and any(k.arg == chave for k in v.keywords))

    def troca_lad(escopo, nome_env):
        for no in ast.walk(escopo):
            if not isinstance(no, ast.Assign):
                continue
            for alvo in no.targets:
                if (isinstance(alvo, ast.Name) and alvo.id == nome_env
                        and dict_com_lad(no.value)):
                    return True
                if (isinstance(alvo, ast.Subscript)
                        and isinstance(alvo.value, ast.Name)
                        and alvo.value.id == nome_env
                        and isinstance(alvo.slice, ast.Constant)
                        and alvo.slice.value == chave):
                    return True
        return False

    achadas, defeitos = 0, []
    for no in ast.walk(arv):
        if not (isinstance(no, ast.Call)
                and (getattr(no.func, "attr", None)
                     or getattr(no.func, "id", None)) == "Popen"
                and no.args):
            continue
        sobe_o_vigia = any(isinstance(c, ast.Constant)
                           and isinstance(c.value, str)
                           and c.value.endswith("radai_watcher.py")
                           for c in ast.walk(no.args[0]))
        if not sobe_o_vigia:
            continue
        achadas += 1
        env = [k.value for k in no.keywords if k.arg == "env"]
        onde = u"%s:%d" % (nome, getattr(no, "lineno", 0))
        if not env:
            defeitos.append(u"%s sobe o vigia sem `env=` (herda a "
                            u"%s de quem roda)" % (onde, chave))
            continue
        v = env[0]
        if herda_do_topo or dict_com_lad(v):
            continue
        if isinstance(v, ast.Name) and troca_lad(funcao_de(no), v.id):
            continue
        defeitos.append(u"%s sobe o vigia com um ambiente que nao troca a "
                        u"%s" % (onde, chave))
    return achadas, defeitos


def checar_vigia_filho_isola_localappdata():
    import io as _io
    print(NL + "[26b] Bateria que sobe o vigia isola a LOCALAPPDATA e o "
          "registro de casos do filho")
    d = os.path.join(RAIZ, "tools")
    if not os.path.isdir(d):
        return True
    total, baterias, defeitos, defeitos_reg = 0, 0, [], []
    fonte_shutdown = u""
    for nome in _componentes.nomes("tools", RAIZ):
        if not (nome.startswith("test_") and nome.endswith(".py")):
            continue
        t = _io.open(_componentes.fonte("tools/" + nome, RAIZ), encoding="utf-8",
                     errors="replace").read()
        if nome == "test_shutdown.py":
            fonte_shutdown = t
        n, dd = _vigias_filhos_sem_localappdata(t, nome)
        if n:
            baterias += 1
        total += n
        defeitos.extend(dd)
        defeitos_reg.extend(_vigias_filhos_sem_localappdata(
            t, nome, "RADAI_REGISTRO_DIR")[1])
    checar(u"toda bateria que sobe o vigia isola o registro de casos do filho "
           u"(RADAI_REGISTRO_DIR; senao a chave do pseudonimo e o caso em "
           u"andamento vao para o app\\registro da oficina, que sincroniza)",
           not defeitos_reg, u"; ".join(defeitos_reg[:6]))
    sem_reg = u"".join(
        ln for ln in fonte_shutdown.splitlines(True)
        if u"RADAI_REGISTRO_DIR" not in ln)
    checar(u"  (isca) o test_shutdown sem o RADAI_REGISTRO_DIR do filho, a "
           u"checagem acusa",
           sem_reg != fonte_shutdown and bool(_vigias_filhos_sem_localappdata(
               sem_reg, u"isca", "RADAI_REGISTRO_DIR")[1]))
    herda = (u"import os, subprocess, sys\n"
             u"os.environ['RADAI_REGISTRO_DIR'] = 'x'\n"
             u"def f():\n"
             u"    subprocess.Popen([sys.executable, 'app/radai_watcher.py'],\n"
             u"                     env=dict(os.environ, LOCALAPPDATA='y'))\n")
    sem_topo = herda.replace(u"os.environ['RADAI_REGISTRO_DIR'] = 'x'\n", u"")
    checar(u"  o registro isolado no topo da bateria vale para o filho que "
           u"herda o ambiente; (isca) sem ele, a checagem acusa",
           not _vigias_filhos_sem_localappdata(
               herda, u"herda", "RADAI_REGISTRO_DIR")[1]
           and bool(_vigias_filhos_sem_localappdata(
               sem_topo, u"isca3", "RADAI_REGISTRO_DIR")[1]))
    checar(u"achei as baterias que sobem o vigia de verdade (%d chamada(s) "
           u"em %d bateria(s))" % (total, baterias),
           total >= 5 and baterias >= 4)
    checar(u"toda bateria que sobe o vigia troca a LOCALAPPDATA do filho "
           u"(senao ele grava e apaga o em_uso.json de quem roda)",
           not defeitos, u"; ".join(defeitos[:6]))
    linhas = fonte_shutdown.splitlines(True)
    forjada = u"".join(
        ln for ln in linhas
        if not (u"LOCALAPPDATA" in ln and ln.lstrip().startswith(u"env[")))
    checar(u"  (isca) o test_shutdown sem a troca da LOCALAPPDATA, a "
           u"checagem acusa",
           forjada != fonte_shutdown and bool(
               _vigias_filhos_sem_localappdata(forjada, u"isca")[1]))
    isca2 = (u"import subprocess, sys\n"
             u"def f():\n"
             u"    subprocess.Popen([sys.executable, 'app/radai_watcher.py'])\n")
    n2, d2 = _vigias_filhos_sem_localappdata(isca2, u"isca2")
    checar(u"  (isca) um Popen do vigia sem `env=`, a checagem acusa",
           n2 == 1 and bool(d2))


def checar_limpeza_das_baterias():
    print("\n[21] Bateria que cria pasta temporaria declara a limpeza")
    cria = re.compile(r"mkdtemp\s*\(\s*prefix\s*=\s*[\"']([^\"']+)[\"']")
    cria2 = re.compile(r"novo_temp\s*\(\s*[\"']([^\"']+)[\"']")
    declara = re.compile(r"adotar_prefixo\s*\(\s*[\"']([^\"']+)[\"']")

    d = os.path.join(RAIZ, "tools")
    faltando, n_bat, fontes = [], 0, {}
    for nome in _componentes.nomes("tools", RAIZ):
        if not (nome.startswith("test_") and nome.endswith(".py")):
            continue
        txt = io.open(_componentes.fonte("tools/" + nome, RAIZ), encoding="utf-8",
                      errors="replace").read()
        fontes[nome] = txt
        criados = set(cria.findall(txt)) | set(cria2.findall(txt))
        if not criados:
            continue
        n_bat += 1
        declarados = set(declara.findall(txt))
        for c in sorted(criados):
            if not any(c.startswith(x) for x in declarados):
                faltando.append("%s: `%s`" % (nome, c))

    checar("achei baterias que criam pasta temporaria", n_bat >= 15, str(n_bat))
    for f in faltando:
        checar("prefixo criado e nao declarado em %s" % f, False)
    checar("toda pasta temporaria criada tem limpeza declarada", not faltando,
           "; ".join(faltando[:3]))
    sem_prefixo = [a for a in _temporarias_fora_da_faxina(fontes)
                   if a.endswith(":")]
    checar("nenhuma bateria cria pasta temporaria sem prefixo (sem ele nem a "
           "limpeza da bateria nem a faxina a reconhecem)", not sem_prefixo,
           "; ".join(sem_prefixo[:4]))
    isca = {"test_isca.py": u"import tempfile\na = tempfile.mkdtemp()\n"
                            u"b = tempfile.mkdtemp(prefix='radai_ok_')\n"}
    checar("  (isca) o `mkdtemp()` sem prefixo e acusado, e o com prefixo nao",
           [a for a in _temporarias_fora_da_faxina(isca) if a.endswith(":")]
           == ["test_isca.py:"], str(_temporarias_fora_da_faxina(isca)))

    aj = os.path.join(d, "_cleanup.py")
    checar("`tools/_cleanup.py` existe", os.path.isfile(aj))
    if os.path.isfile(aj):
        t = io.open(aj, encoding="utf-8", errors="replace").read()
        checar("e ele usa `atexit` (roda tambem quando a bateria FALHA)",
               "atexit.register" in t)
        checar("e so apaga pasta criada DEPOIS do inicio desta execucao",
               "getctime" in t,
               "sem isso, duas baterias em paralelo se atrapalham")
        def _varrer_consulta(fonte):
            try:
                arv = ast.parse(fonte)
            except SyntaxError:
                return False, False
            for no in ast.walk(arv):
                if isinstance(no, ast.FunctionDef) and no.name == "_varrer":
                    chamadas = set(getattr(c.func, "id", "")
                                   for c in ast.walk(no)
                                   if isinstance(c, ast.Call))
                    return ("_outras_execucoes" in chamadas,
                            "_pode_ser_de" in chamadas)
            return False, False
        _cad, _pode = _varrer_consulta(t)
        checar("e `_varrer` consulta o cadastro das execucoes vivas "
               "(`_outras_execucoes`) e pergunta por pasta (`_pode_ser_de`)",
               _cad and _pode, "cadastro=%s por_pasta=%s" % (_cad, _pode))
        _isca = _varrer_consulta(t.replace(
            "_outras_execucoes(bases) if candidatas else []", "[]"))
        checar("  (isca) sem a consulta ao cadastro, a leitura acusa",
               not _isca[0], str(_isca))


PREFIXO_DA_FAXINA = "radai_"
PENDENTES_DA_FAXINA = {}


def _temporarias_fora_da_faxina(fontes):
    achados = []
    for nome, texto in sorted(fontes.items()):
        try:
            arv = ast.parse(texto)
        except SyntaxError:
            continue
        consts = {}
        for no in arv.body:
            if (isinstance(no, ast.Assign) and isinstance(no.value, ast.Constant)
                    and isinstance(no.value.value, str)):
                for alvo in no.targets:
                    if isinstance(alvo, ast.Name):
                        consts[alvo.id] = no.value.value
        for no in ast.walk(arv):
            if not isinstance(no, ast.Call):
                continue
            f = no.func
            if (f.attr if isinstance(f, ast.Attribute)
                    else getattr(f, "id", "")) != "mkdtemp":
                continue
            kw = dict((k.arg, k.value) for k in no.keywords if k.arg)
            if "dir" in kw or len(no.args) >= 3:
                continue
            p = kw.get("prefix", no.args[1] if len(no.args) >= 2 else None)
            if p is None:
                valor = ""
            elif isinstance(p, ast.Constant) and isinstance(p.value, str):
                valor = p.value
            elif isinstance(p, ast.Name) and p.id in consts:
                valor = consts[p.id]
            else:
                continue
            if not valor.startswith(PREFIXO_DA_FAXINA):
                achados.append("%s:%s" % (nome, valor))
    return achados


def checar_temporarias_do_app_na_faxina():
    print("\n[21c] Pasta temporaria que o app cria cai na faxina do arranque")
    try:
        vigia = io.open(_componentes.fonte("app/radai_watcher.py", RAIZ),
                        encoding="utf-8", errors="replace").read()
    except Exception:
        vigia = ""
    checar("a faxina do arranque varre `%s*` (radai_watcher.limpar_temporarios)"
           % PREFIXO_DA_FAXINA,
           ('glob("%s*")' % PREFIXO_DA_FAXINA) in vigia)
    fontes = _fontes_do_app()
    achados = set(_temporarias_fora_da_faxina(fontes))
    novos = sorted(achados - set(PENDENTES_DA_FAXINA))
    checar("toda pasta temporaria do app comeca por `%s` (%d arquivo(s) lidos)"
           % (PREFIXO_DA_FAXINA, len(fontes)), not novos and len(fontes) > 50,
           "; ".join(novos))
    for k, motivo in sorted(PENDENTES_DA_FAXINA.items()):
        print("  PENDENTE  %s -- %s" % (k, motivo))
    consertados = sorted(set(PENDENTES_DA_FAXINA) - achados)
    checar("  e nenhuma pendencia declarada ja foi consertada (tire-a da "
           "lista PENDENTES_DA_FAXINA)", not consertados, "; ".join(consertados))
    isca = {"x.py": u"import tempfile\nP = 'tmp_'\n"
                    u"a = tempfile.mkdtemp()\nb = tempfile.mkdtemp(prefix=P)\n"
                    u"c = tempfile.mkdtemp(prefix='radai_ok_')\n"
                    u"d = tempfile.mkdtemp(prefix='z', dir='q')\n"}
    checar("  (isca) sem prefixo e com prefixo fora da faxina sao acusados; "
           "`radai_` e `dir=` passam",
           sorted(_temporarias_fora_da_faxina(isca)) == ["x.py:", "x.py:tmp_"],
           str(_temporarias_fora_da_faxina(isca)))


def checar_chaves_repetidas():
    print("\n[20] Nenhum literal de dicionario com chave repetida")
    total, achados = 0, []
    for pasta, d in _componentes.pastas_de(("app", "tools", "build"), RAIZ, no_app("")):
        if not os.path.isdir(d):
            continue
        for nome in sorted(os.listdir(d)):
            if not nome.endswith(".py"):
                continue
            cam = os.path.join(d, nome)
            try:
                arv = ast.parse(io.open(cam, encoding="utf-8",
                                        errors="replace").read())
            except SyntaxError:
                continue
            for no in ast.walk(arv):
                if not isinstance(no, ast.Dict):
                    continue
                ks = [k.value for k in no.keys
                      if isinstance(k, ast.Constant)
                      and isinstance(k.value, (str, int))]
                if len(ks) < 2:
                    continue
                total += 1
                vistas, rep = set(), []
                for k in ks:
                    if k in vistas:
                        rep.append(k)
                    vistas.add(k)
                if rep:
                    achados.append("%s/%s linha %d: %s"
                                   % (pasta, nome, no.lineno,
                                      ", ".join(repr(r) for r in sorted(set(rep)))))
    checar("achei literais de dicionario para conferir", total >= 20, str(total))
    for a in achados:
        checar("chave repetida em %s" % a, False)
    checar("nenhum literal tem chave repetida", not achados,
           "; ".join(achados[:3]))


def checar_guarda_de_multiprocessing():
    print("\n[19] Script gerado que cria processo tem o guarda `__main__`")
    CRIAM_PROCESSO = ("predict_from_files", "multiprocessing", "ProcessPool",
                      "Pool(", "num_processes")
    achou_algum = False
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        txt = io.open(_componentes.fonte(no_app(nome)), encoding="utf-8",
                      errors="replace").read()
        for m in re.finditer(r"(?ms)^(_?[A-Z_]*(?:SCRIPT|RUNNER)[A-Z_]*)\s*=\s*"
                             r"r?('''|\"\"\")(.*?)\2", txt):
            var, corpo = m.group(1), m.group(3)
            if not any(c in corpo for c in CRIAM_PROCESSO):
                continue
            achou_algum = True
            checar("%s/%s cria processo e TEM o guarda `__main__`"
                   % (nome, var),
                   'if __name__ == "__main__"' in corpo
                   or "if __name__ == '__main__'" in corpo,
                   "sem ele o filho re-importa e TRAVA no Windows")
            checar("%s/%s chama freeze_support()" % (nome, var),
                   "freeze_support()" in corpo,
                   "e o que faz o filho re-importado SAIR")
    checar("achei ao menos um script gerado que cria processo", achou_algum,
           "se nao ha nenhum, esta checagem nao esta olhando o lugar certo")


def _modulos_alcancados(fontes_app, raizes):
    nomes = set(fontes_app)
    arestas = {}
    for m, txt in fontes_app.items():
        d = set()
        try:
            arv = ast.parse(txt)
        except SyntaxError:
            arv = None
        for no in (ast.walk(arv) if arv is not None else ()):
            if isinstance(no, ast.Import):
                d.update(a.name.split(".")[0] for a in no.names)
            elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
                d.add(no.module.split(".")[0])
            elif isinstance(no, ast.Constant) and isinstance(no.value, str):
                d.update(re.findall(r"\b(radai_\w+|engine)\b", no.value))
        arestas[m] = d & nomes
    vistos, pilha = set(), [r for r in raizes if r in nomes]
    while pilha:
        m = pilha.pop()
        if m in vistos:
            continue
        vistos.add(m)
        pilha.extend(arestas.get(m, ()))
    return vistos


def _imports_de(txt):
    try:
        arv = ast.parse(txt)
    except SyntaxError:
        return set()
    fora = set()
    for no in ast.walk(arv):
        if isinstance(no, ast.Import):
            fora.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
            fora.add(no.module.split(".")[0])
    return fora


ENTRADAS_DO_APP = ("radai_watcher", "radai_lancador")


def checar_modulos_mortos():
    print("\n[18] Modulo de app/ que nenhuma entrada alcanca")
    fontes_app = {}
    for nome in _componentes.nomes("app"):
        if nome.endswith(".py") and not nome.startswith("__"):
            fontes_app[nome[:-3]] = io.open(_componentes.fonte(no_app(nome)),
                                            encoding="utf-8",
                                            errors="replace").read()
    raizes = set(ENTRADAS_DO_APP)
    for pasta in ("build",):
        d = os.path.join(RAIZ, pasta)
        for nome in sorted(os.listdir(d)) if os.path.isdir(d) else ():
            if nome.endswith(".py"):
                raizes |= _imports_de(io.open(os.path.join(d, nome),
                                              encoding="utf-8",
                                              errors="replace").read())
    for d in _componentes.pastas("app", RAIZ):
        for atual, _dirs, arqs in os.walk(d):
            for nome in arqs:
                if nome.lower().endswith((".cmd", ".bat")):
                    raizes |= set(re.findall(
                        r"\b(radai_\w+)\.py\b",
                        io.open(os.path.join(atual, nome), encoding="utf-8",
                                errors="replace").read()))
    vivos = _modulos_alcancados(fontes_app, raizes)
    orfaos = sorted(set(fontes_app) - vivos)
    checar("achei modulos em app/ e as entradas (%s)"
           % ", ".join(ENTRADAS_DO_APP),
           len(fontes_app) > 20 and all(e in vivos for e in ENTRADAS_DO_APP),
           "%d modulo(s)" % len(fontes_app))
    for m in orfaos:
        checar("`%s` nao e alcancado pelo vigia, pelo lancador nem pelo "
               "preparo" % m, False,
               "modulo morto: so uma bateria o importa, ou ninguem")
    checar("nenhum modulo de app/ esta morto", not orfaos, ", ".join(orfaos))
    isca = {"radai_watcher": u"import radai_a" + NL,
            "radai_a": u"x = 1" + NL,
            "radai_b": u"import radai_c" + NL,
            "radai_c": u"y = 2" + NL}
    checar("  (isca) a corrente que so se importa entre si e acusada",
           sorted(set(isca) - _modulos_alcancados(isca, ENTRADAS_DO_APP))
           == ["radai_b", "radai_c"])
    isca["radai_a"] = u'M = ("radai_b",)' + NL
    checar("  (isca) o nome numa lista de __import__ conta como uso",
           _modulos_alcancados(isca, ENTRADAS_DO_APP) == set(isca))


def checar_licenca_de_todo_modelo():
    print("\n[24] Licenca de todo modelo que vai no pacote")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import radai_models as V
    import artefatos as A

    FRAGMENTO = {
        "totalsegmentator": "totalsegmentator",
        "vista3d_monai": "vista-3d",
        "nv_segment_ct": "nv-segment",
        "cads_open": "cads",
        "nninteractive": "nninteractive",
        "hnlnl": "linfonodais",
        "moose": "moose",
        "cranio_buti": "buti",
    }
    textos = [(l["componente"], l["licenca"], bool(l["restritiva"]))
              for l in A.LICENCAS]
    checar("achei a tabela de licencas do preparador", len(textos) >= 6,
           "%d componente(s)" % len(textos))

    sem_fragmento = [i for i in V.MODELOS if i not in FRAGMENTO]
    checar("todo modelo do registro tem fragmento nesta checagem",
           not sem_fragmento,
           ("sem fragmento: %s" % ", ".join(sem_fragmento))
           if sem_fragmento else "%d modelo(s)" % len(V.MODELOS))

    for ident, m in V.MODELOS.items():
        frag = FRAGMENTO.get(ident)
        if not frag:
            continue
        casam = [t for t in textos if frag in t[0].lower()]
        checar("`%s` aparece na tela de licencas" % ident, bool(casam),
               casam[0][1] if casam else ("nada casa com %r" % frag))
        if not casam:
            continue
        if m.get("uso_permitido") == "nao_comercial":
            checar("`%s` esta marcado como restritivo na tela" % ident,
                   any(r for _c, _l, r in casam),
                   "uso_permitido=nao_comercial")

    ps = ler(os.path.join("packager", "prepare.ps1"))
    bloco = ps.split("$script:Licencas = @(", 1)
    checar("achei a tabela de licencas do prepare.ps1", len(bloco) == 2)
    if len(bloco) == 2:
        corpo = bloco[1].split("\n)", 1)[0]
        no_ps_v = re.findall(
            r"componente\s*=\s*'((?:[^']|'')+)'\s*;\s*versao\s*=\s*'([^']*)'\s*;"
            r"\s*licenca\s*=\s*'([^']*)'\s*;\s*restritiva\s*=\s*\$(true|false)",
            corpo)
        no_ps = [(c.replace("''", "'"), l, r == "true")
                 for c, _v, l, r in no_ps_v]

        req = ler("build/requirements-demo.txt")
        m_pin = re.search(r"TotalSegmentator\s*==\s*([0-9][0-9.]*)", req)
        ps_ts = [v for c, v, _l, _r in no_ps_v
                 if c.strip().lower() == "totalsegmentator"]
        checar("o prepare.ps1 nomeia o TotalSegmentator", len(ps_ts) == 1,
               str(ps_ts))
        if m_pin and len(ps_ts) == 1:
            checar("e declara a MESMA versao que o pino",
                   ps_ts[0].strip() == m_pin.group(1),
                   "prepare.ps1=%s, requirements-demo=%s"
                   % (ps_ts[0], m_pin.group(1)))

        checar("as duas tabelas tem o mesmo numero de componentes",
               len(no_ps) == len(textos),
               "artefatos.py=%d, prepare.ps1=%d" % (len(textos), len(no_ps)))
        so_py = sorted(set((l, r) for _c, l, r in textos)
                       - set((l, r) for _c, l, r in no_ps))
        so_ps = sorted(set((l, r) for _c, l, r in no_ps)
                       - set((l, r) for _c, l, r in textos))
        checar("nenhuma licenca so no artefatos.py", not so_py, str(so_py))
        checar("nenhuma licenca so no prepare.ps1", not so_ps, str(so_ps))
        n_restr_py = sum(1 for _c, _l, r in textos if r)
        n_restr_ps = sum(1 for _c, _l, r in no_ps if r)
        checar("as duas contam as mesmas licencas restritivas",
               n_restr_py == n_restr_ps,
               "artefatos.py=%d, prepare.ps1=%d" % (n_restr_py, n_restr_ps))

    m_ps = re.search(r"\$somaEsperada\s*=\s*'([0-9a-fA-F]{64})'", ps)
    checar("o prepare.ps1 confere a soma do Python que ele vai executar",
           bool(m_ps), "sem `$somaEsperada` -- so o tamanho era validado")
    if m_ps:
        try:
            esperado_py = A.ARTEFATOS["cache/python-embed.zip"]["sha256"]
        except Exception:
            esperado_py = ""
        checar("e a soma bate com a de `build/artefatos.py`",
               m_ps.group(1).lower() == (esperado_py or "").lower(),
               "prepare.ps1=%s, artefatos.py=%s"
               % (m_ps.group(1)[:16], (esperado_py or "?")[:16]))


def checar_dado_de_literatura_embarcado():
    print("\n[25] Dado de literatura que o app le em execucao")
    if OF is None:
        _componentes.pulado(u"[25] a pasta de literatura da oficina")
        return
    OF.checar_dado_de_literatura_embarcado(sys.modules[__name__])


def _medir_tamanhos_declarados(V, modelos, pasta_de):
    redondos, divergentes, medidos = [], [], 0
    for ident, m in modelos.items():
        d = pasta_de(ident)
        for chave in ("arquivos", "volumes"):
            for rel, tam in (m.get(chave) or []):
                if tam is None:
                    continue
                medidos += 1
                if int(tam) % 10000 == 0:
                    redondos.append("%s/%s = %d" % (ident, rel, tam))
                alvo = d / rel
                try:
                    real = alvo.stat().st_size if alvo.exists() else None
                except OSError:
                    real = None
                if (real is not None
                        and real not in V._tamanhos_aceitos(m, rel, tam)):
                    divergentes.append("%s/%s: declarado %d, no disco %d"
                                       % (ident, rel, tam, real))
    return redondos, divergentes, medidos


def checar_tamanhos_declarados():
    print("\n[23] Tamanho declarado no registro de modelos")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    import radai_models as V
    from pathlib import Path

    redondos, divergentes, medidos = _medir_tamanhos_declarados(
        V, V.MODELOS, V.pasta_do_modelo)

    t = _temporaria("radai_c23_")
    try:
        for nome, n in (("orig", 1001), ("enx", 601), ("outro", 777)):
            os.makedirs(os.path.join(t, nome))
            with open(os.path.join(t, nome, "ck.pth"), "wb") as f:
                f.write(b"\0" * n)
        m = {"arquivos": [("ck.pth", 1001)],
             "enxuto": {"ck.pth": (601, "0" * 64)}}
        _r, div_isca, _n = _medir_tamanhos_declarados(
            V, {k: m for k in ("orig", "enx", "outro")},
            lambda ident: Path(t) / ident)
    finally:
        _apagar(t)
    checar("  (isca) o checkpoint enxuto do registro no disco passa",
           not any(x.startswith("enx/") for x in div_isca), str(div_isca))
    checar("  (isca) o original no disco passa",
           not any(x.startswith("orig/") for x in div_isca), str(div_isca))
    checar("  (isca) um tamanho que nao e nem o original nem o enxuto reprova",
           any(x.startswith("outro/") for x in div_isca), str(div_isca))

    checar("ha tamanho declarado para conferir", medidos > 0, "%d" % medidos)
    for r in redondos:
        checar("tamanho %s nao parece medido" % r, False,
               "multiplo de 10.000 -- ou meça, ou use None")
    checar("nenhum tamanho declarado e arredondado", not redondos,
           "; ".join(redondos) or "%d conferido(s)" % medidos)
    for x in divergentes:
        checar("tamanho bate com o disco: %s" % x, False,
               "o modelo vai se declarar ausente com o arquivo presente")
    checar("todo arquivo presente bate com o tamanho declarado",
           not divergentes, "; ".join(divergentes) or "byte a byte")

    for ident, m in V.MODELOS.items():
        zips = [rel for rel, _t in (m.get("arquivos") or [])
                if str(rel).lower().endswith(".zip")]
        abre = set(V.zips_a_extrair(m))
        for z in zips:
            checar("`%s` declara quem abre o %s" % (ident, z),
                   z in abre,
                   "sem `extrair`, o zip fica fechado e o motor nao acha a pasta")
    checar("`_extrair_se_preciso` existe para abrir o que se baixa zipado",
           hasattr(V, "_extrair_se_preciso"))

    for ident in V.MODELOS:
        e = V.estado_do_modelo(ident)
        contradiz = (not e["instalado"] and not e["faltando"]
                     and not e.get("embutido"))
        checar("estado de `%s` e coerente" % ident, not contradiz,
               "nada falta => ou esta instalado, ou o registro nao sabe o "
               "que ele precisa")
        checar("`%s` declara o que precisa baixar" % ident,
               bool(e.get("embutido")) or e["bytes_total"] > 0,
               "bytes_total tem de ser > 0 em modelo que nao vem no bundle")


def checar_tema_claro():
    print("\n[26] Tema claro: cor de tela e ficha, e nao hexadecimal")

    TELAS = ("radai_modules.py", "radai_bridge.py", "radai_recon3d_screen.py",
             "radai_todo.py", "radai_menu.py", "radai_consent.py",
             "radai_batch.py", "radai_provenance_screen.py",
             "radai_panel.py", "radai_shutdown.py", "radai_image_screen.py")

    _app = os.path.join(RAIZ, "app")
    _fontes = {}
    for _n in _componentes.nomes("app"):
        if _n.endswith(".py"):
            _fontes[_n] = io.open(_componentes.fonte("app/" + _n), encoding="utf-8",
                                  errors="replace").read()
    definidas = set()
    for _f in _fontes.values():
        definidas |= set(re.findall(r"(?<![\w-])(--[a-zA-Z0-9-]+)\s*:", _f))
        definidas |= set(re.findall(
            r"setProperty\(\s*['\"](--[a-zA-Z0-9-]+)", _f))

    def _fantasmas(fontes):
        return sorted(set(
            "%s em %s" % (m, n) for n, f in fontes.items()
            for m in re.findall(r"var\((--[a-zA-Z0-9-]+)", f)
            if m not in definidas))
    fantasmas = _fantasmas(_fontes)
    checar("toda ficha citada por var() existe em alguma folha de app/",
           not fantasmas, "; ".join(fantasmas[:8]))
    checar("  (isca) a ficha inventada numa tela e acusada",
           _fantasmas({"isca.py": "color:var(--txt-2-isca,#94a3b8)"})
           == ["--txt-2-isca em isca.py"])

    _ui = _fontes.get("radai_ui.py", "")
    _i, _j = _ui.find("TOKENS = u"), _ui.find("CASCA = u")
    _bloco = _ui[_i:_j] if 0 <= _i < _j else ""
    _ic = _bloco.find('data-tema="claro"')
    do_claro = set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:",
                              _bloco[_ic:] if _ic >= 0 else ""))
    checar("  o bloco do tema claro foi achado (--success e --warn nele)",
           "--success" in do_claro and "--warn" in do_claro,
           "%d fichas" % len(do_claro))

    PERMITIDOS = frozenset([
        "#000",
        "#0b0f18",
        "#4DA3FF", "#9D8BFF", "#31D0AA",
        "#3DD9F0",
    ])

    def _crus(fonte):
        limpo = re.sub(r"&#\d+;", " ", fonte)
        limpo = re.sub(r"var\((--[a-zA-Z0-9-]+),\s*#[0-9a-fA-F]{3,8}\)",
                       lambda m: " " if m.group(1) in definidas
                       else m.group(0), limpo)
        limpo = re.sub(
            r"(?<![\w-])(--[a-zA-Z0-9-]+)\s*:\s*#[0-9a-fA-F]{3,8}\b",
            lambda m: " " if m.group(1) in do_claro else m.group(0), limpo)
        return sorted(set(m for m in re.findall(r"#[0-9a-fA-F]{3,8}\b", limpo)
                          if m not in PERMITIDOS))

    for nome in TELAS:
        caminho = _componentes.fonte("app/" + nome)
        if not os.path.isfile(caminho):
            continue
        fonte = io.open(caminho, encoding="utf-8", errors="replace").read()
        crus = _crus(fonte)
        checar("[%s] nenhuma cor escrita a mao" % nome, not crus,
               ", ".join(crus[:6]))
    _isca = _crus(u"a{color:var(--success,#5BC57F)}"
                  u"b{color:var(--txt-2-isca,#94a3b8)}"
                  u":root{--success:#5BC57F;--so-no-escuro-isca:#7fd8a3}")
    checar("  (isca) o recuo de ficha inventada e a ficha que o claro nao "
           "redefine sao acusados, e o recuo de ficha real passa",
           _isca == ["#7fd8a3", "#94a3b8"], str(_isca))

    ui = io.open(_componentes.fonte("app/radai_ui.py"),
                 encoding="utf-8", errors="replace").read()
    i = ui.find("TOKENS = u")
    j = ui.find("CASCA = u")
    bloco = ui[i:j] if 0 <= i < j else ui
    claro = bloco[bloco.find("data-tema=\"claro\""):] if "claro" in bloco else ""
    escuro = bloco[:bloco.find("data-tema=\"claro\"")] if claro else bloco
    fichas_e = set(re.findall(r"(--[a-z0-9-]+)\s*:", escuro))
    fichas_c = set(re.findall(r"(--[a-z0-9-]+)\s*:", claro))
    def de_cor(f):
        return not (f.startswith("--r-") or f.startswith("--ui-")
                    or f.startswith("--font") or f in ("--sombra",))
    so_no_escuro = sorted(f for f in (fichas_e - fichas_c) if de_cor(f))
    checar("as fichas de cor existem tambem no tema claro",
           len(so_no_escuro) <= 12,
           "%d so no escuro: %s" % (len(so_no_escuro),
                                    ", ".join(so_no_escuro[:8])))
    checar("o tema claro existe", bool(fichas_c), str(len(fichas_c)))


def url_versoes_de_fabrica(RV=None):
    try:
        return str(getattr(RV, "URL_VERSOES", "") or "").strip() if RV else ""
    except Exception:
        return u""


def checar_consulta_de_versao_nao_leva_nada():
    import ast as _ast

    PERMITIDOS = {
        "radai_models.py": u"baixa peso de modelo, na maquina de preparo",
        "radai_watcher.py": u"dispara a consulta de versao (nao a faz)",
        "radai_version.py": u"a consulta de versao, automatica, e o download "
                            u"do instalador da release, por ato declarado "
                            u"(baixar_instalador, que so o radai_atualizar "
                            u"chama, conferido pelo sha256 da release)",
        "radai_lancador.py": u"so 127.0.0.1: pergunta ao painel local se "
                             u"ele subiu, antes de abrir o navegador",
        "radai_station_check.py": u"bind local, para saber se a porta "
                                        u"esta livre",
        "radai_records.py": u"resolve nome e abre TCP so para saber se a "
                            u"estacao alcanca a rede; nao envia nada",
    }
    REDE = ("urlopen", "urlretrieve", "HTTPSConnection", "HTTPConnection",
            "socket",
            "gethostbyname", "getaddrinfo", "create_connection", "sendall")
    REDE_MODULOS = ("urllib", "requests", "httpx", "ftplib", "smtplib",
                    "telnetlib", "xmlrpc")

    intrusos = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py") or nome in PERMITIDOS:
            continue
        try:
            fonte = io.open(_componentes.fonte("app/" + nome),
                            encoding="utf-8").read()
        except Exception:
            continue
        try:
            arv = _ast.parse(fonte)
        except Exception:
            continue
        for no in _ast.walk(arv):
            if not isinstance(no, _ast.Call):
                continue
            f = no.func
            alvo = getattr(f, "attr", None) or getattr(f, "id", None)
            recebedor = getattr(getattr(f, "value", None), "id", None)
            if alvo in REDE:
                intrusos.append(u"%s: %s()" % (nome, alvo))
            elif recebedor in REDE_MODULOS:
                intrusos.append(u"%s: %s.%s()" % (nome, recebedor, alvo))
    checar(u"so os modulos declarados falam para fora", not intrusos,
           u"; ".join(sorted(set(intrusos))[:4]))

    fonte = io.open(_componentes.fonte("app/radai_version.py"),
                    encoding="utf-8").read()
    arv = _ast.parse(fonte)
    com_corpo, campos = [], []
    for no in _ast.walk(arv):
        if not isinstance(no, _ast.Call):
            continue
        alvo = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
        if alvo == "Request":
            for kw in no.keywords:
                if kw.arg in ("data", "method"):
                    com_corpo.append(kw.arg)
        if alvo == "urlopen":
            for a in no.args[1:]:
                if isinstance(a, _ast.Constant) and isinstance(a.value, bytes):
                    com_corpo.append("urlopen(data)")
    checar(u"a consulta de versao nao manda corpo", not com_corpo,
           u", ".join(sorted(set(com_corpo))))

    docs = set()
    for no in _ast.walk(arv):
        corpo = getattr(no, "body", None)
        if isinstance(corpo, list) and corpo:
            pri = corpo[0]
            if (isinstance(pri, _ast.Expr)
                    and isinstance(pri.value, _ast.Constant)
                    and isinstance(pri.value.value, str)):
                docs.add(id(pri.value))
    vivos = []
    for no in _ast.walk(arv):
        if isinstance(no, _ast.Constant) and isinstance(no.value, str):
            if id(no) not in docs:
                vivos.append(no.value)
        elif isinstance(no, _ast.Name):
            vivos.append(no.id)
        elif isinstance(no, _ast.Attribute):
            vivos.append(no.attr)
    texto_vivo = u" ".join(vivos).lower()
    for proibido in ("patientid", "patient", "series_count", "hostname",
                     "getnode", "uuid1", "gethostname", "getlogin"):
        if proibido in texto_vivo:
            campos.append(proibido)
    checar(u"e nao carrega identificador de maquina nem de paciente",
           not campos, u", ".join(campos))

    def _quem_baixa_o_instalador(fontes):
        quem = set()
        for nome_f, texto in fontes.items():
            try:
                arv_f = _ast.parse(texto)
            except Exception:
                continue
            for no in _ast.walk(arv_f):
                if isinstance(no, _ast.Call) and (
                        getattr(no.func, "attr", None)
                        or getattr(no.func, "id", None)) == "baixar_instalador":
                    quem.add(nome_f)
        return quem
    fontes_app = {}
    for nome in _componentes.nomes("app"):
        if nome.endswith(".py"):
            try:
                fontes_app[nome] = io.open(_componentes.fonte("app/" + nome),
                                           encoding="utf-8").read()
            except Exception:
                continue
    quem_baixa = _quem_baixa_o_instalador(fontes_app)
    checar(u"o instalador da release so se baixa pelo radai_atualizar, por "
           u"ato declarado", quem_baixa == {"radai_atualizar.py"},
           u", ".join(sorted(quem_baixa)))
    _isca_baixa = dict(fontes_app, **{
        "radai_isca.py": u"import radai_version as V\n"
                         u"V.baixar_instalador({}, u'')\n"})
    checar(u"  (isca) outro modulo que baixe o instalador e acusado",
           _quem_baixa_o_instalador(_isca_baixa)
           == {"radai_atualizar.py", "radai_isca.py"})

    AUTOMATICOS = ("radai_version.py", "radai_records.py")
    POR_ATO = ("radai_models.py", "radai_version.py")
    LOCAIS = ("radai_station_check.py", "radai_watcher.py",
              "radai_lancador.py")
    classes = set(AUTOMATICOS) | set(POR_ATO) | set(LOCAIS)
    sem_classe = sorted(set(PERMITIDOS) - classes)
    checar(u"todo modulo que fala para fora tem classe declarada",
           not sem_classe, u", ".join(sem_classe))
    orfaos = sorted(classes - set(PERMITIDOS))
    checar(u"  e nenhuma classe sobra para modulo fora de `PERMITIDOS`",
           not orfaos, u", ".join(orfaos))
    _isca = dict(PERMITIDOS, **{"radai_isca.py": u"fala para fora"})
    checar(u"  (isca) permitido novo sem classe e acusado",
           sorted(set(_isca) - classes) == ["radai_isca.py"])

    CS = _importar_do_app("radai_consent")
    RR = _importar_do_app("radai_records")
    RV = _importar_do_app("radai_version")
    if not (CS and RR and RV):
        checar(u"a Politica e os dois automaticos importam", False,
               u"sem o valor, a comparacao abaixo seria um verde de mentira")
        return False
    declarados = set(d for c in getattr(CS, "CONEXOES_AUTOMATICAS", ())
                     for d in c.get("destinos", ()))
    _url = url_versoes_de_fabrica(RV)
    _api = RV._api_de(_url) if _url else u""
    _host = re.sub(r"^https?://([^/]+).*$", r"\1", _api or u"")
    hosts_de = {"radai_version.py": {_host} if _host else set(),
                "radai_records.py": set(getattr(RR, "INTERNET_HOSTS", ()))}
    def _politica_cobre(hosts):
        return bool(hosts) and hosts <= declarados

    for mod in AUTOMATICOS:
        hosts = hosts_de.get(mod, set())
        checar(u"a Politica declara o destino de %s" % mod,
               _politica_cobre(hosts),
               u"%s fora de %s" % (sorted(hosts - declarados),
                                   sorted(declarados)))
    _um_declarado = set(sorted(declarados)[:1])
    checar(u"  (isca) destino fora da Politica e acusado; o declarado passa",
           not _politica_cobre({u"exemplo.invalid"})
           and not _politica_cobre(set())
           and bool(_um_declarado) and _politica_cobre(_um_declarado),
           u"declarados: %s" % sorted(declarados))
    return not intrusos and not com_corpo and not campos


def checar_assinatura_das_rotas():
    import ast as _ast
    falhas = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        caminho = _componentes.fonte("app/" + nome)
        try:
            fonte = io.open(caminho, encoding="utf-8").read()
            arvore = _ast.parse(fonte)
        except Exception:
            continue
        for no in _ast.walk(arvore):
            if not isinstance(no, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                continue
            rota = None
            for d in no.decorator_list:
                f = d.func if isinstance(d, _ast.Call) else d
                if not (isinstance(f, _ast.Attribute)
                        and f.attr in ("post", "put", "get", "delete")):
                    continue
                if isinstance(d, _ast.Call) and d.args and isinstance(
                        d.args[0], _ast.Constant):
                    rota = d.args[0].value
                else:
                    rota = "?"
            if rota is None:
                continue

            for arg in list(no.args.args) + list(no.args.kwonlyargs):
                if arg.arg == "request" and arg.annotation is None:
                    falhas.append(u"%s %s: `request` sem `: Request` "
                                  u"(o FastAPI o trata como query, e a rota "
                                  u"devolve 422)" % (nome, rota))

            corpo = _ast.dump(no)
            for alvo in ("Response", "HTMLResponse", "Request"):
                if (u"id='%s'" % alvo) not in corpo:
                    continue
                ligado = False
                for n2 in _ast.walk(no):
                    if isinstance(n2, (_ast.Import, _ast.ImportFrom)):
                        if any(a.asname == alvo or a.name == alvo
                               for a in n2.names):
                            ligado = True
                    if isinstance(n2, _ast.arg) and n2.arg == alvo:
                        ligado = True
                if ligado:
                    continue
                topo = False
                for n2 in arvore.body:
                    if isinstance(n2, (_ast.Import, _ast.ImportFrom)):
                        if any(a.asname == alvo or a.name == alvo
                               for a in n2.names):
                            topo = True
                if topo:
                    continue
                pai = None
                for n2 in _ast.walk(arvore):
                    if isinstance(n2, (_ast.FunctionDef, _ast.AsyncFunctionDef)) \
                            and no in _ast.walk(n2) and n2 is not no:
                        pai = n2
                if pai is not None:
                    for n2 in pai.body:
                        if isinstance(n2, (_ast.Import, _ast.ImportFrom)):
                            if any(a.asname == alvo or a.name == alvo
                                   for a in n2.names):
                                topo = True
                if not topo:
                    falhas.append(u"%s %s: usa `%s` sem import no escopo "
                                  u"(NameError na chamada, 500 na tela)"
                                  % (nome, rota, alvo))

    checar(u"toda rota assina o que usa", not falhas,
           u"; ".join(sorted(set(falhas))[:4]))
    return not falhas


def checar_listas_de_preservados():
    print("\n[36] As tres listas de preservados batem entre si")
    ARQS = [
        ("installer/INSTALL.ps1", r"\$PRESERVAR\s*=\s*@\((.*?)\)"),
        ("installer/UNINSTALL.ps1", r"\$PRESERVAVEL\s*=\s*@\((.*?)\)"),
        ("packager/prepare.ps1", r"\$preserv\s*=\s*@\((.*?)\)"),
    ]
    listas = {}
    for rel, padrao in ARQS:
        caminho = os.path.join(RAIZ, rel.replace("/", os.sep))
        try:
            txt = io.open(caminho, encoding="utf-8-sig",
                          errors="replace").read()
        except Exception as e:
            checar("consigo ler %s" % rel, False, str(e)[:80])
            return
        m = re.search(padrao, txt, re.S)
        checar("achei a lista em %s" % rel, bool(m))
        if not m:
            return
        corpo = re.sub(r"(?m)#.*$", "", m.group(1))
        listas[rel] = set(re.findall(r"['\"]([^'\"]+)['\"]", corpo))
    nomes = list(listas)
    base = listas[nomes[0]]
    for outro in nomes[1:]:
        so_a = sorted(base - listas[outro])
        so_b = sorted(listas[outro] - base)
        checar("%s bate com %s" % (nomes[0].split("/")[-1],
                                   outro.split("/")[-1]),
               not so_a and not so_b,
               "so no 1o: %s | so no 2o: %s" % (so_a or "-", so_b or "-"))
    for n in nomes:
        checar("[%s] preserva `registro`" % n.split("/")[-1],
               "registro" in listas[n],
               "o acervo de casos seria apagado pela atualizacao")

def checar_variavel_lida_antes_de_existir():
    print("\n[37] Variavel lida antes de existir (Set-StrictMode Latest)")
    ferr = os.path.join(RAIZ, "tools", "lerantes.ps1")
    checar("a ferramenta existe", os.path.isfile(ferr),
           "tools/lerantes.ps1")
    if not os.path.isfile(ferr):
        return
    alvos = [os.path.join(RAIZ, "packager", n)
             for n in ("prepare.ps1", "UPDATE.ps1", "languages.ps1")]
    alvos += [os.path.join(RAIZ, "installer", n)
              for n in ("INSTALL.ps1", "UNINSTALL.ps1")]
    alvos = [a for a in alvos if os.path.isfile(a)]
    checar("  e ha .ps1 para varrer", len(alvos) >= 2, str(len(alvos)))
    for a in alvos:
        nome = os.path.basename(a)
        try:
            import subprocess as _sub
            r = _sub.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                          "Bypass", "-File", ferr, "-Arquivo", a],
                         capture_output=True, text=True, timeout=180)
        except Exception as e:
            checar("%s: a varredura rodou" % nome, False,
                   "%s: %s" % (type(e).__name__, e))
            continue
        achados = [l.strip() for l in (r.stdout or "").splitlines()
                   if "LERANTES" in l or "SINTAXE" in l]
        checar("%s: nenhuma variavel lida antes de existir" % nome,
               not achados,
               " | ".join(a.replace("\t", " ") for a in achados[:3]))

    sys.path.insert(0, os.path.join(RAIZ, "tools"))
    try:
        import lerantes_py as _lp
    except Exception as e:
        checar("o detector de Python carrega", False,
               "%s: %s" % (type(e).__name__, e))
        return
    _achados = _lp.varrer()
    checar("nenhum nome lido antes de existir em `.py`",
           not _achados,
           " | ".join("%s: %s" % (c, t) for c, _l, t in _achados[:3]))


def _sem_comentario_ps(t):
    t = re.sub(r"(?s)<#.*?#>", " ", t)
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in t.splitlines())


def _sem_comentario_cmd(t):
    fora = []
    for ln in t.splitlines():
        s = ln.strip().lower()
        if s.startswith("rem ") or s == "rem" or s.startswith("::"):
            continue
        fora.append(ln)
    return "\n".join(fora)


def checar_tela_de_lote_fala_uma_lingua():
    print("\n[38] A janela preta fala INGLES, e a barra do Windows cala")

    DESENHAM = ("Expand-Archive", "Invoke-WebRequest", "Start-BitsTransfer")
    alvos = []
    for pasta in ("packager", "installer", "app", "build"):
        base = os.path.join(RAIZ, pasta)
        for raiz, _d, arqs in os.walk(base):
            if "_montagem" in raiz or ".venv" in raiz:
                continue
            for a in arqs:
                if a.lower().endswith((".ps1", ".cmd")):
                    alvos.append(os.path.join(raiz, a))
    sem_calar = []
    for c in alvos:
        try:
            t = io.open(c, encoding="utf-8-sig", errors="replace").read()
        except Exception:
            continue
        if not any(d in t for d in DESENHAM):
            continue
        _vivo = _sem_comentario_ps(t) if c.lower().endswith(".ps1") \
            else _sem_comentario_cmd(t)
        if not re.search(r"\$(?:script:|global:)?ProgressPreference\s*=\s*"
                         r"['\"]SilentlyContinue['\"]", _vivo):
            sem_calar.append(os.path.relpath(c, RAIZ))
    checar("quem baixa ou extrai cala a barra de progresso",
           not sem_calar,
           " | ".join(sem_calar[:3]) +
           "  (a barra fala a lingua do Windows, nao a do pacote)")

    PORTUGUESAS = (u"nao", u"voce", u"esta", u"pasta", u"arquivo",
                   u"janela", u"clique", u"programa", u"instalacao",
                   u"preparador", u"pacote", u"aqui", u"dentro",
                   u"abrindo", u"procurando", u"achei", u"copiando",
                   u"extraia", u"extraindo", u"feche", u"deixe",
                   u"estruturas", u"aprovada", u"revisao", u"medico",
                   u"erro", u"aviso", u"escolhe", u"maquina", u"fila",
                   u"leia", u"rode", u"copia", u"metade")
    FROTA = []
    for _pasta in ("app", "installer", "packager", "build"):
        for _r, _d, _a in os.walk(os.path.join(RAIZ, _pasta)):
            if "_montagem" in _r or ".venv" in _r:
                continue
            for _f in _a:
                if _f.lower().endswith(".cmd"):
                    FROTA.append(os.path.relpath(os.path.join(_r, _f), RAIZ))
    FROTA.sort()
    checar("a frota de `.cmd` foi descoberta do disco", len(FROTA) >= 8,
           "%d arquivo(s)" % len(FROTA))

    import re as _re
    SEGUROS = _re.compile(
        r"(%[A-Za-z_0-9~]+%|\S+\.(cmd|ps1|py|txt|json|zip|exe)"
        r"|https?://\S+|\^?[<>]|_[A-Za-z]+_)")
    achados = []
    for rel in FROTA:
        c = os.path.join(RAIZ, rel.replace("/", os.sep))
        if not os.path.isfile(c):
            continue
        for n, ln in enumerate(io.open(c, encoding="ascii",
                                       errors="replace").read()
                               .splitlines(), 1):
            s = ln.strip()
            if not s.lower().startswith("echo "):
                continue
            s = SEGUROS.sub(" ", s[5:])
            for p in _re.findall(r"[A-Za-z]+", s):
                if p.lower() in PORTUGUESAS:
                    achados.append("%s:%d %s" % (rel, n, p))
                    break
    DIVIDA_PT = 3
    arquivos_pt = sorted(set(a.split(":")[0] for a in achados))
    checar("a divida de traducao nao CRESCEU",
           len(arquivos_pt) <= DIVIDA_PT,
           "%d arquivo(s) em portugues, teto %d: %s"
           % (len(arquivos_pt), DIVIDA_PT, ", ".join(arquivos_pt)))
    checar("  e o teto e o numero real, sem folga",
           len(arquivos_pt) == DIVIDA_PT,
           "traduziu algum? baixe DIVIDA_PT para %d" % len(arquivos_pt))
    checar("  e quem ja fala ingles continua falando",
           not [a for a in achados
                if a.split(":")[0] not in arquivos_pt],
           " | ".join(achados[:3]))

    ruins = []
    for rel in FROTA:
        c = os.path.join(RAIZ, rel.replace("/", os.sep))
        if not os.path.isfile(c):
            continue
        b = io.open(c, "rb").read()
        if any(ch > 127 for ch in b):
            ruins.append(rel + " (byte acima de 127)")
        if b.count(b"\n") != b.count(b"\r\n"):
            ruins.append(rel + " (LF solto)")
        for ln in b.decode("ascii", "replace").splitlines():
            s = ln.strip().lower()
            if s.startswith("rem") or s.startswith("::"):
                continue
            if "chcp" in s:
                ruins.append(rel + " (chcp no meio do lote)")
                break
    checar("a janela de comando e ASCII, CRLF e sem `chcp`",
           not ruins, " | ".join(ruins[:3]))


def checar_caminho_na_url():
    print("\n[27] Caminho de paciente na URL de um GET")

    _dapp = os.path.join(RAIZ, "app")
    ROTAS = tuple(sorted(n for n in _componentes.nomes("app")
                         if n.endswith(".py"))) if os.path.isdir(_dapp) else ()

    padrao = re.compile(
        r'@app\.get\([^)]*\)\s*\n\s*(?:async\s+)?def\s+\w+\(([^)]*)\)',
        re.S)
    for nome in ROTAS:
        caminho = _componentes.fonte("app/" + nome)
        if not os.path.isfile(caminho):
            continue
        fonte = io.open(caminho, encoding="utf-8", errors="replace").read()
        ruins = []
        for m in padrao.finditer(fonte):
            args = m.group(1)
            for arg in ("pasta", "caminho", "dir", "raiz"):
                if re.search(r"\b%s\s*:" % arg, args):
                    ruins.append("%s(%s…)" % (
                        fonte[:m.start()].count("\n") + 1, arg))
        checar("[%s] nenhuma rota GET recebe caminho" % nome, not ruins,
               ", ".join(ruins[:4]))

    for nome in ("radai_bridge.py", "radai_recon3d_screen.py"):
        caminho = _componentes.fonte("app/" + nome)
        if not os.path.isfile(caminho):
            continue
        fonte = io.open(caminho, encoding="utf-8", errors="replace").read()
        checar("[%s] a imagem viaja por bilhete" % nome,
               "?b=' + encodeURIComponent" in fonte)
        checar("[%s] e o bilhete vem de radai_thumbnail" % nome,
               "radai_thumbnail" in fonte,
               "reimplementar o HMAC seria um segundo segredo")


def checar_ascii_dos_lotes():
    print("\n[bytes] Todo `.cmd` e ASCII puro e CRLF, a raiz inclusive")
    import re as _re

    frota = []
    for base, _d, arqs in os.walk(RAIZ):
        if any(p in base for p in ("_montagem", ".venv", os.sep + "arquivo",
                                   "__pycache__", ".git") + FORA):
            continue
        for a in sorted(arqs):
            if a.lower().endswith((".cmd", ".bat")):
                frota.append(os.path.relpath(os.path.join(base, a), RAIZ))
    frota.sort()
    checar("a frota inclui os `.cmd` da raiz",
           any(os.sep not in f for f in frota),
           "%d arquivo(s), %d na raiz"
           % (len(frota), len([f for f in frota if os.sep not in f])))

    COMANDO_CHCP = _re.compile(rb"^\s*(?!REM\b|::)\s*chcp\b", _re.I | _re.M)
    nao_ascii, com_lf, com_chcp = [], [], []
    for rel in frota:
        b = open(os.path.join(RAIZ, rel.replace("/", os.sep)), "rb").read()
        ruins = [x for x in b if x > 126]
        if ruins:
            n = b[:b.find(bytes([ruins[0]]))].count(b"\n") + 1
            nao_ascii.append("%s:%d (%d byte(s))" % (rel, n, len(ruins)))
        if b.count(b"\n") != b.count(b"\r\n"):
            com_lf.append("%s (%d LF solto)"
                          % (rel, b.count(b"\n") - b.count(b"\r\n")))
        if COMANDO_CHCP.search(b):
            com_chcp.append(rel)

    checar("  nenhum tem byte fora do ASCII",
           not nao_ascii, " | ".join(nao_ascii[:4]))
    checar("  nenhum tem LF solto", not com_lf, " | ".join(com_lf[:4]))
    checar("  e nenhum EXECUTA `chcp`", not com_chcp,
           " | ".join(com_chcp[:4]))


def checar_dado_de_app_embarca():
    print("\n[dado] O dado de `app\\data\\` embarca no pacote")
    import re as _re

    app = os.path.join(RAIZ, "app")
    pedidos = set()

    bib = io.open(_componentes.fonte("app/radai_bibliography.py"),
                  encoding="utf-8", errors="replace").read()
    for m in _re.finditer(r'\(\s*"data"\s*,\s*"([^"]+\.json)"\s*\)', bib):
        pedidos.add(m.group(1))

    checar("achei os nomes nos proprios leitores", len(pedidos) >= 1,
           "%d: %s" % (len(pedidos), sorted(pedidos)))

    faltam = [n for n in sorted(pedidos)
              if not os.path.isfile(os.path.join(app, "data", n))]
    checar("  e todos existem em `app\\data\\`", not faltam, str(faltam))

    ca = io.open(os.path.join(RAIZ, "build", "configurar_ambiente.py"),
                 encoding="utf-8", errors="replace").read()
    inicio = ca.find("def etapa_app(")
    fim = ca.find("\ndef ", inicio + 10) if inicio >= 0 else -1
    corpo = ca[inicio:fim] if inicio >= 0 and fim > inicio else ""
    checar("  e `etapa_app` copia a pasta `data`",
           bool(corpo) and 'RAIZ / "app" / "data"' in corpo
           and 'glob("*.json")' in corpo,
           "a etapa nao tem a copia — o dado fica no repositorio")
    checar("  e NAO copia `registro` nem `modelos` (estado do operador)",
           bool(corpo) and '"registro"' not in corpo
           and '/ "modelos"' not in corpo)


def checar_contraste_dos_temas():
    print("\n[wcag] Texto sobre fundo cumpre a AA nos dois temas")
    import re as _re

    fonte = _componentes.fonte("app/radai_ui.py")
    texto = io.open(fonte, encoding="utf-8", errors="replace").read()

    TEXTOS = ("text", "text-muted", "text-dim")
    FUNDOS = ("bg-0", "bg-1", "panel", "panel-2")
    PISO = 4.5

    def _rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _lum(c):
        def f(v):
            v = v / 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])

    def _razao(a, b):
        la, lb = _lum(_rgb(a)), _lum(_rgb(b))
        if la < lb:
            la, lb = lb, la
        return (la + 0.05) / (lb + 0.05)

    inicios = [m.start() for m in _re.finditer(r"--bg-0:#", texto)]
    checar("achei os blocos de tema em `radai_ui.py`", len(inicios) >= 2,
           "%d bloco(s) com `--bg-0`" % len(inicios))

    ruins, medidos = [], 0
    for i, p in enumerate(inicios):
        fim = inicios[i + 1] if i + 1 < len(inicios) else len(texto)
        bloco = texto[p:fim]
        val = {}
        for k in TEXTOS + FUNDOS:
            m = _re.search(r"--%s:(#[0-9a-fA-F]{6})" % _re.escape(k), bloco)
            if m:
                val[k] = m.group(1)
        faltam = [k for k in TEXTOS + FUNDOS if k not in val]
        if faltam:
            ruins.append("bloco %d nao declara: %s" % (i + 1, ",".join(faltam)))
            continue
        for t in TEXTOS:
            for f in FUNDOS:
                r = _razao(val[t], val[f])
                medidos += 1
                if r < PISO:
                    ruins.append("bloco %d: --%s sobre --%s = %.2f:1"
                                 % (i + 1, t, f, r))

    checar("  mediu as combinacoes de texto x fundo", medidos >= 24,
           "%d medida(s)" % medidos)
    checar("  e nenhuma fica abaixo de 4,5:1", not ruins,
           " | ".join(ruins[:6]))

    m = _re.search(r"--text-dim:(#[0-9a-fA-F]{6})", texto)
    token_escuro = m.group(1).lower() if m else ""
    recuos = {}
    app = os.path.join(RAIZ, "app")
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        t = io.open(_componentes.fonte("app/" + nome), encoding="utf-8",
                    errors="replace").read()
        for mm in _re.finditer(r"text-dim,\s*(#[0-9a-fA-F]{6})", t):
            recuos[mm.group(1).lower()] = recuos.get(mm.group(1).lower(), 0) + 1
    checar("  o recuo literal de `--text-dim` e UM valor so",
           len(recuos) <= 1, str(recuos))
    checar("  e ele e o mesmo do token do tema escuro",
           not recuos or list(recuos) == [token_escuro],
           "recuo=%s token=%s" % (list(recuos), token_escuro))


def checar_goto_tem_rotulo():
    print("\n[goto] Todo `goto` de `.cmd` acha um rotulo, e so um")
    import re as _re

    frota = []
    for base, dirs, arqs in os.walk(RAIZ):
        if any(p in base for p in ("_montagem", ".venv", os.sep + "arquivo",
                                   "__pycache__", ".git") + FORA):
            continue
        for a in arqs:
            if a.lower().endswith((".cmd", ".bat")):
                frota.append(os.path.relpath(os.path.join(base, a), RAIZ))
    frota.sort()
    checar("a frota de `.cmd` saiu do disco, com a raiz dentro",
           len(frota) >= 10 and any(os.sep not in f for f in frota),
           "%d arquivo(s)" % len(frota))

    ALVO = _re.compile(r"\bgoto\s+:?([A-Za-z_][A-Za-z0-9_]*)", _re.I)
    ROTULO = _re.compile(r"^\s*:([A-Za-z_][A-Za-z0-9_]*)")

    sem_rotulo, duplicados = [], []
    for rel in frota:
        caminho = os.path.join(RAIZ, rel.replace("/", os.sep))
        try:
            linhas = io.open(caminho, encoding="utf-8",
                             errors="replace").read().splitlines()
        except OSError:
            continue
        rotulos = {}
        for n, s in enumerate(linhas, 1):
            m = ROTULO.match(s)
            if m:
                rotulos.setdefault(m.group(1).lower(), []).append(n)
        for nome, ns in sorted(rotulos.items()):
            if len(ns) > 1:
                duplicados.append("%s:%s `:%s` em %s"
                                  % (rel, ns[0], nome,
                                     ", ".join(str(x) for x in ns)))
        for n, s in enumerate(linhas, 1):
            nu = s.strip()
            if nu.upper().startswith("REM") or nu.lower().startswith("echo"):
                continue
            for m in ALVO.finditer(nu):
                nome = m.group(1).lower()
                if nome == "eof":
                    continue
                if nome not in rotulos:
                    sem_rotulo.append("%s:%d goto :%s" % (rel, n, nome))

    checar("nenhum `goto` aponta para rotulo que nao existe",
           not sem_rotulo,
           " | ".join(sem_rotulo[:5]) +
           "  (goto sem rotulo ENCERRA o lote com uma mensagem que nomeia"
           " um rotulo, e nao um problema)")
    checar("  e nenhum rotulo esta definido duas vezes",
           not duplicados,
           " | ".join(duplicados[:5]) +
           "  (todo goto cai no PRIMEIRO; o segundo bloco fica inalcancavel)")


_CONFERENCIAS_NA_CAIXA = ("sobreposicoes", "implausiveis",
                          "componentes_distantes", "conferir_sustentacao")


def _conferencias_sem_caixa(fonte):
    try:
        arv = ast.parse(fonte)
    except SyntaxError as e:
        return [u"engine.py nao compila: %s" % e]
    fns = [n for n in ast.walk(arv)
           if isinstance(n, ast.FunctionDef) and n.name == "build_rtstruct"]
    if not fns:
        return [u"build_rtstruct nao achada"]
    fn = fns[0]
    nomes_da_caixa = set()
    for no in ast.walk(fn):
        if (isinstance(no, ast.Assign) and isinstance(no.value, ast.Call)
                and getattr(no.value.func, "attr",
                            getattr(no.value.func, "id", "")) == "Caixas"):
            for t in no.targets:
                if isinstance(t, ast.Name):
                    nomes_da_caixa.add(t.id)
    defeitos = []
    if not nomes_da_caixa:
        defeitos.append(u"build_rtstruct nao monta a `Caixas` da serie")
    for alvo in _CONFERENCIAS_NA_CAIXA:
        chamadas = [c for c in ast.walk(fn) if isinstance(c, ast.Call)
                    and getattr(c.func, "attr",
                                getattr(c.func, "id", "")) == alvo]
        if not chamadas:
            defeitos.append(u"%s nao e chamada em build_rtstruct" % alvo)
            continue
        for c in chamadas:
            kw = [k for k in c.keywords if k.arg == "caixas"]
            if not kw or not (isinstance(kw[0].value, ast.Name)
                              and kw[0].value.id in nomes_da_caixa):
                defeitos.append(u"%s (linha %d) sem `caixas=` da serie"
                                % (alvo, c.lineno))
    return defeitos


def checar_conferencias_na_caixa():
    print(NL + "[14j] As quatro conferencias recebem a caixa da serie (F3)")
    fonte = ler(os.path.join(APP, "engine.py"))
    defeitos = _conferencias_sem_caixa(fonte)
    checar("build_rtstruct monta a Caixas e a passa as quatro conferencias "
           "(%s)" % ", ".join(_CONFERENCIAS_NA_CAIXA), not defeitos,
           "; ".join(defeitos[:4]))
    forjada = re.sub(r"(implausiveis\(masks, grade,)\s*caixas=_cx,?\s*",
                     r"\1 ", fonte, count=1)
    checar("  (isca) sem o `caixas=` do piso de volume, a checagem acusa",
           forjada != fonte and any(
               "implausiveis" in d for d in _conferencias_sem_caixa(forjada)))
    forjada2 = fonte.replace("_cx = radai_geom.Caixas(masks)", "_cx = None", 1)
    checar("  (isca) sem a montagem da Caixas, a checagem acusa",
           forjada2 != fonte and bool(_conferencias_sem_caixa(forjada2)))
    sys.path.insert(0, os.path.join(RAIZ, APP))
    try:
        import radai_geom as _G
        folga = _G.Caixas({}).folga
        checar("a folga de fabrica da Caixas e a da conferencia (e nao None, "
               "o caminho do volume inteiro)",
               folga is not None and folga == _G.FOLGA_DA_CONFERENCIA,
               str(folga))
    except Exception as e:
        checar("radai_geom importa para conferir a folga da Caixas", False,
               "%s: %s" % (type(e).__name__, e))


def _regras_de_gravacao_ligadas(fonte):
    try:
        arv = ast.parse(fonte)
    except SyntaxError as e:
        return [u"engine.py nao compila: %s" % e]
    defeitos = []
    ordem = None
    for no in arv.body:
        if (isinstance(no, ast.Assign) and len(no.targets) == 1
                and getattr(no.targets[0], "id", "") == "ORDEM_DO_FULL"):
            try:
                ordem = ast.literal_eval(no.value)
            except Exception:
                ordem = None
    if not ordem:
        defeitos.append(u"ORDEM_DO_FULL nao achada (ou nao e literal)")
    elif ordem[0][0] != "regras":
        defeitos.append(u"o primeiro passo de ORDEM_DO_FULL e `%s`, e nao "
                        u"`regras`" % ordem[0][0])
    fns = dict((n.name, n) for n in ast.walk(arv)
               if isinstance(n, ast.FunctionDef))
    pf = fns.get("preparar_full")
    if pf is None:
        defeitos.append(u"preparar_full nao achada")
    else:
        ligado = False
        for d in ast.walk(pf):
            if isinstance(d, ast.Dict):
                for k, v in zip(d.keys, d.values):
                    if (isinstance(k, ast.Constant) and k.value == "regras"
                            and isinstance(v, ast.Name)):
                        alvo = [f for f in ast.walk(pf)
                                if isinstance(f, ast.FunctionDef)
                                and f.name == v.id]
                        ligado = bool(alvo) and any(
                            isinstance(c, ast.Call)
                            and getattr(c.func, "id", "")
                            == "aplicar_regras_de_gravacao"
                            for c in ast.walk(alvo[0]))
        if not ligado:
            defeitos.append(u"preparar_full nao liga o passo `regras` a "
                            u"aplicar_regras_de_gravacao")
    lf = fns.get("limpar_fora_do_corpo")
    if lf is None:
        defeitos.append(u"limpar_fora_do_corpo nao achada")
    elif not any(isinstance(d, ast.Delete) for d in ast.walk(lf)):
        defeitos.append(u"limpar_fora_do_corpo nao tira a estrutura que "
                        u"esvazia (R3)")
    return defeitos


def checar_regras_de_gravacao():
    print(NL + "[14k] As regras de gravacao R1-R4: ligadas, e as listas")
    fonte_lf = ler(os.path.join(APP, "engine.py")).replace("\r\n", "\n")
    defeitos = _regras_de_gravacao_ligadas(fonte_lf)
    checar("as regras de gravacao sao o primeiro passo do FULL, ligadas a "
           "aplicar_regras_de_gravacao, e a R3 esvazia",
           not defeitos, "; ".join(defeitos[:4]))
    _a = '    ("regras", u"regras de gravacao (R1 a R4)"),\n'
    _b = '    ("fusao_do_indice_26", u"indice 26 fundido ao sacro"),\n'
    forjada = fonte_lf.replace(_a + _b, _b + _a, 1)
    checar("  (isca) com as regras em SEGUNDO na ordem, a checagem acusa",
           forjada != fonte_lf and any(
               u"primeiro passo" in d
               for d in _regras_de_gravacao_ligadas(forjada)))
    _i = fonte_lf.find("def limpar_fora_do_corpo(")
    forjada2 = (fonte_lf[:_i] + fonte_lf[_i:].replace(
        "                del masks[nome]\n", "                pass\n", 1)
        if _i >= 0 else fonte_lf)
    checar("  (isca) sem o `del` na limpeza fora do corpo, a checagem acusa",
           forjada2 != fonte_lf and any(
               u"esvazia" in d for d in _regras_de_gravacao_ligadas(forjada2)))
    sys.path.insert(0, os.path.join(RAIZ, APP))
    try:
        import engine as E
    except Exception as e:
        checar("o motor importa para conferir as listas das regras", False,
               "%s: %s" % (type(e).__name__, e))
        return
    protegidos = ("adrenal_gland_left", "adrenal_gland_right",
                  "eye_lens_left", "eye_lens_right", "optic_nerve_left",
                  "optic_nerve_right", "common_carotid_artery_left",
                  "internal_carotid_artery_right", "thyroid_gland")
    fora = [n for n in protegidos if E.classe_de_poda(n)[0] != "nunca"]
    checar("as estruturas pequenas que o autor nomeou sao NUNCA_PODA "
           "(adrenais, cristalinos, nervos opticos, carotidas, tireoide)",
           not fora, ", ".join(fora))
    grandes_pequenas = [n for n in protegidos
                        if E._na_lista(E.GRANDES, n) is not None]
    checar("  e nenhuma delas esta em GRANDES (a R1 nao as alcanca)",
           not grandes_pequenas, ", ".join(grandes_pequenas))
    cruzadas = [n for n in E.PODA if E.nunca_poda(n)]
    checar("PODA e NUNCA_PODA sao disjuntas", not cruzadas,
           ", ".join(cruzadas))
    checar("o portao do orgao solido do tronco existe e e chamado dentro da "
           "R4 (_portoes_de_regiao)",
           _chama_dentro(fonte_lf, "_portoes_de_regiao",
                         "_portao_dos_orgaos_solidos")
           and bool(getattr(E, "ORGAOS_SOLIDOS_DO_TRONCO", None)))
    _sem = fonte_lf.replace("    _portao_dos_orgaos_solidos(masks, grade, rel",
                            "    pass  # (masks, grade, rel", 1)
    checar("  (isca) sem a chamada, a checagem acusa",
           _sem != fonte_lf and not _chama_dentro(
               _sem, "_portoes_de_regiao", "_portao_dos_orgaos_solidos"))


def _chama_dentro(fonte, funcao, chamada):
    try:
        arv = ast.parse(fonte)
    except SyntaxError:
        return False
    for no in arv.body:
        if isinstance(no, ast.FunctionDef) and no.name == funcao:
            for c in ast.walk(no):
                if (isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                        and c.func.id == chamada):
                    return True
    return False


def _trava_e_retomada_ligadas(fonte):
    try:
        arv = ast.parse(fonte)
    except SyntaxError as e:
        return [u"engine.py nao compila: %s" % e]
    fns = dict((n.name, n) for n in ast.walk(arv)
               if isinstance(n, ast.FunctionDef))
    defeitos = []

    def _chamadas(no, nome):
        return [c for c in ast.walk(no) if isinstance(c, ast.Call)
                and (getattr(c.func, "id", "") == nome
                     or getattr(c.func, "attr", "") == nome)]

    rt = fns.get("run_ts_task")
    if rt is None:
        defeitos.append(u"run_ts_task nao achada")
    else:
        juizes = _chamadas(rt, "_JuizDaTrava")
        if not juizes:
            defeitos.append(u"run_ts_task nao monta o _JuizDaTrava")
        elif not any(isinstance(a, ast.Name) and a.id == "trava"
                     for j in juizes for a in j.args):
            defeitos.append(u"o _JuizDaTrava de run_ts_task nao recebe a "
                            u"`trava` de quem chamou")
        laco = [w for w in ast.walk(rt) if isinstance(w, ast.While)]
        if not any(_chamadas(w, "julgar") for w in laco):
            defeitos.append(u"run_ts_task nao chama .julgar(...) dentro do "
                            u"laco da task")
        if not any(isinstance(r, ast.Raise) and r.exc is not None
                   and _chamadas(r.exc, "TaskTravada")
                   for r in ast.walk(rt)):
            defeitos.append(u"run_ts_task nao levanta TaskTravada")
    rl = fns.get("rodar_tasks")
    if rl is None:
        defeitos.append(u"rodar_tasks nao achada")
    else:
        plano_menor = any(
            isinstance(a, ast.Assign) and isinstance(a.targets[0],
                                                     ast.Subscript)
            and isinstance(a.targets[0].slice, ast.Constant)
            and a.targets[0].slice.value == "plano_menor"
            and isinstance(a.value, ast.Constant) and a.value.value is True
            for a in ast.walk(rl))
        if not plano_menor:
            defeitos.append(u"rodar_tasks nao pede plano_menor=True na "
                            u"retomada")
        dois = any(k.arg == "tentativa" and isinstance(k.value, ast.Constant)
                   and k.value.value == 2
                   for c in _chamadas(rl, "TaskTravada") for k in c.keywords)
        if not dois:
            defeitos.append(u"rodar_tasks nao levanta TaskTravada com "
                            u"tentativa=2 (a base travada duas vezes)")
    return defeitos


def checar_trava_e_clip_box():
    print(NL + "[14l] A trava da task ligada, e o clip-box so com a medida")
    fonte = ler(os.path.join(APP, "engine.py")).replace("\r\n", "\n")
    defeitos = _trava_e_retomada_ligadas(fonte)
    checar("run_ts_task julga a trava no laco e levanta TaskTravada; "
           "rodar_tasks refaz com o plano menor e sobe a base travada duas "
           "vezes", not defeitos, "; ".join(defeitos[:4]))
    forjada = fonte.replace("_veredito = _juiz.julgar(", "_veredito = (", 1)
    checar("  (isca) sem o `.julgar(` no laco, a checagem acusa",
           forjada != fonte and any(
               u"julgar" in d for d in _trava_e_retomada_ligadas(forjada)))
    forjada2 = fonte.replace('extra["plano_menor"] = True',
                             'extra["plano_menor"] = False', 1)
    checar("  (isca) sem o plano menor na retomada, a checagem acusa",
           forjada2 != fonte and any(
               u"plano_menor" in d
               for d in _trava_e_retomada_ligadas(forjada2)))
    sys.path.insert(0, os.path.join(RAIZ, APP))
    try:
        import engine as E
    except Exception as e:
        checar("o motor importa para conferir o registro do clip-box", False,
               "%s: %s" % (type(e).__name__, e))
        return

    def _fora_do_criterio(reg):
        ruins = []
        for t, ent in reg.items():
            if E._e_base(t) or t in E.TASKS_COM_CROP_MODEL:
                ruins.append(u"%s (base ou crop_model)" % t)
            for rot, v in [(t, ent)] + ([(t + u".fast", ent["fast"])]
                                        if ent.get("fast") else []):
                if not v.get("medido"):
                    continue
                n = v.get("numeros") or {}
                try:
                    ok = float(n.get("dice_min")) >= 0.99
                except (TypeError, ValueError):
                    ok = False
                if not ok:
                    ruins.append(u"%s (medido sem dice_min >= 0,99)" % rot)
        return ruins

    ruins = _fora_do_criterio(E.RECORTE_POR_TASK)
    checar("todo clip-box ligado tem os numeros e passa o criterio (Dice >= "
           "0,99); a base e o crop_model nunca estao no registro",
           not ruins, "; ".join(ruins))
    forjado = dict(E.RECORTE_POR_TASK)
    forjado["lung_vessels"] = dict(forjado["lung_vessels"], medido=True,
                                   numeros=None)
    checar("  (isca) uma task ligada sem numero, a checagem acusa",
           bool(_fora_do_criterio(forjado)))
    forjado_v = dict(E.RECORTE_POR_TASK)
    ab = dict(forjado_v["abdominal_muscles"])
    ab["fast"] = dict(ab.get("fast") or {}, medido=True,
                      numeros={"dice_min": 0.93})
    forjado_v["abdominal_muscles"] = ab
    checar("  (isca) a variante do FAST ligada com o Dice por rotulo "
           "(0,93), a checagem acusa", bool(_fora_do_criterio(forjado_v)))


NPM_SO_EM = ("build/porta/",)


def manifestos_npm_fora_do_lugar(arquivos):
    return sorted(a for a in arquivos
                  if os.path.basename(a) in ("package.json", "package-lock.json")
                  and not a.startswith(NPM_SO_EM))


def checar_npm_so_no_preparo_da_porta():
    print("\n[39] npm so no preparo da porta")
    import subprocess
    try:
        r = subprocess.run(["git", "-C", RAIZ, "ls-files", "-z"],
                           capture_output=True, timeout=120)
        arquivos = ([p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]
                    if r.returncode == 0 else None)
    except Exception:
        arquivos = None
    if arquivos is None:
        checar("npm so em build/porta (fora de um repositorio Git: nada a conferir)", True)
        return
    fora = manifestos_npm_fora_do_lugar(arquivos)
    checar("package.json e package-lock.json so em build/porta", not fora,
           ", ".join(fora))
    checar("  (isca) um package.json em app/ reprova",
           bool(manifestos_npm_fora_do_lugar(arquivos + ["app/package.json"])))
    emp = io.open(os.path.join(RAIZ, "build", "empacotar_instalador.py"),
                  encoding="utf-8").read()
    checar("  e build/porta nao viaja no instalador leve",
           'FORA_PREFIXOS = ("build/porta/",)' in emp
           and "nome.startswith(FORA_PREFIXOS)" in emp)


def checar_icone_e_a_marca():
    print("\n[icone] o .svg, o .ico e o .png sao o mesmo desenho, da marca")
    ui = ler(os.path.join(APP, "radai_ui.py"))
    m = re.search(r"--marca-grad:\s*linear-gradient\(90deg,([^)]*)\)", ui)
    paradas = []
    if m:
        paradas = [p.strip().split()[0].upper()
                   for p in m.group(1).split(",") if p.strip()]
    checar("  `--marca-grad` legivel em radai_ui.py (tres paradas)",
           len(paradas) == 3, str(paradas))

    svg = ler(os.path.join(APP, "favicon.svg"))
    stops = [s.upper() for s in re.findall(r'stop-color="(#[0-9A-Fa-f]{6})"', svg)]
    checar("  o favicon.svg usa as MESMAS paradas do --marca-grad",
           bool(paradas) and stops == paradas,
           "svg=%s marca=%s" % (stops, paradas))

    ger = ler(os.path.join("build", "gerar_icone.py"))
    mm = re.search(r"MARINHO\s*=\s*\(0x([0-9A-Fa-f]{2}),\s*0x([0-9A-Fa-f]{2}),"
                   r"\s*0x([0-9A-Fa-f]{2})\)", ger)
    marinho = ("#" + "".join(mm.groups())).upper() if mm else ""
    fundo = re.search(r'<rect[^>]*fill="(#[0-9A-Fa-f]{6})"', svg)
    checar("  o fundo do favicon.svg e o MARINHO do gerador",
           bool(marinho) and bool(fundo) and fundo.group(1).upper() == marinho,
           "svg=%s gerador=%s" % (fundo.group(1) if fundo else "?", marinho))
    checar("  o favicon.svg desenha em curva, sem <text>",
           "<path" in svg and "<text" not in svg)
    grad_ger = re.search(r"GRAD\s*=\s*\(\((.*?)\)\)", ger, re.S)
    hexes = []
    if grad_ger:
        for tripla in re.findall(r"\(?0x([0-9A-Fa-f]{2}),\s*0x([0-9A-Fa-f]{2}),"
                                 r"\s*0x([0-9A-Fa-f]{2})", grad_ger.group(0)):
            hexes.append(("#" + "".join(tripla)).upper())
    checar("  o gerador pinta com o --marca-grad",
           bool(paradas) and hexes == paradas,
           "gerador=%s marca=%s" % (hexes, paradas))


def main():
    print("=" * 66)
    print(" Radioterapia.AI - verificacao do projeto")
    print(" raiz: %s" % RAIZ)
    print("=" * 66)
    for fn in (checar_sintaxe, checar_acoplamento, checar_config,
               checar_chaves_da_v83,
               checar_arquivos, checar_ciclo_de_calibracao_apagado,
               checar_orfaos_da_v85_apagados,
               checar_o_que_saiu_vai_ao_orfaos,
               checar_dicom,
               checar_sem_dado_de_paciente_no_repositorio,
               checar_js_das_telas,
               checar_escapes_invalidos, checar_escape_que_o_python_come,
               checar_ts_map, checar_runner,
               checar_classes_css, checar_fim_de_linha,
               checar_goto_tem_rotulo, checar_contraste_dos_temas,
               checar_dado_de_app_embarca, checar_ascii_dos_lotes,
               checar_testes_mortos,
               checar_lateralidade_e_resolucao,
               checar_engine_no_escopo,
               checar_padrao_de_fabrica,
               checar_todo_import_aponta_para_arquivo,
               checar_contratos_de_motor,
               checar_motor_que_alimenta_vem_ligado,
               checar_recorte_no_corpo,
               checar_full_antes_dos_plugins,
               checar_todo_gravador_declara_o_desconto,
               checar_cadeia_do_full,
               checar_conferencias_na_caixa,
               checar_regras_de_gravacao,
               checar_trava_e_clip_box,
               checar_promessa_bate_com_quem_grava,
               checar_regra_seis,
               checar_quem_cria_job_le_o_log,
               checar_variaveis_de_ambiente,
               checar_getattr_de_nome_inventado,
               checar_cmd_chama_o_que_embarca,
               checar_lancador_acha_o_pacote,
               checar_marca_unica,
               checar_pacote_leve_completo,
               checar_rotas_vivas,
               checar_acervo_isolado_nas_baterias,
               checar_temporarias_do_app_na_faxina,
               checar_vigia_filho_isola_localappdata,
               checar_limpeza_das_baterias,
               checar_chaves_repetidas,
               checar_guarda_de_multiprocessing,
               checar_dado_de_literatura_embarcado,
               checar_tamanhos_declarados,
               checar_licenca_de_todo_modelo,
               checar_modulos_mortos,
               checar_tema_claro,
               checar_caminho_na_url,
               checar_variavel_lida_antes_de_existir,
               checar_tela_de_lote_fala_uma_lingua,
               checar_listas_de_preservados,
               checar_assinatura_das_rotas,
               checar_consulta_de_versao_nao_leva_nada,
               checar_icone_e_a_marca,
               checar_npm_so_no_preparo_da_porta):
        try:
            _r = fn()
            if _r is False:
                checar("%s reprovou (ver o detalhe acima)" % fn.__name__,
                       False, "a checagem devolveu False")
        except Exception as e:
            import traceback
            checar("%s (excecao)" % fn.__name__, False, "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    falhas = [(n, d) for n, ok, d in _RESULTADOS if not ok]
    print("\n" + "=" * 66)
    if falhas:
        print("FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n, d in falhas:
            print("  - %s%s" % (n, ("  [%s]" % d) if d else ""))
    else:
        print("OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print("=" * 66)
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--paciente-no-stage" in sys.argv[1:]:
        sys.exit(main_do_stage())
    sys.exit(main())
