"""Catálogo local dos termos de terceiros que o usuário pode consultar antes do aceite."""
from functools import lru_cache
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

ARQUIVO = Path(__file__).resolve().parent / "data" / "licencas_suite.json"
NOMES_OPCIONAIS = {"cads_open": "CADS open", "lung-rt": "LUNG RT", "moose": "MOOSE",
                   "neuro-rt": "NEURO RT", "nv_segment_ct": "NV-Segment-CT"}


def catalogo():
    st = ARQUIVO.stat()
    return _ler(ARQUIVO, st.st_size, st.st_mtime_ns)


@lru_cache(maxsize=1)
def _ler(caminho, tamanho, modificado):
    raw = caminho.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    if doc.get("schema") != "local-suite/termos/1" or not doc.get("itens"):
        raise ValueError("Catálogo local de licenças ausente ou incompatível.")
    ids = set()
    for item in doc["itens"]:
        ident = item["id"]
        if not ident or ident in ids or not item.get("titulo") or not item.get("fontes"):
            raise ValueError("Componente inválido no catálogo de termos.")
        campos = {k:v for k,v in item.items() if k!="sha256"}
        canonico = json.dumps(campos,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        if sha256(canonico).hexdigest()!=item.get("sha256"):
            raise ValueError("Termos divergentes da impressão do componente "+ident)
        ids.add(ident)
        for fonte in item["fontes"]:
            url = urlsplit(fonte["url"])
            if url.scheme not in {"http","https"} or not url.hostname:
                raise ValueError("Endereço de origem inválido em "+ident)
    return sha256(raw).hexdigest(), doc["itens"]


def _texto(valor):
    if isinstance(valor, list):
        return " · ".join(_texto(v) for v in valor)
    if isinstance(valor, dict):
        return " · ".join("%s %s" % (k,_texto(v)) for k,v in valor.items())
    return str(valor or "")


def grupos_opcionais():
    return sorted({str(item["ferramenta"]) for item in catalogo()[1]
                   if item.get("ferramenta") and item["ferramenta"] != "rocards_lad" and (item.get("opcional") or
                       any(p.startswith("plugin-") for p in item.get("perfis", ())))})


def _frases_locais():
    from radai_catalogo_nomes_i18n import FRASES as nomes
    from radai_catalogo_licencas_i18n import FRASES as condicoes
    from radai_phrases import CODIGOS
    # Carregadas apenas nas páginas que apresentam o catálogo. Nomes próprios
    # e identificadores de licença sem tradução permanecem conforme a origem.
    dados = {"idiomas": CODIGOS, "frases": [*nomes, *condicoes]}
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return '<script type="application/json" data-radai-frases-locais>' + texto + '</script>'


def bloco(compacto=False):
    _, itens = catalogo()
    linhas = []
    for item in sorted(itens, key=lambda i: (i["titulo"].casefold(), i["id"])):
        campos = [("Finalidade","finalidade"),("Autoria","autoria"),("Integração","integracao"),
                  ("Licença do código","licenca_codigo"),("Licença dos pesos ou dados","licenca_pesos"),
                  ("Origem","origem"),("Ambientes","ambientes"),("Versões","versoes"),("Condições de uso","observacoes")]
        if compacto:
            campos = [campo for campo in campos if campo[1] in ("licenca_codigo", "licenca_pesos", "observacoes")]
        detalhes = "".join("<dt data-radai-frase>%s</dt><dd data-radai-frase>%s</dd>" % (label,escape(_texto(item[k])))
                           for label,k in campos if item.get(k))
        fontes = " · ".join('<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
                            % (escape(f["url"],quote=True),escape(f["rotulo"])) for f in item["fontes"])
        ferramenta = escape(str(item.get("ferramenta") or ""),quote=True)
        ident = "lic-" + escape(item["id"], quote=True)
        ficha = ('<a href="/licencas-ferramentas#%s" target="_blank" rel="noopener">Ver ficha completa</a>' % ident
                 if compacto else "")
        linhas.append('<details class="lic-item" id="%s" data-ferramenta="%s"><summary>%s</summary><dl>%s</dl><div class="lic-fontes">%s</div>%s</details>'
                      % (ident, ferramenta, escape(item["titulo"]), detalhes, fontes, ficha))
    pesquisa = "" if compacto else (
        '<label>Pesquisar modelo, biblioteca ou licença <input class="lic-busca" type="search" autocomplete="off"></label>'
        '<p class="lic-num" aria-live="polite"><span class="lic-total">%d</span> <span data-radai-frase>componentes</span></p>' % len(itens))
    html = '<section class="lic-catalogo" aria-label="Ferramentas e licenças">' + pesquisa + "".join(linhas) + '</section>'
    if compacto:
        return html + _frases_locais()
    return html + _frases_locais() + """
<script>document.querySelectorAll('.lic-catalogo').forEach(function(sec){
 const busca=sec.querySelector('input'), cards=Array.from(sec.querySelectorAll('details'));
 const limpa=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 busca.addEventListener('input',function(){const q=limpa(this.value.trim());let total=0;
 cards.forEach(function(c){c.hidden=!limpa(c.textContent+' '+c.dataset.ferramenta).includes(q);if(!c.hidden)total++;});
 sec.querySelector('.lic-total').textContent=total;});
 const alvo=document.getElementById(location.hash.slice(1));if(alvo && sec.contains(alvo) && alvo.matches('details'))alvo.open=true;});</script>"""


CSS = """.lic-catalogo{margin:14px 0 22px}.lic-catalogo label,.lic-catalogo summary{font-weight:600}
.lic-busca{display:block;width:100%;margin:6px 0;padding:9px 12px;color:inherit;background:transparent;border:1px solid #758591;border-radius:6px}
.lic-item{border-bottom:1px solid #60708055;padding:8px 0}.lic-item summary{cursor:pointer}
.lic-item dt{font-weight:600;margin-top:6px}.lic-item dd{margin-left:0}.lic-fontes{overflow-wrap:anywhere;margin:.75em 0}
.lic-catalogo a{color:var(--accent,#72b8ff)}.lic-num{font-size:0.88rem}"""
