import hashlib
import itertools
import os
from pathlib import Path
import tempfile
import threading
from contextlib import contextmanager

TASK = "lung_nodules"
MAX_FASES = 20
MAX_BYTES = 512 * 1024 * 1024
DONO = "lung"


def pasta_valida(valor, cfg=None):
    if not isinstance(valor, str) or not os.path.isabs(valor):
        raise ValueError("Escolha uma pasta absoluta da estação.")
    pasta = os.path.realpath(valor)
    import radai_batch
    if radai_batch._destino_pode_receber_paciente(pasta):
        raise ValueError("Escolha uma pasta de trabalho fora do programa e de pastas sincronizadas.")
    if not os.path.isdir(pasta):
        raise ValueError("A pasta não está disponível.")
    return pasta


def varrer(pasta, cfg):
    import radai_batch
    series = radai_batch.varrer(pasta_valida(pasta, cfg), modalidades=("CT",),
                               min_cortes=max(5, int(cfg.get("min_cortes", 20))),
                               incluir_zips=False)
    return [metadados_respiratorios(s) for s in series if s.get("axial") and s.get("uid")]


def metadados_respiratorios(s):
    import radai_lung_4d as four
    import radai_batch
    arquivos = radai_batch._so_da_serie([str(p) for p in Path(s['pasta']).iterdir() if p.is_file()], s['uid'], 'CT')
    s = dict(s, fase_respiratoria=None)
    if arquivos:
        s['fase_respiratoria'] = four.fase_respiratoria(ler_ct(arquivos[0]))
    return s


def resolver_series(linhas, cfg):
    import radai_batch
    if not isinstance(linhas, list) or len(linhas) > 500:
        raise ValueError("Seleção de séries inválida.")
    resolved, seen = [], set()
    for item in linhas:
        if not isinstance(item, dict) or not item.get('uid'):
            continue
        pasta = pasta_valida(item.get('pasta'), cfg)
        uid = str(item['uid'])
        if uid in seen:
            continue
        files = radai_batch._so_da_serie([str(p) for p in Path(pasta).iterdir() if p.is_file()], uid, 'CT')
        if len(files) < max(5, int(cfg.get('min_cortes', 20))):
            continue
        ds = ler_ct(files[0])
        s = dict(uid=uid, pasta=pasta, cortes=len(files), modalidade='CT', axial=True,
                 pid=str(ds.get('PatientID', '')), estudo=str(ds.StudyInstanceUID),
                 desc=str(ds.get('SeriesDescription', '')), numero=int(ds.get('SeriesNumber', 0)))
        _inspecionar(s)
        resolved.append(metadados_respiratorios(s))
        seen.add(uid)
    return resolved


