# -*- coding: utf-8 -*-
import io
import json
import os
import re
import shutil
import threading
import time
from datetime import datetime

import radai_queue as Q

_TRAVA = threading.RLock()

_CARDS = []

TETO_DO_VIGIA_NA_TELA = 12
_VIGIA_NA_FILA = {"total": 0}

VARIAVEL_DA_PASTA = "RADAI_FILA_DIR"
NOME_DO_ARQUIVO = "fila.json"
NOME_DO_INDICE = "fila_series.json"
VERSAO_DO_ARQUIVO = 1

_PERSISTIR = {"ligada": False, "erro": u"", "gravacoes": 0}
_GRAVACAO = threading.Lock()
_GANCHOS = {}

FRASE_FECHOU_NO_MEIO = (u"o programa fechou no meio desta série; o que ela "
                        u"fez foi descartado, e ela pode voltar à fila")
FRASE_NAO_ENCONTRADA = u"série não encontrada"
FRASE_ESPERA_O_VIGIA = (u"espera a série do vigia terminar; a que está "
                        u"rodando não é interrompida")

INTERVALO_DO_COMPLEMENTO_S = 3600.0


def _maquina():
    try:
        import radai_batch
        return radai_batch._maquina_desta_estacao()
    except Exception:
        try:
            import socket
            return socket.gethostname()
        except Exception:
            return u""


def ligar_ganchos(**ganchos):
    for k, v in ganchos.items():
        if v is None:
            _GANCHOS.pop(k, None)
        else:
            _GANCHOS[k] = v


def _gancho(nome):
    g = _GANCHOS.get(nome)
    return g if callable(g) else None


def _agora():
    return time.time()


def _hora(ts=None):
    return datetime.fromtimestamp(ts or _agora()).strftime("%H:%M")


_TRECHO_DE_CAMINHO = re.compile(
    u"(?:[A-Za-z]:[\\\\/]|\\\\\\\\|(?<![\\w.])/)[^\\s\"'<>|]*")
_UID_INTEIRO = re.compile(u"\\b\\d+(?:\\.\\d+){5,}\\b")


def sem_caminho(texto):
    s = u"%s" % (texto or u"")
    m = _TRECHO_DE_CAMINHO.search(s)
    if m:
        s = s[:m.start()] + u"[pasta]"
    if u"\\" in s:
        s = s[:s.index(u"\\")] + u"[pasta]"
    s = _UID_INTEIRO.sub(u"[uid]", s)
    return s[:300]


def cards():
    with _TRAVA:
        fora = Q.ordenar([dict(c) for c in _CARDS])
    Q.conferir_ordem(fora)
    return fora


def _visiveis():
    return Q.ordenar(_CARDS)


def _pelo_id(cid):
    if not cid:
        return -1
    for k, c in enumerate(_CARDS):
        if c.get("id") == cid:
            return k
    return -1


def cartao(cid):
    with _TRAVA:
        k = _pelo_id(cid)
        return dict(_CARDS[k]) if k >= 0 else None


def _acoes(c, vis, i):
    pode_mover = Q.pode_mover(c)
    acima = vis[i - 1] if i > 0 else None
    abaixo = vis[i + 1] if i + 1 < len(vis) else None
    return {"subir": bool(pode_mover and acima is not None
                          and Q.pode_mover(acima)),
            "descer": bool(pode_mover and abaixo is not None
                           and Q.pode_mover(abaixo)),
            "tirar": bool(Q.pode_tirar(c)),
            "repor": bool(Q.pode_repor(c)
                          and c.get("mensagem") != FRASE_NAO_ENCONTRADA
                          and (c.get("pasta")
                               or (c.get("carga") or {}).get("pasta")))}


def para_tela(lista):
    lista = list(lista or ())
    fora = []
    for i, c in enumerate(lista):
        d = dict(c)
        d["detalhe"] = detalhe_publico(c.get("carga"))
        d["acoes"] = _acoes(c, lista, i)
        d["posicao"] = i + 1
        for k in ("pasta", "carga", "copiar_rs_para"):
            d.pop(k, None)
        d["copias"] = len(c.get("copiar_rs_para") or ())
        uid = d.get("uid") or u""
        d["uid"] = uid[-8:] if len(uid) > 8 else uid
        for k in ("mensagem", "motivo", "nao_contornavel"):
            if d.get(k):
                d[k] = sem_caminho(d[k])
        d["pendentes_por_memoria"] = [
            {"task": u"%s" % (p.get("task") or u""),
             "pedia_gib": p.get("pedia_gib"), "livre_gib": p.get("livre_gib")}
            for p in (c.get("pendentes_por_memoria") or ())
            if isinstance(p, dict)]
        fora.append(d)
    return fora


# GUARDA: lista de PERMITIDOS; a carga leva a pasta do paciente e não sai inteira.
CAMPOS_DO_DETALHE = ("modo", "modalidade", "cortes", "espessura", "descricao",
                     "protocolos", "tasks")
# GUARDA: a carga e a serie da varredura (`radai_batch._juntar`), com as chaves dela.
FONTE_DO_DETALHE = {"espessura": "espessura_mm", "descricao": "desc"}


def detalhe_publico(carga):
    if not isinstance(carga, dict):
        return {}
    fora = {}
    for k in CAMPOS_DO_DETALHE:
        v = carga.get(FONTE_DO_DETALHE.get(k, k))
        if v in (None, u"", [], {}, ()):
            continue
        if k == "tasks" and isinstance(v, dict):
            v = sorted(t for t, lig in v.items() if lig)
        elif k == "protocolos":
            v = [(p.get("cod") or p.get("nome") or u"") if isinstance(p, dict)
                 else p for p in (v or ())]
            v = [str(p) for p in v if p]
        elif isinstance(v, (list, tuple)):
            v = [str(x) for x in v]
        elif isinstance(v, (int, float)):
            pass
        else:
            v = str(v)
            if u"\\" in v or u":\\" in v or v.startswith(u"/"):
                continue
        if v in ([], u""):
            continue
        fora[k] = v
    return fora


def resumo():
    with _TRAVA:
        r = Q.resumo(_CARDS)
        r["vigia_na_fila"] = int(_VIGIA_NA_FILA.get("total") or 0)
        return r


def limpar():
    with _TRAVA:
        del _CARDS[:]
        _VIGIA_NA_FILA["total"] = 0
    _gravar()


def _chave_da_serie(s):
    s = s or {}
    return (str(s.get("uid") or u""), str(s.get("pasta") or u""))


_ESCOLHA = ("modo", "tasks_extra", "motores_extra", "topo",
            "estudos", "modo_v81",
            "protocolos", "tasks", "comparacao", "oar_fora", "legado_v82",
            "substituir", "protocolos_3d", "so_pos", "so_pos_falharam",
            "protocolo_proprio", "achado_declarado")


def _projecao_da_escolha(carga):
    fora = {}
    for k in _ESCOLHA:
        if k in (carga or {}):
            v = carga[k]
            if isinstance(v, dict):
                v = tuple(sorted((str(a), b) for a, b in v.items()))
            elif isinstance(v, (list, tuple)):
                v = tuple(json.dumps(x, sort_keys=True)
                          if isinstance(x, dict) else x for x in v)
            fora[k] = v
    return fora


