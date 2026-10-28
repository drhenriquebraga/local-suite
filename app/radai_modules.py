# -*- coding: utf-8 -*-
import math

CORES = {
    "bridge": ("--mod-bridge", "--mod-bridge-fraco"),
    "autocontorno": ("--mod-auto", "--mod-auto-fraco"),
    "recon3d": ("--mod-recon", "--mod-recon-fraco"),
    "nidus": ("--mod-nidus", "--mod-nidus-fraco"),
    "elastic": ("--mod-elastic", "--mod-elastic-fraco"),
    "bolus": ("--mod-bolus", "--mod-bolus-fraco"),
}

MODULOS = {
    "bridge": {
        "icone": u"ponte",
        "titulo": u"Dicom", "destaque": u"Bridge",
        "frase": (u"Diagnostica e transforma arquivos para a travessia do exame "
                  u"externo ao sistema de planejamento"),
        "linha": u"Processamento <b>100% local</b>",
    },
    "autocontorno": {
        "icone": u"contornos",
        "titulo": u"Contour", "destaque": u"Lab",
        "frase": (u"Vários modelos sobre o mesmo exame, lado a lado — para "
                  u"ver no que eles concordam, e onde discordam."),
        # GUARDA: a linha diz só "material de estudo" e o local; a frase de
        # não-aprovação mora no `?` do título e no aviso do INICIAR
        # (`radai_review`), e `tools/test_credits.py` cobra os dois lugares.
        "linha": (u"Material de estudo &mdash; <b>100% local</b>. Nenhuma imagem "
                  u"sai desta rede"),
    },
    "recon3d": {
        "icone": u"cubo",
        "titulo": u"Reconstruções ", "destaque": u"3D",
        "frase": (u"Carregue os casos segmentados pelo módulo ContourLab para "
                  u"análise tridimensional"),
        "linha": u"<b>Uso pr&oacute;prio</b> dentro do app",
    },
    "nidus": {
        "icone": u"cruzamento",
        "titulo": u"Nidus ", "destaque": u"RT",
        "frase": (u"A mesma lesão em duas incidências, e onde as duas se "
                  u"cruzam — a lógica da angiografia biplanar."),
        "linha": (u"Constru&ccedil;&atilde;o geom&eacute;trica a partir do "
                  u"desenho do usu&aacute;rio &mdash; <b>n&atilde;o &eacute; "
                  u"um volume de tratamento</b>"),
    },
    "elastic": {
        "icone": u"malha",
        "titulo": u"Elastic ", "destaque": u"RT",
        "frase": (u"O que a deforma\u00e7\u00e3o fez entre duas s\u00e9ries "
                  u"\u2014 e se ela era poss\u00edvel num paciente."),
        "linha": (u"Sugest&atilde;o n&atilde;o aprovada &mdash; e "
                  u"<b>a imagem n&atilde;o sai sem o laudo</b> do campo"),
    },
    "bolus": {
        "icone": u"camadas",
        "titulo": u"3D Printed ", "destaque": u"Bolus",
        "frase": (u"Uma caixa no MPR, uma camada sobre a pele, e os STL para "
                  u"imprimir: o bólus e o molde dele, para pesquisa, fantoma "
                  u"e ensino, e o aplicador de superfície para braquiterapia, "
                  u"um acessório de tratamento que só sai como rascunho."),
        "linha": (u"O STL sai por <b>ato declarado</b>, como rascunho sujeito a "
                  u"revis&atilde;o f&iacute;sica e m&eacute;dica &mdash; a "
                  u"<b>dosimetria do material</b> &eacute; obrigat&oacute;ria"),
    },
}


ANUNCIOS = ()

EM_DESTAQUE = frozenset()

NAO_NAVEGAM = (u"EM CONSTRUÇÃO", u"EM BREVE")


def nao_navega(estado):
    e = (estado or u"").upper()
    return any(e.startswith(x[:8]) for x in NAO_NAVEGAM)

