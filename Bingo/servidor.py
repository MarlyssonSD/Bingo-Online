import socket
import threading
import time
import random
import numpy as np

class ServidorBingo:
    def __init__(self, host='localhost', porta=12345, max_clientes=3):
        # Configurações de conexão
        self.host = host
        self.porta = porta
        self.max_clientes = max_clientes
        
        # Socket do servidor
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.bind((self.host, self.porta))
        self.servidor.listen(self.max_clientes)
        
        # Lista de clientes conectados
        self.clientes = []
        self.clientes_prontos = []
        
        # Números já sorteados
        self.numeros_sorteados = []
        
        print(f"Servidor de Bingo iniciado em {self.host}:{self.porta}")
    
    def iniciar_sorteio(self):
        """
        Método para sortear números a cada 3 segundos
        """
        while len(self.numeros_sorteados) < 75:
            # Sorteia um número entre 1 e 75 que ainda não foi sorteado
            numero = random.randint(1, 75)
            while numero in self.numeros_sorteados:
                numero = random.randint(1, 75)
            
            self.numeros_sorteados.append(numero)
            
            # Imprime a lista de números sorteados
            print("\n--- Números Sorteados ---")
            print(self.numeros_sorteados)
            print(f"Total de números sorteados: {len(self.numeros_sorteados)}")
            
            # Envia o número para todos os clientes conectados
            for cliente in self.clientes:
                try:
                    cliente.send(str(numero).encode('utf-8'))
                except:
                    self.clientes.remove(cliente)
            
            # Pausa de 3 segundos entre os sorteios
            time.sleep(3)
        
        # Finaliza o jogo quando todos os números forem sorteados
        for cliente in self.clientes:
            cliente.send('FIM_JOGO'.encode('utf-8'))
    
    def gerenciar_cliente(self, cliente_socket):
        """
        Gerencia a conexão com cada cliente
        """
        try:
            # Envia confirmação de conexão
            cliente_socket.send('CONECTADO'.encode('utf-8'))
            
            # Aguarda confirmação do cliente
            cliente_socket.recv(1024)
            
            self.clientes_prontos.append(cliente_socket)
            
            # Aguarda todos os clientes estiverem prontos
            while len(self.clientes_prontos) < self.max_clientes:
                time.sleep(1)
            
            # Inicia o sorteio quando todos os clientes estiverem conectados
            if len(self.clientes_prontos) == self.max_clientes:
                print("\n--- Início do Sorteio ---")
                threading.Thread(target=self.iniciar_sorteio).start()
        
        except Exception as e:
            print(f"Erro ao gerenciar cliente: {e}")
            self.clientes.remove(cliente_socket)
    
    def aguardar_conexoes(self):
        """
        Aguarda conexões dos clientes
        """
        while len(self.clientes) < self.max_clientes:
            cliente_socket, endereco = self.servidor.accept()
            print(f"Novo cliente conectado: {endereco}")
            
            self.clientes.append(cliente_socket)
            
            # Inicia thread para gerenciar cada cliente
            threading.Thread(target=self.gerenciar_cliente, args=(cliente_socket,)).start()
        
        print("Número máximo de clientes conectados!")

def main():
    servidor = ServidorBingo()
    servidor.aguardar_conexoes()

if __name__ == "__main__":
    main()