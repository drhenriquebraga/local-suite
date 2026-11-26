"""Observa a trava do dono. Quando liberada após queda, restaura só a rodada correspondente."""
import os
import sys
import time

sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))

import radai_dedicado as modo
import radai_dedicado_windows as windows


RECUOS_RESTAURO_S = (3, 10)


def vigiar(sessao, pasta, plataforma, intervalo=3, leitor_pai=None, *,
           esperar=time.sleep):
    caminho = pasta / "dedicado.json"
    pronto = pasta / ("dedicado-vigia-" + sessao + ".ok")
    confirmou = False
    sem_dono = False
    tentativas = 0
    try:
        while True:
            try:
                reg = modo.ler_registro(caminho)
                if reg["sessao"] != sessao:
                    return
                falta = any(modo._automatico(a["item"]) for a in modo.pendentes(reg))
                if reg.get("terminou") and not falta:
                    return
                if not confirmou:
                    modo.gravar(pronto, {"sessao": sessao, "pid": os.getpid()})
                    confirmou = True
                resultado = modo.recuperar(pasta, plataforma, sessao, None, True)
                if resultado is True or resultado == "nova_abertura":
                    return
            except FileNotFoundError:
                return
            except (ValueError, KeyError, OSError, TypeError):
                # Sem diário verificável não há autorização para reexecutar nada.
                return
            if leitor_pai is not None and not sem_dono:
                leitor_pai.read(1)
                sem_dono = True
                continue
            if resultado is None and not sem_dono:
                # Compatibilidade com lançadores anteriores que não enviam pipe.
                esperar(intervalo)
                continue
            if tentativas >= len(RECUOS_RESTAURO_S):
                return
            esperar(RECUOS_RESTAURO_S[tentativas])
            tentativas += 1
    finally:
        pronto.unlink(missing_ok=True)


if __name__=="__main__":
    if (len(sys.argv) not in (2, 3) or len(sys.argv[1]) != 32
            or (len(sys.argv) == 3 and sys.argv[2] != "--aguardar-pai")):
        raise SystemExit(2)
    vigiar(sys.argv[1], modo.pasta_local(), windows,
           leitor_pai=sys.stdin.buffer if len(sys.argv) == 3 else None)
