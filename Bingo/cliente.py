import socket
import threading
import numpy as np
import random
import time
import sys


class CartelaBingo:
    def __init__(self):
        self.intervalos = {
            "B": (1, 15),
            "I": (16, 30),
            "N": (31, 45),
            "G": (46, 60),
            "O": (61, 75),
        }
        self.cartela_numeros = np.zeros((5, 5), dtype=int)
        self.cartela_marcacao = np.zeros((5, 5), dtype=bool)
        self.gerar_cartela()

    def gerar_cartela(self):
        for coluna, (inicio, fim) in enumerate(self.intervalos.values()):
            numeros_coluna = random.sample(range(inicio, fim + 1), 5)
            self.cartela_numeros[:, coluna] = numeros_coluna
        self.cartela_numeros[2, 2] = 0
        self.cartela_marcacao[2, 2] = True

    def marcar_numero(self, numero):
        for linha in range(5):
            for coluna in range(5):
                if self.cartela_numeros[linha, coluna] == numero:
                    self.cartela_marcacao[linha, coluna] = True
                    return True
        return False

    def verificar_bingo(self):
        verificacao = self.cartela_marcacao.copy()
        verificacao[2, 2] = True
        return np.all(verificacao)

    def imprimir_cartela(self):
        print("\nCartela de Números:")
        print(self.cartela_numeros)
        print("\nCartela de Marcação:")
        print(self.cartela_marcacao)


