# -*- coding: utf-8 -*-
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent

DESTINO = "deploy"

def _raiz_destino(projeto=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import destino_de_entrega
    return destino_de_entrega.raiz_de_entrega(projeto, de=RAIZ)[0]

CATALOGO = RAIZ / "packager" / "catalogo.json"


def tamanho_do_pacote():
    import json
    try:
        p = json.loads(CATALOGO.read_text(encoding="utf-8"))["pacote"]
        return float(p["pacote_gib"]), float(p["disco_gib"])
    except Exception as e:
        raise SystemExit(
            u"PAREI: o catalogo.json nao trouxe o bloco `pacote` (%s: %s).\n"
            u"Rode  python build/gerar_catalogo.py  e empacote de novo."
            % (type(e).__name__, e))


def texto_do_tamanho(gib):
    return u"%.0f" % gib

PASTAS = [
    ("packager", "packager"),
    ("app", "app"),
    ("build", "build"),
    ("tools", "tools"),
    ("installer", "installer"),
]
ARQUIVOS = [
    "LICENSE", "NOTICE",
]

FORA = {"__pycache__", ".venv", "_montagem", "_descarte", "calibracao",
        "_radai_dados", ".git", "node_modules", "modelos", "ts_weights",
        "registro", "cache_tasks"}
FORA_EXT = {".pyc", ".pyo", ".log", ".zip", ".tar", ".whl", ".pth", ".dcm"}
# GUARDA: o preparo da porta (npm, esbuild) gera app/porta/porta.js na oficina;
# a estacao recebe o porta.js pronto e nunca monta a porta.
FORA_PREFIXOS = ("build/porta/",)


def ler_entrega():
    p = RAIZ / "entrega.txt"
    if not p.is_file():
        raise SystemExit(u"PAREI: nao achei %s, que declara PROJETO e VERSAO." % p)
    txt = io.open(p, encoding="utf-8-sig").read()
    d = {}
    for linha in txt.splitlines():
        m = re.match(r"^\s*([A-Z_]+)\s*=\s*(.+?)\s*$", linha)
        if m:
            d[m.group(1)] = m.group(2)
    for k in ("PROJETO", "VERSAO"):
        if not d.get(k):
            raise SystemExit(u"PAREI: `%s` nao esta em entrega.txt." % k)
    return d["PROJETO"], d["VERSAO"], d.get("PRODUTO") or d["PROJETO"]


def ler_bundle_minimo(versao):
    p = RAIZ / "entrega.txt"
    m = None
    for linha in io.open(p, encoding="utf-8-sig").read().splitlines():
        r = re.match(r"^\s*BUNDLE_MINIMO\s*=\s*(.+?)\s*$", linha)
        if r:
            m = r.group(1)
    if not m or not re.match(r"^\d+(\.\d+)*$", m):
        raise SystemExit(u"PAREI: `BUNDLE_MINIMO` falta no entrega.txt, ou nao "
                         u"e' so' digito e ponto (%r). A aba 0 do instalador "
                         u"mostra esse numero, e o modo 3 o cumpre." % m)

    def _n(v):
        return ([int(x) if x.isdigit() else 0 for x in v.split(u".")]
                + [0, 0, 0, 0])[:4]
    if _n(m) > _n(versao):
        raise SystemExit(u"PAREI: BUNDLE_MINIMO=%s e' maior que VERSAO=%s -- "
                         u"este instalador recusaria o pacote da propria "
                         u"versao." % (m, versao))
    return m


FORA_NOMES = {"INSTALL_LOG.txt", "UNINSTALL_LOG.txt",
              "preparar_log.txt", "verify_log.txt",
              "radai_watcher.config"}


def entra(caminho):
    partes = set(Path(caminho).parts)
    if partes & FORA:
        return False
    if Path(caminho).name in FORA_NOMES:
        return False
    return Path(caminho).suffix.lower() not in FORA_EXT


def conferir_sem_phi(itens):
    suspeitos = [n for n, _ in itens
                 if n.lower().endswith((".dcm", ".dicom", ".ima", ".npz", ".npy",
                                        ".nii", ".nii.gz", ".nrrd"))]
    if suspeitos:
        raise SystemExit(
            u"PAREI: achei %d arquivo(s) que parecem imagem ou mascara de "
            u"paciente na montagem:\n  %s\n\n"
            u"Nenhum pacote sai com imagem de paciente dentro."
            % (len(suspeitos), "\n  ".join(suspeitos[:5])))
    for nome, caminho in itens:
        n = Path(nome).name.lower()
        if n in ("chave_nvidia.txt", ".env", "secrets.json",
                 "_pseudonimo.chave", "radai_watcher.config"):
            raise SystemExit(
                u"PAREI: `%s` nao pode entrar num pacote.\n\n"
                u"  chave, segredo ou configuracao do operador -- ver `FORA` "
                u"e `FORA_NOMES`." % nome)
        if "registro/casos/" in nome.replace("\\", "/"):
            raise SystemExit(
                u"PAREI: `%s` e' registro de caso desta maquina.\n\n"
                u"  O acervo do operador nao viaja no instalador." % nome)


def _mesma_pasta(a, b):
    return (os.path.normcase(os.path.realpath(str(a)))
            == os.path.normcase(os.path.realpath(str(b))))


def versionados(raiz=None):
    raiz = Path(raiz or RAIZ)
    try:
        topo = subprocess.run(["git", "-C", str(raiz), "rev-parse",
                               "--show-toplevel"],
                              capture_output=True, timeout=60)
        # GUARDA: pasta que nao e a raiz do proprio repositorio (o app baixado da trava, extraido dentro de outro) responderia "nada versionado".
        if topo.returncode != 0 or not _mesma_pasta(
                topo.stdout.decode("utf-8", "replace").strip() or "\0", raiz):
            return None
        r = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z"],
                           capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return set(p for p in r.stdout.decode("utf-8", "replace").split("\0") if p)


def baixado_da_trava(pasta):
    base = os.environ.get("RADAI_COMPONENTES_DIR", "").strip()
    if not base:
        return False
    try:
        return os.path.commonpath([os.path.realpath(base),
                                   os.path.realpath(str(pasta))]) \
            == os.path.realpath(base)
    except ValueError:
        return False


def conferir_versionados(itens, raiz=None, conhecidos=None):
    raiz = Path(raiz or RAIZ)
    conhecidos = versionados(raiz) if conhecidos is None else conhecidos
    if conhecidos is None:
        print(u"  (fora de um repositorio Git: a conferencia do versionado nao roda)")
        return
    fora = []
    for nome, cheio in itens:
        try:
            rel = Path(cheio).resolve().relative_to(raiz.resolve()).as_posix()
        except ValueError:
            fora.append(nome)
            continue
        if rel not in conhecidos:
            fora.append(nome)
    if fora:
        raise SystemExit(
            u"PAREI: %d arquivo(s) que o Git nao conhece entrariam no instalador:\n"
            u"  %s\n\nVersione, ou tire da oficina." % (len(fora), "\n  ".join(fora[:8])))


def conferir_arvore_baixada(pasta, nome, trava=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import baixar_componentes as B
    try:
        lista = B.ler_trava(trava or B.TRAVA)
    except (B.Parei, OSError, ValueError) as e:
        raise SystemExit(u"PAREI: %s" % e)
    esperada = next((c.get("arvore_sha256") for c in lista
                     if c.get("nome") == nome), None)
    if not esperada:
        raise SystemExit(
            u"PAREI: %s veio da pasta baixada (%s), e a trava nao traz a "
            u"arvore dele: escreva-a com  python build/baixar_componentes.py "
            u"--travar <tag>" % (nome, pasta))
    medida = B.arvore_sha256(str(pasta))
    if medida != esperada:
        raise SystemExit(
            u"PAREI: a arvore de %s em %s (%s) nao e a da trava (%s): a pasta "
            u"mudou depois do download. Baixe de novo "
            u"(build/baixar_componentes.py) sem mexer nela."
            % (nome, pasta, medida[:12], esperada[:12]))
    return medida


def componentes_que_faltam(achados, trava=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import baixar_componentes as B
    try:
        lista = B.ler_trava(trava or B.TRAVA)
    except (B.Parei, OSError, ValueError) as e:
        raise SystemExit(u"PAREI: %s" % e)
    achados = set(achados)
    return sorted(c.get("nome") for c in lista if c.get("nome") not in achados)


def coletar_componentes(ja, suite=None, trava=None):
    sys.path.insert(0, str(RAIZ / "tools"))
    import _componentes
    itens = []
    achados = []
    for pasta, dados in _componentes.componentes(str(suite or RAIZ)):
        achados.append(dados.get("nome"))
        deste = []
        for sub in ("app", "tools"):
            base = Path(pasta) / sub
            if not base.is_dir():
                continue
            for raiz, dirs, arqs in os.walk(base):
                dirs[:] = [d for d in dirs if d not in FORA]
                for a in sorted(arqs):
                    cheio = Path(raiz) / a
                    rel = cheio.relative_to(base)
                    if not entra(rel):
                        continue
                    nome = "%s/%s" % (sub, rel.as_posix())
                    if nome in ja:
                        raise SystemExit(
                            u"PAREI: `%s` existe na Suite e em %s."
                            % (nome, dados.get("nome")))
                    ja.add(nome)
                    deste.append((nome, str(cheio)))
        if baixado_da_trava(pasta) and versionados(pasta) is None:
            medida = conferir_arvore_baixada(pasta, dados.get("nome"), trava)
            print(u"  %s: baixado da trava, com a arvore conferida de novo "
                  u"(%s); sem Git proprio, a conferencia do versionado nao "
                  u"se aplica" % (dados.get("nome"), medida[:12]))
        else:
            conferir_versionados(deste, raiz=pasta)
        itens += deste
    faltam = componentes_que_faltam(achados, trava)
    if faltam:
        raise SystemExit(
            u"PAREI: o instalador sairia sem %s. Clone os repositorios dos "
            u"seis apps como pastas irmas do local-suite (ou aponte "
            u"RADAI_COMPONENTES_DIR para a pasta que os tem), ou monte com "
            u"--dos-repositorios." % u", ".join(faltam))
    return itens


def coletar():
    itens = []
    for origem, dentro in PASTAS:
        base = RAIZ / origem
        if not base.is_dir():
            raise SystemExit(u"PAREI: falta a pasta `%s`." % origem)
        for raiz, dirs, arqs in os.walk(base):
            dirs[:] = [d for d in dirs if d not in FORA]
            for a in sorted(arqs):
                cheio = Path(raiz) / a
                rel = cheio.relative_to(base)
                if not entra(rel):
                    continue
                nome = "%s/%s" % (dentro, rel.as_posix())
                if nome.startswith(FORA_PREFIXOS):
                    continue
                itens.append((nome, str(cheio)))
    conferir_versionados(itens)
    itens += coletar_componentes(set(n for n, _ in itens))
    import _componentes
    for a in ARQUIVOS:
        p = Path(_componentes.fonte(a, str(RAIZ)))
        if not p.is_file():
            raise SystemExit(
                u"PAREI: falta `%s`. LICENSE e NOTICE sao condicao da "
                u"Apache-2.0, e os tres empacotadores abortam sem eles." % a)
        itens.append((a, str(p)))
    return sorted(itens)


def main():
    projeto, versao, produto = ler_entrega()
    bundle_minimo = ler_bundle_minimo(versao)
    raiz_destino = _raiz_destino(projeto)
    saida_dir = raiz_destino / projeto / ("v" + versao)
    saida = saida_dir / ("%s_SETUP_v%s.zip" % (produto, versao))
    pasta_fixo = raiz_destino / projeto / "latest"
    fixo = pasta_fixo / ("%s_SETUP_LATEST.zip" % produto)

    print(u"  %s v%s" % (projeto, versao))
    print(u"  destino: %s  (%s)" % (saida_dir, DESTINO))
    pacote_gib, disco_gib = tamanho_do_pacote()
    tam_txt = texto_do_tamanho(pacote_gib)
    print(u"  pacote completo: ~%s GB (disco para preparar: %.0f GB)"
          % (tam_txt, disco_gib))

    itens = coletar()
    conferir_sem_phi(itens)
    bytes_ = sum(os.path.getsize(c) for _, c in itens)
    print(u"  %d arquivos, %.1f MB antes de comprimir" % (len(itens), bytes_ / 1e6))

    saida_dir.mkdir(parents=True, exist_ok=True)
    tmp = str(saida) + ".parcial"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for nome, caminho in itens:
            z.write(caminho, "programa/" + nome)
        sys.path.insert(0, str(RAIZ / "build"))
        import carimbo
        _entrega_txt = (carimbo.texto(projeto, versao, produto, RAIZ) +
                        u"BUNDLE_MINIMO=%s\n" % bundle_minimo)
        z.writestr("programa/entrega.txt", _entrega_txt)
        z.writestr("programa/VERSION.txt",
                   carimbo.version_txt(projeto, versao, produto, RAIZ))
        _aviso = carimbo.aviso_de_arvore_suja(_entrega_txt)
        if _aviso:
            print(u"  " + _aviso)
        de = RAIZ / "packager" / "START_HERE.cmd"
        if not de.exists():
            raise SystemExit("falta packager/START_HERE.cmd")
        z.write(str(de), "START_HERE.cmd")
        z.writestr("programa/PACKAGE_SIZE.txt", (tam_txt + u"\r\n").encode("ascii"))
        z.writestr("README.txt", LEIA_ME % {"projeto": projeto,
                                    "versao": versao,
                                    "tamanho": tam_txt,
                                    "disco": u"%.0f" % disco_gib})
    conferir_montado(tmp, bundle_minimo)
    # GUARDA: o nome oficial e o LATEST (o asset da release) so recebem o .zip ja conferido.
    if os.path.exists(saida):
        os.unlink(saida)
    os.replace(tmp, saida)
    pasta_fixo.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(saida), str(fixo))

    tam = os.path.getsize(saida)

    try:
        alvo = saida_dir.parent / "README.txt"
        texto = LEIA_ME_PASTA % {"projeto": projeto, "versao": versao,
                                 "pacote": saida.name,
                                 "mb": u"%.1f MB" % (tam / 1e6)}
        io.open(str(alvo), "w", encoding="ascii",
                newline="\r\n").write(texto)
        print(u"  LEIA-ME.txt da pasta reescrito (%s)" % alvo)
    except Exception as e:
        print(u"  AVISO: nao consegui reescrever o LEIA-ME.txt (%s: %s)"
              % (type(e).__name__, e))

    print(u"\n  PRONTO: %s" % saida)
    print(u"  %.1f MB" % (tam / 1e6))
    print(u"\n  (o pacote completo mede ~%s GB na maquina de quem instala;"
          u" este e %.0fx menor, e os pesos nascem la)"
          % (tam_txt, pacote_gib * 1073741824.0 / max(tam, 1.0)))
    return 0


def conferir_montado(caminho, bundle_minimo):
    try:
        with zipfile.ZipFile(caminho) as _z:
            _ruim = _z.testzip()
            _originais = set(_z.namelist())
            _n = {n[len("programa/"):] if n.startswith("programa/") else n
                  for n in _originais}
            _raiz = {n for n in _originais if "/" not in n.rstrip("/")}
            if _raiz != {"README.txt", "START_HERE.cmd"}:
                raise ValueError("a raiz deve conter apenas README.txt e START_HERE.cmd")
            _ent = (_z.read("programa/entrega.txt").decode("utf-8", "replace")
                    if "entrega.txt" in _n else u"")
    except Exception as e:
        raise SystemExit(u"PAREI: nao consegui montar o pacote do "
                         u"preparador — o .zip nao abre (%s: %s)"
                         % (type(e).__name__, e))
    if _ruim:
        raise SystemExit(u"PAREI: nao consegui montar o pacote do preparador "
                         u"— `%s` esta corrompido dentro do .zip." % _ruim)
    _faltam = [x for x in ("START_HERE.cmd", "entrega.txt",
                           "LICENSE", "NOTICE", "PACKAGE_SIZE.txt",
                           "build/requisitos.py", "app/radai_tasks.py",
                           "app/radai_models.py",
                           "packager/catalogo.json")
               if x not in _n and x.replace("/", "\\") not in _n]
    if _faltam:
        raise SystemExit(u"PAREI: nao consegui montar o pacote do preparador "
                         u"— faltam dentro do .zip: %s" % ", ".join(_faltam))
    if (u"BUNDLE_MINIMO=%s" % bundle_minimo) not in _ent:
        raise SystemExit(u"PAREI: o entrega.txt de dentro do .zip nao traz "
                         u"BUNDLE_MINIMO=%s -- a aba 0 do instalador cairia no "
                         u"recuo e diria outro numero." % bundle_minimo)


LEIA_ME_PASTA = r"""A ENTREGA DESTE PROJETO E UM ARQUIVO SO, E ELE ESTA EM  v%(versao)s\

    %(pacote)s     ~%(mb)s

Fora daqui so ha latest\, com uma copia de nome fixo do arquivo acima --
ela e o alvo do link da release. Qualquer OUTRO arquivo solto aqui ou
dentro de v%(versao)s\ veio de copia manual.


O QUE E ESSE ARQUIVO, E O QUE ELE NAO E

Ele e o SETUP -- instala, atualiza e desinstala --, e cabe num e-mail.
Ele nao carrega os modelos.

Em latest\ ha uma copia com o nome fixo _SETUP_LATEST.zip. E o MESMO
arquivo, byte a byte: ela existe so para o link da release, que precisa de
um nome que nao mude a cada versao. A versao esta no VERSION.txt, dentro do
pacote -- e nao no nome do arquivo, que e justamente o que o apelido abre mao
de dizer.

Quem carrega os modelos e o BUNDLE -- o tamanho dele esta no
PACKAGE_SIZE.txt, dentro do .zip. O bundle nao e entrega: e o que a maquina
de passagem monta e o que a estacao offline instala, e quem o produz e o
preparador, NA MAQUINA DO SERVICO, na pasta de trabalho que a pessoa
escolheu. O instalador leve cabe num e-mail, e o que ele monta na ponta e
identico.


COMO SE USA

  1. Extraia o .zip numa pasta.
  2. De dois cliques em START_HERE.cmd, DE DENTRO DA PASTA EXTRAIDA.
  3. Ele abre o preparador, que baixa o que falta e monta o pacote.

Numa maquina que ja tem o Local Suite instalado, o preparador detecta a
instalacao e oferece atualizar (tudo, so o app, ou de um pacote trazido),
montar novo pacote ou desinstalar.

Dois cliques num .cmd DE DENTRO do .zip nao funcionam: o Explorer extrai so
aquele arquivo para uma pasta temporaria e executa sem o resto do pacote. O
proprio START_HERE detecta isso e avisa.


QUEM GERA ESTA PASTA

O build\empacotar_instalador.py, do repositorio da Suite. Ele e o unico
empacotador da entrega, e nao aceita caminho digitado: o destino e a conta

    <raiz de entrega> \ PROJETO \ v<VERSAO>

com PROJETO e VERSAO lidos do entrega.txt na raiz do projeto, e a raiz de
entrega achada por build\destino_de_entrega.py (a variavel
RADAI_RAIZ_DEPLOY, ou a politica de entrega do ecossistema). Subir a VERSAO
la e um ato humano -- e o que responde "o que exatamente esta rodando naquela
estacao".


QUAL BUILD ESTA AQUI

O entrega.txt vai DENTRO do .zip, carimbado a cada publicacao com DATA e
BUILD (data + commit curto). O rodape da tela inicial le esse mesmo arquivo.

Ao relatar um defeito, mande a linha do rodape. Ela e a identidade.

E dentro do programa instalado, em Configuracoes > Diagnosticos e Registros,
o Diagnosticar confere em segundos as versoes, os pesos, a GPU, as travas
clinicas e o laudo da pasta dos exames.


IMAGEM DE PACIENTE NAO MORA AQUI

Daqui sai codigo e o instalador leve. Os pesos de modelo nao saem daqui:
eles sao baixados na maquina de passagem, direto da origem.

Se esta pasta sincroniza com a nuvem, nada de paciente pode morar nela.
Serie DICOM, RTSTRUCT real e log com PatientID ficam em C:\RADIOTERAPIA_AI,
fora de toda pasta que sincroniza. E essa separacao fisica que protege o
dado -- nao o .gitignore, que nao tem efeito sobre a nuvem.


A LICENCA DOS MODELOS

O TotalSegmentator, que faz o fluxo principal, e Apache-2.0. Os quatro
modelos de comparacao -- NV-Segment-CT, CADS, MOOSE e os niveis cervicais --
sao de licenca permissiva ou de uso comercial permitido; o NOTICE diz qual e
de quem. O preparador mostra cada licenca e exige o aceite antes de montar
qualquer pacote, e o pacote e sempre o completo: nao existe versao reduzida.
"""

LEIA_ME = u"""%(projeto)s v%(versao)s - INSTALLER

This file is NOT the program: it is the installer for it.

  1. Extract this whole .zip into a folder.
  2. Double-click START_HERE.cmd, from inside the extracted folder.
  3. On the first screen, choose what to do:

     Install / Update app on this machine   the big button: it checks
                                           whether the program is already
                                           here. If not, it installs
                                           everything straight into the
                                           final folder, in one step (no
                                           .zip). If it is, it decides by
                                           itself: a newer installer in the
                                           release is downloaded, checked
                                           and used; same requirements,
                                           code only, no internet;
                                           otherwise everything, online, or
                                           the full .zip you brought -
                                           without one, it cancels
     Offline machine: install from a       installs the .zip you brought
     package I brought
     Machine with internet: build a        downloads everything, makes a .zip
     package to take to the offline
     machine
     Uninstall

Every option that swaps the code closes the app first, if it is open, and says
so in the log.

Installing everything and building a package need internet. Installing from a
package you brought needs none - it only opens the file someone else prepared.
Updating uses the internet when there is some, and the log says each decision
it took.

THE PACKAGE IS ABOUT %(tamanho)s GB, always the complete one, and preparing it
needs about %(disco)s GB free on disk. It is not inside this .zip on purpose:
that way you build the package with the versions of the day, on your own
machine, and you know exactly what is in it. The same number is in
programa/PACKAGE_SIZE.txt.

The component licences are shown before any download, and none of them starts
without acceptance. None of them is non-commercial: every model allows
commercial use, and the NOTICE file says which licence is whose.

If the preparer stops with an error, its log is kept in
%%LOCALAPPDATA%%\\RadioterapiaAI\\logs - the error screen says which file.

This is study and research material. It is NOT a medical device and it is not
validated for clinical use. Every structure comes out as an UNAPPROVED
SUGGESTION; reviewing and approving remains a medical act, in the planning
system.

The interface is available in twelve languages and opens in English. The Terms
of Use and the licence texts are authoritative in their original language.
"""

def dos_repositorios(argv):
    if "--dos-repositorios" not in argv:
        return 0
    sys.path.insert(0, str(RAIZ / "build"))
    import baixar_componentes
    destino = str(RAIZ / "_montagem" / "componentes")
    print(u"  baixando os componentes da trava (build/componentes.lock.json)...")
    try:
        baixar_componentes.baixar_todos(destino, tok=baixar_componentes.token())
    except baixar_componentes.Parei as e:
        print(u"PAREI: %s" % e)
        return 1
    os.environ["RADAI_COMPONENTES_DIR"] = destino
    return 0


if __name__ == "__main__":
    if dos_repositorios(sys.argv[1:]):
        raise SystemExit(1)
    raise SystemExit(main())
