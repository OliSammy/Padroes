"""
Controller para notificações usando Observer Pattern (padrão MVC)
Sistema de Cafeteria - Padrões GoF
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from database.config import get_db
from database.models import Cliente, Pedido, StatusPedidoEnum
from database.repositories import PedidoRepository
from patterns.observer import PedidoSubject, CozinhaObserver, ClienteObserver

# Importar autenticação
from src.auth_service import get_current_user, get_current_staff_user


class NotificacaoResponse(BaseModel):
    """Schema de resposta para notificação"""
    id: str
    tipo: str  # "status_pedido", "novo_pedido", "pedido_pronto"
    titulo: str
    mensagem: str
    timestamp: datetime
    lida: bool = False
    dados_extras: Optional[Dict[str, Any]] = None


class AtualizarStatusRequest(BaseModel):
    """Schema para atualizar status do pedido"""
    novo_status: str
    observacao: Optional[str] = None


class NotificacaoController:
    """Controller para gerenciamento de notificações usando Observer Pattern"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/notificacoes", tags=["Notificações"])
        # Simular um sistema de notificações em memória (em produção seria um Redis/DB)
        self._notificacoes_sistema = []
        self._setup_routes()
        self._setup_observers()
    
    def _setup_observers(self):
        """Configura os observers do sistema"""
        # Em um sistema real, estes observers estariam sempre ativos
        self.cozinha_observer = CozinhaObserver()
        self.cliente_observer = ClienteObserver()
    
    def _setup_routes(self):
        """Configura as rotas do controller"""
        
        @self.router.get("/", response_model=List[NotificacaoResponse])
        async def obter_notificacoes(
            tipo: Optional[str] = None,
            limit: int = 20,
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_user)
        ):
            """
            Obtém notificações personalizadas usando Observer Pattern
            """
            try:
                from patterns.business_object import PedidoBO
                bo = PedidoBO(db)
                notificacoes = bo.obter_notificacoes_dict(current_user, tipo=tipo or '', limit=limit)
                return notificacoes
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter notificações: {str(e)}"
                )
        
        @self.router.post("/pedido/{pedido_id}/atualizar-status")
        async def atualizar_status_pedido(
            pedido_id: int,
            dados: AtualizarStatusRequest,
            db: Session = Depends(get_db),
            current_user: Cliente = Depends(get_current_staff_user)
        ):
            """Atualiza status de pedido e notifica observadores (apenas staff)"""
            try:
                # Validar status
                try:
                    novo_status = StatusPedidoEnum(dados.novo_status)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Status inválido. Status válidos: {[s.value for s in StatusPedidoEnum]}"
                    )
                
                # Atualizar pedido
                pedido_repo = PedidoRepository(db)
                pedido = pedido_repo.obter_por_id(pedido_id)
                
                if not pedido:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pedido não encontrado"
                    )
                
                status_anterior = pedido.status
                pedido_atualizado = pedido_repo.update_status(
                    pedido_id, 
                    novo_status, 
                    dados.observacao
                )
                
                # Usar Observer Pattern para notificar mudança
                pedido_subject = PedidoSubject(pedido_id)
                
                # Adicionar observers
                pedido_subject.adicionar_observer(self.cozinha_observer)
                pedido_subject.adicionar_observer(self.cliente_observer)
                
                # Definir dados da mudança
                pedido_subject.set_dados_pedido({
                    "pedido_id": pedido_id,
                    "status_anterior": status_anterior.value,
                    "status_novo": novo_status.value,
                    "cliente_id": pedido.cliente_id,
                    "cliente_nome": pedido.cliente.nome,
                    "observacao": dados.observacao,
                    "timestamp": datetime.now()
                })
                
                # Notificar todos os observers
                pedido_subject.notificar_observers()
                
                return {
                    "message": "Status atualizado com sucesso",
                    "pedido_id": pedido_id,
                    "status_anterior": status_anterior.value,
                    "status_novo": novo_status.value,
                    "observers_notificados": len(pedido_subject._observers)
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao atualizar status: {str(e)}"
                )
        
        @self.router.post("/marcar-como-lida/{notificacao_id}")
        async def marcar_notificacao_lida(
            notificacao_id: str,
            current_user: Cliente = Depends(get_current_user)
        ):
            """Marca uma notificação como lida"""
            try:
                # Em um sistema real, isso atualizaria o banco de dados
                return {
                    "message": "Notificação marcada como lida",
                    "notificacao_id": notificacao_id,
                    "usuario": current_user.nome
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao marcar notificação: {str(e)}"
                )
        
        @self.router.get("/tipos-disponiveis")
        async def obter_tipos_notificacao(
            current_user: Cliente = Depends(get_current_user)
        ):
            """Obtém tipos de notificação disponíveis para o usuário"""
            try:
                if current_user.tipo_usuario.value == "staff":
                    tipos = [
                        "novo_pedido",
                        "pedido_atrasado",
                        "pedido_cancelado",
                        "sistema"
                    ]
                else:
                    tipos = [
                        "status_pedido",
                        "promocao",
                        "fidelidade",
                        "sistema"
                    ]
                
                return {
                    "tipos_disponiveis": tipos,
                    "usuario_tipo": current_user.tipo_usuario.value
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao obter tipos: {str(e)}"
                )
        
        @self.router.get("/demo-observer")
        async def demonstrar_observer_pattern():
            """Demonstra o funcionamento do Observer Pattern"""
            try:
                # Criar subject
                pedido_subject = PedidoSubject(999)  # ID fictício
                
                # Adicionar observers
                cozinha = CozinhaObserver()
                cliente = ClienteObserver()
                
                pedido_subject.adicionar_observer(cozinha)
                pedido_subject.adicionar_observer(cliente)
                
                # Simular dados de mudança de status
                pedido_subject.set_dados_pedido({
                    "pedido_id": 999,
                    "status_anterior": "pendente",
                    "status_novo": "em_preparo",
                    "cliente_id": 1,
                    "cliente_nome": "Cliente Demo",
                    "timestamp": datetime.now()
                })
                
                # Notificar observers
                resultado_notificacao = pedido_subject.notificar_observers()
                
                return {
                    "demonstracao": "Observer Pattern",
                    "pedido_id": 999,
                    "observers_registrados": len(pedido_subject._observers),
                    "notificacao_enviada": True,
                    "detalhes": {
                        "cozinha_notificada": True,
                        "cliente_notificado": True,
                        "timestamp": datetime.now()
                    }
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro na demonstração: {str(e)}"
                )
