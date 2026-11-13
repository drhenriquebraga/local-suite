"""Minimal ASGI client keeps the shipped runtime free of test-only httpx."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from fastapi import FastAPI
from test_contour_edit import make_series,E
import radai_contour_edit_api as API


class Client:
    def __init__(self,app):self.app=app
    def request(self,method,url,data=None,origin=None):
        raw=json.dumps(data).encode() if data is not None else b''
        messages=[];received=False;parts=urlsplit(url)
        async def receive():
            nonlocal received
            if received:await asyncio.Event().wait()
            received=True
            return {'type':'http.request','body':raw,'more_body':False}
        async def send(message):messages.append(message)
        headers=[(b'host',b'testserver'),(b'content-type',b'application/json')]
        if origin:headers.append((b'origin',origin.encode()))
        scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':method,'scheme':'http','path':parts.path,'raw_path':parts.path.encode(),'root_path':'','query_string':parts.query.encode(),'headers':headers,'server':('testserver',80),'client':('127.0.0.1',1)}
        asyncio.run(self.app(scope,receive,send))
        status=next(m['status'] for m in messages if m['type']=='http.response.start')
        content=b''.join(m.get('body',b'') for m in messages if m['type']=='http.response.body')
        return status,content
    def post(self,path,data,**kwargs):
        status,content=self.request('POST',API.PREFIX+path,data,**kwargs)
        return status,json.loads(content)


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
        self.uid,self.files=make_series(self.folder)
        def resolve(ticket,source='thumbnail',uid=None):
            if ticket!='known':E.fail('INVALID_TICKET','Escolha a série novamente.')
            return self.folder,self.uid,self.files
        self.mock=patch.object(E,'resolve_ticket',resolve);self.mock.start()
        self.app=FastAPI();API.montar(self.app);self.client=Client(self.app)
    def tearDown(self):
        E._SESSIONS.clear();self.mock.stop();self.tmp.cleanup()
    def open(self):
        status,d=self.client.post('/open',{'b':'known'})
        self.assertEqual(status,200,d);return d
    def mutation(self,d,**extra):return dict(s=d['session'],csrf=d['csrf'],revision=d['revision'],**extra)

    def test_api_full_flow_and_revision_conflicts(self):
        d=self.open();old=d
        status,d=self.client.post('/new-roi',self.mutation(d,name='Manual',color=[255,0,0]));self.assertEqual(status,200,d)
        status,err=self.client.post('/stroke',self.mutation(old,roi=1,plane='axial',index=2,points=[[.5,.5]]));self.assertEqual(status,409)
        status,d=self.client.post('/stroke',self.mutation(d,roi=1,plane='axial',index=2,points=[[.5,.5]],diameter_mm=4));self.assertEqual(status,200,d)
        self.assertTrue(d['can_undo'])
        code,png=self.client.request('GET',API.PREFIX+'/image?s='+d['session']+'&plane=coronal&index=10');self.assertEqual(code,200);self.assertTrue(png.startswith(b'\x89PNG'))
        code,overlay=self.client.request('GET',API.PREFIX+'/overlay?s='+d['session']+'&roi=1&plane=axial&index=2');self.assertEqual(code,200);self.assertTrue(json.loads(overlay)['polygons'])
        status,saved=self.client.post('/save',self.mutation(d));self.assertEqual(status,200,saved)
        code,content=self.client.request('GET',saved['download_url']);self.assertEqual(code,200);self.assertEqual(content[128:132],b'DICM')
        self.assertNotIn(str(self.folder),json.dumps(saved))
        status,result=self.client.post('/close',self.mutation(d));self.assertEqual(status,200)
        code,_=self.client.request('GET',API.PREFIX+'/state?s='+d['session']);self.assertEqual(code,404)

    def test_origin_token_paths_and_payload_rejected(self):
        status,_=self.client.post('/open',{'b':'known'},origin='https://foreign.example');self.assertEqual(status,403)
        status,_=self.client.post('/open',{'b':str(self.folder)});self.assertEqual(status,400)
        d=self.open();bad=self.mutation(d,name='Bad');bad['csrf']='wrong'
        status,_=self.client.post('/new-roi',bad);self.assertEqual(status,403)
        status,_=self.client.post('/import',self.mutation(d,rs='../source.dcm'));self.assertEqual(status,400)
        status,_=self.client.post('/stroke',self.mutation(d,points='x'*(API.MAX_PAYLOAD+1)));self.assertEqual(status,413)

    def test_bounded_sessions(self):
        a=self.open();b=self.open()
        status,_=self.client.post('/open',{'b':'known'});self.assertEqual(status,409)
        self.client.post('/close',self.mutation(a));self.open()


if __name__=='__main__':unittest.main()
