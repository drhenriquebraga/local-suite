@echo off
setlocal
set "R=%~dp0"
cd /d "%R%"
set "LOG=%R%verify_log.txt"

echo ============================================================
echo   Radioterapia.AI Local Suite - verificacao
echo ============================================================
echo.

set "PY="
if exist "%R%_python.txt" set /p PY=<"%R%_python.txt"
if defined PY if not exist "%PY%" set "PY="
if not defined PY if exist "%R%.venv\Scripts\python.exe" set "PY=%R%.venv\Scripts\python.exe"
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo ERRO: nao achei nenhum Python.
  echo Procurei em: _python.txt, .venv\Scripts e no PATH.
  echo ERRO: python ausente> "%LOG%"
  echo.
  pause
  exit /b 1
)
echo Python: %PY%
echo.
echo Rodando as baterias... ^(a saida completa vai para o log^)
echo.

echo Radioterapia.AI - verificacao - %DATE% %TIME%> "%LOG%"
echo python: %PY%>> "%LOG%"
for /f "usebackq delims=" %%P in (`""%PY%" "%R%tools\_componentes.py" --pythonpath"`) do set "PYTHONPATH=%%P"
echo pythonpath: %PYTHONPATH%>> "%LOG%"
echo.>> "%LOG%"

echo.>> "%LOG%"
"%PY%" "%R%tools\check_project.py" >> "%LOG%" 2>&1
set "RC1=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_cleanup.py" >> "%LOG%" 2>&1
set "RC2=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_geom.py" >> "%LOG%" 2>&1
set "RC3=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_tasks.py >> "%LOG%" 2>&1
set "RC4=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_menu.py" >> "%LOG%" 2>&1
set "RC5=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_todo.py" >> "%LOG%" 2>&1
set "RC6=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_engine.py >> "%LOG%" 2>&1
set "RC7=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_ts_runner.py >> "%LOG%" 2>&1
set "RC8=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_names.py >> "%LOG%" 2>&1
set "RC9=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_full_oar.py >> "%LOG%" 2>&1
set "RC10=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_rotulos.py >> "%LOG%" 2>&1
set "RC11=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_fichas.py" >> "%LOG%" 2>&1
set "RC12=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_rodar.py >> "%LOG%" 2>&1
set "RC13=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_verseg.py >> "%LOG%" 2>&1
set "RC14=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_velocidade.py >> "%LOG%" 2>&1
set "RC15=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_neb_telas.py" >> "%LOG%" 2>&1
set "RC16=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_lacunas.py" >> "%LOG%" 2>&1
set "RC17=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_campo.py >> "%LOG%" 2>&1
set "RC18=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_motor2.py >> "%LOG%" 2>&1
set "RC19=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_devices.py >> "%LOG%" 2>&1
set "RC20=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_arranque_devices.py >> "%LOG%" 2>&1
set "RC21=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_watcher.py >> "%LOG%" 2>&1
set "RC22=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_panel.py" >> "%LOG%" 2>&1
set "RC23=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_estacao.py" >> "%LOG%" 2>&1
set "RC24=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_retorno_v88.py" >> "%LOG%" 2>&1
set "RC25=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_rt.py >> "%LOG%" 2>&1
set "RC26=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_caminho_dos_dados.py >> "%LOG%" 2>&1
set "RC27=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_credits.py" >> "%LOG%" 2>&1
set "RC28=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_cover.py" >> "%LOG%" 2>&1
set "RC29=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_packager.py" >> "%LOG%" 2>&1
set "RC30=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_delivery.py" >> "%LOG%" 2>&1
set "RC31=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_consent.py" >> "%LOG%" 2>&1
set "RC32=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_languages.py" >> "%LOG%" 2>&1
set "RC33=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_languages_installer.py" >> "%LOG%" 2>&1
set "RC34=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_shutdown.py" >> "%LOG%" 2>&1
set "RC35=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_ui.py" >> "%LOG%" 2>&1
set "RC36=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_design.py" >> "%LOG%" 2>&1
set "RC37=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_varrer.py" >> "%LOG%" 2>&1
set "RC38=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_porta.py" >> "%LOG%" 2>&1
set "RC39=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_inicio.py" >> "%LOG%" 2>&1
set "RC40=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_provenance.py >> "%LOG%" 2>&1
set "RC41=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_moose.py >> "%LOG%" 2>&1
set "RC42=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_modelos_v84.py >> "%LOG%" 2>&1
set "RC43=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_queue.py" >> "%LOG%" 2>&1
set "RC44=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_ui_interacao.py" >> "%LOG%" 2>&1
set "RC45=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_nv_segment.py >> "%LOG%" 2>&1
set "RC46=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_skin.py >> "%LOG%" 2>&1
set "RC47=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_constructs.py >> "%LOG%" 2>&1
set "RC48=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_hnlnl.py >> "%LOG%" 2>&1
set "RC49=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_zip_split.py >> "%LOG%" 2>&1
set "RC50=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_thumbnail.py" >> "%LOG%" 2>&1
set "RC51=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_recon3d.py >> "%LOG%" 2>&1
set "RC52=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_recon3d_v84.py >> "%LOG%" 2>&1
set "RC53=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_bolus.py >> "%LOG%" 2>&1
set "RC54=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_dicom.py" >> "%LOG%" 2>&1
set "RC55=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_bridge.py >> "%LOG%" 2>&1
set "RC56=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_bridge_motor.py >> "%LOG%" 2>&1
set "RC57=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_bridge_tela.py >> "%LOG%" 2>&1
set "RC58=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_nidus.py >> "%LOG%" 2>&1
set "RC59=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_elastic.py >> "%LOG%" 2>&1
set "RC60=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_lifecycle.py" >> "%LOG%" 2>&1
set "RC61=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_interactions.py >> "%LOG%" 2>&1
set "RC62=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_conversion.py" >> "%LOG%" 2>&1
set "RC63=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_dryrun.py >> "%LOG%" 2>&1
set "RC64=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_installer_light.py" >> "%LOG%" 2>&1
set "RC65=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_weights.py >> "%LOG%" 2>&1
set "RC66=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_loop.py" >> "%LOG%" 2>&1
set "RC67=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_cleaner.py" >> "%LOG%" 2>&1
set "RC68=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_batch.py >> "%LOG%" 2>&1
set "RC69=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_plausibility.py >> "%LOG%" 2>&1
set "RC70=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_overnight.py >> "%LOG%" 2>&1
set "RC71=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_levels.py >> "%LOG%" 2>&1
set "RC72=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_suite.py" >> "%LOG%" 2>&1
set "RC73=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_image.py >> "%LOG%" 2>&1
set "RC74=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_records.py >> "%LOG%" 2>&1
set "RC75=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_version.py" >> "%LOG%" 2>&1
set "RC76=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_validation.py" >> "%LOG%" 2>&1
set "RC77=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_fila_simulacao.py" >> "%LOG%" 2>&1
set "RC78=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_nomes_no_tps.py >> "%LOG%" 2>&1
set "RC79=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_nomes_proprios.py >> "%LOG%" 2>&1
set "RC80=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\_componentes.py" --rodar test_bolus_aplicador.py >> "%LOG%" 2>&1
set "RC81=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_componentes.py" >> "%LOG%" 2>&1
set "RC82=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_entrada.py" >> "%LOG%" 2>&1
set "RC83=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_installer.py" >> "%LOG%" 2>&1
set "RC84=%ERRORLEVEL%"
echo.>> "%LOG%"
"%PY%" "%R%tools\test_instalar_direto.py" >> "%LOG%" 2>&1
set "RC85=%ERRORLEVEL%"

