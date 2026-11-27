"""Testes comportamentais do dedicado com processos, serviços e fila simulados."""
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase, main
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_config as config
import radai_dedicado as dedicado
import radai_dedicado_windows as windows
import radai_lancador as lancador


def processo(nome="spotify", **mudancas):
    dados = dict(nome=nome, pid=91, identidade={"sha256": "abc"}, mesmo_usuario=True,
                 protegido=False, conhecido=True, desktop_verificado=False, janelas=[20],
                 memoria_mb=300, prioridade=32, perfil_independente=True)
    return dict(dados, **mudancas)


def inventario(*processos, shell=True, admin=False, servicos=None):
    return dict(pronto=True, elevado=admin, explorer_interativo=shell, processos=processos,
                servicos=servicos or {})


class Selecao(TestCase):
    def test_preservados_e_sem_identidade(self):
        nomes = ["epic", "eclipse", "aria", "soarian", "monaco", "mosaiq", "raystation",
                 "vitrea", "wfica32", "tasy", "sqlservr", "teamviewer", "msmpeng", "csfalcon",
                 "svchost", "googleupdate", "msedgewebview2", "setup"]
        for nome in nomes:
            with self.subTest(nome=nome):
                self.assertEqual(windows.selecionar(inventario(processo(nome)), 8030), [])
        for atributos in [dict(protegido=True), dict(mesmo_usuario=False),
                          dict(conhecido=False), dict(identidade=None)]:
            self.assertEqual(windows.selecionar(inventario(processo(**atributos)), 8030), [])
        self.assertTrue(windows.selecionar(inventario(processo("epicgameslauncher")), 8030))

    def test_apps_registrados_e_servicos(self):
        for janelas, memoria, marcado in [([], 300, True), ([], 301, False), ([20], 19, False)]:
            with self.subTest(janelas=janelas, memoria=memoria):
                p = processo("editor", conhecido=False, desktop_verificado=True,
                             janelas=janelas, memoria_mb=memoria)
                app, = [i for i in windows.selecionar(inventario(p), 8030) if i["tipo"] == "app"]
                self.assertEqual(app["selecionado"], marcado)
        validos = {"estado": 4, "identidade": {"imagem": "assinada"}}
        servicos = {"BITS": validos, "LanmanWorkstation": validos, "DoSvc": dict(validos, bloqueado=True)}
        self.assertEqual(windows.selecionar(inventario(servicos=servicos), 8030), [])
        with patch.object(windows, "SERVICOS_PAUSAVEIS", set(servicos)):
            itens = windows.selecionar(inventario(admin=True, servicos=servicos), 8030)
        self.assertEqual([i["nome"] for i in itens], ["BITS"])

    def test_navegador_conectado_e_identidades_ambiguas(self):
        exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        perfil = r"C:\Users\operador\perfil"
        self.assertEqual(windows._perfil_do_navegador("chrome", [exe]), "")
        self.assertEqual(windows._perfil_do_navegador("chrome", [exe, "--user-data-dir", perfil]), perfil)
        for args in [[], [exe, "--user-data-dir"], [exe, "--user-data-dir=relativo"],
                     [exe, "--type=renderer"], [exe, "--kiosk"], [exe, "--app=https://local"],
                     [exe, "--user-data-dir="+perfil, "--user-data-dir="+perfil]]:
            with self.subTest(args=args):
                self.assertIsNone(windows._perfil_do_navegador("chrome", args))
        arvore = [dict(pid=10, ppid=4), dict(pid=40, ppid=10), dict(pid=42, ppid=40)]
        self.assertEqual(windows._descendentes(arvore, {40}) | windows._ancestrais(arvore, {40}), {10,40,42})
        for p in [processo("chrome", perfil_independente=False), processo("chrome", janelas=[]),
                  processo("chrome", protegido=True)]:
            self.assertFalse(windows.selecionar(inventario(p), 8030))
        self.assertEqual([i["tipo"] for i in windows.selecionar(inventario(processo("chrome")), 8030)], ["app"])

    def test_sem_shell_ou_sem_host(self):
        pf = Mock()
        pf.inventario.return_value = inventario(processo(), shell=False)
        itens, resumo = windows.prever_com_resumo(8030, pf)
        self.assertNotIn("app", [i["tipo"] for i in itens])
        self.assertTrue(resumo["sem_shell"])
        pf.inventario.return_value = {}
        itens, resumo = windows.prever_com_resumo(8030, pf)
        self.assertEqual(itens, [])
        self.assertIsNone(resumo["administrador"])

    def test_inventario_preserva_arvore_conectada_perfil_da_suite_e_janela_clinica(self):
        processos = [dict(pid=pid, ppid=pai, nome="chrome")
                     for pid, pai in [(10,4), (11,10), (12,10), (20,4), (21,4), (22,4), (23,4)]]
        pf = Mock()
        pf.compartilhada = pf.admin = False
        pf.servicos_ativos.return_value = []
        pf.processo.side_effect = lambda *args: nullcontext(1)
        pf.identidade.side_effect = lambda h,pid: dict(caminho="chrome.exe", usuario="me", sessao=2)
        pf.elevado.return_value = False
        pf.memoria.return_value = False
        pf.prio.return_value = 32
        pf.j.janelas.return_value = [p["pid"] for p in processos]
        pf.j.visivel.return_value = True
        pf.j.pid.side_effect = lambda h: h
        pf.j.linha_de_comando.side_effect = lambda pid: ("chrome.exe --user-data-dir=C:\\suite"
                                                          if pid==22 else "chrome.exe")
        pf.j.titulo.side_effect = lambda hw: {21:"PACS - leitura", 23:None}.get(hw, "Página pessoal")
        with (patch.object(windows.limpeza, "processos", return_value=processos),
              patch.object(windows.limpeza, "arvore_do_app", return_value=[]) as arvore,
              patch.object(windows.limpeza, "navegadores_conectados", return_value=[10,11]),
              patch.object(windows.limpeza, "ler_em_uso", return_value={}),
              patch.object(windows.janela, "perfil_esperado_do_app", return_value=r"C:\suite"),
              patch.object(windows, "_caminho_conhecido", return_value=True),
              patch.object(windows, "_hash", return_value="h"),
              patch.object(windows, "_consultar_assinaturas", return_value={"chrome.exe":"Google LLC"}),
              patch.object(windows, "_aprovado", return_value=True) as assinatura):
            inv = windows.Plataforma.inventario(pf, 8030)
        arvore.assert_called_once_with(processos, windows.os.getpid())
        assinatura.assert_called_once()
        self.assertEqual([i["id"] for i in windows.selecionar(inv, 8030)], [20])

    def test_vinte_processos_revalidados_sem_netstat_e_com_uma_consulta_de_assinaturas(self):
        processos = [dict(nome="spotify", pid=8100+i, ppid=4) for i in range(20)]
        pf = Mock()
        pf.compartilhada = False
        pf.admin = True
        pf.servicos_ativos.return_value = []
        pf.processo.side_effect = lambda *args: nullcontext(1)
        pf.identidade.side_effect = lambda h,pid: dict(caminho=str(pid)+".exe", usuario="me", sessao=2, criado=pid)
        pf.elevado.return_value = False
        pf.memoria.return_value = False
        pf.prio.return_value = 32
        pf.j.janelas.return_value = [p["pid"] for p in processos]
        pf.j.visivel.return_value = True
        pf.j.pid.side_effect = lambda h: h
        def servicos(alvos, lista, pendencias=None):
            self.assertIsNotNone(pendencias)
            pendencias["gupdate"] = ("GoogleUpdate.exe", "hash:GoogleUpdate.exe", "Google LLC")
            pendencias["AdobeARMservice"] = ("armsvc.exe", "hash:armsvc.exe", "Adobe Inc.")
            return {nome:{"estado":4, "identidade":nome+"-scm", "bloqueado":False} for nome in pendencias}
        pf._servicos_disponiveis.side_effect = servicos
        pf.inventario.side_effect = lambda porta, **kw: windows.Plataforma.inventario(pf, porta, **kw)
        with (patch.dict(windows._ASSINATURAS, clear=True),
              patch.object(windows.limpeza, "processos", return_value=processos),
              patch.object(windows.limpeza, "arvore_do_app", return_value=[]),
              patch.object(windows.limpeza, "_clientes_tcp_painel", return_value={8000}) as tcp,
              patch.object(windows.limpeza, "_rodar", side_effect=AssertionError("netstat")),
              patch.object(windows.limpeza, "ler_em_uso", return_value={}),
              patch.object(windows, "_caminho_conhecido", return_value=True),
              patch.object(windows, "_hash", side_effect=lambda path: "hash:"+path) as hash_atual,
              patch.object(windows, "_consultar_assinaturas",
                           side_effect=lambda caminhos:{p:"Google LLC" if p == "GoogleUpdate.exe" else "Spotify AB"
                                                        for p in caminhos}) as cert):
            itens, resumo = windows.prever_com_resumo(8030, pf)
            alvos = [i for i in itens if i["tipo"] == "prioridade"]
            self.assertEqual(len(alvos), 20)
            self.assertEqual(len(cert.call_args.args[0]), 22)
            self.assertEqual([i["nome"] for i in itens if i["tipo"] == "servico"], ["gupdate"])
            windows._ASSINATURAS.clear()  # o processo de prévia saiu
            windows.guardar_certificados_da_previa(resumo["_certificados"], itens, resumo["_certificados_servicos"])
            self.assertEqual(windows._assinante("GoogleUpdate.exe","hash:GoogleUpdate.exe"), "Google LLC")
            self.assertNotIn(("armsvc.exe", "hash:armsvc.exe"), windows._ASSINATURAS)
            for item in alvos:
                self.assertIn(item, windows.Plataforma.verificar_item(pf, item))
            cert.assert_called_once()
            self.assertEqual(tcp.call_count, 21)
            hash_atual.side_effect = lambda path: "atualizado"
            self.assertFalse(windows.Plataforma.verificar_item(pf, alvos[0]))
            cert.assert_called_once()
            tcp.return_value = {alvos[0]["id"]}
            self.assertFalse(windows.Plataforma.verificar_item(pf, alvos[0]))
            tcp.return_value = set()
            self.assertFalse(windows.Plataforma.verificar_item(pf, alvos[0]))

    def test_servico_revalida_so_alvo_e_exige_painel_conectado(self):
        pf = Mock()
        pf.compartilhada = False
        pf.admin = True
        pf.processo.side_effect = lambda *args: nullcontext(1)
        pf.identidade.return_value = {"sessao": 3}
        e = {"estado":4, "identidade":{"imagem":"gupdate"}, "bloqueado":False}
        pf._servicos_disponiveis.return_value = {"gupdate":e}
        lista = [dict(nome="teste", pid=18101, ppid=4)]
        with (patch.object(windows.limpeza, "processos", return_value=lista),
              patch.object(windows.limpeza, "navegadores_conectados", return_value=[29]) as conectado):
            item, = windows.selecionar(inventario(admin=True,servicos={"gupdate":e}), 8030)
            inv = windows.Plataforma.inventario(pf,8030,alvo=item)
            self.assertEqual(windows.selecionar(inv,8030), [item])
            pf._servicos_disponiveis.assert_called_once_with({"gupdate"}, lista)
            pf.servicos_ativos.assert_not_called()
            pf.j.janelas.assert_not_called()
            pf.explorer_interativo.assert_not_called()
            conectado.return_value = []
            self.assertFalse(windows.selecionar(windows.Plataforma.inventario(pf,8030,alvo=item),8030))

    def test_fechamento_sem_janela_aguarda_e_confirma(self):
        pf = Mock()
        pf.processo.return_value = nullcontext(1)
        pf._mesma_instancia.return_value = True
        pf.j.janelas.return_value = []
        pf.espera.side_effect = [258, 0]
        pf.terminar.return_value = True
        self.assertTrue(windows.Plataforma.fechar_app(pf, {"id": 91, "janelas": 0}))
        pf.terminar.assert_called_once_with(1,0)
        self.assertEqual([c.args[1] for c in pf.espera.call_args_list], [0,1200])

    def test_reabre_apenas_pelo_shell_verificado_com_confirmacao(self):
        pf = Mock()
        salvo = dict(caminho=r"C:\Programs\spotify.exe", sessao=1, usuario="me", sha256="h")
        item = dict(identidade=salvo, nome="spotify")
        pf.processo.return_value = nullcontext(1)
        pf.identidade.return_value = salvo
        pf.explorer_interativo.return_value = [71]
        def diretorio(buffer, tamanho):
            buffer.value = r"C:\Windows\System32"
            return len(buffer.value)
        pf.k.GetSystemDirectoryW.side_effect = diretorio
        with (patch.object(windows, "_caminho_conhecido", return_value=True),
              patch.object(windows, "_aprovado", return_value=True),
              patch.object(windows, "_hash", return_value="h"),
              patch.object(windows, "_presenca_app", side_effect=[False, True]),
              patch.object(windows.subprocess, "run") as enviar):
            enviar.return_value = Mock(returncode=0)
            self.assertTrue(windows.Plataforma.reabrir(pf,item))
        comando, = enviar.call_args.args
        env = enviar.call_args.kwargs["env"]
        self.assertEqual(Path(comando[0]).name, "powershell.exe")
        self.assertEqual(env["RADAI_REABRIR"], salvo["caminho"])
        self.assertEqual(env["RADAI_JANELAS"], "71")
        self.assertIn("Document.Application.ShellExecute", comando[-1])
        self.assertNotIn(salvo["caminho"], comando[-1])

    def test_shell_do_desktop_sem_pasta_e_com_usuario_correto(self):
        pf = Mock()
        def diretorio(buffer, tamanho):
            buffer.value = r"C:\Windows"
            return len(buffer.value)
        pf.k.GetWindowsDirectoryW.side_effect = diretorio
        pf.j.janelas.return_value = []
        pf.processo.return_value = nullcontext(1)
        proprio = {"usuario": "local", "sessao": 1, "caminho": windows._normal(r"C:\Windows\explorer.exe")}
        pf.identidade.return_value = proprio.copy()
        pf.elevado.return_value = False
        with patch.object(windows.ctypes, "WinDLL") as dll:
            dll.return_value.GetShellWindow.return_value = 80
            self.assertEqual(windows.Plataforma.explorer_interativo(pf, proprio), [80])
            pf.elevado.return_value = True
            self.assertEqual(windows.Plataforma.explorer_interativo(pf, proprio), [])
            pf.elevado.return_value = False
            pf.identidade.return_value["usuario"] = "outro"
            self.assertEqual(windows.Plataforma.explorer_interativo(pf, proprio), [])

    def test_salvar_documento_e_janela_nova_impedem_termino(self):
        pf = Mock()
        pf.processo.return_value = nullcontext(1)
        pf._mesma_instancia.return_value = True
        pf.j.janelas.return_value = [20]
        pf.j.pid.return_value = 91
        pf.j.visivel.return_value = pf.j.existe.return_value = True
        pf.espera.return_value = 258
        self.assertFalse(windows.Plataforma.fechar_app(pf, {"id": 91, "janelas": 1}))
        self.assertIs(pf.janela_ainda_aberta, True)
        pf.j.fechar.assert_called_once_with(20)
        self.assertFalse(windows.Plataforma.fechar_app(pf, {"id": 91, "janelas": 0}))
        pf.terminar.assert_not_called()

    def test_revalidar_pid_antes_da_acao(self):
        pf = Mock()
        item = windows.selecionar(inventario(processo()), 8030)[0]
        pf.verificar_item.return_value = [dict(item, identidade={"sha256":"novo"})]
        self.assertFalse(windows.aplicar(item, pf))
        pf.fechar_app.assert_not_called()

    def test_assinaturas_em_lote_e_hash(self):
        hashes = {"a.exe":"1", "b.exe":"2"}
        with (patch.dict(windows._ASSINATURAS, clear=True),
              patch.object(windows, "_hash", side_effect=hashes.get),
              patch.object(windows, "_consultar_assinaturas") as conferir):
            conferir.side_effect = lambda nomes: {p:"Fornecedor" for p in nomes}
            self.assertEqual(windows._assinantes_dos([("a.exe","1"),("a.exe","1"),("b.exe","2")]),
                             {("a.exe","1"):"Fornecedor",("b.exe","2"):"Fornecedor"})
            conferir.assert_called_once_with(["a.exe","b.exe"])
            self.assertEqual(windows._assinante("a.exe","1"),"Fornecedor")
            hashes["a.exe"] = "3"
            self.assertEqual(windows._assinante("a.exe","3"),"Fornecedor")
            self.assertEqual(conferir.call_count, 2)
            conferir.assert_called_with(["a.exe"])
            self.assertEqual(windows._assinante("a.exe","antigo"),"")
            self.assertNotIn(("a.exe","antigo"), windows._ASSINATURAS)

    def test_transferencia_e_atualizacao_ativas_sao_preservadas(self):
        pf = Mock()
        pf.admin = True
        pf.atualizando.return_value = False
        pf.transferencias_em_curso.return_value = {"BITS","DoSvc"}
        pf.servico.side_effect = lambda nome, *args: nullcontext(nome)
        pf.estado_servico.side_effect = lambda h, nome, *args: {"estado":4, "identidade":"original"}
        alvos = {"WSearch", "SysMain", "wuauserv", "UsoSvc", "BITS", "DoSvc"}
        consultar = windows.Plataforma._servicos_disponiveis
        self.assertEqual(set(consultar(pf, alvos, [{}])), alvos - {"BITS","DoSvc"})
        pf.atualizando.return_value = True
        self.assertEqual(set(consultar(pf, alvos, [{}])), {"WSearch","SysMain"})
        self.assertFalse({"LanmanServer","LanmanWorkstation","Dhcp","Dnscache"} & windows.SERVICOS_PAUSAVEIS)

    def test_sem_compactacao_ou_pausa_do_shell_e_restauro_de_versoes_anteriores(self):
        serv = {k:{"estado":4,"identidade":"origem","bloqueado":False} for k in ("WSearch","SysMain","wuauserv","UsoSvc","DoSvc","BITS")}
        itens = windows.selecionar(inventario(processo(),admin=True,servicos=serv),8030)
        self.assertFalse(any(i["tipo"] == "memoria" for i in itens))
        self.assertEqual({i["id"] for i in itens if i["tipo"] == "servico"}, set(serv))
        for nome in serv:
            pf = Mock()
            pf.admin=True
            pf.servico.return_value = nullcontext(1)
            pf.estado_servico.side_effect=[dict(estado=1,identidade="origem"),dict(estado=4,identidade="origem")]
            item = {"id":nome,"nome":nome,"tipo":"servico","identidade":"origem","original":4}
            self.assertTrue(windows.Plataforma.alterar_servico(pf,item,restaurando=True))
            pf.start.assert_called_once()
            pf.control.assert_not_called()


