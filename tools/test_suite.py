# -*- coding: utf-8 -*-
import io
import os
import re
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

import radai_modules as M

import _componentes
OFICINA = _componentes.oficina("suite", __file__)
_RESULTADOS = []
VERBOSO = "-v" in sys.argv


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    if VERBOSO or not ok:
        print("  %-6s %s%s" % ("OK" if ok else "FALHA", nome,
                               ("  [%s]" % detalhe) if detalhe else ""))


def secao(t):
    if VERBOSO:
        print("\n-- %s %s" % (t, "-" * max(0, 58 - len(t))))


def ler(rel):
    p = _componentes.fonte(rel)
    if not os.path.isfile(p):
        return ""
    return io.open(p, encoding="utf-8", errors="replace").read()


def norm(t):
    t = unicodedata.normalize("NFKD", str(t or ""))
    t = u"".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", u" ", t).lower()


FRASES_MARCA = (
    u"nada varre o volume",
    u"nao varre o volume procurando",
    u"nao procura o nodulo",
    u"nada pre-marca",
    u"nao pre-marca",
    u"nada sugere posicao",
    u"nao sugere posicao",
    u"nao lista suspeita",
    u"nao lista candidato",
    u"nao marca candidato",
    u"nada pontua",
    u"sem deteccao",
    u"nao ha deteccao",
    u"nunca detecta",
    u"o medico localiza",
    u"realce automatico",
)


def teste_nenhum_texto_promete_ausencia_de_deteccao():
    secao("nenhum texto dos modulos promete ausencia de deteccao")
    achados = []
    for _dono, campo, txt in _textos_dos_modulos(M):
        t = norm(_sem_marcas(txt))
        for f in FRASES_MARCA:
            if f in t:
                achados.append("%s: «%s»" % (campo, f))
    checar("nenhum texto de `radai_modules` repete a regra 6 antiga",
           not achados, "; ".join(achados[:6]))
    checar("  isca: a frase de antes («o médico localiza») e acusada",
           any(f in norm(u"Nada pre-marca: o médico localiza.")
               for f in FRASES_MARCA))


VERBOS = (u"varre|varred|procur|detect|deteccao|pre-marc|pre marc|pontua|"
          u"realc|sugere posicao|lista candidato|lista suspeita|"
          u"marca candidato|aponta")
PROMESSA = re.compile(
    u"(?:nao|nada|nenhum\\w*|nunca|sem)\\s+(?:\\w+\\s+){0,2}?(?:%s)" % VERBOS)

ESCOPOS = (u"de fabrica", u"por omissao", u"padrao", u"sozinh",
           u"por conta propria", u"sem alguem", u"ato declarad", u"declarad",
           u"so roda", u"quem liga", u"quem opera", u"ligad", u"marcad")


def teste_toda_negacao_de_deteccao_carrega_o_escopo():
    secao("negacao de deteccao no ContourLab vem com o escopo na mesma frase")
    sem_escopo, lidos = [], 0
    for _dono, campo, txt in _textos_dos_modulos(M):
        if u".autocontorno" not in campo:
            continue
        lidos += 1
        t = norm(_sem_marcas(txt))
        achou = PROMESSA.search(t)
        if achou and not any(e in t for e in ESCOPOS):
            sem_escopo.append("%s: «%s»" % (campo, achou.group(0)))
    checar("li os textos do ContourLab em `radai_modules` (%d)" % lidos,
           lidos >= 5, str(lidos))
    checar("toda negacao de deteccao nos textos do ContourLab diz em que "
           "condicao vale", not sem_escopo, "; ".join(sem_escopo[:6]))
    isca = norm(u"O programa não detecta tumor.")
    checar("  isca: a negacao sem escopo e acusada",
           bool(PROMESSA.search(isca)) and not any(e in isca for e in ESCOPOS))


FRASES_DO_QUE_SAIU = (u"modo completo",
                      u"modo padrao", u"vista-3d", u"cerebral_bleed",
                      u"liver_vessels", u"sangramento cerebral",
                      u"dentro do estudo", u"estudo do «rodar agora»",
                      u"calibrador", u"o compilador", u"no compilador",
                      u"do compilador", u"tela de calibracao")


def _textos_do_registro():
    for dono, campo, txt in _textos_dos_modulos(M):
        yield (dono, campo, txt)


REGISTROS_DOS_MODULOS = ("MODULOS", "FERRAMENTAS", "AJUDA", "ANUNCIOS")


