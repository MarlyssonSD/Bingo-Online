import socket
import threading
import time
import random
import numpy as np

class ServidorBingo:
    def __init__(self, host='0.0.0.0', porta=12345, max_clientes=3, tempo_espera=30):
        # Configurações de conexão
        self.host = host
        self.porta = porta
        self.max_clientes = max_clientes
        self.tempo_espera = tempo_espera
        
        # Socket do servidor
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.bind((self.host, self.porta))
        self.servidor.listen(self.max_clientes)
        
        # Lista de clientes conectados
        self.clientes = []
        self.clientes_prontos = []
        
        # Números já sorteados
        self.numeros_sorteados = []
        
        # Flag para controle do jogo
        self.jogo_em_andamento = False
        
        # Lock para sincronização
        self.lock = threading.Lock()
        
        print(f"Servidor de Bingo iniciado em {self.host}:{self.porta}")
        print(f"Número mínimo de jogadores: {self.max_clientes}")
    
    def enviar_numero(self, numero):
        """
        Envia um número para todos os clientes conectados de forma segura
        """
        clientes_remover = []
        for cliente in self.clientes:
            try:
                cliente.send(str(numero).encode('utf-8'))
            except:
                clientes_remover.append(cliente)
        
        # Remove clientes desconectados
        for cliente in clientes_remover:
            if cliente in self.clientes:
                self.clientes.remove(cliente)
            if cliente in self.clientes_prontos:
                self.clientes_prontos.remove(cliente)
    
    def finalizar_jogo(self, mensagem='FIM_JOGO'):
        """
        Finaliza o jogo e notifica todos os clientes
        """
        self.jogo_em_andamento = False
        for cliente in self.clientes:
            try:
                cliente.send(mensagem.encode('utf-8'))
            except:
                pass
    
    def iniciar_sorteio(self):
        """
        Método para sortear números a cada 3 segundos
        """
        # Cria uma lista de números de 1 a 75 e embaralha
        numeros_disponiveis = list(range(1, 76))
        random.shuffle(numeros_disponiveis)
        
        while self.jogo_em_andamento and len(self.numeros_sorteados) < 75:
            with self.lock:
                # Pega o próximo número da lista embaralhada
                numero = numeros_disponiveis.pop()
                self.numeros_sorteados.append(numero)
                
                # Imprime a lista de números sorteados
                print("\n--- Números Sorteados ---")
                print(self.numeros_sorteados)
                print(f"Total de números sorteados: {len(self.numeros_sorteados)}")
                
                # Envia o número para todos os clientes
                self.enviar_numero(numero)
                
                # Verifica se ainda há clientes conectados
                if not self.clientes:
                    print("Todos os clientes desconectados. Encerrando jogo.")
                    self.finalizar_jogo()
                    break
            
            # Pausa de 3 segundos entre os sorteios
            time.sleep(3)
        
        # Finaliza o jogo se não foi finalizado por bingo
        if self.jogo_em_andamento:
            self.finalizar_jogo()
    
    def gerenciar_cliente(self, cliente_socket):
        """
        Gerencia a conexão com cada cliente
        """
        try:
            # Envia confirmação de conexão
            cliente_socket.send('CONECTADO'.encode('utf-8'))
            
            # Aguarda confirmação do cliente
            cliente_socket.recv(1024)
            
            with self.lock:
                self.clientes_prontos.append(cliente_socket)
                print(f"Jogadores conectados: {len(self.clientes_prontos)}/{self.max_clientes}")
            
            # Aguarda tempo limite ou número mínimo de jogadores
            tempo_inicio = time.time()
            while (len(self.clientes_prontos) < self.max_clientes and 
                   time.time() - tempo_inicio < self.tempo_espera):
                time.sleep(1)
            
            # Inicia o sorteio se houver número suficiente de jogadores
            if len(self.clientes_prontos) >= self.max_clientes:
                print(f"\n--- Início do Sorteio com {len(self.clientes_prontos)} jogadores ---")
                self.jogo_em_andamento = True
                threading.Thread(target=self.iniciar_sorteio).start()
            else:
                print(f"Não há jogadores suficientes para iniciar o jogo. Mínimo: {self.max_clientes}")
                cliente_socket.send('JOGO_CANCELADO'.encode('utf-8'))
            
            # Loop para receber mensagens do cliente
            while self.jogo_em_andamento:
                try:
                    mensagem = cliente_socket.recv(1024).decode('utf-8')
                    if mensagem == 'BINGO':
                        print(f"\n--- BINGO! Cliente {cliente_socket.getpeername()} venceu! ---")
                        self.finalizar_jogo('BINGO_VENCEDOR')
                        break
                except:
                    break
            
        except Exception as e:
            print(f"Erro ao gerenciar cliente: {e}")
            with self.lock:
                if cliente_socket in self.clientes:
                    self.clientes.remove(cliente_socket)
                if cliente_socket in self.clientes_prontos:
                    self.clientes_prontos.remove(cliente_socket)
    
    def aguardar_conexoes(self):
        """
        Aguarda conexões dos clientes
        """
        while True:
            try:
                cliente_socket, endereco = self.servidor.accept()
                print(f"Novo cliente conectado: {endereco}")
                
                with self.lock:
                    self.clientes.append(cliente_socket)
                
                # Inicia thread para gerenciar cada cliente
                threading.Thread(target=self.gerenciar_cliente, 
                               args=(cliente_socket,)).start()
            
            except Exception as e:
                print(f"Erro ao aceitar conexão: {e}")
                time.sleep(1)

def main():
    # Verifica se o IP e porta foram fornecidos como argumentos
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
    max_clientes = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    tempo_espera = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    
    servidor = ServidorBingo(host=host, porta=porta, 
                           max_clientes=max_clientes, 
                           tempo_espera=tempo_espera)
    try:
        servidor.aguardar_conexoes()
    except KeyboardInterrupt:
        print("\nEncerrando o servidor...")
    finally:
        servidor.servidor.close()

if __name__ == "__main__":
    main()