# -*- coding: utf-8 -*-
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _cleanup
_cleanup.adotar_prefixo('radai_fila_subst_')

import radai_queue as Q

_R = []


def checar(nome, ok, detalhe=""):
    _R.append((nome, bool(ok), detalhe))
    if not ok:
        print(u"  FALHA  %s%s" % (nome, ("  [%s]" % detalhe) if detalhe else ""))
    return bool(ok)


def secao(t):
    print(u"\n-- %s --" % t)


def _serie(r, uid=None, origem=Q.RODAR_AGORA, estado=None):
    c = Q.novo_card(Q.SERIE, rotulo=r, uid=uid or r.lower(), origem=origem)
    if estado:
        c = Q.terminar(c, estado)
    return c


def _rot(cards):
    return [c.get("rotulo") or c.get("tipo") for c in cards]


def teste_a_fila_nasce_vazia():
    secao(u"a fila nasce vazia")
    checar(u"ordenar([]) e vazia", Q.ordenar([]) == [])
    checar(u"acrescentar em vazia devolve os novos",
           _rot(Q.acrescentar([], [_serie(u"A")])) == [u"A"])
    r = Q.resumo([])
    checar(u"o resumo de vazia e zero", r["total"] == 0 and not r["tem_overnight"])
    for f in (lambda: Q.mover([], 0, 1), lambda: Q.cancelar([], 0),
              lambda: Q.marcar_pulado([], u"x"), lambda: Q.reativar_pulados([]),
              lambda: Q.pendentes([]), lambda: Q.limpar([])):
        try:
            f()
            ok = True
        except Exception:
            ok = False
        checar(u"a operacao nao levanta em fila vazia", ok)
    checar(u"o teste de velocidade que ninguem pedia saiu",
           not hasattr(Q, "com_speed_tests") and not hasattr(Q, "SPEED"))
    c = Q.novo_card(Q.SERIE, rotulo=u"A")
    checar(u"todo card nasce com id, origem e executor",
           len(c.get("id") or u"") == 12 and c["origem"] == Q.RODAR_AGORA
           and c["executor"] == Q.LOTE, str(c))
    checar(u"  e o id nao se repete",
           len(set(Q.novo_card(Q.SERIE)["id"] for _ in range(200))) == 200)
    v = Q.novo_card(Q.SERIE, origem=Q.VIGIA)
    checar(u"o card do vigia e executado pelo vigia", v["executor"] == Q.VIGIA)
    checar(u"origem desconhecida vira «Rodar agora»",
           Q.novo_card(Q.SERIE, origem=u"xyz")["origem"] == Q.RODAR_AGORA)


def teste_as_faixas():
    secao(u"as faixas: quem roda, o que entra a mao, o vigia, o turno, o fim")
    on = Q.novo_card(Q.OVERNIGHT, rotulo=u"ON")
    v1 = _serie(u"V1", origem=Q.VIGIA)
    m1 = _serie(u"M1")
    b1 = _serie(u"B1", origem=Q.DICOMBRIDGE)
    r1 = _serie(u"R1")
    r1["estado"] = Q.RODANDO
    p1 = _serie(u"P1", estado=Q.PRONTO)
    f1 = _serie(u"F1", estado=Q.FALHOU)
    f = Q.ordenar([on, v1, p1, m1, f1, r1, b1])
    checar(u"rodando, manual, vigia, turno, terminados",
           _rot(f) == [u"R1", u"M1", u"B1", u"V1", u"ON", u"F1", u"P1"],
           str(_rot(f)))
    checar(u"  e os terminados vem do mais recente para o mais antigo",
           _rot(f)[-2:] == [u"F1", u"P1"], str(_rot(f)))
    checar(u"  e a ordem passa na trava", Q.conferir_ordem(f) is True)
    novo = Q.acrescentar(f, [_serie(u"NOVO", origem=Q.NIDUS)])
    checar(u"pedido novo a mao entra DEPOIS dos manuais e ANTES do vigia",
           _rot(novo).index(u"NOVO") == 3 and _rot(novo)[4] == u"V1",
           str(_rot(novo)))
    mv = Q.novo_card(Q.SERIE, rotulo=u"COMPL", origem=Q.VIGIA,
                     extra={"executor": Q.LOTE})
    g = Q.ordenar([v1, mv])
    checar(u"o complemento de uma serie do vigia roda pelo lote, na faixa "
           u"manual", _rot(g) == [u"COMPL", u"V1"], str(_rot(g)))


def teste_subir_e_descer():
    secao(u"subir e descer, e o que NAO se move")

    def nova():
        a = _serie(u"A")
        a["estado"] = Q.RODANDO
        return [a, _serie(u"B"), _serie(u"C"), _serie(u"V", origem=Q.VIGIA),
                Q.novo_card(Q.OVERNIGHT, rotulo=u"ON")]

    f = nova()
    checar(u"subir C troca com B",
           _rot(Q.mover(f, 2, -1)) == [u"A", u"C", u"B", u"V", u"ON"],
           str(_rot(Q.mover(f, 2, -1))))
    checar(u"B nao sobe por cima do que RODA",
           _rot(Q.mover(f, 1, -1)) == [u"A", u"B", u"C", u"V", u"ON"])
    checar(u"C nao desce para a faixa do vigia",
           _rot(Q.mover(f, 2, 1)) == [u"A", u"B", u"C", u"V", u"ON"])
    checar(u"o card do VIGIA nao sobe (a ordem dele e do vigia)",
           _rot(Q.mover(f, 3, -1)) == [u"A", u"B", u"C", u"V", u"ON"])
    checar(u"o OVERNIGHT nao sobe",
           _rot(Q.mover(f, 4, -1)) == [u"A", u"B", u"C", u"V", u"ON"])
    checar(u"o que RODA nao desce",
           _rot(Q.mover(f, 0, 1)) == [u"A", u"B", u"C", u"V", u"ON"])
    for i, d in ((99, 1), (-1, 1), (1, 0), (1, 7), (None, 1), (1, None)):
        checar(u"mover(%r,%r) devolve a lista igual" % (i, d),
               _rot(Q.mover(f, i, d)) == [u"A", u"B", u"C", u"V", u"ON"])
    antes = nova()
    _ = Q.mover(antes, 2, -1)
    checar(u"mover nao altera a lista recebida",
           _rot(antes) == [u"A", u"B", u"C", u"V", u"ON"], str(_rot(antes)))
    p = _serie(u"P", estado=Q.PULADO)
    checar(u"o pulado (outra estacao) tambem sobe e desce",
           _rot(Q.mover([_serie(u"X"), p], 1, -1)) == [u"P", u"X"])


def teste_tirar_um_cartao():
    secao(u"o X tira o card, e nao tira o que nao pode")
    a = _serie(u"A")
    a["estado"] = Q.RODANDO
    f = [a, _serie(u"B"), _serie(u"C"), _serie(u"V", origem=Q.VIGIA),
         _serie(u"F", estado=Q.FALHOU)]
    g = Q.cancelar(f, 1)
    checar(u"o card que espera sai da lista", _rot(g) == [u"A", u"C", u"V", u"F"],
           str(_rot(g)))
    checar(u"a lista de entrada nao muda (a tela compara com a anterior)",
           _rot(f) == [u"A", u"B", u"C", u"V", u"F"], str(_rot(f)))
    checar(u"o que RODA nao sai por aqui (para isso existe o Cancelar)",
           _rot(Q.cancelar(f, 0)) == _rot(Q.ordenar(f)))
    checar(u"o que o VIGIA achou e espera nao sai pelo X",
           _rot(Q.cancelar(f, 3)) == _rot(Q.ordenar(f)))
    checar(u"o que terminou sai pelo X", u"F" not in _rot(Q.cancelar(f, 4)))
    checar(u"o que falhou pode voltar a fila, o que esta pronto nao",
           Q.pode_repor(_serie(u"x", estado=Q.FALHOU))
           and Q.pode_repor(_serie(u"x", estado=Q.CANCELADO))
           and not Q.pode_repor(_serie(u"x", estado=Q.PRONTO))
           and not Q.pode_repor(_serie(u"x")))


