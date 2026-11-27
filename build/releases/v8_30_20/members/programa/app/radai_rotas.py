"""Livro local de tentativas de inferência. Só é aberto quando há trabalho."""
import contextlib
import ctypes
import functools
import os
import sqlite3
import time
import threading
import uuid
import zipfile
from pathlib import Path

CONDENADAS = ("oom_gpu", "oom_ram", "filho", "trava", "timeout", "motor")
ESQUEMA = """CREATE TABLE IF NOT EXISTS rota (
 id TEXT PRIMARY KEY, uid TEXT NOT NULL, task TEXT NOT NULL, degrau TEXT NOT NULL,
 hw TEXT NOT NULL, driver TEXT NOT NULL, modo TEXT NOT NULL, versao TEXT NOT NULL,
 inicio REAL NOT NULL, fim REAL, motivo TEXT NOT NULL, boot TEXT, pid INTEGER,
 processo TEXT, ram INTEGER, vram INTEGER, na_placa INTEGER, na_maquina INTEGER);
CREATE INDEX IF NOT EXISTS rota_caso ON rota(uid,task);
CREATE INDEX IF NOT EXISTS rota_risco ON rota(task,hw,driver,modo,inicio);
CREATE INDEX IF NOT EXISTS rota_ativa ON rota(motivo);"""


class PressaoDeMemoria:
    """Histerese atualizada por quem já está trabalhando, sem thread ou timer."""
    def __init__(self):
        self.inicio = None
        self.bloqueada = False
        self.lock = threading.Lock()

    def avaliar(self, memoria, agora=None):
        if not memoria or not (memoria.get("total_mb") or memoria.get("commit_total_mb")):
            return False
        agora = time.monotonic() if agora is None else agora
        total = memoria.get("commit_total_mb") or 0
        uso = 1 - (memoria.get("commit_livre_mb", 0) / total) if total else 0
        livre = memoria.get("livre_mb")
        with self.lock:
            if livre is not None and livre < 2560:
                self.bloqueada = True
            if uso > .92:
                self.inicio = agora if self.inicio is None else self.inicio
                if agora - self.inicio >= 5:
                    self.bloqueada = True
            else:
                self.inicio = None
                if uso < .80 and livre is not None and livre >= 2560:
                    self.bloqueada = False
            return self.bloqueada


pressao = PressaoDeMemoria()


def precarga_permitida():
    # Somente os contadores do kernel. Nenhuma enumeração de discos/pagefiles.
    from radai_memory_history import _sample
    try:
        m = _sample()
    except (OSError, AttributeError):
        return True
    return not pressao.avaliar({"total_mb": m.get("physical_total_mib"),
                                "livre_mb": m.get("available_min_mib"),
                                "commit_total_mb": m.get("commit_limit_mib"),
                                "commit_livre_mb": m.get("commit_free_min_mib") or 0})


class SemRota(RuntimeError):
    pass


class Ocupada(RuntimeError):
    pass


class AguardarSozinha(Ocupada):
    pass


@functools.lru_cache(maxsize=1)
def _boot():
    try:
        if os.name == "nt":
            dados = ctypes.create_string_buffer(64)
            if ctypes.windll.ntdll.NtQuerySystemInformation(90, dados, len(dados), None) == 0:
                return uuid.UUID(bytes_le=dados.raw[:16]).hex
        else:
            return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except (OSError, ValueError, AttributeError):
        pass
    return ""


