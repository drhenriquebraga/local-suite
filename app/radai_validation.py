# -*- coding: utf-8 -*-
import hashlib
import hmac
import io
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    import radai_archive
except Exception:
    radai_archive = None

HERE = Path(__file__).resolve().parent

VERSAO_ESQUEMA = "1.0"

NOME_PASTA = "VALIDACAO"
ARQ_ALTERACOES = "REGISTRO_DE_ALTERACOES.md"
ARQ_RASTREIO = "RASTREABILIDADE.jsonl"
ARQ_ESQUEMA = "ESQUEMA.md"
PASTA_EVIDENCIAS = "EVIDENCIAS"
ARQ_SEGREDO = "_pseudonimo.segredo"

PROIBIDOS = ("patientid", "patient_id", "patientname", "patient_name",
             "uid", "seriesinstanceuid", "studyinstanceuid", "sopinstanceuid",
             "caminho", "path", "pasta", "arquivo", "nascimento", "birthdate",
             "accession", "nome", "paciente", "prontuario", "sobrenome")
_RAIZES_PROIBIDAS = ("uid", "patient", "paciente", "caminho", "path", "prontuario",
                     "nome", "pasta", "arquivo", "accession", "nascimento")

_MAX_TEXTO = 48


def _forma_de_metrica(v, _prof=0):
    if isinstance(v, bool) or isinstance(v, int) or isinstance(v, float):
        return True
    if isinstance(v, str):
        s = v.strip()
        if not s or len(s) > _MAX_TEXTO:
            return False
        if any(c in s for c in " \t\\/:@"):
            return False
        if s.count(".") >= 3:
            return False
        return all(c.isalnum() or c in "_-.+%" for c in s)
    if isinstance(v, (list, tuple)) and _prof == 0:
        return len(v) <= 32 and all(_forma_de_metrica(x, 1) for x in v)
    return False


def raiz():
    if radai_archive is not None:
        return radai_archive.raiz() / NOME_PASTA
    return HERE / "calibracao" / NOME_PASTA


def caminho(nome, criar_pasta=False):
    d = raiz()
    if criar_pasta:
        d.mkdir(parents=True, exist_ok=True)
    return d / nome


def pasta_evidencias(versao, criar=False):
    d = raiz() / PASTA_EVIDENCIAS / ("v" + str(versao).lstrip("v"))
    if criar:
        d.mkdir(parents=True, exist_ok=True)
    return d


_SEGREDO_NA_MEMORIA = {}


def _pasta_que_sincroniza(pasta):
    if radai_archive is None:
        return False
    try:
        return bool(radai_archive.em_pasta_sincronizada(pasta)[0])
    except Exception:
        return False


def _segredo():
    p = raiz()
    p.mkdir(parents=True, exist_ok=True)
    arq = p / ARQ_SEGREDO
    if arq.exists():
        try:
            b = arq.read_bytes().strip()
            if len(b) >= 32:
                return b
        except OSError:
            pass
    # GUARDA: chave em texto nunca vai para pasta que sincroniza com a nuvem.
    if _pasta_que_sincroniza(p):
        chave = os.path.normcase(os.path.abspath(str(p)))
        if chave not in _SEGREDO_NA_MEMORIA:
            _SEGREDO_NA_MEMORIA[chave] = os.urandom(32).hex().encode("ascii")
        return _SEGREDO_NA_MEMORIA[chave]
    b = os.urandom(32).hex().encode("ascii")
    arq.write_bytes(b)
    return b


def pseudonimo(bruto):
    chave = str(bruto or "").strip().lower()
    if not chave:
        return "caso-desconhecido"
    d = hmac.new(_segredo(), chave.encode("utf-8"), hashlib.sha256).hexdigest()
    return "caso-" + d[:16]


def versoes_modelos():
    out = {}
    try:
        import importlib.metadata as md
    except Exception:
        return {"_erro": "importlib.metadata indisponivel"}
    for pacote in ("TotalSegmentator", "nnunetv2", "monai", "torch",
                   "SimpleITK", "pydicom", "rt-utils", "numpy", "scipy"):
        try:
            out[pacote] = md.version(pacote)
        except Exception:
            out[pacote] = "ausente"
    out["python"] = "%d.%d.%d" % sys.version_info[:3]
    return out


def versao_pesos():
    base = os.environ.get("TOTALSEG_WEIGHTS_PATH", "")
    if not base:
        return []
    d = Path(base) / "nnunet" / "results"
    if not d.is_dir():
        d = Path(base)
    try:
        return sorted(x.name for x in d.iterdir()
                      if x.is_dir() and x.name.startswith("Dataset"))
    except OSError:
        return []


