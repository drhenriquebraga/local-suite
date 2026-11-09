# -*- coding: utf-8 -*-
import http.server
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
_cleanup.adotar_prefixo("radai_direto_")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "build"))
sys.path.insert(0, os.path.join(RAIZ, "app"))
_ACERVO = tempfile.mkdtemp(prefix="radai_direto_acervo_")
os.environ["RADAI_CALIB_DIR"] = _ACERVO

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


def ler(*rel):
    p = os.path.join(RAIZ, *rel)
    return io.open(p, encoding="utf-8-sig", errors="replace").read()


def _motor():
    import configurar_ambiente as C
    return C


def _tmp():
    return tempfile.mkdtemp(prefix="radai_direto_")


def _instalacao_fantoma(pasta, versao=u"0.1"):
    os.makedirs(os.path.join(pasta, "python"), exist_ok=True)
    os.makedirs(os.path.join(pasta, "launchers"), exist_ok=True)
    os.makedirs(os.path.join(pasta, "ts_weights"), exist_ok=True)
    for rel, txt in ((("radai_watcher.py",), u"# fantoma\n"),
                     (("engine.py",), u"# fantoma\n"),
                     (("radai_geom.py",), u"# fantoma\n"),
                     (("python", "python.exe"), u"x"),
                     (("RADIOTERAPIA_AI_LOCAL_SUITE.cmd",), u"@echo off\r\n"),
                     (("launchers", "start_watcher.cmd",), u"@echo off\r\n"),
                     (("entrega.txt",), u"PROJETO=LOCAL_SUITE\nVERSAO=%s\n" % versao)):
        io.open(os.path.join(pasta, *rel), "w", encoding="utf-8").write(txt)


def teste_pasta_de_instalacao():
    secao(u"a instalacao direta escolhe a pasta pela MARCA, e recusa pasta alheia")
    C = _motor()
    base = _tmp()
    try:
        nova = os.path.join(base, "nao_existe", "LOCAL_SUITE")
        checar(u"pasta que nao existe: aceita",
               C.conferir_pasta_de_instalacao(nova) == u"")
        vazia = os.path.join(base, "vazia")
        os.makedirs(vazia)
        checar(u"pasta vazia: aceita", C.conferir_pasta_de_instalacao(vazia) == u"")
        so_aceite = os.path.join(base, "aceite")
        os.makedirs(so_aceite)
        for n in ("LICENCAS_ACEITAS.txt", "idioma.txt", "preparar_log.txt"):
            io.open(os.path.join(so_aceite, n), "w").write(u"x")
        checar(u"pasta so com o aceite e o idioma do preparador: aceita",
               C.conferir_pasta_de_instalacao(so_aceite) == u"")
        inst = os.path.join(base, "instalada")
        _instalacao_fantoma(inst)
        io.open(os.path.join(inst, "radai_watcher.config"), "w").write(u"ROOT=\n")
        checar(u"instalacao existente (radai_watcher.py + entrega.txt): aceita",
               C.conferir_pasta_de_instalacao(inst) == u"")
        meio = os.path.join(base, "meio")
        os.makedirs(os.path.join(meio, C.OFICINA_NO_LUGAR))
        os.makedirs(os.path.join(meio, "python"))
        io.open(os.path.join(meio, C.OFICINA_NO_LUGAR, C.MARCA_DO_MOTOR), "w").write(u"x")
        checar(u"sobra de uma instalacao direta interrompida (o motor ja tinha comecado): aceita",
               C.conferir_pasta_de_instalacao(meio) == u"")
        so_oficina = os.path.join(base, "so_oficina")
        os.makedirs(os.path.join(so_oficina, C.OFICINA_NO_LUGAR))
        io.open(os.path.join(so_oficina, "LICENCAS_ACEITAS.txt"), "w").write(u"x")
        checar(u"a oficina vazia que o preparador cria antes do motor: aceita",
               C.conferir_pasta_de_instalacao(so_oficina) == u"")
        forjada = os.path.join(base, "forjada")
        os.makedirs(os.path.join(forjada, C.OFICINA_NO_LUGAR))
        io.open(os.path.join(forjada, "planilha.xlsx"), "w").write(u"x")
        m = C.conferir_pasta_de_instalacao(forjada)
        checar(u"pasta alheia com a oficina vazia que o preparador criou: RECUSADA pelo motor",
               bool(m) and u"planilha.xlsx" in m, m)
        alheia = os.path.join(base, "documentos")
        os.makedirs(alheia)
        io.open(os.path.join(alheia, "planilha.xlsx"), "w").write(u"x")
        m = C.conferir_pasta_de_instalacao(alheia)
        checar(u"pasta com arquivo de outra pessoa: RECUSADA, com o nome dele",
               bool(m) and u"planilha.xlsx" in m, m)
        raiz_disco = os.path.splitdrive(base)[0] + os.sep
        checar(u"raiz de disco: RECUSADA",
               bool(C.conferir_pasta_de_instalacao(raiz_disco)))
        antes = os.environ.get("RADAI_RAIZES_NUVEM")
        os.environ["RADAI_RAIZES_NUVEM"] = base
        try:
            m = C.conferir_pasta_de_instalacao(vazia)
            checar(u"pasta que sincroniza com a nuvem: RECUSADA",
                   bool(m) and u"nuvem" in m, m)
        finally:
            if antes is None:
                os.environ.pop("RADAI_RAIZES_NUVEM", None)
            else:
                os.environ["RADAI_RAIZES_NUVEM"] = antes
    finally:
        shutil.rmtree(base, ignore_errors=True)


class _Dubles(object):
    NOMES = ("etapa_runtime", "etapa_pip", "etapa_libs", "etapa_pesos",
             "etapa_app", "etapa_validar", "etapa_empacotar",
             "etapa_distribuir", "conferir_recorte_no_corpo",
             "escrever_recibo_medido", "conferir_modelos_exigidos")

    def __init__(self, C):
        self.C = C
        self.chamadas = []
        self.ctxs = []
        self.velhos = {n: getattr(C, n) for n in self.NOMES}

    def __enter__(self):
        C = self.C

        def faz(nome):
            def _f(ctx, *a, **kw):
                self.chamadas.append(nome)
                self.ctxs.append(ctx)
                b = pathlib.Path(str(ctx["bundle"]))
                if nome == "etapa_runtime":
                    (b / "python").mkdir(parents=True, exist_ok=True)
                    (b / "python" / "python.exe").write_text(u"x")
                if nome == "etapa_pesos":
                    (pathlib.Path(str(ctx["cache"])) / "lixo.zip").write_text(u"z")
                if nome == "etapa_app":
                    (b / "radai_watcher.py").write_text(u"# novo\n")
                    (b / "engine.py").write_text(u"# novo\n")
            return _f
        for n in self.NOMES[:8]:
            setattr(C, n, faz(n))
        C.conferir_recorte_no_corpo = lambda *a, **kw: self.chamadas.append(u"recorte")
        C.escrever_recibo_medido = lambda *a, **kw: ([], [])
        C.conferir_modelos_exigidos = lambda *a, **kw: self.chamadas.append(u"exigidos")
        self.etapas_velhas = C.ETAPAS
        C.ETAPAS = [(n, getattr(C, f)) for n, f in (
            ("runtime", "etapa_runtime"), ("pip", "etapa_pip"),
            ("libs", "etapa_libs"), ("pesos", "etapa_pesos"),
            ("app", "etapa_app"), ("validar", "etapa_validar"),
            ("empacotar", "etapa_empacotar"),
            ("distribuir", "etapa_distribuir"))]
        return self

    def __exit__(self, *a):
        for n, f in self.velhos.items():
            setattr(self.C, n, f)
        self.C.ETAPAS = self.etapas_velhas
        try:
            if self.C.LOG:
                self.C.LOG.close()
        except Exception:
            pass
        self.C.LOG = None


def _aceite(pasta):
    os.makedirs(pasta, exist_ok=True)
    io.open(os.path.join(pasta, "LICENCAS_ACEITAS.txt"), "w", encoding="utf-8").write(
        u"LICENCAS ACEITAS\n[ACEITA]   TotalSegmentator\n")
    io.open(os.path.join(pasta, "idioma.txt"), "w", encoding="utf-8").write(u"en")


def teste_motor_instala_no_lugar():
    secao(u"--instalar: baixa e monta na pasta FINAL, sem montagem, sem .zip")
    C = _motor()
    base = _tmp()
    try:
        final = os.path.join(base, "RADIOTERAPIA_AI", "LOCAL_SUITE")
        _aceite(final)
        with _Dubles(C) as d:
            rc = C.main(["--instalar", final])
        checar(u"o motor termina com 0", rc == 0, rc)
        checar(u"rodou runtime, pip, libs, pesos, validar e SO DEPOIS o app",
               d.chamadas[:6] == ["etapa_runtime", "etapa_pip", "etapa_libs",
                                  "etapa_pesos", "etapa_validar", "etapa_app"],
               d.chamadas)
        checar(u"o finalizar confere os modelos que alimentam o entregue",
               u"exigidos" in d.chamadas, d.chamadas)
        checar(u"a impressao e o entrega.txt saem juntos no finalizar",
               os.path.isfile(os.path.join(final, "_requisitos.json"))
               and os.path.isfile(os.path.join(final, "entrega.txt")))
        checar(u"e NAO empacotou nem conferiu .zip",
               "etapa_empacotar" not in d.chamadas
               and "etapa_distribuir" not in d.chamadas, d.chamadas)
        checar(u"a montagem e a propria pasta final",
               d.ctxs and str(d.ctxs[0]["bundle"]) == str(pathlib.Path(final).resolve()),
               d.ctxs[0]["bundle"] if d.ctxs else u"")
        zips = [os.path.join(r, f) for r, _, fs in os.walk(base) for f in fs
                if f.lower().endswith(".zip")]
        checar(u"nenhum .zip foi criado", not zips, zips)
        checar(u"nenhuma pasta «preparo» nem «_montagem» nasceu",
               not any(n in ("preparo", "_montagem")
                       for _, ds, _ in os.walk(base) for n in ds))
        ent = os.path.join(final, "entrega.txt")
        checar(u"o entrega.txt foi carimbado na pasta final",
               os.path.isfile(ent) and u"VERSAO=" in io.open(ent, encoding="utf-8").read())
        checar(u"o MANIFESTO.txt mora na pasta do programa",
               os.path.isfile(os.path.join(final, "MANIFESTO.txt")))
        checar(u"o idioma escolhido no preparador ficou",
               io.open(os.path.join(final, "idioma.txt"), encoding="utf-8").read().strip() == u"en")
        checar(u"o cache de download foi apagado ao fim",
               not os.path.isdir(os.path.join(final, C.OFICINA_NO_LUGAR, "cache")))
        checar(u"o recorte no corpo foi conferido na pasta final",
               u"recorte" in d.chamadas)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_tentativa_interrompida_e_reconhecida():
    secao(u"o motor marca a oficina ao comecar: a segunda tentativa e' aceita")
    C = _motor()
    base = _tmp()
    try:
        final = os.path.join(base, "LOCAL_SUITE")
        _aceite(final)

        def quebra(ctx):
            raise RuntimeError(u"rede caiu no meio")
        with _Dubles(C) as d:
            C.ETAPAS = [(n, (quebra if n == "libs" else f)) for n, f in C.ETAPAS]
            try:
                C.main(["--instalar", final])
            except (RuntimeError, SystemExit):
                pass
        checar(u"a primeira tentativa deixou o runtime na pasta (fantoma)",
               os.path.isdir(os.path.join(final, "python")))
        checar(u"  e a marca do motor na oficina",
               os.path.isfile(os.path.join(final, C.OFICINA_NO_LUGAR, C.MARCA_DO_MOTOR)))
        m = C.conferir_pasta_de_instalacao(final)
        checar(u"  e a segunda tentativa na mesma pasta e' aceita", m == u"", m)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _instalacao_antiga(pasta):
    os.makedirs(os.path.join(pasta, "python"), exist_ok=True)
    for rel, txt in ((("radai_watcher.py",), u"# antigo\n"),
                     (("engine.py",), u"# antigo\n"),
                     (("radai_watcher.config",), u"ROOT=X:\\exames\n"),
                     (("python", "python.exe"), u"x")):
        io.open(os.path.join(pasta, *rel), "w", encoding="utf-8").write(txt)