class ClienteBingo:
    def __init__(self, host="localhost", porta=12345, max_tentativas=3):
        self.host = host
        self.porta = porta
        self.max_tentativas = max_tentativas
        self.cartelas = [CartelaBingo()]
        self.cliente = None
        self.numeros_sorteados = []
        self.rodando = False
        self.bingo_feito = False

    def adicionar_cartela(self):
        if len(self.cartelas) < 3:
            self.cartelas.append(CartelaBingo())
            print("\n--- Nova cartela adicionada! ---")
            self.cartelas[-1].imprimir_cartela()
            return True
        print("\n--- Você já tem o máximo de cartelas (3)! ---")
        return False

    def marcar_numero_em_todas_cartelas(self, numero):
        return any(cartela.marcar_numero(numero) for cartela in self.cartelas)

    def verificar_bingo_em_todas_cartelas(self):
        for i, cartela in enumerate(self.cartelas, 1):
            if cartela.verificar_bingo():
                return i
        return None

    def imprimir_todas_cartelas(self):
        for i, cartela in enumerate(self.cartelas, 1):
            print(f"\n--- Cartela {i} ---")
            cartela.imprimir_cartela()

    def menu_interativo(self):
        while True:
            print("\n--- MENU ---")
            print("1. Comprar nova cartela (Max:3)")
            print("2. Continuar jogando")
            print("3. Sair")

            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self.adicionar_cartela()
            elif opcao == "2":
                break
            elif opcao == "3":
                self.fechar_conexao()
                sys.exit()
            else:
                print("Opção inválida!")

    def conectar(self):
        tentativas = 0
        while tentativas < self.max_tentativas:
            try:
                self.cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.cliente.settimeout(10)
                self.cliente.connect((self.host, self.porta))

                # 1. Receber mensagem inicial do servidor
                dados = self.cliente.recv(1024).decode("utf-8")

                # Verificar se é mensagem de partidas disponíveis
                if dados.startswith("ESCOLHER_PARTIDA:") or dados.startswith(
                    "PARTIDAS_DISPONIVEIS:"
                ):
                    # Extrair a parte relevante da mensagem
                    partidas_str = dados.split(":", 1)[1]

                    # Processar lista de partidas
                    partidas_disponiveis = []
                    for partida in partidas_str.split(","):
                        try:
                            partida_id, info = partida.split(":")
                            jogadores, max_jogadores = info.split("/")
                            partidas_disponiveis.append(
                                {
                                    "id": partida_id,
                                    "jogadores": jogadores,
                                    "max": max_jogadores,
                                }
                            )
                        except ValueError:
                            continue

                    # Mostrar partidas disponíveis
                    print("\n--- Partidas Disponíveis ---")
                    for partida in partidas_disponiveis:
                        print(
                            f"Partida {partida['id']} - Jogadores: {partida['jogadores']}/{partida['max']}"
                        )

                    # 2. Enviar escolha da partida
                    while True:
                        escolha = input(
                            "Digite o ID da partida que deseja entrar: "
                        ).strip()
                        if any(p["id"] == escolha for p in partidas_disponiveis):
                            break
                        print("ID inválido! Tente novamente.")

                    self.cliente.sendall(escolha.encode("utf-8"))

                    # 3. Receber solicitação de nome
                    resposta = self.cliente.recv(1024).decode("utf-8")
                    if resposta == "DIGITE_SEU_NOME":
                        # 4. Enviar nome do jogador
                        self.nome_jogador = input("Digite seu nome: ").strip()
                        self.cliente.sendall(self.nome_jogador.encode("utf-8"))

                        # 5. Receber confirmação final
                        confirmacao = self.cliente.recv(1024).decode("utf-8")
                        if confirmacao.startswith(
                            ("REGISTRO_ACEITO", "REGISTRO_COMPLETO")
                        ):
                            print("\nRegistrado com sucesso na partida!")
                            self.menu_interativo()
                            self.cliente.sendall("PRONTO".encode("utf-8"))
                            self.rodando = True
                            threading.Thread(target=self.receber_numeros).start()
                            return True
                        else:
                            print("Erro no registro:", confirmacao)
                    else:
                        print("Protocolo inválido:", resposta)
                else:
                    print("Resposta inesperada do servidor:", dados)

            except socket.timeout:
                print("Timeout ao conectar com o servidor")
            except Exception as e:
                print(f"Erro na conexão: {str(e)}")
            finally:
                tentativas += 1
                if tentativas < self.max_tentativas:
                    print(f"Tentando novamente ({tentativas}/{self.max_tentativas})...")
                    time.sleep(2)
                self.fechar_conexao()

        print("Não foi possível conectar após várias tentativas.")
        return False

    def receber_numeros(self):
        while self.rodando:
            try:
                dados = self.cliente.recv(1024).decode("utf-8")
                if not dados:
                    print("\nConexão com o servidor encerrada")
                    break

                if dados.startswith("BINGO_VENCEDOR:"):
                    vencedor = dados.split(":")[1]
                    print(f"\n--- {vencedor} venceu o jogo! ---")
                    break
                elif dados == "JOGO_CANCELADO":
                    print("\n--- Jogo cancelado pelo servidor ---")
                    break
                elif dados == "FIM_JOGO":
                    print("\n--- Jogo encerrado ---")
                    break

                try:
                    numero = int(dados)
                    self.numeros_sorteados.append(numero)
                    print(f"\nNúmero sorteado: {numero}")
                    print("Total sorteados:", len(self.numeros_sorteados))

                    self.marcar_numero_em_todas_cartelas(numero)

                    cartela_vencedora = self.verificar_bingo_em_todas_cartelas()
                    if cartela_vencedora and not self.bingo_feito:
                        print(f"\n--- BINGO na Cartela {cartela_vencedora}! ---")
                        self.bingo_feito = True
                        self.cliente.sendall("BINGO".encode("utf-8"))
                        break

                    self.imprimir_todas_cartelas()

                except ValueError:
                    print("Número inválido recebido:", dados)

            except Exception as e:
                print(f"Erro ao receber dados: {str(e)}")
                break

        self.rodando = False
        self.fechar_conexao()

    def fechar_conexao(self):
        self.rodando = False
        if self.cliente:
            try:
                self.cliente.close()
            except:
                pass
            self.cliente = None


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345

    cliente = ClienteBingo(host=host, porta=porta)
    try:
        if cliente.conectar():
            while cliente.rodando:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando cliente...")
    finally:
        cliente.fechar_conexao()


if __name__ == "__main__":
    main()
