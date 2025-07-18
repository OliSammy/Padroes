from abc import ABC, abstractmethod
from typing import Dict, Type, Optional
from .decorator import ComponenteBebida, BebidaBase, Cafe, Cha, Chocolate, Suco


class BebidaFactory(ABC):
    """Factory Method interface para criação de bebidas"""
    
    @abstractmethod
    def criar_bebida(self) -> ComponenteBebida:
        pass


class CafeFactory(BebidaFactory):
    """Factory concreta para cafés"""
    
    def criar_bebida(self) -> ComponenteBebida:
        return Cafe()


class ChaFactory(BebidaFactory):
    """Factory concreta para chás"""
    
    def criar_bebida(self) -> ComponenteBebida:
        return Cha()


class ChocolateFactory(BebidaFactory):
    """Factory concreta para chocolates"""
    
    def criar_bebida(self) -> ComponenteBebida:
        return Chocolate()


class SucoFactory(BebidaFactory):
    """Factory concreta para sucos"""
    
    def criar_bebida(self) -> ComponenteBebida:
        return Suco()


class MenuFactory:
    """Factory para gerenciar criação de bebidas do menu"""
    
    def __init__(self):
        self._factories: Dict[str, BebidaFactory] = {
            "cafe": CafeFactory(),
            "cha": ChaFactory(),
            "chocolate": ChocolateFactory(),
            "suco": SucoFactory()
        }
    
    def registrar_factory(self, tipo: str, factory: BebidaFactory):
        """Registra uma nova factory"""
        self._factories[tipo] = factory
    
    def criar_bebida(self, tipo: str, nome: Optional[str] = None) -> Optional[ComponenteBebida]:
        """Cria bebida usando factory apropriada"""
        factory = self._factories.get(tipo.lower())
        if factory:
            bebida = factory.criar_bebida()
            if nome and isinstance(bebida, BebidaBase):
                bebida._nome = nome
                bebida._descricao = nome
            return bebida
        return None
    
    def get_tipos_disponiveis(self) -> list:
        """Retorna tipos de bebidas disponíveis"""
        return list(self._factories.keys())


class BebidaFactorySelector:
    """Selector para escolher factory baseado em critérios"""
    
    @staticmethod
    def obter_factory(tipo_bebida: str) -> Optional[BebidaFactory]:
        """Obtém factory baseada no tipo de bebida"""
        factories = {
            "cafe": CafeFactory(),
            "cha": ChaFactory(),
            "chocolate": ChocolateFactory(),
            "suco": SucoFactory()
        }
        return factories.get(tipo_bebida.lower())


