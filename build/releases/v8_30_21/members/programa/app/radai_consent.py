# -*- coding: utf-8 -*-
import hashlib
import json
import os
import socket
import tempfile
from datetime import datetime

import radai_archive
import radai_menu
import radai_web
import radai_termos_catalogo as catalogo_termos

VERSAO_DOCS = "3.3"
DATA_DOCS = "2026-11-26"
ARQUIVO_ACEITE = "aceite.json"

IMPRESSOES_PUBLICADAS = {
    "3.3": "6fccd7ff97461d97c717e1477dee1620247489c07f3ac839d2452236e7662a67",
    "3.2": "bbffb592cb696e14995967c79c863a20e018dcee28ec05f410bb7d574b72f221",
    "3.1": "9d920d66bcea8887c4e8e4020fde7cacfe98074c6807b734b2cebe2915d7aa5b",
    "3.0": "5ead9ebea062180d1d82b0f1d3baf897bdca707b6c664e299778c1ebf3c09a65",
    "2.9": "9ba528a58ff7253eeebc745953d6e8ec0c5a45899aa0bc3687ff302e8c05f0bf",
    "2.8": "a2d38ab1d8ff2a63532ddb3c9762f533d7b21ccfe04f7048c2df43e9fb5fab8d",
    "2.7": "92530490dcc12b8b942bc9ea64dcbf5ba71c6d9868989c095c0cfeb8a1b20ea9",
    "1.4": "8c43155546aca32895fd4bf306267582a2cf6cd0ab2376f6939ddff618b78108",
    "1.5": "73fece8185e4971da0902397c44d6e5a0c5510a6253439eab070ad7124f56489",
    "1.6": "c2c37d60c50a13c6e24bab5c813ce26ff40ebdc0696a82dc649e5c2fc9237b62",
    "1.7": "8d75736e7e460b276f0c1b855870c7024d2bff9a7de31a3a6a5f7c93b7f144f7",
    "1.8": "3d4a4f8773824f220e2e58d61b85522681a10a7ca78daf4618e151845f781ad5",
    "1.9": "087a47baff075f36e14b23ddac71396fc206f7ab9b611a0c88936b2f47948e1d",
    "2.0": "c6b3c126af07cd56a14230008af944a09824c7d7f9ed51b834dcfdca4728aa97",
    "2.1": "5ec308c786f4495cd965ec6a5b6acda89853731f5415eacf9556cf2ea6f28013",
    "2.2": "1e1647d8af01d4fc904b17fe3386a4ca2016eb23a47392ab0499c5c37f288ab1",
    "2.3": "e3aadaa481fdbf73d4741f2517449c665d56bd3f156a285330bc8062f5d266e9",
    "2.4": "a551a58c0157d3bcf48e15b6a68835a5fae36593d814188ad6bd64903c8e21b4",
    "2.5": "bc423324d603e05cee99e762c070e2f2ea62678bffe41e3a1bdd293fd8914bfb",
    "2.6": "c753d3443e001953f4b51f5f61ad90b3ee491194c7d14eb961b1aa423a92abb0",
}

# GUARDA: versao publicada nao se retoca (mudou o texto, versao nova); so a
# linha de uma versao ainda nao publicada se troca, e cada troca fica no dado
# abaixo, com o que entrou no texto.
RESSELAGENS_ANTES_DA_PUBLICACAO = {"1.4": 2, "1.5": 3, "1.6": 4, "1.7": 3,
                                   "1.8": 6, "1.9": 2,
                                   "2.0": 2, "2.1": 2, "2.2": 0, "2.3": 0, "2.4": 0, "2.5": 0, "2.6": 4, "2.7": 0, "2.8": 0, "2.9": 1, "3.0": 0, "3.1": 0, "3.2": 0, "3.3": 0}

IMPRESSOES_TROCADAS_ANTES_DA_PUBLICACAO = {
    "2.9": (("3e70e4a26d5c", u"as fontes e as condições do código e dos pesos no catálogo, no aceite e nos créditos da edição de pesquisa"),),
    "2.6": (("55cb0b988b4e", u"o fechamento de processo sem janela confirmado novamente no momento da ação do processamento dedicado"), ("7ac6e56d88b6", u"a pesquisa automática de nódulos no turno e a entrega hepática da RM nos conjuntos FULL e STUDY"), ("763066ef7611", u"a autorização de nódulos por turno do Vigia, disponível com a instalação compacta do LUNG RT"), ("4a2094608f44", u"a descrição no NOTICE da busca autorizada de nódulos por turno e do processamento hepático automático na RM")),
    "2.1": (("fedb3e1174c9",
             u"a regra clinica nova detalhada, cores, multiplas origens, Cancelar e leitura sem escrita ao abrir, escolha da serie e alteracao das origens so no proximo turno"),
            ("6c55fafa4fb4",
             u"a limitacao explicita das tasks atuais, que nao fornecem mascaras separadas das arterias pulmonares e do tronco pulmonar; essas estruturas nao sao acrescentadas ao composto, sem novos modelos ou plugins")),
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


def _maquina():
    return os.environ.get("COMPUTERNAME") or socket.gethostname()


def _caminho():
    # Em acervo de rede cada estação conserva seu recibo mesmo depois do aceite das outras.
    chave = hashlib.sha256(_maquina().casefold().encode("utf-8")).hexdigest()
    return radai_archive.raiz() / "aceites" / chave / ARQUIVO_ACEITE


def aceite():
    caminho = _caminho()
    if not caminho.is_file():
        # O recibo legado serve para mostrar a mudança dos termos à estação de origem.
        caminho = radai_archive.raiz() / ARQUIVO_ACEITE
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            d = json.load(arquivo)
        if isinstance(d, dict) and str(d.get("maquina") or "").casefold() == _maquina().casefold():
            return d
    except (OSError, ValueError, UnicodeError):
        pass
    return {}


def aceito():
    try:
        a = aceite()
        if (a.get("versao") != VERSAO_DOCS or a.get("ensino_pesquisa") is not True
                or set(a.get("itens") or ()) != {p[0] for p in PONTOS}
                or set(a.get("ferramentas_opcionais") or ()) != set(catalogo_termos.grupos_opcionais())):
            return False
        catalogo = catalogo_termos.catalogo()[0]
        feita = str(a.get("impressao") or "")
        atual = impressao_dos_documentos()
        return bool(feita) and feita == atual and a.get("catalogo_sha256") == catalogo
    except Exception:
        return False


def ferramenta_autorizada(grupo):
    return (grupo in catalogo_termos.grupos_opcionais() and aceito()
            and grupo in (aceite().get("ferramentas_opcionais") or ()))


def montar_registro(quem="", itens=None, catalogo_sha256=None, ensino_pesquisa=False, ferramentas=()):
    return {"versao": VERSAO_DOCS, "data_documentos": DATA_DOCS,
            "impressao": impressao_dos_documentos(),
            "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quem": str(quem or "")[:80],
            "maquina": _maquina(), "ensino_pesquisa": ensino_pesquisa is True,
            "catalogo_sha256": catalogo_sha256,
            "ferramentas_opcionais": sorted(set(ferramentas or ())),
            "itens": list(itens or [])}


def _guardar_recibo_anterior(caminho):
    fonte = caminho if caminho.is_file() else radai_archive.raiz() / ARQUIVO_ACEITE
    if not fonte.is_file():
        return
    dados = fonte.read_bytes()
    try:
        antigo = json.loads(dados.decode("utf-8"))
    except (UnicodeError, ValueError):
        return
    if (not isinstance(antigo, dict) or str(antigo.get("maquina") or "").casefold() != _maquina().casefold()
            or antigo.get("versao") == VERSAO_DOCS):
        return
    historico = caminho.parent / "historico"
    historico.mkdir(exist_ok=True)
    destino = historico / (hashlib.sha256(dados).hexdigest() + ".json")
    if destino.is_file() and destino.read_bytes() == dados:
        return
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=historico, delete=False) as arquivo:
            temporario = arquivo.name
            arquivo.write(dados)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, destino)
    finally:
        if temporario and os.path.exists(temporario):
            os.unlink(temporario)


def registrar_aceite(quem="", itens=None, catalogo_sha256=None, ensino_pesquisa=False, ferramentas=()):
    if ensino_pesquisa is not True or catalogo_sha256 != catalogo_termos.catalogo()[0]:
        raise ValueError("Confira o catálogo vigente e confirme o uso para ensino e pesquisa.")
    if not isinstance(itens, list) or set(itens) != {k for k, _, _ in PONTOS}:
        raise ValueError("Falta a confirmação dos termos de uso da suíte.")
    if not isinstance(ferramentas, (list, tuple)) or set(ferramentas) != set(catalogo_termos.grupos_opcionais()):
        raise ValueError("Confira o catálogo vigente e confirme o uso para ensino e pesquisa.")
    d = montar_registro(quem, itens, catalogo_sha256, ensino_pesquisa, ferramentas)
    caminho = _caminho()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    _guardar_recibo_anterior(caminho)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=caminho.parent,
                                         prefix="aceite-", suffix=".tmp", delete=False) as arquivo:
            tmp = arquivo.name
            json.dump(d, arquivo, ensure_ascii=False, indent=1)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(tmp, caminho)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return d


