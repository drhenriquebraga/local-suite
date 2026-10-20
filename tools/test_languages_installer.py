# -*- coding: utf-8 -*-
import io
import json
import os
import re
import sys
import _componentes

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREP = os.path.join(RAIZ, "packager")
sys.path.insert(0, os.path.join(RAIZ, "app"))

_ok = 0
_falhas = []


def checar(nome, cond, detalhe=u""):
    global _ok
    if cond:
        _ok += 1
        print(u"    OK     %s" % nome)
    else:
        _falhas.append(nome)
        print(u"    FALHA  %s  %s" % (nome, detalhe))


def secao(t):
    print(u"\n  ── %s %s" % (t, u"─" * max(0, 62 - len(t))))


def ler(*p):
    caminho = os.path.join(*p)
    if not os.path.isfile(caminho):
        return u""
    return io.open(caminho, encoding="utf-8-sig", errors="replace").read()


def dicionario():
    return json.loads(io.open(os.path.join(PREP, "languages.json"),
                              encoding="utf-8").read())


def _fonte_como_o_powershell_ve(s):
    return re.sub(r"(['\"])\s*\+\s*[\r\n]+\s*\1", u"", s)


_MARCADOR = re.compile(r"\{(\d+)\}")


def _marcadores_divergentes(d):
    ruins = []
    for k, v in d["frases"].items():
        mk = set(_MARCADOR.findall(k))
        for c in d["codigos"][1:]:
            t = v.get(c) or u""
            if not t:
                continue
            mt = set(_MARCADOR.findall(t))
            if mt != mk:
                ruins.append((k[:40], c, u"marcadores %s, a chave tem %s"
                              % (sorted(mt), sorted(mk))))
                continue
            if mk:
                resto = _MARCADOR.sub(u"", t.replace(u"{{", u"").replace(u"}}", u""))
                if u"{" in resto or u"}" in resto:
                    ruins.append((k[:40], c, u"chave solta"))
    return ruins


def teste_dicionario():
    secao(u"o dicionario: estrutura e cobertura")

    j = os.path.join(PREP, "languages.json")
    checar(u"languages.json existe", os.path.isfile(j))
    if not os.path.isfile(j):
        return
    d = dicionario()

    checar(u"12 idiomas", len(d["codigos"]) == 12, str(len(d["codigos"])))
    checar(u"o primeiro e pt-BR (a chave e o portugues)",
           d["codigos"][0] == "pt-BR", d["codigos"][0])
    checar(u"o padrao e pt-BR", d["padrao"] == "pt-BR", d["padrao"])
    checar(u"tem frases", len(d["frases"]) >= 60, str(len(d["frases"])))

    try:
        import radai_languages as I
        app = [c for c, _, _, _ in I.IDIOMAS]
        checar(u"os 12 codigos sao os mesmos do app",
               set(app) == set(d["codigos"]),
               u"so no app=%s · so no json=%s"
               % (sorted(set(app) - set(d["codigos"])),
                  sorted(set(d["codigos"]) - set(app))))
        checar(u"o padrao e o mesmo do app", I.PADRAO == d["padrao"])
    except ImportError:
        checar(u"radai_languages importavel", False)

    faltando = [(k, c) for k, v in d["frases"].items()
                for c in d["codigos"][1:] if not v.get(c)]
    checar(u"nenhuma entrada faltando", not faltando, str(faltando[:3]))

    LEGITIMAS = {(u"3 · Preparar", "es"), (u"MONAI VISTA-3D (código)", "es"),
                 (u"Idioma", "es"), (u"Desinstalar", "es"),
                 (u"Instalador v{0}", "es")}
    iguais = [(k, c) for k, v in d["frases"].items()
              for c in d["codigos"][1:]
              if v.get(c) == k and (k, c) not in LEGITIMAS]
    checar(u"nenhuma 'traducao' identica ao portugues", not iguais,
           str(iguais[:3])[:80])

    ruins = _marcadores_divergentes(d)
    checar(u"todo marcador {n} sobrevive em todos os idiomas, e nenhuma "
           u"traducao tem chave solta", not ruins, str(ruins[:3])[:160])
    _isca = {"codigos": ["pt-BR", "en", "de"], "frases": {
        u"Sao {0} GB de {1} e {2} de {3}": {
            u"en": u"It is {0} GB of {1} and {2} of", u"de": u"Es {0} GB {1} {2} {3}}"}}}
    _r = _marcadores_divergentes(_isca)
    checar(u"  (a isca: perder o {3} e chave solta sao os DOIS acusados)",
           sorted(c for _k, c, _m in _r) == [u"de", u"en"], _r)
    for k, v in d["frases"].items():
        if "{0}" in k:
            sem = [c for c in d["codigos"][1:] if "{0}" not in v.get(c, u"")]
            checar(u"o marcador {0} sobrevive em todos: %s" % k[:34],
                   not sem, str(sem))

    checar(u"o arquivo declara a procedencia das traducoes",
           u"NAO" in d.get("_leia", u"") and u"tradutor humano" in d.get("_leia", u""))


