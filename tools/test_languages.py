# -*- coding: utf-8 -*-
import ast
import html
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

SEM_TAG = r"</?[A-Za-z][^>\n]*>"

import tempfile as _tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_ac_idiomas')
_cleanup.adotar_prefixo('radai_t_molde_')
os.environ["RADAI_CALIB_DIR"] = _tempfile.mkdtemp(prefix="radai_ac_idiomas_")


_ok = _falhou = 0
_falhas = []


def secao(t):
    print(u"\n── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def checar(rotulo, cond, detalhe=u""):
    global _ok, _falhou
    if cond:
        _ok += 1
        print(u"  OK     %s" % rotulo)
    else:
        _falhou += 1
        _falhas.append(rotulo)
        print(u"  FALHA  %s  %s" % (rotulo, detalhe))


def ler(rel):
    p = _componentes.fonte(rel)
    if not os.path.isfile(p):
        return u""
    return io.open(p, encoding="utf-8", errors="replace").read()


def _sem_acento(txt):
    import unicodedata
    d = unicodedata.normalize("NFD", txt)
    return u"".join(c for c in d if not unicodedata.combining(c)).casefold()


def teste_tabela():
    secao(u"a tabela: doze colunas, sem buraco e sem repetida")
    import radai_phrases as F
    import radai_languages as I

    checar(u"doze idiomas declarados", len(I.IDIOMAS) == 12, str(len(I.IDIOMAS)))
    checar(u"o padrao (a lingua em que esta escrito) e pt-BR",
           I.PADRAO == "pt-BR", I.PADRAO)

    checar(u"e a tela abre em ingles quando ninguem escolheu",
           I.INICIAL_SEM_ESCOLHA == "en", I.INICIAL_SEM_ESCOLHA)
    checar(u"e sao mesmo duas constantes diferentes",
           I.PADRAO != I.INICIAL_SEM_ESCOLHA)

    codigos = [c for c, _, _, _ in I.IDIOMAS]
    checar(u"a lista nao comeca pelo portugues", codigos[0] != "pt-BR",
           codigos[0])
    checar(u"e o portugues esta na lista, entre os outros",
           "pt-BR" in codigos[1:], u"%s" % codigos)

    latinos = [n for c, _, n, _ in I.IDIOMAS if c in
               ("de", "en", "es", "fr", "it", "pl", "pt-BR")]
    checar(u"o bloco latino esta em ordem alfabetica",
           latinos == sorted(latinos, key=_sem_acento), u"%s" % latinos)

    faltam = set(codigos) - {"pt-BR"} - set(F.CODIGOS)
    sobram = set(F.CODIGOS) - set(codigos)
    checar(u"toda lingua do seletor tem coluna na tabela", not faltam,
           u"%s" % sorted(faltam))
    checar(u"e toda coluna da tabela aparece no seletor", not sobram,
           u"%s" % sorted(sobram))

    larguras = {len(l) for l in F.TABELA}
    checar(u"toda linha tem 1 + 11 colunas", larguras == {12}, str(larguras))

    chaves = [F.normalizar(l[0]) for l in F.TABELA]
    checar(u"nenhuma chave vazia", all(chaves), u"")
    repetidas = {k for k in chaves if chaves.count(k) > 1}
    checar(u"nenhuma chave repetida", not repetidas, str(sorted(repetidas))[:120])

    brancas = [(l[0][:30], i) for l in F.TABELA
               for i in range(1, 12) if l[i] and not l[i].strip()]
    checar(u"nenhuma coluna com so espaco", not brancas, str(brancas)[:120])


def teste_construir():
    secao(u"construir(): o dicionario que vai para o navegador")
    import radai_phrases as F

    d = F.construir()
    checar(u"um dicionario por idioma, menos o padrao",
           sorted(d) == sorted(F.CODIGOS), str(sorted(d)))
    for cod in F.CODIGOS:
        iguais = [k for k, v in d[cod].items() if k == v]
        checar(u"%s: nenhuma 'traducao' identica ao portugues" % cod,
               not iguais, str(iguais[:2])[:90])

    total = len({F.normalizar(l[0]) for l in F.TABELA})
    for cod in F.CODIGOS:
        frac = len(d[cod]) / float(total)
        checar(u"%s cobre >= 80%% das frases (%d/%d)" % (cod, len(d[cod]), total),
               frac >= 0.80, u"%.0f%%" % (frac * 100))


CHAVES_OPCIONAIS_NEURO = frozenset((
    '%s mm por pixel da projeção',
    '%s mm por pixel da projeção — acima do que esta série oferece: o que aparece a mais é interpolação, e não o paciente',
    '%s · %s cortes · %s mm',
    'A cor de cada linha diz de qual incidência ela veio. A linha mais forte é onde as duas se cruzam.',
    'A fila deu esta série como pronta, e nenhuma segmentação com osso apareceu ao lado dela.',
    'A projeção é paralela, sem ampliação. A sala mostra a posição do arco para quem estuda, sem distância fonte–detector e sem colisão.',
    'Acompanhar a caixa',
    'Afastar',
    'Ajustar à tela',
    'C:\\... ou \\\\servidor\\...',
    'Caixa de recorte',
    'Carregar série',
    'Convenção dos ângulos: a do arco em C (DICOM). LAO põe o detector do lado esquerdo do paciente; CRA o inclina para a cabeça.',
    'Cruzar de novo',
    'Enquanto um ângulo é arrastado, chega uma prévia em baixa resolução; o lápis espera a projeção cheia.',
    'Esta série já tem uma entrega do ContourLab, e ela não tem osso que sirva para a projeção.',
    'Guardar incidência',
    'Inverter cores',
    'Limpar recorte',
    'Listar séries',
    'O 3D da caixa mostra o que está dentro dela: o vaso por limiar (sem o osso da segmentação do ContourLab), o osso dessa segmentação e a pele. Ele pode mostrar o rosto: fica nesta máquina e não se exporta. A interseção não aparece no 3D.',
    'O que esta tela é, e o que ela não é.',
    'Sala',
    'Sala na vista padrão',
    'Segmentar em AUTO (substitui a entrega)',
    'Segmentar em AUTO e substituir',
    'Segmentar em AUTO grava o FULL e substitui a entrega desta série. A entrega nova também é sugestão, e passa pela revisão médica.',
    'Segmentar primeiro (AUTO)',
    'Substituir a entrega desta série?',
    'Tirar o osso',
    'Vista do detector',
    'Vista livre',
    'a confirmação não abriu: nada foi para a fila',
    'a fila está parada: o cartão espera alguém clicar em «Iniciar» na barra da fila, e só então a segmentação AUTO começa',
    'a fila fechou o cartão, e nenhuma segmentação com osso apareceu ao lado da série: o osso continua na projeção',
    'a fila não responde: quando a segmentação terminar, escolha a série de novo',
    'a malha não veio do servidor',
    'a marcação continua salva.',
    'a marcação salva desta série voltou: as incidências estão na lista',
    'a mesma lesão em duas incidências, e onde as duas se cruzam',
    'a projeção não veio do servidor',
    'a retroprojeção falhou: as linhas continuam as do último estado bom, e as incidências desenhadas estão salvas — «Cruzar de novo» tenta outra vez.',
    'a roda do mouse aproxima',
    'a segmentação AUTO desta série está rodando: quando terminar, o osso sai da projeção',
    'a segmentação não terminou: o osso continua na projeção.',
    'a segmentação terminou: o osso saiu da projeção',
    'a série parou de responder: «Tentar de novo» reabre a série, e a marcação continua salva.',
    'a tela voltou ao último estado bom, e nada do que foi desenhado se perdeu.',
    'aguarde a projeção desta incidência chegar para desenhar sobre ela',
    'aparecem aqui quando uma incidência é guardada',
    'arrastar gira a incidência',
    'arrastar gira só o 3D',
    'arrastar move o arco · Shift gira a sala',
    'arraste as bordas da caixa nos três planos: a projeção mostra só o que fica dentro dela',
    'arraste contornando o ninho',
    'arraste contornando o ninho · soltar fecha a área',
    'arraste contornando o ninho · soltar fecha a área · Shift ou o botão do meio movem a imagem ampliada',
    'as linhas da marcação não vieram do servidor, nem depois de uma nova tentativa: as incidências desenhadas estão salvas — «Cruzar de novo» tenta outra vez.',
    'carregando o corte…',
    'circule o ninho antes de guardar (3 pontos, no mínimo)',
    'esta série não está mais no acervo: recarregue a lista e escolha-a de novo',
    'fila indisponível: a fila da estação não respondeu. Mande a série pelo «Rodar agora» e escolha-a de novo quando terminar.',
    'guarde ou apague o traço antes de girar: a lista já tem o máximo de incidências',
    'ilustrativa: projeção paralela, sem colisão',
    'legenda do MPR',
    'linhas finas: o que foi retroprojetado',
    'mapa LAO/RAO por CRA/CAU: setas giram 1 grau, Shift e setas 10 graus',
    'mapa de incidências',
    'montando…',
    'na fila, e a fila está rodando: a segmentação AUTO desta série começa na vez dela',
    'na fila: quando a segmentação AUTO do ContourLab terminar, o osso sai da projeção',
    'nenhuma incidência guardada — gire o gantry, circule o ninho, e guarde',
    'nesta série nada pode ser desenhado: escolha outra na lista.',
    'não consegui reler a segmentação: escolha a série de novo.',
    'o 3D não veio do servidor',
    'o 3D olha de onde o detector olha: a mesma orientação da projeção',
    'o cartão continua na fila, e esta tela parou de acompanhá-lo: quando a segmentação terminar, escolha a série de novo',
    'o cartão saiu da fila, e nenhuma segmentação com osso apareceu ao lado da série: o osso continua na projeção',
    'o corte não veio do servidor',
    'o osso está à mostra: a segmentação do ContourLab foi achada, e está desligada',
    'o osso sai da projeção (MIP) pela segmentação do ContourLab',
    'o que o visor menor mostra',
    'o traço da incidência anterior foi guardado antes de girar',
    'o visor enquadra o que está na caixa de recorte',
    'onde se cruzam',
    'pedido de projeção substituído por um mais novo',
    'projetando…',
    'prévia · baixa resolução',
    'sinal da RM, sem HU: as janelas são relativas ao sinal desta série',
    'série aberta — escolha a incidência e circule a área',
    'vaso colado ao osso pode sair junto com ele: confira com o osso à mostra',
    'é o máximo — cada incidência é um volume na memória.',
))


def _texto_de_tela():
    import radai_phrases as F

    def literais(caminho):
        arv = ast.parse(io.open(caminho, encoding="utf-8").read())
        docs = set()
        for no in ast.walk(arv):
            if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef,
                               ast.AsyncFunctionDef)):
                c = no.body[0] if no.body else None
                if (isinstance(c, ast.Expr)
                        and isinstance(c.value, ast.Constant)
                        and isinstance(c.value.value, str)):
                    docs.add(id(c.value))
        fora = []
        for no in ast.walk(arv):
            if (isinstance(no, ast.Constant) and isinstance(no.value, str)
                    and id(no) not in docs):
                fora.append(no.value)
            elif isinstance(no, ast.JoinedStr):
                for v in no.values:
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        fora.append(v.value)
        return fora

    partes = []
    for n in _componentes.nomes("app"):
        if n.endswith(".py") and n != "radai_phrases.py":
            partes.extend(literais(_componentes.fonte("app/" + n)))

    try:
        for _chave, _pag in _telas():
            partes.append(_pag)
    except Exception:
        pass

    tela_neuro = _fonte_neuro()
    if tela_neuro is not None:
        partes.extend(literais(str(tela_neuro)))
    bruto = u"\n".join(partes)
    _atrib = u" ".join(
        re.findall(r'(?:title|aria-label|placeholder)="([^"]+)"', bruto))
    sem_tag = re.sub(SEM_TAG, u"", bruto) + u" | " + _atrib
    return F.normalizar(html.unescape(sem_tag))



NAO_TRADUZ = (
    u"DicomBridge", u"AutoContorno RT", u"AutoContorno", u"Radioterapia.AI",
    u"Radioterapia.AI Local", u"Local Suite", u"TotalSegmentator",
    u"MONAI VISTA-3D", u"VISTA-3D", u"CADS", u"nnInteractive", u"Eclipse",
    u"Apache-2.0", u"ApprovalStatus", u"UNAPPROVED", u"MIT", u"BSD-3",
    u"NVIDIA License", u"CC0", u"DICOM", u"RTSTRUCT", u"MIP", u"MinIP",
    u"Secondary Capture",
    u"CT", u"MR", u"TPS", u"GPU", u"CPU", u"PNG", u"UID", u"HU",
    u"pydicom", u"zlib", u"numpy", u"scikit-image", u"SimpleITK",
    u"Contorno RT", u"Auto",
    u"radioterapia.ai", u"· radioterapia.ai", u"Auto-Contorno",
    u"Henrique Braga · radioterapia.ai",
    u"MIP/MinIP", u"nnU-Net", u"TG-263",
    u"NEURO RT", u"Neuro RT", u"Neuro", u"Nidus RT", u"Elastic RT", u"Nidus", u"Elastic",
    u"NIDUS RT", u"ELASTIC RT", u"NIDUS", u"ELASTIC", u"RT",
    u"TG-132", u"AAPM TG-132", u"Med Phys", u"Brock et al.",
    u"3D Printed Bolus", u"3D Printed", u"Bolus", u"STL", u"LPS",
    u"Radioterapia.AI Local Suite", u"Henrique Braga",
    u"LAO 0°", u"CRA 0°", u"REC 00:00",
    u"Eclipse / Monaco", u"Xio / Focal",
)