def teste_motor_atualiza_a_instalacao_antiga():
    secao(u"--instalar sobre a instalacao antiga (sem entrega.txt), com a sobra «preparo» ao lado")
    C = _motor()
    base = _tmp()
    try:
        final = os.path.join(base, "RADIOTERAPIA_AI", "LOCAL_SUITE")
        _instalacao_antiga(final)
        _aceite(final)
        os.makedirs(os.path.join(final, C.OFICINA_NO_LUGAR))
        os.makedirs(os.path.join(final, "preparo", "_montagem", "LOCAL_SUITE"))
        m = C.conferir_pasta_de_instalacao(final)
        checar(u"a pasta da instalacao antiga, com a oficina vazia e a sobra «preparo»: aceita",
               m == u"", m)
        with _Dubles(C) as d:
            try:
                rc = C.main(["--instalar", final])
            except SystemExit as e:
                rc = u"%s" % e
        checar(u"«Atualizar tudo» (--instalar) roda o motor inteiro sobre ela",
               rc == 0 and "etapa_app" in d.chamadas, rc)
        checar(u"  e ela sai com a marca nova (entrega.txt ao lado do radai_watcher.py)",
               C.marca_de_instalacao(final))
        checar(u"  e a configuracao do operador ficou",
               io.open(os.path.join(final, "radai_watcher.config"), encoding="utf-8").read()
               == u"ROOT=X:\\exames\n")
        clone = os.path.join(base, "clone")
        os.makedirs(clone)
        for n in ("radai_watcher.py", "engine.py"):
            io.open(os.path.join(clone, n), "w").write(u"#")
        m = C.conferir_pasta_de_instalacao(clone)
        checar(u"  (isca) radai_watcher.py sem o python\\python.exe ao lado: RECUSADA",
               bool(m) and u"engine.py" in m, m)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_motor_recusa():
    secao(u"--instalar recusa o que nao pode, ANTES de baixar")
    C = _motor()
    base = _tmp()
    try:
        alheia = os.path.join(base, "alheia")
        _aceite(alheia)
        io.open(os.path.join(alheia, "foto.jpg"), "w").write(u"x")
        for rotulo, argv, trecho in (
                (u"--instalar com --preparo", ["--instalar", alheia, "--preparo", base],
                 u"modos diferentes"),
                (u"pasta alheia", ["--instalar", alheia], u"foto.jpg"),
                (u"sem o aceite gravado", ["--instalar", os.path.join(base, "nova")],
                 u"LICENCAS_ACEITAS")):
            with _Dubles(C) as d:
                try:
                    C.main(argv)
                    msg = u"(voltou sem parar)"
                except SystemExit as e:
                    msg = u"%s" % e
            checar(u"%s: para com o motivo" % rotulo, trecho in msg, msg[:160])
            checar(u"  e nada foi baixado", not d.chamadas, d.chamadas)
        fonte = ler("build", "configurar_ambiente.py")
        checar(u"o modo «Atualizar modelos e plugins» saiu do motor",
               u"so_pacote" not in fonte and u"etapa_finalizar_pacote" not in fonte)
        import contextlib
        err = io.StringIO()
        with _Dubles(C) as d, contextlib.redirect_stderr(err):
            try:
                C.main(["--instalar", alheia, "--so-pacote"])
                msg = u""
            except SystemExit as e:
                msg = u"%s" % e
        checar(u"  e quem ainda pedir --so-pacote e recusado antes de baixar",
               msg == u"2" and u"--so-pacote" in err.getvalue() and not d.chamadas,
               (msg, err.getvalue()[-160:]))
    finally:
        shutil.rmtree(base, ignore_errors=True)


class _Servidor(object):
    def __init__(self, arquivos):
        self.arquivos = arquivos
        dono = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                nome = self.path.rsplit("/", 1)[-1]
                corpo = dono.arquivos.get(nome)
                if corpo is None:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *a):
                pass
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = u"http://127.0.0.1:%d/d/" % self.srv.server_address[1]

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


def _zip_bytes(membros):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for nome, dado in membros:
            z.writestr(nome, dado)
    return b.getvalue()


