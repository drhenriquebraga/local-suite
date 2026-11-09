Radioterapia.ai Local Suite - Preparador
================================================================

O QUE E ISTO

Este preparador roda UMA VEZ, numa maquina que tenha internet e permissao
para baixar arquivos. Ele monta o pacote que sera instalado na estacao.

    Maquina com internet          Estacao de tratamento
    (esta aqui)                   (sem internet, sem admin)

    PREPARAR_AUTO_CONTORNO.cmd    INSTALL.cmd
      baixa Python                  extrai
      baixa bibliotecas             copia para C:\RADIOTERAPIA_AI
      baixa TODOS os pesos          registra a versao
      confere cada SHA-256
      pede aceite das licencas
      monta o .zip  ------------->  leva no pendrive


COMO RODAR

  Dois cliques em  PREPARAR_AUTO_CONTORNO.cmd

O pacote e sempre o COMPLETO -- todas as tarefas e todos os modelos --, e o
tamanho dele esta em PACKAGE_SIZE.txt, na raiz do instalador, em GB. A pasta de
trabalho precisa de cerca do DOBRO disso livre: a montagem intermediaria e o
pacote final convivem nela. Leva de 20 minutos a 2 horas, conforme a internet.

INSTALAR / ATUALIZAR APP NESTA MAQUINA (o botao grande da tela) NAO monta
pacote. Sem instalacao nesta maquina, baixa e monta direto na pasta final do
programa, em etapa unica, sem pasta de montagem, sem .zip e sem
descompactar. Com instalacao, segue a cascata da atualizacao: troca so o que
mudou, e a configuracao do operador fica.


================================================================
SE OS SCRIPTS ESTIVEREM BLOQUEADOS
================================================================

Muitas estacoes de pesquisa e de clinica bloqueiam a execucao de scripts do
PowerShell. Os tres cenarios, do mais comum ao mais restrito:


1. POLITICA "RESTRICTED" DA PROPRIA MAQUINA  (o caso comum)

   O PREPARAR_AUTO_CONTORNO.cmd ja resolve sozinho: ele chama o PowerShell
   com -ExecutionPolicy Bypass, que vale SO PARA AQUELE PROCESSO. Nao altera
   a maquina, nao fica registrado e nao precisa de administrador.

   Se voce viu a janela abrir, este caso ja passou.


2. O ARQUIVO VEIO DA INTERNET E ESTA "BLOQUEADO"

   O Windows marca arquivos baixados. O sintoma e uma mensagem sobre
   "arquivo baixado da internet" ou "nao esta assinado digitalmente".

   Solucao, sem administrador:

     a) Clique com o botao direito no arquivo -> Propriedades
     b) Na aba Geral, no rodape, marque "Desbloquear"
     c) OK

   Faca isso nos DOIS arquivos: o .cmd e o .ps1.

   Pelo Prompt de Comando, na pasta:

     powershell -NoProfile -Command "Get-ChildItem . | Unblock-File"


3. POLITICA IMPOSTA POR DIRETIVA DE DOMINIO  (o caso duro)

   Se o TI aplicou a politica por GPO, o -ExecutionPolicy Bypass NAO
   funciona: a diretiva de dominio vence a do processo. O sintoma e a
   mensagem citar "substituida por uma politica definida em um nivel mais
   especifico".

   Nesse caso ha dois caminhos.

   CAMINHO A - instalar por COPIA DE PASTA, sem script nenhum

     O preparo em si precisa de Python; a INSTALACAO, nao. Se o problema
     for so' na estacao, prepare o pacote noutra maquina e, na estacao:

       1. Extraia o pacote
       2. Copie a pasta LOCAL_SUITE para C:\RADIOTERAPIA_AI\LOCAL_SUITE
       3. Dois cliques em RADIOTERAPIA_AI_LOCAL_SUITE.cmd

     E so'. Nao ha script para liberar.

   CAMINHO B - se o bloqueio for na maquina de PREPARO

     Havendo Python 3.9 ou superior:

       python programa\build\configurar_ambiente.py --preparo C:\caminho

     Esse caminho PULA a tela de licencas, e o preparo se recusa a rodar
     sem o aceite gravado. Crie, na pasta de trabalho, um
     LICENCAS_ACEITAS.txt a partir do MODELO_LICENCAS_ACEITAS.txt.
     Proposital: pular a tela nao pode virar pular o aceite.

   CAMINHO C - pedir a liberacao certa ao TI

