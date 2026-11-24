# -*- coding: utf-8 -*-
"""Shared task sheet for Rodar Agora and DICOM Bridge. Data comes from the installed task catalog."""

import json
from functools import lru_cache
from pathlib import Path

TABELA = [
    ("Catálogo de tarefas",
     "Task catalog",
     "Catálogo de tareas",
     "Aufgabenkatalog",
     "Catalogue des tâches",
     "Catalogo delle attività",
     "Katalog zadań",
     "タスク一覧",
     "任务目录",
     "دليل المهام",
     "작업 목록",
     "কাজের তালিকা"),
    ("O AUTO escolhe as tarefas conforme a anatomia da série. Consulte aqui o que cada tarefa segmenta.",
     "AUTO selects tasks according to the anatomy in the series. See what each task segments.",
     "AUTO elige las tareas según la anatomía de la serie. Consulte qué segmenta cada tarea.",
     "AUTO wählt die Aufgaben anhand der Anatomie der Serie. Hier sehen Sie, was jede Aufgabe segmentiert.",
     "AUTO choisit les tâches selon l’anatomie de la série. Consultez les structures segmentées par chacune.",
     "AUTO sceglie le attività in base all’anatomia della serie. Consulta le strutture segmentate da ciascuna attività.",
     "AUTO dobiera zadania do anatomii widocznej w serii. Sprawdź, co segmentuje każde zadanie.",
     "AUTO はシリーズに写る解剖部位に応じてタスクを選びます。各タスクの対象構造を確認できます。",
     "AUTO 根据序列中的解剖部位选择任务。您可以查看每个任务分割哪些结构。",
     "يختار AUTO المهام بحسب التشريح الظاهر في السلسلة. يمكنك معرفة البنى التي تحددها كل مهمة.",
     "AUTO는 영상 시리즈에 나타난 해부학적 부위에 따라 작업을 선택합니다. 각 작업의 분할 대상을 확인할 수 있습니다.",
     "সিরিজে দৃশ্যমান অঙ্গসংস্থান অনুযায়ী AUTO কাজ বেছে নেয়। প্রতিটি কাজ কোন গঠন বিভাজন করে তা দেখুন।"),
    ("Não foi possível carregar a ficha desta tarefa.",
     "The task details could not be loaded.",
     "No se pudo cargar la ficha de esta tarea.",
     "Die Details dieser Aufgabe konnten nicht geladen werden.",
     "Impossible de charger la fiche de cette tâche.",
     "Impossibile caricare la scheda di questa attività.",
     "Nie udało się wczytać opisu zadania.",
     "タスクの詳細を読み込めませんでした。",
     "无法加载此任务的详情。",
     "تعذّر تحميل تفاصيل هذه المهمة.",
     "작업 설명을 불러올 수 없습니다.",
     "কাজটির বিবরণ লোড করা যায়নি।"),
    ("Identifica órgãos, ossos, músculos e vasos na TC. A anatomia identificada orienta as tarefas seguintes.",
     "Identifies organs, bones, muscles and vessels on CT. This anatomy guides subsequent tasks.",
     "Identifica órganos, huesos, músculos y vasos en la TC. Esta anatomía guía las tareas posteriores.",
     "Erkennt Organe, Knochen, Muskeln und Gefäße in der CT. Diese Anatomie dient den folgenden Aufgaben als Orientierung.",
     "Identifie les organes, les os, les muscles et les vaisseaux sur la TDM. Ces repères anatomiques guident les tâches suivantes.",
     "Identifica organi, ossa, muscoli e vasi nella TC. Questi riferimenti anatomici guidano le attività successive.",
     "Rozpoznaje narządy, kości, mięśnie i naczynia w TK. Ta anatomia ukierunkowuje kolejne zadania.",
     "CT で臓器、骨、筋肉、血管を識別します。識別した解剖構造を後続のタスクに使用します。",
     "在 CT 上识别器官、骨骼、肌肉和血管，并利用这些解剖信息指导后续任务。",
     "يحدد الأعضاء والعظام والعضلات والأوعية في التصوير المقطعي. وتوجّه هذه المعالم التشريحية المهام اللاحقة.",
     "CT에서 장기, 뼈, 근육과 혈관을 식별합니다. 이 해부학적 정보는 이후 작업에 활용됩니다.",
     "সিটি ছবিতে অঙ্গ, হাড়, পেশি ও রক্তনালি শনাক্ত করে। এই অঙ্গসংস্থান পরবর্তী কাজকে নির্দেশনা দেয়।"),
    ("Identifica órgãos, ossos, músculos e vasos na RM. A anatomia identificada orienta as tarefas seguintes.",
     "Identifies organs, bones, muscles and vessels on MRI. This anatomy guides subsequent tasks.",
     "Identifica órganos, huesos, músculos y vasos en la RM. Esta anatomía guía las tareas posteriores.",
     "Erkennt Organe, Knochen, Muskeln und Gefäße in der MRT. Diese Anatomie dient den folgenden Aufgaben als Orientierung.",
     "Identifie les organes, les os, les muscles et les vaisseaux sur l’IRM. Ces repères anatomiques guident les tâches suivantes.",
     "Identifica organi, ossa, muscoli e vasi nella RM. Questi riferimenti anatomici guidano le attività successive.",
     "Rozpoznaje narządy, kości, mięśnie i naczynia w MR. Ta anatomia ukierunkowuje kolejne zadania.",
     "MRI で臓器、骨、筋肉、血管を識別します。識別した解剖構造を後続のタスクに使用します。",
     "在 MRI 上识别器官、骨骼、肌肉和血管，并利用这些解剖信息指导后续任务。",
     "يحدد الأعضاء والعظام والعضلات والأوعية في التصوير بالرنين المغناطيسي. وتوجّه هذه المعالم التشريحية المهام اللاحقة.",
     "MRI에서 장기, 뼈, 근육과 혈관을 식별합니다. 이 해부학적 정보는 이후 작업에 활용됩니다.",
     "এমআরআই ছবিতে অঙ্গ, হাড়, পেশি ও রক্তনালি শনাক্ত করে। এই অঙ্গসংস্থান পরবর্তী কাজকে নির্দেশনা দেয়।"),
    ("Segmenta o sacro e as vértebras cervicais, torácicas e lombares separadamente na RM.",
     "Segments the sacrum and individual cervical, thoracic and lumbar vertebrae on MRI.",
     "Segmenta el sacro y cada vértebra cervical, torácica y lumbar en la RM.",
     "Segmentiert das Kreuzbein und die einzelnen Hals-, Brust- und Lendenwirbel in der MRT.",
     "Segmente le sacrum et chaque vertèbre cervicale, thoracique et lombaire sur l’IRM.",
     "Segmenta il sacro e le singole vertebre cervicali, toraciche e lombari nella RM.",
     "Segmentuje kość krzyżową oraz poszczególne kręgi szyjne, piersiowe i lędźwiowe w MR.",
     "MRI で仙骨と各頸椎・胸椎・腰椎を個別に分割します。",
     "在 MRI 上分别分割骶骨以及各节颈椎、胸椎和腰椎。",
     "يحدّد العجز وكل فقرة عنقية وصدرية وقطنية على حدة في التصوير بالرنين المغناطيسي.",
     "MRI에서 천골과 각 경추, 흉추, 요추를 개별적으로 분할합니다.",
     "এমআরআই ছবিতে স্যাক্রাম এবং প্রতিটি সার্ভাইক্যাল, থোরাসিক ও লাম্বার কশেরুকা আলাদাভাবে বিভাজন করে।"),
    ("Divide o fígado em oito segmentos anatômicos na RM.",
     "Divides the liver into eight anatomical segments on MRI.",
     "Divide el hígado en ocho segmentos anatómicos en la RM.",
     "Unterteilt die Leber in der MRT in acht anatomische Segmente.",
     "Divise le foie en huit segments anatomiques sur l’IRM.",
     "Suddivide il fegato in otto segmenti anatomici nella RM.",
     "Dzieli wątrobę na osiem segmentów anatomicznych w MR.",
     "MRI で肝臓を 8 つの解剖学的区域に分けます。",
     "在 MRI 上将肝脏划分为八个解剖分段。",
     "يقسّم الكبد إلى ثمانية قطاعات تشريحية في التصوير بالرنين المغناطيسي.",
     "MRI에서 간을 8개의 해부학적 분절로 나눕니다.",
     "এমআরআই ছবিতে যকৃৎকে আটটি শারীরস্থানিক খণ্ডে বিভক্ত করে।"),
    ("Marca áreas suspeitas de lesão hepática na RM para revisão.",
     "Marks areas of suspected liver lesions on MRI for review.",
     "Marca áreas sospechosas de lesión hepática en la RM para su revisión.",
     "Markiert in der MRT mögliche Leberläsionen zur Überprüfung.",
     "Signale sur l’IRM les zones suspectes de lésion hépatique à examiner.",
     "Segnala nella RM le aree sospette per lesioni epatiche da valutare.",
     "Oznacza podejrzane zmiany wątroby w MR do weryfikacji.",
     "MRI で肝病変が疑われる領域を確認用にマークします。",
     "在 MRI 上标记疑似肝脏病灶区域，供复核。",
     "يضع علامات على المناطق المشتبه بوجود آفات كبدية فيها في التصوير بالرنين المغناطيسي لمراجعتها.",
     "MRI에서 간 병변이 의심되는 부위를 표시하여 검토할 수 있게 합니다.",
     "পর্যালোচনার জন্য এমআরআই ছবিতে যকৃতের সন্দেহজনক ক্ষতের স্থান চিহ্নিত করে।"),
]