def _acrescentar(arq, texto):
    arq = Path(arq)
    arq.parent.mkdir(parents=True, exist_ok=True)
    trava = arq.with_suffix(arq.suffix + ".trava")
    fd = None
    for _ in range(60):
        try:
            fd = os.open(str(trava), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except OSError:
            try:
                if trava.exists() and (datetime.now().timestamp()
                                       - trava.stat().st_mtime) > 30:
                    trava.unlink()
                    continue
            except OSError:
                pass
            _dormir(0.05)
    if fd is None:
        return False
    try:
        os.close(fd)
        with io.open(str(arq), "a", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        return True
    except OSError:
        return False
    finally:
        try:
            trava.unlink()
        except OSError:
            pass


def _dormir(s):
    import time
    time.sleep(s)


def registrar_caso(identificador, versao_app, resultado, operador=None,
                   modelos=None, pesos=None, extra=None, quando=None):
    try:
        linha = {
            "quando": (quando or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
            "esquema": VERSAO_ESQUEMA,
            "caso": pseudonimo(identificador),
            "app": str(versao_app),
            "operador": str(operador or os.environ.get("USERNAME")
                            or os.environ.get("USER") or "desconhecido"),
            "maquina": os.environ.get("COMPUTERNAME") or "desconhecida",
            "modelos": modelos if modelos is not None else versoes_modelos(),
            "pesos": pesos if pesos is not None else versao_pesos(),
            "resultado": str(resultado),
        }
        for k, v in (extra or {}).items():
            kb = str(k).strip().lower()
            if kb in PROIBIDOS or kb in linha:
                continue
            if any(p in kb for p in _RAIZES_PROIBIDAS):
                continue
            if not _forma_de_metrica(v):
                continue
            linha[str(k)] = v
        return linha["caso"] if _acrescentar(
            caminho(ARQ_RASTREIO, criar_pasta=True),
            json.dumps(linha, ensure_ascii=False) + "\n") else ""
    except Exception:
        return ""


def ler_casos(limite=None):
    arq = caminho(ARQ_RASTREIO)
    if not arq.exists():
        return []
    out = []
    try:
        with io.open(str(arq), "r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    continue
    except OSError:
        return []
    out.reverse()
    return out[:limite] if limite else out


CABECALHO_ALTERACOES = u"""# Registro de alterações — Auto-Contorno

Exigido pela RDC ANVISA 657/2022, Art. 5º §2º, para software desenvolvido
internamente e de uso exclusivo do serviço. **Retenção de dez anos após o
descarte** — por isso é markdown, texto puro: nada garante que um formato
binário de hoje abra em 2036.

Uma entrada por versão publicada, da mais nova para a mais antiga. O campo
*por quê* é escrito por gente: ele é a diferença entre um registro que
documenta e um que só lista.

Este arquivo mora fora de pasta que sincroniza, ao lado do acervo, porque referencia caso
clínico. Não commite, não copie para dentro do projeto.

---
"""


def registrar_alteracao(versao, o_que, por_que, autor=None, quando=None):
    o_que = (o_que or "").strip()
    por_que = (por_que or "").strip()
    if not o_que or not por_que:
        raise ValueError(
            "registrar_alteracao exige 'o_que' e 'por_que'. Entrada sem a razao "
            "da mudanca nao atende ao Art. 5o §2o — e nao ajuda quem ler depois.")
    arq = caminho(ARQ_ALTERACOES, criar_pasta=True)
    dt = (quando or datetime.now()).strftime("%Y-%m-%d")
    quem = autor or os.environ.get("USERNAME") or os.environ.get("USER") or "—"
    entrada = (u"\n## v%s — %s\n\n"
               u"**O que mudou.** %s\n\n"
               u"**Por quê.** %s\n\n"
               u"Registrado por %s em %s.\n" % (
                   str(versao).lstrip("v"), dt, o_que, por_que, quem, dt))
    if not arq.exists():
        arq.write_text(CABECALHO_ALTERACOES, encoding="utf-8")
        return _acrescentar(arq, entrada)
    try:
        txt = arq.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    corte = txt.find("\n---\n")
    if corte < 0:
        return _acrescentar(arq, entrada)
    cab, resto = txt[:corte + 5], txt[corte + 5:]
    try:
        arq.write_text(cab + entrada + resto, encoding="utf-8")
        return True
    except OSError:
        return False


def arquivar_evidencia(versao, origem, descricao):
    origem = Path(origem)
    if not origem.is_file():
        return ""
    d = pasta_evidencias(versao, criar=True)
    alvo = d / origem.name
    n = 1
    while alvo.exists():
        alvo = d / ("%s_%d%s" % (origem.stem, n, origem.suffix))
        n += 1
    try:
        shutil.copy2(str(origem), str(alvo))
    except OSError:
        return ""
    _acrescentar(d / "INDICE.md",
                 u"- `%s` — %s _(arquivado em %s)_\n" % (
                     alvo.name, descricao,
                     datetime.now().strftime("%Y-%m-%d %H:%M")))
    return str(alvo)


def conferir():
    d = raiz()
    nuvem, motivo = (False, "")
    if radai_archive is not None:
        try:
            nuvem, motivo = radai_archive.em_pasta_sincronizada(d)
        except Exception:
            pass
    casos = ler_casos()
    versoes = sorted(set(c.get("app", "?") for c in casos))
    return {
        "caminho": str(d),
        "existe": d.is_dir(),
        "nuvem": nuvem,
        "motivo": motivo,
        "casos": len(casos),
        "versoes": versoes,
        "alteracoes": caminho(ARQ_ALTERACOES).exists(),
        "esquema": caminho(ARQ_ESQUEMA).exists(),
        "aviso": (u"O registro de validacao esta em %s, que parece pasta "
                  u"sincronizada (%r no caminho). Ele referencia caso clinico: "
                  u"isso sairia do hospital. A chave do pseudonimo nao e "
                  u"gravada nela e vale so enquanto o programa esta aberto%s. "
                  u"Aponte o acervo para uma pasta local." % (
                      d, motivo,
                      u"; a que ja esta la (%s) deve sair dela" % ARQ_SEGREDO
                      if caminho(ARQ_SEGREDO).exists() else u""))
                  if nuvem else "",
    }


ESQUEMA = u"""# Esquema do registro de validação

Versão do esquema: **%(esquema)s**

Escrito pelo próprio gerador, ao lado dos dados, de propósito: em dez anos o
repositório pode não estar mais acessível, e um arquivo de dados sem a
descrição dos campos é um arquivo ilegível.

## `RASTREABILIDADE.jsonl`

Uma linha JSON por caso processado. Append puro — linha existente nunca é
reescrita.

| Campo | O que é |
|---|---|
| `quando` | data e hora locais do processamento, `YYYY-MM-DD HH:MM:SS` |
| `esquema` | versão deste esquema, para quem ler no futuro saber o formato |
| `caso` | **pseudônimo** — `caso-` + 16 hex de HMAC-SHA256 do identificador |
| `app` | versão do Auto-Contorno |
| `operador` | usuário do sistema operacional que rodou |
| `maquina` | nome da estação |
| `modelos` | versão de cada componente que influencia o resultado |
| `pesos` | datasets nnU-Net presentes na instalação |
| `resultado` | desfecho: `ok`, `falha`, ou o motivo |
| demais | métricas do caso — contagem de estruturas, duração, tarefas |

### O que NUNCA aparece aqui

`PatientID`, nome, data de nascimento, UID de série ou de estudo, caminho de
arquivo. O gerador recusa chaves com esses nomes, e há teste na bateria que
falha se alguma escapar.

### Sobre o pseudônimo

HMAC-SHA256 com segredo local de 32 bytes, gerado na primeira execução e
guardado em `_pseudonimo.segredo`, ao lado deste arquivo. Em pasta que
sincroniza com a nuvem o segredo não é gravado: vale só enquanto o programa
está aberto.

Não é um hash simples de propósito: `PatientID` tem espaço de busca pequeno, e
SHA-256 puro de um número de prontuário volta por força bruta em segundos. Com
o HMAC, sem o segredo o pseudônimo não volta.

A etiqueta é **estável** — o mesmo caso dá a mesma em execuções diferentes, que
é o que permite acompanhá-lo ao longo do tempo. Para reidentificar numa
auditoria, recalcule o HMAC sobre o candidato e compare.

**O segredo é dado a preservar.** Perdê-lo não expõe nada, mas quebra a ligação
entre o que foi registrado antes e o que vier depois.

## `REGISTRO_DE_ALTERACOES.md`

Uma entrada por versão publicada, mais nova em cima: data, versão, o que mudou
e **por quê**. O gerador recusa entrada sem a razão — número de versão repetido
não é registro de alteração.

## `EVIDENCIAS/v<versao>/`

Resultado de bateria, medida e captura da versão correspondente, com um
`INDICE.md` dizendo o que é cada arquivo.

## Retenção

Dez anos **após o descarte** do software (RDC ANVISA 657/2022, Art. 5º §2º).
Markdown e JSONL, texto puro, porque nada garante que um formato binário de
hoje abra no fim desse prazo.

## Onde isto mora

Fora de pasta que sincroniza com a nuvem, ao lado do acervo, porque
este registro referencia caso clínico.
""" % {"esquema": VERSAO_ESQUEMA}


def semear(versao_app=None, forcar=False):
    d = raiz()
    d.mkdir(parents=True, exist_ok=True)
    (d / PASTA_EVIDENCIAS).mkdir(exist_ok=True)
    arq = caminho(ARQ_ESQUEMA)
    if forcar or not arq.exists():
        arq.write_text(ESQUEMA, encoding="utf-8")
    alt = caminho(ARQ_ALTERACOES)
    if not alt.exists():
        alt.write_text(CABECALHO_ALTERACOES, encoding="utf-8")
    if versao_app:
        pasta_evidencias(versao_app, criar=True)
    return str(d)
