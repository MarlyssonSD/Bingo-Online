import socket
import threading
import random
import time
import sys


class PartidaBingo:
    def __init__(self, id_partida, min_clientes=2, max_clientes=10, tempo_espera=30):
        self.id_partida = id_partida
        self.min_clientes = min_clientes
        self.max_clientes = max_clientes
        self.tempo_espera = tempo_espera

        self.clientes = []
        self.clientes_prontos = []
        self.nomes_jogadores = {}
        self.numeros_sorteados = []

        self.jogo_em_andamento = False
        self.aceitando_conexoes = True
        self.sorteio_iniciado = False

        self.lock = threading.Lock()

        print(f"\n--- Partida {self.id_partida} criada ---")
        print(f"Aguardando jogadores ({self.min_clientes}-{self.max_clientes})...")
        print(f"Tempo de espera: {self.tempo_espera}s")

    def gerenciar_cliente(self, cliente_socket, endereco):
        try:
            if self.jogo_em_andamento or self.sorteio_iniciado:
                cliente_socket.sendall("JOGO_EM_ANDAMENTO".encode("utf-8"))
                cliente_socket.close()
                return

            # Fluxo de conexão simplificado e robusto
            cliente_socket.sendall("CONECTADO|DIGITE_NOME".encode("utf-8"))
            nome_jogador = cliente_socket.recv(1024).decode("utf-8").strip()

            if not nome_jogador:
                raise ValueError("Nome inválido")

            with self.lock:
                self.clientes.append(cliente_socket)
                self.clientes_prontos.append(cliente_socket)
                self.nomes_jogadores[cliente_socket] = nome_jogador

                print(
                    f"\n[Partida {self.id_partida}] Jogador '{nome_jogador}' conectado"
                )
                print(f"Total: {len(self.clientes_prontos)}/{self.max_clientes}")

                cliente_socket.sendall(
                    f"REGISTRADO|PARTIDA_{self.id_partida}".encode("utf-8")
                )

                if len(self.clientes_prontos) >= self.max_clientes:
                    self.iniciar_jogo()
                elif len(self.clientes_prontos) >= self.min_clientes and not hasattr(
                    self, "temporizador_iniciado"
                ):
                    self.temporizador_iniciado = True
                    threading.Thread(target=self.iniciar_temporizador).start()

            # Loop principal do jogo
            while self.jogo_em_andamento:
                try:
                    mensagem = cliente_socket.recv(1024).decode("utf-8")
                    if mensagem == "BINGO":
                        self.verificar_bingo(cliente_socket)
                        break
                except:
                    break

            self.remover_cliente(cliente_socket)

        except Exception as e:
            print(f"[Partida {self.id_partida}] Erro: {str(e)}")
            try:
                cliente_socket.close()
            except:
                pass

    def iniciar_jogo(self):
        with self.lock:
            if not self.sorteio_iniciado:
                print(f"\n--- Iniciando Partida {self.id_partida} ---")
                print(f"Jogadores conectados: {len(self.clientes_prontos)}")
                self.jogo_em_andamento = True
                self.sorteio_iniciado = True
                threading.Thread(target=self.iniciar_sorteio).start()

    def iniciar_temporizador(self):
        print(
            f"\n[Partida {self.id_partida}] Aguardando {self.tempo_espera}s por mais jogadores..."
        )
        time.sleep(self.tempo_espera)
        self.iniciar_jogo()

    def iniciar_sorteio(self):
        numeros = random.sample(range(1, 76), 75)

        for numero in numeros:
            if not self.jogo_em_andamento:
                break

            self.numeros_sorteados.append(numero)
            print(f"\n[Partida {self.id_partida}] Número sorteado: {numero}")
            print(f"Total sorteados: {len(self.numeros_sorteados)}/75")

            self.enviar_numero(numero)
            time.sleep(3)

            if not self.clientes:
                self.finalizar_jogo("TODOS_DESCONECTADOS")
                break

        if self.jogo_em_andamento:
            self.finalizar_jogo()

    def verificar_bingo(self, cliente_socket):
        vencedor = self.nomes_jogadores.get(cliente_socket, "Jogador desconhecido")
        print(f"\n--- [Partida {self.id_partida}] BINGO! {vencedor} venceu! ---")
        self.finalizar_jogo("BINGO_VENCEDOR", vencedor)

    def enviar_numero(self, numero):
        with self.lock:
            clientes_remover = []
            for cliente in self.clientes[:]:
                try:
                    cliente.send(str(numero).encode("utf-8"))
                except:
                    clientes_remover.append(cliente)

            for cliente in clientes_remover:
                self.remover_cliente(cliente)

    def remover_cliente(self, cliente_socket):
        with self.lock:
            try:
                if cliente_socket in self.clientes:
                    self.clientes.remove(cliente_socket)
                if cliente_socket in self.clientes_prontos:
                    self.clientes_prontos.remove(cliente_socket)

                print(
                    f"[Partida {self.id_partida}] Jogador removido. Restantes: {len(self.clientes_prontos)}"
                )

                if (
                    self.jogo_em_andamento
                    and len(self.clientes_prontos) < self.min_clientes
                ):
                    print(
                        f"\n[Partida {self.id_partida}] Jogo cancelado - jogadores insuficientes"
                    )
                    self.finalizar_jogo("JOGO_CANCELADO")

                cliente_socket.close()
            except Exception as e:
                print(f"[Partida {self.id_partida}] Erro ao remover cliente: {str(e)}")

    def finalizar_jogo(self, mensagem="FIM_JOGO", vencedor=None):
        self.jogo_em_andamento = False
        self.sorteio_iniciado = False
        self.aceitando_conexoes = False

        mensagem_final = f"{mensagem}:{vencedor}" if vencedor else mensagem

        for cliente in self.clientes[:]:
            try:
                cliente.send(mensagem_final.encode("utf-8"))
                cliente.close()
            except:
                pass

        self.clientes.clear()
        self.clientes_prontos.clear()
        self.nomes_jogadores.clear()

        print(f"\n--- [Partida {self.id_partida}] Jogo finalizado ---")


