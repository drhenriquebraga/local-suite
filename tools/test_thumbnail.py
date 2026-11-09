# -*- coding: utf-8 -*-
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))


def pasta_app(aqui):
    for c in (os.path.join(aqui, "..", "app"), os.path.join(aqui, "..")):
        if os.path.exists(os.path.join(c, "radai_watcher.py")):
            return os.path.abspath(c)
    return os.path.abspath(os.path.join(aqui, "..", "app"))


APP = pasta_app(AQUI)
sys.path.insert(0, APP)

import tempfile as _tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_ac_miniatura')
os.environ["RADAI_CALIB_DIR"] = _tempfile.mkdtemp(prefix="radai_ac_miniatura_")


_RESULTADOS = []


def checar(nome, ok, detalhe=""):
    _RESULTADOS.append((nome, bool(ok), detalhe))
    if not ok:
        print("  FALHA  %s%s" % (nome, ("  [%s]" % detalhe) if detalhe else ""))
    return bool(ok)


def secao(t):
    print("\n-- %s --" % t)


def fonte(nome):
    return io.open(_componentes.fonte("app/" + nome), encoding="utf-8",
                   errors="replace").read()


PACIENTE_COM_ESPACO = u"ISCA BELTRANO 12345"


def _tem_paciente(texto):
    return any(p in (texto or u"") for p in PACIENTE_COM_ESPACO.split())


def teste_o_caminho_nao_viaja_na_url():
    secao("o bilhete: caminho nenhum na URL")
    import radai_thumbnail as M

    p = r"C:\\Pacientes\\ISCA_BELTRANO_12345\\CT"
    uid = "1.9.999.2.55.3.1234567890.1.9999"
    b = M.bilhete(p, uid)

    checar(u"o bilhete não contém o caminho", "BELTRANO" not in b
           and "Pacientes" not in b and "\\" not in b)
    _dig = u"".join(c for c in uid if c.isdigit())
    _vaza = [_dig[i:i + 8] for i in range(0, max(0, len(_dig) - 7))
             if _dig[i:i + 8] in b]
    checar(u"nem o UID da série, nem 8 dígitos seguidos dele",
           uid not in b and not _vaza, u", ".join(_vaza[:3]))
    checar(u"é hexadecimal puro (cabe em URL sem escapar)",
           bool(re.match(r"^[0-9a-f]{32}$", b)), b[:40])
    checar(u"resolve de volta para (pasta, uid)", M.resolver(b) == (p, uid))
    checar(u"bilhete desconhecido devolve (None, None), sem levantar",
           M.resolver("f" * 32) == (None, None))
    checar(u"e bilhete vazio também", M.resolver("") == (None, None)
           and M.resolver(None) == (None, None))

    checar(u"o mesmo par dá o mesmo bilhete", M.bilhete(p, uid) == b)
    checar(u"série diferente dá bilhete diferente",
           M.bilhete(p, uid + "0") != b)
    checar(u"pasta diferente dá bilhete diferente",
           M.bilhete(p + "2", uid) != b)


def teste_cabecalho_http_e_ascii():
    secao("cabecalho HTTP: latin-1 nao aceita travessao")
    src = fonte("radai_bridge.py")
    checar(u"a rota tem um saneador de cabeçalho", "def _cab(t)" in src)
    checar(u"e ele é usado em todos os cabeçalhos X-RadAI",
           src.count("_cab(") >= 4, "%d usos" % src.count("_cab("))

    msgs = re.findall(r'"erro":\s*u?"([^"]{6,})"', fonte("radai_thumbnail.py"))
    msgs += re.findall(r'u"([^"]*—[^"]*)"', fonte("radai_thumbnail.py"))
    fora_latin = [m for m in msgs if any(ord(c) > 255 for c in m)]
    checar(u"o módulo emite ao menos uma mensagem fora do latin-1",
           bool(fora_latin), u"%d mensagens lidas" % len(msgs))
    msg = fora_latin[0] if fora_latin else u"RTSTRUCT — sem corte"

    def _cab(t):
        return (t or u"").encode("ascii", "replace").decode("ascii")[:200]

    try:
        _cab(msg).encode("latin-1")
        ok = True
    except Exception as e:
        ok, msg2 = False, str(e)
    checar(u"depois do saneador ela cabe num cabeçalho HTTP", ok)

    try:
        u"RTSTRUCT — sem corte".encode("latin-1")
        estoura = False
    except UnicodeEncodeError:
        estoura = True
    checar(u"o travessão CRU estoura em latin-1 (é o defeito original)", estoura)
    checar(u"e saneado não estoura", _cab(u"RTSTRUCT — sem corte") == "RTSTRUCT ? sem corte")


def teste_serie_sem_pixel_nao_e_erro():
    secao("serie sem pixel: 204, e nao 404")
    import radai_thumbnail as M
    for m in ("RTSTRUCT", "RTPLAN", "RTDOSE"):
        checar(u"%s está na lista de modalidades sem pixel" % m,
               m in M.SEM_IMAGEM)
    for m in ("CT", "MR", "PT", "US", "NM", "CR", "DX", "XA", "MG"):
        checar(u"%s NÃO está na lista (ela é de quem não tem)" % m,
               m not in M.SEM_IMAGEM)

    src = fonte("radai_bridge.py")
    checar(u"a rota da miniatura devolve 204 para série sem imagem",
           "204 if info.get(\"sem_imagem\")" in src)


_PONTE_DOM = u"""
function El(id){
 var self = this; this.id = id || ''; this.style = {}; this.hidden = false;
 this.textContent = ''; this.className = ''; this.value = ''; this.src = '';
 this._a = {}; this._c = {}; this._q = {}; this._h = '';
 this.classList = {
  add: function(c){ self._c[c] = true; },
  remove: function(){ for(var k = 0; k < arguments.length; k++) delete self._c[arguments[k]]; },
  contains: function(c){ return !!self._c[c]; },
  toggle: function(c, on){ if(on === undefined) on = !self._c[c];
   if(on) self._c[c] = true; else delete self._c[c]; return on; }};
}
El.prototype.addEventListener = function(){};
El.prototype.setAttribute = function(k, v){ this._a[k] = String(v); };
El.prototype.getAttribute = function(k){ return this._a.hasOwnProperty(k) ? this._a[k] : null; };
El.prototype.removeAttribute = function(k){ delete this._a[k]; };
El.prototype.querySelector = function(s){ return this._q[s] || (this._q[s] = new El(s)); };
El.prototype.appendChild = function(c){ return c; };
El.prototype.removeChild = function(c){ return c; };
El.prototype.click = function(){};
Object.defineProperty(El.prototype, 'innerHTML', {
 get: function(){ return this._h; }, set: function(v){ this._h = v; this._q = {}; }});
var ELS = {};
var document = {body: {contains: function(){ return true; }, appendChild: function(){},
                        removeChild: function(){}},
 getElementById: function(id){ return ELS[id] || (ELS[id] = new El(id)); },
 addEventListener: function(){}, querySelectorAll: function(){ return []; },
 createElement: function(){ return new El(''); }};
var window = {};
var URL = {createObjectURL: function(b){ return 'blob:' + b; }, revokeObjectURL: function(){}};
var PEDIDOS = [], SINAIS = [], VOANDO = 0, MAXVOO = 0;
var STATUS = function(){ return 200; };
function fetch(url, op){
 var m = /corte=(\\d+)/.exec(url), i = m ? +m[1] : -1;
 var j = /janela=([^&]+)/.exec(url);
 PEDIDOS.push({i: i, janela: j ? decodeURIComponent(j[1]) : ''});
 if(op && op.signal) SINAIS.push(op.signal);
 VOANDO++; MAXVOO = Math.max(MAXVOO, VOANDO);
 var st = STATUS(i);
 return new Promise(function(res){ setTimeout(function(){
  VOANDO--;
  res({status: st, ok: st === 200,
       headers: {get: function(h){ return h === 'X-RadAI-Modalidade' ? 'RTSTRUCT' : ''; }},
       blob: function(){ return Promise.resolve('c' + i); }});
 }, 1); });
}
"""