def _estado_do_turno(F):
    for c in F.cards():
        if c.get("tipo") == Q.OVERNIGHT:
            return c.get("estado")
    return None


def teste_o_que_o_limpar_tira():
    secao(u"o que o Limpar tira, e o que fica")
    pend = _serie(u"PARC_C", estado=Q.PARCIAL)
    pend["pendentes_por_memoria"] = [{"task": u"t", "pedia_gib": 9.0,
                                      "livre_gib": 3.0}]
    roda = _serie(u"R")
    roda["estado"] = Q.RODANDO
    turno = Q.novo_card(Q.OVERNIGHT, rotulo=u"ON")
    f = [roda, _serie(u"E"), _serie(u"P", estado=Q.PULADO),
         _serie(u"OK", estado=Q.PRONTO), _serie(u"PARC", estado=Q.PARCIAL),
         pend, _serie(u"F", estado=Q.FALHOU),
         _serie(u"CAN", estado=Q.CANCELADO), turno]
    ficam, saem = Q.limpar(f)
    checar(u"sai so o que terminou com sucesso (o pronto)",
           sorted(_rot(saem)) == [u"OK"], str(_rot(saem)))
    checar(u"  e fica o que roda, o que espera, o pulado, o parcial, o que "
           u"falhou, o cancelado, o parcial que espera o complemento e o turno",
           sorted(_rot(ficam)) == sorted([u"R", u"E", u"P", u"PARC", u"PARC_C",
                                          u"F", u"CAN", u"ON"]),
           str(_rot(ficam)))
    checar(u"  e o parcial pede a confirmacao, como o que falhou",
           sorted(_rot([c for c in f if Q.pede_confirmacao_no_limpar(c)]))
           == [u"CAN", u"F", u"PARC"])
    ficam2, saem2 = Q.limpar(f, com_falhas=True)
    checar(u"com a confirmacao, saem tambem o parcial, o que falhou e o "
           u"cancelado", sorted(_rot(saem2)) == [u"CAN", u"F", u"OK", u"PARC"],
           str(_rot(saem2)))
    checar(u"  e o que roda, o que espera e o parcial que espera o "
           u"complemento continuam", u"R" in _rot(ficam2)
           and u"E" in _rot(ficam2) and u"PARC_C" in _rot(ficam2))
    entrega = _serie(u"FULL_CAIU", estado=Q.PARCIAL)
    entrega["mensagem"] = u"FULL nao saiu: memoria"
    checar(u"a entrega que saiu parcial (FULL que falhou) nao sai sem a "
           u"confirmacao", Q.limpar([entrega])[1] == []
           and _rot(Q.limpar([entrega], True)[1]) == [u"FULL_CAIU"])
    velho = Q.sai_no_limpar
    try:
        Q.sai_no_limpar = (lambda c, com_falhas=False: c.get("estado")
                           in (Q.PRONTO, Q.PARCIAL)
                           or (com_falhas and c.get("estado") in Q.SEM_SUCESSO))
        isca = Q.limpar([entrega])[1]
    finally:
        Q.sai_no_limpar = velho
    checar(u"ISCA: com a regra de antes, o parcial sai sem confirmacao (a "
           u"checagem sabe reprovar)", _rot(isca) == [u"FULL_CAIU"])
    tf = Q.terminar(Q.novo_card(Q.OVERNIGHT, rotulo=u"TF"), Q.FALHOU)
    checar(u"o turno que nao abriu so sai com a confirmacao",
           Q.limpar([tf])[1] == [] and _rot(Q.limpar([tf], True)[1]) == [u"TF"])


def teste_pulado_fica_na_fila():
    secao(u"o pulado fica na fila, com o dono")
    f = [_serie(u"A"), _serie(u"B", uid=u"bb"), _serie(u"C")]
    g = Q.marcar_pulado(f, u"bb", dono=u"ESTACAO-2")
    checar(u"o card FICA na lista", len(g) == 3)
    checar(u"com o estado pulado", g[1]["estado"] == Q.PULADO)
    checar(u"e com o DONO, para a tela dizer quem pegou",
           g[1]["dono"] == u"ESTACAO-2", g[1]["dono"])
    checar(u"e ele sai dos pendentes desta maquina",
           u"B" not in _rot(Q.pendentes(g)), str(_rot(Q.pendentes(g))))
    checar(u"uid desconhecido nao muda a lista",
           [c["estado"] for c in Q.marcar_pulado(f, u"zzz")]
           == [c["estado"] for c in f])
    checar(u"uid vazio nao marca a fila inteira",
           [c["estado"] for c in Q.marcar_pulado(f, u"")]
           == [c["estado"] for c in f],
           u"um `if not uid` ausente marcaria TODOS os cards sem uid")
    v = [_serie(u"V", uid=u"vv", origem=Q.VIGIA)]
    checar(u"o card do vigia nao vira pulado pelo lote",
           Q.marcar_pulado(v, u"vv")[0]["estado"] == Q.ESPERANDO)
    r = Q.reativar_pulados(g)
    checar(u"reativar devolve a esperar, sem dono, no MESMO lugar",
           r[1]["estado"] == Q.ESPERANDO and r[1]["dono"] == u""
           and _rot(r) == [u"A", u"B", u"C"], str(_rot(r)))


def teste_a_trava_da_ordem():
    secao(u"a trava da ordem levanta")
    on = Q.novo_card(Q.OVERNIGHT, rotulo=u"ON")
    bom = Q.ordenar([_serie(u"A"), on])
    checar(u"a ordem correta passa", Q.conferir_ordem(bom) is True)

    try:
        Q.conferir_ordem([on, _serie(u"A")])
        ok, msg = False, u""
    except ValueError as e:
        ok, msg = True, u"%s" % e
    checar(u"card que espera DEPOIS do turno levanta", ok)
    checar(u"  e a mensagem diz qual", u"A" in msg, msg[:90])

    a, b = _serie(u"A"), _serie(u"B")
    b["estado"] = Q.RODANDO
    try:
        Q.conferir_ordem([a, b])
        ok2, msg2 = False, u""
    except ValueError as e:
        ok2, msg2 = True, u"%s" % e
    checar(u"o que RODA fora do topo levanta", ok2)
    checar(u"  e a mensagem nomeia o card fora da faixa",
           u"B" in msg2, msg2[:90])
    try:
        Q.conferir_ordem([_serie(u"V", origem=Q.VIGIA), _serie(u"M")])
        ok3 = False
    except ValueError:
        ok3 = True
    checar(u"o manual DEPOIS do vigia levanta", ok3)


