# 🎉 Bingo - Jogo Online 🎉

## Descrição

Este é um projeto em **Python** que implementa uma versão **online** do jogo **Bingo**. Os jogadores poderão se conectar ao servidor e interagir em tempo real através de um chat enquanto jogam. O objetivo é completar a cartela de números para ganhar o prêmio da partida, que pode ser uma quantia de dinheiro 💰 ou um prêmio material 🎁.

## Observações
- O jogo será implementado utilizando **Sockets** em **Python** 🔌.
- O jogo será **online**: os jogadores se conectam ao servidor e interagem em tempo real 🌐.

## Bibliotecas Necessárias

```txt
flask>=2.3.0
flask-socketio>=5.3.0
python-socketio>=5.8.0
python-engineio>=4.4.0
numpy>=1.24.0
eventlet>=0.33.0
gunicorn
```


### Para rodar o projeto, certifique-se de ter o Python instalado em seu sistema. As bibliotecas utilizadas no projeto são:

- `socket` (Padrão do Python) – Utilizada para comunicação entre cliente e servidor.
- `threading` (Padrão do Python) – Permite execução concorrente de múltiplas threads.
- `random` (Padrão do Python) – Geração de números aleatórios.
- `time` (Padrão do Python) – Utilizada para pausas e temporização no jogo.
- `flask` – Utilizado para criar a interface web.
- `flask-socketio` – Comunicação em tempo real entre servidor e clientes.
- `eventlet` – Servidor assíncrono para aplicações em Flask com WebSocket.
- `numpy` – Manipulação eficiente de dados numéricos (como as cartelas).
- `gunicorn` – Servidor WSGI para hospedar a aplicação online.

## Integrantes
- Camila Fontes 👩‍💻
- Laila Valença 👩‍💻
- Miguel Ferreira 👨‍💻
- Marlysson Dantas 👨‍💻

## Regras do Jogo
1. O jogo começa quando **no mínimo 2 jogadores** estão conectados 👥.
2. A cada intervalo de tempo, um **número será sorteado** e os jogadores deverão marcar o número na sua cartela 🏷️.
3. Quando um jogador marcar **todos os números** em sua cartela, ele pode declarar **"BINGO"** 🎉. O servidor verifica se a cartela está completa e, se estiver, o jogador vence!
4. Caso o jogador tenha declarado **"BINGO"** sem ter ganhado, a punição é não poder declarar por um determinado tempo.
5. O **prêmio** da partida será dado ao vencedor 🏆.

## Funcionalidades
- **Histórico de Números Sorteados**: O administrador pode escolher se deseja manter um registro dos números sorteados 📜.
- **Punição por BINGO falso**: Jogadores que declararem "BINGO" incorretamente serão **punidos com um tempo de espera**, mas não serão expulsos ❗.
- **Aviso de BINGO**: O sistema avisa a todos os jogadores quando alguém declarar "BINGO" 📢.
- **Verificação de Vencedor**: O servidor verifica se alguém completou sua cartela corretamente e avisa se o jogo continuará ou se alguém venceu 🥳.

## Ideias Extras (Sugestões)
- **Chat**: Os jogadores podem conversar entre si enquanto jogam 🗣️.
- **Múltiplas Cartelas**: A possibilidade de um jogador ter **mais de uma cartela** para aumentar as chances de ganhar 🎲.

## Como Jogar
1. Conecte-se ao servidor 🖥️.
2. Aguarde o sorteio dos números ⏳.
3. Marque os números na sua cartela ✍️.
4. Declare **"BINGO"** quando completar a cartela 🔴.
5. O servidor verifica se a sua cartela está correta ✔️.
6. Se alguém vencer, o jogo será encerrado e o prêmio será atribuído ao vencedor 🏅.

## Tecnologias Utilizadas
- **Python**: Linguagem de programação para o desenvolvimento do jogo 🐍.
- **Sockets**: Comunicação em rede para o jogo online 🌐.

## Possibilidades para colocar o jogo online (IP público)
- Jogar o seguinte código no terminal após rodar o app.py (serveo): `ssh -R 80:localhost:5000 serveo.net`
- Jogar o seguinte código no terminal após rodar o app.py (ngrok): `ngrok http 5000`
