# -*- coding: utf-8 -*-
"""Enriquecimentos locais, depois de resolver o destino e antes de construir o STUDY."""
import time

GRUPOS_COSTAIS = frozenset(("ribs_left", "ribs_right"))
COSTELAS = GRUPOS_COSTAIS | frozenset(
    "rib_%s_%d" % (lado, numero) for lado in ("left", "right") for numero in range(1, 13)
)

CORONARIA = "rocards_lad"


def coronarias_ativas():
    """Só o aceite específico desta estação autoriza a execução e o cache da DA."""
    try:
        from radai_plugin_coronarias import ativado
        return ativado() is True
    except Exception:
        return False


def exigir_plugin_coronarias():
    if not coronarias_ativas():
        raise PermissionError("O plugin Coronárias requer ativação em Configurações > Plugins.")


def entregar_da(protocolo, tem_coracao, no_protocolo, marcada_na_serie):
    """A lista de um protocolo antigo não trazia a preferência de excluir a DA."""
    if marcada_na_serie:
        return True
    return (protocolo or {}).get("da_com_coracao") is not False and (tem_coracao or no_protocolo)


def _coronaria_com_cache(ref, coracao, dispositivo, python_exe, log):
    exigir_plugin_coronarias()
    import numpy as np
    from pathlib import Path
    import radai_cache_tasks as cache
    import radai_rocards as rede
    # O recorte de retenção está na grade nativa ZYX. A rede normaliza sua
    # orientação em separado e devolve os voxels à mesma grade.
    de, ate = [], []
    for eixo, passo in enumerate(reversed(ref.GetSpacing())):
        indices = np.flatnonzero(coracao.any(axis=tuple(i for i in range(3) if i != eixo)))
        folga = int(np.ceil(rede.MARGEM_MM / passo))
        de.append(max(0, int(indices[0]) - folga))
        ate.append(min(coracao.shape[eixo], int(indices[-1]) + folga + 1))
    caixa = tuple(slice(a, b) for a, b in zip(de, ate))
    forma = tuple(b-a for a,b in zip(de,ate))
    dados = {}

    def executar():
        m, info = rede.segmentar(ref, coracao, dispositivo=dispositivo, python_exe=python_exe,
                                log=log, interpolar_lacunas=True)
        if m.shape != coracao.shape or not m.any() or np.count_nonzero(m) != np.count_nonzero(m[caixa]):
            raise ValueError("Saída da coronária vazia ou incompatível com o recorte de 10 mm.")
        dados.update(info)
        return m[caixa].astype(np.uint8, copy=False)

    def fontes():
        from radai_models import pasta_do_modelo
        raiz = Path(pasta_do_modelo(CORONARIA)) / "models"
        app = Path(rede.__file__).parent
        pesos = [p for nome in rede.MODELOS for p in
                 (raiz/nome/"saved_model.pb", raiz/nome/"keras_metadata.pb",
                  raiz/nome/"variables"/"variables.index", raiz/nome/"variables"/"variables.data-00000-of-00001")]
        recibo = raiz.parent/"runtime"/".rocards-requisitos.sha256"
        return pesos + [recibo] + [app/n for n in ("radai_rocards.py", "radai_rocards_worker.py", "radai_rocards_gap.py")]

    recortada = cache.rotulos_de_motor(CORONARIA, de + ate, forma, dispositivo, "DA-focal-10mm-v1",
                                       fontes, executar, dados=dados)
    if dados.get("do_cache"):
        log("Coronária DA recuperada do cache desta TC e recorte cardíaco.")
    final = np.zeros(coracao.shape, dtype=np.uint8)
    final[caixa] = recortada
    return final, dados


def preparar_coronaria(saida, dispositivo, python_exe, enriquecimento, meta):
    """Adia o recorte até o coração já ter passado pelo acabamento da série."""
    def segmentar_da(coracao):
        inicio = time.monotonic()
        try:
            import numpy as np
            import radai_cache_tasks as cache
            ref = getattr(saida, "_img_lida", None)
            if ref is None:
                saida.serie_lida()
                ref = getattr(saida, "_img_lida", None)
            if ref is None:
                raise ValueError("TC indisponível na grade original")
            mascara, dados = _coronaria_com_cache(ref, np.asarray(coracao, dtype=bool), dispositivo,
                                                 python_exe, saida.log)
            if mascara.shape != tuple(reversed(ref.GetSize())) or not mascara.any():
                raise ValueError("máscara vazia ou incompatível com a TC")
            meta.setdefault("modelos_study", {})[CORONARIA] = dados
            return mascara, dados.get("descricao_dicom") or "DA estimada por ROCardS, recorte Heart_ai + 10 mm."
        except (MemoryError, cache.ReprocessamentoSemMapa):
            raise
        except Exception as exc:
            aviso = "Coronária DA ROCardS indisponível (%s)." % str(exc)[:180]
            enriquecimento["avisos"].append(aviso)
            saida.log("Aviso: " + aviso)
            return None, None
        finally:
            meta.setdefault("tempos_modelos_finais", []).append(
                ("Coronária DA ROCardS", time.monotonic() - inicio))
    return segmentar_da