def teste_modelos_que_alimentam_o_entregue():
    secao(u"o modelo que alimenta o entregue PARA o preparo (tudo ou nada)")
    C = _motor()
    import hashlib
    import types
    import radai_models
    import radai_motores_full
    velho_log = C.log
    linhas = []
    C.log = lambda m="": linhas.append(u"%s" % m)
    base = _tmp()
    try:
        exig = C.modelos_exigidos()
        checar(u"os exigidos sao o encefalo e os niveis, lidos dos motores",
               set(exig) == set(radai_motores_full.MODELO_DO_MOTOR.values()) | {u"hnlnl"}
               and u"cranio_buti" in exig, exig)
        checar(u"  e nenhum modelo so de comparacao entra na lista",
               not set(exig) & {u"nv_segment_ct", u"cads_open", u"moose"}, exig)

        def pasta_do_modelo(ident, criar=False):
            d = pathlib.Path(base) / "modelos" / str(ident)
            if criar:
                d.mkdir(parents=True, exist_ok=True)
            return d

        def registro(falha, sem=(), no_estado=None, na_pasta=None, modelos=None,
                     chamados=None):
            def baixar(ident):
                if chamados is not None:
                    chamados.append(ident)
                if ident in falha:
                    raise falha[ident]
                return {"baixados": [], "pulados": []}

            def estado_do_modelo(ident):
                if ident in (no_estado or {}):
                    raise no_estado[ident]
                return {"bytes_total": 0}

            def pasta_falsa(ident, criar=False):
                if ident in (na_pasta or {}):
                    raise na_pasta[ident]
                return pasta_do_modelo(ident, criar)
            campos = dict(MODELOS=radai_models.MODELOS if modelos is None else modelos,
                          baixar=baixar, estado_do_modelo=estado_do_modelo,
                          pasta_do_modelo=pasta_falsa)
            for nome in sem:
                campos.pop(nome)
            return types.SimpleNamespace(**campos)
        ctx = {"bundle": pathlib.Path(base)}
        import inspect
        checar(u"o registro falso tem a pasta_do_modelo com a assinatura da real",
               inspect.signature(pasta_do_modelo)
               == inspect.signature(radai_models.pasta_do_modelo),
               str(inspect.signature(radai_models.pasta_do_modelo)))

        def caiu_no_geral():
            return [l for l in linhas if u"nenhum modelo extra baixado" in l]

        def roda(falha, exigidos=None, sem=(), funcao=None, **kw):
            try:
                (funcao or C.baixar_modelos_do_registro)(
                    ctx, registro(falha, sem, **kw), [], exigidos)
                return None
            except Exception as e:
                return e
        r = roda({u"cranio_buti": IOError(u"sha256 nao bate")})
        checar(u"o download do encefalo falha: o preparo PARA",
               isinstance(r, C.FaltaModeloExigido) and u"NAO BAIXADO" in str(r)
               and u"sha256 nao bate" in str(r), repr(r))
        r = roda({u"hnlnl": IOError(u"CRC")})
        checar(u"o dos niveis cervicais falha: o preparo PARA",
               isinstance(r, C.FaltaModeloExigido) and u"NAO BAIXADO" in str(r)
               and u"CRC" in str(r), repr(r))
        r = roda({u"cranio_buti": OSError(u"getaddrinfo failed")})
        checar(u"  sem rede: para como SEM CONEXAO (o codigo da tela)",
               isinstance(r, C.SemRede), repr(r))
        r = roda({u"nv_segment_ct": IOError(u"x")})
        checar(u"o de comparacao falha: o pacote sai sem ele, e o log diz",
               r is None and any(u"NAO BAIXADO" in l for l in linhas), repr(r))
        r = roda({u"cranio_buti": IOError(u"x")}, exigidos=())
        checar(u"  (isca) sem a lista dos exigidos, o encefalo passava calado",
               r is None, repr(r))
        checar(u"nenhuma rodada caiu no except geral",
               not caiu_no_geral(), repr(caiu_no_geral()[:1]))
        del linhas[:]
        r = roda({})
        checar(u"sem falha nenhuma, a rodada passa: o registro falso cobre o que "
               u"o preparador chama",
               r is None and not any(u"NAO BAIXADO" in l for l in linhas),
               repr((r, [l for l in linhas if u"NAO BAIXADO" in l][:1])))
        r = roda({}, sem=(u"pasta_do_modelo",))
        checar(u"  (isca) sem a pasta_do_modelo no registro falso, a rodada sem "
               u"falha PARA e diz o que faltou",
               isinstance(r, C.FaltaModeloExigido) and u"AttributeError" in str(r),
               repr(r))

        def _versao_de_antes():
            src = inspect.getsource(C.baixar_modelos_do_registro)
            ini = (u"            try:\n"
                   u"                e = radai_models.estado_do_modelo(ident)\n")
            fim = u"                r = radai_models.baixar(ident)\n"
            if ini not in src or fim not in src:
                return None
            a, b = src.index(ini), src.index(fim)
            pre = u"".join(l[4:] for l in src[a + 17:b].splitlines(True))
            ns = dict(vars(C))
            exec(compile(src[:a] + pre + u"            try:\n" + src[b:],
                         u"<preambulo fora do try>", "exec"), ns)
            return ns["baixar_modelos_do_registro"]
        de_antes = _versao_de_antes()
        checar(u"(isca) a versao de antes, com o preambulo fora do try, se monta "
               u"da fonte", de_antes is not None)

        del linhas[:]
        chamados = []
        r = roda({}, no_estado={u"hnlnl": ValueError(u"registro ilegivel")},
                 chamados=chamados)
        checar(u"erro antes do download dos niveis (o estado do modelo): o "
               u"preparo PARA na hora, com a causa",
               isinstance(r, C.FaltaModeloExigido) and u"hnlnl" in str(r)
               and u"ValueError: registro ilegivel" in str(r)
               and u"cranio_buti" not in chamados, repr((r, chamados)))
        checar(u"  e o log nao diz que o bundle segue valido",
               not caiu_no_geral(), repr(caiu_no_geral()[:1]))
        del linhas[:]
        r = roda({}, no_estado={u"hnlnl": ValueError(u"registro ilegivel")},
                 funcao=de_antes)
        checar(u"  (isca) na versao de antes, o mesmo erro caia no except geral "
               u"e o preparo seguia dizendo que o bundle segue valido",
               de_antes is not None and r is None and bool(caiu_no_geral()),
               repr((r, caiu_no_geral()[:1])))
        r = roda({}, na_pasta={u"cranio_buti": PermissionError(u"acesso negado")})
        checar(u"erro na pasta do encefalo: o preparo PARA, com a causa",
               isinstance(r, C.FaltaModeloExigido) and u"cranio_buti" in str(r)
               and u"PermissionError: acesso negado" in str(r), repr(r))
        sem_licenca = dict(radai_models.MODELOS)
        sem_licenca[u"cranio_buti"] = dict(sem_licenca[u"cranio_buti"])
        sem_licenca[u"cranio_buti"].pop("licenca")
        r = roda({}, modelos=sem_licenca)
        checar(u"registro do encefalo sem a licenca: o preparo PARA, com a causa",
               isinstance(r, C.FaltaModeloExigido) and u"cranio_buti" in str(r)
               and u"KeyError" in str(r) and u"licenca" in str(r), repr(r))
        del linhas[:]
        chamados = []
        r = roda({}, no_estado={u"cads_open": ValueError(u"registro ilegivel")},
                 chamados=chamados)
        depois = [i for i in list(radai_models.MODELOS)[
            list(radai_models.MODELOS).index(u"cads_open") + 1:]
            if not radai_models.MODELOS[i].get("embutido")]
        checar(u"erro antes do download de um de comparacao: o pacote segue sem "
               u"ele, com a linha no log, e os modelos seguintes sao baixados",
               r is None and any(u"cads_open NAO BAIXADO (ValueError: registro "
                                 u"ilegivel)" in l for l in linhas)
               and depois and set(depois) <= set(chamados)
               and not caiu_no_geral(), repr((r, chamados, caiu_no_geral()[:1])))
        del linhas[:]
        chamados = []
        r = roda({}, no_estado={u"cads_open": ValueError(u"registro ilegivel")},
                 chamados=chamados, funcao=de_antes)
        checar(u"  (isca) na versao de antes, nenhum modelo seguinte era baixado",
               de_antes is not None and r is None and not chamados
               and bool(caiu_no_geral()), repr((r, chamados)))

        try:
            C.conferir_modelos_exigidos(base)
            checar(u"pacote sem os pesos exigidos: a validacao reprova", False)
        except C.FaltaModeloExigido as e:
            checar(u"pacote sem os pesos exigidos: a validacao reprova",
                   u"cranio_buti" in str(e) and u"hnlnl" in str(e), str(e)[:200])
        bom = b"pesos"
        radai_models.MODELOS[u"_teste_exigido"] = {
            "nome": u"t", "motor": u"t", "licenca": u"t", "uso_permitido": u"livre",
            "arquivos": [(u"w.bin", len(bom))],
            "sha256": {u"w.bin": hashlib.sha256(bom).hexdigest()}}
        try:
            alvo = pathlib.Path(base) / "modelos" / "_teste_exigido"
            alvo.mkdir(parents=True)
            (alvo / "w.bin").write_bytes(bom)
            try:
                C.conferir_modelos_exigidos(base, [u"_teste_exigido"])
                checar(u"com os pesos e a soma do registro: passa", True)
            except C.FaltaModeloExigido as e:
                checar(u"com os pesos e a soma do registro: passa", False, str(e))
            (alvo / "w.bin").write_bytes(b"PESOS")
            try:
                C.conferir_modelos_exigidos(base, [u"_teste_exigido"])
                checar(u"(isca) mesmo tamanho e soma diferente: reprova", False)
            except C.FaltaModeloExigido:
                checar(u"(isca) mesmo tamanho e soma diferente: reprova", True)
        finally:
            radai_models.MODELOS.pop(u"_teste_exigido", None)
        fonte = ler("build", "configurar_ambiente.py")
        for nome in (u"def etapa_validar(", u"def etapa_finalizar_no_lugar("):
            corpo = fonte[fonte.index(nome):]
            corpo = corpo[:corpo.index(u"\ndef ", 1)]
            checar(u"%s confere os exigidos" % nome[4:-1],
                   u"conferir_modelos_exigidos(" in corpo)
    finally:
        C.log = velho_log
        shutil.rmtree(base, ignore_errors=True)


def teste_a_demo_saiu_do_preparo():
    secao(u"a demo saiu do produto: o preparo nao baixa nem instala series")
    import artefatos
    fonte = ler("build", "configurar_ambiente.py")
    checar(u"o motor nao tem mais o baixador da demo",
           u"instalar_demo" not in fonte and u"EXTENSOES_DA_DEMO" not in fonte)
    checar(u"  nem os artefatos o endereco dela",
           not hasattr(artefatos, "url_da_demo") and not hasattr(artefatos, "DEMO"))
    corpo = fonte[fonte.index(u"def etapa_pesos("):fonte.index(u"def etapa_app(")]
    checar(u"  e a etapa de pesos termina nos modelos do registro",
           u"baixar_modelos_do_registro(" in corpo and u"demo" not in corpo.lower())


def _rodar_install(no_lugar, pacote, extra=None):
    ps1 = os.path.join(RAIZ, "installer", "INSTALL.ps1")
    env = dict(os.environ)
    env.pop("RADAI_RAIZ_INSTALACAO", None)
    env["RADAI_ATALHOS_NA_RAIZ"] = "1"
    env["RADAI_PASTA_PACOTE"] = pacote
    env["RADAI_LICENCAS_ACEITAS"] = "S"
    if no_lugar:
        env["RADAI_INSTALAR_NO_LUGAR"] = no_lugar
    env.update(extra or {})
    p = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", "Get-Content -LiteralPath '%s' -Raw -Encoding UTF8 | Invoke-Expression" % ps1],
        cwd=pacote, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def teste_install_no_lugar():
    secao(u"o INSTALL.ps1 no lugar: atalhos, registro e orfaos, sem copiar nada")
    base = _tmp()
    try:
        raiz = os.path.join(base, "RADIOTERAPIA_AI")
        prog = os.path.join(raiz, "LOCAL_SUITE")
        _instalacao_fantoma(prog, versao=u"8.4")
        io.open(os.path.join(prog, "radai_watcher.config"), "w").write(u"ROOT=D:\\x\n")
        io.open(os.path.join(prog, "radai_calibrator.py"), "w").write(u"# orfao\n")
        os.makedirs(os.path.join(prog, "__pycache__"))
        io.open(os.path.join(prog, "LICENCAS_ACEITAS.txt"), "w", encoding="utf-8").write(
            u"LICENCAS ACEITAS\r\n[ACEITA]   TotalSegmentator\r\n")
        pacote = os.path.join(base, "pacote_vazio")
        os.makedirs(pacote)
        rc, out = _rodar_install(prog, pacote)
        checar(u"o INSTALL.ps1 no lugar termina com 0", rc == 0, out[-600:])
        checar(u"  e diz que nao ha nada a copiar",
               u"nada a copiar" in out, out[-300:])
        checar(u"  e mostra as licencas que vieram com a instalacao",
               u"LICENCAS DOS COMPONENTES" in out)
        checar(u"nao nasceu LOCAL_SUITE dentro de LOCAL_SUITE",
               not os.path.isdir(os.path.join(prog, "LOCAL_SUITE")))
        checar(u"nenhum log de copia (robocopy nao rodou)",
               not any(f == "INSTALAR_COPIA_LOG.txt"
                       for _, _, fs in os.walk(base) for f in fs))
        checar(u"o log da instalacao mora na pasta do programa",
               os.path.isfile(os.path.join(prog, "INSTALL_LOG.txt")))
        reg = os.path.join(raiz, "_instalados.json")
        d = {}
        try:
            d = json.load(io.open(reg, encoding="utf-8"))
        except Exception:
            pass
        e = d.get("LOCAL_SUITE") or {}
        checar(u"registrado em <raiz>\\_instalados.json com o caminho e a versao",
               e.get("caminho", u"").rstrip("\\").lower() == prog.lower()
               and e.get("versao") == u"8.4", d)
        checar(u"o atalho foi criado (na raiz de teste)",
               os.path.isfile(os.path.join(raiz, "_atalhos_desktop",
                                           "Radioterapia.ai Local Suite.lnk")))
        checar(u"o orfao que nos retiramos saiu",
               not os.path.exists(os.path.join(prog, "radai_calibrator.py")))
        checar(u"o __pycache__ saiu",
               not os.path.exists(os.path.join(prog, "__pycache__")))
        checar(u"a configuracao do operador ficou intacta",
               io.open(os.path.join(prog, "radai_watcher.config")).read() == u"ROOT=D:\\x\n")
        os.remove(os.path.join(prog, "engine.py"))
        rc2, out2 = _rodar_install(prog, pacote)
        checar(u"(isca) faltando um essencial na pasta final: a instalacao PARA",
               rc2 != 0 and u"engine.py" in out2, out2[-300:])
    finally:
        shutil.rmtree(base, ignore_errors=True)


