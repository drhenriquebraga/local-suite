"""Valida o ZIP local e inicia o preparador offline após confirmação na estação."""
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import re
import stat
import shutil
import sys
from zipfile import ZipFile

import radai_atualizar as atualizador
from radai_version import _maior

AJUDA = "Traga o SETUP da Local Suite de outra máquina. O instalador verifica as dependências já instaladas."
CONFIRMAR = "Confirme a origem do instalador antes de atualizar."
INVALIDO = "Escolha um SETUP mais recente da Local Suite."
MAX_ZIP = 256 * 1024**2
FORMATO = re.compile(r"[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}\Z")
ENTREGA = "programa/entrega.txt"
OBRIGATORIOS = {ENTREGA, "programa/_requisitos.json", "programa/build/requisitos.py",
                "programa/packager/prepare.ps1", "programa/packager/UPDATE.ps1",
                "programa/app/radai_watcher.py"}


def envio_local(scope, headers):
    from urllib.parse import urlsplit
    locais = ("localhost", "127.0.0.1", "::1")
    origem = scope.get("scheme", "http") + "://" + headers.get("host", "")
    try:
        hostname = urlsplit(origem).hostname
    except ValueError:
        return False
    return (scope.get("method") == "POST" and (scope.get("client") or ("",))[0] in locais
            and hostname in locais and headers.get("origin") == origem
            and headers.get("sec-fetch-site") in (None, "same-origin")
            and headers.get("content-type", "").lower() == "application/zip"
            and headers.get("x-radai-setup") == "local-zip")


def conferir(arquivo, estacao, destino):
    from radai_lung_install import _inside
    with ZipFile(arquivo) as pacote:
        itens = pacote.infolist()
        expandido = sum(i.file_size for i in itens)
        if len(itens) > 20000 or expandido > 1024**3:
            raise ValueError(INVALIDO)
        if shutil.disk_usage(Path(destino).parent).free < expandido:
            raise OSError(errno.ENOSPC, "Não há espaço livre suficiente para copiar o ZIP local.")
        vistos = set()
        for i in itens:
            chave = i.filename.rstrip("/") if i.is_dir() else i.filename
            if ("\\" in chave or ":" in chave or chave.casefold() in vistos or i.flag_bits & 1
                    or stat.S_ISLNK(i.external_attr >> 16) or i.external_attr & 0x400):
                raise ValueError(INVALIDO)
            _inside(destino, chave)
            vistos.add(chave.casefold())
        if not OBRIGATORIOS.issubset(pacote.namelist()) or pacote.getinfo(ENTREGA).file_size > 16384:
            raise ValueError(INVALIDO)
        valores = dict(linha.split("=", 1) for linha in pacote.read(ENTREGA).decode("utf-8-sig").splitlines()
                       if "=" in linha and not linha.startswith("#"))
    nova = valores.get("VERSAO", "")
    atual = atualizador.campo_da_entrega(estacao, "VERSAO")
    if (valores.get("PROJETO") != "LOCAL_SUITE" or valores.get("PRODUTO") != "RADIOTERAPIA_AI_LOCAL_SUITE"
            or atualizador.campo_da_entrega(estacao, "PROJETO") != "LOCAL_SUITE"
            or not FORMATO.fullmatch(atual) or not FORMATO.fullmatch(nova) or not _maior(nova, atual)):
        raise ValueError(INVALIDO)
    return atual, nova


def confirmar(atual, nova, digest, idioma):
    import radai_janela
    import radai_phrases
    from radai_plugin_setup_i18n import TABELA
    idiomas = ["pt-BR", *radai_phrases.CODIGOS]
    indice = idiomas.index(idioma) if idioma in idiomas else 0
    aviso = next(linha[indice] for linha in TABELA if linha[0] == CONFIRMAR)
    janelas = radai_janela.guardadas()
    dono = ctypes.c_void_p(janelas[0]) if janelas else None
    # A confirmação local já existente protege a execução de SETUPs offline.
    # Topmost, em primeiro plano, "Não" por padrão e saída por inatividade.
    flags = 0x40000 | 0x10000 | 0x124
    texto = f"{aviso}\n\n{atual} → {nova}\nSHA-256: {digest}"
    return ctypes.windll.user32.MessageBoxTimeoutW(dono, texto, "Local Suite", flags, 0, 120000) == 6


def executar(estacao, pasta, digest):
    # pasta é criada pelo servidor em mkdtemp, nunca vem do pedido do navegador.
    copia = Path(pasta) / "setup.zip"
    destino = Path(pasta) / "extraido"
    try:
        with copia.open("rb") as arquivo:
            soma = hashlib.sha256()
            for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
                soma.update(bloco)
            if soma.hexdigest() != digest:
                raise ValueError(INVALIDO)
            arquivo.seek(0)
            atual, _ = conferir(arquivo, estacao, destino)
            arquivo.seek(0)
            atualizador.extrair(arquivo, destino)
        processo = atualizador.lancar_preparador(str(destino / "programa"), estacao, atual, offline=True)
        processo.wait()
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


if __name__ == "__main__":
    try:
        executar(*sys.argv[1:])
    except Exception:
        ctypes.windll.user32.MessageBoxW(None, atualizador.M_ABRIR, "Local Suite", 0x40010)
        sys.exit(1)
