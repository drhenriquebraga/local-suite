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


_SO_LEITURA = {"tasklist", "nvidia-smi", "powercfg", "netstat"}


def _comandos(fonte):
    chamados = set()
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.List) or not no.elts:
            continue
        itens = [x.value for x in no.elts
                 if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        if not itens or itens[0].startswith(("-", "/")):
            continue
        chamados.add(itens[0])
    return chamados


def teste_so_le_a_estacao():
    secao(u"o limpador so mede: nenhum comando que mude a estacao")
    chamados = _comandos(_fonte())
    checar(u"o modulo so chama comando de LEITURA",
           chamados <= _SO_LEITURA, u", ".join(sorted(chamados)))
    checar(u"  ISCA: um `sc stop` reprova",
           not (_comandos(u"x = ['sc', 'stop', 'WSearch']\n") <= _SO_LEITURA))
    checar(u"e nao abre processo pela API de encerrar",
           u"TerminateProcess" not in _fonte()
           and u"PostMessageW" not in _fonte())


def teste_o_laudo_nao_levanta():
    secao(u"o laudo")
    d = L.laudo()
    for k in ("memoria", "aplicacoes", "piso_mb", "disco", "ganhos"):
        checar(u"o laudo traz `%s`" % k, k in d)
    for k in ("servicos", "recuperavel", "aviso"):
        checar(u"e nao traz mais `%s`" % k, k not in d)
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
    base = dict(aplicacoes_pesadas=lambda *a, **k: [],
                espaco_em_disco=lambda *a, **k: [])
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
    secao(u"as faxinas nao apagam o que esta em uso")
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


def teste_a_arvore_do_app():
    secao(u"em_uso: a arvore do programa, e so ela")
    t = _tabela()
    arv = L.arvore_do_app(t, VIG)
    checar(u"a arvore tem o vigia, o cmd que o abriu, o conhost e os filhos",
           {VIG, 200, 210, 300, 301} <= arv, sorted(arv))
    checar(u"  e NAO sobe ate o Explorer (nem pega o cmd dos outros)",
           100 not in arv and 500 not in arv and 400 not in arv, sorted(arv))
    curta = L.arvore_do_app(t, VIG, max_subida=0)
    checar(u"  ISCA: sem subir, o cmd que abriu o vigia fica de fora",
           200 not in curta and VIG in curta, sorted(curta))
    if os.name == "nt":
        procs = L.processos()
        checar(u"a lista real de processos tem este processo, com o pai",
               any(p["pid"] == os.getpid() and p["ppid"] > 0 for p in procs),
               len(procs))
        checar(u"  e so leva o que a arvore e o netstat usam",
               all(set(p) == {"pid", "ppid", "exe", "nome"} for p in procs[:20]))


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
    L_ = L.linhas_do_diagnostico(cf, ld, {"pids": [1, 2], "atualizado": u"x"})
    checar(u"todas as linhas comecam por `diagnostico:`",
           all(x.startswith(u"diagnostico: ") for x in L_), L_[:3])
    checar(u"comeca e termina marcado", u"começo" in L_[0] and u"fim" in L_[-1])
    checar(u"o que falta aparece como FALTA",
           any(u"[FALTA] Pesos — trunk_cavities" in x for x in L_))
    checar(u"a nota de alcance nao vira achado",
           not any(u"alcance" in x for x in L_))
    checar(u"memoria, disco apertado e a sinalizacao para o kit",
           any(u"4000 MB livres" in x for x in L_)
           and any(u"aperta" in x for x in L_)
           and any(u"2 PID(s)" in x for x in L_), L_)
    checar(u"  e nada de servico nem de Otimizar (um laudo antigo com "
           u"servicos nao os faz voltar)",
           not any(u"SysMain" in x or u"Otimizar" in x or u"servi" in x
                   for x in L_), L_)
    checar(u"nenhuma linha leva a palavra que pinta de vermelho a barra "
           u"(«erro», «falhou», «nao consegui»)",
           not any(p in x.lower() for x in L_
                   for p in (u"erro", u"falhou", u"não consegui"))
           , [x for x in L_ if u"erro" in x.lower()])


_NOMES_QUE_SAIRAM = (
    "SERVICOS", "estado_dos_servicos", "parar_servico", "iniciar_servico",
    "espaco_recuperavel", "liberar", "classificar", "plano_de_otimizacao",
    "fechar_processos", "otimizar", "restaurar", "mapa_de_reabertura",
    "ler_estado_otimizar", "NOME_ESTADO_OTIMIZAR", "WSRT_PROTEGIDOS",
    "WSRT_CATALOGO", "ORIGEM_WSRT", "AVISO_DA_LISTA")
_CHAMADAS_QUE_SAIRAM = (
    "parar_servico", "iniciar_servico", "estado_dos_servicos",
    "plano_de_otimizacao", "ler_estado_otimizar", "espaco_recuperavel",
    "sugestao_de_otimizacao", "otimizar_estacao", "restaurar_se_pendente",
    "fechar_processos")
_TEXTOS_QUE_SAIRAM = (
    "/api/otimizar", "/api/limpador", "/api/lote/otimizacao", "/api/lote/otimizar", "pausar_servicos",
    "overnight_pausados", "radaiOtimizar", "radaiOtimSugerir",
    "limpCarregar", "otimRestaurar", "radai_pipe_otm", "ov_pausar",
    "pl_prep", "data-radai-frase>Otimizar<")
_FICAM_NO_LIMPADOR = (
    "memoria_da_estacao", "memoria_do_processo_mb", "teto_do_commit_mb",
    "disco_necessario_gb", "espaco_em_disco", "ganhos_de_velocidade",
    "aplicacoes_pesadas", "laudo", "linhas_do_diagnostico", "PROTEGIDOS",
    "_protegido", "processos", "arvore_do_app", "navegadores_conectados",
    "conteudo_em_uso", "gravar_em_uso", "apagar_em_uso", "ler_em_uso",
    "caminho_em_uso", "pasta_de_estado")


def _restos_do_otimizar(fontes):
    fora = []
    for caminho, texto in sorted(fontes.items()):
        nome = os.path.basename(caminho)
        try:
            arv = ast.parse(texto)
        except SyntaxError as e:
            fora.append(u"%s: nao compila (%s)" % (nome, e))
            continue
        for no in ast.walk(arv):
            if (nome == "radai_cleaner.py"
                    and isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.Name))
                    and getattr(no, "name", getattr(no, "id", u""))
                    in _NOMES_QUE_SAIRAM
                    and (not isinstance(no, ast.Name)
                         or isinstance(no.ctx, ast.Store))):
                fora.append(u"%s define `%s`" % (
                    nome, getattr(no, "name", getattr(no, "id", u""))))
            elif (isinstance(no, ast.Attribute)
                  and no.attr in _CHAMADAS_QUE_SAIRAM):
                fora.append(u"%s:%d usa `.%s`" % (nome, no.lineno, no.attr))
            elif (isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and no.name in _CHAMADAS_QUE_SAIRAM):
                fora.append(u"%s:%d define `%s`" % (nome, no.lineno, no.name))
            elif (isinstance(no, (ast.List, ast.Tuple)) and len(no.elts) > 1
                  and isinstance(no.elts[0], ast.Constant)
                  and isinstance(no.elts[1], ast.Constant)
                  and str(no.elts[0].value).lower() in ("sc", "sc.exe")
                  and str(no.elts[1].value).lower() in (
                      "stop", "start", "query", "config", "pause")):
                fora.append(u"%s:%d chama `sc`" % (nome, no.lineno))
            elif (isinstance(no, ast.Constant) and isinstance(no.value, str)):
                if no.value.strip() == u"Otimizar":
                    fora.append(u"%s:%d leva o botao 'Otimizar'"
                                % (nome, no.lineno))
                for t in _TEXTOS_QUE_SAIRAM:
                    if t in no.value:
                        fora.append(u"%s:%d leva %r" % (nome, no.lineno, t))
    return sorted(set(fora))