_CABECA_PS = r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$arq = '%(arq)s'
$erros = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($arq, [ref]$null, [ref]$erros)
if ($erros -and $erros.Count -gt 0) { 'PARSE:erro ' + $erros[0].Message; exit 2 }
function T { param([AllowEmptyString()][string]$Texto) return $Texto }
foreach ($n in @(%(nomes)s)) {
    $f = $ast.Find({ param($x) $x -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $x.Name -eq $n }, $true)
    if (-not $f) { 'FALTA:' + $n; exit 3 }
    . ([scriptblock]::Create($f.Extent.Text))
}
"""


def _rodar_ps(corpo, nomes, timeout=120):
    tmp = _tmp()
    try:
        alvo = os.path.join(tmp, "h.ps1")
        texto = _CABECA_PS % {
            "arq": os.path.join(RAIZ, "packager", "prepare.ps1").replace("'", "''"),
            "nomes": u", ".join(u"'%s'" % n for n in nomes)} + corpo
        io.open(alvo, "w", encoding="utf-8-sig", newline="\r\n").write(texto)
        p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", alvo], capture_output=True, timeout=timeout)
        out = (p.stdout or b"").decode("utf-8", "replace") + \
              (p.stderr or b"").decode("utf-8", "replace")
        d = {}
        for l in out.splitlines():
            if u":" in l:
                k, v = l.split(u":", 1)
                if k.isupper():
                    d[k] = v.strip()
        return d, out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_preparador_pasta_e_processo():
    secao(u"o preparador: a pasta que serve, o programa rodando e a marca antiga")
    base = _tmp()
    try:
        nova = os.path.join(base, "nova", "LOCAL_SUITE")
        vazia = os.path.join(base, "vazia"); os.makedirs(vazia)
        aceite = os.path.join(base, "aceite"); os.makedirs(aceite)
        io.open(os.path.join(aceite, "LICENCAS_ACEITAS.txt"), "w").write(u"x")
        alheia = os.path.join(base, "alheia"); os.makedirs(alheia)
        io.open(os.path.join(alheia, "planilha.xlsx"), "w").write(u"x")
        inst = os.path.join(base, "inst"); _instalacao_fantoma(inst)
        antiga = os.path.join(base, "busca", "Local_suite")
        os.makedirs(os.path.join(antiga, "python"))
        io.open(os.path.join(antiga, "radai_watcher.py"), "w").write(u"#")
        io.open(os.path.join(antiga, "python", "python.exe"), "w").write(u"x")
        meio = os.path.join(base, "meio"); os.makedirs(os.path.join(meio, "_instalacao"))
        io.open(os.path.join(meio, "_instalacao", "_motor_comecou.txt"), "w").write(u"x")
        io.open(os.path.join(meio, "lixo.bin"), "w").write(u"x")
        forjada = os.path.join(base, "forjada"); os.makedirs(os.path.join(forjada, "_instalacao"))
        io.open(os.path.join(forjada, "planilha.xlsx"), "w").write(u"x")
        venv = os.path.dirname(sys.executable)
        corpo = u"""
$script:PacoteGB = 19.0
foreach ($par in @(@('NOVA','%(nova)s'), @('VAZIA','%(vazia)s'), @('ACEITE','%(aceite)s'),
                   @('ALHEIA','%(alheia)s'), @('INST','%(inst)s'), @('ANTIGA','%(antiga)s'),
                   @('MEIO','%(meio)s'), @('FORJADA','%(forjada)s'), @('RAIZ','C:\\'))) {
    $m = PastaServeParaInstalarDireto $par[1]
    $par[0] + ':' + $(if ($m) { 'recusa ' + ($m -replace "[`r`n]+", ' ') } else { 'aceita' })
}
'GBNOVA:' + (GBnecessariosDireto '%(nova)s')
'GBINST:' + (GBnecessariosDireto '%(inst)s')
function Registrar { param($Texto, $Tipo) }
function RodarAtualizador { param($Pasta, $Extra)
    $script:Rodou += ($Extra -join ' '); $r = $script:Respostas[0]
    $script:Respostas = @($script:Respostas | Select-Object -Skip 1); return $r }
function PerguntarSeTentaDeNovo { param($Pasta) $script:Perguntou++; return $script:Tenta }
function PerguntarSeProcessando { param($Pasta) return $script:Encerra }
function FecharJanelasDoApp { $script:Janelas++; return 0 }
$script:Encerra = $false; $script:Rodou = @(); $script:Janelas = 0
$r = GarantirAppFechado '%(inst)s'
'FECHA_PROCESSANDO:' + $r + '|' + $script:Rodou.Count + '|' + $script:Janelas
$script:Encerra = $true; $script:Janelas = 0
foreach ($caso in @(@('FECHA_VAZIA', '%(vazia)s', @(0), $true),
                    @('FECHA_OK', '%(inst)s', @(0), $true),
                    @('FECHA_DENOVO', '%(inst)s', @(4, 0), $true),
                    @('FECHA_DESISTE', '%(inst)s', @(4), $false))) {
    $script:Rodou = @(); $script:Perguntou = 0
    $script:Respostas = $caso[2]; $script:Tenta = $caso[3]
    $r = GarantirAppFechado $caso[1]
    $caso[0] + ':' + $r + '|' + $script:Rodou.Count + '|' + $script:Perguntou + '|' + ($script:Rodou -join ',')
}
$env:RADAI_RAIZES_BUSCA = '%(busca)s'
$achada = AcharInstalacao
'ACHADA:' + $(if ($achada) { $achada.como + '|' + $achada.pasta } else { 'nada' })
""" % {"nova": nova, "vazia": vazia, "aceite": aceite, "alheia": alheia,
           "inst": inst, "antiga": antiga, "meio": meio, "forjada": forjada, "venv": venv,
           "busca": os.path.join(base, "busca")}
        m, out = _rodar_ps(corpo, ["MarcaDeInstalacao", "MarcaDeInstalacaoAntiga", "SobraDoPreparoAntigo",
                                   "VersaoDaPasta", "RaizesDeBusca", "AcharInstalacao",
                                   "PastaServeParaInstalarDireto", "GarantirAppFechado",
                                   "GBnecessariosDireto"])
        for k in ("NOVA", "VAZIA", "ACEITE", "INST", "ANTIGA", "MEIO"):
            checar(u"pasta %s: aceita" % k.lower(), m.get(k) == u"aceita", m.get(k) or out[-300:])
        checar(u"pasta alheia: recusada, com o nome do arquivo dela",
               (m.get(u"ALHEIA") or u"").startswith(u"recusa") and u"planilha.xlsx" in m.get(u"ALHEIA", u""),
               m.get(u"ALHEIA"))
        checar(u"raiz de disco: recusada", (m.get(u"RAIZ") or u"").startswith(u"recusa"), m.get(u"RAIZ"))
        checar(u"pasta alheia com so a oficina vazia: recusada, com o nome do arquivo dela",
               (m.get(u"FORJADA") or u"").startswith(u"recusa") and u"planilha.xlsx" in m.get(u"FORJADA", u""),
               m.get(u"FORJADA"))
        checar(u"disco pedido numa pasta nova: o programa inteiro + folga (21 GB)",
               m.get(u"GBNOVA") == u"21", m.get(u"GBNOVA"))
        checar(u"  e numa instalacao existente, so a folga (5 GB)",
               m.get(u"GBINST") == u"5", m.get(u"GBINST"))
        checar(u"pasta sem instalacao: nao ha app a encerrar, e o atualizador nem roda",
               m.get(u"FECHA_VAZIA") == u"True|0|0|", m.get(u"FECHA_VAZIA") or out[-300:])
        checar(u"instalacao: o atualizador encerra o app (-SoEncerrar) e segue",
               m.get(u"FECHA_OK") == u"True|1|0|-SoEncerrar", m.get(u"FECHA_OK"))
        checar(u"  nao conseguiu (codigo 4): pergunta, e Tentar de novo roda outra vez",
               m.get(u"FECHA_DENOVO") == u"True|2|1|-SoEncerrar,-SoEncerrar",
               m.get(u"FECHA_DENOVO"))
        checar(u"  e Cancelar para tudo, sem trocar nada",
               m.get(u"FECHA_DESISTE") == u"False|1|1|-SoEncerrar", m.get(u"FECHA_DESISTE"))
        checar(u"app processando e a pessoa nao confirma: nada e encerrado, nem a "
               u"janela, e nada e trocado", m.get(u"FECHA_PROCESSANDO") == u"False|0|0",
               m.get(u"FECHA_PROCESSANDO"))
        checar(u"a instalacao ANTIGA (sem entrega.txt) e' achada pela marca",
               (m.get(u"ACHADA") or u"").startswith(u"marca antiga|")
               and m.get(u"ACHADA", u"").lower().endswith(antiga.lower()),
               m.get(u"ACHADA") or out[-300:])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_a_busca_le_o_registro_do_pai():
    secao(u"a tela 0 le a versao do entrega.txt, e nunca o registro de dentro")
    base = _tmp()
    try:
        raiz = os.path.join(base, "RADIOTERAPIA_AI")
        prog = os.path.join(raiz, "LOCAL_SUITE")
        _instalacao_fantoma(prog, versao=u"8.4")
        io.open(os.path.join(prog, "_instalados.json"), "w", encoding="utf-8").write(
            json.dumps({"LOCAL_SUITE": {"versao": "8.3", "caminho": prog}}))
        corpo = u"""
$env:RADAI_RAIZES_BUSCA = '%(raiz)s'
$a = AcharInstalacao
'SODENTRO:' + $(if ($a) { $a.como + '|' + $a.versao + '|' + $a.pasta } else { 'nada' })
[System.IO.File]::WriteAllText('%(pai)s', '{"LOCAL_SUITE": {"versao": "8.2", "caminho": "%(prog_json)s"}}')
$a = AcharInstalacao
'COMPAI:' + $(if ($a) { $a.como + '|' + $a.versao + '|' + $a.pasta } else { 'nada' })
""" % {"raiz": raiz, "pai": os.path.join(raiz, "_instalados.json"),
           "prog_json": prog.replace("\\", "\\\\")}
        m, out = _rodar_ps(corpo, ["MarcaDeInstalacao", "MarcaDeInstalacaoAntiga",
                                   "SobraDoPreparoAntigo", "VersaoDaPasta",
                                   "RaizesDeBusca", "AcharInstalacao"])
        s = (m.get(u"SODENTRO") or u"").split(u"|")
        checar(u"so com o registro de DENTRO: ele e ignorado, e a pasta e achada pela marca",
               len(s) == 3 and s[0] == u"marca" and s[1] == u"8.4"
               and s[2].lower() == prog.lower(), m.get(u"SODENTRO") or out[-300:])
        c = (m.get(u"COMPAI") or u"").split(u"|")
        checar(u"com o registro do pai: achada por ele, e a versao e a do entrega.txt "
               u"(8.4), nem a do registro (8.2) nem a do de dentro (8.3)",
               len(c) == 3 and c[0] == u"registro" and c[1] == u"8.4"
               and c[2].lower() == prog.lower(), m.get(u"COMPAI") or out[-300:])
    finally:
        shutil.rmtree(base, ignore_errors=True)


_MOTOR_FALSO = u'''import json, os, sys
a = sys.argv[1:]
open(os.environ["RADAI_ARGV_FALSO"], "w").write(json.dumps(a))
if "--instalar" in a:
    d = a[a.index("--instalar") + 1]
    os.makedirs(os.path.join(d, "python"), exist_ok=True)
    for n in ("radai_watcher.py", "entrega.txt", os.path.join("python", "python.exe")):
        open(os.path.join(d, n), "a").close()
print("motor falso: ok")
'''


def teste_preparar_ramo_direto():
    secao(u"Preparar de verdade: o ramo direto chama o motor com --instalar, sem .zip")
    base = _tmp()
    try:
        aqui = os.path.join(base, "packager")
        os.makedirs(aqui)
        io.open(os.path.join(aqui, "configurar_ambiente.py"), "w").write(_MOTOR_FALSO)
        argv = os.path.join(base, "argv.json")
        nova = os.path.join(base, "RADIOTERAPIA_AI", "LOCAL_SUITE")
        inst = os.path.join(base, "inst", "LOCAL_SUITE")
        _instalacao_fantoma(inst, versao=u"8.3")
        alheia = os.path.join(base, "alheia")
        os.makedirs(alheia)
        io.open(os.path.join(alheia, "foto.jpg"), "w").write(u"x")

        def cenario(rot, modo, pasta, fecha=True):
            return u"""
