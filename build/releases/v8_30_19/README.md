# Local Suite 8.30.19

### Local Suite 8.30.19

- Com a fila parada, as abas acompanham mudanças por uma conexão local compartilhada. Recolher a barra ou ocultar a tela interrompe as consultas de acompanhamento. Diagnóstico e Configurações só verificam o ambiente completo quando o operador pede.
- O seletor mostra os nomes dos favoritos e das unidades sem abrir pastas de rede automaticamente. O Vigia contínuo acompanha alterações nas pastas e interrompe a leitura ao pausar ou encerrar o turno.
- O esforço de fábrica em TC é Máximo. A suíte preserva a preferência já salva e permite ajustar uma série no modo Personalizado. A estação pode escolher prioridade reduzida de CPU para os processos de inferência.
- Antes de carregar NumPy e SciPy, a suíte configura o OpenBLAS para uma thread quando a estação ainda não definiu esse valor. Isso reduz a memória reservada em repouso e preserva os parâmetros de inferência do PyTorch.
- A recuperação do modo dedicado tem tempo de espera limitado. Se o Windows ainda estiver devolvendo um recurso, a suíte mantém a pendência registrada para recuperação e libera o uso do aplicativo.
- O suporte a processamento simultâneo em múltiplas GPUs permanece desativado nesta versão.
- Atualização de código compatível com o bundle principal 8.30.6 ou superior. A edição mantém os bundles de pesos existentes.

## Reproduzir o instalador

Use o SETUP público da versão 8.30.18 e o Python 3.12.10 para Windows x64 com zlib 1.3.1. Execute na pasta da receita.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.18.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.19.zip
```
