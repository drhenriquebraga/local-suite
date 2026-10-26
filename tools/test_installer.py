# -*- coding: utf-8 -*-
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
_cleanup.adotar_prefixo('radai_ac_instalado')
_cleanup.adotar_prefixo('radai_inst_')


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
sys.path.insert(0, os.path.join(RAIZ, "build"))

import tempfile as _tempfile
import _componentes
os.environ["RADAI_CALIB_DIR"] = _tempfile.mkdtemp(prefix="radai_ac_instalado_")


_RESULTADOS = []
_TEMPS = []
VERBOSO = "-v" in sys.argv


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    if VERBOSO or not ok:
        print("  %-6s %s%s" % ("OK" if ok else "FALHA", nome,
                               ("  [%s]" % detalhe) if detalhe else ""))


def secao(t):
    if VERBOSO:
        print("\n-- %s %s" % (t, "-" * max(0, 58 - len(t))))


def temp(prefixo):
    d = tempfile.mkdtemp(prefix="radai_inst_" + prefixo + "_")
    _TEMPS.append(d)
    return d


ESSENCIAIS = [
    "python/python.exe",
    "radai_watcher.py",
    "engine.py",
    "radai_geom.py",
    "RADIOTERAPIA_AI_LOCAL_SUITE.cmd",
    "launchers/start_watcher.cmd",
    "launchers/open_browser.cmd",
    "maintenance/UNINSTALL.cmd",
    "ts_weights/total/algum_peso.bin",
]


def peso_do_recorte_no_corpo():
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    import radai_tasks
    return "/".join(["ts_weights", radai_tasks.DATASET_DO_BODY_PASTA]
                    + radai_tasks.PESO_DO_BODY.replace("\\", "/").split("/"))


def montar_fantoma(base, projeto="AUTO_CONTORNO"):
    b = os.path.join(base, projeto)
    for rel in ESSENCIAIS + [peso_do_recorte_no_corpo()]:
        p = os.path.join(b, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("fantoma de teste: " + rel + "\n")
    pc = os.path.join(b, "__pycache__")
    os.makedirs(pc, exist_ok=True)
    with open(os.path.join(pc, "modulo_que_nao_existe_mais.pyc"), "wb") as f:
        f.write(b"\x00\x00\x00\x00")
    return b


def empacotar(oficina, saida, projeto="AUTO_CONTORNO", versao="9.9"):
    import configurar_ambiente as ca
    ca.LOG = open(os.path.join(oficina, "log.txt"), "a", encoding="utf-8")
    try:
        ctx = {"raiz": ca.RAIZ, "destino": _P(oficina), "bundle": _P(os.path.join(oficina, projeto)),
               "cache": _P(os.path.join(oficina, "cache")), "saida": _P(saida),
               "projeto": projeto, "versao": versao, "cuda": "cu121", "so_cpu": False}
        ca.etapa_empacotar(ctx)
        ca.etapa_distribuir(ctx)
        return ctx["pacote"]
    finally:
        # GUARDA: log aberto ate o fim do processo prende a pasta temporaria no Windows.
        aberto, ca.LOG = ca.LOG, None
        try:
            aberto.close()
        except Exception:
            pass


def _apagavel(caminho):
    try:
        os.remove(caminho)
        return True
    except OSError:
        return False


def _P(s):
    from pathlib import Path
    return Path(s)


def _porta_de_teste_na_instalacao(raiz_destino):
    for dst in (os.path.join(raiz_destino, "AUTO_CONTORNO"), raiz_destino):
        cfg = os.path.join(dst, "radai_watcher.config")
        if (os.path.isfile(os.path.join(dst, "radai_watcher.py"))
                and not os.path.isfile(cfg)):
            with open(cfg, "w", encoding="utf-8") as f:
                f.write("PORT=%d\n" % _porta_livre())


def instalar(pasta_extraida, raiz_destino, amb=None):
    ps1 = os.path.join(pasta_extraida, "INSTALL.ps1")
    _porta_de_teste_na_instalacao(raiz_destino)
    env = dict(os.environ)
    env["RADAI_RAIZ_INSTALACAO"] = raiz_destino
    env["RADAI_ATALHOS_NA_RAIZ"] = "1"
    env["RADAI_PASTA_PACOTE"] = pasta_extraida
    env["RADAI_LICENCAS_ACEITAS"] = "S"
    env["LOCALAPPDATA"] = (amb or {}).get("LOCALAPPDATA") or temp("inst_ad")
    env.update(amb or {})
    p = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", "Get-Content -LiteralPath '%s' -Raw -Encoding UTF8 | Invoke-Expression" % ps1],
        cwd=pasta_extraida, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def teste_pacote_e_um_arquivo_so():
    secao("pacote: um .zip, com os quatro arquivos do contrato")
    of, sa = temp("of"), temp("sa")
    montar_fantoma(of)
    pacote = empacotar(of, sa)
    checar("o log do empacotamento fica fechado (a pasta temporaria sai no fim)",
           _apagavel(os.path.join(of, "log.txt")))
    if os.name == "nt":
        preso = os.path.join(of, "preso.txt")
        with open(preso, "w") as _f:
            checar("  (isca) arquivo ainda aberto nao se apaga no Windows",
                   not _apagavel(preso))

    checar("o nome e <PRODUTO>_BUNDLE_v<VERSAO>.zip",
           pacote.name == "AUTO_CONTORNO_BUNDLE_v9.9.zip", pacote.name)
    checar("e a VERSAO esta no nome",
           "9.9" in pacote.name,
           "e o que responde: o que exatamente esta naquela estacao")
    soltos = [p.name for p in _P(sa).iterdir()]
    checar("e o unico arquivo na pasta de entrega", soltos == [pacote.name], str(soltos))

    with zipfile.ZipFile(str(pacote)) as z:
        nomes = z.namelist()
        for n in ("INSTALL.cmd", "INSTALL.ps1", "entrega.txt", "LEIA-ME.txt"):
            checar("na raiz do zip: %s" % n, n in nomes)
        for e in ESSENCIAIS:
            checar("o programa veio: %s" % e, ("AUTO_CONTORNO/" + e) in nomes)
        checar("e o recorte no corpo (Dataset300) veio junto",
               ("AUTO_CONTORNO/" + peso_do_recorte_no_corpo()) in nomes)
        ent = z.read("entrega.txt").decode("utf-8")
        checar("entrega.txt tem PROJETO", "PROJETO=AUTO_CONTORNO" in ent)
        checar("entrega.txt tem VERSAO", "VERSAO=9.9" in ent)
        checar("entrega.txt tem DATA carimbada agora", "DATA=" in ent, ent.strip()[-16:])
        checar("nada comprimido (ZIP_STORED)",
               all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist()))