def _rotulo_de(s):
    return (s.get("rotulo") or s.get("nome") or s.get("descricao")
            or (u"série …%s" % str(s.get("uid") or u"")[-8:]
                if s.get("uid") else u"série"))


def _vivo(c):
    return (Q.e_do_lote(c)
            and c.get("estado") in (Q.ESPERANDO, Q.RODANDO, Q.PULADO))


TETO_DE_COPIAS = 8


def _destinos(lista):
    fora = []
    for p in (lista or ()):
        p = (u"%s" % (p or u"")).strip().strip('"')
        if p and p not in fora:
            fora.append(p)
    return fora


def frase_do_teto_de_copias(n, somadas=False):
    if somadas:
        return (u"copiar_rs_para leva até %d pastas; somadas às que a série "
                u"já tinha na fila, seriam %d" % (TETO_DE_COPIAS, n))
    return (u"copiar_rs_para leva até %d pastas, e vieram %d"
            % (TETO_DE_COPIAS, n))


def _somar_destinos(k, s):
    c = _CARDS[k]
    antes = list(c.get("copiar_rs_para") or ())
    destinos = _destinos(antes + list((s or {}).get("copiar_rs_para") or ()))
    if destinos == antes:
        return False
    c2 = dict(c)
    c2["copiar_rs_para"] = destinos
    _CARDS[k] = c2
    return True


def _estouro_de_copias(prontos):
    somadas = {}
    for c in _CARDS:
        if _vivo(c):
            somadas.setdefault(_chave_da_serie(c),
                               list(c.get("copiar_rs_para") or ()))
    for k, (_origem, carga) in enumerate(prontos):
        chave = _chave_da_serie(carga)
        junto = _destinos(list(somadas.get(chave) or ())
                          + list(carga.get("copiar_rs_para") or ()))
        if len(junto) > TETO_DE_COPIAS:
            return u"item %d: %s" % (k + 1,
                                     frase_do_teto_de_copias(len(junto), True))
        somadas[chave] = junto
    return u""


def _atualizar_escolha(k, s):
    c = _CARDS[k]
    if c.get("estado") not in (Q.ESPERANDO, Q.PULADO):
        return False
    velha = dict(c.get("carga") or {})
    nova = dict(velha)
    for campo in _ESCOLHA:
        if campo in (s or {}):
            nova[campo] = s[campo]
        else:
            nova.pop(campo, None)
    destinos = _destinos(list(c.get("copiar_rs_para") or ())
                         + list((s or {}).get("copiar_rs_para") or ()))
    mudou_destino = destinos != list(c.get("copiar_rs_para") or ())
    if (_projecao_da_escolha(nova) == _projecao_da_escolha(velha)
            and not mudou_destino):
        return False
    c2 = dict(c)
    c2["carga"] = nova
    c2["copiar_rs_para"] = destinos
    _CARDS[k] = c2
    return True


def _acrescentar(series, origem):
    vivas = {}
    for k, c in enumerate(_CARDS):
        if _vivo(c):
            vivas.setdefault(_chave_da_serie(c), k)
    novos, repetidas, atualizadas, vistas, ids = [], 0, 0, {}, []
    for s in (series or ()):
        s = dict(s or {})
        chave = _chave_da_serie(s)
        if chave[0] and chave in vistas:
            repetidas += 1
            ids.append(vistas[chave])
            continue
        if chave[0] and chave in vivas:
            k = vivas[chave]
            if _CARDS[k].get("estado") == Q.RODANDO:
                _somar_destinos(k, s)
                repetidas += 1
            elif _atualizar_escolha(k, s):
                atualizadas += 1
            else:
                repetidas += 1
            ids.append(_CARDS[k]["id"])
            vistas[chave] = _CARDS[k]["id"]
            continue
        destinos = _destinos(s.pop("copiar_rs_para", None))
        c = Q.novo_card(Q.SERIE, rotulo=_rotulo_de(s), uid=s.get("uid") or u"",
                        pasta=s.get("pasta") or u"", origem=origem,
                        extra={"carga": s, "copiar_rs_para": destinos,
                               "criado": _agora()})
        novos.append(c)
        ids.append(c["id"])
        if chave[0]:
            vistas[chave] = c["id"]
    if novos:
        novo = Q.acrescentar(_CARDS, novos)
        del _CARDS[:]
        _CARDS.extend(novo)
    return {"novos": len(novos), "repetidas": repetidas,
            "atualizadas": atualizadas, "ids": ids}


def acrescentar_series(series, origem=Q.RODAR_AGORA):
    with _TRAVA:
        conta = _acrescentar(series, origem)
    _gravar()
    return {"novos": conta["novos"], "repetidas": conta["repetidas"],
            "atualizadas": conta["atualizadas"]}


def pedir(series, com_speed=True):
    acrescentar_series(series)
    return cards()


ESCOLHAS_DO_CONTRATO = ("protocolos", "protocolos_3d", "comparacao",
                        "oar_fora", "modalidade")
MODOS_DO_CONTRATO = {"fast": "fast", "auto": "auto",
                     "personalizado": "perso", "perso": "perso"}


def _item_do_contrato(item, origem_padrao):
    if not isinstance(item, dict):
        return None, u"o item não é um objeto"
    pasta = (u"%s" % (item.get("pasta") or u"")).strip().strip('"')
    uid = (u"%s" % (item.get("uid") or u"")).strip()
    if not pasta:
        return None, u"faltou a pasta da série"
    if not os.path.isabs(pasta):
        return None, u"a pasta da série não é um caminho completo"
    if not uid:
        return None, u"faltou o uid da série"
    origem = (u"%s" % (item.get("origem") or origem_padrao or
                       Q.RODAR_AGORA)).strip().lower()
    if origem == Q.VIGIA:
        return None, (u"o vigia põe as séries dele pela varredura, e não "
                      u"por esta rota")
    if origem not in Q.MANUAIS:
        return None, u"origem desconhecida: %s" % origem[:40]
    modo_bruto = (u"%s" % (item.get("modo") or u"auto")).strip().lower()
    modo = MODOS_DO_CONTRATO.get(modo_bruto)
    if not modo:
        return None, u"modo desconhecido: %s" % modo_bruto[:40]
    chaves = item.get("chaves")
    if chaves is None:
        chaves = {}
    if not isinstance(chaves, dict):
        return None, u"as chaves das tasks vêm como {task: 0|1}"
    tasks = {}
    for t, v in chaves.items():
        t = (u"%s" % t).strip()
        if not t:
            continue
        try:
            tasks[t] = 1 if int(v) else 0
        except (TypeError, ValueError):
            return None, u"a chave da task %s não é 0 nem 1" % t[:40]
    destinos = item.get("copiar_rs_para") or []
    if not isinstance(destinos, (list, tuple)):
        return None, u"copiar_rs_para é uma lista de pastas"
    destinos = _destinos(destinos)
    if len(destinos) > TETO_DE_COPIAS:
        return None, frase_do_teto_de_copias(len(destinos))
    for d in destinos:
        if not os.path.isabs(d):
            return None, u"pasta de cópia sem caminho completo"
    rotulo = (u"%s" % (item.get("rotulo") or u"")).strip()[:120]
    carga = {"uid": uid, "pasta": pasta, "modo": modo}
    if tasks:
        carga["tasks"] = tasks
    if rotulo:
        carga["rotulo"] = rotulo
    for k in ESCOLHAS_DO_CONTRATO:
        if item.get(k) not in (None, u"", [], {}):
            carga[k] = item[k]
    # GUARDA: so o true literal substitui a entrega; a tela pede a confirmacao antes.
    if item.get("substituir") is True:
        carga["substituir"] = True
    if destinos:
        carga["copiar_rs_para"] = destinos
    return (origem, carga), u""


