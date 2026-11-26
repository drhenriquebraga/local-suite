# Local Suite 8.30.18

Correção de desempenho no Windows para a fila, a navegação em pastas e os visores.

- Fechar ou cancelar a busca interrompe as leituras pendentes de pastas, acervos, favoritos e mídias, inclusive em compartilhamentos de rede.
- A fila e o log atualizam enquanto estão em exibição. O card mantém o indicador de progresso na etapa em execução.
- As miniaturas e os visores carregam os dados sob demanda. Ao fechar o visor, a suíte libera os dados associados à aba.
- Em repouso, a tela inicial pausa a animação e o Vigia aguarda trabalho. Execuções de processamento e monitoramento solicitadas pelo operador continuam em segundo plano.

Atualização apenas de código. O instalador aproveita o bundle compatível já instalado. O kit de diagnóstico para Windows é um download separado para medições locais de desempenho.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.17 e o Python 3.12.10 para Windows x64 com zlib 1.3.1. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.17.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.18.zip
```
