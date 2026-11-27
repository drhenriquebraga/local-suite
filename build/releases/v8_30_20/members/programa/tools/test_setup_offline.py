"""Regressões da atualização por SETUP sem rede. Apenas estações temporárias."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ("app", "tools", "build")]
import radai_setup_offline as offline
import radai_atualizar as update
import requisitos
from test_prepare_profiles import ps_run


class SetupOffline(unittest.TestCase):
    def test_instalacao_existente_sem_rede_entra_na_atualizacao(self):
        body = """
$script:Ocupado=$false
$script:Instalado=@{pasta='C:\\Teste';como='teste'}
function ConferirInstalacao {return $script:Instalado}
function PerfilDaInstalacao {return 'full'}
function Sessao {}
function HaRede {throw 'consulta prematura de rede'}
function IniciarPacoteOffline {throw 'bundle solicitado indevidamente'}
function ContinuarComTermos {param($acao,$dados) if ($acao -ne 'atualizar') {throw $acao}}
$r=InstalarOuAtualizar
@{resultado=$r}|ConvertTo-Json -Compress
"""
        self.assertEqual(ps_run(body, ['InstalarOuAtualizar'])['resultado'], 'atualizar')

    def test_primeira_instalacao_offline_pede_bundle(self):
        body = """
$script:Ocupado=$false
$form=[pscustomobject]@{UseWaitCursor=$false}
function ConferirInstalacao {return $null}
function HaRede {return $false}
function IniciarPacoteOffline {param([switch]$SemRede) if (-not $SemRede) {throw 'offline'}}
$r=InstalarOuAtualizar
@{resultado=$r}|ConvertTo-Json -Compress
"""
        self.assertEqual(ps_run(body, ['InstalarOuAtualizar'])['resultado'], 'offline')

    def test_decisao_de_codigo_antes_da_rede(self):
        body = """
$inst=@{pasta='C:\\Teste'}
$script:VERSAO_INSTALADOR='8.30.11'
$script:SetupSemRede=$false
$script:CascataVeioDe=''
$script:aplicou=$false
function VersaoDaPasta {return '8.30.9'}
function Registrar {}
function DescreverUnidade {return 'fixture'}
function VersaoPublicada {throw 'consultou release'}
function HaRede {throw 'consultou a rede'}
function ConfirmarSeRetrocede {return $true}
function PerguntarSeProcessando {return $true}
function RodarAtualizador {param($p,$flags) if ($flags -contains '-SoDecidir') {return 0}
 if ($flags -notcontains '-SomenteLocal') {throw 'modo de galeria incorreto'}; $script:aplicou=$true; return 0}
