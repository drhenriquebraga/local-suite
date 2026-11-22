# Local Suite 8.30.3

## Mudanças para o operador

A entrega de `Heart_ai` na TC passa a determinar a inclusão da descendente anterior (DA) por ROCardS em AUTO e nos protocolos de STUDY ou FULL. O operador pode desligar a DA para a série ou excluí-la do seu protocolo. A preferência do protocolo acompanha a exportação de configurações. O comentário DICOM do reto Johns Hopkins identifica a população de desenvolvimento do modelo.

O gravador registra os valores DICOM Decimal String que precisou corrigir no STUDY. A busca no histórico das comparações agora constrói um índice por consulta. Quatro rotas do gravador foram verificadas com dados sintéticos.

O modo dedicado usa o Explorer da área de trabalho para reabrir aplicativos mesmo quando todas as janelas de pasta estão fechadas. A prévia indica quando a estação não oferece um Explorer adequado. O navegador pessoal com o perfil padrão pode aparecer na prévia após a conferência da sessão, da assinatura, da árvore de processos e dos títulos das janelas. A permissão para habilitar esse modo fica sob controle do operador de cada estação. Se a estação ainda estiver reservada pelo modo dedicado, o lançador preserva a instância e pede que o operador tente novamente depois da restauração.

A política 3.1 explica como a suíte usa o identificador de segurança do Windows (SID) e o nome do computador. O NOTICE inclui os créditos, as transformações e os termos das ilustrações BodyParts3D.

## Rebuild and verify the installer

Download the versioned 8.30.2 installer. With Windows CPython 3.14.6 and the zlib runtime listed in `manifest.json`, run this command in the release directory. The script verifies the source archive, member bytes and final ZIP. [Local Suite 8.30.2 installer](https://github.com/drhenriquebraga/local-suite/releases/download/v8.30.2/RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.2.zip)

```powershell
python3.14 rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.2.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.3.zip
```

The versioned ZIP and the LATEST ZIP have identical SHA-256 hashes. This release supports offline bundles from 8.30. The models and runtime dependencies match 8.30.2.

## Test the published SETUP

Extract the SETUP so its `programa/` directory is beside this release's `testes/` directory. The dedicated-processing tests simulate the queue, applications and services, and keep the recovery journal in a temporary directory. The coronary tests use synthetic CT images, SimpleITK, NumPy and pydicom. The first-use tests use a local web server, Playwright and Chrome on Windows.

```powershell
python -B programa/tools/test_dedicado.py
python -B testes/test_coronaria_study.py
python -B testes/webaceite/test_first_use.py
```