================================================================
E TUDO OU NADA
================================================================

  Este programa nao tem versao reduzida. Ele e um so, montado com todos os
  componentes -- runtime Python, TotalSegmentator e os modelos de
  comparacao --, e nao ha escolha de plugins: o pacote e sempre o
  completo.

  A separacao entre preparo e instalacao mudou QUEM baixa os pesos: voce,
  direto da origem, aceitando os termos de quem os publica. Nao mudou uma
  linha do que o pacote contem nem do que o programa faz.

  E ha uma razao alem da licenca para nao existir versao reduzida: o
  contorno bom depende do conjunto. Um pacote sem parte dos modelos
  entregaria um resultado pior e continuaria se chamando Local Suite --
  e quem o instalasse julgaria o aplicativo por uma versao que nunca foi o
  que construimos. Entregar menos, com o mesmo nome, e pior do que nao
  entregar.

  ENTAO: se voce recusar qualquer uma das licencas, o preparador PARA. Nao
  monta um pacote menor, nao baixa pela metade, nao instala nada. Recusar
  nao produz uma versao limitada do aplicativo -- produz nao poder usa-lo.

  A trava esta no proprio preparo, e nao so' na tela: rodando por linha de
  comando, com o arquivo de aceite escrito a mao, uma linha [RECUSADA]
  derruba o preparo do mesmo jeito.


  AS LICENCAS

  Nenhum componente do pacote e de uso nao comercial. O TotalSegmentator,
  que faz o auto-contorno do fluxo principal, e Apache-2.0; o NV-Segment-CT
  (NVIDIA Open Model License), o CADS (CC BY-SA 4.0), o MOOSE (CC BY 4.0),
  os niveis cervicais (CC0-1.0) e o modelo do encefalo em TC (MIT)
  permitem uso comercial. O NOTICE diz qual e de quem.

  Permitir uso comercial NAO e o mesmo que estar liberado para rotina
  clinica: o cartao do NV-Segment-CT diz "for research purposes and not
  for clinical usage". Leia cada licenca antes de aceitar.


================================================================
NA ESTACAO, DEPOIS
================================================================

  1. Copie o .zip para a estacao
  2. EXTRAIA o .zip  (nao de dois cliques no INSTALL.cmd de dentro do zip:
     o Explorer extrai so aquele arquivo e o instalador nao acha o resto)
  3. Dois cliques em INSTALL.cmd

  Instala em  C:\RADIOTERAPIA_AI\LOCAL_SUITE\  e registra a versao em
  C:\RADIOTERAPIA_AI\_instalados.json.

  A atualizacao preserva o que voce construiu: radai_watcher.config,
  _dados.txt, a pasta calibracao\ inteira e os .log.


================================================================
O QUE FICA GUARDADO
================================================================

  LICENCAS_ACEITAS.txt   o que voce aceitou, quando e em qual maquina
  MANIFESTO.txt          cada componente: versao, origem, tamanho e SHA-256
  preparar_log.txt       o log completo do preparo

  Os dois primeiros viajam DENTRO do pacote e sao exibidos de novo na
  estacao. O MANIFESTO responde "qual versao esta instalada", que e o que o
  registro do servico precisa dizer -- guarde-o junto da
  documentacao do servico. A retencao exigida e de dez anos.


================================================================
SE ALGO DER ERRADO
================================================================

  O preparo ABORTA em vez de continuar torto. Se um arquivo baixado nao
  bater com a soma esperada, ele para e diz qual foi e qual soma se
  esperava -- em vez de empacotar um peso corrompido que so daria defeito
  no primeiro paciente processado, semanas depois.

  Mande o preparar_log.txt junto com o relato. Ele esta na pasta de
  trabalho que voce escolheu.

  E O LOG DO PREPARADOR, que existe desde o primeiro segundo -- inclusive
  quando nada chegou a ser baixado --, fica em

      %LOCALAPPDATA%\RadioterapiaAI\logs\preparer_<data>.log

  A tela de erro do START_HERE.cmd diz qual arquivo e mostra as ultimas
  linhas dele.

  Ferramenta de apoio. Nao validada para uso clinico. Toda saida e rascunho
  sujeito a revisao medica.