PONTOS = [
    ("uso_estudo",
     u"A Local Suite destina-se ao ensino e à pesquisa.",
     u"Os autores de cada modelo definem as condições de uso do código e dos pesos. Consulte as licenças na ficha do componente."),
    ("unapproved",
     u"Nenhuma estrutura gerada aqui pode ser usada para tratar.",
     u"Toda estrutura é uma sugestão de IA não aprovada (ApprovalStatus = UNAPPROVED). Os comparadores identificam o modelo no nome da ROI dentro do RTSTRUCT escolhido. Com nomes próprios da estação, a descrição conserva o nome padrão e a indicação de sugestão não aprovada. A aprovação médica ocorre no sistema de planejamento."),
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
     u"Os modelos rodam nesta estação. Abrir a suíte dispensa consulta externa de versão. "
     u"O registro de casos guarda a conexão como «não verificada». Verificar atualizações ou obter componentes "
     u"aciona as origens descritas na Política. Uma tarefa solicitada pode tentar obter um peso ausente. "
     u"Essas operações não enviam imagens, nomes ou identificadores de pacientes."),
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
     u"Quando a segmentação pesquisa achados.",
     'No PERSONALIZADO, a tarefa de achado ou o protocolo que a inclui precisa ser escolhido. O Vigia só pesquisa nódulos em TC de tórax com o LUNG RT instalado e a autorização do operador para aquele turno. Na RM abdominal, a identificação do fígado pode acionar segmentos e lesões hepáticas. O registro identifica as tarefas executadas. Todo achado requer revisão médica.'),

    ("responsavel",
     u"O serviço é o controlador dos dados.",
     u"O programa roda na infraestrutura do serviço, com dados do serviço. "
     u"Base legal, consentimento e retenção são responsabilidade dele."),
    ("licenca_pesos",
     u"Cada modelo e biblioteca de terceiros tem autoria e condições de uso próprias.",
     u"As licenças abaixo são DO PESO, e não do código: o NV-Segment-CT da "
     u"NVIDIA (Open Model License — uso comercial PERMITIDO, e o cartão do "
     u"modelo diz que ele é para pesquisa e não para uso clínico); o CADS na "
     u"variante `open` (CC BY-SA 4.0 — comercial, com ShareAlike, que alcança "
     u"um fine-tune seu e não o contorno que sai dele); o MOOSE (CC BY 4.0 — "
     u"comercial, sem ShareAlike, e EXIGE atribuição); e os níveis cervicais "
     u"de Weissmann et al. (CC0-1.0, domínio público); e o modelo do encéfalo "
     u"em TC de Buti et al. (MIT). O código do TotalSegmentator tem licença "
     u"Apache-2.0. Consulte a ficha da tarefa para os termos dos pesos. No JHU pélvico, a licença MIT "
     u"se aplica ao código. A publicação dos pesos não especifica uma licença "
     u"separada para os checkpoints."),
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
            "uso_permitido": m.get("uso_permitido") or u"nao_especificado",
            "livre": m.get("uso_permitido") == u"livre",
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
              (u"catalogo de componentes", catalogo_termos.catalogo()[0]),
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
            fontes, catalogo_termos.catalogo()[0], texto_canonico, radai_credits.pagina,
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

CONEXOES_AUTOMATICAS = ()  # Abrir a suíte e registrar um caso dispensam sondas externas.


POLITICA = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Política de Privacidade · Radioterapia.AI</title><style>""" + _CSS + u"""</style></head><body><header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela">Privacidade</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>
<div class="env">
<div class="rc-capa">
 <span class="rc-chip"><i>§</i> Documento</span>
 <h1>Política de <span data-radai-t="1">Privacidade</span></h1>
