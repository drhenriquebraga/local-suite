# -*- coding: utf-8 -*-
import os
import platform
import shutil
import sys

import radai_version

ESPACO_MINIMO_GB = 14.0

BUILD_MINIMO = 14393


def _gb(n):
    return round(float(n) / (1024.0 ** 3), 1)


def raiz_da_instalacao():
    return os.path.dirname(radai_version.registro_da_instalacao())


def conferir():
    itens = []
    raiz = raiz_da_instalacao()
    nome_do_registro = radai_version.NOME_DO_REGISTRO

    def _item(ok, titulo, valor, o_que_fazer=u"", critico=True):
        itens.append({"ok": bool(ok), "titulo": titulo, "valor": valor,
                      "o_que_fazer": o_que_fazer, "critico": bool(critico)})

    try:
        sistema = platform.system()
        versao = platform.version()
        build = 0
        for parte in str(versao).split("."):
            if parte.isdigit():
                build = int(parte)
        _item(sistema == "Windows" and build >= BUILD_MINIMO,
              u"Sistema", u"%s %s (build %s)" % (sistema, platform.release(),
                                                 build or u"?"),
              u"A suíte é para Windows 10 build %d ou mais novo. A estação de "
              u"campo é um LTSB 2016, e é ele que define o piso — abaixo dele "
              u"o runtime embarcado não é garantido." % BUILD_MINIMO)
    except Exception as e:
        _item(False, u"Sistema", u"não consegui ler (%s)" % type(e).__name__)

    try:
        bits = platform.machine()
        _item(bits.lower() in ("amd64", "x86_64"),
              u"Arquitetura", bits,
              u"O runtime embarcado e o torch são 64 bits. Numa máquina 32 "
              u"bits nada disto instala.")
    except Exception:
        pass

    try:
        unidade = os.path.splitdrive(raiz)[0] or "C:"
        alvo = unidade + os.sep
        livre = shutil.disk_usage(alvo).free
        _item(_gb(livre) >= ESPACO_MINIMO_GB,
              u"Espaço em %s" % unidade, u"%.1f GB livres" % _gb(livre),
              u"O pacote é montado na máquina e pesa cerca de 8,4 GB; com a "
              u"montagem intermediária são ~%.0f GB. Libere espaço antes."
              % ESPACO_MINIMO_GB)
    except Exception as e:
        _item(False, u"Espaço em disco",
              u"não consegui medir (%s)" % type(e).__name__)

    try:
        pai = os.path.dirname(raiz.rstrip("\\/")) or raiz
        base = raiz if os.path.isdir(raiz) else pai
        if not os.path.isdir(base):
            raise OSError("nem a raiz nem a pasta pai dela existem")
        marca = os.path.join(base, "_radai_teste_escrita.tmp")
        with open(marca, "w") as f:
            f.write("x")
        os.remove(marca)
        _item(True, u"Escrita em %s" % base, u"pode escrever, sem administrador")
    except Exception as e:
        _item(False, u"Escrita em %s" % raiz,
              u"NÃO consegui escrever (%s)" % type(e).__name__,
              u"A suíte instala sem administrador, mas precisa poder escrever "
              u"na pasta. Peça à TI permissão de escrita nesta pasta — não "
              u"peça administrador.")

    reg = os.path.join(raiz, nome_do_registro)
    if os.path.isfile(reg):
        try:
            import json
            with open(reg, encoding="utf-8-sig") as f:
                d = json.load(f)
            _item(isinstance(d, dict), u"Registro de instalados",
                  u"%d projeto(s) registrado(s)" % len(d or {}),
                  u"", critico=False)
        except Exception as e:
            _item(False, u"Registro de instalados",
                  u"existe e NÃO abre (%s)" % type(e).__name__,
                  u"O `%s` é compartilhado entre os projetos e responde qual "
                  u"versão está nesta sala. Corrompido, a próxima instalação "
                  u"apaga a entrada dos vizinhos. Renomeie-o antes de "
                  u"instalar." % nome_do_registro)
    else:
        _item(True, u"Registro de instalados", u"ainda não existe (normal)",
              u"", critico=False)

    if os.path.isdir(raiz):
        try:
            projetos = sorted(d for d in os.listdir(raiz)
                              if os.path.isdir(os.path.join(raiz, d))
                              and not d.startswith("_"))
            _item(True, u"Já instalado aqui",
                  u", ".join(projetos) if projetos else u"nenhum projeto ainda",
                  u"", critico=False)
        except Exception:
            pass

    _item(True, u"Python desta sessão",
          u"%s (%s)" % (platform.python_version(), sys.executable),
          u"", critico=False)

    criticos = [i for i in itens if i["critico"] and not i["ok"]]
    return {"itens": itens, "pronto": not criticos,
            "faltando": len(criticos),
            "raiz": raiz}