# Candidato conservador do ensaio da junção: 0,10 cm³; só um componente
# desconectado de toda a alça em 3D pode ser transferido. O limite é físico.
ILHA_COLON_MAX_MM3 = 100.0


def repartir_intestino(engine, reto, colon, delgado, quadris, grade):
    import numpy as np
    from scipy import ndimage
    forma = reto.shape
    compacta = engine.MascaraCompacta.de
    vazio = engine.MascaraCompacta(forma, None, None)
    def preparar(m):
        if m is None:
            return vazio
        r = compacta(m)
        if r.shape != forma:
            raise ValueError("máscaras de pelve em grades diferentes")
        return r

    delgado = preparar(delgado)
    reto = engine._diferenca_compacta(reto, delgado)
    ilhas = vazio
    colon = preparar(colon)
    if grade is not None and colon.any() and reto.any():
        caixa = colon.caixa
        local = colon[caixa]
        # Primeiro mede o contato em uma caixa restrita. Só rotula o cólon
        # inteiro quando há uma interface; uma alça pode continuar em outra fatia.
        encontro = tuple(slice(max(c.start, r.start-1), min(c.stop, r.stop+1))
                         for c, r in zip(caixa, reto.caixa))
        if all(v.start < v.stop for v in encontro):
            margem = tuple(slice(max(0, s.start-1), min(f, s.stop+1))
                           for s, f in zip(encontro, forma))
            interior = tuple(slice(s.start-m.start, s.stop-m.start) for s,m in zip(encontro,margem))
            contato = colon[encontro] & ndimage.binary_dilation(reto[margem])[interior]
            if contato.any():
                rotulos, n = ndimage.label(local, structure=np.ones((3,3,3), bool))
                if n > 1:
                    volumes = np.bincount(rotulos.ravel())
                    pequenos = volumes * grade.volume_voxel_mm3 <= ILHA_COLON_MAX_MM3
                    pequenos[0] = False
                    pequenos[1 + volumes[1:].argmax()] = False
                    # O FOV pode truncar uma alça que continua fora da série.
                    for eixo, trecho in enumerate(caixa):
                        if trecho.start == 0:
                            pequenos[np.unique(rotulos.take(0, axis=eixo))] = False
                        if trecho.stop == forma[eixo]:
                            pequenos[np.unique(rotulos.take(-1, axis=eixo))] = False
                    janela = tuple(slice(s.start-c.start, s.stop-c.start) for s,c in zip(encontro,caixa))
                    ids = np.unique(rotulos[janela][contato])
                    ids = ids[pequenos[ids]]
                    if ids.size:
                        partes = engine.MascaraCompacta(forma, caixa, np.isin(rotulos, ids))
                        ilhas = engine._diferenca_compacta(partes, delgado)
                        reto = engine._uniao_compacta((reto, ilhas), forma)
                        colon = engine._diferenca_compacta(colon, ilhas)

    caudal, bilateral = vazio, None
    if grade is not None and all(p is not None for p in quadris):
        eixo, sinal = grade.eixo_sinal("sup")
        lados = []
        for p in quadris:
            p = preparar(p)
            planos = np.zeros(forma[eixo], bool)
            if p.any():
                planos[p.caixa[eixo]] = p[p.caixa].any(axis=tuple(i for i in range(3) if i != eixo))
            lados.append(planos[::sinal])
        comuns = np.flatnonzero(lados[0] & lados[1])
        if comuns.size and not (lados[0][0] or lados[1][0]):
            bilateral = int(comuns[0])
            if reto.any():
                plano = bilateral if sinal > 0 else forma[eixo]-1-bilateral
                local = reto[reto.caixa].copy()
                indices = np.arange(reto.caixa[eixo].start, reto.caixa[eixo].stop)
                np.moveaxis(local,eixo,0)[(indices-plano)*sinal >= 0] = False
                caudal = engine.MascaraCompacta(forma,reto.caixa,local)
                reto = engine._diferenca_compacta(reto, caudal)
                ilhas = engine._diferenca_compacta(ilhas, caudal)
    return reto, colon, ilhas, caudal, bilateral