def _folhas_de_texto(obj, caminho):
    if isinstance(obj, str):
        yield caminho, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            for par in _folhas_de_texto(v, "%s.%s" % (caminho, k)):
                yield par
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            for par in _folhas_de_texto(v, "%s[%d]" % (caminho, i)):
                yield par


def _textos_dos_modulos(mod):
    for nome in REGISTROS_DOS_MODULOS:
        for caminho, txt in _folhas_de_texto(getattr(mod, nome, None), nome):
            yield ("radai_modules", caminho, txt)


def _sem_marcas(t):
    return re.sub(r"<[^>]+>", "", t or "")


def _citam_o_que_saiu(textos):
    return ["%s.%s: «%s»" % (dono, campo, f)
            for dono, campo, txt in textos
            for f in FRASES_DO_QUE_SAIU if f in norm(_sem_marcas(txt))]


def teste_nenhum_texto_cita_o_que_saiu():
    secao("o registro e o roteiro nao citam modo, motor ou task que sairam")
    textos = list(_textos_do_registro())
    checar("li os textos do registro e do roteiro (%d)" % len(textos),
           len(textos) > 50, str(len(textos)))
    dos_modulos = [t for t in textos if t[0] == "radai_modules"]
    checar("  e os dos baloes e cartoes de `radai_modules` (%d)"
           % len(dos_modulos), len(dos_modulos) > 40, str(len(dos_modulos)))
    checar("  entre eles o `?` do AutoContorno",
           any(c.startswith("AJUDA.autocontorno.") for _d, c, _t in dos_modulos))
    achados = _citam_o_que_saiu(textos)
    checar("nenhum texto cita modo, motor ou task que saiu", not achados,
           "; ".join(achados[:4]))
    checar("  isca: um `nao_faz` que diga «o lote da noite executa o modo "
           "Padrao» e acusado",
           _citam_o_que_saiu([("x", "nao_faz[0]",
                               u"o lote da noite executa o modo Padrão")])
           == ["x.nao_faz[0]: «modo padrao»"])
    _velha = {"AJUDA": {"autocontorno": {u"O que não faz": (
        u"Não roda biblioteca de achado por omissão: o modo "
        u"<b>Padrão</b> é só anatomia, e é ele que o vigia da noite roda "
        u"de fábrica. Ligar detecção é escolha declarada, série a série.",)}}}

    class _Mod(object):
        AJUDA = _velha["AJUDA"]
    checar("  isca: o balao de antes (o modo <b>Padrao</b>, com a marca) e "
           "acusado",
           _citam_o_que_saiu(list(_textos_dos_modulos(_Mod)))
           == [u"radai_modules.AJUDA.autocontorno.O que não faz[0]: "
               u"«modo padrao»"])
    checar("  isca: e sem tirar as marcas ele passaria (o ponto cego)",
           not [f for f in FRASES_DO_QUE_SAIU
                if f in norm(_velha["AJUDA"]["autocontorno"][
                    u"O que não faz"][0])])
    checar("  isca: a regra B da v8.2 («marcar a caixa dela dentro do estudo») "
           "e acusada",
           _citam_o_que_saiu([("x", "regra_b", u"marcar a caixa dela dentro "
                                               u"do estudo, no «Rodar agora»")])
           == ["x.regra_b: «dentro do estudo»"])
    checar("  isca: o prints «na tela de calibração» e acusado",
           _citam_o_que_saiu([("x", "por_que", u"olhando os prints na tela "
                                               u"de calibração")])
           == ["x.por_que: «tela de calibracao»"])
    checar("  isca: o PERSONALIZADO da v8.3 e a identidade («compilador de "
           "modelos») passam",
           not _citam_o_que_saiu([("x", "a", u"ligar a chave no modo "
                                             u"PERSONALIZADO da série"),
                                  ("x", "b", u"Pós-processamento geométrico e "
                                             u"compilador de modelos que já "
                                             u"existem")]))


LISTAS_DO_NV = ("CLASSES_DE_ENTREGA", "CLASSES_DE_ACHADO",
                "CLASSES_FORA_DA_ENTREGA")