def _processo(pid):
    """Token de criação, '' se saiu, None se Windows recusou a consulta."""
    if os.name != "nt":
        try:
            return Path("/proc/%d/stat" % pid).read_text().rsplit(")", 1)[1].split()[19]
        except FileNotFoundError:
            return ""
        except (OSError, IndexError):
            return None
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.GetProcessTimes.argtypes = [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [w.HANDLE]
    h = kernel.OpenProcess(0x1000, False, pid)
    if not h:
        return "" if ctypes.get_last_error() == 87 else None
    try:
        tempos = [w.FILETIME() for _ in range(4)]
        if kernel.GetProcessTimes(h, *(ctypes.byref(x) for x in tempos)):
            return str((tempos[0].dwHighDateTime << 32) | tempos[0].dwLowDateTime)
        return None
    finally:
        kernel.CloseHandle(h)


def arquivo():
    import radai_archive
    import radai_queue_state
    pasta = radai_queue_state.pasta_da_fila()
    if radai_archive._e_rede(pasta) or radai_queue_state._sincroniza(pasta):
        # O livro é próprio da estação inclusive quando a fila é compartilhada.
        pasta = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LocalSuite" / "fila"
        if radai_archive._e_rede(str(pasta)) or radai_queue_state._sincroniza(str(pasta)):
            raise OSError("A estação precisa de uma pasta local para o livro de rotas.")
    return Path(pasta) / "rotas.sqlite3"


def _hardware(plano):
    if plano["modo"] == "cpu":
        return "CPU"
    return str(plano.get("uuid") or "%s/%s" % (plano["indice"], plano.get("placa", "?")))


def caminhos(planos, piloto=None):
    """Cada item corresponde a um modo físico distinto. CPU repetida não é um recuo."""
    saida = []
    if piloto is not None:
        planos = sorted(planos, key=lambda p: p.get("indice") != piloto)
        if planos and planos[0].get("indice") == piloto and planos[0]["modo"] != "cpu":
            saida.append(dict(planos[0], degrau="D0"))
    for i, plano in enumerate(planos):
        if plano["modo"] == "cpu":
            continue
        if plano["modo"] == "gpu":
            saida.append(dict(plano, degrau="D3" if i else "D1"))
        saida.append(dict(plano, degrau="D3" if i else "D2", modo="gpu_resultado_na_cpu"))
    saida.append(dict(modo="cpu", degrau="D4", indice=None, capacidade=None,
                      motivo="CPU, mesma rede e resolução"))
    return saida


class Livro:
    def __init__(self, caminho, versao, boot=None, processo=None, agora=time.time):
        self.caminho = Path(caminho)
        self.versao = versao
        self.boot = _boot() if boot is None else boot
        self.processo = processo or _processo
        self.agora = agora

    @contextlib.contextmanager
    def transacao(self):
        self.caminho.parent.mkdir(exist_ok=True, parents=True)
        with contextlib.closing(sqlite3.connect(str(self.caminho), timeout=8)) as db:
            db.row_factory = sqlite3.Row
            db.executescript(ESQUEMA)
            db.execute("BEGIN IMMEDIATE")
            with db:
                yield db

    def recuperar(self, db):
        for row in db.execute("SELECT id,boot,pid,processo FROM rota WHERE fim IS NULL").fetchall():
            if row["boot"] and self.boot and row["boot"] != self.boot:
                motivo = "reinicio"
            else:
                atual = self.processo(row["pid"])
                if atual is None or (atual and (not row["processo"] or row["processo"] == atual)):
                    continue
                motivo = "motor" if self.boot and row["boot"] == self.boot else "interrompido"
            db.execute("UPDATE rota SET fim=?,motivo=? WHERE id=?", (self.agora(), motivo, row["id"]))

    def admitir(self, uid, task, planos, memoria, ram):
        with self.transacao() as db:
            self.recuperar(db)
            vivas = db.execute("SELECT uid,task,hw,ram,vram FROM rota WHERE fim IS NULL").fetchall()
            if any(r["uid"] == uid and r["task"] == task for r in vivas):
                raise Ocupada("A tarefa já tem uma execução nesta estação.")
            if memoria.get("commit_livre_mb") and ram > memoria["commit_livre_mb"]:
                raise Ocupada("Commit livre insuficiente para inferência e acabamento.")
            if pressao.avaliar(memoria):
                raise Ocupada("A estação está sob pressão de memória.")
            if vivas:
                reservada = sum(r["ram"] or 0 for r in vivas)
                disponivel = min(memoria.get("livre_mb", 0) - 2560,
                                 memoria.get("commit_livre_mb", 0))
                if not ram or not memoria.get("commit_total_mb") or (
                    memoria.get("commit_livre_mb", 0) / memoria["commit_total_mb"] < .08
                ) or ram + reservada > disponivel:
                    raise Ocupada("RAM física ou commit insuficiente para admitir outra tarefa.")
            bloqueadas = set()
            for r in db.execute("SELECT hw,driver,modo,degrau,motivo FROM rota WHERE uid=? AND task=?", (uid, task)):
                if r["motivo"] in CONDENADAS:
                    bloqueadas.add((r["hw"], r["driver"], r["modo"], r["degrau"] == "D0"))
            ocupacao = False
            learned_after = _inicio_do_aprendizado(db, self.agora())
            for p in planos:
                hw, driver, modo = _hardware(p), str(p.get("driver") or ""), p["modo"]
                if (hw, driver, modo, p["degrau"] == "D0") in bloqueadas:
                    continue
                if modo != "cpu" and driver:
                    aprendidas = db.execute(
                        "SELECT count(DISTINCT uid) FROM rota WHERE task=? AND hw=? AND driver=? "
                        "AND modo=? AND (degrau='D0')=? AND motivo IN ('oom_ram','oom_gpu') AND inicio>=?",
                        (task, hw, driver, modo, int(p["degrau"] == "D0"), learned_after)).fetchone()[0]
                    if aprendidas >= (1 if p["degrau"] == "D0" else 2):
                        continue
                if p["degrau"] == "D1" and vivas and (hw, driver, modo, True) in bloqueadas:
                    raise AguardarSozinha("Retomada exclusiva após liberar a outra execução.")
                na_placa = [r for r in vivas if r["hw"] == hw]
                # No piloto conservador uma placa tem sempre um único dono.
                if na_placa or (modo == "cpu" and vivas):
                    ocupacao = True
                    continue
                precisa = int(p.get("precisa_tudo_mb" if modo == "gpu" else "precisa_rede_mb") or 0)
                margem = int(p.get("margem_mb" if modo == "gpu" else "margem_rede_mb") or 0)
                if modo != "cpu" and precisa + margem > p.get("vram_livre_mb", 0):
                    ocupacao = True
                    continue
                ident = uuid.uuid4().hex
                pid = os.getpid()
                db.execute("INSERT INTO rota VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (ident, uid, task, p["degrau"], hw, driver, modo, self.versao,
                            self.agora(), None, "rodando", self.boot, pid, self.processo(pid),
                            ram, precisa, len(na_placa)+1, len(vivas)+1))
                return ident, p
            if ocupacao:
                raise Ocupada("Recursos da estação reservados por outra tarefa.")
            raise SemRota("As rotas de recurso disponíveis para esta tarefa já falharam.")

    def terminar(self, ident, motivo):
        with self.transacao() as db:
            db.execute("UPDATE rota SET motivo=?,fim=? WHERE id=? AND fim IS NULL",
                       (motivo, self.agora(), ident))

    def retomar(self, uid):
        if not uid or not self.caminho.is_file():
            return False
        with self.transacao() as db:
            self.recuperar(db)
            row = db.execute("SELECT motivo FROM rota WHERE uid=? ORDER BY inicio DESC LIMIT 1", (uid,)).fetchone()
            return bool(row and row["motivo"] in ("motor", "reinicio", "interrompido", "concluida"))

