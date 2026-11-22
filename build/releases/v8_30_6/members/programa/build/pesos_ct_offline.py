"""Monta ou importa os checkpoints de resolução de TC e o localizador do ULTRA."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

BUILD = Path(__file__).resolve().parent
sys.path[:0] = [str(BUILD), str(BUILD.parent / "app")]
import artefatos
import radai_tasks


def origens():
    for mm, dataset in radai_tasks.DATASETS_RESOLUCAO_CT.items():
        nome = "Dataset%d_TotalSegmentator_total_%dmm_1559subj.zip" % (dataset, mm)
        yield mm, nome, artefatos.PESOS_TS[nome]
    nome = 'Dataset299_body_1559subj.zip'
    yield 'body_ultra', nome, artefatos.PESOS_TS[nome]


def exigir(perfil, pesos):
    if perfil == 'body_ultra':
        return radai_tasks.exigir_peso_body_ultra(pesos)
    return radai_tasks.exigir_peso_resolucao_ct(perfil, pesos)


def conferir(arquivo):
    ok, msg, _ = artefatos.conferir_peso_ts(str(arquivo), arquivo.name, arquivo.stem)
    if not ok:
        raise ValueError(msg)


def importar(origem, pesos):
    pesos.mkdir(parents=True, exist_ok=True)
    for mm, nome, _ in origens():
        try:
            exigir(mm, pesos)
            print(f"{nome} OK", flush=True)
            continue
        except RuntimeError:
            pass
        arquivo = origem / nome
        conferir(arquivo)
        with tempfile.TemporaryDirectory(prefix=".import-ct-", dir=pesos) as tmp:
            novo = Path(tmp)
            with zipfile.ZipFile(arquivo) as z:
                z.extractall(novo, [m for m in z.infolist() if m.filename.startswith(arquivo.stem + "/")])
            exigir(mm, novo)
            destino = pesos / arquivo.stem
            reserva = novo / "anterior"
            if destino.exists():
                destino.rename(reserva)
            try:
                (novo / arquivo.stem).rename(destino)
            except OSError:
                if reserva.exists() and not destino.exists():
                    reserva.rename(destino)
                raise
        print(f"{nome} OK", flush=True)


def montar(origem, destino):
    if destino.exists():
        raise FileExistsError(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fontes = list(origens())
    for _, nome, _ in fontes:
        conferir(origem / nome)
    with tempfile.TemporaryDirectory(dir=destino.parent, prefix=".peso-ct-") as tmp:
        pacote = Path(tmp) / "suplemento.zip"
        with zipfile.ZipFile(pacote, "w", compression=zipfile.ZIP_STORED) as z:
            for _, nome, _ in fontes:
                z.write(origem / nome, nome)
            for modulo in (artefatos, radai_tasks):
                script = Path(modulo.__file__)
                z.write(script, script.name)
            z.write(__file__, "pesos_ct_offline.py")
            z.write(BUILD.parent / "LICENSE", "LICENSE")
            z.write(BUILD.parent / "NOTICE", "NOTICE")
            z.write(BUILD.parent / "app/data/ajuda-tasks/LICENSE-TotalSegmentator.txt", "LICENSE-TotalSegmentator.txt")
            z.writestr("origens.json", json.dumps({
                nome: dict(tabela, url="https://github.com/wasserth/TotalSegmentator/releases/download/"
                           + tabela["release"] + "/" + nome)
                for _, nome, tabela in fontes}, indent=2))
            z.writestr("IMPORTAR.cmd", (
                '@echo off\r\nsetlocal\r\nset "station=%~1"\r\n'
                'if not defined station set "station=C:\\RADIOTERAPIA_AI\\LOCAL_SUITE"\r\n'
                'if not exist "%station%\\python\\python.exe" (echo Provide the Local Suite installation folder. & pause & exit /b 2)\r\n'
                '"%station%\\python\\python.exe" -B "%~dp0pesos_ct_offline.py" importar --origem "%~dp0." --destino "%station%\\ts_weights"\r\n'
                'set "result=%ERRORLEVEL%"\r\npause\r\nexit /b %result%\r\n'))
            z.writestr("LEIA-ME.txt", (
                "Local Suite - TotalSegmentator v3 CT de 3 e 6 mm e localizador corporal ULTRA de 1,5 mm\r\n\r\n"
                "Para atualizar uma estacao: extraia o suplemento em uma pasta, execute IMPORTAR.cmd e depois "
                "o SETUP da nova versao. Em instalacao personalizada, passe a pasta da suite como argumento a IMPORTAR.cmd.\r\n"
                "Para montar um BUNDLE completo: copie os tres ZIPs Dataset para cache/pesos_ts dentro da pasta de "
                "trabalho do preparador antes de clicar em montar. O instalador confere o CRC e as somas SHA-256 registradas.\r\n"
                "O suplemento requer uma instalacao/base compativel. A verificacao do SETUP inclui bibliotecas, "
                "runtime e demais modelos. Pesos originais e termos: veja origens.json e LICENSE-TotalSegmentator.txt.\r\n"))
        with zipfile.ZipFile(pacote) as z:
            if z.testzip():
                raise ValueError("CRC inválido no suplemento")
        pacote.rename(destino)
    sha = hashlib.sha256()
    with destino.open("rb") as f:
        for bloco in iter(lambda: f.read(4 << 20), b""):
            sha.update(bloco)
    print(destino, destino.stat().st_size, sha.hexdigest(), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("montar", "importar"))
    parser.add_argument("--origem", type=Path, required=True)
    parser.add_argument("--destino", type=Path, required=True)
    args = parser.parse_args()
    (montar if args.acao == "montar" else importar)(args.origem.resolve(), args.destino.resolve())