def teste_o_cancelado_nao_volta_a_rodar():
    secao(u"o card tirado nao volta a rodar")
    import radai_queue_state as F
    F.limpar()
    try:
        F.pedir([{"uid": u"U1", "pasta": u"p1", "nome": u"A"},
                 {"uid": u"U2", "pasta": u"p2", "nome": u"B"},
                 {"uid": u"U3", "pasta": u"p3", "nome": u"C"}])
        F.cancelar(1)
        checar(u"o X tira o card da fila de verdade",
               [c["uid"] for c in F.cards()] == [u"U1", u"U3"],
               str([c["uid"] for c in F.cards()]))
        F.pedir([{"uid": u"U2", "pasta": u"p2", "nome": u"B"}])
        checar(u"pedida de novo, ela volta como UM card esperando",
               [c["uid"] for c in F.cards()] == [u"U1", u"U3", u"U2"],
               str([c["uid"] for c in F.cards()]))
        F.assumir(u"U1", u"p1")
        F.marcar(u"U1", Q.PRONTO, u"p1")
        F.pedir([{"uid": u"U1", "pasta": u"p1", "nome": u"A"}])
        F.assumir(u"U1", u"p1")
        est = [(c["uid"], c["estado"]) for c in F.cards()]
        checar(u"o `rodando` cai no card que ESPERA, e nao no terminado",
               est.count((u"U1", Q.RODANDO)) == 1
               and est.count((u"U1", Q.PRONTO)) == 1, str(est))
        F.marcar(u"U1", Q.FALHOU, u"p1")
        est = [(c["uid"], c["estado"]) for c in F.cards()]
        checar(u"  e fechar fecha SO o card vivo -- o pronto continua pronto",
               est.count((u"U1", Q.PRONTO)) == 1
               and est.count((u"U1", Q.FALHOU)) == 1, str(est))
        F.limpar()
        F.pedir([{"uid": u"X", "pasta": u"copia1"}, {"uid": u"X", "pasta": u"copia2"}])
        F.assumir(u"X", u"copia2")
        est = [(c["pasta"], c["estado"]) for c in F.cards()]
        checar(u"a mesma serie copiada para dois lugares: a pasta desempata",
               (u"copia2", Q.RODANDO) in est and (u"copia1", Q.ESPERANDO) in est,
               str(est))
        F.limpar()
        F.pedir([{"uid": u"Y", "pasta": u"py"}])
        cid = F.cards()[0]["id"]
        checar(u"o X pelo id tira o card", F.tirar(cid) is True
               and F.cards() == [])
        checar(u"  e um id que nao existe nao tira nada", F.tirar(u"x" * 12)
               is False)
    finally:
        F.limpar()


def teste_a_mesma_serie_nao_entra_duas_vezes():
    secao(u"a mesma serie nao entra duas vezes")
    import radai_queue_state as F
    F.limpar()
    try:
        r1 = F.acrescentar_series([{"uid": u"U1", "pasta": u"p"},
                                   {"uid": u"U2", "pasta": u"p"}])
        r2 = F.acrescentar_series([{"uid": u"U2", "pasta": u"p"},
                                   {"uid": u"U3", "pasta": u"p"},
                                   {"uid": u"U3", "pasta": u"p"}])
        checar(u"a conta diz quantas entraram e quantas ja estavam",
               r1 == {"novos": 2, "repetidas": 0, "atualizadas": 0}
               and r2 == {"novos": 1, "repetidas": 2, "atualizadas": 0}, str((r1, r2)))
        checar(u"  e a fila tem UM card de cada",
               sorted(c["uid"] for c in F.cards()) == [u"U1", u"U2", u"U3"])
        F.assumir(u"U1", u"p")
        F.marcar(u"U1", Q.PRONTO, u"p")
        r3 = F.acrescentar_series([{"uid": u"U1", "pasta": u"p"}])
        checar(u"a serie ja feita pode ser pedida de novo",
               r3 == {"novos": 1, "repetidas": 0, "atualizadas": 0}, str(r3))
        r4 = F.acrescentar_series([{"pasta": u"p"}, {"pasta": u"p"}])
        checar(u"serie sem UID nao e tratada como repetida",
               r4 == {"novos": 2, "repetidas": 0, "atualizadas": 0}, str(r4))
    finally:
        F.limpar()


def teste_pedir_de_novo_com_outro_modo_atualiza():
    secao(u"pedir de novo com outro modo atualiza a escolha")
    import radai_queue_state as F
    F.limpar()

    def _carga(uid):
        for c in F.cards():
            if c.get("uid") == uid:
                return c.get("carga") or {}
        return {}
    try:
        F.acrescentar_series([{"uid": u"M1", "pasta": u"p", "modo": u"padrao"},
                              {"uid": u"M2", "pasta": u"p", "modo": u"padrao"}])
        r = F.acrescentar_series([{"uid": u"M1", "pasta": u"p",
                                   "modo": u"completo"}])
        checar(u"pedir de novo em OUTRO modo conta como atualizada",
               r == {"novos": 0, "repetidas": 0, "atualizadas": 1}, str(r))
        checar(u"  e a carga do card passa a ter o modo novo",
               _carga(u"M1").get("modo") == u"completo", str(_carga(u"M1")))
        checar(u"  e continua UM card dela",
               sum(1 for c in F.cards() if c.get("uid") == u"M1") == 1)
        checar(u"  e a outra serie nao muda",
               _carga(u"M2").get("modo") == u"padrao", str(_carga(u"M2")))
        F.acrescentar_series([{"uid": u"M3", "pasta": u"p",
                               "modo": u"personalizado",
                               "tasks_extra": (u"a", u"b")}])
        r2 = F.acrescentar_series([{"uid": u"M3", "pasta": u"p",
                                    "modo": u"personalizado",
                                    "tasks_extra": [u"a", u"b"]}])
        checar(u"o MESMO pedido de novo e so repetida (lista == tupla)",
               r2 == {"novos": 0, "repetidas": 1, "atualizadas": 0}, str(r2))
        F.acrescentar_series([{"uid": u"E1", "pasta": u"p", "estudos": [],
                               "tasks_extra": [u"trunk_cavities"]}])
        r5 = F.acrescentar_series([{"uid": u"E1", "pasta": u"p",
                                    "estudos": [u"torax", u"abdome"],
                                    "tasks_extra": [u"trunk_cavities"]}])
        checar(u"pedir de novo com OUTRO estudo (mesmas caixas) conta como "
               u"atualizada", r5 == {"novos": 0, "repetidas": 0,
                                     "atualizadas": 1}, str(r5))
        checar(u"  e a carga passa a levar os estudos novos",
               list(_carga(u"E1").get("estudos") or ())
               == [u"torax", u"abdome"], str(_carga(u"E1")))
        r6 = F.acrescentar_series([{"uid": u"E1", "pasta": u"p",
                                    "estudos": (u"torax", u"abdome"),
                                    "tasks_extra": (u"trunk_cavities",)}])
        checar(u"os MESMOS estudos de novo sao so repetida (lista == tupla)",
               r6 == {"novos": 0, "repetidas": 1, "atualizadas": 0}, str(r6))
        F.acrescentar_series([{"uid": u"E2", "pasta": u"p",
                               "modo_v81": u"completo"}])
        r7 = F.acrescentar_series([{"uid": u"E2", "pasta": u"p",
                                    "estudos": [u"torax"]}])
        checar(u"de uma pagina v8.1 para a v8.2: atualiza, `modo_v81` sai e "
               u"`estudos` entra", r7.get("atualizadas") == 1
               and "modo_v81" not in _carga(u"E2")
               and list(_carga(u"E2").get("estudos") or ()) == [u"torax"],
               str((r7, _carga(u"E2"))))
        _velha = F._ESCOLHA
        try:
            F._ESCOLHA = ("modo", "tasks_extra", "motores_extra", "topo")
            F.acrescentar_series([{"uid": u"E3", "pasta": u"p",
                                   "estudos": [],
                                   "tasks_extra": [u"trunk_cavities"]}])
            ri = F.acrescentar_series([{"uid": u"E3", "pasta": u"p",
                                        "estudos": [u"torax"],
                                        "tasks_extra": [u"trunk_cavities"]}])
        finally:
            F._ESCOLHA = _velha
        checar(u"  (isca) com a `_ESCOLHA` da v8.1, o Torax pedido de novo "
               u"seria «repetida» -- a checagem discrimina",
               ri == {"novos": 0, "repetidas": 1, "atualizadas": 0}
               and list(_carga(u"E3").get("estudos") or ()) == [], str(ri))
        _p1 = {"uid": u"V1", "pasta": u"p", "modo": u"perso",
               "protocolos": [u"cranio"], "tasks": {u"teeth": 1},
               "comparacao": {u"ts": 0, u"nv": 0}, "oar_fora": []}
        F.acrescentar_series([dict(_p1)])
        for _rot, _mud in (
                (u"OUTRO protocolo", {"protocolos": [u"cranio",
                                                     u"torax_mama"]}),
                (u"OUTRA chave de task", {"tasks": {u"teeth": 0}}),
                (u"OUTRA comparacao", {"comparacao": {u"ts": 1, u"nv": 0}}),
                (u"OUTRO recorte do OAR", {"oar_fora": [u"Esophagus"]}),
                (u"OUTRO modo", {"modo": u"fast"})):
            _novo = dict(_p1)
            _novo.update(_mud)
            _r = F.acrescentar_series([_novo])
            checar(u"v8.3: pedir de novo com %s conta como atualizada" % _rot,
                   _r == {"novos": 0, "repetidas": 0, "atualizadas": 1},
                   str(_r))
            _p1 = _novo
        _igual = dict(_p1)
        _igual["protocolos"] = tuple(_p1["protocolos"])
        _igual["oar_fora"] = tuple(_p1["oar_fora"])
        _igual["tasks"] = dict(reversed(list(_p1["tasks"].items())))
        _r = F.acrescentar_series([_igual])
        checar(u"  e a MESMA escolha de novo e so repetida (lista == tupla, "
               u"dicionario em outra ordem)",
               _r == {"novos": 0, "repetidas": 1, "atualizadas": 0}, str(_r))
        checar(u"  e a carga leva a escolha nova inteira",
               _carga(u"V1").get("modo") == u"fast"
               and list(_carga(u"V1").get("protocolos") or ())
               == [u"cranio", u"torax_mama"]
               and list(_carga(u"V1").get("oar_fora") or ())
               == [u"Esophagus"], str(_carga(u"V1")))
        _velha = F._ESCOLHA
        try:
            F._ESCOLHA = ("modo", "tasks_extra", "motores_extra", "topo",
                          "estudos", "modo_v81")
            F.acrescentar_series([{"uid": u"V2", "pasta": u"p",
                                   "modo": u"perso", "protocolos": []}])
            ri2 = F.acrescentar_series([{"uid": u"V2", "pasta": u"p",
                                         "modo": u"perso",
                                         "protocolos": [u"torax_mama"]}])
        finally:
            F._ESCOLHA = _velha
        checar(u"  (isca) com a `_ESCOLHA` da v8.2, o Torax / Mama pedido de "
               u"novo seria «repetida» -- a checagem discrimina",
               ri2 == {"novos": 0, "repetidas": 1, "atualizadas": 0}, str(ri2))
        r3 = F.acrescentar_series([{"uid": u"M1", "pasta": u"p"}])
        checar(u"pedir de novo SEM modo tira o modo da carga",
               r3.get("atualizadas") == 1 and "modo" not in _carga(u"M1"),
               str((r3, _carga(u"M1"))))
        F.assumir(u"M2", u"p")
        r4 = F.acrescentar_series([{"uid": u"M2", "pasta": u"p",
                                    "modo": u"completo"}])
        checar(u"a que ja roda nao troca de modo (conta como repetida)",
               r4 == {"novos": 0, "repetidas": 1, "atualizadas": 0}
               and _carga(u"M2").get("modo") == u"padrao",
               str((r4, _carga(u"M2"))))
    finally:
        F.limpar()