def pasta_de_retomada(uid):
    import hashlib
    return arquivo().parent / "execucoes" / hashlib.sha256(uid.encode("utf-8")).hexdigest()


def caminho_do_mapa(uid, assinatura):
    if len(assinatura) != 64 or any(c not in "0123456789abcdef" for c in assinatura):
        raise ValueError("assinatura inválida")
    return pasta_de_retomada(uid) / (assinatura + ".npz")


def ler_mapa(caminho, forma):
    import numpy as np
    if not caminho.is_file():
        return None
    try:
        with caminho.open("rb") as dados, np.load(dados, allow_pickle=False) as z:
            arr = z["arr"]
            if arr.shape != tuple(forma) or arr.dtype.kind not in "iu":
                return None
            return arr, bool(z["vazio"].item())
    except (ValueError, KeyError, OSError, EOFError, zipfile.BadZipFile):
        return None


def guardar_mapa(caminho, arr, vazio):
    import numpy as np
    import shutil
    import tempfile
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(caminho.parent).free < arr.nbytes + 1024**3:
        return False
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=caminho.parent, delete=False, suffix=".tmp") as f:
            temp = f.name
            # ZIP sem compressão. NumPy escreve a matriz em blocos e o ZIP preserva CRC.
            np.savez(f, arr=arr, vazio=np.bool_(vazio))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, caminho)
        return True
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


def encerrar_mapas(uid):
    import shutil
    if uid:
        p = pasta_de_retomada(uid)
        raiz = (arquivo().parent.resolve() / "execucoes")
        resolvido = p.resolve()
        if resolvido.parent == raiz and resolvido.name == p.name and p.is_dir():
            shutil.rmtree(resolvido)

def descartar_apos_entrega(uid, log=None):
    try:
        encerrar_mapas(uid)
    except OSError as exc:
        if log:
            log("Mapas locais da execução: limpeza adiada (%s)." % type(exc).__name__)


def ultimo_recurso(uid):
    try:
        p = arquivo()
        if not p.is_file():
            return {}
        with contextlib.closing(sqlite3.connect(str(p), timeout=2)) as db:
            row = db.execute("SELECT degrau,motivo FROM rota WHERE uid=? ORDER BY inicio DESC LIMIT 1",
                             (uid,)).fetchone()
            return {"degrau": row[0], "resultado_recurso": row[1]} if row else {}
    except (OSError, sqlite3.Error):
        return {}


def diagnostico(esquecer=False):
    """Resumo solicitado pelo operador, sem UIDs, caminhos ou informações do paciente."""
    p = arquivo()
    if not p.is_file():
        return []
    with Livro(p, "").transacao() as db:
        if esquecer:
            # Esquecer o aprendizado não libera rotas já condenadas para uma série.
            db.execute("CREATE TABLE IF NOT EXISTS aprendizado(corte REAL NOT NULL)")
            db.execute("DELETE FROM aprendizado")
            db.execute("INSERT INTO aprendizado VALUES(?)", (time.time(),))
        return [dict(r) for r in db.execute(
            "SELECT task,hw,driver,modo,degrau,count(DISTINCT uid) AS series FROM rota "
            "WHERE motivo IN ('oom_gpu','oom_ram') AND inicio>=? AND driver<>'' "
            "GROUP BY task,hw,driver,modo,degrau ORDER BY task,hw", (_inicio_do_aprendizado(db,time.time()),))]


def _inicio_do_aprendizado(db, agora):
    existe = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='aprendizado'").fetchone()
    corte = db.execute("SELECT max(corte) FROM aprendizado").fetchone()[0] if existe else None
    return max(agora - 30*86400, corte or 0)


