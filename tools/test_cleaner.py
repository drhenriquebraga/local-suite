# -*- coding: utf-8 -*-
import ast
import io
import os
import sys

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
for c in (os.path.join(RAIZ, "app"), RAIZ):
    if os.path.exists(os.path.join(c, "radai_cleaner.py")):
        sys.path.insert(0, c)
        break

import tempfile
sys.path.insert(0, AQUI)
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_ac_limp')
os.environ.setdefault("RADAI_CALIB_DIR",
                      tempfile.mkdtemp(prefix="radai_ac_limp"))

import radai_cleaner as L

VERBOSO = "-v" in sys.argv
_R = []


def checar(nome, ok, detalhe=""):
    ok = bool(ok)
    _R.append((nome, ok, detalhe))
    if VERBOSO or not ok:
        print("  %s  %s%s" % ("OK  " if ok else "FALHA", nome,
                              ("  [%s]" % (detalhe,)) if detalhe else ""))
    return ok


def secao(t):
    print(u"\n── %s %s" % (t, u"─" * max(0, 62 - len(t))))


def teste_so_para_o_que_esta_na_lista():
    secao(u"a lista de servicos e de PERMITIDOS")
    nomes = [n for n, _ in L.SERVICOS]
    checar(u"a lista existe e nao esta vazia", len(nomes) >= 5, str(len(nomes)))
    checar(u"cada servico traz o PORQUE ao lado",
           all(len(p) > 30 for _, p in L.SERVICOS),
           u"sigla sem explicacao e uma lista que ninguem revisa")
    checar(u"e nenhum nome se repete", len(set(nomes)) == len(nomes))

    for fora in ("Vitrea", "VitreaWorkstation", "VarianDbService", "Eclipse",
                 "ARIA", "WinDefend", "Spooler", "Dnscache", "LanmanServer",
                 "", "  ", "sc", "*", "SysMain;Vitrea", "SysMain Vitrea",
                 "../SysMain", "SysMain&calc"):
        r = L.parar_servico(fora)
        checar(u"recusa parar `%s`" % (fora or u"(vazio)"),
               r.get("ok") is False, str(r.get("msg"))[:60])
        checar(u"  e diz o nome no motivo (nao um erro generico)",
               u"lista" in str(r.get("msg", "")).lower())

    checar(u"e a recusa acontece ANTES de chamar o sistema",
           u"if nome not in _NOMES_SERVICOS" in _fonte(),
           u"a trava e a primeira linha util da funcao")
    checar(u"e o nome e normalizado antes de casar com a lista",
           u'nome = str(nome or "").strip()' in _fonte(),
           u"espaco a mais nao pode virar `nao esta na lista`")


def teste_o_trabalho_clinico_nunca_e_tocado():
    secao(u"Vitrea, Varian, Eclipse e ARIA: nem tocados, nem sugeridos")
    for alvo in ("vitrea", "varian", "eclipse", "aria"):
        checar(u"`%s` esta na lista de protegidos" % alvo,
               alvo in L.PROTEGIDOS)
    for nome in ("Vitrea.exe", "VITREA.EXE", "VitreaWorkstation.exe",
                 "Eclipse.exe", "ARIA.exe", "VarianDbService.exe",
                 "radai_watcher.py", "RadioterapiaAI.exe",
                 "TotalSegmentator.exe", "MsMpEng.exe", "csrss.exe"):
        checar(u"`%s` e protegido" % nome, L._protegido(nome))
    for nome in ("chrome.exe", "notepad.exe", "OUTLOOK.EXE", "Teams.exe"):
        checar(u"`%s` NAO e protegido (ele pode ser sugerido)" % nome,
               not L._protegido(nome))
    for nome in ("Pinnacle3.exe", "OncentraPlanning.exe", "XiO.exe",
                 "iPlanRTDose.exe", "BrainlabElements.exe",
                 "PrecisionTPS.exe", "TomoTherapyPlanning.exe",
                 "LimbusContour.exe", "AutoContour.exe", "AccurayService.exe",
                 "RayStation.exe", "RayCare.exe", "RaySearchLicense.exe"):
        checar(u"`%s` e protegido (TPS de outro fabricante)" % nome,
               L._protegido(nome))

    for a in L.aplicacoes_pesadas(piso_mb=1):
        checar(u"nenhum protegido na sugestao (%s)" % a["nome"],
               not L._protegido(a["nome"]), a["nome"])

    for meu in ("radioterapia", "radai", "totalsegmentator"):
        checar(u"`%s` esta protegido de nos mesmos" % meu, meu in L.PROTEGIDOS)


_PORTAS_QUE_FECHAM = ("fechar_processos", "otimizar")


def _chamadores(arvore, alvo):
    fora = set()
    for fn in ast.walk(arvore):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for no in ast.walk(fn):
            if isinstance(no, ast.Call):
                f = no.func
                nome = (f.id if isinstance(f, ast.Name) else
                        f.attr if isinstance(f, ast.Attribute) else u"")
                if nome == alvo:
                    fora.add(fn.name)
    return fora


def teste_so_uma_porta_fecha():
    secao(u"fechar: uma porta so, e ela reclassifica no clique")
    arv = ast.parse(_fonte())
    codigo = _codigo()
    for proibido in ("taskkill", "pkill", "Stop-Process", "Stop-Service"):
        checar(u"o codigo nao chama `%s` (sem comando que esconda falha)"
               % proibido, proibido not in codigo)
    donos = set()
    for fn in ast.walk(arv):
        if isinstance(fn, ast.FunctionDef):
            for no in ast.walk(fn):
                if (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                        and no.func.attr == "TerminateProcess"):
                    donos.add(fn.name)
    checar(u"`TerminateProcess` so e chamado em `_forcar`", donos == {"_forcar"},
           str(sorted(donos)))
    checar(u"`_forcar` so e chamada por `_fechar_pid`",
           _chamadores(arv, "_forcar") == {"_fechar_pid"},
           str(sorted(_chamadores(arv, "_forcar"))))
    checar(u"`_postar_fechar` (o WM_CLOSE) so e chamada por `_fechar_pid`",
           _chamadores(arv, "_postar_fechar") == {"_fechar_pid"},
           str(sorted(_chamadores(arv, "_postar_fechar"))))
    checar(u"`_fechar_pid` so e chamada por `fechar_processos`",
           _chamadores(arv, "_fechar_pid") == {"fechar_processos"},
           str(sorted(_chamadores(arv, "_fechar_pid"))))
    fp = next(n for n in ast.walk(arv) if isinstance(n, ast.FunctionDef)
              and n.name == "fechar_processos")
    linhas = dict((getattr(n.func, "id", getattr(n.func, "attr", "")), n.lineno)
                  for n in ast.walk(fp) if isinstance(n, ast.Call))
    checar(u"`fechar_processos` classifica ANTES de fechar",
           0 < linhas.get("classificar", 0) < linhas.get("_fechar_pid", 0),
           str(linhas))
    publicas = [n for n in dir(L) if not n.startswith("_") and callable(getattr(L, n))]
    for n in publicas:
        if any(x in n.lower() for x in ("fechar", "matar", "kill", "encerrar",
                                        "terminar", "otimizar")):
            checar(u"`%s` e uma das portas declaradas (ou so le)" % n,
                   n in _PORTAS_QUE_FECHAM + ("plano_de_otimizacao",
                                              "ler_estado_otimizar"), n)
    checar(u"e o laudo nao afirma mais que «nao fecha aplicacao nenhuma»",
           u"não fecha aplicação nenhuma" not in L.AVISO_DA_LISTA
           and u"listas fechadas" in L.AVISO_DA_LISTA, L.AVISO_DA_LISTA)