FERRAMENTAS = {
    "bridge": [
        ("bridge_laudo", u"exportar", u"Converter imagens para o TPS", "/bridge/laudo",
         u"TPS não lê o exame externo? Carregue o estudo, escolha as séries e a "
         u"segmentação de cada uma, veja o diagnóstico e receba a série DICOM "
         u"pronta numa pasta nova.", u"",
         (u"várias séries", u"diagnóstico", u"segmentação na fila",
          u"JPEG e PNG", u"CD")),
    ],
    "autocontorno": [
        # GUARDA: o cartão não nomeia modo; os três (FAST, AUTO,
        # PERSONALIZADO) estão no `?` do ContourLab, e `tools/test_suite.py`
        # (seção 11) compara o `?` com os rótulos da tela (`radai_batch`).
        ("lote", u"rodar", u"Rodar agora", "/lote",
         u"Realiza segmentação de imagens de Tomografia e Ressonância. "
         u"Personalize o seu estudo de acordo com topografias, tasks "
         u"(plugins) e diferentes modelos.", u""),
        ("ver", u"olho", u"Ver segmentação", "/ver",
         u"Avalie os resultados comparando diferentes processamentos em "
         u"cortes axiais lado a lado, e veja como eles se comportam.", u""),
    ],
    "recon3d": [
        ("recon_anatomia", u"cubo", u"Anatomia geral", "/recon3d/anatomia",
         u"Visualize cada órgão, com ajuste de transparências no visor 3D, "
         u"além da segmentação nos 3 planos (axial, sagital e coronal) e MIP "
         u"e MinIP com laje ajustável.", u"",
         (u"3D", u"MIP", u"MinIP", u"laje 1-100 mm"),
         u"Carrega a série inteira em memória, uma vez. Numa estação com o "
         u"vigia rodando, espere alguns segundos e alguns GB."),
        ("recon_torax", u"pulmoes", u"Anatomia torácica", "/recon3d/toracica",
         u"Reconstrução das tarefas geradas pelo protocolo do ContourLab: "
         u"Lobos, mediastino, vascularização, algoritmo de nódulos pulmonares "
         u"e muito mais.", u"",
         (u"3D", u"estudo torácico", u"desenho no axial")),
        ("recon_vascular", u"vaso", u"Vascular", "/recon3d/vascular",
         u"Superfície, trajeto dos vasos e projeções bidimensionais "
         u"sintéticas a partir da segmentação de vasos", u"",
         (u"angiografia sintética", u"3D", u"MIP")),
    ],
    "nidus": [
        ("nidus_projecao", u"cruzamento", u"Projeção Vascular", "/nidus/projecao",
         u"Projeta a angiotomografia, ou a RM com gadolínio, na incidência "
         u"escolhida; o médico circula, e a área vira um tubo. Dois tubos se "
         u"cruzam.", u"",
         (u"MIP", u"incidência livre", u"TC e RM", u"sem exportação")),
    ],
    "elastic": [
        ("elastic_fusao", u"malha", u"Fus\u00e3o el\u00e1stica",
         "/elastic/fusao",
         u"Registra duas s\u00e9ries do mesmo paciente \u2014 TC, RM ou "
         u"PET; r\u00edgido e depois deform\u00e1vel \u2014 e mede o campo: "
         u"jacobiano, ida-e-volta e deslocamento, com a grade deformada por "
         u"cima da imagem e o laudo ao lado.", u"",
         (u"TG-132", u"B-spline", u"sem propaga\u00e7\u00e3o")),
    ],
    # GUARDA: a faixa da espessura e o molde vão nas TAGS do cartão, com
    # os números do motor (`radai_bolus.ESPESSURA_MIN_MM` e vizinhas);
    # `tools/test_suite.py` lê as tags: mudou a faixa, o cartão reprova.
    "bolus": [
        ("bolus_gerar", u"camadas", u"Gerar bólus", "/bolus/gerar",
         u"Defina um volume sobre a superfície e defina a região do bólus. "
         u"Ajuste para espessura anatômica, bloco em caixa projetado ou molde "
         u"(casca) para preenchimento com material de cera. Exporte em STL "
         u"para dosimetria.", u"",
         (u"STL", u"molde", u"aplicador de superfície", u"camada 1-30 mm")),
    ],
}

