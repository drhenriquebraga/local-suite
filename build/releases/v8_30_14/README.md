# Local Suite 8.30.14

O DICOM Bridge permite converter imagens para o TPS sem enfileirar segmentação. Cada série de RM tem uma escolha explícita de processamento. A ajuda de cada tarefa mostra sua finalidade e as estruturas do modelo.

Na entrega DICOM, cópias equivalentes são reunidas e colisões entre imagens diferentes bloqueiam o lote. A descompressão sem alteração do conteúdo preserva os identificadores. Imagens derivadas recebem novos identificadores e referências de origem. O gravador de RTSTRUCT usa o plano físico de cada corte em séries irregulares e informa a estrutura afetada quando a verificação geométrica falha.

A seleção de protocolos e achados do AutoContorno Neuro foi integrada. As estruturas destinadas ao STUDY podem ser revistas antes de rodar. O reconstrutor permite alternar o plano principal e ampliar a visualização. O seletor de esforço no modo personalizado recebeu navegação por teclado e gesto de arrastar.

Esta atualização inclui o código do NEURO RT 1.3.17. O pacote de pesos do NEURO RT 1.3.13 continua compatível. Para atualizar offline, use o ZIP do SETUP em Configurações → Atualização offline. O instalador confere as dependências presentes na estação.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.12 e o Python 3.14.6 para Windows x64 com zlib 1.3.1.zlib-ng. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.12.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.14.zip
```