def teste_para_mas_nao_desabilita():
    secao(u"parar nao e desabilitar")
    arvore = ast.parse(_fonte())
    verbos, chamados = set(), set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.List) or not no.elts:
            continue
        itens = [x.value for x in no.elts
                 if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        if not itens or itens[0].startswith(("-", "/")):
            continue
        chamados.add(itens[0])
        verbos |= set(x.lower() for x in itens[1:])
    checar(u"ele chama `sc stop`", u"stop" in verbos,
           u", ".join(sorted(verbos)) or u"(nenhum)")
    for proibido in ("config", "delete", "add", "create", "start=", "disabled",
                     "/setactive", "/f", "-force"):
        checar(u"e NAO chama `%s`" % proibido, proibido not in verbos,
               u"a estacao que o TI entrega e a que o TI encontra depois")
    checar(u"o modulo so chama LEITURA, mais o `sc stop`",
           chamados <= {"sc", "tasklist", "nvidia-smi", "powercfg", "netstat"},
           u", ".join(sorted(chamados)))


def teste_o_estado_nao_depende_do_idioma():
    secao(u"o estado sai do token, e nao do rotulo traduzido")
    fonte = _fonte()
    checar(u"nao casa com o rotulo `STATE`", u'"STATE" in' not in fonte)
    checar(u"casa com os tokens, que sao ASCII em qualquer idioma",
           u"RUNNING" in fonte and u"STOPPED" in fonte)

    est = L.estado_dos_servicos()
    checar(u"a consulta devolve uma linha por servico da lista",
           len(est) == len(L.SERVICOS), u"%d de %d" % (len(est), len(L.SERVICOS)))
    validos = {"rodando", "parado", "ausente"}
    checar(u"e todo estado e um dos tres",
           all(s["estado"] in validos for s in est),
           ", ".join(sorted(set(s["estado"] for s in est))))
    if os.name == "nt":
        ausentes = sum(1 for s in est if s["estado"] == "ausente")
        checar(u"e nem todos sao `ausente` (era o sintoma do defeito)",
               ausentes < len(est),
               u"%d de %d ausentes" % (ausentes, len(est)))


def teste_o_laudo_nao_levanta():
    secao(u"o laudo")
    d = L.laudo()
    for k in ("memoria", "servicos", "aplicacoes", "piso_mb", "aviso"):
        checar(u"o laudo traz `%s`" % k, k in d)
    m = d["memoria"]
    checar(u"a memoria vem em MB e fecha a conta",
           m["total_mb"] == 0 or
           abs((m["usada_mb"] + m["livre_mb"]) - m["total_mb"]) <= 1,
           str(m))
    checar(u"as aplicacoes vem ordenadas da maior para a menor",
           all(d["aplicacoes"][i]["memoria_mb"] >= d["aplicacoes"][i + 1]["memoria_mb"]
               for i in range(max(0, len(d["aplicacoes"]) - 1))))
    checar(u"e nenhuma abaixo do piso",
           all(a["memoria_mb"] >= d["piso_mb"] for a in d["aplicacoes"]))


class _Troca(object):
    def __init__(self, alvo, **novos):
        self.alvo, self.novos, self.velhos = alvo, novos, {}

    def __enter__(self):
        for k, v in self.novos.items():
            self.velhos[k] = getattr(self.alvo, k)
            setattr(self.alvo, k, v)
        return self

    def __exit__(self, *a):
        for k, v in self.velhos.items():
            setattr(self.alvo, k, v)
        return False


def _laudo_leve(**troca):
    base = dict(estado_dos_servicos=lambda: [], aplicacoes_pesadas=lambda *a, **k: [],
                espaco_em_disco=lambda *a, **k: [],
                espaco_recuperavel=lambda: [])
    base.update(troca)
    with _Troca(L, **base):
        return L.laudo()


def _com_config(texto):
    pasta = _cleanup.temporaria("radai_ac_limp_cfg_")
    cam = os.path.join(pasta, "radai_watcher.config")
    if texto is not None:
        io.open(cam, "w", encoding="utf-8").write(texto)
    return cam


def teste_o_device_do_config_chega_aos_ganhos():
    secao(u"o DEVICE do config chega aos ganhos")
    velho = os.environ.get("RADAI_CONFIG")
    gpu = lambda: (True, u"Quadro P2200")
    try:
        for texto, espera_cpu, rotulo in (
                (u"ROOT=\nDEVICE=auto\n", False, u"DEVICE=auto"),
                (u"﻿DEVICE=gpu   # comentario\n", False, u"DEVICE=gpu"),
                (None, False, u"sem config (o de fabrica e auto)"),
                (u"DEVICE=\n", False, u"DEVICE vazio (o de fabrica)"),
                (u"DEVICE=cpu\n", True, u"ISCA: DEVICE=cpu escrito")):
            os.environ["RADAI_CONFIG"] = _com_config(texto)
            d = _laudo_leve(_tem_gpu=gpu, _torch_do_arranque=lambda: None)
            diz = any(u"configurado para CPU" in (g.get("detalhe") or u"")
                      for g in d["ganhos"])
            checar(u"%s: %s" % (rotulo, u"diz CPU" if espera_cpu
                                else u"NAO diz «configurado para CPU»"),
                   diz == espera_cpu, str((d.get("device"), [g.get("rotulo")
                                                             for g in d["ganhos"]])))
    finally:
        if velho is None:
            os.environ.pop("RADAI_CONFIG", None)
        else:
            os.environ["RADAI_CONFIG"] = velho
    with _Troca(L, _tem_gpu=gpu, _torch_do_arranque=lambda: None):
        g = L.ganhos_de_velocidade("")
    checar(u"o vazio passado a mao tambem e o de fabrica (auto), nunca CPU",
           not any(u"configurado para CPU" in x.get("detalhe", u"") for x in g), str(g))


def teste_a_placa_que_existe_e_nomeada():
    secao(u"a placa que nao e NVIDIA e nomeada")
    iris = [{"nome": u"Intel(R) Iris(R) Xe Graphics", "vendor": "intel"},
            {"nome": u"Microsoft Remote Display Adapter", "vendor": "microsoft"}]
    with _Troca(L, _tem_gpu=lambda: (False, u""), _placas_do_windows=lambda: iris):
        g = [x for x in L.ganhos_de_velocidade("auto") if x["chave"] == "gpu"]
    checar(u"a Iris Xe aparece com «que o TotalSegmentator não usa»",
           g and u"Iris(R) Xe" in g[0]["detalhe"]
           and u"TotalSegmentator não usa" in g[0]["detalhe"], str(g))
    checar(u"  e o adaptador remoto NAO e contado como placa",
           g and u"Remote" not in g[0]["detalhe"], str(g))
    checar(u"  e o rotulo diz «NVIDIA» (a placa que falta), nao «sem GPU»",
           g and g[0]["rotulo"] == u"Sem GPU NVIDIA nesta estação", str(g))
    with _Troca(L, _tem_gpu=lambda: (False, u""), _placas_do_windows=lambda: []):
        g2 = [x for x in L.ganhos_de_velocidade("auto") if x["chave"] == "gpu"]
    checar(u"ISCA: sem placa listada, «Não achei GPU NVIDIA» e nenhum nome",
           g2 and u"Não achei GPU NVIDIA" in g2[0]["detalhe"]
           and u"não usa" not in g2[0]["detalhe"], str(g2))
    if os.name == "nt":
        real = L._placas_do_windows()
        checar(u"nesta maquina o Windows lista ao menos uma placa (CIM)",
               len(real) >= 1, str(real))


def teste_o_nvidia_smi_e_achado_e_nao_pelo_path():
    secao(u"o nvidia-smi e achado, e nao pelo PATH")
    import ast as _ast
    import radai_devices as RD
    arv = _ast.parse(_fonte())
    fn = next(n for n in _ast.walk(arv) if isinstance(n, _ast.FunctionDef)
              and n.name == "_tem_gpu")
    chama = [n.func.attr for n in _ast.walk(fn) if isinstance(n, _ast.Call)
             and isinstance(n.func, _ast.Attribute)]
    checar(u"_tem_gpu pergunta a radai_devices.placas_nvidia",
           "placas_nvidia" in chama, str(chama))
    velho = RD.placas_nvidia
    try:
        RD.placas_nvidia = lambda timeout=20: {
            "placas": [{"indice": 0, "nome": "Quadro P2000", "total_mb": 5120.0,
                        "livre_mb": 4000.0, "driver": "472.98"}], "falha": ""}
        checar(u"com a placa achada, _tem_gpu devolve o nome",
               L._tem_gpu() == (True, "Quadro P2000"), str(L._tem_gpu()))
        RD.placas_nvidia = lambda timeout=20: {"placas": [],
                                               "falha": "nvidia-smi nao encontrado"}
        checar(u"ISCA: sem placa achada, (False, '')", L._tem_gpu() == (False, ""))
    finally:
        RD.placas_nvidia = velho


def teste_a_placa_que_o_torch_nao_alcanca():
    secao(u"a GPU que o torch nao alcanca")
    tr = {"importa": True, "disponivel": False, "versao": "2.5.1+cu121",
          "cuda": "12.1"}
    with _Troca(L, _tem_gpu=lambda: (True, u"Quadro P2000"),
                _torch_do_arranque=lambda: tr):
        g = [x for x in L.ganhos_de_velocidade("auto") if x["chave"] == "gpu"]
    checar(u"o item diz que o torch nao alcanca, e aponta o driver",
           g and u"não a alcança" in g[0]["detalhe"] and u"driver" in g[0]["detalhe"]
           and u"configurado para CPU" not in g[0]["detalhe"], str(g))
    with _Troca(L, _tem_gpu=lambda: (True, u"Quadro P2000"),
                _torch_do_arranque=lambda: dict(tr, disponivel=True)):
        g2 = [x for x in L.ganhos_de_velocidade("auto") if x["chave"] == "gpu"]
    checar(u"ISCA: com o torch alcancando a placa, nenhum item de GPU", not g2, str(g2))
    with _Troca(L, _tem_gpu=lambda: (True, u"Quadro P2000"),
                _torch_do_arranque=lambda: None):
        g3 = [x for x in L.ganhos_de_velocidade("auto") if x["chave"] == "gpu"]
    checar(u"sem a sonda do arranque, calado («nao sei» nao vira conselho)",
           not g3, str(g3))


def teste_so_biblioteca_padrao():
    secao(u"so biblioteca padrao")
    fonte = _fonte()
    for pesado in ("numpy", "psutil", "fastapi", "pydicom", "SimpleITK",
                   "torch", "scipy"):
        checar(u"nao importa `%s`" % pesado,
               (u"import %s" % pesado) not in fonte)


def _arvore_velha(raiz, nome, idade_h, arquivo_novo=False):
    import time as _t
    d = os.path.join(raiz, nome)
    serie = os.path.join(d, "PAC", "CT")
    os.makedirs(serie)
    io.open(os.path.join(serie, "IM0001"), "wb").write(b"x")
    velho = _t.time() - idade_h * 3600
    for r, ds, fs in os.walk(d):
        for f in fs:
            os.utime(os.path.join(r, f), (velho, velho))
    if arquivo_novo:
        io.open(os.path.join(serie, "RS_RadAI_20260924_12345678.dcm"),
                "wb").write(b"rt")
    for r, ds, fs in sorted(os.walk(d), key=lambda x: -len(x[0])):
        os.utime(r, (velho, velho))
    return d


def _arvore_velha_somente_leitura(raiz, nome, idade_h=30):
    import stat
    import time as _t
    d = _arvore_velha(raiz, nome, idade_h)
    obj = os.path.join(d, ".git", "objects", "ab")
    os.makedirs(obj)
    f = os.path.join(obj, "cdef0123")
    io.open(f, "wb").write(b"blob")
    os.chmod(f, stat.S_IREAD)
    vazia = os.path.join(d, "skills", "evals")
    os.makedirs(vazia)
    velho = _t.time() - idade_h * 3600
    for r, ds, fs in sorted(os.walk(d), key=lambda x: -len(x[0])):
        for x in fs:
            os.utime(os.path.join(r, x), (velho, velho))
        os.utime(r, (velho, velho))
    os.chmod(vazia, stat.S_IREAD)
    return d, f


def teste_a_faxina_apaga_o_somente_leitura_e_para_no_teto():
    secao(u"a faxina apaga o objeto somente leitura e para no teto de tempo")
    import shutil
    import stat
    import radai_archive as A
    raiz = tempfile.mkdtemp(prefix="radai_ac_limp_ro_")
    try:
        isca, f_isca = _arvore_velha_somente_leitura(raiz, "isca_rmtree")
        checar(u"o objeto do fantoma e somente leitura, e a pasta vazia "
               u"tambem (a copia das skills)",
               not (os.stat(f_isca).st_mode & stat.S_IWRITE)
               and not (os.stat(os.path.join(isca, "skills", "evals"))
                        .st_mode & stat.S_IWRITE))
        try:
            shutil.rmtree(isca)
            recusou = False
        except PermissionError:
            recusou = True
        checar(u"  (isca) o rmtree simples recusa o objeto somente leitura "
               u"(o defeito, reproduzido)", recusou and os.path.exists(f_isca))
        A.apagar_arvore(isca)
        checar(u"apagar_arvore tira a pasta com o objeto somente leitura",
               not os.path.exists(isca))

        velhas = [_arvore_velha_somente_leitura(raiz, "radai_git_%d" % k)[0]
                  for k in range(3)]
        t = [0.0]

        def relogio():
            t[0] += 1.0
            return t[0]
        n, e = A.limpar_temporaria(caminho=raiz, idade_h=6, teto_s=2.5,
                                   relogio=relogio)
        sobra = [v for v in velhas if os.path.exists(v)]
        checar(u"com o teto, a faxina para no meio e o resto fica para a "
               u"proxima (2 apagadas, 1 adiada, nenhuma recusa)",
               (n, e) == (2, 0) and len(sobra) == 1, repr((n, e, sobra)))
        n2, e2 = A.limpar_temporaria(caminho=raiz, idade_h=6)
        checar(u"a proxima faxina leva o resto, com o objeto somente leitura",
               (n2, e2) == (1, 0) and not any(os.path.exists(v)
                                              for v in velhas),
               repr((n2, e2)))
        outras = [_arvore_velha_somente_leitura(raiz, "radai_git_b%d" % k)[0]
                  for k in range(3)]
        t[0] = 0.0
        n3, _e3 = A.limpar_temporaria(caminho=raiz, idade_h=6, teto_s=1e9,
                                      relogio=relogio)
        checar(u"  (isca) sem o teto apertado, a mesma faxina leva as tres",
               n3 == 3 and not any(os.path.exists(v) for v in outras),
               repr(n3))
        checar(u"o teto padrao e curto (o lote chama a faxina a cada serie)",
               0 < A.TETO_DA_FAXINA_S <= 5.0, repr(A.TETO_DA_FAXINA_S))
    finally:
        A.apagar_arvore(raiz)


def teste_a_faxina_nao_apaga_o_que_esta_em_uso():
    secao(u"as tres faxinas nao apagam o que esta em uso")
    import time as _t
    import tempfile as _tf
    import radai_archive as A
    raiz = _tf.mkdtemp(prefix="radai_ac_limp_faxina_")
    try:
        viva = _arvore_velha(raiz, "radai_zipado_viva", 30, arquivo_novo=True)
        morta = _arvore_velha(raiz, "radai_zipado_morta", 30)
        declarada = _arvore_velha(raiz, "radai_declarada", 30)
        import zipfile as _zf
        baixado = os.path.join(raiz, "downloads", "exame.zip")
        os.makedirs(os.path.dirname(baixado))
        with _zf.ZipFile(baixado, "w") as z:
            z.writestr("PAC/CT/IM0001", b"x" * 300)
        da_fila = _arvore_velha(raiz, A.nome_da_extracao_do_zip(baixado), 30)
        checar(u"a pasta de cima da viva e VELHA (e isso que enganava)",
               _t.time() - os.path.getmtime(viva) > 20 * 3600)

        checar(u"arvore com arquivo recente la dentro: em uso",
               A.pasta_temporaria_em_uso(viva, 6)[0] is True,
               A.pasta_temporaria_em_uso(viva, 6))
        checar(u"arvore toda velha: livre",
               A.pasta_temporaria_em_uso(morta, 6)[0] is False)
        A.marcar_em_uso(declarada)
        checar(u"declarada por este processo: em uso",
               A.pasta_temporaria_em_uso(declarada, 6)[0] is True)
        import radai_queue_state as QS
        QS.limpar()
        QS.pedir([{"uid": "1.2.3.4.5", "rotulo": u"serie",
                   "pasta": "PAC/CT", "zip": baixado}],
                 com_speed=False)
        velho_tmp0 = _tf.tempdir
        _tf.tempdir = raiz
        try:
            checar(u"um card de `.zip` que ainda vai rodar (pasta relativa + "
                   u"zip): a EXTRACAO dele esta em uso",
                   A.pasta_temporaria_em_uso(da_fila, 6)[0] is True,
                   A.pasta_temporaria_em_uso(da_fila, 6))
            real_px = A.pasta_da_extracao_do_zip
            A.pasta_da_extracao_do_zip = lambda *a, **k: u""
            try:
                isca = A.pasta_temporaria_em_uso(da_fila, 6)
            finally:
                A.pasta_da_extracao_do_zip = real_px
            checar(u"ISCA: sem a traducao zip -> extracao, o mesmo card NAO "
                   u"protege nada (o defeito da revisao, reproduzido)",
                   isca[0] is False, isca)
        finally:
            _tf.tempdir = velho_tmp0
        checar(u"  e com a temporaria trocada no meio (o vigia a troca no "
               u"arranque), a extracao e reconhecida pelo NOME",
               A.pasta_temporaria_em_uso(da_fila, 6)[0] is True,
               A.pasta_temporaria_em_uso(da_fila, 6))
        checar(u"  pasta relativa de card nao vira caminho (nao e lugar "
               u"nenhum)",
               "PAC/CT" not in A._pastas_da_fila_pendente(),
               A._pastas_da_fila_pendente())

        n, e = A.limpar_temporaria(caminho=raiz, idade_h=6)
        checar(u"entre pedidos: a morta sai, e so ela",
               not os.path.exists(morta) and os.path.exists(viva)
               and os.path.exists(declarada) and os.path.exists(da_fila),
               (n, e, sorted(os.listdir(raiz))))
        checar(u"  e o RTSTRUCT gravado dentro da extracao ficou",
               os.path.exists(os.path.join(
                   viva, "PAC", "CT", "RS_RadAI_20260924_12345678.dcm")))

        A.soltar_em_uso(declarada)
        QS.limpar()
        checar(u"soltas a declaracao e a fila, as duas deixam de estar em uso",
               A.pasta_temporaria_em_uso(declarada, 6)[0] is False
               and A.pasta_temporaria_em_uso(da_fila, 6)[0] is False)

        real = A.pasta_temporaria_em_uso
        A.pasta_temporaria_em_uso = lambda c, h: (False, u"")
        try:
            A.limpar_temporaria(caminho=raiz, idade_h=6)
        finally:
            A.pasta_temporaria_em_uso = real
        checar(u"ISCA: sem a regra de «em uso», a extracao com a entrega "
               u"recente SAI (o defeito, reproduzido)",
               not os.path.exists(viva), sorted(os.listdir(raiz)))
        checar(u"na duvida (teto da busca), em uso",
               A.mudou_depois(declarada, _t.time(), teto=1) is True)

        viva2 = _arvore_velha(raiz, "radai_zipado_viva2", 30, arquivo_novo=True)
        morta2 = _arvore_velha(raiz, "radai_zipado_morta2", 30)
        velho_tmp = _tf.tempdir
        _tf.tempdir = raiz
        try:
            _b, lista = L._temp_antigo()
        finally:
            _tf.tempdir = velho_tmp
        nomes = set(os.path.basename(x) for x in lista)
        checar(u"o limpador oferece a morta, e NAO a viva",
               "radai_zipado_morta2" in nomes and "radai_zipado_viva2" not in nomes,
               sorted(nomes))

        import importlib.util as _iu
        velho_env = dict(os.environ)
        cfg = os.path.join(raiz, "faxina.config")
        io.open(cfg, "w", encoding="utf-8").write(
            u"ROOT=\nLOG_DIR=%s\n" % os.path.join(raiz, "log"))
        os.environ["RADAI_CONFIG"] = cfg
        try:
            spec = _iu.spec_from_file_location(
                "vigia_faxina", _componentes.fonte("app/radai_watcher.py"))
            V = _iu.module_from_spec(spec)
            spec.loader.exec_module(V)
            _tf.tempdir = raiz
            try:
                V.wlog = lambda m="": None
                V.limpar_temporarios()
            finally:
                _tf.tempdir = velho_tmp
        finally:
            os.environ.clear()
            os.environ.update(velho_env)
        checar(u"o arranque do vigia apaga a morta e deixa a viva",
               not os.path.exists(morta2) and os.path.exists(viva2),
               sorted(os.listdir(raiz)))
    finally:
        try:
            QS.limpar()
        except Exception:
            pass
        import shutil
        shutil.rmtree(raiz, ignore_errors=True)


def teste_a_extracao_do_zip_e_a_mesma_conta_do_lote():
    secao(u"a extracao do .zip: a faxina usa a mesma conta do lote")
    import shutil
    import tempfile as _tf
    import zipfile as _zf
    import radai_archive as A
    import radai_batch as B
    raiz = _tf.mkdtemp(prefix="radai_ac_limp_extracao_")
    velho_tmp = _tf.tempdir
    try:
        zp = os.path.join(raiz, "downloads", "exame do portal.zip")
        os.makedirs(os.path.dirname(zp))
        with _zf.ZipFile(zp, "w") as z:
            z.writestr("PAC/CT/IM0001", b"x" * 300)
        os.utime(zp, (1758000000.75, 1758000000.75))
        temp = os.path.join(raiz, "temp")
        os.makedirs(temp)
        _tf.tempdir = temp
        base, erro = B.preparar_zip(zp)
        checar(u"o lote extraiu o .zip", bool(base) and not erro
               and os.path.isdir(base), (base, erro))
        checar(u"a pasta da extracao e a MESMA que a faxina calcula",
               base == A.pasta_da_extracao_do_zip(zp),
               (os.path.basename(base or u""),
                os.path.basename(A.pasta_da_extracao_do_zip(zp))))
        checar(u"  e o nome comeca pelo prefixo das extracoes",
               os.path.basename(base or u"").startswith(A.PREFIXO_DA_EXTRACAO))

        import hashlib
        real = A.nome_da_extracao_do_zip

        def _conta_sem_int(c):
            st = os.stat(c)
            return A.PREFIXO_DA_EXTRACAO + hashlib.sha1(
                ("%s|%s|%d" % (os.path.abspath(c), st.st_mtime, st.st_size))
                .encode("utf-8")).hexdigest()[:12]
        A.nome_da_extracao_do_zip = _conta_sem_int
        try:
            isca = A.pasta_da_extracao_do_zip(zp)
        finally:
            A.nome_da_extracao_do_zip = real
        checar(u"ISCA: uma conta que diverge (mtime sem `int`) da outra "
               u"pasta, e a comparacao a pega", isca != base,
               os.path.basename(isca))
        checar(u"arquivo que nao existe mais: sem nome (o lote tambem nao "
               u"reencontra a extracao sem o `stat`)",
               A.nome_da_extracao_do_zip(os.path.join(raiz, "sumiu.zip")) == u""
               and A.pasta_da_extracao_do_zip(
                   os.path.join(raiz, "sumiu.zip")) == u"")
    finally:
        _tf.tempdir = velho_tmp
        shutil.rmtree(raiz, ignore_errors=True)


_PRIMITIVOS = ("_forcar", "_postar_fechar", "_abrir_programa",
               "_esperar_saida", "_janelas_por_pid")


class _TocouNaMaquina(AssertionError):
    pass


def _rede_de_seguranca():
    def _faca(nome):
        def _f(*a, **k):
            raise _TocouNaMaquina(u"a bateria chamou `%s` de verdade" % nome)
        return _f
    for n in _PRIMITIVOS:
        setattr(L, n, _faca(n))


VIG = os.getpid()


def _p(pid, exe, ppid=100, janela=False, caminho=u"", sessao=1, mem=50):
    return {"pid": pid, "ppid": ppid, "exe": exe,
            "nome": L.nome_do_processo(exe), "caminho": caminho,
            "sessao": sessao, "janela": janela, "mem_mb": mem}


def _tabela():
    return [
        _p(100, "explorer.exe", ppid=50, janela=True,
           caminho=u"C:\\Windows\\explorer.exe"),
        _p(200, "cmd.exe", janela=True, caminho=u"C:\\Windows\\System32\\cmd.exe"),
        _p(210, "conhost.exe", ppid=200),
        _p(VIG, "python.exe", ppid=200, caminho=u"C:\\Programas\\py\\python.exe"),
        _p(300, "python.exe", ppid=VIG, caminho=u"C:\\Programas\\py\\python.exe"),
        _p(301, "ts_visor.exe", ppid=VIG, janela=True),
        _p(400, "OneDrive.exe"),
        _p(500, "cmd.exe", janela=True, caminho=u"C:\\Windows\\System32\\cmd.exe"),
        _p(600, "chrome.exe", janela=True), _p(601, "chrome.exe", ppid=600),
        _p(650, "brave.exe", janela=True),
        _p(700, "Foo.exe", janela=True), _p(701, "Bar.exe"),
        _p(800, "worker.exe", janela=True,
           caminho=u"D:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\bin\\worker.exe"),
        _p(801, "helper.exe", janela=True,
           caminho=u"C:\\RADIOTERAPIA_AI_ANTIGO\\helper.exe"),
        _p(802, "y.exe", janela=True, caminho=u"c:/radioterapia_ai/x/y.exe"),
        _p(900, "Spotify.exe", janela=True), _p(901, "Spotify.exe", ppid=900),
        _p(960, "Dropbox.exe"),
        _p(1000, "Vitrea.exe", janela=True), _p(1001, "EXCEL.EXE", janela=True),
        _p(1002, "TeamViewer.exe", janela=True), _p(1003, "MsMpEng.exe"),
        _p(1004, "Visor.exe", janela=True,
           caminho=u"C:\\Vitrea\\bin\\Visor.exe"),
        _p(1100, "OneDrive.exe", sessao=2),
        _p(1200, "RtkAudUService64.exe"),
        _p(1300, "ShellExperienceHost.exe", janela=True),
        _p(1400, "python.exe", caminho=u"C:\\dev\\.venv\\Scripts\\python.exe"),
    ]


def _itens(plano):
    return dict((str(i["nome"]).lower(), i) for i in plano.get("itens") or [])


def teste_a_arvore_do_app_nunca_entra_na_lista():
    secao(u"otimizar: a arvore do programa nunca entra na lista")
    t = _tabela()
    arv = L.arvore_do_app(t, VIG)
    checar(u"a arvore tem o vigia, o cmd que o abriu, o conhost e os filhos",
           {VIG, 200, 210, 300, 301} <= arv, sorted(arv))
    checar(u"  e NAO sobe ate o Explorer (nem pega o cmd dos outros)",
           100 not in arv and 500 not in arv and 400 not in arv, sorted(arv))
    pl = L.plano_de_otimizacao(procs=t, pid_app=VIG, admin=False,
                               com_disco=False)
    it = _itens(pl)
    for fora in ("python", "conhost", "ts_visor", "chrome", "brave", "worker",
                 "y", "bar", "vitrea", "excel", "teamviewer", "msmpeng",
                 "visor", "shellexperiencehost", "explorer"):
        checar(u"`%s` nao entra na lista do Otimizar" % fora, fora not in it,
               sorted(it))
    checar(u"o `cmd` da lista e so o dos outros (1 processo, desmarcado)",
           it.get("cmd", {}).get("n") == 1 and not it["cmd"]["marcado"],
           it.get("cmd"))
    checar(u"a sessao de outro usuario nao conta (OneDrive: 1 processo)",
           it.get("onedrive", {}).get("n") == 1, it.get("onedrive"))
    checar(u"os protegidos contam o programa, pela arvore E pelo caminho",
           pl["protegidos"].get("app", 0) == 6, pl["protegidos"])
    with _Troca(L, arvore_do_app=lambda procs, pid_app=None, **k: {VIG}):
        it2 = _itens(L.plano_de_otimizacao(procs=t, pid_app=VIG, admin=False,
                                           com_disco=False))
    checar(u"ISCA: sem a arvore, o visor do vigia e o cmd dele aparecem",
           "ts_visor" in it2 and it2.get("cmd", {}).get("n") == 2, sorted(it2))
    with _Troca(L, no_ecossistema=lambda c: False):
        it3 = _itens(L.plano_de_otimizacao(procs=t, pid_app=VIG, admin=False,
                                           com_disco=False))
    checar(u"ISCA: sem a marca de pasta, o `worker` de D:\\RADIOTERAPIA_AI "
           u"aparece", "worker" in it3, sorted(it3))


def teste_o_caminho_protege_por_componente():
    secao(u"otimizar: o caminho protege por componente de pasta")
    for c, esperado in (
            (u"C:\\RADIOTERAPIA_AI\\AUTO_CONTORNO\\python\\python.exe", True),
            (u"D:\\RADIOTERAPIA_AI\\LOCAL_SUITE\\python\\python.exe", True),
            (u"c:/radioterapia_ai/x/y.exe", True),
            (u"\\\\srv\\RADIOTERAPIA_AI\\bin\\a.exe", True),
            (u"C:\\RADIOTERAPIA_AI_ANTIGO\\a.exe", False),
            (u"C:\\Users\\usuario\\RADIOTERAPIA_AI.txt", False),
            (u"C:\\dev\\.venv\\Scripts\\python.exe", False),
            (u"", False), (None, False)):
        checar(u"%s -> %s" % (c, esperado), L.no_ecossistema(c) is esperado)
    arv = ast.parse(_fonte())
    fn = next(n for n in ast.walk(arv) if isinstance(n, ast.FunctionDef)
              and n.name == "no_ecossistema")
    usa_re = [n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)
              and isinstance(n.value, ast.Name) and n.value.id == "re"]
    checar(u"e a funcao nao usa regex (split por componente de `normpath`)",
           u"normpath" in _corpo("no_ecossistema") and not usa_re, usa_re)


