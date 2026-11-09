# -*- coding: utf-8 -*-
import itertools
import os
import threading

SERIE = "serie"
OVERNIGHT = "overnight"

TIPOS = (SERIE, OVERNIGHT)

ESPERANDO = "esperando"
PULADO = "pulado"
RODANDO = "rodando"
PRONTO = "pronto"
PARCIAL = "parcial"
FALHOU = "falhou"
CANCELADO = "cancelado"

SKIPPED = PULADO
FEITO = PRONTO

ESTADOS = (ESPERANDO, PULADO, RODANDO, PRONTO, PARCIAL, FALHOU, CANCELADO)
NA_ESPERA = (ESPERANDO, PULADO)
TERMINAIS = (PRONTO, PARCIAL, FALHOU, CANCELADO)
SEM_SUCESSO = (FALHOU, CANCELADO)

RODAR_AGORA = "rodar_agora"
DICOMBRIDGE = "dicombridge"
NIDUS = "nidus"
VIGIA = "vigia"
NEURO = "neuro"

ORIGENS = (RODAR_AGORA, DICOMBRIDGE, NIDUS, NEURO, VIGIA)
MANUAIS = (RODAR_AGORA, DICOMBRIDGE, NIDUS, NEURO)

LOTE = "lote"
EXECUTORES = (LOTE, VIGIA, NEURO)

FAIXA_RODANDO = 0
FAIXA_MANUAL = 1
FAIXA_VIGIA = 2
FAIXA_TURNO = 3
FAIXA_FIM = 4

_SEQ = itertools.count(1)
_SEQ_TRAVA = threading.Lock()


def _proximo_seq():
    with _SEQ_TRAVA:
        return next(_SEQ)


def novo_id():
    return os.urandom(6).hex()


def novo_card(tipo, rotulo=u"", uid=u"", pasta=u"", extra=None,
              origem=RODAR_AGORA):
    origem = origem if origem in ORIGENS else RODAR_AGORA
    d = {"id": novo_id(), "tipo": tipo, "origem": origem,
         "executor": origem if origem in (VIGIA, NEURO) else LOTE,
         "rotulo": rotulo or u"", "uid": uid or u"", "pasta": pasta or u"",
         "estado": ESPERANDO, "dono": u"", "segundos": None,
         "mensagem": u"", "fim": 0}
    if extra:
        d.update(extra)
    return d


def executor(c):
    c = c or {}
    e = c.get("executor")
    if e in EXECUTORES:
        return e
    return c.get("origem") if c.get("origem") in (VIGIA, NEURO) else LOTE


def e_do_vigia(c):
    return executor(c) == VIGIA and (c or {}).get("tipo") == SERIE


def e_do_lote(c):
    return executor(c) == LOTE and (c or {}).get("tipo") == SERIE


def e_turno(c):
    return (c or {}).get("tipo") == OVERNIGHT


def faixa(c):
    c = c or {}
    estado = c.get("estado")
    if e_turno(c):
        return FAIXA_TURNO
    if estado == RODANDO:
        return FAIXA_RODANDO
    if estado in TERMINAIS:
        return FAIXA_FIM
    if executor(c) == VIGIA:
        return FAIXA_VIGIA
    return FAIXA_MANUAL


def terminar(c, estado):
    novo = dict(c or {})
    novo["estado"] = estado
    if estado in TERMINAIS:
        novo["fim"] = _proximo_seq()
    else:
        novo["fim"] = 0
    return novo


def ordenar(cards):
    cards = list(cards or ())

    def chave(c):
        f = faixa(c)
        if f == FAIXA_FIM:
            return (f, -int((c or {}).get("fim") or 0))
        return (f, 0)

    return sorted(cards, key=chave)


def acrescentar(cards, novos):
    cards = list(cards or ())
    novos = [c for c in (novos or ()) if c]
    return ordenar(cards + novos)


def pode_mover(c):
    return e_manual(c) and (c or {}).get("estado") in NA_ESPERA


def mover(cards, indice, direcao):
    cards = ordenar(cards)
    try:
        i = int(indice)
        d = int(direcao)
    except (TypeError, ValueError):
        return cards
    if d not in (-1, 1) or not (0 <= i < len(cards)):
        return cards
    j = i + d
    if not (0 <= j < len(cards)):
        return cards
    if not (pode_mover(cards[i]) and pode_mover(cards[j])):
        return cards
    cards[i], cards[j] = cards[j], cards[i]
    return cards


