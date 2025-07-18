"""
Controller para gerenciamento de bebidas (padrão MVC)
Sistema de Cafeteria - Padrões GoF
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from database.config import get_db
from database.models import Cliente, Bebida, TipoBebidasEnum
from database.crud import BebidaRepository, PersonalizacaoRepository
from patterns.business_object import ProdutoBO
from patterns.factory import MenuFactory, BebidaFactorySelector
from patterns.decorator import *

# Importar autenticação
from src.auth_service import get_current_user, get_current_staff_user


class BebidaCreate(BaseModel):
    """Schema para criação de bebida"""
    nome: str = Field(..., min_length=1, max_length=100)
    preco_base: float = Field(..., gt=0)
    tipo: str = Field(..., description="Tipo da bebida: cafe, cha, suco")
    descricao: Optional[str] = None
    disponivel: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "nome": "Cappuccino",
                "preco_base": 8.50,
                "tipo": "cafe",
                "descricao": "Café espresso com leite vaporizado e espuma",
                "disponivel": True
            }
        }


class BebidaUpdate(BaseModel):
    """Schema para atualização de bebida"""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    preco_base: Optional[float] = Field(None, gt=0)
    tipo: Optional[str] = None
    descricao: Optional[str] = None
    disponivel: Optional[bool] = None


class BebidaResponse(BaseModel):
    """Schema de resposta para bebida"""
    id: int
    nome: str
    preco_base: float
    tipo: str
    descricao: Optional[str]
    disponivel: bool
    personalizacoes_disponiveis: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class BebidaPersonalizadaResponse(BaseModel):
    """Schema para bebida personalizada usando Decorator Pattern"""
    descricao: str
    preco_final: float
    tipo: str
    personalizacoes_aplicadas: List[str]


class MenuResponse(BaseModel):
    """Schema para resposta do menu completo"""
    bebidas_disponiveis: List[BebidaResponse]
    tipos_bebidas: List[str]
    total_bebidas: int


class BebidaController:
    """Controller para gerenciamento de bebidas"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/bebidas", tags=["Bebidas"])
        self.menu_factory = MenuFactory()
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Configura as rotas do controller"""
        
        # Rotas públicas (acessíveis a todos os usuários autenticados)
        @self.router.get("/", response_model=List[BebidaResponse])
        async def listar_bebidas(
            tipo: Optional[str] = Query(None, description="Filtrar por tipo de bebida"),
            disponivel: Optional[bool] = Query(True, description="Mostrar apenas bebidas disponíveis"),
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """
            Lista todas as bebidas disponíveis no cardápio (dados prontos do BO)
            """
            try:
                produto_bo = ProdutoBO(db)
                bebidas_dict = produto_bo.listar_bebidas_dict(tipo, disponivel)
                return bebidas_dict
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao listar bebidas: {str(e)}"
                )
        
        @self.router.get("/menu", response_model=MenuResponse)
        async def obter_menu_completo(
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """
            Obtém o menu completo da cafeteria usando Factory Pattern (dados prontos do BO)
            """
            try:
                produto_bo = ProdutoBO(db)
                menu_dict = produto_bo.obter_menu_completo_dict()
                return MenuResponse(**menu_dict)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter menu: {str(e)}"
                )
        
        @self.router.get("/{bebida_id}", response_model=BebidaResponse)
        async def obter_bebida(
            bebida_id: int,
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """
            Obtém detalhes de uma bebida específica por ID (dados prontos do BO)
            """
            try:
                produto_bo = ProdutoBO(db)
                bebida_dict = produto_bo.obter_bebida_dict(bebida_id)
                if not bebida_dict:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Bebida não encontrada"
                    )
                return bebida_dict
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter bebida: {str(e)}"
                )
        
        @self.router.post("/personalizar/{bebida_id}", response_model=BebidaPersonalizadaResponse)
        async def personalizar_bebida(
            bebida_id: int,
            personalizacoes_ids: List[int],
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """Personaliza uma bebida usando o Decorator Pattern (dados prontos do BO)"""
            try:
                produto_bo = ProdutoBO(db)
                bebida_pers_dict = produto_bo.personalizar_bebida_dict(bebida_id, personalizacoes_ids)
                if not bebida_pers_dict:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Bebida não encontrada ou não foi possível personalizar"
                    )
                return BebidaPersonalizadaResponse(**bebida_pers_dict)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao personalizar bebida: {str(e)}"
                )
        
        # Rotas administrativas (apenas para staff)
        @self.router.post("/", response_model=BebidaResponse)
        async def criar_bebida(
            bebida_data: BebidaCreate,
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Cria uma nova bebida (apenas staff)"""
            try:
                produto_bo = ProdutoBO(db)
                # Validar tipo de bebida
                try:
                    tipo_enum = TipoBebidasEnum(bebida_data.tipo)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Tipo de bebida inválido. Tipos válidos: {[t.value for t in TipoBebidasEnum]}"
                    )
                # Criar bebida usando Business Object
                bebida_dict = produto_bo.criar_bebida_dict(
                    nome=bebida_data.nome,
                    preco_base=bebida_data.preco_base,
                    tipo=tipo_enum,
                    descricao=bebida_data.descricao,
                    disponivel=bebida_data.disponivel
                )
                if not bebida_dict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Já existe uma bebida com este nome"
                    )
                return bebida_dict
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao criar bebida: {str(e)}"
                )
        
        @self.router.put("/{bebida_id}", response_model=BebidaResponse)
        async def atualizar_bebida(
            bebida_id: int,
            bebida_data: BebidaUpdate,
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Atualiza uma bebida existente (apenas staff)"""
            try:
                produto_bo = ProdutoBO(db)
                # Validar tipo se fornecido
                if bebida_data.tipo:
                    try:
                        TipoBebidasEnum(bebida_data.tipo)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Tipo de bebida inválido. Tipos válidos: {[t.value for t in TipoBebidasEnum]}"
                        )
                # Atualizar usando Business Object
                bebida_dict = produto_bo.atualizar_bebida_dict(
                    bebida_id=bebida_id,
                    dados_atualizacao=bebida_data.model_dump(exclude_unset=True)
                )
                if not bebida_dict:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Bebida não encontrada"
                    )
                return bebida_dict
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao atualizar bebida: {str(e)}"
                )
        
        @self.router.delete("/{bebida_id}")
        async def deletar_bebida(
            bebida_id: int,
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Deleta uma bebida (apenas staff)"""
            try:
                produto_bo = ProdutoBO(db)
                # Verificar se tem pedidos associados
                if produto_bo.bebida_tem_pedidos(bebida_id):
                    # Apenas desabilitar em vez de deletar
                    produto_bo.atualizar_bebida_dict(
                        bebida_id=bebida_id,
                        dados_atualizacao={"disponivel": False}
                    )
                    return {"message": "Bebida desabilitada com sucesso (possui pedidos associados)"}
                else:
                    # Deletar completamente
                    produto_bo.deletar_bebida(bebida_id)
                    return {"message": "Bebida deletada com sucesso"}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao deletar bebida: {str(e)}"
                )
        
        @self.router.get("/tipos/disponiveis")
        async def obter_tipos_bebidas(
            current_user: Cliente = Depends(get_current_user)
        ):
            """Obtém tipos de bebidas disponíveis usando Factory Pattern"""
            try:
                tipos = self.menu_factory.get_tipos_disponiveis()
                return {
                    "tipos_disponiveis": tipos,
                    "total": len(tipos)
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter tipos: {str(e)}"
                )
