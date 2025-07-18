"""
Padrão Command para encapsular ações do sistema
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from .decorator import ComponenteBebida
from .observer import PedidoSubject, CozinhaObserver, ClienteObserver
from .state import Pedido as EstadoPedido


class Command(ABC):
    """Interface Command"""
    
    @abstractmethod
    def executar(self):
        pass
    
    @abstractmethod
    def desfazer(self):
        pass


class SistemaCafeteria:
    """Receiver - Sistema que executa as operações"""
    
    def __init__(self):
        self.pedidos_ativos: List[PedidoSubject] = []
        self._proximo_id = 1
        self._historico_comandos: List[Command] = []
    
    def executar_criacao_pedido(self, bebida: ComponenteBebida) -> PedidoSubject:
        """Executa criação de pedido"""
        pedido_id = self._proximo_id
        
        # Criar subject do pedido
        novo_pedido = PedidoSubject(pedido_id)
        novo_pedido.adicionar_observer(CozinhaObserver())
        novo_pedido.adicionar_observer(ClienteObserver())
        novo_pedido.notificar_observers()
        
        self.pedidos_ativos.append(novo_pedido)
        self._proximo_id += 1
        
        return novo_pedido
    
    def executar_cancelamento_pedido(self, pedido_id: int) -> bool:
        """Executa cancelamento de pedido"""
        pedido_para_cancelar = next(
            (p for p in self.pedidos_ativos if p.pedido.pedido_id == pedido_id), 
            None
        )
        
        if pedido_para_cancelar:
            pedido_para_cancelar.pedido.cancelar_pedido()
            pedido_para_cancelar.notificar_observers()
            print(f"[Sistema] Pedido {pedido_id} cancelado!")
            return True
        
        # Se o pedido não está na lista interna, pode ter sido criado externamente
        # Neste caso, apenas logamos que não foi encontrado na lista, mas não é erro crítico
        print(f"[Sistema] Pedido {pedido_id} não encontrado na lista interna! (pode ter sido criado externamente)")
        return True  # Retorna True para permitir que o BO faça o cancelamento no banco
    
    def executar_alteracao_status(self, pedido_id: int) -> bool:
        """Executa avanço no status do pedido"""
        pedido = next(
            (p for p in self.pedidos_ativos if p.pedido.pedido_id == pedido_id), 
            None
        )
        
        if pedido:
            pedido.avancar_estado()
            print(f"[Sistema] Status do pedido {pedido_id} alterado!")
            return True
        
        print(f"[Sistema] Pedido {pedido_id} não encontrado!")
        return False
    
    def obter_pedido(self, pedido_id: int) -> Optional[PedidoSubject]:
        """Obtém pedido por ID"""
        return next(
            (p for p in self.pedidos_ativos if p.pedido.pedido_id == pedido_id), 
            None
        )


class CriarPedidoCommand(Command):
    """Command concreto para criar pedido"""
    
    def __init__(self, pedido_bo, cliente_id: int, metodo_pagamento):
        self._pedido_bo = pedido_bo
        self._cliente_id = cliente_id
        self._metodo_pagamento = metodo_pagamento
        self.pedido_id = None

    def executar(self):
        """Executa criação do pedido via BO e armazena o id criado"""
        self.pedido_id = self._pedido_bo.criar_pedido(
            cliente_id=self._cliente_id,
            metodo_pagamento=self._metodo_pagamento
        )
        print(f"[Command] Comando criar pedido executado! Pedido ID: {self.pedido_id}")

    def desfazer(self):
        """Desfaz criação do pedido (cancela o pedido criado)"""
        if self.pedido_id:
            self._pedido_bo.cancelar_pedido_state_pattern(self.pedido_id)
            print(f"[Command] Comando criar pedido desfeito!")



class CancelarPedidoCommand(Command):
    """Command concreto para cancelar pedido via BO"""
    def __init__(self, pedido_bo, pedido_id: int):
        self._pedido_bo = pedido_bo
        self._pedido_id = pedido_id
        self.resultado = None

    def executar(self):
        self.resultado = self._pedido_bo._cancelar_pedido_state_pattern_impl(self._pedido_id)
        print(f"[Command] Comando cancelar pedido {self._pedido_id} executado!")

    def desfazer(self):
        print(f"[Command] Não é possível desfazer cancelamento do pedido {self._pedido_id}!")


class AvancarEstadoPedidoCommand(Command):
    """Command concreto para avançar estado do pedido via BO"""
    def __init__(self, pedido_bo, pedido_id: int):
        self._pedido_bo = pedido_bo
        self._pedido_id = pedido_id
        self.resultado = None

    def executar(self):
        self.resultado = self._pedido_bo._avancar_estado_pedido_impl(self._pedido_id)
        print(f"[Command] Comando avançar estado do pedido {self._pedido_id} executado!")

    def desfazer(self):
        print(f"[Command] Não implementado desfazer avanço de estado do pedido {self._pedido_id}!")


class AlterarStatusPedidoCommand(Command):
    """Command concreto para alterar status do pedido"""
    
    def __init__(self, sistema: SistemaCafeteria, pedido_id: int):
        self._sistema = sistema
        self._pedido_id = pedido_id
        self._status_anterior: Optional[str] = None
    
    def executar(self):
        """Executa alteração de status"""
        pedido = self._sistema.obter_pedido(self._pedido_id)
        if pedido:
            self._status_anterior = pedido.pedido.get_estado()
            if self._sistema.executar_alteracao_status(self._pedido_id):
                print(f"[Command] Status do pedido {self._pedido_id} alterado!")
            else:
                print(f"[Command] Falha ao alterar status do pedido {self._pedido_id}!")
    
    def desfazer(self):
        """Desfazer alteração de status é complexo, apenas logamos"""
        print(f"[Command] Reverter status do pedido {self._pedido_id} para {self._status_anterior}!")


class CommandInvoker:
    """Invoker - Gerencia execução dos comandos"""
    
    def __init__(self):
        self._historico: List[Command] = []
        self._posicao_atual = -1
    
    def executar_comando(self, comando: Command):
        """Executa um comando e o adiciona ao histórico"""
        comando.executar()
        
        # Remove comandos após a posição atual (para redo)
        self._historico = self._historico[:self._posicao_atual + 1]
        self._historico.append(comando)
        self._posicao_atual += 1
        
        print(f"[Invoker] Comando executado. Histórico: {len(self._historico)} comandos")
    
    def desfazer(self) -> bool:
        """Desfaz o último comando"""
        if self._posicao_atual >= 0:
            comando = self._historico[self._posicao_atual]
            comando.desfazer()
            self._posicao_atual -= 1
            print(f"[Invoker] Comando desfeito. Posição atual: {self._posicao_atual}")
            return True
        
        print("[Invoker] Nenhum comando para desfazer!")
        return False
    
    def refazer(self) -> bool:
        """Refaz o próximo comando"""
        if self._posicao_atual < len(self._historico) - 1:
            self._posicao_atual += 1
            comando = self._historico[self._posicao_atual]
            comando.executar()
            print(f"[Invoker] Comando refeito. Posição atual: {self._posicao_atual}")
            return True
        
        print("[Invoker] Nenhum comando para refazer!")
        return False
    
    def obter_historico(self) -> List[str]:
        """Obtém histórico de comandos como strings"""
        return [type(cmd).__name__ for cmd in self._historico]


class InterfaceUsuario:
    """Interface simplificada para demonstrar o padrão Command"""
    
    def __init__(self):
        self._sistema = SistemaCafeteria()
        self._invoker = CommandInvoker()
    
    def criar_pedido(self, bebida: ComponenteBebida):
        """Cria um pedido usando command pattern"""
        comando = CriarPedidoCommand(self._sistema, bebida)
        self._invoker.executar_comando(comando)
    
    def cancelar_pedido(self, pedido_id: int):
        """Cancela um pedido usando command pattern"""
        comando = CancelarPedidoCommand(self._sistema, pedido_id)
        self._invoker.executar_comando(comando)
    
    def alterar_status_pedido(self, pedido_id: int):
        """Altera status de um pedido usando command pattern"""
        comando = AlterarStatusPedidoCommand(self._sistema, pedido_id)
        self._invoker.executar_comando(comando)
    
    def desfazer_ultimo_comando(self):
        """Desfaz o último comando"""
        return self._invoker.desfazer()
    
    def refazer_comando(self):
        """Refaz o último comando desfeito"""
        return self._invoker.refazer()
    
    def obter_historico_comandos(self) -> List[str]:
        """Obtém histórico de comandos"""
        return self._invoker.obter_historico()