"""Rodada dedicada iniciada pelo operador local, com devolução independente da UI."""
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath



def pasta_local():
    return Path(os.environ["LOCALAPPDATA"]) / "RADIOTERAPIA_AI"


def gravar(caminho, registro):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=caminho.parent, prefix="dedicado-", suffix=".tmp",
                                     encoding="utf-8", delete=False) as fp:
        nome = fp.name
        try:
            json.dump(registro, fp, ensure_ascii=True, allow_nan=False)
            fp.flush()
            os.fsync(fp.fileno())
        except BaseException:
            fp.close()
            Path(nome).unlink(missing_ok=True)
            raise
    try:
        os.replace(nome, caminho)
    finally:
        Path(nome).unlink(missing_ok=True)


class Reserva:
    """Um dono da rodada por estação e usuário; o SO libera a trava na queda."""
    def __init__(self, pasta):
        self.arquivo = None
        self.pasta = pasta

    def adquirir(self):
        if self.arquivo is not None:
            return True
        self.pasta.mkdir(parents=True, exist_ok=True)
        fp = (self.pasta / "dedicado.lock").open("a+b")
        try:
            if not fp.seek(0, 2):
                fp.write(b"0")
                fp.flush()
            fp.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fp.close()
            return False
        self.arquivo = fp
        return True

    def soltar(self):
        if self.arquivo:
            self.arquivo.close()
            self.arquivo = None


@contextmanager
def reservar_para_encerrar(pasta=None):
    """O lançador só derruba sua árvore enquanto nenhuma rodada pode usar a estação."""
    reserva = None
    try:
        reserva = Reserva(pasta if pasta is not None else pasta_local())
        permitido = reserva.adquirir()
    except (OSError, KeyError):
        permitido = False
    try:
        yield permitido
    finally:
        if reserva is not None:
            reserva.soltar()


def abrir_vigia(sessao):
    """A primeira ação só é permitida quando o vigia leu o journal desta rodada."""
    import radai_job
    import radai_pulso
    pasta = pasta_local()
    pronto = pasta / ("dedicado-vigia-" + sessao + ".ok")
    proc = subprocess.Popen(
        [sys.executable, "-B", str(Path(__file__).with_name("radai_dedicado_vigia.py")), sessao, "--aguardar-pai"],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | radai_job.flags_de_saida(), close_fds=True)
    radai_pulso.poupar_enquanto_vivo(proc)
    limite = time.monotonic() + 3
    confirmou = False
    try:
        while proc.poll() is None and time.monotonic() < limite:
            try:
                if json.loads(pronto.read_bytes()) == {"pid": proc.pid, "sessao": sessao}:
                    confirmou = True
                    return proc
            except (OSError, ValueError):
                pass
            time.sleep(.05)
        return None
    finally:
        if not confirmou and proc.stdin:
            proc.stdin.close()
        pronto.unlink(missing_ok=True)


def _automatico(item):
    return item.get("automatico", item.get("tipo") == "servico")


def devolver_registro(reg, caminho, plataforma, manuais=(), automaticos=True, apenas_retentaveis=False):
    """Retoma intenções comprováveis, inclusive após interrupção entre ação e confirmação."""
    permitidos = set(manuais)
    for acao in reversed(reg["acoes"]):
        if acao["estado"] not in ("intencao", "aplicada", "pendente"):
            continue
        item = acao["item"]
        antes = (acao["estado"], acao.get("motivo_restauro"))
        if apenas_retentaveis and antes == ("pendente", "nova_abertura"):
            continue
        motivo = None
        if item.get("reversao") is False:
            acao["estado"] = "devolvida"
        elif (_automatico(item) and automaticos) or acao["id"] in permitidos:
            try:
                devolveu = plataforma.restaurar(item)
            except (TimeoutError, BlockingIOError):
                devolveu, motivo = False, "transitoria"
            except Exception:
                devolveu = False
            acao["estado"] = "devolvida" if devolveu else "pendente"
            if not devolveu:
                acao["motivo_restauro"] = motivo or "nova_abertura"
        if acao["estado"] == "devolvida":
            acao.pop("motivo_restauro", None)
        if (acao["estado"], acao.get("motivo_restauro")) != antes:
            gravar(caminho, reg)


def pendentes(reg):
    return [a for a in reg["acoes"] if a["estado"] in ("intencao", "aplicada", "pendente")]