_PONTE_RODA = u"""
function tique(){ return new Promise(function(r){ setTimeout(r, 3); }); }
async function assentar(){
 for(var k = 0; k < 400; k++){
  await tique();
  var v = DC.visor, C = v && v.carga;
  if(!C) return;
  if(!C.nVoando && (C.parado || C.cursor >= C.ordem.length)) return;
 }
}
var PAROU = 0, _parou = dcVisorParou;
dcVisorParou = function(){ PAROU++; return _parou.apply(this, arguments); };
async function cenario(n, status, antes){
 ELS = {}; PEDIDOS = []; SINAIS = []; VOANDO = 0; MAXVOO = 0; PAROU = 0;
 STATUS = status;
 dcVisorLigar({bilhete: 'b0', cortes: n, central: Math.floor(n / 2)});
 await assentar();
 if(antes) await antes();
 for(var k = 0; k < 20; k++) await tique();
 var cx = ELS['dc_visor'];
 var unicos = PEDIDOS.filter(function(p, k, t){
  return t.map(function(x){ return x.i; }).indexOf(p.i) === k; }).length;
 return {pedidos: PEDIDOS.length, unicos: unicos,
         primeiros: PEDIDOS.slice(0, 3).map(function(p){ return p.i; }),
         maxvoo: MAXVOO, parou: PAROU,
         aviso: cx.querySelector('[data-ue="aviso"]').textContent,
         semimg: cx.querySelector('.ue-visor').classList.contains('sem-img'),
         mod: cx.querySelector('.ue-visor').getAttribute('data-mod')};
}
(async function(){
 var R = {};
 R.tudo_bem = await cenario(40, function(){ return 200; });
 R.tudo_404 = await cenario(40, function(){ return 404; });
 R.tudo_204 = await cenario(40, function(){ return 204; });
 R.tudo_500 = await cenario(40, function(){ return 500; });
 R.central_422 = await cenario(40, function(i){ return i === 20 ? 422 : 200; },
   async function(){ DC.visor.ir(20); await assentar(); DC.visor.ir(21);
                     DC.visor.ir(20); await assentar(); });
 ELS = {}; PEDIDOS = []; SINAIS = []; STATUS = function(){ return 200; };
 dcVisorLigar({bilhete: 'b0', cortes: 40, central: 20});
 DC.visor.ir(7);
 var velho = DC.visor, sinaisVelhos = SINAIS.slice(), antes = PEDIDOS.length;
 dcJanela('osso');
 R.janela = {abortados: sinaisVelhos.filter(function(s){ return s && s.aborted; }).length,
             emVooNoVelho: sinaisVelhos.length, velhoFechado: !!velho.fechado,
             novoAtual: DC.visor.atual,
             primeiroNovo: PEDIDOS[antes] || null};
 await assentar();
 console.log('JSON:' + JSON.stringify(R));
})();
"""


def _node():
    import shutil
    return shutil.which("node")


def _rodar_node(js):
    import json
    import subprocess
    import tempfile
    node = _node()
    d = tempfile.mkdtemp(prefix="radai_ac_miniatura_js_")
    alvo = os.path.join(d, "r.js")
    try:
        io.open(alvo, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, alvo], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        for ln in reversed((r.stdout or "").splitlines()):
            if ln.startswith("JSON:"):
                return json.loads(ln[5:]), None
        return None, ((r.stderr or "") + (r.stdout or ""))[-600:]
    finally:
        import shutil as _sh
        _sh.rmtree(d, ignore_errors=True)


def teste_o_erro_nao_vira_laco_infinito():
    secao("o visor do DicomBridge: 404 e 204 param, e o corte falho nao volta")
    if not _node():
        checar(u"node disponível para executar o visor", False,
               u"PULADO -- sem node")
        return
    import radai_bridge
    import radai_thumbnail as M
    import radai_viewer
    d, erro = _rodar_node(_PONTE_DOM + radai_viewer.JS_UM_EIXO
                          + radai_bridge.JS_COMUM + radai_bridge.JS
                          + _PONTE_RODA)
    checar(u"o visor do DicomBridge executa com o DOM dublado", d is not None,
           erro or u"")
    if d is None:
        return
    b = d["tudo_bem"]
    checar(u"a série chega por bissecção: 50%, 25%, 75%",
           b["primeiros"] == M.ordem_de_bisseccao(40)[:3] == [20, 10, 30],
           str(b["primeiros"]))
    checar(u"todos os 40 cortes chegam, cada um uma vez",
           b["pedidos"] == 40 and b["unicos"] == 40, str(b))
    checar(u"e nunca mais de três em voo", b["maxvoo"] <= 3, str(b["maxvoo"]))
    for caso, n in ((u"tudo_404", 404), (u"tudo_204", 204)):
        r = d[caso]
        checar(u"%d em todo corte: PARA — só os três que estavam em voo" % n,
               r["pedidos"] <= 3 and r["pedidos"] == r["unicos"], str(r))
        checar(u"  e a tela diz por que UMA vez (e não uma por pedido em voo)",
               r["parou"] == 1, str(r))
    checar(u"404: a tela manda recarregar a pasta",
           d["tudo_404"]["aviso"] == u"recarregue a pasta", str(d["tudo_404"]))
    checar(u"204: a moldura mostra a sigla da série, e não fica preta",
           d["tudo_204"]["semimg"] and d["tudo_204"]["mod"] == u"RTSTRUCT",
           str(d["tudo_204"]))
    r = d["central_422"]
    checar(u"422 no corte central: cada corte pedido UMA vez, mesmo rolando "
           u"até o que falhou", r["pedidos"] == 40 and r["unicos"] == 40,
           str(r))
    checar(u"  e a tela diz que ESTE corte não pôde ser lido",
           r["aviso"] == u"este corte não pôde ser lido", str(r))
    r = d["tudo_500"]
    checar(u"500 em todos: cada corte uma vez, e a tela diz que não abriu",
           r["pedidos"] == 40 and r["unicos"] == 40
           and r["aviso"] == u"não consegui abrir a série", str(r))
    j = d["janela"]
    checar(u"trocar a janela aborta o que estava em voo no visor velho",
           j["emVooNoVelho"] >= 1 and j["abortados"] == j["emVooNoVelho"]
           and j["velhoFechado"], str(j))
    checar(u"  e o visor novo abre no MESMO corte, na janela nova",
           j["novoAtual"] == 7 and (j["primeiroNovo"] or {}).get("i") == 7
           and (j["primeiroNovo"] or {}).get("janela") == u"osso", str(j))


