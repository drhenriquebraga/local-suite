# Local Suite 8.30.4

## Mudanças para o operador

O RTSTRUCT usa o espaçamento de coluna para deslocamentos horizontais na imagem e o espaçamento de linha para deslocamentos verticais. A correção afeta séries em que os pixels têm larguras e alturas diferentes.

No AUTO em TC, `Bag_Bowel` e `Bag_Bowel_OAR` recebem acabamento FAST. As demais estruturas recebem o acabamento PADRÃO. No PERSONALIZADO, a suíte respeita a escolha de acabamento feita pelo operador.

O plugin de coronárias ROCardS vem desativado. O operador pode ativá-lo nas Configurações da estação com o aceite de uso em pesquisa e obtenção dos arquivos do modelo, ou importar um pacote preparado para uso offline. O instalador permite selecionar os componentes ao montar o pacote portátil.

## Rebuild the Windows installer

Download the 8.30.3 SETUP and run the following command in this directory with the Python and zlib versions recorded in `manifest.json`. The rebuild verifies the baseline, individual members and final SHA-256. The versioned ZIP and the LATEST ZIP contain identical bytes. [Local Suite 8.30.3 installer](https://github.com/drhenriquebraga/local-suite/releases/download/v8.30.3/RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.3.zip)

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.3.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.4.zip
```

## Test the packaged sources

No fantoma de 48 cortes, o FAST reduziu os vértices da bolsa de 7.973 para 5.806. O STUDY ocupou 239.860 bytes, ante 294.560 bytes no PADRÃO. As duas máscaras 3D e os contornos das demais estruturas coincidiram. As medições desta estação não demonstraram redução do tempo total.

A bateria de RTSTRUCT passou nas 303 verificações. No controle de nove cortes com pixels de 0,96 × 0,68 mm, o arquivo relido recuperou os 1.956 vértices de referência e o preenchimento esperado nos dois leitores. A bateria histórica `test_motor2.py` ainda acusa 21 verificações também reprovadas na candidata anterior (27 naquela árvore), entre elas contratos antigos do FULL simultâneo ao AUTO, do modo FAST retirado e do recorte do reto. As verificações de entrega das bolsas usam o fluxo atual.

Extract the rebuilt installer and copy the `testes` directory alongside its `programa` directory. Run the suites below with the application dependencies installed. The settings test also uses Playwright and Chrome on Windows. The tests use synthetic data.

```powershell
python -B programa/tools/test_geom.py
python -B programa/tools/test_bolsas_fast.py
python -B programa/tools/test_motor2.py
python -B programa/tools/test_rtstruct_pixel_spacing.py
python -B programa/tools/test_rt.py
python -B testes/test_coronaria_study.py
python -B testes/test_coronarias_offline.py
python -B testes/test_coronarias_settings.py
python -B testes/test_plugin_coronarias_instalacao.py
```