def _listas_do_nv(src):
    import ast
    try:
        arv = ast.parse(src or "")
    except SyntaxError:
        return None
    achou, uniao = {}, None
    for no in arv.body:
        if not (isinstance(no, ast.Assign) and len(no.targets) == 1
                and isinstance(no.targets[0], ast.Name)):
            continue
        nome, v = no.targets[0].id, no.value
        try:
            if nome in ("CLASSES_DE_ACHADO", "CLASSES_FORA_DA_ENTREGA") \
                    and isinstance(v, ast.Dict):
                achou[nome] = set(ast.literal_eval(v).keys())
            elif nome == "CLASSES_DE_ENTREGA" and isinstance(v, ast.Call) \
                    and len(v.args) == 1:
                achou[nome] = set(ast.literal_eval(v.args[0]))
            elif nome == "CLASSES_PERMITIDAS":
                uniao = set(n.id for n in ast.walk(v)
                            if isinstance(n, ast.Name)
                            and n.id.startswith("CLASSES_"))
        except (ValueError, TypeError, SyntaxError):
            return None
    if set(achou) != set(LISTAS_DO_NV) or uniao != set(LISTAS_DO_NV):
        return None
    return achou


def teste_as_contagens_do_nv_sao_as_do_motor():
    secao("fronteira: as contagens do NV-Segment-CT sao as do motor")
    listas = _listas_do_nv(ler("app/radai_nv_engine.py"))
    checar("li as tres listas do motor e a uniao delas (ast)",
           listas is not None)
    if listas is None:
        return
    e, a, f = (listas[n] for n in LISTAS_DO_NV)
    checar("as tres listas do motor sao disjuntas",
           len(e) + len(a) + len(f) == len(e | a | f),
           str((len(e), len(a), len(f))))
    checar("  isca: a lista so num comentario nao e lida",
           _listas_do_nv(u"# CLASSES_DE_ACHADO = {}\n") is None)
    checar("  isca: `CLASSES_PERMITIDAS` que deixa de ser a uniao nao passa",
           _listas_do_nv(
               u"CLASSES_DE_ENTREGA = frozenset(['a'])\n"
               u"CLASSES_DE_ACHADO = {'b': 'b'}\n"
               u"CLASSES_FORA_DA_ENTREGA = {'c': 'c'}\n"
               u"CLASSES_PERMITIDAS = frozenset(set(CLASSES_DE_ENTREGA))\n")
           is None)
    if OFICINA is None:
        _componentes.pulado(u"as contagens do NV no documento de engenharia")
    else:
        OFICINA.contagens_do_nv_no_documento(sys.modules[__name__], listas)


_RE_NUMERO_DE_ARQUIVOS = re.compile(
    r"\b(?:ate |no maximo )?(um|dois|tres|quatro|cinco|seis|sete|oito|nove|"
    r"dez|\d+) (arquivos|rtstruct|conjuntos)\b")


def _baloes_de_encontradas(html_):
    m = re.search(r'id="vr_sub_encontradas"(.*?)</h3>', html_ or "", re.S)
    return [_sem_marcas(p) for p in
            re.findall(r"<p>(.*?)</p>", m.group(1), re.S)] if m else []


def _balao_dos_conjuntos_certo(txt, rotulos):
    t = norm(txt)
    return (bool(txt) and not _RE_NUMERO_DE_ARQUIVOS.search(t)
            and all(norm(r) in t for r in rotulos))


def teste_o_balao_do_ver_conta_pelo_registro():
    secao("ver segmentacao: o balao dos conjuntos e o do registro")
    try:
        import radai_sets
        import radai_view
        html_ = radai_view._pagina()
    except Exception as e:
        checar("radai_view e radai_sets importam e a pagina rende", False,
               "%s: %s" % (type(e).__name__, e))
        return
    por_cod = dict((c["cod"], c) for c in radai_sets.CONJUNTOS)
    entregue = [c["rotulo_curto"] for c in radai_sets.CONJUNTOS
                if c.get("entregue")]
    checar("o registro tem UM conjunto entregue", len(entregue) == 1,
           str(entregue))
    rotulos = entregue[:1] + [por_cod[c]["rotulo_curto"]
                              for c in ("full", "ts") if c in por_cod]
    baloes = _baloes_de_encontradas(html_)
    dos_conj = [b for b in baloes if "marcas ao lado" in norm(b)]
    checar("achei o paragrafo do balao que fala dos arquivos da serie",
           len(dos_conj) == 1, "%d paragrafos" % len(baloes))
    txt = dos_conj[0] if dos_conj else u""
    checar("ele nao fixa numero de arquivos, e nomeia pelo registro: %s"
           % ", ".join(rotulos), _balao_dos_conjuntos_certo(txt, rotulos),
           txt[:160])
    checar("  isca: a frase de antes («ate cinco [...] So o AI_OAR») reprova",
           not _balao_dos_conjuntos_certo(
               u"Cada série entrega até cinco arquivos, e as marcas ao lado "
               u"dizem quais existem. Só o AI_OAR vai para o TPS.", rotulos))
    checar("  isca: o nome certo com um numero fixo tambem reprova",
           not _balao_dos_conjuntos_certo(
               txt.replace(u"um arquivo por conjunto",
                           u"até sete arquivos por conjunto"), rotulos))
    for forma in (u"cinco arquivos", u"sete RTSTRUCT",
                  u"no máximo cinco arquivos", u"6 conjuntos"):
        checar(u"  isca: «%s» com os nomes certos tambem reprova" % forma,
               not _balao_dos_conjuntos_certo(
                   txt.replace(u"um arquivo por conjunto", forma), rotulos))


