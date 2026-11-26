"""Índice local e avisos descartáveis do turno corrente do Vigia."""
from contextlib import closing, contextmanager
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

ErroIndice = sqlite3.Error


@contextmanager
def conectar(arquivo):
    with closing(sqlite3.connect(str(arquivo), timeout=6)) as db:
        with db:
            yield db


def atualizar_consulta(arquivo, series, remover=None):
    with conectar(arquivo) as db:
        db.execute("CREATE TABLE IF NOT EXISTS consulta(uid TEXT PRIMARY KEY, pasta TEXT, paciente TEXT)")
        if remover is None:
            db.execute("DELETE FROM consulta")
        else:
            db.executemany("DELETE FROM consulta WHERE uid=?", ((u,) for u in remover))
        db.executemany("INSERT OR REPLACE INTO consulta VALUES (?,?,?)",
                       ((uid, str(s.get("dir") or ""), str(s.get("pid") or "")) for uid, s in series.items()))


def consultar(arquivo, uid):
    if not arquivo.is_file():
        return "", ""
    with conectar(arquivo) as db:
        try:
            return db.execute("SELECT pasta,paciente FROM consulta WHERE uid=?", (uid,)).fetchone() or ("", "")
        except sqlite3.OperationalError:
            return "", ""


def chave(pasta):
    p = str(pasta)
    if p.startswith("\\\\?\\UNC\\"):
        p = "\\\\" + p[8:]
    elif p.startswith("\\\\?\\"):
        p = p[4:]
    return os.path.normcase(os.path.normpath(p))


def abaixo(pasta, raiz):
    try:
        return os.path.commonpath((pasta, raiz)) == raiz
    except ValueError:
        return False


def _json(d):
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False)


def invalidacoes(arquivo):
    if not arquivo.is_file():
        return [], 0
    with conectar(arquivo) as db:
        try:
            rows = list(db.execute("SELECT pasta,seq FROM invalidar_json"))
        except sqlite3.OperationalError:
            return [], 0
    return [p for p, _ in rows], max((seq for _, seq in rows), default=0)


def confirmar_json(arquivo, seq):
    if seq:
        with conectar(arquivo) as db:
            db.execute("DELETE FROM invalidar_json WHERE seq<=?", (seq,))