def enfileirar(itens, origem=None):
    if isinstance(itens, dict):
        itens = itens.get("itens")
    if not isinstance(itens, (list, tuple)) or not itens:
        return {"ok": False, "erro": u"nenhum item para a fila"}
    prontos, erros = [], []
    for k, it in enumerate(itens):
        r, erro = _item_do_contrato(it, origem)
        if erro:
            erros.append(u"item %d: %s" % (k + 1, erro))
        else:
            prontos.append(r)
    if erros:
        return {"ok": False, "erro": erros[0], "erros": erros}
    ids = []
    with _TRAVA:
        estouro = _estouro_de_copias(prontos)
        if not estouro:
            for origem_k, carga in prontos:
                ids.extend(_acrescentar([carga], origem_k)["ids"])
            vis = _visiveis()
            pos = dict((c.get("id"), i + 1) for i, c in enumerate(vis))
            cartoes = [{"id": i, "posicao": pos.get(i, 0)} for i in ids]
    if estouro:
        return {"ok": False, "erro": estouro, "erros": [estouro]}
    _gravar()
    return {"ok": True, "cartoes": cartoes}


def estado_publico(ids=None):
    quero = set(i for i in (ids or ()) if i)
    lote = _estado_do_lote()
    with _TRAVA:
        vis = _visiveis()
        fora = []
        for i, c in enumerate(vis):
            if quero and c.get("id") not in quero:
                continue
            fora.append({"id": c.get("id"), "rotulo": c.get("rotulo") or u"",
                         "estado": c.get("estado") or Q.ESPERANDO,
                         "posicao": i + 1, "origem": c.get("origem") or u"",
                         "mensagem": sem_caminho(c.get("mensagem") or u"")})
    d = {"ok": True, "cartoes": fora}
    # GUARDA: sem o andamento do lote o campo fica de fora; quem le trata a ausencia como desconhecido.
    if isinstance(lote, dict) and "rodando" in lote:
        d["rodando"] = bool(lote.get("rodando"))
    return d


def config_do_turno():
    with _TRAVA:
        for c in _CARDS:
            if c.get("tipo") == Q.OVERNIGHT:
                fora = {}
                tmp = dict((c.get("carga") or {}).get("temporarios") or {})
                if tmp:
                    fora["temporarios"] = tmp
                return fora
    return None


def turno_na_vez():
    with _TRAVA:
        turno = [c for c in _CARDS if c.get("tipo") == Q.OVERNIGHT]
        if not turno or turno[0].get("estado") != Q.ESPERANDO:
            return False
        return not any(Q.e_do_lote(c)
                       and c.get("estado") in (Q.ESPERANDO, Q.RODANDO)
                       for c in _CARDS)


def turno_agendado():
    with _TRAVA:
        return any(c.get("tipo") == Q.OVERNIGHT
                   and c.get("estado") in (Q.ESPERANDO, Q.RODANDO)
                   for c in _CARDS)


def fechar_turno(estado, motivo=u""):
    if estado == "feito":
        estado = Q.PRONTO
    if estado not in (Q.PRONTO, Q.FALHOU):
        raise ValueError(u"o card do turno fecha como pronto ou falhou, e nao "
                         u"`%s`" % estado)
    with _TRAVA:
        for k, c in enumerate(_CARDS):
            if c.get("tipo") == Q.OVERNIGHT:
                c2 = Q.terminar(c, estado)
                c2["motivo"] = (u"%s" % (motivo or u""))[:240]
                _CARDS[k] = c2
                break
        else:
            return False
    _gravar()
    return True


def marcar_turno_aberto(motivo=u""):
    with _TRAVA:
        for k, c in enumerate(_CARDS):
            if c.get("tipo") == Q.OVERNIGHT:
                c2 = Q.terminar(c, Q.RODANDO)
                c2["motivo"] = (u"%s" % (motivo or u""))[:240]
                _CARDS[k] = c2
                break
        else:
            return False
    _gravar()
    return True


def tirar_turno_cumprido():
    with _TRAVA:
        antes = len(_CARDS)
        atuais = [c for c in _CARDS
                  if not (c.get("tipo") == Q.OVERNIGHT
                          and c.get("estado") == Q.PRONTO)]
        del _CARDS[:]
        _CARDS.extend(atuais)
        mudou = len(_CARDS) != antes
    if mudou:
        _gravar()
    return mudou


def series_esperando():
    with _TRAVA:
        fora = []
        for c in _visiveis():
            if not Q.e_do_lote(c) or c.get("estado") != Q.ESPERANDO:
                continue
            carga = c.get("carga")
            if carga:
                fora.append(dict(carga))
    return fora


def ha_manual_esperando():
    with _TRAVA:
        return any(Q.e_do_lote(c) and c.get("estado") == Q.ESPERANDO
                   for c in _CARDS)


def _temporarios_do_pedido(tmp):
    if not isinstance(tmp, dict):
        return {}
    fora = {}
    for k, v in list(tmp.items())[:8]:
        fora[(u"%s" % k)[:40]] = (u"%s" % (v if v is not None else u""))[:1024]
    return fora


def overnight(ligado=True, rotulo=u"Turno da noite", temporarios=None):
    with _TRAVA:
        atuais = [c for c in _CARDS if c.get("tipo") != Q.OVERNIGHT]
        if ligado:
            extra = {}
            tmp = _temporarios_do_pedido(temporarios)
            if tmp:
                extra["carga"] = {"temporarios": tmp}
            atuais = Q.acrescentar(
                atuais,
                [Q.novo_card(Q.OVERNIGHT, rotulo=rotulo, extra=extra)])
        del _CARDS[:]
        _CARDS.extend(atuais)
    _gravar()
    return cards()


def mover(visivel, direcao):
    with _TRAVA:
        novo = Q.mover(_CARDS, visivel, direcao)
        del _CARDS[:]
        _CARDS.extend(novo)
    _gravar()
    return cards()


def mover_id(cid, direcao):
    with _TRAVA:
        vis = _visiveis()
        for i, c in enumerate(vis):
            if c.get("id") == cid:
                novo = Q.mover(vis, i, direcao)
                del _CARDS[:]
                _CARDS.extend(novo)
                break
    _gravar()
    return cards()


def cancelar(visivel):
    with _TRAVA:
        novo = Q.cancelar(_CARDS, visivel)
        del _CARDS[:]
        _CARDS.extend(novo)
    _gravar()
    return cards()


def tirar(cid):
    with _TRAVA:
        k = _pelo_id(cid)
        if k < 0 or not Q.pode_tirar(_CARDS[k]):
            return False
        del _CARDS[k]
    _gravar()
    return True


