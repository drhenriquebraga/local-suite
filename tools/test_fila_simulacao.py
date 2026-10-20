# -*- coding: utf-8 -*-
import asyncio
import atexit
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "app"))
sys.path.insert(0, AQUI)

import _cleanup
import _componentes

_BASE = tempfile.mkdtemp(prefix="radai_fila_sim_")
_cleanup.adotar_prefixo("radai_fila_sim_")
atexit.register(shutil.rmtree, _BASE, True)


def _sub(nome):
    p = os.path.join(_BASE, nome)
    os.makedirs(p, exist_ok=True)
    return p


os.environ["RADAI_CALIB_DIR"] = _sub("acervo")
os.environ["RADAI_REGISTRO_DIR"] = _sub("registro")
os.environ["RADAI_FILA_DIR"] = _sub("fila")
os.environ["LOCALAPPDATA"] = _sub("appdata")
os.environ["RADAI_URL_VERSOES"] = "0"
os.environ["RADAI_NOTIFICACAO"] = "0"
os.environ.pop("RADAI_RAIZES_NUVEM", None)

import radai_queue as Q
import radai_queue_state as F
import radai_batch as L

_R = []


def checar(nome, ok, detalhe=""):
    _R.append((nome, bool(ok), detalhe))
    print(u"  %s  %s%s" % (u"ok   " if ok else u"FALHA", nome,
                           (u"  [%s]" % detalhe) if (detalhe and not ok) else u""))
    return bool(ok)


def secao(t):
    print(u"\n-- %s --" % t)


def esperar(cond, segundos=10.0):
    fim = time.time() + segundos
    while time.time() < fim:
        try:
            if cond():
                return True
        except Exception:
            pass
        time.sleep(0.02)
    return False


def _zerar():
    F.limpar()
    for quem in ("lote", "vigia"):
        F.soltar_a_vez(quem)
    F.ligar_ganchos(soltar_trava_morta=None, achar_pasta=None)
    F._PERSISTIR["ligada"] = False
    F._PERSISTIR["erro"] = u""
    with L._TRAVA:
        L._JOB.update({"rodando": False, "cancelar": False, "pausar": False,
                       "erro": "", "resultados": [], "feitas": 0, "total": 0})


def _pasta(nome):
    return _sub(os.path.join("series", nome))


MARC = dict((k, (lambda *a, **k2: True)) for k in L.MARCADORES_EXIGIDOS)


class Duble(object):

    def __init__(self, desfechos=None, durante=None, segura=None):
        self.vistos = []
        self.cargas = []
        self.desfechos = dict(desfechos or {})
        self.durante = durante
        self.segura = segura

    def __call__(self, s, *a, **k):
        uid = s.get("uid")
        self.vistos.append(uid)
        self.cargas.append(dict(s))
        if self.durante:
            self.durante(uid)
        if self.segura is not None and uid in self.segura:
            self.segura[uid].wait(10)
        r = {"uid": uid, "erro": "", "pulada": "", "pulo": "",
             "segundos": 0.0, "pasta": s.get("pasta")}
        r.update(self.desfechos.get(uid) or {})
        if r.get("cancelado"):
            L.cancelar()
        return r


class Lote(object):

    def __init__(self, dublê, ocupado=None, log=None):
        self.d = dublê
        self.ocupado = ocupado
        self.log = log

    def __enter__(self):
        self.guardados = (L.pode_segmentar, L._uma_serie)
        L.pode_segmentar = lambda *a, **k: (True, "")
        L._uma_serie = self.d
        return self

    def __exit__(self, *a):
        esperar(lambda: not L.estado().get("rodando"), 10)
        L.pode_segmentar, L._uma_serie = self.guardados
        with L._TRAVA:
            L._JOB.update({"rodando": False, "cancelar": False,
                           "pausar": False, "erro": ""})
        F.soltar_a_vez("lote")

    def iniciar(self, series=None):
        return L.iniciar(series if series is not None else F.series_esperando(),
                         ja_na_fila=True, marcadores=MARC, maquina="BATERIA",
                         ocupado=self.ocupado, log=self.log)


def _estados():
    return [(c.get("uid"), c.get("estado")) for c in F.cards()
            if c.get("tipo") == Q.SERIE]


def _app():
    rotas = {}

    class _App(object):
        def get(self, r, **kw):
            def _reg(f):
                rotas[r] = f
                return f
            return _reg

        def post(self, r, **kw):
            return self.get(r)

    F.montar(_App())
    return rotas


class _Pedido(object):

    def __init__(self, corpo):
        self._corpo = corpo

    async def json(self):
        return self._corpo


def _post(rotas, rota, corpo):
    return asyncio.run(rotas[rota](_Pedido(corpo)))


def teste_o_contrato_c1_em_python():
    secao(u"C1: enfileirar e estado, em Python")
    _zerar()
    p1, p2 = _pasta("bridge1"), _pasta("bridge2")
    dest = _sub("destino_bridge")
    r = F.enfileirar({"itens": [
        {"pasta": p1, "uid": u"1.2.3.4.5.6.7.1", "modo": u"personalizado",
         "chaves": {u"trunk_cavities": 1, u"lung_vessels": 0},
         "copiar_rs_para": [dest], "origem": u"dicombridge",
         "rotulo": u"TC convertida"},
        {"pasta": p2, "uid": u"1.2.3.4.5.6.7.2", "origem": u"nidus"}]})
    checar(u"enfileirar devolve ok e um cartao por item, com id e posicao",
           r.get("ok") and len(r.get("cartoes") or ()) == 2
           and all(c.get("id") and c.get("posicao") for c in r["cartoes"]),
           str(r))
    c1 = F.cartao(r["cartoes"][0]["id"])
    checar(u"  o cartao guarda a origem, o modo normalizado e as chaves",
           c1["origem"] == Q.DICOMBRIDGE and c1["carga"]["modo"] == u"perso"
           and c1["carga"]["tasks"] == {u"trunk_cavities": 1,
                                        u"lung_vessels": 0}, str(c1))
    checar(u"  e as pastas de copia do RTSTRUCT", c1["copiar_rs_para"] == [dest])
    c2 = F.cartao(r["cartoes"][1]["id"])
    checar(u"  sem modo, o pedido e AUTO", c2["carga"]["modo"] == u"auto")
    r2 = F.enfileirar([{"pasta": p1, "uid": u"1.2.3.4.5.6.7.1",
                        "origem": u"dicombridge", "modo": u"personalizado",
                        "chaves": {u"trunk_cavities": 1, u"lung_vessels": 0},
                        "copiar_rs_para": [_sub("outro_destino")]}])
    checar(u"a mesma serie de novo devolve o MESMO cartao",
           r2["cartoes"][0]["id"] == r["cartoes"][0]["id"]
           and len(F.cards()) == 2, str(r2))
    checar(u"  e soma a pasta de copia nova",
           len(F.cartao(r["cartoes"][0]["id"])["copiar_rs_para"]) == 2)
    ruins = [
        ({"uid": u"1.2"}, u"faltou a pasta"),
        ({"pasta": u"relativa\\x", "uid": u"1.2"}, u"caminho completo"),
        ({"pasta": p1}, u"faltou o uid"),
        ({"pasta": p1, "uid": u"1.2", "modo": u"turbo"}, u"modo desconhecido"),
        ({"pasta": p1, "uid": u"1.2", "chaves": [u"x"]}, u"{task: 0|1}"),
        ({"pasta": p1, "uid": u"1.2", "chaves": {u"x": u"sim"}}, u"não é 0"),
        ({"pasta": p1, "uid": u"1.2", "origem": u"vigia"}, u"varredura"),
        ({"pasta": p1, "uid": u"1.2", "origem": u"outro"}, u"origem"),
        ({"pasta": p1, "uid": u"1.2", "copiar_rs_para": u"C:\\x"}, u"lista"),
        ({"pasta": p1, "uid": u"1.2", "copiar_rs_para": [u"rel"]},
         u"caminho completo"),
        ({"pasta": p1, "uid": u"1.2",
          "copiar_rs_para": [_sub("teto%d" % k) for k in range(9)]},
         u"leva até 8 pastas, e vieram 9")]
    for item, frase in ruins:
        antes = len(F.cards())
        rr = F.enfileirar([item, {"pasta": p2, "uid": u"9.9.9.9.9.9.1"}])
        checar(u"recusa (%s), sem entrar nada da lista" % frase,
               not rr.get("ok") and frase in (rr.get("erro") or u"")
               and len(F.cards()) == antes, str(rr))
    checar(u"lista vazia e recusada", not F.enfileirar([]).get("ok"))
    e = F.estado_publico([r["cartoes"][1]["id"]])
    checar(u"estado devolve id, rotulo, estado, posicao, origem e mensagem",
           e.get("ok") and len(e["cartoes"]) == 1
           and sorted(e["cartoes"][0]) == sorted(
               ["id", "rotulo", "estado", "posicao", "origem", "mensagem"]),
           str(e))
    tudo = F.estado_publico()
    checar(u"  e sem ids, todos os cartoes, na ordem da tela",
           [c["posicao"] for c in tudo["cartoes"]] == [1, 2])
    checar(u"  e o topo diz `rodando: false` com a fila parada esperando o "
           u"Iniciar", tudo.get("rodando") is False, str(tudo.get("rodando")))
    velho = L.andamento
    try:
        def _quebrado():
            raise RuntimeError(u"andamento indisponivel")
        L.andamento = _quebrado
        sem = F.estado_publico()
    finally:
        L.andamento = velho
    checar(u"  sem o andamento do lote, `rodando` fica de fora (desconhecido), "
           u"e o resto continua", "rodando" not in sem and sem.get("ok")
           and len(sem.get("cartoes") or ()) == 2, str(sorted(sem)))
    ja = len(F.cartao(r["cartoes"][0]["id"])["copiar_rs_para"])
    muitos = [_sub("soma%d" % k) for k in range(9 - ja)]
    antes = len(F.cards())
    rs = F.enfileirar([{"pasta": p1, "uid": u"1.2.3.4.5.6.7.1",
                        "copiar_rs_para": muitos},
                       {"pasta": _pasta("soma_outra"), "uid": u"9.8.7.6.5.4.1"}])
    checar(u"as pastas de copia somadas acima do teto recusam a lista inteira, "
           u"com o motivo", not rs.get("ok") and u"seriam 9" in (rs.get("erro")
                                                             or u"")
           and len(F.cards()) == antes
           and len(F.cartao(r["cartoes"][0]["id"])["copiar_rs_para"]) == ja,
           str(rs))
    corta = F._destinos
    try:
        F._destinos = lambda lista: corta(lista)[:8]
        ri = F.enfileirar([{"pasta": _pasta("isca_teto"), "uid": u"9.8.7.6.5.4.2",
                            "copiar_rs_para": [_sub("teto%d" % k)
                                               for k in range(9)]}])
    finally:
        F._destinos = corta
    checar(u"ISCA: com o corte calado de antes, as 9 pastas entram como 8 sem "
           u"aviso (a checagem sabe reprovar)", ri.get("ok"), str(ri))
    _zerar()


