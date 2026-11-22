"""Gera catálogo offline a partir das distribuições Windows do pacote e das fontes dos modelos."""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
APP = HERE.parent/"app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(HERE))
import artefatos
import configurar_ambiente as config
import radai_models
import radai_tasks

PERFIS = ["full", "lung-rt"]
SEM_PESOS = "Não se aplica. Este componente é software sem pesos de segmentação próprios."
SUITE = "Integração e empacotamento pela Radioterapia.AI Local Suite."
TS = "https://github.com/wasserth/TotalSegmentator"
MOOSE = "https://github.com/ENHANCE-PET/MOOSE"
ROC = "https://github.com/AIM-Harvard/ROCardS"
CADS = "https://github.com/murong-xu/CADS"
NVIDIA = "https://huggingface.co/nvidia/NV-Segment-CT"
JHU = "https://github.com/JHU-MICA/TwoStepMalePelvicCTSeg"
HNLNL = "https://github.com/putzfn/HNLNL_autosegmentation_trained_models"
BUTI = "https://huggingface.co/GregoryButi/CT_Brain_Segmentation_Radiotherapy"
MODEL_CARD = {
    "totalsegmentator": ("TotalSegmentator", "Segmentação anatômica e localização dos recortes em TC e RM.",
        "Jakob Wasserthal e colaboradores, University Hospital Basel", "Apache-2.0", "Ver os termos da tarefa e da revisão correspondente.", TS,
        "", "O autor informa que o software se destina à pesquisa. Os termos das tarefas comerciais do upstream são distintos."),
    "rocards_lad": ("ROCardS · descendente anterior", "Inferência da DA em TC por sete modelos usando o recorte do Heart_ai.",
        "Artificial Intelligence in Medicine, Brigham and Women’s Hospital / Harvard Medical School e colaboradores",
        "CC BY-NC 4.0", "CC BY-NC 4.0", ROC, ROC+"/blob/40b80a6d6f76b1e72877a139b711bb0a345519d7/LICENSE",
        "Pesquisa não comercial. Outras utilizações exigem autorização específica do titular. A margem de 10 mm e a interpolação são da integração local."),
    "jhu_rectum": ("JHU/MICA · reto pélvico", "Localização pélvica e refinamento do reto na TC.",
        "Rahul Pemmaraju e colaboradores, Johns Hopkins University", "MIT", "O release de checkpoints não especifica uma licença própria de pesos.",
        JHU, JHU+"/releases/tag/models", "O repositório publica código MIT. A licença para redistribuição ou uso dos pesos deve ser esclarecida com os autores. O modelo publicado foi desenvolvido para pelve masculina."),
    "cads_open": ("CADS open · Dataset556_GC256", "Comparação das estruturas pélvicas e de radioterapia da tarefa 556.",
        "Murong Xu e colaboradores, projeto CADS", "Apache-2.0", "CC BY-SA 4.0", CADS, CADS+"#model-variants",
        "A variante open é a selecionada. Atribuição e compartilhamento pela mesma licença se aplicam segundo os termos. Os conjuntos de treinamento têm termos independentes."),
    "nv_segment_ct": ("NV-Segment-CT", "Comparador de estruturas de TC com prompts de classe.",
        "NVIDIA e colaboradores do projeto VISTA", "Apache-2.0", "NVIDIA Open Model License Agreement", NVIDIA, NVIDIA+"#model-weights-license",
        "O cartão do modelo especifica finalidade de pesquisa e exclui uso clínico. A licença comercial dos pesos não constitui aprovação clínica."),
    "moose": ("MOOSE · comparadores", "Inferência de modelos opcionais para comparação cardíaca e de composição corpórea.",
        "ENHANCE.PET, Lalith Shiyam Sundar e colaboradores", "Apache-2.0", "CC BY 4.0", MOOSE, MOOSE+"/blob/main/MODEL_LICENSE",
        "Os comparadores são módulos selecionáveis. As tarefas cardíaca, composição corporal e costelas têm entradas próprias."),
    "moose_ribs": ("MOOSE · arcos costais, Dataset444_Ribs", "Complementação posterior das costelas a partir das pontas localizadas na TC.",
        "ENHANCE.PET, Lalith Shiyam Sundar e colaboradores", "Apache-2.0", "CC BY 4.0", MOOSE, MOOSE+"/blob/main/MODEL_LICENSE",
        "O recorte, a junção com as costelas TS, os vetos vertebrais e a escrita do STUDY são implementações da suíte."),
    "hnlnl": ("HNLNL · níveis cervicais", "Inferência dos níveis linfonodais de cabeça e pescoço.",
        "Thomas Weissmann, Florian Putz e colaboradores", "CC0-1.0 para o material do repositório. nnU-Net tem licença própria.",
        "CC0-1.0 no repositório que distribui os modelos treinados.", HNLNL, HNLNL+"/releases", "Task110_HNLNFixed."),
    "cranio_buti": ("CT Brain Segmentation Radiotherapy", "Segmentação de órgãos de risco encefálicos em TC.",
        "Grégory Buti e colaboradores", "nnU-Net sob Apache-2.0. O cartão distribui o modelo.",
        "MIT, conforme o repositório do modelo.", BUTI, BUTI+"/tree/d3f8bc7248ac9138e03be7e6a839d7844599b8a1",
        "A seleção e a composição dos OARs para entrega são da suíte."),
}
PY_OVERRIDES = {
    "jinja2": "BSD-3-Clause", "colorama": "BSD-3-Clause", "vtk": "BSD-3-Clause",
    "pyasn1-modules": "BSD-2-Clause", "trx-python": "BSD-2-Clause",
    "aenum": "BSD-3-Clause", "statsmodels": "BSD-3-Clause e avisos de componentes de terceiros da distribuição.",
    "matplotlib": "Matplotlib License (baseada na licença PSF); terceiros conforme os avisos da distribuição.",
    "python-dateutil": "Apache-2.0 OR BSD-3-Clause",
    "scikit-image": "BSD-3-Clause e licenças específicas dos arquivos discriminadas no LICENSE da distribuição.",
    "kiwisolver": "BSD-3-Clause para Kiwi e Modified BSD para código Cassowary, conforme LICENSE.",
    "dipy": "BSD-3-Clause; componentes e dados de terceiros seguem os respectivos avisos.",
    "torchvision": "BSD-3-Clause; terceiros conforme os avisos do binário.",
    "pyplastimatch": "BSD-3-Clause", "numpy": "BSD-3-Clause; consulte as licenças de terceiros da roda.",
    "scipy": "BSD-3-Clause; consulte as licenças de terceiros da roda.",
}
PY_PURPOSE = {
    "torch":"Executa as redes de segmentação em CPU ou GPU.", "torchvision":"Operadores de visão e transformação de tensores.",
    "totalsegmentator":"Ferramentas Python do TotalSegmentator para leitura e execução das tarefas.",
    "nnunetv2":"Inferência, reamostragem e pós-processamento dos modelos nnU-Net.",
    "monai":"Transformações de imagens e inferência dos modelos médicos em PyTorch.",
    "pydicom":"Lê e grava datasets DICOM e seus atributos.", "simpleitk":"Lê séries e mantém a geometria física das imagens.",
    "rt-utils":"Manipula máscaras e ROIs de RTSTRUCT.", "nibabel":"Leitura, orientação e gravação de volumes NIfTI.",
    "numpy":"Arrays de voxels e operações numéricas.", "scipy":"Filtros, componentes conexos e interpolação de volumes.",
    "keras":"Reconstrói e executa as redes Keras do ROCardS.", "tensorflow":"Executa a cascata ROCardS a partir de SavedModels.",
    "pylibjpeg-openjpeg":"Decodifica JPEG 2000/HTJ2K em DICOM.", "pylibjpeg":"Integra decodificadores de pixels ao leitor DICOM.",
    "fastapi":"Serve os endpoints locais da interface e da fila.", "uvicorn":"Executa o servidor ASGI da suíte.",
    "xgboost":"Executa classificadores auxiliares de modalidade e fase da TC.", "pip":"Instala as distribuições Python do ambiente.",
    "opencv-python":"Extrai e rasteriza contornos em cortes bidimensionais.", "vtk":"Processamento e visualização de superfícies 3D.",
    "tensorflow-estimator":"Interfaces de estimadores compatíveis com TensorFlow 2.10.",
}
def normal(text):
    return re.sub(r"[-_.]+", "-", text).lower()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def item_hash(row):
    return digest(json.dumps({k:v for k,v in row.items() if k!="sha256"}, ensure_ascii=False,
                             sort_keys=True, separators=(",",":")).encode("utf-8"))