def repor(cid):
    with _TRAVA:
        k = _pelo_id(cid)
        if k < 0 or not Q.pode_repor(_CARDS[k]):
            return None
        velho = _CARDS[k]
        carga = dict(velho.get("carga") or {})
        carga.setdefault("uid", velho.get("uid"))
        carga.setdefault("pasta", velho.get("pasta"))
        if not carga.get("pasta"):
            return None
        if Q.executor(velho) == Q.VIGIA:
            carga.setdefault("modo", "auto")
        for c in _CARDS:
            if (c is not velho and _vivo(c)
                    and _chave_da_serie(c) == _chave_da_serie(carga)):
                return None
        novo = Q.novo_card(
            Q.SERIE, rotulo=velho.get("rotulo") or _rotulo_de(carga),
            uid=carga.get("uid") or u"", pasta=carga.get("pasta") or u"",
            origem=(velho.get("origem") if velho.get("origem") in Q.MANUAIS
                    else Q.RODAR_AGORA),
            extra={"carga": carga,
                   "copiar_rs_para": list(velho.get("copiar_rs_para") or ()),
                   "criado": _agora()})
        del _CARDS[k]
        arrumado = Q.acrescentar(_CARDS, [novo])
        del _CARDS[:]
        _CARDS.extend(arrumado)
        cid_novo = novo["id"]
    _gravar()
    return cid_novo


def _soltar_travas_mortas():
    soltar = _gancho("soltar_trava_morta")
    if soltar is None:
        return []
    with _TRAVA:
        alvos = [(c.get("id"), c.get("uid"), c.get("pasta")
                  or (c.get("carga") or {}).get("pasta"))
                 for c in _CARDS
                 if c.get("tipo") == Q.SERIE and c.get("estado") != Q.RODANDO
                 and c.get("uid")]
    soltas, vistos = [], set()
    for cid, uid, pasta in alvos:
        if not pasta or (uid, pasta) in vistos:
            continue
        vistos.add((uid, pasta))
        try:
            if soltar(pasta, uid):
                soltas.append(cid)
        except Exception:
            continue
    return soltas


def limpar_fila(com_falhas=False):
    soltas = _soltar_travas_mortas()
    with _TRAVA:
        ficam, saem = Q.limpar(_CARDS, com_falhas=com_falhas)
        del _CARDS[:]
        _CARDS.extend(ficam)
        falhas = [c for c in _CARDS if Q.pede_confirmacao_no_limpar(c)]
        parciais = [c for c in falhas if c.get("estado") == Q.PARCIAL]
        for cid in soltas:
            k = _pelo_id(cid)
            if k >= 0:
                c2 = dict(_CARDS[k])
                c2["trava_solta"] = True
                _CARDS[k] = c2
        complemento = len([c for c in _CARDS if c.get("estado") == Q.PARCIAL
                           and Q.tem_complemento_pendente(c)])
    _gravar()
    return {"tirados": len(saem), "travas_soltas": len(soltas),
            "falhas_restantes": len(falhas),
            "parciais_restantes": len(parciais),
            "esperam_complemento": complemento,
            "frase": frase_do_limpar(len(saem), len(soltas))}


def frase_do_limpar(tirados, soltas):
    partes = [u"%d cartão tirado" % tirados if tirados == 1
              else u"%d cartões tirados" % tirados]
    if soltas:
        partes.append(u"%d trava solta" % soltas if soltas == 1
                      else u"%d travas soltas" % soltas)
    return u", ".join(partes)


_PREFERENCIA = (Q.RODANDO, Q.ESPERANDO, Q.PULADO)


def _indice_da_serie(uid, pasta=u"", estados=_PREFERENCIA, executor=Q.LOTE):
    if not uid:
        return -1
    vis = _visiveis()
    for estado in estados:
        for c in vis:
            if (c.get("tipo") == Q.SERIE and Q.executor(c) == executor
                    and c.get("estado") == estado
                    and Q.mesma_serie(c, uid, pasta)):
                for k, bruto in enumerate(_CARDS):
                    if bruto is c:
                        return k
    return -1


def assumir(uid, pasta=u""):
    if not uid:
        return None
    with _TRAVA:
        _fechar_rodando_do_lote(u"terminou sem desfecho registrado")
        k = _indice_da_serie(uid, pasta, (Q.ESPERANDO, Q.PULADO))
        if k < 0:
            return False
        c2 = dict(_CARDS[k])
        c2["estado"] = Q.RODANDO
        c2["fim"] = 0
        c2["comecou"] = _agora()
        if not c2.get("complemento"):
            c2["mensagem"] = u""
        _CARDS[k] = c2
    _gravar()
    return True


def _fechar_rodando_do_lote(mensagem):
    for k, c in enumerate(_CARDS):
        if Q.e_do_lote(c) and c.get("estado") == Q.RODANDO:
            c2 = Q.terminar(c, Q.FALHOU)
            c2["mensagem"] = mensagem
            _CARDS[k] = c2


def fechar_rodando_do_lote(mensagem):
    with _TRAVA:
        _fechar_rodando_do_lote(mensagem)
    _gravar()


def _frase_da_memoria(pendentes):
    partes = []
    for p in pendentes or ():
        try:
            partes.append(u"%s (pedia %.1f GiB, havia %.1f GiB)"
                          % (p.get("task"), float(p.get("pedia_gib") or 0),
                             float(p.get("livre_gib") or 0)))
        except (TypeError, ValueError):
            partes.append(u"%s" % p.get("task"))
    return (u"ficou de fora por falta de memória: %s; a estação tenta de novo "
            u"a cada hora ociosa" % u", ".join(partes))


def _pendentes_limpos(pendentes):
    fora = []
    for p in pendentes or ():
        if not isinstance(p, dict) or not p.get("task"):
            continue
        d = {"task": u"%s" % p["task"]}
        for k in ("pedia_gib", "livre_gib"):
            try:
                d[k] = round(float(p.get(k)), 2)
            except (TypeError, ValueError):
                d[k] = None
        fora.append(d)
    return fora


def _aplicar_desfecho(c, estado, ja_concluida=False, faltou=None,
                      sem_estrutura=None, nao_contornavel=u"", mensagem=u"",
                      pendentes=None, parcial=u""):
    pendentes = _pendentes_limpos(pendentes)
    era_complemento = bool(c.get("complemento"))
    if estado in ("feito", Q.PRONTO) and (faltou or pendentes or parcial):
        estado = Q.PARCIAL
    if estado == "feito":
        estado = Q.PRONTO
    if estado == "skipped":
        estado = Q.PULADO
    c2 = Q.terminar(c, estado)
    for k in ("ja_concluida", "faltou", "sem_estrutura", "nao_contornavel",
              "complemento"):
        c2.pop(k, None)
    if ja_concluida:
        c2["ja_concluida"] = True
    if nao_contornavel:
        c2["nao_contornavel"] = (u"%s" % nao_contornavel)[:200]
    if faltou:
        c2["faltou"] = [u"%s" % x for x in faltou][:40]
    if sem_estrutura:
        c2["sem_estrutura"] = [u"%s" % x for x in sem_estrutura][:20]
    if c.get("comecou") and estado in Q.TERMINAIS:
        c2["segundos"] = int(max(0.0, _agora() - float(c["comecou"])))
    if estado in (Q.PRONTO, Q.PARCIAL):
        c2["pendentes_por_memoria"] = pendentes
        if pendentes:
            c2["tentativa_complemento"] = _agora()
            c2["mensagem"] = _frase_da_memoria(pendentes)
            if era_complemento:
                c2["mensagem"] = (u"tentou de novo às %s e ainda não coube — "
                                  % _hora() + c2["mensagem"])
        elif era_complemento:
            c2["mensagem"] = (u"completada às %s; substituiu a parcial"
                              % _hora())
        else:
            c2["mensagem"] = mensagem or u""
        if parcial:
            c2["mensagem"] = ((c2["mensagem"] + u" · ")
                              if c2.get("mensagem") else u"") + (
                u"%s" % parcial)[:240]
    else:
        c2["mensagem"] = mensagem or u""
        if not era_complemento:
            c2.pop("pendentes_por_memoria", None)
    return c2