def ler_registro(caminho):
    reg = json.loads(caminho.read_text(encoding="utf-8"))
    if (not isinstance(reg, dict) or not isinstance(reg.get("sessao"), str)
            or not isinstance(reg.get("acoes"), list)):
        raise ValueError("registro de devolução incompleto")
    for acao in reg["acoes"]:
        if (not isinstance(acao, dict) or not isinstance(acao.get("id"), str)
                or not isinstance(acao.get("estado"), str) or not isinstance(acao.get("item"), dict)
                or not all(isinstance(acao["item"].get(k), str) for k in ("tipo", "nome"))):
            raise ValueError("ação de devolução incompleta")
    return reg


def diagnostico_do_restauro(pasta=None):
    """Consultado no diagnóstico solicitado. Somente nomes técnicos, sem caminhos."""
    try:
        reg = ler_registro((pasta or pasta_local()) / "dedicado.json")
    except FileNotFoundError:
        return []
    except (OSError, ValueError, KeyError, TypeError):
        return ["diário de restauração indisponível"]
    itens = []
    for acao in pendentes(reg):
        item = acao["item"]
        if _automatico(item) and item.get("reversao") is not False:
            nome = item["nome"] if re.fullmatch(r"[\w.-]{1,80}", item["nome"], flags=re.ASCII) else item["tipo"]
            itens.append(nome)
    return itens


def recuperar(pasta, plataforma, sessao=None, resposta_ocupada=False, apos_fechamento=False):
    reserva = Reserva(pasta)
    if not reserva.adquirir():
        return resposta_ocupada
    try:
        caminho = pasta / "dedicado.json"
        if not caminho.is_file():
            return True
        reg = ler_registro(caminho)
        if sessao and reg["sessao"] != sessao:
            return True
        if reg.get("terminou") and not any(_automatico(a["item"]) for a in pendentes(reg)):
            return True
        devolver_registro(reg, caminho, plataforma, apenas_retentaveis=apos_fechamento)
        if not reg.get("terminou"):
            reg["terminou"] = True
            gravar(caminho, reg)
        faltam = [a for a in pendentes(reg) if _automatico(a["item"])]
        if apos_fechamento and faltam and not any(a.get("motivo_restauro") == "transitoria" for a in faltam):
            return "nova_abertura"
        return not faltam
    finally:
        reserva.soltar()


