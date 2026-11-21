# Local Suite 8.30

This Windows release adds a research contour for the left anterior descending coronary artery (`DA_ai`). ROCardS runs on the CT inside a box drawn around the finished `Heart_ai` with a 10 mm margin, clipped at the image boundary. The result returns to the CT grid. The DICOM description records how many internal slices were interpolated. Clinical interpretation and independent anatomical validation remain necessary.

In automatic mode the coronary contour follows the inclusion of the heart. In FULL, select the coronary task explicitly or add it to the workstation’s protocol. Turning off the task or excluding its ROI prevents delivery. A compatible cached result can be reused for post-processing. In automatic device mode, TensorFlow uses a compatible GPU when available and otherwise uses CPU. The PyTorch and TensorFlow device selections are independent.

## Installation and terms

The public download is the lightweight SETUP. Extract it and run `START_HERE_TO_INSTALL_LOCAL_SUITE.cmd`. On the connected workstation, the installer presents the applicable terms for each tool and obtains the chosen dependencies and weights from the providers. The local operator can also prepare a private transfer package. An offline installation requires a package from version 8.30 or later and records the receiving operator’s decisions.

The suite asks for a separate teaching and research agreement on first use. Its searchable catalogue lists the tools, authors, conditions for code and weights, and links to the original sources. Updating preserves workstation protocols and custom ROI names.

The task help identifies each distributed illustration by title, author, source and licence. The coronary, rib and lung examples use licensed BodyParts3D atlas plates. The rectal examples use the attributed public TCIA collection. [BodyParts3D coronary plate](https://github.com/Kevin-Mattheus-Moerman/BodyParts3D/blob/2c83c698788cff57f6317bddcf712e7acfbea7d8/assets/BodyParts3D_data/png/FMA3862nsn.png) · [TCIA collection](https://doi.org/10.7937/QSTF-ST65)

ROCardS code and weights are licensed by the authors under CC BY-NC 4.0 for noncommercial research. The local integration changes the cardiac crop, restores the result to the CT grid and exports it as an RTSTRUCT ROI. The JHU pelvic model has an MIT code licence. Its published release does not specify separate terms for the checkpoints. [ROCardS upstream terms](https://github.com/AIM-Harvard/ROCardS#license) · [ROCardS weight licence](https://github.com/AIM-Harvard/ROCardS/blob/40b80a6d6f76b1e72877a139b711bb0a345519d7/ROCardS/data/models/LICENSE_WEIGHTS) · [JHU source and releases](https://github.com/JHU-MICA/TwoStepMalePelvicCTSeg)

## Rebuild the public SETUP

Download the public baseline and run the following command from this directory. This SETUP was compressed with Windows CPython 3.14.6 and `1.3.1.zlib-ng`. Use those versions for byte-for-byte reproduction. [Local Suite 8.28 baseline SETUP](https://github.com/drhenriquebraga/local-suite/releases/download/v8.28/RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.28.zip)

```powershell
python3.14 rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.28.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.zip
```

The manifest records the public baseline hash, the source and hash of each installer member, and the finished ZIP hash. The script verifies all three before writing the result. Identical installer members come from the baseline. Changed and new members are under `members/`. Rebuilding the SETUP requires neither model downloads nor acceptance of installation terms.

## Synthetic checks

Extract the rebuilt installer into a temporary directory and copy `testes/` into it alongside `programa/`. From that directory use the Suite Python to run the synthetic coronary-selection, DICOM round-trip, cache and bundle tests.

```powershell
python -B testes/test_coronaria_study.py
python -B testes/test_cache_modelos_finais.py
python -B testes/test_bundle_830.py
python -B testes/test_aceite_830.py
powershell -NoProfile -File testes/test_termos_instalador.ps1
```

The optional `test_catalogo_licencas.py` comparison takes the actual installed package directories as `--base`, `--runtime` (ROCardS) and `--neuro`.