def marcar(uid, estado, pasta=u"", ja_concluida=False, faltou=None,
           sem_estrutura=None, nao_contornavel=u"", mensagem=u"",
           pendentes=None, parcial=u""):
    with _TRAVA:
        k = _indice_da_serie(uid, pasta)
        if k >= 0:
            _CARDS[k] = _aplicar_desfecho(
                _CARDS[k], estado, ja_concluida=ja_concluida, faltou=faltou,
                sem_estrutura=sem_estrutura, nao_contornavel=nao_contornavel,
                mensagem=mensagem, pendentes=pendentes, parcial=parcial)
    _gravar()
    return cards()


def remover(uid, pasta=u""):
    with _TRAVA:
        k = _indice_da_serie(uid, pasta)
        if k >= 0:
            del _CARDS[k]
    _gravar()
    return cards()


def proxima_esperando(excluir=()):
    fora = set(excluir or ())
    with _TRAVA:
        for c in _visiveis():
            if not Q.e_do_lote(c) or c.get("estado") != Q.ESPERANDO:
                continue
            if _chave_da_serie(c) in fora:
                continue
            carga = c.get("carga")
            if carga:
                return dict(carga)
    return None


def ainda_esperando(uid, pasta=u""):
    with _TRAVA:
        return _indice_da_serie(uid, pasta, (Q.ESPERANDO, Q.PULADO)) >= 0


def skipped(uid, dono=u"", motivo=u""):
    with _TRAVA:
        novo = Q.marcar_pulado(_CARDS, uid, dono=dono or u"outra estação",
                               motivo=motivo)
        del _CARDS[:]
        _CARDS.extend(novo)
    _gravar()
    return cards()


def troca_de_paciente(livre=None):
    with _TRAVA:
        candidatos = [(_chave_da_serie(c), dict(c.get("carga") or {}))
                      for c in _CARDS
                      if c.get("tipo") == Q.SERIE and c.get("estado") == Q.PULADO]
    escolhidos = set()
    for chave, carga in candidatos:
        if livre is None:
            escolhidos.add(chave)
            continue
        try:
            if livre(carga or {"uid": chave[0], "pasta": chave[1]}):
                escolhidos.add(chave)
        except Exception:
            continue
    voltaram = []
    with _TRAVA:
        for k, c in enumerate(_CARDS):
            if (c.get("tipo") == Q.SERIE and c.get("estado") == Q.PULADO
                    and _chave_da_serie(c) in escolhidos):
                _CARDS[k] = Q.reativar_pulados([c])[0]
                voltaram.append(_chave_da_serie(c))
    if voltaram:
        _gravar()
    return voltaram


def vigia_na_fila(itens, total=None):
    itens = [dict(i) for i in (itens or ()) if i and i.get("uid")]
    with _TRAVA:
        rodando = set(c.get("uid") for c in _CARDS
                      if Q.e_do_vigia(c) and c.get("estado") == Q.RODANDO)
        itens = [i for i in itens if i["uid"] not in rodando]
        _VIGIA_NA_FILA["total"] = int(total if total is not None
                                      else len(itens))
        quero = itens[:TETO_DO_VIGIA_NA_TELA]
        velhos = dict((c.get("uid"), c) for c in _CARDS
                      if Q.e_do_vigia(c) and c.get("estado") == Q.ESPERANDO)
        resto = [c for c in _CARDS
                 if not (Q.e_do_vigia(c) and c.get("estado") == Q.ESPERANDO)]
        novos = []
        for i in quero:
            c = velhos.get(i["uid"])
            if c is None:
                c = Q.novo_card(Q.SERIE, rotulo=i.get("rotulo") or u"",
                                uid=i["uid"], pasta=i.get("pasta") or u"",
                                origem=Q.VIGIA)
            else:
                c = dict(c)
                c["rotulo"] = i.get("rotulo") or c.get("rotulo") or u""
                c["pasta"] = i.get("pasta") or c.get("pasta") or u""
            if i.get("mensagem"):
                c["mensagem"] = sem_caminho(u"%s" % i["mensagem"])[:200]
            novos.append(c)
        arrumado = Q.ordenar(resto + novos)
        del _CARDS[:]
        _CARDS.extend(arrumado)
    return len(quero)


def vigia_comecou(uid, rotulo=u"", pasta=u""):
    if not uid:
        return None
    with _TRAVA:
        for k, c in enumerate(_CARDS):
            if (Q.e_do_vigia(c) and c.get("estado") == Q.RODANDO):
                c2 = Q.terminar(c, Q.FALHOU)
                c2["mensagem"] = u"terminou sem desfecho registrado"
                _CARDS[k] = c2
        alvo = None
        for k, c in enumerate(_CARDS):
            if (Q.e_do_vigia(c) and c.get("estado") == Q.ESPERANDO
                    and c.get("uid") == uid):
                alvo = k
                break
        if alvo is None:
            c = Q.novo_card(Q.SERIE, rotulo=rotulo or u"", uid=uid,
                            pasta=pasta or u"", origem=Q.VIGIA)
            _CARDS.append(c)
            alvo = len(_CARDS) - 1
        c2 = dict(_CARDS[alvo])
        c2["estado"] = Q.RODANDO
        c2["comecou"] = _agora()
        if rotulo:
            c2["rotulo"] = rotulo
        if pasta:
            c2["pasta"] = pasta
        _CARDS[alvo] = c2
        cid = c2["id"]
        arrumado = Q.ordenar(_CARDS)
        del _CARDS[:]
        _CARDS.extend(arrumado)
    _gravar()
    return cid


VIGIA_VOLTA = "volta"


def vigia_terminou(uid, estado, mensagem=u"", faltou=None, pendentes=None,
                   ja_concluida=False, parcial=u""):
    with _TRAVA:
        k = -1
        for i, c in enumerate(_CARDS):
            if (Q.e_do_vigia(c) and c.get("estado") == Q.RODANDO
                    and c.get("uid") == uid):
                k = i
                break
        if k < 0:
            return False
        if estado == VIGIA_VOLTA:
            del _CARDS[k]
        else:
            _CARDS[k] = _aplicar_desfecho(
                _CARDS[k], estado, faltou=faltou, mensagem=mensagem,
                pendentes=pendentes, ja_concluida=ja_concluida,
                parcial=parcial)
    _gravar()
    return True


_FECHAR_AO_FIM = {"pedido": False, "desde": 0.0}


def pedir_fechar_ao_fim(sim=True):
    with _VEZ_COND:
        _FECHAR_AO_FIM["pedido"] = bool(sim)
        _FECHAR_AO_FIM["desde"] = _agora() if sim else 0.0
    return bool(sim)