def _chave_falsa():
    return "nv" + "api-" + ("f4nt0m4" * 4)


def _chave_aws_falsa():
    return "AK" + "IA" + "F4NT0M4D3T3ST3XX"


def _pem_falso():
    return "-----" + "BEGIN RSA PRIVATE KEY" + "-----\nMIIE...\n"


def teste_credencial_aborta_a_geracao():
    secao("pacote: credencial na montagem ABORTA")
    of, sa = temp("of2"), temp("sa2")
    b = montar_fantoma(of)
    with open(os.path.join(b, "modelos_chave_nvidia.txt"), "w", encoding="utf-8") as f:
        f.write(_chave_falsa() + "\n")
    erro = ""
    try:
        empacotar(of, sa)
    except SystemExit as e:
        erro = str(e)
    checar("a geracao abortou", "PAREI" in erro, erro[:60])
    checar("e nenhum .zip foi deixado para tras",
           not any(p.suffix == ".zip" for p in _P(sa).iterdir()),
           str([p.name for p in _P(sa).iterdir()]))


def teste_pacote_sem_recorte_no_corpo_nao_sai():
    secao("pacote: sem o recorte no corpo (Dataset300) a geracao ABORTA")
    peso = peso_do_recorte_no_corpo()
    pasta_300 = "/".join(peso.split("/")[:2])
    for rotulo, tirar in (("sem a pasta do Dataset300", pasta_300),
                          ("com a pasta e SEM o peso (download interrompido)",
                           peso)):
        of, sa = temp("of300"), temp("sa300")
        b = montar_fantoma(of)
        alvo = os.path.join(b, tirar.replace("/", os.sep))
        if os.path.isdir(alvo):
            shutil.rmtree(alvo)
        else:
            os.remove(alvo)
        erro = ""
        try:
            empacotar(of, sa)
        except (RuntimeError, SystemExit) as e:
            erro = str(e)
        checar("%s: a geracao abortou" % rotulo,
               "recorte no corpo" in erro, erro[:90] or "(nao abortou)")
        checar("  e nenhum .zip foi deixado para tras",
               not any(p.suffix == ".zip" for p in _P(sa).iterdir()),
               str([p.name for p in _P(sa).iterdir()]))


def teste_trava_separa_mencao_de_segredo():
    secao("trava: citar o prefixo passa; carregar o segredo nao")
    import configurar_ambiente as ca
    d = temp("trava")

    def julgar(nome, conteudo):
        p = os.path.join(d, nome)
        modo = "wb" if isinstance(conteudo, bytes) else "w"
        with open(p, modo, **({} if isinstance(conteudo, bytes) else {"encoding": "utf-8"})) as f:
            f.write(conteudo)
        return ca.parece_credencial(p)

    checar("codigo que valida o prefixo da licenca",
           not julgar("valida.py", 'if not chave.lower().startswith("aca_"):\n'),
           julgar("valida.py", 'if not chave.lower().startswith("aca_"):\n'))
    checar("valor invalido de teste (nvapi-1234)",
           not julgar("teste_algo.py", 'for ruim in ("", "nvapi-1234", "abc"):\n'))
    checar("binario com a sequencia por acaso",
           not julgar("_algo.pyd", b"MZ\x90\x00\x03" + b"\x00" * 200 + b"sk-abc" + b"\x00" * 200))
    checar("documentacao explicando a trava",
           not julgar("LEIA.md", "A trava procura nvapi-, sk- e ghp_ no conteudo.\n"))

    checar("chave da NVIDIA com corpo",
           bool(julgar("qualquer.txt", "API=" + _chave_falsa() + "\n")),
           julgar("qualquer.txt", "API=" + _chave_falsa() + "\n"))
    checar("chave privada PEM", bool(julgar("cert.txt", _pem_falso())))
    checar("chave da AWS",
           bool(julgar("notas.txt", "aws = " + _chave_aws_falsa() + "\n")))
    checar("e o nome sozinho ainda aborta, mesmo com conteudo inocente",
           bool(julgar("chave_nvidia.txt", "isto aqui nem parece uma chave\n")),
           julgar("chave_nvidia.txt", "x"))

    motivo = julgar("vazou.txt", "API=" + _chave_falsa() + "\n")
    checar("o log nao repete a chave inteira", _chave_falsa() not in motivo, motivo)


def teste_o_proprio_repositorio_passa_na_trava():
    secao("trava: nenhum arquivo do repositorio dispara a trava")
    import configurar_ambiente as ca
    achados = []
    for sub in ("app", "tools", "build", "installer"):
        pasta = os.path.join(RAIZ, sub)
        if not os.path.isdir(pasta):
            continue
        for nome in sorted(os.listdir(pasta)):
            p = os.path.join(pasta, nome)
            if not os.path.isfile(p):
                continue
            motivo = ca.parece_credencial(p)
            if motivo:
                achados.append("%s/%s (%s)" % (sub, nome, motivo))
    checar("nenhum arquivo do repositorio parece credencial",
           not achados, " | ".join(achados))


def teste_credencial_renomeada_tambem_aborta():
    secao("pacote: credencial DISFARCADA tambem aborta")
    of, sa = temp("of3"), temp("sa3")
    b = montar_fantoma(of)
    with open(os.path.join(b, "config_extra.txt"), "w", encoding="utf-8") as f:
        f.write("valor = " + _chave_falsa() + "\n")
    erro = ""
    try:
        empacotar(of, sa)
    except SystemExit as e:
        erro = str(e)
    checar("renomear nao engana a trava", "PAREI" in erro, erro[:60])


def _extrair(pacote, destino):
    with zipfile.ZipFile(str(pacote)) as z:
        z.extractall(destino)
    return destino


def _ler_lnk(caminho):
    d = temp("lnk")
    s = os.path.join(d, "l.ps1")
    with open(s, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("param([string]$C)\n"
                "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($C)\n"
                "'ICONE=' + $s.IconLocation\n'ALVO=' + $s.TargetPath\n")
    p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", s, "-C", caminho], capture_output=True,
                       timeout=120)
    r = {}
    for l in p.stdout.decode("cp1252", "replace").splitlines():
        if "=" in l:
            k, v = l.split("=", 1)
            r[k.strip()] = v.strip()
    return r.get("ICONE", ""), r.get("ALVO", "")


