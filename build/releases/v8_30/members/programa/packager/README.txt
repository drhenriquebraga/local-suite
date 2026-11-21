Radioterapia.ai Local Suite - Preparador
================================================================

O QUE E ISTO

Este preparador roda UMA VEZ, numa maquina que tenha internet e permissao
para baixar arquivos. Ele monta o pacote que sera instalado na estacao.

    Maquina com internet          Estacao de pesquisa
    (esta aqui)                   (sem internet, sem admin)

    PREPARAR_AUTO_CONTORNO.cmd    INSTALL.cmd
      revisa e aceita os termos     revisa os termos na estacao
      baixa Python e bibliotecas    extrai o pacote
      baixa os pesos escolhidos     copia os componentes aceitos
      verifica hashes e tamanhos    registra a versao
      monta o .zip  ------------->  leva no pendrive


COMO RODAR

  Dois cliques em  PREPARAR_AUTO_CONTORNO.cmd

PACKAGE_SIZE.txt estima o tamanho quando todos os opcionais entram. A pasta
de trabalho precisa de espaco para a montagem e o arquivo final.

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

   Consulte o TI para executar o instalador autorizado. O preparo local e a
   instalacao offline exigem uma decisao do operador sobre as ferramentas.


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

  MANIFESTO.txt registra a versao, a origem e os hashes dos componentes.
  O aceite das ferramentas fica no perfil local do Windows e pertence ao
  operador da estacao. A pasta de trabalho contem preparar_log.txt.


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
