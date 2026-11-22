# Local Suite 8.30.2

## Instalação e primeiro uso

Abra o ZIP no Explorer e execute `START_HERE_TO_INSTALL_LOCAL_SUITE.cmd`. Ao escolher instalar ou atualizar, o preparador identifica a instalação existente. Sem internet, informa a condição e abre a seleção de um pacote offline. O progresso permite cancelar pelo canto inferior direito.

Na primeira abertura do aplicativo, o operador revê as condições dos componentes e registra um único aceite. Autorizar os termos das ferramentas opcionais não inicia seu download. A página **Referências e licenças** reúne a bibliografia, a procedência das estruturas, as licenças dos componentes e o aceite gravado nesta estação. Cada modelo inclui as informações publicadas por seus autores.

## Installer and reference library

Start the Windows installer from the SETUP ZIP. Install / Update discovers the workstation installation and opens the offline package picker if the connection is unavailable. In the web app, the first-use agreement presents the optional tool conditions together. The reference library groups publications and structure provenance in one tab and the workstation’s recorded acceptance and source licenses in a second tab. Both former page addresses continue to work. The model list is alphabetical.

## Rebuild the SETUP

Download the versioned 8.30.1 public installer. Using Windows CPython 3.14.6 and `1.3.1.zlib-ng`, run the command below from this directory. The script verifies the baseline, each member and the output ZIP against `manifest.json`. [Versioned Local Suite 8.30.1 installer](https://github.com/drhenriquebraga/local-suite/releases/download/v8.30.1/RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.1.zip)

```powershell
python3.14 rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.1.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.2.zip
```

The two ZIP assets have identical contents. The minimum supported offline bundle remains 8.30. The installer obtains the selected dependencies on the operator’s connection.

## Run the interface checks

Extract the public SETUP. Copy `testes/` alongside `programa/` and run the following commands from the extraction directory. The native checks use Windows PowerShell 5.1. The web checks use Python, FastAPI, Uvicorn, Playwright and an installed Chrome browser. They use temporary workstation storage and local HTTP routes.

```powershell
powershell -NoProfile -STA -File testes/instalador/fluxo_832.ps1
powershell -NoProfile -STA -File testes/instalador/destinos.ps1
python -B testes/instalador/test_native.py
python -B testes/webaceite/test_first_use.py
python -B testes/biblioteca/test_reference_library.py
```
