# python app.py apenas

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string
from cartela import GerenciadorCartelas
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bingo_secret_key'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", logger=True, engineio_logger=True)

# Dicionário para armazenar as partidas ativas
partidas = {}

# Dicionário para armazenar os gerenciadores de cartelas dos jogadores
gerenciadores_cartelas = {}

def iniciar_jogo(codigo):
    """Função auxiliar para iniciar o jogo"""
    print(f"Iniciando jogo na sala {codigo}")
    if codigo not in partidas:
        print(f"Partida {codigo} não existe mais")
        return
        
    partida = partidas[codigo]
    
    # Muda o estado para em_andamento e limpa os números sorteados
    partida['estado'] = 'em_andamento'
    partida['numeros_sorteados'] = []
    partida['vencedor'] = None
    
    # Notifica todos os jogadores que o jogo começou
    socketio.emit('jogo_iniciado', room=codigo)
    socketio.emit('atualizar_estado', {
        'estado': 'em_andamento',
        'mensagem': 'O jogo começou! Boa sorte!'
    }, room=codigo)
    
    # Inicia o sorteio de números em uma nova thread
    eventlet.spawn(sortear_numeros, codigo)

def sortear_numeros(codigo):
    """Função auxiliar para sortear números"""
    print(f"Iniciando sorteio de números na sala {codigo}")
    if codigo not in partidas:
        print(f"Partida {codigo} não existe mais")
        return
        
    numeros_disponiveis = list(range(1, 76))
    random.shuffle(numeros_disponiveis)
    
    for numero in numeros_disponiveis:
        # Verifica se a partida ainda existe e está em andamento
        if codigo not in partidas or partidas[codigo]['estado'] != 'em_andamento':
            print(f"Partida {codigo} finalizada ou não existe mais")
            break
        
        print(f"Sorteando número {numero} na sala {codigo}")
        partidas[codigo]['numeros_sorteados'].append(numero)
        socketio.emit('numero_sorteado', {'numero': numero}, room=codigo)
        
        # Verifica se algum jogador fez bingo
        for jogador in partidas[codigo]['jogadores']:
            if jogador in gerenciadores_cartelas:
                gerenciador = gerenciadores_cartelas[jogador]
                gerenciador.marcar_numero_em_todas_cartelas(numero)
                cartela_bingo = gerenciador.verificar_bingo_em_todas_cartelas()
                
                if cartela_bingo:
                    print(f"BINGO! Jogador {jogador} venceu na sala {codigo}")
                    partidas[codigo]['estado'] = 'finalizado'
                    partidas[codigo]['vencedor'] = jogador
                    socketio.emit('bingo', {'vencedor': jogador}, room=codigo)
                    return
        
        eventlet.sleep(3)  # Espera 3 segundos entre os sorteios

def contagem_regressiva(codigo):
    """Função auxiliar para contagem regressiva"""
    print(f"Iniciando contagem regressiva na sala {codigo}")
    
    for i in range(30, -1, -1):
        if codigo not in partidas:
            print(f"Partida {codigo} não existe mais")
            return
        if partidas[codigo]['estado'] != 'contagem':
            print(f"Partida {codigo} não está mais em contagem")
            return
            
        print(f"Contagem {i} segundos na sala {codigo}")
        socketio.emit('atualizar_contagem', {'segundos': i}, room=codigo)
        
        if i == 0:
            print(f"Contagem finalizada, iniciando jogo na sala {codigo}")
            iniciar_jogo(codigo)  # Chama a função que inicia o jogo
            return
        
        eventlet.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jogar', methods=['GET', 'POST'])
def jogar():
    if request.method == 'POST':
        nome_jogador = request.form.get('nome_jogador')
        if not nome_jogador:
            return redirect(url_for('index'))
        
        session['nome_jogador'] = nome_jogador
        return render_template('jogar.html', nome_jogador=nome_jogador)
    
    return redirect(url_for('index'))

@app.route('/partida/<codigo>')
def partida(codigo):
    if 'nome_jogador' not in session:
        return redirect(url_for('index'))
    
    if codigo not in partidas:
        return redirect(url_for('jogar'))
    
    return render_template('partida.html', 
                         codigo=codigo, 
                         nome_jogador=session['nome_jogador'])

