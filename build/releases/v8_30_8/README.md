# Local Suite 8.30.8

A seleção de esforço passa a mostrar uma única imagem da TC de demonstração. O visor abre no corte central. Ao escolher outro card, os contornos mudam no mesmo corte. O botão de ajuda ao lado de **Esforço de processamento** reúne a origem da TC, os modelos e as estruturas gravadas. A seção **Comparar esforços** começa recolhida.

Em TC, o esforço **Leve** usa a rede nativa de 6 mm. Neste exemplo público, gravou 32 das 33 estruturas solicitadas. A vesícula ficou sem contorno. **Alto**, **Extra** e **Máximo** compartilham a rede de 1,5 mm e o mesmo acabamento anatômico. Nos RTSTRUCTs desta TC, o Alto gravou 49,47% menos vértices e o Extra gravou 24,98% menos vértices que o Máximo. Os cartões apresentam o tempo estimado de processamento da suíte em relação ao Máximo. O tempo de importação no TPS ainda não foi medido.

A TC de demonstração é o caso s0102 da coleção TotalSegmentator CT v2.0.1 do University Hospital Basel, licenciada em CC BY 4.0. O pacote offline mínimo compatível é o 8.30.6. [Origem da TC](https://zenodo.org/records/10047292)


## Reproduzir o instalador

Execute na pasta da receita com o ZIP público da versão 8.30.7.

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.7.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.8.zip
```