def ler_ct(caminho, pixels=False):
    import numpy as np
    import pydicom
    from pydicom.errors import InvalidDicomError
    import radai_dicom
    if not radai_dicom.vale_abrir(str(caminho))[0]:
        raise ValueError("Arquivo auxiliar não é uma imagem de TC.")
    try:
        ds = pydicom.dcmread(caminho, stop_before_pixels=not pixels)
    except InvalidDicomError:
        ds = pydicom.dcmread(caminho, stop_before_pixels=not pixels, force=True)
    try:
        iop = np.asarray(ds.ImageOrientationPatient, dtype=float)
        pos = np.asarray(ds.ImagePositionPatient, dtype=float)
        spacing = np.asarray(ds.PixelSpacing, dtype=float)
        valid = (str(ds.SOPClassUID) == "1.2.840.10008.5.1.4.1.1.2"
                 and str(ds.Modality) == "CT"
                 and all(pydicom.uid.UID(str(ds.get(k, ""))).is_valid for k in
                         ("SOPInstanceUID", "SeriesInstanceUID", "StudyInstanceUID", "FrameOfReferenceUID"))
                 and 0 < int(ds.Rows) <= 8192 and 0 < int(ds.Columns) <= 8192
                 and iop.shape == (6,) and pos.shape == (3,) and spacing.shape == (2,)
                 and np.isfinite(iop).all() and np.isfinite(pos).all()
                 and np.isfinite(spacing).all() and (spacing > 0).all()
                 and np.allclose(iop.reshape(2, 3) @ iop.reshape(2, 3).T, np.eye(2), atol=1e-4))
    except (AttributeError, ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError("Arquivo sem identificação ou geometria válida de TC axial clássica.")
    return ds


def _inspecionar(s):
    import numpy as np
    import pydicom
    import radai_batch

    pasta = pasta_valida(s["pasta"])
    arquivos = radai_batch._so_da_serie(
        [str(p) for p in sorted(Path(pasta).iterdir()) if p.is_file()], s["uid"], "CT")
    if len(arquivos) != s["cortes"] or len(arquivos) < 5:
        raise ValueError("A série mudou ou está incompleta. Carregue-a novamente.")
    ident = set()
    instancias = set()
    geometrias = set()
    posicoes = []
    tags = ("PatientID", "IssuerOfPatientID", "StudyInstanceUID", "SeriesInstanceUID",
            "FrameOfReferenceUID", "SOPInstanceUID", "SOPClassUID", "Rows", "Columns",
            "PixelSpacing", "ImageOrientationPatient", "ImagePositionPatient")
    hash_ = hashlib.sha256()
    hashes_instancias = []
    for f in arquivos:
        ds = ler_ct(f)
        ident.add(tuple(str(ds.get(t, "")) for t in tags[:5]))
        iop = np.array(ds.ImageOrientationPatient, dtype=float)
        pos = np.array(ds.ImagePositionPatient, dtype=float)
        espac = tuple(float(v) for v in ds.PixelSpacing)
        if (str(ds.SOPClassUID) != "1.2.840.10008.5.1.4.1.1.2"
                or not np.isfinite(iop).all() or not np.isfinite(pos).all()
                or len(espac) != 2 or not np.isfinite(espac).all() or min(espac) <= 0
                or not np.allclose(iop.reshape(2, 3) @ iop.reshape(2, 3).T, np.eye(2), atol=1e-4)):
            raise ValueError("Geometria de TC axial clássica inválida ou não suportada.")
        geometrias.add((int(ds.Rows), int(ds.Columns), espac, tuple(iop)))
        posicoes.append(pos)
        instancias.add(str(ds.SOPInstanceUID))
        with open(f, "rb") as entrada:
            hash_instancia = hashlib.sha256()
            for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
                hash_instancia.update(bloco)
            hashes_instancias.append((str(ds.SOPInstanceUID), hash_instancia.hexdigest()))
    if len(ident) != 1 or len(instancias) != len(arquivos) or len(geometrias) != 1:
        raise ValueError("A série mistura identificações, instâncias ou geometrias diferentes.")
    paciente, emissor, estudo, uid, frame = next(iter(ident))
    if not paciente or not estudo or not frame or uid != s["uid"]:
        raise ValueError("A série não tem identificação e referência espacial suficientes.")
    linhas, cols, espac, iop = next(iter(geometrias))
    normal = np.cross(iop[:3], iop[3:])
    if abs(normal[2]) < .98:
        raise ValueError("A série não tem orientação axial compatível.")
    p = np.asarray(posicoes)
    eixo = p @ normal
    diffs = np.diff(np.sort(eixo))
    if diffs.min() <= .001 or not np.allclose(diffs, np.median(diffs), rtol=.01, atol=.05):
        raise ValueError("A série tem cortes duplicados, ausentes ou espaçamento irregular.")
    deslocamento = p - p[0] - (eixo - eixo[0])[:, None] * normal
    if np.max(np.linalg.norm(deslocamento, axis=1)) > .1:
        raise ValueError("A série tem inclinação de gantry ou deslocamento lateral não suportado.")
    hash_.update(repr((sorted(hashes_instancias), linhas, cols, espac, iop, frame)).encode())
    return arquivos, (paciente, emissor, estudo, frame), hash_.hexdigest()


def validar_grupo(series, sbrt, alvo, adicionais=()):
    import radai_lung_4d as four
    if not 2 <= len(series) <= MAX_FASES:
        raise ValueError("Selecione entre 2 e 20 fases respiratórias.")
    ids = {s["uid"] for s in series}
    catalogo = {s["uid"]: s for s in list(series) + list(adicionais)}
    if len(ids) != len(series) or sbrt not in catalogo or alvo not in catalogo:
        raise ValueError("Escolha as fases, a série de anatomia SBRT e a referência.")
    verificados, grupo, porcentagens = {}, None, set()
    for uid, s in catalogo.items():
        arquivos, id_, assinatura = _inspecionar(s)
        if grupo is None:
            grupo = id_
        if grupo != id_:
            raise ValueError("As séries não compartilham paciente, estudo e referencial DICOM.")
        if uid in ids:
            fase = four.fase_respiratoria(ler_ct(arquivos[0]))
            if fase is None:
                raise ValueError("Inclua somente fases respiratórias; AVG/MIP, convencional e contrastadas ficam fora do CINE.")
            if fase in porcentagens:
                raise ValueError("Selecione somente uma reconstrução de cada fase respiratória.")
            porcentagens.add(fase)
        verificados[uid] = assinatura
    return verificados


@contextmanager
def _serie(s, esperado=None):
    import engine
    import radai_archive

    arquivos, _, assinatura = _inspecionar(s)
    if esperado is not None and assinatura != esperado:
        raise ValueError("A série mudou após a conferência; carregue as fases novamente.")
    with radai_archive.TemporariaDaSerie():
        stage = tempfile.mkdtemp(prefix="radai_lung_")
        engine.copy_sorted(arquivos, stage)
        ref = engine.load_sitk(stage)
        engine.conferir_volume_contornavel(ref, min_cortes=5, modalidade="CT")
        yield stage, ref, assinatura


@contextmanager
def _trava_serie(s, cfg):
    import radai_archive
    import radai_batch

    pasta, uid = pasta_valida(s["pasta"], cfg), s["uid"]
    radai_archive.conferir_escrita_no_destino(pasta)
    m = cfg.get("marcadores") or {}
    obrig = ("claim", "renovar", "unclaim", "lock_e_meu")
    if not all(callable(m.get(k)) for k in obrig):
        raise RuntimeError("A coordenação de séries não está disponível.")
    if not m["claim"](pasta, uid, {"machine": cfg.get("maquina", ""), "origem": "LUNG RT"}):
        raise RuntimeError("A série está em uso em outra estação.")
    fim = threading.Event()
    hb = threading.Thread(target=radai_batch.bater_lock, daemon=True,
                          args=(m["renovar"], pasta, uid, fim, cfg.get("heartbeat_s", 300)))
    hb.start()
    try:
        def confirmar():
            if not lock_proprio(m["lock_e_meu"](pasta, uid)):
                raise RuntimeError("A reserva da série deixou de pertencer a esta estação.")
        yield confirmar
    finally:
        fim.set()
        hb.join()
        if lock_proprio(m["lock_e_meu"](pasta, uid)):
            m["unclaim"](pasta, uid)


def lock_proprio(resultado):
    return resultado[0] is True if isinstance(resultado, tuple) else resultado is True


def inferir(ref, cfg):
    import engine
    import numpy as np

    jid = engine._job_new()
    fim = threading.Event()
    log = cfg.get("log")
    t = None
    try:
        cancelar = cfg.get("cancel_event")
        if cancelar is not None and cancelar.is_set():
            raise RuntimeError("Processamento cancelado.")
        def vigiar_cancelamento():
            while not fim.wait(.2):
                if cancelar is not None and cancelar.is_set():
                    engine._set(jid, cancelar=True)
                    return
        if cancelar is not None:
            threading.Thread(target=vigiar_cancelamento, daemon=True).start()
        if callable(log):
            log("LUNG RT · ACHADO: executando somente lung_nodules por pedido explícito.")
            t = threading.Thread(target=engine.drenar_log, args=(jid, log, fim), daemon=True)
            t.start()
        m = engine.run_ts_task(ref, TASK, engine._resolve_device(cfg.get("device", "auto")),
                               jid, timeout_s=cfg.get("timeout_task_s"), suavizar=False,
                               recorte_no_corpo=False)
        if cancelar is not None and cancelar.is_set():
            raise RuntimeError("Processamento cancelado.")
        if not isinstance(m, dict):
            raise RuntimeError("O motor não devolveu uma resposta válida.")
        receber = cfg.get("receber_pulmoes")
        if callable(receber):
            lungs = m.get("lung")
            if lungs is not None:
                lungs = np.asarray(lungs, bool)
                if lungs.shape != tuple(reversed(ref.GetSize())):
                    raise ValueError("A máscara pulmonar não corresponde à grade da fase.")
            receber(lungs)
        a = m.get(TASK)
        if a is None:
            return None
        a = np.asarray(a, dtype=bool)
        if a.shape != tuple(reversed(ref.GetSize())):
            raise ValueError("A máscara não corresponde à série que foi processada.")
        return a if a.any() else None
    finally:
        fim.set()
        if t is not None:
            t.join(timeout=3)
        engine._job_del(jid)


def transportar(mask, fonte, alvo):
    import numpy as np
    import SimpleITK as sitk
    from scipy import ndimage

    if mask is None:
        return None
    mask = np.asarray(mask, dtype=bool)
    if mask.shape != tuple(reversed(fonte.GetSize())):
        raise ValueError("A máscara não está na grade da fase de origem.")
    if not mask.any():
        return None
    if fonte.IsSameImageGeometryAs(alvo):
        return mask
    caixa = ndimage.find_objects(mask.view(np.uint8), max_label=1)[0]
    for zyx in itertools.product(*[(s.start, s.stop - 1) for s in caixa]):
        ponto = fonte.TransformIndexToPhysicalPoint(tuple(reversed(zyx)))
        indice = alvo.TransformPhysicalPointToContinuousIndex(ponto)
        if any(i < -0.499 or i > n - .501 for i, n in zip(indice, alvo.GetSize())):
            raise ValueError("Um contorno fica fora do campo da referência; escolha outra série.")
    imagem = sitk.GetImageFromArray(mask.view(np.uint8))
    imagem.CopyInformation(fonte)
    novo = sitk.Resample(imagem, alvo, sitk.Transform(3, sitk.sitkIdentity),
                         sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
    a = np.array(sitk.GetArrayViewFromImage(novo), dtype=bool, copy=True)
    from radai_geom import rotular
    if rotular(mask)[1] != rotular(a)[1]:
        raise ValueError("A grade de referência perde, divide ou funde contornos desta fase.")
    return a


def unir_fases(fases):
    import numpy as np
    from scipy import ndimage

    saida = {}
    uniao = None
    for i, mask in enumerate(fases, 1):
        if mask is None or not mask.any():
            continue
        labels, n = ndimage.label(mask)
        if (n + len(saida) + 1) * mask.nbytes > MAX_BYTES or n + len(saida) > 128:
            raise ValueError("A seleção tem contornos demais para exportar de uma vez.")
        for j in range(1, n + 1):
            saida["GTV_F%02d_N%02d" % (i, j)] = (labels == j)
        uniao = mask.copy() if uniao is None else uniao | mask
    if uniao is not None:
        saida["ITV"] = uniao
    return saida


def _saida(stage, s, cfg, tipo):
    import engine
    import radai_sets
    import radai_output
    import radai_version

    import secrets
    nome = "RS_RadAI_%s_%s_%s_%s.dcm" % (
        tipo, radai_sets.data_do_nome(s), secrets.token_hex(5), s["uid"][-8:])
    return radai_output.Saida(engine, stage, s["pasta"], nome, tasks=(TASK,),
                              versao=radai_version._entrega_txt(),
                              log=cfg.get("log"), modalidade="CT")


def rodar_nodulos(s, cfg, esperado=None, destino=None):
    if destino is None:
        return processar_serie(s, cfg, esperado)["estado"] == "positivo"
    with _trava_serie(s, cfg) as confirmar, _serie(s, esperado) as (stage, ref, _):
        mask = inferir(ref, cfg)
        if mask is not None:
            confirmar()
            saida = _saida(stage, s, cfg, "LUNG")
            if not saida.conjunto("nod", {TASK: mask}, "nosso", suavizar_mm=0.0,
                                 observacoes={TASK: "ACHADO; sugestão de IA não aprovada."}):
                raise RuntimeError("Não foi possível gravar o RTSTRUCT de nódulos.")
        if destino is not None:
            return transportar(mask, ref, destino)
        return mask is not None


def geometria(ref):
    return {"size_xyz": list(ref.GetSize()), "spacing_xyz": list(ref.GetSpacing()),
            "origin_lps": list(ref.GetOrigin()), "direction": list(ref.GetDirection())}


def medir_lesoes(mask, ref, lobos=None):
    import numpy as np
    from radai_lung_4d import componentes
    if mask is None:
        return []
    spacing = np.asarray(ref.GetSpacing())
    lesions = []
    for n, center, quantos, pedaco in componentes(mask, ref):
        extent = np.array(pedaco._sub.shape[::-1]) * spacing
        lobe = 'indeterminado'
        if isinstance(lobos, dict):
            overlaps = []
            for name, m in lobos.items():
                if np.shape(m) != mask.shape:
                    continue
                local = (m[pedaco.caixa] if hasattr(type(m), "recorte")
                         else np.asarray(m)[pedaco.caixa])
                overlaps.append((int(np.count_nonzero(np.asarray(local, bool) & pedaco._sub)), name))
            if overlaps and max(overlaps)[0] > quantos / 2:
                lobe = max(overlaps)[1]
        lesions.append({"id": "N%03d" % n, "volume_mm3": float(quantos * spacing.prod()),
                        "centro_lps_mm": list(center), "extensao_xyz_mm": extent.tolist(),
                        "lobo": lobe, "origem_lobo": "mascara_lobar" if lobe != 'indeterminado' else None,
                        "origem": TASK, "grade": "nativa"})
    return lesions


def serie_volume(s):
    import SimpleITK as sitk
    with _serie(s) as (_, ref, _):
        return sitk.GetArrayFromImage(ref), tuple(ref.GetSpacing())


abrir_serie = _serie


def registrar_erro(exc, cfg):
    import traceback
    log = (cfg or {}).get('log')
    if callable(log):
        frames = traceback.extract_tb(exc.__traceback__)
        log('LUNG: %s; %s' % (type(exc).__name__, ' > '.join(
            '%s:%d:%s' % (Path(f.filename).name, f.lineno, f.name) for f in frames)))


def processar_serie(s, cfg, esperado=None):
    import radai_lung_receipts as receipts
    from datetime import datetime, timezone
    with _trava_serie(s, cfg) as confirmar:
        _, identidade, assinatura = _inspecionar(s)
        if esperado is not None and esperado != assinatura:
            raise ValueError("A série mudou após a conferência; carregue-a novamente.")
        cached = receipts.ler(s, assinatura)
        receber = cfg.get('receber_resultado')
        if cached:
            nativas = receipts.ler_mascaras(s, cached) if callable(receber) else None
            if not callable(receber) or nativas is not None:
                if callable(receber):
                    with _serie(s, assinatura) as (_, ref, _):
                        receber(ref, *nativas)
                confirmar()
                return dict(cached, reutilizado=True)
        paciente, emissor, estudo, frame = identidade
        r = {"schema": receipts.SCHEMA, "recipe": receipts.RECIPE, "task": TASK,
             "series_uid": s['uid'], "study_uid": estudo, "frame_uid": frame,
             "paciente_chave": hashlib.sha256((paciente + '\0' + emissor).encode()).hexdigest(),
             "assinatura": assinatura, "estado": "falha", "lesoes": [], "outputs": [],
             "created_at": datetime.now(timezone.utc).isoformat(), "reutilizado": False}
        try:
            with _serie(s, assinatura) as (stage, ref, _):
                lungs = {}
                def receber_pulmoes(m):
                    lungs['mask'] = m
                    if callable(cfg.get('receber_pulmoes')):
                        cfg['receber_pulmoes'](m)
                mask = inferir(ref, dict(cfg, receber_pulmoes=receber_pulmoes))
                confirmar()
                r.update(geometria=geometria(ref), lesoes=medir_lesoes(mask, ref),
                         estado="positivo" if mask is not None else "vazio")
                if mask is not None:
                    out = _saida(stage, s, cfg, "LUNG")
                    if not out.conjunto("nod", {TASK: mask}, "nosso", suavizar_mm=0.0,
                                        observacoes={TASK: "ACHADO; sugestão de IA não aprovada."}):
                        raise RuntimeError("Não foi possível gravar o RTSTRUCT de nódulos.")
                    path = Path(out._alvo('NOD_'))
                    r['outputs'] = [{"name": path.name, "sha256": receipts.sha256(path)}]
                r['mascaras_nativas'] = receipts.guardar_mascaras(
                    s, mask, lungs.get('mask'), tuple(reversed(ref.GetSize())))
                confirmar()
                receipts.gravar(s, r)
                if callable(receber):
                    receber(ref, mask, lungs.get('mask'))
                return r
        except Exception as exc:
            import radai_batch
            r.update(estado="adiado" if type(exc).__name__ in ('TaskTravada', 'RecursoPrevisto') else "falha",
                     erro=type(exc).__name__, outputs=[])
            registrar_erro(exc, cfg)
            confirmar()
            receipts.gravar(s, r)
            raise


def rodar_4d(series, uid_sbrt, uid_alvo, cfg, parar, avancar, adicionais=()):
    import radai_batch
    from engine import MascaraCompacta
    import radai_lung_4d as four
    import SimpleITK as sitk

    chaves = validar_grupo(series, uid_sbrt, uid_alvo, adicionais)
    por_uid = {s["uid"]: s for s in list(series) + list(adicionais)}
    alvo = por_uid[uid_alvo]
    with _serie(alvo, chaves[uid_alvo]) as (_, ref_alvo, _):
        grade = sitk.Image(ref_alvo.GetSize(), sitk.sitkUInt8)
        grade.CopyInformation(ref_alvo)
    sbrt = dict(por_uid[uid_sbrt], modo="perso", protocolos=["sbrt_pulmao"],
                tasks={TASK: True}, achado_declarado=True, comparacao={},
                protocolos_3d=[], substituir=False)
    transportadas, previas, medidas, estados = {}, {}, {}, {}
    centro_lps = grade.TransformContinuousIndexToPhysicalPoint(tuple((n-1)/2 for n in grade.GetSize()))
    if parar.is_set():
        return None
    avancar("Processando anatomia SBRT na série escolhida.")
    r = radai_batch._uma_serie(
        sbrt, False, None, cfg.get("device", "auto"), cfg.get("python_exe"),
        cfg.get("timeout_task_s", 10800), 10800, cfg.get("log"),
        cfg["marcadores"], cfg.get("maquina", ""), cfg.get("heartbeat_s", 300),
        cfg.get("suavizar_mm", 1.5))
    if r.get("erro") or (r.get("pulada") and r.get("pulo") != "concluida"):
        raise RuntimeError("Não foi possível concluir a anatomia SBRT selecionada.")
    for i, s in enumerate(series, 1):
        if parar.is_set():
            return None
        if s['uid'] not in transportadas:
            avancar("Processando pulmões e nódulos · fase %d/%d." % (i, len(series)))
            def receber(ref, mask, lungs):
                transportada = transportar(mask, ref, grade)
                transportadas[s['uid']] = (None if transportada is None else
                                           MascaraCompacta.de(transportada))
                medidas[s['uid']] = medir_lesoes(mask, ref)
                previas[s['uid']] = four.previa(ref, mask, lungs, centro_lps)
            try:
                receipt = processar_serie(s, dict(cfg, cancel_event=parar, receber_resultado=receber), chaves[s['uid']])
                estados[s['uid']] = receipt['estado']
            except Exception as exc:
                if parar.is_set():
                    return None
                registrar_erro(exc, cfg)
                estados[s['uid']] = 'falha'
                transportadas[s['uid']], medidas[s['uid']] = None, []
                with _serie(s, chaves[s['uid']]) as (_, ref, _):
                    previas[s['uid']] = four.previa(ref, None, None, centro_lps)
                avancar("Uma fase falhou; permanece como lacuna, sem medida. Confira antes de exportar.")
        if sum(m.bytes_guardados() for m in transportadas.values() if m is not None) > MAX_BYTES:
            raise ValueError("As fases excedem a memória reservada para o consenso 4D.")
    fases = [transportadas[s["uid"]] for s in series]
    medidas = {i: medidas[s['uid']] for i, s in enumerate(series)}
    masks, curvas = four.associar(fases, grade, medidas_nativas=medidas)
    return {'serie': alvo, 'assinatura': chaves[uid_alvo], 'masks': masks,
            'lacunas': [i for i, m in enumerate(fases) if m is None],
            'curvas': curvas, 'cine': [previas[s['uid']] for s in series],
            'fases': fases, 'grade': grade, 'medidas_nativas': medidas,
            'estados_fases': [estados[s['uid']] for s in series]}


def exportar(s, assinatura, masks, cfg, curvas=None):
    import engine
    import radai_output

    with _trava_serie(s, cfg) as confirmar, _serie(s, assinatura) as (stage, _, _):
        saida = _saida(stage, s, cfg, "ITV4D")
        nota = "Contorno de fase da TC 4D; sugestão de IA não aprovada."
        observacoes = {}
        for k in masks:
            track = next((t for t in curvas or () if k == 'ITV_' + t['id']), None)
            observacoes[k] = ("União por lesão; sugestão de ITV não aprovada. "
                              "Fases contribuintes: %s. Lacunas: %s." % (
                                  ','.join(str(i) for i in track['contribuintes']),
                                  ','.join(str(i) for i in track['lacunas'])) if track else
                             ("União dos contornos detectados nas fases selecionadas; "
                              "sugestão de ITV não aprovada." if k == "ITV" or k.startswith("ITV_") else nota))
        rt, nomes = engine.build_rtstruct(
            stage, masks, tasks=(TASK,), versao_worker=saida.versao,
            origem={k: "nosso" for k in masks}, suavizar_mm=0.0,
            rotulo="LUNG RT 4D", derivar=False, modalidade="CT",
            exigir_grade=True,
            observacoes=observacoes)
        try:
            if len(nomes) != len(masks):
                raise RuntimeError("A exportação não preservou todos os contornos.")
            confirmar()
            saida._gravar_arquivo(rt, os.path.join(s["pasta"], saida.rs_name))
        finally:
            radai_output._apagar_temp_do_rs(rt, engine)
