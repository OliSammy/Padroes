"""
Controller para dashboard e relatórios (padrão MVC)
Sistema de Cafeteria - Padrões GoF
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database.config import get_db
from database.models import Cliente, Pedido, Bebida, StatusPedidoEnum, ItemPedido
from database.crud import PedidoRepository, BebidaRepository

# Importar autenticação
from src.auth_service import get_current_user, get_current_staff_user


class EstatisticasResponse(BaseModel):
    """Schema de resposta para estatísticas gerais"""
    total_pedidos: int
    pedidos_hoje: int
    faturamento_total: float
    pedidos_pendentes: int
    pedidos_em_preparo: int
    ticket_medio: float


class BebidaMaisVendidaResponse(BaseModel):
    """Schema para bebidas mais vendidas"""
    bebida_id: int
    nome_bebida: str
    total_vendido: int
    receita_gerada: float


class RelatorioPeriodoResponse(BaseModel):
    """Schema para relatório de período"""
    periodo_inicio: datetime
    periodo_fim: datetime
    total_pedidos: int
    receita_total: float
    ticket_medio: float
    bebidas_mais_vendidas: List[BebidaMaisVendidaResponse]


class DashboardController:
    """Controller para dashboard e relatórios"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Configura as rotas do controller"""
        
        @self.router.get("/estatisticas", response_model=EstatisticasResponse)
        async def obter_estatisticas_gerais(
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém estatísticas gerais e métricas de performance do sistema (via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.estatisticas_dict()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter estatísticas: {str(e)}"
                )
        
        @self.router.get("/bebidas-mais-vendidas", response_model=List[BebidaMaisVendidaResponse])
        async def obter_bebidas_mais_vendidas(
            limite: int = Query(10, ge=1, le=50, description="Número de bebidas no ranking"),
            dias: int = Query(30, ge=1, le=365, description="Período em dias"),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém ranking das bebidas mais vendidas por período (via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.bebidas_mais_vendidas_dict(limite, dias)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter ranking de bebidas: {str(e)}"
                )
        
        @self.router.get("/relatorio-periodo", response_model=RelatorioPeriodoResponse)
        async def obter_relatorio_periodo(
            data_inicio: datetime = Query(..., description="Data de início do período"),
            data_fim: datetime = Query(..., description="Data de fim do período"),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém relatório detalhado de um período específico (via BO)"""
            try:
                if data_inicio >= data_fim:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Data de início deve ser anterior à data de fim"
                    )
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.relatorio_periodo_dict(data_inicio, data_fim)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao gerar relatório: {str(e)}"
                )
        
        @self.router.get("/pedidos-tempo-real")
        async def obter_pedidos_tempo_real(
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém pedidos em tempo real para a cozinha (via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.pedidos_tempo_real_dict()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter pedidos em tempo real: {str(e)}"
                )
        
        @self.router.get("/grafico-vendas")
        async def obter_dados_grafico_vendas(
            dias: int = Query(7, ge=1, le=90, description="Número de dias para o gráfico"),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Obtém dados para gráfico de vendas (via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                return bo.grafico_vendas_dict(dias)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter dados do gráfico: {str(e)}"
                )
        
        @self.router.get("/resumo-cliente")
        async def obter_resumo_cliente(
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """Obtém resumo para o cliente logado (via BO)"""
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                # Garante que o id do usuário é int (evita Column[int])
                # Garante que o id do usuário é int puro (evita Column)
                user_id = current_user.id
                # Se for Column ou não for int, lança erro
                if not isinstance(user_id, int):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="ID do usuário inválido para consulta de resumo."
                    )
                return bo.resumo_cliente_dict(user_id)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter resumo do cliente: {str(e)}"
                )
