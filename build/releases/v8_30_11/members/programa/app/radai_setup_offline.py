"""Abre o SETUP escolhido pelo operador no próprio Windows, sem baixar arquivos."""
import base64
import ctypes
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from zipfile import ZipFile

import radai_atualizar as atualizador
from radai_version import _maior

BOTAO = "Escolher ZIP do instalador"
AJUDA = "Traga o SETUP da Local Suite de outra máquina. O instalador verifica as dependências já instaladas."
CONFIRMAR = "Confirme a origem do instalador antes de atualizar."
INVALIDO = "Escolha um SETUP mais recente da Local Suite."
FORMATO = re.compile(r"[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}\Z")
ENTREGA = "programa/entrega.txt"
OBRIGATORIOS = {ENTREGA, "programa/_requisitos.json", "programa/build/requisitos.py",
                "programa/packager/prepare.ps1", "programa/packager/UPDATE.ps1",
                "programa/app/radai_watcher.py"}


def conferir(arquivo, estacao, destino):
    from radai_lung_install import _inside
    with ZipFile(arquivo) as pacote:
        itens = pacote.infolist()
        if len(itens) > 20000 or sum(i.file_size for i in itens) > 1024**3:
            raise ValueError(INVALIDO)
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


def escolher(titulo):
    # A API não recebe caminhos, ZIPs nem argumentos de PowerShell do navegador.
    script = """Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Title = $env:RADAI_TITULO_ZIP
$d.Filter = 'Local Suite SETUP (*.zip)|*.zip'
$d.CheckFileExists = $true
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
try {
    if ($d.ShowDialog($owner) -eq 'OK') {
        [Console]::Write([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($d.FileName)))
    }
} finally { $d.Dispose(); $owner.Dispose() }
"""
    run = subprocess.run([atualizador.powershell(), "-NoProfile", "-STA", "-EncodedCommand",
                          base64.b64encode(script.encode("utf-16le")).decode("ascii")],
                         capture_output=True, check=True, creationflags=atualizador.CREATE_NO_WINDOW,
                         env=dict(os.environ, RADAI_TITULO_ZIP=titulo))
    return base64.b64decode(run.stdout, validate=True).decode("utf8")


def executar(estacao, idioma):
    import radai_phrases
    from radai_plugin_setup_i18n import TABELA
    idiomas = ["pt-BR", *radai_phrases.CODIGOS]
    indice = idiomas.index(idioma) if idioma in idiomas else 0
    traducoes = {linha[0]: linha[indice] for linha in TABELA if len(linha) > indice}
    def t(texto):
        return traducoes.get(texto, texto)
    def avisar(texto, flags):
        return ctypes.windll.user32.MessageBoxW(None, texto, "Local Suite", flags | 0x40000)
    try:
        caminho = escolher(t(BOTAO))
        if not caminho:
            return
        with tempfile.TemporaryDirectory(prefix="local-suite-setup-") as temp:
            # Uma cópia privada congela os bytes mesmo se o pendrive for removido.
            copia = Path(temp) / "setup.zip"
            soma = hashlib.sha256()
            with open(caminho, "rb") as original:
                if not 0 < os.fstat(original.fileno()).st_size <= 256 * 1024**2:
                    raise ValueError(INVALIDO)
                with copia.open("xb") as saida:
                    for bloco in iter(lambda: original.read(1024 * 1024), b""):
                        if saida.tell() + len(bloco) > 256 * 1024**2:
                            raise ValueError(INVALIDO)
                        soma.update(bloco)
                        saida.write(bloco)
            destino = Path(temp) / "extraido"
            atual, nova = conferir(copia, estacao, destino)
            if avisar(f"{t(CONFIRMAR)}\n\n{atual} → {nova}\n{Path(caminho).name}\nSHA-256: {soma.hexdigest()}", 0x124) != 6:
                return
            atualizador.extrair(copia, destino)
            processo = atualizador.lancar_preparador(str(destino / "programa"), estacao, atual, offline=True)
            processo.wait()
    except Exception as erro:
        detalhe = str(erro)
        avisar(t(INVALIDO) + ("\n\n" + detalhe if detalhe and detalhe != INVALIDO else ""), 0x10)


if __name__ == "__main__":
    executar(sys.argv[1], sys.argv[2])

