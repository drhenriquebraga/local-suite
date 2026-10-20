# -*- coding: utf-8 -*-
import io
import json
import os
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
APP = os.path.join(RAIZ, "app")

_BASE = tempfile.mkdtemp(prefix="radai_valid_")
os.environ["RADAI_CALIB_DIR"] = _BASE
sys.path.insert(0, APP)

import radai_archive
import radai_validation as V

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_valid_')


assert str(radai_archive.raiz()) == _BASE, (
    "o acervo nao foi para a pasta temporaria: %s" % radai_archive.raiz())

_RESULTADOS = []
_TEMPS = [_BASE]
VERBOSO = "-v" in sys.argv


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    if VERBOSO or not ok:
        print("  %-6s %s%s" % ("OK" if ok else "FALHA", nome,
                               ("  [%s]" % detalhe) if detalhe else ""))


def secao(t):
    if VERBOSO:
        print("\n-- %s %s" % (t, "-" * max(0, 58 - len(t))))


def limpar():
    d = V.raiz()
    if d.exists():
        shutil.rmtree(str(d), ignore_errors=True)


def teste_nenhum_identificador_no_arquivo():
    secao("rastreio: nada que identifique paciente entra no arquivo")
    limpar()
    V.registrar_caso(
        identificador="PRONTUARIO-77431",
        versao_app="2.0", resultado="ok", operador="tecnico1",
        modelos={"TotalSegmentator": "2.4.0"}, pesos=["Dataset291"],
        extra={"estruturas": 142, "segundos": 4356, "tasks": ["total"]})
    bruto = io.open(str(V.caminho(V.ARQ_RASTREIO)), encoding="utf-8").read()

    checar("o PatientID nao aparece", "77431" not in bruto)
    checar("nem em minusculas ou pedaco", "prontuario" not in bruto.lower())
    linha = json.loads(bruto.strip())
    checar("o caso e uma etiqueta", linha["caso"].startswith("caso-"), linha["caso"])
    checar("de 16 hex", len(linha["caso"]) == len("caso-") + 16, linha["caso"])
    checar("as metricas sobreviveram", linha.get("estruturas") == 142)
    checar("a versao do app esta la", linha.get("app") == "2.0")
    checar("e a de cada modelo tambem",
           linha.get("modelos", {}).get("TotalSegmentator") == "2.4.0")


def teste_chave_com_cara_de_identificador_e_recusada():
    secao("rastreio: extra com identificador dentro e recusado")
    limpar()
    V.registrar_caso(
        "PAC-1", "2.0", "ok",
        extra={"uid": "1.9.999.2.55.3.1091183246",
               "PatientID": "FANTOMA-0001",
               "caminho": r"C:\TCs\PAC 1\CT",
               "SeriesInstanceUID": "1.2.840.1",
               "paciente_nome": "Fulano de Tal",
               "observacao": "paciente Maria, prontuario 8891",
               "serie_ref": "1.9.999.2.55.3.109",
               "operador_email": "tecnico@hospital.br",
               "estruturas": 7, "segundos": 4356,
               "tasks": ["total", "head_glands_cavities"],
               "gpu": True, "dsc_medio": 0.87})
    linha = json.loads(io.open(str(V.caminho(V.ARQ_RASTREIO)), encoding="utf-8").read().strip())
    bruto = json.dumps(linha, ensure_ascii=False)
    for proibido in ("1.2.840", "77431", "TCs", "Fulano", "Maria", "8891", "@hospital"):
        checar("nao vazou %r" % proibido, proibido not in bruto, bruto[:100])
    checar("mas a contagem passou", linha.get("estruturas") == 7)
    checar("a duracao passou", linha.get("segundos") == 4356)
    checar("a lista de tasks passou", linha.get("tasks") == ["total", "head_glands_cavities"])
    checar("o booleano passou", linha.get("gpu") is True)
    checar("e o float passou", linha.get("dsc_medio") == 0.87)