def teste_chaves_casam():
    secao(u"toda chave aparece nos .ps1 (chave morta nunca casa)")
    d = dicionario()

    fontes = {}
    for rel in (("packager", "prepare.ps1"), ("installer", "INSTALL.ps1")):
        fontes[rel[1]] = _fonte_como_o_powershell_ve(ler(RAIZ, *rel))

    tudo = u"\n".join(fontes.values())
    checar(u"os dois .ps1 foram lidos", len(tudo) > 20000, u"%d chars" % len(tudo))

    mortas = []
    for k in d["frases"]:
        if k in (u"Idioma",):
            continue
        pat = u"['\"][ \\t]*" + re.escape(k) + u"[ \\t]*['\"]"
        if re.search(pat, tudo):
            continue
        if u"\n" in k and k in tudo:
            continue
        mortas.append(k)
    checar(u"nenhuma chave morta", not mortas,
           u"\n         · " + u"\n         · ".join(m[:66] for m in mortas[:8]))

    d2 = dicionario()
    prep = _fonte_como_o_powershell_ve(ler(RAIZ, "packager", "prepare.ps1"))
    sem_entrada = []
    for m in re.finditer(
            r"(?:NovoRotulo|NovoBotao|NovaAba|NovaCaixaTexto)\s+'((?:[^']|'')+)'",
            prep):
        t = m.group(1).replace(u"''", u"'").strip()
        if (len(t) < 4 or t.startswith((u"C:\\", u"\\\\", u"http", u"v"))
                or u" " not in t):
            continue
        if t in (u"Radioterapia", u".ai Local Suite",
                 u"Contorno RT", u"Auto"):
            continue
        if t not in d2["frases"]:
            sem_entrada.append(t)
    checar(u"toda frase que a fabrica poe na tela tem entrada",
           not sem_entrada,
           u"\n         · " + u"\n         · ".join(
               x[:66] for x in sem_entrada[:8]))

    blocos = [b.group(1).replace(u"\r\n", u"\n").strip()
              for b in re.finditer(r'@"\r?\n(.*?)\r?\n"@',
                                   ler(RAIZ, "packager", "prepare.ps1"), re.S)]
    fixos = [b for b in blocos if u"$" not in b]
    faltam_blocos = [b for b in fixos if b not in d2["frases"]]
    checar(u"os visores de texto fixo tem entrada (%d de %d blocos)"
           % (len(fixos), len(blocos)),
           not faltam_blocos, str([b[:50] for b in faltam_blocos]))

    checar(u"a checagem ainda sabe reprovar (isca)",
           u"'ZZQX frase que nao existe ZZQX'" not in tudo)
    checar(u"e ainda sabe aprovar (frase real de tela)",
           u"'Preparar o pacote'" in tudo)


def teste_codificacao():
    secao(u"BOM e CRLF: sem eles a chave acentuada nunca casa")

    for rel in (("packager", "languages.ps1"),
                ("packager", "prepare.ps1"),
                ("installer", "INSTALL.ps1")):
        nome = rel[1]
        caminho = os.path.join(RAIZ, *rel)
        if not os.path.isfile(caminho):
            checar(u"%s existe" % nome, False)
            continue
        b = io.open(caminho, "rb").read()
        checar(u"%s: tem BOM" % nome, b[:3] == b"\xef\xbb\xbf")
        soltos = b.count(b"\n") - b.count(b"\r\n")
        checar(u"%s: CRLF em toda linha" % nome, soltos == 0,
               u"%d LF solto" % soltos)

    j = os.path.join(PREP, "languages.json")
    if os.path.isfile(j):
        b = io.open(j, "rb").read()
        checar(u"languages.json: SEM BOM", b[:3] != b"\xef\xbb\xbf")
        checar(u"languages.json: e UTF-8 valido",
               b.decode("utf-8", errors="strict") is not None)

    d = dicionario()
    inst = _fonte_como_o_powershell_ve(ler(RAIZ, "installer", "INSTALL.ps1"))
    doInst = [k for k in d["frases"]
              if re.search(u"['\"][ 	]*" + re.escape(k) + u"[ 	]*['\"]", inst)]
    comAcento = [k for k in doInst if any(ord(c) > 127 for c in k)]
    checar(u"as chaves do INSTALL.ps1 sao ASCII (ele escreve sem acento)",
           not comAcento, str(comAcento[:2]))
    checar(u"o INSTALL.ps1 usa varias chaves do dicionario",
           len(doInst) >= 10, u"%d" % len(doInst))


