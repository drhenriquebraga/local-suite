# -*- coding: utf-8 -*-
import hashlib
import io
import json
import os
import sys

ARQUIVO = u"_requisitos.json"

_FONTES = (
    (u"requirements", os.path.join(u"build", u"requirements-demo.txt")),
)


def _ler(raiz, rel):
    caminho = os.path.join(raiz, *rel.split(u"/")) if u"/" in rel else \
        os.path.join(raiz, rel)
    if not os.path.isfile(caminho):
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
            import _componentes
            caminho = _componentes.fonte(rel.replace("\\", "/"), suite=raiz)
        except Exception:
            pass
    try:
        with io.open(caminho, encoding=u"utf-8-sig", errors=u"replace") as f:
            return f.read()
    except Exception:
        return u""


def _do_configurador(raiz):
    import re
    t = _ler(raiz, os.path.join(u"build", u"configurar_ambiente.py"))
    partes = []
    for chave in (u"PY_VERSAO", u"PIP_RODA"):
        m = re.search(r'^%s\s*=\s*"([^"]*)"' % chave, t, re.M)
        partes.append(u"%s=%s" % (chave, m.group(1) if m else u"?"))
    tasks = _tasks_do_catalogo(raiz)
    partes.append(u"TASKS=" + u",".join(tasks))
    return u"\n".join(partes), tasks


def _tasks_do_catalogo(raiz):
    import ast
    t = _ler(raiz, os.path.join(u"app", u"radai_tasks.py"))
    if not t:
        raise ValueError(u"nao achei app/radai_tasks.py em %r -- sem ele a "
                         u"impressao sairia sem tasks, e duas instalacoes com "
                         u"pesos diferentes compariam IGUAL" % raiz)
    for no in ast.parse(t).body:
        if isinstance(no, ast.Assign) and \
                getattr(no.targets[0], u"id", u"") == u"_LINHAS":
            linhas = ast.literal_eval(no.value)
            return sorted(x[0] for x in linhas if x[5])
    raise ValueError(u"app/radai_tasks.py nao declara `_LINHAS` -- a extracao "
                     u"tem de FALHAR aqui, e nao devolver lista vazia: lista "
                     u"vazia vira impressao que compara igual com qualquer "
                     u"outra vazia")


def _versoes(raiz):
    import re
    t = _ler(raiz, os.path.join(u"build", u"artefatos.py"))
    m = re.search(r"^VERSOES\s*=\s*\{(.*?)^\}", t, re.M | re.S)
    if not m:
        return u"", {}
    pares = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', m.group(1)))
    pares = {k:v for k,v in pares.items() if not k.endswith("_rocards")}
    return u"\n".join(u"%s=%s" % (k, pares[k]) for k in sorted(pares)), pares


def _modelos_do_registro(raiz):
    import ast
    t = _ler(raiz, os.path.join(u"app", u"radai_models.py"))
    if not t:
        raise ValueError(u"nao achei app/radai_models.py em %r" % raiz)
    for no in ast.parse(t).body:
        if isinstance(no, ast.Assign) and \
                getattr(no.targets[0], u"id", u"") == u"MODELOS":
            modelos = ast.literal_eval(no.value)
            linhas = []
            for ident in sorted(modelos):
                if ident == "rocards_lad":
                    continue
                m = modelos[ident] or {}
                arqs = sorted(u"%s:%s" % (r, t_) for r, t_ in
                              (m.get(u"arquivos") or ()))
                vols = sorted(u"%s:%s" % (r, t_) for r, t_ in
                              (m.get(u"volumes") or ()))
                dig = dict(m.get(u"sha256") or {})
                dig.update(m.get(u"md5") or {})
                dig.update(m.get(u"sha256_dos_volumes") or {})
                cont = sorted(u"%s:%s" % (r, t_) for r, t_ in
                              (m.get(u"conteudo") or ()))
                linhas.append(u"%s=%s|%s|%s|%s%s" % (
                    ident, u",".join(arqs), u",".join(vols),
                    u",".join(u"%s:%s" % (k, dig[k]) for k in sorted(dig)),
                    m.get(u"revisao") or u"",
                    (u"|" + u",".join(cont)) if cont else u""))
            return u"\n".join(linhas)
    raise ValueError(u"app/radai_models.py nao declara `MODELOS`")


