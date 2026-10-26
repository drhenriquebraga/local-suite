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
LEIA_DA_TRAVA = (
    u"A versão de cada app que o empacotador baixa com --dos-repositorios. "
    u"A tag é a do repositório do app; arvore_sha256 é o sha256 do manifesto "
    u"da árvore extraída (uma linha «<sha256 do arquivo>  <caminho relativo, "
    u"sem a pasta de topo do zip>» por arquivo, em ordem, com os bytes como o "
    u"zip os entrega), e prova identidade com o que foi conferido (não "
    u"autenticidade). Os bytes do zip não entram: o GitHub não os promete "
    u"estáveis. Tag nula: o app ainda não publicou versão, e o download para. "
    u"Escrever: python build/baixar_componentes.py --travar <tag>.")


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


def manifesto_da_arvore(pasta):
    base = os.path.realpath(pasta)
    linhas = []
    for raiz, _dirs, arqs in os.walk(base):
        for a in arqs:
            cheio = os.path.join(raiz, a)
            rel = os.path.relpath(cheio, base).replace(os.sep, "/")
            linhas.append((rel, sha256(cheio)))
    linhas.sort()
    return u"".join(u"%s  %s\n" % (s, r) for r, s in linhas)


def arvore_sha256(pasta):
    return hashlib.sha256(manifesto_da_arvore(pasta).encode("utf-8")).hexdigest()


def _extrair_em(arquivo_zip, temporaria):
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


def extrair(arquivo_zip, pasta_final, conferir=None):
    temporaria = pasta_final + ".baixando"
    if os.path.isdir(temporaria):
        shutil.rmtree(temporaria)
    os.makedirs(temporaria)
    try:
        _extrair_em(arquivo_zip, temporaria)
        medida = conferir(temporaria) if conferir else None
    except Exception:
        shutil.rmtree(temporaria, ignore_errors=True)
        raise
    if os.path.isdir(pasta_final):
        shutil.rmtree(pasta_final)
    os.rename(temporaria, pasta_final)
    return medida


def conferir_marca(pasta, nome):
    caminho = os.path.join(pasta, "componente.json")
    if not os.path.isfile(caminho):
        raise Parei(u"%s: o pacote não traz o componente.json" % nome)
    with io.open(caminho, encoding="utf-8-sig") as f:
        dados = json.load(f)
    if dados.get("suite") != SUITE or dados.get("nome") != nome:
        raise Parei(u"%s: a marca do pacote diz suite=%r, nome=%r"
                    % (nome, dados.get("suite"), dados.get("nome")))


def _conferida(nome, esperada=None, tag=u""):
    def conferir(pasta):
        conferir_marca(pasta, nome)
        medida = arvore_sha256(pasta)
        if esperada is not None and medida != esperada:
            raise Parei(u"%s %s: a árvore extraída (%s) não é a da trava (%s)"
                        % (nome, tag, medida[:12], esperada[:12]))
        return medida
    return conferir


def baixar_todos(destino, trava=TRAVA, origem=ORIGEM_PADRAO, tok=None,
                 avisar=print):
    lista = ler_trava(trava)
    sem_tag = [c["nome"] for c in lista if not c.get("tag")]
    if sem_tag:
        raise Parei(u"sem versão publicada na trava: %s. Publique o app e "
                    u"escreva a tag em build/componentes.lock.json."
                    % u", ".join(sem_tag))
    sem_arvore = [c["nome"] for c in lista if not c.get("arvore_sha256")]
    if sem_arvore:
        raise Parei(u"sem a árvore conferida na trava: %s. Escreva-a com  "
                    u"python build/baixar_componentes.py --travar <tag>"
                    % u", ".join(sem_arvore))
    if not os.path.isdir(destino):
        os.makedirs(destino)
    feitos = []
    for c in lista:
        url = origem.format(repositorio=c["repositorio"], tag=c["tag"])
        tmp = tempfile.mkdtemp(prefix="_baixando_", dir=destino)
        try:
            arq = os.path.join(tmp, "pacote.zip")
            baixar(url, arq, tok)
            pasta = os.path.join(destino, c["nome"])
            medida = extrair(arq, pasta, _conferida(c["nome"], c["arvore_sha256"],
                                                    c["tag"]))
            feitos.append((c["nome"], c["tag"], medida))
            avisar(u"  %s %s  árvore %s" % (c["nome"], c["tag"], medida[:12]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return feitos


def escrever_trava(caminho, dados):
    partes = [u"{"]
    for k in dados:
        if k != "componentes":
            partes.append(u"  %s: %s," % (json.dumps(k), json.dumps(
                dados[k], ensure_ascii=False)))
    itens = [u"    " + json.dumps(c, ensure_ascii=False)
             for c in dados["componentes"]]
    partes.append(u'  "componentes": [\n' + u",\n".join(itens) + u"\n  ]")
    partes.append(u"}")
    parcial = caminho + ".parcial"
    with io.open(parcial, "w", encoding="utf-8") as f:
        f.write(u"\n".join(partes) + u"\n")
    os.replace(parcial, caminho)


def travar(tag, trava=TRAVA, origem=ORIGEM_PADRAO, tok=None, avisar=print):
    with io.open(trava, encoding="utf-8-sig") as f:
        dados = json.load(f)
    lista = ler_trava(trava)
    tmp = tempfile.mkdtemp(prefix="radai_travar_")
    novos = []
    try:
        for c in lista:
            arq = os.path.join(tmp, c["nome"] + ".zip")
            baixar(origem.format(repositorio=c["repositorio"], tag=tag), arq, tok)
            medida = extrair(arq, os.path.join(tmp, c["nome"]),
                             _conferida(c["nome"]))
            novo = dict((k, v) for k, v in c.items() if k != "sha256")
            novo.update(tag=tag, arvore_sha256=medida)
            novos.append(novo)
            avisar(u"  %s %s  árvore %s" % (c["nome"], tag, medida))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    dados["_leia"] = LEIA_DA_TRAVA
    dados["componentes"] = novos
    escrever_trava(trava, dados)
    return novos


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    destino = os.path.join(RAIZ, "_montagem", "componentes")
    trava, origem = TRAVA, ORIGEM_PADRAO
    tag_nova, sem_token = None, False
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
        elif argv[i] == "--travar" and i + 1 < len(argv):
            tag_nova = argv[i + 1]
            i += 1
        elif argv[i] == "--sem-token":
            sem_token = True
        i += 1
    tok = None if (sem_token or origem != ORIGEM_PADRAO) else token()
    try:
        if tag_nova:
            travar(tag_nova, trava, origem, tok)
            print(u"\nPronto: %s com a tag %s e a árvore de cada app."
                  % (trava, tag_nova))
            return 0
        baixar_todos(os.path.abspath(destino), trava, origem, tok)
    except Parei as e:
        print(u"PAREI: %s" % e)
        return 1
    print(u"\nPronto. Para empacotar com estes: %s=%s"
          % ("RADAI_COMPONENTES_DIR", os.path.abspath(destino)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
