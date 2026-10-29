# -*- coding: utf-8 -*-
import importlib.util
import contextlib
import uuid
import json
import os
from pathlib import Path
import stat
import shutil
import threading
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE))
import _componentes
_componentes.ligar_caminho()
import _cleanup
_cleanup.adotar_prefixo("radai_atualizar89_")
BASE = Path(_cleanup.temporaria("radai_atualizar89_"))
os.environ["RADAI_CALIB_DIR"] = str(BASE / "calib")
os.environ["RADAI_REGISTRO_DIR"] = str(BASE / "registro")
os.environ["RADAI_NAVEGADOR"] = "0"
import radai_atualizar as A
import radai_janela as J
import radai_lancador as L

ROOT = Path(_componentes.raiz_da_suite())
UPDATE = (ROOT / "packager" / "UPDATE.ps1").read_text(encoding="utf-8-sig")

CAPTURA_CS = r'''using System; using System.Text; using System.Runtime.InteropServices;
public static class CapturaConsole89 {
 [StructLayout(LayoutKind.Sequential)] public struct Coord { public short X,Y; }
 [StructLayout(LayoutKind.Sequential)] public struct Rect { public short L,T,R,B; }
 [StructLayout(LayoutKind.Sequential)] public struct Info { public Coord Size,Cursor; public short Attr; public Rect Window; public Coord Max; }
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern IntPtr CreateFile(string n,uint a,uint s,IntPtr x,uint c,uint f,IntPtr t);
 [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int n);
 [DllImport("kernel32.dll")] static extern uint GetFileType(IntPtr h);
 [DllImport("kernel32.dll")] static extern bool GetConsoleScreenBufferInfo(IntPtr h,out Info i);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool ReadConsoleOutputCharacter(IntPtr h,StringBuilder b,uint n,Coord c,out uint r);
 [StructLayout(LayoutKind.Explicit, CharSet=CharSet.Unicode, Size=20)] public struct Registro { [FieldOffset(0)] public ushort Tipo; [FieldOffset(4)] public int Down; [FieldOffset(8)] public ushort Repeticoes; [FieldOffset(10)] public ushort Virtual; [FieldOffset(12)] public ushort Scan; [FieldOffset(14)] public char Unicode; [FieldOffset(16)] public uint Control; }
 [DllImport("kernel32.dll")] static extern bool FlushConsoleInputBuffer(IntPtr h);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern bool WriteConsoleInput(IntPtr h,Registro[] r,uint n,out uint w);
 public static void DigitarR() { var h=CreateFile("CONIN$",0xC0000000,3,IntPtr.Zero,3,0,IntPtr.Zero); if(!FlushConsoleInputBuffer(h)) throw new Exception("entrada de console nao limpa"); var r=new Registro[4]; for(int i=0;i<4;i++){r[i].Tipo=1;r[i].Repeticoes=1;r[i].Down=i%2==0?1:0;r[i].Virtual=(ushort)(i<2?82:13);r[i].Unicode=(char)(i<2?82:13);} uint n; if(!WriteConsoleInput(h,r,4,out n)) throw new Exception("entrada de console nao escrita"); }
 public static uint Tipo() { return GetFileType(GetStdHandle(-11)); }
 public static string Texto() { var h=CreateFile("CONOUT$",0x80000000,3,IntPtr.Zero,3,0,IntPtr.Zero); Info i; if(!GetConsoleScreenBufferInfo(h,out i)) return ""; uint n; var b=new StringBuilder(20000); var c=new Coord(); ReadConsoleOutputCharacter(h,b,(uint)Math.Min(19999,i.Size.X*i.Size.Y),c,out n); return b.ToString(); }
}'''