class Coordenador:
    def __init__(self, pasta, plataforma, fila, iniciar, pausar, habilitado, porta,
                 vigia=abrir_vigia, intervalo=2, teto_preparo=45, medir=None):
        self.pasta, self.plataforma = pasta, plataforma
        self.fila, self.iniciar, self.pausar = fila, iniciar, pausar
        self.habilitado, self.porta = habilitado, porta
        self.vigia, self.intervalo = vigia, intervalo
        self.teto_preparo, self.medir = teto_preparo, medir
        self.medicao_sessao = None
        self.proxima_medicao = 0
        self.ram_inicial = None
        self.desligando = False
        self.estacionado = False
        self.registro = pasta / "dedicado.json"
        self.trava = threading.RLock()
        self.reserva = Reserva(pasta)
        self.planos = {}
        self.dono = ""
        self.sair_pedido = threading.Event()
        self.mudou = threading.Event()
        self.fim = threading.Event()
        self.fim.set()
        self.proc = None
        self.reg = None
        self.journal_ativo = False
        self._historico_lido = False
        self._historico = None
        self.publico = dict(ativo=False, fase="completed", seq=0, sessao="", total=0, feitas=0)
        self.ultimo = None

    def _status(self, **dados):
        with self.trava:
            if all(self.publico.get(k) == v for k, v in dados.items()):
                return
            mudou_estado = any(k in dados and dados[k] != self.publico.get(k) for k in ("ativo", "fase", "em_espera"))
            self.publico.update(dados)
            if mudou_estado:
                from radai_pulso import notificar_mudanca
                notificar_mudanca("config")
            self.publico["seq"] += 1
            if "ativo" in dados:
                self._historico_lido = False
                import radai_queue_state
                radai_queue_state.avisar_ocupacao()

    def atualizar_medicao(self, dono):
        # Só o monitor visível do operador pede métricas. Soltar a trava durante
        # a consulta mantém as ações de fila e restauração independentes da GPU.
        with self.trava:
            if not self.publico["ativo"] or self.estacionado or not self.medir or self.dono != dono:
                return
            sessao = self.publico["sessao"]
            agora = time.monotonic()
            if self.medicao_sessao != sessao:
                self.medicao_sessao, self.proxima_medicao, self.ram_inicial = sessao, 0, None
            if agora < self.proxima_medicao:
                return
            self.proxima_medicao = agora + 60
        try:
            ram, vram = self.medir()
        except Exception:
            return
        with self.trava:
            if not self.publico["ativo"] or self.publico["sessao"] != sessao:
                return
            if self.ram_inicial is None:
                self.ram_inicial = ram
            ganho = round(ram - self.ram_inicial, 2) if ram is not None and self.ram_inicial is not None else None
            self._status(memoria_livre_gb=ram, vram_livre_gb=vram, ganho_memoria_gb=ganho)

    def estado(self):
        with self.trava:
            reg = self.reg
            if not self.publico["ativo"]:
                if not self._historico_lido:
                    self._historico = None
                    try:
                        rec = ler_registro(self.registro)
                        if rec.get("terminou"):
                            self._historico = rec
                    except (OSError, ValueError, AttributeError):
                        pass
                    self._historico_lido = True
                reg = self._historico or reg
            acoes = pendentes(reg) if reg and not self.publico["ativo"] else []
            return dict(self.publico, sessao=(reg or {}).get("sessao", self.publico["sessao"]),
                        disponivel=bool(self.habilitado()), restauracao_pendente=any(_automatico(a["item"]) for a in acoes),
                        reabrir=[{"id": a["id"], "nome": a["item"]["nome"]} for a in acoes if not _automatico(a["item"])])

    def antes_da_previa(self):
        if not self.habilitado():
            return None, dict(ok=False, disponivel=False, motivo="desligado")
        f = self.fila()
        if not f["total"]:
            return None, dict(ok=False, disponivel=True, motivo="vazia", itens=[], total=0)
        return f, None

    def prever(self, dono):
        f, erro = self.antes_da_previa()
        if erro:
            return erro
        resumo = {}
        try:
            if hasattr(self.plataforma, "prever_com_resumo"):
                candidatos, resumo = self.plataforma.prever_com_resumo(porta=self.porta)
            else:
                candidatos = self.plataforma.prever(porta=self.porta)
        except Exception:
            candidatos = []
        return self.registrar_previa(dono, f, candidatos, resumo)

    def registrar_previa(self, dono, f, candidatos, resumo):
        certificados = resumo.get("_certificados", ())
        if certificados and hasattr(self.plataforma, "guardar_certificados_da_previa"):
            self.plataforma.guardar_certificados_da_previa(certificados, candidatos, resumo.get("_certificados_servicos", ()))
        itens = {secrets.token_hex(10): i for i in candidatos}
        token = secrets.token_urlsafe(32)
        now = time.monotonic()
        with self.trava:
            self.planos = {k: x for k, x in self.planos.items() if x[0] > now}
            if len(self.planos) >= 16:
                self.planos.pop(next(iter(self.planos)))
            self.planos[token] = (now+180, dono, f["revisao"], itens)
        return dict(ok=True, disponivel=True, token=token, total=f["total"],
                    administrador=resumo.get("administrador"), sem_shell=bool(resumo.get("sem_shell")),
                    preservados=resumo.get("preservados", []), hospeda_servicos=bool(resumo.get("hospeda_servicos")),
                    itens=[dict(id=k, nome=i["nome"], tipo=i["tipo"], navegador=bool(i.get("navegador")),
                                janelas=int(i.get("janelas") or 0), conhecido=bool(i.get("conhecido", True)),
                                memoria_mb=int(i.get("memoria_mb") or 0), selecionado=bool(i.get("selecionado")))
                           for k, i in itens.items()])

    def entrar(self, dono, dados):
        ids = dados.get("itens")
        if (dados.get("consentido") is not True or not isinstance(ids, list) or len(ids)>512
                or not all(isinstance(x,str) for x in ids) or len(ids)!=len(set(ids))):
            return {"ok":False, "motivo":"consentimento"}
        token = dados.get("token")
        with self.trava:
            if not isinstance(token, str) or not self.habilitado():
                return {"ok":False, "motivo":"desligado"}
            pedido = (dono, token, frozenset(ids))
            if self.ultimo == pedido:
                return dict(ok=True, **self.estado())
            plano = self.planos.get(token)
            if not plano or time.monotonic()>plano[0] or plano[1]!=dono or not set(ids)<=plano[3].keys():
                return {"ok":False, "motivo":"plano_vencido"}
            if self.publico["ativo"]:
                return {"ok":False, "motivo":"ocupada"}
            pode_gravar = True
            try:
                if not self.reserva.adquirir():
                    return {"ok":False, "motivo":"ocupada"}
            except OSError:
                pode_gravar = False
            sucesso = False
            try:
                fila = self.fila()
                if not fila["total"] or fila["revisao"]!=plano[2]:
                    return {"ok":False, "motivo":"fila_alterada"}
                anterior = None
                if pode_gravar and self.registro.exists():
                    try:
                        anterior = ler_registro(self.registro)
                        if any(_automatico(a["item"]) for a in pendentes(anterior)):
                            # O vigia conserva a posse da devolução anterior. A nova fila
                            # pode iniciar com os recursos atuais, sem intervir na estação.
                            anterior = None
                            pode_gravar = False
                    except (OSError, ValueError, TypeError, KeyError):
                        # Guarda íntegro o journal que a estação ainda precisa recuperar.
                        anterior = None
                        pode_gravar = False
                sessao = secrets.token_hex(16)
                selecionadas = [(k, plano[3][k]) for k in ids]
                fechar = {item["id"] for _,item in selecionadas if item["tipo"]=="app"}
                self.reg = dict(sessao=sessao, terminou=False, acoes=[
                    {"id":k, "item":item, "estado":"prevista"} for k,item in selecionadas
                    if item["tipo"] not in ("memoria","prioridade") or item["id"] not in fechar])
                # Outras janelas fechadas por escolhas anteriores continuam disponíveis para reabrir.
                if anterior:
                    self.reg["acoes"].extend(a for a in pendentes(anterior) if not _automatico(a["item"]))
                pulos_iniciais = 0
                self.journal_ativo = False
                self.proc = None
                if pode_gravar:
                    try:
                        gravar(self.registro,self.reg)
                        self.journal_ativo = True
                    except OSError:
                        pass
                if not self.journal_ativo:
                    self.reserva.soltar()
                    # Sem intenção durável o lote só usa recursos da própria Suite.
                    for acao in self.reg["acoes"]:
                        if acao["estado"] == "prevista":
                            acao["estado"] = "pulada"
                            pulos_iniciais += 1
                self.dono=dono
                self.estacionado=False
                self.sair_pedido.clear()
                self.desligando=False
                self.fim.clear()
                self._status(sessao=sessao,ativo=True,fase="preparing",aplicados=0,pulados=pulos_iniciais,
                             feitas=0,total=fila["total"], prints_seguros=[], log_seq=fila.get("log_seq",0), memoria_livre_gb=None,
                             ganho_memoria_gb=None, vram_livre_gb=None, ficaram_abertos=[], servicos_restaurados=0)
                self.ultimo=pedido
                self.planos.pop(token)
                threading.Thread(target=self._rodar,args=(fila,),daemon=True,name="suite-dedicado").start()
                sucesso=True
                return dict(ok=True, **self.estado())
            finally:
                if not sucesso:
                    self.reserva.soltar()

    def _rodar(self, inicio):
        resultado = "completed"
        iniciado = threading.Event()
        falhou = threading.Event()
        def comecar():
            with self.trava:
                if iniciado.is_set() or self.desligando:
                    return
                iniciado.set()
                try:
                    if self.fila()["revisao"] != inicio["revisao"] or not self.iniciar(inicio):
                        falhou.set()
                    else:
                        self._status(fase="ready_wait")
                except Exception:
                    falhou.set()
        teto = threading.Timer(self.teto_preparo, comecar)
        teto.daemon = True
        teto.start()
        try:
            novas = [a for a in self.reg["acoes"] if a["estado"]=="prevista"]
            if novas:
                try:
                    self.proc=self.vigia(self.reg["sessao"])
                except OSError:
                    self.proc=None
            for a in novas:
                if self.sair_pedido.is_set() or iniciado.is_set():
                    a["estado"]="pulada"
                    self._status(pulados=self.publico["pulados"]+1)
                    continue
                # Sem supervisor disponível a fila prossegue com as aplicações abertas.
                if self.proc is None or self.proc.poll() is not None:
                    a["estado"]="pulada"
                else:
                    a["estado"]="intencao"
                    try:
                        gravar(self.registro,self.reg)
                    except OSError:
                        a["estado"]="pulada"
                        self._status(pulados=self.publico["pulados"]+1)
                        continue
                    try:
                        if hasattr(self.plataforma, "aplicar_com_detalhe"):
                            aplicada, aberta = self.plataforma.aplicar_com_detalhe(a["item"])
                            if aberta:
                                self._status(ficaram_abertos=[*self.publico["ficaram_abertos"],a["item"]["nome"]])
                        else:
                            aplicada = self.plataforma.aplicar(a["item"])
                        a["estado"] = "aplicada" if aplicada else "pulada"
                    except Exception:
                        a["estado"]="pendente"
                try:
                    gravar(self.registro,self.reg)
                except OSError:
                    # A intenção já estava gravada; a devolução tenta de novo.
                    pass
                campo="aplicados" if a["estado"]=="aplicada" else "pulados"
                self._status(**{campo:self.publico[campo]+1})
            comecar()
            if falhou.is_set():
                resultado = "failed"
                return
            from radai_pulso import observar_fila
            devolvidas_na_pausa = []
            pausa_anterior = False
            with observar_fila(self.mudou):
                while True:
                    self.mudou.clear()
                    if self.sair_pedido.is_set():
                        resultado = "returned"
                        break
                    atual=self.fila()
                    estacionado = (not atual.get("rodando") and (atual.get("pausado")
                                   or (atual.get("continuo", atual.get("overnight")) and not atual.get("na_fila"))))
                    with self.trava:
                        mudou_pausa = self.estacionado != bool(estacionado)
                        self.estacionado = bool(estacionado)
                    if mudou_pausa:
                        import radai_queue_state
                        radai_queue_state.avisar_ocupacao()
                    pausa = bool(atual.get("pausado") and not atual.get("rodando"))
                    if self.journal_ativo and pausa and not pausa_anterior:
                        aplicadas = [a for a in pendentes(self.reg) if _automatico(a["item"])]
                        devolver_registro(self.reg, self.registro, self.plataforma)
                        devolvidas_na_pausa = [a for a in aplicadas if a["estado"] == "devolvida"]
                    if (self.journal_ativo and devolvidas_na_pausa and not pausa
                            and atual.get("rodando") and self.proc and self.proc.poll() is None):
                        for acao in devolvidas_na_pausa:
                            if self.sair_pedido.is_set():
                                break
                            acao["estado"] = "intencao"
                            gravar(self.registro, self.reg)
                            try:
                                aplicada = self.plataforma.aplicar(acao["item"])
                                acao["estado"] = "aplicada" if aplicada else "pulada"
                            except Exception:
                                acao["estado"] = "pendente"
                            gravar(self.registro, self.reg)
                        devolvidas_na_pausa = []
                    pausa_anterior = pausa
                    novos = [(seq,linha) for seq,linha in atual.get("eventos_log",[]) if seq > self.publico["log_seq"]]
                    dados = {}
                    if novos:
                        dados["log_seq"] = novos[-1][0]
                        dados["prints_seguros"] = (self.publico["prints_seguros"] + [linha for _,linha in novos])[-3:]
                    feitos = (len(set(inicio["ids"]) - set(atual["ids"]))
                              if "ids" in inicio and "ids" in atual else max(0, inicio["total"]-atual["total"]))
                    self._status(fase=atual["fase"], feitas=feitos, em_espera=bool(estacionado), **dados)
                    if atual.get("pausado") and not atual.get("rodando") and not atual.get("continuo", atual.get("overnight")):
                        resultado = "returned"
                        break
                    if not atual.get("continuo", atual.get("overnight")) and atual["encerrada"](inicio):
                        resultado="partial" if atual["com_falha"](inicio) else "completed"
                        break
                    if estacionado:
                        self.mudou.wait()
                    else:
                        self.sair_pedido.wait(self.intervalo)
        except Exception:
            resultado="failed"
        finally:
            teto.cancel()
            with self.trava:
                self._status(fase="restoring")
                try:
                    if self.journal_ativo:
                        devolver_registro(self.reg,self.registro,self.plataforma)
                        self.reg["terminou"]=True
                        gravar(self.registro,self.reg)
                except OSError:
                    resultado = "partial"
                finally:
                    acoes = self.reg["acoes"]
                    self._status(ativo=False, fase=resultado,
                        servicos_restaurados=sum(a["estado"]=="devolvida" and a["item"]["tipo"]=="servico" for a in acoes))
                    if getattr(self, "liberar_fila", None):
                        self.liberar_fila()
                    self.reserva.soltar()
                    # A EOF também é entregue pelo SO se a estação perder este processo.
                    canal = getattr(self.proc, "stdin", None)
                    if canal:
                        canal.close()
                    self.fim.set()

    def sair(self,sessao,itens=None,dono=None):
        with self.trava:
            if dono is not None and self.publico["ativo"] and dono != self.dono:
                return {"ok":False,"motivo":"sessao"}
            if not self.publico["ativo"]:
                try:
                    if not self.reserva.adquirir():
                        return {"ok":False,"motivo":"sessao"}
                except OSError:
                    return {"ok":False,"motivo":"sessao"}
                try:
                    # Relê depois da trava: o vigia pode ter concluído ações entre cliques.
                    try:
                        reg = ler_registro(self.registro)
                    except (OSError, ValueError):
                        return {"ok":False,"motivo":"sessao"}
                    if reg["sessao"] != sessao:
                        return {"ok":False,"motivo":"sessao"}
                    ids=[a["id"] for a in pendentes(reg) if not _automatico(a["item"])]
                    manuais=[i for i in itens if i in ids] if itens is not None else ()
                    devolver_registro(reg,self.registro,self.plataforma,manuais=manuais)
                    self.reg=reg
                    self._historico_lido = False
                finally:
                    self.reserva.soltar()
            elif self.publico["sessao"]!=sessao or itens is not None:
                return {"ok":False,"motivo":"sessao"}
            else:
                self.sair_pedido.set()
                self.mudou.set()
            return dict(ok=True,**self.estado())


