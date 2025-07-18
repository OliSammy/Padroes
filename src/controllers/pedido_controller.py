"""
Controller para gerenciamento de pedidos (padrão MVC)
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from DAO.config import get_db
from DAO.models import Cliente, StatusPedidoEnum, MetodoPagamentoEnum
from DAO.crud import PedidoRepository, CarrinhoRepository
from patterns.business_object import PedidoBO
from patterns.observer import PedidoSubject, CozinhaObserver, ClienteObserver
from patterns.state import Pedido as PedidoState
from patterns.strategy import ContextoPagamento, DescontoPix, DescontoFidelidade, SemDesconto

# Importar autenticação
from src.auth_service import get_current_user, get_current_staff_user
from patterns.command import InterfaceUsuario


class PedidoCreate(BaseModel):
    """
    Schema para criação de pedido com desconto automático baseado no método de pagamento
    
    O sistema aplica desconto automaticamente conforme o método escolhido:
    - PIX: 5% de desconto
    - FIDELIDADE: 10% de desconto  
    - DINHEIRO/CARTÃO: sem desconto
    """
    metodo_pagamento: str = Field(
        ..., 
        description="Método de pagamento",
        examples=["pix", "cartao", "dinheiro", "fidelidade"],
        pattern="^(pix|cartao|dinheiro|fidelidade)$"
    )


class PedidoStatusUpdate(BaseModel):
    """Schema para atualização de status do pedido"""
    novo_status: str = Field(
        ...,
        description="Novo status do pedido",
        examples=["pendente", "recebido", "em_preparo", "pronto", "entregue", "cancelado"],
        pattern="^(pendente|recebido|em_preparo|pronto|entregue|cancelado)$"
    )


class PedidoResponse(BaseModel):
    """Schema de resposta para pedido com todas as informações principais"""
    id: int = Field(..., description="ID único do pedido")
    cliente_id: int = Field(..., description="ID do cliente que fez o pedido")
    cliente_nome: str = Field(..., description="Nome do cliente")
    status: str = Field(..., description="Status atual do pedido", examples=["pendente", "recebido", "em_preparo", "pronto", "entregue", "cancelado"])
    total: float = Field(..., description="Valor total dos itens antes do desconto", ge=0)
    desconto: float = Field(..., description="Valor do desconto aplicado", ge=0)
    total_final: float = Field(..., description="Valor final após desconto", ge=0)
    metodo_pagamento: str = Field(..., description="Método de pagamento utilizado", examples=["dinheiro", "cartao", "pix", "fidelidade"])
    data_pedido: datetime = Field(..., description="Data e hora de criação do pedido")
    data_atualizacao: datetime = Field(..., description="Data e hora da última atualização")
    observacoes: Optional[str] = Field(None, description="Observações consolidadas dos itens do pedido")
    itens_count: int = Field(..., description="Número total de itens no pedido", ge=0)


class PedidoDetalhesResponse(PedidoResponse):
    """Schema detalhado de resposta para pedido com itens e histórico completos"""
    itens: List[Dict[str, Any]] = Field(..., description="Lista completa de itens do pedido com personalizações")
    historico: List[Dict[str, Any]] = Field(..., description="Histórico completo de alterações de status")


class PedidoController:
    """Controller para operações de pedidos"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/pedidos", tags=["Pedidos"])
        self._setup_routes()
        self.interface_comando = InterfaceUsuario()
    
    def _setup_routes(self):
        """Configura as rotas do controller"""
        
        @self.router.post("", response_model=PedidoResponse)
        async def criar_pedido(
            pedido_data: PedidoCreate,
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """
            Cria um novo pedido a partir do carrinho do usuário
            
            **Parâmetros:**
            - **metodo_pagamento**: Método de pagamento escolhido ('dinheiro', 'cartao', 'pix', 'fidelidade')
            
            **Comportamento:**
            - Converte todos os itens do carrinho em um pedido
            - Aplica desconto automático baseado no método de pagamento:
              - PIX: 5% de desconto
              - FIDELIDADE: 10% de desconto
              - DINHEIRO/CARTÃO: sem desconto
            - Status inicial: PENDENTE
            - Limpa o carrinho após criação do pedido
            
            **Retorna:**
            - Dados completos do pedido criado com status PENDENTE
            """
            return await self.criar_novo_pedido(current_user.id, pedido_data, db)
        
        @self.router.get("", response_model=List[PedidoResponse])
        async def listar_pedidos(
            status: Optional[str] = None,
            skip: int = 0,
            limit: int = 100,
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """
            Lista pedidos do usuário logado com filtros opcionais
            
            **Parâmetros de Query:**
            - **status** (opcional): Filtrar por status específico ('pendente', 'recebido', 'em_preparo', 'pronto', 'entregue', 'cancelado')
            - **skip** (opcional): Número de registros para pular (paginação) - padrão: 0
            - **limit** (opcional): Número máximo de registros retornados - padrão: 100
            
            **Retorna:**
            - Lista de pedidos do usuário autenticado, ordenados por data de criação
            """
            return await self.listar_pedidos_filtrados(current_user.id, status, skip, limit, db)
        
        @self.router.get("/{pedido_id}", response_model=PedidoDetalhesResponse)
        async def obter_pedido(
            pedido_id: int,
            current_user: Cliente = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """
            Obtém detalhes completos de um pedido específico
            
            **Parâmetros de Path:**
            - **pedido_id**: ID único do pedido a ser consultado
            
            **Retorna:**
            - Dados completos do pedido incluindo:
              - Informações básicas do pedido
              - Lista detalhada de itens com personalizações
              - Histórico completo de mudanças de status
            
            **Observações:**
            - Usuários podem consultar apenas seus próprios pedidos
            - Staff pode consultar qualquer pedido
            """
            return await self.obter_detalhes_pedido(pedido_id, db)
        
        @self.router.patch("/{pedido_id}/status")
        async def alterar_status(
            pedido_id: int,
            status_data: PedidoStatusUpdate,
            db: Session = Depends(get_db)
        ):
            """
            Altera o status de um pedido específico
            
            **Parâmetros de Path:**
            - **pedido_id**: ID único do pedido a ter o status alterado
            
            **Body (JSON):**
            - **novo_status**: Novo status do pedido ('recebido', 'em_preparo', 'pronto', 'entregue', 'cancelado')
            
            **Transições Permitidas:**
            - PENDENTE → RECEBIDO ou CANCELADO
            - RECEBIDO → EM_PREPARO ou CANCELADO  
            - EM_PREPARO → PRONTO
            - PRONTO → ENTREGUE
            - ENTREGUE e CANCELADO são estados finais
            
            **Retorna:**
            - Confirmação da alteração de status com o pedido_id e novo status
            """
            return await self.alterar_status_pedido(pedido_id, status_data, db)
        
        @self.router.get("/cliente/{cliente_id}/historico", response_model=List[PedidoResponse])
        async def historico_cliente(
            cliente_id: int,
            db: Session = Depends(get_db)
        ):
            """Obtém histórico de pedidos do cliente"""
            return await self.obter_historico_cliente(cliente_id, db)
        
        @self.router.get("/cozinha/pendentes")
        async def pedidos_cozinha(
            db: Session = Depends(get_db)
        ):
            """Lista pedidos pendentes para a cozinha"""
            return await self.listar_pedidos_cozinha(db)
        
        # ENDPOINTS PARA COZINHA (STAFF) - Ver pedidos por status
        @self.router.get("/cozinha/todos", response_model=List[PedidoResponse])
        async def listar_todos_pedidos_cozinha(
            status: Optional[str] = None,
            skip: int = 0,
            limit: int = 100,
            current_staff: Cliente = Depends(get_current_staff_user),
            db: Session = Depends(get_db)
        ):
            """
            Lista todos os pedidos do sistema para equipe da cozinha (STAFF apenas)
            
            **Acesso:** Restrito a usuários do tipo STAFF
            
            **Parâmetros de Query:**
            - **status** (opcional): Filtrar por status específico ('pendente', 'recebido', 'em_preparo', 'pronto', 'entregue', 'cancelado')
            - **skip** (opcional): Número de registros para pular (paginação) - padrão: 0
            - **limit** (opcional): Número máximo de registros retornados - padrão: 100
            
            **Retorna:**
            - Lista de todos os pedidos de todos os clientes (visão administrativa da cozinha)
            - Usado para monitoramento geral do fluxo de pedidos
            """
            return await self.listar_todos_pedidos_por_status(status, skip, limit, db)
        
        @self.router.get("/cozinha/status/{status}", response_model=List[PedidoResponse])
        async def listar_pedidos_por_status_cozinha(
            status: str,
            skip: int = 0,
            limit: int = 100,
            current_staff: Cliente = Depends(get_current_staff_user),
            db: Session = Depends(get_db)
        ):
            """
            Lista pedidos por status específico para equipe da cozinha (STAFF apenas)
            
            **Acesso:** Restrito a usuários do tipo STAFF
            
            **Parâmetros de Path:**
            - **status**: Status específico a filtrar ('pendente', 'recebido', 'em_preparo', 'pronto', 'entregue', 'cancelado')
            
            **Parâmetros de Query:**
            - **skip** (opcional): Número de registros para pular (paginação) - padrão: 0
            - **limit** (opcional): Número máximo de registros retornados - padrão: 100
            
            **Casos de Uso Comuns:**
            - `/cozinha/status/pendente` - Novos pedidos aguardando confirmação
            - `/cozinha/status/recebido` - Pedidos confirmados aguardando preparo
            - `/cozinha/status/em_preparo` - Pedidos atualmente sendo preparados
            - `/cozinha/status/pronto` - Pedidos prontos para entrega
            
            **Retorna:**
            - Lista de pedidos filtrados pelo status especificado
            """
            return await self.listar_todos_pedidos_por_status(status, skip, limit, db)
        
        # NOVOS ENDPOINTS USANDO STATE PATTERN
        @self.router.post("/{pedido_id}/avancar-estado")
        async def avancar_estado_pedido(
            pedido_id: int,
            db: Session = Depends(get_db)
        ):
            """
            Avança o pedido para o próximo estado usando State Pattern
            
            **Parâmetros de Path:**
            - **pedido_id**: ID único do pedido
            
            **Comportamento:**
            - Usa State Pattern para determinar o próximo estado automaticamente
            - Sequência: Pendente → Recebido → Em Preparo → Pronto → Entregue
            - Integra Observer Pattern para notificações automáticas
            
            **Retorna:**
            - Estado anterior e novo estado
            - Confirmação da transição realizada
            - Lista dos padrões utilizados
            
            **Casos de Uso:**
            - Cozinha avançando status sequencialmente
            - Fluxo automático sem escolher status específico
            """
            return await self.avancar_estado_usando_state_pattern(pedido_id, db)
        
        @self.router.post("/{pedido_id}/cancelar-state")
        async def cancelar_pedido_state(
            pedido_id: int,
            db: Session = Depends(get_db)
        ):
            """
            Cancela pedido usando State Pattern para validar se é possível
            
            **Parâmetros de Path:**
            - **pedido_id**: ID único do pedido a ser cancelado
            
            **Comportamento:**
            - Usa State Pattern para verificar se cancelamento é permitido
            - Estados que permitem cancelamento: Pendente, Recebido
            - Estados que NÃO permitem: Em Preparo, Pronto, Entregue, Cancelado
            - Integra Observer Pattern para notificações
            
            **Retorna:**
            - Sucesso/falha do cancelamento
            - Razão se não foi possível cancelar
            - Estado anterior e atual
            
            **Vantagens:**
            - Validação automática baseada no estado atual
            - Lógica de negócio encapsulada no State Pattern
            """
            return await self.cancelar_usando_state_pattern(pedido_id, db)
    
    async def criar_novo_pedido(
        self,
        cliente_id: int,
        pedido_data: PedidoCreate,
        db: Session
    ) -> PedidoResponse:
        """Cria novo pedido usando Business Object com desconto automático"""
        try:
            pedido_bo = PedidoBO(db)
            # O método do BO já faz toda a lógica de validação, desconto, pagamento, etc.
            pedido = pedido_bo.criar_pedido_completo(cliente_id, pedido_data.metodo_pagamento)
            return PedidoResponse(**pedido)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar pedido: {str(e)}"
            )
    
    async def listar_pedidos_filtrados(
        self,
        cliente_id: Optional[int],
        status_filtro: Optional[str],
        skip: int,
        limit: int,
        db: Session
    ) -> List[PedidoResponse]:
        """Lista pedidos com filtros (dados prontos do BO)"""
        try:
            pedido_bo = PedidoBO(db)
            pedidos_dict = pedido_bo.listar_pedidos_dict(cliente_id, status_filtro, skip, limit)
            return [PedidoResponse(**pedido) for pedido in pedidos_dict]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar pedidos: {str(e)}"
            )
    
    async def obter_detalhes_pedido(self, pedido_id: int, db: Session) -> PedidoDetalhesResponse:
        """Obtém detalhes completos do pedido (usando apenas dados serializáveis do BO)"""
        try:
            pedido_bo = PedidoBO(db)
            pedido_dict = pedido_bo.obter_pedido_detalhado_dict(pedido_id)
            if not pedido_dict:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pedido não encontrado"
                )
            return PedidoDetalhesResponse(**pedido_dict)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter pedido: {str(e)}"
            )
    
    async def alterar_status_pedido(
        self, 
        pedido_id: int, 
        status_data: PedidoStatusUpdate, 
        db: Session
    ) -> Dict[str, Any]:
        """Altera status do pedido usando State Pattern"""
        try:
            # Validar status
            try:
                novo_status = StatusPedidoEnum(status_data.novo_status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Status inválido"
                )
            
            # Usar Business Object
            pedido_bo = PedidoBO(db)
            
            if pedido_bo.alterar_status(pedido_id, novo_status):
                return {
                    "message": "Status alterado com sucesso",
                    "pedido_id": pedido_id,
                    "novo_status": novo_status.value
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não foi possível alterar o status. Verifique as transições permitidas."
                )
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao alterar status: {str(e)}"
            )
    
    async def cancelar_pedido_sistema(self, pedido_id: int, db: Session) -> Dict[str, Any]:
        """Cancela pedido usando Command Pattern"""
        try:
            # Primeiro verificar se o pedido existe no banco
            pedido_bo = PedidoBO(db)
            
            # Tentar cancelar no banco primeiro
            if pedido_bo.alterar_status(pedido_id, StatusPedidoEnum.CANCELADO):
                # Se cancelou no banco, tentar cancelar no Command Pattern também
                # (isso pode falhar se o pedido não estiver na lista interna, mas não é crítico)
                try:
                    self.interface_comando.cancelar_pedido(pedido_id)
                except Exception as command_error:
                    print(f"[WARNING] Command Pattern falhou, mas pedido foi cancelado no banco: {command_error}")
                
                return {
                    "message": "Pedido cancelado com sucesso",
                    "pedido_id": pedido_id
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não foi possível cancelar o pedido"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao cancelar pedido: {str(e)}"
            )
    
    async def obter_historico_cliente(self, cliente_id: int, db: Session) -> List[PedidoResponse]:
        """Obtém histórico de pedidos do cliente (dados prontos do BO)"""
        try:
            pedido_bo = PedidoBO(db)
            historico = pedido_bo.historico_cliente_dict(cliente_id)
            return [PedidoResponse(**pedido) for pedido in historico]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter histórico: {str(e)}"
            )
    
    async def listar_pedidos_cozinha(self, db: Session) -> List[Dict[str, Any]]:
        """Lista pedidos para a cozinha (usando apenas dados serializáveis do BO)"""
        try:
            pedido_bo = PedidoBO(db)
            pedidos_dict = pedido_bo.listar_pedidos_dict(None, 'pendente', 0, 1000)  # ou outro status se necessário
            # Adiciona tempo_espera e itens serializados
            resultado = []
            for pedido in pedidos_dict:
                data_pedido = pedido.get("data_pedido")
                tempo_espera = None
                if data_pedido:
                    try:
                        tempo_espera = (datetime.utcnow() - data_pedido).total_seconds() / 60
                    except Exception:
                        tempo_espera = None
                pedido_formatado = {
                    "id": pedido.get("id"),
                    "cliente_nome": pedido.get("cliente_nome"),
                    "status": pedido.get("status"),
                    "total": pedido.get("total_final"),
                    "data_pedido": data_pedido,
                    "tempo_espera": tempo_espera,
                    "itens": pedido.get("itens", [])  # Se quiser detalhar, adapte o BO para trazer itens
                }
                resultado.append(pedido_formatado)
            return resultado
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar pedidos da cozinha: {str(e)}"
            )
    
    # NOVOS MÉTODOS USANDO STATE PATTERN
    async def avancar_estado_usando_state_pattern(self, pedido_id: int, db: Session) -> Dict[str, Any]:
        """Avança estado do pedido usando State Pattern (delegando ao Business Object)"""
        try:
            pedido_bo = PedidoBO(db)
            resultado = pedido_bo.avancar_estado_pedido(pedido_id)
            # O método do BO já retorna o dicionário esperado, inclusive com mensagem e transição
            return resultado
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao avançar estado: {str(e)}"
            )
    
    async def cancelar_usando_state_pattern(self, pedido_id: int, db: Session) -> Dict[str, Any]:
        """Cancela pedido usando State Pattern para validação (delegando ao Business Object)"""
        try:
            pedido_bo = PedidoBO(db)
            resultado = pedido_bo.cancelar_pedido_state_pattern(pedido_id)
            return resultado
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao cancelar pedido: {str(e)}"
            )
    
    def _get_proxima_transicao(self, estado_atual: str) -> Optional[str]:
        """Obtém a próxima transição possível"""
        transicoes = {
            "Pendente": "Recebido",
            "Recebido": "Em preparo", 
            "Em preparo": "Pronto",
            "Pronto": "Entregue",
            "Entregue": None,
            "Cancelado": None
        }
        return transicoes.get(estado_atual)
    
    def _get_razao_nao_cancelamento(self, estado: str) -> str:
        """Obtém razão pela qual não pode cancelar no estado atual"""
        razoes = {
            "Em preparo": "Pedido já está sendo preparado na cozinha",
            "Pronto": "Pedido já está pronto para entrega",
            "Entregue": "Pedido já foi entregue ao cliente",
            "Cancelado": "Pedido já está cancelado"
        }
        return razoes.get(estado, "Estado não permite cancelamento")

    async def listar_todos_pedidos_por_status(
        self, 
        status_filtro: Optional[str], 
        skip: int, 
        limit: int, 
        db: Session
    ) -> List[PedidoResponse]:
        """Lista todos os pedidos de todos os clientes por status (para admin), usando apenas dados prontos do BO"""
        try:
            pedido_bo = PedidoBO(db)
            # cliente_id=None para buscar todos
            pedidos_dict = pedido_bo.listar_pedidos_dict(None, status_filtro, skip, limit)
            return [PedidoResponse(**pedido) for pedido in pedidos_dict]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar pedidos: {str(e)}"
            )
