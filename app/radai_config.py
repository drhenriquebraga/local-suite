# -*- coding: utf-8 -*-
import io
import json
import os
import re
from pathlib import Path

VERSAO_CONFIG = "1.0"


def ler_bruto(texto):
    valores = {}
    for linha in (texto or u"").lstrip(u"﻿").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        valores[k.strip()] = v.strip()
    return valores


def ler_arquivo(caminho):
    try:
        p = Path(caminho)
        if not p.exists():
            return u"", {}
        texto = p.read_text(encoding="utf-8-sig", errors="ignore")
        return texto, ler_bruto(texto)
    except Exception:
        return u"", {}


NOME_CONFIG = "radai_watcher.config"


def caminho_padrao():
    return (os.environ.get("RADAI_CONFIG")
            or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            NOME_CONFIG))


def root_configurado():
    return chave_configurada("ROOT")


def comentarios(texto):
    ajuda, bloco = {}, []
    for linha in (texto or "").splitlines():
        cru = linha.strip()
        if cru.startswith("#"):
            limpo = cru.lstrip("#").strip()
            moldura = (set(limpo) <= set(u"─-=_ ")
                       or limpo[:3] in (u"───", u"---", u"==="))
            if limpo and not moldura:
                bloco.append(limpo)
        elif cru and "=" in cru:
            ajuda[cru.split("=", 1)[0].strip()] = " ".join(bloco)
            bloco = []
        else:
            bloco = []
    return ajuda


def chave_configurada(nome):
    try:
        _texto, valores = ler_arquivo(caminho_padrao())
        return (valores.get(nome) or "").split("#")[0].strip().strip('"')
    except Exception:
        return ""


def escrever(caminho, mudancas, modelo=u""):
    mudancas = dict(mudancas or {})
    for k, v in mudancas.items():
        if "\n" in str(v) or "\r" in str(v):
            return False, u"o valor de %s tem quebra de linha" % k

    p = Path(caminho)
    try:
        texto = p.read_text(encoding="utf-8-sig", errors="ignore") if p.exists() else (modelo or u"")
    except Exception as e:
        return False, u"nao consegui ler o config atual (%s)" % e

    restantes, saida = dict(mudancas), []
    for linha in texto.splitlines():
        cru = linha.strip()
        if cru and not cru.startswith("#") and "=" in cru:
            chave = cru.split("=", 1)[0].strip()
            if chave in restantes:
                saida.append(u"%s=%s" % (chave, str(restantes.pop(chave)).strip()))
                continue
        saida.append(linha)
    for chave in [c for c in mudancas if c in restantes]:
        saida.append(u"")
        saida.append(u"# acrescentado pela tela de configuracoes")
        saida.append(u"%s=%s" % (chave, str(restantes[chave]).strip()))

    novo = u"\n".join(saida).rstrip(u"\n") + u"\n"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(novo, encoding="utf-8")
        os.replace(str(tmp), str(p))
        return True, u""
    except Exception as e:
        return False, u"nao consegui gravar em %s (%s)" % (caminho, e)


def _moldura(limpo):
    return (set(limpo) <= set(u"─-=_ ") or limpo[:3] in (u"───", u"---", u"==="))