def pode_tirar(c):
    c = c or {}
    if e_turno(c):
        return c.get("estado") != RODANDO
    if c.get("estado") == RODANDO:
        return False
    if c.get("estado") in NA_ESPERA and executor(c) == VIGIA:
        return False
    return True


def pode_repor(c):
    c = c or {}
    return (executor(c) != NEURO and c.get("tipo") == SERIE and c.get("estado") in SEM_SUCESSO
            and bool(c.get("uid")))


def cancelar(cards, indice):
    cards = ordenar(cards)
    try:
        i = int(indice)
    except (TypeError, ValueError):
        return cards
    if not (0 <= i < len(cards)):
        return cards
    if not pode_tirar(cards[i]):
        return cards
    del cards[i]
    return cards


def tem_complemento_pendente(c):
    return bool((c or {}).get("pendentes_por_memoria"))


def sai_no_limpar(c, com_falhas=False):
    c = c or {}
    if e_turno(c):
        return com_falhas and c.get("estado") in SEM_SUCESSO
    estado = c.get("estado")
    if estado == PRONTO:
        return True
    # GUARDA: o parcial nao e sucesso; sai so com a confirmacao, e nunca enquanto o complemento espera.
    if estado == PARCIAL:
        return bool(com_falhas) and not tem_complemento_pendente(c)
    if estado in SEM_SUCESSO:
        return bool(com_falhas)
    return False


def pede_confirmacao_no_limpar(c):
    return sai_no_limpar(c, True) and not sai_no_limpar(c, False)


def limpar(cards, com_falhas=False):
    ficam, saem = [], []
    for c in (cards or ()):
        (saem if sai_no_limpar(c, com_falhas) else ficam).append(c)
    return ficam, saem


def marcar_pulado(cards, uid, dono=u"", motivo=u""):
    cards = list(cards or ())
    if not uid:
        return cards
    for k, c in enumerate(cards):
        if (c.get("uid") == uid and executor(c) == LOTE
                and c.get("estado") in (ESPERANDO, RODANDO)):
            novo = dict(c)
            novo["estado"] = PULADO
            novo["dono"] = dono or u""
            novo["motivo"] = motivo or u""
            cards[k] = novo
    return cards


def reativar_pulados(cards):
    cards = list(cards or ())
    for k, c in enumerate(cards):
        if c.get("estado") == PULADO:
            novo = dict(c)
            novo["estado"] = ESPERANDO
            novo["dono"] = u""
            novo.pop("motivo", None)
            cards[k] = novo
    return cards


def pendentes(cards):
    return [c for c in ordenar(cards)
            if c.get("tipo") == SERIE and c.get("estado") in (ESPERANDO,
                                                              RODANDO)]


def mesma_serie(card, uid, pasta=u""):
    c = card or {}
    if not uid or c.get("uid") != uid:
        return False
    p1, p2 = str(c.get("pasta") or u""), str(pasta or u"")
    return (not p1) or (not p2) or p1 == p2


def resumo(cards):
    cards = list(cards or ())
    por = {}
    for c in cards:
        e = c.get("estado") or ESPERANDO
        por[e] = por.get(e, 0) + 1
    manuais = [c for c in cards if e_manual(c)]
    return {"total": len(cards),
            "esperando": por.get(ESPERANDO, 0),
            "pulado": por.get(PULADO, 0),
            "rodando": por.get(RODANDO, 0),
            "pronto": por.get(PRONTO, 0),
            "parcial": por.get(PARCIAL, 0),
            "falhou": por.get(FALHOU, 0),
            "cancelado": por.get(CANCELADO, 0),
            "manuais_esperando": len([c for c in manuais
                                      if c.get("estado") == ESPERANDO]),
            "vigia_esperando": len([c for c in cards if e_do_vigia(c)
                                    and c.get("estado") == ESPERANDO]),
            "series": len([c for c in cards if c.get("tipo") == SERIE]),
            "tem_overnight": any(e_turno(c) for c in cards)}


def conferir_ordem(cards):
    cards = list(cards or ())
    ultima = -1
    for c in cards:
        f = faixa(c)
        if f < ultima:
            raise ValueError(
                u"o card `%s` (%s, %s) esta fora da faixa dele: a tela "
                u"mostraria uma ordem que nao e a do trabalho. Quem montou a "
                u"lista nao passou por `ordenar`."
                % (c.get("rotulo") or c.get("tipo"), c.get("estado"),
                   c.get("origem")))
        ultima = f
    return True


def e_manual(c):
    return ((c or {}).get("tipo") == SERIE
            and executor(c) in (LOTE, NEURO))