def teste_limpar_fila_e_a_rota():
    secao(u"o Limpar da estacao, e a rota dele")
    import asyncio
    import radai_queue_state as F
    F.limpar()
    try:
        F.pedir([{"uid": u"U1", "pasta": u"p"}, {"uid": u"U2", "pasta": u"p"},
                 {"uid": u"U3", "pasta": u"p"}, {"uid": u"U4", "pasta": u"p"}])
        F.overnight(True)
        F.assumir(u"U1", u"p")
        F.marcar(u"U1", Q.PRONTO, u"p")
        F.assumir(u"U2", u"p")
        F.marcar(u"U2", Q.FALHOU, u"p")
        F.assumir(u"U3", u"p")
        r = F.limpar_fila()
        fic = sorted((c.get("uid"), c.get("estado")) for c in F.cards())
        checar(u"o Limpar tira so o pronto: o que roda, o que espera, o que "
               u"falhou e o turno ficam",
               fic == sorted([(u"U2", Q.FALHOU), (u"U3", Q.RODANDO),
                              (u"U4", Q.ESPERANDO), (u"", Q.ESPERANDO)]),
               str(fic))
        checar(u"  e a conta diz o que saiu e quantas falhas pedem confirmacao",
               r["tirados"] == 1 and r["falhas_restantes"] == 1
               and r["frase"] == u"1 cartão tirado", str(r))
        r2 = F.limpar_fila(com_falhas=True)
        checar(u"confirmado, o que falhou sai tambem, e o que roda nao",
               r2["tirados"] == 1 and any(c.get("uid") == u"U3"
                                          and c.get("estado") == Q.RODANDO
                                          for c in F.cards()), str(r2))
        capt = {}

        class _App(object):
            def get(self, rota, **kw):
                def _r(f):
                    capt[rota] = f
                    return f
                return _r

            def post(self, rota, **kw):
                return self.get(rota)

        class _Pedido(object):
            def __init__(self, corpo):
                self._corpo = corpo

            async def json(self):
                return self._corpo
        F.montar(_App())
        checar(u"a rota `/api/fila/limpar` existe",
               "/api/fila/limpar" in capt)
        d = asyncio.run(capt["/api/fila/limpar"](_Pedido({})))
        checar(u"  e devolve o pacote da barra, com a contagem e a frase",
               "cards" in d and "tirados" in d and "frase" in d
               and "lote" in d and "removidos" in d, str(sorted(d)))
    finally:
        F.limpar()


