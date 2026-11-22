"""Verifica o rascunho real do Rodar agora e seu trânsito até o planejador de entrega."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import radai_batch as lote
import radai_config as config


class Complementos(unittest.TestCase):
    def test_sem_aceite_tarefa_visivel_ajuda_habilitada_e_previa_sem_da(self):
        import radai_plugin_coronarias
        with tempfile.TemporaryDirectory() as pasta, patch.object(radai_plugin_coronarias, "REGISTRO", Path(pasta)):
            ct = lote.opcoes_da_tela("CT")
            linha, = [it for it in ct["tasks"] if it["task"] == "rocards_lad"]
            self.assertTrue(linha["plugin_bloqueado"])
            self.assertIn("Configurações > Plugins > Coronárias", linha["por_que_travada"])
            proprio = {"id":"antigo", "nome":"Estação", "modalidade":"CT", "estruturas":["heart","rocards_lad"],
                       "merges":[{"nome":"CoracaoDA", "de":["heart","rocards_lad"]}]}
            pedido = {"modalidade":"CT", "modo":"perso", "protocolo_proprio":"antigo",
                      "tasks":{"rocards_lad":1}, "tasks_marcadas":["rocards_lad"]}
            with patch.object(lote, "protocolo_proprio_da_escolha", return_value=proprio):
                previa = lote.previa_da_entrega(pedido)
            self.assertFalse(previa["complementos_previstos"]["rocards_lad"])
            self.assertEqual({it["chave"] for it in previa["oar"]["estruturas"]}, {"heart"})
            self.assertFalse(any(it["chave"] == "rocards_lad" for it in previa["oar"]["fora"]))
            fontes = []
            for nome in ("_linhaTask", "_swHTML", "_ajHTML", "_nomeNaTela", "complementoLigado"):
                inicio = lote.PAGINA.index("function " + nome + "(")
                proxima = lote.PAGINA.index("\nfunction ", inicio + 1)
                fontes.append(lote.PAGINA[inicio:proxima])
            script = "\n".join(fontes) + "\nconst esc=String, window={}; const t=" + json.dumps(linha) + """