def teste_a_peneira_de_forma_isolada():
    secao("rastreio: forma de metrica passa, forma de identificador nao")
    passa = [142, 0, -3, 4356.5, True, False, "total", "head_glands_cavities",
             "v2.0", "2.4.0", "ok", ["total", "lung_vessels"], 0.87]
    nao = ["Fulano de Tal", r"C:\TCs\PAC 1\CT", "1.9.999.2.55.3.109",
           "tecnico@hospital.br", "/var/dados/pac", "a" * 60,
           "Maria Silva", "prontuario 8891", {"a": 1}, None,
           ["ok", "Fulano de Tal"]]
    for v in passa:
        checar("passa: %r" % (v,), V._forma_de_metrica(v))
    for v in nao:
        checar("recusa: %r" % (v if not isinstance(v, str) or len(v) < 30 else v[:26] + "...",),
               not V._forma_de_metrica(v))


def teste_pseudonimo_nao_volta_por_forca_bruta():
    secao("pseudonimo: forca bruta sobre o espaco de prontuarios falha")
    limpar()
    import hashlib
    alvo_real = "45012"
    etiqueta = V.pseudonimo(alvo_real)

    achou_hmac = None
    achou_sha = None
    sha_alvo = hashlib.sha256(alvo_real.encode()).hexdigest()[:16]
    for n in range(45000, 45100):
        cand = str(n)
        if V.pseudonimo(cand) == etiqueta and cand != alvo_real:
            achou_hmac = cand
        if hashlib.sha256(cand.encode()).hexdigest()[:16] == sha_alvo:
            achou_sha = cand

    checar("hash simples cairia (a busca funciona)", achou_sha == alvo_real, str(achou_sha))
    checar("o HMAC nao cai: so o proprio valor bate",
           V.pseudonimo(alvo_real) == etiqueta)
    checar("e nenhum outro candidato colide", achou_hmac is None, str(achou_hmac))

    seg = V.caminho(V.ARQ_SEGREDO)
    guardado = seg.read_bytes()
    seg.unlink()
    outra = V.pseudonimo(alvo_real)
    checar("trocar o segredo troca a etiqueta", outra != etiqueta,
           "%s vs %s" % (etiqueta, outra))
    seg.write_bytes(guardado)
    checar("e devolver o segredo devolve a etiqueta", V.pseudonimo(alvo_real) == etiqueta)


def teste_pseudonimo_e_estavel_e_normaliza():
    secao("pseudonimo: estavel entre execucoes, tolerante a caixa e espaco")
    a = V.pseudonimo("PAC_0001")
    checar("o mesmo caso da a mesma etiqueta", V.pseudonimo("PAC_0001") == a)
    checar("caixa nao importa", V.pseudonimo("pac_0001") == a)
    checar("espaco em volta nao importa", V.pseudonimo("  PAC_0001 ") == a)
    checar("caso diferente, etiqueta diferente", V.pseudonimo("PAC_0002") != a)
    checar("vazio nao explode", V.pseudonimo("") == "caso-desconhecido")
    checar("None nao explode", V.pseudonimo(None) == "caso-desconhecido")


def teste_registro_segue_o_acervo_fora_de_c_ai():
    secao("lugar: o registro segue o acervo, que fica fora da nuvem")
    limpar()
    checar("a raiz esta dentro do acervo", str(V.raiz()).startswith(_BASE), str(V.raiz()))
    r = V.conferir()
    checar("o laudo nao acusa nuvem", r["nuvem"] is False, r["motivo"])

    guardado = os.environ.get("RADAI_CALIB_DIR")
    os.environ["RADAI_CALIB_DIR"] = os.path.join(_BASE, "Meu Drive", "radai")
    r2 = V.conferir()
    checar("mas acusa quando o caminho tem cara de nuvem", r2["nuvem"] is True, r2["motivo"])
    checar("e o aviso diz o que fazer", "local" in r2["aviso"].lower(), r2["aviso"][:70])
    os.environ["RADAI_CALIB_DIR"] = guardado