def fechando_ao_fim():
    with _VEZ_COND:
        return bool(_FECHAR_AO_FIM["pedido"])


_VEZ_COND = threading.Condition(threading.Lock())
_VEZ = {"dono": None, "lote_quer": False, "desde": 0.0}


def quem_tem_a_vez():
    with _VEZ_COND:
        return {"dono": _VEZ["dono"], "lote_quer": bool(_VEZ["lote_quer"]),
                "desde": _VEZ["desde"]}


def tentar_a_vez(quem):
    with _VEZ_COND:
        if _VEZ["dono"] not in (None, quem):
            return False
        if quem == Q.VIGIA and _VEZ["lote_quer"]:
            return False
        _VEZ["dono"] = quem
        _VEZ["desde"] = _agora()
        return True


def querer_a_vez(quem=Q.LOTE):
    with _VEZ_COND:
        if quem == Q.LOTE:
            _VEZ["lote_quer"] = True


def esperar_a_vez(quem=Q.LOTE, parar=None, passo_s=0.5, ao_esperar=None):
    avisou = False
    with _VEZ_COND:
        if quem == Q.LOTE:
            _VEZ["lote_quer"] = True
        while _VEZ["dono"] not in (None, quem):
            if parar is not None:
                try:
                    if parar():
                        if quem == Q.LOTE:
                            _VEZ["lote_quer"] = False
                        _VEZ_COND.notify_all()
                        return False
                except Exception:
                    pass
            if not avisou and ao_esperar is not None:
                avisou = True
                dono = _VEZ["dono"]
                _VEZ_COND.release()
                try:
                    ao_esperar(dono)
                except Exception:
                    pass
                finally:
                    _VEZ_COND.acquire()
                continue
            _VEZ_COND.wait(passo_s)
        _VEZ["dono"] = quem
        _VEZ["desde"] = _agora()
        return True


def soltar_a_vez(quem):
    with _VEZ_COND:
        if _VEZ["dono"] == quem:
            _VEZ["dono"] = None
            _VEZ["desde"] = 0.0
        if quem == Q.LOTE:
            _VEZ["lote_quer"] = False
        _VEZ_COND.notify_all()


def avisar_espera(mensagem=FRASE_ESPERA_O_VIGIA):
    with _TRAVA:
        for k, c in enumerate(_CARDS):
            if Q.e_do_lote(c) and c.get("estado") == Q.ESPERANDO:
                c2 = dict(c)
                c2["mensagem"] = mensagem
                _CARDS[k] = c2
                break


def apagar_aviso_de_espera():
    with _TRAVA:
        for k, c in enumerate(_CARDS):
            if (Q.e_do_lote(c) and c.get("estado") == Q.ESPERANDO
                    and c.get("mensagem") == FRASE_ESPERA_O_VIGIA):
                c2 = dict(c)
                c2["mensagem"] = u""
                _CARDS[k] = c2


def complemento_na_vez(livre_gib, agora=None, intervalo_s=None):
    agora = _agora() if agora is None else agora
    intervalo_s = (INTERVALO_DO_COMPLEMENTO_S if intervalo_s is None
                   else intervalo_s)
    with _TRAVA:
        for c in _visiveis():
            if c.get("estado") != Q.PARCIAL or not Q.tem_complemento_pendente(c):
                continue
            ultima = float(c.get("tentativa_complemento") or 0)
            if agora - ultima < intervalo_s:
                continue
            pedia = max([float(p.get("pedia_gib") or 0)
                         for p in c.get("pendentes_por_memoria") or ()] or [0])
            if livre_gib is None or float(livre_gib) < pedia:
                continue
            carga = dict(c.get("carga") or {})
            carga.setdefault("uid", c.get("uid"))
            carga.setdefault("pasta", c.get("pasta"))
            if not carga.get("pasta"):
                continue
            return dict(c)
    return None


def preparar_complemento(cid):
    with _TRAVA:
        k = _pelo_id(cid)
        if k < 0:
            return None
        c = _CARDS[k]
        if c.get("estado") != Q.PARCIAL or not Q.tem_complemento_pendente(c):
            return None
        carga = dict(c.get("carga") or {})
        carga.setdefault("uid", c.get("uid"))
        carga.setdefault("pasta", c.get("pasta"))
        if Q.executor(c) == Q.VIGIA:
            carga.setdefault("modo", "auto")
        carga["substituir"] = True
        carga["complemento_de_memoria"] = [
            p.get("task") for p in c.get("pendentes_por_memoria") or ()]
        c2 = Q.terminar(c, Q.ESPERANDO)
        c2["executor"] = Q.LOTE
        c2["carga"] = carga
        c2["pasta"] = carga.get("pasta") or u""
        c2["complemento"] = True
        c2["tentativa_complemento"] = _agora()
        c2["mensagem"] = (u"tentando de novo a task que ficou de fora "
                          u"(%s)" % _hora())
        _CARDS[k] = c2
        arrumado = Q.ordenar(_CARDS)
        del _CARDS[:]
        _CARDS.extend(arrumado)
        fora = dict(carga)
    _gravar()
    return fora


def _nomes_do_rs(pasta, uid):
    try:
        nomes = os.listdir(pasta)
    except OSError:
        return []
    try:
        import radai_sets
        return list(radai_sets.arquivos_da_serie(nomes, uid))
    except Exception:
        cauda = u"_%s.dcm" % (u"%s" % uid)[-8:].lower()
        return [n for n in nomes
                if n.startswith(u"RS_RadAI_") and n.lower().endswith(cauda)]


def _sincroniza(caminho):
    try:
        import radai_archive
        nuvem, _motivo = radai_archive.em_pasta_sincronizada(caminho)
        return bool(nuvem)
    except Exception:
        return False


def copiar_entrega(uid, pasta=u""):
    with _TRAVA:
        k = _indice_da_serie(uid, pasta, Q.TERMINAIS + (Q.RODANDO,))
        if k < 0:
            return {"copiados": 0, "erros": []}
        c = _CARDS[k]
        destinos = list(c.get("copiar_rs_para") or ())
        origem = c.get("pasta") or (c.get("carga") or {}).get("pasta") or pasta
        cid = c.get("id")
    if not destinos or c.get("estado") not in (Q.PRONTO, Q.PARCIAL):
        return {"copiados": 0, "erros": []}
    nomes = _nomes_do_rs(origem, uid)
    erros, copiados = [], 0
    if not nomes:
        erros.append(u"nenhum RTSTRUCT RadAI desta série ao lado dela")
    for destino in destinos:
        if not nomes:
            break
        if os.path.normcase(os.path.abspath(destino)) == \
                os.path.normcase(os.path.abspath(origem)):
            continue
        if not os.path.isdir(destino):
            erros.append(u"a pasta de cópia não existe mais")
            continue
        if _sincroniza(destino):
            erros.append(u"a pasta de cópia sincroniza com a nuvem: não copio "
                         u"dado de paciente para ela")
            continue
        for n in nomes:
            alvo = os.path.join(destino, n)
            tmp = alvo + u".copiando"
            try:
                shutil.copy2(os.path.join(origem, n), tmp)
                os.replace(tmp, alvo)
                copiados += 1
            except OSError as e:
                erros.append(u"não copiei um RTSTRUCT (%s)" % type(e).__name__)
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    with _TRAVA:
        k = _pelo_id(cid)
        if k >= 0:
            c2 = dict(_CARDS[k])
            frase = (u"RTSTRUCT copiado para %d pasta(s)"
                     % len([d for d in destinos if os.path.isdir(d)])
                     if copiados else u"")
            if erros:
                frase = (frase + u"; " if frase else u"") + erros[0]
            if frase:
                c2["mensagem"] = ((c2.get("mensagem") or u"") + u" · "
                                  if c2.get("mensagem") else u"") + frase
            _CARDS[k] = c2
    _gravar()
    return {"copiados": copiados, "erros": erros}


