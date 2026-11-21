import json
import sys
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "setup/programa/app"))
import radai_batch as b
import radai_modes as md
import radai_output
import radai_bridge as bridge
import radai_acabamento_i18n as tx
import radai_snc_rm as snc
import radai_tasks as t
import radai_todo as todo
from radai_phrases import CODIGOS, construir
def conferir(titulo, cond):
 if not cond: raise AssertionError(titulo)
 print('OK', titulo)
s={"modalidade":"CT","modo":"perso","protocolos":["sbrt_figado"]}
def nomes(s):
 d=b.previa_da_entrega(s)['oar']
 return {i['chave'] for i in d['estruturas']},{i['chave'] for i in d['fora']}
for modo in ('auto','fast',''):
 e=b.escolha_da_serie(dict(s,modo=modo,acabamento='fast',anatomia_geral_full=True))
 conferir('AUTO/STUDY '+str(modo), e['modo']=='auto' and not e['anatomia_geral_full'] and e['acabamento']=='padrao')
conferir('somente modos de entrada vigentes no Bridge', [c for c,n in bridge.MODOS_DE_SEGMENTACAO]==['nenhuma','auto','personalizado'])
with patch.object(snc,'disponivel',return_value=False):
 mr=b.opcoes_da_tela('MR');ct=b.opcoes_da_tela('CT')
 conferir('SNC indisponível está visível e bloqueado só em RM',any(x['cod']=='snc_rm' and x['disponivel'] is False for x in mr['protocolos']) and not any(x['cod']=='snc_rm' for x in ct['protocolos']))
conferir('dois modos por série', [m['cod'] for m in mr['modos']]==['auto','perso'])
ct_auto=b.escolha_da_serie({"modo":"auto","modalidade":"CT"})
conferir('AUTO inclui união cervical sem níveis separados', not b.niveis_pedidos_no_study(ct_auto))
conferir('níveis separados avançados',b.niveis_pedidos_no_study(b.escolha_da_serie(dict(s,protocolos=['cabeca_pescoco']))))
conferir('simples sem níveis separados',not b.niveis_pedidos_no_study(b.escolha_da_serie(dict(s,protocolos=['cabeca_pescoco_simples']))))
simples,fora=nomes(dict(s,protocolos=['cabeca_pescoco_simples']))
conferir('LNL_UNION na prévia do simples',any('lnl_union' in k.lower() for k in simples))
study,fora=nomes(dict(s,protocolos=['torax_mama']))
import radai_sets
conferir('tórax/mama conserva exclusão das sete SBRT',study.isdisjoint(radai_sets.SO_NOS_SBRT))
sbrt,fora=nomes(s)
conferir('SBRT habilita extras torácicos',bool(sbrt & radai_sets.SO_NOS_SBRT))
conferir('migrar full não ativa todos os modelos',b.escolha_da_serie(dict(s,protocolos_3d=['anatomia_geral']))['tasks']=={})
conferir('saída nomeada única FULL', [a['cod'] for a in b.arquivos_da_escolha(dict(s,anatomia_geral_full=True))]==['full'])
s2=dict(s,protocolos=[],tasks={'teeth':1},tasks_marcadas=['teeth'])
teeth=set(radai_output.rotulos_da_task_marcada('teeth'))
mantidas,_=nomes(s2)
conferir('tarefa dentes marcada entra no STUDY',bool(teeth) and teeth<=mantidas)
k=sorted(teeth)[0]; mantidas,fora=nomes(dict(s2,oar_fora=[k]))
conferir('remoção individual prevalece sobre task',k in fora and k not in mantidas)
ts,fora=nomes(dict(s,comparacao={'ts':1}))
chaves={k for k in ts if k.startswith('ts:')}
conferir('TS cru reconhecido nas linhas do mesmo RTSTRUCT',bool(chaves))
k=sorted(chaves)[0]; ts,fora=nomes(dict(s,comparacao={'ts':1},oar_fora=[k]))
conferir('ROI comparadora pode ser retirada',k not in ts and k in fora)
tri,fora=nomes(dict(modo='perso',modalidade='MR',protocolos=['snc_rm'],oar_fora=['brainstem']))
conferir('RM oferece dez ROIs e respeita exclusão',len(tri|fora)==10 and 'brainstem' in fora and 'brainstem' not in tri)
conferir('pesos da task de vasos antiga saíram, 117 e localizadores continuam',not any('LEGACY' in x['task'] for x in t.CATALOGO) and any(117 in x['datasets'] for x in t.CATALOGO) and t.DATASET_RECORTE==298 and t.DATASET_RECORTE_ROBUSTO==297)
dicts=construir()
conferir('12 idiomas e 100% dos novos textos de interface preenchidos',len(CODIGOS)==11 and all(len(row)==12 and all(isinstance(x,str) and x.strip() for x in row) for row in tx.FRASES))
conferir('parcial fica amarelo inclusive se a mensagem também refere falha',todo._classificar('parcial: não consegui completar')=='aviso' and todo._classificar('FALHOU')=='erro')
