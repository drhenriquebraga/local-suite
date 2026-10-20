# -*- coding: utf-8 -*-
import hashlib
import os

VERSOES = {
    "python": "3.10.11",
    "totalsegmentator": "2.18.0",
    "nnunetv2": "2.7.0",
    "torch": "2.5.1+cu121",
    "monai": "1.4.0",
}

LICENCAS = [
    {"componente": "Python", "versao": VERSOES["python"],
     "licenca": "PSF License", "restritiva": False,
     "origem": "https://www.python.org/ftp/python/",
     "resumo": u"Runtime portátil, sem instalação e sem administrador. "
               u"Licença permissiva, sem restrição de uso."},
    {"componente": "TotalSegmentator", "versao": VERSOES["totalsegmentator"],
     "licenca": "Apache-2.0", "restritiva": False,
     "origem": "https://github.com/wasserth/TotalSegmentator",
     "resumo": u"É ele que reconhece os órgãos no fluxo principal. Licença "
               u"permissiva: não restringe o uso, inclusive comercial. O "
               u"próprio autor declara que NÃO é dispositivo médico e não se "
               u"destina a uso clínico."},
    {"componente": "nnU-Net", "versao": VERSOES["nnunetv2"],
     "licenca": "Apache-2.0", "restritiva": False,
     "origem": "https://github.com/MIC-DKFZ/nnUNet",
     "resumo": u"A arquitetura sobre a qual o TotalSegmentator foi treinado. "
               u"Os autores pedem que seja citada junto."},
    {"componente": "PyTorch e bibliotecas de apoio",
     "versao": VERSOES["torch"],
     "licenca": "BSD-3-Clause, MIT, Apache-2.0", "restritiva": False,
     "origem": "https://pypi.org",
     "resumo": u"SimpleITK, pydicom, rt-utils, nibabel, NumPy, SciPy, "
               u"FastAPI, uvicorn. Todas permissivas."},
    {"componente": "MONAI (código do bundle de inferência)",
     "versao": VERSOES["monai"],
     "licenca": "Apache-2.0", "restritiva": False,
     "origem": "https://github.com/Project-MONAI/VISTA",
     "resumo": u"A biblioteca que executa o bundle, e o grafo de inferência "
               u"(`configs/inference.json`) que a NVIDIA não publica. É "
               u"código permissivo; os PESOS vêm da NVIDIA, no item seguinte."},
    {"componente": u"NV-Segment-CT (NVIDIA) — PESOS",
     "versao": u"vista3d_pretrained_model",
     "licenca": "NVIDIA Open Model License Agreement", "restritiva": False,
     "origem": "https://huggingface.co/nvidia/NV-Segment-CT",
     "resumo": u"Permite uso comercial: «Models are commercially usable» "
               u"(LICENSE, linha 224). É o mesmo peso do MONAI VISTA-3D — "
               u"sha256 idêntico, medido nos dois arquivos —, publicado pela "
               u"NVIDIA sob este contrato; a publicação sob a NVIDIA License "
               u"3.3 («research or evaluation purposes only») não entra no "
               u"pacote. O CAVEAT CLÍNICO NÃO SAI JUNTO COM O COMERCIAL: o "
               u"cartão do modelo diz «for research purposes and not for "
               u"clinical usage». Ler «comercialmente usável» como «liberado "
               u"para rotina» é o erro que esta frase existe para impedir."},
    {"componente": u"CADS (variante open) — PESOS",
     "versao": "v1.0.0 · Dataset556_GC256",
     "licenca": "CC BY-SA 4.0", "restritiva": False,
     "origem": "https://github.com/murong-xu/CADS",
     "resumo": u"Permite uso comercial. O SHAREALIKE só alcança obra "
               u"derivada do peso (fine-tune), e não o contorno que sai "
               u"dele. É a variante `open` de propósito: as outras duas são "
               u"restritas, e existe uma livre que serve."},
    {"componente": u"MOOSE (ENHANCE.PET) — PESOS",
     "versao": u"moosez-v.3.1.3 · Dataset888_Cardiac e Dataset778_Body_composition",
     "licenca": "CC BY 4.0", "restritiva": False,
     "origem": "https://github.com/ENHANCE-PET/MOOSE",
     "resumo": u"Permite uso comercial, SEM ShareAlike — e EXIGE atribuição, "
               u"que é a metade da CC BY que se esquece. Lida no arquivo "
               u"`MODEL_LICENSE` do repositório, e não num badge: badge é "
               u"cartaz, não ato de licenciamento. São dois pesos e "
               u"dezesseis estruturas — as quatro câmaras do coração, o "
               u"miocárdio, a artéria pulmonar e a composição corporal —, "
               u"nove delas sem equivalente livre no pacote. Sai em arquivo "
               u"próprio (`MSE_`): o protocolo de delineamento do grupo é de "
               u"medicina nuclear, não de radioterapia."},
    {"componente": u"Níveis linfonodais de cabeça e pescoço (Weissmann et al.)",
     "versao": "Task110_HNLNFixed",
     "licenca": "CC0-1.0", "restritiva": False,
     "origem": "https://github.com/putzfn/"
               "HNLNL_autosegmentation_trained_models",
     "resumo": u"Domínio público — a licença mais permissiva do pacote, sem "
               u"exigir sequer atribuição (que damos assim mesmo). O artigo "
               u"é Weissmann et al., Front Oncol 2023. 20 níveis cervicais, "
               u"treinados pelo consenso de Grégoire et al. 2014 (a "
               u"atualização de 2013), que saem com nome neutro (LNL01 a "
               u"LNL20)."},
    {"componente": u"CT Brain Segmentation Radiotherapy (Buti et al.) — PESOS",
     "versao": u"nnUNetTrainer__nnUNetPlans__3d_fullres",
     "licenca": "MIT", "restritiva": False,
     "origem": "https://huggingface.co/GregoryButi/"
               "CT_Brain_Segmentation_Radiotherapy",
     "resumo": u"Permite uso comercial. Tronco encefálico e quiasma em TC, "
               u"que entram também no OAR; cerebelo, ventrículos e linha "
               u"média só no FULL."},
]