def teste_a_rota_do_visor_do_bridge_separa_os_casos():
    secao("a rota do visor do DicomBridge separa os casos")
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except Exception as e:
        checar(u"fastapi e o TestClient disponíveis", False,
               u"PULADO: %s" % type(e).__name__)
        return
    import radai_bridge
    import radai_thumbnail as M
    app = FastAPI()
    radai_bridge.montar(app)
    cli = TestClient(app)
    N = 12
    pasta, uid = _serie_sintetica(N)
    b = M.bilhete(pasta, uid)
    r = cli.get("/api/bridge/corte", params={"b": b, "corte": 5,
                                             "janela": "mediastino"})
    checar(u"o corte sai em PNG", r.status_code == 200
           and r.content[:8] == b"\x89PNG\r\n\x1a\n", str(r.status_code))
    checar(u"bilhete morto é 404",
           cli.get("/api/bridge/corte", params={"b": "f" * 32}).status_code
           == 404)
    linhas = []
    orig_png, orig_log = M.png, M._log_da_estacao
    M._JA_REGISTRADAS.clear()
    try:
        M.png = lambda *a, **k: (b"", {"erro": u"não decodifica", "cortes": N,
                                       "corte": 5})
        r422 = cli.get("/api/bridge/corte", params={"b": b, "corte": 5})
        M.png = lambda *a, **k: (b"", {"sem_imagem": True,
                                       "erro": u"RTSTRUCT — x",
                                       "modalidade": "RTSTRUCT"})
        r204 = cli.get("/api/bridge/corte", params={"b": b, "corte": 5})

        def _explode(*a, **k):
            raise IOError(u"Sem DICOM em \\\\servidor\\imagens\\Patients"
                          u"\\ISCA BELTRANO 12345\\CT")
        M.png = _explode
        M._log_da_estacao = lambda: linhas.append
        r500a = cli.get("/api/bridge/corte", params={"b": b, "corte": 1})
        r500b = cli.get("/api/bridge/corte", params={"b": b, "corte": 2})
    finally:
        M.png, M._log_da_estacao = orig_png, orig_log
    checar(u"corte que não decodifica é 422, e não 404 (que pararia a série)",
           r422.status_code == 422, str(r422.status_code))
    checar(u"série que não é imagem é 204, com a sigla no cabeçalho",
           r204.status_code == 204
           and r204.headers.get("X-RadAI-Modalidade") == "RTSTRUCT",
           "%s %r" % (r204.status_code, r204.headers.get("X-RadAI-Modalidade")))
    checar(u"o 500 leva só o tipo no cabeçalho",
           r500a.status_code == 500
           and r500a.headers.get("x-radai-erro") == "OSError",
           "%s %r" % (r500a.status_code, r500a.headers.get("x-radai-erro")))
    checar(u"e a causa vai para o log, UMA vez para dois cortes da série",
           r500b.status_code == 500
           and sum(1 for l in linhas if u"falhou com OSError" in l) == 1,
           u" | ".join(linhas)[:300])
    checar(u"sem o caminho do paciente, nem o pedaço depois do espaço",
           linhas and not any(_tem_paciente(l) or u"servidor" in l
                              for l in linhas), u" | ".join(linhas)[:300])


def teste_a_pasta_e_varrida_uma_vez():
    secao("a pasta e varrida uma vez por bilhete")
    import radai_thumbnail as M
    checar(u"há uma memória da série por bilhete", hasattr(M, "_SERIES"))
    src = fonte("radai_thumbnail.py")
    checar(u"e `png` não chama `varrer` direto",
           "radai_dicom.varrer" not in src.split("def png(")[1])
    checar(u"quem varre é `_serie_do_bilhete`",
           "def _serie_do_bilhete" in src
           and "radai_dicom.varrer" in src.split("def _serie_do_bilhete")[1])


def teste_a_reducao_nao_inventa_pixel():
    secao("a reducao: sem PIL, e sem esticar")
    import numpy as np
    import radai_thumbnail as M

    a = np.arange(512 * 512, dtype=np.int32).reshape(512, 512)
    r = M._reduzir(a, 192)
    checar(u"cabe no lado pedido", max(r.shape) <= 192, "%s" % (r.shape,))
    checar(u"todo valor da reduzida veio da original (não interpolou)",
           bool(np.isin(r, a).all()))

    b = np.arange(64 * 512, dtype=np.int32).reshape(64, 512)
    r2 = M._reduzir(b, 192)
    checar(u"não quadrada: o lado maior é o teto", max(r2.shape) <= 192,
           "%s" % (r2.shape,))
    checar(u"e a proporção é preservada (±1 pixel)",
           abs(r2.shape[1] / float(r2.shape[0]) - 512 / 64.0) < 0.6,
           "%s vs %.1f" % (r2.shape, 512 / 64.0))

    c = np.zeros((40, 40), dtype=np.int32)
    checar(u"menor que o teto passa intacta",
           M._reduzir(c, 192).shape == (40, 40))


def teste_a_janela_vem_do_recon3d():
    secao("a janela: uma fonte so")
    import radai_thumbnail as M
    import radai_recon3d as R
    src = fonte("radai_thumbnail.py")
    checar(u"a miniatura não define janela própria",
           "JANELAS" not in src.replace("radai_recon3d.JANELAS", ""))
    checar(u"ela usa as do recon3d", "radai_recon3d.JANELAS" in src)
    for j in ("pulmao", "mediastino", "osso"):
        checar(u"a janela `%s` existe" % j, j in R.JANELAS)
    checar(u"o PNG sai de `radai_recon3d.para_png`",
           "radai_recon3d.para_png" in src)
    checar(u"e o módulo não importa PIL",
           not re.search(r"^\s*(import\s+PIL|from\s+PIL)", src, re.M))


def teste_a_miniatura_nao_e_visualizador():
    secao("a fronteira: identificacao, e nao diagnostico")
    src = fonte("radai_thumbnail.py")
    bridge = fonte("radai_bridge.py")

    for termo in ("annotate", "anotar", "marcar_achado", "realce", "heatmap",
                  "overlay", "bbox", "candidat", "suspeit", "score",
                  "probabilidade"):
        checar(u"a miniatura não faz `%s`" % termo,
               termo not in src.lower(), termo)

    fonte_bridge = fonte("radai_bridge.py")

    for termo in ("to_obj", ".mp4", "salvar_png", "salvar_imagem",
                  "toblob", "todataurl"):
        checar(u"a grade não exporta imagem (`%s`)" % termo,
               termo not in fonte_bridge.lower(), termo)

    for termo in ("attachment", "content-disposition"):
        checar(u"o DicomBridge não serve anexo (`%s`)" % termo,
               termo not in fonte_bridge.lower(), termo)

    for termo in ("download", "attachment", "content-disposition", "to_obj",
                  ".mp4", "salvar_png", "exportar"):
        checar(u"a miniatura não exporta (`%s`)" % termo,
               termo not in src.lower(), termo)

    checar(u"a grade usa <img>, e não <canvas>",
           "<img id=" in bridge and "<canvas" not in bridge.lower())


def teste_o_corte_pedido_nao_estoura():
    secao("corte fora da faixa: prende na borda")
    import radai_thumbnail as M
    checar(u"o corte central de 117 é 58", M.central(117) == 58)
    checar(u"de 1 corte é 0", M.central(1) == 0)
    checar(u"de 0 é 0 (e não -1)", M.central(0) == 0)
    checar(u"de negativo é 0", M.central(-5) == 0)


