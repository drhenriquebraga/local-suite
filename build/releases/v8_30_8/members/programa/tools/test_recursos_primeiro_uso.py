"""Exercita a cópia do código em uma estação isolada e a seleção offline de recursos."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
import configurar_ambiente as preparar
from empacotar_instalador import entra


class RecursosDoPrimeiroUso(unittest.TestCase):
    def test_galeria_exige_originais_publicos_e_seis_studys(self):
        preparar._ligar_caminho()
        from radai_fast_config import ORIGEM_STUDY_PUBLICO
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp) / 'fast_previews'
            pasta.mkdir()
            inventario = {}
            perfis = {}
            for ident, mm, finish in [('leve','6',0), ('medio','3',1), ('alto','1.5',4),
                                      ('extra','1.5',4), ('maximo','1.5',4), ('ultra','1.5',4)]:
                nome = f'study-{ident}-stack-001.webp'
                conteudo = f'pagina de teste de {ident}'.encode()
                (pasta / nome).write_bytes(conteudo)
                inventario[nome] = sha256(conteudo).hexdigest()
                perfis[ident] = dict(mm=mm, effective_mm=mm, base_attempts_mm=[mm], finish=finish, body_mm=1.5 if ident=='ultra' else 6, source='RTSTRUCT_STUDY',
                                     pages=[nome], rois={'1': {'name':'Liver', 'color':[1,2,3]}},
                                     labelsBySlice=[['1']])
            manifesto = dict(version=3, protocol='sbrt_lung', case_id='s0102', firstSlice=1, lastSlice=1,
                             total_slices=1, positionsMm=[0], orientation='axial-radiological',
                             superiorAt='last', columns=1, rowsPerPage=1, tileWidth=16, tileHeight=16,
                             profiles=perfis)
            manifesto.update(ORIGEM_STUDY_PUBLICO, author='Jakob Wasserthal, University Hospital Basel')
            arq = pasta / 'tc-study.json'
            arq.write_text(json.dumps(manifesto), encoding='utf-8')
            inventario[arq.name] = sha256(arq.read_bytes()).hexdigest()
            recibo = dict(ORIGEM_STUDY_PUBLICO, version=3, sha256=inventario)
            fonte = pasta.parent / 'fast_preview_sources.json'
            fonte.write_text(json.dumps({'study_public':recibo}), encoding='utf-8')
            self.assertEqual(preparar._previas_publicadas(pasta), set(inventario))
            for chave in ('source_ct_sha256','source_version','source_archive_member','source_archive_url','dataset_doi'):
                errado = recibo.copy()
                errado.pop(chave)
                fonte.write_text(json.dumps({'study_public':errado}), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, chave):
                    preparar._previas_publicadas(pasta)
            fonte.write_text(json.dumps({'study_public':recibo}), encoding='utf-8')
            arq.write_text(json.dumps(dict(manifesto, source_archive_member='outro/ct.nii.gz')), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'source_archive_member'):
                preparar._previas_publicadas(pasta)
            arq.write_text(json.dumps(manifesto), encoding='utf-8')
            (pasta / 'study-medio-stack-001.webp').write_bytes(b'outra imagem com o nome publico')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                preparar._previas_publicadas(pasta)
            del perfis['medio']
            arq.write_text(json.dumps(manifesto), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'seis STUDYs'):
                preparar._previas_publicadas(pasta)

    def test_montagem_preserva_estacao_e_transfere_as_previas(self):
        recursos = {
            "data/dicas-suite.json", "data/fast_preview_sources.json", "data/roteiro-suite.css", "data/roteiro-suite.js",
            "radai_fast_ui.py", "radai_fast_i18n.py", "radai_fast_config.py", "radai_roteiro.py",
        }
        publicadas = preparar._previas_publicadas(ROOT / "app/data/fast_previews")
        recursos.update("data/fast_previews/" + nome for nome in publicadas)
        self.assertIn('tc-study.json', publicadas)
        self.assertNotIn('tc-perfis.json', publicadas)
        for perfil in ('leve','medio','alto','extra','maximo','ultra'):
            self.assertIn(f'study-{perfil}-stack-001.webp', publicadas)
        self.assertFalse(entra('programa/app/data/fast_previews/local.png'))
        self.assertFalse(entra('programa/app/data/fast_previews/caso/study-leve-stack-001.webp'))
        self.assertFalse(entra('programa/app/data/fast_previews/study-6-raw-stack-001.webp'))
        self.assertFalse(entra('programa/app/data/fast_previews/thorax-0.png'))
        privados = {
            "radai_watcher.config": b"GUIA_VISTO=1\n",
            "local-suite-dicas-vistas.json": b'["fast"]',
            "nomes_proprios.json": b'{"exemplo":"nome-de-teste"}',
            "protocolos_proprios.json": b'[{"nome":"protocolo-de-teste"}]',
        }
        with tempfile.TemporaryDirectory() as tmp, patch.object(preparar, "log"):
            alvo = Path(tmp)
            for nome, antes in privados.items():
                (alvo / nome).write_bytes(antes)
            preparar._montar_codigo({"instalar": True, "bundle": alvo})
            extra = alvo / "data/fast_previews/arquivo-da-estacao.png"
            extra.write_bytes(b"isca")
            previa_local = alvo / "ajudas-locais/fast-previews/upper-0.png"
            previa_local.parent.mkdir(parents=True)
            previa_local.write_bytes(b"previa local")
            portateis = {p.relative_to(alvo).as_posix() for p in preparar._arquivos_do_bundle(alvo)}
            self.assertTrue(recursos.issubset(portateis), recursos - portateis)
            self.assertFalse(privados.keys() & portateis)
            self.assertNotIn(extra.relative_to(alvo).as_posix(), portateis)
            self.assertNotIn(previa_local.relative_to(alvo).as_posix(), portateis)
            for nome, antes in privados.items():
                self.assertEqual((alvo / nome).read_bytes(), antes, nome)
                self.assertFalse(entra(nome), nome)
            for nome in recursos:
                self.assertEqual((ROOT / "app" / nome).read_bytes(), (alvo / nome).read_bytes(), nome)
            (alvo / 'data/fast_previews/study-leve-stack-001.webp').write_bytes(b'isca com nome publico')
            with self.assertRaisesRegex(ValueError, 'difere da imagem pública'):
                list(preparar._arquivos_do_bundle(alvo))


if __name__ == "__main__":
    unittest.main()
