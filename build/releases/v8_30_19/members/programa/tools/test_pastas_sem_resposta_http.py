"""Prazos de leitura, vagas locais e desconexão no ASGI real. Usa apenas loopback e pastas sintéticas."""
import contextlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
TESTE_ANTES = "--antes" in sys.argv
if TESTE_ANTES:
    APP = APP.parents[2] / "suite-8318" / "programa" / "app"
sys.path.insert(0, str(APP))

def aguardar(condicao, segundos=4):
    fim = time.monotonic() + segundos
    while not condicao():
        if time.monotonic() > fim:
            raise AssertionError("Prazo da asserção esgotado")
        time.sleep(.015)

class Painel:
    def __init__(self, porta):
        self.porta = porta

    def iniciar(self, rota, corpo=None, timeout=9):
        conn = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=timeout)
        conn.request("POST" if corpo is not None else "GET", rota,
                     json.dumps(corpo) if corpo is not None else None,
                     {"Content-Type": "application/json", "Origin": "http://127.0.0.1:%d" % self.porta})
        return conn

    def pedir(self, rota, corpo=None, timeout=9):
        c = self.iniciar(rota, corpo, timeout)
        try:
            r = c.getresponse()
            bruto = r.read()
            assert r.status == 200, (rota, r.status, bruto[:200])
            return json.loads(bruto)
        finally:
            c.close()

def interromper(conn):
    if conn.sock:
        conn.sock.shutdown(socket.SHUT_RDWR)
    conn.close()

def antes(painel, raiz):
    import radai_batch
    original = os.path.isdir
    entrou = threading.Event()
    sair = threading.Event()
    alvo = str(raiz / "alvo-bloqueado")
    def isdir(path):
        if str(path) == alvo:
            entrou.set()
            sair.wait(3)
            return False
        return original(path)
    with patch.object(radai_batch.os.path, "isdir", side_effect=isdir):
        c = painel.iniciar("/api/lote/conferir_pasta", {"caminho": alvo})
        try:
            assert entrou.wait(2)
            try:
                painel.pedir("/api/status", timeout=.45)
            except (TimeoutError, socket.timeout):
                print("BASELINE 8.30.18 /api/status sem resposta em 450 ms durante isdir bloqueado", flush=True)
            else:
                raise AssertionError("Não reproduziu bloqueio da versão anterior")
        finally:
            sair.set()
            c.getresponse().read()
            c.close()
        assert not painel.pedir("/api/status")["ligado"]

# A injeção é exclusiva do teste. Intercepta toda UNC antes de tocar em arquivos/DNS.
FILHO = r'''
import contextlib,json,os,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import radai_consulta_isolada as iso
operacao,dados=json.load(sys.stdin.buffer)
c=dados.get("caminho") or dados.get("novos",{}).get("ROOT","")
bloqueio = c.replace("/","\\").startswith("\\\\") or c.endswith("LOCAL-BLOCO") or operacao == "mapear_unidade"
if operacao == "dedicado_prever":
    import subprocess
    iso._limitar_descendentes()
    neto=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],
                          stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    Path(sys.argv[2],"neto").write_text(str(neto.pid),encoding="utf8")
    bloqueio=True
if bloqueio:
    Path(sys.argv[2],str(os.getpid())).write_text(operacao,encoding="utf8")
    time.sleep(45)
    raise RuntimeError("Bloqueio não interrompido")
with contextlib.redirect_stdout(sys.stderr):
    resposta=iso._consultar(operacao,dados)
sys.stdout.buffer.write(json.dumps({"dados":resposta}).encode("utf8"))
'''