def teste_semear_e_idempotente():
    secao("semear: cria a estrutura e nao estraga o que ja existe")
    limpar()
    V.semear(versao_app="2.0")
    for nome in (V.ARQ_ESQUEMA, V.ARQ_ALTERACOES):
        checar("criou %s" % nome, V.caminho(nome).exists())
    checar("criou EVIDENCIAS/v2.0", V.pasta_evidencias("2.0").is_dir())
    V.registrar_alteracao("2.0", "primeira entrada", "para testar a idempotencia")
    antes = V.caminho(V.ARQ_ALTERACOES).read_text(encoding="utf-8")
    V.semear(versao_app="2.0")
    depois = V.caminho(V.ARQ_ALTERACOES).read_text(encoding="utf-8")
    checar("semear de novo nao apaga o historico", antes == depois)


def teste_alteracao_exige_o_porque():
    secao("alteracoes: entrada sem a razao da mudanca e recusada")
    limpar()
    erro = ""
    try:
        V.registrar_alteracao("2.1", "subiu a versao", "")
    except ValueError as e:
        erro = str(e)
    checar("recusou entrada sem por_que", "por_que" in erro, erro[:70])
    erro = ""
    try:
        V.registrar_alteracao("2.1", "", "porque sim")
    except ValueError as e:
        erro = str(e)
    checar("e sem o_que tambem", "o_que" in erro, erro[:70])
    checar("com os dois, grava", V.registrar_alteracao(
        "2.1", "trocou o mapeamento dos lobos",
        "o TS ja entrega os cinco separados; juntavamos sem precisar"))


def teste_alteracao_mais_nova_em_cima():
    secao("alteracoes: a entrada mais nova fica em cima")
    limpar()
    V.registrar_alteracao("2.0", "primeira", "razao um")
    V.registrar_alteracao("2.1", "segunda", "razao dois")
    txt = V.caminho(V.ARQ_ALTERACOES).read_text(encoding="utf-8")
    checar("as duas estao la", "primeira" in txt and "segunda" in txt)
    checar("a 2.1 vem antes da 2.0", txt.index("v2.1") < txt.index("v2.0"))
    checar("e o cabecalho sobreviveu no topo",
           txt.index("Registro de alterações") < txt.index("v2.1"))
    checar("a norma esta citada", "657/2022" in txt)
    checar("e a retencao tambem", "dez anos" in txt)


def teste_evidencia_e_copiada_e_indexada():
    secao("evidencias: copia, nao move, e indexa o que arquivou")
    limpar()
    origem = os.path.join(_BASE, "verify_log.txt")
    io.open(origem, "w", encoding="utf-8").write("TUDO OK: 1680 checagens\n")
    alvo = V.arquivar_evidencia("2.0", origem, "bateria completa da versao 2.0")
    checar("arquivou", bool(alvo) and os.path.exists(alvo), str(alvo))
    checar("o original continua onde estava", os.path.exists(origem))
    idx = V.pasta_evidencias("2.0") / "INDICE.md"
    checar("indexou", idx.exists())
    if idx.exists():
        checar("com a descricao", "bateria completa" in idx.read_text(encoding="utf-8"))
    alvo2 = V.arquivar_evidencia("2.0", origem, "segunda captura")
    checar("nome repetido nao sobrescreve", alvo2 != alvo and os.path.exists(alvo2),
           os.path.basename(alvo2 or ""))