_CONTROLADOR = None


def sinalizacao():
    c = _CONTROLADOR
    if c and c.publico["ativo"]:
        supervisor = c.proc.pid if c.proc and c.proc.poll() is None else None
        # O Kit protege qualquer executável em um componente RADIOTERAPIA_AI.
        # O supervisor usa o próprio sys.executable e o pipe acorda na queda do dono.
        caminho_protegido = "radioterapia_ai" in (p.casefold() for p in PureWindowsPath(sys.executable).parts[:-1])
        if c.estacionado and (caminho_protegido or supervisor is None or not any(
                _automatico(a["item"]) and a["item"].get("reversao") is not False
                for a in pendentes(c.reg or {}))):
            return False, None
        return True, supervisor
    return False, None


def supervisor_em_pausa():
    c = _CONTROLADOR
    return bool(c and c.publico["ativo"] and c.estacionado and c.proc)


def fechar():
    c = _CONTROLADOR
    if c and c.publico["ativo"]:
        with c.trava:
            c.desligando = True
            c.sair(c.publico["sessao"])
        c.fim.wait(8)


# O monitor público só recebe fragmentos técnicos extraídos do log local.
_TRECHO_DO_LOG = re.compile(
    r"\b(?:predicting part [1-9]\d? of [1-9]\d?|parte? [1-9]\d?\s*/\s*[1-9]\d?|"
    r"device\s*[:=]\s*(?:cpu|cuda(?::[0-9])?|gpu)|dispositivo\s*[:=]\s*(?:cpu|cuda|gpu)|"
    r"(?:carregando modelo|loading model|resampling|predicting|exporting|"
    r"gravando (?:o )?rtstruct|montando (?:o )?rtstruct|postprocessing|pós-processamento))\b", re.I)


