# Local Suite 8.30.16

O instalador corrige a identificação da versão ao abrir o arquivo de início diretamente no ZIP pelo Explorador do Windows.

A tela inicial do instalador mostra o código incluído, o bundle offline mínimo e o bundle instalado na estação para cada produto. Quando existe um registro de instalação pela internet, a capa identifica essa origem.

| Produto | Código no SETUP | Bundle offline mínimo |
|---|---|---|
| Local Suite | 8.30.16 | 8.30.6 |
| LUNG RT | 1.1.15 | 1.1.2 |
| NEURO RT | 1.3.18 | 1.3.0 |

O NEURO RT 1.3.18 é uma atualização de código. Quem já tem o bundle de pesos 1.3.13 ou 1.3.17 pode reutilizá-lo.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.15 e o Python 3.12.10 para Windows x64 com zlib 1.3.1. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.15.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.16.zip
```
