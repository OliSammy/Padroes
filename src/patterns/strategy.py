from abc import ABC, abstractmethod

class DescontoStrategy(ABC):
    """Interface Strategy para cálculo de descontos"""
    
    @abstractmethod
    def calcular_desconto(self, valor: float) -> float:
        """Calcula desconto baseado na strategy"""
        pass
    
    @abstractmethod
    def get_descricao(self) -> str:
        """Retorna descrição do desconto"""
        pass


class DescontoPix(DescontoStrategy):
    """Strategy concreta para desconto PIX"""
    
    def calcular_desconto(self, valor: float) -> float:
        """5% de desconto no PIX"""
        return valor * 0.05
    
    def get_descricao(self) -> str:
        return "Desconto PIX (5%)"


class DescontoFidelidade(DescontoStrategy):
    """Strategy concreta para desconto fidelidade"""
    
    def calcular_desconto(self, valor: float) -> float:
        """10% de desconto para clientes fidelidade"""
        return valor * 0.10
    
    def get_descricao(self) -> str:
        return "Desconto Fidelidade (10%)"


class SemDesconto(DescontoStrategy):
    """Strategy concreta para sem desconto"""
    
    def calcular_desconto(self, valor: float) -> float:
        """Nenhum desconto"""
        return 0.0
    
    def get_descricao(self) -> str:
        return "Sem desconto"


class ContextoPagamento:
    """Contexto que usa as strategies de desconto"""
    
    def __init__(self):
        self._strategy = None

    def set_strategy(self, strategy: DescontoStrategy):
        """Define a strategy de desconto"""
        self._strategy = strategy
    
    def calcular_total(self, valor_original: float) -> float:
        """Calcula total com desconto aplicado"""
        if self._strategy:
            desconto = self._strategy.calcular_desconto(valor_original)
            return valor_original - desconto
        return valor_original
    
    def get_descricao_desconto(self) -> str:
        """Retorna descrição do desconto atual"""
        if self._strategy:
            return self._strategy.get_descricao()
        return "Nenhum desconto definido"