def _pesos_de_resolucao_ct(raiz):
    """Lê também árvores antigas, que ainda não publicavam esse requisito."""
    import ast
    def tabela(arquivo, chave):
        for no in ast.parse(_ler(raiz, arquivo)).body:
            if isinstance(no, ast.Assign) and getattr(no.targets[0], "id", "") == chave:
                return ast.literal_eval(no.value)
        return {}
    perfis = tabela("app/radai_tasks.py", "DATASETS_RESOLUCAO_CT")
    if not perfis:
        return {}
    artefatos = tabela("build/artefatos.py", "PESOS_TS")
    saida = {}
    for mm, dataset in sorted(perfis.items()):
        nome = "Dataset%d_TotalSegmentator_total_%dmm_1559subj.zip" % (dataset, mm)
        origem = artefatos[nome]
        saida[str(mm)] = dict(dataset=dataset, sha256=origem["sha256"], bytes=origem["bytes"])
    if tabela('app/radai_tasks.py', 'DATASET_BODY_ULTRA') == 299:
        origem = artefatos['Dataset299_body_1559subj.zip']
        saida['body_ultra'] = dict(dataset=299, sha256=origem['sha256'], bytes=origem['bytes'])
    return saida


def calcular(raiz):
    blocos = []
    req = _ler(raiz, _FONTES[0][1])
    req_n = u"\n".join(l.rstrip() for l in req.replace(u"\r\n", u"\n").split(u"\n")
                       if l.strip() and not l.strip().startswith(u"#"))
    blocos.append(u"[requirements]\n" + req_n)
    cfg, tasks = _do_configurador(raiz)
    blocos.append(u"[configurador]\n" + cfg)
    ver, pares = _versoes(raiz)
    blocos.append(u"[versoes]\n" + ver)
    modelos = _modelos_do_registro(raiz)
    blocos.append(u"[modelos]\n" + modelos)
    base_sem_perfis_ct = hashlib.sha256(u"\n".join(blocos).encode("utf-8")).hexdigest()
    pesos_ct = _pesos_de_resolucao_ct(raiz)
    if pesos_ct:
        blocos.append("[resolucoes_total_v3]\n" + json.dumps(
            pesos_ct, sort_keys=True, separators=(",", ":")))

    texto = u"\n".join(blocos)
    imp = hashlib.sha256(texto.encode(u"utf-8")).hexdigest()
    por_modelo = {}
    for linha in modelos.split(u"\n"):
        if u"=" in linha:
            ident = linha.split(u"=", 1)[0]
            por_modelo[ident] = hashlib.sha256(
                linha.encode(u"utf-8")).hexdigest()[:16]
    return {
        u"impressao": imp,
        u"base_sem_perfis_ct": base_sem_perfis_ct,
        u"resolucoes_total_v3": pesos_ct,
        u"modelos": por_modelo,
        u"tasks": tasks,
        u"versoes": pares,
        u"linhas_requirements": len([l for l in req_n.split(u"\n") if l]),
    }


def gravar(raiz_fonte, destino, versao=u""):
    d = calcular(raiz_fonte)
    d[u"versao"] = versao
    d[u"_leia"] = (u"Impressao do que exige rede: bibliotecas, pesos e "
                   u"runtime. Se ela bate com a do pacote novo, a "
                   u"atualizacao e' copia de codigo -- sem internet e sem "
                   u"administrador. Ver build/requisitos.py.")
    caminho = os.path.join(destino, ARQUIVO)
    with io.open(caminho, u"w", encoding=u"utf-8", newline=u"\n") as f:
        f.write(json.dumps(d, indent=1, ensure_ascii=False, sort_keys=True))
    return caminho, d


