# -*- coding: utf-8 -*-
import io
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
        return io.open(str(p), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


try:
    import radai_cover
    _FOLHA = radai_cover.CSS_DOC
except Exception:
    _FOLHA = u"body{background:var(--bg-0,#060d1a);color:var(--text,#e6edf7);font-family:Arial;margin:0;padding:18px}"

_CABECA = u"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Créditos e licenças · Radioterapia.AI</title><style>""" + _FOLHA + u"""
</style></head><body><header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela">Créditos e licenças</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>
<div class="env">
<div class="rc-capa">
 <span class="rc-chip"><i>§</i> Atribuição</span>
 <h1>Créditos e <span>licenças</span></h1>
 <p class="rc-frase">Quem reconhece o órgão é software de terceiro. Aqui está quem.</p>
 <div class="rc-risca"></div>
</div>

<div class="cx destaque">
<p><b>Não somos autores dos modelos de segmentação.</b> Quem reconhece um órgão
na tomografia é software de terceiro, listado abaixo com autoria, licença,
versão e a declaração do próprio autor.</p>
<p>O que este projeto constrói é a <b>camada de acessibilidade</b>: a interface
que põe um modelo de pesquisa ao alcance de quem não instala Python, não roda
linha de comando e não tem privilégio de administrador na estação. É modesto e é
exato — e não é neutro, porque tornar alcançável é o ato que transforma "modelo
de pesquisa" em "usado na clínica". Os avisos e o humano no laço são
responsabilidade nossa por causa disso.</p>
</div>
"""

_RODAPE = u"""</div>
<footer class="decl"><span class="m"></span>
<span><b>Ferramenta de apoio. Não validada para uso clínico.</b>
Toda saída é rascunho sujeito a revisão médica.</span></footer>
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
<p><b>Nenhum componente deste pacote é de uso não comercial.</b> Todos os
pesos que ele leva são de licença permissiva ou de uso comercial
permitido:</p>
<ul>
 <li><b>TotalSegmentator</b> — Apache-2.0, e é ele que faz o fluxo
 principal.</li>
 <li><b>NV-Segment-CT</b> — pesos sob a <b>NVIDIA Open Model License</b>: uso
 comercial permitido. O cartão do modelo diz que ele é para pesquisa e não
 para uso clínico, e essa frase é do autor, não da licença.</li>
 <li><b>CADS</b>, variante <code>open</code> — <b>CC BY-SA 4.0</b>: comercial,
 com ShareAlike. O ShareAlike não alcança o contorno que sai do modelo;
 alcança peso derivado de <i>fine-tune</i>, que teria de ser redistribuído sob
 a mesma licença.</li>
 <li><b>MOOSE</b> — <b>CC BY 4.0</b>: comercial, sem ShareAlike, e <b>exige
 atribuição</b> — ela está no <code>NOTICE</code> que viaja no pacote.</li>
 <li><b>Níveis linfonodais cervicais</b> (Weissmann et al., 2023) —
 <b>CC0-1.0</b>, domínio público.</li>
 <li><b>Buti et al.</b> — estruturas do encéfalo em TC (tronco
 encefálico, quiasma, cerebelo, ventrículos e linha média) — pesos sob
 <b>MIT</b>: uso comercial permitido.</li>
</ul>
</div>

<div class="cx">
<p><b>A regra do projeto.</b> No pacote distribuído entra apenas licença
permissiva — Apache-2.0, MIT, BSD, CC0, CC BY ou equivalente — ou de uso
comercial permitido, para que você possa instalar em qualquer serviço,
inclusive privado, sem herdar restrição de um componente que veio junto. Este
pacote a cumpre. Um componente novo com licença restrita apareceria aqui, com
a restrição dita, antes de alguém instalar.</p>
</div>

<h3>O que vem no pacote</h3>
<ul>
 <li><b>TotalSegmentator</b> — Apache-2.0. <b>Embarcado.</b> É ele que reconhece
 os órgãos. Roda com o recorte no corpo (a opção <code>body_seg</code> da
 biblioteca): um modelo grosseiro, a 6 mm, localiza o corpo, e a tarefa roda só
 dentro dele, na resolução dela. A estatística de uso que a biblioteca envia de
 fábrica fica desligada. Preservar o aviso de copyright e o NOTICE é condição
 da licença, e os dois empacotadores abortam se faltarem.</li>
 <li><b>Tarefas de achado do TotalSegmentator</b> — nódulos pulmonares
 (<code>lung_nodules</code>) e lesões hepáticas
 (<code>liver_lesions</code>, <code>liver_lesions_mr</code>). <b>Vêm no
 pacote e não rodam de fábrica.</b> Rodam por ato de quem opera, no
 PERSONALIZADO do «Rodar agora» — a chave da tarefa, ou um protocolo de estudo
 das Reconstruções 3D —, e o log anuncia com a
 palavra ACHADO. Pela chave, o que devolvem sai num arquivo próprio de cada
 tarefa e, cru,
 também no conjunto do TotalSegmentator (<code>STUDY_ts</code>) quando ele é
 pedido, como toda
 saída do modelo — nunca no conjunto completo (<code>STUDY_full</code>) nem no
 entregue ao TPS (<code>RadAI_OAR</code>); pelo estudo, só no mapa de rótulos
 dele, que não vai ao TPS.</li>
 <li><b>O derrame pleural e pericárdico é anatomia do tórax</b>
 (<code>pleural_pericard_effusion</code>) neste pacote: roda no FAST e no
 AUTO com o tórax identificado, nasce ligado no PERSONALIZADO da TC, e o
 derrame sai só no conjunto completo: no entregue e no entregue do FAST, o
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
 <li><b>MOOSE (ENHANCE.PET)</b> — <b>embarcado</b>, dois modelos, 1,05 GB.
 Código Apache-2.0, <b>pesos</b> sob <b>CC BY 4.0</b>: uso comercial
 permitido, sem ShareAlike, e <b>exige atribuição</b>. Câmaras cardíacas e
 composição corporal, em arquivo próprio: o protocolo de delineamento do grupo
 é de medicina nuclear, e não de radioterapia.</li>
 <li><b>Níveis linfonodais de cabeça e pescoço (Weissmann et al., 2023)</b> —
 <b>embarcado</b>, 2,26 GB. <b>CC0-1.0</b>, domínio público: código e pesos, a
 licença mais permissiva deste pacote — não exige sequer a atribuição, que
 damos assim mesmo. O modelo foi treinado pelo consenso de Grégoire et al.
 2014 (a atualização de 2013), e os vinte níveis saem com os nomes desse
 consenso (<code>Lvl_Ia</code> a <code>Lvl_VIII_R</code>), pelo mapa entre o
 rótulo do modelo e o nível que os autores publicaram com os pesos — fixado
 para aquela versão dos pesos; com outra versão, voltam os nomes neutros
 (<code>LNL01</code> a <code>LNL20</code>). Do que ele desenha, vão ao
 entregue só a união dos níveis Ia a VIIb (LNL_UNION_ai, que não é OAR nem
 CTV) e a parótida do nível VIII menos o esternocleidomastoideo, a única
 parótida do entregue: a do TotalSegmentator fica só no conjunto completo,
 com o sufixo <code>_ts</code>.</li>
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
publica — o SHA-256 de cada arquivo antes de extrair. Os três motores de
comparação só rodam quando pedidos, na comparação de modelos do PERSONALIZADO
do «Rodar agora», e só em TC; o vigia não os roda. Os níveis cervicais rodam
no AUTO quando o pescoço é detectado, e no PERSONALIZADO quando pedidos; o
FAST não os roda.</p>

<h3>O que NÃO vem, e por quê</h3>
<ul>
 <li><b>nnInteractive (DKFZ)</b> — pesos sob <b>CC BY-NC-SA 4.0</b>, não
 comercial e ShareAlike. <b>Fica fora do pacote</b>: o preparador não o baixa,
 nenhuma tela o chama, e o programa recusa rodá-lo, porque não há entrada dele
 no registro de modelos.</li>
 <li><b>Models Genesis (ASU)</b> — licença própria da universidade, <b>não
 comercial</b>. Fica fora, e hoje nem é usado.</li>
 <li><b>Nenhuma busca por achado ligada de fábrica.</b> O programa executa
 detecção, e <b>nunca por omissão</b>: o vigia roda a base de anatomia e,
 depois dela, as tarefas de anatomia da região que a base desenhou — nenhuma
 de achado —, e no «Rodar agora» nem o FAST, nem o AUTO, nem um protocolo RT
 do PERSONALIZADO liga uma tarefa de achado. Procurar nódulo ou lesão
 hepática é escolha declarada de
 quem opera, e fica registrada. Os cistos renais e o derrame são da
 anatomia: o modelo de anatomia desenha os cistos, com o rótulo dele, para o
 rim não contar o cisto como parênquima, e o derrame é descontado dos pulmões
 — desenhar não é afirmar.</li>
 <li><b>Modelo que diga o que o achado É.</b> Nenhum componente deste pacote
 devolve probabilidade de malignidade ou classe diagnóstica, e não há onde
 escrever isso: o que sai é contorno, com o rótulo do próprio modelo e
 <code>UNAPPROVED</code>. Medir tamanho, distância e densidade é quantificar;
 dizer o que aquilo é, não. Ver os termos de uso.</li>
 <li><b>Qualquer API hospedada.</b> Nenhuma imagem vai para servidor externo:
 a inferência do NV-Segment-CT roda dos pesos locais, e há teste na bateria
 que quebra se alguém acrescentar um envio.</li>
</ul>

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