def restritivas():
    return [l for l in LICENCAS if l["restritiva"]]


def permissivas():
    return [l for l in LICENCAS if not l["restritiva"]]


ARTEFATOS = {
    # GUARDA: artefato rolante (a roda do pip) muda na origem; o hash dele e o
    # que a origem publica, e o hash prova identidade, nao autenticidade.
    "cache/pip-26.2.1-py3-none-any.whl": {
        "sha256": "71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e",
        "bytes": 1816632, "componente": "pip",
        "origem_publica_o_hash": True,
        "opcional": False},
    "cache/python-embed.zip": {
        "sha256": "608619f8619075629c9c69f361352a0da6ed7e62f83a0e19c63e0ea32eb7629d",
        "bytes": 8629277, "componente": "Python",
        "opcional": False},
    "ts/Dataset258_lung_vessels_248subj/nnUNetTrainer__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth": {
        "sha256": "d34156a092a832bc0d765891b0b3a2a47099cd2fcee3a0fa138e966e39aca6b9",
        "bytes": 246834171, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset291_TotalSegmentator_part1_organs_1559subj/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth": {
        "sha256": "98c429f89fd9b3b08890fbb2b4c08c365ad4655fdcadb45efaa29380129fd890",
        "bytes": 251697787, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset292_TotalSegmentator_part2_vertebrae_1532subj/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth": {
        "sha256": "7022f71829ef00aa14d790a7667bc18eb1691f2fe5b0a38c475862abc84c2457",
        "bytes": 251848251, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset293_TotalSegmentator_part3_cardiac_1559subj/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth": {
        "sha256": "189010ac67fec3f1704df7547306d0067eabaaf620e0a46a1bdd183afa0800e4",
        "bytes": 251268859, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset294_TotalSegmentator_part4_muscles_1559subj/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth": {
        "sha256": "655eb40de03aa3de7348b69d7569a1cc3a2dc7969a11c0d60a7331e07df11c28",
        "bytes": 251633339, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset295_TotalSegmentator_part5_ribs_1559subj/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth": {
        "sha256": "a674364c60b304fbd56feccdd95f8d0fe0c45a5bfa1ef25815516e4dde04d3fc",
        "bytes": 251846011, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset298_TotalSegmentator_total_6mm_1559subj/nnUNetTrainer_4000epochs_NoMirroring__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth": {
        "sha256": "3489323a4b759506ab46b489eb78b72142f2143aea6e6d828604d754bd7a9270",
        "bytes": 164951587, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset775_head_glands_cavities_492subj/nnUNetTrainer_DASegOrd0_NoMirroring__nnUNetPlans__3d_fullres_high/fold_0/checkpoint_final.pth": {
        "sha256": "8d7a9ef4ff8455b9f0c2926fa11b507c05d83ebd016e64a772fec814271767ab",
        "bytes": 248039021, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset778_headneck_muscles_part1_492subj/nnUNetTrainer_DASegOrd0_NoMirroring__nnUNetPlans__3d_fullres_high/fold_0/checkpoint_final.pth": {
        "sha256": "8649ba0793ad782457de7dbbeb9327a6a244b7bf1dd65d693208d50044894b70",
        "bytes": 247469613, "componente": "TotalSegmentator",
        "opcional": False},
    "ts/Dataset779_headneck_muscles_part2_492subj/nnUNetTrainer_DASegOrd0_NoMirroring__nnUNetPlans__3d_fullres_high/fold_0/checkpoint_final.pth": {
        "sha256": "fde73561a8b046db59315db0326257601eaccef876e8db380dde9d90702f5f11",
        "bytes": 247540205, "componente": "TotalSegmentator",
        "opcional": False},
    "nv_segment_ct/configs/inference.json": {
        "sha256": "b1f7f98012db40a9069f7d79e97ad80320fa7bfd8247b38747836e39baf77e59",
        "bytes": 5914, "componente": "NV-Segment-CT",
        "opcional": True},
    "nv_segment_ct/docs/labels.json": {
        "sha256": "f30fcfb382c3e0e605f2f25d81380f129fdcefc858561877fbe7744d9bf5387b",
        "bytes": 3068, "componente": "NV-Segment-CT",
        "opcional": True},
    "nv_segment_ct/configs/metadata.json": {
        "sha256": "7554d8b015426e7034df9504e8407d413ff469114345999bb9ac58340d814149",
        "bytes": 8083, "componente": "NV-Segment-CT",
        "opcional": True},
    "nv_segment_ct/models/model.pt": {
        "sha256": "c92bab26d00b4a5d89fa8a383900cdeb88302fd318e5e816df0bbec7106d9a1b",
        "bytes": 871970895, "componente": "NV-Segment-CT",
        "opcional": True},
}

