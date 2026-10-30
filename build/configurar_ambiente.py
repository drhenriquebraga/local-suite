# -*- coding: utf-8 -*-
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parent.parent

RAIZES_DE_ENTREGA = ("deploy",)


def raiz_de_entrega():
    try:
        import destino_de_entrega
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import destino_de_entrega
    try:
        projeto = ler_entrega(RAIZ)[0]
    except SystemExit:
        projeto = None
    return destino_de_entrega.raiz_de_entrega(projeto, de=RAIZ)[0]


def ler_entrega(raiz_projeto):
    arq = raiz_projeto / "entrega.txt"
    if not arq.exists():
        raise SystemExit(
            "ERRO: nao achei %s.\n"
            "      Ele declara PROJETO e VERSAO." % arq)
    campos = {}
    with open(str(arq), "r", encoding="utf-8-sig", errors="replace") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            campos[chave.strip().upper()] = valor.strip()
    for obrigatorio in ("PROJETO", "VERSAO"):
        if not campos.get(obrigatorio):
            raise SystemExit(
                "ERRO: %s sem a linha %s=." % (arq, obrigatorio))
    return (campos["PROJETO"], campos["VERSAO"],
            campos.get("PRODUTO") or campos["PROJETO"])


def pasta_de_entrega(destino, projeto, versao):
    if str(destino).strip().lower() == "pendrive":
        raise SystemExit(
            "ERRO: `--destino pendrive` nao existe mais.\n"
            "      A pasta do pendrive foi apagada, e a raiz de entrega\n"
            "      (destino_de_entrega.raiz_de_entrega) e a unica entrega.\n"
            "      O bundle nao e entrega: ele nasce em _montagem\\ aqui,\n"
            "      ou na pasta de trabalho do preparador na maquina do\n"
            "      servico.")
    if str(destino).strip().lower() not in RAIZES_DE_ENTREGA:
        raise SystemExit(
            "ERRO: destino %r nao existe. Use 'deploy'." % destino)
    return raiz_de_entrega() / projeto / ("v" + versao)


PY_VERSAO = "3.10.11"
URL_EMBED = "https://www.python.org/ftp/python/%s/python-%s-embed-amd64.zip" % (PY_VERSAO, PY_VERSAO)
PIP_RODA = "pip-26.2.1-py3-none-any.whl"
URL_PIP = ("https://files.pythonhosted.org/packages/f3/6e/"
           "1736e5b4ae2b778ef2f81c47d797de9f891d4d8acb047a24ca37a60294dd/"
           + PIP_RODA)
def _pastas_do_app():
    sys.path.insert(0, str(RAIZ / "tools"))
    import _componentes
    return [RAIZ / "app", RAIZ] + [Path(p) for p in _componentes.pastas_base("app", str(RAIZ))[1:]]


def _ligar_caminho():
    sys.path.insert(0, str(RAIZ / "tools"))
    import _componentes
    _componentes.ligar_caminho(str(RAIZ))


def _tasks_do_catalogo():
    for cand in _pastas_do_app():
        if (cand / "radai_tasks.py").is_file():
            if str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
            break
    import radai_tasks
    res = getattr(radai_tasks, "RESERVAS", frozenset())
    return tuple(d["task"] for d in radai_tasks.CATALOGO
                 if d["datasets"] and d["task"] not in res)


def _nucleo_do_catalogo():
    todas = _tasks_do_catalogo()
    import radai_tasks
    try:
        for cand in _pastas_do_app():
            if (cand / "engine.py").is_file():
                if str(cand) not in sys.path:
                    sys.path.insert(0, str(cand))
                break
        import engine
        nuc = tuple(t for t in todas if engine.alimenta_o_entregue(t))
        return nuc or todas
    except Exception:
        return todas


def tasks_levadas(bundle):
    import radai_tasks
    pesos_dir = Path(str(bundle)) / "ts_weights"
    no_disco = set()
    if pesos_dir.is_dir():
        for d in os.listdir(str(pesos_dir)):
            m = re.match(r"Dataset(\d+)_", d)
            if m:
                no_disco.add(int(m.group(1)))
    return [t for t in _tasks_do_catalogo()
            if set(radai_tasks.datasets_necessarios(t)) <= no_disco]


def modelos_levados(bundle):
    mdir = Path(str(bundle)) / "modelos"
    if not mdir.is_dir():
        return []
    try:
        import radai_models
        conhecidos = set(radai_models.MODELOS)
    except Exception:
        conhecidos = None
    saida = []
    for d in sorted(os.listdir(str(mdir))):
        p = mdir / d
        if not p.is_dir() or not os.listdir(str(p)):
            continue
        saida.append(d if (conhecidos is None or d in conhecidos)
                     else d + "(?)")
    return saida


def escrever_recibo_medido(bundle):
    levadas = tasks_levadas(bundle)
    achados = modelos_levados(bundle)
    sel = Path(str(bundle)) / "plugins.txt"
    if not sel.is_file():
        return levadas, achados

    atual = sel.read_text(encoding="utf-8")
    if "LEVADO=" not in atual:
        atual = (atual.rstrip("\n")
                 + "\n\n# MEDIDO no `ts_weights` do pacote, no momento de\n"
                   "# empacotar -- e nao a lista do que foi PEDIDO acima.\n"
                   "# A pasta acumula entre preparos, entao as duas podem\n"
                   "# diferir, e a diferenca e o que o suporte precisa.\n"
                 + "LEVADO=%s\n" % ",".join(levadas))
    if "MODELOS_LEVADOS=" not in atual:
        atual = (atual.rstrip("\n")
                 + "\n\n# MEDIDO em `modelos\\`, pelo mesmo motivo do\n"
                   "# `LEVADO` acima: a pasta acumula, e `MODELOS=` so\n"
                   "# pode dizer o que foi PEDIDO. `(?)` marca pasta que\n"
                   "# o registro de `radai_models` nao conhece -- ela\n"
                   "# esta no pacote mesmo assim.\n"
                 + "MODELOS_LEVADOS=%s\n" % ",".join(achados))
    sel.write_text(atual, encoding="utf-8")
    return levadas, achados


NUCLEO = _nucleo_do_catalogo()
TASKS = _tasks_do_catalogo()

IMPORTS_OBRIGATORIOS = ["torch", "pkg_resources", "totalsegmentator.config", "pydicom",
                        "fastapi", "uvicorn", "rt_utils", "SimpleITK", "nibabel",
                        "scipy", "numpy", "nnunetv2", "monai",
                        "openjpeg"]

LOG = None


def log(msg=""):
    linha = "%s %s" % (datetime.now().strftime("%H:%M:%S"), msg) if msg else ""
    print(linha, flush=True)
    if LOG:
        try:
            LOG.write(linha + "\n")
            LOG.flush()
        except Exception:
            pass


def para_o_log(caminho, ctx):
    base = (ctx or {}).get("preparo")
    if not base:
        return str(caminho)
    try:
        rel = Path(str(caminho)).resolve().relative_to(Path(str(base)).resolve())
        return u"<pasta de trabalho>%s%s" % (os.sep, rel)
    except Exception:
        return Path(str(caminho)).name


def titulo(t):
    log()
    log("=" * 70)
    log(" " + t)
    log("=" * 70)


def mb(n):
    return "%.1f MB" % (n / 1048576.0)


def gb(n):
    return "%.2f GB" % (n / 1073741824.0)



SINAIS_DE_REDE = (
    "unexpected_eof_while_reading",
    "getaddrinfo failed",
    "name or service not known",
    "temporary failure in name resolution",
    "network is unreachable",
    "no route to host",
    "connection reset",
    "connection refused",
    "connection aborted",
    "forcibly closed",
    "timed out",
    "timeout",
    "ssleoferror",
    "winerror 10054",
    "winerror 10060",
    "winerror 10061",
    "winerror 11001",
    "winerror 10051",
    "contenttooshorterror",
    "retrieval incomplete",
)


class SemRede(RuntimeError):
    cabecalho = "SEM CONEXAO nesta etapa"
    codigo = 2


def falha_de_rede(exc):
    vistos = 0
    while exc is not None and vistos < 6:
        t = ("%s %s" % (type(exc).__name__, exc)).lower()
        if any(s in t for s in SINAIS_DE_REDE):
            return True
        exc = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
        vistos += 1
    return False


SINAIS_DE_CERTIFICADO = (
    "certificate_verify_failed",
    "certificate verify failed",
    "unable to get local issuer certificate",
    "unable to get issuer certificate",
    "self signed certificate in certificate chain",
    "self-signed certificate in certificate chain",
)
SINAIS_DE_RELOGIO = (
    "certificate has expired",
    "certificate is not yet valid",
)
SINAIS_DE_CORTE_TLS = (
    "unexpected_eof_while_reading",
    "eof occurred in violation of protocol",
    "ssleoferror",
)


def _texto_da_cadeia(exc):
    partes, vistos = [], 0
    while exc is not None and vistos < 6:
        partes.append(("%s %s" % (type(exc).__name__, exc)).lower())
        exc = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
        vistos += 1
    return u" | ".join(partes)


def falha_de_certificado(exc):
    t = exc.lower() if isinstance(exc, str) else _texto_da_cadeia(exc)
    if any(s in t for s in SINAIS_DE_RELOGIO):
        return "relogio"
    if any(s in t for s in SINAIS_DE_CERTIFICADO):
        return "inspecao"
    return None


def corte_no_aperto_de_mao(exc):
    t = exc.lower() if isinstance(exc, str) else _texto_da_cadeia(exc)
    return any(s in t for s in SINAIS_DE_CORTE_TLS)


class InspecaoHTTPS(SemRede):
    cabecalho = "A REDE DESTA MAQUINA INSPECIONA HTTPS"
    codigo = 3


class RelogioErrado(SemRede):
    cabecalho = "CERTIFICADO FORA DA VALIDADE: CONFIRA A DATA E A HORA"
    codigo = 4


CODIGOS_DO_SERVIDOR_FORA = (408, 429)


def erro_do_servidor(exc):
    import urllib.error as _ue
    vistos = 0
    while exc is not None and vistos < 6:
        if isinstance(exc, _ue.HTTPError):
            cod = getattr(exc, "code", None)
            if isinstance(cod, int) and (500 <= cod < 600
                                         or cod in CODIGOS_DO_SERVIDOR_FORA):
                return cod
        exc = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
        vistos += 1
    return None


class ServidorFora(SemRede):
    cabecalho = "O SERVIDOR DE ORIGEM RESPONDEU ERRO"
    codigo = 5


class DivergeDaOrigem(RuntimeError):
    pass


def _host(url):
    try:
        from urllib.parse import urlparse
        return urlparse(str(url)).hostname or str(url)
    except Exception:
        return str(url)


_O_QUE_FAZER_REDE = (
    "     O que fazer:\n"
    "       1. confira se o navegador DESTA maquina abre https://github.com;\n"
    "       2. se abre, peca ao TI que instale no Windows o certificado raiz do\n"
    "          proxy (Autoridades de Certificacao Raiz Confiaveis), ou que\n"
    "          libere github.com e release-assets.githubusercontent.com sem\n"
    "          inspecao para programas;\n"
    "       3. ou monte o pacote em outra rede (em casa, por exemplo) e traga-o\n"
    "          no pendrive: modo 3, \"Instalar de um arquivo que eu trouxe\".\n"
    "     Isto NAO e defeito do pacote nem do arquivo. O que ja foi baixado\n"
    "     fica, e nao sera refeito.")


def texto_da_inspecao(url, tipo, detalhe, recuo=u""):
    host = _host(url)
    if tipo == "relogio":
        cabeca = ("o certificado de %s parece VENCIDO ou AINDA NAO VALIDO.\n"
                  "     Antes de tudo, confira a DATA e a HORA do Windows desta\n"
                  "     maquina: com o relogio errado, todo certificado do mundo\n"
                  "     e recusado. Se o relogio estiver certo, a rede desta\n"
                  "     maquina inspeciona HTTPS com um certificado vencido.\n"
                  % host)
    else:
        cabeca = ("a rede desta maquina inspeciona HTTPS: ao abrir %s, o\n"
                  "     certificado apresentado nao foi reconhecido por este\n"
                  "     programa (CERTIFICATE_VERIFY_FAILED). E o que acontece\n"
                  "     quando um proxy ou firewall da instituicao abre a conexao\n"
                  "     e a assina com um certificado proprio -- o navegador\n"
                  "     confia nele, e o programa nao.\n" % host)
    return (cabeca + ("     %s\n" % recuo if recuo else "") + _O_QUE_FAZER_REDE
            + "\n     (detalhe tecnico: %s)" % str(detalhe)[:200])


def texto_do_servidor(url, tentativas, codigo, detalhe):
    return ("o servidor de %s respondeu HTTP %d %d vezes, com pausa entre\n"
            "     elas. E o servidor de origem que esta fora do ar ou\n"
            "     sobrecarregado: a rede desta maquina funciona (ela falou com\n"
            "     ele), e nao ha defeito no pacote nem no arquivo.\n"
            "     O que fazer: espere alguns minutos e mande preparar de novo.\n"
            "     O que ja foi baixado fica, e nao sera refeito. Se persistir\n"
            "     por horas, o problema continua sendo da origem, e nao desta\n"
            "     maquina.\n"
            "     (detalhe tecnico: %s)"
            % (_host(url), codigo, tentativas, str(detalhe)[:160]))


def texto_do_corte(url, tentativas, detalhe):
    return ("nao consegui alcancar %s: a conexao foi cortada no meio do\n"
            "     aperto de mao TLS (UNEXPECTED_EOF), %d vezes, com pausa entre\n"
            "     elas. Isso acontece de dois jeitos: SEM INTERNET, ou quando a\n"
            "     rede desta maquina inspeciona HTTPS e derruba a conexao de\n"
            "     programas (o navegador passa e o programa nao).\n"
            % (_host(url), tentativas)
            + _O_QUE_FAZER_REDE
            + "\n     (detalhe tecnico: %s)" % str(detalhe)[:160])


PRAZO_SEM_DADO_S = 120