$script:Modo = '%(modo)s'
$script:FechaOk = $%(fecha)s
$cxPasta = [pscustomobject]@{ Text = '%(pasta)s' }
$script:Ocupado = $false
$script:Chamou = @()
$script:Falhou = ''
if (Test-Path -LiteralPath '%(argv)s') { Remove-Item -LiteralPath '%(argv)s' }
Preparar
'%(rot)sFALHOU:' + ($script:Falhou -replace "[`r`n]+", ' ')
'%(rot)sCHAMOU:' + ($script:Chamou -join ',')
'%(rot)sARGV:' + $(if (Test-Path -LiteralPath '%(argv)s') { Get-Content -LiteralPath '%(argv)s' -Raw } else { '' })
'%(rot)sINST:' + $script:PastaInstalada
'%(rot)sZIP:' + @(Get-ChildItem -LiteralPath '%(base)s' -Recurse -Filter '*.zip' -ErrorAction SilentlyContinue).Count
""" % {"rot": rot, "modo": modo, "pasta": pasta, "argv": argv, "base": base,
               "fecha": u"true" if fecha else u"false"}

        corpo = u"""
$env:RADAI_ARGV_FALSO = '%(argv)s'
$script:AQUI = '%(aqui)s'
$script:Cancelar = $false
$script:BtParar = $null
$btRodar = [pscustomobject]@{ Enabled = $true }
$script:DownloadGB = 13.0; $script:PacoteGB = 19.0; $script:DiscoGB = 42.0
$script:NTarefas = '23'; $script:NModelos = '4'; $script:TamanhoDeOnde = 'teste'
$script:EstacaoFinal = $true; $script:VERSAO_INSTALADOR = '8.4'
$script:PacoteFinal = ''; $script:PastaInstalada = ''; $script:Instalado = $null
$script:Trabalho = ''; $script:ArquivoLog = ''
$abas = [pscustomobject]@{ SelectedTab = $null }; $aba4 = 'aba4'
function Registrar { param($Texto, $Tipo) }
function Falhar { param($Texto) $script:Falhou = [string]$Texto }
function Pump { }
function AnotarPastaDoOperador { param($a, $b) }
function DestinoSincroniza { param($a) return $null }
function DescreverUnidade { param($a) return 'disco local' }
function SemPastaDoOperador { param($a) return $a }
function NomeDoArquivo { param($a) if ($a) { return (Split-Path -Leaf $a) } return '' }
function GravarAceites { param($Pasta) $script:Chamou += 'aceite'
    $f = Join-Path $Pasta 'LICENCAS_ACEITAS.txt'; Set-Content -LiteralPath $f -Value 'x'; return $f }
function AcharOuBaixarPython { param($Pasta) $script:Chamou += ('python@' + (Split-Path -Leaf $Pasta)); return '%(py)s' }
function InstalarNoLugar { param($Pasta) $script:Chamou += 'instalarnolugar'; $script:PastaInstalada = $Pasta; $script:InstalouNoLugar = $true }
function InstalarAqui { param($Zip) $script:Chamou += 'instalaraqui' }
function GarantirAppFechado { param($Pasta) $script:Chamou += 'fechado'; return $script:FechaOk }
function AcharInstalacao { return $null }
function PintarEstado { }
function AtualizarConclusao { param($a, $b) $script:Chamou += 'conclusao' }
""" % {"argv": argv, "aqui": aqui, "py": sys.executable}
        corpo += cenario(u"NOVA", u"1", nova)
        corpo += cenario(u"SETE", u"7", inst)
        corpo += cenario(u"ABERTO", u"7", inst, fecha=False)
        corpo += cenario(u"ALHEIA", u"1", alheia)
        m, out = _rodar_ps(corpo, [
            "Preparar", "ModoDireto", "PastaServeParaInstalarDireto",
            "ConfirmarSeRetrocede", "PerguntaDoRetrocesso", "MarcaDeInstalacao", "MarcaDeInstalacaoAntiga", "SobraDoPreparoAntigo",
            "VersaoDaPasta", "MaisNovaQue", "ComoNumero", "GBnecessarios",
            "GBnecessariosDireto", "GBInteiro", "LinhaDeArgumentos", "AcompanharProcesso",
            "LevarDoPreparoAntigo", "ListaDePreservados"],
            timeout=180)

        def argv_de(k):
            try:
                return json.loads(m.get(k) or u"[]")
            except ValueError:
                return []
        a = argv_de(u"NOVAARGV")
        checar(u"modo 1 numa pasta nova: o motor recebe --instalar <pasta final>",
               u"--instalar" in a and a[a.index(u"--instalar") + 1] == nova
               and u"--preparo" not in a, (m.get(u"NOVAARGV"), m.get(u"NOVAFALHOU"), out[-400:]))
        checar(u"  o Python do preparo fica na oficina _instalacao, dentro da pasta",
               u"python@_instalacao" in (m.get(u"NOVACHAMOU") or u""), m.get(u"NOVACHAMOU"))
        checar(u"  e depois so' os atalhos e o registro (InstalarNoLugar), sem extrair .zip",
               u"instalarnolugar" in (m.get(u"NOVACHAMOU") or u"")
               and u"instalaraqui" not in (m.get(u"NOVACHAMOU") or u"")
               and m.get(u"NOVAZIP") == u"0", (m.get(u"NOVACHAMOU"), m.get(u"NOVAZIP")))
        a7 = argv_de(u"SETEARGV")
        checar(u"modo 7 na instalacao: --instalar <pasta>, sem --so-pacote",
               u"--instalar" in a7 and u"--so-pacote" not in a7, m.get(u"SETEARGV"))
        c7 = (m.get(u"SETECHAMOU") or u"").split(u",")
        checar(u"  e encerra o app aberto ANTES do aceite e do motor",
               u"fechado" in c7 and c7.index(u"fechado") < c7.index(u"aceite")
               and u"instalarnolugar" in c7, m.get(u"SETECHAMOU"))
        checar(u"o app que nao fecha (o operador cancelou): nada roda",
               m.get(u"ABERTOCHAMOU") == u"fechado" and not m.get(u"ABERTOARGV"),
               (m.get(u"ABERTOCHAMOU"), m.get(u"ABERTOARGV")))
        checar(u"pasta alheia: Preparar recusa ANTES do aceite e do motor",
               u"foto.jpg" in (m.get(u"ALHEIAFALHOU") or u"")
               and not m.get(u"ALHEIACHAMOU") and not m.get(u"ALHEIAARGV"),
               (m.get(u"ALHEIAFALHOU"), m.get(u"ALHEIACHAMOU")))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_instalar_no_lugar_do_preparador():
    secao(u"InstalarNoLugar de verdade: o preparador roda o INSTALL.ps1 sem copiar")
    base = _tmp()
    antes = os.environ.get("RADAI_ATALHOS_NA_RAIZ")
    os.environ["RADAI_ATALHOS_NA_RAIZ"] = "1"
    try:
        raiz = os.path.join(base, "RADIOTERAPIA_AI")
        prog = os.path.join(raiz, "LOCAL_SUITE")
        _instalacao_fantoma(prog, versao=u"8.4")
        os.makedirs(os.path.join(prog, "_instalacao"))
        io.open(os.path.join(prog, "LICENCAS_ACEITAS.txt"), "w").write(u"[ACEITA]   x\n")
        corpo = u"""
$script:AQUI = '%(aqui)s'
$script:PastaInstalada = ''
$script:Linhas = New-Object System.Collections.Generic.List[string]
function Registrar { param($Texto, $Tipo) [void]$script:Linhas.Add([string]$Texto) }
function Pump { }
InstalarNoLugar '%(prog)s'
'INST:' + $script:PastaInstalada
'LOG:' + (($script:Linhas | Where-Object { $_ -match 'nada a copiar|PRONTO' }) -join ' | ')
'SOBRA:' + (Test-Path -LiteralPath '%(saida)s')
'AMB:' + [string]$env:RADAI_INSTALAR_NO_LUGAR
""" % {"aqui": os.path.join(RAIZ, "packager"), "prog": prog,
           "saida": os.path.join(prog, "_instalacao", "_instalador_saida.txt")}
        nomes = ["InstalarNoLugar", "MarcaDeInstalacao", "RegistroDaInstalacaoConfere"]
        m, out = _rodar_ps(corpo, nomes, timeout=240)
        checar(u"a instalacao ficou marcada na pasta final",
               (m.get(u"INST") or u"").lower() == prog.lower(), (m.get(u"INST"), out[-400:]))
        for rot, script in ((u"INSTALL.ps1 que sai com 1", u"Write-Output 'parou'\r\nexit 1\r\n"),
                            (u"INSTALL.ps1 que sai com 0 sem registrar",
                             u"Write-Output 'nada'\r\nexit 0\r\n")):
            falso = os.path.join(base, "falso_%d" % len(rot))
            os.makedirs(falso)
            io.open(os.path.join(falso, "INSTALL.ps1"), "w", encoding="utf-8-sig").write(script)
            prog2 = os.path.join(base, "R%d" % len(rot), "LOCAL_SUITE")
            _instalacao_fantoma(prog2, versao=u"8.4")
            os.makedirs(os.path.join(prog2, "_instalacao"))
            c2 = u"""
