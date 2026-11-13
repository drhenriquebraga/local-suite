# Ferramentas DICOM e editor compartilhado

Pedido do autor de 13/11/2026. Implementação autorizada na continuidade da
Suite 8.22. Não alterar fontes, pesos, protocolos de segmentação ou animações
existentes. Fonte canônica: este checkout; NEURO: Temp/radai-neuro-131.

## Contrato de uso

- Barra compacta com ícones, tooltip, teclado e nomes acessíveis nos visores.
- Lápis, pincel, borracha, pan, medida física, janela/nível, zoom, desfazer,
  refazer e acesso ao editor. Ctrl+roda e vírgula/ponto ajustam o pincel quando
  uma ferramenta de pintura está ativa; campos de texto não capturam atalhos.
- Editor comum aberto como área de trabalho sobre o visor, mantendo sua série.
  Permite selecionar o RTSTRUCT, criar e nomear ROIs, editar e interpolar com
  prévia explícita. Salvar gera uma nova entrega UNAPPROVED; preserva o original
  e os contornos das ROIs não alteradas. Grava pelo motor do host.
- Geometria nativa e LPS; nenhuma transferência entre pacientes/séries/quadros
  de referência. Contornos incompatíveis são recusados com explicação.
- NIDUS usa pincel na máscara do consenso e mostra a mesma máscara no TOF 3D.
  Retirar expansão da grade; preservar troca de MPR e zoom independente.
- Entrada por pasta identifica TOF original e grupos temporais adquiridos.
  Escolha ambígua permanece explícita. Cache das incidências de 5° é limitado,
  serial e cancelável; TOF estático não se torna enchimento temporal.

## Trabalho e evidência

- Root: toolbar, editor UI, integração/adapters e distribuição.
- nidus_loading_motion: tela NIDUS, zoom, picker/cache e integração toolbar.
- nidus_cine_backend: pincel/borracha/mesh do consenso e descoberta temporal.
- tof_temporal_literature: core/API do editor e preservação RTSTRUCT.
- O caminho do exemplo real de angiografia ainda não foi informado nesta rodada.
  Os testes usam dados sintéticos; não constituem validação clínica.
- Interpolação implementada com prévia e aplicação explícita entre dois cortes,
  preservando os cortes desenhados manualmente.

## Entrega 8.23

- Editor compartilhado no host; NEURO 1.3.7 e LUNG 1.1.7 usam os mesmos controles.
- NIDUS: pincel físico no MPR, superfície do consenso na reconstrução 3D, zoom e
  pan por visor, sem expansão da estação; 72 incidências em passos de 5 graus
  preparadas com cache limitado e carregamento de pasta TOF/CINE.
- RTSTRUCT novo é publicado atomicamente. Cada máscara alterada é reimportada
  do arquivo pronto e comparada voxel a voxel antes de disponibilizar a cópia.
  O adaptador reutiliza o extrator terminal do motor; não altera o motor global.
- Campos sem edição mantêm seus contornos/referências. Geometrias Enhanced,
  irregulares ou contornos incompatíveis são recusados sem reamostragem implícita.
- A barra encaminha ferramentas ao editor comum quando o visor de origem não
  possui operação nativa; edição não é aplicada diretamente a uma malha 3D.
- Novos textos e tooltips estão nos 12 idiomas suportados. Sem troca de fontes,
  pesos, Python ou requisito mínimo de bundle.
- Cópias manuais aparecem nos visores 2D/3D, inclusive sem uma segmentação AUTO
  anterior. Não contam como conclusão de anatomia para o AUTO/Vigia. O retorno
  do editor seleciona a cópia gravada nos visores Ver segmentações e Recon3D.
- Gestos fixam série, ROI, corte, revisão e diâmetro no início; trocas de corte
  durante o desenho são bloqueadas. Requisições canceladas ou antigas não
  aplicam contornos a outra série.

## Verificação prevista

Round-trip físico em grade oblíqua/anisotrópica, ROIs não editadas preservadas,
undo/redo, pincel em mm, interpolação sem sobrescrever cortes âncora, referências
DICOM, troca de série durante requests, eventos de zoom e atalhos, doze idiomas,
cache cancelável, instaladores/código único e integridade dos dois espelhos.
