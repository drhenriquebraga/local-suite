# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

import radai_archive
import radai_menu
import radai_web

VERSAO_DOCS = "2.0"
DATA_DOCS = "2026-10-25"
ARQUIVO_ACEITE = "aceite.json"

IMPRESSOES_PUBLICADAS = {
    "1.4": "8c43155546aca32895fd4bf306267582a2cf6cd0ab2376f6939ddff618b78108",
    "1.5": "73fece8185e4971da0902397c44d6e5a0c5510a6253439eab070ad7124f56489",
    "1.6": "c2c37d60c50a13c6e24bab5c813ce26ff40ebdc0696a82dc649e5c2fc9237b62",
    "1.7": "8d75736e7e460b276f0c1b855870c7024d2bff9a7de31a3a6a5f7c93b7f144f7",
    "1.8": "3d4a4f8773824f220e2e58d61b85522681a10a7ca78daf4618e151845f781ad5",
    "1.9": "087a47baff075f36e14b23ddac71396fc206f7ab9b611a0c88936b2f47948e1d",
    "2.0": "c6b3c126af07cd56a14230008af944a09824c7d7f9ed51b834dcfdca4728aa97",
}

# GUARDA: versao publicada nao se retoca (mudou o texto, versao nova); so a
# linha de uma versao ainda nao publicada se troca, e cada troca fica no dado
# abaixo, com o que entrou no texto.
RESSELAGENS_ANTES_DA_PUBLICACAO = {"1.4": 2, "1.5": 3, "1.6": 4, "1.7": 3,
                                   "1.8": 6, "1.9": 2,
                                   "2.0": 2}

IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO = {
    "2.0": (
        ("4ed91a7fa1c7",
         u"a janela achada pelo titulo, com a linha de comando so como "
         u"recuo, e o F11 so na janela que nao cobre o monitor; o estado "
         u"do otimizador tirado tambem dos quatro modelos do registro, so "
         u"em pacote novo, com a modificacao no NOTICE; o Vascular pela "
         u"segmentacao do ContourLab; o lado da ATM pelo plano medio; os "
         u"dois eixos, a caixa sugerida e o fundo cego do aplicador; a "
         u"escala medida e a ordem dos cortes da imagem do DicomBridge; e "
         u"o aviso MIT do rt-utils no NOTICE"),
        ("a876f8e0154f",
         u"o estado do otimizador tirado dos pesos do TotalSegmentator nos "
         u"pacotes montados e tambem na instalacao direta numa estacao, nos "
         u"Termos, nos Creditos e no NOTICE; o NOTICE com o mapa de rotulos "
         u"do NV-Segment-CT que viaja no instalador leve sob a Apache-2.0, "
         u"que o repositorio do modelo da a todo arquivo que nao e peso; e "
         u"a licenca do CADS open pela publicacao da variante, com o "
         u"LICENSE_MODEL da raiz anterior a ela"),
    ),
    "1.9": (
        ("6ff05d6480aa",
         u"o que o DicomBridge exporta sai em Implicit VR Little Endian nos "
         u"dois sistemas, e o botao do primeiro uso decide so o desenho do "
         u"furo; o CD e lido uma vez, e o pipeline carrega o que a leitura "
         u"achou, a nao ser que o disco tenha mudado"),
        ("efe6ad92b255",
         u"o NOTICE e o subtitulo dos Termos e da Politica com o nome do "
         u"produto, Local Suite, no lugar de Auto-Contorno; e o NOTICE diz "
         u"em que repositorio moram os dois arquivos de outro app que ele "
         u"aponta"),
    ),
    "1.8": (
        ("58a2e6e1212f",
         u"a folha do Overnight Run so le a pasta ao abrir, o teste de "
         u"escrita passa ao Salvar e iniciar, e o ROOT trocado com o turno "
         u"aberto vale no turno seguinte"),
        ("51f1a20351b3",
         u"sai o registro das conversoes que nada grava; o contato pelo "
         u"canal publicado, sem e-mail; o instalador do pacote encerra o "
         u"app como o atualizador; sem funcao de escolha de modelo; a "
         u"mandibula na faixa do C1 ao C4; o DicomBridge com a pasta pela "
         u"metade apagada, o teto e a conferencia das copias do RTSTRUCT, "
         u"a lista na memoria, a sessao da aba e o sufixo do EXTERNO; a "
         u"chave e os campos do Nidus RT na aba; o raio padrao editavel e a "
         u"face de entrada do aplicador"),
        ("bc5a21693d64",
         u"o retorno de campo: fechar pelo X termina a serie em curso e so o "
         u"Fechar tudo interrompe; a trava morta solta ao abrir; o log da "
         u"serie na _RadAI; o caso em andamento e o interrompido no "
         u"registro; o marcador de pronta so com RTSTRUCT no disco; o "
         u"substituir do Nidus RT na fila; o pescoco tambem pelo cranio "
         u"acima do C1; a aorta recortada; a parede que cobre as costelas; "
         u"a pele de um corpo com as estruturas; o pancreas na Bag_Bowel_ai; "
         u"as cristas iliacas e o anus; o raio padrao que so sobe; o corte "
         u"DICOM incompleto recusado; o tema do sistema; o Atualizar app"),
        ("96049f4d5c8c",
         u"o entregue gravado das mascaras finais do completo, antes dele; "
         u"as cristas iliacas e o anus no entregue so com a pelve; o "
         u"marcador de pronta sem RTSTRUCT afastado (done_sem_rtstruct) e a "
         u"serie refeita; a trava com o instante de criacao do dono; o X com "
         u"o turno da noite agendado e o lote que volta a andar; a "
         u"reabertura que pergunta com o turno aberto ou agendado; o "
         u"can't start new thread e a memoria de commit como recurso; a "
         u"faxina do Rodar agora com teto de 2 s e o somente leitura"),
        ("72febbeca60c",
         u"o marcador de pronta sem RTSTRUCT a vista so e afastado quando "
         u"esta estacao o gravou ou quando o RTSTRUCT vai ao lado da serie, "
         u"e o de outra estacao com destino proprio fica; tres faltas de "
         u"recurso seguidas no mesmo processo param o vigia, com a linha no "
         u"log e no cartao, e uma serie concluida zera a conta"),
        ("74be53864f55",
         u"a tela de Creditos deixa de apontar para um documento que nao "
         u"viaja com o programa (a avaliacao dos modelos de pulmao, citada "
         u"no Models Genesis e no modelo que diria o que o achado e)"),
    ),
    "1.7": (
        ("f175cf345fc4",
         u"o vigia sempre AUTO sem o TASKS, o estudo 3D como ato, o derrame "
         u"como anatomia e a mama contendo a glandula"),
        ("b829cde0c294",
         u"os niveis com os nomes de Gregoire e a uniao e as parotidas do "
         u"nivel VIII no OAR, o indice 26 no sacro, o portao do orgao solido, "
         u"a Bag_Bowel_test, o cache por tarefa, os campos novos dos "
         u"marcadores, a pasta propria da serie, o DicomBridge que grava no "
         u"servidor, o video das Reconstrucoes 3D, o TPS de destino, o "
         u"desinstalador e os dados publicos da demo no NOTICE"),
        ("03691d107503",
         u"os niveis cervicais pelo ensemble 2D+3D dos autores, com teto fixo "
         u"de 6 horas"),
    ),
}


def _caminho():
    return radai_archive.raiz() / ARQUIVO_ACEITE


