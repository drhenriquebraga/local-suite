# Local Suite 8.30.20

### Local Suite 8.30.20

- No Rodar Agora, escolha o período no explorador de pastas. O mesmo intervalo vale para a leitura das séries. O rodapé indica pastas fora do período e a opção Todas permite encontrá-las.
- As miniaturas da tabela carregam quando aparecem na tela. Fechar o popup interrompe as leituras. As abas de reconstrução podem compartilhar o cálculo da mesma superfície. O editor interrompe a preparação de prévias ao sair.
- O acervo informa o esforço registrado para cada entrega. A suíte preserva a preferência salva na estação e os modelos escolhidos para a série.
- O código NEURO RT passa a 1.3.19. O serviço de prévia temporal do Nidus aguarda o primeiro trabalho para iniciar e libera o trabalhador ao esvaziar a fila. O código LUNG RT permanece em 1.1.15 e carrega sob demanda.
- A fila registra falhas de memória por tarefa e registra o caminho de execução de cada tentativa. O pós-processamento e a gravação do STUDY terminam em um processo separado para devolver a memória à estação.
- A edição de uso normal processa uma série por vez. O piloto de bancada para duas placas exige duas GPUs NVIDIA identificadas e duas séries de teste. O agendamento e os recuos foram exercitados por simulação. O desempenho em duas GPUs físicas aguarda medição.
- O modo dedicado registra os recursos alterados e sua restauração ao terminar. Janelas abertas em paralelo podem compartilhar a mesma superfície 3D. O fechamento da última aba encerrou o motor e liberou o perfil do Edge em 10,6 s no ensaio da estação.
- A tela dos pacotes informa a disponibilidade do espelho por componente. Para os pacotes sem espelho, permanecem a origem indicada pelo autor e a importação de ZIP. O espelho do instalador continua disponível.
- Na validação com dados sintéticos, a varredura passou em 51 verificações, as miniaturas em 178 e as reconstruções em 179. O teste do instalador verificou a cópia e a importação do livro de rotas e do pós-processador na pasta de destino.
- O instalador aceita os mesmos pacotes de pesos. Os mínimos continuam em 8.30.6 para a suíte, 1.3.0 para o NEURO RT e 1.1.2 para o LUNG RT.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.19 e o Python 3.12.10 para Windows x64 com zlib 1.3.1. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.19.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.20.zip
```