def teste_o_desconhecido_nasce_desmarcado():
    secao(u"otimizar: o desconhecido com janela nasce desmarcado")
    t = _tabela()
    it = _itens(L.plano_de_otimizacao(procs=t, pid_app=VIG, admin=False,
                                      com_disco=False))
    checar(u"`Foo` (desconhecido, com janela) entra DESMARCADO",
           "foo" in it and it["foo"]["marcado"] is False
           and u"não o reconhece" in it["foo"]["nota"], it.get("foo"))
    checar(u"`Bar` (desconhecido, sem janela) nao entra",
           "bar" not in it, sorted(it))
    checar(u"`helper` de RADIOTERAPIA_AI_ANTIGO (nao e a marca) entra "
           u"desmarcado", it.get("helper", {}).get("marcado") is False,
           it.get("helper"))
    checar(u"OneDrive (catalogo Sempre) entra MARCADO",
           it.get("onedrive", {}).get("marcado") is True, it.get("onedrive"))
    checar(u"Dropbox (SemJanela, sem janela) entra MARCADO",
           it.get("dropbox", {}).get("marcado") is True, it.get("dropbox"))
    checar(u"Spotify (SemJanela) com janela aberta entra DESMARCADO",
           it.get("spotify", {}).get("marcado") is False
           and it["spotify"]["n"] == 2, it.get("spotify"))
    checar(u"a camada de audio (lista SessaoAudio) entra marcada",
           it.get("rtkauduservice64", {}).get("marcado") is True
           and it["rtkauduservice64"]["classe"] == "audio",
           it.get("rtkauduservice64"))
    checar(u"os marcados vem primeiro na lista",
           [i["marcado"] for i in L.plano_de_otimizacao(
               procs=t, pid_app=VIG, admin=False, com_disco=False)["itens"]]
           == sorted([i["marcado"] for i in L.plano_de_otimizacao(
               procs=t, pid_app=VIG, admin=False, com_disco=False)["itens"]],
               reverse=True))
    for nome, classe in (("chrome.exe", "navegador"), ("brave.exe", "navegador"),
                         ("opera.exe", "navegador"), ("vivaldi.exe", "navegador"),
                         ("msedge.exe", "navegador")):
        c = L.classificar(_p(5000, nome, janela=True), (), 1, VIG)
        checar(u"`%s` e navegador (nunca tocado)" % nome,
               c["classe"] == classe and not c["fecha"], c)
    with _Troca(L, NAVEGADORES=()):
        c = L.classificar(_p(5000, "brave.exe", janela=True), (), 1, VIG)
    checar(u"ISCA: sem a lista de navegadores, o brave cai em outra classe "
           u"(a checagem enxerga a precedencia)", c["classe"] != "navegador", c)
    cat = L.WSRT_CATALOGO + (("^Foo$", "Sempre", u"Foo", u""),)
    with _Troca(L, WSRT_CATALOGO=cat):
        it4 = _itens(L.plano_de_otimizacao(procs=t, pid_app=VIG, admin=False,
                                           com_disco=False))
    checar(u"ISCA: o mesmo Foo num catalogo Sempre vem marcado",
           it4.get("foo", {}).get("marcado") is True, it4.get("foo"))