def teste_o_otimizar_e_a_pausa_de_servicos_sairam():
    secao(u"o Otimizar e a pausa de servicos sairam; as medidas e o "
          u"em_uso ficam")
    fontes = {}
    for caminho in _componentes.arquivos("app"):
        if os.path.basename(caminho) in ("radai_consent.py",
                                         "radai_phrases.py"):
            continue
        fontes[caminho] = io.open(caminho, encoding="utf-8").read()
    checar(u"li o app das sete pastas (o limpador, o vigia, o lote, o "
           u"painel e a barra)",
           set(("radai_cleaner.py", "radai_watcher.py", "radai_batch.py",
                "radai_panel.py", "radai_todo.py", "radai_overnight.py"))
           <= set(os.path.basename(c) for c in fontes),
           len(fontes))
    restos = _restos_do_otimizar(fontes)
    checar(u"nenhum resto do Otimizar nem da pausa de servicos no app",
           not restos, u" | ".join(restos[:12]))
    isca = {"isca.py": (u"import radai_cleaner as LP\n"
                        u"def f(app):\n"
                        u"    LP.parar_servico('SysMain')\n"
                        u"    x = ['sc', 'stop', 'WSearch']\n"
                        u"    return '/api/otimizar/plano', "
                        u"{'pausar_servicos': True}\n")}
    r = _restos_do_otimizar(isca)
    checar(u"  ISCA: a chamada, o `sc`, a rota e a chave sao acusados",
           len(r) == 4, r)
    for n in _FICAM_NO_LIMPADOR:
        checar(u"o limpador continua com `%s`" % n, hasattr(L, n))
    import radai_overnight as OV
    checar(u"o radai_overnight fica so com a frota",
           hasattr(OV, "frota") and hasattr(OV, "resumo_da_frota")
           and not any(hasattr(OV, n) for n in
                       ("iniciar", "encerrar", "estado", "ha_registro",
                        "restaurar_se_pendente")),
           sorted(n for n in dir(OV) if not n.startswith("__")))


