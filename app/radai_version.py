# -*- coding: utf-8 -*-
import io
import json
import os
import threading

_AQUI = os.path.dirname(os.path.abspath(__file__))


def _entrega_txt():
    d = _AQUI
    for _ in range(4):
        p = os.path.join(d, "entrega.txt")
        if os.path.isfile(p):
            try:
                for linha in io.open(p, encoding="utf-8-sig",
                                     errors="replace"):
                    linha = linha.strip()
                    if linha.upper().startswith("VERSAO="):
                        return linha.split("=", 1)[1].strip()
            except Exception:
                return ""
        pai = os.path.dirname(d)
        if pai == d:
            break
        d = pai
    return ""


def _projeto_txt():
    d = _AQUI
    for _ in range(4):
        p = os.path.join(d, "entrega.txt")
        if os.path.isfile(p):
            try:
                for linha in io.open(p, encoding="utf-8-sig",
                                     errors="replace"):
                    linha = linha.strip()
                    if linha.upper().startswith("PROJETO="):
                        return linha.split("=", 1)[1].strip()
            except Exception:
                return ""
        pai = os.path.dirname(d)
        if pai == d:
            break
        d = pai
    return "AUTO_CONTORNO"


NOME_DO_REGISTRO = "_instalados.json"
TETO_DA_SUBIDA = 4


def pasta_do_programa():
    d = _AQUI
    for _ in range(TETO_DA_SUBIDA):
        if os.path.isfile(os.path.join(d, "entrega.txt")):
            return d
        pai = os.path.dirname(d)
        if pai == d:
            break
        d = pai
    return ""


def registro_da_instalacao(pasta=None):
    # GUARDA: regra unica, a mesma do INSTALL.ps1, do UPDATE.ps1 e do
    # UNINSTALL.ps1: o registro mora no PAI da pasta do programa, nunca dentro.
    raiz = (os.environ.get("RADAI_RAIZ_INSTALACAO") or "").strip().strip('"')
    if raiz:
        return os.path.join(raiz, NOME_DO_REGISTRO)
    pasta = pasta or pasta_do_programa()
    if pasta:
        return os.path.join(os.path.dirname(os.path.abspath(pasta)),
                            NOME_DO_REGISTRO)
    drive = os.environ.get("SystemDrive") or "C:"
    return os.path.join(drive + os.sep, "RADIOTERAPIA_AI", NOME_DO_REGISTRO)


def _mesma_pasta(a, b):
    try:
        return (os.path.normcase(os.path.abspath(str(a)).rstrip("\\/")) ==
                os.path.normcase(os.path.abspath(str(b)).rstrip("\\/")))
    except Exception:
        return False


def _instalados():
    p = registro_da_instalacao()
    if not os.path.isfile(p):
        return {}, p
    try:
        return json.loads(io.open(p, encoding="utf-8-sig").read()), p
    except Exception:
        return {}, p


JANELA_DIAS = 45


def idade(hoje=None):
    import datetime
    r = {"data": u"", "dias": None, "janela_dias": JANELA_DIAS,
         "estado": "sem_carimbo", "frase": u""}
    try:
        import radai_delivery
        data = str(radai_delivery.carimbo(recarregar=True).get("data") or "")
    except Exception:
        data = u""
    try:
        if not data:
            r["frase"] = (u"este build nao diz de quando e — provavelmente e "
                          u"anterior ao carimbo, e vale conferir se ha versao "
                          u"mais nova")
            return r
        r["data"] = data
        d = datetime.datetime.strptime(data[:10], "%Y-%m-%d").date()
        agora = hoje or datetime.date.today()
        dias = (agora - d).days
        r["dias"] = dias
        if dias < 0:
            r["estado"] = "relogio_suspeito"
            r["frase"] = (u"o build diz %s, que esta no futuro — o relogio "
                          u"desta maquina pode estar errado" % data)
        elif dias >= JANELA_DIAS:
            r["estado"] = "vencido"
            r["frase"] = (u"este build tem %d dias — vale conferir se ha "
                          u"versao mais nova" % dias)
        elif dias >= int(JANELA_DIAS * 0.7):
            r["estado"] = "perto"
            r["frase"] = u"este build tem %d dias" % dias
        else:
            r["estado"] = "novo"
            r["frase"] = u"publicado em %s" % data
    except Exception:
        pass
    return r