def candidato(painel, raiz):
    import ctypes
    import radai_batch
    import radai_config
    import radai_varrer
    import radai_consulta_isolada as iso
    criancas = []
    inicio = subprocess.Popen
    marcadores = raiz / "filhos"
    marcadores.mkdir()
    def iniciar(comando, **kwargs):
        assert comando[-1].endswith("radai_consulta_isolada.py"), comando
        p = inicio([sys.executable, "-B", "-c", FILHO, str(APP), str(marcadores)], **kwargs)
        criancas.append(p)
        return p
    def quem_bloqueou():
        return [p for p in criancas if (marcadores / str(p.pid)).is_file() and p.poll() is None]
    def quantidade(n):
        aguardar(lambda:len(quem_bloqueou())==n)

    # As três listagens podem consultar somente a máscara de letras do kernel.
    if os.name == "nt":
        k32 = ctypes.windll.kernel32
        with patch.object(k32, "GetLogicalDrives", return_value=(1 << 2) | (1 << 25)) as mascara, \
             patch.object(k32, "GetDriveTypeW", side_effect=AssertionError("sondou tipo")), \
             patch.object(k32, "QueryDosDeviceW", side_effect=AssertionError("classificou em lote")), \
             patch.object(os.path, "isdir", side_effect=AssertionError("acessou raiz")):
            letras = ["C:\\","Z:\\"]
            assert [u["raiz"] for u in radai_batch.unidades_do_explorador(validade_s=0)] == letras
            assert radai_varrer.letras_de_rede() == letras and radai_config._unidades() == letras
            assert mascara.call_count == 3
    print("PASS GetLogicalDrives em todas as listas, zero sondagens a unidades",flush=True)

    import radai_thumbnail as miniaturas
    bilhete=miniaturas.bilhete(r"\\synthetic-never-contact.invalid\nao_tocar", "fixture123")
    for rota,alvo,atr,corpo in [
            ("/api/lote/miniatura?b="+bilhete,miniaturas,"png_central",None),
            ("/api/lote/corte?b="+bilhete,miniaturas,"png",None),
            ("/api/lote/sentido",radai_batch,"sentido_do_bilhete",{"b":bilhete})]:
        entrou,saiu=threading.Event(),threading.Event()
        def leitor(*args,parar):
            try:
                entrou.set()
                aguardar(parar)
                return None, {}
            finally:
                saiu.set()
        with patch.object(alvo,atr,side_effect=leitor):
            c=painel.iniciar(rota,corpo)
            try:
                assert entrou.wait(4),rota
                t=time.monotonic()
                interromper(c)
                assert saiu.wait(2),rota
                print("PASS %s cancela leitura do bilhete em %.3fs"%(rota.split("?")[0],time.monotonic()-t),flush=True)
            finally:
                c.close()

    pasta_local = raiz / "arquivo-local"
    (pasta_local / "entrada").mkdir(parents=True)
    rede = r"\\synthetic-never-contact.invalid\nao_tocar"
    with patch.object(iso.subprocess,"Popen",side_effect=iniciar), contextlib.ExitStack() as recursos:
        def travar(rota, corpo):
            c = painel.iniciar(rota,corpo)
            recursos.callback(c.close)
            return c
        try:
            um=travar("/api/config/testar", {"caminho":rede})
            quantidade(1)
            dois=travar("/api/pastas/mapear", {})
            quantidade(2)
            antes_n=len(criancas)
            assert painel.pedir("/api/pastas/mapear", {})["codigo"] == "ocupado"
            assert painel.pedir("/api/lote/pastas", {"caminho":rede})["codigo"] == "ocupado"
            assert len(criancas)==antes_n
            t=time.monotonic()
            assert not painel.pedir("/api/status")["ligado"]
            dur_status=time.monotonic()-t
            t=time.monotonic()
            for rota in ("/api/lote/pastas","/api/pastas"):
                r = painel.pedir(rota, {"caminho":str(pasta_local)})
                assert not r["erro"] and r["pastas"][0]["nome"] == "entrada",r
            dur_local=time.monotonic()-t
            assert dur_local<3 and dur_status<1, (dur_local,dur_status)
            print("PASS duas operações bloqueadas; status %.3fs, duas navegações locais %.3fs"%(dur_status,dur_local),flush=True)
            tres=travar("/api/pastas", {"caminho":str(raiz/"LOCAL-BLOCO")})
            quantidade(3)
            assert not painel.pedir("/api/status")["ligado"]
            assert painel.pedir("/api/pastas", {"caminho":str(pasta_local)})["codigo"]=="ocupado"
            t=time.monotonic()
            for c in (um,dois,tres):
                interromper(c)
            quantidade(0)
            assert all(p.poll() is not None for p in criancas)
            print("PASS três processos encerrados após fechar os três clientes em %.3fs"%(time.monotonic()-t),flush=True)
            for rota in ("/api/lote/conferir_pasta","/api/config/testar","/api/pastas","/api/lote/favorita","/api/config"):
                pedido = {"valores":{"ROOT":rede}} if rota=="/api/config" else {"caminho":rede}
                t=time.monotonic()
                resposta = painel.pedir(rota,pedido)
                d=time.monotonic()-t
                assert resposta.get("codigo")=="tempo_esgotado" and resposta.get("erro"), (rota,resposta)
                assert not resposta.get("vazio") and 4.7<d<7.5, (rota,d)
                quantidade(0)
                print("PASS %s %s %.3fs; zero leitores restantes"%(rota,resposta["codigo"],d),flush=True)
            n=len(criancas)
            time.sleep(.45)
            assert len(criancas)==n
            resultado=painel.pedir("/api/lote/conferir_pasta",{"caminho":str(pasta_local)})
            assert resultado["leitura"] and not resultado["erro"]
            assert painel.pedir("/api/config/testar",{"caminho":str(pasta_local)})["escrita"]
            assert list(pasta_local.glob("_radai_teste_escrita*")) == []
            r = painel.pedir("/api/config", {"valores":{"ROOT":str(pasta_local)}})
            assert r["precisa_confirmar"] and r["validacao"]["escrita"], r
            r = painel.pedir("/api/config", {"valores":{"ROOT":str(pasta_local)}, "confirmar_root":True})
            assert r["ok"] and r["salvos"]==["ROOT"], r
            assert painel.pedir("/api/config")["valores"]["ROOT"]==str(pasta_local)
            assert all(p.poll() is not None for p in criancas)
            if os.name=="nt":
                from ctypes import wintypes as W
                import radai_dedicado as dd
                k=ctypes.WinDLL("kernel32",use_last_error=True)
                abrir=k.OpenProcess; abrir.argtypes,abrir.restype=[W.DWORD,W.BOOL,W.DWORD],W.HANDLE
                esperar=k.WaitForSingleObject; esperar.argtypes,esperar.restype=[W.HANDLE,W.DWORD],W.DWORD
                controlador=dd._CONTROLADOR
                with patch.object(controlador,"porta",painel.porta), patch.object(controlador,"antes_da_previa",
                                      return_value=({"total":1, "revisao":"fixture"},None)):
                    p=travar("/api/estacao/dedicado/prever",{})
                    quantidade(1)
                    neto=int((marcadores/"neto").read_text("utf8"))
                    handle=abrir(0x100000,False,neto)
                    assert handle, "sem handle do neto de teste"
                    try:
                        assert esperar(handle,0)==258
                        antes=time.monotonic()
                        interromper(p)
                        assert esperar(handle,2500)==0, "auxiliar sobreviveu ao fechamento da prévia"
                        quantidade(0)
                        print("PASS prévia dedicada: inventário simulado e auxiliar encerrados em %.3fs"%
                              (time.monotonic()-antes),flush=True)
                    finally:
                        k.CloseHandle(W.HANDLE(handle))
            print("PASS nenhuma nova tentativa automática; nova leitura manual e confirmação de ROOT funcionam",flush=True)
        finally:
            for p in criancas:
                if p.poll() is None:
                    p.kill()
                    p.wait(5)