PESOS_TS = {
    "Dataset831_TotalSegmentator_part1_organs_1830subj.zip": {"release": "v3.0.0-weights", "bytes": 434915575,
        "sha256": "ed3990bd0b6e39536c55c026207f2625af869981be2aa2e27c13e3f11f89b84a",
        "origem_publica_o_hash": True},
    "Dataset832_TotalSegmentator_part2_vertebrae_1559subj.zip": {"release": "v3.0.0-weights", "bytes": 334822528,
        "sha256": "0bc10da483a1efa621bc322f9f324af467475d068d51a41dff016dadb1528063",
        "origem_publica_o_hash": True},
    "Dataset833_TotalSegmentator_part3_cardiac_1830subj.zip": {"release": "v3.0.0-weights", "bytes": 334155206,
        "sha256": "27721bc6158214f53b81883af05d2018da11d1d0af55d88c57c5ae1e29b0e422",
        "origem_publica_o_hash": True},
    "Dataset834_TotalSegmentator_part4_muscles_1830subj.zip": {"release": "v3.0.0-weights", "bytes": 334231870,
        "sha256": "4d07332e45f04d54efa0c3706aed6a40cd66f25d5a4e3a45bdbcb1532b9c96ed",
        "origem_publica_o_hash": True},
    "Dataset835_TotalSegmentator_part5_ribs_1559subj.zip": {"release": "v3.0.0-weights", "bytes": 334519368,
        "sha256": "ddcdaac399941721d18e37b181c6c5c4569054889b4c3d139290c377b57102ea",
        "origem_publica_o_hash": True},
    "Dataset837_TotalSegmentator_total_6mm_1559subj.zip": {"release": "v3.0.0-weights", "bytes": 132026264,
        "sha256": "45381db2e7686b613d9ade95114f9c0f6e947d6620f6e63a34206fa8426ad01f",
        "origem_publica_o_hash": True},
    "Dataset775_head_glands_cavities_492subj.zip": {"release": "v2.3.0-weights", "bytes": 231091065,
        "sha256": None},
    "Dataset778_headneck_muscles_part1_492subj.zip": {"release": "v2.3.0-weights", "bytes": 230197164,
        "sha256": None},
    "Dataset779_headneck_muscles_part2_492subj.zip": {"release": "v2.3.0-weights", "bytes": 230397368,
        "sha256": None},
    "Dataset776_headneck_bones_vessels_492subj.zip": {"release": "v2.3.0-weights", "bytes": 230805136,
        "sha256": None},
    "Dataset850_TotalSegMRI_part1_organs_1088subj.zip": {"release": "v2.5.0-weights", "bytes": 231681650,
        "sha256": None},
    "Dataset851_TotalSegMRI_part2_muscles_1088subj.zip": {"release": "v2.5.0-weights", "bytes": 232156399,
        "sha256": None},
    "Dataset777_head_muscles_492subj.zip": {"release": "v2.3.0-weights", "bytes": 230370685,
        "sha256": None},
    "Dataset117_lung_airways_arteries_veins_282subj.zip": {"release": "v2.5.0-weights", "bytes": 229853539,
        "sha256": "bdd71e8cf8c38351cf82ead0f854b93b92ea39406633f5a9e85cc72a902fa56e",
        "origem_publica_o_hash": True},
    "Dataset258_lung_vessels_248subj.zip": {"release": "v2.0.0-weights", "bytes": 230593821,
        "sha256": None},
    "Dataset343_mediastinum_1786subj.zip": {"release": "v2.5.0-weights", "bytes": 233215432,
        "sha256": "561c64fc20b5fde4f1776c0a369910156266e7653afc038574dd8ddc4f12fd9a",
        "origem_publica_o_hash": True},
    "Dataset315_thoraxCT.zip": {"release": "v2.0.0-weights", "bytes": 233744954,
        "sha256": None},
    "Dataset260_hip_implant_71subj.zip": {"release": "v2.0.0-weights", "bytes": 232729513,
        "sha256": None},
    "Dataset115_mandible.zip": {"release": "v2.5.0-weights", "bytes": 230321497,
        "sha256": None},
    "Dataset351_oculomotor_muscles_18subj.zip": {"release": "v2.4.0-weights", "bytes": 230606852,
        "sha256": None},
    "Dataset527_breasts_1559subj.zip": {"release": "v2.5.0-weights", "bytes": 233756114,
        "sha256": None},
    "Dataset305_vertebrae_discs_1559subj.zip": {"release": "v2.5.0-weights", "bytes": 233569643,
        "sha256": "b0c936e317a9be1eccaf52bf7043ff28af6c40a3e200cbc6cbc1fbdc0c234920",
        "origem_publica_o_hash": True},
    "Dataset913_lung_nodules.zip": {"release": "v2.5.0-weights", "bytes": 765102050,
        "sha256": None},
    "Dataset952_abdominal_muscles_167subj.zip": {"release": "v2.5.0-weights", "bytes": 124276110,
        "sha256": "7442ec9a0ed29e8263cd6e889eecad8e03680f4d9c3e005aebbfe677dee1faff",
        "origem_publica_o_hash": True},
    "Dataset570_ct_liver_segments.zip": {"release": "v2.5.0-weights", "bytes": 230049561,
        "sha256": None},
    "Dataset756_mri_vertebrae_1076subj.zip": {"release": "v2.5.0-weights", "bytes": 230791939,
        "sha256": None},
    "Dataset576_mri_liver_segments_120subj.zip": {"release": "v2.5.0-weights", "bytes": 229689699,
        "sha256": None},
    "Dataset113_ToothFairy3.zip": {"release": "v2.5.0-weights", "bytes": 232066830,
        "sha256": "cf28693eec49b7a8448e2ebf0a372da41855a099a26d52d1cffe15a3c7e4b740",
        "origem_publica_o_hash": True},
    "Dataset591_ct_liver_lesions_842subj.zip": {"release": "v2.5.0-weights", "bytes": 230940114,
        "sha256": "b3bdd53de65dc64a46264edfdeb491b18e8f95973a691eeccfa530d1da1678a0",
        "origem_publica_o_hash": True},
    "Dataset589_ct_mri_liver_lesions_750subj.zip": {"release": "v2.5.0-weights", "bytes": 231339706,
        "sha256": "67807f2da94acbebf55d714ed84c6d0c7c06d937ead6bcb4d1039e48c1664f66",
        "origem_publica_o_hash": True},
    "Dataset300_body_6mm_1559subj.zip": {"release": "v2.0.0-weights", "bytes": 124286256,
        "sha256": None},
    "Dataset298_TotalSegmentator_total_6mm_1559subj.zip": {"release": "v2.0.0-weights", "bytes": 134827240,
        "sha256": None},
    "Dataset297_TotalSegmentator_total_3mm_1559subj.zip": {"release": "v2.0.0-weights", "bytes": 135386075,
        "sha256": None},
    "Dataset852_TotalSegMRI_total_3mm_1088subj.zip": {"release": "v2.5.0-weights", "bytes": 126399352,
        "sha256": None},
    "Dataset291_TotalSegmentator_part1_organs_1559subj.zip": {"release": "v2.0.0-weights", "bytes": 233742255,
        "sha256": None},
    "Dataset292_TotalSegmentator_part2_vertebrae_1532subj.zip": {"release": "v2.0.0-weights", "bytes": 234050721,
        "sha256": None},
    "Dataset293_TotalSegmentator_part3_cardiac_1559subj.zip": {"release": "v2.0.0-weights", "bytes": 234190318,
        "sha256": None},
    "Dataset294_TotalSegmentator_part4_muscles_1559subj.zip": {"release": "v2.0.0-weights", "bytes": 233625081,
        "sha256": None},
    "Dataset295_TotalSegmentator_part5_ribs_1559subj.zip": {"release": "v2.0.0-weights", "bytes": 234016576,
        "sha256": None},
}