def aceite():
    try:
        with open(str(_caminho()), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def aceito():
    try:
        a = aceite()
        if a.get("versao") != VERSAO_DOCS:
            return False
        feita = str(a.get("impressao") or "")
        return bool(feita) and feita == impressao_dos_documentos()
    except Exception:
        return False


def montar_registro(quem="", itens=None):
    return {"versao": VERSAO_DOCS, "data_documentos": DATA_DOCS,
            "impressao": impressao_dos_documentos(),
            "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quem": str(quem or "")[:80],
            "maquina": os.environ.get("COMPUTERNAME", ""),
            "itens": list(itens or [])}


def registrar_aceite(quem="", itens=None):
    d = montar_registro(quem, itens)
    caminho = _caminho()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(str(caminho), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    return d


PONTOS = [
    ("uso_estudo",
     u"Este é um projeto de estudo e comparação de modelos.",
     u"Não é software médico registrado, não tem marcação regulatória e não "
     u"substitui nenhuma etapa do fluxo clínico do serviço."),
    ("unapproved",
     u"Nenhuma estrutura gerada aqui pode ser usada para tratar.",
     u"Toda estrutura sai como sugestão não aprovada — ApprovalStatus = "
     u"UNAPPROVED — com sufixo de procedência (_ai, _ts, _nv, _cds, _mse, "
     u"_lnl), e cada plugin grava o seu arquivo com um sufixo próprio de "
     u"três letras, listado no NOTICE. Com as tags próprias da estação, uma "
     u"estrutura do entregue pode sair sem o sufixo, com o nome que a estação "
     u"escolheu, e a descrição dela guarda o nome padrão e diz que é sugestão "
     u"de IA não aprovada. Nenhuma tela deste aplicativo aprova "
     u"estrutura: a proteção é por desenho, não por recomendação."),
    ("revisao",
     u"A revisão é ato médico, feita no sistema de planejamento.",
     u"O contorno que trata um paciente é revisado e aprovado por quem "
     u"responde por ele. Concordar com a IA também é um ato de revisão."),
    ("inventa",
     u"O modelo contorna com confiança o que não existe.",
     u"Pedir uma biblioteca de cabeça e pescoço numa TC de tórax devolve "
     u"parótidas plausíveis e inventadas. Sem contraste, estruturas vasculares "
     u"saem não confiáveis. Ele não recusa: desenha."),
    ("remove",
     u"O programa tira estruturas antes de gravar, e diz no log.",
     u"Antes do pós-processamento, quatro regras tiram do conjunto completo — "
     u"e por isso também do entregue — o que não deve chegar ao plano: a "
     u"ponta de um órgão grande na borda do campo, a ilha pequena de um órgão "
     u"que é uma peça só, o pedaço desenhado fora do corpo, e, numa série "
     u"que não mostra a região deles, o coração, o crânio, o encéfalo ou um "
     u"órgão sólido do abdome. Cada remoção vai ao log e ao registro do caso, com o nome, o volume e a "
     u"regra, e não ao RTSTRUCT. O TotalSegmentator cru, quando pedido, sai "
     u"sem elas, e é nele que se confere o que o modelo desenhou. A revisão "
     u"confere também o que falta."),
    ("local",
     u"O processamento é local, e nenhuma imagem vai para servidor externo.",
     u"Os modelos rodam nesta estação. Não há função neste programa que envie "
     u"imagem para servidor externo, e uma verificação automatizada lê o "
     u"código dele e reprova chamada de rede escrita fora dos poucos módulos "
     u"autorizados. Sozinho, o programa faz duas conexões, e "
     u"nenhuma leva imagem ou dado de paciente: a consulta de versão, no "
     u"arranque, e o teste de internet do registro de casos. E, se faltar o "
     u"peso de uma tarefa, a biblioteca do TotalSegmentator tenta baixá-lo da "
     u"origem dela. A Política de Privacidade diz o destino e a frequência de "
     u"cada conexão."),
    ("exportar",
     u"O que você exporta pode identificar o paciente.",
     u"Nada sai da estação sem um ato seu, e cada saída diz o que leva. O "
     u"DicomBridge grava a série como ela veio, com nome, registro e "
     u"nascimento do paciente, numa pasta nova dentro da que você escolher — "
     u"a Downloads do usuário, de partida — e recusa a "
     u"pasta que o programa reconhece como sincronizada com a nuvem e a pasta "
     u"que o vigia processa; a imagem convertida (JPEG, PNG, TIFF ou BMP) "
     u"sai como "
     u"paciente DESCONHECIDO, e atribuí-la ao paciente certo é ato de quem a "
     u"importa no TPS. O vídeo do visor das Reconstruções 3D, o STL do bólus "
     u"e o arquivo do aplicador de braquiterapia vão para a pasta de "
     u"downloads do navegador, e quem confere esse "
     u"destino é você. O pacote do registro de casos sai sem nome, sem "
     u"registro e sem UID. Nenhuma saída anonimiza: tirar o nome do cabeçalho "
     u"não basta, porque a reconstrução 3D de uma TC de crânio devolve o rosto "
     u"— e o vídeo dela também. A Política de Privacidade lista todas."),
    ("deteccao",
     u"Detecção existe nos modelos, não vem ligada, e ligar é ato seu.",
     u"Os modelos de terceiros trazem tarefas e classes que procuram achado — "
     u"nódulo pulmonar, lesão hepática, tumor. Nenhuma roda por "
     u"omissão: o vigia roda sempre o AUTO — a base de anatomia e, depois "
     u"dela, as tarefas de anatomia da região que a própria base desenhou, "
     u"nunca uma de achado — e não lê tarefa do arquivo de configuração, e no "
     u"«Rodar agora» nem o FAST, nem o AUTO, nem um protocolo RT do "
     u"PERSONALIZADO liga uma delas. Ligar uma é ligar a chave dela no "
     u"PERSONALIZADO — e então o que ela devolve sai num arquivo próprio e, "
     u"cru, também no conjunto do TotalSegmentator (RadAI_TS) quando ele é "
     u"pedido, nunca no conjunto completo nem no entregue —, escolher ali um "
     u"protocolo próprio da estação que inclua achado, que pede a declaração "
     u"a cada envio à fila, ou pedir ali um "
     u"protocolo de estudo das Reconstruções 3D, que não grava RTSTRUCT, só "
     u"um mapa de rótulos na subpasta _RadAI da série. Nos três casos o "
     u"programa varre a imagem procurando, o log anuncia com a palavra "
     u"ACHADO, e o registro do caso guarda quais rodaram. O derrame pleural e "
     u"o pericárdico são anatomia do tórax: saem no conjunto completo, e no "
     u"entregue o pericárdico vai dentro do coração de radioterapia. Os "
     u"cistos renais "
     u"são desenhados de fábrica pelo modelo de anatomia, com o rótulo dele: "
     u"desenhar não é afirmar, e o contorno não diz o que a lesão é. Num "
     u"serviço que dependa da isenção do art. 5º da RDC 657/2022, ligar muda "
     u"a classe do aplicativo inteiro — em outra jurisdição a pergunta é "
     u"outra, e a resposta é de lá."),
    ("responsavel",
     u"O serviço é o controlador dos dados.",
     u"O programa roda na infraestrutura do serviço, com dados do serviço. "
     u"Base legal, consentimento e retenção são responsabilidade dele."),
    ("licenca_pesos",
     u"Você recebeu pesos de terceiros, e cada um tem a sua licença.",
     u"As licenças abaixo são DO PESO, e não do código: o NV-Segment-CT da "
     u"NVIDIA (Open Model License — uso comercial PERMITIDO, e o cartão do "
     u"modelo diz que ele é para pesquisa e não para uso clínico); o CADS na "
     u"variante `open` (CC BY-SA 4.0 — comercial, com ShareAlike, que alcança "
     u"um fine-tune seu e não o contorno que sai dele); o MOOSE (CC BY 4.0 — "
     u"comercial, sem ShareAlike, e EXIGE atribuição); e os níveis cervicais "
     u"de Weissmann et al. (CC0-1.0, domínio público); e o modelo do encéfalo "
     u"em TC de Buti et al. (MIT). O TotalSegmentator, "
     u"que faz o fluxo principal, é Apache-2.0. NENHUM componente deste "
     u"pacote é de uso não comercial."),
]

PROIBE = frozenset((
    "unapproved",
))
CUIDADO = frozenset((
    "inventa",
    "remove",
    "exportar",
    "deteccao",
))


def sinal_do_ponto(chave):
    if chave in PROIBE:
        return u"nao"
    if chave in CUIDADO:
        return u"atencao"
    return u"sim"


def fontes_de_terceiros():
    try:
        import radai_models
    except Exception:
        return []
    fora = []
    for chave, m in sorted((getattr(radai_models, "MODELOS", None) or {}).items()):
        fora.append({
            "chave": chave,
            "nome": m.get("nome") or chave,
            "licenca": m.get("licenca") or u"",
            "livre": (m.get("uso_permitido") or u"") != u"nao_comercial",
        })
    return fora


def _visivel(html):
    import html as _h
    import re as _re
    t = _re.sub(r"(?is)<!--.*?-->", u" ", html or u"")
    t = _re.sub(r"(?is)<(style|script)\b.*?</\1\s*>", u" ", t)
    t = _re.sub(r"(?s)<[^>]*>", u" ", t)
    return u" ".join(_h.unescape(t).split())


def _pagina_de_creditos():
    import radai_credits
    return radai_credits.pagina()


def texto_canonico():
    pontos = u"\n".join(u"%s [%s] %s — %s" % (c, sinal_do_ponto(c), t, d)
                        for (c, t, d) in PONTOS)
    fontes = u"\n".join(u"%s — %s" % (f.get("nome") or u"",
                                      f.get("licenca") or u"")
                        for f in fontes_de_terceiros())
    blocos = ((u"aceite", _visivel(PAGINA_ACEITE)),
              (u"pontos", pontos),
              (u"pesos", fontes),
              (u"termos", _visivel(TERMOS)),
              (u"politica", _visivel(POLITICA)),
              (u"creditos", _visivel(_pagina_de_creditos())))
    return u"\n\n".join(u"== %s ==\n%s" % b for b in blocos)


_IMPRESSAO = {"par": None}


def _chave_da_impressao():
    import radai_credits
    fontes = u"\n".join(u"%s — %s" % (f.get("nome") or u"",
                                      f.get("licenca") or u"")
                        for f in fontes_de_terceiros())
    return (PAGINA_ACEITE, TERMOS, POLITICA, tuple(PONTOS), PROIBE, CUIDADO,
            fontes, texto_canonico, radai_credits.pagina,
            radai_credits.chave_do_texto())


def impressao_dos_documentos():
    import hashlib
    chave = _chave_da_impressao()
    par = _IMPRESSAO["par"]
    if par is not None and par[0] == chave:
        return par[1]
    valor = hashlib.sha256(texto_canonico().encode("utf-8")).hexdigest()
    _IMPRESSAO["par"] = (chave, valor)
    return valor


try:
    import radai_cover
    _CSS = radai_cover.CSS_DOC
except Exception:
    _CSS = (u"body{font-family:Arial;background:var(--bg-0,#060d1a);color:var(--text,#e6edf7);"
            u"margin:0;padding:18px;line-height:1.65}"
            u".env{max-width:820px;margin:0 auto}")

CONEXOES_AUTOMATICAS = (
    {"nome": u"Consulta de versão",
     "destinos": ("api.github.com",),
     "texto": (u"Destino: <code>api.github.com</code>, a página de versões do "
               u"projeto, num endereço escrito no código do programa. A "
               u"variável de ambiente <code>RADAI_URL_VERSOES</code> o troca "
               u"por outro (um espelho da instituição) ou, com o valor "
               u"<code>0</code>, desliga a consulta. Quando: uma vez, no "
               u"arranque, em segundo plano. Leva: um <code>GET</code> sem "
               u"corpo e sem parâmetro, com o cabeçalho <code>User-Agent: "
               u"radioterapia-ai-local-suite</code> — nada da estação, nada "
               u"de paciente. Sozinha, ela não baixa nada: se houver versão "
               u"nova, avisa no log e na porta da suíte, com um aviso e um "
               u"ponto na engrenagem; baixar o instalador é um ato seu, no "
               u"«Atualizar agora» (abaixo).")},
    {"nome": u"Teste de internet do registro de casos",
     "destinos": ("pypi.org", "github.com"),
     "texto": (u"Destino: <code>pypi.org</code> e <code>github.com</code>. "
               u"Quando: no máximo a cada 30 minutos, entre uma série e a "
               u"seguinte. Leva: nada — resolve o nome, abre e fecha uma "
               u"conexão na porta 443, sem enviar dado. Serve para o registro "
               u"de cada caso dizer se a estação tinha internet.")},
)


def _lista_de_conexoes():
    return u"\n".join(
        u' <li data-destinos="%s"><b>%s.</b> %s</li>'
        % (u" ".join(c["destinos"]), c["nome"], c["texto"])
        for c in CONEXOES_AUTOMATICAS)


POLITICA = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Política de Privacidade · Radioterapia.AI</title><style>""" + _CSS + u"""
</style></head><body><header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela">Privacidade</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>
<div class="env">
<div class="rc-capa">
 <span class="rc-chip"><i>§</i> Documento</span>
 <h1>Política de <span data-radai-t="1">Privacidade</span></h1>
</div>
<p class="sub">Radioterapia.AI · Local Suite — versão """ + VERSAO_DOCS + u""",
de """ + DATA_DOCS + u""".</p>

<div class="cx aviso">
<p>Este documento descreve o que <b>o programa faz</b>, verificável no código
desta versão. Não é parecer jurídico e não substitui a avaliação do encarregado
de dados do seu serviço.</p>
<p><b>Em resumo:</b> o programa trata imagem de paciente dentro da
infraestrutura do serviço. Os dados, depois de segmentados, <b>ficam ali</b>. O
que sai, sai por um ato seu, e cada saída está nomeada abaixo com o que
leva.</p>
</div>

<h2>1 · Quem é responsável pelos dados</h2>
<p>O programa é instalado e executado <b>na infraestrutura do serviço de
radioterapia</b>, sobre imagens do próprio serviço. Para efeito da LGPD
(Lei 13.709/2018), o <b>serviço é o controlador</b> dos dados pessoais tratados.
O código é aberto, sob a licença Apache-2.0: quem o escreve e quem o publica
não opera, não hospeda e não acessa os dados de nenhum serviço.</p>

<h2>2 · Que dados o programa trata</h2>
<ul>
 <li><b>Imagens DICOM</b> das séries que você aponta, e os cabeçalhos delas.</li>
 <li><b>Identificadores</b>, para organizar o trabalho: o PatientID; o UID da
 série — inteiro no nome dos marcadores e dentro do de conclusão, no nome do
 log da série, no índice local, no acervo e no arquivo da fila, e só
 os oito últimos dígitos no log e na tela; e o nome do paciente, que aparece nas telas
 de escolha e de conversão de séries, servidas apenas a esta estação
 (<code>127.0.0.1</code>), e é gravado nas séries que o DicomBridge exporta
 (seção 5).</li>
 <li><b>O log da estação</b> registra o caminho da série <b>relativo</b> à
 pasta que você apontou — e essa pasta costuma ter o nome do paciente, porque
 quem a nomeia é o sistema que gravou o exame. O caminho absoluto do
 compartilhamento aparece na linha de arranque, quando a varredura não o
 alcança e nas mensagens de erro — a de gravação, por exemplo, cita o arquivo
 que não pôde gravar. Trate o log como qualquer dado de paciente antes de
 tirá-lo da infraestrutura do serviço.</li>
 <li><b>Contornos</b> gerados, e o que o programa mede deles e decide sobre
 eles — o volume, o que as regras de gravação tiraram antes de gravar (seção
 1.3 dos Termos), o que não saiu e por quê —, no log e no registro de
 casos.</li>
 <li><b>No Elastic RT</b>, ao abrir, a Fusão elástica não lê nenhuma pasta:
 cada uma das duas séries — a que se deforma e a de destino — é escolhida por
 você, no acervo desta estação ou numa pasta que você aponta — com o campo
 vazio, a tela pede a pasta —, e a fusão só começa no clique em
 «Fundir». Com as duas escolhidas, o programa lê o
 PatientID e a data de nascimento de cada uma, dentro do processo, só para
 compará-los: a tela recebe apenas se as duas parecem ser de pessoas
 diferentes, e o alerta não impede a fusão.</li>
 <li><b>Um CD</b>, quando você pede «Carregar um CD» no DicomBridge: o
 programa pergunta ao Windows quais unidades são de CD e têm disco — o
 rótulo do disco é consultado só para saber se há disco, e não é guardado
 nem mostrado —, lê o disco inteiro, pastas e subpastas, sem gravar nada
 nele, e o trata como uma pasta apontada. O disco é lido uma vez: o que a
 leitura achou fica na memória do processo e é o que o pipeline carrega, a
 não ser que o disco tenha mudado no meio, quando ele é lido de novo. O CD
 não é oferecido como destino da entrega, e a leitura pode ser
 cancelada.</li>
 <li><b>A leitura de uma pasta que você aponta</b>, no «Rodar agora», no
 «Ver segmentação», no DicomBridge, na Fusão elástica e no «Gerar bólus»:
 ela roda em segundo plano, e as séries aparecem na tela conforme são
 achadas, cada uma com o corte central primeiro. O filtro de data deixa de
 fora a pasta de série que não mudou nos últimos dias — 1, 3, 7 (de
 partida) ou 30, ou todas —, pela data de modificação da pasta, sem abrir
 DICOM nenhum. O que a leitura achou — o caminho, a descrição e os
 identificadores de cada série — fica na memória do processo, até 15 minutos
 depois de ela terminar e no máximo oito leituras, e a leitura pode ser
 parada.</li>
</ul>

<h2>3 · Onde esses dados ficam</h2>
<p>Na estação, ou na infraestrutura do serviço que você apontar. O programa não
tem armazenamento próprio fora dela. Os lugares, um por um:</p>
<ul>
 <li><b>Ao lado da série.</b> Os <b>RTSTRUCT</b> (<code>RS_RadAI_*.dcm</code>)
 são gravados na pasta dos DICOMs — ou na árvore de <code>OUT_DIR</code>, se
 ela estiver preenchida (seção 5). Quais, depende do modo em que a série
 rodou (Termos, seção 1.1): no AUTO — e o vigia roda sempre o AUTO —, o
 conjunto entregue ao sistema de planejamento e o conjunto completo; no FAST,
 só o entregue do FAST; no PERSONALIZADO, o entregue, o completo e o que você
 pediu além deles — o do TotalSegmentator cru, um arquivo para cada plugin,
 para cada modelo de comparação e para os níveis cervicais. Junto fica a
 subpasta <code>_RadAI</code>, com os marcadores de coordenação entre máquinas,
 o log da série e, quando você pede um, o mapa de
 rótulos de um estudo das Reconstruções 3D. O UID inteiro da série está no
 nome de cada marcador, e o que vai dentro depende de qual: o da série em
 curso (a trava, o arquivo &lt;UID&gt;.lock.json em <code>_RadAI</code>) guarda o nome
 da máquina, o número do processo dono e o instante de criação dele (o campo
 <code>criado</code>, um número do Windows), a etapa em que a série está, o
 dispositivo e o tempo de cada tarefa, e a reserva de entrega guarda o nome da máquina e a
 hora — os dois sem nome de paciente e sem caminho; o da escolha que você faz
 na fila guarda a decisão (incluir ou pular) e as regiões marcadas; o de
 conclusão guarda o PatientID, a data do exame e o UID inteiro da série, com
 a máquina, o modo em que ela rodou, os protocolos pedidos no PERSONALIZADO,
 as tarefas, o nome do RTSTRUCT gravado, a
 lista das estruturas, os conjuntos gravados, as regiões que a anatomia
 mostrou, o dispositivo em que rodou e as tarefas que travaram —
 e, quando uma tarefa falhou sem derrubar a série, o texto do erro dela, como
 a exceção o escreveu —, e ainda, quando houver: o que faltou na série e por
 quê (<code>faltou</code>), as tarefas que rodaram sem desenhar nada
 (<code>tasks_sem_estrutura</code>), as que vieram do cache por tarefa
 (<code>tasks_do_cache</code>) e a chave de cada uma no cache
 (<code>cache_das_tasks</code>), a impressão da receita do pós-processamento
 (<code>receita_pos</code>), os motores que rodaram fora do TotalSegmentator
 (<code>motores_fora_do_ts</code>), as tarefas que não couberam na memória,
 com o que cada uma pedia e o que a estação tinha
 (<code>tasks_puladas_por_memoria</code>), o conjunto que não pôde ser
 gravado e o motivo, sem caminho e sem UID (<code>parcial</code>) e,
 quando só o
 pós-processamento foi refeito
 a partir do cache, a origem <code>refeito_pos</code>; e o de falha guarda o
 texto do último erro, como a
 exceção o escreveu, que pode citar o caminho da pasta da série — e essa
 pasta costuma ter o nome do paciente (seção 2) —, com a máquina e a hora, a
 assinatura da falha (<code>assinatura</code>) — dez caracteres que resumem
 o tipo e o texto do erro, iguais em toda série que falhou do mesmo jeito —, o
 turno em que ela falhou (<code data-radai-t="1">turno</code>), a versão do programa
 (<code>versao_do_app</code>), o número de cortes da série
 (<code data-radai-t="1">cortes</code>), até quando cada máquina a deixou adiada
 (<code>adiada</code>), a falha repetida que a pôs em espera
 (<code>em_espera</code>) e, quando a série não é contornável, o motivo, sem
 caminho e sem UID (<code>inelegivel</code>). O de conclusão só é escrito,
 pronta ou parcial, depois que ao menos um RTSTRUCT do programa daquela série
 está gravado e conferido no disco; o de conclusão que já estava na pasta sem
 nenhum RTSTRUCT RadAI da série no disco (Termos, seção 1.4) é afastado para
 o marcador <code>done_sem_rtstruct</code> (o arquivo
 &lt;UID&gt;.done_sem_rtstruct.json em <code>_RadAI</code>), com o mesmo
 conteúdo, e a série é refeita; numa estação com destino próprio, só o que
 ela mesma gravou, e o de outra estação fica onde está. Ao soltar o marcador da série
 em curso, o programa primeiro o renomeia — o nome ganha
 <code>.soltando.</code>, o nome da máquina e o número do processo — e depois
 o apaga; se ele cair nesse instante, esse rastro fica, com o conteúdo do
 marcador, e nada o lê. O log da série
 (<code>_RadAI\\&lt;UID&gt;.log.txt</code>, e o
 <code>_RadAI\\&lt;UID&gt;.log.anterior.txt</code>) recebe cada linha do log
 daquela série no momento em que ela é escrita, no vigia e no «Rodar agora»,
 com o PatientID, o nome e o caminho trocados por
 <code>&lt;paciente&gt;</code> e <code>&lt;caminho&gt;</code>; o UID inteiro
 fica no nome do arquivo, como nos marcadores. Ele tem teto de 4 MB: cheio,
 ele para de crescer, e na tentativa seguinte vira o
 <code>.anterior</code>. Ele fica com a série, como os marcadores de
 conclusão, e é dado de paciente junto com ela. O mapa de rótulos
 (<code>rotulos_</code> e os oito últimos dígitos do UID) guarda o contorno
 cru de cada tarefa que rodou na série — as de achado inclusive —, a geometria da
 série e os protocolos pedidos, com o UID inteiro dentro, e é gravado de novo
 quando a série é estudada de novo. Numa estação que usou uma versão
 anterior, a <code>_RadAI</code> pode guardar ainda as miniaturas que o
 DicomBridge desenhava ali (<code>miniaturas\\</code>), que são imagem da
 série: esta versão não grava mais nelas e não as apaga — apagar é escrever
 no compartilhamento, e isso se combina com o TI. Trate a subpasta
 <code>_RadAI</code> como dado de paciente, junto com a série. Para um
 exame que chegou em <code>.zip</code>, a pasta dos DICOMs é a extração dele,
 dentro da pasta de trabalho (o item «A pasta de trabalho», abaixo).</li>
 <li><b>O índice das pastas</b>, em
 <code>%LOCALAPPDATA%\\RadAI_Watcher\\index.json</code>, no perfil do usuário
 do Windows: por pasta de série, o PatientID, o UID da série e o do estudo, as
 datas e os primeiros 64 caracteres da descrição da série — que é texto livre,
 onde há serviço que digita nome ou iniciais. Ele existe para o vigia não
 reler o compartilhamento inteiro a cada varredura, e para reconhecer as
 fases de uma TC 4D pelo estudo e pela descrição.</li>
 <li><b>A pasta de trabalho</b>: a que tem mais espaço livre entre a pasta
 <code>tmp</code> da instalação (numa estação instalada no caminho padrão,
 <code>C:\\RADIOTERAPIA_AI\\tmp</code>), o <code>%TEMP%</code> do Windows e a
 pasta <code>RADIOTERAPIA_AI\\tmp</code> na raiz de cada disco local da
 estação — nunca uma pasta de rede ou que sincroniza com a nuvem, e só uma
 que aceita gravação. A escolha vale para o processo inteiro, e a variável de
 ambiente <code>RADAI_TMP</code> a fixa. <b>Cada série segmentada ganha nela
 uma pasta própria</b> (<code>radai_serie_</code>…), e ficam ali a
 <b>cópia de trabalho</b> da série, o que os modelos gravam a partir dela e
 uma <b>cópia de cada RTSTRUCT</b> que o programa grava, montada ali antes de
 ir para o lado da série, com o nome, o registro e o nascimento do paciente,
 como o arquivo entregue. Ficam também na pasta de trabalho: o <b>exame que
 chega em <code>.zip</code></b> — o «Rodar agora» e o «Ver segmentação» o
 aceitam —, extraído como veio, identificado, com os RTSTRUCT dele gravados
 dentro da extração; os arquivos que você arrasta para a <b>área de
 envio</b> do DicomBridge — séries DICOM ou imagens —, copiados para
 <code>radai_bridge_entrada</code> com os nomes encurtados, e a extração de
 um <code>.zip</code> que você aponta nele; as <b>miniaturas</b> que o
 DicomBridge desenha de cada série (<code>radai_miniaturas</code>), imagens
 da série com o nome do arquivo feito de um resumo do UID; e a <b>série que
 o DicomBridge converte</b>, numa pasta própria dentro de
 <code>radai_bridge_entrada</code>, identificada como a entregue, até a
 entrega, que a leva para a primeira pasta de destino — a de séries DICOM e
 a de imagens. A seção 6 diz o que o programa apaga dali, quando — e o que
 ele não apaga.</li>
 <li><b>Ao lado do arquivo de configuração</b> (o
 <code>radai_watcher.config</code>, na pasta do programa, ou onde a variável
 <code>RADAI_CONFIG</code> apontar): os nomes próprios das estruturas
 (<code>nomes_proprios.json</code>: a chave «Padrão / Tags próprias» e, por
 estrutura, o nome que a estação escolheu) e os protocolos próprios
 (<code>protocolos_proprios.json</code>: de cada um, o nome, a modalidade, as
 estruturas, as uniões e se ele procura achado) — nada de paciente. A
 atualização os preserva, e o desinstalador oferece guardá-los, como faz com
 o arquivo de configuração. No próprio arquivo de configuração vão também a
 pasta favorita (<code>PASTA_FAVORITA</code>) e a marca de que o guia já
 foi visto nesta estação (<code>GUIA_VISTO</code>).</li>
 <li><b>O acervo</b> (<code>calibracao\\</code>, na pasta do programa, ou onde o
 <code>_dados.txt</code> ou a variável <code>RADAI_CALIB_DIR</code> apontarem):
 o índice das séries contornadas (<code>acervo.jsonl</code>), com o PatientID,
 a data do exame, o UID inteiro e o caminho da pasta de cada uma, o nome do
 RTSTRUCT e a máquina — é dele que sai a lista das séries já processadas
 que o «Ver segmentação», as Reconstruções 3D, o Nidus RT, a Fusão elástica
 e o «Gerar bólus» mostram na aba do acervo local, lida no próprio processo; a
 série escolhida ali abre por um bilhete, sem caminho no endereço da
 página; as máscaras do NV-Segment-CT, uma por série, com o UID
 inteiro no nome do arquivo (<code>nv\\</code>), quando ele roda; e, também
 quando ele roda, uma linha por estrutura comparada com o TotalSegmentator
 (<code>comparacoes.jsonl</code>), com o UID inteiro e o caminho da pasta da
 série; o registro de validação
 (<code>VALIDACAO\\</code>), com cada caso identificado por pseudônimo; o
 índice da fila (<code>fila_series.json</code>): de cada cartão gravado na
 fila, o caminho da pasta da série, o rótulo que a barra
 mostra — que pode ser o nome do paciente —, as pastas para onde copiar o
 RTSTRUCT e a última mensagem (o item «A fila», abaixo); o
 registro dos atos de exportação do 3D Printed Bolus
 (<code>radai_bolus_atos.log</code>: uma linha por arquivo exportado — o STL
 do bólus ou do molde, com o modo e a espessura medida, ou o
 <code>.zip</code> do aplicador de braquiterapia, com os parâmetros dos
 canais, o afterloader e o cateter escolhidos, o raio padrão escolhido, a
 face de entrada do cateter — um lado do paciente: direita, esquerda,
 anterior, posterior, inferior ou superior —, o raio mínimo medido e a cor
 da curva —, com a data e o nome do arquivo — sem nome, registro nem UID); o
 registro dos atos de gravação de vídeo das
 Reconstruções 3D (<code>radai_recon3d_atos.log</code>: uma linha por
 gravação, com a data, a hora e o formato — sem nome, registro nem UID);
 e o registro deste aceite. Numa estação que usou uma versão anterior, o
 acervo pode guardar ainda o que o ciclo de calibração gravou — as receitas,
 as versões e o <b>acervo de treino</b>, com pares de TC e máscara em NIfTI,
 que são <b>imagem de paciente</b>: esta versão não grava mais neles, e não
 os apaga. O programa avisa no arranque se o acervo estiver
 numa pasta que sincroniza com a nuvem.</li>
 <li><b>O cache por tarefa</b>, em <code>cache_tasks\\</code>, ao lado do
 acervo — na pasta do programa, de fábrica — ou onde a variável de ambiente
 <code>RADAI_CACHE_TASKS_DIR</code> apontar: para cada tarefa do
 TotalSegmentator que rodou numa série, o mapa de rótulos que ela devolveu
 (<code>rotulos.npz</code>) e um <code>meta.json</code> com a tarefa, a
 receita e a forma do volume. Não leva nome, PatientID nem UID — o nome de
 cada entrada é uma impressão SHA-256 da imagem, da tarefa e da receita —,
 mas o mapa é o contorno da anatomia daquele paciente: <b>é dado derivado de
 paciente, e não sai da estação</b>. Serve para não rodar de novo a mesma
 tarefa sobre a mesma imagem e para refazer só o pós-processamento de uma
 série. O programa não grava o cache numa pasta que sincroniza com a nuvem,
 numa pasta de rede nem dentro da pasta dos exames (<code>ROOT</code> ou
 <code>OUT_DIR</code>): nesses casos o cache fica desligado, e o log diz. A
 seção 6 diz quando ele é apagado.</li>
 <li><b>O log</b> (<code>.log</code>) e o <code>radai_status.json</code>, junto
 do acervo — ou em <code>LOG_DIR</code>, se ela estiver preenchida. O relatório
 de arranque (<code>arranque_&lt;data&gt;.txt</code>), que fica no mesmo lugar,
 não leva dado de paciente.</li>
 <li><b>O registro do lançador</b> (<code>radai_lancador.log</code>, na pasta
 do programa): a data, a hora e o número do processo de cada passo da
 abertura — a porta, a sessão anterior que foi encerrada ou que recebeu a
 pergunta —, e, quando a sessão anterior não fechou normalmente ou quando o
 motor parou antes de abrir o painel, as últimas linhas da saída da janela do
 motor, que são linhas do log da sessão (seção 2). Passando de 512 kB, ele
 guarda só a metade mais nova. Quando o motor para antes de abrir, a página
 de carregamento mostra só o código de saída e «Tentar novamente»; para
 atender esse botão, o lançador escuta só nesta estação
 (<code>127.0.0.1</code>), numa porta que o Windows escolhe e com uma ficha
 no endereço, por até 10 minutos.</li>
 <li><b>A fila</b>, em <code>C:\\RADIOTERAPIA_AI\\fila\\fila.json</code>, no
 disco do sistema — a variável <code>RADAI_FILA_DIR</code> a põe em outro
 lugar, e, com o acervo apontado por <code>RADAI_CALIB_DIR</code>, ela mora
 na pasta <code>fila</code> dele: de cada cartão, um identificador, de onde
 ele veio (o «Rodar agora», o DicomBridge, o Nidus RT ou o vigia), o estado
 e as horas em que entrou e terminou, o UID inteiro da série, a escolha que
 você fez — o modo, as tarefas, os protocolos e, quando você confirmou que a
 entrega anterior da série seja substituída, essa escolha — e, quando outra estação está
 com a série, o nome dela. Sem nome
 de paciente e sem caminho: esses moram no índice da fila, no acervo (acima).
 As séries que o vigia achou e que ainda esperam não são gravadas, porque ele
 as acha de novo. Ao fechar o programa, os cartões que terminaram com sucesso
 saem do arquivo; ao reabrir, os outros voltam à barra, e o que estava
 rodando volta como falha. A fila vazia não cria arquivo, e o programa não
 grava a fila numa pasta que sincroniza com a nuvem: a barra diz.</li>
 <li><b>O registro de casos</b> (<code>registro\\</code>, na pasta do programa)
 guarda, por tentativa de cada série, o que aconteceu — sem nome, sem
 PatientID e sem UID: a série é identificada por um pseudônimo que não se
 reverte fora desta estação, e o log daquela tentativa vai junto,
 higienizado. O nome da máquina também entra por pseudônimo, inclusive em
 cada etapa: numa clínica pequena ele é o nome de uma pessoa. Ele diz também o modo, o que as regras de gravação tiraram, as
 tarefas que travaram, o pico de memória e a versão e o build do programa,
 que vão também ao índice dos casos (<code>indice.jsonl</code>). O caso é
 gravado também ao começar, em
 <code>registro\\em_andamento\\&lt;pseudônimo&gt;_&lt;processo&gt;.json</code>:
 o pseudônimo da série e o da máquina, a versão e o build do programa, o
 número do processo, por onde a série entrou (o vigia ou o «Rodar agora»), o
 modo, a última etapa e a hora — sem nome, PatientID nem UID —, e esse
 arquivo sai quando a série termina; ao abrir o programa, o caso em
 andamento de um processo que não existe mais vira um caso «interrompido»,
 com a última etapa e a hora. Na gravação, o programa
 confere que nenhum identificador daquela série escapou para o caso ou para o
 log dele, e recusa gravar se escapou. O relatório do registro, que o botão
 de Configurações grava em <code>registro\\relatorios\\</code> (em
 <code>.md</code> e <code>.html</code>) — e que o pacote exportado leva, do
 período dele —, é feito desses casos — contagens,
 tempos, remoções, falhas, versões e as estações, por pseudônimo; a versão e
 o build do programa que o gerou; por motivo de falha, de travamento e de
 interrupção, a primeira e a última data e as versões do programa; os casos
 interrompidos; e os casos recentes com falha, com o pseudônimo, a data e a
 hora, a versão, por onde a série entrou, o modo e o motivo curto —, e,
 antes de gravar, o programa confere que ele não traz UID, e recusa se
 trouxer. A chave do pseudônimo fica num arquivo na pasta do registro
 (<code>_pseudonimo.chave</code>), e a do registro de validação, na pasta
 dele (<code>_pseudonimo.segredo</code>); numa pasta que o programa
 reconhece como sincronizada com a nuvem ela não é gravada: vale só na
 memória do programa, enquanto ele está aberto, e as telas de Configurações
 dizem por quê. A chave que uma versão anterior já tenha gravado ali
 continua sendo lida, e tirá-la da nuvem é ato do serviço.</li>
 <li><b data-radai-t="1">No perfil do usuário do Windows</b>, em
 <code>%LOCALAPPDATA%\\RADIOTERAPIA_AI</code>: o <code>em_uso.json</code>, que o
 programa grava enquanto está aberto, renova a cada 60 segundos e apaga quando
 fecha normalmente — ele existe para o kit de otimização da estação (o
 Workstation RT, do mesmo autor) não fechar o que é deste programa, e leva a
 versão do formato, o nome do programa, a hora, os números de processo do
 programa, dos processos dele e do navegador ligado ao painel, a porta e se há
 uma série sendo segmentada: nada de paciente; e, quando o programa é
 aberto pelo atalho, o
 <code>motor_&lt;porta&gt;.json</code>, que diz se o motor está rodando, o
 número do processo e a hora: nada de paciente. Numa estação que usou uma
 versão anterior, o programa apaga dali, no arranque, o
 <code>otimizar.json</code> que o «Otimizar» de antes deixou (só nomes de
 programas e de serviços, e a hora), e diz no log (Termos, seção
 4.3).</li>
 <li><b data-radai-t="1">No %TEMP% do usuário</b>, quando o programa é aberto pelo atalho: a
 saída da janela do motor, que roda sem janela
 (<code>radai_motor_&lt;porta&gt;.txt</code>) — as mesmas linhas do log da
 sessão (seção 2), recomeçada a cada arranque —, que o lançador mostra se a
 sessão anterior não fechou normalmente; a página local de carregamento que
 o lançador abre no navegador antes de o programa responder
 (<code>radai_carregando_&lt;porta&gt;.html</code>, e o
 <code>radai_carregando_&lt;porta&gt;.js</code> com o estado da abertura), sem
 nada da estação nem de paciente; o perfil próprio do navegador do
 painel (<code>radai_janela</code>), com o armazenamento e o cache de páginas
 dele (o item abaixo); e, quando você pede o «Atualizar agora» (seção 4), a
 pasta <code>radai_atualizar</code>, com o instalador baixado, que sai no
 arranque seguinte, e a extração dele, que fica. O registro dessa
 atualização (<code>radai_atualizar.log</code>, na pasta do programa) guarda
 o que o atualizador mostra na janela dele, sem nada de paciente, e recomeça
 quando passa de 1 MB.</li>
 <li><b data-radai-t="1">Na central de notificações do Windows.</b> Quando uma série termina,
 falha ou é adiada, o programa mostra uma notificação do Windows — no vigia e
 no «Rodar agora» —, e a página aberta, se você permitiu, uma do navegador.
 As duas levam só os oito últimos dígitos do UID e o que aconteceu (o que foi
 gravado, a tentativa) — nunca o nome, o PatientID, um caminho ou o texto do
 erro, que fica no log. <b>A central de notificações do Windows guarda o
 histórico</b>, e quem usar a estação depois o vê. A variável de ambiente
 <code>RADAI_NOTIFICACAO=0</code> desliga a do Windows.</li>
 <li><b data-radai-t="1">O idioma</b> que você escolhe no seletor — no canto das
 telas do aceite e do primeiro uso, ou em Configurações — vai para a chave
 <code>IDIOMA</code> do arquivo de configuração da estação (pela rota interna
 <code>POST /api/idioma</code>) e para o armazenamento local do navegador.</li>
 <li><b data-radai-t="1">Na memória do programa, enquanto ele roda.</b> No
 DicomBridge, de cada entrega com segmentação, a lista das séries entregues —
 as pastas para onde foram, o UID, a escolha e o rótulo, que leva a descrição
 da série —, por até 24 horas e no máximo 64 entregas, nunca em disco: ela
 serve para conferir no disco se o RTSTRUCT chegou a cada pasta e para pôr a
 série de novo na fila, e some quando o programa fecha. No Nidus RT, as
 malhas do 3D da caixa — que, numa série com a cabeça no campo, podem
 mostrar o rosto —, no máximo 24 MB, apagadas quando a série fecha e depois
 de 10 minutos sem uso, nunca em disco. E o que cada leitura de pasta achou
 (seção 2).</li>
 <li><b data-radai-t="1">No navegador desta estação.</b> O armazenamento local do navegador
 guarda, além do idioma, preferências da tela — o tema (claro, escuro ou o
 do sistema), que sem escolha abre escuro e que se escolhe em Configurações
 ou no canto das telas do
 aceite e do primeiro uso, onde ele é gravado antes mesmo do aceite, como o
 idioma; se o menu da esquerda fica expandido; se os avisos já foram
 pedidos; o filtro de data das leituras de pasta — e, para cada série que avisou o fim ou a falha, os oito últimos
 dígitos do UID e a hora do aviso, que nada apaga. O armazenamento da aba, que
 o navegador apaga quando a aba fecha, guarda a pasta varrida no «Rodar agora»
 e, quando você abre uma série do lote no «Ver segmentação», o caminho da
 pasta dela e o UID inteiro, que essa tela apaga assim que os lê; sem dado
 de paciente, o endereço e o nome das telas que a aba visitou (até 40, sem a
 busca do endereço), para o «←» voltar por elas, a guia aberta nas telas que
 a lembram, se a barra da fila foi aberta ou recolhida à mão nesta aba, se
 a tela anterior a mostrava aberta e o passo do guia em que a aba está; no
 DicomBridge, de cada entrega com segmentação, o nome da pasta
 <code>DICOM_BRIDGE_</code>, os identificadores dos cartões que ele pôs na
 fila, com o estado de cada um, e um bilhete opaco — sem caminho e sem a
 descrição da série; e, no Nidus RT, o desenho e os parâmetros de cada
 série aberta — os ângulos, o recorte, a janela, MIP ou MinIP, a laje, o
 inverter, o osso ligado ou desligado, as incidências guardadas e o traço em
 curso —, sob uma impressão SHA-256 do UID da série, de 24 caracteres, sem
 caminho e sem UID: ela é a mesma enquanto a aba estiver aberta, até depois
 de o programa reiniciar.
 Aberto pelo atalho, o navegador do painel usa um perfil próprio
 (<code>radai_janela</code>, no <code>%TEMP%</code> do usuário), e é nele
 que tudo isso fica.</li>
</ul>
<p><b>Nada disso sai sozinho.</b> O que sai, sai por um ato seu — seção 5.</p>

<h2>4 · Conexões de rede</h2>
<p><b>Nenhuma imagem de paciente é enviada para servidor externo.</b> Não existe
função de envio de imagem neste programa. Uma verificação automatizada lê o
código dele e reprova chamada de rede escrita fora de uma lista curta de
módulos autorizados — os que fazem as conexões desta seção e os que só escutam
nesta estação —, e confere que o destino das duas conexões automáticas está
nesta Política. Ela lê o código deste programa, e não o que faz um programa de
terceiro que ele executa: é o caso da biblioteca do TotalSegmentator, cujas
saídas estão descritas abaixo.</p>

<h3>As que o programa faz sozinho</h3>
<p>São duas, e nenhuma leva imagem ou dado de paciente. Como toda conexão pela
internet, elas mostram ao destino o endereço IP de saída e a hora.</p>
<ul id="conexoes-automaticas">
""" + _lista_de_conexoes() + u"""
</ul>
<p><b>A estatística de uso do TotalSegmentator fica desligada.</b> De fábrica,
a biblioteca envia a <code>stats.totalsegmentator.com</code> um relatório de
uso a cada predição. Este programa grava <code>send_usage_stats=false</code> no
arquivo de configuração dela e, no processo que a executa, troca a função de
envio por uma que não envia nada.</p>
<p><b>E uma que só acontece se faltar peso.</b> O pacote traz os pesos de
todas as tarefas que o programa aceita rodar. Se o peso de uma delas faltar na
estação, a biblioteca do TotalSegmentator tenta baixá-lo da origem dela quando
a tarefa roda; sem internet, a tarefa falha e o log diz.</p>
<p><b>E o preparador, que monta o pacote.</b> Numa máquina com internet, ele
baixa o Python, as bibliotecas fixadas e os pesos de cada modelo, da origem de
cada um. Os pesos do TotalSegmentator, desde a v8.2, ele baixa por conta
própria — dos endereços que a própria biblioteca fixada monta, pelo
repositório de certificados do Windows — e confere cada arquivo antes de
extrair: o tamanho exato que a origem publica, o SHA-256 onde a origem publica
um, e o CRC de cada membro do <code>.zip</code>. Nesse preparo nada da estação
e nenhum dado de paciente sobe: só o pedido de cada arquivo. O preparador não
baixa imagem nenhuma: o pacote não traz séries de exemplo.</p>
<p><b>E o «Instalar / Atualizar app nesta máquina» do preparador.</b> O botão
confere primeiro se o programa já está nesta máquina, pela marca na pasta e
pelo registro de instalação. Se não está, ele instala tudo, com os pedidos do
parágrafo acima. Se está, ele consulta a release mais
nova do projeto em <code>api.github.com</code> — um GET sem corpo, com o
cabeçalho <code>User-Agent: radioterapia-ai-preparador</code>, no mesmo
endereço que a variável <code>RADAI_URL_VERSOES</code> troca ou desliga. Se
houver instalador mais novo, ele o baixa da release (o
<code>_SETUP_LATEST.zip</code>, de cerca de 2 MB), confere o tamanho e o
SHA-256 quando a release os publica, recusa o arquivo que grave fora da pasta
ou que diga outra versão, e segue a atualização por ele; se a estação precisar
de um pacote novo e houver rede, ele segue para o preparo do pacote, com os
pedidos do parágrafo acima. Quando a release não responde, ele testa a
internet com um pedido sem dado a <code>pypi.org</code> ou a
<code>huggingface.co</code>. Nada da estação e nenhum dado de paciente
sobe.</p>

<h3>As que só acontecem se você pedir</h3>
<ul>
 <li><b>Os links</b> das telas e destes documentos (artigos, licenças, a
 página de versões, o instalador mais recente, a página do projeto e o relato
 de vulnerabilidade) abrem no seu navegador, como qualquer link.</li>
 <li><b>O «Atualizar agora»</b>, no aviso de versão nova da porta ou no
 cartão «Atualizar o programa» de Configurações: o programa baixa o
 instalador da release mais nova do projeto (o
 <code>_SETUP_LATEST.zip</code>, do endereço que a consulta de versão
 devolveu — no GitHub, <code>github.com</code>, que entrega o arquivo por
 <code>release-assets.githubusercontent.com</code>), com o mesmo
 <code>User-Agent</code> da consulta e nada da estação nem de paciente. Ele
 recusa a release que não publica a soma SHA-256 do arquivo, o endereço que
 não é <code>https</code> e o arquivo que passa do tamanho publicado; confere
 a soma antes de usar o arquivo, e recusa o pacote que grava fora da pasta da
 extração, que é de outro projeto ou que diz outra versão. Com a série do
 vigia, o lote do «Rodar agora» ou o turno da noite em andamento, ele espera
 ou pergunta antes. Se só o código muda, o programa fecha, o atualizador roda
 numa janela do Windows e o programa reabre sozinho, com a sua
 configuração; se a versão nova precisa de um pacote novo de modelos, a tela
 diz o tamanho e o tempo estimado do download e pede uma segunda confirmação
 antes de abrir o preparador da versão nova, que segue com os pedidos do
 preparador (acima).</li>
 <li><b>O «Mapear nova unidade de rede»</b>, nos seletores de pasta: abre o
 diálogo de mapeamento do próprio Windows, na sessão de quem está na estação.
 O endereço, o usuário e a senha que você digita ali ficam com o Windows, e o
 programa não os vê; depois, ele só lê de novo a lista de unidades.</li>
</ul>
<p>O programa não tem tela nem rota que baixe peso de modelo: os pesos vêm no
pacote, que o preparador monta.</p>

<h2>5 · O que sai da estação — só por ato seu</h2>
<p>Cada saída, com o que ela leva:</p>
<ul>
 <li><b>O DicomBridge</b> é uma ferramenta de pipeline único, e grava no
 servidor cada entrega numa <b>pasta nova</b> — <code>DICOM_BRIDGE_</code> com a data e
 a hora, sem nome de paciente nem UID —, dentro da pasta Downloads do usuário,
 que é o destino de partida, ou de cada pasta de destino que você escolher,
 copiada para cada uma; outra máquina, um compartilhamento ou um pendrive
 também servem. Se a cópia para um destino falha, a pasta que ficou pela
 metade nele é apagada, e a tela diz qual destino não recebeu. Não há
 <code>.zip</code>: o sistema de planejamento lê a pasta. «Converter imagens
 para o TPS» lê o que você aponta — arquivos, uma pasta ou um CD (seção
 2) —, converte as séries DICOM e as imagens (JPEG, PNG, TIFF ou BMP)
 que você escolhe e as grava em «Entregar». <b>O DICOM vai como veio: cada corte leva
 o nome, o registro e a data de nascimento do paciente</b>, porque é assim que
 o sistema de planejamento o reconhece. Junto vai, por série, um recibo
 (<code>_RadAI\\recibo_conversao.json</code>) sem nome, registro,
 nascimento, caminho de origem nem UID inteiro. Na etapa «Segmentar», as
 séries entregues vão para a fila com as tarefas que você escolheu, e o
 RTSTRUCT, quando sai, é gravado ao lado da série na primeira pasta de
 destino e copiado só para as outras que receberam o DICOM, no máximo 8 —
 com mais destinos e segmentação pedida, a tela não entrega e diz por quê; a
 cópia recusa a pasta que sincroniza com a nuvem, e, antes de dizer
 «RTSTRUCT entregue», o programa confere no disco se as cópias chegaram. A
 imagem — arrastada para a área de envio ou escolhida pelo «Importar
 imagem», que abre o explorador de arquivos do navegador — entra no mesmo
 pipeline, sem segmentação: o ajuste dela
 — a espessura, obrigatória, a escala, digitada ou medida numa distância
 conhecida da própria imagem, a ordem dos cortes, que você pode inverter, e
 a orientação, tirada da descrição da série, com a escala e a ordem
 conferidas ao lado do MPR antes de converter — fica na etapa do diagnóstico, e
 ela é convertida e entregue junto com as séries DICOM escolhidas, na mesma
 pasta nova. <b>A imagem não diz de quem é: cada série de imagem sai como
 paciente DESCONHECIDO</b>, com o seu próprio ID gerado, que diz de onde veio
 (<code>EXTERNO-</code> com a data, a hora e um sufixo aleatório curto, que
 separa duas estações no mesmo segundo), e a pasta leva um
 <code>LEIA-ME.txt</code> de uma linha mandando atribuí-la ao paciente certo
 no sistema de planejamento — ato de quem a importa (Termos, seção 4.5). O
 recibo dela (<code>_RadAI\\recibo_conversao_imagem.json</code>) guarda a
 geometria que você deu, se a ordem dos cortes foi invertida e o ID gerado.
 Antes de gravar, o programa
 recusa o destino que ele reconhece como sincronizado com a nuvem e o que
 fica dentro da pasta que o vigia processa (o <code>ROOT</code>): gravar ali
 seria escrever no compartilhamento de produção.</li>
 <li><b>O vídeo do visor das Reconstruções 3D</b> (Termos, seção 4.4): MP4 ou
 WebM, gravado pelo navegador e salvo na pasta de downloads dele: <b>o
 programa não sabe que pasta é essa e não a confere</b>.
 Cada gravação só começa por um ato declarado, registrado antes em
 <code>radai_recon3d_atos.log</code>. O nome do arquivo diz só a data e a
 hora. <b>Mas o vídeo de uma série com a cabeça no campo pode mostrar o
 rosto</b>: é uma biometria, e tem de ser tratado como dado de paciente.</li>
 <li><b>O STL do 3D Printed Bolus</b>, e o do molde: o arquivo de impressão 3D
 do bólus e, se você pedir, o do molde — a casca oca, de 1 a 4 mm, cujo
 interior é o bólus, com uma das cinco aberturas, para ser preenchida com
 cera —, que o navegador baixa para a pasta de downloads dele — como no
 vídeo, o programa não sabe que pasta é essa e não a confere. Cada um só
 sai
 por um ato declarado A CADA exportação (a declaração não fica lembrada), e
 cada ato é registrado no acervo, em <code>radai_bolus_atos.log</code>, antes
 de o arquivo sair; sem conseguir registrar, o arquivo não sai. O arquivo não
 leva nome, registro nem UID: o nome diz o modo, a espessura e um sorteio (o
 do molde diz a espessura da casca e a abertura), e
 o cabeçalho diz <code>DRAFT UNAPPROVED</code>. <b>Mas a face interna do bólus
 é a superfície da pele do paciente, e o interior do molde é o bólus:</b> num
 bólus de cabeça ou de face, os dois arquivos são uma biometria, e têm de ser
 tratados como dado de paciente.</li>
 <li><b>O aplicador de braquiterapia do 3D Printed Bolus</b> (Termos, seção
 4.2): um <code>.zip</code> com o STL do aplicador e a ficha dele, em texto —
 os parâmetros, o que foi medido de volta na malha, os alertas e os avisos
 que não somem —, que o navegador baixa para a pasta de downloads dele, como
 o STL do bólus. Ele só sai por um ato declarado a cada exportação, e por um
 segundo ato quando a curva de um canal fica entre o piso do equipamento e
 o raio padrão escolhido; cada exportação é registrada em
 <code>radai_bolus_atos.log</code> antes de o arquivo sair, e sem conseguir
 registrar ele não sai. Nem o STL nem a ficha levam nome, registro, data de
 exame ou UID: o nome do arquivo diz o número de canais, a distância à pele,
 se o canal é aberto ou cego e um sorteio, e o cabeçalho do STL diz
 <code>DRAFT UNAPPROVED</code>. <b>Mas a face interna do aplicador é a
 superfície da pele do paciente:</b> num aplicador de cabeça ou de face, o
 arquivo é uma biometria.</li>
 <li><b>O pacote do registro de casos</b>: o botão em Configurações sela um
 <code>.zip</code> com os casos pseudonimizados e o relatório do período. A
 conferência por valor —
 nenhum identificador daquela série no caso nem no log — é feita na gravação
 (seção 3). Antes de selar, o programa confere de novo o <code>caso.json</code>
 de cada um, procurando campo de identificação e caminho de pasta, e deixa
 fora do pacote o que falhar; o <code>caso.md</code> e o <code>log.txt</code>
 entram como foram gravados. Um caso gravado por uma versão anterior, com o
 nome da máquina cru nas etapas, entra no pacote com o pseudônimo, e o arquivo
 da estação não muda. O segredo do pseudônimo não entra no pacote.
 Enviar o <code>.zip</code> é ato seu.</li>
 <li><b>O arquivo das configurações</b>: o «Exportar» de Configurações
 baixa, para a pasta de downloads do navegador, um <code>.json</code> com as
 chaves do arquivo de configuração — as pastas configuradas inclusive —,
 menos as que são desta máquina (<code>DEVICE</code>, <code>PORT</code> e
 <code>GUIA_VISTO</code>), mais os nomes próprios e os protocolos próprios.
 Ele não leva a chave do pseudônimo, o acervo, a fila nem dado de paciente.
 Ao importar, você marca as seções; o programa mostra o que vai mudar e não
 grava o caminho que não existe nesta máquina, a pasta dos exames que não se
 deixa ler e gravar aqui, o valor de <code>TPS_DESTINO</code> que esta
 versão não aceita, nem o nome ou o protocolo que a validação recusa.</li>
 <li><b>O resumo do turno</b>, que a tela de Configurações mostra para você
 copiar: as últimas 24 horas do registro de casos — contagens, tempos,
 falhas por assinatura e uma linha por série, numerada (#1, #2…), com a
 modalidade, as regiões e o número de cortes —, sem nome, sem PatientID e
 sem UID; antes de mostrá-lo, o programa confere que ele não traz UID, e
 recusa se trouxer. Copiá-lo para fora é ato seu.</li>
 <li><b><code>OUT_DIR</code></b> (arquivo de configuração, vazio de fábrica):
 grava o RTSTRUCT em outra árvore, repetindo as pastas a partir da pasta dos
 exames — o que inclui a pasta do paciente.</li>
 <li><b><code>STATUS_DIR</code></b> (arquivo de configuração, vazio de
 fábrica): cada máquina grava ali o seu sinal de vida — nome da máquina,
 versão, tamanho da fila, quantas séries estão adiadas (as que esperam a vez
 depois de uma falta de memória), o caminho da pasta dos exames e, da série
 em curso, os oito últimos dígitos do UID, o número de cortes, a data e a
 etapa em que ela está. Sem PatientID e
 sem nome; se o laço de trabalho tiver parado por erro, vai também o tipo e o
 texto do erro, com todo caminho trocado por «&lt;caminho&gt;» e todo UID por
 «&lt;uid&gt;».</li>
</ul>
<p>A gravação do DicomBridge e o <code>STATUS_DIR</code> recusam pasta
que o programa reconhece como sincronizada com a nuvem: ele lê a configuração
do Google Drive para desktop e aceita a lista <code>RADAI_RAIZES_NUVEM</code>
para o que não dá para descobrir. O vídeo do visor, o STL do bólus e o
<code>.zip</code> do aplicador não passam por essa conferência, porque quem
escolhe onde gravar é o navegador.
<code>OUT_DIR</code>, <code>LOG_DIR</code> e o acervo não são recusados — o
acervo gera um aviso no arranque, e os outros dois são decisão de quem
configura.</p>
<p><b>Nenhuma dessas saídas anonimiza.</b> Para ensino, publicação ou segunda
opinião, tirar identificadores do cabeçalho não basta: a reconstrução 3D de uma
TC de crânio reproduz o rosto, e há reidentificação publicada por comparação
com foto. Apagar a face é destrutivo — os voxels viram ar — e é trabalho de
ferramenta dedicada, sobre uma cópia. Este programa não apaga a face.</p>

<h2>6 · Retenção e descarte</h2>
<p>Por conta própria, o programa apaga dado de paciente só nos casos abaixo,
todos declarados:</p>
<ul>
 <li>a <b>pasta própria de cada série</b> (<code>radai_serie_</code>…) sai
 quando a série termina — deu certo ou não —, e com ela tudo o que a
 segmentação gravou ali: a cópia de trabalho, o que o TotalSegmentator, o
 NV-Segment-CT, o CADS, o MOOSE, os níveis cervicais e o modelo do encéfalo
 gravam a partir dela, e a cópia de cada RTSTRUCT. Duas dessas cópias saem
 antes: a do RadAI_STUDY, que sai logo depois de gravada, e a do
 RadAI_STUDY_Fast, que sai logo depois de gravada também. Se o programa cair no meio da série,
 a pasta fica, e as faxinas abaixo a alcançam;</li>
 <li>quando o «Rodar agora» começa uma série, ele apaga das pastas de
 trabalho o que tem o nome começando com <code>radai_</code>, em que nada — na
 árvore inteira, e não só na pasta de cima — é modificado há mais de 6 horas,
 e que <b>ninguém está usando</b>: nem o lote em curso, nem uma série da fila
 que ainda vai rodar. Cada faxina dura no máximo 2 segundos, e o que não
 couber sai na série seguinte; arquivo ou pasta somente leitura dentro dessas
 pastas sai junto. Saem assim o que sobrou de uma execução interrompida e
 <b>a extração de um exame que chegou em <code>.zip</code> e os RTSTRUCT
 gravados nela</b>, depois que o lote dela terminou: para guardar esses
 RTSTRUCT, copie-os antes;</li>
 <li>no <b>arranque do programa</b> — inclusive para quem só usa o «Rodar
 agora», porque o vigia sobe junto mesmo com o <code>ROOT</code> vazio —, o
 programa apaga de cada pasta de trabalho possível (a escolhida, o
 <code>%TEMP%</code> e a <code>RADIOTERAPIA_AI\\tmp</code> de cada disco)
 toda pasta cujo nome começa com <code>radai_</code> e que não é modificada
 há mais de 24 horas, pela mesma regra de uso (nada dentro dela mudou nesse
 prazo, e nenhuma série da fila aponta para ela): de novo o que sobrou de uma
 execução interrompida, e isso pode incluir a pasta de uma série, a extração
 de um exame em <code>.zip</code>, com os RTSTRUCT gravados nela, as
 miniaturas e a área de envio do DicomBridge;</li>
 <li>a <b>área de envio do DicomBridge</b>: o que você arrastou sai quando
 você limpa os carregamentos e quando o programa encerra normalmente, e, no
 arranque, o que tem mais de 12 horas; a extração de um <code>.zip</code>
 apontado ali sai quando o programa encerra;</li>
 <li>a <b>série que o DicomBridge converte</b> e que espera a entrega, na
 pasta de trabalho, sai de lá quando você a descarta, quando a entrega a
 leva — ela vai para a primeira pasta de destino, seja série DICOM ou
 imagem — e quando o programa encerra;</li>
 <li>o <b>cache por tarefa</b>: no arranque e a cada varredura do vigia, sai
 a entrada que não é lida há 14 dias e, se o cache passar de 20 GB, as mais
 antigas até ele caber;</li>
 <li>no arranque, o <b>índice do acervo</b> tira a entrada da série cuja pasta
 não existe mais — a entrada, e nenhum arquivo;</li>
 <li>o <b>«Rodar agora»</b>, ao gravar de novo uma série, substitui os
 <code>RS_RadAI_*</code> que o programa tinha gravado nela — e só depois de você
 confirmar na tela: cada conjunto que ele grava de novo entra por cima do
 anterior, e só então ele apaga os que esta execução não produziu (um plugin
 que não foi pedido de novo, por exemplo). O marcador de conclusão anterior da
 série sai do lugar logo antes da gravação nova e é apagado quando ela
 termina; se a execução não entregar, ele volta. Se o programa cair nesse
 intervalo, a próxima varredura do vigia, ou o próximo «Rodar agora» da
 série, o devolve ao lugar, e o log manda conferir a pasta — ou o apaga, se
 o novo já foi gravado. <b>Refazer no FAST uma série que já
 saiu no AUTO ou no PERSONALIZADO apaga o entregue e o completo dela</b> — e
 todo arquivo de estudo que tinha saído com eles: o TotalSegmentator cru, os
 plugins, os de comparação, os níveis cervicais —, e fica só o entregue do
 FAST; se o entregue anterior já foi importado no sistema de
 planejamento, a cópia de lá não muda. Se a execução falhar no meio,
 nada da entrega anterior é apagado: o que já foi regravado fica novo, e o
 resto continua como estava;</li>
 <li>o <b>Nidus RT</b>, quando a série não tem segmentação com osso que sirva
 para tirá-lo da projeção, pode pedir que ela seja refeita em AUTO,
 substituindo a entrega dela pela mesma regra do «Rodar agora» — e só depois
 de você confirmar na tela;</li>
 <li>o <b>complemento de uma série parcial</b> (Termos, seção 1.4), que
 volta sozinho à fila quando a tarefa que faltou passa a caber na memória,
 grava de novo os arquivos RadAI da série, no lugar dos da entrega parcial,
 pela mesma regra do «Rodar agora», sem pedir confirmação: a série e a
 escolha são as mesmas;</li>
 <li>o <b>DicomBridge</b> grava cada entrega numa pasta nova, com a data e a
 hora no nome, e não apaga nenhuma anterior; se a cópia para um destino falha
 no meio, ele apaga, naquele destino, a pasta que ficou pela metade da
 própria entrega;</li>
 <li>o <b>arquivo da fila</b> e o índice dela perdem, ao fechar o programa,
 os cartões que terminaram com sucesso; e o «Limpar» da barra tira cartões,
 e nenhum arquivo de série;</li>
 <li>o <b>log do vigia</b> (<code>radai_vigia.log</code>) passa por um rodízio:
 quando o programa o abre, no arranque, e ele passou de 8 MB, ele vira
 <code>radai_vigia.anterior.log</code>, e o anterior que existia é
 apagado;</li>
 <li>os <b>marcadores de trabalho</b> em <code>_RadAI</code>: o da série em
 curso sai quando ela termina — e o de uma série desta máquina cujo processo
 morreu, ou cujo número de processo foi reaproveitado por um processo criado
 depois do último sinal dele, sai ao abrir o programa, sem encerrar processo
 nenhum —; o de conclusão afastado por não ter RTSTRUCT
 (<code>done_sem_rtstruct</code>) sai quando a série é refeita; a reserva de entrega — que existe só enquanto
 uma máquina grava os RTSTRUCT, para duas não publicarem a mesma série — sai
 logo depois; e o de falha sai quando ela dá certo ou quando você libera as
 falhas na tela;</li>
 <li>o <b>log da série</b> (<code>_RadAI\\&lt;UID&gt;.log.txt</code>) passa
 por um rodízio: se ele chegou a 4 MB, na tentativa seguinte vira o
 <code>.anterior</code>, e o anterior que existia é apagado; fora isso, ele
 não sai sozinho;</li>
 <li>o <b>caso em andamento</b> do registro de casos sai quando a série
 termina; o de um processo que parou vira, ao abrir o programa, um caso
 «interrompido».</li>
</ul>
<p>Os marcadores de conclusão, os contornos gravados ao lado das séries, os
logs das séries, os mapas de rótulos dos estudos, o acervo, o registro e o log
que não passou pelo rodízio permanecem até que o
serviço os remova. A política de
retenção é do serviço. O registro de validação
(<code>VALIDACAO\\</code>) existe para a retenção de dez anos que a RDC
657/2022 pede ao software de uso exclusivo do serviço.</p>
<p><b>O desinstalador.</b> Ele remove a pasta do programa — e com ela o
cache por tarefa, quando ele mora lá, como de fábrica —, e antes oferece
guardar o arquivo de configuração, os nomes próprios e os protocolos
próprios, o acervo (<code>calibracao\\</code>), o
<code>registro\\</code> e os logs. Ele lista também o que ficou fora da
pasta, e só o apaga se você confirmar, ou se ele for chamado com
<code>-ApagarFora</code>: o que tem o nome começando com <code>radai_</code>
na <code>RADIOTERAPIA_AI\\tmp</code> de cada disco e no <code>%TEMP%</code> —
o que sobrou de uma série, a área de envio, as miniaturas, o perfil do
navegador do painel (<code>radai_janela</code>) e a saída da janela do motor
(<code>radai_motor_&lt;porta&gt;.txt</code>) —; os
<code>motor_&lt;porta&gt;.json</code> que ficam em
<code>%LOCALAPPDATA%\\RADIOTERAPIA_AI</code>; e o cache por tarefa posto fora
da pasta do programa junto com o acervo, pelo <code>_dados.txt</code>.
<b>Ficam onde estão</b>, porque não moram na pasta do programa nem nessa
lista: os <code>RS_RadAI_*</code> e as subpastas <code>_RadAI</code> ao lado
das séries; o <code>%LOCALAPPDATA%\\RadAI_Watcher\\index.json</code>; o
<code>em_uso.json</code> (seção 3); a fila
(<code>C:\\RADIOTERAPIA_AI\\fila</code>); o que o
DicomBridge gravou; o que estiver em <code>OUT_DIR</code> e em
<code>STATUS_DIR</code>; o acervo ou o log que tiverem sido postos fora da
pasta do programa; e o cache por tarefa apontado por
<code>RADAI_CACHE_TASKS_DIR</code>. Apagá-los é ato do serviço.</p>

<h2>7 · Direitos do titular</h2>
<p>Pedidos de acesso, correção ou eliminação são atendidos pelo serviço, que
controla os dados. Os arquivos são identificáveis pelo UID da série — na pasta
do paciente, no índice local e no acervo; o registro de casos e o de validação
usam pseudônimo, que só a estação que o gerou consegue recalcular — e,
quando a pasta deles sincroniza com a nuvem, só enquanto o programa está
aberto (seção 3).</p>

<h2>8 · Contato</h2>
<p>Sobre o software: a página do projeto,
<a href="https://radioterapia.ai">radioterapia.ai</a>. Uma vulnerabilidade se
relata em particular, pelo relato privado do repositório do projeto no GitHub
(<a href="https://github.com/radioterapia-ai/local-suite/security">radioterapia-ai/local-suite</a>,
aba Security), e nunca numa issue pública — e nenhum relato leva dado de
paciente. Sobre os dados do seu serviço: o encarregado de dados da sua
instituição.</p>

<p class="sub" style="margin-top:22px">Ao mudar de versão ou de texto, este
documento pede aceite de novo: o aceite guarda a versão e a impressão digital
do texto aceito, e aceitar um texto não é aceitar o que o seguinte passou a
dizer.</p>
</div></body></html>"""

TERMOS = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Termos de Uso · Radioterapia.AI</title><style>""" + _CSS + u"""
</style></head><body><header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela">Termos de uso</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>
<div class="env">
<div class="rc-capa">
 <span class="rc-chip"><i>§</i> Documento</span>
 <h1>Termos de <span>Uso</span></h1>
</div>
<p class="sub">Radioterapia.AI · Local Suite — versão """ + VERSAO_DOCS + u""",
de """ + DATA_DOCS + u""".</p>

<div class="cx aviso">
<h3>Leia isto antes de tudo</h3>
<p><b>Ferramenta de apoio. Não validada para uso clínico. Toda saída é rascunho
sujeito a revisão médica.</b> Os modelos de segmentação são de terceiros —
<a href="/creditos">autoria, licenças e versões</a>.</p>

<p>Este programa é uma <b>ferramenta de estudo e comparação de modelos de
auto-contorno</b>. <b>Não é dispositivo médico</b>, não possui registro na
ANVISA, marcação CE ou autorização da FDA, e <b>não deve ser usado como
ferramenta clínica de produção</b>.</p>

<p>As estruturas geradas saem como <b>sugestão não aprovada</b>
(<code>ApprovalStatus = UNAPPROVED</code>), com sufixo de procedência no nome
— ou, no entregue de uma estação com tags próprias, com o nome que ela
escolheu e a procedência guardada na descrição de cada estrutura (seção 1.6).
<b>A revisão e a aprovação são ato médico</b>, dentro do sistema de
planejamento. Nada é aprovado automaticamente, e nenhuma configuração deste
programa remove essa fronteira. E a fila não começa sem dizê-lo: o diálogo do
«Iniciar», em toda tela que tem a fila, e a folha do turno da noite repetem
que tudo o que é gravado sai como sugestão não aprovada.</p>

<p><b>E nenhum conjunto entregue declara contorno externo.</b> Nenhum traz
<code>BODY</code>, <code>External</code> ou equivalente, e nenhuma estrutura sai
marcada como <code>EXTERNAL</code>: os compartimentos linfonodais cervicais
saem como <code>CONTROL</code>, e todas as outras estruturas como
<code>ORGAN</code>. A recusa fica dentro da função que escreve o arquivo, e
não numa tela, e vale também para o nome próprio que a estação dá a uma
estrutura (seção 1.6).</p>

<p>Isto é uma afirmação sobre o que os arquivos <b>declaram</b>. O conjunto
<code>Skin</code> é uma <b>casca</b> de 5 mm, e casca sozinha não calcula dose:
um sistema de planejamento que a tome como estrutura externa calcula num volume
oco, com falha de ar em profundidade. Fechar a casca recuperaria a superfície
externa — e, fechada, ela deixa de ser pele, porque pele não preenche
cavidade. Quem preenche criou um <code>BODY</code>, e assume essa
decisão.</p>

<p>Então o que protege aqui não é a geometria, e não afirmamos que seja: um
sistema de planejamento (o XiO) fechava contorno importado sozinho, por não ter
noção de casca. O que vale é o que os arquivos dizem de si: <b>nada aqui é
aprovado</b>, e decidir o que um plano pode usar é ato do físico.</p>
</div>

<h2>1 · O que este programa é</h2>
<p>Um aplicativo de <b>pós-processamento</b> e <b>compilação de modelos de
segmentação que já existem</b>: ele executa mais de um modelo de terceiros sobre
a mesma imagem, pós-processa a saída de cada um e deixa comparar os
resultados. A finalidade é <b>ensino e pesquisa</b>. A suíte traz também um
módulo que não contorna nada — o <b>3D Printed Bolus</b>, que desenha um bólus
sobre a pele e o entrega, e um molde para ele, como arquivo de impressão 3D,
e desenha também um aplicador de superfície para braquiterapia
(seção 4.2).</p>

<h2>1.1 · Os três modos, e o que roda em cada um</h2>
<p>No «Rodar agora», cada série é pedida num de três modos. O vigia da noite
roda sempre o AUTO. Uma série pedida sem modo e sem lista de tarefas — por uma
página de versão anterior, por exemplo — roda como AUTO; a que chega sem modo
e com uma lista de tarefas, de um roteiro, roda a lista, e nela toda tarefa é
obrigatória (seção 1.4).</p>
<ul>
 <li><b data-radai-t="1">FAST</b> — a base de anatomia (a do TotalSegmentator
 para TC, ou a de RM) e, com o tórax identificado pela anatomia, as três
 tarefas que o entregue exige ali: a cavidade do tronco, a glândula mamária
 e o derrame pleural e pericárdico; sem tórax, com o coração do modelo de 100 cm³ ou mais,
 só a cavidade do tronco, para o pericárdio. Na RM, só a base. Nenhum nível
 cervical, nenhum motor de comparação. Grava um arquivo só, o entregue do FAST (seção
 1.2).</li>
 <li><b data-radai-t="1">AUTO</b> — a base e, depois dela, as tarefas de
 anatomia da região que a própria base desenhou (seção 4.1), e, na TC, os
 níveis cervicais quando o pescoço é detectado e o modelo do encéfalo quando
 a anatomia mostra crânio ou cabeça e pescoço. Os músculos oculomotores e os dentes não rodam no
 AUTO: são tarefas avulsas, que se pedem no PERSONALIZADO, cada uma no seu
 arquivo. Grava o conjunto completo e o entregue.</li>
 <li><b data-radai-t="1">PERSONALIZADO</b> — a base, o que os protocolos
 ligados arrastam (Crânio; Cabeça e Pescoço avançado, com os níveis
 cervicais; Tórax / Mama; SBRT Pulmão / Fígado; Abdômen; Pelve; Coluna; e, na
 RM, Coluna e Abdômen) e o que a chave de cada tarefa diz — a chave da tarefa
 vence o protocolo. Na TC, a chave da cavidade do tronco nasce ligada, mesmo
 sem protocolo nenhum: é ela que dá o pericárdio ao coração de radioterapia
 (seção 1.2), e desligá-la é um ato seu. A do derrame pleural e pericárdico
 também nasce ligada. É o único modo com comparação de modelos — o
 TotalSegmentator cru e, só em TC, o NV-Segment-CT, o CADS e o MOOSE —, o
 único em que se tira uma estrutura do entregue daquela série, e o único com
 os protocolos de estudo das Reconstruções 3D, que não gravam RTSTRUCT
 (seção 4.1). A tarefa dos músculos de cabeça e pescoço, que traz os
 constritores da faringe, só roda com o pescoço confirmado pela anatomia
 (seção 4.1), mesmo com a chave dela ligada: a trava vence, e o log
 diz. Com um protocolo próprio da estação ligado (seção 1.6), os protocolos
 RT e a seleção livre se desligam, e as tarefas que as estruturas dele pedem
 ficam ligadas e travadas.</li>
</ul>
<p>Nenhum dos três liga tarefa de achado por conta própria (seção 4.1).</p>

<h2>1.2 · O que sai de cada série</h2>
<ul>
 <li><b>O conjunto completo</b> (rótulo <code>RadAI_FULL</code>) leva tudo o
 que a base e as tarefas complementares produzem — as partes e os compostos
 (cada lobo e o pulmão de cada lado, cada costela e as costelas de cada lado),
 as cavidades do tronco, todos os músculos da tarefa dos músculos do tronco
 quando ela roda, o derrame pleural e o pericárdico quando a tarefa dele
 roda, e os níveis
 cervicais quando eles rodam, com os nomes de Grégoire; a parótida do
 TotalSegmentator sai nele sempre com o sufixo <code>_ts</code> (seção 4) —
 e é onde todo o pós-processamento
 acontece: a margem de cada vaso e da traqueia — depois dela, a aorta sai
 recortada dos pulmões, do esôfago e da traqueia —, e as estruturas
 construídas a partir de outras — o coração de radioterapia (<code>Heart_ai</code>), com
 o pericárdio quando a cavidade do tronco rodou e com o derrame pericárdico
 dentro quando ele foi desenhado, o pericárdio corrigido, as duas cavidades
 intestinais — a <code>Bag_Bowel_ai</code> e a <code>Bag_Bowel_OAR_ai</code>
 (abaixo) —, os olhos — cada um o globo inteiro, com o cristalino
 dentro —, a pele, a parede torácica, o
 fêmur recortado na tuberosidade isquiática, as cristas ilíacas e o ânus,
 a mandíbula cheia, a laringe, as duas articulações temporomandibulares e a
 soma dos pulmões (abaixo). Uma construção só sai quando a
 série trouxe o que ela precisa — a parede, as cavidades intestinais e o ânus
 dependem da cavidade do tronco —, e o log diz o que não saiu e por quê. O
 coração é a exceção:
 sem a cavidade do tronco ele sai assim mesmo, montado só dos rótulos
 cardíacos do modelo, menor que o coração da definição, e a descrição da
 própria estrutura diz isso — na RM, porque ela é um modelo de TC e nenhum
 modo a pede ali; e no PERSONALIZADO de uma TC, só quando você desliga a
 chave dela, que nasce ligada, e o log da série diz. Só a cabeça sólida da tarefa
 craniofacial fica fora dele: ela é um contorno externo.</li>
 <li><b>O conjunto entregue</b> (rótulo <code>RadAI_STUDY</code>) é uma
 <b>seleção</b> do completo: as estruturas de uma lista de permitidas,
 gravadas das máscaras finais do completo, antes dele, e iguais às do
 completo, para o sistema de planejamento
 receber só o que se usa. O composto entra no lugar das partes; o osso da
 pelve (<code>Bone_Pelvic_ai</code>), que leva os dois ossos do quadril e o
 sacro, entra só com a pelve identificada pela anatomia — fora dela, fica só
 no completo; as cristas ilíacas (<code>IliacCrest_L_ai</code> e
 <code>IliacCrest_R_ai</code>) e o ânus (<code>Anus_ai</code>) seguem a
 mesma regra: vão ao entregue só quando a anatomia identifica a pelve na
 série, e no completo saem sempre que são construídos — numa TC de tórax ou
 de abdome alto que pegue só a ponta do quadril, ficam só no completo. Os músculos da pelve (<code>Muscles_ai</code>), o sacro sozinho
 (<code>Sacrum_ai</code>) e as adrenais ficam só no completo. Numa série em
 que a anatomia identifica cabeça e pescoço, as estruturas de uma lista
 fechada — o hioide e as cartilagens da laringe, o ar da
 laringe, a cavidade nasal, os condutos auditivos, os palatos, a faringe, os
 seios da face, o crânio, os músculos da mastigação e os digástricos, a
 língua, os dentes, os processos estiloides e os arcos zigomáticos — ficam só
 no completo; e, sem o tórax identificado, os grandes vasos também. As
 carótidas (<code>A_Carotid_ai</code>) ficam só no completo em toda série.
 A laringe (<code>Larynx_ai</code>), as articulações temporomandibulares
 (<code>TMJ_L_ai</code> e <code>TMJ_R_ai</code>) e a mandíbula
 (<code>Bone_Mandible_ai</code>) entram no entregue sempre que são
 construídas. Numa série
 de cabeça e pescoço sem o tórax identificado, a soma dos pulmões
 (<code>Lungs_ai</code>) vai ao entregue no lugar dos dois pulmões, que
 ficam no completo; nas outras, ela vai junto com eles. O encéfalo de uma RM
 (<code>Brain_ai</code>) fica só no completo: o entregue de uma RM não leva
 encéfalo.
 Dos níveis cervicais, vão ao entregue só a união e as parótidas do nível
 VIII (o quadro logo abaixo e a seção 4), e a parótida do entregue vem só
 daí: sem os níveis — no FAST, por exemplo — ou quando o nível VIII não
 serve, o entregue sai sem parótida, e o log diz por quê. Das duas cavidades intestinais,
 só a <code>Bag_Bowel_OAR_ai</code> vai ao entregue; a
 <code>Bag_Bowel_ai</code> fica no completo, para comparação. A glândula
 mamária sai por
 lado (<code>Breast_L_ai</code> e <code>Breast_R_ai</code>), como o
 TotalSegmentator a desenha, com 3 mm a mais de suavização. O derrame não
 vai ao entregue: o pleural (<code>PleuralEff_L_ai</code> e
 <code>PleuralEff_R_ai</code>) e o pericárdico
 (<code>PericardEff_ai</code>) ficam no completo, e no entregue os pulmões
 saem sem o derrame pleural e o coração de radioterapia leva o pericárdico
 dentro (seção 4.1). O reto sai como <code>Rectum_ai</code>, e o cólon que sai é o
 cólon sem o reto (<code>Bowel_Large_ai</code>); quando a divisão falha, o
 cólon sai inteiro, e o log diz. O reto não é desenhado por um modelo: é o
 cólon do modelo dividido por marcos anatômicos — abaixo do plano axial da
 junção sacroilíaca e, além dele, abaixo e atrás do plano do platô do sacro
 (a face superior de S1); o que o plano do platô tira volta ao cólon, e, sem
 o platô medível, fica só o corte axial, e o log diz —, e a procedência gravada na
 estrutura diz isso («derivada por marco anatômico») — revisá-lo é conferir os
 planos de corte, e não só a borda. No PERSONALIZADO, o que você tirou com o «x»
 sai do entregue daquela série e fica no completo; com um protocolo
 próprio (seção 1.6), o entregue é a seleção dele. O que ficou de fora da
 seleção aparece no log. No AUTO e no PERSONALIZADO, quando nenhuma
 estrutura da seleção sai — numa RM em que só o encéfalo foi desenhado, por
 exemplo —, o entregue não é gravado: o completo é a entrega, a série conta
 como pronta, e o log diz «STUDY: saiu vazio».</li>
 <li><b data-radai-t="1">O entregue do FAST</b> (rótulo <code>RadAI_STUDY_Fast</code>, arquivo
 <code>RS_RadAI_FAST_*</code>) leva as estruturas do entregue menos a
 cavidade intestinal (<code>Bag_Bowel_OAR_ai</code>) e o ânus
 (<code>Anus_ai</code>), que é recortado da outra cavidade — nenhuma das duas
 cavidades sai nele; as cristas ilíacas saem, só com a pelve identificada,
 como no entregue; e ele sai sem parótida, porque ela vem dos níveis
 cervicais, que o FAST não roda —, montadas pelo mesmo
 pós-processamento do completo, com duas diferenças que o nome declara: os
 compostos são suavizados inteiros, e não parte a parte; e os pontos de cada
 contorno são reduzidos (Douglas–Peucker, com tolerância de 0,2 mm e pelo
 menos 3 pontos por contorno), menos nas estruturas finas — os nervos
 ópticos, o quiasma, os constritores da faringe e a tireoide —, que saem sem
 redução. O contorno com menos de 1 cm² de área fica
 como está, e o que mudaria de área em mais de 1% volta ao de antes. Essas
 duas guardas comparam cada contorno com ele mesmo antes da redução, e não
 são o teto da diferença entre os dois entregues. Medido em duas TC de tórax
 de teste, de 5 mm, o entregue do FAST saiu, contra o do AUTO da mesma série,
 com DSC de 0,9697 ou mais por estrutura, e a maior diferença de volume foi de
 4,09%, nas grandes veias (<code>GreatVeins_ai</code>): os compostos
 vasculares podem diferir alguns por cento do AUTO, e quem usa o arquivo para
 um histograma dose-volume conta com isso. Não há conjunto completo ao lado
 dele.</li>
 <li><b>O TotalSegmentator cru</b> (rótulo <code>RadAI_TS</code>) é a saída do
 modelo sem pós-processamento nenhum — a referência contra a qual o resto se
 compara. A única mudança nele é o índice 26, que entra no sacro (abaixo).
 Ele só sai quando pedido, no PERSONALIZADO.</li>
 <li><b>Cada plugin</b> — uma tarefa opcional que não alimenta o conjunto
 completo — grava o seu próprio arquivo (rótulo <code>RadAI_</code> e o
 código dele, como <code>RadAI_ORB</code>), com o nosso pós-processamento; e
 cada modelo de comparação grava o seu.</li>
 <li><b>Os rótulos de antes.</b> Os conjuntos que uma versão anterior gravou,
 com os rótulos <code>STUDY_full</code>, <code>RadAI_OAR</code>,
 <code>RadAI_OAR_Fast</code> e <code>STUDY_</code> com o código, continuam
 legíveis com os nomes que têm: nada do que está gravado é regravado, e a
 série segmentada com os rótulos antigos conta como pronta. O nome do arquivo
 (<code>RS_RadAI_</code>…) não mudou, e é por ele que o programa reconhece o
 conjunto.</li>
</ul>
<div class="cx aviso">
<p><b>Um risco declarado: uma região de drenagem no entregue.</b> Até a
versão 8.3, nenhum nível cervical ia ao entregue. Por decisão do autor,
vão agora dois tipos de estrutura: a <b>união dos níveis Ia a VIIb</b>
(<code>LNL_UNION_ai</code>), uma união anatômica não aprovada que <b>não é
OAR nem CTV</b> — a descrição dela diz isso, e o arquivo a marca como
<code>CONTROL</code>, e não como órgão —; e as <b>parótidas</b>
(<code>Parotid_L_ai</code> e <code>Parotid_R_ai</code>), que saem só do
nível VIII (parotídeo) do modelo menos o esternocleidomastoideo: a parótida
do TotalSegmentator não vai ao entregue, e, numa série em que os níveis não
rodaram, o entregue sai sem parótida.</p>
<p>A união é um volume que se parece com alvo, e não um órgão de risco: um
órgão de risco mal contornado subestima uma dose; um volume eletivo mal
contornado deixa doença fora do campo. Escolher o volume eletivo é decisão
médica, e usar a união sem revisá-la nível a nível, no sistema de
planejamento, é o erro que este quadro existe para evitar. Numa série em que
o modelo erra, ela pode descer abaixo das clavículas: quando passa 30 mm do
topo delas, a união não vai ao entregue daquela série, e a descrição de cada
nível marca o estudo e manda conferir a extensão caudal antes de usar
qualquer nível dela. Com pesos de outra versão que não a do mapa dos nomes
(seção 4), a união sai com o nome neutro e não vai ao entregue. Antes da
união, o nível IVb de cada lado perde a clavícula do mesmo lado, e a união
sai recortada igual.</p>
</div>
<p><b>O índice 26 entra no sacro.</b> O TotalSegmentator dá um rótulo
próprio a uma vértebra de transição lombossacra — o índice 26,
<code>vertebrae_L6</code> na versão 3 e <code>vertebrae_S1</code> na 2. Por
decisão do serviço, esse rótulo é fundido ao sacro antes de qualquer
pós-processamento, em todo arquivo — no conjunto completo, no entregue e
também no TotalSegmentator cru —, e nenhum arquivo grava
<code>Vertebrae_L6</code>; a descrição do sacro diz isso. O
sacro sozinho (<code>Sacrum_ai</code>) sai só no completo; no entregue, ele
vai dentro do osso da pelve.</p>
<p><b data-radai-t="1">O recorte nas laterais, e nenhum por âncora.</b> As
tarefas de TC já rodam só dentro do corpo, pelo recorte no corpo, em qualquer
modo e com as exceções da seção 4. Além dele, três tarefas — a cavidade do
tronco, a glândula mamária e os músculos do tronco — rodam numa caixa
recortada nas laterais: a caixa do que tem mais de −500 HU na série, com
10 mm de margem, em qualquer modo, para caberem na memória da estação.
Nenhuma tarefa roda em volta de uma estrutura que a série já desenhou — o
recorte por âncora —, em nenhum modo. A base nunca é recortada.</p>
<p><b>A mama de restrição saiu.</b> As mamas de restrição
(<code>Breast_OAR_L</code> e <code>Breast_OAR_R</code>) da versão anterior não
saem mais, em nenhum conjunto: a glândula mamária sai como o TotalSegmentator
a desenha, com 3 mm a mais de suavização, e a tarefa dos músculos do tronco,
que servia para limitá-la, saiu do FAST, do AUTO e do protocolo Tórax / Mama
— ela roda pelo protocolo Abdômen, pelos protocolos de estudo das
Reconstruções 3D ou pela chave dela, no PERSONALIZADO.</p>
<p>A cavidade intestinal do entregue (<code>Bag_Bowel_OAR_ai</code>) parte da
cavidade abdominal da tarefa da cavidade do tronco e tira dela o fígado, a
vesícula, a bexiga, a próstata, o baço, os rins, as adrenais, os órgãos do
tórax, os vasos, os músculos (o psoas com 20 mm a mais para trás), os ossos e
a pele; tira também 5 mm em volta das grandes veias, das grandes artérias, do
iliopsoas e do baço, a loja perirrenal, o retroperitônio atrás dos grandes
vasos, o compartimento mesorretal e, abaixo da borda inferior da articulação
sacroilíaca — sem ela, do polo da cabeça femoral —, o que passa de 50 mm da
parede anterior. A veia porta fica fora de toda conta. Depois de suavizada em
20 mm, ela recebe de volta, inteiros, o estômago, o duodeno, o pâncreas e o
delgado, e o cólon sem o reto, e sai como um volume só; por último, depois
de todas as subtrações, o furo de cada corte axial é preenchido. Segue o
atlas de Orton
et al. (2022), menos num ponto, que a descrição da estrutura diz: mantém o
estômago e o pâncreas. A <code>Bag_Bowel_ai</code>, da receita anterior,
também leva o pâncreas inteiro, e fica no completo.</p>
<p>As cristas ilíacas (<code>IliacCrest_L_ai</code> e
<code>IliacCrest_R_ai</code>) e o ânus (<code>Anus_ai</code>) são só recorte
do completo, sem modelo novo. Cada crista é o osso do quadril do lado menos o
sacro e menos a porção do corte mais cranial do fêmur do mesmo lado,
inclusive, para baixo; sem o fêmur no campo, ela só sai quando a série termina
acima da cabeça femoral. O ânus é a <code>Bag_Bowel_ai</code> do último corte
do osso pélvico — o mais caudal dos dois lados —, inclusive, para baixo, e não
sai quando o osso pélvico encosta na borda caudal da série.</p>
<p>A parede torácica (<code>ChestWall_L</code> e <code>ChestWall_R</code>)
parte da cavidade torácica de cada lado — o pulmão e o derrame, se houver —,
com as costelas e a metade da cartilagem do lado, expandida em 15 mm; a
cavidade inteira sai de dentro dela, e por isso a parede não engole derrame.
É recortada pelas vísceras e cavidades vizinhas, sem recorte por vasos,
suavizada em 8 mm, e sai com um contorno por corte em cada lado onde há
pulmão — abaixo da base dele, até dois ramos com costela; o que ficou de fora
vai ao log, em cm³. Em todo corte com costela e pulmão do lado, ela cobre ao
menos 90% das costelas: onde a suavização a tirou de cima delas — numa
paciente magra —, volta o pedaço sem suavizar. Ela só sai com o tórax
identificado pela anatomia, ou pedida pelo protocolo Tórax / Mama. A pele
(<code>Skin</code>) é uma casca de 5 mm de um corpo que leva todas as
estruturas já segmentadas e, na metade anterior, junto das alças e da
cavidade abdominal, o tecido a até 10 mm e um fechamento de 5 mm: o estoma, a
gastrostomia, a hérnia e a parede fina sobre o ar da alça ficam dentro; a
mesa e o braço separado ficam fora.</p>
<p><b>O coração não desce pela veia cava, e não perde o pericárdio.</b> A
veia cava inferior sai do coração de radioterapia (<code>Heart_ai</code>) só
onde está separada dele — fora do pericárdio, do coração do modelo e do
derrame pericárdico —: nenhum pixel desses três sai, e nenhum corte que os
tem é descartado. Depois do derrame e do preenchimento dos furos de cada
corte, saem dele o esôfago e os outros vizinhos de fora do pericárdio — os
pulmões, a traqueia, as vértebras, o esterno, as costelas, as escápulas, as
clavículas, o fígado, o estômago e o baço —, e o log diz quanto de cada. A
suavização final dele é a do parênquima mais 3 mm fixos — 5,5 mm com a
suavização padrão.</p>
<p><b>As estruturas finas saem como o modelo as entregou.</b> Os nervos
ópticos, o quiasma, os constritores da faringe e a tireoide saem sem
suavização da máscara e, no FAST, sem redução de pontos do contorno; o corte
em que eles têm um pixel de largura sai pelo contorno dos pixels.</p>
<p><b>A mandíbula sai cheia.</b> A <code>Bone_Mandible_ai</code> é a
mandíbula da tarefa craniofacial com os dentes inferiores por cima, quando a
série os tem, e com o furo de cada corte preenchido nos três planos; a
suavização dela nunca tira área: o que sai é a união da suavizada com a
cheia.</p>
<p><b>A laringe, as articulações temporomandibulares e a soma dos
pulmões</b> são recorte do completo, sem modelo novo. A laringe
(<code>Larynx_ai</code>) soma e liga a cricoide, a cartilagem tireoide, o ar
da laringe e a hipofaringe — com um fechamento de 3 mm e o furo de cada corte
preenchido —, do corte logo abaixo da borda inferior do hioide ao último
corte com a cricoide; sem o hioide ou sem a cricoide na série, ela não sai.
Cada articulação temporomandibular (<code>TMJ_L_ai</code> e
<code>TMJ_R_ai</code>) é o côndilo da mandíbula do lado, do corte em que o
ramo se divide em dois contornos — o processo coronoide à frente, o côndilo
atrás — ao topo do côndilo, com 1 mm de margem em 3D. O lado sai de um
plano médio que passa pelo centro do crânio sem a mandíbula — na falta dele,
do encéfalo, da vértebra C1 ou da C2 —, e só sem nenhum deles pelo meio da
largura da mandíbula; numa mandíbula parcial sem essas estruturas na série, o lado pode
sair trocado, e o log da série diz qual referência valeu. A soma dos pulmões
(<code>Lungs_ai</code>) é o pulmão esquerdo e o direito do completo, como
saíram, sem o derrame pleural.</p>
<p><b>O encéfalo contém os ventrículos e a linha média.</b> No conjunto
completo, os ventrículos e a linha média (a foice) do modelo do encéfalo em
TC são
recortados para dentro do encéfalo (<code>Brain_ai</code>): o que eles tinham
fora dele sai, e o log diz.</p>

<h2>1.3 · O que o programa tira antes de gravar</h2>
<p>Até a versão 8.2, nenhuma regra do programa apagava estrutura: o que
parecia errado era marcado no log e entregue, porque omitir é o erro menos
visível. Por decisão do autor, isso mudou, com escopo: <b>quatro regras tiram
estrutura do conjunto completo antes do pós-processamento</b> — e por isso
também do entregue e do entregue do FAST, que saem dele. O TotalSegmentator
cru não passa por elas.</p>
<ul>
 <li><b data-radai-t="1">A borda do campo</b> — um órgão grande (o pulmão de cada lado,
 fígado, encéfalo, crânio, coração e pericárdio, estômago, cólon, delgado,
 glúteos máximo e médio, fêmures, ossos do quadril, as cavidades do tronco e o
 mediastino) com menos de 300 cm³ e inteiro na faixa da
 borda de cima ou de baixo da série — o maior entre 10 mm e 2 cortes — não
 sai: é a ponta do órgão, e não o órgão. O pulmão é medido pela união dos
 lobos daquele lado: um lobo inteiro na faixa fica quando o pulmão continua
 além dela.</li>
 <li><b data-radai-t="1">As ilhas</b> — nas estruturas que são uma peça só (o pulmão de
 cada lado, fígado, encéfalo, coração, pericárdio, rins, estômago, vesícula,
 próstata, fêmures, ossos da pelve, glúteos, iliopsoas), um pedaço solto com
 menos de 5% do volume e menos de 10 cm³ sai. No pulmão, o pedaço solto é do
 pulmão inteiro: o de um lobo encostado no lobo vizinho fica. Vasos, dentes,
 níveis cervicais, achados, o derrame,
 estruturas pequenas de cabeça e pescoço, adrenais, costelas, vértebras e o
 que mais for feito de pedaços nunca perdem ilha; nas outras, a ilha fica, e
 o log diz «ilha mantida para revisão».</li>
 <li><b data-radai-t="1">Fora do corpo</b> — na TC, o pedaço desenhado inteiramente fora do
 contorno externo sai, e a estrutura que fica vazia não sai. O corpo, para
 esta regra, é o maior pedaço e todo pedaço com pelo menos metade do volume
 dele: as duas pernas de uma TC só de membros inferiores ficam; um braço
 separado do tronco, que tem bem menos que isso, fica fora, e o que o modelo
 desenhou nele sai junto. A pele continua sendo só a do maior pedaço. Esta
 regra vale também nos
 arquivos de plugin e de comparação, que levam o nosso pós-processamento.</li>
 <li><b data-radai-t="1">A região</b> — o coração do modelo, e com ele o coração de
 radioterapia e o pericárdio, só sai com o tórax identificado ou com o coração
 de 100 cm³ ou mais; o crânio e o encéfalo só saem com a cabeça (o encéfalo
 com 150 cm³ ou mais) ou com o pescoço no campo; e, numa série com a cabeça
 ou o pescoço no campo, um órgão sólido do abdome — fígado, baço, rins e
 pâncreas — abaixo de um piso de volume (100 cm³ o fígado, 15 o baço e cada
 rim, 6 o pâncreas) não sai quando nem o abdome nem a pelve estão no campo e
 o tórax não o explica: é o modelo desenhando, num pescoço, um órgão que não
 está ali.</li>
</ul>
<p>Cada remoção do conjunto completo vai ao log e ao registro do caso — o
nome, o volume, a regra e o motivo —; a dos arquivos de plugin e de
comparação vai só ao log. E <b>nada disso é escrito no RTSTRUCT</b>: a estrutura que saiu
simplesmente não está nele. Os avisos de volume que não tiram nada continuam
como estavam: marcam no log, e a estrutura sai. <b>A revisão confere também o
que falta</b>, e o TotalSegmentator cru, quando pedido, mostra o que o modelo
desenhou.</p>

<h2>1.4 · Onde roda, e quando uma tarefa trava</h2>
<p><b>Onde roda.</b> Na placa NVIDIA da estação quando o modelo cabe nela, e
na CPU quando não — a decisão é pela memória livre da placa (ou pela chave
<code>DEVICE</code> do arquivo de configuração), e o motivo vai ao log. No arranque,
o programa lê as placas da estação e confere as que pode usar com um fantoma
sintético (o <i>canário</i>): nenhuma imagem de paciente entra nessa
conferência. As bibliotecas que usariam a placa Intel (XPU e OpenVINO) existem
no código, em pesquisa, e não vêm no pacote.</p>
<p><b data-radai-t="1">Quando uma tarefa trava.</b> Uma tarefa do TotalSegmentator é dada como
travada depois de 15
minutos sem sinal de vida, ou de 30 minutos sem andar com a memória da estação
em 95% ou mais — os três números são chaves do arquivo de configuração
(<code>TRAVA_SEM_PULSO_MIN</code>, <code>TRAVA_PAGINANDO_MIN</code>,
<code>TRAVA_RAM_PCT</code>). A tarefa travada é encerrada — ela, e não a série —,
a lista segue, e ao fim dela a travada é refeita uma vez, com um plano de
memória menor. Travou de novo: a série sai sem ela, e o log e o registro do
caso dizem. Se a travada for a base — ou uma tarefa que vale como ela: no «Rodar
agora», toda tarefa da lista de um roteiro; no vigia, nenhuma além da base —,
a série não sai: o vigia a
devolve à fila sem gastar tentativa, e o «Rodar agora» a dá como falha, com o
motivo. <code>TIMEOUT_TASK_H</code> continua sendo o teto de cada tarefa do
TotalSegmentator, e também o do NV-Segment-CT e o do MOOSE; os níveis
cervicais têm teto fixo de 6 horas, o CADS, de 1 hora, e o modelo do encéfalo
em TC, de 2 horas, que essa chave não muda.</p>
<p><b data-radai-t="1">Quando uma tarefa não cabe na memória.</b> Antes de
rodar cada tarefa, o programa estima a memória que ela pede. A que não cabe na
memória livre da estação não roda naquela série: o resto segue e é entregue,
e o log, o cartão da fila e o marcador de conclusão dizem qual ficou de fora,
quanto ela pedia e quanto havia — a série fecha como parcial. Se a que não
cabe for a base, ou uma tarefa que vale como ela, a série não sai, como em
toda falta de memória: o vigia a adia. A cada 5 minutos, com a estação ociosa
— nada rodando e nada pedido à mão esperando —, a série parcial cuja última
tentativa tem mais de 1 hora volta sozinha à fila quando a tarefa que faltou
passa a caber na memória livre, com a mesma escolha; o complemento grava os
arquivos RadAI da série de novo, no lugar dos da entrega parcial, e o cartão
diz a hora. E o entregue é gravado antes do completo: se o completo não puder
ser gravado, o entregue fica, e a série conta como parcial, com o
motivo.</p>
<p><b>Pronta ou parcial, só com o arquivo no disco.</b> O marcador de
conclusão de uma série — pronta ou parcial — só é escrito depois que ao menos
um RTSTRUCT do programa daquela série está gravado e conferido no disco: o
arquivo existe, não está vazio e se deixa abrir. Sem arquivo, a série conta
como falha, e o motivo diz o que foi anunciado sem arquivo e o que a entrega
disse. Um marcador de pronta ou parcial que já está na pasta sem nenhum
RTSTRUCT RadAI da série no disco — como os que a versão anterior gravava —
não vale como pronta: o vigia o afasta para o marcador
<code>done_sem_rtstruct</code> (o arquivo &lt;UID&gt;.done_sem_rtstruct.json
em <code>_RadAI</code>), a série volta para a
fila e é refeita, com a linha «marcador sem RTSTRUCT: refazendo» no cartão,
e o «Rodar agora» mostra a série «a refazer». Numa estação com destino
próprio (a chave <code>OUT_DIR</code>), só se afasta o marcador que esta
estação gravou: o de outra estação fica como está, porque o RTSTRUCT dela foi
para o destino dela, que daqui não se vê, e o plano do vigia diz que a série
foi feita por ela. Quando a série é refeita, esse
arquivo sai. Pasta que não se deixa listar (servidor fora do ar, acesso
negado) não conta como ausência. Apagar os <code>RS_RadAI_*.dcm</code> de
uma série pronta faz o vigia refazê-la — no mais tardar na próxima abertura
do programa, porque a sessão aberta guarda as séries que já viu com o
arquivo.</p>
<p><b data-radai-t="1">Falta de recurso.</b> «can't start new thread» e as
mensagens de memória de commit esgotada (VirtualAlloc, <i>commit limit</i>,
<i>memory allocation failed</i>) contam como falta de recurso, como a falta de
memória: a série é adiada nesta máquina sem gastar tentativa. Com 3 faltas
de recurso seguidas no mesmo processo, sem nenhuma série concluída entre
elas, o vigia para de pegar série nova: o log e o cartão da próxima série
dizem «o processo parece sem recurso (memória ou threads): feche e abra o
programa», o «Rodar agora» continua possível, e uma série concluída, do
vigia ou do «Rodar agora», zera a conta.</p>
<p><b data-radai-t="1">O arquivo de configuração de uma versão anterior</b> pode trazer chaves
que saíram — <code>TASKS</code>, <code>INCLUIR_NV</code>,
<code>INCLUIR_CADS</code>, <code>INCLUIR_MOOSE</code>,
<code>INCLUIR_HNLNL</code>, <code>ENTREGAR_TS</code>,
<code>TIMEOUT_NV_H</code> e <code>URL_VERSOES</code>, e os nomes antigos
delas. Elas não ligam nem desligam mais nada, e duas delas mudam o que sai:
numa estação que tinha <code>INCLUIR_HNLNL=0</code>, o de fábrica de uma
versão anterior, os níveis cervicais passam a rodar no AUTO e a entrar no
conjunto completo quando o pescoço é detectado, nas condições da seção 4; e o
vigia deixou de ler a lista <code>TASKS</code> — ele roda sempre o AUTO —,
então uma tarefa que estava escrita nela só roda na noite se a anatomia a
pedir, e fora disso se pede série a série, no PERSONALIZADO do «Rodar agora».
O programa as ignora e diz no arranque, uma linha para cada, «chave obsoleta
ignorada».</p>

<h2>1.5 · O primeiro uso, o sistema de planejamento e o fim do programa</h2>
<p>Numa estação nova, o programa pede, nesta ordem: o idioma e o aceite destes
documentos, na tela que abre antes de todas; depois, na tela do primeiro
uso, a pasta favorita, que é opcional — «Pular por agora», ou «Salvar e
continuar» com o campo vazio, seguem sem ela —; e por fim mostra um guia dos
primeiros passos sobre as telas de verdade, que se pula em qualquer passo,
aparece uma vez por estação e se abre de novo em Configurações, na seção
Geral («Ver o guia de novo»). As duas telas têm no canto o seletor de idioma
e o de tema, e sem escolha o tema abre escuro. A pasta favorita é onde os
seletores de pasta abrem, e a estrela de cada seletor a põe no campo; ela
não muda a pasta que o vigia varre. <b>O primeiro uso não pergunta o sistema
de planejamento</b>: com a chave <code>TPS_DESTINO</code> do arquivo de
configuração vazia, ele grava nela o valor de «Eclipse / Monaco», e a
estação que já tinha escolhido continua com a escolha. A troca — dois
botões, «Eclipse / Monaco» e «Xio / Focal» — mora em Configurações, na seção
Geral («Ajuste de contornos em anel»), e decide o desenho do furo no
RTSTRUCT:</p>
<ul>
 <li><b>Em todo sistema</b>, o texto que o programa escreve no RTSTRUCT — o
 nome e a descrição de cada estrutura, os rótulos — sai em ASCII, sem
 acento; a identificação do paciente sai igual à da imagem, porque é por ela
 que o sistema associa o arquivo à série. O arquivo é gravado em
 <i>Implicit VR Little Endian</i>, a sintaxe padrão do DICOM, e declara o
 repertório de caracteres só quando a identificação do paciente tem acento:
 então, o mesmo da TC, com os mesmos bytes do nome. O furo de um contorno (o
 de dentro de um anel) sai meio pixel para dentro, e não para fora. E nenhum
 contorno sai com área nula, com vértice repetido ou cruzando a si mesmo: o
 de área nula — a parte de um pixel de largura de uma estrutura fina — é
 refeito pelo contorno dos pixels, e não descartado; o que a suavização ou a
 redução de pontos fez cruzar volta ao de antes delas; e o log diz quantos
 de cada. Numa série de corte não axial — a RM sagital ou coronal, a axial
 oblíqua —, esse acabamento é feito no plano dos cortes da própria série, e
 cada contorno sai no plano de um corte dela; o RTSTRUCT de uma série axial
 sai como antes. Que o sistema de planejamento leia contorno fora do plano
 axial depende dele, e se confere na importação. O que o DicomBridge
 exporta — as séries DICOM e as imagens que ele converte — sai também em
 <i>Implicit VR Little Endian</i>, nos dois sistemas.</li>
 <li><b>Com «Eclipse / Monaco»</b> (<code>TPS_DESTINO=eclipse</code>), o furo
 sai como um contorno separado, dentro do de fora.</li>
 <li><b>Com «Xio / Focal»</b> — versões anteriores, ou outros que precisem
 de linha divisória nos anéis — (<code>TPS_DESTINO=monaco</code>), o furo de cada
 contorno é ligado à borda externa por uma linha divisória — sem ela, a pele
 e a parede torácica chegariam preenchidas.</li>
 <li><b>Sem escolha</b>, o RTSTRUCT sai como em «Eclipse / Monaco», e o log
 de cada gravação avisa.</li>
</ul>
<p><b>Fechar o navegador encerra o programa — depois da série em curso.</b>
Aberto pelo atalho, o programa se encerra quando a última aba dele se fecha e
nenhuma outra responde em 15 segundos — ou, se o navegador fechar sem avisar,
depois de três minutos sem sinal de nenhuma tela. Isso não interrompe a série
em curso: o programa não começa outra série, nem do vigia nem do «Rodar
agora», termina a que roda e só então se encerra; com o turno da noite
aberto, segue o turno até o fim. Com o turno da noite agendado na fila e o
lote do «Rodar agora» andando até ele, o fechar pelo X não segura a fila: o
lote segue, o turno abre, e o programa se encerra no fim do turno; lote
pausado ou parado não segura, porque o turno não abriria sozinho. Sem nada
rodando, ele se encerra naqueles 15
segundos; e, se uma tela volta a responder antes, o encerramento é cancelado,
e o lote que parou entre séries por causa do fechar volta a andar sozinho.
O «Fechar tudo» do botão é o que encerra na hora: a série em curso é
interrompida, e nenhum contorno pela metade é gravado. Na próxima abertura, a
trava que uma série desta estação deixou, de um processo que não existe mais
— ou cujo número um processo criado depois do último sinal da trava
reaproveitou, e esse não é encerrado —,
é solta, e a série volta para a fila do vigia, com uma linha no cartão; o
cartão de uma série posta à mão na fila volta como falha, sem trava, para ir
de novo à fila. Uma aba que o navegador apenas pôs para dormir não encerra
nada. Abrir o
programa com outra sessão dele processando uma série, ou com o turno da
noite aberto ou agendado na fila, pergunta, no navegador, antes de
encerrá-la; uma sessão parada e sem turno, ou que não responde, é encerrada
sem pergunta. E o atualizador e o instalador do pacote, antes de trocar o
código, encerram o programa aberto daquela pasta — só o Python dela —: pedem
o «Fechar tudo» e, se ele não sair, o encerram à força; se nem assim,
perguntam se tentam de novo, e nada é copiado por cima do programa
aberto. O «Instalar / Atualizar app nesta máquina», ao abrir numa estação
com o programa instalado, fecha as janelas do navegador do programa — só as
do perfil próprio dele (<code>radai_janela</code>); o navegador da pessoa
nunca é tocado — e o encerra; se o programa estiver processando — uma série,
ou o turno da noite aberto ou agendado —, ele pergunta antes, e a série
interrompida volta para a fila, sem contar como falha.</p>

<h2>1.6 · As tags próprias e os protocolos próprios</h2>
<p>Em Configurações, na seção Estruturas e Protocolos, a estação pode dar
nome próprio às estruturas do entregue e montar protocolos próprios. Os dois
valem só para o entregue — o do AUTO e do PERSONALIZADO e o do FAST —: o
completo sai sempre com os nomes padrão, e os outros apps da suíte leem o
completo ou o nome padrão.</p>
<ul>
 <li><b>As tags próprias.</b> Uma chave «Padrão / Tags próprias»: em
 «Padrão», o entregue sai com os nomes padrão, com <code>_ai</code>, e os
 nomes próprios ficam guardados sem valer. Com «Tags próprias», cada
 estrutura do entregue que tem nome próprio sai com ele — que pode não ter o
 sufixo de procedência —, e toda estrutura do entregue guarda na descrição
 (<code>ROIDescription</code>) o nome padrão e «sugestao IA nao aprovada»,
 com o algoritmo de geração <code>AUTOMATIC</code> e o
 <code>UNAPPROVED</code> de sempre. O nome próprio tem até 16 caracteres,
 só letras sem acento, números e sinais do teclado (ASCII), sem espaço no
 começo nem no fim e sem contrabarra; não repete o nome de outra estrutura
 do entregue nem de uma união; e não pode ser nome de alvo (começar por GTV,
 CTV, ITV ou PTV) nem de contorno externo (BODY, External). A tela recusa o
 nome com o motivo na linha, e o programa confere de novo ao gravar o
 RTSTRUCT: o nome recusado sai como o padrão, e o log diz.</li>
 <li><b>Os protocolos próprios.</b> Cada protocolo vale para uma modalidade
 (TC ou RM) e escolhe as estruturas do entregue entre as que alimentam o
 completo, com uniões — só por soma, cada uma com um nome que segue as regras
 do nome próprio. Ele aparece no PERSONALIZADO do «Rodar agora», numa chave
 com uma lista, só quando há protocolo da modalidade da série. Ligado, ele
 desliga os protocolos RT e a seleção livre; as tarefas que as estruturas
 dele pedem ficam ligadas e travadas; e o entregue daquela série é a seleção
 dele, com a regra de região de sempre (o osso da pelve, por exemplo, só com
 a pelve identificada). O vigia não usa protocolo próprio — roda sempre o
 AUTO —, e o FAST também não. <b>Um protocolo próprio pode incluir
 achado</b> (seção 4.1): então a declaração é pedida a cada envio à fila, o
 log anuncia com a palavra <b data-radai-t="1">ACHADO</b>, e o resultado sai no arquivo próprio
 do achado, nunca no entregue; sem a declaração, a tarefa de achado não
 roda.</li>
</ul>
<p>Os nomes próprios e os protocolos moram ao lado do arquivo de
configuração (a Política de Privacidade, seção 3, diz onde) e viajam no
exportar das configurações (seção 4.3).</p>

<h2>2 · O que ele não é</h2>
<ul>
 <li>Não é sistema de planejamento nem substitui um.</li>
 <li>Não emite laudo, não faz diagnóstico e não recomenda conduta.</li>
 <li>Não aprova estrutura para tratamento. Nenhuma tela dele tem essa ação.</li>
 <li>Não treina modelo. <b>Nenhum modelo aqui é nosso</b>, e nenhum foi
 treinado por nós em caso de paciente. O que é nosso é o que acontece
 <i>depois</i> que o modelo de terceiro devolveu a máscara. Esta versão não
 grava pares de imagem e máscara para treino (a Política de Privacidade diz o
 que uma versão anterior pode ter deixado na estação), e treinar modelo é
 trabalho fora deste programa.</li>
 <li>Não procura achado <b>por conta própria</b>: de fábrica, nenhuma tarefa de
 achado roda. Isto descreve o que vem <b>ligado</b>, e não um limite do que o
 programa sabe fazer — a diferença está em 4.1.</li>
</ul>

<p><b>O que ele é, então.</b> Um <b>pós-processamento geométrico</b> da saída de
modelos de terceiros e um <b>comparador</b> entre eles, com finalidade de
<b>ensino e pesquisa</b>. O pós-processamento aplica regras sobre o que o
modelo já entregou: parte delas vem de diretriz publicada, e a tela de
Procedência diz qual; parte são parâmetros nossos, declarados como nossos.
Nenhuma é um modelo treinado aqui. O código é aberto, sob a licença
Apache-2.0, e quem o usa é convidado a copiá-lo e modificá-lo; para uso
clínico, cabe a quem instala e modifica validá-lo e buscar aprovação na agência
sanitária do país dele.</p>

<p><b>E o que ele faz com detecção.</b> Os modelos de terceiros que ele executa
trazem tarefas e classes que <b>procuram achado</b> — nódulo pulmonar,
lesão hepática, tumor. Elas <b>existem, não vêm ligadas, e ligar uma é ato de
quem opera</b>. O que muda para quem liga está em
<a href="#ato">4.1 · O que exige um ato de quem opera</a>, e vale ler antes.</p>

<h2>2.1 · As três garantias são técnicas, não são promessas</h2>
<p>Promessa é o que alguém contraria. Estas três não dependem de vontade de
ninguém — elas são propriedades do que o programa produz, e qualquer pessoa
pode conferi-las abrindo os arquivos:</p>
<ul>
 <li><b>Nenhum contorno externo é declarado.</b> Nenhum dos conjuntos contém
 <code>BODY</code>, <code>External</code> ou equivalente, e nenhuma estrutura sai
 marcada como <code>EXTERNAL</code>. A recusa fica dentro da função que escreve
 o RTSTRUCT, não numa tela. A casca <code>Skin</code> contém a superfície
 pele–ar, porque é isso que uma pele é — ela não é um contorno externo
 revisado, e não vira um por estar aqui.</li>
 <li><b>Séries separadas, nunca a original.</b> Cada conjunto sai como uma
 série própria, ao lado. A tomografia que está no sistema de planejamento não
 é tocada. Os RTSTRUCT gravados ao lado dela e a subpasta <code>_RadAI</code>
 ficam depois de desinstalar o programa — a
 <a href="/politica-privacidade">Política de Privacidade</a> diz o que fica e
 onde.</li>
 <li><b>Nenhuma estrutura sai aprovada.</b> <code>UNAPPROVED</code> no arquivo e,
 em cada nome, o sufixo de procedência — ou, com as tags próprias, o nome
 padrão e «sugestao IA nao aprovada» na descrição da estrutura. Os dois
 conjuntos entregues — o do AUTO e do PERSONALIZADO e o do FAST — se chamam,
 no próprio arquivo, <i>sugestão não aprovada</i>; os outros levam o rótulo
 <code>RadAI_</code> com o nome ou o código deles (<code>RadAI_FULL</code>,
 <code>RadAI_TS</code>, <code>RadAI_NV</code>…) e dizem que não são o
 entregue. Não existe caminho no
 programa que produza estrutura aprovada.</li>
</ul>
<p>A quarta é de outra natureza e vale dizer junto: <b>as métricas medem
divergência entre modelos, não acurácia.</b> Sem um contorno aprovado como
referência não existe medida de acerto, e chamar a diferença de erro seria
inventar um número.</p>

<h2>3 · Uso responsável</h2>
<p>Ao usar este programa, você reconhece que:</p>
<ul>
 <li>Toda estrutura gerada é <b>sugestão não aprovada</b>
 (<code>ApprovalStatus = UNAPPROVED</code>), identificada por sufixo de
 procedência — ou, com as tags próprias, pela descrição dela.</li>
 <li>Qualquer contorno usado em tratamento deve ser <b>revisado e aprovado por
 profissional habilitado</b>, no sistema de planejamento, sob responsabilidade
 dele.</li>
 <li>O modelo <b>contorna com confiança estruturas que não existem</b> na imagem
 se a biblioteca pedida for de outra região anatômica, e produz contornos não
 confiáveis quando a informação não está na imagem — por exemplo, estruturas
 vasculares em tomografia sem contraste.</li>
 <li>As métricas comparativas medem <b>divergência entre modelos</b>, não
 acurácia. Sem um contorno aprovado como referência, não há medida de acerto.</li>
</ul>

<h2>4 · Modelos de terceiros e suas licenças</h2>
<p>Este programa executa modelos de terceiros, cada um com licença própria, que
você é responsável por respeitar. <b>Quem reconhece o órgão é o modelo de
terceiro</b> — o que construímos é a camada que o torna utilizável numa
estação de radioterapia.</p>
<ul>
 <li><b>TotalSegmentator</b> — Apache-2.0 no código, e os pesos do
 TotalSegmentator sob a mesma licença. É ele que faz o auto-contorno do fluxo
 principal. Licença permissiva: não restringe o uso. Ele roda com o
 <b>recorte no corpo</b> (a opção <code>body_seg</code> da biblioteca): um
 modelo grosseiro, a 6 mm, localiza o corpo, e a tarefa roda só dentro dele,
 na resolução dela — o ar em volta do paciente não é processado. Ele vem
 ligado de fábrica, pela chave <code>RECORTE_NO_CORPO</code> do arquivo de
 configuração. Nas tarefas de RM, e nas que já recortam por conta própria, a
 biblioteca não usa esse recorte. A partir da versão 8.7, nos pacotes
 montados e também na instalação direta numa estação, o preparador tira dos
 checkpoints dos pesos dele o estado do otimizador,
 que só serve ao treino, depois de conferir o download: os pesos da rede
 ficam idênticos byte a byte, cada arquivo leva dentro um aviso de
 modificação, e o <code>NOTICE</code> declara a modificação, como a licença
 pede; o peso que já estava na estação não é reescrito.</li>
 <li><b>NV-Segment-CT (NVIDIA)</b> — código Apache-2.0, <b>pesos sob a NVIDIA
 Open Model License</b>, que <b>permite uso comercial</b>. O cartão do modelo
 diz que ele é para pesquisa e não para uso clínico, e essa frase é do autor
 do modelo, não da licença.</li>
 <li><b>CADS</b>, na variante <code>open</code> — código Apache-2.0, pesos sob
 <b>CC BY-SA 4.0</b>: uso comercial permitido, com <i>ShareAlike</i>. O
 ShareAlike alcança um <i>fine-tune</i> que você faça sobre esses pesos; não
 alcança o contorno que sai deles.</li>
 <li><b>MOOSE</b> — código Apache-2.0, pesos sob <b>CC BY 4.0</b>: uso
 comercial permitido, sem ShareAlike, e <b>exige atribuição</b> — ela está no
 <code>NOTICE</code> que viaja no pacote.</li>
 <li><b>Níveis linfonodais cervicais</b> (Weissmann et al., 2023) —
 <b>CC0-1.0</b>, domínio público. Os vinte níveis saem com os nomes do
 consenso de Grégoire (<code>Lvl_Ia</code> a <code>Lvl_VIII_R</code>; sufixo
 <code>_lnl</code> no arquivo deles e <code>_ai</code> no conjunto completo),
 pelo mapa entre o rótulo do modelo e o nível que os autores publicaram com
 os pesos. O mapa vale para aquela versão dos pesos, e o programa a confere
 antes de usar os nomes: com pesos de outra versão, os níveis voltam aos
 nomes neutros (<code>LNL01</code> a <code>LNL20</code>, e a união
 <code>LNL_Union</code>), e a descrição de cada um diz que o nível não foi
 atribuído. Cada nível sai com a sua cor, mais escura no lado direito, e com o
 tipo <code>CONTROL</code>: é compartimento anatômico, e não órgão nem CTV.
 Sai também a união dos níveis Ia a VIIb (<code>LNL_UNION</code>, sem o
 nível VIII). Um nível que cai do lado errado da linha média fica só na
 união, sem nome de lado.</li>
 <li><b>Buti et al.</b> — estruturas do encéfalo em TC (tronco
 encefálico, quiasma, cerebelo, ventrículos e linha média) — pesos sob
 <b>MIT</b>: uso comercial permitido.</li>
</ul>
<p>Nos pacotes montados a partir da versão 8.7 — e não na instalação direta
numa estação —, o preparador tira o estado do otimizador também dos
checkpoints dos níveis cervicais, do modelo do encéfalo em TC, do MOOSE e do
CADS, só dos que ele baixou naquela montagem. Cada arquivo enxuto é
conferido pela soma SHA-256 que o registro de modelos guarda para ele, e o
que não bate fica como veio da origem; os pesos da rede ficam idênticos byte
a byte, cada arquivo leva dentro o aviso da modificação, e o
<code>NOTICE</code> a declara, como pedem a CC BY e a CC BY-SA. A estação
aceita, de cada um, o arquivo da origem ou o enxuto.</p>
<p>O modelo do encéfalo em TC entra no conjunto completo e roda só em TC: no
AUTO quando o encéfalo está no campo, e no PERSONALIZADO pelos protocolos
Crânio e Cabeça e Pescoço avançado ou pela chave dele. O tronco encefálico e o
quiasma vão também ao entregue.</p>
<p>Os três motores de comparação — NV-Segment-CT, CADS e MOOSE — gravam cada
um o seu arquivo, e <b>só quando pedidos</b>: na comparação de modelos do
PERSONALIZADO do «Rodar agora», e só em TC. O vigia não os roda. Os níveis
cervicais rodam no AUTO — no vigia e no «Rodar agora» — quando o pescoço é
detectado (as vértebras cervicais C2, C3 e C4, com 5 cm³ cada, na base, e a
mandíbula no campo, com 80 cm³ ou mais, medida pelo crânio da base, que a
contém, só na faixa do topo do C1 (sem ele, do topo do C2) ao fim do C4 — ou,
no lugar da mandíbula, o crânio acima do topo dessa faixa, com 50 cm³ ou
mais: a cabeça no campo; a TC de tórax que só sobe ao C1 não tem crânio
acima dele e fica fora, e o log da anatomia diz qual caminho confirmou), e
no PERSONALIZADO pelo protocolo Cabeça e Pescoço avançado ou pela chave
deles; o FAST não os roda. Além disso, só rodam em série de TC em que a
cabeça aparece. Quando rodam, entram no conjunto completo — e, deles, só a
união e as parótidas do nível VIII vão ao entregue (o quadro da seção 1.2)
—; o arquivo próprio deles só sai no PERSONALIZADO. A parótida do entregue
vem só do nível VIII — o nível VIII menos o esternocleidomastoideo —, e só
quando o lado dele se confirma e quando ela é plausível como a glândula
inteira: 0,5 cm³ ou mais, pelo menos metade do volume da do TotalSegmentator
e pelo menos 30% de sobreposição com ela. Quando não é — e sempre que os
níveis não rodam, inclusive no FAST —, o entregue sai sem parótida, e o log
diz por quê. A parótida do TotalSegmentator nunca vai ao entregue: fica só
no conjunto completo, sempre com o sufixo
<code>_ts</code> (<code>Parotid_L_ts</code> e <code>Parotid_R_ts</code>),
para comparação — com o pós-processamento do completo, e não a crua.</p>

<div class="cx destaque">
<p><b>Nenhum componente deste pacote é de uso não comercial.</b> Isso é
verificável e não é uma afirmação deste documento: o registro de modelos do
programa guarda, em cada entrada, o campo que diz o que a licença do peso
permite — é ele que a tela do aceite lê para montar a lista de pesos —, e
uma verificação automatizada <b>reprova</b> o registro em que um modelo tenha
nele valor diferente de «livre». Nenhuma rota nem tela do programa elege
modelo.</p>
</div>

<p>O programa não concede nem amplia direitos sobre esses modelos. O nome e o
endereço da licença de cada modelo e de cada biblioteca que o pacote fixa estão
no <code>NOTICE</code>, que viaja no pacote, e em
<a href="/creditos" data-radai-t="1">Créditos e licenças</a>; as dependências que essas
bibliotecas trazem consigo levam a licença delas no metadado do pacote
instalado; o texto íntegro da licença do NV-Segment-CT viaja também na pasta
do modelo.</p>

<div class="cx">
<p><b>O critério de distribuição.</b> No pacote entra apenas licença
permissiva ou de uso comercial permitido, para que quem baixe o código e
instale em outro serviço não herde restrição sem saber. Componente novo com
licença restrita entraria por esta mesma porta, e é aqui que ele teria de
aparecer antes de alguém instalar.</p>
</div>

<h2 id="ato">4.1 · O que exige um ato de quem opera</h2>
<p>Os modelos de terceiros que este programa executa trazem, além da anatomia,
tarefas e classes que <b>procuram achado</b>. Elas não são nossas, e não foram
escritas por nós:</p>
<ul>
 <li><b>No TotalSegmentator</b> — as tarefas de achado
 <code>lung_nodules</code>, <code>liver_lesions</code> e
 <code>liver_lesions_mr</code>. Ligar uma é
 rodar <b>outro modelo</b> do TotalSegmentator, e não ensinar o de anatomia a
 detectar.</li>
 <li><b>No NV-Segment-CT</b> — classes como <i>lung tumor</i>, <i>hepatic
 tumor</i>, <i>pancreatic tumor</i>, <i>colon cancer primaries</i>, <i>bone
 lesion</i> e os dois cistos renais. A rotina de entrega pede <b>só
 anatomia</b>: as classes de achado ficam fora do pedido, e nenhuma opção de
 tela ou do arquivo de configuração as acrescenta.</li>
</ul>

<p><b>Nada disso vem ligado.</b> O pacote traz as tarefas de achado e sai de
fábrica sem nenhuma delas ligada, e isso não é uma afirmação de documento: são
<b>três lugares que têm de concordar</b> — a lista padrão de tarefas do
programa, a base que o vigia põe na frente de toda série (o arquivo de
configuração não escolhe tarefa), e a tabela por região que o vigia consulta,
quando ainda não há região nenhuma. Se os três divergirem, ou se a tabela, em
qualquer região, o que um protocolo RT do PERSONALIZADO arrasta, cada chave
que nasce ligada nele, ou a lista do FAST trouxer uma
tarefa de achado, a verificação do projeto reprova — e a função que monta cada
uma dessas listas recusa montá-la.</p>

<p><b>O que o vigia roda, sozinho, durante a noite</b> — e o AUTO do «Rodar
agora», que faz a mesma conta da anatomia. Primeiro a base de
anatomia (a do TotalSegmentator para TC, ou a de RM). Depois ele olha a
anatomia que a própria base desenhou: se a série tem pescoço (pelas vértebras
cervicais C2, C3 e C4 e pela mandíbula na faixa do C1 ao C4, ou pelo crânio
acima do C1), é cabeça e pescoço; se tem
encéfalo sem o pescoço, é
crânio; e há o tórax (pulmão, clavícula e escápula), o abdome e a pelve. Na
TC, ele acrescenta as tarefas de anatomia de cada região — as que completam o
conjunto completo e o entregue —, a cavidade do tronco quando o coração do
modelo tem 100 cm³ ou mais sem o tórax identificado, e <b>nenhuma de
achado</b>. No tórax, uma dessas tarefas é a do derrame pleural e
pericárdico, que é anatomia (abaixo). O texto do exame não acrescenta tarefa, e
o arquivo de configuração também não: o vigia roda sempre o AUTO, e a única
escolha que ele soma à da anatomia é a sua, na fila — as tarefas de cabeça e
pescoço, quando você marca essa região para a série; delas, a dos músculos de
cabeça e pescoço, com os constritores da faringe, só roda com o pescoço
confirmado pela anatomia, e o log diz quando ela fica de fora. Tarefa avulsa, achado e
comparação de modelos se pedem série a série, no PERSONALIZADO do «Rodar
agora».</p>

<p><b>Ligar é um ato, e os três que existem estão no PERSONALIZADO do «Rodar
agora».</b> O primeiro é ligar a chave da tarefa no PERSONALIZADO — ela nasce
desligada, com o selo ACHADO, e nenhum protocolo RT a liga. Ligada assim, o
log anuncia com a palavra <b data-radai-t="1">ACHADO</b>, o que ela devolve sai num arquivo próprio
(rótulo <code>RadAI_</code> e o código dela) e, cru, também no conjunto do
TotalSegmentator (<code>RadAI_TS</code>) quando ele é pedido, como toda saída
do modelo — nunca no
conjunto completo nem no entregue —, e o registro do caso guarda quais rodaram, para que a resposta a "o que estava ligado naquela
série?" não dependa da memória de ninguém. O segundo é escolher um
protocolo próprio da estação que inclua achado (seção 1.6): a declaração é
pedida a cada envio à fila, e o que a tarefa devolve segue a regra da chave.
O terceiro é pedir um protocolo de
estudo das Reconstruções 3D: o Anatomia Geral roda todas as tarefas do
catálogo da modalidade, as de achado inclusive, e, na TC, pede também os
níveis cervicais; o Anatomia Torácica roda as do tórax, os nódulos pulmonares
inclusive. O log anuncia com a mesma palavra,
e o marcador de conclusão da série guarda os protocolos pedidos; mas o estudo
não grava RTSTRUCT nenhum: o que ele roda vai a um mapa de rótulos, na
subpasta <code>_RadAI</code> da série (a Política de Privacidade diz o que o
mapa leva), e uma tarefa que só ele pediu não chega ao entregue nem a arquivo
de estudo nenhum. O vigia não liga tarefa de achado, e, fora desses
protocolos de estudo, não há botão que ligue tudo.</p>

<p><b>Os cistos renais são a exceção, e ela é da anatomia.</b> O modelo de
anatomia do TotalSegmentator, que roda de fábrica, desenha os cistos renais
(<code>Kidney_Cyst_L</code> e <code>Kidney_Cyst_R</code>) com o rótulo dele.
Eles saem como estrutura própria, ao lado do rim, para que o rim não conte o
volume do cisto como parênquima: no conjunto completo e no entregue o rim é o
rim sem o cisto, e o cisto está ao lado. <b>Desenhar não é afirmar:</b> o
contorno diz onde o modelo viu um cisto, e não diz o que a lesão é — cisto
contra massa sólida é pergunta diagnóstica, e a resposta não está aqui.</p>

<p><b>O derrame pleural e o pericárdico também são da anatomia.</b> Por
decisão do autor, a tarefa do derrame do TotalSegmentator
(<code>pleural_pericard_effusion</code>) é anatomia do tórax, e não achado:
ela roda no FAST e no AUTO quando a anatomia identifica o tórax, nasce ligada
no PERSONALIZADO da TC, e o derrame que ela desenha sai só no conjunto
completo. O derrame pleural sai partido por lado — cada
voxel com o pulmão mais próximo naquele corte — e é descontado dos pulmões,
para o pulmão não contar o líquido como parênquima; o pericárdico entra no
coração de radioterapia (<code>Heart_ai</code>), e a descrição dele diz
quanto. No entregue e no entregue do FAST, então, o derrame não sai como
estrutura própria: os pulmões saem sem o pleural, e o coração leva o
pericárdico dentro. O arquivo próprio que ela gravava,
como tarefa de achado, saiu. Também aqui, desenhar não é afirmar: o contorno
diz onde o modelo viu líquido, e não diz o que ele é.</p>

<div class="cx aviso">
<p><b>O que muda para quem liga.</b> A RDC 751/2022 considera que o dispositivo
permite diagnóstico direto quando fornece <b>informação decisiva</b> para ele — e
apontar "aqui há um nódulo" é informação decisiva. Num serviço brasileiro que
dependa da isenção do <b>art. 5º da RDC 657/2022</b>, ligar qualquer uma dessas
tarefas muda a classe do <b>aplicativo inteiro</b>, e não só daquele módulo.</p>
<p><b>Em outra jurisdição a pergunta é outra, e a resposta é de lá.</b> Este
documento não responde por FDA, MDR ou por qualquer outra autoridade: quem
instala é quem avalia, valida e registra onde opera.</p>
</div>

<p><b>Classificar não é o mesmo que detectar, e o degrau é mais alto.</b> Uma
probabilidade de malignidade não é informação decisiva para o diagnóstico: <b>é
o diagnóstico</b>, e isso vale mesmo quando a posição foi indicada por você.
Medir tamanho, distância e densidade é quantificar; dizer o que aquilo <b>é</b>,
não — a diferença continua, e atravessá-la é decisão de quem liga. Hoje <b>não
existe classificador neste programa</b>, e isso é <b>ausência</b>, não trava. Se
um dia for construído, entra pela mesma porta: desligado de fábrica, anunciado no
log, registrado no caso.</p>

<h3>De quem é a fronteira</h3>
<p>Numa <b>instalação in-house brasileira</b>, sob a isenção do art. 5º da
RDC 657/2022, a decisão de classe seria do próprio serviço, e uma única função
de achado ligada a mudaria. Enquanto o projeto foi só isso, o código não
executava detecção nenhuma.</p>
<p>O produto é <b>código aberto</b>, que cada serviço adapta, valida e registra
na jurisdição dele. <b>A fronteira não desapareceu: ela é de quem liga</b> — e
é por isso que ela está escrita aqui. Ler a permissão sem este parágrafo seria
entender que não há fronteira nenhuma.</p>

<p><b>E a literatura, como contexto.</b> O artigo do TotalSegmentator trata
detecção como <b>modelo separado</b>, nunca como função da segmentação; e a
política de máscara do treino <b>exclui a anormalidade de dentro do órgão</b>,
de modo que o modelo de anatomia não é treinado para localizar achado. É o que
quem registra o software precisa saber sobre o que <b>cada</b> modelo faz, para
não atribuir a um a capacidade do outro.</p>

<h2 id="bolus">4.2 · O 3D Printed Bolus exporta arquivos, e só por ato seu</h2>
<p>É o único módulo da suíte que entrega um arquivo de geometria: a partir de
uma TC diagnóstica, ele desenha um bólus sobre a pele, dentro de uma caixa que
você fecha — uma camada de espessura escolhida em milímetros inteiros, de 1 a
30, ou o bloco que preenche a caixa até a pele — e o entrega como <b>STL para
impressão 3D</b>. Se você pedir, ele entrega também um <b data-radai-t="1">molde</b>: uma casca
oca de 1 a 4 mm cujo interior é o bólus, com uma abertura — a face externa ou
uma das quatro laterais — por onde ele se preenche com cera, num segundo STL,
pelo mesmo ato. Não roda modelo nenhum: a pele sai do limiar de Hounsfield,
e a superfície é geometria.</p>
<div class="cx aviso">
<p><b>Não é para uso clínico.</b> A densidade do objeto impresso varia com o
filamento, e a <b>dosimetria do material é obrigatória</b> para avaliar a
atenuação antes de qualquer uso. O plano não usa o arquivo: ele usa a TC
feita com o bólus impresso posto no paciente.</p>
</div>
<ul>
 <li><b>Cada exportação é um ato declarado</b>, e a declaração não fica
 lembrada de uma exportação para a outra: sem marcar, a cada vez, que o STL é
 um rascunho sujeito a revisão física e médica, que não é para uso clínico e
 que a atenuação do material será medida antes de qualquer uso, o arquivo não
 sai — e a recusa é do servidor, e não só da tela.</li>
 <li>Cada ato é registrado, sem identificação do paciente, em
 <code>radai_bolus_atos.log</code>, no acervo da estação, antes de o arquivo
 sair; sem conseguir registrar, o arquivo não sai.</li>
 <li><b>Não há RTSTRUCT de bólus.</b> Estrutura de bólus é de uso dosimétrico
 direto — a mesma família do contorno externo, que nenhum conjunto
 declara.</li>
 <li>A espessura é <b>medida</b> na malha (mínima, mediana e máxima), e não
 prometida. O arquivo diz no cabeçalho que é rascunho não aprovado
 (<code>DRAFT UNAPPROVED</code>).</li>
 <li>A face interna do bólus é a superfície da pele do paciente, e o interior
 do molde é o bólus: num bólus de cabeça ou de face, os dois arquivos são uma
 <b>biometria</b> — a
 <a href="/politica-privacidade">Política de Privacidade</a> diz o que eles
 levam e para onde vão.</li>
</ul>
<h3>O aplicador de superfície para braquiterapia</h3>
<p>O mesmo módulo desenha também um <b>aplicador de superfície para
braquiterapia</b>: um corpo impresso sobre a pele, de espessura escolhida, com
canais paralelos que acompanham a pele a uma distância fixa e guiam os
cateteres. A fonte não passa pelo aplicador: ela corre dentro do cateter. Só
aplicador de superfície — nem intersticial, nem intracavitário. Cada
parâmetro vem com um padrão tirado da literatura, e a
<a href="/bibliografia">bibliografia</a> diz de onde.</p>
<div class="cx aviso">
<p><b>Um aplicador é acessório de tratamento, e pesa mais que o bólus.</b> Um
canal mal desenhado pode prender o cateter ou deslocar a posição de parada da
fonte. Por isso o programa não gera o que sabidamente danifica a
braquiterapia — uma curva de canal abaixo do piso do afterloader e do cateter
escolhidos, canais que se cruzam, canal mais estreito que o cateter —, e
alerta no resto: a curva entre o piso e o raio padrão de 35 mm (ou o maior
que o físico escolher), a folga menor
que 0,6 mm entre o canal e o cateter, o canal de fundo cego. O raio padrão
começa em 35 mm e é um campo do formulário que só sobe: o físico pode subi-lo,
e a curva amarela, com as quatro exigências e o segundo ato, vale até ele; o
campo não desce abaixo de 35 mm — o servidor recusa —, e a curva abaixo de
35 mm é sempre amarela. Abaixo do piso do afterloader e do cateter, o programa
não gera. Nada nele sai
aprovado, e nada nele é para uso clínico sem a segunda TC com o aplicador
posto e o plano novo feito sobre ela.</p>
</div>
<ul>
 <li><b>A exportação é um ato declarado, a cada vez:</b> sem marcar que o
 aplicador é um rascunho sujeito a revisão física e médica, que nada nele está
 aprovado, e que antes de qualquer uso haverá segunda TC com o aplicador e
 plano novo, teste de passagem com o cabo de checagem em cada canal,
 pré-plano rodado no afterloader e dosimetria no comissionamento, o arquivo
 não sai. Com a curva amarela há um <b>segundo ato</b>: declarar que as
 posições de parada no trecho curvo serão conferidas por radiografia, que
 nenhuma parada ativa ficará dentro da curva e que as instruções de uso do
 cateter e do afterloader serão conferidas. A recusa é do servidor, e não só
 da tela.</li>
 <li>Sai um <code>.zip</code> com o STL e uma <b>ficha</b> em texto: todos os
 parâmetros, o que foi medido de volta na malha (o raio mínimo de cada canal,
 a distância à pele, o diâmetro), os alertas e os avisos que não somem. A
 ficha nomeia a <b>face de entrada do cateter</b>, escolhida na tela nos dois
 trajetos (aberto e cego), e conta dela todas as distâncias ao longo do
 canal — inclusive o início e o fim de cada trecho de curva amarela de cada
 canal, arredondados para fora. Nenhum
 dos dois leva nome, registro, data de exame ou UID, e o STL diz no cabeçalho
 que é rascunho não aprovado.</li>
 <li><b>Quando o canal não cabe, o programa não gera, e diz por quê.</b>
 Sem nenhum canal na caixa, a tela diz a colocação (e se foi o programa que
 a escolheu), a direção dos canais, o melhor canal — o de menos trajeto sem
 pele; no empate, o mais central —, quanto do trajeto dele tem pele e as
 causas, separadas — falta pele sob o trajeto (e de que lado), a pele perto
 demais do topo da caixa, ou um objeto acima da pele —, com a proposta de
 cada uma. Um canal que cai no meio, com canais aceitos dos dois lados,
 também impede a geração: o centro da área ficaria sem cateter, e isso é
 risco de subcobertura; o canal que cai na borda continua como aviso.
 Quando a caixa não dá nenhum canal útil — nenhum canal, ou um caído no
 meio —, a recusa propõe uma caixa aparada, conferida traçando de novo os
 canais nela, com o botão «Usar a caixa sugerida»: a caixa só muda com esse
 clique, e o aplicador só sai quando você gera de novo. Com a direção dos
 canais automática, o programa traça os canais nas duas direções
 perpendiculares à colocação e fica com a que acomoda mais canais — no
 empate, a de partida —, e o aviso e a ficha dizem qual escolheu. No canal de
 fundo cego, a pele é exigida só até o fundo do canal. A
 distância à pele e a curva do canal — e o raio mínimo que a ficha diz —
 seguem a borda do volume parcial dos voxels do cruzamento de −300 HU, que
 não oscila com a posição do voxel; só a face interna da peça segue o
 cruzamento do limiar.</li>
 <li>Cada exportação é registrada em <code>radai_bolus_atos.log</code>, no
 acervo, antes de o arquivo sair; sem conseguir registrar, ele não sai.</li>
 <li>A face interna do aplicador é a superfície da pele do paciente: num
 aplicador de cabeça ou de face, o arquivo é uma <b>biometria</b>.</li>
</ul>

<h2 id="estacao">4.3 · O que o programa faz na estação</h2>
<p>Além de segmentar, o programa age sobre a estação em que roda, e diz no
log o que fez. <b>Ele não fecha programa nenhum e não para nem religa
serviço do Windows</b>, nem mostra alerta para otimizar a estação: as
medidas de memória e de disco continuam em
Configurações, em Diagnósticos e Registros, e otimizar a estação é trabalho
do kit dela. Numa estação que usou uma versão anterior, ele apaga no arranque
o arquivo em que o otimizador de antes anotava o que tinha fechado (a
Política de Privacidade, seção 3) e o registro de um turno da noite que
pausava serviços (<code>_overnight_servicos.json</code>, na pasta do
programa), com uma linha no log: o programa que foi fechado volta no
próximo logon, e o serviço que ficou parado, no próximo arranque do
Windows.</p>
<ul>
 <li><b data-radai-t="1">O Overnight Run</b> — o turno da noite — entra na fila como o último
 cartão, e abre quando a fila chega nele. A pasta dos
 exames, as modalidades e os dias para trás que você escolhe ao pedir o turno
 vão para o arquivo de configuração, e a estrela do seletor da pasta põe nele
 a pasta favorita. A folha tem dois botões: «Cancelar», que
 fecha sem mudar nada, e «Salvar e iniciar», que só se habilita depois que o
 programa confere que a pasta existe e se deixa ler — ao abrir a folha, ele só
 lê, sem gravar nada nela. Para saber se a pasta grava, o programa cria e
 apaga nela um arquivo de teste ao clicar em «Salvar e iniciar», antes de
 gravar a configuração, e a data da pasta muda; se ela não grava, nada é
 salvo, e a tela diz o motivo. Com
 a fila parada ou pausada, «Salvar e iniciar» a inicia, e o turno começa
 quando ela chegar no card. Trocar a pasta com o turno aberto vale a partir
 do turno seguinte: o que está aberto segue na pasta em que abriu, e o
 cartão do turno diz isso. Com o turno aberto, o programa pede ao Windows
 para não suspender a estação, mesmo com a fila vazia; o vigia lê a pasta e
 põe na fila a série sugerida de cada exame, no AUTO — a TC de simulação do
 exame ou, num exame sem TC, a RM do exame, pela mesma regra no vigia e no
 «Rodar agora» —; quando a fila esvazia depois de uma série pronta, ele varre
 de novo na hora, e, sem nada novo, no intervalo. O cartão do turno fica
 rodando até o turno ser encerrado; e o turno que volta à fila ao reabrir o
 programa, esperando, abre sozinho quando nada está na frente dele.</li>
 <li><b>A janela do programa.</b> Aberto pelo atalho, o programa abre o
 navegador em modo de aplicativo e em tela cheia, num perfil próprio
 (<code>radai_janela</code>); o F11 sai da tela cheia. Para pôr a janela em
 tela cheia e para o «Minimizar» da porta, o motor acha a janela do programa
 pelo título: a janela em modo de aplicativo, cujo título termina na ficha
 que a tela põe nele, é aceita sem ler processo nenhum, e só quando o título
 não basta ele confere pela linha de comando do processo do navegador que a
 janela é do perfil próprio dele. Nenhuma janela de abas do navegador é
 tocada, e a janela guardada se reconfere pelo processo dono e pela classe
 dela. O motor manda o F11 uma vez por janela, e só se ela ainda não cobre o
 monitor inteiro — antes, a traz para a frente —; quem saiu da tela cheia
 pelo F11 não volta a ser posto nela. A pedido, ele a minimiza ou a
 restaura. Uma linha no log do vigia diz por qual dos dois caminhos a janela
 foi achada, sem o título nem a ficha; fora ela, nada disso é gravado em
 disco.</li>
 <li><b>A atualização com um clique.</b> O «Atualizar agora» — no aviso de
 versão nova da porta e no cartão «Atualizar o programa» de Configurações —
 baixa o instalador da release, confere a soma SHA-256 que a release publica
 e, se só o código muda, fecha o programa, roda o atualizador numa janela do
 Windows, refaz os atalhos e reabre o programa, com a sua configuração. Com
 a série do vigia, o lote do «Rodar agora» ou o turno da noite em andamento,
 ele espera ou pergunta antes; e, quando a versão nova precisa de um pacote
 novo de modelos, a tela diz o tamanho e o tempo estimado e pede uma segunda
 confirmação antes de abrir o preparador da versão nova. A Política de
 Privacidade (seção 4) diz o que ele baixa e de onde.</li>
 <li><b>Levar as configurações para outra máquina.</b> Em Configurações, o
 «Exportar configurações» baixa um <code>.json</code> com o arquivo de
 configuração da estação — sem o que é desta máquina: a placa, o
 dispositivo, a porta e a marca do guia —, os nomes próprios e os protocolos
 próprios; não viajam a chave do pseudônimo, o acervo nem a fila. O
 «Importar configurações…» mostra, por seção, o que vai mudar, e grava só o
 que você marcou; o caminho que não existe nesta máquina é avisado e não é
 gravado.</li>
</ul>

<h2 id="video">4.4 · As Reconstruções 3D gravam o visor, e só por ato seu</h2>
<p>As Reconstruções 3D não exportam malha, estrutura nem medida. A única saída
delas é o <b>vídeo do visor</b> — MP4 ou WebM, gravado pelo navegador —, e só
por um ato declarado a cada gravação: sem marcar que o vídeo é dado de
paciente, o botão não grava, e a marca se desfaz quando a gravação termina.
Cada ato é registrado, sem identificação do paciente, em
<code>radai_recon3d_atos.log</code>, no acervo da estação, antes de a
gravação começar; sem conseguir registrar, ela não começa. <b>O vídeo de uma
série com a cabeça no campo pode mostrar o rosto</b>: é uma biometria, e vai
para a pasta de downloads do navegador — a
<a href="/politica-privacidade">Política de Privacidade</a> diz o que isso
implica.</p>
<p>A angiotomografia sintética das Reconstruções 3D (o «Vascular») tira o
osso da projeção pela segmentação que o ContourLab gravou para a série — o
RTSTRUCT dela, achado pelo UID, ou o mapa de rótulos —, lida só na memória
do programa, como no Nidus RT, com um voxel de margem. Numa série com HU e
sem segmentação com osso, ela usa um limiar de 700 HU, que leva junto o vaso
calcificado e o vaso a menos de 2 mm do osso, e a tela diz qual dos dois
valeu; sem HU, como na RM, e sem segmentação, o osso fica na projeção.</p>

<h2 id="bridge">4.5 · O DicomBridge entrega o exame como veio, e a imagem sem dono sai DESCONHECIDO</h2>
<p>O DicomBridge converte para o sistema de planejamento as séries que você
escolhe e entrega cada vez numa <b>pasta nova</b> (<code>DICOM_BRIDGE_</code>
com a data e a hora), sem <code>.zip</code>. A série DICOM vai com a
identificação do paciente como veio: o programa não pede nem muda a
identidade dela. A série com um corte de imagem incompleta no arquivo
(truncado, curto ou sem a imagem) não é convertida: a conversão a recusa
inteira, sem gravar nada, e a tela manda copiá-la ou exportá-la de novo da
origem.</p>
<p>A <b>imagem</b> — JPEG, PNG, TIFF ou BMP, arrastada para a área de envio
ou escolhida pelo «Importar imagem», o quarto botão do cartão de carregar,
que abre o explorador de arquivos do navegador — entra no mesmo pipeline,
sem segmentação, e é outra coisa: a imagem não diz de quem é. Cada série de imagem sai como
paciente <b>DESCONHECIDO</b>, com o seu próprio ID gerado
que diz de onde veio (<code>EXTERNO-</code> com a data, a hora e um sufixo
aleatório curto, que separa duas estações no mesmo segundo), e a pasta da
entrega leva um <code>LEIA-ME.txt</code> de uma linha mandando atribuí-la ao
paciente certo. A escala e a espessura dela vêm de você, e não do
equipamento: digitadas, ou a escala medida por você com dois cliques numa
distância conhecida da própria imagem. A ordem dos cortes é a dos arquivos,
e só você a inverte; a ordem trocada é um espelho que o registro com a TC não
desfaz, e por isso a tela só converte depois que você confere, na
reconstrução, a escala e a ordem dos cortes. Ela entra com referência
espacial própria, não alinhada à TC: o registro com a TC é ato seu, no
sistema de planejamento.</p>
<div class="cx aviso">
<p><b>Atribuir a série ao paciente certo é ato de quem a importa no sistema de
planejamento.</b> Uma série DESCONHECIDO pode virar um paciente novo ou ser
associada à pessoa errada, e o programa não tem como saber de quem é a
imagem.</p>
</div>

<h2 id="nidus">4.6 · O Nidus RT projeta a TC, e o 3D da caixa fica na estação</h2>
<p>O Nidus RT projeta a TC num plano, como a imagem de um arco em C, para
desenhar a lápis sobre a projeção; ele não roda modelo. Os ângulos seguem a
convenção do arco em C, a do DICOM: LAO põe o detector do lado esquerdo do
paciente, e RAO do direito; CRA o inclina para a cabeça, e CAU para os pés.
Towne é CRA 30, e Caldwell, CAU 15. A sala que ele mostra é ilustrativa —
uma projeção paralela, sem ampliação, sem colisão e sem distância
fonte–detector —, e não simula um equipamento. Enquanto um ângulo é
arrastado, a projeção chega numa prévia em baixa resolução, e o lápis espera
a projeção cheia.</p>
<p><b>O 3D da caixa</b> mostra, em malhas, o que está dentro da caixa que você
desenhou: o vaso por limiar, o osso da segmentação do ContourLab e a pele.
<b>Numa série com a cabeça no campo, ele pode mostrar o rosto.</b> As malhas
ficam só na memória do programa — no máximo 24 MB, apagadas quando a série
fecha e depois de 10 minutos sem uso —, e nada do 3D da caixa se exporta.</p>

<h2>5 · Dados de paciente</h2>
<p>Você é responsável por ter base legal para tratar as imagens que aponta ao
programa e por seguir as normas da sua instituição. Os dados, depois de
segmentados, ficam na estação e na infraestrutura do serviço; o que sai, sai
por um ato seu. A <a href="/politica-privacidade">Política de Privacidade</a>
diz onde cada dado fica, cada conexão de rede e cada saída, com o que ela
leva.</p>

<h2>6 · Garantias e responsabilidade</h2>
<p>O software é fornecido <b>"como está"</b>, sem garantia de adequação a
finalidade específica. Não há garantia de que os contornos estejam corretos,
completos ou adequados a qualquer paciente.</p>
<p>Na máxima extensão permitida em lei, os autores não respondem por decisão
clínica, dano ao paciente, perda de dados ou prejuízo decorrente do uso deste
programa. <b>A responsabilidade clínica é de quem trata o paciente.</b></p>

<h2>7 · Mudanças</h2>
<p>Estes termos podem mudar entre versões. Versão nova pede aceite novamente:
o aceite guarda a versão e a impressão digital do texto aceito, e um texto
diferente do aceito pede aceite de novo.</p>

<h2>8 · Contato</h2>
<p>A página do projeto, <a href="https://radioterapia.ai">radioterapia.ai</a>;
uma vulnerabilidade, pelo relato privado do repositório do projeto no GitHub
(<a href="https://github.com/radioterapia-ai/local-suite/security">radioterapia-ai/local-suite</a>,
aba Security), nunca numa issue pública e nunca com dado de paciente.</p>
</div></body></html>"""


def montar(app):
    from fastapi import Request
    from fastapi.responses import HTMLResponse

    @app.get("/politica-privacidade", response_class=HTMLResponse)
    def _politica():
        return radai_menu.aplicar_leitura(POLITICA, "politica")

    @app.get("/termos", response_class=HTMLResponse)
    def _termos():
        return radai_menu.aplicar_leitura(TERMOS, "termos")

    @app.get("/aceite", response_class=HTMLResponse)
    def _aceite():
        return pagina_aceite()

    @app.get("/api/aceite")
    def _estado():
        try:
            impressao = impressao_dos_documentos()
        except Exception:
            impressao = u""
        return {"aceito": aceito(), "versao": VERSAO_DOCS, "data": DATA_DOCS,
                "impressao": impressao,
                "pontos": [{"chave": c, "titulo": t, "detalhe": d,
                            "sinal": sinal_do_ponto(c)}
                           for (c, t, d) in PONTOS],
                "fontes": fontes_de_terceiros(),
                "registro": aceite()}

    @app.post("/api/aceite")
    async def _registrar(request: Request):
        try:
            c = await request.json() or {}
            faltando = [p[0] for p in PONTOS
                        if p[0] not in (c.get("itens") or [])]
            if faltando:
                return {"erro": "faltam confirmar: %s" % ", ".join(faltando)}
            return await radai_web.no_threadpool(
                registrar_aceite, c.get("quem", ""), c.get("itens"))
        except Exception as e:
            return {"erro": "%s: %s" % (type(e).__name__, e)}


LIVRES = ("/aceite", "/termos", "/politica-privacidade", "/creditos",
          "/favicon.ico", "/radai-idiomas.js")

CSS_ACEITE = u"""
*{box-sizing:border-box}
body{margin:0;background:var(--bg-0,#060d1a);color:var(--text,#e6edf7);
 font-family:var(--font-display,Inter,system-ui,Arial)}
.ac{max-width:700px;margin:0 auto;padding:56px 24px 64px}
.ac-lang{position:absolute;top:14px;inset-inline-end:16px;z-index:20;
 display:flex;align-items:center;gap:8px}
.ac-lang .ui-seg>button{padding:6px 9px}
.ac-lang .ui-seg-rot{position:absolute;width:1px;height:1px;overflow:hidden;
 clip:rect(0 0 0 0);white-space:nowrap}
.ac .docs{display:flex;flex-wrap:wrap;gap:6px 18px;margin:10px 2px 0;
 font-size:12px}
.ac .docs a{color:var(--accent,#4DA3FF);text-decoration:none;
 border-bottom:1px solid transparent}
.ac .docs a:hover{border-bottom-color:currentColor}
.ac .docs a:focus-visible{outline:2px solid var(--accent,#4DA3FF);
 outline-offset:2px}
.ac .rot{font:400 10px/1 var(--font-mono,monospace);letter-spacing:.16em;
 text-transform:uppercase;color:var(--text-dim,#72829b)}
.ac h1{font:700 30px/1.2 var(--font-display);letter-spacing:-.02em;
 margin:14px 0 0}
.ac h1 b{color:var(--aviso,#E8A33D);font-weight:700}
.ac .pp{margin:14px 0 0;font-size:13.5px;line-height:1.65;
 color:var(--text-muted,#a3b1c6)}
.ac .fontes{margin:22px 0 0;padding:14px 16px;border-radius:var(--r-lg,8px);
 background:var(--panel,#0c1322);border:1px solid var(--line,#1e293b)}
.ac .fo-tit{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
 color:var(--text-dim,#72829b);margin:0 0 9px;
 font-family:var(--font-mono,monospace)}
.ac .fo{display:flex;gap:14px;align-items:baseline;padding:5px 0;
 border-top:1px solid var(--line,#1e293b);font-size:12px;line-height:1.5}
.ac .fo:first-of-type{border-top:0}
.ac .fo b{flex:0 0 auto;color:var(--text,#e6edf7);font-weight:600}
.ac .fo span{flex:1 1 0;min-width:0;color:var(--text-dim,#72829b);
 text-align:right}
@media (max-width:560px){.ac .fo{flex-direction:column;gap:2px}
 .ac .fo span{text-align:left}}
.ac .pt.nao .v{color:var(--perigo,#E96A5C)}
.ac .pt.atencao .v{color:var(--aviso,#E8A33D)}
.ac .pt{display:flex;gap:11px;align-items:flex-start}
.ac .pt .v{color:var(--success,#5BC57F);font-size:14px;line-height:1.5;
 flex:0 0 auto}
.ac .pt b{display:block;font-size:13px;font-weight:600;line-height:1.45;
 color:var(--text,#e6edf7)}
.ac .pt span{display:block;font-size:12px;line-height:1.55;margin-top:3px;
 color:var(--text-muted,#a3b1c6)}
.ac .aceitar{display:flex;gap:11px;align-items:flex-start;margin:26px 0 0;
 padding:15px 17px;border-radius:var(--r-lg,8px);background:var(--panel,#0c1322);
 border:1px solid var(--line-strong,#2a3a55);cursor:pointer}
.ac .aceitar input{margin:2px 0 0;width:17px;height:17px;flex:0 0 auto;
 accent-color:var(--accent,#4DA3FF)}
.ac .aceitar span{font-size:12.5px;line-height:1.6;color:var(--text-muted,#a3b1c6)}
.ac .aceitar a{color:var(--accent,#4DA3FF)}
.ac input[type=text]{width:100%;margin:12px 0 0;padding:9px 12px;
 border-radius:var(--r-md,6px);border:1px solid var(--line-strong,#2a3a55);
 background:var(--panel-2,#0f1729);color:var(--text,#e6edf7);font:inherit;
 font-size:13px}
.ac .bt{position:relative;overflow:hidden;margin:16px 0 0;display:inline-block;
 padding:11px 26px;border-radius:var(--r-md,6px);border:0;
 background:var(--ok,#12873F);color:var(--ok-txt,#fff);
 font:600 14px/1 var(--font-display);cursor:pointer;
 transition:transform .14s ease,box-shadow .14s ease}
.ac .bt:not([disabled]):hover{transform:translateY(-1px);
 box-shadow:0 6px 18px rgba(21,163,74,.32)}
.ac .bt:not([disabled]):active{transform:none;box-shadow:none}
.ac .bt:not([disabled])::after{content:"";position:absolute;top:0;left:-140%;
 width:70%;height:100%;
 background:linear-gradient(100deg,transparent,rgba(255,255,255,.34),transparent);
 animation:acBrilho 2.6s ease-in-out infinite}
@keyframes acBrilho{0%{left:-140%}55%{left:160%}100%{left:160%}}
.ac .bt[disabled]{opacity:.42;cursor:not-allowed}
@media (prefers-reduced-motion:reduce){
 .ac .bt:not([disabled])::after{animation:none;display:none}
 .ac .bt:not([disabled]):hover{transform:none}
}
.ac .msg{margin:12px 0 0;font-size:12.5px;min-height:18px}
.ac .mini{margin:14px 0 0;font-size:11.5px;line-height:1.6;
 color:var(--text-dim,#72829b)}
.ac .mudou{margin:18px 0 0;padding:11px 14px;border-radius:var(--r-lg,8px);
 background:rgba(225,178,59,.08);border:1px solid rgba(225,178,59,.3);
 font-size:12.5px;line-height:1.6;color:var(--text-muted,#a3b1c6)}
.ac .mudou b{color:var(--warn,#E1B23B)}
"""

PAGINA_ACEITE = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Antes de come&ccedil;ar &middot; Radioterapia.AI</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>@CSS@</style></head><body><div class="ac">

<div class="ac-lang"><span data-radai-idiomas></span></div>

<div class="rot" data-radai-frase>Bem-vindo</div>
<h1>Radioterapia.<b>AI</b> Local Suite</h1>

<p class="pp">Um <b>prot&oacute;tipo de estudo e
compara&ccedil;&atilde;o de modelos de contorno</b>, que roda inteiro na
sua esta&ccedil;&atilde;o. N&atilde;o &eacute; software m&eacute;dico
registrado, e nada que ele produz pode ser usado para tratar sem
revis&atilde;o e aprova&ccedil;&atilde;o m&eacute;dica no sistema de
planejamento.</p>

<div class="fontes" id="ac_fontes" style="display:none">
 <div class="fo-tit" data-radai-frase>Quem reconhece o
 &oacute;rg&atilde;o &mdash; e sob que licen&ccedil;a</div>
 <div id="ac_fo_linhas"></div>
</div>
<div class="mudou" id="ac_mudou" style="display:none"></div>

<div class="pontos" id="ac_pontos"></div>

<label class="aceitar">
 <input type="checkbox" id="ac_ok">
 <span data-radai-frase>Li e aceito os documentos abaixo &mdash; inclusive
 que recebi os pesos de terceiros listados acima, cada um com a sua
 licen&ccedil;a.</span>
</label>

<p class="docs">
 <a href="/termos" target="_blank" rel="noopener">Termos de uso</a>
 <a href="/politica-privacidade" target="_blank" rel="noopener">Pol&iacute;tica
 de privacidade</a>
 <a href="/creditos" target="_blank" rel="noopener">Cr&eacute;ditos e
 licen&ccedil;as</a>
</p>

<div><button class="bt" id="ac_bt" disabled onclick="acEntrar()"
 data-radai-frase>Entrar</button></div>
<p class="msg" id="ac_msg"></p>

<p class="mini">O aceite fica registrado nesta esta&ccedil;&atilde;o, com data
e nome da m&aacute;quina. <b>Ele n&atilde;o interrompe um vigia que j&aacute;
esteja rodando</b> &mdash; travar o lote da noite por uma vers&atilde;o nova de
documento derrubaria a esta&ccedil;&atilde;o de madrugada, em
sil&ecirc;ncio.</p>

</div><script>
var AC_PONTOS = [];
function acEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;')
 .replace(/</g,'&lt;').replace(/>/g,'&gt;')}

fetch('/api/aceite').then(function(r){return r.json()}).then(function(d){
 AC_PONTOS = (d.pontos || []).map(function(p){ return p.chave });
 document.getElementById('ac_pontos').innerHTML =
  (d.pontos || []).map(function(p){
   var G = {nao:  ['nao',     '&#10007;'],
            atencao: ['atencao', '&#9888;'],
            sim:  ['',        '&#10003;']};
   var g = G[p.sinal] || G.sim;
   return '<div class="pt' + (g[0] ? ' ' + g[0] : '') + '">'
    + '<span class="v">' + g[1] + '</span><div>'
    + '<b>' + acEsc(p.titulo) + '</b>'
    + '<span>' + acEsc(p.detalhe) + '</span></div></div>' }).join('');
 var fx = document.getElementById('ac_fontes');
 var fl = document.getElementById('ac_fo_linhas');
 if(fx && fl && (d.fontes || []).length){
  fl.innerHTML = (d.fontes || []).map(function(f){
     return '<div class="fo"><b>' + acEsc(f.nome) + '</b>'
      + '<span>' + acEsc(f.licenca) + '</span></div>' }).join('');
  fx.style.display = '';
 }
 var r = d.registro || {};
 var mudouTexto = !!(d.impressao && r.versao === d.versao
                     && r.impressao !== d.impressao);
 if(r.versao && (r.versao !== d.versao || mudouTexto)){
  var m = document.getElementById('ac_mudou');
  m.style.display = 'block';
  m.innerHTML = '<b data-radai-frase>Os documentos mudaram.</b> '
   + '<span data-radai-frase>Versão aceita:</span> '
   + acEsc(r.versao) + ' (' + acEsc(r.quando || '?') + ') &middot; '
   + '<span data-radai-frase>versão atual:</span> '
   + acEsc(d.versao) + ' (' + acEsc(d.data) + ')';
 }
 acTraduzir();
}).catch(function(){
 acMsg('Não consegui carregar os pontos. Recarregue a página.');
});

function acTraduzir(){
 try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
}
function acMsg(t){
 var el = document.getElementById('ac_msg'); if(!el) return;
 if(window.uiTexto) window.uiTexto(el, t); else el.textContent = t;
 acTraduzir();
}

document.getElementById('ac_ok').addEventListener('change', function(){
 document.getElementById('ac_bt').disabled = !this.checked;
});

function acEntrar(){
 var bt = document.getElementById('ac_bt'), msg = document.getElementById('ac_msg');
 bt.disabled = true; msg.style.color = 'var(--text-dim,#72829b)';
 acMsg('registrando…');
 fetch('/api/aceite', {method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({quem: '',
                        itens: AC_PONTOS})})
 .then(function(r){return r.json()}).then(function(d){
  if(d.erro){ acFalhou(d.erro); return }
  var p = new URLSearchParams(location.search).get('de') || '';
  var n = '';
  for (var k = 0; k < p.length; k++) {
   var cc = p.charCodeAt(k);
   if (cc === 9 || cc === 10 || cc === 13) { continue; }
   n += (cc === 92) ? '/' : p.charAt(k);
  }
  var destino = (n.charAt(0) === '/' && n.charAt(1) !== '/') ? n : '/';
  /* GUARDA: o primeiro uso (TPS de destino e pasta) vem logo depois do
     aceite; sem resposta da rota, segue para o destino de sempre. */
  fetch('/api/primeiro-uso').then(function(r){ return r.json() })
   .then(function(pu){
    location.href = (pu && pu.feito === false)
      ? '/primeiro-uso?de=' + encodeURIComponent(destino) : destino;
   }).catch(function(){ location.href = destino; });
 }).catch(function(e){ acFalhou(e); });
}

function acFalhou(erro){
 var msg = document.getElementById('ac_msg'), bt = document.getElementById('ac_bt');
 if(msg){
  msg.style.color = 'var(--perigo,#E96A5C)';
  var h = '<span data-radai-frase>Não consegui registrar o aceite.</span> '
   + '<code>' + acEsc(erro) + '</code>';
  if(window.uiHTML) window.uiHTML(msg, h); else msg.innerHTML = h;
  acTraduzir();
 }
 if(bt) bt.disabled = false;
}
</script></body></html>"""


def pagina_aceite():
    css = CSS_ACEITE
    try:
        import radai_ui
        css = radai_ui.TOKENS + CSS_ACEITE
    except Exception:
        pass
    pagina = PAGINA_ACEITE.replace("@CSS@", css)
    try:
        import radai_primeiro_uso as _pu
        pagina = _pu.com_canto(pagina)
    except Exception:
        pass
    try:
        import radai_ui as _ui
        pagina = _ui.aplicar(pagina)
    except Exception:
        pass
    try:
        import radai_languages as _idi
        pagina = _idi.so_traduzir(pagina)
    except Exception:
        pass
    return pagina


def montar_portao(app):
    from starlette.responses import RedirectResponse

    try:
        impressao_dos_documentos()
    except Exception:
        pass

    @app.middleware("http")
    async def _portao(request, call_next):
        try:
            caminho = request.url.path or "/"
            # GUARDA: a API passa sempre; o lote da noite não para por
            # documento novo.
            if caminho.startswith("/api/") or caminho in LIVRES:
                return await call_next(request)
            if "." in caminho.rsplit("/", 1)[-1]:
                return await call_next(request)
            try:
                em_dia = aceito()
            except Exception:
                # GUARDA: sem conseguir ler o aceite, o portão FECHA.
                em_dia = False
            if not em_dia:
                return RedirectResponse("/aceite?de=" + caminho,
                                        status_code=303)
        except Exception:
            # GUARDA: falha do próprio portão deixa passar; derrubar o
            # servidor trancaria a estação inteira.
            pass
        return await call_next(request)