def urls(pairs):
    seen = set()
    valid = []
    for label, value in pairs:
        if not isinstance(value, str):
            continue
        value = value.strip()
        if value.startswith("http://"):
            value = "https://"+value[7:]
        u = urlsplit(value)
        if u.scheme != "https" or not u.hostname or u.username or u.password or value in seen or any(ch.isspace() for ch in value):
            continue
        seen.add(value)
        valid.append({"rotulo":label, "url":value})
    return valid


def item(id_, name, goal, authors, code, weights, links, env, versions, profiles, tool, note="", source="Software de terceiros"):
    return dict(id=id_, titulo=name, finalidade=goal, autoria=authors, licenca_codigo=code,
                licenca_pesos=weights, fontes=urls(links), integracao=SUITE, origem=source,
                ambientes=env, versoes=versions, perfis=profiles, ferramenta=tool, observacoes=note)


def modelos():
    rows = []
    all_tasks = {p:set(config.tasks_do_perfil({"profile":p})) for p in PERFIS}
    all_models = {p:set(config.modelos_do_perfil({"profile":p})) for p in PERFIS}
    for key, (name,goal,authors,code,weights,url,terms,note) in MODEL_CARD.items():
        opt = key in ("cads_open", "nv_segment_ct", "moose", "rocards_lad")
        profiles = [p for p in PERFIS if key in ("totalsegmentator", "rocards_lad") or key in all_models[p] or (opt and p == "full")]
        meta = radai_models.MODELOS[key]
        version = meta.get("revisao") or {"totalsegmentator":artefatos.VERSOES["totalsegmentator"],
                    "cads_open":"cads-model-open_v1.0.0", "moose":"moosez-v.3.1.3", "moose_ribs":"moosez-v.3.1.3",
                    "jhu_rectum":"release models", "hnlnl":"nnUnet_model_export"}.get(key)
        links = [("Projeto dos autores",url)]
        if terms:
            links.append(("Termos ou distribuição dos pesos",terms))
        if key == "rocards_lad":
            links.append(("Licença dos pesos distribuídos",ROC+"/blob/"+meta["revisao"]+"/ROCardS/data/models/LICENSE_WEIGHTS"))
            links.append(("Validação pelos autores",'https://arxiv.org/abs/2511.14971'))
        if key == 'nv_segment_ct':
            links.append(('Configuração de inferência MONAI','https://huggingface.co/MONAI/vista3d'))
            version = 'vista3d_pretrained_model · SHA-256 '+meta['sha256']['models/model.pt']
        if key == 'totalsegmentator':
            links.extend([('Dados de TC publicados pelos autores','https://doi.org/10.5281/zenodo.6802613'),
                          ('Dados de RM publicados pelos autores','https://doi.org/10.5281/zenodo.11367004')])
        row = item(key,name,goal,authors,code,weights,links,["Modelos da suíte"],[version] if version else [],profiles,key,note)
        row['evidencia_versao'] = 'Revisão, release ou digest fixado no registro de downloads da suíte.'
        row['dados_treinamento'] = 'O pacote distribui modelos. Acesso e uso das imagens originais dependem do titular do conjunto de dados.'
        if key == 'rocards_lad':
            row['dados_treinamento'] = 'Treino descrito em 560 TCs de planejamento do Brigham/Dana-Farber. Os direitos das imagens clínicas são independentes da licença dos pesos.'
        if key == "rocards_lad":
            row["perfis"] = ["plugin-coronarias"]
        row["opcional"] = opt
        rows.append(row)
    for name, group, desc in (("moose-cardiac","Dataset888_Cardiac","Comparação das estruturas cardíacas na TC."),
                              ("moose-body-composition","Dataset778_Body_composition","Comparação da composição corporal na TC.")):
        row = item(name,"MOOSE · "+group,desc,MODEL_CARD["moose"][2],"Apache-2.0","CC BY 4.0",
                   [("Termos dos modelos",MOOSE+"/blob/main/MODEL_LICENSE"),("Release",MOOSE+"/releases/tag/moosez-v.3.1.3")],
                   ["Comparador opcional"],["moosez-v.3.1.3"],["full"],"moose")
        row["opcional"] = True
        rows.append(row)
    for task in radai_tasks.CATALOGO:
        key = task["task"]
        ds = list(radai_tasks.datasets_necessarios(key))
        row = item("ts-"+normal(key),"TotalSegmentator · "+key,task["rotulo"],MODEL_CARD["totalsegmentator"][2],
                   "Apache-2.0", "Apache-2.0 para a tarefa aberta indicada pelos autores.",
                   [("Tarefas e condições publicadas",TS+"#subtasks"),("Distribuição dos pesos",TS+"/releases")],
                   ["TotalSegmentator"],[artefatos.VERSOES["totalsegmentator"]],[p for p in PERFIS if key in all_tasks[p]],"totalsegmentator",
                   "Modalidade "+task["modalidade"]+". IDs dos checkpoints incluem localizadores compartilhados quando usados.")
        row["datasets"] = ds
        releases = sorted({meta['release'] for filename, meta in artefatos.PESOS_TS.items()
                           if int(re.match(r'Dataset(\d+)', filename).group(1)) in ds})
        row['fontes'] += [{'rotulo':'Release oficial dos pesos '+v, 'url':TS+'/releases/tag/'+v} for v in releases]
        row['evidencia_versao'] = 'Versão do software exigida pelo instalador. As fontes identificam os releases de pesos no manifesto.'
        row["task"] = key
        if key == "lung_nodules":
            row["autoria"] += "; modelo de nódulos fornecido por BLUEMIND AI."
        rows.append(row)
    return rows