def teste_a_serie_que_roda_soma_a_pasta_de_copia():
    secao(u"C1: a serie que ja roda soma a pasta de copia nova")
    _zerar()
    p = _pasta("roda_soma")
    uid = u"1.2.840.31.1"
    d1, d2 = _sub("roda_dest1"), _sub("roda_dest2")
    F.enfileirar([{"pasta": p, "uid": uid, "copiar_rs_para": [d1]}])
    meio = {}

    def _durante(u):
        if u == uid:
            meio["r"] = F.enfileirar([{"pasta": p, "uid": uid,
                                       "copiar_rs_para": [d2]}])
            meio["rodando"] = F.estado_publico().get("rodando")
            cid = (meio["r"].get("cartoes") or [{}])[0].get("id")
            meio["copias"] = list((F.cartao(cid) or {}).get("copiar_rs_para")
                                  or ())
    d = Duble(durante=_durante)
    with Lote(d) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    checar(u"com a fila executando, o topo do estado diz `rodando: true`",
           meio.get("rodando") is True, str(meio.get("rodando")))
    checar(u"a mesma serie pedida de novo enquanto roda devolve o mesmo "
           u"cartao e soma a pasta de copia",
           (meio.get("r") or {}).get("ok") and meio.get("copias") == [d1, d2],
           str(meio))
    checar(u"  e ela nao roda duas vezes", d.vistos == [uid], str(d.vistos))
    _zerar()


def teste_o_contrato_c1_pela_rota():
    secao(u"C1: as rotas /api/fila/enfileirar e /api/fila/estado")
    _zerar()
    rotas = _app()
    for r in ("/api/fila", "/api/fila/estado", "/api/fila/enfileirar",
              "/api/fila/mover", "/api/fila/cancelar", "/api/fila/repor",
              "/api/fila/limpar", "/api/fila/overnight"):
        checar(u"a rota %s existe" % r, r in rotas)
    p = _pasta("rota1")
    d = _post(rotas, "/api/fila/enfileirar",
              {"itens": [{"pasta": p, "uid": u"1.2.840.1.2.3.4.5",
                          "modo": u"fast", "origem": u"dicombridge"}]})
    checar(u"a rota enfileira e responde {ok, cartoes:[{id, posicao}]}",
           d.get("ok") and d["cartoes"][0]["posicao"] == 1, str(d))
    e = _post(rotas, "/api/fila/estado", {"ids": [d["cartoes"][0]["id"]]})
    checar(u"a rota do estado devolve o cartao", e["cartoes"][0]["estado"]
           == Q.ESPERANDO and e["cartoes"][0]["origem"] == Q.DICOMBRIDGE,
           str(e))
    bruto = json.dumps(rotas["/api/fila"](), ensure_ascii=False)
    checar(u"o pacote da barra nao leva a pasta nem o UID inteiro",
           p not in bruto and u"1.2.840.1.2.3.4.5" not in bruto, bruto[:200])
    e2 = _post(rotas, "/api/fila/estado", {"ids": "nao e lista"})
    checar(u"corpo torto na rota do estado nao derruba nada", e2.get("ok"))
    _zerar()


def teste_o_clique_simples_e_a_copia_do_rtstruct():
    secao(u"o clique simples: uma serie, pronta, e o RTSTRUCT copiado")
    _zerar()
    p = _pasta("simples")
    uid = u"1.2.840.99.1.1.123456781"
    dest1, dest2 = _sub("dest_simples1"), _sub("dest_simples2")

    def _grava(u):
        with io.open(os.path.join(p, u"RS_RadAI_20261014_%s.dcm" % u[-8:]),
                     "w") as f:
            f.write(u"rs")
        with io.open(os.path.join(p, u"RS_RadAI_OUTRA_99999999.dcm"), "w") as f:
            f.write(u"outra")
    F.enfileirar([{"pasta": p, "uid": uid, "origem": u"dicombridge",
                   "copiar_rs_para": [dest1, dest2]}])
    d = Duble(durante=_grava)
    with Lote(d) as lt:
        r = lt.iniciar()
        checar(u"o lote aceitou", r.get("ok"), str(r))
        checar(u"  e terminou", esperar(lambda: not L.estado().get("rodando")))
    checar(u"a serie rodou uma vez", d.vistos == [uid], str(d.vistos))
    checar(u"  e o cartao ficou pronto", _estados() == [(uid, Q.PRONTO)],
           str(_estados()))
    for dd in (dest1, dest2):
        checar(u"o RTSTRUCT desta serie foi copiado para %s"
               % os.path.basename(dd),
               os.listdir(dd) == [u"RS_RadAI_20261014_%s.dcm" % uid[-8:]],
               str(os.listdir(dd)))
    c = F.cards()[0]
    checar(u"  e o cartao diz que copiou", u"copiado para 2 pasta" in
           (c.get("mensagem") or u""), c.get("mensagem"))
    checar(u"a vez foi devolvida", F.quem_tem_a_vez()["dono"] is None
           and not F.quem_tem_a_vez()["lote_quer"], str(F.quem_tem_a_vez()))
    _zerar()


def teste_a_copia_recusa_pasta_que_sincroniza():
    secao(u"a copia do RTSTRUCT recusa pasta que sincroniza")
    _zerar()
    p = _pasta("sinc")
    uid = u"1.2.840.99.1.1.555555551"
    nuvem = _sub("nuvem_falsa")
    with io.open(os.path.join(p, u"RS_RadAI_X_%s.dcm" % uid[-8:]), "w") as f:
        f.write(u"rs")
    F.enfileirar([{"pasta": p, "uid": uid, "copiar_rs_para": [nuvem]}])
    F.assumir(uid, p)
    os.environ["RADAI_RAIZES_NUVEM"] = nuvem
    try:
        import radai_archive
        radai_archive._CACHE_RAIZES["quando"] = None
        F.marcar(uid, "pronto", p)
        r = F.copiar_entrega(uid, p)
    finally:
        os.environ.pop("RADAI_RAIZES_NUVEM", None)
        radai_archive._CACHE_RAIZES["quando"] = None
    checar(u"nada foi copiado para a pasta que sincroniza",
           os.listdir(nuvem) == [] and r["copiados"] == 0, str(r))
    checar(u"  e o cartao diz por que", u"sincroniza" in
           (F.cards()[0].get("mensagem") or u""), F.cards()[0].get("mensagem"))
    _zerar()


