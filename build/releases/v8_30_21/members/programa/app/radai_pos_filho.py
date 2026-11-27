"""Acabamento em processo descartável. Somente as matrizes são mapeadas em disco."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

_ATIVOS = {}
_TRAVA = threading.Lock()


def cancelar(uid=None):
    with _TRAVA:
        processos = [r for caso, r in _ATIVOS.items() if uid is None or caso == uid]
        for processo, sinal in processos:
            sinal.set()
            if processo.poll() is None:
                processo.kill()
        return bool(processos)

PREFIXO = "LOCAL_SUITE_POS "
ATRIBUTOS = ("meta_do_full", "rois_do_study", "gravados", "tamanhos_publicados")


class TransporteIndisponivel(Exception):
    pass


class Mapas:
    def __init__(self, pasta):
        self.pasta = Path(pasta)
        self.matrizes = {}
        self.donos = {}
        self.bytes = 0

    def preparar(self, valor):
        import numpy as np
        import engine
        import radai_geom
        import radai_hnlnl
        import radai_motores_full
        if isinstance(valor, np.ndarray):
            if valor.dtype.hasobject:
                raise TransporteIndisponivel("matriz de objetos")
            key = id(valor)
            if key not in self.matrizes:
                self.matrizes[key] = valor
                self.bytes += valor.nbytes
            return ["matriz", str(key)]
        if isinstance(valor, np.generic):
            return self.preparar(valor.item())
        if type(valor) is engine.MasksCruas:
            self.donos[id(valor)] = valor
            return ["rotulos", str(id(valor)), self.preparar(valor._arr), valor._nomes,
                    sorted(valor._consultadas), self.preparar(valor._caixas)]
        if type(valor) is radai_geom.Grade:
            return ["grade", valor.spacing, valor.sentido]
        if isinstance(valor,slice):
            return ["slice", valor.start, valor.stop, valor.step]
        if type(valor) in (dict, radai_hnlnl.NiveisDaSerie, radai_motores_full.Extras):
            # O mapa de níveis mantém seus metadados (ilhas, extensão e grade) junto dos itens.
            extra = self.preparar(vars(valor)) if type(valor) is not dict else None
            return [type(valor).__name__, [(self.preparar(k), self.preparar(v)) for k,v in valor.items()], extra]
        if type(valor) in (list,tuple,set,frozenset):
            return [type(valor).__name__, [self.preparar(v) for v in valor]]
        if isinstance(valor,Path):
            return ["path", str(valor)]
        if valor is None or type(valor) in (str,int,float,bool):
            return valor
        raise TransporteIndisponivel(type(valor).__name__)

    def gravar(self):
        import numpy as np
        if self.bytes + 1024**3 > shutil.disk_usage(self.pasta).free:
            raise TransporteIndisponivel("espaço local para as grades")
        for identidade, matriz in self.matrizes.items():
            np.save(str(self.pasta / ("%d.npy"%identidade)), matriz, allow_pickle=False)

    def ler(self, desc):
        if not isinstance(desc, list):
            return desc
        tipo = desc[0]
        if tipo == "matriz":
            import numpy as np
            if not desc[1].isdigit():
                raise ValueError("identificador inválido")
            if desc[1] not in self.matrizes:
                # Escritas, quando necessárias, existem só no processo de acabamento.
                self.matrizes[desc[1]] = np.load(str(self.pasta / (desc[1]+".npy")), mmap_mode="c", allow_pickle=False)
            return self.matrizes[desc[1]]
        if tipo == "rotulos":
            import engine
            obj = engine.MasksCruas.__new__(engine.MasksCruas)
            obj._arr, obj._nomes = self.ler(desc[2]), desc[3]
            obj._consultadas, obj._caixas = set(desc[4]), self.ler(desc[5])
            self.donos[desc[1]] = obj
            return obj
        if tipo == "grade":
            from radai_geom import Grade
            return Grade(desc[1],desc[2])
        if tipo == "slice":
            return slice(*desc[1:])
        if tipo == "path":
            return Path(desc[1])
        if tipo in ("dict", "NiveisDaSerie", "Extras"):
            from radai_hnlnl import NiveisDaSerie
            from radai_motores_full import Extras
            obj={"dict":dict,"NiveisDaSerie":NiveisDaSerie,"Extras":Extras}[tipo]()
            obj.update((self.ler(k),self.ler(v)) for k,v in desc[1])
            if desc[2] is not None:
                vars(obj).update(self.ler(desc[2]))
            return obj
        formas={"list":list,"tuple":tuple,"set":set,"frozenset":frozenset}
        return formas[tipo](self.ler(v) for v in desc[1])


def _resumir(dado):
    """A saída pela tubulação carrega só metadados, nunca máscaras ou pixels."""
    if isinstance(dado, (tuple,set,frozenset)):
        return list(dado)
    if isinstance(dado,Path):
        return str(dado)
    import numpy as np
    if isinstance(dado,np.generic):
        return dado.item()
    raise TypeError(type(dado).__name__)


def no_executor_da_serie(fn):
    from functools import wraps
    from inspect import signature
    @wraps(fn)
    def despachar(saida, cruas, *args, **kwargs):
        uid = getattr(saida, "uid_execucao", None)
        if uid is None:
            return fn(saida, cruas, *args, **kwargs)
        if args:
            pedido = signature(fn).bind(saida, cruas, *args, **kwargs).arguments
            kwargs = {k:v for k,v in pedido.items() if k not in ("self", "cruas")}
        return executar(saida, cruas, uid_execucao=uid, _local=fn.__get__(saida), **kwargs)
    return despachar


def executar(saida, cruas, uid_execucao=None, _local=None, **kwargs):
    import engine
    import radai_cache_tasks as cache
    local = _local or saida.full_e_oar
    if (getattr(saida, "engine", None) is not engine or getattr(saida, "devolver_mascaras", False)
            or getattr(saida.full_e_oar, "__module__", "") != "radai_output"):
        return local(cruas, **kwargs)
    if not cache.conferir_pasta(tempfile.gettempdir())[0]:
        return local(cruas, **kwargs)
    with tempfile.TemporaryDirectory(prefix="suite_pos_") as pasta:
        mapas=Mapas(pasta)
        estado=cache._MOTORES.get()
        # A referência do cache do motor corresponde à própria série do stage.
        dados=dict(stage=saida.stage, destino=saida.destino, nome=saida.rs_name,
                   versao=saida.versao, tasks=list(saida.tasks), suavizar=saida.suavizar_mm,
                   modalidade=saida.modalidade, cache=cache.armado(),
                   motores={k:v for k,v in (estado or {}).items() if k!="ref"} if estado else None)
        try:
            dados.update(cruas=mapas.preparar(cruas), argumentos=mapas.preparar(kwargs),
                         grade=mapas.preparar(saida._grade))
            mapas.gravar()
            manifesto=Path(pasta)/"pedido.json"
            manifesto.write_text(json.dumps(dados,ensure_ascii=True),encoding="utf-8")
        except (OSError, TransporteIndisponivel) as exc:
            saida.log("Acabamento no processo atual (%s)." % exc)
            return local(cruas, **kwargs)
        saida.log("Acabamento em processo separado, %.1f MiB de mapas locais." % (mapas.bytes/1048576))
        err=Path(pasta)/"erro.txt"
        import radai_dedicado
        dedicado = "1" if radai_dedicado.sinalizacao()[0] else "0"
        with err.open("wb") as erros, subprocess.Popen(
            [sys.executable,"-B",str(Path(__file__).resolve()),str(manifesto)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=erros,text=True,
            encoding="utf-8",errors="replace",creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
            env=dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8",
                     RADAI_INFERENCIA_FILHA_DEDICADA=dedicado)) as filho:
            resultado=None
            cancelamento = threading.Event()
            if uid_execucao:
                with _TRAVA:
                    _ATIVOS[uid_execucao] = (filho, cancelamento)
            try:
                for linha in filho.stdout:
                    if not linha.startswith(PREFIXO):
                        saida.log(linha.rstrip())
                        continue
                    tipo,valor=json.loads(linha[len(PREFIXO):])
                    if tipo=="log":
                        saida.log(valor)
                    elif tipo=="tarefa":
                        saida.informar_tarefa(*valor)
                    elif tipo=="entregar":
                        origem,alvo=valor
                        import radai_sets
                        alvos={os.path.abspath(saida._alvo(x["infixo"])) for x in radai_sets.POR_COD.values()}
                        if os.path.abspath(alvo) not in alvos:
                            raise ValueError("Destino do RTSTRUCT fora desta entrega.")
                        saida._gravar_arquivo(origem,alvo)
                        filho.stdin.write("ok\n")
                        filho.stdin.flush()
                    elif tipo=="pronto":
                        resultado=valor
                    elif tipo=="falha":
                        if valor[0]=="MemoryError":
                            raise MemoryError(valor[1])
                        raise RuntimeError("Acabamento: %s: %s" % tuple(valor))
                rc=filho.wait()
            finally:
                with _TRAVA:
                    if uid_execucao and _ATIVOS.get(uid_execucao, (None,))[0] is filho:
                        del _ATIVOS[uid_execucao]
                if filho.poll() is None:
                    filho.kill()
                    filho.wait()
            if cancelamento.is_set():
                raise engine.Cancelado("Acabamento interrompido pelo operador.")
            if rc or resultado is None:
                detalhe=err.read_text(encoding="utf-8",errors="replace")[-800:]
                raise RuntimeError("O processo de acabamento terminou sem confirmar a entrega (%d). %s"%(rc,detalhe))
        for k,v in resultado["atributos"].items():
            setattr(saida,k,v)
        saida.rotulos_para_cache=set()
        for key,campos in resultado["mapas"].items():
            dono=mapas.donos.get(int(key))
            if dono is not None:
                dono._consultadas.update(campos[0])
                saida.rotulos_para_cache.update((id(dono),k) for k in campos[1])
        if estado is not None:
            estado["usados"].update(resultado["usados"])
        return resultado["entrega"]


def _filho(manifesto):
    import engine
    import radai_output
    import radai_cache_tasks as cache
    import radai_job
    aviso_job = radai_job.armar_motor()
    def enviar(tipo,valor):
        print(PREFIXO+json.dumps([tipo,valor],default=_resumir,ensure_ascii=True),flush=True)
    def copiar(origem,alvo):
        enviar("entregar",(str(origem),str(alvo)))
        if sys.stdin.readline().strip()!="ok":
            raise RuntimeError("O dono da entrega encerrou.")
    req=json.loads(manifesto.read_text(encoding="utf-8"))
    mapas=Mapas(manifesto.parent)
    saida=radai_output.Saida(engine, req["stage"],req["destino"], req["nome"],
            tasks=req["tasks"],versao=req["versao"],suavizar_mm=req["suavizar"],
            modalidade=req["modalidade"], grade=mapas.ler(req["grade"]),
            log=lambda m: enviar("log",m),copiar=copiar)
    saida.ao_progresso = lambda nome, estado: enviar("tarefa", (nome, estado))
    if aviso_job:
        saida.log(aviso_job)
    estado=req["motores"]
    if estado is not None:
        estado["ref"]=None
        cache._MOTORES.set(estado)
        cache.armar(req["cache"])
        if req["cache"] or estado["apenas_pos"]:
            saida.serie_lida()
            cache.volume_dos_motores(getattr(saida,"_img_lida",None))
    entrega=saida.full_e_oar(mapas.ler(req["cruas"]), **mapas.ler(req["argumentos"]))
    destinos=getattr(saida,"rotulos_para_cache",())
    lidos={k:[sorted(v._consultadas), sorted(n for i,n in destinos if i==id(v))]
           for k,v in mapas.donos.items()}
    atributos={k:getattr(saida,k) for k in ATRIBUTOS if hasattr(saida,k)}
    enviar("pronto",dict(entrega=entrega,mapas=lidos,atributos=atributos,usados=cache.motores_usados()))


if __name__=="__main__":
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    try:
        _filho(Path(sys.argv[1]))
    except Exception as exc:
        print(PREFIXO+json.dumps(["falha",[type(exc).__name__,str(exc)]],ensure_ascii=True),flush=True)
        sys.exit(1)