def teste_linha_corrompida_nao_derruba_a_leitura():
    secao("rastreio: JSONL truncado nao impede ler o resto")
    limpar()
    V.registrar_caso("A", "2.0", "ok", extra={"estruturas": 1})
    with io.open(str(V.caminho(V.ARQ_RASTREIO)), "a", encoding="utf-8") as f:
        f.write('{"quando": "2026-08-12", truncad\n')
    V.registrar_caso("B", "2.0", "ok", extra={"estruturas": 2})
    casos = V.ler_casos()
    checar("leu as duas linhas boas", len(casos) == 2, str(len(casos)))
    checar("a mais nova vem primeiro", casos[0].get("estruturas") == 2)


def teste_registrar_nunca_levanta():
    secao("rastreio: falha de escrita nao levanta excecao")
    limpar()
    guardado = os.environ.get("RADAI_CALIB_DIR")
    os.environ["RADAI_CALIB_DIR"] = "Z:\\nao\\existe\\mesmo"
    try:
        r = V.registrar_caso("X", "2.0", "ok")
        checar("devolveu vazio em vez de explodir", r == "", repr(r))
    except Exception as e:
        checar("devolveu vazio em vez de explodir", False, "%s: %s" % (type(e).__name__, e))
    os.environ["RADAI_CALIB_DIR"] = guardado


def teste_esquema_documenta_os_campos():
    secao("esquema: escrito junto com os dados, nao so no repositorio")
    limpar()
    V.semear()
    txt = V.caminho(V.ARQ_ESQUEMA).read_text(encoding="utf-8")
    for campo in ("quando", "caso", "app", "operador", "modelos", "pesos", "resultado"):
        checar("documenta o campo %s" % campo, "`%s`" % campo in txt)
    checar("explica por que nao e hash simples", "forca bruta" in txt or "força bruta" in txt)
    checar("diz o que nunca aparece", "PatientID" in txt)
    checar("e cita a retencao de dez anos", "dez anos" in txt.lower())


def teste_so_biblioteca_padrao():
    secao("estrutura: o modulo nao importa nada fora da stdlib")
    import ast
    src = io.open(_componentes.fonte("app/radai_validation.py"), encoding="utf-8").read()
    fora, permitidos = [], {
        "hashlib", "hmac", "io", "json", "os", "shutil", "sys", "time",
        "datetime", "pathlib", "importlib", "importlib.metadata", "ast",
        "radai_archive",
    }
    for no in ast.walk(ast.parse(src)):
        if isinstance(no, ast.Import):
            for a in no.names:
                if a.name.split(".")[0] not in permitidos:
                    fora.append(a.name)
        elif isinstance(no, ast.ImportFrom) and no.module:
            if no.module.split(".")[0] not in permitidos:
                fora.append(no.module)
    checar("nenhum import fora da stdlib", not fora, ", ".join(fora))


def main():
    print("=" * 64)
    print(" test_validation — registro RDC 657/2022")
    print("=" * 64)
    testes = [teste_nenhum_identificador_no_arquivo,
              teste_chave_com_cara_de_identificador_e_recusada,
              teste_a_peneira_de_forma_isolada,
              teste_pseudonimo_nao_volta_por_forca_bruta,
              teste_pseudonimo_e_estavel_e_normaliza,
              teste_registro_segue_o_acervo_fora_de_c_ai,
              teste_semear_e_idempotente,
              teste_alteracao_exige_o_porque,
              teste_alteracao_mais_nova_em_cima,
              teste_evidencia_e_copiada_e_indexada,
              teste_linha_corrompida_nao_derruba_a_leitura,
              teste_registrar_nunca_levanta,
              teste_esquema_documenta_os_campos,
              teste_so_biblioteca_padrao]
    for t in testes:
        try:
            t()
        except (Exception, SystemExit) as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    for d in _TEMPS:
        shutil.rmtree(d, ignore_errors=True)

    falhas = [(n, d) for n, ok, d in _RESULTADOS if not ok]
    print("\n" + "=" * 64)
    if falhas:
        print("FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n, d in falhas:
            print("  - %s%s" % (n, ("  [%s]" % d) if d else ""))
    else:
        print("OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print("=" * 64)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
