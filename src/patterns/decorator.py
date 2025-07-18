# Função utilitária para aplicar personalizações (Decorator Pattern)
def aplicar_personalizacoes(bebida: 'ComponenteBebida', personalizacoes_ids: list, personalizacao_repo) -> 'ComponenteBebida':
    """Aplica uma lista de personalizações a uma bebida usando os decorators apropriados."""
    if not personalizacoes_ids:
        return bebida
    # Mapeamento nome para decorator concreto
    decorator_map = {
        "leite de aveia": LeiteDeAveia,
        "leite desnatado": LeiteDesnatado,
        "canela": Canela,
        "chocolate extra": ChocolateExtra,
        "chantilly": Chantilly,
        "sem acucar": SemAcucar,
    }
    for pers_id in personalizacoes_ids:
        pers = personalizacao_repo.get_by_id(pers_id)
        if pers:
            nome_norm = pers.nome.strip().lower().replace("á", "a").replace("ã", "a").replace("ç", "c").replace("é", "e").replace("ê", "e").replace(" ", " ")
            decorator_class = decorator_map.get(nome_norm)
            if decorator_class:
                bebida = decorator_class(bebida)
            else:
                bebida = BebidaPersonalizada(bebida, pers.nome, pers.preco_adicional)
    return bebida
from abc import ABC, abstractmethod
from typing import List


class ComponenteBebida(ABC):
    """Interface Component do padrão Decorator"""
    
    @abstractmethod
    def get_descricao(self) -> str:
        pass
    
    @abstractmethod
    def get_preco(self) -> float:
        pass
    
    @abstractmethod
    def get_tipo(self) -> str:
        pass


class BebidaBase(ComponenteBebida):
    """Classe base para bebidas concretas"""
    
    def __init__(self, nome: str, preco: float, tipo: str, descricao: str = ""):
        self._nome = nome
        self._preco = preco
        self._tipo = tipo
        self._descricao = descricao or nome
    
    def get_descricao(self) -> str:
        return self._descricao
    
    def get_preco(self) -> float:
        return self._preco
    
    def get_tipo(self) -> str:
        return self._tipo
    
    def get_nome(self) -> str:
        return self._nome


# Bebidas concretas
class Cafe(BebidaBase):
    def __init__(self, nome: str = "Café", preco: float = 3.50):
        super().__init__(nome, preco, "Café", "Café tradicional")


class Cha(BebidaBase):
    def __init__(self, nome: str = "Chá", preco: float = 3.00):
        super().__init__(nome, preco, "Chá", "Chá tradicional")


class Chocolate(BebidaBase):
    def __init__(self, nome: str = "Chocolate", preco: float = 5.00):
        super().__init__(nome, preco, "Chocolate", "Chocolate quente")


class Suco(BebidaBase):
    def __init__(self, nome: str = "Suco", preco: float = 4.50):
        super().__init__(nome, preco, "Suco", "Suco natural")


class BebidaDecorator(ComponenteBebida):
    """Decorator base para personalizações"""
    
    def __init__(self, bebida: ComponenteBebida):
        self._bebida = bebida
    
    def get_descricao(self) -> str:
        return self._bebida.get_descricao()
    
    def get_preco(self) -> float:
        return self._bebida.get_preco()
    
    def get_tipo(self) -> str:
        return self._bebida.get_tipo()


# Decorators concretos para personalizações
class LeiteDeAveia(BebidaDecorator):
    def get_descricao(self) -> str:
        return self._bebida.get_descricao() + " com Leite de Aveia"
    
    def get_preco(self) -> float:
        return self._bebida.get_preco() + 1.00


class Canela(BebidaDecorator):
    def get_descricao(self) -> str:
        return self._bebida.get_descricao() + " com Canela"
    
    def get_preco(self) -> float:
        return self._bebida.get_preco() + 0.50


class SemAcucar(BebidaDecorator):
    def get_descricao(self) -> str:
        return self._bebida.get_descricao() + " sem Açúcar"
    
    def get_preco(self) -> float:
        return self._bebida.get_preco()  # Sem custo adicional


class LeiteDesnatado(BebidaDecorator):
    def get_descricao(self) -> str:
        return self._bebida.get_descricao() + " com Leite Desnatado"
    
    def get_preco(self) -> float:
        return self._bebida.get_preco() + 0.50


class ChocolateExtra(BebidaDecorator):
    def get_descricao(self) -> str:
        return self._bebida.get_descricao() + " com Chocolate Extra"
    
    def get_preco(self) -> float:
        return self._bebida.get_preco() + 1.00


class Chantilly(BebidaDecorator):
    def get_descricao(self) -> str:
        return self._bebida.get_descricao() + " com Chantilly"
    
    def get_preco(self) -> float:
        return self._bebida.get_preco() + 1.50


class BebidaPersonalizada(BebidaDecorator):
    """Decorator genérico para personalizações dinâmicas"""
    
    def __init__(self, bebida: ComponenteBebida, personalizacao: str, preco_adicional: float = 0.0):
        super().__init__(bebida)
        self._personalizacao = personalizacao
        self._preco_adicional = preco_adicional
    
    def get_descricao(self) -> str:
        return f"{self._bebida.get_descricao()} com {self._personalizacao}"
    
    def get_preco(self) -> float:
        return self._bebida.get_preco() + self._preco_adicional
