import socket
import threading
import time
import random
import sys
from partida import PartidaBingo

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
        self.servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reutilizar o endereço
        self.servidor.bind((self.host, self.porta))
        self.servidor.listen(100)  # Aumentado para permitir mais conexões
        
        # Dicionário de partidas ativas (código_partida -> objeto PartidaBingo)
        self.partidas = {}
        
        # Lista de partidas públicas disponíveis
        self.partidas_publicas = []
        
        # Locks para sincronização
        self.lock_partidas = threading.Lock()
        
        # Flag de controle
        self.aceitando_conexoes = True
        
        print(f"Servidor de Bingo iniciado em {self.host}:{self.porta}")
        print(f"Configuração: min_jogadores={self.min_clientes}, max_jogadores={self.max_clientes}, tempo_espera={self.tempo_espera}s")
    
    def remover_partida(self, codigo_partida, motivo=None):
        """
        Remove uma partida do dicionário de partidas ativas
        
        :param codigo_partida: Código da partida a ser removida
        :param motivo: Motivo da remoção, para registro
        :return: True se a partida foi removida, False caso contrário
        """
        with self.lock_partidas:
            if codigo_partida in self.partidas:
                partida = self.partidas[codigo_partida]
                
                # Remove da lista de partidas públicas se estiver lá
                if codigo_partida in self.partidas_publicas:
                    self.partidas_publicas.remove(codigo_partida)
                    
                if motivo:
                    print(f"\nRemovendo partida {codigo_partida}: {motivo}")
                else:
                    print(f"\nRemovendo partida {codigo_partida}")
                del self.partidas[codigo_partida]
                return True
            return False
    
    def listar_partidas_publicas(self):
        """
        Retorna uma lista de códigos de partidas públicas disponíveis
        """
        with self.lock_partidas:
            partidas_disponiveis = []
            for codigo in self.partidas_publicas:
                if codigo in self.partidas and not self.partidas[codigo].jogo_em_andamento:
                    partidas_disponiveis.append(codigo)
            return partidas_disponiveis
    
    def criar_ou_obter_partida(self, codigo_partida, publica=True):
        """
        Cria uma nova partida ou retorna uma existente com o código fornecido
        
        :param codigo_partida: Código da partida a ser criada ou obtida
        :param publica: Booleano indicando se a partida é pública (True) ou privada (False)
        :return: Tupla com código da partida e objeto PartidaBingo
        """
        with self.lock_partidas:
            # Processa strings específicas de comando
            info_partida = codigo_partida.split(':')
            
            # Verifica se há informação sobre o tipo de partida (formato: NOVOPARTIDA:0 ou NOVOPARTIDA:1)
            if len(info_partida) > 1 and info_partida[0].lower() == "novopartida":
                try:
                    publica = int(info_partida[1]) == 0  # 0 = pública, 1 = privada
                except:
                    publica = True  # padrão é público se houver erro
                
                codigo_partida = info_partida[0]  # Mantém apenas o comando base
            
            # Se o código é para criar uma nova partida
            if codigo_partida.lower() == "novopartida":
                # Gera um código aleatório único
                while True:
                    novo_codigo = f"partida_{random.randint(1000, 9999)}"
                    if novo_codigo not in self.partidas:
                        break
                
                codigo_partida = novo_codigo
                
                # Cria uma nova partida com a flag publica
                print(f"\nCriando nova partida com código: {codigo_partida}, Status: {'Pública' if publica else 'Privada'}")
                partida = PartidaBingo(codigo_partida, 
                                      self.min_clientes, 
                                      self.max_clientes, 
                                      self.tempo_espera,
                                      publica)
                                      
                self.partidas[codigo_partida] = partida
                
                # Adiciona à lista de partidas públicas se for pública
                if publica:
                    self.partidas_publicas.append(codigo_partida)
                    print(f"Partida {codigo_partida} adicionada à lista de partidas públicas")
                
                return codigo_partida, partida
            
            # Verifica se a partida já existe
            if codigo_partida not in self.partidas:
                # Cria uma nova partida com código específico e flag pública
                print(f"\nCriando nova partida com código específico: {codigo_partida}, Status: {'Pública' if publica else 'Privada'}")
                partida = PartidaBingo(codigo_partida, 
                                      self.min_clientes, 
                                      self.max_clientes, 
                                      self.tempo_espera,
                                      publica)
                                      
                self.partidas[codigo_partida] = partida
                
                # Adiciona à lista de partidas públicas se for pública
                if publica:
                    self.partidas_publicas.append(codigo_partida)
                    print(f"Partida {codigo_partida} adicionada à lista de partidas públicas")
                
                return codigo_partida, partida
            
            return codigo_partida, self.partidas[codigo_partida]
    
    def gerenciar_cliente(self, cliente_socket, endereco):
        """
        Gerencia a conexão com cada cliente
        """
        codigo_partida = None
        partida = None
        
        try:
            # Envia confirmação de conexão
            cliente_socket.send('CONECTADO'.encode('utf-8'))
            
            # Recebe o nome do jogador
            nome_jogador = cliente_socket.recv(1024).decode('utf-8')
            if not nome_jogador:
                print(f"Cliente {endereco} desconectou sem informar nome")
                cliente_socket.close()
                return
            
            # Verifica se o cliente solicitou a lista de partidas públicas
            if nome_jogador == "LISTAR_PARTIDAS":
                partidas_disponiveis = self.listar_partidas_publicas()
                resposta = "PARTIDAS_PUBLICAS:" + ",".join(partidas_disponiveis)
                cliente_socket.send(resposta.encode('utf-8'))
                # Espera para ver se o cliente vai se conectar com uma partida específica
                try:
                    nome_jogador = cliente_socket.recv(1024).decode('utf-8')
                    if not nome_jogador or nome_jogador == "SAIR":
                        cliente_socket.close()
                        return
                except:
                    cliente_socket.close()
                    return
            
            # Recebe o código da partida e informação sobre pública/privada
            codigo_partida_info = cliente_socket.recv(1024).decode('utf-8')
            if not codigo_partida_info:
                print(f"Cliente {endereco} desconectou sem informar código da partida")
                cliente_socket.close()
                return
            
            # Parse da informação da partida
            info_partida = codigo_partida_info.split(':')
            publica = True  # padrão é público
            
            if len(info_partida) > 1:
                try:
                    publica = int(info_partida[1]) == 0  # 0 = pública, 1 = privada
                except:
                    publica = True  # padrão é público se houver erro
                
                codigo_partida_recebido = info_partida[0]
            else:
                codigo_partida_recebido = codigo_partida_info
            
            # Cria ou obtém a partida solicitada
            codigo_partida, partida = self.criar_ou_obter_partida(codigo_partida_recebido, publica)
            
            # Envia o código real da partida para o cliente
            try:
                cliente_socket.send(codigo_partida.encode('utf-8'))
                time.sleep(0.5)
            except:
                print(f"Erro ao enviar código da partida para o cliente {nome_jogador}")
                cliente_socket.close()
                return
            
            # Resto do código permanece o mesmo
            # ...
            
            # A parte restante do método permanece inalterada
            # Adiciona o cliente à partida
            resultado = partida.adicionar_cliente(cliente_socket, nome_jogador)
            
            # Se o jogo já estiver em andamento, notifica o cliente e fecha a conexão
            if resultado == "jogo_em_andamento":
                try:
                    cliente_socket.send("jogo_em_andamento".encode('utf-8'))
                    time.sleep(0.5)
                except:
                    pass
                cliente_socket.close()
                return
            
            # Envia confirmação de que o jogador pode entrar na partida
            try:
                cliente_socket.send("pode_entrar".encode('utf-8'))
                time.sleep(0.5)
            except:
                print(f"Erro ao enviar confirmação para o cliente {nome_jogador}")
                partida.remover_cliente(cliente_socket)
                return
            
            # Aguarda confirmação "PRONTO" do cliente
            try:
                confirmacao = cliente_socket.recv(1024).decode('utf-8')
                if confirmacao != 'PRONTO':
                    print(f"Cliente {nome_jogador} enviou confirmação inválida: {confirmacao}")
            except:
                print(f"Erro ao receber confirmação do cliente {nome_jogador}")
                partida.remover_cliente(cliente_socket)
                return
            
            # Inicia o temporizador se atingiu o mínimo de jogadores
            if resultado == "iniciar_temporizador":
                threading.Thread(target=self.iniciar_temporizador, args=(partida,)).start()
            
            # Inicia o jogo se atingiu o número máximo de jogadores
            elif resultado is True:
                partida.iniciar_jogo()
            
            # Loop para receber mensagens do cliente durante o jogo
            while not partida.partida_encerrada:
                try:
                    mensagem = cliente_socket.recv(1024).decode('utf-8')
                    if not mensagem:  # Cliente desconectou
                        resultado = partida.remover_cliente(cliente_socket)
                        if resultado == "partida_cancelada":
                            self.remover_partida(codigo_partida, "Cancelada: jogadores insuficientes")
                        break
                    
                    if mensagem == 'BINGO':
                        print(f"\nCliente {nome_jogador} informou BINGO!")
                        if partida.verificar_bingo(cliente_socket):
                            # Remover a partida do dicionário quando terminar
                            self.remover_partida(codigo_partida, "Finalizada: jogador fez bingo")
                            break
                except Exception as e:
                    print(f"Erro ao receber mensagem do cliente {nome_jogador}: {e}")
                    if not partida.partida_encerrada:
                        resultado = partida.remover_cliente(cliente_socket)
                        if resultado == "partida_cancelada":
                            self.remover_partida(codigo_partida, "Cancelada após erro de comunicação")
                    break
            
            # Verifica se a partida terminou e deve ser removida
            if codigo_partida and partida and partida.partida_encerrada:
                self.remover_partida(codigo_partida, "Partida encerrada")

        except Exception as e:
            print(f"Erro ao gerenciar cliente {endereco}: {e}")
            # Se tiver uma partida associada, tenta remover o cliente
            if partida and cliente_socket:
                resultado = partida.remover_cliente(cliente_socket)
                if resultado == "partida_cancelada" and codigo_partida:
                    self.remover_partida(codigo_partida, "Cancelada após erro no gerenciamento")
            # Garante que o socket é fechado
            try:
                cliente_socket.close()
            except:
                pass
    
    def aguardar_conexoes(self):
        """
        Aguarda conexões dos clientes
        """
        print("\nAguardando conexões de clientes...")
        
        while self.aceitando_conexoes:
            try:
                cliente_socket, endereco = self.servidor.accept()
                print(f"\nNova conexão de: {endereco}")
                
                # Inicia thread para gerenciar cada cliente
                threading.Thread(target=self.gerenciar_cliente, 
                               args=(cliente_socket, endereco)).start()
            
            except Exception as e:
                if self.aceitando_conexoes:
                    print(f"Erro ao aceitar conexão: {e}")
                    time.sleep(1)
    
    def iniciar_temporizador(self, partida):
        """
        Inicia o temporizador para a partida e depois inicia o jogo
        """
        codigo_partida = partida.codigo_partida
        tempo_restante = partida.tempo_espera
        
        while tempo_restante > 0 and not partida.sorteio_iniciado:
            if tempo_restante % 5 == 0 or tempo_restante <= 3:  # Mostra a cada 5 segundos e nos últimos 3
                print(f"\nPartida {codigo_partida}: Aguardando mais jogadores... {tempo_restante}s restantes")
            
            time.sleep(1)
            tempo_restante -= 1
            
            # Verifica se já atingiu o máximo de jogadores durante a espera
            if len(partida.clientes_prontos) >= partida.max_clientes:
                print(f"\nPartida {codigo_partida}: Número máximo de jogadores atingido durante a espera")
                break
            
            # Verifica se ainda tem jogadores suficientes
            if len(partida.clientes_prontos) < partida.min_clientes:
                print(f"\nPartida {codigo_partida}: Jogadores insuficientes durante a espera, reiniciando temporizador")
                return  # Sai sem iniciar o jogo
        
        # Inicia o jogo se não foi iniciado ainda e tem jogadores suficientes
        if not partida.sorteio_iniciado and len(partida.clientes_prontos) >= partida.min_clientes:
            print(f"\nPartida {codigo_partida}: Temporizador concluído. Iniciando jogo com {len(partida.clientes_prontos)} jogadores")
            partida.iniciar_jogo()
        elif not partida.sorteio_iniciado:
            print(f"\nPartida {codigo_partida}: Não há jogadores suficientes após o temporizador. Cancelando partida.")
            partida.finalizar_jogo('JOGO_CANCELADO')
            # Remove a partida do dicionário
            self.remover_partida(codigo_partida, "Cancelada: jogadores insuficientes após temporizador")

    def encerrar_servidor(self):
        """
        Encerra o servidor e todas as partidas ativas
        """
        print("\nEncerrando o servidor...")
        self.aceitando_conexoes = False
        
        # Finaliza todas as partidas ativas
        with self.lock_partidas:
            for codigo, partida in list(self.partidas.items()):
                try:
                    partida.finalizar_jogo('SERVIDOR_ENCERRADO')
                except Exception as e:
                    print(f"Erro ao finalizar partida {codigo}: {e}")
            self.partidas.clear()
        
        # Fecha o socket do servidor
        try:
            self.servidor.close()
        except Exception as e:
            print(f"Erro ao fechar socket do servidor: {e}")

def main():
    # Verifica se o IP e porta foram fornecidos como argumentos
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
    min_clientes = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    max_clientes = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    tempo_espera = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    
    servidor = ServidorBingo(host=host, porta=porta, 
                           min_clientes=min_clientes,
                           max_clientes=max_clientes, 
                           tempo_espera=tempo_espera)
    try:
        servidor.aguardar_conexoes()
    except KeyboardInterrupt:
        print("\nEncerrando o servidor por interrupção do teclado...")
    finally:
        servidor.encerrar_servidor()

if __name__ == "__main__":
    main()