def teste_instalacao_nova():
    secao("instalar: estacao limpa")
    of, sa, ex, rz = temp("of4"), temp("sa4"), temp("ex4"), temp("rz4")
    b = montar_fantoma(of)
    fav = _componentes.fonte("app/favicon.ico")
    if os.path.isfile(fav):
        shutil.copy2(fav, os.path.join(b, "favicon.ico"))
    pacote = empacotar(of, sa)
    _extrair(pacote, ex)
    rc, saida = instalar(ex, rz)
    checar("terminou com codigo 0", rc == 0, "rc=%s | %s" % (rc, saida[-160:]))

    lnk = os.path.join(rz, "_atalhos_desktop", "Radioterapia.ai Local Suite.lnk")
    checar("o atalho foi criado na pasta de TESTE, e nao no Desktop real",
           os.path.isfile(lnk), lnk)
    if os.path.isfile(lnk):
        icone, alvo = _ler_lnk(lnk)
        esperado = os.path.join(rz, "AUTO_CONTORNO", "favicon.ico") + ",0"
        checar("o atalho usa o favicon.ico DA PASTA INSTALADA, com o indice",
               icone.lower() == esperado.lower(),
               "%s -- esperava %s" % (icone, esperado))
        checar("  e aponta para o lancador instalado",
               alvo.lower().startswith(os.path.join(rz, "AUTO_CONTORNO").lower()),
               alvo)

    dst = os.path.join(rz, "AUTO_CONTORNO")
    for e in ESSENCIAIS:
        checar("instalado: %s" % e, os.path.exists(os.path.join(dst, e.replace("/", os.sep))))
    checar("o __pycache__ velho foi limpo",
           not os.path.exists(os.path.join(dst, "__pycache__")))

    reg = os.path.join(rz, "_instalados.json")
    checar("_instalados.json foi criado", os.path.exists(reg))
    if os.path.exists(reg):
        with open(reg, "rb") as f:
            bruto = f.read()
        checar("gravado sem BOM", not bruto.startswith(b"\xef\xbb\xbf"), repr(bruto[:4]))
        d = json.loads(bruto.decode("utf-8"))
        checar("a entrada do projeto existe", "AUTO_CONTORNO" in d, str(list(d)))
        if "AUTO_CONTORNO" in d:
            e = d["AUTO_CONTORNO"]
            checar("com a versao do pacote", e.get("versao") == "9.9", str(e.get("versao")))
            checar("com o caminho de instalacao", e.get("caminho") == dst, str(e.get("caminho")))
            checar("com a data", bool(e.get("data")), str(e.get("data")))


def teste_atualizacao_preserva_dado_do_operador():
    secao("instalar: atualizacao preserva o que o operador configurou")
    of, sa, ex, rz = temp("of5"), temp("sa5"), temp("ex5"), temp("rz5")
    montar_fantoma(of)
    pacote = empacotar(of, sa, versao="1.0")
    _extrair(pacote, ex)
    rc, _ = instalar(ex, rz)
    checar("primeira instalacao ok", rc == 0, "rc=%s" % rc)

    dst = os.path.join(rz, "AUTO_CONTORNO")
    with open(os.path.join(dst, "radai_watcher.config"), "w", encoding="utf-8") as f:
        f.write("ROOT=\\\\servidor\\imagens\\Patients\nPORT=%d\n" % _porta_livre())
    with open(os.path.join(dst, "_dados.txt"), "w", encoding="utf-8") as f:
        f.write("D:\\DADOS_CLINICOS\\radai\n")
    os.makedirs(os.path.join(dst, "calibracao", "receitas"), exist_ok=True)
    with open(os.path.join(dst, "calibracao", "receitas", "reto.json"), "w", encoding="utf-8") as f:
        f.write('{"nome":"reto","ops":[]}')
    with open(os.path.join(dst, "calibracao", "aceite.json"), "w", encoding="utf-8") as f:
        f.write('{"aceito":true}')
    with open(os.path.join(dst, "radai_vigia.log"), "w", encoding="utf-8") as f:
        f.write("historico da estacao\n")

    of2, sa2, ex2 = temp("of6"), temp("sa6"), temp("ex6")
    montar_fantoma(of2)
    pacote2 = empacotar(of2, sa2, versao="2.0")
    _extrair(pacote2, ex2)
    rc, saida = instalar(ex2, rz)
    checar("atualizacao terminou com codigo 0", rc == 0, "rc=%s | %s" % (rc, saida[-160:]))

    checar("radai_watcher.config sobreviveu",
           os.path.exists(os.path.join(dst, "radai_watcher.config")))
    if os.path.exists(os.path.join(dst, "radai_watcher.config")):
        txt = open(os.path.join(dst, "radai_watcher.config"), encoding="utf-8").read()
        checar("  e com o ROOT que o operador tinha posto",
               "\\\\servidor\\imagens" in txt, txt[:40])
    checar("_dados.txt sobreviveu", os.path.exists(os.path.join(dst, "_dados.txt")))
    checar("a receita da calibracao sobreviveu",
           os.path.exists(os.path.join(dst, "calibracao", "receitas", "reto.json")))
    checar("o aceite sobreviveu",
           os.path.exists(os.path.join(dst, "calibracao", "aceite.json")))
    checar("o log sobreviveu", os.path.exists(os.path.join(dst, "radai_vigia.log")))

    reg = json.load(open(os.path.join(rz, "_instalados.json"), encoding="utf-8"))
    checar("o registro passou a dizer 2.0",
           reg.get("AUTO_CONTORNO", {}).get("versao") == "2.0",
           str(reg.get("AUTO_CONTORNO", {}).get("versao")))


def _orfaos(rel):
    import re as _re
    txt = open(os.path.join(RAIZ, rel), encoding="utf-8-sig").read()
    m = _re.search(r"\$ORFAOS\s*=\s*@\((.*?)\)", txt, _re.S)
    return _re.findall(r'"([^"]+)"', m.group(1)) if m else []


