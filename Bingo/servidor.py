import socket
import threading
import time
import random
import sys

class ServidorBingo:
    def __init__(self, host='0.0.0.0', porta=12345, min_clientes=2, max_clientes=10, tempo_espera=30):
        # Configurações de conexão
        self.host = host
        self.porta = porta
        self.min_clientes = min_clientes
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
        
        # Flags de controle
        self.jogo_em_andamento = False
        self.aceitando_conexoes = True
        self.sorteio_iniciado = False
        
        # Lock para sincronização
        self.lock = threading.Lock()
        
        print(f"Servidor de Bingo iniciado em {self.host}:{self.porta}")
        print(f"Número mínimo de jogadores: {self.min_clientes}, máximo de jogadores: {self.max_clientes}")
    
    def gerenciar_cliente(self, cliente_socket, endereco):
        """
        Gerencia a conexão com cada cliente
        """
        try:
            # Se o jogo já começou ou o tempo de espera acabou, recusa a conexão
            if self.jogo_em_andamento or self.sorteio_iniciado:
                cliente_socket.send('JOGO_EM_ANDAMENTO'.encode('utf-8'))
                cliente_socket.close()
                return
            
            # Envia confirmação de conexão
            cliente_socket.send('CONECTADO'.encode('utf-8'))
            
            # Aguarda confirmação do cliente
            cliente_socket.recv(1024)
            
            # Adiciona o cliente à lista de clientes prontos
            with self.lock:
                if cliente_socket not in self.clientes:
                    self.clientes.append(cliente_socket)
                if cliente_socket not in self.clientes_prontos:
                    self.clientes_prontos.append(cliente_socket)
                print(f"\nJogador conectado: {endereco}. Total: {len(self.clientes_prontos)}/{self.max_clientes}")
                
                # Inicia o jogo se atingiu o número máximo de jogadores
                if len(self.clientes_prontos) >= self.max_clientes and not self.sorteio_iniciado:
                    print("\nNúmero máximo de jogadores atingido. Iniciando o jogo...")
                    self.jogo_em_andamento = True
                    self.sorteio_iniciado = True
                    threading.Thread(target=self.iniciar_sorteio).start()
                # Se atingiu 2 jogadores, inicia o tempo de espera
                elif len(self.clientes_prontos) == 2 and not self.sorteio_iniciado:
                    print("\nDois jogadores conectados. Aguardando mais jogadores por 30 segundos...")
                    threading.Thread(target=self.iniciar_temporizador).start()
            
            # Mantém a conexão aberta
            while not self.sorteio_iniciado:
                time.sleep(1)
            
            # Loop para receber mensagens do cliente durante o jogo
            while self.jogo_em_andamento:
                try:
                    mensagem = cliente_socket.recv(1024).decode('utf-8')
                    if not mensagem:  # Cliente desconectou
                        self.remover_cliente(cliente_socket)
                        break
                    if mensagem == 'BINGO':
                        print(f"\n--- BINGO! Cliente {endereco} venceu! ---")
                        self.finalizar_jogo('BINGO_VENCEDOR')
                        break
                except:
                    self.remover_cliente(cliente_socket)
                    break
        
        except Exception as e:
            print(f"Erro ao gerenciar cliente {endereco}: {e}")
            self.remover_cliente(cliente_socket)
    
    def aguardar_conexoes(self):
        """
        Aguarda conexões dos clientes
        """
        while self.aceitando_conexoes:
            try:
                cliente_socket, endereco = self.servidor.accept()
                
                with self.lock:
                    # Verifica se já atingiu o número máximo de jogadores ou se o jogo já começou
                    if len(self.clientes_prontos) >= self.max_clientes or self.jogo_em_andamento:
                        try:
                            cliente_socket.send('JOGO_EM_ANDAMENTO'.encode('utf-8'))
                            cliente_socket.close()
                        except:
                            pass
                        continue
                
                # Inicia thread para gerenciar cada cliente
                threading.Thread(target=self.gerenciar_cliente, 
                               args=(cliente_socket, endereco)).start()
            
            except Exception as e:
                if self.aceitando_conexoes:
                    print(f"Erro ao aceitar conexão: {e}")
                    time.sleep(1)

    def remover_cliente(self, cliente_socket):
        """
        Remove um cliente de todas as listas e fecha sua conexão
        """
        with self.lock:
            try:
                if cliente_socket in self.clientes:
                    self.clientes.remove(cliente_socket)
                if cliente_socket in self.clientes_prontos:
                    self.clientes_prontos.remove(cliente_socket)
                
                try:
                    cliente_socket.shutdown(socket.SHUT_RDWR)  # Adiciona shutdown antes do close
                    cliente_socket.close()
                except:
                    pass
                
                print(f"Cliente removido. Jogadores restantes: {len(self.clientes_prontos)}")
                
                # Se não houver jogadores suficientes durante o jogo, finaliza
                if self.jogo_em_andamento and len(self.clientes_prontos) < self.min_clientes:
                    print("\nNão há jogadores suficientes para continuar. Encerrando jogo...")
                    self.finalizar_jogo('JOGO_CANCELADO')
            except Exception as e:
                print(f"Erro ao remover cliente: {e}")

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
                print("\nTodos os clientes desconectados. Encerrando jogo.")
                self.finalizar_jogo('TODOS_DESCONECTADOS')

    def finalizar_jogo(self, mensagem='FIM_JOGO'):
        """
        Finaliza o jogo e notifica todos os clientes
        """
        self.jogo_em_andamento = False
        self.sorteio_iniciado = False
        
        # Primeiro: Envia a mensagem para todos os clientes
        for cliente in self.clientes[:]:  # Usa uma cópia da lista
            try:
                cliente.send(mensagem.encode('utf-8'))
                time.sleep(0.1)  # Pequena pausa para garantir que a mensagem seja enviada
            except:
                pass
        
        # Segundo: Fecha as conexões
        for cliente in self.clientes[:]:  # Usa uma cópia da lista
            try:
                cliente.shutdown(socket.SHUT_RDWR)
                cliente.close()
            except:
                pass
        
        # Terceiro: Limpa as listas de clientes
        self.clientes.clear()
        self.clientes_prontos.clear()
        
        # Por último: Decide se encerra o servidor ou aguarda novas conexões
        if mensagem in ['JOGO_CANCELADO', 'TODOS_DESCONECTADOS']:
            self.aceitando_conexoes = False
            try:
                self.servidor.close()
            except:
                pass
            print("\nServidor encerrado.")
        else:
            print("\nJogo finalizado. Aguardando novas conexões...")
    
    def iniciar_temporizador(self):
        """
        Inicia o temporizador de 30 segundos e depois inicia o jogo
        """
        time.sleep(self.tempo_espera)  # Aguarda tempo de espera configurado
        
        with self.lock:
            if not self.sorteio_iniciado:
                if len(self.clientes_prontos) >= 2:  # Verifica se ainda tem pelo menos 2 jogadores
                    print(f"\n--- Início do Sorteio com {len(self.clientes_prontos)} jogadores ---")
                    self.jogo_em_andamento = True
                    self.sorteio_iniciado = True
                    threading.Thread(target=self.iniciar_sorteio).start()
                else:
                    print("\nNão há jogadores suficientes. Cancelando jogo...")
                    self.finalizar_jogo('JOGO_CANCELADO')

    def iniciar_sorteio(self):
        """
        Método para sortear números a cada 5 segundos
        """
        # Cria uma lista de números de 1 a 75 e embaralha
        numeros_disponiveis = list(range(1, 76))
        random.shuffle(numeros_disponiveis)
        
        while self.jogo_em_andamento and len(self.numeros_sorteados) < 75:
            # Pega o próximo número da lista embaralhada
            numero = numeros_disponiveis.pop()
            self.numeros_sorteados.append(numero)
            
            # Imprime a lista de números sorteados
            print(f"\n--- Número Sorteados ---")
            print(self.numeros_sorteados)
            print(f"Total de números sorteados: {len(self.numeros_sorteados)}")
            
            # Envia o número para todos os clientes
            self.enviar_numero(numero)
            
            # Verifica se ainda há clientes conectados
            if not self.clientes:
                print("Todos os clientes desconectados. Encerrando jogo.")
                self.finalizar_jogo()
                break
            
            # Pausa entre os sorteios
            time.sleep(3)
        
        # Finaliza o jogo se não foi finalizado por bingo
        if self.jogo_em_andamento:
            self.finalizar_jogo()

def main():
    # Verifica se o IP e porta foram fornecidos como argumentos
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
    min_clientes = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    max_clientes = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    tempo_espera = int(sys.argv[5]) if len(sys.argv) > 5 else 30
    
    servidor = ServidorBingo(host=host, porta=porta, 
                           min_clientes=min_clientes,
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