t.instalado=true;
const html=_linhaTask(t,true,false,true);
console.log(JSON.stringify({html,ligado:complementoLigado({}, {complementos:{rocards_lad:true}},t)}));
"""
            proc = subprocess.run([shutil.which("node") or "node","-"], input=script, capture_output=True,
                                  text=True, encoding="utf8", timeout=10, check=True)
            estado = json.loads(proc.stdout)
            self.assertFalse(estado["ligado"])
            self.assertRegex(estado["html"], r'<input [^>]+ disabled>')
            self.assertNotIn(" checked", estado["html"])
            self.assertRegex(estado["html"], r'<button (?![^>]*disabled)[^>]*data-p4-aj="task"[^>]*>\?</button>')

    @patch("radai_plugin_coronarias.ativado", new=lambda: True)
    def test_rascunho_de_protocolo_antigo_e_sbrt(self):
        # Usa a configuração real em pasta temporária, sem tocar a instalação.
        with tempfile.TemporaryDirectory() as pasta, patch.dict(os.environ, {"RADAI_CONFIG": str(Path(pasta) / "config.txt")}):
            antigo = {"id": "meu-protocolo-v1", "nome": "Minha pelve", "modalidade": "CT",
                      "estruturas": ["urinary_bladder", "rectum"], "merges": []}
            p = Path(pasta) / config.NOME_DOS_PROTOCOLOS
            n = Path(pasta) / config.NOME_DOS_NOMES
            p.write_text(json.dumps({"protocolos": [antigo]}), encoding="utf8")
            n.write_text(json.dumps({"modo": "proprios", "nomes": {"Bladder": "Vesica_A"}}), encoding="utf8")
            originais = p.read_bytes(), n.read_bytes()
            ct = lote.opcoes_da_tela("CT")
            self.assertIn(antigo["id"], {it["id"] for it in ct["protocolos_proprios"]})
            self.assertEqual(config.nomes_proprios(), {"Bladder": "Vesica_A"})
            rm = lote.opcoes_da_tela("MR")
            self.assertFalse(set(lote.COMPLEMENTOS_CT) & {t["task"] for t in rm["tasks"]})
            self.assertEqual(len([ct["base_item"], *ct["tasks"]]), 23)
            self.assertEqual(sum(it["task"] == "rocards_lad" for it in ct["tasks"]), 1)
            for t in ct["tasks"]:
                if t.get("complemento"):
                    t["instalado"] = True
            for grupo in ct["comparacao"]:
                grupo["instalado"] = True
                for t in grupo.get("tarefas", ()):
                    t["instalado"] = True
            script = self._escolher(ct)
            r = subprocess.run([shutil.which("node") or "node", "-"], input=script,
                               text=True, encoding="utf8", capture_output=True, timeout=20, check=True)
            resultados = json.loads(r.stdout)
            for nome in ("sbrt_pulmao", "sbrt_figado"):
                estado = resultados[nome]
                self.assertTrue(estado["padrao"])
                self.assertNotIn("moose_ribs", estado["antes"]["tasks"])
                self.assertEqual(estado["antes"]["tasks_marcadas"], [])
                serie = lote._com_escolhas_da_tela({"series": [estado["depois"]]})[0]
                e = lote.escolha_da_serie(serie)
                self.assertEqual(e["protocolos"], (nome,))
                self.assertTrue(e["personalizado_derivado"])
                self.assertEqual(e["tasks"]["moose_ribs"], 0)
                self.assertEqual(estado["antes"]["tasks"], {k: v for k,v in estado["depois"]["tasks"].items()
                                                            if k != "moose_ribs"})
                self.assertTrue(lote.torax_pedido(serie))
                self.assertNotIn("moose_ribs", lote.tasks_iniciais(serie)[0])
                self.assertEqual(estado["depois"]["protocolos"], [])
            custom = lote.escolha_da_serie(resultados["proprio"])
            self.assertEqual(custom["protocolo_proprio"], antigo["id"])
            self.assertTrue(custom["personalizado_derivado"])
            self.assertIn("moose_ribs", custom["tasks_marcadas"])
            self.assertFalse(set(lote.tasks_do_perso(custom)) & set(lote.COMPLEMENTOS_CT))
            self.assertEqual(lote.protocolo_proprio_da_escolha(custom)["nome"], antigo["nome"])
            self.assertEqual(lote.protocolo_proprio_da_escolha(custom)["estruturas"], antigo["estruturas"])
            self.assertEqual((p.read_bytes(), n.read_bytes()), originais)
            for nome in ("da_task_off", "da_estrutura_off"):
                escolha = lote.escolha_da_serie(resultados[nome])
                self.assertFalse(lote.coronaria_solicitada(escolha))
                self.assertIn("rocards_lad", escolha["oar_fora"])
                self.assertEqual(escolha["tasks"]["rocards_lad"], 0)
            self.assertTrue(lote.coronaria_solicitada(lote.escolha_da_serie(resultados["da_reposta"])))
            self.assertNotIn("rocards_lad", resultados["da_novo_protocolo"]["tasks"])
            self.assertNotIn("rocards_lad", resultados["da_novo_protocolo"]["oar_fora"])
            self.assertTrue(resultados["uniao_ativa"])
            self.assertEqual(resultados["uniao_optout"]["tasks"]["moose_ribs"], 0)
            self.assertFalse(resultados["full_automatico"])
            self.assertEqual(resultados["full_manual"]["tasks_marcadas"], ["moose_ribs", "jhu_rectum"])
            self._verificar_comparadores(resultados)

    def _verificar_comparadores(self, resultados):
        import radai_moose_engine as moose
        import SimpleITK as sitk
        for caso, esperados in (("legado",("cardiac","body_composition")), ("cardiac",("cardiac",)),
                                ("corpo",("body_composition",)), ("nenhum",())):
            recebida = lote._com_escolhas_da_tela({"series":[resultados["comparadores"][caso]]})[0]
            e = lote.escolha_da_serie(recebida)
            self.assertEqual(lote.comparadores_moose(e), esperados)
            self.assertEqual(lote.motores_da_serie(recebida)[0]["mse"], bool(esperados))
            if not esperados:
                continue
            with patch.object(moose, "disponivel", return_value=(True,"")), \
                 patch.object(moose, "rodar", return_value=(True,"")) as rodar, \
                 patch.object(moose, "masks_da_saida", return_value={}):
                moose.contornar(".", ref=sitk.Image(3,3,3,sitk.sitkInt16), modelos=lote.comparadores_moose(e))
            self.assertCountEqual([c.args[0] for c in rodar.call_args_list], esperados)
        mr = dict(resultados["comparadores"]["cardiac"], modalidade="MR")
        self.assertFalse(lote.comparadores_moose(lote.escolha_da_serie(mr)))

    @staticmethod
    def _escolher(ct):
        # Funções executadas sem DOM pelo Node são as mesmas embutidas na página.
        nomes = ("_ppsDaSerie", "_ppDaSerie", "_travadasPeloPp", "_porTask", "_arrastavel",
                 "complementoLigado", "tasksLigadas", "_soAsDele", "ligarProtocolo",
                 "ligarProtocoloProprio", "ligarSelecaoLivre", "chaveDaTask", "tasksDeFabrica",
                 "protocolosLigados", "protocolos3dLigados", "chavesFinais", "_compBloqueada",
                 "comparacaoDe", "mudarComparador", "reiniciarProtocolo", "payloadDaSerie", "_tirarDoOar")
        fontes = []
        for nome in nomes:
            start = lote.PAGINA.index("function " + nome + "(")
            fim = re.search(r"\n(?:function |var |// GUARDA:)", lote.PAGINA[start:])
            fontes.append(lote.PAGINA[start:start + fim.start()])
        return "\n".join(fontes) + "\nconst opt=" + json.dumps(ct, ensure_ascii=True) + """