def _nomes_mortos(nomes, mod):
    return [n for n in nomes or () if not isinstance(getattr(mod, n, None),
                                                     dict)]


def teste_a_topografia_so_procura_tabela_que_existe():
    secao("topografia: o recuo so procura tabela que existe em radai_modes")
    try:
        import radai_modes
        import radai_topography as T
    except Exception as e:
        checar("radai_modes e radai_topography importam", False,
               "%s: %s" % (type(e).__name__, e))
        return
    for nome in ("NOMES_DA_TABELA", "NOMES_DA_TABELA_MR"):
        nomes = getattr(T, nome, None)
        checar("`%s` existe e nao e vazio" % nome, bool(nomes), repr(nomes))
        checar("  e todo nome dele e uma tabela de `radai_modes`",
               not _nomes_mortos(nomes, radai_modes),
               ", ".join(_nomes_mortos(nomes, radai_modes)))
    checar("  isca: a tupla de antes (com PADRAO_POR_REGIAO) reprova",
           _nomes_mortos(("TASKS_POR_TOPOGRAFIA", "PADRAO_POR_REGIAO"),
                         radai_modes) == ["PADRAO_POR_REGIAO"])


def teste_as_crases_dos_documentos():
    if OFICINA is None:
        secao("crase: os documentos de engenharia")
        _componentes.pulado(u"as crases dos documentos de engenharia")
        return
    b = sys.modules[__name__]
    OFICINA.teste_o_que_nao_viaja_nao_leva_crase(b)
    OFICINA.teste_a_crase_de_modulo_aponta_para_o_que_existe(b)


_PALAVRA_DA_MODALIDADE = (("MR", u"rm"), ("PT", u"pet"))


def _tupla_do_fonte(src, padrao):
    m = re.search(padrao, src or u"", re.M)
    if not m:
        return None
    return tuple(re.findall(r"""["']([^"']+)["']""", m.group(1)))


def _modalidades_mal_ditas(txt, mods):
    t = norm(_sem_marcas(txt))
    fora = []
    for cod, palavra in _PALAVRA_DA_MODALIDADE:
        diz = bool(re.search(r"\b%s\b" % palavra, t))
        if (cod in (mods or ())) != diz:
            fora.append(u"%s %s" % ("cala" if not diz else "promete", palavra))
    return fora


def _texto_da_ferramenta(mod, cod):
    for f in (getattr(M, "FERRAMENTAS", {}) or {}).get(mod, ()):
        if f[0] == cod:
            return f[4]
    return u""


def _constantes_int(src, nomes):
    import ast
    fora = {}
    try:
        arv = ast.parse(src or "")
    except SyntaxError:
        return fora
    for no in arv.body:
        if isinstance(no, ast.Assign):
            for t in no.targets:
                if (isinstance(t, ast.Name) and t.id in nomes
                        and isinstance(no.value, ast.Constant)
                        and isinstance(no.value.value, int)):
                    fora[t.id] = no.value.value
    return fora


def _faixas_do_bolus_caladas(txt, k):
    t = norm(_sem_marcas(txt))
    fora = []
    for a, b, o_que in (("ESPESSURA_MIN_MM", "ESPESSURA_MAX_MM", u"espessura"),
                        ("CASCA_MIN_MM", "CASCA_MAX_MM", u"casca")):
        if a in k and b in k and (u"%d a %d mm" % (k[a], k[b])) not in t:
            fora.append(u"%s %d a %d mm" % (o_que, k[a], k[b]))
    if u"molde" not in t:
        fora.append(u"molde")
    return fora


