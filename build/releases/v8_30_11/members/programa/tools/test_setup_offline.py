"""Regressões da atualização por SETUP sem rede. Apenas estações temporárias."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
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

    def test_chamada_da_tela_so_pode_abrir_escolha_no_windows_local(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        with patch.object(update,'limpar_o_baixado'):
            update.montar(app)
        base = 'http://127.0.0.1'
        with TestClient(app,base_url=base,client=('127.0.0.1',8765)) as client, patch.object(
                update, 'abrir_setup_offline',return_value={'ativo':True}) as abrir:
            url = '/api/setup-offline'
            self.assertEqual(client.post(url,json={'acao':'abrir'}).status_code,403)
            self.assertEqual(client.post(url,headers={'origin':base},json={'acao':'abrir','caminho':'x'}).status_code,400)
            self.assertEqual(client.post(url,headers={'origin':base},json={'acao':'abrir','idioma':'pt-BR'}).json(),{'ativo':True})
            abrir.assert_called_once_with('pt-BR')