$script:AQUI = '%(aqui)s'
$script:PastaInstalada = ''
$script:Linhas = New-Object System.Collections.Generic.List[string]
function Registrar { param($Texto, $Tipo) [void]$script:Linhas.Add([string]$Texto) }
function Pump { }
InstalarNoLugar '%(prog)s'
'INST:' + $script:PastaInstalada
'OKI:' + $script:InstalouNoLugar
'LOG:' + (($script:Linhas | Where-Object { $_ -match 'INSTALADO|NAO completou' }) -join ' | ')
""" % {"aqui": falso, "prog": prog2}
            m2, out2 = _rodar_ps(c2, nomes, timeout=240)
            checar(u"(isca) %s: a marca existe, e mesmo assim NAO diz INSTALADO" % rot,
                   not m2.get(u"INST") and m2.get(u"OKI") == u"False"
                   and u"NAO completou" in (m2.get(u"LOG") or u"")
                   and u"INSTALADO em" not in (m2.get(u"LOG") or u""),
                   (m2, out2[-300:]))
        checar(u"  e a saida do INSTALL.ps1 chegou ao log do preparador",
               u"nada a copiar" in (m.get(u"LOG") or u"") and u"PRONTO" in (m.get(u"LOG") or u""),
               m.get(u"LOG"))
        checar(u"  o arquivo de passagem da saida foi apagado", m.get(u"SOBRA") == u"False",
               m.get(u"SOBRA"))
        checar(u"  e as variaveis do modo no lugar nao ficaram no ambiente",
               m.get(u"AMB") == u"", m.get(u"AMB"))
        checar(u"  o atalho e o registro foram feitos",
               os.path.isfile(os.path.join(raiz, "_atalhos_desktop", "Radioterapia.ai Local Suite.lnk"))
               and os.path.isfile(os.path.join(raiz, "_instalados.json")))
    finally:
        if antes is None:
            os.environ.pop("RADAI_ATALHOS_NA_RAIZ", None)
        else:
            os.environ["RADAI_ATALHOS_NA_RAIZ"] = antes
        shutil.rmtree(base, ignore_errors=True)


def _layout_do_preparo_antigo(raiz_rt):
    pasta = os.path.join(raiz_rt, "LOCAL_SUITE")
    prep = os.path.join(pasta, "preparo")
    prog = os.path.join(prep, "LOCAL_SUITE")
    _instalacao_fantoma(prog, versao=u"8.3")
    os.makedirs(os.path.join(prep, "_montagem", "LOCAL_SUITE"))
    io.open(os.path.join(prep, "LICENCAS_ACEITAS.txt"), "w").write(u"x")
    io.open(os.path.join(prep, "_instalados.json"), "w", encoding="utf-8").write(
        json.dumps({"LOCAL_SUITE": {"versao": "8.3", "caminho": prog}}))
    return pasta, prog


def teste_instalar_traz_a_configuracao_do_preparo_antigo():
    secao(u"modo 1 sobre o preparo antigo: a configuracao vem para a pasta nova")
    base = _tmp()
    try:
        raiz_rt = os.path.join(base, "RADIOTERAPIA_AI")
        pasta, prog = _layout_do_preparo_antigo(raiz_rt)
        io.open(os.path.join(prog, "radai_watcher.config"), "w", encoding="utf-8").write(
            u"ROOT=D:\\series_da_clinica\nTPS_DESTINO=eclipse\n")
        os.makedirs(os.path.join(prog, "registro", "casos"))
        io.open(os.path.join(prog, "registro", "casos", "c.json"), "w").write(u"{}")
        io.open(os.path.join(prog, "_dados.txt"), "w").write(u"D:\\acervo\n")
        io.open(os.path.join(pasta, "_dados.txt"), "w").write(u"E:\\ja_estava\n")
        corpo = u"""
$script:Linhas = New-Object System.Collections.Generic.List[string]
function Registrar { param($Texto, $Tipo) [void]$script:Linhas.Add([string]$Texto) }
LevarDoPreparoAntigo '%(pasta)s'
'LEVADOS:' + ($script:LevadosDoPreparo -join ',')
'LOG:' + ($script:Linhas -join ' | ')
""" % {"pasta": pasta}
        m, out = _rodar_ps(corpo, ["LevarDoPreparoAntigo", "ListaDePreservados",
                                   "SobraDoPreparoAntigo", "MarcaDeInstalacao"])
        cfg = os.path.join(pasta, "radai_watcher.config")
        checar(u"o radai_watcher.config com o ROOT de antes chega a pasta nova",
               os.path.isfile(cfg) and u"series_da_clinica" in io.open(
                   cfg, encoding="utf-8").read(), (m, out[-300:]))
        checar(u"  e o registro de casos tambem",
               os.path.isfile(os.path.join(pasta, "registro", "casos", "c.json")))
        checar(u"  o que ja existia na pasta nova NAO e sobrescrito",
               io.open(os.path.join(pasta, "_dados.txt")).read().startswith(u"E:\\"))
        checar(u"  e o log diz o que veio",
               u"radai_watcher.config" in (m.get(u"LOG") or u"")
               and u"_dados.txt" not in (m.get(u"LEVADOS") or u""), m)
        checar(u"  a instalacao antiga fica intacta",
               os.path.isfile(os.path.join(prog, "radai_watcher.config")))
        ps = ler("packager", "prepare.ps1")
        checar(u"o modo 1 chama a copia antes do INSTALL.ps1",
               u"if ($script:Modo -eq '1') { LevarDoPreparoAntigo $trab }\r\n" in ps
               or u"if ($script:Modo -eq '1') { LevarDoPreparoAntigo $trab }\n" in ps)
        vazio = os.path.join(base, "sem_preparo")
        os.makedirs(vazio)
        m2, _o = _rodar_ps(corpo.replace(pasta, vazio), [
            "LevarDoPreparoAntigo", "ListaDePreservados", "SobraDoPreparoAntigo",
            "MarcaDeInstalacao"])
        checar(u"  (isca) sem o preparo antigo ao lado, nada e copiado",
               not m2.get(u"LEVADOS") and not os.path.exists(
                   os.path.join(vazio, "radai_watcher.config")), m2)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_layout_do_preparo_antigo():
    secao(u"a estacao em que a instalacao direta antiga gravou em ...\\preparo\\LOCAL_SUITE")
    C = _motor()
    base = _tmp()
    try:
        raiz_rt = os.path.join(base, "RADIOTERAPIA_AI")
        pasta, prog = _layout_do_preparo_antigo(raiz_rt)
        m = C.conferir_pasta_de_instalacao(pasta)
        checar(u"motor: a pasta padrao com a sobra «preparo» da montagem antiga e' aceita",
               m == u"", m)
        isca = os.path.join(base, "outra")
        os.makedirs(os.path.join(isca, "preparo"))
        io.open(os.path.join(isca, "preparo", "receita.docx"), "w").write(u"x")
        m = C.conferir_pasta_de_instalacao(isca)
        checar(u"  (isca) uma pasta «preparo» qualquer, sem a montagem antiga: RECUSADA",
               bool(m) and u"preparo" in m, m)
        corpo = u"""
$script:DESTINO_PADRAO = '%(pasta)s'
$env:RADAI_RAIZES_BUSCA = '%(raiz)s'
$achada = AcharInstalacao
'ACHADA:' + $(if ($achada) { $achada.como + '|' + $achada.pasta } else { 'nada' })
$script:Instalado = $achada
foreach ($md in @('1', '7')) {
    $script:Modo = $md
    'SUGERE' + $md + ':' + (PastaDoProgramaSugerida)
}
$m = PastaServeParaInstalarDireto '%(pasta)s'
'SERVE:' + $(if ($m) { 'recusa ' + ($m -replace "[`r`n]+", ' ') } else { 'aceita' })
$m = PastaServeParaInstalarDireto '%(isca)s'
'ISCA:' + $(if ($m) { 'recusa' } else { 'aceita' })
""" % {"pasta": pasta, "raiz": raiz_rt, "isca": isca}
        r, out = _rodar_ps(corpo, ["MarcaDeInstalacao", "MarcaDeInstalacaoAntiga",
                                   "SobraDoPreparoAntigo", "VersaoDaPasta",
                                   "RaizesDeBusca", "AcharInstalacao",
                                   "PastaServeParaInstalarDireto",
                                   "PastaDoProgramaSugerida"])
        checar(u"preparador: a instalacao em ...\\preparo\\LOCAL_SUITE e' achada",
               (r.get(u"ACHADA") or u"").lower().endswith(prog.lower()),
               r.get(u"ACHADA") or out[-400:])
        checar(u"  «Instalar nesta maquina» sugere a pasta de cima, e nunca a do preparo",
               (r.get(u"SUGERE1") or u"").lower() == pasta.lower(), r.get(u"SUGERE1"))
        checar(u"  «Atualizar tudo» fica na instalacao achada",
               (r.get(u"SUGERE7") or u"").lower() == prog.lower(), r.get(u"SUGERE7"))
        checar(u"  e a pasta padrao, com a sobra do preparo, e' aceita",
               r.get(u"SERVE") == u"aceita", r.get(u"SERVE"))
        checar(u"  (isca) a pasta com um «preparo» qualquer continua recusada",
               r.get(u"ISCA") == u"recusa", r.get(u"ISCA"))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_instalacao_antiga_so_pelo_atualizar_tudo():
    secao(u"a instalacao antiga (sem entrega.txt): so «Instalar / Atualizar» a alcanca")
    base = _tmp()
    try:
        antiga = os.path.join(base, "antiga")
        os.makedirs(os.path.join(antiga, "python"))
        io.open(os.path.join(antiga, "radai_watcher.py"), "w").write(u"#")
        io.open(os.path.join(antiga, "python", "python.exe"), "w").write(u"x")
        inst = os.path.join(base, "inst")
        _instalacao_fantoma(inst)
        corpo = u"""
