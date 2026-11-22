"""Atualiza somente a extração temporária de um bundle portátil compatível."""
from pathlib import Path
import shutil
import sys

BUILD = Path(__file__).resolve().parent
sys.path.insert(0,str(BUILD))
import configurar_ambiente as cfg
import requisitos


def atualizar(extracao):
    extracao = Path(extracao).resolve()
    projeto, antiga, _ = cfg.ler_entrega(extracao)
    suite, nova, produto = cfg.ler_entrega(BUILD.parent)
    if projeto != suite or not (extracao/"INSTALL.ps1").is_file():
        raise ValueError("A extração não corresponde a um bundle da Local Suite.")
    carga = extracao/projeto
    if antiga == nova:
        return
    compat, motivos = requisitos.comparar(requisitos.ler(str(carga)), requisitos.calcular(str(BUILD.parent)))
    if not compat:
        raise ValueError("Bundle incompatível com o SETUP. " + " ".join(motivos))
    perfil = cfg.perfil_do_destino(None,carga)
    cfg._montar_codigo({"bundle":carga,"versao":nova,"projeto":projeto,"produto":produto,"profile":perfil})
    cfg.validar_codigo_instalado(carga/"python/python.exe",carga)
    for destino in (carga,extracao):
        shutil.copy2(BUILD.parent/"entrega.txt",destino/"entrega.txt")
    shutil.copy2(BUILD.parent/"VERSION.txt",carga/"VERSION.txt")


if __name__=="__main__":
    atualizar(Path(sys.argv[1]))