def ler_lock(path):
    return {normal(a):b for a,b in re.findall(r"^([\w.-]+)==([^\s#]+)", path.read_text(encoding="utf-8"), re.M)}


def arquivos_da_roda(dist):
    notices, binaries = [], []
    for relative in sorted({str(f).replace('\\', '/') for f in dist.files or []}):
        path = PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts or ':' in relative:
            continue
        if path.suffix.lower() in ('.dll', '.exe'):
            binaries.append(relative)
        is_notice = re.match(r'^(copying|licen[cs]e|copyright|notice|third.party)(?:$|[-_. ])', path.name, re.I)
        in_licenses = 'licenses' in (p.lower() for p in path.parts[:-1])
        if (is_notice or in_licenses) and path.suffix.lower() not in ('.py','.pyc','.pyd','.dll','.so','.exe'):
            source = Path(dist.locate_file(relative))
            if source.is_file():
                notices.append(dict(arquivo=relative, sha256=digest(source.read_bytes())))
    return notices, binaries


def licenca(dist, key):
    m = dist.metadata
    if m.get("License-Expression"):
        return m["License-Expression"]
    if key in PY_OVERRIDES:
        return PY_OVERRIDES[key]
    raw = (m.get("License") or "").strip()
    classifiers = [v.split("::")[-1].strip() for v in m.get_all("Classifier",[]) if v.startswith("License ::")]
    terms = " ".join((raw[:250], *classifiers)).lower()
    if " and " in raw.lower() or " or " in raw.lower():
        if len(raw) < 110:
            return raw
    if "isc" in raw.lower() and len(raw)<20:
        return "ISC"
    for kind, pat in (("Apache-2.0",r"apache"),("MIT",r"\bmit\b"),("BSD-3-Clause",r"bsd[- ]3|3.clause.bsd"),
                      ("BSD-2-Clause",r"bsd[- ]2|2.clause.bsd"),("MPL-2.0",r"mpl.2|mozilla public license 2"),
                      ("PSF-2.0",r"python software foundation|psf-2"),("LGPL-3.0-or-later",r"lgpl-3.0-or-later")):
        if re.search(pat, terms):
            return kind
    license_files = [p for p in Path(dist._path).glob("*") if p.is_file() and p.name.upper().startswith(("LICENSE","COPYING"))]
    if license_files:
        doc = license_files[0].read_text(errors="replace",encoding="utf8").lower()
        if "redistribution and use" in doc and "neither the name" in doc:
            return "BSD-3-Clause"
        if "redistribution and use" in doc and "this list of conditions" in doc and "neither the name" not in doc:
            return "BSD (texto na distribuição)"
    if len(raw) < 120 and raw and raw.lower() not in ("unknown","none"):
        return raw
    return ", ".join(classifiers) or "Consultar os avisos da distribuição. Identificador não declarado pelo mantenedor."