def teste_o_lote_alimenta_a_fila_de_verdade():
    secao(u"o lote alimenta a fila, e o desfecho de cada serie chega la")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "app"))
    import radai_queue_state as F
    import radai_batch as L

    F.limpar()
    SERIES = [{"uid": "U1", "nome": "A", "pasta": "p1"},
              {"uid": "U2", "nome": "B", "pasta": "p2"},
              {"uid": "U3", "nome": "C", "pasta": "p3"},
              {"uid": "U4", "nome": "D", "pasta": "p4"}]
    DESFECHO = {"U1": {},
                "U2": {"pulo": "outra", "dono": "PC_VIZINHO",
                       "pulada": "outra estacao esta processando "
                                 "(ou pasta sem permissao)"},
                "U3": {"pulada": "ja concluida (marcador done)"},
                "U4": {"erro": "estourou"}}

    guardados = (L.pode_segmentar, L._uma_serie)
    L.pode_segmentar = lambda *a, **k: (True, "")

    vistos = []

    def _falso(s, *a, **k):
        vistos.append(s.get("uid"))
        r = {"uid": s.get("uid"), "pid": "", "curto": "", "pasta": s.get("pasta"),
             "rs": "", "estruturas": 0, "v3d": 0, "segundos": 0.0,
             "erro": "", "pulada": "", "pulo": ""}
        r.update(DESFECHO.get(s.get("uid"), {}))
        return r
    L._uma_serie = _falso

    try:
        F.overnight(True)
        d = L.iniciar(SERIES, marcadores={k: (lambda *a, **k2: True)
                                          for k in L.MARCADORES_EXIGIDOS},
                      maquina="BATERIA")
        checar(u"o lote aceitou", bool(d.get("ok")), str(d.get("erro"))[:90])

        agora = F.cards()
        series_agora = [c for c in agora if c.get("tipo") == Q.SERIE]
        checar(u"as 4 series entraram na fila no CLIQUE",
               len(series_agora) == 4, u"%d card(s) de serie" % len(series_agora))
        checar(u"  e o overnight vem depois de toda serie que espera",
               agora[-1].get("tipo") == Q.OVERNIGHT if agora else False)
        try:
            Q.conferir_ordem(agora)
            ordem_ok, motivo = True, u""
        except ValueError as e:
            ordem_ok, motivo = False, str(e)[:120]
        checar(u"  e a ordem passa na trava", ordem_ok, motivo)

        for _ in range(200):
            if not L.estado().get("rodando"):
                break
            time.sleep(0.05)
        checar(u"as 4 series foram processadas", vistos == ["U1", "U2", "U3", "U4"],
               u", ".join(vistos))

        fim = {c.get("uid"): c.get("estado")
               for c in F.cards() if c.get("tipo") == Q.SERIE}
        for uid, esperado in (("U1", Q.PRONTO), ("U2", Q.PULADO),
                              ("U3", Q.PRONTO), ("U4", Q.FALHOU)):
            checar(u"%s terminou como `%s`" % (uid, esperado),
                   fim.get(uid) == esperado, u"veio `%s`" % fim.get(uid))
        pulado = [c for c in F.cards() if c.get("uid") == "U2"]
        checar(u"  e o pulado diz por QUEM (a maquina, e nao a frase)",
               bool(pulado) and pulado[0].get("dono") == u"PC_VIZINHO",
               pulado[0].get("dono") if pulado else u"card sumiu")
        checar(u"  e o motivo vai no campo dele",
               bool(pulado) and u"outra estacao esta processando"
               in (pulado[0].get("motivo") or u""),
               pulado[0].get("motivo") if pulado else u"card sumiu")
    finally:
        L.pode_segmentar, L._uma_serie = guardados
        F.limpar()



def teste_o_lote_le_a_fila_viva():
    secao(u"o lote le a fila viva, e o CANCELAR para so o que roda")
    import radai_queue_state as F
    import radai_batch as L
    F.limpar()
    guardados = (L.pode_segmentar, L._uma_serie)
    L.pode_segmentar = lambda *a, **k: (True, "")
    vistos = []

    def _vis(uid):
        for i, c in enumerate(F.cards()):
            if c.get("uid") == uid:
                return i
        return -1

    def _falso(s, *a, **k):
        vistos.append(s.get("uid"))
        if s.get("uid") == u"S1":
            F.cancelar(_vis(u"S2"))
            F.pedir([{"uid": u"S4", "pasta": u"p4", "nome": u"D"}])
            F.mover(_vis(u"S4"), -1)
        return {"uid": s.get("uid"), "erro": "", "pulada": "", "pulo": "",
                "segundos": 0.0}
    L._uma_serie = _falso
    marc = dict((k, (lambda *a, **k2: True)) for k in L.MARCADORES_EXIGIDOS)
    try:
        F.pedir([{"uid": u"S1", "pasta": u"p1", "nome": u"A"},
                 {"uid": u"S2", "pasta": u"p2", "nome": u"B"},
                 {"uid": u"S3", "pasta": u"p3", "nome": u"C"}])
        d = L.iniciar(F.series_esperando(), ja_na_fila=True, marcadores=marc,
                      maquina="BATERIA")
        checar(u"o lote aceitou", bool(d.get("ok")), str(d.get("erro"))[:90])
        for _ in range(200):
            if not L.estado().get("rodando"):
                break
            time.sleep(0.05)
        checar(u"o card tirado no X NAO rodou", u"S2" not in vistos,
               u", ".join(vistos))
        checar(u"a serie acrescentada no meio rodou na MESMA volta, na ordem "
               u"da tela", vistos == [u"S1", u"S4", u"S3"], u", ".join(vistos))

        F.limpar()
        del vistos[:]

        def _interrompe(s, *a, **k):
            vistos.append(s.get("uid"))
            L.cancelar()
            return {"uid": s.get("uid"), "erro": "", "pulada": "", "pulo": "",
                    "cancelado": True, "segundos": 0.0}
        L._uma_serie = _interrompe
        F.pedir([{"uid": u"C1", "pasta": u"p1"}, {"uid": u"C2", "pasta": u"p2"},
                 {"uid": u"C3", "pasta": u"p3"}])
        L.iniciar(F.series_esperando(), ja_na_fila=True, marcadores=marc,
                  maquina="BATERIA")
        for _ in range(200):
            if not L.estado().get("rodando"):
                break
            time.sleep(0.05)
        est = [(c.get("uid"), c.get("estado")) for c in F.cards()]
        checar(u"cancelar para o lote na serie da vez", vistos == [u"C1"],
               u", ".join(vistos))
        checar(u"a serie interrompida fica CANCELADA -- nao vira «pronto», "
               u"e pode voltar a fila",
               (u"C1", Q.CANCELADO) in est and [c.get("acoes", {})
                                                 for c in F.para_tela(F.cards())
                                                 if c.get("uid") == u"C1"]
               [0].get("repor") is True, str(est))
        checar(u"  e as que esperam continuam esperando",
               est[:2] == [(u"C2", Q.ESPERANDO), (u"C3", Q.ESPERANDO)], str(est))
    finally:
        L.pode_segmentar, L._uma_serie = guardados
        with L._TRAVA:
            L._JOB["rodando"] = False
            L._JOB["cancelar"] = False
        F.limpar()


def _esperar_o_lote(L, segundos=10.0):
    fim = time.time() + segundos
    while time.time() < fim:
        if not L.estado().get("rodando"):
            return True
        time.sleep(0.05)
    return False


def teste_a_fila_que_nao_se_le_para_o_lote_e_diz():
    secao(u"a fila que nao se le para o lote, e diz")
    import radai_queue_state as F
    import radai_batch as L
    F.limpar()
    guardados = (L.pode_segmentar, L._uma_serie, F.proxima_esperando)
    L.pode_segmentar = lambda *a, **k: (True, "")
    vistos, linhas = [], []

    def _falso(s, *a, **k):
        vistos.append(s.get("uid"))
        return {"uid": s.get("uid"), "erro": "", "pulada": "", "pulo": "",
                "segundos": 0.0}

    def _quebrada(excluir=()):
        raise OSError(u"a fila nao respondeu (dublado)")
    L._uma_serie = _falso
    marc = dict((k, (lambda *a, **k2: True)) for k in L.MARCADORES_EXIGIDOS)
    try:
        F.pedir([{"uid": u"Q1", "pasta": u"p1"}, {"uid": u"Q2", "pasta": u"p2"}])
        F.proxima_esperando = _quebrada
        d = L.iniciar(F.series_esperando(), ja_na_fila=True, marcadores=marc,
                      maquina="BATERIA", log=linhas.append)
        checar(u"o lote aceitou", bool(d.get("ok")), str(d.get("erro"))[:90])
        checar(u"  e terminou", _esperar_o_lote(L))
        erro = str(L.estado().get("erro") or u"")
        checar(u"a fila que nao se le PARA o lote COM erro, e o erro diz o que foi",
               u"fila nao foi lida" in erro and u"OSError" in erro, erro)
        checar(u"  e o log diz que o lote parou",
               any(u"o lote parou" in str(x) for x in linhas),
               u" | ".join(str(x) for x in linhas[-3:]))
        checar(u"  e nenhuma serie rodou as cegas", vistos == [],
               u", ".join(vistos))
        F.proxima_esperando = guardados[2]
        est = [(c.get("uid"), c.get("estado")) for c in F.cards()]
        checar(u"  e as que esperavam continuam esperando",
               est == [(u"Q1", Q.ESPERANDO), (u"Q2", Q.ESPERANDO)], str(est))
    finally:
        L.pode_segmentar, L._uma_serie, F.proxima_esperando = guardados
        with L._TRAVA:
            L._JOB["rodando"] = False
            L._JOB["cancelar"] = False
            L._JOB["erro"] = ""
        F.limpar()


