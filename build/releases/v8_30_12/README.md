# Local Suite 8.30.12

A instalação offline de NEURO RT e LUNG RT identifica o pacote de pesos pelo ZIP. O preparador protege a fila e fecha a janela da suíte antes de reabri-la. O visor de séries do NEURO mostra os parâmetros técnicos de aquisição.

O LUNG RT oferece contorno de nódulo, protocolos torácicos na série selecionada, saídas por fase em 4D e rastreio contínuo com revisão axial.

Coronárias aceita o ZIP oficial de 646.540.660 bytes no painel. A importação local tem interface em 12 idiomas, escolha por clique ou arraste e aceite de pesquisa. Os três plugins mostram o progresso do envio. NEURO RT 1.3.15 aceita o bundle de pesos 1.3.13. LUNG RT 1.1.15 reaproveita o de 1.1.14.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.11 e o Python 3.14.6 para Windows x64 com zlib 1.3.1.zlib-ng. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.11.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.12.zip
```
