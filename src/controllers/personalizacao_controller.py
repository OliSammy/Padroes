"""
Controller para gerenciamento de personalizações (padrão MVC)
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from DAO.config import get_db
from DAO.crud import PersonalizacaoRepository, BebidaRepository
from DAO.models import TipoBebidasEnum, Cliente
from src.auth_service import get_current_user
from patterns.decorator import (
    ComponenteBebida, BebidaPersonalizada, 
    LeiteDeAveia, Canela, SemAcucar, ChocolateExtra, Chantilly
)
from patterns.factory import MenuFactory


class PersonalizacaoResponse(BaseModel):
    """Schema de resposta para personalização"""
    id: int
    nome: str
    preco_adicional: float
    categoria: str
    disponivel: bool


class BebidaPersonalizadaRequest(BaseModel):
    """Schema para criação de bebida personalizada"""
    bebida_id: int
    personalizacoes: List[int]


class BebidaPersonalizadaResponse(BaseModel):
    """Schema de resposta para bebida personalizada"""
    bebida_base: Dict[str, Any]
    personalizacoes_aplicadas: List[PersonalizacaoResponse]
    descricao_final: str
    preco_final: float
    tipo: str


class PersonalizacaoController:
    """Controller para operações de personalização"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/personalizacoes", tags=["Personalizações"])
        self._setup_routes()
        self.menu_factory = MenuFactory()
        
        # Mapeamento de decorators
        self.decorator_map = {
            "leite_de_aveia": LeiteDeAveia,
            "canela": Canela,
            "sem_acucar": SemAcucar,
            "chocolate_extra": ChocolateExtra,
            "chantilly": Chantilly
        }
    
    def _setup_routes(self):
        """Configura as rotas do controller"""
        
        @self.router.get("", response_model=List[PersonalizacaoResponse])
        async def listar_personalizacoes(
            categoria: Optional[str] = None,
            db: Session = Depends(get_db)
        ):
            """
            Lista todas as personalizações disponíveis no sistema (via BO)
            """
            try:
                from patterns.business_object import ProdutoBO
                bo = ProdutoBO(db)
                return bo.listar_personalizacoes_dict(categoria)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao listar personalizações: {str(e)}"
                )
        
        @self.router.get("/bebida/{bebida_id}", response_model=List[PersonalizacaoResponse])
        async def listar_personalizacoes_bebida(
            bebida_id: int,
            db: Session = Depends(get_db)
        ):
            """Lista personalizações disponíveis para uma bebida específica (via BO)"""
            try:
                from patterns.business_object import ProdutoBO
                bo = ProdutoBO(db)
                return bo.listar_personalizacoes_bebida_dict(bebida_id)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter personalizações da bebida: {str(e)}"
                )
        
        @self.router.post("/personalizar", response_model=BebidaPersonalizadaResponse)
        async def personalizar_bebida(
            request: BebidaPersonalizadaRequest,
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """
            Cria uma bebida personalizada usando Decorator Pattern (via BO)
            """
            try:
                from patterns.business_object import ProdutoBO
                bo = ProdutoBO(db)
                return bo.personalizar_bebida_dict(request.bebida_id, request.personalizacoes)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao personalizar bebida: {str(e)}"
                )
        
        @self.router.get("/categorias")
        async def listar_categorias(
            db: Session = Depends(get_db)
        ):
            """Lista categorias de personalizações disponíveis (via BO)"""
            try:
                from patterns.business_object import ProdutoBO
                bo = ProdutoBO(db)
                return bo.listar_categorias_personalizacao_dict()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter categorias: {str(e)}"
                )
        
        @self.router.get("/preview")
        async def preview_personalizacao(
            bebida_id: int,
            personalizacoes: str,  # IDs separados por vírgula
            db: Session = Depends(get_db)
        ):
            """Preview de bebida personalizada sem salvar (via BO)"""
            try:
                from patterns.business_object import ProdutoBO
                bo = ProdutoBO(db)
                ids = [int(i.strip()) for i in personalizacoes.split(",") if i.strip()]
                return bo.personalizar_bebida_dict(bebida_id, ids)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao gerar preview: {str(e)}"
                )
    
    async def listar_personalizacoes_disponiveis(
        self, 
        categoria: Optional[str], 
        db: Session
    ) -> List[PersonalizacaoResponse]:
        """Lista personalizações disponíveis, opcionalmente filtradas por categoria"""
        try:
            pers_repo = PersonalizacaoRepository(db)
            
            if categoria:
                personalizacoes = pers_repo.get_by_categoria(categoria)
            else:
                personalizacoes = pers_repo.get_all()
            
            # Filtrar apenas disponíveis
            personalizacoes_disponiveis = [p for p in personalizacoes if p.disponivel]
            
            return [
                PersonalizacaoResponse(
                    id=pers.id,
                    nome=pers.nome,
                    preco_adicional=pers.preco_adicional,
                    categoria=pers.categoria or "geral",
                    disponivel=pers.disponivel
                )
                for pers in personalizacoes_disponiveis
            ]
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar personalizações: {str(e)}"
            )
    
    async def obter_personalizacoes_bebida(
        self, 
        bebida_id: int, 
        db: Session
    ) -> List[PersonalizacaoResponse]:
        """Obtém personalizações específicas para uma bebida"""
        try:
            # Verificar se bebida existe
            bebida_repo = BebidaRepository(db)
            bebida = bebida_repo.get_by_id(bebida_id)
            
            if not bebida:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bebida não encontrada"
                )
            
            pers_repo = PersonalizacaoRepository(db)
            personalizacoes = pers_repo.get_by_bebida(bebida_id)
            
            return [
                PersonalizacaoResponse(
                    id=pers.id,
                    nome=pers.nome,
                    preco_adicional=pers.preco_adicional,
                    categoria=pers.categoria or "geral",
                    disponivel=pers.disponivel
                )
                for pers in personalizacoes
            ]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter personalizações da bebida: {str(e)}"
            )
    
    async def criar_bebida_personalizada(
        self, 
        request: BebidaPersonalizadaRequest, 
        db: Session
    ) -> BebidaPersonalizadaResponse:
        """Cria bebida personalizada usando Decorator Pattern"""
        try:
            # Obter bebida base
            bebida_repo = BebidaRepository(db)
            bebida_base = bebida_repo.get_by_id(request.bebida_id)
            
            if not bebida_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bebida não encontrada"
                )
            
            # Criar componente base usando Factory Pattern
            componente_bebida = self.menu_factory.criar_bebida(
                bebida_base.tipo.value,
                bebida_base.nome
            )
            
            if not componente_bebida:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Erro ao criar bebida base"
                )
            
            # Aplicar personalizações usando Decorator Pattern
            pers_repo = PersonalizacaoRepository(db)
            personalizacoes_aplicadas = []
            
            for pers_id in request.personalizacoes:
                personalizacao = pers_repo.get_by_id(pers_id)
                
                if not personalizacao or not personalizacao.disponivel:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Personalização {pers_id} não disponível"
                    )
                
                # Aplicar decorator específico ou genérico
                nome_decorator = personalizacao.nome.lower().replace(" ", "_")
                
                if nome_decorator in self.decorator_map:
                    # Usar decorator específico
                    decorator_class = self.decorator_map[nome_decorator]
                    componente_bebida = decorator_class(componente_bebida)
                else:
                    # Usar decorator genérico
                    componente_bebida = BebidaPersonalizada(
                        componente_bebida,
                        personalizacao.nome,
                        personalizacao.preco_adicional
                    )
                
                personalizacoes_aplicadas.append(
                    PersonalizacaoResponse(
                        id=personalizacao.id,
                        nome=personalizacao.nome,
                        preco_adicional=personalizacao.preco_adicional,
                        categoria=personalizacao.categoria or "geral",
                        disponivel=personalizacao.disponivel
                    )
                )
            
            return BebidaPersonalizadaResponse(
                bebida_base={
                    "id": bebida_base.id,
                    "nome": bebida_base.nome,
                    "preco_base": bebida_base.preco_base,
                    "tipo": bebida_base.tipo.value,
                    "descricao": bebida_base.descricao
                },
                personalizacoes_aplicadas=personalizacoes_aplicadas,
                descricao_final=componente_bebida.get_descricao(),
                preco_final=componente_bebida.get_preco(),
                tipo=componente_bebida.get_tipo()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao personalizar bebida: {str(e)}"
            )
    
    async def obter_categorias_personalizacao(self, db: Session) -> Dict[str, List[str]]:
        """Obtém categorias de personalizações disponíveis"""
        try:
            pers_repo = PersonalizacaoRepository(db)
            todas_personalizacoes = pers_repo.get_all()
            
            categorias = {}
            for pers in todas_personalizacoes:
                if pers.disponivel:
                    categoria = pers.categoria or "geral"
                    if categoria not in categorias:
                        categorias[categoria] = []
                    categorias[categoria].append(pers.nome)
            
            return categorias
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter categorias: {str(e)}"
            )
    
    async def gerar_preview_bebida(
        self, 
        bebida_id: int, 
        personalizacoes_str: str, 
        db: Session
    ) -> Dict[str, Any]:
        """Gera preview da bebida personalizada"""
        try:
            # Parse dos IDs das personalizações
            if personalizacoes_str:
                personalizacao_ids = [int(id.strip()) for id in personalizacoes_str.split(",")]
            else:
                personalizacao_ids = []
            
            # Criar request temporário
            request = BebidaPersonalizadaRequest(
                bebida_id=bebida_id,
                personalizacoes=personalizacao_ids
            )
            
            # Usar método de personalização existente
            resultado = await self.criar_bebida_personalizada(request, db)
            
            return {
                "preview": True,
                "bebida_personalizada": resultado,
                "resumo": {
                    "descricao": resultado.descricao_final,
                    "preco_original": resultado.bebida_base["preco_base"],
                    "preco_final": resultado.preco_final,
                    "valor_personalizacoes": resultado.preco_final - resultado.bebida_base["preco_base"],
                    "total_personalizacoes": len(resultado.personalizacoes_aplicadas)
                }
            }
            
        except HTTPException:
            raise
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IDs de personalização inválidos"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao gerar preview: {str(e)}"
            )
