import socket
import threading
import time
import sys
from cartela import GerenciadorCartelas

class ClienteBingo:
    def __init__(self, host='localhost', porta=12345, max_tentativas=3):
        # Configurações de conexão
        self.host = host
        self.porta = porta
        self.max_tentativas = max_tentativas
        
        # Criar socket do cliente
        self.cliente = None
        
        # Flag para controle de thread
        self.rodando = False
        
        # Código da partida
        self.codigo_partida = None
        
        # Gerenciador de cartelas
        self.gerenciador_cartelas = GerenciadorCartelas()
    
    def menu_interativo(self):
        """
        Menu interativo para o jogador comprar novas cartelas
        """
        while True:
            print("\n--- MENU ---")
            print("1. Comprar nova cartela (Max:3)")
            print("2. Continuar jogando")
            print("3. Sair")
            
            opcao = input("Escolha uma opção: ")
            
            if opcao == '1':
                self.gerenciador_cartelas.adicionar_cartela()
            elif opcao == '2':
                break
            elif opcao == '3':
                self.fechar_conexao()
                sys.exit()
            else:
                print("Opção inválida!")

    def listar_partidas_publicas(self):
        """
        Solicita e exibe a lista de partidas públicas disponíveis
        """
        try:
            socket_temp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_temp.connect((self.host, self.porta))
            
            # Recebe a mensagem de conexão bem-sucedida
            resposta = socket_temp.recv(1024).decode('utf-8')
            if resposta != 'CONECTADO':
                print("Erro ao conectar ao servidor para listar partidas")
                socket_temp.close()
                return []
            
            # Envia comando especial para listar partidas
            socket_temp.send('LISTAR_PARTIDAS'.encode('utf-8'))
            
            # Recebe a lista de partidas
            resposta = socket_temp.recv(1024).decode('utf-8')
            socket_temp.send('SAIR'.encode('utf-8'))
            socket_temp.close()
            
            if resposta.startswith('PARTIDAS_PUBLICAS:'):
                partidas = resposta.split(':', 1)[1].split(',')
                return [p for p in partidas if p]  # Filtra strings vazias
            
            return []
        except Exception as e:
            print(f"Erro ao listar partidas públicas: {e}")
            return []
    
    def conectar(self, codigo_partida=None):
        tentativas = 0
        while tentativas < self.max_tentativas:
            try:
                self.cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.cliente.connect((self.host, self.porta))
                
                resposta = self.cliente.recv(1024).decode('utf-8')
                if resposta == 'CONECTADO':
                    print("Conectado ao servidor!")
                    
                    self.nome_jogador = input("Digite seu nome: ")
                    self.cliente.send(self.nome_jogador.encode('utf-8'))
                    
                    if codigo_partida is None:
                        print("\nVocê pode entrar em uma partida existente ou criar uma nova.")
                        print("1. Criar nova partida pública")
                        print("2. Criar nova partida privada")
                        print("3. Entrar em uma partida existente")
                        print("4. Listar partidas públicas disponíveis")
                        
                        opcao = input("Escolha uma opção: ")
                        
                        if opcao == '1':
                            codigo_partida = "NOVOPARTIDA:0"  # 0 = pública
                        elif opcao == '2':
                            codigo_partida = "NOVOPARTIDA:1"  # 1 = privada
                        elif opcao == '3':
                            codigo_partida = input("Digite o código da partida: ")
                        elif opcao == '4':
                            partidas = self.listar_partidas_publicas()
                            if partidas:
                                print("\nPartidas públicas disponíveis:")
                                for i, partida in enumerate(partidas, 1):
                                    print(f"{i}. {partida}")
                                
                                try:
                                    indice = int(input("\nDigite o número da partida para entrar (0 para cancelar): "))
                                    if 1 <= indice <= len(partidas):
                                        codigo_partida = partidas[indice-1]
                                    else:
                                        print("Operação cancelada. Tentando nova conexão...")
                                        self.cliente.close()
                                        continue
                                except:
                                    print("Opção inválida. Tentando nova conexão...")
                                    self.cliente.close()
                                    continue
                            else:
                                print("Não há partidas públicas disponíveis. Criando uma nova partida pública.")
                                codigo_partida = "NOVOPARTIDA:0"
                        else:
                            print("Opção inválida. Criando uma nova partida pública.")
                            codigo_partida = "NOVOPARTIDA:0"
                    
                    self.cliente.send(codigo_partida.encode('utf-8'))
                    
                    # Recebe o código real da partida do servidor
                    self.codigo_partida = self.cliente.recv(1024).decode('utf-8')
                    print(f"Você está na partida com código: {self.codigo_partida}")
                    
                    # Recebe a resposta do servidor sobre a entrada na partida
                    resposta_partida = self.cliente.recv(1024).decode('utf-8')
                    if resposta_partida == "jogo_em_andamento":
                        print("\n--- ATENÇÃO ---")
                        print("Esta partida já está em andamento e não é possível entrar agora.")
                        print("Por favor, tente entrar em outra partida ou crie uma nova.")
                        self.fechar_conexao()
                        return False
                    
                    self.gerenciador_cartelas.imprimir_todas_cartelas()
                    self.menu_interativo()
                    
                    self.cliente.send('PRONTO'.encode('utf-8'))
                    
                    self.rodando = True
                    threading.Thread(target=self.receber_numeros).start()
                    return True
                else:
                    print(f"Resposta inesperada do servidor: {resposta}")
            except Exception as e:
                print(f"Tentativa {tentativas + 1} falhou: {e}")
                
            # Tratamento comum de falha (tanto para resposta inesperada quanto para exceção)
            tentativas += 1
            if tentativas < self.max_tentativas:
                print("Tentando reconectar em 5 segundos...")
                time.sleep(5)
            self.fechar_conexao()
        
        print("Não foi possível conectar ao servidor após várias tentativas.")
        return False

    def receber_numeros(self):
        """
        Recebe números sorteados do servidor
        """
        while self.rodando:
            try:
                if not self.cliente:
                    break
                    
                dados = self.cliente.recv(1024).decode('utf-8')
                if not dados:
                    print("Conexão perdida com o servidor")
                    break
                
                if dados.startswith('BINGO_VENCEDOR:'):
                    vencedor = dados.split(':')[1]
                    print("\n--- RESULTADO FINAL ---")
                    print("Números sorteados:", self.gerenciador_cartelas.get_numeros_sorteados())
                    if vencedor == self.nome_jogador:
                        print(f"\n--- BINGO! Você venceu com a cartela {self.gerenciador_cartelas.verificar_bingo_em_todas_cartelas()}! ---")
                        print("Parabéns! Você foi o primeiro a completar sua cartela!")
                    else:
                        print(f"\n--- BINGO! O jogador {vencedor} venceu a partida! ---")
                        print("Infelizmente você não foi o primeiro a completar sua cartela.")
                    self.rodando = False
                    break
                
                if dados.startswith('JOGO_CANCELADO:'):
                    motivo = dados.split(':', 1)[1]
                    print("\n--- JOGO CANCELADO ---")
                    print("Motivo:", motivo)
                    print("Números sorteados:", self.gerenciador_cartelas.get_numeros_sorteados())
                    self.rodando = False
                    break
                
                if dados == 'FIM_JOGO' or dados == 'SERVIDOR_ENCERRADO':
                    print("\n--- Jogo Encerrado ---")
                    print("Números sorteados:", self.gerenciador_cartelas.get_numeros_sorteados())
                    self.rodando = False
                    break
                
                try:
                    # Tenta interpretar como um número
                    numero = int(dados)
                    self.gerenciador_cartelas.adicionar_numero_sorteado(numero)
                    
                    print(f"\n--- Número sorteado: {numero} ---")
                    print(f"Números já sorteados: {self.gerenciador_cartelas.get_numeros_sorteados()}")
                    
                    # Marca nas cartelas
                    if self.gerenciador_cartelas.marcar_numero_em_todas_cartelas(numero):
                        print("Número marcado em pelo menos uma cartela!")
                        
                        # Imprime cartelas atualizadas
                        self.gerenciador_cartelas.imprimir_todas_cartelas()
                        
                        # Verifica bingo
                        cartela_vencedora = self.gerenciador_cartelas.verificar_bingo_em_todas_cartelas()
                        if cartela_vencedora is not None and not self.gerenciador_cartelas.bingo_feito:
                            print(f"\n--- BINGO! Você venceu com a cartela {cartela_vencedora}! ---")
                            self.gerenciador_cartelas.bingo_feito = True
                            # Envia notificação ao servidor
                            try:
                                self.cliente.send('BINGO'.encode('utf-8'))
                            except:
                                print("Erro ao enviar notificação de bingo")

                except ValueError:
                    print(f"Mensagem não reconhecida: {dados}")
                    
            except Exception as e:
                print(f"Erro ao receber dados: {e}")
                self.rodando = False
                break
        
        print("\nDesconectado do servidor.")
        self.fechar_conexao()
    
    def fechar_conexao(self):
        """
        Fecha a conexão com o servidor
        """
        self.rodando = False
        if self.cliente:
            try:
                self.cliente.shutdown(socket.SHUT_RDWR)
                self.cliente.close()
            except:
                pass
            self.cliente = None

def main():
    # Verifica se o IP e porta foram fornecidos como argumentos
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
    
    print(f"Conectando ao servidor {host}:{porta}...")
    
    cliente = ClienteBingo(host=host, porta=porta)
    
    # Tenta conectar e participar da partida
    if cliente.conectar():
        print("Esperando o início da partida...")
        
        # Aguarda o término da partida
        while cliente.rodando:
            time.sleep(1)
    
    # Garante que a conexão seja fechada ao sair
    cliente.fechar_conexao()
    print("Jogo finalizado. Até a próxima!")

if __name__ == "__main__":
    main()