def metadados_python(base, runtime, neuro):
    locks = {k:ler_lock(HERE/f) for k,f in [("Python base","requirements-demo.txt"),("ROCardS / TensorFlow","requirements-rocards.txt")]}
    all_rows = {}
    locks["Plugin NEURO RT"] = {}
    for env, folder in (("Python base",base),("ROCardS / TensorFlow",runtime),("Plugin NEURO RT",neuro)):
        if not folder.is_dir():
            raise ValueError("Ambiente Python ausente: "+str(folder))
        seen = {}
        for d in sorted(metadata.distributions(path=[str(folder)]),key=lambda d:normal(d.metadata["Name"])):
            m = d.metadata
            key = normal(m["Name"])
            if env.startswith("ROCardS") and key not in locks[env]:
                continue
            if key in seen:
                raise ValueError("Distribuição duplicada: "+key)
            seen[key] = d.version
            author = (m.get("Author") or m.get("Maintainer") or "").strip()
            if not author or author.lower()=="unknown":
                from email.utils import getaddresses
                names = [n for n,addr in getaddresses([m.get("Author-email","")]) if n]
                author = ", ".join(names) or "Mantenedores de "+m["Name"]+" identificados na distribuição."
            links = [("Página oficial da distribuição",m.get("Home-page"))]
            for rec in m.get_all("Project-URL",[]):
                title, sep, url = rec.partition(",")
                if sep and title.lower() in ("source","source code","homepage","home","repository","code","license","documentation"):
                    links.append((title.strip(),url.strip()))
            if key in ("torch","torchvision") and "+" in d.version:
                links.append(("Índice oficial de binários CUDA", "https://download.pytorch.org/whl/cu121/"+key+"/"))
            links.append(("Metadados publicados no PyPI","https://pypi.org/project/"+key+"/"+d.version.split("+")[0]+"/"))
            lic = licenca(d,key)
            record = ('neuro-python-' if env == 'Plugin NEURO RT' else 'python-') + key
            row = all_rows.get(record)
            if row is None:
                row = item(record,m["Name"],PY_PURPOSE.get(key) or (m.get("Summary") or "Dependência de execução do ambiente Python.").strip(),
                           author,lic,SEM_PESOS,links,[],[],[], "infra-python", source="Distribuição Python")
                row['distribuicao_python'] = key
                row["instalacoes"] = []
                all_rows[record] = row
            row["ambientes"].append(env)
            if d.version not in row["versoes"]:
                row["versoes"].append(d.version)
            profiles = ['plugin-neuro'] if env == 'Plugin NEURO RT' else PERFIS
            row['perfis'] = sorted(set(row['perfis']) | set(profiles))
            notices, binaries = arquivos_da_roda(d)
            row["instalacoes"].append(dict(ambiente=env, versao=d.version, licenca=lic,
                requisito_fixo=key in locks[env], avisos=notices, binarios_nativos=binaries))
            row["fontes"] = urls([(s["rotulo"],s["url"]) for s in row["fontes"]] + links)
            licenses = sorted({x["licenca"] for x in row["instalacoes"]})
            row["licenca_codigo"] = " / ".join(licenses)
        for k,v in locks[env].items():
            if seen.get(k)!=v:
                raise ValueError(env+": requisito não materializado "+k+"=="+v)
    direct = set(locks['Python base']) | {'torchvision','tensorflow','keras','vtk','opencv-python','onnxruntime','antspyx','raidionicsseg'}
    for row in all_rows.values():
        key = row['distribuicao_python']
        if row['ambientes'] == ['Plugin NEURO RT']:
            row['ferramenta'] = 'neuro-rt'
            row['opcional'] = True
            row['selecao_plugin'] = 'recursos-modelos'
        elif row['ambientes'] == ['ROCardS / TensorFlow']:
            row['perfis'] = ['plugin-coronarias']
            row['ferramenta'] = 'rocards_lad'
            row['opcional'] = True
        elif key in direct:
            row['ferramenta'] = 'totalsegmentator' if key == 'totalsegmentator' else 'python-' + key
        row['evidencia_versao'] = 'Metadados das distribuições presentes nos ambientes de referência discriminados em instalacoes.'
    return list(all_rows.values())


