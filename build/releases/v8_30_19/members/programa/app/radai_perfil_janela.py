"""Perfil privado da janela da suíte. Consultar o caminho nunca cria nem move arquivos."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


LEGADO = "radai_janela"
PASTA = "janela"
MARCA = ".local-suite-browser"


def _redirecionado(st):
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def _local(p):
    if not p or not p.is_absolute() or ".." in p.parts or str(p).startswith(("\\\\", "//")):
        return False
    if os.name == "nt" and ctypes.windll.kernel32.GetDriveTypeW(str(p.anchor)) not in (2, 3, 6):
        return False
    for parte in (*reversed(p.parents), p):
        try:
            if _redirecionado(parte.lstat()):
                return False
        except FileNotFoundError:
            break
        except OSError:
            return False
    return True


def caminhos(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    temp = amb.get("RADAI_TEMP_DO_USUARIO") or amb.get("TEMP") or amb.get("TMP")
    local = amb.get("LOCALAPPDATA")
    destinos = (Path(local) / "RADIOTERAPIA_AI" / PASTA if local else None,
                Path(temp) / LEGADO if temp else None)
    return tuple(p if _local(p) else None for p in destinos)


def _nosso(p):
    marca = p / MARCA
    try:
        return _local(marca) and marca.read_bytes() == b"LOCAL_SUITE\n"
    except OSError:
        return False


def _marcar(p):
    try:
        with (p / MARCA).open("xb") as f:
            f.write(b"LOCAL_SUITE\n")
    except FileExistsError:
        if not _nosso(p):
            raise OSError("A marca existente não pertence à suíte")


def perfil_da_janela(ambiente=None):
    novo, antigo = caminhos(ambiente)
    antigo_util = antigo and (not antigo.exists() or _legado_da_suite(antigo))
    if novo and novo.exists():
        p = novo if _nosso(novo) else (antigo if antigo_util else None)
    else:
        p = antigo if antigo_util and antigo.exists() else novo or (antigo if antigo_util else None)
    return str(p) if p else ""


def _legado_da_suite(p):
    estado = p / "Local State"
    return p.is_dir() and (_nosso(p) or (_local(estado) and estado.is_file()))


def perfis_conhecidos(ambiente=None):
    novo, antigo = caminhos(ambiente)
    perfis = []
    if novo and _nosso(novo):
        perfis.append(str(novo))
    if antigo and _legado_da_suite(antigo):
        perfis.append(str(antigo))
    return perfis


def em_uso(p):
    import radai_janela as j
    from radai_pulso import _processos
    api = j.plataforma()
    if api is None:
        return True
    processos = _processos()
    if not processos:
        return True
    for pid, _, nome in processos:
        if nome.lower() not in ("chrome.exe", "msedge.exe"):
            continue
        linha = api.linha_de_comando(pid)
        if not linha:
            if (p / "lockfile").exists():
                return True
            continue
        exato = j.perfil_comprovado_para_fechar(linha)
        if exato and Path(exato) == p:
            return True
    return False


def preparar(ambiente=None, ocupado=em_uso):
    novo, antigo = caminhos(ambiente)
    if not novo or novo.exists():
        return perfil_da_janela(ambiente)
    if antigo and antigo.exists():
        if not _legado_da_suite(antigo):
            antigo = None
        elif ocupado(antigo):
            return str(antigo)
    etapa = None
    try:
        novo.parent.mkdir(parents=True, exist_ok=True)
        if antigo and antigo.is_dir():
            # A troca de nome é atômica no mesmo volume. No outro volume,
            # a cópia só fica visível quando termina; a origem segue íntegra.
            if antigo.stat().st_dev == novo.parent.stat().st_dev:
                _marcar(antigo)
                antigo.rename(novo)
                return str(novo)
        etapa = Path(tempfile.mkdtemp(prefix=".janela-", dir=novo.parent))
        if antigo and antigo.is_dir():
            def ignorar_links(base, nomes):
                return [n for n in nomes if _redirecionado((Path(base) / n).lstat())]
            shutil.copytree(antigo, etapa, dirs_exist_ok=True, symlinks=True, ignore=ignorar_links)
            if ocupado(antigo):
                return str(antigo)
        _marcar(etapa)
        etapa.rename(novo)
        etapa = None
        return str(novo)
    except OSError:
        if novo and _nosso(novo):
            return str(novo)
        return str(antigo) if antigo else ""
    finally:
        if etapa is not None:
            shutil.rmtree(etapa, ignore_errors=True)


def remover(perfil, ambiente=None):
    # Só o desinstalador, depois da escolha "apagar itens externos".
    p = Path(perfil)
    if str(p) not in perfis_conhecidos(ambiente) or em_uso(p):
        return False
    # Python 3.8+ em Windows remove a junction, sem seguir seu destino.
    shutil.rmtree(p)
    return True


def argumentos_navegador(exe, url, p):
    return [exe, "--app=" + url, "--start-maximized", "--user-data-dir=" + p,
            "--no-first-run", "--no-default-browser-check", "--disable-background-mode"]


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).absolute().parent))
    cli = argparse.ArgumentParser()
    modos = cli.add_mutually_exclusive_group(required=True)
    modos.add_argument("--preparar", action="store_true")
    modos.add_argument("--abrir", nargs=2, metavar=("NAVEGADOR", "URL"))
    modos.add_argument("--listar", action="store_true")
    modos.add_argument("--remover")
    args = cli.parse_args()
    if args.abrir:
        import subprocess
        exe, url = args.abrir
        p = preparar()
        if not p or Path(exe).name.lower() not in ("chrome.exe", "msedge.exe"):
            sys.exit(1)
        argv = argumentos_navegador(exe, url, p)
        try:
            subprocess.Popen(argv, creationflags=getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0))
        except OSError:
            subprocess.Popen(argv)
    elif args.preparar:
        print(preparar())
    elif args.listar:
        print(json.dumps(perfis_conhecidos()))
    else:
        sys.exit(0 if remover(args.remover) else 1)
