# Local Suite 8.30.9

O instalador mostra as versões dos plugins compatíveis e reúne os termos necessários para a seleção em uma tela. Os itens começam marcados para revisão. O botão de aceite registra a decisão do operador para a seleção apresentada.

Na montagem de um pacote offline da suíte, o preparador confere os componentes locais e grava o ZIP no destino escolhido. Uma estação com os componentes da seleção completos pode preparar o pacote sem internet. A estimativa de espaço considera o destino e os temporários dos componentes faltantes.

O visor dos seis esforços usa a TC pública s0102 do University Hospital Basel, da região central do tórax à região central do fígado. Os seis contornos compartilham uma única base de 98 cortes. A demonstração acompanha o download de dependências e o pacote offline da suíte. [Origem da TC e licença](https://zenodo.org/records/10047292)



## Reproduzir o instalador

Execute na pasta da receita com o ZIP pÃºblico da versÃ£o 8.30.8.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.8.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.9.zip
```