def teste_so_stdlib_e_o_que_o_bundle_tem():
    secao("dependencias: so o que o bundle tem")
    src = fonte("radai_thumbnail.py")
    importa = set(re.findall(r"^\s*import\s+([a-zA-Z_][\w.]*)", src, re.M))
    importa |= set(re.findall(r"^\s*from\s+([a-zA-Z_][\w.]*)", src, re.M))
    permitidos = {"hashlib", "hmac", "os", "threading", "numpy", "pydicom",
                  "radai_dicom", "radai_recon3d", "struct", "zlib", "io", "sys",
                  "traceback", "radai_records", "radai_archive",
                  "pydicom.pixels", "pydicom.dataset", "pydicom.uid"}
    fora = sorted(importa - permitidos)
    checar(u"não importa nada fora do que o bundle tem", not fora, ", ".join(fora))
    topo = src.split("def bilhete")[0]
    checar(u"numpy não é importado no topo", "import numpy" not in topo)
    checar(u"pydicom não é importado no topo", "import pydicom" not in topo)


def _maior_buraco(carregados, n):
    maior = corrida = 0
    for i in range(n):
        if i in carregados:
            corrida = 0
        else:
            corrida += 1
            maior = max(maior, corrida)
    return maior


def teste_a_ordem_de_bisseccao():
    secao("a ordem de bisseccao: o meio, depois os meios")
    import radai_thumbnail as M
    checar(u"n = 100 começa por 50, 25, 75 e os meios dos quartos",
           M.ordem_de_bisseccao(100)[:7] == [50, 25, 75, 12, 38, 63, 88],
           str(M.ordem_de_bisseccao(100)[:7]))
    checar(u"n = 0 e n inválido não levantam",
           M.ordem_de_bisseccao(0) == [] and M.ordem_de_bisseccao(None) == []
           and M.ordem_de_bisseccao("x") == [] and M.ordem_de_bisseccao(-3) == [])
    cobre, comeca, buraco = [], [], []
    for n in range(1, 401):
        o = M.ordem_de_bisseccao(n)
        if sorted(o) != list(range(n)):
            cobre.append(n)
        if o[0] != M.central(n):
            comeca.append(n)
        feitos = set()
        for k, i in enumerate(o, 1):
            feitos.add(i)
            if _maior_buraco(feitos, n) > 2.0 * n / k:
                buraco.append((n, k))
                break
    checar(u"cobre 0..n-1 exatamente uma vez, para n de 1 a 400", not cobre,
           str(cobre[:5]))
    checar(u"começa no corte central da miniatura (`central`)", not comeca,
           str(comeca[:5]))
    checar(u"com k carregados, o maior buraco é ≤ 2n/k", not buraco,
           str(buraco[:5]))


def _serie_sintetica(n=24):
    from datetime import datetime
    import make_test_series
    base = _tempfile.mkdtemp(prefix="radai_ac_miniatura_ue_")
    pasta = os.path.join(base, "PAC_UE", "CT")
    uid = make_test_series.escreve_serie(pasta, "PAC_UE", datetime.now(), n)
    return pasta, uid


def _chromium():
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if not os.path.isdir(base):
        return None
    for nome in sorted(os.listdir(base), reverse=True):
        if not nome.startswith("chromium-"):
            continue
        for sub in ("chrome-win64", "chrome-win"):
            exe = os.path.join(base, nome, sub, "chrome.exe")
            if os.path.isfile(exe):
                return exe
    return None


_PNG_1PX = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
            b"\x01\x08\x00\x00\x00\x00:~\x9bU\x00\x00\x00\nIDATx\x9cc`\x00\x00"
            b"\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82")


def _roda_no_navegador(nav, js, cenarios, trocar=None):
    import json as _json
    base = u"http://visor.radai.test"
    import radai_ui
    import radai_viewer as RV
    pagina = radai_ui.aplicar(
        u"<!doctype html><html><head><meta charset='utf-8'><style>%s%s"
        u"</style></head><body>%s<div id='ue' style='width:300px'></div>"
        u"<script>%s</script></body></html>"
        % (RV.CSS, RV.CSS_UM_EIXO, RV.html(com_3d=False), js))
    if trocar:
        pagina = pagina.replace(trocar[0], trocar[1])
    ctx = nav.new_context(viewport={"width": 1200, "height": 900})
    abrir = {}

    def atender(route):
        caminho = route.request.url.split(base, 1)[-1].split("?")[0]
        if caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/api/umeixo/abrir":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps(abrir.get("d") or {}))
        else:
            route.fulfill(status=200, content_type=u"image/png",
                          body=_PNG_1PX)
    fora = []
    try:
        ctx.route(base + u"/**", atender)
        pg = ctx.new_page()
        pg.goto(base + u"/", wait_until="load")
        for c in cenarios:
            abrir["d"] = c.get("abrir")
            fora.append(pg.evaluate(c["js"]))
    finally:
        ctx.close()
    return fora


_UM_EIXO_RODA = u"""(async () => {
 var cx = document.getElementById('ue');
 var V = RadaiUmEixo(cx, {n: 20, inicio: 10, cranial: %s,
   url: function(i){ return '/c?k=' + i }});
 var v = cx.querySelector('.ue-visor');
 v.dispatchEvent(new WheelEvent('wheel', {deltaY: 120, bubbles: true, cancelable: true}));
 var roda = V.atual;
 V.ir(10);
 v.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true}));
 var seta = V.atual;
 V.ir(10);
 v.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true}));
 var lado = V.atual;
 V.fechar();
 return [roda, seta, lado];
})()"""

_UM_EIXO_ABRIR = u"""(async () => {
 var cx = document.getElementById('ue');
 var V = await umEixoAbrir(cx, {pasta: 'x', uid: 'y'});
 if(!V) return -1;
 cx.querySelector('.ue-visor').dispatchEvent(
   new WheelEvent('wheel', {deltaY: 120, bubbles: true, cancelable: true}));
 var a = V.atual;
 umEixoFechar(cx);
 return a;
})()"""

_UI_VISOR_RODA = u"""(() => {
 var V = uiVisor({titulo: 't', total: 20, inicial: 10, cranial: %s,
   src: function(k, j){ return '/c?k=' + k }});
 var qs = document.querySelectorAll('.ui-visor-img'), q = qs[qs.length - 1];
 q.dispatchEvent(new WheelEvent('wheel', {deltaY: 120, bubbles: true, cancelable: true}));
 var roda = V.corte();
 V.ir(10);
 document.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true}));
 var seta = V.corte();
 V.fechar();
 return [roda, seta];
})()"""

_UI_VISOR_SENTIDO_DEPOIS = u"""(() => {
 var V = uiVisor({titulo: 't', total: 20, inicial: 10,
   src: function(k, j){ return '/c?k=' + k }});
 V.definirSentido(%s);
 var qs = document.querySelectorAll('.ui-visor-img'), q = qs[qs.length - 1];
 q.dispatchEvent(new WheelEvent('wheel', {deltaY: 120, bubbles: true, cancelable: true}));
 var roda = V.corte();
 V.fechar();
 return roda;
})()"""

_ZOOM_UM_EIXO = u"""(async () => {
 var cx = document.getElementById('ue');
 var V = RadaiUmEixo(cx, {n: 20, inicio: 10, url: function(i){ return '/c?k=' + i }});
 await new Promise(function(r){ setTimeout(r, 150) });
 var img = cx.querySelector('.ue-img'), bt = cx.querySelector('[data-ue-ajustar]');
 var razao = function(){ return Math.round(100 * img.getBoundingClientRect().width
                                        / cx.querySelector('.ue-visor').clientWidth) };
 var fora = {z0: V.zoom, r0: razao(), p0: bt.getAttribute('aria-pressed'),
             txt: bt.textContent};
 bt.click();
 fora.z1 = V.zoom; fora.r1 = razao(); fora.p1 = bt.getAttribute('aria-pressed');
 bt.click();
 fora.z2 = V.zoom;
 V.fechar();
 return fora;
})()"""