def teste_reinstalar_tira_o_que_saiu_do_pacote():
    secao("instalar: reinstalar tira o que saiu do pacote (e so' isso)")
    a, b = _orfaos("installer/INSTALL.ps1"), _orfaos("packager/UPDATE.ps1")
    checar("o INSTALL.ps1 tem a lista $ORFAOS", bool(a), a)
    checar("  e ela e' IGUAL a do UPDATE.ps1", a == b and bool(a),
           "INSTALL=%s | UPDATE=%s" % (a, b))
    checar("  e leva o launchers\\start_engine.cmd",
           "launchers\\start_engine.cmd" in a, a)
    of, sa, ex, rz = temp("of_orf"), temp("sa_orf"), temp("ex_orf"), temp("rz_orf")
    montar_fantoma(of)
    pacote = empacotar(of, sa, versao="2.0")
    _extrair(pacote, ex)
    dst = os.path.join(rz, "AUTO_CONTORNO")
    for rel in ("launchers/start_engine.cmd", "launchers/meu_atalho.cmd",
                "iniciar_motor.cmd"):
        p = os.path.join(dst, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("REM " + rel + "\n")
    rc, saida = instalar(ex, rz)
    checar("a reinstalacao terminou com codigo 0", rc == 0,
           "rc=%s | %s" % (rc, saida[-160:]))
    checar("  e o launchers\\start_engine.cmd saiu",
           not os.path.exists(os.path.join(dst, "launchers", "start_engine.cmd")))
    checar("  e o iniciar_motor.cmd da raiz saiu",
           not os.path.exists(os.path.join(dst, "iniciar_motor.cmd")))
    checar("  e o .cmd do OPERADOR na mesma pasta ficou",
           os.path.exists(os.path.join(dst, "launchers", "meu_atalho.cmd")),
           "a lista tira o que e' NOSSO; remocao generica desfaz o sem /MIR")


def teste_registro_nao_apaga_outro_projeto():
    secao("instalar: o registro compartilhado e lido antes de gravar")
    of, sa, ex, rz = temp("of7"), temp("sa7"), temp("ex7"), temp("rz7")
    os.makedirs(rz, exist_ok=True)
    with open(os.path.join(rz, "_instalados.json"), "w", encoding="utf-8") as f:
        json.dump({"ATLAS_DE_ANATOMIA": {"versao": "1.0", "data": "2026-08-01",
                                         "caminho": "C:\\RADIOTERAPIA_AI\\ATLAS_DE_ANATOMIA"},
                   "FACILITA_RT": {"versao": "2.8.1", "data": "2026-08-05",
                                   "caminho": "C:\\RADIOTERAPIA_AI\\FACILITA_RT"}}, f)
    montar_fantoma(of)
    _extrair(empacotar(of, sa), ex)
    rc, saida = instalar(ex, rz)
    checar("instalou", rc == 0, "rc=%s | %s" % (rc, saida[-160:]))

    d = json.load(open(os.path.join(rz, "_instalados.json"), encoding="utf-8"))
    checar("ATLAS_DE_ANATOMIA continua la", "ATLAS_DE_ANATOMIA" in d, str(sorted(d)))
    checar("FACILITA_RT continua la", "FACILITA_RT" in d, str(sorted(d)))
    checar("  com a versao intacta",
           d.get("FACILITA_RT", {}).get("versao") == "2.8.1",
           str(d.get("FACILITA_RT", {}).get("versao")))
    checar("e AUTO_CONTORNO entrou", "AUTO_CONTORNO" in d, str(sorted(d)))


def teste_registro_corrompido_nao_derruba_a_instalacao():
    secao("instalar: registro ilegivel nao impede instalar")
    of, sa, ex, rz = temp("of8"), temp("sa8"), temp("ex8"), temp("rz8")
    os.makedirs(rz, exist_ok=True)
    with open(os.path.join(rz, "_instalados.json"), "w", encoding="utf-8") as f:
        f.write("{isto nao e json")
    montar_fantoma(of)
    _extrair(empacotar(of, sa), ex)
    rc, saida = instalar(ex, rz)
    checar("instalou mesmo assim", rc == 0, "rc=%s | %s" % (rc, saida[-160:]))
    checar("guardou copia do arquivo ilegivel",
           os.path.exists(os.path.join(rz, "_instalados.json.corrompido")))
    d = json.load(open(os.path.join(rz, "_instalados.json"), encoding="utf-8"))
    checar("e o registro voltou a ser valido", "AUTO_CONTORNO" in d, str(sorted(d)))


def teste_pacote_incompleto_falha_alto():
    secao("instalar: pacote pela metade para com mensagem, nao pela metade")
    of, sa, ex, rz = temp("of9"), temp("sa9"), temp("ex9"), temp("rz9")
    montar_fantoma(of)
    _extrair(empacotar(of, sa), ex)
    os.remove(os.path.join(ex, "AUTO_CONTORNO", "engine.py"))
    rc, saida = instalar(ex, rz)
    checar("nao terminou com 0", rc != 0, "rc=%s" % rc)
    checar("disse o que faltava", "engine.py" in saida, saida[-200:])
    checar("e explicou em portugues", "incompleto" in saida.lower(), saida[-200:])
    checar("nao deixou instalacao pela metade",
           not os.path.exists(os.path.join(rz, "AUTO_CONTORNO", "python", "python.exe")))


def teste_rodar_de_dentro_do_zip_e_recusado():
    secao("instalar: rodar de dentro do .zip para com a explicacao certa")
    of, sa, rz = temp("ofC"), temp("saC"), temp("rzC")
    montar_fantoma(of)
    pacote = empacotar(of, sa)

    base = temp("ofD")
    falsa = os.path.join(base, "Temp1_AUTO_CONTORNO_v9.9.zip")
    os.makedirs(falsa)
    with zipfile.ZipFile(str(pacote)) as z:
        for n in ("INSTALL.cmd", "INSTALL.ps1"):
            with open(os.path.join(falsa, n), "wb") as f:
                f.write(z.read(n))

    rc, saida = instalar(falsa, rz)
    checar("nao instalou", rc != 0, "rc=%s" % rc)
    checar("disse que o problema e estar dentro do zip",
           "dentro do arquivo .zip" in saida, saida[-200:])
    checar("e ensinou a saida (Extrair tudo)", "Extrair tudo" in saida, saida[-200:])
    checar("nada foi criado no destino",
           not os.path.exists(os.path.join(rz, "AUTO_CONTORNO")))


def teste_onde_instalar_nao_e_modo_de_teste():
    secao(u"onde instalar e modo de teste sao duas coisas")
    ps1 = io.open(os.path.join(RAIZ, "installer", "INSTALL.ps1"),
                  encoding="utf-8-sig", errors="replace").read()

    checar(u"o instalador honra RADAI_RAIZ_INSTALACAO",
           u"$env:RADAI_RAIZ_INSTALACAO" in ps1)
    checar(u"e tem uma variavel SO para o modo de teste",
           u"RADAI_ATALHOS_NA_RAIZ" in ps1)

    todas = ps1.splitlines()
    i = -1
    for n, linha in enumerate(todas):
        if u"_atalhos_desktop" in linha and not linha.strip().startswith(u"#"):
            i = sum(len(x) + 1 for x in todas[:n])
            break
    checar(u"a pasta de atalhos de teste existe no codigo", i > 0)
    if i <= 0:
        return
    linhas = ps1[:i].splitlines()
    abre = u""
    for linha in reversed(linhas):
        if linha.strip().startswith(u"if (") and u"$env:" in linha:
            abre = linha.strip()
            break
    checar(u"o `if` dos atalhos decide pela variavel de TESTE",
           u"RADAI_ATALHOS_NA_RAIZ" in abre,
           u"ele decidia por RADAI_RAIZ_INSTALACAO, que hoje e' o destino "
           u"escolhido pelo operador — achei: %s" % (abre or u"(nenhum if)"))
    checar(u"e NAO pela raiz de instalacao",
           u"RADAI_RAIZ_INSTALACAO" not in abre,
           u"instalar num D: nao pode significar 'isto e teste'")

    prep = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                   encoding="utf-8-sig", errors="replace").read()
    checar(u"o preparador manda o destino escolhido",
           u"$env:RADAI_RAIZ_INSTALACAO = $destino" in prep)
    checar(u"e NAO liga o modo de teste",
           u"RADAI_ATALHOS_NA_RAIZ" not in prep,
           u"instalacao de campo tem de criar o atalho de verdade")