def teste_o_limpar_pede_confirmacao_da_entrega_parcial():
    secao(u"o Limpar tira so o sucesso: a entrega parcial pede confirmacao")
    _zerar()
    ps = [(u"1.2.840.32.%d" % i, _pasta("parc%d" % i)) for i in range(2)]
    F.pedir([{"uid": u, "pasta": p} for u, p in ps])
    motivo = u"o FULL nao saiu (MemoryError); o OAR ficou"
    d = Duble(desfechos={ps[0][0]: {"parcial": {"conjunto": u"FULL",
                                                "motivo": motivo}}})
    with Lote(d) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    checar(u"a entrega que saiu parcial fecha o cartao como parcial, com o "
           u"motivo", sorted(_estados()) == sorted([(ps[0][0], Q.PARCIAL),
                                                    (ps[1][0], Q.PRONTO)])
           and motivo in (F.cards()[0].get("mensagem") or u"")
           + (F.cards()[1].get("mensagem") or u""), str(_estados()))
    r = F.limpar_fila()
    checar(u"o Limpar tira so o pronto, e conta o parcial entre os que pedem "
           u"confirmacao", r["tirados"] == 1 and r["falhas_restantes"] == 1
           and r["parciais_restantes"] == 1
           and _estados() == [(ps[0][0], Q.PARCIAL)], str(r))
    r2 = F.limpar_fila(com_falhas=True)
    checar(u"  confirmado, o parcial sai", r2["tirados"] == 1
           and _estados() == [], str(r2))
    _zerar()


def teste_limpar_no_meio_da_fila():
    secao(u"limpar no meio da fila: tira o pronto, nao toca no que roda")
    _zerar()
    ps = [(u"1.2.840.7.%d" % i, _pasta("meio%d" % i)) for i in range(4)]
    F.pedir([{"uid": u, "pasta": p} for u, p in ps[:1]])
    F.assumir(ps[0][0], ps[0][1])
    F.marcar(ps[0][0], "pronto", ps[0][1])
    F.pedir([{"uid": u, "pasta": p} for u, p in ps[1:]])
    meio = {}

    def _durante(uid):
        if uid == ps[1][0]:
            meio["r"] = F.limpar_fila()
            meio["est"] = _estados()
    d = Duble(durante=_durante)
    with Lote(d) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    checar(u"o Limpar no meio tirou so o pronto que ja estava la",
           meio.get("r", {}).get("tirados") == 1, str(meio.get("r")))
    checar(u"  e a serie que rodava continuou rodando",
           (ps[1][0], Q.RODANDO) in meio.get("est", []), str(meio.get("est")))
    checar(u"  e as que esperavam rodaram depois, na ordem",
           d.vistos == [ps[1][0], ps[2][0], ps[3][0]], str(d.vistos))
    _zerar()


def teste_cancelar_e_limpar():
    secao(u"cancelar e limpar: o cancelado pede confirmacao, o resto fica")
    _zerar()
    ps = [(u"1.2.840.8.%d" % i, _pasta("canc%d" % i)) for i in range(3)]
    F.pedir([{"uid": u, "pasta": p} for u, p in ps])
    d = Duble(desfechos={ps[0][0]: {"cancelado": True}})
    with Lote(d) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    est = _estados()
    checar(u"o Cancelar parou a fila na serie da vez", d.vistos == [ps[0][0]],
           str(d.vistos))
    checar(u"  a cancelada fica CANCELADA, e as outras esperam",
           sorted(est) == sorted([(ps[0][0], Q.CANCELADO),
                                  (ps[1][0], Q.ESPERANDO),
                                  (ps[2][0], Q.ESPERANDO)]), str(est))
    r = F.limpar_fila()
    checar(u"o Limpar nao tira a cancelada sem confirmacao",
           r["tirados"] == 0 and r["falhas_restantes"] == 1, str(r))
    r2 = F.limpar_fila(com_falhas=True)
    checar(u"  confirmado, tira, e as que esperam continuam",
           r2["tirados"] == 1 and sorted(_estados()) == sorted(
               [(ps[1][0], Q.ESPERANDO), (ps[2][0], Q.ESPERANDO)]),
           str(_estados()))
    d2 = Duble()
    with Lote(d2) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    checar(u"o Iniciar seguinte roda as que sobraram",
           d2.vistos == [ps[1][0], ps[2][0]], str(d2.vistos))
    _zerar()


def teste_subir_e_descer_muda_a_ordem_do_trabalho():
    secao(u"subir e descer muda a ordem em que as series rodam")
    _zerar()
    ps = [(u"1.2.840.9.%d" % i, _pasta("ordem%d" % i)) for i in range(3)]
    F.pedir([{"uid": u, "pasta": p} for u, p in ps])
    terceiro = [c["id"] for c in F.cards() if c["uid"] == ps[2][0]][0]
    F.mover_id(terceiro, -1)
    F.mover_id(terceiro, -1)
    F.mover_id(terceiro, -1)
    checar(u"a terceira subiu ate o topo (e o excesso nao quebra)",
           [c["uid"] for c in F.cards()] == [ps[2][0], ps[0][0], ps[1][0]],
           str([c["uid"] for c in F.cards()]))
    d = Duble()
    with Lote(d) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    checar(u"e o lote rodou na ordem da tela", d.vistos == [ps[2][0], ps[0][0],
                                                            ps[1][0]],
           str(d.vistos))
    _zerar()


def teste_o_dicombridge_enfileira_com_a_fila_rodando():
    secao(u"o DicomBridge pondo serie com a fila rodando")
    _zerar()
    ps = [(u"1.2.840.10.%d" % i, _pasta("db%d" % i)) for i in range(2)]
    bridge = (u"1.2.840.10.99", _pasta("db_bridge"))
    F.pedir([{"uid": u, "pasta": p} for u, p in ps])
    F.vigia_na_fila([{"uid": u"1.2.840.10.V1", "rotulo": u"vigia 1"}], 1)
    meio = {}

    def _durante(uid):
        if uid == ps[0][0]:
            meio["r"] = F.enfileirar([{"pasta": bridge[1], "uid": bridge[0],
                                       "origem": u"dicombridge"}])
            meio["ordem"] = [(c["uid"], c["origem"]) for c in F.cards()]
    d = Duble(durante=_durante)
    with Lote(d) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    checar(u"o pedido do DicomBridge entrou com a fila rodando",
           (meio.get("r") or {}).get("ok"), str(meio.get("r")))
    ordem = meio.get("ordem") or []
    checar(u"  e entrou DEPOIS das manuais que esperavam e ANTES do vigia",
           [u for u, _o in ordem] == [ps[0][0], ps[1][0], bridge[0],
                                      u"1.2.840.10.V1"], str(ordem))
    checar(u"  e rodou na mesma volta do lote, sem novo Iniciar",
           d.vistos == [ps[0][0], ps[1][0], bridge[0]], str(d.vistos))
    checar(u"  e a serie do vigia nao foi rodada pelo lote",
           u"1.2.840.10.V1" not in d.vistos)
    _zerar()


def teste_a_serie_do_vigia_termina_e_o_manual_vem_em_seguida():
    secao(u"A1: a serie do vigia que roda termina, e o manual vem logo depois")
    _zerar()
    vuid = u"1.2.840.11.V"
    checar(u"o vigia pega a vez", F.tentar_a_vez("vigia"))
    F.vigia_comecou(vuid, u"vigia", _pasta("a1v"))
    m = (u"1.2.840.11.M", _pasta("a1m"))
    F.pedir([{"uid": m[0], "pasta": m[1]}])
    linhas = []
    solta = threading.Event()
    d = Duble(segura={m[0]: solta})
    with Lote(d, ocupado=lambda: {"quem": "vigia", "o_que": u"série"},
              log=linhas.append) as lt:
        r = lt.iniciar()
        checar(u"o Iniciar com o vigia rodando NAO e recusado",
               r.get("ok") and r.get("espera_o_vigia"), str(r))
        checar(u"  o lote quer a vez imediatamente (o vigia nao pega outra)",
               F.quem_tem_a_vez()["lote_quer"] is True)
        checar(u"  e o log diz que a do vigia termina primeiro",
               esperar(lambda: any(u"termina primeiro" in str(x)
                                   for x in linhas), 60))
        time.sleep(0.3)
        checar(u"  e o manual NAO roda enquanto a serie do vigia nao acaba",
               d.vistos == [], str(d.vistos))
        cm = [c for c in F.cards() if c["uid"] == m[0]][0]
        checar(u"  e o cartao do manual diz que espera a do vigia",
               cm.get("mensagem") == F.FRASE_ESPERA_O_VIGIA, cm.get("mensagem"))
        F.vigia_terminou(vuid, "pronto")
        F.soltar_a_vez("vigia")
        checar(u"o vigia soltou a vez e NAO a pega de novo para a proxima "
               u"serie dele", F.tentar_a_vez("vigia") is False)
        checar(u"o vigia terminou: o manual roda em seguida",
               esperar(lambda: d.vistos == [m[0]], 5), str(d.vistos))
        checar(u"  e, com o lote rodando, o vigia espera",
               F.tentar_a_vez("vigia") is False)
        solta.set()
        esperar(lambda: not L.estado().get("rodando"))
    checar(u"o lote terminou e devolveu a vez: o vigia volta",
           F.tentar_a_vez("vigia") is True)
    F.soltar_a_vez("vigia")
    est = dict(_estados())
    checar(u"os dois cartoes terminaram prontos", est.get(vuid) == Q.PRONTO
           and est.get(m[0]) == Q.PRONTO, str(est))
    _zerar()