function FecharJanelasDoApp {return 0}
function AcharInstalacao {return $inst}
function PintarEstado {}
$r=AtualizarApp $inst
@{resultado=$r;aplicou=$script:aplicou}|ConvertTo-Json -Compress
"""
        self.assertEqual(ps_run(body, ['AtualizarApp','MaisNovaQue','ComoNumero']),
                         {'resultado':'codigo','aplicou':True})

    def test_recibo_igual_e_requisitos_divergentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            station = Path(tmp)
            (station / 'python').mkdir()
            (station / 'python/python.exe').touch()
            (station / 'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.30.9\n')
            stamp = dict(requisitos.calcular(ROOT), versao='8.30.9')
            (station / '_requisitos.json').write_text(json.dumps(stamp))
            self.assertEqual(requisitos.comparar_estacao(str(ROOT), tmp), (True, []))
            for bad in (dict(stamp, impressao='outro'), dict(stamp, versao='8.30.8')):
                (station / '_requisitos.json').write_text(json.dumps(bad))
                self.assertFalse(requisitos.comparar_estacao(str(ROOT), tmp)[0])

    def test_selecao_nativa_confere_produto_versao_e_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            station = Path(tmp)
            (station / 'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.30.9\n')
            path = station / 'candidato.zip'
            for ver,product,extra,ok in [('8.30.11','LOCAL_SUITE','',True),('8.30.9','LOCAL_SUITE','',False),
                                          ('8.30.1','LOCAL_SUITE','',False),('8.30.11','OUTRO','',False),
                                          ('8.30.11','LOCAL_SUITE','../arquivo',False)]:
                with ZipFile(path,'w') as z:
                    for key in offline.OBRIGATORIOS:
                        z.writestr(key, f'PROJETO={product}\nPRODUTO=RADIOTERAPIA_AI_LOCAL_SUITE\nVERSAO={ver}\n'
                                   if key==offline.ENTREGA else '')
                    if extra: z.writestr(extra,'')
                with self.subTest(ver=ver,product=product,extra=extra):
                    if ok: self.assertEqual(offline.conferir(path, station, station/'out'), ('8.30.9',ver))
                    else:
                        with self.assertRaises(ValueError): offline.conferir(path, station, station/'out')

    def test_zip_local_em_fluxo_sem_rede_sem_sondagem(self):
        import hashlib
        import io
        import shutil
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from radai_watcher import PortaoDoHost
        app = FastAPI()
        app.add_middleware(PortaoDoHost, porta=8765, estado=app.state)
        with patch.object(update, 'limpar_o_baixado'):
            update.montar(app)
        base = 'http://127.0.0.1:8765'
        headers = {'origin': base, 'content-type': 'application/zip', 'x-radai-setup': 'local-zip',
                   'x-radai-idioma': 'fr'}
        pacote = io.BytesIO()
        with ZipFile(pacote, 'w') as z:
            for chave in offline.OBRIGATORIOS:
                z.writestr(chave, ('PROJETO=LOCAL_SUITE\nPRODUTO=RADIOTERAPIA_AI_LOCAL_SUITE\nVERSAO=8.30.11\n'
                                  if chave == offline.ENTREGA else ''))
            z.writestr('exemplo.bin', bytes(17 * 1024**2))
        dados = pacote.getvalue()
        sha = hashlib.sha256(dados).hexdigest()
        with tempfile.TemporaryDirectory() as tmp, TestClient(app, base_url=base, client=('127.0.0.1',1234)) as c:
            raiz = Path(tmp)
            (raiz/'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.30.9\n')
            (raiz/'python').mkdir()
            (raiz/'python/python.exe').touch()
            (raiz/'radai_lancador.py').touch()
            url = '/api/setup-offline/pacote'

            def receber(programa, pasta, digest):
                self.assertEqual(programa, tmp)
                self.assertEqual(digest, sha)
                self.assertEqual((Path(pasta)/'setup.zip').stat().st_size, len(dados))
                shutil.rmtree(pasta)
                return {'ativo': True}
            with patch.object(update, 'pasta_do_programa', return_value=tmp), patch.object(
                    update, 'o_que_segura', return_value=None), patch.object(offline, 'confirmar', return_value=True) as confirma, patch.object(
                    update, 'abrir_setup_offline', side_effect=receber) as abre:
                self.assertEqual(c.post('/api/setup-offline',json={'acao':'abrir'}).status_code,404)
                for err in ({'origin': 'http://localhost:8765'}, {'sec-fetch-site':'cross-site'},
                            {'x-radai-setup':'x'}, {'content-type':'application/json'}):
                    self.assertEqual(c.post(url,headers=dict(headers,**err),content=b'abc').status_code,403)
                self.assertEqual(c.post(url,headers=headers,content=b'abc').status_code,422)
                self.assertEqual(c.post(url,headers=dict(headers,**{'content-length':'16'}),content=b'abc').status_code,400)
                with patch.object(shutil,'disk_usage',return_value=Mock(free=0)):
                    self.assertEqual(c.post(url,headers=headers,content=dados).status_code,507)
                self.assertEqual(c.post(url,headers=dict(headers,**{'content-length':str(offline.MAX_ZIP+1)}),
                                        content=b'x').status_code,413)
                with patch.dict(update._CTX,recebendo_setup=True):
                    self.assertEqual(c.post(url,headers=headers,content=b'abc').status_code,409)
                self.assertFalse(confirma.called or abre.called)
                confirma.return_value=False
                self.assertEqual(c.post(url,headers=headers,content=dados).json(),{'cancelado':True})
                self.assertFalse(abre.called)
                confirma.return_value=True
                r=c.post(url,headers=headers,content=dados)
                self.assertEqual((r.status_code,r.json()),(200,{'versao':'8.30.11','sha256':sha}))
                confirma.assert_called_with('8.30.9','8.30.11',sha,'fr')
                self.assertEqual(abre.call_count,1)
                self.assertFalse(update._offline_ativo())

    def test_reconfere_digest_antes_de_extrair_e_preserva_runtime(self):
        import hashlib
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.30.9\n')
            for digest_correto in (True, False):
                etapa=root/'temp'
                etapa.mkdir()
                zip_path=etapa/'setup.zip'
                with ZipFile(zip_path,'w') as z:
                    for k in offline.OBRIGATORIOS:
                        z.writestr(k,'PROJETO=LOCAL_SUITE\nPRODUTO=RADIOTERAPIA_AI_LOCAL_SUITE\nVERSAO=8.30.11\n'
                                   if k==offline.ENTREGA else '')
                digest=hashlib.sha256(zip_path.read_bytes()).hexdigest()
                with patch.object(update,'lancar_preparador',return_value=Mock()) as preparar:
                    if digest_correto:
                        offline.executar(tmp,str(etapa),digest)
                        preparar.assert_called_once_with(str(etapa/'extraido'/'programa'),tmp,'8.30.9',offline=True)
                    else:
                        with self.assertRaises(ValueError):
                            offline.executar(tmp,str(etapa),'0'*64)
                        preparar.assert_not_called()
                    self.assertFalse(etapa.exists())