class ServidorBingo:
    def __init__(self, host="0.0.0.0", porta=12345):
        self.host = host
        self.porta = porta
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.bind((self.host, self.porta))
        self.servidor.listen(5)

        self.partidas = {}
        self.proximo_id = 1
        self.lock = threading.Lock()

        print(f"\n=== SERVIDOR DE BINGO ===")
        print(f"Endereço: {self.host}:{self.porta}")
        print("Comandos disponíveis:")
        print("nova - Criar nova partida")
        print("listar - Ver partidas ativas")
        print("sair - Encerrar servidor")

        threading.Thread(target=self.gerenciar_comandos, daemon=True).start()
        threading.Thread(target=self.aceitar_conexoes, daemon=True).start()

    def criar_nova_partida(self):
        try:
            print("\n--- Criar Nova Partida ---")
            min_jog = int(input("Mínimo de jogadores [2]: ") or 2)
            max_jog = int(input("Máximo de jogadores [10]: ") or 10)
            espera = int(input("Tempo de espera (segundos) [30]: ") or 30)

            with self.lock:
                id_partida = self.proximo_id
                self.partidas[id_partida] = PartidaBingo(
                    id_partida=id_partida,
                    min_clientes=min_jog,
                    max_clientes=max_jog,
                    tempo_espera=espera,
                )
                self.proximo_id += 1

            print(f"\nPartida {id_partida} criada com sucesso!")
            print(f"Configuração: {min_jog}-{max_jog} jogadores, {espera}s de espera")

        except ValueError:
            print("Erro: Valores inválidos. Use apenas números.")

    def listar_partidas(self):
        with self.lock:
            if not self.partidas:
                print("\nNenhuma partida ativa no momento")
                return

            print("\n--- Partidas Ativas ---")
            for id_partida, partida in self.partidas.items():
                status = "Em jogo" if partida.jogo_em_andamento else "Aguardando"
                print(
                    f"Partida {id_partida}: {status} | Jogadores: {len(partida.clientes_prontos)}/{partida.max_clientes}"
                )

    def aceitar_conexoes(self):
        while True:
            try:
                cliente, endereco = self.servidor.accept()

                with self.lock:
                    partidas_disponiveis = [
                        (id, p)
                        for id, p in self.partidas.items()
                        if p.aceitando_conexoes and not p.jogo_em_andamento
                    ]

                if not partidas_disponiveis:
                    cliente.sendall("NENHUMA_PARTIDA_DISPONIVEL".encode("utf-8"))
                    cliente.close()
                    continue

                lista_partidas = ",".join(
                    [
                        f"{id}:{len(p.clientes_prontos)}/{p.max_clientes}"
                        for id, p in partidas_disponiveis
                    ]
                )
                cliente.sendall(f"ESCOLHER_PARTIDA:{lista_partidas}".encode("utf-8"))

                escolha = cliente.recv(1024).decode("utf-8").strip()

                try:
                    id_escolhido = int(escolha)
                    if id_escolhido not in [id for id, _ in partidas_disponiveis]:
                        raise ValueError

                    partida = self.partidas[id_escolhido]
                    threading.Thread(
                        target=partida.gerenciar_cliente, args=(cliente, endereco)
                    ).start()

                except:
                    cliente.sendall("PARTIDA_INVALIDA".encode("utf-8"))
                    cliente.close()

            except Exception as e:
                print(f"Erro ao aceitar conexão: {str(e)}")

    def gerenciar_comandos(self):
        while True:
            comando = input("\n> ").strip().lower()

            if comando == "nova":
                self.criar_nova_partida()
            elif comando == "listar":
                self.listar_partidas()
            elif comando == "sair":
                print("Encerrando servidor...")
                self.servidor.close()
                sys.exit()
            else:
                print("Comando inválido. Use 'nova', 'listar' ou 'sair'")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 12345

    servidor = ServidorBingo(host=host, porta=porta)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServidor encerrado pelo usuário")
    finally:
        servidor.servidor.close()


if __name__ == "__main__":
    main()
