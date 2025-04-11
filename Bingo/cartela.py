import random
import numpy as np

class CartelaBingo:
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
        # Cria uma cópia para não modificar a original
        verificacao = self.cartela_marcacao.copy()
        
        # Ignora o centro (já que ele começa marcado)
        verificacao[2, 2] = True
        
        # Retorna True apenas se TODAS as posições forem True
        return np.all(verificacao)
    
    def imprimir_cartela(self):
        """
        Imprime a cartela de números e a matriz de marcação
        """
        print("\nCartela de Números:")
        print(self.cartela_numeros)
        print("\nCartela de Marcação:")
        print(self.cartela_marcacao)

class GerenciadorCartelas:
    def __init__(self):
        # Lista de cartelas do jogador (inicialmente uma)
        self.cartelas = [CartelaBingo()]
        
        # Flag para controle de bingo
        self.bingo_feito = False
        
        # Lista de números sorteados
        self.numeros_sorteados = []
    
    def adicionar_cartela(self):
        """
        Adiciona uma nova cartela ao jogador, se ele ainda não tiver 3
        """
        if len(self.cartelas) < 3:
            nova_cartela = CartelaBingo()
            self.cartelas.append(nova_cartela)
            print("\n--- Nova cartela adicionada! ---")
            nova_cartela.imprimir_cartela()
            return True
        else:
            print("\n--- Você já tem o número máximo de cartelas (3)! ---")
            return False
    
    def marcar_numero_em_todas_cartelas(self, numero):
        """
        Marca um número em todas as cartelas do jogador
        
        :param numero: Número a ser marcado
        :return: True se o número foi marcado em pelo menos uma cartela, False caso contrário
        """
        marcado = False
        for cartela in self.cartelas:
            if cartela.marcar_numero(numero):
                marcado = True
        return marcado
    
    def verificar_bingo_em_todas_cartelas(self):
        """
        Verifica se há bingo em alguma das cartelas do jogador
        
        :return: True se há bingo em pelo menos uma cartela, False caso contrário
        """
        for i, cartela in enumerate(self.cartelas, 1):
            if cartela.verificar_bingo():
                return i
        return None
    
    def imprimir_todas_cartelas(self):
        """
        Imprime todas as cartelas do jogador
        """
        for i, cartela in enumerate(self.cartelas, 1):
            print(f"\n--- Cartela {i} ---")
            cartela.imprimir_cartela()
    
    def adicionar_numero_sorteado(self, numero):
        """
        Adiciona um número à lista de números sorteados
        """
        self.numeros_sorteados.append(numero)
    
    def get_numeros_sorteados(self):
        """
        Retorna a lista de números sorteados
        """
        return self.numeros_sorteados

if __name__ == "__main__":
    cartela = CartelaBingo()
    cartela.imprimir_cartela()
    
    # Simulando marcação de alguns números
    numeros_sorteados = [10, 25, 40, 55, 70]
    for numero in numeros_sorteados:
        cartela.marcar_numero(numero)
    
    print("\nApós marcação:")
    cartela.imprimir_cartela()
    
    print("\nBingo?", cartela.verificar_bingo())
    