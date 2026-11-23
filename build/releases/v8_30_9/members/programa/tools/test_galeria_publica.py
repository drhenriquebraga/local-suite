"""Prova aquisição inicial, réplica desconectada e rejeição de uma galeria danificada."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "build"))
import galeria_publica as g


class GaleriaPublica(unittest.TestCase):
    def setUp(self):
        td = TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.layers = {"tc-study.json": b'{"version":4}'}
        self.layers.update({f"study-{p}-stack-001.webp": p.encode() for p in
                            ("ct", "leve", "medio", "alto", "extra", "maximo", "ultra")})
        self.archive = self.root / "galeria-esforcos-s0102-v1.zip"
        with ZipFile(self.archive, "w") as z:
            for n,b in self.layers.items():
                z.writestr(n,b)
        recurso = dict(filename=self.archive.name, bytes=self.archive.stat().st_size,
                       sha256=sha256(self.archive.read_bytes()).hexdigest(), url=g.URL_BASE+self.archive.name)
        catalog = dict(version=4, case_id="s0102", resource=recurso,
                       sha256={n:sha256(b).hexdigest() for n,b in self.layers.items()})
        (self.source / "fast_preview_sources.json").write_text(json.dumps(dict(study_public=catalog)),encoding="utf-8")
        self.cache = self.root / "cache"
        self.dest = self.root / "instalada"
        self.offline = Mock(side_effect=AssertionError("consultou a rede"))

    def test_primeiro_download_replica_offline_e_cache(self):
        download = Mock(side_effect=lambda url,p:shutil.copyfile(self.archive,p))
        g.instalar(self.source,self.dest,[],self.cache,download,lambda m:None)
        download.assert_called_once()
        g.instalar(self.source,self.dest,[],self.cache,self.offline,lambda m:None)
        for nome,b in self.layers.items():
            self.assertEqual((self.dest/nome).read_bytes(),b)
        replica = self.root / "replica"
        g.instalar(self.source,replica,[self.dest],self.root / "cache-vazio",self.offline,lambda m:None)
        (replica / "tc-study.json").write_bytes(b"galeria antiga")
        g.instalar(self.source,replica,[],self.cache,self.offline,lambda m:None)
        self.assertEqual((replica / "tc-study.json").read_bytes(),self.layers["tc-study.json"])
        self.offline.assert_not_called()

    def test_zip_incorreto_falha_antes_de_publicar(self):
        self.dest.mkdir()
        obsoleto = self.dest / "tc-study.json"
        obsoleto.write_bytes(b"anterior")
        with self.assertRaisesRegex(ValueError,"SHA-256"):
            g.instalar(self.source,self.dest,[],self.cache,lambda url,p:p.write_bytes(b"parcial"),lambda m:None)
        self.assertEqual(list(self.dest.iterdir()),[obsoleto])
        self.assertEqual(obsoleto.read_bytes(),b"anterior")
        self.assertFalse((self.cache/self.archive.name).exists())


if __name__ == "__main__":
    unittest.main()

