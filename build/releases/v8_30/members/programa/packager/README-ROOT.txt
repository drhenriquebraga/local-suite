Radioterapia.ai Local Suite
Auto-contorno de estruturas para radioterapia
================================================================


COMO COMECAR

  1. Extraia este .zip inteiro  (botao direito -> "Extrair tudo...")
  2. Abra a pasta extraida
  3. Dois cliques em  START_HERE_TO_INSTALL_LOCAL_SUITE.cmd

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
    baixa os pesos das ferramentas selecionadas, direto da fonte
    confere o SHA-256 de cada um
    monta o pacote

  O TAMANHO DELE esta em PACKAGE_SIZE.txt, ao lado do START_HERE_TO_INSTALL_LOCAL_SUITE.cmd, em
  GB; a tela do preparador mostra o mesmo numero. A pasta de trabalho
  precisa de cerca do DOBRO disso livre: a montagem e o pacote convivem
  nela ate o fim.

  Leva de 20 minutos a 2 horas, conforme a internet.


TERMOS DOS COMPONENTES

A suite destina-se ao ensino e a pesquisa. O catalogo apresenta autoria,
finalidade, licencas de codigo e pesos, e fontes de cada componente. O ROCardS
tem uso restrito a pesquisa nao comercial (CC BY-NC 4.0). No JHU pelvico,
a licenca MIT cobre o codigo. A publicacao dos checkpoints nao especifica
licenca separada para os pesos. Os termos originais ficam em:
  https://github.com/AIM-Harvard/ROCardS#license
  https://github.com/JHU-MICA/TwoStepMalePelvicCTSeg/releases/tag/models

Antes de obter os recursos, revise cada ferramenta. Os modelos opcionais
entram conforme a selecao do operador. Na estacao de destino, o instalador
pede uma decisao propria para instalar ou atualizar.

Se a politica da estacao bloquear o instalador, consulte o TI para executar
o instalador autorizado e revisar os termos no perfil do operador.

================================================================
O QUE E ESTA PASTA
================================================================

  START_HERE_TO_INSTALL_LOCAL_SUITE.cmd     o unico arquivo para clicar
  PACKAGE_SIZE.txt   o tamanho do pacote completo, em GB
  README.txt         o texto de entrada, em ingles
  LICENSE            a licenca deste programa (Apache-2.0)
  NOTICE             a autoria dos componentes de terceiros

  O START_HERE se copia para uma pasta temporaria do Windows e roda de
  la. Nao importa de onde voce clicou - do .zip, de Downloads, de um
  pendrive.


O QUE FICA GUARDADO

  MANIFESTO.txt registra os componentes, versoes, origens e hashes.
  O recibo pertence ao operador da maquina. Ele fica no perfil local do
  Windows. Cada estacao revisa os termos antes de instalar ou atualizar.
  A pasta de trabalho tambem contem o preparar_log.txt.


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