def teste_o_cancelar_do_vigia_e_o_pausar_na_espera():
    secao(u"forcar a parada do vigia, e pausar enquanto espera")
    _zerar()
    chamadas = []

    def _cancelar_vigia(pausar):
        chamadas.append(pausar)
        return {"ok": True, "interrompida": u"12345678"}
    capt = {}

    class _App(object):
        def get(self, r, **kw):
            def _reg(f):
                capt[r] = f
                return f
            return _reg

        def post(self, r, **kw):
            return self.get(r)

        def api_route(self, r, **kw):
            return self.get(r)
    guarda = dict(L._CFG)
    try:
        L.montar(_App(), {"ocupado": lambda: {"quem": "vigia"},
                          "cancelar_vigia": _cancelar_vigia,
                          "marcadores": MARC})
        r = capt["/api/pipeline/cancelar"]()
        checar(u"o Cancelar com o vigia rodando interrompe a serie DELE",
               r.get("ok") and chamadas == [True], str((r, chamadas)))
        checar(u"  sem lote esperando, o vigia fica pausado (nao retoma a "
               u"mesma serie)", r.get("lote_segue") is False)
        with L._TRAVA:
            L._JOB["rodando"] = True
        try:
            r2 = capt["/api/pipeline/cancelar"]()
        finally:
            with L._TRAVA:
                L._JOB["rodando"] = False
        checar(u"  com o lote esperando, o vigia nao pausa e o lote segue",
               chamadas[-1] is False and r2.get("lote_segue") is True,
               str((r2, chamadas)))
    finally:
        L._CFG.clear()
        L._CFG.update(guarda)
    _zerar()
    F.tentar_a_vez("vigia")
    m = (u"1.2.840.12.M", _pasta("pausa"))
    F.pedir([{"uid": m[0], "pasta": m[1]}])
    d = Duble()
    with Lote(d, ocupado=lambda: {"quem": "vigia"}) as lt:
        lt.iniciar()
        time.sleep(0.2)
        L.pausar(True)
        checar(u"Pausar enquanto o lote espera o vigia: o lote desiste",
               esperar(lambda: not L.estado().get("rodando"), 5))
    checar(u"  e nada rodou, e a serie continua esperando",
           d.vistos == [] and _estados() == [(m[0], Q.ESPERANDO)],
           str((d.vistos, _estados())))
    checar(u"  e o lote nao segura mais a vez", not F.quem_tem_a_vez()["lote_quer"])
    F.soltar_a_vez("vigia")
    _zerar()


def teste_a_fila_do_vigia_na_barra():
    secao(u"o que o vigia achou aparece depois do que entrou a mao")
    _zerar()
    F.pedir([{"uid": u"M1", "pasta": _pasta("vg_m1")}])
    itens = [{"uid": u"V%02d" % i, "rotulo": u"v%d" % i} for i in range(30)]
    n = F.vigia_na_fila(itens, 30)
    vis = [c for c in F.cards() if c.get("origem") == Q.VIGIA]
    checar(u"a barra mostra no maximo %d do vigia" % F.TETO_DO_VIGIA_NA_TELA,
           n == F.TETO_DO_VIGIA_NA_TELA and len(vis) == n, str(n))
    checar(u"  e o resumo diz quantas ha ao todo", F.resumo()["vigia_na_fila"]
           == 30)
    checar(u"  e todas vem depois do manual", F.cards()[0]["uid"] == u"M1")
    ids = [c["id"] for c in vis]
    F.vigia_na_fila(itens[1:], 29)
    vis2 = [c for c in F.cards() if c.get("origem") == Q.VIGIA]
    checar(u"a varredura seguinte guarda o id de quem continua",
           [c["id"] for c in vis2][:5] == ids[1:6], str(vis2[:2]))
    F.vigia_comecou(u"V01", u"v1", _pasta("vg_v1"))
    checar(u"a serie que o vigia pega vai ao topo, rodando",
           F.cards()[0]["uid"] == u"V01"
           and F.cards()[0]["estado"] == Q.RODANDO)
    F.vigia_na_fila(itens[1:], 29)
    checar(u"  e a varredura nao a duplica como espera",
           [c["uid"] for c in F.cards()].count(u"V01") == 1)
    F.vigia_terminou(u"V01", F.VIGIA_VOLTA)
    checar(u"a serie adiada volta para a fila do vigia (o cartao sai)",
           u"V01" not in [c["uid"] for c in F.cards()
                          if c.get("estado") == Q.RODANDO])
    vigia_espera = [c for c in F.para_tela(F.cards())
                    if c.get("origem") == Q.VIGIA]
    checar(u"o cartao do vigia que espera nao sobe, nao desce e nao sai",
           all(not (a["acoes"]["subir"] or a["acoes"]["descer"]
                    or a["acoes"]["tirar"]) for a in vigia_espera))
    F.vigia_na_fila([], 0)
    checar(u"vigia desligado: os cartoes dele somem da barra",
           not [c for c in F.cards() if c.get("origem") == Q.VIGIA
                and c.get("estado") == Q.ESPERANDO])
    _zerar()


def teste_duas_estacoes_na_mesma_pasta():
    secao(u"duas estacoes na mesma pasta: os locks de verdade")
    _zerar()
    a, b = _vigia("PC_A"), _vigia("PC_B")
    p = _pasta("duas")
    uid = u"1.2.840.13.1"
    checar(u"a estacao A pega a serie", a.claim(p, uid, {"machine": "PC_A"}))
    F.pedir([{"uid": uid, "pasta": p}])
    marc_b = {"claim": b.claim, "unclaim": b.unclaim, "has_marker": b.has_marker,
              "read_marker": b.read_marker, "m_path": b.m_path,
              "renovar": b.renovar_lock, "diagnostico": b._diagnostico_do_lock}
    vistos = []

    def _uma(s, *aa, **kk):
        vistos.append(s.get("uid"))
        r = {"uid": s["uid"], "erro": "", "pulada": "", "pulo": "",
             "segundos": 0.0}
        if b.has_marker(s["pasta"], s["uid"], "done"):
            r.update({"pulada": "ja concluida", "pulo": "concluida"})
            return r
        if not b.claim(s["pasta"], s["uid"], {"machine": "PC_B"}):
            r.update({"pulada": "outra estacao", "pulo": "outra",
                      "dono": L._dono_do_lock(s, marc_b)})
            return r
        b.unclaim(s["pasta"], s["uid"])
        return r
    guardados = (L.pode_segmentar, L._uma_serie)
    L.pode_segmentar = lambda *x, **k: (True, "")
    L._uma_serie = _uma
    try:
        L.iniciar(F.series_esperando(), ja_na_fila=True, marcadores=marc_b,
                  maquina="PC_B")
        esperar(lambda: not L.estado().get("rodando"))
        c = F.cards()[0]
        checar(u"na estacao B a serie fica PULADA, com o nome de A",
               c["estado"] == Q.PULADO and c.get("dono") == u"PC_A", str(c))
        a.m_path(p, uid, "done", criar=True).write_text(u"{}", encoding="utf-8")
        a.unclaim(p, uid)
        L.iniciar([], ja_na_fila=True, marcadores=marc_b, maquina="PC_B")
        esperar(lambda: not L.estado().get("rodando"))
        c = F.cards()[0]
        checar(u"A entregou: em B ela volta, e fica pronta SEM refazer",
               c["estado"] == Q.PRONTO and c.get("ja_concluida") is True,
               str(c))
        checar(u"  e o marcador de pronta continua la",
               a.has_marker(p, uid, "done"))
    finally:
        L.pode_segmentar, L._uma_serie = guardados
        with L._TRAVA:
            L._JOB.update({"rodando": False, "cancelar": False})
    _zerar()