_ZOOM_UI_VISOR = u"""(async () => {
 var V = uiVisor({titulo: 't', total: 20, inicial: 10,
   src: function(k, j){ return '/c?k=' + k }});
 await new Promise(function(r){ setTimeout(r, 150) });
 var vs = document.querySelectorAll('.ui-visor'), raiz = vs[vs.length - 1];
 var modal = raiz.closest('.ui-modal');
 for(var t = 0; modal && t < 200; t++){
  var tf = getComputedStyle(modal).transform;
  if(tf === 'none' || tf === 'matrix(1, 0, 0, 1, 0, 0)') break;
  await new Promise(function(r){ setTimeout(r, 25) });
 }
 var img = raiz.querySelector('.ui-visor-img img'), q = raiz.querySelector('.ui-visor-img');
 var bt = raiz.querySelector('.ui-visor-ajustar');
 var razao = function(){ return Math.round(100 * img.getBoundingClientRect().width
                                        / q.clientWidth) };
 var fora = {z0: V.zoom(), r0: razao(), p0: bt.getAttribute('aria-pressed'),
             txt: bt.textContent};
 bt.click();
 fora.z1 = V.zoom(); fora.r1 = razao(); fora.p1 = bt.getAttribute('aria-pressed');
 bt.click();
 fora.z2 = V.zoom();
 V.ajustar();
 fora.z3 = V.zoom();
 V.fechar();
 return fora;
})()"""

_ZOOM_PALCO = u"""(() => {
 var P = window.__palco || (window.__palco = RadaiPalco({base: '/p'}));
 var fora = {z0: P.zoom, l0: document.getElementById('zlbl').textContent};
 document.getElementById('zreset').click();
 fora.z1 = P.zoom; fora.l1 = document.getElementById('zlbl').textContent;
 return fora;
})()"""

_PALCO_RODA = u"""(() => {
 if(!window.__palco) window.__palco = RadaiPalco({base: '/p'});
 var P = window.__palco;
 P.definirForma([20, 30, 30], %s);
 P.corte = {axial: 10, coronal: 15, sagital: 15};
 var ax = document.querySelector('[data-v="axial"]');
 var co = document.querySelector('[data-v="coronal"]');
 ax.dispatchEvent(new WheelEvent('wheel', {deltaY: 120, bubbles: true, cancelable: true}));
 co.dispatchEvent(new WheelEvent('wheel', {deltaY: 120, bubbles: true, cancelable: true}));
 return [P.corte.axial, P.corte.coronal];
})()"""


def teste_a_roda_vai_para_caudal():
    secao(u"a roda do mouse vai para caudal, pela posição dos cortes")
    import pydicom
    import radai_thumbnail as M
    import radai_viewer as RV
    pasta_c, uid_c = _serie_sintetica(8)
    pasta_p, uid_p = _serie_sintetica(8)
    for nome in os.listdir(pasta_p):
        f = os.path.join(pasta_p, nome)
        ds = pydicom.dcmread(f)
        ds.ImageOrientationPatient = [-1, 0, 0, 0, 1, 0]
        ds.PatientPosition = "FFS"
        ds.save_as(f)
    dc = M.preparar_visor(pasta_c, uid_c)
    dp = M.preparar_visor(pasta_p, uid_p)
    zs = [a["ipp"][2] for a in M.serie_do_bilhete(dp["b"])["arquivos"]]
    checar(u"a série de pés primeiro sai ordenada com o z descendo",
           zs[0] > zs[-1], str(zs[:3]))
    checar(u"cabeça primeiro: o índice cresce para cranial (1)",
           dc.get("cranial") == 1, str(dc))
    checar(u"pés primeiro: o índice cresce para caudal (-1)",
           dp.get("cranial") == -1, str(dp))
    sem = {"arquivos": [{"ipp": []}, {"ipp": []}]}
    plano = {"arquivos": [{"ipp": [0, 0, 5.0]}, {"ipp": [0, 9, 5.0]}]}
    checar(u"  (isca) sem posição, ou sem andar em z: desconhecido (0)",
           M.sentido_cranial(sem) == 0 and M.sentido_cranial(plano) == 0
           and M.sentido_cranial({}) == 0)

    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        checar(u"Chromium e Playwright disponíveis", False, u"PULADO")
        return
    js = RV.JS_PALCO + RV.JS_UM_EIXO
    velho = js.replace(u"V.ir(V.atual + V.rumoCaudal(passo));",
                       u"V.ir(V.atual + passo);")
    sem_plumagem = js.replace(u" cranial: d.cranial,", u"")
    abre = lambda cr: {"js": _UM_EIXO_ABRIR, "abrir": {
        "b": "f" * 32, "cortes": 20, "central": 10, "janela": "mediastino",
        "cranial": cr}}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            r = _roda_no_navegador(nav, js, [
                {"js": _UM_EIXO_RODA % 1}, {"js": _UM_EIXO_RODA % -1},
                {"js": _UM_EIXO_RODA % 0}, abre(1), abre(-1),
                {"js": _PALCO_RODA % 1}, {"js": _PALCO_RODA % -1},
                {"js": _UI_VISOR_RODA % 1}, {"js": _UI_VISOR_RODA % -1},
                {"js": _UI_VISOR_RODA % 0},
                {"js": _UI_VISOR_SENTIDO_DEPOIS % 1},
                {"js": _UI_VISOR_SENTIDO_DEPOIS % -1},
                {"js": _UI_VISOR_SENTIDO_DEPOIS % u"'x'"}])
            checar(u"um eixo, cabeça primeiro: a roda para baixo desce o "
                   u"índice (caudal), e a seta para baixo também",
                   r[0][:2] == [9, 9], str(r[0]))
            checar(u"um eixo, pés primeiro: a roda para baixo sobe o índice "
                   u"(caudal)", r[1][:2] == [11, 11], str(r[1]))
            checar(u"a seta para o lado continua sendo o próximo índice",
                   r[0][2] == 11 and r[1][2] == 11, str((r[0], r[1])))
            checar(u"sem o sentido medido, a roda segue o índice",
                   r[2] == [11, 11, 11], str(r[2]))
            checar(u"o visor aberto pelo /api/umeixo/abrir usa o sentido "
                   u"da série", r[3] == 9 and r[4] == 11, str(r[3:5]))
            checar(u"o visor de três planos: o axial vai para caudal, o "
                   u"coronal segue o índice",
                   r[5] == [9, 16] and r[6] == [11, 16], str(r[5:7]))
            checar(u"o visor modal (uiVisor): cabeça primeiro desce o índice, "
                   u"pés primeiro sobe, sem sentido segue o índice (roda e "
                   u"seta para baixo)",
                   r[7] == [9, 9] and r[8] == [11, 11] and r[9] == [11, 11],
                   str(r[7:10]))
            checar(u"o uiVisor aberto sem o sentido aceita o sentido depois "
                   u"(definirSentido), e valor que não é 1 nem -1 volta ao "
                   u"índice", r[10:13] == [9, 11, 11], str(r[10:13]))
            iscas = _roda_no_navegador(
                nav, js, [{"js": _UI_VISOR_SENTIDO_DEPOIS % 1}],
                trocar=(u"definirSentido: function(c){ cranial = (c === 1 || "
                        u"c === -1) ? c : 0 }",
                        u"definirSentido: function(c){}"))
            checar(u"  (isca) o definirSentido que não guarda o sentido deixa a "
                   u"roda no índice", iscas[0] == 11, str(iscas))
            roda_ui = u"ir(i + rumoCaudal(e.deltaY > 0 ? 1 : -1));"
            iscas = _roda_no_navegador(
                nav, js, [{"js": _UI_VISOR_RODA % 1}],
                trocar=(roda_ui, u"ir(i + (e.deltaY > 0 ? 1 : -1));"))
            checar(u"  (isca) o uiVisor que só soma o índice vai para cranial "
                   u"na cabeça primeiro", iscas[0][0] == 11, str(iscas))
            iscas = _roda_no_navegador(nav, velho, [{"js": _UM_EIXO_RODA % 1}])
            checar(u"  (isca) a roda que só soma o índice vai para cranial "
                   u"na cabeça primeiro", velho != js and iscas[0][0] == 11,
                   str(iscas))
            iscas = _roda_no_navegador(nav, sem_plumagem, [abre(1)])
            checar(u"  (isca) sem passar o sentido do abrir, a roda volta "
                   u"ao índice", sem_plumagem != js and iscas[0] == 11,
                   str(iscas))
        finally:
            nav.close()


