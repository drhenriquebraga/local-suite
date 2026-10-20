# -*- coding: utf-8 -*-
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAVA = os.path.join(RAIZ, "build", "componentes.lock.json")
ORIGEM_PADRAO = "https://api.github.com/repos/{repositorio}/zipball/{tag}"
SUITE = "local-suite"


class Parei(Exception):
    pass


def ler_trava(caminho=TRAVA):
    with io.open(caminho, encoding="utf-8-sig") as f:
        dados = json.load(f)
    lista = dados.get("componentes")
    if not isinstance(lista, list) or not lista:
        raise Parei(u"a trava %s não lista componente nenhum" % caminho)
    return lista


def token():
    for chave in ("GITHUB_TOKEN", "GH_TOKEN"):
        valor = os.environ.get(chave, "").strip()
        if valor:
            return valor
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True,
                           text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def baixar(url, destino, tok=None):
    pedido = urllib.request.Request(url, headers={
        "User-Agent": "radioterapia-ai-local-suite",
        "Accept": "application/vnd.github+json"})
    if tok and url.startswith("https://"):
        pedido.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(pedido, timeout=120) as r, \
            io.open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def sha256(caminho):
    h = hashlib.sha256()
    with io.open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def extrair(arquivo_zip, pasta_final):
    temporaria = pasta_final + ".baixando"
    if os.path.isdir(temporaria):
        shutil.rmtree(temporaria)
    os.makedirs(temporaria)
    base = os.path.realpath(temporaria)
    with zipfile.ZipFile(arquivo_zip) as z:
        nomes = [n for n in z.namelist() if not n.endswith("/")]
        topos = set(n.split("/", 1)[0] for n in nomes)
        if len(topos) != 1:
            raise Parei(u"o pacote não tem uma pasta de topo só (achei %d)" % len(topos))
        for nome in nomes:
            rel = nome.split("/", 1)[1] if "/" in nome else ""
            if not rel:
                continue
            alvo = os.path.realpath(os.path.join(temporaria, rel))
            if not alvo.startswith(base + os.sep):
                raise Parei(u"o pacote tenta gravar fora da pasta: %s" % nome)
            if not os.path.isdir(os.path.dirname(alvo)):
                os.makedirs(os.path.dirname(alvo))
            with z.open(nome) as o, io.open(alvo, "wb") as d:
                shutil.copyfileobj(o, d)
    if os.path.isdir(pasta_final):
        shutil.rmtree(pasta_final)
    os.rename(temporaria, pasta_final)


def conferir_marca(pasta, nome):
    caminho = os.path.join(pasta, "componente.json")
    if not os.path.isfile(caminho):
        raise Parei(u"%s: o pacote não traz o componente.json" % nome)
    with io.open(caminho, encoding="utf-8-sig") as f:
        dados = json.load(f)
    if dados.get("suite") != SUITE or dados.get("nome") != nome:
        raise Parei(u"%s: a marca do pacote diz suite=%r, nome=%r"
                    % (nome, dados.get("suite"), dados.get("nome")))


def baixar_todos(destino, trava=TRAVA, origem=ORIGEM_PADRAO, tok=None,
                 avisar=print):
    lista = ler_trava(trava)
    sem_tag = [c["nome"] for c in lista if not c.get("tag")]
    if sem_tag:
        raise Parei(u"sem versão publicada na trava: %s. Publique o app e "
                    u"escreva a tag em build/componentes.lock.json."
                    % u", ".join(sem_tag))
    if not os.path.isdir(destino):
        os.makedirs(destino)
    feitos = []
    for c in lista:
        url = origem.format(repositorio=c["repositorio"], tag=c["tag"])
        tmp = tempfile.mkdtemp(prefix="_baixando_", dir=destino)
        try:
            arq = os.path.join(tmp, "pacote.zip")
            baixar(url, arq, tok)
            soma = sha256(arq)
            if c.get("sha256") and c["sha256"] != soma:
                raise Parei(u"%s %s: o sha256 baixado (%s) não é o da trava (%s)"
                            % (c["nome"], c["tag"], soma[:12], c["sha256"][:12]))
            if not c.get("sha256"):
                avisar(u"  AVISO: %s %s sem sha256 na trava; o baixado é %s"
                       % (c["nome"], c["tag"], soma))
            pasta = os.path.join(destino, c["nome"])
            extrair(arq, pasta)
            conferir_marca(pasta, c["nome"])
            feitos.append((c["nome"], c["tag"], soma))
            avisar(u"  %s %s  %s" % (c["nome"], c["tag"], soma[:12]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return feitos


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    destino = os.path.join(RAIZ, "_montagem", "componentes")
    trava, origem = TRAVA, ORIGEM_PADRAO
    i = 0
    while i < len(argv):
        if argv[i] == "--destino" and i + 1 < len(argv):
            destino = argv[i + 1]
            i += 1
        elif argv[i] == "--trava" and i + 1 < len(argv):
            trava = argv[i + 1]
            i += 1
        elif argv[i] == "--origem" and i + 1 < len(argv):
            origem = argv[i + 1]
            i += 1
        i += 1
    try:
        baixar_todos(os.path.abspath(destino), trava, origem,
                     token() if origem == ORIGEM_PADRAO else None)
    except Parei as e:
        print(u"PAREI: %s" % e)
        return 1
    print(u"\nPronto. Para empacotar com estes: %s=%s"
          % ("RADAI_COMPONENTES_DIR", os.path.abspath(destino)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