def teste_downgrade_nao_passa_sem_confirmacao():
    secao("instalar: versao mais nova instalada nao e sobrescrita calada")
    of, sa, ex, rz = temp("ofA"), temp("saA"), temp("exA"), temp("rzA")
    montar_fantoma(of)
    _extrair(empacotar(of, sa, versao="3.0"), ex)
    rc, _ = instalar(ex, rz)
    checar("instalou a 3.0", rc == 0, "rc=%s" % rc)

    of2, sa2, ex2 = temp("ofB"), temp("saB"), temp("exB")
    montar_fantoma(of2)
    _extrair(empacotar(of2, sa2, versao="2.0"), ex2)
    rc, saida = instalar(ex2, rz)
    checar("a 2.0 foi recusada", rc == 2, "rc=%s | %s" % (rc, saida[-160:]))
    d = json.load(open(os.path.join(rz, "_instalados.json"), encoding="utf-8"))
    checar("o registro continua dizendo 3.0",
           d.get("AUTO_CONTORNO", {}).get("versao") == "3.0",
           str(d.get("AUTO_CONTORNO", {}).get("versao")))


def teste_registro_mora_no_pai_e_o_de_dentro_e_renomeado():
    secao("instalar: o registro mora no PAI da pasta do programa")
    of, sa, ex, rz = temp("ofR"), temp("saR"), temp("exR"), temp("rzR")
    montar_fantoma(of)
    _extrair(empacotar(of, sa, versao="2.0"), ex)
    dst = os.path.join(rz, "AUTO_CONTORNO")
    os.makedirs(dst)
    dentro = os.path.join(dst, "_instalados.json")
    with open(dentro, "w", encoding="utf-8") as f:
        json.dump({"AUTO_CONTORNO": {"versao": "1.0", "caminho": dst}}, f)
    rc, saida = instalar(ex, dst)
    checar("a raiz que ja termina no projeto instala nela mesma", rc == 0,
           "rc=%s | %s" % (rc, saida[-200:]))
    pai = os.path.join(rz, "_instalados.json")
    checar("o registro foi gravado no PAI", os.path.isfile(pai), pai)
    if os.path.isfile(pai):
        e = json.load(open(pai, encoding="utf-8")).get("AUTO_CONTORNO", {})
        checar("  com a versao e o caminho desta instalacao",
               e.get("versao") == "2.0" and e.get("caminho") == dst, str(e))
    checar("o de dentro saiu do nome que o app lia", not os.path.exists(dentro))
    checar("  e foi RENOMEADO, nao apagado",
           os.path.isfile(dentro + ".antigo")
           and "1.0" in open(dentro + ".antigo", encoding="utf-8").read())
    checar("  e o log diz o que aconteceu", "registro antigo" in saida, saida[-300:])

    of2, sa2, ex2, rz2 = temp("ofR2"), temp("saR2"), temp("exR2"), temp("rzR2")
    montar_fantoma(of2)
    _extrair(empacotar(of2, sa2, versao="2.0"), ex2)
    dst2 = os.path.join(rz2, "AUTO_CONTORNO")
    os.makedirs(dst2)
    alheio = os.path.join(dst2, "_instalados.json")
    with open(alheio, "w", encoding="utf-8") as f:
        json.dump({"OUTRO_PROJETO": {"versao": "1.0", "caminho": "D:\\outro"}}, f)
    rc2, _s2 = instalar(ex2, rz2)
    checar("(isca) registro de dentro que nao fala deste projeto fica como esta",
           rc2 == 0 and os.path.isfile(alheio)
           and not os.path.exists(alheio + ".antigo"))