_VIGIAS = {}


def _vigia(maquina):
    if maquina in _VIGIAS:
        return _VIGIAS[maquina]
    base = _sub("vigia_" + maquina)
    cfg = os.path.join(base, "radai_watcher.config")
    with io.open(cfg, "w", encoding="utf-8") as f:
        f.write(u"ROOT=\nLOG_DIR=%s\n" % os.path.join(base, "log"))
    velhos = dict((k, os.environ.get(k)) for k in
                  ("RADAI_CONFIG", "RADAI_MACHINE", "LOCALAPPDATA"))
    os.environ["RADAI_CONFIG"] = cfg
    os.environ["RADAI_MACHINE"] = maquina
    os.environ["LOCALAPPDATA"] = os.path.join(base, "appdata")
    try:
        spec = importlib.util.spec_from_file_location(
            "vigia_sim_%s" % maquina, _componentes.fonte("app/radai_watcher.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod._CONSOLE["saida"] = io.StringIO()
    finally:
        for k, v in velhos.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    _VIGIAS[maquina] = mod
    return mod


def _pid_morto():
    import subprocess
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def _lock_de(mod, pasta, uid, maquina, pid, heartbeat=None):
    lp = mod.m_path(pasta, uid, "lock", criar=True)
    dado = {"machine": maquina, "pid_os": pid,
            "token": u"%s#%s" % (maquina, pid),
            "heartbeat": heartbeat or time.time(),
            "start": time.strftime("%Y-%m-%d %H:%M:%S")}
    criado = mod._criado_em(pid)
    if criado is not None:
        dado["criado"] = criado
    lp.write_text(json.dumps(dado), encoding="utf-8")
    return lp


def teste_a_trava_de_processo_morto():
    secao(u"a trava de processo morto diz a verdade, e o Limpar a solta")
    _zerar()
    a = _vigia("PC_A")
    morto = _pid_morto()
    p1, p2, p3, p4 = (_pasta("trava%d" % i) for i in range(4))
    u1, u2, u3, u4 = (u"1.2.840.14.%d" % i for i in range(4))
    lp1 = _lock_de(a, p1, u1, "PC_A", morto)
    lp2 = _lock_de(a, p2, u2, "PC_OUTRA", morto)
    lp3 = _lock_de(a, p3, u3, "PC_A", os.getppid())
    lp4 = _lock_de(a, p4, u4, "PC_A", morto)
    a.m_path(p4, u4, "done", criar=True).write_text(u"{}", encoding="utf-8")
    estado, _d = a._diagnostico_do_lock(p1, u1)
    checar(u"batimento recente com o processo desta maquina morto: «morto»",
           estado == "morto", estado)
    checar(u"  e o de outra maquina continua «trabalhando» (nao se julga)",
           a._diagnostico_do_lock(p2, u2)[0] == "trabalhando")
    checar(u"  e o de um processo vivo continua «trabalhando»",
           a._diagnostico_do_lock(p3, u3)[0] == "trabalhando")
    d3 = json.loads(lp3.read_text(encoding="utf-8"))
    checar(u"  a trava do fantoma e como a real: o inicio de agora e o "
           u"instante de criacao do dono",
           d3.get("start", u"")[:10] == time.strftime("%Y-%m-%d")
           and d3.get("criado") == a._criado_em(os.getppid())
           and d3.get("criado") is not None, str(d3))
    lp3.write_text(json.dumps(dict(d3, criado=int(d3.get("criado") or 0) + 1)),
                   encoding="utf-8")
    checar(u"  (isca) com outro instante de criacao, o processo vivo nao e "
           u"o dono",
           a._diagnostico_do_lock(p3, u3)[0] != "trabalhando")
    lp3.write_text(json.dumps(d3), encoding="utf-8")
    marc = {"has_marker": a.has_marker, "read_marker": a.read_marker,
            "diagnostico": a._diagnostico_do_lock}
    sit = L._situacao({"pasta": p1, "uid": u1}, marc)
    checar(u"o «Rodar agora» deixa de dizer «em processamento»: parou no meio",
           sit.get("situacao") == "retomavel", str(sit))
    F.pedir([{"uid": u, "pasta": p} for u, p in
             ((u1, p1), (u2, p2), (u3, p3), (u4, p4))])
    for u, p in ((u1, p1), (u2, p2), (u3, p3), (u4, p4)):
        F.assumir(u, p)
        F.marcar(u, "falhou", p)
    F.ligar_ganchos(soltar_trava_morta=a.soltar_trava_morta)
    r = F.limpar_fila()
    checar(u"o Limpar solta a trava morta desta maquina",
           not lp1.exists() and r["travas_soltas"] >= 1, str(r))
    checar(u"  e NAO toca a trava de outra maquina", lp2.exists())
    checar(u"  nem a de processo vivo", lp3.exists())
    checar(u"  e o marcador de serie pronta continua la",
           a.has_marker(p4, u4, "done"))
    checar(u"  e diz no fim o que fez", u"trava" in r["frase"], r["frase"])
    c1 = [c for c in F.para_tela(F.cards()) if c["uid"] == u1[-8:]][0]
    checar(u"  e o cartao oferece «pôr na fila de novo»",
           c1["acoes"]["repor"] is True and c1.get("trava_solta") is True,
           str(c1))
    cid = [c["id"] for c in F.cards() if c["uid"] == u1][0]
    novo = F.repor(cid)
    checar(u"«pôr na fila de novo» devolve a serie a fila, esperando",
           novo and [c["estado"] for c in F.cards() if c["uid"] == u1]
           == [Q.ESPERANDO], str(_estados()))
    for lp in (lp2, lp3, lp4):
        try:
            lp.unlink()
        except OSError:
            pass
    _zerar()


def teste_reabrir_com_a_fila_cheia():
    secao(u"fechar e reabrir com a fila cheia")
    _zerar()
    F._PERSISTIR["ligada"] = True
    ps = dict((n, (u"1.2.840.15.%d" % i, _pasta("reab_%s" % n)))
              for i, n in enumerate((u"pronta", u"roda", u"espera", u"falhou",
                                     u"parcial", u"some", u"bridge")))
    F.pedir([{"uid": ps[n][0], "pasta": ps[n][1],
              "rotulo": u"ISCA BELTRANO %s" % n, "pid": u"FANTOMA-0001",
              "modo": u"perso", "tasks": {u"teeth": 1}}
             for n in (u"pronta", u"roda", u"espera", u"falhou", u"parcial",
                       u"some")])
    F.enfileirar([{"pasta": ps[u"bridge"][1], "uid": ps[u"bridge"][0],
                   "origem": u"dicombridge",
                   "copiar_rs_para": [_sub("reab_destino")]}])
    for n, est in ((u"pronta", "pronto"), (u"falhou", "falhou")):
        F.assumir(*ps[n])
        F.marcar(ps[n][0], est, ps[n][1])
    F.assumir(*ps[u"parcial"])
    F.marcar(ps[u"parcial"][0], "pronto", ps[u"parcial"][1],
             pendentes=[{"task": u"abdominal_muscles", "pedia_gib": 9.5,
                         "livre_gib": 2.0}])
    F.assumir(*ps[u"roda"])
    F.vigia_na_fila([{"uid": u"1.2.840.15.V", "rotulo": u"vigia"}], 1)
    checar(u"a fila foi gravada", os.path.isfile(F.arquivo_da_fila())
           and os.path.isfile(F.arquivo_do_indice()), F.estado_da_gravacao())
    bruto = io.open(F.arquivo_da_fila(), encoding="utf-8").read()
    checar(u"o arquivo da fila (em RADIOTERAPIA_AI) nao tem pasta, nome nem "
           u"PatientID", u"ISCA" not in bruto and u"FANTOMA-0001" not in bruto
           and u"reab_" not in bruto and u"series" not in bruto, bruto[:200])
    checar(u"  e tem os UID e a escolha da serie", ps[u"espera"][0] in bruto
           and u"teeth" in bruto)
    checar(u"  e nao grava o que o vigia so achou (ele acha de novo)",
           u"1.2.840.15.V" not in bruto)
    indice = io.open(F.arquivo_do_indice(), encoding="utf-8").read()
    checar(u"a pasta mora no indice do acervo",
           u"reab_espera" in indice and os.path.dirname(F.arquivo_do_indice())
           == os.environ["RADAI_CALIB_DIR"])
    shutil.rmtree(ps[u"some"][1])
    F._CARDS[:] = []
    F._PERSISTIR["ligada"] = False
    r = F.carregar()
    est = dict(_estados())
    checar(u"reaberta: a pronta saiu", ps[u"pronta"][0] not in est, str(est))
    checar(u"  a que rodava volta como falha, e pode voltar a fila",
           est.get(ps[u"roda"][0]) == Q.FALHOU and [
               c for c in F.para_tela(F.cards())
               if c["uid"] == ps[u"roda"][0][-8:]][0]["acoes"]["repor"],
           str(est))
    c_roda = [c for c in F.cards() if c["uid"] == ps[u"roda"][0]][0]
    checar(u"    com a frase de que o programa fechou no meio",
           c_roda.get("mensagem") == F.FRASE_FECHOU_NO_MEIO)
    checar(u"  a que esperava volta esperando, com o rotulo e a escolha",
           est.get(ps[u"espera"][0]) == Q.ESPERANDO
           and [c for c in F.cards() if c["uid"] == ps[u"espera"][0]][0]
           ["carga"].get("tasks") == {u"teeth": 1}
           and [c for c in F.cards() if c["uid"] == ps[u"espera"][0]][0]
           ["rotulo"] == u"ISCA BELTRANO espera", str(est))
    checar(u"  a que falhou volta para mostrar o que refazer",
           est.get(ps[u"falhou"][0]) == Q.FALHOU)
    cp = [c for c in F.cards() if c["uid"] == ps[u"parcial"][0]][0]
    checar(u"  a parcial volta com o complemento pendente",
           cp["estado"] == Q.PARCIAL and cp["pendentes_por_memoria"]
           [0]["task"] == u"abdominal_muscles", str(cp))
    cs = [c for c in F.cards() if c["uid"] == ps[u"some"][0]][0]
    checar(u"  a pasta que sumiu volta como falha «série não encontrada»",
           cs["estado"] == Q.FALHOU
           and cs["mensagem"] == F.FRASE_NAO_ENCONTRADA, str(cs))
    checar(u"    e sem oferecer «pôr na fila de novo»",
           not [c for c in F.para_tela(F.cards())
                if c["uid"] == ps[u"some"][0][-8:]][0]["acoes"]["repor"])
    cb = [c for c in F.cards() if c["uid"] == ps[u"bridge"][0]][0]
    checar(u"  o pedido do DicomBridge volta com a origem e a pasta de copia",
           cb["origem"] == Q.DICOMBRIDGE and cb["copiar_rs_para"],
           str(cb))
    checar(u"  e o resumo bate", r["falharam"] == 1
           and r["nao_encontradas"] == 1, str(r))
    F.assumir(*ps[u"espera"])
    F.ao_fechar()
    F._CARDS[:] = []
    F._PERSISTIR["ligada"] = False
    F.carregar()
    est2 = dict(_estados())
    checar(u"fechar pelo botao com uma serie rodando: ela volta com falha",
           est2.get(ps[u"espera"][0]) == Q.FALHOU, str(est2))
    _zerar()


def teste_onde_a_fila_mora():
    secao(u"onde a fila mora: C:\\RADIOTERAPIA_AI, e a bateria nunca grava la")
    guarda = dict((k, os.environ.get(k)) for k in
                  ("RADAI_FILA_DIR", "RADAI_CALIB_DIR", "SystemDrive"))
    try:
        os.environ.pop("RADAI_FILA_DIR", None)
        os.environ.pop("RADAI_CALIB_DIR", None)
        os.environ["SystemDrive"] = u"C:"
        checar(u"na estacao: C:\\RADIOTERAPIA_AI\\fila",
               os.path.normcase(F.pasta_da_fila())
               == os.path.normcase(u"C:\\RADIOTERAPIA_AI\\fila"),
               F.pasta_da_fila())
        os.environ["RADAI_CALIB_DIR"] = _sub("acervo_isolado")
        checar(u"com o acervo isolado (bateria, prova), a fila vai junto",
               F.pasta_da_fila() == os.path.join(_sub("acervo_isolado"), u"fila"),
               F.pasta_da_fila())
        os.environ["RADAI_FILA_DIR"] = _sub("fila_pedida")
        checar(u"e RADAI_FILA_DIR vence", F.pasta_da_fila() == _sub("fila_pedida"))
    finally:
        for k, v in guarda.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    _zerar()
    velha = os.environ["RADAI_FILA_DIR"]
    os.environ["RADAI_FILA_DIR"] = _sub("fila_vazia")
    try:
        F.carregar()
        F.limpar()
        F.ao_fechar()
        checar(u"fila vazia e sem arquivo: subir, limpar e fechar nao gravam "
               u"nada", os.listdir(_sub("fila_vazia")) == [],
               str(os.listdir(_sub("fila_vazia"))))
        F.pedir([{"uid": u"1.2.840.20.1", "pasta": _pasta("vazia")}])
        checar(u"  e o primeiro cartao grava", os.path.isfile(F.arquivo_da_fila()))
    finally:
        os.environ["RADAI_FILA_DIR"] = velha
    _zerar()


def teste_a_fila_nao_grava_em_pasta_que_sincroniza():
    secao(u"a fila nao grava em pasta que sincroniza")
    _zerar()
    fila = os.environ["RADAI_FILA_DIR"]
    for nome in os.listdir(fila):
        os.remove(os.path.join(fila, nome))
    os.environ["RADAI_RAIZES_NUVEM"] = fila
    try:
        import radai_archive
        radai_archive._CACHE_RAIZES["quando"] = None
        F.carregar()
        F.pedir([{"uid": u"1.2.840.16.1", "pasta": _pasta("nuvem")}])
        checar(u"a gravacao fica desligada, e diz por que",
               not F.estado_da_gravacao()["ligada"]
               and u"sincroniza" in F.estado_da_gravacao()["erro"],
               str(F.estado_da_gravacao()))
        checar(u"  e nenhum arquivo foi escrito na pasta espelhada",
               os.listdir(fila) == [], str(os.listdir(fila)))
    finally:
        os.environ.pop("RADAI_RAIZES_NUVEM", None)
        radai_archive._CACHE_RAIZES["quando"] = None
    _zerar()


def teste_reabrir_solta_a_trava_e_acha_pelo_acervo():
    secao(u"ao reabrir: a trava do processo morto sai, e a pasta vem do acervo")
    _zerar()
    a = _vigia("PC_A")
    F._PERSISTIR["ligada"] = True
    p = _pasta("reab_trava")
    uid = u"1.2.840.17.1"
    F.pedir([{"uid": uid, "pasta": p}])
    F.assumir(uid, p)
    lp = _lock_de(a, p, uid, "PC_A", _pid_morto())
    F._CARDS[:] = []
    F._PERSISTIR["ligada"] = False
    F.ligar_ganchos(soltar_trava_morta=a.soltar_trava_morta)
    r = F.carregar()
    checar(u"a trava da serie que rodava sai (sem trava, ela pode voltar)",
           not lp.exists() and r.get("travas_soltas") == 1, str(r))
    novo = _pasta("reab_movida")
    u2 = u"1.2.840.17.2"
    F._PERSISTIR["ligada"] = True
    F.pedir([{"uid": u2, "pasta": _pasta("reab_velha")}])
    shutil.rmtree(_pasta("reab_velha"))
    import radai_archive
    radai_archive.registrar_serie(uid=u2, pasta=novo, rs=u"x.dcm")
    F._CARDS[:] = []
    F._PERSISTIR["ligada"] = False
    F.carregar()
    c = [c for c in F.cards() if c["uid"] == u2][0]
    checar(u"a pasta que mudou de lugar e achada pelo acervo",
           c["estado"] == Q.ESPERANDO and c["pasta"] == novo, str(c))
    _zerar()


def teste_o_complemento_por_memoria():
    secao(u"C4: a task que nao coube volta a cada hora ociosa")
    _zerar()
    p = _pasta("comp")
    uid = u"1.2.840.18.1"
    F.pedir([{"uid": uid, "pasta": p, "modo": u"auto"}])
    pend = [{"task": u"abdominal_muscles", "pedia_gib": 9.5, "livre_gib": 2.0}]
    d = Duble(desfechos={uid: {"tasks_puladas_por_memoria": pend}})
    with Lote(d) as lt:
        lt.iniciar()
        esperar(lambda: not L.estado().get("rodando"))
    c = F.cards()[0]
    checar(u"a serie sai PARCIAL, com o que ficou de fora e os numeros",
           c["estado"] == Q.PARCIAL and c["pendentes_por_memoria"][0]["task"]
           == u"abdominal_muscles" and u"pedia 9.5 GiB, havia 2.0 GiB"
           in c["mensagem"], str(c))
    checar(u"  e o Limpar nao a tira enquanto o complemento espera",
           F.limpar_fila()["tirados"] == 0 and len(F.cards()) == 1)
    agora = time.time()
    checar(u"antes de uma hora, nao tenta",
           F.complemento_na_vez(64.0, agora=agora + 60) is None)
    checar(u"depois de uma hora, sem memoria, nao tenta",
           F.complemento_na_vez(4.0, agora=agora + 3700) is None)
    checar(u"depois de uma hora, com memoria, e a vez dela",
           (F.complemento_na_vez(16.0, agora=agora + 3700) or {}).get("uid")
           == uid)
    guarda = dict(L._CFG)
    linhas = []
    L._CFG.update({"marcadores": MARC, "ocupado": lambda: None,
                   "log": linhas.append, "maquina": "BATERIA"})
    try:
        F.pedir([{"uid": u"1.2.840.18.9", "pasta": _pasta("comp_manual")}])
        checar(u"com serie pedida a mao esperando, a estacao nao esta ociosa",
               L.tentar_complemento(livre_gib=16.0, agora=agora + 3700)
               is None)
        F.tirar([c["id"] for c in F.cards() if c["uid"] == u"1.2.840.18.9"][0])
        L._CFG["ocupado"] = lambda: {"quem": "vigia"}
        checar(u"com o vigia segmentando, tambem nao",
               L.tentar_complemento(livre_gib=16.0, agora=agora + 3700)
               is None)
        L._CFG["ocupado"] = lambda: None
        d2 = Duble(desfechos={uid: {"tasks_puladas_por_memoria": pend}})
        with Lote(d2):
            r = L.tentar_complemento(livre_gib=16.0, agora=agora + 3700)
            checar(u"ociosa e com memoria: o complemento comeca sozinho",
                   (r or {}).get("ok"), str(r))
            esperar(lambda: not L.estado().get("rodando"))
        carga = d2.cargas[0] if d2.cargas else {}
        checar(u"  pede SUBSTITUIR a entrega parcial, com a mesma escolha",
               carga.get("substituir") is True and carga.get("modo") == u"auto"
               and carga.get("complemento_de_memoria")
               == [u"abdominal_muscles"], str(carga))
        c = F.cards()[0]
        checar(u"  ainda nao coube: continua parcial, e diz que tentou",
               c["estado"] == Q.PARCIAL and u"tentou de novo" in c["mensagem"],
               c["mensagem"])
        d3 = Duble()
        with Lote(d3):
            L.tentar_complemento(livre_gib=16.0, agora=time.time() + 3700)
            esperar(lambda: not L.estado().get("rodando"))
        c = F.cards()[0]
        checar(u"coube: o cartao fica pronto, com a linha da substituicao",
               c["estado"] == Q.PRONTO and c["mensagem"].startswith(
                   u"completada às") and c["mensagem"].endswith(
                   u"substituiu a parcial"), str(c))
        checar(u"  e o log diz que o complemento rodou",
               any(u"complemento" in str(x) for x in linhas))
    finally:
        L._CFG.clear()
        L._CFG.update(guarda)
    _zerar()


def teste_o_cartao_do_vigia_conta_o_desfecho():
    secao(u"o desfecho da serie do vigia chega ao cartao")
    _zerar()
    a = _vigia("PC_A")
    casos = (
        ({"ok": True, "faltou": [{"estrutura": u"Heart_ai"}],
          "tasks_puladas_por_memoria": [{"task": u"t", "pedia_gib": 9,
                                         "livre_gib": 1}]}, Q.PARCIAL),
        ({"ok": True}, Q.PRONTO),
        ({"cancelada": True}, Q.CANCELADO),
        ({"encerrada": True}, Q.FALHOU),
        ({"erro": u"falhou em C:\\pac\\SILVA\\x", "classe": "DETERMINISTICO"},
         Q.FALHOU),
        ({"erro": u"descartada: outra", "classe": ""}, Q.PRONTO),
        ({"classe": a.RECURSO}, None))
    for k, (info, esperado) in enumerate(casos):
        uid = u"1.2.840.19.%d" % k
        F.vigia_comecou(uid, u"vigia %d" % k, _pasta("vd%d" % k))
        a.ULTIMO_DESFECHO.clear()
        a.ULTIMO_DESFECHO.update(info)
        a.ULTIMO_DESFECHO["uid"] = uid
        a._contar_o_desfecho_a_fila(uid)
        c = [x for x in F.cards() if x["uid"] == uid]
        if esperado is None:
            checar(u"adiada por recurso: o cartao sai (volta a fila do vigia)",
                   c == [], str(c))
        else:
            checar(u"desfecho %s -> %s" % (sorted(info)[0], esperado),
                   c and c[0]["estado"] == esperado, str(c))
    falhou = [x for x in F.para_tela(F.cards())
              if x["uid"] == u"1.2.840.19.4"[-8:]][0]
    checar(u"a falha do vigia vai ao cartao sem a pasta do paciente",
           u"SILVA" not in (falhou.get("mensagem") or u""), falhou.get("mensagem"))
    _zerar()


def teste_o_log_segue_depois_de_800_linhas():
    secao(u"o log da tela segue depois das 800 linhas")
    a = _vigia("PC_LOG")
    with a.LOCK_DO_LOG:
        a.LOGBUF.clear()
        a.LOGSEQ[0] = 0
    for i in range(1000):
        a.wlog(u"linha %d" % i)
    fatia, prox, _ = a.fatia_do_log(0, 400)
    checar(u"o cursor 0 depois de 1000 linhas comeca na primeira guardada",
           fatia[0].endswith(u"linha 200") and prox == 600, str((fatia[0], prox)))
    cursor = prox
    fatia, cursor, _ = a.fatia_do_log(cursor, 400)
    checar(u"  e a segunda volta chega ao fim", cursor == 1000
           and fatia[-1].endswith(u"linha 999"), str(cursor))
    for i in range(1000, 1300):
        a.wlog(u"linha %d" % i)
    fatia, cursor2, _ = a.fatia_do_log(cursor, 400)
    checar(u"com o buffer cheio, as linhas NOVAS continuam chegando",
           len(fatia) == 300 and fatia[0].endswith(u"linha 1000")
           and cursor2 == 1300, str((len(fatia), cursor2)))
    fatia, c3, rein = a.fatia_do_log(99999, 400)
    checar(u"cursor maior que o total (o programa reabriu): recomeca",
           rein and len(fatia) == 400, str((len(fatia), c3, rein)))
    import radai_todo as T
    sys.modules["__main__"].LOGBUF = a.LOGBUF
    sys.modules["__main__"].fatia_do_log = a.fatia_do_log
    sys.modules["__main__"].STATE = a.STATE
    try:
        linhas, prox, _e = T._fatia_do_log(1250, 400)
        checar(u"a rota do log usa o numero de sequencia",
               prox == 1300 and len(linhas) == 50
               and linhas[0]["txt"] == u"linha 1250", str((prox, len(linhas))))
        del sys.modules["__main__"].fatia_do_log
        linhas_v, prox_v, _e = T._fatia_do_log(1250, 400)
        checar(u"  (isca) pelo indice de antes, o cursor 1250 nao traz nada -- "
               u"a checagem discrimina", linhas_v == [] and prox_v == 800,
               str((len(linhas_v), prox_v)))
    finally:
        for k in ("LOGBUF", "fatia_do_log", "STATE"):
            if hasattr(sys.modules["__main__"], k):
                delattr(sys.modules["__main__"], k)


def _node():
    return shutil.which("node")


def _funcao_js(js, nome):
    i = js.find(u"function %s(" % nome)
    if i < 0:
        return u""
    k = js.find(u"{", i)
    prof = 0
    for j in range(k, len(js)):
        if js[j] == u"{":
            prof += 1
        elif js[j] == u"}":
            prof -= 1
            if prof == 0:
                return js[i:j + 1]
    return u""


def _rodar_js(js):
    import subprocess
    d = tempfile.mkdtemp(prefix="radai_fila_sim_js_")
    alvo = os.path.join(d, "x.js")
    try:
        with io.open(alvo, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run([_node(), alvo], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for ln in reversed((r.stdout or u"").splitlines()):
        if ln.startswith(u"JSON:"):
            return json.loads(ln[5:]), u""
    return None, ((r.stderr or u"") + (r.stdout or u""))[-300:]


def teste_a_barra_aberta_recolhida_e_o_dicombridge():
    secao(u"a barra: recolhida no HTML, abre sozinha no Rodar agora e no Ver "
          u"segmentacao, e abre com o DicomBridge")
    import radai_todo as T
    import radai_menu
    checar(u"so o Rodar agora e o Ver segmentacao abrem a barra sozinhos",
           T.TELAS_QUE_ABREM_SOZINHAS == (u"lote", u"ver"),
           str(T.TELAS_QUE_ABREM_SOZINHAS))
    import re
    inicial = []
    for tela in (u"lote", u"bridge_laudo", u"ver", u"recon_anatomia"):
        p = radai_menu.aplicar(u"<html><head></head><body>x</body></html>", tela)
        m = re.search(r'<html class="dir-recolhida" data-dir-sozinha="(\d)">', p)
        inicial.append(m.group(1) if m else None)
    porta = radai_menu.aplicar_porta(u"<html><head></head><body>x</body></html>")
    checar(u"a porta nao tem a barra", u'class="radai-tarefas"' not in porta
           and u"radai-tarefas-css" not in porta)
    if not _node():
        checar(u"node disponivel", False, u"PULADO")
        return
    fontes = [_funcao_js(T.HTML, u"radaiFilaChegouDoBridge")]
    checar(u"as funcoes estao na barra", all(fontes))
    js = (u"var CH = [];\nvar window = {uiDireita: function(v){ CH.push(v) }};\n"
          u"function radaiTfPontoFila(){}\n"
          u"var RADAI_FILA_IDS = null;\n" + u"\n".join(fontes)
          + u"""
var R = {};
R.primeira = radaiFilaChegouDoBridge([{id: 'a', origem: 'dicombridge'}]);
R.mesma = radaiFilaChegouDoBridge([{id: 'a', origem: 'dicombridge'}]);
R.lote = radaiFilaChegouDoBridge([{id: 'a', origem: 'dicombridge'},
                                  {id: 'b', origem: 'rodar_agora'}]);
R.nova = radaiFilaChegouDoBridge([{id: 'a', origem: 'dicombridge'},
                                  {id: 'b', origem: 'rodar_agora'},
                                  {id: 'c', origem: 'dicombridge'}]);
console.log('JSON:' + JSON.stringify(R));
""")
    r, erro = _rodar_js(js)
    checar(u"a barra executa no node", r is not None, erro)
    if not r:
        return
    checar(u"todas nascem recolhidas no HTML; abrem sozinhas so o Rodar agora e o "
           u"Ver segmentacao", inicial == [u"1", u"0", u"1", u"0"], str(inicial))
    checar(u"o primeiro retrato nao abre nada (a historia nao e novidade)",
           r["primeira"] is False)
    checar(u"  nem o mesmo cartao de novo, nem um do Rodar agora",
           r["mesma"] is False and r["lote"] is False)
    checar(u"  e um cartao NOVO do DicomBridge abre a barra",
           r["nova"] is True)
    checar(u"window.radaiFilaAbrir existe na barra",
           u"window.radaiFilaAbrir = function" in T.HTML)
    i = T.HTML.find(u"window.radaiFilaAbrir = function")
    publica = T.HTML[i:T.HTML.find(u"};", i) + 2] if i >= 0 else u""
    interna = _funcao_js(T.HTML, u"radaiFilaAbrirBarra")
    checar(u"a funcao interna tem nome proprio (nao e a global publicada)",
           bool(interna) and u"function radaiFilaAbrir(" not in T.HTML)

    def _chamar(js_da_barra):
        prog = (u"const vm = require('vm');\n"
                u"globalThis.window = globalThis;\n"
                u"globalThis.R = {uiDireita: [], aba: [], carregou: 0};\n"
                u"vm.runInThisContext(" + json.dumps(
                    u"function radaiTfAba(q){ R.aba.push(q) }\n"
                    u"function radaiTfPontoFila(){}\n"
                    u"function radaiFilaCarregar(){ R.carregou++ }\n"
                    u"window.uiDireita = function(v){ R.uiDireita.push(v) };\n"
                    + js_da_barra) + u");\n"
                u"try{ R.volta = window.radaiFilaAbrir(); }"
                u"catch(e){ R.erro = String(e && e.name) }\n"
                u"console.log('JSON:' + JSON.stringify(R));\n")
        return _rodar_js(prog)
    r2, erro2 = _chamar(interna + u"\n" + publica)
    checar(u"window.radaiFilaAbrir() de verdade, no escopo global da pagina: "
           u"a barra abre na aba da fila e recarrega",
           r2 is not None and not r2.get("erro") and r2["uiDireita"] == [u"0"]
           and r2["aba"] == [u"fila"] and r2["carregou"] == 1, erro2 or str(r2))
    velho = (interna.replace(u"function radaiFilaAbrirBarra(",
                             u"function radaiFilaAbrir(")
             + u"\n" + publica.replace(u"radaiFilaAbrirBarra();",
                                       u"radaiFilaAbrir();"))
    r3, erro3 = _chamar(velho)
    checar(u"  (isca) com o nome interno igual ao publicado, a funcao chama a "
           u"si mesma e estoura -- a checagem discrimina",
           r3 is not None and r3.get("erro") == u"RangeError", erro3 or str(r3))


def teste_a_navegacao_livre_com_a_fila_rodando():
    secao(u"a navegacao fica livre com a fila rodando")
    import ast
    with io.open(_componentes.fonte("app/radai_watcher.py"),
                 encoding="utf-8") as f:
        arvore = ast.parse(f.read())
    nomes = set(n.name for n in ast.walk(arvore)
                if isinstance(n, ast.FunctionDef))
    checar(u"o portao que mandava toda tela para /lote saiu",
           u"montar_portao_da_fila" not in nomes)
    with io.open(_componentes.fonte("app/radai_batch.py"),
                 encoding="utf-8") as f:
        lote = f.read()
    checar(u"  e o aviso de «estação dedicada» do /lote saiu com ele",
           u'id="dedicada"' not in lote and u"dedicada=1" not in lote)
    checar(u"o vigia nao recusa ligar com o «Rodar agora» rodando (ele "
           u"espera a vez)", u"Espere ele terminar e ligue a fila depois"
           not in io.open(_componentes.fonte("app/radai_watcher.py"),
                          encoding="utf-8").read())


def main():
    print(u"test_fila_simulacao | a fila unica da estacao, do clique as "
          u"sequencias de quem conhece o app")
    testes = (teste_o_contrato_c1_em_python,
              teste_o_contrato_c1_pela_rota,
              teste_a_serie_que_roda_soma_a_pasta_de_copia,
              teste_o_limpar_pede_confirmacao_da_entrega_parcial,
              teste_o_clique_simples_e_a_copia_do_rtstruct,
              teste_a_copia_recusa_pasta_que_sincroniza,
              teste_limpar_no_meio_da_fila,
              teste_cancelar_e_limpar,
              teste_subir_e_descer_muda_a_ordem_do_trabalho,
              teste_o_dicombridge_enfileira_com_a_fila_rodando,
              teste_a_serie_do_vigia_termina_e_o_manual_vem_em_seguida,
              teste_o_cancelar_do_vigia_e_o_pausar_na_espera,
              teste_a_fila_do_vigia_na_barra,
              teste_duas_estacoes_na_mesma_pasta,
              teste_a_trava_de_processo_morto,
              teste_reabrir_com_a_fila_cheia,
              teste_onde_a_fila_mora,
              teste_a_fila_nao_grava_em_pasta_que_sincroniza,
              teste_reabrir_solta_a_trava_e_acha_pelo_acervo,
              teste_o_complemento_por_memoria,
              teste_o_cartao_do_vigia_conta_o_desfecho,
              teste_o_log_segue_depois_de_800_linhas,
              teste_a_barra_aberta_recolhida_e_o_dicombridge,
              teste_a_navegacao_livre_com_a_fila_rodando)
    todos = set(k for k, v in globals().items()
                if k.startswith("teste_") and callable(v))
    fora = sorted(todos - set(t.__name__ for t in testes))
    checar(u"todo teste deste arquivo esta registrado", not fora, ", ".join(fora))
    for t in testes:
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            checar(u"%s (excecao inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            try:
                _zerar()
            except Exception:
                pass
    falhas = [(n, d) for n, ok, d in _R if not ok]
    print(u"\n" + u"=" * 64)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_R)))
        for n, d in falhas:
            print(u"  - %s%s" % (n, ("  [%s]" % d) if d else u""))
    else:
        print(u"OK: %d checagens, todas passaram" % len(_R))
    print(u"=" * 64)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