def ler(pasta):
    try:
        with io.open(os.path.join(pasta, ARQUIVO),
                     encoding=u"utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def comparar_estacao(raiz_fonte, pasta):
    """A exceção offline exige requisitos compatíveis E checkpoints presentes."""
    pacote = calcular(raiz_fonte)
    instalado = ler(pasta)
    compativel, motivos = comparar(instalado, pacote)
    perfis = pacote.get("resolucoes_total_v3")
    if not perfis:
        return compativel, motivos
    base = dict(pacote, impressao=pacote["base_sem_perfis_ct"])
    if not compativel and not comparar(instalado, base)[0]:
        return False, motivos
    # O interpretador é o da estação antiga. Use o verificador desta entrega.
    import importlib.util
    fonte = os.path.join(raiz_fonte, "app", "radai_tasks.py")
    spec = importlib.util.spec_from_file_location("radai_tasks_da_entrega", fonte)
    tasks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tasks)
    pesos = os.path.join(pasta, "ts_weights")
    fallback_v2 = tasks.base_no_disco("CT", pesos) == "total_v2"
    for mm in perfis:
        try:
            if mm == 'body_ultra':
                tasks.exigir_peso_body_ultra(pesos)
            elif not fallback_v2:
                tasks.exigir_peso_resolucao_ct(int(mm), pesos)
        except RuntimeError as exc:
            return False, [str(exc)]
    return True, []


def comparar(instalado, pacote):
    motivos = []
    a = (instalado or {}).get(u"impressao") or u""
    b = (pacote or {}).get(u"impressao") or u""
    # The complete 8.27 runtime and weights are a verified superset of 8.28.
    # Pin both complete fingerprints: a changed wheel, model or crop stays blocked.
    if (a == "7df29f976f35be4cff76a495764fbf9147b31c6ac2b13be7fced748f236a89be"
            and b == "c12321768237edb89d17f03964859c64feeb2ec426583904888f07fb72bda6dc"):
        return True, []
    # The verified 8.30.3 base already contains every requirement of 8.30.4.
    if (a == "904b72cfd6a437b44c8b3f23dc5457ba0790ab7219de060e8f801f44330c21bf"
            and b == "3f73d83811b252605f060d52435f6381802f8de7353641c34a86a4eb853a945a"):
        return True, []
    if not a:
        motivos.append(u"a instalacao nao tem _requisitos.json "
                       u"(e anterior a este mecanismo)")
    if not b:
        motivos.append(u"o pacote nao tem _requisitos.json")
    if a and b and a != b:
        ct_antigo = (instalado or {}).get("resolucoes_total_v3") or {}
        ct_novo = (pacote or {}).get("resolucoes_total_v3") or {}
        for mm in sorted(set(ct_antigo) | set(ct_novo)):
            if ct_antigo.get(mm) != ct_novo.get(mm):
                registro = ct_novo.get(mm) or ct_antigo[mm]
                motivos.append("TotalSegmentator v3 em %s mm: Dataset%s" % (mm, registro["dataset"]))
        ta = set((instalado or {}).get(u"tasks") or [])
        tb = set((pacote or {}).get(u"tasks") or [])
        if ta != tb:
            motivos.append(u"as tarefas mudaram: %s"
                           % u", ".join(sorted(tb ^ ta)) or u"(?)")
        va = (instalado or {}).get(u"versoes") or {}
        vb = (pacote or {}).get(u"versoes") or {}
        for k in sorted(set(va) | set(vb)):
            if va.get(k) != vb.get(k):
                motivos.append(u"%s: %s -> %s" % (k, va.get(k, u"(ausente)"),
                                                  vb.get(k, u"(ausente)")))
        la = (instalado or {}).get(u"linhas_requirements")
        lb = (pacote or {}).get(u"linhas_requirements")
        if la != lb:
            motivos.append(u"requirements: %s -> %s linhas" % (la, lb))
        ma = (instalado or {}).get(u"modelos")
        mb = (pacote or {}).get(u"modelos") or {}
        if ma is None and mb:
            motivos.append(u"a impressao passou a conferir os pesos dos "
                           u"modelos; o pacote leva: %s" % u", ".join(sorted(mb)))
        elif ma is not None:
            for k in sorted(set(ma) | set(mb)):
                if k not in ma:
                    motivos.append(u"modelo novo: %s" % k)
                elif k not in mb:
                    motivos.append(u"modelo retirado: %s" % k)
                elif ma[k] != mb[k]:
                    motivos.append(u"pesos trocados: %s" % k)
        if not motivos:
            motivos.append(u"as bibliotecas ou os pesos mudaram "
                           u"(a impressao difere)")
    return (bool(a) and a == b), motivos
