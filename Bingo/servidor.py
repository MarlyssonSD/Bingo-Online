import socket
import threading
import time
import random
import sys

class PartidaBingo:
    """
    Classe responsável por gerenciar uma partida de bingo.
    """
    def __init__(self, clientes, min_clientes, max_clientes, tempo_espera):
        self.clientes = clientes  # Lista de clientes conectados à partida
        self.min_clientes = min_clientes  # Número mínimo de jogadores para iniciar
        self.max_clientes = max_clientes  # Número máximo de jogadores permitidos
        self.tempo_espera = tempo_espera  # Tempo de espera antes do sorteio começar
        self.numeros_sorteados = []  # Lista de números sorteados
        self.jogo_em_andamento = False  # Estado do jogo
        self.sorteio_iniciado = False  # Indica se o sorteio começou
        self.nomes_jogadores = {}  # Dicionário para armazenar nomes dos jogadores
        self.lock = threading.Lock()  # Lock para sincronização de threads

    def iniciar_partida(self):
        """
        Inicia a partida após um tempo de espera.
        """
        print(f"\nPartida iniciada com {len(self.clientes)} jogadores.")
        print(f"Esperando {self.tempo_espera} segundos até iniciar o sorteio...")
        time.sleep(self.tempo_espera)  # Aguarda o tempo definido antes de iniciar
        print("\nIniciando sorteio...")
        self.jogo_em_andamento = True
        threading.Thread(target=self.iniciar_sorteio).start()

    def iniciar_sorteio(self):
        """
        Sorteia números aleatoriamente de 1 a 75 e os envia para os jogadores.
        """
        numeros_disponiveis = list(range(1, 76))
        random.shuffle(numeros_disponiveis)
        
        while self.jogo_em_andamento and len(self.numeros_sorteados) < 75:
            numero = numeros_disponiveis.pop()
            self.numeros_sorteados.append(numero)
            
            print(f"\n--- Número Sorteado: {numero} ---")
            print(f"Todos Números Sorteados: {self.numeros_sorteados}")
            self.enviar_numero(numero)
            time.sleep(3)  # Intervalo entre sorteios
        
        self.finalizar_partida()

    def enviar_numero(self, numero):
        """
        Envia o número sorteado para todos os clientes conectados.
        """
        with self.lock:
            clientes_remover = []
            for cliente in self.clientes[:]:
                try:
                    cliente.send(str(numero).encode('utf-8'))
                except (socket.error, ConnectionError):
                    clientes_remover.append(cliente)
            
            for cliente in clientes_remover:
                self.remover_cliente(cliente)

    def remover_cliente(self, cliente_socket):
        """
        Remove um cliente da lista caso perca a conexão ou saia da partida.
        """
        with self.lock:
            try:
                self.clientes.remove(cliente_socket)
                if cliente_socket in self.nomes_jogadores:
                    del self.nomes_jogadores[cliente_socket]
                cliente_socket.shutdown(socket.SHUT_RDWR)
                cliente_socket.close()
            except:
                pass
            
            if len(self.clientes) < self.min_clientes:
                print("Número insuficiente de jogadores. Finalizando a partida.")
                self.finalizar_partida()

    def finalizar_partida(self):
        """
        Finaliza a partida e notifica os jogadores.
        """
        self.jogo_em_andamento = False
        print("\nPartida finalizada. Enviando notificação de fim de jogo...")
        for cliente in self.clientes:
            try:
                cliente.send("JOGO_FINALIZADO".encode('utf-8'))
                cliente.shutdown(socket.SHUT_RDWR)
                cliente.close()
            except:
                pass
        print("Todos os clientes desconectados e partida encerrada.")

class ServidorBingo:
    """
    Classe responsável por gerenciar conexões e partidas de bingo.
    """
    def __init__(self, host='0.0.0.0', porta=12345, min_clientes=2, max_clientes=10, tempo_espera=30):
        self.host = host
        self.porta = porta
        self.min_clientes = min_clientes
        self.max_clientes = max_clientes
        self.tempo_espera = tempo_espera
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.bind((self.host, self.porta))
        self.servidor.listen(self.max_clientes)
        self.clientes = []
        self.lock = threading.Lock()
        print(f"Servidor de Bingo iniciado em {self.host}:{self.porta}")

    def aguardar_conexoes(self):
        """
        Aguarda conexões de jogadores e inicia partidas quando possível.
        """
        while True:
            try:
                cliente_socket, endereco = self.servidor.accept()
                with self.lock:
                    if len(self.clientes) >= self.max_clientes:
                        cliente_socket.send("LIMITE_DE_JOGADORES".encode('utf-8'))
                        cliente_socket.close()
                        continue

                    cliente_socket.send("CONECTADO".encode('utf-8'))
                    nome_jogador = cliente_socket.recv(1024).decode('utf-8')
                    self.clientes.append(cliente_socket)
                    print(f"Jogador '{nome_jogador}' conectado: {endereco}. Total de jogadores: {len(self.clientes)}")

                    if len(self.clientes) >= self.min_clientes:
                        print(f"Temos {len(self.clientes)} jogadores. Iniciando nova partida...")
                        threading.Thread(target=self.iniciar_partida, args=(self.clientes,)).start()
            except Exception as e:
                print(f"Erro ao aceitar conexão: {e}")

    def iniciar_partida(self, clientes):
        """
        Cria uma nova instância de PartidaBingo e inicia o jogo.
        """
        partida = PartidaBingo(clientes, self.min_clientes, self.max_clientes, self.tempo_espera)
        partida.iniciar_partida()

# Função principal para iniciar o servidor

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
    min_clientes = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    max_clientes = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    tempo_espera = int(sys.argv[5]) if len(sys.argv) > 5 else 30

    servidor = ServidorBingo(host=host, porta=porta, min_clientes=min_clientes, max_clientes=max_clientes, tempo_espera=tempo_espera)
    servidor.aguardar_conexoes()

if __name__ == "__main__":
    main()