def _zoom_ok(r):
    um, mo, pa = r
    return (um.get("z0") == 1.25 and 120 <= um.get("r0", 0) <= 130
            and um.get("p0") == u"false" and um.get("z1") == 1
            and 97 <= um.get("r1", 0) <= 103 and um.get("p1") == u"true"
            and um.get("z2") == 1.25,
            mo.get("z0") == 1.25 and 120 <= mo.get("r0", 0) <= 130
            and mo.get("p0") == u"false" and mo.get("z1") == 1
            and 97 <= mo.get("r1", 0) <= 103 and mo.get("p1") == u"true"
            and mo.get("z2") == 1.25 and mo.get("z3") == 1,
            pa.get("z0") == 1.25 and pa.get("l0") == u"125%"
            and pa.get("z1") == 1 and pa.get("l1") == u"100%")


def teste_o_visor_abre_em_125():
    secao(u"todo visor de imagem da Suite abre em 125%, e «ajustar» volta a caber")
    import radai_viewer as RV
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        checar(u"Chromium e Playwright disponíveis", False, u"PULADO")
        return
    js = RV.JS_PALCO + RV.JS_UM_EIXO
    cen = [{"js": _ZOOM_UM_EIXO}, {"js": _ZOOM_UI_VISOR}, {"js": _ZOOM_PALCO}]
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            r = _roda_no_navegador(nav, js, cen)
            um, mo, pa = _zoom_ok(r)
            checar(u"um eixo (RadaiUmEixo): abre em 1,25, a imagem 25% maior "
                   u"que o quadro, e «ajustar» (marcado) volta a 1 e de novo a "
                   u"1,25", um, str(r[0]))
            checar(u"  o botão diz «ajustar»", r[0].get("txt") == u"ajustar",
                   r[0].get("txt"))
            checar(u"visor modal (uiVisor): o mesmo, e ajustar() volta a 1", mo,
                   str(r[1]))
            checar(u"  o botão diz «ajustar»", r[1].get("txt") == u"ajustar",
                   r[1].get("txt"))
            checar(u"visor de três planos (RadaiPalco): abre em 125%, e "
                   u"«ajustar» volta a 100%", pa, str(r[2]))
            sem = _roda_no_navegador(
                nav, js, cen, trocar=(u"window.UI_VISOR_ZOOM_INICIAL = 1.25;",
                                      u""))
            checar(u"  (isca) sem o zoom inicial da casca, os três abrem em "
                   u"100% e reprovam", not any(_zoom_ok(sem)), str(sem))
            js_um = js.replace(u"V.zoom = (V.zoom === 1) ? V.zoomInicial : 1;",
                               u"")
            iscas = _roda_no_navegador(nav, js_um, cen[:1])
            checar(u"  (isca) o «ajustar» do um eixo que não troca o zoom "
                   u"reprova", js_um != js and not _zoom_ok(
                       iscas + [r[1], r[2]])[0], str(iscas))
            iscas = _roda_no_navegador(
                nav, js, cen[1:2],
                trocar=(u"zoom = (zoom === 1) ? zoomInicial : 1; aplicarZoom();",
                        u""))
            checar(u"  (isca) o «ajustar» do modal que não troca o zoom reprova",
                   not _zoom_ok([r[0]] + iscas + [r[2]])[1], str(iscas))
        finally:
            nav.close()


def teste_a_serie_sem_preambulo_tem_miniatura():
    secao(u"a série sem preâmbulo (sem .dcm) também tem miniatura")
    import pydicom
    from pydicom.dataset import FileMetaDataset
    import radai_thumbnail as M
    pasta, uid = _serie_sintetica(6)
    for nome in os.listdir(pasta):
        f = os.path.join(pasta, nome)
        ds = pydicom.dcmread(f)
        ds.preamble = None
        ds.file_meta = FileMetaDataset()
        os.remove(f)
        pydicom.dcmwrite(os.path.join(pasta, os.path.splitext(nome)[0]), ds,
                         implicit_vr=True, little_endian=True,
                         enforce_file_format=False)
    with open(os.path.join(pasta, sorted(os.listdir(pasta))[0]), "rb") as fh:
        cab = fh.read(132)
    checar(u"o fantoma não tem o DICM no byte 128", cab[128:132] != b"DICM")
    b = M.bilhete(pasta, uid)
    dados, info = M.png(b, 2)
    checar(u"o corte sai em PNG", dados[:4] == b"\x89PNG", str(info))
    c, l = M._janela_auto(b, M.serie_do_bilhete(b))
    checar(u"a janela automática lê o corte central", l > 1.0, str((c, l)))