def remover(caminho, chaves, copia=True, agora=None):
    alvo = set(chaves or ())
    p = Path(caminho)
    try:
        if not p.exists():
            return True, [], u"", u""
        bruto = p.read_bytes()
        texto = bruto.decode("utf-8-sig", "ignore")
    except Exception as e:
        return False, [], u"", u"nao consegui ler o config atual (%s)" % e
    linhas = texto.splitlines()
    fora, removidas = set(), []
    for i, linha in enumerate(linhas):
        cru = linha.strip()
        if not cru or cru.startswith("#") or "=" not in cru:
            continue
        chave = cru.split("=", 1)[0].strip()
        if chave not in alvo:
            continue
        fora.add(i)
        if chave not in removidas:
            removidas.append(chave)
        j = i - 1
        # GUARDA: só o bloco de ajuda colado na chave; a moldura de seção e o
        # que vem depois de uma linha em branco são de outras chaves.
        while j >= 0:
            c = linhas[j].strip()
            if not c.startswith("#") or _moldura(c.lstrip("#").strip()):
                break
            fora.add(j)
            j -= 1
    if not removidas:
        return True, [], u"", u""
    novo = u"\n".join(l for i, l in enumerate(linhas) if i not in fora)
    while u"\n\n\n" in novo:
        novo = novo.replace(u"\n\n\n", u"\n\n")
    novo = novo.strip(u"\n") + u"\n"
    destino_copia = u""
    try:
        if copia:
            import datetime as _dt
            marca = (agora or _dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
            destino_copia = str(p.with_name(p.name + ".antes-da-migracao-" + marca))
            Path(destino_copia).write_bytes(bruto)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(novo, encoding="utf-8")
        os.replace(str(tmp), str(p))
        return True, removidas, destino_copia, u""
    except Exception as e:
        return False, [], destino_copia, u"nao consegui gravar em %s (%s)" % (caminho, e)


TPS_VALIDOS = ("eclipse", "monaco")
TPS_PADRAO = "eclipse"

# GUARDA: o valor gravado (eclipse/monaco) e identidade em disco que o motor e o DicomBridge leem; o nome na tela mora aqui.
TPS_ROTULOS = {"eclipse": u"Eclipse / Monaco", "monaco": u"Xio / Focal"}


def tps_canonico(bruto):
    v = str(bruto or u"").split("#")[0].strip().strip('"').lower()
    return v if v in TPS_VALIDOS else u""


def rotulo_do_tps(bruto):
    return TPS_ROTULOS.get(tps_canonico(bruto), u"")


def tps_destino():
    return tps_canonico(chave_configurada("TPS_DESTINO"))


def _unidades():
    if os.name != "nt":
        return ["/"]
    achadas = []
    for letra in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        raiz = "%s:\\" % letra
        try:
            if os.path.exists(raiz):
                achadas.append(raiz)
        except Exception:
            pass
    return achadas


EXTENSOES_LISTAVEIS = (".zip",)


def _sem_acento(s):
    import unicodedata
    return u"".join(c for c in unicodedata.normalize("NFD", str(s or "").lower())
                    if unicodedata.category(c) != "Mn")


def listar_pastas(caminho="", arquivos="", busca=""):
    r = {"caminho": "", "pai": "", "pastas": [], "arquivos": [],
         "unidades": [], "erro": "", "busca": "", "achados": -1}
    pedidas = tuple(e for e in str(arquivos or "").lower().replace(" ", "").split(",")
                    if e in EXTENSOES_LISTAVEIS)
    try:
        r["unidades"] = _unidades()
        bruto = str(caminho or "").strip().strip('"')
        if not bruto:
            return r
        p = Path(bruto)
        if not p.is_dir():
            r["erro"] = u"nao e uma pasta acessivel desta maquina"
            return r
        r["caminho"] = str(p)
        pai = p.parent
        r["pai"] = "" if str(pai) == str(p) else str(pai)
        nomes, arqs = [], []
        try:
            for entrada in os.scandir(str(p)):
                try:
                    if entrada.is_dir():
                        nomes.append(entrada.name)
                    elif pedidas and entrada.name.lower().endswith(pedidas):
                        arqs.append(entrada.name)
                except Exception:
                    pass
        except PermissionError as e:
            r["erro"] = u"sem permissao para listar (%s)" % e
            return r
        termo = _sem_acento(busca)
        if termo:
            nomes = [n for n in nomes if termo in _sem_acento(n)]
            arqs = [n for n in arqs if termo in _sem_acento(n)]
            r["busca"] = str(busca or "").strip()
            r["achados"] = len(nomes)
        nomes.sort(key=lambda s: s.lower())
        r["pastas"] = [{"nome": n, "caminho": str(p / n)} for n in nomes[:1500]]
        arqs.sort(key=lambda s: s.lower())
        r["arquivos"] = [{"nome": n, "caminho": str(p / n)} for n in arqs[:1500]]
        if len(nomes) > 1500:
            r["erro"] = (u"mostrando 1500 de %d pastas — %s"
                         % (len(nomes),
                            u"refine a busca" if termo else
                            u"use a busca, ou digite o caminho para ir direto"))
    except Exception as e:
        r["erro"] = u"%s: %s" % (type(e).__name__, e)
    return r


def validar_pasta(caminho):
    r = {"caminho": caminho or "", "vazio": not str(caminho or "").strip(),
         "existe": False, "leitura": False, "escrita": False, "erro": "", "aviso": "",
         "codigo": "", "detalhe": ""}
    if r["vazio"]:
        r["aviso"] = (u"ROOT vazio: o vigia sobe o painel e nao varre nada. "
                      u"E o padrao de fabrica, proposital.")
        return r
    try:
        p = Path(str(caminho).strip().strip('"'))
        r["existe"] = p.is_dir()
        if not r["existe"]:
            r["erro"] = u"a pasta nao existe ou nao esta acessivel desta maquina"
            r["codigo"] = "nao_existe"
            return r
        try:
            next(iter(os.scandir(str(p))), None)
            r["leitura"] = True
        except Exception as e:
            r["erro"] = u"sem permissao de leitura (%s)" % e
            r["codigo"], r["detalhe"] = "sem_leitura", u"%s" % e
            return r
        teste = p / ("_radai_teste_escrita_%d.tmp" % os.getpid())
        try:
            teste.write_text(u"x", encoding="utf-8")
            r["escrita"] = True
        except Exception as e:
            r["erro"] = (u"da para LER mas NAO para escrever (%s). O vigia grava o "
                         u"RTSTRUCT e os marcadores _RadAI na propria pasta da serie: "
                         u"sem escrita, nenhuma serie e processada. Fale com o TI." % e)
            r["codigo"], r["detalhe"] = "sem_escrita", u"%s" % e
        finally:
            try:
                teste.unlink()
            except Exception:
                pass
    except Exception as e:
        r["erro"] = u"%s: %s" % (type(e).__name__, e)
        r["codigo"], r["detalhe"] = "erro", r["erro"]
    return r


def pasta_favorita():
    return chave_configurada("PASTA_FAVORITA")


def validar_favorita(caminho):
    r = {"caminho": caminho or "", "vazio": not str(caminho or "").strip(),
         "existe": False, "leitura": False, "codigo": "", "detalhe": ""}
    if r["vazio"]:
        return r
    try:
        p = Path(str(caminho).strip().strip('"'))
        r["existe"] = p.is_dir()
        if not r["existe"]:
            r["codigo"] = "nao_existe"
            return r
        try:
            next(iter(os.scandir(str(p))), None)
            r["leitura"] = True
        except Exception as e:
            r["codigo"], r["detalhe"] = "sem_leitura", u"%s" % e
    except Exception as e:
        r["codigo"], r["detalhe"] = "erro", u"%s: %s" % (type(e).__name__, e)
    return r


def gravar_tps(caminho, tps, modelo=u""):
    t = tps_canonico(tps)
    if not t:
        return False, u"escolha eclipse ou monaco"
    return escrever(caminho, {"TPS_DESTINO": t}, modelo=modelo)


NOME_DOS_NOMES = "nomes_proprios.json"
NOME_DOS_PROTOCOLOS = "protocolos_proprios.json"
MODOS_DOS_NOMES = ("padrao", "proprios")
LIMITE_DO_NOME = 16
LIMITE_DO_NOME_DO_PROTOCOLO = 60
MODALIDADES = ("CT", "MR")
# GUARDA: nome de alvo ou de contorno externo numa sugestao de orgao confunde quem
# planeja, e o TPS pode tratar BODY/External como o corpo.
PREFIXOS_DE_ALVO = ("GTV", "CTV", "ITV", "PTV")
NOMES_DE_CORPO = ("BODY", "EXTERNAL")

MOTIVO_ESPACO = u"sem espaço no começo nem no fim"
MOTIVO_LIMITE = u"até 16 caracteres"
MOTIVO_ASCII = u"só letras sem acento, números e sinais do teclado (ASCII)"
MOTIVO_CONTRABARRA = u"sem contrabarra: o DICOM a usa como separador"
MOTIVO_RESERVADO = (u"nome reservado a alvo (GTV, CTV, ITV, PTV) ou ao contorno "
                    u"externo (BODY, External)")
MOTIVO_REPETIDO = u"repete o nome de outra estrutura"
MOTIVO_REPETE_UNIAO = u"repete o nome de uma união de um protocolo próprio"
MOTIVO_DESCONHECIDA = u"estrutura que esta instalação não conhece"
MOTIVO_DESCONHECIDAS = u"estrutura que esta instalação não conhece: %s"
MOTIVO_SEM_LISTA = u"a lista de estruturas não está disponível nesta instalação"
MOTIVO_SEM_NOME_PROT = u"dê um nome ao protocolo"
MOTIVO_NOME_PROT_LONGO = u"até 60 caracteres"
MOTIVO_NOME_PROT_REPETIDO = u"já existe um protocolo com este nome nesta modalidade"
MOTIVO_MODALIDADE = u"escolha TC ou RM"
MOTIVO_VAZIO = u"escolha pelo menos uma estrutura"
MOTIVO_SEM_NOME_UNIAO = u"dê um nome à união"
MOTIVO_UNIAO_CURTA = u"uma união precisa de pelo menos duas estruturas"
MOTIVO_UNIAO_REPETIDA = u"repete o nome de outra estrutura deste protocolo"


def ao_lado_do_config(nome, caminho_cfg=None):
    base = caminho_cfg or caminho_padrao()
    return os.path.join(os.path.dirname(os.path.abspath(base)), nome)


def _ler_json(caminho):
    try:
        with io.open(caminho, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def _gravar_json(caminho, dados):
    try:
        pasta = os.path.dirname(os.path.abspath(caminho))
        if not os.path.isdir(pasta):
            os.makedirs(pasta)
        tmp = caminho + ".tmp"
        with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write(u"\n")
        os.replace(tmp, caminho)
        return True, u""
    except Exception as e:
        return False, u"nao consegui gravar em %s (%s)" % (caminho, e)


def modalidade_canonica(bruto):
    v = str(bruto or u"").strip().upper()
    return {"TC": "CT", "RM": "MR"}.get(v, v if v in MODALIDADES else u"")


def motivo_do_nome(nome):
    s = u"" if nome is None else u"%s" % nome
    if not s:
        return u""
    if s != s.strip():
        return MOTIVO_ESPACO
    if any(ord(c) < 32 or ord(c) > 126 for c in s):
        return MOTIVO_ASCII
    if len(s) > LIMITE_DO_NOME:
        return MOTIVO_LIMITE
    if u"\\" in s:
        return MOTIVO_CONTRABARRA
    alto = s.upper()
    if alto in NOMES_DE_CORPO or alto.startswith(PREFIXOS_DE_ALVO):
        return MOTIVO_RESERVADO
    return u""


def _limpar_nomes(bruto):
    saida = {}
    if isinstance(bruto, dict):
        for k, v in bruto.items():
            if (isinstance(k, str) and isinstance(v, str)
                    and k.strip() and v != u""):
                saida[k.strip()] = v
    return saida


def _limpar_cores(bruto):
    if not isinstance(bruto, dict):
        return {}
    return {k: list(v) for k, v in bruto.items()
            if isinstance(k, str) and k.strip()
            and isinstance(v, (list, tuple)) and len(v) == 3
            and all(type(c) is int and 0 <= c <= 255 for c in v)}


def cor_propria(nome_padrao, cfg=None, caminho_cfg=None):
    d = ler_nomes(caminho_cfg) if cfg is None else cfg
    if d.get("modo") != "proprios":
        return None
    cor = _limpar_cores(d.get("cores")).get(nome_padrao)
    return tuple(cor) if cor is not None else None


def ler_nomes(caminho_cfg=None):
    d = _ler_json(ao_lado_do_config(NOME_DOS_NOMES, caminho_cfg))
    d = d if isinstance(d, dict) else {}
    modo = d.get("modo") if d.get("modo") in MODOS_DOS_NOMES else u"padrao"
    return {"modo": modo, "nomes": _limpar_nomes(d.get("nomes")),
            "cores": _limpar_cores(d.get("cores"))}


def modo_dos_nomes(caminho_cfg=None):
    return ler_nomes(caminho_cfg)["modo"]


def nomes_proprios(caminho_cfg=None):
    d = ler_nomes(caminho_cfg)
    if d["modo"] != u"proprios":
        return {}
    # GUARDA: arquivo editado a mao nao leva ao DICOM o nome que a tela recusa.
    return dict((k, v) for k, v in d["nomes"].items() if not motivo_do_nome(v))


def _padroes_da_lista(linhas):
    vistos = []
    for l in linhas or ():
        n = (l or {}).get("nome_padrao") if isinstance(l, dict) else None
        if n and n not in vistos:
            vistos.append(n)
    return vistos


def unioes_por_modalidade(protocolos):
    saida = {}
    for p in protocolos or ():
        for m in p.get("merges") or ():
            nome = (m or {}).get("nome") or u""
            if nome:
                saida.setdefault(p.get("modalidade") or u"", set()).add(
                    nome.casefold())
    return saida


def conferir_nomes(nomes, estruturas_por_modalidade, protocolos=()):
    nomes = _limpar_nomes(nomes)
    erros = {}
    listas = dict((m, _padroes_da_lista(l))
                  for m, l in (estruturas_por_modalidade or {}).items())
    if not any(listas.values()):
        if nomes:
            erros[u""] = MOTIVO_SEM_LISTA
        return erros
    for k, v in nomes.items():
        m = motivo_do_nome(v)
        if m:
            erros[k] = m
    conhecidas = set()
    for padroes in listas.values():
        conhecidas.update(padroes)
    for k in nomes:
        if k not in conhecidas and k not in erros:
            erros[k] = MOTIVO_DESCONHECIDA
    unioes = unioes_por_modalidade(protocolos)
    for mod, padroes in listas.items():
        grupos = {}
        for n in padroes:
            efetivo = nomes.get(n) or n
            grupos.setdefault(efetivo.casefold(), []).append(n)
        for membros in grupos.values():
            if len(membros) < 2:
                continue
            for n in membros:
                if nomes.get(n) and n not in erros:
                    erros[n] = MOTIVO_REPETIDO
        for n in padroes:
            v = nomes.get(n)
            if v and n not in erros and v.casefold() in unioes.get(mod, ()):
                erros[n] = MOTIVO_REPETE_UNIAO
    return erros


def gravar_nomes(modo, nomes, estruturas_por_modalidade, protocolos=None,
                 caminho_cfg=None, cores=None):
    modo = modo if modo in MODOS_DOS_NOMES else u"padrao"
    nomes = _limpar_nomes(nomes)
    if cores is None:
        cores = ler_nomes(caminho_cfg).get("cores", {})
    limpas = _limpar_cores(cores)
    conhecidas = set(n for ls in (estruturas_por_modalidade or {}).values()
                     for n in _padroes_da_lista(ls))
    if not isinstance(cores, dict) or len(limpas) != len(cores) or set(limpas) - conhecidas:
        return False, {"ok": False, "erro": u"Cor inválida: use três inteiros de 0 a 255 para uma estrutura conhecida.", "erros": {}}
    cores = limpas
    if protocolos is None:
        protocolos = ler_protocolos(caminho_cfg)
    erros = conferir_nomes(nomes, estruturas_por_modalidade, protocolos)
    if erros:
        return False, {"ok": False, "erros": erros}
    ok, erro = _gravar_json(ao_lado_do_config(NOME_DOS_NOMES, caminho_cfg),
                            {"versao": 1, "modo": modo, "nomes": nomes, "cores": cores})
    if not ok:
        return False, {"ok": False, "erro": erro, "erros": {}}
    return True, {"ok": True, "modo": modo, "nomes": nomes, "cores": cores, "erros": {}}


_ID_DO_PROTOCOLO = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _id_novo():
    return u"p" + os.urandom(5).hex()


def _limpar_protocolo(bruto):
    if not isinstance(bruto, dict):
        return None
    ident = u"%s" % (bruto.get("id") or u"")
    estruturas = []
    for e in bruto.get("estruturas") or ():
        if isinstance(e, str) and e.strip() and e.strip() not in estruturas:
            estruturas.append(e.strip())
    merges = []
    for m in bruto.get("merges") or ():
        if not isinstance(m, dict):
            continue
        de = []
        for e in m.get("de") or ():
            if isinstance(e, str) and e.strip() and e.strip() not in de:
                de.append(e.strip())
        merges.append({"nome": u"%s" % (m.get("nome") or u""), "de": de})
    return {"id": ident if _ID_DO_PROTOCOLO.match(ident) else u"",
            "nome": u"%s" % (bruto.get("nome") or u""),
            "modalidade": modalidade_canonica(bruto.get("modalidade")),
            "estruturas": estruturas, "merges": merges,
            "tem_achado": bool(bruto.get("tem_achado"))}


def ler_protocolos(caminho_cfg=None):
    d = _ler_json(ao_lado_do_config(NOME_DOS_PROTOCOLOS, caminho_cfg))
    lista = d.get("protocolos") if isinstance(d, dict) else None
    saida = []
    for p in lista or ():
        q = _limpar_protocolo(p)
        if q and q["id"] and q["modalidade"]:
            saida.append(q)
    return saida


def protocolos_proprios(modalidade=None, caminho_cfg=None):
    m = modalidade_canonica(modalidade) if modalidade else None
    return [p for p in ler_protocolos(caminho_cfg)
            if m is None or p["modalidade"] == m]


def tasks_de_achado():
    try:
        import radai_sets
        return frozenset(p["task"] for p in radai_sets.PLUGINS
                         if p.get("achado"))
    except Exception:
        return frozenset()


def conferir_protocolo(bruto, linhas, nomes=None, outros=(), achados=None):
    p = _limpar_protocolo(bruto) or _limpar_protocolo({})
    erros = {}
    if not p["id"]:
        p["id"] = _id_novo()
    p["nome"] = p["nome"].strip()
    if not p["nome"]:
        erros["nome"] = MOTIVO_SEM_NOME_PROT
    elif len(p["nome"]) > LIMITE_DO_NOME_DO_PROTOCOLO:
        erros["nome"] = MOTIVO_NOME_PROT_LONGO
    elif any(ord(c) < 32 for c in p["nome"]):
        erros["nome"] = MOTIVO_ASCII
    if not p["modalidade"]:
        erros["modalidade"] = MOTIVO_MODALIDADE
    if "nome" not in erros and p["modalidade"]:
        for o in outros or ():
            if (o.get("id") != p["id"] and o.get("modalidade") == p["modalidade"]
                    and (o.get("nome") or u"").strip().casefold()
                    == p["nome"].casefold()):
                erros["nome"] = MOTIVO_NOME_PROT_REPETIDO
                break
    validas = [l for l in linhas or ()
               if isinstance(l, dict) and l.get("protocolo") is not False]
    padroes = _padroes_da_lista(validas)
    task_de = dict(((l.get("nome_padrao"), l.get("task") or u"") for l in validas))
    achado_de = set(l.get("nome_padrao") for l in validas if l.get("achado"))
    if not padroes:
        erros["estruturas"] = MOTIVO_SEM_LISTA
        return p, erros
    fora = [e for e in p["estruturas"] if e not in padroes]
    if fora:
        erros["estruturas"] = MOTIVO_DESCONHECIDAS % u", ".join(fora[:6])
    if not p["estruturas"] and not p["merges"]:
        erros["estruturas"] = MOTIVO_VAZIO
    nomes = _limpar_nomes(nomes)
    usados = dict(((nomes.get(e) or e).casefold(), e) for e in p["estruturas"])
    for i, m in enumerate(p["merges"]):
        chave = u"uniao:%d" % i
        if not m["nome"]:
            erros[chave] = MOTIVO_SEM_NOME_UNIAO
            continue
        motivo = motivo_do_nome(m["nome"])
        if motivo:
            erros[chave] = motivo
            continue
        fora_u = [e for e in m["de"] if e not in padroes]
        if fora_u:
            erros[chave] = MOTIVO_DESCONHECIDAS % u", ".join(fora_u[:6])
            continue
        if len(m["de"]) < 2:
            erros[chave] = MOTIVO_UNIAO_CURTA
            continue
        if m["nome"].casefold() in usados:
            erros[chave] = MOTIVO_UNIAO_REPETIDA
            continue
        usados[m["nome"].casefold()] = m["nome"]
    achados = tasks_de_achado() if achados is None else frozenset(achados)
    partes = set(p["estruturas"])
    for m in p["merges"]:
        partes.update(m["de"])
    p["tem_achado"] = any(task_de.get(e) in achados or e in achado_de
                          for e in partes)
    return p, erros


def gravar_protocolo(bruto, linhas, caminho_cfg=None, achados=None):
    lista = ler_protocolos(caminho_cfg)
    p, erros = conferir_protocolo(bruto, linhas,
                                  nomes=ler_nomes(caminho_cfg)["nomes"],
                                  outros=lista, achados=achados)
    if erros:
        return False, {"ok": False, "protocolo": p, "erros": erros}
    nova = [o for o in lista if o["id"] != p["id"]]
    pos = next((i for i, o in enumerate(lista) if o["id"] == p["id"]), len(nova))
    nova.insert(pos, p)
    ok, erro = _gravar_json(ao_lado_do_config(NOME_DOS_PROTOCOLOS, caminho_cfg),
                            {"versao": 1, "protocolos": nova})
    if not ok:
        return False, {"ok": False, "erro": erro, "erros": {}}
    return True, {"ok": True, "protocolo": p, "erros": {}}


def apagar_protocolo(ident, caminho_cfg=None):
    lista = ler_protocolos(caminho_cfg)
    nova = [o for o in lista if o["id"] != ident]
    if len(nova) == len(lista):
        return False, u"protocolo que nao existe"
    return _gravar_json(ao_lado_do_config(NOME_DOS_PROTOCOLOS, caminho_cfg),
                        {"versao": 1, "protocolos": nova})


def linhas_da_tabela(modalidade="CT"):
    try:
        import radai_sets
        f = getattr(radai_sets, "estruturas_para_tabela", None)
    except Exception:
        f = None
    if f is None:
        return [], MOTIVO_SEM_LISTA
    try:
        bruto = f(modalidade_canonica(modalidade) or "CT") or []
    except Exception as e:
        return [], u"%s (%s: %s)" % (MOTIVO_SEM_LISTA, type(e).__name__, e)
    linhas = []
    for l in bruto:
        if not isinstance(l, dict) or not l.get("nome_padrao"):
            continue
        linhas.append({"task": u"%s" % (l.get("task") or u""),
                       "nome_padrao": u"%s" % l["nome_padrao"],
                       "chave_anatomica": u"%s" % (l.get("chave_anatomica") or u""),
                       "no_study": bool(l.get("no_study")),
                       "achado": bool(l.get("achado")),
                       "protocolo": l.get("protocolo") is not False})
    return linhas, u""


def estruturas_por_modalidade():
    saida = {}
    for m in MODALIDADES:
        linhas, _erro = linhas_da_tabela(m)
        saida[m] = linhas
    return saida


ARQUIVO_DOS_NOMES_ANATOMICOS = ("data", "nomes_anatomicos.json")
IDIOMA_BASE = u"pt-BR"
_ANATOMICOS = {}


def nomes_anatomicos():
    if "nomes" not in _ANATOMICOS:
        d = _ler_json(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   *ARQUIVO_DOS_NOMES_ANATOMICOS))
        _ANATOMICOS["nomes"] = (d.get("nomes") if isinstance(d, dict)
                                and isinstance(d.get("nomes"), dict) else {})
    return _ANATOMICOS["nomes"]


def nome_anatomico(chave, idioma=IDIOMA_BASE):
    d = nomes_anatomicos().get(chave) or {}
    return d.get(idioma) or d.get(IDIOMA_BASE) or u""


FORMATO_DA_EXPORTACAO = u"radai-configuracao"
VERSAO_DA_EXPORTACAO = 1
SECOES_DA_EXPORTACAO = ("configuracao", "nomes", "protocolos")
# GUARDA: placa, dispositivo e porta sao desta maquina; GUIA_VISTO e da estacao.
DA_MAQUINA = ("DEVICE", "PORT", "GUIA_VISTO")
CHAVES_DE_PASTA = ("ROOT", "ROOTS", "OUT_DIR", "LOG_DIR", "STATUS_DIR", "PASTA_FAVORITA")
MOTIVO_CAMINHO = u"caminho que não existe nesta máquina: não será gravado"
MOTIVO_ROOT = (u"a pasta que o vigia varre precisa existir aqui, com leitura e "
               u"escrita: não será gravada")
MOTIVO_TPS = u"valor que esta versão não aceita: não será gravado"
MOTIVO_QUEBRA = u"valor com quebra de linha: não será gravado"
MOTIVO_NAO_E_EXPORTACAO = u"este arquivo não é uma exportação das configurações"
MOTIVO_EXPORTACAO_NOVA = (u"esta exportação veio de uma versão mais nova do "
                          u"programa")


def exportar(caminho_cfg, chaves, versao=u"", agora=None):
    import datetime as _dt
    _t, valores = ler_arquivo(caminho_cfg)
    conf = {}
    for k in chaves or ():
        if k in DA_MAQUINA or k not in valores:
            continue
        conf[k] = u"%s" % valores[k]
    return {"formato": FORMATO_DA_EXPORTACAO, "versao": VERSAO_DA_EXPORTACAO,
            "gerado_em": (agora or _dt.datetime.now()).strftime(
                "%Y-%m-%d %H:%M"),
            "programa": u"%s" % (versao or u""),
            "secoes": {"configuracao": conf,
                       "nomes": ler_nomes(caminho_cfg),
                       "protocolos": ler_protocolos(caminho_cfg)}}


def _secoes_da_exportacao(dados):
    if (not isinstance(dados, dict)
            or dados.get("formato") != FORMATO_DA_EXPORTACAO):
        return None, MOTIVO_NAO_E_EXPORTACAO
    try:
        versao = int(dados.get("versao") or 0)
    except Exception:
        versao = 0
    if versao > VERSAO_DA_EXPORTACAO:
        return None, MOTIVO_EXPORTACAO_NOVA
    secoes = dados.get("secoes")
    return (secoes if isinstance(secoes, dict) else {}), u""


def _aviso_da_chave(chave, valor, validar=None):
    if u"\n" in valor or u"\r" in valor:
        return MOTIVO_QUEBRA
    if chave == "TPS_DESTINO" and valor.strip() and not tps_canonico(valor):
        return MOTIVO_TPS
    if chave == "ROOTS":
        try:
            raizes = json.loads(valor or "[]")
        except (TypeError, ValueError):
            return MOTIVO_ROOT
        if (not isinstance(raizes, list) or len(valor) > 65536
                or any(not isinstance(v, str) or not v.strip() for v in raizes)):
            return MOTIVO_ROOT
        for raiz in raizes:
            laudo = (validar or validar_pasta)(raiz)
            if not all(laudo.get(k) for k in ("existe", "leitura", "escrita")):
                return MOTIVO_ROOT
        return u""
    limpo = valor.split(u"#")[0].strip().strip(u'"')
    if chave in CHAVES_DE_PASTA and limpo:
        if chave == "ROOT":
            laudo = (validar or validar_pasta)(limpo)
            if not (laudo.get("existe") and laudo.get("leitura")
                    and laudo.get("escrita")):
                return MOTIVO_ROOT
        elif not os.path.isdir(limpo):
            return MOTIVO_CAMINHO
    return u""


def previa_da_importacao(dados, caminho_cfg, chaves, estruturas, validar=None,
                         achados=None):
    secoes, erro = _secoes_da_exportacao(dados)
    if erro:
        return {"ok": False, "erro": erro}
    _t, atuais = ler_arquivo(caminho_cfg)
    conf = secoes.get("configuracao")
    conf = conf if isinstance(conf, dict) else {}
    itens, ignoradas = [], []
    for k in sorted(conf):
        v = conf[k]
        if k not in (chaves or ()) or k in DA_MAQUINA or not isinstance(
                v, (str, int, float)):
            ignoradas.append(u"%s" % k)
            continue
        v = u"%s" % v
        atual = atuais.get(k, u"")
        itens.append({"chave": k, "atual": atual, "novo": v,
                      "muda": v.strip() != (atual or u"").strip(),
                      "aviso": _aviso_da_chave(k, v, validar)})
    bruto_n = secoes.get("nomes") if isinstance(secoes.get("nomes"), dict) else {}
    modo = bruto_n.get("modo") if bruto_n.get("modo") in MODOS_DOS_NOMES else u"padrao"
    nomes = _limpar_nomes(bruto_n.get("nomes"))
    lista_p = secoes.get("protocolos")
    lista_p = lista_p if isinstance(lista_p, list) else []
    validos, recusados = [], []
    for bruto in lista_p:
        q = _limpar_protocolo(bruto) or {}
        mod = q.get("modalidade") or u""
        p, erros = conferir_protocolo(bruto, (estruturas or {}).get(mod) or [],
                                      nomes=nomes, outros=validos,
                                      achados=achados)
        if erros:
            recusados.append({"nome": p.get("nome") or u"", "erros": erros})
        else:
            validos.append(p)
    erros_n = conferir_nomes(nomes, estruturas, validos)
    return {"ok": True,
            "configuracao": {"itens": itens, "ignoradas": ignoradas},
            "nomes": {"modo": modo, "total": len(nomes),
                      "cores": {k: v for k, v in _limpar_cores(bruto_n.get("cores")).items()
                                if any(k in _padroes_da_lista(ls) for ls in (estruturas or {}).values())},
                      "recusados": erros_n,
                      "validos": dict((k, v) for k, v in nomes.items()
                                      if k not in erros_n)},
            "protocolos": {"validos": validos, "recusados": recusados}}


def importar(dados, secoes, caminho_cfg, chaves, estruturas, modelo=u"",
             validar=None, achados=None):
    previa = previa_da_importacao(dados, caminho_cfg, chaves, estruturas,
                                  validar=validar, achados=achados)
    if not previa.get("ok"):
        return previa
    marcadas = set(s for s in (secoes or ()) if s in SECOES_DA_EXPORTACAO)
    feito = {"ok": True, "gravado": {}, "erro": u""}
    if "configuracao" in marcadas:
        mud = dict((i["chave"], i["novo"].strip())
                   for i in previa["configuracao"]["itens"]
                   if i["muda"] and not i["aviso"])
        if mud:
            ok, erro = escrever(caminho_cfg, mud, modelo=modelo)
            if not ok:
                return {"ok": False, "erro": erro}
        feito["gravado"]["configuracao"] = sorted(mud)
    if "protocolos" in marcadas:
        validos = previa["protocolos"]["validos"]
        ok, erro = _gravar_json(
            ao_lado_do_config(NOME_DOS_PROTOCOLOS, caminho_cfg),
            {"versao": 1, "protocolos": validos})
        if not ok:
            return {"ok": False, "erro": erro}
        feito["gravado"]["protocolos"] = len(validos)
    if "nomes" in marcadas:
        validos = previa["nomes"]["validos"]
        if "protocolos" not in marcadas:
            erros = conferir_nomes(validos, estruturas,
                                   ler_protocolos(caminho_cfg))
            previa["nomes"]["recusados"].update(erros)
            validos = dict((k, v) for k, v in validos.items() if k not in erros)
        ok, erro = _gravar_json(ao_lado_do_config(NOME_DOS_NOMES, caminho_cfg),
                                {"versao": 1, "modo": previa["nomes"]["modo"],
                                 "nomes": validos, "cores": previa["nomes"].get("cores", {})})
        if not ok:
            return {"ok": False, "erro": erro}
        feito["gravado"]["nomes"] = len(validos)
    feito["previa"] = previa
    return feito