def extras(checkouts):
    rows = []
    def tool(key,name,goal,author,license_,url,version,profiles=PERFIS,group=None):
        rows.append(item(key,name,goal,author,license_,SEM_PESOS,[("Projeto ou termos oficiais",url)],
                         ["Infraestrutura"],[version] if version else [],profiles,group or key))
    tool("cpython","CPython embeddable","Interpretador Windows de execução da suíte.","Python Software Foundation",
         "PSF-2.0 e licenças de componentes da distribuição.", "https://docs.python.org/3.10/license.html",artefatos.VERSOES["python"])
    tool("nvidia-cuda","CUDA Runtime 12.1","Aceleração por GPU das operações do PyTorch.","NVIDIA Corporation",
         "NVIDIA CUDA Toolkit EULA, inclusive as condições de redistribuição.", "https://docs.nvidia.com/cuda/archive/12.1.1/eula/index.html","12.1")
    tool("nvidia-cudnn","cuDNN","Primitivas de convolução utilizadas pelos modelos em GPU.","NVIDIA Corporation",
         "NVIDIA Software License Agreement e condições aplicáveis ao componente cuDNN.", "https://developer.nvidia.com/cudnn","9 (DLL no wheel do PyTorch)")
    native = [
        ('openssl','OpenSSL','TLS e criptografia no interpretador.','OpenSSL Project, Eric Young e colaboradores','OpenSSL License e Original SSLeay License (ramo 1.1.1).','https://openssl-library.org/source/license/index.html','1.1.1t','cpython'),
        ('sqlite','SQLite','Banco embarcado da biblioteca padrão.','D. Richard Hipp e colaboradores SQLite','Domínio público, conforme a declaração dos autores.','https://www.sqlite.org/copyright.html','3.40.1','cpython'),
        ('zlib','zlib','Compressão e descompressão de fluxos.','Jean-loup Gailly e Mark Adler','Zlib','https://zlib.net/zlib_license.html','1.2.13 (CPython)','cpython'),
        ('libffi','libffi','Interoperabilidade de ctypes com bibliotecas nativas.','Anthony Green e colaboradores','MIT','https://github.com/libffi/libffi','ABI 7','cpython'),
        ('msvc-runtime','Microsoft Visual C++ Runtime','Executa componentes compilados para Windows.','Microsoft Corporation','Microsoft Visual C++ Runtime 2015–2022 License Terms.','https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/','ABI v140','cpython'),
        ('openblas','OpenBLAS','Álgebra linear nos wheels NumPy e SciPy.','OpenBLAS e colaboradores','BSD-3-Clause; ver demais créditos no wheel.','https://github.com/OpenMathLib/OpenBLAS','','python-numpy'),
        ('ffmpeg','FFmpeg do OpenCV','Leitura e escrita de vídeo por meio do wheel OpenCV.','FFmpeg developers','LGPL-2.1-or-later conforme o wheel opencv-python.','https://github.com/opencv/opencv-python#licensing','','python-opencv-python'),
        ('openjpeg','OpenJPEG','Codificação e decodificação JPEG 2000 em imagens médicas.','UCLouvain, Université de Bretagne Sud e colaboradores','BSD-2-Clause','https://github.com/uclouvain/openjpeg','','python-pylibjpeg-openjpeg'),
        ('gdcm','GDCM','Leitura de imagens médicas pelo ImageIO do SimpleITK.','Mantenedores do projeto Grassroots DICOM','BSD-3-Clause e avisos dos arquivos de terceiros.','https://sourceforge.net/projects/gdcm/','','python-simpleitk'),
    ]
    for key,name,goal,author,terms,url,version,group in native:
        tool(key,name,goal,author,terms,url,version,group=group)
    for label, key in [("Motion","motion"),("Framer Motion","framer-motion"),("Motion DOM","motion-dom"),("Motion Utils","motion-utils")]:
        tool("web-"+key,label,"Animação da interface da porta da suíte.","Motion B.V. e colaboradores","MIT","https://github.com/motiondivision/motion","14.1.0")
    tool("web-tslib","tslib","Auxiliares de execução do código TypeScript compilado.","Microsoft Corporation","0BSD","https://github.com/microsoft/tslib","2.8.1")
    tool("web-anton","Anton","Tipografia do título da porta da suíte.","The Anton Project Authors","OFL-1.1","https://github.com/googlefonts/AntonFont","")
    tool("build-esbuild","esbuild","Preparação do JavaScript da interface no desenvolvimento.","Evan Wallace","MIT","https://github.com/evanw/esbuild","0.28.2",[])
    comps = json.loads((HERE/"componentes.lock.json").read_text(encoding="utf-8"))["componentes"]
    goals = dict(CONTOURLAB="Orquestração de segmentação, acabamento e geração de RTSTRUCT.",
                 DICOM_BRIDGE="Entrada e trânsito de séries DICOM.", RECON_3D="Reconstrução e visualização tridimensional.",
                 ELASTIC_RT="Registro e alinhamento de imagens usando SimpleITK e SciPy do ambiente base.", **{"3D_PRINTED_BOLUS":"Construção e exportação de bolus para impressão 3D."})
    for comp in comps:
        key = comp["nome"]
        source = "https://github.com/"+comp["repositorio"]
        # Catalog each component against its own repository, whose license may
        # differ from the aggregate suite. Read only explicit local checkouts.
        component_path = checkouts/key/"LICENSE"
        if component_path.is_file():
            body = component_path.read_text(encoding="utf8",errors="replace").lower()
        else:
            body = ""
        label = ("Apache-2.0" if "apache license" in body else "MIT" if "mit license" in body
                 else "Consultar a licença no repositório do componente.")
        row = item("suite-"+normal(key),key,goals[key],"Henrique Braga e colaboradores",label,SEM_PESOS,
                   [("Repositório do componente",source)],["Aplicativo"],[comp["tag"]],["full"],key,source="Componente da Local Suite")
        row["integracao"] = "Módulo integrado pela equipe Radioterapia.AI."
        row['evidencia_versao'] = 'Tag do repositório fonte fixada em componentes.lock.json.'
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base","runtime","neuro","checkouts"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--plugins",type=Path,default=HERE/'licencas_plugins.json')
    parser.add_argument("--saida",type=Path,default=APP/"data/licencas_suite.json")
    args = parser.parse_args()
    rows = modelos()+extras(args.checkouts)+metadados_python(args.base,args.runtime,args.neuro)
    external = json.loads(args.plugins.read_text(encoding="utf-8-sig"))
    rows.extend(external if isinstance(external,list) else external["itens"])
    for x in rows:
        x.setdefault("opcional",False)
        x.setdefault("perfis",[])
        x.setdefault("ferramenta",x["id"])
        x.setdefault('evidencia_versao','Versão da distribuição de referência ou da receita de instalação. A instalação da estação é verificada separadamente.')
        if not x["fontes"] or any(not x.get(k) for k in ("id","licenca_codigo","licenca_pesos","finalidade")):
            raise ValueError("Entrada incompleta: "+x["id"])
        x["sha256"] = item_hash(x)
    rows.sort(key=lambda x:x["id"])
    if len(set(x["id"] for x in rows)) != len(rows):
        raise ValueError("Identificador duplicado")
    args.saida.write_bytes((json.dumps({"schema":"local-suite/termos/1","itens":rows},ensure_ascii=False,indent=2)+"\n").encode("utf-8"))
    print("Itens:",len(rows),"SHA-256:",digest(args.saida.read_bytes()))


if __name__ == "__main__":
    main()