def teste_as_rotas_do_visor_de_um_eixo():
    secao("as rotas do visor de um eixo")
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except Exception as e:
        checar(u"fastapi e o TestClient disponíveis", False,
               u"PULADO: %s" % type(e).__name__)
        return
    import json
    import radai_thumbnail as M
    import radai_viewseg
    app = FastAPI()
    radai_viewseg.montar(app)
    cli = TestClient(app)
    N = 24
    pasta, uid = _serie_sintetica(N)

    d = cli.post("/api/umeixo/abrir",
                 json={"pasta": pasta, "zip": "", "uid": uid}).json()
    checar(u"abrir devolve o bilhete e a contagem", bool(d.get("b"))
           and d.get("cortes") == N and d.get("central") == M.central(N), str(d))
    checar(u"TC abre em mediastino", d.get("janela") == "mediastino",
           str(d.get("janela")))
    crua = json.dumps(d, ensure_ascii=False)
    checar(u"a resposta NÃO leva o caminho da pasta",
           pasta not in crua and "PAC_UE" not in crua
           and pasta.replace("\\", "\\\\") not in crua, crua[:120])
    b = d.get("b", "")

    r = cli.get("/api/umeixo/corte", params={"b": b, "corte": 3,
                                              "janela": "mediastino"})
    checar(u"o corte sai em PNG", r.status_code == 200
           and r.content[:8] == b"\x89PNG\r\n\x1a\n",
           "%s %s" % (r.status_code, r.headers.get("content-type")))
    etag = r.headers.get("etag", "")
    checar(u"com ETag e guarda privada",
           bool(etag) and "private" in r.headers.get("cache-control", ""),
           "%r %r" % (etag, r.headers.get("cache-control")))
    r2 = cli.get("/api/umeixo/corte",
                 params={"b": b, "corte": 3, "janela": "mediastino"},
                 headers={"If-None-Match": etag})
    checar(u"quem já tem o corte recebe 304, sem PNG", r2.status_code == 304
           and not r2.content, str(r2.status_code))
    r3 = cli.get("/api/umeixo/corte", params={"b": b, "corte": 3,
                                               "janela": "osso"})
    checar(u"janela diferente, etiqueta diferente",
           r3.headers.get("etag", "") not in ("", etag),
           "%r %r" % (etag, r3.headers.get("etag")))
    r4 = cli.get("/api/umeixo/corte", params={"b": "f" * 32, "corte": 0})
    checar(u"bilhete morto é 404", r4.status_code == 404, str(r4.status_code))

    original = M.png
    try:
        M.png = lambda *a, **k: (b"", {"erro": u"não decodifica", "cortes": N,
                                       "corte": 5})
        r5 = cli.get("/api/umeixo/corte", params={"b": b, "corte": 5})
        M.png = lambda *a, **k: (b"", {"sem_imagem": True, "erro": u"RTSTRUCT — x",
                                       "modalidade": "RTSTRUCT"})
        r6 = cli.get("/api/umeixo/corte", params={"b": b, "corte": 7,
                                                   "janela": "pulmao"})
    finally:
        M.png = original
    checar(u"corte que não decodifica é 422 — os outros seguem",
           r5.status_code == 422, str(r5.status_code))
    checar(u"série que não é imagem é 204", r6.status_code == 204,
           str(r6.status_code))

    e = cli.post("/api/umeixo/abrir",
                 json={"pasta": pasta + "_nao_existe", "uid": uid}).json()
    checar(u"pasta que não existe devolve erro, e não levanta",
           bool(e.get("erro")) and not e.get("b"), str(e))

    linhas_z = []
    orig_log_z = M._log_da_estacao
    M._JA_REGISTRADAS.clear()
    try:
        M._log_da_estacao = lambda: linhas_z.append
        z = cli.post("/api/umeixo/abrir", json={
            "pasta": "DICOM/ST0", "uid": uid,
            "zip": "C:\\RADIOTERAPIA_AI\\tmp\\%s\\exame.zip"
                   % PACIENTE_COM_ESPACO
        }).json()
    finally:
        M._log_da_estacao = orig_log_z
    cru_z = json.dumps(z, ensure_ascii=False)
    checar(u"o .zip que sumiu: frase FIXA, sem o caminho",
           z.get("erro") == u"não achei a pasta da série"
           and not _tem_paciente(cru_z) and "RADIOTERAPIA_AI" not in cru_z,
           cru_z[:160])
    checar(u"  e a causa vai para o log da estação, sem o caminho",
           any(u"visor de um eixo, abrir: falhou" in l for l in linhas_z)
           and not any(_tem_paciente(l) for l in linhas_z),
           u" | ".join(linhas_z)[:300])

    linhas = []
    orig_png, orig_log = M.png, M._log_da_estacao
    M._JA_REGISTRADAS.clear()
    try:
        def _explode(*a, **k):
            raise IOError(u"Sem DICOM em \\\\servidor\\imagens\\Patients"
                          u"\\%s\\CT" % PACIENTE_COM_ESPACO)
        M.png = _explode
        M._log_da_estacao = lambda: linhas.append
        r7 = cli.get("/api/umeixo/corte", params={"b": b, "corte": 2})
        r8 = cli.get("/api/umeixo/corte", params={"b": b, "corte": 3})
    finally:
        M.png, M._log_da_estacao = orig_png, orig_log
    checar(u"o 500 leva só o tipo no cabeçalho",
           r7.status_code == 500 and r7.headers.get("x-radai-erro") == "OSError",
           "%s %r" % (r7.status_code, r7.headers.get("x-radai-erro")))
    checar(u"e a causa vai para o log da estação, UMA vez para dois cortes",
           r8.status_code == 500
           and sum(1 for l in linhas if u"falhou com OSError" in l) == 1,
           u" | ".join(linhas)[:300])
    checar(u"sem o caminho do paciente, nem o pedaço depois do espaço", linhas
           and not any(_tem_paciente(l) or u"servidor" in l for l in linhas),
           u" | ".join(linhas)[:300])

    orig_prep = M.preparar_visor
    linhas2 = []
    M._JA_REGISTRADAS.clear()
    try:
        def _explode2(*a, **k):
            raise ValueError(u"C:\\RADIOTERAPIA_AI\\tmp\\%s\\CT"
                             % PACIENTE_COM_ESPACO)
        M.preparar_visor = _explode2
        M._log_da_estacao = lambda: linhas2.append
        f = cli.post("/api/umeixo/abrir",
                     json={"pasta": pasta, "zip": "", "uid": uid}).json()
    finally:
        M.preparar_visor, M._log_da_estacao = orig_prep, orig_log
    checar(u"abrir que levanta: frase fixa e o tipo, sem a mensagem",
           f.get("erro") == u"não consegui abrir a série"
           and f.get("tipo") == "ValueError"
           and not _tem_paciente(json.dumps(f)), str(f))
    checar(u"e a causa dela vai para o log", any(
        u"falhou com ValueError" in l for l in linhas2), u" | ".join(linhas2))
    checar(u"  sem o caminho, nem o pedaço depois do espaço",
           linhas2 and not any(_tem_paciente(l) for l in linhas2),
           u" | ".join(linhas2)[:300])


def teste_o_caminho_com_espaco_nao_vaza_pelo_log():
    secao(u"o caminho com espaco nao vaza pelo log")
    import radai_thumbnail as M
    pac = PACIENTE_COM_ESPACO
    formas = [
        u"Sem DICOM em \\\\servidor\\imagens\\Patients\\%s\\CT" % pac,
        u"Não achei o arquivo C:\\RADIOTERAPIA_AI\\tmp\\%s\\exame.zip."
        % pac,
        u"Exception thrown in SimpleITK ImageFileReader_Execute: "
        u"D:\\a\\SimpleITK\\Code\\IO\\src\\sitkImageReaderBase.cxx:91:\n"
        u"sitk::ERROR: The file \"C:\\TC\\%s\\x.dcm\" does not exist." % pac,
    ]
    d = _tempfile.mkdtemp(prefix="radai_ac_miniatura_espaco_")
    try:
        open(os.path.join(d, pac, u"x.dcm"))
    except OSError as e:
        formas.append(str(e))
    finally:
        os.rmdir(d)
    for k, texto in enumerate(formas):
        linhas = []
        M._JA_REGISTRADAS.clear()
        try:
            raise OSError(texto)
        except OSError as e:
            M.registrar_falha(u"forma %d" % k, e, log=linhas.append)
        tudo = u"\n".join(linhas)
        checar(u"forma %d: nenhum pedaço da pasta do paciente no log" % k,
               bool(linhas) and not _tem_paciente(tudo), tudo[-240:])
        checar(u"  e o caminho vira a marca", u"<caminho>" in tudo, tudo[-240:])
    limpa = M._sem_caminho(formas[2])
    checar(u"no SimpleITK a causa, depois das aspas, fica",
           limpa.endswith(u'"<caminho>" does not exist.')
           and u"\n" in limpa, repr(limpa))
    checar(u"mensagem sem caminho passa intacta",
           M._sem_caminho(u"a série não tem cortes") == u"a série não tem cortes")


