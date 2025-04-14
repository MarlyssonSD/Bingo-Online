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
partidas = {}  # Partidas da Sala Particular
partidas_sala_2 = {}  # Partidas da Sala Pública

# Dicionário para armazenar os gerenciadores de cartelas dos jogadores
gerenciadores_cartelas = {}

def iniciar_jogo(codigo, tipo_sala='1'):
    """Função auxiliar para iniciar o jogo"""
    print(f"Iniciando jogo na sala {codigo}")
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    if codigo not in partidas_dict:
        print(f"Partida {codigo} não existe mais")
        return
        
    partida = partidas_dict[codigo]
    
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
    eventlet.spawn(sortear_numeros, codigo, tipo_sala)

def sortear_numeros(codigo, tipo_sala='1'):
    """Função auxiliar para sortear números"""
    print(f"Iniciando sorteio de números na sala {codigo}")
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    if codigo not in partidas_dict:
        print(f"Partida {codigo} não existe mais")
        return
        
    numeros_disponiveis = list(range(1, 76))
    random.shuffle(numeros_disponiveis)
    
    for numero in numeros_disponiveis:
        # Verifica se a partida ainda existe e está em andamento
        if codigo not in partidas_dict or partidas_dict[codigo]['estado'] != 'em_andamento':
            print(f"Partida {codigo} finalizada ou não existe mais")
            break
        
        print(f"Sorteando número {numero} na sala {codigo}")
        partidas_dict[codigo]['numeros_sorteados'].append(numero)
        socketio.emit('numero_sorteado', {'numero': numero}, room=codigo)
        
        eventlet.sleep(3)  # Espera 3 segundos entre os sorteios

def contagem_regressiva(codigo, tipo_sala='1'):
    """Função auxiliar para contagem regressiva"""
    print(f"Iniciando contagem regressiva na sala {codigo}")
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    for i in range(30, -1, -1):
        if codigo not in partidas_dict:
            print(f"Partida {codigo} não existe mais")
            return
        if partidas_dict[codigo]['estado'] != 'contagem':
            print(f"Partida {codigo} não está mais em contagem")
            return
            
        print(f"Contagem {i} segundos na sala {codigo}")
        socketio.emit('atualizar_contagem', {'segundos': i}, room=codigo)
        
        if i == 0:
            print(f"Contagem finalizada, iniciando jogo na sala {codigo}")
            iniciar_jogo(codigo, tipo_sala)  # Chama a função que inicia o jogo
            return
        
        eventlet.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jogar', methods=['GET', 'POST'])
def jogar():
    if request.method == 'POST':
        nome_jogador = request.form.get('nome_jogador')
        tipo_sala = request.form.get('tipo_sala', '1')  # '1' para Sala Particular, '2' para Sala Pública
        if not nome_jogador:
            return redirect(url_for('index'))
        
        session['nome_jogador'] = nome_jogador
        session['tipo_sala'] = tipo_sala
        return render_template('jogar.html', nome_jogador=nome_jogador, tipo_sala=tipo_sala)
    
    return redirect(url_for('index'))

@app.route('/partida/<codigo>')
def partida(codigo):
    if 'nome_jogador' not in session:
        return redirect(url_for('index'))
    
    tipo_sala = session.get('tipo_sala', '1')
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    if codigo not in partidas_dict:
        return redirect(url_for('jogar'))
    
    return render_template('partida.html', 
                         codigo=codigo, 
                         nome_jogador=session['nome_jogador'])