const CAMPOS_DA_ESCOLHA=[], s={modalidade:'CT'}, resultado={};
function _opcDaSerie(){return opt}
function modoDe(){return 'perso'}
let e; function escolhaDe(){return e}
function inicio(){return {modo:'perso',prot:{},p3d:{},mao:{},comp:{},oar_fora:{},marcadas:{},complementos:{}}}
for(const cod of ['sbrt_pulmao','sbrt_figado']){
  e=inicio(); ligarProtocolo(s,e,cod,true);
  const antes=payloadDaSerie(s), padrao=!!tasksLigadas(s,e).moose_ribs;
  chaveDaTask(s,e,'moose_ribs',false);
  resultado[cod]={antes,padrao,depois:payloadDaSerie(s)};
}
e=inicio(); ligarProtocoloProprio(s,e,true,'meu-protocolo-v1');
chaveDaTask(s,e,'moose_ribs',true);
resultado.proprio=payloadDaSerie(s);
e=inicio(); e.destinos_complementos={moose_ribs:true}; e.oar_fora={ribs_left:true,ribs_right:true};
resultado.uniao_ativa=!!tasksLigadas(s,e).moose_ribs;
chaveDaTask(s,e,'moose_ribs',false); resultado.uniao_optout=payloadDaSerie(s);
e=inicio(); ligarProtocolo(s,e,'sbrt_pulmao',true); e.anatomia_geral_full=true;
resultado.full_automatico=!!tasksLigadas(s,e).moose_ribs;
chaveDaTask(s,e,'moose_ribs',true); chaveDaTask(s,e,'jhu_rectum',true);
resultado.full_manual=payloadDaSerie(s);
e=inicio(); ligarProtocolo(s,e,'sbrt_pulmao',true);
e.coracao_na_entrega=true; e.destinos_complementos={rocards_lad:true};
chaveDaTask(s,e,'rocards_lad',false); resultado.da_task_off=payloadDaSerie(s);
const SERIES=[s], PREV_ULT={};
function chaveDe(){return 's'}
function pedirPrevia(){} function pintarCarrinho(){}
const botao={closest:()=>({getAttribute:()=>0,querySelectorAll:()=>[]}),getAttribute:()=>'rocards_lad'};
_tirarDoOar(botao,false); resultado.da_reposta=payloadDaSerie(s);
_tirarDoOar(botao,true); resultado.da_estrutura_off=payloadDaSerie(s);
ligarProtocolo(s,e,'sbrt_figado',true); resultado.da_novo_protocolo=payloadDaSerie(s);
e=inicio(); e.comp={mse:1};
resultado.comparadores={legado:payloadDaSerie(s)};
mudarComparador(s,e,'mse_body_composition',false,'mse');
resultado.comparadores.cardiac=payloadDaSerie(s);
mudarComparador(s,e,'mse',true,null);
mudarComparador(s,e,'mse_cardiac',false,'mse');
resultado.comparadores.corpo=payloadDaSerie(s);
mudarComparador(s,e,'mse',false,null);
resultado.comparadores.nenhum=payloadDaSerie(s);
console.log(JSON.stringify(resultado));"""

    @patch("radai_plugin_coronarias.ativado", new=lambda: True)
    def test_coronaria_so_acompanha_destino_cardiaco(self):
        for serie, presente, retirada in (
                ({}, True, False),
                ({"modo": "perso", "protocolos": ["sbrt_pulmao"]}, True, False),
                ({"modo": "perso", "tasks": {"rocards_lad": 0}}, False, True),
                ({"modo": "perso", "oar_fora": ["rocards_lad"]}, False, True),
                ({"modo": "perso", "oar_fora": ["heart"]}, False, False),
                ({"modo": "perso", "tasks": {"rocards_lad": 1}, "oar_fora": ["heart"]}, True, False),
                ({"modo": "perso", "anatomia_geral_full": True}, True, False),
                ({"modo": "perso", "anatomia_geral_full": True, "tasks": {"rocards_lad": 0}}, False, True),
                ({"modo": "perso", "anatomia_geral_full": True, "tasks": {"rocards_lad": 1}}, True, False),
                ({"modalidade": "MR"}, False, False)):
            with self.subTest(serie=serie):
                p = lote.previa_da_entrega(serie)
                self.assertEqual(p["complementos_previstos"]["rocards_lad"], presente)
                self.assertEqual(any(it["chave"] == "rocards_lad" for it in p["oar"]["estruturas"]), presente)
                self.assertEqual(any(it["chave"] == "rocards_lad" for it in p["oar"]["fora"]), retirada)
                self.assertNotIn("rocards_lad", p["tasks"])
        proprio = {"id": "da-e-pulmao", "nome": "DA e pulmão", "modalidade": "CT",
                   "estruturas": ["rocards_lad", "lung_left"], "merges": []}
        with patch.object(lote, "protocolo_proprio_da_escolha", return_value=proprio):
            serie = {"modo": "perso", "modalidade": "CT", "protocolo_proprio": "da-e-pulmao"}
            previa = lote.previa_da_entrega(serie)
            self.assertEqual({it["chave"] for it in previa["oar"]["estruturas"]}, {"rocards_lad", "lung_left"})
            self.assertTrue(previa["complementos_previstos"]["rocards_lad"])
            for veto in ({"oar_fora": ["rocards_lad"]}, {"tasks": {"rocards_lad": 0}}):
                self.assertFalse(lote.previa_da_entrega(dict(serie, **veto))["complementos_previstos"]["rocards_lad"])
        uniao = dict(proprio, estruturas=[], merges=[{"nome":"MinhaUniao", "de":["rocards_lad","lung_left"]}])
        with patch.object(lote, "protocolo_proprio_da_escolha", return_value=uniao):
            previa = lote.previa_da_entrega(serie)
            self.assertTrue(previa["complementos_previstos"]["rocards_lad"])
            self.assertEqual([it["chave"] for it in previa["oar"]["estruturas"]], ["uniao:MinhaUniao"])
            for veto in ({"oar_fora": ["uniao:MinhaUniao"]}, {"tasks": {"rocards_lad": 0}}):
                self.assertFalse(lote.previa_da_entrega(dict(serie, **veto))["complementos_previstos"]["rocards_lad"])

    @patch("radai_plugin_coronarias.ativado", new=lambda: True)
    def test_coronaria_em_cada_protocolo_ct_e_preserva_exclusao_da_estacao(self):
        for protocolo in lote._md().protocolos_de("CT"):
            previa = lote.previa_da_entrega({"modo": "perso", "protocolos": [protocolo["cod"]]})
            chaves = {it["chave"] for it in previa["oar"]["estruturas"]}
            self.assertEqual("heart" in chaves, "rocards_lad" in chaves, protocolo["cod"])
        antigo = {"id": "cardio", "nome": "Cardio", "modalidade": "CT", "estruturas": ["Heart_ai"], "merges": []}
        novo = dict(antigo, da_com_coracao=False)
        self.assertNotEqual(config._conteudo_protocolo(antigo), config._conteudo_protocolo(novo))
        for p, espera in ((antigo, True), (novo, False)):
            guardado, = config._protocolos_do_pacote([p])
            with patch.object(lote, "protocolo_proprio_da_escolha", return_value=guardado):
                for full in (False, True):
                    previa = lote.previa_da_entrega({"modo": "perso", "protocolo_proprio": "cardio", "anatomia_geral_full": full})
                    self.assertTrue(previa["coracao_na_entrega"])
                    self.assertEqual(previa["complementos_previstos"]["rocards_lad"], espera)
                    manual = lote.previa_da_entrega({"modo": "perso", "protocolo_proprio": "cardio",
                                                   "tasks": {"rocards_lad": 1}, "anatomia_geral_full": full})
                    self.assertTrue(manual["complementos_previstos"]["rocards_lad"])

    def test_exclusao_exportada_e_importada_e_colisao_com_uniao(self):
        import radai_config_transferencia as xfer
        import radai_sets
        linhas = radai_sets.estruturas_para_tabela("CT")
        p = {"nome": "Cardio", "modalidade": "CT", "id": "cardio", "estruturas": ["Heart_ai"],
             "merges": [], "da_com_coracao": False}
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            origem, destino = Path(a)/"config.txt", Path(b)/"config.txt"
            config.gravar_protocolo(p, linhas, origem)
            outros = dict(p)
            del outros["da_com_coracao"]
            config.gravar_protocolo(outros, linhas, destino)
            dados = xfer.exportar(origem, [], "8.30.3", ["protocolos"], {})
            pedido = {"dados": dados, "substituir_protocolos": True}
            args = (destino, [], {"CT":linhas}, {})
            resumo = xfer.transferir(pedido, *args)
            self.assertEqual(len(resumo["personalizadas"]["conflitos"]), 1)
            xfer.transferir(dict(pedido, revisao=resumo["revisao"]), *args, aplicar=True)
            self.assertIs(config.ler_protocolos(destino)[0]["da_com_coracao"], False)
        uniao = {"nome":"DA_ai", "de":["Heart_ai","DA_ai"]}
        _, erros = config.conferir_protocolo(dict(outros, merges=[uniao]), linhas)
        self.assertIn("uniao:0", erros)

    @patch("radai_plugin_coronarias.ativado", new=lambda: True)
    def test_previa_dos_membros_da_uniao_e_do_full(self):
        protocolo = {"id":"costelas", "nome":"Arcos", "modalidade":"CT", "estruturas":[],
                     "merges":[{"nome":"ArcosUnidos", "de":["ribs_left","ribs_right"]}]}
        serie = {"modo":"perso", "modalidade":"CT", "protocolo_proprio":"costelas"}
        with patch.object(lote, "protocolo_proprio_da_escolha", return_value=protocolo):
            p = lote.previa_da_entrega(serie)
            self.assertTrue(p["complementos_previstos"]["moose_ribs"])
            self.assertEqual([it["chave"] for it in p["oar"]["estruturas"]], ["uniao:ArcosUnidos"])
            p = lote.previa_da_entrega(dict(serie, oar_fora=["uniao:ArcosUnidos"]))
            self.assertFalse(p["complementos_previstos"]["moose_ribs"])
        serie = {"modo":"perso", "modalidade":"CT", "regioes":["pelve"]}
        normal = lote.previa_da_entrega(serie)
        full = lote.previa_da_entrega(dict(serie, anatomia_geral_full=True))
        self.assertEqual(normal["tasks"], full["tasks"])
        self.assertEqual([a["cod"] for a in full["arquivos"]], ["full"])
        chaves = {it["chave"] for it in full["oar"]["estruturas"]}
        self.assertTrue({"ribs_left","ribs_right","sternum","costal_cartilages"} <= chaves)
        self.assertNotIn("rectum", chaves)
        self.assertEqual(full["complementos_previstos"], {
            "rocards_lad": "heart" in chaves, "moose_ribs": False, "jhu_rectum": False})

    def test_full_so_executa_os_complementos_explicitos(self):
        import radai_study_modelos as study
        saida = SimpleNamespace(engine=SimpleNamespace(), modalidade="CT", _img_lida=object(), log=lambda _:None)
        with patch("radai_ribs_posterior.refinar", side_effect=RuntimeError("teste")) as ribs, \
             patch("radai_rectum_jhu.segmentar", side_effect=RuntimeError("teste")) as jhu:
            for escolhidas in ((), ("moose_ribs",), ("jhu_rectum",), ("moose_ribs","jhu_rectum")):
                masks = {"rectum":object()}
                r = study.aplicar(saida, masks, {}, {"rectum","ribs_left"}, ["pelve"], None,
                                  "cpu", None, full=True, marcadas=escolhidas)
                self.assertTrue(r["pelve_jhu"])
                self.assertNotIn("rectum", masks)
                self.assertEqual(ribs.called, "moose_ribs" in escolhidas)
                self.assertEqual(jhu.called, "jhu_rectum" in escolhidas)
                ribs.reset_mock()
                jhu.reset_mock()

    def test_plano_real_do_gravador_full_e_merge(self):
        import engine
        import radai_output as entrega
        from radai_study_modelos import COSTELAS
        class PlanoRecebido(BaseException):
            pass
        sd = entrega.Saida(engine, ".", ".", "RS.dcm", grade=object(), modalidade="CT")
        base = {k:object() for k in ("rib_left_1","rib_right_1","sternum","costal_cartilages")}
        protocolo = {"nome":"Arcos", "estruturas":[],
                     "merges":[{"nome":"ArcosUnidos","de":["ribs_left","ribs_right"]}]}
        with patch.object(engine, "curar", return_value=(dict(base),{})), \
             patch("radai_study_modelos.aplicar", side_effect=PlanoRecebido) as modelo:
            with self.assertRaises(PlanoRecebido):
                sd.full_e_oar({"total":base}, modo="perso", protocolo=protocolo)
            self.assertEqual(modelo.call_args.args[3] & COSTELAS, {"ribs_left","ribs_right"})
            self.assertFalse(modelo.call_args.kwargs["full"])
            with self.assertRaises(PlanoRecebido):
                sd.full_e_oar({"total":base}, modo="perso", anatomia_geral_full=True)
            self.assertTrue({"ribs_left","ribs_right","sternum","costal_cartilages"} <= modelo.call_args.args[3])
            self.assertTrue(modelo.call_args.kwargs["full"])
            self.assertFalse(modelo.call_args.kwargs["marcadas"])

    def test_todas_as_imagens_e_traducoes(self):
        from radai_acabamento_i18n import FRASES
        legendas = {f[0]: f for f in FRASES}
        pasta = APP / "data" / "ajuda-tasks"
        self.assertEqual({f.stem for f in pasta.glob("*.png")}, set(lote.FONTES_DAS_FIGURAS))
        self.assertFalse(set(lote.CAPTURAS_LOCAIS) & set(lote.FONTES_DAS_FIGURAS))
        for credito in lote.FONTES_DAS_FIGURAS.values():
            for campo in ("url", "licenca", "autor", "titulo"):
                self.assertTrue(credito[campo])
        for grupo in lote.FIGURAS_DAS_TASKS.values():
            for ident, legenda in grupo:
                self.assertTrue((APP / "data" / "ajuda-tasks" / (ident + ".png")).is_file())
                self.assertEqual(len(legendas[legenda]), 12)
        for v in lote.COMPLEMENTOS_CT.values():
            self.assertEqual(len(legendas[v["rotulo"]]), 12)
            self.assertEqual(len(legendas[v["ajuda"]]), 12)
        for mod in ("CT", "MR"):
            catalogo = lote.opcoes_da_tela(mod)
            for task in [catalogo["base_item"], *catalogo["tasks"]]:
                self.assertTrue(task["figuras"], task["task"])
                self.assertTrue(task["fonte_breve"], task["task"])

    def test_captura_facultativa_so_por_nome_e_impressao(self):
        from hashlib import sha256
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp, patch("radai_archive.raiz", return_value=tmp):
            pasta = Path(tmp) / "ajudas-locais"
            pasta.mkdir()
            nome = "costelas-modelos"
            dados = b"figura da estacao de teste"
            (pasta / (nome + ".png")).write_bytes(dados)
            self.assertIsNone(lote._captura_local(nome))
            self.assertIsNone(lote._captura_local("../" + nome))
            with patch.dict(lote.CAPTURAS_LOCAIS, {nome:("moose_ribs", sha256(dados).hexdigest(), "TC")}):
                self.assertEqual(lote._captura_local(nome), dados)


if __name__ == "__main__":
    unittest.main(verbosity=2)
