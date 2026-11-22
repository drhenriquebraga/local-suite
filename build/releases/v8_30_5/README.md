# Local Suite 8.30.5

## Acabamento FAST

Em Configurações, escolha uma das cinco posições e compare as bordas sobre o mesmo corte de tórax ou de abdome. O nível central reproduz o FAST da 8.30.4. No AUTO de TC, a preferência se aplica às bolsas intestinais. No PERSONALIZADO, ela entra quando o operador escolhe FAST. A construção anatômica das estruturas continua fazendo parte da entrega.

As dez imagens são cortes de fantomas matemáticos, gerados sem dados de pacientes. As linhas vêm das coordenadas relidas no RTSTRUCT produzido pelo motor para cada nível. A alteração do acabamento pode mudar a aparência dos contornos e a densidade de vértices. O tempo de execução varia com a estrutura e a estação.

Para reproduzir as prévias, extraia o SETUP em uma pasta de trabalho e execute `python qa/gerar_previas.py --programa CAMINHO_DO_SETUP/programa` com o runtime da suíte. O script grava os dez PNGs nessa extração. O arquivo `qa/verificacao-fantomas.json` registra a soma SHA-256 e o número de pontos de cada contorno no corte apresentado.

## Ao abrir a suíte

Na primeira abertura interativa, o guia fica disponível após a seleção de idioma e o aceite de termos. A primeira dica aparece ao sair do guia. Nas aberturas seguintes, o app mostra uma dica por vez e guarda na estação quais já foram exibidas. Em Configurações → Geral, o operador pode rever o guia e ligar ou desligar as dicas. As preferências integram a transferência de configurações da suíte.

## Rebuild

Use the Python and zlib versions in `manifest.json`. The script verifies the previous installer and the exact bytes of each member and of the rebuilt ZIP. [Download the 8.30.4 baseline](https://github.com/drhenriquebraga/local-suite/releases/download/v8.30.4/RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.4.zip)

```powershell
python rebuild.py RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.4.zip RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.30.5.zip
```