def teste_o_registro_diz_o_que_a_tela_aceita():
    secao("o registro diz o que a tela aceita (modalidade, faixa, modo)")
    mods_n = _tupla_do_fonte(ler("app/radai_nidus_screen.py"),
                             r"^MODALIDADES\s*=\s*\(([^)]*)\)")
    checar("li as modalidades do seletor do Nidus (%s)" % (mods_n,),
           bool(mods_n))
    for dono, txt in ((u"FERRAMENTAS nidus_projecao",
                       _texto_da_ferramenta("nidus", "nidus_projecao")),):
        ruim = _modalidades_mal_ditas(txt, mods_n)
        checar("%s diz as modalidades que a tela lista" % dono, not ruim,
               "; ".join(ruim))
    checar("  isca: o texto de antes («Projeta a angiotomografia») cala a RM",
           _modalidades_mal_ditas(u"Projeta a angiotomografia na incidência "
                                  u"escolhida", ("CT", "MR"))
           == [u"cala rm"])
    checar("  isca: prometer RM que a tela nao lista tambem reprova",
           _modalidades_mal_ditas(u"a angiotomografia ou a RM", ("CT",))
           == [u"promete rm"])
    mods_e = _tupla_do_fonte(ler("app/radai_elastic_screen.py"),
                             r"^MODALIDADES\s*=\s*\(([^)]*)\)")
    checar("li as modalidades que o Elastic varre (%s)" % (mods_e,),
           bool(mods_e))
    for dono, txt in ((u"FERRAMENTAS elastic_fusao",
                       _texto_da_ferramenta("elastic", "elastic_fusao")),):
        ruim = _modalidades_mal_ditas(txt, mods_e)
        checar("%s diz as modalidades que a tela funde" % dono, not ruim,
               "; ".join(ruim))
    webgl = "getContext('webgl'" in ler("app/radai_recon3d_screen.py")
    checar("a tela das Reconstrucoes tem o renderizador WebGL", webgl)
    comp = u" ".join((getattr(M, "AJUDA", {}).get("recon3d") or {}).get(
        u"Componentes de terceiros") or ())
    _ok_r = lambda t: (u"malha" in norm(t) and u"webgl" in norm(t)) is webgl
    checar("o `?` das Reconstrucoes diz a malha em WebGL", _ok_r(comp),
           comp[:120])
    checar("  isca: o `?` de antes (a nuvem «sem WebGL») reprova",
           not _ok_r(u"o 3D é uma nuvem de pontos com numpy e scipy.ndimage, "
                     u"desenhada em canvas 2D, sem WebGL."))
    anat = _texto_da_ferramenta("recon3d", "recon_anatomia")
    # GUARDA: o cartão diz visor 3D com transparência por órgão, que é o que o renderizador de malha entrega.
    _ok_a = lambda t: (u"visor 3d" in norm(t) and u"transparenc" in norm(t)) or not webgl
    checar("o cartao da Anatomia geral diz o visor 3D com transparencia",
           _ok_a(anat), anat[:120])
    checar("  isca: um cartao sem o 3D reprova",
           not _ok_a(u"Três planos, MIP e MinIP com laje ajustável."))
    k = _constantes_int(ler("app/radai_bolus.py"),
                        ("ESPESSURA_MIN_MM", "ESPESSURA_MAX_MM",
                         "CASCA_MIN_MM", "CASCA_MAX_MM"))
    checar("li as faixas do motor do bolus (%s)" % sorted(k.items()),
           len(k) == 4)
    # GUARDA: a faixa da espessura vai na TAG, e a tag tem de ser a do motor.
    _tags_b = ()
    for f in (getattr(M, "FERRAMENTAS", {}) or {}).get("bolus", ()):
        if f[0] == "bolus_gerar" and len(f) > 6:
            _tags_b = f[6]
    _faixa = u"camada %d-%d mm" % (k.get("ESPESSURA_MIN_MM", -1),
                                   k.get("ESPESSURA_MAX_MM", -1))
    checar("a tag do cartao do bolus diz a faixa do motor (%s)" % _faixa,
           _faixa in _tags_b and u"molde" in _tags_b, repr(_tags_b))
    checar("  isca: uma faixa diferente da do motor reprova",
           (u"camada %d-%d mm" % (k.get("ESPESSURA_MIN_MM", -1),
                                  k.get("ESPESSURA_MAX_MM", -1) + 1)) not in _tags_b)
    checar("  isca: o cartao de antes («a camada de N mm») reprova nas tres",
           len(_faixas_do_bolus_caladas(
               u"gera a camada de N mm (Anatômico) ou o bloco que encaixa",
               {"ESPESSURA_MIN_MM": 1, "ESPESSURA_MAX_MM": 30,
                "CASCA_MIN_MM": 1, "CASCA_MAX_MM": 4})) == 3)
    rotulos = re.findall(r'"cod":\s*"(?:fast|auto|perso)",\s*"rotulo":\s*'
                         r'u?"([^"]+)"', ler("app/radai_batch.py"))
    checar("li os rotulos dos modos na tela do «Rodar agora» (%s)" % rotulos,
           len(rotulos) == 3, str(rotulos))
    # GUARDA: o cartão não nomeia modo; quem os nomeia é o `?` do ContourLab, ao lado do título.
    lote = u" ".join(u" ".join(v) for v in M.secoes_de_ajuda("autocontorno").values())
    faltam = [r for r in rotulos if r not in lote]
    checar("o `?` do ContourLab nomeia os tres modos", not faltam,
           ", ".join(faltam))
    checar("  isca: o cartao de antes («cada motor entrega o conjunto dele») "
           "reprova",
           [r for r in rotulos if r not in
            u"Um caso ou uma pasta inteira. Você escolhe as séries, e cada "
            u"motor entrega o conjunto dele, separado, para comparar."])