@lru_cache(maxsize=1)
def catalogo_publicado():
    return json.loads(Path(__file__).with_name("radai_task_classes.json").read_text(encoding="utf-8"))


def completar_item(item):
    if item.get("estruturas_fonte") == "class_map":
        return
    nome = (item.get("modelo") or {}).get("task") or item["task"]
    publicado = catalogo_publicado()
    classes = publicado["classes"].get(nome)
    if classes and (not item.get("estruturas") or item.get("estruturas_fonte") == "ts_map"):
        item["estruturas"] = list(classes)
        item["estruturas_fonte"] = "TotalSegmentator " + publicado["version"]


def script_bridge():
    # Component updates can also run in a suite whose options API predates this catalog.
    data = catalogo_publicado()
    codigos = ("en", "es", "de", "fr", "it", "pl", "ja", "zh-CN", "ar", "ko", "bn")
    frases = {row[0]: dict(zip(codigos, row[1:])) for row in TABELA}
    return ("var dcCatalogoPublicado=" + json.dumps(data, separators=(",", ":")) + ";\n"
            + "var dcFrasesDasFichas=" + json.dumps(frases, ensure_ascii=False) + ";\n" + JS)


CSS = """.selo-vel{font-family:var(--font-mono,monospace);font-size:9.5px;
 letter-spacing:.4px;padding:2px 6px;border-radius:4px;flex:0 0 auto;
 white-space:nowrap;border:1px solid var(--line,#1e293b);
 color:var(--text-dim,#72829b)}
.selo-vel.fast{color:var(--success,#5BC57F);border-color:rgba(91,197,127,.38);
 background:rgba(91,197,127,.08)}
.selo-vel.slow{color:var(--warn,#E1B23B);border-color:rgba(225,178,59,.38);
 background:rgba(225,178,59,.08)}
.selo-vel.ultra-slow{color:var(--perigo,#E96A5C);
 border-color:rgba(233,106,92,.45);background:rgba(233,106,92,.08)}
.selo-vel.estimada{border-style:dashed;background:transparent}
.tk-aj{margin-left:auto;flex:0 0 auto;position:relative;
 width:18px;height:18px;padding:0;border-radius:50%;cursor:pointer;
 border:1px solid var(--line,#1e293b);background:transparent;
 color:var(--text-dim,#72829b);font-family:inherit;font-size:11px;
 line-height:1;display:flex;align-items:center;justify-content:center;
 transition:color .16s ease,border-color .16s ease,background .16s ease}
.tk-aj::after{content:'';position:absolute;top:-4px;left:-4px;
 right:-4px;bottom:-4px}
.tk-aj:hover,.tk-aj:focus-visible{color:var(--accent);
 border-color:var(--accent);background:rgba(125,176,255,.08)}
.tk-b{font-size:12px;line-height:1.5}
body:has(.tk-modal-ficha) .ui-balao-flutuante{display:none}
.tk-figura{margin:9px 0}.tk-figura img{display:block;width:100%;height:auto;border-radius:6px}
.tk-figura figcaption{margin-top:4px;font-size:11px;line-height:1.4}
.tk-cod{font-family:var(--font-mono,monospace);font-size:10.5px;
 color:var(--text-dim,#72829b);margin:0 0 10px;
 padding-bottom:9px;border-bottom:1px solid var(--line,#1e293b)}
.tk-l{display:flex;gap:10px;align-items:baseline;margin:0 0 6px}
.tk-k{flex:1 1 auto;color:var(--text-dim,#72829b);min-width:0}
.tk-v{flex:0 0 auto;max-width:58%;text-align:right;color:var(--text,#e6edf7)}
.tk-avisos{margin:0 0 11px;padding:8px 10px;
 border-radius:var(--r-sm,5px);border:1px solid var(--borda-aviso,#4a3a18);
 background:var(--fundo-aviso,#1c1608);color:var(--aviso,#E8A33D);
 font-size:11.5px;line-height:1.45}
.tk-avisos>div{margin:0 0 3px}
.tk-avisos>div:last-child{margin-bottom:0}
.tk-sec{margin:10px 0 8px}
.tk-sec .tk-k{display:block;margin:0 0 5px}
.tk-est{display:flex;flex-wrap:wrap;gap:4px;max-height:132px;overflow:auto}
.tk-est span{font:400 10.5px/1.4 var(--font-mono,monospace);padding:1px 6px;
 border-radius:4px;border:1px solid var(--line,#1e293b);
 color:var(--text-muted,#a3b1c6);background:var(--panel-2,#0f1729)}
.tk-vazio{font-size:11.5px;color:var(--text-dim,#72829b)}
.tk-sep{margin:12px 0 7px;padding-top:9px;border-top:1px solid var(--line,#1e293b);
 font:600 9.5px/1.3 var(--font-mono,monospace);letter-spacing:.5px;
 text-transform:uppercase;color:var(--text-dim,#72829b)}
@media (max-width:420px){
 .tk-l{display:block;margin:0 0 9px}
 .tk-v{max-width:none;text-align:left;display:block}
}
.tk-trava{margin:0 0 10px;padding:8px 10px;border-radius:var(--r-md);
 background:var(--panel-2);border:1px solid var(--line);font-size:12.5px;
 line-height:1.5;color:var(--text)}"""