AJUDA = {
    "home": {
        u"O que não faz": (
            u"Nada é aprovado automaticamente: toda estrutura sai <b>_ai</b> "
            u"e <b>UNAPPROVED</b>.",
            u"Nenhuma biblioteca de achado vem ligada: de fábrica, só "
            u"anatomia. Detecção existe e roda por <b>ato declarado de quem "
            u"opera</b> — e nenhuma imagem sai desta estação."),
        u"Componentes de terceiros": (
            u"<b>TotalSegmentator</b> — Apache-2.0.",
            u"A lista completa, com a licença de cada um, está em "
            u"<b>Créditos</b> — ela sai do registro de modelos, e não de "
            u"um texto escrito à mão aqui."),
    },
    "bridge": {
        u"O que não faz": (
            u"Não reamostra corte e não descarta duplicata. Série DICOM "
            u"atravessa com o UID e o Frame of Reference que trouxe, menos a "
            u"colorida, que sai com UID novo, a de geometria assumida, que "
            u"sai com UID e Frame of Reference novos, e a sem Frame of "
            u"Reference, que ganha um próprio. E não grava corte incompleto: "
            u"a série que tem um é recusada inteira.",
            u"Não promete Hounsfield no que ele converte de imagem: o cinza "
            u"de um JPEG é nível de exibição. E a série convertida nasce com "
            u"Frame of Reference próprio, para o sistema de planejamento "
            u"exigir um registro em vez de supor que ela já está alinhada.",
            u"Não marca, não realça e não lista achado: mostra a imagem e o "
            u"cabeçalho."),
        u"Componentes de terceiros": (
            u"Leitura e escrita DICOM por <b>pydicom</b> (MIT); a miniatura é "
            u"PNG escrito com <b>zlib</b>, sem dependência de imagem.",),
        u"processamento local": (
            u"O caminho da pasta fica no processo; a miniatura viaja por um "
            u"bilhete opaco, nunca pelo caminho do paciente na URL. Nenhuma "
            u"imagem sai da estação.",),
    },
    "autocontorno": {
        u"O que não faz": (
            u"Não aprova nada: toda estrutura sai <b>_ai</b> e "
            u"<b>UNAPPROVED</b>.",
            u"Não roda biblioteca de achado por omissão: o FAST, o AUTO e a "
            u"noite rodam a base e as tarefas da região que a anatomia "
            u"mostrou, e nenhum protocolo RT do PERSONALIZADO arrasta uma de "
            u"achado. Ligar detecção é escolha declarada: a chave da própria "
            u"tarefa no PERSONALIZADO de uma série, ou um protocolo de estudo "
            u"das Reconstruções 3D, cuja saída não vai ao TPS.",
            u"Não manda imagem para a nuvem: a segmentação roda nesta "
            u"estação."),
        u"Componentes de terceiros": (
            u"<b>TotalSegmentator</b> — Apache-2.0. Faz o fluxo principal.",
            u"A lista completa, com a licença de cada um, está em "
            u"<b>Créditos</b> — ela sai do registro de modelos, e não de "
            u"um texto escrito à mão aqui.",
            u"Quem reconhece o órgão é terceiro. O que construímos é a camada "
            u"de acessibilidade."),
    },
    "recon3d": {
        u"O que não faz": (
            u"Não segmenta: consome o que o ContourLab já produziu.",
            u"<b>Não exporta</b> malha nem estrutura. Uso próprio, dentro do "
            u"app."),
        u"Componentes de terceiros": (
            u"Projeção MIP/MinIP em numpy. O 3D é a malha de cada estrutura, "
            u"montada neste programa (a mesma superfície do bólus) sobre a "
            u"distância do <b>scipy.ndimage</b> (BSD-3), e desenhada em WebGL "
            u"próprio, sem biblioteca de terceiros; sem WebGL, uma nuvem de "
            u"pontos em canvas 2D. As máscaras vêm do TotalSegmentator, "
            u"Apache-2.0.",),
    },
    "nidus": {
        u"O que não faz": (
            u"Não detecta e não segmenta: projeta o que o médico circulou. "
            u"Nada aqui é aprendido.",
            u"<b>Não exporta</b> e <b>não calcula volume</b> — a interseção é "
            u"uma construção de visualização, e um número em cm³ ao lado dela "
            u"seria um volume de alvo com passos a mais.",
            u"Não substitui angiografia digital: na angioTC, e na RM com "
            u"gadolínio, a veia de drenagem realça como a artéria nutridora. "
            u"E na RM o sinal não é HU: a janela é relativa à própria série."),
        u"Componentes de terceiros": (
            u"Reamostragem e projeção com <b>SimpleITK</b> (Apache-2.0) e "
            u"<b>numpy</b>; o PNG é escrito com <b>zlib</b>, sem dependência "
            u"de imagem.",
            u"Nenhum modelo. Este módulo não usa IA — é geometria."),
    },
    "elastic": {
        u"O que não faz": (
            u"<b>Não propaga contorno.</b> Ele mostra e mede a deformação; "
            u"não move estrutura de uma série para a outra. Estrutura "
            u"propagada chega ao plano com aparência de contorno conferido.",
            u"Não é segunda opinião contra outro programa: o campo deformável "
            u"de outros sistemas raramente é exportado em formato aberto. O que "
            u"se mede é a transformação contra ela mesma.",
            u"Não detecta e não classifica nada — é registro de imagem."),
        u"Componentes de terceiros": (
            u"Registro, campo, jacobiano e inversão com <b>SimpleITK</b> "
            u"(Apache-2.0); o PNG é escrito com <b>zlib</b>.",
            u"As métricas seguem o <b>AAPM TG-132</b> (Brock et al., Med "
            u"Phys 2017). Os <b>limiares são deste aplicativo</b> — o TG-132 "
            u"pede QA por caso e não publica limiar universal.",
            u"Nenhum modelo e nenhum peso. Este módulo não usa IA."),
    },
    "bolus": {
        u"O que não faz": (
            u"<b>O bólus não é para uso clínico.</b> A densidade varia com o "
            u"filamento, e a atenuação do material tem de ser medida antes de "
            u"qualquer uso — o programa não a conhece.",
            u"<b>O aplicador de superfície é acessório de tratamento.</b> Um "
            u"canal mal desenhado pode prender o cateter ou deslocar a "
            u"posição de parada da fonte. Ele sai como rascunho sujeito a "
            u"revisão física e médica, e nada nele está aprovado: antes de "
            u"tratar, segunda TC com o aplicador posto e plano novo feito "
            u"sobre ela, e teste de passagem com o cabo de checagem em cada "
            u"canal.",
            u"Não grava RTSTRUCT e não calcula dose. Para o plano considerar a "
            u"peça, o físico faz uma TC com ela posta.",
            u"Não é para TC de simulação com máscara: a peça fica sobre a "
            u"pele, numa TC diagnóstica recente. RM é recusada — sem "
            u"Hounsfield não há pele a medir."),
        u"Componentes de terceiros": (
            u"Leitura e reamostragem com <b>SimpleITK</b> (Apache-2.0); campo "
            u"de distância e suavização com <b>scipy.ndimage</b> (BSD-3) e "
            u"<b>numpy</b>. A superfície, o molde e os STL são escritos neste "
            u"programa.",
            u"O 3D foi portado do reconstrutor do DeFace RT, do mesmo autor. "
            u"Nenhum modelo e nenhum peso: este módulo não usa IA."),
    },
}