@socketio.on('connect')
def handle_connect():
    print(f"Cliente conectado: {request.sid}")
    # Se o jogador já estava em uma partida, reconecta à sala
    nome_jogador = session.get('nome_jogador')
    if nome_jogador:
        for codigo, partida in partidas.items():
            if nome_jogador in partida['jogadores']:
                join_room(codigo)
                print(f"Reconectando {nome_jogador} à sala {codigo}")
                # Reenvia o estado atual da partida
                emit('jogador_entrou', {'nome': nome_jogador}, room=codigo)
                if partida['estado'] == 'contagem':
                    emit('iniciar_contagem', room=codigo)
                elif partida['estado'] == 'em_andamento':
                    emit('jogo_iniciado', room=codigo)
                break

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Cliente desconectado: {request.sid}")

@socketio.on('criar_partida')
def criar_partida():
    nome_jogador = session.get('nome_jogador')
    if not nome_jogador:
        emit('erro', {'mensagem': 'Nome do jogador não encontrado'})
        return
    
    # Verifica se o jogador já está em alguma partida
    for codigo_partida, partida in partidas.items():
        if nome_jogador in partida['jogadores']:
            if partida['estado'] == 'aguardando':
                join_room(codigo_partida)
                emit('partida_criada', {'codigo': codigo_partida})
                emit('jogador_entrou', {'nome': nome_jogador}, room=codigo_partida)
                return
            else:
                emit('erro', {'mensagem': 'Você já está em uma partida em andamento'})
                return
    
    # Gera um código único para a partida
    codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while codigo in partidas:
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    print(f"Criando nova partida com código {codigo}")
    
    # Inicializa a partida
    partidas[codigo] = {
        'jogadores': [nome_jogador],
        'estado': 'aguardando',
        'numeros_sorteados': [],
        'vencedor': None
    }
    
    # Cria um gerenciador de cartelas para o jogador
    gerenciadores_cartelas[nome_jogador] = GerenciadorCartelas()
    
    # Adiciona o jogador à sala
    join_room(codigo)
    
    emit('partida_criada', {'codigo': codigo})
    emit('jogador_entrou', {'nome': nome_jogador}, room=codigo)

@socketio.on('entrar_partida')
def entrar_partida(data):
    codigo = data.get('codigo')
    nome_jogador = session.get('nome_jogador')
    
    if not nome_jogador:
        emit('erro', {'mensagem': 'Nome do jogador não encontrado'})
        return
    
    if codigo not in partidas:
        emit('erro', {'mensagem': 'Partida não encontrada'})
        return
    
    partida = partidas[codigo]
    
    # Verifica se o jogador já está na partida
    if nome_jogador in partida['jogadores']:
        join_room(codigo)
        # Envia lista atualizada de jogadores para todos
        for jogador in partida['jogadores']:
            socketio.emit('jogador_entrou', {'nome': jogador}, room=codigo)
        emit('redirecionar', {'codigo': codigo})
        return
    
    # Verifica se a partida já está em andamento
    if partida['estado'] == 'em_andamento':
        emit('erro', {'mensagem': 'Esta partida já está em andamento. Não é possível entrar agora.'})
        return
    
    print(f"Jogador {nome_jogador} entrando na partida {codigo}")
    
    # Adiciona o jogador à partida
    partida['jogadores'].append(nome_jogador)
    
    # Cria um gerenciador de cartelas para o jogador
    gerenciadores_cartelas[nome_jogador] = GerenciadorCartelas()
    
    # Adiciona o jogador à sala
    join_room(codigo)
    
    # Notifica todos na sala sobre todos os jogadores
    for jogador in partida['jogadores']:
        socketio.emit('jogador_entrou', {'nome': jogador}, room=codigo)
    
    # Redireciona o jogador para a página da partida
    emit('redirecionar', {'codigo': codigo})
    
    # Se temos dois jogadores e a contagem ainda não começou, inicia a contagem regressiva
    if len(partida['jogadores']) >= 2 and partida['estado'] == 'aguardando':
        print(f"Dois ou mais jogadores conectados na sala {codigo}, iniciando contagem")
        partida['estado'] = 'contagem'
        eventlet.spawn(contagem_regressiva, codigo)

