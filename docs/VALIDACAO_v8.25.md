# Validação da Local Suite 8.25

- Um cartão nativo de carregamento no Rodar agora, com seleção e arrastar integrados.
- Anatomia Geral recebe Segmentar novo caso. O endereço anterior de Anatomia Torácica redireciona para ela; o cartão e o item de navegação anteriores foram retirados.
- LUNG separa Detectar nódulo pulmonar (um caso) de Rastreio populacional de nódulos pulmonares (monitoramento).
- Conferir pesos mostra progresso e resultado, com versões independentes de código e bundle. A instalação principal continua incluindo os códigos NEURO/LUNG; recursos adicionais permanecem opcionais.
- Correção de consulta às máscaras lazy de RM, de caminhos Windows estendidos na exportação NEURO e da revalidação repetida das máscaras na recuperação de estudos.
- O visor NEURO carrega superfícies de forma incremental, sem bloquear os controles; o texto das séries do CINE permanece compacto.

## Evidências locais

- ContourLab: 915 verificações; menu: 336; bootstrap integrado: 8 testes; regressões NEURO e pesos: 66 testes, com dois testes opcionais ignorados; LUNG: 16 testes; Anatomia Geral: 14 verificações.
- Novos títulos verificados no navegador nos 12 idiomas.
- Caso de RM: execução real de total_mr, vertebrae_mr, SynthSeg e CerebrA/ANTs. A falha MasksCruas.get foi reproduzida, corrigida e seguida de nova execução pelo fluxo padrão.
- STUDY, FULL, VMR e RTSTRUCT NEURO conferidos: identidade, StudyInstanceUID, FrameOfReferenceUID e referências aos cortes originais preservados; ApprovalStatus UNAPPROVED. As entregas do caso contêm, respectivamente, 1, 4, 5 e 134 ROIs.
- TOF carregado automaticamente, alvos geométricos manuais de teste em três incidências, reconstruções MPR/3D e CINE adquirido com 48 fases. MP4 local com dois ciclos completos, decodificado e conferido.
- Imagens, vídeos, DICOM e registros do caso permanecem fora do repositório e dos pacotes públicos.

## Limites das verificações

Esses ensaios verificam execução, interação e integridade das entregas. Não constituem avaliação clínica das segmentações.

A bateria ampla tools/test_ui.py também foi executada. Registrou um limite de cores já excedido no editor inalterado e duas dependências ausentes no ambiente dessa bateria (importação do DicomBridge e Playwright Python). As verificações Chrome/Playwright Node das alterações foram executadas separadamente. Esses problemas não foram contados como testes aprovados.