def limpar_print(linha):
    achado = _TRECHO_DO_LOG.search(str(linha)[:2048])
    return achado.group(0) if achado else ""


def medir_recursos():
    import radai_cleaner
    dados = radai_cleaner.memoria_da_estacao()
    ram = round(dados["livre_mb"] / 1024, 2) if dados.get("total_mb") else None
    try:
        import radai_devices
        placas = radai_devices.placas_nvidia(timeout=1).get("placas", [])
        livre = placas[0].get("livre_mb") if placas else None
        vram = round(livre / 1024, 2) if livre is not None else None
    except Exception:
        vram = None
    return ram, vram


def _snapshot(f, estado_vigia):
    from radai_queue_state import assinatura_do_pedido
    cards = f.cards()
    v = estado_vigia()
    ativos = [c for c in cards if c.get("estado") in ("esperando","rodando")]
    turno = any(f.Q.e_turno(c) for c in ativos)
    permitidos = {c["id"]: assinatura_do_pedido(c) for c in ativos}
    rastreio = any(c.get("tipo") == "lung_screening" for c in ativos)
    continuo = bool(turno or rastreio or v.get("overnight"))
    executores = {"lung-screening" if c.get("tipo") == "lung_screening" else f.Q.executor(c)
                  for c in ativos}
    revisao = [(c["id"], c.get("estado"),f.Q.executor(c), c.get("carga"),c.get("iniciar_pedido")) for c in ativos]
    # O conteúdo da fila fica só na RAM. A revisão é opaca e não integra o journal.
    assinatura = hashlib.sha256(json.dumps(revisao,sort_keys=True,default=str).encode()).hexdigest()
    rodando = bool(any(c.get("estado")=="rodando" and not f.Q.e_turno(c) for c in cards) or v.get("em_execucao"))
    fase = v.get("fase", "ready_wait")
    linhas = [limpar_print(linha) for linha in v.get("log_recente", [])]
    log_seq = int(v.get("log_seq",0))
    eventos = [(pos,linha) for pos,linha in enumerate(linhas,log_seq-len(linhas)+1) if linha][-3:]
    finais = {c["id"]:c.get("estado") for c in cards if c.get("estado") in f.Q.TERMINAIS}
    def encerrada(inicio):
        if rodando or continuo:
            return False
        autorizados = set(inicio["ids"])
        escolhas = inicio.get("permitidos")
        sem_pendentes = not any(c["id"] in autorizados and not f.Q.e_turno(c)
                                and (escolhas is None or escolhas.get(c["id"]) == assinatura_do_pedido(c))
                                for c in ativos)
        return sem_pendentes
    return {"total":len(ativos) or int(bool(v.get("overnight"))), "overnight":bool(v.get("overnight")), "ids":[c["id"] for c in ativos], "revisao":assinatura,
            "permitidos":permitidos, "executores":executores, "turno":turno, "continuo":continuo, "rodando":rodando, "na_fila":v.get("na_fila"), "scan":v.get("varredura_vazia",0),
            "fase":fase, "eventos_log":eventos, "log_seq":log_seq, "encerrada":encerrada,
            "com_falha":lambda i:any(finais.get(k) in ("falhou","parcial","cancelado")
                or (k in permitidos and k in i.get("permitidos", {}) and permitidos[k] != i["permitidos"][k])
                for k in i["ids"])}


