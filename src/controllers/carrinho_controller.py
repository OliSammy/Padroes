"""
Controller para gerenciamento do carrinho (padrão MVC)
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from DAO.config import get_db
from DAO.models import Cliente
from DAO.crud import CarrinhoRepository, BebidaRepository, PersonalizacaoRepository
from patterns.business_object import ClienteBO
from patterns.decorator import ComponenteBebida, BebidaPersonalizada
from patterns.factory import MenuFactory

# Importar autenticação
from src.auth_service import get_current_user


class CarrinhoItemCreate(BaseModel):
    """Schema para criação de item no carrinho"""
    bebida_id: int
    quantidade: int = 1
    personalizacoes: List[int] = []
    observacoes: Optional[str] = None


class CarrinhoItemUpdate(BaseModel):
    """Schema para atualização de item no carrinho"""
    quantidade: int
    personalizacoes: List[int] = []


class CarrinhoItemResponse(BaseModel):
    """Schema de resposta para item do carrinho"""
    id: int
    bebida_id: int
    bebida_nome: str
    bebida_descricao: str
    quantidade: int
    preco_unitario: float
    subtotal: float
    personalizacoes: List[Dict[str, Any]]
    observacoes: Optional[str] = None


class CarrinhoResponse(BaseModel):
    """Schema de resposta para carrinho completo"""
    itens: List[CarrinhoItemResponse]
    total_itens: int
    total_valor: float


class CarrinhoController:
    """Controller para operações do carrinho"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/carrinho", tags=["Carrinho"])
        self._setup_routes()
        self.menu_factory = MenuFactory()
    
    def _setup_routes(self):
        """Configura as rotas do controller"""
        
        @self.router.get("", response_model=CarrinhoResponse)
        async def obter_carrinho(
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """
            Obtém o carrinho completo do cliente autenticado
            
            **Autenticação:** Requer token JWT válido
            
            **Retorna:**
            - **itens**: Lista completa de itens no carrinho com detalhes
            - **total_itens**: Número total de itens
            - **total_valor**: Valor total do carrinho antes de descontos
            
            **Informações dos Itens:**
            - Dados da bebida (nome, descrição, preço)
            - Quantidade selecionada
            - Personalizações aplicadas com preços
            - Observações especiais
            - Subtotal do item
            
            **Casos de Uso:**
            - Visualização do carrinho antes do checkout
            - Cálculo de totais em tempo real
            - Revisão de personalizações aplicadas
            """
            return await self.obter_carrinho_cliente(current_user.id, db)
        
        @self.router.post("", response_model=Dict[str, Any])
        async def adicionar_item(
            item_data: CarrinhoItemCreate,
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """
            Adiciona um item ao carrinho com personalizações usando Decorator Pattern
            
            **Body (JSON):**
            - **bebida_id**: ID da bebida a ser adicionada
            - **quantidade**: Quantidade desejada (padrão: 1)
            - **personalizacoes**: Lista de IDs das personalizações (opcional)
            - **observacoes**: Observações especiais para o item (opcional)
            
            **Comportamento:**
            - Aplica padrão Decorator para personalizações
            - Calcula preço final com personalizações
            - Valida disponibilidade da bebida
            - Soma quantidade se item já existir no carrinho
            
            **Autenticação:** Requer token JWT válido
            
            **Retorna:**
            - Confirmação da adição
            - Dados do item adicionado
            - Novo total do carrinho
            
            **Erros:**
            - 404: Bebida não encontrada
            - 400: Bebida não disponível
            """
            return await self.adicionar_item_carrinho(current_user.id, item_data, db)
        
        @self.router.put("/{item_id}", response_model=Dict[str, Any])
        async def atualizar_item(
            item_id: int,
            item_data: CarrinhoItemUpdate,
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """Atualiza item do carrinho"""
            return await self.atualizar_item_carrinho(item_id, current_user.id, item_data, db)
        
        @self.router.delete("/{item_id}")
        async def remover_item(
            item_id: int,
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """Remove item do carrinho"""
            return await self.remover_item_carrinho(item_id, current_user.id, db)
        
        @self.router.delete("")
        async def limpar_carrinho(
            cliente_id: int,
            db: Session = Depends(get_db)
        ):
            """Limpa carrinho do cliente"""
            return await self.limpar_carrinho_cliente(cliente_id, db)
        
        @self.router.get("/total")
        async def obter_total(
            cliente_id: int,
            db: Session = Depends(get_db)
        ):
            """Obtém total do carrinho"""
            return await self.obter_total_carrinho(cliente_id, db)
    
    async def obter_carrinho_cliente(self, cliente_id: int, db: Session) -> CarrinhoResponse:
        """Obtém carrinho do cliente usando Business Object, retornando apenas dicts serializáveis"""
        try:
            cliente_bo = ClienteBO(db)
            carrinho_dict = cliente_bo.obter_carrinho_dict(cliente_id)
            return CarrinhoResponse(**carrinho_dict)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter carrinho: {str(e)}"
            )
    
    async def adicionar_item_carrinho(
        self, 
        cliente_id: int, 
        item_data: CarrinhoItemCreate, 
        db: Session
    ) -> Dict[str, Any]:
        """Adiciona item ao carrinho usando Business Object, retornando apenas dicts serializáveis"""
        try:
            cliente_bo = ClienteBO(db)
            result = cliente_bo.adicionar_ao_carrinho_dict(
                cliente_id=cliente_id,
                bebida_id=item_data.bebida_id,
                quantidade=item_data.quantidade,
                personalizacoes=item_data.personalizacoes,
                observacoes=item_data.observacoes
            )
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Erro ao adicionar item ao carrinho"
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno: {str(e)}"
            )
    
    async def atualizar_item_carrinho(
        self, 
        item_id: int, 
        cliente_id: int, 
        item_data: CarrinhoItemUpdate, 
        db: Session
    ) -> Dict[str, Any]:
        """Atualiza item do carrinho usando Business Object, retornando apenas dicts serializáveis"""
        try:
            cliente_bo = ClienteBO(db)
            result = cliente_bo.atualizar_item_carrinho_dict(
                item_id=item_id,
                cliente_id=cliente_id,
                quantidade=item_data.quantidade,
                personalizacoes=item_data.personalizacoes
            )
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Erro ao atualizar item do carrinho"
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao atualizar item: {str(e)}"
            )
    
    async def remover_item_carrinho(self, item_id: int, cliente_id: int, db: Session) -> Dict[str, Any]:
        """Remove item do carrinho usando Business Object, retornando apenas dicts serializáveis"""
        try:
            cliente_bo = ClienteBO(db)
            result = cliente_bo.remover_item_carrinho_dict(item_id, cliente_id)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Erro ao remover item do carrinho"
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao remover item: {str(e)}"
            )
    
    async def limpar_carrinho_cliente(self, cliente_id: int, db: Session) -> Dict[str, Any]:
        """Limpa carrinho do cliente usando Business Object, retornando apenas dicts serializáveis"""
        try:
            cliente_bo = ClienteBO(db)
            result = cliente_bo.limpar_carrinho_dict(cliente_id)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Erro ao limpar carrinho"
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao limpar carrinho: {str(e)}"
            )
    
    async def obter_total_carrinho(self, cliente_id: int, db: Session) -> Dict[str, float]:
        """Obtém total do carrinho"""
        try:
            cliente_bo = ClienteBO(db)
            total = cliente_bo.obter_total_carrinho(cliente_id)
            
            return {"total": total}
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao calcular total: {str(e)}"
            )