def aplicar(saida, masks, origem, destinos, regioes, grade, dispositivo, python_exe,
            usar_arcos=True, usar_reto=True, full=False, base_ts=None, marcadas=()):
    import radai_cache_tasks as cache
    engine = saida.engine
    resultado = {"limites": {}, "pelve_jhu": False, "tempos": [], "avisos": [], "detalhes": {}}
    if saida.modalidade != "CT":
        return resultado
    if full:
        # A lista do FULL pode conter Ribs e Rectum mesmo sem o operador
        # pedir essas redes. A escolha expressa fica separada do padrão do STUDY.
        usar_arcos = usar_arcos and "moose_ribs" in marcadas
        usar_reto = usar_reto and "jhu_rectum" in marcadas
    arcos = set(destinos) & COSTELAS if usar_arcos else set()
    intestino = {"rectum", "colon", "bag_bowel", "bag_bowel_oar", "anus"}
    # A união da estação pode pedir intestino indiretamente. Fechar dependências
    # com nomes apenas, antes de materializar a grade ou carregar qualquer rede.
    planejar = getattr(engine, "plano_de_rotulos", None)
    plano = planejar(destinos, set(masks) | {"rectum"}) if destinos and planejar else set()
    pede_reto = bool(intestino.intersection(set(destinos) | plano))
    pelve = False
    if pede_reto:
        anatomia = set(regioes or ())
        if not anatomia and hasattr(engine, "regioes_no_campo"):
            anatomia = set(engine.regioes_no_campo(masks, grade)[0])
        pelve = "pelve" in anatomia
    if not arcos and not pelve:
        return resultado

    def aviso(texto):
        resultado["avisos"].append(texto)
        saida.log("Aviso: " + texto)

    def imagem():
        ref = getattr(saida, "_img_lida", None)
        if ref is None:
            saida.serie_lida()
            ref = getattr(saida, "_img_lida", None)
        if ref is None:
            raise RuntimeError("TC indisponível na grade original")
        return ref

    if arcos:
        from radai_ribs_posterior import refinar
        inicio = time.monotonic()
        try:
            vetos = {}
            alteradas, dados = refinar(imagem(), base_ts if base_ts is not None else masks, arcos,
                dispositivo=dispositivo, python_exe=python_exe, log=saida.log, vetos=vetos)
            if vetos:
                resultado["vetos_costais"] = vetos
            resultado["detalhes"]["moose_ribs"] = dados
            for k, m in alteradas.items():
                masks[k] = m
                origem[k] = "moose_ribs"
                grupo = "ribs_left" if k.startswith("rib_left_") else "ribs_right"
                origem[grupo] = "moose_ribs"
            if dados["estado"] in ("falha", "ignorado", "parcial"):
                aviso("Arcos costais MOOSE: %s. As porções sem complemento conservam a base TS."
                      % dados["motivo"].rstrip(". "))
        except cache.ReprocessamentoSemMapa:
            raise
        except Exception as exc:
            aviso("Complemento MOOSE indisponível (%s). Mantidas as costelas do TS." % str(exc)[:120])
        resultado["tempos"].append(("Arcos costais MOOSE", time.monotonic() - inicio))
    if not pelve:
        return resultado
    resultado["pelve_jhu"] = True
    if "rectum" in masks:
        del masks["rectum"]
    origem.pop("rectum", None)
    if not usar_reto:
        return resultado
    inicio = time.monotonic()
    try:
        from radai_rectum_jhu import segmentar
        ref = imagem()
        mask, detalhes = segmentar(ref, dispositivo=dispositivo, python_exe=python_exe, log=saida.log, base_ts=base_ts)
        if tuple(mask.shape) != tuple(reversed(ref.GetSize())) or not mask.any():
            raise ValueError("reto vazio ou incompatível com a grade da TC")
        reto = engine.MascaraCompacta.de(mask)
        del mask
        # O intestino grosso do contrato é o da base TS. Nenhum novo voxel
        # deve aparecer no intervalo que ambos deixaram vazio.
        def base(chave):
            if base_ts is not None and chave in base_ts:
                return base_ts.compacta(chave) if hasattr(base_ts, "compacta") else base_ts[chave]
            return masks.get(chave)

        colon = base("colon")
        delgado = base("small_intestine")
        if delgado is None:
            delgado = base("small_bowel")
        reto, grosso, ilhas, anal, marco = repartir_intestino(
            engine, reto, colon, delgado, (base("hip_left"), base("hip_right")), grade)
        limites = {"rectum": reto}
        if colon is not None:
            limites["colon"] = grosso
            origem["colon"] = "ts_jhu_colon"
        masks.update(limites)
        origem["rectum"] = "jhu_rectum"
        resultado["limites"] = limites
        resultado["sobreposicao_reto_jhu"] = ilhas
        resultado["pelve_terminal"] = {"anal": anal, "bilateral": marco,
                                        "interface": engine._intersecao_compacta(grosso, reto),
                                        "entregar_anus": "anus" in set(destinos) | plano}
        detalhes.update({"ilha_colon_vx": int(ilhas.sum()), "transferido_anus_vx": int(anal.sum()),
                         "ultimo_isquio_bilateral_canonico": marco})
        if marco is None:
            aviso("Limite inferior bilateral do reto indeterminado no campo; mantido o limite da rede.")
        saida.log("Junção pélvica: %d voxels das ilhas para o reto, %d do reto para o ânus." %
                  (int(ilhas.sum()), int(anal.sum())))
        resultado["detalhes"]["jhu_rectum"] = detalhes
    except (cache.ReprocessamentoSemMapa, MemoryError):
        raise
    except Exception as exc:
        aviso("Reto Johns Hopkins indisponível (%s). O reto não foi derivado do cólon." % str(exc)[:120])
    resultado["tempos"].append(("Reto Johns Hopkins", time.monotonic() - inicio))
    return resultado

