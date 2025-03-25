import random
import numpy as np

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
        print("Cartela de Números:")
        print(self.cartela_numeros)
        print("\nCartela de Marcação:")
        print(self.cartela_marcacao)

# Exemplo de uso
if __name__ == "__main__":
    cartela = CarteldeBingo()
    cartela.imprimir_cartela()
    
    # Simulando marcação de alguns números
    numeros_sorteados = [10, 25, 40, 55, 70]
    for numero in numeros_sorteados:
        cartela.marcar_numero(numero)
    
    print("\nApós marcação:")
    cartela.imprimir_cartela()
    
    print("\nBingo?", cartela.verificar_bingo())
    