Radioterapia.ai Local Suite
Auto-contorno de estruturas para radioterapia
================================================================


COMO COMECAR

  1. Extraia este .zip inteiro  (botao direito -> "Extrair tudo...")
  2. Abra a pasta extraida
  3. Dois cliques em  START_HERE.cmd

  So isso. Nao ha instalador para rodar antes.


E SE VOCE CLICAR SEM EXTRAIR?

  O Windows nao executa programa de dentro de um .zip: ele abre so' o
  arquivo clicado, numa pasta temporaria, sem o resto.

  O START_HERE percebe isso sozinho. Ele pergunta ao Windows qual .zip
  esta aberto, procura nas pastas de download e na raiz de cada disco e,
  se ainda assim nao achar, abre uma janela pedindo que voce aponte o
  arquivo. Extrair primeiro continua sendo o caminho curto.


A PRIMEIRA TELA: O QUE VOCE VAI FAZER

  Um botao grande e duas opcoes menores:

  INSTALAR / ATUALIZAR APP NESTA MAQUINA   (o botao grande)
                                     confere se o programa ja esta nesta
                                     maquina, pela marca na pasta e pelo
                                     registro de instalacao:
                                     - se NAO esta, instala tudo: baixa e
                                       monta DIRETO na pasta final, em
                                       etapa unica, sem .zip
                                     - se esta, segue a cascata, que decide
                                       sozinha:
                                       1. com internet, se a release tem
                                          instalador mais novo, baixa-o,
                                          confere e segue por ele
                                       2. se a instalacao tem os mesmos
                                          requisitos, troca so' o codigo,
                                          sem internet
                                       3. se nao tem e ha internet,
                                          atualiza tudo na pasta instalada
                                       4. se nao tem e nao ha internet,
                                          pede o .zip completo que voce
                                          trouxe; sem ele, cancela e diz
                                          que o pacote instalado nao serve

  Maquina offline: instalar de um    instala o .zip que voce trouxe; nao
  pacote que eu trouxe               baixa nada, nao precisa de internet
  Maquina com internet: montar um    baixa tudo e gera UM arquivo para
  pacote para levar para a maquina   levar num pendrive
  offline

  Desinstalar (discreto, embaixo)    remove, e oferece guardar o que
                                     voce construiu

  Instalar tudo e montar um pacote precisam de internet; a atualizacao
  usa a internet quando ha, e diz no log cada decisao.
  Toda opcao que troca o codigo fecha o app antes, se ele estiver
  aberto naquela pasta, e diz no log.


O QUE VAI ACONTECER NO PREPARO

  Voce le e aceita as licencas dos componentes, escolhe a pasta de
  trabalho, e ele faz o resto:

    baixa o Python portatil       nao instala nada no Windows
    baixa as bibliotecas          em versoes fixadas
    baixa os pesos de TODOS os modelos
    confere o SHA-256 de cada um
    monta o pacote

  O PACOTE E SEMPRE O COMPLETO: todas as tarefas do TotalSegmentator e
  todos os modelos de comparacao. Nao ha versao reduzida para escolher.

  O TAMANHO DELE esta em PACKAGE_SIZE.txt, ao lado do START_HERE.cmd, em
  GB; a tela do preparador mostra o mesmo numero. A pasta de trabalho
  precisa de cerca do DOBRO disso livre: a montagem e o pacote convivem
  nela ate o fim.

  Leva de 20 minutos a 2 horas, conforme a internet.


E TUDO OU NADA

  O programa nao tem versao reduzida. Se voce recusar qualquer uma das
  licencas, ele para e nao monta nada.

  Nenhum componente do pacote e de uso nao comercial: o TotalSegmentator
  e Apache-2.0, e os quatro modelos de comparacao (NV-Segment-CT, CADS,
  MOOSE e os niveis cervicais) sao de licenca permissiva ou de uso
  comercial permitido. O NOTICE diz qual licenca e de quem, e a tela das
  licencas mostra cada uma antes de qualquer download.


================================================================
SE OS SCRIPTS ESTIVEREM BLOQUEADOS
================================================================

  Acontece em estacao de clinica e de pesquisa. Nesse caso NAO tente
  contornar por linha de comando: a instalacao vira uma copia de pasta,
  e nao precisa de script nenhum.

  1. Extraia o pacote (o .zip grande que o preparador montou)

  2. Copie a pasta  LOCAL_SUITE  de dentro dele para

         C:\RADIOTERAPIA_AI\LOCAL_SUITE\

     Crie as pastas se nao existirem - isso nao precisa de
     administrador.

  3. Dentro dela, dois cliques em

         RADIOTERAPIA_AI_LOCAL_SUITE.cmd

     E esse o arquivo que abre o programa. Ele sobe o painel no
     navegador, em  http://127.0.0.1:8777/

  4. Para ter o atalho na area de trabalho: botao direito nesse arquivo
     -> "Enviar para" -> "Area de trabalho (criar atalho)"

  So isso. O programa funciona igual: a instalacao normal faz
  exatamente essa copia, e mais o registro da versao.

  SE PREFERIR PEDIR LIBERACAO AO TI, o pedido que costuma passar nao e
  "liberar scripts na maquina". E:

      "Liberar execucao para a pasta C:\RADIOTERAPIA_AI e suas
       subpastas, para o usuario X."

  E um pedido de escopo pequeno, para uma pasta que so existe para
  receber estes aplicativos.


================================================================
O QUE E ESTA PASTA
================================================================

  START_HERE.cmd     o unico arquivo para clicar
  PACKAGE_SIZE.txt   o tamanho do pacote completo, em GB
  README.txt         o texto de entrada, em ingles
  LICENSE            a licenca deste programa (Apache-2.0)
  NOTICE             a autoria dos componentes de terceiros

  O START_HERE se copia para uma pasta temporaria do Windows e roda de
  la. Nao importa de onde voce clicou - do .zip, de Downloads, de um
  pendrive.


O QUE FICA GUARDADO

  LICENCAS_ACEITAS.txt   o que voce aceitou, quando e em qual maquina
  MANIFESTO.txt          cada componente: versao, origem e SHA-256
  preparar_log.txt       o log completo do preparo

  Os dois primeiros viajam DENTRO do pacote. O MANIFESTO responde "qual
  versao esta instalada", que e o que o registro de validacao da RDC
  657/2022 precisa dizer - guarde-o junto da documentacao do servico. A
  retencao exigida e de dez anos.


SE ALGO DER ERRADO

  O preparo ABORTA em vez de continuar torto. Se um arquivo baixado nao
  bater com a soma esperada, ele para e diz qual foi e qual soma se
  esperava - em vez de empacotar um peso corrompido que so' daria
  defeito no primeiro paciente processado, semanas depois.

  O LOG DO PREPARADOR fica em

      %LOCALAPPDATA%\RadioterapiaAI\logs\preparer_<data>.log

  um arquivo por execucao, e a tela de erro do START_HERE diz qual e
  mostra as ultimas linhas. Mande esse arquivo junto com o relato -- e o
  preparar_log.txt, que fica na pasta de trabalho que voce escolheu.


================================================================

  Ferramenta de apoio. NAO validada para uso clinico.

  Quem reconhece os orgaos e software de terceiro - TotalSegmentator e
  os modelos de comparacao -, listado no NOTICE. Toda estrutura gerada
  sai como SUGESTAO NAO APROVADA: revisar e aprovar continua sendo ato
  medico, no sistema de planejamento.

  radioterapia.ai