class _Gravador(object):
    def __init__(self, resposta=None):
        self.chamadas = []
        self.resposta = resposta or {"ok": True, "como": u"fechado pela janela"}

    def __call__(self, *a, **k):
        self.chamadas.append((a, k))
        return self.resposta


def teste_fechar_refaz_a_classificacao_e_nunca_o_proprio_pid():
    secao(u"otimizar: fechar reclassifica no clique, e nunca o proprio PID")
    t = _tabela()
    g = _Gravador()
    linhas = []
    with _Troca(L, _fechar_pid=g):
        r = L.fechar_processos(
            ["python", "cmd", "OneDrive", "chrome", "Foo", "Bar", "Inexistente",
             "ts_visor"], procs_fn=lambda: t, pid_app=VIG, log=linhas.append)
    fechados = sorted(a[0]["pid"] for a, _k in g.chamadas)
    checar(u"fecha so o cmd dos outros, o OneDrive desta sessao e o Foo",
           fechados == [400, 500, 700], fechados)
    for pid in (VIG, 200, 210, 300, 301, 600, 601, 701, 1100, 1400):
        checar(u"PID %d nao foi fechado" % pid, pid not in fechados)
    n_proc = sum(1 for p in t if p["nome"].lower() in
                 ("python", "cmd", "onedrive", "chrome", "foo", "bar",
                  "ts_visor"))
    checar(u"uma linha de log POR PROCESSO (e uma para o que nao estava aberto)",
           len(linhas) == n_proc + 1
           and any(u"inexistente já não estava aberto" in x for x in linhas),
           u"%d linhas para %d processos" % (len(linhas), n_proc))
    checar(u"a linha de quem ficou diz o motivo (o proprio PID)",
           any(u"PID %d) ficou aberto — é este programa" % VIG in x
               for x in linhas), [x for x in linhas if str(VIG) in x])
    checar(u"  e o filho do vigia diz que e do programa",
           any(u"PID 300) ficou aberto — faz parte do Radioterapia.AI" in x
               for x in linhas), [x for x in linhas if u"PID 300" in x])
    checar(u"o resumo devolve os nomes fechados, sem repetir",
           r["fechados"] == ["cmd", "Foo", "OneDrive"], r["fechados"])
    g2 = _Gravador()
    tudo = lambda p, *a, **k: {"classe": "x", "fecha": True, "marcado": True,
                                "rotulo": u"", "nota": u""}
    with _Troca(L, _fechar_pid=g2, classificar=tudo):
        L.fechar_processos(["python"], procs_fn=lambda: t, pid_app=VIG)
    checar(u"ISCA: sem a classificacao no clique, o proprio vigia seria fechado",
           VIG in [a[0]["pid"] for a, _k in g2.chamadas])
    marcas = []
    with _Troca(L, _janelas_por_pid=lambda: marcas.append("j") or {},
                _postar_fechar=lambda h: marcas.append("p"),
                _esperar_saida=lambda pid, s: marcas.append("e") or True,
                _forcar=lambda pid: marcas.append("f") or {"ok": True,
                                                            "como": u"forçado"}):
        r1 = L._fechar_pid({"pid": VIG})
        antes = list(marcas)
        r2 = L._fechar_pid({"pid": 99999})
    checar(u"`_fechar_pid` recusa o proprio PID sem chamar primitivo nenhum",
           r1["ok"] is False and antes == [], (r1, antes))
    checar(u"ISCA: para um PID qualquer, os primitivos (dublados) sao chamados",
           r2["ok"] is True and "f" in marcas, (r2, marcas))