def teste_o_x_entre_a_escolha_e_o_comeco_vence():
    secao(u"o X entre a escolha e o comeco vence")
    import radai_queue_state as F
    import radai_batch as L
    F.limpar()
    guardados = (L.pode_segmentar, L._uma_serie, F.proxima_esperando)
    L.pode_segmentar = lambda *a, **k: (True, "")
    vistos, linhas = [], []
    original = F.proxima_esperando

    def _falso(s, *a, **k):
        vistos.append(s.get("uid"))
        return {"uid": s.get("uid"), "erro": "", "pulada": "", "pulo": "",
                "segundos": 0.0}

    def _com_x(excluir=()):
        s = original(excluir=excluir)
        if s and s.get("uid") == u"R1":
            vis = [i for i, c in enumerate(F.cards()) if c.get("uid") == u"R1"]
            if vis:
                F.cancelar(vis[0])
        return s
    L._uma_serie = _falso
    marc = dict((k, (lambda *a, **k2: True)) for k in L.MARCADORES_EXIGIDOS)
    try:
        F.pedir([{"uid": u"R1", "pasta": u"p1"}, {"uid": u"R2", "pasta": u"p2"}])
        F.proxima_esperando = _com_x
        L.iniciar(F.series_esperando(), ja_na_fila=True, marcadores=marc,
                  maquina="BATERIA", log=linhas.append)
        checar(u"o lote terminou", _esperar_o_lote(L))
        checar(u"a serie tirada no X entre a escolha e o comeco NAO rodou",
               u"R1" not in vistos, u", ".join(vistos))
        checar(u"  e a seguinte rodou", vistos == [u"R2"], u", ".join(vistos))
        checar(u"  e o log diz por que ela ficou de fora",
               any(u"saiu da fila antes de comecar" in str(x) for x in linhas),
               u" | ".join(str(x) for x in linhas[-4:]))
        F.limpar()
        F.pedir([{"uid": u"A1", "pasta": u"p"}])
        checar(u"assumir marca o card vivo e diz que marcou",
               F.assumir(u"A1", u"p") is True
               and [c.get("estado") for c in F.cards()] == [Q.RODANDO])
        checar(u"assumir de serie que nao esta na fila diz False",
               F.assumir(u"NAO_HA", u"p") is False)
        checar(u"assumir sem UID diz None -- «nao sei»",
               F.assumir(u"", u"p") is None)
    finally:
        L.pode_segmentar, L._uma_serie, F.proxima_esperando = guardados
        with L._TRAVA:
            L._JOB["rodando"] = False
            L._JOB["cancelar"] = False
        F.limpar()


class _Lock(object):

    def __init__(self, uid, estado=u"trabalhando", dono=u"PC_VIZINHO"):
        self.uid, self.estado, self.dono = uid, estado, dono
        self.sem_permissao = False

    def _meu(self, uid):
        return uid == self.uid

    def marcadores(self, L):
        m = dict((k, (lambda *a, **k2: True)) for k in L.MARCADORES_EXIGIDOS)

        def has_marker(pasta, uid, nome):
            if nome == "done":
                return False
            if nome == "lock":
                return (self._meu(uid) and self.estado != u"livre"
                        and not self.sem_permissao)
            return False

        def claim(pasta, uid, info=None):
            if not self._meu(uid):
                return True
            if self.sem_permissao:
                return False
            return self.estado in (u"livre", u"travado")

        def read_marker(pasta, uid, nome):
            if self._meu(uid) and nome == "lock" and self.estado != u"livre" \
                    and not self.sem_permissao:
                return {"machine": self.dono}
            return None

        def diagnostico(pasta, uid):
            if not self._meu(uid) or self.sem_permissao:
                return u"livre", {}
            return self.estado, {"machine": self.dono}
        m.update({"has_marker": has_marker, "claim": claim,
                  "read_marker": read_marker, "diagnostico": diagnostico})
        return m


def teste_o_pulado_volta_quando_o_lock_libera():
    secao(u"o pulado volta quando o lock libera")
    import radai_queue_state as F
    import radai_batch as L
    real = L._uma_serie
    guardados = (L.pode_segmentar, L._uma_serie, F.troca_de_paciente)
    L.pode_segmentar = lambda *a, **k: (True, "")
    vistos, linhas, durante = [], [], {}
    trava = _Lock(u"X1")

    def _dub(s, *a, **k):
        if s.get("uid") == trava.uid and (trava.sem_permissao
                                          or trava.estado == u"trabalhando"):
            vistos.append(u"pulou:" + s.get("uid"))
            return real(s, *a, **k)
        vistos.append(s.get("uid"))
        if s.get("uid") == u"Y1":
            c = [x for x in F.cards() if x.get("uid") == u"X1"]
            durante["x1"] = dict(c[0]) if c else {}
            if durante.get("expira"):
                trava.estado = u"travado"
        return {"uid": s.get("uid"), "erro": "", "pulada": "", "pulo": "",
                "segundos": 0.0}

    def _rodar(fila_uids):
        F.limpar()
        del vistos[:]
        del linhas[:]
        F.pedir([{"uid": u, "pasta": u"p_" + u} for u in fila_uids])
        L.iniciar(F.series_esperando(), ja_na_fila=True,
                  marcadores=trava.marcadores(L), maquina="BATERIA",
                  log=linhas.append)
        terminou = _esperar_o_lote(L)
        estados = dict((c.get("uid"), c.get("estado")) for c in F.cards())
        return terminou, estados

    L._uma_serie = _dub
    try:
        trava.estado, durante["expira"] = u"trabalhando", True
        fim, est = _rodar([u"X1", u"Y1"])
        checar(u"o lote terminou", fim)
        x1 = durante.get("x1") or {}
        checar(u"enquanto o dono vivia, X1 ficou PULADA",
               x1.get("estado") == Q.PULADO, str(x1.get("estado")))
        checar(u"  com o NOME da maquina no dono, e nao a frase do motivo",
               x1.get("dono") == u"PC_VIZINHO", repr(x1.get("dono")))
        checar(u"  e o motivo no campo dele",
               u"outra estacao esta processando" in (x1.get("motivo") or u""),
               repr(x1.get("motivo")))
        checar(u"o lock liberou na troca de paciente: X1 VOLTOU e rodou",
               vistos == [u"pulou:X1", u"Y1", u"X1"], u", ".join(vistos))
        checar(u"  e terminou pronta", est.get(u"X1") == Q.PRONTO, str(est))
        checar(u"  e o log diz por que ela voltou",
               any(u"voltou a esperar" in str(l) for l in linhas),
               u" | ".join(str(l) for l in linhas[-4:]))

        trava.estado, durante["expira"] = u"trabalhando", False
        fim, est = _rodar([u"X1", u"Y1"])
        checar(u"com o dono vivo, a fila TERMINA (nao gira em volta dele)", fim)
        checar(u"  e X1 fica pulada, sem nova tentativa",
               est.get(u"X1") == Q.PULADO
               and vistos == [u"pulou:X1", u"Y1"], u"%s | %s" % (est, vistos))

        trava.estado = u"travado"
        L.iniciar([], ja_na_fila=True, marcadores=trava.marcadores(L),
                  maquina="BATERIA", log=linhas.append)
        _esperar_o_lote(L)
        est = dict((c.get("uid"), c.get("estado")) for c in F.cards())
        checar(u"a fila que ficou com a pulada: o «Iniciar» seguinte a roda",
               est.get(u"X1") == Q.PRONTO and vistos[-1:] == [u"X1"],
               u"%s | %s" % (est, vistos))

        teto = getattr(L, "_MAX_RETOMADAS", None)
        trava.estado, trava.sem_permissao = u"trabalhando", True
        durante["expira"] = False
        fim, est = _rodar([u"X1", u"Y1"])
        n = sum(1 for v in vistos if v == u"pulou:X1")
        checar(u"pasta sem permissao: tenta de novo no maximo %s vez(es), e "
               u"a fila TERMINA" % teto,
               fim and teto is not None and n == 1 + teto,
               u"%d tentativa(s)" % n)
        trava.sem_permissao = False

        F.troca_de_paciente = lambda livre=None: []
        trava.estado, durante["expira"] = u"trabalhando", True
        fim, est = _rodar([u"X1", u"Y1"])
        checar(u"  isca: sem a troca, X1 fica pulada mesmo com o lock livre "
               u"(a checagem discrimina)",
               est.get(u"X1") == Q.PULADO and u"X1" not in vistos,
               u"%s | %s" % (est, vistos))
    finally:
        L.pode_segmentar, L._uma_serie, F.troca_de_paciente = guardados
        with L._TRAVA:
            L._JOB["rodando"] = False
            L._JOB["cancelar"] = False
        F.limpar()


