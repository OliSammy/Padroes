"""
Padrões GoF implementados para o sistema de cafeteria
"""

# Importações condicionais para evitar erros
try:
    from .decorator import *
except ImportError:
    pass

try:
    from .observer import *
except ImportError:
    pass

try:
    from .strategy import *
except ImportError:
    pass

try:
    from .factory import *
except ImportError:
    pass

try:
    from .command import *
except ImportError:
    pass

try:
    from .state import *
except ImportError:
    pass

try:
    from .dao import *
except ImportError:
    pass

try:
    from .business_object import *
except ImportError:
    pass

__all__ = [
    # Decorator Pattern
    'ComponenteBebida',
    'BebidaDecorator',
    'Cafe',
    'Cha',
    'Chocolate',
    'LeiteDeAveia',
    'Canela',
    'SemAcucar',
    'Leite',
    'ExtraShot',
    
    # Observer Pattern
    'Observer',
    'Subject',
    'PedidoSubject',
    'CozinhaObserver',
    'ClienteObserver',
    
    # Strategy Pattern
    'DescontoStrategy',
    'DescontoFidelidade',
    'DescontoPix',
    'SemDesconto',
    'ContextoPagamento',
    
    # Factory Method Pattern
    'BebidaFactory',
    'CafeFactory',
    'ChaFactory',
    'ChocolateFactory',
    'MenuFactory',
    
    # Command Pattern
    'Command',
    'CriarPedidoCommand',
    'CancelarPedidoCommand',
    'AlterarPedidoCommand',
    'CommandInvoker',
    
    # State Pattern
    'EstadoPedido',
    'PedidoRecebido',
    'PedidoEmPreparo',
    'PedidoPronto',
    'PedidoEntregue',
    'PedidoCancelado',
    'ContextoPedido',
    
    # DAO Pattern
    'GenericDAO',
    'PedidoDAO',
    'ClienteDAO',
    'ProdutoDAO',
    
    # Business Object Pattern
    'PedidoBO',
    'ClienteBO',
    'ProdutoBO'
]