class Indice:
    def __init__(self, arquivo):
        self.arquivo = arquivo
        self.pronto = False

    def iniciar(self, cache, series):
        with conectar(self.arquivo) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS invalidar_json (seq INTEGER PRIMARY KEY AUTOINCREMENT, pasta TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS partes (pasta TEXT, uid TEXT, nome TEXT, dados TEXT,
                    PRIMARY KEY(pasta,uid));
                CREATE INDEX IF NOT EXISTS partes_uid ON partes(uid);
                CREATE TABLE IF NOT EXISTS datas (pasta TEXT, nome TEXT, data TEXT, PRIMARY KEY(pasta,nome));
                CREATE INDEX IF NOT EXISTS data_maxima ON datas(data);
                CREATE TABLE IF NOT EXISTS series (uid TEXT PRIMARY KEY, grupo TEXT, dados TEXT,
                    data TEXT, manual TEXT DEFAULT '', escolha TEXT DEFAULT '', espera INTEGER DEFAULT 0,
                    ate REAL, repetida INTEGER DEFAULT 0);
                CREATE INDEX IF NOT EXISTS series_grupo ON series(grupo);
                CREATE INDEX IF NOT EXISTS series_data ON series(data);
                CREATE INDEX IF NOT EXISTS series_espera ON series(espera);
                CREATE TABLE IF NOT EXISTS assinaturas(pasta TEXT PRIMARY KEY,mtime REAL,quantidade INTEGER);
                CREATE TABLE IF NOT EXISTS pastas_ordem (ordem INTEGER PRIMARY KEY, pasta TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS fora (uid TEXT PRIMARY KEY, classe TEXT, dados TEXT);
                CREATE INDEX IF NOT EXISTS fora_classe ON fora(classe);
                BEGIN IMMEDIATE;
                DELETE FROM assinaturas;
                DELETE FROM pastas_ordem;
                DELETE FROM fora;
                DELETE FROM partes;
                DELETE FROM datas;
                DELETE FROM series;
            """)
            for pasta, entrada in cache.items():
                partes = entrada.get("series")
                if partes is not None:
                    self._gravar_partes(db, pasta, partes)
                    if entrada.get("sig"):
                        db.execute("INSERT INTO assinaturas VALUES (?,?,?)", (chave(pasta), *entrada["sig"]))
                marcadores = entrada.get("marcadores")
                if marcadores:
                    pasta = chave(os.path.dirname(pasta))
                    db.executemany("INSERT INTO datas VALUES (?,?,?)",
                                   ((pasta, name, item[1]) for name, item in marcadores.items() if item[1]))
            for uid, s in series.items():
                self._resumo(db, uid, s)
        self.pronto = True

    @staticmethod
    def _gravar_partes(db, pasta, partes):
        if partes:
            db.execute("INSERT OR IGNORE INTO pastas_ordem(pasta) VALUES (?)", (chave(pasta),))
        db.executemany("INSERT INTO partes VALUES (?,?,?,?)",
                       ((chave(pasta), uid, pasta, _json(info)) for uid, info in partes.items()))

    @staticmethod
    def _resumo(db, uid, s):
        db.execute("INSERT INTO series(uid,grupo,dados,data) VALUES (?,?,?,?) ON CONFLICT(uid) "
                   "DO UPDATE SET grupo=excluded.grupo,dados=excluded.dados,data=excluded.data",
                   (uid, str(s.get("estudo") or s["dir"]), _json(s), s["date"]))

    def contexto(self, uids, grupos):
        """Só os estudos afetados. Inclui irmãos para a triagem sem reabrir a pasta deles."""
        with conectar(self.arquivo) as db:
            for uid in uids:
                row = db.execute("SELECT grupo FROM series WHERE uid=?", (uid,)).fetchone()
                if row:
                    grupos.add(row[0])
            return {u: (json.loads(s), manual, escolha)
                    for grupo in grupos for u, s, manual, escolha in
                    db.execute("SELECT uid,dados,manual,escolha FROM series WHERE grupo=?", (grupo,))}

    def partes_inalteradas(self, pasta, sig):
        with conectar(self.arquivo) as db:
            p = chave(pasta)
            if db.execute("SELECT mtime,quantidade FROM assinaturas WHERE pasta=?", (p,)).fetchone() != sig:
                return None
            return {u: json.loads(s) for u, s in db.execute("SELECT uid,dados FROM partes WHERE pasta=?", (p,))}

    def trocar(self, pastas, removidas, unir, finalizar):
        """Uma transação troca as partes antigas pelo que realmente foi lido."""
        atingidos, grupos, completos = set(), set(), {}
        with conectar(self.arquivo) as db:
            for p in removidas:
                # 'p' e seu subdiretório têm chaves contíguas na ordem binária.
                prefixo = chave(p).rstrip(os.sep) + os.sep
                limite = prefixo[:-1] + chr(ord(os.sep) + 1)
                filtro = "pasta=? OR (pasta>=? AND pasta<?)"
                args = (chave(p), prefixo, limite)
                atingidos.update(x[0] for x in db.execute("SELECT uid FROM partes WHERE "+filtro, args))
                db.execute("INSERT OR REPLACE INTO invalidar_json(pasta) SELECT DISTINCT pasta "
                           "FROM partes WHERE "+filtro, args)
                db.execute("DELETE FROM partes WHERE "+filtro, args)
                db.execute("DELETE FROM datas WHERE "+filtro, args)
                db.execute("DELETE FROM assinaturas WHERE "+filtro, args)
            for p, (sig, partes) in pastas.items():
                chave_p = chave(p)
                db.execute("INSERT OR REPLACE INTO invalidar_json(pasta) VALUES (?)", (chave_p,))
                atingidos.update(x[0] for x in db.execute("SELECT uid FROM partes WHERE pasta=?", (chave_p,)))
                db.execute("DELETE FROM partes WHERE pasta=?", (chave_p,))
                self._gravar_partes(db, p, partes)
                if sig:
                    db.execute("INSERT OR REPLACE INTO assinaturas VALUES (?,?,?)", (chave_p, *sig))
                else:
                    db.execute("DELETE FROM assinaturas WHERE pasta=?", (chave_p,))
                atingidos.update(partes)
            for uid in atingidos:
                anterior = db.execute("SELECT grupo FROM series WHERE uid=?", (uid,)).fetchone()
                if anterior:
                    grupos.add(anterior[0])
                bruto = {}
                for pasta, dados in db.execute("SELECT nome,dados FROM partes JOIN pastas_ordem USING(pasta) WHERE uid=? ORDER BY ordem", (uid,)):
                    unir(bruto, pasta, {uid: json.loads(dados)})
                completos.update(finalizar(bruto))
                if uid in completos:
                    self._resumo(db, uid, completos[uid])
                else:
                    db.execute("DELETE FROM series WHERE uid=?", (uid,))
        return atingidos, grupos, completos

    def fila(self, dados):
        with conectar(self.arquivo) as db:
            db.executemany("UPDATE series SET manual=?,escolha=?,espera=?,ate=?,repetida=? WHERE uid=?",
                           ((v.get("manual", ""), v.get("escolha", ""), v.get("espera", 0),
                             v.get("ate"), v.get("repetida", 0), uid) for uid, v in dados.items()))

    def aguardar(self, uid):
        with conectar(self.arquivo) as db:
            db.execute("UPDATE series SET espera=3 WHERE uid=?", (uid,))

    def temporais(self):
        with conectar(self.arquivo) as db:
            return {r[0] for r in db.execute("SELECT uid FROM series WHERE espera>0")}

    def vencer(self, limite):
        with conectar(self.arquivo) as db:
            vencidas = list(db.execute("SELECT uid,grupo FROM series WHERE data<?", (limite,)))
            db.execute("DELETE FROM series WHERE data<?", (limite,))
            return vencidas

    def marcador(self, pasta, nome, data):
        with conectar(self.arquivo) as db:
            if data:
                db.execute("INSERT OR REPLACE INTO datas VALUES (?,?,?)", (chave(pasta), nome, data))
            else:
                db.execute("DELETE FROM datas WHERE pasta=? AND nome=?", (chave(pasta), nome))

    def data(self):
        with conectar(self.arquivo) as db:
            valor = db.execute("SELECT MAX(data) FROM datas").fetchone()[0]
            return [valor] if valor else []

    def status(self):
        with conectar(self.arquivo) as db:
            n, man, fora, trans, ad, ate = db.execute("""
                SELECT count(*), sum(manual!=''), sum(escolha=''), sum(espera=1), sum(espera=2),
                       min(CASE WHEN espera=2 THEN ate END) FROM series""").fetchone()
            return dict(series_total=n, fila_manual=man or 0, nao_simulacao=fora or 0,
                        em_transito=trans or 0, adiadas=ad or 0, volta_das_adiadas=ate)

    def repetidas(self, fila):
        with conectar(self.arquivo) as db:
            return {r[0] for r in db.execute("SELECT uid FROM series WHERE repetida=1")}.intersection(
                s["uid"] for s in fila)

    def atualizar_fora(self, descartes, remover=None):
        with conectar(self.arquivo) as db:
            if remover is None:
                db.execute("DELETE FROM fora")
            else:
                db.executemany("DELETE FROM fora WHERE uid=?", ((u,) for u in remover))
            for classe, itens in zip(("puladas", "nao_contornaveis", "em_espera"), descartes):
                db.executemany("INSERT OR REPLACE INTO fora VALUES (?,?,?)",
                               ((i["uid"], classe, _json(i)) for i in itens))
            contagens = dict(puladas=0, nao_contornaveis=0, em_espera=0)
            contagens.update(db.execute("SELECT classe,count(*) FROM fora GROUP BY classe"))
            return contagens

    def fora(self, classe):
        pos = 0
        while True:
            with conectar(self.arquivo) as db:
                pagina = list(db.execute("SELECT rowid,dados FROM fora WHERE classe=? AND rowid>? "
                                         "ORDER BY rowid LIMIT 128", (classe, pos)))
            if not pagina:
                return
            for pos, dados in pagina:
                yield json.loads(dados)


class Avisos:
    LIMITE = 8192
    RETENTATIVA = 60
    PRAZO_ABRIR = 3

    def __init__(self, raizes, ignorar, acordar, quiet, log):
        self.raizes = tuple(raizes)
        self.ignorar = ignorar
        self.acordar = acordar
        self.quiet = quiet
        self.log = log
        self.trava = threading.RLock()
        self.ativos = {}
        self.modos = {}
        self.pendentes = {}
        self.marcas = {}
        self.sem_cobertura = set()
        self.no_intervalo = set()
        self.ressincronizar = set()
        self.fechado = False

    def abrir(self):
        sinais = [(r, self._armar(r, primeira=True)) for r in self.raizes]
        prazo = time.monotonic()+self.PRAZO_ABRIR
        for raiz, sinal in sinais:
            if sinal:
                sinal.wait(max(0, prazo-time.monotonic()))
        with self.trava:
            for raiz, _ in sinais:
                if self.modos.get(raiz, ("",))[0] == "abrindo":
                    self.sem_cobertura.add(raiz)
                    self.log("Vigia: a inscrição ainda não confirmou; a pasta será reconciliada.")

    def _armar(self, raiz, primeira=False):
        from radai_avisos_windows import inscrever
        sinal = threading.Event()
        token = object()
        with self.trava:
            if self.fechado:
                return
            velho = self.ativos.pop(raiz, None)
            self.modos[raiz] = ("abrindo", time.monotonic(), token)
        if velho:
            velho.fechar()

        def receber(estado, eventos):
            with self.trava:
                if self.fechado or self.modos[raiz][2] is not token:
                    return
                if estado == "pronto":
                    self.modos[raiz] = (estado, 0, token)
                    if not primeira or raiz in self.sem_cobertura:
                        self.sem_cobertura.discard(raiz)
                        self.ressincronizar.add(raiz)
                elif estado == "mudou":
                    acordar = False
                    for acao, relativo in eventos:
                        partes = Path(relativo).parts
                        if not partes or os.path.isabs(relativo) or ".." in partes:
                            continue
                        nome = partes[-1]
                        if len(partes) >= 2 and partes[-2].lower() == "_radai":
                            uid, _, tipo = nome.rpartition(".")[0].rpartition(".")
                            if nome.endswith(".json") and uid and tipo in ("done", "fail", "fila"):
                                p = os.path.join(raiz, *partes[:-2])
                                self.marcas[(p, uid, tipo)] = None
                        elif not any(self.ignorar(x) for x in partes):
                            p = os.path.join(raiz, *partes)
                            # Ação 3 pode ser escrita de um arquivo recém-criado.
                            anterior = self.pendentes.get(p)
                            if anterior and acao == 3:
                                acao = anterior[0]
                            self.pendentes[p] = (acao, time.monotonic() + self.quiet)
                            acordar = True
                        if len(self.pendentes) + len(self.marcas) > self.LIMITE:
                            self.pendentes.clear()
                            self.marcas.clear()
                            self.ressincronizar.update(self.raizes)
                            break
                    if not acordar and not self.ressincronizar:
                        return  # um marcador não acorda a estação nem abre imagens
                else:
                    self.modos[raiz] = (estado, time.monotonic()+self.RETENTATIVA, token)
                    self.log("Vigia: avisos da pasta %s (%s). Usando a varredura de segurança." % (raiz, estado))
                sinal.set()
                self.acordar.set()
        try:
            assinatura = inscrever(raiz, receber)
        except (OSError, RuntimeError, ImportError):
            receber("sem_suporte", ())
            return
        with self.trava:
            fechado = self.fechado
            if not fechado:
                self.ativos[raiz] = assinatura
        if fechado:
            assinatura.fechar()
        return sinal

    def reconciliar(self):
        with self.trava:
            self.no_intervalo.update(self.raizes)

    def retirar(self, agora, periodo):
        with self.trava:
            reabrir = [p for p,(m,quando,_) in self.modos.items()
                       if m in ("overflow","desconectado") and agora >= quando]
        for p in reabrir:
            self._armar(p)
        with self.trava:
            recuos = {p for p,(m,_,_) in self.modos.items() if m == "sem_suporte"} if periodo else set()
            if periodo:
                recuos.update(self.no_intervalo)
                self.no_intervalo.clear()
            varrer = self.ressincronizar | recuos
            self.ressincronizar = set()
            # Um segundo arquivo reinicia QUIET para a série inteira. Uma pasta
            # recém-movida também espera os últimos avisos de seus descendentes.
            ultimos = {}
            for p, (_, quando) in self.pendentes.items():
                pai = os.path.dirname(p)
                while pai and pai not in self.raizes and ultimos.get(pai, 0) < quando:
                    ultimos[pai] = quando
                    pai = os.path.dirname(pai)
            prontos = {p:a for p,(a,quando) in self.pendentes.items()
                       if agora >= max(quando, ultimos.get(os.path.dirname(p), 0), ultimos.get(p, 0))}
            for p in prontos:
                self.pendentes.pop(p)
            marcas = list(self.marcas) if periodo or prontos or varrer else []
            for marca in marcas:
                self.marcas.pop(marca)
            return varrer, prontos, marcas

    def sem_suporte(self, raiz):
        with self.trava:
            return any(chave(raiz) == chave(r) and modo == "sem_suporte" for r,(modo,_,_) in self.modos.items())

    def aguarda(self, dirs):
        with self.trava:
            return any(abaixo(chave(p), chave(d)) or abaixo(chave(d), chave(p))
                       for p in self.pendentes for d in dirs)

    def esperar(self, segundos):
        with self.trava:
            agora = time.monotonic()
            prazos = [quando for _,quando in self.pendentes.values() if quando > agora]
            prazos.extend(quando for m,quando,_ in self.modos.values() if m in ("overflow","desconectado"))
        prazo = min([segundos]+[max(0, v-time.monotonic()) for v in prazos])
        self.acordar.wait(prazo)
        self.acordar.clear()

    def solicitar_fechamento(self):
        with self.trava:
            self.fechado = True
            todas = list(self.ativos.values())
            self.marcas.clear()
            self.pendentes.clear()
        for a in todas:
            if hasattr(a, "solicitar_fechamento"):
                a.solicitar_fechamento()

    def fechar(self):
        self.solicitar_fechamento()
        with self.trava:
            todas = list(self.ativos.values())
            self.ativos.clear()
        for a in todas:
            a.fechar()
