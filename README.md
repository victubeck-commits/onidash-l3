# OniDash L3

OniDash L3 e uma utilidade para Windows com controles Xbox. Detecta um duplo toque rapido do analogico esquerdo (ou pressoes configuraveis de botoes) e simula automaticamente um clique do stick esquerdo (LS/L3), usado em jogos como **Onimusha: Way of the Sword** para correr.

## Por que este projeto

Jogos como Onimusha: Way of the Sword usam o duplo toque do analogico esquerdo ou o clique LS/L3 para ativar a corrida. Em controles reais essa deteccao pode falhar ou ser desconfortavel. Este programa cria um controle Xbox virtual e injeta o LS no momento certo, sem interferir na movimentacao normal.

## Funcionalidades

- Leitura em tempo real do controle Xbox real via XInput.
- Controle Xbox virtual via ViGEmBus/vgamepad.
- Espelhamento de todos os eixos e botoes para o controle virtual.
- Gatilho por analogico: empurre o stick para frente de 0 a 4 vezes. 0 significa "so de segurar".
- Gatilho por botao: escolha A, B, X, Y, LB, RB, LT, RT, L3/L4, Start, Back ou D-Pad, com 1 a 4 pressoes.
- Modo do L3: Segurar (corre enquanto anda) ou Toque (clique rapido).
- Delay de ativacao e desativacao configuravel (0 a 1000 ms), com opcao de ativar/desativar.
- Interface preto/dourado, icone, status em tempo real e indicador do LS.
- Suporte opcional ao HidHide para ocultar o controle real e tornar o virtual o principal.
- Idiomas: Portugues, English, Espanol.

## Requisitos

- Windows 10/11.
- Controle Xbox (USB recomendado).
- ViGEmBus Driver 1.22 ou superior.
- XInput (ja incluso no Windows).
- Para rodar o script: Python 3.10+ com `XInput-Python` e `vgamepad`.
- Opcional: HidHide.

## Como usar (script)

```bat
cd %USERPROFILE%\Documents\XboxDashL3
pip install XInput-Python vgamepad
python xbox_dash_l3.py
```

## Como usar (.exe)

Abra `dist\OniDashL3\OniDashL3.exe` ou o atalho `OniDash L3`.

Passos:
1. Conecte o controle Xbox por USB.
2. Selecione o controle na lista.
3. Ajuste gatilhos, modo e delays.
4. Ative a funcao.
5. No jogo/Steam, escolha o controle virtual se necessario.

## HidHide (opcional)

Para tornar o controle virtual principal automaticamente:
1. Instale o HidHide: https://github.com/nefarius/HidHide/releases
2. Marque "Usar HidHide" no app.
3. Reinicie o app.
4. Reconecte o USB do controle.

## Limitacoes

- Alguns jogos leem o controle fisico (slot 0) antes do virtual. Se o virtual nao responder, use HidHide, reconecte ou altere a ordem.
- A deteccao de duplo toque depende da calibracao do analogico; ajuste limiar, histerese, intervalo e delays.
- HidHide e um driver de terceiros e pode exigir reinicio.
- O programa nao substitui nem altera o driver do controle real.

## Solucao de problemas

- Se aparecer "vgamepad indisponivel", instale o ViGEmBus e reinicie.
- Falso positivo: aumente o limiar e reduza o intervalo.
- Nao detecta: diminua o limiar e aumente o intervalo; verifique a opcao de inverter eixo Y.
- Pressoes de botao nao contam: solte totalmente o botao entre os toques.

## Arquivos de idioma

- `README.md` - Portugues
- `README.en.md` - English
- `README.es.md` - Espanol