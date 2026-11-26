"""Carrega o histórico do plugin instalado no processo cancelável do visor."""
from hashlib import sha256
import inspect
import os
from pathlib import Path
import sys
from types import SimpleNamespace


def _origem(pasta, uid):
    chave = os.path.normcase(str(Path(pasta))) + "\0" + str(uid)
    return sha256(chave.encode("utf-8", "surrogatepass")).hexdigest()


class Publicados(dict):
    # O plugin usa (Path, UID) ao procurar a publicação e modifica somente a
    # pequena linha correspondente. O RPC transporta uma chave por série.
    def __contains__(self, chave):
        return super().__contains__(_origem(*chave))

    def __getitem__(self, chave):
        return super().__getitem__(_origem(*chave))


async def complementar(request, leitor, limite, publicados):
    from radai_consulta_isolada import ler
    # Origem do plugin e pasta privada vêm da instância já autorizada pelo servidor.
    raiz = Path(inspect.getfile(type(leitor))).resolve().parent.parent
    indices = list(publicados.values())
    fontes = [_origem(p, uid) for p, uid in publicados]
    dados = await ler(request, "historico_neuro", {
        "plugin": str(raiz), "dados": str(leitor.store.data_dir), "limite": limite, "fontes": fontes})
    for i, campos in dados.get("atualizadas", []):
        if 0 <= i < len(indices):
            for chave, valor in campos.items():
                if chave == "detalhes_locais" or not indices[i].get(chave):
                    indices[i][chave] = valor
    return dados.get("series", [])


def listar(dados):
    raiz = Path(dados["plugin"])
    limite = max(1, min(200, int(dados["limite"])))
    # Os caminhos acima não são parâmetros da API pública.
    sys.path.insert(0, str(raiz))
    from integration.neuro_native_review import NeuroReview
    from neuro_rt.result_store import ResultStore
    pasta = Path(dados["dados"])
    if not (pasta / "studies").is_dir():
        return {"series": [], "atualizadas": []}
    store = ResultStore(pasta)
    fontes = dados["fontes"]
    mapeadas = Publicados((chave, {}) for chave in fontes)
    # rows() espera um iterador de revisões e ordena o lote do mais recente para o
    # mais antigo. Por estudo preservamos essa ordem sem abrir o histórico inteiro.
    lote = SimpleNamespace(data_dir=store.data_dir)
    review = NeuroReview(SimpleNamespace(studies=SimpleNamespace(store=lote)), None)
    saida = []
    for pasta_estudo in sorted(store.root.iterdir(), reverse=True):
        if not pasta_estudo.is_dir():
            continue
        try:
            revisoes = store._valid_revisions(pasta_estudo.name)
        except (OSError, ValueError):
            continue
        lote.iter_manifests = lambda **args: (registro for _, registro in revisoes)
        saida.extend(review.rows(limite - len(saida), mapeadas))
        if len(saida) >= limite:
            break
    alteradas = [[i, {k: linha[k] for k in ("detalhes_locais","pid","date") if k in linha}]
                 for i, linha in enumerate(mapeadas.values()) if "detalhes_locais" in linha]
    return {"series": saida, "atualizadas": alteradas}
