"""Transporte opcional dos pesos ROCardS e de wheels oficiais CPython 3.10 Windows x64."""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import zipfile

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))  # O Python embutido usa um ._pth isolado.
import radai_models

ARQUIVO = "Coronarias-ROCardS-win64.zip"
WHEELS = APP / "data" / "wheels-rocards-win64.json"
REQUISITOS = APP / "data" / "requirements-rocards.txt"


def _catalogo():
    modelo = radai_models.MODELOS["rocards_lad"]
    arquivos = {rel: (size, modelo["sha256"][rel], radai_models.url_do_arquivo(modelo, rel))
                for rel, size in modelo["arquivos"]}
    wheels = json.loads(WHEELS.read_text(encoding="utf-8"))
    pins = [s.strip() for s in REQUISITOS.read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.startswith("#")]
    if [w["requisito"] for w in wheels] != pins:
        raise ValueError("O catálogo de wheels não corresponde à versão do runtime da suíte.")
    for w in wheels:
        arquivos["wheels/" + w["arquivo"]] = w["bytes"], w["sha256"], w["url"]
    return arquivos


def _copiar(fonte, alvo, tamanho, esperado):
    sha = hashlib.sha256()
    total = 0
    while True:
        bloco = fonte.read(min(1024 * 1024, tamanho - total + 1))
        if not bloco:
            break
        total += len(bloco)
        if total > tamanho:
            raise ValueError("Recurso maior que o publicado.")
        alvo.write(bloco)
        sha.update(bloco)
    if total != tamanho or sha.hexdigest() != esperado:
        raise ValueError("Tamanho ou SHA-256 diferente do catálogo oficial.")


def _obter(rel, recurso, bases, temporario):
    tamanho, soma, url = recurso
    for base in bases:
        arq = base / rel
        if not arq.is_file() or arq.stat().st_size != tamanho:
            continue
        try:
            with arq.open("rb") as fonte, temporario.open("wb") as alvo:
                _copiar(fonte, alvo, tamanho, soma)
            return
        except (OSError, ValueError):
            continue
    for tentativa in range(3):
        try:
            with urlopen(url, timeout=90) as fonte, temporario.open("wb") as alvo:
                _copiar(fonte, alvo, tamanho, soma)
            return
        except OSError:
            if tentativa == 2:
                raise


def montar(saida, base=None):
    pasta = Path(saida).resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    bases = [radai_models.pasta_do_modelo("rocards_lad")]
    if base:
        base = Path(base)
        bases[:0] = [base, base / "rocards", base / "modelos" / "rocards",
                     base / "programa" / "app" / "modelos" / "rocards"]
    catalogo = _catalogo()
    with tempfile.TemporaryDirectory(prefix=".pacote-coronarias-", dir=pasta) as temp:
        temp = Path(temp)
        pacote = temp / ARQUIVO
        with zipfile.ZipFile(pacote, "w", allowZip64=False) as z:
            for n, (rel, recurso) in enumerate(catalogo.items(), 1):
                print(f"{n}/{len(catalogo)} {rel}", flush=True)
                _obter(rel, recurso, bases, temp / "recurso")
                z.write(temp / "recurso", rel, compress_type=zipfile.ZIP_STORED)
        os.replace(pacote, pasta / ARQUIVO)
    return pasta / ARQUIVO


def _conferir_diretorio(fonte, catalogo):
    # O ZipFile cria um objeto por entrada ao abrir. Confira a contagem e o
    # tamanho do diretório antes de permitir que ele aloque memória para isso.
    tamanho = fonte.seek(0, os.SEEK_END)
    if tamanho < 22 or tamanho > sum(v[0] for v in catalogo.values()) + 1024 * 1024:
        raise ValueError("Tamanho inválido para o pacote de Coronárias.")
    fonte.seek(-22, os.SEEK_END)
    marca, disco, disco_ini, aqui, total, central, offset, comentario = struct.unpack("<4s4H2LH", fonte.read(22))
    if (marca != b"PK\x05\x06" or disco or disco_ini or comentario or aqui != len(catalogo)
            or total != aqui or central > aqui * 1024 or offset + central + 22 != tamanho):
        raise ValueError("Diretório ZIP incompatível com o pacote oficial.")
    fonte.seek(0)


