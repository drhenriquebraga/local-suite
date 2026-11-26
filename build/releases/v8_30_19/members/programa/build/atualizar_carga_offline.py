"""Atualiza somente a extração temporária de um bundle portátil compatível."""
from pathlib import Path
import filecmp
import shutil
import sys
import tempfile

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
    try:
        galeria_publica.instalar(dados, carga/"data/fast_previews", fontes, None, galeria_publica.sem_rede,
                                 print, diretorios_de_pacotes=pacotes)
    except galeria_publica.GaleriaAusente as exc:
        if antiga == nova:
            raise ValueError("O bundle desta versão está sem a galeria pública íntegra. "
                             "Confira o pacote transferido.") from exc
        print("AVISO: " + str(exc), flush=True)
    perfil = cfg.perfil_do_destino(None,carga)
    ctx = {"bundle": carga, "versao": nova, "projeto": projeto, "produto": produto, "profile": perfil,
           "galeria_adiada": True}  # A galeria já foi conferida acima em modo offline.
    if antiga == nova:
        # Candidatas diferentes podem levar o mesmo número. O montador oficial
        # define a lista inteira do código. Pesos e preferências ficam fora dela.
        with tempfile.TemporaryDirectory(dir=extracao) as pasta:
            novo = Path(pasta)
            cfg._montar_codigo(dict(ctx, bundle=novo, instalar=True))
            for nome in ("entrega.txt", "VERSION.txt"):
                shutil.copy2(BUILD.parent/nome, novo/nome)
            filecmp.clear_cache()
            mudou = False
            for origem in novo.rglob("*"):
                if origem.is_file():
                    destino = carga / origem.relative_to(novo)
                    if destino.is_file() and filecmp.cmp(origem, destino, shallow=False):
                        continue
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(origem, destino)
                    mudou = True
            if not mudou and filecmp.cmp(BUILD.parent/"entrega.txt", extracao/"entrega.txt", shallow=False):
                return
    else:
        cfg._montar_codigo(ctx)
    cfg.validar_codigo_instalado(carga/"python/python.exe",carga)
    for destino in (carga,extracao):
        shutil.copy2(BUILD.parent/"entrega.txt",destino/"entrega.txt")
    shutil.copy2(BUILD.parent/"VERSION.txt",carga/"VERSION.txt")


if __name__=="__main__":
    atualizar(Path(sys.argv[1]), pasta_pacote=Path(sys.argv[2]) if len(sys.argv)>2 else None,
              estacao=Path(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3] else None)