type "%LOG%"

echo.
echo ============================================================
if not "%RC1%"=="0" goto :falhou
if not "%RC2%"=="0" goto :falhou
if not "%RC3%"=="0" goto :falhou
if not "%RC4%"=="0" goto :falhou
if not "%RC5%"=="0" goto :falhou
if not "%RC6%"=="0" goto :falhou
if not "%RC7%"=="0" goto :falhou
if not "%RC8%"=="0" goto :falhou
if not "%RC9%"=="0" goto :falhou
if not "%RC10%"=="0" goto :falhou
if not "%RC11%"=="0" goto :falhou
if not "%RC12%"=="0" goto :falhou
if not "%RC13%"=="0" goto :falhou
if not "%RC14%"=="0" goto :falhou
if not "%RC15%"=="0" goto :falhou
if not "%RC16%"=="0" goto :falhou
if not "%RC17%"=="0" goto :falhou
if not "%RC18%"=="0" goto :falhou
if not "%RC19%"=="0" goto :falhou
if not "%RC20%"=="0" goto :falhou
if not "%RC21%"=="0" goto :falhou
if not "%RC22%"=="0" goto :falhou
if not "%RC23%"=="0" goto :falhou
if not "%RC24%"=="0" goto :falhou
if not "%RC25%"=="0" goto :falhou
if not "%RC26%"=="0" goto :falhou
if not "%RC27%"=="0" goto :falhou
if not "%RC28%"=="0" goto :falhou
if not "%RC29%"=="0" goto :falhou
if not "%RC30%"=="0" goto :falhou
if not "%RC31%"=="0" goto :falhou
if not "%RC32%"=="0" goto :falhou
if not "%RC33%"=="0" goto :falhou
if not "%RC34%"=="0" goto :falhou
if not "%RC35%"=="0" goto :falhou
if not "%RC36%"=="0" goto :falhou
if not "%RC37%"=="0" goto :falhou
if not "%RC38%"=="0" goto :falhou
if not "%RC39%"=="0" goto :falhou
if not "%RC40%"=="0" goto :falhou
if not "%RC41%"=="0" goto :falhou
if not "%RC42%"=="0" goto :falhou
if not "%RC43%"=="0" goto :falhou
if not "%RC44%"=="0" goto :falhou
if not "%RC45%"=="0" goto :falhou
if not "%RC46%"=="0" goto :falhou
if not "%RC47%"=="0" goto :falhou
if not "%RC48%"=="0" goto :falhou
if not "%RC49%"=="0" goto :falhou
if not "%RC50%"=="0" goto :falhou
if not "%RC51%"=="0" goto :falhou
if not "%RC52%"=="0" goto :falhou
if not "%RC53%"=="0" goto :falhou
if not "%RC54%"=="0" goto :falhou
if not "%RC55%"=="0" goto :falhou
if not "%RC56%"=="0" goto :falhou
if not "%RC57%"=="0" goto :falhou
if not "%RC58%"=="0" goto :falhou
if not "%RC59%"=="0" goto :falhou
if not "%RC60%"=="0" goto :falhou
if not "%RC61%"=="0" goto :falhou
if not "%RC62%"=="0" goto :falhou
if not "%RC63%"=="0" goto :falhou
if not "%RC64%"=="0" goto :falhou
if not "%RC65%"=="0" goto :falhou
if not "%RC66%"=="0" goto :falhou
if not "%RC67%"=="0" goto :falhou
if not "%RC68%"=="0" goto :falhou
if not "%RC69%"=="0" goto :falhou
if not "%RC70%"=="0" goto :falhou
if not "%RC71%"=="0" goto :falhou
if not "%RC72%"=="0" goto :falhou
if not "%RC73%"=="0" goto :falhou
if not "%RC74%"=="0" goto :falhou
if not "%RC75%"=="0" goto :falhou
if not "%RC76%"=="0" goto :falhou
if not "%RC77%"=="0" goto :falhou
if not "%RC78%"=="0" goto :falhou
if not "%RC79%"=="0" goto :falhou
if not "%RC80%"=="0" goto :falhou
if not "%RC81%"=="0" goto :falhou
if not "%RC82%"=="0" goto :falhou
if not "%RC83%"=="0" goto :falhou
if not "%RC84%"=="0" goto :falhou
if not "%RC85%"=="0" goto :falhou
echo   TUDO OK.  Log: verify_log.txt
echo ============================================================
echo.
pause
exit /b 0