foreach ($par in @(@('ANTIGA', '%(antiga)s'), @('COMPLETA', '%(inst)s'))) {
    $script:Instalado = @{ pasta = $par[1]; versao = ''; projeto = 'x'; como = 'marca' }
    $par[0] + ':' + (InstalacaoAntigaAchada) + '|' + [bool](RecusaDaInstalacaoAntiga $script:Instalado)
}
$script:Instalado = $null
'NADA:' + (InstalacaoAntigaAchada)
""" % {"antiga": antiga, "inst": inst}
        r, out = _rodar_ps(corpo, ["MarcaDeInstalacao", "InstalacaoAntigaAchada",
                                   "RecusaDaInstalacaoAntiga"])
        checar(u"a antiga e' reconhecida como antiga, e o desinstalar pede a marca antes",
               r.get(u"ANTIGA") == u"True|True", r.get(u"ANTIGA") or out[-300:])
        checar(u"  (isca) a completa passa", r.get(u"COMPLETA") == u"False|False",
               r.get(u"COMPLETA"))
        checar(u"  e sem instalacao achada nada e' antigo", r.get(u"NADA") == u"False",
               r.get(u"NADA"))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    fp = ler("packager", "prepare.ps1")
    checar(u"o modo «Atualizar modelos e plugins» saiu da tela 0",
           u"$btModo6" not in fp and u"--so-pacote" not in fp
           and u"'Atualizar modelos e plugins'" not in fp)
    i = fp.index(u"$btModo5.Add_Click({")
    corpo5 = fp[i:fp.index(u"\n})", i)]
    checar(u"«Desinstalar» diante da instalacao antiga pergunta e completa a marca "
           u"ANTES de chamar o desinstalador",
           u"RecusaDaInstalacaoAntiga" in corpo5 and u"CompletarMarcaParaRemover" in corpo5
           and u"'YesNo'" in corpo5
           and corpo5.index(u"CompletarMarcaParaRemover") < corpo5.index(u"JanelaDesinstalar"))
    checar(u"«Desinstalar» segue so a deteccao",
           u"$temInst = [bool]$script:Instalado\r\n" in fp
           or u"$temInst = [bool]$script:Instalado\n" in fp)
    base = _tmp()
    try:
        antiga = os.path.join(base, "Local_suite")
        os.makedirs(os.path.join(antiga, "python"))
        io.open(os.path.join(antiga, "radai_watcher.py"), "w").write(u"#")
        io.open(os.path.join(antiga, "python", "python.exe"), "w").write(u"x")
        solta = os.path.join(base, "solta")
        os.makedirs(solta)
        io.open(os.path.join(solta, "radai_watcher.py"), "w").write(u"#")
        corpo = u"""
function Registrar { param($Texto, $Tipo) }
'ANTIGA:' + (CompletarMarcaParaRemover @{ pasta = '%(antiga)s'; versao = '7.9' })
'SOLTA:' + (CompletarMarcaParaRemover @{ pasta = '%(solta)s'; versao = '' })
'MARCA:' + (MarcaDeInstalacao '%(antiga)s')
""" % {"antiga": antiga, "solta": solta}
        r, out = _rodar_ps(corpo, ["CompletarMarcaParaRemover", "MarcaDeInstalacao",
                                   "MarcaDeInstalacaoAntiga"])
        ent = os.path.join(antiga, "entrega.txt")
        checar(u"a antiga ganha o entrega.txt que falta, e o desinstalador a reconhece",
               r.get(u"ANTIGA") == u"True" and r.get(u"MARCA") == u"True"
               and u"VERSAO=7.9" in io.open(ent).read(), (r, out[-300:]))
        checar(u"  (isca) pasta so com radai_watcher.py (sem o python): nada e gravado",
               r.get(u"SOLTA") == u"False"
               and not os.path.exists(os.path.join(solta, "entrega.txt")), r)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_a_rota_da_aba1_nao_reabre_o_caminho_do_zip():
    secao(u"a resposta da aba 1 troca o modo: «Sim» nunca prepara .zip para extrair aqui")
    corpo = u"""
$bt1 = @{ Enabled = $false }
$rot1 = @{ Text = '' }
function AtualizarSugestaoPasta { }
function MarcarModo { param([string]$Qual) $script:Marcado += $Qual }
foreach ($caso in @(@('A', '2', $true), @('B', '1', $false), @('C', '2', $false),
                    @('D', '1', $true), @('E', '7', $true), @('F', '', $true))) {
    $script:Marcado = ''
    $script:Modo = $caso[1]
    $rbSim = @{ Checked = [bool]$caso[2] }
    $rbNao = @{ Checked = -not [bool]$caso[2] }
    AtualizarRota
    $caso[0] + ':' + $script:Marcado + '|' + $script:EstacaoFinal
}
"""
    r, out = _rodar_ps(corpo, ["AtualizarRota"])
    checar(u"modo 2 com «Sim — instalar aqui»: vira o modo 1 (instalacao direta)",
           (r.get(u"A") or u"").startswith(u"1|"), r.get(u"A") or out[-300:])
    checar(u"modo 1 com «Nao — maquina de passagem»: vira o modo 2",
           (r.get(u"B") or u"").startswith(u"2|"), r.get(u"B"))
    checar(u"  (isca) a resposta que ja concorda com o modo nao remarca nada",
           r.get(u"C") == u"|False" and r.get(u"D") == u"|True", (r.get(u"C"), r.get(u"D")))
    checar(u"  e os modos de atualizar nao sao trocados pela pergunta",
           r.get(u"E") == u"|True", r.get(u"E"))
    checar(u"  e sem modo a resposta escolhe o modo, como antes",
           (r.get(u"F") or u"").startswith(u"1|"), r.get(u"F"))
    fp = ler("packager", "prepare.ps1")
    checar(u"o rotulo do «Sim» nao promete pacote montado na pasta",
           u"'O pacote é montado dentro desta pasta e fica pronto para uso:'" not in fp)


def teste_conclusao_do_modo_direto_traduzida():
    secao(u"a tela de conclusao do modo direto sai no idioma escolhido")
    corpo = u"""
. '%(lang)s'
[void](Carregar-Idiomas '%(pack)s')
$txt4 = [pscustomobject]@{ Text = '' }
function CaminhoDoPrograma { return '' }
$btAbrirPrograma = [pscustomobject]@{ Visible = $false; Enabled = $false; Left = 0 }
$btAbrirPasta = [pscustomobject]@{ Visible = $false; Enabled = $false; Left = 0 }
$btFechar = [pscustomobject]@{ Visible = $false; Enabled = $false; Left = 0 }
$script:PastaInstalada = 'C:\\PASTA_DO_TESTE\\LOCAL_SUITE'
$script:PASTA_RT = 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE'
$script:EstacaoFinal = $true
foreach ($cod in @('pt-BR', 'en', 'de')) {
    $script:IdiomaAtual = $cod
    foreach ($md in @('1', '7')) {
        $script:Modo = $md
        AtualizarConclusao 'C:\\PASTA_DO_TESTE\\LOCAL_SUITE' ''
        ('TELA_' + $cod.Replace('-', '_').ToUpper() + '_' + $md) + ':' + ($txt4.Text -replace "[`r`n]+", ' ~ ')
    }
}
""" % {"lang": os.path.join(RAIZ, "packager", "languages.ps1"),
           "pack": os.path.join(RAIZ, "packager")}
    r, out = _rodar_ps(corpo, ["AtualizarConclusao", "ModoDireto"])
    pt = r.get(u"TELA_PT_BR_1") or u""
    checar(u"(isca) em portugues a conclusao diz PRONTO e o PRIMEIRO USO",
           u"INSTALADO DIRETO" in pt and u"PRIMEIRO USO" in pt, pt[:200] or out[-400:])
    marcas = (u"PRONTO", u"INSTALADO DIRETO", u"ATUALIZADOS", u"PRIMEIRO USO",
              u"Sem pacote", u"O programa está em", u"Ferramenta de apoio",
              u"O REGISTRO, PARA GUARDAR")
    for chave in (u"TELA_EN_1", u"TELA_EN_7", u"TELA_DE_1", u"TELA_DE_7"):
        t = r.get(chave) or u""
        sobra = [m for m in marcas if m in t]
        checar(u"%s: nada em portugues, e o caminho continua la" % chave,
               t and not sobra and u"PASTA_DO_TESTE" in t, (sobra, t[:160]))


def teste_retrocesso_pergunta_nos_modos_diretos():
    secao(u"instalador mais velho que a instalacao: os modos 1 e 7 perguntam antes")
    base = _tmp()
    try:
        nova = os.path.join(base, "nova")
        _instalacao_fantoma(nova, versao=u"9.1")
        igual = os.path.join(base, "igual")
        _instalacao_fantoma(igual, versao=u"8.4")
        corpo = u"""
$script:VERSAO_INSTALADOR = '8.4'
foreach ($md in @('1', '7')) {
    $script:Modo = $md
    'NOVA' + $md + ':' + ((PerguntaDoRetrocesso '%(nova)s') -replace "[`r`n]+", ' ')
    'IGUAL' + $md + ':' + ((PerguntaDoRetrocesso '%(igual)s') -replace "[`r`n]+", ' ')
}
""" % {"nova": nova, "igual": igual}
        r, out = _rodar_ps(corpo, ["PerguntaDoRetrocesso", "VersaoDaPasta",
                                   "MaisNovaQue", "ComoNumero"])
        for md in (u"1", u"7"):
            checar(u"modo %s sobre a v9.1 com o instalador v8.4: pergunta" % md,
                   u"9.1" in (r.get(u"NOVA" + md) or u""), r.get(u"NOVA" + md) or out[-300:])
            checar(u"  (isca) e sobre a mesma versao, nao pergunta",
                   r.get(u"IGUAL" + md) == u"", r.get(u"IGUAL" + md))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    fp = ler("packager", "prepare.ps1")
    i = fp.index(u"function ConfirmarSeRetrocede")
    corpo_c = fp[i:fp.index(u"\n}", i)]
    checar(u"ConfirmarSeRetrocede mostra a pergunta de PerguntaDoRetrocesso, sem atalho do modo 6",
           u"PerguntaDoRetrocesso" in corpo_c and u"'6'" not in corpo_c, corpo_c[:300])


def teste_aceite_registra_a_forma():
    secao(u"aceitar todas: cada licenca continua registrada, e o recibo diz a forma")
    fonte = ler("packager", "prepare.ps1")
    i = fonte.index(u"function GravarAceites")
    corpo = fonte[i:fonte.index(u"\nfunction ", i + 10)]
    checar(u"o LICENCAS_ACEITAS.txt diz se foi «todas de uma vez»",
           u"Forma do aceite" in corpo and u"-Name AceiteDeUmaVez" in corpo)
    checar(u"  e continua gravando uma linha por licenca",
           u"foreach ($cx in $script:CaixasLicenca)" in corpo and u"[ACEITA]" in corpo)
    base = _tmp()
    try:
        prog = os.path.join(base, "LOCAL_SUITE")
        _instalacao_fantoma(prog, versao=u"8.3")
        io.open(os.path.join(prog, "LICENCAS_ACEITAS.txt"), "w").write(u"ACEITE DA 8.3\n")
        nova = os.path.join(base, "nova")
        os.makedirs(nova)
        io.open(os.path.join(nova, "LICENCAS_ACEITAS.txt"), "w").write(u"tentativa\n")
        corpo_ps = u"""
