"""Atualiza somente a extração temporária de um bundle portátil compatível."""
from pathlib import Path
import shutil
import sys

BUILD = Path(__file__).resolve().parent
sys.path.insert(0,str(BUILD))
import configurar_ambiente as cfg
import requisitos
import galeria_publica


def atualizar(extracao, *, pasta_pacote=None, estacao=None):
    extracao = Path(extracao).resolve()
    projeto, antiga, _ = cfg.ler_entrega(extracao)
    suite, nova, produto = cfg.ler_entrega(BUILD.parent)
    if projeto != suite or not (extracao/"INSTALL.ps1").is_file():
        raise ValueError("A extração não corresponde a um bundle da Local Suite.")
    carga = extracao/projeto
    if antiga != nova:
        compat, motivos = requisitos.comparar_estacao(str(BUILD.parent), str(carga))
        if not compat:
            raise ValueError("Bundle incompatível com o SETUP. " + " ".join(motivos))
    dados = BUILD.parent / "app/data"
    fontes = [dados / "fast_previews"]
    diretorios = [p for p in (pasta_pacote, BUILD.parent, BUILD.parent.parent) if p]
    pacotes = [d for p in diretorios for d in (Path(p), Path(p)/"recursos")]
    if estacao:
        fontes.append(Path(estacao) / "data/fast_previews")
        pacotes.append(Path(estacao) / "_instalacao/cache")
    adiada = False
    try:
        galeria_publica.instalar(dados, carga/"data/fast_previews", fontes, None, galeria_publica.sem_rede,
                                 print, diretorios_de_pacotes=pacotes)
    except galeria_publica.GaleriaAusente as exc:
        if antiga == nova:
            raise ValueError("O bundle desta versão está sem a galeria pública íntegra. "
                             "Confira o pacote transferido.") from exc
        adiada = True
        print("AVISO: " + str(exc), flush=True)
    if antiga == nova:
        return
    perfil = cfg.perfil_do_destino(None,carga)
    cfg._montar_codigo({"bundle":carga,"versao":nova,"projeto":projeto,"produto":produto,"profile":perfil,
                        "galeria_adiada":adiada})
    cfg.validar_codigo_instalado(carga/"python/python.exe",carga)
    for destino in (carga,extracao):
        shutil.copy2(BUILD.parent/"entrega.txt",destino/"entrega.txt")
    shutil.copy2(BUILD.parent/"VERSION.txt",carga/"VERSION.txt")


if __name__=="__main__":
    atualizar(Path(sys.argv[1]), pasta_pacote=Path(sys.argv[2]) if len(sys.argv)>2 else None,
              estacao=Path(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3] else None)