def teste_o_andamento_que_falha_diz_uma_vez():
    secao(u"o andamento que falha diz, uma vez")
    import contextlib
    import io
    import radai_queue_state as F
    import radai_batch as L
    guardado = L.andamento
    del F._AVISOU_ANDAMENTO[:]

    def _quebrado():
        raise RuntimeError(u"andamento dublado")
    buf = io.StringIO()
    try:
        L.andamento = _quebrado
        with contextlib.redirect_stdout(buf):
            a = F._estado_do_lote()
            b = F._estado_do_lote()
    finally:
        L.andamento = guardado
        del F._AVISOU_ANDAMENTO[:]
    checar(u"o andamento que falha devolve {} -- a barra nao cai",
           a == {} and b == {}, str((a, b)))
    checar(u"  e diz na tela preta, uma vez so",
           buf.getvalue().count(u"[fila]") == 1
           and u"RuntimeError" in buf.getvalue(), buf.getvalue()[:160])


def _pacote_da_rota():
    capturadas = {}

    class _App(object):
        def get(self, rota, **kw):
            def _reg(f):
                capturadas[rota] = f
                return f
            return _reg

        def post(self, rota, **kw):
            return self.get(rota)

    import radai_queue_state as F
    F.montar(_App())
    return capturadas["/api/fila"]()


def teste_a_fila_nao_manda_caminho_nem_uid_inteiro():
    secao(u"a fila nao manda caminho de paciente nem UID inteiro")
    import json
    import radai_queue_state as F

    CAMINHO = "\\\\servidor\\exames\\ISCA_BELTRANO_12345\\CT"
    UID = u"1.2.99.1.2.55.3.1234"
    F.limpar()
    F.pedir([{"rotulo": u"TC de torax", "uid": UID, "pasta": CAMINHO}],
            com_speed=False)

    interno = [c for c in F.cards() if c.get("tipo") == "serie"][0]
    checar(u"o card INTERNO guarda a pasta inteira",
           interno.get("pasta") == CAMINHO, interno.get("pasta"))
    checar(u"  e o UID inteiro", interno.get("uid") == UID)

    fora = [c for c in F.para_tela(F.cards()) if c.get("tipo") == "serie"][0]
    checar(u"na rede nao ha campo `pasta`", "pasta" not in fora,
           u", ".join(sorted(fora)))
    checar(u"  e o UID vai truncado em 8",
           fora.get("uid") == UID[-8:], fora.get("uid"))

    pacote = _pacote_da_rota()
    bruto = json.dumps(pacote, ensure_ascii=False)
    checar(u"o pacote da rota nao tem o caminho",
           u"ISCA_BELTRANO" not in bruto and u"servidor" not in bruto,
           bruto[:140])
    checar(u"  e nao tem o UID inteiro", UID not in bruto, bruto[:140])
    checar(u"  e a rota ainda devolve a serie",
           any(c.get("tipo") == "serie" for c in pacote.get("cards") or []),
           u"fila vazia passaria nas duas acima sem proteger nada")
    F.limpar()


def _rota_post(rota):
    capturadas = {}

    class _App(object):
        def get(self, r, **kw):
            def _reg(f):
                capturadas[r] = f
                return f
            return _reg

        def post(self, r, **kw):
            return self.get(r)

    import radai_queue_state as F
    F.montar(_App())
    return capturadas[rota]


class _Pedido(object):

    def __init__(self, corpo):
        self._corpo = corpo

    async def json(self):
        return self._corpo


def teste_o_card_do_turno_leva_os_valores_e_a_vez():
    secao(u"o card do turno: os valores de um turno so, e a vez dele")
    import asyncio
    import json
    import radai_queue_state as F
    SHARE = "\\\\servidor\\exames"
    F.limpar()
    F.pedir([{"rotulo": u"A", "uid": u"1.2.99.7.1", "pasta": u"x"}],
            com_speed=False)
    rota = _rota_post("/api/fila/overnight")
    asyncio.run(rota(_Pedido({"ligado": True, "pausar_servicos": False,
                              "temporarios": {"ROOT": SHARE,
                                              "MODALITIES": "CT,MR",
                                              "DAYS_BACK": "30"}})))
    cfg = F.config_do_turno()
    checar(u"a rota guarda no card os valores de um turno so",
           cfg == {"pausar_servicos": False,
                   "temporarios": {"ROOT": SHARE, "MODALITIES": "CT,MR",
                                   "DAYS_BACK": "30"}}, str(cfg))
    bruto = json.dumps(_pacote_da_rota(), ensure_ascii=False)
    checar(u"  e o ROOT do turno NAO vai para o navegador (a carga sai)",
           u"servidor" not in bruto and u"temporarios" not in bruto,
           bruto[:160])
    F.overnight(True, temporarios={"TASKS": "lung_nodules",
                                   "ROOT": u"y" * 5000})
    t = (F.config_do_turno() or {}).get("temporarios") or {}
    checar(u"a chave que o turno nao aceita NAO some na fila (o vigia a "
           u"recusa)", t.get("TASKS") == "lung_nodules", str(t)[:120])
    checar(u"  e o valor tem teto de tamanho", len(t.get("ROOT") or "") == 1024,
           str(len(t.get("ROOT") or "")))
    F.overnight(True, pausar_servicos=True)
    checar(u"sem valores do turno, a chave nem aparece",
           F.config_do_turno() == {"pausar_servicos": True},
           str(F.config_do_turno()))

    checar(u"com serie ESPERANDO na frente, nao e a vez do turno",
           F.turno_na_vez() is False)
    F.assumir(u"1.2.99.7.1", u"x")
    checar(u"  nem com ela RODANDO", F.turno_na_vez() is False)
    F.marcar(u"1.2.99.7.1", Q.PRONTO, u"x")
    checar(u"a serie terminou: E a vez do turno", F.turno_na_vez() is True)
    F.pedir([{"rotulo": u"B", "uid": u"1.2.99.7.2", "pasta": u"x"}],
            com_speed=False)
    F.skipped(u"1.2.99.7.2", dono=u"PC2", motivo=u"outra estacao")
    checar(u"  e a PULADA (outra estacao a segura) nao segura o turno",
           F.turno_na_vez() is True)

    checar(u"o card que ainda espera NAO sai ao encerrar um turno",
           F.tirar_turno_cumprido() is False
           and _estado_do_turno(F) == Q.ESPERANDO)
    F.fechar_turno(Q.PRONTO, u"turno aberto as 22:10")
    fim = F.cards()
    turno = [c for c in fim if c.get("tipo") == Q.OVERNIGHT]
    checar(u"fechar deixa o card «pronto» com o motivo",
           _estado_do_turno(F) == Q.PRONTO and turno
           and turno[0].get("motivo") == u"turno aberto as 22:10", str(turno))
    checar(u"  e nenhum card que espera fica depois dele (a trava da ordem "
           u"passa)", Q.conferir_ordem(fim) is True
           and all(c.get("estado") not in Q.NA_ESPERA
                   for c in fim[fim.index(turno[0]) + 1:]))
    F.fechar_turno("feito", u"turno aberto as 22:11")
    checar(u"  o «feito» de antes ainda fecha o turno como pronto",
           _estado_do_turno(F) == Q.PRONTO)
    checar(u"  e o feito NAO e a vez de novo", F.turno_na_vez() is False)
    try:
        F.fechar_turno(Q.RODANDO, u"x")
        levantou = False
    except ValueError:
        levantou = True
    checar(u"o card do turno nao fecha como «rodando» (iria para o topo)",
           levantou)
    checar(u"encerrar o turno tira o card que o abriu",
           F.tirar_turno_cumprido() is True and _estado_do_turno(F) is None)
    F.limpar()

