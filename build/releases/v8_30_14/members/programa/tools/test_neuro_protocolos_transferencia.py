"""Configurações de estações fictícias, sem DICOM e sem modelos instalados."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import radai_config as C
import radai_config_transferencia as T
import radai_neuro_protocolos_io as N


def protocolo(id, nome, roi='Chiasm'):
    return {'id':'p'+id*32,'name':nome,'modality':'CT','plan':{
        'anatomy':'cranio_buti','findings':[], 'rois':{'cranio_buti':[roi]}}}


class NeuroConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cfg = Path(temp.name)/'station.config'
        self.cfg.write_text('DEVICE=cpu\n')
        self.neuro = self.cfg.with_name(N.ARQUIVO)
        self.gravar([protocolo('a','Original')])

    def gravar(self, rows):
        self.neuro.write_text(json.dumps({'schema':N.SCHEMA, 'protocols':rows}),encoding='utf-8')

    def importar(self, doc, **opcoes):
        req = {'dados':doc,'aparencia':{},**opcoes}
        previa=T.transferir(req,self.cfg,[],{},'')
        req['revisao']=previa['revisao']
        T.transferir(req,self.cfg,[],{},'',aplicar=True)
        return previa

    def test_transferencia_sem_plugin_mescla_e_desfaz_na_mesma_transacao(self):
        pacote = T.exportar(self.cfg,[],'teste',['protocolos_neuro'],{})
        self.assertEqual(pacote['secoes']['protocolos_neuro'],N.ler(self.cfg))
        pacote['secoes']['protocolos_neuro']['protocols']=[
            protocolo('b','Original','Brain'),protocolo('c','Outro','Brainstem')]
        previa = self.importar(pacote)
        self.assertEqual(len(previa['personalizadas']['conflitos']),1)
        self.assertEqual([p['name'] for p in N.ler(self.cfg)['protocols']],['Original','Outro'])
        self.assertEqual(N.ler(self.cfg)['protocols'][0]['plan']['rois']['cranio_buti'],['Chiasm'])
        self.importar(pacote,substituir_protocolos=True)
        self.assertEqual(N.ler(self.cfg)['protocols'][0],protocolo('a','Original','Brain'))
        T.desfazer(self.cfg)
        self.assertEqual(N.ler(self.cfg)['protocols'][0],protocolo('a','Original'))

    def test_backup_antigo_e_arquivo_sem_neuro_preservam_protocolos(self):
        antes=T._snapshot(self.cfg); del antes[N.ARQUIVO]
        T._restaurar(self.cfg, antes)
        self.cfg.with_name(T.BACKUP).write_text(json.dumps({'arquivos':antes,'apos':antes,'aparencia':{}}))
        T.desfazer(self.cfg)
        self.importar(T.exportar(self.cfg,[],'antiga',['aparencia'],{}))
        self.assertEqual(N.ler(self.cfg)['protocols'],[protocolo('a','Original')])

    def test_recusa_dados_identificadores_sem_alterar_arquivo(self):
        pacote=T.exportar(self.cfg,[],'teste',['protocolos_neuro'],{})
        pacote['secoes']['protocolos_neuro']['protocols'][0]['patient_id']='inventado'
        antes=self.neuro.read_bytes()
        with self.assertRaises(C.ErroPersonalizacao): self.importar(pacote)
        self.assertEqual(self.neuro.read_bytes(),antes)


if __name__ == '__main__':
    unittest.main()
