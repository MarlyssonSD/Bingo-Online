import socket
import threading
import numpy as np
import random
import time
import sys

class CarteldeBingo:
    def __init__(self):
        # Definindo os intervalos para cada coluna
        self.intervalos = {
            'B': (1, 15),
            'I': (16, 30),
            'N': (31, 45),
            'G': (46, 60),
            'O': (61, 75)
        }
        
        # Inicializando a cartela de números
        self.cartela_numeros = np.zeros((5, 5), dtype=int)
        
        # Inicializando a matriz binária de marcação
        self.cartela_marcacao = np.zeros((5, 5), dtype=bool)
        
        # Gerar a cartela
        self.gerar_cartela()
    
    def gerar_cartela(self):
        """
        Gera a cartela de bingo seguindo as regras especificadas
        """
        for coluna, (inicio, fim) in enumerate(self.intervalos.values()):
            # Gerar números únicos para cada coluna
            numeros_coluna = random.sample(range(inicio, fim + 1), 5)
            
            # Preencher a coluna na matriz
            self.cartela_numeros[:, coluna] = numeros_coluna
        
        # Garantir que o centro seja um espaço livre (0)
        self.cartela_numeros[2, 2] = 0
        self.cartela_marcacao[2, 2] = True  # Centro sempre marcado
    
    def marcar_numero(self, numero):
        """
        Marca um número na cartela se ele existir
        
        :param numero: Número a ser marcado
        :return: True se o número foi marcado, False caso contrário
        """
        for linha in range(5):
            for coluna in range(5):
                if self.cartela_numeros[linha, coluna] == numero:
                    self.cartela_marcacao[linha, coluna] = True
                    return True
        return False
    
    def verificar_bingo(self):
        """
        Verifica se a cartela tem bingo
        
        :return: True se há bingo, False caso contrário
        """
        # Verificar linhas
        if np.any(np.all(self.cartela_marcacao, axis=1)):
            return True
        
        # Verificar colunas
        if np.any(np.all(self.cartela_marcacao, axis=0)):
            return True
        
        # Verificar diagonais
        diagonal_principal = np.all(np.diag(self.cartela_marcacao))
        diagonal_secundaria = np.all(np.diag(np.fliplr(self.cartela_marcacao)))
        
        return diagonal_principal or diagonal_secundaria
    
    def imprimir_cartela(self):
        """
        Imprime a cartela de números e a matriz de marcação
        """
        print("\nCartela de Números:")
        print(self.cartela_numeros)
        print("\nCartela de Marcação:")
        print(self.cartela_marcacao)

class ClienteBingo:
    def __init__(self, host='localhost', porta=12345, max_tentativas=3):
        # Configurações de conexão
        self.host = host
        self.porta = porta
        self.max_tentativas = max_tentativas
        
        # Criar cartela do jogador
        self.cartela = CarteldeBingo()
        
        # Criar socket do cliente
        self.cliente = None
        
        # Lista de números sorteados
        self.numeros_sorteados = []
        
        # Flag para controle de thread
        self.rodando = False
        
        # Flag para controle de bingo
        self.bingo_feito = False
    
    def conectar(self):
        """
        Conecta ao servidor de Bingo com tentativas de reconexão
        """
        tentativas = 0
        while tentativas < self.max_tentativas:
            try:
                self.cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.cliente.connect((self.host, self.porta))
                
                # Recebe confirmação de conexão
                resposta = self.cliente.recv(1024).decode('utf-8')
                if resposta == 'CONECTADO':
                    print("Conectado ao servidor!")
                    
                    # Imprime a cartela do jogador
                    self.cartela.imprimir_cartela()
                    
                    # Confirma prontidão
                    self.cliente.send('PRONTO'.encode('utf-8'))
                    
                    # Inicia thread para receber números
                    self.rodando = True
                    threading.Thread(target=self.receber_numeros).start()
                    return True
                
            except Exception as e:
                print(f"Tentativa {tentativas + 1} falhou: {e}")
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
                
                if dados == 'FIM_JOGO':
                    print("\n--- Jogo Encerrado ---")
                    print("Números sorteados:", self.numeros_sorteados)
                    break
                
                if dados == 'BINGO_VENCEDOR':
                    print("\n--- Alguém fez BINGO! Jogo encerrado! ---")
                    print("Números sorteados:", self.numeros_sorteados)
                    break
                
                if dados == 'JOGO_CANCELADO':
                    print("\n--- Jogo Cancelado - Não há jogadores suficientes ---")
                    break
                
                try:
                    numero = int(dados)
                except ValueError:
                    print(f"Mensagem inválida recebida: {dados}")
                    continue
                
                # Adiciona o número à lista local de sorteados
                self.numeros_sorteados.append(numero)
                
                # Imprime o número sorteado
                print(f"\n--- Número Sorteado: {numero} ---")
                print("Números sorteados até agora:", self.numeros_sorteados)
                
                # Tenta marcar o número na cartela
                if self.cartela.marcar_numero(numero):
                    print(f"Número {numero} marcado na sua cartela!")
                    
                    # Verifica se tem Bingo
                    if self.cartela.verificar_bingo() and not self.bingo_feito:
                        print("\n--- BINGO! Você ganhou! ---")
                        self.bingo_feito = True
                        try:
                            self.cliente.send('BINGO'.encode('utf-8'))
                        except:
                            print("Não foi possível enviar mensagem de BINGO")
                        break
                
                # Mostra a cartela atualizada
                self.cartela.imprimir_cartela()
            
            except Exception as e:
                print(f"Erro ao receber números: {e}")
                break
        
        self.rodando = False
        self.fechar_conexao()
    
    def fechar_conexao(self):
        """
        Fecha a conexão com o servidor
        """
        self.rodando = False
        if self.cliente:
            try:
                self.cliente.close()
            except:
                pass
            self.cliente = None

def main():
    # Verifica se o IP do servidor foi fornecido como argumento
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345
    
    cliente = ClienteBingo(host=host, porta=porta)
    try:
        if cliente.conectar():
            # Aguarda o usuário pressionar Ctrl+C para sair
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando o cliente...")
    finally:
        cliente.fechar_conexao()

if __name__ == "__main__":
    main()