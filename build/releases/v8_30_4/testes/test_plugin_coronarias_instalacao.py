"""Contratos da instalação base e da pré-carga de pesquisa (sem rede ou exames)."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


from pastas_teste_coronarias import PROGRAMA as BASE
sys.path[:0] = [str(BASE / "app"), str(BASE / "build")]
import configurar_ambiente as cfg
import consentimento_instalador as consent
import empacotar_instalador as setup
import radai_models
import radai_rocards_dependencies as deps
import requisitos
import pacotes_portateis as pacotes


class InstalacaoPlugin(unittest.TestCase):
    def test_aceite_de_coronarias_e_exclusivo_do_preparo_selecionado(self):
        cat = BASE / "app/data/licencas_suite.json"
        pol = consent.carregar(cat.with_name("termos_instalador.json"))
        itens = {it["id"]: it for it in consent.carregar(cat)["itens"]}
        self.assertEqual(itens["rocards_lad"]["perfis"], ["plugin-coronarias"])
        proofs = [{"id":k,"sha256":consent.assinatura(row,pol["condicoes"][k])}
                  for k,row in itens.items() if k in pol["condicoes"] and "full" in row["perfis"]]
        r = {"schema":"local-suite/aceite/2","contexto":"instalador","finalidade":"ensino-pesquisa",
             "revisao_finalidade":pol["revisao_finalidade"],"perfil":"full","usuario_sid":"S",
             "maquina":"ESTACAO","omitidos":[],"itens":proofs}
        with tempfile.TemporaryDirectory() as temp:
            rec = Path(temp)/"recibo.json"
            rec.write_text(json.dumps(r),encoding="utf-8")
            self.assertEqual(consent.validar(cat,rec,"full","S","ESTACAO"),set())
            r.update(perfil="plugin-coronarias",itens=[])
            rec.write_text(json.dumps(r),encoding="utf-8")
            with self.assertRaises(ValueError):
                consent.validar(cat,rec,"plugin-coronarias","S","ESTACAO")
            r["itens"]=[{"id":"rocards_lad","sha256":consent.assinatura(itens["rocards_lad"],pol["condicoes"]["rocards_lad"])}]
            rec.write_text(json.dumps(r),encoding="utf-8")
            self.assertEqual(consent.validar(cat,rec,"plugin-coronarias","S","ESTACAO"),set())

    def test_montagem_exclusiva_e_combinacoes(self):
        from itertools import combinations
        for n in range(1,4):
            for selecao in combinations(pacotes.PROFILES,n):
                with tempfile.TemporaryDirectory() as tmp, patch.object(consent,"exigir") as terms, \
                        patch.object(pacotes,"montar",return_value="ZIP") as montar, patch.object(pacotes.subprocess,"run") as coronarias:
                    pasta=Path(tmp)
                    pacotes.preparar(selecao,pasta)
                    self.assertEqual([c.args[0] for c in terms.call_args_list],[pacotes.PROFILES[k] for k in selecao])
                    self.assertEqual([c.args[0] for c in montar.call_args_list],[k for k in selecao if k!="coronarias"])
                    self.assertEqual(coronarias.called,"coronarias" in selecao)
        with patch.object(consent,"exigir",side_effect=ValueError("cancelado")), patch.object(pacotes,"montar") as build:
            with self.assertRaises(ValueError): pacotes.preparar(["lung-rt"], Path("."))
            build.assert_not_called()

    def test_formato_lung_e_neuro_com_codigo_real_e_recurso_minimo(self):
        import zipfile
        from unittest.mock import patch
        def sample(source, work, recipe):
            f=work/"recurso.bin"
            f.write_bytes(b"teste")
            yield "resources/recurso.bin", f, {"sha256":hashlib.sha256(b"teste").hexdigest(),"size":5}, "models"
        for plugin in ("neuro-rt","lung-rt"):
            with tempfile.TemporaryDirectory() as temp, patch.object(pacotes,"recursos_neuro",sample), patch.object(pacotes,"recursos_lung",sample):
                path=pacotes.montar(plugin,Path(temp))
                with zipfile.ZipFile(path) as z:
                    self.assertIsNone(z.testzip())
                    meta=json.loads(z.read("release-manifest.json"))
                    self.assertEqual(meta["plugin_id"],plugin)
                    for row in meta["files"]:
                        self.assertEqual(hashlib.sha256(z.read(row["path"])).hexdigest(),row["sha256"])
                    self.assertIn("resources/recurso.bin",z.namelist())
                    if plugin=="lung-rt":
                        self.assertTrue(pacotes.lung.inspect_local_source(path)["offline"])
                    else:
                        self.assertEqual(json.loads(z.read("offline-bundle.json"))["schema"],"neuro-rt/local-bundle/1")
                        import radai_neuro_install as sdk
                        pasta=Path(temp)/"inspecao"
                        z.extractall(pasta)
                        self.assertEqual(sdk.inspect_local_source(pasta)["kind"],"offline_bundle")

    def test_preparo_linguas(self):
        idiomas=json.loads((BASE/"packager/languages.json").read_text(encoding="utf-8-sig"))
        expected=set(idiomas["codigos"])-{"pt-BR"}
        for text in ("Montar pacotes do app e dos plugins para levar","Coronárias (ROCardS)","Selecionar pasta de destino","Pacotes preparados"):
            self.assertEqual(set(idiomas["frases"][text]),expected)
        clause=consent.carregar(BASE/"app/data/termos_instalador.json")["condicoes"]["rocards_lad"]
        self.assertEqual(set(clause["trad"]),expected|{"pt-BR"})

    def test_portatil_mesmo_se_montagem_tiver_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            caminhos = ["modelos/ROCardS/models/HEART/saved_model.pb", "registro/aceites/abc.json",
                        "Plugins/neuro/registro.txt", "modelos/moose_ribs/weights.pth", "app.py"]
            for rel in caminhos:
                f = raiz / rel
                f.parent.mkdir(parents=True,exist_ok=True)
                f.touch()
            saida = {p.relative_to(raiz).as_posix() for p in cfg._arquivos_do_bundle(raiz)}
            self.assertEqual(saida, set(caminhos[-2:]))
        self.assertFalse(setup.entra("modelos/rocards/models/LICENSE_WEIGHTS"))
        self.assertFalse(setup.entra("Registro/aceites/estacao/plugin.json"))

    def test_perfis_e_fingerprint(self):
        for p in ["full","lung-rt"]:
            self.assertNotIn("rocards_lad",cfg.modelos_do_perfil({"profile":p}))
        publicado = requisitos.ler(str(BASE))
        self.assertEqual(publicado["impressao"],requisitos.calcular(str(BASE))["impressao"])
        self.assertNotIn("rocards_lad",publicado["modelos"])
        self.assertTrue(requisitos.comparar({"impressao":"904b72cfd6a437b44c8b3f23dc5457ba0790ab7219de060e8f801f44330c21bf"},publicado)[0])

    def test_download_so_apos_escolha(self):
        with self.assertRaises(PermissionError):
            radai_models.baixar("rocards_lad")
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{"RADAI_MODELOS_DIR":d}), \
                patch.object(radai_models,"baixar") as baixar, patch.object(deps,"preparar_runtime") as runtime:
            deps.preparar()
            baixar.assert_called_once_with("rocards_lad",pesquisa_rocards=True)
            runtime.assert_called_once_with(sys.executable,Path(d)/"rocards")
        self.assertEqual(deps.LOCK.read_bytes(),(BASE/"build/requirements-rocards.txt").read_bytes())

    def test_integridade_do_catalogo(self):
        itens = consent.carregar(BASE/'app/data/licencas_suite.json')["itens"]
        for row in itens:
            serialized = json.dumps({k:v for k,v in row.items() if k!="sha256"}, sort_keys=True,ensure_ascii=False,separators=(",",":"))
            self.assertEqual(row["sha256"],hashlib.sha256(serialized.encode()).hexdigest())
            if row["id"] == "rocards_lad" or row["ambientes"] == ["ROCardS / TensorFlow"]:
                self.assertTrue(row["opcional"])
                self.assertEqual(row["ferramenta"], "rocards_lad")
        self.assertEqual((BASE/"app/maintenance/TERMOS_SUITE.ps1").read_bytes(),(BASE/"packager/TERMOS_SUITE.ps1").read_bytes())
        self.assertEqual((BASE/"app/maintenance/consentimento_instalador.py").read_bytes(),(BASE/"build/consentimento_instalador.py").read_bytes())


if __name__ == "__main__":
    unittest.main()

