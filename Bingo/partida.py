import socket
import threading
import time
import random
class PartidaBingo:
    def __init__(self, codigo_partida, min_clientes=2, max_clientes=10, tempo_espera=6): #Alterar para testes rápidos
        # Identificador da partida
        self.codigo_partida = codigo_partida
        
        # Configurações da partida
        self.min_clientes = min_clientes
        self.max_clientes = max_clientes
        self.tempo_espera = tempo_espera
        
        # Lista de clientes conectados
        self.clientes = []
        self.clientes_prontos = []
        self.nomes_jogadores = {}
        
        # Números já sorteados
        self.numeros_sorteados = []
        
        # Tempo entre os sorteios em segundos
        self.tempo_para_sorteio = 3 #Tempo para testes
        # self.tempo_para_sorteio = 3 #Tempo de espera entre os sorteios 
         
        
        # Flags de controle
        self.jogo_em_andamento = False
        self.sorteio_iniciado = False
        self.partida_encerrada = False
        
        # Lock para sincronização
        self.lock = threading.Lock()
        
        print(f"Partida {self.codigo_partida} criada. Aguardando jogadores...")
    
    def adicionar_cliente(self, cliente_socket, nome_jogador):
        """
        Adiciona um cliente à partida
        """
        with self.lock:
            if cliente_socket not in self.clientes:
                self.clientes.append(cliente_socket)
                self.clientes_prontos.append(cliente_socket)
                self.nomes_jogadores[cliente_socket] = nome_jogador
                print(f"\nJogador '{nome_jogador}' conectado à partida {self.codigo_partida}. Total: {len(self.clientes_prontos)}/{self.max_clientes}")
            
            # Verifica se atingiu o máximo de jogadores
            if len(self.clientes_prontos) >= self.max_clientes and not self.sorteio_iniciado:
                print(f"\nNúmero máximo de jogadores atingido na partida {self.codigo_partida}. Iniciando o jogo...")
                return True
            
            # Se atingiu o mínimo, pode iniciar o temporizador
            if len(self.clientes_prontos) >= self.min_clientes and not self.sorteio_iniciado:
                print(f"\nMínimo de jogadores atingido na partida {self.codigo_partida}. Aguardando mais jogadores ou início da partida...")
                return "iniciar_temporizador"
            
            return False
    
    def remover_cliente(self, cliente_socket):
        """
        Remove um cliente da partida e notifica outros jogadores
        """
        with self.lock:
            nome_jogador = "Jogador desconhecido"
            if cliente_socket in self.nomes_jogadores:
                nome_jogador = self.nomes_jogadores[cliente_socket]
                del self.nomes_jogadores[cliente_socket]
                
            if cliente_socket in self.clientes:
                self.clientes.remove(cliente_socket)
            if cliente_socket in self.clientes_prontos:
                self.clientes_prontos.remove(cliente_socket)
            
            try:
                cliente_socket.shutdown(socket.SHUT_RDWR)
                cliente_socket.close()
            except:
                pass
            
            print(f"Jogador '{nome_jogador}' desconectado da partida {self.codigo_partida}. Jogadores restantes: {len(self.clientes_prontos)}")
            
            # Notificar todos os jogadores sobre a saída
            self.enviar_mensagem_para_todos(f"JOGADOR_SAIU:{nome_jogador}")
            
            # Se não houver jogadores suficientes durante o jogo, finaliza
            if self.jogo_em_andamento and len(self.clientes_prontos) < self.min_clientes:
                print(f"\nNão há jogadores suficientes para continuar a partida {self.codigo_partida}. Encerrando jogo...")
                self.finalizar_jogo('JOGO_CANCELADO:Não há jogadores suficientes')
                return "partida_cancelada"
            
            return "cliente_removido"
    
    def verificar_bingo(self, cliente_socket):
        """
        Verifica se um cliente fez bingo
        """
        vencedor = self.nomes_jogadores.get(cliente_socket, "Jogador desconhecido")
        print(f"\n--- BINGO! {vencedor} venceu a partida {self.codigo_partida}! ---")
        self.finalizar_jogo('BINGO_VENCEDOR', vencedor)
        self.jogo_em_andamento = False

        return True

    def iniciar_jogo(self):
        """
        Inicia o jogo
        """
        with self.lock:
            self.jogo_em_andamento = True
            self.sorteio_iniciado = True
        
        threading.Thread(target=self.iniciar_sorteio).start()
        return True
    
    def iniciar_sorteio(self):
        """
        Método para sortear números a cada 3 segundos
        """
        # Cria uma lista de números de 1 a 75 e embaralha
        numeros_disponiveis = list(range(1, 76))
        random.shuffle(numeros_disponiveis)
        
        while self.jogo_em_andamento and len(self.numeros_sorteados) < 75:
            # Pega o próximo número da lista embaralhada
            numero = numeros_disponiveis.pop()
            self.numeros_sorteados.append(numero)
            
            # Imprime a lista de números sorteados
            print(f"\n--- Partida {self.codigo_partida} - Números Sorteados ---")
            print(self.numeros_sorteados)
            print(f"Total de números sorteados: {len(self.numeros_sorteados)}")
            
            # Envia o número para todos os clientes
            self.enviar_numero(numero)
            
            # Verifica se ainda há clientes conectados
            if not self.clientes:
                print(f"Todos os clientes desconectados da partida {self.codigo_partida}. Encerrando jogo.")
                self.finalizar_jogo()
                break
            
            # Pausa entre os sorteios
            time.sleep(self.tempo_para_sorteio)
        
        # Finaliza o jogo se não foi finalizado por bingo
        if self.jogo_em_andamento:
            self.finalizar_jogo()
    
    def enviar_numero(self, numero):
        """
        Envia um número para todos os clientes conectados de forma segura
        """
        with self.lock:  # Adiciona lock para evitar problemas de concorrência
            clientes_remover = []
            for cliente in self.clientes[:]:  # Cria uma cópia da lista para iterar
                try:
                    cliente.send(str(numero).encode('utf-8'))
                except (socket.error, ConnectionError):  # Especifica melhor os erros
                    clientes_remover.append(cliente)
            
            # Remove clientes desconectados
            for cliente in clientes_remover:
                self.remover_cliente(cliente)
            
            # Se não houver mais clientes, finaliza o jogo
            if not self.clientes:
                print(f"\nTodos os clientes desconectados da partida {self.codigo_partida}. Encerrando jogo.")
                self.finalizar_jogo('TODOS_DESCONECTADOS')
    
    def finalizar_jogo(self, mensagem='FIM_JOGO', vencedor=None):
        """
        Finaliza o jogo e notifica todos os clientes
        """
        with self.lock:
            if self.partida_encerrada:
                return
            
            self.jogo_em_andamento = False
            self.sorteio_iniciado = False
            self.partida_encerrada = True
            
            # Formata a mensagem final com informações relevantes
            if mensagem == 'BINGO_VENCEDOR' and vencedor:
                mensagem_final = f'BINGO_VENCEDOR:{vencedor}'
            elif mensagem == 'JOGO_CANCELADO':
                mensagem_final = 'JOGO_CANCELADO:Não há jogadores suficientes'
            else:
                mensagem_final = mensagem
            
            # Envia a mensagem para todos os clientes
            for cliente in self.clientes[:]:  # Usa uma cópia da lista
                try:
                    cliente.send(mensagem_final.encode('utf-8'))
                    time.sleep(0.1)  # Pequena pausa para evitar congestionamento
                except:
                    pass
            
            # Fecha as conexões
            for cliente in self.clientes[:]:
                try:
                    cliente.shutdown(socket.SHUT_RDWR)
                    cliente.close()
                except:
                    pass
            
            self.clientes.clear()
            self.clientes_prontos.clear()
            self.nomes_jogadores.clear()
            
            print(f"\nPartida {self.codigo_partida} finalizada.")
            
    def enviar_mensagem_para_todos(self, mensagem):
        """
        Envia uma mensagem para todos os clientes conectados
        """
        with self.lock:
            clientes_remover = []
            for cliente in self.clientes[:]:  # Cria uma cópia da lista para iterar
                try:
                    cliente.send(mensagem.encode('utf-8'))
                except:
                    clientes_remover.append(cliente)
            
            # Remove clientes desconectados
            for cliente in clientes_remover:
                self.remover_cliente(cliente)