_PROMESSA_DE_VERSAO = re.compile(
    r"(?:candidat[oa]s? d[ao]|escrit[oa]s? para a|fica para a|entra na|"
    r"prometid[oa]s? para a)\s+v(\d+)\.(\d+)")


def _versao(txt):
    m = re.match(r"^\s*(\d+)\.(\d+)", txt or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _promessas_vencidas(textos, versao):
    fora = []
    for dono, campo, txt in textos:
        for m in _PROMESSA_DE_VERSAO.finditer(norm(txt)):
            v = (int(m.group(1)), int(m.group(2)))
            if versao and v <= versao:
                fora.append("%s.%s: v%d.%d" % (dono, campo, v[0], v[1]))
    return fora


def teste_o_registro_nao_promete_o_que_venceu():
    secao("o registro nao promete para a versao em curso nem para uma anterior")
    ent = None
    for linha in ler("entrega.txt").splitlines():
        if linha.startswith("VERSAO="):
            ent = _versao(linha.split("=", 1)[1])
    checar("li a VERSAO do entrega.txt (%s)" % (ent,), bool(ent))
    textos = [t for t in _textos_do_registro() if t[0] != "radai_modules"]
    vencidas = _promessas_vencidas(textos, ent)
    checar("nenhum texto do registro promete para a VERSAO do entrega.txt "
           "ou para uma anterior", bool(ent) and not vencidas,
           "; ".join(vencidas[:4]))
    checar("  isca: «NÃO implementada na v8.2 — escrita para a v8.3» e "
           "acusada em dia com a 8.3",
           _promessas_vencidas([("x", "estado", u"NÃO implementada na v8.2 — "
                                                u"escrita para a v8.3")],
                               (8, 3)) == ["x.estado: v8.3"])
    checar("  isca: e a promessa para a versao SEGUINTE passa",
           not _promessas_vencidas([("x", "estado", u"candidato da v8.4")],
                                   (8, 3)))


def main():
    print("=" * 64)
    print(" test_suite — os textos dos modulos, as crases e o que a tela aceita")
    print("=" * 64)
    testes = [teste_nenhum_texto_promete_ausencia_de_deteccao,
              teste_toda_negacao_de_deteccao_carrega_o_escopo,
              teste_nenhum_texto_cita_o_que_saiu,
              teste_as_contagens_do_nv_sao_as_do_motor,
              teste_o_balao_do_ver_conta_pelo_registro,
              teste_a_topografia_so_procura_tabela_que_existe,
              teste_as_crases_dos_documentos,
              teste_o_registro_diz_o_que_a_tela_aceita,
              teste_o_registro_nao_promete_o_que_venceu]
    for t in testes:
        try:
            t()
        except (Exception, SystemExit) as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    falhas = [(n, d) for n, ok, d in _RESULTADOS if not ok]
    print("\n" + "=" * 64)
    if falhas:
        print("FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n, d in falhas:
            print("  - %s%s" % (n, ("  [%s]" % d) if d else ""))
    else:
        print("OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print("=" * 64)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