SEM_EXPORTACAO = {
    "recon3d": (
        u'<p class="md-semexp">Esta tela <b>n&atilde;o exporta</b> malha nem '
        u'estrutura. Reconstru&ccedil;&atilde;o exportada como malha sai do '
        u'nosso ambiente e pode ser levada ao centro cir&uacute;rgico; '
        u'bot&atilde;o de exportar malha &eacute; uma declara&ccedil;&atilde;o '
        u'de uso pretendido, e uso pretendido define '
        u'classifica&ccedil;&atilde;o regulat&oacute;ria. Dentro do app '
        u'&eacute; uso pr&oacute;prio. O RTSTRUCT do ContourLab continua '
        u'exportando normalmente.</p>'),
    "nidus": (
        u'<p class="md-semexp">A interse&ccedil;&atilde;o &eacute; uma '
        u'<b>constru&ccedil;&atilde;o geom&eacute;trica</b> a partir do '
        u'desenho do usu&aacute;rio &mdash; n&atilde;o &eacute; um volume de '
        u'tratamento. Ela n&atilde;o exporta, e esta tela <b>n&atilde;o '
        u'calcula nem exibe o volume dela em cm&sup3;</b>: um n&uacute;mero '
        u'ao lado de uma forma &eacute; um volume de alvo com passos a mais. '
        u'A constru&ccedil;&atilde;o vira n&uacute;mero, o n&uacute;mero vira '
        u'registro, e o registro vira a coisa que se compara com o plano.</p>'
    ),
    "elastic": (
        u'<p class="md-semexp">Este m&oacute;dulo <b>n&atilde;o propaga '
        u'contorno</b> e n&atilde;o grava RTSTRUCT. Ele mostra e mede a '
        u'deforma&ccedil;&atilde;o; levar uma estrutura de uma s&eacute;rie '
        u'para a outra por um campo que ningu&eacute;m conferiu &eacute; '
        u'exatamente o que o TG-132 existe para evitar. E a imagem fundida '
        u'<b>n&atilde;o &eacute; servida sem o laudo do campo</b>: uma '
        u'fus&atilde;o el&aacute;stica sempre produz imagem convincente, '
        u'inclusive quando dobrou o paciente.</p>'
    ),
    "bolus": (
        u'<p class="md-semexp">Este m&oacute;dulo <b>exporta um STL</b> por '
        u'pe&ccedil;a &mdash; o b&oacute;lus e, se pedido, o molde &mdash; e, '
        u'para o aplicador de superf&iacute;cie, um .zip com o STL e a ficha; '
        u's&oacute; por <b>ato declarado a cada exporta&ccedil;&atilde;o</b>: '
        u'rascunho sujeito a revis&atilde;o f&iacute;sica e m&eacute;dica. '
        u'O aplicador &eacute; <b>acess&oacute;rio de tratamento</b>: antes '
        u'de tratar, segunda TC com ele posto, plano novo feito sobre ela e '
        u'teste de passagem com o cabo de checagem em cada canal. '
        u'N&atilde;o grava RTSTRUCT &mdash; estrutura de b&oacute;lus &eacute; '
        u'de uso dosim&eacute;trico direto, a mesma fam&iacute;lia do BODY que '
        u'este programa n&atilde;o entrega. O plano considera a pe&ccedil;a '
        u'pela TC feita com ela posta.</p>'
    ),
}


