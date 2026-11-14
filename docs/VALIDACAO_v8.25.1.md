# Procedência dos componentes — 8.25.1

A verificação anônima dos arquivos públicos revelou que o cache usado na construção da 8.25 tinha finais de linha Windows. O GitHub serve os mesmos componentes com finais de linha LF. A trava de construção foi corrigida para os bytes públicos exatos.

Todos os arquivos diferentes foram comparados: somente os finais de linha mudaram. Os arquivos Python também passaram por comparação de suas árvores sintáticas, sem diferença de algoritmo. A execução funcional e as entregas DICOM verificadas na 8.25 permanecem aplicáveis.

O SETUP já contém os componentes. A correção trata de sua procedência e da reprodução da construção a partir dos repositórios públicos. O LUNG 1.1.11 incorpora o instalador principal 8.25.1; NEURO 1.3.11 e receitas de pesos permanecem iguais.

Para preparar caches e travas, utilizar os arquivos do GitHub e a rotina build/baixar_componentes.py. Não deduzir o hash público a partir de git archive com conversão de finais de linha do Windows. Conferir todas as árvores públicas antes de promover o LATEST.