def teste_reinstalar_tira_a_demo_e_a_verificacao_profunda():
    secao("instalar: a demo e o verify.cmd saem de quem atualiza")
    a, b = _orfaos("installer/INSTALL.ps1"), _orfaos("packager/UPDATE.ps1")
    checar("o $ORFAOS leva o maintenance\\verify.cmd",
           "maintenance\\verify.cmd" in a and a == b, a)
    import re as _re
    pa = []
    for rel in ("installer/INSTALL.ps1", "packager/UPDATE.ps1"):
        txt = open(os.path.join(RAIZ, rel), encoding="utf-8-sig").read()
        pa.append([_re.findall(r'"([^"]+)"', m) for m in _re.findall(
            r"\$PASTAS_ORFAS\s*=\s*@\(([^)]*)\)", txt)])
    checar("e o $PASTAS_ORFAS (a demo) e o mesmo nos dois",
           len(pa) == 2 and pa[0] == pa[1] == [["demo"]], pa)
    of, sa, ex, rz = temp("ofO"), temp("saO"), temp("exO"), temp("rzO")
    montar_fantoma(of)
    _extrair(empacotar(of, sa, versao="2.0"), ex)
    dst = os.path.join(rz, "AUTO_CONTORNO")
    for rel in ("demo/LCTSC/MANIFESTO.json", "maintenance/verify.cmd",
                "maintenance/meu_script.cmd"):
        p = os.path.join(dst, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("x\n")
    rc, saida = instalar(ex, rz)
    checar("a reinstalacao terminou com codigo 0", rc == 0, saida[-200:])
    checar("a pasta demo\\ saiu inteira",
           not os.path.exists(os.path.join(dst, "demo")))
    checar("  com uma linha no log", "a pasta demo" in saida, saida[-300:])
    checar("o maintenance\\verify.cmd saiu",
           not os.path.exists(os.path.join(dst, "maintenance", "verify.cmd")))
    checar("  e o que e do operador em maintenance\\ ficou",
           os.path.isfile(os.path.join(dst, "maintenance", "meu_script.cmd")))
    checar("  e o desinstalador tambem",
           os.path.isfile(os.path.join(dst, "maintenance", "UNINSTALL.cmd")))


ATUALIZAR = os.path.join(RAIZ, "packager", "UPDATE.ps1")


def _porta_livre():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def montar_pacote_leve(base, versao, projeto="LOCAL_SUITE"):
    p = os.path.join(base, "pacote")
    for sub in ("app", "tools", "build", "packager"):
        os.makedirs(os.path.join(p, sub), exist_ok=True)
    with open(os.path.join(p, "entrega.txt"), "w", encoding="utf-8") as f:
        f.write("PROJETO=%s\nVERSAO=%s\n" % (projeto, versao))
    for n in ("radai_watcher.py", "engine.py", "radai_geom.py"):
        with open(os.path.join(p, "app", n), "w", encoding="utf-8") as f:
            f.write("# %s versao %s\n" % (n, versao))
    for f_ in ("requisitos.py", "requirements-demo.txt",
               "configurar_ambiente.py", "artefatos.py"):
        shutil.copy2(os.path.join(RAIZ, "build", f_), os.path.join(p, "build", f_))
    for rel in ("app/radai_tasks.py", "app/radai_models.py"):
        shutil.copy2(_componentes.fonte(rel), os.path.join(p, rel.replace("/", os.sep)))
    shutil.copy2(ATUALIZAR, os.path.join(p, "packager", "UPDATE.ps1"))
    return p


def montar_instalacao_leve(base, versao, pacote, porta, projeto="LOCAL_SUITE"):
    raiz = os.path.join(base, "RADIOTERAPIA_AI")
    inst = os.path.join(raiz, projeto)
    os.makedirs(os.path.join(inst, "python"))
    for n in ("radai_watcher.py", "engine.py", "radai_geom.py"):
        with open(os.path.join(inst, n), "w", encoding="utf-8") as f:
            f.write("# %s ANTIGO\n" % n)
    with open(os.path.join(inst, "entrega.txt"), "w", encoding="utf-8") as f:
        f.write("PROJETO=%s\nVERSAO=%s\n" % (projeto, versao))
    with open(os.path.join(inst, "radai_watcher.config"), "w", encoding="utf-8") as f:
        f.write("PORT=%d\nROOT=C:\\nao_toque\n" % porta)
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import requisitos as R
    d = R.calcular(pacote)
    d["versao"] = versao
    with open(os.path.join(inst, "_requisitos.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(d))
    return raiz, inst


def _rodar_atualizar(pacote, args, amb):
    env = dict(os.environ)
    env.update(amb)
    p = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", os.path.join(pacote, "packager", "UPDATE.ps1")] + args,
        capture_output=True, stdin=subprocess.DEVNULL, env=env, timeout=300)
    return p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode("cp1252", "replace")


def _python_falso(pasta):
    os.makedirs(pasta, exist_ok=True)
    exe = os.path.join(pasta, "python.exe")
    shutil.copy2(os.path.join(os.environ.get("SystemRoot", "C:\\Windows"),
                              "System32", "PING.EXE"), exe)
    return exe


def _subir(exe):
    return subprocess.Popen([exe, "-n", "240", "127.0.0.1"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL)


def _vivo(proc):
    return proc.poll() is None


def teste_atualizar_registra_no_pai_e_tira_a_demo():
    secao("atualizar: o registro na regra unica, e a demo sai")
    base = temp("atreg")
    amb = {"LOCALAPPDATA": temp("atreg_ad"), "RADAI_ATALHOS_NA_RAIZ": "1"}
    pac = montar_pacote_leve(base, "8.5")
    raiz, inst = montar_instalacao_leve(base, "8.4", pac, _porta_livre())
    pai = os.path.join(raiz, "_instalados.json")
    dentro = os.path.join(inst, "_instalados.json")
    with open(pai, "w", encoding="utf-8") as f:
        json.dump({"LOCAL_SUITE": {"versao": "8.4", "caminho": inst},
                   "FACILITA_RT": {"versao": "2.8.1", "caminho": "C:\\x\\FACILITA_RT"}}, f)
    with open(dentro, "w", encoding="utf-8") as f:
        json.dump({"LOCAL_SUITE": {"versao": "8.3", "caminho": inst}}, f)
    os.makedirs(os.path.join(inst, "demo", "LCTSC"))
    with open(os.path.join(inst, "demo", "LCTSC", "MANIFESTO.json"), "w") as f:
        f.write("{}")
    os.makedirs(os.path.join(inst, "maintenance"))
    with open(os.path.join(inst, "maintenance", "verify.cmd"), "w") as f:
        f.write("REM\n")
    rc, t = _rodar_atualizar(pac, ["-Destino", inst, "-Python", sys.executable,
                                   "-SemPerguntar"], amb)
    checar("a atualizacao rodou", rc == 0, t[-400:])
    d = json.load(open(pai, encoding="utf-8")) if os.path.isfile(pai) else {}
    checar("o registro do PAI passou a 8.5, com o caminho",
           d.get("LOCAL_SUITE", {}).get("versao") == "8.5"
           and d.get("LOCAL_SUITE", {}).get("caminho") == inst, str(d)[:200])
    checar("  e o projeto vizinho ficou", d.get("FACILITA_RT", {}).get("versao") == "2.8.1")
    checar("o de dentro foi renomeado, sem apagar",
           not os.path.exists(dentro) and os.path.isfile(dentro + ".antigo"))
    checar("  e o log diz", "registro antigo" in t, t[-300:])
    checar("a pasta demo saiu, com uma linha no log",
           not os.path.exists(os.path.join(inst, "demo")) and "a pasta demo" in t)
    checar("o maintenance\\verify.cmd saiu",
           not os.path.exists(os.path.join(inst, "maintenance", "verify.cmd")))

    with open(pai, "w", encoding="utf-8") as f:
        json.dump({"LOCAL_SUITE": {"versao": "7.0", "caminho": "E:\\outra_estacao"}}, f)
    rc2, t2 = _rodar_atualizar(pac, ["-Destino", inst, "-Python", sys.executable,
                                     "-SemPerguntar"], amb)
    e2 = (json.load(open(pai, encoding="utf-8")).get("LOCAL_SUITE") or {}) if os.path.isfile(pai) else {}
    checar("registro do pai falando de outra pasta: passa a falar desta, e diz",
           rc2 == 0 and e2.get("caminho") == inst and "agora diz esta pasta" in t2,
           (e2, t2[-200:]))
    checar("  e nenhum registro nasce DENTRO da pasta",
           not os.path.exists(dentro), dentro)
    src = open(ATUALIZAR, encoding="utf-8-sig").read()
    checar("o atualizador nao manda rodar um UPDATE.cmd que nao existe",
           "UPDATE.cmd" not in src)
    checar("  nem fala do modo que saiu", "modelos e plugins" not in src)


def teste_atualizar_encerra_o_app_da_pasta():
    secao("atualizar: o app aberto na pasta e encerrado sozinho")
    base = temp("atenc")
    ad = temp("atenc_ad")
    amb = {"LOCALAPPDATA": ad, "RADAI_ATALHOS_NA_RAIZ": "1"}
    porta = _porta_livre()
    pac = montar_pacote_leve(base, "8.5")
    raiz, inst = montar_instalacao_leve(base, "8.4", pac, porta)
    fora = _python_falso(os.path.join(base, "outro_programa"))
    exe = _python_falso(os.path.join(inst, "python"))
    ping_dentro = os.path.join(inst, "ping.exe")
    shutil.copy2(fora, ping_dentro)
    procs = []
    try:
        app = _subir(exe)
        filho = _subir(exe)
        alheio = _subir(fora)
        nao_python = _subir(ping_dentro)
        procs = [app, filho, alheio, nao_python]
        os.makedirs(os.path.join(ad, "RADIOTERAPIA_AI"))
        with open(os.path.join(ad, "RADIOTERAPIA_AI", "motor_%d.json" % porta), "w") as f:
            json.dump({"estado": "rodando", "pid": alheio.pid, "hora": "x"}, f)
        rc, t = _rodar_atualizar(pac, ["-Destino", inst, "-SoEncerrar"], amb)
        checar("-SoEncerrar termina com 0", rc == 0, t[-400:])
        checar("o python.exe da pasta foi encerrado (e o filho dele)",
               not _vivo(app) and not _vivo(filho), t[-300:])
        checar("  com uma linha no log", "encerrado a forca" in t and "app encerrado" in t,
               t[-300:])
        checar("(isca) o python.exe de FORA da pasta continua vivo", _vivo(alheio))
        checar("  mesmo com o PID dele no estado do motor, que e recusado",
               "nao e o Python desta pasta" in t, t[-300:])
        checar("(isca) o programa da pasta que nao e Python continua vivo",
               _vivo(nao_python))

        rc2, t2 = _rodar_atualizar(pac, ["-Destino", inst, "-SoEncerrar"], amb)
        checar("sem app aberto: -SoEncerrar diz e sai com 0",
               rc2 == 0 and "nao esta aberto" in t2, t2[-200:])

        app2 = _subir(exe)
        procs.append(app2)
        with open(os.path.join(ad, "RADIOTERAPIA_AI", "motor_%d.json" % porta), "w") as f:
            json.dump({"estado": "rodando", "pid": app2.pid, "hora": "x"}, f)
        rc3, t3 = _rodar_atualizar(pac, ["-Destino", inst, "-Python", sys.executable,
                                         "-SemPerguntar"], amb)
        checar("Atualizar com o app aberto: encerra e atualiza", rc3 == 0
               and not _vivo(app2), t3[-400:])
        checar("  o codigo novo chegou",
               "versao 8.5" in open(os.path.join(inst, "engine.py")).read())
        est = json.load(open(os.path.join(ad, "RADIOTERAPIA_AI", "motor_%d.json" % porta)))
        checar("  e o estado do motor encerrado a forca deixa de dizer rodando",
               est.get("estado") == "encerrado", est)
    finally:
        for p in procs:
            try:
                p.kill()
            except Exception:
                pass


def teste_atualizar_pede_ao_app_que_feche():
    secao("atualizar: o app que responde e fechado pelo proprio Fechar tudo")
    import http.server
    import threading
    base = temp("atped")
    amb = {"LOCALAPPDATA": temp("atped_ad"), "RADAI_ATALHOS_NA_RAIZ": "1"}
    pac = montar_pacote_leve(base, "8.5")
    exe_dir = os.path.join(base, "RADIOTERAPIA_AI", "LOCAL_SUITE", "python")
    pedidos = []
    estado = {}

    class Mao(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            corpo = b'{"radai": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            pedidos.append((self.path, self.rfile.read(n)))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
            try:
                estado["app"].kill()
            except Exception:
                pass

            def _fechar():
                srv.shutdown()
                srv.server_close()
            threading.Thread(target=_fechar, daemon=True).start()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Mao)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    raiz, inst = montar_instalacao_leve(base, "8.4", pac, srv.server_address[1])
    exe = _python_falso(exe_dir)
    app = _subir(exe)
    estado["app"] = app
    try:
        rc, t = _rodar_atualizar(pac, ["-Destino", inst, "-SoEncerrar"], amb)
        checar("o app recebeu o pedido de fechar (POST /api/encerrar, modo tudo)",
               pedidos and pedidos[0][0] == "/api/encerrar"
               and b'"tudo"' in pedidos[0][1], pedidos)
        checar("  e saiu sem precisar de forca", rc == 0 and not _vivo(app)
               and "a forca" not in t and "pedi ao app" in t, t[-300:])
    finally:
        try:
            app.kill()
        except Exception:
            pass
        try:
            srv.server_close()
        except Exception:
            pass


FUNCOES_DO_ENCERRAMENTO = ("PortaDaInstalacao", "PortaViva", "EONossoPainel",
                           "PedirParaEncerrar", "_Prefixo", "ProcessoDaPasta",
                           "EstadoDoMotor", "ProcessosDoApp", "EsperarSumir",
                           "MarcarMotorEncerrado", "EncerrarOApp")


def _funcoes_ps1(texto):
    import re as _re
    achadas, atual, nome = {}, [], None
    for linha in texto.replace("\r\n", "\n").split("\n"):
        if nome is None:
            m = _re.match(r"function ([\w-]+)\(", linha)
            if not m:
                continue
            if linha.count("{") and linha.count("{") == linha.count("}"):
                achadas[m.group(1)] = linha
                continue
            nome, atual = m.group(1), [linha]
            continue
        atual.append(linha)
        if linha == "}":
            achadas[nome] = "\n".join(atual)
            nome = None
    return achadas


def teste_instalar_e_atualizar_encerram_pela_mesma_regra():
    secao("instalar e atualizar: o app aberto se encerra pela MESMA regra")
    a = _funcoes_ps1(open(os.path.join(RAIZ, "installer", "INSTALL.ps1"),
                          encoding="utf-8-sig").read())
    b = _funcoes_ps1(open(ATUALIZAR, encoding="utf-8-sig").read())
    for nome in FUNCOES_DO_ENCERRAMENTO:
        checar("%s: o INSTALL.ps1 tem a mesma do UPDATE.ps1" % nome,
               nome in a and a.get(nome) == b.get(nome),
               "diverge" if nome in a else "ausente no INSTALL.ps1")
    forjada = dict(a)
    forjada["ProcessoDaPasta"] = a.get("ProcessoDaPasta", "").replace(
        "python.exe", "pythonw.exe")
    checar("(isca) uma letra trocada numa delas e acusada",
           forjada["ProcessoDaPasta"] != b.get("ProcessoDaPasta"))


def _instalacao_com_app(base, porta):
    of, sa, ex, rz = (temp(base + "_of"), temp(base + "_sa"),
                      temp(base + "_ex"), temp(base + "_rz"))
    montar_fantoma(of)
    _extrair(empacotar(of, sa, versao="2.0"), ex)
    rc, saida = instalar(ex, rz)
    dst = os.path.join(rz, "AUTO_CONTORNO")
    with open(os.path.join(dst, "radai_watcher.config"), "w",
              encoding="utf-8") as f:
        f.write("PORT=%d\n" % porta)
    with open(os.path.join(dst, "engine.py"), "w", encoding="utf-8") as f:
        f.write("# ANTIGO\n")
    return ex, rz, dst, rc, saida


def teste_instalar_encerra_o_app_da_pasta():
    secao("instalar (INSTALL.cmd do pacote): o app aberto e encerrado antes da copia")
    ad = temp("inenc_ad")
    porta = _porta_livre()
    ex, rz, dst, rc0, s0 = _instalacao_com_app("inenc", porta)
    checar("a primeira instalacao deu certo", rc0 == 0, s0[-200:])
    exe = _python_falso(os.path.join(dst, "python"))
    fora = _python_falso(os.path.join(temp("inenc_fora"), "outro_programa"))
    ping_dentro = os.path.join(dst, "ping_do_operador.exe")
    shutil.copy2(fora, ping_dentro)
    procs = []
    try:
        app = _subir(exe)
        filho = _subir(exe)
        alheio = _subir(fora)
        nao_python = _subir(ping_dentro)
        procs = [app, filho, alheio, nao_python]
        os.makedirs(os.path.join(ad, "RADIOTERAPIA_AI"))
        with open(os.path.join(ad, "RADIOTERAPIA_AI", "motor_%d.json" % porta),
                  "w") as f:
            json.dump({"estado": "rodando", "pid": alheio.pid, "hora": "x"}, f)
        preso = False
        try:
            open(exe, "r+b").close()
        except OSError:
            preso = True
        checar("(isca) com o app aberto o python.exe da pasta esta preso: "
               "copiar por cima falharia", preso)
        rc, t = instalar(ex, rz, {"LOCALAPPDATA": ad})
        checar("a reinstalacao com o app aberto termina com 0", rc == 0, t[-400:])
        checar("  o python.exe da pasta foi encerrado (e o filho dele)",
               not _vivo(app) and not _vivo(filho), t[-300:])
        checar("  com as linhas no log", "encerrado a forca" in t
               and "app encerrado" in t, t[-300:])
        checar("  e o codigo novo chegou",
               "ANTIGO" not in open(os.path.join(dst, "engine.py"),
                                    encoding="utf-8").read())
        checar("(isca) o python.exe de FORA da pasta continua vivo",
               _vivo(alheio))
        checar("  mesmo com o PID dele no estado do motor, que e recusado",
               "nao e o Python desta pasta" in t, t[-300:])
        checar("(isca) o programa da pasta que nao e Python continua vivo",
               _vivo(nao_python))
        est = json.load(open(os.path.join(ad, "RADIOTERAPIA_AI",
                                          "motor_%d.json" % porta)))
        checar("  e o estado do motor de outro processo nao e reescrito",
               est.get("estado") == "rodando" and est.get("pid") == alheio.pid,
               est)
        rc2, t2 = instalar(ex, rz, {"LOCALAPPDATA": ad})
        checar("sem app aberto: diz e instala", rc2 == 0
               and "o app nao esta aberto nesta pasta" in t2, t2[-300:])
    finally:
        for p in procs:
            try:
                p.kill()
            except Exception:
                pass


def teste_instalar_para_quando_nao_consegue_encerrar():
    secao("instalar: o painel que nao fecha faz perguntar, e sem console para")
    import http.server
    import threading
    pedidos = []

    class Mao(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            corpo = b'{"radai": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            pedidos.append((self.path, self.rfile.read(n)))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Mao)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        ex, rz, dst, rc0, s0 = _instalacao_com_app("inpar", srv.server_address[1])
        checar("a primeira instalacao deu certo", rc0 == 0, s0[-200:])
        rc, t = instalar(ex, rz)
        checar("o painel de outro processo na porta desta pasta para a copia",
               rc != 0 and "nao consegui encerra-lo" in t, "rc=%s | %s"
               % (rc, t[-300:]))
        checar("  e nada foi copiado",
               "ANTIGO" in open(os.path.join(dst, "engine.py"),
                                encoding="utf-8").read())
        checar("  e o painel que nao e desta pasta nunca recebe o pedido de "
               "fechar", not pedidos, pedidos)
    finally:
        try:
            srv.shutdown()
            srv.server_close()
        except Exception:
            pass


def main():
    print("=" * 64)
    print(" test_installer — contrato de instalacao do ecossistema")
    print("=" * 64)

    if not os.path.isdir(os.path.join(RAIZ, "build")):
        print("\n  NAO SE APLICA: nao ha build/ nesta arvore.")
        print("  Esta bateria testa o EMPACOTAMENTO; o deploy so roda a")
        print("  aplicacao. Rode-a no repositorio, antes de publicar.")
        print("=" * 64)
        return 0

    testes = [teste_pacote_e_um_arquivo_so,
              teste_pacote_sem_recorte_no_corpo_nao_sai,
              teste_credencial_aborta_a_geracao,
              teste_trava_separa_mencao_de_segredo,
              teste_o_proprio_repositorio_passa_na_trava,
              teste_credencial_renomeada_tambem_aborta,
              teste_instalacao_nova,
              teste_atualizacao_preserva_dado_do_operador,
              teste_reinstalar_tira_o_que_saiu_do_pacote,
              teste_registro_nao_apaga_outro_projeto,
              teste_registro_corrompido_nao_derruba_a_instalacao,
              teste_pacote_incompleto_falha_alto,
              teste_rodar_de_dentro_do_zip_e_recusado,
              teste_downgrade_nao_passa_sem_confirmacao,
              teste_onde_instalar_nao_e_modo_de_teste,
              teste_registro_mora_no_pai_e_o_de_dentro_e_renomeado,
              teste_reinstalar_tira_a_demo_e_a_verificacao_profunda,
              teste_atualizar_registra_no_pai_e_tira_a_demo,
              teste_atualizar_encerra_o_app_da_pasta,
              teste_atualizar_pede_ao_app_que_feche,
              teste_instalar_e_atualizar_encerram_pela_mesma_regra,
              teste_instalar_encerra_o_app_da_pasta,
              teste_instalar_para_quando_nao_consegue_encerrar]
    for t in testes:
        try:
            t()
        except (Exception, SystemExit) as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    for d in _TEMPS:
        shutil.rmtree(d, ignore_errors=True)

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
