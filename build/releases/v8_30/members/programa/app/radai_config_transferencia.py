"""Transferência transacional das preferências da suíte, sem dados de casos."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import radai_config as C

SECOES = ("configuracao", "nomes", "protocolos", "aparencia")
JORNAL = ".suite-config-pendente.json"
BACKUP = ".suite-config-anterior.json"
PREFERENCIAS = {
    "radai_tema": {"claro", "escuro", "sistema"},
    "radai_idioma": {"pt-BR", "en", "de", "es", "fr", "it", "pl", "ja", "zh-CN", "ar", "ko", "bn"},
    "radai_trilho_aberto": {"0", "1"},
    "radai_varrer_dias": {"0", "1", "3", "7", "30"},
}


def _prefs(valores):
    if not isinstance(valores, dict) or any(
        k not in PREFERENCIAS or not isinstance(v, str) or v not in PREFERENCIAS[k]
        for k, v in valores.items()
    ):
        raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
    return dict(valores)


def _arquivos(cfg):
    cfg = Path(cfg)
    return (cfg, cfg.with_name(C.NOME_DOS_NOMES), cfg.with_name(C.NOME_DOS_PROTOCOLOS))


def _snapshot(cfg):
    return {p.name: p.read_bytes().decode("utf-8") if p.exists() else None for p in _arquivos(cfg)}


def _restaurar(cfg, documentos):
    if set(documentos) != {p.name for p in _arquivos(cfg)}:
        raise ValueError(C._ARQUIVO_INVALIDO)
    for destino in _arquivos(cfg):
        texto = documentos[destino.name]
        if texto is None:
            destino.unlink(missing_ok=True)
        else:
            C._gravar_bytes(destino, texto.encode("utf-8"))


def recuperar(cfg):
    pendente = Path(cfg).with_name(JORNAL)
    if pendente.exists():
        _restaurar(cfg, json.loads(pendente.read_text(encoding="utf-8")))
        pendente.unlink()


def _gravar(cfg, antes, depois, aparencia, *, guardar_anterior=True):
    pendente = Path(cfg).with_name(JORNAL)
    C._gravar_bytes(pendente, json.dumps(antes).encode())
    try:
        for p in _arquivos(cfg):
            if depois[p.name] != antes[p.name]:
                if depois[p.name] is None:
                    p.unlink(missing_ok=True)
                else:
                    C._gravar_bytes(p, depois[p.name].encode("utf-8"))
        if guardar_anterior:
            C._gravar_bytes(pendente.with_name(BACKUP), json.dumps(
                {"arquivos": antes, "apos": depois, "aparencia": aparencia}).encode())
        pendente.unlink()
    except BaseException:
        recuperar(cfg)
        raise


def exportar(cfg, chaves, versao, secoes, aparencia):
    sec = _selecao(secoes, SECOES)
    with C._editar_personalizadas(cfg):
        pacote = C.exportar(cfg, chaves, versao)
        if sec.intersection(("nomes", "protocolos")):
            # Uma personalização ilegível não deve virar um backup vazio.
            perfil, protocolos = C._estado_personalizado(cfg)
            pacote["secoes"].update(nomes=perfil, protocolos=protocolos)
        pacote["secoes"]["aparencia"] = _prefs(aparencia)
        pacote["secoes"] = {k: v for k, v in pacote["secoes"].items() if k in sec}
    return pacote


def _selecao(valores, existentes):
    if not isinstance(valores, list) or not valores or any(
        not isinstance(k, str) or k not in SECOES or k not in existentes for k in valores
    ):
        raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
    return set(valores)


def transferir(pedido, cfg, chaves, estruturas, modelo, aplicar=False):
    doc = pedido.get("dados")
    secs, erro = C._secoes_da_exportacao(doc)
    if erro or type(doc.get("versao")) is not int or doc["versao"] != C.VERSAO_DA_EXPORTACAO:
        raise C.ErroPersonalizacao(erro or C._ARQUIVO_INVALIDO)
    disponiveis = [s for s in SECOES if s in secs]
    marcadas = _selecao(pedido.get("secoes", disponiveis), disponiveis)
    if "configuracao" in marcadas and not isinstance(secs["configuracao"], dict):
        raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
    aparencia = _prefs(pedido.get("aparencia", {}))
    prefs_novas = _prefs(secs["aparencia"]) if "aparencia" in marcadas else {}
    with C._editar_personalizadas(cfg):
        antes = _snapshot(cfg)
        assinatura = json.dumps([antes, doc, aparencia], sort_keys=True, separators=(",", ":")).encode()
        revisao = hashlib.sha256(assinatura).hexdigest()
        if aplicar and revisao != pedido.get("revisao"):
            raise C.ErroPersonalizacao("As configurações mudaram. Confira a nova prévia.", 409)
        resumo = C.previa_da_importacao(doc, cfg, chaves, estruturas)
        with TemporaryDirectory() as pasta:
            copia = Path(pasta) / Path(cfg).name
            _restaurar(copia, antes)
            sub = {k: secs[k] for k in ("nomes", "protocolos") if k in marcadas}
            conflitos = {}
            if sub:
                personal = {"dados": dict(doc, secoes=sub)}
                conflitos = C.transferir_personalizadas(personal, copia, estruturas)
                if aplicar:
                    personal.update(revisao=conflitos["revisao"],
                                    substituir_nomes=pedido.get("substituir_nomes", False),
                                    substituir_protocolos=pedido.get("substituir_protocolos", False))
                    C.transferir_personalizadas(personal, copia, estruturas, aplicar=True)
            if not aplicar:
                return dict(resumo, revisao=revisao, secoes=disponiveis, personalizadas=conflitos)
            if "configuracao" in marcadas:
                mudar = {i["chave"]: i["novo"] for i in resumo["configuracao"]["itens"]
                         if i["muda"] and not i["aviso"]}
                if mudar:
                    ok, erro = C.escrever(copia, mudar, modelo)
                    if not ok:
                        raise OSError(erro)
            _gravar(cfg, antes, _snapshot(copia), aparencia)
            return {"ok": True, "aparencia": prefs_novas}


def desfazer(cfg):
    with C._editar_personalizadas(cfg):
        backup = Path(cfg).with_name(BACKUP)
        if not backup.exists():
            raise C.ErroPersonalizacao("Nenhuma alteração para desfazer.")
        dados = json.loads(backup.read_text(encoding="utf-8"))
        atual = _snapshot(cfg)
        if atual != dados.get("apos"):
            raise C.ErroPersonalizacao("As configurações mudaram. Confira a nova prévia.", 409)
        _gravar(cfg, atual, dados["arquivos"], {}, guardar_anterior=False)
        backup.unlink()
        return {"ok": True, "aparencia": dados["aparencia"]}


def salvar(pedido, cfg, chaves, padroes, estruturas, modelo):
    """Valida as três edições da tela em conjunto antes de trocar os arquivos."""
    valores = pedido.get("valores", {})
    if not isinstance(valores, dict) or any(k not in chaves or not isinstance(v, str)
                                             or "\n" in v or "\r" in v for k, v in valores.items()):
        raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
    prefs = _prefs(pedido.get("aparencia", {}))
    with C._editar_personalizadas(cfg):
        antes = _snapshot(cfg)
        disco = C.ler_arquivo(cfg)[1]
        mudancas = {k: v for k, v in valores.items()
                    if v.strip() != str(disco.get(k, padroes.get(k, ""))).strip()}
        if "ROOT" in mudancas:
            return {"ok": False, "precisa_confirmar": True}
        with TemporaryDirectory() as pasta:
            copia = Path(pasta) / Path(cfg).name
            _restaurar(copia, antes)
            if mudancas:
                ok, erro = C.escrever(copia, mudancas, modelo)
                if not ok:
                    raise OSError(erro)
            if "nomes" in pedido:
                n = C._perfil_de_nomes(pedido["nomes"])
                ok, resultado = C.gravar_nomes(n["modo"], n["nomes"], estruturas,
                                                caminho_cfg=copia, cores=n["cores"])
                if not ok:
                    return dict(resultado, secao="nomes")
            if "protocolo" in pedido:
                prot = pedido["protocolo"]
                if not isinstance(prot, dict):
                    raise C.ErroPersonalizacao(C._ARQUIVO_INVALIDO)
                ok, resultado = C.gravar_protocolo(prot, estruturas.get(prot.get("modalidade"), []), copia)
                if not ok:
                    return dict(resultado, secao="protocolos")
            depois = _snapshot(copia)
        if antes != depois:
            _gravar(cfg, antes, depois, prefs, guardar_anterior=False)
        return {"ok": True, "nada_mudou": antes == depois, "salvos": sorted(mudancas)}
