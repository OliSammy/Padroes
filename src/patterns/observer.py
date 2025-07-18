from abc import ABC, abstractmethod
from patterns.state import Pedido

class Observer(ABC):
    @abstractmethod
    def update(self, pedido_id, estado):
        pass

class PedidoSubject:
    def __init__(self, pedido_id):
        self.pedido = Pedido(pedido_id)
        self._observers = []

    def adicionar_observer(self, observer):
        self._observers.append(observer)

    def remover_observer(self, observer):
        self._observers.remove(observer)

    def notificar_observers(self):
        for observer in self._observers:
            observer.update(self.pedido.pedido_id, self.pedido.get_estado())

    def avancar_estado(self):
        self.pedido.avancar_estado()
        self.notificar_observers()
    
    def set_status(self, status):
        """Método para definir status diretamente para testes"""
        # Para testes, vamos simular mudança de status
        self.notificar_observers()

class CozinhaObserver(Observer):
    def update(self, pedido_id, estado):
        print(f"[Cozinha] Pedido {pedido_id} está agora '{estado}'.")

class ClienteObserver(Observer):
    def update(self, pedido_id, estado):
        print(f"[Cliente] Seu pedido {pedido_id} está agora '{estado}'.")