class Rodada(TestCase):
    def setUp(self):
        diretorio = TemporaryDirectory()
        self.addCleanup(diretorio.cleanup)
        self.pasta = Path(diretorio.name)
        self.arquivo = self.pasta / "dedicado.json"
        self.servico = {"id": "servico-a", "tipo": "servico", "nome": "servico-a", "selecionado": True}
        self.pf = Mock(spec=["prever", "aplicar", "restaurar"])
        self.pf.prever.return_value = [self.servico]
        self.pf.aplicar.return_value = self.pf.restaurar.return_value = True
        self.iniciou = Event()
        self.snapshot = {"total": 1, "revisao": "r1", "ids": [1], "fase": "running",
                         "encerrada": lambda inicio: self.iniciou.is_set(), "com_falha": lambda inicio: False}
        self.iniciar = Mock(side_effect=lambda inicio: self.iniciou.set() or True)
        self.ctrl = dedicado.Coordenador(self.pasta, self.pf, lambda: self.snapshot, self.iniciar,
                                         Mock(), lambda: True, 8030, vigia=lambda _: Mock(poll=lambda: None),
                                         intervalo=.005, teto_preparo=2)

    def pedido(self):
        plano = self.ctrl.prever("operador")
        return dict(token=plano["token"], consentido=True, itens=[i["id"] for i in plano["itens"]])

    def entrar(self, pedido=None):
        self.assertTrue(self.ctrl.entrar("operador", pedido or self.pedido())["ok"])

    def terminou(self):
        self.assertTrue(self.ctrl.fim.wait(3))
        self.assertEqual(self.ctrl.estado()["fase"], "completed")
        self.iniciar.assert_called_once()

    def test_pausa_com_monitor_devolve_servico_e_observa_a_fila(self):
        restaurou, reaplicou = Event(), Event()
        self.snapshot.update(continuo=True, pausado=True, rodando=False)
        self.pf.restaurar.side_effect = lambda item: restaurou.set() or True
        self.entrar()
        try:
            self.assertTrue(restaurou.wait(2))
            self.assertTrue(self.ctrl.estado()["ativo"])
            self.pf.aplicar.side_effect = lambda item: reaplicou.set() or True
            self.snapshot.update(pausado=False, rodando=True)
            self.ctrl.mudou.set()
            self.assertTrue(reaplicou.wait(2))
        finally:
            self.snapshot.update(continuo=False, rodando=False, pausado=False)
            self.ctrl.mudou.set()
        self.terminou()
        self.assertEqual(self.pf.restaurar.call_count, 2)

    def test_consentimento_e_revisao(self):
        pedido = self.pedido()
        self.assertFalse(self.ctrl.entrar("outro", pedido)["ok"])
        self.assertFalse(self.ctrl.entrar("operador", dict(pedido, consentido=False))["ok"])
        self.snapshot["revisao"] = "r2"
        self.assertEqual(self.ctrl.entrar("operador", pedido)["motivo"], "fila_alterada")
        self.iniciar.assert_not_called()

    def test_intencao_duravel_antes_da_acao_e_devolucao_sem_ui(self):
        estados = []
        self.pf.aplicar.side_effect = lambda item: estados.append(dedicado.ler_registro(self.arquivo)["acoes"][0]["estado"]) or True
        pedido = self.pedido()
        self.entrar(pedido)
        self.terminou()
        self.assertEqual(estados, ["intencao"])
        self.pf.restaurar.assert_called_once_with(self.servico)
        self.assertEqual(dedicado.ler_registro(self.arquivo)["acoes"][0]["estado"], "devolvida")
        self.entrar(pedido)
        self.iniciar.assert_called_once()

    def test_falha_do_journal(self):
        with patch.object(dedicado, "gravar", side_effect=OSError("disco")):
            self.entrar()
            self.terminou()
        self.assertEqual(self.ctrl.estado()["pulados"], 1)
        self.pf.aplicar.assert_not_called()

    def test_sem_supervisor(self):
        self.ctrl.vigia = lambda _: None
        self.entrar()
        self.terminou()
        self.assertEqual(self.ctrl.estado()["pulados"], 1)
        self.pf.aplicar.assert_not_called()

    def test_excecao_depois_de_intencao(self):
        self.pf.aplicar.side_effect = OSError("resposta perdida")
        self.entrar()
        self.terminou()
        self.pf.restaurar.assert_called_once_with(self.servico)

    def test_teto_de_preparo(self):
        entrou, liberar = Event(), Event()
        def aplicar(item):
            entrou.set()
            return liberar.wait(3)
        self.pf.aplicar.side_effect = aplicar
        self.ctrl.teto_preparo = .1
        self.entrar()
        try:
            self.assertTrue(entrou.wait(1))
            self.assertTrue(self.iniciou.wait(1))
        finally:
            liberar.set()
        self.terminou()

    def test_recuperacao_exclusiva_e_idempotente_depois_da_queda(self):
        app = {"nome": "editor", "tipo": "app"}
        journal = dict(sessao="original", terminou=False, acoes=[
            {"id":"s", "estado":"intencao", "item":self.servico},
            {"id":"a", "estado":"aplicada", "item":app}])
        dedicado.gravar(self.arquivo, journal)
        reserva = dedicado.Reserva(self.pasta)
        self.assertTrue(reserva.adquirir())
        try:
            self.assertFalse(dedicado.recuperar(self.pasta, self.pf))
            self.pf.restaurar.assert_not_called()
        finally:
            reserva.soltar()
        for _ in range(2):
            self.assertTrue(dedicado.recuperar(self.pasta, self.pf))
        self.pf.restaurar.assert_called_once_with(self.servico)
        reg = dedicado.ler_registro(self.arquivo)
        self.assertTrue(reg["terminou"])
        self.assertEqual([a["id"] for a in dedicado.pendentes(reg)], ["a"])
        dedicado.devolver_registro(reg, self.arquivo, self.pf, manuais=["a"])
        self.pf.restaurar.assert_called_with(app)

    def test_lancador_espera_o_dono_e_mantem_a_reserva_ate_encerrar(self):
        mensagens, tentativas = [], []
        def derrubar(reg):
            with dedicado.reservar_para_encerrar(self.pasta) as outra:
                self.assertFalse(outra)
            tentativas.append(reg["pid"])
            return [reg["pid"]]
        def encerrar():
            return lancador.encerrar_instancia(8030, "sem painel", {"pid": 99}, mensagens.append,
                derrubar_=derrubar, livre=lambda *_: True, sair=lambda *_: True,
                reservar=lambda: dedicado.reservar_para_encerrar(self.pasta))
        with dedicado.reservar_para_encerrar(self.pasta) as ativo:
            self.assertTrue(ativo)
            self.assertFalse(encerrar())
            self.assertFalse(tentativas)
        self.assertTrue(encerrar())
        self.assertEqual(tentativas, [99])

    def test_telemetria_somente_por_pedido_do_monitor_com_intervalo(self):
        medir=Mock(return_value=(3.0,1.0))
        self.ctrl.medir=medir
        self.ctrl.dono="operador"
        self.ctrl._status(ativo=True,sessao="s")
        self.ctrl.estado()
        self.ctrl.atualizar_medicao("outro")
        medir.assert_not_called()
        with patch.object(dedicado.time,"monotonic",side_effect=[10,11,71]):
            for _ in range(3):
                self.ctrl.atualizar_medicao("operador")
        self.assertEqual(medir.call_count,2)
        self.assertEqual(self.ctrl.estado()["vram_livre_gb"],1.0)
        self.ctrl._status(ativo=False)
        self.ctrl.atualizar_medicao("operador")
        self.assertEqual(medir.call_count,2)

    def test_monitor_expoe_so_fragmento_tecnico(self):
        self.assertEqual(dedicado.limpar_print("paciente ficticio uid=123 predicting part 1 of 5 /dados"),
                         "predicting part 1 of 5")
        self.assertEqual(dedicado.limpar_print("paciente ficticio uid=123"), "")

    def test_consentimento_da_estacao_em_exportacao_e_arquivo_antigo(self):
        arquivo = self.pasta / "config.txt"
        arquivo.write_text("MODO_DEDICADO=0\nIDIOMA=pt-BR\n", encoding="utf-8")
        chaves = ["MODO_DEDICADO", "IDIOMA"]
        pacote = config.exportar(arquivo, chaves)
        self.assertEqual(pacote["secoes"]["configuracao"], {"IDIOMA":"pt-BR"})
        pacote["secoes"]["configuracao"].update(MODO_DEDICADO="1", IDIOMA="en")
        previa = config.previa_da_importacao(pacote, arquivo, chaves, {})
        self.assertEqual(previa["configuracao"]["ignoradas"], ["MODO_DEDICADO"])
        self.assertTrue(config.importar(pacote, ["configuracao"], arquivo, chaves, {})["ok"])
        self.assertEqual(config.ler_arquivo(arquivo)[1], {"MODO_DEDICADO":"0", "IDIOMA":"en"})


if __name__ == "__main__":
    main(verbosity=2)