</div>
<p class="sub">Radioterapia.AI · Local Suite — versão """ + VERSAO_DOCS + u""", de """ + DATA_DOCS + u""".</p>

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
<p>Ao importar um RTSTRUCT, o aplicativo lê as referências DICOM e grava uma cópia na pasta da
série selecionada. O arquivo continua contendo os dados DICOM originais. O visor de comparação
e o reconstrutor podem abrir essa cópia. Importá-la não registra uma segmentação automática concluída.</p>
<p>Na estação, ou na infraestrutura do serviço que você apontar. O programa não
tem armazenamento próprio fora dela. Os lugares, um por um:</p>
<ul>
 <li><b>Ao lado da série.</b> Os <b>RTSTRUCT</b> (<code>RS_RadAI_*.dcm</code>)
 são gravados na pasta dos DICOMs — ou na árvore de <code>OUT_DIR</code>, se
 ela estiver preenchida (seção 5). Quais, depende do modo em que a série
 rodou. O AUTO entrega STUDY; no PERSONALIZADO a chave de anatomia geral seleciona o FULL.
 As entradas usadas para margens, recortes e uniões são processadas enquanto forem necessárias.
 Junto fica a subpasta <code>_RadAI</code>, com os marcadores de coordenação entre máquinas,
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
 onde há serviço que digita nome ou iniciais. O índice ajuda a reconhecer fases de TC 4D e a reaproveitar leituras. Ao iniciar o Vigia contínuo, a suíte tenta inscrever as pastas nos avisos de alteração do Windows antes da primeira varredura. Depois, ela verifica os caminhos afetados. Se perder avisos, a inscrição cair ou a origem não os oferecer, pode voltar a varrer a pasta para recuperar o que chegou. Ao pausar ou desligar o Vigia, essas leituras param. O Overnight Run conserva a descoberta própria do turno.</li>
 <li><b>Índices locais do Vigia.</b> Na mesma pasta de <code>index.json</code>, o arquivo <code>vigia-consulta.sqlite3</code> associa o UID da série à pasta e ao identificador do paciente. O arquivo <code>vigia-turno.sqlite3</code> reúne datas, descrições e cabeçalhos de série usados pela triagem, caminhos, alterações pendentes, decisões da fila e registros de falhas. Caminhos e descrições podem conter nomes, e os índices exigem a mesma proteção que os exames. São metadados locais. Nenhum pixel DICOM é gravado nesses índices. A pasta habitual é <code>%LOCALAPPDATA%\\RadAI_Watcher</code>. Se for inadequada, a suíte tenta uma pasta local <code>RadAI_Watcher</code> na área temporária ou na pasta do programa. Os índices podem permanecer em disco após o fechamento. O índice do turno renova seus dados de trabalho quando é reconstruído.</li>
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
 estrutura, o nome e a cor RGB que a estação escolheu) e os protocolos próprios
 (<code>protocolos_proprios.json</code>: de cada um, o nome, a modalidade, as
 estruturas, as uniões e se ele procura achado) — nada de paciente. A
 atualização os preserva, e o desinstalador oferece guardá-los, como faz com
 o arquivo de configuração. No próprio arquivo de configuração vão também a
 lista de pastas do turno (<code>ROOTS</code>), a pasta principal
 (<code>ROOT</code>), a pasta favorita (<code>PASTA_FAVORITA</code>) e a marca de que o guia já
 foi visto nesta estação (<code>GUIA_VISTO</code>). A opção de oferecer o processamento
 dedicado (<code>MODO_DEDICADO</code>) pertence à estação. A exportação omite essa
 preferência, e a importação preserva o valor local mesmo ao ler um arquivo antigo.</li>
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
 e o registro deste aceite. A partir da versão 2.6 dos documentos, os recibos ficam
 na subpasta <code>aceites</code> do acervo, separados por uma chave derivada do nome
 da estação. Cada estação confirma a sua leitura, inclusive quando o acervo é compartilhado.
 Numa estação que usou uma versão anterior, o
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
 arquivo sai quando a série termina; na manutenção do primeiro processamento, o caso em andamento de um processo que não existe mais pode virar um caso «interrompido»,
 com a última etapa e a hora. Na gravação, o programa
 confere que nenhum identificador daquela série escapou para o caso ou para o
 log dele, e recusa gravar se escapou. O relatório do registro, que a rotina
 própria de relatórios grava em <code>registro\\relatorios\\</code> (em
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
 <li><b>Histórico técnico de memória do motor.</b> Durante o processamento, o
 motor registra em <code>calibracao\\memoria-motor-v1.json</code>, na pasta
 local da instalação, a contagem de amostras e os extremos de memória
 observados por fase, incluindo a inferência, o pós-processamento e a
 gravação. O histórico é agregado entre execuções. Ele mede a memória do
 processo e do Windows e não identifica pacientes, exames ou horários de
 atendimento.</li>
 <li><b data-radai-t="1">No perfil do usuário do Windows</b>, em
 <code>%LOCALAPPDATA%\\RADIOTERAPIA_AI</code>: o <code>em_uso.json</code>, que o programa atualiza quando muda sua atividade e apaga ao fechar normalmente. Durante um processamento ou uma sessão dedicada que ainda precise de proteção, pode renovar a marca a cada 60 segundos. Em repouso na instalação padrão, aguarda a próxima mudança — ele existe para o kit de otimização da estação (o
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
 <li><b>Recibo do instalador.</b> Ao aceitar os termos de componentes, o instalador
 grava o identificador de segurança (SID) da conta Windows, o nome do computador, a data e a hora
 UTC, o perfil de instalação, a finalidade de ensino e pesquisa e sua revisão. O recibo
 identifica o catálogo e as condições aceitas por suas impressões SHA-256 e lista os
 componentes opcionais omitidos. Esses dados permitem conferir se o mesmo operador
 já aceitou as condições aplicáveis naquela estação. O arquivo fica em
 <code>%LOCALAPPDATA%\\Radioterapia.AI\\LocalSuite\\Termos\\instalador\\&lt;perfil&gt;\\vigente\\LICENCAS_COMPONENTES.json</code>.
 Na versão 8.30, o nome da pasta no lugar de <code>vigente</code> era a impressão do catálogo.
 Ao migrar um recibo compatível, o instalador registra o formato de origem e conserva a data
 original. Uma nova decisão atualiza o arquivo vigente. Esses recibos permanecem no perfil
 do Windows até sua remoção local, sem prazo automático de expiração. A suíte não os envia
 aos fornecedores dos modelos nem os inclui no pacote de transferência ou na exportação
 das configurações. O recibo do aceite feito no aplicativo está descrito no item sobre o acervo.</li>
 <li><b>Histórico do esforço e das tentativas.</b> O card de entrega no acervo mostra o esforço registrado pelo motor. Para entregas antigas sem esse dado, o esforço aparece como desconhecido. Os registros locais de retomada identificam a série pelo UID, a tarefa e a rota de execução. Um UID pode identificar um exame e requer a mesma proteção que o acervo. A liberação de memória, uma pausa ou a retomada em outro dispositivo preservam o esforço escolhido.</li>
 <li><b>Histórico dos aceites.</b> Ao confirmar a nova edição, o recibo anterior da própria estação fica na subpasta <code>historico</code>, junto ao recibo atual. O arquivo anterior conserva data, versão, impressão e os demais campos originais.</li>
 <li><b>Registro local do processamento dedicado.</b> Ao confirmar o modo, a Suite grava
 <code>%LOCALAPPDATA%\\RADIOTERAPIA_AI\\dedicado.json</code> no perfil do usuário do Windows.
 O registro de recuperação contém os nomes e os caminhos dos executáveis envolvidos,
 os nomes dos serviços, identificadores técnicos dos processos e da sessão, e o estado
 das ações necessário para desfazê-las. Títulos de janelas, nomes de pacientes,
 caminhos de exames e identificadores DICOM ficam fora desse registro. Na tela do modo, cada série é identificada pela posição na fila. Se uma devolução automática não terminar, o diário mantém a pendência. O supervisor faz tentativas curtas para falhas transitórias e encerra. Uma restrição de permissão ou de política é registrada para nova tentativa em uso posterior.</li>
 <li><b data-radai-t="1">No %TEMP% do usuário</b>, quando o programa é aberto pelo atalho: a
 saída da janela do motor, que roda sem janela
 (<code>radai_motor_&lt;porta&gt;.txt</code>) — as mesmas linhas do log da
 sessão (seção 2), recomeçada a cada arranque —, que o lançador mostra se a
 sessão anterior não fechou normalmente; a página local de carregamento que
 o lançador abre no navegador antes de o programa responder
 (<code>radai_carregando_&lt;porta&gt;.html</code>, e o
 <code>radai_carregando_&lt;porta&gt;.js</code> com o estado da abertura), sem
 nada da estação nem de paciente; e, quando você pede o «Atualizar agora» (seção 4), a
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
 série de novo na fila, e some quando o programa fecha. No Nidus RT, quando o plugin opcional NEURO RT estiver instalado, as
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
 pedidos; o filtro de data das leituras de pasta —, um contador de entregas e os
 últimos 256 avisos da fila. Para evitar repetir o som e a notificação, cada
 aviso registra o identificador do cartão (ou o trecho final do UID da série)
 e o tipo de evento. O armazenamento da aba, que
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
 O navegador do painel guarda esses itens e o cache em seu perfil próprio, <code>%LOCALAPPDATA%\\RADIOTERAPIA_AI\\janela</code>. Em uma atualização a suíte reconhece o perfil anterior em <code>%TEMP%\\radai_janela</code> e tenta migrá-lo quando ele está livre. Se estiver em uso ou a migração não puder terminar, a suíte pode continuar com o perfil anterior.</li>
</ul>
<p><b>Nada disso sai sozinho.</b> O que sai, sai por um ato seu — seção 5.</p>

<p>O NEURO RT é um plugin opcional, instalado apenas por pedido em
 <code>Plugins/NEURO RT</code>. Ele possui termo e política próprios, apresentados
 antes da instalação e no primeiro uso. Sua consulta e seus downloads usam o
 repositório público <code>github.com/drhenriquebraga/neuro-rt</code> e os arquivos
 da release, com verificação de integridade. Nenhuma imagem de paciente é
 incluída nessa consulta ou nesses downloads. As referências ao Nidus nesta
 Política descrevem a ferramenta do plugin quando instalada.</p>

<h2>4 · Conexões de rede</h2>
<p>Os exames são processados na infraestrutura do serviço. Consultar atualizações e baixar componentes envia aos fornecedores os pedidos técnicos descritos abaixo. Uma origem na internet pode observar a hora, o endereço IP de saída e os cabeçalhos do pedido. Esses pedidos não levam imagens, nomes, identificadores de pacientes ou caminhos dos exames.</p>

<h3>Ao abrir a suíte e ao registrar casos</h3>
<p>A interface conversa com o motor nesta estação, pelo endereço local <code>127.0.0.1</code>. Abrir o painel e deixá-lo parado não inicia consulta de versões nem teste de internet. O registro de casos mantém a conexão como «não verificada». Ele não faz sondas DNS ou conexões TCP para preencher esse campo.</p>
<h3>Quando você escolhe Verificar atualizações em Configurações</h3>
<p id="consulta-a-pedido">A suíte consulta <code>api.github.com</code> e o espelho oficial em <code>drhenriquebraga.com.br</code>. Na verificação explícita pode consultar as duas origens e mostrar o resultado de cada uma. A requisição HTTPS usa GET sem corpo, com <code>User-Agent: radioterapia-ai-local-suite</code>. O GitHub recebe <code>Accept: application/vnd.github+json</code>. O espelho recebe <code>Accept: application/json</code> e <code>Cache-Control: no-cache</code>. Para obter a versão recente, o verificador pode incluir um marcador de tempo para evitar resposta desatualizada. <code>RADAI_URL_VERSOES</code> permite configurar a origem de versões. O valor <code>0</code> desliga a consulta. O resultado mostra a versão disponível. Quando a consulta encontra uma nova versão, a porta de entrada pode indicá-la com um aviso e um ponto na engrenagem. A instalação começa quando você pede a atualização.</p>
<p>As informações dos plugins NEURO RT, LUNG RT e Coronárias disponíveis na estação podem ser verificadas localmente. Para consultar uma release ou baixar componentes de um plugin, use os controles do plugin em Configurações ou prepare o pacote pelo instalador. Na instalação por ZIP local, a suíte lê o pacote que você escolheu. A caixa de arquivo transmite o ZIP à própria estação pela conexão local. A atualização verifica o código e as dependências existentes. As configurações distinguem o espelho do código da disponibilidade de um pacote de pesos. Os pacotes de dependências e de pesos são obtidos pelas origens já indicadas ou pelo ZIP escolhido pelo operador. Os termos específicos continuam disponíveis em <a href="/licencas-ferramentas">Termos e licenças</a>.</p>
<p>Se você escolher uma pasta de rede, a leitura usa o servidor dessa pasta. No Overnight Run, a tela de frota lê arquivos da subpasta <code>.radai-status</code> de cada origem elegível do turno. Fora do turno, usa a pasta compartilhada definida em <code>STATUS_DIR</code>, quando configurada. A descoberta da frota não envia anúncios UDP. Os campos desse compartilhamento estão descritos na seção 5, em <code>STATUS_DIR</code>.</p>
<p><b>A estatística de uso do TotalSegmentator fica desligada.</b> De fábrica,
a biblioteca envia a <code>stats.totalsegmentator.com</code> um relatório de
uso a cada predição. Este programa grava <code>send_usage_stats=false</code> no
arquivo de configuração dela e, no processo que a executa, troca a função de
envio por uma que não envia nada.</p>
<p><b>Se faltar um peso.</b> O conteúdo disponível depende do pacote e dos plugins instalados. Se uma tarefa solicitada do TotalSegmentator precisar de um peso ausente, a biblioteca pode tentar obtê-lo na origem indicada por seus autores. Se o arquivo continuar indisponível, a execução registra o motivo. Para uma estação sem rede, prepare antes o pacote com os componentes necessários.</p>
<p><b>E o preparador, que monta o pacote.</b> Numa máquina com internet, ele
baixa o Python, as bibliotecas fixadas e os pesos de cada modelo, da origem de
cada um. Os pesos do TotalSegmentator, desde a v8.2, ele baixa por conta
própria — dos endereços que a própria biblioteca fixada monta, pelo
repositório de certificados do Windows — e confere cada arquivo antes de
extrair: o tamanho exato que a origem publica, o SHA-256 onde a origem publica
um, e o CRC de cada membro do <code>.zip</code>. Nesse preparo nada da estação
e nenhum dado de paciente sobe: só o pedido de cada arquivo. A instalação das dependências pode obter o exemplo público de demonstração do visor de esforços. A origem e a licença da TC aparecem no visor. Essa demonstração dispensa exames do serviço.</p>
<p><b>E o «Instalar / Atualizar app nesta máquina» do preparador.</b> O botão
confere primeiro se o programa já está nesta máquina, pela marca na pasta e
pelo registro de instalação. Se não está, ele instala tudo, com os pedidos do
parágrafo acima. Se está, ele consulta a release mais
nova do projeto em <code>api.github.com</code> — um GET sem corpo, com o
cabeçalho <code>User-Agent: radioterapia-ai-preparador</code>, no mesmo
endereço que a variável <code>RADAI_URL_VERSOES</code> troca ou desliga. Se
o endereço padrão não responder corretamente, tenta o espelho
<code>drhenriquebraga.com.br</code>. Se houver instalador mais novo,
ele baixa apenas o <code>_SETUP_LATEST.zip</code> e exige o tamanho e o
SHA-256 publicados, recusa o arquivo que grave fora da pasta
ou que diga outra versão, e segue a atualização por ele; se a estação precisar
de um pacote novo e houver rede, ele segue para o preparo do pacote, com os
pedidos do parágrafo acima. Quando a release não responde, ele testa a
internet com um pedido sem dado a <code>pypi.org</code> ou a
<code>huggingface.co</code>. Nada da estação e nenhum dado de paciente
sobe.</p>

<h3>Outras conexões iniciadas por você</h3>
<ul>
 <li><b>Coronárias (ROCardS)</b>. Ativar pela internet ou preparar o pacote
 portátil de pesquisa pode baixar os pesos do repositório AIM-Harvard no GitHub
 e as bibliotecas do PyPI. Esses downloads não enviam imagens. A opção
 «Importar de um pacote» confere e instala os recursos na estação, sem rede.</li>
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
 ou pergunta antes. Se só o código muda, uma janela de console mostra cinco
 etapas: conferir o pacote e o destino; testar a escrita e encerrar as janelas
 do perfil próprio do programa e seu motor; copiar o código e limpar seus
 caches; refazer os atalhos; reabrir o painel. O atualizador só anuncia
 «ATUALIZADO» depois de confirmar a versão esperada num processo novo e numa
 janela própria visível, e então a console fecha após 5 segundos. A sua
 configuração é preservada. Uma falha mantém o diagnóstico na console; se a
 cópia ficou incompleta, não reabre o código parcial e orienta executar o
 instalador novamente depois de corrigir o motivo. Antes da troca ou com o
 código já completo, oferece «R» para reabrir o programa. Se a versão nova
 precisa de um pacote novo de modelos, a tela
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
<p>Exportar configurações cria um JSON das categorias selecionadas: preferências da estação,
nomes e cores, protocolos próprios e aparência. Revise nomes livres e caminhos antes de compartilhar.
O histórico de casos, os exames, as credenciais e os aceites de licenças não fazem parte dessa exportação.
A importação mostra uma prévia; o aplicativo mantém na estação a cópia das configurações anteriores para desfazer.</p>
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
 <li><b>O pacote do registro de casos</b>: a exportação específica do
 registro, quando solicitada separadamente, sela um
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
 <li><b>Diagnóstico técnico da estação.</b> Em Configurações, em Diagnósticos e Registros, o botão
 <b data-radai-t="1">Diagnosticar</b> grava na pasta Downloads local do usuário um ZIP com
 um único arquivo, <code>diagnostico.json</code>. Ele contém a hora da coleta,
 as versões detectadas, dados técnicos do Windows, CPU, GPU, disco,
 paginação e memória, e contagens de falhas conhecidas em uma amostra
 limitada de registros. Inclui os extremos de memória por fase do motor
 quando disponíveis. Os dados de pacientes, imagens, UIDs, caminhos, nomes da
 estação, credenciais e textos dos logs ficam fora desse arquivo. O
 compartilhamento do ZIP é manual, pela pessoa autorizada pelo serviço.
 O botão realiza a coleta e a gravação local.</li>
 <li><b>O arquivo das configurações</b>: o «Exportar» de Configurações
 baixa, para a pasta de downloads do navegador, um <code>.json</code> com as
 chaves do arquivo de configuração — as pastas configuradas inclusive —,
 menos as que são desta máquina (<code>DEVICE</code>, <code>PORT</code>,
 <code>GUIA_VISTO</code>), os nomes e as cores das estruturas, os protocolos próprios e as preferências de aparência selecionadas.
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
 fábrica): quando o trabalho autorizado exige sinalizar a frota, cada máquina grava ali o seu sinal de vida — nome da máquina,
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
 gravam a partir dela, e a cópia de cada RTSTRUCT. A cópia temporária do STUDY sai depois da gravação. Se o programa cair no meio da série,
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
 <li>na manutenção que acompanha o primeiro processamento, inclusive no Rodar Agora com a origem do Vigia vazia, o
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
 <li>o <b>cache por tarefa</b>: na limpeza associada à varredura completa do Vigia, sai
 a entrada que não é lida há 14 dias e, se o cache passar de 20 GB, as mais
 antigas até ele caber;</li>
 <li>o <b>índice do acervo</b> mantém registros locais. Abrir a suíte não percorre os caminhos dos exames para retirar entradas. Uma conferência só pode remover do índice uma entrada cuja ausência tenha sido confirmada. Um compartilhamento inacessível não confirma exclusão.</li>
 <li>o <b>«Rodar agora»</b>, ao gravar de novo uma série, substitui os
 <code>RS_RadAI_*</code> que o programa tinha gravado nela — e só depois de você
 confirmar na tela: cada conjunto que ele grava de novo entra por cima do
 anterior, e só então ele apaga os que esta execução não produziu (um plugin
 que não foi pedido de novo, por exemplo). O marcador de conclusão anterior da
 série sai do lugar logo antes da gravação nova e é apagado quando ela
 termina; se a execução não entregar, ele volta. Se o programa cair nesse
 intervalo, a próxima varredura do vigia, ou o próximo «Rodar agora» da
 série, o devolve ao lugar, e o log manda conferir a pasta — ou o apaga, se
 o novo já foi gravado. <b>Refazer a série pode substituir a entrega anterior</b>. Se o entregue anterior já foi importado no sistema de
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
o que sobrou de uma série, a área de envio, as miniaturas e a saída da janela do motor
(<code>radai_motor_&lt;porta&gt;.txt</code>) —; o perfil reconhecido do navegador da suíte, atual ou anterior, se estiver fora de uso (<code>%LOCALAPPDATA%\\RADIOTERAPIA_AI\\janela</code> ou <code>%TEMP%\\radai_janela</code>); os dois índices SQLite do Vigia e arquivos auxiliares correspondentes que o desinstalador localizar na pasta local de dados ou no temporário, depois de conferir o caminho; os <code>motor_&lt;porta&gt;.json</code> que ficam em
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
(<a href="https://github.com/drhenriquebraga/local-suite/security">drhenriquebraga/local-suite</a>,
aba Security), e nunca numa issue pública — e nenhum relato leva dado de
paciente. Sobre os dados do seu serviço: o encarregado de dados da sua
instituição.</p>

<p class="sub" style="margin-top:22px">Ao mudar de versão ou de texto, este
documento pede aceite de novo: o aceite guarda a versão e a impressão digital
do texto aceito, e aceitar um texto não é aceitar o que o seguinte passou a
dizer.</p>
</div></body></html>"""


TERMOS = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Termos de Uso · Radioterapia.AI</title><style>""" + _CSS + u"""</style></head><body><header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela">Termos de uso</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>
<div class="env">
<div class="rc-capa">
 <span class="rc-chip"><i>§</i> Documento</span>
 <h1>Termos de <span>Uso</span></h1>
</div>
<p class="sub">Radioterapia.AI · Local Suite — versão """ + VERSAO_DOCS + u""", de """ + DATA_DOCS + u""".</p>

<div class="cx aviso">
<h3>Uso em ensino e pesquisa</h3>
<p>A Local Suite organiza a execução, a comparação e o pós-processamento de modelos desenvolvidos por terceiros.
O instalador usa a conexão de quem instala para obter os componentes nas fontes indicadas. Um pacote portátil
reúne os componentes preparados localmente para instalação offline. O aceite da suíte conserva as condições
de cada titular.
<a href="/licencas-ferramentas">Consultar finalidade, autoria, licenças e fontes de todos os componentes.</a></p>

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

<h2>1.1 · Modos de execução e acabamento</h2>
<p>O AUTO e o Vigia entregam o <code>RadAI_STUDY</code> conforme a modalidade e a anatomia identificadas.
No PERSONALIZADO, a seleção de protocolos, tarefas e estruturas determina a entrega. Em chamadas por script sem modo, a ausência de lista seleciona AUTO; uma lista fornecida torna obrigatórias as tarefas indicadas.
A chave «Anatomia Geral (FULL)» troca o destino para <code>RadAI_FULL</code> nas tarefas escolhidas.
Os resultados de comparação pedidos explicitamente recebem identificação da origem.</p>
<p>Todo protocolo inicia em PADRÃO. A escolha manual de FAST permite suavizar compostos em conjunto e
usar menos vértices quando a forma o permite. As bolsas intestinais admitem simplificação maior.
Crops, margens, uniões, exclusões e acabamentos anatômicos conservam os insumos de que precisam.
O acabamento pode alterar a borda do contorno e exige revisão na imagem de origem.</p>
<p>O protocolo simples de cabeça e pescoço inclui a união cervical quando a anatomia permite.
O avançado também oferece os níveis individuais. Na RM craniana T1 compatível, o SNC usa o SynthSeg
do NEURO RT com o aceite e os recursos do plugin. As dez estruturas propostas exigem revisão.
Um registro de atlas pode estar deslocado mesmo quando o RTSTRUCT referencia os cortes corretos.</p>
<p>A seleção de Anatomia Torácica pode incluir nódulos. O Vigia pesquisa nódulos em TC de tórax somente
quando o operador os autoriza naquele turno e o LUNG RT está instalado.</p>

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
 conforme as tarefas habilitadas. O acabamento de cada estrutura solicitada inclui, conforme o caso, a margem de cada vaso e da traqueia — depois dela, a aorta sai
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
 <li><b>O conjunto entregue</b> (<code>RadAI_STUDY</code>) reúne as estruturas selecionadas para o caso, com os mesmos recortes, margens e uniões que lhes cabem no FULL. O composto entra no lugar das partes; o osso da
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
 carótidas (<code>A_Carotid_ai</code>) ficam como estrutura própria só no
 completo; suas máscaras também compõem <code>GreatArteries_ai</code>, fora do
 <code>Heart_ai</code>. Ao final, o composto atual recebe a união com
 <code>Heart_Model_ai</code> menos o <code>Heart_ai</code> final, somente com
 as duas máscaras válidas na mesma grade, sem mudar o coração. A regra vale
 para o conjunto solicitado, preservando os filtros regionais de
 entrega; não acrescenta uma exigência de tórax ao completo. Sem uma das duas
 máscaras, o composto anterior é preservado e o motivo fica no log; o coração
 ausente não é tratado como vazio para somar o modelo inteiro. As tarefas atuais
 não fornecem máscaras separadas das artérias pulmonares e do tronco pulmonar.
 Essa diferença é uma operação geométrica, não uma identificação exclusiva
 dessas artérias nem a execução de outro modelo. <code>GreatVeins_ai</code> conserva a sobreposição
 com o coração de radioterapia.
 A laringe (<code>Larynx_ai</code>), as articulações temporomandibulares
 (<code>TMJ_L_ai</code> e <code>TMJ_R_ai</code>) e a mandíbula
 (<code>Bone_Mandible_ai</code>) entram no entregue sempre que são
 construídas. Numa série
 de cabeça e pescoço sem o tórax identificado, a soma dos pulmões
 (<code>Lungs_ai</code>) vai ao entregue no lugar dos dois pulmões, que
 ficam no completo; nas outras, ela vai junto com eles. O encéfalo de uma RM
 (<code>Brain_ai</code>) fica só no completo: o entregue de uma RM não leva
 encéfalo.
 No protocolo simples, as estruturas derivadas dos níveis incluem a união e as parótidas do nível
 VIII (o quadro logo abaixo e a seção 4), e a parótida do entregue vem só
 daí: sem os níveis ou quando o nível VIII não
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
 planos de corte, e não só a borda. No PERSONALIZADO, estruturas desmarcadas podem continuar necessárias aos recortes,
 margens e uniões de outra estrutura. Se nenhuma ROI com geometria válida puder ser entregue, a fila informa a falha.
 Quando existe entrega parcial, o aviso identifica as ausências.</li>
 <li><b>Acabamento do RTSTRUCT.</b> O gravador ajusta a quantidade de pontos por contorno.
 Em bordas pequenas, côncavas ou compartilhadas, mais vértices podem ser necessários.
 O esôfago final mantém prioridade sobre a aorta e as grandes artérias. Conjuntos FAST de versões
 anteriores permanecem disponíveis para leitura.</li>
 <li><b>Comparações e tarefas opcionais.</b> Quando pedidos, os contornos dos comparadores integram o mesmo RTSTRUCT e recebem prefixos de procedência (<code>TS_</code>, <code>NV_</code>, <code>CADS_</code>, <code>MOOSE_</code>). O TS cru preserva as máscaras do modelo, com a fusão sacral descrita abaixo. As tarefas anatômicas marcadas alimentam a entrega escolhida.</li>
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
o AUTO e o protocolo simples oferecem a <b>união dos níveis Ia a VIIb</b>
(<code>LNL_UNION_ai</code>), uma união anatômica não aprovada que <b>não é
OAR nem CTV</b> — a descrição dela diz isso, e o arquivo a marca como
<code>CONTROL</code>, e não como órgão —; e as <b>parótidas</b>
(<code>Parotid_L_ai</code> e <code>Parotid_R_ai</code>), que saem só do
nível VIII (parotídeo) do modelo menos o esternocleidomastoideo: a parótida
do TotalSegmentator não vai ao entregue, e, numa série em que os níveis não
rodaram, o entregue sai sem parótida. O protocolo avançado também permite enviar os níveis cervicais individuais.</p>
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
união, o nível IVb de cada lado perde a clavícula do mesmo lado. No
acabamento final, a união perde as intersecções com a mandíbula, os escalenos
anteriores, médios e posteriores, as clavículas e o hioide, conforme as máscaras
anatômicas disponíveis. A união não desconta mais os esternocleidomastoideos
nem os platismas bilaterais; as intersecções com esses músculos são mantidas.
A regra própria das parótidas do VIII menos o esternocleidomastoideo continua.
Preservar essas intersecções pode aumentar a união em relação à versão 8.8.
Os demais recortes continuam; a revisão médica continua obrigatória e a
união não se torna um alvo aprovado.</p>
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
que servia para limitá-la, saiu do AUTO e do protocolo Tórax / Mama
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
de todas as subtrações, o furo de cada corte axial é preenchido; a
cartilagem costal é retirada também depois desse preenchimento. Segue o
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
<p><b>O coração de radioterapia.</b> Antes da suavização, somente nos
cortes em que existe máscara da veia cava inferior, o <code>Heart_ai</code>
é limitado ao pericárdio disponível. Nos outros cortes essa restrição não é
aplicada. A cartilagem costal sai do coração, inclusive após o preenchimento.
A regra que retira a cava quando separada do coração continua, assim como o
recorte do esôfago e dos vizinhos de fora do pericárdio. A suavização final é
a do parênquima mais 3 mm fixos — 5,5 mm com o padrão. O
<code>Heart_Model_ai</code> das tarefas atuais é uma máscara única: não
contém rótulos separados de câmaras e vasos. Ela é preservada no FULL; o
programa não inventa essas partes nem aciona o MOOSE para desmembrá-la.
O MOOSE continua como comparação opcional, no PERSONALIZADO.</p>
<p><b>As estruturas finas saem como o modelo as entregou.</b> Os nervos
ópticos, o quiasma, os constritores da faringe e a tireoide saem sem
suavização adicional da máscara. A redução dos vértices respeita os detalhes da borda. O corte
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
atrás — ao topo do côndilo, com margem total de 3 mm no plano axial e para
cranial, sem expansão caudal. O limite inferior fica antes do primeiro corte
caudal com contorno único por hemimandíbula e é reaplicado após o acabamento;
a margem não é acrescentada à mandíbula. O lado sai de um
plano médio que passa pelo centro do crânio sem a mandíbula — na falta dele,
do encéfalo, da vértebra C1 ou da C2 —, e só sem nenhum deles pelo meio da
largura da mandíbula; numa mandíbula parcial sem essas estruturas na série, o lado pode
sair trocado, e o log da série diz qual referência valeu. A soma dos pulmões
(<code>Lungs_ai</code>) é o pulmão esquerdo e o direito do completo, como
saíram, sem o derrame pleural.</p>
<p><b>A medula e a cauda equina são uma partição por marco.</b> A
<code>SpinalCord_ai</code> fica cranial ao primeiro corte de L2 encontrado
a partir da extremidade cranial. Desse corte
para caudal, incluindo o próprio corte de L2, a porção existente é entregue
como <code>CaudaEquina_ai</code>, no conjunto solicitado. A divisão
usa a medula já finalizada, não acrescenta voxels nem chama outro modelo, e
sua procedência diz que é derivada por marco anatômico. O limite é reaplicado
no acabamento para não misturar as duas porções. Sem L2 válida na mesma grade,
a medula permanece inteira e não se cria uma cauda equina por aproximação; se
não houver medula caudal ao marco, essa porção pode sair vazia. O nome não
substitui a revisão médica do marco e da extensão.</p>
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
também da seleção do STUDY. O TotalSegmentator
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
<code>DEVICE</code> do arquivo de configuração), e o motivo vai ao log. O simples ato de abrir o painel não executa um modelo para testar a placa. Quando uma checagem de capacidade é solicitada e o teste de dispositivo se aplica, o programa pode usar um fantoma sintético (o <i>canário</i>) e reaproveitar uma verificação local válida. Nenhuma imagem de paciente entra nessa checagem. As bibliotecas que usariam a placa Intel (XPU e OpenVINO) existem
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
diz a hora. Quando parte das estruturas puder ser entregue, o único conjunto da série segue com aviso das ausências.</p>
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
nenhuma outra responde em 10 segundos — ou, se o navegador fechar sem avisar,
depois de três minutos sem sinal de nenhuma tela. Isso não interrompe a série
em curso: o programa não começa outra série, nem do vigia nem do «Rodar
agora», termina a que roda e só então se encerra; com o turno da noite
aberto, segue o turno até o fim. Com o turno da noite agendado na fila e o
lote do «Rodar agora» andando até ele, o fechar pelo X não segura a fila: o
lote segue, o turno abre, e o programa se encerra no fim do turno; lote
pausado ou parado não segura, porque o turno não abriria sozinho. Sem nada
rodando, ele inicia o encerramento ao fim da tolerância de 10 segundos. No ensaio, o processo terminou em até 15 segundos ao todo. Se uma tela volta a responder antes do encerramento, ele é cancelado,
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
do perfil próprio da suíte, atual ou anterior; o navegador da pessoa
nunca é tocado — e o encerra; se o programa estiver processando — uma série,
ou o turno da noite aberto ou agendado —, ele pergunta antes, e a série
interrompida volta para a fila, sem contar como falha.</p>

<h2>1.6 · As tags próprias e os protocolos próprios</h2>
<p>Em Configurações, na seção Estruturas e Protocolos, a estação pode dar
nome próprio às estruturas do entregue e montar protocolos próprios. Os dois
valem só para o entregue — o do AUTO e do PERSONALIZADO —: o
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
 <li><b>As cores próprias.</b> No mesmo editor, a estação pode escolher a cor
 RGB de cada estrutura do STUDY, mesmo sem trocar seu nome. São três inteiros
 de 0 a 255, gravados em <code>ROIDisplayColor</code>. A escolha só vale no
 modo «Tags próprias»; em «Padrão» fica guardada sem valer. O FULL mantém as
 cores padrão. A cor não muda a máscara, a procedência nem a condição
 não aprovada da estrutura.</li>
 <li><b>Os protocolos próprios.</b> Cada protocolo vale para uma modalidade
 (TC ou RM) e escolhe as estruturas do entregue entre as que alimentam o
 completo, com uniões — só por soma, cada uma com um nome que segue as regras
 do nome próprio. Ele aparece no PERSONALIZADO do «Rodar agora», numa chave
 com uma lista, só quando há protocolo da modalidade da série. Ligado, ele
 desliga os protocolos RT e a seleção livre; as tarefas que as estruturas
 dele pedem ficam ligadas e travadas; e o entregue daquela série é a seleção
 dele, com a regra de região de sempre (o osso da pelve, por exemplo, só com
 a pelve identificada). O vigia não usa protocolo próprio — roda sempre o
 AUTO. <b>Um protocolo próprio pode incluir
 achado</b> (seção 4.1): então a declaração é pedida a cada envio à fila, o
 log anuncia com a palavra <b data-radai-t="1">ACHADO</b>, e o resultado segue para a entrega escolhida; sem a declaração, a tarefa de achado não
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
 <li>A pesquisa de nódulos pulmonares depende da escolha do operador. Na RM abdominal, identificar fígado aciona a pesquisa de lesões hepáticas. A seção 4.1 descreve as tarefas por modalidade e a declaração do operador.</li>
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
 padrão e «sugestao IA nao aprovada» na descrição da estrutura. O rótulo do conjunto identifica a entrega (<code>RadAI_STUDY</code> ou <code>RadAI_FULL</code>). Os prefixos das ROIs de comparação identificam os modelos selecionados. Não existe caminho no
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
 <li><b>Buti et al.</b> — estruturas do encéfalo em TC (tronco
 encefálico, quiasma, cerebelo, ventrículos e linha média) — pesos sob
 <b>MIT</b>: uso comercial permitido.</li>
 <li><b>CADS</b>, na variante <code>open</code> — código Apache-2.0, pesos sob
 <b>CC BY-SA 4.0</b>: uso comercial permitido, com <i>ShareAlike</i>. O
 ShareAlike alcança um <i>fine-tune</i> que você faça sobre esses pesos; não
 alcança o contorno que sai deles.</li>
 <li><b>JHU-MICA</b> — a licença MIT acompanha o código. O release dos pesos
 pélvicos não declara uma licença separada para os checkpoints. A ficha
 no catálogo aponta para o repositório e a publicação dos autores.</li>
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
 <li><b>NV-Segment-CT (NVIDIA)</b> — código Apache-2.0, <b>pesos sob a NVIDIA
 Open Model License</b>, que <b>permite uso comercial</b>. O cartão do modelo
 diz que ele é para pesquisa e não para uso clínico, e essa frase é do autor
 do modelo, não da licença.</li>
 <li><b>ROCardS</b> — os autores destinam o código e os pesos à pesquisa
 não comercial sob CC BY-NC 4.0. A tarefa começa desativada. O aceite do instalador
 e o aceite geral da suíte não a ativam. Em Configurações → Plugins → Coronárias,
 o operador pode aceitar os termos específicos e destinar esta estação ao ensino
 vinculado à pesquisa e à pesquisa não comercial. <a href="https://github.com/AIM-Harvard/ROCardS#license"
 target="_blank" rel="noopener noreferrer">Projeto e termos dos autores</a>.</li>
 <li><b>TotalSegmentator</b> — o código tem licença Apache-2.0. A ficha
 de cada tarefa no <a href="/licencas-ferramentas">catálogo de ferramentas</a>
 identifica as condições dos respectivos pesos e a fonte dos autores. Ele roda com o
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
deles. Além disso, só rodam em série de TC em que a
cabeça aparece. Quando rodam, entram no conjunto completo — e, deles, só a
união e as parótidas do nível VIII vão ao entregue (o quadro da seção 1.2)
—; o arquivo próprio deles só sai no PERSONALIZADO. A parótida do entregue
vem só do nível VIII — o nível VIII menos o esternocleidomastoideo —, e só
quando o lado dele se confirma e quando ela é plausível como a glândula
inteira: 0,5 cm³ ou mais, pelo menos metade do volume da do TotalSegmentator
e pelo menos 30% de sobreposição com ela. Quando não é — e sempre que os
níveis não rodam, em qualquer protocolo —, o entregue sai sem parótida, e o log
diz por quê. A parótida do TotalSegmentator nunca vai ao entregue: fica só
no conjunto completo, sempre com o sufixo
<code>_ts</code> (<code>Parotid_L_ts</code> e <code>Parotid_R_ts</code>),
para comparação — com o pós-processamento do completo, e não a crua.</p>

<div class="cx destaque">
<p>O registro guarda o campo que diz o que a licença do peso permite
— é ele que a tela do aceite lê para montar a lista de pesos.
Nenhuma rota nem tela do programa elege modelo. No modelo
pélvico da JHU, a licença MIT cobre o código. Os checkpoints são publicados
pelos autores sem licença específica declarada para os pesos.</p>
</div>

<p>O programa não concede nem amplia direitos sobre esses modelos. O nome e o
endereço da licença de cada modelo e de cada biblioteca que o pacote fixa estão
no <code>NOTICE</code>, que viaja no pacote, e em
<a href="/creditos" data-radai-t="1">Créditos e licenças</a>; as dependências que essas
bibliotecas trazem consigo levam a licença delas no metadado do pacote
instalado; o texto íntegro da licença do NV-Segment-CT viaja também na pasta
do modelo.</p>

<div class="cx">
<p>O preparador registra a origem e a identificação dos pesos. Quando os
termos de um peso não estão especificados, essa condição aparece na lista
de modelos.</p>
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

<p><b>As listas iniciais de anatomia vêm sem tarefas de achado.</b> O pacote traz as tarefas de achado. São
<b>três lugares que têm de concordar</b> — a lista padrão de tarefas do
programa, a base que o vigia põe na frente de toda série (o arquivo de
configuração não escolhe tarefa), e a tabela por região que o vigia consulta,
quando ainda não há região nenhuma. Se os três divergirem, ou se a tabela, em
qualquer região, o que um protocolo RT do PERSONALIZADO arrasta, cada chave
que nasce ligada nele trouxer uma
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
achado</b> nessa tabela. Para pesquisar nódulos durante um turno, escolha Sim no formulário do Vigia antes de iniciar. A opção vem em Não e fica bloqueada sem o módulo LUNG RT instalado. O Vigia só inclui a tarefa em TC com tórax identificado, durante o turno autorizado. Na RM abdominal, o Vigia e o «Rodar agora» acrescentam a segmentação dos segmentos e lesões hepáticas quando a base identifica fígado. No tórax, uma das tarefas de anatomia é a do derrame pleural e
pericárdico, que é anatomia (abaixo). O texto do exame não acrescenta tarefa, e
o arquivo de configuração também não: o vigia roda sempre o AUTO, e a fila também permite pedir as tarefas de cabeça e
pescoço, quando você marca essa região para a série; delas, a dos músculos de
cabeça e pescoço, com os constritores da faringe, só roda com o pescoço
confirmado pela anatomia, e o log diz quando ela fica de fora. Tarefa avulsa e
comparação de modelos se pedem série a série, no PERSONALIZADO do «Rodar
agora».</p>

<p><b>Pedidos explícitos no «Rodar agora».</b> No PERSONALIZADO do «Rodar agora», o primeiro é ligar a chave da tarefa no PERSONALIZADO — ela nasce
desligada, com o selo ACHADO; o protocolo Anatomia Torácica também a solicita. Ligada assim, o
log anuncia a tarefa com a palavra <b data-radai-t="1">ACHADO</b>. Os resultados seguem a seleção da série, e a descrição da ROI identifica a origem. O registro do caso guarda quais rodaram, para que a resposta a "o que estava ligado naquela
série?" não dependa da memória de ninguém. O segundo é escolher um
protocolo próprio da estação que inclua achado (seção 1.6): a declaração é
pedida a cada envio à fila, e o que a tarefa devolve segue a regra da chave.
O protocolo Anatomia Torácica solicita as tarefas torácicas, inclusive nódulos. A chave Anatomia Geral (FULL) entrega apenas o conjunto completo das tarefas selecionadas.
 A revisão antes de iniciar o turno apresenta a escolha feita para a pesquisa de nódulos. O pedido vale somente para esse turno.
Rodar somente nódulos no LUNG RT não marca a anatomia como concluída.</p>

<p>No LUNG RT, o usuário declara o pedido ao iniciar um caso, o rastreio de uma
pasta ou as fases de uma TC 4D. O resultado é uma sugestão não aprovada; uma
fase sem contorno não exclui nódulos. O ITV sugerido é a união geométrica dos
contornos das fases selecionadas. Ele não confirma que os achados pertencem à
mesma lesão e não constitui um alvo de tratamento validado.</p>

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
ela roda no AUTO quando a anatomia identifica o tórax, nasce ligada
no PERSONALIZADO da TC, e o derrame pode ser entregue separadamente no FULL ou quando a ROI é pedida no PERSONALIZADO. O derrame pleural sai partido por lado — cada
voxel com o pulmão mais próximo naquele corte — e é descontado dos pulmões,
para o pulmão não contar o líquido como parênquima; o pericárdico entra no
coração de radioterapia (<code>Heart_ai</code>), e a descrição dele diz
quanto. No STUDY do AUTO, os pulmões saem sem o pleural, e o coração leva o
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
<p>O processamento dedicado depende de sua confirmação no diálogo de INICIAR.
Confira a lista de aplicativos e serviços antes de autorizar. Salve o trabalho aberto.
A Suite solicita o fechamento das janelas selecionadas. Uma janela que continuar aberta
permanece na estação. Um processo incluído sem janela pode ser encerrado se continuar
sem janela no momento da ação.
Navegadores exigem seleção própria. O navegador da Suite, os sistemas clínicos,
o acesso remoto, a segurança do Windows e as conexões de rede ficam protegidos.</p>
<p>Ao confirmar o <b>processamento dedicado</b>, você autoriza as ações exibidas na prévia. A segmentação pode usar prioridade acima do normal. Com permissão de administrador, o programa pode parar temporariamente serviços selecionados e previamente ativos, entre eles Windows Search (<code>WSearch</code>), <code>SysMain</code> e os serviços de atualização ou transferência <code>wuauserv</code>, <code>UsoSvc</code>, <code>DoSvc</code> e <code>BITS</code>, quando a situação do serviço permite. Transferências em andamento do BITS e do DoSvc e atualizações do sistema em andamento são preservadas. Pode reduzir a prioridade de aplicativos elegíveis e fechar aplicativos autorizados. O Windows continua gerenciando a memória dos demais programas. A rede da estação permanece disponível para acessar os exames e gravar as entregas. O diário registra as ações que precisam ser revertidas.</p>
<p>Os recursos disponíveis determinam quando e em qual dispositivo uma tarefa pode prosseguir. O esforço de processamento escolhido para a série continua valendo nas retomadas. A suíte registra o esforço da entrega para consulta no acervo local.</p>
<p>Quando a fila termina, ou fica pausada sem trabalho em curso, a sessão dedicada termina automaticamente. O turno Overnight e o rastreio contínuo acionados pelo operador permanecem ativos até seu encerramento. Ao encerrar a sessão dedicada, a suíte tenta restaurar as prioridades, iniciar os serviços que parou e reabrir os sincronizadores que fechou. Os demais aplicativos fechados podem ser reabertos pelo resumo. Se o motor cair, o supervisor tenta a restauração. Um erro transitório permite até duas novas tentativas após esperas de 3 e 10 segundos. O diário local guarda o que ficou pendente, inclusive de versões anteriores. O auxiliar encerra e a suíte pode retomar a devolução em uma próxima abertura.</p>
<p>O botão Diagnosticar fica em Configurações, em Diagnósticos e Registros, e grava as medidas de memória e de disco
em Downloads. Numa estação que usou uma versão anterior, ele apaga no arranque
o arquivo em que o otimizador de antes anotava o que tinha fechado (a
Política de Privacidade, seção 3) e o registro de um turno da noite que
pausava serviços (<code>_overnight_servicos.json</code>, na pasta do
programa), com uma linha no log: o programa que foi fechado volta no
próximo logon, e o serviço que ficou parado, no próximo arranque do
Windows.</p>
<ul>
 <li><b data-radai-t="1">O Overnight Run</b> — o turno da noite — entra na fila
 como o último cartão. «Cancelar» fecha a folha sem mudar nada. Ao abrir a
 folha, o programa só confere que as pastas existem e leem, sem gravar nelas.
 «Salvar e incluir na fila» guarda as pastas, as
 modalidades e os dias para trás, mas não inicia o turno nem a fila. É preciso
 clicar em <b>INICIAR</b>. O turno começa quando a fila chega no cartão
 autorizado; um cartão novo ou recuperado sem essa autorização espera.
 O botão «Adicionar pasta» permite escolher mais de uma origem. Ao salvar,
 o programa confere a leitura e a escrita de todas as pastas, criando e
 apagando um arquivo de teste; isso pode mudar a data da pasta. Sem escrita,
 nada é salvo e o motivo aparece. Com o turno aberto, o programa pede ao
 Windows para não suspender a estação. A descoberta começa pelas subpastas
 mais recentes; cada subárvore de exame concluída pode alimentar a fila
 enquanto as outras são descobertas, preservando a triagem por exame, o
 intervalo de espera de arquivos em trânsito e as travas entre estações.
 No AUTO, a fila usa a TC de simulação do exame ou, num exame sem TC,
 a RM do exame, pela mesma regra do vigia e do «Rodar agora». Trocar ROOT ou
 ROOTS com o turno aberto vale a partir do turno seguinte: o turno atual
 mantém as origens capturadas ao abrir. O pedido ao Windows para não
 suspender a estação vale mesmo com a fila vazia.
 Uma lista parcial nunca autoriza segmentar um volume incompleto. O botão
 «Interromper Overnight Run» para a descoberta e solicita o cancelamento da
 série em curso; as entregas já concluídas são preservadas. Encerrar o turno
 sem cancelar deixa a série em curso terminar. Nenhum outro programa é
 fechado e nenhum serviço de terceiros é pausado.</li>
 <li><b>A janela do programa.</b> Aberto pelo atalho, o programa abre o
 navegador em modo de aplicativo, maximizado com as barras do Windows
 visíveis, no perfil próprio <code>%LOCALAPPDATA%\\RADIOTERAPIA_AI\\janela</code> ou no perfil anterior reconhecido. O botão
 «Maximizar» da porta pede explicitamente a tela cheia pelo F11 e passa a
 «Restaurar»; o F11 também permite sair dela. Para controlar a janela, o
 motor a acha pelo título que termina na ficha da tela; se isso não basta,
 confere a linha de comando do processo do navegador. Nenhuma janela de abas
 da pessoa é tocada; a janela guardada é reconferida pelo processo e classe.
 O F11 só é enviado por pedido explícito. «Minimizar» afeta apenas a janela
 do programa. O log informa o método de identificação sem título nem ficha.</li>
 <li><b>A atualização com um clique.</b> O «Atualizar agora» — no aviso de
 versão nova da porta e no cartão «Atualizar o programa» de Configurações —
 baixa o instalador da release, confere a soma SHA-256 que a release publica
 e, se só o código muda, abre uma console com cinco etapas: pacote e destino,
 teste de escrita e encerramento das janelas próprias e do motor, cópia e
 limpeza dos caches do código, atalhos e reabertura. Só anuncia «ATUALIZADO»
 depois de confirmar o painel da versão esperada em um processo novo e numa
 janela própria visível, com a sua configuração preservada; a console fecha
 após 5 segundos. Se falhar, o diagnóstico fica na console. Uma cópia
 incompleta não é reaberta automaticamente: é preciso corrigir o motivo e
 executar o instalador novamente. Com
 a série do vigia, o lote do «Rodar agora» ou o turno da noite em andamento,
 ele espera ou pergunta antes; e, quando a versão nova precisa de um pacote
 novo de modelos, a tela diz o tamanho e o tempo estimado e pede uma segunda
 confirmação antes de abrir o preparador da versão nova. A Política de
 Privacidade (seção 4) diz o que ele baixa e de onde.</li>
 <li><b>Levar as configurações para outra máquina.</b> Em Configurações, o
 «Exportar configurações» baixa um <code>.json</code> com o arquivo de
 configuração da estação — sem o que é desta máquina: a placa, o
 dispositivo, a porta e a marca do guia —, os nomes e cores próprios e os protocolos
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
(<a href="https://github.com/drhenriquebraga/local-suite/security">drhenriquebraga/local-suite</a>,
aba Security), nunca numa issue pública e nunca com dado de paciente.</p>
</div><p><b>NEURO RT opcional.</b> O plugin é instalado separadamente, por pedido
 explícito, com seus avisos e licenças próprios no instalador e no primeiro uso.
 O protocolo de SNC em RM exige série compatível, recursos instalados e o aceite próprio do NEURO RT. O Vigia pode acioná-lo no AUTO. Resultados continuam como sugestões
 não aprovadas e a aprovação pertence ao operador no TPS.</p>
<p>Nas configurações, Verificar atualizações consulta a versão publicada sob
 demanda, sem iniciar a instalação. Se o decisor de atualização falhar, é
 possível abrir o instalador já baixado e verificado para seguir o preparo guiado.</p>
</body></html>"""


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

    @app.get("/licencas-ferramentas", response_class=HTMLResponse)
    def _licencas():
        import radai_bibliography
        return radai_bibliography.pagina_com_menu("termos")

    @app.get("/api/aceite")
    def _estado():
        try:
            impressao = impressao_dos_documentos()
        except Exception:
            impressao = u""
        return {"aceito": aceito(), "versao": VERSAO_DOCS, "data": DATA_DOCS,
                "impressao": impressao, "catalogo_sha256": catalogo_termos.catalogo()[0],
                "opcionais": catalogo_termos.grupos_opcionais(),
                "nomes_opcionais": catalogo_termos.NOMES_OPCIONAIS,
                "pontos": [{"chave": c, "titulo": t, "detalhe": d,
                            "sinal": sinal_do_ponto(c)}
                           for (c, t, d) in PONTOS],
                "fontes": fontes_de_terceiros(),
                "registro": aceite()}

    @app.post("/api/aceite")
    async def _registrar(request: Request):
        try:
            c = await request.json() or {}
            if c.get("impressao") != impressao_dos_documentos():
                return {"erro": "Os documentos mudaram. Recarregue a página."}
            return await radai_web.no_threadpool(
                registrar_aceite, c.get("quem", ""), c.get("itens"),
                c.get("catalogo_sha256"), c.get("ensino_pesquisa"), c.get("ferramentas_opcionais", []))
        except Exception as e:
            return {"erro": "%s: %s" % (type(e).__name__, e)}


LIVRES = ("/aceite", "/termos", "/politica-privacidade", "/creditos",
          "/licencas-ferramentas", "/favicon.ico", "/radai-idiomas.js")

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
.ac #ac_opcionais h2{font-size:1.02rem;margin:20px 0 6px}
.ac #ac_opcionais p{color:var(--text-muted,#a3b1c6);font-size:.87rem}
.ac .ac-ferramenta{padding:.35rem 0;align-items:baseline}
.ac .ac-ferramenta a{margin-inline-start:auto;color:var(--accent,#4da3ff);font-size:.83rem}
.ac #ac_todos{color:var(--accent,#4da3ff);background:none;border:0;padding:.4rem 0;cursor:pointer;text-decoration:underline}
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

<p class="pp">A Local Suite integra modelos de terceiros para ensino e pesquisa. Os componentes são baixados das fontes dos autores e executados localmente. Os contornos gerados são sugestões experimentais.</p>
<p class="pp">Quando os autores publicam um peso sem indicar licença própria, essa condição aparece
na ficha. Para usos que dependem de autorização adicional, consulte o titular nos links da ficha.</p>
<details id="ac_catalogo" data-impressao="@CATALOGO_SHA@" data-documentos="@DOC_SHA@"><summary>Consultar todos os modelos, ferramentas e licenças</summary>
<button type="button" id="ac_todos" hidden>Mostrar todos os componentes</button>
@CATALOGO@</details>
<section id="ac_opcionais"><h2>Termos de ferramentas opcionais</h2>
<p>O aceite abrange as ferramentas abaixo. A instalação de cada ferramenta é uma escolha separada.</p><div id="ac_ferramentas"></div></section>
<div class="mudou" id="ac_mudou" style="display:none"></div>

<div class="pontos" id="ac_pontos"></div>

<p class="pp" data-radai-frase>Para procurar uma versão da suíte ou dos plugins, escolha Verificar atualizações em Configurações. O registro de casos não testa a conexão com a internet.</p>
<p class="pp" data-radai-frase>O Vigia acompanha as pastas escolhidas enquanto está ligado. No modo dedicado, você autoriza as ações exibidas para os aplicativos e serviços da estação. O perfil da janela e o diário de recuperação ficam no perfil local do Windows.</p>
<p class="pp" data-radai-frase>Ao confirmar, declaro que li os Termos de Uso e a Política de Privacidade 3.3 e aceito as condições de uso para ensino e pesquisa. As ferramentas opcionais mantêm suas condições e autorizações específicas.</p>

<p class="docs">
 <a href="/termos" target="_blank" rel="noopener">Termos de uso</a>
 <a href="/politica-privacidade" target="_blank" rel="noopener">Pol&iacute;tica
 de privacidade</a>
 <a href="/creditos" target="_blank" rel="noopener">Cr&eacute;ditos e
 licen&ccedil;as</a>
 <a href="/licencas-ferramentas" target="_blank" rel="noopener">Catálogo de ferramentas e licenças</a>
</p>

<div><button class="bt" id="ac_bt" disabled onclick="acEntrar()"
 data-radai-frase>Aceito os Termos e a Política 3.3</button></div>
<p class="msg" id="ac_msg"></p>

<p class="mini">O aceite fica registrado nesta esta&ccedil;&atilde;o, com data
e nome da m&aacute;quina. <b>Ele n&atilde;o interrompe um vigia que j&aacute;
esteja rodando</b> &mdash; travar o lote da noite por uma vers&atilde;o nova de
documento derrubaria a esta&ccedil;&atilde;o de madrugada, em
sil&ecirc;ncio.</p>

</div><script>
var AC_PONTOS = [];
var AC_CATALOGO = document.getElementById('ac_catalogo').dataset.impressao;
var AC_DOCUMENTOS = document.getElementById('ac_catalogo').dataset.documentos;
var AC_FERRAMENTAS = [];
var AC_PRONTO = false;
function acEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;')
 .replace(/</g,'&lt;').replace(/>/g,'&gt;')}

fetch('/api/aceite').then(function(r){return r.json()}).then(function(d){
 if(!AC_DOCUMENTOS || AC_DOCUMENTOS!==d.impressao || !AC_CATALOGO || AC_CATALOGO!==d.catalogo_sha256){throw new Error('Catálogo alterado');}
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
 var r = d.registro || {};
 const op=document.getElementById('ac_ferramentas');
 const alvo=new URLSearchParams(location.search).get('ferramenta');
 const fichas=Array.from(document.querySelectorAll('.lic-item')), todos=document.getElementById('ac_todos');
 todos.onclick=function(){fichas.forEach(x=>x.hidden=false);todos.hidden=true;};
 AC_FERRAMENTAS=d.opcionais;
 AC_FERRAMENTAS.forEach(function(f){
  const ficha=fichas.find(x=>x.dataset.ferramenta===f);
  if(!ficha) throw new Error('Catálogo alterado');
  const linha=document.createElement('div'), visto=document.createElement('span'), nome=document.createElement('b');
  linha.className='pt ac-ferramenta';visto.className='v';visto.textContent='✓';visto.setAttribute('aria-hidden','true');
  nome.textContent=d.nomes_opcionais[f] || f;
  const link=document.createElement('a');link.href='#'+ficha.id;link.textContent='Consultar termos';
  link.addEventListener('click',function(){document.getElementById('ac_catalogo').open=true;
   fichas.forEach(x=>x.hidden=x.dataset.ferramenta!==f);todos.hidden=false;ficha.open=true;});
  linha.append(visto,nome,link);op.append(linha);
  if(f===alvo){
   document.getElementById('ac_catalogo').open=true;
   fichas.forEach(x=>x.hidden=x.dataset.ferramenta!==f); todos.hidden=false; ficha.open=true;
   link.focus();
  }
 });
 AC_PRONTO=AC_PONTOS.length>0;
 document.getElementById('ac_bt').disabled=!AC_PRONTO;
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

function acEntrar(){
 if(!AC_PRONTO || document.getElementById('ac_bt').disabled){return;}
 var bt = document.getElementById('ac_bt'), msg = document.getElementById('ac_msg');
 bt.disabled = true; msg.style.color = 'var(--text-dim,#72829b)';
 acMsg('registrando…');
 fetch('/api/aceite', {method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({quem: '',
                        itens: AC_PONTOS, ensino_pesquisa:true, catalogo_sha256:AC_CATALOGO,
                        impressao:AC_DOCUMENTOS, ferramentas_opcionais:AC_FERRAMENTAS})})
 .then(function(r){return r.json()}).then(function(d){
  if(d.erro){ acFalhou(d.erro); return }
  var busca=new URLSearchParams(location.search);
  if(busca.get('contexto')==='processamento'){
   acMsg('Aceite registrado.'); window.close(); return;
  }
  var p = busca.get('de') || '';
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
 if(bt) bt.disabled = !AC_PRONTO;
}
</script></body></html>"""


def pagina_aceite():
    css = CSS_ACEITE
    try:
        import radai_ui
        css = radai_ui.TOKENS + CSS_ACEITE
    except Exception:
        pass
    pagina = (PAGINA_ACEITE.replace("@CSS@", css + catalogo_termos.CSS)
              .replace("@CATALOGO_SHA@", catalogo_termos.catalogo()[0])
              .replace("@DOC_SHA@", impressao_dos_documentos()))
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
    return pagina.replace("@CATALOGO@", catalogo_termos.bloco(compacto=True))


def montar_portao(app):
    from starlette.responses import JSONResponse, RedirectResponse

    try:
        impressao_dos_documentos()
    except Exception:
        pass

    @app.middleware("http")
    async def _portao(request, call_next):
        try:
            caminho = request.url.path or "/"
            if request.method == "POST" and caminho in (
                    "/api/plugins/lung-rt/install", "/api/plugins/neuro-rt/install",
                    "/api/plugins/neuro-rt/update"):
                grupo = caminho.split("/")[3]
                if not ferramenta_autorizada(grupo):
                    return JSONResponse({"erro":"Consulte e aceite os termos deste plugin antes de instalar.",
                                         "detail":{"code":"TERMS_REQUIRED",
                                                   "message":"Aceite os termos do plugin em Ferramentas e licenças."},
                                         "aceite":"/aceite?ferramenta="+grupo+"&de=/config"}, status_code=409)
            # Leituras, cancelamentos e acompanhamento de um lote já iniciado
            # continuam disponíveis. Começar uma nova execução exige o aceite atual.
            if request.method == "POST" and caminho in (
                    "/api/plugins/coronarias/ativar", "/api/plugins/coronarias/importar",
                    "/api/vigia/ligar", "/api/overnight/iniciar", "/api/pipeline/iniciar",
                    "/api/lote/enfileirar", "/api/lote/refazer_pos", "/api/lote/iniciar"):
                if not aceito():
                    return JSONResponse({"erro":"Aceite os termos de ensino e pesquisa antes de iniciar.",
                                         "aceite":"/aceite"}, status_code=409)
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
            return JSONResponse({"erro":"Não foi possível conferir o aceite nesta estação.",
                                 "aceite":"/aceite"}, status_code=503)
        return await call_next(request)