function Idioma-Atual { return 'pt-BR' }
function FinalidadeDeclarada { return $null }
$script:CaixasLicenca = @(); $script:OpcoesLicenca = @()
$script:VERSAO = '8.4'; $script:EstacaoFinal = $true
[void](GravarAceites '%(prog)s')
[void](GravarAceites '%(nova)s')
'FEITO:ok'
""" % {"prog": prog, "nova": nova}
        r, out = _rodar_ps(corpo_ps, ["GravarAceites", "VersaoDaPasta", "MarcaDeInstalacao"])
        velhos = [n for n in os.listdir(prog) if n.startswith(u"LICENCAS_ACEITAS_v8.3_")]
        checar(u"atualizar na pasta do programa guarda o aceite anterior ao lado",
               len(velhos) == 1 and io.open(os.path.join(prog, velhos[0])).read()
               == u"ACEITE DA 8.3\n", (velhos, out[-300:]))
        checar(u"  e grava o aceite novo no nome de sempre",
               u"LICENCAS ACEITAS" in io.open(os.path.join(prog, "LICENCAS_ACEITAS.txt"),
                                              encoding="utf-8").read())
        checar(u"  (isca) numa pasta que nao e instalacao, nada vai para o lado "
               u"(a pasta tem de continuar aceita pelo motor)",
               sorted(os.listdir(nova)) == [u"LICENCAS_ACEITAS.txt", u"idioma.txt"],
               os.listdir(nova))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    j = fonte.index(u"function AceitarTodasAsLicencas")
    f = fonte[j:fonte.index(u"\n}", j)]
    checar(u"aceitar todas NAO responde pelos de uso restrito (eles pedem resposta)",
           u"OpcoesLicenca" in f and u".sim.Checked = $true" not in f, f[:200])


_CORPO_BOTAO_UNICO = u"""
$script:Ocupado = $false
$btModo5 = New-Object psobject -Property @{ Enabled = $null }
function Sessao { param($Texto) }
function PintarEstado { }
function IniciarAtualizarApp { param($Inst) $script:Cascata += [string]$Inst.pasta; return 'x' }
function MarcarModo { param($Qual) $script:Modo = $Qual }
$base = '%(base)s'
$raizes = @{ VAZIO = '%(vazio)s'; QUASE = '%(quase)s'; REGISTRO = '%(registro)s'; MARCA = '%(marca)s' }
function Rodar {
    param([string]$Prefixo)
    foreach ($caso in @('VAZIO', 'QUASE', 'REGISTRO', 'MARCA', 'APONTADA', 'SUMIU', 'OCUPADO')) {
        $env:RADAI_RAIZES_BUSCA = $raizes['VAZIO']
        if ($raizes.ContainsKey($caso)) { $env:RADAI_RAIZES_BUSCA = $raizes[$caso] }
        $script:Instalado = $null
        if ($caso -eq 'APONTADA') { $script:Instalado = @{ pasta = '%(apontada)s'; como = 'apontada' } }
        if ($caso -eq 'SUMIU') { $script:Instalado = @{ pasta = '%(sumiu)s'; como = 'apontada' } }
        $script:Ocupado = ($caso -eq 'OCUPADO')
        $script:Modo = ''
        $script:Cascata = @()
        $btModo5.Enabled = $null
        $r = InstalarOuAtualizar
        $Prefixo + $caso + ':' + $r + '|' + $script:Modo + '|' +
            ((@($script:Cascata) | ForEach-Object { $_.Replace($base, '<base>') }) -join ';') +
            '|' + $btModo5.Enabled
    }
}
Rodar ''
function InstalarOuAtualizar { MarcarModo '1'; return 'instalar' }
Rodar 'ISCA1_'
function InstalarOuAtualizar {
    if ($script:Instalado) { [void](IniciarAtualizarApp $script:Instalado); return 'atualizar' }
    MarcarModo '1'
    return 'instalar'
}
Rodar 'ISCA2_'
"""

_ESPERADO_BOTAO_UNICO = {
    u"VAZIO": u"instalar|1||False",
    u"QUASE": u"instalar|1||False",
    u"REGISTRO": u"atualizar||<base>\\outro_disco\\LOCAL_SUITE|True",
    u"MARCA": u"atualizar||<base>\\marca\\LOCAL_SUITE|True",
    u"APONTADA": u"atualizar||<base>\\apontada\\LOCAL_SUITE|True",
    u"SUMIU": u"instalar|1||False",
    u"OCUPADO": u"|||",
}


def _divergencias_do_botao(r, prefixo):
    def decisao(x):
        return (x or u"").rsplit(u"|", 1)[0]
    return [(k, r.get(prefixo + k), v) for k, v in sorted(_ESPERADO_BOTAO_UNICO.items())
            if decisao(r.get(prefixo + k)) != decisao(v)]


def teste_o_botao_unico_confere_a_instalacao():
    secao(u"«Instalar / Atualizar app nesta maquina»: confere a instalacao no clique; "
          u"com ela vai a cascata, sem ela instala tudo")
    base = _tmp()
    try:
        raiz = {}
        for caso in (u"vazio", u"quase", u"registro", u"marca"):
            raiz[caso] = os.path.join(base, caso)
            os.makedirs(raiz[caso])
        quase = os.path.join(raiz[u"quase"], u"LOCAL_SUITE")
        os.makedirs(quase)
        io.open(os.path.join(quase, u"radai_watcher.py"), u"w").write(u"#")
        json.dump({u"LOCAL_SUITE": {u"caminho": os.path.join(base, u"nao_existe", u"LOCAL_SUITE")}},
                  io.open(os.path.join(raiz[u"quase"], u"_instalados.json"), u"w", encoding=u"utf-8"))
        longe = os.path.join(base, u"outro_disco", u"LOCAL_SUITE")
        _instalacao_fantoma(longe, u"8.5")
        json.dump({u"LOCAL_SUITE": {u"caminho": longe, u"versao": u"8.5"}},
                  io.open(os.path.join(raiz[u"registro"], u"_instalados.json"), u"w", encoding=u"utf-8"))
        _instalacao_fantoma(os.path.join(raiz[u"marca"], u"LOCAL_SUITE"), u"8.5")
        apontada = os.path.join(base, u"apontada", u"LOCAL_SUITE")
        _instalacao_fantoma(apontada, u"8.5")
        q = lambda x: x.replace(u"'", u"''")
        corpo = _CORPO_BOTAO_UNICO % {
            u"base": q(base), u"vazio": q(raiz[u"vazio"]), u"quase": q(raiz[u"quase"]),
            u"registro": q(raiz[u"registro"]), u"marca": q(raiz[u"marca"]),
            u"apontada": q(apontada), u"sumiu": q(os.path.join(base, u"sumiu", u"LOCAL_SUITE"))}
        r, out = _rodar_ps(corpo, [u"MarcaDeInstalacao", u"MarcaDeInstalacaoAntiga",
                                   u"SobraDoPreparoAntigo", u"VersaoDaPasta", u"UnidadesLocais",
                                   u"RaizesDeBusca", u"AcharInstalacao",
                                   u"ConferirInstalacao", u"InstalarOuAtualizar"])
        checar(u"o harness rodou os sete casos", all(k in r for k in _ESPERADO_BOTAO_UNICO),
               out[-400:])
        for caso, oque in ((u"VAZIO", u"sem instalacao: instala tudo, sem cascata"),
                           (u"QUASE", u"registro que aponta pasta inexistente e pasta sem "
                                      u"entrega.txt nao contam: instala tudo"),
                           (u"REGISTRO", u"pelo registro unico, numa pasta fora das raizes: "
                                         u"a cascata nela"),
                           (u"MARCA", u"pela marca na pasta: a cascata nela"),
                           (u"APONTADA", u"a pasta que a pessoa apontou antes, com a marca: "
                                         u"a cascata nela"),
                           (u"SUMIU", u"a pasta apontada que sumiu nao conta: instala tudo"),
                           (u"OCUPADO", u"com outra acao em curso, nada acontece")):
            checar(u"  " + oque, r.get(caso) == _ESPERADO_BOTAO_UNICO[caso],
                   u"%s (esperava %s)" % (r.get(caso), _ESPERADO_BOTAO_UNICO[caso]))
        for pre, nome in ((u"ISCA1_", u"o «Instalar nesta maquina» antigo, que sempre instala"),
                          (u"ISCA2_", u"a decisao pela deteccao da abertura, sem conferir no clique")):
            checar(u"  (isca) %s reprova" % nome, bool(_divergencias_do_botao(r, pre)),
                   u"a versao errada passou nos mesmos casos")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    fp = ler("packager", "prepare.ps1")
    checar(u"o botao grande chama a decisao, e nao a cascata nem o modo 1 direto",
           u"$btModo1.Add_Click({ [void](InstalarOuAtualizar) })" in fp
           and u"$btModo1.Add_Click({ MarcarModo '1' })" not in fp)
    i = fp.find(u"function IniciarAtualizarApp")
    corpo_ia = fp[i:fp.find(u"\n}", i)]
    j = fp.find(u"function AtualizarApp")
    corpo_aa = fp[j:fp.find(u"\n}", j)]
    checar(u"a cascata continua encerrando o app da pasta antes de trocar codigo "
           u"(o atualizador, sem perguntar)",
           u"AtualizarApp $Inst" in corpo_ia and u"RodarAtualizador $pasta @('-SemPerguntar')" in corpo_aa)
    k = fp.find(u"if (-not (ConfirmarSeRetrocede $trab)) { return }")
    checar(u"e o instalar tudo encerra o app da pasta antes de montar nela",
           k >= 0 and u"GarantirAppFechado $trab" in fp[k:k + 200])


def main():
    teste_o_botao_unico_confere_a_instalacao()
    teste_preparador_pasta_e_processo()
    teste_a_busca_le_o_registro_do_pai()
    teste_preparar_ramo_direto()
    teste_instalar_no_lugar_do_preparador()
    teste_aceite_registra_a_forma()
    teste_layout_do_preparo_antigo()
    teste_instalar_traz_a_configuracao_do_preparo_antigo()
    teste_instalacao_antiga_so_pelo_atualizar_tudo()
    teste_conclusao_do_modo_direto_traduzida()
    teste_a_rota_da_aba1_nao_reabre_o_caminho_do_zip()
    teste_retrocesso_pergunta_nos_modos_diretos()
    teste_install_no_lugar()
    teste_pasta_de_instalacao()
    teste_motor_instala_no_lugar()
    teste_motor_recusa()
    teste_motor_atualiza_a_instalacao_antiga()
    teste_tentativa_interrompida_e_reconhecida()
    teste_a_demo_saiu_do_preparo()
    teste_modelos_que_alimentam_o_entregue()
    print(u"\n" + u"=" * 68)
    if _falhou:
        print(u"FALHOU: %d de %d checagens" % (_falhou, _ok + _falhou))
        for f in _falhas:
            print(u"  -   %s" % f)
    else:
        print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 68)
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
