# Local Suite 8.30.1

This release repairs the Windows installer for new stations and for upgrades from older versions, including the failure to import `radai_rocards_worker` during validation. The minimum supported offline bundle is 8.30.

## Install or update

Open the SETUP ZIP in Windows Explorer and run `START_HERE_TO_INSTALL_LOCAL_SUITE.cmd`. The language selector opens in English. Select your preferred language, then choose **Install / Update**. A connected workstation with an older dependency bundle downloads the components it needs and resumes in the existing installation folder.

The installer presents applicable third-party conditions in a scrollable panel with source links. One acceptance covers the components shown. On the same Windows account and workstation, compatible receipts carry forward, including documented optional exclusions. New or revised conditions trigger review. Third-party attribution remains available in the suite's catalogue.

The revised validator checks the new ROCardS worker before completing the upgrade. Previously saved protocols and custom structure names stay in the workstation's configuration. The original studies and model weights are external to the public SETUP. For an offline station, prepare a transfer package on a connected workstation.

## Rebuild the public download

Use Windows CPython 3.14.6 with `1.3.1.zlib-ng` to reproduce the release bytes. Download the 8.30 baseline and run this command from this directory. [Versioned 8.30 SETUP](https://github.com/drhenriquebraga/local-suite/releases/download/v8.30/RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.zip)

```powershell
python3.14 rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.1.zip
```

The manifest records the digest of the public baseline, the source and SHA-256 of each member, and the final ZIP SHA-256. The 402 members produce a 13,114,128-byte SETUP with SHA-256 `2174fa358af3a8aadd4b9ab30a5b4832948b21af5787d4ed528a9bcccfa8f2a0`. The published versioned and LATEST assets are identical. Rebuilding requires only the baseline and this directory.

## Verify the installer workflow

On Windows, extract the rebuilt SETUP and copy the `testes` directory alongside `programa`. With Python on PATH, run these checks from the extraction directory.

```powershell
powershell -NoProfile -STA -File testes/fluxo-instalador.ps1
powershell -NoProfile -STA -File testes/test_termos_831.ps1
```

The routing checks simulate the presence of a network connection, compatible and outdated bundles, failures, and retries. The terms check opens a native panel and tests receipt migration with a synthetic identity and disposable files.

To repeat the upgrade test, provide a previous public SETUP without the ROCardS worker and a compatible offline test assembly containing `python`, `ts_weights`, and `modelos`. The test copies the older app into a temporary directory and reuses the runtime and weights from that assembly.

```powershell
python -B testes/test_runtime_831.py --previous-zip C:/fixtures/previous-setup.zip --runtime-root C:/fixtures/offline-runtime
```

The suite is distributed for teaching and research. See the model sources and terms in the installed catalogue. [Segmentation changes introduced in 8.30](../v8_30/README.md)
