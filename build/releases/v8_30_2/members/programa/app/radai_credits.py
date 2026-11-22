# -*- coding: utf-8 -*-
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROTA = "/creditos"


def caminho_notice():
    for c in (HERE.parent / "NOTICE", HERE / "NOTICE"):
        if c.is_file():
            return c
    return None


def ler_notice():
    p = caminho_notice()
    if p is None:
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


try:
    import radai_cover
    _FOLHA = radai_cover.CSS_DOC
except Exception:
    _FOLHA = u"body{background:var(--bg-0,#060d1a);color:var(--text,#e6edf7);font-family:Arial;margin:0;padding:18px}"

_CABECA = u"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Créditos e licenças · Radioterapia.AI</title><style>""" + _FOLHA + u"""
</style></head><body><header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela" data-radai-frase>Créditos e licenças</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>
<div class="env">
<div class="rc-capa">
 <span class="rc-chip"><i>§</i> Atribuição</span>
 <h1>Créditos e licenças</h1>
 <p class="rc-frase">Quem reconhece o órgão é software de terceiro. Aqui está quem.</p>
 <div class="rc-risca"></div>
</div>

<div class="cx destaque">
<p><b>Não somos autores dos modelos de segmentação.</b> Quem reconhece um órgão
na tomografia é software de terceiro, listado abaixo com autoria, licença,
versão e a declaração do próprio autor.</p>
<p>A Local Suite integra essas ferramentas para ensino e pesquisa. O preparador
usa a conexão da estação para obter as dependências nas fontes indicadas.
O <a href="/licencas-ferramentas">catálogo de ferramentas e licenças</a>
identifica a finalidade, os autores e os termos do código e dos pesos de cada componente.</p>
</div>
"""

_RODAPE = u"""<div class="cx"><h2 data-radai-frase>Modo de processamento dedicado</h2>
<a href="https://libraries.dev/voice-ring" rel="noopener noreferrer">Voice Ring · libraries.dev</a> ·
<a href="https://transitions.dev/transitions/thinking-states/" rel="noopener noreferrer">Thinking States · transitions.dev</a></div></div>
<footer class="decl"><span class="m"></span>
<span><b>Ferramenta de apoio. Não validada para uso clínico.</b>
<span data-radai-frase>Toda saída é rascunho sujeito a revisão médica.</span></span></footer>
</body></html>"""

_SEM_NOTICE = u"""<div class="cx falta">
<b>O arquivo NOTICE não foi encontrado nesta instalação.</b><br><br>
Ele carrega a autoria, a licença e a declaração de cada componente de terceiro —
e preservá-lo é <b>condição da Apache-2.0</b>, a licença que nos permite usar o
TotalSegmentator. Sem ele, esta instalação está fora da licença.<br><br>
Avise quem montou o pacote. O arquivo vive na raiz do projeto e deve ser
copiado junto com os módulos.
</div>"""


