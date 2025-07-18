
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from datetime import datetime
import bcrypt

from database.models import *

class BaseRepository:
    """Repositório base com operações CRUD"""
    
    def __init__(self, db: Session, model):
        self.db = db
        self.model = model
    
    def create(self, obj):
        """Cria um novo registro"""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def get_by_id(self, id: int):
        """Busca por ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100):
        """Lista todos os registros"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def update(self, id: int, **kwargs):
        """Atualiza um registro"""
        obj = self.get_by_id(id)
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            self.db.commit()
            self.db.refresh(obj)
        return obj
    
    def delete(self, id: int):
        """Deleta um registro"""
        obj = self.get_by_id(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj

class ClienteRepository(BaseRepository):
       
    def __init__(self, db: Session):
        super().__init__(db, Cliente)
    
    def get_by_email(self, email: str) -> Optional[Cliente]:
        """Busca cliente por email"""
        return self.db.query(Cliente).filter(Cliente.email == email).first()
    
    def authenticate(self, email: str, password: str) -> Optional[Cliente]:
        """Autentica cliente"""
        cliente = self.get_by_email(email)
        if cliente and bcrypt.checkpw(password.encode('utf-8'), cliente.senha_hash.encode('utf-8')):
            return cliente
        return None
    
    def create_cliente(self, nome: str, email: str, password: str) -> Cliente:
        """Cria novo cliente"""
        senha_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cliente = Cliente(
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            pontos_fidelidade=0
        )
        return self.create(cliente)
    
    def update_pontos_fidelidade(self, cliente_id: int, pontos: int):
        """Atualiza pontos de fidelidade"""
        cliente = self.get_by_id(cliente_id)
        if cliente:
            cliente.pontos_fidelidade += pontos
            self.db.commit()
            self.db.refresh(cliente)
        return cliente

class BebidaRepository(BaseRepository):
    """Repositório para bebidas"""
    
    def __init__(self, db: Session):
        super().__init__(db, Bebida)
    
    def get_by_tipo(self, tipo: TipoBebidasEnum) -> List[Bebida]:
        """Busca bebidas por tipo"""
        return self.db.query(Bebida).filter(
            and_(Bebida.tipo == tipo, Bebida.disponivel == True)
        ).all()
    
    def get_disponiveis(self) -> List[Bebida]:
        """Lista bebidas disponíveis"""
        return self.db.query(Bebida).filter(Bebida.disponivel == True).all()
    
    def search(self, query: str) -> List[Bebida]:
        """Busca bebidas por nome ou descrição"""
        return self.db.query(Bebida).filter(
            and_(
                Bebida.disponivel == True,
                or_(
                    Bebida.nome.ilike(f"%{query}%"),
                    Bebida.descricao.ilike(f"%{query}%")
                )
            )
        ).all()
    
    def listar_bebidas(self, tipo: Optional[str] = None, disponivel: Optional[bool] = True) -> List[Bebida]:
        """Lista bebidas com filtros opcionais"""
        query = self.db.query(Bebida)
        
        if disponivel is not None:
            query = query.filter(Bebida.disponivel == disponivel)
        
        if tipo:
            try:
                tipo_enum = TipoBebidasEnum(tipo)
                query = query.filter(Bebida.tipo == tipo_enum)
            except ValueError:
                pass  # Tipo inválido, ignora o filtro
        
        return query.all()
    
    def obter_por_id(self, bebida_id: int) -> Optional[Bebida]:
        """Obtém bebida por ID"""
        return self.get_by_id(bebida_id)
    
    def obter_por_nome(self, nome: str) -> Optional[Bebida]:
        """Busca bebida por nome"""
        return self.db.query(Bebida).filter(Bebida.nome == nome).first()
    
    def tem_pedidos_associados(self, bebida_id: int) -> bool:
        """Verifica se a bebida tem pedidos associados"""
        from database.models import ItemPedido
        count = self.db.query(ItemPedido).filter(ItemPedido.bebida_id == bebida_id).count()
        return count > 0

class PersonalizacaoRepository(BaseRepository):
    """Repositório para personalizações"""
    
    def __init__(self, db: Session):
        super().__init__(db, Personalizacao)
    
    def get_by_bebida(self, bebida_id: int) -> List[Personalizacao]:
        """Busca personalizações por bebida"""
        return self.db.query(Personalizacao).filter(
            and_(
                Personalizacao.bebida_id == bebida_id,
                Personalizacao.disponivel == True
            )
        ).all()
    
    def obter_por_bebida(self, bebida_id: int) -> List[Personalizacao]:
        """Alias para get_by_bebida"""
        return self.get_by_bebida(bebida_id)
    
    def obter_por_id(self, personalizacao_id: int) -> Optional[Personalizacao]:
        """Obtém personalização por ID"""
        return self.get_by_id(personalizacao_id)
    
    def get_by_categoria(self, categoria: str) -> List[Personalizacao]:
        """Busca personalizações por categoria"""
        return self.db.query(Personalizacao).filter(
            and_(
                Personalizacao.categoria == categoria,
                Personalizacao.disponivel == True
            )
        ).all()

class CarrinhoRepository(BaseRepository):
    def update_item(self, item_id: int, quantidade: int, personalizacoes: Optional[list] = None):
        """Atualiza quantidade e personalizações de um item do carrinho"""
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.quantidade = quantidade
        # Remove personalizações antigas
        self.db.query(ItemCarrinhoPersonalizacao).filter(
            ItemCarrinhoPersonalizacao.item_carrinho_id == item_id
        ).delete()
        # Adiciona novas personalizações
        if personalizacoes:
            for pers_id in personalizacoes:
                pers_item = ItemCarrinhoPersonalizacao(
                    item_carrinho_id=item_id,
                    personalizacao_id=pers_id
                )
                self.db.add(pers_item)
        self.db.commit()
        self.db.refresh(item)
        return item
    """Repositório para carrinho"""
    
    def __init__(self, db: Session):
        super().__init__(db, ItemCarrinho)
    
    def get_by_cliente(self, cliente_id: int) -> List[ItemCarrinho]:
        """Busca itens do carrinho por cliente"""
        return self.db.query(ItemCarrinho).filter(
            ItemCarrinho.cliente_id == cliente_id
        ).all()
    
    def add_item(self, cliente_id: int, bebida_id: int, quantidade: int = 1, personalizacoes: Optional[List[int]] = None, observacoes: Optional[str] = None):
        """Adiciona item ao carrinho (sempre criando item separado), deduplicando personalizações"""
        # Busca bebida e calcula preço
        bebida = self.db.query(Bebida).filter(Bebida.id == bebida_id).first()
        if not bebida:
            raise ValueError("Bebida não encontrada")
        
        preco_unitario = bebida.preco_base
        
        # Deduplicar personalizações
        personalizacoes_unicas = list(dict.fromkeys(personalizacoes)) if personalizacoes else []
        # Adiciona preço das personalizações
        for pers_id in personalizacoes_unicas:
            pers = self.db.query(Personalizacao).filter(Personalizacao.id == pers_id).first()
            if pers:
                preco_unitario += pers.preco_adicional
        
        # SEMPRE cria novo item (removendo verificação de item existente para permitir itens separados)
        item = ItemCarrinho(
            cliente_id=cliente_id,
            bebida_id=bebida_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacoes=observacoes
        )
        item = self.create(item)
        
        # Adiciona personalizações
        for pers_id in personalizacoes_unicas:
            pers_item = ItemCarrinhoPersonalizacao(
                item_carrinho_id=item.id,
                personalizacao_id=pers_id
            )
            self.db.add(pers_item)
        if personalizacoes_unicas:
            self.db.commit()
        
        return item
    
    def update_quantidade(self, item_id: int, quantidade: int):
        """Atualiza quantidade de um item"""
        item = self.get_by_id(item_id)
        if item:
            item.quantidade = quantidade
            self.db.commit()
            self.db.refresh(item)
        return item
    
    def clear_carrinho(self, cliente_id: int):
        """Limpa carrinho do cliente"""
        self.db.query(ItemCarrinho).filter(
            ItemCarrinho.cliente_id == cliente_id
        ).delete()
        self.db.commit()
    
    def get_total_carrinho(self, cliente_id: int) -> float:
        """Calcula total do carrinho"""
        itens = self.get_by_cliente(cliente_id)
        total = sum(item.preco_unitario * item.quantidade for item in itens)
        return total

class PedidoRepository(BaseRepository):
    """Repositório para pedidos"""
    
    def __init__(self, db: Session):
        super().__init__(db, Pedido)
    
    def obter_por_id(self, id: int) -> Optional[Pedido]:
        """Busca pedido por ID"""
        return self.get_by_id(id)
    
    def obter_todos(self, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Lista todos os pedidos"""
        return self.get_all(skip, limit)
    
    def salvar(self, pedido: Pedido) -> Pedido:
        """Salva ou atualiza um pedido"""
        if pedido.id:
            self.db.merge(pedido)
        else:
            self.db.add(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido
    
    def obter_pedidos_por_cliente(self, cliente_id: int) -> List[Pedido]:
        """Busca pedidos por cliente"""
        return self.get_by_cliente(cliente_id)
    
    def obter_pedidos_por_status(self, status: StatusPedidoEnum) -> List[Pedido]:
        """Busca pedidos por status"""
        return self.get_by_status(status)
    
    def get_by_cliente(self, cliente_id: int) -> List[Pedido]:
        """Busca pedidos por cliente"""
        return self.db.query(Pedido).filter(
            Pedido.cliente_id == cliente_id
        ).order_by(desc(Pedido.created_at)).all()
    
    def get_by_status(self, status: StatusPedidoEnum, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Busca pedidos por status com paginação"""
        return self.db.query(Pedido).filter(
            Pedido.status == status
        ).order_by(Pedido.created_at).offset(skip).limit(limit).all()
    
    def get_pedidos_cozinha(self) -> List[Pedido]:
        """Busca pedidos para a cozinha"""
        return self.db.query(Pedido).filter(
            Pedido.status.in_([
                StatusPedidoEnum.PENDENTE,
                StatusPedidoEnum.EM_PREPARO
            ])
        ).order_by(Pedido.created_at).all()
    
    def create_from_carrinho(self, cliente_id: int, metodo_pagamento: MetodoPagamentoEnum) -> Pedido:
        """Cria pedido a partir do carrinho com desconto automático baseado no método de pagamento"""
        # Busca itens do carrinho
        carrinho_repo = CarrinhoRepository(self.db)
        itens_carrinho = carrinho_repo.get_by_cliente(cliente_id)
        
        if not itens_carrinho:
            raise ValueError("Carrinho vazio")
        
        # Calcula totais
        total = sum(item.preco_unitario * item.quantidade for item in itens_carrinho)
        desconto = 0.0
        
        # Aplica desconto automaticamente baseado no método de pagamento
        if metodo_pagamento == MetodoPagamentoEnum.PIX:
            desconto = total * 0.05  # 5% de desconto para PIX
        elif metodo_pagamento == MetodoPagamentoEnum.FIDELIDADE:
            desconto = total * 0.10  # 10% de desconto para fidelidade
        # DINHEIRO e CARTAO não têm desconto (desconto = 0.0)
        
        total_final = total - desconto
        
        # Cria pedido
        pedido = Pedido(
            cliente_id=cliente_id,
            total=total,
            desconto=desconto,
            total_final=total_final,
            status=StatusPedidoEnum.PENDENTE,
            metodo_pagamento=metodo_pagamento
        )
        pedido = self.create(pedido)
        
        # Lista para consolidar observações
        observacoes_consolidadas = []
        
        # Cria itens do pedido
        for idx, item_carrinho in enumerate(itens_carrinho, 1):
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                bebida_id=item_carrinho.bebida_id,
                quantidade=item_carrinho.quantidade,
                preco_unitario=item_carrinho.preco_unitario,
                subtotal=item_carrinho.preco_unitario * item_carrinho.quantidade,
                observacoes=item_carrinho.observacoes  # Transfere observações do carrinho
            )
            self.db.add(item_pedido)
            
            # Consolida observações para o pedido geral
            obs = getattr(item_carrinho, 'observacoes', None)
            if obs:
                bebida_nome = item_carrinho.bebida.nome
                observacoes_consolidadas.append(f"Item {idx} ({bebida_nome}): {obs}")
            
            # Copia personalizações
            for pers in item_carrinho.personalizacoes:
                item_pers = ItemPedidoPersonalizacao(
                    item_pedido_id=item_pedido.id,
                    personalizacao_id=pers.personalizacao_id
                )
                self.db.add(item_pers)
        
        # Commit dos itens primeiro
        self.db.commit()
        
        # Atualiza observações consolidadas do pedido usando SQL direto
        if observacoes_consolidadas:
            from sqlalchemy import text
            observacoes_texto = ", ".join(observacoes_consolidadas)
            self.db.execute(
                text("UPDATE pedidos SET observacoes = :obs WHERE id = :pedido_id"),
                {"obs": observacoes_texto, "pedido_id": pedido.id}
            )
            self.db.commit()
        
        # Limpa carrinho
        carrinho_repo.clear_carrinho(cliente_id)
        
        # Cria histórico
        self.add_historico(pedido.id, None, StatusPedidoEnum.PENDENTE, "Pedido criado")
        
        self.db.commit()
        return pedido
    
    def update_status(self, pedido_id: int, novo_status: StatusPedidoEnum, observacao: str = None):
        """Atualiza status do pedido"""
        pedido = self.get_by_id(pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado")
        
        status_anterior = pedido.status
        pedido.status = novo_status
        pedido.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(pedido)
        
        # Adiciona ao histórico
        self.add_historico(pedido_id, status_anterior, novo_status, observacao)
        
        return pedido
    
    def add_historico(self, pedido_id: int, status_anterior: StatusPedidoEnum, 
                     status_novo: StatusPedidoEnum, observacao: str = None):
        """Adiciona entrada no histórico"""
        historico = HistoricoPedido(
            pedido_id=pedido_id,
            status_anterior=status_anterior,
            status_novo=status_novo,
            observacao=observacao
        )
        self.db.add(historico)
        self.db.commit()
    
    def get_estatisticas(self):
        """Retorna estatísticas dos pedidos"""
        total_pedidos = self.db.query(Pedido).count()
        pedidos_hoje = self.db.query(Pedido).filter(
            Pedido.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        faturamento_total = self.db.query(Pedido).filter(
            Pedido.status != StatusPedidoEnum.CANCELADO
        ).with_entities(Pedido.total_final).all()
        
        faturamento = sum(f[0] for f in faturamento_total if f[0])
        
        return {
            "total_pedidos": total_pedidos,
            "pedidos_hoje": pedidos_hoje,
            "faturamento_total": faturamento,
            "pedidos_pendentes": self.db.query(Pedido).filter(
                Pedido.status == StatusPedidoEnum.PENDENTE
            ).count(),
            "pedidos_em_preparo": self.db.query(Pedido).filter(
                Pedido.status == StatusPedidoEnum.EM_PREPARO
            ).count()
        }

    def listar_por_cliente(self, cliente_id: int, limit: int = 10, offset: int = 0) -> List[Pedido]:
        """Lista pedidos de um cliente com paginação"""
        return self.db.query(Pedido).filter(
            Pedido.cliente_id == cliente_id
        ).order_by(desc(Pedido.created_at)).offset(offset).limit(limit).all()

    def listar_com_filtros(self, status: Optional[StatusPedidoEnum] = None, 
                          data_inicio: Optional[datetime] = None, 
                          data_fim: Optional[datetime] = None,
                          limit: int = 50, offset: int = 0) -> List[Pedido]:
        """Lista pedidos com filtros"""
        query = self.db.query(Pedido)
        
        if status:
            query = query.filter(Pedido.status == status)
        
        if data_inicio:
            query = query.filter(Pedido.created_at >= data_inicio)
            
        if data_fim:
            query = query.filter(Pedido.created_at <= data_fim)
        
        return query.order_by(desc(Pedido.created_at)).offset(offset).limit(limit).all()

    def listar_por_status(self, status: StatusPedidoEnum, limit: int = 20, offset: int = 0) -> List[Pedido]:
        """Lista pedidos por status com paginação"""
        return self.db.query(Pedido).filter(
            Pedido.status == status
        ).order_by(Pedido.created_at).offset(offset).limit(limit).all()


class HistoricoRepository(BaseRepository):
    """Repositório para histórico de pedidos"""
    
    def __init__(self, db: Session):
        super().__init__(db, HistoricoPedido)
    
    def obter_por_id(self, id: int) -> Optional[HistoricoPedido]:
        """Busca histórico por ID"""
        return self.get_by_id(id)
    
    def obter_por_pedido(self, pedido_id: int) -> List[HistoricoPedido]:
        """Busca histórico de um pedido específico"""
        return self.db.query(HistoricoPedido).filter(
            HistoricoPedido.pedido_id == pedido_id
        ).order_by(HistoricoPedido.timestamp).all()
    
    def salvar(self, historico: HistoricoPedido) -> HistoricoPedido:
        """Salva entrada do histórico"""
        return self.create(historico)
    
    def obter_ultimas_mudancas(self, limit: int = 50) -> List[HistoricoPedido]:
        """Obtém as últimas mudanças de status"""
        return self.db.query(HistoricoPedido).order_by(
            desc(HistoricoPedido.timestamp)
        ).limit(limit).all()
    
    def obter_historico_periodo(self, data_inicio: datetime, data_fim: datetime) -> List[HistoricoPedido]:
        """Obtém histórico de um período específico"""
        return self.db.query(HistoricoPedido).filter(
            and_(
                HistoricoPedido.timestamp >= data_inicio,
                HistoricoPedido.timestamp <= data_fim
            )
        ).order_by(HistoricoPedido.timestamp).all()