def teste_costura():
    secao(u"a costura: fabricas registram, e o seletor esta no cabecalho")
    p = ler(RAIZ, "packager", "prepare.ps1")

    checar(u"NovoRotulo registra em vez de atribuir .Text",
           u"Registrar-Texto $r $Texto" in p and u"$r.Text = $Texto" not in p)
    checar(u"NovoBotao registra em vez de atribuir .Text",
           u"Registrar-Texto $b $Texto" in p and u"$b.Text = $Texto" not in p)
    checar(u"NovaAba registra sem o espaco de enfeite",
           u"$Titulo.Trim() -Antes" in p)
    checar(u"a caixa de aceite da licenca registra",
           u"Registrar-Texto $cx" in p)
    checar(u"o que a licenca permite registra",
           u"Registrar-Texto $per $L.permite" in p)
    checar(u"o resumo da licenca vai na dica, traduzido, e a troca de idioma o refaz",
           u"(T $L.resumo)" in p
           and re.search(r"AoTrocarIdioma\s*=\s*\{(?:.|\n)*?AtualizarDicasDasLicencas", p)
           is not None)

    checar(u"o seletor esta no cabecalho", u"Novo-SeletorIdioma" in p)
    checar(u"o seletor e ancorado a direita (a janela redimensiona)",
           re.search(r"\$selIdioma\.Anchor\s*=\s*'Top,Right'", p) is not None)

    for f in ("AtualizarBotaoLicencas", "AtualizarRota", "AtualizarSugestaoPasta"):
        checar(u"a troca de idioma recalcula %s" % f,
               re.search(r"AoTrocarIdioma\s*=\s*\{(?:.|\n)*?" + f, p) is not None)

    checar(u"ha plano B se o languages.ps1 faltar",
           u"} catch {" in p and u"function T {" in p)

    m = ler(RAIZ, "packager", "languages.ps1")
    codigo = u"\n".join(l for l in m.splitlines()
                        if not l.lstrip().startswith("#"))
    checar(u"o handler do seletor nao chama GetNewClosure",
           u".GetNewClosure()" not in codigo)
    checar(u"e os dados dele viajam no Tag do controle",
           u"$cb.Tag = @{" in m and u"$d = $this.Tag" in m)

    i = ler(RAIZ, "installer", "INSTALL.ps1")
    checar(u"o INSTALL.ps1 traduz pelo Diga (a unica saida de tela)",
           u"Write-Host (T $txt)" in i)
    checar(u"o INSTALL.ps1 tem T de identidade antes da primeira mensagem",
           i.index(u"function T {") < i.index(u"function Diga"))
    checar(u"o INSTALL.ps1 le o idioma do pacote", u"idioma.txt" in i)
    checar(u"e aceita RADAI_IDIOMA (caminho automatizado, sem console)",
           u"RADAI_IDIOMA" in i)