@socketio.on('solicitar_cartelas')
def enviar_cartelas():
    nome_jogador = session.get('nome_jogador')
    if nome_jogador in gerenciadores_cartelas:
        gerenciador = gerenciadores_cartelas[nome_jogador]
        cartelas = []
        
        for cartela in gerenciador.cartelas:
            cartelas.append({
                'numeros': cartela.cartela_numeros.tolist(),
                'marcacao': cartela.cartela_marcacao.tolist()
            })
        
        emit('cartelas', {'cartelas': cartelas})

@socketio.on('entrar_sala')
def entrar_sala(data):
    codigo = data.get('codigo')
    nome = data.get('nome')
    if not codigo or not nome:
        emit('erro', {'mensagem': 'Código e nome são obrigatórios'})
        return
    
    if codigo not in partidas:
        emit('erro', {'mensagem': 'Sala não encontrada'})
        return
    
    sala = partidas[codigo]
    
    # Verifica se o jogo já começou (estado em_andamento)
    if sala['estado'] == 'em_andamento':
        emit('erro', {'mensagem': 'O jogo já começou. Não é possível entrar agora.'})
        return
    
    # Verifica se o nome já está em uso
    if nome in [jogador['nome'] for jogador in sala['jogadores'].values()]:
        emit('erro', {'mensagem': 'Nome já está em uso'})
        return
    
    # Adiciona o jogador à sala
    sid = request.sid
    sala['jogadores'][sid] = {
        'nome': nome,
        'cartelas': [],
        'bingo': False
    }
    
    # Gera cartelas para o novo jogador
    cartelas = []
    for _ in range(3):
        cartela = gerar_cartela()
        cartelas.append({
            'numeros': cartela,
            'marcacao': [[False for _ in range(5)] for _ in range(5)]
        })
    sala['jogadores'][sid]['cartelas'] = cartelas
    
    # Adiciona o jogador à sala do Socket.IO
    join_room(codigo)
    
    # Atualiza o estado da sala
    if len(sala['jogadores']) >= 2 and sala['estado'] == 'aguardando':
        sala['estado'] = 'contagem'
        sala['contagem'] = 30
        emit('atualizar_estado', {
            'estado': 'contagem',
            'contagem': 30
        }, room=codigo)
    
    # Envia as cartelas para o jogador
    emit('cartelas', {'cartelas': cartelas})
    
    # Atualiza a lista de jogadores para todos
    emit('atualizar_jogadores', {
        'jogadores': [jogador['nome'] for jogador in sala['jogadores'].values()]
    }, room=codigo)

@socketio.on('iniciar_jogo')
def handle_iniciar_jogo(data):
    """Handler do evento de iniciar jogo via Socket.IO"""
    codigo = data.get('codigo')
    if not codigo or codigo not in partidas:
        emit('erro', {'mensagem': 'Sala não encontrada'})
        return
    
    sala = partidas[codigo]
    
    # Verifica se o jogo já começou
    if sala['estado'] != 'aguardando' and sala['estado'] != 'contagem':
        emit('erro', {'mensagem': 'O jogo já começou'})
        return
    
    # Verifica se há jogadores suficientes
    if len(sala['jogadores']) < 2:
        emit('erro', {'mensagem': 'É necessário pelo menos 2 jogadores'})
        return
    
    # Inicia o jogo chamando a função auxiliar
    iniciar_jogo(codigo)

@socketio.on('sair_sala')
def sair_sala(data):
    codigo = data.get('codigo')
    if not codigo or codigo not in partidas:
        emit('erro', {'mensagem': 'Sala não encontrada'})
        return
    
    sala = partidas[codigo]
    sid = request.sid
    
    # Remove o jogador da sala
    if sid in sala['jogadores']:
        del sala['jogadores'][sid]
        leave_room(codigo)
        
        # Se não houver mais jogadores, remove a sala
        if not sala['jogadores']:
            del partidas[codigo]
        else:
            # Se o jogo ainda não começou, atualiza o estado
            if sala['estado'] == 'aguardando' or sala['estado'] == 'contagem':
                if len(sala['jogadores']) < 2:
                    sala['estado'] = 'aguardando'
                    sala['contagem'] = None
                    emit('atualizar_estado', {
                        'estado': 'aguardando'
                    }, room=codigo)
            
            # Atualiza a lista de jogadores
            emit('atualizar_jogadores', {
                'jogadores': [jogador['nome'] for jogador in sala['jogadores']]
            }, room=codigo)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0') 