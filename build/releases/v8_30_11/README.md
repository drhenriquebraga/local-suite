# Local Suite 8.30.11

O instalador reconhece estações já preparadas antes de consultar a internet. Quando os requisitos são compatíveis, o SETUP atualiza apenas o código, mesmo sem conexão. As configurações, os modelos e os plugins da estação são preservados. A galeria demonstrativa ausente pode ser obtida depois.

Em Configurações, no item Atualizar o programa, a opção Escolher ZIP do instalador abre o seletor local do Windows. A tela identifica em vermelho as fontes de atualização indisponíveis.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.10 e o Python 3.14.6 para Windows x64 com zlib 1.3.1.zlib-ng. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.10.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.11.zip
```
