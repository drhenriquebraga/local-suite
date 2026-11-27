# Local Suite 8.30.21

### Local Suite 8.30.21

- O modo dedicado preserva o navegador da Local Suite. A fila pode começar mesmo se o Windows demorar para informar quais outros aplicativos e serviços estão abertos. A tela informa quando o inventário ficou indisponível.
- No Rodar Agora, a escolha de esforço fica no formulário personalizado. O botão de enfileirar informa a quantidade de séries e fica desabilitado quando a seleção está vazia. O explorador começa com Hoje e calcula os demais intervalos pela data local da estação.
- Os cartões da fila mostram identificação do paciente, modalidade, cortes e tempo decorrido. A lista acompanha também as últimas tarefas, o pós-processamento e a gravação. Uma ROI sem contorno é registrada para revisão quando as tarefas terminaram e o RTSTRUCT foi entregue. Uma falha de tarefa ou de entrega conserva a indicação operacional.
- O Editor de Contornos se ajusta à janela, abre o RTSTRUCT escolhido no seletor e permite selecionar a estrutura na imagem. A lista oferece renomeação pelo menu. Os visores respeitam os anéis internos dos arquivos produzidos pela suíte e preservam a geometria original dos contornos externos ambíguos.
- Os termos do NEURO RT e do LUNG RT ficam disponíveis nas confirmações de processamento. A seta das áreas de importação foi centralizada.
- O SETUP leva o LUNG RT 1.1.16 e o NEURO RT 1.3.19. A atualização reutiliza os pesos atuais. Os bundles mínimos continuam em 8.30.6 para a suíte, 1.3.0 para NEURO RT e 1.1.2 para LUNG RT.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.20 e o Python 3.12.10 para Windows x64 com zlib 1.3.1. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.20.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.21.zip
```