def montar(app, cfg, iniciar_fila, pausar_fila):
    global _CONTROLADOR
    import ipaddress
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from urllib.parse import urlsplit
    import radai_queue_state as fila
    import radai_dedicado_windows as windows

    def snapshot():
        def atividade():
            from radai_batch import andamento
            v = dict(cfg.get("estado_dedicado",dict)())
            lote = andamento()
            etapa = (lote.get("etapa") if lote.get("rodando") else v.get("etapa")) or ""
            nomes = (("copi", "input"), ("lendo", "input"), ("carregando modelo", "loading_model"),
                     ("segment", "inference"), ("task", "inference"), ("infer", "inference"),
                     ("pós", "postprocessing"), ("pos-process", "postprocessing"),
                     ("montando", "postprocessing"), ("grav", "writing_output"))
            v["fase"]=next((fase for prefixo,fase in nomes if str(etapa).lower().startswith(prefixo)), "ready_wait")
            v["em_execucao"] = v.get("em_execucao") or bool(lote.get("rodando"))
            return v
        dados = _snapshot(fila,atividade)
        dados["pausado"] = fila.rastreio_pausado()
        return dados
    def iniciar(s):
        if not s["total"]:
            return False
        fila.limitar_sessao_dedicada(s["permitidos"])
        if not s["executores"] and s.get("overnight"):
            return True
        ct = s["turno"] or bool(s["executores"] & {"lote","vigia"})
        if ct and not iniciar_fila(permitidos=s["permitidos"]).get("ok"):
            return False
        if "neuro" in s["executores"]:
            fila.pausar_neuro(False)
        return True
    def pausar():
        fila.pausar_neuro(True)
        pausar_fila()
    def habilitado():
        if "dedicado_habilitado" in cfg:
            valor = cfg["dedicado_habilitado"]()
        else:
            import radai_config
            valor = radai_config.chave_configurada("MODO_DEDICADO")
        return (valor or "1").lower() not in ("0","false","off")
    c = Coordenador(pasta_local(),windows,snapshot,iniciar,pausar,habilitado,cfg.get("porta_dedicado", 0), medir=medir_recursos)
    c.liberar_fila = lambda: fila.limitar_sessao_dedicada(None)
    _CONTROLADOR = c
    cookie = "suite_estacao_dedicada"
    segredo = secrets.token_bytes(32)
    import hmac
    def resposta(d,status=200):
        return JSONResponse(d,status_code=status,headers={"Cache-Control":"no-store"})
    def auth(req, emitir=False):
        if not req.client:
            return None
        try:
            if not ipaddress.ip_address(req.client.host).is_loopback:
                return None
        except ValueError:
            return None
        host = req.headers.get("host","")
        try:
            url=urlsplit(req.url.scheme+"://"+host)
            if url.hostname not in ("localhost","127.0.0.1","::1") or (c.porta and url.port!=int(c.porta)):
                return None
        except ValueError:
            return None
        origin=req.headers.get("origin")
        if origin!=req.url.scheme+"://"+host:
            if req.method!="GET" or origin or req.headers.get("sec-fetch-site")!="same-origin":
                return None
        token=req.cookies.get(cookie,"")
        def assinar(val):
            return hmac.new(segredo,val.encode("ascii"),"sha256").hexdigest()
        partes=token.split(".")
        if (len(partes)==2 and len(partes[0])==48 and partes[0].isascii()
                and partes[1].isascii() and hmac.compare_digest(assinar(partes[0]),partes[1])):
            return token
        if emitir:
            novo=secrets.token_hex(24)
            return novo+"."+assinar(novo)
        return None

    async def corpo(req):
        if req.headers.get("content-type","").split(";",1)[0].strip()!="application/json":
            return None
        buf=bytearray()
        async for bloco in req.stream():
            if len(buf)+len(bloco)>32768:
                return None
            buf.extend(bloco)
        try:
            dados=json.loads(buf)
            return dados if isinstance(dados,dict) else None
        except (ValueError,UnicodeError):
            return None

    def negada():
        return resposta({"ok":False,"motivo":"sessao"},403)

    @app.post("/api/estacao/dedicado/prever")
    async def prever(req:Request):
        dono=auth(req,True)
        if not dono or await corpo(req) is None:
            return negada()
        from starlette.concurrency import run_in_threadpool
        from radai_consulta_isolada import ler, erro_da_consulta
        fila_anterior, erro = await run_in_threadpool(c.antes_da_previa)
        if erro:
            return resposta(erro)
        try:
            candidatos, resumo = await ler(req, "dedicado_prever", {"porta": c.porta, "pid_motor": os.getpid()}, prazo=20)
        except ConnectionAbortedError as exc:
            return resposta({"ok": False, **erro_da_consulta(exc)}, 503)
        except (OSError, ValueError):
            # O inventário serve para oferecer ações opcionais no Windows.
            # Um plano vazio mantém o navegador, os aplicativos e os serviços em uso.
            candidatos, resumo = [], {"inventario_indisponivel": True}
        plano = c.registrar_previa(dono, fila_anterior, candidatos, resumo)
        plano["inventario_indisponivel"] = bool(resumo.get("inventario_indisponivel"))
        r=resposta(plano)
        r.set_cookie(cookie,dono,httponly=True,samesite="strict",path="/api/estacao/dedicado")
        return r

    @app.post("/api/estacao/dedicado/entrar")
    async def entrar(req:Request):
        dono=auth(req)
        dados=await corpo(req) if dono else None
        if dados is None:
            return negada()
        from starlette.concurrency import run_in_threadpool
        d=await run_in_threadpool(c.entrar,dono,dados)
        return resposta(d,202 if d["ok"] else 409)

    @app.get("/api/estacao/dedicado/estado")
    def estado(req:Request, telemetria:bool=False):
        dono=auth(req,True)
        if not dono:
            return negada()
        if telemetria:
            c.atualizar_medicao(dono)
        with c.trava:
            if c.publico["ativo"] and c.dono != dono:
                return negada()
            # Somente a prévia estabelece o dono. Um GET tardio da tela não
            # pode substituir o cookie que acabou de autorizar o início.
            return resposta(c.estado())

    async def devolver(req,reabrir):
        dono=auth(req)
        dados=await corpo(req) if dono else None
        if dados is None:
            return negada()
        ids=dados.get("itens",[]) if reabrir else None
        if reabrir and (not isinstance(ids,list) or not all(isinstance(v,str) for v in ids)):
            return negada()
        from starlette.concurrency import run_in_threadpool
        d=await run_in_threadpool(c.sair,dados.get("sessao"),ids,dono)
        return resposta(d,200 if d.get("ok") else 409)

    @app.post("/api/estacao/dedicado/sair")
    async def sair(req:Request):
        return await devolver(req,False)

    @app.post("/api/estacao/dedicado/reabrir")
    async def reabrir(req:Request):
        return await devolver(req,True)

    def no_arranque():
        if c.registro.exists():
            try:
                recuperar(c.pasta,windows)
            except (OSError, ValueError, TypeError, KeyError):
                # Um registro incompleto fica disponível para diagnóstico local.
                pass
            finally:
                with c.trava:
                    c._historico_lido = False
    threading.Thread(target=no_arranque,daemon=True,name="suite-restauro-local").start()
