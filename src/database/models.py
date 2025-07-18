"""
Modelos SQLAlchemy para o banco de dados
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .config import Base

# Enums para o banco
class TipoBebidasEnum(enum.Enum):
    CAFE = "cafe"
    CHA = "cha"
    SUCO = "suco"

class StatusPedidoEnum(enum.Enum):
    PENDENTE = "pendente"
    RECEBIDO = "recebido"
    EM_PREPARO = "em_preparo"
    PRONTO = "pronto"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"

class MetodoPagamentoEnum(enum.Enum):
    DINHEIRO = "dinheiro"
    CARTAO = "cartao"
    PIX = "pix"
    FIDELIDADE = "fidelidade"  

class TipoUsuarioEnum(enum.Enum):
    CLIENTE = "cliente"
    STAFF = "staff"

# Modelos
class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    tipo_usuario = Column(Enum(TipoUsuarioEnum), default=TipoUsuarioEnum.CLIENTE, nullable=False)
    pontos_fidelidade = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    pedidos = relationship("Pedido", back_populates="cliente")
    carrinho = relationship("ItemCarrinho", back_populates="cliente")

class Bebida(Base):
    __tablename__ = "bebidas"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    preco_base = Column(Float, nullable=False)
    tipo = Column(Enum(TipoBebidasEnum), nullable=False)
    descricao = Column(Text)
    disponivel = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    personalizacoes = relationship("Personalizacao", back_populates="bebida")
    itens_carrinho = relationship("ItemCarrinho", back_populates="bebida")
    itens_pedido = relationship("ItemPedido", back_populates="bebida")

class Personalizacao(Base):
    __tablename__ = "personalizacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    preco_adicional = Column(Float, default=0.0)
    categoria = Column(String(50))  # "leite", "adocante", "extra"
    disponivel = Column(Boolean, default=True)
    
    # Relacionamentos
    bebida_id = Column(Integer, ForeignKey("bebidas.id"))
    bebida = relationship("Bebida", back_populates="personalizacoes")
    itens_carrinho = relationship("ItemCarrinhoPersonalizacao", back_populates="personalizacao")
    itens_pedido = relationship("ItemPedidoPersonalizacao", back_populates="personalizacao")

class ItemCarrinho(Base):
    __tablename__ = "itens_carrinho"
    
    id = Column(Integer, primary_key=True, index=True)
    quantidade = Column(Integer, default=1)
    preco_unitario = Column(Float, nullable=False)
    observacoes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    cliente = relationship("Cliente", back_populates="carrinho")
    bebida_id = Column(Integer, ForeignKey("bebidas.id"))
    bebida = relationship("Bebida", back_populates="itens_carrinho")
    personalizacoes = relationship("ItemCarrinhoPersonalizacao", back_populates="item_carrinho")

class ItemCarrinhoPersonalizacao(Base):
    __tablename__ = "itens_carrinho_personalizacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamentos
    item_carrinho_id = Column(Integer, ForeignKey("itens_carrinho.id"))
    item_carrinho = relationship("ItemCarrinho", back_populates="personalizacoes")
    personalizacao_id = Column(Integer, ForeignKey("personalizacoes.id"))
    personalizacao = relationship("Personalizacao", back_populates="itens_carrinho")

class Pedido(Base):
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    total = Column(Float, nullable=False)
    desconto = Column(Float, default=0.0)
    total_final = Column(Float, nullable=False)
    status = Column(Enum(StatusPedidoEnum), default=StatusPedidoEnum.PENDENTE)
    metodo_pagamento = Column(Enum(MetodoPagamentoEnum), nullable=False)
    observacoes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    cliente = relationship("Cliente", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido")
    historico = relationship("HistoricoPedido", back_populates="pedido")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    observacoes = Column(Text)  # Observações específicas do item
    
    # Relacionamentos
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    pedido = relationship("Pedido", back_populates="itens")
    bebida_id = Column(Integer, ForeignKey("bebidas.id"))
    bebida = relationship("Bebida", back_populates="itens_pedido")
    personalizacoes = relationship("ItemPedidoPersonalizacao", back_populates="item_pedido")

class ItemPedidoPersonalizacao(Base):
    __tablename__ = "itens_pedido_personalizacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamentos
    item_pedido_id = Column(Integer, ForeignKey("itens_pedido.id"))
    item_pedido = relationship("ItemPedido", back_populates="personalizacoes")
    personalizacao_id = Column(Integer, ForeignKey("personalizacoes.id"))
    personalizacao = relationship("Personalizacao", back_populates="itens_pedido")

class HistoricoPedido(Base):
    __tablename__ = "historico_pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    status_anterior = Column(Enum(StatusPedidoEnum))
    status_novo = Column(Enum(StatusPedidoEnum), nullable=False)
    observacao = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    pedido = relationship("Pedido", back_populates="historico")