def teste_o_contrato_leva_substituir_ao_lote():
    secao(u"o «substituir» do contrato chega ao cartao e ao lote")
    import tempfile
    import radai_queue_state as F
    F.limpar()
    pasta = tempfile.mkdtemp(prefix="radai_fila_subst_")
    uid = u"1.2.826.0.1.3680043.8.498.6061"
    try:
        r = F.enfileirar({"itens": [
            {"pasta": pasta, "uid": uid, "modo": "auto", "origem": "nidus",
             "substituir": True}]})
        cid = ((r.get("cartoes") or [{}])[0] or {}).get("id")
        carga = (F.cartao(cid) or {}).get("carga") or {}
        checar(u"o true do contrato fica no cartao", r.get("ok")
               and carga.get("substituir") is True, str(carga)[:160])
        s = F.proxima_esperando() or {}
        checar(u"  e vai na serie que o lote puxa da fila",
               s.get("substituir") is True and s.get("modo") == "auto", str(s))
        F.tirar(cid)
        for valor in ("sim", 1, "true"):
            r2 = F.enfileirar({"itens": [
                {"pasta": pasta, "uid": uid + u"%s" % len(str(valor)),
                 "modo": "auto", "origem": "nidus", "substituir": valor}]})
            c2 = ((r2.get("cartoes") or [{}])[0] or {}).get("id")
            checar(u"  (isca) %r nao substitui nada" % (valor,),
                   "substituir" not in ((F.cartao(c2) or {}).get("carga") or {}))
            F.tirar(c2)
        import radai_batch as L
        logs = []

        def _uma(serie):
            marc = {"has_marker": lambda p, u, k: k == "done",
                    "claim": lambda *a, **k: False,
                    "read_marker": lambda *a, **k: None}
            return L._uma_serie(dict(serie), False, ["total_v3"], "cpu", "",
                                60, 60, logs.append, marc, "ESTA", 60)
        com = _uma(dict(s, curto=uid[-8:], pid=u"F"))
        sem = _uma({"uid": uid, "pasta": pasta, "curto": uid[-8:], "pid": u"F",
                    "modo": "auto"})
        checar(u"o lote refaz a serie ja pronta quando o cartao leva "
               u"«substituir» (vai ao claim, e nao pula)",
               com.get("pulo") != "concluida", str(com.get("pulada")))
        checar(u"  (isca) sem ele, o lote pula a serie com marcador de pronta",
               sem.get("pulo") == "concluida", str(sem.get("pulada")))
    finally:
        F.limpar()
        import shutil
        shutil.rmtree(pasta, ignore_errors=True)


def teste_a_linha_do_vigia_e_o_fechar_ao_fim():
    secao(u"a linha no cartao do vigia, e a fila segurada ao fechar pelo X")
    import radai_queue_state as F
    F.limpar()
    F.vigia_na_fila([{"uid": u"1.2.3.4.5.6.7", "rotulo": u"PAC · 15/10/2026",
                      "pasta": u"C:\\share\\PAC",
                      "mensagem": u"a trava ficou de um processo desta "
                                  u"estação que parou; foi solta ao abrir"},
                     {"uid": u"1.2.3.4.5.6.8", "rotulo": u"OUTRA",
                      "pasta": u"C:\\share\\OUTRA"}])
    tela = dict((c.get("rotulo"), c) for c in F.para_tela(F.cards()))
    checar(u"o cartao do vigia mostra a linha que veio com ele",
           u"foi solta ao abrir" in (tela.get(u"PAC · 15/10/2026") or {})
           .get("mensagem", u""), str(tela.get(u"PAC · 15/10/2026")))
    checar(u"  e o outro cartao nao ganha linha nenhuma",
           not (tela.get(u"OUTRA") or {}).get("mensagem"))
    F.vigia_na_fila([{"uid": u"1.2.3.4.5.6.7", "rotulo": u"PAC",
                      "pasta": u"C:\\share\\PAC",
                      "mensagem": u"copiado de C:\\share\\PAC\\CT"}])
    msg = (F.cards() or [{}])[0].get("mensagem", u"")
    checar(u"  e a linha nao leva caminho", u"C:\\" not in msg, msg)
    F.limpar()
    checar(u"a fila nasce sem pedido de fechar ao fim",
           F.fechando_ao_fim() is False)
    F.pedir_fechar_ao_fim(True)
    checar(u"  e o pedido vale ate ser solto", F.fechando_ao_fim() is True)
    F.pedir_fechar_ao_fim(False)
    checar(u"  e solta", F.fechando_ao_fim() is False)


def main():
    print(u"test_queue | a fila da estacao")
    _TESTES = (teste_a_fila_nasce_vazia,
               teste_as_faixas,
               teste_subir_e_descer,
               teste_tirar_um_cartao,
               teste_o_que_o_limpar_tira,
               teste_pulado_fica_na_fila,
               teste_a_trava_da_ordem,
               teste_o_cancelado_nao_volta_a_rodar,
               teste_a_mesma_serie_nao_entra_duas_vezes,
               teste_pedir_de_novo_com_outro_modo_atualiza,
               teste_limpar_fila_e_a_rota,
               teste_o_lote_alimenta_a_fila_de_verdade,
               teste_o_lote_le_a_fila_viva,
               teste_a_fila_que_nao_se_le_para_o_lote_e_diz,
               teste_o_x_entre_a_escolha_e_o_comeco_vence,
               teste_o_pulado_volta_quando_o_lock_libera,
               teste_o_andamento_que_falha_diz_uma_vez,
               teste_a_fila_nao_manda_caminho_nem_uid_inteiro,
               teste_o_card_do_turno_leva_os_valores_e_a_vez,
               teste_o_contrato_leva_substituir_ao_lote,
               teste_a_linha_do_vigia_e_o_fechar_ao_fim)
    todos = set(k for k, v in globals().items()
                if k.startswith("teste_") and callable(v))
    fora = sorted(todos - set(f.__name__ for f in _TESTES))
    checar(u"todo teste deste arquivo esta registrado", not fora, ", ".join(fora))

    for t in _TESTES:
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    falhas = [(n, d) for n, ok, d in _R if not ok]
    print(u"\n" + u"=" * 64)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_R)))
        for n, d in falhas:
            print(u"  - %s%s" % (n, ("  [%s]" % d) if d else ""))
    else:
        print(u"OK: %d checagens, todas passaram" % len(_R))
    print(u"=" * 64)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