def _extrair(arquivo, novo, catalogo):
    with open(arquivo, "rb") as fonte:
        _conferir_diretorio(fonte, catalogo)
        with zipfile.ZipFile(fonte) as z:
            infos = z.infolist()
            if (len(infos) != len(catalogo) or {i.orig_filename for i in infos} != set(catalogo)
                    or any(i.filename != i.orig_filename for i in infos)):
                raise ValueError("Arquivos inesperados, ausentes ou repetidos no pacote.")
            for info in infos:
                rel = info.filename
                tamanho, soma, _ = catalogo[rel]
                tipo = stat.S_IFMT(info.external_attr >> 16)
                if (info.file_size != tamanho or tipo not in (0, stat.S_IFREG)
                        or info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                    raise ValueError("Entrada ZIP incompatível: " + rel)
                alvo = novo / rel
                alvo.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as entrada, alvo.open("xb") as saida:
                    _copiar(entrada, saida, tamanho, soma)


def _payload(nome):
    partes = PurePosixPath(nome).parts
    if not partes or nome.startswith("/") or ".." in partes or "\\" in nome or ":" in nome:
        raise ValueError("Caminho inválido no índice de um wheel.")
    if partes[0].endswith(".data"):
        if partes[1] in ("scripts", "headers"):
            return None  # Não participam dos imports da rede.
        if partes[1] not in ("purelib", "platlib", "data"):
            raise ValueError("Área de instalação de wheel desconhecida.")
        partes = partes[2:]
    return Path(*partes)


def _reaproveitar(runtime, wheels, alvo):
    """Reconstrói um runtime limpo com os bytes locais atestados pelos RECORDs oficiais."""
    if not runtime.is_dir():
        return False
    try:
        for wheel in sorted(wheels.glob("*.whl")):
            with zipfile.ZipFile(wheel) as z:
                indice, = [i for i in z.namelist() if i.count("/") == 1 and i.endswith(".dist-info/RECORD")]
                registros = z.read(indice)
                for nome, hash_wheel, tamanho in csv.reader(io.StringIO(registros.decode("utf8"))):
                    destino = _payload(nome)
                    if destino is None or nome == indice:
                        continue
                    metodo, codigo = hash_wheel.split("=", 1)
                    if metodo != "sha256":
                        raise ValueError("Algoritmo de hash de wheel incompatível.")
                    digest = base64.urlsafe_b64decode(codigo + "==").hex()
                    copia = alvo / destino
                    copia.parent.mkdir(parents=True, exist_ok=True)
                    with (runtime / destino).open("rb") as fonte, copia.open("wb") as gravar:
                        _copiar(fonte, gravar, int(tamanho), digest)
                (alvo / indice).write_bytes(registros)
        return True
    except (OSError, ValueError, csv.Error):
        # A projeção parcial contém apenas arquivos temporários e não é executada.
        if alvo.exists():
            shutil.rmtree(alvo)
        return False


def _runtime(wheels, anterior, alvo):
    from radai_rocards_dependencies import RECIBO, verificar
    if not _reaproveitar(anterior, wheels, alvo):
        dados = json.loads(WHEELS.read_text(encoding="utf8"))
        lista = wheels.parent / "requirements-verificados.txt"
        lista.write_text("".join(f"{(wheels / w['arquivo']).resolve().as_uri()} --hash=sha256:{w['sha256']}\n"
                                 for w in dados), encoding="ascii")
        subprocess.run([sys.executable, "-B", "-m", "pip", "--isolated", "install",
                        "--no-index", "--require-hashes", "--no-deps", "--ignore-installed",
                        "--no-build-isolation", "--only-binary=:all:", "--disable-pip-version-check",
                        "--no-compile", "--no-input", "--no-cache-dir",
                        "--target", str(alvo), "-r", str(lista)], check=True, stdin=subprocess.DEVNULL)
    (alvo / RECIBO).write_text(hashlib.sha256(REQUISITOS.read_bytes()).hexdigest(), encoding="ascii")
    verificar(sys.executable, alvo)


_PARTES = ("models", "runtime")


def recuperar(destino):
    """Reverte uma substituição interrompida. O chamador mantém a trava do modelo."""
    backup = destino / ".transferencia-offline"
    if not backup.exists():
        return
    pendente = backup / "pendente.json"
    if pendente.exists():
        originais = json.loads(pendente.read_text(encoding="utf8"))
        if not isinstance(originais, list) or not set(originais) <= set(_PARTES):
            raise ValueError("Registro de recuperação do plugin inválido.")
        for nome in reversed(_PARTES):
            anterior, atual = backup / nome, destino / nome
            if anterior.exists() or nome not in originais:
                if atual.exists():
                    atual.rename(backup / ("descartar-" + nome))
                if anterior.exists():
                    anterior.rename(atual)
        pendente.rename(backup / "revertido")
    if any((backup / nome).exists() for nome in ("concluido", "revertido")) or not any(backup.iterdir()):
        shutil.rmtree(backup)
    else:
        raise ValueError("A cópia de recuperação do plugin precisa ser conferida.")


def _publicar(novo, destino):
    backup = destino / ".transferencia-offline"
    backup.mkdir()
    pendente = backup / "pendente.json"
    originais = [nome for nome in _PARTES if (destino / nome).exists()]
    # Escrever fora do diretório de recuperação antes do rename evita um
    # recibo parcial se a máquina desligar durante a gravação.
    inicio = novo / "pendente.json"
    inicio.write_text(json.dumps(originais), encoding="utf8")
    inicio.rename(pendente)
    try:
        for nome in _PARTES:
            if nome in originais:
                (destino / nome).rename(backup / nome)
            (novo / nome).rename(destino / nome)
        pendente.rename(backup / "concluido")
    except BaseException:
        recuperar(destino)
        raise
    # DLLs em uso em uma estação previamente ativa podem retardar a limpeza.
    # O marcador já confirma que a nova geração passou na prova completa.
    shutil.rmtree(backup, ignore_errors=True)


def instalar(arquivo_zip):
    from radai_archive import _travar_indice
    destino = radai_models.pasta_do_modelo("rocards_lad", criar=True)
    with _travar_indice(destino / "preparo"):
        recuperar(destino)
        with tempfile.TemporaryDirectory(prefix=".importacao-", dir=destino) as temp:
            novo = Path(temp)
            _extrair(arquivo_zip, novo, _catalogo())
            _runtime(novo / "wheels", destino / "runtime", novo / "runtime")
            _publicar(novo, destino)
    return destino


def _main():
    cli = argparse.ArgumentParser(description=__doc__)
    cmd = cli.add_subparsers(dest="acao", required=True)
    gerar = cmd.add_parser("montar")
    gerar.add_argument("--saida", required=True)
    gerar.add_argument("--base")
    args = cli.parse_args()
    print(montar(args.saida, args.base), flush=True)


if __name__ == "__main__":
    _main()