:falhou
echo   FALHOU. Codigo de saida de cada bateria:
echo     check_project=%RC1%
echo     test_cleanup=%RC2%
echo     test_geom=%RC3%
echo     test_tasks=%RC4%
echo     test_menu=%RC5%
echo     test_todo=%RC6%
echo     test_engine=%RC7%
echo     test_ts_runner=%RC8%
echo     test_names=%RC9%
echo     test_full_oar=%RC10%
echo     test_rotulos=%RC11%
echo     test_fichas=%RC12%
echo     test_rodar=%RC13%
echo     test_verseg=%RC14%
echo     test_velocidade=%RC15%
echo     test_neb_telas=%RC16%
echo     test_lacunas=%RC17%
echo     test_campo=%RC18%
echo     test_motor2=%RC19%
echo     test_devices=%RC20%
echo     test_arranque_devices=%RC21%
echo     test_watcher=%RC22%
echo     test_panel=%RC23%
echo     test_estacao=%RC24%
echo     test_retorno_v88=%RC25%
echo     test_rt=%RC26%
echo     test_caminho_dos_dados=%RC27%
echo     test_credits=%RC28%
echo     test_cover=%RC29%
echo     test_packager=%RC30%
echo     test_delivery=%RC31%
echo     test_consent=%RC32%
echo     test_languages=%RC33%
echo     test_languages_installer=%RC34%
echo     test_shutdown=%RC35%
echo     test_ui=%RC36%
echo     test_design=%RC37%
echo     test_varrer=%RC38%
echo     test_porta=%RC39%
echo     test_inicio=%RC40%
echo     test_provenance=%RC41%
echo     test_moose=%RC42%
echo     test_modelos_v84=%RC43%
echo     test_queue=%RC44%
echo     test_ui_interacao=%RC45%
echo     test_nv_segment=%RC46%
echo     test_skin=%RC47%
echo     test_constructs=%RC48%
echo     test_hnlnl=%RC49%
echo     test_zip_split=%RC50%
echo     test_thumbnail=%RC51%
echo     test_recon3d=%RC52%
echo     test_recon3d_v84=%RC53%
echo     test_bolus=%RC54%
echo     test_dicom=%RC55%
echo     test_bridge=%RC56%
echo     test_bridge_motor=%RC57%
echo     test_bridge_tela=%RC58%
echo     test_nidus=%RC59%
echo     test_elastic=%RC60%
echo     test_lifecycle=%RC61%
echo     test_interactions=%RC62%
echo     test_conversion=%RC63%
echo     test_dryrun=%RC64%
echo     test_installer_light=%RC65%
echo     test_weights=%RC66%
echo     test_loop=%RC67%
echo     test_cleaner=%RC68%
echo     test_batch=%RC69%
echo     test_plausibility=%RC70%
echo     test_overnight=%RC71%
echo     test_levels=%RC72%
echo     test_suite=%RC73%
echo     test_image=%RC74%
echo     test_records=%RC75%
echo     test_version=%RC76%
echo     test_validation=%RC77%
echo     test_fila_simulacao=%RC78%
echo     test_nomes_no_tps=%RC79%
echo     test_nomes_proprios=%RC80%
echo     test_bolus_aplicador=%RC81%
echo     test_componentes=%RC82%
echo     test_entrada=%RC83%
echo     test_installer=%RC84%
echo     test_instalar_direto=%RC85%
echo   O veredito e a soma dos rodapes OK: e FALHOU: do log.
echo   Log completo: %LOG%
echo ============================================================
echo.
pause
exit /b 1