def teste_servico_so_com_administrador():
    secao(u"otimizar: servico do Windows so com administrador")
    velho = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = _cleanup.temporaria("radai_ac_limp_lad_")
    try:
        g, linhas = _Gravador({"ok": True, "msg": u"SysMain: parado."}), []
        with _Troca(L, parar_servico=g, _fechar_pid=_Gravador()):
            r = L.otimizar([], ["SysMain"], [], log=linhas.append, admin=False,
                           procs_fn=lambda: _tabela(), pid_app=VIG)
        checar(u"sem admin: nenhum `sc stop`", g.chamadas == [], g.chamadas)
        checar(u"  e o log diz que so os processos foram tocados",
               any(u"sem administrador" in x for x in linhas), linhas)
        checar(u"  e o resumo diz admin=False", r.get("admin") is False, r)
        pl = L.plano_de_otimizacao(procs=_tabela(), pid_app=VIG, admin=False,
                                   com_disco=False)
        checar(u"o plano sem admin nao oferece servico e explica",
               pl["servicos"] == [] and u"Sem administrador" in pl["aviso_servicos"],
               (pl["servicos"], pl["aviso_servicos"]))
        with _Troca(L, parar_servico=g, _fechar_pid=_Gravador()):
            r2 = L.otimizar([], ["SysMain"], [], log=linhas.append, admin=True,
                            procs_fn=lambda: _tabela(), pid_app=VIG)
        checar(u"ISCA: com admin, o mesmo pedido chega ao `parar_servico`",
               len(g.chamadas) == 1 and r2["servicos_parados"] == ["SysMain"],
               (g.chamadas, r2))
        with _Troca(L, estado_dos_servicos=lambda: [
                {"nome": "SysMain", "porque": "x", "estado": "rodando"},
                {"nome": "WSearch", "porque": "y", "estado": "parado"}]):
            pl2 = L.plano_de_otimizacao(procs=_tabela(), pid_app=VIG,
                                        admin=True, com_disco=False)
        checar(u"com admin o plano oferece so o servico que esta rodando",
               [s["nome"] for s in pl2["servicos"]] == ["SysMain"], pl2["servicos"])
        checar(u"o registro do Restaurar guarda o servico que NOS paramos",
               L.ler_estado_otimizar().get("servicos") == ["SysMain"],
               L.ler_estado_otimizar())
    finally:
        if velho is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = velho