def conferir_peso_ts(caminho, nome, pasta=None, anunciado=None):
    import zipfile
    esperado = PESOS_TS.get(nome) or {}
    if not os.path.isfile(caminho):
        return False, u"nao baixou: %s" % nome, u""
    tam = os.path.getsize(caminho)
    ref = esperado.get("bytes") or anunciado
    if ref and tam != int(ref):
        return False, (u"%s tem %d bytes, esperado %d (%s).\n"
                       u"     Download truncado, pagina de erro com nome de "
                       u"zip, ou o autor republicou o arquivo na origem."
                       % (nome, tam, int(ref),
                          u"tabela do projeto" if esperado.get("bytes")
                          else u"anunciado pelo servidor")), u""
    h = hashlib.sha256()
    try:
        with open(caminho, "rb") as f:
            for b in iter(lambda: f.read(1 << 22), b""):
                h.update(b)
    except OSError as e:
        return False, u"nao consegui ler %s: %s" % (nome, e), u""
    medido = h.hexdigest()
    if esperado.get("sha256") and medido != esperado["sha256"]:
        return False, (u"%s NAO CONFERE com a soma publicada pela origem.\n"
                       u"     esperado %s\n     achado   %s\n"
                       u"     Tamanho certo e conteudo errado: espelho, proxy "
                       u"que reescreve, ou o autor republicou o arquivo."
                       % (nome, esperado["sha256"], medido)), medido
    try:
        with zipfile.ZipFile(caminho) as z:
            ruim = z.testzip()
            nomes = z.namelist()
    except Exception as e:
        return False, (u"%s nao e um zip legivel (%s: %s)"
                       % (nome, type(e).__name__, e)), medido
    if ruim is not None:
        return False, (u"%s: o CRC de %s nao bate -- o arquivo chegou "
                       u"corrompido." % (nome, ruim)), medido
    if not nomes:
        return False, u"%s esta vazio" % nome, medido
    for m in nomes:
        norm = m.replace(u"\\", u"/")
        partes = [p for p in norm.split(u"/") if p]
        if (norm.startswith(u"/") or (len(norm) > 1 and norm[1] == u":")
                or u".." in partes):
            return False, (u"%s tem um caminho que escreveria fora da pasta "
                           u"de pesos: %s" % (nome, m)), medido
        if pasta and partes and partes[0] not in (pasta, u"__MACOSX"):
            return False, (u"%s nao tem a forma que a biblioteca espera: o "
                           u"membro %s nao esta em %s/" % (nome, m, pasta)), medido
    if esperado.get("sha256"):
        veredito = u"tamanho, SHA-256 (publicado pela origem) e CRC conferem"
    elif esperado:
        veredito = (u"tamanho (da origem) e CRC conferem; a origem nao publica "
                    u"SHA-256 deste arquivo")
    elif ref:
        veredito = (u"FORA DA TABELA do projeto: conferido pelo tamanho "
                    u"anunciado e pelo CRC")
    else:
        veredito = (u"FORA DA TABELA do projeto: conferido pelo CRC e pela "
                    u"forma (o tamanho anunciado so e conferido na "
                    u"transferencia, e nao aqui)")
    return True, u"%s: %s" % (nome, veredito), medido


