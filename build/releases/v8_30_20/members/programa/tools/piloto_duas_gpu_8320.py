"""Piloto opt-in de duas GPUs. Executa duas TCs anônimas no laboratório, fora da fila da estação."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))


def worker(pedido):
    cfg = json.loads(pedido.read_text(encoding="utf-8"))
    pasta = Path(cfg["work"])
    os.environ.update(RADAI_FILA_DIR=str(pasta.parent / "fila"), RADAI_CALIB_DIR=str(pasta / "calib"),
                      RADAI_REGISTRO_DIR=str(pasta / "historico"), RADAI_TMP=str(pasta / "temp"),
                      CUDA_DEVICE_ORDER="PCI_BUS_ID", CUDA_VISIBLE_DEVICES=str(cfg["gpu"]))
    import engine
    from radai_rotas import AguardarSozinha
    from radai_geom import Grade
    from radai_output import Saida
    import pydicom
    try:
        ref = engine.load_sitk(cfg["serie"])
        # Cada trabalho recebe uma única série, isolada em seu processo.
        uids = engine.sitk.ImageSeriesReader.GetGDCMSeriesIDs(cfg["serie"]) or ()
        if len(uids) != 1:
            raise ValueError("A pasta precisa conter exatamente uma série de TC.")
        uid = str(uids[0])
        j = engine._job_new()
        try:
            engine.registrar_serie(j,uid)
            # No serial o planejador usa a mesma placa física do ensaio paralelo.
            inventario = engine._vram_por_placa
            if not cfg["paralelo"]:
                def so_desta():
                    dados = inventario()
                    return dict(dados, placas=[p for p in dados["placas"] if p["indice"] == cfg["gpu"]])
                engine._vram_por_placa = so_desta
            else:
                engine._set(j,indice_piloto=cfg["gpu"])
            cruas = {}
            inicio = time.monotonic()
            engine.run_ts_task(ref,"total_v3","gpu",j,suavizar=False,cruas=cruas)
            fim_rede = time.monotonic()
            arr = cruas["total_v3"]._arr
            mapa = hashlib.sha256(memoryview(arr).cast("B")).hexdigest()
            saida = Saida(engine,cfg["serie"],pasta,"RS_RadAI_piloto.dcm",tasks=["total_v3"],
                          grade=Grade.de_sitk(ref),modalidade="CT")
            saida.uid_execucao = uid
            entrega = saida.full_e_oar(cruas, volume_hu=engine.sitk.GetArrayViewFromImage(ref),
                      modo="auto", esforco="maximo", arcos_costais_moose=False,
                      coronaria_rocards=False, reto_jhu=False)
            ds = pydicom.dcmread(entrega["entregue"])
            digest = hashlib.sha256()
            for roi in ds.ROIContourSequence:
                for contorno in roi.ContourSequence:
                    digest.update(repr(tuple(map(str,contorno.ContourData))).encode("ascii"))
            plano = engine._job(j)
            if not any(r.get("modo","").startswith("gpu") and r.get("indice") == cfg["gpu"]
                       for r in plano.get("planos",{}).values()):
                raise RuntimeError("A tarefa não executou numa GPU. Conferir disponibilidade antes de homologar.")
            resumo = dict(mapa_sha256=mapa,contornos_sha256=digest.hexdigest(),
                          gpu=cfg["gpu"],inferir_s=fim_rede-inicio,study_s=time.monotonic()-inicio)
            (pasta/"medidas.json").write_text(json.dumps(resumo,indent=2),encoding="utf-8")
        finally:
            engine._job_del(j)
    except AguardarSozinha:
        return 75
    return 0


def piloto(series, saida):
    import engine
    import radai_cache_tasks
    placas = [p for p in engine._vram_por_placa()["placas"] if p.get("uuid")]
    if len(placas) < 2:
        raise SystemExit("Piloto indisponível: a medição exige duas GPUs NVIDIA físicas identificadas.")
    if not radai_cache_tasks.conferir_pasta(saida)[0]:
        raise SystemExit("Escolha uma saída local, fora do acervo e das pastas sincronizadas.")
    if saida.exists() and any(saida.iterdir()):
        raise SystemExit("O diretório de destino deve estar vazio.")
    series = [str(p.resolve()) for p in series]
    if len(set(series)) != 2:
        raise SystemExit("Escolha duas séries independentes.")
    uids = [engine.sitk.ImageSeriesReader.GetGDCMSeriesIDs(p) or () for p in series]
    if any(len(u) != 1 for u in uids) or uids[0][0]==uids[1][0]:
        raise SystemExit("O piloto exige duas séries com UIDs distintos.")
    for modo in ("serial","paralelo"):
        tentativas = []
        for i, serie in enumerate(series):
            work = saida/modo/str(i)
            work.mkdir(parents=True)
            req = work/"pedido.json"
            req.write_text(json.dumps(dict(serie=serie, work=str(work), gpu=placas[i]["indice"],
                                           paralelo=modo=="paralelo")),encoding="utf-8")
            cmd = [sys.executable,"-B",str(Path(__file__).resolve()),"--worker",str(req)]
            proc = subprocess.Popen(cmd)
            tentativas.append((proc,cmd))
            if modo=="serial" and proc.wait():
                raise RuntimeError("A referência em série falhou.")
        retornos = [(proc.wait(),cmd) for proc,cmd in tentativas]
        for rc,cmd in retornos:
            if rc == 75:
                # D0 já foi condenado. A mesma task retoma em D1 com a outra encerrada.
                rc = subprocess.run(cmd).returncode
            if rc:
                raise RuntimeError("A execução do piloto falhou.")
    relatorio = []
    for i in range(2):
        medidas = [json.loads((saida/m/str(i)/"medidas.json").read_text(encoding="utf-8"))
                   for m in ("serial","paralelo")]
        if any(medidas[0][k]!=medidas[1][k] for k in ("mapa_sha256","contornos_sha256")):
            raise RuntimeError("As saídas do piloto divergiram. O pareamento não está homologado.")
        relatorio.append(dict(serial=medidas[0], paralelo=medidas[1]))
    (saida/"comparacao.json").write_text(json.dumps(relatorio,indent=2),encoding="utf-8")


if __name__=="__main__":
    if len(sys.argv)==3 and sys.argv[1]=="--worker":
        sys.exit(worker(Path(sys.argv[2])))
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("series", type=Path, nargs=2)
    p.add_argument("--saida", type=Path, required=True)
    args = p.parse_args()
    piloto(args.series,args.saida.resolve())

