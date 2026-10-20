# -*- coding: utf-8 -*-
import os
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