TIMEOUT_S = 8.0

URL_VERSOES = u"https://github.com/drhenriquebraga/local-suite/releases"

VARIAVEL_URL_VERSOES = "RADAI_URL_VERSOES"
_DESLIGADA = ("0", "off", "desligado", "desligada", "nao", "no", "false")


def url_em_vigor():
    amb = os.environ.get(VARIAVEL_URL_VERSOES)
    if amb is not None:
        amb = amb.strip()
        if amb.lower() in _DESLIGADA:
            return u""
        if amb:
            return amb
    return URL_VERSOES


def _url(url_pagina):
    return url_em_vigor() if url_pagina is None else url_pagina

USER_AGENT = "radioterapia-ai-local-suite"

DIAS_SEM_VERIFICAR = 21

FRASE_DO_404 = (u"consulta indisponivel (o endereco das versoes respondeu "
                u"404: endereco errado ou release que nao existe)")

_CONSULTA = {"estado": "nunca", "versao": u"", "quando": None,
             "erro": u"", "url": u""}
_TRAVA_CONSULTA = threading.Lock()
_THREAD_CONSULTA = None


def _api_de(url_pagina):
    import re
    u = str(url_pagina or "").strip()
    if not u.lower().startswith(("http://", "https://")):
        return u""
    m = re.search(r"github\.com/([^/]+)/([^/]+)", u)
    if m:
        dono, repo = m.group(1), m.group(2).replace(u".git", u"")
        return (u"https://api.github.com/repos/%s/%s/releases/latest"
                % (dono, repo))
    return u


SUFIXO_DO_INSTALADOR = u"_SETUP_LATEST.zip"


def _campo_da_entrega(chave):
    d = _AQUI
    for _ in range(4):
        p = os.path.join(d, "entrega.txt")
        if os.path.isfile(p):
            try:
                for linha in io.open(p, encoding="utf-8-sig",
                                     errors="replace"):
                    linha = linha.strip()
                    if linha.upper().startswith(chave.upper() + "="):
                        return linha.split("=", 1)[1].strip()
            except Exception:
                return u""
            return u""
        pai = os.path.dirname(d)
        if pai == d:
            break
        d = pai
    return u""


def nome_do_instalador_latest():
    produto = _campo_da_entrega("PRODUTO") or _campo_da_entrega("PROJETO")
    return (produto + SUFIXO_DO_INSTALADOR) if produto else u""


def link_do_instalador(url_pagina=None, nome=None):
    import re
    u = str(URL_VERSOES if url_pagina is None else url_pagina or "").strip()
    m = re.search(r"https?://github\.com/([^/]+)/([^/?#]+)", u)
    nome = nome if nome is not None else nome_do_instalador_latest()
    if not m or not nome:
        return u""
    dono, repo = m.group(1), m.group(2).replace(u".git", u"")
    return (u"https://github.com/%s/%s/releases/latest/download/%s"
            % (dono, repo, nome))