INLINE = u"b|em|strong|code|small|sup|sub|u|kbd|abbr|mark"


def _frases_visiveis(pagina):
    t = re.sub(r"<script.*?</script>", u" ", pagina, flags=re.S)
    t = re.sub(r"<style.*?</style>", u" ", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", u" ", t, flags=re.S)
    t = re.sub(r"<title.*?</title>", u" ", t, flags=re.S)
    t = re.sub(r"<!doctype[^>]*>", u" ", t, flags=re.I)
    t = re.sub(r"</?(%s)\b[^>]*>" % INLINE, u"", t)
    t = re.sub(r"</?[A-Za-z][^>]*>", u"\x00", t)
    import radai_phrases as F
    for pedaco in html.unescape(t).split(u"\x00"):
        f = F.normalizar(pedaco)
        if len(f) < 4 or not re.search(u"[A-Za-zÀ-ÿ]", f):
            continue
        if f in NAO_TRADUZ:
            continue
        if len(f.split()) < 2 and f.lower() not in _UMA_PALAVRA:
            continue
        yield f


_UMA_PALAVRA = frozenset([
    u"abrir", u"entrar", u"salvar", u"testar", u"aplicar", u"cancelar",
    u"varrer", u"listar", u"converter", u"rodar", u"pausar", u"fechar",
    u"janela", u"laje", u"eixo", u"modalidade", u"pendências", u"log",
    u"vigia", u"calibrador", u"compilador", u"configurações", u"início",
    u"procedência", u"privacidade", u"créditos", u"diagnóstico",
])


TELAS_DA_MAO = (
    ("/vigia", "radai_watcher", "PAGE", "vigia"),
    ("/bridge/laudo", "radai_bridge", "pagina", "bridge_laudo"),
    ("/elastic/fusao", "radai_elastic_screen", "pagina", "elastic_fusao"),
    ("/bolus/gerar", "radai_bolus_screen", "pagina", "bolus_gerar"),
    ("/recon3d/anatomia", "radai_recon3d_screen", "pagina",
     "recon_anatomia"),
    ("/recon3d/toracica", "radai_recon3d_screen", "pagina", "recon_torax",
     {"ferramenta": "toracica"}),
    ("/recon3d/vascular", "radai_recon3d_vascular", "pagina",
     "recon_vascular"),
    ("/ver", "radai_view", "_pagina", "ver"),
    ("/lote", "radai_batch", "_pagina", "lote"),
    ("/procedencia", "radai_provenance_screen", "pagina", "procedencia"),
    ("/aceite", "radai_consent", "pagina_aceite", "aceite"),
    ("/primeiro-uso", "radai_primeiro_uso", "pagina", "primeiro_uso"),
)

ROTAS_MONTADAS = ("/", "/suite", "/autocontorno", "/config",
                  "/bridge", "/recon3d", "/neuro", "/elastic", "/bolus")

FORA_DA_MEDIDA = {
    "/termos": u"documento legal — não se traduz por dicionário",
    "/politica-privacidade": u"documento legal — idem",
    "/bibliografia": u"229 frases, 225 delas citação bibliográfica",
    "/torax": u"responde 410 — o módulo saiu para projeto próprio",
    "/diagnostico": u"montada dentro da rota, e ainda depende do parâmetro "
                    u"`nu`",
    "/creditos": u"monta, mas 30 de 43 frases sem chave — dívida declarada",
}


def _fonte_neuro():
    from pathlib import Path
    import json
    definida = os.environ.get("RADAI_NEURO_SOURCE")
    if definida is None:
        return None
    escolhida = definida.strip()
    if not escolhida:
        raise ValueError("RADAI_NEURO_SOURCE foi definida vazia.")
    raiz = Path(escolhida).expanduser().resolve()
    manifesto = raiz / "module.json"
    tela = (raiz / "app/radai_nidus_screen.py").resolve()
    if (not manifesto.is_file() or not tela.is_file()
            or not tela.is_relative_to(raiz)
            or json.loads(manifesto.read_text(encoding="utf-8-sig")).get("id") != "neuro-rt"):
        raise ValueError("RADAI_NEURO_SOURCE deve apontar para a fonte válida do plugin NEURO RT.")
    return tela


def _telas_do_neuro():
    tela = _fonte_neuro()
    if tela is None:
        return []
    import importlib
    antigas = list(sys.path)
    try:
        sys.path.insert(0, str(tela.parent))
        modulo = importlib.import_module("radai_nidus_screen")
        from pathlib import Path
        import radai_projection
        if (Path(modulo.__file__).resolve() != tela
                or modulo.radai_nidus is not radai_projection):
            raise ValueError("A tela Nidus não corresponde à fonte explícita e ao núcleo compartilhado.")
        return [("nidus_projecao", modulo.pagina())]
    finally:
        sys.path[:] = antigas


def teste_neuro_opcional():
    secao(u"NEURO na base; a tela Nidus pertence à fonte opcional")
    nomes = set(_componentes.nomes("app"))
    checar(u"NEURO é a rota-base, sem minipágina Nidus antiga",
           "/neuro" in ROTAS_MONTADAS and "/nidus" not in ROTAS_MONTADAS)
    checar(u"a tela Nidus não faz parte do integrador base",
           "radai_nidus_screen.py" not in nomes)
    checar(u"o núcleo de geometria compartilhado permanece na base",
           "radai_projection.py" in nomes)
    checar(u"Nidus não é importado pela lista obrigatória de telas",
           all(linha[1] != "radai_nidus_screen" for linha in TELAS_DA_MAO))
    import radai_phrases as F
    linhas = {F.normalizar(linha[0]): linha for linha in F.TABELA}
    iguais_ao_pt = {("Sala", "es"), ("Sala", "it"), ("Sala", "pl"), ("montando…", "es")}
    incompletas = [chave for chave in CHAVES_OPCIONAIS_NEURO
                   if chave not in linhas or len(linhas[chave]) != 12
                   or any(not isinstance(valor, str) or not (valor.strip() or (chave, codigo) in iguais_ao_pt)
                          for codigo, valor in zip(F.CODIGOS, linhas[chave][1:]))]
    checar(u"o catálogo compartilhado Nidus conserva os doze idiomas sempre",
           not incompletas, str(incompletas[:5]))
    try:
        tela = _fonte_neuro()
        checar(u"RADAI_NEURO_SOURCE ausente ou válida", True)
        if tela is None:
            print(u"  OPCIONAL: tela Nidus não carregada; use RADAI_NEURO_SOURCE para medi-la.")
        else:
            checar(u"a tela opcional indicada monta de verdade", len(_telas_do_neuro()) == 1)
            corpus = _texto_de_tela()
            sem_fonte = [chave for chave in CHAVES_OPCIONAIS_NEURO
                         if chave not in corpus and not _molde_vivo(chave, corpus)]
            checar(u"cada chave opcional continua viva na fonte indicada",
                   not sem_fonte, str(sem_fonte[:5]))
    except Exception as erro:
        checar(u"RADAI_NEURO_SOURCE ausente ou válida", False, str(erro))


def _telas():
    import radai_menu
    saida = []
    try:
        import radai_panel
        saida.append((u"autocontorno",
                      radai_panel._costurar_home(radai_panel.pagina_inicial())))
        saida.append((u"config",
                      radai_menu.aplicar(radai_panel.PAGINA_CONFIG, "config",
                                         com_tarefas=False)))
    except Exception as e:
        checar(u"as telas do painel montam", False, str(e)[:70])
    try:
        import radai_router
        saida.append((u"inicio", radai_router.montar_porta()))
        import radai_modules
        for chave in sorted(radai_modules.MODULOS):
            if chave == "autocontorno":
                continue
            saida.append((chave, radai_menu.aplicar(
                radai_modules.pagina_completa(chave), chave,
                com_tarefas=False)))
    except Exception as e:
        checar(u"as mini-páginas montam", False, str(e)[:70])
    for linha in TELAS_DA_MAO:
        _rota, mod, alvo, chave = linha[:4]
        kw = linha[4] if len(linha) > 4 else {}
        try:
            m = __import__(mod)
            bruto = getattr(m, alvo)
            bruto = bruto(**kw) if callable(bruto) else bruto
            saida.append((chave, radai_menu.aplicar(bruto, chave)))
        except Exception:
            pass
    try:
        for chave, pagina in _telas_do_neuro():
            saida.append((chave, radai_menu.aplicar(pagina, chave)))
    except Exception as erro:
        checar(u"a tela opcional Nidus monta", False, str(erro))
    return saida


def _rotas_html():
    achadas = {}
    fontes = [(n, _componentes.fonte("app/" + n))
              for n in _componentes.nomes("app") if n.endswith(".py")]
    try:
        tela = _fonte_neuro()
        if tela is not None:
            fontes.append(("NEURO_RT/app/radai_nidus_screen.py", str(tela)))
    except Exception as erro:
        checar(u"a fonte opcional de rotas Nidus é válida", False, str(erro))
    for n, caminho in fontes:
        try:
            arv = ast.parse(io.open(caminho, encoding="utf-8").read())
        except Exception:
            continue
        consts = {}
        for no in ast.walk(arv):
            if (isinstance(no, ast.Assign) and len(no.targets) == 1
                    and isinstance(no.targets[0], ast.Name)
                    and isinstance(no.value, ast.Constant)
                    and isinstance(no.value.value, str)):
                consts[no.targets[0].id] = no.value.value
        html_sem_anotacao = set()
        for funcao in ast.walk(arv):
            if not isinstance(funcao, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if any(isinstance(item, ast.Call)
                   and getattr(item.func, "id", "") == "HTMLResponse"
                   for item in ast.walk(funcao)):
                html_sem_anotacao.update(id(decorador) for decorador in funcao.decorator_list)
        for no in ast.walk(arv):
            if not isinstance(no, ast.Call):
                continue
            f = no.func
            if not (isinstance(f, ast.Attribute) and f.attr == "get"):
                continue
            if not (id(no) in html_sem_anotacao or any(k.arg == "response_class"
                       and getattr(k.value, "id", "") == "HTMLResponse"
                       for k in no.keywords)):
                continue
            if not no.args:
                continue
            a = no.args[0]
            rota = None
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                rota = a.value
            elif isinstance(a, ast.Name):
                rota = consts.get(a.id)
            if rota and rota.startswith("/") and not rota.startswith("/api/"):
                achadas.setdefault(rota, n)
    return achadas


def _rotas_sem_dono(achadas):
    medidas = set(ROTAS_MONTADAS) | {l[0] for l in TELAS_DA_MAO}
    if os.environ.get("RADAI_NEURO_SOURCE", "").strip():
        medidas.add("/nidus/projecao")
    return sorted(r for r in achadas
                  if r not in medidas and r not in FORA_DA_MEDIDA)


def teste_rotas_medidas():
    secao(u"toda rota HTML e medida, ou esta declarada fora")
    achadas = _rotas_html()
    checar(u"a varredura achou as rotas do app (%d)" % len(achadas),
           len(achadas) >= 18, str(sorted(achadas))[:120])
    checar(u"a varredura ve /bridge/laudo", "/bridge/laudo" in achadas)
    checar(u"a varredura vê a página NEURO servida pelo loader", "/neuro" in achadas)
    if not os.environ.get("RADAI_NEURO_SOURCE", "").strip():
        checar(u"a varredura base não inventa a tela Nidus ausente",
               "/nidus/projecao" not in achadas)
    checar(u"e /bridge/tps e /bridge/imagem deixaram de ser tela (levam ao pipeline)",
           "/bridge/tps" not in achadas and "/bridge/imagem" not in achadas)

    orfas = _rotas_sem_dono(achadas)
    checar(u"nenhuma rota fora da medida e sem motivo declarado", not orfas,
           u"\n         · " + u"\n         · ".join(
               u"%s (servida por %s)" % (r, achadas[r]) for r in orfas[:6]))

    fantasmas = [r for r in FORA_DA_MEDIDA if r not in achadas]
    checar(u"e nenhum motivo declarado aponta para rota que sumiu",
           not fantasmas, str(fantasmas)[:120])
    checar(u"todo motivo declarado diz alguma coisa",
           all(len(v.split()) >= 3 for v in FORA_DA_MEDIDA.values()))

    isca = dict(achadas)
    isca["/tela-que-ninguem-mediu"] = "isca.py"
    checar(u"a checagem ainda sabe reprovar (isca)",
           "/tela-que-ninguem-mediu" in _rotas_sem_dono(isca))
    checar(u"e ainda sabe aprovar (rota medida de verdade)",
           "/lote" not in _rotas_sem_dono(achadas))


def teste_toda_frase_tem_chave():
    secao(u"toda frase da tela tem chave (a checagem inversa)")
    import radai_phrases as F
    chaves = set(F.normalizar(l[0]) for l in F.TABELA)

    telas = _telas()
    checar(u"as telas montam", len(telas) >= 6, str(len(telas)))
    total, faltando = 0, 0
    for chave, p in telas:
        frases = list(_frases_visiveis(p))
        sem = [f for f in frases if f not in chaves]
        total += len(frases)
        faltando += len(sem)
        if not frases:
            continue
        parte = len(sem) / float(len(frases))
        checar(u"[%s] a maioria das frases tem chave (%d de %d)"
               % (chave, len(frases) - len(sem), len(frases)),
               parte <= 0.25,
               u"sem chave: " + u" | ".join(f[:44] for f in sem[:4]))
    checar(u"a checagem viu frase de verdade", total > 120, str(total))
    print(u"         · %d de %d frases com chave" % (total - faltando, total))

    isca = u"esta frase nao existe na tabela de traducao, e deve ser acusada"
    checar(u"a checagem ainda sabe reprovar (isca)", isca not in chaves)
    real = u"Componentes de terceiros"
    checar(u"e ainda sabe aprovar (frase real de tela)",
           F.normalizar(real) in chaves, real)


PAYLOADS = (
    ("json:protocolos", "radai_modes", "PROTOCOLOS", ("rotulo", "ajuda"),
     "todas"),
    ("json:plugins", "radai_sets", "PLUGINS",
     ("nome", "rotulo", "rotulo_curto", "ajuda"), "todas"),
    ("json:aceite", "radai_consent", "PONTOS", (1, 2), "todas"),
)


def _frases_do_payload(itens, campos):
    for it in itens:
        for c in campos:
            try:
                v = it[c]
            except Exception:
                v = None
            if isinstance(v, str) and v.strip():
                yield v


def _regra_da_fonte(chave, frases, chaves, piso=None):
    import radai_phrases as F
    sem = [f for f in frases if F.normalizar(f) not in chaves]
    com = len(frases) - len(sem)
    if piso == "todas":
        return (u"[%s] toda frase tem chave (%d de %d)"
                % (chave, com, len(frases)), not sem,
                u"sem chave: " + u" | ".join(f[:44] for f in sem[:4]))
    if piso is not None:
        return (u"[%s] a divida declarada nao aumentou (%d de %d, piso %d)"
                % (chave, com, len(frases), piso), com >= piso,
                u"caiu abaixo do piso: " + u" | ".join(
                    f[:44] for f in sem[:2]))
    return (u"[%s] a maioria das frases tem chave (%d de %d)"
            % (chave, com, len(frases)),
            bool(frases) and len(sem) / float(len(frases)) <= 0.25,
            u"sem chave: " + u" | ".join(f[:44] for f in sem[:4]))


def _ligadesliga(src=None):
    src = ler("app/radai_panel.py") if src is None else src
    m = re.search(r"var LIGADESLIGA=\{(.*?)\};", src, re.S)
    if not m:
        return None
    return re.findall(r"\b[A-Z0-9_]+:\s*'([^']+)'", m.group(1))


def _linhas_do_motor(M):
    for m in M.MOTORES:
        for alimentam in ((), (m["cod"],)):
            for linha in M.ajuda_do_motor(m["cod"], alimentam).split(u"\n"):
                if linha.strip():
                    yield linha


def teste_frase_que_chega_por_json():
    secao(u"a frase que chega por JSON (o que o HTML nao mostra)")
    import radai_phrases as F
    chaves = set(F.normalizar(l[0]) for l in F.TABELA)
    visto = 0
    for linha in PAYLOADS:
        chave, mod, alvo, campos = linha[:4]
        piso = linha[4] if len(linha) > 4 else None
        try:
            itens = getattr(__import__(mod), alvo)
        except Exception as e:
            checar(u"[%s] a fonte existe" % chave, False, str(e)[:70])
            continue
        frases = list(_frases_do_payload(itens, campos))
        visto += len(frases)
        if not frases:
            checar(u"[%s] a fonte tem frase" % chave, False, u"vazia")
            continue
        checar(*_regra_da_fonte(chave, frases, chaves, piso))

    import radai_modes as M
    linhas = sorted(set(_linhas_do_motor(M)))
    visto += len(linhas)
    checar(*_regra_da_fonte(u"json:motores", linhas, chaves, "todas"))
    _sem_uma = chaves - {F.normalizar(linhas[0])}
    checar(u"a regra «todas» do `?` dos motores reprova UMA frase sem chave "
           u"(isca), que o teto comum deixaria passar",
           not _regra_da_fonte(u"isca", linhas, _sem_uma, "todas")[1]
           and _regra_da_fonte(u"isca", linhas, _sem_uma)[1])

    class _Colado(object):
        MOTORES = M.MOTORES

        @staticmethod
        def ajuda_do_motor(cod, alimentam=None):
            return M.ajuda_do_motor(cod, alimentam).replace(u"\n", u" ")

    _rot, _ok_colado, _det = _regra_da_fonte(
        u"json:motores", sorted(set(_linhas_do_motor(_Colado))), chaves,
        "todas")
    checar(u"a checagem do `?` dos motores ainda sabe reprovar (isca: as "
           u"duas partes coladas, como eram ate 23/09)", not _ok_colado, _rot)

    lig = _ligadesliga()
    checar(u"[js:ligadesliga] a tabela existe no fonte (%s frase(s); vazia "
           u"desde a v8.3)" % (u"?" if lig is None else len(lig)),
           lig is not None, u"o `var LIGADESLIGA` mudou de forma?")
    lig = lig or []
    visto += len(lig)
    checar(*_regra_da_fonte(u"js:ligadesliga", lig, chaves, "todas"))
    _src = ler("app/radai_panel.py")
    _traduzidas = sorted(l[0] for l in F.TABELA
                         if u"'" not in l[0] and u"\n" not in l[0]
                         and u"\\" not in l[0] and len(l[0]) > 12)[:4]

    def _forjada(frases):
        _linhas = u"".join(u" CHAVE_ISCA_%d: '%s',\n" % (i, f)
                           for i, f in enumerate(frases))
        return _ligadesliga(_src.replace(u"var LIGADESLIGA={",
                                         u"var LIGADESLIGA={\n" + _linhas, 1))
    _isca1 = _forjada([u"ZZQX chave de liga-desliga que ninguem traduziu"]) or []
    checar(u"a checagem das chaves de liga/desliga ainda sabe reprovar "
           u"(isca: uma chave nova na tabela, sem traducao)",
           len(_isca1) == 1
           and not _regra_da_fonte(u"js:ligadesliga", _isca1, chaves,
                                   "todas")[1], str(_isca1))
    _isca2 = _forjada(_traduzidas + [u"ZZQX a quinta, sem traducao"]) or []
    checar(u"e reprova UMA frase sem chave entre quatro traduzidas (isca), "
           u"que o teto comum deixaria passar",
           len(_isca2) == 5
           and not _regra_da_fonte(u"js:ligadesliga", _isca2, chaves,
                                   "todas")[1]
           and _regra_da_fonte(u"js:ligadesliga", _isca2, chaves)[1],
           str(_isca2))
    checar(u"  e a tabela sumida do fonte é acusada como tal (isca)",
           _ligadesliga(_src.replace(u"var LIGADESLIGA={",
                                     u"var OUTRO_NOME={", 1)) is None)

    checar(u"a checagem viu frase de verdade (%d)" % visto, visto >= 25,
           str(visto))

    forjado = [{"rotulo": u"ZZQX rotulo que ninguem traduziu ZZQX"}]
    sobrou = [f for f in _frases_do_payload(forjado, ("rotulo",))
              if F.normalizar(f) not in chaves]
    checar(u"a checagem ainda sabe reprovar (isca)", len(sobrou) == 1)
    import radai_consent as CS
    _pontos = list(_frases_do_payload(CS.PONTOS, (1, 2)))
    _um_a_mais = _pontos + [u"ZZQX ponto novo que ninguem traduziu ZZQX"]
    checar(u"a regra «todas» reprova UM ponto sem traducao (isca)",
           not _regra_da_fonte(u"isca", _um_a_mais, chaves, "todas")[1]
           and _regra_da_fonte(u"isca", _um_a_mais, chaves)[1])
    checar(u"e ainda sabe aprovar (rotulo real)",
           F.normalizar(M.PROT_POR_COD["pelve"]["rotulo"]) in chaves)

    import radai_tasks as T
    _vel = set()
    for _d in T.CATALOGO:
        for _r in T.ficha(_d["task"]):
            if _r["rot"] in (u"velocidade", u"tempo contra a base",
                             u"de onde vem a velocidade"):
                _vel.add(_r["rot"])
                if _r.get("frase"):
                    _vel.add(_r["val"])
    _vel = sorted(_vel)
    checar(u"[ficha:velocidade] achei as linhas da velocidade (%d)"
           % len(_vel), len(_vel) >= 5,
           u"a ficha parou de dizer de onde vem a etiqueta?")
    checar(*_regra_da_fonte(u"ficha:velocidade", _vel, chaves, "todas"))
    _sem = chaves - {F.normalizar(u"estimada pela forma do modelo; não "
                                  u"medida")}
    checar(u"a regra da ficha da velocidade ainda sabe reprovar (isca: a "
           u"frase da estimativa sem chave)",
           not _regra_da_fonte(u"isca", _vel, _sem, "todas")[1])


def _molde_vivo(chave, tela):
    if not _MARCA_DO_MOLDE.search(chave):
        return False
    partes = [p.strip() for p in _MARCA_DO_MOLDE.split(chave) if p.strip()]
    return (len(u"".join(partes)) >= 12
            and all(p in tela for p in partes))


def teste_chave_viva():
    secao(u"toda chave aparece nas telas (chave morta nunca casa)")
    import radai_phrases as F

    tela = _texto_de_tela()
    checar(u"a fonte de comparação não está vazia", len(tela) > 50000,
           u"%d chars" % len(tela))

    _js = u'for(var i=0;i<L.length;i++) h += x(i);'
    _frase = u"esta frase vem DEPOIS da comparacao e tem de sobreviver"
    _junto = re.sub(SEM_TAG, u"",
                    _js + u"\n" + _frase + u"\n<div class=\"x\">")
    checar(u"a limpeza de tag para na quebra de linha", _frase in _junto,
           u"a comparação do JS comeu o literal seguinte")

    diferidas = (CHAVES_OPCIONAIS_NEURO if _fonte_neuro() is None else frozenset())
    if diferidas:
        print(u"  OPCIONAL: vivacidade de %d chaves Nidus adiada para RADAI_NEURO_SOURCE; catálogo continua medido." % len(diferidas))
    mortas = [F.normalizar(l[0]) for l in F.TABELA
              if F.normalizar(l[0]) not in diferidas
              and F.normalizar(l[0]) not in tela
              and not _molde_vivo(F.normalizar(l[0]), tela)]
    checar(u"nenhuma chave morta", not mortas,
           u"\n         · " + u"\n         · ".join(m[:70] for m in mortas[:8]))

    isca = u"ZZQX frase que não existe em tela nenhuma ZZQX"
    checar(u"a checagem ainda sabe reprovar (isca)",
           F.normalizar(isca) not in tela)
    checar(u"o molde montado por concatenação vale pelas partes fixas (isca)",
           _molde_vivo(u"parte fixa um %s e parte fixa dois",
                       u"x = 'parte fixa um ' + v + ' e parte fixa dois';")
           and not _molde_vivo(u"parte fixa um %s e parte fixa dois",
                               u"x = 'parte fixa um ' + v;")
           and not _molde_vivo(u"sem marcador nenhum aqui", u"sem marcador nenhum aqui"))
    checar(u"  e o molde cujas partes não estão em tela nenhuma é morto (isca)",
           not _molde_vivo(u"ZZQX parte que ninguém escreveu %s nem esta ZZQX", tela))

    checar(u"e ainda sabe aprovar (frase real de tela)",
           F.normalizar(u"Vigia de Auto-Contorno") in tela)


def teste_nao_traduzir():
    secao(u"a fronteira: nomenclatura e procedencia nao mudam de idioma")
    import radai_phrases as F
    import radai_languages as I

    d = F.construir()

    presas = [F.normalizar(l[0]) for l in F.TABELA
              if F.normalizar(l[0]).strip(u" \"'.,;:()[]") in I.NAO_TRADUZIR]
    checar(u"nenhuma chave E um termo de NAO_TRADUZIR", not presas,
           str(presas[:3])[:140])

    perdidos = []
    for linha in F.TABELA:
        pt = F.normalizar(linha[0])
        for t in I.NAO_TRADUZIR:
            if t not in pt:
                continue
            for i, cod in enumerate(F.CODIGOS, start=1):
                alvo = F.normalizar(linha[i])
                if alvo and t not in alvo:
                    perdidos.append((cod, t, pt[:34]))
    checar(u"toda traducao preserva a nomenclatura da frase", not perdidos,
           u"\n         · " + u"\n         · ".join(
               u"%s perdeu %s em %r" % p for p in perdidos[:6]))

    vazou = [(c, k[:30], s) for c in F.CODIGOS for k, v in d[c].items()
             for s in re.findall(r"_(?:ai|ts|v3D)\b", v) if s not in k]
    checar(u"nenhuma traducao INVENTA sufixo de procedencia", not vazou,
           str(vazou[:3])[:140])


def _funcao_js(js, nome):
    i = js.find(u"function %s(" % nome)
    if i < 0:
        return u""
    a = js.find(u"{", i)
    if a < 0:
        return u""
    n = 0
    for k in range(a, len(js)):
        if js[k] == u"{":
            n += 1
        elif js[k] == u"}":
            n -= 1
            if n == 0:
                return js[a:k + 1]
    return u""


def teste_js():
    secao(u"o JS costurado: sem marcador solto e com as travas no lugar")
    import radai_languages as I

    js = I.corpo_js()
    for m in ("@IDIOMAS@", "@FRASES@", "@FIXOS@", "@PADRAO@"):
        checar(u"marcador %s foi substituido" % m, m not in js)

    checar(u"tem a normalizacao de espaco", u"replace(/\\s+/g,' ')" in js)
    checar(u"o passo do BLOCO existe", u"var BLOCOS=" in js)
    checar(u"o passo do NO DE TEXTO existe", u"createTreeWalker" in js)
    checar(u"marca o que ja traduziu", u"data-radai-t" in js)
    checar(u"pula elemento fragil (input, canvas, img)",
           u"var FRAGIL=" in js and u"canvas" in js)
    checar(u"pula SCRIPT, STYLE e TEXTAREA",
           u"'SCRIPT'" in js and u"'STYLE'" in js and u"'TEXTAREA'" in js)
    checar(u"marca a direcao do texto para o arabe", u"'rtl':'ltr'" in js)
    checar(u"o aviso de documento existe", u"avisarDocumento" in js)
    checar(u"o aviso cobre termos e privacidade",
           u"'/termos'" in js and u"'/politica-privacidade'" in js)
    checar(u"e nao cita mais a pagina que saiu do app",
           u"'/saibamais'" not in js)

    checar(u"o JS faz UM fetch so", js.count(u"fetch(") == 1,
           str(js.count(u"fetch(")))
    corpo_g = _funcao_js(js, u"gravarNaEstacao")
    checar(u"  e ele mora em gravarNaEstacao",
           corpo_g.count(u"fetch(") == 1, corpo_g[:60])
    checar(u"  para /api/idioma, por POST",
           u"fetch('/api/idioma'" in corpo_g and u"method:'POST'" in corpo_g,
           corpo_g[:120])
    checar(u"  levando so o codigo do idioma",
           u"body:JSON.stringify({idioma:cod})" in corpo_g, corpo_g[:160])
    checar(u"o JS nao usa XHR", u"XMLHttpRequest" not in js)
    checar(u"o JS nao mexe em value nem em atributo de formulario",
           u".value=" not in js and u"setAttribute('value'" not in js)


def teste_aplicar():
    secao(u"aplicar(): costura, ou devolve a pagina intacta")
    import radai_languages as I

    p = u"<html><head></head><body><p>oi</p></body></html>"
    saida = I.aplicar(p)
    checar(u"costura numa pagina completa", u"radai-idioma-js" in saida)
    checar(u"nao duplica quando ja tem", I.aplicar(saida) == saida)
    checar(u"pagina sem </head> sai intacta",
           I.aplicar(u"<body>x</body>") == u"<body>x</body>")
    checar(u"pagina sem </body> sai intacta",
           I.aplicar(u"<html><head></head>") == u"<html><head></head>")
    checar(u"vazio sai vazio", I.aplicar(u"") == u"")
    checar(u"o seletor entra ANTES do </body>",
           saida.index(u"radai-idioma-js") < saida.rindex(u"</body>"))


def _tem_emoji(texto):
    return any(0x1F000 <= ord(ch) <= 0x1FAFF for ch in texto or u"")


def _json_de(js, nome):
    import json as _json
    for marca in (u"var %s=" % nome, u" %s=" % nome):
        i = js.find(marca)
        if i >= 0:
            try:
                return _json.JSONDecoder().raw_decode(js, i + len(marca))[0]
            except Exception:
                return None
    return None


def teste_bandeiras():
    secao(u"as bandeiras: desenho em SVG, uma por idioma, sem emoji")
    import xml.etree.ElementTree as ET
    import radai_languages as I

    codigos = [c for c, _, _, _ in I.IDIOMAS]
    checar(u"toda lingua do seletor tem bandeira, e so elas",
           sorted(I.BANDEIRAS) == sorted(codigos),
           u"%s" % sorted(set(codigos) ^ set(I.BANDEIRAS)))
    proibidas = {u"text", u"image", u"a", u"script", u"use",
                 u"foreignObject", u"style", u"tspan"}
    vistas = {}
    for c in codigos:
        svg = I.bandeira(c)
        try:
            raiz = ET.fromstring(svg)
        except Exception as e:
            checar(u"[%s] e SVG bem formado" % c, False, str(e)[:80])
            continue
        tags = {el.tag.split(u"}")[-1] for el in raiz.iter()}
        attrs = {k.split(u"}")[-1] for el in raiz.iter() for k in el.attrib}
        checar(u"[%s] SVG no quadro 30 x 20" % c,
               raiz.tag.split(u"}")[-1] == u"svg"
               and raiz.get(u"viewBox") == u"0 0 30 20", raiz.get(u"viewBox"))
        checar(u"[%s] so forma e cor (sem texto, imagem, link, script)" % c,
               not (tags & proibidas), u"%s" % sorted(tags & proibidas))
        checar(u"[%s] nenhum id nem href (aparece duas vezes na pagina)" % c,
               not (attrs & {u"id", u"href"}), u"%s" % sorted(attrs))
        checar(u"[%s] tem o que desenhar" % c, len(list(raiz.iter())) >= 2)
        checar(u"[%s] nenhum emoji nem indicador regional" % c,
               not _tem_emoji(svg))
        checar(u"[%s] e um desenho proprio" % c, svg not in vistas,
               u"igual a %s" % vistas.get(svg))
        vistas[svg] = c
    checar(u"o codigo de ontem (zh) leva a bandeira de hoje",
           I.bandeira(u"zh") == I.bandeira(u"zh-CN") != u"")
    checar(u"codigo desconhecido nao ganha bandeira de reserva",
           I.bandeira(u"xx") == u"" and I.bandeira(u"") == u"")

    checar(u"a tabela do Python continua com quatro campos",
           all(len(t) == 4 for t in I.IDIOMAS))
    lista = _json_de(I.corpo_js(), u"IDIOMAS") or []
    checar(u"o navegador recebe as doze, cada uma com a bandeira",
           len(lista) == 12 and all(len(x) == 5 and x[4] == I.bandeira(x[0])
                                    for x in lista),
           u"%d linhas" % len(lista))
    checar(u"nenhum emoji no JS nem no estilo servidos",
           not _tem_emoji(I.corpo_js()) and not _tem_emoji(I.estilo()))


def teste_seletor_js():
    secao(u"o seletor: as duas ancoras, a lista e a grade, o teclado")
    import radai_languages as I
    js = I.corpo_js()
    m = _funcao_js(js, u"montar")
    checar(u"montar() le a ancora de hoje E a de ontem",
           u"querySelectorAll('[data-radai-idiomas],[data-radai-lang]')" in m,
           m[:120])
    checar(u"  e monta em TODAS (era so a primeira)",
           u"forEach.call(alvos" in m)
    checar(u"  e `grade` escolhe a forma de grade",
           u"==='grade'" in m and u"montarGrade(" in m and u"montarLista(" in m)
    r = _funcao_js(js, u"rotuloDe")
    checar(u"cada linha leva a bandeira e o nome na lingua dele",
           u"x[4]" in r and u"lang=" in r and u"x[2]" in r, r[:120])
    ml = _funcao_js(js, u"montarLista")
    checar(u"a lista e um listbox de opcoes",
           u'aria-haspopup="listbox"' in ml and u'role="option"' in ml
           and u"aria-selected" in ml and u"aria-expanded" in ml)
    checar(u"  com teclado: setas, Home/End e Esc devolvendo o foco",
           all(k in ml for k in (u"'ArrowDown'", u"'ArrowUp'", u"'Home'",
                                 u"'End'", u"'Escape'", u"fechar(true)")))
    checar(u"  e as linhas sao botoes (o `<a>` sem href nao recebia foco)",
           u"<a " not in ml)
    mg = _funcao_js(js, u"montarGrade")
    checar(u"a grade e um radiogroup",
           u"'radiogroup'" in mg and u'role="radio"' in mg
           and u"aria-checked" in mg)
    e = _funcao_js(js, u"escolher")
    checar(u"escolher() grava no navegador ANTES de pedir ao servidor",
           0 <= e.find(u"localStorage.setItem('radai_idioma'")
           < e.find(u"gravarNaEstacao("), e[:120])
    checar(u"  e a recarga espera a gravacao, com teto",
           u".then(ir,ir)" in e and u"setTimeout(ir," in e)
    checar(u"atual() continua lendo o navegador primeiro",
           u"localStorage.getItem('radai_idioma')" in _funcao_js(js, u"atual"))


def teste_idioma_da_estacao():
    secao(u"a escolha grava no config da estacao, e a primeira abertura o le")
    import shutil
    import radai_languages as I

    base = _tempfile.mkdtemp(prefix="radai_ac_idiomas_cfg_")
    cfg = os.path.join(base, "radai_watcher.config")
    modelo = (u"# Pasta de pacientes: combine com o TI antes.\nROOT=\n"
              u"# a porta do painel\nPORT=8777\n")
    io.open(cfg, "w", encoding="utf-8").write(modelo)
    guardado = os.environ.get("RADAI_CONFIG")
    os.environ["RADAI_CONFIG"] = cfg

    def texto():
        return io.open(cfg, encoding="utf-8-sig").read()
    try:
        checar(u"sem IDIOMA no config, o config nao decide",
               I.idioma_do_config() == u"")
        base_ini = I.padrao_efetivo()
        marca0 = I.etag_js()
        ok, r = I.gravar_na_estacao(u"de")
        checar(u"gravar `de` funciona", ok and r == u"de", repr((ok, r)))
        checar(u"  e o config ganha IDIOMA=de",
               u"IDIOMA=de" in texto().splitlines(), texto()[-60:])
        checar(u"  sem perder os comentarios nem as outras chaves",
               u"# Pasta de pacientes" in texto() and u"PORT=8777" in texto())
        checar(u"a primeira abertura passa a ser em alemao",
               I.padrao_efetivo() == u"de", I.padrao_efetivo())
        checar(u"  e o JS servido abre em alemao",
               _json_de(I.corpo_js(), u"INICIAL") == u"de",
               repr(_json_de(I.corpo_js(), u"INICIAL")))
        checar(u"  com outra marca: o navegador rebusca o dicionario",
               I.etag_js() != marca0)
        ok, r = I.gravar_na_estacao(u"zh")
        checar(u"o codigo de ontem e gravado com o nome de hoje",
               ok and r == u"zh-CN" and u"IDIOMA=zh-CN" in texto(), repr(r))
        checar(u"  e a linha e trocada, e nao repetida",
               texto().count(u"IDIOMA=") == 1, str(texto().count(u"IDIOMA=")))
        antes = texto()
        for ruim in (u"klingon", u"", None, u"pt-br", u"<script>", 42):
            ok, r = I.gravar_na_estacao(ruim)
            checar(u"%r e recusado, e o config nao muda" % (ruim,),
                   not ok and texto() == antes, repr((ok, r))[:70])
        io.open(cfg, "w", encoding="utf-8").write(modelo + u"IDIOMA=klingon\n")
        checar(u"IDIOMA com lixo, escrito a mao, nao vira idioma",
               I.idioma_do_config() == u"" and I.padrao_efetivo() == base_ini,
               I.padrao_efetivo())
        io.open(cfg, "w", encoding="utf-8-sig").write(u"IDIOMA=fr\n" + modelo)
        checar(u"IDIOMA na primeira linha, com o BOM do Bloco de Notas",
               I.idioma_do_config() == u"fr", repr(I.idioma_do_config()))

        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
        except Exception:
            print(u"    PULADO as rotas: sem fastapi neste runtime")
            return
        import radai_consent
        import radai_router
        app = FastAPI()
        I.montar(app)
        radai_router.montar(app)
        radai_consent.montar_portao(app)
        checar(u"o dicionario NAO monta /api/idioma sozinho (e do painel)",
               u"/api/idioma" not in {getattr(r, "path", u"") for r in
                                      I.montar(FastAPI()).routes})
        cli = TestClient(app)
        io.open(cfg, "w", encoding="utf-8").write(modelo)
        r = cli.post(u"/api/idioma", json={u"idioma": u"fr"})
        checar(u"POST /api/idioma grava (e o portao do aceite deixa passar)",
               r.status_code == 200 and r.json().get(u"idioma") == u"fr",
               u"%s %s" % (r.status_code, r.text[:80]))
        checar(u"  e o config diz IDIOMA=fr", u"IDIOMA=fr" in texto())
        g = cli.get(u"/api/idioma").json()
        checar(u"GET /api/idioma diz o que vale e o que esta no config",
               g.get(u"idioma") == u"fr" and g.get(u"config") == u"fr",
               str(g)[:90])
        for corpo in ({u"idioma": u"klingon"}, [u"fr"], {}):
            r = cli.post(u"/api/idioma", json=corpo)
            checar(u"POST com %r e 400, e o config nao muda" % (corpo,),
                   r.status_code == 400 and u"IDIOMA=fr" in texto(),
                   u"%s %s" % (r.status_code, r.text[:60]))
        r = cli.post(u"/api/idioma", content=b"nao e json",
                     headers={u"Content-Type": u"application/json"})
        checar(u"POST sem JSON e 400", r.status_code == 400, str(r.status_code))
        j1 = cli.get(I.ROTA_JS)
        cli.post(u"/api/idioma", json={u"idioma": u"it"})
        j2 = cli.get(I.ROTA_JS, headers={u"If-None-Match": j1.headers.get(u"etag")})
        checar(u"depois da escolha, a marca velha recebe o corpo novo (200)",
               j2.status_code == 200
               and _json_de(j2.text, u"INICIAL") == u"it",
               u"%s %r" % (j2.status_code, _json_de(j2.text, u"INICIAL")))
        j3 = cli.get(I.ROTA_JS, headers={u"If-None-Match": j2.headers.get(u"etag")})
        checar(u"  e a marca nova recebe 304", j3.status_code == 304,
               str(j3.status_code))
    finally:
        if guardado is None:
            os.environ.pop("RADAI_CONFIG", None)
        else:
            os.environ["RADAI_CONFIG"] = guardado
        shutil.rmtree(base, ignore_errors=True)


def teste_aviso_documento():
    secao(u"documento legal: avisa em cada idioma, e nao traduz o texto")
    import radai_phrases as F

    d = F.construir()
    aviso = None
    for linha in F.TABELA:
        if u"vale em português" in linha[0]:
            aviso = F.normalizar(linha[0])
    checar(u"a frase do aviso existe na tabela", aviso is not None)
    if aviso:
        faltam = [c for c in F.CODIGOS if aviso not in d[c]]
        checar(u"o aviso esta nos onze idiomas", not faltam, str(faltam))

    termos = ler("app/radai_consent.py")
    longas = [F.normalizar(l[0]) for l in F.TABELA if len(F.normalizar(l[0])) > 160]
    dentro = [t for t in longas if t and t != aviso and F.normalizar(termos).count(t)]
    checar(u"nenhum paragrafo dos termos entrou na tabela", not dentro,
           str(dentro[:1])[:120])


from html.parser import HTMLParser as _HTMLParser

_VAZIOS = frozenset((u"area", u"base", u"br", u"col", u"embed", u"hr", u"img",
                     u"input", u"link", u"meta", u"param", u"source",
                     u"track", u"wbr"))

_REGRAS_COPIADAS = (
    u"if(el.getAttribute('data-radai-t')==='1') return;",
    u"if(el.closest('.radai-lang')) return;",
    u"if(el.querySelector&&el.querySelector(FRAGIL)) return;",
    u"if(el.querySelector&&el.querySelector(ANCORA)) return;",
    u"if(el.querySelector&&el.querySelector('[data-radai-t=\"1\"]')) return;",
    u"if(!chave||fixo(chave)) return;",
    u"if(tag==='SCRIPT'||tag==='STYLE'||tag==='TEXTAREA') continue;",
    u"if(pai&&pai.closest&&pai.closest('.radai-lang')) continue;",
    u"if(pai&&pai.getAttribute&&pai.getAttribute('data-radai-t')==='1') "
    u"continue;",
)


class _No(object):
    __slots__ = ("tag", "attrs", "pai", "filhos", "trocado")

    def __init__(self, tag, attrs, pai):
        self.tag = tag
        self.attrs = dict((k, u"" if v is None else v) for k, v in attrs)
        self.pai = pai
        self.filhos = []
        self.trocado = False

    def classes(self):
        return self.attrs.get(u"class", u"").split()


class _Texto(object):
    __slots__ = ("v", "pai")

    def __init__(self, v, pai):
        self.v = v
        self.pai = pai


class _Arvore(_HTMLParser):

    def __init__(self):
        _HTMLParser.__init__(self, convert_charrefs=True)
        self.raiz = _No(u"#documento", [], None)
        self.cur = self.raiz

    def handle_starttag(self, tag, attrs):
        no = _No(tag, attrs, self.cur)
        self.cur.filhos.append(no)
        if tag not in _VAZIOS:
            self.cur = no

    def handle_startendtag(self, tag, attrs):
        self.cur.filhos.append(_No(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        c = self.cur
        while c is not None and c.tag != tag:
            c = c.pai
        if c is not None and c.pai is not None:
            self.cur = c.pai

    def handle_data(self, dado):
        self.cur.filhos.append(_Texto(dado, self.cur))


def _elementos(no):
    for f in no.filhos:
        if isinstance(f, _No):
            yield f
            for g in _elementos(f):
                yield g


def _textos(no):
    for f in no.filhos:
        if isinstance(f, _Texto):
            yield f
        else:
            for g in _textos(f):
                yield g


def _acima(no):
    while isinstance(no, _No):
        yield no
        no = no.pai


def _literal_js(js, nome):
    marca = u"var %s=" % nome
    i = js.find(marca)
    if i < 0:
        return None
    partes = []
    for ln in js[i + len(marca):].splitlines():
        if ln.strip().startswith(u"//"):
            continue
        m = re.match(r"^((?:[^';]|'[^']*')*);", ln)
        if m:
            partes.append(m.group(1))
            break
        partes.append(ln)
    return u"".join(re.findall(r"'([^']*)'", u" ".join(partes)))


def _seletor(item):
    m = re.match(r"^([a-z][a-z0-9]*)$", item)
    if m:
        t = m.group(1)
        return lambda n: n.tag == t
    m = re.match(r"^\.([\w-]+)$", item)
    if m:
        c = m.group(1)
        return lambda n: c in n.classes()
    m = re.match(r"^\.([\w-]+)>([a-z][a-z0-9]*)$", item)
    if m:
        c, t = m.groups()
        return lambda n: (n.tag == t and isinstance(n.pai, _No)
                          and c in n.pai.classes())
    m = re.match(r"^\[([\w-]+)\]$", item)
    if m:
        a = m.group(1)
        return lambda n: a in n.attrs
    raise ValueError(u"seletor que a simulacao nao sabe ler: %r" % item)


def _documentos_do_tradutor(js):
    i = js.find(u"function avisarDocumento(")
    j = js.find(u"function ", i + 10) if i >= 0 else -1
    corpo = js[i:j] if i >= 0 else u""
    rotas = re.findall(r"p!=='(/[^']*)'", corpo)
    m = re.search(r"document\.querySelector\('([^']+)'\)\|\|document\.body",
                  corpo)
    return rotas, (m.group(1) if m else None)


def _pagina_da_rota(rota):
    import radai_menu
    for n in _componentes.nomes("app"):
        if not n.endswith(".py"):
            continue
        try:
            arv = ast.parse(io.open(_componentes.fonte("app/" + n),
                                    encoding="utf-8").read())
        except Exception:
            continue
        for no in ast.walk(arv):
            if not isinstance(no, ast.FunctionDef):
                continue
            decorada = any(
                isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and d.func.attr == "get" and d.args
                and isinstance(d.args[0], ast.Constant)
                and d.args[0].value == rota
                for d in no.decorator_list)
            if not decorada:
                continue
            for r in ast.walk(no):
                v = getattr(r, "value", None) if isinstance(r, ast.Return) \
                    else None
                if (isinstance(v, ast.Call)
                        and isinstance(v.func, ast.Attribute)
                        and v.func.attr == "aplicar_leitura"
                        and len(v.args) == 2
                        and isinstance(v.args[0], ast.Name)
                        and isinstance(v.args[1], ast.Constant)):
                    mod = __import__(n[:-3])
                    bruto = getattr(mod, v.args[0].id)
                    bruto = bruto() if callable(bruto) else bruto
                    return radai_menu.aplicar_leitura(bruto, v.args[1].value)
            raise ValueError(u"%s (%s): a rota nao devolve "
                             u"aplicar_leitura(NOME, chave)" % (rota, n))
    raise ValueError(u"%s: nenhuma funcao de app/ serve esta rota" % rota)


def _trocado_no_documento(pagina, chaves, js, conteiner):
    import radai_languages as I
    listas = {}
    for nome in (u"BLOCOS", u"FRAGIL", u"ANCORA"):
        v = _literal_js(js, nome)
        if not v:
            raise ValueError(u"o JS do tradutor nao tem `var %s`" % nome)
        listas[nome] = [s.strip() for s in v.split(u",") if s.strip()]
    e_bloco = [_seletor(s) for s in listas[u"BLOCOS"]]
    fragil = [_seletor(s) for s in listas[u"FRAGIL"]]
    ancora = [_seletor(s) for s in listas[u"ANCORA"]]
    e_cont = _seletor(conteiner)
    fixos = set(I.NAO_TRADUZIR)

    def fixo(t):
        nu = re.sub(u"^[\\s\"'(\\[]+|[\\s\"'.,;:)\\]]+$", u"", t)
        return nu in fixos

    raiz = _Arvore()
    raiz.feed(pagina)
    raiz.close()
    corpo = next((e for e in _elementos(raiz.raiz) if e.tag == u"body"),
                 raiz.raiz)
    cont = next((e for e in _elementos(corpo) if e_cont(e)), None)
    if cont is None:
        raise ValueError(u"a pagina nao tem o conteiner %s" % conteiner)

    def no_documento(el):
        return any(a is cont for a in _acima(el))

    def algum(el, testes):
        return any(t(d) for d in _elementos(el) for t in testes)

    def lingua(el):
        return any(u"radai-lang" in a.classes() for a in _acima(el))

    fora = []
    for el in list(_elementos(corpo)):
        if not any(t(el) for t in e_bloco):
            continue
        if any(a.trocado for a in _acima(el.pai)):
            continue
        if el.attrs.get(u"data-radai-t") == u"1" or lingua(el):
            continue
        if algum(el, fragil) or algum(el, ancora):
            continue
        if any(d.attrs.get(u"data-radai-t") == u"1" for d in _elementos(el)):
            continue
        chave = _norm_do_tradutor(u"".join(t.v for t in _textos(el)))
        if not chave or fixo(chave) or chave not in chaves:
            continue
        el.trocado = True
        el.attrs[u"data-radai-t"] = u"1"
        if no_documento(el):
            fora.append((1, el.tag, chave))
    for t in _textos(corpo):
        pai = t.pai
        if pai.tag in (u"script", u"style", u"textarea") or lingua(pai):
            continue
        if any(a.trocado for a in _acima(pai)):
            continue
        if pai.attrs.get(u"data-radai-t") == u"1":
            continue
        chave = _norm_do_tradutor(t.v)
        if not chave or fixo(chave) or chave not in chaves:
            continue
        if no_documento(pai):
            fora.append((2, pai.tag, chave))
    return fora


def _norm_do_tradutor(texto):
    import radai_phrases as F
    return F.normalizar(texto)


_ISCA_DOC = (u"<html><body><header class=\"rc-topo\"><b>ACHADO</b></header>"
             u"<div class=\"%s\"><p>Quando uma delas roda, o log anuncia com a "
             u"palavra <b%s>ACHADO</b>, e o que ela devolve sai num arquivo "
             u"proprio.</p><ul><li%s>ACHADO</li></ul></div></body></html>")


def teste_documento_nao_passa_pelo_dicionario():
    secao(u"documento legal: nenhum PEDACO do texto passa pelo dicionario")
    import radai_phrases as F
    import radai_languages as I

    js = I.corpo_js()
    faltam = [r for r in _REGRAS_COPIADAS if r not in js]
    checar(u"o tradutor ainda tem as regras de pulo que a simulacao copia",
           not faltam, u"\n         · " + u"\n         · ".join(faltam[:4]))
    _sem = js.replace(_REGRAS_COPIADAS[-1], u"")
    checar(u"  (isca) sem o pulo do `data-radai-t` no passo 2, a conferencia "
           u"acusa a regra",
           [r for r in _REGRAS_COPIADAS if r not in _sem]
           == [_REGRAS_COPIADAS[-1]])
    try:
        _seletor(u"div p")
        _leu = True
    except ValueError:
        _leu = False
    checar(u"  (isca) seletor de forma que a simulacao nao conhece LEVANTA, "
           u"em vez de ser ignorado", not _leu)
    rotas, cont = _documentos_do_tradutor(js)
    checar(u"o aviso de documento declara as telas e o conteiner do texto "
           u"(%s em %s)" % (cont, u", ".join(rotas)),
           u"/termos" in rotas and len(rotas) >= 2 and bool(cont),
           str((rotas, cont)))
    if not (rotas and cont):
        return
    chaves = set()
    for v in F.construir().values():
        chaves.update(v)

    for rota in rotas:
        try:
            trocas = _trocado_no_documento(_pagina_da_rota(rota), chaves,
                                           js, cont)
        except Exception as e:
            checar(u"%s: a simulacao montou a tela servida" % rota, False,
                   u"%s: %s" % (type(e).__name__, str(e)[:120]))
            continue
        checar(u"%s: nenhum no do texto do documento casa chave do "
               u"dicionario" % rota, not trocas,
               u"\n         · " + u"\n         · ".join(
                   u"passo %d, <%s> %r" % (p, t, k[:48])
                   for (p, t, k) in trocas[:9]))
        if rota == u"/termos":
            checar(u"  e os Termos dizem ACHADO em qualquer idioma, que e a "
                   u"palavra que o log escreve (REGRA B)",
                   u"ACHADO" not in [k for (_p, _t, k) in trocas],
                   u"o <b>ACHADO</b> casa a chave dos selos; marque-o com "
                   u"data-radai-t=\"1\" no radai_consent")

    classe = cont.lstrip(u".") if cont.startswith(u".") else u"env"
    isca = _ISCA_DOC % (classe, u"", u"")
    trocas = _trocado_no_documento(isca, {u"ACHADO"}, js, cont)
    checar(u"  (isca) a chave CURTA num no do paragrafo e acusada -- o caso "
           u"que a checagem de 160 caracteres deixava passar",
           (2, u"b", u"ACHADO") in trocas, str(trocas))
    checar(u"  (isca) e o bloco que E a chave inteira tambem (o passo 1)",
           (1, u"li", u"ACHADO") in trocas, str(trocas))
    checar(u"  (isca) e o cabecalho, que e interface, NAO entra na conta",
           len(trocas) == 2, str(trocas))
    marcada = _ISCA_DOC % (classe, u" data-radai-t=\"1\"",
                           u" data-radai-t=\"1\"")
    trocas = _trocado_no_documento(marcada, {u"ACHADO"}, js, cont)
    checar(u"  (isca) marcado com data-radai-t=\"1\", o mesmo texto passa "
           u"-- e o conserto que o dono dos Termos aplica", not trocas,
           str(trocas))
    try:
        crua = re.sub(r"\s+data-radai-t=\"1\"", u"",
                      _pagina_da_rota(u"/termos"))
        trocas = _trocado_no_documento(crua, chaves, js, cont)
        checar(u"  (isca) os Termos servidos, sem as marcas, voltam a "
               u"trocar o ACHADO", u"ACHADO" in [k for (_p, _t, k) in trocas],
               str(trocas[:4]))
    except Exception as e:
        checar(u"  (isca) os Termos servidos montam sem as marcas", False,
               str(e)[:120])


_ISCA_BOTAO = (
    u"<html><body><table><tr data-i=\"0\"><td class=\"vr-acao\">"
    u"<button class=\"mini\" onclick=\"vrAbrirDoAcervo(0)\">abrir</button>"
    u"</td></tr></table></body></html>",
    u"<html><body><table><tbody><tr class=\"linha\" data-i=\"0\">"
    u"<td class=\"vr-acao\"><button class=\"mini\" data-abrir=\"0\">abrir"
    u"</button></td></tr></tbody></table></body></html>",
)


def teste_o_botao_sobrevive_a_traducao():
    secao(u"o botao dentro de um bloco sobrevive a traducao (o «abrir» do /ver)")
    import radai_phrases as F
    import radai_languages as I

    js = I.corpo_js()
    chaves = set()
    for v in F.construir().values():
        chaves.update(v)
    checar(u"a isca e real: «abrir» e chave do dicionario", u"abrir" in chaves)
    fragil = [s.strip() for s in (_literal_js(js, u"FRAGIL") or u"").split(u",")]
    checar(u"`button` esta em FRAGIL (bloco com controle dentro nao e "
           u"reescrito por cima)", u"button" in fragil, u", ".join(fragil))

    js_sem = re.sub(u"(var FRAGIL='[^']*?)button,", u"\\1", js)
    for n, isca in enumerate(_ISCA_BOTAO, 1):
        trocas = _trocado_no_documento(isca, chaves, js, u".vr-acao")
        checar(u"linha %d do /ver: a celula NAO e reescrita (o botao fica)" % n,
               (1, u"td", u"abrir") not in trocas, str(trocas))
        checar(u"  e o botao se traduz sozinho (o texto nao fica em portugues)",
               (1, u"button", u"abrir") in trocas, str(trocas))
        trocas = _trocado_no_documento(isca, chaves, js_sem, u".vr-acao")
        checar(u"  (isca) sem `button` em FRAGIL, a celula volta a apagar o "
               u"botao", js_sem != js and (1, u"td", u"abrir") in trocas,
               str(trocas))


def teste_peso():
    secao(u"peso: o que cada tela carrega, e o que o navegador guarda")
    import radai_languages as I

    costura = len(I._js().encode("utf-8")) / 1024.0
    checar(u"a costura de cada tela cabe em 8 KB (%.1f KB)" % costura,
           costura < 8, u"%.1f KB" % costura)
    checar(u"e ela NAO carrega o dicionario",
           u"@FRASES@" not in I._js() and u'"pt-BR"' not in I._js())

    corpo = len(I.corpo_js().encode("utf-8")) / 1024.0
    checar(u"o dicionario cabe em 2 MB (%.0f KB)" % corpo, corpo < 2048,
           u"%.0f KB" % corpo)

    checar(u"a costura aponta para a rota", I.ROTA_JS in I._js())
    checar(u"e ha quem a monte", callable(getattr(I, "montar", None)))
    v = ler("app/radai_watcher.py")
    checar(u"o vigia monta o dicionario", u"radai_languages.montar(app)" in v)

    marca = I.etag_js()
    checar(u"o ETag existe e e estavel", marca and marca == I.etag_js(), marca)

    try:
        import radai_consent as CS
        checar(u"o portao do aceite deixa o dicionario passar",
               I.ROTA_JS in CS.LIVRES, str(CS.LIVRES))
    except Exception as e:
        checar(u"radai_consent importa", False, str(e)[:60])


def teste_frase_traduzida_e_alcancavel():
    secao(u"a frase tem chave E esta ao alcance do tradutor")
    import re as _re
    import html as _html
    import radai_modules as MD
    import radai_phrases as PH

    chaves = set(t0[0] for t0 in PH.TABELA)

    for ch in sorted(MD.MODULOS):
        linha = (MD.MODULOS.get(ch) or {}).get("linha")
        if not linha:
            continue
        txt = _html.unescape(_re.sub(r"<[^>]+>", "", linha)).strip()
        checar(u"a tarja de `%s` tem chave na tabela" % ch, txt in chaves,
               txt[:60])

    # GUARDA: a tarja é o alerta de `radai_ui.alerta`, montado por `radai_modules.linha_clinica`.
    trecho = MD.linha_clinica(u"bridge")
    checar(u"e o span da tarja leva `data-radai-frase`",
           "data-radai-frase" in trecho,
           trecho.replace(chr(10), " ")[:78])

    idi = io.open(_componentes.fonte("app/radai_languages.py"),
                  encoding="utf-8").read()
    checar(u"e `BLOCOS` continua conhecendo `[data-radai-frase]`",
           "[data-radai-frase]" in idi)
    checar(u"e a tarja de rodape (`.rodape-clinico>span`) continua na lista",
           ".rodape-clinico>span" in idi,
           u"ela ja sumiu uma vez, com o mesmo sintoma")


def teste_o_titulo_da_aba_e_traduzido():
    secao(u"o título da aba troca de idioma")
    js = io.open(_componentes.fonte("app/radai_languages.py"),
                 encoding="utf-8", errors="replace").read()
    checar(u"o tradutor escreve em `document.title`", "document.title" in js)
    checar(u"  e guarda o título de fábrica antes de trocar",
           "__radaiTitulo0" in js)
    i = js.find("function traduzir(")
    j = js.find("\n function ", i + 10)
    corpo = js[i:j] if i >= 0 else ""
    checar(u"e isso acontece DENTRO de `traduzir()`",
           "document.title" in corpo and "__radaiTitulo0" in corpo,
           u"fora da função a linha nunca roda")
    checar(u"o corte usa o separador que as telas escrevem (`·`)",
           u"\\u00b7" in corpo or u"·" in corpo)
    sys.path.insert(0, APP)
    try:
        import radai_phrases as _P
    finally:
        sys.path.pop(0)
    chaves = {l[0] for l in _P.TABELA}
    for rotulo in (u"Rodar agora", u"Configurações"):
        checar(u"o rótulo `%s` tem chave (senão a aba fica em português)"
               % rotulo, rotulo in chaves)


def teste_texto_repintado_por_js_perde_a_marca():
    secao(u"texto repintado por JS perde a marca de traduzido")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    import radai_ui
    checar(u"`uiTexto` existe", u"window.uiTexto = function" in radai_ui.JS)
    def _corpo(nome):
        i = radai_ui.JS.index(u"window.%s = function" % nome)
        return radai_ui.JS[i:radai_ui.JS.index(chr(10) + u" };", i)]

    checar(u"  e ele TIRA a marca",
           u"removeAttribute('data-radai-t')" in _corpo(u"uiTexto"),
           u"sem isto ele e um `textContent` com outro nome")
    checar(u"`uiHTML` tira a marca dos filhos tambem",
           u"window.uiHTML = function" in radai_ui.JS
           and u"querySelectorAll('[data-radai-t]')" in _corpo(u"uiHTML"),
           u"um span marcado dentro de conteudo novo congela aquele pedaco")

    import radai_batch, radai_todo
    ALVOS = ((u"radai_batch", radai_batch.PAGINA,
              (u"cd_night_tx", u"cartver", u"conta")),
             (u"radai_todo", radai_todo.HTML, (u"radai_tf_sub",)))
    import re
    for nome, fonte, ids in ALVOS:
        for i in ids:
            achou = re.search(
                r"getElementById\(['\"]%s['\"]\)\.textContent\s*=" % i, fonte)
            checar(u"%s: `%s` nao e escrito por textContent cru" % (nome, i),
                   not achou, u"use `uiTexto`")
    checar(u"e os repintores do lote usam `uiTexto`",
           radai_batch.PAGINA.count(u"uiTexto(") >= 3,
           u"%d chamada(s)" % radai_batch.PAGINA.count(u"uiTexto("))
    checar(u"e a barra da direita tambem",
           u"uiTexto(document.getElementById('radai_tf_sub')" in radai_todo.HTML)

    import radai_panel

    def _corpo_fn(fonte, nome):
        i = fonte.find(u"function %s(" % nome)
        if i < 0:
            return u""
        j = fonte.find(chr(10) + u"function ", i + 10)
        return fonte[i:(j if j > 0 else len(fonte))]

    def _pelo_tradutor(corpo):
        return u"uiHTML(" in corpo or u"uiTexto(" in corpo

    _cfg = radai_panel.PAGINA_CONFIG
    for _fn in (u"cfBarra", u"cfPintar"):
        _c = _corpo_fn(_cfg, _fn)
        checar(u"radai_panel: `%s` repinta pelo tradutor" % _fn,
               bool(_c) and _pelo_tradutor(_c), _c[:120] or u"(ausente)")
    _velho = _corpo_fn(_cfg, u"cfPintar").replace(
        u"if(window.uiHTML) uiHTML(r, h); else r.innerHTML = h;",
        u"r.innerHTML=h;")
    checar(u"  (isca) o `cfPintar` de antes, com `innerHTML` cru, e acusado",
           not _pelo_tradutor(_velho), _velho[-80:])


def _selos_sem_traducao(tabela, codigos):
    import radai_phrases as F
    por_pt = dict((F.normalizar(l[0]), l) for l in tabela)
    fora = []
    for selo in SELOS_TRADUZIDOS:
        linha = por_pt.get(F.normalizar(selo))
        for i, cod in enumerate(codigos, start=1):
            if (linha is None or i >= len(linha)
                    or not F.normalizar(linha[i])):
                fora.append((selo, cod))
    return fora


SELOS_TRADUZIDOS = (u"ACHADO", u"fast", u"regular", u"slow", u"ultra-slow")


def teste_os_selos_sao_traduzidos():
    secao(u"os selos da linha da serie saem na lingua da estacao")
    import radai_phrases as F
    falta = _selos_sem_traducao(F.TABELA, F.CODIGOS)
    checar(u"ACHADO e fast/regular/slow/ultra-slow tem coluna nos onze "
           u"idiomas", not falta, str(falta[:8]))
    d = F.construir()
    checar(u"  e numa estacao em alemao os cinco trocam de palavra",
           all(d["de"].get(F.normalizar(x)) for x in SELOS_TRADUZIDOS),
           str([(x, d["de"].get(x)) for x in SELOS_TRADUZIDOS]))
    _rot = F.normalizar(u"Nódulos pulmonares — ACHADO (lung_nodules)")
    checar(u"  e o ACHADO usa a MESMA palavra dos rotulos das tasks de "
           u"achado (a caixa e o selo dizem a mesma coisa)",
           all(d[c].get(u"ACHADO") and d[c][u"ACHADO"] in d[c].get(_rot, u"")
               for c in F.CODIGOS),
           str(dict((c, d[c].get(u"ACHADO")) for c in F.CODIGOS)))
    sem = [l for l in F.TABELA if F.normalizar(l[0]) != u"slow"]
    n = len(_selos_sem_traducao(sem, F.CODIGOS))
    checar(u"  (isca) sem a linha do `slow`, a checagem acusa os onze "
           u"idiomas", n == 11, str(n))


_MARCA_DO_MOLDE = re.compile(r"%s|%d|\{\d+\}")
_REGRAS_DO_MOLDE = (
    u"var novo=d[chave];\n   if(!novo) novo=porMolde(cod,chave,el);",
    u"var novo=d[chave];\n   if(!novo) novo=porMolde(cod,chave,no.parentNode);",
    u"if(el&&el.closest&&(el.closest('.env')\n"
    u"      ||el.closest('[data-radai-t=\"1\"]:not([data-radai-tr])')))",
    u"if(partes.join('').length<12) return;",
    u"if((tr.match(MARCA)||[]).length!==km.length) return;",
)


def _moldes(d):
    fora = []
    for k, tr in sorted(d.items()):
        km = _MARCA_DO_MOLDE.findall(k)
        if not km or not tr:
            continue
        if len(_MARCA_DO_MOLDE.findall(tr)) != len(km):
            continue
        partes = _MARCA_DO_MOLDE.split(k)
        if len(u"".join(partes)) < 12:
            continue
        fora.append((re.compile(u"^" + u"(.+?)".join(re.escape(p)
                                                     for p in partes) + u"$"),
                     tr, km))
    return fora


def _por_molde_simulado(d, chave):
    for rx, tr, km in _moldes(d):
        m = rx.match(chave)
        if not m:
            continue
        seq = [0]

        def _troca(mo):
            mk = mo.group(0)
            if mk.startswith(u"{"):
                return m.group(km.index(mk) + 1) if mk in km else mk
            pos = [i for i, x in enumerate(km) if x.startswith(u"%")]
            if seq[0] < len(pos):
                v = m.group(pos[seq[0]] + 1)
                seq[0] += 1
                return v
            return mk
        return _MARCA_DO_MOLDE.sub(_troca, tr)
    return u""


def teste_o_tradutor_por_molde():
    secao(u"o tradutor por molde: frase com valor dentro")
    import radai_languages as I
    import radai_phrases as F
    js = I.corpo_js()
    faltam = [r for r in _REGRAS_DO_MOLDE if r not in js]
    checar(u"as guardas do molde estao no JS, na letra", not faltam,
           u" | ".join(f[:50] for f in faltam))
    d = F.construir()
    idiomas = [c for c in F.CODIGOS if c in d]
    chaves_com_marca = sorted(k for k in d.get("en", {})
                              if _MARCA_DO_MOLDE.search(k))
    checar(u"ha chaves com marcador no dicionario (as do limpador)",
           len(chaves_com_marca) >= 3, str(len(chaves_com_marca)))
    sem = []
    for c in idiomas:
        ms = set(tr for _rx, tr, _km in _moldes(d[c]))
        for k in chaves_com_marca:
            if d[c].get(k) and d[c][k] not in ms:
                sem.append((c, k[:30]))
    checar(u"toda chave com marcador vira molde nos %d idiomas" % len(idiomas),
           not sem, str(sem[:4]))
    k1 = next((k for k in chaves_com_marca
               if k.startswith(u"Esta máquina tem %s, e o torch")), None)
    valores = (u"NVIDIA Quadro P2200", u"2.5.1+cu121", u"12.1")
    tela = (k1 % valores) if k1 else u""
    esperado = (d["de"].get(k1, u"") % valores) if k1 else u""
    sai = _por_molde_simulado(d["de"], tela)
    checar(u"simulacao: a frase com o nome da placa sai em alemao, com os "
           u"tres valores intactos",
           bool(sai) and sai == esperado and all(v in sai for v in valores),
           sai[:90])
    sem_marca = dict(d["de"])
    if k1:
        sem_marca[k1] = sem_marca[k1].replace(u"%s", u"X", 1)
    checar(u"  (isca) a traducao sem um marcador nao vira molde",
           not _por_molde_simulado(sem_marca, tela))
    checar(u"  (isca) a parte fixa mexida nao casa",
           not _por_molde_simulado(d["de"], tela.replace(u"torch deste",
                                                         u"torch daquele")))
    checar(u"  (isca) a frase com um resto sem chave nao casa (tudo ou nada)",
           not _por_molde_simulado(d["de"], tela + u" E mais uma frase."))

    import shutil as _sh
    import subprocess as _sp
    import json as _json
    import tempfile as _tf
    node = _sh.which("node")
    if not node:
        checar(u"`node` nesta maquina (PULADO: a simulacao acima vale)", True)
        return
    try:
        a = js.index(u" var MARCA=")
        b = js.index(u" function traduzir(cod){")
    except ValueError:
        checar(u"o trecho do molde achado no JS", False)
        return
    prog = (u"var FRASES = %s;\n" % _json.dumps({"de": d["de"]},
                                               ensure_ascii=False)
            + js[a:b] + u"\n"
            + u"var env = {closest: function(s){ return s === '.env' }};\n"
            + u"var marc = {closest: function(s){ return s.indexOf("
              u"'data-radai-t') >= 0 }};\n"
            + u"var trad = {closest: function(s){ return s.indexOf("
              u"'data-radai-t') >= 0 && s.indexOf(':not([data-radai-tr])') < 0 }};\n"
            + u"console.log(JSON.stringify([porMolde('de', %s, null),"
              u" porMolde('de', %s, env), porMolde('de', %s, marc),"
              u" porMolde('de', %s, null), porMolde('de', %s, trad)]));"
            % (_json.dumps(tela, ensure_ascii=False),
               _json.dumps(tela, ensure_ascii=False),
               _json.dumps(tela, ensure_ascii=False),
               _json.dumps(tela + u" E mais uma frase.", ensure_ascii=False),
               _json.dumps(tela, ensure_ascii=False)))
    tmp = _tf.mkdtemp(prefix="radai_t_molde_")
    try:
        arq = os.path.join(tmp, "molde.js")
        io.open(arq, "w", encoding="utf-8").write(prog)
        r = _sp.run([node, arq], capture_output=True, text=True,
                    encoding="utf-8", timeout=60)
        try:
            saida = _json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            saida = [u"(erro) " + (r.stderr or u"")[-160:]]
    finally:
        _sh.rmtree(tmp, ignore_errors=True)
    checar(u"node: o JS de verdade da a mesma frase que a simulacao",
           saida and saida[0] == esperado, str(saida[:1])[:120])
    checar(u"  e NADA dentro do documento (`.env`) nem debaixo de "
           u"`data-radai-t`", len(saida) == 5 and saida[1] == u""
           and saida[2] == u"", str(saida[1:3]))
    checar(u"  e a frase com um resto sem chave fica em portugues",
           len(saida) == 5 and saida[3] == u"", str(saida[3:4]))
    checar(u"  e o molde VALE no bloco cujo texto o proprio tradutor ja trocou "
           u"(o title da celula traduzida)",
           len(saida) == 5 and saida[4] == esperado, str(saida[4:]))
    checar(u"o passo 1 deixa a sua marca propria (`data-radai-tr`) ao traduzir",
           u"el.setAttribute('data-radai-tr','1');" in js)


def teste_os_moldes_da_l3():
    secao(u"os moldes da L3: o texto que o codigo produz casa a chave")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    import radai_phrases as F
    import radai_triage
    import radai_version
    import radai_elastic_screen
    d = F.construir()

    def _s(uid, esp, cortes, n=0, data="20260901", desc=u"x"):
        return {"uid": uid, "espessura": esp, "espessura_mm": esp,
                "cortes": cortes, "count": cortes, "axial": True,
                "modalidade": "CT", "estudo": "E1", "date": data, "n": n,
                "desc": desc}
    motivos = []
    for grupo in (
            [_s("A", 3.0, 200, 1), _s("B", 5.0, 120, 2)],
            [_s("A", 3.0, 200, 1), _s("B", 3.0, 60, 2)],
            [_s("A", 2.5, 144, 2, "20260903"), _s("B", 2.99, 120, 1)],
            [_s("AVG", 3.0, 200, 50, desc=u"CT THORAX AVE")]
            + [_s("F%d" % i, 3.0, 200, 60 + i, desc=u"CT %d%%" % (i * 10))
               for i in range(11)]):
        motivos.extend(radai_triage.escolher_simulacao(grupo).values())
    pedacos = [p for m in motivos for p in m.split(u"; ")]
    checar(u"o motivo da sugestao chega em frases separadas por «; » "
           u"(%d frases de %d motivos)" % (len(pedacos), len(motivos)),
           len(motivos) == 4 and len(pedacos) >= 9, str(pedacos[:3])[:120])
    import datetime
    _hoje = datetime.date(2026, 9, 27)
    idades = []
    for data in (u"", u"2026-09-26", u"2026-06-01", u"2026-08-20",
                 u"2027-01-01"):
        _orig = None
        try:
            import radai_delivery
            _orig = radai_delivery.carimbo
            radai_delivery.carimbo = (lambda recarregar=False, _d=data:
                                      {"data": _d})
            idades.append(radai_version.idade(hoje=_hoje).get("frase") or u"")
        finally:
            if _orig is not None:
                radai_delivery.carimbo = _orig
    idades = [f for f in idades if f]
    checar(u"a idade do build tem as cinco frases", len(idades) == 5,
           str(idades)[:120])
    rotulo = radai_elastic_screen.rotulo_de(
        {"numero": 3, "cortes": 30, "esp": 3.0, "date": "20260926",
         "curto": "09067519"}, 1)
    frases = pedacos + idades + [rotulo]
    ruins = []
    for c in F.CODIGOS:
        for f in frases:
            exata = d[c].get(F.normalizar(f))
            sai = exata or _por_molde_simulado(d[c], F.normalizar(f))
            if not sai or sai == f:
                ruins.append((c, f[:50]))
    checar(u"cada frase que o codigo produz sai traduzida nos %d idiomas "
           u"(%d frases)" % (len(F.CODIGOS), len(frases)), not ruins,
           str(ruins[:4])[:160])
    _de = _por_molde_simulado(d["de"], F.normalizar(rotulo))
    checar(u"  e os valores passam intactos (o descritor do Elastic RT)",
           all(v in _de for v in (u"[1]", u"3", u"30", u"3.00 mm",
                                  u"09067519")), _de[:90])
    isca = [p.replace(u"piso", u"chao") for p in pedacos if u"piso" in p]
    checar(u"  (isca) uma palavra trocada no codigo e o casamento some",
           bool(isca) and all(not _por_molde_simulado(d["de"], F.normalizar(i))
                              and not d["de"].get(F.normalizar(i))
                              for i in isca), str(isca[:1])[:90])


def _passo3_do_tradutor(js):
    m = re.search(r"\n[ \t]*\[[^\]\n]*\]\.forEach\(function\(at\)", js)
    b = js.find(u"var rtl=false", m.start()) if m else -1
    return js[m.start() + 1:b] if b > 0 else u""


def _passo3_ok(trecho):
    codigo = u"\n".join(l for l in trecho.splitlines()
                        if not l.strip().startswith(u"//"))
    lista = re.search(r"\[([^\]]*)\]\.forEach", codigo)
    atributos = lista.group(1) if lista else u""
    return (u"'placeholder'" in atributos, u"porMolde(" in codigo)


def _placeholders_de_tela():
    fora = {}
    for n in _componentes.nomes("app"):
        if not n.endswith(".py") or n == "radai_phrases.py":
            continue
        arv = ast.parse(io.open(_componentes.fonte("app/" + n), encoding="utf-8").read())
        for no in ast.walk(arv):
            if not (isinstance(no, ast.Constant) and isinstance(no.value, str)):
                continue
            for m in re.finditer(r'placeholder="([^"]*)"', no.value):
                v = html.unescape(m.group(1))
                v = u" ".join(v.split())
                if u"'+" in v or u"+'" in v:
                    continue
                if not re.search(u"[A-Za-zÀ-ÿ]{3,}", v):
                    continue
                fora.setdefault(v, n)
    pnl = io.open(_componentes.fonte("app/radai_panel.py"), encoding="utf-8").read()
    i = pnl.find(u"var VAZIO_SIGNIFICA={")
    j = pnl.find(u"};", i)
    if 0 <= i < j:
        for m in re.finditer(r":\s*'([^']+)'", pnl[i:j]):
            v = m.group(1).replace(u"\\\\", u"\\").replace(u"\\)", u")")
            fora.setdefault(u" ".join(v.split()), u"radai_panel.py (VAZIO_SIGNIFICA)")
    return fora


def teste_os_atributos_e_as_frases_montadas():
    secao(u"onda 4b: placeholder, molde nos atributos e frases montadas")
    import radai_languages as I
    import radai_phrases as F
    js = I.corpo_js()
    trecho = _passo3_do_tradutor(js)
    le_ph, molde = _passo3_ok(trecho)
    checar(u"o passo 3 do tradutor le o `placeholder`", le_ph, trecho[:80])
    checar(u"  e casa o MOLDE nos atributos (depois da chave exata)", molde)
    velho = (u"// ── passo 3: `title` e `aria-label`\n"
             u"  ['title','aria-label'].forEach(function(at){\n"
             u"    var novo=d[chave];\n    if(novo) el.setAttribute(at,novo);\n")
    checar(u"  (isca) o passo 3 de antes reprova nas duas",
           _passo3_ok(velho) == (False, False), str(_passo3_ok(velho)))
    lista = re.search(r"\[([^\]]*)\]\.forEach", u"\n".join(
        l for l in trecho.splitlines() if not l.strip().startswith(u"//")))
    checar(u"  e continua sem `value`, `name` e `data-*` (o que se grava)",
           bool(lista) and all(x not in lista.group(1)
                               for x in (u"'value'", u"'name'", u"'data-")),
           lista.group(1) if lista else u"")

    d = F.construir()
    tab = dict((F.normalizar(t[0]), t) for t in F.TABELA)
    phs = _placeholders_de_tela()
    checar(u"os placeholders de frase foram achados (%d)" % len(phs),
           len(phs) >= 15, str(sorted(phs)[:3])[:120])
    sem = [(k, n) for k, n in sorted(phs.items())
           if not (tab.get(F.normalizar(k)) and all(tab[F.normalizar(k)][1:]))]
    checar(u"todo placeholder de frase tem chave nos doze idiomas",
           not sem, u"; ".join(u"%s (%s)" % (k[:40], n) for k, n in sem[:5]))
    checar(u"  (isca) um placeholder sem chave e acusado",
           not tab.get(F.normalizar(u"zzqx dica de campo sem chave zzqx")))

    montadas = [
        (u"Voltar para Radioterapia.AI Local", u"Radioterapia.AI Local"),
        (u"tirar Heart_ai do STUDY desta série", u"Heart_ai"),
        (u"devolver Bag_Bowel_ai ao STUDY", u"Bag_Bowel_ai"),
        (u"opacidade de Liver_ai", u"Liver_ai"),
        (u"abrir a ajuda de total_v3", u"total_v3"),
        (u"1 série(s) achada(s)", u"1"),
        (u"Nenhuma série contornada em C:\\EXAMES\\PAC. Séries sem RTSTRUCT ao "
         u"lado não aparecem aqui — processe antes.", u"C:\\EXAMES\\PAC"),
        (u"2 conjunto(s) de contorno nesta pasta", u"2"),
        (u"43 estruturas no STUDY, 0 fora", u"43"),
        (u"3 série(s) que esta máquina contornou já não estão no lugar — "
         u"a pasta foi movida ou apagada.", u"3"),
        (u"O «Rodar agora» está segmentando agora (desde 22:10).", u"22:10"),
        (u"O vigia está contornando uma série agora (desde 03:10).", u"03:10"),
        (u"Uma série está sendo contornada agora (desde 01:02).", u"01:02"),
    ]
    ruins = []
    for c in F.CODIGOS:
        for frase, valor in montadas:
            sai = d[c].get(F.normalizar(frase)) or _por_molde_simulado(
                d[c], F.normalizar(frase))
            if not sai or sai == frase or valor not in sai:
                ruins.append((c, frase[:40], sai[:40]))
    checar(u"as %d frases montadas saem traduzidas nos %d idiomas, com o "
           u"valor intacto" % (len(montadas), len(F.CODIGOS)), not ruins,
           str(ruins[:3])[:200])
    checar(u"  (isca) a forma de antes («43 / 0») nao casa chave nem molde",
           not d["de"].get(u"43 / 0") and not _por_molde_simulado(d["de"],
                                                                   u"43 / 0"))


def _ajuda_do_ts_mente(ajuda, funde_no_cru):
    return funde_no_cru and (u"índice 26" not in ajuda
                             or u"não recebe nada nosso" in ajuda)


def teste_a_ajuda_do_ts_cru_diz_o_indice_26():
    secao(u"COMP-08: a ajuda do «TS cru» diz que o índice 26 entra no sacro")
    import radai_sets as S
    import radai_phrases as F
    eng = io.open(os.path.join(os.path.dirname(S.__file__), "engine.py"),
                  encoding="utf-8").read()
    funde = u"OBSERVACAO_DO_INDICE_26_NO_CRU" in eng
    ts = [c for c in S.CONJUNTOS if c.get("cod") == "ts"][0]
    checar(u"a ajuda não afirma uma linha de base intocada que o código não entrega",
           not _ajuda_do_ts_mente(ts["ajuda"], funde), ts["ajuda"])
    d = F.construir()
    checar(u"  e tem as onze traduções",
           all(d[c].get(F.normalizar(ts["ajuda"])) for c in F.CODIGOS))
    checar(u"  (isca) a frase velha é acusada", _ajuda_do_ts_mente(
        u"a linha de base da comparação, e por isso não recebe nada nosso.", True))


def _literais_com(marca):
    fora = []
    for n in _componentes.nomes("app"):
        if not n.endswith(".py") or n == "radai_phrases.py":
            continue
        arv = ast.parse(io.open(_componentes.fonte("app/" + n),
                                encoding="utf-8").read())
        fora += [(n, no.value) for no in ast.walk(arv)
                 if isinstance(no, ast.Constant) and isinstance(no.value, str)
                 and marca in no.value]
    return fora


def _frases_do_segmentado(fontes):
    import radai_phrases as F
    fora = {}

    def _pega(txt, n):
        f = F.normalizar(html.unescape(txt))
        if re.search(u"[A-Za-zÀ-ÿ]{3,}", f) and f not in NAO_TRADUZ:
            fora.setdefault(f, n)
    for n, s in fontes:
        for m in re.finditer(r"<select\b([^>]*\bdata-ui-seg\b[^>]*)>(.*?)</select>",
                             s, re.S):
            for a in re.findall(r'aria-label="([^"]+)"', m.group(1)):
                _pega(a, n)
            for at, txt in re.findall(r"<option\b([^>]*)>([^<]*)</option>",
                                      m.group(2)):
                _pega(txt, n)
                for a in re.findall(r'(?:title|data-ui-balao)="([^"]+)"', at):
                    _pega(a, n)
    return fora


def _frases_do_estado_do_tema(src):
    m = re.search(r"var _tm = \((.*?)\);", src)
    if not m:
        return None
    return [f for f in re.findall(r"'([^']+)'", m.group(1)) if u" " in f]


def _frases_do_laudo_montadas(fonte):
    fora = []

    def _str(no):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            return [no.value]
        if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Mod):
            return _str(no.left)
        if isinstance(no, ast.IfExp):
            return _str(no.body) + _str(no.orelse)
        return []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Assign) or len(no.targets) != 1:
            continue
        alvo = no.targets[0]
        if isinstance(alvo, ast.Name) and alvo.id == "_titulo":
            fora += _str(no.value)
        elif (isinstance(alvo, ast.Subscript)
              and getattr(alvo.value, "id", "") == "enc"):
            fora += [s for s in _str(no.value)
                     if u"%" not in s and re.search(u"[a-zà-ÿ]{3,} ", s)]
    return fora


def _constante_do_modulo(rel, nome):
    p = _componentes.fonte(rel)
    if not os.path.isfile(p):
        return None
    for no in ast.parse(io.open(p, encoding="utf-8").read()).body:
        if (isinstance(no, ast.Assign) and len(no.targets) == 1
                and getattr(no.targets[0], "id", "") == nome
                and isinstance(no.value, ast.Constant)):
            return no.value.value
    return None


def _sem_os_doze(frases, tab):
    import radai_phrases as F
    return [f for f in frases
            if not (tab.get(F.normalizar(f))
                    and all(F.normalizar(c) for c in tab[F.normalizar(f)][1:]))]


def teste_as_frases_fora_do_html():
    secao(u"o que a medida do HTML não vê: o segmentado, o estado do tema, "
          u"o laudo montado e a linha do cartão")
    import radai_phrases as F
    tab = dict((F.normalizar(l[0]), l) for l in F.TABELA)

    seg = _frases_do_segmentado(_literais_com(u"data-ui-seg"))
    checar(u"[segmentado] achei as opções do seletor do tema (%d frases)"
           % len(seg), all(F.normalizar(f) in seg for f in
                           (u"Claro", u"Escuro", u"Sistema", u"Aparência",
                            u"Seguir o tema do sistema")),
           str(sorted(seg))[:160])
    sem = _sem_os_doze(seg, tab)
    checar(u"[segmentado] toda opção, `title` e `aria-label` tem os doze "
           u"idiomas, até a de uma palavra", not sem,
           u" | ".join(u"%s (%s)" % (f[:40], seg[f]) for f in sem[:5]))
    isca = _frases_do_segmentado([(u"isca.py",
        u'<select id="x" data-ui-seg aria-label="Aparência">'
        u'<option value="a" title="ZZQX dica sem chave">Claro</option>'
        u'<option value="b">Zzqxbranco</option></select>')])
    checar(u"  (isca) a opção e o `title` sem chave são acusados",
           sorted(_sem_os_doze(isca, tab)) == [u"ZZQX dica sem chave",
                                               u"Zzqxbranco"],
           str(sorted(_sem_os_doze(isca, tab))))

    tm = _frases_do_estado_do_tema(ler("app/radai_panel.py"))
    checar(u"[tema] achei as frases do estado do tema no painel",
           tm is not None and u"tema do sistema" in tm, str(tm))
    sem = _sem_os_doze(tm or [], tab)
    checar(u"[tema] cada uma tem os doze idiomas", not sem, str(sem))
    checar(u"  (isca) o estado sumido do fonte é acusado como tal",
           _frases_do_estado_do_tema(u"var _outro = ('a b');") is None)

    import radai_dicom as D
    with io.open(D.__file__, encoding="utf-8") as fh:
        lau = _frases_do_laudo_montadas(fh.read())
    checar(u"[laudo] achei os títulos montados e os valores fixos (%d)"
           % len(lau), len(lau) >= 6 and any(
               u"ImageOrientationPatient" in f for f in lau), str(lau[:3])[:160])
    sem = _sem_os_doze(lau, tab)
    checar(u"[laudo] cada um tem os doze idiomas", not sem,
           u" | ".join(f[:50] for f in sem[:5]))
    isca = _frases_do_laudo_montadas(
        u"_titulo = (u'ZZQX titulo sem chave %d.' % n)\n"
        u"enc[u'X'] = u'zzqx valor fixo sem chave'\n"
        u"enc[u'Y'] = u'%d grades' % n\n")
    checar(u"  (isca) o título montado e o valor fixo sem chave são acusados, "
           u"e o valor com número fica de fora",
           sorted(_sem_os_doze(isca, tab)) == [u"ZZQX titulo sem chave %d.",
                                               u"zzqx valor fixo sem chave"],
           str(isca))

    lin = _constante_do_modulo("app/radai_watcher.py",
                               "FRASE_DA_TRAVA_SOLTA_AO_ABRIR")
    checar(u"[cartão] a linha da trava solta ao abrir existe no vigia",
           isinstance(lin, str) and len(lin) > 20, str(lin)[:60])
    checar(u"[cartão] e tem os doze idiomas",
           isinstance(lin, str) and not _sem_os_doze([lin], tab))
    checar(u"  (isca) a constante de nome trocado é acusada como ausente",
           _constante_do_modulo("app/radai_watcher.py",
                                "FRASE_ZZQX_QUE_NAO_EXISTE") is None)
    msr = _constante_do_modulo("app/radai_watcher.py",
                               "FRASE_DO_MARCADOR_SEM_RTSTRUCT")
    checar(u"[cartão] a linha do marcador sem RTSTRUCT existe no vigia",
           isinstance(msr, str) and len(msr) > 10, str(msr)[:60])
    checar(u"[cartão] e tem os doze idiomas",
           isinstance(msr, str) and not _sem_os_doze([msr], tab))
    rec = _constante_do_modulo("app/radai_watcher.py",
                               "FRASE_DO_RECURSO_ESGOTADO")
    checar(u"[cartão] a linha do teto do recurso existe no vigia",
           isinstance(rec, str) and len(rec) > 20, str(rec)[:60])
    checar(u"[cartão] e tem os doze idiomas",
           isinstance(rec, str) and not _sem_os_doze([rec], tab))
    checar(u"  (isca) a mesma linha com uma palavra a mais é acusada",
           isinstance(rec, str) and bool(_sem_os_doze([rec + u" já"], tab)))

    sits = _frases_da_situacao(ler("app/radai_batch.py"))
    checar(u"[situação] achei as situações da série no «Rodar agora» (%d)"
           % len(sits), u"a refazer: marcador sem RTSTRUCT" in sits
           and u"parou no meio" in sits, str(sits)[:160])
    sem = _sem_os_doze(sits, tab)
    checar(u"[situação] cada uma tem os doze idiomas", not sem, str(sem))
    isca = _frases_da_situacao(u"x = sit('&#1;','zzqx situacao sem chave','')")
    checar(u"  (isca) a situação sem chave é acusada",
           _sem_os_doze(isca, tab) == [u"zzqx situacao sem chave"], str(isca))


def _frases_da_situacao(fonte):
    return re.findall(r"\bsit\('[^']*',\s*'([^']+)'", fonte or u"")


def main():
    print(u"=" * 68)
    print(u"test_languages | o dicionario, a maquina e a fronteira")
    print(u"=" * 68)
    teste_a_ajuda_do_ts_cru_diz_o_indice_26()
    teste_tabela()
    teste_construir()
    teste_chave_viva()
    teste_neuro_opcional()
    teste_rotas_medidas()
    teste_toda_frase_tem_chave()
    teste_frase_que_chega_por_json()
    teste_nao_traduzir()
    teste_js()
    teste_aplicar()
    teste_bandeiras()
    teste_seletor_js()
    teste_idioma_da_estacao()
    teste_aviso_documento()
    teste_documento_nao_passa_pelo_dicionario()
    teste_o_botao_sobrevive_a_traducao()
    teste_peso()
    teste_frase_traduzida_e_alcancavel()
    teste_o_titulo_da_aba_e_traduzido()
    teste_texto_repintado_por_js_perde_a_marca()
    teste_os_selos_sao_traduzidos()
    teste_o_tradutor_por_molde()
    teste_os_moldes_da_l3()
    teste_os_atributos_e_as_frases_montadas()
    teste_as_frases_fora_do_html()
    print(u"\n" + u"=" * 68)
    if _falhou:
        print(u"FALHOU: %d de %d checagens" % (_falhou, _ok + _falhou))
        for f in _falhas:
            print(u"  - %s" % f)
    else:
        print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 68)
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