def main():
    with tempfile.TemporaryDirectory(prefix="suite_smb_controlado_") as tmp:
        base = Path(tmp)
        for chave in ("RADAI_CALIB_DIR", "RADAI_TMP", "RADAI_CACHE_TASKS_DIR", "RADAI_FILA_DIR", "RADAI_REGISTRO_DIR",
                      "LOCALAPPDATA", "APPDATA", "RADAI_DATA_DIR", "RADAI_DEDICADO_DIR"):
            pasta=base/chave
            pasta.mkdir()
            os.environ[chave]=str(pasta)
        cfg=base/"suite.config"
        cfg.write_text("ROOT=\nDRY_RUN=1\nLOG_DIR="+str(base/"logs"),encoding="utf8")
        os.environ.update(RADAI_CONFIG=str(cfg), RADAI_MACHINE="QA_HTTP_LOCAL")
        import radai_consent as C
        assert C._caminho().resolve().is_relative_to(base)
        C.registrar_aceite("QA", [k for k,_,_ in C.PONTOS], C.catalogo_termos.catalogo()[0],True,C.catalogo_termos.grupos_opcionais())
        import radai_watcher as W
        import uvicorn
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1",0))
            sock.listen()
            porta=sock.getsockname()[1]
            W.montar_portao_do_host(W.app,porta)
            server=uvicorn.Server(W.config_do_servidor(W.app,porta))
            fio=threading.Thread(target=server.run,kwargs={"sockets":[sock]},daemon=True)
            fio.start()
            try:
                aguardar(lambda:server.started)
                (antes if TESTE_ANTES else candidato)(Painel(porta),base)
            finally:
                server.should_exit=True
                fio.join(7)
                assert not fio.is_alive()
                if W._LOG_FH:
                    W._LOG_FH.close()
                    W._LOG_FH=None

if __name__=="__main__":
    main()
