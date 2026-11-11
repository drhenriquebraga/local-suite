# Local Suite 8.21 — NEURO RT 1.3.5 — LUNG RT 1.1.5

## Correções

- O limite global de 16 MiB no PortaoDoHost era aplicado antes das rotas de upload dos bundles. A exceção de 16 GiB agora vale somente para upload ZIP de pesos, autenticado, local e da mesma origem; os demais pedidos preservam o limite pequeno. O tamanho real também é conferido durante streaming e uploads interrompidos não deixam o arquivo parcial.
- A entrada do NEURO monta as ferramentas básicas após verificar o código, mesmo quando há um erro anterior de preparo de recursos. NIDUS não requer pesos. Ferramentas que precisam de modelos mostram a orientação no próprio card.
- Configurações NEURO/LUNG têm somente preparo automático de pesos e importação do bundle offline. O instalador principal é responsável por todo o código. Uma tentativa antiga não se sobrepõe ao erro atual; o diagnóstico fica em um só local. Ícones seguem a mesma ordem dos demais cards e a explicação do fechamento/reabertura fica na ajuda.
- O instalador LUNG, com uma Suite existente, solicita apenas recursos. Uma instalação compacta inicia o código base a partir da própria Suite. O pacote para levar contém todos os recursos CT/RX, independentemente da seleção opcional de pré-laudos na instalação local.

## NIDUS

Estação equilibrada escolhida pelo usuário: projeção principal e grade de sala/axial/coronal/sagital, barra de ações com temperatura. A angiografia pode ser maximizada; duplo clique no MPR troca-o com a projeção. A roda percorre os cortes MPR. A centralização usa o centro geométrico da máscara de consenso atual, incluindo a edição quando ativa, sem modificar a máscara ou a exportação.

A sugestão de série prioriza TOF 3D original e preserva a seleção explícita. MIP/MPR já derivadas não são priorizadas. Na RM, Anatomia e Tecidos ajustam o sinal da série carregada: não geram uma nova sequência T1, fusão ou unidades Hounsfield. Consenso vermelho espesso, projeções mais finas e rodapé padrão de material de estudo local.

O seletor de resolução foi retirado. O motor atual finaliza em 1024 × 1024; durante o arraste angular usa a prévia já existente e retorna à qualidade final ao soltar. Isso não acrescenta informação anatômica ao exame original. O lápis usa a transformação SVG inversa para manter as coordenadas ao alterar a proporção ou maximizar o visor.

## Compatibilidade e evidências

- Preservados os pesos existentes, o Python da Suite e os termos individuais aplicáveis aos recursos.
- Bundle LUNG real 1.1.2, 6.376.849.386 bytes: upload pelo servidor completo e instalação dos 14 recursos CT/RX com rede externa bloqueada; código ativo preservado. SHA do bundle: f862fa75f3cb05034dc3d4b7d72e4a4c23f9865d8cab178d69b7981dee0f58ce.
- O bundle NEURO 1.3.0 original não foi fornecido nesta rodada. Compatibilidade de importação de pesos antigos é exercitada por fixtures autenticadas e pelos contratos do SDK; os anexos fornecidos eram logs de falhas.
- Não houve execução de inferência clínica nem alteração do motor clínico de contornos nesta entrega. O núcleo compartilhado de reconstrução vascular continua preservado.
- BUNDLE_MINIMO permanece 8.4; esta correção não exige recriar os pacotes pesados.

As verificações finais dos ZIPs e downloads públicos ficam em C:/AI_DEPLOY/VERIFICACOES_v8.21. A publicação contém dois instaladores leves por produto (versionado e LATEST); nenhum peso, Python ou imagem de paciente é publicado.

Bibliografia e inferências técnicas: [TOF e reconstrução no NIDUS](TOF-RECONSTRUCAO-NIDUS-11NOV2026.md).