_SCRIPT_TRUSTSTORE = (
    "import sys, time, socket, urllib.request\n"
    "socket.setdefaulttimeout(" + str(PRAZO_SEM_DADO_S) + ")\n"
    "try:\n"
    "    from pip._vendor import truststore\n"
    "except Exception as e:\n"
    "    print('SEM_TRUSTSTORE %s: %s' % (type(e).__name__, e), flush=True)\n"
    "    sys.exit(3)\n"
    "truststore.inject_into_ssl()\n"
    "u = [0.0]\n"
    "def p(b, t, total):\n"
    "    if total > 0 and time.time() - u[0] > 5:\n"
    "        u[0] = time.time()\n"
    "        print('    %5.1f%%' % min(100.0, 100.0 * b * t / total), flush=True)\n"
    "urllib.request.urlretrieve(sys.argv[1], sys.argv[2], reporthook=p)\n"
    "print('TRUSTSTORE_OK', flush=True)\n"
)


def baixar_pelo_truststore(py, url, destino, timeout=7200):
    if not py or not os.path.isfile(str(py)):
        return False, (u"o recuo pelo truststore precisa do Python do pacote, "
                       u"que ainda nao existe nesta etapa")
    try:
        proc = subprocess.Popen(
            [str(py), "-c", _SCRIPT_TRUSTSTORE, str(url), str(destino)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1,
            env=dict(os.environ, PYTHONIOENCODING="utf-8:replace",
                     PYTHONUNBUFFERED="1"))
    except Exception as e:
        return False, u"nao consegui abrir o recuo (%s: %s)" % (
            type(e).__name__, e)
    ultimas = []

    def _ler():
        try:
            for linha in proc.stdout:
                linha = linha.rstrip()
                if not linha:
                    continue
                ultimas.append(linha)
                del ultimas[:-12]
                if linha.lstrip().endswith("%"):
                    log("  (truststore) " + linha.strip())
        except Exception:
            pass
    import threading
    leitor = threading.Thread(target=_ler, daemon=True)
    leitor.start()
    try:
        proc.wait(timeout=timeout)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        leitor.join(5)
        try:
            os.remove(str(destino))
        except OSError:
            pass
        _progresso = [l.strip() for l in list(ultimas)
                      if l.strip().endswith("%")]
        if _progresso:
            return False, (u"o recuo pelo truststore baixou so ate %s e passou "
                           u"do prazo total (%d s) — a rede esta lenta demais "
                           u"para este arquivo"
                           % (_progresso[-1], int(timeout)))
        return False, (u"o recuo pelo truststore passou do tempo (%d s) — "
                       u"a conexao ficou aberta sem trazer nada"
                       % int(timeout))
    leitor.join(10)
    texto = u" | ".join(ultimas)
    if proc.returncode == 0 and "TRUSTSTORE_OK" in texto:
        return True, texto
    try:
        os.remove(str(destino))
    except OSError:
        pass
    return False, texto


def baixar(url, destino, minimo_bytes=0, chave=None, py_recuo=None):
    destino = Path(destino)

    def _conferir(rotulo):
        if not chave:
            return
        try:
            import artefatos
        except ImportError:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import artefatos
        ok, msg = artefatos.conferir(str(destino), chave)
        if not ok:
            try:
                destino.unlink()
            except OSError:
                pass
            raise RuntimeError("CONFERENCIA FALHOU (%s)\n     %s"
                               % (rotulo, msg))
        log("  conferido: SHA-256 bate")

    if destino.exists() and destino.stat().st_size > minimo_bytes:
        log("  ja baixado: %s (%s)" % (destino.name, mb(destino.stat().st_size)))
        _conferir("cache")
        return destino
    log("  baixando %s" % url)
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    t0 = time.time()
    _transferir(url, parcial, _relogio_de_progresso(), py_recuo)
    os.replace(str(parcial), str(destino))
    tam = destino.stat().st_size
    log("  ok: %s em %ds" % (mb(tam), int(time.time() - t0)))
    if tam < minimo_bytes:
        raise RuntimeError("download incompleto: %s tem %s, esperado > %s"
                           % (destino.name, mb(tam), mb(minimo_bytes)))
    _conferir("download")
    return destino


def _relogio_de_progresso():
    ultimo = [0]

    def progresso(blocos, tam_bloco, total):
        baixado = blocos * tam_bloco
        if total > 0 and time.time() - ultimo[0] > 3:
            ultimo[0] = time.time()
            log("    %5.1f%%  %s de %s" % (100.0 * min(baixado, total) / total,
                                        mb(min(baixado, total)), mb(total)))
    return progresso


def _transferir(url, parcial, progresso, py_recuo=None):
    parcial = Path(str(parcial))
    _ESPERAS = (2, 6)
    _ultimo = None
    for _tent in range(len(_ESPERAS) + 1):
        try:
            urllib.request.urlretrieve(url, str(parcial),
                                       reporthook=progresso)
            _ultimo = None
            break
        except Exception as e:
            _ultimo = e
            try:
                parcial.unlink()
            except OSError:
                pass
            if falha_de_certificado(e):
                break
            _cod = erro_do_servidor(e)
            if not (falha_de_rede(e) or _cod) or _tent >= len(_ESPERAS):
                break
            if _cod:
                log("    o servidor respondeu HTTP %d; tento de novo em %ds "
                    "(%d de %d)" % (_cod, _ESPERAS[_tent], _tent + 1,
                                    len(_ESPERAS)))
            else:
                log("    a conexao falhou; tento de novo em %ds (%d de %d)"
                    % (_ESPERAS[_tent], _tent + 1, len(_ESPERAS)))
            time.sleep(_ESPERAS[_tent])
    if _ultimo is None:
        return
    e = _ultimo
    tipo = falha_de_certificado(e)
    if tipo:
        log("    o certificado de %s foi RECUSADO pelo repositorio do "
            "Windows (%s)" % (_host(url), str(e)[:120]))
        if py_recuo and tipo == "inspecao":
            log("    tento de novo pelo truststore (o caminho de certificados "
                "do navegador), so neste download")
            ok, texto = baixar_pelo_truststore(py_recuo, url, parcial)
            if ok:
                log("    ok pelo truststore: a cadeia foi completada pelo "
                    "Windows")
                return
            recuo = (u"Tentei tambem pelo truststore (o caminho do navegador), "
                     u"e ele nao resolveu: %s" % texto[-160:])
        elif tipo == "inspecao":
            recuo = (u"O recuo pelo truststore so existe depois da etapa 2 "
                     u"(ele vem dentro do pip do pacote).")
        else:
            recuo = u""
        if tipo == "relogio":
            raise RelogioErrado(texto_da_inspecao(url, tipo, e, recuo))
        raise InspecaoHTTPS(texto_da_inspecao(url, tipo, e, recuo))
    _cod = erro_do_servidor(e)
    if _cod:
        raise ServidorFora(texto_do_servidor(url, len(_ESPERAS) + 1, _cod, e))
    if falha_de_rede(e):
        if corte_no_aperto_de_mao(e):
            raise SemRede(texto_do_corte(url, len(_ESPERAS) + 1, e))
        raise SemRede(
            "nao consegui alcancar %s.\n"
            "     Tentei %d vezes, com pausa entre elas.\n"
            "     Isto NAO e defeito do pacote nem do arquivo: e a "
            "conexao.\n"
            "     Ligue a internet (ou libere o proxy) e mande preparar "
            "de novo.\n"
            "     O que ja foi baixado fica, e nao sera refeito.\n"
            "     (detalhe tecnico: %s)"
            % (url, len(_ESPERAS) + 1, str(e)[:160]))
    raise e


_BLOCOS = dict.fromkeys(range(0x2580, 0x25A0), u"#")


def _sem_bloco(linha):
    return linha.translate(_BLOCOS)


def rodar(cmd, titulo_curto, cwd=None, env=None, timeout=None):
    log("  $ %s" % " ".join(str(c) for c in cmd[:6]) + (" ..." if len(cmd) > 6 else ""))
    t0 = time.time()
    proc = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    ultimas = []
    fonte = [None]
    def _e_barra(s):
        return "%|" in s
    barra_pendente = [None]

    def _para_o_arquivo(s):
        if LOG:
            LOG.write("      " + s + "\n")

    for linha in proc.stdout:
        linha = _sem_bloco(linha.rstrip())
        if not linha:
            continue
        m = re.search(r"Using cached (\S+\.tar\.gz)", linha) or \
            re.search(r"Downloading (\S+\.tar\.gz)", linha)
        if m:
            fonte[0] = m.group(1)
        if _e_barra(linha):
            barra_pendente[0] = linha
            print("%s       %s" % (datetime.now().strftime("%H:%M:%S"),
                                   linha[:150]), flush=True)
            continue
        if barra_pendente[0] is not None:
            _para_o_arquivo(barra_pendente[0])
            barra_pendente[0] = None
        ultimas = (ultimas + [linha])[-40:]
        _para_o_arquivo(linha)
        if any(p in linha for p in ("ERROR", "error:", "Downloading", "Installing collected",
                                    "Successfully", "WARNING: ", "Traceback")):
            log("      " + linha[:150])
    if barra_pendente[0] is not None:
        _para_o_arquivo(barra_pendente[0])
    proc.wait(timeout=timeout)
    if proc.returncode:
        log("  FALHOU (%s) — ultimas linhas:" % proc.returncode)
        for l in ultimas[-15:]:
            log("      " + l[:150])
        if fonte[0]:
            log("  DIAGNOSTICO: `%s` -- o pip nao achou RODA para o Python "
                "%s e caiu para o codigo-fonte." % (fonte[0], PY_VERSAO))
            log("  O runtime embeddable nao tem compilador nem backend de "
                "build: compilar nao e' uma opcao aqui.")
            log("  Pine no build/requirements-demo.txt uma versao desse "
                "pacote que publique roda cp310-win_amd64.")
        raise RuntimeError("%s falhou com codigo %s" % (titulo_curto, proc.returncode))
    log("  ok em %ds" % int(time.time() - t0))


def tamanho_pasta(p):
    total = 0
    for base, _, arquivos in os.walk(str(p)):
        for a in arquivos:
            try:
                total += os.path.getsize(os.path.join(base, a))
            except Exception:
                pass
    return total


def etapa_runtime(ctx):
    titulo("1/8 · Runtime Python %s embeddable (portatil, sem admin)" % PY_VERSAO)
    py_dir = ctx["bundle"] / "python"
    if (py_dir / "python.exe").exists():
        log("  runtime ja existe em %s" % py_dir)
        return
    zip_path = baixar(URL_EMBED, ctx["cache"] / "python-embed.zip", 5 * 1048576,
                      chave="cache/python-embed.zip")
    py_dir.mkdir(parents=True, exist_ok=True)
    log("  extraindo...")
    with zipfile.ZipFile(str(zip_path)) as z:
        z.extractall(str(py_dir))

    pth = list(py_dir.glob("python*._pth"))
    if not pth:
        raise RuntimeError("nao achei o arquivo ._pth do embeddable")
    texto = pth[0].read_text(encoding="utf-8")
    if "#import site" in texto:
        pth[0].write_text(texto.replace("#import site", "import site"), encoding="utf-8")
        log("  'import site' religado em %s" % pth[0].name)
    (py_dir / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)
    if "Lib\\site-packages" not in texto:
        with open(str(pth[0]), "a", encoding="utf-8") as f:
            f.write("\nLib\\site-packages\n")
    log("  runtime pronto: %s" % py_dir)


def pip_responde(py):
    try:
        r = subprocess.run([str(py), "-m", "pip", "--version"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except Exception as e:
        return False, u"%s: %s" % (type(e).__name__, e)
    saida = (r.stdout or u"").strip() or (r.stderr or u"").strip()
    if r.returncode == 0 and saida.lower().startswith(u"pip "):
        return True, saida.split(u" from ")[0]
    return False, (saida.splitlines() or [u"codigo %s" % r.returncode])[-1]


def etapa_pip(ctx):
    titulo("2/8 · pip dentro do runtime portatil")
    py = ctx["py"]
    ok, qual = pip_responde(py)
    if ok:
        log("  pip ja instalado (%s)" % qual)
        return
    log("  o pip ainda nao esta no runtime (normal na primeira vez); "
        "baixando a roda")
    roda = baixar(URL_PIP, ctx["cache"] / PIP_RODA, 500000,
                  chave="cache/" + PIP_RODA)

    sp = Path(py).parent / "Lib" / "site-packages"
    sp.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(roda) as z:
        membros = [m for m in z.namelist()
                   if m.startswith("pip/") or m.startswith("pip-")]
        if not membros:
            raise SystemExit(
                "PAREI: %s nao tem o pacote `pip` dentro.\n"
                "Isso nao e uma roda do pip." % PIP_RODA)
        for m in membros:
            z.extract(m, str(sp))
    log("  pip extraido: %d arquivos em Lib/site-packages" % len(membros))

    rodar([py, "-m", "pip", "--version"], "pip --version")
    rodar([py, "-m", "pip", "install", "--no-warn-script-location", "setuptools<81"],
          "setuptools<81")


def clausula_que_exclui(requires_python, alvo=PY_VERSAO):
    if not requires_python:
        return ""
    meu = tuple(int(x) for x in str(alvo).split(".") if x.isdigit())
    if not meu:
        return ""
    for bruta in str(requires_python).split(","):
        m = re.match(r"^\s*(>=|<=|==|!=|>|<)\s*([0-9][0-9.]*)\s*$", bruta)
        if not m:
            continue
        op, txt = m.group(1), m.group(2).rstrip(".")
        dele = tuple(int(x) for x in txt.split(".") if x.isdigit())
        if not dele:
            continue
        cur = meu[:len(dele)]
        ruim = ((op == ">=" and cur < dele) or (op == ">" and cur <= dele) or
                (op == "<=" and cur > dele) or (op == "<" and cur >= dele) or
                (op == "!=" and cur == dele) or (op == "==" and cur != dele))
        if ruim:
            return bruta.strip()
    return ""


def roda_que_serve(arquivos):
    rodas = [f.get("filename", "") for f in arquivos
             if f.get("filename", "").endswith(".whl")]
    if not rodas:
        return True
    for nome in rodas:
        py_ok = ("cp310" in nome or "py3-none" in nome or "py2.py3" in nome)
        so_ok = ("win_amd64" in nome or nome.endswith("-any.whl"))
        if py_ok and so_ok:
            return True
    return False


def conferir_pinos_contra_runtime(linhas, alvo=PY_VERSAO):
    import json
    problemas, conferidos = [], 0
    for linha in linhas:
        nome, _, versao = str(linha).partition("==")
        nome, versao = nome.strip(), versao.split("#")[0].strip()
        if not nome or not versao or "+" in versao:
            continue
        try:
            url = "https://pypi.org/pypi/%s/%s/json" % (nome, versao)
            with urllib.request.urlopen(url, timeout=20) as r:
                dados = json.loads(r.read().decode("utf-8"))
            info, arquivos = dados.get("info") or {}, dados.get("urls") or []
        except Exception as exc:
            log("  (nao consegui conferir %s==%s no PyPI: %s -- o pip decide)"
                % (nome, versao, str(exc)[:60]))
            continue
        conferidos += 1
        clausula = clausula_que_exclui(info.get("requires_python"), alvo)
        if clausula:
            problemas.append((nome, versao, "versao",
                              "exige Python %s, e a clausula `%s` exclui o %s"
                              % (info.get("requires_python") or "?", clausula,
                                 alvo)))
        elif not roda_que_serve(arquivos):
            problemas.append((nome, versao, "roda",
                              "aceita o Python %s (%s) mas nao publica roda "
                              "cp310-win_amd64: o pip cairia no codigo-fonte, "
                              "e este runtime nao compila"
                              % (alvo, info.get("requires_python") or "sem "
                                 "Requires-Python")))
    if problemas:
        for nome, versao, _cod, motivo in problemas:
            log("  PINO INCOMPATIVEL: %s==%s %s" % (nome, versao, motivo))
        raise RuntimeError(
            "%d pino(s) de build/requirements-demo.txt nao instalam no Python "
            "%s deste pacote: %s. Corrija o pino no arquivo -- a versao mais "
            "nova do PyPI nem sempre suporta o runtime alvo."
            % (len(problemas), alvo,
               ", ".join("%s==%s" % (p[0], p[1]) for p in problemas)))
    log("  pinos conferidos contra o Python %s: %d ok" % (alvo, conferidos))


def etapa_libs(ctx):
    titulo("3/8 · Bibliotecas (torch %s, TotalSegmentator, DICOM...)" % ctx["cuda"])
    py = ctx["py"]
    req = RAIZ / "build" / "requirements-demo.txt"
    if not req.exists():
        raise RuntimeError("nao achei %s" % req)

    linhas = []
    for linha in req.read_text(encoding="utf-8").splitlines():
        cru = linha.strip()
        if not cru or cru.startswith("#"):
            continue
        if cru.startswith("torch=="):
            if ctx["so_cpu"]:
                linhas.append("torch==2.5.1")
            else:
                linhas.append("torch==2.5.1+%s" % ctx["cuda"])
            continue
        linhas.append(cru)
    req_efetivo = (Path(str(ctx.get("destino") or ctx["bundle"].parent))
                   / "requirements-efetivo.txt")
    req_efetivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    log("  requirements efetivo: %s" % req_efetivo)
    for l in linhas:
        log("     %s" % l)

    conferir_pinos_contra_runtime(linhas)

    cmd = [py, "-m", "pip", "install", "--no-warn-script-location", "-r", str(req_efetivo)]
    if not ctx["so_cpu"]:
        cmd += ["--extra-index-url", "https://download.pytorch.org/whl/%s" % ctx["cuda"]]
    rodar(cmd, "pip install -r requirements", timeout=7200)
    if not ctx.get("instalar"):
        tirar_lib_do_torch(ctx["bundle"])
    log("  tamanho do runtime: %s" % gb(tamanho_pasta(ctx["bundle"] / "python")))


def tirar_lib_do_torch(bundle):
    lib = Path(str(bundle)) / "python" / "Lib" / "site-packages" / "torch" / "lib"
    if not lib.is_dir():
        return 0
    n = total = 0
    for p in sorted(lib.glob("*.lib")):
        try:
            tam = p.stat().st_size
            p.unlink()
        except OSError as e:
            log("  nao consegui tirar %s (%s)" % (p.name, e))
            continue
        n += 1
        total += tam
    if n:
        log("  torch\\lib: %d biblioteca(s) de ligacao (.lib, %s) fora do "
            "pacote: so servem para compilar extensao do torch, e o programa "
            "carrega as .dll" % (n, mb(total)))
    return total


_SCRIPT_TABELA = (
    "import ast, inspect, json, sys, textwrap\n"
    "pedido = json.loads(sys.argv[1])\n"
    "fora = {'erro': [], 'itens': [], 'base': '', 'velhos': [],\n"
    "        'versao_ts': ''}\n"
    "try:\n"
    "    from importlib import metadata\n"
    "    fora['versao_ts'] = metadata.version('TotalSegmentator')\n"
    "except Exception:\n"
    "    pass\n"
    "from totalsegmentator import libs\n"
    "from totalsegmentator.map_tasks_config import TASK_ID_WEIGHTS_CONFIGS as T\n"
    "from totalsegmentator.bin.totalseg_download_weights import TASK_TO_ID\n"
    "arv = ast.parse(textwrap.dedent(inspect.getsource(\n"
    "    libs.download_pretrained_weights)))\n"
    "for no in ast.walk(arv):\n"
    "    if (isinstance(no, ast.Assign) and len(no.targets) == 1\n"
    "            and isinstance(no.targets[0], ast.Name)):\n"
    "        try:\n"
    "            if no.targets[0].id == 'url':\n"
    "                fora['base'] = ast.literal_eval(no.value)\n"
    "            elif no.targets[0].id == 'old_weights':\n"
    "                fora['velhos'] = list(ast.literal_eval(no.value))\n"
    "        except Exception as e:\n"
    "            fora['erro'].append('nao li %s: %s' % (no.targets[0].id, e))\n"
    "ids, de_onde = [], {}\n"
    "for t in pedido['tasks']:\n"
    "    if t not in TASK_TO_ID:\n"
    "        fora['erro'].append('task que a biblioteca nao conhece: %s' % t)\n"
    "        continue\n"
    "    for i in TASK_TO_ID[t]:\n"
    "        if i not in ids:\n"
    "            ids.append(i); de_onde[i] = t\n"
    "for i in pedido['extra']:\n"
    "    if i not in ids:\n"
    "        ids.append(i); de_onde[i] = 'recorte'\n"
    "for i in ids:\n"
    "    info = T.get(i)\n"
    "    fora['itens'].append({'id': i, 'de_onde': de_onde[i],\n"
    "                          'info': dict(info) if info else None})\n"
    "print('TABELA_JSON ' + json.dumps(fora), flush=True)\n"
)


def tabela_da_biblioteca(py, tasks, extra=(), env=None, timeout=600):
    pedido = json.dumps({"tasks": list(tasks),
                         "extra": [int(x) for x in extra]})
    try:
        r = subprocess.run([str(py), "-c", _SCRIPT_TABELA, pedido],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout,
                           env=dict(env or os.environ,
                                    PYTHONIOENCODING="utf-8:replace"))
    except Exception as e:
        raise RuntimeError("nao consegui ler a tabela de pesos da biblioteca "
                           "(%s: %s)" % (type(e).__name__, e))
    linha = next((l for l in (r.stdout or "").splitlines()
                  if l.startswith("TABELA_JSON ")), None)
    if r.returncode != 0 or linha is None:
        cauda = " | ".join(((r.stdout or "") + (r.stderr or "")).strip()
                           .splitlines()[-6:])
        raise RuntimeError("nao consegui ler a tabela de pesos da biblioteca "
                           "(codigo %s): %s" % (r.returncode, cauda[-400:]))
    t = json.loads(linha[len("TABELA_JSON "):])
    problemas = list(t.get("erro") or [])
    base = str(t.get("base") or "").rstrip("/")
    if not base.lower().startswith("https://"):
        problemas.append("a biblioteca nao declara a URL base dos pesos (lida "
                         "de `download_pretrained_weights`): %r" % base)
    itens = []
    for it in t.get("itens") or []:
        info = it.get("info")
        if not info:
            problemas.append("Dataset%s: a biblioteca nao tem caminho de "
                             "download" % it.get("id"))
            continue
        versao = info.get("version")
        if info.get("commercial") or not versao or versao == "TODO":
            problemas.append("Dataset%s: a biblioteca nao publica este peso "
                             "no GitHub (versao=%r, comercial=%r)"
                             % (it.get("id"), versao, info.get("commercial")))
            continue
        pasta = str(info["foldername"])
        itens.append({"id": it["id"], "pasta": pasta,
                      "rel_path": info.get("rel_path") or "",
                      "url": "%s/%s/%s.zip" % (base, versao, pasta),
                      "zip": pasta + ".zip",
                      "de_onde": it.get("de_onde") or ""})
    if problemas:
        raise RuntimeError("a tabela de pesos da biblioteca nao serve para "
                           "montar o pacote: %s" % "; ".join(problemas))
    return {"base": base, "velhos": list(t.get("velhos") or []),
            "versao_ts": t.get("versao_ts") or "", "itens": itens}


def _peso_completo(pasta):
    pasta = Path(str(pasta))
    if not pasta.is_dir():
        return False
    for _raiz, _pastas, arquivos in os.walk(str(pasta)):
        if any(a.endswith(".pth") for a in arquivos):
            return True
    return False


def _extrair_como_a_biblioteca(zip_path, pai, pasta):
    pai = Path(str(pai))
    pai.mkdir(parents=True, exist_ok=True)
    passagem = pai / (".x" + (re.sub(r"\D", "", pasta.split("_")[0])[:6]
                              or "p"))
    if passagem.exists():
        shutil.rmtree(str(passagem), ignore_errors=True)
    passagem.mkdir(parents=True)
    try:
        with zipfile.ZipFile(str(zip_path)) as z:
            z.extractall(str(passagem))
        for nome in sorted(os.listdir(str(passagem))):
            de = passagem / nome
            para = pai / nome
            if nome == pasta:
                if para.exists():
                    shutil.rmtree(str(para), ignore_errors=True)
                os.replace(str(de), str(para))
            elif de.is_dir():
                shutil.copytree(str(de), str(para), dirs_exist_ok=True)
            else:
                shutil.copy2(str(de), str(para))
    finally:
        shutil.rmtree(str(passagem), ignore_errors=True)


def instalar_peso_ts(item, pesos, cache, py_recuo=None, registro=None,
                     py_do_pacote=None, enxutos=None):
    try:
        import artefatos
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import artefatos
    pesos = Path(str(pesos))
    pai = pesos / item["rel_path"] if item.get("rel_path") else pesos
    alvo = pai / item["pasta"]
    rot = "Dataset%s" % item["id"]
    if _peso_completo(alvo):
        log("  %s: ja no disco (%s)" % (rot, item["pasta"]))
        return "ja"
    if alvo.exists():
        log("  %s: a pasta existe SEM checkpoint (extracao interrompida?). "
            "Refaco." % rot)
        shutil.rmtree(str(alvo), ignore_errors=True)
    zdir = Path(str(cache)) / "pesos_ts"
    zdir.mkdir(parents=True, exist_ok=True)
    zip_ = zdir / item["zip"]
    medido = ""
    if zip_.exists():
        ok, msg, medido = artefatos.conferir_peso_ts(str(zip_), item["zip"],
                                                     item["pasta"])
        if ok:
            log("  %s: zip ja estava no cache, e confere" % rot)
        else:
            log("  %s: o zip do cache NAO confere, e sai (%s)"
                % (rot, msg.splitlines()[0]))
            zip_.unlink()
    if not zip_.exists():
        log("  %s: baixando %s" % (rot, item["url"]))
        parcial = zip_.with_suffix(".zip.parcial")
        t0 = time.time()
        _transferir(item["url"], parcial, _relogio_de_progresso(), py_recuo)
        os.replace(str(parcial), str(zip_))
        log("  %s: %s em %ds" % (rot, mb(zip_.stat().st_size),
                                 int(time.time() - t0)))
        ok, msg, medido = artefatos.conferir_peso_ts(str(zip_), item["zip"],
                                                     item["pasta"])
        if not ok:
            diverge = artefatos.diverge_da_origem(item["zip"],
                                                  zip_.stat().st_size, medido)
            try:
                zip_.unlink()
            except OSError:
                pass
            if diverge:
                _rel = (artefatos.PESOS_TS.get(item["zip"]) or {}).get("release")
                _pino = u""
                if _rel and (u"/%s/" % _rel) not in item["url"]:
                    _pino = (u"\n     E a tabela do projeto registra a release "
                             u"%s, enquanto a biblioteca pede %s: o pino do "
                             u"TotalSegmentator subiu e build/artefatos.PESOS_TS "
                             u"ficou para tras." % (_rel, item["url"]))
                raise DivergeDaOrigem(
                    u"CONFERENCIA FALHOU (%s): o arquivo chegou, e NAO e o que "
                    u"a origem publicou.\n     %s%s\n"
                    u"     Isto PARA o preparo, e nao troca a base pela "
                    u"reserva: a reserva e' para o peso que nao veio, e este "
                    u"veio diferente. Baixar de novo traria o mesmo arquivo; "
                    u"alguem precisa conferir a origem (ou o proxy desta rede) "
                    u"antes de montar o pacote." % (rot, msg, _pino))
            raise RuntimeError("CONFERENCIA FALHOU (%s)\n     %s" % (rot, msg))
    log("  conferido: %s" % msg)
    log("  sha256 medido: %s" % medido)
    if registro is not None:
        registro[item["zip"]] = {
            "bytes": zip_.stat().st_size, "sha256": medido,
            "veredito": msg.split(": ", 1)[-1],
            "url": item["url"], "quando": datetime.now().isoformat(
                timespec="seconds")}
    _extrair_como_a_biblioteca(zip_, pai, item["pasta"])
    if not _peso_completo(alvo):
        raise RuntimeError("%s: extraido, e a pasta %s continua sem "
                           "checkpoint -- o zip nao tem a forma que a "
                           "biblioteca espera" % (rot, item["pasta"]))
    try:
        zip_.unlink()
    except OSError:
        pass
    enxugar_pasta_de_peso(py_do_pacote, alvo, pesos, enxutos)
    return "baixado"


REGISTRO_DOS_PESOS = "pesos_ts_conferidos.json"
RECIBO_DO_ENXUGAR = "checkpoints_enxugados.json"

_SCRIPT_ENXUGAR = """import hashlib, json, os, sys
import torch
FORMATOS = (('network_weights', 'optimizer_state', None),
            ('state_dict', 'optimizer_state_dict', 'plot_stuff'))
AVISO = 'radai_modificacao'
def texto(rede, chave):
    return ('Radioterapia.AI Local Suite, preparo do pacote: %s '
            'removido (so serve ao treino); %s e as demais '
            'entradas sem alteracao.' % (chave, rede))
def formato(ck):
    if isinstance(ck, dict):
        for rede, chave, marca in FORMATOS:
            if isinstance(ck.get(rede), dict) and (marca is None or marca in ck):
                return rede, chave
    return None
def ler(p):
    try:
        return torch.load(p, map_location='cpu', weights_only=False)
    except TypeError:
        return torch.load(p, map_location='cpu')
def soma(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()
def crus(t):
    t = t.detach().cpu().contiguous().reshape(-1)
    return t.view(torch.uint8).numpy().tobytes() if t.numel() else b''
def digest(sd):
    h = hashlib.sha256()
    n = 0
    for k, v in sd.items():
        h.update(repr(k).encode('utf-8'))
        if torch.is_tensor(v):
            n += 1
            h.update(str(v.dtype).encode('ascii'))
            h.update(repr(tuple(v.shape)).encode('ascii'))
            h.update(crus(v))
        else:
            h.update(repr(v).encode('utf-8'))
    return h.hexdigest(), n
def igual(a, b):
    import numpy as np
    if torch.is_tensor(a) or torch.is_tensor(b):
        return (torch.is_tensor(a) and torch.is_tensor(b)
                and a.dtype == b.dtype and tuple(a.shape) == tuple(b.shape)
                and crus(a) == crus(b))
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return (type(a) is type(b) and a.dtype == b.dtype
                and a.shape == b.shape and a.tobytes() == b.tobytes())
    if isinstance(a, np.generic) or isinstance(b, np.generic):
        return type(a) is type(b) and a.tobytes() == b.tobytes()
    if isinstance(a, dict):
        return (type(a) is type(b) and list(a.keys()) == list(b.keys())
                and all(igual(a[k], b[k]) for k in a))
    if isinstance(a, (list, tuple)):
        return (type(a) is type(b) and len(a) == len(b)
                and all(igual(x, y) for x, y in zip(a, b)))
    if isinstance(a, float) and isinstance(b, float):
        return a == b or (a != a and b != b)
    try:
        r = a == b
        return r if isinstance(r, bool) else repr(a) == repr(b)
    except Exception:
        return repr(a) == repr(b)
def sair(r, codigo=0):
    print('ENXUGAR_JSON ' + json.dumps(r), flush=True)
    sys.exit(codigo)
def comparar(pa, pb):
    a, b = ler(pa), ler(pb)
    rede, chave = formato(a) or FORMATOS[0][:2]
    fora = [k for k in a if k not in (chave, AVISO)
            and (k not in b or not igual(a[k], b[k]))]
    fora += [k for k in b if k not in a and k not in (chave, AVISO)]
    da = digest(a.get(rede) or {})
    db = digest(b.get(rede) or {})
    sair({'estado': 'iguais' if not fora and da == db else 'diferentes',
          'diferem': fora, 'digest_a': da[0], 'digest_b': db[0],
          'tensores': da[1]})
def enxugar(c, esperado=''):
    base = {'bytes_antes': os.path.getsize(c), 'sha256_antes': soma(c)}
    ck = ler(c)
    f = formato(ck)
    if f is None:
        sair(dict(base, estado='nao_e_nnunet'))
    rede, chave = f
    d0, n0 = digest(ck[rede])
    base.update(digest_rede=d0, tensores=n0)
    if chave not in ck:
        sair(dict(base, estado='sem_estado_do_otimizador'))
    aviso = texto(rede, chave)
    novo = {}
    for k, v in ck.items():
        if k != chave:
            novo[k] = v
    novo[AVISO] = aviso
    tmp = c + '.enxuto.parcial'
    # GUARDA: gravar pelo objeto de arquivo; pelo caminho o torch poe o nome do arquivo dentro do zip e o sha256 do enxuto deixa de ser reprodutivel
    with open(tmp, 'wb') as saida:
        torch.save(novo, saida)
    del novo
    volta = ler(tmp)
    fora = []
    if list(volta.keys()) != [k for k in ck if k != chave] + [AVISO]:
        fora.append('chaves: %r' % list(volta.keys()))
    for k in ck:
        if k != chave and (k not in volta or not igual(ck[k], volta[k])):
            fora.append('a entrada %s mudou' % k)
    if digest(volta.get(rede) or {}) != (d0, n0):
        fora.append('os pesos da rede mudaram')
    if volta.get(AVISO) != aviso:
        fora.append('o aviso de modificacao nao ficou no arquivo')
    del volta
    if not fora and esperado and soma(tmp) != esperado:
        fora.append('o enxuto nao e o do registro (sha256 %s, o registro '
                    'diz %s)' % (soma(tmp)[:12], esperado[:12]))
    if fora:
        os.remove(tmp)
        sair(dict(base, estado='diverge', problemas=fora), 3)
    os.replace(tmp, c)
    sair(dict(base, estado='enxugado', removido=chave,
              bytes_depois=os.path.getsize(c), sha256_depois=soma(c)))
if sys.argv[1] == 'comparar':
    comparar(sys.argv[2], sys.argv[3])
else:
    enxugar(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
"""


def _rodar_enxugar(py, args, timeout):
    try:
        r = subprocess.run([str(py), "-B", "-c", _SCRIPT_ENXUGAR]
                           + [str(a) for a in args],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout,
                           env=dict(os.environ,
                                    PYTHONIOENCODING="utf-8:replace",
                                    PYTHONDONTWRITEBYTECODE="1"))
    except Exception as e:
        return {"estado": "falhou",
                "detalhe": u"%s: %s" % (type(e).__name__, e)}
    linha = next((l for l in (r.stdout or "").splitlines()
                  if l.startswith("ENXUGAR_JSON ")), None)
    if linha is None:
        cauda = " | ".join(((r.stdout or "") + (r.stderr or "")).strip()
                           .splitlines()[-4:])
        return {"estado": "falhou",
                "detalhe": u"codigo %s: %s" % (r.returncode, cauda[-300:])}
    return json.loads(linha[len("ENXUGAR_JSON "):])


def enxugar_checkpoint(py, caminho, timeout=1800, esperado=None):
    return _rodar_enxugar(py, ["enxugar", caminho]
                          + ([esperado] if esperado else []), timeout)


def comparar_checkpoints(py, original, enxuto, timeout=1800):
    return _rodar_enxugar(py, ["comparar", original, enxuto], timeout)


def checkpoints_da_pasta(pasta):
    fora = []
    for raiz, pastas, arquivos in os.walk(str(pasta)):
        pastas.sort()
        for a in sorted(arquivos):
            if a.startswith("checkpoint") and a.endswith(".pth"):
                fora.append(Path(raiz) / a)
    return fora


def _enxugar_e_relatar(py, ck, rel, enxutos=None, esperado=None):
    r = enxugar_checkpoint(py, ck, esperado=esperado)
    estado = r.get("estado")
    if estado == "enxugado":
        log("  estado do otimizador removido: %s (%s -> %s); pesos da "
            "rede identicos byte a byte (%d tensores)"
            % (rel, mb(r["bytes_antes"]), mb(r["bytes_depois"]),
               int(r.get("tensores") or 0)))
        log("    sha256 antes  %s" % r["sha256_antes"])
        log("    sha256 depois %s" % r["sha256_depois"])
        if enxutos is not None:
            enxutos[rel] = dict(r, quando=datetime.now().isoformat(
                timespec="seconds"))
    elif estado == "sem_estado_do_otimizador":
        log("  %s: ja estava sem o estado do otimizador" % rel)
    elif estado == "nao_e_nnunet":
        log("  %s: nao e checkpoint do nnU-Net; fica como veio" % rel)
    else:
        log("  !! %s: o estado do otimizador FICA (%s). O arquivo segue "
            "o original, conferido no download."
            % (rel, "; ".join(r.get("problemas") or [])
               or r.get("detalhe") or estado))
    return rel, r


def enxugar_pasta_de_peso(py, pasta, pesos, enxutos=None):
    if not py or not os.path.isfile(str(py)):
        log("  estado do otimizador: fica nos checkpoints de %s (sem o Python "
            "do pacote para conferir a rede)" % Path(str(pasta)).name)
        return []
    return [_enxugar_e_relatar(py, ck, ck.relative_to(Path(str(pesos)))
                               .as_posix(), enxutos)
            for ck in checkpoints_da_pasta(pasta)]


def _assinatura(caminho):
    try:
        st = os.stat(str(caminho))
    except OSError:
        return None
    return st.st_size, st.st_mtime_ns


def enxugar_modelo_do_registro(py, ident, m, pasta, antes, enxutos=None):
    pedidos = m.get("enxuto") or {}
    chegaram = [rel for rel in sorted(pedidos)
                if _assinatura(Path(str(pasta)) / rel)
                not in (None, antes.get(rel))]
    if not chegaram:
        return []
    if not py or not os.path.isfile(str(py)):
        log("  estado do otimizador: fica nos pesos de %s (sem o Python do "
            "pacote para conferir a rede)" % ident)
        return []
    return [_enxugar_e_relatar(py, Path(str(pasta)) / rel,
                               "modelos/%s/%s" % (ident, rel), enxutos,
                               esperado=pedidos[rel][1])
            for rel in chegaram]


def _ler_recibo_do_enxugar(oficina):
    try:
        return json.loads((Path(str(oficina)) / RECIBO_DO_ENXUGAR)
                          .read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gravar_recibo_do_enxugar(oficina, recibo):
    try:
        (Path(str(oficina)) / RECIBO_DO_ENXUGAR).write_text(
            json.dumps(recibo, indent=1, sort_keys=True), encoding="utf-8")
    except Exception as e:
        log("  AVISO: nao consegui gravar %s (%s)" % (RECIBO_DO_ENXUGAR, e))


def _ler_registro_dos_pesos(oficina):
    try:
        return json.loads((Path(str(oficina)) / REGISTRO_DOS_PESOS)
                          .read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gravar_registro_dos_pesos(oficina, registro):
    try:
        (Path(str(oficina)) / REGISTRO_DOS_PESOS).write_text(
            json.dumps(registro, indent=1, sort_keys=True), encoding="utf-8")
    except Exception as e:
        log("  AVISO: nao consegui gravar %s (%s)" % (REGISTRO_DOS_PESOS, e))


def baixar_pesos_ts(py, tasks, pesos, cache, extra=(), env=None,
                    oficina=None):
    tab = tabela_da_biblioteca(py, tasks, extra, env)
    log("  tabela da biblioteca (TotalSegmentator %s): %d arquivo(s), de %s"
        % (tab["versao_ts"] or "?", len(tab["itens"]), tab["base"]))
    pesos = Path(str(pesos))
    for velho in tab["velhos"]:
        p = pesos / velho
        if p.exists():
            log("  removendo peso de geracao antiga (a biblioteca faz o "
                "mesmo): %s" % velho)
            shutil.rmtree(str(p), ignore_errors=True)
    registro = _ler_registro_dos_pesos(oficina) if oficina else {}
    enxutos = _ler_recibo_do_enxugar(oficina) if oficina else {}
    falhas = {}
    try:
        for n, item in enumerate(tab["itens"], 1):
            log("  -- %d/%d  Dataset%s  (%s)"
                % (n, len(tab["itens"]), item["id"], item["de_onde"]))
            try:
                instalar_peso_ts(item, pesos, cache, py_recuo=py,
                                 registro=registro, py_do_pacote=py,
                                 enxutos=enxutos)
            except (SemRede, DivergeDaOrigem):
                raise
            except Exception as e:
                falhas[item["id"]] = u"%s" % e
                log("  !! Dataset%s NAO veio: %s" % (item["id"], e))
        segunda = [it for it in tab["itens"] if it["id"] in falhas]
        if segunda:
            log("  segunda tentativa para %d dataset(s) que nao vieram: %s"
                % (len(segunda), ", ".join("Dataset%s" % it["id"]
                                          for it in segunda)))
        for item in segunda:
            try:
                instalar_peso_ts(item, pesos, cache, py_recuo=py,
                                 registro=registro, py_do_pacote=py,
                                 enxutos=enxutos)
                del falhas[item["id"]]
                log("  -- Dataset%s veio na segunda tentativa" % item["id"])
            except (SemRede, DivergeDaOrigem):
                raise
            except Exception as e:
                falhas[item["id"]] = u"%s" % e
                log("  !! Dataset%s NAO veio de novo: %s" % (item["id"], e))
    finally:
        if oficina:
            _gravar_registro_dos_pesos(oficina, registro)
            if enxutos:
                _gravar_recibo_do_enxugar(oficina, enxutos)
    return falhas


def garantir_base(alvo, pesos, py, env=None, cache=None, oficina=None):
    import radai_tasks
    def _da_base(t):
        return set(radai_tasks.datasets_necessarios(t, recorte_no_corpo=False))
    alvo = list(alvo)
    for base in list(alvo):
        reserva = radai_tasks.reserva_de(base)
        if not reserva:
            continue
        if _da_base(base) <= set(radai_tasks.baixados(str(pesos))):
            continue
        log("  !! a base %s NAO baixou. Indo para a reserva %s."
            % (base, reserva))
        baixar_pesos_ts(py, [radai_tasks.nome_na_biblioteca(reserva)],
                        pesos, cache or Path(str(pesos)).parent / "cache",
                        env=env, oficina=oficina)
        if _da_base(reserva) <= set(radai_tasks.baixados(str(pesos))):
            alvo[alvo.index(base)] = reserva
            log("  -- a estacao vai rodar com a %s" % reserva)
        else:
            raise RuntimeError(
                "nem a base %s nem a reserva %s baixaram. Sem base anatomica "
                "o pacote sai sem pulmao, sem coracao e sem osso. Confira a "
                "rede e rode de novo." % (base, reserva))
    return tuple(alvo)


def conferir_recorte_no_corpo(pesos):
    import radai_tasks
    presente, frase = radai_tasks.pesos_do_recorte_no_corpo(str(pesos))
    if presente:
        log("  recorte no corpo: %s" % radai_tasks.DATASET_DO_BODY_PASTA)
        return
    raise RuntimeError(
        "o recorte no corpo (--body_seg) nao esta no pacote: %s. Sem o "
        "Dataset%d a estacao roda cada TC sem o recorte, com o dobro do "
        "tempo em CPU, ou tenta baixa-lo numa internet que nao tem. Nao "
        "empacote: rode a etapa 4 de novo (--etapas 4) com internet."
        % (frase, radai_tasks.DATASET_BODY))


class FaltaModeloExigido(RuntimeError):
    pass


def modelos_exigidos():
    _ligar_caminho()
    import radai_motores_full
    return radai_motores_full.modelos_do_entregue()


def conferir_modelos_exigidos(bundle, exigidos=None):
    _ligar_caminho()
    import radai_models
    velho = os.environ.get("RADAI_MODELOS_DIR")
    os.environ["RADAI_MODELOS_DIR"] = str(Path(str(bundle)) / "modelos")
    problemas = []
    try:
        for ident in (modelos_exigidos() if exigidos is None else exigidos):
            e = radai_models.estado_do_modelo(ident)
            if not e.get("instalado"):
                problemas.append(u"%s: faltam %s" % (
                    ident, u", ".join(e.get("faltando") or []) or u"os pesos"))
                continue
            d = radai_models.pasta_do_modelo(ident)
            antes = len(problemas)
            m = radai_models.MODELOS[ident]
            for rel, sha in sorted((m.get("sha256") or {}).items()):
                aceitas = {sha}
                enxuto = (m.get("enxuto") or {}).get(rel)
                if enxuto:
                    aceitas.add(enxuto[1])
                if not (d / rel).is_file() or sha256_de(d / rel) not in aceitas:
                    problemas.append(u"%s: %s nao confere com o registro"
                                     % (ident, rel))
            if len(problemas) == antes:
                log("  %-16s pesos conferidos (alimenta o entregue)" % ident)
    finally:
        if velho is None:
            os.environ.pop("RADAI_MODELOS_DIR", None)
        else:
            os.environ["RADAI_MODELOS_DIR"] = velho
    if problemas:
        raise FaltaModeloExigido(
            u"o pacote nao sai sem os modelos que alimentam o entregue:\n     "
            + u"\n     ".join(problemas))


def baixar_modelos_do_registro(ctx, radai_models, fora_por_escolha,
                               exigidos=None):
    exigidos = set(modelos_exigidos() if exigidos is None else exigidos)
    oficina = ctx.get("destino")
    enxutos = _ler_recibo_do_enxugar(oficina) if oficina else {}
    recibo_antes = dict(enxutos)
    try:
        os.environ["RADAI_MODELOS_DIR"] = str(ctx["bundle"] / "modelos")
        faltaram = []
        for ident, m in radai_models.MODELOS.items():
            if m.get("embutido"):
                continue
            if ident in exigidos and (ident in fora_por_escolha or not (
                    m.get("repo") or m.get("url_direta")
                    or m.get("url_por_arquivo"))):
                raise FaltaModeloExigido(
                    u"%s alimenta o RTSTRUCT entregue e nao pode ficar fora "
                    u"do pacote" % ident)
            if ident in fora_por_escolha:
                log("  -- %s: DISPENSADO por escolha na tela. Nao foi "
                    "baixado, e o conjunto de comparacao dele nao sai. "
                    "A entrega (RadAI_OAR e RadAI_Full) nao muda." % ident)
                continue
            if not (m.get("repo") or m.get("url_direta") or m.get("url_por_arquivo")):
                log("  -- %s: sem rota de download automatico, pulado" % ident)
                continue
            try:
                e = radai_models.estado_do_modelo(ident)
                log("  -- %s (%s, %.0f MB)"
                    % (ident, m["licenca"].split("·")[-1].strip()[:46],
                       (e["bytes_total"] or 0) / 1e6))
                pasta = radai_models.pasta_do_modelo(ident)
                antes = dict((rel, _assinatura(Path(str(pasta)) / rel))
                             for rel in (m.get("enxuto") or {}))
                r = radai_models.baixar(ident)
                log("     baixados: %s | ja tinha: %s"
                    % (", ".join(r.get("baixados") or []) or "nada",
                       len(r.get("pulados") or [])))
                if m.get("uso_permitido") == "nao_comercial":
                    log("     LICENCA DOS PESOS: USO NAO COMERCIAL (%s). "
                        "O aceite ja foi dado na tela de licencas."
                        % m["licenca"])
            except Exception as e2:
                faltaram.append(ident)
                if ident in exigidos:
                    msg = (u"%s NAO BAIXADO (%s: %s). Ele alimenta o RTSTRUCT "
                           u"entregue: o pacote nao sai sem ele."
                           % (ident, type(e2).__name__, e2))
                    if falha_de_rede(e2):
                        raise SemRede(msg) from e2
                    raise FaltaModeloExigido(msg) from e2
                if falha_de_rede(e2):
                    log("     SEM CONEXAO para este modelo. O pacote sai sem "
                        "ele e o aplicativo funciona normalmente -- o que "
                        "falta e o conjunto de comparacao dele.")
                else:
                    log("     %s NAO BAIXADO (%s: %s)"
                        % (ident, type(e2).__name__, e2))
                    log("     O pacote sai sem ele; o aplicativo funciona.")
            else:
                if not ctx.get("instalar"):
                    enxugar_modelo_do_registro(ctx.get("py"), ident, m, pasta,
                                               antes, enxutos)
        entraram = [i for i, m in radai_models.MODELOS.items()
                    if not m.get("embutido")
                    and (m.get("repo") or m.get("url_direta"))
                    and i not in faltaram and i not in fora_por_escolha]
        log("  ── o que este pacote leva ──")
        log("     TotalSegmentator: embutido, e o motor do lote")
        for i in sorted(entraram):
            log("     %-16s pesos NO PACOTE" % i)
        for i in sorted(fora_por_escolha):
            log("     %-16s DISPENSADO por escolha (nao e falha)" % i)
        for i in sorted(faltaram):
            log("     %-16s NAO BAIXADO -- veja o motivo acima" % i)
        if faltaram:
            log("  ATENCAO: %d modelo(s) sem os pesos neste pacote: %s. O "
                "TotalSegmentator faz o fluxo principal e esta completo."
                % (len(faltaram), ", ".join(faltaram)))
        log("  modelos: %s" % gb(tamanho_pasta(ctx["bundle"] / "modelos")))
    except (SemRede, FaltaModeloExigido):
        raise
    except Exception as e:
        log("     nenhum modelo extra baixado (%s: %s). O bundle segue "
            "valido: o TotalSegmentator e o motor padrao."
            % (type(e).__name__, e))
    finally:
        if oficina and enxutos != recibo_antes:
            _gravar_recibo_do_enxugar(oficina, enxutos)

def etapa_pesos(ctx):
    import radai_tasks
    alvo = TASKS
    try:
        custo = radai_tasks.custo_mb(list(alvo), base="__vazio__")
    except Exception:
        custo = 0
    titulo("4/8 · Pesos do TotalSegmentator (%d task(s), ~%.1f GB)"
           % (len(alvo), custo / 1024.0))
    pesos = ctx["bundle"] / "ts_weights"
    pesos.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TOTALSEG_WEIGHTS_PATH=str(pesos))
    cache = ctx.get("cache") or Path(str(ctx["bundle"])).parent / "cache"
    oficina = ctx.get("destino")
    tasks_lib = [radai_tasks.nome_na_biblioteca(t) for t in alvo]
    log("  tasks: %s" % ", ".join(alvo))


    try:
        extra = list(radai_tasks.datasets_do_pacote(list(alvo)))
    except Exception as e:
        raise RuntimeError(
            "nao consegui conferir os localizadores de recorte (%s). O pacote "
            "sairia possivelmente sem o Dataset297/300/852, e a estacao "
            "travaria offline na primeira execucao dessas tasks." % e)
    falhas = baixar_pesos_ts(ctx["py"], tasks_lib, pesos, cache, extra=extra,
                             env=env, oficina=oficina)
    alvo = garantir_base(alvo, pesos, ctx["py"], env, cache=cache,
                         oficina=oficina)

    ainda = [n for n in radai_tasks.datasets_do_pacote(list(alvo))
             if n not in radai_tasks.baixados(str(pesos))]
    if ainda:
        motivos = "".join("\n     Dataset%d: %s" % (n, str(falhas[n])
                                                      .splitlines()[0][:160])
                          for n in ainda if n in falhas)
        raise RuntimeError(
            "faltam pesos depois do download: %s. Nao empacote: a estacao e "
            "offline, e o que faltar aqui falta la para sempre.%s"
            % (", ".join("Dataset%d" % n for n in ainda), motivos))
    conferir_recorte_no_corpo(pesos)

    log("  %d tasks baixadas; pesos: %s" % (len(alvo), gb(tamanho_pasta(pesos))))

    _ligar_caminho()
    import radai_models

    fora_por_escolha = []
    try:
        _arq = Path(ctx["preparo"]) / "LICENCAS_ACEITAS.txt"
        for _nome in dispensados(_arq):
            _id = IDENT_DISPENSAVEL.get(_nome)
            if _id:
                fora_por_escolha.append(_id)
    except Exception as _e:
        log("  nao consegui ler a escolha de licencas (%s): baixando o que "
            "tiver rota" % type(_e).__name__)


    baixar_modelos_do_registro(ctx, radai_models, fora_por_escolha)




DISPENSAVEIS = ()

IDENT_DISPENSAVEL = {}


def dispensados(arquivo):
    try:
        if not arquivo.is_file():
            return []
        texto = arquivo.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    fora = []
    for linha in texto.split("\n"):
        if "[DISPENSADO]" not in linha:
            continue
        for nome in DISPENSAVEIS:
            if nome.lower() in linha.lower():
                fora.append(nome)
    return sorted(set(fora))


def _exigir_aceite_completo(arquivo):
    if not arquivo.is_file():
        return
    try:
        texto = arquivo.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        raise SystemExit("Nao consegui ler o %s: %s" % (arquivo, e))
    recusadas = [l.strip() for l in texto.split("\n") if "[RECUSADA]" in l]
    if recusadas:
        raise SystemExit(
            "PAREI: ha licenca RECUSADA no %s.\n\n"
            "%s\n\n"
            "Estes componentes sao OBRIGATORIOS: sem eles nao ha programa\n"
            "nenhum a montar, e nada e instalado.\n\n"
            "Nenhum componente do pacote e de uso restrito, entao nao\n"
            "ha o que marcar como [DISPENSADO]."
            % (arquivo, "\n".join("  " + r for r in recusadas[:8])))


if str(RAIZ / "build") not in sys.path:
    sys.path.insert(0, str(RAIZ / "build"))


def _texto_entrega(projeto, versao, produto=""):
    import carimbo
    return carimbo.texto(projeto, versao, produto, raiz=RAIZ)


def gravar_impressao(b, versao):
    try:
        try:
            import requisitos as _req
        except ImportError:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import requisitos as _req
        _caminho, _d = _req.gravar(str(RAIZ), str(b), versao)
        log("  %s  (impressao %s)" % (_req.ARQUIVO, _d["impressao"][:12]))
    except Exception as _e:
        raise RuntimeError("nao consegui gravar a impressao de "
                           "requisitos: %s" % _e)


def etapa_app(ctx):
    titulo("5/8 · Aplicacao (worker, motor, libs e ferramentas)")
    b = ctx["bundle"]
    obrigatorios = ["engine.py", "radai_watcher.py", "radai_geom.py",
                    "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"]
    sys.path.insert(0, str(RAIZ / "tools"))
    import _componentes
    origens = {}
    for pasta_app in _componentes.pastas_base("app", str(RAIZ)):
        for padrao in ("radai_*.py", "*.cmd"):
            for p in Path(pasta_app).glob(padrao):
                if p.name in origens:
                    raise RuntimeError("app/%s existe em dois projetos: %s e %s"
                                       % (p.name, origens[p.name], p))
                origens[p.name] = p
    for nome in obrigatorios:
        if nome not in origens:
            for pasta_app in _componentes.pastas_base("app", str(RAIZ)):
                if (Path(pasta_app) / nome).is_file():
                    origens[nome] = Path(pasta_app) / nome
                    break
        if nome not in origens:
            raise RuntimeError("falta app/%s" % nome)
    for nome in sorted(origens):
        shutil.copy2(str(origens[nome]), str(b / nome))
        log("  %s" % nome)

    dados = RAIZ / "app" / "data"
    if dados.is_dir():
        alvo_dados = b / "data"
        alvo_dados.mkdir(parents=True, exist_ok=True)
        n_dados = 0
        for p in sorted(dados.glob("*.json")):
            shutil.copy2(str(p), str(alvo_dados / p.name))
            n_dados += 1
        log("  data/  %d arquivo(s) de referencia (bibliografia, desempenho "
            "publicado)" % n_dados)
        if not n_dados:
            log("  ATENCAO: `app\\data\\` existe e esta sem .json — a tela de "
                "Procedencia e o desempenho publicado saem vazios")

    # GUARDA: a porta mora numa subpasta de app/; sem esta copia a estacao abre a porta sem script, arte e fonte.
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "radai_porta_do_preparo", str(RAIZ / "app" / "radai_porta.py"))
    _rp = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_rp)
    alvo_porta = b / _rp.PASTA
    alvo_porta.mkdir(parents=True, exist_ok=True)
    for nome in sorted(_rp.ARQUIVOS):
        origem = RAIZ / "app" / _rp.PASTA / nome
        if not origem.is_file():
            raise RuntimeError("falta app/%s/%s" % (_rp.PASTA, nome))
        shutil.copy2(str(origem), str(alvo_porta / nome))
    log("  %s/  %d arquivo(s) da porta" % (_rp.PASTA, len(_rp.ARQUIVOS)))

    lancadores = b / "launchers"
    lancadores.mkdir(parents=True, exist_ok=True)
    for p in sorted((RAIZ / "app" / "launchers").glob("*.cmd")):
        shutil.copy2(str(p), str(lancadores / p.name))
        log("  launchers/%s" % p.name)
    if not list(lancadores.glob("*.cmd")):
        raise RuntimeError(
            "app/launchers/ nao tem .cmd: o INSTALL.ps1 exige "
            "launchers/start_watcher.cmd e recusaria a instalacao inteira")
    ferramentas = b / "maintenance"
    ferramentas.mkdir(parents=True, exist_ok=True)
    for desinst in ("UNINSTALL.cmd", "UNINSTALL.ps1"):
        origem = RAIZ / "installer" / desinst
        if not origem.exists():
            raise RuntimeError("falta installer/%s" % desinst)
        shutil.copy2(str(origem), str(ferramentas / desinst))
        log("  maintenance/%s" % desinst)

    if ctx.get("instalar"):
        log("  a impressao de requisitos sai no fim, junto com o entrega.txt")
    else:
        gravar_impressao(b, ctx["versao"])

    icones = sorted(p for p in (RAIZ / "app").iterdir()
                    if p.suffix.lower() in (".ico", ".png", ".svg"))
    for origem in icones:
        shutil.copy2(str(origem), str(b / origem.name))
        log("  %s" % origem.name)
    if not any(p.suffix.lower() == ".ico" for p in icones):
        log("  AVISO: nenhum .ico em app/ — atalhos ficarao com o icone padrao")

    destino_tools = b / "tools"
    destino_tools.mkdir(exist_ok=True)
    for p in sorted((RAIZ / "tools").glob("*.py")):
        shutil.copy2(str(p), str(destino_tools / p.name))
        log("  tools/%s" % p.name)

    for nome in ("LICENSE", "NOTICE"):
        origem = RAIZ / nome
        if not origem.is_file():
            raise SystemExit(
                "PAREI: falta o %s na raiz do projeto.\n"
                "A Apache-2.0 exige preservar o aviso de copyright e o NOTICE.\n"
                "Sem ele o pacote nao pode ser distribuido." % nome)
        shutil.copy2(str(origem), str(b / nome))
        log("  %s  (exigido pela Apache-2.0)" % nome)


_PASTAS_DE_MODELO = ("nv_segment_ct", "cads_open", "hnlnl",
                     "nninteractive", "moose", "cranio_buti")


def etapa_validar(ctx):
    titulo("6/8 · Validacao (se falhar aqui, NAO empacota)")
    py = ctx["py"]
    script = "; ".join("__import__('%s')" % m for m in IMPORTS_OBRIGATORIOS)
    script += "; print('IMPORTS OK')"
    rodar([py, "-c", script], "validacao de imports")

    pesos = ctx["bundle"] / "ts_weights"
    tam = tamanho_pasta(pesos)
    log("  pesos: %s" % gb(tam))
    if tam < 1.5 * 1073741824:
        raise RuntimeError("pesos com apenas %s — esperado ~2 GB. Rode a etapa 4 de novo." % gb(tam))
    conferir_recorte_no_corpo(pesos)
    conferir_modelos_exigidos(ctx["bundle"])

    env = dict(os.environ, TOTALSEG_WEIGHTS_PATH=str(pesos))
    rodar([py, "-m", "totalsegmentator.bin.TotalSegmentator", "--help"],
          "TotalSegmentator --help", env=env)

    conviver = ("import nnunetv2, totalsegmentator; "
                "from nnunetv2.inference.predict_from_raw_data import "
                "nnUNetPredictor; "
                "from nnunetv2.utilities.file_path_utilities import "
                "get_output_folder; "
                "print('nnunetv2', getattr(nnunetv2, '__version__', '?')); "
                "print('CONVIVEM OK')")
    rodar([py, "-c", conviver], "TotalSegmentator e nnunetv2 no mesmo Python")

    cuda_script = ("import torch; print('torch', torch.__version__); "
                   "print('cuda_compilada', torch.version.cuda); "
                   "print('cuda_disponivel', torch.cuda.is_available())")
    rodar([py, "-c", cuda_script], "checagem do torch")
    log("  ATENCAO: 'cuda_disponivel False' aqui e ESPERADO se esta maquina nao")
    log("  tem placa NVIDIA. O que importa e 'cuda_compilada' bater com o driver")
    log("  da estacao de destino (rode nvidia-smi la).")
    log("  tamanho total do bundle montado: %s" % gb(tamanho_pasta(ctx["bundle"])))


_NOMES_SUSPEITOS = ("chave", "key", "token", "secret", "senha", "password",
                    "credential", "credencial", ".pem", ".pfx", "id_rsa")

_CONTEUDO_SUSPEITO = (
    (re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}"), "chave da NVIDIA"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "chave da OpenAI"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "token do GitHub"),
    (re.compile(r"\baca_[A-Za-z0-9_\-]{8,}"), "licenca academica"),
    (re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "chave da AWS"),
    (re.compile(r"\bAIza[A-Za-z0-9_\-]{30,}"), "chave do Google"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "chave privada PEM"),
)

_FORA_DA_VARREDURA = ("site-packages", "python\\lib", "python/lib",
                      "ts_weights", "__pycache__", ".git")


def parece_credencial(caminho, teto_bytes=64 * 1024):
    nome = os.path.basename(caminho)
    if any(s in nome.lower() for s in _NOMES_SUSPEITOS):
        return "nome suspeito"
    try:
        if os.path.getsize(caminho) > teto_bytes:
            return ""
        with open(caminho, "rb") as f:
            bruto = f.read()
    except OSError:
        return ""
    if b"\x00" in bruto:
        return ""
    txt = bruto.decode("utf-8", "ignore")
    for padrao, rotulo in _CONTEUDO_SUSPEITO:
        achado = padrao.search(txt)
        if achado:
            return "%s (%s...)" % (rotulo, achado.group(0)[:12])
    return ""


def achar_credenciais(raiz, teto_bytes=64 * 1024):
    fora = []
    for base, dirs, arqs in os.walk(str(raiz)):
        baixo = base.lower()
        if any(x in baixo for x in _FORA_DA_VARREDURA):
            dirs[:] = []
            continue
        for nome in arqs:
            caminho = os.path.join(base, nome)
            motivo = parece_credencial(caminho, teto_bytes)
            if motivo:
                fora.append("%s  (%s)" % (os.path.relpath(caminho, str(raiz)), motivo))
    return sorted(fora)


def _escrever_manifesto(ctx, pasta=None):
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import artefatos
    except Exception as e:
        log("  AVISO: nao consegui importar artefatos.py (%s) — manifesto sai"
            " sem as somas conhecidas" % e)
        artefatos = None

    linhas = []
    linhas.append("MANIFESTO DO PACOTE")
    linhas.append("=" * 78)
    linhas.append("")
    linhas.append("Este arquivo responde: QUAL VERSAO DE CADA COMPONENTE ESTA")
    linhas.append("INSTALADA NESTA ESTACAO. Guarde-o junto da documentacao do")
    linhas.append("servico -- ele atende ao registro de validacao exigido pela")
    linhas.append("RDC ANVISA 657/2022, cuja retencao e de DEZ ANOS apos o")
    linhas.append("descarte do software.")
    linhas.append("")
    linhas.append("Projeto ....: %s" % ctx["projeto"])
    linhas.append("Versao .....: %s" % ctx["versao"])
    linhas.append("Preparado em: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    linhas.append("Maquina ....: %s" % os.environ.get("COMPUTERNAME", "?"))
    linhas.append("Usuario ....: %s" % os.environ.get("USERNAME", "?"))
    linhas.append("Runtime ....: Python %s embeddable" % PY_VERSAO)
    linhas.append("Aceleracao .: %s" % ("CPU" if ctx["so_cpu"] else ctx["cuda"]))
    linhas.append("")

    if artefatos:
        linhas.append("-" * 78)
        linhas.append("VERSOES FIXADAS")
        linhas.append("-" * 78)
        linhas.append("")
        for k in sorted(artefatos.VERSOES):
            linhas.append("  %-20s %s" % (k, artefatos.VERSOES[k]))
        linhas.append("")
        linhas.append("  Versao fixada, nunca 'a mais recente'. A tabela acima")
        linhas.append("  e a fonte: ela sai de build/artefatos.py, que e o mesmo")
        linhas.append("  arquivo que o instalador confere por SHA-256.")
        linhas.append("")
        linhas.append("-" * 78)
        linhas.append("LICENCAS")
        linhas.append("-" * 78)
        linhas.append("")
        for lic in artefatos.LICENCAS:
            marca = "  [RESTRITIVA] " if lic["restritiva"] else "  [permissiva] "
            linhas.append(marca + lic["componente"] + "  " + lic["licenca"])
            linhas.append("        origem: " + lic["origem"])
        linhas.append("")

    linhas.append("-" * 78)
    linhas.append("ARQUIVOS, COM SOMA DE VERIFICACAO")
    linhas.append("-" * 78)
    linhas.append("")
    linhas.append("%-70s  %-18s  %13s  %s"
                  % ("arquivo", "componente", "bytes", "sha256"))
    linhas.append("")
    achados = ausentes = 0
    _enx = _ler_recibo_do_enxugar(ctx["destino"])
    if artefatos:
        base = ctx["bundle"]
        for chave in sorted(artefatos.ARTEFATOS):
            if chave.startswith("cache/"):
                caminho = ctx["cache"] / chave.split("/", 1)[1]
            elif chave.split("/", 1)[0] in _PASTAS_DE_MODELO:
                caminho = base / "modelos" / chave.split("/", 1)[0] / chave.split("/", 1)[1]
            else:
                caminho = base / "ts_weights" / chave.split("/", 1)[1]
            if not os.path.isfile(str(caminho)):
                ausentes += 1
                opc = artefatos.ARTEFATOS[chave].get("opcional")
                linhas.append("%-70s  %s" % (chave,
                              "AUSENTE (opcional, recusado)" if opc else "AUSENTE"))
                continue
            achados += 1
            _rel = chave.split("/", 1)[1] if chave.startswith("ts/") else ""
            if _rel in _enx:
                linhas.append(_linha_do_enxuto(artefatos, chave, caminho,
                                               _enx[_rel]))
            else:
                linhas.append(artefatos.linha_manifesto(chave, str(caminho)))
    linhas.append("")
    linhas.append("  %d arquivo(s) presente(s), %d ausente(s)." % (achados, ausentes))
    linhas.append("")
    linhas.append("  As somas acima foram COMPUTADAS DESTES ARQUIVOS, agora,")
    linhas.append("  e cada linha diz se ela confere com a tabela. Arquivo sem")
    linhas.append("  soma na tabela aparece como NAO CONFERIDO -- ele existe,")
    linhas.append("  e ninguem provou que e o que devia ser.")
    linhas.append("")
    linhas.append("  PESOS DO TOTALSEGMENTATOR: o preparador os baixa ele")
    linhas.append("  mesmo (as URLs saem da tabela da propria")
    linhas.append("  biblioteca) e confere cada zip ANTES de extrair:")
    linhas.append("  tamanho exato publicado pelo GitHub, SHA-256 quando o")
    linhas.append("  GitHub publica um (nem todos tem), e o CRC de cada")
    linhas.append("  membro do zip. A tabela acima (checkpoints) cobre so")
    linhas.append("  parte deles; a conferencia no download esta abaixo.")
    linhas.append("")
    _reg = _ler_registro_dos_pesos(ctx["destino"])
    if _reg:
        linhas.append("  ZIPS DE PESO CONFERIDOS NO DOWNLOAD (%d):" % len(_reg))
        for _z in sorted(_reg):
            _v = _reg[_z] or {}
            linhas.append("  %s" % _z)
            linhas.append("      bytes %s   baixado em %s"
                          % (_v.get("bytes", "?"), _v.get("quando", "?")))
            linhas.append("      sha256     %s" % (_v.get("sha256") or "?"))
            linhas.append("      %s" % (_v.get("veredito") or "?"))
        try:
            _no_disco = sorted(d for d in os.listdir(str(ctx["bundle"]
                                                         / "ts_weights"))
                               if re.match(r"Dataset\d+_", d))
        except OSError:
            _no_disco = []
        _sem = [d for d in _no_disco if (d + ".zip") not in _reg]
        if _sem:
            linhas.append("")
            linhas.append("  NO PACOTE SEM CONFERENCIA NESTA MONTAGEM (%d) --"
                          % len(_sem))
            linhas.append("  ja estavam no disco antes do recibo existir:")
            for d in _sem:
                linhas.append("    %s" % d)
    else:
        linhas.append("  (nenhum zip de peso passou pela conferencia NESTA")
        linhas.append("   montagem: os pesos ja estavam no disco, de um")
        linhas.append("   preparo anterior. Eles NAO foram conferidos aqui.)")
    linhas.append("")
    linhas.append("  CHECKPOINTS SEM O ESTADO DO OTIMIZADOR (%d):" % len(_enx))
    linhas.append("  O estado do otimizador (optimizer_state; no nnU-Net v1,")
    linhas.append("  optimizer_state_dict) so serve para continuar o treino.")
    linhas.append("  O preparo o tira de cada checkpoint do nnU-Net (os do")
    linhas.append("  TotalSegmentator e os que o registro de modelos declara)")
    linhas.append("  logo depois do download conferido, regrava o")
    linhas.append("  arquivo com um aviso de modificacao dentro dele e confere")
    linhas.append("  que os pesos da rede e as demais entradas sao identicos")
    linhas.append("  byte a byte ao original. Peso que ja estava no disco nao")
    linhas.append("  e reescrito.")
    for _r in sorted(_enx):
        _v = _enx[_r] or {}
        linhas.append("  %s" % _r)
        linhas.append("      bytes %s -> %s   em %s"
                      % (_v.get("bytes_antes", "?"), _v.get("bytes_depois", "?"),
                         _v.get("quando", "?")))
        linhas.append("      sha256 antes  %s" % (_v.get("sha256_antes") or "?"))
        linhas.append("      sha256 depois %s" % (_v.get("sha256_depois") or "?"))
        linhas.append("      rede: %s tensores identicos byte a byte (digest %s)"
                      % (_v.get("tensores", "?"), _v.get("digest_rede") or "?"))
    linhas.append("")
    linhas.append("  Os do NV-Segment-CT conferem o sha256 NO DOWNLOAD")
    linhas.append("  (`radai_models.baixar`, campo `sha256` do registro), e")
    linhas.append("  nao so o tamanho em bytes: tamanho pega truncamento, nao")
    linhas.append("  troca.")
    linhas.append("")

    alvo = Path(str(pasta or ctx["destino"])) / "MANIFESTO.txt"
    alvo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    log("  MANIFESTO.txt: %d arquivo(s) listado(s)" % achados)
    return alvo


def _linha_do_enxuto(artefatos, chave, caminho, reg):
    a = artefatos.ARTEFATOS.get(chave) or {}
    esperado = a.get("sha256") or ""
    antes = reg.get("sha256_antes") or ""
    veredito = ""
    try:
        agora = sha256_de(caminho)
    except OSError as e:
        agora, veredito = "", "NAO FOI POSSIVEL SOMAR (%s)" % str(e)[:60]
    if not agora:
        veredito = veredito or "NAO FOI POSSIVEL SOMAR"
    elif agora != reg.get("sha256_depois"):
        veredito = ("NAO CONFERE com o recibo do preparo: o arquivo mudou "
                    "depois de enxugado")
    elif esperado and antes == esperado:
        veredito = ("sem o estado do otimizador: a soma de ANTES confere com "
                    "a tabela, e os pesos da rede sao identicos byte a byte")
    elif esperado:
        veredito = ("sem o estado do otimizador: a soma de ANTES NAO CONFERE "
                    "com a tabela, que esperava %s" % esperado)
    else:
        veredito = "sem o estado do otimizador; SEM SOMA NA TABELA"
    return ("  %s\n      componente %-20s bytes %s (antes %s)\n"
            "      sha256     %s\n      sha256 antes %s\n      %s"
            % (chave, a.get("componente", "?"), reg.get("bytes_depois", "?"),
               reg.get("bytes_antes", "?"), agora or "?", antes or "?",
               veredito))


def _avulsos_do_pacote(ctx):
    inst = RAIZ / "installer"
    leia = ctx["destino"] / "LEIA-ME.txt"
    leia.write_text(
        LEIA_ME % {"projeto": ctx["projeto"], "versao": ctx["versao"],
                   "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
                   "cuda": "CPU" if ctx["so_cpu"] else ctx["cuda"]},
        encoding="utf-8")

    texto = _texto_entrega(ctx["projeto"], ctx["versao"],
                           ctx.get("produto") or ctx["projeto"])
    try:
        import carimbo as _car
        _aviso_sujo = _car.aviso_de_arvore_suja(texto)
    except Exception:
        _aviso_sujo = ""
    if _aviso_sujo:
        log("  " + _aviso_sujo)
    ent = ctx["destino"] / "entrega.txt"
    ent.write_text(texto, encoding="utf-8")

    (ctx["bundle"] / "entrega.txt").write_text(texto, encoding="utf-8")

    manifesto = _escrever_manifesto(ctx)

    aceite = None
    if ctx.get("preparo"):
        cand = Path(ctx["preparo"]) / "LICENCAS_ACEITAS.txt"
        if cand.is_file():
            aceite = cand

    prep = RAIZ / "packager"
    opcionais = [("languages.ps1", prep / "languages.ps1"),
                 ("languages.json", prep / "languages.json")]

    idioma = str(ctx.get("idioma") or "").strip()
    if not idioma:
        c = Path(ctx["preparo"]) / "idioma.txt" if ctx.get("preparo") else None
        if c is not None and c.is_file():
            try:
                idioma = c.read_text(encoding="utf-8-sig").strip()
            except OSError:
                idioma = ""
    if not idioma:
        idioma = "pt-BR"

    try:
        import json as _json
        _d = _json.loads((prep / "languages.json").read_text(encoding="utf-8"))
        _cods = list(_d.get("codigos") or [])
        if _cods and idioma not in _cods:
            raise SystemExit(
                "idioma %r nao esta no dicionario. Os que existem: %s"
                % (idioma, ", ".join(_cods)))
    except SystemExit:
        raise
    except Exception:
        pass

    alvo_id = Path(str(ctx.get("destino") or ctx["bundle"].parent)) / "idioma.txt"
    try:
        alvo_id.write_text(idioma, encoding="utf-8")
        opcionais.append(("idioma.txt", alvo_id))
        (ctx["bundle"] / "idioma.txt").write_text(idioma, encoding="utf-8")
        log("idioma do pacote: %s (o instalador E o painel abrem nele)" % idioma)
    except OSError as e:
        log("nao consegui gravar o idioma.txt (%s) — o pacote sai sem ele, e "
            "o instalador cai no portugues" % e)

    pares = [("INSTALL.cmd", inst / "INSTALL.cmd"),
             ("INSTALL.ps1", inst / "INSTALL.ps1"),
             ("entrega.txt", ent),
             ("MANIFESTO.txt", manifesto),
             ("LEIA-ME.txt", leia)]
    if aceite is not None:
        pares.append(("LICENCAS_ACEITAS.txt", aceite))
    faltando = [r for r, o in pares if not o.exists()]
    if faltando:
        raise SystemExit(
            "PAREI: faltam arquivos do contrato de instalacao: %s\n"
            "Sem eles o .zip nao e instalavel." % ", ".join(faltando))
    pares.extend([(r, o) for r, o in opcionais if o.exists()])
    return pares


def etapa_empacotar(ctx):
    projeto, versao = ctx["projeto"], ctx["versao"]
    produto = ctx.get("produto") or projeto
    titulo("7/8 · Empacotando %s_BUNDLE_v%s.zip (SEM compressao)"
           % (produto, versao))
    alvo = ctx["saida"] / ("%s_BUNDLE_v%s.zip" % (produto, versao))
    if alvo.exists():
        log("  removendo .zip anterior")
        alvo.unlink()
    t0 = time.time()
    n = [0]

    achados = achar_credenciais(ctx["bundle"])
    if achados:
        for c in achados:
            log("  CREDENCIAL: %s" % c)
        raise SystemExit(
            "PAREI antes de empacotar: ha credencial na montagem (acima).\n"
            "Credencial em pendrive nao se recolhe. Tire os arquivos e rode\n"
            "esta etapa de novo.")
    log("  varredura de credenciais: limpa")

    conferir_recorte_no_corpo(ctx["bundle"] / "ts_weights")

    try:
        levadas, achados = escrever_recibo_medido(ctx["bundle"])
        log("  recibo: %d task(s) com peso completo no pacote" % len(levadas))
        log("  recibo: %d modelo(s) com peso no pacote" % len(achados))
        _faltam = [t for t in TASKS if t not in set(levadas)]
        if _faltam:
            log("  ATENCAO: o pacote completo saiu SEM peso completo de: %s"
                % ", ".join(_faltam))
    except Exception as e:
        log("  nao consegui medir o que o pacote leva (%s)" % e)

    avulsos = _avulsos_do_pacote(ctx)
    for rotulo, origem in avulsos:
        if origem is None:
            continue
        motivo = parece_credencial(str(origem))
        if motivo:
            raise SystemExit(
                "PAREI antes de empacotar: %s parece credencial (%s).\n"
                "Credencial em pendrive nao se recolhe." % (origem, motivo))

    ctx["saida"].mkdir(parents=True, exist_ok=True)
    total = sum(1 for _ in ctx["bundle"].rglob("*") if _.is_file())
    log("  %d arquivos na montagem" % total)

    with zipfile.ZipFile(str(alvo), "w", compression=zipfile.ZIP_STORED,
                         allowZip64=True) as z:
        for rotulo, origem in avulsos:
            if origem is None:
                continue
            z.write(str(origem), rotulo)
            log("  + %s" % rotulo)
        raiz = ctx["bundle"]
        for p in sorted(raiz.rglob("*")):
            if not p.is_file():
                continue
            z.write(str(p), "%s/%s" % (projeto, p.relative_to(raiz).as_posix()))
            n[0] += 1
            if n[0] % 2000 == 0:
                log("    ... %d de %d arquivos" % (n[0], total))

    tam = alvo.stat().st_size
    log("  %s  (%s, %d arquivos, %ds)" % (alvo.name, gb(tam), n[0], int(time.time() - t0)))
    ctx["pacote"] = alvo


LEIA_ME = """================================================================
 %(projeto)s  v%(versao)s  -  Radioterapia.AI
================================================================
Este .zip e autocontido. A estacao NAO precisa de internet, nem de
administrador, nem de Python instalado: o runtime vem aqui dentro.

 1. Copie o .zip para o disco LOCAL da estacao (C:\\...).
    Instalar direto do pendrive ou da rede e muito lento.

 2. Botao direito no .zip  ->  "Extrair tudo..."
    EXTRAIA ANTES DE INSTALAR. Dar dois cliques no INSTALL.cmd de
    dentro do zip nao funciona: o Windows extrai so aquele arquivo
    para uma pasta temporaria e o programa nao vem junto.

 3. Dois cliques em  INSTALL.cmd
    Instala em  C:\\RADIOTERAPIA_AI\\%(projeto)s
    Se ja houver uma versao instalada, ele PRESERVA o que voce
    configurou: a pasta das tomografias, o acervo da calibracao e
    o aceite. Cria o atalho e registra a versao em
    C:\\RADIOTERAPIA_AI\\_instalados.json.

 4. Abra a suite pelo atalho, e em Configuracoes ->
    Diagnosticos e Registros, clique em Diagnosticar: tem de dar
    0 faltando.

 5. Abra pelo atalho "Radioterapia.ai Local Suite" na area de
    trabalho. O painel sobe em  http://127.0.0.1:8777/  (o motor
    roda sem janela; para fechar, FECHAR APP no painel).
    Na primeira vez ele pede o aceite e, logo depois, a pasta
    favorita, que e opcional. A pasta que o turno varre se escolhe
    no ContourLab, em Rodar agora, Incluir Overnight Run: sem ela o
    vigia nao varre nada. Os aneis saem no padrao Eclipse / Monaco;
    para Xio / Focal, Configuracoes, Geral.

================================================================
 CONTEUDO DO .ZIP
================================================================
 INSTALL.cmd        o duplo clique
 INSTALL.ps1        o trabalho do instalador
 entrega.txt         projeto e versao
 LEIA-ME.txt         este arquivo
 %(projeto)s\\   o programa: runtime Python, bibliotecas,
                     pesos dos modelos e a aplicacao

 Montado em %(quando)s  ·  torch %(cuda)s

================================================================
 SEGURANCA
================================================================
 As estruturas entram no TPS como SUGESTAO NAO APROVADA, com o
 sufixo _ai no nome. Revisao e aprovacao continuam sendo ato
 medico, dentro do TPS. Nada e aprovado automaticamente.

 Nenhuma imagem e enviada para fora: os modelos rodam nesta
 maquina, a partir dos pesos que vieram neste pacote.
================================================================
"""


def etapa_distribuir(ctx):
    titulo("8/8 · Conferindo o pacote")
    pacote = ctx.get("pacote")
    if pacote is None:
        pacote = ctx["saida"] / ("%s_BUNDLE_v%s.zip"
                                 % (ctx.get("produto") or ctx["projeto"],
                                    ctx["versao"]))
    if not pacote.exists():
        raise SystemExit("PAREI: nao achei %s.\n"
                         "       Rode a etapa 7 (empacotar) antes." % pacote)

    projeto = ctx["projeto"]
    with zipfile.ZipFile(str(pacote)) as z:
        nomes = z.namelist()
        ruins = z.testzip()
        if ruins is not None:
            raise SystemExit("PAREI: o .zip esta corrompido em %s" % ruins)

        faltando = [n for n in ("INSTALL.cmd", "INSTALL.ps1", "entrega.txt",
                                "LEIA-ME.txt") if n not in nomes]
        if faltando:
            raise SystemExit("PAREI: faltam no .zip: %s" % ", ".join(faltando))
        log("  contrato de instalacao: os 4 arquivos estao la")

        essenciais = ["python/python.exe", "radai_watcher.py", "engine.py",
                      "radai_geom.py",
                      "RADIOTERAPIA_AI_LOCAL_SUITE.cmd",
                      "launchers/start_watcher.cmd",
                      "launchers/open_browser.cmd",
                      "maintenance/UNINSTALL.cmd"]
        faltando = [e for e in essenciais
                    if ("%s/%s" % (projeto, e)) not in nomes]
        if faltando:
            raise SystemExit("PAREI: faltam no .zip: %s" % ", ".join(faltando))
        if not any(n.startswith("%s/ts_weights/" % projeto) for n in nomes):
            raise SystemExit("PAREI: o .zip nao tem ts_weights — sem pesos nao segmenta.")
        log("  programa: runtime, modulos e pesos presentes")

        suspeitos = []
        for nome in nomes:
            base = nome.rsplit("/", 1)[-1]
            if any(s in base.lower() for s in _NOMES_SUSPEITOS):
                if any(x in nome.lower() for x in _FORA_DA_VARREDURA):
                    continue
                suspeitos.append("%s  (nome suspeito)" % nome)
        if suspeitos:
            for s in suspeitos:
                log("  CREDENCIAL: %s" % s)
            raise SystemExit(
                "PAREI: ha arquivo com cara de credencial DENTRO do .zip.\n"
                "Credencial em pendrive nao se recolhe.")
        log("  varredura do .zip: nenhuma credencial")

    tam = pacote.stat().st_size
    log("")
    log("  PRONTO. Um arquivo so, para levar no pendrive:")
    log("  %s" % para_o_log(pacote, ctx))
    log("     %s  (%s, %d bytes)" % (pacote.name, gb(tam), tam))
    log("")
    log("  Na estacao: extrair o .zip e dar dois cliques em INSTALL.cmd.")


ETAPAS = [("runtime", etapa_runtime), ("pip", etapa_pip), ("libs", etapa_libs),
          ("pesos", etapa_pesos), ("app", etapa_app), ("validar", etapa_validar),
          ("empacotar", etapa_empacotar), ("distribuir", etapa_distribuir)]


OFICINA_NO_LUGAR = "_instalacao"
MARCA_DO_MOTOR = "_motor_comecou.txt"
NOMES_DO_PREPARO_NA_PASTA = ("LICENCAS_ACEITAS.txt", "idioma.txt",
                             "preparar_log.txt", OFICINA_NO_LUGAR)


PREPARO_ANTIGO = "preparo"


def marca_de_instalacao(pasta):
    p = Path(str(pasta))
    return (p / "radai_watcher.py").is_file() and (p / "entrega.txt").is_file()


def marca_de_instalacao_antiga(pasta):
    # GUARDA: a mesma dupla de MarcaDeInstalacaoAntiga no prepare.ps1; so o --instalar inteiro a aceita.
    p = Path(str(pasta))
    return marca_de_instalacao(p) or ((p / "radai_watcher.py").is_file()
                                      and (p / "python" / "python.exe").is_file())


def sobra_do_preparo_antigo(pasta):
    p = Path(str(pasta))
    if p.name.lower() != PREPARO_ANTIGO or not p.is_dir():
        return False
    if (p / "_montagem").is_dir() or (p / "_instalados.json").is_file():
        return True
    try:
        return any(marca_de_instalacao(s) for s in p.iterdir() if s.is_dir())
    except OSError:
        return False


def conferir_pasta_de_instalacao(destino):
    try:
        alvo = Path(str(destino)).resolve()
    except Exception as e:
        return u"o caminho nao se resolve (%s)" % e
    if not str(destino).strip():
        return u"nenhuma pasta foi dada"
    if alvo == Path(alvo.anchor):
        return u"%s e a raiz de um disco: escolha uma pasta dentro dele" % alvo
    try:
        _ligar_caminho()
        import radai_archive
        sinc, motivo = radai_archive.em_pasta_sincronizada(str(alvo))
        if sinc:
            return (u"%s sincroniza com a nuvem (%s): o programa e os pesos "
                    u"nao podem morar ali" % (alvo, motivo))
    except Exception:
        pass
    if not alvo.exists():
        return u""
    if not alvo.is_dir():
        return u"%s existe e nao e uma pasta" % alvo
    # GUARDA: so a oficina que o MOTOR marcou prova tentativa nossa; a vazia o preparador cria antes de chamar o motor.
    if marca_de_instalacao_antiga(alvo) or (alvo / OFICINA_NO_LUGAR / MARCA_DO_MOTOR).is_file():
        return u""
    try:
        estranhos = sorted(n for n in os.listdir(str(alvo))
                           if n not in NOMES_DO_PREPARO_NA_PASTA
                           and not sobra_do_preparo_antigo(alvo / n))
    except OSError as e:
        return u"nao consegui listar %s (%s)" % (alvo, e)
    if estranhos:
        return (u"%s ja tem %d item(ns) que nao sao desta instalacao (%s). "
                u"Escolha uma pasta vazia, nova, ou a pasta de uma "
                u"instalacao existente." % (alvo, len(estranhos),
                                            u", ".join(estranhos[:4])))
    return u""


def etapa_finalizar_no_lugar(ctx):
    titulo("7/8 · Finalizando na pasta final (sem .zip e sem extracao)")
    b = ctx["bundle"]
    conferir_recorte_no_corpo(b / "ts_weights")
    conferir_modelos_exigidos(b)
    try:
        levadas, achados = escrever_recibo_medido(b)
        log("  recibo: %d task(s) com peso completo" % len(levadas))
        log("  recibo: %d modelo(s) com peso" % len(achados))
    except Exception as e:
        log("  nao consegui medir o que foi instalado (%s)" % e)
    gravar_impressao(b, ctx["versao"])
    texto = _texto_entrega(ctx["projeto"], ctx["versao"],
                           ctx.get("produto") or ctx["projeto"])
    (b / "entrega.txt").write_text(texto, encoding="utf-8")
    log("  entrega.txt (v%s)" % ctx["versao"])
    idioma = str(ctx.get("idioma") or "").strip()
    if not idioma:
        try:
            idioma = (b / "idioma.txt").read_text(encoding="utf-8-sig").strip()
        except OSError:
            idioma = u""
    idioma = idioma or u"pt-BR"
    (b / "idioma.txt").write_text(idioma, encoding="utf-8")
    log("  idioma.txt: %s" % idioma)
    _escrever_manifesto(ctx, b)
    _limpar_oficina_no_lugar(ctx)


def _limpar_oficina_no_lugar(ctx):
    cache = ctx.get("cache")
    if cache and Path(str(cache)).is_dir():
        shutil.rmtree(str(cache), ignore_errors=True)
        log("  cache de download apagado")
    req = Path(str(ctx["destino"])) / "requirements-efetivo.txt"
    try:
        req.unlink()
    except OSError:
        pass


def sha256_de(caminho):
    import hashlib
    h = hashlib.sha256()
    with open(str(caminho), "rb") as f:
        for bloco in iter(lambda: f.read(1048576), b""):
            h.update(bloco)
    return h.hexdigest()


def etapas_do_modo(instalar=False):
    g = globals()
    if instalar:
        nomes = (("runtime", "etapa_runtime"), ("pip", "etapa_pip"),
                 ("libs", "etapa_libs"), ("pesos", "etapa_pesos"),
                 ("validar", "etapa_validar"), ("app", "etapa_app"),
                 ("finalizar", "etapa_finalizar_no_lugar"))
    else:
        return list(ETAPAS)
    return [(n, g[f]) for n, f in nomes]


def linhas_do_cabecalho(preparo, oficina_no_log):
    if preparo:
        return ["  (este pacote e' a CARGA: leve-o a estacao junto com o",
                "   instalador SETUP, ou instale-o aqui mesmo)",
                "  pasta de passagem %s   (temporaria: pode apagar depois)"
                % oficina_no_log]
    try:
        _raiz = str(raiz_de_entrega())
    except SystemExit as e:
        _raiz = "(raiz de entrega nao resolvida: %s)" % str(e).splitlines()[0]
    return ["  (ele NAO e entrega: a entrega e o instalador leve, em",
            "        %s, gerado por build\\empacotar_instalador.py)" % _raiz,
            "  oficina em .... %s   (intermediario, gitignorado)"
            % oficina_no_log]


def _bloco_pacote():
    try:
        cam = RAIZ / "packager" / "catalogo.json"
        return json.loads(cam.read_text(encoding="utf-8")).get("pacote") or {}
    except Exception:
        return {}


def _tamanho_do_pacote_txt():
    p = _bloco_pacote().get("pacote_gib")
    return ("%.0f" % p) if p else "20 (reserva: sem catalogo.json)"


def _disco_para_preparar_gib():
    return float(_bloco_pacote().get("disco_gib") or 42.0)


def main(argv=None):
    global LOG
    ap = argparse.ArgumentParser(description="Configurador do Ambiente Radioterapia.AI")
    ap.add_argument("--destino", default="deploy",
                    help="deploy (o unico; a raiz sai de destino_de_entrega)")
    ap.add_argument("--cuda", default="cu121", help="cu118 | cu121 | cu124 (padrao cu121)")
    ap.add_argument("--so-cpu", action="store_true", help="bundle sem CUDA (teste/maquina sem GPU)")
    ap.add_argument("--etapas", default="", help="ex.: 4,5,6 (padrao: todas)")
    ap.add_argument("--idioma", default="",
                    help="pt-BR (padrao) | en | es | de | fr | it | pl | ja | "
                         "zh | ar | ko | bn")
    ap.add_argument("--preparo", default="",
                    help="pasta de trabalho do preparador (modo usuario final)")
    ap.add_argument("--tasks", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--modelos", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--instalar", default="",
                    help="pasta FINAL do programa: baixa e monta direto nela, "
                         "sem montagem, sem .zip e sem extracao")
    a = ap.parse_args(argv)
    if a.instalar and a.preparo:
        raise SystemExit("PAREI: --instalar e --preparo sao modos diferentes: "
                         "um instala na pasta final, o outro monta um pacote "
                         "para levar. Escolha um.")
    if a.tasks is not None or a.modelos is not None:
        raise SystemExit(
            "PAREI: --tasks e --modelos nao sao mais opcoes do preparo.\n"
            "O pacote e' sempre o COMPLETO (pipeline unico): todas as tasks\n"
            "do catalogo e todos os modelos de comparacao, ~%s GB.\n"
            "Tire as duas opcoes e rode de novo." % _tamanho_do_pacote_txt())

    projeto, versao, produto = ler_entrega(RAIZ)
    no_lugar = None
    if a.instalar:
        no_lugar = Path(a.instalar).resolve()
        motivo = conferir_pasta_de_instalacao(no_lugar)
        if motivo:
            raise SystemExit("PAREI antes de baixar: %s" % motivo)
        oficina = no_lugar / OFICINA_NO_LUGAR
        saida = oficina
        aceite = no_lugar / "LICENCAS_ACEITAS.txt"
        _exigir_aceite_completo(aceite)
        if not aceite.is_file():
            raise SystemExit(
                "Nao achei o LICENCAS_ACEITAS.txt em %s.\n"
                "A instalacao direta exige o aceite gravado ANTES do download. "
                "Rode pelo instalador (START_HERE)." % no_lugar)
        oficina.mkdir(parents=True, exist_ok=True)
        (oficina / MARCA_DO_MOTOR).write_text(
            u"instalacao direta iniciada em %s\n" % datetime.now().strftime("%d/%m/%Y %H:%M"),
            encoding="utf-8")
    elif a.preparo:
        base = Path(a.preparo).resolve()
        oficina = base / "_montagem"
        saida = base / ("%s_v%s" % (projeto, versao))
        aceite = base / "LICENCAS_ACEITAS.txt"
        _exigir_aceite_completo(aceite)
        if not aceite.is_file():
            raise SystemExit(
                "Nao achei o LICENCAS_ACEITAS.txt em %s.\n"
                "O modo --preparo exige o aceite gravado ANTES do download. "
                "Rode pelo PREPARAR_AUTO_CONTORNO.cmd." % base)
    else:
        oficina = RAIZ / "_montagem"
        saida = oficina / ("%s_v%s" % (projeto, versao))

    oficina.mkdir(parents=True, exist_ok=True)
    LOG = open(str(oficina / "configurar_ambiente_log.txt"), "a", encoding="utf-8", errors="replace")

    ctx = {"raiz": RAIZ, "destino": oficina,
           "bundle": no_lugar if no_lugar else oficina / projeto,
           "cache": oficina / "cache",
           "saida": saida,
           "projeto": projeto, "versao": versao, "produto": produto,
           "cuda": a.cuda, "so_cpu": a.so_cpu,
           "idioma": a.idioma,
           "preparo": str(no_lugar) if no_lugar else a.preparo,
           "instalar": str(no_lugar) if no_lugar else ""}
    ctx["bundle"].mkdir(parents=True, exist_ok=True)
    ctx["cache"].mkdir(parents=True, exist_ok=True)
    ctx["saida"].mkdir(parents=True, exist_ok=True)
    ctx["py"] = ctx["bundle"] / "python" / "python.exe"

    try:
        _sel = ctx["bundle"] / "plugins.txt"
        _linhas = [
            "# O que este pacote levou. Gerado pelo preparo; nao editar.",
            "#",
            "# O pacote e' sempre o COMPLETO (pipeline unico): todas",
            "# as tasks do catalogo e todos os modelos de",
            "# comparacao. NUCLEO e o que gera o RadAI_Full; o resto e'",
            "# material de comparacao. As linhas LEVADO, abaixo, sao MEDIDAS",
            "# no pacote -- se diferirem de TASKS, o pacote saiu incompleto.",
            "",
            "VERSAO=%s" % versao,
            "NUCLEO=%s" % ",".join(NUCLEO),
            "TASKS=%s" % ",".join(TASKS),
            "MODELOS=(todos)",
        ]
        _sel.write_text("\n".join(_linhas) + "\n", encoding="utf-8")
    except Exception:
        pass

    escolhidas = set(int(x) for x in a.etapas.replace(" ", "").split(",") if x) if a.etapas else None

    titulo("Configurador do Ambiente · Radioterapia.AI")
    log("  projeto ....... %s v%s   (entrega.txt)" % (projeto, versao))
    if no_lugar:
        log("  modo ......... instalacao DIRETA na pasta final")
        log("  pasta final .. <pasta de trabalho>   (nada de .zip nem de "
            "extracao)")
    else:
        log("  o pacote sai em %s" % para_o_log(saida, ctx))
        for _l in linhas_do_cabecalho(bool(a.preparo), para_o_log(oficina, ctx)):
            log(_l)
    log("  runtime alvo .. Python %s embeddable (o das estacoes)" % PY_VERSAO)
    log("  torch ......... %s" % ("CPU" if a.so_cpu else a.cuda))
    log("  log ........... %s"
        % para_o_log(oficina / "configurar_ambiente_log.txt", ctx))
    livre = shutil.disk_usage(str(oficina)).free
    log("  espaco livre .. %s" % gb(livre))
    _disco = _disco_para_preparar_gib()
    if no_lugar:
        _disco = float(_bloco_pacote().get("pacote_gib") or 20.0) + 2.0
    if no_lugar and livre < _disco * 1073741824 and not marca_de_instalacao_antiga(no_lugar):
        log("  AVISO: menos de %.0f GB livres para o programa completo."
            % _disco)
    elif not no_lugar and livre < _disco * 1073741824:
        log("  AVISO: menos de %.0f GB livres. A montagem e o .zip do pacote "
            "completo (~%s GB cada) convivem nesta pasta."
            % (_disco, _tamanho_do_pacote_txt()))

    t0 = time.time()
    for i, (nome, fn) in enumerate(etapas_do_modo(bool(no_lugar)), start=1):
        if escolhidas and i not in escolhidas:
            continue
        try:
            fn(ctx)
        except SemRede as e:
            log("")
            log("-" * 70)
            log(" %s (%d - %s)" % (getattr(e, "cabecalho", SemRede.cabecalho),
                                   i, nome))
            log("")
            log(" %s" % e)
            log("-" * 70)
            return int(getattr(e, "codigo", 2))
        except Exception as e:
            log("")
            log("!" * 70)
            log(" ETAPA %d (%s) FALHOU: %s" % (i, nome, e))
            log(" Corrija e rode de novo com:  --etapas %d" % i)
            log(" (as etapas anteriores nao serao refeitas)")
            log("!" * 70)
            return 1
    log("")
    log("TUDO PRONTO em %d min." % int((time.time() - t0) / 60))
    return 0


if __name__ == "__main__":
    sys.exit(main())