_CRITERIO = u"""
<h2>Licenças, e o que elas permitem a você</h2>

<div class="cx destaque">
<p>O catálogo registra os termos publicados pelas equipes responsáveis.</p>
<ul>
 <li><b>Buti et al.</b> — estruturas do encéfalo em TC (tronco
 encefálico, quiasma, cerebelo, ventrículos e linha média) — pesos sob
 <b>MIT</b>: uso comercial permitido.</li>
 <li><b>CADS</b>, variante <code>open</code> — <b>CC BY-SA 4.0</b>: comercial,
 com ShareAlike. O ShareAlike não alcança o contorno que sai do modelo;
 alcança peso derivado de <i>fine-tune</i>, que teria de ser redistribuído sob
 a mesma licença.</li>
 <li><b>JHU-MICA</b> — a arquitetura do modelo pélvico tem licença MIT.
 A publicação oficial dos checkpoints não declara licença separada para os pesos.</li>
 <li><b>MOOSE</b> — <b>CC BY 4.0</b>: comercial, sem ShareAlike, e <b>exige
 atribuição</b> — ela está no <code>NOTICE</code> que viaja no pacote.</li>
 <li><b>Níveis linfonodais cervicais</b> (Weissmann et al., 2023) —
 <b>CC0-1.0</b>, domínio público.</li>
 <li><b>NV-Segment-CT</b> — pesos sob a <b>NVIDIA Open Model License</b>: uso
 comercial permitido. O cartão do modelo diz que ele é para pesquisa e não
 para uso clínico, e essa frase é do autor, não da licença.</li>
 <li><b>ROCardS</b> — os autores autorizam o uso do código e dos pesos em
 pesquisa não comercial sob CC BY-NC 4.0.
 <a href="https://github.com/AIM-Harvard/ROCardS#license" target="_blank"
 rel="noopener noreferrer">Projeto e termos dos autores</a>.</li>
 <li><b>TotalSegmentator</b> — código sob Apache-2.0. Consulte os termos
 dos pesos na ficha da tarefa no catálogo.</li>
</ul>
</div>

<div class="cx">
<p>A origem do código e dos pesos fica registrada no preparo. O catálogo
identifica também os pesos para os quais o fornecedor não publicou termos
específicos.</p>
</div>

<h3>O que vem no pacote</h3>
<ul>
 <li><b>TotalSegmentator</b> — Apache-2.0. <b>Embarcado.</b> É ele que reconhece
 os órgãos. Roda com o recorte no corpo (a opção <code>body_seg</code> da
 biblioteca): um modelo grosseiro, a 6 mm, localiza o corpo, e a tarefa roda só
 dentro dele, na resolução dela. A estatística de uso que a biblioteca envia de
 fábrica fica desligada. Preservar o aviso de copyright e o NOTICE é condição
 da licença, e os dois empacotadores abortam se faltarem. A partir da versão
 8.7, nos pacotes montados e também na instalação direta, os checkpoints dele
 saem sem o estado do
 otimizador, que só serve ao treino — os pesos da rede ficam idênticos byte a
 byte —, e o NOTICE declara a modificação.</li>
 <li><b>Tarefas de achado do TotalSegmentator</b> — nódulos pulmonares
 (<code>lung_nodules</code>), lesões hepáticas na TC (<code>liver_lesions</code>) e na RM
 (<code>liver_lesions_mr</code>). O operador pode pedir a tarefa no PERSONALIZADO ou por protocolo de estudo.
 Escolher um protocolo próprio da estação que inclua achado exige declaração a cada envio à fila.
 No Vigia, a pesquisa de nódulos inicia em Não e requer o módulo LUNG RT instalado. A instalação compacta é suficiente. Os pesos de pré-laudos são opcionais. Ao escolher Sim e iniciar o turno, o operador solicita a pesquisa para as TCs em que o Vigia identifica tórax.
 Na RM abdominal, o Vigia e o «Rodar agora» acrescentam a pesquisa de lesões hepáticas quando a base identifica fígado.
 Nódulos na TC e lesões hepáticas na RM entram no destino escolhido quando há resultado. Outros achados solicitados e comparadores selecionados identificam sua origem no RTSTRUCT.</li>

 <li><b>O derrame pleural e pericárdico é anatomia do tórax</b>
 (<code>pleural_pericard_effusion</code>) neste pacote: roda no
 AUTO com o tórax identificado, nasce ligado no PERSONALIZADO da TC, e o
 derrame pode sair como ROI no FULL ou por seleção explícita no PERSONALIZADO. No STUDY do AUTO, o
 pericárdico vai dentro do coração de radioterapia (<code>Heart_ai</code>), e
 os pulmões saem sem o pleural — desenhar não é afirmar.<br>
 Referência do modelo de derrame: <a href="https://doi.org/10.1097/RLI.0000000000000869"
 target="_blank" rel="noopener">doi:10.1097/RLI.0000000000000869</a></li>
 <li><b>A porta da suíte</b> — a tela de entrada, no navegador — leva a
 biblioteca de animação <b>Motion</b> (MIT), com as dependências dela (MIT e
 0BSD), e a fonte <b>Anton</b> (SIL Open Font License 1.1).
 <b>Embarcadas</b>, com o texto de cada licença no NOTICE.</li>
 <li><b>PyTorch, nnU-Net, SimpleITK, pydicom, rt_utils, FastAPI</b> e as demais
 bibliotecas que o pacote fixa — licenças permissivas (BSD, Apache-2.0, MIT, e
 a da matplotlib, derivada da licença do Python). <b>Embarcados.</b> A lista
 completa, com a versão e o endereço de cada licença, é a do NOTICE, logo
 abaixo.</li>
 <li><b>NV-Segment-CT (NVIDIA)</b> — <b>embarcado</b>, 832 MB. Código
 Apache-2.0 (a inferência vem do bundle MONAI), <b>pesos</b> sob a
 <b>NVIDIA Open Model License</b>, que <b>permite uso comercial</b>. O caveat
 clínico não sai junto com o comercial: o cartão do modelo diz <i>for
 research purposes and not for clinical usage</i>, e ler "comercialmente
 usável" como "liberado para rotina" é a leitura que esta linha impede. A
 licença íntegra viaja na pasta do modelo.</li>
 <li><b>CADS — variante <code>open</code>, tarefa 556</b> — <b>embarcado</b>,
 761 MB. Código Apache-2.0, <b>pesos</b> sob <b>CC BY-SA 4.0</b>: permite uso
 comercial, com ShareAlike. É a variante <code>open</code> de propósito — a
 <code>reference</code> tem licença customizada cujo texto não está publicado,
 e a <code>research</code> é CC BY-NC-SA. Terceiro motor, só para comparação.</li>
 <li><b>MOOSE (ENHANCE.PET)</b> — os dois modelos de comparação somam 1,05 GiB.
 Código Apache-2.0, <b>pesos</b> sob <b>CC BY 4.0</b>: uso comercial
 permitido, sem ShareAlike, e <b>exige atribuição</b>. Câmaras cardíacas e
 composição corporal, em arquivo próprio: o protocolo de delineamento do grupo
 é de medicina nuclear. O Dataset444 é independente e complementa a porção
 posterior das costelas no STUDY. O arquivo de download tem 459.952.870 bytes.</li>
 <li><b>JHU-MICA</b> — modelo pélvico em duas etapas para TC masculina.
 O preparador busca os arquivos na release oficial. O texto da licença MIT
 da arquitetura acompanha a instalação em <code>data/LICENCA-JHU-MICA.txt</code>.
 A release dos checkpoints não especifica uma licença própria para os pesos.</li>
 <li><b>Níveis linfonodais de cabeça e pescoço (Weissmann et al., 2023)</b> —
 <b>embarcado</b>, 2,26 GB. <b>CC0-1.0</b>, domínio público: código e pesos, a
 licença mais permissiva deste pacote — não exige sequer a atribuição, que
 damos assim mesmo. O modelo foi treinado pelo consenso de Grégoire et al.
 2014 (a atualização de 2013), e os vinte níveis saem com os nomes desse
 consenso (<code>Lvl_Ia</code> a <code>Lvl_VIII_R</code>), pelo mapa entre o
 rótulo do modelo e o nível que os autores publicaram com os pesos — fixado
 para aquela versão dos pesos; com outra versão, voltam os nomes neutros
 (<code>LNL01</code> a <code>LNL20</code>). No AUTO e no protocolo simples, o estudo inclui a união dos níveis Ia a VIIb (LNL_UNION_ai, que não é OAR nem
 CTV) e a parótida do nível VIII menos o esternocleidomastoideo, a única
 parótida do entregue: a do TotalSegmentator fica só no conjunto completo,
 com o sufixo <code>_ts</code>. O protocolo avançado oferece também os níveis cervicais separados.</li>
 <li><b>Buti et al. — estruturas do encéfalo em TC</b> — <b>embarcado</b>,
 247 MB. <b>Pesos</b> sob <b>MIT</b>: uso comercial permitido. Treinado em TC
 do conjunto GLIS-RT (The Cancer Imaging Archive). O tronco encefálico e o
 quiasma entram no conjunto completo e no entregue; o cerebelo, os
 ventrículos e a linha média, só no conjunto completo. O encéfalo e os nervos
 ópticos continuam os do TotalSegmentator.</li>
</ul>
<p class="sub">Os pesos de terceiro que não vêm do PyPI — NV-Segment-CT,
CADS, MOOSE, os níveis cervicais e o encéfalo em TC — o preparador baixa da
origem de cada um,
percorrendo o registro de modelos do próprio programa. Um modelo novo entra ali,
e não numa lista escrita à mão. Os pesos do TotalSegmentator, desde a v8.2,
o preparador também baixa por conta própria, dos endereços que a
biblioteca fixada monta, e confere o tamanho, o CRC e — onde a origem o
publica — o SHA-256 de cada arquivo antes de extrair. Nos pacotes montados
a partir da versão 8.7, os checkpoints dos níveis cervicais, do encéfalo em
TC, do MOOSE e do CADS também saem sem o estado do otimizador, com cerca de
metade do tamanho de cada checkpoint e a rede idêntica byte a byte, e o
NOTICE declara a modificação de cada um. Os três motores de
comparação só rodam quando pedidos, na comparação de modelos do PERSONALIZADO
do «Rodar agora», e só em TC; o vigia não os roda. Os níveis cervicais rodam
no AUTO quando o pescoço é detectado e no PERSONALIZADO quando pedidos.
A chave de suavização controla o acabamento das estruturas selecionadas.</p>

<h3>O que NÃO vem, e por quê</h3>
<ul>
 <li><b>nnInteractive (DKFZ)</b> — pesos sob <b>CC BY-NC-SA 4.0</b>, não
 comercial e ShareAlike. <b>Fica fora do pacote</b>: o preparador não o baixa,
 nenhuma tela o chama, e o programa recusa rodá-lo, porque não há entrada dele
 no registro de modelos.</li>
 <li><b>Models Genesis (ASU)</b> — licença própria da universidade, <b>não
 comercial</b>. Fica fora, e hoje nem é usado.</li>
 <li><b>Seleção das tarefas.</b> As tabelas de anatomia por região, os protocolos RT de fábrica e o FAST
 preservam a seleção anatômica. O Vigia só pesquisa nódulos na TC de tórax quando o operador autoriza a tarefa naquele turno. O complemento hepático
 da RM abdominal inclui lesões quando a base encontra fígado. O registro guarda as tarefas executadas.
 Os cistos renais e o derrame fazem parte da anatomia. O modelo desenha os cistos com o rótulo dele
 para o rim não contar o cisto como parênquima. O derrame é descontado dos pulmões. Desenhar não é afirmar.</li>

 <li><b>Modelo que diga o que o achado É.</b> Nenhum componente deste pacote
 devolve probabilidade de malignidade ou classe diagnóstica, e não há onde
 escrever isso: o que sai é contorno, com o rótulo do próprio modelo e
 <code>UNAPPROVED</code>. Medir tamanho, distância e densidade é quantificar;
 dizer o que aquilo é, não. Ver os termos de uso.</li>
 <li><b>Qualquer API hospedada.</b> Nenhuma imagem vai para servidor externo:
 a inferência do NV-Segment-CT roda dos pesos locais, e há teste na bateria
 que quebra se alguém acrescentar um envio.</li>
</ul>

<h3>Referências visuais do processamento dedicado</h3>
<p>O anel de processamento da Local Suite tem como referência visual o <b>voice-ring</b>.
As mensagens animadas de progresso seguem a referência <b>Thinking States</b> do
transitions.dev. A Suite desenha o anel localmente e apresenta o progresso da fila.</p>

<h3>A atribuição completa, como o NOTICE a declara</h3>
"""


def chave_do_texto():
    p = caminho_notice()
    estado = None
    if p is not None:
        try:
            st = os.stat(str(p))
            estado = (str(p), st.st_size, st.st_mtime_ns)
        except OSError:
            estado = (str(p), None, None)
    return (_CABECA, _CRITERIO, _SEM_NOTICE, _RODAPE, ler_notice,
            caminho_notice, estado)


def pagina():
    txt = ler_notice()
    if not txt:
        return _CABECA + _CRITERIO + _SEM_NOTICE + _RODAPE
    seguro = (txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return _CABECA + _CRITERIO + u"<pre>" + seguro + u"</pre>" + _RODAPE


def montar(app):
    from fastapi.responses import HTMLResponse

    @app.get(ROTA, response_class=HTMLResponse)
    def _tela():
        try:
            import radai_menu
            return radai_menu.aplicar_leitura(pagina(), "creditos")
        except Exception:
            return pagina()

    return app
