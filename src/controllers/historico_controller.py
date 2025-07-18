"""
Controller para gerenciamento do histórico de pedidos (padrão MVC)
Sistema de Cafeteria - Padrões GoF
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from database.config import get_db
from database.models import Cliente, HistoricoPedido, StatusPedidoEnum
from database.repositories import PedidoRepository, HistoricoRepository
from patterns.business_object import PedidoBO

# Importar autenticação
from src.auth_service import get_current_user, get_current_staff_user


class HistoricoResponse(BaseModel):
    """Schema de resposta para histórico do pedido"""
    id: int
    pedido_id: int
    status_anterior: Optional[str]
    status_novo: str
    observacao: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class PedidoComHistoricoResponse(BaseModel):
    """Schema de resposta para pedido com histórico completo"""
    pedido_id: int
    status_atual: str
    cliente_nome: str
    total_final: float
    created_at: datetime
    historico: List[HistoricoResponse]


class HistoricoController:
    """Controller para gerenciamento do histórico de pedidos"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/historico", tags=["Histórico de Pedidos"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Configura as rotas do controller"""
        
        @self.router.get("/pedido/{pedido_id}", response_model=List[HistoricoResponse])
        async def obter_historico_pedido(
            pedido_id: int,
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """Obtém o histórico completo de um pedido específico (via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                # Verificar se o pedido existe e permissões
                pedido = bo.obter_pedido(pedido_id)
                if not pedido:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pedido não encontrado"
                    )
                if (getattr(current_user, 'tipo_usuario', None) and getattr(current_user.tipo_usuario, 'value', None) == "cliente" and 
                    getattr(pedido, 'cliente_id', None) != getattr(current_user, 'id', None)):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Você só pode ver o histórico dos seus próprios pedidos"
                    )
                return bo.historico_pedido_dict(pedido_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter histórico: {str(e)}"
                )
        
        @self.router.get("/cliente/{cliente_id}", response_model=List[PedidoComHistoricoResponse])
        async def obter_historico_cliente(
            cliente_id: int,
            limit: int = Query(10, ge=1, le=100, description="Limite de pedidos retornados"),
            offset: int = Query(0, ge=0, description="Offset para paginação"),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """Obtém o histórico de pedidos de um cliente (via BO)"""
            try:
                # Verificar permissões
                if (current_user.tipo_usuario.value == "cliente" and 
                    current_user.id != cliente_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Você só pode ver seu próprio histórico"
                    )
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.historico_cliente_dict(cliente_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter histórico do cliente: {str(e)}"
                )
        
        @self.router.get("/todos", response_model=List[PedidoComHistoricoResponse])
        async def obter_todos_historicos(
            status_filtro: Optional[str] = Query(None, description="Filtrar por status"),
            data_inicio: Optional[datetime] = Query(None, description="Data de início do filtro"),
            data_fim: Optional[datetime] = Query(None, description="Data de fim do filtro"),
            limit: int = Query(50, ge=1, le=200, description="Limite de pedidos retornados"),
            offset: int = Query(0, ge=0, description="Offset para paginação"),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém histórico de todos os pedidos (apenas staff, via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.historico_geral_dict(
                    status_filtro=status_filtro,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    limit=limit,
                    offset=offset
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter históricos: {str(e)}"
                )
        
        @self.router.get("/status/{status}")
        async def obter_pedidos_por_status(
            status: str,
            limit: int = Query(20, ge=1, le=100),
            offset: int = Query(0, ge=0),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém pedidos por status específico (apenas staff, via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.historico_geral_dict(status_filtro=status, limit=limit, offset=offset)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter pedidos por status: {str(e)}"
                )
        
        @self.router.get("/estatisticas")
        async def obter_estatisticas_historico(
            dias: int = Query(30, ge=1, le=365, description="Número de dias para análise"),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém estatísticas do histórico de pedidos (apenas staff, via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.estatisticas_dict()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter estatísticas: {str(e)}"
                )
