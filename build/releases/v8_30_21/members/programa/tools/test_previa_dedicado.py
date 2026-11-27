import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from fastapi import FastAPI
from starlette.requests import Request
import radai_dedicado as d
import radai_consulta_isolada as iso

def request(method, cookie=''):
    headers={'host':'127.0.0.1:8030','origin':'http://127.0.0.1:8030','sec-fetch-site':'same-origin','content-type':'application/json'}
    if cookie: headers['cookie']=cookie
    async def receive(): return {'type':'http.request','body':b'{}','more_body':False}
    return Request({'type':'http','asgi':{'version':'3.0'},'method':method,'scheme':'http','path':'/','query_string':b'','client':('127.0.0.1',13000),'headers':[(k.encode(),v.encode()) for k,v in headers.items()]},receive)
class Dedicado(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        app=FastAPI()
        with patch.object(d,'pasta_local',return_value=Path(t.name)):
            d.montar(app,{'porta_dedicado':8030,'dedicado_habilitado':lambda:'1'},lambda **kw:{'ok':True}, lambda:None)
        self.routes={r.path.rsplit('/',1)[-1]:r.endpoint for r in app.routes if 'dedicado' in r.path}
        d._CONTROLADOR.fila=lambda:{'total':1,'revisao':'test'}
    async def test_previa_em_estacao_lenta(self):
        with patch.object(iso,'ler',AsyncMock(side_effect=TimeoutError('prazo'))):
            res=await self.routes['prever'](request('POST'))
        self.assertEqual(res.status_code,200)
        self.assertEqual(json.loads(res.body)['itens'],[])
        self.assertTrue(json.loads(res.body)['token'])
    async def test_estado_em_paralelo_nao_sobrescreve_cookie_da_previa(self):
        res=self.routes['estado'](request('GET'))
        self.assertNotIn('set-cookie',res.headers)
    async def test_plano_vazio_normal(self):
        with patch.object(iso,'ler',AsyncMock(return_value=[[],{}])):
            res=await self.routes['prever'](request('POST'))
        self.assertEqual(res.status_code,200);self.assertTrue(json.loads(res.body)['token'])
        self.assertIn('httponly',res.headers['set-cookie'].lower())
    async def test_desconexao_nao_emite_plano(self):
        with patch.object(iso,'ler',AsyncMock(side_effect=ConnectionAbortedError('cliente encerrou'))):
            res=await self.routes['prever'](request('POST'))
        self.assertNotIn('token',json.loads(res.body))
if __name__=='__main__':unittest.main(verbosity=2)