@contextlib.contextmanager
def desktop_isolado():
    import ctypes
    from ctypes import wintypes
    u=ctypes.WinDLL("user32",use_last_error=True)
    u.GetProcessWindowStation.restype=wintypes.HANDLE
    u.GetUserObjectInformationW.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    u.GetUserObjectInformationW.restype=wintypes.BOOL
    u.CreateDesktopW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p]
    u.CreateDesktopW.restype=wintypes.HANDLE
    u.CloseDesktop.argtypes=[wintypes.HANDLE]
    u.CloseDesktop.restype=wintypes.BOOL
    n=wintypes.DWORD()
    estacao=u.GetProcessWindowStation()
    u.GetUserObjectInformationW(estacao,2,None,0,ctypes.byref(n))
    if not n.value: raise ctypes.WinError(ctypes.get_last_error())
    nome_estacao=ctypes.create_unicode_buffer(n.value//ctypes.sizeof(ctypes.c_wchar))
    if not u.GetUserObjectInformationW(estacao,2,nome_estacao,n.value,ctypes.byref(n)):
        raise ctypes.WinError(ctypes.get_last_error())
    nome="RadaiConsole89_"+uuid.uuid4().hex
    h=u.CreateDesktopW(nome,None,None,0,0x01ff,None)
    if not h: raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield nome_estacao.value+"\\"+nome
    finally:
        if not u.CloseDesktop(h): raise ctypes.WinError(ctypes.get_last_error())


def inicio():
    spec = importlib.util.spec_from_file_location("inicio_atualizar89", ROOT / "tools" / "test_inicio.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(os.name == "nt", "atualizador Windows")
class Atualizacao89(unittest.TestCase):
    def pasta(self, nome):
        p = BASE / nome
        p.mkdir(parents=True, exist_ok=True)
        return p

    def test_console_real_com_pai_redirecionado_e_compativel_com_88(self):
        if os.name != "nt":
            self.skipTest("console Win32")
        with desktop_isolado() as desktop:
            for legado,compartilhada in ((False,False),(True,False),(True,True)):
                with self.subTest(iniciador88=legado,console_compartilhada=compartilhada):
                    base = self.pasta("console_%s_%s" % (legado,compartilhada))
                    (base / "packager").mkdir(exist_ok=True)
                    resultado = base / "console.json"
                    prefixo = UPDATE[:UPDATE.index("function UnidadesLocais")]
                    corpo = prefixo + "\nAdd-Type -TypeDefinition '" + CAPTURA_CS.replace("'", "''").replace("\n", " ") + "'\n"
                    corpo += "$script:LogDoAtualizador='%s'\nif(-not $script:ConsoleExtra){Start-Transcript -Path $script:LogDoAtualizador -Append | Out-Null}\n" % str(base/"atualizador.log").replace("'","''")
                    corpo += "Diga 'LOCAL_SUITE_CONSOLE_VISIVEL_89'\nStart-Sleep -Milliseconds 150\n"
                    corpo += "[CapturaConsole89]::DigitarR()\n$entrada=[RadaiConsoleAtualizacao]::Ler()\n"
                    corpo += "$r=@{entrada=$entrada;tipo=[CapturaConsole89]::Tipo();visivel=([CapturaConsole89]::Texto().Contains('LOCAL_SUITE_CONSOLE_VISIVEL_89'));extra=$script:ConsoleExtra}\n"
                    corpo += "[IO.File]::WriteAllText('%s',($r|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))\nexit 0\n" % str(resultado).replace("'", "''")
                    (base / "packager" / "UPDATE.ps1").write_text(corpo, encoding="utf-8-sig")
                    app = str(Path(A.__file__).parent)
                    pai = ("import sys,subprocess;sys.path.insert(0,%r);import radai_atualizar as A\n" % app)
                    pai += "def criar(cmd,**kw):\n"
                    pai += " if %r: kw['stdin']=subprocess.DEVNULL\n" % legado
                    pai += " if %r: kw['creationflags']=0\n" % compartilhada
                    pai += " si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=4;si.lpDesktop=%r;kw['startupinfo']=si\n" % desktop
                    pai += " return subprocess.Popen(cmd,**kw)\n"
                    pai += "p=A.lancar_atualizador(%r,%r,123,popen=criar)\nsys.exit(p.wait(timeout=35))\n" % (str(base), str(base))
                    with (base / "pai.log").open("wb") as log:
                        outer=subprocess.STARTUPINFO();outer.dwFlags=subprocess.STARTF_USESHOWWINDOW;outer.wShowWindow=4;outer.lpDesktop=desktop
                        r = subprocess.run([sys.executable, "-B", "-c", pai], stdout=log, stderr=subprocess.STDOUT, timeout=45, startupinfo=outer, creationflags=subprocess.CREATE_NEW_CONSOLE if compartilhada else subprocess.CREATE_NO_WINDOW)
                    self.assertEqual(r.returncode, 0, (base / "pai.log").read_text(errors="replace"))
                    d = json.loads(resultado.read_text(encoding="utf-8-sig"))
                    if not compartilhada: self.assertTrue(d["visivel"], d)
                    self.assertEqual(d["entrada"],"R",d)
                    self.assertEqual(d["tipo"], 1 if legado else 2, d)
                    self.assertEqual(d["extra"], legado and not compartilhada, d)
                    texto_pai=(base/"pai.log").read_text(errors="replace")
                    self.assertEqual("LOCAL_SUITE_CONSOLE_VISIVEL_89" in texto_pai, compartilhada)
                    self.assertIn("LOCAL_SUITE_CONSOLE_VISIVEL_89",(base/"atualizador.log").read_text(encoding="utf-8-sig",errors="replace"))

    def test_prontidao_exige_pid_do_atualizador(self):
        base = self.pasta("pronto")
        class P:
            pid = 987
            def poll(self): return None
        arquivo = base / "pronto_nonce.json"
        P.radai_sinal_pronto=str(arquivo);P.radai_chave_pronto="nova"
        arquivo.write_text(json.dumps({"pronto": True, "pid": 987, "chave":"nova"}), encoding="utf-8")
        self.assertTrue(A.esperar_atualizador_pronto(str(base), P(), teto_s=1))
        arquivo.write_text(json.dumps({"pronto": True, "pid": 123, "chave":"nova"}), encoding="utf-8")
        self.assertFalse(A.esperar_atualizador_pronto(str(base), P(), teto_s=0.02, dormir=lambda t: None))
        arquivo.write_text("{", encoding="utf-8")
        self.assertFalse(A.esperar_atualizador_pronto(str(base), P(), teto_s=0.02, dormir=lambda t: None))

    def test_nonce_novo_rejeita_sinal_antigo_com_pid_reutilizado(self):
        base=self.pasta("nonce")
        (base/"packager").mkdir(exist_ok=True)
        antigo=base/"_atualizador_pronto.json"
        antigo.write_text(json.dumps({"pronto":True,"pid":777,"chave":"antiga"}),encoding="utf-8")
        class P:
            pid=777
            def poll(self): return None
        sinais=[]
        def criar(cmd,**kw):
            caminho=cmd[cmd.index("-SinalPronto")+1]
            self.assertFalse(Path(caminho).exists())
            sinais.append(caminho)
            return P()
        a=A.lancar_atualizador(str(base),str(base),123,popen=criar)
        b=A.lancar_atualizador(str(base),str(base),123,popen=criar)
        self.assertNotEqual(a.radai_sinal_pronto,b.radai_sinal_pronto)
        self.assertNotEqual(a.radai_chave_pronto,b.radai_chave_pronto)
        self.assertFalse(A.esperar_atualizador_pronto(str(base),a,teto_s=0.01,dormir=lambda t:None))
        sinal=Path(a.radai_sinal_pronto)
        sinal.write_text(json.dumps({"pronto":True,"pid":777,"chave":"antiga"}),encoding="utf-8")
        self.assertFalse(A.esperar_atualizador_pronto(str(base),a,teto_s=0.01,dormir=lambda t:None))
        sinal.write_text(json.dumps({"pronto":True,"pid":777,"chave":a.radai_chave_pronto}),encoding="utf-8")
        self.assertTrue(A.esperar_atualizador_pronto(str(base),a,teto_s=0.1))
        sinal.write_text(json.dumps({"pronto":False,"pid":777,"chave":a.radai_chave_pronto,"erro":"sem escrita"}),encoding="utf-8")
        self.assertFalse(A.esperar_atualizador_pronto(str(base),a,teto_s=1))
        self.assertTrue(antigo.exists())

    def test_flag_de_perfil_e_argumento_real_com_espacos(self):
        if os.name!="nt": self.skipTest("CommandLineToArgvW")
        perfil=str(BASE/"perfil com espacos"/"radai_janela")
        self.assertEqual(J.perfil_comprovado_para_fechar('"C:\\Program Files\\Chrome\\chrome.exe" "--user-data-dir=%s"' % perfil),perfil)
        self.assertEqual(J.perfil_comprovado_para_fechar('msedge.exe --user-data-dir "%s"' % perfil),perfil)
        for linha in ('chrome.exe', 'chrome.exe --user-data-dir=',
                      'chrome.exe "https://site/?x=--user-data-dir=%s"' % perfil,
                      'chrome.exe "texto --user-data-dir=%s"' % perfil,
                      'chrome.exe --user-data-dir=relativo',
                      'chrome.exe "--user-data-dir=%s" "--user-data-dir=%s"' % (perfil,perfil),
                      'outro.exe "--user-data-dir=%s"' % perfil):
            self.assertEqual(J.perfil_comprovado_para_fechar(linha),"",linha)

    def test_janela_pronta_exige_tela_da_versao_nova_visivel(self):
        class PF:
            def existe(self,h): return True
            def classe(self,h): return J.CLASSE_DA_JANELA
            def pid(self,h): return 321
            def visivel(self,h): return True
            def minimizada(self,h): return False
            def linha_de_comando(self,p): return 'msedge.exe "--user-data-dir=%s"' % J.perfil_esperado_do_app()
        with patch.object(J,"_JANELAS",{1:{"pid":321,"versao":"8.9"}}), patch.object(J,"VERSAO_DA_TELA","8.9"):
            self.assertTrue(J.pronta_para_atualizacao(PF()))
            J._JANELAS[1]["versao"]="8.8"
            self.assertFalse(J.pronta_para_atualizacao(PF()))
            J._JANELAS[1]["versao"]="8.9"
            pf=PF();pf.minimizada=lambda h:True
            self.assertFalse(J.pronta_para_atualizacao(pf))
            pf=PF();pf.pid=lambda h:999
            self.assertFalse(J.pronta_para_atualizacao(pf))

    def test_fechamento_exige_classe_pid_e_perfil_completo(self):
        perfil = str(BASE / "perfil" / "radai_janela")
        outro = str(BASE / "pessoal" / "radai_janela")
        class PF:
            fechadas = []
            def janelas(self): return [1, 2, 3, 4, 5]
            def existe(self,h): return h not in self.fechadas
            def classe(self,h): return "Outra" if h == 3 else J.CLASSE_DA_JANELA
            def pid(self,h):
                if h == 5:
                    self.n = getattr(self,"n",0)+1
                    return 50+self.n
                return h*10
            def linha_de_comando(self,p):
                if p == 20: return 'chrome.exe --user-data-dir="%s"' % outro
                if p == 40: return 'chrome.exe --type=renderer --user-data-dir="%s"' % perfil
                return 'msedge.exe --user-data-dir="%s"' % perfil
            def fechar(self,h): self.fechadas.append(h);return True
        pf=PF()
        self.assertEqual(J.fechar_para_atualizar(pf=pf,perfil=perfil), {"ok":True,"janelas":1})
        self.assertEqual(pf.fechadas,[1])
        self.assertFalse(J.fechar_para_atualizar(pf=pf,perfil=str(BASE/"pessoal"))["ok"])

    def test_janela_trocada_ou_resistente_nao_e_fechada_a_forca(self):
        if os.name!="nt": self.skipTest("argv Windows")
        perfil=str(BASE/"janela em teste"/"radai_janela")
        outro=str(BASE/"pessoal"/"radai_janela")
        class PF:
            fechadas=[];linhas={};classes={}
            def janelas(self): return [1,2,3]
            def existe(self,h): return True
            def pid(self,h): return h
            def classe(self,h):
                self.classes[h]=self.classes.get(h,0)+1
                return "Outra" if h==2 and self.classes[h]>1 else J.CLASSE_DA_JANELA
            def linha_de_comando(self,p):
                self.linhas[p]=self.linhas.get(p,0)+1
                return 'chrome.exe "--user-data-dir=%s"' % (outro if p==1 and self.linhas[p]>1 else perfil)
            def fechar(self,h): self.fechadas.append(h);return True
        pf=PF()
        d=J.fechar_para_atualizar(pf=pf,perfil=perfil,teto_s=0)
        self.assertEqual(pf.fechadas,[3])
        self.assertEqual(d,{"ok":False,"janelas":0,"pendentes":1})

    def test_processos_exigem_entrada_ou_descendencia_e_criacao(self):
        t=inicio();base=self.pasta("processos")
        funcs=t._funcoes_ps1(UPDATE)
        nomes=("_Prefixo","PythonDaPasta","SeloDoProcesso","EntradaDoApp","ProcessoDaPasta","ProcessosDoApp")
        prefixo=UPDATE[:UPDATE.index("function UnidadesLocais")]
        fonte=prefixo+"\n"+"\n".join(funcs[n] for n in nomes)+"\n"
        local=str(base).replace("'","''")
        fonte+=r"""
$base='%s'
$exe=Join-Path $base 'python\python.exe'
$watcher=Join-Path $base 'radai_watcher.py'
$fora=Join-Path $base 'outro.py'
function FakeP($id,$pai,$cmd,$criado,$executavel) { return [pscustomobject]@{Name='python.exe';ProcessId=$id;ParentProcessId=$pai;CommandLine=$cmd;CreationDate=$criado;ExecutablePath=$executavel} }
$hora=[datetime]'2026-10-28T00:00:00'
$script:Fakes=@(
 (FakeP 101 1 ('"'+$exe+'" "'+$watcher+'"') $hora $exe),
 (FakeP 102 101 ('"'+$exe+'" -c "from multiprocessing.spawn import spawn_main"') $hora.AddSeconds(1) $exe),
 (FakeP 103 1 ('"'+$exe+'" "'+$fora+'" "'+$watcher+'"') $hora $exe),
 (FakeP 104 101 ('"C:\fora\python.exe" -c "pass"') $hora 'C:\fora\python.exe')
)
function Get-CimInstance { param($ClassName,$Filter,$ErrorAction)
 if($Filter -match 'ProcessId=(\d+)'){return @($script:Fakes|Where-Object {$_.ProcessId -eq [int]$Matches[1]})}
 return $script:Fakes
}
$primeiros=@(ProcessosDoApp $base 1)
$script:Fakes=@($script:Fakes|Where-Object {$_.ProcessId -ne 101})
$orfao=ProcessoDaPasta 102 $base
($script:Fakes|Where-Object {$_.ProcessId -eq 102}).CreationDate=$hora.AddMinutes(5)
($script:Fakes|Where-Object {$_.ProcessId -eq 102}).ParentProcessId=1
$depois=@(ProcessosDoApp $base 1)
$reutilizado=ProcessoDaPasta 102 $base
@{primeiros=$primeiros;orfao=$orfao;depois=$depois;reutilizado=$reutilizado}|ConvertTo-Json -Compress
""" % local
        prova=base/"processos.ps1";prova.write_text(fonte,encoding="utf-8-sig")
        rc,saida=t._rodar_ps(str(prova),[],{})
        self.assertEqual(rc,0,saida[-1000:])
        d=json.loads(next(l for l in reversed(saida.splitlines()) if l.strip().startswith("{")))
        self.assertEqual(d["primeiros"],[101,102],d)
        self.assertTrue(d["orfao"],d)
        self.assertEqual(d["depois"],[],d)
        self.assertFalse(d["reutilizado"],d)

    def test_sucessor_abre_janela_e_timeout_nao_e_sucesso(self):
        class Proc:
            def poll(self): return None
        chamadas=[]
        kw=dict(escrever=lambda t:None,travar=lambda p:True,aguardar=lambda *a:True,
                instancia=lambda p:(L.LIVRE,None),anterior=lambda p:None,
                carregando=lambda p,u:str(BASE/"carregando.html"),
                abrir=lambda *a,**k:chamadas.append(a) or True,
                subir=lambda *a:Proc(),sucessor=123,abrir_sucessor=True)
        estado,rc=L.lancar("http://127.0.0.1:9876/",esperar=lambda *a:(L.NO_AR,0),**kw)
        self.assertEqual((estado,rc),(L.NO_AR,0));self.assertEqual(len(chamadas),1)
        estado,rc=L.lancar("http://127.0.0.1:9876/",esperar=lambda *a:(L.DEMOROU,0),**kw)
        self.assertEqual((estado,rc),(L.DEMOROU,L.RC_REABERTURA_NAO_PRONTA))
        self.assertEqual(len(chamadas),2)

    def test_painel_rejeita_pid_antigo_versao_errada_e_outro_programa(self):
        from http.server import HTTPServer, BaseHTTPRequestHandler
        t=inicio();base=self.pasta("contrato_painel")
        atual={"radai":True,"pid":222,"aqui":"8.9","janela_pronta":True};pedidos=[]
        class H(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_POST(self):
                pedidos.append((self.headers.get("Origin"),json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))))))
                corpo=json.dumps(atual).encode()
                self.send_response(200);self.send_header("Content-Length",str(len(corpo)));self.end_headers();self.wfile.write(corpo)
        srv=HTTPServer(("127.0.0.1",0),H);porta=srv.server_address[1]
        thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
        fonte=t._funcoes_ps1(UPDATE)["PainelNovo"]
        prova=base/"painel.ps1"
        prova.write_text(fonte+"\n$script:MotivoReabrir=''\nif(PainelNovo %d '8.9' 111){exit 0}else{exit 9}\n" % porta,encoding="utf-8-sig")
        try:
            for dado,esperado in (({"radai":True,"pid":111,"aqui":"8.9","janela_pronta":True},9),
                                  ({"radai":True,"pid":222,"aqui":"8.8","janela_pronta":True},9),
                                  ({"pid":222,"aqui":"8.9"},9),
                                  ({"radai":True,"pid":222,"aqui":"8.9","janela_pronta":False},9),
                                  ({"radai":True,"pid":222,"aqui":"8.9","janela_pronta":True},0)):
                atual.clear();atual.update(dado)
                rc,saida=t._rodar_ps(str(prova),[],{})
                self.assertEqual(rc,esperado,saida)
            self.assertEqual(pedidos,[("http://127.0.0.1:%d" % porta,{"acao":"estado"})]*5)
        finally:
            srv.shutdown();srv.server_close();thread.join(3)

    def test_pagina_perdida_antes_de_fechando_se_recupera(self):
        node=shutil.which("node")
        if not node:
            spec=importlib.util.find_spec("playwright")
            candidato=Path(spec.origin).parent/"driver"/"node.exe" if spec else None
            node=str(candidato) if candidato and candidato.is_file() else None
        self.assertTrue(node,"Node do ambiente de desenvolvimento e necessario a prova JavaScript")
        js=A.JS.replace("@TETO_REABERTURA@","600000")
        js=js[js.index(">")+1:js.rfind("</script>")]
        gancho=" function pintar(d){"
        self.assertIn(gancho,js)
        js=js.replace(gancho," window.__prova89={pintar:pintar,armar:function(){atualizando=true;pid0=111;reabrindo=false}};\n"+gancho,1)
        antes="""global.window={addEventListener:function(){}};global.document={readyState:'loading',addEventListener:function(){}};
global.sessionStorage={getItem:function(){return ''},setItem:function(){}};
var tarefas=[],destinos=[];global.setTimeout=function(f){tarefas.push(f);return tarefas.length};global.clearTimeout=function(){};
global.location={replace:function(p){destinos.push(p)}};
global.fetch=function(){return Promise.resolve({ok:true,json:function(){return Promise.resolve({pid:222})}})};
"""
        depois="""
(async function(){
 window.__prova89.armar();window.__prova89.pintar(null);
 if(tarefas.length!==1) throw Error('perda do motor nao iniciou recuperacao');
 tarefas.shift()();await new Promise(function(r){setImmediate(r)});
 if(destinos.join(',')!=='/') throw Error('PID novo nao voltou ao programa');
 destinos=[];window.__prova89.armar();window.__prova89.pintar({pid:222,etapa:'livre'});
 if(destinos.join(',')!=='/') throw Error('pulou fechando e nao recuperou');
 console.log('OK recuperacao sem observar fechando');
})().catch(function(e){console.error(e);process.exitCode=1});
"""
        r=subprocess.run([node,"-e",antes+js+depois],capture_output=True,text=True,encoding="utf-8",timeout=20)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_update_confirma_pid_e_versao_em_http(self):
        t=inicio(); base=str(self.pasta("painel"));pac=t._pacote_leve(base,"8.9")
        _,inst=t._instalacao_leve(base,"8.8",pac,t._porta_livre())
        rc,saida=t._rodar_ps(str(Path(pac)/"packager"/"UPDATE.ps1"),["-Destino",inst,"-Python",sys.executable,"-SemPerguntar","-Reabrir","-TetoReabrirS","8"],{"RADAI_ATALHOS_NA_RAIZ":"1","LOCALAPPDATA":str(Path(base)/"ad")})
        self.assertEqual(rc,0,saida[-1500:])
        self.assertIn("Painel da v8.9 confirmado",saida)
        self.assertIn("ATUALIZADO. versao 8.8 -> 8.9",saida)
        for etapa in ("1/5","2/5","3/5","4/5","5/5"): self.assertIn(etapa,saida)

    def test_update_sem_painel_nao_anuncia_sucesso(self):
        t=inicio();base=str(self.pasta("sem_painel"));pac=t._pacote_leve(base,"8.9")
        (Path(pac)/"app"/"radai_lancador.py").write_text("pass\n",encoding="utf-8")
        _,inst=t._instalacao_leve(base,"8.8",pac,t._porta_livre())
        rc,saida=t._rodar_ps(str(Path(pac)/"packager"/"UPDATE.ps1"),["-Destino",inst,"-Python",sys.executable,"-SemPerguntar","-Reabrir","-TetoReabrirS","1"],{"RADAI_ATALHOS_NA_RAIZ":"1","LOCALAPPDATA":str(Path(base)/"ad")})
        self.assertNotEqual(rc,0,saida[-1000:])
        self.assertIn("reabertura nao foi confirmada",saida)
        self.assertNotIn("ATUALIZADO. versao",saida)

    def test_falha_do_sinal_aborta_antes_de_encerrar_ou_copiar(self):
        t=inicio();base=str(self.pasta("sinal_sem_pasta"));pac=t._pacote_leve(base,"8.9")
        _,inst=t._instalacao_leve(base,"8.8",pac,t._porta_livre())
        pronto=Path(pac)/"nao_existe"/"pronto.json"
        rc,saida=t._rodar_ps(str(Path(pac)/"packager"/"UPDATE.ps1"),["-Destino",inst,"-Python",sys.executable,"-SemPerguntar","-Reabrir","-SinalPronto",str(pronto),"-ChavePronto","prova"],{"RADAI_ATALHOS_NA_RAIZ":"1","LOCALAPPDATA":str(Path(base)/"ad")})
        self.assertNotEqual(rc,0,saida[-1000:])
        self.assertIn("ANTIGO",(Path(inst)/"engine.py").read_text())
        self.assertNotIn("Encerrando o motor antigo",saida)
        self.assertNotIn("3/5  Copiando",saida)
        self.assertFalse((Path(inst)/"reaberto.txt").exists())

    def test_preflight_reprova_antes_de_copiar(self):
        if os.name!="nt": self.skipTest("permissao de escrita Win32")
        t=inicio();base=str(self.pasta("preflight"));pac=t._pacote_leve(base,"8.9")
        _,inst=t._instalacao_leve(base,"8.8",pac,t._porta_livre())
        alvo=Path(inst)/"engine.py";alvo.chmod(stat.S_IREAD)
        pronto=Path(pac)/"_atualizador_pronto.json"
        try:
            rc,saida=t._rodar_ps(str(Path(pac)/"packager"/"UPDATE.ps1"),["-Destino",inst,"-Python",sys.executable,"-SemPerguntar","-Reabrir","-SinalPronto",str(pronto)],{"RADAI_ATALHOS_NA_RAIZ":"1","LOCALAPPDATA":str(Path(base)/"ad")})
            self.assertNotEqual(rc,0,saida[-1000:]);self.assertTrue(pronto.exists())
            self.assertIs(json.loads(pronto.read_text(encoding="utf-8-sig"))["pronto"],False)
            self.assertIn("ANTIGO",alvo.read_text())
            self.assertNotIn("ATUALIZADO. versao",saida)
        finally: alvo.chmod(stat.S_IWRITE|stat.S_IREAD)


if __name__ == "__main__":
    unittest.main(verbosity=2)