JS = """
function _tkEsc(val){
 return String(val == null ? '' : val).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function _tkNome(text){
 var traduzido=window.radaiFrase ? window.radaiFrase(text) : text;
 if(traduzido!==text || typeof dcFrasesDasFichas==='undefined') return traduzido;
 return (dcFrasesDasFichas[text]||{})[document.documentElement.lang]||text;
}
function uiAbrirFichaDaTask(item, origem){
 if(!item || !window.uiModal) return;
 window.uiModal({titulo:_tkNome(item.rotulo || item.task), html:_fichaHTML(item,true),
                 classe:'tk-modal-ficha', largura:(item.figuras || []).length ? 920 : 580, origem:origem});
}
function _descrDaTask(id){
 var descr={
  total:'Identifica órgãos, ossos, músculos e vasos na TC. A anatomia identificada orienta as tarefas seguintes.',
  total_mr:'Identifica órgãos, ossos, músculos e vasos na RM. A anatomia identificada orienta as tarefas seguintes.',
  vertebrae_mr:'Segmenta o sacro e as vértebras cervicais, torácicas e lombares separadamente na RM.',
  liver_segments_mr:'Divide o fígado em oito segmentos anatômicos na RM.',
  liver_lesions_mr:'Marca áreas suspeitas de lesão hepática na RM para revisão.'
 };
 return descr[id==='total_v3'||id==='total_v2'?'total':id]||'';
}
function _chipsHTML(nomes){
 return '<div class="tk-est">' + (nomes || []).map(function(n){
  return '<span>' + _tkEsc(n) + '</span>' }).join('') + '</div>';
}
function _fichaHTML(t, ilustrar){
 var h = '<div class="tk-b"><div class="tk-cod">' + _tkEsc(t.task)
   + ((t.datasets || []).length ? (' · Dataset' + _tkEsc(t.datasets[0])) : '') + '</div>';
 if(t.por_que_travada)
  h += '<p class="tk-trava" data-f="trava" data-radai-frase>' + _tkEsc(t.por_que_travada) + '</p>';
 var avisos = (t.avisos || []).slice();
 var desc = t.ajuda || _descrDaTask(t.task);
 if(desc && avisos.indexOf(desc)<0)
  h += '<p data-f="descricao" data-radai-frase>' + _tkEsc(_tkNome(desc)) + '</p>';
 if(t.permitida === false) avisos.unshift('não permitida neste motor' + (t.porque_nao ? (': ' + t.porque_nao) : ''));
 else if(t.disponivel === false && t.porque_nao) avisos.push(t.porque_nao);
 if(avisos.length)
  h += '<div class="tk-avisos" data-f="avisos">' + avisos.map(function(a){
   return '<div data-radai-frase>' + _tkEsc(a) + '</div>' }).join('') + '</div>';
 if(ilustrar) (t.figuras || []).forEach(function(fig){
  var f = fig.fonte;
  h += '<figure class="tk-figura"><img loading="lazy" src="' + _tkEsc(fig.url) +
       '" alt="' + _tkEsc(_tkNome(fig.legenda) + (f ? ' · ' + f.titulo : '')) +
       '"><figcaption><span data-radai-frase>' + _tkEsc(fig.legenda) + '</span>';
  if(f){
   h += ' · ' + _tkEsc(f.titulo) + '<br><a target="_blank" rel="noopener noreferrer" href="' +
        _tkEsc(f.url) + '">' + _tkEsc(f.autor) + '</a> · <a target="_blank" rel="noopener noreferrer" href="' +
        _tkEsc(f.licenca_url) + '">' + _tkEsc(f.licenca) + '</a>';
  }
  h += '</figcaption></figure>';
 });
 var sv = _seloVel(t);
 if(sv) h += '<div class="tk-l" data-f="tempo"><span class="tk-k" data-radai-frase>tempo</span>'
          + '<span class="tk-v">' + sv.outerHTML + '</span></div>';
 if(t.alimenta)
  h += '<div class="tk-l" data-f="alimenta"><span class="tk-k" data-radai-frase>alimenta</span>'
     + '<span class="tk-v">' + _tkEsc(t.arquivo || 'RTSTRUCT') + '</span></div>';
 var m = t.modelo || {};
 if(m.nome)
  h += '<div class="tk-l" data-f="modelo"><span class="tk-k" data-radai-frase>modelo de origem</span>'
     + '<span class="tk-v">' + _tkEsc(m.nome) + '</span></div>'
     + '<div class="tk-l" data-f="versao"><span class="tk-k" data-radai-frase>versão</span>'
     + '<span class="tk-v">' + _tkEsc(m.versao || '—') + '</span></div>'
     + '<div class="tk-l" data-f="task"><span class="tk-k" data-radai-frase>task na biblioteca</span>'
     + '<span class="tk-v">' + _tkEsc(m.task || t.task) + '</span></div>';
 h += '<div class="tk-sec" data-f="segmenta"><span class="tk-k" data-radai-frase>o que segmenta</span>'
    + ((t.estruturas || []).length ? _chipsHTML(t.estruturas)
       : '<div class="tk-vazio" data-radai-frase>a lista sai da biblioteca instalada na estação</div>')
    + '</div>';
 if(t.estruturas_fonte==='TotalSegmentator 2.18.0')
  h += '<small><a href="https://github.com/wasserth/TotalSegmentator/blob/v2.18.0/totalsegmentator/map_to_binary.py" target="_blank" rel="noopener noreferrer">TotalSegmentator 2.18.0 · class_map</a></small>';
 var resto = (t.ficha || []).filter(function(r){ return r.rot !== 'modelo' });
 if(resto.length){
  var fc = _fichaCorpo({task: t.task, ficha: resto}), cod = fc.querySelector('.tk-cod');
  if(cod) fc.removeChild(cod);
  h += '<div class="tk-sep" data-radai-frase>ficha técnica</div>' + fc.innerHTML;
 }
 return h + '</div>';
}

function _fichaCorpo(t){
 var b=document.createElement('div'); b.className='tk-b';
 var c=document.createElement('div'); c.className='tk-cod';
 c.textContent=t.task; b.appendChild(c);
 (t.ficha||[]).forEach(function(r){
  var li=document.createElement('div'); li.className='tk-l';
  var k=document.createElement('span'); k.className='tk-k';
  k.setAttribute('data-radai-frase',''); k.textContent=r.rot;
  var v=document.createElement('span'); v.className='tk-v';
  if(r.frase) v.setAttribute('data-radai-frase','');
  var val = (r.val === null || r.val === undefined) ? '' : String(r.val);
  if(r.rot === 'velocidade' && val.charAt(0) === '~'){
   v.appendChild(document.createTextNode('~'));
   var vt=document.createElement('span'); vt.textContent=val.slice(1);
   v.appendChild(vt);
  } else {
   v.textContent=val;
  }
  li.appendChild(k); li.appendChild(v); b.appendChild(li);
 });
 return b;
}

function _seloVel(t){
 if(!t || !t.velocidade) return null;
 var s=document.createElement('span');
 s.className='selo-vel ' + t.velocidade + (t.velocidade_medida ? '' : ' estimada');
 var rot = String(t.velocidade_rotulo || t.velocidade);
 if(rot.charAt(0) === '~'){ s.appendChild(document.createTextNode('~')); rot = rot.slice(1) }
 var tg=document.createElement('span'); tg.textContent = rot; s.appendChild(tg);
 var de = '';
 (t.ficha||[]).forEach(function(r){
  if(r.rot === 'de onde vem a velocidade') de = r.val });
 if(!de && t.velocidade_fonte) de = t.velocidade_fonte;
 s.title = de || (t.velocidade_medida ? 'medida contra a base, na mesma série e na mesma máquina'
                                      : 'estimada pela forma do modelo; não medida');
 return s;
}
"""