def teste_restaurar_reabre_o_que_tem_mapa():
    secao(u"restaurar: reabre o que tem mapa, e diz o resto")
    raiz = _cleanup.temporaria("radai_ac_limp_rest_")
    guardado = dict((k, os.environ.get(k)) for k in
                    ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"))
    os.environ["LOCALAPPDATA"] = os.path.join(raiz, "lad")
    os.environ["ProgramFiles"] = os.path.join(raiz, "pf")
    os.environ.pop("ProgramFiles(x86)", None)
    try:
        for v in ("9.0.1.0", "10.0.2.0", "130.0.2.0"):
            d = os.path.join(raiz, "pf", "Google", "Drive File Stream", v)
            os.makedirs(d)
            io.open(os.path.join(d, "GoogleDriveFS.exe"), "wb").write(b"")
        vs = [os.path.basename(os.path.dirname(x)) for x in L._versoes_do_drive()]
        checar(u"as versoes do Drive vem da mais nova para a mais velha",
               vs == ["130.0.2.0", "10.0.2.0", "9.0.1.0"], vs)
        checar(u"ISCA: por texto, a ordem seria outra",
               sorted(vs, reverse=True) != vs, sorted(vs, reverse=True))
        L._gravar_estado_otimizar({"fechados": ["GoogleDriveFS", "OneDrive",
                                                "Spotify"], "servicos": []})
        tentou = []

        def _abrir(exe, args):
            tentou.append(os.path.basename(os.path.dirname(exe)))
            return "10.0" in exe

        linhas = []
        with _Troca(L, _abrir_programa=_abrir):
            r = L.restaurar(log=linhas.append, admin=False,
                            procs_fn=lambda: [])
        checar(u"tentou a 130 e depois a 10 (parou quando abriu)",
               tentou == ["130.0.2.0", "10.0.2.0"], tentou)
        checar(u"o Google Drive foi reaberto", r["reabertos"] == [u"Google Drive"],
               r)
        checar(u"o OneDrive sem executavel manda abrir pelo menu Iniciar",
               r["nao_achados"] == [u"OneDrive"], r)
        checar(u"o Spotify volta no logon, e o log diz",
               r["no_logon"] == ["Spotify"]
               and any(u"próximo logon" in x for x in linhas), (r, linhas))
        checar(u"o registro sai depois de restaurar",
               L.ler_estado_otimizar() == {}, L.ler_estado_otimizar())
        L._gravar_estado_otimizar({"fechados": ["GoogleDriveFS"]})
        tentou[:] = []
        with _Troca(L, _abrir_programa=_abrir):
            r2 = L.restaurar(admin=False, procs_fn=lambda: [
                _p(7, "GoogleDriveFS.exe")])
        checar(u"o que ja esta aberto nao e aberto de novo",
               tentou == [] and r2["reabertos"] == [], (tentou, r2))
    finally:
        for k, v in guardado.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


_NETSTAT = u"""
Conexões ativas

  Proto  Endereço local         Endereço externo       Estado         PID
  TCP    127.0.0.1:8777         0.0.0.0:0              LISTENING       %(vig)d
  TCP    127.0.0.1:53211        127.0.0.1:8777         ESTABLISHED     601
  TCP    127.0.0.1:8777         127.0.0.1:53211        ESTABLISHED     %(vig)d
  TCP    [::1]:5000             [::1]:8777             ESTABELECIDA    650
  TCP    127.0.0.1:5001         127.0.0.1:8778         ESTABLISHED     700
  TCP    127.0.0.1:5002         127.0.0.1:8777         TIME_WAIT       0
  UDP    127.0.0.1:8777         *:*                                    960
""" % {"vig": VIG}

_CHAVES_EM_USO = {"versao", "app", "atualizado", "pids", "porta", "segmentando"}


def _formato_em_uso(d):
    import datetime as _dt
    ruins = []
    if set(d) != _CHAVES_EM_USO:
        ruins.append(u"chaves %s" % sorted(set(d) ^ _CHAVES_EM_USO))
    if d.get("versao") != 1:
        ruins.append(u"versao")
    if d.get("app") != "radioterapia-ai-local-suite":
        ruins.append(u"app")
    try:
        q = _dt.datetime.fromisoformat(str(d.get("atualizado")))
        if q.tzinfo is None:
            ruins.append(u"atualizado sem fuso")
    except Exception:
        ruins.append(u"atualizado ilegivel")
    if not (isinstance(d.get("pids"), list)
            and all(isinstance(x, int) and x > 0 for x in d["pids"])):
        ruins.append(u"pids")
    if not isinstance(d.get("porta"), int) or isinstance(d.get("porta"), bool):
        ruins.append(u"porta")
    if not isinstance(d.get("segmentando"), bool):
        ruins.append(u"segmentando")
    return ruins


def teste_o_arquivo_de_sinalizacao():
    secao(u"em_uso.json: o formato combinado, e ele some na saida")
    import json
    def _janela_cobre(renovar_s):
        return (float(renovar_s) * int(L.RENOVACOES_NA_JANELA)
                <= float(L.JANELA_DO_KIT_S))
    checar(u"a janela do kit (%d s) cobre ao menos %d renovacoes de %d s"
           % (L.JANELA_DO_KIT_S, L.RENOVACOES_NA_JANELA, L.RENOVAR_EM_USO_S),
           _janela_cobre(L.RENOVAR_EM_USO_S) and L.RENOVAR_EM_USO_S > 0,
           str(L.RENOVAR_EM_USO_S))
    checar(u"  ISCA: renovar a cada 120 s (2,5 por janela) e acusado",
           not _janela_cobre(120))
    checar(u"  e o contrato continua 5 min e 3 renovacoes (mudou: avise o kit)",
           L.JANELA_DO_KIT_S == 300 and L.RENOVACOES_NA_JANELA == 3)
    velho = os.environ.get("LOCALAPPDATA")
    base = _cleanup.temporaria("radai_ac_limp_uso_")
    os.environ["LOCALAPPDATA"] = base
    try:
        nav = L.navegadores_conectados(8777, procs=_tabela(),
                                       saida_netstat=_NETSTAT)
        checar(u"o netstat acha o navegador conectado (IPv4 e IPv6) e sobe ao "
               u"processo principal de mesmo nome",
               nav == [600, 601, 650], nav)
        checar(u"  e nao pega o proprio servidor, outra porta nem o PID 0",
               VIG not in nav and 700 not in nav and 0 not in nav, nav)
        checar(u"netstat que falhou (codigo de saida) nao inventa PID",
               L.navegadores_conectados(8777, procs=_tabela(),
                                        saida_netstat=u"") == [])
        cam = L.caminho_em_uso()
        checar(u"o endereco e %LOCALAPPDATA%\\RADIOTERAPIA_AI\\em_uso.json",
               cam == os.path.join(base, "RADIOTERAPIA_AI", "em_uso.json"), cam)
        ok = L.gravar_em_uso(8777, True, pid_app=VIG, procs=_tabela(),
                             saida_netstat=_NETSTAT)
        d = json.load(io.open(cam, encoding="utf-8")) if ok else {}
        checar(u"o vigia grava o arquivo", ok and os.path.isfile(cam), cam)
        checar(u"o formato e o combinado (6 chaves, tipos certos)",
               _formato_em_uso(d) == [], _formato_em_uso(d))
        checar(u"os pids: o vigia, o cmd, o conhost, os filhos e o navegador",
               {VIG, 200, 210, 300, 301, 600, 601, 650} <= set(d.get("pids") or []),
               d.get("pids"))
        checar(u"  e nada de fora (explorer, o cmd dos outros, o Foo)",
               not ({100, 500, 700} & set(d.get("pids") or [])), d.get("pids"))
        checar(u"nada de paciente: so os dois textos combinados",
               [k for k, v in d.items() if isinstance(v, str)]
               in (["app", "atualizado"], ["atualizado", "app"]), sorted(d))
        checar(u"segmentando e a porta como pedidos",
               d.get("segmentando") is True and d.get("porta") == 8777, d)
        checar(u"ISCA: uma chave a mais reprova o formato",
               _formato_em_uso(dict(d, root=u"x")) != [])
        checar(u"apagar na saida limpa: o arquivo some",
               L.apagar_em_uso() is True and not os.path.exists(cam))
        checar(u"  e apagar de novo nao levanta (idempotente)",
               L.apagar_em_uso() is True)
        falso = os.path.join(base, "sou_arquivo")
        io.open(falso, "wb").write(b"x")
        os.environ["LOCALAPPDATA"] = falso
        try:
            r = L.gravar_em_uso(8777, False, pid_app=VIG, procs=_tabela(),
                                saida_netstat=u"")
            checar(u"com a pasta impossivel, gravar devolve False sem levantar",
                   r is False)
        except Exception as e:
            checar(u"com a pasta impossivel, gravar devolve False sem levantar",
                   False, repr(e))
        os.environ.pop("LOCALAPPDATA", None)
        checar(u"sem LOCALAPPDATA: sem endereco e sem gravar",
               L.caminho_em_uso() == u"" and L.gravar_em_uso(
                   8777, False, procs=_tabela(), saida_netstat=u"") is False)
    finally:
        if velho is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = velho


def teste_o_diagnostico_vira_linhas_de_log():
    secao(u"diagnosticar: o relatorio vira linhas de log")
    cf = {"secoes": [{"titulo": u"Pesos", "itens": [
        {"nome": u"total_v3", "ok": True, "valor": u"ok", "grave": True},
        {"nome": u"trunk_cavities", "ok": False, "valor": u"ausente",
         "grave": True},
        {"nome": u"alcance", "ok": None, "valor": u"", "grave": False,
         "nota": True}]}], "resumo": {"ok": 1, "faltam": 1, "avisos": 0}}
    ld = {"memoria": {"total_mb": 16000, "livre_mb": 4000, "pct": 75},
          "disco": [{"unidade": "C:", "livre_gb": 10.0, "total_gb": 500.0,
                     "aperta": True}], "ganhos": [], "aplicacoes": [],
          "servicos": [{"nome": "SysMain", "estado": "rodando"}]}
    pl = L.plano_de_otimizacao(procs=_tabela(), pid_app=VIG, admin=False,
                               com_disco=False)
    L_ = L.linhas_do_diagnostico(cf, ld, pl, {"pids": [1, 2], "atualizado": u"x"})
    checar(u"todas as linhas comecam por `diagnostico:`",
           all(x.startswith(u"diagnostico: ") for x in L_), L_[:3])
    checar(u"comeca e termina marcado", u"começo" in L_[0] and u"fim" in L_[-1])
    checar(u"o que falta aparece como FALTA",
           any(u"[FALTA] Pesos — trunk_cavities" in x for x in L_))
    checar(u"a nota de alcance nao vira achado",
           not any(u"alcance" in x for x in L_))
    checar(u"memoria, disco apertado, servicos e o que o Otimizar fecharia",
           any(u"4000 MB livres" in x for x in L_)
           and any(u"aperta" in x for x in L_)
           and any(u"SysMain" in x for x in L_)
           and any(u"fecharia" in x for x in L_), L_)
    checar(u"nenhuma linha leva a palavra que pinta de vermelho a barra "
           u"(«erro», «falhou», «nao consegui»)",
           not any(p in x.lower() for x in L_
                   for p in (u"erro", u"falhou", u"não consegui"))
           , [x for x in L_ if u"erro" in x.lower()])


def _achar_ps1_do_workstation():
    env = os.environ.get("RADAI_WSRT_PS1")
    if env:
        return env if os.path.isfile(env) else u""
    bases = [RAIZ]
    g = os.path.join(RAIZ, ".git")
    if os.path.isfile(g):
        try:
            txt = io.open(g, encoding="utf-8").read().strip()
            if txt.startswith("gitdir:"):
                gd = os.path.normpath(txt.split(":", 1)[1].strip())
                partes = gd.split(os.sep)
                if ".git" in partes:
                    bases.append(os.sep.join(partes[:partes.index(".git")]))
        except Exception:
            pass
    for b in bases:
        d = os.path.abspath(b)
        for _ in range(6):
            c = os.path.join(d, "REDE_AMERICAS", "WORKSTATION_RT",
                             "Arquivo_KitSuporteRT.ps1")
            if os.path.isfile(c):
                return c
            pai = os.path.dirname(d)
            if pai == d:
                break
            d = pai
    return u""


def _sem_comentario_ps1(linha):
    aspa = None
    for k, ch in enumerate(linha):
        if aspa:
            if ch == aspa:
                aspa = None
        elif ch in u"'\"":
            aspa = ch
        elif ch == u"#":
            return linha[:k]
    return linha


def _variavel_ps1(texto, nome, _visto=None):
    import re as _re
    _visto = set(_visto or ())
    m = _re.search(r"(?m)^" + _re.escape(nome) + r"\s*=", texto)
    if not m:
        raise KeyError(nome)
    expr, i = u"", m.end()
    for linha in texto[i:].splitlines():
        linha = _sem_comentario_ps1(linha)
        if not linha.strip():
            continue
        expr += linha + u"\n"
        s = expr.strip()
        if s and not s.endswith(u"+"):
            break
    fora = u""
    for m2 in _re.finditer(r"'((?:[^']|'')*)'|\$script:(\w+)", expr):
        if m2.group(1) is not None:
            fora += m2.group(1).replace(u"''", u"'")
        else:
            ref = u"$script:" + m2.group(2)
            if ref in _visto:
                raise ValueError(ref)
            fora += _variavel_ps1(texto, ref, _visto | {nome})
    return fora


def _catalogo_ps1(texto):
    import re as _re
    i = texto.index(u"function Get-CatalogoProcessos")
    j = texto.index(u"\n}", i)
    return set((m.group(1), m.group(2)) for m in _re.finditer(
        r"Padrao\s*=\s*'((?:[^']|'')*)';.*?Nivel\s*=\s*'(\w+)'",
        texto[i:j]))


def _divergencia(nossa, deles):
    a, b = set(nossa), set(deles)
    return sorted(a - b), sorted(b - a)


def _falta_descoberta(nossa, falta):
    # GUARDA: item do .ps1 que a nossa lista ja casa por outro padrao (a
    # busca e por regex sem distincao de caixa) continua protegido.
    return [x for x in falta
            if not (_re_simples(x) and L._casa(tuple(nossa), x))]


def _re_simples(x):
    return bool(x) and all(c.isalnum() or c in u"_-" for c in x)


def _grupos_do_otimizar(painel, modulo):
    import re as _re
    m = _re.search(r"fetch\('/api/otimizar/aplicar'.*?JSON\.stringify\(\{([^}]*)\}",
                   painel, _re.S)
    js = set(_re.findall(r"(\w+)\s*:", m.group(1))) if m else None
    i = painel.index("async def _api_otimizar_aplicar")
    j = painel.index("@app.", i)
    rota = set(_re.findall(r"_lista\(\"(\w+)\"\)", painel[i:j]))
    arv = ast.parse(modulo)
    fn = next(n for n in ast.walk(arv) if isinstance(n, ast.FunctionDef)
              and n.name == "otimizar")
    params = [a.arg for a in fn.args.args][:3]
    NAO_EXECUTA = {"len", "_log", "str", "list", "tuple", "sorted", "set"}

    def _nomes_diretos(expr):
        if isinstance(expr, ast.Name):
            return {expr.id}
        if isinstance(expr, ast.BoolOp):
            return set().union(*[_nomes_diretos(v) for v in expr.values])
        return set()
    usados = set()
    for n in ast.walk(fn):
        if isinstance(n, (ast.For, ast.comprehension)):
            usados |= _nomes_diretos(n.iter) & set(params)
        elif isinstance(n, ast.Call):
            f = n.func
            nome_f = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
            if nome_f in NAO_EXECUTA:
                continue
            for a in list(n.args) + [k.value for k in n.keywords]:
                usados |= _nomes_diretos(a) & set(params)
    if not js or not rota or not params:
        raise ValueError(u"um elo da corrente do Otimizar nao foi achado")
    return {"js": js, "rota": rota, "executor": set(params), "usados": usados}


def teste_o_plano_e_o_executor_se_cobrem_nos_dois_sentidos():
    secao(u"(4c) a corrente do Otimizar confere nos dois sentidos")
    pasta = os.path.dirname(os.path.abspath(L.__file__))
    painel = io.open(os.path.join(pasta, "radai_panel.py"),
                     encoding="utf-8").read()
    modulo = _fonte()
    g = _grupos_do_otimizar(painel, modulo)
    checar(u"a tela manda exatamente o que a rota repassa",
           g["js"] == g["rota"], u"%s x %s" % (sorted(g["js"]), sorted(g["rota"])))
    checar(u"  e a rota repassa exatamente o que o executor recebe",
           g["rota"] == g["executor"],
           u"%s x %s" % (sorted(g["rota"]), sorted(g["executor"])))
    checar(u"  e o executor USA cada grupo numa chamada (nenhum ignorado)",
           g["usados"] == g["executor"],
           u"sem uso: %s" % sorted(g["executor"] - g["usados"]))
    checar(u"  e os tres grupos do plano estao na corrente",
           g["executor"] == {"nomes", "servicos", "discos"}, sorted(g["executor"]))
    sem_rota = painel.replace(u'_lista("discos")', u'[]', 1)
    gi = _grupos_do_otimizar(sem_rota, modulo)
    checar(u"ISCA: a rota que deixa de repassar o disco e acusada",
           gi["js"] != gi["rota"] and gi["rota"] != gi["executor"])
    sem_uso = modulo.replace(u"for chave in discos or ():",
                             u"for chave in ():", 1)
    gu = _grupos_do_otimizar(painel, sem_uso)
    checar(u"ISCA: o executor que recebe o disco e nao o usa e acusado",
           gu["usados"] != gu["executor"], sorted(gu["usados"]))


def teste_as_listas_nao_casam_por_acidente():
    secao(u"(4b) as listas nao casam por acidente, e a cultura nao decide")
    import re as _re
    for nome in sorted(L.ORIGEM_WSRT):
        if nome == "WSRT_CATALOGO":
            itens = [p for p, _n, _r, _o in L.WSRT_CATALOGO]
        else:
            itens = list(getattr(L, nome))
        ruins = [x for x in itens if not x or not str(x).strip()
                 or u"||" in x or x.startswith(u"|") or x.endswith(u"|")]
        checar(u"%s: nenhum item vazio, sem `||` e sem `|` na ponta" % nome,
               not ruins, str(ruins[:5]))
        nao_compila = []
        for x in itens:
            try:
                _re.compile(x)
            except _re.error:
                nao_compila.append(x)
        checar(u"  e cada item compila", not nao_compila, str(nao_compila))
        checar(u"  e a lista nao casa um nome inventado",
               not L._casa(tuple(itens), u"ProcessoInventadoQXZ7"))
    soltos = [x for n in L.ORIGEM_WSRT if n != "WSRT_CATALOGO"
              for x in getattr(L, n)
              if _re.search(r"(?<![\^\w])Epic(?!Systems|Games)", x)]
    soltos += [p for p, _n, _r, _o in L.WSRT_CATALOGO
               if _re.search(r"(?<![\^\w])Epic(?!Systems|Games)", p)]
    checar(u"nenhum `Epic` solto (so ^Epic$, EpicSystems ou ^EpicGames)",
           not soltos, str(soltos))
    checar(u"a lista de jogos nao casa o prontuario (EpicSystems, Epic)",
           not L._casa((u"^Steam|^EpicGames",), u"EpicSystems")
           and not L._casa((u"^Steam|^EpicGames",), u"Epic"))
    checar(u"«preservar» casa o prontuario Epic",
           L._casa(L.WSRT_SESSAO_PRESERVAR, u"Epic")
           and L._casa(L.WSRT_SESSAO_PRESERVAR, u"EpicSystems"))
    for padrao, nome in ((u"wfica32", u"WFICA32"), (u"Citrix", u"CITRIX"),
                         (u"WFICA32", u"wfica32"), (u"sqlservr", u"SQLSERVR")):
        checar(u"`%s` casa `%s` (a cultura nao decide)" % (padrao, nome),
               L._casa((padrao,), nome))
    regex = L._regex((u"wfica32",))
    checar(u"  e a regex e sem distincao de maiuscula, sem LOCALE",
           bool(regex.flags & _re.IGNORECASE)
           and not (regex.flags & getattr(_re, "LOCALE", 0)))


def teste_as_listas_batem_com_o_workstation_rt():
    secao(u"(4) as listas batem com o .ps1 do Workstation RT")
    coberta = _falta_descoberta(("Vitrea", r"\\Patients\\"),
                                ["VitreaQualquer", "Mirada", r"\\Patients$"])
    checar(u"o item do .ps1 que a nossa lista ja casa nao e' falta, e o que "
           u"ela nao casa continua sendo (isca: Mirada e a regex)",
           coberta == ["Mirada", r"\\Patients$"], coberta)
    ps1 = _achar_ps1_do_workstation()
    if not ps1:
        print(u"  PULADO  o .ps1 do Workstation RT nao existe nesta maquina "
              u"(na estacao de campo, nunca existe)")
        return
    texto = io.open(ps1, encoding="utf-8-sig", errors="replace").read()
    for nome_py, (var, linha) in sorted(L.ORIGEM_WSRT.items()):
        nossa = getattr(L, nome_py)
        try:
            if nome_py == "WSRT_CATALOGO":
                a_mais, falta = _divergencia(((p, n) for p, n, _r, _o in nossa),
                                             _catalogo_ps1(texto))
            else:
                deles = [x for x in _variavel_ps1(texto, var).split(u"|") if x]
                a_mais, falta = _divergencia(nossa, deles)
                falta = _falta_descoberta(nossa, falta)
        except Exception as e:
            checar(u"%s (%s, L%d) foi lida no .ps1" % (nome_py, var, linha),
                   False, u"%s: %s" % (type(e).__name__, e))
            continue
        checar(u"%s = %s (L%d no dia da copia)" % (nome_py, var, linha),
               not a_mais and not falta,
               u"so aqui: %s | so la: %s" % (a_mais, falta))
    falso = (u"$script:A = 'x|y' +\n    '|z' +\n    # um comentario no meio\n"
             u"    #\n\n    '|w' +\n    '|' + $script:B\n\n# depois\n"
             u"$script:B = 'q'\n")
    checar(u"comentario e linha em branco DENTRO da soma nao a cortam",
           _variavel_ps1(falso, "$script:A") == u"x|y|z|w|q",
           _variavel_ps1(falso, "$script:A"))
    deles = [x for x in _variavel_ps1(texto, "$script:Protegidos").split(u"|") if x]
    isca = _divergencia(tuple(L.WSRT_PROTEGIDOS) + ("NomeInventado",), deles)
    checar(u"ISCA: um nome a mais na nossa copia e acusado",
           isca[0] == ["NomeInventado"], isca)
    checar(u"a marca do ecossistema e a mesma dos dois lados",
           _variavel_ps1(texto, "$script:MarcaEcossistema") == L.MARCA_ECOSSISTEMA)
    checar(u"o arquivo de sinalizacao e o mesmo endereco que o .ps1 le",
           u"'em_uso.json'" in texto and L.NOME_EM_USO == "em_uso.json")
    for rot, arq in ((u"REDE_AMERICAS", ps1), (u"kit global", _achar_kit_global())):
        if not arq:
            print(u"  PULADO  o %s nao existe nesta maquina" % rot)
            continue
        t = io.open(arq, encoding="utf-8-sig", errors="replace").read()
        m = _janela_do_kit(t)
        checar(u"a janela do %s (%s min) e a nossa JANELA_DO_KIT_S (%d s)"
               % (rot, m, L.JANELA_DO_KIT_S),
               m is not None and m * 60 == L.JANELA_DO_KIT_S, str(m))
    alargada = u"$script:EmUsoMaxMin  = 10\r\n"
    checar(u"  ISCA: a janela alargada para 10 min no .ps1 e acusada",
           (_janela_do_kit(alargada) or 0) * 60 != L.JANELA_DO_KIT_S)


def _janela_do_kit(texto):
    import re as _re
    m = _re.search(r"(?m)^\$script:EmUsoMaxMin\s*=\s*(\d+)\s*$", texto)
    return int(m.group(1)) if m else None


def _achar_kit_global():
    env = os.environ.get("RADAI_WSRT_GLOBAL_PS1")
    if env:
        return env if os.path.isfile(env) else u""
    ref = _achar_ps1_do_workstation()
    bases = [RAIZ] + ([os.path.dirname(os.path.dirname(os.path.dirname(ref)))]
                      if ref else [])
    for b in bases:
        d = os.path.abspath(b)
        for _ in range(6):
            c = os.path.join(d, "WORKSTATION_KIT_GLOBAL", "WorkstationKit.ps1")
            if os.path.isfile(c):
                return c
            pai = os.path.dirname(d)
            if pai == d:
                break
            d = pai
    return u""


def teste_o_leitor_do_ps1_pula_comentario():
    secao(u"(4b) o leitor do .ps1 atravessa comentario")
    texto = (u"$script:Outra = 'x|y'\n"
             u"$script:Lista = 'a|b' +\n"
             u"    # um comentario no meio da soma, sem '+' no fim\n"
             u"    #\n"
             u"\n"
             u"    '|c|d#e' +   # comentario depois do '+'\n"
             u"    '|f' + $script:Outra\n"
             u"$script:Depois = 'nao entra'\n")
    try:
        v = _variavel_ps1(texto, u"$script:Lista")
    except Exception as e:
        v = u"%s: %s" % (type(e).__name__, e)
    checar(u"a soma atravessa as linhas de comentario",
           v.startswith(u"a|b|c"), v)
    checar(u"  e o comentario depois do '+' nao interrompe a soma",
           v == u"a|b|c|d#e|fx|y", v)
    checar(u"  e o '#' DENTRO da aspa e texto, nao comentario",
           u"d#e" in v, v)


def _corpo(nome):
    arv = ast.parse(_fonte())
    fn = next(n for n in ast.walk(arv) if isinstance(n, ast.FunctionDef)
              and n.name == nome)
    return ast.get_source_segment(_fonte(), fn) or u""


def _fonte():
    caminho = os.path.join(os.path.dirname(os.path.abspath(L.__file__)),
                           "radai_cleaner.py")
    return io.open(caminho, encoding="utf-8").read()


def _codigo():
    import tokenize
    caminho = os.path.join(os.path.dirname(os.path.abspath(L.__file__)),
                           "radai_cleaner.py")
    fora, anterior = [], tokenize.INDENT
    with io.open(caminho, "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING and anterior in (
                    tokenize.INDENT, tokenize.NEWLINE, tokenize.NL,
                    tokenize.ENCODING, tokenize.DEDENT):
                anterior = tok.type
                continue
            if tok.type not in (tokenize.NL, tokenize.NEWLINE):
                anterior = tok.type
            fora.append(tok.string)
    return " ".join(fora)


def main():
    print(u"test_cleaner | a lista fechada, e o que nunca se toca")
    _rede_de_seguranca()
    for t in (teste_so_para_o_que_esta_na_lista,
              teste_o_trabalho_clinico_nunca_e_tocado,
              teste_so_uma_porta_fecha,
              teste_a_arvore_do_app_nunca_entra_na_lista,
              teste_o_caminho_protege_por_componente,
              teste_o_desconhecido_nasce_desmarcado,
              teste_fechar_refaz_a_classificacao_e_nunca_o_proprio_pid,
              teste_servico_so_com_administrador,
              teste_restaurar_reabre_o_que_tem_mapa,
              teste_o_arquivo_de_sinalizacao,
              teste_o_diagnostico_vira_linhas_de_log,
              teste_o_plano_e_o_executor_se_cobrem_nos_dois_sentidos,
              teste_as_listas_nao_casam_por_acidente,
              teste_o_leitor_do_ps1_pula_comentario,
              teste_as_listas_batem_com_o_workstation_rt,
              teste_para_mas_nao_desabilita,
              teste_o_estado_nao_depende_do_idioma,
              teste_o_laudo_nao_levanta,
              teste_o_device_do_config_chega_aos_ganhos,
              teste_a_placa_que_existe_e_nomeada,
              teste_o_nvidia_smi_e_achado_e_nao_pelo_path,
              teste_a_placa_que_o_torch_nao_alcanca,
              teste_so_biblioteca_padrao,
              teste_a_faxina_nao_apaga_o_que_esta_em_uso,
              teste_a_faxina_apaga_o_somente_leitura_e_para_no_teto,
              teste_a_extracao_do_zip_e_a_mesma_conta_do_lote):
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    falhas = [(n, d) for n, ok, d in _R if not ok]
    print(u"\n" + u"=" * 66)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_R)))
        for n, d in falhas:
            print(u"  - %s%s" % (n, (u"  [%s]" % d) if d else u""))
    else:
        print(u"OK: %d checagens, todas passaram" % len(_R))
    print(u"=" * 66)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