def consultar(url_pagina=None, timeout=None, forcar=False):
    import json
    import urllib.error
    import urllib.request

    url_pagina = _url(url_pagina)
    fora = {"estado": "erro", "versao": u"", "erro": u"", "url": url_pagina}
    api = _api_de(url_pagina)
    if not api:
        fora["estado"] = "sem_endereco"
        fora["erro"] = (u"sem endereco das versoes (%s=0 no ambiente "
                        u"desliga a consulta)" % VARIAVEL_URL_VERSOES
                        if not str(url_pagina or u"").strip() else
                        u"endereco das versoes fora do formato do GitHub")
        return fora

    if forcar:
        import time
        api += ("&" if "?" in api else "?") + "consulta=" + str(time.time_ns())
    aqui = u""
    try:
        import radai_delivery
        aqui = str((radai_delivery.carimbo() or {}).get("versao") or "")
    except Exception:
        pass

    try:
        req = urllib.request.Request(
            api, headers={"User-Agent": USER_AGENT,
                          "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(
                req, timeout=float(timeout or TIMEOUT_S)) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        tag = str(d.get("tag_name") or "").lstrip("vV")
        if not tag:
            fora["erro"] = u"a resposta nao trouxe tag_name"
            return fora
        fora["versao"] = tag
        fora["instalador"] = instalador_da_release(d)
        if not aqui:
            fora["estado"] = "erro"
            fora["erro"] = (u"achei a versao publicada (%s), mas nao sei a "
                            u"desta instalacao" % tag)
        else:
            fora["estado"] = "nova" if _maior(tag, aqui) else "atual"
        return fora
    except urllib.error.HTTPError as e:
        if e.code == 404:
            fora["estado"] = "nao_achada"
            fora["erro"] = (
                u"o endereco das versoes respondeu 404: ou ele esta errado, "
                u"ou nao existe release publicada nele. Confira o endereco "
                u"das versoes (RADAI_URL_VERSOES).")
        else:
            fora["erro"] = u"HTTP %s" % e.code
        return fora
    except Exception as e:
        fora["erro"] = u"%s: %s" % (type(e).__name__, str(e)[:120])
        return fora


def instalador_da_release(d, nome=None):
    nome = nome_do_instalador_latest() if nome is None else nome
    if not nome or not isinstance(d, dict):
        return {}
    for a in d.get("assets") or []:
        if not isinstance(a, dict) or str(a.get("name") or "") != nome:
            continue
        dig = str(a.get("digest") or "").strip()
        sha = (dig.split(":", 1)[1].strip().lower()
               if dig.lower().startswith("sha256:") else u"")
        try:
            tam = int(a.get("size") or 0)
        except (TypeError, ValueError):
            tam = 0
        return {"nome": nome, "url": str(a.get("browser_download_url") or ""),
                "tamanho": tam, "sha256": sha}
    return {}


TETO_DO_INSTALADOR_BYTES = 256 * 1024 * 1024
TETO_DO_DOWNLOAD_S = 900.0


def _endereco_local(url):
    resto = str(url or "").split("://", 1)[-1]
    lugar = resto.split("/", 1)[0].rsplit("@", 1)[-1]
    return lugar.split(":", 1)[0].lower() in ("127.0.0.1", "localhost")


def baixar_instalador(inst, pasta, timeout=None, progresso=None,
                      relogio=None):
    import hashlib
    import re
    import time
    import urllib.request
    relogio = relogio or time.monotonic
    r = {"ok": False, "motivo": u"", "arquivo": u"", "bytes": 0,
         "segundos": 0.0}
    inst = inst if isinstance(inst, dict) else {}
    url = str(inst.get("url") or "").strip()
    sha = str(inst.get("sha256") or "").strip().lower()
    nome = str(inst.get("nome") or "").strip()
    try:
        tam = int(inst.get("tamanho") or 0)
    except (TypeError, ValueError):
        tam = 0
    if not url or not nome:
        r["motivo"] = u"a release não diz de onde baixar o instalador"
        return r
    # GUARDA: sem a soma publicada pela release nada do que se baixa e
    # executado; ela prova identidade com o publicado, nao autenticidade.
    if not re.match(r"^[0-9a-f]{64}$", sha):
        r["motivo"] = (u"a release não publica a soma SHA-256 do instalador, "
                       u"e sem ela nada baixado é executado")
        return r
    if not (url.lower().startswith("https://") or _endereco_local(url)):
        r["motivo"] = u"o endereço do instalador não é https"
        return r
    if tam <= 0 or tam > TETO_DO_INSTALADOR_BYTES:
        r["motivo"] = u"a release diz um tamanho fora do esperado"
        return r
    if os.path.sep in nome or "/" in nome or nome.startswith("."):
        r["motivo"] = u"o nome do instalador na release não é um nome de arquivo"
        return r
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, nome)
    h = hashlib.sha256()
    n = 0
    t0 = relogio()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(
                req, timeout=float(timeout or 30.0)) as resp, \
                io.open(destino, "wb") as f:
            while True:
                bloco = resp.read(256 * 1024)
                if not bloco:
                    break
                n += len(bloco)
                if n > tam:
                    raise ValueError(u"o arquivo passou do tamanho da release")
                if relogio() - t0 > TETO_DO_DOWNLOAD_S:
                    raise ValueError(u"o download passou de %d min"
                                     % int(TETO_DO_DOWNLOAD_S // 60))
                h.update(bloco)
                f.write(bloco)
                if progresso:
                    try:
                        progresso(n, tam)
                    except Exception:
                        pass
    except Exception as e:
        _apagar(destino)
        r["motivo"] = u"o download falhou (%s: %s)" % (type(e).__name__,
                                                       str(e)[:120])
        r["bytes"] = n
        return r
    r["bytes"] = n
    r["segundos"] = max(0.0, relogio() - t0)
    if n != tam:
        _apagar(destino)
        r["motivo"] = (u"o arquivo baixado tem %d bytes, e a release diz %d"
                       % (n, tam))
        return r
    if h.hexdigest().lower() != sha:
        _apagar(destino)
        r["motivo"] = (u"a soma SHA-256 do arquivo baixado (%s…) não bate com "
                       u"a da release (%s…)" % (h.hexdigest()[:12], sha[:12]))
        return r
    r["ok"] = True
    r["arquivo"] = destino
    return r


def _apagar(caminho):
    try:
        if caminho and os.path.isfile(caminho):
            os.remove(caminho)
    except Exception:
        pass


def _maior(a, b):
    def _n(v):
        fora = []
        for pedaco in str(v or "").lstrip("vV").split("."):
            fora.append(int(pedaco) if pedaco.isdigit() else 0)
        return tuple(fora + [0] * (4 - len(fora)))[:4]
    return _n(a) > _n(b)


def iniciar_consulta(url_pagina=None, timeout=None, ao_terminar=None, forcar=False):
    url_pagina = _url(url_pagina)
    import datetime
    import threading
    global _TRAVA_CONSULTA, _THREAD_CONSULTA
    if _TRAVA_CONSULTA is None:
        _TRAVA_CONSULTA = threading.Lock()
    def _rodar():
        try:
            r = consultar(url_pagina, timeout, forcar=True) if forcar else consultar(url_pagina, timeout)
        except Exception as e:
            r = {"estado": "erro", "erro": type(e).__name__}
        with _TRAVA_CONSULTA:
            _CONSULTA.update(r)
            _CONSULTA["quando"] = datetime.datetime.now()
            _CONSULTA["consultando"] = False
        if ao_terminar:
            try:
                ao_terminar(ultima_consulta())
            except Exception:
                pass
    with _TRAVA_CONSULTA:
        anterior = globals().get("_THREAD_CONSULTA")
        if anterior is not None and anterior.is_alive():
            return anterior
        _CONSULTA["consultando"] = True
        t = threading.Thread(target=_rodar, name="radai-versao", daemon=True)
        _THREAD_CONSULTA = t
        t.start()
        return t


def ultima_consulta(hoje=None):
    import datetime
    with (_TRAVA_CONSULTA or _travinha()):
        d = dict(_CONSULTA)
    est, quando = d.get("estado"), d.get("quando")
    if est == "nova":
        d["frase"] = (u"ha uma versao mais nova publicada: %s"
                      % d.get("versao"))
    elif est == "atual":
        d["frase"] = u"conferido agora: esta e a versao mais recente"
    elif est == "nunca":
        d["frase"] = u""
    elif est == "nao_achada":
        d["frase"] = FRASE_DO_404
    else:
        _e = (d.get("erro") or u"sem detalhe")
        _m = _e.split(":")[0].strip()[:60]
        d["frase"] = u"consulta indisponivel (%s)" % _m
    if quando is not None and est not in ("nova", "atual"):
        dias = ((hoje or datetime.datetime.now()) - quando).days
        if dias >= DIAS_SEM_VERIFICAR:
            d["frase"] += u" (ha %d dias sem conseguir)" % dias
    return d


def _travinha():
    import threading
    return threading.Lock()


def linhas_de_consulta(d=None):
    d = d or ultima_consulta()
    if d.get("estado") in ("nunca", "atual"):
        return []
    if not d.get("frase"):
        return []
    return [u"versao: " + d["frase"]]


def para_a_tela():
    fora = {"estado": "nunca", "nova": False, "publicada": u"", "aqui": u"",
            "link": u""}
    try:
        d = ultima_consulta()
        fora["estado"] = str(d.get("estado") or "nunca")
        fora["consultando"] = bool(d.get("consultando"))
        fora["publicada"] = str(d.get("versao") or "")
        try:
            import radai_delivery
            fora["aqui"] = str((radai_delivery.carimbo() or {}).get("versao")
                               or u"")
        except Exception:
            fora["aqui"] = u""
        if fora["estado"] == "nova":
            fora["nova"] = True
            fora["publicada"] = str(d.get("versao") or u"")
            fora["link"] = link_do_instalador(d.get("url") or None) or u""
    except Exception:
        pass
    return fora


def conferir(appver):
    laudo = {"ok": True, "avisos": [], "fontes": {}}
    try:
        codigo = str(appver or "").strip()
        entrega = _entrega_txt()
        projeto = _projeto_txt()
        inst, caminho_inst = _instalados()
        entrada = (inst or {}).get(projeto) or {}
        if not isinstance(entrada, dict):
            entrada = {}
        registrada = str(entrada.get("versao") or "")
        onde = str(entrada.get("caminho") or entrada.get("pasta") or "")
        aqui = pasta_do_programa()

        existe = bool(onde) and os.path.isdir(onde)
        e_esta = (not onde) or (bool(aqui) and _mesma_pasta(onde, aqui))
        dentro = os.path.join(aqui, NOME_DO_REGISTRO) if aqui else ""
        ignorado = (dentro if dentro and os.path.isfile(dentro)
                    and not _mesma_pasta(dentro, caminho_inst) else "")
        laudo["fontes"] = {
            "codigo": codigo, "entrega_txt": entrega,
            "instalada": registrada, "instalada_em": onde,
            "instalada_existe": existe,
            "registro": caminho_inst,
            "registro_existe": os.path.isfile(caminho_inst),
            "registro_ignorado": ignorado,
            "pasta_do_programa": aqui, "projeto": projeto,
        }
        if ignorado:
            laudo["avisos"].append(
                u"há um segundo registro DENTRO da pasta do programa (%s), "
                u"deixado por uma atualização antiga. Ele não é lido: o "
                u"registro desta instalação é %s, e a próxima atualização "
                u"renomeia o de dentro." % (ignorado, caminho_inst))
        if onde and not existe:
            laudo["ok"] = False
            laudo["avisos"].append(
                u"o registro aponta para uma pasta que nao existe mais (%s). "
                u"Ele diz o que foi instalado um dia, e nao o que esta "
                u"instalado agora." % onde)

        if entrega and codigo and entrega != codigo:
            laudo["ok"] = False
            laudo["avisos"].append(
                u"o código diz versão %s e o `entrega.txt` diz %s — alguém "
                u"mexeu no código sem subir a versão, ou subiu a versão sem "
                u"publicar. Não quebra nada hoje; quebra a resposta a \"o que "
                u"exatamente está rodando naquela estação\"."
                % (codigo, entrega))

        if existe and not e_esta:
            laudo["ok"] = False
            laudo["avisos"].append(
                u"o registro %s aponta outra pasta para `%s` (%s, versão %s), "
                u"e o código em execução está em %s. Você provavelmente está "
                u"rodando uma CÓPIA que não é a instalada — foi assim que um "
                u"conserto publicado deixou de chegar à máquina, e a tela do "
                u"erro era idêntica nos dois casos."
                % (caminho_inst, projeto, onde, registrada or u"?",
                   aqui or _AQUI))
        elif (registrada and codigo and registrada != codigo
              and (existe or not onde)):
            laudo["ok"] = False
            laudo["avisos"].append(
                u"o registro %s diz versão %s para esta pasta, e o código em "
                u"execução é %s: o registro ficou para trás. Rode Atualizar "
                u"de novo, que ele o acerta." % (caminho_inst, registrada,
                                                 codigo))

        if not registrada:
            laudo["avisos"].append(
                u"não há registro de instalação para `%s` em %s — este "
                u"processo está rodando fora de uma instalação (do "
                u"repositório, ou de um pacote extraído à mão). Normal em "
                u"desenvolvimento." % (projeto, caminho_inst))
    except Exception as e:
        laudo["avisos"].append(
            u"não consegui conferir as versões (%s)" % type(e).__name__)
    return laudo


def linhas_para_log(laudo):
    f = laudo.get("fontes") or {}
    fora = []
    if laudo.get("avisos"):
        fora.append(u"versao: codigo=%s entrega.txt=%s instalada=%s "
                    u"(registro lido: %s)"
                    % (f.get("codigo") or "?", f.get("entrega_txt") or "-",
                       f.get("instalada") or "-", f.get("registro") or "-"))
        for a in laudo["avisos"]:
            fora.append(u"   " + a)
    return fora