def pasta_da_fila():
    alt = (os.environ.get(VARIAVEL_DA_PASTA) or u"").strip().strip('"')
    if alt:
        return alt
    # GUARDA: acervo isolado (bateria, prova) isola a fila junto; sem isso o teste grava no C: de quem roda.
    acervo = (os.environ.get("RADAI_CALIB_DIR") or u"").strip().strip('"')
    if acervo:
        return os.path.join(acervo, u"fila")
    disco = (os.environ.get("SystemDrive") or u"C:").rstrip(u"\\/")
    return os.path.join(disco + os.sep, u"RADIOTERAPIA_AI", u"fila")


def arquivo_da_fila():
    return os.path.join(pasta_da_fila(), NOME_DO_ARQUIVO)


def arquivo_do_indice():
    try:
        import radai_archive
        return str(radai_archive.raiz() / NOME_DO_INDICE)
    except Exception:
        return u""


def estado_da_gravacao():
    return {"ligada": bool(_PERSISTIR["ligada"]),
            "erro": _PERSISTIR["erro"], "gravacoes": _PERSISTIR["gravacoes"]}


# GUARDA: so o que nao identifica o paciente vai para o arquivo da fila; o resto mora no indice do acervo.
ESCOLHA_PERSISTIDA = ("modo", "tasks", "protocolos", "protocolos_3d",
                      "comparacao", "oar_fora", "substituir", "so_pos",
                      "modalidade", "tasks_extra", "motores_extra", "topo",
                      "estudos", "complemento_de_memoria",
                      "protocolo_proprio", "achado_declarado")
CAMPOS_DO_ARQUIVO = ("id", "tipo", "origem", "executor", "estado", "uid",
                     "fim", "criado", "dono", "pendentes_por_memoria",
                     "tentativa_complemento", "ja_concluida",
                     "complemento", "trava_solta")
CAMPOS_DO_INDICE = ("pasta", "rotulo", "copiar_rs_para", "mensagem", "motivo",
                    "faltou", "sem_estrutura", "nao_contornavel")


def _ao_arquivo(c):
    d = dict((k, c.get(k)) for k in CAMPOS_DO_ARQUIVO if k in c)
    escolha = {}
    for k in ESCOLHA_PERSISTIDA:
        v = (c.get("carga") or {}).get(k)
        if v not in (None, u"", [], {}):
            escolha[k] = v
    if escolha:
        d["escolha"] = escolha
    return d


def _ao_indice(c):
    d = dict((k, c.get(k)) for k in CAMPOS_DO_INDICE if c.get(k))
    carga = dict(c.get("carga") or {})
    for k in ESCOLHA_PERSISTIDA:
        carga.pop(k, None)
    if carga:
        d["carga"] = carga
    return d


def _persistiveis():
    return [c for c in _CARDS
            if not (Q.e_do_vigia(c) and c.get("estado") == Q.ESPERANDO)]


def _escrever_json(caminho, dado):
    pasta = os.path.dirname(caminho)
    if pasta and not os.path.isdir(pasta):
        os.makedirs(pasta)
    tmp = caminho + u".novo"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(dado, f, ensure_ascii=False, indent=0)
    os.replace(tmp, caminho)


def _gravar():
    if not _PERSISTIR["ligada"]:
        return False
    fila_p, indice_p = arquivo_da_fila(), arquivo_do_indice()
    with _GRAVACAO:
        with _TRAVA:
            lista = [dict(c) for c in _persistiveis()]
        if not lista and not os.path.isfile(fila_p):
            return True
        for p in (fila_p, indice_p):
            if not p:
                _PERSISTIR["erro"] = u"o acervo não foi achado"
                return False
            if _sincroniza(p):
                _PERSISTIR["erro"] = (u"a fila não é gravada: a pasta "
                                      u"sincroniza com a nuvem")
                return False
        try:
            _escrever_json(fila_p, {
                "versao": VERSAO_DO_ARQUIVO,
                "gravado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cartoes": [_ao_arquivo(c) for c in lista]})
            _escrever_json(indice_p, {
                "versao": VERSAO_DO_ARQUIVO,
                "series": dict((c["id"], _ao_indice(c)) for c in lista)})
        except Exception as e:
            _PERSISTIR["erro"] = u"a fila não foi gravada (%s)" % type(e).__name__
            return False
        _PERSISTIR["erro"] = u""
        _PERSISTIR["gravacoes"] += 1
    return True


def _ler_json(caminho):
    try:
        with io.open(caminho, encoding="utf-8-sig") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _existe(carga):
    if not isinstance(carga, dict):
        return False
    z = carga.get("zip")
    if z:
        return os.path.isfile(str(z))
    p = carga.get("pasta")
    return bool(p) and os.path.isdir(str(p))


def _achar_pasta(uid):
    try:
        import radai_archive
        for reg in radai_archive.ler_acervo():
            if reg.get("uid") == uid and reg.get("pasta") \
                    and os.path.isdir(str(reg["pasta"])):
                return str(reg["pasta"])
    except Exception:
        pass
    achar = _gancho("achar_pasta")
    if achar is not None:
        try:
            p = achar(uid)
            if p and os.path.isdir(str(p)):
                return str(p)
        except Exception:
            pass
    return u""