def teste_viagem():
    secao(u"o idioma escolhido viaja: preparador -> zip -> estacao -> painel")
    p = ler(RAIZ, "packager", "prepare.ps1")
    c = ler(RAIZ, "build", "configurar_ambiente.py")

    checar(u"o preparador grava idioma.txt junto do aceite",
           u"'idioma.txt'" in p and u"Idioma-Atual" in p)
    checar(u"o empacotador leva languages.ps1 e languages.json",
           u'"languages.ps1"' in c and u'"languages.json"' in c)
    checar(u"o empacotador leva o idioma.txt", u'"idioma.txt"' in c)

    checar(u"os opcionais entram DEPOIS da checagem que aborta",
           c.index(u"opcionais") < c.index(u"faltando = [r for r, o in pares")
           and c.index(u"pares.extend") > c.index(u"faltam arquivos do contrato"))

    checar(u"idioma.txt tambem dentro da pasta do programa",
           u'ctx["bundle"] / "idioma.txt"' in c)

    import radai_languages as I
    ps1 = io.open(os.path.join(RAIZ, "packager", "languages.ps1"),
                  encoding="utf-8-sig").read()
    bloco = ps1.split(u"function Nomes-Idiomas")[-1].split(u"}")[0]
    ordem_ps = re.findall(r"'([a-zA-Z][a-zA-Z\-]*)'\s*=", bloco)
    ordem_app = [c for c, _, _, _ in I.IDIOMAS]
    checar(u"o preparador lista os idiomas na MESMA ordem do app",
           ordem_ps == ordem_app,
           u"ps1=%s | app=%s" % (ordem_ps, ordem_app))

    checar(u"e o preparador tambem abre em ingles sem escolha salva",
           u"$script:IdiomaInicialSemEscolha = 'en'" in ps1)
    checar(u"e a lingua em que ele esta ESCRITO segue pt-BR",
           u'"padrao": "pt-BR"' in io.open(
               os.path.join(RAIZ, "packager", "languages.json"),
               encoding="utf-8").read())

    checar(u"o app expoe padrao_efetivo()", callable(getattr(I, "padrao_efetivo", None)))
    checar(u"sem idioma.txt, a tela abre em ingles",
           I.padrao_efetivo() == "en", I.padrao_efetivo())
    checar(u"e o idioma em que o programa esta ESCRITO segue pt-BR",
           I.PADRAO == "pt-BR", I.PADRAO)

    js = I.corpo_js()
    checar(u"nenhum marcador sobrou no JS",
           not [m for m in ("@IDIOMAS@", "@FRASES@", "@FIXOS@", "@PADRAO@",
                            "@INICIAL@") if m in js])

    checar(u"o JS recebe INICIAL alem de PADRAO", u"INICIAL=" in js)
    checar(u"atual() le a escolha do localStorage",
           u"localStorage.getItem('radai_idioma')" in js)
    checar(u"  e cai em INICIAL quando nao ha escolha",
           u"||INICIAL" in js.replace(u" ", u""))
    checar(u"  e normaliza codigo de idioma antigo",
           u"canon(" in js and u"ALIAS" in js,
           u"`zh` virou `zh-CN`; o que esta gravado no navegador nao muda")
    checar(u"o aviso de documento compara com PADRAO, nao com INICIAL",
           u"if(cod===PADRAO) return;" in js)
    fonte = io.open(_componentes.fonte("app/radai_languages.py"),
                    encoding="utf-8").read()
    checar(u"e o GUARDA: diz por que sao dois",
           any(u"GUARDA:" in l and u"PADRAO" in l and u"INICIAL" in l
               for l in fonte.splitlines())
           and u"sumiria" in fonte and u"avisarDocumento" in fonte)

    checar(u"o leitor do idioma.txt nao tem except cego",
           u"except (OSError, UnicodeError):" in fonte
           and u"except Exception:\n            # Arquivo ilegivel" not in fonte)

    checar(u"le o idioma.txt com utf-8-sig (BOM do Bloco de Notas)",
           u'encoding="utf-8-sig"' in fonte)


def teste_fronteira():
    secao(u"traducao e coisa de tela: nada do que se grava muda de idioma")
    d = dicionario()
    p = ler(RAIZ, "packager", "prepare.ps1")

    i = p.index(u"LICENCAS ACEITAS")
    bloco = p[i:i + 2200]
    checar(u"o LICENCAS_ACEITAS.txt nao passa por T()",
           u"(T '" not in bloco and u"(T \"" not in bloco)

    NOMES = (u"Apache-2.0", u"PSF License", u"NVIDIA License", u"BSD-3-Clause",
             u"nnU-Net", u"TotalSegmentator")
    presentes = [n for n in NOMES if n in d["frases"]]
    checar(u"nenhum identificador de licenca virou chave de traducao",
           not presentes, str(presentes))

    for k, v in d["frases"].items():
        for termo in (u"NV-Segment-CT", u"VISTA-3D", u"TotalSegmentator",
                      u"TPS", u"_ai"):
            if termo in k:
                sem = [c for c in d["codigos"][1:] if termo not in v.get(c, u"")]
                checar(u"'%s' intacto em todas as traducoes de: %s"
                       % (termo, k[:30]), not sem, str(sem))


def _literais_de_T(src):
    achadas = []
    for m in re.finditer(r"\(T\s+'((?:[^']|'')*)'", src):
        f = m.group(1).replace(u"''", u"'")
        if f and f not in achadas:
            achadas.append(f)
    for m in re.finditer(r'\(T\s+"([^"]*)"', src):
        f = m.group(1)
        if f and f not in achadas:
            achadas.append(f)
    return achadas