@socketio.on('connect')
def handle_connect():
    print(f"Cliente conectado: {request.sid}")
    # Se o jogador já estava em uma partida, reconecta à sala
    nome_jogador = session.get('nome_jogador')
    tipo_sala = session.get('tipo_sala', '1')
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    if nome_jogador:
        for codigo, partida in partidas_dict.items():
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
    tipo_sala = session.get('tipo_sala', '1')
    
    if not nome_jogador:
        emit('erro', {'mensagem': 'Nome do jogador não encontrado'})
        return
    
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    # Verifica se o jogador já está em alguma partida
    for codigo_partida, partida in partidas_dict.items():
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
    while codigo in partidas_dict:
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    print(f"Criando nova partida com código {codigo}")
    
    # Inicializa a partida
    partidas_dict[codigo] = {
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
    tipo_sala = session.get('tipo_sala', '1')
    
    if not nome_jogador:
        emit('erro', {'mensagem': 'Nome do jogador não encontrado'})
        return
    
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    if codigo not in partidas_dict:
        emit('erro', {'mensagem': 'Partida não encontrada'})
        return
    
    partida = partidas_dict[codigo]
    
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
        eventlet.spawn(contagem_regressiva, codigo, tipo_sala)

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
    nome_jogador = session.get('nome_jogador')
    tipo_sala = session.get('tipo_sala', '1')
    
    if not nome_jogador:
        emit('erro', {'mensagem': 'Nome do jogador não encontrado'})
        return
        
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    if not codigo or codigo not in partidas_dict:
        emit('erro', {'mensagem': 'Sala não encontrada'})
        return
    
    sala = partidas_dict[codigo]
    
    # Verifica se o jogo está em andamento e tem apenas 2 jogadores
    jogo_em_andamento = sala['estado'] == 'em_andamento'
    tem_dois_jogadores = len(sala['jogadores']) == 2
    
    # Remove o jogador da sala
    if nome_jogador in sala['jogadores']:
        sala['jogadores'].remove(nome_jogador)
        leave_room(codigo)
        
        # Se não houver mais jogadores, remove a sala
        if not sala['jogadores']:
            del partidas_dict[codigo]
        else:
            # Se o jogo estava em andamento e tinha apenas 2 jogadores,
            # o jogador restante é o vencedor
            if jogo_em_andamento and tem_dois_jogadores:
                jogador_restante = sala['jogadores'][0]
                print(f"VITÓRIA POR WO! Jogador {jogador_restante} venceu na sala {codigo} porque o outro jogador saiu.")
                sala['estado'] = 'finalizado'
                sala['vencedor'] = jogador_restante
                socketio.emit('bingo', {'vencedor': jogador_restante, 'vitoria_por_wo': True}, room=codigo)
                socketio.emit('mensagem', {
                    'texto': f"O jogador {nome_jogador} saiu da partida. {jogador_restante} foi declarado vencedor!",
                    'vitoria_por_wo': True
                }, room=codigo)
            # Se o jogo ainda não começou, atualiza o estado
            elif sala['estado'] == 'aguardando' or sala['estado'] == 'contagem':
                if len(sala['jogadores']) < 2:
                    sala['estado'] = 'aguardando'
                    sala['contagem'] = None
                    emit('atualizar_estado', {
                        'estado': 'aguardando'
                    }, room=codigo)
            
            # Atualiza a lista de jogadores
            emit('atualizar_jogadores', {
                'jogadores': sala['jogadores']
            }, room=codigo)
    
    # Notifica a sala que o jogador saiu
    emit('jogador_saiu', {'nome': nome_jogador}, room=codigo)

@socketio.on('solicitar_partidas')
def enviar_partidas(data):
    tipo_sala = data.get('tipo_sala', '1')
    # Só envia partidas disponíveis para Sala Pública
    if tipo_sala != '2':
        return
        
    partidas_disponiveis = []
    
    for codigo, partida in partidas_sala_2.items():
        # Incluir partidas tanto em aguardando quanto em contagem
        if partida['estado'] in ['aguardando', 'contagem']:
            partidas_disponiveis.append({
                'codigo': codigo,
                'jogadores': partida['jogadores'],
                'estado': partida['estado'],
                'contagem': partida.get('contagem', None)
            })
    
    emit('atualizar_partidas', {'partidas': partidas_disponiveis})

@socketio.on('bingo')
def handle_bingo(data):
    """Handler do evento de bingo via Socket.IO"""
    codigo = data.get('codigo')
    nome_jogador = session.get('nome_jogador')
    tipo_sala = session.get('tipo_sala', '1')
    
    if not nome_jogador:
        emit('erro', {'mensagem': 'Nome do jogador não encontrado'})
        return
    
    partidas_dict = partidas if tipo_sala == '1' else partidas_sala_2
    
    if codigo not in partidas_dict:
        emit('erro', {'mensagem': 'Partida não encontrada'})
        return
    
    partida = partidas_dict[codigo]
    
    # Verifica se o jogo está em andamento
    if partida['estado'] != 'em_andamento':
        emit('erro', {'mensagem': 'O jogo não está em andamento'})
        return
    
    # Marca todos os números sorteados na cartela do jogador
    gerenciador = gerenciadores_cartelas[nome_jogador]
    for numero in partida['numeros_sorteados']:
        gerenciador.marcar_numero_em_todas_cartelas(numero)
    
    # Verifica se o jogador fez bingo
    cartela_bingo = gerenciador.verificar_bingo_em_todas_cartelas()
    
    if cartela_bingo:
        print(f"BINGO! Jogador {nome_jogador} venceu na sala {codigo}")
        partida['estado'] = 'finalizado'
        partida['vencedor'] = nome_jogador
        socketio.emit('bingo', {'vencedor': nome_jogador}, room=codigo)
    else:
        emit('erro', {'mensagem': 'Bingo inválido! Verifique sua cartela novamente.'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0') 