"""Confere os termos de distribuição com os mesmos ambientes materiais usados pelo pacote."""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import urlsplit

PROG = Path(__file__).resolve().parents[1] / 'programa'
sys.path.insert(0, str(PROG/'build'))
import catalogo_licencas as maker

CAT = PROG/'app/data/licencas_suite.json'
DATA = json.loads(CAT.read_bytes())
ROWS = {r['id']:r for r in DATA['itens']}
ENV = {}


class Catalogo(unittest.TestCase):
    def test_identidade_e_fontes(self):
        self.assertEqual(DATA['schema'], 'local-suite/termos/1')
        self.assertEqual(len(ROWS), len(DATA['itens']))
        self.assertEqual(list(ROWS), sorted(ROWS))
        for key, row in ROWS.items():
            with self.subTest(key=key):
                for field in ('id','titulo','finalidade','autoria','licenca_codigo','licenca_pesos','integracao','fontes','origem','ferramenta','ambientes','evidencia_versao'):
                    self.assertTrue(row[field],field)
                self.assertIsInstance(row['versoes'],list)
                self.assertLessEqual(set(row['perfis']),{'full','lung-rt','plugin-neuro','plugin-lung'})
                self.assertEqual(row['sha256'],maker.item_hash(row))
                for ref in row['fontes']:
                    parsed = urlsplit(ref['url'])
                    self.assertEqual(parsed.scheme,'https',ref)
                    self.assertTrue(parsed.hostname)
                    self.assertFalse(parsed.username or parsed.password)

    def test_tarefas_modelos_restricoes(self):
        self.assertTrue(set(maker.radai_models.MODELOS) <= set(ROWS))
        expected = {r['task'] for r in maker.radai_tasks.CATALOGO}
        self.assertEqual(expected,{r['task'] for r in ROWS.values() if 'task' in r})
        for perfil in ('full','lung-rt'):
            represented = {r['task'] for r in ROWS.values() if 'task' in r and perfil in r['perfis']}
            self.assertEqual(represented,set(maker.config.tasks_do_perfil({'profile':perfil})))
            self.assertTrue(set(maker.config.modelos_do_perfil({'profile':perfil})) <= {k for k,r in ROWS.items() if perfil in r['perfis']})
        self.assertNotIn('lung_vessels_LEGACY',expected)
        self.assertIn('CC BY-NC 4.0',ROWS['rocards_lad']['licenca_pesos'])
        self.assertIn('pesquisa não comercial',ROWS['rocards_lad']['observacoes'].lower())
        self.assertIn('não especifica',ROWS['jhu_rectum']['licenca_pesos'])
        self.assertIn('uso clínico',ROWS['nv_segment_ct']['observacoes'])

    def test_aceite_por_selecao(self):
        for key in ('torch','monai','nnunetv2','tensorflow','keras','simpleitk'):
            self.assertEqual(ROWS['python-'+key]['ferramenta'],'python-'+key)
        optional = [r for r in ROWS.values() if any(p.startswith('plugin-') for p in r['perfis'])]
        self.assertTrue(optional)
        for row in optional:
            self.assertIn(row['selecao_plugin'],('base','recursos-modelos','laudo','laudo_rx'))
            self.assertNotIn('full',row['perfis'])
            self.assertNotIn('lung-rt',row['perfis'])
        self.assertEqual(ROWS['neuro-metastasis-qtim']['perfis'],[])
        self.assertEqual(ROWS['ts-total-v2']['perfis'],[])
        for key in ('cads_open','moose','nv_segment_ct'):
            self.assertTrue(ROWS[key]['opcional'])
            self.assertEqual(ROWS[key]['ferramenta'],key)
        self.assertFalse(ROWS['moose_ribs']['opcional'])

    def test_ambientes_reais_e_avisos(self):
        if not ENV:
            self.skipTest('Informe --base, --runtime e --neuro para comparar com os wheels materiais.')
        locks_tf = maker.ler_lock(PROG/'build/requirements-rocards.txt')
        for env, path in ENV.items():
            seen = {}
            for row in ROWS.values():
                for installed in row.get('instalacoes',[]):
                    if env != installed['ambiente']:
                        continue
                    name = row['distribuicao_python']
                    self.assertNotIn(name,seen)
                    seen[name] = installed['versao']
                    for notice in installed['avisos']:
                        f = path/notice['arquivo']
                        self.assertTrue(f.resolve().is_relative_to(path.resolve()))
                        self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),notice['sha256'],str(f))
                    for binary in installed['binarios_nativos']:
                        self.assertTrue((path/binary).is_file(),binary)
            actual = {maker.normal(d.metadata['Name']):d.version for d in metadata.distributions(path=[str(path)])}
            if env == 'ROCardS / TensorFlow':
                actual = {k:v for k,v in actual.items() if k in locks_tf}
                self.assertEqual(actual,locks_tf)
            self.assertEqual(seen,actual,env)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for k in ('base','runtime','neuro'):
        parser.add_argument('--'+k,type=Path,required=True)
    args = parser.parse_args()
    ENV = {'Python base':args.base,'ROCardS / TensorFlow':args.runtime,'Plugin NEURO RT':args.neuro}
    unittest.main(argv=sys.argv[:1],verbosity=2)
