"""Carga de TC para o bólus. Confere os cabeçalhos antes de copiar ou decodificar."""
from contextlib import contextmanager
import os
import math
from pathlib import Path
from tempfile import TemporaryDirectory


_TAGS = ("SeriesInstanceUID", "Rows", "Columns", "NumberOfFrames", "SamplesPerPixel", "PatientPosition",
         "ImageOrientationPatient", "ImagePositionPatient")


def conferir_cancelamento(parar):
    if parar and parar():
        raise InterruptedError("Leitura interrompida.")


def posicao_axial(ds, orientacao):
    # A mesma projeção normal usada pelo leitor DICOM para ordenação física dos cortes.
    try:
        iop = tuple(float(x) for x in ds.ImageOrientationPatient)
        if len(iop) != 6 or (orientacao and any(abs(a-b) > 1e-6 for a,b in zip(iop,orientacao))):
            return None, orientacao
        a,b,c,d,e,f = iop
        normal = (b*f-c*e, c*d-a*f, a*e-b*d)
        if abs(sum(x*x for x in normal)-1) > 1e-3:
            return None, orientacao
        ipp = list(ds.ImagePositionPatient)
        if len(ipp) != 3:
            return None, orientacao
        z = sum(float(v)*n for v,n in zip(ipp,normal))
        return (z if math.isfinite(z) else None), iop
    except (AttributeError, ValueError, TypeError):
        return None, orientacao


def selecionar(pasta, uid, parar=None):
    import radai_bolus
    import engine
    import pydicom
    import SimpleITK as sitk

    conferir_cancelamento(parar)
    # Testar a forma curta só quando a API Windows recebeu uma forma estendida.
    # Enumerar com scandir permite interromper inclusive diretórios SMB numerosos.
    pasta = os.fspath(pasta)
    longa = pasta.startswith(engine._PREFIXO_LONGO)
    plana = engine._sem_prefixo_longo(pasta) if longa else pasta
    copiar = longa and not engine._componentes_intactos(plana)
    arquivos = []
    posicoes = []
    total = 0
    posicao = ""
    forma = None
    orientacao = None
    serie_uid = str(uid or "")
    with os.scandir(pasta) as entradas:
        for item in entradas:
            conferir_cancelamento(parar)
            if not item.is_file():
                continue
            caminho = item.path
            try:
                ds = pydicom.dcmread(caminho, force=True, stop_before_pixels=True, specific_tags=_TAGS)
            except (ValueError, EOFError, pydicom.errors.InvalidDicomError):
                continue
            chave = str(ds.get("SeriesInstanceUID") or "")
            if not chave or (serie_uid and chave != serie_uid):
                continue
            if not serie_uid and not (ds.get("Rows") and ds.get("Columns")):
                continue
            serie_uid = chave
            linhas = int(ds.get("Rows") or 0)
            colunas = int(ds.get("Columns") or 0)
            quadros = int(ds.get("NumberOfFrames", 1))
            if (min(linhas, colunas, quadros) <= 0 or int(ds.get("SamplesPerPixel", 1)) != 1
                    or (forma and forma != (linhas, colunas))):
                raise radai_bolus.Recusa("Não foi possível conferir as dimensões da TC.")
            forma = (linhas, colunas)
            total += linhas * colunas * quadros
            radai_bolus.conferir_tamanho_da_serie(total)
            z, orientacao = posicao_axial(ds, orientacao)
            posicoes.append(z)
            if longa and (len(os.path.join(plana,item.name)) > engine._TETO_DO_CAMINHO_PLANO
                          or not engine._componentes_intactos(item.name)):
                copiar = True
            arquivos.append(str(caminho))
            posicao = posicao or str(ds.get("PatientPosition", "")).strip().upper()
    conferir_cancelamento(parar)
    if not arquivos:
        raise radai_bolus.Recusa("Não foi possível conferir as dimensões da TC.")
    if longa and not copiar:
        try:
            copiar = not os.path.samefile(pasta, plana)
        except OSError:
            copiar = True
        if not copiar:
            arquivos = [engine._sem_prefixo_longo(a) for a in arquivos]
    if not copiar and len(arquivos) > 1:
        if None not in posicoes and len(set(posicoes)) == len(arquivos):
            arquivos = [a for _, a in sorted(zip(posicoes,arquivos))]
        else:
            # Geometria ausente/ambígua usa a mesma ordenação GDCM do motor.
            ordenados = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(plana,serie_uid)
            if len(ordenados) != len(arquivos):
                raise radai_bolus.Recusa("Não foi possível abrir todos os cortes da TC.")
            arquivos = list(ordenados)
    conferir_cancelamento(parar)
    return arquivos, total, posicao, serie_uid, copiar


@contextmanager
def arquivos_para_leitura(selecao, parar):
    import radai_bolus
    arquivos, _, _, uid, copiar = selecao
    if not copiar:
        yield arquivos
        return
    import engine
    import SimpleITK as sitk

    # GDCM não alcança alguns caminhos estendidos do Windows. Copiar somente a série conferida.
    with TemporaryDirectory(prefix="radai_bolus_") as stage:
        for i, origem in enumerate(arquivos):
            conferir_cancelamento(parar)
            destino = Path(stage) / ("%06d.dcm" % i)
            with open(origem, "rb") as entrada, destino.open("wb") as saida:
                while True:
                    conferir_cancelamento(parar)
                    bloco = entrada.read(1024 * 1024)
                    if not bloco:
                        break
                    saida.write(bloco)
            if not engine._tem_preambulo_dicom(destino):
                convertido = destino.with_suffix(".part")
                engine.copiar_como_parte_10(destino, convertido)
                os.replace(convertido, destino)
        conferir_cancelamento(parar)
        ordenados = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(stage, uid)
        if len(ordenados) != len(arquivos):
            raise radai_bolus.Recusa("Não foi possível abrir todos os cortes da TC.")
        yield ordenados


def ler_pixels(selecao, pasta, parar=None):
    import engine
    import SimpleITK as sitk

    with arquivos_para_leitura(selecao, parar) as arquivos:
        conferir_cancelamento(parar)
        engine._conferir_inclinacao(pasta, arquivos)
        conferir_cancelamento(parar)
        if len(arquivos) == 1:
            leitor = sitk.ImageFileReader()
            leitor.SetFileName(arquivos[0])
        else:
            leitor = sitk.ImageSeriesReader()
            leitor.SetFileNames(arquivos)
        if parar:
            leitor.AddCommand(sitk.sitkProgressEvent, lambda: leitor.Abort() if parar() else None)
        try:
            img = leitor.Execute()
        finally:
            leitor.RemoveAllCommands()
        conferir_cancelamento(parar)
        return img
