# -*- coding: utf-8 -*-
import shutil
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_prep_')
_cleanup.adotar_prefixo('radai_concl_')
_cleanup.adotar_prefixo('radai_extr_')
_cleanup.adotar_prefixo('radai_aceite_')
_cleanup.adotar_prefixo('radai_rede_')
_cleanup.adotar_prefixo('radai_barra_')
_cleanup.adotar_prefixo('radai_recibo_')
_cleanup.adotar_prefixo('radai_pkg_trava_')

_ACERVO_TESTE = tempfile.mkdtemp(prefix='radai_prep_acervo_')
os.environ["RADAI_CALIB_DIR"] = _ACERVO_TESTE

# GUARDA: o PSModulePath herdado do pwsh 7 faz o Windows PowerShell 5.1 carregar módulos do 7 e perder o Get-FileHash.
_PSMODULEPATH_HERDADO = os.environ.pop("PSModulePath", None)


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BB = chr(92)
CRLF = chr(13) + chr(10)
sys.path.insert(0, os.path.join(RAIZ, "build"))
sys.path.insert(0, os.path.join(RAIZ, "app"))

_ok = _falhou = 0
_falhas = []


def secao(t):
    print(u"\n── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def checar(rotulo, cond, detalhe=u""):
    global _ok, _falhou
    if cond:
        _ok += 1
        print(u"  OK     %s" % rotulo)
    else:
        _falhou += 1
        _falhas.append(rotulo)
        print(u"  FALHA  %s  %s" % (rotulo, detalhe))


def ler(rel):
    p = _componentes.fonte(rel)
    return io.open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else u""


def _ps51_acha_o_get_filehash(amb):
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", "(Get-FileHash -Algorithm SHA256 -LiteralPath "
             "$env:ComSpec).Hash.Length"], capture_output=True, timeout=120,
            env=amb, stdin=subprocess.DEVNULL)
    except Exception:
        return None
    return r.stdout.decode("utf-8", "replace").strip() == u"64"


def _psmodulepath_do_pwsh7():
    try:
        r = subprocess.run(["pwsh", "-NoProfile", "-Command",
                            "$env:PSModulePath"], capture_output=True,
                           timeout=60, stdin=subprocess.DEVNULL)
        return r.stdout.decode("utf-8", "replace").strip() or None
    except Exception:
        return None


def teste_o_ps51_nao_herda_os_modulos_do_pwsh7():
    secao(u"o Windows PowerShell 5.1 do harness não herda os módulos do pwsh 7")
    checar(u"o ambiente do harness não leva PSModulePath",
           u"PSModulePath" not in os.environ
           and u"PSMODULEPATH" not in os.environ)
    checar(u"o PowerShell 5.1 acha o Get-FileHash com o ambiente do harness",
           _ps51_acha_o_get_filehash(dict(os.environ)) is True)
    do7 = _psmodulepath_do_pwsh7()
    if not do7:
        print(u"  PULADO a isca: sem pwsh 7 nesta máquina")
        return
    checar(u"  (isca) com o PSModulePath do pwsh 7 o 5.1 perde o Get-FileHash",
           _ps51_acha_o_get_filehash(dict(os.environ, PSModulePath=do7))
           is False, do7[:120])


def teste_aborta():
    secao(u"aborta, nunca pula (o teste que mais importa)")
    import artefatos as A

    tmp = tempfile.mkdtemp(prefix="radai_prep_")
    bom = os.path.join(tmp, "bom.bin")
    io.open(bom, "wb").write(b"conteudo conhecido")

    ok, msg = A.conferir(bom, "chave/que/nao/existe")
    checar(u"chave fora da tabela REPROVA", not ok)
    checar(u"e a mensagem manda somar o arquivo", u"acrescente" in msg.lower(),
           msg[:70])

    qualquer = sorted(A.ARTEFATOS)[0]
    ok, _ = A.conferir(os.path.join(tmp, "nao_existe"), qualquer)
    checar(u"arquivo ausente REPROVA", not ok)

    chave = min(A.ARTEFATOS, key=lambda k: A.ARTEFATOS[k]["bytes"])
    tam = A.ARTEFATOS[chave]["bytes"]
    falso = os.path.join(tmp, "falso.bin")
    io.open(falso, "wb").write(b"x" * tam)
    ok, msg = A.conferir(falso, chave)
    checar(u"tamanho certo com conteudo errado REPROVA", not ok)
    checar(u"a mensagem cita espelho trocado ou corrupcao",
           u"espelho" in msg.lower() or u"corrupcao" in msg.lower(), msg[:70])
    checar(u"a mensagem mostra o hash esperado E o achado",
           msg.count(u"esperado") and msg.count(u"achado"), msg[:70])

    curto = os.path.join(tmp, "curto.bin")
    io.open(curto, "wb").write(b"<html>404</html>")
    ok, msg = A.conferir(curto, chave)
    checar(u"tamanho errado REPROVA", not ok)
    checar(u"e tem diagnostico proprio (truncado / pagina de erro)",
           u"truncado" in msg.lower() or u"pagina de erro" in msg.lower(),
           msg[:70])

    import configurar_ambiente as _C
    montagens = []
    try:
        _b = io.open(os.path.join(RAIZ, "_bundle.txt"),
                     encoding="utf-8-sig").read().strip()
        if _b:
            montagens.append(_b)
    except Exception:
        pass
    montagens.append(os.path.join(RAIZ, "_montagem", "AUTO_CONTORNO"))
    cab, resto = chave.split("/", 1)
    real = u""
    for bundle in montagens:
        if cab == "cache":
            c = os.path.join(os.path.dirname(bundle), "cache", *resto.split("/"))
        elif cab in getattr(_C, "_PASTAS_DE_MODELO", ()):
            c = os.path.join(bundle, "modelos", cab, *resto.split("/"))
        else:
            c = os.path.join(bundle, "ts_weights", *resto.split("/"))
        if os.path.isfile(c):
            real = c
            break
    if real:
        ok, _ = A.conferir(real, chave)
        checar(u"o arquivo de verdade APROVA", ok, real)
    else:
        print(u"  (pulado: nao ha montagem nesta maquina -- procurei em %s)"
              % u"; ".join(montagens))


def teste_baixar_confere():
    secao(u"baixar() confere, e apaga o que reprovou")
    fonte = ler("build/configurar_ambiente.py")
    checar(u"baixar() aceita a chave do artefato",
           u"def baixar(url, destino, minimo_bytes=0, chave=None, py_recuo=None)"
           in fonte)
    checar(u"ele levanta quando nao confere", u"CONFERENCIA FALHOU" in fonte)
    checar(u"e APAGA o arquivo reprovado", u"destino.unlink()" in fonte,
           u"senao a proxima execucao reusa o que foi recusado")
    checar(u"o que ja estava em cache tambem e conferido",
           u'_conferir("cache")' in fonte)
    checar(u"as duas chamadas passam chave",
           fonte.count(u'chave="cache/') == 2, str(fonte.count(u'chave="cache/')))


def teste_versao_fixada():
    secao(u"versao fixada, nunca 'a mais recente'")
    import artefatos as A

    for k, v in A.VERSOES.items():
        checar(u"%s tem versao com digito" % k, bool(re.match(r"^\d", v)), v)
        checar(u"  e ela e EXATA, e nao uma faixa",
               bool(re.match(r"^\d+\.\d+(\.\d+)?([+.].+)?$", v)),
               u"%r nao e um pino: faixa migra o parque em silencio" % v)

    req = ler("build/requirements-demo.txt")
    soltos = [l.strip() for l in req.split("\n")
              if l.strip() and not l.strip().startswith("#")
              and "==" not in l and not l.strip().startswith("-")]
    checar(u"nenhuma dependencia sem == no requirements", not soltos,
           str(soltos[:3]))
    checar(u"a palavra 'latest' nao aparece no requirements",
           "latest" not in req.lower())

    emp = ler("build/configurar_ambiente.py")
    checar(u"o empacotador nao busca 'latest'",
           "latest" not in _codigo_sem_prosa(emp).lower().replace(
               "latest_", ""))
    isca = emp + (u'\n_URL_ISCA = "https://github.com/x/y/releases/latest"\n')
    checar(u"  (isca) uma URL `releases/latest` no CODIGO reprova",
           "latest" in _codigo_sem_prosa(isca).lower().replace("latest_",
                                                                ""))
    prosa = emp + u'\n# o asset _SETUP_LATEST.zip da release\n'
    checar(u"  e a prosa que cita o nome do asset nao conta",
           "setup_latest" not in _codigo_sem_prosa(prosa).lower())


def _codigo_sem_prosa(fonte):
    import ast
    import tokenize
    prosa = set()
    for n in ast.walk(ast.parse(fonte)):
        if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)):
            prosa.add((n.value.lineno, n.value.col_offset))
    fora = []
    for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and tok.start in prosa:
            continue
        fora.append(tok.string)
    return u" ".join(fora)


def teste_um_caminho():
    secao(u"um caminho de aquisicao: tudo baixa, nada vem embarcado")
    emp = ler("build/configurar_ambiente.py")
    checar(u"os pesos do TotalSegmentator sao BAIXADOS na etapa 4",
           u"def etapa_pesos(" in emp)

    import ast
    arv = ast.parse(emp)
    etapa = next((n for n in ast.walk(arv)
                  if isinstance(n, ast.FunctionDef) and n.name == "etapa_pesos"),
                 None)
    checar(u"achei a funcao etapa_pesos para inspecionar", etapa is not None)
    laco_do_registro = next((n for n in ast.walk(arv)
                             if isinstance(n, ast.FunctionDef)
                             and n.name == "baixar_modelos_do_registro"), None)
    checar(u"  e ela chama `baixar_modelos_do_registro`",
           etapa is not None and laco_do_registro is not None
           and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                   and c.func.id == "baixar_modelos_do_registro"
                   for c in ast.walk(etapa)))
    percorre = chama = False
    for alvo in (etapa, laco_do_registro):
        if alvo is None:
            continue
        for laco in ast.walk(alvo):
            if not isinstance(laco, ast.For):
                continue
            fonte = ast.dump(laco.iter)
            if "MODELOS" not in fonte:
                continue
            percorre = True
            for c in ast.walk(laco):
                if (isinstance(c, ast.Call)
                        and isinstance(c.func, ast.Attribute)
                        and c.func.attr == "baixar"):
                    chama = True
    checar(u"a etapa 4 PERCORRE o registro de modelos", percorre,
           u"sem laco sobre radai_models.MODELOS, modelo novo fica de fora")
    checar(u"e chama baixar() dentro do laco", chama,
           u"percorrer sem baixar deixaria o registro decorativo")
    pesos = []
    for r, _, fs in os.walk(RAIZ):
        if "_montagem" in r or ".git" in r or ".venv" in r:
            continue
        pesos += [os.path.join(r, f) for f in fs if f.endswith((".pth", ".pt"))]
    checar(u"nenhum peso de modelo versionado no repositorio", not pesos,
           str(pesos[:2]))


def teste_aceite_artefato():
    secao(u"o aceite vira arquivo, e e PRE-CONDICAO do build")
    ps = ler("packager/prepare.ps1")
    checar(u"o preparador grava LICENCAS_ACEITAS.txt",
           u"LICENCAS_ACEITAS.txt" in ps)
    checar(u"com quem, maquina e data", u"$env:USERNAME" in ps
           and u"$env:COMPUTERNAME" in ps and u"yyyy-MM-dd" in ps)
    checar(u"registra tambem o RECUSADO, nao so o aceito",
           u"[RECUSADA]" in ps, u"licenca recusada e informacao, nao ausencia")

    i = ps.find(u"function GravarAceites {")
    j = ps.find(u"\nfunction AcharOuBaixarPython {", i)
    k = ps.find(u"function FinalidadeDeclarada {")
    m = ps.find(u"\nfunction AplicarFinalidade {", k)
    bloco = (ps[k:m] + u"\n" + ps[i:j]) if min(i, j, k, m) >= 0 else u""
    checar(u"as funcoes do aceite foram recortadas", bool(bloco))
    if bloco:
        tmp = tempfile.mkdtemp(prefix="radai_aceite_")
        try:
            dub = (
                u"Set-StrictMode -Version Latest\n"
                u"$ErrorActionPreference = 'Stop'\n"
                u"$script:DeclFinalidade = $null\n"
                u"$script:OpcoesLicenca = @()\n"
                u"$script:EstacaoFinal = $false\n"
                u"$script:VERSAO = '0.0-teste'\n"
                u"$script:CaixasLicenca = @(\n"
                u"  New-Object PSObject -Property @{ Checked = $true;\n"
                u"    Tag = @{ componente='X'; versao='1'; licenca='MIT';\n"
                u"             origem='https://exemplo' } })\n"
                u"function T { param($s) $s }\n"
                u"function Idioma-Atual { 'pt-BR' }\n"
                + bloco
                + (u"\nGravarAceites '%s'\n" % tmp.replace("\\", "\\\\")))
            alvo = os.path.join(tmp, "t.ps1")
            io.open(alvo, "w", encoding="utf-8-sig").write(dub)
            out = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", alvo], capture_output=True, text=True, timeout=120)
            erro = (out.stderr or u"").strip()
            checar(u"gravar o aceite NAO levanta (o erro de campo de 21/09)",
                   not erro, erro.replace("\n", " ")[:150])
            feito = os.path.join(tmp, "LICENCAS_ACEITAS.txt")
            checar(u"  e o arquivo sai", os.path.exists(feito))
            if os.path.exists(feito):
                txt = io.open(feito, encoding="utf-8").read()
                checar(u"  e sem licenca restrita ele NAO diz "
                       u"«FINALIDADE NAO DECLARADA»",
                       u"NAO DECLARADA" not in txt,
                       u"recusa inventada onde nao houve pergunta")
                checar(u"  e o aceite do componente obrigatorio esta la",
                       u"[ACEITA]" in txt)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    emp = ler("build/configurar_ambiente.py")
    checar(u"o modo --preparo EXIGE o aceite gravado",
           u"Nao achei o LICENCAS_ACEITAS.txt" in emp)
    checar(u"e o aceite entra no .zip",
           u'("LICENCAS_ACEITAS.txt", aceite)' in emp)

    checar(u"nao existe mais a opcao de pacote parcial",
           u"--sem-vista" not in emp, u"--sem-vista deveria ter saido")
    checar(u"o build EXIGE aceite completo",
           u"def _exigir_aceite_completo(" in emp)
    checar(u"e uma linha [RECUSADA] derruba o preparo",
           u'"[RECUSADA]" in l' in emp)
    checar(u"a trava fica no motor, nao so na interface",
           emp.index(u"def _exigir_aceite_completo(") > 0
           and u"_exigir_aceite_completo(aceite)" in emp)

    ps2 = ler("packager/prepare.ps1")
    checar(u"a tela exige TODAS as licencas",
           u"Where-Object { -not $_.Checked }" in ps2)
    checar(u"e nao manda mais variante para o motor",
           u"--sem-vista" not in ps2)


def teste_pino_cabe_no_runtime_alvo():
    secao(u"pino que nao instala no runtime alvo (o caso do xgboost)")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import configurar_ambiente as C

    checar(u"o alvo continua sendo o 3.10.11", C.PY_VERSAO == "3.10.11",
           C.PY_VERSAO)

    checar(u"reprova `>=3.12` contra o 3.10.11",
           C.clausula_que_exclui(">=3.12") == ">=3.12")
    checar(u"reprova `<3.10`", C.clausula_que_exclui("<3.10") == "<3.10")
    for bom in (">=3.10", ">=3.9", "<4.0,>=3.8", "<3.15,>=3.10", ""):
        checar(u"aceita `%s`" % (bom or u"(nao declara)"),
               C.clausula_que_exclui(bom) == u"")
    checar(u"ignora o que nao sabe ler (`~=3.12`)",
           C.clausula_que_exclui("~=3.12") == u"")

    fonte = ler("build/configurar_ambiente.py")
    corpo = fonte.split(u"def etapa_libs(")[-1].split(u"\ndef ")[0]
    linhas_uteis = [l for l in corpo.splitlines() if not l.lstrip().startswith(u"#")]
    i_conf = next((n for n, l in enumerate(linhas_uteis)
                   if u"conferir_pinos_contra_runtime(" in l), -1)
    i_pip = next((n for n, l in enumerate(linhas_uteis)
                  if u'"pip install -r requirements"' in l), -1)
    checar(u"a etapa 3 chama conferir_pinos_contra_runtime", i_conf >= 0)
    checar(u"e chama ANTES do pip install", 0 <= i_conf < i_pip,
           u"conferidor na linha %d, pip na %d" % (i_conf, i_pip))

    checar(u"sem roda nenhuma = sdist puro, e PASSA (o nnunetv2 e um)",
           C.roda_que_serve([]) is True)
    checar(u"reprova quem publica roda e nenhuma serve",
           C.roda_que_serve([{"filename": "dipy-1.12.0-cp311-cp311-win_amd64.whl"},
                             {"filename": "dipy-1.12.0-cp312-cp312-win_amd64.whl"}])
           is False)
    checar(u"aceita roda cp310 do Windows",
           C.roda_que_serve([{"filename": "dipy-1.11.0-cp310-cp310-win_amd64.whl"}])
           is True)
    checar(u"aceita roda universal (`py3-none-any`)",
           C.roda_que_serve([{"filename": "rt_utils-1.2.7-py3-none-any.whl"}])
           is True)
    checar(u"aceita `py3-none-win_amd64` (a roda do xgboost)",
           C.roda_que_serve([{"filename": "xgboost-3.2.0-py3-none-win_amd64.whl"}])
           is True)

    req = ler("build/requirements-demo.txt")
    for pkg, ruim, porque in (("xgboost", "3.4.1", u"exige Python >=3.12"),
                              ("dipy", "1.12.0", u"nao publica roda cp310")):
        pinos = [l.strip() for l in req.splitlines()
                 if l.strip().startswith(pkg + "==")]
        checar(u"%s esta pinado uma vez so" % pkg, len(pinos) == 1, str(pinos))
        checar(u"e nao e mais o %s (%s)" % (ruim, porque),
               pinos and pinos[0] != "%s==%s" % (pkg, ruim), str(pinos))
    checar(u"o dipy esta pinado (o TotalSegmentator o exige sem versao)",
           any(l.strip().startswith("dipy==") for l in req.splitlines()))

    fonte_rodar = fonte.split(u"def rodar(")[-1].split(u"\ndef ")[0]
    checar(u"o rodar() guarda o pacote que caiu para codigo-fonte",
           u"\\.tar\\.gz" in fonte_rodar
           and u"fonte[0] = m.group(1)" in fonte_rodar)


def teste_extracao_vai_para_o_disco_do_destino():
    secao(u"o pacote trazido e extraido no disco do DESTINO")
    ps = ler("packager/prepare.ps1")
    i = ps.find(u"function PastaDeExtracao {")
    j = ps.find(u"\nfunction LivreEm {", i)
    bloco = ps[i:j] if i >= 0 and j > i else u""
    checar(u"a funcao existe e foi recortada", bool(bloco))
    if not bloco:
        return

    def rodar_ps(destino, zip_path):
        dub = (u"$cxPasta = New-Object PSObject -Property @{ Text = '%s' }\n"
               % destino) + bloco + (u"\nPastaDeExtracao '%s'\n" % zip_path)
        tmp = tempfile.mkdtemp(prefix="radai_extr_")
        try:
            alvo = os.path.join(tmp, "t.ps1")
            io.open(alvo, "w", encoding="utf-8-sig").write(dub)
            out = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", alvo], capture_output=True, text=True, timeout=120)
            return (out.stdout or u"").strip().splitlines()[-1:] or [u""]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    r = rodar_ps(u"D:\\RADIOTERAPIA_AI\\LOCAL_SUITE",
                 u"D:\\RADIOTERAPIA_AI\\INSTALADOR\\bundle.zip")[0]
    checar(u"com destino escolhido, extrai NO DESTINO",
           r.upper().startswith(u"D:\\RADIOTERAPIA_AI\\LOCAL_SUITE"), r)
    checar(u"  e nao no %TEMP%", u"\\Temp\\" not in r, r)

    r2 = rodar_ps(u"", u"E:\\pendrive\\bundle.zip")[0]
    checar(u"sem destino, extrai ao lado do .zip",
           r2.upper().startswith(u"E:\\PENDRIVE"), r2)

    i2 = ps.find(u"function InstalarAqui {")
    j2 = ps.find(u"\nfunction ", i2 + 1)
    j2 = len(ps) if (i2 >= 0 and j2 < 0) else j2
    inst = ps[i2:j2] if i2 >= 0 and j2 > i2 else u""
    codigo = u"\n".join(l for l in inst.splitlines()
                        if not l.lstrip().startswith(u"#"))
    checar(u"InstalarAqui usa PastaDeExtracao", u"PastaDeExtracao $Zip" in codigo)
    i_esp = codigo.find(u"$livre -lt")
    i_ext = codigo.find(u"ExtrairEntrada $ent")
    checar(u"o espaco e conferido ANTES da extracao",
           0 <= i_esp < i_ext, u"conferencia em %d, extracao em %d" % (i_esp, i_ext))
    checar(u"e a conta pede o DOBRO quando extrai no disco do destino",
           u"$fator = 1" in codigo and u"$fator = 2" in codigo)
    checar(u"a mensagem diz quanto falta e quanto ha",
           u"GB $livre" in codigo and u"GB $precisa" in codigo)
    k = codigo.find(u"} finally {")
    checar(u"o `finally` existe e remove a extracao",
           k > 0 and u"RemoverSemTravar $tmp" in codigo[k:],
           u"antes o Remove-Item ficava DENTRO do try, depois da instalacao")
    rem = _funcoes_ps(u"packager/prepare.ps1", [u"RemoverSemTravar", u"InstalarAqui"])
    corpo_rem = rem.get(u"RemoverSemTravar", u"")
    checar(u"  e ela apaga com -Recurse, num processo que a janela espera",
           u"Remove-Item -LiteralPath $env:RADAI_APAGAR -Recurse" in corpo_rem
           and u"while (-not $pr.HasExited)" in corpo_rem
           and u"Pump" in corpo_rem, corpo_rem[:120] + _motivo_ast(rem))
    cod_inst = u"\n".join(l for l in rem.get(u"InstalarAqui", u"").splitlines()
                          if not l.lstrip().startswith(u"#"))
    checar(u"`InstalarAqui` nao apaga pasta na thread da janela",
           bool(cod_inst) and not re.search(r"Remove-Item\b[^\n]*-Recurse", cod_inst),
           [l.strip() for l in cod_inst.splitlines() if u"Remove-Item" in l][:2])
    checar(u"  e a sobra que nao saiu PARA a instalacao (nao extrai por cima)",
           u"RemoverSemTravar $tmp" in cod_inst.split(u"New-Item -ItemType Directory -Path $tmp")[0]
           and u"Nao consegui apagar a extracao anterior" in cod_inst)


class _Recorte(dict):
    falha = u""


_CACHE_AST = {}
_AST_ACUSADO = set()


def _parsear_ps(alvo):
    tmp = tempfile.mkdtemp(prefix="radai_prep_ast_")
    try:
        saida = os.path.join(tmp, "f.json")
        script = os.path.join(tmp, "ast.ps1")
        io.open(script, "w", encoding="utf-8-sig", newline="\r\n").write(
            u"param([string]$Arq, [string]$Saida)\n"
            u"$ErrorActionPreference = 'Stop'\n"
            u"$erros = $null\n"
            u"$ast = [System.Management.Automation.Language.Parser]::ParseFile("
            u"$Arq, [ref]$null, [ref]$erros)\n"
            u"if ($erros -and $erros.Count -gt 0) {\n"
            u"    [Console]::Error.WriteLine('o arquivo tem ' + $erros.Count + "
            u"' erro(s) de sintaxe; o primeiro: ' + $erros[0].Message + "
            u"' (linha ' + $erros[0].Extent.StartLineNumber + ')')\n"
            u"    exit 2\n"
            u"}\n"
            u"$r = @{}\n"
            u"foreach ($f in $ast.FindAll({ param($n) $n -is "
            u"[System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {\n"
            u"    $r[$f.Name] = $f.Extent.Text\n"
            u"}\n"
            u"[System.IO.File]::WriteAllText($Saida, ($r | ConvertTo-Json -Depth 3), "
            u"(New-Object System.Text.UTF8Encoding($false)))\n")
        try:
            p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                                "Bypass", "-File", script, "-Arq", alvo,
                                "-Saida", saida],
                               capture_output=True, timeout=240)
            rc, err = p.returncode, (p.stderr or b"") + (p.stdout or b"")
        except subprocess.TimeoutExpired:
            return None, u"o PowerShell do recorte esgotou 240 s"
        except OSError as e:
            return None, u"nao consegui rodar o PowerShell do recorte: %s" % e
        if not os.path.isfile(saida):
            try:
                texto = err.decode("oem", "replace")
            except LookupError:
                texto = err.decode("cp1252", "replace")
            return None, (u"o PowerShell do recorte saiu com rc=%s sem gravar o "
                          u"JSON; fim da saida: %s" % (rc, texto.strip()[-300:]))
        try:
            d = json.loads(io.open(saida, encoding="utf-8").read() or u"{}")
        except ValueError as e:
            return None, u"o JSON do recorte nao abre (%s), rc=%s" % (e, rc)
        return (d if isinstance(d, dict) else {}), u""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _funcoes_ps(rel, nomes):
    alvo = os.path.join(RAIZ, rel.replace(u"/", os.sep))
    try:
        st = os.stat(alvo)
        chave = (alvo, st.st_mtime_ns, st.st_size)
    except OSError:
        chave = (alvo, None, None)
    if chave not in _CACHE_AST:
        todas, falha = _parsear_ps(alvo)
        if todas is None:
            todas, falha2 = _parsear_ps(alvo)
            if todas is None:
                falha = u"%s | na segunda tentativa: %s" % (falha, falha2)
            else:
                falha = u""
        _CACHE_AST[chave] = (todas, falha)
    todas, falha = _CACHE_AST[chave]
    r = _Recorte((n, todas[n]) for n in nomes if todas and n in todas)
    if falha:
        r.falha = falha
        if rel not in _AST_ACUSADO:
            _AST_ACUSADO.add(rel)
            checar(u"o parser do PowerShell recortou %s" % rel, False, falha)
    return r


def _motivo_ast(fs):
    return (u" -- o parser falhou: %s" % fs.falha) if getattr(fs, "falha", u"") else u""


def teste_o_recorte_diz_por_que_falhou():
    secao(u"o recorte pelo parser: um PowerShell por arquivo, e a falha diz por que")
    fantasma = os.path.join(tempfile.gettempdir(),
                            u"radai_prep_nao_existe_%d.ps1" % os.getpid())
    todas, falha = _parsear_ps(fantasma)
    checar(u"(isca) arquivo que nao existe: sem recorte, e COM o motivo "
           u"(rc e o fim do stderr)",
           todas is None and u"rc=" in falha and len(falha) > 60, falha[:200])
    vazio = _Recorte()
    vazio.falha = u"rc=1 exemplo"
    checar(u"  e o motivo vai para o detalhe da checagem que recebeu o vazio",
           _motivo_ast(vazio) == u" -- o parser falhou: rc=1 exemplo"
           and _motivo_ast({}) == u"", _motivo_ast(vazio))
    chamadas = []
    real = globals()["_parsear_ps"]

    def contar(alvo):
        chamadas.append(alvo)
        return real(alvo)
    globals()["_parsear_ps"] = contar
    try:
        a = _funcoes_ps(u"packager/prepare.ps1", [u"AcompanharProcesso"])
        b = _funcoes_ps(u"packager/prepare.ps1", [u"Pump", u"Registrar"])
    finally:
        globals()["_parsear_ps"] = real
    checar(u"duas chamadas sobre o mesmo arquivo parseiam no maximo uma vez",
           len(chamadas) <= 1 and u"AcompanharProcesso" in a and u"Registrar" in b,
           u"%d parse(s); %s | %s" % (len(chamadas), sorted(a), sorted(b)))


def _rodar_harness(texto, timeout=90):
    tmp = tempfile.mkdtemp(prefix="radai_prep_har_")
    try:
        alvo = os.path.join(tmp, "h.ps1")
        # GUARDA: sem isto a saida segue a pagina de codigo do console (cp850 no verify.cmd) e o acento vira lixo.
        texto = (u"[Console]::OutputEncoding = "
                 u"New-Object System.Text.UTF8Encoding $false\n" + texto)
        io.open(alvo, "w", encoding="utf-8-sig", newline="\r\n").write(texto)
        p = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy",
                              "Bypass", "-STA", "-File", alvo],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL)
        try:
            out = p.communicate(timeout=timeout)[0]
        except subprocess.TimeoutExpired:
            p.kill()
            try:
                p.communicate(timeout=30)
            except Exception:
                pass
            return None, None
        return out.decode("utf-8", "replace"), p.returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _marcas(saida):
    d = {}
    for l in (saida or u"").splitlines():
        if u":" in l:
            k, v = l.split(u":", 1)
            if k.isupper():
                d[k] = v.strip()
    return d


def teste_extracao_nao_prende_a_janela():
    secao(u"a extracao bombeia a janela no meio de um arquivo grande")
    fs = _funcoes_ps(u"packager/prepare.ps1",
                     [u"ExtrairEntrada", u"PumpSeHouveTempo"])
    checar(u"as duas funcoes existem e foram recortadas pelo parser",
           set(fs) == {u"ExtrairEntrada", u"PumpSeHouveTempo"},
           u"%s%s" % (sorted(fs), _motivo_ast(fs)))
    if set(fs) != {u"ExtrairEntrada", u"PumpSeHouveTempo"}:
        return
    import zipfile as _zf
    tmp = tempfile.mkdtemp(prefix="radai_extr_")
    try:
        zp = os.path.join(tmp, "p.zip")
        with _zf.ZipFile(zp, "w", _zf.ZIP_STORED) as z:
            z.writestr("peso_grande.bin", os.urandom(12 * 1048576))
        dest = os.path.join(tmp, "peso_grande.bin")

        def harness(cancelar_no_pump):
            return (
                u"$ErrorActionPreference = 'Stop'\n"
                u"Set-StrictMode -Version Latest\n"
                u"Add-Type -AssemblyName System.IO.Compression.FileSystem\n"
                u"$script:Cancelar = $false\n"
                u"$script:Tamanhos = New-Object System.Collections.ArrayList\n"
                u"$script:Alvo = '%s'\n"
                u"function Pump {\n"
                u"    [void]$script:Tamanhos.Add((Get-Item -LiteralPath $script:Alvo).Length)\n"
                u"    %s\n"
                u"}\n"
                u"$script:RelogioPump = [System.Diagnostics.Stopwatch]::StartNew()\n"
                u"$script:BufExtracao = New-Object byte[] (4MB)\n"
                % (dest, u"$script:Cancelar = $true" if cancelar_no_pump else u"")
                + fs[u"PumpSeHouveTempo"] + u"\n" + fs[u"ExtrairEntrada"] + u"\n" +
                u"$z = [System.IO.Compression.ZipFile]::OpenRead('%s')\n"
                u"# o relogio VENCE antes do primeiro pedaco: o bombeamento que\n"
                u"# vier tem de acontecer DENTRO da gravacao\n"
                u"Start-Sleep -Milliseconds 250\n"
                u"try { ExtrairEntrada $z.Entries[0] $script:Alvo; 'CANCELOU:nao' }\n"
                u"catch { 'CANCELOU:' + $_.Exception.Message }\n"
                u"finally { $z.Dispose() }\n"
                u"'PUMPS:' + ($script:Tamanhos -join ',')\n"
                u"'TAM:' + (Get-Item -LiteralPath $script:Alvo).Length\n" % zp)

        out, rc = _rodar_harness(harness(False))
        m = _marcas(out)
        tams = [int(x) for x in m.get(u"PUMPS", u"").split(u",") if x.strip()]
        checar(u"o arquivo de 12 MB saiu inteiro", m.get(u"TAM") == str(12 * 1048576),
               u"%s | %s" % (m.get(u"TAM"), (out or u"")[-200:]))
        checar(u"a janela foi bombeada DURANTE a gravacao dele",
               any(0 < t < 12 * 1048576 for t in tams),
               u"bombeamentos com o arquivo em %s bytes -- nenhum no meio: a "
               u"janela so' respira entre arquivos" % tams)
        out2, rc2 = _rodar_harness(harness(True))
        m2 = _marcas(out2)
        checar(u"e o Cancelar vale no meio de um arquivo grande",
               u"cancelado" in m2.get(u"CANCELOU", u""),
               m2.get(u"CANCELOU", (out2 or u"")[-160:]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_ler_o_filho_nao_prende_a_janela():
    secao(u"ler o filho nao prende a janela (e nao trava no stderr)")
    fs = _funcoes_ps(u"packager/prepare.ps1", [u"AcompanharProcesso"])
    corpo = fs.get(u"AcompanharProcesso", u"")
    checar(u"a funcao existe e foi recortada pelo parser", bool(corpo),
           _motivo_ast(fs))
    if not corpo:
        return
    tmp = tempfile.mkdtemp(prefix="radai_prep_filho_")
    try:
        filho = os.path.join(tmp, "filho.py")
        io.open(filho, "w", encoding="utf-8").write(
            u"import sys, time\n"
            u"time.sleep(3)\n"
            u"sys.stderr.write(('x' * 100 + '\\n') * 2000)\n"
            u"sys.stderr.flush()\n"
            u"print('fim do filho')\n"
            u"sys.exit(3)\n")
        h = (u"$ErrorActionPreference = 'Stop'\n"
             u"Set-StrictMode -Version Latest\n"
             u"$script:Linhas = New-Object System.Collections.ArrayList\n"
             u"$script:Pumps = 0\n"
             u"$script:PumpsNoSilencio = -1\n"
             u"function Registrar { param([string]$Texto, [string]$Nivel = 'info')\n"
             u"    # quantos bombeamentos houve ANTES da primeira linha -- os\n"
             u"    # que so' o relogio pode ter dado, com o filho calado\n"
             u"    if ($script:PumpsNoSilencio -lt 0) { $script:PumpsNoSilencio = $script:Pumps }\n"
             u"    [void]$script:Linhas.Add($Nivel + '|' + $Texto) }\n"
             u"function Pump { $script:Pumps++ }\n"
             + corpo + u"\n" +
             u"$psi = New-Object System.Diagnostics.ProcessStartInfo\n"
             u"$psi.FileName = '%s'\n"
             u"$psi.Arguments = '\"%s\"'\n"
             u"$psi.UseShellExecute = $false\n"
             u"$psi.RedirectStandardOutput = $true\n"
             u"$psi.RedirectStandardError = $true\n"
             u"$psi.CreateNoWindow = $true\n"
             u"$p = [System.Diagnostics.Process]::Start($psi)\n"
             u"$rc = AcompanharProcesso $p\n"
             u"'RC:' + $rc\n"
             u"'PUMPS:' + $script:PumpsNoSilencio\n"
             u"'ERRO:' + @($script:Linhas | Where-Object { $_ -like 'erro|*' }).Count\n"
             u"'FIM:' + @($script:Linhas | Where-Object { $_ -like '*fim do filho*' }).Count\n"
             % (sys.executable, filho))
        out, rc = _rodar_harness(h, timeout=60)
        checar(u"termina (sem deadlock no stderr cheio)", out is not None,
               u"esgotou 60 s: o pai espera o stdout e o filho espera alguem "
               u"ler o stderr")
        if out is None:
            return
        m = _marcas(out)
        checar(u"devolve o codigo de saida do filho", m.get(u"RC") == u"3",
               u"%s | %s" % (m.get(u"RC"), out[-200:]))
        checar(u"le as 2.000 linhas do stderr, com a cor de erro",
               m.get(u"ERRO") == u"2000", m.get(u"ERRO"))
        checar(u"e a linha do stdout", m.get(u"FIM") == u"1", m.get(u"FIM"))
        n = int(m.get(u"PUMPS") or 0)
        checar(u"e bombeia a janela durante os 3 s de silencio (%d vezes)" % n,
               n >= 15, u"com menos, o Windows marca «Nao esta respondendo»")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    fs2 = _funcoes_ps(u"packager/prepare.ps1", [u"Preparar", u"JanelaDesinstalar"])
    checar(u"`Preparar` le o motor por `AcompanharProcesso`",
           u"AcompanharProcesso $proc" in fs2.get(u"Preparar", u""))
    checar(u"`JanelaDesinstalar` le o desinstalador por ela",
           u"AcompanharProcesso $pr" in fs2.get(u"JanelaDesinstalar", u""))
    ps = ler("packager/prepare.ps1")
    codigo = u"\n".join(l for l in ps.splitlines()
                        if not l.lstrip().startswith(u"#"))
    fs3 = _funcoes_ps(u"packager/prepare.ps1", [u"RodarAtualizador"])
    checar(u"o Atualizar tambem (o atualizador e lido por `AcompanharProcesso`)",
           u"return (AcompanharProcesso $pr)" in fs3.get(u"RodarAtualizador", u"")
           and u"RodarAtualizador $pasta @('-SemPerguntar')" in codigo
           and u"RodarAtualizador $Pasta @('-SoEncerrar')" in codigo)
    checar(u"e nenhum `EndOfStream` sobrou no codigo",
           u"EndOfStream" not in codigo,
           u"`EndOfStream` bloqueia num pipe calado")


def teste_esperar_a_rede_nao_prende_a_janela():
    secao(u"esperar a rede nao prende a janela (download e versao publicada)")
    nomes = [u"EsperarSemTravar", u"BaixarSemTravar", u"VersaoPublicada",
             u"AcharOuBaixarPython", u"LigarTls12", u"RespondeuHttp"]
    fs = _funcoes_ps(u"packager/prepare.ps1", nomes)
    checar(u"as seis funcoes existem e foram recortadas pelo parser",
           set(fs) == set(nomes), u"%s%s" % (sorted(fs), _motivo_ast(fs)))
    if set(fs) != set(nomes):
        return
    import pathlib
    tmp = tempfile.mkdtemp(prefix="radai_prep_rede_")
    try:
        origem = os.path.join(tmp, "origem.bin")
        io.open(origem, "wb").write(os.urandom(300000))
        destino = os.path.join(tmp, "destino.bin")
        ausente = pathlib.Path(os.path.join(tmp, "nao_existe.bin")).as_uri()
        base = (u"$ErrorActionPreference = 'Stop'\n"
                u"Set-StrictMode -Version Latest\n"
                u"$script:Pumps = 0\n"
                u"$script:Espera = $null\n"
                u"$script:Fonte = $null\n"
                u"$script:PulsouAberta = 0\n"
                u"function Pump { $script:Pumps++\n"
                u"    if ($script:Espera -and -not $script:Espera.IsCompleted) {\n"
                u"        $script:PulsouAberta++ }\n"
                u"    if ($script:Fonte) { [void]$script:Fonte.TrySetResult($true) } }\n"
                u"function T { param([AllowEmptyString()][string]$Texto) return $Texto }\n")
        medida = (u"$script:Fonte = New-Object 'System.Threading.Tasks.TaskCompletionSource[bool]'\n"
                  u"$script:Espera = [System.Threading.Tasks.Task]::WhenAny("
                  u"[System.Threading.Tasks.Task[]]@($script:Fonte.Task, "
                  u"[System.Threading.Tasks.Task]::Delay(8000)))\n"
                  u"EsperarSemTravar $script:Espera\n"
                  u"'PULSOU:' + $script:PulsouAberta\n"
                  u"$script:Espera = $null; $script:Fonte = $null\n")
        h = (base + fs[u"EsperarSemTravar"] + u"\n" + fs[u"BaixarSemTravar"] + u"\n" +
             medida +
             u"try { EsperarSemTravar ([System.Threading.Tasks.Task]::FromException("
             u"(New-Object System.IO.IOException('proxy recusou a conexao')))); "
             u"'FALHA:nao levantou' } catch { 'FALHA:' + $_.Exception.GetType().Name + "
             u"'|' + $_.Exception.Message }\n"
             u"$cts = New-Object System.Threading.CancellationTokenSource; $cts.Cancel()\n"
             u"try { EsperarSemTravar ([System.Threading.Tasks.Task]::FromCanceled($cts.Token)); "
             u"'CANCELADA:nao levantou' } catch { 'CANCELADA:' + $_.Exception.Message }\n"
             u"try { EsperarSemTravar ([System.Threading.Tasks.Task]::Delay(6000)) 300; "
             u"'PRAZO:nao levantou' } catch { 'PRAZO:' + $_.Exception.Message }\n"
             u"BaixarSemTravar '%s' '%s'\n"
             u"'BAIXOU:' + (Get-Item -LiteralPath '%s').Length\n"
             u"try { BaixarSemTravar '%s' '%s'; 'AUSENTE:nao levantou' } catch { "
             u"'AUSENTE:' + $_.Exception.GetType().Name + '|' + $_.Exception.Message }\n"
             % (pathlib.Path(origem).as_uri(), destino, destino, ausente,
                os.path.join(tmp, "d2.bin")))
        out, _rc = _rodar_harness(h, timeout=60)
        m = _marcas(out)
        checar(u"a espera devolve a vez a janela ANTES de terminar",
               (m.get(u"PULSOU") or u"0") != u"0",
               u"PULSOU=%s -- a janela so' respirou depois da espera: e' o "
               u"`.Wait()` que a marca «Nao esta respondendo» | %s"
               % (m.get(u"PULSOU"), (out or u"")[-160:]))
        isca = (base +
                u"function EsperarSemTravar { param($Tarefa, [int]$LimiteMs = 0)\n"
                u"    try { [void]$Tarefa.Wait() } catch { }\n"
                u"    Pump }\n" + medida)
        out_i, _rc_i = _rodar_harness(isca, timeout=60)
        checar(u"  e a medida sabe reprovar (isca: `.Wait()` e depois `Pump`)",
               _marcas(out_i).get(u"PULSOU") == u"0",
               u"PULSOU=%s na isca | %s" % (_marcas(out_i).get(u"PULSOU"),
                                           (out_i or u"")[-160:]))
        checar(u"a falha levanta com a mensagem de DENTRO",
               m.get(u"FALHA", u"").startswith(u"IOException|proxy recusou"),
               m.get(u"FALHA"))
        checar(u"a tarefa cancelada levanta dizendo que foi cancelada",
               u"cancelada" in m.get(u"CANCELADA", u""), m.get(u"CANCELADA"))
        checar(u"e o prazo vence em vez de esperar para sempre",
               u"tempo esgotado" in m.get(u"PRAZO", u""), m.get(u"PRAZO"))
        checar(u"`BaixarSemTravar` baixa de verdade (file://, 300.000 bytes)",
               m.get(u"BAIXOU") == u"300000", m.get(u"BAIXOU"))
        checar(u"  e a origem que nao existe levanta com o motivo, sem estourar",
               m.get(u"AUSENTE", u"").count(u"|") == 1
               and u"nao levantou" not in m.get(u"AUSENTE", u""),
               m.get(u"AUSENTE"))

        h2 = (base + u"$script:Chamou = 0\n"
              u"function EsperarSemTravar { param($Tarefa, [int]$LimiteMs = 0)\n"
              u"    $script:Chamou++; $script:Prazo = $LimiteMs; throw 'espera dublada' }\n"
              + fs[u"VersaoPublicada"] + u"\n" + fs[u"LigarTls12"] + u"\n" +
              fs[u"RespondeuHttp"] + u"\n" +
              u"$script:VersaoLa = $null\n"
              u"$script:URL_RELEASES = 'http://127.0.0.1:9/x'\n"
              u"$c = VersaoPublicada\n"
              u"'VERSAO:' + $c.ok + '|' + $c.erro + '|' + $script:Chamou + '|' + $script:Prazo\n")
        out2, _rc2 = _rodar_harness(h2, timeout=60)
        v = (_marcas(out2).get(u"VERSAO") or u"").split(u"|")
        checar(u"`VersaoPublicada` espera a rede por `EsperarSemTravar`, com prazo",
               len(v) == 4 and v[2] == u"1" and int(v[3] or 0) > 0,
               (out2 or u"")[-200:])
        checar(u"  e devolve o erro da espera como motivo, sem levantar",
               len(v) == 4 and v[0] == u"False" and v[1] == u"espera dublada", v)

        h3 = (base + u"$script:Baixou = ''\n"
              u"function Get-Command { throw 'sem python no PATH' }\n"
              u"function Registrar { param($Texto, $Nivel) }\n"
              u"function Falhar { param($Texto) $script:Falhou = $Texto }\n"
              u"$script:Falhou = ''\n"
              u"function BaixarSemTravar { param($Url, $Destino)\n"
              u"    $script:Baixou = $Url\n"
              u"    [System.IO.File]::WriteAllBytes($Destino, (New-Object byte[] 10)) }\n"
              + fs[u"AcharOuBaixarPython"] + u"\n" +
              u"$r = AcharOuBaixarPython '%s'\n"
              u"'PYTHON:' + $script:Baixou + '|' + ($null -eq $r) + '|' + "
              u"($script:Falhou -replace \"[`r`n]+\", ' ')\n" % tmp)
        out3, _rc3 = _rodar_harness(h3, timeout=60)
        p3 = (_marcas(out3).get(u"PYTHON") or u"").split(u"|")
        checar(u"`AcharOuBaixarPython` baixa o Python por `BaixarSemTravar`",
               len(p3) >= 3 and p3[0].startswith(u"https://www.python.org/"),
               (out3 or u"")[-200:])
        checar(u"  e o download curto demais e' recusado com motivo",
               len(p3) >= 3 and p3[1] == u"True" and u"bytes" in p3[2], p3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_sem_url_rolante():
    secao(u"nenhuma URL rolante (hash fixo exige origem imutavel)")
    import artefatos as A

    bruto = ler("build/configurar_ambiente.py")
    cfg = u"\n".join(l for l in bruto.splitlines()
                     if not l.lstrip().startswith("#"))

    ROLANTES = (u"bootstrap.pypa.io/get-pip.py",
                u"bootstrap.pypa.io/pip/",
                u"/releases/latest/",
                u"githubusercontent.com/[^\"']*/(?:master|main)/")
    achados = [r for r in ROLANTES if re.search(r, cfg)]
    checar(u"nenhuma URL rolante conhecida no configurador",
           not achados, str(achados))

    checar(u"o pip vem da roda do PyPI", u"files.pythonhosted.org" in cfg)
    checar(u"e o get-pip.py nao e mais baixado",
           u"bootstrap.pypa.io" not in cfg)

    roda = [k for k in A.ARTEFATOS if k.endswith(".whl")]
    checar(u"a roda do pip esta na tabela de artefatos", len(roda) == 1,
           str(roda))
    if roda:
        checar(u"e ela declara que o hash veio da origem",
               A.ARTEFATOS[roda[0]].get("origem_publica_o_hash") is True)

    checar(u"o GUARDA: registra a licao do artefato rolante",
           any(u"GUARDA:" in l and u"rolante" in l
               for l in ler("build/artefatos.py").splitlines()))

    checar(u"o pip e instalado extraindo a roda em site-packages",
           u"site-packages" in cfg and u"zipfile.ZipFile(roda)" in cfg)
    checar(u"e o pip e testado logo depois",
           u'rodar([py, "-m", "pip", "--version"]' in cfg)

    com = ler("packager/START_HERE.cmd")
    checar(u"o ramo 1 mostra a data da copia instalada",
           u"%%~tF" in com and u"Esta copia e de" in com)
    checar(u"e diz que quem atualiza e o .cmd da pasta extraida",
           u"DE DENTRO DA PASTA EXTRAIDA" in com
           or u"FROM INSIDE THE EXTRACTED FOLDER" in com)

    import configurar_ambiente as C
    checar(u"a barra de progresso vira ASCII na captura",
           callable(getattr(C, "_sem_bloco", None)))
    if hasattr(C, "_sem_bloco"):
        bloco = u"Downloading:  57%|████▋    | 132M/234M"
        saida = C._sem_bloco(bloco)
        checar(u"nenhum bloco Unicode sobra",
               not any(0x2580 <= ord(c) < 0x25A0 for c in saida), saida[:50])
        checar(u"e o preenchimento se distingue da moldura",
               u"#" in saida and u"|#" in saida, saida[:50])
        checar(u"acento e pontuacao passam intactos",
               C._sem_bloco(u"ATENÇÃO · licença")
               == u"ATENÇÃO · licença")

    p = ler("packager/prepare.ps1")
    checar(u"o preparador manda o Python escrever em UTF-8",
           u"PYTHONIOENCODING" in p)
    checar(u"E LE a saida em UTF-8 (senao todo acento quebra)",
           u"$pi.StandardOutputEncoding" in p and u"$pi.StandardErrorEncoding" in p)


def teste_manifesto():
    secao(u"o manifesto atende a RDC 657/2022 na mesma escrita")
    emp = ler("build/configurar_ambiente.py")
    checar(u"existe a funcao do manifesto", u"def _escrever_manifesto(" in emp)
    checar(u"ele cita a RDC 657", u"657" in emp)
    checar(u"e entra no pacote", u'("MANIFESTO.txt", manifesto)' in emp)

    import artefatos as A
    linha = A.linha_manifesto(sorted(A.ARTEFATOS)[0])
    checar(u"a entrada traz o sha256 INTEIRO (64 hexa)",
           re.search(r"[0-9a-f]{64}", linha) is not None, linha[:60])
    checar(u"e ela quebra em varias linhas (caminho longo nao corta o hash)",
           linha.count("\n") >= 2, repr(linha[:50]))

    gerado = os.path.join(RAIZ, "_montagem", "MANIFESTO.txt")
    if os.path.isfile(gerado):
        t = io.open(gerado, encoding="utf-8", errors="replace").read()
        checar(u"o manifesto gerado tem as versoes fixadas", u"VERSOES FIXADAS" in t)
        checar(u"tem a secao de licencas", u"LICENCAS" in t)
        checar(u"marca a restritiva", u"[RESTRITIVA]" in t)
        checar(u"tem soma de verificacao", re.search(r"[0-9a-f]{64}", t) is not None)
        checar(u"diz a retencao de dez anos", u"DEZ ANOS" in t)
    else:
        print(u"  (pulado: manifesto ainda nao gerado nesta maquina)")


def teste_link_de_licenca_leva_a_licenca():
    secao(u"todo link de licenca leva a um texto de licenca")
    ps1 = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                  encoding="utf-8-sig", errors="replace").read()
    urls = re.findall(r"url\s*=\s*'([^']+)'", ps1)
    checar(u"a tela declara os links", len(urls) >= 8, len(urls))

    raizes = [u for u in urls
              if re.match(r"^https?://[^/]+/?$", u.strip())]
    checar(u"nenhum aponta para a raiz de um site", not raizes, raizes)

    downloads = [u for u in urls if "/downloads/" in u or "/download/" in u]
    checar(u"nenhum e' pagina de download", not downloads, downloads)

    RAMO_CERTO = {
        "MIC-DKFZ/nnInteractive": "master",
        "MIC-DKFZ/nnUNet": "master",
        "wasserth/TotalSegmentator": "master",
        "Project-MONAI/VISTA": "main",
        "pytorch/pytorch": "main",
    }
    for u in urls:
        for repo, ramo in RAMO_CERTO.items():
            if repo in u and "/blob/" in u:
                checar(u"  %s usa o ramo `%s`" % (repo, ramo),
                       ("/blob/%s/" % ramo) in u,
                       u"%s -- ramo errado devolve 404" % u)

    monai = [u for u in urls if "Project-MONAI/VISTA" in u and "/blob/" in u]
    for u in monai:
        checar(u"  o link do MONAI aponta LICENSE.txt", u.endswith(".txt"), u)

    genericos = [u for u in urls
                 if "creativecommons.org" in u and "/blob/" not in u]
    checar(u"nenhum e' texto generico de licenca, sem o autor",
           not genericos,
           u"%s -- leve ao repositorio, onde o autor a declara" % genericos)


def teste_o_preparador_acha_o_bundle_que_o_motor_produz():
    secao(u"o preparador acha o bundle que o motor produz")
    import fnmatch

    engine = ler("build/configurar_ambiente.py")
    m = re.search(r'\("(%s_BUNDLE_v%s\.zip)"\s*%', engine)
    checar(u"o motor compoe o nome do bundle", bool(m),
           u"procurei o `%s_BUNDLE_v%s.zip` em configurar_ambiente.py")

    campos = {}
    for linha in io.open(os.path.join(RAIZ, "entrega.txt"),
                         encoding="utf-8-sig").read().splitlines():
        if "=" in linha and not linha.strip().startswith("#"):
            k, v = linha.split("=", 1)
            campos[k.strip()] = v.strip()
    produto = campos.get("PRODUTO") or campos.get("PROJETO") or u""
    versao = campos.get("VERSAO") or u""
    checar(u"o entrega.txt declara PRODUTO e VERSAO",
           bool(produto and versao), campos)
    nome = u"%s_BUNDLE_v%s.zip" % (produto, versao)

    ps1 = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                  encoding="utf-8-sig", errors="replace").read()
    bloco = ps1[ps1.find("$todos = @(Get-ChildItem"):][:900]
    padroes = re.findall(r"-like\s+'([^']+)'", bloco)
    checar(u"o preparador declara padroes de busca", bool(padroes), bloco[:120])

    casou = [p for p in padroes if fnmatch.fnmatch(nome, p)]
    checar(u"e ao menos um casa com `%s`" % nome, bool(casou),
           u"padroes: %s — o defeito de campo foi exatamente este"
           % u", ".join(padroes))

    velho = u"AUTO_CONTORNO_BUNDLE_v2.0.zip"
    checar(u"e o nome antigo tambem e' reconhecido",
           any(fnmatch.fnmatch(velho, p) for p in padroes), padroes)

    checar(u"ha recuo para o maior .zip quando nenhum padrao casa",
           u"if (-not $zip)" in bloco or u"if (-not $zip)" in ps1)

    checar(u"a tela final trata pacote nao localizado",
           u"} elseif (-not $Zip) {" in ps1,
           u"sem isto, `Split-Path -Leaf ''` vira 'Erro inesperado'")


def teste_o_montador_acha_o_que_o_pacote_leva():
    secao(u"o pacote leve leva o que a montagem le da raiz")
    fonte = ler("build/configurar_ambiente.py")

    lidos = set(re.findall(r'RAIZ / "([^"/]+\.[a-z]+)"', fonte))
    for _tupla in re.findall(r'for nome in \(([^)]*)\):\s*\n\s*origem = RAIZ / nome', fonte):
        lidos |= set(re.findall(r'"([^"/]+)"', _tupla))
    checar(u"a montagem le ao menos um arquivo da raiz", len(lidos) >= 1,
           u", ".join(sorted(lidos)))

    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import empacotar_instalador as E
    leva = set(E.ARQUIVOS) | {p[0] for p in E.PASTAS}

    for nome in sorted(lidos):
        checar(u"a montagem le `%s`, e o pacote o leva" % nome,
               nome in leva,
               u"nao esta em ARQUIVOS de empacotar_instalador.py")

    conh = E.versionados(RAIZ)
    checar(u"o empacotador le o que o Git conhece",
           conh is not None and u"app/radai_version.py" in conh)
    falso = [(u"tools/test_x.py", os.path.join(RAIZ, "tools", "test_x.py")),
             (u"tools/test_x (1).py", os.path.join(RAIZ, "tools", "test_x (1).py"))]
    try:
        E.conferir_versionados(falso, RAIZ, {u"tools/test_x.py"})
        checar(u"(isca) a copia de conflito do Drive, nao versionada, PARA o pacote", False)
    except SystemExit as e:
        checar(u"(isca) a copia de conflito do Drive, nao versionada, PARA o pacote",
               u"test_x (1).py" in str(e), str(e)[:200])
    try:
        E.conferir_versionados(falso[:1], RAIZ, {u"tools/test_x.py"})
        checar(u"  e o versionado passa", True)
    except SystemExit as e:
        checar(u"  e o versionado passa", False, str(e)[:200])
    _repo = tempfile.mkdtemp(prefix="radai_pkg_trava_")
    try:
        subprocess.run(["git", "init", "-q", _repo], check=True,
                       capture_output=True)
        with open(os.path.join(_repo, ".gitignore"), "w") as _f:
            _f.write("_montagem/\n")
        _app = os.path.join(_repo, "_montagem", "componentes", "X", "app")
        os.makedirs(_app)
        with open(os.path.join(_app, "radai_x.py"), "w") as _f:
            _f.write("x = 1\n")
        _pasta_x = os.path.dirname(_app)
        checar(u"o app baixado da trava, extraido dentro de outro repositorio, "
               u"nao e lido como «nada versionado»",
               E.versionados(_pasta_x) is None and E.versionados(_repo) is not None)
        _ls = subprocess.run(["git", "-C", _pasta_x, "ls-files", "-z"],
                             capture_output=True).stdout
        checar(u"  (isca) o ls-files de dentro da pasta extraida responde vazio, "
               u"e pararia o pacote", _ls == b"")
        _antes = os.environ.get("RADAI_COMPONENTES_DIR")
        os.environ["RADAI_COMPONENTES_DIR"] = os.path.dirname(_pasta_x)
        try:
            checar(u"  e e reconhecido como baixado da trava (conferido pelo sha256)",
                   E.baixado_da_trava(_pasta_x)
                   and not E.baixado_da_trava(RAIZ))
        finally:
            if _antes is None:
                os.environ.pop("RADAI_COMPONENTES_DIR", None)
            else:
                os.environ["RADAI_COMPONENTES_DIR"] = _antes
    finally:
        shutil.rmtree(_repo, ignore_errors=True)
    try:
        _nomes_leve = [n for n, _c in E.coletar()]
    except SystemExit as _e:
        _nomes_leve = []
        checar(u"o empacotador coleta o instalador leve", False, str(_e))
    checar(u"o preparo da porta (npm) nao viaja; o porta.js pronto, sim",
           not any(n.startswith(u"build/porta/") for n in _nomes_leve)
           and u"app/porta/porta.js" in _nomes_leve)
    import artefatos as _art
    _emp = ler("build/empacotar_instalador.py")
    checar(u"a demo saiu do produto: nem baixador, nem lembrete de asset na release",
           not hasattr(_art, "demo_na_release") and not hasattr(_art, "DEMO")
           and u"demo_na_release" not in _emp
           and u"instalar_demo" not in fonte
           and not os.path.exists(os.path.join(RAIZ, "tools", "demos.py")))
    checar(u"  (isca) a busca acharia o baixador se ele voltasse",
           u"instalar_demo" in u"def instalar_demo(ctx):")
    checar(u"o cache por task nao entra",
           not E.entra(u"cache_tasks/ab/rotulos.npz"))
    for nome in (u"app/cache_tasks/ab/rotulos.npz", u"tools/mascara.nii.gz"):
        try:
            E.conferir_sem_phi([(nome, u"x")])
            checar(u"(isca) `%s` no pacote PARA" % nome, False)
        except SystemExit:
            checar(u"(isca) `%s` no pacote PARA" % nome, True)

    checar(u"a verificacao profunda saiu da instalacao: o verify.cmd nao viaja "
           u"no instalador leve", "verify.cmd" not in E.ARQUIVOS, E.ARQUIVOS)
    _ess = fonte[fonte.index(u"def etapa_distribuir("):]
    _ess = _ess[:_ess.index(u"\ndef ", 1)]
    checar(u"  nem a etapa 5 o poe em maintenance/, nem o pacote o exige",
           u"verify.cmd" not in fonte[fonte.index(u"def etapa_app("):
                                      fonte.index(u"def etapa_validar(")]
           and u"verify.cmd" not in _ess)
    checar(u"o desinstalador continua indo para maintenance/",
           'ferramentas / desinst' in fonte)


def teste_contrato():
    secao(u"o pacote respeita o contrato, e os arquivos as regras do Windows")
    ps1 = os.path.join(RAIZ, "packager", "prepare.ps1")
    cmd = os.path.join(RAIZ, "packager", "PREPARAR_AUTO_CONTORNO.cmd")

    bruto = io.open(cmd, "rb").read()
    checar(u"o .cmd esta em CRLF",
           bruto.count(bytes([13, 10])) > 10
           and bruto.count(bytes([10])) == bruto.count(bytes([13, 10])),
           u"%d CRLF de %d LF" % (bruto.count(bytes([13, 10])),
                                  bruto.count(bytes([10]))))
    linhas_cmd = [l.strip().lower()
                  for l in bruto.decode("ascii", "replace").split("\n")]
    chcp_comando = [l for l in linhas_cmd
                    if l.startswith("chcp") or l.startswith("@chcp")]
    checar(u"o .cmd nao EXECUTA chcp", not chcp_comando, str(chcp_comando[:2]))
    checar(u"o cabecalho do .cmd e ASCII puro",
           all(b < 128 for b in bruto[:400]))
    checar(u"o .cmd tem pause", b"pause" in bruto.lower(),
           u"janela que pisca e fecha nao e diagnosticavel")

    b = io.open(ps1, "rb").read()
    tem_bom = b[:3] == b"\xef\xbb\xbf"
    so_ascii = all(x < 128 for x in b)
    checar(u"o .ps1 e ASCII puro OU tem BOM", so_ascii or tem_bom,
           u"ascii=%s bom=%s" % (so_ascii, tem_bom))

    checar(u"o instalador vai para C:\\RADIOTERAPIA_AI",
           u"RADIOTERAPIA_AI" in ler("installer/INSTALL.ps1"))
    checar(u"e registra em _instalados.json",
           u"_instalados.json" in ler("installer/INSTALL.ps1"))
    inst = ler("installer/INSTALL.ps1")
    checar(u"o registro e LIDO antes de gravar",
           u"ReadAllText($REGISTRO" in inst or u"Get-Content" in inst)
    checar(u"e lido com encoding explicito (5.1 le UTF-8 como ANSI)",
           u"System.Text.Encoding]::UTF8" in inst)

    com = ler("packager/START_HERE.cmd")
    checar(u"o START_HERE existe", bool(com))
    checar(u"NAO detecta pelo nome da pasta temporaria",
           u"^Temp[0-9][0-9]*_" not in com,
           u"nome de pasta do Explorer muda entre versoes do Windows")
    checar(u"detecta pela existencia de programa" + u"\\",
           u"programa" + u"\\" + u"packager" + u"\\" + u"prepare.ps1" in com)

    checar(u"a casa fica no TEMP, e nao no C:",
           u'set "CASA=%TEMP%' in com,
           u"pasta de trabalho no C: fica la para sempre")
    checar(u"e ela nao leva o nome antigo do produto",
           u"CASA=C:" not in com)
    checar(u"1) rodando ja da casa, nao recopia",
           u'if /i "%AQUI%"=="%CASA%"' in com)
    checar(u"2) com o programa ao lado, copia para a casa",
           u'xcopy "%AQUI%' + u"\\" + u'*" "%CASA%' + u"\\" + u'"' in com)
    checar(u"(a) pergunta ao Explorer qual .zip esta aberto",
           u"Shell.Application" in com and u"Document.Folder.Self.Path" in com)
    checar(u"(b) procura nas pastas de download E na raiz de cada disco",
           u"Downloads" in com and u"Get-PSDrive -PSProvider FileSystem" in com,
           u"raiz de disco cobre o pendrive, que e como isto viaja")
    checar(u"(c) e, falhando os dois, PERGUNTA com um seletor de arquivo",
           u"OpenFileDialog" in com,
           u"os dois primeiros sao palpites; este nao")
    checar(u"o seletor roda em -STA (senao ele nao abre)",
           u"-STA -Command" in com)
    checar(u"e avisa antes de o seletor aparecer",
           u"abro uma janela" in com or u"open a window" in com,
           u"seletor que aparece sem aviso parece travamento")
    checar(u"e nao culpa a pessoa por uma pasta que ela nao criou",
           u"Nao achei a pasta preparador" not in com)
    checar(u"a busca e INLINE, nao num .ps1 ao lado",
           u"achar_pacote.ps1" not in com,
           u"clicando de dentro do zip, so' o .cmd e extraido")
    checar(u"e extrai com Expand-Archive (lote nao descompacta)",
           u"Expand-Archive" in com)
    checar(u"nao conseguindo criar a casa, roda no lugar mesmo",
           u"rodar daqui mesmo" in com
           or u"Running from here instead" in com
           or u"run from here instead" in com)
    checar(u"e se nao achar o .zip, diz os quatro passos",
           (u"NAO ACHEI O PACOTE" in com and u"Extrair Tudo" in com)
           or (u"PACKAGE NOT FOUND" in com and u"Extract All" in com))
    checar(u"e tem pause em todos os caminhos",
           com.count(u"pause") >= 4, u"%d pause(s)" % com.count(u"pause"))

    raizleia = ler("packager/README-ROOT.txt")
    checar(u"o LEIA-ME da raiz manda EXTRAIR antes", u"Extraia este .zip" in raizleia)
    checar(u"e diz por que (o Windows nao executa de dentro do zip)",
           u"nao executa programa de dentro" in raizleia)
    checar(u"aponta o unico clique", u"START_HERE.cmd" in raizleia)
    import artefatos as _art
    _restr = list(_art.restritivas())
    _corrido = u" ".join(raizleia.split())
    if _restr:
        checar(u"e avisa do componente nao comercial (%d no registro)"
               % len(_restr), u"NAO COMERCIAL" in _corrido)
    else:
        checar(u"e NAO anuncia componente nao comercial (o registro nao tem)",
               u"NAO COMERCIAL" not in _corrido,
               u"o LEIA-ME afirma uma restricao que o pacote nao tem")

    leia = ler("packager/README.txt")
    for t in (u"Desbloquear", u"ExecutionPolicy Bypass", u"diretiva de dominio"):
        checar(u"o LEIA-ME tecnico cobre: %s" % t, t in leia)
    checar(u"o LEIA-ME avisa de nao clicar de dentro do zip",
           u"EXTRAIA" in leia or u"nao de dois cliques" in leia.lower())


def teste_guarda_da_nuvem():
    secao(u"o destino do download nao pode sincronizar com a nuvem")
    ps = ler("packager/prepare.ps1")

    checar(u"existe deteccao de raiz espelhada", u"function RaizesEspelhadas" in ps)
    checar(u"e ela LE A CONFIGURACAO DO DRIVE",
           u"root_preference_sqlite.db" in ps,
           u"lista fixa de tres pastas envelhece em silencio")
    checar(u"le sobre uma COPIA (o original fica travado)",
           u"Copy-Item -LiteralPath $db" in ps)

    checar(u"apara o lixo do byte cru ate achar pasta que existe",
           u"function AparaAtePasta" in ps and u"PathType Container" in ps)
    checar(u"e tem piso, para nao descer ate a raiz do disco",
           u"$c.Length -gt 3" in ps,
           u"sem piso, um candidato morto desce ate a raiz do disco e recusa tudo")

    checar(u"compara prefixo COM a barra (nao casa AI_IMPORTANTE)",
           u"$r + '" + u"\\" + u"'" in ps)

    corpo = ps[ps.index(u"function Preparar {"):]
    checar(u"o guarda roda ANTES de qualquer download",
           corpo.index(u"DestinoSincroniza $trab") < corpo.index(u"AcharOuBaixarPython $pyDir"),
           u"depois do primeiro byte ja e tarde: o Drive comeca a subir")
    checar(u"e ele PARA, nao apenas avisa",
           u"$espelho) {" in ps and u"Falhar (" in ps)
    checar(u"a pasta de trabalho e escolhida pelo usuario, nao constante",
           u"FolderBrowserDialog" in ps and u"$cxPasta" in ps)
    checar(u"o destino padrao e o perfil do usuario, fora das tres raizes",
           u"PACOTE_SUGERIDO = Join-Path $env:USERPROFILE" in ps)


def teste_reexibicao():
    secao(u"quem instala ve as licencas, e confirma")
    inst = ler("installer/INSTALL.ps1")

    checar(u"o instalador procura o LICENCAS_ACEITAS.txt",
           u"$ARQ_LICENCAS = Join-Path $AQUI 'LICENCAS_ACEITAS.txt'" in inst)
    checar(u"e exibe o conteudo", u"$txtLic" in inst and u"Write-Host" in inst)
    checar(u"destaca a restricao de uso quando existe",
           u"RESTRICAO DE USO" in inst and u"NAO COMERCIAL" in inst)
    checar(u"pede confirmacao", u"Read-Host" in inst)
    checar(u"recusar CANCELA a instalacao",
           u"Instalacao cancelada" in inst)
    checar(u"e diz a saida: preparar pacote sem o componente",
           u"prepare um pacote novo SEM ele" in inst)

    checar(u"sem console, RECUSA em vez de presumir",
           u"Nao ha console para confirmar as licencas" in inst)
    checar(u"quem automatiza declara por variavel de ambiente",
           u"RADAI_LICENCAS_ACEITAS" in inst)
    checar(u"o log distingue automatizado de confirmado no console",
           u"'automatizado'" in inst and u"'confirmado_no_console'" in inst,
           u"registro que nao distingue e registro que mente")

    checar(u"pacote sem o arquivo avisa e segue",
           u"nao traz LICENCAS_ACEITAS.txt" in inst)
    checar(u"e a ausencia fica anotada no log",
           u"licencas_reexibidas=arquivo_ausente" in inst)

    emp = ler("build/configurar_ambiente.py")
    checar(u"e o aceite viaja no .zip para poder ser reexibido",
           u'("LICENCAS_ACEITAS.txt", aceite)' in emp)


def teste_icone_e_atalhos():
    secao(u"o icone, e os atalhos que o usam")

    ico = _componentes.fonte("app/radioterapia_ai.ico")
    checar(u"o .ico existe em app/", os.path.isfile(ico))
    if os.path.isfile(ico):
        b = io.open(ico, "rb").read()
        checar(u"e um ICO de verdade (cabecalho)", b[:4] == b"\x00\x00\x01\x00",
               repr(b[:4]))
        qtd = b[4] | (b[5] << 8)
        checar(u"traz varias resolucoes", qtd >= 6, u"%d resolucao(oes)" % qtd)
        larguras = sorted({b[6 + 16 * i] for i in range(qtd)})
        checar(u"tem a entrada de 256 (gravada como 0)", 0 in larguras,
               str(larguras))
        checar(u"e as pequenas, que sao as da barra de tarefas",
               16 in larguras and 32 in larguras, str(larguras))

    fav = _componentes.fonte("app/favicon.ico")
    checar(u"o favicon.ico existe em app/", os.path.isfile(fav))
    if os.path.isfile(fav):
        b = io.open(fav, "rb").read()
        checar(u"  e e' um ICO de verdade (cabecalho)",
               b[:4] == b"\x00\x00\x01\x00", repr(b[:4]))
        qtd = b[4] | (b[5] << 8)
        larguras = sorted({b[6 + 16 * i] for i in range(qtd)})
        checar(u"  com a de 256 e as pequenas da barra de tarefas",
               0 in larguras and 16 in larguras and 32 in larguras,
               str(larguras))

    inst = ler("installer/INSTALL.ps1")
    checar(u"o instalador cria atalho na area de trabalho",
           u'GetFolderPath("Desktop")' in inst)
    checar(u"e no menu Iniciar DO USUARIO (a pasta comum exigiria admin)",
           u'GetFolderPath("Programs")' in inst)
    checar(u"o nome e o do produto, que e o que se digita na busca",
           u"Auto Contorno - Radioterapia.ai.lnk" in inst)
    checar(u"os atalhos apontam para o start_watcher.cmd",
           u'$s.TargetPath       = $alvo' in inst)
    checar(u"e usam o icone quando ele veio no pacote",
           u"$s.IconLocation = ($icone + ',0')" in inst)
    checar(u"  e o favicon.ico vem antes do nome velho",
           u'@("favicon.ico", "radioterapia_ai.ico")' in inst)
    checar(u"falha de atalho nao derruba a instalacao",
           u"nao consegui criar o atalho em" in inst and u"Anote (" in inst)
    checar(u"e o motivo fica anotado no log",
           u'Anote ("atalho " + $d.rotulo + " falhou: "' in inst)

    emp = ler("build/configurar_ambiente.py")
    emp_cod = u"\n".join(l for l in emp.splitlines()
                         if not l.lstrip().startswith(u"#"))
    checar(u"o empacotador leva todo .ico de app/ para dentro do pacote",
           u'p.suffix.lower() in (".ico", ".png", ".svg")' in emp_cod,
           u"sem ele o atalho fica com o icone generico de .cmd")
    upd = ler("packager/UPDATE.ps1")
    checar(u"e o ATUALIZAR tambem copia .ico",
           u'".ico"' in upd.split(u"$EXT_APP", 1)[-1][:200])



def teste_pacote_do_preparador():
    secao(u"o pacote que o usuario baixa: codigo, sem peso")
    pub = ler("build/empacotar_instalador.py")
    checar(u"o empacotador monta o pacote do preparador",
           u"START_HERE.cmd" in pub)
    com = ler("packager/START_HERE.cmd")
    checar(u"o START_HERE procura por PADRAO, e nao por nome exato",
           u"_v*.zip" in com,
           u"sem curinga, a busca envelhece a cada versao")
    checar(u"e procura o nome do produto",
           u"RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_*.zip" in com)
    checar(u"e o nome anterior tambem e procurado",
           u"RADIOTERAPIA_AI_LOCAL_SUITE_INSTALADOR_v*.zip" in com,
           u"quem tem o .zip da versao passada em Downloads para de ser achado")
    checar(u"e o padrao de hoje acha o `_SETUP_LATEST.zip`",
           u"RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_*.zip" in com
           and u"RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v*.zip" not in com)
    checar(u"e ainda aceita o nome antigo",
           u"AUTO_CONTORNO*.zip" in com,
           u"quem ja baixou nao fica sem instalar por renomeacao nossa")
    checar(u"e o laco percorre os nomes um a um (array nao serve)",
           u"foreach($nm in $n)" in com)
    for pasta in ("packager", "build", "app", "tools", "installer"):
        checar(u"o pacote leva a pasta %s" % pasta, pasta in pub)
    checar(u"e os avulsos da raiz (entrega.txt, LICENSE, NOTICE)",
           all(u'"%s"' % x in pub
               for x in ("entrega.txt", "LICENSE", "NOTICE")))
    checar(u"e tira o __pycache__", u"__pycache__" in pub)
    checar(u"confere que o zip saiu, e aborta se nao",
           u"nao consegui montar o pacote do preparador" in pub)

    import zipfile
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import destino_de_entrega as _DE
    try:
        pasta = str(_DE.raiz_de_entrega(u"AUTO_CONTORNO", de=RAIZ)[0]
                    / u"AUTO_CONTORNO" / u"v2.0")
    except SystemExit:
        pasta = u""
    zipp = None
    if pasta and os.path.isdir(pasta):
        for n in sorted(os.listdir(pasta)):
            if not n.lower().endswith(".zip"):
                continue
            p = os.path.join(pasta, n)
            try:
                with zipfile.ZipFile(p) as z:
                    l = z.namelist()
                if "START_HERE.cmd" in l and any(
                        x.startswith("programa/") for x in l):
                    zipp = p
                    break
            except (zipfile.BadZipFile, OSError):
                continue
    if zipp is None:
        print(u"  (pulado: nao ha pacote do preparador nesta maquina)")
        return
    print(u"  (pacote achado por marca: %s)" % os.path.basename(zipp))
    with zipfile.ZipFile(zipp) as z:
        nomes = z.namelist()

    raiz = sorted(n for n in nomes if "/" not in n.rstrip("/") and n.strip("/"))
    executaveis = [n for n in raiz if n.lower().endswith((".cmd", ".bat", ".exe", ".ps1"))]
    checar(u"a raiz tem UM executavel", len(executaveis) == 1, str(raiz))
    checar(u"e ele se chama START_HERE.cmd",
           executaveis == ["START_HERE.cmd"], str(executaveis))
    checar(u"o verify.cmd NAO esta na raiz",
           "verify.cmd" not in raiz,
           u"e o runner de testes; na raiz ele vira o botao errado")
    checar(u"a raiz tem o LEIA-ME do usuario", "LEIA-ME.txt" in raiz, str(raiz))
    checar(u"e as duas licencas, que a Apache-2.0 exige preservar",
           "LICENSE" in raiz and "NOTICE" in raiz, str(raiz))
    checar(u"a raiz nao tem mais nada solto", len(raiz) == 4, str(raiz))

    for n in ("programa/packager/prepare.ps1",
              "programa/build/configurar_ambiente.py",
              "programa/build/artefatos.py",
              "programa/installer/INSTALL.ps1",
              "programa/app/radioterapia_ai.ico",
              "programa/entrega.txt", "programa/verify.cmd"):
        checar(u"o pacote tem %s" % n, n in nomes)
    checar(u"o START_HERE nao esta duplicado dentro de programa",
           "programa/packager/START_HERE.cmd" not in nomes)
    pesados = [n for n in nomes if n.endswith((".pth", ".pt"))]
    checar(u"NENHUM peso de modelo no pacote", not pesados, str(pesados[:2]))
    checar(u"nenhum __pycache__ no pacote",
           not [n for n in nomes if "__pycache__" in n])
    tam = os.path.getsize(zipp)
    checar(u"cabe em 50 MB (%.1f MB)" % (tam / 1048576.0), tam < 50 * 1048576,
           u"%d bytes" % tam)


def teste_interface():
    secao(u"a tela: acentos, rolagem, roteamento e o botao de procurar")
    ps = ler("packager/prepare.ps1")
    bruto = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"), "rb").read()

    tem_acento = any(b > 127 for b in bruto[3:])
    tem_bom = bruto[:3] == bytes([0xEF, 0xBB, 0xBF])
    checar(u"tem acento (o texto e em portugues de verdade)", tem_acento)
    checar(u"e por isso tem BOM", (not tem_acento) or tem_bom,
           u"acento sem BOM fecha string no meio no PowerShell 5.1")

    checar(u"o texto longo tem rolagem vertical",
           u"$t.ScrollBars = 'Vertical'" in ps)
    checar(u"e o log tambem", u"$script:CaixaLog.ScrollBars = 'Vertical'" in ps)
    checar(u"a lista de licencas rola", u"$rolo2.AutoScroll = $true" in ps)

    checar(u"a marca do cabecalho e' PINTADA (sem os dois rotulos)",
           u"function PintarMarcaDoCabecalho" in ps
           and u"$mMarca.Add_Paint(" in ps
           and u"NovoRotulo 'Radioterapia'" not in ps
           and u"(26 + $larguraAuto) 16" not in ps,
           u"os dois Label somavam a folga dos dois lados")
    _fn = ps[ps.find(u"function PintarMarcaDoCabecalho"):]
    _fn = _fn[:_fn.find(u"\n}") + 2]
    checar(u"  e mede com GenericTypographic (sem folga em volta da palavra)",
           u"GenericTypographic" in _fn and u"MeasureString($t.Palavra" in _fn,
           _fn[:120])
    checar(u"  e as duas metades sao a marca inteira",
           u"Palavra = 'Radioterapia'; Sufixo = '.ai Local Suite'" in ps)
    checar(u"a altura da linha de licenca vem do texto (nome, licenca, o que permite, origem)",
           u"$alturaDaLinha = [Math]::Max(44, $alturaDoTexto + 10)" in ps
           and u"$g.MeasureString($par[0], $par[1], [int]$par[2])" in ps
           and u"(T $L.permite), (Fonte 8), $col[2].l" in ps)

    checar(u"pergunta se esta maquina e a estacao de uso",
           u"ESTA MÁQUINA É A ESTAÇÃO DE USO?" in ps)
    checar(u"e so libera o passo seguinte depois da resposta",
           u"$bt1.Enabled = $false" in ps and u"$bt1.Enabled = $true" in ps)
    checar(u"a sugestao de pasta MUDA conforme a resposta",
           u"function AtualizarSugestaoPasta" in ps
           and u"$script:EstacaoFinal -eq $true" in ps)
    checar(u"instalar nesta maquina sugere a PASTA DO PROGRAMA, e nao uma «preparo»",
           u"$cxPasta.Text = (PastaDoProgramaSugerida)" in ps
           and u"$cxPasta.Text = $script:PREPARO_SUGERIDO" not in ps)
    checar(u"  e o motor monta direto nela; o INSTALL.ps1 so faz atalhos e registro",
           u"$argumentos = @($motor, '--instalar', $trab)" in ps
           and u"InstalarNoLugar $trab" in ps)
    checar(u"e sendo estacao, ele INSTALA sozinho ao terminar",
           u"function InstalarAqui" in ps and u"InstalarAqui $script:PacoteFinal" in ps)

    checar(u"o passo 3 tem botao de procurar pasta",
           u"FolderBrowserDialog" in ps and u"$btPasta" in ps)
    checar(u"e o dialogo deixa criar pasta nova",
           u"$d.ShowNewFolderButton = $true" in ps)

    checar(u"a tela 4 muda conforme a resposta do passo 1",
           u"ESTA É A ESTAÇÃO DE USO" in ps and u"AGORA LEVE PARA A ESTAÇÃO" in ps)
    checar(u"e abre a pasta do pacote com o arquivo selecionado",
           u"explorer.exe" in ps and u"/select," in ps)

    codigo = u"\n".join(l for l in ps.splitlines()
                        if not l.lstrip().startswith(u"#"))
    checar(u"o texto da aba 1 leva o tamanho do catalogo",
           u"(GBInteiro $script:DownloadGB), (GBInteiro $script:PacoteGB)"
           in codigo)
    velhos = [n for n in (u"5,5 GB", u"8,4 GB", u"12,7 GB", u"12,6 GB",
                          u"20 GB livres", u"3,1 GB")
              if n in codigo]
    checar(u"e nenhum numero velho ficou escrito no codigo", not velhos,
           u"%s -- numero escrito a mao envelhece na primeira task nova"
           % velhos)

    checar(u"nao afirma que a estacao nunca tem administrador",
           u"nunca tem" not in ps)


def teste_abrir():
    secao(u"RADIOTERAPIA_AI_LOCAL_SUITE.cmd: o nome que a pessoa procura")
    abrir = ler("app/RADIOTERAPIA_AI_LOCAL_SUITE.cmd")
    checar(u"o arquivo existe", bool(abrir))
    checar(u"ele chama o start_watcher, nao duplica a logica",
           u'call "%ALVO%start_watcher.cmd"' in abrir)

    import os as _os
    onde = [d for d in _os.listdir(_os.path.join(RAIZ, "app"))
            if _os.path.isfile(_os.path.join(RAIZ, "app", d, "start_watcher.cmd"))]
    checar(u"o start_watcher mora numa subpasta de app/", bool(onde), str(onde))
    for sub in onde:
        checar(u"e o lancador procura em `%s\\`" % sub,
               (u'%%~dp0%s\\start_watcher.cmd' % sub) in abrir,
               u"a pasta existe no disco e o lancador nao a procura")
    checar(u"a geracao anterior (`ferramentas\\`) continua na lista",
           u'%~dp0ferramentas\\start_watcher.cmd' in abrir,
           u"estacao que so atualizou o codigo ainda a tem no disco")
    checar(u"e a raiz tambem, que e onde alguem ja copiou a mao",
           u'%~dp0start_watcher.cmd' in abrir)
    checar(u"e avisa se a copia veio pela metade",
           u"INSTALACAO INCOMPLETA" in abrir
           or u"INCOMPLETE INSTALLATION" in abrir)
    b = io.open(_componentes.fonte("app/RADIOTERAPIA_AI_LOCAL_SUITE.cmd"), "rb").read()
    checar(u"esta em CRLF",
           b.count(bytes([13, 10])) == b.count(bytes([10])))
    emp = ler("build/configurar_ambiente.py")
    checar(u"o empacotador o leva como OBRIGATORIO",
           u'"RADIOTERAPIA_AI_LOCAL_SUITE.cmd"' in emp)
    inst = ler("installer/INSTALL.ps1")
    checar(u"e o atalho aponta para ele",
           u'$alvo = Join-Path $DESTINO "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"' in inst)

    leia = ler("packager/README-ROOT.txt")
    checar(u"o LEIA-ME manda COPIAR A PASTA, nao rodar script",
           u"copia de pasta" in leia and u"RADIOTERAPIA_AI_LOCAL_SUITE.cmd" in leia)
    checar(u"e nao instrui powershell para o caso bloqueado",
           u"powershell -NoProfile -ExecutionPolicy Bypass -File INSTALL.ps1" not in leia)


def teste_conclusao_qual_botao():
    secao(u"tela 4: rodar a suite, e a pasta so para quem leva")
    ps = ler("packager/prepare.ps1")

    checar(u"o botao se chama `Rodar Suite Local`",
           u"NovoBotao 'Rodar Su\u00edte Local'" in ps,
           u"era «Rodar o Local Suite agora»")
    idi = json.loads(ler("packager/languages.json"))
    fr = idi.get("frases", {})
    checar(u"e ele tem entrada nos 11 idiomas",
           len([c for c in idi["codigos"] if c != idi["padrao"]
                and fr.get(u"Rodar Su\u00edte Local", {}).get(c)]) == 11)
    checar(u"em ingles ele diz `Run Local Suite`",
           fr.get(u"Rodar Su\u00edte Local", {}).get("en") == u"Run Local Suite")
    checar(u"e a chave velha nao ficou orfa",
           u"Rodar o Local Suite agora" not in fr
           and u"Rodar o Local Suite agora" not in ps)

    i = ps.find(u"$btAbrirPrograma.Add_Click(")
    j = ps.find(u"$aba4.Controls.Add($btAbrirPrograma)", i)
    clique = ps[i:j] if i > 0 and j > i else u""
    checar(u"o clique existe", bool(clique))
    checar(u"ele lanca o programa", u"Start-Process $exe" in clique)
    checar(u"e fecha a janela em seguida", u"$form.Close()" in clique,
           u"«fecha o powershell» -- e o ShowDialog e a ultima linha do arquivo")
    codigo = u"\n".join(l for l in clique.splitlines()
                        if not l.lstrip().startswith(u"#"))
    checar(u"ele NAO abre navegador por conta propria",
           u"http" not in codigo,
           u"duas abas, e a segunda numa porta que ainda nao subiu")
    checar(u"  e a guarda sabe reprovar (isca)",
           u"http" in (clique + u"\nStart-Process 'http://x'"))
    lanc = ler("app/launchers/start_watcher.cmd")
    checar(u"  e o lancador e quem abre", u"http://127.0.0.1:8777/" in lanc)
    checar(u"e nao fecha quando nao achou o lancador",
           clique.find(u"return") < clique.find(u"$form.Close()"),
           u"fechar sem abrir e indistinguivel de ter funcionado")

    checar(u"ha uma funcao `CaminhoDoPrograma`",
           u"function CaminhoDoPrograma" in ps)
    checar(u"e o clique a usa", u"$exe = CaminhoDoPrograma" in clique)
    checar(u"e a decisao de visibilidade tambem",
           u"$exeAqui = CaminhoDoPrograma" in ps,
           u"botao aparece se, e somente se, clicar nele funciona")

    i = ps.find(u"function AtualizarConclusao")
    corpo = ps[i:ps.find(u"\n}", i)] if i > 0 else u""
    for bt in (u"btAbrirPrograma", u"btAbrirPasta"):
        checar(u"`$%s.Visible` e atribuido UMA vez" % bt,
               corpo.count(u"$%s.Visible =" % bt) == 1,
               u"%d atribuicoes" % corpo.count(u"$%s.Visible =" % bt))

    bloco = _bloco_de_decisao(ps)
    checar(u"achei o bloco de decisao no .ps1", bool(bloco))
    if bloco:
        for nome, instalou, zip_existe, prog, pasta in (
                (u"modo 3 -- instalou o que trouxe", True, True, True, False),
                (u"modo 1 -- esta e a estacao de uso", True, False, True, False),
                (u"modo 2 -- maquina de passagem", False, True, False, True),
                (u"instalacao que nao completou", False, False, False, False)):
            r = _rodar_decisao(bloco, instalou, zip_existe)
            if r is None:
                checar(u"%s: rodou" % nome, False, u"o PowerShell nao respondeu")
                continue
            checar(u"%s: RODAR aparece = %s" % (nome, prog),
                   r["prog"] == prog, u"veio %s" % r["prog"])
            checar(u"%s: pasta do pacote aparece = %s" % (nome, pasta),
                   r["pasta"] == pasta, u"veio %s" % r["pasta"])
        r = _rodar_decisao(bloco, False, True, antiga_no_padrao=True)
        checar(u"modo 2 com instalacao ANTIGA na pasta padrao: RODAR NAO aparece",
               r is not None and not r["prog"],
               u"o recuo para PASTA_RT dizia «instalou aqui» por uma "
               u"instalacao que esta sessao nem tocou -- %s" % r)
        checar(u"  e a pasta do pacote aparece", r is not None and r["pasta"],
               u"%s" % r)
        r = _rodar_decisao(bloco, True, True)
        checar(u"os dois nunca aparecem juntos",
               r is not None and not (r["prog"] and r["pasta"]))
        checar(u"e o Fechar encosta no que sobrou",
               r is not None and r["fechar"] == 282, u"x=%s" % (r or {}).get("fechar"))


def _bloco_de_decisao(ps):
    i = ps.find(u"$exeAqui = CaminhoDoPrograma")
    j = ps.find(u"else { 20 }", i)
    return ps[i:j + len(u"else { 20 }")] if i > 0 and j > i else u""


def _rodar_decisao(bloco, instalou, zip_existe, antiga_no_padrao=False):
    import subprocess
    import tempfile
    real = _funcoes_ps(u"packager/prepare.ps1",
                       [u"CaminhoDoPrograma"]).get(u"CaminhoDoPrograma", u"")
    if not real:
        return None
    d = tempfile.mkdtemp(prefix="radai_concl_")
    inst = os.path.join(d, "instalado")
    padrao = os.path.join(d, "padrao")
    os.makedirs(inst)
    os.makedirs(padrao)
    if instalou:
        io.open(os.path.join(inst, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"),
                "w").write(u"@echo off\r\n")
    if antiga_no_padrao:
        io.open(os.path.join(padrao, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"),
                "w").write(u"@echo off\r\n")
    cabeca = (u"\n$ErrorActionPreference = 'Stop'\n"
              u"Set-StrictMode -Version Latest\n"
              u"$script:LANCADORES = @('RADIOTERAPIA_AI_LOCAL_SUITE.cmd',\n"
              u"                       'ABRIR_AUTO_CONTORNO.cmd')\n"
              u"$script:PASTA_RT = '%s'\n"
              u"$script:PastaInstalada = %s\n"
              % (padrao, (u"'%s'" % inst) if instalou else u"''") +
              real + u"\n" +
              u"$Zip = if ($env:FAKE_ZIP -eq '1') { $PSCommandPath } else { '' }\n"
              u"$btAbrirPrograma = [pscustomobject]@{ Visible = $null }\n"
              u"$btAbrirPasta    = [pscustomobject]@{ Visible = $null; Enabled = $null }\n"
              u"$btFechar        = [pscustomobject]@{ Left = 0 }\n")
    rabo = (u"\n'RES' + ':' + $btAbrirPrograma.Visible + ':' + "
            u"$btAbrirPasta.Visible + ':' + $btFechar.Left\n")
    f = os.path.join(d, "d.ps1")
    io.open(f, "w", encoding="utf-8-sig", newline="\r\n").write(
        cabeca + bloco + rabo)
    amb = dict(os.environ)
    amb["FAKE_ZIP"] = "1" if zip_existe else "0"
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", f], capture_output=True, text=True, timeout=90,
            env=amb).stdout
    except Exception:
        return None
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    for linha in out.splitlines():
        if linha.startswith("RES:"):
            _, a, b, c = linha.split(":")
            return {"prog": a == "True", "pasta": b == "True",
                    "fechar": int(c)}
    return None


def teste_instalador_zip():
    secao(u"INSTALL.cmd: mesmo tratamento do clique de dentro do .zip")
    cmd = ler("installer/INSTALL.cmd")
    checar(u"detecta pela AUSENCIA da pasta do programa",
           u"radai_watcher.py" in cmd and u"goto :pacote_ok" in cmd,
           u"nao pelo nome que o Explorer da a pasta temporaria")
    checar(u"  e resolve por MARCA, sem nome de projeto cravado",
           u"AUTO_CONTORNO\" goto" not in cmd
           and u"LOCAL_SUITE\" goto" not in cmd,
           u"nome proprio no `if exist` volta a quebrar no proximo renome")
    checar(u"pergunta ao Explorer qual .zip esta aberto",
           u"Shell.Application" in cmd)
    checar(u"procura tambem na raiz de cada disco",
           u"Get-PSDrive -PSProvider FileSystem" in cmd)
    checar(u"e, falhando, PERGUNTA com um seletor",
           u"OpenFileDialog" in cmd)
    checar(u"em -STA, senao o seletor nao abre", u"-STA -Command" in cmd)
    checar(u"achando, extrai e continua a instalacao de la",
           u"ExtractToDirectory" in cmd and u"call " in cmd)
    checar(u"e limpa a extracao temporaria no fim",
           u'rmdir /s /q "%EXTRAI%"' in cmd)


def teste_dois_layouts():
    import subprocess
    import tempfile
    secao(u"START_HERE.cmd: os dois layouts, rodando de verdade")

    import re
    lan = os.path.join(RAIZ, "packager", "START_HERE.cmd")
    texto = io.open(lan, encoding="utf-8", errors="replace").read()
    m = re.search(r'(?m)^set "CASA=(?!%AQUI%)[^"]+"', texto)
    if not m:
        checar(u"achei a atribuicao da CASA para redirecionar", False,
               u"o lancador mudou a forma de definir a casa; sem redirecionar, "
               u"este teste escreve na maquina de quem o roda -- ajuste a bateria")
        return
    CASA_REAL = m.group(0)

    base = tempfile.mkdtemp(prefix="radai_prep_layouts_")
    for sub, marca in ((u"", u"FLAT"), (u"programa", u"PROGRAMA")):
        raiz = os.path.join(base, marca.lower())
        peq = os.path.join(raiz, sub) if sub else raiz
        os.makedirs(os.path.join(peq, "packager"))
        os.makedirs(os.path.join(peq, "build"))
        io.open(os.path.join(peq, "packager", "prepare.ps1"), "w",
                encoding="utf-8-sig", newline="").write(
                    u"Write-Host 'MARCA:%s'" % marca + CRLF + u"exit 0" + CRLF)
        io.open(os.path.join(peq, "build", "configurar_ambiente.py"),
                "w").write("# fantoma" + chr(10))
        casa = os.path.join(base, "casa_" + marca.lower())
        lote = texto.replace(CASA_REAL, 'set "CASA=' + casa + '"')
        checar(u"layout `%s`: a CASA foi desviada do %%TEMP%% real"
               % ((sub + u"/") if sub else u"raiz"),
               casa in lote and CASA_REAL not in lote,
               u"sem isto o teste faz xcopy dentro da pasta de instalacao "
               u"real da maquina de quem roda a bateria")
        io.open(os.path.join(raiz, "START_HERE.cmd"), "w",
                encoding="ascii", newline="\r\n").write(lote)
        cru = io.open(os.path.join(raiz, "START_HERE.cmd"), "rb").read()
        checar(u"layout `%s`: o fantoma saiu em CRLF"
               % ((sub + u"/") if sub else u"raiz"),
               cru.count(b"\n") == cru.count(b"\r\n") and cru.count(b"\r\n") > 0,
               u"com LF o cmd.exe perde o rumo e o `goto` cai noutro lugar: "
               u"a bateria mediria o modo de falha do LF, nao o lancador")
        saida, _rc, _logs = _rodar_start_here(
            os.path.join(raiz, "START_HERE.cmd"),
            os.path.join(base, "lad_" + marca.lower()))
        saida = saida + u"\n" + u"\n".join(t for _n, t in _logs)
        rotulo = (sub + u"/") if sub else u"raiz"
        checar(u"layout `%s`: o lancador chega ao prepare.ps1" % rotulo,
               ("MARCA:" + marca) in saida, saida[-500:])
        checar(u"layout `%s`: sem 'A EXTRACAO NAO COMPLETOU'" % rotulo,
               "EXTRACAO NAO COMPLETOU" not in saida,
               u"a mensagem culpa a extracao por um caminho errado")

    import time
    for rotulo, dias_raiz, dias_prog, espera in (
            (u"raiz mais nova vence o `programa\\` velho", 0, 5, u"RAIZNOVA"),
            (u"`programa\\` mais novo vence a raiz velha", 5, 0, u"PROGNOVO"),
            (u"a versao nova em programa vence com a data do preparador igual", 0, 0, u"PROGNOVO")):
        raiz = os.path.join(base, "empate_" + espera.lower())
        agora = time.time()
        for sub, marca, dias in (("", u"RAIZNOVA" if espera == u"RAIZNOVA"
                                  else u"RAIZVELHA", dias_raiz),
                                 ("programa", u"PROGNOVO" if espera == u"PROGNOVO"
                                  else u"PROGVELHO", dias_prog)):
            peq = os.path.join(raiz, sub) if sub else raiz
            os.makedirs(os.path.join(peq, "packager"), exist_ok=True)
            os.makedirs(os.path.join(peq, "build"), exist_ok=True)
            alvo = os.path.join(peq, "packager", "prepare.ps1")
            io.open(alvo, "w", encoding="utf-8-sig", newline="").write(
                u"Write-Host 'MARCA:%s'" % marca + CRLF + u"exit 0" + CRLF)
            quando = agora - dias * 86400
            os.utime(alvo, (quando, quando))
            if dias_raiz == dias_prog:
                io.open(os.path.join(peq, "entrega.txt"), "w", encoding="ascii").write(
                    "VERSAO=" + ("8.8" if sub else "8.7.1") + "\n")
            io.open(os.path.join(peq, "build", "configurar_ambiente.py"),
                    "w").write("# fantoma" + chr(10))
        casa = os.path.join(base, "casa_empate_" + espera.lower())
        io.open(os.path.join(raiz, "START_HERE.cmd"), "w",
                encoding="ascii", newline="\r\n").write(
                    texto.replace(CASA_REAL, 'set "CASA=' + casa + '"'))
        saida, _rc, _logs = _rodar_start_here(
            os.path.join(raiz, "START_HERE.cmd"),
            os.path.join(base, "lad_empate_" + espera.lower()))
        saida = saida + u"\n" + u"\n".join(t for _n, t in _logs)
        checar(rotulo, ("MARCA:" + espera) in saida,
               u"esperava MARCA:%s -- %s" % (espera, saida[-300:]))

    raiz = os.path.join(base, "fallback_programa")
    peq = os.path.join(raiz, "programa")
    os.makedirs(os.path.join(peq, "packager"))
    os.makedirs(os.path.join(peq, "build"))
    io.open(os.path.join(peq, "packager", "prepare.ps1"), "w",
            encoding="utf-8-sig", newline="").write(
                u"Write-Host 'MARCA:FALLBACK_PROGRAMA'" + CRLF + u"exit 0" + CRLF)
    io.open(os.path.join(peq, "build", "configurar_ambiente.py"), "w").write("x")
    bloqueio = os.path.join(base, "pai_bloqueado.txt")
    io.open(bloqueio, "w").write("arquivo, nao uma pasta")
    casa = os.path.join(bloqueio, "casa")
    bat = os.path.join(raiz, "START_HERE.cmd")
    io.open(bat, "w", encoding="ascii", newline="\r\n").write(
        texto.replace(CASA_REAL, 'set "CASA=' + casa + '"'))
    saida, rc, logs = _rodar_start_here(bat, os.path.join(base, "lad_fallback"))
    tudo = saida + u"\n" + u"\n".join(t for _n, t in logs)
    checar(u"sem poder criar a CASA, o layout programa abre da pasta extraida",
           rc == 0 and u"MARCA:FALLBACK_PROGRAMA" in tudo, tudo[-500:])

    intrusos = []
    for r, _d, fs in os.walk(CASA_REAL):
        for f in fs:
            if f == "prepare.ps1":
                t = io.open(os.path.join(r, f), encoding="utf-8-sig",
                            errors="replace").read()
                if "MARCA:" in t:
                    intrusos.append(os.path.join(r, f))
    checar(u"e a instalacao real nao foi tocada", not intrusos,
           u"; ".join(intrusos))


def _pagina_oem():
    try:
        import ctypes
        cp = ctypes.windll.kernel32.GetOEMCP()
        u"x".encode("cp%d" % cp)
        return "cp%d" % cp
    except Exception:
        return "cp850"


def _rodar_start_here(bat, lad, cod="cp1252", console_novo=False):
    os.makedirs(lad, exist_ok=True)
    amb = dict(os.environ)
    amb["LOCALAPPDATA"] = lad
    extra = {}
    if console_novo:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        extra = {"creationflags": subprocess.CREATE_NEW_CONSOLE,
                 "startupinfo": si}
    try:
        p = subprocess.run(["cmd", "/c", bat], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=180, env=amb, **extra)
        tela, rc = p.stdout.decode(cod, "replace"), p.returncode
    except Exception as e:
        tela, rc = u"(nao rodou: %s)" % e, None
    logs = []
    pasta = os.path.join(lad, "RadioterapiaAI", "logs")
    if os.path.isdir(pasta):
        for n in sorted(os.listdir(pasta)):
            logs.append((n, io.open(os.path.join(pasta, n), "rb").read()
                         .decode("utf-8", "replace")))
    return tela, rc, logs


def teste_start_here_diz_o_tamanho_e_guarda_o_log():
    import re as _re
    secao(u"START_HERE: o tamanho da fonte unica, e o log que sobrevive")
    lan = os.path.join(RAIZ, "packager", "START_HERE.cmd")
    texto = io.open(lan, encoding="utf-8", errors="replace").read()
    m = _re.search(r'(?m)^set "CASA=(?!%AQUI%)[^"]+"', texto)
    checar(u"achei a atribuicao da CASA para redirecionar", bool(m))
    if not m:
        return
    base = tempfile.mkdtemp(prefix="radai_prep_start_")
    try:
        def fantoma(nome, tamanho, rc_ps, corpo=None):
            raiz = os.path.join(base, nome)
            os.makedirs(os.path.join(raiz, "packager"))
            os.makedirs(os.path.join(raiz, "build"))
            linhas = u"".join(u"Write-Host 'linha %02d do preparador'" % i + CRLF
                              for i in range(1, 41))
            fim = (u"[Environment]::Exit(%d)" % rc_ps) if rc_ps else u"exit 0"
            io.open(os.path.join(raiz, "packager", "prepare.ps1"), "w",
                    encoding="utf-8-sig", newline="").write(
                        corpo if corpo is not None else linhas + fim + CRLF)
            shutil.copy2(os.path.join(RAIZ, "packager", "preparer_log.ps1"),
                         os.path.join(raiz, "packager", "preparer_log.ps1"))
            io.open(os.path.join(raiz, "build", "configurar_ambiente.py"),
                    "w").write("# fantoma" + chr(10))
            if tamanho is not None:
                io.open(os.path.join(raiz, "PACKAGE_SIZE.txt"), "w",
                        encoding="ascii", newline="").write(tamanho + CRLF)
            casa = os.path.join(base, "casa_" + nome)
            io.open(os.path.join(raiz, "START_HERE.cmd"), "w", encoding="ascii",
                    newline="\r\n").write(
                        texto.replace(m.group(0), 'set "CASA=' + casa + '"'))
            return os.path.join(raiz, "START_HERE.cmd")

        tela, rc, logs = _rodar_start_here(fantoma("com_tamanho", u"19", 0),
                                           os.path.join(base, "lad1"))
        corrida = u" ".join(tela.split())
        checar(u"com PACKAGE_SIZE.txt, a tela diz «about 19 GB»",
               u"about 19 GB" in corrida, tela[-300:])
        checar(u"  e nao o 12.6 escrito a mao", u"12.6" not in tela)
        tela2, _rc2, _l2 = _rodar_start_here(fantoma("sem_tamanho", None, 0),
                                             os.path.join(base, "lad2"))
        checar(u"sem o arquivo, cai na reserva «about 20 GB»",
               u"about 20 GB" in u" ".join(tela2.split()), tela2[-300:])
        checar(u"a ordem dos botoes da tela preta e' a da janela",
               tela.find(u"INSTALL / UPDATE APP ON THIS MACHINE")
               < tela.find(u"OFFLINE MACHINE: INSTALL FROM A PACKAGE I BROUGHT")
               < tela.find(u"MACHINE WITH INTERNET: BUILD A PACKAGE")
               < tela.find(u"UNINSTALL.")
               and tela.find(u"INSTALL / UPDATE APP ON THIS MACHINE") >= 0)

        checar(u"um log por execucao, em %LOCALAPPDATA%\\RadioterapiaAI\\logs",
               len(logs) == 1, [n for n, _t in logs])
        if logs:
            nome, txt = logs[0]
            checar(u"  com data no nome (preparer_AAAAMMDD_HHMMSS.log)",
                   _re.match(r"^preparer_\d{8}_\d{6}\.log$", nome) is not None,
                   nome)
            checar(u"  e com a saida INTEIRA do preparador",
                   u"linha 01 do preparador" in txt
                   and u"linha 40 do preparador" in txt, txt[:200])
            checar(u"  e o codigo de saida escrito nele",
                   u"exited with code 0" in txt, txt[-200:])
        checar(u"com codigo 0, nenhuma tela de erro",
               u"stopped with error" not in tela)

        tela3, rc3, logs3 = _rodar_start_here(
            fantoma("erro", u"19", -805306369), os.path.join(base, "lad3"))
        checar(u"a tela diz o codigo", u"stopped with error -805306369" in tela3,
               tela3[-400:])
        caminho = logs3[0][0] if logs3 else u"(sem log)"
        checar(u"  e ONDE esta o log", caminho in tela3
               and u"RadioterapiaAI\\logs" in tela3, caminho)
        checar(u"  e mostra o FIM dele (a linha 40)",
               u"linha 40 do preparador" in tela3, tela3[-400:])
        checar(u"  e so' o fim: a linha 10 nao aparece na tela",
               u"linha 10 do preparador" not in tela3,
               u"a tela despejou o log inteiro")
        checar(u"  e diz, para ESTE codigo, que o processo foi encerrado de fora",
               u"did not finish by itself" in tela3, tela3[-400:])
        checar(u"  e diz que e' a leitura USUAL, sem afirmar o mecanismo",
               u"usually means" in tela3 and u"-805306369 means" not in tela3,
               tela3[-300:])
        checar(u"  e devolve o mesmo codigo", rc3 == -805306369 or
               (rc3 is not None and (rc3 & 0xFFFFFFFF) == 0xCFFFFFFF), rc3)
        checar(u"  e a CASA nao tem log nenhum (a extracao seguinte o apagaria)",
               not any(f.lower().endswith(u".log")
                       for _r, _d, fs in os.walk(os.path.join(base, "casa_erro"))
                       for f in fs))

        import time as _time
        lad4 = os.path.join(base, "lad4")
        pl4 = os.path.join(lad4, "RadioterapiaAI", "logs")
        os.makedirs(pl4)
        agora = _time.time()
        velhos = []
        for i in range(25):
            n = os.path.join(pl4, "preparer_20200101_0000%02d.log" % i)
            io.open(n, "w").write(u"velho %d\n" % i)
            os.utime(n, (agora - 86400 * (30 - i), agora - 86400 * (30 - i)))
            velhos.append(n)
        io.open(os.path.join(pl4, "outro.txt"), "w").write(u"nao e' log")
        _t4, _rc4, logs4 = _rodar_start_here(fantoma("podar", u"19", 0), lad4)
        nomes4 = [n for n, _t in logs4 if n.startswith(u"preparer_")]
        checar(u"os logs velhos sao podados: ficam os 20 mais novos",
               len(nomes4) == 20, u"%d logs" % len(nomes4))
        checar(u"  e o desta execucao esta entre eles",
               any(not n.startswith(u"preparer_2020") for n in nomes4), nomes4[-3:])
        checar(u"  e os mais VELHOS e' que sairam",
               not os.path.exists(velhos[0]) and os.path.exists(velhos[-1]))
        checar(u"  e o arquivo que nao e' log do preparador ficou",
               os.path.exists(os.path.join(pl4, "outro.txt")))

        cod = _pagina_oem()
        corpo5 = (u"$w = New-Object System.IO.StreamWriter([Console]::OpenStandardOutput(), "
                  u"(New-Object System.Text.UTF8Encoding($false)))" + CRLF +
                  u"$w.AutoFlush = $true" + CRLF +
                  u"$w.WriteLine('Sessão em UTF-8: ação')" + CRLF +
                  u"throw 'Exceção de teste: não terminou'" + CRLF)
        tela5, rc5, logs5 = _rodar_start_here(fantoma("acento", u"19", 0, corpo5),
                                              os.path.join(base, "lad5"), cod,
                                              console_novo=True)
        checar(u"a linha em UTF-8 aparece certa na tela de erro (%s)" % cod,
               u"Sessão em UTF-8: ação" in tela5, tela5[-400:])
        checar(u"  e a mensagem de excecao do host TAMBEM (pagina do console)",
               u"Exceção de teste: não terminou" in tela5,
               [l for l in tela5.splitlines() if u"teste" in l][:3])

        pp = os.path.join(base, "preparar_cmd")
        os.makedirs(pp)
        shutil.copy2(os.path.join(RAIZ, "packager", "PREPARAR_AUTO_CONTORNO.cmd"), pp)
        shutil.copy2(os.path.join(RAIZ, "packager", "preparer_log.ps1"), pp)
        io.open(os.path.join(pp, "prepare.ps1"), "w", encoding="utf-8-sig",
                newline="").write(
            u"".join(u"Write-Host 'linha %02d do preparador'" % i + CRLF
                     for i in range(1, 41)) + u"[Environment]::Exit(-805306369)" + CRLF)
        tela6, rc6, logs6 = _rodar_start_here(
            os.path.join(pp, "PREPARAR_AUTO_CONTORNO.cmd"), os.path.join(base, "lad6"))
        checar(u"o PREPARAR_AUTO_CONTORNO.cmd mostra o fim do log",
               u"linha 40 do preparador" in tela6
               and u"linha 10 do preparador" not in tela6, tela6[-300:])
        checar(u"  e a mesma explicacao do -805306369 que o START_HERE",
               u"did not finish by itself" in tela6 and u"usually means" in tela6,
               tela6[-300:])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _python_de_fantoma(prog):
    destino = os.path.join(prog, "python")
    os.makedirs(destino, exist_ok=True)
    cfg = os.path.join(sys.prefix, "pyvenv.cfg")
    try:
        if os.path.isfile(cfg):
            shutil.copy2(sys.executable, os.path.join(destino, "python.exe"))
            shutil.copy2(cfg, os.path.join(prog, "pyvenv.cfg"))
        else:
            origem = os.path.dirname(sys.executable)
            for n in os.listdir(origem):
                nl = n.lower()
                if (nl == "python.exe" or nl.endswith((".dll", "._pth"))
                        or (nl.startswith("python") and nl.endswith(".zip"))):
                    shutil.copy2(os.path.join(origem, n), destino)
    except OSError as e:
        return u"a copia do interpretador falhou: %s" % e
    try:
        p = subprocess.run([os.path.join(destino, "python.exe"), "-c",
                            "import sys; sys.exit(7)"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=60)
    except Exception as e:
        return u"o Python do fantoma nao rodou: %s" % e
    if p.returncode != 7:
        return (u"a sonda devolveu %s, e nao 7: %s"
                % (p.returncode, p.stdout.decode("cp1252", "replace")[-200:]))
    return u""


def _rodar_lote(bat, extra=None, tirar=("RADAI_CONFIG",)):
    amb = dict(os.environ)
    for k in tirar:
        amb.pop(k, None)
    amb.setdefault("RADAI_NAVEGADOR", "0")
    # GUARDA: o lancador grava a pagina de carregamento e o console do motor no temporario, um arquivo por porta.
    proprio = tempfile.mkdtemp(prefix="radai_prep_lote_")
    for k in ("TMPDIR", "TEMP", "TMP", "RADAI_TMP"):
        amb[k] = proprio
    amb.update(extra or {})
    try:
        p = subprocess.run(["cmd", "/c", bat], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=180, env=amb)
        return p.stdout.decode("cp1252", "replace"), p.returncode
    except Exception as e:
        return u"(nao rodou: %s)" % e, None


_MOTOR_FANTOMA_NO_AR = u'''import ctypes, json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
aqui = os.path.dirname(os.path.abspath(__file__))
porta = int(open(os.path.join(aqui, "radai_watcher.config")).read().split("PORT=")[1].split()[0])
janela = ctypes.windll.kernel32.GetConsoleWindow() if os.name == "nt" else 0
open(os.path.join(aqui, "motor.txt"), "w").write("%s %s" % (os.environ.get("RADAI_MOTOR_OCULTO"), int(janela or 0)))
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        corpo = json.dumps({"radai": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(corpo)
    def log_message(self, *a):
        pass
srv = HTTPServer(("127.0.0.1", porta), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(15)
'''

_MOTOR_FANTOMA_MORRE = u'''import sys
print("motivo-do-fantoma: a porta estava ocupada")
sys.exit(7)
'''


def teste_o_motor_sobe_sem_janela():
    secao(u"o motor sobe sem janela, e a segunda janela preta nao nasce")
    if os.name != "nt":
        checar(u"(fora do Windows os lotes .cmd nao se aplicam)", True)
        return
    texto = io.open(os.path.join(RAIZ, "app", "launchers", "start_watcher.cmd"),
                    encoding="ascii").read()
    checar(u"o .cmd do navegador nao e aberto por `start` direto (o cmd /K "
           u"que ficava parado no prompt)",
           u'start "" /min "%JANELA%"' not in texto)
    checar(u"  e o recuo sem lancador o abre por `cmd /c call`",
           u'start "" /min cmd /c call "%JANELA%" %URL%' in texto)
    checar(u"com o lancador, o navegador abre DEPOIS do painel, no mesmo lote",
           texto.find(u'"%PROG%radai_lancador.py" --url %URL%')
           < texto.find(u'call "%JANELA%" %URL%')
           and texto.find(u'call "%JANELA%" %URL%') > 0)
    import socket as _s

    def porta_livre():
        s = _s.socket()
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        return p
    base = tempfile.mkdtemp(prefix="radai_prep_paren_")
    try:
        def montar(nome, motor):
            porta = porta_livre()
            prog = os.path.join(base, nome)
            os.makedirs(os.path.join(prog, "launchers"), exist_ok=True)
            motivo = _python_de_fantoma(prog)
            io.open(os.path.join(prog, "radai_watcher.py"), "w",
                    encoding="utf-8").write(motor)
            shutil.copy2(_componentes.fonte("app/radai_lancador.py"),
                         os.path.join(prog, "radai_lancador.py"))
            io.open(os.path.join(prog, "launchers", "start_watcher.cmd"), "w",
                    encoding="ascii", newline="\r\n").write(texto)
            io.open(os.path.join(prog, "launchers", "open_browser.cmd"), "w",
                    encoding="ascii", newline="\r\n").write(u"@exit /b 0\n")
            io.open(os.path.join(prog, "radai_watcher.config"), "w",
                    encoding="ascii", newline="\r\n").write(u"PORT=%d\n" % porta)
            return prog, motivo

        prog, motivo = montar(u"OCULTO (1)", _MOTOR_FANTOMA_NO_AR)
        checar(u"o Python do fantoma roda", not motivo, motivo)
        if motivo:
            return
        temp_do_lote = os.path.join(base, u"temp_do_lote")
        os.makedirs(temp_do_lote)
        geral = tempfile.gettempdir()

        def do_lancador(pasta):
            try:
                return set(x for x in os.listdir(pasta)
                           if x.startswith((u"radai_carregando_",
                                            u"radai_motor_")))
            except OSError:
                return set()
        antes = do_lancador(geral)
        tela, rc = _rodar_lote(os.path.join(prog, "launchers",
                                            "start_watcher.cmd"),
                               extra={"TMPDIR": temp_do_lote,
                                      "TEMP": temp_do_lote,
                                      "TMP": temp_do_lote,
                                      "RADAI_TMP": temp_do_lote})
        checar(u"o lancador gravou a pagina de carregamento no temporario do "
               u"lote (a medida abaixo nao e vazia)",
               bool(do_lancador(temp_do_lote)), sorted(do_lancador(temp_do_lote)))
        checar(u"  e nada no temporario de quem roda a bateria",
               not (do_lancador(geral) - antes),
               sorted(do_lancador(geral) - antes))
        checar(u"painel no ar: o lote sai com 0 e diz que o painel subiu",
               rc == 0 and u"Panel is up" in tela, u"rc=%s %s" % (rc, tela[-300:]))
        checar(u"  pelo caminho sem janela (o recuo visivel nao rodou)",
               u"leave this window OPEN" not in tela
               and u"Vigia encerrado." not in tela, tela[-300:])
        marca = u""
        for _ in range(20):
            try:
                marca = io.open(os.path.join(prog, "motor.txt")).read()
                break
            except Exception:
                time.sleep(0.25)
        checar(u"o motor recebeu RADAI_MOTOR_OCULTO=1 e NAO tem janela de "
               u"console", marca == u"1 0", repr(marca))

        prog7, _m = montar(u"MORRE (1)", _MOTOR_FANTOMA_MORRE)
        tela7, rc7 = _rodar_lote(os.path.join(prog7, "launchers",
                                              "start_watcher.cmd"))
        checar(u"o motor morreu no arranque: o lote devolve o codigo dele (7)",
               rc7 == 7, u"rc=%s" % rc7)
        checar(u"  e a janela mostra o motivo que o motor escreveu",
               u"THE ENGINE STOPPED BEFORE THE PANEL CAME UP (code 7)" in tela7
               and u"motivo-do-fantoma" in tela7, tela7[-400:])
        checar(u"  e o fim de sempre, com o codigo",
               u"THE STUDY QUEUE STOPPED with code 7." in tela7, tela7[-300:])
    finally:
        time.sleep(0.5)
        shutil.rmtree(base, ignore_errors=True)


def teste_parentese_no_caminho_nao_derruba_o_lote():
    secao(u"parentese no caminho e no texto: os lotes rodam ate o fim")
    if os.name != "nt":
        checar(u"(fora do Windows os lotes .cmd nao se aplicam)", True)
        return
    base = tempfile.mkdtemp(prefix="radai_prep_paren_")
    try:
        _parentese_no_vigia(base)
        _parentese_nos_instaladores(base)
        _parentese_no_rodar_com_bundle(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _parentese_no_vigia(base):
    texto = io.open(os.path.join(RAIZ, "app", "launchers", "start_watcher.cmd"),
                    encoding="ascii").read()
    raiz_txt = io.open(_componentes.fonte("app/RADIOTERAPIA_AI_LOCAL_SUITE.cmd"),
                       encoding="ascii").read()

    def montar(nome, lote, rc_py, porta=u"8803"):
        prog = os.path.join(base, nome)
        os.makedirs(os.path.join(prog, "launchers"), exist_ok=True)
        motivo = _python_de_fantoma(prog)
        io.open(os.path.join(prog, "radai_watcher.py"), "w").write(
            u"import sys\nsys.exit(%d)\n" % rc_py)
        io.open(os.path.join(prog, "launchers", "start_watcher.cmd"), "w",
                encoding="ascii", newline="\r\n").write(lote)
        io.open(os.path.join(prog, "launchers", "open_browser.cmd"), "w",
                encoding="ascii", newline="\r\n").write(u"@exit\n")
        io.open(os.path.join(prog, "radai_watcher.config"), "w",
                encoding="ascii", newline="\r\n").write(u"PORT=%s\n" % porta)
        io.open(os.path.join(prog, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"), "w",
                encoding="ascii", newline="\r\n").write(raiz_txt)
        return prog, motivo

    prog, motivo = montar(u"LOCAL_SUITE (1)", texto, 7)
    checar(u"o Python do fantoma roda", not motivo, motivo)
    if motivo:
        return
    lote = os.path.join(prog, "launchers", "start_watcher.cmd")

    tela, rc = _rodar_lote(lote)
    checar(u"start_watcher: com o vigia saindo com 7, a tela diz o codigo",
           u"THE STUDY QUEUE STOPPED with code 7." in tela, tela[-400:])
    checar(u"  e imprime o parentese da linha do log inteiro",
           u"Log tab (http://127.0.0.1:8803/lote)." in tela, tela[-400:])
    checar(u"  e chega a linha SEGUINTE, ainda dentro do bloco",
           u"Send that log to whoever administers this installation." in tela,
           u"o `)` fechou o bloco no meio")
    checar(u"  e devolve o codigo do vigia (7), e nao 0 nem 255",
           rc == 7, rc)
    isca = texto.replace(u"^(%URL%lote^)", u"(%URL%lote)")
    checar(u"  isca: a linha do log tem o escape que a isca tira",
           isca != texto)
    prog_i, _m = montar(u"ISCA_VIGIA (1)", isca, 7)
    tela_i, rc_i = _rodar_lote(os.path.join(prog_i, "launchers",
                                            "start_watcher.cmd"))
    checar(u"  isca: com o `)` sem escape, o lote morre no meio (reprova)",
           u"Send that log to whoever administers" not in tela_i and rc_i != 7,
           u"rc=%s -- a checagem nao discrimina o defeito" % rc_i)

    prog0, _m = montar(u"LOCAL_SUITE (2)", texto, 0)
    tela0, rc0 = _rodar_lote(os.path.join(prog0, "launchers",
                                          "start_watcher.cmd"))
    checar(u"start_watcher: com o vigia saindo com 0, diz que encerrou",
           u"Vigia encerrado." in tela0 and u"STOPPED" not in tela0,
           tela0[-300:])
    checar(u"  e devolve 0", rc0 == 0, rc0)

    antigo = (u'if defined PORTA (\n'
              u'  echo %PORTA%| findstr /r "^[0-9][0-9]*$" >nul || set "PORTA="\n'
              u')\n')
    novo = (u'if defined PORTA for /f "delims=0123456789" %%X in ("%PORTA%") '
            u'do set "PORTA="\n')
    checar(u"start_watcher: o teste de digitos da porta esta fora de bloco",
           novo in texto)
    progp, _m = montar(u"PORTA (1)", texto, 7, porta=u"87)78")
    telap, rcp = _rodar_lote(os.path.join(progp, "launchers",
                                          "start_watcher.cmd"))
    checar(u"  PORT=87)78 no config: volta para 8777 e o lote vai ate o fim",
           u"http://127.0.0.1:8777/" in telap
           and u"Send that log to whoever administers" in telap and rcp == 7,
           u"rc=%s %s" % (rcp, telap[-200:]))
    progpi, _m = montar(u"PORTA_ISCA (1)", texto.replace(novo, antigo), 7,
                        porta=u"87)78")
    telapi, rcpi = _rodar_lote(os.path.join(progpi, "launchers",
                                            "start_watcher.cmd"))
    checar(u"  isca: com o teste antigo dentro do bloco, o lote morre (reprova)",
           novo in texto and rcpi != 7
           and u"Send that log to whoever administers" not in telapi,
           u"rc=%s -- a checagem nao discrimina o defeito" % rcpi)

    tela_r, rc_r = _rodar_lote(os.path.join(prog, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"))
    checar(u"RADIOTERAPIA_AI_LOCAL_SUITE.cmd: o codigo do vigia chega a quem "
           u"clicou (7)", rc_r == 7 and u"STOPPED with code 7" in tela_r,
           u"rc=%s" % rc_r)
    oca = os.path.join(base, u"SUITE (3)")
    os.makedirs(oca)
    io.open(os.path.join(oca, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"), "w",
            encoding="ascii", newline="\r\n").write(raiz_txt)
    tela_o, rc_o = _rodar_lote(os.path.join(oca, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"))
    checar(u"  sem os lancadores, diz ONDE procurou -- com o parentese da pasta",
           u"INCOMPLETE INSTALLATION" in tela_o
           and (oca + u"\\launchers\\") in tela_o
           and u"Copy the WHOLE" in tela_o and rc_o == 1,
           u"rc=%s %s" % (rc_o, tela_o[-300:]))
    isca_r = (raiz_txt.replace(u'echo      "%~dp0launchers\\"', u'echo      %~dp0launchers\\')
              .replace(u'echo      "%~dp0ferramentas\\"', u'echo      %~dp0ferramentas\\')
              .replace(u'echo      "%~dp0"', u'echo      %~dp0'))
    oca_i = os.path.join(base, u"SUITE_ISCA (3)")
    os.makedirs(oca_i)
    io.open(os.path.join(oca_i, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"), "w",
            encoding="ascii", newline="\r\n").write(isca_r)
    tela_oi, rc_oi = _rodar_lote(os.path.join(oca_i, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"))
    checar(u"  isca: com os caminhos sem aspas, a tela de erro morre (reprova)",
           isca_r != raiz_txt and u"Copy the WHOLE" not in tela_oi,
           u"rc=%s -- a checagem nao discrimina o defeito" % rc_oi)


def _sem_aspas(texto, variaveis):
    saida = []
    for linha in texto.split(u"\n"):
        if linha.lstrip().lower().startswith(u"echo"):
            for v in variaveis:
                linha = linha.replace(u'"%' + v + u'%"', u'%' + v + u'%')
        saida.append(linha)
    return u"\n".join(saida)


def _parentese_nos_instaladores(base):
    import re as _re
    here = io.open(os.path.join(RAIZ, "packager", "START_HERE.cmd"),
                   encoding="ascii").read()
    m = _re.search(r'(?m)^set "CASA=(?!%AQUI%)[^"]+"', here)
    checar(u"START_HERE: achei a atribuicao da CASA para desviar", bool(m))
    if not m:
        return

    def fantoma_here(nome, lote):
        raiz = os.path.join(base, nome)
        os.makedirs(os.path.join(raiz, "packager"))
        os.makedirs(os.path.join(raiz, "build"))
        io.open(os.path.join(raiz, "packager", "prepare.ps1"), "w",
                encoding="utf-8-sig", newline="").write(
            u"Write-Host 'linha 01 do preparador'" + CRLF
            + u"[Environment]::Exit(5)" + CRLF)
        shutil.copy2(os.path.join(RAIZ, "packager", "preparer_log.ps1"),
                     os.path.join(raiz, "packager", "preparer_log.ps1"))
        io.open(os.path.join(raiz, "build", "configurar_ambiente.py"),
                "w").write("# fantoma" + chr(10))
        casa = os.path.join(base, u"casa " + nome)
        io.open(os.path.join(raiz, "START_HERE.cmd"), "w", encoding="ascii",
                newline="\r\n").write(lote.replace(m.group(0),
                                                   u'set "CASA=' + casa + u'"'))
        return os.path.join(raiz, "START_HERE.cmd"), casa

    bat, casa = fantoma_here(u"pacote (1)", here)
    tela, rc, logs = _rodar_start_here(bat, os.path.join(base, u"lad (1)"))
    checar(u"START_HERE: pasta, CASA e log com parentese -- diz para onde copia",
           (u'Copying to "%s"' % casa) in tela, tela[:400])
    checar(u"  e mostra a tela de erro inteira, com o log e a CASA",
           u"The preparer stopped with error 5." in tela
           and u"Please send this file" in tela
           and (u'"%s"' % casa) in tela.split(u"README.txt in")[-1]
           and u"does not need scripts" in tela, tela[-500:])
    checar(u"  e o caminho do log, que tem o parentese do %LOCALAPPDATA%",
           bool(logs) and (u"lad (1)" in tela) and logs[0][0] in tela,
           [n for n, _t in logs])
    checar(u"  e devolve o codigo do preparador (5)", rc == 5, rc)
    bat_i, _c = fantoma_here(u"pacote isca (1)",
                             _sem_aspas(here, (u"CASA", u"RADAI_LOG_PREPARADOR")))
    tela_i, rc_i, _l = _rodar_start_here(bat_i, os.path.join(base, u"lad isca (1)"))
    checar(u"  isca: com os caminhos sem aspas, o lote morre no meio (reprova)",
           rc_i != 5 and u"does not need scripts" not in tela_i,
           u"rc=%s -- a checagem nao discrimina o defeito" % rc_i)

    prep = io.open(os.path.join(RAIZ, "packager", "PREPARAR_AUTO_CONTORNO.cmd"),
                   encoding="ascii").read()

    def fantoma_prep(nome, lote):
        pp = os.path.join(base, nome)
        os.makedirs(pp)
        io.open(os.path.join(pp, "PREPARAR_AUTO_CONTORNO.cmd"), "w",
                encoding="ascii", newline="\r\n").write(lote)
        shutil.copy2(os.path.join(RAIZ, "packager", "preparer_log.ps1"), pp)
        io.open(os.path.join(pp, "prepare.ps1"), "w", encoding="utf-8-sig",
                newline="").write(u"Write-Host 'linha 01'" + CRLF
                                  + u"[Environment]::Exit(5)" + CRLF)
        return os.path.join(pp, "PREPARAR_AUTO_CONTORNO.cmd")

    tela_p, rc_p, logs_p = _rodar_start_here(fantoma_prep(u"preparar (1)", prep),
                                             os.path.join(base, u"lad (2)"))
    checar(u"PREPARAR_AUTO_CONTORNO: log com parentese -- a tela de erro inteira",
           u"The preparer stopped with error 5." in tela_p
           and bool(logs_p) and logs_p[0][0] in tela_p
           and u"Please send this file" in tela_p and rc_p == 5,
           u"rc=%s %s" % (rc_p, tela_p[-300:]))
    tela_pi, rc_pi, _l = _rodar_start_here(
        fantoma_prep(u"preparar isca (1)", _sem_aspas(prep, (u"RADAI_LOG_PREPARADOR",))),
        os.path.join(base, u"lad isca (2)"))
    checar(u"  isca: com o log sem aspas, o lote morre no meio (reprova)",
           rc_pi != 5 and u"Please send this file" not in tela_pi,
           u"rc=%s -- a checagem nao discrimina o defeito" % rc_pi)

    inst = io.open(os.path.join(RAIZ, "installer", "INSTALL.cmd"),
                   encoding="ascii").read()

    def fantoma_inst(nome, lote):
        d = os.path.join(base, nome)
        os.makedirs(os.path.join(d, "LOCAL_SUITE"))
        io.open(os.path.join(d, "LOCAL_SUITE", "radai_watcher.py"), "w").write(
            u"# fantoma\n")
        io.open(os.path.join(d, "INSTALL.cmd"), "w", encoding="ascii",
                newline="\r\n").write(lote)
        return d

    d = fantoma_inst(u"inst (1)", inst)
    tela_n, rc_n = _rodar_lote(os.path.join(d, "INSTALL.cmd"))
    checar(u"INSTALL.cmd: pasta com parentese e sem o INSTALL.ps1 -- diz qual",
           u"nao achei o INSTALL.ps1" in tela_n and (u'"%s\\"' % d) in tela_n
           and u"O QUE FAZER" in tela_n and rc_n == 1,
           u"rc=%s %s" % (rc_n, tela_n[-300:]))
    d_i = fantoma_inst(u"inst isca (1)", _sem_aspas(inst, (u"AQUI",)))
    tela_ni, rc_ni = _rodar_lote(os.path.join(d_i, "INSTALL.cmd"))
    checar(u"  isca: com a pasta sem aspas, o lote morre no meio (reprova)",
           u"O QUE FAZER" not in tela_ni,
           u"rc=%s -- a checagem nao discrimina o defeito" % rc_ni)


def _parentese_no_rodar_com_bundle(base):
    lote = io.open(os.path.join(RAIZ, "rodar_com_bundle.cmd"),
                   encoding="ascii").read()
    abre = u'if not "%RADAI_NAVEGADOR%"=="0" start "" http://127.0.0.1:%PORTA%/'
    checar(u"rodar_com_bundle: achei a linha que abre o navegador para calar",
           abre in lote)
    if abre not in lote:
        return
    repo = os.path.join(base, u"repo (1)")
    bundle = os.path.join(base, u"bundle (1)")
    dados = os.path.join(base, u"dados (1)")
    os.makedirs(os.path.join(repo, "app"))
    os.makedirs(os.path.join(repo, "tools"))
    shutil.copy2(os.path.join(RAIZ, "tools", "_componentes.py"),
                 os.path.join(repo, "tools", "_componentes.py"))
    motivo = _python_de_fantoma(bundle)
    checar(u"  o Python do fantoma roda", not motivo, motivo)
    if motivo:
        return
    io.open(os.path.join(repo, "rodar_com_bundle.cmd"), "w", encoding="ascii",
            newline="\r\n").write(lote.replace(abre, u"REM (a bateria nao abre navegador)"))
    io.open(os.path.join(repo, "_bundle.txt"), "w", encoding="ascii",
            newline="\r\n").write(bundle + u"\n")
    io.open(os.path.join(repo, "_dados.txt"), "w", encoding="ascii",
            newline="\r\n").write(dados + u"\n")
    io.open(os.path.join(repo, "app", "radai_watcher.py"), "w").write(
        u"import os, sys\n"
        u"print('REGISTRO=[%s]' % os.environ.get('RADAI_REGISTRO_DIR', ''))\n"
        u"print('ACERVO=[%s]' % os.environ.get('RADAI_CALIB_DIR', ''))\n"
        u"sys.exit(3)\n")
    bat = os.path.join(repo, "rodar_com_bundle.cmd")
    tela, rc = _rodar_lote(bat, tirar=("RADAI_CONFIG", "RADAI_REGISTRO_DIR",
                                       "RADAI_CALIB_DIR"))
    checar(u"rodar_com_bundle: o registro vai para <_dados.txt>\\registro",
           (u"REGISTRO=[%s\\registro]" % dados) in tela, tela[-300:])
    checar(u"  e o banner diz onde", (u'Registro: "%s\\registro"' % dados) in tela)
    checar(u"  e o codigo do vigia volta (3), com a tela de erro inteira",
           rc == 3 and u"Guarde esse arquivo" in tela, u"rc=%s" % rc)
    ja = os.path.join(base, u"ja definido")
    tela2, _rc2 = _rodar_lote(bat, extra={"RADAI_REGISTRO_DIR": ja},
                              tirar=("RADAI_CONFIG", "RADAI_CALIB_DIR"))
    checar(u"  e quem ja definiu RADAI_REGISTRO_DIR manda",
           (u"REGISTRO=[%s]" % ja) in tela2, tela2[-200:])
    isolado = os.path.join(base, u"acervo isolado (1)")
    cfg = os.path.join(base, u"isolado.config")
    io.open(cfg, "w", encoding="ascii", newline="\r\n").write(
        u"# config da prova\nROOT=\nPORT = 8799\n")
    tela4, _rc4 = _rodar_lote(bat, extra={"RADAI_CALIB_DIR": isolado,
                                          "RADAI_CONFIG": cfg},
                              tirar=("RADAI_REGISTRO_DIR",))
    checar(u"  e quem ja definiu RADAI_CALIB_DIR manda: o _dados.txt nao "
           u"desfaz o isolamento de uma prova",
           (u"ACERVO=[%s]" % isolado) in tela4
           and (u"REGISTRO=[%s\\registro]" % isolado) in tela4, tela4[-300:])
    checar(u"  e o painel do banner e o da PORT do config",
           u"http://127.0.0.1:8799/" in tela4
           and u"http://127.0.0.1:8777/" not in tela4, tela4[-400:])
    os.remove(os.path.join(repo, "_dados.txt"))
    tela3, _rc3 = _rodar_lote(bat, tirar=("RADAI_CONFIG", "RADAI_REGISTRO_DIR",
                                          "RADAI_CALIB_DIR"))
    checar(u"  sem o _dados.txt, o banner avisa que o padrao SINCRONIZA",
           (u"REGISTRO=[%s]" % os.path.join(repo, u"app", u"registro")) in tela3
           and u"SINCRONIZA" in tela3, tela3[-300:])


def teste_erro_de_topo_vai_para_o_log():
    secao(u"o erro que para o preparador fica no log de sessao, em UTF-8")
    fonte = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                    encoding="utf-8-sig", newline="").read()
    ancora = u"$script:ErroJaNoLog = $false"
    checar(u"a marca do `trap` existe no preparador", ancora in fonte)
    if ancora not in fonte:
        return
    tmp = tempfile.mkdtemp(prefix="radai_prep_trap_")
    try:
        copia = os.path.join(tmp, "prepare.ps1")
        io.open(copia, "w", encoding="utf-8-sig", newline="").write(
            fonte.replace(ancora, ancora + CRLF +
                          u"throw 'Exceção injetada pela bateria'", 1))
        amb = dict(os.environ)
        amb["RADAI_LOG_PREPARADOR"] = "bateria"
        p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                            "Bypass", "-STA", "-File", copia],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, env=amb, timeout=120)
        linhas = [l.decode("utf-8", "replace") for l in p.stdout.splitlines()]
        erro = [l for l in linhas if u"ERRO que parou o preparador" in l]
        checar(u"o log de sessao tem a linha do erro", bool(erro),
               u" | ".join(linhas[-3:])[:200])
        checar(u"  em UTF-8, com o acento inteiro",
               bool(erro) and u"Exceção injetada pela bateria" in erro[0],
               erro[:1])
        checar(u"  e com ONDE aconteceu",
               any(u"  em: " in l and u"prepare.ps1" in l for l in linhas),
               linhas[-2:])
        checar(u"  e o erro continua sendo erro (codigo de saida != 0)",
               p.returncode != 0, p.returncode)
        checar(u"  e so' uma vez", len(erro) == 1, len(erro))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_membros_ps1():
    import subprocess
    secao(u"PowerShell: propriedade lida de tabela literal existe nela")

    guarda = os.path.join(RAIZ, "tools", "check_ps1_members.ps1")
    checar(u"o guarda existe", os.path.isfile(guarda))
    if not os.path.isfile(guarda):
        return

    alvos = []
    for base, ds, fs in os.walk(RAIZ):
        ds[:] = [d for d in ds
                 if d not in (".git", ".venv", "_montagem", "__pycache__")]
        for f in fs:
            if f.lower().endswith(".ps1"):
                alvos.append(os.path.join(base, f))
    checar(u"achei os .ps1 do projeto", len(alvos) >= 4,
           u"%d encontrado(s)" % len(alvos))

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "exit 0"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
    except Exception:
        checar(u"PULADO: sem PowerShell nesta maquina", True,
               u"o guarda nao rodou -- rode a bateria numa maquina com "
               u"PowerShell antes de empacotar")
        return

    ruins = []
    for a in sorted(alvos):
        p = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", guarda, "-Arquivo", a],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        saida = p.stdout.decode("cp1252", "replace")
        for linha in saida.splitlines():
            if linha.startswith(("FALTA", "PARSE")):
                ruins.append((os.path.relpath(a, RAIZ), linha.replace("\t", " ")))
    checar(u"nenhuma propriedade ausente nos %d arquivo(s)" % len(alvos),
           not ruins,
           u" | ".join(u"%s: %s" % r for r in ruins[:4]))
    for rel, l in ruins[:8]:
        print(u"         %-28s %s" % (rel, l))


def teste_preparador_abre():
    import subprocess
    import time
    secao(u"prepare.ps1: chega a janela sem morrer")

    alvo = os.path.join(RAIZ, "packager", "prepare.ps1")
    checar(u"o preparador existe", os.path.isfile(alvo))
    if not os.path.isfile(alvo):
        return

    ORCAMENTO = 12
    try:
        p = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-STA", "-File", alvo],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL)
    except Exception as e:
        checar(u"PULADO: sem PowerShell nesta maquina", True, u"%s" % e)
        return

    t0 = time.time()
    try:
        saida = p.communicate(timeout=ORCAMENTO)[0].decode("cp1252", "replace")
        sem_tela = any(m in saida for m in (
            "ShowDialog", "Windows Forms", "STA", "no display",
            "System.Windows.Forms"))
        if sem_tela and "propriedade" not in saida.lower():
            checar(u"PULADO: esta maquina nao monta janela", True,
                   saida.strip()[:200])
            return
        checar(u"chega a janela sem morrer",
               False,
               u"morreu em %.1fs, rc=%s: %s"
               % (time.time() - t0, p.returncode, saida.strip()[:400]))
        for l in saida.splitlines()[:12]:
            if l.strip():
                print(u"         %s" % l.rstrip()[:110])
    except subprocess.TimeoutExpired:
        p.kill()
        try:
            p.communicate(timeout=30)
        except Exception:
            pass
        checar(u"chega a janela sem morrer (sobreviveu %ds)" % ORCAMENTO, True)


def teste_sem_rede_nao_e_artefato_quebrado():
    secao(u"sem rede e aviso; 404 e hash continuam sendo erro")
    import importlib.util
    import socket
    import ssl
    import urllib.error

    spec = importlib.util.spec_from_file_location(
        "_ca_rede", os.path.join(RAIZ, "build", "configurar_ambiente.py"))
    M = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(M)
    except SystemExit:
        pass

    checar(u"existe a excecao propria e o classificador",
           hasattr(M, "SemRede") and hasattr(M, "falha_de_rede"))

    de_rede = (
        (urllib.error.URLError(ssl.SSLEOFError(
            "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation "
            "of protocol (_ssl.c:1010)")), u"o caso de campo"),
        (urllib.error.URLError(socket.gaierror(11001, "getaddrinfo failed")),
         u"DNS nao resolve"),
        (TimeoutError("timed out"), u"tempo esgotado"),
        (OSError("[WinError 10054] conexao existente forcibly closed"),
         u"conexao derrubada"),
    )
    for e, rot in de_rede:
        checar(u"%s -> e rede" % rot, M.falha_de_rede(e) is True)

    de_artefato = (
        (urllib.error.HTTPError("u", 404, "Not Found", {}, None), u"404"),
        (RuntimeError("CONFERENCIA FALHOU (download) sha256 nao bate"),
         u"hash que nao bate"),
        (RuntimeError("download incompleto: x tem 3 MB, esperado > 20 MB"),
         u"download truncado"),
    )
    for e, rot in de_artefato:
        checar(u"%s -> NAO e rede (continua sendo erro)" % rot,
               M.falha_de_rede(e) is False)

    fonte = ler("build/configurar_ambiente.py")
    checar(u"o laco das etapas trata `SemRede` em separado",
           "except SemRede as e:" in fonte)
    checar(u"e a tela dele nao diz FALHOU nem manda corrigir",
           "SEM CONEXAO nesta etapa" in fonte)
    checar(u"o `.parcial` e apagado quando a conexao cai",
           "parcial.unlink()" in fonte)
    checar(u"modelo de comparacao sem rede nao para a montagem",
           "o aplicativo funciona normalmente" in fonte)

    import types as _types
    _fonte_mod = M

    def _com_falhas(erro, quantas):
        estado = {"n": 0}

        def _falso(url, alvo, reporthook=None):
            estado["n"] += 1
            if estado["n"] <= quantas:
                raise erro
            io.open(alvo, "wb").write(b"x" * 4096)
            return alvo, None

        velho = _fonte_mod.urllib.request.urlretrieve
        d = tempfile.mkdtemp(prefix="radai_rede_")
        try:
            _fonte_mod.urllib.request.urlretrieve = _falso
            alvo = os.path.join(d, "a.bin")
            try:
                _fonte_mod.baixar("https://exemplo/a.bin", alvo)
                return estado["n"], None
            except Exception as e:
                return estado["n"], e
        finally:
            _fonte_mod.urllib.request.urlretrieve = velho
            shutil.rmtree(d, ignore_errors=True)

    _eof = Exception("<urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING] "
                     "EOF occurred in violation of protocol>")
    n, err = _com_falhas(_eof, 1)
    checar(u"uma falha de rede NAO mata o preparo",
           err is None and n == 2, u"tentativas=%d erro=%s" % (n, err))
    n, err = _com_falhas(_eof, 99)
    checar(u"  e tres seguidas viram `SemRede`",
           isinstance(err, M.SemRede) and n == 3,
           u"tentativas=%d erro=%s" % (n, type(err).__name__))
    _404 = Exception("HTTP Error 404: Not Found")
    n, err = _com_falhas(_404, 99)
    checar(u"  mas um 404 para na primeira",
           err is not None and not isinstance(err, M.SemRede) and n == 1,
           u"tentativas=%d erro=%s" % (n, type(err).__name__))


def teste_autoteste_percorre_a_tela():
    import subprocess
    import time
    secao(u"o autoteste percorre a tela de verdade (janela, cliques, medidas)")

    alvo = os.path.join(RAIZ, "packager", "prepare.ps1")
    if not os.path.isfile(alvo):
        checar(u"o preparador existe", False)
        return

    amb = dict(os.environ)
    amb["RADAI_PREPARADOR_AUTOTESTE"] = "1"
    amb["RADAI_LOG_PREPARADOR"] = "bateria"
    _appdata = tempfile.mkdtemp(prefix="radai_prep_appdata_")
    os.makedirs(os.path.join(_appdata, "RadioterapiaAI"))
    io.open(os.path.join(_appdata, "RadioterapiaAI", "idioma.txt"), "w",
            encoding="ascii").write(u"pt-BR")
    amb["APPDATA"] = _appdata
    import http.server as _hs
    import threading as _th

    class _Nao(_hs.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass
    _srv404 = _hs.ThreadingHTTPServer(("127.0.0.1", 0), _Nao)
    _th.Thread(target=_srv404.serve_forever, daemon=True).start()
    amb["RADAI_PREPARADOR_URL_NAO_ACHADA"] = (u"http://127.0.0.1:%d/releases/latest"
                                       % _srv404.server_address[1])
    try:
        p = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-STA", "-File", alvo],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, env=amb)
        saida = p.communicate(timeout=180)[0].decode("cp1252", "replace")
    except Exception as e:
        checar(u"PULADO: nao consegui subir a janela", True, u"%s" % e)
        return
    finally:
        shutil.rmtree(_appdata, ignore_errors=True)
        try:
            _srv404.shutdown()
            _srv404.server_close()
        except Exception:
            pass

    linhas = [l.rstrip() for l in saida.splitlines() if l.strip()]
    marc = {}
    for l in linhas:
        p_ = l.split("\t")
        marc.setdefault(p_[0], []).append(p_[1:])

    if u"FIM" not in marc:
        if any(m in saida for m in ("ShowDialog", "STA", "no display")):
            checar(u"PULADO: esta maquina nao monta janela", True,
                   saida.strip()[:160])
            return
        checar(u"o autoteste chega ao fim", False, saida.strip()[-400:])
        return
    checar(u"o autoteste chega ao fim", True, u"%d linhas" % len(linhas))

    abas_ = (marc.get(u"ABAS") or [[u"0", u""]])[0]
    titulos = abas_[1].split(u"|") if len(abas_) > 1 else []
    checar(u"a trilha tem CINCO abas", abas_[0] == u"5", abas_)
    checar(u"  e nenhuma e a de plugins",
           not any(u"Modelos" in t or u"tarefas" in t for t in titulos),
           titulos)
    checar(u"  e depois das licencas vem o preparo",
           len(titulos) == 5 and titulos[2].startswith(u"2 ")
           and titulos[3].startswith(u"3 ") and u"Prepar" in titulos[3]
           and titulos[4].startswith(u"4 "), titulos)

    def _so_ascii(t):
        return re.sub(u"[^A-Za-z0-9 ().]", u"", t)
    esperado = [u"Instalar / Atualizar app nesta máquina",
                u"Máquina offline: instalar de um pacote que eu trouxe",
                u"Máquina com internet: montar um pacote para levar para a máquina offline",
                u"Desinstalar"]
    for chave, oque in ((u"ORDEM", u"na tela"), (u"ORDEMTAB", u"no Tab")):
        vistos = ((marc.get(chave) or [[u""]])[0][0]).split(u"|")
        ok = (len(vistos) == 4 and
              all(_so_ascii(v) == _so_ascii(e) for v, e in zip(vistos, esperado)))
        checar(u"os botoes da aba 0 %s: o unico Instalar / Atualizar, as duas "
               u"opcoes da maquina offline e o Desinstalar, quatro botoes" % oque,
               ok, vistos)

    _cat = json.load(io.open(os.path.join(RAIZ, "packager", "catalogo.json"),
                             encoding="utf-8"))
    _p = _cat.get("pacote") or {}
    tam = (marc.get(u"TAMANHO") or [[]])[0]
    checar(u"a janela carregou o tamanho do CATALOGO, e nao a reserva",
           len(tam) >= 6 and tam[5].startswith(u"catalogo.json"),
           tam[5:6] if len(tam) >= 6 else tam)
    if len(tam) >= 5 and _p:
        checar(u"  pacote, disco e download batem com o catalogo",
               abs(float(tam[0].replace(u",", u".")) - _p["pacote_gib"]) < 0.05
               and abs(float(tam[1].replace(u",", u".")) - _p["disco_gib"]) < 0.05
               and abs(float(tam[2].replace(u",", u".")) - _p["download_gib"]) < 0.05,
               u"%s contra %s" % (tam[:3], (_p["pacote_gib"], _p["disco_gib"],
                                          _p["download_gib"])))
        checar(u"  e as contagens tambem (tarefas, modelos)",
               tam[3] == str(_p["tarefas"]) and tam[4] == str(_p["modelos"]),
               tam[3:5])
    _gb = lambda v: u"%.0f" % v
    pasta = (marc.get(u"PASTA") or [[u""]])[0][0]
    if _p:
        checar(u"o rotulo da pasta pede o disco do catalogo (%s GB)"
               % _gb(_p["disco_gib"]),
               (u"cerca de %s GB" % _gb(_p["disco_gib"])) in pasta, pasta)
    aba1 = (marc.get(u"ABA1") or [[u"", u""]])[0]
    checar(u"o visor da aba 1 nao mostra marcador cru",
           aba1[0] == u"ok", aba1[0])
    if _p and len(aba1) > 1:
        checar(u"  e diz o pacote (%s GB) e o download (%s GB) do catalogo"
               % (_gb(_p["pacote_gib"]), _gb(_p["download_gib"])),
               (u"cerca de %s GB" % _gb(_p["pacote_gib"])) in aba1[1]
               and (u"cerca de %s GB" % _gb(_p["download_gib"])) in aba1[1],
               aba1[1][:120])
    ico = (marc.get(u"ICONE") or [[u""]])[0][0]
    checar(u"a janela do preparador usa o favicon.ico", ico == u"favicon.ico",
           ico)
    aba0 = (marc.get(u"ABA0") or [[u""]])[0][0]
    _titulos0 = [u"Confere se o programa", u"instala o .zip preparado",
                 u"Baixa tudo e gera um .zip", u"Mostra o que vai apagar"]
    _pos0 = [aba0.find(t) for t in _titulos0]
    checar(u"o texto da aba 0 explica na ordem dos botoes: instalar ou "
           u"atualizar, arquivo, levar, desinstalar",
           all(p >= 0 for p in _pos0) and _pos0 == sorted(_pos0),
           u"posicoes %s | %s" % (_pos0, aba0[:120]))

    for frase in (u"preparador iniciado", u"janela aberta",
                  u"janela fechada; fim normal"):
        checar(u"o log de sessao tem «%s»" % frase, frase in saida,
               u"sem esta linha o log nao distingue fim normal de morte")

    conf = marc.get(u"AUTOCONF", [])
    checar(u"a conferencia de versao roda no autoteste (5 casos)",
           len(conf) == 5, u"%d caso(s)" % len(conf))
    checar(u"e nenhum deles levanta excecao",
           not any(len(c) > 1 and c[1] == u"ERRO" for c in conf),
           u"; ".join(u" ".join(c) for c in conf if len(c) > 1
                      and c[1] == u"ERRO")[:110])
    por_caso = {c[0]: c[1:] for c in conf if len(c) >= 2}
    checar(u"versao publicada maior -> `velho`",
           (por_caso.get(u"ha versao nova") or [u""])[0] == u"velho",
           str(por_caso.get(u"ha versao nova")))
    checar(u"versao publicada menor -> `atual`",
           (por_caso.get(u"estou em dia") or [u""])[0] == u"atual",
           str(por_caso.get(u"estou em dia")))
    sem = por_caso.get(u"sem resposta") or [u"", u""]
    checar(u"sem resposta -> `sem_resposta`, e NUNCA `atual`",
           sem[0] == u"sem_resposta", str(sem))
    checar(u"e a frase traz o motivo", len(sem) > 1 and u"proxy" in sem[1],
           str(sem)[:90])

    rede = por_caso.get(u"sem rede") or [u"", u""]
    checar(u"a funcao de rede e EXECUTADA (cache vazio, porta morta)",
           bool(rede[0]), u"(o autoteste nao emitiu o caso `sem rede`)")
    checar(u"e ela nao levanta -- ela devolve `falhou` com motivo",
           rede[0] == u"falhou",
           u"%s -- ERRO aqui e excecao dentro de VersaoPublicada" % str(rede))

    priv = por_caso.get(u"404") or [u"", u""]
    checar(u"o 404 e' exercido no autoteste",
           priv[0] == u"falhou", str(priv)[:160])
    _pt = priv[1] if len(priv) > 1 else u""

    def _diz_o_404(t):
        return (u"respondeu 404" in t and u"esta errado" in t
                and u"release publicada" in t and u"privad" not in t
                and u"conta" not in t)
    checar(u"  e a frase diz o que um 404 quer dizer com o repositorio "
           u"publico: endereco errado ou release que nao existe",
           _diz_o_404(_pt), _pt[:160])
    checar(u"  (isca) a frase de antes, que dizia repositorio privado, e "
           u"acusada", not _diz_o_404(
               u"o repositorio e privado: no navegador, quem entra com uma "
               u"conta autorizada ve as versoes, mas este programa nao usa "
               u"conta e nao consegue compara-las."))
    checar(u"  e a frase de repositorio privado saiu do preparador",
           u"o repositorio e privado" not in io.open(
               alvo, encoding="utf-8-sig").read())
    checar(u"  e da o link permanente do instalador",
           u"/releases/latest/download/" in _pt
           and _pt.rstrip().endswith(u"_SETUP_LATEST.zip"), _pt[-120:])
    checar(u"  e a frase velha («nao ha release publica») saiu da tela",
           u"nao ha release publica" not in _pt
           and u"(T 'nao ha release publica" not in io.open(
               alvo, encoding="utf-8-sig").read(), _pt[:80])

    prep_src = ler(os.path.join("packager", "prepare.ps1"))
    n_restritos = prep_src.count(u"restritiva = $true")
    fin = marc.get(u"FINALIDADE", [])
    checar(u"o autoteste percorreu a tela de licencas", bool(fin),
           u"(nao emitido)")
    if fin:
        seletor = fin[0][0]
        restritas = fin[0][1]
        botao = fin[0][2]
        checar(u"o pacote de hoje nao tem componente de uso restrito",
               n_restritos == 0,
               u"%d na tabela de licencas -- se voltou um, a pergunta de "
               u"finalidade tem de voltar junto" % n_restritos)
        checar(u"e por isso nao ha pergunta de finalidade a responder",
               seletor == u"seletor=ausente", seletor)
        checar(u"a tela nao lista nenhuma licenca de dupla resposta",
               restritas == u"restritas=0", restritas)
        checar(u"e o botao de aceitar abre sem declaracao nenhuma",
               botao == u"botao=True", botao)
        checar(u"restrito sem pergunta seria reprovado",
               not (n_restritos and seletor == u"seletor=ausente"),
               u"restritos=%d com %s" % (n_restritos, seletor))

    jan = marc.get(u"IDIOMAJANELA", [])
    checar(u"a janelinha de idioma abriu antes das abas", bool(jan),
           u"(o autoteste nao emitiu IDIOMAJANELA)")
    if jan:
        checar(u"e ela tem os controles dela",
               len(jan[0]) > 1 and jan[0][1] != u"controles=0", jan[0])

    _mc = (marc.get(u"MARCA") or [[]])[0]
    marca = dict(x.split(u"=", 1) for x in _mc if u"=" in x)
    checar(u"a splash NAO mostra imagem (so o logotipo tipografico)",
           marca.get(u"imagens") == u"0", _mc[:1] or u"(sem MARCA)")
    try:
        _topo = int(marca.get(u"topo", u"999"))
    except ValueError:
        _topo = 999
    checar(u"  e a marca subiu para o alto da janela (sem o buraco da imagem)",
           _topo <= 40, u"topo=%s" % marca.get(u"topo"))

    _cb = (marc.get(u"CABECALHO") or [[]])[0]
    cab = dict(x.split(u"=", 1) for x in _cb if u"=" in x)
    try:
        _vn, _va = int(cab.get(u"vao", u"-9")), int(cab.get(u"vao_antigo", u"-9"))
    except ValueError:
        _vn = _va = -9
    checar(u"o cabecalho mediu as duas montagens", _vn >= 0 and _va >= 0,
           u"%s" % _cb)
    checar(u"  (isca) a montagem antiga TEM o vao que o autor viu",
           _va >= 6, u"vao_antigo=%s" % _va)
    checar(u"  e a marca de hoje encosta as duas metades",
           0 <= _vn <= max(3, _va // 2) and _vn < _va,
           u"vao=%s vao_antigo=%s" % (_vn, _va))
    checar(u"  e o Paint rodou sem erro", cab.get(u"pintado") == u"ok",
           cab.get(u"pintado"))
    checar(u"  e o titulo radioterapia.ai, pintado sem erro",
           marca.get(u"titulo") == u"radioterapia.ai"
           and marca.get(u"pintado") == u"ok",
           u"%s | %s" % (marca.get(u"titulo"), marca.get(u"pintado")))
    try:
        _cl, _az, _vi = [int(x) for x in marca.get(u"pixels", u"").split(u"/")]
    except ValueError:
        _cl = _az = _vi = 0
    checar(u"  e ele CHEGOU a tela: letras claras e as duas pontas do "
           u"gradiente do .ai", _cl >= 50 and _az >= 5 and _vi >= 5,
           u"claros/azuis/violetas = %s" % marca.get(u"pixels"))
    checar(u"  com o subtitulo LOCAL SUITE",
           marca.get(u"sub", u"").lower() == u"local suite", marca.get(u"sub"))
    checar(u"  e logo, titulo e subtitulo EM CIMA da pergunta do idioma",
           marca.get(u"ordem") == u"ok", marca.get(u"ordem"))

    _ent = _entrega()
    _v = (marc.get(u"VERSOES") or [[u"", u"", u""]])[0] + [u"", u"", u""]
    checar(u"a aba 0 diz a versao do instalador, lida do entrega.txt "
           u"(v%s)" % _ent.get(u"VERSAO"),
           _v[0] == u"Instalador v%s" % _ent.get(u"VERSAO"), _v[0])
    checar(u"  e o pacote de transferencia mais antigo que ele aceita "
           u"(v%s)" % _ent.get(u"BUNDLE_MINIMO"),
           _v[1] == (u"Aceita pacote de transferencia (bundle) versao %s ou "
                     u"superior" % _ent.get(u"BUNDLE_MINIMO")), _v[1])
    checar(u"  lido do BUNDLE_MINIMO, e nao do recuo",
           _v[2] == u"entrega.txt", _v[2])

    fora = marc.get(u"FORA", [])
    checar(u"nenhum clicavel caiu fora da aba", not fora,
           u"; ".join(u" ".join(f[:4]) for f in fora[:3]))

    cliques = marc.get(u"CLIQUE", [])
    checar(u"todos os botoes foram clicados", len(cliques) >= 5,
           u"%d cliques" % len(cliques))
    parados = [c for c in cliques if len(c) > 1 and c[1] != u"ok"]
    checar(u"nenhum botao ficou parado na propria aba", not parados,
           u"; ".join(u" ".join(c) for c in parados[:3]))

    antes = marc.get(u"MODO3ANTES", [])
    checar(u"a aba 2 esta travada ANTES de o modo 3 ser escolhido",
           bool(antes) and antes[0][0] == u"licencas=False",
           antes[0][0] if antes else u"(nao emitido)")

    ps1 = io.open(alvo, encoding="utf-8-sig").read()
    checar(u"os botoes antigos do bloco Atualizar sairam (tudo, so o app, de um pacote)",
           all(x not in ps1 for x in (u"$btModo7", u"$btModo8", u"'Atualizar só o app'",
                                      u"'Atualizar de um pacote que eu trouxe (.zip)'")),
           u"um segundo botao de atualizar devolve a escolha que a cascata faz")
    i = ps1.find("$btModo5.Add_Click({")
    cabeca = ps1[i:i + 300] if i >= 0 else u""
    checar(u"`$btModo5` pergunta a pasta antes de agir",
           "GarantirInstalacao" in cabeca
           and "if (-not $inst) { return }" in cabeca,
           cabeca[:120].replace(u"\n", u" "))
    checar(u"o botao Atualizar app separado saiu: um botao so instala ou atualiza",
           u"$btModo4" not in ps1 and u"'Atualizar app' 20" not in ps1,
           u"dois botoes devolvem ao operador a escolha que a conferencia faz")
    _f = _funcoes_ps(u"packager/prepare.ps1", [u"InstalarOuAtualizar"]).get(u"InstalarOuAtualizar", u"")
    checar(u"o botao unico confere a instalacao e escolhe entre a cascata e o instalar tudo",
           u"$btModo1.Add_Click({ [void](InstalarOuAtualizar) })" in ps1
           and u"ConferirInstalacao" in _f and u"IniciarAtualizarApp" in _f
           and u"MarcarModo '1'" in _f and u"GarantirInstalacao" not in _f,
           _f[:160].replace(u"\n", u" "))
    _bt = {}
    for _v in marc.get(u"BOTAO", []):
        if _v:
            _bt[_v[0]] = dict(x.split(u"=", 1) for x in _v[1:] if u"=" in x)
    checar(u"o autoteste clicou o botao unico nos quatro fantomas",
           sorted(_bt) == [u"marca", u"quase", u"registro", u"vazio"], sorted(_bt))
    _sem = {u"modo": u"1", u"cascata": u"", u"como": u"-", u"aba": u"1",
            u"desinstalar": u"False"}
    checar(u"  sem instalacao: instala tudo (modo 1, aba 1), sem cascata",
           _bt.get(u"vazio") == _sem, _bt.get(u"vazio"))
    checar(u"  (isca) registro que aponta pasta sem marca e pasta sem entrega.txt "
           u"nao contam: instala tudo",
           _bt.get(u"quase") == _sem, _bt.get(u"quase"))
    checar(u"  com instalacao pelo registro unico (pasta fora das raizes): vai a "
           u"cascata nela, e nao instala",
           _bt.get(u"registro") == {u"modo": u"", u"cascata": u"<base>\\outro_disco\\LOCAL_SUITE",
                                    u"como": u"registro", u"aba": u"0",
                                    u"desinstalar": u"True"}, _bt.get(u"registro"))
    checar(u"  com instalacao pela marca na pasta: vai a cascata nela, e nao instala",
           _bt.get(u"marca") == {u"modo": u"", u"cascata": u"<base>\\marca\\LOCAL_SUITE",
                                 u"como": u"marca", u"aba": u"0",
                                 u"desinstalar": u"True"}, _bt.get(u"marca"))

    for chave, oque in ((u"PORTAOK", u"os dois botoes nascem acesos"),
                        (u"IDIOMASYNC", u"os dois seletores de idioma nao divergem"),
                        (u"ESTADO", u"o painel de estado acompanha a troca de "
                                    u"idioma (pasta apontada a mao)"),
                        (u"VERSOESPOS", u"as linhas de versao cabem entre o "
                                        u"painel de estado e a pergunta"),
                        (u"VERSOESTROCA", u"e acompanham a troca de idioma, "
                                          u"com o numero dentro"),
                        (u"MODO3OK", u"o modo 3 solta a aba 2, que ele nao usa"),
                        (u"MODO3CLIQUE", u"e a soltura sobrevive a mexer numa caixa"),
                        (u"VOLTAOK", u"voltar do modo 3 apaga o que ele escreveu"),
                        (u"LINHAS", u"a porta tem o botao unico em destaque (maior, "
                                    u"cheio, fonte maior), as duas opcoes menores lado "
                                    u"a lado, o Desinstalar discreto, e cada botao a sua "
                                    u"explicacao curta embaixo"),
                        (u"DIRETO", u"instalar nesta maquina aponta a pasta FINAL "
                                    u"(a instalacao achada ou a padrao), nunca «preparo»"),
                        (u"TODAS", u"aceitar todas marca cada caixa NA TELA e leva ao preparo"),
                        (u"LINHASLIC", u"cada componente tem UMA linha: nome, licenca, o que "
                                       u"permite e o link da origem"),
                        (u"PACOTE", u"o pacote para levar nao nasce dentro da pasta do "
                                    u"programa"),
                        (u"MODO7", u"o modo 7 (o ramo «atualizar tudo» da cascata) fixa a "
                                   u"pasta instalada"),
                        (u"LIVRE", u"e a pasta volta a ser livre fora deles")):
        v = marc.get(chave, [])
        checar(oque, bool(v) and v[0][0] == u"ok",
               (v[0][0] if v else u"o autoteste nao emitiu %s" % chave))

    idi = marc.get(u"IDIOMA", [])
    _n = 0
    if idi:
        try:
            _n = int(str(idi[0][0]).split("=")[-1])
        except Exception:
            _n = 0
    checar(u"ha pelo menos dois seletores de idioma", _n >= 2,
           idi[0][0] if idi else u"(nao emitido)")
    _combo = 0
    if idi:
        try:
            _combo = int(str(idi[0][-1]).split("=")[-1])
        except Exception:
            _combo = -1
    checar(u"e a aba 0 NAO repete a pergunta do idioma", _combo == 0,
           idi[0][-1] if idi else u"(nao emitido)")

    cl = [v for v in marc.get(u"CLIQUE", [])
          if v and u"Aceitar todas" in v[0]]
    checar(u"o aceite das licencas leva direto ao preparo (aba 3)",
           bool(cl) and cl[0][1] == u"ok" and cl[0][2].endswith(u"-> 3"),
           (u"%s" % (cl[0] if cl else u"(o autoteste nao clicou)")))
    ly = marc.get(u"LOGY", [])
    checar(u"e o log da aba 4 comeca ABAIXO do rotulo",
           bool(ly) and ly[0][0] == u"ok",
           (ly[0][0] if ly else u"(nao emitido)"))


def teste_o_catalogo_json_nao_diverge_do_python():
    secao(u"o catalogo.json nao diverge do Python")
    import json
    cam = os.path.join(RAIZ, "packager", "catalogo.json")
    checar(u"o catalogo.json existe", os.path.isfile(cam), cam)
    if not os.path.isfile(cam):
        return
    dados = json.loads(io.open(cam, encoding="utf-8").read())

    sys.path.insert(0, os.path.join(RAIZ, "app"))
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import gerar_catalogo
    vivo = gerar_catalogo.montar()

    for chave in ("tasks", "modelos"):
        a, b = dados.get(chave) or [], vivo.get(chave) or []
        checar(u"%s: mesma quantidade" % chave, len(a) == len(b),
               u"json %d, python %d \u2014 rode build/gerar_catalogo.py"
               % (len(a), len(b)))
        for x, y in zip(a, b):
            if x != y:
                dif = sorted(k for k in set(list(x) + list(y))
                             if x.get(k) != y.get(k))
                checar(u"  %s `%s` confere" % (chave, x.get("task") or x.get("id")),
                       False, u"campos: %s" % ", ".join(dif))
                break
        else:
            if len(a) == len(b):
                checar(u"  %s: toda entrada confere" % chave, True)

    pa, pb = dados.get("pacote") or {}, vivo.get("pacote") or {}
    checar(u"o bloco `pacote` existe e confere com o Python vivo",
           bool(pa) and pa == pb,
           u"json %s, python %s -- rode build/gerar_catalogo.py"
           % (pa.get("pacote_gib"), pb.get("pacote_gib")))
    if pa:
        mb = (sum(t["mb"] for t in dados["tasks"])
              + sum(m["mb"] for m in dados["modelos"] if not m["nucleo"]))
        conta = round(pa["base_gib"] + pa["fator_disco"] * mb / 1024.0, 1)
        checar(u"  e o pacote e' a conta das parcelas (%.1f GiB)" % conta,
               abs(pa["pacote_gib"] - conta) < 0.051,
               u"pacote %s" % pa["pacote_gib"])
        import gerar_catalogo as _G
        checar(u"  e o disco e' o teto do dobro mais a folga (%s GiB)"
               % pa.get("disco_gib"),
               abs(pa["disco_gib"] - _G.disco_para_preparar(pa["pacote_gib"]))
               < 0.051 and pa.get("folga_gib") == _G.FOLGA_GIB,
               u"disco %s, folga %s" % (pa["disco_gib"], pa.get("folga_gib")))
        checar(u"  e ele pede MAIS que os 38,1 GiB medidos num preparo completo",
               pa["disco_gib"] > 38.1,
               u"%s GiB: o disco com exatamente isso livre enche no fim"
               % pa["disco_gib"])
        _novos = sum(float(m.get("mb") or 0)
                     for m in (dados.get("modelos") or ())
                     if m.get("id") in ("cranio_buti",))
        _alvo = 18.97 + float(pa.get("fator_disco") or 1.0) * _novos / 1024.0
        checar(u"  e fica perto do medido na montagem (18,97 GiB, +-1,5, mais "
               u"o modelo do encefalo: alvo %.2f GiB)" % _alvo,
               abs(pa["pacote_gib"] - _alvo) <= 1.5,
               u"%s GiB -- remeca a BASE (montagem - ts_weights - modelos) "
               u"em build/gerar_catalogo.py" % pa["pacote_gib"])

    import engine
    for ta in dados["tasks"]:
        checar(u"  `%s`: nucleo bate com `alimenta_o_entregue`" % ta["task"],
               bool(ta["nucleo"]) == bool(engine.alimenta_o_entregue(ta["task"])),
               u"json diz %s" % ta["nucleo"])


def teste_o_recibo_mede_o_pacote_e_nao_repete_o_pedido():
    secao(u"o recibo mede o pacote, e nao repete o pedido")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import configurar_ambiente as C
    import radai_tasks as K

    base = tempfile.mkdtemp(prefix="radai_recibo_")
    try:
        b = os.path.join(base, "bundle")
        pesos = os.path.join(b, "ts_weights")
        mods = os.path.join(b, "modelos")
        os.makedirs(pesos)
        os.makedirs(mods)

        checar(u"pacote sem peso nenhum leva zero task",
               C.tasks_levadas(b) == [], C.tasks_levadas(b))
        checar(u"  e zero modelo", C.modelos_levados(b) == [])

        base_ct = K.BASES_CT[0]
        for d in K.datasets_necessarios(base_ct):
            os.makedirs(os.path.join(pesos, "Dataset%03d_x" % int(d)))
        checar(u"com os datasets da base no disco, ela conta como levada",
               base_ct in C.tasks_levadas(b), C.tasks_levadas(b))

        parcial = None
        for t in C._tasks_do_catalogo():
            ds = list(K.datasets_necessarios(t))
            if len(ds) > 1 and t != base_ct:
                parcial = (t, ds)
                break
        if parcial:
            t, ds = parcial
            os.makedirs(os.path.join(pesos, "Dataset%03d_x" % int(ds[0])),
                        exist_ok=True)
            checar(u"task com peso PELA METADE nao entra no recibo "
                   u"(`%s`, %d de %d datasets)" % (t, 1, len(ds)),
                   t not in C.tasks_levadas(b))
        else:
            checar(u"(nenhuma task do catalogo tem mais de um dataset)", True)

        import radai_models as RM
        conhecido = sorted(RM.MODELOS)[0]
        os.makedirs(os.path.join(mods, conhecido))
        io.open(os.path.join(mods, conhecido, "peso.bin"), "w").write(u"x")
        os.makedirs(os.path.join(mods, "vazia"))
        os.makedirs(os.path.join(mods, "forasteira"))
        io.open(os.path.join(mods, "forasteira", "p.bin"), "w").write(u"x")

        achados = C.modelos_levados(b)
        checar(u"modelo com peso na pasta entra no recibo",
               conhecido in achados, achados)
        checar(u"  pasta VAZIA nao entra (sobra de download interrompido: "
               u"prometeria um motor que nao roda)",
               "vazia" not in achados and "vazia(?)" not in achados, achados)
        checar(u"  e pasta que o registro nao conhece entra MARCADA, "
               u"nao some (o recibo diz o que ESTA no pacote)",
               "forasteira(?)" in achados, achados)

        import inspect
        for f in (C.tasks_levadas, C.modelos_levados):
            args = list(inspect.signature(f).parameters)
            checar(u"`%s` recebe SO o pacote — nao ha por onde o pedido "
                   u"entrar" % f.__name__, args == ["bundle"], args)

        recibo = os.path.join(b, "plugins.txt")
        io.open(recibo, "w", encoding="utf-8").write(
            u"VERSAO=9.9\nTASKS=%s\nMODELOS=%s\n" % (base_ct, conhecido))
        levadas, achados2 = C.escrever_recibo_medido(b)
        txt = io.open(recibo, encoding="utf-8").read()
        linhas = dict(l.split("=", 1) for l in txt.splitlines()
                      if "=" in l and not l.startswith("#"))

        checar(u"o recibo GRAVADO tem a linha `LEVADO=`", "LEVADO" in linhas)
        checar(u"e a linha `MODELOS_LEVADOS=` — a que faltava",
               "MODELOS_LEVADOS" in linhas, sorted(linhas))
        checar(u"  `LEVADO` bate com a medida", "LEVADO" in linhas
               and linhas["LEVADO"] == ",".join(levadas))
        checar(u"  `MODELOS_LEVADOS` bate com a medida",
               "MODELOS_LEVADOS" in linhas
               and linhas["MODELOS_LEVADOS"] == ",".join(achados2))
        checar(u"  e o PEDIDO continua no arquivo (a diferenca entre os "
               u"dois é a informação)",
               linhas.get("TASKS") == base_ct
               and linhas.get("MODELOS") == conhecido)
        checar(u"as duas dizem coisas DIFERENTES neste pacote — é o caso "
               u"que o recibo existe para mostrar",
               linhas.get("MODELOS") != linhas.get("MODELOS_LEVADOS"),
               (linhas.get("MODELOS"), linhas.get("MODELOS_LEVADOS")))

        C.escrever_recibo_medido(b)
        txt2 = io.open(recibo, encoding="utf-8").read()
        checar(u"rodar de novo deixa o recibo BYTE A BYTE igual "
               u"(`--etapas 7` é o conselho do próprio preparo)",
               txt2 == txt, "o recibo mudou na segunda passada")
        checar(u"  e cada linha aparece UMA vez",
               txt2.count("LEVADO=") == 1
               and txt2.count("MODELOS_LEVADOS=") == 1,
               (txt2.count("LEVADO="), txt2.count("MODELOS_LEVADOS=")))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_a_selecao_nunca_tira_o_nucleo():
    secao(u"a selecao nunca tira o nucleo")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import configurar_ambiente as C

    checar(u"o nucleo nao esta vazio", len(C.NUCLEO) > 0, str(len(C.NUCLEO)))
    import radai_tasks as _K
    checar(u"  e a base anatomica esta nele", _K.BASES_CT[0] in C.NUCLEO,
           u"sem ela o RadAI_OAR sai sem pulmao, coracao e osso")
    import engine
    checar(u"  e todo membro dele alimenta o entregue",
           all(engine.alimenta_o_entregue(x) for x in C.NUCLEO))

    for _r in sorted(_K.RESERVAS):
        checar(u"  e a reserva `%s` fica FORA dele" % _r,
               _r not in C.NUCLEO,
               u"o pacote levaria as duas bases: 2,9 GB onde 1,77 basta")
        checar(u"    (e ela e' a proxima da ordem de preferencia)",
               _K.reserva_de(_K.BASES_CT[0]) == _r or _r not in _K.BASES_CT,
               u"`reserva_de` deriva de BASES_CT, e nao de uma lista nova")

    checar(u"o completo contem o nucleo",
           all(x in C.TASKS for x in C.NUCLEO))
    checar(u"a funcao da selecao saiu junto com a selecao",
           not hasattr(C, "tasks_pedidas"),
           u"funcao que ignora o argumento guarda so' a si mesma")
    import radai_tasks as _KK

    class _Sentinela(Exception):
        pass

    _v = (C.baixar_pesos_ts, C.titulo, C.log)
    pedidos = []
    extras = []
    trab = tempfile.mkdtemp(prefix="radai_prep_pesos_")
    try:
        def _baixar(py, tasks, pesos, cache, extra=(), env=None, oficina=None):
            pedidos.extend(tasks)
            extras.extend(extra)
            raise _Sentinela("fim do laco")
        C.baixar_pesos_ts = _baixar
        C.titulo = lambda *a, **kw: None
        C.log = lambda *a, **kw: None
        parou = u""
        try:
            C.etapa_pesos({"bundle": __import__("pathlib").Path(trab),
                           "py": "py-dublado", "preparo": trab})
        except _Sentinela as e:
            parou = u"%s" % e
        checar(u"a etapa de pesos chegou ao download (dublado)",
               u"fim do laco" in parou, parou[:120])
        esperado = [_KK.nome_na_biblioteca(t) for t in C.TASKS]
        checar(u"`etapa_pesos` pede o CATALOGO INTEIRO (%d tasks), pelo "
               u"nome da biblioteca" % len(esperado), pedidos == esperado,
               u"pediu %d: %s" % (len(pedidos),
                                  sorted(set(esperado) - set(pedidos))[:4]))
        checar(u"  e os localizadores de recorte vao JUNTO (datasets_do_pacote)",
               sorted(extras) == sorted(_KK.datasets_do_pacote(list(C.TASKS))),
               u"%s" % sorted(extras)[:8])
    finally:
        C.baixar_pesos_ts, C.titulo, C.log = _v
        shutil.rmtree(trab, ignore_errors=True)

    import subprocess as _sp
    for flag in (u"--tasks=", u"--modelos=hnlnl"):
        trab = tempfile.mkdtemp(prefix="radai_prep_cli_")
        try:
            alvo = os.path.join(trab, "preparo")
            r = _sp.run([sys.executable,
                         os.path.join(RAIZ, "build", "configurar_ambiente.py"),
                         "--preparo", alvo, flag],
                        capture_output=True, timeout=120)
            txt = (r.stdout + r.stderr).decode("utf-8", "replace")
            checar(u"`%s` e' RECUSADO com o motivo" % flag,
                   r.returncode != 0 and u"nao sao mais opcoes do preparo" in txt,
                   u"rc=%s: %s" % (r.returncode, txt.strip()[-160:]))
            checar(u"  e nada foi criado no disco",
                   not os.path.exists(alvo),
                   u"a recusa veio depois de criar a pasta de trabalho")
        finally:
            shutil.rmtree(trab, ignore_errors=True)


def teste_a_base_tem_reserva_e_ela_so_baixa_quando_precisa():
    secao(u"a base anatomica tem reserva, e ela so baixa quando precisa")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    import configurar_ambiente as C
    import radai_tasks as K

    PREF = K.BASES_CT[0]
    RES = K.reserva_de(PREF)
    checar(u"a base preferida tem reserva declarada", bool(RES),
           u"%s -> %s" % (PREF, RES))
    if not RES:
        return
    D_PREF = set(K.datasets_necessarios(PREF, recorte_no_corpo=False))
    D_RES = set(K.datasets_necessarios(RES, recorte_no_corpo=False))
    checar(u"  e as duas pedem datasets DIFERENTES",
           D_PREF and D_RES and not (D_PREF & D_RES),
           u"se fossem os mesmos, a reserva nao seria reserva de nada")

    v_rodar, v_baix, v_log = C.baixar_pesos_ts, K.baixados, C.log
    chamadas = []
    ditas = []
    try:
        C.baixar_pesos_ts = (lambda py, tasks, pesos, cache, extra=(),
                             env=None, oficina=None:
                             chamadas.append((u"baixar %s" % u",".join(tasks),
                                              list(tasks))) or {})
        C.log = lambda m="": ditas.append(m)

        K.baixados = lambda base=None: set(D_PREF)
        chamadas[:] = []
        try:
            r = C.garantir_base((PREF,), "pesos", "py")
        except Exception as e:
            r = None
            checar(u"com a base no disco, a reserva NAO e baixada", False,
                   u"%s: %s" % (type(e).__name__, str(e)[:60]))
        else:
            checar(u"com a base no disco, a reserva NAO e baixada", not chamadas,
                   u"1,17 GB a mais em todo pacote para cobrir o que nao houve")
        checar(u"  e o alvo continua sendo a preferida", r == (PREF,), str(r))

        K.baixados = lambda base=None: set(D_RES)
        chamadas[:] = []
        ditas[:] = []
        r = C.garantir_base((PREF,), "pesos", "py")
        checar(u"sem a base no disco, a reserva e baixada", len(chamadas) == 1,
               u" | ".join(c[0] for c in chamadas))
        _cmd = chamadas[0][1] if chamadas else []
        _t = _cmd[0] if len(_cmd) == 1 else ""
        checar(u"  e a task pedida leva o nome da BIBLIOTECA (a chave do TASK_TO_ID)",
               _t == K.nome_na_biblioteca(RES),
               u"mandou %r; o CLI so conhece %r"
               % (_t, K.nome_na_biblioteca(RES)))
        checar(u"    (e esse nome e mesmo diferente do nosso)",
               K.nome_na_biblioteca(RES) != RES,
               u"se fossem iguais esta checagem nao provaria nada")
        checar(u"  e o ALVO passa a ser a reserva", r == (RES,),
               u"conferir os datasets da preferida reprovaria o pacote certo")
        checar(u"  e o log do PREPARO diz que caiu",
               any(RES in m and PREF in m for m in ditas),
               u"quem monta o pacote precisa saber que levou a reserva")

        K.baixados = lambda base=None: set()
        chamadas[:] = []
        try:
            C.garantir_base((PREF,), "pesos", "py")
            checar(u"sem base nenhuma, o preparo PARA", False,
                   u"um pacote sem base anatomica nao e um pacote menor")
        except RuntimeError as e:
            checar(u"sem base nenhuma, o preparo PARA", True)
            checar(u"  e o erro nomeia as duas", PREF in str(e) and RES in str(e),
                   str(e)[:70])

        K.baixados = lambda base=None: set()
        chamadas[:] = []
        outras = tuple(t for t in C.NUCLEO if K.reserva_de(t) is None)[:3]
        r = C.garantir_base(outras, "pesos", "py")
        checar(u"task sem reserva atravessa sem tentar nada",
               r == outras and not chamadas, str(r))

        K.baixados = lambda base=None: set(D_PREF) - {K.DATASET_BODY}
        chamadas[:] = []
        ditas[:] = []
        try:
            r = C.garantir_base((PREF,), "pesos", "py")
        except Exception as e:
            r = u"%s: %s" % (type(e).__name__, str(e)[:60])
        checar(u"base no disco SEM o Dataset300: a reserva NAO e baixada",
               not chamadas, u" | ".join(c[0] for c in chamadas))
        checar(u"  e o alvo continua sendo a preferida", r == (PREF,), str(r))
    finally:
        C.baixar_pesos_ts, K.baixados, C.log = v_rodar, v_baix, v_log

    fonte = ler("build/configurar_ambiente.py")
    import re as _re
    corpo = fonte[fonte.index(u"def etapa_pesos("):]
    _fim = corpo.find(u"\ndef ", 10)
    corpo = corpo[:_fim] if _fim > 0 else corpo
    checar(u"o recorte pegou SO a etapa_pesos", _fim > 0 and len(corpo) < 40000,
           u"%d caracteres" % len(corpo))
    checar(u"a conferencia do fim confere o ALVO, e nao o catalogo",
           u"datasets_do_pacote(list(TASKS))" not in corpo,
           u"selecao que nao chega a conferencia vira preparo completo calado")
    checar(u"  e ela confere pelo DISCO",
           u"radai_tasks.baixados(" in corpo,
           u"`rodar` devolve zero para download que nao gravou nada")


def teste_o_pacote_e_um_so():
    secao(u"o pacote e' um so': sem aba de plugins, sem selecao ao motor")
    ps1 = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                  encoding="utf-8-sig").read()
    codigo = u"\n".join(l for l in ps1.splitlines()
                        if not l.lstrip().startswith(u"#"))
    checar(u"nenhuma aba de modelos e tarefas no codigo",
           u"Modelos e tarefas" not in codigo)
    fs = _funcoes_ps(u"packager/prepare.ps1", [u"Preparar"])
    prep = fs.get(u"Preparar", u"")
    checar(u"a funcao `Preparar` foi recortada pelo parser", bool(prep),
           _motivo_ast(fs))
    prep_cod = u"\n".join(l for l in prep.splitlines()
                          if not l.lstrip().startswith(u"#"))
    checar(u"e a chamada do motor nao leva `--tasks` nem `--modelos`",
           bool(prep_cod) and u"--tasks" not in prep_cod
           and u"--modelos" not in prep_cod)
    checar(u"  e diz no log que o pacote e' o COMPLETO",
           u"Pacote COMPLETO" in prep_cod)
    sobras = [n for n in (u"AjustarPluginsAoModo", u"RotPlugModo3",
                          u"GBdaEscolha", u"EscolhaDeTasks",
                          u"EscolhaDeModelos", u"AtualizarContaPlugins",
                          u"CaixasTask", u"BtPlugTudo", u"BtPlugMin",
                          u"abaPlug")
              if n in codigo]
    checar(u"nada do que so' servia a escolha sobrou no codigo", not sobras,
           u", ".join(sobras))
    checar(u"a pasta do programa sai do `entrega.txt`, e nao cravada",
           u"$script:PROJETO_RT = ProjetoDaEntrega" in ps1
           and u"Copie a pasta $($script:PROJETO_RT)" in ps1,
           u"o projeto virou LOCAL_SUITE em 05/09 e o texto ficou no nome "
           u"velho por 17 dias")
    checar(u"e o lancador citado e o PRIMEIRO da lista unica",
           u"$($script:LANCADORES[0])" in ps1
           and u"foreach ($n in $script:LANCADORES)" in ps1,
           u"duas listas divergem, e a que fica para tras e a da prosa")
    _m = re.search(r"\$script:LANCADORES = @\(\s*'([^']+)'", ps1)
    _lanc = _m.group(1) if _m else u""
    checar(u"  e esse lancador EXISTE em app/",
           bool(_lanc) and os.path.isfile(_componentes.fonte("app/" + _lanc)),
           u"o texto manda clicar em %r, que nao esta no projeto"
           % (_lanc or u"(nao achei a lista)"))
    checar(u"o `v1.1` saiu do canto do cabecalho",
           u"NovoRotulo ('v' + $script:VERSAO)" not in ps1,
           u"era a versao do PREPARADOR, lida como a do pacote")
    checar(u"  e ela continua no relatorio, que e onde serve",
           u"'Preparador versao : '" in ps1)


def teste_barra_nao_enche_a_janela_de_diagnostico():
    secao(u"a barra de progresso nao entra na janela de diagnostico")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import configurar_ambiente as C

    tmp = tempfile.mkdtemp(prefix="radai_barra_")
    try:
        falso = os.path.join(tmp, "isca.py")
        with io.open(falso, "w", encoding="utf-8") as fh:
            fh.write(u"import sys\n")
            fh.write(u"pc = chr(37) + chr(124)\n")
            fh.write(u"print('Downloading:   0' + pc + '          | 1.0k/230M')\n")
            fh.write(u"print('Downloading:  50' + pc + '#####     | 115M/230M')\n")
            fh.write(u"print('Downloading: 100' + pc + '##########| 230M/230M')\n")
            fh.write(u"print('ERROR: o pacote nao publica roda cp310-win_amd64')\n")
            fh.write(u"sys.exit(1)\n")

        alvo = io.StringIO()
        log_velho, out_velho = C.LOG, sys.stdout
        C.LOG = alvo
        sys.stdout = io.StringIO()
        try:
            try:
                C.rodar([sys.executable, falso], u"isca da barra")
                levantou = False
            except RuntimeError:
                levantou = True
            except Exception:
                levantou = None
        finally:
            C.LOG, sys.stdout = log_velho, out_velho

        texto = alvo.getvalue()
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        barras = [l for l in linhas if u"%|" in l]

        checar(u"o comando que falha levanta RuntimeError", levantou is True,
               u"levantou=%r" % (levantou,))
        checar(u"no ARQUIVO sobra UMA linha de barra, e nao tres",
               len(barras) == 1,
               u"achei %d -- a corrida inteira foi gravada" % len(barras))
        checar(u"  e a que sobra e a ULTIMA, que diz o total baixado",
               bool(barras) and u"100" in barras[0],
               (barras[:1] or [u"(nenhuma)"])[0])

        pos = texto.find(u"ultimas linhas:")
        janela = texto[pos:] if pos >= 0 else u""
        checar(u"a janela de diagnostico foi impressa", bool(janela))
        checar(u"  e ela NAO tem barra de progresso dentro",
               bool(janela) and u"%|" not in janela,
               u"a barra empurrou o erro para fora da janela")
        checar(u"  e ela tem o erro DE VERDADE",
               u"roda cp310-win_amd64" in janela,
               u"o erro nao sobreviveu a corrida de barras")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_o_recorte_no_corpo_vai_no_pacote():
    secao(u"o recorte no corpo (Dataset300) vai no pacote, ou nao se empacota")
    import ast as _ast
    import configurar_ambiente as C
    import radai_tasks as K

    checar(u"`conferir_recorte_no_corpo` existe",
           hasattr(C, "conferir_recorte_no_corpo"))
    if not hasattr(C, "conferir_recorte_no_corpo"):
        return
    v_log = C.log
    d = tempfile.mkdtemp(prefix="radai_prep_body_")

    def _roda():
        try:
            C.conferir_recorte_no_corpo(d)
            return u""
        except RuntimeError as e:
            return u"%s" % e
    try:
        C.log = lambda *a, **k: None
        e1 = _roda()
        checar(u"sem a pasta do Dataset%d: PARA" % K.DATASET_BODY, bool(e1))
        checar(u"  e a mensagem diz o que falta e por que nao empacotar",
               u"--body_seg" in e1 and (u"Dataset%d" % K.DATASET_BODY) in e1
               and u"Nao empacote" in e1, e1[:160])
        pasta = os.path.join(d, K.DATASET_DO_BODY_PASTA)
        os.makedirs(pasta)
        checar(u"pasta do Dataset%d SEM o checkpoint: PARA" % K.DATASET_BODY,
               bool(_roda()), u"download interrompido passaria por completo")
        ck = os.path.join(pasta, K.PESO_DO_BODY)
        os.makedirs(os.path.dirname(ck))
        io.open(ck, "wb").write(b"peso de mentira")
        e3 = _roda()
        checar(u"com o checkpoint: segue", not e3, e3[:120])
    finally:
        C.log = v_log
        shutil.rmtree(d, ignore_errors=True)

    arv = _ast.parse(ler("build/configurar_ambiente.py"))
    chamam = set()
    for no in _ast.walk(arv):
        if isinstance(no, _ast.FunctionDef):
            for dentro in _ast.walk(no):
                if (isinstance(dentro, _ast.Call)
                        and getattr(dentro.func, "id", "") == "conferir_recorte_no_corpo"):
                    chamam.add(no.name)
    checar(u"a etapa 4 confere (`etapa_pesos`)", u"etapa_pesos" in chamam,
           sorted(chamam))
    checar(u"a etapa 6 confere (`etapa_validar`)",
           u"etapa_validar" in chamam, sorted(chamam))
    checar(u"a etapa 7 confere (`etapa_empacotar`), que e' a porta do .zip",
           u"etapa_empacotar" in chamam,
           u"`--etapas 7` montaria o pacote sem o recorte: %s" % sorted(chamam))
    emp = [n for n in _ast.walk(arv) if isinstance(n, _ast.FunctionDef)
           and n.name == u"etapa_empacotar"]
    lin_conf, lin_zip = [], []
    for dentro in (_ast.walk(emp[0]) if emp else ()):
        if isinstance(dentro, _ast.Call):
            f = dentro.func
            if getattr(f, "id", "") == "conferir_recorte_no_corpo":
                lin_conf.append(dentro.lineno)
            elif getattr(f, "attr", "") == "ZipFile":
                lin_zip.append(dentro.lineno)
    checar(u"  e antes de abrir o .zip para gravar",
           bool(lin_conf) and bool(lin_zip) and min(lin_conf) < min(lin_zip),
           u"conferencia %s, ZipFile %s" % (lin_conf, lin_zip))
    checar(u"e a conta do pacote baixa o Dataset%d" % K.DATASET_BODY,
           K.DATASET_BODY in K.datasets_do_pacote(list(C.TASKS)),
           u"a conferencia pararia todo preparo: ninguem o baixaria")

    from pathlib import Path as _Pa
    of = tempfile.mkdtemp(prefix="radai_prep_body_emp_")
    b = os.path.join(of, "AUTO_CONTORNO")
    sa = os.path.join(of, "saida")
    ck = os.path.join(b, "ts_weights", K.DATASET_DO_BODY_PASTA, K.PESO_DO_BODY)

    def _ctx():
        return {"raiz": C.RAIZ, "destino": _Pa(of), "bundle": _Pa(b),
                "cache": _Pa(os.path.join(of, "cache")), "saida": _Pa(sa),
                "projeto": "AUTO_CONTORNO", "versao": "9.9", "cuda": "cu121",
                "so_cpu": False}

    def _empacota(ctx):
        try:
            C.etapa_empacotar(ctx)
            return u""
        except (RuntimeError, SystemExit) as e:
            return u"%s: %s" % (type(e).__name__, e)
    try:
        C.log = lambda *a, **k: None
        for rel in (os.path.join("ts_weights", "total", "algum_peso.bin"), ck):
            p = os.path.join(b, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "wb").write(b"peso de mentira")
        c1 = _ctx()
        e_com = _empacota(c1)
        pac = c1.get("pacote")
        checar(u"com o checkpoint, a etapa 7 empacota o fantoma",
               not e_com and pac is not None and os.path.isfile(str(pac)),
               e_com[:160] or str(pac))
        shutil.rmtree(os.path.join(b, "ts_weights", K.DATASET_DO_BODY_PASTA))
        e_sem = _empacota(_ctx())
        checar(u"sem o checkpoint, a etapa 7 PARA, e diz por que",
               u"RuntimeError" in e_sem and u"--body_seg" in e_sem,
               e_sem[:160] or u"empacotou sem o recorte")
        _zips = sorted(n for n in os.listdir(sa) if n.lower().endswith(".zip")) \
            if os.path.isdir(sa) else []
        checar(u"  e nao sobra .zip na pasta de saida (nem o da volta anterior)",
               not _zips, str(_zips))
    finally:
        C.log = v_log
        shutil.rmtree(of, ignore_errors=True)


def teste_o_caminho_do_pacote_nao_vai_para_o_log():
    secao(u"o log leva o nome do pacote, e nao o caminho de quem preparou")
    _nomes = [u"SemUsuario", u"NomeDoArquivo", u"Registrar", u"Sessao",
              u"AnotarPastaDoOperador", u"SemPastaDoOperador"]
    fs = _funcoes_ps(u"packager/prepare.ps1", _nomes)
    faltam = [n for n in _nomes if n not in fs]
    checar(u"achei as seis funcoes no prepare.ps1", not faltam,
           u"%s%s" % (faltam, _motivo_ast(fs)))
    if not faltam:
        d = tempfile.mkdtemp(prefix="radai_prep_nome_")
        try:
            arq = os.path.join(d, "preparar_log.txt")
            h = (u"$ErrorActionPreference = 'Stop'\n"
                 u"Set-StrictMode -Version Latest\n"
                 u"$script:LogSessao = $null\n"
                 u"$script:CaixaLog = $null\n"
                 u"$script:PastasDoOperador = @()\n"
                 u"$script:ArquivoLog = '%s'\n" % arq
                 + fs[u"SemUsuario"] + u"\n" + fs[u"Sessao"] + u"\n"
                 + fs[u"AnotarPastaDoOperador"] + u"\n"
                 + fs[u"SemPastaDoOperador"] + u"\n"
                 + fs[u"Registrar"] + u"\n" + fs[u"NomeDoArquivo"] + u"\n"
                 u"'SEM:' + (SemUsuario 'C:\\Users\\usuario fantoma\\Desktop\\trab\\x.zip')\n"
                 u"'SEMD:' + (SemUsuario 'D:\\trabalho\\x.zip')\n"
                 u"'SEMC:' + (SemUsuario 'c:\\users\\Usuario Fantoma\\AppData\\Local\\Temp\\a')\n"
                 u"'SEMR:' + (SemUsuario \"[WinError 3] nao achei: "
                 u"'C:\\\\Users\\\\usuario fantoma\\\\x'\")\n"
                 u"'NOME:' + (NomeDoArquivo 'C:\\Users\\usuario fantoma\\trab\\LOCAL_SUITE_v8.1\\"
                 u"RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v8.1.zip')\n"
                 u"'VAZIO:[' + (NomeDoArquivo '') + ']'\n"
                 u"Registrar 'extraindo o pacote em C:\\Users\\usuario fantoma\\AppData\\Local\\Temp\\radai'\n"
                 u"'FIM:ok'\n")
            out, rc = _rodar_harness(h)
            m = _marcas(out)
            checar(u"o harness rodou", m.get(u"FIM") == u"ok",
                   (out or u"")[-200:])
            checar(u"`SemUsuario` troca o perfil por <usuario>",
                   m.get(u"SEM") == u"C:\\Users\\<usuario>\\Desktop\\trab\\x.zip",
                   m.get(u"SEM"))
            checar(u"  sem mexer no que nao e' perfil",
                   m.get(u"SEMD") == u"D:\\trabalho\\x.zip", m.get(u"SEMD"))
            checar(u"  e sem depender de maiuscula",
                   u"Fantoma" not in (m.get(u"SEMC") or u"")
                   and u"<usuario>" in (m.get(u"SEMC") or u""), m.get(u"SEMC"))
            checar(u"  nem da contrabarra dobrada (o repr de um OSError)",
                   m.get(u"SEMR") == (u"[WinError 3] nao achei: "
                                      u"'C:\\\\Users\\\\<usuario>\\\\x'"),
                   m.get(u"SEMR"))
            checar(u"`NomeDoArquivo` devolve so' o nome",
                   m.get(u"NOME") == u"RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v8.1.zip",
                   m.get(u"NOME"))
            checar(u"  e vazio para caminho vazio (nao levanta)",
                   m.get(u"VAZIO") == u"[]", m.get(u"VAZIO"))
            txt = (io.open(arq, encoding="utf-8-sig").read()
                   if os.path.isfile(arq) else u"")
            checar(u"o `Registrar` de verdade gravou o log", u"extraindo" in txt,
                   txt[:120])
            checar(u"  e o arquivo de log nao leva o nome de quem preparou",
                   u"fantoma" not in txt.lower(), txt[:160])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    ps = ler("packager/prepare.ps1")
    _cru = re.compile(r"\+\s*\$(?:script:PacoteFinal|script:ArquivoLog|zip|Zip)\b")
    crus = [l for l in ps.splitlines()
            if u"Registrar" in l and _cru.search(l)]
    checar(u"nenhum `Registrar` concatena o caminho do pacote", not crus,
           u" | ".join(l.strip()[:80] for l in crus[:3]))
    checar(u"  e a busca sabe reprovar (isca: a linha velha)",
           bool(_cru.search(u"Registrar ('pacote: ' + $script:PacoteFinal) 'ok'")))
    checar(u"o log nao escreve o nome do usuario por extenso",
           u"$env:USERNAME" not in u"\n".join(
               l for l in ps.splitlines() if u"Registrar" in l))
    checar(u"a falha do motor diz o log pelo nome",
           u"'O log completo esta em:' + [char]10 + $script:ArquivoLog" not in ps)
    i = ps.find(u"function AtualizarConclusao")
    corpo = ps[i:ps.find(u"\n}", i)] if i > 0 else u""
    blocos = re.findall(r'@"\r?\n(.*?)\r?\n"@', corpo, re.S)
    checar(u"achei os textos da aba 4", len(blocos) >= 4, u"%d" % len(blocos))
    ruins = [b[:40] for b in blocos
             if re.search(r"(?<!NomeDoArquivo )\$Zip\b|\$pastaZip|\$Pasta\b"
                          r"|\$\(\$script:ArquivoLog\)", b)]
    checar(u"nenhum texto da aba 4 escreve o caminho do pacote ou do log",
           not ruins, ruins)
    checar(u"  e a busca sabe reprovar (isca: o texto velho)",
           bool(re.search(r"(?<!NomeDoArquivo )\$Zip\b",
                          u"  O pacote continua aqui:\n\n      $Zip\n")))

    import configurar_ambiente as C
    base = tempfile.mkdtemp(prefix="radai_prep_log_")
    try:
        z = os.path.join(base, u"LOCAL_SUITE_v8.1",
                         u"RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v8.1.zip")
        r1 = C.para_o_log(z, {"preparo": base})
        checar(u"no --preparo, o .zip sai relativo a pasta de trabalho",
               base not in r1 and u"LOCAL_SUITE_v8.1" in r1
               and r1.endswith(u"BUNDLE_v8.1.zip"), r1)
        r2 = C.para_o_log(os.path.join(os.path.dirname(base), u"outro.zip"),
                          {"preparo": base})
        checar(u"  e o que esta FORA dela sai so' pelo nome", r2 == u"outro.zip", r2)
        checar(u"  e na oficina do projeto (sem --preparo) sai inteiro",
               C.para_o_log(z, {}) == z)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    mot = ler("build/configurar_ambiente.py")
    checar(u"o PRONTO do motor passa por `para_o_log`",
           u'log("  %s" % pacote)' not in mot
           and u'log("  %s" % para_o_log(pacote, ctx))' in mot)


def teste_a_pasta_escolhida_nao_vai_para_o_log():
    secao(u"a pasta escolhida vai para o log pelo rotulo, e nao pelo nome")
    nomes = [u"SemUsuario", u"EPastaSugerida", u"AnotarPastaDoOperador",
             u"AnotarPastaDaInstalacao", u"SemPastaDoOperador",
             u"DescreverUnidade", u"Sessao", u"Registrar"]
    fs = _funcoes_ps(u"packager/prepare.ps1", nomes)
    faltam = [n for n in nomes if n not in fs]
    checar(u"achei as oito funcoes no prepare.ps1", not faltam,
           u"%s%s" % (faltam, _motivo_ast(fs)))
    if faltam:
        return

    def rodar(troca=None):
        f = dict(fs)
        f.update(troca or {})
        d = tempfile.mkdtemp(prefix="radai_prep_pasta_")
        try:
            arq = os.path.join(d, "preparar_log.txt")
            ses = os.path.join(d, "sessao.txt")
            h = (u"$ErrorActionPreference = 'Stop'\n"
                 u"Set-StrictMode -Version Latest\n"
                 u"$script:CaixaLog = $null\n"
                 u"$script:RAIZ_RT = 'C:\\RADIOTERAPIA_AI'\n"
                 u"$script:DESTINO_PADRAO = 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE'\n"
                 u"$script:PROJETO_RT = 'LOCAL_SUITE'\n"
                 u"$script:PASTA_RT = 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE'\n"
                 u"$script:PREPARO_SUGERIDO = "
                 u"'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\preparo'\n"
                 u"$script:PastasDoOperador = @()\n"
                 u"$script:ArquivoLog = '%s'\n" % arq
                 + u"$script:LogSessao = New-Object System.IO.StreamWriter("
                   u"'%s', $false, (New-Object System.Text.UTF8Encoding($false)))\n"
                   % ses
                 + u"$script:LogSessao.AutoFlush = $true\n"
                 + u"\n".join(f[n] for n in (
                     u"SemUsuario", u"EPastaSugerida", u"AnotarPastaDoOperador",
                     u"AnotarPastaDaInstalacao", u"SemPastaDoOperador",
                     u"DescreverUnidade", u"Sessao", u"Registrar")) + u"\n"
                 u"AnotarPastaDoOperador 'D:\\Suporte\\Hospital_X_Maria' '<pasta de trabalho>'\n"
                 u"AnotarPastaDoOperador 'C:\\Users\\usuario fantoma\\Downloads\\pacotes_Maria' '<pasta do .zip>'\n"
                 u"AnotarPastaDoOperador '\\\\srv\\clinica\\Setor_Maria' '<pasta de destino>'\n"
                 u"AnotarPastaDoOperador 'E:\\' '<RAIZ>'\n"
                 u"AnotarPastaDoOperador 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE' '<SUGERIDA>'\n"
                 u"AnotarPastaDoOperador 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\preparo' '<NOSSA>'\n"
                 u"AnotarPastaDoOperador 'C:\\RADIOTERAPIA_AI' '<RAIZ_RT>'\n"
                 u"AnotarPastaDoOperador 'D:\\RADIOTERAPIA_AI\\' '<RAIZ_D>'\n"
                 u"AnotarPastaDoOperador 'C:\\Users\\usuario fantoma' '<PERFIL>'\n"
                 u"'J:' + (SemPastaDoOperador 'C:\\Users\\usuario fantoma\\AppData\\Local\\Temp\\radai_x')\n"
                 u"AnotarPastaDoOperador 'd:\\suporte\\hospital_x_maria\\' '<OUTRO>'\n"
                 u"AnotarPastaDoOperador 'C:\\RADIOTERAPIA_AI\\Maria_suporte' '<pasta de trabalho>'\n"
                 u"AnotarPastaDoOperador 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\Maria_sub' '<pasta de destino>'\n"
                 u"'N:' + $script:PastasDoOperador.Count\n"
                 u"'A:' + (SemPastaDoOperador 'extraindo o pacote em D:\\Suporte\\Hospital_X_Maria\\_radai_extracao ...')\n"
                 u"'B:' + (SemPastaDoOperador \"[WinError 3] nao achei: 'D:\\\\Suporte\\\\Hospital_X_Maria\\\\x'\")\n"
                 u"'C:' + (SemPastaDoOperador 'd:/suporte/HOSPITAL_X_MARIA/LOCAL_SUITE_v8.1')\n"
                 u"'D:' + (SemPastaDoOperador 'D:\\Suporte\\Hospital_X_Maria2\\a')\n"
                 u"'E:' + (SemPastaDoOperador 'Source : \\\\srv\\clinica\\Setor_Maria\\LOCAL_SUITE\\')\n"
                 u"'F:' + (SemPastaDoOperador 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\preparo\\x E:\\y')\n"
                 u"'G:' + (DescreverUnidade $env:SystemRoot)\n"
                 u"'H:' + (DescreverUnidade '\\\\srv\\clinica\\x')\n"
                 u"'I:' + (DescreverUnidade '')\n"
                 u"'K:' + (SemPastaDoOperador 'C:\\RADIOTERAPIA_AI\\Maria_suporte\\LOCAL_SUITE_v8.1\\x.zip')\n"
                 u"'KS:' + (SemPastaDoOperador 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\Maria_sub\\LOCAL_SUITE')\n"
                 u"'L:' + (SemPastaDoOperador 'a pasta D:\\Suporte\\Hospital_X_Maria. E em D:\\Suporte\\Hospital_X_Maria...')\n"
                 u"'M:' + (SemPastaDoOperador 'D:\\Suporte\\Hospital_X_Maria.bak\\a D:\\Suporte\\Hospital_X_Maria-2\\b')\n"
                 u"Registrar 'pasta de trabalho: D:\\Suporte\\Hospital_X_Maria'\n"
                 u"Registrar '  extraindo o pacote em C:\\Users\\usuario fantoma\\Downloads\\pacotes_Maria\\_radai_extracao ...'\n"
                 u"Registrar '    Destino : \\\\srv\\clinica\\Setor_Maria\\LOCAL_SUITE\\'\n"
                 u"Sessao 'direto na sessao: D:\\Suporte\\Hospital_X_Maria\\preparar_log.txt'\n"
                 u"'O:' + (SemPastaDoOperador 'E:\\Clinica_Joana\\LOCAL_SUITE')\n"
                 u"$script:Instalado = @{ pasta = 'E:\\Clinica_Joana\\LOCAL_SUITE'; versao = '8.1' }\n"
                 u"'P:' + (SemPastaDoOperador 'instalacao detectada: E:\\Clinica_Joana\\LOCAL_SUITE (unidade E:, disco local)')\n"
                 u"Registrar ('  pasta: ' + $script:Instalado.pasta)\n"
                 u"Sessao ('instalacao detectada: ' + $script:Instalado.pasta)\n"
                 u"Registrar '    E:\\Clinica_Joana\\LOCAL_SUITE\\radai_watcher.py'\n"
                 u"$script:Instalado = @{ pasta = 'F:\\RADIOTERAPIA_AI\\Joana_livre'; versao = '8.1' }\n"
                 u"'Q:' + (SemPastaDoOperador 'pasta: F:\\RADIOTERAPIA_AI\\Joana_livre')\n"
                 u"$script:Instalado = @{ pasta = 'H:\\Setor_Ana\\AUTO_CONTORNO'; versao = '7.0' }\n"
                 u"'T:' + (SemPastaDoOperador 'pasta: H:\\Setor_Ana\\AUTO_CONTORNO')\n"
                 u"$script:Instalado = @{ pasta = 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE'; versao = '8.1' }\n"
                 u"'R:' + (SemPastaDoOperador 'pasta: C:\\RADIOTERAPIA_AI\\LOCAL_SUITE')\n"
                 u"$script:Instalado = @{ pasta = 'G:\\RADIOTERAPIA_AI\\LOCAL_SUITE'; versao = '8.1' }\n"
                 u"'S:' + (SemPastaDoOperador 'pasta: G:\\RADIOTERAPIA_AI\\LOCAL_SUITE')\n"
                 u"$script:LogSessao.Dispose()\n"
                 u"'FIM:ok'\n")
            out, rc = _rodar_harness(h)

            def ler_(p):
                return (io.open(p, encoding="utf-8-sig").read()
                        if os.path.isfile(p) else u"")
            return out, _marcas(out), ler_(arq), ler_(ses)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    out, m, log, ses = rodar()
    checar(u"o harness rodou", m.get(u"FIM") == u"ok", (out or u"")[-300:])
    checar(u"so' as cinco pastas escolhidas foram anotadas (raiz de disco, as "
           u"sugeridas, a raiz do ecossistema, o perfil e a repetida ficam de "
           u"fora)", m.get(u"N") == u"5", m.get(u"N"))
    checar(u"  e o %TEMP% dentro do perfil nao ganha rotulo de pasta escolhida",
           m.get(u"J") == u"C:\\Users\\usuario fantoma\\AppData\\Local\\Temp\\radai_x",
           m.get(u"J"))
    checar(u"a pasta de trabalho vira o rotulo, e o resto do caminho fica",
           m.get(u"A") == u"extraindo o pacote em <pasta de trabalho>\\"
                          u"_radai_extracao ...", m.get(u"A"))
    checar(u"  tambem com a contrabarra dobrada (o repr de um OSError)",
           m.get(u"B") == u"[WinError 3] nao achei: '<pasta de trabalho>\\\\x'",
           m.get(u"B"))
    checar(u"  e com barra normal e outra caixa de letra",
           m.get(u"C") == u"<pasta de trabalho>/LOCAL_SUITE_v8.1", m.get(u"C"))
    checar(u"  sem comer o comeco de OUTRA pasta de nome parecido",
           m.get(u"D") == u"D:\\Suporte\\Hospital_X_Maria2\\a", m.get(u"D"))
    checar(u"  e o caminho de rede (UNC) tambem",
           m.get(u"E") == u"Source : <pasta de destino>\\LOCAL_SUITE\\", m.get(u"E"))
    checar(u"  e o que a tela sugere, ou raiz de disco, passa como esta",
           m.get(u"F") == u"C:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\preparo\\x E:\\y",
           m.get(u"F"))
    checar(u"a pasta DIGITADA sob a raiz do ecossistema vira o rotulo (o "
           u"prefixo `C:\\RADIOTERAPIA_AI\\` nao a poupa mais)",
           m.get(u"K") == u"<pasta de trabalho>\\LOCAL_SUITE_v8.1\\x.zip",
           m.get(u"K"))
    checar(u"  e a subpasta da SUGERIDA tambem (o nome dela foi digitado)",
           m.get(u"KS") == u"<pasta de destino>\\LOCAL_SUITE", m.get(u"KS"))
    checar(u"o ponto que fecha a frase nao protege o nome da pasta",
           m.get(u"L") == u"a pasta <pasta de trabalho>. E em "
                          u"<pasta de trabalho>...", m.get(u"L"))
    checar(u"  e o ponto que CONTINUA o nome continua sendo outra pasta",
           m.get(u"M") == u"D:\\Suporte\\Hospital_X_Maria.bak\\a "
                          u"D:\\Suporte\\Hospital_X_Maria-2\\b", m.get(u"M"))
    checar(u"`DescreverUnidade` diz a unidade e se e' local",
           m.get(u"G") == u"unidade %s, disco local"
           % (os.environ.get("SystemDrive") or u"C:").upper(), m.get(u"G"))
    checar(u"  e o caminho de rede, sem o nome do servidor",
           m.get(u"H") == u"caminho de rede (UNC)", m.get(u"H"))
    checar(u"  e nao levanta com caminho vazio",
           m.get(u"I") == u"unidade desconhecida", m.get(u"I"))
    checar(u"a instalacao so' e' anotada depois de achada (a troca nao "
           u"adivinha)", m.get(u"O") == u"E:\\Clinica_Joana\\LOCAL_SUITE",
           m.get(u"O"))
    checar(u"a instalacao ACHADA sai pelo rotulo, com a folha do projeto",
           m.get(u"P") == u"instalacao detectada: <pasta da instalacao>\\"
                          u"LOCAL_SUITE (unidade E:, disco local)", m.get(u"P"))
    checar(u"  com folha de nome livre, a propria pasta vira o rotulo",
           m.get(u"Q") == u"pasta: <pasta da instalacao>", m.get(u"Q"))
    checar(u"  e a folha de antes (`AUTO_CONTORNO`) tambem e' do projeto",
           m.get(u"T") == u"pasta: <pasta da instalacao>\\AUTO_CONTORNO",
           m.get(u"T"))
    checar(u"  e a instalacao na pasta sugerida passa como esta",
           m.get(u"R") == u"pasta: C:\\RADIOTERAPIA_AI\\LOCAL_SUITE", m.get(u"R"))
    checar(u"  e na raiz do ecossistema de outro disco tambem",
           m.get(u"S") == u"pasta: G:\\RADIOTERAPIA_AI\\LOCAL_SUITE", m.get(u"S"))
    checar(u"o `Registrar` de verdade gravou o log",
           u"pasta de trabalho:" in log and u"extraindo" in log, log[:160])
    _nomes_escolhidos = (u"maria", u"fantoma", u"joana")
    checar(u"  e o log nao leva o nome de nenhuma das pastas escolhidas, nem "
           u"o da instalacao achada",
           not any(n in log.lower() for n in _nomes_escolhidos), log[:300])
    checar(u"  e leva o rotulo, com o que vem depois dele (a PASTA antes do "
           u"perfil: com o perfil trocado antes, ela nao casaria)",
           u"<pasta do .zip>\\_radai_extracao" in log
           and u"<pasta de destino>\\LOCAL_SUITE" in log
           and u"pasta: <pasta da instalacao>\\LOCAL_SUITE" in log
           and u"<pasta da instalacao>\\LOCAL_SUITE\\radai_watcher.py" in log,
           log[:400])
    checar(u"a `Sessao` tambem troca (e' o log que sobrevive a janela)",
           u"direto na sessao: <pasta de trabalho>\\preparar_log.txt" in ses
           and u"instalacao detectada: <pasta da instalacao>\\LOCAL_SUITE" in ses
           and not any(n in ses.lower() for n in _nomes_escolhidos), ses[:300])

    reg = fs[u"Registrar"]
    isca = re.sub(r"SemPastaDoOperador\s+", u"", reg)
    isca = isca.replace(u"(SemPastaDoOperador $Texto)", u"$Texto")
    checar(u"  (a isca cabe no `Registrar`)", isca != reg, reg[:200])
    _o, _m, log2, _s = rodar({u"Registrar": isca})
    checar(u"  (isca: sem a troca, o nome da pasta volta ao log -- a checagem "
           u"acima o reprova)", u"Hospital_X_Maria" in log2, log2[:200])
    ordem = reg.replace(u"SemUsuario (SemPastaDoOperador $Texto)",
                        u"SemPastaDoOperador (SemUsuario $Texto)")
    checar(u"  (a isca da ordem cabe no `Registrar`)", ordem != reg, reg[:200])
    _o, _m, log3, _s = rodar({u"Registrar": ordem})
    checar(u"  (isca: com o perfil trocado ANTES, a pasta do .zip nao casa -- "
           u"a checagem do rotulo acima o reprova)",
           u"<pasta do .zip>\\_radai_extracao" not in log3
           and u"pacotes_Maria" in log3, log3[:300])
    prefixo = (u"function EPastaSugerida {\n"
               u"    param([string]$Caminho)\n"
               u"    $c = ([string]$Caminho).Trim().TrimEnd('\\', '/')\n"
               u"    foreach ($n in @($script:RAIZ_RT, $script:DESTINO_PADRAO)) {\n"
               u"        if ($c -ieq $n -or $c.StartsWith($n + '\\',"
               u" [System.StringComparison]::OrdinalIgnoreCase)) { return $true }\n"
               u"    }\n"
               u"    return $false\n"
               u"}")
    _o, m4, _l, _s = rodar({u"EPastaSugerida": prefixo})
    checar(u"  (isca: com o prefixo antigo, a pasta digitada sob "
           u"`C:\\RADIOTERAPIA_AI\\` passa inteira -- a checagem acima o reprova)",
           m4.get(u"FIM") == u"ok" and u"Maria_suporte" in (m4.get(u"K") or u""),
           m4.get(u"K"))
    anot = fs[u"AnotarPastaDoOperador"]
    velho = anot.replace(u"(?![\\w\\-]|\\.[\\w\\-])", u"(?![\\w.\\-])")
    checar(u"  (a isca do fim de nome cabe na `AnotarPastaDoOperador`)",
           velho != anot, anot[-300:])
    _o, m5, _l, _s = rodar({u"AnotarPastaDoOperador": velho})
    checar(u"  (isca: com o fim de nome antigo, «...Hospital_X_Maria.» passa "
           u"inteiro -- a checagem acima o reprova)",
           m5.get(u"FIM") == u"ok"
           and u"Hospital_X_Maria." in (m5.get(u"L") or u""), m5.get(u"L"))
    sem = fs[u"SemPastaDoOperador"]
    semi = re.sub(r"[^\n]*try \{ AnotarPastaDaInstalacao \$pInst \}[^\n]*\n?",
                  u"", sem)
    checar(u"  (a isca da instalacao cabe na `SemPastaDoOperador`)",
           semi != sem, sem[:300])
    _o, m6, log6, _s = rodar({u"SemPastaDoOperador": semi})
    checar(u"  (isca: sem a anotacao, a instalacao achada volta ao log por "
           u"extenso -- as checagens acima o reprovam)",
           m6.get(u"FIM") == u"ok" and u"Clinica_Joana" in (m6.get(u"P") or u"")
           and u"joana" in log6.lower(), m6.get(u"P"))

    ps = ler("packager/prepare.ps1")

    def lidas(texto):
        n = set(re.findall(r"Get-Variable\s+-Name\s+(\w+)", texto))
        for lista in re.findall(r"foreach \(\$nome in @\(([^)]*)\)\)", texto):
            n |= set(re.findall(r"'(\w+)'", lista))
        return n

    def sem_atribuicao(nomes_):
        return sorted(x for x in nomes_
                      if not re.search(r"^\$script:%s\s*=" % re.escape(x), ps, re.M))
    lid = lidas(fs[u"EPastaSugerida"] + fs[u"AnotarPastaDaInstalacao"]
                + fs[u"SemPastaDoOperador"])
    checar(u"as variaveis lidas por `Get-Variable` sao atribuidas no topo do "
           u"prepare.ps1 (%d: %s)" % (len(lid), u", ".join(sorted(lid))),
           len(lid) >= 7 and not sem_atribuicao(lid), sem_atribuicao(lid))
    checar(u"  (isca: um nome que ninguem atribui e' acusado)",
           sem_atribuicao(lid | {u"PREPARO_QUE_SAIU"}) == [u"PREPARO_QUE_SAIU"])

    cod = u"\n".join(l for l in ps.splitlines()
                     if not l.lstrip().startswith(u"#"))
    i = cod.find(u"function Preparar {")
    corpo = cod[i:cod.find(u"\nfunction ", i + 10)] if i >= 0 else u""
    a = corpo.find(u"AnotarPastaDoOperador $trab")
    g = corpo.find(u"DestinoSincroniza $trab")
    r = corpo.find(u"Registrar ('pasta de trabalho:")
    checar(u"`Preparar` anota a pasta de trabalho ANTES da guarda da nuvem e "
           u"da primeira linha do log", 0 <= a < g and a < r,
           u"anota=%d guarda=%d linha=%d" % (a, g, r))
    checar(u"  e a linha «pasta de trabalho:» nao concatena o caminho",
           not re.search(r"Registrar \('pasta de trabalho: ' \+ \$trab\)", corpo)
           and u"DescreverUnidade $trab" in corpo, corpo[r:r + 120] if r >= 0 else u"")
    checar(u"  e a busca sabe reprovar (isca: a linha velha)",
           bool(re.search(r"Registrar \('pasta de trabalho: ' \+ \$trab\)",
                          u"        Registrar ('pasta de trabalho: ' + $trab)")))
    i = cod.find(u"function InstalarDeArquivo {")
    corpo = cod[i:cod.find(u"\nfunction ", i + 10)] if i >= 0 else u""
    z = corpo.find(u"AnotarPastaDoOperador (Split-Path -Parent $zip)")
    n = corpo.find(u"InstalarAqui $zip")
    checar(u"o modo 3 anota a pasta do .zip antes de extrair", 0 <= z < n,
           u"anota=%d instala=%d" % (z, n))
    s1 = ps.find(u"\nSessao (")
    for fn in (u"EPastaSugerida", u"AnotarPastaDoOperador",
               u"AnotarPastaDaInstalacao", u"SemPastaDoOperador"):
        f1 = ps.find(u"function %s" % fn)
        checar(u"`%s` e' definida antes da primeira linha da sessao" % fn,
               0 <= f1 < s1, u"funcao=%d sessao=%d" % (f1, s1))


def teste_o_modo_3_nao_consulta_a_versao():
    secao(u"modo 3 nao consulta a versao; Sim e Cancelar param o preparo")
    fs = _funcoes_ps(u"packager/prepare.ps1", [u"VersaoDeixaPreparar"])
    f = fs.get(u"VersaoDeixaPreparar", u"")
    checar(u"achei `VersaoDeixaPreparar`", bool(f), _motivo_ast(fs))
    if f:
        h = (u"$ErrorActionPreference = 'Stop'\n"
             u"Set-StrictMode -Version Latest\n"
             u"$script:Modo = ''\n"
             u"$script:BtRodar = [pscustomobject]@{ Enabled = $true }\n"
             u"$global:EST = ''; $global:RESP = ''; $global:M = @{}\n"
             u"function Registrar { param($Texto, $Nivel) }\n"
             u"function ConferirMinhaVersao { $global:M.consultou = 1\n"
             u"    return @{ estado = $global:EST; frase = 'f'; url = 'https://exemplo/releases' } }\n"
             u"function PerguntarSobreVersaoNova { param($c) $global:M.perguntou = 1\n"
             u"    return $global:RESP }\n"
             u"function Start-Process { param($x) $global:M.abriu = 1 }\n"
             + f + u"\n"
             u"$casos = @(@('3','velho','Yes'), @('2','velho','Yes'),\n"
             u"           @('2','velho','Cancel'), @('2','velho','No'),\n"
             u"           @('1','atual','Yes'))\n"
             u"$i = 0\n"
             u"foreach ($c in $casos) {\n"
             u"    $script:Modo = $c[0]; $global:EST = $c[1]; $global:RESP = $c[2]\n"
             u"    $global:M = @{ consultou = 0; perguntou = 0; abriu = 0 }\n"
             u"    $r = VersaoDeixaPreparar\n"
             u"    [Console]::Out.WriteLine('C' + $i + ':' + $global:M.consultou + ',' +\n"
             u"        $global:M.perguntou + ',' + $global:M.abriu + ',' + ($r -join '|') +\n"
             u"        ',' + $script:BtRodar.Enabled)\n"
             u"    $i++\n"
             u"}\n"
             u"'FIM:ok'\n")
        out, rc = _rodar_harness(h)
        m = _marcas(out)
        checar(u"o harness rodou", m.get(u"FIM") == u"ok", (out or u"")[-240:])
        esperado = {
            u"C0": (u"modo 3: NAO consulta a internet, e segue", u"0,0,0,True,True"),
            u"C1": (u"«Sim» (abrir a pagina): abre e NAO prepara", u"1,1,1,False,True"),
            u"C2": (u"«Cancelar»: NAO prepara", u"1,1,0,False,True"),
            u"C3": (u"«Nao» (seguir com a antiga): prepara", u"1,1,0,True,True"),
            u"C4": (u"em dia: nao pergunta, e prepara", u"1,0,0,True,True"),
        }
        for k in sorted(esperado):
            rot, val = esperado[k]
            checar(rot, m.get(k) == val, u"veio %s" % m.get(k))

    ps = ler("packager/prepare.ps1")
    checar(u"um so' handler no botao de preparar",
           ps.count(u"$btRodar.Add_Click(") == 1,
           u"%d" % ps.count(u"$btRodar.Add_Click("))
    i = ps.find(u"$btRodar.Add_Click(")
    h = ps[i:ps.find(u"\n})", i)] if i > 0 else u""
    cod = u"\n".join(l for l in h.splitlines() if not l.lstrip().startswith(u"#"))
    _prep = re.search(r"^\s*Preparar\s*$", cod, re.M)
    pos = [cod.find(x) for x in (u"if ($script:Ocupado) { return }",
                                 u"InstalarDeArquivo",
                                 u"VersaoDeixaPreparar")] + [
        _prep.start() if _prep else -1]
    checar(u"  e a ordem e' Ocupado -> modo 3 -> versao -> Preparar",
           all(p > 0 for p in pos) and pos == sorted(pos), pos)
    fora = [l for l in ps.splitlines()
            if u"ConferirMinhaVersao" in l and not l.lstrip().startswith(u"#")
            and u"function ConferirMinhaVersao" not in l]
    checar(u"a consulta so' e' chamada pela decisao e pelo autoteste",
           len(fora) == 2, u" | ".join(l.strip()[:60] for l in fora))


def teste_raiz_de_disco_chega_ao_motor():
    secao(u"a pasta de trabalho na raiz de um disco chega inteira ao motor")
    fs = _funcoes_ps(u"packager/prepare.ps1", [u"LinhaDeArgumentos"])
    f = fs.get(u"LinhaDeArgumentos", u"")
    checar(u"achei `LinhaDeArgumentos`", bool(f), _motivo_ast(fs))
    if not f:
        return
    d = tempfile.mkdtemp(prefix="radai_prep_args_")
    try:
        eco = os.path.join(d, "eco.py")
        io.open(eco, "w", encoding="utf-8").write(
            u"import sys, json\nprint('ARGV:' + json.dumps(sys.argv[1:]))\n")
        casos = [u"D:\\", u"C:\\Pasta com espaco\\trab", u"E:\\trab\\"]
        h = (u"$ErrorActionPreference = 'Stop'\n"
             u"Set-StrictMode -Version Latest\n" + f + u"\n")
        for i, c in enumerate(casos):
            h += (u"$pi = New-Object System.Diagnostics.ProcessStartInfo\n"
                  u"$pi.FileName = '%s'\n"
                  u"$pi.Arguments = LinhaDeArgumentos @('%s', '--preparo', '%s')\n"
                  u"$pi.UseShellExecute = $false\n"
                  u"$pi.RedirectStandardOutput = $true\n"
                  u"$p = [System.Diagnostics.Process]::Start($pi)\n"
                  u"$o = $p.StandardOutput.ReadToEnd(); $p.WaitForExit()\n"
                  u"[Console]::Out.WriteLine('C%d' + $o.Trim().Substring(4))\n"
                  % (sys.executable, eco, c, i))
        h += u"'FIM:ok'\n"
        out, rc = _rodar_harness(h)
        m = {}
        for l in (out or u"").splitlines():
            if l[:2] in (u"C0", u"C1", u"C2") and l[2:3] == u":":
                try:
                    m[l[:2]] = json.loads(l[3:])
                except ValueError:
                    m[l[:2]] = l[3:]
        checar(u"o harness rodou", u"FIM:ok" in (out or u""), (out or u"")[-200:])
        for i, (c, rot) in enumerate(zip(casos, (
                u"a raiz de um disco chega inteira",
                u"caminho com espaco e barras no meio chega intacto",
                u"pasta terminada em barra chega intacta"))):
            checar(rot, m.get(u"C%d" % i) == [u"--preparo", c],
                   u"%r -> %r" % (c, m.get(u"C%d" % i)))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    ps = ler("packager/prepare.ps1")
    checar(u"e o preparo monta a linha do motor por ela",
           u"$pi.Arguments = LinhaDeArgumentos $argumentos" in ps)


def teste_o_bundle_escolhido_e_o_que_acabou_de_sair():
    secao(u"o bundle escolhido e' o que o motor acabou de gravar")
    ps = ler("packager/prepare.ps1")
    i = ps.find(u"$todos = @(Get-ChildItem")
    j = ps.find(u"if ($zip) { $script:PacoteFinal", i)
    trecho = ps[i:j] if i > 0 and j > i else u""
    checar(u"achei o trecho que escolhe o bundle", bool(trecho))
    if not trecho:
        return
    d = tempfile.mkdtemp(prefix="radai_prep_bundle_")
    try:
        def _arq(rel, n, quando):
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "wb").write(b"z" * n)
            os.utime(p, (quando, quando))
        agora = 1790000000
        _arq(os.path.join(u"LOCAL_SUITE_v8.0",
                          u"RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v8.0.zip"), 3000, agora - 86400)
        _arq(os.path.join(u"LOCAL_SUITE_v8.1",
                          u"RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v8.1.zip"), 1000, agora - 60)
        _arq(os.path.join(u"cache", u"python-embed.zip"), 5000, agora)
        h = (u"$ErrorActionPreference = 'Stop'\n"
             u"Set-StrictMode -Version Latest\n"
             u"$trab = '%s'\n" % d + trecho +
             u"\n'ESCOLHIDO:' + $zip.Name\n")
        out, rc = _rodar_harness(h)
        m = _marcas(out)
        checar(u"com dois bundles, vale o mais novo (e nao o maior)",
               m.get(u"ESCOLHIDO") == u"RADIOTERAPIA_AI_LOCAL_SUITE_BUNDLE_v8.1.zip",
               u"escolheu %r" % m.get(u"ESCOLHIDO"))
        shutil.rmtree(os.path.join(d, u"LOCAL_SUITE_v8.0"))
        shutil.rmtree(os.path.join(d, u"LOCAL_SUITE_v8.1"))
        _arq(os.path.join(u"outro", u"pequeno.zip"), 10, agora + 60)
        out, rc = _rodar_harness(h)
        m = _marcas(out)
        checar(u"  e sem bundle pela forma, o recuo e' o maior .zip",
               m.get(u"ESCOLHIDO") == u"python-embed.zip",
               u"escolheu %r" % m.get(u"ESCOLHIDO"))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _entrega(raiz=None):
    d = {}
    p = os.path.join(raiz or RAIZ, "entrega.txt")
    if not os.path.isfile(p):
        return d
    for l in io.open(p, encoding="utf-8-sig").read().splitlines():
        m = re.match(r"^\s*([A-Z_]+)\s*=\s*(.+?)\s*$", l)
        if m:
            d[m.group(1)] = m.group(2)
    return d


def _como_numero(v):
    n = []
    for p in re.sub(r"^[vV]", u"", v or u"").split(u"."):
        n.append(int(p) if p.isdigit() else 0)
    return (n + [0, 0, 0, 0])[:4]


PIPELINE_UNICO_DESDE = u"8.0"


def _repositorio_de(raiz):
    try:
        top = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=raiz,
            stderr=subprocess.STDOUT, timeout=60)
    except FileNotFoundError:
        return False, u"git nao esta no PATH"
    except subprocess.CalledProcessError:
        return False, u"nao e' um repositorio git"
    except subprocess.TimeoutExpired:
        return False, u"o git esgotou 60 s"
    top = top.decode("utf-8", "replace").strip()
    if (os.path.normcase(os.path.abspath(top))
            != os.path.normcase(os.path.abspath(raiz))):
        return False, u"a arvore esta DENTRO de outro repositorio (%s)" % top
    return True, u""


def _impressao_da_tag(tag):
    import tarfile
    eh, motivo = _repositorio_de(RAIZ)
    if not eh:
        return None, motivo, True
    d = tempfile.mkdtemp(prefix="radai_prep_tag_")
    try:
        try:
            dados = subprocess.check_output(
                ["git", "archive", "--format=tar", tag, "build",
                 "app/radai_tasks.py", "app/radai_models.py"],
                cwd=RAIZ, stderr=subprocess.STDOUT, timeout=120)
        except FileNotFoundError:
            return None, u"git nao esta no PATH", True
        except subprocess.CalledProcessError as e:
            return (None, (e.output or b"").decode("utf-8", "replace").strip()[:160],
                    False)
        with tarfile.open(fileobj=io.BytesIO(dados)) as tf:
            tf.extractall(d)
        import requisitos as R
        return R.calcular(d)[u"impressao"], u"", False
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _bundle_minimo_serve(minimo, versao, imp_tag, imp_aqui, erro_tag=u"",
                         sem_repo=False, publica=False):
    if imp_tag is None:
        if minimo == versao:
            return (True, u"AVISO: a tag v%s nao existe (%s) -- com BUNDLE_MINIMO "
                          u"igual a VERSAO nao ha pacote mais antigo a conferir"
                    % (minimo, erro_tag), u"")
        if publica:
            return (True, u"PULADO a comparacao com a tag v%s: a arvore publica "
                          u"nasce sem as versoes de antes dela, e a VERSAO sobe "
                          u"na oficina, onde a tag existe" % minimo, u"")
        if sem_repo:
            return (True, u"AVISO: nao sei -- %s, e a conferencia da v%s precisa "
                          u"das tags do repositorio de desenvolvimento, onde a "
                          u"VERSAO sobe" % (erro_tag, minimo), u"")
        return (False, u"", u"a tag v%s nao existe (%s): sem ela nao ha como "
                            u"provar que o pacote dela serve. Busque as tags "
                            u"(git fetch --tags) ou suba BUNDLE_MINIMO para a "
                            u"VERSAO desta entrega (%s)"
                % (minimo, erro_tag, versao))
    if imp_tag != imp_aqui:
        return (False, u"", u"a impressao de requisitos mudou desde a v%s: suba "
                            u"BUNDLE_MINIMO para a VERSAO desta entrega (%s)"
                % (minimo, versao))
    return True, u"", u""


def teste_o_bundle_minimo_serve_a_esta_versao():
    secao(u"o BUNDLE_MINIMO do entrega.txt serve a esta versao")
    ent = _entrega()
    v, m = ent.get(u"VERSAO", u""), ent.get(u"BUNDLE_MINIMO", u"")
    checar(u"o entrega.txt declara BUNDLE_MINIMO", bool(m),
           u"sem ele a aba 0 cai no recuo (a propria VERSAO)")
    if not m:
        return
    checar(u"  so' digito e ponto, como a VERSAO",
           re.match(r"^\d+(\.\d+)*$", m) is not None, m)
    checar(u"  e nao passa da VERSAO (%s <= %s)" % (m, v),
           _como_numero(m) <= _como_numero(v), u"%s > %s" % (m, v))
    checar(u"  nem desce abaixo do pipeline unico (v%s)" % PIPELINE_UNICO_DESDE,
           _como_numero(m) >= _como_numero(PIPELINE_UNICO_DESDE),
           u"pacote de antes do pipeline unico pode nao levar todos os pesos")

    import requisitos as R
    imp_aqui = R.calcular(RAIZ)[u"impressao"]
    imp_tag, erro, sem_repo = _impressao_da_tag(u"v" + m)
    ok, aviso, motivo = _bundle_minimo_serve(
        m, v, imp_tag, imp_aqui, erro, sem_repo,
        publica=not _componentes.arvore_de_engenharia(__file__))
    if aviso:
        print(u"  %s" % aviso)
    checar(u"a impressao de requisitos da v%s e' a desta arvore" % m, ok,
           motivo)

    _, _, mi = _bundle_minimo_serve(u"8.0", u"8.1", u"aaa", u"bbb")
    checar(u"  (isca: impressoes diferentes reprovam, e dizem o que fazer)",
           mi == u"a impressao de requisitos mudou desde a v8.0: suba "
                 u"BUNDLE_MINIMO para a VERSAO desta entrega (8.1)", mi)
    ok_a, av_a, _ = _bundle_minimo_serve(u"8.1", u"8.1", None, u"x", u"sem tag")
    ok_b, _, mo_b = _bundle_minimo_serve(u"8.0", u"8.1", None, u"x", u"sem tag")
    checar(u"  (isca: sem a tag, AVISO so' com o minimo igual a VERSAO)",
           ok_a and av_a.startswith(u"AVISO") and not ok_b
           and u"nao existe" in mo_b, (ok_a, av_a[:40], ok_b, mo_b[:60]))
    ok_c, av_c, _ = _bundle_minimo_serve(u"8.0", u"8.1", None, u"x",
                                         u"nao e' um repositorio git", True)
    checar(u"  (isca: fora de um repositorio, AVISO de «nao sei», e nao reprova)",
           ok_c and av_c.startswith(u"AVISO: nao sei"), av_c[:60])
    ok_d, av_d, _ = _bundle_minimo_serve(u"8.0", u"8.1", None, u"x", u"sem tag",
                                         publica=True)
    ok_e, _, _ = _bundle_minimo_serve(u"8.0", u"8.1", u"aaa", u"bbb",
                                      publica=True)
    checar(u"  (isca: na arvore publica sem a tag antiga, PULADO e nao reprova; "
           u"com a tag, a impressao diferente reprova igual)",
           ok_d and av_d.startswith(u"PULADO") and not ok_e, (ok_d, av_d[:40], ok_e))
    fora = tempfile.mkdtemp(prefix="radai_prep_semgit_")
    try:
        eh_fora, mot_fora = _repositorio_de(fora)
        eh_aqui, mot_aqui = _repositorio_de(RAIZ)
        dentro = os.path.join(RAIZ, u"tools")
        eh_dentro, mot_dentro = _repositorio_de(dentro)
        checar(u"  e a pergunta «e' a raiz de um repositorio?» separa os tres "
               u"casos (pasta solta, dentro de outro, a raiz)",
               (not eh_fora) and (not eh_dentro)
               and ((eh_aqui and u"DENTRO de outro" in mot_dentro)
                    or not eh_aqui),
               u"%s | %s | %s" % (mot_fora, mot_dentro, mot_aqui))
    finally:
        shutil.rmtree(fora, ignore_errors=True)
    d = tempfile.mkdtemp(prefix="radai_prep_imp_")
    try:
        shutil.copytree(os.path.join(RAIZ, "build"), os.path.join(d, "build"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(d, "app"))
        shutil.copy2(_componentes.fonte("app/radai_tasks.py"),
                     os.path.join(d, "app", "radai_tasks.py"))
        shutil.copy2(_componentes.fonte("app/radai_models.py"),
                     os.path.join(d, "app", "radai_models.py"))
        req = os.path.join(d, "build", "requirements-demo.txt")
        io.open(req, "a", encoding="utf-8").write(u"\nisca-da-bateria==9.9.9\n")
        checar(u"  (isca: uma linha a mais no requirements MUDA a impressao)",
               R.calcular(d)[u"impressao"] != imp_aqui,
               u"a impressao nao viu a mudanca -- «igual» nao provaria nada")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    ps = ler("packager/prepare.ps1")
    checar(u"a aba 0 le os dois numeros do entrega.txt (nenhum a mao)",
           u"ValorDaEntrega 'VERSAO'" in ps
           and u"ValorDaEntrega 'BUNDLE_MINIMO'" in ps
           and not re.search(r"Instalador v\d", ps)
           and not re.search(r"versao \d+\.\d+ ou superior", ps))
    emp = ler("build/empacotar_instalador.py")
    checar(u"e o instalador leve leva o BUNDLE_MINIMO no entrega.txt dele",
           u"BUNDLE_MINIMO=" in emp, u"o carimbo so' tem VERSAO e DATA; sem "
           u"esta linha a aba 0 do instalador publicado cai no recuo")


def teste_o_modo_3_cumpre_a_linha_da_aba_0():
    import zipfile
    secao(u"o modo 3 cumpre a linha «aceita pacote versao X ou superior»")
    nomes = [u"VersaoDoZip", u"DecisaoDoPacote", u"MaisNovaQue", u"ComoNumero",
             u"AplicarCodigoPorCima", u"AcompanharProcesso", u"VersaoDaPasta"]
    fs = _funcoes_ps(u"packager/prepare.ps1", nomes)
    faltam = [n for n in nomes if n not in fs]
    checar(u"as sete funcoes existem e foram recortadas pelo parser",
           not faltam, u"%s%s" % (faltam, _motivo_ast(fs)))
    if faltam:
        return
    d = tempfile.mkdtemp(prefix="radai_prep_modo3_")
    try:
        def _zip(nome, entradas):
            p = os.path.join(d, nome)
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("INSTALL.ps1", u"# fantoma\n")
                for n, t in entradas:
                    z.writestr(n, t)
            return p
        ent = lambda v: (u"PRODUTO=X\nPROJETO=LOCAL_SUITE\nVERSAO=%s\n" % v)
        zips = [
            _zip("a.zip", [("entrega.txt", ent(u"8.0")),
                           ("LOCAL_SUITE/entrega.txt", ent(u"8.0"))]),
            _zip("b.zip", [("entrega.txt", ent(u"7.9"))]),
            _zip("c.zip", [("LOCAL_SUITE/radai_watcher.py", u"#\n")]),
            _zip("d.zip", [("LOCAL_SUITE/entrega.txt",
                            u"﻿" + ent(u"8.1"))]),
            _zip("e.zip", [("entrega.txt", u"PROJETO=LOCAL_SUITE\n")]),
            _zip("f.zip", [("entrega.txt", ent(u"8.2"))]),
        ]
        base = (u"$ErrorActionPreference = 'Stop'\n"
                u"Set-StrictMode -Version Latest\n"
                u"function T { param([AllowEmptyString()][string]$Texto) return $Texto }\n"
                + fs[u"ComoNumero"] + u"\n" + fs[u"MaisNovaQue"] + u"\n"
                + fs[u"VersaoDoZip"] + u"\n")
        corpo = u""
        for i, z in enumerate(zips):
            corpo += (u"$vz = VersaoDoZip '%s'\n"
                      u"$dc = DecisaoDoPacote $vz.versao '8.0' '8.1' $vz.erro\n"
                      u"'Z%d:' + $vz.versao + '|' + $dc.acao + '|' + $vz.onde + "
                      u"'|' + $dc.frase\n" % (z, i))
        corpo += (u"$dc = DecisaoDoPacote '8.10' '8.9' '8.10'\n"
                  u"'NUM:' + $dc.acao\n'FIM:ok'\n")
        out, rc = _rodar_harness(base + fs[u"DecisaoDoPacote"] + u"\n" + corpo)
        m = _marcas(out)
        checar(u"o harness rodou", m.get(u"FIM") == u"ok", (out or u"")[-240:])
        z = {k: (m.get(k) or u"").split(u"|") + [u"", u"", u""]
             for k in (u"Z0", u"Z1", u"Z2", u"Z3", u"Z4", u"Z5")}
        checar(u"pacote v8.0 (o minimo) num instalador v8.1: instala E aplica "
               u"o codigo novo por cima",
               z[u"Z0"][:3] == [u"8.0", u"instala_e_atualiza", u"entrega.txt"],
               z[u"Z0"][:3])
        checar(u"pacote v7.9, abaixo do minimo: RECUSA, com a frase que diz o "
               u"que fazer",
               z[u"Z1"][1] == u"recusa" and z[u"Z1"][3] == (
                   u'Este pacote e da versao 7.9; este instalador aceita pacote '
                   u'de transferencia da versao 8.0 ou superior. Monte um pacote '
                   u'novo com "Máquina com internet: montar um pacote para levar '
                   u'para a máquina offline".'),
               z[u"Z1"][1:4])
        checar(u"pacote sem entrega.txt: recusa com motivo proprio",
               z[u"Z2"][1] == u"recusa" and u"entrega.txt" in z[u"Z2"][3],
               z[u"Z2"][1:4])
        checar(u"carimbo so' dentro da pasta do projeto, com BOM: acha a v8.1 "
               u"e instala como hoje",
               z[u"Z3"][:3] == [u"8.1", u"instala", u"LOCAL_SUITE/entrega.txt"],
               z[u"Z3"][:3])
        checar(u"carimbo sem VERSAO: recusa, dizendo que falta a VERSAO",
               z[u"Z4"][1] == u"recusa" and u"VERSAO" in z[u"Z4"][3],
               z[u"Z4"][1:4])
        checar(u"pacote mais novo que o instalador: instala como hoje",
               z[u"Z5"][:2] == [u"8.2", u"instala"], z[u"Z5"][:2])
        checar(u"e a conta e' de numero, e nao de texto (8.10 > 8.9)",
               m.get(u"NUM") == u"instala", m.get(u"NUM"))
        _real = fs[u"DecisaoDoPacote"]
        _isca = _real.replace(u"if ($Minimo -and (MaisNovaQue $Minimo $Pacote))",
                              u"if ($false)")
        checar(u"  (a isca cabe no texto da funcao)", _isca != _real)
        out_i, _ = _rodar_harness(base + _isca + u"\n" + corpo)
        zi = (_marcas(out_i).get(u"Z1") or u"").split(u"|") + [u""]
        checar(u"  (isca: sem a comparacao, o pacote v7.9 passaria -- e a "
               u"checagem acima o reprova)", zi[1] != u"recusa", zi[:2])

        aqui = os.path.join(d, "packager")
        os.makedirs(aqui)
        io.open(os.path.join(aqui, "UPDATE.ps1"), "w", encoding="utf-8-sig",
                newline="\r\n").write(
            u"param([string]$Destino = '', [switch]$SemPerguntar)\n"
            u"[System.IO.File]::WriteAllText($env:RADAI_ARGS_FALSO, "
            u"($Destino + '|' + $SemPerguntar))\n"
            u"Write-Output 'atualizador falso falando'\n"
            u"exit ([int]$env:RADAI_RC_FALSO)\n")
        inst = os.path.join(d, "LOCAL_SUITE")
        os.makedirs(inst)
        io.open(os.path.join(inst, "entrega.txt"), "w").write(ent(u"8.0"))
        inst81 = os.path.join(d, "ja81")
        os.makedirs(inst81)
        io.open(os.path.join(inst81, "entrega.txt"), "w").write(ent(u"8.1"))
        inst79 = os.path.join(d, "ja79")
        os.makedirs(inst79)
        io.open(os.path.join(inst79, "entrega.txt"), "w").write(ent(u"7.9"))
        sem_v = os.path.join(d, "sem_versao")
        os.makedirs(sem_v)
        io.open(os.path.join(sem_v, "entrega.txt"), "w").write(u"PROJETO=LOCAL_SUITE\n")
        args = os.path.join(d, "args.txt")

        def aplicar(rc_falso, pasta, funcao=None):
            if os.path.isfile(args):
                os.remove(args)
            h = (u"$ErrorActionPreference = 'Stop'\n"
                 u"Set-StrictMode -Version Latest\n"
                 u"[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)\n"
                 u"$env:RADAI_ARGS_FALSO = '%s'\n"
                 u"$env:RADAI_RC_FALSO = '%d'\n"
                 u"$script:AQUI = '%s'\n"
                 u"$script:VERSAO_INSTALADOR = '8.1'\n"
                 u"$script:PastaInstalada = '%s'\n"
                 u"$script:ResultadoModo3 = ''\n"
                 u"$script:Instalado = $null\n"
                 u"$script:Linhas = New-Object System.Collections.ArrayList\n"
                 u"function Registrar { param([string]$Texto, [string]$Nivel = 'info')\n"
                 u"    [void]$script:Linhas.Add($Nivel + '|' + $Texto) }\n"
                 u"function Pump { }\n"
                 u"function AcharInstalacao { return @{ pasta = 'x'; versao = '8.1' } }\n"
                 u"function PintarEstado { }\n"
                 % (args, rc_falso, aqui, pasta)
                 + fs[u"ComoNumero"] + u"\n" + fs[u"MaisNovaQue"] + u"\n"
                 + fs[u"VersaoDaPasta"] + u"\n" + fs[u"AcompanharProcesso"] + u"\n"
                 + (funcao or fs[u"AplicarCodigoPorCima"]) + u"\n"
                 u"AplicarCodigoPorCima '8.0'\n"
                 u"'LOG:' + (($script:Linhas | ForEach-Object { $_ }) -join ' || ')\n"
                 u"'TELA4:' + $script:ResultadoModo3\n"
                 u"'INST:' + $(if ($script:Instalado) { 'relido' } else { 'nao' })\n"
                 u"'FIM:ok'\n")
            o, _r = _rodar_harness(h)
            mm = _marcas(o)
            chamou = (io.open(args, encoding="utf-8-sig").read()
                      if os.path.isfile(args) else u"")
            return mm, chamou, o

        m0, a0, o0 = aplicar(0, inst)
        checar(u"rc 0: o log diz «pacote v8.0 instalado e codigo atualizado "
               u"para v8.1»",
               u"ok|pacote v8.0 instalado e codigo atualizado para v8.1"
               in (m0.get(u"LOG") or u""), (m0.get(u"LOG") or (o0 or u""))[-240:])
        checar(u"  pelo MESMO caminho do botao: UPDATE.ps1 -Destino <pasta> "
               u"-SemPerguntar", a0 == inst + u"|True", a0)
        checar(u"  a saida do atualizador vai para o log (AcompanharProcesso)",
               u"atualizador falso falando" in (m0.get(u"LOG") or u""))
        checar(u"  e a tela 4 e o painel de estado ficam sabendo",
               u"aplicado por cima" in (m0.get(u"TELA4") or u"")
               and m0.get(u"INST") == u"relido",
               u"%s | %s" % (m0.get(u"TELA4"), m0.get(u"INST")))
        m3, a3, _o3 = aplicar(3, inst)
        _l3 = m3.get(u"LOG") or u""
        checar(u"rc 3 (a impressao divergiu): diz que o pacote nao serve e "
               u"manda montar um novo",
               u"alerta|O PACOTE v8.0 NAO SERVE A ESTA VERSAO" in _l3
               and u"Maquina com internet: montar um pacote para levar para a "
                   u"maquina offline" in _l3, _l3[-200:])
        checar(u"  e diz que o que ficou instalado e' a v8.0",
               u"O que ficou instalado e a v8.0" in _l3
               and u"v8.0" in (m3.get(u"TELA4") or u""), m3.get(u"TELA4"))
        m1, _a1, _o1 = aplicar(1, inst)
        checar(u"outro codigo: diz que o codigo novo nao foi aplicado",
               u"nao foi aplicado (codigo 1)" in (m1.get(u"LOG") or u""),
               (m1.get(u"LOG") or u"")[-160:])
        mv, av, _ov = aplicar(0, u"")
        checar(u"instalacao que nao completou: NAO chama o atualizador",
               av == u"" and u"nao completou" in (mv.get(u"LOG") or u""),
               u"%r | %s" % (av, mv.get(u"LOG")))
        mj, aj, _oj = aplicar(0, inst81)
        checar(u"pasta ja na v8.1 (o INSTALL recusou retroceder): NAO chama",
               aj == u"" and u"ja esta na v8.1" in (mj.get(u"LOG") or u""),
               u"%r | %s" % (aj, mj.get(u"LOG")))
        checar(u"  e a tela 4 diz que o pacote v8.0 nao chegou (e nao «instalado»)",
               u"não chegou" in (mj.get(u"TELA4") or u"")
               and u"v8.1" in (mj.get(u"TELA4") or u""), mj.get(u"TELA4"))
        m79, a79, _o79 = aplicar(0, inst79)
        _l79 = m79.get(u"LOG") or u""
        checar(u"pasta na v7.9 com pacote v8.0 (o INSTALL falhou sobre uma "
               u"instalacao velha): NAO chama o atualizador",
               a79 == u"" and u"alerta|  a pasta instalada esta na v7.9, e nao na v8.0"
               in _l79 and u"pacote v8.0 instalado" not in _l79,
               u"%r | %s" % (a79, _l79[-200:]))
        checar(u"  e a tela 4 diz que a pasta esta na v7.9 e o pacote nao chegou",
               u"não chegou" in (m79.get(u"TELA4") or u"")
               and u"v7.9" in (m79.get(u"TELA4") or u""), m79.get(u"TELA4"))
        ms, as_, _os = aplicar(0, sem_v)
        checar(u"pasta sem VERSAO no entrega.txt: NAO chama (nao ha como saber "
               u"se o pacote chegou)",
               as_ == u"" and u"versao desconhecida" in (ms.get(u"LOG") or u""),
               u"%r | %s" % (as_, ms.get(u"LOG")))
        _real_a = fs[u"AplicarCodigoPorCima"]
        _isca_a = _real_a.replace(u"if (-not $naDoPacote) {", u"if ($false) {")
        checar(u"  (a isca cabe no texto da funcao)", _isca_a != _real_a)
        _mi, ai79, _oi = aplicar(0, inst79, _isca_a)
        checar(u"  (isca: sem a conferencia, a pasta 7.9 receberia o codigo "
               u"da v8.1 -- e a checagem acima o reprova)",
               ai79 == inst79 + u"|True", ai79)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    ps = ler("packager/prepare.ps1")
    i = ps.find(u"function InstalarDeArquivo {")
    f = ps[i:ps.find(u"\nfunction ", i + 10)] if i >= 0 else u""
    cod = u"\n".join(l for l in f.splitlines() if not l.lstrip().startswith(u"#"))
    pos = [cod.find(x) for x in (u"$vz = VersaoDoZip $zip",
                                 u"$dec = DecisaoDoPacote",
                                 u"if ($dec.acao -eq 'recusa') {",
                                 u"InstalarAqui $zip",
                                 u"AplicarCodigoPorCima $vz.versao")]
    checar(u"InstalarDeArquivo: le a versao, decide e recusa ANTES de "
           u"extrair, e aplica o codigo DEPOIS de instalar",
           all(p > 0 for p in pos) and pos == sorted(pos), pos)
    rec = cod[pos[2]:pos[3]] if all(p > 0 for p in pos) else u""
    checar(u"  e a recusa volta sem instalar nada",
           u"return" in rec[:rec.find(u"\n    }") + 1] if rec else False,
           rec[:160])


def _modulo_do_motor():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_ca_v82", os.path.join(RAIZ, "build", "configurar_ambiente.py"))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    return M


def _zip_de_peso(caminho, pasta, macosx=False, extra=(), peso=b"P" * 4096):
    import zipfile as _zf
    with _zf.ZipFile(caminho, "w", _zf.ZIP_DEFLATED) as z:
        z.writestr(pasta + "/", b"")
        base = pasta + "/nnUNetTrainer__nnUNetPlans__3d_fullres/"
        z.writestr(base + "plans.json", b"{}")
        z.writestr(base + "dataset.json", b"{}")
        z.writestr(base + "fold_0/checkpoint_final.pth", peso,
                   compress_type=_zf.ZIP_STORED)
        if macosx:
            z.writestr("__MACOSX/._" + pasta, b"mac")
        for nome, dado in extra:
            z.writestr(nome, dado)


_SINTETICO = (
    "import collections, sys\n"
    "import numpy as np\n"
    "import torch\n"
    "g = torch.Generator().manual_seed(7)\n"
    "enc = torch.randn(3, 4, 5, generator=g)\n"
    "w = collections.OrderedDict()\n"
    "w['encoder.stages.0.conv.weight'] = enc\n"
    "w['decoder.encoder.stages.0.conv.weight'] = enc\n"
    "w['encoder.stages.0.norm.num_batches_tracked'] = torch.tensor(5)\n"
    "w['seg_layers.0.weight'] = torch.linspace(-1, 1, 12).half()\n"
    "w['seg_layers.0.bias'] = enc[1, 2]\n"
    "ck = {'network_weights': w,\n"
    "      'optimizer_state': {'state': {0: {'momentum_buffer':\n"
    "          torch.randn(400, 250, generator=g)}},\n"
    "                          'param_groups': [{'lr': 0.01}]},\n"
    "      'grad_scaler_state': None,\n"
    "      'logging': {'train_losses': [0.5, float('nan'), np.float64(0.25)],\n"
    "                  'epoca': np.arange(3)},\n"
    "      '_best_ema': np.float32(0.9), 'current_epoch': 999,\n"
    "      'init_args': {'plans': {'x': 1}, 'configuration': '3d_fullres',\n"
    "                    'fold': 0},\n"
    "      'trainer_name': 'nnUNetTrainer',\n"
    "      'inference_allowed_mirroring_axes': (0, 1, 2)}\n"
    "modo = sys.argv[2] if len(sys.argv) > 2 else 'cheio'\n"
    "if modo == 'lightning':\n"
    "    ck = {'state_dict': w, 'optimizer_states': [1]}\n"
    "torch.save(ck, sys.argv[1])\n"
)

_ESTRAGAR = (
    "import sys, torch\n"
    "ck = torch.load(sys.argv[1], map_location='cpu', weights_only=False)\n"
    "if sys.argv[3] == 'um_ulp':\n"
    "    t = ck['network_weights']['seg_layers.0.weight']\n"
    "    t.view(torch.int16)[0] += 1\n"
    "elif sys.argv[3] == 'sem_init_args':\n"
    "    ck.pop('init_args')\n"
    "ck.pop('optimizer_state', None)\n"
    "torch.save(ck, sys.argv[2])\n"
    "print(ck.get('radai_modificacao', ''))\n"
)


def _python_do_pacote():
    try:
        b = io.open(os.path.join(RAIZ, "_bundle.txt"),
                    encoding="utf-8-sig").read().strip()
    except Exception:
        return u""
    py = os.path.join(b, "python", "python.exe") if b else u""
    return py if os.path.isfile(py) else u""


def _no_python_do_pacote(py, script, *args):
    r = subprocess.run([py, "-B", "-c", script] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return r.returncode, (r.stdout or u"") + (r.stderr or u"")


def teste_o_estado_do_otimizador_sai_e_a_rede_fica():
    secao(u"o enxugar dos checkpoints: sai o estado do otimizador, a rede "
          u"fica byte a byte")
    import hashlib as _hl
    import types as _types
    C = _modulo_do_motor()
    base = tempfile.mkdtemp(prefix="radai_prep_enxugar_")
    ditas = []
    _log = C.log
    try:
        C.log = lambda m="": ditas.append(u"%s" % m)
        pesos = os.path.join(base, "ts_weights")
        pasta = os.path.join(pesos, "Dataset9101_fantoma")
        fold = os.path.join(pasta, "nnUNetTrainer__nnUNetPlans__3d_fullres",
                            "fold_0")
        os.makedirs(fold)
        io.open(os.path.join(fold, "checkpoint_final.pth"), "wb").write(b"x")
        io.open(os.path.join(fold, "debug.json"), "wb").write(b"{}")
        achados = [p.name for p in C.checkpoints_da_pasta(pasta)]
        checar(u"acha os checkpoints da pasta do dataset, e so eles (%s)"
               % achados, achados == ["checkpoint_final.pth"], achados)
        r = C.enxugar_pasta_de_peso("nao_existe_python.exe", pasta, pesos, {})
        checar(u"sem o Python do pacote, nada se mexe e o log diz que o "
               u"estado do otimizador fica",
               r == [] and io.open(os.path.join(fold, "checkpoint_final.pth"),
                                   "rb").read() == b"x"
               and any(u"fica" in d for d in ditas), ditas[-1:])
        fonte = ler("build/configurar_ambiente.py")
        checar(u"o enxugar so roda depois do download conferido e extraido "
               u"(e nunca no peso que ja estava no disco)",
               _chamada_depois_de(fonte, "instalar_peso_ts",
                                  "enxugar_pasta_de_peso",
                                  "_extrair_como_a_biblioteca")
               and _chamada_depois_de(fonte, "instalar_peso_ts",
                                      "enxugar_pasta_de_peso",
                                      "conferir_peso_ts"))
        isca = fonte.replace(u"_extrair_como_a_biblioteca(zip_, pai, "
                             u"item[\"pasta\"])", u"pass", 1)
        checar(u"(isca) sem a extracao antes, a checagem de ordem reprova",
               isca != fonte and not _chamada_depois_de(
                   isca, "instalar_peso_ts", "enxugar_pasta_de_peso",
                   "_extrair_como_a_biblioteca"))
        tl = os.path.join(base, "b", "python", "Lib", "site-packages", "torch",
                          "lib")
        os.makedirs(tl)
        outra = os.path.join(base, "b", "python", "Lib", "outra.lib")
        for n_ in ("torch_cpu.dll", "torch_cpu.lib", "c10.lib", "c10.dll"):
            io.open(os.path.join(tl, n_), "wb").write(b"z" * 10)
        io.open(outra, "wb").write(b"z")
        tirado = C.tirar_lib_do_torch(os.path.join(base, "b"))
        checar(u"as .lib do torch saem do pacote, as .dll ficam, e nada fora "
               u"de torch\\lib muda (%s)" % sorted(os.listdir(tl)),
               tirado == 20 and sorted(os.listdir(tl))
               == ["c10.dll", "torch_cpu.dll"] and os.path.isfile(outra))
        checar(u"e so no pacote novo: a instalacao no lugar nao perde arquivo",
               _chamada_sob_condicao(fonte, "etapa_libs", "tirar_lib_do_torch",
                                     u"instalar"))
        isca2 = fonte.replace(u'    if not ctx.get("instalar"):\n        '
                              u'tirar_lib_do_torch(ctx["bundle"])',
                              u'    tirar_lib_do_torch(ctx["bundle"])', 1)
        checar(u"(isca) a chamada sem a condicao seria acusada",
               isca2 != fonte and not _chamada_sob_condicao(
                   isca2, "etapa_libs", "tirar_lib_do_torch", u"instalar"))
        py = _python_do_pacote()
        if not py:
            checar(u"PULADO: nao ha pacote montado nesta maquina "
                   u"(_bundle.txt); o enxugar com o torch nao foi provado",
                   True)
            return
        ck = os.path.join(fold, "checkpoint_final.pth")
        cod, saida = _no_python_do_pacote(py, _SINTETICO, ck)
        checar(u"o checkpoint sintetico (nnU-Net, com estado do otimizador) "
               u"foi gravado no Python do pacote", cod == 0, saida[-300:])
        original = os.path.join(base, "original.pth")
        shutil.copy2(ck, original)
        soma0 = _hl.sha256(open(ck, "rb").read()).hexdigest()
        r = C.enxugar_checkpoint(py, ck)
        checar(u"o estado do otimizador saiu (%s: %s -> %s bytes)"
               % (r.get("estado"), r.get("bytes_antes"), r.get("bytes_depois")),
               r.get("estado") == "enxugado"
               and r.get("bytes_depois", 1e12) < r.get("bytes_antes", 0) / 2
               and r.get("sha256_antes") == soma0
               and r.get("sha256_depois") == _hl.sha256(
                   open(ck, "rb").read()).hexdigest(), r)
        checar(u"e nenhum arquivo de passagem sobrou na pasta",
               sorted(os.listdir(fold)) == ["checkpoint_final.pth",
                                            "debug.json"], os.listdir(fold))
        cmp_ = C.comparar_checkpoints(py, original, ck)
        checar(u"a rede e as outras entradas sao identicas byte a byte "
               u"(%s tensores, digest %s)" % (cmp_.get("tensores"),
                                               (cmp_.get("digest_a") or u"")[:12]),
               cmp_.get("estado") == "iguais" and cmp_.get("tensores") == 5
               and cmp_.get("digest_a") == cmp_.get("digest_b")
               == r.get("digest_rede"), cmp_)
        cod, aviso = _no_python_do_pacote(py, _ESTRAGAR, ck,
                                          os.path.join(base, "lixo.pth"),
                                          "nada")
        checar(u"o arquivo enxuto leva o aviso de modificacao dentro dele",
               u"optimizer_state removido" in aviso, aviso[-200:])
        for modo, chave in (("um_ulp", "network_weights"),
                            ("sem_init_args", "init_args")):
            estragado = os.path.join(base, "isca_%s.pth" % modo)
            _no_python_do_pacote(py, _ESTRAGAR, original, estragado, modo)
            c2 = C.comparar_checkpoints(py, original, estragado)
            checar(u"(isca) %s: a comparacao acusa (%s)"
                   % (modo, c2.get("diferem")),
                   c2.get("estado") == "diferentes"
                   and chave in (c2.get("diferem") or []), c2)
        r2 = C.enxugar_checkpoint(py, ck)
        checar(u"rodar de novo nao mexe no arquivo ja enxuto",
               r2.get("estado") == "sem_estado_do_otimizador"
               and _hl.sha256(open(ck, "rb").read()).hexdigest()
               == r.get("sha256_depois"), r2)
        outro = os.path.join(base, "lightning.pth")
        _no_python_do_pacote(py, _SINTETICO, outro, "lightning")
        s_outro = _hl.sha256(open(outro, "rb").read()).hexdigest()
        r3 = C.enxugar_checkpoint(py, outro)
        checar(u"checkpoint que nao e do nnU-Net fica como veio",
               r3.get("estado") == "nao_e_nnunet"
               and _hl.sha256(open(outro, "rb").read()).hexdigest() == s_outro,
               r3)

        www = os.path.join(base, "www", "v9-weights")
        os.makedirs(www)
        _no_python_do_pacote(py, _SINTETICO, os.path.join(base, "ck9102.pth"))
        bruto = open(os.path.join(base, "ck9102.pth"), "rb").read()
        _zip_de_peso(os.path.join(www, "Dataset9102_fantoma.zip"),
                     "Dataset9102_fantoma", peso=bruto)
        S = _Servidor(os.path.join(base, "www"))
        _tab, _time = C.tabela_da_biblioteca, C.time
        try:
            C.time = _types.SimpleNamespace(time=time.time,
                                            sleep=lambda s: None)
            C.tabela_da_biblioteca = lambda p, t, extra=(), env=None: {
                "base": S.base, "velhos": [], "versao_ts": "fantoma",
                "itens": [{"id": 9102, "pasta": "Dataset9102_fantoma",
                           "rel_path": "", "zip": "Dataset9102_fantoma.zip",
                           "url": "%s/v9-weights/Dataset9102_fantoma.zip"
                                  % S.base, "de_onde": "fantoma"}]}
            ofi = os.path.join(base, "oficina")
            os.makedirs(ofi)
            pesos2 = os.path.join(base, "ts2")
            falhas = C.baixar_pesos_ts(py, ["fantoma"], pesos2,
                                       os.path.join(base, "cache"),
                                       oficina=ofi)
            rel = ("Dataset9102_fantoma/nnUNetTrainer__nnUNetPlans__3d_fullres"
                   "/fold_0/checkpoint_final.pth")
            no_disco = os.path.join(pesos2, *rel.split("/"))
            recibo = json.load(io.open(os.path.join(ofi, C.RECIBO_DO_ENXUGAR),
                                       encoding="utf-8"))
            checar(u"no download conferido, o preparo tira o estado do "
                   u"otimizador e grava o recibo com as duas somas",
                   not falhas and os.path.getsize(no_disco) < len(bruto) / 2
                   and (recibo.get(rel) or {}).get("sha256_antes")
                   == _hl.sha256(bruto).hexdigest()
                   and (recibo.get(rel) or {}).get("sha256_depois")
                   == _hl.sha256(open(no_disco, "rb").read()).hexdigest(),
                   (falhas, recibo))
            checar(u"e o log diz o que saiu e que a rede ficou identica",
                   any(u"estado do otimizador removido" in d
                       and u"identicos" in d for d in ditas), ditas[-6:])
            shutil.copy2(os.path.join(base, "ck9102.pth"), no_disco)
            C.baixar_pesos_ts(py, ["fantoma"], pesos2,
                              os.path.join(base, "cache"), oficina=ofi)
            checar(u"o peso que ja estava no disco nao e reescrito (a estacao "
                   u"instalada nao muda)",
                   open(no_disco, "rb").read() == bruto)
        finally:
            C.tabela_da_biblioteca, C.time = _tab, _time
            S.fechar()
        man = os.path.join(base, "man")
        os.makedirs(man)
        from pathlib import Path as _P
        ctx = {"projeto": "LOCAL_SUITE", "versao": "9.9", "so_cpu": True,
               "cuda": "cpu", "bundle": _P(base), "cache": _P(base) / "c",
               "destino": _P(ofi)}
        C._escrever_manifesto(ctx, man)
        texto = io.open(os.path.join(man, "MANIFESTO.txt"),
                        encoding="utf-8").read()
        checar(u"o MANIFESTO lista o checkpoint enxuto, com as duas somas e "
               u"a prova da rede", u"SEM O ESTADO DO OTIMIZADOR" in texto
               and (recibo.get(rel) or {}).get("sha256_antes", u"?") in texto
               and u"identicos byte a byte" in texto)
    finally:
        C.log = _log
        shutil.rmtree(base, ignore_errors=True)


_SINTETICO_V1 = (
    "import collections, sys\n"
    "import torch\n"
    "g = torch.Generator().manual_seed(11)\n"
    "w = collections.OrderedDict()\n"
    "w['conv_blocks_context.0.blocks.0.conv.weight'] = torch.randn(\n"
    "    4, 1, 3, 3, 3, generator=g)\n"
    "w['conv_blocks_context.0.blocks.0.instnorm.weight'] = torch.ones(4)\n"
    "w['seg_outputs.0.weight'] = torch.randn(21, 4, 1, 1, 1, generator=g)\n"
    "ck = {'epoch': 1000, 'state_dict': w,\n"
    "      'optimizer_state_dict': {'state': {0: {'momentum_buffer':\n"
    "          torch.randn(400, 250, generator=g)}},\n"
    "          'param_groups': [{'lr': 0.01, 'momentum': 0.99}]},\n"
    "      'lr_scheduler_state_dict': None,\n"
    "      'plot_stuff': ([0.5, 0.4], [0.6, 0.5], [0.1, 0.2], [0.7]),\n"
    "      'best_stuff': (0, 0.4, 0.4, 900),\n"
    "      'amp_grad_scaler': {'scale': 65536.0}}\n"
    "torch.save(ck, sys.argv[1])\n"
)

_LER_AVISO = (
    "import sys, torch\n"
    "ck = torch.load(sys.argv[1], map_location='cpu', weights_only=False)\n"
    "print(ck.get('radai_modificacao', ''))\n"
    "print(sorted(ck))\n"
)


def teste_o_enxugar_dos_modelos_do_registro():
    secao(u"o enxugar dos modelos do registro: nnU-Net v1 e v2, enxuto "
          u"reprodutivel e conferido pelo sha256 do registro")
    import hashlib as _hl
    import types as _types
    from pathlib import Path as _P
    C = _modulo_do_motor()
    py = _python_do_pacote()
    if not py:
        checar(u"PULADO: nao ha pacote montado nesta maquina (_bundle.txt); "
               u"o enxugar dos modelos do registro nao foi provado", True)
        return
    soma = lambda p: _hl.sha256(open(p, "rb").read()).hexdigest()
    base = tempfile.mkdtemp(prefix="radai_prep_enxugar_")
    _log = C.log
    velho_dir = os.environ.get("RADAI_MODELOS_DIR")
    M = None
    try:
        C.log = lambda m="": None
        v1 = os.path.join(base, "v1_original.model")
        cod, saida = _no_python_do_pacote(py, _SINTETICO_V1, v1)
        checar(u"o checkpoint sintetico do nnU-Net v1 foi gravado no Python "
               u"do pacote", cod == 0, saida[-300:])
        ck = os.path.join(base, "a", "model_final_checkpoint.model")
        os.makedirs(os.path.dirname(ck))
        shutil.copy2(v1, ck)
        r = C.enxugar_checkpoint(py, ck)
        checar(u"nnU-Net v1: sai o optimizer_state_dict (%s: %s -> %s bytes)"
               % (r.get("estado"), r.get("bytes_antes"), r.get("bytes_depois")),
               r.get("estado") == "enxugado"
               and r.get("removido") == "optimizer_state_dict"
               and r.get("bytes_depois", 1e12) < r.get("bytes_antes", 0) / 2, r)
        cmp_ = C.comparar_checkpoints(py, v1, ck)
        checar(u"  e o state_dict e as outras entradas sao identicos byte a "
               u"byte (%s tensores)" % cmp_.get("tensores"),
               cmp_.get("estado") == "iguais" and cmp_.get("tensores") == 3
               and cmp_.get("digest_a") == cmp_.get("digest_b")
               == r.get("digest_rede"), cmp_)
        cod, aviso = _no_python_do_pacote(py, _LER_AVISO, ck)
        checar(u"  e o aviso de modificacao no arquivo diz o que saiu do "
               u"formato v1", u"optimizer_state_dict removido" in aviso
               and u"state_dict e as demais" in aviso
               and u"'plot_stuff'" in aviso, aviso[-300:])

        outro = os.path.join(base, "b_outra_pasta", "outro_nome.pth")
        os.makedirs(os.path.dirname(outro))
        shutil.copy2(v1, outro)
        r2 = C.enxugar_checkpoint(py, outro)
        checar(u"o enxuto e reprodutivel: o mesmo original noutra pasta e com "
               u"outro nome da o mesmo sha256",
               bool(r2.get("sha256_depois"))
               and r2.get("sha256_depois") == r.get("sha256_depois"),
               (r2.get("sha256_depois"), r.get("sha256_depois")))

        def _pelo_script(script, caminho):
            _c, s = _no_python_do_pacote(py, script, "enxugar", caminho)
            linha = [l for l in s.splitlines() if l.startswith("ENXUGAR_JSON ")]
            return json.loads(linha[0][len("ENXUGAR_JSON "):]) if linha else {}
        isca = C._SCRIPT_ENXUGAR.replace(
            u"    with open(tmp, 'wb') as saida:\n"
            u"        torch.save(novo, saida)\n",
            u"    torch.save(novo, tmp)\n", 1)
        c1 = os.path.join(base, "isca1", "model_final_checkpoint.model")
        c2 = os.path.join(base, "isca2", "x.pth")
        for c in (c1, c2):
            os.makedirs(os.path.dirname(c))
            shutil.copy2(v1, c)
        s1 = _pelo_script(isca, c1).get("sha256_depois")
        s2 = _pelo_script(isca, c2).get("sha256_depois")
        checar(u"(isca) gravando pelo caminho, o nome do arquivo entra no zip "
               u"e o sha256 do enxuto muda com ele",
               isca != C._SCRIPT_ENXUGAR and s1 and s2 and s1 != s2, (s1, s2))

        e1 = os.path.join(base, "esperado", "model_final_checkpoint.model")
        os.makedirs(os.path.dirname(e1))
        shutil.copy2(v1, e1)
        r3 = C.enxugar_checkpoint(py, e1, esperado="0" * 64)
        checar(u"com o sha256 do registro diferente, o enxuto nao entra e o "
               u"original fica", r3.get("estado") == "diverge"
               and soma(e1) == soma(v1)
               and not os.path.exists(e1 + ".enxuto.parcial"), r3)
        r4 = C.enxugar_checkpoint(py, e1, esperado=r.get("sha256_depois"))
        checar(u"  e com o sha256 do registro, entra",
               r4.get("estado") == "enxugado"
               and soma(e1) == r.get("sha256_depois"), r4)

        rel = "fold_0/model_final_checkpoint.model"
        bundle = os.path.join(base, "bundle")
        ofi = os.path.join(base, "oficina")
        os.makedirs(ofi)
        alvo = os.path.join(bundle, "modelos", "fantoma", *rel.split("/"))
        estado = {"baixa": True}

        def _baixar(ident):
            if estado["baixa"]:
                os.makedirs(os.path.dirname(alvo), exist_ok=True)
                shutil.copyfile(v1, alvo)
                return {"baixados": [rel]}
            return {"pulados": [rel]}
        falso = _types.SimpleNamespace(
            MODELOS={"fantoma": {
                "nome": u"fantoma", "repo": "x/y", "licenca": u"x · livre",
                "uso_permitido": "livre",
                "enxuto": {rel: (r["bytes_depois"], r["sha256_depois"])}}},
            estado_do_modelo=lambda i: {"bytes_total": 0},
            pasta_do_modelo=lambda i, criar=False: _P(bundle) / "modelos" / i,
            baixar=_baixar)
        ctx = {"bundle": _P(bundle), "py": py, "destino": _P(ofi),
               "instalar": ""}
        C.baixar_modelos_do_registro(ctx, falso, [], exigidos=set())
        chave = "modelos/fantoma/" + rel
        try:
            recibo = json.load(io.open(os.path.join(ofi, C.RECIBO_DO_ENXUGAR),
                                       encoding="utf-8"))
        except Exception:
            recibo = {}
        checar(u"no download conferido, o preparo enxuga o checkpoint que o "
               u"registro declara, e o recibo guarda as duas somas",
               os.path.isfile(alvo) and soma(alvo) == r["sha256_depois"]
               and (recibo.get(chave) or {}).get("sha256_antes") == soma(v1)
               and (recibo.get(chave) or {}).get("sha256_depois")
               == r["sha256_depois"], recibo)
        shutil.copyfile(v1, alvo)
        estado["baixa"] = False
        C.baixar_modelos_do_registro(ctx, falso, [], exigidos=set())
        checar(u"o checkpoint que ja estava no disco nao e reescrito",
               soma(alvo) == soma(v1))
        os.remove(alvo)
        estado["baixa"] = True
        C.baixar_modelos_do_registro(dict(ctx, instalar=bundle), falso, [],
                                     exigidos=set())
        checar(u"e na instalacao no lugar (nao e pacote novo) o que chega "
               u"fica como veio", soma(alvo) == soma(v1))
        man = os.path.join(base, "man")
        os.makedirs(man)
        C._escrever_manifesto({"projeto": "LOCAL_SUITE", "versao": "9.9",
                               "so_cpu": True, "cuda": "cpu",
                               "bundle": _P(bundle), "cache": _P(base) / "c",
                               "destino": _P(ofi)}, man)
        checar(u"o MANIFESTO lista o checkpoint enxuto do modelo",
               chave in io.open(os.path.join(man, "MANIFESTO.txt"),
                                encoding="utf-8").read())

        import radai_models as M
        rel2 = "nnUNetTrainer__nnUNetPlans__3d_fullres/fold_all/checkpoint_final.pth"
        d_reg = os.path.join(base, "reg")
        alvo2 = os.path.join(d_reg, "modelos", "fantoma_enx", *rel2.split("/"))
        os.makedirs(os.path.dirname(alvo2))
        M.MODELOS["fantoma_enx"] = {
            "nome": u"fantoma", "motor": "x", "embutido": False, "repo": "x/y",
            "arquivos": [(rel2, r["bytes_antes"])], "sha256": {rel2: soma(v1)},
            "enxuto": {rel2: (r["bytes_depois"], r["sha256_depois"])},
            "licenca": u"x", "uso_permitido": "livre"}

        def _confere():
            try:
                C.conferir_modelos_exigidos(d_reg, [u"fantoma_enx"])
                return None
            except C.FaltaModeloExigido as e:
                return u"%s" % e
        shutil.copyfile(ck, alvo2)
        checar(u"a conferencia dos modelos exigidos aceita o enxuto do "
               u"registro", _confere() is None, _confere())
        shutil.copyfile(v1, alvo2)
        checar(u"  e o original", _confere() is None, _confere())
        M.MODELOS["fantoma_enx"]["enxuto"] = {rel2: (r["bytes_depois"],
                                                     "0" * 64)}
        shutil.copyfile(ck, alvo2)
        checar(u"(isca) o enxuto que nao e o do registro PARA o pacote",
               _confere() is not None)
    finally:
        C.log = _log
        if M is not None:
            M.MODELOS.pop("fantoma_enx", None)
        if velho_dir is None:
            os.environ.pop("RADAI_MODELOS_DIR", None)
        else:
            os.environ["RADAI_MODELOS_DIR"] = velho_dir
        shutil.rmtree(base, ignore_errors=True)


def _chamada_sob_condicao(fonte, funcao, chamada, palavra):
    import ast as _ast
    for no in _ast.walk(_ast.parse(fonte)):
        if isinstance(no, _ast.FunctionDef) and no.name == funcao:
            for se in _ast.walk(no):
                if not isinstance(se, _ast.If) or palavra not in \
                        _ast.unparse(se.test):
                    continue
                for sub in se.body:
                    for c in _ast.walk(sub):
                        if isinstance(c, _ast.Call) and getattr(
                                c.func, "id", "") == chamada:
                            return True
    return False


def _chamada_depois_de(fonte, funcao, chamada, antes):
    import ast as _ast
    for no in _ast.walk(_ast.parse(fonte)):
        if isinstance(no, _ast.FunctionDef) and no.name == funcao:
            linhas = {}
            for sub in _ast.walk(no):
                if isinstance(sub, _ast.Call):
                    f = sub.func
                    nome = f.attr if isinstance(f, _ast.Attribute) else \
                        getattr(f, "id", "")
                    linhas.setdefault(nome, []).append(sub.lineno)
            return bool(linhas.get(chamada)) and bool(linhas.get(antes)) \
                and min(linhas[chamada]) > max(linhas[antes])
    return False


class _Servidor(object):

    def __init__(self, pasta):
        import http.server as _hs
        import threading as _th
        self.pedidos = []
        self.roteiro = {}
        dono = self

        class _H(_hs.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=pasta, **kw)

            def do_GET(self):
                dono.pedidos.append(self.path)
                fila = dono.roteiro.get(self.path)
                if fila:
                    cod = fila.pop(0)
                    self.send_response(cod)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return None
                return super().do_GET()

            def log_message(self, *a):
                pass
        self.srv = _hs.ThreadingHTTPServer(("127.0.0.1", 0), _H)
        _th.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def fechar(self):
        try:
            self.srv.shutdown()
            self.srv.server_close()
        except Exception:
            pass


def teste_pesos_ts_baixados_por_nos():
    secao(u"os pesos do TotalSegmentator: baixados por nos, conferidos, "
          u"extraidos como a biblioteca")
    import hashlib as _hl
    import types as _types
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    C = _modulo_do_motor()
    import artefatos as A
    base = tempfile.mkdtemp(prefix="radai_prep_pesos_ts_")
    www = os.path.join(base, "www", "v9-weights")
    os.makedirs(www)
    S = _Servidor(os.path.join(base, "www"))
    ditas = []
    _log, _time = C.log, C.time
    _tab = C.tabela_da_biblioteca
    _pesos_ts = dict(A.PESOS_TS)
    try:
        C.log = lambda m="": ditas.append(u"%s" % m)
        C.time = _types.SimpleNamespace(time=time.time, sleep=lambda s: None)
        _zip_de_peso(os.path.join(www, "Dataset9001_bom_a.zip"),
                     "Dataset9001_bom_a", macosx=True)
        _zip_de_peso(os.path.join(www, "Dataset9002_bom_b.zip"),
                     "Dataset9002_bom_b")
        _zip_de_peso(os.path.join(www, "Dataset9003_crc.zip"),
                     "Dataset9003_crc", peso=b"Q" * 50000)
        b3 = bytearray(open(os.path.join(www, "Dataset9003_crc.zip"), "rb").read())
        i3 = bytes(b3).find(b"Q" * 1000) + 500
        b3[i3] ^= 0xFF
        open(os.path.join(www, "Dataset9003_crc.zip"), "wb").write(bytes(b3))
        _zip_de_peso(os.path.join(www, "Dataset9004_forma.zip"),
                     "Dataset9004_forma", extra=(("outra_pasta/x.txt", b"x"),))
        _zip_de_peso(os.path.join(www, "Dataset9005_escapa.zip"),
                     "Dataset9005_escapa", extra=(("Dataset9005_escapa/../../fora.txt", b"x"),))

        def _itens(ids_pastas):
            return [{"id": i, "pasta": p, "rel_path": "", "zip": p + ".zip",
                     "url": "%s/v9-weights/%s.zip" % (S.base, p),
                     "de_onde": "fantoma"} for i, p in ids_pastas]
        todos = [(9001, "Dataset9001_bom_a"), (9002, "Dataset9002_bom_b"),
                 (9003, "Dataset9003_crc"), (9004, "Dataset9004_forma"),
                 (9005, "Dataset9005_escapa")]
        C.tabela_da_biblioteca = lambda py, tasks, extra=(), env=None: {
            "base": S.base, "velhos": ["Task999_geracao_velha"],
            "versao_ts": "fantoma", "itens": _itens(todos)}
        pesos = os.path.join(base, "ts_weights")
        cache = os.path.join(base, "cache")
        ofi = os.path.join(base, "oficina")
        os.makedirs(os.path.join(pesos, "Task999_geracao_velha"))
        os.makedirs(ofi)
        falhas = C.baixar_pesos_ts("py", ["fantoma"], pesos, cache,
                                   oficina=ofi)
        ck = lambda p: os.path.join(pesos, p, "nnUNetTrainer__nnUNetPlans__"
                                    "3d_fullres", "fold_0", "checkpoint_final.pth")
        checar(u"os dois zips BONS foram extraidos no lugar da biblioteca",
               os.path.isfile(ck("Dataset9001_bom_a"))
               and os.path.isfile(ck("Dataset9002_bom_b")), sorted(os.listdir(pesos)))
        checar(u"  e o __MACOSX do zip veio junto, como o `extractall` faz",
               os.path.isdir(os.path.join(pesos, "__MACOSX")))
        checar(u"  e o zip saiu do cache depois de extraido (disco do pacote)",
               not os.listdir(os.path.join(cache, "pesos_ts")),
               os.listdir(os.path.join(cache, "pesos_ts")))
        checar(u"  e nenhuma pasta de passagem sobrou",
               not [d for d in os.listdir(pesos) if d.startswith(".x")],
               os.listdir(pesos))
        checar(u"a pasta de geracao antiga saiu (a limpeza da biblioteca)",
               not os.path.exists(os.path.join(pesos, "Task999_geracao_velha")))
        checar(u"(isca) CRC quebrado e' RECUSADO",
               9003 in falhas and u"CRC" in falhas[9003], falhas.get(9003))
        checar(u"  e nada dele foi extraido",
               not os.path.exists(os.path.join(pesos, "Dataset9003_crc")))
        checar(u"(isca) membro fora da pasta do dataset e' RECUSADO",
               9004 in falhas and u"forma" in falhas[9004], falhas.get(9004))
        checar(u"(isca) membro com `..` e' RECUSADO antes de extrair",
               9005 in falhas and u"fora da pasta" in falhas[9005]
               and not os.path.exists(os.path.join(base, "fora.txt")),
               falhas.get(9005))
        checar(u"  e o zip recusado nao fica no cache (cache nao e prova)",
               not os.listdir(os.path.join(cache, "pesos_ts")))
        reg = json.load(io.open(os.path.join(ofi, C.REGISTRO_DOS_PESOS),
                                encoding="utf-8"))
        soma_a = _hl.sha256(open(os.path.join(www, "Dataset9001_bom_a.zip"),
                                 "rb").read()).hexdigest()
        checar(u"o recibo guarda a soma MEDIDA de cada zip",
               (reg.get("Dataset9001_bom_a.zip") or {}).get("sha256") == soma_a,
               reg.get("Dataset9001_bom_a.zip"))
        checar(u"  e diz que ele estava FORA da tabela do projeto",
               u"FORA DA TABELA" in (reg.get("Dataset9001_bom_a.zip") or {})
               .get("veredito", u""))
        checar(u"  e a soma medida sai no log",
               any(u"sha256 medido: " + soma_a in d for d in ditas))

        n0 = len(S.pedidos)
        C.tabela_da_biblioteca = lambda py, tasks, extra=(), env=None: {
            "base": S.base, "velhos": [], "versao_ts": "fantoma",
            "itens": _itens(todos[:2])}
        os.remove(ck("Dataset9002_bom_b"))
        falhas2 = C.baixar_pesos_ts("py", ["fantoma"], pesos, cache,
                                    oficina=ofi)
        novos = S.pedidos[n0:]
        checar(u"o que ja esta no disco NAO e' baixado de novo",
               not any("9001" in p for p in novos), novos)
        checar(u"(isca) pasta SEM checkpoint e' refeita, e nao tomada por pronta",
               any("9002" in p for p in novos)
               and os.path.isfile(ck("Dataset9002_bom_b")) and not falhas2,
               novos)

        zb = os.path.join(www, "Dataset9002_bom_b.zip")
        tam_b = os.path.getsize(zb)
        soma_b = _hl.sha256(open(zb, "rb").read()).hexdigest()
        C.tabela_da_biblioteca = lambda py, tasks, extra=(), env=None: {
            "base": S.base, "velhos": [], "versao_ts": "fantoma",
            "itens": _itens([(9002, "Dataset9002_bom_b")])}
        for rotulo, entrada, deve in (
                (u"tamanho da tabela que nao bate", {"bytes": tam_b + 1,
                                                    "sha256": None}, u"bytes"),
                (u"SHA-256 da origem que nao bate", {"bytes": tam_b,
                                                    "sha256": "0" * 64,
                                                    "origem_publica_o_hash": True},
                 u"NAO CONFERE")):
            shutil.rmtree(os.path.join(pesos, "Dataset9002_bom_b"),
                          ignore_errors=True)
            A.PESOS_TS["Dataset9002_bom_b.zip"] = dict(entrada)
            try:
                f3 = C.baixar_pesos_ts("py", ["fantoma"], pesos, cache)
                checar(u"(isca) %s LEVANTA `DivergeDaOrigem` (e nao vira "
                       u"falha que a reserva cobre)" % rotulo, False,
                       u"voltou com falhas=%r" % (f3,))
            except C.DivergeDaOrigem as e:
                checar(u"(isca) %s LEVANTA `DivergeDaOrigem` (e nao vira "
                       u"falha que a reserva cobre)" % rotulo,
                       deve in u"%s" % e and u"nao troca a base pela reserva"
                       in u"%s" % e, (u"%s" % e)[:160])
            checar(u"  e nada dele foi extraido, e o zip nao ficou no cache",
                   not os.path.exists(os.path.join(pesos, "Dataset9002_bom_b"))
                   and not os.listdir(os.path.join(cache, "pesos_ts")),
                   os.listdir(os.path.join(cache, "pesos_ts")))
        _dv = A.diverge_da_origem
        try:
            A.diverge_da_origem = lambda *a, **kw: False
            shutil.rmtree(os.path.join(pesos, "Dataset9002_bom_b"),
                          ignore_errors=True)
            try:
                f3b = C.baixar_pesos_ts("py", ["fantoma"], pesos, cache)
            except C.DivergeDaOrigem:
                f3b = u"levantou"
            checar(u"  (isca) sem a pergunta `diverge_da_origem`, o zip "
                   u"divergente volta a ser so' uma falha (o defeito de 24/09)",
                   isinstance(f3b, dict) and 9002 in f3b, f3b)
        finally:
            A.diverge_da_origem = _dv
        shutil.rmtree(os.path.join(pesos, "Dataset9002_bom_b"),
                      ignore_errors=True)
        A.PESOS_TS["Dataset9002_bom_b.zip"] = {"release": "v1-weights",
                                               "bytes": tam_b + 1,
                                               "sha256": None}
        try:
            C.baixar_pesos_ts("py", ["fantoma"], pesos, cache)
            _pino = u"voltou sem levantar"
        except C.DivergeDaOrigem as e:
            _pino = u"%s" % e
        checar(u"release da tabela diferente da que a biblioteca pede: a "
               u"frase diz que o PINO subiu sem a tabela",
               u"o pino do TotalSegmentator subiu" in _pino, _pino[-200:])
        shutil.rmtree(os.path.join(pesos, "Dataset9002_bom_b"), ignore_errors=True)
        A.PESOS_TS["Dataset9002_bom_b.zip"] = {"bytes": tam_b, "sha256": soma_b,
                                               "origem_publica_o_hash": True}
        ditas[:] = []
        f4 = C.baixar_pesos_ts("py", ["fantoma"], pesos, cache)
        checar(u"com tamanho e soma certos, PASSA -- e diz que conferiu a soma",
               not f4 and any(u"SHA-256 (publicado pela origem)" in d
                              for d in ditas), f4)

        shutil.rmtree(os.path.join(pesos, "Dataset9002_bom_b"))
        zc = os.path.join(cache, "pesos_ts", "Dataset9002_bom_b.zip")
        shutil.copy2(zb, zc)
        n1 = len(S.pedidos)
        C.baixar_pesos_ts("py", ["fantoma"], pesos, cache)
        checar(u"zip BOM no cache e' reusado sem ir a rede",
               len(S.pedidos) == n1 and os.path.isfile(ck("Dataset9002_bom_b")),
               S.pedidos[n1:])
        shutil.rmtree(os.path.join(pesos, "Dataset9002_bom_b"))
        open(zc, "wb").write(b"<html>404</html>")
        n2 = len(S.pedidos)
        C.baixar_pesos_ts("py", ["fantoma"], pesos, cache)
        checar(u"(isca) zip PODRE no cache sai, e o arquivo desce de novo",
               len(S.pedidos) == n2 + 1 and os.path.isfile(ck("Dataset9002_bom_b")),
               S.pedidos[n2:])

        C.tabela_da_biblioteca = lambda py, tasks, extra=(), env=None: {
            "base": "http://127.0.0.1:9", "velhos": [], "versao_ts": "fantoma",
            "itens": [{"id": 9006, "pasta": "Dataset9006_x", "rel_path": "",
                       "zip": "Dataset9006_x.zip", "de_onde": "fantoma",
                       "url": "http://127.0.0.1:9/Dataset9006_x.zip"}]}
        try:
            C.baixar_pesos_ts("py", ["fantoma"], pesos, cache)
            checar(u"sem rede, `SemRede` SOBE (nao e' anotado como artefato)",
                   False, u"voltou sem levantar")
        except C.SemRede:
            checar(u"sem rede, `SemRede` SOBE (nao e' anotado como artefato)",
                   True)

        fonte = ler("build/configurar_ambiente.py")
        _m = fonte[fonte.find(u"def _escrever_manifesto("):]
        _m = _m[:_m.find(u"\ndef ", 10)]
        checar(u"o MANIFESTO.txt le o recibo dos pesos conferidos",
               u"_ler_registro_dos_pesos(ctx[\"destino\"])" in _m
               and u"NO PACOTE SEM CONFERENCIA" in _m)
        checar(u"  e o paragrafo que dizia «NAO confere hash» saiu do TEXTO "
               u"do manifesto",
               u'linhas.append("  que NAO confere hash no download.' not in _m)
        _e = fonte[fonte.find(u"def _extrair_como_a_biblioteca("):]
        _e = _e[:_e.find(u"\ndef ", 10)]
        checar(u"a pasta de passagem da extracao tem nome CURTO (MAX_PATH)",
               u'passagem = pai / (".x"' in _e and u".extraindo_\" + pasta" not in _e)
    finally:
        C.log, C.time, C.tabela_da_biblioteca = _log, _time, _tab
        A.PESOS_TS.clear()
        A.PESOS_TS.update(_pesos_ts)
        S.fechar()
        shutil.rmtree(base, ignore_errors=True)


def teste_o_servidor_e_a_segunda_passada():
    secao(u"o servidor que responde 5xx e a segunda passada, antes da reserva")
    import inspect as _insp
    import textwrap as _tw
    import types as _types
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    C = _modulo_do_motor()
    base = tempfile.mkdtemp(prefix="radai_prep_5xx_")
    www = os.path.join(base, "www", "v9-weights")
    os.makedirs(www)
    S = _Servidor(os.path.join(base, "www"))
    ditas = []
    _log, _time, _tab = C.log, C.time, C.tabela_da_biblioteca
    try:
        C.log = lambda m="": ditas.append(u"%s" % m)
        C.time = _types.SimpleNamespace(time=time.time, sleep=lambda s: None)
        _zip_de_peso(os.path.join(www, "Dataset9101_x.zip"), "Dataset9101_x")
        cam = "/v9-weights/Dataset9101_x.zip"
        C.tabela_da_biblioteca = lambda py, tasks, extra=(), env=None: {
            "base": S.base, "velhos": [], "versao_ts": "fantoma",
            "itens": [{"id": 9101, "pasta": "Dataset9101_x", "rel_path": "",
                       "zip": "Dataset9101_x.zip", "de_onde": "fantoma",
                       "url": S.base + cam}]}
        pesos = os.path.join(base, "ts_weights")
        cache = os.path.join(base, "cache")
        ck = os.path.join(pesos, "Dataset9101_x", "nnUNetTrainer__nnUNetPlans__"
                          "3d_fullres", "fold_0", "checkpoint_final.pth")

        def _rodar(roteiro, fn=None):
            shutil.rmtree(pesos, ignore_errors=True)
            shutil.rmtree(cache, ignore_errors=True)
            S.roteiro[cam] = list(roteiro)
            n0 = len(S.pedidos)
            try:
                r = (fn or C.baixar_pesos_ts)("py", ["fantoma"], pesos, cache)
            except Exception as e:
                r = e
            finally:
                S.roteiro.pop(cam, None)
            return r, sum(1 for p in S.pedidos[n0:] if p == cam)

        ditas[:] = []
        r, n = _rodar([503, 503])
        checar(u"503, 503 e depois o arquivo: baixa na terceira tentativa",
               r == {} and n == 3 and os.path.isfile(ck), u"%r, %d pedido(s)"
               % (r, n))
        checar(u"  e o log diz que foi o SERVIDOR (HTTP 503), e nao a conexao",
               any(u"o servidor respondeu HTTP 503" in d for d in ditas))
        _eds = C.erro_do_servidor
        try:
            C.erro_do_servidor = lambda e: None
            r_i, n_i = _rodar([503, 503])
        finally:
            C.erro_do_servidor = _eds
        checar(u"  (isca) sem `erro_do_servidor`, o 503 vira UM pedido e uma "
               u"falha -- o defeito que a revisao provou",
               n_i == 1 or (isinstance(r_i, dict) and 9101 in r_i),
               u"%r, %d pedido(s)" % (r_i, n_i))

        r, n = _rodar([503] * 10)
        checar(u"503 para sempre: `ServidorFora`, e nao falha que a reserva "
               u"cobre", isinstance(r, C.ServidorFora), repr(r)[:120])
        checar(u"  e com 3 pedidos (as tentativas de rede), nem mais nem menos",
               n == 3, n)
        checar(u"  e com o codigo 5 e o cabecalho do servidor",
               getattr(r, "codigo", None) == 5
               and u"SERVIDOR" in getattr(r, "cabecalho", u""))
        checar(u"  e a frase diz que a rede desta maquina funciona",
               u"a rede desta maquina funciona" in u"%s" % r
               and u"HTTP 503" in u"%s" % r, (u"%s" % r)[:160])
        checar(u"  e ela e' uma `SemRede` (o laco das etapas a trata como "
               u"conexao, e nao como FALHOU)", isinstance(r, C.SemRede))
        r, n = _rodar([504] * 10)
        checar(u"504 (gateway timeout) sai como SERVIDOR, e nao como «sem "
               u"conexao»", isinstance(r, C.ServidorFora), repr(r)[:120])
        checar(u"(isca) 404 NAO e' erro do servidor (continua artefato)",
               C.erro_do_servidor(__import__("urllib.error").error.HTTPError(
                   "u", 404, "Not Found", {}, None)) is None)

        ditas[:] = []
        r, n = _rodar([404])
        checar(u"404 e depois o arquivo: a segunda passada o traz",
               r == {} and n == 2 and os.path.isfile(ck),
               u"%r, %d pedido(s)" % (r, n))
        checar(u"  e o log diz «segunda tentativa»",
               any(u"segunda tentativa" in d for d in ditas))
        r, n = _rodar([404] * 10)
        checar(u"404 para sempre: volta em `falhas`, com UM pedido por passada",
               isinstance(r, dict) and 9101 in r and n == 2,
               u"%r, %d pedido(s)" % (r, n))
        fonte = _tw.dedent(_insp.getsource(C.baixar_pesos_ts))
        i0 = fonte.find(u"        segunda = [")
        i1 = fonte.find(u"    finally:", i0)
        recorte = fonte[:i0] + fonte[i1:] if 0 < i0 < i1 else u""
        checar(u"  (isca) recortei a segunda passada do fonte", bool(recorte))
        if recorte:
            ns = dict(C.__dict__)
            exec(compile(recorte, "<sem_segunda_passada>", "exec"), ns)
            r_i, n_i = _rodar([404], fn=ns["baixar_pesos_ts"])
            checar(u"  (isca) sem a segunda passada, o 404 passageiro vira "
                   u"falha -- e a base iria para a reserva",
                   isinstance(r_i, dict) and 9101 in r_i and n_i == 1,
                   u"%r, %d pedido(s)" % (r_i, n_i))
    finally:
        C.log, C.time, C.tabela_da_biblioteca = _log, _time, _tab
        S.fechar()
        shutil.rmtree(base, ignore_errors=True)


def teste_a_divergencia_nao_chega_a_reserva():
    secao(u"a divergencia da origem PARA a etapa 4, e nao chega a reserva")
    import pathlib as _pl
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    C = _modulo_do_motor()
    base = tempfile.mkdtemp(prefix="radai_prep_diverge_")
    ctx = {"bundle": _pl.Path(base) / "bundle", "py": "py-dublado",
           "cache": _pl.Path(base) / "cache", "destino": _pl.Path(base),
           "preparo": base}
    chamou = []
    _v = (C.baixar_pesos_ts, C.garantir_base, C.log, C.titulo)
    try:
        C.log = lambda *a, **kw: None
        C.titulo = lambda *a, **kw: None

        def _garantir(alvo, *a, **kw):
            chamou.append(tuple(alvo))
            return tuple(alvo)
        C.garantir_base = _garantir

        def _diverge(*a, **kw):
            raise C.DivergeDaOrigem(u"CONFERENCIA FALHOU (Dataset831): fantoma")
        C.baixar_pesos_ts = _diverge
        try:
            C.etapa_pesos(ctx)
            desfecho = u"voltou sem levantar"
        except C.DivergeDaOrigem:
            desfecho = u"DivergeDaOrigem"
        except Exception as e:
            desfecho = u"%s: %s" % (type(e).__name__, str(e)[:80])
        checar(u"a etapa 4 deixa `DivergeDaOrigem` subir",
               desfecho == u"DivergeDaOrigem", desfecho)
        checar(u"  e `garantir_base` (a reserva) NAO foi chamada", not chamou,
               chamou)
        C.baixar_pesos_ts = lambda *a, **kw: {831: u"CONFERENCIA FALHOU"}
        try:
            C.etapa_pesos(ctx)
        except Exception:
            pass
        checar(u"  (isca) com a divergencia anotada em `falhas`, a reserva "
               u"SERIA chamada -- o duble enxerga a chamada", bool(chamou),
               chamou)
    finally:
        C.baixar_pesos_ts, C.garantir_base, C.log, C.titulo = _v
        shutil.rmtree(base, ignore_errors=True)


def teste_cada_codigo_do_motor_tem_frase_no_preparador():
    secao(u"cada codigo de saida do motor tem frase (traduzida) no preparador")
    import re as _re
    C = _modulo_do_motor()

    def _todas(cls):
        out = [cls]
        for s in cls.__subclasses__():
            out.extend(_todas(s))
        return out
    classes = _todas(C.SemRede)
    codigos = {}
    for c in classes:
        codigos.setdefault(int(c.codigo), []).append(c.__name__)
    checar(u"cada classe de rede tem um codigo SO' dela",
           all(len(v) == 1 for v in codigos.values()), codigos)
    checar(u"  e o relogio nao e' inspecao (classes separadas)",
           not issubclass(C.RelogioErrado, C.InspecaoHTTPS)
           and C.RelogioErrado.codigo != C.InspecaoHTTPS.codigo)
    fs = _funcoes_ps(u"packager/prepare.ps1", [u"Preparar"])
    prep = fs.get(u"Preparar", u"")
    checar(u"a funcao `Preparar` foi recortada pelo parser", bool(prep),
           _motivo_ast(fs))
    if not prep:
        return
    lj = json.load(io.open(os.path.join(RAIZ, "packager", "languages.json"),
                           encoding="utf-8"))
    idiomas = [c for c in lj["codigos"] if c != lj["padrao"]]

    def _frases(prep):
        out = {}
        for m in _re.finditer(r"\$rcMotor\s+-eq\s+(\d+)\)\s*\{\s*\$classe\s*=\s*"
                              r"\(T\s+'((?:[^']|'')*)'\)", prep):
            out[int(m.group(1))] = m.group(2).replace(u"''", u"'")
        return out
    frases = _frases(prep)
    for cod in sorted(codigos):
        f = frases.get(cod)
        checar(u"codigo %d (%s) tem frase na caixa do preparador"
               % (cod, u", ".join(codigos[cod])), bool(f))
        if f:
            tr = lj["frases"].get(f) or {}
            faltam = [i for i in idiomas if not tr.get(i)]
            checar(u"  e ela esta traduzida nos %d idiomas" % len(idiomas),
                   not faltam, faltam)
    checar(u"a frase do relogio (4) fala da DATA e da HORA, e nao do TI",
           u"DATA e a HORA" in frases.get(4, u"")
           and u"certificado raiz" not in frases.get(4, u""),
           frases.get(4, u"")[:80])
    sem4 = _re.sub(r"\}\s*elseif\s*\(\$rcMotor\s+-eq\s+4\)\s*\{[^}]*", u"",
                   prep)
    checar(u"  (isca) sem o ramo do codigo 4, a conferencia acusa",
           4 not in _frases(sem4) and 4 in frases)


def teste_o_passo_4_diz_o_limite_da_conferencia():
    secao(u"o passo 4 do preparador diz o limite da conferencia")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import artefatos as A
    ps1 = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                  encoding="utf-8-sig").read().replace(u"\r\n", u"\n")
    codigo = u"\n".join(l for l in ps1.splitlines()
                        if not l.lstrip().startswith(u"#"))
    i = codigo.find(u"  4. Confere")
    passo4 = codigo[i:codigo.find(u"  5. ", i)] if i >= 0 else u""
    checar(u"a tela 1 tem o passo 4", bool(passo4))

    def coerente(passo4, tabela):
        sem_soma = any(not v.get("sha256") for v in tabela.values())
        return (u"tamanho e CRC" in passo4) == sem_soma \
            and u"SHA-256 de cada arquivo" not in passo4
    checar(u"o passo 4 diz «tamanho e CRC» se, e so se, ha zip sem soma "
           u"na tabela", coerente(passo4, A.PESOS_TS), passo4)
    checar(u"  (isca) a frase velha reprova",
           not coerente(u"  4. Confere o SHA-256 de cada arquivo baixado\n",
                        A.PESOS_TS))
    checar(u"  (isca) com todo zip somado, a frase com o limite reprova",
           not coerente(passo4, {k: dict(v, sha256="0" * 64)
                                 for k, v in A.PESOS_TS.items()}))
    checar(u"o log do passo 4/4 nao promete SHA-256 de cada arquivo",
           u"Cada arquivo baixado tem o SHA-256" not in codigo
           and u"tamanho e CRC nos demais" in codigo)
    checar(u"  e diz o desfecho do modelo de comparacao (fica fora, nao PARA)",
           u"modelo de comparacao que nao confere fica fora" in codigo)
    lj = json.load(io.open(os.path.join(RAIZ, "packager", "languages.json"),
                           encoding="utf-8"))
    bloco = [k for k in lj["frases"] if u"  4. Confere" in k]
    checar(u"o bloco da tela 1 no dicionario e' o NOVO (e so' um)",
           len(bloco) == 1 and u"tamanho e CRC" in bloco[0], len(bloco))

    total = len(A.PESOS_TS)
    com = sum(1 for v in A.PESOS_TS.values() if v.get("sha256"))
    lados = set([com, total - com])
    fontes = {}
    for rel in (os.path.join("build", "artefatos.py"),
                os.path.join("packager", "prepare.ps1"),
                os.path.join("tools", "test_packager.py")):
        fontes[rel] = io.open(os.path.join(RAIZ, rel),
                              encoding="utf-8-sig").read()
    erradas = _contagens_erradas(fontes, total, lados)
    checar(u"toda contagem «N dos M» dos zips diz M = %d (a tabela) e N em "
           u"%s" % (total, sorted(lados)), not erradas, str(erradas[:4]))
    isca = dict(fontes)
    isca["isca"] = u"# calcula-lo: 13 dos " + u"38 tem (a tabela antiga)\n"
    checar(u"  (isca) a contagem da tabela antiga (38) numa copia do texto "
           u"e acusada",
           any(e[0] == "isca" for e in
               _contagens_erradas(isca, total, lados)))
    isca = {"isca": u"# eram 25 dos 38 ate a liver_segments_mr\n"}
    checar(u"  e o que vem depois de «eram» e registro, e passa",
           not _contagens_erradas(isca, total, lados))


_RE_CONTAGEM = re.compile(
    r"(\d+)\s+dos\s+(\d+)\s+(?:zips|tem)"
    r"|qualquer um dos\s*(?:#\s*>?\s*)?(\d+)")


def _contagens_erradas(fontes, total, lados):
    fora = []
    for rel, txt in sorted(fontes.items()):
        for m in _RE_CONTAGEM.finditer(txt or u""):
            antes = txt[max(0, m.start() - 12):m.start()]
            if u"eram" in antes:
                continue
            if m.group(3):
                ok = int(m.group(3)) == total
            else:
                ok = (int(m.group(2)) == total
                      and int(m.group(1)) in lados)
            if not ok:
                fora.append((rel, txt.count(u"\n", 0, m.start()) + 1,
                             m.group(0)))
    return fora


def teste_certificado_recusado():
    secao(u"certificado recusado: a rede inspeciona HTTPS, e o que fazer")
    import ssl
    import types as _types
    import urllib.error
    C = _modulo_do_motor()
    _ret = C.urllib.request.urlretrieve
    _time, _log = C.time, C.log
    ditas = []
    base = tempfile.mkdtemp(prefix="radai_prep_cert_")
    S = _Servidor(base)
    try:
        C.time = _types.SimpleNamespace(time=time.time, sleep=lambda s: None)
        C.log = lambda m="": ditas.append(u"%s" % m)
        n = {"c": 0}

        def _com(erro):
            def _falso(url, alvo, reporthook=None):
                n["c"] += 1
                raise erro
            return _falso
        cert = urllib.error.URLError(ssl.SSLCertVerificationError(
            1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
               "unable to get local issuer certificate (_ssl.c:1007)"))
        checar(u"certificado recusado NAO e' classificado como «sem rede»",
               C.falha_de_rede(cert) is False
               and C.falha_de_certificado(cert) == "inspecao")
        curto = urllib.error.ContentTooShortError(
            "retrieval incomplete: got only 10 out of 99 bytes", None)
        checar(u"a conexao que fecha no meio do arquivo e' REDE (tenta de novo)",
               C.falha_de_rede(curto) is True
               and C.falha_de_certificado(curto) is None)
        C.urllib.request.urlretrieve = _com(cert)
        alvo = os.path.join(base, "a.bin.parcial")
        try:
            C._transferir("https://exemplo.test/a.zip", alvo, None, None)
            checar(u"sem recuo, o certificado recusado PARA", False, u"passou")
        except C.InspecaoHTTPS as e:
            t = u"%s" % e
            checar(u"sem recuo, o certificado recusado PARA com `InspecaoHTTPS`",
                   True)
            checar(u"  e com o codigo 3 e o cabecalho da classe",
                   e.codigo == 3 and u"INSPECIONA HTTPS" in e.cabecalho)
            checar(u"  e a frase diz «a rede desta maquina inspeciona HTTPS»",
                   u"a rede desta maquina inspeciona HTTPS" in t, t[:120])
            checar(u"  e diz o que fazer (TI, certificado raiz, modo 3)",
                   u"O que fazer" in t and u"certificado raiz" in t
                   and u"modo 3" in t, t[-300:])
            checar(u"  e nomeia o host, e nao a biblioteca",
                   u"exemplo.test" in t)
        checar(u"  e NAO tentou de novo pelo mesmo caminho (1 chamada)",
               n["c"] == 1, u"%d chamadas" % n["c"])
        checar(u"  e o `.parcial` nao sobrou", not os.path.exists(alvo))

        io.open(os.path.join(base, "arquivo.bin"), "wb").write(b"z" * 3000)
        n["c"] = 0
        ok_recuo = True
        try:
            C._transferir(S.base + "/arquivo.bin", alvo, None,
                          py_recuo=sys.executable)
        except Exception as e:
            ok_recuo = u"%s: %s" % (type(e).__name__, str(e)[:160])
        checar(u"com o Python do pacote, o RECUO pelo truststore baixa "
               u"(processo proprio)",
               ok_recuo is True and os.path.isfile(alvo)
               and os.path.getsize(alvo) == 3000, ok_recuo)
        checar(u"  e o log diz que foi pelo truststore",
               any(u"truststore" in d for d in ditas))
        try:
            os.remove(alvo)
        except OSError:
            pass
        _rec = None
        try:
            C._transferir("https://exemplo.test/a.zip", alvo, None,
                          py_recuo=os.path.join(base, "nao_existe.exe"))
        except C.InspecaoHTTPS as e:
            _rec = e
        checar(u"(isca) recuo sem Python: PARA dizendo por que",
               _rec is not None and u"Python do pacote" in u"%s" % _rec,
               (u"%s" % _rec)[:200] if _rec is not None else u"nao levantou")

        C.urllib.request.urlretrieve = _com(urllib.error.URLError(
            ssl.SSLCertVerificationError(
                1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify "
                   "failed: certificate has expired (_ssl.c:1007)")))
        n["c"] = 0
        ditas[:] = []
        try:
            C._transferir("https://exemplo.test/a.zip", alvo, None,
                          py_recuo=sys.executable)
            _rel = None
        except C.SemRede as e:
            _rel = e
        checar(u"certificado VENCIDO levanta `RelogioErrado`, e NAO "
               u"`InspecaoHTTPS`",
               isinstance(_rel, C.RelogioErrado)
               and not isinstance(_rel, C.InspecaoHTTPS), repr(_rel)[:120])
        checar(u"  e com o codigo 4 e o cabecalho que manda conferir a DATA",
               getattr(_rel, "codigo", None) == 4
               and u"DATA E A HORA" in getattr(_rel, "cabecalho", u""),
               (getattr(_rel, "codigo", None), getattr(_rel, "cabecalho", u"")))
        checar(u"  e a mensagem manda olhar a DATA e a HORA",
               u"DATA e a HORA" in u"%s" % _rel, (u"%s" % _rel)[:160])
        checar(u"  e nao gasta o recuo pelo truststore (o relogio o derrubaria "
               u"igual): 1 chamada", n["c"] == 1
               and not any(u"tento de novo pelo truststore" in d
                           for d in ditas), n["c"])

        n["c"] = 0
        C.urllib.request.urlretrieve = _com(Exception(
            "<urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred "
            "in violation of protocol (_ssl.c:1010)>"))
        _eof = None
        try:
            C._transferir("https://exemplo.test/a.zip", alvo, None, None)
        except C.SemRede as e:
            _eof = e
        t = u"%s" % _eof if _eof is not None else u""
        checar(u"o EOF que persiste vira `SemRede` (e nao inspecao)",
               _eof is not None and not isinstance(_eof, C.InspecaoHTTPS)
               and n["c"] == 3,
               u"%s, %d chamadas" % (type(_eof).__name__ if _eof is not None
                                     else u"nao levantou", n["c"]))
        checar(u"  e diz as DUAS leituras: sem internet, ou rede que "
               u"inspeciona HTTPS",
               _eof is not None and u"SEM INTERNET" in t
               and u"inspeciona HTTPS" in t, t[:200] or u"nao levantou")

        trab = os.path.join(base, "trab")
        os.makedirs(trab)
        io.open(os.path.join(trab, "LICENCAS_ACEITAS.txt"), "w").write(u"x\n")

        def _etapa(ctx):
            raise C.InspecaoHTTPS(u"detalhe fantoma")
        _v = (sys.argv, C.ETAPAS, C._exigir_aceite_completo, C.LOG)
        ditas[:] = []
        try:
            sys.argv = ["configurar_ambiente.py", "--preparo", trab]
            C.ETAPAS = [("pesos", _etapa)]
            C._exigir_aceite_completo = lambda p: None
            rc = C.main()
        finally:
            try:
                C.LOG.close()
            except Exception:
                pass
            sys.argv, C.ETAPAS, C._exigir_aceite_completo, C.LOG = _v
        checar(u"o motor devolve 3 para a inspecao de HTTPS", rc == 3, rc)
        checar(u"  e o bloco diz A REDE DESTA MAQUINA INSPECIONA HTTPS (e nao "
               u"«SEM CONEXAO»)",
               any(u"A REDE DESTA MAQUINA INSPECIONA HTTPS" in d for d in ditas)
               and not any(u"SEM CONEXAO" in d for d in ditas))
        cab_inspecao = list(ditas)

        def _etapa_relogio(ctx):
            raise C.RelogioErrado(u"detalhe fantoma do relogio")
        ditas[:] = []
        try:
            sys.argv = ["configurar_ambiente.py", "--preparo", trab]
            C.ETAPAS = [("pesos", _etapa_relogio)]
            C._exigir_aceite_completo = lambda p: None
            rc4 = C.main()
        finally:
            try:
                C.LOG.close()
            except Exception:
                pass
            sys.argv, C.ETAPAS, C._exigir_aceite_completo, C.LOG = _v
        checar(u"o motor devolve 4 para o certificado fora da validade",
               rc4 == 4, rc4)
        checar(u"  e o bloco manda conferir a DATA E A HORA, e NAO diz "
               u"«INSPECIONA HTTPS»",
               any(u"CONFIRA A DATA E A HORA" in d for d in ditas)
               and not any(u"INSPECIONA HTTPS" in d for d in ditas),
               [d for d in ditas if u"(1 - pesos)" in d][:1])
        checar(u"  (isca) o bloco da inspecao reprova nessa checagem",
               not any(u"CONFIRA A DATA E A HORA" in d for d in cab_inspecao))
        ditas[:] = cab_inspecao
        cab = u"\n".join(ditas)
        checar(u"no --preparo o cabecalho NAO cita a raiz de entrega nem "
               u"empacotar_instalador",
               u"AI_DEPLOY" not in cab and u"empacotar_instalador" not in cab,
               [d for d in ditas if u"DEPLOY" in d or u"empacotar" in d][:2])
        checar(u"  e diz o que o pacote e', em texto de campo",
               u"CARGA" in cab and u"pasta de passagem" in cab)
        oficina_dev = u"\n".join(C.linhas_do_cabecalho(False, u"<oficina>"))
        checar(u"  (isca) fora do --preparo, a frase da oficina continua",
               u"empacotar_instalador" in oficina_dev, oficina_dev[:160])
    finally:
        C.urllib.request.urlretrieve = _ret
        C.time, C.log = _time, _log
        S.fechar()
        shutil.rmtree(base, ignore_errors=True)


def teste_sonda_do_pip_calada():
    secao(u"a sonda do pip e' calada, e a frase e' de campo")
    C = _modulo_do_motor()
    ditas = []
    _log = C.log
    try:
        C.log = lambda m="": ditas.append(u"%s" % m)
        ok, qual = C.pip_responde(sys.executable)
        checar(u"com pip, a sonda responde a versao",
               ok and qual.lower().startswith(u"pip "), qual)
        ok2, qual2 = C.pip_responde(os.path.join(tempfile.gettempdir(),
                                                 "nao_existe_python.exe"))
        checar(u"sem Python, a sonda diz nao -- e nao levanta", ok2 is False,
               qual2)
        checar(u"  e a SONDA nao escreveu nada no log", not ditas, ditas[:2])

        class _Parar(Exception):
            pass
        _v = (C.pip_responde, C.baixar, C.titulo)
        try:
            C.pip_responde = lambda py: (False, u"No module named pip")

            def _b(*a, **kw):
                raise _Parar()
            C.baixar = _b
            C.titulo = lambda *a, **kw: None
            try:
                C.etapa_pip({"py": "py-dublado",
                             "cache": __import__("pathlib").Path(tempfile.gettempdir())})
            except _Parar:
                pass
        finally:
            C.pip_responde, C.baixar, C.titulo = _v
        texto = u"\n".join(ditas)
        checar(u"a etapa diz «normal na primeira vez», e nao FALHOU",
               u"normal na primeira vez" in texto and u"FALHOU" not in texto,
               texto[:200])
    finally:
        C.log = _log
    import ast as _ast
    arv = _ast.parse(ler("build/configurar_ambiente.py"))
    etapa = next(n for n in _ast.walk(arv)
                 if isinstance(n, _ast.FunctionDef) and n.name == "etapa_pip")
    primeira = None
    for no in _ast.walk(etapa):
        if isinstance(no, _ast.Call) and getattr(no.func, "id", "") in (
                "rodar", "pip_responde"):
            if primeira is None or no.lineno < primeira.lineno:
                primeira = no
    checar(u"a PRIMEIRA pergunta ao pip da etapa e' a sonda calada",
           primeira is not None and primeira.func.id == "pip_responde",
           getattr(getattr(primeira, "func", None), "id", None))


def _lancadores_mortos(bundle):
    fora = []
    for rel in ("launchers/start_engine.cmd", "iniciar_motor.cmd",
                "ferramentas/iniciar_motor.cmd"):
        if os.path.exists(os.path.join(bundle, *rel.split("/"))):
            fora.append(rel)
    return fora


def teste_o_lancador_do_motor_http_saiu():
    secao(u"o lancador do motor HTTP saiu do pacote")
    C = _modulo_do_motor()
    b = tempfile.mkdtemp(prefix="radai_prep_app_")
    _v = (C.log, C.titulo)
    try:
        C.log = lambda *a, **kw: None
        C.titulo = lambda *a, **kw: None
        from pathlib import Path as _P
        C.etapa_app({"bundle": _P(b), "versao": u"9.9"})
        lanc = sorted(os.listdir(os.path.join(b, "launchers")))
        checar(u"a etapa 5 roda e grava os lancadores",
               u"start_watcher.cmd" in lanc and u"open_browser.cmd" in lanc,
               lanc)
        checar(u"  e NAO grava o start_engine.cmd", not _lancadores_mortos(b),
               _lancadores_mortos(b))
        checar(u"  e o texto dele saiu do motor",
               not hasattr(C, "INICIAR_MOTOR"))
        import radai_porta as _rp
        faltam = [n for n in sorted(_rp.ARQUIVOS)
                  if not os.path.isfile(os.path.join(b, _rp.PASTA, n))
                  or open(os.path.join(b, _rp.PASTA, n), "rb").read()
                  != open(os.path.join(RAIZ, "app", _rp.PASTA, n), "rb").read()]
        checar(u"a etapa 5 leva a porta (porta.js, a fonte e a imagem), byte a byte",
               not faltam, faltam)
        etapa = io.open(os.path.join(RAIZ, "build", "configurar_ambiente.py"),
                        encoding="utf-8").read()
        etapa = etapa[etapa.index(u"def etapa_app("):]
        etapa = etapa[:etapa.index(u"\ndef ")]
        linha = u"shutil.copy2(str(origem), str(alvo_porta / nome))"

        def _copia_ativa(texto):
            return any(l.strip().startswith(linha) for l in texto.split(u"\n"))
        checar(u"  pela lista do servidor (radai_porta.ARQUIVOS)",
               _copia_ativa(etapa) and u"_rp.ARQUIVOS" in etapa)
        checar(u"  (isca) a linha de copia comentada reprova",
               not _copia_ativa(etapa.replace(linha, u"# " + linha)))
        io.open(os.path.join(b, "launchers", "start_engine.cmd"), "w").write(u"x")
        checar(u"  (isca) um start_engine.cmd no pacote e' acusado",
               _lancadores_mortos(b) == [u"launchers/start_engine.cmd"])
    finally:
        C.log, C.titulo = _v
        shutil.rmtree(b, ignore_errors=True)


def teste_tabela_da_biblioteca_real():
    secao(u"a tabela de pesos da biblioteca do pacote (real)")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    C = _modulo_do_motor()
    import artefatos as A
    import radai_tasks as K
    py = u""
    try:
        _b = io.open(os.path.join(RAIZ, "_bundle.txt"),
                     encoding="utf-8-sig").read().strip()
        if _b and os.path.isfile(os.path.join(_b, "python", "python.exe")):
            py = os.path.join(_b, "python", "python.exe")
    except Exception:
        pass
    if not py:
        checar(u"PULADO: nao ha pacote montado nesta maquina (_bundle.txt)",
               True, u"a tabela real nao foi conferida")
        return
    try:
        tab = C.tabela_da_biblioteca(
            py, [K.nome_na_biblioteca(t) for t in C.TASKS],
            K.datasets_do_pacote(list(C.TASKS)))
    except Exception as e:
        checar(u"a tabela da biblioteca foi lida", False,
               u"%s: %s" % (type(e).__name__, str(e)[:200]))
        return
    checar(u"a tabela da biblioteca foi lida (TotalSegmentator %s, %d zips)"
           % (tab["versao_ts"], len(tab["itens"])), bool(tab["itens"]))
    checar(u"a URL base e' a do autor no GitHub",
           tab["base"] == u"https://github.com/wasserth/TotalSegmentator/"
                          u"releases/download", tab["base"])
    ruins = [i["url"] for i in tab["itens"]
             if not i["url"].startswith(tab["base"] + u"/v")
             or not i["url"].endswith(u"/" + i["pasta"] + u".zip")]
    checar(u"toda URL e' `<base>/<versao>/<pasta>.zip`, a conta da biblioteca",
           not ruins, ruins[:2])
    fora = [i["zip"] for i in tab["itens"] if i["zip"] not in A.PESOS_TS]
    checar(u"TODO zip que a versao pinada baixa esta em artefatos.PESOS_TS",
           not fora, fora[:4])
    def _outra_release(tabela):
        return [(i["zip"], tabela[i["zip"]].get("release"))
                for i in tab["itens"] if i["zip"] in tabela
                and (u"/%s/" % tabela[i["zip"]].get("release")) not in i["url"]]
    outra = _outra_release(A.PESOS_TS)
    checar(u"  e na MESMA release que a biblioteca pede", not outra, outra[:3])
    _isca = dict(A.PESOS_TS)
    _z0 = tab["itens"][0]["zip"]
    _isca[_z0] = dict(_isca[_z0], release="v0.0.0-isca")
    checar(u"  (isca) uma entrada com outra release reprova",
           bool(_outra_release(_isca)))
    ids = set(i["id"] for i in tab["itens"])
    checar(u"  e a lista cobre os localizadores de recorte",
           set(K.datasets_do_pacote(list(C.TASKS))) <= ids,
           sorted(set(K.datasets_do_pacote(list(C.TASKS))) - ids))
    checar(u"  e traz a lista de pesos velhos que a biblioteca limpa",
           isinstance(tab["velhos"], list) and len(tab["velhos"]) > 0)
    try:
        C.tabela_da_biblioteca(py, [u"total_v2"])
        checar(u"(isca) task que a biblioteca nao conhece e' RECUSADA", False)
    except RuntimeError as e:
        checar(u"(isca) task que a biblioteca nao conhece e' RECUSADA",
               u"nao conhece" in u"%s" % e, (u"%s" % e)[:120])


def teste_o_recuo_pelo_truststore_respeita_o_prazo():
    secao(u"o recuo pelo truststore respeita o prazo")
    import inspect as _insp
    import socket as _so
    import threading as _th
    C = _modulo_do_motor()
    try:
        from pip._vendor import truststore as _ts
    except Exception as e:
        checar(u"(o Python desta bateria tem o truststore do pip)", False,
               u"%s" % e)
        return
    ditas = []
    C.log = lambda m="": ditas.append(u"%s" % m)
    srv = _so.socket(_so.AF_INET, _so.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    porta = srv.getsockname()[1]
    abertas = []
    parar = _th.Event()

    def _aceitar():
        srv.settimeout(0.5)
        while not parar.is_set():
            try:
                c, _a = srv.accept()
                abertas.append(c)
            except Exception:
                continue
    _th.Thread(target=_aceitar, daemon=True).start()
    base = tempfile.mkdtemp(prefix="radai_prep_truststore_")
    url = "http://127.0.0.1:%d/x.zip" % porta
    try:
        t0 = time.time()
        ok, texto = C.baixar_pelo_truststore(
            sys.executable, url, os.path.join(base, "a.zip"), timeout=3)
        dt = time.time() - t0
        checar(u"com a conexao muda, o recuo VOLTA no prazo (timeout=3), e "
               u"diz que passou do tempo", not ok and dt < 20
               and u"passou do tempo" in texto, u"%.1f s | %s" % (dt, texto))
        checar(u"  e nao deixa arquivo pela metade",
               not os.path.exists(os.path.join(base, "a.zip")))
        alvo = u"socket.setdefaulttimeout(%d)" % C.PRAZO_SEM_DADO_S
        checar(u"o filho tem prazo de socket (`PRAZO_SEM_DADO_S`)",
               alvo in C._SCRIPT_TRUSTSTORE, C._SCRIPT_TRUSTSTORE[:120])
        velho = C._SCRIPT_TRUSTSTORE
        try:
            C._SCRIPT_TRUSTSTORE = velho.replace(
                alvo, u"socket.setdefaulttimeout(2)")
            t0 = time.time()
            ok2, texto2 = C.baixar_pelo_truststore(
                sys.executable, url, os.path.join(base, "b.zip"), timeout=60)
            dt2 = time.time() - t0
        finally:
            C._SCRIPT_TRUSTSTORE = velho
        checar(u"  e com ele o filho desiste SOZINHO, sem esperar o prazo do "
               u"pai (60 s)", not ok2 and dt2 < 30
               and u"passou do tempo" not in texto2,
               u"%.1f s | %s" % (dt2, texto2[:160]))
        src = _insp.getsource(C.baixar_pelo_truststore)
        checar(u"  (isca) a leitura em thread esta onde a isca a procura",
               src.count(u"    leitor.start()\n") == 1)
        ns = dict(vars(C))
        exec(compile(src.replace(u"    leitor.start()\n", u"    _ler()\n"),
                     "<isca-truststore>", "exec"), ns)
        voltou = []

        def _rodar_isca():
            try:
                voltou.append(ns["baixar_pelo_truststore"](
                    sys.executable, url, os.path.join(base, "c.zip"),
                    timeout=3))
            except Exception as e:
                voltou.append(e)
        _th.Thread(target=_rodar_isca, daemon=True).start()
        time.sleep(10)
        checar(u"ISCA: lendo a saida antes de esperar, a funcao NAO volta no "
               u"prazo (o defeito da revisao, reproduzido)", not voltou,
               str(voltou)[:120])
        def _gotejo(fn, nome, prazo=6):
            sv = _so.socket(_so.AF_INET, _so.SOCK_STREAM)
            sv.bind(("127.0.0.1", 0))
            sv.listen(4)
            fim = _th.Event()
            caiu = []

            def _servir(c):
                try:
                    c.recv(4096)
                    c.sendall(b"HTTP/1.0 200 OK\r\n"
                              b"Content-Length: 1000000\r\n\r\n")
                    while not fim.is_set():
                        c.sendall(b"x" * 2000)
                        time.sleep(0.3)
                except Exception:
                    caiu.append(time.time())
                finally:
                    try:
                        c.close()
                    except Exception:
                        pass

            def _aceitar_g():
                sv.settimeout(0.5)
                while not fim.is_set():
                    try:
                        c, _a = sv.accept()
                    except Exception:
                        continue
                    _th.Thread(target=_servir, args=(c,), daemon=True).start()
            _th.Thread(target=_aceitar_g, daemon=True).start()
            dest = os.path.join(base, nome)
            viu = []
            rodando = _th.Event()
            rodando.set()

            def _espiar():
                while rodando.is_set():
                    if os.path.exists(dest):
                        viu.append(True)
                        return
                    time.sleep(0.1)
            _th.Thread(target=_espiar, daemon=True).start()
            try:
                ok_g, texto_g = fn(sys.executable, "http://127.0.0.1:%d/g.zip"
                                   % sv.getsockname()[1], dest, timeout=prazo)
                volta = time.time()
                rodando.clear()
                depois = os.path.exists(dest)
                time.sleep(4)
                queda = [t - volta for t in caiu]
            finally:
                fim.set()
                time.sleep(1)
                try:
                    sv.close()
                except Exception:
                    pass
                try:
                    os.remove(dest)
                except OSError:
                    pass
            return (ok_g, texto_g, bool(viu), depois,
                    (min(queda) if queda else None))
        ditas[:] = []
        ok3, tx3, antes3, depois3, queda3 = _gotejo(C.baixar_pelo_truststore,
                                                    "d.zip")
        checar(u"lento mas vivo: o arquivo EXISTIA durante o download e NAO "
               u"existe depois do prazo", not ok3 and antes3 and not depois3,
               u"antes=%s depois=%s | %s" % (antes3, depois3, tx3[:120]))
        checar(u"  e o filho MORREU no prazo: o servidor ve a conexao cair "
               u"logo depois do retorno", queda3 is not None and queda3 < 3.5,
               str(queda3))
        checar(u"  e a frase diz a rede lenta (com o progresso), e nao «sem "
               u"trazer nada»", u"lenta demais" in tx3
               and u"sem trazer nada" not in tx3 and u"%" in tx3, tx3[:160])
        checar(u"  (pre-condicao) o log mostrou o progresso do truststore",
               any(u"(truststore)" in d and d.strip().endswith(u"%")
                   for d in ditas), str(ditas[-3:]))
        src3 = _insp.getsource(C.baixar_pelo_truststore)
        for de, para, rotulo, falhou in (
                (u"            proc.kill()\n", u"            pass\n",
                 u"sem o `kill`, o filho segue vivo depois do prazo",
                 lambda r: r[4] is None),
                (u"            os.remove(str(destino))\n",
                 u"            pass\n",
                 u"sem o `os.remove`, o `.parcial` pela metade sobra",
                 lambda r: r[3]),
                (u"        if _progresso:\n", u"        if False:\n",
                 u"com a frase unica, o download lento vira «sem trazer "
                 u"nada»", lambda r: u"sem trazer nada" in r[1])):
            ns3 = dict(vars(C))
            exec(compile(src3.replace(de, para, 1), "<isca-gotejo>", "exec"),
                 ns3)
            r = _gotejo(ns3["baixar_pelo_truststore"], "e.zip")
            checar(u"ISCA: %s (a checagem sabe reprovar)" % rotulo,
                   de in src3 and falhou(r),
                   u"antes=%s depois=%s queda=%s | %s"
                   % (r[2], r[3], r[4], r[1][:100]))
    finally:
        parar.set()
        for c in abertas:
            try:
                c.close()
            except Exception:
                pass
        try:
            srv.close()
        except Exception:
            pass
        shutil.rmtree(base, ignore_errors=True)


def teste_o_veredito_fora_da_tabela_nao_promete_tamanho():
    secao(u"o veredito fora da tabela nao promete o que nao conferiu")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import artefatos as A
    base = tempfile.mkdtemp(prefix="radai_prep_veredito_")
    try:
        z = os.path.join(base, "Dataset9101_fora.zip")
        _zip_de_peso(z, "Dataset9101_fora")
        tam = os.path.getsize(z)
        checar(u"(o zip de teste esta fora da tabela do projeto)",
               os.path.basename(z) not in A.PESOS_TS)
        ok, msg, _m = A.conferir_peso_ts(z, os.path.basename(z),
                                         "Dataset9101_fora")
        checar(u"sem `anunciado`: passa, e o veredito diz CRC e forma — e NAO "
               u"«tamanho anunciado» conferido aqui",
               ok and u"CRC" in msg and u"conferido pelo tamanho" not in msg
               and u"transferencia" in msg, msg)
        ok2, msg2, _m = A.conferir_peso_ts(z, os.path.basename(z),
                                           "Dataset9101_fora", anunciado=tam)
        checar(u"com `anunciado` certo: passa, e ai sim diz o tamanho",
               ok2 and u"tamanho anunciado" in msg2, msg2)
        ok3, msg3, _m = A.conferir_peso_ts(z, os.path.basename(z),
                                           "Dataset9101_fora",
                                           anunciado=tam + 7)
        checar(u"ISCA: com `anunciado` errado, recusa (a conferencia de "
               u"tamanho so existe quando o numero chega)",
               not ok3 and u"anunciado pelo servidor" in msg3, msg3)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _registro_cobre_o_ensemble(m, arquivos):
    cont = set(r for r, _t in (m.get("conteudo") or ()))
    sha = set(m.get("sha256") or {})
    return cont == set(arquivos) and sha == set(arquivos)


def teste_o_preparo_confere_os_pesos_do_ensemble():
    secao(u"o preparo confere os pesos do ensemble dos niveis cervicais")
    import hashlib
    import pathlib
    import zipfile
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import radai_models as M
    import radai_hnlnl_engine as HM
    import radai_zip_split as ZS
    import requisitos as R
    import configurar_ambiente as C
    m = M.MODELOS["hnlnl"]
    arqs = HM.arquivos_do_ensemble()
    checar(u"o registro confere, por tamanho e sha256, o que o ensemble le "
           u"(nos dois sentidos)", _registro_cobre_o_ensemble(m, arqs),
           str(sorted(set(arqs) ^ set(m.get("sha256") or {}))))
    um = [a for a in arqs if a.startswith("2d/") and "/fold_4/" in a][0]
    checar(u"  ISCA: o registro sem um peso do 2D reprova",
           not _registro_cobre_o_ensemble(
               dict(m, conteudo=[x for x in m["conteudo"] if x[0] != um]),
               arqs))
    hexa = lambda s: len(s or "") == 64 and all(c in "0123456789abcdef"
                                                for c in s)
    checar(u"os dois volumes da origem tem tamanho e sha256",
           all(n in (m.get("sha256_dos_volumes") or {}) and t > 0
               and hexa(m["sha256_dos_volumes"][n]) for n, t in m["volumes"])
           and all(hexa(v) for v in m["sha256"].values()))

    d = tempfile.mkdtemp(prefix="radai_prep_ensemble_")
    velho_dir = os.environ.get("RADAI_MODELOS_DIR")
    velho_log, velho_reg = C.log, M.MODELOS["hnlnl"]
    velho_baixar, velho_juntar = M._baixar_arquivo, ZS.juntar
    try:
        rq = os.path.join(d, "req")
        shutil.copytree(os.path.join(RAIZ, "build"), os.path.join(rq, "build"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(rq, "app"))
        for n in ("radai_tasks.py", "radai_models.py"):
            shutil.copy2(_componentes.fonte("app/" + n), os.path.join(rq, "app"))
        antes = R.calcular(rq)
        p = os.path.join(rq, "app", "radai_models.py")
        t = io.open(p, encoding="utf-8").read()
        alvo = m["sha256"][um]
        io.open(p, "w", encoding="utf-8").write(
            t.replace(alvo, "0" * 64, 1))
        depois = R.calcular(rq)
        checar(u"a soma de um peso do ensemble trocada muda a impressao de "
               u"requisitos, e so a do hnlnl",
               depois[u"impressao"] != antes[u"impressao"]
               and [k for k in antes[u"modelos"]
                    if antes[u"modelos"][k] != depois[u"modelos"][k]]
               == [u"hnlnl"])

        C.log = lambda *a, **k: None
        base = os.path.join(d, "bundle")
        pasta = pathlib.Path(base) / "modelos" / "hnlnl"
        for rel in arqs:
            f = pasta / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(("peso " + rel).encode("utf-8"))
        (pasta / "pesos_extraidos.txt").write_text(u"x", encoding="utf-8")
        falso = dict(m, conteudo=[(r, (pasta / r).stat().st_size)
                                  for r in arqs],
                     sha256=dict((r, hashlib.sha256(
                         (pasta / r).read_bytes()).hexdigest())
                         for r in arqs))
        M.MODELOS["hnlnl"] = falso

        def _confere(reg):
            M.MODELOS["hnlnl"] = reg
            try:
                C.conferir_modelos_exigidos(base, [u"hnlnl"])
                return None
            except C.FaltaModeloExigido as e:
                return str(e)
        checar(u"com os dez pesos e as somas: o preparo passa",
               _confere(falso) is None)
        guardado = (pasta / um).read_bytes()
        (pasta / um).unlink()
        r = _confere(falso)
        checar(u"sem um peso do 2D: o preparo PARA, e diz qual",
               r is not None and u"fold_4" in r, r)
        sem_conferir = dict(m, conteudo=[], sha256={})
        checar(u"  ISCA: so com a marca da extracao (o registro de antes), "
               u"passava", _confere(sem_conferir) is None)
        (pasta / um).write_bytes(guardado[:-1] + b"X")
        r = _confere(falso)
        checar(u"mesmo tamanho e soma diferente: o preparo PARA",
               r is not None and u"fold_4" in r, r)
        (pasta / um).write_bytes(guardado)

        os.environ["RADAI_MODELOS_DIR"] = os.path.join(d, "baixa")
        z = os.path.join(d, "origem.zip")
        with zipfile.ZipFile(z, "w") as zf:
            for rel in arqs:
                zf.writestr(rel, (pasta / rel).read_bytes())
        vols = {"NnunetModelExport.z01": b"disco 0",
                "NnunetModelExport.zip": open(z, "rb").read()}
        registro_baixa = dict(falso, volumes=[(n, len(b)) for n, b in
                                              vols.items()],
                              sha256_dos_volumes=dict(
                                  (n, hashlib.sha256(b).hexdigest())
                                  for n, b in vols.items()))
        pedidos = []

        def _baixar(url, alvo, esperado, ident, rel, progresso=None,
                    sha_esperado=None, md5_esperado=None):
            pedidos.append((rel, sha_esperado))
            pathlib.Path(alvo).write_bytes(vols[rel])

        M._baixar_arquivo = _baixar
        ZS.juntar = lambda v, dest, progresso=None: shutil.copyfile(v[-1],
                                                                    dest)
        M.MODELOS["hnlnl"] = registro_baixa
        r = M._baixar_em_volumes("hnlnl", registro_baixa)
        dest = M.pasta_do_modelo("hnlnl")
        checar(u"o download dos volumes pede a soma da origem de cada um",
               sorted(pedidos) == sorted(registro_baixa["sha256_dos_volumes"]
                                         .items()), str(pedidos))
        checar(u"  e com o conteudo conferido, marca a extracao",
               r.get("ok") and (dest / "pesos_extraidos.txt").is_file()
               and M.estado_do_modelo("hnlnl")["instalado"], str(r))
        (dest / um).unlink()
        checar(u"sem um peso do 2D no disco, o modelo nao esta instalado",
               not M.estado_do_modelo("hnlnl")["instalado"]
               and um in M.estado_do_modelo("hnlnl")["faltando"])
        del pedidos[:]
        M._baixar_em_volumes("hnlnl", registro_baixa)
        checar(u"  e o proximo preparo baixa e extrai de novo (a marca nao "
               u"basta)", len(pedidos) == 2
               and M.estado_do_modelo("hnlnl")["instalado"], str(pedidos))
        (dest / "pesos_extraidos.txt").unlink()
        trocado = dict(registro_baixa, sha256=dict(registro_baixa["sha256"],
                                                   **{um: "0" * 64}))
        M.MODELOS["hnlnl"] = trocado
        erro = None
        try:
            M._baixar_em_volumes("hnlnl", trocado)
        except Exception as e:
            erro = e
        checar(u"o conteudo extraido com soma diferente da origem: o "
               u"download levanta e nao marca a extracao",
               erro is not None and u"sha256" in str(erro)
               and not (dest / "pesos_extraidos.txt").is_file(), repr(erro))
    finally:
        M.MODELOS["hnlnl"] = velho_reg
        C.log = velho_log
        M._baixar_arquivo, ZS.juntar = velho_baixar, velho_juntar
        if velho_dir is None:
            os.environ.pop("RADAI_MODELOS_DIR", None)
        else:
            os.environ["RADAI_MODELOS_DIR"] = velho_dir
        shutil.rmtree(d, ignore_errors=True)


def _cascata_pacote(base, versao):
    p = os.path.join(base, "este_instalador")
    for sub in ("app", "tools", "build", "packager"):
        os.makedirs(os.path.join(p, sub), exist_ok=True)
    io.open(os.path.join(p, "entrega.txt"), "w").write(
        u"PRODUTO=RADIOTERAPIA_AI_LOCAL_SUITE\nPROJETO=LOCAL_SUITE\nVERSAO=%s\n" % versao)
    for n in ("radai_watcher.py", "engine.py"):
        io.open(os.path.join(p, "app", n), "w").write(u"# %s versao %s\n" % (n, versao))
    io.open(os.path.join(p, "tools", "testar_algo.py"), "w").write(u"# v%s\n" % versao)
    for f in ("requisitos.py", "requirements-demo.txt", "configurar_ambiente.py",
              "artefatos.py"):
        shutil.copy2(os.path.join(RAIZ, "build", f), os.path.join(p, "build", f))
    for rel in ("app/radai_tasks.py", "app/radai_models.py"):
        shutil.copy2(_componentes.fonte(rel), os.path.join(p, rel.replace(u"/", os.sep)))
    shutil.copy2(os.path.join(RAIZ, "packager", "UPDATE.ps1"),
                 os.path.join(p, "packager", "UPDATE.ps1"))
    for n in ("NOTICE", "LICENSE"):
        io.open(os.path.join(p, n), "w", encoding="utf-8").write(u"%s %s\n" % (n, versao))
    return p


def _cascata_instalacao(unidade, nome, versao, impressao, porta, igual=True):
    import requisitos as R
    raiz = os.path.join(unidade, "RADIOTERAPIA_AI")
    inst = os.path.join(raiz, nome)
    for sub in ("tools", "python", "calibracao"):
        os.makedirs(os.path.join(inst, sub), exist_ok=True)
    for n in ("radai_watcher.py", "engine.py"):
        io.open(os.path.join(inst, n), "w").write(u"# %s ANTIGO\n" % n)
    io.open(os.path.join(inst, "entrega.txt"), "w").write(
        u"PROJETO=LOCAL_SUITE\nVERSAO=%s\n" % versao)
    io.open(os.path.join(inst, "radai_watcher.config"), "w").write(
        u"PORT=%d\nROOT=C:\\nao_toque\n" % porta)
    io.open(os.path.join(inst, "python", "python.exe"), "wb").write(b"MZ\0")
    d = R.calcular(impressao)
    if not igual:
        d["impressao"] = u"0" * 64
        d["versoes"] = dict(d.get("versoes") or {}, torch=u"0.0.1+isca")
    d["versao"] = versao
    io.open(os.path.join(inst, "_requisitos.json"), "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False))
    reg = os.path.join(raiz, "_instalados.json")
    atual = {}
    if os.path.isfile(reg):
        atual = json.load(io.open(reg, encoding="utf-8"))
    atual[nome] = {"versao": versao, "caminho": inst}
    io.open(reg, "w", encoding="utf-8").write(json.dumps(atual))
    return inst


def _zip_do_instalador(destino, versao, fuga=False):
    import zipfile as _zf
    prep = (u"$m = Join-Path (Split-Path -Parent (Split-Path -Parent "
            u"$MyInvocation.MyCommand.Path)) 'marca.txt'\r\n"
            u"[System.IO.File]::WriteAllText($m, ([string]$env:RADAI_ATUALIZAR_APP) + '|' + "
            u"([string]$env:RADAI_ATUALIZAR_APP_DE))\r\n"
            u"exit 7\r\n")
    with _zf.ZipFile(destino, "w", _zf.ZIP_DEFLATED) as z:
        z.writestr("LOCAL_SUITE_SETUP/entrega.txt",
                   u"PRODUTO=RADIOTERAPIA_AI_LOCAL_SUITE\r\nPROJETO=LOCAL_SUITE\r\n"
                   u"VERSAO=%s\r\n" % versao)
        z.writestr("LOCAL_SUITE_SETUP/packager/prepare.ps1",
                   (u"\ufeff" + prep).encode("utf-8"))
        if fuga:
            z.writestr("../fora_da_extracao.txt", u"fugiu")
    return io.open(destino, "rb").read()


_FUNCOES_DA_CASCATA = [
    u"AtualizarApp", u"IniciarAtualizarApp", u"UltimoDaSaida", u"CampoDaEntregaEm",
    u"MesmaVersao", u"HaRede", u"ExtrairInstaladorNovo", u"AcharPreparadorEm",
    u"BaixarInstaladorNovo", u"ContinuarPeloInstaladorNovo", u"VersaoPublicada",
    u"InstaladorDaRelease", u"NomeDoInstaladorLatest", u"LinkDoInstalador",
    u"RespondeuHttp", u"LigarTls12", u"EsperarSemTravar", u"BaixarSemTravar",
    u"ComoNumero", u"MaisNovaQue", u"VersaoDaPasta", u"ConfirmarSeRetrocede",
    u"PerguntaDoRetrocesso", u"AtualizarDePacote", u"ValorDaEntrega",
    u"UrlDaConsultaDeVersao"]


def _pslit(s):
    return u"'" + str(s).replace(u"'", u"''") + u"'"


def teste_atualizar_app_e_uma_cascata():
    secao(u"«Atualizar app» e' uma cascata: release, impressao, rede, pacote")
    import hashlib
    import http.server as _hs
    import threading as _th
    import socket as _so

    fs = _funcoes_ps(u"packager/prepare.ps1", _FUNCOES_DA_CASCATA)
    faltam = [n for n in _FUNCOES_DA_CASCATA if n not in fs]
    checar(u"as funcoes da cascata existem e foram recortadas pelo parser",
           not faltam, u"faltam %s%s" % (faltam, _motivo_ast(fs)))
    if faltam:
        return

    base = tempfile.mkdtemp(prefix="radai_prep_cascata_")
    srv = None
    try:
        temp = os.path.join(base, "temp")
        ad = os.path.join(base, "ad")
        for d in (temp, ad):
            os.makedirs(d)
        zips = {}
        bom = _zip_do_instalador(os.path.join(base, "bom.zip"), u"99.0")
        zips[u"bom"] = bom
        zips[u"mentira"] = _zip_do_instalador(os.path.join(base, "mentira.zip"), u"98.0")
        zips[u"fuga"] = _zip_do_instalador(os.path.join(base, "fuga.zip"), u"99.0", fuga=True)
        nome = u"RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_LATEST.zip"

        class _H(_hs.BaseHTTPRequestHandler):
            def _manda(self, codigo, corpo, tipo="application/json"):
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_GET(self):
                porta = self.server.server_address[1]
                partes = self.path.strip("/").split("/")
                if partes[0] == "zip" and len(partes) == 2 and partes[1] in zips:
                    return self._manda(200, zips[partes[1]], "application/zip")
                if partes[0] == "rede":
                    return self._manda(200, b"ok", "text/plain")
                if partes[0] == "sem_release":
                    return self._manda(404, b"{}")
                casos = {
                    u"novo": (u"v99.0", u"bom", 0, None),
                    u"tamanho": (u"v99.0", u"bom", 1, None),
                    u"soma": (u"v99.0", u"bom", 0, u"0" * 64),
                    u"mentira": (u"v99.0", u"mentira", 0, None),
                    u"fuga": (u"v99.0", u"fuga", 0, None),
                    u"velho": (u"v0.1", u"bom", 0, None),
                }
                if partes[0] not in casos:
                    return self._manda(404, b"{}")
                tag, z, mais, soma = casos[partes[0]]
                corpo = zips[z]
                rel = {"tag_name": tag, "assets": [
                    {"name": u"OUTRO_SETUP.zip", "size": 1,
                     "browser_download_url": u"http://127.0.0.1:%d/nada" % porta},
                    {"name": nome, "size": len(corpo) + mais,
                     "digest": u"sha256:" + (soma or hashlib.sha256(corpo).hexdigest()),
                     "browser_download_url": u"http://127.0.0.1:%d/zip/%s" % (porta, z)}]}
                return self._manda(200, json.dumps(rel).encode("utf-8"))

            def log_message(self, *a):
                pass

        srv = _hs.ThreadingHTTPServer(("127.0.0.1", 0), _H)
        _th.Thread(target=srv.serve_forever, daemon=True).start()
        url = u"http://127.0.0.1:%d" % srv.server_address[1]

        s = _so.socket()
        s.bind(("127.0.0.1", 0))
        porta_app = s.getsockname()[1]
        s.close()
        pac = _cascata_pacote(base, u"8.5")
        disco = os.path.join(base, "D_")
        insts = {}
        for cena, igual in ((u"A", True), (u"B", True), (u"C", True), (u"D", True),
                            (u"E", True), (u"F", True), (u"G", False), (u"H", False),
                            (u"I", False), (u"J", False), (u"K", False),
                            (u"IA", True), (u"IB", True), (u"IC", False), (u"ID", False)):
            insts[cena] = _cascata_instalacao(disco, u"LS_" + cena, u"8.4", pac,
                                              porta_app, igual=igual)
        morta = u"http://127.0.0.1:9/x"

        def cena(nome_cena, inst, release, redes, veio=u""):
            return (u"$script:VersaoLa = $null; $script:Log = @(); $script:Atualizador = 0\n"
                    u"$script:Marcou = ''; $script:Avisos = @(); $script:Fechou = 0\n"
                    u"$script:Concluiu = ''\n"
                    u"$script:CascataVeioDe = %s\n"
                    u"$script:URL_RELEASES = %s\n"
                    u"$script:URLS_DA_REDE = @(%s)\n"
                    u"$fim = [string](UltimoDaSaida (IniciarAtualizarApp @{ pasta = %s; versao = '8.4' }))\n"
                    u"'%s:' + $fim + '|' + $script:Atualizador + '|' + $script:Marcou + '|' + "
                    u"$script:Avisos.Count + '|' + $script:Fechou + '|' + "
                    u"([string]$env:RADAI_ATUALIZAR_APP) + '|' + "
                    u"(($script:Avisos | ForEach-Object { $_ }) -join ' / ') + '|' + "
                    u"(($script:Log | ForEach-Object { $_ }) -join ' ## ') + '|' + "
                    u"$script:Concluiu\n"
                    % (_pslit(veio), _pslit(release), u", ".join(_pslit(r) for r in redes),
                       _pslit(inst), nome_cena))

        cab = (u"$ErrorActionPreference = 'Stop'\n"
               u"Set-StrictMode -Version Latest\n"
               u"$env:TEMP = %(temp)s; $env:TMP = %(temp)s; $env:LOCALAPPDATA = %(ad)s\n"
               u"$env:RADAI_SEM_JANELA = '1'\n"
               u"$env:RADAI_ATUALIZAR_APP = $null; $env:RADAI_ATUALIZAR_APP_DE = $null\n"
               u"$script:AQUI = %(aqui)s\n"
               u"$script:UPDATE_PS1 = %(upd)s\n"
               u"$script:PY = %(py)s\n"
               u"$script:VERSAO_INSTALADOR = '8.5'\n"
               u"$script:PROJETO_RT = 'LOCAL_SUITE'\n"
               u"$script:URL_REPOSITORIO = 'https://github.com/drhenriquebraga/local-suite'\n"
               u"$script:Ocupado = $false\n"
               u"$script:CascataConferiuAVersao = $false\n"
               u"$script:PacoteEscolhido = ''\n"
               u"function Pump { }\n"
               u"function T { param([AllowEmptyString()][string]$Texto) return $Texto }\n"
               u"function Sessao { param($Texto) }\n"
               u"function Registrar { param([string]$Texto, [string]$Nivel = 'info')\n"
               u"    $script:Log += ($Nivel + ' ' + ($Texto -replace '[|\\r\\n]', ' ')) }\n"
               u"function Falhar { param([string]$Texto) Registrar ('FALHAR ' + $Texto) 'erro' }\n"
               u"function DescreverUnidade { param($P) return 'unidade de teste' }\n"
               u"function EsconderPreparo { }\n"
               u"function MostrarPreparo { }\n"
               u"function EsconderAJanela { }\n"
               u"function MostrarAJanela { }\n"
               u"function FecharAJanela { $script:Fechou++ }\n"
               u"function MarcarModo { param([string]$Qual) $script:Marcou += $Qual }\n"
               u"function AvisarAtualizarApp { param([string]$Texto, [string]$Icone = 'Information')\n"
               u"    $script:Avisos += ($Icone + ' ' + ($Texto -replace '[|\\r\\n]', ' ')) }\n"
               u"function PerguntarSeTentaDeNovo { param($Pasta) return $false }\n"
               u"function PerguntarSeProcessando { param($Pasta) return $true }\n"
               u"function FecharJanelasDoApp { return 0 }\n"
               u"function ConcluirAtualizacao { param($Inst, $Como, $De)\n"
               u"    $script:Concluiu += $Como }\n"
               u"function AcharInstalacao { return $null }\n"
               u"function PintarEstado { }\n"
               u"function AnotarPastaDoOperador { param($a, $b) }\n"
               u"function EscolherPacoteTrazido { param($Titulo) $script:TituloDoPacote = $Titulo\n"
               u"    return $script:PacoteEscolhido }\n"
               u"function RodarAtualizador { param([string]$Pasta, [string[]]$Extra)\n"
               u"    $ErrorActionPreference = 'Continue'\n"
               u"    $script:Atualizador++\n"
               u"    $saida = & powershell -NoProfile -ExecutionPolicy Bypass -File $script:UPDATE_PS1 "
               u"-Destino $Pasta -Python $script:PY @Extra 2>&1\n"
               u"    $rc = $LASTEXITCODE\n"
               u"    foreach ($l in @($saida)) { Registrar ('  upd ' + [string]$l) }\n"
               u"    return $rc }\n"
               % {"temp": _pslit(temp), "ad": _pslit(ad),
                  "aqui": _pslit(os.path.join(pac, "packager")),
                  "upd": _pslit(os.path.join(pac, "packager", "UPDATE.ps1")),
                  "py": _pslit(sys.executable)})
        funcoes = u"\n".join(fs[n] for n in _FUNCOES_DA_CASCATA) + u"\n"
        corpo = (cab + funcoes +
                 cena(u"A", insts[u"A"], url + u"/novo/latest", [morta]) +
                 u"$mk = Join-Path $env:TEMP 'RadioterapiaAI_instalador_v99.0\\LOCAL_SUITE_SETUP\\marca.txt'\n"
                 u"'MARCA:' + $(if (Test-Path -LiteralPath $mk) { [System.IO.File]::ReadAllText($mk) } else { '(sem marca)' })\n"
                 u"'ZIPFICOU:' + (Test-Path -LiteralPath (Join-Path $env:TEMP 'RadioterapiaAI_instalador_v99.0.zip'))\n" +
                 cena(u"B", insts[u"B"], url + u"/tamanho/latest", [morta]) +
                 cena(u"C", insts[u"C"], url + u"/soma/latest", [morta]) +
                 cena(u"D", insts[u"D"], url + u"/mentira/latest", [morta]) +
                 cena(u"E", insts[u"E"], url + u"/fuga/latest", [morta]) +
                 cena(u"F", insts[u"F"], url + u"/velho/latest", [morta]) +
                 cena(u"G", insts[u"G"], url + u"/velho/latest", [morta]) +
                 cena(u"H", insts[u"H"], url + u"/sem_release/latest", [morta]) +
                 cena(u"I", insts[u"I"], morta, [morta]) +
                 u"'TITULO:' + $script:TituloDoPacote\n" +
                 cena(u"J", insts[u"J"], morta, [url + u"/rede"]) +
                 cena(u"K", insts[u"K"], morta, [morta], veio=u"8.4"))

        def mutar(nome_f, de, para):
            txt = fs[nome_f]
            return (txt.replace(de, para) if txt.count(de) == 1 else u""), txt.count(de)

        iscas = [
            (u"IA", u"AtualizarApp", u"elseif (MaisNovaQue $la.versao $script:VERSAO_INSTALADOR)",
             u"elseif ($false)", url + u"/novo/latest", [morta]),
            (u"IB", u"BaixarInstaladorNovo", u"if ([int64]$ins.tamanho -gt 0) {",
             u"if ($false) {", url + u"/tamanho/latest", [morta]),
            (u"IC", u"AtualizarApp", u"    if ($rede) {\r\n", u"    if ($true) {\r\n",
             morta, [morta]),
            (u"ID", u"IniciarAtualizarApp", u"AvisarAtualizarApp ((T 'Atualiza",
             u"$null = Write-Output ((T 'Atualiza", morta, [morta]),
        ]
        montou = {}
        for nome_i, nome_f, de, para, rel, redes in iscas:
            txt, n = mutar(nome_f, de, para)
            if not txt and u"\r\n" in de:
                txt, n = mutar(nome_f, de.replace(u"\r\n", u"\n"), para.replace(u"\r\n", u"\n"))
            montou[nome_i] = n == 1
            if txt:
                corpo += txt + u"\n"
                corpo += cena(nome_i, insts[nome_i], rel, redes)
                corpo += fs[nome_f] + u"\n"
        out, rc = _rodar_harness(corpo, timeout=600)
        m = _marcas(out)
        if out is None:
            checar(u"a cascata rodou no PowerShell", False, u"esgotou o tempo")
            return

        def c(k):
            v = (m.get(k) or u"").split(u"|")
            return v + [u""] * (9 - len(v))

        def codigo(inst):
            return io.open(os.path.join(inst, "engine.py")).read()

        def entrega(inst):
            return io.open(os.path.join(inst, "entrega.txt")).read()

        a = c(u"A")
        checar(u"(1) release com instalador mais novo: baixa, confere e SEGUE POR ELE",
               a[0] == u"novo" and a[1] == u"0" and a[4] == u"1",
               u"fim=%s atualizador=%s fechou=%s | %s" % (a[0], a[1], a[4], (out or u"")[-400:]))
        _mt = m.get(u"MARCA") or u""
        checar(u"  o instalador novo rodou com a pasta instalada e a versao que o chamou",
               _mt.lower() == (insts[u"A"] + u"|8.5").lower(), _mt or u"(sem marca)")
        checar(u"  conferido por tamanho E soma SHA-256, e o log diz",
               u"tamanho de" in a[7] and u"soma SHA-256" in a[7], a[7][-300:])
        checar(u"  o .zip baixado nao fica para tras", m.get(u"ZIPFICOU") == u"False",
               m.get(u"ZIPFICOU"))
        checar(u"  e a variavel do contrato nao vaza para depois", a[5] == u"", a[5])
        checar(u"  e este nao trocou o codigo da instalacao (quem troca e o novo)",
               u"ANTIGO" in codigo(insts[u"A"]), codigo(insts[u"A"]))
        for k, oque, frase in ((u"B", u"o tamanho nao bate", u"bytes, e a release diz"),
                               (u"C", u"a soma nao bate", u"nao bate com a da release"),
                               (u"D", u"o instalador diz outra versao", u"diz ser a v98.0"),
                               (u"E", u"o .zip grava fora da pasta", u"grava fora da pasta")):
            v = c(k)
            checar(u"  (isca) %s: RECUSA o baixado e segue com este instalador" % oque,
                   v[0] == u"codigo" and v[1] == u"1" and v[4] == u"0" and frase in v[7],
                   u"fim=%s atualizador=%s | %s" % (v[0], v[1], v[7][-260:]))
        checar(u"  e nada do .zip que fugia foi gravado fora da extracao",
               not os.path.exists(os.path.join(temp, u"fora_da_extracao.txt")))
        f = c(u"F")
        checar(u"(2) impressao igual: so o codigo, pelo UPDATE.ps1, sem perguntar",
               f[0] == u"codigo" and f[1] == u"1" and f[2] == u"" and f[3] == u"0",
               u"%s | %s" % (f[:5], f[7][-300:]))
        checar(u"  e o codigo novo chegou, com a versao no entrega.txt",
               u"versao 8.5" in codigo(insts[u"F"]) and u"VERSAO=8.5" in entrega(insts[u"F"]),
               codigo(insts[u"F"]))
        checar(u"  e o log diz cada decisao da cascata (1/4 e 2/4)",
               u"cascata 1/4" in f[7] and u"cascata 2/4" in f[7], f[7][-300:])
        checar(u"  e a tela segue sozinha para a etapa 4, com o botao verde de abrir o app",
               f[8] == u"codigo", u"concluiu=%r" % f[8])
        checar(u"  (isca) quem segue para atualizar tudo NAO vai para a etapa 4",
               c(u"G")[8] == u"", u"concluiu=%r" % c(u"G")[8])
        for k, oque in ((u"G", u"release respondeu"), (u"H", u"o 404 da release ainda e rede"),
                        (u"J", u"release fora, mas a sonda da rede responde"),
                        (u"K", u"veio do instalador anterior, que baixou este")):
            v = c(k)
            checar(u"(3) impressao diferente e ha rede (%s): segue para ATUALIZAR TUDO" % oque,
                   v[0] == u"tudo" and v[2] == u"7" and v[3] == u"1"
                   and v[6].startswith(u"Information"),
                   u"%s | %s" % (v[:7], v[7][-260:]))
            checar(u"  e nao tocou no codigo antes", u"ANTIGO" in codigo(insts[k]))
        k = c(u"K")
        checar(u"  vindo do instalador anterior, nao consulta a release de novo",
               u"nao consulto a release de novo" in k[7], k[7][-200:])
        i = c(u"I")
        checar(u"(4) impressao diferente, sem rede e sem pacote: CANCELA",
               i[0] == u"cancelado" and i[2] == u"" and i[3] == u"1", u"%s | %s" % (i[:7], i[7][-300:]))
        checar(u"  com o alerta que diz incompativel, impede o uso e manda trazer o pacote",
               i[6].startswith(u"Warning") and u"incompatível" in i[6]
               and u"impede o uso" in i[6] and u"Traga um pacote atualizado" in i[6]
               and u"v8.5" in i[6], i[6][:300])
        checar(u"  e o seletor do .zip abriu com o titulo da cascata",
               u"Sem internet" in (m.get(u"TITULO") or u""), m.get(u"TITULO"))
        checar(u"  e o log diz CANCELADO e a decisao 4/4", u"CANCELADO" in i[7]
               and u"cascata 4/4" in i[7], i[7][-300:])
        checar(u"  e nada foi trocado", u"ANTIGO" in codigo(insts[u"I"])
               and u"VERSAO=8.4" in entrega(insts[u"I"]))
        for nome_i, oque, ok in (
                (u"IA", u"sem a etapa 1, a release mais nova e' ignorada", lambda v: v[0] != u"novo"),
                (u"IB", u"sem conferir o tamanho, o baixado errado passa", lambda v: v[0] == u"novo"),
                (u"IC", u"sem olhar a rede, o sem-rede vira atualizar tudo", lambda v: v[0] == u"tudo"),
                (u"ID", u"sem o alerta, o cancelamento sai calado", lambda v: v[3] == u"0")):
            v = c(nome_i)
            checar(u"  (isca) %s: a checagem pega" % oque, montou.get(nome_i) and ok(v),
                   u"montou=%s %s" % (montou.get(nome_i), v[:5]))

        import radai_version as _rv
        h = (u"$ErrorActionPreference = 'Stop'\nSet-StrictMode -Version Latest\n"
             u"$script:URL_REPOSITORIO = 'https://github.com/drhenriquebraga/local-suite'\n"
             u"$script:URL_PAGINA_VERSOES = $script:URL_REPOSITORIO + '/releases'\n"
             + fs[u"UrlDaConsultaDeVersao"] + u"\n"
             u"$env:RADAI_URL_VERSOES = $null; 'PADRAO:' + (UrlDaConsultaDeVersao)\n"
             u"$env:RADAI_URL_VERSOES = '0'; 'DESLIGADA:' + (UrlDaConsultaDeVersao)\n"
             u"$env:RADAI_URL_VERSOES = 'https://github.com/outro/repo/releases'; "
             u"'OUTRA:' + (UrlDaConsultaDeVersao)\n"
             u"$env:RADAI_URL_VERSOES = 'http://127.0.0.1:5/latest'; 'LOCAL:' + (UrlDaConsultaDeVersao)\n")
        out2, _rc2 = _rodar_harness(h, timeout=60)
        m2 = _marcas(out2)
        checar(u"a release consultada e' a mesma que o app consulta (radai_version)",
               m2.get(u"PADRAO") == _rv._api_de(_rv.URL_VERSOES)
               and m2.get(u"OUTRA") == _rv._api_de(u"https://github.com/outro/repo/releases")
               and m2.get(u"LOCAL") == u"http://127.0.0.1:5/latest",
               u"%s | %s" % (m2, _rv._api_de(_rv.URL_VERSOES)))
        checar(u"  e RADAI_URL_VERSOES=0 desliga a consulta, como no app",
               m2.get(u"DESLIGADA") == u"" and u"DESLIGADA:" in (out2 or u""), m2.get(u"DESLIGADA"))
    finally:
        if srv is not None:
            try:
                srv.shutdown()
                srv.server_close()
            except Exception:
                pass
        shutil.rmtree(base, ignore_errors=True)


def teste_a_instalacao_em_outro_disco():
    secao(u"a instalacao em outro disco (D:\\RADIOTERAPIA_AI\\LOCAL_SUITE): registro e deteccao")
    nomes = [u"UnidadesLocais", u"RaizesDeBusca", u"AcharInstalacao", u"MarcaDeInstalacao",
             u"MarcaDeInstalacaoAntiga", u"SobraDoPreparoAntigo", u"VersaoDaPasta"]
    fs = _funcoes_ps(u"packager/prepare.ps1", nomes)
    checar(u"as funcoes da deteccao existem e foram recortadas",
           set(fs) == set(nomes), u"%s%s" % (sorted(fs), _motivo_ast(fs)))
    if set(fs) != set(nomes):
        return
    base = tempfile.mkdtemp(prefix="radai_prep_disco_")
    try:
        c_ = os.path.join(base, "C_") + os.sep
        d_ = os.path.join(base, "D_") + os.sep
        os.makedirs(os.path.join(c_, "RADIOTERAPIA_AI"))
        pac = _cascata_pacote(base, u"8.5")
        inst = _cascata_instalacao(d_, u"LOCAL_SUITE", u"8.4", pac, 8799)
        reg = os.path.join(d_, "RADIOTERAPIA_AI", "_instalados.json")
        import radai_version as _rv
        _antes = os.environ.pop("RADAI_RAIZ_INSTALACAO", None)
        try:
            checar(u"o app le o registro no PAI da pasta, no disco dela",
                   os.path.normcase(_rv.registro_da_instalacao(inst)) == os.path.normcase(reg),
                   _rv.registro_da_instalacao(inst))
        finally:
            if _antes is not None:
                os.environ["RADAI_RAIZ_INSTALACAO"] = _antes
        corpo = (u"$ErrorActionPreference = 'Stop'\nSet-StrictMode -Version Latest\n"
                 u"$env:RADAI_RAIZES_BUSCA = $null\n" +
                 u"\n".join(fs[n] for n in nomes) + u"\n"
                 u"$env:RADAI_UNIDADES_LOCAIS = %(u)s\n"
                 u"$a = AcharInstalacao\n"
                 u"'ACHOU:' + $(if ($a) { $a.como + '|' + $a.versao + '|' + $a.pasta } else { 'nada' })\n"
                 u"[System.IO.File]::Delete(%(reg)s)\n"
                 u"$a = AcharInstalacao\n"
                 u"'SEMREG:' + $(if ($a) { $a.como + '|' + $a.versao + '|' + $a.pasta } else { 'nada' })\n"
                 u"function UnidadesLocais { return @(@(%(c)s, %(d)s)[0]) }\n"
                 u"$a = AcharInstalacao\n"
                 u"'ISCA:' + $(if ($a) { $a.pasta } else { 'nada' })\n"
                 % {"u": _pslit(c_ + u";" + d_), "reg": _pslit(reg), "c": _pslit(c_), "d": _pslit(d_)})
        out, _rc = _rodar_harness(corpo, timeout=90)
        m = _marcas(out)
        a = (m.get(u"ACHOU") or u"").split(u"|")
        checar(u"o preparador acha a instalacao do SEGUNDO disco pelo registro do pai",
               len(a) == 3 and a[0] == u"registro" and a[1] == u"8.4"
               and os.path.normcase(a[2]) == os.path.normcase(inst), m.get(u"ACHOU") or (out or u"")[-300:])
        s = (m.get(u"SEMREG") or u"").split(u"|")
        checar(u"  e sem o registro, pela marca, no mesmo disco",
               len(s) == 3 and s[0] == u"marca" and os.path.normcase(s[2]) == os.path.normcase(inst),
               m.get(u"SEMREG"))
        checar(u"  (isca) olhando so o primeiro disco, nao acha",
               m.get(u"ISCA") == u"nada", m.get(u"ISCA"))
        _cascata_instalacao(d_, u"LOCAL_SUITE", u"8.4", pac, 8799)
        upd = os.path.join(pac, "packager", "UPDATE.ps1")
        amb = dict(os.environ)
        amb.update({"TEMP": os.path.join(base, "temp"), "TMP": os.path.join(base, "temp"),
                    "LOCALAPPDATA": os.path.join(base, "ad"), "RADAI_SEM_JANELA": "1"})
        for dd in (amb["TEMP"], amb["LOCALAPPDATA"]):
            os.makedirs(dd, exist_ok=True)
        resultados = {}
        for nome_c, unidades in ((u"DOIS", c_ + u";" + d_), (u"SOC", c_)):
            amb["RADAI_UNIDADES_LOCAIS"] = unidades
            p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                "-File", upd, "-Python", sys.executable, "-SemPerguntar"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, timeout=300, env=amb)
            resultados[nome_c] = (p.returncode, p.stdout.decode("cp1252", "replace"))
        rc, t = resultados[u"DOIS"]
        checar(u"o atualizador, sem -Destino, acha a instalacao do segundo disco e atualiza",
               rc == 0 and inst.lower() in t.lower()
               and u"versao 8.5" in io.open(os.path.join(inst, "engine.py")).read(),
               u"rc=%s | %s" % (rc, t[-300:]))
        rc2, t2 = resultados[u"SOC"]
        checar(u"  (isca) so com o primeiro disco, nao acha e diz como apontar",
               rc2 == 1 and u"Nao achei nenhuma instalacao" in t2, u"rc=%s | %s" % (rc2, t2[-200:]))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    print(u"=" * 68)
    print(u"test_packager | hashes, versoes fixadas, aceite e manifesto")
    print(u"=" * 68)
    teste_o_ps51_nao_herda_os_modulos_do_pwsh7()
    teste_aborta()
    teste_baixar_confere()
    teste_versao_fixada()
    teste_um_caminho()
    teste_aceite_artefato()
    teste_extracao_vai_para_o_disco_do_destino()
    teste_o_recorte_diz_por_que_falhou()
    teste_extracao_nao_prende_a_janela()
    teste_ler_o_filho_nao_prende_a_janela()
    teste_esperar_a_rede_nao_prende_a_janela()
    teste_sem_url_rolante()
    teste_pino_cabe_no_runtime_alvo()
    teste_manifesto()
    teste_link_de_licenca_leva_a_licenca()
    teste_o_preparador_acha_o_bundle_que_o_motor_produz()
    teste_o_montador_acha_o_que_o_pacote_leva()
    teste_contrato()
    teste_guarda_da_nuvem()
    teste_reexibicao()
    teste_o_catalogo_json_nao_diverge_do_python()
    teste_o_recibo_mede_o_pacote_e_nao_repete_o_pedido()
    teste_a_selecao_nunca_tira_o_nucleo()
    teste_a_base_tem_reserva_e_ela_so_baixa_quando_precisa()
    teste_o_pacote_e_um_so()
    teste_icone_e_atalhos()
    teste_pacote_do_preparador()
    teste_interface()
    teste_abrir()
    teste_conclusao_qual_botao()
    teste_instalador_zip()
    teste_dois_layouts()
    teste_start_here_diz_o_tamanho_e_guarda_o_log()
    teste_parentese_no_caminho_nao_derruba_o_lote()
    teste_o_motor_sobe_sem_janela()
    teste_erro_de_topo_vai_para_o_log()
    teste_membros_ps1()
    teste_preparador_abre()
    teste_sem_rede_nao_e_artefato_quebrado()
    teste_autoteste_percorre_a_tela()
    teste_barra_nao_enche_a_janela_de_diagnostico()
    teste_o_recorte_no_corpo_vai_no_pacote()
    teste_o_caminho_do_pacote_nao_vai_para_o_log()
    teste_a_pasta_escolhida_nao_vai_para_o_log()
    teste_o_modo_3_nao_consulta_a_versao()
    teste_raiz_de_disco_chega_ao_motor()
    teste_o_bundle_escolhido_e_o_que_acabou_de_sair()
    teste_o_bundle_minimo_serve_a_esta_versao()
    teste_o_modo_3_cumpre_a_linha_da_aba_0()
    teste_pesos_ts_baixados_por_nos()
    teste_o_estado_do_otimizador_sai_e_a_rede_fica()
    teste_o_enxugar_dos_modelos_do_registro()
    teste_o_servidor_e_a_segunda_passada()
    teste_a_divergencia_nao_chega_a_reserva()
    teste_cada_codigo_do_motor_tem_frase_no_preparador()
    teste_o_passo_4_diz_o_limite_da_conferencia()
    teste_certificado_recusado()
    teste_o_recuo_pelo_truststore_respeita_o_prazo()
    teste_o_veredito_fora_da_tabela_nao_promete_tamanho()
    teste_sonda_do_pip_calada()
    teste_o_lancador_do_motor_http_saiu()
    teste_tabela_da_biblioteca_real()
    teste_o_preparo_confere_os_pesos_do_ensemble()
    teste_atualizar_app_e_uma_cascata()
    teste_a_instalacao_em_outro_disco()
    print(u"\n" + u"=" * 68)
    if _falhou:
        print(u"FALHOU: %d de %d checagens" % (_falhou, _ok + _falhou))
        for f in _falhas:
            print(u"  - %s" % f)
    else:
        print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 68)
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