def carregar(log=None):
    fila_p, indice_p = arquivo_da_fila(), arquivo_do_indice()
    _PERSISTIR["ligada"] = True
    for p in (fila_p, indice_p):
        if p and _sincroniza(p):
            _PERSISTIR["ligada"] = False
            _PERSISTIR["erro"] = (u"a fila não é gravada: a pasta sincroniza "
                                  u"com a nuvem")
            if log:
                log(u"fila: NAO gravo a fila em disco -- %s sincroniza com a "
                    u"nuvem" % os.path.dirname(p))
            return {"voltaram": 0, "falharam": 0, "nao_encontradas": 0}
    dado = _ler_json(fila_p) if os.path.isfile(fila_p) else {}
    indice = (_ler_json(indice_p).get("series") or {}) if indice_p and \
        os.path.isfile(indice_p) else {}
    voltaram, falharam, sumidas, soltar = [], 0, 0, []
    for e in dado.get("cartoes") or ():
        if not isinstance(e, dict) or not e.get("id"):
            continue
        estado = e.get("estado")
        if estado not in Q.ESTADOS or estado == Q.PRONTO:
            continue
        if Q.executor(e) == Q.VIGIA and estado == Q.ESPERANDO:
            continue
        # GUARDA: o turno aberto acaba com o processo que o abriu; o card dele nao volta como turno a abrir nem como falha.
        if Q.e_turno(e) and estado == Q.RODANDO:
            continue
        c = dict(e)
        ind = indice.get(e["id"]) or {}
        for k in CAMPOS_DO_INDICE:
            if ind.get(k):
                c[k] = ind[k]
        carga = dict(ind.get("carga") or {})
        carga.update(e.get("escolha") or {})
        c.pop("escolha", None)
        if c.get("tipo") == Q.SERIE:
            carga.setdefault("uid", c.get("uid"))
            if c.get("pasta"):
                carga.setdefault("pasta", c.get("pasta"))
        c["carga"] = carga
        c.setdefault("rotulo", u"série …%s" % str(c.get("uid") or u"")[-8:])
        c.setdefault("mensagem", u"")
        if estado == Q.RODANDO:
            c = Q.terminar(c, Q.FALHOU)
            c["mensagem"] = FRASE_FECHOU_NO_MEIO
            c["executor"] = Q.executor(c)
            falharam += 1
            soltar.append(c)
        if c.get("tipo") == Q.SERIE and not _existe(carga):
            achada = _achar_pasta(c.get("uid"))
            if achada:
                carga["pasta"] = achada
                c["pasta"] = achada
            else:
                c = Q.terminar(c, Q.FALHOU)
                c["mensagem"] = FRASE_NAO_ENCONTRADA
                c.pop("pendentes_por_memoria", None)
                sumidas += 1
        voltaram.append(c)
    with _TRAVA:
        presentes = set(c.get("id") for c in _CARDS)
        for c in voltaram:
            if c.get("id") not in presentes:
                _CARDS.append(c)
        arrumado = Q.ordenar(_CARDS)
        del _CARDS[:]
        _CARDS.extend(arrumado)
    soltas = 0
    pegar = _gancho("soltar_trava_morta")
    for c in soltar:
        p = c.get("pasta") or (c.get("carga") or {}).get("pasta")
        if pegar is not None and p and c.get("uid"):
            try:
                if pegar(p, c["uid"]):
                    soltas += 1
            except Exception:
                pass
    _gravar()
    if log and voltaram:
        log(u"fila: %d cartao(oes) voltaram do disco (%d fechados no meio, "
            u"%d serie(s) nao encontrada(s), %d trava(s) desta maquina "
            u"solta(s))" % (len(voltaram), falharam, sumidas, soltas))
    return {"voltaram": len(voltaram), "falharam": falharam,
            "nao_encontradas": sumidas, "travas_soltas": soltas}


def ao_fechar():
    with _TRAVA:
        for k, c in enumerate(_CARDS):
            if c.get("tipo") == Q.SERIE and c.get("estado") == Q.RODANDO:
                c2 = Q.terminar(c, Q.FALHOU)
                c2["mensagem"] = FRASE_FECHOU_NO_MEIO
                _CARDS[k] = c2
        fica = [c for c in _CARDS
                if not (c.get("estado") == Q.PRONTO and c.get("tipo") == Q.SERIE)
                and not (Q.e_turno(c) and c.get("estado") == Q.RODANDO)]
        del _CARDS[:]
        _CARDS.extend(fica)
    return _gravar()


def montar(app):
    from fastapi import Request

    def _pacote():
        lote = _estado_do_lote()
        return {"cards": com_andamento(para_tela(cards()), lote),
                "resumo": resumo(), "lote": botoes_do_lote(lote),
                "vez": quem_tem_a_vez(), "gravacao": estado_da_gravacao(),
                "maquina": _maquina()}

    def _erro(e):
        return {"cards": [], "erro": "%s: %s" % (type(e).__name__, e)}

    async def _corpo(request):
        try:
            c = await request.json()
        except Exception:
            c = None
        return c if isinstance(c, dict) else {}

    @app.get("/api/fila")
    def _ler():
        try:
            return _pacote()
        except Exception as e:
            return dict(_erro(e), resumo={})

    @app.post("/api/fila/estado")
    async def _estado(request: Request):
        try:
            c = await _corpo(request)
            return estado_publico(c.get("ids"))
        except Exception as e:
            return {"ok": False, "erro": "%s: %s" % (type(e).__name__, e)}

    @app.post("/api/fila/enfileirar")
    async def _enfileirar(request: Request):
        try:
            return enfileirar(await _corpo(request))
        except Exception as e:
            return {"ok": False, "erro": "%s: %s" % (type(e).__name__, e)}

    @app.post("/api/fila/mover")
    async def _mover(request: Request):
        try:
            c = await _corpo(request)
            if c.get("id"):
                mover_id(str(c["id"]), c.get("d"))
            else:
                mover(c.get("i"), c.get("d"))
            return _pacote()
        except Exception as e:
            return _erro(e)

    @app.post("/api/fila/overnight")
    async def _overnight(request: Request):
        try:
            c = await _corpo(request)
            overnight(bool(c.get("ligado", True)),
                      temporarios=c.get("temporarios"))
            return _pacote()
        except Exception as e:
            return _erro(e)

    @app.post("/api/fila/cancelar")
    async def _cancelar(request: Request):
        try:
            c = await _corpo(request)
            cid = c.get("id")
            if cid:
                tirar(str(cid))
            else:
                cancelar(c.get("i"))
            return _pacote()
        except Exception as e:
            return _erro(e)

    @app.post("/api/fila/repor")
    async def _repor(request: Request):
        try:
            c = await _corpo(request)
            novo = repor(str(c.get("id") or u""))
            d = _pacote()
            d["ok"] = bool(novo)
            d["id"] = novo or u""
            if not novo:
                d["aviso"] = u"esta série não pode voltar à fila agora"
            return d
        except Exception as e:
            return _erro(e)

    @app.post("/api/fila/limpar")
    async def _limpar(request: Request):
        try:
            c = await _corpo(request)
            r = limpar_fila(com_falhas=bool(c.get("com_falhas")))
            d = _pacote()
            d.update(r)
            d["removidos"] = r["tirados"]
            return d
        except Exception as e:
            return _erro(e)

    return app


_AVISOU_ANDAMENTO = []


def _estado_do_lote():
    try:
        import radai_batch
    except Exception:
        return {}
    try:
        return radai_batch.andamento()
    except Exception as e:
        if not _AVISOU_ANDAMENTO:
            _AVISOU_ANDAMENTO.append(1)
            try:
                print(u"[fila] o andamento do lote nao foi lido (%s: %s) -- "
                      u"os botoes Pausar e Cancelar da barra podem aparecer "
                      u"desabilitados com um lote rodando"
                      % (type(e).__name__, str(e)[:160]))
            except Exception:
                pass
        return {}


def com_andamento(lista, lote):
    fora = []
    ok = bool((lote or {}).get("rodando"))
    for c in (lista or ()):
        d = dict(c)
        if (ok and d.get("estado") == Q.RODANDO and d.get("tipo") == Q.SERIE
                and Q.executor(d) == Q.LOTE):
            d["andamento"] = {"etapa": lote.get("etapa") or u"",
                              "parte": lote.get("parte") or u"",
                              "segundos": lote.get("segundos"),
                              "feitas": lote.get("feitas", 0),
                              "total": lote.get("total", 0)}
        fora.append(d)
    return fora


def botoes_do_lote(lote):
    lote = lote or {}
    return {"rodando": bool(lote.get("rodando")),
            "pausa_pedida": bool(lote.get("pausar")),
            "cancelando": bool(lote.get("cancelar"))}