def diverge_da_origem(nome, bytes_achados, medido=u""):
    esperado = PESOS_TS.get(nome) or {}
    try:
        if esperado.get("bytes") and int(bytes_achados) != int(esperado["bytes"]):
            return True
    except (TypeError, ValueError):
        return False
    return bool(esperado.get("sha256") and medido
                and medido != esperado["sha256"])


def por_componente(nome):
    return {k: v for k, v in ARTEFATOS.items() if v["componente"] == nome}


def conferir(caminho, chave):
    esperado = ARTEFATOS.get(chave)
    if esperado is None:
        return False, (u"artefato fora da tabela: %s\n"
                       u"     Some o arquivo e acrescente em "
                       u"build/artefatos.py ANTES de empacotar." % chave)
    if not os.path.isfile(caminho):
        return False, u"nao baixou: %s" % caminho
    tam = os.path.getsize(caminho)
    if tam != esperado["bytes"]:
        return False, (u"%s tem %d bytes, esperado %d.\n"
                       u"     Download truncado, ou o espelho devolveu outra "
                       u"coisa (pagina de erro com nome de arquivo)."
                       % (chave, tam, esperado["bytes"]))
    h = hashlib.sha256()
    try:
        with open(caminho, "rb") as f:
            while True:
                b = f.read(1 << 22)
                if not b:
                    break
                h.update(b)
    except OSError as e:
        return False, u"nao consegui ler %s: %s" % (caminho, e)
    achado = h.hexdigest()
    if achado != esperado["sha256"]:
        return False, (u"%s NAO CONFERE.\n"
                       u"     esperado %s\n"
                       u"     achado   %s\n"
                       u"     Tamanho certo e conteudo errado: espelho trocado "
                       u"ou corrupcao." % (chave, esperado["sha256"], achado))
    return True, u"%s confere" % chave


def linha_manifesto(chave, caminho=None):
    a = ARTEFATOS.get(chave) or {}
    esperado = a.get("sha256") or u""
    soma = u""
    veredito = u""
    if caminho and os.path.isfile(caminho):
        try:
            h = hashlib.sha256()
            with open(caminho, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    h.update(b)
            soma = h.hexdigest()
        except Exception as e:
            soma, veredito = u"", u"NAO FOI POSSIVEL SOMAR (%s)" % str(e)[:60]
        if soma:
            if not esperado:
                veredito = u"SEM SOMA NA TABELA — nao conferido"
            elif soma == esperado:
                veredito = u"confere com a tabela"
            else:
                veredito = u"NAO CONFERE — a tabela esperava %s" % esperado
    if not soma:
        soma = esperado or u"?"
        veredito = veredito or u"valor ESPERADO pela tabela (arquivo nao lido)"
    return (u"  %s@N@"
            u"      componente %-20s bytes %d@N@"
            u"      sha256     %s@N@"
            u"      %s"
            % (chave, a.get("componente", u"?"), a.get("bytes", 0),
               soma, veredito)).replace(u"@N@", u"\n")