def teste_a_causa_vai_para_o_log_uma_vez_e_sem_caminho():
    secao(u"a causa vai para o log, uma vez e sem caminho")
    import radai_thumbnail as M
    M._JA_REGISTRADAS.clear()
    linhas = []

    def _funcao_que_levanta():
        raise IOError(u"Sem DICOM em C:\\RADIOTERAPIA_AI\\tmp\\"
                      u"ISCA_BELTRANO_12345\\CT e \\\\servidor\\imagens\\"
                      u"Patients\\ISCA_BELTRANO_12345")
    try:
        _funcao_que_levanta()
    except IOError as e:
        primeira = M.registrar_falha(u"teste", e, log=linhas.append)
        segunda = M.registrar_falha(u"teste", e, log=linhas.append)
    checar(u"escreve na primeira vez, e não na segunda",
           primeira is True and segunda is False, "%r %r" % (primeira, segunda))
    texto = u"\n".join(linhas)
    checar(u"diz onde e o tipo", u"teste: falhou com OSError" in texto, texto[:200])
    checar(u"os quadros saem como arquivo:linha função",
           u"test_thumbnail.py:" in texto and u"_funcao_que_levanta" in texto,
           texto[:300])
    checar(u"nenhum caminho de paciente, nem de disco, nem de rede",
           u"BELTRANO" not in texto and re.search(r"[A-Za-z]:\\|\\\\", texto) is None,
           texto[:300])
    try:
        raise KeyError("x")
    except KeyError as e:
        checar(u"outro tipo no mesmo lugar escreve de novo",
               M.registrar_falha(u"teste", e, log=linhas.append) is True)

    M._JA_REGISTRADAS.clear()
    vistas = []
    b_hoje = M.bilhete(u"C:\\x\\ISCA_BELTRANO_12345\\CT", u"1.2.3")
    b_amanha = M.bilhete(u"C:\\x\\FANTOMA_JOAO_67890\\CT", u"1.2.4")
    try:
        raise OSError(u"rede caiu")
    except OSError as e:
        c1 = M.registrar_falha(u"visor", e, log=vistas.append, bilhete=b_hoje)
        c2 = M.registrar_falha(u"visor", e, log=vistas.append, bilhete=b_hoje)
        c3 = M.registrar_falha(u"visor", e, log=vistas.append, bilhete=b_amanha)
    checar(u"a mesma série, o mesmo tipo: escreve uma vez só",
           c1 is True and c2 is False, "%r %r" % (c1, c2))
    checar(u"OUTRA série com o mesmo tipo escreve de novo", c3 is True, repr(c3))
    checar(u"e o bilhete não vai para o log",
           not any(b_hoje in l or b_amanha in l for l in vistas),
           u" | ".join(vistas)[:200])
    checar(u"nem fica na memória: só uma impressão dele",
           not any(b_hoje in str(k) for k in M._JA_REGISTRADAS),
           str(sorted(M._JA_REGISTRADAS))[:200])
    teto_velho = M._TETO_REGISTRADAS
    M._JA_REGISTRADAS.clear()
    del M._ORDEM_REGISTRADAS[:]
    try:
        M._TETO_REGISTRADAS = 5
        for k in range(12):
            try:
                raise OSError(u"x")
            except OSError as e:
                M.registrar_falha(u"visor", e, log=lambda _l: None,
                                  bilhete=u"serie %d" % k)
        checar(u"a memória das já registradas respeita o teto",
               len(M._JA_REGISTRADAS) <= 5 and len(M._ORDEM_REGISTRADAS) <= 5,
               "%d %d" % (len(M._JA_REGISTRADAS), len(M._ORDEM_REGISTRADAS)))
    finally:
        M._TETO_REGISTRADAS = teto_velho
    principal = sys.modules.get("__main__")
    tinha = hasattr(principal, "wlog")
    velho = getattr(principal, "wlog", None)
    vistas = []
    try:
        principal.wlog = vistas.append
        try:
            raise RuntimeError("y")
        except RuntimeError as e:
            M.registrar_falha(u"teste do wlog", e)
    finally:
        if tinha:
            principal.wlog = velho
        else:
            del principal.wlog
    checar(u"sem `log` dado, escreve no `wlog` do `__main__`",
           any(u"teste do wlog: falhou com RuntimeError" in l for l in vistas),
           u" | ".join(vistas)[:200])


def teste_a_janela_automatica_e_da_serie():
    secao("a janela automatica e da serie, e nao do corte")
    import radai_thumbnail as M
    checar(u"TC abre em mediastino", M.janela_do_visor("CT") == "mediastino")
    checar(u"RM abre na automática", M.janela_do_visor("MR") == "auto")
    checar(u"sem modalidade, automática", M.janela_do_visor("") == "auto")
    pasta, uid = _serie_sintetica(12)
    b = M.bilhete(pasta, uid)
    import radai_recon3d as R
    vistas, original = [], R.para_png
    try:
        def _captura(arr, centro, largura):
            vistas.append((round(float(centro), 3), round(float(largura), 3)))
            return original(arr, centro, largura)
        R.para_png = _captura
        d1, _i1 = M.png(b, 1, "auto", lado=M.LADO_VISOR)
        d2, _i2 = M.png(b, 6, "auto", lado=M.LADO_VISOR)
    finally:
        R.para_png = original
    checar(u"os cortes saem na janela automática", bool(d1) and bool(d2))
    checar(u"os dois cortes recebem a MESMA janela, a da série",
           len(vistas) == 2 and vistas[0] == vistas[1], str(vistas))
    c, l = M._JANELA_AUTO.get(b, (0, 0))
    checar(u"e ela é positiva e é a guardada para o bilhete",
           l > 0 and vistas and vistas[0] == (round(c, 3), round(l, 3)),
           "%r %r" % ((c, l), vistas))


def main():
    print("test_thumbnail | a grade do DicomBridge, e a fronteira dela")
    try:
        import numpy
    except Exception:
        print("  numpy ausente — a bateria nao roda aqui")
        print("\n" + "=" * 64)
        print("OK: 0 checagens (runtime sem numpy)")
        print("=" * 64)
        return 0
    testes = [teste_o_caminho_nao_viaja_na_url,
              teste_cabecalho_http_e_ascii,
              teste_serie_sem_pixel_nao_e_erro,
              teste_o_erro_nao_vira_laco_infinito,
              teste_a_rota_do_visor_do_bridge_separa_os_casos,
              teste_a_pasta_e_varrida_uma_vez,
              teste_a_reducao_nao_inventa_pixel,
              teste_a_janela_vem_do_recon3d,
              teste_a_miniatura_nao_e_visualizador,
              teste_o_corte_pedido_nao_estoura,
              teste_so_stdlib_e_o_que_o_bundle_tem,
              teste_a_ordem_de_bisseccao,
              teste_a_serie_sem_preambulo_tem_miniatura,
              teste_as_rotas_do_visor_de_um_eixo,
              teste_a_roda_vai_para_caudal,
              teste_o_visor_abre_em_125,
              teste_a_causa_vai_para_o_log_uma_vez_e_sem_caminho,
              teste_o_caminho_com_espaco_nao_vaza_pelo_log,
              teste_a_janela_automatica_e_da_serie]
    todos = set(k for k, v in globals().items()
                if k.startswith("teste_") and callable(v))
    fora = sorted(todos - set(f.__name__ for f in testes))
    checar("todo teste do arquivo esta na lista do main()", not fora,
           ", ".join(fora))
    for t in testes:
        try:
            t()
        except Exception as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
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
