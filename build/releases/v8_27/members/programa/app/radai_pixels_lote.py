"""Pré-carga local dos pixels que o visor do Rodar Agora efetivamente apresenta."""
import atexit
import os
import shutil
import tempfile
import re
import stat
import threading
from collections import OrderedDict

import radai_archive


def limpar_abandonados(raiz=None, vivo=None):
    from radai_lancador import processo_vivo
    raiz = os.path.realpath(raiz or radai_archive.pasta_temporaria_local(False))
    vivo = vivo or processo_vivo
    try:
        with os.scandir(raiz) as entradas:
            for entrada in entradas:
                dono = re.fullmatch(r"radai_pixels_lote_([1-9][0-9]{0,9})_[a-z0-9_]{8}", entrada.name)
                if not dono or vivo(int(dono[1])):
                    continue
                try:
                    estado = entrada.stat(follow_symlinks=False)
                    caminho = os.path.realpath(entrada.path)
                    if (stat.S_ISDIR(estado.st_mode) and not entrada.is_symlink()
                            and not getattr(estado, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                            and os.path.dirname(caminho) == raiz):
                        shutil.rmtree(caminho)
                except OSError:
                    continue
    except OSError:
        pass


def _orcamento():
    import radai_cleaner
    livre = (radai_cleaner.memoria_da_estacao() or {}).get("livre_mb") or 0
    return min(2 << 30, int(livre) * (1 << 20) // 4)


def _ocupado():
    import radai_queue_state
    vez = radai_queue_state.quem_tem_a_vez()
    return bool(vez.get("dono") or vez.get("lote_quer"))


class CacheDePixels:
    def __init__(self, temporaria=None, orcamento=_orcamento, ocupado=_ocupado):
        self.temporaria = temporaria or (lambda: radai_archive.pasta_temporaria_local(False))
        self.orcamento = orcamento
        self.ocupado = ocupado
        self.trava = threading.RLock()
        self.geracao = None
        self.pendentes = OrderedDict()
        self.volumes = OrderedDict()
        self.thread = None
        self.escrita = threading.Lock()
        self.sinal = threading.Event()

    def iniciar(self, busca):
        self.limpar()
        with self.trava:
            self.geracao = busca

    def oferecer(self, busca, serie):
        arquivos = serie.get("arquivos") or ()
        if not arquivos:
            return
        chave = (serie["uid"], arquivos[0]["caminho"])
        with self.trava:
            if self.geracao != busca or busca is None or chave in self.volumes:
                return
            if chave in self.pendentes:
                return
            agendados = sum(len(s["arquivos"]) for _, s in self.pendentes.values())
            if len(self.pendentes) >= 500 or agendados + len(arquivos) > 24000:
                return
            self.pendentes[chave] = (busca, serie)
            if self.thread is None:
                self.thread = threading.Thread(target=self._trabalhar, name="lote-pixels", daemon=True)
                self.thread.start()

    def _trabalhar(self):
        while True:
            with self.trava:
                if not self.pendentes:
                    self.thread = None
                    return
                chave = next(iter(self.pendentes))
                busca, serie = self.pendentes[chave]
            if self.ocupado():
                self.sinal.wait(0.25)
                self.sinal.clear()
                continue
            with self.trava:
                if self.geracao != busca or chave not in self.pendentes:
                    continue
                self.pendentes.pop(chave)
            with self.escrita:
                try:
                    self._preparar(chave, busca, serie)
                except Exception:
                    # Toda falha de pré-carga mantém a leitura normal do visor disponível.
                    pass
            with self.trava:
                if self.geracao == busca and chave not in self.volumes and self.ocupado():
                    self.pendentes[chave] = (busca, serie)

    def _vigente(self, busca):
        with self.trava:
            return self.geracao == busca and not self.ocupado()

    @staticmethod
    def _apagar(pasta):
        try:
            shutil.rmtree(pasta)
        except OSError:
            # O prefixo da faxina permite nova tentativa se o Windows reteve o arquivo.
            pass
        finally:
            radai_archive.soltar_em_uso(pasta)

    def _preparar(self, chave, busca, serie):
        import numpy as np
        import radai_thumbnail as mini
        if not self._vigente(busca):
            return
        arqs = serie["arquivos"]
        primeira_fonte = mini._fonte(arqs[0])
        primeiro = mini._ler_corte(arqs[0]["caminho"])
        if not mini._mesmo_corte(primeiro, serie, arqs[0]):
            return
        altura, largura = int(primeiro.Rows), int(primeiro.Columns)
        teto = self.orcamento()
        por_corte = altura * largura * 4
        if not por_corte or max(len(arqs), 8) * por_corte > teto:
            return
        # O visor usa o frame central de cada arquivo multiframe.
        base = mini._hu(primeiro)
        del primeiro
        if base.ndim != 2 or not base.size:
            return
        forma = (len(arqs), *base.shape)
        tamanho = len(arqs) * base.nbytes
        if tamanho > teto:
            return
        with self.trava:
            while self.volumes and sum(v[2] for v in self.volumes.values()) + tamanho > teto:
                _, antigo = self.volumes.popitem(last=False)
                self._apagar(antigo[0])
        raiz = self.temporaria()
        if shutil.disk_usage(raiz).free < tamanho + (512 << 20):
            return
        pasta = tempfile.mkdtemp(prefix="radai_pixels_lote_%d_" % os.getpid(), dir=raiz)
        radai_archive.marcar_em_uso(pasta)
        mapa = None
        try:
            caminho = os.path.join(pasta, "pixels.f32")
            mapa = np.memmap(caminho, mode="w+", dtype=np.float32, shape=forma)
            fontes = []
            for i, arq in enumerate(arqs):
                if not self._vigente(busca):
                    return
                fonte = mini._fonte(arq)
                # O primeiro corte também deve ficar entre as duas leituras da assinatura.
                if i == 0 and fonte != primeira_fonte:
                    return
                if i:
                    ds = mini._ler_corte(arq["caminho"])
                    if (not mini._mesmo_corte(ds, serie, arq)
                            or (int(ds.Rows), int(ds.Columns)) != (altura, largura)):
                        return
                    base = mini._hu(ds)
                    del ds
                if base.shape != forma[1:] or mini._fonte(arq) != fonte:
                    return
                mapa[i] = base
                fontes.append(fonte)
            mapa.flush()
            del mapa
            mapa = None
            with self.trava:
                if self.geracao != busca or self.ocupado():
                    return
                anterior = self.volumes.pop(chave, None)
                if anterior:
                    self._apagar(anterior[0])
                self.volumes[chave] = (pasta, forma, tamanho, fontes)
                pasta = None
        finally:
            del mapa
            if pasta is not None:
                self._apagar(pasta)

    def corte(self, serie, i):
        import numpy as np
        import radai_thumbnail as mini
        arqs = serie["arquivos"]
        chave = (serie["uid"], arqs[0]["caminho"])
        with self.trava:
            volume = self.volumes.get(chave)
            if volume is None:
                return None
            pasta, forma, _, fontes = volume
            try:
                if forma[0] == len(arqs) and fontes[i] == mini._fonte(arqs[i]):
                    self.volumes.move_to_end(chave)
                    mapa = np.memmap(os.path.join(pasta, "pixels.f32"), mode="r", dtype=np.float32, shape=forma)
                    try:
                        return mapa[i].copy()
                    finally:
                        del mapa
            except OSError:
                pass
            self.volumes.pop(chave)
            self._apagar(pasta)
            return None

    def limpar(self, busca=None):
        with self.trava:
            if busca is not None and self.geracao != busca:
                return
            self.geracao = None
            self.pendentes.clear()
            self.sinal.set()
            antigos = list(self.volumes.values())
            self.volumes.clear()
        # Espera no máximo a leitura do corte em andamento. Só retorna depois de retirar os arquivos.
        with self.escrita:
            for volume in antigos:
                self._apagar(volume[0])


pixels = CacheDePixels()
atexit.register(pixels.limpar)