def _esc(t):
    return (str(t or "").replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;").replace(u'"', u"&quot;"))


CSS = u"""
@font-face{font-family:Anton;src:url('/porta/Anton-Regular.ttf') format('truetype');font-display:swap;font-weight:400}
body{margin:0}
body[data-tela="autocontorno"] .wrap:has(.md-pg){max-width:none;margin:0;width:100%}
.md-pg{--md-topo:clamp(24px,calc(34vh - 86px),240px);position:relative;isolation:isolate;
 box-sizing:border-box;display:flex;flex-direction:column;overflow-x:clip;
 min-height:calc(100dvh - var(--ui-topo,60px));padding:36px clamp(24px,5vw,68px) 22px}
.md-pg::before{content:'';position:absolute;inset:0;z-index:-2;pointer-events:none;
 background:radial-gradient(ellipse at 8% 48%,rgba(23,52,91,.2),transparent 57%),
  radial-gradient(ellipse at 84% 8%,rgba(51,38,77,.09),transparent 48%)}
.md-palco{position:relative;display:grid;align-items:start;gap:34px 42px;
 grid-template-columns:minmax(250px,.9fr) minmax(0,1.65fr);padding-top:var(--md-topo)}
.md-n3 .md-palco{grid-template-columns:minmax(0,1fr)}
.md-intro{position:relative;min-width:0}
.md-n3 .md-intro{display:flex;align-items:center;gap:30px}
.md-tit{display:flex;align-items:center;gap:14px}
.md-tit h1{margin:0;font:400 61px/1.08 Anton,'Arial Narrow',sans-serif;letter-spacing:.1px;
 color:var(--text);flex:0 1 auto;min-width:0;text-wrap:balance}
.md-tit .ui-ajuda{flex:0 0 auto}
.md-tit h1 .ls-fim{background:var(--nome-grad);-webkit-background-clip:text;
 background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
.md-tit .ui-ajuda{width:20px;height:20px;font-size:12px}
.md-tit .ui-balao{width:min(460px,72vw);max-height:60vh;overflow:auto;line-height:1.6}
.md-tit .ui-ajuda.dir .ui-balao{left:0;right:auto;transform-origin:top left}
:root[dir="rtl"] .md-tit .ui-ajuda.dir .ui-balao{left:auto;right:0;transform-origin:top right}
.md-tit .ui-balao p{margin:0 0 8px}
.md-tit .hm-aj-t{display:block;margin:12px 0 4px;
 font:700 10px/1 var(--font-mono,monospace);letter-spacing:.12em;
 text-transform:uppercase;color:var(--md-cor,var(--accent))}
.md-tit .ui-balao p:first-child .hm-aj-t{margin-top:0}
.md-simbolo{width:92px;height:92px;margin-top:45px;color:rgba(138,184,223,.42)}
.md-n3 .md-simbolo{width:58px;height:58px;margin:0}
.md-simbolo svg{display:block;width:100%;height:100%}
.md-simbolo .ls-detalhe{stroke-width:.9}
.md-feixe{position:absolute;z-index:-1;pointer-events:none;left:-7%;width:114%;
 top:calc(var(--md-topo) - 22px);height:280px;opacity:.7}
.md-n3 .md-feixe{top:calc(var(--md-topo) + 110px)}
.md-feixe path{vector-effect:non-scaling-stroke}
.md-feixe .f0{stop-color:rgba(64,156,255,0)}
.md-feixe .f1{stop-color:rgba(112,210,255,.8)}
.md-feixe .f2{stop-color:rgba(160,136,237,.8)}
.md-feixe .f3{stop-color:rgba(157,184,239,0)}

.md-grade{position:relative;z-index:1;display:grid;align-items:stretch;gap:20px;
 grid-template-columns:repeat(2,minmax(0,1fr))}
.md-n1 .md-grade{grid-template-columns:minmax(0,420px)}
.md-n3 .md-grade{grid-template-columns:repeat(3,minmax(0,1fr))}
.md-fer{position:relative;isolation:isolate;overflow:hidden;display:flex;flex-direction:column;
 box-sizing:border-box;min-height:227px;padding:26px 25px 22px;border-radius:15px;
 border:1px solid rgba(181,185,192,.26);color:inherit;text-decoration:none;
 background:linear-gradient(120deg,rgba(159,191,230,.063),rgba(27,42,71,.14) 55%,rgba(147,137,187,.047));
 -webkit-backdrop-filter:blur(9px);backdrop-filter:blur(9px);
 box-shadow:0 17px 40px rgba(0,0,0,.2);
 transition:transform 220ms cubic-bezier(.23,1,.32,1),border-color 200ms ease,
  background 200ms ease,box-shadow 200ms ease}
.md-fer::before{content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;
 box-shadow:inset 0 1px rgba(242,215,169,.23);opacity:.6;transition:opacity 180ms ease}
.md-fer::after{content:'';position:absolute;inset:-60% -100%;z-index:-1;pointer-events:none;
 background:linear-gradient(110deg,transparent 45%,rgba(244,214,163,.07) 50%,transparent 55%);
 transform:translateX(-35%);opacity:0}
a.md-fer:hover,a.md-fer:focus-visible{border-color:rgba(214,188,143,.66);
 background:linear-gradient(120deg,rgba(172,201,227,.11),rgba(38,53,81,.2) 55%,rgba(179,150,195,.082));
 box-shadow:0 18px 38px rgba(0,0,0,.27);transform:translateY(-3px)}
a.md-fer:hover::before,a.md-fer:focus-visible::before{opacity:1;
 box-shadow:inset 0 1px rgba(242,215,169,.72)}
a.md-fer:hover::after{opacity:1;transform:translateX(35%);
 transition:transform 650ms cubic-bezier(.23,1,.32,1),opacity 150ms ease}
a.md-fer:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.md-visual{position:absolute;right:16px;top:14px;width:92px;height:92px;pointer-events:none;
 color:var(--md-cor,var(--accent));opacity:.15;
 transition:transform 350ms cubic-bezier(.23,1,.32,1),opacity 220ms ease}
.md-visual svg{display:block;width:100%;height:100%;stroke-width:.65}
a.md-fer:hover .md-visual,a.md-fer:focus-visible .md-visual{opacity:.3;
 transform:translateY(-2px) scale(1.08)}
.md-fer .ic{display:block;width:24px;height:24px;color:var(--md-cor,var(--accent))}
.md-fer .ic svg{display:block;width:24px;height:24px}
.md-fer .cab{display:flex;align-items:center;flex-wrap:wrap;gap:8px 10px;margin-top:22px;
 padding-right:56px}
.md-fer h2{margin:0;font:600 20px/1.2 var(--font-display);letter-spacing:-.012em;
 color:var(--text);min-width:0}
.md-fer .est{font:600 9px/1 var(--font-mono,monospace);letter-spacing:.1em;
 text-transform:uppercase;padding:4px 7px;border-radius:var(--r-pill,999px);
 border:1px solid var(--line-strong);color:var(--text-muted);white-space:nowrap;flex:0 0 auto}
.md-fer .est.obra{border-color:var(--warn);color:var(--warn)}
.md-fer .est.pesada{border-color:var(--warn);color:var(--warn);
 background:rgba(225,178,59,.10);cursor:help}
.md-fer p{margin:12px 0 0;font-size:12.5px;line-height:1.55;color:var(--text-muted);max-width:46ch}
.md-pe{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;
 margin-top:auto;padding-top:16px}
.md-fer .tags{display:flex;flex-wrap:wrap;gap:5px;margin:0;min-width:0}
.md-fer .tags span{font:400 10px/1 var(--font-mono,monospace);padding:4px 7px;
 border-radius:var(--r-sm,5px);background:rgba(148,170,205,.06);color:var(--text-muted);
 border:1px solid rgba(148,170,205,.18)}
.md-abrir{flex:0 0 auto;display:grid;place-items:center;width:24px;height:24px;margin-left:auto;
 color:var(--text-muted);transition:transform 220ms cubic-bezier(.23,1,.32,1),color 160ms ease}
.md-abrir svg{width:20px;height:20px}
a.md-fer:hover .md-abrir,a.md-fer:focus-visible .md-abrir{color:var(--text);transform:translateX(3px)}
.md-fer.obra{opacity:.62;border-style:dashed;cursor:default}
.md-fer.destaque{border-color:var(--md-cor,var(--accent));
 background:linear-gradient(var(--md-cor-fraco,transparent),var(--md-cor-fraco,transparent)),
 linear-gradient(120deg,rgba(159,191,230,.063),rgba(27,42,71,.14) 55%,rgba(147,137,187,.047))}
.md-atalho{margin:18px 0 0;font-size:12.5px;color:var(--text-muted)}
.md-atalho a{color:var(--md-cor,var(--accent));text-underline-offset:3px}
.md-atalho a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.md-pg > .ui-alerta{margin-top:auto;padding-top:26px;border-top:0;
 justify-content:flex-start;text-align:left;font-size:12px}
.md-clin{display:flex;align-items:flex-start;gap:8px;font-size:12px;line-height:1.55;
 color:var(--text-muted)}
.md-clin .pt{width:7px;height:7px;border-radius:50%;flex:0 0 auto;margin-top:5px;
 background:var(--warn)}

:root[data-tema="claro"] .md-pg::before{
 background:radial-gradient(ellipse at 8% 48%,rgba(77,140,214,.11),transparent 57%),
  radial-gradient(ellipse at 84% 8%,rgba(115,83,184,.07),transparent 48%)}
:root[data-tema="claro"] .md-simbolo{color:rgba(23,82,140,.34)}
:root[data-tema="claro"] .md-feixe{opacity:.42}
:root[data-tema="claro"] .md-feixe .f0{stop-color:rgba(23,110,170,0)}
:root[data-tema="claro"] .md-feixe .f1{stop-color:rgb(23,110,170)}
:root[data-tema="claro"] .md-feixe .f2{stop-color:rgb(115,83,184)}
:root[data-tema="claro"] .md-feixe .f3{stop-color:rgba(115,83,184,0)}
:root[data-tema="claro"] .md-fer{border-color:rgba(23,52,91,.15);
 background:linear-gradient(120deg,rgba(255,255,255,.95),rgba(239,244,251,.9) 55%,rgba(244,240,251,.92));
 box-shadow:0 14px 32px rgba(22,32,46,.09)}
:root[data-tema="claro"] .md-fer::before{box-shadow:inset 0 1px rgba(255,255,255,.95)}
:root[data-tema="claro"] .md-fer::after{
 background:linear-gradient(110deg,transparent 45%,rgba(176,140,80,.12) 50%,transparent 55%)}
:root[data-tema="claro"] a.md-fer:hover,:root[data-tema="claro"] a.md-fer:focus-visible{
 border-color:rgba(138,106,47,.6);
 background:linear-gradient(120deg,rgba(255,255,255,1),rgba(241,246,252,.96) 55%,rgba(246,242,252,.97));
 box-shadow:0 16px 34px rgba(22,32,46,.13)}
:root[data-tema="claro"] a.md-fer:hover::before,:root[data-tema="claro"] a.md-fer:focus-visible::before{
 box-shadow:inset 0 1px rgba(176,140,80,.55)}
:root[data-tema="claro"] .md-visual{opacity:.13}
:root[data-tema="claro"] .md-fer .tags span{background:rgba(23,52,91,.04);border-color:rgba(23,52,91,.14)}

@media (max-width:1180px){
 .md-palco{gap:30px 28px;grid-template-columns:minmax(230px,.8fr) minmax(0,1.6fr)}
 .md-tit h1{font-size:52px}
}
@media (max-width:980px){.md-n3 .md-grade{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:900px){
 .md-pg{min-height:0}
 .md-palco{grid-template-columns:minmax(0,1fr);padding-top:20px}
 .md-intro{padding-right:84px}
 .md-simbolo{position:absolute;right:0;top:0;width:72px;height:72px;margin:0}
 .md-n3 .md-intro{padding-right:0}
 .md-n3 .md-simbolo{position:static}
 .md-n1 .md-grade{grid-template-columns:minmax(0,1fr)}
 .md-feixe{top:60px}
 .md-n3 .md-feixe{top:150px}
}
@media (max-width:640px){
 .md-grade,.md-n3 .md-grade{grid-template-columns:minmax(0,1fr)}
 .md-tit h1{font-size:44px;white-space:normal}
}
@media (prefers-reduced-motion:reduce){
 .md-fer,.md-visual,.md-abrir,.md-fer::before{transition:none}
 a.md-fer:hover,a.md-fer:focus-visible,a.md-fer:hover .md-visual,
 a.md-fer:focus-visible .md-visual,a.md-fer:hover .md-abrir{transform:none}
 .md-fer::after{display:none}
}
"""


def _ajuda(paragrafos):
    try:
        import radai_ui
        return radai_ui.ajuda(*paragrafos)
    except Exception:
        return u""


def ajuda_do_modulo(chave):
    return balao_da_home(chave)


def linha_clinica(chave):
    linha = (MODULOS.get(chave) or {}).get("linha") or ALERTA_DA_PORTA
    try:
        import radai_ui
        return radai_ui.alerta(linha)
    except Exception:
        return (u'<div class="ui-alerta md-clin"><span class="pt"></span>'
                u'<span data-radai-frase>%s</span></div>' % linha)


ALERTA_DA_PORTA = (u"Ferramenta de apoio, n&atilde;o validada para uso "
                   u"cl&iacute;nico")


TITULO_TERCEIROS = u"Componentes de terceiros"
TITULO_DA_TELA = u"O que sai daqui"


def _terceiros_derivados():
    try:
        import radai_consent
        fontes = radai_consent.fontes_de_terceiros()
    except Exception:
        return None
    if not fontes:
        return None
    saida = []
    for f in fontes:
        saida.append(u"<b>%s</b> — %s" % (_esc(f["nome"]), _esc(f["licenca"])))
    saida.append(u"Quem reconhece o órgão é terceiro. O que construímos é a "
                 u"camada de acessibilidade.")
    return saida


def secoes_de_ajuda(chave):
    secoes = dict(AJUDA.get(chave) or {})
    longo = SEM_EXPORTACAO.get(chave)
    if longo:
        miolo = longo.split(u">", 1)[-1].rsplit(u"</p>", 1)[0]
        secoes = dict([(TITULO_DA_TELA, (miolo,))] + list(secoes.items()))
    if chave in (u"home", u"autocontorno") and TITULO_TERCEIROS in secoes:
        derivada = _terceiros_derivados()
        if derivada:
            secoes[TITULO_TERCEIROS] = derivada
    return secoes


def balao_da_home(chave):
    secoes = secoes_de_ajuda(chave)
    if not secoes:
        return u""
    paragrafos = []
    frase = (MODULOS.get(chave) or {}).get("frase")
    if frase:
        paragrafos.append(_esc(frase))
    for titulo in secoes:
        paragrafos.append(u'<b class="hm-aj-t">%s</b>' % _esc(titulo))
        for p in secoes[titulo]:
            paragrafos.append(p)
    try:
        import radai_ui
        return radai_ui.ajuda(*paragrafos, direita=True)
    except Exception:
        return u""

def _icone(nome):
    try:
        import radai_ui
        return radai_ui.icone_de(nome)
    except Exception:
        return u""


_SETA = (u'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
         u'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         u'<path d="M5 12h14M13 6l6 6-6 6"/></svg>')


def _cartao(f, cor):
    cod, ico, nome, rota, texto = f[0], f[1], f[2], f[3], f[4]
    estado = f[5] if len(f) > 5 else u""
    tags = f[6] if len(f) > 6 else ()
    pesada = f[7] if len(f) > 7 else u""
    obra = nao_navega(estado)
    pill = u""
    if pesada:
        pill = (u'<span class="est pesada" title="%s" data-radai-frase>%s</span>'
                % (_esc(pesada), _esc(u"PESADA")))
    if estado and estado != u"@VIGIA@":
        pill += (u'<span class="est%s" data-radai-frase>%s</span>'
                 % (u" obra" if obra else u"", _esc(estado)))
    elif estado == u"@VIGIA@":
        pill += u'<span class="est" id="md_vigia">&mdash;</span>'
    desenho = _icone(ico)
    corpo = (u'<span class="md-visual" aria-hidden="true">%s</span>'
             u'<span class="ic">%s</span>'
             u'<div class="cab"><h2 data-radai-frase>%s</h2>%s</div>'
             u'<p data-radai-frase>%s</p>'
             % (desenho, desenho, _esc(nome), pill, _esc(texto)))
    pe = u""
    if tags:
        pe = (u'<div class="tags">%s</div>'
              % u"".join(u"<span>%s</span>" % _esc(t) for t in tags))
    if obra or not rota:
        return (u'<div class="md-fer obra" aria-disabled="true">%s'
                u'<div class="md-pe">%s</div></div>' % (corpo, pe))
    return (u'<a class="md-fer%s" href="%s">%s<div class="md-pe">%s'
            u'<span class="md-abrir" aria-hidden="true">%s</span></div></a>'
            % (u" destaque" if cod in EM_DESTAQUE else u"", _esc(rota), corpo, pe,
               _SETA))


def _feixe(linhas=15, largura=1210, altura=330, pontos=40):
    caminhos = []
    meio = (linhas - 1) / 2.0
    for k in range(linhas):
        f = (k - meio) / meio
        d = []
        for i in range(pontos + 1):
            u = i / float(pontos)
            centro = (altura * 0.43 + 21 * math.sin(2 * math.pi * (u * 0.92 - 0.12))
                      + 26 * u)
            abre = 14 + 40 * abs(u - 0.47) ** 1.3
            y = centro + f * abre
            d.append(u"%s%.1f %.1f" % (u"L" if i else u"M", u * largura, y))
        caminhos.append(u'<path d="%s"/>' % u" ".join(d))
    return (u'<svg class="md-feixe" viewBox="0 0 %d %d" preserveAspectRatio="none" '
            u'fill="none" aria-hidden="true" focusable="false"><defs>'
            u'<linearGradient id="md-feixe-grad"><stop class="f0" offset="0"/>'
            u'<stop class="f1" offset=".25"/><stop class="f2" offset=".7"/>'
            u'<stop class="f3" offset="1"/></linearGradient></defs>'
            u'<g stroke="url(#md-feixe-grad)" stroke-width=".8">%s</g></svg>'
            % (largura, altura, u"".join(caminhos)))


FEIXE = _feixe()


def _arte(chave):
    try:
        import radai_porta
        return radai_porta.icone(chave)
    except Exception:
        return u""


def titulo_com_fim(m):
    titulo, destaque = m.get("titulo") or u"", m.get("destaque") or u""
    fim = destaque.strip()
    if not fim:
        return u"<h1>%s</h1>" % _esc(titulo)
    return (u'<h1 data-ls-fim="%s">%s<span class="ls-fim">%s</span></h1>'
            % (_esc(fim), _esc(titulo), _esc(destaque)))


# GUARDA: todo módulo leva o alerta no pé, depois dos cartões, numa linha só.
CLINICA_NO_RODAPE = frozenset(MODULOS)


# GUARDA: tela sem cartão próprio que o cartão de outra promete; sai quando as duas telas virarem uma.
ATALHOS = {}


def atalhos(chave):
    return u"".join(
        u'<p class="md-atalho"><a href="%s" data-radai-frase>%s</a></p>'
        % (_esc(rota), _esc(texto)) for texto, rota in ATALHOS.get(chave, ()))


def pagina(chave):
    m = MODULOS.get(chave)
    if not m:
        return u""
    var, _fraca = CORES.get(chave, ("--accent", "--accent-fraco"))
    ferramentas = FERRAMENTAS.get(chave, ())
    cartoes = u"".join(_cartao(f, var) for f in ferramentas)
    n = max(1, min(3, len(ferramentas)))
    alerta = linha_clinica(chave)
    no_pe = chave in CLINICA_NO_RODAPE
    return (
        u'<div class="md-pg md-n%d" style="--md-cor:var(%s);--md-cor-fraco:var(%s)">'
        u'<div class="md-palco">%s'
        u'<div class="md-intro"><div class="md-tit">%s%s</div>%s'
        u'<div class="md-simbolo" aria-hidden="true">%s</div></div>'
        u'<div class="md-grade" role="group" aria-label="ESCOLHA A FERRAMENTA">%s</div>'
        u'</div>%s%s</div>'
        % (n, var, _fraca, FEIXE, titulo_com_fim(m), ajuda_do_modulo(chave),
           (u"" if no_pe else alerta), _arte(chave), cartoes, atalhos(chave),
           (alerta if no_pe else u"")))


JS_VIGIA = u"""
<script>
(function(){
 var el = document.getElementById('md_vigia');
 if(!el) return;
 fetch('/api/painel').then(function(r){ return r.json() }).then(function(d){
  var v = d && d.vigia || {};
  var t = v.pausado ? 'PAUSADO' : (v.rodando ? 'RODANDO' : 'INERTE');
  el.textContent = t;
 }).catch(function(){ el.textContent = '—' });
})();
</script>"""


def pagina_completa(chave, titulo=u""):
    m = MODULOS.get(chave) or {}
    nome = titulo or (u"%s%s" % (m.get("titulo", u""), m.get("destaque", u"")))
    return (u'<!doctype html><html><head><meta charset="utf-8">'
            u'<title>%s &middot; Radioterapia.AI</title>'
            u'<meta name="viewport" content="width=device-width,initial-scale=1">'
            u'<style>%s</style></head><body>%s%s</body></html>'
            % (_esc(nome), CSS, pagina(chave), JS_VIGIA))