def teste_frase_de_T_tem_entrada():
    secao(u"toda frase passada a `T` tem entrada (a outra porta)")
    frases = dicionario().get(u"frases", {})
    for nome in (os.path.join(PREP, "prepare.ps1"),
                 os.path.join(RAIZ, "installer", "INSTALL.ps1")):
        curto = os.path.basename(nome)
        try:
            src = io.open(nome, encoding="utf-8-sig").read()
        except Exception as e:
            checar(u"%s foi lido" % curto, False, str(e))
            continue
        achadas = _literais_de_T(src)
        chamadas = len(re.findall(r"\(T\s", src))
        checar(u"%s: o extrator acompanha o fonte" % curto,
               (chamadas < 5) or (len(achadas) >= chamadas // 2),
               u"%d chamada(s) a `T` no fonte, %d literal(is) extraída(s)"
               % (chamadas, len(achadas)))
        faltam = [f for f in achadas if f not in frases]
        checar(u"  e todas têm chave no dicionário", not faltam,
               u"%d sem entrada: %s"
               % (len(faltam), u" | ".join(x[:40] for x in faltam[:4])))

    forjado = (u"$a = (T 'frase que ninguem traduziu')\n"
               u"$b = (T 'com aspa '' dentro')\n"
               u'$c = (T "entre aspas duplas")\n')
    achou = _literais_de_T(forjado)
    checar(u"o extrator acha as três formas (isca)",
           achou == [u"frase que ninguem traduziu",
                     u"com aspa ' dentro",
                     u"entre aspas duplas"],
           repr(achou))


def _marca_traduzida(fonte_da_splash):
    ruins = []
    for l in fonte_da_splash.splitlines():
        cod = l.split(u"#", 1)[0]
        if not any(m in cod for m in (u"radioterapia", u".ai'", u"LOCAL SUITE",
                                      u"Local Suite")):
            continue
        if re.search(r"\(T\s|Registrar-Texto|NovoRotulo|NovoBotao", cod):
            ruins.append(l.strip()[:70])
    return ruins


def teste_marca_e_versao():
    secao(u"a marca na splash nao se traduz; a versao na aba 0, sim")
    p = ler(RAIZ, "packager", "prepare.ps1")
    i = p.find(u"function PerguntarIdioma {")
    j = p.find(u"try { PerguntarIdioma }", i)
    splash = p[i:j] if i >= 0 and j > i else u""
    checar(u"achei a splash (`PerguntarIdioma`)", bool(splash))
    for lit in (u"'radioterapia'", u"'.ai'", u"'LOCAL SUITE'"):
        checar(u"a splash escreve a marca: %s" % lit, lit in splash)
    ruins = _marca_traduzida(splash)
    checar(u"e nenhum pedaco da marca passa por `T` ou pelo registro",
           not ruins, ruins[:3])
    checar(u"  (isca: uma splash com (T 'LOCAL SUITE') e' acusada)",
           _marca_traduzida(u"$sub.Text = (T 'LOCAL SUITE')\n") != [])
    checar(u"o rotulo bilingue continua fora do dicionario",
           u"'Idioma  ·  Language  ·  Idioma  ·  Sprache  ·  Langue'" in splash
           and u"Idioma  ·  Language" not in u" ".join(dicionario()["frases"]))

    d = dicionario()
    for k in (u"Instalador v{0}",
              u"Aceita pacote de transferencia (bundle) versao {0} ou superior"):
        checar(u"a linha de versao tem entrada nos doze: %s" % k[:34],
               k in d["frases"] and all(u"{0}" in d["frases"][k].get(c, u"")
                                        for c in d["codigos"][1:]),
               sorted(c for c in d["codigos"][1:]
                      if u"{0}" not in d["frases"].get(k, {}).get(c, u"")))
    checar(u"e a troca de idioma as repinta (PintarVersoes no AoTrocarIdioma)",
           re.search(r"AoTrocarIdioma\s*=\s*\{(?:.|\n)*?PintarVersoes", p)
           is not None)


def main():
    print(u"\n" + u"=" * 70)
    print(u"  IDIOMAS DO PREPARADOR E DO INSTALADOR")
    print(u"=" * 70)
    for t in (teste_dicionario, teste_chaves_casam, teste_codificacao,
              teste_costura, teste_viagem, teste_fronteira,
              teste_frase_de_T_tem_entrada, teste_marca_e_versao):
        t()
    print(u"\n" + u"=" * 70)
    if _falhas:
        print(u"FALHOU: %d de %d checagens" % (len(_falhas), _ok + len(_falhas)))
        for f in _falhas:
            print(u"    - %s" % f)
        print(u"=" * 70)
        return 1
    print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
