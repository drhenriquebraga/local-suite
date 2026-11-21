"""Testes sintéticos. A paridade com uma bancada existente exige --paridade e --pesos."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from scipy import ndimage
import SimpleITK as sitk
import pydicom

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.append(str(Path(__file__).resolve().parent))
import radai_ribs_posterior as posterior
import radai_ribs_predict as inferencia
import engine
from radai_geom import Grade
from engine import MascaraCompacta


def _fixture():
    shape = (48, 64, 78)
    ref = sitk.Image(shape[::-1], sitk.sitkInt16)
    masks = {}
    for name, xs in (("rib_left_7", slice(54, 66)), ("rib_right_7", slice(12, 24)),
                     ("vertebrae_T7", slice(35, 43))):
        m = np.zeros(shape, bool)
        m[20:27, 39:45, xs] = True
        masks[name] = MascaraCompacta.de(m)
    pred = np.zeros(shape, np.uint8)
    pred[20:27, 39:45, 39:66] = 7
    pred[20:27, 39:45, 12:39] = 20
    pred[10:13, 37:39, 45:48] = 7
    return ref, masks, pred


def _mock_pred(ref, pred):
    def segmentar(roi, *_):
        start = ref.TransformPhysicalPointToIndex(roi.GetOrigin())[::-1]
        return pred[tuple(slice(a, a + n) for a, n in zip(start, roi.GetSize()[::-1]))]
    return mock.patch.object(inferencia, "predizer", side_effect=segmentar)


class TesteCostelas(unittest.TestCase):
    def test_hu_na_ponta_preserva_base_e_nao_se_propaga_pela_vertebra(self):
        ref, masks, pred = _fixture()
        nome = "rib_left_7"
        base = np.asarray(masks[nome]).copy()
        contato_ts = (23, 42, 42)
        base[contato_ts] = True
        masks[nome] = MascaraCompacta.de(base)
        vetos = {}
        with _mock_pred(ref, pred):
            partes, info = posterior.refinar(ref, masks, nome, vetos=vetos)
        self.assertEqual(info["corrigidas"], 1, info)
        self.assertEqual(set(vetos), {nome, "ribs_left"})
        veto = np.asarray(vetos[nome])
        np.testing.assert_array_equal(veto, np.asarray(vetos["ribs_left"]))
        self.assertTrue(np.any(veto))
        self.assertFalse(np.any(veto & base))
        m = np.asarray(partes[nome])
        self.assertTrue(np.all(m[base]))
        grade = Grade.de_sitk(ref)
        hu = np.full(m.shape, -1000, dtype=np.int16)
        hu[np.asarray(masks["vertebrae_T7"])] = 750
        cortical_nova = (23, 45, 52)
        hu[cortical_nova] = 450
        self.assertFalse(m[cortical_nova])
        self.assertTrue(np.any(engine.refinar_por_hu(m, hu, grade, 300) & veto))
        mod = engine.refinar_por_hu(m, hu, grade, 300, veto=vetos[nome])
        self.assertTrue(mod[cortical_nova])
        self.assertTrue(mod[contato_ts])
        self.assertFalse(np.any(mod & veto))

    def test_veto_no_rtstruct_preserva_planos_e_uniao_com_vertebra(self):
        # Série sintética e releitura por SOPInstanceUID, inclusive após a
        # adaptação do TPS. Cria um conflito conhecido na ROI já gravada.
        from make_test_series import escreve_serie, ROWS, COLS, PIXEL_MM
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(tempfile, "tempdir", tmp):
            pasta = Path(tmp)
            stage = pasta / "ct"
            escreve_serie(stage, "qa-costal", datetime(2026, 1, 1), 12)
            cab = [pydicom.dcmread(p, stop_before_pixels=True) for p in stage.glob("*.dcm")]
            cab.sort(key=lambda d: int(d.InstanceNumber))
            grade = Grade.de_sitk(engine.load_sitk(stage))
            shape = (len(cab), ROWS, COLS)
            costela = np.zeros(shape, bool)
            costela[2:10, 50:65, 42:75] = True
            osso = np.zeros(shape, bool)
            osso[3:9, 51:61, 35:47] = True
            guarda = np.zeros(shape, bool)
            guarda[4:8, 55:60, 39:47] = True
            k = "rib_left_7"
            masks = {k: costela, "vertebrae_T7": osso}
            vetos = {k: MascaraCompacta.de(guarda)}
            original, mapa = engine.build_rtstruct(stage, dict(masks), suavizar_mm=0)
            ds = pydicom.dcmread(original)
            n = mapa[k]
            def reler(d, nome):
                return np.asarray(engine._raster_do_dataset(d, cab, grade, shape, [nome], None)[nome])
            antes = reler(ds, n)
            self.assertTrue(np.any(antes & guarda))
            numeros = {r.ROIName: int(r.ROINumber) for r in ds.StructureSetROISequence}
            meta = {}
            engine._finalizar_rois_terminais(ds, cab, grade, masks, mapa, {"vetos_costais": vetos},
                {}, None, (PIXEL_MM, PIXEL_MM), numeros, {n: [0, 240, 0]}, meta=meta)
            salvo = pasta / "retocado.dcm"
            ds.save_as(salvo)
            np.testing.assert_array_equal(reler(pydicom.dcmread(salvo), n), antes & ~guarda)
            self.assertEqual(meta["acabamento_terminal"]["contato_costovertebral"][k],
                             int(np.count_nonzero(antes & guarda)))
            # O protocolo antigo pode conter uma união vazia ou duplicada. O
            # veto da costela deve respeitar o tecido solicitado pelo operador.
            prep, _ = engine.build_rtstruct(stage, dict(masks), suavizar_mm=0, adiar=True,
                                            vetos_costais=vetos)
            try:
                unido = pasta / "unido.dcm"
                mapa, _ = prep.gravar_selecao(masks, unido, unioes=[
                    {}, {"nome": "CostelaMaisOsso", "de": list(masks)},
                    {"nome": "CostelaMaisOsso", "de": [k]}])
                ds = pydicom.dcmread(unido)
                self.assertFalse(np.any(reler(ds, mapa[k]) & guarda))
                self.assertTrue(reler(ds, mapa["uniao:CostelaMaisOsso"])[5, 57, 43])
            finally:
                prep.liberar()

    def test_pedidos_e_ausencia_de_destino(self):
        self.assertEqual(posterior._pedidos(["Rib01_R", "rib_left_12"]), {"rib_right_1", "rib_left_12"})
        self.assertEqual(len(posterior._pedidos("Ribs_L")), 12)
        self.assertEqual(len(posterior._pedidos("Ribs")), 24)
        with mock.patch.object(inferencia, "predizer") as pred:
            alteradas, info = posterior.refinar(None, {}, ["Lung_L"])
        pred.assert_not_called()
        self.assertEqual((alteradas, info["estado"]), ({}, "ignorado"))

    def test_preserva_osso_lado_grade_e_componente(self):
        ref, masks, pred = _fixture()
        with _mock_pred(ref, pred):
            alteradas, info = posterior.refinar(ref, masks, ["Rib07_L", "rib_right_7"])
        self.assertEqual(info["estado"], "aplicado", info)
        self.assertEqual(info["corrigidas"], 2)
        self.assertGreater(info["voxels_vetados_vertebra"], 0)
        for name, mod in alteradas.items():
            added = np.asarray(mod) & ~np.asarray(masks[name])
            self.assertEqual(mod.shape, masks[name].shape)
            self.assertTrue(np.all(np.asarray(mod)[np.asarray(masks[name])]))
            self.assertFalse(np.any(added & np.asarray(masks["vertebrae_T7"])))
            self.assertTrue(np.all(np.where(added)[2] >= 43) if "left" in name
                            else np.all(np.where(added)[2] < 35))
            self.assertFalse(added[11, 37, 46])
        with _mock_pred(ref, pred):
            unilateral, info = posterior.refinar(ref, masks, "rib_left_7")
        self.assertEqual(set(unilateral), {"rib_left_7"})

    def test_compacta_sem_expandir_e_sem_preencher_fora_do_campo(self):
        ref, masks, pred = _fixture()
        cortical = np.asarray(masks["rib_left_7"])
        borda = np.roll(cortical, -20, axis=0)
        masks["rib_left_7"] = MascaraCompacta.de(borda)
        with mock.patch.object(MascaraCompacta, "cheia", side_effect=AssertionError("expansão densa")), _mock_pred(ref, pred):
            out, info = posterior.refinar(ref, masks, ["rib_left_7", "rib_right_7"])
        self.assertEqual(set(out), {"rib_right_7"}, info)
        self.assertEqual(info["por_costela"]["rib_left_7"]["estado"], "limite_do_campo")
        self.assertEqual(info["estado"], "parcial")
        del masks["vertebrae_T7"]
        with mock.patch.object(inferencia, "predizer") as runner:
            out, info = posterior.refinar(ref, masks, ["rib_right_7"])
        runner.assert_not_called()
        self.assertEqual(info["por_costela"]["rib_right_7"]["estado"], "sem_referencia_vertebral")

    def test_associacao_impede_troca_de_lado_duplicata_ou_nivel_invertido(self):
        def ancoras(pares):
            a, b = np.repeat(np.asarray(pares, np.uint8), 25, axis=0).T
            return posterior._ancoras(a, b)
        self.assertEqual(ancoras([(5, 6), (6, 7)]), {6: 5, 7: 6})
        self.assertEqual(ancoras([(5, 6), (6, 5), (7, 21), (13, 12)]), {})
        self.assertEqual(ancoras([(4, 6), (5, 6), (17, 17)]), {17: 17})

    def test_predicao_danificada_retorna_ts(self):
        ref, masks, pred = _fixture()
        with mock.patch.object(inferencia, "predizer", return_value=pred[:1]):
            out, info = posterior.refinar(ref, masks, "rib_right_7")
        self.assertEqual((out, info["estado"], info["voxels_acrescidos"]), ({}, "falha", 0))
        vetos = {}
        with _mock_pred(ref, pred), mock.patch.object(engine, "_uniao_compacta", side_effect=MemoryError()):
            out, info = posterior.refinar(ref, masks, "rib_right_7", vetos=vetos)
        self.assertEqual((out, vetos, info["estado"], info["corrigidas"]), ({}, {}, "falha", 0))

    def test_retorno_na_grade_original_com_reorientacao_ras(self):
        a = np.zeros((34, 27, 22), np.int16)
        a[8:14, 3:8, 15:21] = 200
        ref = sitk.GetImageFromArray(a)
        ref.SetOrigin((3., 8., -7.))
        ref.SetSpacing((1.5, 1.5, 1.5))
        ref.SetDirection((0., 0., 1., 0., -1., 0., 1., 0., 0.))
        out = inferencia.aplicar_modelo(ref, lambda img: (img[0] > 150).astype(np.uint8))
        self.assertTrue(inferencia._grade_igual(ref, out))
        np.testing.assert_array_equal(sitk.GetArrayFromImage(out), a > 150)


def paridade(base, pesos, relatorio, artefatos=None):
    recorte = base / "clipping-posterior-01"
    foto = sitk.ReadImage(str(base / "CT_torax.nii.gz"))
    def abrir(p):
        img = sitk.ReadImage(str(p))
        if not inferencia._grade_igual(img, foto):
            raise ValueError("Grade diferente da TC em " + p.name)
        return sitk.GetArrayFromImage(img)
    def extrair(array, nomes):
        boxes = ndimage.find_objects(array, max_label=max(nomes))
        return {nome: MascaraCompacta(array.shape, boxes[k - 1], array[boxes[k - 1]] == k)
                for k, nome in nomes.items() if boxes[k - 1] is not None}
    ts = abrir(base / "totalseg.nii.gz")
    ids = {k: posterior.COSTELAS[k - 92] for k in range(92, 116)}
    masks = extrair(ts, ids)
    mapa_v = json.loads((recorte / "vertebras.json").read_text())["labels"]
    masks.update(extrair(abrir(recorte / "vertebras.nii.gz"), {int(k): v for k, v in mapa_v.items()}))
    caixa_ref = json.loads((recorte / "recortes.json").read_text())["bounds_native_half_open"]["posterior"]
    observada = {}
    runner = inferencia.predizer
    def comparar(roi, *params):
        nativa = runner(roi, *params)
        exp = sitk.ReadImage(str(recorte / "clin_CT_ribs_segmentation_posterior_ct.nii.gz"))
        if not inferencia._grade_igual(exp, roi):
            raise ValueError("Recorte de produção difere do recorte de bancada.")
        orig = sitk.GetArrayFromImage(exp)
        observada["diferencas_rotulos_moose"] = int(np.count_nonzero(nativa != orig))
        if artefatos:
            local = sitk.GetImageFromArray(nativa)
            local.CopyInformation(roi)
            sitk.WriteImage(local, str(artefatos / "rotulos_moose_caixa.nii.gz"), True)
        return nativa
    with mock.patch.object(inferencia, "predizer", side_effect=comparar):
        out, info = posterior.refinar(foto, masks, "Ribs", pasta_pesos=pesos)
    esperado = abrir(recorte / "hibrido_posterior.nii.gz")
    produzido = ts.copy()
    for k, nome in ids.items():
        if nome in out:
            area = out[nome].caixa
            alvo = produzido[area]
            alvo[out[nome].recorte(area) & ~masks[nome].recorte(area)] = k
    if artefatos:
        combinado = sitk.GetImageFromArray(produzido)
        combinado.CopyInformation(foto)
        sitk.WriteImage(combinado, str(artefatos / "arcos_hibridos.nii.gz"), True)
    observada.update(resumo=info, caixa_igual=info.get("caixa_xyz") == caixa_ref,
                     diferencas_rotulos_hibrido=int(np.count_nonzero(produzido != esperado)),
                     originais_modificados=int(np.count_nonzero(produzido[ts > 0] != ts[ts > 0])))
    texto = json.dumps(observada, indent=2, ensure_ascii=False)
    if relatorio:
        relatorio.write_text(texto, encoding="utf8")
    print(texto)
    return (observada.get("diferencas_rotulos_moose") == 0 and observada["caixa_igual"]
            and observada["diferencas_rotulos_hibrido"] == 0 and info["corrigidas"] == 18)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--paridade", type=Path)
    parser.add_argument("--pesos", type=Path)
    parser.add_argument("--relatorio", type=Path)
    parser.add_argument("--artefatos", type=Path, help="Pasta local para a verificação do RTSTRUCT")
    args = parser.parse_args()
    if args.paridade:
        if not args.pesos:
            parser.error("--paridade exige --pesos")
        if args.artefatos:
            args.artefatos.mkdir(parents=True, exist_ok=True)
        sys.exit(0 if paridade(args.paridade, args.pesos, args.relatorio, args.artefatos) else 1)
    unittest.main(argv=[sys.argv[0]], verbosity=2)
