from abc import ABC, abstractmethod

class EstadoPedido(ABC):
    @abstractmethod
    def proximo_estado(self, pedido):
        pass
    @abstractmethod
    def __str__(self):
        pass
    @abstractmethod
    def pode_cancelar(self):
        """Define se é possível cancelar neste estado"""
        pass

class PendenteState(EstadoPedido):
    def proximo_estado(self, pedido):
        pedido.estado = RecebidoState()
    def __str__(self):
        return "Pendente"
    def pode_cancelar(self):
        return True

class RecebidoState(EstadoPedido):
    def proximo_estado(self, pedido):
        pedido.estado = EmPreparoState()
    def __str__(self):
        return "Recebido"
    def pode_cancelar(self):
        return True

class EmPreparoState(EstadoPedido):
    def proximo_estado(self, pedido):
        pedido.estado = ProntoState()
    def __str__(self):
        return "Em preparo"
    def pode_cancelar(self):
        return False  # Não pode cancelar quando já está em preparo

class ProntoState(EstadoPedido):
    def proximo_estado(self, pedido):
        pedido.estado = EntregueState()
    def __str__(self):
        return "Pronto"
    def pode_cancelar(self):
        return False

class EntregueState(EstadoPedido):
    def proximo_estado(self, pedido):
        pass  # Estado final
    def __str__(self):
        return "Entregue"
    def pode_cancelar(self):
        return False
    
class CanceladoState(EstadoPedido):
    def proximo_estado(self, pedido):
        pass  # Estado final
    def __str__(self):
        return "Cancelado"
    def pode_cancelar(self):
        return False
    
class Pedido:
    def __init__(self, pedido_id, estado_inicial="pendente"):
        self.pedido_id = pedido_id
        # Mapear estado inicial do banco para classe State
        estado_map = {
            "pendente": PendenteState(),
            "recebido": RecebidoState(),
            "em_preparo": EmPreparoState(),
            "pronto": ProntoState(),
            "entregue": EntregueState(),
            "cancelado": CanceladoState()
        }
        self.estado = estado_map.get(estado_inicial, PendenteState())

    def avancar_estado(self):
        """Avança para o próximo estado usando State Pattern"""
        estado_anterior = str(self.estado)
        self.estado.proximo_estado(self)
        estado_novo = str(self.estado)
        return estado_anterior, estado_novo
        
    def cancelar_pedido(self):
        """Cancela o pedido se permitido no estado atual"""
        if self.estado.pode_cancelar():
            estado_anterior = str(self.estado)
            self.estado = CanceladoState()
            return True, estado_anterior, "Cancelado"
        return False, str(self.estado), str(self.estado)

    def get_estado(self):
        return str(self.estado).lower().replace(" ", "_")
    
    def get_estado_display(self):
        return str(self.estado)
    
    def pode_ser_cancelado(self):
        """Verifica se o pedido pode ser cancelado no estado atual"""
        return self.estado.pode_cancelar()