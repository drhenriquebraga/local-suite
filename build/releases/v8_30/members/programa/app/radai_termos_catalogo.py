"""Catálogo local dos termos de terceiros que o usuário pode consultar antes do aceite."""
from functools import lru_cache
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

ARQUIVO = Path(__file__).resolve().parent / "data" / "licencas_suite.json"


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
                   if item.get("ferramenta") and (item.get("opcional") or
                       any(p.startswith("plugin-") for p in item.get("perfis", ())))})


def bloco():
    _, itens = catalogo()
    linhas = []
    for item in itens:
        campos = [("Finalidade","finalidade"),("Autoria","autoria"),("Integração","integracao"),
                  ("Licença do código","licenca_codigo"),("Licença dos pesos ou dados","licenca_pesos"),
                  ("Origem","origem"),("Ambientes","ambientes"),("Versões","versoes"),("Condições de uso","observacoes")]
        detalhes = "".join("<dt>%s</dt><dd>%s</dd>" % (label,escape(_texto(item[k])))
                           for label,k in campos if item.get(k))
        fontes = " · ".join('<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
                            % (escape(f["url"],quote=True),escape(f["rotulo"])) for f in item["fontes"])
        ferramenta = escape(str(item.get("ferramenta") or ""),quote=True)
        linhas.append('<details class="lic-item" data-ferramenta="%s"><summary>%s</summary><dl>%s</dl><p>%s</p></details>'
                      % (ferramenta,escape(item["titulo"]),detalhes,fontes))
    return """<section class="lic-catalogo" aria-label="Ferramentas e licenças">
<label>Pesquisar modelo, biblioteca ou licença <input class="lic-busca" type="search" autocomplete="off"></label>
<p class="lic-num" aria-live="polite"><span class="lic-total">%s</span> componentes</p>%s</section>
<script>document.querySelectorAll('.lic-catalogo').forEach(function(sec){
 const busca=sec.querySelector('input'), cards=Array.from(sec.querySelectorAll('details'));
 const limpa=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const textos=cards.map(c=>limpa(c.textContent+' '+c.dataset.ferramenta));
 busca.addEventListener('input',function(){const q=limpa(this.value.trim());let total=0;
 cards.forEach(function(c,i){c.hidden=!textos[i].includes(q);if(!c.hidden)total++;});
 sec.querySelector('.lic-total').textContent=total;});});</script>""" % (len(itens),"".join(linhas))


CSS = """.lic-catalogo{margin:14px 0 22px}.lic-catalogo label,.lic-catalogo summary{font-weight:600}
.lic-busca{display:block;width:100%;margin:6px 0;padding:9px 12px;color:inherit;background:transparent;border:1px solid #758591;border-radius:6px}
.lic-item{border-bottom:1px solid #60708055;padding:8px 0}.lic-item summary{cursor:pointer}
.lic-item dt{font-weight:600;margin-top:6px}.lic-item dd{margin-left:0}.lic-item p{overflow-wrap:anywhere}
.lic-catalogo a{color:var(--accent,#72b8ff)}.lic-num{font-size:0.88rem}"""