def _chama(fonte, nome):
    return any(isinstance(no, ast.Attribute) and no.attr == nome
               and isinstance(getattr(no, "ctx", None), ast.Load)
               for no in ast.walk(ast.parse(fonte)))


def teste_o_registro_antigo_sai_no_arranque():
    secao(u"o otimizar.json e o registro do turno antigo saem no arranque")
    import json
    import radai_overnight as OV
    velho = os.environ.get("LOCALAPPDATA")
    base = _cleanup.temporaria("radai_ac_limp_antigo_")
    os.environ["LOCALAPPDATA"] = base
    linhas = []
    try:
        est = os.path.join(base, "RADIOTERAPIA_AI", "otimizar.json")
        os.makedirs(os.path.dirname(est))
        io.open(est, "w", encoding="utf-8").write(
            u'{"fechados": ["OneDrive"], "servicos": ["SysMain"]}')
        checar(u"o otimizar.json de uma versao anterior sai, com uma linha "
               u"no log", L.apagar_estado_antigo_do_otimizar(linhas.append)
               is True and not os.path.exists(est) and len(linhas) == 1,
               linhas)
        checar(u"  e sem o arquivo nao faz nada nem escreve",
               L.apagar_estado_antigo_do_otimizar(linhas.append) is False
               and len(linhas) == 1)
    finally:
        if velho is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = velho
    pasta = _cleanup.temporaria("radai_ac_limp_ovn_")
    reg = os.path.join(pasta, OV.NOME_REGISTRO_ANTIGO)
    io.open(reg, "w", encoding="utf-8").write(json.dumps(
        {"servicos": [{"nome": "SysMain", "acao": "parado"},
                      {"nome": "WSearch", "acao": "nao_mexido"}]}))
    linhas = []
    checar(u"o registro do turno antigo sai, e o log diz o servico que "
           u"ficou parado", OV.apagar_registro_antigo(linhas.append, pasta)
           is True and not os.path.exists(reg)
           and u"SysMain" in u"".join(linhas)
           and u"WSearch" not in u"".join(linhas), linhas)
    checar(u"  e o arquivo ilegivel tambem sai",
           io.open(reg, "w", encoding="utf-8").write(u"{x") is not None
           and OV.apagar_registro_antigo(None, pasta) is True
           and not os.path.exists(reg))
    vigia = io.open(_componentes.fonte("app/radai_watcher.py"),
                    encoding="utf-8").read()
    checar(u"o arranque do vigia chama as duas faxinas",
           _chama(vigia, "apagar_registro_antigo")
           and _chama(vigia, "apagar_estado_antigo_do_otimizar"))
    checar(u"  ISCA: sem a chamada, a checagem reprova",
           not _chama(vigia.replace(u".apagar_registro_antigo(", u".x("),
                      "apagar_registro_antigo"))


def _fonte():
    caminho = os.path.join(os.path.dirname(os.path.abspath(L.__file__)),
                           "radai_cleaner.py")
    return io.open(caminho, encoding="utf-8").read()


def main():
    print(u"test_cleaner | as medidas da estacao, o em_uso, e o que nunca se toca")
    for t in (teste_o_otimizar_e_a_pausa_de_servicos_sairam,
              teste_o_registro_antigo_sai_no_arranque,
              teste_o_trabalho_clinico_nunca_e_tocado,
              teste_a_arvore_do_app,
              teste_o_arquivo_de_sinalizacao,
              teste_o_diagnostico_vira_linhas_de_log,
              teste_so_le_a_estacao,
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
